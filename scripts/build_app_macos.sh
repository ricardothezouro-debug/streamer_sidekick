#!/usr/bin/env bash
# Build do Streamer Sidekick como .app para macOS.
# Rode ESTE script em um Mac (o PyInstaller precisa da plataforma alvo).
#
#   chmod +x scripts/build_app_macos.sh
#   ./scripts/build_app_macos.sh
#
# Resultado: dist/"Streamer Sidekick.app"
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

VENV="${PROJECT_ROOT}/.venv"
PYTHON="${VENV}/bin/python"
SPEC="${PROJECT_ROOT}/packaging/streamer_sidekick_macos.spec"
BRAND="${PROJECT_ROOT}/src/streamer_sidekick/assets/brand"

if [ ! -x "$PYTHON" ]; then
  echo "Venv nao encontrado em ${PYTHON}."
  echo "Crie e instale as dependencias com:"
  echo "  python3 -m venv .venv"
  echo "  source .venv/bin/activate"
  echo "  pip install -r requirements.txt -r requirements-build.txt"
  exit 1
fi

# Gera o icone .icns a partir do PNG, se ainda nao existir e houver ferramentas.
ICNS="${BRAND}/app_icon.icns"
PNG="${BRAND}/app_icon.png"
if [ ! -f "$ICNS" ] && [ -f "$PNG" ] && command -v iconutil >/dev/null 2>&1; then
  echo "Gerando ${ICNS} a partir de app_icon.png..."
  ICONSET="$(mktemp -d)/app_icon.iconset"
  mkdir -p "$ICONSET"
  for size in 16 32 64 128 256 512; do
    sips -z "$size" "$size" "$PNG" --out "${ICONSET}/icon_${size}x${size}.png" >/dev/null
    double=$((size * 2))
    sips -z "$double" "$double" "$PNG" --out "${ICONSET}/icon_${size}x${size}@2x.png" >/dev/null
  done
  iconutil -c icns "$ICONSET" -o "$ICNS"
fi

"$PYTHON" -m PyInstaller --noconfirm --clean "$SPEC"

echo ""
echo "Build concluido:"
echo "  ${PROJECT_ROOT}/dist/Streamer Sidekick.app"
echo ""
echo "Na primeira execucao, conceda permissao em:"
echo "  Ajustes do Sistema > Privacidade e Seguranca > Acessibilidade"
echo "para os atalhos globais funcionarem."
