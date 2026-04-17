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
- [ ] `pyproject.toml`, `requirements.txt`, `.gitignore`, README inicial.
- [ ] Esqueleto do pacote `easyjlc/` com `app.py` abrindo janela CustomTkinter vazia.
- [ ] `config.py` resolvendo diretórios XDG / AppData (usar `platformdirs`).
- [ ] `settings.py` e `history.py` com persistência JSON + testes.
- [ ] Script `run_dev.sh` / `run_dev.bat` que cria venv local e chama `python -m easyjlc`.

### Sprint 2 — Paridade com o downloader atual (2 dias)
- [ ] `core/easyeda.py`: porta da lógica de venv/subprocess de `legacy/jlc_downloader.py`.
- [ ] Tela principal: campo LCSC ID, seletor de pasta (tkinter `filedialog`), botão Baixar, log tab.
- [ ] Integração com histórico e preferências.
- [ ] Teste manual: baixar `C2040` em Linux e Windows.

### Sprint 3 — Busca, preço, estoque (3–4 dias)
- [ ] `core/jlc_api.py`: endpoints de busca e detalhe; cache em disco.
- [ ] `ui/search_panel.py` + `ui/detail_panel.py` com resultado paginado e filtros básicos.
- [ ] Chips de preço/estoque/Basic-Extended no detail panel.

### Sprint 4 — Preview renderizado (4–5 dias)
- [ ] `core/kicad_parse.py`: parser S-expr lendo `.kicad_sym` (versão ≥ 7) e `.kicad_mod`.
- [ ] `ui/preview_canvas.py`: desenha símbolo (pinos, retângulos, texto) em `tk.Canvas` com zoom/pan.
- [ ] `ui/footprint_canvas.py`: desenha pads + silkscreen (várias camadas coloridas).
- [ ] Cache do parse para evitar reparsear em navegação.

### Sprint 5 — Empacotamento (2 dias)
- [ ] Specs PyInstaller (Linux + Windows) com `--onefile` e ícones embutidos.
- [ ] `build_release.sh`: roda lint, testes, PyInstaller, gera artefatos em `dist/`.
- [ ] AppImage (Linux) via `linuxdeploy` ou manter binário onefile.
- [ ] Smoke test em VM Windows.

### UI Polish — backlog (feedback do usuário após Sprint 2)
- [ ] **Pasta default pré-selecionada** na aba Download (ex.: primeira recente, `~/KiCad/lib`, ou última usada no histórico com sucesso). Hoje o campo abre vazio.
- [ ] **Seletor de pasta moderno**: o `tkinter.filedialog` nativo tem visual antigo no Linux. Opções: (a) empacotar/usar `zenity`/`kdialog` quando disponíveis; (b) criar um file picker custom em CustomTkinter; (c) usar `tkfilebrowser` (terceiros). Decidir na Sprint de polish.
- [ ] Revisar espaçamento, alinhamento e cores dos botões/chips quando a Sprint 3 estiver fechada.

### Pós-MVP (v1.1+)
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
