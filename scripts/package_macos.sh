#!/usr/bin/env bash
# Empacota o .app buildado num zip pronto para a Release.
# Rode DEPOIS de scripts/build_app_macos.sh.
#
#   ./scripts/package_macos.sh   ->  release/StreamerSidekick-<versao>-macos.zip
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

APP="dist/Streamer Sidekick.app"
if [ ! -d "$APP" ]; then
  echo "Build nao encontrado. Rode primeiro: ./scripts/build_app_macos.sh" >&2
  exit 1
fi

VERSION="$(sed -n 's/^__version__ = "\(.*\)"$/\1/p' src/streamer_sidekick/__init__.py)"
if [ -z "$VERSION" ]; then
  echo "Nao foi possivel ler __version__" >&2
  exit 1
fi

mkdir -p release
ZIP="release/StreamerSidekick-${VERSION}-macos.zip"
rm -f "$ZIP"

# ditto (e nao zip): preserva symlinks, bits de execucao e metadados do bundle.
# --keepParent mantem o proprio "Streamer Sidekick.app" como raiz do zip, que e
# o que o updater espera encontrar.
ditto -c -k --sequesterRsrc --keepParent "$APP" "$ZIP"

echo ""
echo "Pacote criado:"
echo "  ${PROJECT_ROOT}/${ZIP}"
