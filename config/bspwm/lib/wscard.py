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
import re
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

RADIUS = {'glass': 26, 'minimal': 16, 'liquid': 30, 'fire': 22,
          'nature': 26, 'sketch': 20, 'crystal': 28, 'lava': 20, 'neon': 24, 'holo': 28}
CHAMFER = {'cyber': 24, 'hud': 16, 'crystal': 14}


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


def wavy(x, y, w, h, r, amp, seed, wavelength=170, kind='mix'):
    """Points of a rounded rectangle pushed in and out along its normal.
    kind: 'mix' two sines (water, vines, tentacles), 'sine' one clean sine
    (a slithering snake), 'tongue' pointed crests with a random height each
    (flames). On a window frame the waves keep their length whatever its
    size (and get a bit deeper), so a big window gets many, like the bar."""
    rnd = random.Random(seed)
    ph = [rnd.uniform(0, 6) for _ in range(3)]
    pts = rrect_points(x, y, w, h, r, 2.5)
    n = len(pts)
    k1, k2 = 5, 9
    if _FRAME[0]:
        k1 = max(5, round(2 * (w + h) / wavelength))
        k2 = round(k1 * 1.75)
        amp *= 1.5
    heights = [rnd.uniform(0.45, 1.0) for _ in range(k1 + 1)]
    out = []
    for i, (px, py, nx, ny) in enumerate(pts):
        t = i / n * 2 * PI
        if kind == 'sine':
            o = amp * math.sin(t * k1 + ph[0])
        elif kind == 'tongue':
            u = (t * k1 + ph[0]) / (2 * PI)
            f = u - math.floor(u)
            peak = heights[int(math.floor(u)) % len(heights)]
            o = amp * (2.2 * peak * (1 - abs(2 * f - 1)) ** 3 - 0.35)
        else:
            o = amp * (0.6 * math.sin(t * k1 + ph[0]) + 0.4 * math.sin(t * k2 + ph[1]))
        out.append((px + nx * o, py + ny * o, nx, ny))
    return out


def zigzag(x, y, w, h, r, amp, seed):
    """A lightning outline: straight strokes of random length (4 to 26 px)
    that jump in and out by random amounts, now and then a sharp spike,
    never a regular pattern (a seam of stitches is what regular looks
    like)."""
    rnd = random.Random(seed)
    pts = rrect_points(x, y, w, h, r, 2.0)
    n = len(pts)
    out, i, prev = [], 0, 0.0
    while i < n:
        px, py, nx, ny = pts[i]
        o = rnd.uniform(-1, 1) * amp
        if rnd.random() < 0.12:   # a spike
            o = amp * rnd.uniform(1.6, 2.6) * (1 if prev <= 0 else -1)
        elif abs(o - prev) < amp * 0.5:   # keep it jagged
            o = -o if o else amp * 0.8
        out.append((px + nx * o, py + ny * o, nx, ny))
        prev = o
        i += rnd.choice((2, 3, 4, 5, 6, 8, 10, 13))
    return out


# the outline of each style (wavy/jagged ones also cut the window itself
# to that shape: bin/RoundBorders, window_region)
# style: (amplitude, seed, wave length on a window, kind of wave)
WAVES = {'liquid': (3, 7, 170, 'mix'), 'venom': (3.2, 3, 170, 'mix'), 'butterfly': (2.6, 4, 170, 'mix'),
         'fire': (2.6, 11, 60, 'tongue'), 'nature': (1.6, 13, 170, 'mix'), 'snake': (3.6, 17, 115, 'sine')}
SHAPED = {'cyber', 'hud', 'crystal', 'pixel', 'lava', 'storm', 'sketch'} | set(WAVES)


def snake_ring(x, y, w, h, s):
    """The slithering path of the snake frame (the same wave that cuts
    the window)."""
    amp, seed, wl, kind = WAVES['snake']
    return wavy(x, y, w, h, max(_r('snake', s), 4), amp * s, seed, wl, kind)


def _r(style, s):
    return _RADIUS[0] if _RADIUS[0] is not None else RADIUS.get(style, 24) * s


def shape(cr, style, x, y, w, h, s):
    """The card's outline as the current path."""
    if style in CHAMFER:
        chamfer(cr, x, y, w, h, CHAMFER[style] * s)
    elif style == 'pixel':
        q = max(3, round(4 * s))
        notched(cr, round(x), round(y), round(w / q) * q, round(h / q) * q, q)
    elif style in WAVES:
        amp, seed, wl, kind = WAVES[style]
        poly(cr, wavy(x, y, w, h, max(_r(style, s), 4), amp * s, seed, wl, kind))
    elif style == 'lava':
        ws.jagged(cr, rrect_points(x, y, w, h, RADIUS['lava'] * s, 3), random.Random(3),
                  2.2 * s * (1.4 if _FRAME[0] else 1), smooth=1)
    elif style == 'storm':
        poly(cr, zigzag(x, y, w, h, max(_r(style, s), 4), 3.2 * s * (1.3 if _FRAME[0] else 1), 5))
    elif style == 'sketch':
        ws.jagged(cr, rrect_points(x, y, w, h, max(_r(style, s), 4), 4), random.Random(8), 1.6 * s, smooth=4)
    else:
        rounded(cr, x, y, w, h, _r(style, s))


def alpha_region(surf, dx=0, dy=0, threshold=3):
    """The pixels of an ARGB surface that are not (almost) transparent, as
    a cairo.Region: the X shape of an overlay, so the compositor only
    blends what is actually painted. Runs found with C-speed byte searches
    on the alpha channel; equal rows merge into one rectangle."""
    surf.flush()
    W, H, stride = surf.get_width(), surf.get_height(), surf.get_stride()
    data = bytes(surf.get_data())
    pat = re.compile(b'[' + bytes([threshold]) + b'-\xff]+')   # alpha >= threshold
    reg = cairo.Region()
    prev, y0 = None, 0
    for y in range(H + 1):
        if y < H:
            alpha = data[y * stride + 3:y * stride + W * 4:4]   # BGRA, little-endian
            runs = tuple((m.start(), m.end()) for m in pat.finditer(alpha))
        else:
            runs = None
        if runs != prev:
            if prev:
                for a0, a1 in prev:
                    reg.union(cairo.RectangleInt(a0 + dx, y0 + dy, a1 - a0, y - y0))
            prev, y0 = runs, y
    return reg


def window_outline(cr, style, x, y, w, h, radius):
    """shape() as a window frame draws it (same scale, radius and waves)."""
    _FRAME[0], _RADIUS[0] = True, float(radius)
    try:
        shape(cr, style, x, y, w, h, WINDOW_SCALE)
    finally:
        _FRAME[0], _RADIUS[0] = False, None


def window_region(style, w, h, bw, radius):
    """The X shape of a w x h window (bw border) cut to the style's outline,
    as a cairo.Region in the window's coordinates (the border is outside,
    at negative ones). Only the edge bands are scanned: a middle row is one
    run between its left and right edge, and equal rows merge into one
    rectangle (a few ms even for a full-screen window, so a mouse resize
    stays smooth)."""
    W, H = int(w + 2 * bw), int(h + 2 * bw)
    surf = cairo.ImageSurface(cairo.FORMAT_A8, W, H)
    cr = cairo.Context(surf)
    cr.set_antialias(cairo.ANTIALIAS_NONE)
    window_outline(cr, style, bw / 2, bw / 2, W - bw, H - bw, max(0, radius))
    cr.set_source_rgba(0, 0, 0, 1)
    cr.fill()
    surf.flush()
    stride = surf.get_stride()
    data = bytes(surf.get_data())
    B = min(int(max(radius, 0) + 48), W // 2, H // 2)   # the band where the outline lives
    rows = [None] * H
    # no antialiasing: every pixel is 0 or 255, runs are found with C-speed
    # byte searches (no numpy needed, a few ms for a full-screen window)
    full = re.compile(b'\xff+')
    for yy in range(H):
        row = data[yy * stride:yy * stride + W]
        if B <= yy < H - B:   # a middle row: one run between its edges
            l0, r0 = row.find(b'\xff'), row.rfind(b'\xff')
            rows[yy] = ((l0,), (r0 + 1,)) if l0 >= 0 else ((), ())
        else:
            ms = [(m.start(), m.end()) for m in full.finditer(row)]
            rows[yy] = (tuple(m[0] for m in ms), tuple(m[1] for m in ms))
    reg = cairo.Region()
    y0 = 0
    for yy in range(1, H + 1):
        if yy == H or rows[yy] != rows[y0]:
            for a0, a1 in zip(*rows[y0]):
                reg.union(cairo.RectangleInt(int(a0) - int(bw), y0 - int(bw), int(a1 - a0), yy - y0))
            y0 = yy
    return reg


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
WINDOW_REACH = 64     # px they may draw outside the window (overlay margin)


def paint_window(cr, style, x, y, w, h, radius, focused, inner_glow=True):
    """The frame of a window in the style (bin/RoundBorders draws it right
    above the window): the card's frame and ornaments without its inside,
    dimmed when the window has no focus. inner_glow=False (Lite) leaves out
    the soft glow inside the edge: fewer translucent pixels to composite."""
    _FRAME[0], _RADIUS[0] = True, float(radius)
    try:
        cr.push_group()
        # a soft inner glow along the frame gives it depth
        with ws.tinted(style, ws.tint_target('windows')):
            glow = ws.rgb(ws.NATIVE.get(style, '#6fa8ff'))
        if inner_glow:
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
    if not _far():
        liquid_tube(cr, p, x, y, w, h, s)


def liquid_tube(cr, p, x, y, w, h, s):
    """A window's liquid rim: a thick glossy tube of the gradient, with
    bubbles running in it and drops hanging from the bottom edge."""
    stops = ['#34dcff', '#4f8dff', '#7a5cff', '#b37cff']
    for extra, a in ((18, 0.07), (10, 0.16)):
        p()
        cr.set_line_width(7 + extra)
        cr.set_source(neon_grad(x, x + w, stops, a))
        cr.stroke()
    p()
    cr.set_line_width(7)
    cr.set_source(neon_grad(x, x + w, stops, 0.95))
    cr.stroke()
    cr.save()   # gloss: a white line along the top-left of the tube
    cr.translate(-1.2, -1.6)
    p()
    cr.restore()
    cr.set_line_width(1.6)
    g = cairo.LinearGradient(x, y, x + w * 0.6, y + h * 0.6)
    g.add_color_stop_rgba(0, 1, 1, 1, 0.75)
    g.add_color_stop_rgba(1, 1, 1, 1, 0.05)
    cr.set_source(g)
    cr.stroke()
    rnd = random.Random(int(w) * 7 + int(h))
    pts = rrect_points(x, y, w, h, _RADIUS[0] or 12, 6)
    for px_, py_, nx, ny in pts[::11]:   # bubbles inside the tube
        if rnd.random() < 0.55:
            r = rnd.uniform(1.2, 2.6)
            cr.arc(px_, py_, r, 0, 2 * PI)
            cr.set_source_rgba(1, 1, 1, 0.45)
            cr.set_line_width(0.8)
            cr.stroke()
    for px_, py_, nx, ny in pts:            # drops hanging from the bottom
        if ny > 0.9 and rnd.random() < 0.035:
            L = rnd.uniform(6, 16)
            col = ws.color_at(stops, (px_ - x) / max(1, w))
            cr.new_path()
            cr.move_to(px_ - 3, py_ + 2)
            cr.curve_to(px_ - 3, py_ + L * 0.6, px_ - 4, py_ + L, px_, py_ + L)
            cr.curve_to(px_ + 4, py_ + L, px_ + 3, py_ + L * 0.6, px_ + 3, py_ + 2)
            cr.close_path()
            cr.set_source_rgba(*col, 0.95)
            cr.fill()
            cr.arc(px_ - 1, py_ + L - 3, 1, 0, 2 * PI)
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
    L = (92 if _far() else 64) * s   # on a window they must fit in WINDOW_REACH
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


CARDS = {'glass': card_glass, 'cyber': card_cyber, 'minimal': card_minimal,
         'pixel': card_pixel, 'liquid': card_liquid, 'hud': card_hud, 'fire': card_fire,
         'nature': card_nature, 'sketch': card_sketch, 'crystal': card_crystal, 'lava': card_lava,
         'neon': card_neon, 'holo': card_holo}


# ─────────────────────────────────────────────────── password field
FIELD = {
    'glass': ('#6fa8ff', '#ffffff'), 'cyber': ('#19e6ff', '#ff2bd6'), 'minimal': ('#3a4058', '#5a6385'),
    'pixel': ('#1f5bff', '#4f86ff'),
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
    glow = style not in ('glass', 'minimal', 'pixel')
    for extra, al in (((8 * s, 0.08), (4 * s, 0.16)) if glow else ()):
        p()
        cr.set_line_width(1.6 * s + extra)
        cr.set_source(neon_grad(x, x + w, [a, b], al))
        cr.stroke()
    p()
    cr.set_line_width(1.6 * s)
    cr.set_source(neon_grad(x, x + w, [a, b], 0.95))
    cr.stroke()


# ─────────────────────────────── Storm, Venom, Butterflies, Snakes
import wsthree as w3  # noqa: E402


def _ring(x, y, w, h, s, key, step=3.0):
    r = _RADIUS[0] if _RADIUS[0] is not None else RADIUS[key] * s
    return rrect_points(x, y, w, h, max(r, 4), step)


def card_storm(cr, p, x, y, w, h, cx, cy, s):
    blue = rgb('#4f9dff')
    rnd = random.Random(31)
    halo(cr, cx, cy, w * 0.8, rgb('#1d3fd6'), 0.25)
    _tint(cr, p, '#060b1c', 0.55)
    pts = _ring(x, y, w, h, s, 'storm')
    reach = (70 if _far() else 34) * s
    for (bx, by), (dx, dy) in (((x, y), (-1, -1)), ((x + w, y), (1, -1)), ((x, y + h), (-1, 1)),
                               ((x + w, y + h), (1, 1))):   # bolts off the corners
        for _ in range(2):
            w3.bolt(cr, rnd, bx - dx * 6 * s, by - dy * 6 * s, bx + dx * rnd.uniform(0.5, 1) * reach,
                    by + dy * rnd.uniform(0.3, 1) * reach, 1.3 * s, blue, 1)
    for px_, py_, nx, ny in pts[::23]:   # small arcs crackling out of the edges
        if rnd.random() < 0.45:
            L = rnd.uniform(8, 18) * s
            w3.bolt(cr, rnd, px_, py_, px_ + nx * L + rnd.uniform(-6, 6) * s, py_ + ny * L + rnd.uniform(-6, 6) * s,
                    0.8 * s, blue, 0, a=0.85)
    for extra, a in ((12 * s, 0.07), (6 * s, 0.16), (3 * s, 0.4)):
        p()
        cr.set_line_width(1.6 * s + extra)
        cr.set_source_rgba(*blue, a)
        cr.stroke()
    p()
    cr.set_line_width(1.4 * s)
    cr.set_source_rgba(0.9, 0.96, 1, 1)
    cr.stroke()

def card_venom(cr, p, x, y, w, h, cx, cy, s):
    red, black, rim = rgb('#ff1a2e'), rgb('#0a0406'), rgb('#ff3a3a')
    rnd = random.Random(37)
    halo(cr, cx, cy, w * 0.8, rgb('#6a0010'), 0.3)
    _tint(cr, p, '#0b0305', 0.55)
    r = _RADIUS[0] if _RADIUS[0] is not None else RADIUS['venom'] * s
    for k, (amp, wd, seed) in enumerate(((3.2, 5.0, 3), (2.4, 3.4, 9))):   # twisting tentacles on the frame
        ring = [(px, py) for px, py, _a, _b in wavy(x, y, w, h, max(r, 4), amp * s, seed)]
        w3.tube(cr, ring + ring[:1], [wd * s] * (len(ring) + 1), black, rim, red, 0.3)
    reach = (80 if _far() else 40) * s
    for (bx, by), base in (((x, y), -3 * PI / 4), ((x + w, y), -PI / 4), ((x, y + h), 3 * PI / 4),
                           ((x + w, y + h), PI / 4)):   # tentacles curling out of the corners
        for i in range(3):
            ang = base + rnd.uniform(-0.6, 0.6)
            L = rnd.uniform(0.5, 1) * reach
            pts = [(bx + math.cos(ang) * L * t / 19 + math.sin(t / 3 + i) * 5 * s * t / 19,
                    by + math.sin(ang) * L * t / 19 + math.cos(t / 3 + i) * 5 * s * t / 19) for t in range(20)]
            w3.tube(cr, pts, [(5.5 * (1 - t / 20) + 0.5) * s for t in range(20)], black, rim, red, 0.25)
    for _ in range(int(w / (90 * s)) + 1):   # venom dripping from the bottom
        w3.drip(cr, rnd.uniform(x + r, x + w - r), y + h + 1, rnd.uniform(6, 18 if _far() else 12) * s, 2 * s, red, 0.95)
    if _far():   # the jaws on the right side
        w3.maw(cr, x + w - 6 * s, cy, 2.4 * s, black, rim, red)

def card_butterfly(cr, p, x, y, w, h, cx, cy, s):
    pink, violet, blue = rgb('#ff7ae0'), rgb('#b07cff'), rgb('#8fb8ff')
    rnd = random.Random(41)
    halo(cr, x, y, w * 0.6, violet, 0.22)
    halo(cr, x + w, y + h, w * 0.6, pink, 0.22)
    _tint(cr, p, '#120824', 0.5)
    r = _RADIUS[0] if _RADIUS[0] is not None else RADIUS['butterfly'] * s
    for amp, seed, col in ((2.6, 4, pink), (3.0, 8, violet)):   # glowing vines
        ring = wavy(x, y, w, h, max(r, 4), amp * s, seed)
        for extra, a in ((7 * s, 0.1), (3 * s, 0.25), (0, 0.95)):
            poly(cr, ring)
            cr.set_line_width(1.3 * s + extra)
            cr.set_source_rgba(*col, a)
            cr.stroke()
    for px_, py_, _nx, _ny in rrect_points(x, y, w, h, max(r, 4), 40 * s):   # blossoms on the vine
        if rnd.random() < 0.45:
            w3.flower(cr, px_, py_, rnd.uniform(3, 5) * s, rnd.choice((pink, violet)), a=0.95, rot=rnd.uniform(0, 1))
    big = (34 if _far() else 20) * s
    w3.butterfly(cr, x + 4 * s, y + 4 * s, big, -0.4, pink, blue)
    w3.butterfly(cr, x + w - 4 * s, y + h - 4 * s, big * 0.9, 0.4, violet, pink)
    w3.butterfly(cr, x + w - 10 * s, y - 6 * s, big * 0.45, 0.3, blue, pink, 0.85)
    w3.butterfly(cr, x + 12 * s, y + h + 6 * s, big * 0.4, -0.3, pink, violet, 0.85)
    if _far():
        for _ in range(5):
            ang = rnd.uniform(0, 2 * PI)
            w3.butterfly(cr, cx + math.cos(ang) * (w / 2 + rnd.uniform(30, 90) * s),
                         cy + math.sin(ang) * (h / 2 + rnd.uniform(20, 60) * s), rnd.uniform(6, 11) * s,
                         rnd.uniform(-0.5, 0.5), rnd.choice((pink, violet, blue)), pink, 0.8)
        ws.stars(cr, (x - 100 * s, y - 80 * s, w + 200 * s, h + 160 * s), 70, 43,
                 colors=('#ffb8f0', '#e0c8ff', '#ffffff'))
    else:
        ws.stars(cr, (x - 6, y - 6, w + 12, 12), int(w / 50), 43, colors=('#ffb8f0', '#e0c8ff'))


def card_snake(cr, p, x, y, w, h, cx, cy, s):
    """The frame is a snake: its body slithers once round the window (the
    same wave the window is cut to), the tail slips under the head at the
    top left corner and the head rises off it, tongue out."""
    lime, base = rgb('#7dff2e'), rgb('#0c1a0c')
    halo(cr, cx, cy, w * 0.8, rgb('#1f6a10'), 0.25)
    _tint(cr, p, '#040d05', 0.55)
    ring = [(px, py) for px, py, _nx, _ny in snake_ring(x, y, w, h, s)]
    n = len(ring)
    k = int(n * 0.985)   # a full lap: the tail ends right under the head
    body = ring[:k]
    # a coil: at the lower right corner the body loops once round itself
    ci = min(range(len(body)), key=lambda i: -(body[i][0] - x) - (body[i][1] - y))
    (px0, py0), (px1, py1) = body[ci - 1], body[ci]
    d = math.atan2(py1 - py0, px1 - px0)   # heading at the corner
    R = 15 * s
    ocx, ocy = px1 + math.cos(d - PI / 2) * R, py1 + math.sin(d - PI / 2) * R
    a0 = d + PI / 2
    loop = [(ocx + math.cos(a0 - t / 40 * 2 * PI) * R * (1 + 0.1 * math.sin(t / 40 * 2 * PI)),
             ocy + math.sin(a0 - t / 40 * 2 * PI) * R * (1 + 0.1 * math.sin(t / 40 * 2 * PI)))
            for t in range(1, 40)]
    body = body[:ci + 1] + loop + body[ci + 1:]
    # the neck leaves the corner going up and out
    (ax, ay), (bx, by) = body[-6], body[-1]
    ang = math.atan2(by - ay, bx - ax)
    for i in range(1, 12):
        ang -= 0.07
        bx, by = bx + math.cos(ang) * 2.6 * s, by + math.sin(ang) * 2.6 * s - 0.9 * s
        body.append((bx, by))
    w3.snake_body(cr, body, 10 * s, base, lime, lime, head_k=1.9)
    if _far():   # a second, smaller snake round the lower left corner
        seg = [(x - 26 * s + math.sin(t / 3) * 6 * s, y + h * 0.6 + t * 4 * s) for t in range(18)]
        w3.snake_body(cr, seg, 5 * s, base, lime, lime)


RADIUS.update({'storm': 20, 'venom': 22, 'butterfly': 28, 'snake': 22})
CARDS.update({'storm': card_storm, 'venom': card_venom, 'butterfly': card_butterfly, 'snake': card_snake})
FIELD.update({'storm': ('#4f9dff', '#dff0ff'), 'venom': ('#ff1a2e', '#ff6a3a'),
              'butterfly': ('#ff7ae0', '#b07cff'), 'snake': ('#7dff2e', '#e8ff5a')})


# ─────────────────────────────────────────────────────── lock clock
def clock_colors(style):
    """(time, date) colors of the lock clock in the style (hex)."""
    with ws.tinted(style, ws.tint_target('locks')):
        a, b = (ws.rgb(c) for c in FIELD.get(style, ('#c0caf5', '#7aa2f7')))
    light = tuple(min(1.0, v * 0.35 + 0.65) for v in a)   # the time stays readable

    def lum(c):
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    date = max((a, b), key=lambda c: (lum(c) >= 0.45, max(c) - min(c)))   # the more vivid readable one
    while lum(date) < 0.5:
        date = tuple(v + (1 - v) * 0.25 for v in date)
    return ['#%02x%02x%02x' % tuple(round(v * 255) for v in c) for c in (light, date)]


def paint_clock(cr, style, cx, cy, w, h, s, bg=(0.05, 0.06, 0.1)):
    """The plate the lock clock is written on: the style's scene inside its
    outline, veiled, framed like a window of the style (lightning, the
    snake, vines, flames...), with a glow in the style's color where the
    digits go. i3lock writes the live time and date over it."""
    x, y = cx - w / 2, cy - h / 2
    radius = min(h / 2, 26 * s)
    cr.save()
    window_outline(cr, style, x, y, w, h, radius)
    cr.clip()
    try:
        import wsback
        cr.set_source_surface(wsback.render(style, int(w), int(h), ws.tint_target('locks')), x, y)
        cr.paint()
    except Exception:
        pass
    cr.set_source_rgba(*bg, 0.62)
    cr.paint()
    with ws.tinted(style, ws.tint_target('locks')):
        glow = ws.rgb(ws.NATIVE.get(style, '#6fa8ff'))
    g = cairo.RadialGradient(cx, cy - h * 0.08, 0, cx, cy - h * 0.08, w * 0.45)
    g.add_color_stop_rgba(0, *glow, 0.28)
    g.add_color_stop_rgba(1, *glow, 0)
    cr.set_source(g)
    cr.paint()
    cr.restore()
    paint_window(cr, style, x, y, w, h, radius, True)


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
    elif args[:1] == ['clockcolors'] and len(args) == 2:
        print(*clock_colors(args[1]))
    elif args[:1] == ['clock'] and len(args) == 10:
        # clock SRC DST CX CY W H SCALE BG STYLE: the clock plate onto an image
        src, dst, cx, cy, w, h, s, bg, style = args[1:]
        from PIL import Image
        img = Image.open(src).convert('RGBA')
        over = cairo.ImageSurface(cairo.FORMAT_ARGB32, *img.size)
        h_ = bg.lstrip('#')
        paint_clock(cairo.Context(over), style, float(cx), float(cy), float(w), float(h), float(s),
                    tuple(int(h_[i:i + 2], 16) / 255 for i in (0, 2, 4)))
        over.flush()
        ov = Image.frombuffer('RGBA', img.size, bytes(over.get_data()), 'raw', 'BGRa', over.get_stride(), 1)
        img.alpha_composite(ov)
        img.convert('RGB').save(dst, compress_level=1)
    else:
        print('wscard.py style | panel SRC DST X Y W H SCALE BG STYLE | clock SRC DST CX CY W H SCALE BG STYLE'
              ' | clockcolors STYLE', file=sys.stderr)
        sys.exit(1)


# ═══════════════════════════════════════════════ window backgrounds
# Drawn right UNDER a (translucent) terminal by bin/RoundBorders: typing
# on a lava rock, in liquid glass, among leaves... Dark enough to read on.
def _bg_base(cr, w, h, top, bottom):
    g = cairo.LinearGradient(0, 0, w * 0.3, h)
    g.add_color_stop_rgb(0, *rgb(top))
    g.add_color_stop_rgb(1, *rgb(bottom))
    cr.set_source(g)
    cr.paint()


def _vignette(cr, w, h, a=0.55):
    g = cairo.RadialGradient(w / 2, h / 2, min(w, h) * 0.3, w / 2, h / 2, max(w, h) * 0.75)
    g.add_color_stop_rgba(0, 0, 0, 0, 0)
    g.add_color_stop_rgba(1, 0, 0, 0, a)
    cr.set_source(g)
    cr.paint()


def bg_lava(cr, w, h, rnd):
    _bg_base(cr, w, h, '#1e0d08', '#0d0503')
    # basalt plates: jittered grid cells, each a slightly different stone
    cell = 90
    pts = {}
    for i in range(-1, int(w / cell) + 2):
        for j in range(-1, int(h / cell) + 2):
            pts[i, j] = (i * cell + rnd.uniform(-30, 30), j * cell + rnd.uniform(-30, 30))
    for i in range(-1, int(w / cell) + 1):
        for j in range(-1, int(h / cell) + 1):
            quad = [pts[i, j], pts[i + 1, j], pts[i + 1, j + 1], pts[i, j + 1]]
            cr.new_path()
            for k, (px_, py_) in enumerate(quad):
                (cr.move_to if k == 0 else cr.line_to)(px_, py_)
            cr.close_path()
            v = rnd.uniform(0.06, 0.16)
            cr.set_source_rgba(0.32 * v * 6, 0.16 * v * 6, 0.1 * v * 6, 0.55)
            cr.fill_preserve()
            # molten seams between the plates
            glow = rnd.random()
            for lw, a, col in ((7, 0.07 * glow, '#ff2a00'), (3, 0.25 * glow, '#ff5a00'), (1.1, 0.8 * glow, '#ffb020')):
                cr.set_line_width(lw)
                cr.set_source_rgba(*rgb(col), a)
                cr.stroke_preserve()
            cr.new_path()
    halo(cr, w * 0.85, h, w * 0.6, rgb('#ff3a00'), 0.25)
    for _ in range(int(w * h / 9000)):
        cr.arc(rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(0.6, 1.6), 0, 2 * PI)
        cr.set_source_rgba(*rgb(rnd.choice(['#ff7a18', '#ffc400', '#ff3a00'])), rnd.uniform(0.2, 0.7))
        cr.fill()
    _vignette(cr, w, h, 0.5)


def bg_liquid(cr, w, h, rnd):
    _bg_base(cr, w, h, '#0b1a45', '#120a38')
    for fx, fy, col, a in ((0.15, 0.2, '#20c8ff', 0.35), (0.85, 0.35, '#7a5cff', 0.32),
                           (0.4, 0.9, '#3b6bff', 0.30), (0.95, 0.95, '#b37cff', 0.25)):
        halo(cr, w * fx, h * fy, max(w, h) * 0.55, rgb(col), a)
    for k in range(7):   # slow wave lines
        yy = h * (0.12 + k * 0.13)
        cr.move_to(0, yy)
        for i in range(1, 41):
            xx = w * i / 40
            cr.line_to(xx, yy + 10 * math.sin(i / 40 * 2 * PI * 1.5 + k))
        cr.set_line_width(1.2)
        cr.set_source_rgba(*rgb('#6fd8ff'), 0.08)
        cr.stroke()
    for _ in range(int(w * h / 12000)):   # bubbles
        bx, by, br = rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(2, 9)
        cr.arc(bx, by, br, 0, 2 * PI)
        cr.set_source_rgba(1, 1, 1, 0.06)
        cr.fill_preserve()
        cr.set_source_rgba(*rgb('#9fe6ff'), 0.25)
        cr.set_line_width(0.8)
        cr.stroke()
        cr.arc(bx - br * 0.35, by - br * 0.35, br * 0.25, 0, 2 * PI)
        cr.set_source_rgba(1, 1, 1, 0.35)
        cr.fill()
    _vignette(cr, w, h, 0.4)


def bg_nature(cr, w, h, rnd):
    _bg_base(cr, w, h, '#0a2214', '#04100a')
    halo(cr, w * 0.2, 0, max(w, h) * 0.7, rgb('#5fdc7f'), 0.16)   # light through the canopy
    for _ in range(int(w * h / 14000)):   # a forest of dim leaves
        ws.leaf(cr, rnd.uniform(-20, w), rnd.uniform(-20, h), rnd.uniform(26, 70), rnd.uniform(0, 2 * PI),
                rgb(rnd.choice(['#1f8f3a', '#2fbf55', '#145c28'])))
    cr.set_source_rgba(*rgb('#04100a'), 0.62)
    cr.paint()
    for (cx, cy, base) in ((0, 0, PI / 4), (w, h, -3 * PI / 4)):   # brighter branches at two corners
        for k in range(6):
            ws.leaf(cr, cx, cy, rnd.uniform(40, 90), base + rnd.uniform(-0.7, 0.7),
                    rgb(rnd.choice(['#2fbf55', '#3fd46a', '#1f8f3a'])))
    cr.set_source_rgba(*rgb('#04100a'), 0.35)
    cr.paint()
    _vignette(cr, w, h, 0.45)


def bg_fire(cr, w, h, rnd):
    _bg_base(cr, w, h, '#120604', '#1e0804')
    halo(cr, w / 2, h * 1.05, max(w, h) * 0.7, rgb('#ff3a00'), 0.38)
    halo(cr, w * 0.2, h, w * 0.4, rgb('#ffb000'), 0.18)
    for i in range(int(w / 26)):   # flame silhouettes along the bottom
        fx = i * 26 + rnd.uniform(-6, 6)
        L = rnd.uniform(h * 0.08, h * 0.28)
        _flame(cr, fx, h + 4, rnd.uniform(-0.15, 0.15), -1, L, rnd.uniform(8, 16), a=0.35)
    for _ in range(int(w * h / 5000)):   # embers rising
        cr.arc(rnd.uniform(0, w), rnd.uniform(0, h) ** 1.0, rnd.uniform(0.6, 1.8), 0, 2 * PI)
        cr.set_source_rgba(*rgb(rnd.choice(['#ff7a18', '#ffc400', '#ff3a00'])), rnd.uniform(0.15, 0.7))
        cr.fill()
    _vignette(cr, w, h, 0.45)


def bg_hud(cr, w, h, rnd):
    _bg_base(cr, w, h, '#061226', '#030912')
    blue = rgb('#2d8cff')
    for x in range(0, int(w), 24):   # fine grid
        cr.move_to(x + 0.5, 0)
        cr.line_to(x + 0.5, h)
    for y in range(0, int(h), 24):
        cr.move_to(0, y + 0.5)
        cr.line_to(w, y + 0.5)
    cr.set_line_width(1)
    cr.set_source_rgba(*blue, 0.06)
    cr.stroke()
    for _ in range(int(w * h / 40000) + 3):   # circuit traces
        x, y = rnd.randrange(0, int(w), 24), rnd.randrange(0, int(h), 24)
        cr.move_to(x, y)
        for _k in range(rnd.randint(2, 5)):
            if rnd.random() < 0.5:
                x += rnd.choice((-1, 1)) * 24 * rnd.randint(2, 6)
            else:
                y += rnd.choice((-1, 1)) * 24 * rnd.randint(1, 4)
            cr.line_to(x, y)
        cr.set_line_width(1.3)
        cr.set_source_rgba(*blue, 0.22)
        cr.stroke()
        cr.arc(x, y, 2.5, 0, 2 * PI)
        cr.set_source_rgba(*rgb('#7fc6ff'), 0.5)
        cr.fill()
    for y in range(0, int(h), 3):   # scan lines
        cr.rectangle(0, y, w, 1)
    cr.set_source_rgba(0, 0, 0, 0.12)
    cr.fill()
    halo(cr, w * 0.8, h * 0.2, w * 0.5, blue, 0.10)
    _vignette(cr, w, h, 0.5)


def bg_cyber(cr, w, h, rnd):
    _bg_base(cr, w, h, '#120828', '#07030f')
    hz = h * 0.62   # synthwave floor
    halo(cr, w / 2, hz, w * 0.6, rgb('#ff2bd6'), 0.22)
    for i in range(-20, 21):
        cr.move_to(w / 2 + i * w * 0.02, hz)
        cr.line_to(w / 2 + i * w * 0.12, h)
    k = 0
    y = hz
    while y < h:
        cr.move_to(0, y)
        cr.line_to(w, y)
        k += 1
        y = hz + (k ** 1.7) * 3
    cr.set_line_width(1)
    cr.set_source_rgba(*rgb('#ff2bd6'), 0.18)
    cr.stroke()
    cr.move_to(0, hz)
    cr.line_to(w, hz)
    cr.set_source_rgba(*rgb('#19e6ff'), 0.5)
    cr.set_line_width(1.5)
    cr.stroke()
    ws.stars(cr, (0, 0, w, hz), int(w * hz / 6000), 3)
    _vignette(cr, w, h, 0.5)


def bg_neon(cr, w, h, rnd):
    _bg_base(cr, w, h, '#0a0d24', '#070a18')
    for fx, fy, col in ((0, 0, '#19d4ff'), (1, 1, '#ff3fd8'), (1, 0, '#2f6bff'), (0, 1, '#8b3dff')):
        halo(cr, w * fx, h * fy, max(w, h) * 0.5, rgb(col), 0.18)
    _vignette(cr, w, h, 0.3)


def bg_glass(cr, w, h, rnd, deep='#0f1530'):
    _bg_base(cr, w, h, '#1a2550', deep)
    for i in range(4):   # light streaks across the glass
        x0 = rnd.uniform(-w * 0.3, w)
        g = cairo.LinearGradient(x0, 0, x0 + w * 0.25, h)
        g.add_color_stop_rgba(0, 1, 1, 1, 0)
        g.add_color_stop_rgba(0.5, 0.8, 0.9, 1, 0.05)
        g.add_color_stop_rgba(1, 1, 1, 1, 0)
        cr.move_to(x0, 0)
        cr.line_to(x0 + w * 0.12, 0)
        cr.line_to(x0 + w * 0.37, h)
        cr.line_to(x0 + w * 0.25, h)
        cr.close_path()
        cr.set_source(g)
        cr.fill()
    halo(cr, w * 0.85, h * 0.1, w * 0.5, rgb('#6fa8ff'), 0.18)
    _vignette(cr, w, h, 0.35)


def bg_crystal(cr, w, h, rnd):
    bg_glass(cr, w, h, rnd, deep='#0a1228')
    for _ in range(int(w * h / 60000) + 2):
        ws.sparkle(cr, rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(3, 7), (1, 1, 1), 0.35)


def bg_pixel(cr, w, h, rnd):
    _bg_base(cr, w, h, '#071030', '#040818')
    for x in range(0, int(w), 16):
        for y in range(0, int(h), 16):
            cr.rectangle(x, y, 2, 2)
    cr.set_source_rgba(*rgb('#1f5bff'), 0.10)
    cr.fill()
    for _ in range(int(w * h / 15000)):   # pixel stars
        x, y = rnd.randrange(0, int(w), 4), rnd.randrange(0, int(h), 4)
        q = rnd.choice((2, 4))
        cr.rectangle(x, y, q, q)
        cr.set_source_rgba(*rgb(rnd.choice(['#ffffff', '#ffd21e', '#4f86ff'])), rnd.uniform(0.2, 0.6))
        cr.fill()


def bg_minimal(cr, w, h, rnd):
    _bg_base(cr, w, h, '#12151e', '#0b0d13')
    _vignette(cr, w, h, 0.25)


def bg_sketch(cr, w, h, rnd):
    _bg_base(cr, w, h, '#1a1a1a', '#121212')
    lead = rgb('#d6d6d6')
    for y in range(24, int(h), 24):   # notebook lines drawn by hand
        cr.move_to(0, y + rnd.uniform(-0.6, 0.6))
        cr.line_to(w, y + rnd.uniform(-0.6, 0.6))
    cr.set_line_width(0.7)
    cr.set_source_rgba(*lead, 0.07)
    cr.stroke()
    cr.move_to(48, 0)
    cr.line_to(48, h)
    cr.set_source_rgba(*rgb('#d98080'), 0.12)
    cr.stroke()
    for _ in range(6):   # shading scribbles in the corners
        x, y = rnd.choice((rnd.uniform(0, w * 0.2), rnd.uniform(w * 0.8, w))), rnd.uniform(h * 0.7, h)
        for i in range(8):
            cr.move_to(x + i * 5, y)
            cr.line_to(x + i * 5 + 14, y - 14)
    cr.set_source_rgba(*lead, 0.06)
    cr.stroke()


def bg_holo(cr, w, h, rnd):
    _bg_base(cr, w, h, '#0c0a2a', '#05040f')
    for fx, fy, col, a in ((0.2, 0.3, '#3b5bff', 0.28), (0.75, 0.6, '#c03cff', 0.26), (0.5, 0.95, '#ff4fd8', 0.15)):
        halo(cr, w * fx, h * fy, max(w, h) * 0.45, rgb(col), a)   # nebula
    ws.stars(cr, (0, 0, w, h), int(w * h / 2500), 9)
    ws.orbit(cr, w * 0.6, h * 0.5, w * 0.55, h * 0.25, -0.2, 0.14, width=1.2, beads=False)
    _vignette(cr, w, h, 0.4)


BACKDROPS = {'lava': bg_lava, 'liquid': bg_liquid, 'nature': bg_nature, 'fire': bg_fire, 'hud': bg_hud,
             'cyber': bg_cyber, 'neon': bg_neon, 'glass': bg_glass, 'crystal': bg_crystal,
             'pixel': bg_pixel, 'minimal': bg_minimal,
             'sketch': bg_sketch, 'holo': bg_holo}


def paint_backdrop(cr, style, w, h, radius=0):
    """The themed background of a window, w x h, corners rounded like it."""
    import wsback   # the detailed scenes (cached renders)
    fn = BACKDROPS.get(style)
    if not fn and style not in wsback.SCENES:
        return
    cr.save()
    rounded(cr, 0, 0, w, h, max(0, radius))
    cr.clip()
    try:
        cr.set_source_surface(wsback.render(style, w, h, ws.tint_target('windows')), 0, 0)
        cr.paint()
    except Exception:
        if fn:
            with ws.tinted(style, ws.tint_target('windows')):
                fn(cr, w, h, random.Random(1234))
    cr.restore()
