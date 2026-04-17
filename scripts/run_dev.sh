#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

cd "$PROJECT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 não encontrado no PATH." >&2
    exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "Criando virtualenv em $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip >/dev/null
python -m pip install -r "$PROJECT_DIR/requirements.txt"

exec python -m easyjlc "$@"
