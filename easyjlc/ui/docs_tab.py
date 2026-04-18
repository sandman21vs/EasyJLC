"""Aba Documentação — guia rápido de como configurar o KiCad com o EasyJLC."""

from __future__ import annotations

import customtkinter as ctk

from easyjlc.config import default_output_dir
from easyjlc.i18n import t


SECTIONS: list[tuple[str, str]] = [
    (
        "Onde o EasyJLC salva os componentes",
        "Por padrão, cada download vai para a pasta escolhida na aba "
        "\"Download direto\". Quando você ainda não configurou nada, o "
        "EasyJLC sugere a pasta:\n\n"
        "    {default_path}\n\n"
        "Ela é criada automaticamente no primeiro download. A última pasta "
        "utilizada fica memorizada em \"Recentes\" para facilitar o reuso.",
    ),
    (
        "Recomendação: use a pasta do próprio projeto KiCad",
        "Para projetos que você pretende compartilhar (Git, zip, Drive, etc.), "
        "a melhor prática é salvar os símbolos e footprints dentro da pasta "
        "do projeto KiCad, por exemplo:\n\n"
        "    MeuProjeto/\n"
        "    ├── MeuProjeto.kicad_pro\n"
        "    ├── MeuProjeto.kicad_sch\n"
        "    ├── MeuProjeto.kicad_pcb\n"
        "    └── libs/\n"
        "        ├── MeuProjeto.kicad_sym\n"
        "        └── MeuProjeto.pretty/\n\n"
        "Com isso o projeto fica autocontido: quem clonar ou abrir o .zip "
        "recebe os componentes juntos, sem precisar baixar tudo de novo pelo "
        "LCSC. No EasyJLC, basta escolher essa pasta \"libs\" como destino do "
        "download.",
    ),
    (
        "Configurar a biblioteca de SÍMBOLOS no KiCad",
        "1. Abra o KiCad (janela principal) ou o Schematic Editor.\n"
        "2. Menu: Preferências → Gerenciar Bibliotecas de Símbolos\n"
        "   (Preferences → Manage Symbol Libraries).\n"
        "3. Escolha a aba:\n"
        "   • \"Project Specific Libraries\" (Bibliotecas do Projeto) — "
        "recomendada quando os símbolos estão dentro da pasta do projeto.\n"
        "   • \"Global Libraries\" (Bibliotecas Globais) — se você quer usar "
        "os mesmos componentes em vários projetos (ex.: pasta "
        "~/Documents/EasyJLC).\n"
        "4. Clique no botão \"+\" e preencha:\n"
        "   • Nickname: um nome curto, ex.: \"EasyJLC\" ou o nome do projeto.\n"
        "   • Library Path: caminho para o arquivo .kicad_sym baixado.\n"
        "     - Projeto: use ${KIPRJMOD}/libs/Meu.kicad_sym\n"
        "     - Global : use o caminho absoluto, ex.: "
        "~/Documents/EasyJLC/Meu.kicad_sym\n"
        "   • Library Format: KiCad.\n"
        "5. OK. Os símbolos já aparecem no \"Add Symbol\" do Schematic.",
    ),
    (
        "Configurar a biblioteca de FOOTPRINTS no KiCad",
        "1. No PCB Editor (ou janela principal).\n"
        "2. Menu: Preferências → Gerenciar Bibliotecas de Footprint\n"
        "   (Preferences → Manage Footprint Libraries).\n"
        "3. Mesma lógica das bibliotecas de símbolo: aba \"Project Specific\" "
        "ou \"Global\".\n"
        "4. Clique em \"+\" e preencha:\n"
        "   • Nickname: idem (ex.: \"EasyJLC\").\n"
        "   • Library Path: caminho para a pasta .pretty/ que contém os "
        ".kicad_mod baixados.\n"
        "     - Projeto: ${KIPRJMOD}/libs/Meu.pretty\n"
        "     - Global : ~/Documents/EasyJLC/Meu.pretty\n"
        "   • Library Format: KiCad.\n"
        "5. OK. Os footprints aparecem no Footprint Editor / PCB.",
    ),
    (
        "Variáveis úteis de caminho",
        "• ${KIPRJMOD}  — pasta do projeto atual (recomendado para bibliotecas "
        "do projeto).\n"
        "• ${KICAD_USER_LIB} — pasta global configurada em Preferências → "
        "Configurar Caminhos (Configure Paths).\n"
        "• ${HOME}      — sua home (Linux/macOS) ou perfil de usuário "
        "(Windows).\n\n"
        "Use ${KIPRJMOD} sempre que puder em bibliotecas de projeto: o "
        "caminho vira relativo e o projeto funciona em qualquer máquina.",
    ),
    (
        "Fluxo recomendado com EasyJLC",
        "1. Crie o projeto KiCad e, dentro dele, uma pasta \"libs\".\n"
        "2. No EasyJLC, aba Download direto, selecione essa pasta \"libs\" "
        "como destino.\n"
        "3. Baixe os componentes necessários (um por um ou pela aba "
        "Buscar).\n"
        "4. No KiCad, configure bibliotecas do projeto usando ${KIPRJMOD}/"
        "libs/... apontando para os .kicad_sym / .pretty baixados.\n"
        "5. Faça commit / zip do projeto inteiro — os componentes vão junto.",
    ),
]


class DocsTab(ctk.CTkFrame):
    def __init__(self, master) -> None:
        super().__init__(master, fg_color="transparent")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=0, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)
        scroll = self._scroll

        ctk.CTkLabel(
            scroll,
            text=t("Usando o EasyJLC com o KiCad"),
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
            justify="left",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 4))

        ctk.CTkLabel(
            scroll,
            text=t(
                "Guia rápido para apontar as bibliotecas do KiCad "
                "para os componentes baixados."
            ),
            font=ctk.CTkFont(size=12),
            text_color="gray70",
            anchor="w",
            justify="left",
            wraplength=780,
        ).grid(row=1, column=0, sticky="ew", pady=(0, 12))

        default_path = str(default_output_dir())
        for idx, (title, body) in enumerate(SECTIONS, start=2):
            translated_body = t(body).replace("{default_path}", default_path)
            self._section(scroll, idx, t(title), translated_body)

        # Roda do mouse: CTkScrollableFrame só escuta na sua própria canvas;
        # filhos engolem o evento. Propagamos recursivamente (mesmo truque da
        # lista de resultados da aba Buscar).
        self._bind_wheel(self._scroll)

    def _section(self, parent, row: int, title: str, body: str) -> None:
        frame = ctk.CTkFrame(parent, fg_color=("gray90", "gray20"), corner_radius=8)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 10), padx=(0, 2))
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
            justify="left",
        ).grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 4))

        ctk.CTkLabel(
            frame,
            text=body,
            font=ctk.CTkFont(size=12),
            anchor="w",
            justify="left",
            wraplength=780,
        ).grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))

    def _bind_wheel(self, widget) -> None:
        widget.bind("<MouseWheel>", self._wheel, add="+")
        widget.bind("<Button-4>", self._wheel, add="+")
        widget.bind("<Button-5>", self._wheel, add="+")
        for child in widget.winfo_children():
            self._bind_wheel(child)

    def _wheel(self, event) -> str:
        canvas = self._scroll._parent_canvas  # type: ignore[attr-defined]
        if event.num == 4:
            canvas.yview_scroll(-3, "units")
        elif event.num == 5:
            canvas.yview_scroll(3, "units")
        else:
            canvas.yview_scroll(int(-event.delta / 40) or (-1 if event.delta > 0 else 1), "units")
        return "break"
