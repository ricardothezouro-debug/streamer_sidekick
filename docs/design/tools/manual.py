"""Manual de identidade Sidekick OS (PDF A4 paisagem), desenhado com Qt.

Cada página é uma função draw(p, n) num espaço lógico de 1600 x 1131.
O mesmo desenho vai para PNG (revisão) e para PDF vetorial. Tokens: DESIGN.md.

Uso (na raiz do repo, com o venv do projeto):
    python docs/design/tools/manual.py pdf docs/design/sidekick-os-manual.pdf
    python docs/design/tools/manual.py png <pasta> [números das páginas]

Fontes: Chakra Petch, IBM Plex Sans, IBM Plex Mono e VT323 (OFL, Google Fonts).
Procuradas em src/streamer_sidekick/assets/fonts ou na pasta da variável SIDEKICK_FONTS.
"""
import os
import glob
import sys
from pathlib import Path

from PySide6.QtCore import QMarginsF, QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QFontDatabase, QImage, QLinearGradient,
                           QPageLayout, QPageSize, QPainter, QPainterPath, QPdfWriter,
                           QPen, QPixmap)
from PySide6.QtWidgets import QApplication

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
FONTS = Path(os.environ.get("SIDEKICK_FONTS", REPO / "src/streamer_sidekick/assets/fonts"))
BRAND = REPO / "src/streamer_sidekick/assets/brand"
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(HERE))
import sidekick_icons as ICONS  # noqa: E402

W, H, M = 1600, 1131, 80

C = {
    "canvas": "#090A12", "sunken": "#06070C", "surface": "#0F1320", "surface-raised": "#161B2C",
    "hairline": "#262E42", "hairline-strong": "#3A4560", "control-border": "#5C6886",
    "ink": "#EEF2FF", "ink-muted": "#A3ACC2", "ink-faint": "#7A84A0",
    "primary": "#37F2FF", "primary-hover": "#7AF6FF", "on-primary": "#04131A", "primary-tint": "#0E3640",
    "brand": "#FF4FD8", "on-brand": "#1A0414", "success": "#B9FF43", "on-success": "#0B1400",
    "warning": "#FFC857", "danger": "#FF5C7A", "synth": "#7B3CFF",
    "synth-sun-top": "#FFD35C", "synth-sun-bottom": "#FF4FD8",
}


def col(key, alpha=255):
    c = QColor(C.get(key, key))
    c.setAlpha(alpha)
    return c


FAMILY = {"display": "Chakra Petch", "body": "IBM Plex Sans", "hud": "VT323", "mono": "IBM Plex Mono"}
WEIGHT = {400: QFont.Weight.Normal, 500: QFont.Weight.Medium, 600: QFont.Weight.DemiBold, 700: QFont.Weight.Bold}


def F(fam, px, w=400, ls=0.0):
    f = QFont(FAMILY.get(fam, fam))
    f.setPixelSize(max(1, int(round(px))))
    f.setWeight(WEIGHT[w])
    f.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    if ls:  # percentual: igual na tela e no PDF (absoluto muda com o DPI)
        f.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 100 + 100 * ls / max(1, px))
    return f


L, R, CENTER = Qt.AlignmentFlag.AlignLeft, Qt.AlignmentFlag.AlignRight, Qt.AlignmentFlag.AlignHCenter


def T(p, x, y, s, f, color, w=None, align=L, h=None):
    """Uma linha. Com largura, elide com reticências."""
    p.setFont(f)
    p.setPen(col(color) if isinstance(color, str) else color)
    fm = p.fontMetrics()
    if w is not None:
        s = fm.elidedText(s, Qt.TextElideMode.ElideRight, int(w))
    ww = w if w is not None else fm.horizontalAdvance(s) + 6
    p.drawText(QRectF(x, y, ww, h or fm.height()), int(align | Qt.AlignmentFlag.AlignVCenter), s)
    return fm.horizontalAdvance(s)


def adv(p, s, f):
    p.setFont(f)
    return p.fontMetrics().horizontalAdvance(s)


def P(p, x, y, w, s, f, color, lh=1.5):
    """Parágrafo com quebra de linha. Devolve a altura usada."""
    p.setFont(f)
    p.setPen(col(color) if isinstance(color, str) else color)
    fm = p.fontMetrics()
    step = f.pixelSize() * lh
    yy = y
    for block in s.split("\n"):
        cur = ""
        for word in block.split(" "):
            test = (cur + " " + word).strip()
            if cur and fm.horizontalAdvance(test) > w:
                p.drawText(QPointF(x, yy + fm.ascent()), cur)
                yy += step
                cur = word
            else:
                cur = test
        p.drawText(QPointF(x, yy + fm.ascent()), cur)
        yy += step
    return yy - y


def bullets(p, x, y, w, items, f, color, dot="primary", gap=10):
    yy = y
    for it in items:
        p.setBrush(col(dot))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(QRectF(x, yy + f.pixelSize() * 0.55, 6, 6))
        yy += P(p, x + 18, yy, w - 18, it, f, color) + gap
    return yy - y


# ---------------------------------------------------------------- imagens
_cache = {}


def pix(name):
    if name not in _cache:
        _cache[name] = QPixmap(str(BRAND / name))
    return _cache[name]


def icon(icon_id, size=128):
    key = f"icon:{icon_id}:{size}"
    if key not in _cache:
        from streamer_sidekick.ui.components import neon_qicon
        _cache[key] = neon_qicon(icon_id, size).pixmap(size, size)
    return _cache[key]


def ui_icon(p, name, x, y, size=24, color="ink-muted"):
    ICONS.draw_ui(p, name, x, y, size, col(color))


def brand_icon(p, name, x, y, size=48, main=None, accent=None, grid=False):
    ICONS.draw_brand(p, name, x, y, size, lambda k: col(k), main, accent, grid)


def draw_pix(p, pm, r: QRectF, keep=True):
    if keep:
        s = min(r.width() / pm.width(), r.height() / pm.height())
        w, h = pm.width() * s, pm.height() * s
        r = QRectF(r.left() + (r.width() - w) / 2, r.top() + (r.height() - h) / 2, w, h)
    p.drawPixmap(r, pm, QRectF(pm.rect()))
    return r


def tinted(pm, color):
    out = QPixmap(pm.size())
    out.fill(Qt.GlobalColor.transparent)
    q = QPainter(out)
    q.drawPixmap(0, 0, pm)
    q.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    q.fillRect(out.rect(), QColor(color))
    q.end()
    return out


# ---------------------------------------------------------------- contraste
def _lum(h):
    r, g, b = [int(h.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(a, b):
    la, lb = sorted([_lum(C.get(a, a)), _lum(C.get(b, b))], reverse=True)
    return (la + 0.05) / (lb + 0.05)


# ---------------------------------------------------------------- componentes
def chamfer_path(r: QRectF, ch=10.0):
    path = QPainterPath()
    path.moveTo(r.left(), r.top())
    path.lineTo(r.right() - ch, r.top())
    path.lineTo(r.right(), r.top() + ch)
    path.lineTo(r.right(), r.bottom())
    path.lineTo(r.left(), r.bottom())
    path.closeSubpath()
    return path


def panel_window(p, r, title="", meta="", featured=False, titlebar=True, shadow=True):
    if shadow:
        p.fillPath(chamfer_path(r.translated(4, 4)), QColor(0, 0, 0, 178))
    path = chamfer_path(r)
    p.fillPath(path, col("surface"))
    if titlebar:
        bar = QRectF(r.left(), r.top(), r.width(), 30)
        p.fillPath(chamfer_path(bar), col("surface-raised"))
        p.setPen(QPen(col("hairline"), 1))
        p.drawLine(QPointF(bar.left(), bar.bottom()), QPointF(bar.right(), bar.bottom()))
    p.setBrush(Qt.BrushStyle.NoBrush)
    if featured:
        p.setPen(QPen(col("primary", 55), 7))
        p.drawPath(path)
        p.setPen(QPen(col("primary"), 1.2))
        p.drawPath(path)
        p.fillRect(QRectF(r.left(), r.top(), r.width() - 10, 2), col("brand"))
    else:
        p.setPen(QPen(col("hairline"), 1))
        p.drawPath(path)
    if titlebar and title:
        T(p, r.left() + 12, r.top() + 2, title.upper(), F("hud", 22, ls=1.5), "ink-muted", h=28)
    if titlebar and meta:
        f = F("hud", 22, ls=1)
        T(p, r.right() - 18 - adv(p, meta, f), r.top() + 2, meta, f, "ink-faint", h=28)
    return QRectF(r.left() + 16, r.top() + (46 if titlebar else 16), r.width() - 32, r.height() - (62 if titlebar else 32))


def focus_ring(p, r):
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(col("primary"), 2))
    p.drawRoundedRect(r.adjusted(-4, -4, 4, 4), 6, 6)


def button(p, r, label, kind="secondary", state="rest"):
    f = F("body", 14, 600)
    rr = r.translated(0, 1) if state == "pressed" else r
    if kind == "primary":
        bg = {"hover": "primary-hover", "disabled": "hairline"}.get(state, "primary")
        fg = "ink-faint" if state == "disabled" else "on-primary"
        if state not in ("pressed", "disabled"):
            p.fillRect(r.translated(0, 2), col("primary-tint"))
        p.setBrush(col(bg))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(rr, 4, 4)
        T(p, rr.left(), rr.top(), label, f, fg, rr.width(), CENTER, rr.height())
    elif kind == "ghost":
        fg = "ink-faint" if state == "disabled" else ("primary-hover" if state == "hover" else "primary")
        if state == "hover":
            p.setBrush(col("surface-raised"))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(rr, 4, 4)
        T(p, rr.left(), rr.top(), label, f, fg, rr.width(), CENTER, rr.height())
    elif kind == "danger":
        fg = "ink-faint" if state == "disabled" else "danger"
        p.setBrush(col("danger", 30) if state == "hover" else Qt.BrushStyle.NoBrush)
        p.setPen(QPen(col(fg), 1))
        p.drawRoundedRect(rr, 4, 4)
        T(p, rr.left(), rr.top(), label, f, fg, rr.width(), CENTER, rr.height())
    else:
        border = "primary" if state == "hover" else "hairline-strong"
        fg = "ink-faint" if state == "disabled" else "ink"
        p.setBrush(col("surface-raised") if state != "disabled" else col("surface"))
        p.setPen(QPen(col(border), 1))
        p.drawRoundedRect(rr, 4, 4)
        T(p, rr.left(), rr.top(), label, f, fg, rr.width(), CENTER, rr.height())
    if state == "focus":
        focus_ring(p, r)


def input_field(p, x, y, w, label, value="", placeholder="", state="rest", error=""):
    T(p, x, y, label, F("body", 14, 600), "ink" if state != "disabled" else "ink-faint")
    r = QRectF(x, y + 26, w, 38)
    border = {"focus": "primary", "error": "danger", "disabled": "hairline"}.get(state, "control-border")
    p.setBrush(col("sunken") if state != "disabled" else col("surface"))
    p.setPen(QPen(col(border), 1.4 if state in ("focus", "error") else 1))
    p.drawRoundedRect(r, 4, 4)
    if value:
        T(p, x + 12, r.top(), value, F("body", 14), "ink", w - 24, h=r.height())
        if state == "focus":
            vx = x + 12 + adv(p, value, F("body", 14)) + 2
            p.fillRect(QRectF(vx, r.top() + 10, 1.5, 18), col("primary"))
    else:
        T(p, x + 12, r.top(), placeholder, F("body", 14), "ink-faint", w - 24, h=r.height())
    if error:
        T(p, x, r.bottom() + 6, error, F("body", 12), "danger", w)
    return r


def chip(p, x, y, label, dot, h=24, pulse=False):
    f = F("body", 13)
    w = adv(p, label, f) + 34
    r = QRectF(x, y, w, h)
    p.setBrush(col("surface-raised"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(r, h / 2, h / 2)
    if pulse:
        p.setBrush(col(dot, 70))
        p.drawEllipse(QPointF(x + 13, y + h / 2), 7.5, 7.5)
    p.setBrush(col(dot))
    p.drawEllipse(QPointF(x + 13, y + h / 2), 4, 4)
    T(p, x + 23, y, label, f, "ink-muted", h=h)
    return w


def badge(p, x, y, label, kind):
    f = F("hud", 20, ls=1.2)
    w = adv(p, label, f) + 16
    r = QRectF(x, y, w, 24)
    if kind in ("live", "trophy"):
        p.setBrush(col("brand" if kind == "live" else "success"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, 2, 2)
        T(p, x, y, label, f, "on-brand" if kind == "live" else "on-success", w, CENTER, 24)
    else:
        c = "warning" if kind == "missable" else "hairline-strong"
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(col(c), 1))
        p.drawRoundedRect(r, 2, 2)
        T(p, x, y, label, f, "warning" if kind == "missable" else "ink-muted", w, CENTER, 24)
    return w


def segmented(p, x, y, done, total, segs=20, w=12, h=16, gap=3):
    filled = round(segs * done / total) if total else 0
    for i in range(segs):
        r = QRectF(x + i * (w + gap), y, w, h)
        if i < filled:
            p.fillRect(r.adjusted(-1.5, -1.5, 1.5, 1.5), col("success", 45))
            p.fillRect(r, col("success"))
        else:
            p.fillRect(r, col("hairline"))
    return segs * (w + gap) - gap


def synth(p, r: QRectF, cx=0.5, sun=0.42, horizon=0.62, sky_top="sunken", border=True):
    p.save()
    p.setClipRect(r)
    hy = r.top() + r.height() * horizon
    sky = QLinearGradient(0, r.top(), 0, hy)
    sky.setColorAt(0, col(sky_top))
    sky.setColorAt(1, col("synth", 120))
    p.fillRect(QRectF(r.left(), r.top(), r.width(), hy - r.top()), sky)
    x0, rad = r.left() + r.width() * cx, r.height() * sun
    sun_g = QLinearGradient(0, hy - rad, 0, hy)
    sun_g.setColorAt(0, col("synth-sun-top"))
    sun_g.setColorAt(1, col("synth-sun-bottom"))
    p.setBrush(sun_g)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPie(QRectF(x0 - rad, hy - rad, rad * 2, rad * 2), 0, 180 * 16)
    sun_clip = QPainterPath()
    sun_clip.moveTo(x0, hy)
    sun_clip.arcTo(QRectF(x0 - rad, hy - rad, rad * 2, rad * 2), 0, 180)
    sun_clip.closeSubpath()
    p.save()
    p.setClipPath(sun_clip, Qt.ClipOperation.IntersectClip)
    for i in range(5):  # cortes horizontais, mais grossos perto do horizonte
        t = hy - rad * 0.52 + i * rad * 0.105
        p.fillRect(QRectF(x0 - rad, t, rad * 2, rad * (0.018 + i * 0.012)), sky)
    p.restore()
    p.fillRect(QRectF(r.left(), hy, r.width(), r.bottom() - hy), col("sunken"))
    p.setPen(QPen(col("primary", 95), max(1.0, r.height() / 220)))
    p.drawLine(QPointF(r.left(), hy), QPointF(r.right(), hy))
    span = r.width() / 9
    for i in range(-22, 23):
        p.drawLine(QPointF(x0 + i * span * 0.12, hy), QPointF(x0 + i * span, r.bottom()))
    y, step = hy, r.height() * 0.018
    while y < r.bottom():
        p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
        y += step
        step *= 1.42
    p.restore()
    if border:
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(col("hairline"), 1))
        p.drawRect(r)


def module_card(p, r, icon_pm, title, desc, status, dot, hover=False, max_lines=2):
    p.setBrush(col("surface"))
    p.setPen(QPen(col("hairline-strong" if hover else "hairline"), 1))
    p.drawRoundedRect(r, 4, 4)
    ic = QRectF(r.left() + 14, r.top() + 14, 56, 56)
    p.setBrush(col("sunken"))
    p.setPen(QPen(col("hairline-strong"), 1))
    p.drawRoundedRect(ic, 6, 6)
    if isinstance(icon_pm, str):  # ícone de marca em pixel, 48 px dentro do quadrado de 56
        brand_icon(p, icon_pm, ic.left() + 4, ic.top() + 4, 48)
    elif icon_pm is not None:
        draw_pix(p, icon_pm, ic.adjusted(6, 6, -6, -6))
    tx = ic.right() + 14
    tw = r.right() - tx - 14
    T(p, tx, r.top() + 14, title, F("display", 19, 600), "ink", tw)
    f = F("body", 13)
    p.setFont(f)
    fm = p.fontMetrics()
    lines, cur = [], ""
    for wd in desc.split():
        t = (cur + " " + wd).strip()
        if cur and fm.horizontalAdvance(t) > tw:
            lines.append(cur)
            cur = wd
        else:
            cur = t
    lines.append(cur)
    if len(lines) > max_lines:
        keep = lines[:max_lines - 1]
        lines = keep + [fm.elidedText(" ".join(lines[max_lines - 1:]), Qt.TextElideMode.ElideRight, int(tw))]
    for i, ln in enumerate(lines):
        T(p, tx, r.top() + 42 + i * 19, ln, f, "ink-muted")
    chip(p, r.left() + 16, r.bottom() - 38, status, dot)
    button(p, QRectF(r.right() - 76, r.bottom() - 42, 62, 32), "Abrir", "ghost")


def nav_item(p, r, label, icon_id, state="rest"):
    if state in ("hover", "active"):
        p.setBrush(col("surface-raised"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, 4, 4)
    if state == "active":
        p.fillRect(QRectF(r.left(), r.top() + 9, 3, r.height() - 18), col("brand"))
    color = {"active": "primary", "hover": "ink"}.get(state, "ink-muted")
    ui_icon(p, icon_id, r.left() + 16, r.top() + (r.height() - 24) / 2, 24, color)
    T(p, r.left() + 50, r.top(), label, F("body", 15, 600), "ink" if state != "rest" else "ink-muted", h=r.height())


def tab(p, r, label, active=False):
    T(p, r.left(), r.top(), label, F("body", 14, 600), "ink" if active else "ink-muted", r.width(), CENTER, r.height() - 2)
    p.fillRect(QRectF(r.left(), r.bottom() - 2, r.width(), 2), col("primary") if active else col("hairline"))


def callout(p, r, kind, title, body):
    color = {"info": "primary", "warning": "warning", "danger": "danger"}[kind]
    p.setBrush(col("surface-raised"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(r, 2, 2)
    p.fillRect(QRectF(r.left(), r.top(), 3, r.height()), col(color))
    T(p, r.left() + 16, r.top() + 10, title, F("body", 14, 600), color)
    P(p, r.left() + 16, r.top() + 34, r.width() - 32, body, F("body", 13), "ink-muted", 1.45)


def checkbox(p, x, y, checked):
    r = QRectF(x, y, 20, 20)
    if checked:
        p.setBrush(col("success"))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(r, 3, 3)
        p.setPen(QPen(col("on-success"), 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        path = QPainterPath(QPointF(x + 5, y + 10.5))
        path.lineTo(x + 8.5, y + 14)
        path.lineTo(x + 15, y + 6.5)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
    else:
        p.setBrush(col("sunken"))
        p.setPen(QPen(col("control-border"), 1.2))
        p.drawRoundedRect(r, 3, 3)


def marker(p, x, y, n):
    p.setBrush(col("brand"))
    p.setPen(QPen(col("canvas"), 2))
    p.drawEllipse(QPointF(x, y), 15, 15)
    T(p, x - 15, y - 15, str(n), F("hud", 24), "on-brand", 30, CENTER, 30)


def x_mark(p, x, y, ok=False):
    p.setBrush(col("success" if ok else "danger"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QPointF(x, y), 13, 13)
    p.setPen(QPen(col("on-success" if ok else "on-brand"), 2.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    if ok:
        path = QPainterPath(QPointF(x - 5.5, y + 0.5))
        path.lineTo(x - 1.5, y + 4.5)
        path.lineTo(x + 6, y - 4)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
    else:
        p.drawLine(QPointF(x - 5, y - 5), QPointF(x + 5, y + 5))
        p.drawLine(QPointF(x + 5, y - 5), QPointF(x - 5, y + 5))


# ---------------------------------------------------------------- moldura
SECTIONS = []


def frame(p, n, section):
    p.fillRect(QRectF(0, 0, W, H), col("canvas"))
    T(p, M, 34, "SIDEKICK OS  ·  MANUAL DE IDENTIDADE", F("hud", 22, ls=2), "ink-faint")
    f = F("hud", 22, ls=2)
    T(p, W - M - adv(p, section.upper(), f), 34, section.upper(), f, "primary")
    p.setPen(QPen(col("hairline"), 1))
    p.drawLine(QPointF(M, 70), QPointF(W - M, 70))
    T(p, M, H - 56, "Streamer Sidekick", F("body", 13), "ink-faint")
    num = f"{n:02d} / {len(PAGES):02d}"
    f2 = F("hud", 26, ls=1)
    T(p, W - M - adv(p, num, f2), H - 62, num, f2, "ink-muted")


def heading(p, title, lead="", y=104, w=900):
    T(p, M, y, title, F("display", 54, 700), "ink")
    if lead:
        return y + 88 + P(p, M, y + 82, w, lead, F("body", 20), "ink-muted", 1.45)
    return y + 84


def label(p, x, y, s, color="ink-faint"):
    T(p, x, y, s.upper(), F("hud", 22, ls=1.6), color)


# ---------------------------------------------------------------- páginas
def page_cover(p, n):
    p.fillRect(QRectF(0, 0, W, H), col("canvas"))
    synth(p, QRectF(0, 0, W, H), cx=0.74, sun=0.27, horizon=0.66, sky_top="canvas", border=False)
    draw_pix(p, pix("brand_logo.png"), QRectF(M, 86, 420, 128))
    T(p, M - 6, 300, "Sidekick OS", F("display", 140, 700), "ink")
    P(p, M, 470, 760, "Manual de identidade visual do Streamer Sidekick", F("body", 30), "ink-muted", 1.3)
    T(p, M, 560, "VERSÃO 1.1  ·  OUTUBRO DE 2026", F("hud", 32, ls=3), "primary")
    T(p, M, 612, "Fonte da verdade: DESIGN.md", F("body", 16), "ink-muted")


def page_essence(p, n):
    frame(p, n, "Essência")
    y = heading(p, "O SO de bolso de um streamer gamer",
                "O Streamer Sidekick é usado durante a live, com o jogo aberto e a atenção dividida. "
                "A interface se apaga e só o que importa acende. A personalidade vem da metáfora de um "
                "sistema operacional retrô: cada bloco é uma janela, os números aparecem num display de "
                "terminal e o progresso das platinas avança em blocos, como uma barra de vida.", w=1100)
    principles = [
        ("A interface se apaga", "brilho é exceção",
         "Fundo escuro e calmo. Só três coisas podem brilhar: o painel em destaque (um por tela), "
         "o progresso e o indicador ao vivo."),
        ("Cada bloco é uma janela", "painel-janela",
         "Seções são janelas com barra de título em fonte VCR, canto chanfrado e sombra dura. "
         "Elas substituem a borda neon em tudo."),
        ("Cor com papel", "1 cor = 1 função",
         "Ciano é agir. Rosa é a marca e o ao vivo. Limão é progresso e conquista. "
         "Roxo é só tinta da arte synthwave."),
        ("Synthwave é tempero", "não é prato",
         "Sol listrado, grid em perspectiva e roxo aparecem no Início, no onboarding, "
         "nas telas vazias e no Sobre. Nunca atrás de texto longo."),
    ]
    cw, ch = (W - 2 * M - 32) / 2, 236
    for i, (t, meta, body) in enumerate(principles):
        x = M + (i % 2) * (cw + 32)
        yy = y + 18 + (i // 2) * (ch + 32)
        inner = panel_window(p, QRectF(x, yy, cw, ch), t, meta)
        T(p, inner.left(), inner.top() - 2, t, F("display", 28, 600), "ink")
        P(p, inner.left(), inner.top() + 50, inner.width(), body, F("body", 19), "ink-muted", 1.5)
    yb = y + 18 + 2 * (ch + 32) + 12
    label(p, M, yb, "De onde vem")
    infl = [("SO retrô vaporwave", "painéis-janela, fonte VCR, progresso em blocos"),
            ("HUD de RPG escuro", "contenção, um destaque por vez, progresso como XP"),
            ("Paleta cyberpunk", "neon em fundo preto, com papel para cada cor")]
    iw = (W - 2 * M) / 3
    for i, (a, b) in enumerate(infl):
        T(p, M + i * iw, yb + 32, a, F("display", 20, 600), "ink")
        T(p, M + i * iw, yb + 64, b, F("body", 17), "ink-muted", iw - 30)


def page_logo(p, n):
    frame(p, n, "Logo")
    y = heading(p, "Logo", "O logo combina o robô sidekick (antena, visor e headset) com o nome em duas cores. "
                           "Ele vive na barra lateral e não se repete na área de conteúdo.", w=1000)
    big = QRectF(M, y + 20, 860, 380)
    p.fillRect(big, col("surface"))
    lr = draw_pix(p, pix("brand_logo.png"), big.adjusted(150, 110, -150, -110))
    pad = lr.height() * 0.25
    zone = lr.adjusted(-pad, -pad, pad, pad)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(col("brand"), 1.2, Qt.PenStyle.DashLine))
    p.drawRect(zone)
    p.setPen(QPen(col("ink-faint"), 1, Qt.PenStyle.DotLine))
    p.drawRect(lr)
    T(p, zone.left(), zone.bottom() + 12, "área de proteção = 1/4 da altura do logo em toda a volta",
      F("body", 14), "ink-muted")
    label(p, big.left() + 16, big.top() + 14, "Principal sobre surface")

    rx = M + 900
    label(p, rx, y + 20, "Ícone do app")
    draw_pix(p, pix("app_icon.png"), QRectF(rx, y + 56, 150, 150))
    label(p, rx + 190, y + 20, "Símbolo")
    p.fillRect(QRectF(rx + 190, y + 56, 150, 150), col("sunken"))
    draw_pix(p, pix("brand_icon.png"), QRectF(rx + 210, y + 76, 110, 110))
    label(p, rx, y + 236, "Sobre sunken (barra lateral)")
    sb = QRectF(rx, y + 272, 440, 128)
    p.fillRect(sb, col("sunken"))
    draw_pix(p, pix("brand_logo.png"), sb.adjusted(40, 30, -40, -30))

    yy = y + 436
    label(p, M, yy, "Tamanho mínimo")
    T(p, M, yy + 32, "Logo: 120 px de largura na tela ou 30 mm impresso.  Ícone: 16 px.", F("body", 16), "ink-muted")
    label(p, M, yy + 84, "Não faça", "danger")
    tiles = ["Esticar ou achatar", "Fundo claro", "Sobre a arte synthwave", "Recolorir"]
    tw = (W - 2 * M - 3 * 24) / 4
    th = 180
    for i, cap in enumerate(tiles):
        r = QRectF(M + i * (tw + 24), yy + 120, tw, th)
        if i == 1:
            p.fillRect(r, QColor("#EEF2FF"))
        elif i == 2:
            synth(p, r, cx=0.5, sun=0.5, horizon=0.75)
        else:
            p.fillRect(r, col("surface"))
        inner = r.adjusted(40, 50, -40, -60)
        if i == 0:
            draw_pix(p, pix("brand_logo.png"), QRectF(inner.left() + 30, inner.top() - 10, inner.width() - 60, inner.height() + 20), keep=False)
        elif i == 3:
            draw_pix(p, tinted(pix("brand_logo.png"), C["success"]), inner)
        else:
            draw_pix(p, pix("brand_logo.png"), inner)
        x_mark(p, r.right() - 22, r.top() + 22)
        T(p, r.left(), r.bottom() + 10, cap, F("body", 15, 600), "ink-muted")


def swatch_big(p, r, key, name, papel, use, avoid):
    top = QRectF(r.left(), r.top(), r.width(), 250)
    p.fillRect(top, col(key))
    on = {"primary": "on-primary", "brand": "on-brand", "success": "on-success", "synth": "ink"}[key]
    T(p, top.left() + 20, top.top() + 18, name, F("display", 34, 700), on)
    T(p, top.left() + 20, top.top() + 62, papel, F("body", 16, 600), on)
    T(p, top.left() + 20, top.bottom() - 52, C[key], F("hud", 34), on)
    rgb = QColor(C[key])
    T(p, top.left() + 20, top.bottom() - 24, f"RGB {rgb.red()} {rgb.green()} {rgb.blue()}", F("body", 13), on)
    body = QRectF(r.left(), top.bottom(), r.width(), r.height() - 250)
    p.fillRect(body, col("surface"))
    T(p, body.left() + 20, body.top() + 16, "{colors." + key + "}", F("mono", 13), "ink-faint")
    label(p, body.left() + 20, body.top() + 50, "Use em", "success")
    h = P(p, body.left() + 20, body.top() + 82, body.width() - 40, use, F("body", 17), "ink-muted", 1.45)
    label(p, body.left() + 20, body.top() + 96 + h, "Não use em", "danger")
    P(p, body.left() + 20, body.top() + 130 + h, body.width() - 40, avoid, F("body", 17), "ink-muted", 1.45)


def page_colors(p, n):
    frame(p, n, "Cores")
    y = heading(p, "Cores com papel", "Quatro cores de marca, cada uma com uma única função. "
                                       "Se uma cor não tem papel, ela não entra.")
    data = [("primary", "Ciano", "Ação", "botão primário, foco, aba ativa, links, painel em destaque", "texto corrido e decoração"),
            ("brand", "Rosa", "Marca e ao vivo", "logo, item de navegação ativo, ao vivo e gravando, faixa do destaque", "botões e estados de erro"),
            ("success", "Limão", "Progresso e conquista", "barras de progresso, troféu obtido, concluído, adicionar plugin", "texto longo e fundos grandes"),
            ("synth", "Roxo", "Tinta synthwave", "arte synthwave, onboarding, telas vazias", "qualquer controle interativo")]
    cw = (W - 2 * M - 3 * 24) / 4
    for i, d in enumerate(data):
        swatch_big(p, QRectF(M + i * (cw + 24), y + 16, cw, 660), *d)


def page_neutrals(p, n):
    frame(p, n, "Cores")
    y = heading(p, "Superfícies, texto e semânticas",
                "Um fundo quase preto azulado em quatro níveis, mais as bordas. Quanto mais alto o nível, mais clara a superfície.", w=1100)
    label(p, M, y + 10, "Escala de superfície")
    ramp = [("sunken", "barra lateral, campos"), ("canvas", "fundo da janela"), ("surface", "painéis e cards"),
            ("surface-raised", "barra de título, hover"), ("hairline", "divisórias, borda"),
            ("hairline-strong", "botão secundário"), ("control-border", "borda de campo (3,3:1)")]
    rw = (W - 2 * M) / len(ramp)
    for i, (k, u) in enumerate(ramp):
        r = QRectF(M + i * rw, y + 44, rw, 150)
        p.fillRect(r, col(k))
        if i:
            p.setPen(QPen(col("canvas"), 1))
            p.drawLine(r.topLeft(), r.bottomLeft())
        T(p, r.left() + 12, r.bottom() + 10, k, F("mono", 13, 500), "ink", rw - 16)
        T(p, r.left() + 12, r.bottom() + 32, C[k], F("hud", 24), "ink-muted")
        T(p, r.left() + 12, r.bottom() + 60, u, F("body", 15), "ink-faint", rw - 16)
    p.setPen(QPen(col("hairline-strong"), 1))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(QRectF(M, y + 44, W - 2 * M, 150))

    yt = y + 300
    label(p, M, yt, "Texto sobre surface")
    tw = (W - 2 * M - 48) / 3
    for i, (k, u) in enumerate([("ink", "texto principal e títulos"), ("ink-muted", "texto secundário, descrições"),
                                ("ink-faint", "placeholder, desabilitado, metadados")]):
        r = QRectF(M + i * (tw + 24), yt + 36, tw, 150)
        p.fillRect(r, col("surface"))
        T(p, r.left() + 20, r.top() + 14, "Marcar evento", F("display", 30, 600), k)
        T(p, r.left() + 20, r.top() + 62, f"{k}  {C[k]}", F("mono", 13), "ink-muted")
        T(p, r.left() + 20, r.top() + 88, u, F("body", 15), "ink-faint")
        rt = f"{ratio(k, 'surface'):.1f}:1".replace(".", ",")
        T(p, r.right() - 20 - adv(p, rt, F("hud", 34)), r.bottom() - 48, rt, F("hud", 34), "success")

    ys = yt + 230
    label(p, M, ys, "Semânticas")
    x = M
    for k, lab, nm in [("success", "Concluído", "success"), ("warning", "Atenção", "warning"),
                       ("danger", "Erro", "danger"), ("primary", "Informação", "primary")]:
        w = chip(p, x, ys + 38, lab, k, h=30)
        T(p, x, ys + 80, f"{nm}  {C[k]}", F("mono", 13), "ink-muted")
        x += max(w, 190) + 40
    P(p, M + 900, ys + 36, 620, "Estado nunca depende só de cor: o ponto vem sempre com um rótulo, e o erro diz como resolver.",
      F("body", 15), "ink-muted")


def page_contrast(p, n):
    frame(p, n, "Cores")
    y = heading(p, "Proporção e contraste",
                "Numa tela típica, a superfície domina e o neon é pouco. Todos os pares de texto passam no nível AA da WCAG.", w=1100)
    label(p, M, y + 10, "Proporção aproximada numa tela")
    parts = [("surface", 70, "superfícies"), ("ink", 18, "texto"), ("primary", 7, "ciano"),
             ("brand", 2.5, "rosa"), ("success", 1.8, "limão"), ("synth", 0.7, "roxo")]
    x, bw = M, W - 2 * M
    for k, pct, nm in parts:
        w = bw * pct / 100
        p.fillRect(QRectF(x, y + 46, w, 70), col(k))
        x += w
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(col("hairline-strong"), 1))
    p.drawRect(QRectF(M, y + 46, bw, 70))
    xs = M
    for k, pct, nm in parts:
        s = f"{nm} {str(pct).replace('.', ',')}%"
        p.fillRect(QRectF(xs, y + 140, 14, 14), col(k))
        xs += 22 + T(p, xs + 22, y + 132, s, F("body", 15), "ink-muted") + 34

    yt = y + 200
    label(p, M, yt, "Contraste (WCAG 2.1)")
    pairs = [("ink", "canvas"), ("ink", "surface"), ("ink", "surface-raised"), ("ink-muted", "surface"),
             ("ink-faint", "surface"), ("primary", "surface"), ("on-primary", "primary"), ("brand", "surface"),
             ("success", "surface"), ("on-success", "success"), ("warning", "surface"), ("danger", "surface"),
             ("control-border", "surface"), ("hairline", "surface")]
    colw = (W - 2 * M - 40) / 2
    for i, (a, b) in enumerate(pairs):
        cx = M + (i // 7) * (colw + 40)
        cy = yt + 40 + (i % 7) * 66
        r = QRectF(cx, cy, 120, 54)
        p.fillRect(r, col(b))
        T(p, r.left(), r.top(), "Aa", F("display", 28, 700), a, 120, CENTER, 54)
        T(p, cx + 140, cy + 4, f"{a}  sobre  {b}", F("mono", 14), "ink")
        v = ratio(a, b)
        tag = "AA texto" if v >= 4.5 else ("AA componente" if v >= 3 else "decorativo")
        T(p, cx + 140, cy + 28, tag, F("body", 13), "ink-faint")
        rs = f"{v:.2f}:1".replace(".", ",")
        colr = "success" if v >= 4.5 else ("warning" if v >= 3 else "ink-faint")
        T(p, cx + colw - adv(p, rs, F("hud", 34)), cy + 6, rs, F("hud", 34), colr)
        p.setPen(QPen(col("hairline"), 1))
        p.drawLine(QPointF(cx, cy + 60), QPointF(cx + colw, cy + 60))


def page_type_families(p, n):
    frame(p, n, "Tipografia")
    y = heading(p, "Tipografia", "Três famílias com papéis separados, todas de licença OFL e embarcadas no app, "
                                 "para ter a mesma cara no Windows e no macOS.", w=1100)
    cols = [
        ("Chakra Petch", "display", "Títulos e cards", "Angular e técnica: dá o tom de sistema operacional sem virar ficção científica genérica.",
         [(400, "Regular"), (500, "Medium"), (600, "SemiBold"), (700, "Bold")]),
        ("IBM Plex Sans", "body", "Interface e texto", "Legível em tamanho pequeno, com todos os acentos. Botões, descrições, campos e guias.",
         [(400, "Regular"), (500, "Medium"), (600, "SemiBold"), (700, "Bold")]),
        ("VT323", "hud", "HUD e números", "Fonte de terminal VCR. Só para rótulos curtos em caixa alta e números que mudam.",
         [(400, "Regular")]),
    ]
    cw = (W - 2 * M - 2 * 32) / 3
    for i, (name, fam, role, desc, weights) in enumerate(cols):
        x = M + i * (cw + 32)
        top = y + 20
        r = QRectF(x, top, cw, 640)
        inner = panel_window(p, r, role, fam)
        big = "24/40" if fam == "hud" else "Aa"
        T(p, inner.left(), inner.top() + 6, big, F(fam, 150 if fam == "hud" else 132, 700 if fam == "display" else 400), "ink")
        T(p, inner.left(), inner.top() + 196, name, F("display", 30, 600), "primary")
        P(p, inner.left(), inner.top() + 244, inner.width(), desc, F("body", 15), "ink-muted", 1.5)
        alpha = "ABCDEFGHIJKLMNOPQRSTUVWXYZ\nabcdefghijklmnopqrstuvwxyz\n0123456789  áéíóú ãõ ç  “…”"
        if fam == "hud":
            alpha = "ABCDEFGHIJKLMNOPQRSTUVWXYZ\n0123456789  AO VIVO  PERDÍVEL\nTROFÉUS 24/40  ·  100%"
        P(p, inner.left(), inner.top() + 330, inner.width(), alpha, F(fam, 26 if fam == "hud" else 19), "ink", 1.45)
        yy = inner.top() + 450
        for wv, wn in weights:
            T(p, inner.left(), yy, f"{wn}  Marcar evento", F(fam, 22 if fam == "hud" else 19, wv), "ink-muted", inner.width())
            yy += 34
    ym = y + 690
    label(p, M, ym, "Apoio: IBM Plex Mono")
    T(p, M + 300, ym - 2, "C:\\Users\\Gamox\\Videos\\marcacoes\\dredge.txt    Ctrl+Alt+M", F("mono", 20), "ink")
    T(p, M + 300, ym + 32, "caminhos de arquivo, logs e atalhos de teclado", F("body", 14), "ink-faint")


def page_type_scale(p, n):
    frame(p, n, "Tipografia")
    y = heading(p, "Hierarquia", "Cada texto do app usa um destes papéis. Tamanhos em pixels da interface.")
    rows = [("display", "display", 32, 700, "Título de página", "Platinas"),
            ("heading", "display", 22, 600, "Seção", "Favoritos do Início"),
            ("title", "display", 17, 600, "Título de card", "DREDGE — Platina Definitiva"),
            ("body", "body", 14, 400, "Texto", "Registre eventos da live com horário e arquivo por jogo."),
            ("body-strong", "body", 14, 600, "Nav e rótulos", "Configurações"),
            ("caption", "body", 12, 400, "Legenda", "Atualizado há 2 minutos"),
            ("button", "body", 13, 600, "Botão", "Marcar agora"),
            ("hud-label", "hud", 18, 400, "Barra de título", "FAVORITOS"),
            ("numeric-lg", "hud", 44, 400, "Número grande", "07"),
            ("numeric-md", "hud", 24, 400, "Número médio", "24/40"),
            ("mono", "mono", 12, 400, "Caminhos e atalhos", "Ctrl+Alt+M")]
    k = 1.6  # amostras ampliadas para leitura no papel
    yy = y + 6
    for tok, fam, px, wv, uso, sample in rows:
        T(p, M, yy + 6, tok, F("mono", 14, 500), "primary", 170)
        T(p, M + 180, yy + 6, f"{px} / {wv}", F("hud", 24), "ink-muted", 120)
        T(p, M + 300, yy + 6, uso, F("body", 14), "ink-faint", 200)
        hh = max(44, px * k * 1.25)
        T(p, M + 520, yy, sample, F(fam, px * k, wv, 1.6 if tok == "hud-label" else 0), "ink", W - 2 * M - 520, h=hh)
        yy += hh + 8
        p.setPen(QPen(col("hairline"), 1))
        p.drawLine(QPointF(M, yy - 4), QPointF(W - M, yy - 4))
    rules = ["VT323 nunca em frase: no máximo 3 palavras ou um número, e nunca abaixo de 18 px.",
             "Números que mudam usam VT323 ou Plex Mono, que têm largura fixa e não pulam.",
             "Carregamento termina com reticências: Carregando…  Botões em frase normal: Salvar marcação."]
    bullets(p, M, yy + 18, W - 2 * M, rules, F("body", 15), "ink-muted", gap=6)


def page_shape(p, n):
    frame(p, n, "Forma e espaço")
    y = heading(p, "Forma, espaço e elevação",
                "Tudo é quase reto. O chanfro de 10 px no canto do painel-janela é a assinatura herdada da identidade atual.", w=1100)
    label(p, M, y + 10, "Raios")
    x = M
    for nm, rad in [("none 0", 0), ("xs 2", 2), ("sm 4", 4), ("md 6", 6), ("full", 40)]:
        r = QRectF(x, y + 46, 96, 96 if nm != "full" else 40)
        p.setBrush(col("surface-raised"))
        p.setPen(QPen(col("primary"), 1.4))
        p.drawRoundedRect(r, rad * 3 if nm != "full" else 20, rad * 3 if nm != "full" else 20)
        T(p, x, y + 152, nm, F("mono", 13), "ink-muted")
        x += 124
    T(p, M, y + 182, "raios desenhados 3x maiores para leitura", F("body", 12), "ink-faint")
    P(p, M, y + 212, 560, "sm 4 é o padrão de tudo. Pílula só em chips de status. xs em callouts e selos. md nos ícones de 48 px.",
      F("body", 15), "ink-muted")

    cx = M + 700
    label(p, cx, y + 10, "Chanfro do painel-janela")
    zoom = QRectF(cx, y + 46, 360, 220)
    panel_window(p, zoom, "Favoritos", "3/4")
    p.setPen(QPen(col("brand"), 1.2, Qt.PenStyle.DashLine))
    p.drawLine(QPointF(zoom.right() - 10, zoom.top() - 18), QPointF(zoom.right() + 18, zoom.top() + 10))
    T(p, zoom.right() + 24, zoom.top() - 12, "10 px", F("hud", 26), "brand")
    T(p, zoom.right() + 24, zoom.bottom() - 20, "sombra dura 4/4, preto 70%", F("body", 13), "ink-muted")

    ys = y + 330
    label(p, M, ys, "Espaçamento (base 4)")
    x = M
    for nm, v in [("xxs", 4), ("xs", 8), ("sm", 12), ("md", 16), ("lg", 24), ("xl", 32), ("xxl", 48)]:
        p.fillRect(QRectF(x, ys + 40 + (48 - v), v * 2, v), col("primary"))
        T(p, x, ys + 100, f"{nm} {v}", F("mono", 13), "ink-muted")
        x += max(v * 2, 60) + 30
    P(p, M, ys + 136, 620, "Dentro do painel: md 16. Entre painéis e abaixo do título da página: lg 24.", F("body", 15), "ink-muted")

    ye = ys + 220
    label(p, M, ye, "Elevação")
    ew = (W - 2 * M - 2 * 40) / 3
    lv = [("0  plano", "fundo canvas"), ("1  janela", "surface + borda + sombra dura"),
          ("2  destaque", "borda ciano, faixa rosa, brilho suave. Um por tela.")]
    for i, (t, d) in enumerate(lv):
        r = QRectF(M + i * (ew + 40), ye + 44, ew, 150)
        if i == 0:
            p.setPen(QPen(col("hairline"), 1, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(r)
        else:
            panel_window(p, r, t.split("  ")[1], featured=(i == 2))
        T(p, r.left(), r.bottom() + 14, t, F("hud", 26), "ink")
        T(p, r.left() + 150, r.bottom() + 18, d, F("body", 13), "ink-muted", ew - 150)


def page_actions(p, n):
    frame(p, n, "Componentes")
    y = heading(p, "Ações e campos", "Um botão primário por área visível: a ação que a pessoa veio fazer. O resto é secundário.")
    states = [("rest", "padrão"), ("hover", "hover"), ("pressed", "pressionado"), ("focus", "foco"), ("disabled", "desabilitado")]
    kinds = [("primary", "Primário", "Marcar agora"), ("secondary", "Secundário", "Novo jogo"),
             ("ghost", "Fantasma", "Voltar aos guias"), ("danger", "Perigo", "Remover")]
    x0, cw = M + 200, 230
    for j, (_, sname) in enumerate(states):
        T(p, x0 + j * cw, y + 4, sname.upper(), F("hud", 22, ls=1.4), "ink-faint")
    for i, (kind, kname, lab) in enumerate(kinds):
        yy = y + 46 + i * 70
        T(p, M, yy + 8, kname, F("body", 16, 600), "ink")
        for j, (st, _) in enumerate(states):
            button(p, QRectF(x0 + j * cw, yy, 168, 38), lab, kind, st)
    yb = y + 46 + 4 * 70 + 30
    p.setPen(QPen(col("hairline"), 1))
    p.drawLine(QPointF(M, yb), QPointF(W - M, yb))
    label(p, M, yb + 24, "Campos")
    fw = (W - 2 * M - 3 * 40) / 4
    yi = yb + 62
    input_field(p, M, yi, fw, "Evento", placeholder="Ex.: boss derrotado…")
    input_field(p, M + (fw + 40), yi, fw, "Evento", value="Platina do DREDGE", state="focus")
    input_field(p, M + 2 * (fw + 40), yi, fw, "Pasta das marcações", value="C:\\Marcacoes", state="error",
                error="Pasta não encontrada. Escolha outra em Trocar pasta.")
    input_field(p, M + 3 * (fw + 40), yi, fw, "Atalho", value="Ctrl+Alt+M", state="disabled")
    for j, s in enumerate(["padrão", "foco", "erro", "desabilitado"]):
        T(p, M + j * (fw + 40), yi + 110, s.upper(), F("hud", 22, ls=1.4), "ink-faint")
    rules = ["Rótulo acima do campo, erro abaixo, e o erro diz como resolver.",
             "Placeholder mostra um exemplo e termina com reticências. Nunca substitui o rótulo.",
             "Remover sempre pede confirmação, com Não como padrão."]
    bullets(p, M, yi + 160, W - 2 * M, rules, F("body", 15), "ink-muted", gap=6)


def page_status(p, n):
    frame(p, n, "Componentes")
    y = heading(p, "Status, selos e progresso",
                "Estado se lê de longe: um ponto, um selo ou uma barra. Chip de status nunca pode parecer campo de texto.", w=1100)
    label(p, M, y + 10, "Chips de status")
    x = M
    for lab, dot, pulse in [("Pronto para transmitir", "success", False), ("Arquivo sem permissão", "warning", False),
                            ("OBS desconectado", "danger", False), ("Nenhum arquivo ativo", "ink-faint", False),
                            ("Ao vivo há 1h12", "brand", True)]:
        x += chip(p, x, y + 46, lab, dot, h=30, pulse=pulse) + 18
    label(p, M, y + 108, "Selos e tags")
    x = M
    for lab, kind in [("AO VIVO", "live"), ("GRAVANDO", "live"), ("PLATINADO", "trophy"), ("OBTIDO", "trophy"),
                      ("PERDÍVEL", "missable"), ("SPOILER", "spoiler")]:
        x += badge(p, x, y + 146, lab, kind) + 16
    sp = QRectF(x + 30, y + 136, W - M - x - 30, 46)
    p.setBrush(col("surface-raised"))
    p.setPen(QPen(col("hairline-strong"), 1, Qt.PenStyle.DashLine))
    p.drawRoundedRect(sp, 2, 2)
    T(p, sp.left() + 14, sp.top(), "Spoiler escondido. Clique para revelar.", F("body", 14), "ink-faint", sp.width() - 20, h=sp.height())

    yp = y + 228
    label(p, M, yp, "Progresso em blocos")
    for i, (nm, d, t, tag) in enumerate([("Começando", 0, 40, None), ("Em andamento", 24, 40, None), ("Concluído", 40, 40, "PLATINADO")]):
        yy = yp + 40 + i * 64
        T(p, M, yy, nm, F("body", 15, 600), "ink-muted", 170)
        sw = segmented(p, M + 180, yy + 2, d, t)
        T(p, M + 200 + sw, yy - 6, f"{d}/{t}", F("hud", 34), "ink")
        if tag:
            badge(p, M + 300 + sw, yy - 1, tag, "trophy")
    P(p, M, yp + 250, 760, "20 blocos de 12 x 16 px, 3 px de espaço. Preenchido em limão com brilho leve; vazio em hairline. "
                           "O número ao lado usa VT323.", F("body", 15), "ink-muted")

    nx = M + 900
    label(p, nx, yp, "Display numérico (Contador)")
    r = QRectF(nx, yp + 40, W - M - nx, 230)
    inner = panel_window(p, r, "Mortes no boss", "PRESET 2")
    T(p, inner.left(), inner.top() - 6, "07", F("hud", 150), "ink")
    T(p, inner.left() + 190, inner.top() + 40, "+1  Ctrl+Alt+K", F("mono", 16), "ink-muted")
    button(p, QRectF(inner.left() + 190, inner.top() + 90, 120, 36), "Resetar", "secondary")


def page_structure(p, n):
    frame(p, n, "Componentes")
    y = heading(p, "Estrutura", "O painel-janela agrupa uma seção. O card representa um módulo ou plugin.")
    r = QRectF(M, y + 40, 640, 230)
    inner = panel_window(p, r, "Favoritos", "3/4")
    module_card(p, QRectF(inner.left(), inner.top() + 4, inner.width(), 150), "marker", "Marcador",
                "Registre eventos da live com horário e arquivo por jogo.", "default.txt", "success")
    ann = [(r.left() + 140, r.top() + 15, "barra de título 30 px · VT323 em caixa alta"),
           (r.right() - 70, r.top() + 15, "metadado curto"),
           (r.right() + 14, r.top() - 16, "chanfro 10 px"),
           (r.right() + 18, r.bottom() + 18, "sombra dura 4/4")]
    lx = r.right() + 60
    for i, (ax, ay, txt) in enumerate(ann):
        marker(p, ax, ay, i + 1)
        marker(p, lx, r.top() + 30 + i * 52, i + 1)
        T(p, lx + 26, r.top() + 18 + i * 52, txt, F("body", 15), "ink-muted")

    yc = y + 320
    label(p, M, yc, "Card: padrão, hover e texto longo")
    cw = (W - 2 * M - 2 * 24) / 3
    module_card(p, QRectF(M, yc + 36, cw, 150), "counter", "Contador",
                "Overlays transparentes para o OBS com presets e atalhos.", "2 overlays abertos", "success")
    module_card(p, QRectF(M + cw + 24, yc + 36, cw, 150), "marker", "Marcador",
                "Registre eventos da live com horário e arquivo por jogo.", "default.txt", "success", hover=True)
    module_card(p, QRectF(M + 2 * (cw + 24), yc + 36, cw, 150), "puzzle", "StreamOn",
                "Abre seus apps e painéis de live (OBS, dashboards e o que você configurar) em um clique, sem perder tempo.",
                "Pronto para transmitir", "ink-faint")

    yn = yc + 230
    label(p, M, yn, "Navegação")
    for i, (lab, ic, st) in enumerate([("Início", "home", "rest"), ("Plugins", "plugins", "hover"), ("Platinas", "platinas", "active")]):
        rr = QRectF(M, yn + 36 + i * 50, 240, 42)
        p.fillRect(rr.adjusted(-8, -4, 8, 4), col("sunken"))
        nav_item(p, rr, lab, ic, st)
        T(p, M + 260, yn + 36 + i * 50, ["padrão", "hover", "ativo · barra rosa 3 px"][i], F("body", 13), "ink-faint", h=42)
    tx = M + 520
    label(p, tx, yn, "Abas")
    for i, t in enumerate(["Passo a passo", "Onde está…", "40 Troféus"]):
        tab(p, QRectF(tx + i * 150, yn + 40, 140, 40), t, active=(i == 0))
    label(p, tx, yn + 104, "Callouts")
    cw2 = (W - M - tx - 2 * 16) / 3
    for i, (k, t, b) in enumerate([("info", "Como usar", "Faça o passo, marque e siga."),
                                   ("warning", "Perdível", "Faça antes de sair da ilha."),
                                   ("danger", "Irreversível", "Remover apaga os arquivos.")]):
        callout(p, QRectF(tx + i * (cw2 + 16), yn + 140, cw2, 86), k, t, b)


def page_icons(p, n):
    frame(p, n, "Iconografia")
    y = heading(p, "Ícones de interface", "Linha HUD: grade de 24, traço reto de 2 px, pontas quadradas e o mesmo chanfro "
                                          "do painel-janela. Uma cor por papel, nunca degradê, nunca emoji.", w=1150)
    names = ICONS.UI_ICONS
    cols = 10
    cw = (W - 2 * M) / cols
    for i, nm in enumerate(names):
        cx = M + (i % cols) * cw
        cy = y + 24 + (i // cols) * 168
        r = QRectF(cx, cy, cw - 14, 150)
        p.fillRect(r, col("surface"))
        ui_icon(p, nm, r.center().x() - 24, r.top() + 22, 48, "primary")
        T(p, r.left() + 4, r.bottom() - 54, ICONS.UI_NAMES[nm], F("body", 14, 600), "ink", r.width() - 8, CENTER)
        T(p, r.left() + 4, r.bottom() - 30, nm, F("mono", 12), "ink-faint", r.width() - 8, CENTER)
    yr = y + 24 + 2 * 168 + 20
    label(p, M, yr, "Cor por estado")
    states = [("ink-muted", "repouso"), ("ink", "hover"), ("primary", "ativo"), ("danger", "destrutivo"),
              ("ink-faint", "desabilitado")]
    for i, (c, t) in enumerate(states):
        x = M + i * 128
        p.fillRect(QRectF(x, yr + 36, 108, 84), col("sunken"))
        ui_icon(p, "remove" if c == "danger" else "platinas", x + 42, yr + 50, 24, c)
        T(p, x, yr + 86, t, F("body", 13), "ink-muted", 108, CENTER)
    xs = M + 5 * 128 + 40
    label(p, xs, yr, "Tamanhos")
    for i, (s, t) in enumerate([(24, "24 nav"), (20, "20 subnav"), (16, "16 em botão")]):
        x = xs + i * 128
        p.fillRect(QRectF(x, yr + 36, 108, 84), col("sunken"))
        ui_icon(p, "platinas", x + 54 - s / 2, yr + 66 - s / 2, s, "ink")
        T(p, x, yr + 86, t, F("mono", 12), "ink-muted", 108, CENTER)
    button(p, QRectF(xs + 3 * 128 + 10, yr + 44, 200, 38), "", "secondary")
    ui_icon(p, "popout", xs + 3 * 128 + 30, yr + 55, 16, "ink")
    T(p, xs + 3 * 128 + 54, yr + 44, "Abrir em janela", F("body", 14, 600), "ink", h=38)
    T(p, xs + 3 * 128 + 10, yr + 94, "ícone 16 + texto", F("body", 13), "ink-faint")
    rules = ["Traço sempre de 2 px reais (1,5 px no tamanho 16); o desenho escala, a espessura não.",
             "Ícone só-ícone tem nome acessível e dica (tooltip). Ícone com texto vem à esquerda dele.",
             "Onde hoje há emoji (sino, check, coração, envelope, festa), entra o ícone correspondente."]
    bullets(p, M, yr + 150, W - 2 * M, rules, F("body", 16), "ink-muted", gap=6)


def page_icons_brand(p, n):
    frame(p, n, "Iconografia")
    y = heading(p, "Ícones de marca", "Pixel-art na grade 12 × 12, para os momentos de personalidade: telas vazias, "
                                       "onboarding, conquistas e os cards das ferramentas. Nunca na barra lateral.", w=1150)
    names = list(ICONS.BRAND)
    cols = 6
    cw = (W - 2 * M) / cols
    for i, nm in enumerate(names):
        cx = M + (i % cols) * cw
        cy = y + 24 + (i // cols) * 196
        r = QRectF(cx, cy, cw - 18, 178)
        p.fillRect(r, col("surface"))
        brand_icon(p, nm, r.center().x() - 48, r.top() + 18, 96)
        T(p, r.left(), r.bottom() - 44, ICONS.BRAND_NAMES[nm], F("body", 15, 600), "ink", r.width(), CENTER)
        T(p, r.left(), r.bottom() - 22, nm, F("mono", 12), "ink-faint", r.width(), CENTER)
    yr = y + 24 + 2 * 196 + 10
    label(p, M, yr, "Construção")
    brand_icon(p, "trophy", M, yr + 40, 144, grid=True)
    P(p, M + 170, yr + 40, 420, "Cada célula é um quadrado sólido, sem antisserrilhado. Três tintas: a cor do papel do ícone, "
                               "um acento e o branco ink para brilho.", F("body", 16), "ink-muted")
    xs = M + 640
    label(p, xs, yr, "Tamanhos: só múltiplos de 12")
    for i, (s, t) in enumerate([(48, "48 cards e vazios"), (96, "96 onboarding"), (24, "24 não use")]):
        x = xs + i * 240
        box = QRectF(x, yr + 40, 210, 130)
        p.fillRect(box, col("sunken"))
        brand_icon(p, "star", box.center().x() - s / 2, box.center().y() - s / 2 - 10, s)
        T(p, x, box.bottom() - 26, t, F("mono", 12), "danger" if s == 24 else "ink-muted", 210, CENTER)
    P(p, xs, yr + 190, 700, "Em 48 px cada célula tem 4 px, então a arte continua inteira nas escalas 125%, 150% e 200% "
                           "do Windows. Abaixo disso as células ficam desiguais: use o ícone de interface.",
      F("body", 15), "ink-muted")


def page_synth(p, n):
    frame(p, n, "Synthwave")
    y = heading(p, "Arte synthwave", "Sol listrado, horizonte roxo e grid em perspectiva. Pintado em vetor pelo app, sem imagem. É tempero: aparece pouco.", w=1100)
    big = QRectF(M, y + 30, 900, 420)
    synth(p, big, cx=0.5, sun=0.42, horizon=0.62)
    notes = [(big.left() + 450, big.top() + 110, "sol: amarelo para rosa"),
             (big.left() + 450, big.top() + 230, "5 cortes horizontais"),
             (big.left() + 120, big.top() + 255, "horizonte em roxo 40%"),
             (big.left() + 220, big.bottom() - 60, "grid ciano 35%")]
    for i, (ax, ay, t) in enumerate(notes):
        marker(p, ax, ay, i + 1)
    lx = big.right() + 50
    for i, (_, _, t) in enumerate(notes):
        marker(p, lx + 15, big.top() + 30 + i * 52, i + 1)
        T(p, lx + 44, big.top() + 18 + i * 52, t, F("body", 16), "ink-muted")
    label(p, lx, big.top() + 250, "Use em", "success")
    T(p, lx, big.top() + 282, "topo do Início, onboarding, telas vazias, Sobre", F("body", 15), "ink-muted", W - M - lx)
    label(p, lx, big.top() + 330, "Não use", "danger")
    T(p, lx, big.top() + 362, "atrás de texto longo, dentro de guias, em controles", F("body", 15), "ink-muted", W - M - lx)

    ye = big.bottom() + 50
    label(p, M, ye, "Exemplo: tela vazia")
    r = QRectF(M, ye + 36, 700, 220)
    inner = panel_window(p, r, "Favoritos", "0/4")
    synth(p, QRectF(inner.left(), inner.top(), 220, inner.height()), cx=0.5, sun=0.36, horizon=0.66)
    T(p, inner.left() + 244, inner.top() + 10, "Nenhum favorito ainda", F("display", 22, 600), "ink")
    P(p, inner.left() + 244, inner.top() + 46, inner.width() - 244, "Fixe até 4 ferramentas para abrir direto do Início.", F("body", 14), "ink-muted")
    button(p, QRectF(inner.left() + 244, inner.bottom() - 44, 190, 38), "Gerenciar favoritos", "primary")


# ---------------------------------------------------------------- telas
def sidebar(p, active):
    p.fillRect(QRectF(0, 0, 232, 800), col("sunken"))
    p.setPen(QPen(col("hairline"), 1))
    p.drawLine(QPointF(232, 0), QPointF(232, 800))
    draw_pix(p, pix("brand_logo.png"), QRectF(24, 20, 184, 56))
    items = [("Início", "home"), ("Plugins", "plugins"), ("Platinas", "platinas"), ("Atalhos", "hotkey"),
             ("Diagnóstico", "diagnostics"), ("Configurações", "settings"), ("Ajuda", "help"), ("Sobre", "about")]
    for i, (lab, ic) in enumerate(items):
        nav_item(p, QRectF(12, 100 + i * 48, 208, 40), lab, ic, "active" if lab == active else "rest")
    T(p, 18, 744, "ONLINE", F("hud", 20, ls=1.5), "success")
    T(p, 18, 766, "v0.9.0", F("hud", 20, ls=1), "ink-faint")


def screen_home(p):
    p.fillRect(QRectF(0, 0, 1280, 800), col("canvas"))
    sidebar(p, "Início")
    x0, x1 = 264, 1248
    T(p, x0, 24, "Início", F("display", 32, 700), "ink")
    chip(p, x0, 78, "Atualizado · v0.9.0", "success")
    button(p, QRectF(x0, 114, 140, 36), "Marcar agora", "primary")
    button(p, QRectF(x0 + 152, 114, 116, 36), "Novo jogo")
    button(p, QRectF(x0 + 276, 114, 170, 36), "Gerenciar favoritos", "ghost")
    synth(p, QRectF(x1 - 500, 24, 500, 128), cx=0.5, sun=0.42, horizon=0.62)
    badge(p, x1 - 116, 36, "AO VIVO", "live")
    fav = QRectF(x0, 176, x1 - x0, 210)
    inner = panel_window(p, fav, "Favoritos", "3/4")
    cw = (inner.width() - 32) / 3
    cards = [("marker", "Marcador", "Registre eventos da live com horário e arquivo por jogo.", "default.txt", "success"),
             ("counter", "Contador", "Overlays transparentes para o OBS com presets e atalhos.", "2 overlays abertos", "success"),
             ("puzzle", "StreamOn", "Abre seus apps e painéis de live (OBS, dashboards e o que você configurar) em um clique.", "Pronto para transmitir", "ink-faint")]
    for i, c in enumerate(cards):
        module_card(p, QRectF(inner.left() + i * (cw + 16), inner.top(), cw, 148), *c)
    pl = QRectF(x0, 410, (x1 - x0) * 0.58, 250)
    inner = panel_window(p, pl, "Platinas em andamento", "3 guias", featured=True)
    rows = [("DREDGE — Platina Definitiva", 24, 40, ("PERDÍVEL", "missable")), ("The Witcher 3", 9, 78, None),
            ("Kingdom Hearts Final Mix", 63, 63, ("PLATINADO", "trophy"))]
    for i, (nm, d, t, tag) in enumerate(rows):
        yy = inner.top() + i * 64
        wnm = T(p, inner.left(), yy, nm, F("display", 17, 600), "ink", 320)
        if tag:
            badge(p, inner.left() + min(wnm, 320) + 12, yy, *tag)
        sw = segmented(p, inner.left(), yy + 30, d, t, w=11, h=15)
        T(p, inner.left() + sw + 14, yy + 22, f"{d}/{t}", F("hud", 30), "ink")
    up = QRectF(pl.right() + 24, 410, x1 - pl.right() - 24, 250)
    inner = panel_window(p, up, "Últimas atualizações", "GitHub")
    for i, (v, t) in enumerate([("v0.9.0", "Cara nova: Sidekick OS."), ("v0.8.7", "Feedback na aba Sobre, direto para o Gmail."),
                                ("v0.8.4", "Subtitler 1.0.1 no catálogo.")]):
        yy = inner.top() + i * 62
        T(p, inner.left(), yy - 4, v, F("hud", 30), "primary")
        T(p, inner.left(), yy + 26, t, F("body", 13), "ink-muted", inner.width())
    T(p, x0, 690, "Progresso, versão 0.9.0 e notas são dados de exemplo.", F("body", 12), "ink-faint")


def screen_guide(p):
    p.fillRect(QRectF(0, 0, 1280, 800), col("canvas"))
    sidebar(p, "Platinas")
    x0, x1 = 264, 1248
    button(p, QRectF(x0, 22, 168, 34), "Voltar aos guias", "ghost")
    button(p, QRectF(x1 - 170, 22, 170, 34), "Abrir em janela", "secondary")
    T(p, x0, 66, "DREDGE — Platina Definitiva", F("display", 32, 700), "ink")
    sw = segmented(p, x0, 124, 24, 40, segs=30, w=12, h=16)
    T(p, x0 + sw + 16, 114, "24/40", F("hud", 34), "ink")
    T(p, x0 + sw + 92, 122, "troféus", F("body", 13), "ink-muted")
    chip(p, x1 - 160, 118, "112/309 passos", "success")
    tabs = ["Passo a passo", "Onde está…", "Missões", "67 Peixes", "Santuários", "Docas", "40 Troféus", "Mapas"]
    tw = (x1 - x0) / len(tabs)
    for i, t in enumerate(tabs):
        tab(p, QRectF(x0 + i * tw, 158, tw, 40), t, active=(i == 0))
    callout(p, QRectF(x0, 216, x1 - x0, 66), "warning", "Perdível",
            "Converse com o personagem do farol antes de avançar a história, ou o troféu dele some.")
    r = QRectF(x0, 300, x1 - x0, 380)
    inner = panel_window(p, r, "Fase 2 — Mar aberto", "5/12")
    steps = [(True, "2.1", "Compre o motor maior na doca", None),
             (True, "2.2", "Pesque três espécies de águas profundas", None),
             (False, "2.3", "Entregue a relíquia ao colecionador", ("PERDÍVEL", "missable")),
             (False, "2.4", "Investigue o naufrágio ao norte", ("SPOILER", "spoiler")),
             (False, "2.5", "Volte ao porto antes do anoitecer", None)]
    for i, (done, num, t, tag) in enumerate(steps):
        yy = inner.top() + i * 62
        checkbox(p, inner.left(), yy + 6, done)
        T(p, inner.left() + 34, yy, num, F("hud", 30), "primary" if not done else "ink-faint")
        tx = inner.left() + 86
        wt = T(p, tx, yy + 2, t, F("display", 17, 600), "ink-faint" if done else "ink", 520)
        if tag:
            badge(p, tx + wt + 12, yy + 2, *tag)
        sub = "Concluído" if done else ("Conteúdo protegido. Clique na tag para revelar." if tag and tag[1] == "spoiler" else "Quando: ao chegar na nova região.")
        T(p, tx, yy + 28, sub, F("body", 13), "ink-faint" if done else "ink-muted", 700)
        p.setPen(QPen(col("hairline"), 1))
        p.drawLine(QPointF(inner.left(), yy + 54), QPointF(inner.right(), yy + 54))
    T(p, x0, 700, "Passos ilustrativos: o conteúdo real vem de cada guia.", F("body", 12), "ink-faint")


def page_screen(p, n, title, lead, draw, notes):
    frame(p, n, "Aplicação")
    y = heading(p, title, lead, w=1200)
    s = 0.96
    sx, sy = M, y + 24
    p.save()
    p.translate(sx, sy)
    p.scale(s, s)
    p.setClipRect(QRectF(0, 0, 1280, 720))
    draw(p)
    p.restore()
    p.setPen(QPen(col("hairline-strong"), 1))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(QRectF(sx, sy, 1280 * s, 720 * s))
    lx = sx + 1280 * s + 28
    lw = W - M - lx
    for i, (ax, ay, t) in enumerate(notes):
        marker(p, sx + ax * s, sy + ay * s, i + 1)
        yy = sy + 6 + i * 92
        marker(p, lx + 15, yy + 15, i + 1)
        P(p, lx + 40, yy + 2, lw - 40, t, F("body", 15), "ink-muted", 1.4)


def page_home(p, n):
    page_screen(p, n, "Aplicação: Início", "O Início vira um painel de verdade, com o logo só na barra lateral.", screen_home, [
        (250, 132, "Uma ação primária. O resto é secundário ou fantasma."),
        (1200, 160, "Synthwave ao lado do título, nunca acima nem atrás do texto."),
        (540, 186, "Painel-janela com barra de título e metadado (3/4)."),
        (285, 357, "Chip de status no lugar da caixa que parecia campo."),
        (836, 412, "O único painel em destaque da tela: progresso das platinas."),
        (660, 486, "Números em VT323 e progresso em blocos.")])


def page_guide(p, n):
    page_screen(p, n, "Aplicação: guia de platina", "Os guias seguem a mesma linguagem, com tags e callouts da spec.", screen_guide, [
        (248, 132, "Progresso geral em blocos, com o número em VT323."),
        (248, 178, "Abas com sublinhado ciano, no lugar da grade de caixas."),
        (248, 249, "Callout de um nível só: nada de caixa dentro de caixa."),
        (900, 560, "PERDÍVEL sempre visível. SPOILER esconde só o conteúdo."),
        (248, 362, "Passo feito: check limão e texto apagado.")])


def page_dos(p, n):
    frame(p, n, "Faça e não faça")
    y = heading(p, "Faça e não faça")
    pairs = []
    cw = (W - 2 * M - 40) / 2
    rh = 190

    def pair(i, title, good, bad):
        yy = y + 8 + i * (rh + 14)
        T(p, M, yy, title, F("display", 22, 600), "ink")
        for k, (fn, ok) in enumerate([(good, True), (bad, False)]):
            r = QRectF(M + k * (cw + 40), yy + 38, cw, rh - 38)
            p.fillRect(r, col("sunken"))
            T(p, r.left() + 14, r.top() + 6, "FAÇA" if ok else "NÃO FAÇA", F("hud", 22, ls=1.5), "success" if ok else "danger")
            x_mark(p, r.right() - 20, r.top() + 18, ok)
            body = r.adjusted(0, 32, 0, 0)
            p.save()
            p.setClipRect(body)
            fn(body)
            p.restore()

    def glow_good(r):
        for j in range(3):
            panel_window(p, QRectF(r.left() + 20 + j * 230, r.top() + 8, 210, 96), ["Favoritos", "Platinas", "Notas"][j], featured=(j == 1))

    def glow_bad(r):
        for j in range(3):
            rr = QRectF(r.left() + 20 + j * 230, r.top() + 12, 210, 90)
            g = QLinearGradient(rr.topLeft(), rr.bottomRight())
            g.setColorAt(0, col("primary"))
            g.setColorAt(1, col("brand"))
            p.setBrush(col("surface"))
            p.setPen(QPen(col("primary", 70), 8))
            p.drawRoundedRect(rr, 8, 8)
            p.setPen(QPen(g, 2))
            p.drawRoundedRect(rr, 8, 8)

    def chip_good(r):
        chip(p, r.left() + 24, r.top() + 34, "Nenhum arquivo ativo", "ink-faint", h=30)
        chip(p, r.left() + 260, r.top() + 34, "Pronto para transmitir", "success", h=30)

    def chip_bad(r):
        for j, t in enumerate(["Nenhum arquivo ativo", "Pronto para transmitir"]):
            rr = QRectF(r.left() + 24 + j * 300, r.top() + 30, 270, 40)
            p.setBrush(col("sunken"))
            p.setPen(QPen(col("control-border"), 1))
            p.drawRoundedRect(rr, 4, 4)
            T(p, rr.left() + 12, rr.top(), t, F("body", 14, 600), "ink", h=40)

    def hud_good(r):
        T(p, r.left() + 24, r.top() + 16, "TROFÉUS", F("hud", 26, ls=1.5), "ink-muted")
        T(p, r.left() + 150, r.top() + 8, "24/40", F("hud", 44), "ink")
        T(p, r.left() + 24, r.top() + 70, "Pesque três espécies de águas profundas.", F("body", 16), "ink-muted")

    def hud_bad(r):
        P(p, r.left() + 24, r.top() + 14, cw - 60, "Pesque três espécies de águas profundas antes de voltar ao porto principal da ilha.",
          F("hud", 18), "ink-muted", 1.2)

    def text_good(r):
        module_card(p, QRectF(r.left() + 20, r.top() + 6, 460, 108), "puzzle", "StreamOn",
                    "Abre seus apps e painéis de live (OBS, dashboards e o que você configurar) em um clique.", "Pronto", "ink-faint",
                    max_lines=1)

    def text_bad(r):
        rr = QRectF(r.left() + 20, r.top() + 6, 460, 108)
        p.setBrush(col("surface"))
        p.setPen(QPen(col("hairline"), 1))
        p.drawRoundedRect(rr, 4, 4)
        p.save()
        p.setClipRect(QRectF(rr.left() + 80, rr.top(), 108, rr.height()))
        T(p, rr.left() + 80, rr.top() + 14, "StreamOn", F("display", 19, 600), "ink")
        P(p, rr.left() + 80, rr.top() + 44, 300, "Abre seus apps e painéis de live (OBS, dashboards", F("body", 13), "ink-muted", 1.4)
        p.restore()

    pair(0, "Brilho é exceção", glow_good, glow_bad)
    pair(1, "Chip de status não parece campo", chip_good, chip_bad)
    pair(2, "VT323 só em rótulo curto e número", hud_good, hud_bad)
    pair(3, "Texto longo termina em reticências", text_good, text_bad)


def page_back(p, n):
    p.fillRect(QRectF(0, 0, W, H), col("canvas"))
    synth(p, QRectF(0, H * 0.58, W, H * 0.42), cx=0.5, sun=0.62, horizon=0.55, sky_top="canvas", border=False)
    draw_pix(p, pix("brand_icon.png"), QRectF(M, 110, 120, 128))
    T(p, M, 270, "Sidekick OS", F("display", 72, 700), "ink")
    P(p, M, 370, 900, "A fonte da verdade é o DESIGN.md na raiz do projeto: tokens, componentes, regras e a migração do tema atual. "
                      "Este manual é a leitura visual dele.", F("body", 18), "ink-muted", 1.5)
    label(p, M, 470, "Fontes (licença SIL Open Font License)")
    T(p, M, 504, "Chakra Petch (Cadson Demak)  ·  IBM Plex Sans e Plex Mono (IBM)  ·  VT323 (Peter Hull)", F("body", 16), "ink-muted")
    T(p, M, 560, "STREAMER SIDEKICK  ·  GAMOX  ·  2026", F("hud", 28, ls=3), "primary")


PAGES = [page_cover, page_essence, page_logo, page_colors, page_neutrals, page_contrast, page_type_families,
         page_type_scale, page_shape, page_actions, page_status, page_structure, page_icons, page_icons_brand, page_synth,
         page_home, page_guide, page_dos, page_back]


def setup(painter):
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)


def render_png(outdir: Path, only=None, scale=1.0):
    outdir.mkdir(parents=True, exist_ok=True)
    for i, fn in enumerate(PAGES, 1):
        if only and i not in only:
            continue
        img = QImage(int(W * scale), int(H * scale), QImage.Format.Format_ARGB32)
        img.fill(col("canvas"))
        p = QPainter(img)
        setup(p)
        p.scale(scale, scale)
        fn(p, i)
        p.end()
        img.save(str(outdir / f"p{i:02d}.png"))
    print("png ok")


def render_pdf(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.stem + ".tmp.pdf")
    wr = QPdfWriter(str(tmp))
    wr.setResolution(300)
    wr.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    wr.setPageOrientation(QPageLayout.Orientation.Landscape)
    wr.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)
    wr.setTitle("Sidekick OS — Manual de identidade visual")
    wr.setCreator("Streamer Sidekick")
    p = QPainter(wr)
    if not p.isActive():
        raise SystemExit(f"Não consegui gravar {tmp}.")
    setup(p)
    s = wr.width() / W
    for i, fn in enumerate(PAGES, 1):
        if i > 1:
            wr.newPage()
        p.save()
        p.scale(s, s)
        fn(p, i)
        p.restore()
    p.end()
    del wr
    try:
        os.replace(tmp, path)
    except PermissionError:
        raise SystemExit(f"{path} está aberto em outro programa. A versão nova ficou em {tmp}.")
    print("pdf ok", path, len(PAGES), "páginas,", round(path.stat().st_size / 1024), "KB")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    fams = set()
    for f in glob.glob(str(FONTS / "*.ttf")):
        fams.update(QFontDatabase.applicationFontFamilies(QFontDatabase.addApplicationFont(f)))
    missing = {"Chakra Petch", "IBM Plex Sans", "IBM Plex Mono", "VT323"} - fams
    if missing:
        print("AVISO: fontes não encontradas em", FONTS, "->", ", ".join(sorted(missing)))
    args = sys.argv[1:]
    if args[:1] == ["pdf"]:
        render_pdf(Path(args[1]))
    elif args[:1] == ["png"]:
        render_png(Path(args[1]), {int(a) for a in args[2:] if a.isdigit()} or None)
    else:
        print(__doc__)
