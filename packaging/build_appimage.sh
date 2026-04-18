#!/usr/bin/env bash
# Gera um AppImage a partir de dist/easyjlc (PyInstaller onefile).
#
# Requer:
#   - dist/easyjlc já construído (rode scripts/build_release.sh antes)
#   - /tmp/appimagetool (baixado de github.com/AppImage/appimagetool)
#
# Saída: dist/EasyJLC-<versão>-x86_64.AppImage
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VERSION="$(grep -m1 '^version' pyproject.toml | sed -E 's/.*"([^"]+)".*/\1/')"
APPDIR="build/AppDir"
ICON="easyjlc/resources/icons/easyjlc.png"
BINARY="dist/easyjlc"
APPIMAGETOOL="${APPIMAGETOOL:-/tmp/appimagetool}"

if [[ ! -x "$BINARY" ]]; then
    echo "Binário $BINARY não encontrado. Rode scripts/build_release.sh primeiro." >&2
    exit 1
fi
if [[ ! -x "$APPIMAGETOOL" ]]; then
    echo "appimagetool não encontrado em $APPIMAGETOOL." >&2
    echo "Baixe de https://github.com/AppImage/appimagetool/releases" >&2
    exit 1
fi

echo ">> Montando AppDir em $APPDIR..."
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/share/applications" \
         "$APPDIR/usr/share/icons/hicolor/512x512/apps"

cp "$BINARY" "$APPDIR/usr/bin/easyjlc"
cp "$ICON" "$APPDIR/usr/share/icons/hicolor/512x512/apps/easyjlc.png"
cp "$ICON" "$APPDIR/easyjlc.png"          # AppImage raiz
ln -sf easyjlc.png "$APPDIR/.DirIcon"

cat > "$APPDIR/easyjlc.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=EasyJLC
Comment=Baixa símbolos e footprints KiCad do LCSC/JLCPCB
Exec=easyjlc
Icon=easyjlc
Terminal=false
Categories=Development;Electronics;
EOF
cp "$APPDIR/easyjlc.desktop" "$APPDIR/usr/share/applications/easyjlc.desktop"

cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/easyjlc" "$@"
EOF
chmod +x "$APPDIR/AppRun"

echo ">> Rodando appimagetool..."
OUT="dist/EasyJLC-${VERSION}-x86_64.AppImage"
ARCH=x86_64 "$APPIMAGETOOL" "$APPDIR" "$OUT"

echo
echo "AppImage pronto: $OUT"
ls -lh "$OUT"
