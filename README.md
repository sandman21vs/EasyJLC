# EasyJLC

GUI multiplataforma para buscar, pré-visualizar e baixar símbolos + footprints KiCad direto do catálogo **LCSC / JLCPCB**, com preço, estoque e histórico de downloads.

Sucessor dos scripts `jlc_downloader.py` / `.bat` (preservados em [`legacy/`](legacy/)).

![Licença](https://img.shields.io/badge/license-GPL--3.0--or--later-blue) ![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![Plataforma](https://img.shields.io/badge/linux-x86__64-green) ![Idiomas](https://img.shields.io/badge/i18n-pt--BR%20%7C%20en%20%7C%20de-orange)

---

## Recursos

- **Busca**: MPN, LCSC ID ou palavra-chave. Paginada, com thumbnails, badge Basic/Extended e ordenação por estoque/preço.
- **Preview KiCad renderizado**: símbolo (pinos, retângulos, polylines) e footprint (pads rotacionados, silkscreen por camada) desenhados em `tk.Canvas`, com zoom e pan.
- **Download completo**: símbolo + footprint via `easyeda2kicad`, em venv isolado gerenciado pelo app.
- **Preço + estoque** (JLCPCB API), com faixa por quantidade e link direto para o datasheet.
- **Histórico** persistente: rebaixar, abrir pasta, copiar LCSC ID.
- **Pasta default multiplataforma**: `~/Documents/EasyJLC` (via `platformdirs`).
- **Aba Documentação** embutida com guia de como apontar as bibliotecas do KiCad para os componentes baixados.
- **Multi-idioma**: pt-BR, inglês, alemão — selecionável no header (aplica no próximo start). Estrutura pronta para outros idiomas via JSON.
- **Tema claro/escuro/sistema** via CustomTkinter.

---

## Instalação

### Linux — AppImage (recomendado, qualquer distro x86-64)

```bash
wget https://github.com/<user>/EasyJLC/releases/download/v0.1.0/EasyJLC-0.1.0-x86_64.AppImage
chmod +x EasyJLC-0.1.0-x86_64.AppImage
./EasyJLC-0.1.0-x86_64.AppImage
```

Requer `python3 >= 3.10` no sistema (presente por default na maioria das distros) — usado para criar um venv isolado para o `easyeda2kicad` na primeira execução.

### Linux — pacote `.deb` (Debian / Ubuntu / Mint / Pop!_OS)

```bash
wget https://github.com/<user>/EasyJLC/releases/download/v0.1.0/easyjlc_0.1.0_amd64.deb
sudo dpkg -i easyjlc_0.1.0_amd64.deb
# se faltar alguma dep:
sudo apt-get install -f
```

O app aparece no menu de aplicações; para desinstalar: `sudo apt remove easyjlc`.

### Windows

Binário `.exe` em preparação (Sprint 5 follow-up). Por enquanto, rode a partir do código-fonte — veja abaixo.

### A partir do código-fonte

```bash
git clone https://github.com/<user>/EasyJLC.git
cd EasyJLC
./scripts/run_dev.sh          # Linux / macOS
# ou
scripts\run_dev.bat           # Windows
```

Os scripts criam um venv em `.venv/`, instalam dependências de `requirements.txt` e executam `python -m easyjlc`.

---

## Primeiro uso

1. **Pasta de saída**: por padrão `~/Documents/EasyJLC`. Sobrescreva na aba **Download direto** se preferir a pasta do projeto KiCad (recomendado — facilita compartilhar o projeto sem perder componentes).
2. **easyeda2kicad**: na primeira execução o app provisiona um venv isolado (~30–60 s, só uma vez) em `~/.local/share/EasyJLC/easyeda2kicad-venv/`.
3. **Configurar KiCad**: a aba **Documentação** tem o passo-a-passo para adicionar a biblioteca baixada ao **Symbol Library Manager** e **Footprint Library Manager**, incluindo como usar `${KIPRJMOD}` para caminhos relativos ao projeto.

---

## Idiomas

Troque o idioma no menu dropdown à direita do header. O arquivo de catálogo fica em `easyjlc/resources/i18n/<lang>.json` — pt-BR é a chave identidade (strings pt-BR são as próprias chaves, sem necessidade de catálogo).

Para adicionar um idioma novo:

1. Copie `easyjlc/resources/i18n/en.json` para `<código>.json`.
2. Traduza os valores (mantenha placeholders como `{lcsc_id}`, `{stock:,}`, `{query}` intactos).
3. Adicione o código em `SUPPORTED_LANGUAGES` em `easyjlc/i18n.py`.

---

## Construindo seu próprio binário

```bash
./scripts/build_release.sh          # dist/easyjlc (onefile, ~24 MB)
./packaging/build_appimage.sh       # dist/EasyJLC-<v>-x86_64.AppImage
./packaging/build_deb.sh            # dist/easyjlc_<v>_amd64.deb
```

O `build_appimage.sh` espera `appimagetool` em `/tmp/appimagetool`. Baixe de [AppImage/appimagetool/releases](https://github.com/AppImage/appimagetool/releases) e dê `chmod +x`.

---

## Desenvolvimento

```bash
python -m pip install -e .[dev]
python -m pytest                     # 60 testes
python -m easyjlc                    # roda a GUI
```

### Estrutura

```
easyjlc/
├── app.py                 # ponto de entrada GUI
├── config.py              # paths XDG / AppData, logging
├── settings.py            # preferências persistentes
├── history.py             # histórico de downloads
├── i18n.py                # catálogo gettext-style
├── core/
│   ├── easyeda.py         # runner subprocess do easyeda2kicad
│   ├── jlc_api.py         # cliente REST JLCPCB/LCSC
│   ├── kicad_parse.py     # parser S-expr .kicad_sym / .kicad_mod
│   └── models.py
├── ui/                    # tabs: search, download, history, docs, log
└── resources/
    ├── icons/
    └── i18n/              # pt-BR.json, en.json, de.json
packaging/                 # specs PyInstaller + scripts AppImage/.deb
scripts/                   # run_dev.sh, build_release.sh
tests/                     # pytest
legacy/                    # scripts originais do SandKrux (referência)
```

### Princípios

- `core/` não importa `ui/` — facilita testes e um futuro CLI.
- `easyeda2kicad` é a engine de download oficial, invocada via subprocess num venv isolado gerido pelo app.
- Parser S-expr minimal para `.kicad_sym` (≥ KiCad 7) e `.kicad_mod` — suficiente para preview, sem dependência do KiCad instalado.

---

## Roadmap

Completo em [`PLAN.md`](PLAN.md). Resumo do que falta:

- [ ] Build Windows (`.exe`)
- [ ] Ícone oficial (atual é placeholder)
- [ ] Filtros na busca (categoria, pacote, faixa de estoque/preço)
- [ ] BOM loader (importar `.csv` KiCad e baixar em lote)
- [ ] Build macOS + CI GitHub Actions

---

## Créditos

- [**easyeda2kicad**](https://github.com/uPesy/easyeda2kicad.py) — engine de conversão EasyEDA → KiCad
- [**SandKrux/KiCad-Tools**](https://github.com/SandKrux/KiCad-Tools) — inspiração dos scripts originais em `legacy/`
- [**Import-LIB-KiCad-Plugin**](https://github.com/Steffen-W/Import-LIB-KiCad-Plugin) — referência de UX para busca paginada

---

## Licença

[GPL-3.0-or-later](LICENSE).
