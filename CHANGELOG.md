# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versionamento [SemVer](https://semver.org/lang/pt-BR/).

## [0.1.0] — 2026-04-18

Primeira release pública. MVP de GUI fechado com busca, preview renderizado, download e empacotamento Linux.

### Adicionado

- **GUI CustomTkinter** com abas Buscar, Download direto, Histórico, Documentação e Log.
- **Busca paginada** na API JLCPCB/LCSC com MPN, LCSC ID ou palavra-chave; thumbnails pré-carregadas, badges Basic/Extended, chips de preço e estoque.
- **Preview KiCad renderizado** lendo `.kicad_sym` e `.kicad_mod`:
  - Símbolo: pinos, retângulos, círculos, polylines.
  - Footprint: pads com rotação correta (retângulos via `create_polygon` com cantos rotacionados; ovais não-circulares via polígono elíptico), silkscreen por camada, pad numbering.
  - Zoom ancorado no cursor, pan por drag, duplo clique = fit.
- **Download** via `easyeda2kicad` em venv isolado gerenciado pelo app (em `~/.local/share/EasyJLC/easyeda2kicad-venv/`).
- **Pasta default multiplataforma**: `~/Documents/EasyJLC` (via `platformdirs`).
- **Histórico** persistente em JSON: rebaixar, abrir pasta, copiar LCSC ID.
- **Aba Documentação** embutida com guia de como configurar o KiCad Symbol/Footprint Library Manager, incluindo uso de `${KIPRJMOD}` para caminhos relativos ao projeto.
- **Multi-idioma**: pt-BR, inglês, alemão — selecionável no header, aplica no próximo start.
- **Tema** claro/escuro/sistema via CustomTkinter.
- **Preferências persistentes** (JSON em `user_config_dir`), histórico, logs rotativos.

### Empacotamento

- **Binário Linux onefile** (`dist/easyjlc`) via PyInstaller — 24 MB.
- **AppImage** (`EasyJLC-0.1.0-x86_64.AppImage`) — roda em qualquer distro x86-64.
- **Pacote `.deb`** (`easyjlc_0.1.0_amd64.deb`) — instala em `/opt/easyjlc/`, cria entry no menu, declara `Depends: python3 >= 3.10`.
- Scripts: `scripts/build_release.sh`, `packaging/build_appimage.sh`, `packaging/build_deb.sh`.

### Notas

- O binário Linux requer `python3` no sistema para provisionar o venv do `easyeda2kicad` no primeiro uso. Distros modernas já trazem.
- Ícone atual é placeholder (gerado com Pillow). Substitua `easyjlc/resources/icons/easyjlc.png` e refaça o build quando tiver logo oficial.
- Build Windows (`.exe`) será publicado numa release futura.
