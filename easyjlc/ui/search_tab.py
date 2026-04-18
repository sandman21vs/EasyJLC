"""Aba Buscar — pesquisa JLCPCB com lista de resultados e painel de detalhe."""

from __future__ import annotations

import logging
import queue
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
from easyjlc.ui.bindings import bind_select_all
from easyjlc.ui.preview_panel import PreviewPanel

log = logging.getLogger("easyjlc.search_tab")

POLL_MS = 80
PAGE_SIZE = 20


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
        self._current_components: list[Component] = []
        self._selected: Component | None = None
        self._worker: threading.Thread | None = None
        self._preview_worker: threading.Thread | None = None
        self._image_worker: threading.Thread | None = None
        self._current_page = 1
        self._total_pages = 1
        self._current_query = ""
        self._image_token = 0

        self._build_ui()
        self.after(POLL_MS, self._poll_queue)

    # ---------- UI ----------

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=2, minsize=320)
        self.grid_columnconfigure(1, weight=3, minsize=360)
        self.grid_rowconfigure(1, weight=1)

        search_bar = ctk.CTkFrame(self, fg_color="transparent")
        search_bar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        search_bar.grid_columnconfigure(0, weight=1)

        self.query_var = ctk.StringVar()
        self.query_entry = ctk.CTkEntry(
            search_bar,
            textvariable=self.query_var,
            placeholder_text="MPN, LCSC ID ou palavra-chave (ex: LM358, C2040, 10k 0603)",
        )
        self.query_entry.grid(row=0, column=0, sticky="ew")
        self.query_entry.bind("<Return>", lambda _e: self._start_search())
        bind_select_all(self.query_entry)

        self.search_btn = ctk.CTkButton(
            search_bar, text="Buscar", width=110, command=self._start_search
        )
        self.search_btn.grid(row=0, column=1, sticky="e", padx=(8, 0))

        # Resultados.
        left = ctk.CTkFrame(self)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 6))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)

        self.results_header = ctk.CTkLabel(
            left, text="Nenhuma busca feita", anchor="w", text_color="gray60"
        )
        self.results_header.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))

        self.results_scroll = ctk.CTkScrollableFrame(left, fg_color="transparent")
        self.results_scroll.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        self.results_scroll.grid_columnconfigure(0, weight=1)

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
        right.grid(row=1, column=1, sticky="nsew", padx=(6, 0))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)

        self.detail = DetailPanel(
            right,
            on_download=self._trigger_download,
            on_preview=self._start_preview,
        )
        self.detail.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

    # ---------- Ações ----------

    def _start_search(self, page: int = 1) -> None:
        if self._worker and self._worker.is_alive():
            return

        query = self.query_var.get().strip()
        if not query:
            self.query_entry.focus_set()
            return

        self.on_log(f'[busca] pesquisando "{query}" página {page}')
        self._current_query = query
        self._current_page = page
        self._set_searching(True)
        self.results_header.configure(text=f"Buscando “{query}”...")

        self._worker = threading.Thread(
            target=self._worker_search, args=(query, page), daemon=True
        )
        self._worker.start()

    def _worker_search(self, query: str, page: int) -> None:
        try:
            result = self.client.search(query, page=page, page_size=PAGE_SIZE)
            self._msg_queue.put(("ok", result))
        except JlcApiError as exc:
            self._msg_queue.put(("err", str(exc)))
        except Exception as exc:  # pragma: no cover — defesa extra
            log.exception("Erro inesperado na busca")
            self._msg_queue.put(("err", f"Erro inesperado: {exc}"))

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self._msg_queue.get_nowait()
                if kind == "ok":
                    self._render_results(payload)  # type: ignore[arg-type]
                elif kind == "err":
                    self._render_error(str(payload))
                elif kind == "preview_ok":
                    lcsc_id, artifacts = payload  # type: ignore[misc]
                    self._render_preview(str(lcsc_id), artifacts)
                elif kind == "preview_err":
                    lcsc_id, message = payload  # type: ignore[misc]
                    self._render_preview_error(str(lcsc_id), str(message))
                elif kind == "image_ok":
                    token, lcsc_id, data = payload  # type: ignore[misc]
                    self._render_image(int(token), str(lcsc_id), data)  # type: ignore[arg-type]
                elif kind == "image_err":
                    token, lcsc_id = payload  # type: ignore[misc]
                    self._render_image_error(int(token), str(lcsc_id))
        except queue.Empty:
            pass
        self.after(POLL_MS, self._poll_queue)

    def _render_results(self, result: SearchResult) -> None:
        self._set_searching(False)
        self._current_components = result.items
        self._total_pages = result.total_pages

        if not result.items:
            self.results_header.configure(
                text=f"Nenhum resultado para “{self._current_query}”"
            )
            self.on_log(f'[busca] nenhum resultado para "{self._current_query}"')
        else:
            self.results_header.configure(
                text=f"{result.total} resultados — mostrando {len(result.items)}"
            )
            self.on_log(
                f'[busca] {result.total} resultados, exibindo {len(result.items)} na página {result.page}'
            )

        for child in self.results_scroll.winfo_children():
            child.destroy()

        for idx, comp in enumerate(result.items):
            self._build_result_row(idx, comp)

        self.page_label.configure(
            text=f"Página {result.page} de {result.total_pages}" if result.items else ""
        )
        self.prev_btn.configure(state="normal" if result.page > 1 else "disabled")
        self.next_btn.configure(
            state="normal" if result.page < result.total_pages else "disabled"
        )

        if result.items:
            self._select(result.items[0])

    def _render_error(self, message: str) -> None:
        self._set_searching(False)
        self.results_header.configure(text=f"Erro: {message}")
        self.on_log(f"[busca] {message}")
        for child in self.results_scroll.winfo_children():
            child.destroy()

    def _build_result_row(self, idx: int, comp: Component) -> None:
        row = ctk.CTkFrame(self.results_scroll, border_width=1, border_color="gray30")
        row.grid(row=idx, column=0, sticky="ew", pady=3, padx=2)
        row.grid_columnconfigure(0, weight=1)
        row.bind("<Button-1>", lambda _e, c=comp: self._select(c))

        def _fwd(event, c=comp):  # passa o clique dos filhos ao row
            self._select(c)

        top = ctk.CTkFrame(row, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=(6, 0))
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

        badge = ctk.CTkLabel(
            top,
            text=" Basic " if comp.is_basic else " Extended ",
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
        sub.grid(row=1, column=0, sticky="w", padx=8)
        sub.bind("<Button-1>", _fwd)

        unit = comp.unit_price_for(1)
        price_str = f"${unit:.4f}" if unit is not None else "—"
        foot = ctk.CTkLabel(
            row,
            text=f"estoque: {comp.stock:,}   •   preço (1): {price_str}",
            font=ctk.CTkFont(size=11),
            text_color="gray60",
            anchor="w",
        )
        foot.grid(row=2, column=0, sticky="w", padx=8, pady=(0, 6))
        foot.bind("<Button-1>", _fwd)

    def _select(self, comp: Component) -> None:
        self._selected = comp
        self.on_log(
            "[busca] selecionado "
            f"{comp.lcsc_id} | {comp.mpn or '-'} | pacote={comp.package or '-'} | "
            f"estoque={comp.stock} | imagem={'sim' if comp.image_url else 'não'}"
        )
        self.detail.show(comp)
        self._start_image_load(comp)

    def _prev_page(self) -> None:
        if self._current_page > 1:
            self._start_search(page=self._current_page - 1)

    def _next_page(self) -> None:
        if self._current_page < self._total_pages:
            self._start_search(page=self._current_page + 1)

    def _trigger_download(self, comp: Component) -> None:
        self.on_log(f"[busca] enviar {comp.lcsc_id} para Download direto")
        self.on_download(comp.lcsc_id)

    def _start_preview(self, comp: Component) -> None:
        if self._preview_worker and self._preview_worker.is_alive():
            self.on_log("Já há um preview em andamento.")
            return

        self.on_log(f"[preview {comp.lcsc_id}] solicitado na aba Buscar")
        self.detail.set_preview_running(True)
        self._preview_worker = threading.Thread(
            target=self._worker_preview, args=(comp.lcsc_id,), daemon=True
        )
        self._preview_worker.start()

    def _worker_preview(self, lcsc_id: str) -> None:
        preview_dir = _preview_dir(lcsc_id)
        try:
            preview_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self._msg_queue.put(("preview_err", (lcsc_id, f"Falha ao criar cache: {exc}")))
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
            self._msg_queue.put(("preview_ok", (lcsc_id, existing)))
            return

        def cb(line: str) -> None:
            self._msg_queue.put(("log", f"[preview {lcsc_id}] {line}"))

        try:
            rc = self.runner.download(lcsc_id, preview_dir, log_cb=cb)
        except EasyEdaError as exc:
            self._msg_queue.put(("preview_err", (lcsc_id, str(exc))))
            return
        except Exception as exc:  # pragma: no cover — defesa extra
            log.exception("Erro inesperado no preview")
            self._msg_queue.put(("preview_err", (lcsc_id, f"Erro inesperado: {exc}")))
            return

        if rc != 0:
            self._msg_queue.put(("preview_err", (lcsc_id, f"easyeda2kicad retornou {rc}")))
            return

        artifacts = find_kicad_artifacts(preview_dir, lcsc_id=lcsc_id)
        self._msg_queue.put(
            (
                "log",
                f"[preview {lcsc_id}] após download "
                f"symbol={artifacts.symbol or '-'} footprint={artifacts.footprint or '-'}",
            )
        )
        self._msg_queue.put(("preview_ok", (lcsc_id, artifacts)))

    def _render_preview(self, lcsc_id: str, artifacts) -> None:
        if self._selected is None or self._selected.lcsc_id != lcsc_id:
            return
        self.detail.set_preview_running(False)
        warnings = self.detail.show_preview(artifacts)
        for warning in warnings:
            self.on_log(f"[preview {lcsc_id}] {warning}")

    def _render_preview_error(self, lcsc_id: str, message: str) -> None:
        if self._selected is None or self._selected.lcsc_id != lcsc_id:
            return
        self.detail.set_preview_running(False)
        self.detail.clear_preview(f"Preview falhou: {message}")
        self.on_log(f"[preview {lcsc_id}] {message}")

    def _start_image_load(self, comp: Component) -> None:
        self._image_token += 1
        token = self._image_token
        if not comp.image_url:
            self.on_log(f"[imagem {comp.lcsc_id}] sem image_access_id na resposta JLC")
            self.detail.clear_image("Imagem JLC indisponível.")
            return

        self.on_log(f"[imagem {comp.lcsc_id}] carregando {comp.image_url}")
        self.detail.set_image_loading()
        self._image_worker = threading.Thread(
            target=self._worker_image, args=(token, comp.lcsc_id, comp.image_url), daemon=True
        )
        self._image_worker.start()

    def _worker_image(self, token: int, lcsc_id: str, url: str) -> None:
        try:
            resp = requests.get(url, timeout=12, headers=DEFAULT_HEADERS)
            resp.raise_for_status()
        except requests.RequestException as exc:
            self._msg_queue.put(("log", f"[imagem {lcsc_id}] falhou: {exc}"))
            self._msg_queue.put(("image_err", (token, lcsc_id)))
            return
        self._msg_queue.put(
            (
                "log",
                f"[imagem {lcsc_id}] HTTP {resp.status_code}, {len(resp.content)} bytes, "
                f"content-type={resp.headers.get('content-type', '-')}",
            )
        )
        self._msg_queue.put(("image_ok", (token, lcsc_id, resp.content)))

    def _render_image(self, token: int, lcsc_id: str, data: bytes) -> None:
        if (
            token != self._image_token
            or self._selected is None
            or self._selected.lcsc_id != lcsc_id
        ):
            return
        try:
            image = Image.open(BytesIO(data))
        except OSError:
            self.on_log(f"[imagem {lcsc_id}] PIL não reconheceu os bytes retornados")
            self.detail.clear_image("Imagem JLC inválida.")
            return
        self.on_log(f"[imagem {lcsc_id}] exibindo {image.format or '-'} {image.size[0]}x{image.size[1]}")
        self.detail.show_image(image)

    def _render_image_error(self, token: int, lcsc_id: str) -> None:
        if (
            token != self._image_token
            or self._selected is None
            or self._selected.lcsc_id != lcsc_id
        ):
            return
        self.detail.clear_image("Imagem JLC não carregou.")

    def _set_searching(self, running: bool) -> None:
        state = "disabled" if running else "normal"
        self.search_btn.configure(
            state=state, text="Buscando..." if running else "Buscar"
        )
        self.query_entry.configure(state=state)


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
        self.grid_rowconfigure(3, weight=2)
        self.grid_rowconfigure(4, weight=3)
        self._image_ref: ctk.CTkImage | None = None

        self.title_lbl = ctk.CTkLabel(
            self,
            text="Selecione um resultado",
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w",
            justify="left",
        )
        self.title_lbl.grid(row=0, column=0, sticky="ew", pady=(0, 2))

        self.sub_lbl = ctk.CTkLabel(
            self, text="", text_color="gray60", anchor="w", justify="left"
        )
        self.sub_lbl.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        self.image_label = ctk.CTkLabel(
            self,
            text="Imagem JLC",
            height=92,
            fg_color="#171717",
            text_color="gray70",
            corner_radius=8,
        )
        self.image_label.grid(row=2, column=0, sticky="ew", pady=(0, 8))

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=3, column=0, sticky="nsew")
        self.scroll.grid_columnconfigure(0, weight=1)

        self.preview_panel = PreviewPanel(self)
        self.preview_panel.grid(row=4, column=0, sticky="nsew", pady=(8, 0))

        self.action_bar = ctk.CTkFrame(self, fg_color="transparent")
        self.action_bar.grid(row=5, column=0, sticky="ew", pady=(8, 0))
        self.action_bar.grid_columnconfigure((0, 1), weight=1)

        self.preview_btn = ctk.CTkButton(
            self.action_bar,
            text="Pré-visualizar",
            height=38,
            command=self._click_preview,
            state="disabled",
        )
        self.preview_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.download_btn = ctk.CTkButton(
            self.action_bar,
            text="⬇  Baixar símbolo + footprint",
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
        self.preview_btn.configure(state="normal", text="Pré-visualizar")
        self.preview_panel.clear("Preview: clique em Pré-visualizar para carregar.")

        for child in self.scroll.winfo_children():
            child.destroy()

        chip_row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        chip_row.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self._chip(chip_row, "Basic" if comp.is_basic else "Extended",
                   fg="#2ecc71" if comp.is_basic else "#7f8c8d", col=0)
        self._chip(chip_row, f"Estoque: {comp.stock:,}", fg="#3498db", col=1)
        unit1 = comp.unit_price_for(1)
        if unit1 is not None:
            self._chip(chip_row, f"${unit1:.4f} / un", fg="#f39c12", col=2)
        self._chip(chip_row, f"Mín: {comp.min_purchase}", fg="#7f8c8d", col=3)

        if comp.prices:
            ctk.CTkLabel(
                self.scroll,
                text="Preço por quantidade",
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
                text="Abrir datasheet",
                fg_color="transparent",
                border_width=1,
                command=lambda u=comp.datasheet_url: _open_url(u),
            ).grid(row=3, column=0, sticky="ew", pady=(0, 10))

        if comp.description:
            ctk.CTkLabel(
                self.scroll,
                text="Descrição",
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
                text="Especificações",
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
            text="Carregando..." if running else "Pré-visualizar",
        )
        if running:
            self.preview_panel.clear("Preview carregando arquivos KiCad...")

    def show_preview(self, artifacts) -> list[str]:
        return self.preview_panel.show_artifacts(artifacts)

    def clear_preview(self, message: str) -> None:
        self.preview_panel.clear(message)

    def set_image_loading(self) -> None:
        self._image_ref = None
        self.image_label.configure(image=None, text="Carregando imagem JLC...")

    def show_image(self, image: Image.Image) -> None:
        image = image.convert("RGBA")
        image.thumbnail((220, 90), Image.Resampling.LANCZOS)
        self._image_ref = ctk.CTkImage(light_image=image, dark_image=image, size=image.size)
        self.image_label.configure(image=self._image_ref, text="")

    def clear_image(self, message: str) -> None:
        self._image_ref = None
        self.image_label.configure(image=None, text=message)


def _preview_dir(lcsc_id: str) -> Path:
    safe_id = "".join(ch for ch in lcsc_id.upper() if ch.isalnum() or ch in {"_", "-"})
    return cache_dir() / "previews" / safe_id


def _open_url(url: str) -> None:
    import webbrowser

    try:
        webbrowser.open(url)
    except Exception:
        pass
