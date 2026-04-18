"""Aba Download — campo LCSC ID, seletor de pasta e execução em thread."""

from __future__ import annotations

import logging
import queue
import threading
import time
from pathlib import Path
from tkinter import filedialog
from typing import Callable

import customtkinter as ctk

from easyjlc.core import find_kicad_artifacts
from easyjlc.core import EasyEdaError, EasyEdaRunner
from easyjlc.settings import Settings
from easyjlc.ui.bindings import bind_select_all
from easyjlc.ui.preview_panel import PreviewPanel

log = logging.getLogger("easyjlc.download_tab")


class DownloadTab(ctk.CTkFrame):
    """Interface da aba Download.

    `on_log` recebe cada linha de log (já na thread da UI).
    `on_finished` recebe (lcsc_id, output_dir|None, success, message).
    """

    POLL_MS = 80

    def __init__(
        self,
        master,
        settings: Settings,
        runner: EasyEdaRunner,
        on_log: Callable[[str], None],
        on_finished: Callable[[str, str | None, bool, str], None],
    ) -> None:
        super().__init__(master, fg_color="transparent")
        self.settings = settings
        self.runner = runner
        self.on_log = on_log
        self.on_finished = on_finished

        self._msg_queue: "queue.Queue[tuple[str, object]]" = queue.Queue()
        self._worker: threading.Thread | None = None
        self._download_started_at: float | None = None
        self._last_preview_lcsc_id = ""

        self._build_ui()
        self.after(self.POLL_MS, self._poll_queue)

    # ---------- UI ----------

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(5, weight=1)

        ctk.CTkLabel(self, text="LCSC ID", anchor="w").grid(
            row=0, column=0, sticky="w", padx=(0, 10), pady=(4, 2)
        )
        self.lcsc_var = ctk.StringVar()
        self.lcsc_entry = ctk.CTkEntry(
            self, textvariable=self.lcsc_var, placeholder_text="ex: C2040"
        )
        self.lcsc_entry.grid(row=0, column=1, columnspan=2, sticky="ew", pady=(4, 2))
        self.lcsc_entry.bind("<Return>", lambda _e: self._start_download())
        bind_select_all(self.lcsc_entry)
        self.lcsc_var.trace_add("write", self._on_lcsc_changed)

        ctk.CTkLabel(self, text="Pasta de saída", anchor="w").grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=(10, 2)
        )
        self.output_var = ctk.StringVar(value=self.settings.output_dir or "")
        self.output_entry = ctk.CTkEntry(
            self,
            textvariable=self.output_var,
            placeholder_text="Deixe vazio para usar a pasta default do easyeda2kicad",
        )
        self.output_entry.grid(row=1, column=1, sticky="ew", pady=(10, 2))
        bind_select_all(self.output_entry)

        ctk.CTkButton(self, text="Procurar...", width=110, command=self._browse).grid(
            row=1, column=2, sticky="e", padx=(8, 0), pady=(10, 2)
        )

        self.recent_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.recent_frame.grid(row=2, column=1, columnspan=2, sticky="ew", pady=(2, 0))
        self._render_recent()

        self.download_btn = ctk.CTkButton(
            self,
            text="⬇  Baixar",
            height=38,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._start_download,
        )
        self.download_btn.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(18, 4))

        self.status_var = ctk.StringVar(value="Pronto.")
        ctk.CTkLabel(
            self, textvariable=self.status_var, text_color="gray70", anchor="w"
        ).grid(row=4, column=0, columnspan=3, sticky="ew")

        self.preview_panel = PreviewPanel(self)
        self.preview_panel.grid(
            row=5, column=0, columnspan=3, sticky="nsew", pady=(12, 0)
        )

    def _render_recent(self) -> None:
        for child in self.recent_frame.winfo_children():
            child.destroy()

        recents = self.settings.recent_output_dirs[:5]
        if not recents:
            return

        ctk.CTkLabel(
            self.recent_frame,
            text="Recentes:",
            text_color="gray60",
            font=ctk.CTkFont(size=11),
        ).grid(row=0, column=0, sticky="w", padx=(0, 6))

        for idx, path in enumerate(recents):
            short = path if len(path) <= 40 else "..." + path[-37:]
            ctk.CTkButton(
                self.recent_frame,
                text=short,
                height=22,
                width=1,
                fg_color="transparent",
                border_width=1,
                font=ctk.CTkFont(size=10),
                command=lambda p=path: self.output_var.set(p),
            ).grid(row=0, column=idx + 1, sticky="w", padx=2)

    def _browse(self) -> None:
        initial = self.output_var.get() or self.settings.output_dir or str(Path.home())
        selected = filedialog.askdirectory(
            title="Selecione a pasta de destino",
            initialdir=initial,
            mustexist=False,
        )
        if selected:
            self.output_var.set(selected)

    # ---------- Ação ----------

    def trigger_download(self, lcsc_id: str, output_dir: str | None) -> None:
        """Permite outra aba (ex.: Histórico) disparar um download."""
        self.on_log(f"[download] trigger externo para {lcsc_id}, output={output_dir or '(campo atual)'}")
        self.lcsc_var.set(lcsc_id)
        if output_dir is not None:
            self.output_var.set(output_dir)
        self._start_download()

    def _start_download(self) -> None:
        if self._worker and self._worker.is_alive():
            self.on_log("Já há um download em andamento.")
            return

        lcsc_id = self.lcsc_var.get().strip()
        if not lcsc_id:
            self.on_log("Digite um LCSC ID antes de baixar.")
            self.lcsc_entry.focus_set()
            return

        raw_output = self.output_var.get().strip()
        output_dir: Path | None = Path(raw_output).expanduser() if raw_output else None
        self.on_log(f"[download] iniciar {lcsc_id}, output={output_dir or '(default easyeda2kicad)'}")

        if output_dir is not None and not output_dir.exists():
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                self.on_log(f'Pasta criada: "{output_dir}"')
            except OSError as exc:
                self.on_log(f"Falha ao criar pasta: {exc}")
                return

        self._set_running(True)
        self._download_started_at = time.time()
        self.status_var.set(f"Baixando {lcsc_id}...")
        self.preview_panel.clear("Preview aguardando o download terminar...")

        self._worker = threading.Thread(
            target=self._worker_entry,
            args=(lcsc_id, output_dir),
            daemon=True,
        )
        self._worker.start()

    def _worker_entry(self, lcsc_id: str, output_dir: Path | None) -> None:
        def cb(line: str) -> None:
            self._msg_queue.put(("log", line))

        try:
            rc = self.runner.download(lcsc_id, output_dir, log_cb=cb)
        except EasyEdaError as exc:
            self._msg_queue.put(("log", f"Erro: {exc}"))
            self._msg_queue.put(
                ("done", (lcsc_id, str(output_dir) if output_dir else None, False, str(exc)))
            )
            return
        except Exception as exc:  # pragma: no cover — defesa extra
            log.exception("Erro inesperado no worker")
            self._msg_queue.put(("log", f"Erro inesperado: {exc}"))
            self._msg_queue.put(
                ("done", (lcsc_id, str(output_dir) if output_dir else None, False, str(exc)))
            )
            return

        success = rc == 0
        message = "" if success else f"exit code {rc}"
        self._msg_queue.put(
            ("done", (lcsc_id, str(output_dir) if output_dir else None, success, message))
        )

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self._msg_queue.get_nowait()
                if kind == "log":
                    self.on_log(str(payload))
                elif kind == "done":
                    lcsc_id, output_dir_s, success, message = payload  # type: ignore[misc]
                    self._on_download_done(lcsc_id, output_dir_s, success, message)
        except queue.Empty:
            pass
        self.after(self.POLL_MS, self._poll_queue)

    def _on_download_done(
        self, lcsc_id: str, output_dir: str | None, success: bool, message: str
    ) -> None:
        self._set_running(False)
        self.on_log(
            f"[download] finalizado {lcsc_id}: success={success}, "
            f"output={output_dir or '(default)'}, message={message or '-'}"
        )
        if success:
            self.status_var.set(f"{lcsc_id} baixado.")
            if output_dir:
                self.settings.output_dir = output_dir
                self.settings.add_recent_output(output_dir)
                self._render_recent()
                since = self._download_started_at
                artifacts = find_kicad_artifacts(
                    output_dir,
                    changed_since=(since - 1.0) if since is not None else None,
                    lcsc_id=lcsc_id,
                )
                self.on_log(
                    f"[preview] busca pós-download filtrada por {lcsc_id}: "
                    f"symbol={artifacts.symbol or '-'} footprint={artifacts.footprint or '-'}"
                )
                if not artifacts.has_all:
                    artifacts = find_kicad_artifacts(output_dir, lcsc_id=lcsc_id)
                    self.on_log(
                        f"[preview] fallback na pasta inteira filtrado por {lcsc_id}: "
                        f"symbol={artifacts.symbol or '-'} footprint={artifacts.footprint or '-'}"
                    )
                warnings = self.preview_panel.show_artifacts(artifacts, lcsc_id=lcsc_id)
                self._last_preview_lcsc_id = lcsc_id
                for warning in warnings:
                    self.on_log(f"[preview] {warning}")
            else:
                self.preview_panel.clear(
                    "Preview indisponível: escolha uma pasta de saída para localizar os arquivos."
                )
        else:
            self.status_var.set(f"{lcsc_id} falhou. {message}".strip())
            self.preview_panel.clear("Preview indisponível: download falhou.")
        self.on_finished(lcsc_id, output_dir, success, message)

    def _set_running(self, running: bool) -> None:
        state = "disabled" if running else "normal"
        self.download_btn.configure(
            state=state,
            text="⏳  Baixando..." if running else "⬇  Baixar",
        )
        self.lcsc_entry.configure(state=state)
        self.output_entry.configure(state=state)

    def _on_lcsc_changed(self, *_args) -> None:
        lcsc_id = self.lcsc_var.get().strip()
        if lcsc_id == self._last_preview_lcsc_id:
            return
        self._last_preview_lcsc_id = ""
        self.on_log(f"[download] LCSC ID alterado para {lcsc_id or '(vazio)'}; limpando preview")
        self.preview_panel.clear("Preview: baixe este componente para atualizar.")
