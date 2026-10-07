"""Gera o GIF do espaço de divulgação do Início (assets/promo/gamox_canal.gif).

Loop de 10 s no visual Sidekick OS: o sticker do Gamox chama para o canal, o
botão de inscrever é clicado e, no fim, "Anuncie aqui". O espaço do Início
recorta as laterais quando a janela é estreita (de ~335 a 520 px de largura),
então tudo que importa fica na faixa central de 330 px.

Precisa do ffmpeg no PATH (ou na variável FFMPEG).

    python scripts/make_promo_gif.py            -> gera o GIF
    python scripts/make_promo_gif.py --stills   -> só quadros de conferência (pasta temporária)
"""
from __future__ import annotations

import math
import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (QColor, QFont, QFontMetricsF, QGuiApplication, QImage, QLinearGradient,  # noqa: E402
                           QPainter, QPainterPath, QPen)

app = QGuiApplication(sys.argv)
from streamer_sidekick.ui import tokens  # noqa: E402

tokens.load_fonts()

W, H = 520, 150          # tamanho lógico do espaço no Início
SCALE = 2                # desenhado em 2x para telas de alta densidade
FPS = 15
DUR = 10.0
SAFE_L, SAFE_R = 95, 425  # faixa que aparece mesmo com a janela estreita
STICKER = ROOT / "src/streamer_sidekick/assets/brand/gamox_sticker.png"
OUT = ROOT / "src/streamer_sidekick/assets/promo/gamox_canal.gif"
C = tokens.color


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def prog(t, a, b):
    return clamp((t - a) / (b - a))


def out_cubic(x):
    return 1 - (1 - x) ** 3


def in_out(x):
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def out_back(x, s=1.7):
    x -= 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def font(role, px, weight=QFont.Weight.Normal, spacing=0.0):
    f = QFont(tokens.family(role))
    f.setPixelSize(int(px))
    f.setWeight(weight)
    if spacing:
        f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    return f


def text(p, s, x, y, f, color, align="left", alpha=1.0, glow=None):
    if alpha <= 0 or not s:
        return 0.0
    fm = QFontMetricsF(f)
    w = fm.horizontalAdvance(s)
    if align == "center":
        x -= w / 2
    path = QPainterPath()
    path.addText(QPointF(x, y), f, s)
    p.save()
    p.setOpacity(p.opacity() * alpha)
    if glow:
        for width, a in ((7, 30), (4, 60)):
            p.strokePath(path, QPen(C(glow, a), width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                                    Qt.PenJoinStyle.RoundJoin))
    p.fillPath(path, C(color) if isinstance(color, str) else color)
    p.restore()
    return w


def chamfer(r: QRectF, cut=8.0) -> QPainterPath:
    path = QPainterPath()
    path.moveTo(r.left(), r.top())
    path.lineTo(r.right() - cut, r.top())
    path.lineTo(r.right(), r.top() + cut)
    path.lineTo(r.right(), r.bottom())
    path.lineTo(r.left(), r.bottom())
    path.closeSubpath()
    return path


# ------------------------------------------------------------------ fundo
HORIZON = 93.0


def background(p, t):
    sky = QLinearGradient(0, 0, 0, HORIZON)
    sky.setColorAt(0, C("sunken"))
    sky.setColorAt(1, C("synth", 150))
    p.fillRect(QRectF(0, 0, W, HORIZON), sky)
    # sol listrado
    cx, rad = W / 2, 58
    sun = QLinearGradient(0, HORIZON - rad, 0, HORIZON)
    sun.setColorAt(0, C("synth-sun-top"))
    sun.setColorAt(1, C("synth-sun-bottom"))
    disc = QPainterPath()
    disc.addEllipse(QPointF(cx, HORIZON), rad, rad)
    clip = QPainterPath()
    clip.addRect(QRectF(0, 0, W, HORIZON))
    stripes = QPainterPath()
    for i in range(5):
        y = HORIZON - rad * 0.55 + i * 7.5
        stripes.addRect(QRectF(cx - rad, y, 2 * rad, 1.2 + i * 1.1))
    p.fillPath(disc.intersected(clip).subtracted(stripes), sun)
    # chão + grid em perspectiva andando para frente (1 ciclo por segundo: fecha o loop)
    p.fillRect(QRectF(0, HORIZON, W, H - HORIZON), C("sunken"))
    p.setPen(QPen(C("brand", 210), 1.2))
    p.drawLine(QPointF(0, HORIZON), QPointF(W, HORIZON))
    p.setPen(QPen(C("primary", 110), 0.8))
    for i in range(-14, 15):
        p.drawLine(QPointF(cx + i * 6, HORIZON), QPointF(cx + i * 60, H + 40))
    phase = (t % 1.0)
    for k in range(9):
        z = (k + phase) / 9
        y = HORIZON + (H - HORIZON) * z ** 2.2
        p.setPen(QPen(C("primary", int(40 + 110 * z)), 0.8))
        p.drawLine(QPointF(0, y), QPointF(W, y))


def scanlines(p):
    p.save()
    p.setPen(Qt.PenStyle.NoPen)
    for y in range(0, H, 2):
        p.fillRect(QRectF(0, y, W, 0.6), QColor(0, 0, 0, 40))
    p.restore()


# ------------------------------------------------------------------ peças
_sticker = QImage(str(STICKER))


def sticker(p, t):
    k_in = out_back(prog(t, 0.25, 0.75), 1.9)
    k_out = in_out(prog(t, 6.15, 6.5))
    if k_in <= 0 or k_out >= 1:
        return
    h = 104
    w = h * _sticker.width() / _sticker.height()
    bob = math.sin(t * 2 * math.pi * 0.8) * 1.6 if 0.75 < t < 6.15 else 0
    y = H - h + 6 + (1 - k_in) * 120 + k_out * 120 + bob
    p.drawImage(QRectF(SAFE_L + 2, y, w, h), _sticker)


def cursor(p, x, y, pressed):
    rows = ["#.......", "##......", "#*#.....", "#**#....", "#***#...", "#****#..", "#*****#.", "#**####.",
            "#*#.....", "##......"]
    cell = 1.6 if not pressed else 1.4
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    for r, line in enumerate(rows):
        for c_, ch in enumerate(line):
            if ch in "#*":
                p.fillRect(QRectF(x + c_ * cell, y + r * cell, cell, cell), C("sunken" if ch == "#" else "ink"))
    p.restore()


BUBBLE = QRectF(222, 22, 200, 96)


def bubble_frame(p, alpha):
    if alpha <= 0:
        return
    p.save()
    p.setOpacity(alpha)
    path = chamfer(BUBBLE, 10)
    p.fillPath(path.translated(3, 3), QColor(0, 0, 0, 150))
    p.fillPath(path, C("surface"))
    p.fillRect(QRectF(BUBBLE.x(), BUBBLE.y(), BUBBLE.width() - 10, 2), C("brand"))
    p.setPen(QPen(C("primary"), 1.2))
    p.drawPath(path)
    tail = QPainterPath()  # rabicho apontando para o sticker
    tail.moveTo(BUBBLE.left() + 1, BUBBLE.top() + 58)
    tail.lineTo(BUBBLE.left() - 9, BUBBLE.top() + 70)
    tail.lineTo(BUBBLE.left() + 1, BUBBLE.top() + 70)
    p.fillPath(tail, C("surface"))
    p.drawLine(QPointF(BUBBLE.left() + 1, BUBBLE.top() + 58), QPointF(BUBBLE.left() - 9, BUBBLE.top() + 70))
    p.drawLine(QPointF(BUBBLE.left() - 9, BUBBLE.top() + 70), QPointF(BUBBLE.left() + 1, BUBBLE.top() + 70))
    p.restore()


def scene_canal(p, t):
    frame_a = out_cubic(prog(t, 0.8, 1.0)) * (1 - in_out(prog(t, 6.15, 6.4)))
    bubble_frame(p, frame_a)
    x = BUBBLE.x() + 14
    # parte 1: o convite
    a1 = 1 - in_out(prog(t, 3.85, 4.0))
    if t < 4.0:
        msg = "CLICA AQUI!"
        n = int(len(msg) * prog(t, 1.0, 1.45))
        caret = "_" if 1.0 <= t < 1.6 and int(t * 6) % 2 == 0 else ""  # só com o balão na tela
        text(p, msg[:n] + caret, x, BUBBLE.y() + 34, font("hud", 30, spacing=1), "primary", alpha=a1, glow="primary")
        text(p, "e se inscreve no canal", x, BUBBLE.y() + 54, font("body", 13), "ink",
             alpha=a1 * out_cubic(prog(t, 1.6, 1.9)))
        k = out_back(prog(t, 2.1, 2.45), 1.6)
        if k > 0:
            p.save()
            p.translate(x, BUBBLE.y() + 80)
            p.scale(0.85 + 0.15 * k, 0.85 + 0.15 * k)
            text(p, "@Gamoxkun", 0, 0, font("display", 21, QFont.Weight.Bold), "ink", alpha=a1 * clamp(k),
                 glow="brand")
            p.restore()
    # parte 2: o botão de inscrever sendo clicado
    elif t < 6.4:
        a2 = out_cubic(prog(t, 4.0, 4.2)) * (1 - in_out(prog(t, 6.15, 6.4)))
        text(p, "YOUTUBE.COM/@GAMOXKUN", x, BUBBLE.y() + 24, font("hud", 17, spacing=1), "ink-muted", alpha=a2)
        btn = QRectF(x, BUBBLE.y() + 34, 172, 34)
        pressed = 5.05 <= t < 5.2
        done = t >= 5.2
        p.save()
        p.setOpacity(a2)
        path = chamfer(btn.translated(0, 2 if pressed else 0), 7)
        if not pressed:
            p.fillPath(chamfer(btn.translated(3, 3), 7), QColor(0, 0, 0, 150))
        p.fillPath(path, C("success") if done else C("brand"))
        p.restore()
        label = "VALEU!" if done else "INSCREVER-SE"
        text(p, label, btn.center().x(), btn.y() + 23 + (2 if pressed else 0), font("display", 16, QFont.Weight.Bold),
             "on-success" if done else "on-brand", "center", a2)
        if done:
            k = prog(t, 5.2, 5.75)
            p.save()
            p.setOpacity(a2 * (1 - k))
            p.setPen(QPen(C("success"), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(btn.adjusted(-10 * k, -10 * k, 10 * k, 10 * k), 6, 6)
            p.restore()
        text(p, "toque aqui e vem pro canal", x, BUBBLE.y() + 86, font("body", 11), "ink-muted",
             alpha=a2 * out_cubic(prog(t, 5.4, 5.7)))
        # cursor vindo da direita até o botão
        k1 = in_out(prog(t, 4.35, 4.95))
        sx, sy = BUBBLE.right() + 8, BUBBLE.bottom() + 6
        tx, ty = btn.center().x() + 30, btn.center().y() + 2
        if t < 6.0:
            cursor(p, sx + (tx - sx) * k1, sy + (ty - sy) * k1, pressed)


def scene_anuncie(p, t):
    # varredura de CRT abre e fecha o quadro do "Anuncie aqui"
    open_k = in_out(prog(t, 6.45, 6.8))
    close_k = in_out(prog(t, 9.35, 9.75))
    if open_k <= 0 or close_k >= 1:
        return
    frame = QRectF(SAFE_L + 4, 14, SAFE_R - SAFE_L - 8, 122)
    top = frame.top() + frame.height() * close_k
    bottom = frame.top() + frame.height() * open_k
    vis = QRectF(frame.left(), top, frame.width(), max(0.0, bottom - top))
    p.save()
    p.setClipRect(vis)
    path = chamfer(frame, 12)
    p.fillPath(path, QColor(11, 7, 22, 235))
    # cantos que piscam, como moldura de "espaço livre"
    blink = 1.0 if int(t * 3) % 2 == 0 else 0.45
    p.setPen(QPen(C("primary", int(255 * blink)), 2))
    L = 12
    for cx_, cy_, dx, dy in ((frame.left() + 6, frame.top() + 6, 1, 1), (frame.right() - 6, frame.top() + 6, -1, 1),
                             (frame.left() + 6, frame.bottom() - 6, 1, -1), (frame.right() - 6, frame.bottom() - 6, -1, -1)):
        p.drawLine(QPointF(cx_, cy_), QPointF(cx_ + L * dx, cy_))
        p.drawLine(QPointF(cx_, cy_), QPointF(cx_, cy_ + L * dy))
    k = out_back(prog(t, 6.75, 7.15), 1.5)
    p.translate(W / 2, 74)
    p.scale(0.8 + 0.2 * k, 0.8 + 0.2 * k)
    text(p, "ANUNCIE AQUI", 0, 0, font("display", 36, QFont.Weight.Bold, spacing=1), "ink", "center", clamp(k),
         glow="brand")
    p.restore()
    p.save()
    p.setClipRect(vis)
    text(p, "SEU BANNER NESTE ESPAÇO", W / 2, 104, font("hud", 17, spacing=2), "primary", "center",
         out_cubic(prog(t, 7.2, 7.5)))
    p.restore()
    # a linha da varredura
    for edge, k_ in ((bottom, open_k), (top, close_k)):
        if 0 < k_ < 1:
            p.fillRect(QRectF(frame.left(), edge - 1.5, frame.width(), 3), C("primary", 220))


def frame(t: float) -> QImage:
    im = QImage(W * SCALE, H * SCALE, QImage.Format.Format_RGB32)
    p = QPainter(im)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.scale(SCALE, SCALE)
    background(p, t)
    sticker(p, t)
    scene_canal(p, t)
    scene_anuncie(p, t)
    scanlines(p)
    p.end()
    return im


def main() -> int:
    n = int(DUR * FPS)
    if "--stills" in sys.argv:
        import tempfile
        out = Path(tempfile.gettempdir()) / "promo_stills"
        out.mkdir(exist_ok=True)
        for t in (0.0, 0.6, 1.3, 2.6, 3.95, 4.6, 5.1, 5.6, 6.6, 7.6, 9.5, 9.95):
            frame(t).save(str(out / f"t{t:05.2f}.png"))
        print("quadros em", out)
        return 0
    ffmpeg = os.environ.get("FFMPEG", "ffmpeg")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.Popen(
        [ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W * SCALE}x{H * SCALE}",
         "-r", str(FPS), "-i", "-", "-vf",
         "split[a][b];[a]palettegen=max_colors=256:stats_mode=full[pal];[b][pal]paletteuse=dither=bayer:bayer_scale=4",
         "-loop", "0", str(OUT)], stdin=subprocess.PIPE)
    for i in range(n):
        im = frame(i / FPS)
        proc.stdin.write(bytes(im.constBits()))
    proc.stdin.close()
    proc.wait()
    print(f"GIF em {OUT} ({OUT.stat().st_size / 1024:.0f} KB, {n} quadros)")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
