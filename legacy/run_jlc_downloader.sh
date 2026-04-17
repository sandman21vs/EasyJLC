#!/usr/bin/env bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

if command -v python3 >/dev/null 2>&1; then
    exec python3 "$SCRIPT_DIR/jlc_downloader.py"
fi

if command -v python >/dev/null 2>&1; then
    exec python "$SCRIPT_DIR/jlc_downloader.py"
fi

echo "Python nao encontrado no sistema."
read -r -p "Pressione Enter para fechar..."
