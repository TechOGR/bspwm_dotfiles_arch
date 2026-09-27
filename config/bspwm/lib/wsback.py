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

VERSION = 2
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


def bg_gradient(cr, w, h, rnd):
    g = cairo.LinearGradient(0, 0, w, h)
    for t, col in ((0, '#10236a'), (0.5, '#2a1466'), (1, '#4a1060')):
        g.add_color_stop_rgb(t, *rgb(col))
    cr.set_source(g)
    cr.paint()
    for _ in range(6):   # mesh-like colour blobs
        halo(cr, rnd.uniform(0, w), rnd.uniform(0, h), rnd.uniform(0.35, 0.6) * max(w, h),
             rgb(rnd.choice(['#2f6bff', '#8b3dff', '#e040fb', '#5fe1ff'])), rnd.uniform(0.15, 0.3))
    for k in range(5):   # silky ribbons
        y0 = h * rnd.uniform(0.1, 0.9)
        cr.move_to(-20, y0)
        cr.curve_to(w * 0.3, y0 - 120, w * 0.6, y0 + 120, w + 20, y0 + rnd.uniform(-60, 60))
        cr.set_line_width(rnd.uniform(20, 60))
        cr.set_source_rgba(1, 1, 1, 0.025)
        cr.stroke()
    grain(cr, w, h, 0.10, seed=51)
    reading_shade(cr, w, h, 0.36)
    vignette(cr, w, h, 0.4)


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


def bg_macos(cr, w, h, rnd):
    base(cr, w, h, ['#2a3150', '#20253a', '#161a28'])
    for k, (col, a) in enumerate((('#5b8cff', 0.20), ('#b58cff', 0.16), ('#ff8ad8', 0.12))):   # Big Sur waves
        y0 = h * (0.45 + k * 0.15)
        cr.move_to(0, h)
        cr.line_to(0, y0)
        cr.curve_to(w * 0.3, y0 - 90, w * 0.6, y0 + 80, w, y0 - 40)
        cr.line_to(w, h)
        cr.close_path()
        g = cairo.LinearGradient(0, y0 - 90, 0, h)
        g.add_color_stop_rgba(0, *rgb(col), a)
        g.add_color_stop_rgba(1, *rgb(col), a * 0.3)
        cr.set_source(g)
        cr.fill()
    halo(cr, w / 2, 0, w * 0.7, (1, 1, 1), 0.06)
    grain(cr, w, h, 0.06, seed=71)
    reading_shade(cr, w, h, 0.3)
    vignette(cr, w, h, 0.35)


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
          'gradient': bg_gradient, 'pixel': bg_pixel, 'macos': bg_macos, 'minimal': bg_minimal,
          'sketch': bg_sketch, 'holo': bg_holo}


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
