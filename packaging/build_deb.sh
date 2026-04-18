#!/usr/bin/env bash
# Gera um pacote .deb a partir de dist/easyjlc (PyInstaller onefile).
#
# Saída: dist/easyjlc_<versão>_amd64.deb
# Instalação: sudo dpkg -i dist/easyjlc_0.1.0_amd64.deb
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VERSION="$(grep -m1 '^version' pyproject.toml | sed -E 's/.*"([^"]+)".*/\1/')"
PKGROOT="build/deb-root"
ICON="easyjlc/resources/icons/easyjlc.png"
BINARY="dist/easyjlc"

if [[ ! -x "$BINARY" ]]; then
    echo "Binário $BINARY não encontrado. Rode scripts/build_release.sh primeiro." >&2
    exit 1
fi

echo ">> Montando árvore .deb em $PKGROOT..."
rm -rf "$PKGROOT"
mkdir -p "$PKGROOT/DEBIAN" \
         "$PKGROOT/opt/easyjlc" \
         "$PKGROOT/usr/bin" \
         "$PKGROOT/usr/share/applications" \
         "$PKGROOT/usr/share/icons/hicolor/512x512/apps" \
         "$PKGROOT/usr/share/doc/easyjlc"

cp "$BINARY" "$PKGROOT/opt/easyjlc/easyjlc"
chmod 755 "$PKGROOT/opt/easyjlc/easyjlc"
ln -sf /opt/easyjlc/easyjlc "$PKGROOT/usr/bin/easyjlc"
cp "$ICON" "$PKGROOT/usr/share/icons/hicolor/512x512/apps/easyjlc.png"
cp LICENSE "$PKGROOT/usr/share/doc/easyjlc/copyright" 2>/dev/null || true

cat > "$PKGROOT/usr/share/applications/easyjlc.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=EasyJLC
Comment=Baixa símbolos e footprints KiCad do LCSC/JLCPCB
Exec=easyjlc
Icon=easyjlc
Terminal=false
Categories=Development;Electronics;
EOF

SIZE=$(du -sk "$PKGROOT" | cut -f1)
cat > "$PKGROOT/DEBIAN/control" <<EOF
Package: easyjlc
Version: ${VERSION}
Section: electronics
Priority: optional
Architecture: amd64
Depends: python3 (>= 3.10), python3-venv
Installed-Size: ${SIZE}
Maintainer: EasyJLC contributors <noreply@easyjlc.local>
Homepage: https://github.com/
Description: GUI para baixar símbolos/footprints KiCad via LCSC/JLCPCB
 EasyJLC é um aplicativo gráfico multiplataforma para buscar, pré-visualizar
 e baixar símbolos e footprints KiCad diretamente do catálogo LCSC/JLCPCB,
 com preço e estoque. Suporta pt-BR, inglês e alemão.
EOF

OUT="dist/easyjlc_${VERSION}_amd64.deb"
echo ">> dpkg-deb --build $PKGROOT $OUT"
dpkg-deb --root-owner-group --build "$PKGROOT" "$OUT"

echo
echo ".deb pronto: $OUT"
ls -lh "$OUT"
