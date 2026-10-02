"""Ícones do Sidekick OS (DESIGN.md, seção Iconography).

- ``icon-ui``: linha HUD na grade 24, traço reto de 2 px, cantos chanfrados, uma cor por estado.
- ``icon-brand``: pixel-art 12x12, só em 48 ou 96 px (momentos de marca).

Os desenhos são os mesmos de ``docs/design/tools/sidekick_icons.py`` (de onde o
manual de identidade é gerado). Mudou um, mude o outro.
"""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen

# ------------------------------------------------------------------ interface (linha HUD)


def _ch_rect(path, x, y, w, h, c=3.0):
    """Retângulo com o canto superior direito chanfrado (o gesto do painel-janela)."""
    path.moveTo(x, y)
    path.lineTo(x + w - c, y)
    path.lineTo(x + w, y + c)
    path.lineTo(x + w, y + h)
    path.lineTo(x, y + h)
    path.closeSubpath()


def _oct(path, x, y, w, h, c=1.5):
    """Octógono: todos os cantos chanfrados (usado para cabeça e pontos)."""
    path.moveTo(x + c, y)
    path.lineTo(x + w - c, y)
    path.lineTo(x + w, y + c)
    path.lineTo(x + w, y + h - c)
    path.lineTo(x + w - c, y + h)
    path.lineTo(x + c, y + h)
    path.lineTo(x, y + h - c)
    path.lineTo(x, y + c)
    path.closeSubpath()


def _poly(path, pts, close=False):
    path.moveTo(*pts[0])
    for pt in pts[1:]:
        path.lineTo(*pt)
    if close:
        path.closeSubpath()


def _ui(name):
    """(contornos, preenchidos) na grade 24x24."""
    s, f = QPainterPath(), QPainterPath()
    if name == "home":  # o robô sidekick
        _ch_rect(s, 4, 8, 16, 11)
        _poly(s, [(12, 8), (12, 4.5)])
        f.addRect(10.5, 2, 3, 3)
        _poly(s, [(7.5, 14), (9.5, 12), (11.5, 14)])
        _poly(s, [(12.5, 14), (14.5, 12), (16.5, 14)])
        _poly(s, [(1.5, 11), (1.5, 16)])
        _poly(s, [(22.5, 11), (22.5, 16)])
    elif name == "plugins":
        _poly(s, [(4, 8), (9, 8), (9, 5), (13, 5), (13, 8), (18, 8), (18, 11), (21, 11), (21, 15),
                  (18, 15), (18, 20), (4, 20)], close=True)
    elif name == "platinas":
        _poly(s, [(7, 4), (17, 4), (17, 10), (14, 13), (10, 13), (7, 10)], close=True)
        _poly(s, [(7, 6), (4, 6), (4, 9), (7, 10)])
        _poly(s, [(17, 6), (20, 6), (20, 9), (17, 10)])
        _poly(s, [(12, 13), (12, 17)])
        _ch_rect(s, 8, 17, 8, 3, 1.5)
    elif name == "hotkey":
        _ch_rect(s, 3, 7, 18, 11)
        for x in (6, 9.5, 13, 16.5):
            f.addRect(x - 0.25, 9.75, 2, 2)
        _poly(s, [(8, 15), (16, 15)])
    elif name == "diagnostics":
        _poly(s, [(2, 12), (7, 12), (9, 6), (13, 18), (15, 12), (22, 12)])
    elif name == "settings":
        for y, kx in ((6, 8), (12, 15), (18, 10)):
            _poly(s, [(3, y), (21, y)])
            f.addRect(kx - 2, y - 2, 4, 4)
    elif name == "help":
        _ch_rect(s, 3, 3, 18, 18, 4)
        _poly(s, [(9, 9), (9, 7), (15, 7), (15, 11), (12, 12.5), (12, 14.5)])
        f.addRect(11, 16, 2, 2)
    elif name == "about":
        _oct(s, 8.5, 3, 7, 7, 2)
        _poly(s, [(4, 21), (4, 17), (8, 13.5), (16, 13.5), (20, 17), (20, 21)])
    elif name == "marker":
        _poly(s, [(6, 3), (18, 3), (18, 21), (12, 16.5), (6, 21)], close=True)
        _poly(s, [(9.5, 8), (14.5, 8)])
        _poly(s, [(9.5, 11.5), (13, 11.5)])
    elif name == "counter":
        _ch_rect(s, 3, 5, 18, 14)
        _poly(s, [(6.5, 12), (11.5, 12)])
        _poly(s, [(9, 9.5), (9, 14.5)])
        _poly(s, [(14.5, 10), (16, 8.5), (16, 15.5)])
        _poly(s, [(14, 15.5), (18, 15.5)])
    elif name == "folder":
        _poly(s, [(3, 5), (10, 5), (12, 8), (21, 8), (21, 19), (3, 19)], close=True)
        _poly(s, [(3, 10.5), (21, 10.5)])
    elif name == "backup":  # disquete
        _ch_rect(s, 4, 4, 16, 16, 3.5)
        _poly(s, [(8, 4), (8, 9), (15, 9), (15, 4)])
        f.addRect(12, 5.5, 1.5, 2)
        _poly(s, [(7.5, 20), (7.5, 13), (16.5, 13), (16.5, 20)])
    elif name == "alert":
        _poly(s, [(12, 3), (21.5, 20), (2.5, 20)], close=True)
        _poly(s, [(12, 9), (12, 14)])
        f.addRect(11, 16, 2, 2)
    elif name == "favorite":  # estrela angular
        pts = [(12, 2.5), (14.6, 8.9), (21.5, 9.2), (16.2, 13.6), (17.9, 20.4), (12, 16.6),
               (6.1, 20.4), (7.8, 13.6), (2.5, 9.2), (9.4, 8.9)]
        _poly(s, pts, close=True)
    elif name == "live":  # transmissão
        f.addRect(10, 10, 4, 4)
        _poly(s, [(8, 8), (6, 12), (8, 16)])
        _poly(s, [(16, 8), (18, 12), (16, 16)])
        _poly(s, [(5, 5), (2, 12), (5, 19)])
        _poly(s, [(19, 5), (22, 12), (19, 19)])
    elif name == "update":  # baixar
        _poly(s, [(12, 3), (12, 14)])
        _poly(s, [(7, 9.5), (12, 14.5), (17, 9.5)])
        _poly(s, [(4, 15), (4, 20), (20, 20), (20, 15)])
    elif name == "popout":  # abrir em janela
        _ch_rect(s, 3, 8, 13, 13, 2.5)
        _poly(s, [(13, 3), (21, 3), (21, 11)])
        _poly(s, [(21, 3), (12, 12)])
    elif name == "remove":  # lixeira
        _poly(s, [(3.5, 6), (20.5, 6)])
        _poly(s, [(9, 6), (9, 3), (15, 3), (15, 6)])
        _poly(s, [(6, 6), (7, 21), (17, 21), (18, 6)])
        _poly(s, [(10, 10), (10, 17)])
        _poly(s, [(14, 10), (14, 17)])
    elif name == "back":
        _poly(s, [(14, 5), (7, 12), (14, 19)])
    elif name == "clip":  # claquete (ClipIt)
        _poly(s, [(3, 4), (21, 4), (21, 8), (3, 8)], close=True)
        _poly(s, [(8, 4), (10, 8)])
        _poly(s, [(14, 4), (16, 8)])
        _poly(s, [(3, 8), (3, 20), (21, 20), (21, 8)])
        _poly(f, [(10, 11.5), (15.5, 14.5), (10, 17.5)], close=True)
    elif name == "power":  # liga (StreamOn)
        _poly(s, [(15.5, 5.5), (20, 10), (20, 16.5), (15.5, 21), (8.5, 21), (4, 16.5), (4, 10), (8.5, 5.5)])
        _poly(s, [(12, 2.5), (12, 11)])
    elif name == "captions":  # legenda (Subtitler)
        _ch_rect(s, 3, 5, 18, 14)
        _poly(s, [(6.5, 11.5), (10, 11.5)])
        _poly(s, [(13, 11.5), (17.5, 11.5)])
        _poly(s, [(6.5, 15), (13, 15)])
        _poly(s, [(15.5, 15), (17.5, 15)])
    else:
        raise KeyError(name)
    return s, f


UI_ICONS = ["home", "plugins", "platinas", "hotkey", "diagnostics", "settings", "help", "about",
            "marker", "counter", "folder", "backup", "alert", "favorite", "live", "update", "popout",
            "remove", "back", "clip", "power", "captions"]
UI_NAMES = {"home": "Início", "plugins": "Plugins", "platinas": "Platinas", "hotkey": "Atalhos",
            "diagnostics": "Diagnóstico", "settings": "Configurações", "help": "Ajuda", "about": "Sobre",
            "marker": "Marcador", "counter": "Contador", "folder": "Pasta", "backup": "Backup",
            "alert": "Alerta", "favorite": "Favorito", "live": "Ao vivo", "update": "Atualizar",
            "popout": "Abrir em janela", "remove": "Remover", "back": "Voltar",
            "clip": "ClipIt", "power": "StreamOn", "captions": "Subtitler"}


def draw_ui(p: QPainter, name, x, y, size, color: QColor, stroke=None):
    """Desenha o ícone de interface. O traço tem 2 px reais em 20 px ou mais, e 1,5 px abaixo."""
    k = size / 24.0
    stroke = stroke or (2.0 if size >= 20 else 1.5)
    s, f = _ui(name)
    p.save()
    p.translate(x, y)
    p.scale(k, k)
    p.setPen(QPen(color, stroke / k, Qt.PenStyle.SolidLine, Qt.PenCapStyle.SquareCap, Qt.PenJoinStyle.MiterJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(s)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    p.drawPath(f)
    p.restore()


# ------------------------------------------------------------------ marca (pixel 12x12)
# '#' cor principal (papel do ícone), '+' acento, '*' tinta clara (ink)
BRAND = {
    "sidekick": ("primary", "brand", [
        ".....++.....", ".....##.....", "..########..", ".#........#.", "##.**..**.##", "##.**..**.##",
        "##........##", ".#..####..#.", "..########..", ".#..........", ".####.......", "............"]),
    "trophy": ("success", "ink", [
        "..########..", "#.#+.....#.#", "#.#+.....#.#", ".##......##.", "..#......#..", "...#....#...",
        "....####....", ".....##.....", ".....##.....", "...######...", "...######...", "............"]),
    "floppy": ("primary", "brand", [
        "##########..", "#.#....#.##.", "#.#..+.#..##", "#.######...#", "#..........#", "#..........#",
        "#.########.#", "#.#******#.#", "#.#......#.#", "#.#******#.#", "#.#......#.#", "############"]),
    "gamepad": ("primary", "brand", [
        "............", "............", ".##########.", "#..........#", "#.#.....+..#", "####...+.+.#",
        "#.#.....+..#", "#..........#", "#...####...#", "##.#....#.##", ".##......##.", "............"]),
    "crt": ("primary", "brand", [
        "############", "#..........#", "#.********.#", "#.*+.....*.#", "#.*......*.#", "#.*......*.#",
        "#.********.#", "#..........#", "############", "....####....", "..########..", "............"]),
    "cassette": ("brand", "primary", [
        "............", "............", "############", "#.********.#", "#..........#", "#.++++++++.#",
        "#.+*+..+*+.#", "#.++++++++.#", "#..........#", "#..######..#", "############", "............"]),
    "star": ("primary", "brand", [
        ".....##.....", ".....##.....", "....####....", "############", ".####**####.", "..########..",
        "...######...", "...######...", "..###..###..", "..##....##..", ".##......##.", "............"]),
    "live": ("brand", "ink", [
        "............", ".#........#.", "#..#....#..#", "#.#..##..#.#", "#.#.#++#.#.#", "#.#..##..#.#",
        "#..#.##.#..#", ".#...##...#.", ".....##.....", "....####....", "...######...", "............"]),
    "puzzle": ("primary", "brand", [
        "............", "....##......", "....##......", ".########...", ".#......#...", ".#..**..###.",
        ".#..**..###.", ".#......#...", ".#......#...", ".########...", "............", "............"]),
    "marker": ("primary", "brand", [
        "..########..", "..#......#..", "..#.++++.#..", "..#......#..", "..#.+++..#..", "..#......#..",
        "..#......#..", "..#......#..", "..#..##..#..", "..#.#..#.#..", "..##....##..", "..#......#.."]),
    "counter": ("primary", "brand", [
        "############", "#..........#", "#.......#..#", "#..+...##..#", "#..+....#..#", "#.+++...#..#",
        "#..+....#..#", "#..+....#..#", "#......###.#", "#..........#", "############", "............"]),
    "clip": ("primary", "brand", [
        "............", "#++##++##++#", "............", "############", "#..........#", "#...*......#",
        "#...**.....#", "#...***....#", "#...**.....#", "#...*......#", "############", "............"]),
    "power": ("primary", "brand", [
        "............", ".....++.....", "..#..++..#..", ".#...++...#.", "#....++....#", "#....++....#",
        "#..........#", "#..........#", ".#........#.", "..#......#..", "...######...", "............"]),
    "captions": ("brand", "primary", [
        "............", "############", "#..........#", "#..........#", "#..........#", "#.+++.****.#",
        "#..........#", "#.****.+++.#", "#..........#", "############", "....#.......", "...##......."]),
}
BRAND_NAMES = {"sidekick": "Sidekick", "trophy": "Troféu", "floppy": "Disquete", "gamepad": "Controle",
               "crt": "Monitor CRT", "cassette": "Fita", "star": "Favorito", "live": "Ao vivo",
               "puzzle": "Plugin", "marker": "Marcador", "counter": "Contador",
               "clip": "ClipIt", "power": "StreamOn", "captions": "Subtitler"}


def draw_brand(p: QPainter, name, x, y, size, palette, main=None, accent=None, grid=False):
    """Pixel-art. `palette(key)` devolve QColor para um token. Tamanho deve ser múltiplo de 12."""
    main_key, acc_key, rows = BRAND[name]
    colors = {"#": palette(main or main_key), "+": palette(accent or acc_key), "*": palette("ink")}
    cell = size / 12.0
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    p.setPen(Qt.PenStyle.NoPen)
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            if ch in colors:
                p.setBrush(colors[ch])
                p.drawRect(QRectF(x + c * cell, y + r * cell, cell, cell))
    if grid:
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(QPen(palette("hairline-strong"), 0.6))
        for i in range(13):
            p.drawLine(QPointF(x + i * cell, y), QPointF(x + i * cell, y + size))
            p.drawLine(QPointF(x, y + i * cell), QPointF(x + size, y + i * cell))
    p.restore()


def validate():
    bad = []
    for k, (_, _, rows) in BRAND.items():
        if len(rows) != 12 or any(len(r) != 12 for r in rows):
            bad.append(k)
    for k in UI_ICONS:
        _ui(k)
    return bad


# ------------------------------------------------------------------ helpers do app
from PySide6.QtGui import QIcon, QPixmap  # noqa: E402

from streamer_sidekick.ui import tokens  # noqa: E402

_cache: dict = {}


def _render(key: tuple, size: int, dpr: float, paint) -> QPixmap:
    full = key + (dpr,)
    if full not in _cache:
        pm = QPixmap(int(round(size * dpr)), int(round(size * dpr)))
        pm.setDevicePixelRatio(dpr)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        paint(p)
        p.end()
        _cache[full] = pm
    return _cache[full]


def _screen_dpr() -> float:
    from PySide6.QtGui import QGuiApplication

    screen = QGuiApplication.primaryScreen()
    return screen.devicePixelRatio() if screen else 1.0


def ui_pixmap(name: str, size: int = 24, color: str = "ink-muted", dpr: float | None = None) -> QPixmap:
    """Pixmap nítido de um ícone de interface (na escala ``dpr``; padrão: tela principal)."""

    def paint(p: QPainter) -> None:
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_ui(p, name, 0, 0, size, tokens.color(color))

    return _render(("ui", name, size, color), size, dpr or _screen_dpr(), paint)


def ui_icon(name: str, size: int = 24, color: str = "ink-muted") -> QIcon:
    """QIcon com 1x e 2x (nítido em qualquer monitor) e os estados do DESIGN.md:
    hover em ``ink`` e desabilitado em ``ink-faint``."""
    icon = QIcon()
    for dpr in (1.0, 2.0):
        icon.addPixmap(ui_pixmap(name, size, color, dpr), QIcon.Mode.Normal)
        icon.addPixmap(ui_pixmap(name, size, "ink-faint", dpr), QIcon.Mode.Disabled)
        if color == "ink-muted":
            icon.addPixmap(ui_pixmap(name, size, "ink", dpr), QIcon.Mode.Active)
    return icon


def brand_pixmap(name: str, size: int = 48, dpr: float | None = None) -> QPixmap:
    """Ícone de marca em pixel. ``size`` deve ser múltiplo de 12 (48 ou 96)."""

    def paint(p: QPainter) -> None:
        draw_brand(p, name, 0, 0, size, tokens.color)

    return _render(("brand", name, size), size, dpr or _screen_dpr(), paint)


def has_ui(name: str) -> bool:
    return name in UI_ICONS


def has_brand(name: str) -> bool:
    return name in BRAND
