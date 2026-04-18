"""Aba Buscar — pesquisa JLCPCB com lista de resultados e painel de detalhe."""

from __future__ import annotations

import logging
import queue
import re
import threading
from io import BytesIO
from pathlib import Path
from typing import Callable

import customtkinter as ctk
import requests
from PIL import Image

from easyjlc.config import cache_dir
from easyjlc.core.jlc_api import DEFAULT_HEADERS
from easyjlc.core import (
    Component,
    EasyEdaError,
    EasyEdaRunner,
    JlcApiError,
    JlcClient,
    SearchResult,
    find_kicad_artifacts,
)
from easyjlc.i18n import t
from easyjlc.ui.bindings import bind_select_all
from easyjlc.ui.preview_panel import PreviewPanel

log = logging.getLogger("easyjlc.search_tab")

POLL_MS = 80
PAGE_SIZE = 20
LCSC_ID_RE = re.compile(r"^C\d+$", re.IGNORECASE)


class SearchTab(ctk.CTkFrame):
    """on_download é chamado com (lcsc_id) quando o usuário clica Baixar."""

    def __init__(
        self,
        master,
        client: JlcClient,
        runner: EasyEdaRunner,
        on_download: Callable[[str], None],
        on_log: Callable[[str], None],
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.client = client
        self.runner = runner
        self.on_download = on_download
        self.on_log = on_log

        self._msg_queue: "queue.Queue[tuple[str, object]]" = queue.Queue()
        self._raw_items: list[Component] = []
        self._current_components: list[Component] = []
        self._selected: Component | None = None
        self._current_page = 1
        self._total_pages = 1
        self._current_query = ""
        self._results_query = ""
        self._image_bytes_cache: dict[str, bytes] = {}
        self._pending_image_urls: set[str] = set()
        self._row_image_labels: dict[str, ctk.CTkLabel] = {}
        self._row_image_refs: dict[str, ctk.CTkImage] = {}
        self._search_request_id = 0
        self._preview_request_id = 0
        self._search_running = False

        # Filter state
        self._filter_type_var = ctk.StringVar(value="All")
        self._filter_package_var = ctk.StringVar(value="")
        self._filter_stock_var = ctk.StringVar(value="")
        self._filter_price_var = ctk.StringVar(value="")
        # Serializa chamadas HTTP à API JLC: se o usuário cancelar e buscar de
        # novo, o novo worker espera o anterior sair antes de mandar request.
        # Sem isso, múltiplas threads batem no WAF simultaneamente e travam.
        self._http_search_lock = threading.Lock()
        # Limita paralelismo das thumbnails de uma página (20 resultados) pra
        # não irritar o WAF da JLC com burst de 20 GETs.
        self._image_semaphore = threading.Semaphore(3)

        self._build_ui()
        self.after(POLL_MS, self._poll_queue)

    # ---------- UI ----------

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=2, minsize=320)
        self.grid_columnconfigure(1, weight=3, minsize=360)
        self.grid_rowconfigure(2, weight=1)

        search_bar = ctk.CTkFrame(self, fg_color="transparent")
        search_bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        search_bar.grid_columnconfigure(0, weight=1)

        self.query_var = ctk.StringVar()
        self.query_entry = ctk.CTkEntry(
            search_bar,
            textvariable=self.query_var,
            placeholder_text=t("MPN, LCSC ID ou palavra-chave (ex: LM358, C2040, 10k 0603)"),
        )
        self.query_entry.grid(row=0, column=0, sticky="ew")
        self.query_entry.bind("<Return>", lambda _e: self._start_search())
        bind_select_all(self.query_entry)

        self.search_btn = ctk.CTkButton(
            search_bar, text=t("Buscar"), width=110, command=self._start_search
        )
        self.search_btn.grid(row=0, column=1, sticky="e", padx=(8, 0))

        # Filter bar
        filter_bar = ctk.CTkFrame(self, fg_color="transparent")
        filter_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        ctk.CTkLabel(filter_bar, text=t("Tipo:"), text_color="gray70", width=32, anchor="w").pack(
            side="left", padx=(4, 2)
        )
        self._type_menu = ctk.CTkSegmentedButton(
            filter_bar,
            values=["All", "Basic", "Extended"],
            variable=self._filter_type_var,
            command=lambda _v: self._apply_filters(),
            width=180,
        )
        self._type_menu.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(filter_bar, text=t("Package:"), text_color="gray70", anchor="w").pack(
            side="left", padx=(0, 2)
        )
        pkg_entry = ctk.CTkEntry(
            filter_bar,
            textvariable=self._filter_package_var,
            placeholder_text="0402, SOP-8…",
            width=90,
        )
        pkg_entry.pack(side="left", padx=(0, 12))
        pkg_entry.bind("<Return>", lambda _e: self._apply_filters())
        pkg_entry.bind("<FocusOut>", lambda _e: self._apply_filters())

        ctk.CTkLabel(filter_bar, text=t("Estoque ≥"), text_color="gray70", anchor="w").pack(
            side="left", padx=(0, 2)
        )
        stk_entry = ctk.CTkEntry(
            filter_bar,
            textvariable=self._filter_stock_var,
            placeholder_text="0",
            width=60,
        )
        stk_entry.pack(side="left", padx=(0, 12))
        stk_entry.bind("<Return>", lambda _e: self._apply_filters())
        stk_entry.bind("<FocusOut>", lambda _e: self._apply_filters())

        ctk.CTkLabel(filter_bar, text=t("Preço ≤ $"), text_color="gray70", anchor="w").pack(
            side="left", padx=(0, 2)
        )
        price_entry = ctk.CTkEntry(
            filter_bar,
            textvariable=self._filter_price_var,
            placeholder_text="∞",
            width=60,
        )
        price_entry.pack(side="left", padx=(0, 4))
        price_entry.bind("<Return>", lambda _e: self._apply_filters())
        price_entry.bind("<FocusOut>", lambda _e: self._apply_filters())

        ctk.CTkButton(
            filter_bar,
            text=t("Limpar"),
            width=60,
            fg_color="transparent",
            border_width=1,
            command=self._clear_filters,
        ).pack(side="left", padx=(4, 0))

        # Resultados.
        left = ctk.CTkFrame(self)
        left.grid(row=2, column=0, sticky="nsew", padx=(0, 6))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)

        self.results_header = ctk.CTkLabel(
            left, text=t("Nenhuma busca feita"), anchor="w", text_color="gray60"
        )
        self.results_header.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))

        self.results_scroll = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.results_scroll.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        self.results_scroll.grid_columnconfigure(0, weight=1)
        # CTkScrollableFrame só liga roda do mouse na própria canvas; filhos
        # (rows + labels) engolem o evento. Forçamos propagação recursiva.
        self._bind_list_wheel(self.results_scroll)

        pager = ctk.CTkFrame(left, fg_color="transparent")
        pager.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        pager.grid_columnconfigure(1, weight=1)

        self.prev_btn = ctk.CTkButton(
            pager, text="←", width=40, command=self._prev_page, state="disabled"
        )
        self.prev_btn.grid(row=0, column=0, sticky="w")

        self.page_label = ctk.CTkLabel(pager, text="", anchor="center")
        self.page_label.grid(row=0, column=1, sticky="ew")

        self.next_btn = ctk.CTkButton(
            pager, text="→", width=40, command=self._next_page, state="disabled"
        )
        self.next_btn.grid(row=0, column=2, sticky="e")

        # Detalhe.
        right = ctk.CTkFrame(self)
        right.grid(row=2, column=1, sticky="nsew", padx=(6, 0))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)

        self.detail = DetailPanel(
            right,
            on_download=self._trigger_download,
            on_preview=self._start_preview,
        )
        self.detail.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

    # ---------- Filtros ----------

    def _apply_filters(self) -> None:
        if not self._raw_items:
            return

        lib_type = self._filter_type_var.get()
        pkg = self._filter_package_var.get().strip().lower()
        stock_text = self._filter_stock_var.get().strip()
        price_text = self._filter_price_var.get().strip()

        try:
            min_stock = int(stock_text) if stock_text else 0
        except ValueError:
            min_stock = 0

        try:
            max_price = float(price_text) if price_text else None
        except ValueError:
            max_price = None

        filtered: list[Component] = []
        for comp in self._raw_items:
            if lib_type == "Basic" and not comp.is_basic:
                continue
            if lib_type == "Extended" and comp.is_basic:
                continue
            if pkg and pkg not in comp.package.lower():
                continue
            if comp.stock < min_stock:
                continue
            if max_price is not None:
                unit = comp.unit_price_for(1)
                if unit is None or unit > max_price:
                    continue
            filtered.append(comp)

        self._current_components = filtered
        self._clear_results()
        for idx, comp in enumerate(filtered):
            self._build_result_row(idx, comp)
        for comp in filtered:
            self._prefetch_row_image(comp)

        shown = len(filtered)
        total = len(self._raw_items)
        if shown == total:
            self.results_header.configure(
                text=t("{total} resultados — mostrando {shown}", total=total, shown=shown)
            )
        else:
            self.results_header.configure(
                text=t(
                    "{total} resultados — mostrando {shown}",
                    total=total,
                    shown=shown,
                )
                + f" ({t('filtrado')})"
            )

        if filtered:
            self._select(filtered[0])
        else:
            self.detail.reset(t("Nenhum componente passa pelos filtros atuais."))

    def _clear_filters(self) -> None:
        self._filter_type_var.set("All")
        self._filter_package_var.set("")
        self._filter_stock_var.set("")
        self._filter_price_var.set("")
        self._apply_filters()

    # ---------- Ações ----------

    def _start_search(self, page: int = 1, query_override: str | None = None) -> None:
        if self._search_running and query_override is None:
            # Clique no botão enquanto está rodando = cancelar a busca em voo.
            self._cancel_search()
            return

        query = (query_override if query_override is not None else self.query_var.get()).strip()
        if not query:
            self.query_entry.focus_set()
            return
        if LCSC_ID_RE.match(query) and page != 1:
            self.on_log(f'[busca] "{query}" é LCSC ID exato; forçando página 1')
            page = 1

        self._search_request_id += 1
        req_id = self._search_request_id
        # Invalida preview pendente — imagens são dedupadas por URL/seleção.
        self._preview_request_id += 1

        self.on_log(f'[busca] pesquisando "{query}" página {page} id={req_id}')
        self._current_query = query
        self._current_page = page
        self._selected = None
        self._set_searching(True)
        self._clear_results()
        self.detail.reset(t("Selecione um resultado para ver símbolo + footprint."))
        self.results_header.configure(text=t("Buscando “{query}”...", query=query))

        threading.Thread(
            target=self._worker_search, args=(req_id, query, page), daemon=True
        ).start()

    def _cancel_search(self) -> None:
        # Invalida o req_id em voo; o callback do worker será descartado.
        self._search_request_id += 1
        self._preview_request_id += 1
        self._set_searching(False)
        self.results_header.configure(
            text=(
                t("Busca cancelada: “{query}”", query=self._current_query)
                if self._current_query
                else t("Busca cancelada")
            )
        )
        self.on_log("[busca] cancelada pelo usuário")

    def _worker_search(self, req_id: int, query: str, page: int) -> None:
        with self._http_search_lock:
            if req_id != self._search_request_id:
                # Usuário cancelou / disparou nova busca enquanto esperávamos
                # o lock. Não bate no servidor.
                self._msg_queue.put(
                    ("log", f'[busca] id={req_id} descartado antes do HTTP (nova busca em curso)')
                )
                return
            try:
                result = self.client.search(query, page=page, page_size=PAGE_SIZE)
                self._msg_queue.put(("ok", (req_id, result)))
            except JlcApiError as exc:
                self._msg_queue.put(("err", (req_id, str(exc))))
            except Exception as exc:  # pragma: no cover — defesa extra
                log.exception("Erro inesperado na busca")
                self._msg_queue.put(("err", (req_id, f"Erro inesperado: {exc}")))

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self._msg_queue.get_nowait()
                if kind == "ok":
                    req_id, result = payload  # type: ignore[misc]
                    self._render_results(int(req_id), result)  # type: ignore[arg-type]
                elif kind == "err":
                    req_id, message = payload  # type: ignore[misc]
                    self._render_error(int(req_id), str(message))
                elif kind == "preview_ok":
                    req_id, lcsc_id, artifacts = payload  # type: ignore[misc]
                    self._render_preview(int(req_id), str(lcsc_id), artifacts)
                elif kind == "preview_err":
                    req_id, lcsc_id, message = payload  # type: ignore[misc]
                    self._render_preview_error(int(req_id), str(lcsc_id), str(message))
                elif kind == "image_ok":
                    lcsc_id, url, data = payload  # type: ignore[misc]
                    self._pending_image_urls.discard(str(url))
                    self._image_bytes_cache[str(url)] = bytes(data)  # type: ignore[arg-type]
                    # Renderiza em todas as rows da página atual que usem esta URL.
                    url_str = str(url)
                    for cur in self._current_components:
                        if cur.image_url == url_str:
                            self._render_row_thumbnail(cur.lcsc_id, bytes(data))  # type: ignore[arg-type]
                elif kind == "image_err":
                    lcsc_id, url = payload  # type: ignore[misc]
                    self._pending_image_urls.discard(str(url))
                    url_str = str(url)
                    for cur in self._current_components:
                        if cur.image_url == url_str:
                            self._render_row_thumbnail_error(cur.lcsc_id)
                elif kind == "log":
                    self.on_log(str(payload))
        except queue.Empty:
            pass
        self.after(POLL_MS, self._poll_queue)

    def _render_results(self, req_id: int, result: SearchResult) -> None:
        if req_id != self._search_request_id:
            return
        self._set_searching(False)
        self._raw_items = result.items
        self._total_pages = result.total_pages
        self._results_query = self._current_query

        if not result.items:
            self.results_header.configure(
                text=t("Nenhum resultado para “{query}”", query=self._current_query)
            )
            self.on_log(f'[busca] nenhum resultado para "{self._current_query}"')
        elif result.fallback_reason:
            self.results_header.configure(
                text=t(
                    "Resultado local para {lcsc_id} — API indisponível",
                    lcsc_id=result.items[0].lcsc_id,
                )
            )
            self.on_log(
                f"[busca] fallback local para {result.items[0].lcsc_id}: "
                f"{result.fallback_reason}"
            )
        else:
            self.on_log(
                f'[busca] {result.total} resultados, exibindo {len(result.items)} na página {result.page}'
            )

        self.page_label.configure(
            text=(
                t("Página {page} de {total}", page=result.page, total=result.total_pages)
                if result.items
                else ""
            )
        )
        self.prev_btn.configure(state="normal" if result.page > 1 else "disabled")
        self.next_btn.configure(
            state="normal" if result.page < result.total_pages else "disabled"
        )

        self._apply_filters()

    def _render_error(self, req_id: int, message: str) -> None:
        if req_id != self._search_request_id:
            return
        self._set_searching(False)
        self.results_header.configure(text=t("Erro: {message}", message=message))
        self.on_log(f"[busca] {message}")
        self._clear_results()
        self.detail.reset(t("Busca falhou. Ajuste o termo e tente novamente."))

    def _build_result_row(self, idx: int, comp: Component) -> None:
        row = ctk.CTkFrame(self.results_scroll, border_width=1, border_color="gray30")
        row.grid(row=idx, column=0, sticky="ew", pady=3, padx=2)
        row.grid_columnconfigure(1, weight=1)
        row.bind("<Button-1>", lambda _e, c=comp: self._select(c))

        def _fwd(event, c=comp):  # passa o clique dos filhos ao row
            self._select(c)

        thumb = ctk.CTkLabel(
            row,
            text="—" if comp.image_url else "",
            width=56,
            height=56,
            fg_color="#1a1a1a",
            text_color="gray50",
            corner_radius=6,
        )
        thumb.grid(row=0, column=0, rowspan=3, padx=(8, 8), pady=6, sticky="n")
        thumb.bind("<Button-1>", _fwd)
        self._row_image_labels[comp.lcsc_id] = thumb

        top = ctk.CTkFrame(row, fg_color="transparent")
        top.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=(6, 0))
        top.grid_columnconfigure(1, weight=1)
        top.bind("<Button-1>", _fwd)

        mpn_lbl = ctk.CTkLabel(
            top,
            text=comp.mpn or comp.lcsc_id,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        mpn_lbl.grid(row=0, column=0, sticky="w")
        mpn_lbl.bind("<Button-1>", _fwd)

        badge_text = (
            t(" Basic ") if comp.is_basic
            else t(" Extended ") if comp.library_type
            else t(" LCSC ID ")
        )
        badge = ctk.CTkLabel(
            top,
            text=badge_text,
            fg_color="#2ecc71" if comp.is_basic else "#95a5a6",
            text_color="black",
            corner_radius=8,
            font=ctk.CTkFont(size=9, weight="bold"),
        )
        badge.grid(row=0, column=2, sticky="e", padx=(8, 0))
        badge.bind("<Button-1>", _fwd)

        sub = ctk.CTkLabel(
            row,
            text=f"{comp.lcsc_id}  •  {comp.manufacturer}  •  {comp.package}",
            font=ctk.CTkFont(size=11),
            text_color="gray70",
            anchor="w",
        )
        sub.grid(row=1, column=1, sticky="w", padx=(0, 8))
        sub.bind("<Button-1>", _fwd)

        unit = comp.unit_price_for(1)
        price_str = f"${unit:.4f}" if unit is not None else "—"
        foot = ctk.CTkLabel(
            row,
            text=t(
                "estoque: {stock:,}   •   preço (1): {price}",
                stock=comp.stock,
                price=price_str,
            ),
            font=ctk.CTkFont(size=11),
            text_color="gray60",
            anchor="w",
        )
        foot.grid(row=2, column=1, sticky="w", padx=(0, 8), pady=(0, 6))
        foot.bind("<Button-1>", _fwd)

        # Propaga roda do mouse (row + todos os filhos) para a scrollbar.
        self._bind_list_wheel(row)

    def _select(self, comp: Component) -> None:
        if self._selected is not None and self._selected.lcsc_id == comp.lcsc_id:
            self.on_log(f"[busca] seleção repetida ignorada: {comp.lcsc_id}")
            return
        self._selected = comp
        # Invalida preview pendente do item anterior; imagens já são descartadas
        # automaticamente pelo check de lcsc_id selecionado no render.
        self._preview_request_id += 1
        self.on_log(
            "[busca] selecionado "
            f"{comp.lcsc_id} | {comp.mpn or '-'} | pacote={comp.package or '-'} | "
            f"estoque={comp.stock} | imagem={'sim' if comp.image_url else 'não'}"
        )
        self.detail.show(comp)
        self._start_preview(comp)

    def _prev_page(self) -> None:
        if self._search_running:
            self.on_log("[busca] paginação ignorada: busca em andamento")
            return
        if self.query_var.get().strip() != self._results_query:
            self.on_log("[busca] paginação ignorada: termo do campo mudou desde o último resultado")
            return
        if self._current_page > 1:
            self._start_search(page=self._current_page - 1, query_override=self._results_query)

    def _next_page(self) -> None:
        if self._search_running:
            self.on_log("[busca] paginação ignorada: busca em andamento")
            return
        if self.query_var.get().strip() != self._results_query:
            self.on_log("[busca] paginação ignorada: termo do campo mudou desde o último resultado")
            return
        if LCSC_ID_RE.match(self._results_query):
            self.on_log("[busca] paginação ignorada: LCSC ID exato não tem página 2")
            return
        if self._current_page < self._total_pages:
            self._start_search(page=self._current_page + 1, query_override=self._results_query)

    def _trigger_download(self, comp: Component) -> None:
        self.on_log(f"[busca] enviar {comp.lcsc_id} para Download direto")
        self.on_download(comp.lcsc_id)

    def _start_preview(self, comp: Component) -> None:
        self._preview_request_id += 1
        req_id = self._preview_request_id
        self.on_log(f"[preview {comp.lcsc_id}] solicitado na aba Buscar id={req_id}")
        self.detail.set_preview_running(True)
        threading.Thread(
            target=self._worker_preview, args=(req_id, comp.lcsc_id), daemon=True
        ).start()

    def _worker_preview(self, req_id: int, lcsc_id: str) -> None:
        preview_dir = _preview_dir(lcsc_id)
        try:
            preview_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._msg_queue.put(("preview_err", (req_id, lcsc_id, f"Falha ao criar cache: {exc}")))
            return

        existing = find_kicad_artifacts(preview_dir, lcsc_id=lcsc_id)
        self._msg_queue.put(
            (
                "log",
                f"[preview {lcsc_id}] cache {preview_dir} "
                f"symbol={existing.symbol or '-'} footprint={existing.footprint or '-'}",
            )
        )
        if existing.has_all:
            self._msg_queue.put(("preview_ok", (req_id, lcsc_id, existing)))
            return

        def cb(line: str) -> None:
            self._msg_queue.put(("log", f"[preview {lcsc_id}] {line}"))

        try:
            rc = self.runner.download(lcsc_id, preview_dir, log_cb=cb)
        except EasyEdaError as exc:
            self._msg_queue.put(("preview_err", (req_id, lcsc_id, str(exc))))
            return
        except Exception as exc:  # pragma: no cover — defesa extra
            log.exception("Erro inesperado no preview")
            self._msg_queue.put(("preview_err", (req_id, lcsc_id, f"Erro inesperado: {exc}")))
            return

        if rc != 0:
            self._msg_queue.put(("preview_err", (req_id, lcsc_id, f"easyeda2kicad retornou {rc}")))
            return

        artifacts = find_kicad_artifacts(preview_dir, lcsc_id=lcsc_id)
        self._msg_queue.put(
            (
                "log",
                f"[preview {lcsc_id}] após download "
                f"symbol={artifacts.symbol or '-'} footprint={artifacts.footprint or '-'}",
            )
        )
        self._msg_queue.put(("preview_ok", (req_id, lcsc_id, artifacts)))

    def _render_preview(self, req_id: int, lcsc_id: str, artifacts) -> None:
        if (
            req_id != self._preview_request_id
            or self._selected is None
            or self._selected.lcsc_id != lcsc_id
        ):
            return
        self.detail.set_preview_running(False)
        warnings = self.detail.show_preview(artifacts, lcsc_id=lcsc_id)
        for warning in warnings:
            self.on_log(f"[preview {lcsc_id}] {warning}")

    def _render_preview_error(self, req_id: int, lcsc_id: str, message: str) -> None:
        if (
            req_id != self._preview_request_id
            or self._selected is None
            or self._selected.lcsc_id != lcsc_id
        ):
            return
        self.detail.set_preview_running(False)
        self.detail.clear_preview(f"Preview falhou: {message}")
        self.on_log(f"[preview {lcsc_id}] {message}")

    def _prefetch_row_image(self, comp: Component) -> None:
        if not comp.image_url:
            return
        cached = self._image_bytes_cache.get(comp.image_url)
        if cached is not None:
            self._render_row_thumbnail(comp.lcsc_id, cached)
            return
        if comp.image_url in self._pending_image_urls:
            return
        self._pending_image_urls.add(comp.image_url)
        threading.Thread(
            target=self._worker_image, args=(comp.lcsc_id, comp.image_url), daemon=True
        ).start()

    def _worker_image(self, lcsc_id: str, url: str) -> None:
        with self._image_semaphore:
            try:
                resp = requests.get(url, timeout=12, headers=DEFAULT_HEADERS)
                resp.raise_for_status()
            except Exception as exc:  # inclui SSLError, ImportError de plugins etc.
                self._msg_queue.put(
                    ("log", f"[imagem {lcsc_id}] falhou: {type(exc).__name__}: {exc}")
                )
                self._msg_queue.put(("image_err", (lcsc_id, url)))
                return
            self._msg_queue.put(("image_ok", (lcsc_id, url, resp.content)))

    def _render_row_thumbnail(self, lcsc_id: str, data: bytes) -> None:
        label = self._row_image_labels.get(lcsc_id)
        if label is None:
            return  # página mudou ou row foi removida
        try:
            image = Image.open(BytesIO(data))
            image = image.convert("RGBA")
            image.thumbnail((56, 56), Image.Resampling.LANCZOS)
            ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=image.size)
        except Exception as exc:  # plugin PIL ausente em build frozen etc.
            label.configure(text="?", image="")
            self.on_log(f"[imagem {lcsc_id}] render falhou: {type(exc).__name__}: {exc}")
            return
        self._row_image_refs[lcsc_id] = ctk_image
        label.configure(image=ctk_image, text="")

    def _render_row_thumbnail_error(self, lcsc_id: str) -> None:
        label = self._row_image_labels.get(lcsc_id)
        if label is None:
            return
        label.configure(text="x", image="")

    def _bind_list_wheel(self, widget) -> None:
        widget.bind("<MouseWheel>", self._list_wheel, add="+")
        widget.bind("<Button-4>", self._list_wheel, add="+")
        widget.bind("<Button-5>", self._list_wheel, add="+")
        for child in widget.winfo_children():
            self._bind_list_wheel(child)

    def _list_wheel(self, event) -> str:
        parent_canvas = self.results_scroll._parent_canvas  # type: ignore[attr-defined]
        if event.num == 4:
            parent_canvas.yview_scroll(-2, "units")
        elif event.num == 5:
            parent_canvas.yview_scroll(2, "units")
        else:
            parent_canvas.yview_scroll(int(-event.delta / 40) or (-1 if event.delta > 0 else 1), "units")
        return "break"

    def _set_searching(self, running: bool) -> None:
        self._search_running = running
        self.search_btn.configure(
            state="normal", text="Cancelar" if running else "Buscar"
        )
        self.query_entry.configure(state="normal")
        if running:
            self.prev_btn.configure(state="disabled")
            self.next_btn.configure(state="disabled")

    def _clear_results(self) -> None:
        for child in self.results_scroll.winfo_children():
            child.destroy()
        self._row_image_labels.clear()
        self._row_image_refs.clear()
        self.page_label.configure(text="")
        self.prev_btn.configure(state="disabled")
        self.next_btn.configure(state="disabled")


class DetailPanel(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_download: Callable[[Component], None],
        on_preview: Callable[[Component], None],
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.on_download = on_download
        self.on_preview = on_preview
        self._component: Component | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=2)
        self.grid_rowconfigure(3, weight=3)

        self.title_lbl = ctk.CTkLabel(
            self,
            text=t("Selecione um resultado"),
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w",
            justify="left",
        )
        self.title_lbl.grid(row=0, column=0, sticky="ew", pady=(0, 2))

        self.sub_lbl = ctk.CTkLabel(
            self, text="", text_color="gray60", anchor="w", justify="left"
        )
        self.sub_lbl.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=2, column=0, sticky="nsew")
        self.scroll.grid_columnconfigure(0, weight=1)

        self.preview_panel = PreviewPanel(self)
        self.preview_panel.grid(row=3, column=0, sticky="nsew", pady=(8, 0))

        self.action_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.action_bar.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        self.action_bar.grid_columnconfigure((0, 1), weight=1)

        self.preview_btn = ctk.CTkButton(
            self.action_bar,
            text=t("Pré-visualizar"),
            height=38,
            command=self._click_preview,
            state="disabled",
        )
        self.preview_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.download_btn = ctk.CTkButton(
            self.action_bar,
            text=t("⬇  Baixar símbolo + footprint"),
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._click_download,
            state="disabled",
        )
        self.download_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))

    def show(self, comp: Component) -> None:
        self._component = comp

        self.title_lbl.configure(text=comp.mpn or comp.lcsc_id)
        parts = [comp.lcsc_id]
        if comp.manufacturer:
            parts.append(comp.manufacturer)
        if comp.package:
            parts.append(comp.package)
        if comp.category:
            parts.append(comp.category)
        self.sub_lbl.configure(text="  •  ".join(parts))

        self.download_btn.configure(state="normal")
        self.preview_btn.configure(state="normal", text=t("Pré-visualizar"))
        self.preview_panel.clear(t("Preview: carregando símbolo e footprint..."))

        for child in self.scroll.winfo_children():
            child.destroy()

        chip_row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        chip_row.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        lib_label = (
            t("Basic") if comp.is_basic
            else t("Extended") if comp.library_type
            else t("LCSC ID")
        )
        self._chip(
            chip_row,
            lib_label,
            fg="#2ecc71" if comp.is_basic else "#7f8c8d",
            col=0,
        )
        self._chip(chip_row, t("Estoque: {stock:,}", stock=comp.stock), fg="#3498db", col=1)
        unit1 = comp.unit_price_for(1)
        if unit1 is not None:
            self._chip(chip_row, t("${unit:.4f} / un", unit=unit1), fg="#f39c12", col=2)
        self._chip(chip_row, t("Mín: {qty}", qty=comp.min_purchase), fg="#7f8c8d", col=3)

        if comp.prices:
            ctk.CTkLabel(
                self.scroll,
                text=t("Preço por quantidade"),
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
            ).grid(row=1, column=0, sticky="w", pady=(6, 2))

            tiers = ctk.CTkFrame(self.scroll, fg_color="transparent")
            tiers.grid(row=2, column=0, sticky="ew", pady=(0, 10))
            tiers.grid_columnconfigure(0, weight=1)
            tiers.grid_columnconfigure(1, weight=1)

            for i, tier in enumerate(comp.prices):
                qty_str = (
                    f"{tier.qty_min}+"
                    if tier.qty_max is None
                    else f"{tier.qty_min} – {tier.qty_max}"
                )
                ctk.CTkLabel(tiers, text=qty_str, anchor="w").grid(
                    row=i, column=0, sticky="w", padx=(4, 0)
                )
                ctk.CTkLabel(tiers, text=f"${tier.unit_usd:.4f}", anchor="e").grid(
                    row=i, column=1, sticky="e", padx=(0, 4)
                )

        if comp.datasheet_url:
            ctk.CTkButton(
                self.scroll,
                text=t("Abrir datasheet"),
                fg_color="transparent",
                border_width=1,
                command=lambda u=comp.datasheet_url: _open_url(u),
            ).grid(row=3, column=0, sticky="ew", pady=(0, 10))

        if comp.description:
            ctk.CTkLabel(
                self.scroll,
                text=t("Descrição"),
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
            ).grid(row=4, column=0, sticky="w")
            desc = ctk.CTkLabel(
                self.scroll,
                text=comp.description,
                wraplength=420,
                justify="left",
                anchor="w",
                text_color="gray70",
            )
            desc.grid(row=5, column=0, sticky="ew", pady=(0, 10))

        if comp.attributes:
            ctk.CTkLabel(
                self.scroll,
                text=t("Especificações"),
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
            ).grid(row=6, column=0, sticky="w")
            attrs_frame = ctk.CTkFrame(self.scroll, fg_color="transparent")
            attrs_frame.grid(row=7, column=0, sticky="ew", pady=(2, 10))
            attrs_frame.grid_columnconfigure(1, weight=1)
            for i, (name, value) in enumerate(comp.attributes[:15]):
                ctk.CTkLabel(
                    attrs_frame, text=name, anchor="w", text_color="gray60",
                    font=ctk.CTkFont(size=11),
                ).grid(row=i, column=0, sticky="w", padx=(0, 10))
                ctk.CTkLabel(
                    attrs_frame, text=value, anchor="w", font=ctk.CTkFont(size=11),
                ).grid(row=i, column=1, sticky="w")

    def _chip(self, parent, text: str, fg: str, col: int) -> None:
        ctk.CTkLabel(
            parent, text=f" {text} ",
            fg_color=fg, text_color="black",
            corner_radius=10,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).grid(row=0, column=col, padx=(0, 6), sticky="w")

    def _click_download(self) -> None:
        if self._component:
            self.on_download(self._component)

    def _click_preview(self) -> None:
        if self._component:
            self.on_preview(self._component)

    def set_preview_running(self, running: bool) -> None:
        self.preview_btn.configure(
            state="disabled" if running else "normal",
            text=t("Carregando...") if running else t("Pré-visualizar"),
        )
        if running:
            self.preview_panel.clear(t("Preview carregando arquivos KiCad..."))

    def show_preview(self, artifacts, lcsc_id: str | None = None) -> list[str]:
        return self.preview_panel.show_artifacts(artifacts, lcsc_id=lcsc_id)

    def clear_preview(self, message: str) -> None:
        self.preview_panel.clear(message)

    def reset(self, message: str | None = None) -> None:
        self._component = None
        self.title_lbl.configure(text=message or t("Selecione um resultado"))
        self.sub_lbl.configure(text="")
        self.download_btn.configure(state="disabled")
        self.preview_btn.configure(state="disabled", text=t("Pré-visualizar"))
        self.preview_panel.clear(t("Preview: selecione um componente."))
        for child in self.scroll.winfo_children():
            child.destroy()


def _preview_dir(lcsc_id: str) -> Path:
    safe_id = "".join(ch for ch in lcsc_id.upper() if ch.isalnum() or ch in {"_", "-"})
    return cache_dir() / "previews" / safe_id


def _open_url(url: str) -> None:
    import webbrowser

    try:
        webbrowser.open(url)
    except Exception:
        pass
