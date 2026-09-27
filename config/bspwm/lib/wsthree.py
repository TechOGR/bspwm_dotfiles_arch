# =============================================================
# Author:  TechOGR
# Repo:    https://github.com/TechOGR/bspwm_dotfiles_arch
#
# wsthree - the third set of styles (Storm, Venom, Butterflies, Snakes)
# and the themed icons of EVERY style: the ghost and the pac-man wear the
# theme (electric cracks, venom and drips, flowers, scales, flames, lava
# cracks, leaves, bubbles, scanlines, chromatic glitch, glass, facets,
# neon tubes, iridescence) and the dots become the theme's own thing
# (electric orbs, blood drops, flowers, snake eyes, flames, embers,
# leaves, bubbles, reticles, diamonds, beads, crystals, rings, planets).
# Registered into lib/wspill.py when it is imported.
#
# Copyright (C) 2021-2026 TechOGR <https://github.com/TechOGR>
# Licensed under GPL-3.0 license
# =============================================================

import math
import random

import cairo

import wspill as ws
from wspill import PI, rgb, rounded, halo, hline, glow_stroke

# ═══════════════════════════════════════════════════════════ primitives


def _mix(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def _poly(cr, pts, close=False):
    cr.new_path()
    for i, p in enumerate(pts):
        (cr.move_to if i == 0 else cr.line_to)(*p)
    if close:
        cr.close_path()


def bolt_points(rnd, x0, y0, x1, y1, jag=0.28, depth=4):
    """A lightning path by midpoint displacement."""
    pts = [(x0, y0), (x1, y1)]
    for _ in range(depth):
        out = [pts[0]]
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            mx, my = (ax + bx) / 2, (ay + by) / 2
            L = math.hypot(bx - ax, by - ay)
            nx, ny = -(by - ay) / (L or 1), (bx - ax) / (L or 1)
            o = rnd.uniform(-jag, jag) * L
            out += [(mx + nx * o, my + ny * o), (bx, by)]
        pts = out
    return pts


def bolt(cr, rnd, x0, y0, x1, y1, width=1.6, glow=(0.45, 0.7, 1.0), branches=2, jag=0.28, a=1.0):
    pts = bolt_points(rnd, x0, y0, x1, y1, jag)
    for extra, al in ((9, 0.05), (5, 0.12), (2.5, 0.35)):
        _poly(cr, pts)
        cr.set_line_width(width + extra)
        cr.set_source_rgba(*glow, al * a)
        cr.stroke()
    _poly(cr, pts)
    cr.set_line_width(width)
    cr.set_source_rgba(0.92, 0.97, 1, a)
    cr.stroke()
    for _ in range(branches):   # forks off the main bolt
        i = rnd.randrange(1, max(2, len(pts) - 2))
        bx, by = pts[i]
        L = math.hypot(x1 - x0, y1 - y0) * rnd.uniform(0.2, 0.45)
        ang = math.atan2(y1 - y0, x1 - x0) + rnd.choice((-1, 1)) * rnd.uniform(0.5, 1.1)
        bolt(cr, rnd, bx, by, bx + math.cos(ang) * L, by + math.sin(ang) * L, width * 0.6, glow, 0, jag, a * 0.8)


def tube(cr, pts, widths, base, rim, glow=None, glow_a=0.35):
    """A thick body along pts (tentacle, snake), widths per point, lit on
    one side."""
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        ax, ay = pts[max(0, i - 1)]
        bx, by = pts[min(len(pts) - 1, i + 1)]
        L = math.hypot(bx - ax, by - ay) or 1
        nx, ny = -(by - ay) / L, (bx - ax) / L
        wd = widths[i] / 2
        left.append((x + nx * wd, y + ny * wd))
        right.append((x - nx * wd, y - ny * wd))
    outline = left + right[::-1]
    if glow:
        for extra, a in ((8, glow_a * 0.3), (4, glow_a * 0.6)):
            _poly(cr, outline, True)
            cr.set_line_width(extra)
            cr.set_source_rgba(*glow, a)
            cr.stroke()
    _poly(cr, outline, True)
    cr.set_source_rgba(*base, 1)
    cr.fill()
    _poly(cr, left)   # rim light
    cr.set_line_width(0.9)
    cr.set_source_rgba(*rim, 0.9)
    cr.stroke()
    return left, right


def wavy_ring(x, y, w, h, amp, waves, phase, step=3.0):
    """Points around a capsule, pushed in and out by a sine (vines,
    tentacles, snakes wrapping the pill)."""
    pts = ws.capsule_points(x, y, w, h, step)
    n = len(pts)
    return [(px + nx * amp * math.sin(i / n * 2 * PI * waves + phase),
             py + ny * amp * math.sin(i / n * 2 * PI * waves + phase), nx, ny)
            for i, (px, py, nx, ny) in enumerate(pts)]


def butterfly(cr, x, y, size, angle, c1, c2, a=1.0):
    """Two pairs of wings (gradient, glowing edge) and a dark body."""
    cr.save()
    cr.translate(x, y)
    cr.rotate(angle)
    halo(cr, 0, 0, size * 1.4, c1, 0.25 * a)
    for side in (-1, 1):
        for up, sc in ((1, 1.0), (-1, 0.7)):
            cr.save()
            cr.scale(side, 1)
            cr.new_path()
            cr.move_to(0, 0)
            if up > 0:
                cr.curve_to(size * 0.3, -size * 1.0, size * 1.1, -size * 1.0, size * 1.0, -size * 0.2)
                cr.curve_to(size * 0.9, size * 0.1, size * 0.3, size * 0.05, 0, 0)
            else:
                cr.curve_to(size * 0.5, size * 0.1, size * 0.8 * sc, size * 0.7, size * 0.35, size * 0.8)
                cr.curve_to(size * 0.1, size * 0.8, 0, size * 0.3, 0, 0)
            cr.close_path()
            g = cairo.LinearGradient(0, -size, size, size)
            g.add_color_stop_rgba(0, *c1, 0.85 * a)
            g.add_color_stop_rgba(1, *c2, 0.75 * a)
            cr.set_source(g)
            cr.fill_preserve()
            cr.set_source_rgba(1, 1, 1, 0.55 * a)
            cr.set_line_width(max(0.6, size * 0.06))
            cr.stroke()
            cr.restore()
    cr.move_to(0, -size * 0.35)
    cr.line_to(0, size * 0.55)
    cr.set_line_width(max(0.8, size * 0.1))
    cr.set_source_rgba(0.12, 0.05, 0.2, a)
    cr.stroke()
    for side in (-1, 1):   # antennae
        cr.move_to(0, -size * 0.35)
        cr.curve_to(side * size * 0.1, -size * 0.7, side * size * 0.3, -size * 0.8, side * size * 0.35, -size * 0.85)
    cr.set_line_width(max(0.5, size * 0.04))
    cr.stroke()
    cr.restore()


def flower(cr, x, y, r, c, center=(1, 1, 0.9), a=1.0, petals=5, rot=0.0):
    for k in range(petals):
        ang = rot + k * 2 * PI / petals
        cr.save()
        cr.translate(x + math.cos(ang) * r * 0.55, y + math.sin(ang) * r * 0.55)
        cr.rotate(ang)
        cr.scale(r * 0.55, r * 0.38)
        cr.arc(0, 0, 1, 0, 2 * PI)
        cr.restore()
        cr.set_source_rgba(*c, a)
        cr.fill()
    cr.arc(x, y, r * 0.28, 0, 2 * PI)
    cr.set_source_rgba(*center, a)
    cr.fill()


def drip(cr, x, y, L, w, c, a=1.0):
    cr.new_path()
    cr.move_to(x - w, y)
    cr.curve_to(x - w, y + L * 0.5, x - w * 1.3, y + L * 0.8, x, y + L)
    cr.curve_to(x + w * 1.3, y + L * 0.8, x + w, y + L * 0.5, x + w, y)
    cr.close_path()
    cr.set_source_rgba(*c, a)
    cr.fill()
    cr.arc(x - w * 0.3, y + L * 0.72, w * 0.35, 0, 2 * PI)
    cr.set_source_rgba(1, 1, 1, 0.45 * a)
    cr.fill()


def maw(cr, x, y, k, black, rim, red):
    """Venom's open jaws facing right, teeth and tongue, k = scale (1 = a
    26 px tall head)."""
    cr.save()
    cr.translate(x, y)
    cr.scale(k, k)
    for sy in (-1, 1):   # upper and lower jaw
        cr.new_path()
        cr.move_to(-4, sy * 13)
        cr.curve_to(10, sy * 18, 26, sy * 16, 38, sy * 13)
        cr.curve_to(34, sy * 10, 30, sy * 8, 27, sy * 7)
        cr.curve_to(18, sy * 4, 10, sy * 2, 2, sy * 1)
        cr.close_path()
        g = cairo.LinearGradient(0, sy * 18, 0, 0)
        g.add_color_stop_rgb(0, *_mix(black, rim, 0.18))
        g.add_color_stop_rgb(1, *black)
        cr.set_source(g)
        cr.fill()
        cr.move_to(-4, sy * 13)   # rim light along the outer edge
        cr.curve_to(10, sy * 18, 26, sy * 16, 38, sy * 13)
        cr.set_line_width(1)
        cr.set_source_rgba(*rim, 0.8)
        cr.stroke()
    cr.new_path()   # the mouth
    cr.move_to(2, -1)
    cr.curve_to(10, -2, 18, -4, 27, -7)
    cr.curve_to(30, -2, 30, 2, 27, 7)
    cr.curve_to(18, 4, 10, 2, 2, 1)
    cr.close_path()
    g = cairo.RadialGradient(8, 0, 0, 14, 0, 18)
    g.add_color_stop_rgb(0, 0.25, 0, 0.02)
    g.add_color_stop_rgb(1, *red)
    cr.set_source(g)
    cr.fill()
    for i in range(7):   # fangs along both jaws
        t = 0.12 + i * 0.13
        tx, ty = 2 + 25 * t, 1 + 6 * t * t
        L = 2.5 + 3.5 * (1 - abs(t - 0.6))
        for sy in (-1, 1):
            cr.move_to(tx - 1.3, sy * ty)
            cr.line_to(tx + 1.3, sy * ty)
            cr.line_to(tx + 0.4, sy * (ty - L))
            cr.close_path()
    cr.set_source_rgba(1, 0.95, 0.9, 1)
    cr.fill()
    cr.move_to(4, 0.5)   # the tongue
    cr.curve_to(16, 3, 26, -2, 36, 5)
    cr.set_line_width(1.8)
    cr.set_source_rgba(*_mix(red, (1, 0.4, 0.5), 0.3), 1)
    cr.stroke()
    cr.restore()


def snake_head(cr, x, y, size, angle, base, rim, eye):
    cr.save()
    cr.translate(x, y)
    cr.rotate(angle)
    cr.new_path()   # wedge head
    cr.move_to(-size * 0.3, -size * 0.45)
    cr.curve_to(size * 0.4, -size * 0.6, size * 1.0, -size * 0.3, size * 1.1, 0)
    cr.curve_to(size * 1.0, size * 0.3, size * 0.4, size * 0.6, -size * 0.3, size * 0.45)
    cr.close_path()
    g = cairo.LinearGradient(0, -size * 0.6, 0, size * 0.6)
    g.add_color_stop_rgb(0, *_mix(base, rim, 0.35))
    g.add_color_stop_rgb(1, *base)
    cr.set_source(g)
    cr.fill_preserve()
    cr.set_source_rgba(*rim, 0.9)
    cr.set_line_width(1)
    cr.stroke()
    halo(cr, size * 0.45, -size * 0.2, size * 0.5, eye, 0.6)
    cr.save()   # eye with a slit pupil
    cr.translate(size * 0.45, -size * 0.2)
    cr.scale(size * 0.16, size * 0.12)
    cr.arc(0, 0, 1, 0, 2 * PI)
    cr.restore()
    cr.set_source_rgba(*eye, 1)
    cr.fill()
    cr.rectangle(size * 0.44, -size * 0.3, size * 0.03, size * 0.2)
    cr.set_source_rgba(0, 0, 0, 1)
    cr.fill()
    cr.move_to(size * 1.08, 0)   # forked tongue
    cr.line_to(size * 1.45, 0)
    cr.line_to(size * 1.62, -size * 0.12)
    cr.move_to(size * 1.45, 0)
    cr.line_to(size * 1.62, size * 0.12)
    cr.set_line_width(max(0.8, size * 0.07))
    cr.set_source_rgba(*rim, 1)
    cr.stroke()
    cr.restore()


def snake_body(cr, pts, wmax, base, rim, glow, head=True, tail=True, head_k=1.7):
    n = len(pts)
    widths = []
    for i in range(n):   # taper over a few points, whatever the length
        wd = wmax
        if tail:
            wd *= min(1.0, 0.25 + i / 18)
        if head:
            wd *= min(1.0, 0.7 + (n - 1 - i) / 12)
        widths.append(wd)
    left, right = tube(cr, pts, widths, base, rim, glow, 0.35)
    for i in range(2, n - 2, 2):   # scales: little arcs across the body
        (lx, ly), (rx, ry) = left[i], right[i]
        mx, my = (lx + rx) / 2, (ly + ry) / 2
        r = widths[i] * 0.42
        ang = math.atan2(pts[min(n - 1, i + 1)][1] - pts[i - 1][1], pts[min(n - 1, i + 1)][0] - pts[i - 1][0])
        cr.new_path()
        cr.arc(mx, my, r, ang + PI * 0.5, ang + PI * 1.5)
        cr.set_line_width(0.6)
        cr.set_source_rgba(*rim, 0.35)
        cr.stroke()
    if head and n > 2:
        (ax, ay), (bx, by) = pts[-2], pts[-1]
        snake_head(cr, bx, by, wmax * head_k, math.atan2(by - ay, bx - ax), base, rim, rgb('#e8ff5a'))


# ═══════════════════════════════════════════════════════════ new styles
ws.STYLES += [
    ('storm', 'Storm', 'lightning, pure energy'),
    ('venom', 'Venom', 'moving shadows, venom'),
    ('butterfly', 'Butterflies', 'delicate, free, magic'),
    ('snake', 'Snakes', 'power, mystery, scales'),
]
ws.STYLE_IDS = [s[0] for s in ws.STYLES]
ws.COLORS.update({
    'storm': ('#8fd0ff', '#dff0ff', ['#4fa8ff', '#5fb4ff', '#6fc0ff', '#8fd0ff']),
    'venom': ('#ff3a2a', '#ff5a3a', ['#ff1a2e', '#ff2233', '#ff2a38', '#ff3340']),
    'butterfly': ('#e8c8ff', '#ffc8f0', ['#ff9ae8', '#f09cff', '#e0a0ff', '#ffb0ea']),
    'snake': ('#8dff3a', '#a6ff3a', ['#7dff2e', '#8aff32', '#96ff36', '#a2ff3a']),
})
ws.GLOW.update({'storm': 0.55, 'venom': 0.55, 'butterfly': 0.5, 'snake': 0.5})
ws.NATIVE.update({'storm': '#4f9dff', 'venom': '#ff2030', 'butterfly': '#d67dff', 'snake': '#7dff2e'})


# ─────────────────────────────────────────────────────────── pill frames
def _pill_dark(cr, px, py, pw, ph, col, a=0.93):
    rounded(cr, px, py, pw, ph, ph / 2)
    cr.set_source_rgba(*rgb(col), a)
    cr.fill()


def frame_storm(cr, m):
    px, py, pw, ph = ws.pill_rect(m)
    W, cy = m['win_w'], m['win_h'] / 2
    rnd = random.Random(61)
    blue = rgb('#4f9dff')
    halo(cr, px + pw * 0.2, cy, ph * 1.8, rgb('#1d4dff'), 0.3)
    halo(cr, px + pw * 0.8, cy, ph * 1.8, rgb('#1d4dff'), 0.3)
    for side, bx in ((-1, px + 4), (1, px + pw - 4)):   # bolts shooting off both ends
        for _ in range(3):
            bolt(cr, rnd, bx, cy + rnd.uniform(-4, 4), bx + side * rnd.uniform(m['side'] * 0.5, m['side'] * 0.95),
                 cy + rnd.uniform(-m['ext'] * 1.5, m['ext'] * 1.5), 1.1, blue, 1)
    _pill_dark(cr, px, py, pw, ph, '#040a1c')
    outline = lambda: ws.jagged(cr, ws.capsule_points(px, py, pw, ph, 3), random.Random(5), 1.6, smooth=0)  # noqa
    for extra, a in ((9, 0.07), (5, 0.16), (2.5, 0.4)):
        outline()
        cr.set_line_width(1.4 + extra)
        cr.set_source_rgba(*blue, a)
        cr.stroke()
    outline()
    cr.set_line_width(1.3)
    cr.set_source_rgba(0.9, 0.96, 1, 1)
    cr.stroke()


def frame_venom(cr, m):
    px, py, pw, ph = ws.pill_rect(m)
    W, cy = m['win_w'], m['win_h'] / 2
    red, black, rim = rgb('#ff1a2e'), rgb('#0a0406'), rgb('#ff3a3a')
    halo(cr, px + pw * 0.5, cy, pw * 0.6, rgb('#7a0010'), 0.35)
    _pill_dark(cr, px, py, pw, ph, '#0b0305')
    for k, (amp, waves, ph0, wd) in enumerate(((2.2, 7, 0.0, 3.2), (2.8, 5, 2.0, 2.4), (1.6, 9, 4.0, 1.8))):
        ring = wavy_ring(px - 1, py - 1, pw + 2, ph + 2, amp, waves, ph0, 3)
        pts = [(x, y) for x, y, _nx, _ny in ring] + [(ring[0][0], ring[0][1])]
        tube(cr, pts, [wd * 1.3] * len(pts), black, rim, red, 0.1)
    rnd = random.Random(7)
    for i in range(4):   # tentacles curling out of the left end
        ang = PI + rnd.uniform(-0.9, 0.9)
        pts = []
        L = rnd.uniform(m['side'] * 0.4, m['side'] * 0.8)
        for t in range(18):
            f = t / 17
            pts.append((px + 4 + math.cos(ang) * L * f + math.sin(f * 7 + i) * 4 * f,
                        cy + math.sin(ang) * L * f * 0.5 + math.cos(f * 6 + i) * 3 * f))
        tube(cr, pts, [3.5 * (1 - t / 18) + 0.4 for t in range(18)], black, rim, red, 0.2)
    maw(cr, px + pw - 2, cy, ph / 26, black, rim, red)
    for x in (px + pw * 0.3, px + pw * 0.62, px + pw * 0.85):   # drips from the bottom
        drip(cr, x, py + ph, rnd.uniform(3, m['ext'] + 2), 1.4, red, 0.95)


def frame_butterfly(cr, m):
    px, py, pw, ph = ws.pill_rect(m)
    W, cy = m['win_w'], m['win_h'] / 2
    pink, violet, blue = rgb('#ff7ae0'), rgb('#b07cff'), rgb('#8fb8ff')
    halo(cr, px + pw * 0.2, cy, ph * 1.8, violet, 0.25)
    halo(cr, px + pw * 0.8, cy, ph * 1.8, pink, 0.25)
    _pill_dark(cr, px, py, pw, ph, '#120824')
    for amp, waves, ph0, col in ((2.0, 6, 0.0, pink), (2.4, 4, 2.2, violet)):   # glowing vines
        ring = wavy_ring(px, py, pw, ph, amp, waves, ph0, 3)
        pts = [(x, y) for x, y, _a, _b in ring] + [(ring[0][0], ring[0][1])]
        for extra, a in ((6, 0.1), (3, 0.25), (0, 0.95)):
            _poly(cr, pts)
            cr.set_line_width(1.1 + extra)
            cr.set_source_rgba(*col, a)
            cr.stroke()
    rnd = random.Random(19)
    for px_, py_, _nx, _ny in ws.capsule_points(px, py, pw, ph, 14)[::2]:   # little blossoms on the vine
        if rnd.random() < 0.4:
            flower(cr, px_, py_, rnd.uniform(2.2, 3.4), rnd.choice((pink, violet)), a=0.95, rot=rnd.uniform(0, 1))
    butterfly(cr, px - 8, cy + 3, 13, -0.35, pink, blue)
    butterfly(cr, px + pw + 10, cy - 4, 15, 0.3, violet, pink)
    butterfly(cr, px - m['side'] * 0.6, cy - 6, 6, -0.2, pink, violet, 0.8)
    butterfly(cr, px + pw + m['side'] * 0.62, cy + 7, 6, 0.4, blue, pink, 0.8)
    ws.stars(cr, (0, 0, W, m['win_h']), 26, 29, colors=('#ffb8f0', '#e0c8ff', '#ffffff'))


def _coil(px, py, pw, ph, waves, cy):
    """The snake's path round a capsule: the tail on the right cap, once
    around (bottom, left, top) and the neck rising off the top right."""
    ring = wavy_ring(px - 2, py - 2, pw + 4, ph + 4, 1.3, waves, 1.0, 2.5)
    n_top = next(i for i, p in enumerate(ring) if p[3] != -1)   # first point of the right cap
    start = n_top + 4
    body = [(x, y) for x, y, _a, _b in ring[start:] + ring[:n_top - 2]]
    ex, ey = body[-1]
    neck = [(ex + i * 2.4, ey - math.sin(i / 11 * PI * 0.5) * ph * 0.35) for i in range(1, 12)]
    return body, neck


def frame_snake(cr, m):
    px, py, pw, ph = ws.pill_rect(m)
    W, cy = m['win_w'], m['win_h'] / 2
    lime, base = rgb('#7dff2e'), rgb('#0c1a0c')
    halo(cr, px + pw / 2, cy, pw * 0.55, rgb('#1f6a10'), 0.3)
    _pill_dark(cr, px, py, pw, ph, '#040d05')
    # the body wraps the pill once and the head leaves on the right
    body, exit_pts = _coil(px, py, pw, ph, 5, cy)
    snake_body(cr, body + exit_pts, 6, base, lime, lime, head_k=1.9)
    rounded(cr, px + 3, py + 3, pw - 6, ph - 6, (ph - 6) / 2)
    cr.set_source_rgba(*lime, 0.18)
    cr.set_line_width(0.8)
    cr.stroke()


ws.FRAMES.update({'storm': frame_storm, 'venom': frame_venom, 'butterfly': frame_butterfly, 'snake': frame_snake})


# ─────────────────────────────────────────────────────────── bar skins
def bar_storm(cr, x, y, w, h, cy):
    rnd = random.Random(71)
    blue = rgb('#4f9dff')
    for fx in (0.05, 0.3, 0.7, 0.95):
        halo(cr, x + w * fx, cy, h * 2.2, rgb('#1d4dff'), 0.16)
    for side, bx in ((-1, x + 3), (1, x + w - 3)):   # bolts out of both ends
        for _ in range(3):
            bolt(cr, rnd, bx, cy + rnd.uniform(-4, 4), bx + side * rnd.uniform(22, 44),
                 cy + rnd.uniform(-y, y), 1.1, blue, 1)
    fx = x + h
    while fx < x + w - h:   # small arcs crackling over the top edge
        if rnd.random() < 0.3:
            bolt(cr, rnd, fx, y + 1, fx + rnd.uniform(-10, 10), max(0, y - rnd.uniform(3, y)), 0.8, blue, 0, a=0.8)
        fx += rnd.uniform(40, 90)
    ws._capsule(cr, x, y, w, h)
    cr.set_source_rgba(*rgb('#040a1c'), 0.93)
    cr.fill()
    outline = lambda: ws.jagged(cr, ws.capsule_points(x, y, w, h, 3), random.Random(9), 1.5, smooth=0)  # noqa
    for extra, a in ((9, 0.06), (5, 0.14), (2.5, 0.38)):
        outline()
        cr.set_line_width(1.3 + extra)
        cr.set_source_rgba(*blue, a)
        cr.stroke()
    outline()
    cr.set_line_width(1.2)
    cr.set_source_rgba(0.9, 0.96, 1, 1)
    cr.stroke()


def bar_venom(cr, x, y, w, h, cy):
    red, black, rim = rgb('#ff1a2e'), rgb('#0a0406'), rgb('#ff3a3a')
    for fx in (0.1, 0.5, 0.9):
        halo(cr, x + w * fx, cy, h * 2.4, rgb('#7a0010'), 0.25)
    ws._capsule(cr, x, y, w, h)
    cr.set_source_rgba(*rgb('#0b0305'), 0.94)
    cr.fill()
    for amp, waves, ph0, wd in ((2.0, 30, 0.0, 3.0), (2.4, 22, 2.0, 2.2)):
        ring = wavy_ring(x - 1, y - 1, w + 2, h + 2, amp, waves, ph0, 4)
        pts = [(px, py) for px, py, _a, _b in ring] + [(ring[0][0], ring[0][1])]
        tube(cr, pts, [wd * 1.3] * len(pts), black, rim, red, 0.1)
    rnd = random.Random(11)
    for side, bx in ((-1, x + 4), (1, x + w - 4)):   # tentacles reaching out of the ends
        for i in range(4):
            ang = (PI if side < 0 else 0) + rnd.uniform(-0.8, 0.8)
            L = rnd.uniform(24, 46)
            pts = [(bx + math.cos(ang) * L * t / 17 + math.sin(t / 2.4 + i) * 3 * t / 17,
                    cy + math.sin(ang) * L * t / 17 * 0.5 + math.cos(t / 2 + i) * 2 * t / 17) for t in range(18)]
            tube(cr, pts, [3.2 * (1 - t / 18) + 0.4 for t in range(18)], black, rim, red, 0.2)
    fx = x + h
    while fx < x + w - h:
        if rnd.random() < 0.4:
            drip(cr, fx, y + h, rnd.uniform(2, 7), 1.3, red, 0.9)
        fx += rnd.uniform(40, 110)


def bar_butterfly(cr, x, y, w, h, cy):
    pink, violet, blue = rgb('#ff7ae0'), rgb('#b07cff'), rgb('#8fb8ff')
    for fx, col in ((0.05, violet), (0.5, pink), (0.95, violet)):
        halo(cr, x + w * fx, cy, h * 2.2, col, 0.14)
    ws._capsule(cr, x, y, w, h)
    cr.set_source_rgba(*rgb('#120824'), 0.93)
    cr.fill()
    for amp, waves, ph0, col in ((1.8, 26, 0.0, pink), (2.2, 18, 2.2, violet)):
        ring = wavy_ring(x, y, w, h, amp, waves, ph0, 4)
        pts = [(px, py) for px, py, _a, _b in ring] + [(ring[0][0], ring[0][1])]
        for extra, a in ((5, 0.08), (2.5, 0.22), (0, 0.9)):
            _poly(cr, pts)
            cr.set_line_width(1 + extra)
            cr.set_source_rgba(*col, a)
            cr.stroke()
    rnd = random.Random(23)
    for px_, py_, _nx, _ny in ws.capsule_points(x, y, w, h, 18)[::2]:
        if rnd.random() < 0.3:
            flower(cr, px_, py_, rnd.uniform(2.2, 3.2), rnd.choice((pink, violet)), a=0.9, rot=rnd.uniform(0, 1))
    butterfly(cr, x - 6, cy + 2, 13, -0.3, pink, blue)
    butterfly(cr, x + w + 8, cy - 2, 14, 0.35, violet, pink)
    butterfly(cr, x - 30, cy - 6, 6, -0.2, pink, violet, 0.8)
    butterfly(cr, x + w + 32, cy + 6, 6, 0.4, blue, pink, 0.8)
    for _ in range(int(w / 140)):   # little butterflies over the bar
        bx = rnd.uniform(x + w * 0.1, x + w * 0.9)
        if not (x + w * 0.38 < bx < x + w * 0.62):
            butterfly(cr, bx, max(4, y - 1), rnd.uniform(3.5, 5), rnd.uniform(-0.5, 0.5),
                      rnd.choice((pink, violet, blue)), pink, 0.85)


def bar_snake(cr, x, y, w, h, cy):
    lime, base = rgb('#7dff2e'), rgb('#0c1a0c')
    for fx in (0.1, 0.5, 0.9):
        halo(cr, x + w * fx, cy, h * 2.2, rgb('#1f6a10'), 0.2)
    ws._capsule(cr, x, y, w, h)
    cr.set_source_rgba(*rgb('#040d05'), 0.93)
    cr.fill()
    body, exit_pts = _coil(x, y, w, h, 40, cy)
    snake_body(cr, body + exit_pts, 5.6, base, lime, lime, head_k=1.9)


ws.BAR_SKINS.update({'storm': bar_storm, 'venom': bar_venom, 'butterfly': bar_butterfly, 'snake': bar_snake})
ws.BAR_MARGIN.update({'storm': 48, 'venom': 56, 'butterfly': 56, 'snake': 40})


# ═══════════════════════════════════════════════ themed icons (all styles)
# fn(cr, kind, x, y, s, c): kind = 'ghost' | 'pac' | 'dot'; c = state color

def _shape(cr, kind, x, y, s):
    if kind == 'ghost':
        ws.ghost_path(cr, x, y, s * 0.95)
    else:
        ws.pac_path(cr, x, y, s * 0.55)


def _eyes(cr, kind, x, y, s, white=(1, 1, 1), pupil=(0.05, 0.08, 0.2), glow=None):
    if kind == 'ghost':
        for dx in (-s * 0.19, s * 0.19):
            if glow:
                halo(cr, x + dx, y - s * 0.1, s * 0.25, glow, 0.8)
            cr.save()
            cr.translate(x + dx, y - s * 0.1)
            cr.scale(s * 0.12, s * 0.16)
            cr.arc(0, 0, 1, 0, 2 * PI)
            cr.restore()
            cr.set_source_rgba(*white, 1)
            cr.fill()
            if pupil:
                cr.arc(x + dx + s * 0.04, y - s * 0.07, s * 0.06, 0, 2 * PI)
                cr.set_source_rgba(*pupil, 1)
                cr.fill()
    else:
        cr.arc(x + s * 0.05, y - s * 0.28, s * 0.07, 0, 2 * PI)
        cr.set_source_rgba(*(pupil or (0.08, 0.06, 0.12)), 1)
        cr.fill()


def _clip(cr, kind, x, y, s):
    cr.save()
    _shape(cr, kind, x, y, s)
    cr.clip()


def _outline(cr, kind, x, y, s, c, width=1.0, a=1.0, glow=True):
    if glow:
        for extra, al in ((3, 0.15), (1.5, 0.35)):
            _shape(cr, kind, x, y, s)
            cr.set_line_width(width + extra)
            cr.set_source_rgba(*c, al * a)
            cr.stroke()
    _shape(cr, kind, x, y, s)
    cr.set_line_width(width)
    cr.set_source_rgba(*c, a)
    cr.stroke()


def _vgrad(cr, x, y, s, top, bottom):
    g = cairo.LinearGradient(0, y - s / 2, 0, y + s / 2)
    g.add_color_stop_rgb(0, *top)
    g.add_color_stop_rgb(1, *bottom)
    return g


def icon_storm(cr, kind, x, y, s, c):
    if kind == 'dot':   # electric orb
        halo(cr, x, y, s * 0.6, c, 0.6)
        cr.arc(x, y, s * 0.26, 0, 2 * PI)
        cr.set_source_rgba(*c, 0.25)
        cr.fill_preserve()
        cr.set_line_width(1.3)
        cr.set_source_rgba(0.9, 0.97, 1, 1)
        cr.stroke()
        cr.arc(x, y, s * 0.09, 0, 2 * PI)
        cr.set_source_rgba(1, 1, 1, 1)
        cr.fill()
        return
    _shape(cr, kind, x, y, s)
    cr.set_source(_vgrad(cr, x, y, s, _mix(c, (0.05, 0.1, 0.3), 0.55), (0.02, 0.05, 0.16)))
    cr.fill()
    _clip(cr, kind, x, y, s)   # crackle inside
    rnd = random.Random(int(x))
    for _ in range(3):
        pts = bolt_points(rnd, x - s * 0.5, y + rnd.uniform(-s / 3, s / 3), x + s * 0.5, y + rnd.uniform(-s / 3, s / 3),
                          0.3, 3)
        _poly(cr, pts)
        cr.set_line_width(0.7)
        cr.set_source_rgba(*c, 0.9)
        cr.stroke()
    cr.restore()
    _outline(cr, kind, x, y, s, (0.85, 0.95, 1), 1.2)
    _eyes(cr, kind, x, y, s, (0.9, 0.97, 1), (0.1, 0.3, 0.8))


def icon_venom(cr, kind, x, y, s, c):
    if kind == 'dot':   # a blood drop, dripping
        halo(cr, x, y, s * 0.5, c, 0.45)
        g = cairo.RadialGradient(x - s * 0.08, y - s * 0.1, 0, x, y, s * 0.25)
        g.add_color_stop_rgb(0, *_mix(c, (1, 1, 1), 0.35))
        g.add_color_stop_rgb(1, *_mix(c, (0.2, 0, 0), 0.4))
        cr.arc(x, y, s * 0.24, 0, 2 * PI)
        cr.set_source(g)
        cr.fill()
        drip(cr, x, y + s * 0.18, s * 0.45, s * 0.07, c, 0.95)
        return
    _shape(cr, kind, x, y, s)
    cr.set_source(_vgrad(cr, x, y, s, _mix(c, (1, 0.8, 0.5), 0.25), _mix(c, (0.15, 0, 0), 0.55)))
    cr.fill()
    _outline(cr, kind, x, y, s, _mix(c, (1, 0.6, 0.4), 0.3), 1.0)
    _eyes(cr, kind, x, y, s, (1, 0.95, 0.6), None, glow=(1, 0.8, 0.3))
    for dx in ((-0.25, 0.1, 0.32) if kind == 'ghost' else (-0.2, 0.15)):   # drips off the bottom
        drip(cr, x + dx * s, y + s * (0.42 if kind == 'ghost' else 0.35), s * 0.3, s * 0.06, c, 0.9)


def icon_butterfly(cr, kind, x, y, s, c):
    if kind == 'dot':   # a blossom
        halo(cr, x, y, s * 0.55, c, 0.4)
        flower(cr, x, y, s * 0.32, c, (1, 1, 0.9), 1, rot=0.3)
        return
    _shape(cr, kind, x, y, s)
    cr.set_source(_vgrad(cr, x, y, s, _mix(c, (1, 1, 1), 0.3), _mix(c, (0.6, 0.3, 0.9), 0.35)))
    cr.fill()
    _clip(cr, kind, x, y, s)   # flower print
    rnd = random.Random(int(x) + 3)
    for _ in range(7):
        flower(cr, x + rnd.uniform(-s / 2, s / 2), y + rnd.uniform(-s / 2, s / 2), rnd.uniform(s * 0.08, s * 0.14),
               _mix(c, (0.75, 0.35, 0.95), 0.6), (1, 1, 1), 0.8, rot=rnd.uniform(0, 1))
    cr.restore()
    _outline(cr, kind, x, y, s, (1, 0.85, 1), 0.9)
    _eyes(cr, kind, x, y, s, (1, 1, 1), (0.35, 0.1, 0.45))


def icon_snake(cr, kind, x, y, s, c):
    if kind == 'dot':   # a snake eye with a slit pupil
        halo(cr, x, y, s * 0.55, c, 0.45)
        cr.save()
        cr.translate(x, y)
        cr.scale(s * 0.3, s * 0.2)
        cr.arc(0, 0, 1, 0, 2 * PI)
        cr.restore()
        g = cairo.RadialGradient(x, y, 0, x, y, s * 0.3)
        g.add_color_stop_rgb(0, *_mix(c, (1, 1, 0.5), 0.5))
        g.add_color_stop_rgb(1, *_mix(c, (0, 0.2, 0), 0.4))
        cr.set_source(g)
        cr.fill()
        cr.save()
        cr.translate(x, y)
        cr.scale(s * 0.05, s * 0.18)
        cr.arc(0, 0, 1, 0, 2 * PI)
        cr.restore()
        cr.set_source_rgba(0, 0, 0, 1)
        cr.fill()
        return
    _shape(cr, kind, x, y, s)
    cr.set_source(_vgrad(cr, x, y, s, _mix(c, (1, 1, 0.6), 0.2), _mix(c, (0, 0.2, 0), 0.4)))
    cr.fill()
    _clip(cr, kind, x, y, s)   # scales
    r = s * 0.13
    for row in range(-5, 6):
        for col in range(-5, 6):
            cx = x + col * r * 1.6 + (row % 2) * r * 0.8
            cy = y + row * r * 0.9
            cr.new_path()
            cr.arc(cx, cy, r, 0, PI)
            cr.set_line_width(0.6)
            cr.set_source_rgba(0.02, 0.12, 0.02, 0.55)
            cr.stroke()
    cr.restore()
    _outline(cr, kind, x, y, s, _mix(c, (1, 1, 0.6), 0.3), 0.9)
    _eyes(cr, kind, x, y, s, (0.1, 0.12, 0.05), None)


def icon_fire(cr, kind, x, y, s, c):
    if kind == 'dot':   # a small flame
        halo(cr, x, y, s * 0.55, c, 0.5)
        cr.new_path()
        cr.move_to(x, y - s * 0.38)
        cr.curve_to(x + s * 0.2, y - s * 0.1, x + s * 0.26, y + s * 0.2, x, y + s * 0.26)
        cr.curve_to(x - s * 0.26, y + s * 0.2, x - s * 0.2, y - s * 0.1, x, y - s * 0.38)
        cr.close_path()
        g = cairo.LinearGradient(0, y - s * 0.4, 0, y + s * 0.26)
        g.add_color_stop_rgb(0, *rgb('#ffe28a'))
        g.add_color_stop_rgb(1, *c)
        cr.set_source(g)
        cr.fill()
        return
    _shape(cr, kind, x, y, s)
    cr.set_source(_vgrad(cr, x, y, s, rgb('#ffe28a'), _mix(c, (0.6, 0.05, 0), 0.45)))
    cr.fill()
    _outline(cr, kind, x, y, s, rgb('#ffd060'), 0.9)
    _eyes(cr, kind, x, y, s, (1, 1, 0.9), (0.4, 0.05, 0))


def icon_lava(cr, kind, x, y, s, c):
    if kind == 'dot':   # an ember: dark crust, hot core
        halo(cr, x, y, s * 0.55, c, 0.5)
        g = cairo.RadialGradient(x, y, 0, x, y, s * 0.25)
        g.add_color_stop_rgb(0, *rgb('#ffe070'))
        g.add_color_stop_rgb(0.55, *c)
        g.add_color_stop_rgb(1, *rgb('#2a0e06'))
        cr.arc(x, y, s * 0.25, 0, 2 * PI)
        cr.set_source(g)
        cr.fill()
        return
    _shape(cr, kind, x, y, s)
    cr.set_source_rgb(*rgb('#2a140c'))
    cr.fill()
    _clip(cr, kind, x, y, s)   # molten cracks
    rnd = random.Random(int(x) + 5)
    for _ in range(4):
        pts = bolt_points(rnd, x + rnd.uniform(-s / 2, s / 2), y - s / 2, x + rnd.uniform(-s / 2, s / 2), y + s / 2,
                          0.25, 3)
        for lw, a, col in ((2.4, 0.35, c), (0.9, 1, rgb('#ffd040'))):
            _poly(cr, pts)
            cr.set_line_width(lw)
            cr.set_source_rgba(*col, a)
            cr.stroke()
    cr.restore()
    _outline(cr, kind, x, y, s, c, 1.0)
    _eyes(cr, kind, x, y, s, (1, 0.85, 0.4), (0.3, 0.05, 0))


def icon_nature(cr, kind, x, y, s, c):
    if kind == 'dot':   # a small leaf
        halo(cr, x, y, s * 0.5, c, 0.4)
        ws.leaf(cr, x - s * 0.25, y + s * 0.12, s * 0.55, -0.5, c)
        return
    _shape(cr, kind, x, y, s)
    cr.set_source(_vgrad(cr, x, y, s, _mix(c, (1, 1, 1), 0.25), _mix(c, (0, 0.2, 0.05), 0.45)))
    cr.fill()
    _clip(cr, kind, x, y, s)   # leaf veins
    cr.move_to(x - s / 2, y + s / 2)
    cr.line_to(x + s / 2, y - s / 2)
    for k in range(-3, 4):
        bx, by = x + k * s * 0.12, y - k * s * 0.12
        cr.move_to(bx, by)
        cr.line_to(bx + s * 0.18, by + s * 0.05)
        cr.move_to(bx, by)
        cr.line_to(bx - s * 0.05, by - s * 0.18)
    cr.set_line_width(0.7)
    cr.set_source_rgba(0.02, 0.2, 0.05, 0.45)
    cr.stroke()
    cr.restore()
    _outline(cr, kind, x, y, s, _mix(c, (1, 1, 1), 0.3), 0.8)
    _eyes(cr, kind, x, y, s)


def icon_liquid(cr, kind, x, y, s, c):
    if kind == 'dot':   # a bubble
        cr.arc(x, y, s * 0.24, 0, 2 * PI)
        g = cairo.RadialGradient(x - s * 0.08, y - s * 0.08, 0, x, y, s * 0.24)
        g.add_color_stop_rgba(0, 1, 1, 1, 0.35)
        g.add_color_stop_rgba(1, *c, 0.85)
        cr.set_source(g)
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.6)
        cr.set_line_width(0.8)
        cr.stroke()
        cr.arc(x - s * 0.09, y - s * 0.09, s * 0.06, 0, 2 * PI)
        cr.set_source_rgba(1, 1, 1, 0.9)
        cr.fill()
        return
    _shape(cr, kind, x, y, s)
    cr.set_source(_vgrad(cr, x, y, s, _mix(c, (1, 1, 1), 0.35), _mix(c, (0.05, 0.1, 0.4), 0.3)))
    cr.fill()
    _clip(cr, kind, x, y, s)   # glossy highlight
    cr.save()
    cr.translate(x - s * 0.15, y - s * 0.3)
    cr.scale(s * 0.35, s * 0.15)
    cr.arc(0, 0, 1, 0, 2 * PI)
    cr.restore()
    cr.set_source_rgba(1, 1, 1, 0.45)
    cr.fill()
    cr.restore()
    _eyes(cr, kind, x, y, s)


def icon_hud(cr, kind, x, y, s, c):
    if kind == 'dot':   # a reticle
        cr.arc(x, y, s * 0.2, 0, 2 * PI)
        cr.set_line_width(1)
        cr.set_source_rgba(*c, 0.95)
        cr.stroke()
        for a0 in range(4):
            ang = a0 * PI / 2
            cr.move_to(x + math.cos(ang) * s * 0.26, y + math.sin(ang) * s * 0.26)
            cr.line_to(x + math.cos(ang) * s * 0.38, y + math.sin(ang) * s * 0.38)
        cr.stroke()
        cr.arc(x, y, s * 0.05, 0, 2 * PI)
        cr.fill()
        return
    _clip(cr, kind, x, y, s)   # scanline fill
    for yy in range(int(y - s), int(y + s), 2):
        cr.rectangle(x - s, yy, 2 * s, 1)
    cr.set_source_rgba(*c, 0.55)
    cr.fill()
    cr.restore()
    _outline(cr, kind, x, y, s, c, 1.2)
    _eyes(cr, kind, x, y, s, (0.85, 0.95, 1), (0.05, 0.2, 0.5))


def icon_cyber(cr, kind, x, y, s, c):
    if kind == 'dot':   # a diamond
        halo(cr, x, y, s * 0.5, c, 0.5)
        _poly(cr, [(x, y - s * 0.28), (x + s * 0.2, y), (x, y + s * 0.28), (x - s * 0.2, y)], True)
        cr.set_source_rgba(*c, 1)
        cr.fill()
        return
    for dx, col in ((-1.6, rgb('#ff2bd6')), (1.6, rgb('#19e6ff'))):   # chromatic glitch
        _shape(cr, kind, x + dx, y, s)
        cr.set_source_rgba(*col, 0.6)
        cr.fill()
    _shape(cr, kind, x, y, s)
    cr.set_source_rgba(*_mix(c, (1, 1, 1), 0.25), 1)
    cr.fill()
    _clip(cr, kind, x, y, s)
    for yy in (y - s * 0.15, y + s * 0.2):   # glitch slices
        cr.rectangle(x - s, yy, 2 * s, s * 0.06)
    cr.set_source_rgba(0, 0, 0, 0.35)
    cr.fill()
    cr.restore()
    _eyes(cr, kind, x, y, s)


def icon_glass(cr, kind, x, y, s, c):
    if kind == 'dot':   # a glass bead
        cr.arc(x, y, s * 0.22, 0, 2 * PI)
        cr.set_source_rgba(*c, 0.45)
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.8)
        cr.set_line_width(0.9)
        cr.stroke()
        cr.arc(x - s * 0.07, y - s * 0.08, s * 0.05, 0, 2 * PI)
        cr.set_source_rgba(1, 1, 1, 0.95)
        cr.fill()
        return
    _shape(cr, kind, x, y, s)
    cr.set_source_rgba(*c, 0.45)
    cr.fill()
    _clip(cr, kind, x, y, s)
    g = cairo.LinearGradient(x - s / 2, y - s / 2, x + s / 2, y + s / 2)
    g.add_color_stop_rgba(0, 1, 1, 1, 0.55)
    g.add_color_stop_rgba(0.5, 1, 1, 1, 0.05)
    g.add_color_stop_rgba(1, 1, 1, 1, 0.2)
    cr.set_source(g)
    cr.paint()
    cr.restore()
    _outline(cr, kind, x, y, s, (1, 1, 1), 1.0, 0.9)
    _eyes(cr, kind, x, y, s)


def icon_crystal(cr, kind, x, y, s, c):
    if kind == 'dot':   # a crystal
        _poly(cr, [(x, y - s * 0.3), (x + s * 0.17, y - s * 0.05), (x, y + s * 0.3), (x - s * 0.17, y - s * 0.05)],
              True)
        cr.set_source_rgba(*_mix(c, (1, 1, 1), 0.3), 0.9)
        cr.fill_preserve()
        cr.set_source_rgba(1, 1, 1, 0.9)
        cr.set_line_width(0.7)
        cr.stroke()
        ws.sparkle(cr, x + s * 0.12, y - s * 0.2, s * 0.12, (1, 1, 1), 0.9)
        return
    _shape(cr, kind, x, y, s)
    cr.set_source_rgba(*c, 0.85)
    cr.fill()
    _clip(cr, kind, x, y, s)   # facets
    rnd = random.Random(int(x) + 9)
    for _ in range(6):
        _poly(cr, [(x + rnd.uniform(-s, s) / 2, y + rnd.uniform(-s, s) / 2) for _k in range(3)], True)
        cr.set_source_rgba(1, 1, 1, rnd.uniform(0.08, 0.35))
        cr.fill()
    cr.restore()
    _outline(cr, kind, x, y, s, (1, 1, 1), 0.9)
    _eyes(cr, kind, x, y, s)


def icon_neon(cr, kind, x, y, s, c):
    if kind == 'dot':   # a neon ring
        for lw, a in ((5, 0.15), (2.5, 0.4), (1.2, 1)):
            cr.arc(x, y, s * 0.2, 0, 2 * PI)
            cr.set_line_width(lw)
            cr.set_source_rgba(*c, a)
            cr.stroke()
        return
    _shape(cr, kind, x, y, s)
    cr.set_source_rgba(*c, 0.15)
    cr.fill()
    for lw, a in ((6, 0.12), (3, 0.3)):   # the tube
        _shape(cr, kind, x, y, s)
        cr.set_line_width(lw)
        cr.set_source_rgba(*c, a)
        cr.stroke()
    _shape(cr, kind, x, y, s)
    cr.set_line_width(1.6)
    cr.set_source_rgba(*_mix(c, (1, 1, 1), 0.5), 1)
    cr.stroke()
    _eyes(cr, kind, x, y, s, _mix(c, (1, 1, 1), 0.6), None)


def icon_holo(cr, kind, x, y, s, c):
    if kind == 'dot':   # a tiny ringed planet
        g = cairo.RadialGradient(x - s * 0.08, y - s * 0.08, 0, x, y, s * 0.2)
        g.add_color_stop_rgb(0, *_mix(c, (1, 1, 1), 0.5))
        g.add_color_stop_rgb(1, *_mix(c, (0.2, 0.1, 0.4), 0.5))
        cr.arc(x, y, s * 0.18, 0, 2 * PI)
        cr.set_source(g)
        cr.fill()
        cr.save()
        cr.translate(x, y)
        cr.rotate(-0.4)
        cr.scale(s * 0.34, s * 0.09)
        cr.arc(0, 0, 1, 0, 2 * PI)
        cr.restore()
        cr.set_line_width(0.8)
        cr.set_source_rgba(1, 1, 1, 0.75)
        cr.stroke()
        return
    _shape(cr, kind, x, y, s)
    g = cairo.LinearGradient(x - s / 2, y - s / 2, x + s / 2, y + s / 2)
    for t, col in ((0, '#8fe6ff'), (0.35, '#ffb8f0'), (0.7, '#c77dff'), (1, '#6aa8ff')):
        g.add_color_stop_rgb(t, *_mix(rgb(col), c, 0.35))
    cr.set_source(g)
    cr.fill()
    _clip(cr, kind, x, y, s)
    cr.rectangle(x - s, y - s * 0.35, 2 * s, s * 0.12)   # a sheen band
    cr.set_source_rgba(1, 1, 1, 0.3)
    cr.fill()
    cr.restore()
    _outline(cr, kind, x, y, s, (1, 1, 1), 0.8, 0.8)
    _eyes(cr, kind, x, y, s)


ws.ICON_PAINTERS.update({
    'storm': icon_storm, 'venom': icon_venom, 'butterfly': icon_butterfly, 'snake': icon_snake,
    'fire': icon_fire, 'lava': icon_lava, 'nature': icon_nature, 'liquid': icon_liquid, 'hud': icon_hud,
    'cyber': icon_cyber, 'glass': icon_glass, 'crystal': icon_crystal, 'neon': icon_neon, 'holo': icon_holo,
})
