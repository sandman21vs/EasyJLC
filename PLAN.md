# EasyJLC — Plano de Ação

> Aplicativo gráfico multiplataforma para baixar símbolos/footprints KiCad a partir do LCSC/EasyEDA, com busca, preview, preço e estoque JLCPCB. Substitui e expande o fluxo atual de `jlc_downloader.py` / `.bat`.

Projeto criado em `/home/idea/EasyJLC` a partir dos scripts do `SandKrux` (copiados para `legacy/`).

---

## 1. Decisões travadas

| Tema | Escolha | Observação |
|------|---------|-----------|
| Nome do projeto | **EasyJLC** | Pasta `/home/idea/EasyJLC` |
| Linguagem | **Python 3.10+** | Mesma base do script atual |
| GUI | **CustomTkinter** | Tema claro/escuro, baixa dependência, cross-platform |
| Distribuição | **PyInstaller** (`.exe` para Windows, binário/AppImage para Linux) | macOS como follow-up |
| Escopo MVP | Download GUI + histórico + preferências + busca/preview completo + preço/estoque | Tudo marcado pelo usuário |
| Preview | **Completo** (símbolo + footprint renderizados) | Parse dos `.kicad_sym` / `.kicad_mod` baixados |
| Plataforma inicial | Linux + Windows | macOS na v1.2 |

Inspiração de features (sem usar como plugin): [Steffen-W/Import-LIB-KiCad-Plugin](https://github.com/Steffen-W/Import-LIB-KiCad-Plugin).

---

## 2. Arquitetura proposta

```
EasyJLC/
├── PLAN.md                   # este documento
├── README.md                 # instruções de uso / instalação
├── pyproject.toml            # metadados + deps (PEP 621)
├── requirements.txt          # fallback para builds PyInstaller
├── .gitignore
├── easyjlc/                  # pacote principal
│   ├── __init__.py
│   ├── __main__.py           # python -m easyjlc
│   ├── app.py                # ponto de entrada GUI (CustomTkinter)
│   ├── config.py             # paths (XDG / AppData), logging
│   ├── settings.py           # preferências persistentes (JSON em user dir)
│   ├── history.py            # histórico de downloads
│   ├── core/
│   │   ├── easyeda.py        # wrapper sobre easyeda2kicad (subprocess + venv)
│   │   ├── jlc_api.py        # cliente REST JLCPCB/LCSC (preço, estoque, busca)
│   │   ├── kicad_parse.py    # parser S-expr minimal para .kicad_sym / .kicad_mod
│   │   └── models.py         # dataclasses: Component, Price, StockInfo
│   ├── ui/
│   │   ├── main_window.py    # layout: barra superior, área central, log
│   │   ├── search_panel.py   # campo de busca + resultados
│   │   ├── detail_panel.py   # metadados + preço + estoque + botão download
│   │   ├── preview_canvas.py # desenho símbolo (Canvas)
│   │   ├── footprint_canvas.py # desenho footprint
│   │   ├── history_panel.py  # lista de IDs baixados, rebaixar
│   │   ├── settings_dialog.py
│   │   └── widgets.py        # componentes reutilizáveis (chips, badges)
│   └── resources/
│       ├── icons/
│       └── themes/
├── legacy/                   # scripts originais (referência)
│   ├── jlc_downloader.py
│   ├── jlc_downloader.bat
│   ├── jlc_downloader_app.bat
│   ├── run_jlc_downloader.sh
│   └── jlc_downloader.desktop
├── packaging/
│   ├── easyjlc.spec          # PyInstaller (Linux)
│   ├── easyjlc-win.spec      # PyInstaller (Windows)
│   ├── easyjlc.desktop       # .desktop para Linux
│   └── icon.png / icon.ico
├── scripts/
│   ├── run_dev.sh            # roda a partir do venv dev
│   ├── run_dev.bat
│   └── build_release.sh      # chama PyInstaller
└── tests/
    ├── test_history.py
    ├── test_settings.py
    ├── test_jlc_api.py        # com mocks HTTP
    └── test_kicad_parse.py
```

### Princípios
- **Back-end desacoplado da GUI**: `core/` não importa nada de `ui/`. Facilita testes e futuro CLI.
- **easyeda2kicad** continua sendo a engine real do download (roda via subprocess em venv local, igual ao script atual).
- **API JLCPCB**: investigar endpoints usados pelo plugin Import-LIB-KiCad-Plugin e pelo site `jlcpcb.com/parts` (endpoint `jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList`). Respeitar throttle e cache em disco.
- **Cache**: resultados de busca + metadados de componentes expiram em 24 h por padrão (configurável), armazenados em `user_cache_dir/easyjlc/`.
- **Logs**: `user_log_dir/easyjlc/app.log` rotativo; console tab na GUI mostra ao vivo.

---

## 3. Fluxos de usuário (MVP)

### 3.1 Download direto por LCSC ID (compatível com hoje)
1. Usuário digita `C2040` no campo de busca.
2. App consulta JLC API → mostra painel de detalhes (nome, pacote, descrição, preço unitário por faixa, estoque, imagem, datasheet link).
3. App renderiza preview do símbolo e footprint (após clique em "Pré-visualizar" — que dispara o download para cache).
4. Usuário escolhe pasta de saída (ou usa default lembrada) → clica **Baixar**.
5. Entrada vai para histórico com timestamp + caminho de saída.

### 3.2 Busca textual
1. Campo de busca aceita termos ("ESP32-S3", "0603 10k", "LM358").
2. Resultados paginados em lista com: thumbnail, MPN, pacote, preço, estoque, botão "Detalhes".
3. Filtros laterais: categoria, pacote, faixa de estoque, faixa de preço, Basic/Extended JLCPCB.

### 3.3 Histórico
- Aba dedicada mostrando últimos N downloads, ordenáveis por data/ID.
- Ações: **Rebaixar**, **Abrir pasta**, **Copiar LCSC ID**, **Remover**.

### 3.4 Preferências
- Pasta de saída default.
- Tema (light/dark/system).
- Idioma (pt-BR / en) — estrutura pronta, strings em `resources/i18n/`.
- Política de cache (TTL, limpar agora).
- Mostrar preço em USD ou BRL (cotação consultada uma vez por sessão).

---

## 4. Roadmap

### Sprint 1 — Fundação (2–3 dias)
- [x] `pyproject.toml`, `requirements.txt`, `.gitignore`, README inicial.
- [x] Esqueleto do pacote `easyjlc/` com `app.py` abrindo janela CustomTkinter vazia.
- [x] `config.py` resolvendo diretórios XDG / AppData (usar `platformdirs`).
- [x] `settings.py` e `history.py` com persistência JSON + testes.
- [x] Script `run_dev.sh` / `run_dev.bat` que cria venv local e chama `python -m easyjlc`.

### Sprint 2 — Paridade com o downloader atual (2 dias)
- [x] `core/easyeda.py`: porta da lógica de venv/subprocess de `legacy/jlc_downloader.py`.
- [x] Tela principal: campo LCSC ID, seletor de pasta (tkinter `filedialog`), botão Baixar, log tab.
- [x] Integração com histórico e preferências.
- [ ] Teste manual: baixar `C2040` em Linux e Windows.

### Sprint 3 — Busca, preço, estoque (3–4 dias)
- [x] `core/jlc_api.py`: endpoints de busca e detalhe; cache em disco.
- [x] `ui/search_panel.py` + `ui/detail_panel.py` com resultado paginado.
- [ ] Filtros básicos.
- [x] Chips de preço/estoque/Basic-Extended no detail panel.

### Sprint 4 — Preview renderizado (feito)
- [x] `core/kicad_parse.py`: parser S-expr lendo `.kicad_sym` (versão ≥ 7) e `.kicad_mod`.
- [x] `ui/preview_canvas.py`: desenha símbolo (pinos, retângulos, polylines) em `tk.Canvas`.
- [x] `ui/footprint_canvas.py`: desenha pads + silkscreen (cores por camada).
- [x] Cache em `~/.cache/EasyJLC/previews/<LCSC_ID>/` evita re-baixar via easyeda2kicad.

### Sprint 4.5 — Estabilizar busca (feito)
- [x] Remover `trace_add` no campo de busca, `reset_session()`, watchdog/throttle; timeout 15 s.
- [x] Remover `_drain_message_queue` e `_interrupt_search_engine`.
- [x] Padronizar com contador de request-id + checagem no callback (padrão do plugin `Import-LIB-KiCad-Plugin/plugins/component_search.py`).
- [x] Botão **Buscar** vira **Cancelar** enquanto há busca em voo; clicar cancela e invalida o req_id.
- [x] Dedup de fetch de imagem: `_pending_image_urls` + cache de bytes por URL.
- [x] `_http_search_lock` serializa POST à JLC (WAF bate quando 3 threads disputam).

### Sprint 4.6 — Licença GPL-3.0 (feito)
- [x] Projeto migrado para GPL-3.0-or-later.
- [x] `LICENSE`, `pyproject.toml`, `README.md` atualizados.

### Sprint 4.7 — UX da aba Buscar (feito)
- [x] Thumbnails na lista da esquerda, pré-carregadas página a página com semáforo de 3 threads.
- [x] Auto-select do primeiro resultado + auto-preview no clique (símbolo + footprint).
- [x] Remoção da imagem grande no painel direito (redundante com thumbnail).

### Sprint 4.8 — Usabilidade do preview (feito)
- [x] Scroll do mouse na lista de resultados (bind recursivo em `<MouseWheel>` + `<Button-4>`/`<Button-5>` em cada row e filhos, propagando pro `_parent_canvas` do `CTkScrollableFrame`).
- [x] Zoom + pan no canvas de símbolo e footprint (scroll = zoom ancorado no cursor, drag = pan, duplo clique = fit). Auto-fit em resize só acontece se o usuário ainda não interagiu.
- [x] Rotação de pads honrada no footprint canvas (retangulares via `create_polygon` com cantos rotacionados; oval não-circular via polígono elíptico rotacionado).
- [x] Pasta default `~/Documents/EasyJLC` pré-selecionada na aba Download quando settings está vazio (`config.default_output_dir()` via `platformdirs.user_documents_path`).
- [x] Nova aba "Documentação" com guia de configuração das bibliotecas do KiCad + recomendação de colocar componentes dentro da pasta do projeto (`${KIPRJMOD}`).
- [x] Scroll do mouse na aba Documentação (bind recursivo `<MouseWheel>`/`<Button-4>`/`<Button-5>` no `CTkScrollableFrame`).
- [x] Visibilidade da seção "Recentes" no Download tab: cores `("gray85","gray25")` / texto `("gray10","gray95")` no light e dark.
- [ ] Revisão rápida de alinhamento / espaçamento dos botões.

### Sprint 4.9 — Estrutura multi-idioma (feito)
- [x] `easyjlc/i18n.py`: carregador gettext-style (pt-BR = chave identidade; en/de via catálogo JSON em `easyjlc/resources/i18n/*.json`). Placeholders `{name}` preservados via `str.format(**kwargs)` com fallback silencioso.
- [x] Migração das strings de UI para `t(...)`: `main_window`, `docs_tab`, `download_tab`, `search_tab`, `history_tab`, `log_tab`, `preview_panel`, `preview_canvas`, `footprint_canvas`.
- [x] Catálogos `en.json` e `de.json` traduzidos (79 strings cada) por agentes Haiku em paralelo, com validação de placeholders e cobertura 100%.
- [x] Seletor de idioma no header (`CTkOptionMenu`) grava em `settings.language`; aplicação efetiva no próximo start (mensagem no log).
- [x] `_tab_names` dict no `MainWindow` para desacoplar `tabs.set(...)` do texto exibido (CTkTabview indexa por label).

### Sprint 5 — Empacotamento (Linux feito)
- [x] `packaging/easyjlc-linux.spec` — onefile Linux, customtkinter data + i18n bundled, console=False.
- [x] `scripts/build_release.sh` — pytest → pyinstaller → `dist/easyjlc` (~24 MB).
- [x] Patch `easyeda.py` para PyInstaller: `sys.frozen` usa `shutil.which("python3")` em vez de `sys.executable`; venv do easyeda2kicad criado via `python3 -m venv` em subprocess quando frozen.
- [x] Ícone placeholder em `easyjlc/resources/icons/easyjlc.png` (512x512, gerado via Pillow — substituir quando tiver logo oficial).
- [x] `packaging/build_appimage.sh` — gera `dist/EasyJLC-<v>-x86_64.AppImage` (24 MB). Requer `appimagetool` em `/tmp/appimagetool` (baixar de github.com/AppImage/appimagetool/releases).
- [x] `packaging/build_deb.sh` — gera `dist/easyjlc_<v>_amd64.deb` (23 MB) com `.desktop`, ícone no hicolor, binário em `/opt/easyjlc/`, symlink em `/usr/bin/easyjlc`, dependência `python3 >= 3.10`.
- [ ] Teste manual: baixar `C2040` com o binário (validar bootstrap do venv em `user_data_dir`).
- [ ] Spec Windows (`packaging/easyjlc-windows.spec`) + build em máquina Windows do usuário.
- [ ] Ícones reais (substituir placeholder); `.ico` para Windows.
- [ ] Smoke test em VM/máquina Windows.

### UI Polish — backlog (feedback do usuário após Sprint 2)
- [ ] **Pasta default pré-selecionada** na aba Download (ex.: primeira recente, `~/KiCad/lib`, ou última usada no histórico com sucesso). Hoje o campo abre vazio.
- [ ] **Seletor de pasta moderno**: o `tkinter.filedialog` nativo tem visual antigo no Linux. Opções: (a) empacotar/usar `zenity`/`kdialog` quando disponíveis; (b) criar um file picker custom em CustomTkinter; (c) usar `tkfilebrowser` (terceiros). Decidir na Sprint de polish.
- [ ] Revisar espaçamento, alinhamento e cores dos botões/chips quando a Sprint 3 estiver fechada.

### Pós-MVP (v1.1+)
- [ ] **Preview SVG em memória** (ex-Sprint 4.7): vendorizar `easyeda_svg_renderer` do plugin GPL (`legacy/Import-LIB-KiCad-Plugin/plugins/easyeda2kicad/`) + `cairosvg`. Ganho: elimina o subprocess de ~5-10 s no primeiro preview. Risco: reescreve o canvas e quebra a paridade 1:1 com os arquivos baixados. **Adiado** até o cache miss virar gargalo real — a fidelidade do preview atual com o `.kicad_sym` final tem valor.
- [ ] BOM loader: importar `.csv` do KiCad e baixar todos os símbolos/footprints em lote.
- [ ] Atalho "Criar símbolo alternativo" (picker de BOM equivalentes JLC Basic).
- [ ] Suporte macOS (build + assinatura).
- [ ] Integração com `kicad-cli` para validar os libs baixados.
- [ ] Tradução completa pt-BR / en (Weblate ou arquivos `.po`).
- [ ] Publicar em GitHub com CI (GitHub Actions) construindo releases para Linux/Windows.

---

## 5. Riscos & mitigações

| Risco | Mitigação |
|-------|-----------|
| API JLCPCB sem contrato público / mudar sem aviso | Isolar em `core/jlc_api.py`, contratos tipados, testes com fixtures, fallback para scrape se necessário. |
| Parser S-expr falhar em símbolos esquisitos | Fallback: abrir KiCad headless (`kicad-cli sym upgrade`) ou cair em preview só-de-metadados. |
| PyInstaller + Tkinter em Linux (problema de tema) | Testar com `--hidden-import` e embutir fontes; fallback AppImage. |
| Usuário sem Python no Windows | Binário PyInstaller resolve; legacy `.bat` cai fora após MVP. |
| Throttle/ban da API | Cache agressivo + backoff exponencial + User-Agent identificável. |

---

## 6. Próximo passo imediato

Aguardando o "ok" do usuário neste plano para começar a **Sprint 1** (scaffold do pacote + CustomTkinter rodando). Após aprovação:
1. Criar `pyproject.toml` com deps (`customtkinter`, `platformdirs`, `requests`, `pillow`).
2. Subir esqueleto de pastas + janela placeholder rodando em Linux.
3. Commit inicial do repositório git em `/home/idea/EasyJLC`.
