# =============================================================
# Author:  TechOGR
# Repo:    https://github.com/TechOGR/bspwm_dotfiles_arch
#
# wsback - detailed window backgrounds of the theme styles, drawn under
# the translucent terminals by bin/RoundBorders (wscard.paint_backdrop):
# material grain, light and shade, and the scenery of each style. The
# middle stays darker for the text; the detail lives towards the edges.
# Renders are cached (style, size, tint) in ~/.cache/rice-backdrops.
#
# Copyright (C) 2021-2026 TechOGR <https://github.com/TechOGR>
# Licensed under GPL-3.0 license
# =============================================================

import os
import math
import random
import hashlib

import cairo

import wspill as ws
from wspill import PI, rgb

VERSION = 3
CACHE = os.path.join(os.path.expanduser('~/.cache'), 'rice-backdrops')


# ─────────────────────────────────────────────────────────── helpers
def halo(cr, x, y, r, c, a):
    ws.halo(cr, x, y, r, c, a)


_NOISE = {}


def noise(size=192, seed=7, soft=False):
    """A tileable grain surface (grey values, alpha 255)."""
    key = (size, seed, soft)
    if key not in _NOISE:
        rnd = random.Random(seed)
        stride = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, size)
        data = bytearray(stride * size)
        for y in range(size):
            for x in range(size):
                v = rnd.randint(0, 255)
                i = y * stride + x * 4
                data[i:i + 4] = bytes((v, v, v, 255))
        surf = cairo.ImageSurface.create_for_data(data, cairo.FORMAT_ARGB32, size, size, stride)
        if soft:   # blurred grain: stone / fog / clouds
            big = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
            c = cairo.Context(big)
            c.scale(4, 4)
            c.set_source_surface(surf, 0, 0)
            c.get_source().set_filter(cairo.FILTER_BILINEAR)
            c.get_source().set_extend(cairo.EXTEND_REPEAT)
            c.paint()
            surf = big
        _NOISE[key] = (surf, data)
    return _NOISE[key][0]


def grain(cr, w, h, a=0.06, op=cairo.OPERATOR_OVERLAY, seed=7, soft=False, scale=1.0):
    cr.save()
    cr.scale(scale, scale)
    pat = cairo.SurfacePattern(noise(seed=seed, soft=soft))
    pat.set_extend(cairo.EXTEND_REPEAT)
    cr.set_source(pat)
    cr.set_operator(op)
    cr.paint_with_alpha(a)
    cr.restore()


def base(cr, w, h, stops, angle=0.35):
    g = cairo.LinearGradient(0, 0, w * angle, h)
    for i, col in enumerate(stops):
        g.add_color_stop_rgb(i / max(1, len(stops) - 1), *rgb(col))
    cr.set_source(g)
    cr.paint()


def reading_shade(cr, w, h, a=0.38):
    """Darker where the text is (left / middle), the scenery shows at the edges."""
    g = cairo.RadialGradient(w * 0.38, h * 0.42, 0, w * 0.38, h * 0.42, max(w, h) * 0.65)
    g.add_color_stop_rgba(0, 0, 0, 0, a)
    g.add_color_stop_rgba(0.7, 0, 0, 0, a * 0.35)
    g.add_color_stop_rgba(1, 0, 0, 0, 0)
    cr.set_source(g)
    cr.paint()


def vignette(cr, w, h, a=0.55):
    g = cairo.RadialGradient(w / 2, h / 2, min(w, h) * 0.35, w / 2, h / 2, max(w, h) * 0.78)
    g.add_color_stop_rgba(0, 0, 0, 0, 0)
    g.add_color_stop_rgba(1, 0, 0, 0, a)
    cr.set_source(g)
    cr.paint()


def glow_line(cr, pts, c, width, layers=((10, 0.05), (5, 0.12), (2.2, 0.35)), core=None):
    for extra, a in layers:
        _poly(cr, pts)
        cr.set_line_width(width + extra)
        cr.set_source_rgba(*c, a)
        cr.stroke()
    _poly(cr, pts)
    cr.set_line_width(width)
    cr.set_source_rgba(*(core or c), 1)
    cr.stroke()


def _poly(cr, pts, close=False):
    cr.new_path()
    for i, p in enumerate(pts):
        (cr.move_to if i == 0 else cr.line_to)(*p)
    if close:
        cr.close_path()


def jitter_line(rnd, x0, y0, x1, y1, parts=8, amp=6):
    pts = [(x0, y0)]
    for i in range(1, parts):
        t = i / parts
        nx, ny = -(y1 - y0), x1 - x0
        n = math.hypot(nx, ny) or 1
        o = rnd.uniform(-amp, amp)
        pts.append((x0 + (x1 - x0) * t + nx / n * o, y0 + (y1 - y0) * t + ny / n * o))
    pts.append((x1, y1))
    return pts


def bokeh(cr, rnd, w, h, n, colors, rmin=6, rmax=26, a=(0.04, 0.12)):
    for _ in range(n):
        x, y, r = rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(rmin, rmax)
        c = rgb(rnd.choice(colors))
        cr.arc(x, y, r, 0, 2 * PI)
        cr.set_source_rgba(*c, rnd.uniform(*a))
        cr.fill_preserve()
        cr.set_source_rgba(*c, rnd.uniform(*a) * 1.6)
        cr.set_line_width(1)
        cr.stroke()


def rays(cr, x, y, w, h, c, n=6, a=0.05, spread=0.9, rnd=None):
    rnd = rnd or random.Random(3)
    for _ in range(n):
        ang = PI / 2 + rnd.uniform(-spread, spread) * 0.6
        width = rnd.uniform(0.04, 0.12)
        L = max(w, h) * 1.4
        cr.move_to(x, y)
        cr.line_to(x + L * math.cos(ang - width), y + L * math.sin(ang - width))
        cr.line_to(x + L * math.cos(ang + width), y + L * math.sin(ang + width))
        cr.close_path()
        g = cairo.RadialGradient(x, y, 0, x, y, L * 0.7)
        g.add_color_stop_rgba(0, *c, a)
        g.add_color_stop_rgba(1, *c, 0)
        cr.set_source(g)
        cr.fill()


# ═══════════════════════════════════════════════════════════ scenes
def bg_lava(cr, w, h, rnd):
    base(cr, w, h, ['#221008', '#150906', '#0c0503'])
    # basalt plates: jittered cells, each shaded like a lit stone
    cell = 110
    pts = {}
    for i in range(-1, int(w / cell) + 3):
        for j in range(-1, int(h / cell) + 3):
            pts[i, j] = (i * cell + rnd.uniform(-38, 38), j * cell + rnd.uniform(-38, 38))
    seams = []
    for i in range(-1, int(w / cell) + 2):
        for j in range(-1, int(h / cell) + 2):
            corners = [pts[i, j], pts[i + 1, j], pts[i + 1, j + 1], pts[i, j + 1]]
            poly = []
            for k in range(4):   # rough stone edges
                poly += jitter_line(rnd, *corners[k], *corners[(k + 1) % 4], parts=4, amp=5)[:-1]
            cx = sum(p[0] for p in corners) / 4
            cy = sum(p[1] for p in corners) / 4
            _poly(cr, poly, True)
            v = rnd.uniform(0.7, 1.25)
            g = cairo.RadialGradient(cx - 30, cy - 30, 5, cx, cy, cell * 0.9)
            g.add_color_stop_rgb(0, 0.23 * v, 0.14 * v, 0.10 * v)
            g.add_color_stop_rgb(1, 0.07 * v, 0.04 * v, 0.03 * v)
            cr.set_source(g)
            cr.fill_preserve()
            cr.set_source_rgba(0, 0, 0, 0.55)   # the stone's dark lip
            cr.set_line_width(4)
            cr.stroke()
            seams.append((poly, rnd.random()))
            if rnd.random() < 0.35:   # hairline cracks inside a plate
                a0 = rnd.uniform(0, 2 * PI)
                crack = jitter_line(rnd, cx, cy, cx + math.cos(a0) * cell * 0.45, cy + math.sin(a0) * cell * 0.45,
                                    parts=5, amp=6)
                glow_line(cr, crack, rgb('#ff4a00'), 0.8, layers=((4, 0.08), (1.8, 0.3)), core=rgb('#ffb030'))
    grain(cr, w, h, 0.22, seed=11, soft=True)
    # molten seams: the hotter ones glow wide, with a yellow core
    for poly, heat in seams:
        if heat < 0.25:
            continue
        glow_line(cr, poly + [poly[0]], rgb('#ff3a00'), 1.1 + heat,
                  layers=((12 * heat, 0.05), (6 * heat, 0.14), (2.5, 0.45)), core=rgb('#ffc040'))
    # lava pools glowing up from below + haze
    for fx, fy, r in ((0.85, 1.0, 0.55), (0.1, 0.95, 0.35), (0.6, 0.7, 0.2)):
        halo(cr, w * fx, h * fy, max(w, h) * r, rgb('#ff4000'), 0.30)
    grain(cr, w, h, 0.10, seed=3)
    for _ in range(int(w * h / 4500)):   # embers, a few big with a glow
        x, y, r = rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(0.6, 1.8)
        c = rgb(rnd.choice(['#ff7a18', '#ffc400', '#ff3a00']))
        if r > 1.5:
            halo(cr, x, y, r * 5, c, 0.35)
        cr.arc(x, y, r, 0, 2 * PI)
        cr.set_source_rgba(*c, rnd.uniform(0.35, 0.9))
        cr.fill()
    reading_shade(cr, w, h, 0.35)
    vignette(cr, w, h, 0.55)


def bg_liquid(cr, w, h, rnd):
    base(cr, w, h, ['#0a2a5e', '#0d1a4a', '#1a0d42'])
    rays(cr, w * 0.3, -h * 0.1, w, h, rgb('#7fe6ff'), n=7, a=0.07, rnd=rnd)
    for fx, fy, col, a in ((0.1, 0.15, '#20c8ff', 0.30), (0.9, 0.3, '#7a5cff', 0.28),
                           (0.35, 1.0, '#3b6bff', 0.30), (1.0, 1.0, '#c07cff', 0.25)):
        halo(cr, w * fx, h * fy, max(w, h) * 0.55, rgb(col), a)
    # caustics: a web of bright wavy lines
    for k in range(26):
        y0 = rnd.uniform(-h * 0.1, h * 1.1)
        ph = rnd.uniform(0, 6)
        amp = rnd.uniform(8, 26)
        f = rnd.uniform(1.5, 4.5)
        cr.move_to(0, y0)
        for i in range(1, 61):
            x = w * i / 60
            cr.line_to(x, y0 + amp * math.sin(i / 60 * f * 2 * PI + ph) + 10 * math.sin(i / 7 + ph))
        cr.set_line_width(rnd.uniform(0.6, 1.8))
        cr.set_source_rgba(*rgb(rnd.choice(['#8fe8ff', '#b8f2ff', '#9fb8ff'])), rnd.uniform(0.04, 0.12))
        cr.stroke()
    grain(cr, w, h, 0.16, seed=5, soft=True, scale=1.5)
    bokeh(cr, rnd, w, h, int(w * h / 26000), ['#6fd8ff', '#9f8cff', '#4f8dff'], 10, 40, (0.03, 0.08))
    for _ in range(int(w * h / 7000)):   # bubbles with a light rim and a shine
        bx, by, br = rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(2, 11)
        g = cairo.RadialGradient(bx - br * 0.3, by - br * 0.3, 0, bx, by, br)
        g.add_color_stop_rgba(0, 1, 1, 1, 0.10)
        g.add_color_stop_rgba(0.8, 0.6, 0.85, 1, 0.05)
        g.add_color_stop_rgba(1, 0.7, 0.9, 1, 0.35)
        cr.arc(bx, by, br, 0, 2 * PI)
        cr.set_source(g)
        cr.fill()
        cr.arc(bx - br * 0.35, by - br * 0.4, br * 0.28, 0, 2 * PI)
        cr.set_source_rgba(1, 1, 1, 0.55)
        cr.fill()
    reading_shade(cr, w, h, 0.32)
    vignette(cr, w, h, 0.45)


def bg_nature(cr, w, h, rnd):
    base(cr, w, h, ['#10331e', '#0a2414', '#04120a'])
    rays(cr, w * 0.15, -h * 0.15, w, h, rgb('#d8ffb0'), n=8, a=0.08, rnd=rnd)   # sun through the canopy
    halo(cr, w * 0.15, 0, max(w, h) * 0.6, rgb('#9fe07a'), 0.18)
    greens = ['#145c28', '#1f8f3a', '#2fbf55', '#3fd46a', '#0f4a20']
    for layer, (count, size, dim) in enumerate(((int(w * h / 9000), (30, 60), 0.72),
                                               (int(w * h / 20000), (50, 100), 0.45))):
        for _ in range(count):   # far leaves, then nearer bigger ones
            ws.leaf(cr, rnd.uniform(-30, w), rnd.uniform(-30, h), rnd.uniform(*size), rnd.uniform(0, 2 * PI),
                    rgb(rnd.choice(greens)))
        cr.set_source_rgba(*rgb('#04120a'), dim)
        cr.paint()
        grain(cr, w, h, 0.10, seed=13 + layer, soft=True)
    # branches with leaves along them, from two corners
    for (x0, y0, dx, dy) in ((0, 0, 1, 1), (w, h, -1, -1), (w, 0, -1, 1)):
        x, y = x0, y0
        ang = math.atan2(dy, dx) + rnd.uniform(-0.3, 0.3)
        for step in range(9):
            nx, ny = x + math.cos(ang) * 30, y + math.sin(ang) * 30
            cr.move_to(x, y)
            cr.line_to(nx, ny)
            cr.set_line_width(max(1, 4 - step * 0.4))
            cr.set_source_rgba(*rgb('#3a2a14'), 0.8)
            cr.stroke()
            for side in (-1, 1):
                ws.leaf(cr, nx, ny, rnd.uniform(22, 40) * (1 - step * 0.05), ang + side * rnd.uniform(0.5, 1.1),
                        rgb(rnd.choice(greens[1:4])))
            x, y = nx, ny
            ang += rnd.uniform(-0.35, 0.35)
    for _ in range(int(w * h / 16000)):   # fireflies
        x, y = rnd.uniform(0, w), rnd.uniform(0, h)
        halo(cr, x, y, 10, rgb('#e8ff8a'), 0.35)
        cr.arc(x, y, 1.3, 0, 2 * PI)
        cr.set_source_rgba(*rgb('#f4ffb0'), 0.9)
        cr.fill()
    reading_shade(cr, w, h, 0.38)
    vignette(cr, w, h, 0.55)


def _flame(cr, fx, fy, L, width, sway, cols, a):
    tx, ty = fx + sway, fy - L
    cr.new_path()
    cr.move_to(fx - width, fy)
    cr.curve_to(fx - width * 1.1, fy - L * 0.45, tx - width * 0.5 + sway * 0.3, ty + L * 0.35, tx, ty)
    cr.curve_to(tx + width * 0.4 + sway * 0.2, ty + L * 0.4, fx + width * 1.1, fy - L * 0.4, fx + width, fy)
    cr.close_path()
    g = cairo.LinearGradient(fx, fy, tx, ty)
    g.add_color_stop_rgba(0, *rgb(cols[0]), a)
    g.add_color_stop_rgba(0.5, *rgb(cols[1]), a * 0.7)
    g.add_color_stop_rgba(1, *rgb(cols[2]), 0)
    cr.set_source(g)
    cr.fill()


def bg_fire(cr, w, h, rnd):
    base(cr, w, h, ['#0c0403', '#1a0704', '#2a0a04'], angle=0)
    halo(cr, w / 2, h * 1.1, max(w, h) * 0.8, rgb('#ff3a00'), 0.45)
    grain(cr, w, h, 0.14, seed=17, soft=True, scale=2)   # smoke
    for layer, (cols, hmul, a, step) in enumerate((
            (('#7a0f00', '#c52a00', '#ff5a00'), 0.55, 0.55, 34),
            (('#d63a00', '#ff7a00', '#ffb000'), 0.38, 0.6, 26),
            (('#ff9a00', '#ffd23a', '#fff4b0'), 0.2, 0.55, 20))):
        x = rnd.uniform(-step, 0)
        while x < w + step:
            L = rnd.uniform(0.4, 1.0) * h * hmul
            _flame(cr, x, h + 6, L, rnd.uniform(step * 0.45, step * 0.8), rnd.uniform(-L * 0.15, L * 0.15), cols, a)
            x += step * rnd.uniform(0.6, 1.2)
    for _ in range(int(w * h / 3500)):   # rising embers, streaked upwards
        x, y = rnd.uniform(0, w), rnd.uniform(0, h) ** 0.9 * h ** 0.1
        L = rnd.uniform(2, 9)
        c = rgb(rnd.choice(['#ff7a18', '#ffc400', '#ff3a00', '#ffe28a']))
        g = cairo.LinearGradient(x, y, x + 1.5, y - L)
        g.add_color_stop_rgba(0, *c, rnd.uniform(0.4, 0.9))
        g.add_color_stop_rgba(1, *c, 0)
        cr.move_to(x, y)
        cr.line_to(x + 1.5, y - L)
        cr.set_line_width(rnd.uniform(1, 2))
        cr.set_source(g)
        cr.stroke()
    grain(cr, w, h, 0.08, seed=4)
    reading_shade(cr, w, h, 0.42)
    vignette(cr, w, h, 0.5)


def bg_hud(cr, w, h, rnd):
    base(cr, w, h, ['#071630', '#050e20', '#02060e'])
    blue, soft = rgb('#2d8cff'), rgb('#7fc6ff')
    for step, a in ((24, 0.05), (120, 0.10)):   # fine + major grid
        for x in range(0, int(w), step):
            cr.move_to(x + 0.5, 0)
            cr.line_to(x + 0.5, h)
        for y in range(0, int(h), step):
            cr.move_to(0, y + 0.5)
            cr.line_to(w, y + 0.5)
        cr.set_line_width(1)
        cr.set_source_rgba(*blue, a)
        cr.stroke()
    # hexagon cluster in a corner
    R = 18
    for i in range(7):
        for j in range(5):
            if rnd.random() < 0.55:
                cx = w - 40 - i * R * 1.75 - (j % 2) * R * 0.87
                cy = 40 + j * R * 1.5
                cr.new_path()
                for k in range(6):
                    a0 = PI / 6 + k * PI / 3
                    (cr.move_to if k == 0 else cr.line_to)(cx + R * 0.9 * math.cos(a0), cy + R * 0.9 * math.sin(a0))
                cr.close_path()
                cr.set_source_rgba(*blue, rnd.uniform(0.04, 0.16))
                cr.fill_preserve()
                cr.set_source_rgba(*soft, 0.25)
                cr.set_line_width(1)
                cr.stroke()
    # radar in the bottom-right
    rx, ry, rr = w - 110, h - 110, 80
    for k in range(1, 5):
        cr.arc(rx, ry, rr * k / 4, 0, 2 * PI)
        cr.set_source_rgba(*blue, 0.2)
        cr.set_line_width(1)
        cr.stroke()
    cr.move_to(rx - rr, ry)
    cr.line_to(rx + rr, ry)
    cr.move_to(rx, ry - rr)
    cr.line_to(rx, ry + rr)
    cr.stroke()
    cr.move_to(rx, ry)
    cr.arc(rx, ry, rr, -0.9, -0.1)
    cr.close_path()
    g = cairo.RadialGradient(rx, ry, 0, rx, ry, rr)
    g.add_color_stop_rgba(0, *soft, 0.0)
    g.add_color_stop_rgba(1, *soft, 0.25)
    cr.set_source(g)
    cr.fill()
    for _ in range(5):
        a0, d = rnd.uniform(0, 2 * PI), rnd.uniform(0.2, 0.9) * rr
        halo(cr, rx + math.cos(a0) * d, ry + math.sin(a0) * d, 6, soft, 0.6)
    # circuit traces with glowing nodes
    for _ in range(int(w * h / 30000) + 4):
        x, y = rnd.randrange(0, int(w), 24), rnd.randrange(0, int(h), 24)
        pts = [(x, y)]
        for _k in range(rnd.randint(3, 6)):
            if rnd.random() < 0.5:
                x += rnd.choice((-1, 1)) * 24 * rnd.randint(2, 6)
            else:
                y += rnd.choice((-1, 1)) * 24 * rnd.randint(1, 4)
            pts.append((x, y))
        glow_line(cr, pts, blue, 1.2, layers=((5, 0.05), (2.5, 0.12)), core=(*blue,))
        for px_, py_ in (pts[0], pts[-1]):
            halo(cr, px_, py_, 7, soft, 0.5)
            cr.arc(px_, py_, 2.2, 0, 2 * PI)
            cr.set_source_rgba(*soft, 0.9)
            cr.fill()
    # data bars on the left edge
    for k in range(10):
        cr.rectangle(14, h * 0.3 + k * 12, rnd.uniform(20, 70), 4)
        cr.set_source_rgba(*blue, rnd.uniform(0.15, 0.4))
        cr.fill()
    for y in range(0, int(h), 3):   # scan lines
        cr.rectangle(0, y, w, 1)
    cr.set_source_rgba(0, 0, 0, 0.14)
    cr.fill()
    grain(cr, w, h, 0.07, seed=21)
    reading_shade(cr, w, h, 0.3)
    vignette(cr, w, h, 0.55)


def bg_cyber(cr, w, h, rnd):
    hz = h * 0.6
    sky = cairo.LinearGradient(0, 0, 0, hz)
    for t, col in ((0, '#0b0520'), (0.7, '#3a0a4a'), (1, '#7a1060')):
        sky.add_color_stop_rgb(t, *rgb(col))
    cr.set_source(sky)
    cr.rectangle(0, 0, w, hz)
    cr.fill()
    ws.stars(cr, (0, 0, w, hz * 0.8), int(w * hz / 3000), 3)
    # synthwave sun: striped disc
    sx, sy, sr = w * 0.68, hz - 10, min(w, h) * 0.24
    cr.save()
    cr.arc(sx, sy, sr, PI, 2 * PI)
    cr.clip()
    g = cairo.LinearGradient(0, sy - sr, 0, sy)
    g.add_color_stop_rgb(0, *rgb('#ffe14d'))
    g.add_color_stop_rgb(1, *rgb('#ff2bd6'))
    cr.set_source(g)
    cr.paint()
    for k in range(7):
        yy = sy - sr * 0.45 + k * sr * 0.08
        cr.rectangle(sx - sr, yy, 2 * sr, 2 + k * 1.4)
    cr.set_source_rgb(*rgb('#3a0a4a'))
    cr.fill()
    cr.restore()
    halo(cr, sx, sy, sr * 1.8, rgb('#ff2bd6'), 0.25)
    # wireframe mountains
    for layer, (col, top, a) in enumerate((('#19e6ff', 0.55, 0.5), ('#ff2bd6', 0.4, 0.7))):
        pts = [(0, hz)]
        x = 0
        while x < w:
            x += rnd.uniform(40, 110)
            pts.append((x, hz - rnd.uniform(0.05, top) * hz * 0.5))
        pts.append((w, hz))
        _poly(cr, pts, True)
        cr.set_source_rgba(*rgb('#0b0520'), 0.85)
        cr.fill_preserve()
        cr.set_source_rgba(*rgb(col), a)
        cr.set_line_width(1.3)
        cr.stroke()
    # floor
    floor = cairo.LinearGradient(0, hz, 0, h)
    floor.add_color_stop_rgb(0, *rgb('#1a0630'))
    floor.add_color_stop_rgb(1, *rgb('#07020f'))
    cr.set_source(floor)
    cr.rectangle(0, hz, w, h - hz)
    cr.fill()
    for i in range(-24, 25):
        cr.move_to(w / 2 + i * w * 0.02, hz)
        cr.line_to(w / 2 + i * w * 0.16, h)
    k, y = 0, hz
    while y < h:
        cr.move_to(0, y)
        cr.line_to(w, y)
        k += 1
        y = hz + (k ** 1.8) * 2.5
    cr.set_line_width(1.1)
    cr.set_source_rgba(*rgb('#ff2bd6'), 0.35)
    cr.stroke()
    glow_line(cr, [(0, hz), (w, hz)], rgb('#19e6ff'), 1.5, layers=((8, 0.08), (3, 0.25)))
    for y in range(0, int(h), 3):
        cr.rectangle(0, y, w, 1)
    cr.set_source_rgba(0, 0, 0, 0.12)
    cr.fill()
    reading_shade(cr, w, h, 0.45)
    vignette(cr, w, h, 0.5)


def bg_holo(cr, w, h, rnd):
    base(cr, w, h, ['#0d0b2e', '#07061a', '#030208'])
    for _ in range(9):   # nebula made of many soft clouds
        halo(cr, rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(0.25, 0.55) * max(w, h),
             rgb(rnd.choice(['#3b5bff', '#c03cff', '#ff4fd8', '#4fd8ff', '#6a3cff'])), rnd.uniform(0.08, 0.2))
    grain(cr, w, h, 0.28, seed=31, soft=True, scale=2.5)
    ws.stars(cr, (0, 0, w, h), int(w * h / 1400), 9)
    for _ in range(int(w * h / 60000) + 3):   # bright stars with spikes
        ws.sparkle(cr, rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(4, 9),
                   rgb(rnd.choice(['#ffffff', '#bfe6ff', '#ffc8f0'])), 0.8)
    # a ringed planet in a corner
    px, py, pr = w - 120, h - 90, 60
    ws.orbit(cr, px, py, pr * 2.1, pr * 0.45, -0.25, 0.45, width=1.6, beads=False)
    g = cairo.RadialGradient(px - pr * 0.4, py - pr * 0.4, pr * 0.1, px, py, pr)
    g.add_color_stop_rgb(0, *rgb('#ffb8f0'))
    g.add_color_stop_rgb(0.5, *rgb('#8a4dff'))
    g.add_color_stop_rgb(1, *rgb('#1b1050'))
    cr.arc(px, py, pr, 0, 2 * PI)
    cr.set_source(g)
    cr.fill()
    halo(cr, px, py, pr * 1.8, rgb('#b07cff'), 0.25)
    ws.orbit(cr, w * 0.45, h * 0.5, w * 0.6, h * 0.3, -0.18, 0.18, width=1.2, beads=True)
    reading_shade(cr, w, h, 0.35)
    vignette(cr, w, h, 0.45)


def bg_pixel(cr, w, h, rnd):
    q = 4
    sky = cairo.LinearGradient(0, 0, 0, h)
    for t, col in ((0, '#05081e'), (0.6, '#0c1a4d'), (1, '#1f2a6e')):
        sky.add_color_stop_rgb(t, *rgb(col))
    cr.set_source(sky)
    cr.paint()
    for _ in range(int(w * h / 3000)):   # pixel stars
        x, y = rnd.randrange(0, int(w), q), rnd.randrange(0, int(h * 0.7), q)
        s = rnd.choice((q // 2, q // 2, q))
        cr.rectangle(x, y, s, s)
        cr.set_source_rgba(*rgb(rnd.choice(['#ffffff', '#ffd21e', '#4f86ff', '#ff7ad9'])), rnd.uniform(0.3, 0.9))
        cr.fill()
    mx, my, mr = w * 0.8, h * 0.22, 36   # pixel moon
    for y in range(-mr, mr, q):
        for x in range(-mr, mr, q):
            if x * x + y * y < mr * mr and (x - 12) ** 2 + (y - 6) ** 2 > (mr * 0.7) ** 2:
                cr.rectangle(mx + x, my + y, q, q)
    cr.set_source_rgb(*rgb('#ffe89a'))
    cr.fill()
    for layer, (col, top, jag) in enumerate((('#101e5a', 0.45, 60), ('#0a1236', 0.62, 40))):   # pixel mountains
        x, y = 0, h * top
        while x < w:
            y = max(h * (top - 0.15), min(h * (top + 0.1), y + rnd.choice((-q, 0, q)) * rnd.randint(1, 4)))
            cr.rectangle(x, int(y / q) * q, q * 2, h - y + q)
            x += q * 2
        cr.set_source_rgb(*rgb(col))
        cr.fill()
    for x in range(0, int(w), 16):   # dotted pixel grid
        for y in range(0, int(h), 16):
            cr.rectangle(x, y, 1, 1)
    cr.set_source_rgba(*rgb('#4f86ff'), 0.18)
    cr.fill()
    reading_shade(cr, w, h, 0.4)


def bg_glass(cr, w, h, rnd, deep='#0f1530', accent='#6fa8ff'):
    base(cr, w, h, ['#1d2a5e', '#131c42', deep])
    for fx, fy, col in ((0.9, 0.05, accent), (0.05, 0.95, '#8f7dff'), (0.6, 0.6, '#3f9bff')):
        halo(cr, w * fx, h * fy, max(w, h) * 0.5, rgb(col), 0.2)
    bokeh(cr, rnd, w, h, int(w * h / 14000), [accent, '#bfd8ff', '#9f8cff'], 12, 48, (0.03, 0.09))
    for i in range(5):   # refraction streaks
        x0 = rnd.uniform(-w * 0.3, w)
        g = cairo.LinearGradient(x0, 0, x0 + w * 0.3, h)
        g.add_color_stop_rgba(0, 1, 1, 1, 0)
        g.add_color_stop_rgba(0.5, 0.85, 0.92, 1, 0.07)
        g.add_color_stop_rgba(1, 1, 1, 1, 0)
        cr.move_to(x0, 0)
        cr.line_to(x0 + w * 0.08, 0)
        cr.line_to(x0 + w * 0.38, h)
        cr.line_to(x0 + w * 0.30, h)
        cr.close_path()
        cr.set_source(g)
        cr.fill()
    grain(cr, w, h, 0.22, seed=41, soft=True)   # frost
    grain(cr, w, h, 0.07, seed=42)
    reading_shade(cr, w, h, 0.34)
    vignette(cr, w, h, 0.4)


def bg_crystal(cr, w, h, rnd):
    bg_glass(cr, w, h, rnd, deep='#0a1228', accent='#8fe6ff')
    for _ in range(int(w * h / 50000) + 3):   # ice shards in the corners
        cx, cy = rnd.choice(((0, 0), (w, 0), (0, h), (w, h)))
        a0 = math.atan2(h / 2 - cy, w / 2 - cx) + rnd.uniform(-0.6, 0.6)
        L = rnd.uniform(60, 160)
        wd = rnd.uniform(8, 18)
        tip = (cx + math.cos(a0) * L, cy + math.sin(a0) * L)
        nx, ny = -math.sin(a0) * wd, math.cos(a0) * wd
        _poly(cr, [(cx + nx, cy + ny), tip, (cx - nx, cy - ny)], True)
        g = cairo.LinearGradient(cx, cy, *tip)
        g.add_color_stop_rgba(0, 0.75, 0.9, 1, 0.22)
        g.add_color_stop_rgba(1, 1, 1, 1, 0.04)
        cr.set_source(g)
        cr.fill_preserve()
        cr.set_source_rgba(0.85, 0.95, 1, 0.35)
        cr.set_line_width(1)
        cr.stroke()
    for _ in range(int(w * h / 25000) + 4):
        ws.sparkle(cr, rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(3, 8), (1, 1, 1), 0.45)


def bg_neon(cr, w, h, rnd):
    base(cr, w, h, ['#0b0e26', '#080a1c', '#05060f'])
    bw, bh = 64, 26   # a dark brick wall
    for row in range(int(h / bh) + 1):
        off = (row % 2) * bw / 2
        for col in range(-1, int(w / bw) + 1):
            x, y = col * bw + off, row * bh
            cr.rectangle(x + 2, y + 2, bw - 4, bh - 4)
            v = rnd.uniform(0.03, 0.07)
            cr.set_source_rgba(v * 1.2, v * 1.2, v * 2.2, 1)
            cr.fill()
    grain(cr, w, h, 0.18, seed=61, soft=True)
    # neon signs: a circle, a triangle and a line, glowing on the wall
    shapes = [
        ('circle', w * 0.78, h * 0.3, min(w, h) * 0.14, '#ff3fd8'),
        ('tri', w * 0.18, h * 0.78, min(w, h) * 0.12, '#19d4ff'),
    ]
    for kind, cx, cy, r, col in shapes:
        c = rgb(col)
        if kind == 'circle':
            pts = [(cx + r * math.cos(a / 40 * 2 * PI), cy + r * math.sin(a / 40 * 2 * PI)) for a in range(41)]
        else:
            pts = [(cx + r * math.cos(-PI / 2 + k * 2 * PI / 3), cy + r * math.sin(-PI / 2 + k * 2 * PI / 3))
                   for k in range(4)]
        halo(cr, cx, cy, r * 2.4, c, 0.18)
        glow_line(cr, pts, c, 3, layers=((22, 0.04), (12, 0.10), (6, 0.25)), core=(1, 1, 1))
    glow_line(cr, [(w * 0.08, h * 0.12), (w * 0.4, h * 0.12)], rgb('#8b3dff'), 2.5,
              layers=((16, 0.05), (8, 0.14), (4, 0.3)), core=(1, 1, 1))
    for fx, fy, col in ((0, 0, '#19d4ff'), (1, 1, '#ff3fd8')):
        halo(cr, w * fx, h * fy, max(w, h) * 0.45, rgb(col), 0.14)
    reading_shade(cr, w, h, 0.4)
    vignette(cr, w, h, 0.45)


def bg_minimal(cr, w, h, rnd):
    base(cr, w, h, ['#161a24', '#10131b', '#0a0c11'])
    for x in range(0, int(w), 32):   # a faint dot grid
        for y in range(0, int(h), 32):
            cr.rectangle(x, y, 1, 1)
    cr.set_source_rgba(1, 1, 1, 0.05)
    cr.fill()
    halo(cr, w * 0.85, h * 0.1, w * 0.5, rgb('#a9c2ff'), 0.05)
    grain(cr, w, h, 0.07, seed=81)
    vignette(cr, w, h, 0.35)


def bg_sketch(cr, w, h, rnd):
    base(cr, w, h, ['#1d1d1d', '#171717', '#121212'])
    grain(cr, w, h, 0.20, seed=91, soft=True)   # paper fibre
    grain(cr, w, h, 0.08, seed=92)
    lead = rgb('#d6d6d6')
    for y in range(26, int(h), 26):   # notebook lines by hand
        pts = jitter_line(rnd, 0, y, w, y, parts=12, amp=0.8)
        _poly(cr, pts)
        cr.set_line_width(0.7)
        cr.set_source_rgba(*lead, 0.07)
        cr.stroke()
    _poly(cr, jitter_line(rnd, 52, 0, 52, h, parts=12, amp=0.8))
    cr.set_source_rgba(*rgb('#d98080'), 0.14)
    cr.stroke()

    def pencil(path, a=0.22, passes=3):
        ws.sketch_stroke(cr, path, lead, passes=passes, jitter=0.9, width=1.1, alpha=a, seed=rnd.randint(0, 999))
    # doodles along the right edge and the bottom
    cx, cy = w - 90, 80
    pencil(lambda: (cr.new_path(), cr.arc(cx, cy, 34, 0, 2 * PI)))
    pencil(lambda: (cr.new_path(), cr.arc(cx, cy, 22, 0, 2 * PI)), 0.15)
    for k in range(5):   # a star
        a0 = -PI / 2 + k * 4 * PI / 5
        a1 = -PI / 2 + (k + 1) * 4 * PI / 5
        sx, sy = w - 180, h - 90
        pencil(lambda a0=a0, a1=a1, sx=sx, sy=sy: (cr.new_path(), cr.move_to(sx + 36 * math.cos(a0), sy + 36 * math.sin(a0)),
                                                   cr.line_to(sx + 36 * math.cos(a1), sy + 36 * math.sin(a1))), 0.2, 2)
    ax, ay = w - 300, h - 60   # an arrow
    pencil(lambda: (cr.new_path(), cr.move_to(ax, ay), cr.curve_to(ax + 40, ay - 50, ax + 90, ay - 30, ax + 110, ay - 70)))
    pencil(lambda: (cr.new_path(), cr.move_to(ax + 96, ay - 72), cr.line_to(ax + 110, ay - 70),
                    cr.line_to(ax + 106, ay - 56)))
    ghost = lambda: ws.ghost_path(cr, w - 70, h - 170, 46)   # noqa: E731  a pac-man ghost, of course
    pencil(ghost, 0.28)
    ws.hatch(cr, ghost, (w - 110, h - 210, 80, 80), lead, spacing=3.5, alpha=0.1)
    for _ in range(4):   # shading scribbles
        x, y = rnd.uniform(w * 0.6, w - 60), rnd.uniform(h * 0.3, h * 0.7)
        for i in range(10):
            cr.move_to(x + i * 4, y)
            cr.line_to(x + i * 4 + 16, y - 16)
        cr.set_source_rgba(*lead, 0.05)
        cr.set_line_width(0.8)
        cr.stroke()
    reading_shade(cr, w, h, 0.25)


SCENES = {'lava': bg_lava, 'liquid': bg_liquid, 'nature': bg_nature, 'fire': bg_fire, 'hud': bg_hud,
          'cyber': bg_cyber, 'neon': bg_neon, 'glass': bg_glass, 'crystal': bg_crystal,
          'pixel': bg_pixel, 'minimal': bg_minimal,
          'sketch': bg_sketch, 'holo': bg_holo}


# ─────────────────────────────── Storm, Venom, Butterflies, Snakes
def bg_storm(cr, w, h, rnd):
    import wsthree as w3
    base(cr, w, h, ['#0c1636', '#070d24', '#03060f'])
    for _ in range(int(w * h / 40000) + 6):   # heavy clouds, lit from inside
        cx, cy = rnd.uniform(-0.1, 1.1) * w, rnd.uniform(-0.15, 0.35) * h
        halo(cr, cx, cy, rnd.uniform(80, 240), rgb(rnd.choice(('#1a2a5a', '#22367a', '#101c40'))), 0.35)
    for fx, fy in ((0.8, 0.12), (0.15, 0.2)):
        halo(cr, w * fx, h * fy, max(w, h) * 0.35, rgb('#3d8bff'), 0.18)
    cr.set_line_width(0.8)   # rain
    for _ in range(int(w * h / 2500)):
        x, y, L = rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(8, 22)
        cr.move_to(x, y)
        cr.line_to(x - L * 0.25, y + L)
    cr.set_source_rgba(*rgb('#9fc8ff'), 0.07)
    cr.stroke()
    blue = rgb('#4f9dff')
    for fx in (0.08, 0.86, 0.62):   # the bolts, from the clouds down to the edges
        x0 = w * fx
        w3.bolt(cr, rnd, x0, -10, x0 + rnd.uniform(-0.15, 0.15) * w, h * rnd.uniform(0.55, 1.05),
                2.2, blue, 4, 0.22, 0.75)
    grain(cr, w, h, 0.08, seed=51)
    reading_shade(cr, w, h, 0.45)
    vignette(cr, w, h, 0.5)


def bg_venom(cr, w, h, rnd):
    import wsthree as w3
    base(cr, w, h, ['#1a0508', '#0c0305', '#050102'])
    halo(cr, w * 0.85, h * 0.2, max(w, h) * 0.45, rgb('#8a0014'), 0.22)
    halo(cr, w * 0.1, h * 0.9, max(w, h) * 0.4, rgb('#6a0010'), 0.2)
    red, black, rim = rgb('#ff1a2e'), rgb('#070203'), rgb('#ff3a3a')
    for i in range(9):   # tentacles reaching in from the edges
        edge = rnd.choice(('l', 'r', 't', 'b'))
        if edge in 'lr':
            bx, by = (-20 if edge == 'l' else w + 20), rnd.uniform(0, h)
            ang = (0 if edge == 'l' else PI) + rnd.uniform(-0.6, 0.6)
        else:
            bx, by = rnd.uniform(0, w), (-20 if edge == 't' else h + 20)
            ang = (PI / 2 if edge == 't' else -PI / 2) + rnd.uniform(-0.6, 0.6)
        L = rnd.uniform(0.25, 0.5) * min(w, h) + 80
        wd = rnd.uniform(14, 30)
        pts = [(bx + math.cos(ang) * L * t / 39 + math.sin(t / 5 + i) * 18 * t / 39,
                by + math.sin(ang) * L * t / 39 + math.cos(t / 4 + i) * 18 * t / 39) for t in range(40)]
        w3.tube(cr, pts, [wd * (1 - t / 42) + 1 for t in range(40)], black, rim, red, 0.25)
    for _ in range(int(w / 70)):   # drops of venom
        w3.drip(cr, rnd.uniform(0, w), rnd.uniform(-5, 0), rnd.uniform(10, 50), rnd.uniform(1.5, 3.5), red, 0.6)
    bokeh(cr, rnd, w, h, int(w * h / 30000), ['#ff1a2e', '#ff4a3a'], 2, 8, (0.05, 0.14))
    grain(cr, w, h, 0.09, seed=53)
    reading_shade(cr, w, h, 0.5)
    vignette(cr, w, h, 0.55)


def bg_butterfly(cr, w, h, rnd):
    import wsthree as w3
    base(cr, w, h, ['#241040', '#160a2c', '#0b0618'])
    for fx, fy, col in ((0.9, 0.1, '#c77dff'), (0.1, 0.85, '#ff7ae0'), (0.5, 0.5, '#6a4dff')):
        halo(cr, w * fx, h * fy, max(w, h) * 0.45, rgb(col), 0.14)
    bokeh(cr, rnd, w, h, int(w * h / 12000), ['#ff9ae8', '#c77dff', '#9fb8ff'], 3, 16, (0.03, 0.1))
    pink, violet, blue = rgb('#ff7ae0'), rgb('#b07cff'), rgb('#8fb8ff')
    for (cx, cy, ang0) in ((0, 0, 0.6), (w, h, PI + 0.6), (w, 0, PI - 0.5), (0, h, -0.5)):   # glowing vines
        for k in range(3):
            pts, a, x, y = [], ang0 + rnd.uniform(-0.4, 0.4), cx, cy
            for t in range(60):
                a += math.sin(t / 6 + k) * 0.08
                x += math.cos(a) * 6
                y += math.sin(a) * 6
                pts.append((x, y))
            col = rnd.choice((pink, violet))
            glow_line(cr, pts, col, 1.4, layers=((8, 0.05), (4, 0.12)))
            for i in range(6, len(pts), 9):
                w3.flower(cr, *pts[i], rnd.uniform(4, 8), rnd.choice((pink, violet, blue)), a=0.8,
                          rot=rnd.uniform(0, 1))
    for _ in range(int(w * h / 60000) + 4):
        w3.butterfly(cr, rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(8, 20), rnd.uniform(-0.6, 0.6),
                     rnd.choice((pink, violet, blue)), rnd.choice((pink, violet)), 0.55)
    ws.stars(cr, (0, 0, w, h), int(w * h / 3000), 57, colors=('#ffb8f0', '#e0c8ff', '#ffffff'))
    grain(cr, w, h, 0.07, seed=55)
    reading_shade(cr, w, h, 0.45)
    vignette(cr, w, h, 0.5)


def bg_snake(cr, w, h, rnd):
    import wsthree as w3
    base(cr, w, h, ['#0a2410', '#061408', '#020803'])
    halo(cr, w * 0.8, h * 0.8, max(w, h) * 0.45, rgb('#1f6a10'), 0.2)
    r = 26   # snakeskin: rows of overlapping scales
    for row in range(-1, int(h / (r * 0.8)) + 2):
        for col in range(-1, int(w / (r * 1.6)) + 2):
            x = col * r * 1.6 + (row % 2) * r * 0.8
            y = row * r * 0.8
            cr.new_path()
            cr.arc(x, y, r, 0.1, PI - 0.1)
            cr.set_line_width(1.2)
            cr.set_source_rgba(*rgb('#3aff2e'), 0.035 + 0.02 * rnd.random())
            cr.stroke()
    lime, dark = rgb('#7dff2e'), rgb('#0c1a0c')
    pts = []   # a snake winding across the bottom right
    for t in range(90):
        f = t / 89
        pts.append((w * (0.35 + 0.7 * f), h * (0.95 - 0.35 * f) + math.sin(f * 9) * h * 0.08))
    w3.snake_body(cr, pts[::-1], 26, dark, lime, lime, head=False)
    pts = [(w * (-0.05 + 0.6 * t / 59), h * (0.3 - 0.25 * t / 59) + math.sin(t / 6) * 30) for t in range(60)]
    w3.snake_body(cr, pts, 16, dark, lime, lime)
    grain(cr, w, h, 0.08, seed=59)
    reading_shade(cr, w, h, 0.5)
    vignette(cr, w, h, 0.55)


SCENES.update({'storm': bg_storm, 'venom': bg_venom, 'butterfly': bg_butterfly, 'snake': bg_snake})


# ─────────────────── the fourth set: Halloween, Desert, Neo Tokyo, Abyss,
# Enchanted Forest, Cosmos, Samurai, Steampunk, Glacier, Witchcraft,
# Golden Dragon, Graffiti (their objects live in lib/wsfour.py)
def _area(w, h, per):
    return max(1, int(w * h / per))


def _fog(cr, w, y0, h0, c, a=0.18, rnd=None):
    """A bank of fog lying over a band of the picture."""
    rnd = rnd or random.Random(5)
    for _ in range(int(w / 70) + 3):
        x = rnd.uniform(-0.1, 1.1) * w
        cr.save()
        cr.translate(x, y0 + rnd.uniform(0, h0))
        cr.scale(rnd.uniform(90, 200), rnd.uniform(14, 30))
        g = cairo.RadialGradient(0, 0, 0, 0, 0, 1)
        g.add_color_stop_rgba(0, *c, a)
        g.add_color_stop_rgba(1, *c, 0)
        cr.set_source(g)
        cr.arc(0, 0, 1, 0, 2 * PI)
        cr.fill()
        cr.restore()


def bg_halloween(cr, w, h, rnd):
    import wsfour as w4
    base(cr, w, h, ['#1e0b2a', '#110618', '#060208'])
    mr = min(w, h) * 0.13
    w4.moon(cr, w * 0.82, h * 0.2, mr, rgb('#ff6ad5'), glow=0.5)
    for _ in range(4):   # clouds drifting over the moon
        cx, cy = w * 0.82 + rnd.uniform(-mr * 2, mr * 2), h * 0.2 + rnd.uniform(-mr * 0.6, mr * 0.9)
        cr.save()
        cr.translate(cx, cy)
        cr.scale(mr * rnd.uniform(1.2, 2.2), mr * rnd.uniform(0.18, 0.3))
        cr.arc(0, 0, 1, 0, 2 * PI)
        cr.restore()
        cr.set_source_rgba(*rgb('#1a0a24'), 0.75)
        cr.fill()
    for _ in range(_area(w, h, 90000) + 4):
        w4.bat(cr, w * 0.82 + rnd.uniform(-mr * 4, mr * 3), h * 0.2 + rnd.uniform(-mr * 1.5, mr * 2.5),
               rnd.uniform(6, 16), rnd.uniform(-0.4, 0.4), rnd.random(), a=0.9)
    sil = rgb('#08030c')
    w4.dead_tree(cr, -10, h + 10, h * 0.55, -1.25, 22, rnd, sil, 5)
    w4.dead_tree(cr, w + 10, h + 10, h * 0.5, -1.9, 20, rnd, sil, 5)
    for k in range(int(w / 90) + 2):   # the graveyard
        gx = rnd.uniform(0.08, 0.92) * w
        gh = rnd.uniform(26, 54)
        w4.tombstone(cr, gx, h + 4, gh * 0.6, gh, rgb('#120818'), rgb('#7a3aaa'), cross=rnd.random() < 0.3, a=0.9)
    _fog(cr, w, h * 0.82, h * 0.2, rgb('#8a5aaa'), 0.16, rnd)
    for k in range(int(w / 260) + 2):
        w4.pumpkin(cr, rnd.uniform(0.05, 0.95) * w, h - rnd.uniform(8, 20), rnd.uniform(12, 22), lit=1.0)
    for _ in range(_area(w, h, 6000)):   # embers
        cr.arc(rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(0.6, 1.8), 0, 2 * PI)
        cr.set_source_rgba(*rgb(rnd.choice(('#ff8a2a', '#ffc43d', '#c04dff'))), rnd.uniform(0.15, 0.6))
        cr.fill()
    grain(cr, w, h, 0.08, seed=61)
    reading_shade(cr, w, h, 0.5)
    vignette(cr, w, h, 0.55)


def bg_desert(cr, w, h, rnd):
    import wsfour as w4
    base(cr, w, h, ['#3a1608', '#24100a', '#0c0503'], angle=0.0)
    ws.stars(cr, (0, 0, w, h * 0.3), _area(w, h, 9000), 63, colors=('#ffe8c8', '#ffffff'))
    hz = h * 0.62
    halo(cr, w * 0.24, hz, max(w, h) * 0.45, rgb('#ff6a1a'), 0.32)
    w4.sun_disc(cr, w * 0.24, hz - h * 0.04, min(w, h) * 0.11)
    for layer, (col, amp, yk) in enumerate((('#4a1a14', 0.16, 0.0), ('#2a0e08', 0.1, 0.05))):   # mesas
        cr.move_to(0, h)
        x = 0
        while x <= w + 40:
            top = hz + yk * h - rnd.uniform(0, amp * h) * (1 if rnd.random() < 0.35 else 0.2)
            cr.line_to(x, top)
            x += rnd.uniform(40, 120)
            cr.line_to(x, top)
            x += rnd.uniform(10, 30)
        cr.line_to(w, h)
        cr.close_path()
        cr.set_source_rgba(*rgb(col), 0.95)
        cr.fill()
    for k in range(3):   # dunes
        cr.move_to(0, h)
        y0 = h * (0.78 + k * 0.07)
        cr.line_to(0, y0)
        for i in range(1, 21):
            cr.line_to(w * i / 20, y0 - math.sin(i / 20 * PI * (1.5 + k) + k) * h * 0.04)
        cr.line_to(w, h)
        cr.close_path()
        cr.set_source(_vg(h * 0.7, h, ('#8a4a1a', '#5a2a0e', '#3a1a08')[k], '#120804'))
        cr.fill()
    for k in range(int(w / 300) + 2):
        cx = rnd.choice((rnd.uniform(0.02, 0.2), rnd.uniform(0.8, 0.98))) * w
        w4.cactus(cr, cx, h * rnd.uniform(0.86, 0.98), h * rnd.uniform(0.18, 0.3), a=0.95)
    w4.bull_skull(cr, w * 0.62, h * 0.93, min(w, h) * 0.08, a=0.85)
    cr.set_line_width(1)   # heat haze
    for k in range(6):
        yy = hz - h * 0.05 + k * 6
        cr.move_to(0, yy)
        for i in range(1, 41):
            cr.line_to(w * i / 40, yy + math.sin(i * 1.3 + k) * 1.5)
        cr.set_source_rgba(1, 0.8, 0.5, 0.04)
        cr.stroke()
    for _ in range(_area(w, h, 5000)):   # dust
        cr.arc(rnd.uniform(0, w), rnd.uniform(h * 0.4, h), rnd.uniform(0.5, 1.4), 0, 2 * PI)
        cr.set_source_rgba(1, 0.75, 0.4, rnd.uniform(0.08, 0.3))
        cr.fill()
    grain(cr, w, h, 0.07, seed=63)
    reading_shade(cr, w, h, 0.5)
    vignette(cr, w, h, 0.5)


def _vg(y0, y1, top, bottom, a=1.0):
    g = cairo.LinearGradient(0, y0, 0, y1)
    g.add_color_stop_rgba(0, *rgb(top), a)
    g.add_color_stop_rgba(1, *rgb(bottom), a)
    return g


def bg_neotokyo(cr, w, h, rnd):
    import wsfour as w4
    base(cr, w, h, ['#160a3a', '#0c0626', '#04020e'])
    for fx, fy, col in ((0.15, 0.25, '#e03cff'), (0.85, 0.3, '#3a6bff'), (0.5, 0.95, '#ff3ab4')):
        halo(cr, w * fx, h * fy, max(w, h) * 0.4, rgb(col), 0.14)
    ws.stars(cr, (0, 0, w, h * 0.35), _area(w, h, 12000), 65)
    lights = [rgb('#ff3ab4'), rgb('#3ad8ff'), rgb('#ffd23a'), rgb('#b44dff')]
    w4.skyline(cr, -10, w + 10, h * 0.8, h * 0.18, h * 0.6, rnd, rgb('#100a2e'), lights, 0.95, (24, 60), 3)
    w4.torii(cr, w * 0.72, h * 0.86, min(w, h) * 0.22, min(w, h) * 0.2, rgb('#08041a'), rgb('#ff3ab4'))
    w4.skyline(cr, -10, w + 10, h * 0.92, h * 0.06, h * 0.32, rnd, rgb('#07041a'), lights, 1.0, (30, 80), 3.4)
    for k in range(int(w / 220) + 2):   # neon signs on the fronts
        sx, sy = rnd.uniform(0.04, 0.96) * w, rnd.uniform(0.45, 0.8) * h
        col = rnd.choice(lights)
        sh = rnd.uniform(40, 90)
        w4.neon(cr, lambda: ws.rounded(cr, sx, sy, 10, sh, 2), col, 1.4, 0.75)
    bx, by = w * 0.08, h * 0.42   # the big sign: 未来
    ws.rounded(cr, bx, by, 40, 86, 4)
    cr.set_source_rgba(*rgb('#12062a'), 0.95)
    cr.fill()
    w4.neon(cr, lambda: ws.rounded(cr, bx, by, 40, 86, 4), rgb('#ff3ab4'), 1.8)
    w4.kanji(cr, 'mi', bx + 7, by + 8, 26, rgb('#ff3ab4'), 2.2)
    w4.kanji(cr, 'rai', bx + 7, by + 46, 26, rgb('#ff3ab4'), 2.2)
    for k in range(int(w / 30)):   # the wet street mirrors the lights
        x = rnd.uniform(0, w)
        g = cairo.LinearGradient(0, h * 0.92, 0, h)
        col = rnd.choice(lights)
        g.add_color_stop_rgba(0, *col, 0.3)
        g.add_color_stop_rgba(1, *col, 0)
        cr.rectangle(x, h * 0.92, rnd.uniform(2, 8), h * 0.08)
        cr.set_source(g)
        cr.fill()
    cr.set_line_width(0.8)   # rain
    for _ in range(_area(w, h, 1800)):
        x, y, L = rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(8, 20)
        cr.move_to(x, y)
        cr.line_to(x - L * 0.2, y + L)
    cr.set_source_rgba(*rgb('#b8a8ff'), 0.07)
    cr.stroke()
    w4.blossom_branch(cr, w + 6, -6, min(w, h) * 0.45, 2.4, rnd, n=22)
    for _ in range(_area(w, h, 20000)):
        w4.petal(cr, rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(4, 8), rnd.uniform(0, 3), a=0.7)
    grain(cr, w, h, 0.07, seed=65)
    reading_shade(cr, w, h, 0.5)
    vignette(cr, w, h, 0.5)


def bg_abyss(cr, w, h, rnd):
    import wsfour as w4
    base(cr, w, h, ['#04284a', '#021630', '#010814'], angle=0.1)
    rays(cr, w * 0.3, -h * 0.1, w, h, rgb('#5ad8ff'), 7, 0.07, 0.8, rnd)
    rays(cr, w * 0.75, -h * 0.1, w, h, rgb('#5ad8ff'), 5, 0.05, 0.7, rnd)
    cr.set_line_width(1.2)   # caustics near the surface
    for k in range(9):
        yy = h * 0.03 + k * h * 0.025
        cr.move_to(0, yy)
        for i in range(1, 61):
            cr.line_to(w * i / 60, yy + math.sin(i * 0.9 + k * 1.7) * 5 + math.sin(i * 0.37 + k) * 3)
        cr.set_source_rgba(*rgb('#8ae8ff'), 0.06)
        cr.stroke()
    for _ in range(_area(w, h, 2500)):   # marine snow
        cr.arc(rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(0.4, 1.3), 0, 2 * PI)
        cr.set_source_rgba(0.8, 0.95, 1, rnd.uniform(0.08, 0.35))
        cr.fill()
    for k in range(_area(w, h, 90000) + 3):   # jellyfish drifting along the edges
        jx = rnd.choice((rnd.uniform(0.03, 0.2), rnd.uniform(0.78, 0.97))) * w
        w4.jellyfish(cr, jx, rnd.uniform(0.1, 0.6) * h, rnd.uniform(26, 60),
                     rgb(rnd.choice(('#5ab8ff', '#b07cff', '#2affc8', '#ff7ab8'))), rnd.uniform(0, 6), 0.75)
    cr.move_to(0, h)   # the sea floor
    for i in range(0, 41):
        cr.line_to(w * i / 40, h * 0.9 - math.sin(i * 0.5) * h * 0.03 - rnd.uniform(0, h * 0.02))
    cr.line_to(w, h)
    cr.close_path()
    cr.set_source_rgba(*rgb('#020a16'), 0.95)
    cr.fill()
    for k in range(int(w / 70) + 2):
        x = rnd.uniform(0, w)
        if rnd.random() < 0.5:
            w4.coral(cr, x, h * 0.95, rnd.uniform(30, 70), rgb(rnd.choice(('#ff5a9a', '#2affc8', '#ffb84a'))), rnd,
                     0.85, depth=3)
        else:
            w4.seaweed(cr, x, h, rnd.uniform(40, 110), rgb(rnd.choice(('#1ab890', '#2affc8'))), rnd.uniform(0, 6), 0.8)
    base_c, rim = rgb('#030c1c'), rgb('#3ad8ff')
    for i in range(3):   # a giant arm reaching up from the lower right
        pts = [(w + 20 - t * w * 0.012 * (1 + i * 0.3), h + 20 - t * h * 0.016 + math.sin(t / 4 + i) * 16)
               for t in range(36)]
        w4.tentacle(cr, pts, rnd.uniform(18, 30), base_c, rim, rgb('#2ccfff'), a=0.9)
    for _ in range(_area(w, h, 15000)):
        w4.bubble(cr, rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(1.5, 5), rgb('#5af0ff'), 0.5)
    grain(cr, w, h, 0.07, seed=67)
    reading_shade(cr, w, h, 0.5)
    vignette(cr, w, h, 0.55)


def bg_forest(cr, w, h, rnd):
    import wsfour as w4
    base(cr, w, h, ['#10260a', '#081406', '#020602'])
    rays(cr, w * 0.4, -h * 0.15, w, h, rgb('#e8ff8a'), 8, 0.06, 0.9, rnd)
    for k in range(int(w / 140) + 3):   # trunks, far and near
        tx = rnd.uniform(-0.05, 1.05) * w
        tw = rnd.uniform(14, 46)
        near = rnd.random() < 0.4
        col = rgb('#060e04' if near else '#0c1c08')
        cr.rectangle(tx - tw / 2, 0, tw, h)
        cr.set_source_rgba(*col, 0.95 if near else 0.75)
        cr.fill()
        cr.set_line_width(1)
        for i in range(int(h / 40)):   # bark
            cr.move_to(tx - tw * 0.3 + rnd.uniform(-3, 3), i * 40 + rnd.uniform(0, 20))
            cr.line_to(tx - tw * 0.3 + rnd.uniform(-3, 3), i * 40 + rnd.uniform(25, 40))
        cr.set_source_rgba(*rgb('#3a5a1a'), 0.25)
        cr.stroke()
    _fog(cr, w, h * 0.55, h * 0.3, rgb('#8ac85a'), 0.08, rnd)
    for k in range(int(w / 50)):   # ferns and grass at the feet
        gx = rnd.uniform(0, w)
        for i in range(5):
            ang = -PI / 2 + rnd.uniform(-0.8, 0.8)
            L = rnd.uniform(20, 60)
            cr.move_to(gx, h)
            cr.curve_to(gx + math.cos(ang) * L * 0.3, h + math.sin(ang) * L * 0.6, gx + math.cos(ang) * L * 0.8,
                        h + math.sin(ang) * L * 0.8, gx + math.cos(ang) * L, h + math.sin(ang) * L * 0.7)
        cr.set_line_width(2)
        cr.set_source_rgba(*rgb('#1e4a10'), 0.9)
        cr.stroke()
    for k in range(int(w / 160) + 2):
        w4.mushroom(cr, rnd.uniform(0.03, 0.97) * w, h - rnd.uniform(2, 10), rnd.uniform(18, 40),
                    tilt=rnd.uniform(-0.2, 0.2))
    vine_pts = [(w * 0.02 + math.sin(i / 5) * 12, i * h / 30) for i in range(18)]
    w4.vine(cr, vine_pts, 6, rnd)
    for _ in range(_area(w, h, 4000)):   # fireflies
        w4.firefly(cr, rnd.uniform(0, w), rnd.uniform(h * 0.15, h), rnd.uniform(0.8, 2.0), rgb('#e8ff6a'),
                   rnd.uniform(0.25, 0.9))
    for _ in range(_area(w, h, 120000) + 2):
        w3_butterfly(cr, rnd.uniform(0.05, 0.95) * w, rnd.uniform(0.1, 0.6) * h, rnd.uniform(7, 12))
    grain(cr, w, h, 0.07, seed=69)
    reading_shade(cr, w, h, 0.5)
    vignette(cr, w, h, 0.55)


def w3_butterfly(cr, x, y, s):
    import wsthree as w3
    w3.butterfly(cr, x, y, s, random.Random(int(x)).uniform(-0.5, 0.5), rgb('#ffe066'), rgb('#ffb000'), 0.8)


def bg_cosmos(cr, w, h, rnd):
    import wsfour as w4
    base(cr, w, h, ['#0c0e34', '#06071e', '#02020a'])
    for _ in range(9):   # nebula
        halo(cr, rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(0.2, 0.45) * max(w, h),
             rgb(rnd.choice(('#c04dff', '#3a5aff', '#ff4fa8', '#6a6cff'))), rnd.uniform(0.06, 0.14))
    grain(cr, w, h, 0.12, seed=71, soft=True, op=cairo.OPERATOR_SOFT_LIGHT)
    ws.stars(cr, (0, 0, w, h), _area(w, h, 1800), 71, colors=('#ffffff', '#b8c0ff', '#ffd8f0'))
    for _ in range(_area(w, h, 60000) + 3):
        ws.sparkle(cr, rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(3, 7), (1, 1, 1), 0.7)
    pr = min(w, h) * 0.22
    w4.planet(cr, w * 0.92, h * 0.3, pr, rgb('#8a7cff'), rgb('#2a1a7a'), tilt=-0.25, ring_c=rgb('#d8b8ff'), a=0.9)
    w4.planet(cr, w * 0.68, h * 0.12, pr * 0.18, rgb('#ff8ab8'), rgb('#6a2a6a'), ring=False, a=0.9)
    for _ in range(int(w / 50) + 4):   # an asteroid belt low across the picture
        f = rnd.random()
        w4.asteroid(cr, f * w, h * (0.86 + math.sin(f * 3) * 0.06) + rnd.uniform(-20, 20), rnd.uniform(4, 16), rnd,
                    a=0.9)
    sx, sy = w * 0.2, h * 0.15   # a shooting star
    g = cairo.LinearGradient(sx, sy, sx + 160, sy + 60)
    g.add_color_stop_rgba(0, 1, 1, 1, 0)
    g.add_color_stop_rgba(1, 1, 1, 1, 0.8)
    cr.move_to(sx, sy)
    cr.line_to(sx + 160, sy + 60)
    cr.set_source(g)
    cr.set_line_width(1.6)
    cr.stroke()
    w4.helmet(cr, w * 0.08, h * 0.82, min(w, h) * 0.14, a=0.85)
    reading_shade(cr, w, h, 0.45)
    vignette(cr, w, h, 0.5)


def bg_samurai(cr, w, h, rnd):
    import wsfour as w4
    base(cr, w, h, ['#2e0612', '#16040a', '#060103'])
    mr = min(w, h) * 0.16
    w4.moon(cr, w * 0.18, h * 0.24, mr, rgb('#ff2a1a'), glow=0.55, craters=False)
    for _ in range(5):   # streaks of cloud across the moon
        cy = h * 0.24 + rnd.uniform(-mr, mr)
        cr.save()
        cr.translate(w * 0.18 + rnd.uniform(-mr, mr), cy)
        cr.scale(mr * rnd.uniform(1.5, 3), mr * rnd.uniform(0.05, 0.12))
        cr.arc(0, 0, 1, 0, 2 * PI)
        cr.restore()
        cr.set_source_rgba(*rgb('#1a0408'), 0.85)
        cr.fill()
    for k, (col, yk) in enumerate((('#2a0810', 0.62), ('#16040a', 0.74), ('#0a0205', 0.86))):   # mountains
        cr.move_to(0, h)
        x = 0
        while x <= w:
            cr.line_to(x, h * yk - rnd.uniform(0, h * 0.12))
            x += rnd.uniform(40, 110)
        cr.line_to(w, h)
        cr.close_path()
        cr.set_source_rgba(*rgb(col), 0.97)
        cr.fill()
        if k == 1:
            w4.pagoda(cr, w * 0.2, h * 0.76, min(w, h) * 0.32, rgb('#0e0306'), rgb('#ff6a3a'))
    _fog(cr, w, h * 0.7, h * 0.2, rgb('#aa3a4a'), 0.12, rnd)
    for k in range(4):   # a sakura tree reaching in from the upper right
        w4.blossom_branch(cr, w + 10, h * (0.02 + k * 0.1), min(w, h) * rnd.uniform(0.3, 0.5),
                          PI + rnd.uniform(-0.4, 0.3), rnd, n=20)
    for _ in range(_area(w, h, 9000)):
        w4.petal(cr, rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(4, 9), rnd.uniform(0, 3),
                 rgb(rnd.choice(('#ff8ab8', '#ffb0cc', '#ff6a9a'))), rnd.uniform(0.4, 0.85))
    L = min(w * 0.5, 420)
    w4.katana(cr, w * 0.5, h * 0.95, -0.12, L, 0.85)
    grain(cr, w, h, 0.08, seed=73)
    reading_shade(cr, w, h, 0.5)
    vignette(cr, w, h, 0.55)


def bg_steampunk(cr, w, h, rnd):
    import wsfour as w4
    base(cr, w, h, ['#2e1608', '#180b04', '#080402'])
    halo(cr, w * 0.7, h * 0.35, max(w, h) * 0.45, rgb('#ff8a1a'), 0.18)
    for _ in range(5):   # big gears turning in the dark
        w4.gear(cr, rnd.choice((rnd.uniform(-0.05, 0.2), rnd.uniform(0.8, 1.05))) * w, rnd.uniform(0, 1) * h,
                rnd.uniform(60, 140), rnd.randint(14, 24), rnd.uniform(0, 1), a=0.18)
    sil = rgb('#0c0603')
    for k in range(int(w / 120) + 2):   # factory and smokestacks
        fx = rnd.uniform(0, w)
        fw, fh = rnd.uniform(30, 80), rnd.uniform(h * 0.1, h * 0.3)
        cr.rectangle(fx, h - fh, fw, fh)
        if rnd.random() < 0.6:
            sx = fx + fw * rnd.uniform(0.2, 0.8)
            sh = fh + rnd.uniform(40, 120)
            cr.rectangle(sx - 5, h - sh, 10, sh)
            for i in range(5):
                w4.steam(cr, sx + i * 14 + rnd.uniform(-4, 4), h - sh - i * 26, 14 + i * 6, 0.35, int(sx) + i,
                         (0.55, 0.45, 0.38))
        cr.set_source_rgba(*sil, 0.95)
        cr.fill()
    w4.airship(cr, w * 0.75, h * 0.18, min(w, h) * 0.4, 0.85)
    py_ = h * 0.92   # pipes along the bottom
    for k in range(2):
        yy = py_ + k * 16
        w4.brass_path(cr, lambda: (cr.new_path(), cr.move_to(-10, yy), cr.line_to(w + 10, yy)), 9 - k * 2, 0.9)
        for i in range(int(w / 120) + 1):
            fx = i * 120 + rnd.uniform(0, 40)
            ws.rounded(cr, fx - 4, yy - 7, 8, 14, 2)
            cr.set_source(w4._vgrad(yy - 7, yy + 7, rgb('#ffd27a'), rgb('#6a3a12')))
            cr.fill()
    w4.gauge(cr, w * 0.9, h * 0.8, min(w, h) * 0.06, 0.4, 0.9)
    for _ in range(_area(w, h, 7000)):   # sparks
        cr.arc(rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(0.5, 1.5), 0, 2 * PI)
        cr.set_source_rgba(*rgb(rnd.choice(('#ffb84a', '#ff8a1a'))), rnd.uniform(0.15, 0.6))
        cr.fill()
    grain(cr, w, h, 0.1, seed=75)
    reading_shade(cr, w, h, 0.5)
    vignette(cr, w, h, 0.55)


def bg_glacier(cr, w, h, rnd):
    import wsfour as w4
    base(cr, w, h, ['#0c1e40', '#06112c', '#020610'])
    ws.stars(cr, (0, 0, w, h * 0.5), _area(w, h, 5000), 77, colors=('#ffffff', '#cdf6ff'))
    for k, col in enumerate(('#2affc8', '#4fc8ff', '#8a7cff')):   # an aurora
        cr.move_to(-10, h * 0.1)
        for i in range(1, 31):
            cr.line_to(w * i / 30, h * (0.12 + 0.06 * k) + math.sin(i * 0.5 + k * 1.3) * h * 0.04)
        g = cairo.LinearGradient(0, h * 0.05, 0, h * 0.35)
        g.add_color_stop_rgba(0, *rgb(col), 0)
        g.add_color_stop_rgba(0.5, *rgb(col), 0.16)
        g.add_color_stop_rgba(1, *rgb(col), 0)
        cr.set_line_width(h * 0.08)
        cr.set_source(g)
        cr.stroke()
    for k, (col, yk) in enumerate((('#1a3a66', 0.55), ('#0e2448', 0.68))):   # snowy peaks
        cr.move_to(0, h)
        x = 0
        tops = []
        while x <= w + 60:
            ty = h * yk - rnd.uniform(0, h * 0.18)
            tops.append((x, ty))
            x += rnd.uniform(60, 160)
        for i, (tx, ty) in enumerate(tops):
            cr.line_to(tx, ty)
        cr.line_to(w, h)
        cr.close_path()
        cr.set_source_rgba(*rgb(col), 0.95)
        cr.fill()
        for i in range(1, len(tops) - 1):   # snow caps down the slopes of each peak
            (lx, ly), (tx, ty), (rx, ry) = tops[i - 1], tops[i], tops[i + 1]
            if ty > ly or ty > ry:
                continue
            f = 0.3
            ax, ay = tx + (lx - tx) * f, ty + (ly - ty) * f
            bx, by = tx + (rx - tx) * f, ty + (ry - ty) * f
            _poly(cr, [(tx, ty), (bx, by), (tx + (bx - tx) * 0.55, by - (by - ty) * 0.15),
                       (tx + (bx - tx) * 0.2, ty + (by - ty) * 0.75), (tx + (ax - tx) * 0.35, ay - (ay - ty) * 0.1),
                       (ax, ay)], True)
            cr.set_source_rgba(0.85, 0.95, 1, 0.32 - k * 0.1)
            cr.fill()
    w4.crystal_cluster(cr, w * 0.04, h * 1.0, h * 0.45, rgb('#4fc8ff'), rnd, 0.8, n=7)
    w4.crystal_cluster(cr, w * 0.96, h * 1.0, h * 0.36, rgb('#4fc8ff'), rnd, 0.75, n=6)
    for i in range(int(w / 12)):   # the frozen lake
        y = h * 0.86 + rnd.uniform(0, h * 0.14)
        x = rnd.uniform(0, w)
        cr.move_to(x, y)
        cr.line_to(x + rnd.uniform(20, 80), y)
    cr.set_line_width(1)
    cr.set_source_rgba(0.7, 0.9, 1, 0.06)
    cr.stroke()
    w4.wolf(cr, w * 0.8, h * 0.8, min(w, h) * 0.22, rgb('#16305a'), rgb('#9ae8ff'), rgb('#4fe0ff'), 0.85)
    for _ in range(_area(w, h, 3000)):   # snowfall
        r = rnd.uniform(0.6, 2.2)
        cr.arc(rnd.uniform(0, w), rnd.uniform(0, h), r, 0, 2 * PI)
        cr.set_source_rgba(1, 1, 1, rnd.uniform(0.15, 0.6) * (r / 2.2))
        cr.fill()
    for _ in range(_area(w, h, 60000) + 2):
        w4.snowflake(cr, rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(6, 12), rgb('#cdf6ff'), 0.45, 1.0)
    grain(cr, w, h, 0.06, seed=77)
    reading_shade(cr, w, h, 0.45)
    vignette(cr, w, h, 0.5)


def bg_witch(cr, w, h, rnd):
    import wsfour as w4
    base(cr, w, h, ['#1e0a36', '#100422', '#05020c'])
    violet = rgb('#b43cff')
    w4.crescent(cr, w * 0.12, h * 0.16, min(w, h) * 0.07, rgb('#e8d8ff'), glow=0.4)
    sil = rgb('#07020e')
    w4.dead_tree(cr, w + 10, h + 10, h * 0.6, -1.85, 24, rnd, sil, 5)
    w4.raven(cr, w * 0.82, h * 0.42, min(w, h) * 0.12, a=0.95)
    R = min(w, h) * 0.3   # the magic circle
    cx, cy = w * 0.68, h * 0.62
    halo(cr, cx, cy, R * 1.6, violet, 0.12)
    w4.pentagram(cr, cx, cy, R, violet, 1.6, 0.35)
    cr.arc(cx, cy, R * 1.12, 0, 2 * PI)
    cr.set_line_width(1)
    cr.set_source_rgba(*violet, 0.25)
    cr.stroke()
    for k in range(12):   # runes round the circle
        ang = k * PI / 6
        rx, ry = cx + math.cos(ang) * R * 1.06, cy + math.sin(ang) * R * 1.06
        cr.move_to(rx - 3, ry - 4)
        cr.line_to(rx + 2, ry)
        cr.line_to(rx - 2, ry + 4)
    cr.set_source_rgba(*rgb('#e8b8ff'), 0.4)
    cr.stroke()
    for k in range(int(w / 110) + 3):   # candles on the floor
        x = rnd.uniform(0.03, 0.97) * w
        w4.candle(cr, x, h - rnd.uniform(4, 20), rnd.uniform(18, 40), rnd.uniform(6, 10), a=0.95,
                  lean=rnd.uniform(-0.08, 0.08))
    w4.spellbook(cr, w * 0.16, h * 0.93, min(w, h) * 0.22, 0.95)
    _fog(cr, w, h * 0.8, h * 0.2, rgb('#6a3aaa'), 0.12, rnd)
    for _ in range(_area(w, h, 30000) + 4):
        w4.wisp(cr, rnd.uniform(0, w), rnd.uniform(0.15, 0.8) * h, rnd.uniform(10, 20),
                rgb(rnd.choice(('#c84cff', '#7aff9a', '#ff6ad5'))), 0.55)
    for _ in range(_area(w, h, 4500)):
        ws.sparkle(cr, rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(1.2, 3),
                   rgb(rnd.choice(('#e8b8ff', '#ffffff'))), rnd.uniform(0.2, 0.6))
    grain(cr, w, h, 0.08, seed=79)
    reading_shade(cr, w, h, 0.5)
    vignette(cr, w, h, 0.55)


def bg_dragon(cr, w, h, rnd):
    import wsfour as w4
    base(cr, w, h, ['#300a06', '#180403', '#080101'])
    halo(cr, w * 0.6, h * 0.5, max(w, h) * 0.5, rgb('#ff5a1a'), 0.12)
    gold = rgb(w4.GOLD)
    for _ in range(_area(w, h, 40000) + 5):   # clouds
        w4.cloud_scroll(cr, rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(40, 90), rgb('#c88a2a'),
                        rnd.uniform(0.25, 0.45), rnd.choice((-1, 1)))
    w4.pagoda(cr, w * 0.9, h, min(w, h) * 0.5, rgb('#120302'), rgb('#ff6a3a'))
    pts = []   # the dragon winding across the lower half
    for t in range(140):
        f = t / 139
        pts.append((w * (-0.05 + 1.0 * f), h * (0.85 - 0.25 * f) + math.sin(f * 9) * h * 0.08))
    w4.dragon_body(cr, pts, min(w, h) * 0.06, a=0.8, head_k=2.6)
    for k in range(int(w / 300) + 2):   # lanterns hanging from the top
        w4.lantern_cn(cr, rnd.uniform(0.05, 0.95) * w, rnd.uniform(0, 30), rnd.uniform(30, 52), 0.95)
    w4.meander(cr, 0, w, 10, 8, gold, 1.0, 0.25)
    w4.meander(cr, 0, w, h - 10, 8, gold, 1.0, 0.25)
    for _ in range(_area(w, h, 14000)):
        w4.sakura(cr, rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(3, 6), rgb('#ff6a8a'), rnd.uniform(0, 1),
                  rnd.uniform(0.4, 0.8))
    for _ in range(_area(w, h, 5000)):   # embers
        cr.arc(rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(0.5, 1.6), 0, 2 * PI)
        cr.set_source_rgba(*rgb(rnd.choice(('#ffc42e', '#ff6a1a'))), rnd.uniform(0.15, 0.6))
        cr.fill()
    grain(cr, w, h, 0.08, seed=81)
    reading_shade(cr, w, h, 0.5)
    vignette(cr, w, h, 0.55)


def bg_graffiti(cr, w, h, rnd):
    import wsfour as w4
    base(cr, w, h, ['#1a1024', '#0e0818', '#05030a'])
    w4.bricks(cr, 0, 0, w, h, rgb('#241a30'), rnd, 46, 20, 0.85)
    cols = [rgb(c) for c in w4.SPRAY]
    for _ in range(_area(w, h, 26000) + 4):   # splats and drips all over the wall
        x, y = rnd.uniform(0, w), rnd.uniform(0, h * 0.8)
        if 0.25 * w < x < 0.6 * w and 0.2 * h < y < 0.7 * h and rnd.random() < 0.7:
            continue   # keep the middle calmer for the text
        w4.splat(cr, x, y, rnd.uniform(8, 26), rnd.choice(cols), rnd, rnd.uniform(0.35, 0.7),
                 drips=rnd.randint(1, 4))
    for k in range(3):   # big sprayed strokes
        x0, y0 = rnd.uniform(0, w), rnd.uniform(0, h)
        pts = [(x0 + i * 30, y0 + math.sin(i * 0.8 + k) * 40) for i in range(int(rnd.uniform(5, 10)))]
        w4.spray(cr, lambda: w4._curve(cr, pts), rnd.choice(cols), 4, rnd, 0.45)
    w4.crown(cr, w * 0.85, h * 0.25, min(w, h) * 0.16, rgb('#eb1fed'), 2.6)
    w4.skull(cr, w * 0.12, h * 0.3, min(w, h) * 0.12, eyes=rgb('#25ebf5'), a=0.85)
    w4.crown(cr, w * 0.12, h * 0.3 - min(w, h) * 0.08, min(w, h) * 0.1, rgb('#25ebf5'), 2.0)
    for k, col in enumerate(cols[:3]):
        w4.spray_can(cr, w * (0.04 + k * 0.05), h - 4, min(w, h) * 0.12, col, 0.9)
    for k in range(int(w / 40)):   # the wet ground mirrors the colors
        x = rnd.uniform(0, w)
        g = cairo.LinearGradient(0, h * 0.93, 0, h)
        col = rnd.choice(cols)
        g.add_color_stop_rgba(0, *col, 0.25)
        g.add_color_stop_rgba(1, *col, 0)
        cr.rectangle(x, h * 0.93, rnd.uniform(3, 12), h * 0.07)
        cr.set_source(g)
        cr.fill()
    grain(cr, w, h, 0.1, seed=83)
    reading_shade(cr, w, h, 0.55)
    vignette(cr, w, h, 0.55)


SCENES.update({'halloween': bg_halloween, 'desert': bg_desert, 'neotokyo': bg_neotokyo, 'abyss': bg_abyss,
               'forest': bg_forest, 'cosmos': bg_cosmos, 'samurai': bg_samurai, 'steampunk': bg_steampunk,
               'glacier': bg_glacier, 'witch': bg_witch, 'dragon': bg_dragon, 'graffiti': bg_graffiti})


def render(style, w, h, tint=None):
    """The scene as a surface, from the cache when it was drawn before."""
    w, h = max(1, int(w)), max(1, int(h))
    key = hashlib.md5(f'{VERSION}|{style}|{w}|{h}|{tint}'.encode()).hexdigest()[:16]
    path = os.path.join(CACHE, f'{style}-{w}x{h}-{key}.png')
    try:
        return cairo.ImageSurface.create_from_png(path)
    except Exception:
        pass
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, w, h)
    cr = cairo.Context(surf)
    fn = SCENES.get(style)
    if fn:
        with ws.tinted(style, tint):
            fn(cr, w, h, random.Random(1234))
    try:
        os.makedirs(CACHE, exist_ok=True)
        surf.write_to_png(path + '.tmp')
        os.replace(path + '.tmp', path)
        files = sorted((os.path.join(CACHE, f) for f in os.listdir(CACHE)), key=os.path.getmtime)
        for old in files[:-40]:   # keep the cache small
            os.remove(old)
    except OSError:
        pass
    return surf
