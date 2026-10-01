"""Tokens do design system Sidekick OS.

Fonte única de cores, fontes e medidas do app, espelhando o frontmatter do
``DESIGN.md`` na raiz do projeto. Nenhum widget deve escrever um hex na mão:
leia daqui. Plugins e guias também podem importar este módulo (com fallback
para os valores do DESIGN.md quando rodarem fora do hub).
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QFont, QFontDatabase

# Neutros puxados para o roxo: harmonizam com o papel de parede vaporwave.
COLORS: dict[str, str] = {
    "canvas": "#120A24",
    "sunken": "#0B0716",
    "surface": "#161029",
    "surface-raised": "#211839",
    "hairline": "#352A54",
    "hairline-strong": "#4B3E72",
    "control-border": "#7465A0",
    "ink": "#F4F0FF",
    "ink-muted": "#BCB2DA",
    "ink-faint": "#9388B6",
    "primary": "#37F2FF",
    "primary-hover": "#7AF6FF",
    "on-primary": "#04131A",
    "primary-tint": "#123B4A",
    "brand": "#FF4FD8",
    "on-brand": "#1A0414",
    "success": "#B9FF43",
    "on-success": "#0B1400",
    "warning": "#FFC857",
    "danger": "#FF5C7A",
    "synth": "#7B3CFF",
    "synth-sun-top": "#FFD35C",
    "synth-sun-bottom": "#FF4FD8",
    "shadow-hard": "#000000",
}

# Papel de parede do "SO": fica fixo atrás das páginas; os painéis são janelas por cima.
# Texto solto sobre ele (título e subtítulo de página) fica no céu, a parte escura.
WALLPAPERS: dict[str, dict] = {
    "futurefunk": {"label": "Future funk", "top": "#1C0C3C", "mid": "#4A1777", "horizon": "#6A1C70",
                   "glow": 115, "grid": 80, "horizon_at": 0.78, "scanlines": True},
    "noite": {"label": "Noite roxa", "top": "#120A26", "mid": "#2A1050", "horizon": "#4A1660",
              "glow": 70, "grid": 50, "horizon_at": 0.80, "scanlines": True},
    "liso": {"label": "Liso", "flat": True},
}
DEFAULT_WALLPAPER = "futurefunk"

RADII = {"none": 0, "xs": 2, "sm": 4, "md": 6, "full": 9999}
SPACING = {"xxs": 4, "xs": 8, "sm": 12, "md": 16, "lg": 24, "xl": 32, "xxl": 48}

# Papel -> (família preferida embarcada, substitutas por plataforma)
FONT_STACKS: dict[str, tuple[str, ...]] = {
    "display": ("Chakra Petch", "Bahnschrift", "Avenir Next Condensed", "Segoe UI"),
    "body": ("IBM Plex Sans", "Segoe UI", "SF Pro Text", "Helvetica Neue"),
    "hud": ("VT323", "Consolas", "Menlo"),
    "mono": ("IBM Plex Mono", "Consolas", "Menlo"),
}

# Escala tipográfica (px, peso) — DESIGN.md, seção Typography.
TYPE = {
    "display": ("display", 32, 700),
    "heading": ("display", 22, 600),
    "title": ("display", 18, 600),
    "body": ("body", 14, 400),
    "body-strong": ("body", 14, 600),
    "caption": ("body", 12, 400),
    "button": ("body", 13, 600),
    "hud-label": ("hud", 20, 400),
    "numeric-lg": ("hud", 44, 400),
    "numeric-md": ("hud", 24, 400),
    "mono": ("mono", 12, 400),
}

PANEL_CHAMFER = 10
PANEL_SHADOW = 4
PANEL_TITLEBAR = 30

FONTS_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"

_resolved: dict[str, str] = {}
_fonts_loaded = False


def color(name: str, alpha: int = 255) -> QColor:
    """QColor de um token (``color("primary")``), com alfa opcional."""
    c = QColor(COLORS[name])
    if alpha != 255:
        c.setAlpha(alpha)
    return c


def hex_(name: str) -> str:
    return COLORS[name]


def load_fonts() -> None:
    """Registra as fontes embarcadas (uma vez). Precisa de um QGuiApplication."""
    global _fonts_loaded
    if _fonts_loaded:
        return
    _fonts_loaded = True
    if not FONTS_DIR.exists():
        return
    for file in sorted(FONTS_DIR.iterdir()):
        if file.suffix.lower() in {".ttf", ".otf"}:
            QFontDatabase.addApplicationFont(str(file))


def family(role: str) -> str:
    """Primeira família disponível para o papel (embarcada > substitutas)."""
    if role in _resolved:
        return _resolved[role]
    available = set(QFontDatabase.families())
    stack = FONT_STACKS[role]
    chosen = next((f for f in stack if f in available), stack[-1])
    _resolved[role] = chosen
    return chosen


def font(token: str, size: int | None = None, weight: int | None = None) -> QFont:
    """QFont de um papel tipográfico (``font("numeric-md")``)."""
    role, px, w = TYPE[token]
    f = QFont(family(role))
    f.setPixelSize(size or px)
    f.setWeight(QFont.Weight(weight or w))
    return f
