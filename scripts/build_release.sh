#!/usr/bin/env bash
# Build do binário PyInstaller do EasyJLC.
#
# Uso:
#     ./scripts/build_release.sh           # Linux onefile em dist/easyjlc
#
# Requer venv já provisionado (veja scripts/run_dev.sh).
set -euo pipefail

cd "$(dirname "$0")/.."

VENV=".venv"
if [[ ! -x "$VENV/bin/python" ]]; then
    echo "Venv $VENV não encontrado. Rode scripts/run_dev.sh antes." >&2
    exit 1
fi

"$VENV/bin/pip" install --quiet --upgrade pyinstaller

echo ">> Rodando testes..."
"$VENV/bin/python" -m pytest -q

echo ">> Limpando dist/ e build/ anteriores..."
rm -rf dist build

case "$(uname -s)" in
    Linux*)
        SPEC="packaging/easyjlc-linux.spec"
        ;;
    *)
        echo "SO não suportado por este script: $(uname -s)" >&2
        echo "No Windows, rode: .venv\\Scripts\\pyinstaller packaging\\easyjlc-windows.spec" >&2
        exit 1
        ;;
esac

echo ">> PyInstaller ($SPEC)..."
"$VENV/bin/pyinstaller" "$SPEC" --noconfirm

echo
echo "Binário pronto: dist/easyjlc"
ls -lh dist/easyjlc
