## EasyJLC 0.1.0 — primeira release pública

GUI multiplataforma para buscar, pré-visualizar e baixar símbolos + footprints KiCad do LCSC/JLCPCB, com preço, estoque e histórico.

### Downloads

| Arquivo | Plataforma | Tamanho | Instalação |
|---------|------------|---------|------------|
| `EasyJLC-0.1.0-x86_64.AppImage` | Linux x86-64, qualquer distro | 24 MB | `chmod +x` + duplo clique |
| `easyjlc_0.1.0_amd64.deb` | Debian / Ubuntu / Mint / Pop!_OS | 23 MB | `sudo dpkg -i easyjlc_0.1.0_amd64.deb` |
| `easyjlc` | Binário Linux onefile (cru) | 24 MB | `./easyjlc` |

Windows `.exe` virá numa release separada.

### Destaques

- **Busca** LCSC / JLCPCB paginada com thumbnails, preço, estoque, badge Basic/Extended.
- **Preview KiCad renderizado** (símbolo + footprint) com zoom e pan; rotação de pads correta.
- **Download completo** via `easyeda2kicad` em venv isolado gerenciado pelo app.
- **Aba Documentação** com guia para configurar o KiCad Symbol/Footprint Library Manager.
- **Multi-idioma**: pt-BR, inglês, alemão (selecionável no header).
- **Pasta default** `~/Documents/EasyJLC` multiplataforma.

### Requisitos

- Linux x86-64 com `python3 >= 3.10` (usado apenas para provisionar o venv do `easyeda2kicad` na primeira execução; presente por default na maioria das distros).
- Conexão com internet para baixar componentes.

### Changelog completo

Veja [CHANGELOG.md](../CHANGELOG.md).

### Licença

GPL-3.0-or-later.
