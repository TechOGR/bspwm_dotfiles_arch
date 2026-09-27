# =============================================================
# Author:  TechOGR
# Repo:    https://github.com/TechOGR/bspwm_dotfiles_arch
#
# wscard - the login card of BetterLock (and its preview) drawn in the
# style of the theme: the same language as the bar skins and workspace
# pills of lib/wspill.py. BetterLock keeps the frosted glass and the
# avatar / texts; this gives it the card's shape (card_mask), frame and
# decorations (paint_card) and the password field (paint_field).
#
# Copyright (C) 2021-2026 TechOGR <https://github.com/TechOGR>
# Licensed under GPL-3.0 license
# =============================================================

import math
import random

import cairo

import wspill as ws
from wspill import PI, rgb, rounded, hline, neon_grad, glow_stroke


def halo(cr, x, y, r, c, a):
    if _FRAME[0] and r > 40:   # a card-sized glow would tint the window
        return
    ws.halo(cr, x, y, r, c, a)

# window frames (paint_window): no interior, no long protrusions, the
# corner radius of picom
_FRAME = [False]
_RADIUS = [None]

RADIUS = {'glass': 26, 'minimal': 16, 'gradient': 26, 'macos': 22, 'liquid': 30, 'fire': 22,
          'nature': 26, 'sketch': 20, 'crystal': 28, 'lava': 20, 'neon': 24, 'holo': 28}
CHAMFER = {'cyber': 24, 'hud': 16}


def style_of():
    """The style the card follows: the whole theme, else the bar skin,
    else the workspaces (None = BetterLock's own card)."""
    try:
        import barconf as bc
        import ricekit
        kit = ricekit.current()
        if kit in ws.FRAMES:
            return kit
        conf = bc.load()
        for key in ('bar_skin', 'ws_style'):
            if conf.get(key) in ws.FRAMES:
                return conf[key]
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────────────────── shapes
def rrect_points(x, y, w, h, r, step=3.0):
    """Points around a rounded rectangle, clockwise, with outward normals."""
    r = min(r, w / 2, h / 2)
    pts = []

    def edge(x0, y0, x1, y1, nx, ny):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        for i in range(n):
            t = i / n
            pts.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, nx, ny))

    def corner(cx, cy, a0):
        k = max(3, int(PI * r / 2 / step))
        for i in range(k):
            a = a0 + PI / 2 * i / k
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a), math.cos(a), math.sin(a)))
    edge(x + r, y, x + w - r, y, 0, -1)
    corner(x + w - r, y + r, -PI / 2)
    edge(x + w, y + r, x + w, y + h - r, 1, 0)
    corner(x + w - r, y + h - r, 0)
    edge(x + w - r, y + h, x + r, y + h, 0, 1)
    corner(x + r, y + h - r, PI / 2)
    edge(x, y + h - r, x, y + r, -1, 0)
    corner(x + r, y + r, PI)
    return pts


def poly(cr, pts):
    cr.new_path()
    for i, (px, py, *_n) in enumerate(pts):
        (cr.move_to if i == 0 else cr.line_to)(px, py)
    cr.close_path()


def chamfer(cr, x, y, w, h, c):
    cr.new_path()
    cr.move_to(x + c, y)
    cr.line_to(x + w - c, y)
    cr.line_to(x + w, y + c)
    cr.line_to(x + w, y + h - c)
    cr.line_to(x + w - c, y + h)
    cr.line_to(x + c, y + h)
    cr.line_to(x, y + h - c)
    cr.line_to(x, y + c)
    cr.close_path()


def notched(cr, x, y, w, h, q):
    cr.new_path()
    pts = [(2 * q, 0), (w - 2 * q, 0), (w - 2 * q, q), (w - q, q), (w - q, 2 * q), (w, 2 * q),
           (w, h - 2 * q), (w - q, h - 2 * q), (w - q, h - q), (w - 2 * q, h - q), (w - 2 * q, h),
           (2 * q, h), (2 * q, h - q), (q, h - q), (q, h - 2 * q), (0, h - 2 * q), (0, 2 * q),
           (q, 2 * q), (q, q), (2 * q, q)]
    for i, (px, py) in enumerate(pts):
        (cr.move_to if i == 0 else cr.line_to)(x + px, y + py)
    cr.close_path()


def wavy(x, y, w, h, r, amp, seed):
    rnd = random.Random(seed)
    ph = [rnd.uniform(0, 6) for _ in range(3)]
    pts = rrect_points(x, y, w, h, r, 2.5)
    n = len(pts)
    out = []
    for i, (px, py, nx, ny) in enumerate(pts):
        t = i / n * 2 * PI
        o = amp * (0.6 * math.sin(t * 5 + ph[0]) + 0.4 * math.sin(t * 9 + ph[1]))
        out.append((px + nx * o, py + ny * o, nx, ny))
    return out


def shape(cr, style, x, y, w, h, s):
    """The card's outline as the current path."""
    if style in CHAMFER:
        chamfer(cr, x, y, w, h, CHAMFER[style] * s)
    elif style == 'pixel':
        q = max(3, round(4 * s))
        notched(cr, round(x), round(y), round(w / q) * q, round(h / q) * q, q)
    elif style == 'liquid':
        r = _RADIUS[0] if _RADIUS[0] is not None else RADIUS['liquid'] * s
        poly(cr, wavy(x, y, w, h, max(r, 4), 3 * s, 7))
    elif style == 'lava':
        ws.jagged(cr, rrect_points(x, y, w, h, RADIUS['lava'] * s, 3), random.Random(3), 2.2 * s, smooth=1)
    else:
        r = _RADIUS[0] if _RADIUS[0] is not None else RADIUS.get(style, 24) * s
        rounded(cr, x, y, w, h, r)


def card_mask(style, w, h, s):
    """8-bit alpha of the card shape (for the frost and the shadow)."""
    surf = cairo.ImageSurface(cairo.FORMAT_A8, w, h)
    cr = cairo.Context(surf)
    shape(cr, style, 1, 1, w - 2, h - 2, s)
    cr.set_source_rgba(0, 0, 0, 1)
    cr.fill()
    surf.flush()
    return surf


# ─────────────────────────────────────────────────────────── card
def paint_card(cr, style, x, y, w, h, s, part='locks'):
    """Frame, tint and decorations of the card (the frost is under it)."""
    p = lambda: shape(cr, style, x, y, w, h, s)  # noqa: E731
    cx, cy = x + w / 2, y + h / 2
    fn = CARDS.get(style)
    if fn:
        with ws.tinted(style, ws.tint_target(part)):
            fn(cr, p, x, y, w, h, cx, cy, s)


WINDOW_SCALE = 0.8   # decorations of a window frame vs a lock card
WINDOW_REACH = 44     # px they may draw outside the window (overlay margin)


def paint_window(cr, style, x, y, w, h, radius, focused):
    """The frame of a window in the style (bin/RoundBorders draws it right
    above the window): the card's frame and ornaments without its inside,
    dimmed when the window has no focus."""
    _FRAME[0], _RADIUS[0] = True, float(radius)
    try:
        cr.push_group()
        # a soft inner glow along the frame gives it depth
        with ws.tinted(style, ws.tint_target('windows')):
            glow = ws.rgb(ws.NATIVE.get(style, '#6fa8ff'))
        cr.save()
        shape(cr, style, x, y, w, h, WINDOW_SCALE)
        cr.clip()
        for width, a in ((22, 0.05), (12, 0.08), (5, 0.12)):
            shape(cr, style, x, y, w, h, WINDOW_SCALE)
            cr.set_line_width(width)
            cr.set_source_rgba(*glow, a)
            cr.stroke()
        cr.restore()
        paint_card(cr, style, x, y, w, h, WINDOW_SCALE, part='windows')
        cr.pop_group_to_source()
        cr.paint_with_alpha(1.0 if focused else 0.45)
    finally:
        _FRAME[0], _RADIUS[0] = False, None


def _tint(cr, p, col, a):
    if _FRAME[0]:
        return
    p()
    cr.set_source_rgba(*rgb(col), a)
    cr.fill()


def _gloss(cr, x, y, w, h, s, a=0.16):
    if _FRAME[0]:
        return
    g = cairo.LinearGradient(0, y, 0, y + h * 0.4)
    g.add_color_stop_rgba(0, 1, 1, 1, a)
    g.add_color_stop_rgba(1, 1, 1, 1, 0)
    cr.set_source(g)
    cr.rectangle(x, y, w, h * 0.4)
    cr.fill()


def _far(*_a):
    """Decorations reaching far from the frame: cards only (on a window
    they would cover the neighbours)."""
    return not _FRAME[0]


def card_glass(cr, p, x, y, w, h, cx, cy, s):
    blue = rgb('#6fa8ff')
    _tint(cr, p, '#0f1530', 0.30)
    cr.save(); p(); cr.clip(); _gloss(cr, x, y, w, h, s, 0.18); cr.restore()  # noqa: E702
    glow_stroke(cr, p, blue, 1.4 * s, layers=((14 * s, 0.04), (7 * s, 0.09)))
    p()
    rim = cairo.LinearGradient(0, y, 0, y + h)
    rim.add_color_stop_rgba(0, 1, 1, 1, 0.75)
    rim.add_color_stop_rgba(1, 0.6, 0.75, 1, 0.3)
    cr.set_source(rim)
    cr.set_line_width(1.6 * s)
    cr.stroke()
    for dy in ((-0.22, 0.22) if _far() else ()):   # light lines leaving the sides
        yy = cy + dy * 60 * s
        hline(cr, x - 90 * s, x, yy, blue, 0, 0.6, 1.2 * s)
        hline(cr, x + w, x + w + 90 * s, yy, blue, 0.6, 0, 1.2 * s)


def card_cyber(cr, p, x, y, w, h, cx, cy, s):
    cyan, mag = rgb('#19e6ff'), rgb('#ff2bd6')
    _tint(cr, p, '#0a0614', 0.55)
    for extra, a in ((12 * s, 0.06), (6 * s, 0.14), (0, 1)):
        p()
        cr.set_line_width(2 * s + extra)
        g = cairo.LinearGradient(x, y, x + w, y + h)
        g.add_color_stop_rgba(0, *cyan, a)
        g.add_color_stop_rgba(1, *mag, a)
        cr.set_source(g)
        cr.stroke()
    c, o = CHAMFER['cyber'] * s, 8 * s
    for sx, sy, col in ((x, y, cyan), (x + w, y, mag), (x, y + h, cyan), (x + w, y + h, mag)):
        dx, dy = (1 if sx == x else -1), (1 if sy == y else -1)
        cr.move_to(sx - dx * o, sy + dy * (c + 30 * s))
        cr.line_to(sx - dx * o, sy + dy * (c - o * 0.4))
        cr.line_to(sx + dx * (c - o * 0.4), sy - dy * o)
        cr.line_to(sx + dx * (c + 30 * s), sy - dy * o)
        cr.set_line_width(1.6 * s)
        cr.set_source_rgba(*col, 0.85)
        cr.stroke()
    if _far():
        hline(cr, x - 100 * s, x - 12 * s, cy, cyan, 0.05, 0.9, 1.4 * s)
        hline(cr, x + w + 12 * s, x + w + 100 * s, cy, mag, 0.9, 0.05, 1.4 * s)


def card_minimal(cr, p, x, y, w, h, cx, cy, s):
    _tint(cr, p, '#0e1016', 0.55)
    p()
    cr.set_source_rgba(*rgb('#3a4058'), 1)
    cr.set_line_width(1.2 * s)
    cr.stroke()


def card_gradient(cr, p, x, y, w, h, cx, cy, s):
    cr.save(); p(); cr.clip()  # noqa: E702
    if _FRAME[0]:
        cr.new_path()
        cr.rectangle(0, 0, 0, 0)
        cr.clip()
    g = cairo.LinearGradient(x, y, x + w, y + h)
    for t, col, a in ((0, '#2462ff', 0.40), (0.5, '#6a3cf5', 0.32), (1, '#d63cf5', 0.40)):
        g.add_color_stop_rgba(t, *rgb(col), a)
    cr.set_source(g)
    cr.paint()
    _gloss(cr, x, y, w, h, s, 0.22)
    cr.restore()
    for extra, a in ((16 * s, 0.05), (8 * s, 0.12), (0, 1)):
        p()
        cr.set_line_width(2.4 * s + extra)
        cr.set_source(neon_grad(x, x + w, ['#2f6bff', '#8b3dff', '#e040fb'], a))
        cr.stroke()


def card_pixel(cr, p, x, y, w, h, cx, cy, s):
    q = max(3, round(4 * s))
    x0, y0 = round(x), round(y)
    ww, hh = round(w / q) * q, round(h / q) * q
    _tint(cr, p, '#050a1f', 0.6)
    for inset, col in ((0, '#1f5bff'), (q, '#4f86ff')):
        # a ring = outer shape + inner shape, filled even-odd
        notched(cr, x0 + inset, y0 + inset, ww - 2 * inset, hh - 2 * inset, q)
        outer = cr.copy_path()
        notched(cr, x0 + inset + q, y0 + inset + q, ww - 2 * inset - 2 * q, hh - 2 * inset - 2 * q, q)
        cr.append_path(outer)
        cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
        cr.set_source_rgb(*rgb(col))
        cr.fill()
        cr.set_fill_rule(cairo.FILL_RULE_WINDING)
    for side, bx in (((-1, x0), (1, x0 + ww)) if _far() else ()):
        for i in range(8):
            cr.rectangle(bx + side * (2 + i * 2) * q - (q if side < 0 else 0), cy, q, q)
            cr.set_source_rgba(*rgb('#4f86ff'), max(0.1, 0.8 - i * 0.1))
            cr.fill()


def card_macos(cr, p, x, y, w, h, cx, cy, s):
    _tint(cr, p, '#2a3048', 0.35)
    cr.save(); p(); cr.clip(); _gloss(cr, x, y, w, h, s, 0.10); cr.restore()  # noqa: E702
    p()
    cr.set_source_rgba(1, 1, 1, 0.22)
    cr.set_line_width(1.2 * s)
    cr.stroke()


def card_liquid(cr, p, x, y, w, h, cx, cy, s):
    halo(cr, x + w * 0.2, y + h * 0.2, w * 0.7, rgb('#20c8ff'), 0.20)
    halo(cr, x + w * 0.8, y + h * 0.85, w * 0.7, rgb('#a45bff'), 0.20)
    cr.save(); p(); cr.clip()  # noqa: E702
    if _FRAME[0]:
        cr.new_path()
        cr.rectangle(0, 0, 0, 0)
        cr.clip()
    g = cairo.LinearGradient(x, y, x + w, y + h)
    for t, col, a in ((0, '#34dcff', 0.30), (0.5, '#5c86ff', 0.24), (1, '#b37cff', 0.30)):
        g.add_color_stop_rgba(t, *rgb(col), a)
    cr.set_source(g)
    cr.paint()
    _gloss(cr, x, y, w, h, s, 0.28)
    cr.restore()
    for extra, a in ((12 * s, 0.07), (5 * s, 0.16), (0, 0.95)):
        p()
        cr.set_line_width(2.2 * s + extra)
        cr.set_source(neon_grad(x, x + w, ['#34dcff', '#5c86ff', '#b37cff'], a))
        cr.stroke()
    for bx, by, br, col in ((x - 16 * s, y + h * 0.3, 7, '#34dcff'), (x - 30 * s, y + h * 0.22, 3.5, '#34dcff'),
                            (x + w + 18 * s, y + h * 0.7, 8, '#b37cff'), (x + w + 34 * s, y + h * 0.78, 4, '#b37cff'),
                            (x + w * 0.2, y + h + 14 * s, 4, '#5c86ff')):
        br *= s
        halo(cr, bx, by, br * 2.4, rgb(col), 0.4)
        cr.arc(bx, by, br, 0, 2 * PI)
        cr.set_source_rgba(*rgb(col), 0.95)
        cr.fill()
        cr.arc(bx - br * 0.3, by - br * 0.35, br * 0.35, 0, 2 * PI)
        cr.set_source_rgba(1, 1, 1, 0.6)
        cr.fill()


def card_hud(cr, p, x, y, w, h, cx, cy, s):
    blue, soft = rgb('#2d8cff'), rgb('#7fc6ff')
    _tint(cr, p, '#050c18', 0.55)
    glow_stroke(cr, p, blue, 1.2 * s, layers=((8 * s, 0.07), (3 * s, 0.16)))
    L, c = 34 * s, CHAMFER['hud'] * s
    for sx, sy in ((x, y), (x + w, y), (x, y + h), (x + w, y + h)):
        dx, dy = (1 if sx == x else -1), (1 if sy == y else -1)
        cr.move_to(sx + dx * (c + 6 * s), sy + dy * 5 * s)
        cr.line_to(sx + dx * (c + 6 * s + L), sy + dy * 5 * s)
        cr.move_to(sx + dx * 5 * s, sy + dy * (c + 6 * s))
        cr.line_to(sx + dx * 5 * s, sy + dy * (c + 6 * s + L))
    cr.set_line_width(2 * s)
    cr.set_source_rgba(*soft, 0.85)
    cr.stroke()
    for side, bx in (((-1, x), (1, x + w)) if _far() else ()):   # tech lines + node, like the bar ends
        x1 = bx + side * 110 * s
        hline(cr, *sorted((bx, x1)), cy, blue, *((0.15, 0.95) if side < 0 else (0.95, 0.15)), 1.3 * s)
        halo(cr, x1, cy, 8 * s, blue, 0.5)
        cr.arc(x1, cy, 2.6 * s, 0, 2 * PI)
        cr.set_source_rgba(*soft, 1)
        cr.fill()
    for i in range(int(w / (14 * s))):
        tx = x + c + 10 * s + i * 14 * s
        if tx > x + w - c - 10 * s:
            break
        cr.move_to(tx, y + h - 2 * s)
        cr.line_to(tx, y + h - (7 if i % 4 == 0 else 4) * s)
    cr.set_line_width(1 * s)
    cr.set_source_rgba(*blue, 0.5)
    cr.stroke()


def _flame(cr, fx, fy, dx, dy, length, width, a=0.95):
    orange, yellow = rgb('#ff6a00'), rgb('#ffc400')
    nx, ny = -dy, dx
    tx, ty = fx + dx * length, fy + dy * length
    cr.new_path()
    cr.move_to(fx + nx * width, fy + ny * width)
    cr.curve_to(fx + nx * width + dx * length * 0.5, fy + ny * width + dy * length * 0.5,
                tx + nx * width * 0.4, ty + ny * width * 0.4, tx, ty)
    cr.curve_to(tx - nx * width * 0.2, ty - ny * width * 0.2,
                fx - nx * width + dx * length * 0.3, fy - ny * width + dy * length * 0.3,
                fx - nx * width, fy - ny * width)
    cr.close_path()
    g = cairo.LinearGradient(fx, fy, tx, ty)
    g.add_color_stop_rgba(0, *orange, a)
    g.add_color_stop_rgba(0.6, *yellow, a * 0.55)
    g.add_color_stop_rgba(1, *yellow, 0)
    cr.set_source(g)
    cr.fill()


def card_fire(cr, p, x, y, w, h, cx, cy, s):
    rnd = random.Random(17)
    orange = rgb('#ff6a00')
    halo(cr, cx, y + h, w * 0.8, rgb('#ff2a00'), 0.25)
    for fx_, fy_, nx, ny in rrect_points(x, y, w, h, RADIUS['fire'] * s, 9 * s):
        if ny < 0.2 and rnd.random() < 0.7:   # flames lick up and out, not down
            length = rnd.uniform(8, 30 if ny < -0.5 else 22) * s
            _flame(cr, fx_, fy_, nx * 0.6 + rnd.uniform(-0.2, 0.2), min(ny, 0) - 0.5, length, rnd.uniform(3, 6) * s)
    _tint(cr, p, '#120604', 0.55)
    grad = cairo.LinearGradient(0, y, 0, y + h)
    grad.add_color_stop_rgb(0, *rgb('#ffc400'))
    grad.add_color_stop_rgb(1, *orange)
    glow_stroke(cr, p, orange, 2 * s, layers=((12 * s, 0.08), (5 * s, 0.2)), source=grad)
    reach = 60 * s if _far() else 10
    for _ in range(40 if _far() else int(w / 25)):
        cr.arc(rnd.uniform(x - reach, x + w + reach), rnd.uniform(y - reach, y + h * 0.6), rnd.uniform(0.8, 2) * s,
               0, 2 * PI)
        cr.set_source_rgba(*rgb(rnd.choice(['#ff7a18', '#ffc400', '#ff3a00'])), rnd.uniform(0.3, 0.85))
        cr.fill()


def card_nature(cr, p, x, y, w, h, cx, cy, s):
    green = rgb('#2ee06f')
    halo(cr, cx, cy, w * 0.8, rgb('#0c5a2a'), 0.3)
    _tint(cr, p, '#06140c', 0.5)
    glow_stroke(cr, p, green, 2 * s, layers=((12 * s, 0.06), (5 * s, 0.15)))
    L = 92 * s
    bunch = [(-0.5, 1.0, '#2fbf55'), (0.45, 0.9, '#1f8f3a'), (-1.1, 0.75, '#6fdc7f'),
             (0.05, 0.8, '#3fd46a'), (1.0, 0.65, '#58c96a'), (-0.2, 0.55, '#8ff09a')]
    for (sx, sy, base) in ((x + 8 * s, y + 8 * s, -3 * PI / 4), (x + w - 8 * s, y + h - 8 * s, PI / 4),
                           (x + w - 8 * s, y + 8 * s, -PI / 4), (x + 8 * s, y + h - 8 * s, 3 * PI / 4)):
        big = sy < cy and sx < cx or sy > cy and sx > cx
        for ang, k, col in (bunch if big else bunch[:3]):
            ws.leaf(cr, sx, sy, L * k * (1 if big else 0.6), base + ang * 0.7, rgb(col))


def card_sketch(cr, p, x, y, w, h, cx, cy, s):
    lead = rgb('#d6d6d6')
    _tint(cr, p, '#141414', 0.6)
    ws.hatch(cr, p, (x, y + h * 0.7, w, h * 0.3), lead, spacing=7 * s, alpha=0.07, width=0.8 * s)
    ws.sketch_stroke(cr, p, lead, passes=5, jitter=1.6 * s, width=1.5 * s, alpha=0.7, seed=5)
    ws.sketch_stroke(cr, lambda: shape(cr, 'sketch', x + 6 * s, y + 6 * s, w - 12 * s, h - 12 * s, s), lead,
                     passes=3, jitter=1 * s, width=1 * s, alpha=0.4, seed=6)
    rnd = random.Random(8)
    k = 1 if _far() else 0.25   # draft lines overshoot less on a window
    for yy in (y - 1, y + h + 1):
        cr.move_to(x - rnd.uniform(30, 60) * s * k, yy)
        cr.line_to(x + w + rnd.uniform(30, 60) * s * k, yy)
    for xx in (x - 1, x + w + 1):
        cr.move_to(xx, y - rnd.uniform(30, 50) * s * k)
        cr.line_to(xx, y + h + rnd.uniform(30, 50) * s * k)
    cr.set_line_width(0.8 * s)
    cr.set_source_rgba(*lead, 0.25)
    cr.stroke()
    if not _far():
        return
    kx, ky = x + w + 36 * s, y - 20 * s
    crown = lambda: (cr.new_path(), cr.move_to(kx - 16 * s, ky + 12 * s), cr.line_to(kx - 16 * s, ky - 6 * s),  # noqa
                     cr.line_to(kx - 8 * s, ky + 3 * s), cr.line_to(kx, ky - 12 * s), cr.line_to(kx + 8 * s, ky + 3 * s),
                     cr.line_to(kx + 16 * s, ky - 6 * s), cr.line_to(kx + 16 * s, ky + 12 * s), cr.close_path())
    ws.sketch_stroke(cr, crown, lead, passes=3, jitter=0.8 * s, width=1.3 * s, alpha=0.85, seed=9)


def card_crystal(cr, p, x, y, w, h, cx, cy, s):
    ice, blue = rgb('#bfe6ff'), rgb('#2f8cff')
    halo(cr, x + w * 0.2, y + h * 0.3, w * 0.7, blue, 0.16)
    _tint(cr, p, '#0a1228', 0.25)
    cr.save(); p(); cr.clip(); _gloss(cr, x, y, w, h, s, 0.22); cr.restore()  # noqa: E702
    glow_stroke(cr, p, blue, 1, layers=((16 * s, 0.05), (8 * s, 0.10)))
    p()
    rim = cairo.LinearGradient(0, y, 0, y + h)
    rim.add_color_stop_rgba(0, 1, 1, 1, 0.95)
    rim.add_color_stop_rgba(0.5, *ice, 0.45)
    rim.add_color_stop_rgba(1, *rgb('#6fc8ff'), 0.9)
    cr.set_source(rim)
    cr.set_line_width(2.6 * s)
    cr.stroke()
    shape(cr, 'crystal', x + 5 * s, y + 5 * s, w - 10 * s, h - 10 * s, s)
    cr.set_source_rgba(1, 1, 1, 0.2)
    cr.set_line_width(1 * s)
    cr.stroke()
    cr.move_to(x + 40 * s, y + 6 * s)
    cr.line_to(x + w * 0.55, y + 6 * s)
    cr.set_line_width(2 * s)
    cr.set_source(ws.hfade(x + 40 * s, x + w * 0.55, (1, 1, 1), 0.85, 0))
    cr.stroke()
    ws.sparkle(cr, x + w - 22 * s, y + 4 * s, 11 * s, (1, 1, 1), 0.95)
    ws.sparkle(cr, x + 14 * s, y + h - 16 * s, 6 * s, ice, 0.8)


def card_lava(cr, p, x, y, w, h, cx, cy, s):
    rnd = random.Random(23)
    halo(cr, cx, y + h, w * 0.8, rgb('#ff2a00'), 0.28)
    pts = rrect_points(x, y, w, h, RADIUS['lava'] * s, 3)
    ws.jagged(cr, [(px + nx * 9 * s, py + ny * 9 * s, nx, ny) for px, py, nx, ny in pts], rnd, 4 * s, smooth=1)
    outer = cr.copy_path()
    ws.jagged(cr, pts, random.Random(3), 2.2 * s, smooth=1)
    cr.append_path(outer)
    cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    g = cairo.LinearGradient(0, y, 0, y + h)
    g.add_color_stop_rgb(0, *rgb('#3a2319'))
    g.add_color_stop_rgb(1, *rgb('#1a0d08'))
    cr.set_source(g)
    cr.fill()
    cr.set_fill_rule(cairo.FILL_RULE_WINDING)
    _tint(cr, p, '#0d0604', 0.5)
    for extra, a, col in ((12 * s, 0.10, '#ff2a00'), (6 * s, 0.22, '#ff4a00'), (2.6 * s, 0.9, '#ff6a00'),
                          (1.1 * s, 1, '#ffd23a')):
        p()
        cr.set_line_width(extra)
        cr.set_source_rgba(*rgb(col), a)
        cr.stroke()
    for px_, py_, nx, ny in pts[::7]:   # glowing cracks into the rock
        if rnd.random() < 0.6:
            L = rnd.uniform(5, 10) * s
            cr.move_to(px_, py_)
            cr.line_to(px_ + nx * L * 0.5 + rnd.uniform(-3, 3) * s, py_ + ny * L * 0.5)
            cr.line_to(px_ + nx * L + rnd.uniform(-3, 3) * s, py_ + ny * L)
    cr.set_line_width(1.3 * s)
    cr.set_source_rgba(*rgb('#ff7a18'), 0.9)
    cr.stroke()
    for side, bx in (((-1, x - 16 * s), (1, x + w + 16 * s)) if _far() else ()):
        for _ in range(5):
            ws.rock_shard(cr, bx + side * rnd.uniform(0, 60) * s, cy + rnd.uniform(-h / 2, h / 2),
                          rnd.uniform(4, 9) * s, rnd)


def card_neon(cr, p, x, y, w, h, cx, cy, s):
    stops = ['#19d4ff', '#2f6bff', '#8b3dff', '#ff3fd8']
    _tint(cr, p, '#070a18', 0.55)
    for extra, a in ((20 * s, 0.05), (12 * s, 0.10), (6 * s, 0.22), (0, 1)):
        p()
        cr.set_line_width(3 * s + extra)
        g = cairo.LinearGradient(x, y, x + w, y + h)
        for i, col in enumerate(stops):
            g.add_color_stop_rgba(i / 3, *rgb(col), a)
        cr.set_source(g)
        cr.stroke()
    shape(cr, 'neon', x + 1.5 * s, y + 1.5 * s, w - 3 * s, h - 3 * s, s)
    cr.set_source_rgba(1, 1, 1, 0.5)
    cr.set_line_width(0.9 * s)
    cr.stroke()


def card_holo(cr, p, x, y, w, h, cx, cy, s):
    if _far():
        ws.stars(cr, (x - 160 * s, y - 120 * s, w + 320 * s, h + 240 * s), 120, 71)
    else:   # a few stars along the frame
        ws.stars(cr, (x - 6, y - 6, w + 12, 12), int(w / 40), 71)
        ws.stars(cr, (x - 6, y + h - 6, w + 12, 12), int(w / 40), 72)
    halo(cr, x, y + h * 0.3, w * 0.7, rgb('#3b5bff'), 0.22)
    halo(cr, x + w, y + h * 0.7, w * 0.7, rgb('#c03cff'), 0.22)
    for dx, dy, rot, a in (((70, 26, -0.18, 0.55), (46, 40, 0.12, 0.35)) if _far() else ()):
        ws.orbit(cr, cx, cy, w / 2 + dx * s, h / 2 + dy * s * 0.4, rot, a, width=1.4 * s, beads=(dx == 70))
    cr.save(); p(); cr.clip()  # noqa: E702
    if _FRAME[0]:
        cr.new_path()
        cr.rectangle(0, 0, 0, 0)
        cr.clip()
    g = cairo.LinearGradient(x, y, x + w, y + h)
    for t, col, a in ((0, '#1b3cff', 0.22), (0.5, '#6a3cff', 0.18), (1, '#ff4fd8', 0.22)):
        g.add_color_stop_rgba(t, *rgb(col), a)
    cr.set_source(g)
    cr.paint()
    _gloss(cr, x, y, w, h, s, 0.2)
    cr.restore()
    glow_stroke(cr, p, rgb('#b07cff'), 2 * s, layers=((12 * s, 0.07), (5 * s, 0.18)),
                source=neon_grad(x, x + w, ['#8fe6ff', '#ffffff', '#ffb8f0'], 0.9))


CARDS = {'glass': card_glass, 'cyber': card_cyber, 'minimal': card_minimal, 'gradient': card_gradient,
         'pixel': card_pixel, 'macos': card_macos, 'liquid': card_liquid, 'hud': card_hud, 'fire': card_fire,
         'nature': card_nature, 'sketch': card_sketch, 'crystal': card_crystal, 'lava': card_lava,
         'neon': card_neon, 'holo': card_holo}


# ─────────────────────────────────────────────────── password field
FIELD = {
    'glass': ('#6fa8ff', '#ffffff'), 'cyber': ('#19e6ff', '#ff2bd6'), 'minimal': ('#3a4058', '#5a6385'),
    'gradient': ('#2f6bff', '#e040fb'), 'pixel': ('#1f5bff', '#4f86ff'), 'macos': ('#5b8cff', '#ffffff'),
    'liquid': ('#34dcff', '#b37cff'), 'hud': ('#2d8cff', '#7fc6ff'), 'fire': ('#ff6a00', '#ffc400'),
    'nature': ('#2ee06f', '#9be07a'), 'sketch': ('#d6d6d6', '#d6d6d6'), 'crystal': ('#bfe6ff', '#ffffff'),
    'lava': ('#ff6a00', '#ffd23a'), 'neon': ('#19d4ff', '#ff3fd8'), 'holo': ('#4fd8ff', '#ff8ae0'),
}


def paint_field(cr, style, x, y, w, h, s):
    with ws.tinted(style, ws.tint_target('locks')):
        _paint_field(cr, style, x, y, w, h, s)


def _paint_field(cr, style, x, y, w, h, s):
    a, b = FIELD.get(style, ('#6fa8ff', '#bb9af7'))
    if style in CHAMFER:
        p = lambda: chamfer(cr, x, y, w, h, h * 0.35)  # noqa: E731
    elif style == 'pixel':
        q = max(2, round(3 * s))
        p = lambda: notched(cr, round(x), round(y), round(w / q) * q, round(h / q) * q, q)  # noqa: E731
    else:
        p = lambda: rounded(cr, x, y, w, h, h / 2 if style != 'minimal' else 10 * s)  # noqa: E731
    p()
    cr.set_source_rgba(0, 0, 0, 0.45)
    cr.fill()
    if style == 'sketch':
        ws.sketch_stroke(cr, p, rgb(a), passes=3, jitter=1 * s, width=1.1 * s, alpha=0.7, seed=12)
        return
    glow = style in ('cyber', 'neon', 'gradient', 'liquid', 'hud', 'fire', 'nature', 'lava', 'holo', 'crystal')
    for extra, al in (((8 * s, 0.08), (4 * s, 0.16)) if glow else ()):
        p()
        cr.set_line_width(1.6 * s + extra)
        cr.set_source(neon_grad(x, x + w, [a, b], al))
        cr.stroke()
    p()
    cr.set_line_width(1.6 * s)
    cr.set_source(neon_grad(x, x + w, [a, b], 0.95))
    cr.stroke()


# ═══════════════════════════════════════════ command line (ScreenLocker)
def panel(src, dst, x, y, w, h, s, bg, style):
    """Frosted panel in the style's shape + its frame, onto an image."""
    from PIL import Image, ImageFilter
    img = Image.open(src).convert('RGB')
    region = img.crop((x, y, x + w, y + h))
    small = region.resize((max(1, w // 4), max(1, h // 4)), Image.BILINEAR)
    frost = small.filter(ImageFilter.GaussianBlur(6)).resize((w, h), Image.BICUBIC)
    frost = Image.blend(frost, Image.new('RGB', (w, h), bg), 0.62)
    m = card_mask(style, w, h, s)
    m.flush()
    mask = Image.frombuffer('L', (w, h), bytes(m.get_data()), 'raw', 'L', m.get_stride(), 1)
    img.paste(frost, (x, y), mask)
    over = cairo.ImageSurface(cairo.FORMAT_ARGB32, *img.size)
    paint_card(cairo.Context(over), style, x, y, w, h, s)
    over.flush()
    ov = Image.frombuffer('RGBA', img.size, bytes(over.get_data()), 'raw', 'BGRa', over.get_stride(), 1)
    img.paste(ov, (0, 0), ov)
    img.save(dst, compress_level=1)


if __name__ == '__main__':
    import sys
    args = sys.argv[1:]
    if args[:1] == ['style']:
        # "style tint": the cache key of ScreenLocker needs both
        st = style_of() or ''
        print(st, ws.tint_target('locks') or '' if st else '')
    elif args[:1] == ['panel'] and len(args) == 10:
        src, dst, x, y, w, h, s, bg, style = args[1:]
        h_ = bg.lstrip('#')
        panel(src, dst, int(x), int(y), int(w), int(h), float(s),
              tuple(int(h_[i:i + 2], 16) for i in (0, 2, 4)), style)
    else:
        print('wscard.py style | panel SRC DST X Y W H SCALE BG STYLE', file=sys.stderr)
        sys.exit(1)
