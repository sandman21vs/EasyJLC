# EasyJLC

Cross-platform GUI to search, preview, and download KiCad symbols + footprints directly from the **LCSC / JLCPCB** catalog, with price, stock, and download history.

Successor to the `jlc_downloader.py` / `.bat` scripts (preserved in [`legacy/`](legacy/)).

![License](https://img.shields.io/badge/license-GPL--3.0--or--later-blue) ![Python](https://img.shields.io/badge/python-3.10%2B-blue) ![Platform](https://img.shields.io/badge/linux%20%7C%20windows-x86__64-green) ![Languages](https://img.shields.io/badge/i18n-pt--BR%20%7C%20en%20%7C%20de-orange)

---

## Features

- **Search**: MPN, LCSC ID, or keyword. Paginated, with thumbnails, Basic/Extended badges, and stock/price sorting.
- **Search filters**: filter results by library type (Basic/Extended), package, minimum stock, and maximum price — applied instantly without a new API call.
- **Rendered KiCad preview**: symbol (pins, rectangles, polylines) and footprint (rotated pads, silkscreen per layer) drawn on a `tk.Canvas` with zoom and pan.
- **Full download**: symbol + footprint via `easyeda2kicad`, in an isolated venv managed by the app.
- **Price + stock** (JLCPCB API), with quantity price breaks and a direct link to the datasheet.
- **Persistent history**: re-download, open folder, copy LCSC ID.
- **Cross-platform default folder**: `~/Documents/EasyJLC` (via `platformdirs`).
- **Built-in Documentation tab**: step-by-step guide for pointing KiCad libraries to downloaded components.
- **Multi-language**: pt-BR, English, German — selectable in the header (applies on next start). Ready for more languages via JSON.
- **Light/dark/system theme** via CustomTkinter.

---

## Installation

### Linux — AppImage (recommended, any x86-64 distro)

```bash
wget https://github.com/sandman21vs/EasyJLC/releases/download/v0.1.0/EasyJLC-0.1.0-x86_64.AppImage
chmod +x EasyJLC-0.1.0-x86_64.AppImage
./EasyJLC-0.1.0-x86_64.AppImage
```

Requires `python3 >= 3.10` on the system (present by default on most distros) — used to create an isolated venv for `easyeda2kicad` on first run.

### Linux — `.deb` package (Debian / Ubuntu / Mint / Pop!_OS)

```bash
wget https://github.com/sandman21vs/EasyJLC/releases/download/v0.1.0/easyjlc_0.1.0_amd64.deb
sudo dpkg -i easyjlc_0.1.0_amd64.deb
# if dependencies are missing:
sudo apt-get install -f
```

The app appears in the application menu; to uninstall: `sudo apt remove easyjlc`.

### Windows

Download `easyjlc.exe` from the [latest release](https://github.com/sandman21vs/EasyJLC/releases/latest) and run it directly — no installation required.

### From source

```bash
git clone https://github.com/sandman21vs/EasyJLC.git
cd EasyJLC
./scripts/run_dev.sh          # Linux / macOS
# or
scripts\run_dev.bat           # Windows
```

The scripts create a venv in `.venv/`, install dependencies from `requirements.txt`, and run `python -m easyjlc`.

---

## First use

1. **Output folder**: defaults to `~/Documents/EasyJLC`. Override it in the **Direct Download** tab — using your KiCad project folder is recommended (makes it easy to share the project without losing components).
2. **easyeda2kicad**: on first run the app provisions an isolated venv (~30–60 s, once only) at `~/.local/share/EasyJLC/easyeda2kicad-venv/`.
3. **Configure KiCad**: the **Documentation** tab has a step-by-step guide for adding the downloaded library to the **Symbol Library Manager** and **Footprint Library Manager**, including how to use `${KIPRJMOD}` for project-relative paths.

---

## Languages

Switch the language in the dropdown on the right side of the header. Catalog files are at `easyjlc/resources/i18n/<lang>.json` — pt-BR is the identity key (pt-BR strings are the keys themselves, no catalog file needed).

To add a new language:

1. Copy `easyjlc/resources/i18n/en.json` to `<code>.json`.
2. Translate the values (keep placeholders like `{lcsc_id}`, `{stock:,}`, `{query}` intact).
3. Add the code to `SUPPORTED_LANGUAGES` in `easyjlc/i18n.py`.

---

## Building your own binary

```bash
./scripts/build_release.sh          # dist/easyjlc (onefile, ~24 MB)
./packaging/build_appimage.sh       # dist/EasyJLC-<v>-x86_64.AppImage
./packaging/build_deb.sh            # dist/easyjlc_<v>_amd64.deb
# Windows (run in the project root with .venv active):
python -m PyInstaller packaging/easyjlc-windows.spec --noconfirm
```

`build_appimage.sh` expects `appimagetool` at `/tmp/appimagetool`. Download it from [AppImage/appimagetool/releases](https://github.com/AppImage/appimagetool/releases) and `chmod +x`.

---

## Development

```bash
python -m pip install -e .[dev]
python -m pytest                     # 60 tests
python -m easyjlc                    # run the GUI
```

### Structure

```
easyjlc/
├── app.py                 # GUI entry point
├── config.py              # XDG / AppData paths, logging
├── settings.py            # persistent preferences
├── history.py             # download history
├── i18n.py                # gettext-style catalog
├── core/
│   ├── easyeda.py         # easyeda2kicad subprocess runner
│   ├── jlc_api.py         # JLCPCB/LCSC REST client
│   ├── kicad_parse.py     # S-expr parser for .kicad_sym / .kicad_mod
│   └── models.py
├── ui/                    # tabs: search, download, history, docs, log
└── resources/
    ├── icons/
    └── i18n/              # pt-BR.json, en.json, de.json
packaging/                 # PyInstaller specs + AppImage/.deb scripts
scripts/                   # run_dev.sh, build_release.sh
tests/                     # pytest
legacy/                    # original SandKrux scripts (reference)
```

### Principles

- `core/` does not import `ui/` — simplifies testing and a future CLI.
- `easyeda2kicad` is the official download engine, invoked via subprocess in an isolated venv managed by the app.
- Minimal S-expr parser for `.kicad_sym` (≥ KiCad 7) and `.kicad_mod` — sufficient for preview, no KiCad installation required.

---

## Roadmap

Full details in [`PLAN.md`](PLAN.md). What's left:

- [x] Windows build (`.exe`)
- [x] Search filters (category, package, stock/price range)
- [ ] Official icon (current is placeholder)
- [ ] BOM loader (import KiCad `.csv` and batch download)
- [ ] macOS build + GitHub Actions CI

---

## Credits

- [**easyeda2kicad**](https://github.com/uPesy/easyeda2kicad.py) — EasyEDA → KiCad conversion engine
- [**SandKrux/KiCad-Tools**](https://github.com/SandKrux/KiCad-Tools) — inspiration for the original scripts in `legacy/`
- [**Import-LIB-KiCad-Plugin**](https://github.com/Steffen-W/Import-LIB-KiCad-Plugin) — UX reference for paginated search

---

## License

[GPL-3.0-or-later](LICENSE).
