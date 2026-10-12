# =============================================================
# Author:  TechOGR
# Repo:    https://github.com/TechOGR/bspwm_dotfiles_arch
#
# wsfour - the fourth set of styles, twelve neon scenes: Halloween,
# Desert, Neo Tokyo, Abyss, Enchanted Forest, Cosmos, Samurai,
# Steampunk, Glacier, Witchcraft, Golden Dragon and Graffiti. The
# objects of each scene (pumpkins, bats, cacti, a bull skull, torii and
# neon kanji, jellyfish and tentacles, mushrooms and fireflies, ringed
# planets and an astronaut, a katana and sakura, brass gears and an
# airship, ice crystals and a wolf, a raven and a spellbook, a golden
# dragon among clouds, paint splats and crowns) shared by the workspace
# pill, the bar skin and the icons (here), the lock card and the window
# frames (lib/wscard.py) and the window backgrounds (lib/wsback.py).
# Registered into lib/wspill.py when it is imported.
#
# Copyright (C) 2021-2026 TechOGR <https://github.com/TechOGR>
# Licensed under GPL-3.0 license
# =============================================================

import math
import random

import cairo

import wspill as ws
import wsthree as w3
from wspill import PI, rgb, rounded, halo

TAU = 2 * PI


# ═══════════════════════════════════════════════════════════ helpers
def _mix(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def _poly(cr, pts, close=False):
    cr.new_path()
    for i, p in enumerate(pts):
        (cr.move_to if i == 0 else cr.line_to)(p[0], p[1])
    if close:
        cr.close_path()


def _curve(cr, pts, close=False):
    """A smooth path through the points (Catmull-Rom)."""
    n = len(pts)
    cr.new_path()
    if n < 3:
        _poly(cr, pts, close)
        return
    cr.move_to(pts[0][0], pts[0][1])
    for i in range(n if close else n - 1):
        p0 = pts[(i - 1) % n] if (close or i > 0) else pts[0]
        p1, p2 = pts[i], pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if (close or i + 2 < n) else pts[-1]
        cr.curve_to(p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6,
                    p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6, p2[0], p2[1])
    if close:
        cr.close_path()


def neon(cr, path, c, width=1.4, a=1.0, core=0.55, layers=((7, 0.07), (3.6, 0.18), (1.6, 0.42))):
    """A glowing tube along path() with a paler core (neon sign)."""
    for extra, al in layers:
        path()
        cr.set_line_width(width + extra)
        cr.set_source_rgba(*c, al * a)
        cr.stroke()
    path()
    cr.set_line_width(width)
    cr.set_source_rgba(*_mix(c, (1, 1, 1), core), a)
    cr.stroke()


def _vgrad(y0, y1, top, bottom, a=1.0):
    g = cairo.LinearGradient(0, y0, 0, y1)
    g.add_color_stop_rgba(0, *top, a)
    g.add_color_stop_rgba(1, *bottom, a)
    return g


def _radial(x, y, r, inner, outer, a_in=1.0, a_out=1.0, fx=0.0, fy=0.0):
    g = cairo.RadialGradient(x + fx * r, y + fy * r, 0, x, y, r)
    g.add_color_stop_rgba(0, *inner, a_in)
    g.add_color_stop_rgba(1, *outer, a_out)
    return g


def _ellipse(cr, x, y, rx, ry, rot=0.0):
    cr.save()
    cr.translate(x, y)
    cr.rotate(rot)
    cr.scale(max(rx, 0.01), max(ry, 0.01))
    cr.new_sub_path()
    cr.arc(0, 0, 1, 0, TAU)
    cr.restore()


def flame(cr, x, y, h, w, c, a=1.0, lean=0.0):
    """A candle / wisp flame standing on (x, y), pointing up."""
    halo(cr, x, y - h * 0.45, h * 1.4, c, 0.35 * a)
    cr.new_path()
    cr.move_to(x, y)
    cr.curve_to(x - w, y - h * 0.15, x - w * 0.8 + lean * h, y - h * 0.65, x + lean * h, y - h)
    cr.curve_to(x + w * 0.8 + lean * h, y - h * 0.65, x + w, y - h * 0.15, x, y)
    cr.close_path()
    g = cairo.RadialGradient(x, y - h * 0.25, 0, x, y - h * 0.35, h * 0.8)
    g.add_color_stop_rgba(0, 1, 1, 0.92, a)
    g.add_color_stop_rgba(0.35, *_mix(c, (1, 1, 0.8), 0.45), a)
    g.add_color_stop_rgba(1, *c, 0.15 * a)
    cr.set_source(g)
    cr.fill()


def _sample(cr, step=4.0):
    """Points every ~step px along the current path (flattened)."""
    pts = []
    for kind, p in cr.copy_path_flat():
        if kind in (cairo.PATH_MOVE_TO, cairo.PATH_LINE_TO):
            if pts and kind == cairo.PATH_LINE_TO:
                (ax, ay) = pts[-1]
                L = math.hypot(p[0] - ax, p[1] - ay)
                for k in range(1, int(L / step)):
                    pts.append((ax + (p[0] - ax) * k * step / L, ay + (p[1] - ay) * k * step / L))
            pts.append((p[0], p[1]))
    cr.new_path()
    return pts


# ═══════════════════════════════════════════════════════════ Halloween
def pumpkin(cr, x, y, r, a=1.0, face=True, lit=1.0, glow=True):
    """A jack-o'-lantern: five ribs, a curled stem and a carved face lit
    from inside."""
    orange, dark, light = rgb('#ff7a1a'), rgb('#7a2604'), rgb('#ffb45a')
    if glow:
        halo(cr, x, y, r * 2.4, orange, 0.32 * a * lit)
    for dx, rx, k in ((-0.62, 0.48, 0.55), (0.62, 0.48, 0.55), (-0.3, 0.5, 0.8), (0.3, 0.5, 0.8), (0, 0.46, 1.0)):
        _ellipse(cr, x + dx * r, y, rx * r, 0.86 * r)
        cr.set_source(_radial(x + dx * r, y - r * 0.25, r * 0.95, _mix(light, orange, 1 - k * 0.6),
                              _mix(dark, orange, 0.25 * k), a, a))
        cr.fill_preserve()
        cr.set_source_rgba(*dark, 0.55 * a)
        cr.set_line_width(max(0.5, r * 0.06))
        cr.stroke()
    cr.new_path()   # the stem
    cr.move_to(x - r * 0.1, y - r * 0.74)
    cr.curve_to(x - r * 0.12, y - r * 1.0, x + r * 0.05, y - r * 1.15, x + r * 0.28, y - r * 1.12)
    cr.line_to(x + r * 0.25, y - r * 0.98)
    cr.curve_to(x + r * 0.1, y - r * 0.98, x + r * 0.08, y - r * 0.9, x + r * 0.1, y - r * 0.74)
    cr.close_path()
    cr.set_source_rgba(*rgb('#4a6a1c'), a)
    cr.fill()
    if not face:
        return
    fire = rgb('#ffe066')
    halo(cr, x, y + r * 0.05, r * 0.9, fire, 0.45 * a * lit)
    for sx in (-1, 1):   # triangle eyes
        _poly(cr, [(x + sx * r * 0.52, y - r * 0.06), (x + sx * r * 0.14, y - r * 0.06),
                   (x + sx * r * 0.34, y - r * 0.42)], True)
        cr.set_source_rgba(*fire, a * (0.6 + 0.4 * lit))
        cr.fill()
    _poly(cr, [(x - r * 0.08, y + r * 0.1), (x + r * 0.08, y + r * 0.1), (x, y - r * 0.04)], True)
    cr.fill()
    pts = [(x - r * 0.6, y + r * 0.22)]   # the jagged grin
    for i in range(1, 8):
        pts.append((x - r * 0.6 + i * r * 0.15, y + r * (0.22 if i % 2 else 0.36) + r * 0.12 * math.sin(i / 7 * PI)))
    pts += [(x + r * 0.55, y + r * 0.3), (x + r * 0.3, y + r * 0.62), (x, y + r * 0.7), (x - r * 0.3, y + r * 0.62)]
    _poly(cr, pts, True)
    cr.set_source_rgba(*fire, a * (0.6 + 0.4 * lit))
    cr.fill()


def bat(cr, x, y, s, angle=0.0, flap=0.6, c=None, rim=None, eye=None, a=1.0):
    """A bat seen from the front: scalloped wings (flap 0 down - 1 up),
    pointed ears, glowing eyes."""
    c = c or rgb('#140a1c')
    rim = rim or rgb('#b05cff')
    eye = eye or rgb('#ff8a2a')
    cr.save()
    cr.translate(x, y)
    cr.rotate(angle)
    cr.scale(s, s)
    up = 0.75 - 1.05 * flap

    def wing(sx):
        cr.move_to(0.08 * sx, -0.1)
        cr.curve_to(0.35 * sx, -0.3 + up * 0.3, 0.7 * sx, -0.42 + up * 0.6, 1.0 * sx, -0.3 + up)
        tips = [(0.82, 0.02), (0.62, -0.06), (0.42, 0.1), (0.22, 0.02), (0.1, 0.16)]
        px_, py_ = 1.0, -0.3 + up
        for tx, ty in tips:
            ty2 = ty + up * (1 - tx) * 0.2 + up * tx * 0.55
            cr.curve_to(px_ * sx - 0.05 * sx, py_ + 0.12, tx * sx + 0.06 * sx, ty2 + 0.1, tx * sx, ty2)
            px_, py_ = tx, ty2
        cr.close_path()

    cr.new_path()
    wing(-1)
    wing(1)
    _ellipse(cr, 0, 0.02, 0.16, 0.26)
    _ellipse(cr, 0, -0.26, 0.13, 0.12)
    cr.move_to(-0.11, -0.3)   # ears
    cr.line_to(-0.13, -0.5)
    cr.line_to(-0.03, -0.34)
    cr.close_path()
    cr.move_to(0.11, -0.3)
    cr.line_to(0.13, -0.5)
    cr.line_to(0.03, -0.34)
    cr.close_path()
    cr.restore()   # the path stays where it was built, in the outer space
    path = cr.copy_path()
    for extra, al in ((2.2, 0.18), (0.9, 0.5)):   # moonlit rim
        cr.new_path()
        cr.append_path(path)
        cr.set_line_width(extra)
        cr.set_source_rgba(*rim, al * a)
        cr.stroke()
    cr.new_path()
    cr.append_path(path)
    cr.set_source_rgba(*c, a)
    cr.fill()
    for sx in (-1, 1):
        ex = x + (sx * 0.05 * math.cos(angle) - (-0.27) * math.sin(angle)) * s
        ey = y + (sx * 0.05 * math.sin(angle) + (-0.27) * math.cos(angle)) * s
        cr.arc(ex, ey, max(0.45, s * 0.035), 0, TAU)
        cr.set_source_rgba(*eye, a)
        cr.fill()


def skull(cr, x, y, s, bone=None, shade=None, eyes=None, a=1.0):
    """A cartoon skull (s = its width); eyes: a color the sockets glow in."""
    bone = bone or rgb('#efe4cc')
    shade = shade or rgb('#8a7a66')
    cr.new_path()
    cr.arc(x, y - s * 0.08, s * 0.5, PI * 0.82, PI * 2.18)
    cr.line_to(x + s * 0.3, y + s * 0.3)
    cr.curve_to(x + s * 0.3, y + s * 0.5, x - s * 0.3, y + s * 0.5, x - s * 0.3, y + s * 0.3)
    cr.close_path()
    cr.set_source(_radial(x - s * 0.12, y - s * 0.25, s * 0.85, bone, shade, a, a))
    cr.fill()
    for sx in (-1, 1):
        _ellipse(cr, x + sx * s * 0.19, y - s * 0.02, s * 0.13, s * 0.15)
        cr.set_source_rgba(0.06, 0.03, 0.05, a)
        cr.fill()
        if eyes:
            halo(cr, x + sx * s * 0.19, y - s * 0.02, s * 0.16, eyes, 0.9 * a)
    _poly(cr, [(x - s * 0.06, y + s * 0.2), (x + s * 0.06, y + s * 0.2), (x, y + s * 0.08)], True)
    cr.set_source_rgba(0.06, 0.03, 0.05, a)
    cr.fill()
    cr.set_line_width(max(0.4, s * 0.035))
    for k in range(-2, 3):   # teeth
        cr.move_to(x + k * s * 0.09, y + s * 0.3)
        cr.line_to(x + k * s * 0.09, y + s * 0.42)
    cr.stroke()


def moon(cr, x, y, r, c, a=1.0, craters=True, glow=0.45):
    halo(cr, x, y, r * 2.6, c, glow * a)
    cr.arc(x, y, r, 0, TAU)
    cr.set_source(_radial(x, y, r, _mix(c, (1, 1, 1), 0.55), _mix(c, (0.1, 0, 0.1), 0.25), a, a, -0.3, -0.3))
    cr.fill()
    if craters:
        rnd = random.Random(int(r * 10))
        for _ in range(6):
            ang, d = rnd.uniform(0, TAU), rnd.uniform(0, r * 0.65)
            cr.arc(x + math.cos(ang) * d, y + math.sin(ang) * d, r * rnd.uniform(0.08, 0.2), 0, TAU)
            cr.set_source_rgba(*_mix(c, (0.2, 0, 0.15), 0.5), 0.22 * a)
            cr.fill()


def candle(cr, x, y, h, w, wax=None, fire=None, a=1.0, lean=0.0):
    """A wax candle standing on (x, y) with drips and a lit flame."""
    wax = wax or rgb('#efe2c6')
    fire = fire or rgb('#ffb347')
    cr.new_path()
    cr.move_to(x - w / 2, y)
    cr.line_to(x - w / 2, y - h)
    cr.curve_to(x - w / 4, y - h + w * 0.18, x + w / 4, y - h + w * 0.18, x + w / 2, y - h)
    cr.line_to(x + w / 2, y)
    cr.close_path()
    g = cairo.LinearGradient(x - w / 2, 0, x + w / 2, 0)
    g.add_color_stop_rgba(0, *_mix(wax, (1, 1, 1), 0.3), a)
    g.add_color_stop_rgba(1, *_mix(wax, (0.3, 0.2, 0.1), 0.45), a)
    cr.set_source(g)
    cr.fill()
    for dx, L in ((-0.32, 0.35), (0.2, 0.22)):   # wax drips
        w3.drip(cr, x + dx * w, y - h + w * 0.1, h * L, w * 0.16, _mix(wax, (1, 1, 1), 0.2), a)
    cr.move_to(x, y - h)
    cr.line_to(x, y - h - w * 0.3)
    cr.set_line_width(max(0.4, w * 0.12))
    cr.set_source_rgba(0.1, 0.06, 0.04, a)
    cr.stroke()
    flame(cr, x, y - h - w * 0.15, w * 1.5, w * 0.42, fire, a, lean)


def cobweb(cr, cx, cy, r, a0, a1, c, a=1.0, threads=5, rings=4):
    """A spider web in a corner: threads from (cx, cy) between angles a0
    and a1, sagging rings between them."""
    angs = [a0 + (a1 - a0) * i / (threads - 1) for i in range(threads)]
    cr.set_line_width(0.7)
    for ang in angs:
        cr.move_to(cx, cy)
        cr.line_to(cx + math.cos(ang) * r, cy + math.sin(ang) * r)
    for k in range(1, rings + 1):
        rr = r * k / (rings + 0.4)
        for i in range(threads - 1):
            p0 = (cx + math.cos(angs[i]) * rr, cy + math.sin(angs[i]) * rr)
            p1 = (cx + math.cos(angs[i + 1]) * rr, cy + math.sin(angs[i + 1]) * rr)
            mid = (angs[i] + angs[i + 1]) / 2
            sag = rr * 0.78
            cr.move_to(*p0)
            cr.curve_to(cx + math.cos(mid) * sag, cy + math.sin(mid) * sag, cx + math.cos(mid) * sag,
                        cy + math.sin(mid) * sag, *p1)
    cr.set_source_rgba(*c, 0.55 * a)
    cr.stroke()


def dead_tree(cr, x, y, L, ang, width, rnd, c, depth=5, a=1.0):
    """A bare, twisted tree (or branch) growing from (x, y) along ang."""
    pts, px_, py_, d = [], x, y, ang
    for i in range(6):
        pts.append((px_, py_))
        d += rnd.uniform(-0.22, 0.22)
        px_ += math.cos(d) * L / 5
        py_ += math.sin(d) * L / 5
    branch(cr, pts, width, width * 0.55, c, a)
    if depth <= 0 or width < 0.8:
        return
    for k in range(rnd.choice((2, 2, 3))):
        i = rnd.randrange(2, 6)
        bx, by = pts[i]
        dead_tree(cr, bx, by, L * rnd.uniform(0.45, 0.7), d + rnd.choice((-1, 1)) * rnd.uniform(0.35, 0.9),
                  width * 0.55, rnd, c, depth - 1, a)


def tombstone(cr, x, y, w, h, c, rim, cross=False, a=1.0):
    cr.new_path()
    if cross:
        bw = w * 0.28
        cr.rectangle(x - bw / 2, y - h, bw, h)
        cr.rectangle(x - w / 2, y - h * 0.72, w, bw)
    else:
        cr.move_to(x - w / 2, y)
        cr.line_to(x - w / 2, y - h + w / 2)
        cr.arc(x, y - h + w / 2, w / 2, PI, 2 * PI)
        cr.line_to(x + w / 2, y)
        cr.close_path()
    path = cr.copy_path()
    cr.set_source_rgba(*c, a)
    cr.fill()
    cr.append_path(path)
    cr.set_line_width(0.8)
    cr.set_source_rgba(*rim, 0.55 * a)
    cr.stroke()


# ═══════════════════════════════════════════════════════════ Desert
def cactus(cr, x, y, h, a=1.0, arms=((-1, 0.45, 0.32), (1, 0.62, 0.26)), rim=None):
    """A saguaro standing on (x, y): trunk, arms, ribs and spines, lit from
    the setting sun on one side."""
    green, dark = rgb('#5fae45'), rgb('#1f4a1a')
    rim = rim or rgb('#ffb04a')
    w = h * 0.2
    cr.save()
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    cr.new_path()
    cr.move_to(x, y)
    cr.line_to(x, y - h + w / 2)
    for side, at, L in arms:
        ay = y - h * at
        cr.move_to(x, ay)
        cr.line_to(x + side * w * 1.3, ay)
        cr.line_to(x + side * w * 1.3, ay - h * L)
    path = cr.copy_path()
    cr.set_line_width(w + 2.2)   # warm rim from the sun
    cr.set_source_rgba(*rim, 0.55 * a)
    cr.stroke()
    cr.append_path(path)
    cr.set_line_width(w)
    g = cairo.LinearGradient(x - h * 0.4, 0, x + h * 0.4, 0)
    g.add_color_stop_rgba(0, *_mix(green, (1, 0.9, 0.5), 0.35), a)
    g.add_color_stop_rgba(0.5, *green, a)
    g.add_color_stop_rgba(1, *dark, a)
    cr.set_source(g)
    cr.stroke()
    cr.set_line_width(max(0.4, w * 0.1))   # ribs
    for dx in (-0.22, 0.22):
        cr.move_to(x + dx * w, y)
        cr.line_to(x + dx * w, y - h + w * 0.6)
    cr.set_source_rgba(*dark, 0.6 * a)
    cr.stroke()
    rnd = random.Random(int(h * 7 + x))
    for _ in range(int(h / 3)):   # spines
        cr.arc(x + rnd.uniform(-w / 2, w / 2), y - rnd.uniform(0, h * 0.95), max(0.3, w * 0.05), 0, TAU)
        cr.set_source_rgba(1, 0.95, 0.8, 0.55 * a)
        cr.fill()
    cr.restore()


def bull_skull(cr, x, y, s, bone=None, shade=None, glow=None, a=1.0):
    """A longhorn skull, the snout down (s = its height)."""
    bone = bone or rgb('#f2e4c8')
    shade = shade or rgb('#9a7a58')
    if glow:
        halo(cr, x, y, s * 1.3, glow, 0.35 * a)
    for sx in (-1, 1):   # horns
        cr.new_path()
        cr.move_to(x + sx * s * 0.26, y - s * 0.28)
        cr.curve_to(x + sx * s * 0.6, y - s * 0.4, x + sx * s * 0.95, y - s * 0.35, x + sx * s * 1.0, y - s * 0.72)
        cr.curve_to(x + sx * s * 0.88, y - s * 0.48, x + sx * s * 0.6, y - s * 0.24, x + sx * s * 0.24, y - s * 0.1)
        cr.close_path()
        g = cairo.LinearGradient(x, 0, x + sx * s, 0)
        g.add_color_stop_rgba(0, *bone, a)
        g.add_color_stop_rgba(1, *_mix(shade, (0.2, 0.1, 0.05), 0.4), a)
        cr.set_source(g)
        cr.fill()
    pts = [(-0.3, -0.34), (0.3, -0.34), (0.27, 0.02), (0.15, 0.4), (0.1, 0.6), (-0.1, 0.6), (-0.15, 0.4), (-0.27, 0.02)]
    _curve(cr, [(x + px * s, y + py * s) for px, py in pts], True)
    cr.set_source(_radial(x - s * 0.08, y - s * 0.2, s * 0.8, bone, shade, a, a))
    cr.fill()
    for sx in (-1, 1):
        _ellipse(cr, x + sx * s * 0.14, y - s * 0.08, s * 0.08, s * 0.11, sx * 0.4)
        cr.set_source_rgba(0.1, 0.05, 0.02, a)
        cr.fill()
        _ellipse(cr, x + sx * s * 0.05, y + s * 0.5, s * 0.025, s * 0.05)
        cr.fill()
    cr.move_to(x, y - s * 0.3)   # a crack
    cr.line_to(x + s * 0.04, y - s * 0.18)
    cr.line_to(x - s * 0.02, y - s * 0.05)
    cr.set_line_width(max(0.4, s * 0.025))
    cr.set_source_rgba(*shade, 0.8 * a)
    cr.stroke()


def sun_disc(cr, x, y, r, a=1.0, bands=True):
    """The setting sun: a hot disc with haze bands across its lower half."""
    gold, red = rgb('#ffd25a'), rgb('#ff5a1a')
    halo(cr, x, y, r * 3.2, rgb('#ff8a1a'), 0.35 * a)
    cr.push_group()
    cr.arc(x, y, r, 0, TAU)
    cr.set_source(_vgrad(y - r, y + r, _mix(gold, (1, 1, 1), 0.3), red, a))
    cr.fill()
    if bands:
        cr.set_operator(cairo.OPERATOR_DEST_OUT)
        for k in range(4):
            by = y + r * (0.15 + k * 0.22)
            cr.rectangle(x - r, by, 2 * r, r * (0.04 + k * 0.03))
        cr.set_source_rgba(0, 0, 0, 1)
        cr.fill()
    cr.pop_group_to_source()
    cr.paint()


def tumbleweed(cr, x, y, r, c, a=1.0, seed=1):
    rnd = random.Random(seed)
    cr.set_line_width(max(0.4, r * 0.06))
    for _ in range(14):
        a0 = rnd.uniform(0, TAU)
        rr = rnd.uniform(0.4, 1.0) * r
        cr.new_sub_path()
        cr.arc(x + rnd.uniform(-0.3, 0.3) * r, y + rnd.uniform(-0.3, 0.3) * r, rr, a0, a0 + rnd.uniform(1.5, 4))
    cr.set_source_rgba(*c, 0.85 * a)
    cr.stroke()


def plank(cr, x, y, w, h, a=1.0, seed=3, nails=True):
    """A weathered wooden board: grain, knots, nails."""
    wood, dark = rgb('#6a3a1c'), rgb('#2a1408')
    rnd = random.Random(seed)
    rounded(cr, x, y, w, h, min(h / 2, 4))
    cr.set_source(_vgrad(y, y + h, _mix(wood, (1, 0.8, 0.5), 0.15), dark, a))
    cr.fill()
    cr.save()
    rounded(cr, x, y, w, h, min(h / 2, 4))
    cr.clip()
    cr.set_line_width(0.6)
    for k in range(int(h / 3) + 1):   # grain
        gy = y + 1.5 + k * 3 + rnd.uniform(-0.5, 0.5)
        cr.move_to(x, gy)
        for i in range(1, int(w / 10) + 2):
            cr.line_to(x + i * 10, gy + math.sin(i * 0.7 + k) * 0.6)
    cr.set_source_rgba(*_mix(dark, (0, 0, 0), 0.3), 0.45 * a)
    cr.stroke()
    for _ in range(int(w / 70) + 1):   # knots
        _ellipse(cr, rnd.uniform(x + 6, x + w - 6), rnd.uniform(y + 2, y + h - 2), rnd.uniform(2, 4), 1.2)
        cr.set_source_rgba(0.12, 0.05, 0.02, 0.5 * a)
        cr.fill()
    cr.restore()
    if nails:
        for nx in (x + 4, x + w - 4):
            cr.arc(nx, y + h / 2, max(0.8, h * 0.12), 0, TAU)
            cr.set_source_rgba(0.55, 0.5, 0.45, a)
            cr.fill()
            cr.arc(nx - 0.3, y + h / 2 - 0.3, max(0.3, h * 0.05), 0, TAU)
            cr.set_source_rgba(1, 1, 1, 0.6 * a)
            cr.fill()


def sheriff_star(cr, x, y, r, c, a=1.0, glow=True):
    if glow:
        halo(cr, x, y, r * 2.0, c, 0.45 * a)
    cr.new_path()
    for i in range(12):
        ang = -PI / 2 + i * PI / 6
        rr = r if i % 2 == 0 else r * 0.5
        (cr.move_to if i == 0 else cr.line_to)(x + math.cos(ang) * rr, y + math.sin(ang) * rr)
    cr.close_path()
    cr.set_source(_radial(x, y, r, _mix(c, (1, 1, 1), 0.45), _mix(c, (0.4, 0.2, 0), 0.35), a, a, -0.3, -0.3))
    cr.fill()
    for i in range(6):   # the balls on the tips
        ang = -PI / 2 + i * PI / 3
        cr.arc(x + math.cos(ang) * r, y + math.sin(ang) * r, r * 0.16, 0, TAU)
        cr.set_source_rgba(*_mix(c, (1, 1, 1), 0.3), a)
        cr.fill()
    cr.arc(x, y, r * 0.3, 0, TAU)
    cr.set_line_width(max(0.4, r * 0.08))
    cr.set_source_rgba(*_mix(c, (0.3, 0.15, 0), 0.6), a)
    cr.stroke()


def cowboy_hat(cr, x, y, s, a=1.0):
    """A cowboy hat resting on (x, y) (s = its width)."""
    felt, band = rgb('#7a4a22'), rgb('#3a1e0c')
    cr.new_path()   # the brim, curled up at both sides
    cr.move_to(x - s * 0.5, y - s * 0.12)
    cr.curve_to(x - s * 0.38, y + s * 0.02, x + s * 0.38, y + s * 0.02, x + s * 0.5, y - s * 0.12)
    cr.curve_to(x + s * 0.4, y + s * 0.1, x - s * 0.4, y + s * 0.1, x - s * 0.5, y - s * 0.12)
    cr.close_path()
    cr.set_source_rgba(*felt, a)
    cr.fill()
    cr.new_path()   # the crown, pinched on top
    cr.move_to(x - s * 0.24, y)
    cr.curve_to(x - s * 0.27, y - s * 0.3, x - s * 0.18, y - s * 0.42, x - s * 0.06, y - s * 0.36)
    cr.curve_to(x, y - s * 0.32, x, y - s * 0.32, x + s * 0.06, y - s * 0.36)
    cr.curve_to(x + s * 0.18, y - s * 0.42, x + s * 0.27, y - s * 0.3, x + s * 0.24, y)
    cr.close_path()
    cr.set_source(_vgrad(y - s * 0.4, y, _mix(felt, (1, 0.8, 0.5), 0.3), felt, a))
    cr.fill()
    cr.rectangle(x - s * 0.245, y - s * 0.1, s * 0.49, s * 0.07)
    cr.set_source_rgba(*band, a)
    cr.fill()


# ═══════════════════════════════════════════════════════════ Neo Tokyo / Samurai
# neon kanji, strokes in a unit box: 未来 (mirai, "the future") and 侍 (samurai)
KANJI = {
    'mi': [[(0.2, 0.3), (0.8, 0.3)], [(0.08, 0.52), (0.92, 0.52)], [(0.5, 0.06), (0.5, 0.97)],
           [(0.47, 0.55), (0.3, 0.75), (0.08, 0.9)], [(0.53, 0.55), (0.72, 0.75), (0.93, 0.9)]],
    'rai': [[(0.14, 0.24), (0.86, 0.24)], [(0.3, 0.32), (0.37, 0.43)], [(0.7, 0.32), (0.63, 0.43)],
            [(0.06, 0.52), (0.94, 0.52)], [(0.5, 0.05), (0.5, 0.97)],
            [(0.47, 0.55), (0.3, 0.75), (0.08, 0.9)], [(0.53, 0.55), (0.72, 0.75), (0.93, 0.9)]],
    'samurai': [[(0.3, 0.05), (0.2, 0.25), (0.06, 0.42)], [(0.2, 0.26), (0.2, 0.97)],
                [(0.42, 0.2), (0.92, 0.2)], [(0.67, 0.04), (0.67, 0.4)], [(0.36, 0.4), (0.98, 0.4)],
                [(0.34, 0.6), (0.98, 0.6)], [(0.82, 0.47), (0.82, 0.92), (0.72, 0.86)],
                [(0.5, 0.7), (0.58, 0.8)]],
}


def kanji(cr, name, x, y, size, c, width=1.4, a=1.0, glow=True):
    """A kanji written in neon tubes, (x, y) its top left corner."""
    cr.save()
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)

    def path():
        cr.new_path()
        for stroke in KANJI[name]:
            for i, (px, py) in enumerate(stroke):
                (cr.move_to if i == 0 else cr.line_to)(x + px * size, y + py * size)
    if glow:
        neon(cr, path, c, width, a)
    else:
        path()
        cr.set_line_width(width)
        cr.set_source_rgba(*c, a)
        cr.stroke()
    cr.restore()


def torii(cr, x, y, w, h, c, glow=None, a=1.0):
    """A torii gate standing on (x, y) (w = width of the top beam)."""
    cr.new_path()
    pw = w * 0.09
    for sx in (-1, 1):   # pillars, a little slanted
        cr.move_to(x + sx * w * 0.3 - pw / 2, y)
        cr.line_to(x + sx * w * 0.27 - pw / 2, y - h * 0.8)
        cr.line_to(x + sx * w * 0.27 + pw / 2, y - h * 0.8)
        cr.line_to(x + sx * w * 0.3 + pw / 2, y)
        cr.close_path()
    cr.rectangle(x - w * 0.4, y - h * 0.68, w * 0.8, h * 0.07)   # nuki
    cr.move_to(x - w * 0.5, y - h * 1.0)   # kasagi, its ends sweeping up
    cr.curve_to(x - w * 0.25, y - h * 0.86, x + w * 0.25, y - h * 0.86, x + w * 0.5, y - h * 1.0)
    cr.line_to(x + w * 0.46, y - h * 0.86)
    cr.curve_to(x + w * 0.25, y - h * 0.78, x - w * 0.25, y - h * 0.78, x - w * 0.46, y - h * 0.86)
    cr.close_path()
    cr.rectangle(x - w * 0.04, y - h * 0.82, w * 0.08, h * 0.15)   # the plaque
    path = cr.copy_path()
    if glow:
        for extra, al in ((5, 0.1), (2.5, 0.25), (1.2, 0.6)):
            cr.new_path()
            cr.append_path(path)
            cr.set_line_width(extra)
            cr.set_source_rgba(*glow, al * a)
            cr.stroke()
    cr.new_path()
    cr.append_path(path)
    cr.set_source_rgba(*c, a)
    cr.fill()


def sakura(cr, x, y, r, c=None, rot=0.0, a=1.0):
    """A cherry blossom: five notched petals and a pale heart."""
    c = c or rgb('#ff8ab8')
    for k in range(5):
        ang = rot + k * TAU / 5
        cr.save()
        cr.translate(x, y)
        cr.rotate(ang)
        cr.new_path()
        cr.move_to(0, 0)
        cr.curve_to(-r * 0.55, -r * 0.3, -r * 0.42, -r * 0.92, -r * 0.16, -r)
        cr.line_to(0, -r * 0.84)
        cr.line_to(r * 0.16, -r)
        cr.curve_to(r * 0.42, -r * 0.92, r * 0.55, -r * 0.3, 0, 0)
        cr.close_path()
        cr.restore()
        cr.set_source(_radial(x, y, r, _mix(c, (0.75, 0.1, 0.35), 0.35), _mix(c, (1, 1, 1), 0.35), a, a))
        cr.fill()
    cr.arc(x, y, r * 0.18, 0, TAU)
    cr.set_source_rgba(1, 0.92, 0.7, a)
    cr.fill()


def petal(cr, x, y, s, ang, c=None, a=1.0):
    """A single falling sakura petal."""
    c = c or rgb('#ff9ac4')
    cr.save()
    cr.translate(x, y)
    cr.rotate(ang)
    cr.new_path()
    cr.move_to(0, s * 0.5)
    cr.curve_to(-s * 0.55, s * 0.2, -s * 0.4, -s * 0.45, -s * 0.12, -s * 0.5)
    cr.line_to(0, -s * 0.36)
    cr.line_to(s * 0.12, -s * 0.5)
    cr.curve_to(s * 0.4, -s * 0.45, s * 0.55, s * 0.2, 0, s * 0.5)
    cr.close_path()
    cr.restore()
    cr.set_source_rgba(*c, a)
    cr.fill()


def branch(cr, pts, w0, w1, c, a=1.0):
    """A tapering branch through pts (w0 at the base, w1 at the tip)."""
    left, right = [], []
    n = len(pts)
    for i, (px, py) in enumerate(pts):
        ax, ay = pts[max(0, i - 1)]
        bx, by = pts[min(n - 1, i + 1)]
        L = math.hypot(bx - ax, by - ay) or 1
        nx, ny = -(by - ay) / L, (bx - ax) / L
        wd = (w0 + (w1 - w0) * i / max(1, n - 1)) / 2
        left.append((px + nx * wd, py + ny * wd))
        right.append((px - nx * wd, py - ny * wd))
    _poly(cr, left + right[::-1], True)
    cr.set_source_rgba(*c, a)
    cr.fill()


def blossom_branch(cr, x, y, L, ang, rnd, c=None, bark=None, a=1.0, n=7):
    """A sakura twig with blossoms from (x, y) towards angle ang."""
    c = c or rgb('#ff8ab8')
    bark = bark or rgb('#2a1218')
    pts, cx, cy, d = [], x, y, ang
    for i in range(10):
        pts.append((cx, cy))
        d += rnd.uniform(-0.25, 0.25)
        cx += math.cos(d) * L / 9
        cy += math.sin(d) * L / 9
    branch(cr, pts, max(1.2, L * 0.07), 0.6, bark, a)
    for i in range(n):   # blossoms along it, a twig or two
        px, py = pts[rnd.randrange(2, len(pts))]
        sakura(cr, px + rnd.uniform(-L * 0.08, L * 0.08), py + rnd.uniform(-L * 0.08, L * 0.08),
               rnd.uniform(0.07, 0.12) * L, c, rnd.uniform(0, 1.3), a)


def kitsune(cr, x, y, s, c, a=1.0, width=1.2):
    """A fox mask drawn in neon (s = its height)."""
    def path():
        cr.new_path()
        pts = [(-0.42, -0.05), (-0.46, -0.5), (-0.2, -0.24), (0, -0.28), (0.2, -0.24), (0.46, -0.5), (0.42, -0.05),
               (0.32, 0.22), (0.1, 0.48), (0, 0.52), (-0.1, 0.48), (-0.32, 0.22)]
        _curve(cr, [(x + px * s, y + py * s) for px, py in pts], True)
        for sx in (-1, 1):   # eyes
            cr.move_to(x + sx * s * 0.28, y + s * 0.0)
            cr.curve_to(x + sx * s * 0.2, y - s * 0.07, x + sx * s * 0.1, y - s * 0.04, x + sx * s * 0.08, y + s * 0.04)
            cr.curve_to(x + sx * s * 0.16, y + s * 0.06, x + sx * s * 0.24, y + s * 0.05,
                        x + sx * s * 0.28, y + s * 0.0)
        cr.move_to(x - s * 0.06, y + s * 0.38)
        cr.line_to(x + s * 0.06, y + s * 0.38)
        cr.move_to(x - s * 0.02, y - s * 0.2)   # the marking on the brow
        cr.line_to(x, y - s * 0.1)
        cr.line_to(x + s * 0.02, y - s * 0.2)
    path()
    cr.set_source_rgba(*_mix(c, (0, 0, 0), 0.7), 0.6 * a)
    cr.fill()
    cr.save()
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    neon(cr, path, c, width, a)
    cr.restore()


def skyline(cr, x0, x1, base, hmin, hmax, rnd, body=None, lights=None, a=1.0, step=(8, 22), win=1.6):
    """City blocks along base with lit windows in neon colors."""
    body = body or rgb('#0c0a24')
    lights = lights or [rgb('#ff3ab4'), rgb('#3ad8ff'), rgb('#ffd23a'), rgb('#b44dff')]
    x = x0
    while x < x1:
        bw = rnd.uniform(*step)
        bh = rnd.uniform(hmin, hmax)
        cr.rectangle(x, base - bh, bw - 1, bh)
        cr.set_source_rgba(*body, a)
        cr.fill()
        if rnd.random() < 0.3:   # an antenna
            cr.move_to(x + bw / 2, base - bh)
            cr.line_to(x + bw / 2, base - bh - rnd.uniform(3, 9))
            cr.set_line_width(0.7)
            cr.stroke()
        col = rnd.choice(lights)
        for wy in range(int(base - bh + 2), int(base - 2), int(win * 2.2)):
            for wx in range(int(x + 1.5), int(x + bw - 2), int(win * 2.2)):
                if rnd.random() < 0.38:
                    cr.rectangle(wx, wy, win, win * 0.8)
        cr.set_source_rgba(*col, 0.85 * a)
        cr.fill()
        x += bw


# ═══════════════════════════════════════════════════════════ Abyss
def jellyfish(cr, x, y, s, c, t=0.0, a=1.0, tentacles=6):
    """A glowing jellyfish, its bell centred on (x, y) (s = bell width)."""
    halo(cr, x, y, s * 1.6, c, 0.3 * a)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    for i in range(tentacles):   # trailing tentacles
        tx = x + (i / max(1, tentacles - 1) - 0.5) * s * 0.75
        cr.move_to(tx, y + s * 0.08)
        L = s * (1.1 + 0.5 * ((i * 7) % 3) / 2)
        for k in range(1, 12):
            f = k / 11
            cr.line_to(tx + math.sin(f * 7 + t * 3 + i) * s * 0.07 * f * 2, y + s * 0.08 + L * f)
    cr.set_line_width(max(0.5, s * 0.025))
    cr.set_source_rgba(*_mix(c, (1, 1, 1), 0.3), 0.6 * a)
    cr.stroke()
    for sx in (-1, 1):   # frilly oral arms
        cr.move_to(x + sx * s * 0.08, y + s * 0.05)
        for k in range(1, 10):
            f = k / 9
            cr.line_to(x + sx * s * (0.08 + math.sin(f * 9 + t * 2) * 0.06), y + s * 0.05 + s * 0.75 * f)
    cr.set_line_width(max(0.8, s * 0.07))
    cr.set_source_rgba(*c, 0.45 * a)
    cr.stroke()
    cr.new_path()   # the bell with a scalloped rim
    cr.move_to(x - s * 0.5, y + s * 0.08)
    cr.curve_to(x - s * 0.52, y - s * 0.55, x + s * 0.52, y - s * 0.55, x + s * 0.5, y + s * 0.08)
    for k in range(6, 0, -1):
        fx0 = x - s * 0.5 + s * k / 6
        cr.curve_to(fx0 - s * 0.03, y + s * 0.16, fx0 - s * 0.13, y + s * 0.16, fx0 - s / 6, y + s * 0.08)
    cr.close_path()
    path = cr.copy_path()
    cr.set_source(_radial(x, y - s * 0.2, s * 0.6, _mix(c, (1, 1, 1), 0.6), c, 0.95 * a, 0.45 * a))
    cr.fill()
    cr.append_path(path)
    cr.set_line_width(max(0.5, s * 0.03))
    cr.set_source_rgba(*_mix(c, (1, 1, 1), 0.5), 0.9 * a)
    cr.stroke()
    for k in range(-2, 3):   # radial canals in the bell
        cr.move_to(x, y - s * 0.32)
        cr.line_to(x + k * s * 0.13, y + s * 0.05)
    cr.set_line_width(max(0.3, s * 0.015))
    cr.set_source_rgba(1, 1, 1, 0.35 * a)
    cr.stroke()


def squid(cr, x, y, s, c, a=1.0, width=1.2):
    """A little squid drawn in neon (s = its height): the abyss emblem."""
    def path():
        cr.new_path()
        _curve(cr, [(x, y - s * 0.5), (x + s * 0.2, y - s * 0.22), (x + s * 0.16, y + s * 0.05),
                    (x - s * 0.16, y + s * 0.05), (x - s * 0.2, y - s * 0.22)], True)
        for k in range(-2, 3):   # curly arms
            bx = x + k * s * 0.07
            cr.move_to(bx, y + s * 0.05)
            cr.curve_to(bx + k * s * 0.05, y + s * 0.25, bx + k * s * 0.15, y + s * 0.3,
                        bx + k * s * 0.12 + (s * 0.06 if k >= 0 else -s * 0.06), y + s * 0.44)
            cr.arc(bx + k * s * 0.12 + (s * 0.03 if k >= 0 else -s * 0.03), y + s * 0.44, s * 0.03, PI, TAU)
    path()
    cr.set_source_rgba(*_mix(c, (0, 0, 0), 0.6), 0.5 * a)
    cr.fill()
    cr.save()
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    neon(cr, path, c, width, a)
    cr.restore()
    for sx in (-1, 1):
        cr.arc(x + sx * s * 0.07, y - s * 0.08, s * 0.04, 0, TAU)
        cr.set_source_rgba(1, 1, 1, a)
        cr.fill()


def bubble(cr, x, y, r, c, a=1.0):
    cr.arc(x, y, r, 0, TAU)
    cr.set_source_rgba(*c, 0.12 * a)
    cr.fill_preserve()
    cr.set_line_width(max(0.5, r * 0.18))
    cr.set_source_rgba(*_mix(c, (1, 1, 1), 0.4), 0.75 * a)
    cr.stroke()
    cr.arc(x - r * 0.35, y - r * 0.35, r * 0.28, 0, TAU)
    cr.set_source_rgba(1, 1, 1, 0.8 * a)
    cr.fill()


def coral(cr, x, y, h, c, rnd, a=1.0, depth=3, ang=-PI / 2, w=None):
    """A branching coral growing from (x, y), glowing at the tips."""
    w = w or max(1.0, h * 0.12)
    ex, ey = x + math.cos(ang) * h * 0.45, y + math.sin(ang) * h * 0.45
    cr.move_to(x, y)
    cr.line_to(ex, ey)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_width(w)
    cr.set_source_rgba(*_mix(c, (0, 0, 0.1), 0.45), a)
    cr.stroke()
    if depth <= 0:
        halo(cr, ex, ey, w * 2.2, c, 0.6 * a)
        cr.arc(ex, ey, w * 0.55, 0, TAU)
        cr.set_source_rgba(*_mix(c, (1, 1, 1), 0.4), a)
        cr.fill()
        return
    for d in (-0.5, 0.45):
        coral(cr, ex, ey, h * rnd.uniform(0.55, 0.75), c, rnd, a, depth - 1, ang + d + rnd.uniform(-0.2, 0.2), w * 0.72)


def seaweed(cr, x, y, h, c, phase=0.0, a=1.0, w=None):
    w = w or max(1.5, h * 0.12)
    left, right = [], []
    for k in range(13):
        f = k / 12
        cx = x + math.sin(f * 4 + phase) * h * 0.12 * f
        cy = y - h * f
        wd = w * (1 - f * 0.8) / 2
        left.append((cx - wd, cy))
        right.append((cx + wd, cy))
    _poly(cr, left + right[::-1], True)
    cr.set_source(_vgrad(y - h, y, _mix(c, (1, 1, 1), 0.2), _mix(c, (0, 0, 0), 0.6), a))
    cr.fill()


def tentacle(cr, pts, wmax, base, rim, glow, suckers=True, a=1.0):
    """An octopus arm: a tapering tube, lit rim and a row of suckers."""
    n = len(pts)
    widths = [wmax * (1 - i / n) ** 0.8 + 0.4 for i in range(n)]
    left, right = w3.tube(cr, pts, widths, base, rim, glow, 0.3 * a)
    if suckers:
        for i in range(2, n - 2, 2):
            sx, sy = right[i]
            r = widths[i] * 0.22
            cr.arc(sx, sy, r, 0, TAU)
            cr.set_source_rgba(*_mix(rim, (1, 1, 1), 0.3), 0.75 * a)
            cr.fill()


# ═══════════════════════════════════════════════════════════ Enchanted forest
def mushroom(cr, x, y, s, cap=None, a=1.0, glow=True, tilt=0.0):
    """A fly agaric standing on (x, y) (s = cap width): red cap, white
    spots, a skirt on the stem and a soft glow under the cap."""
    cap = cap or rgb('#e8402a')
    stem = rgb('#f2e6c8')
    cr.save()
    cr.translate(x, y)
    cr.rotate(tilt)
    if glow:
        halo(cr, 0, -s * 0.45, s * 1.1, _mix(cap, (1, 0.8, 0.4), 0.4), 0.3 * a)
    cr.new_path()   # stem
    cr.move_to(-s * 0.13, 0)
    cr.curve_to(-s * 0.1, -s * 0.25, -s * 0.12, -s * 0.45, -s * 0.09, -s * 0.6)
    cr.line_to(s * 0.09, -s * 0.6)
    cr.curve_to(s * 0.12, -s * 0.45, s * 0.1, -s * 0.25, s * 0.13, 0)
    cr.close_path()
    g = cairo.LinearGradient(-s * 0.13, 0, s * 0.13, 0)
    g.add_color_stop_rgba(0, *stem, a)
    g.add_color_stop_rgba(1, *_mix(stem, (0.4, 0.3, 0.2), 0.45), a)
    cr.set_source(g)
    cr.fill()
    _ellipse(cr, 0, -s * 0.42, s * 0.15, s * 0.04)   # the skirt
    cr.set_source_rgba(*_mix(stem, (1, 1, 1), 0.3), a)
    cr.fill()
    cr.new_path()   # cap
    cr.move_to(-s * 0.5, -s * 0.56)
    cr.curve_to(-s * 0.5, -s * 1.05, s * 0.5, -s * 1.05, s * 0.5, -s * 0.56)
    cr.curve_to(s * 0.25, -s * 0.5, -s * 0.25, -s * 0.5, -s * 0.5, -s * 0.56)
    cr.close_path()
    cr.set_source(_radial(-s * 0.12, -s * 0.85, s * 0.7, _mix(cap, (1, 0.8, 0.6), 0.35), _mix(cap, (0.2, 0, 0), 0.4),
                          a, a))
    cr.fill()
    rnd = random.Random(int(s * 13))
    for _ in range(6):   # white spots
        ang = rnd.uniform(PI * 1.1, PI * 1.9)
        d = rnd.uniform(0.15, 0.36) * s
        cr.arc(math.cos(ang) * d, -s * 0.62 + math.sin(ang) * d * 0.9, s * rnd.uniform(0.035, 0.07), 0, TAU)
        cr.set_source_rgba(1, 0.97, 0.92, 0.95 * a)
        cr.fill()
    cr.restore()


def vine(cr, pts, width, rnd, a=1.0, leaves=True, moss=None):
    """A mossy branch along pts: bark tube lit by moss, leaves sprouting."""
    bark, moss = rgb('#3a2412'), moss or rgb('#9ce02e')
    n = len(pts)
    left, right = w3.tube(cr, pts, [width * (0.8 + 0.2 * math.sin(i * 0.4)) for i in range(n)], bark,
                          _mix(moss, (0.6, 0.4, 0.2), 0.35), moss, 0.18 * a)
    cr.set_line_width(0.5)   # bark grooves
    for i in range(0, n - 3, 3):
        cr.move_to(*left[i])
        cr.line_to(*right[min(n - 1, i + 2)])
    cr.set_source_rgba(0.08, 0.04, 0.01, 0.5 * a)
    cr.stroke()
    if leaves:
        for i in range(2, n - 1, max(2, int(n / 9))):
            if rnd.random() < 0.7:
                (ax, ay), (bx, by) = pts[i - 1], pts[i]
                ang = math.atan2(by - ay, bx - ax) + rnd.choice((-1, 1)) * rnd.uniform(0.6, 1.3)
                ws.leaf(cr, bx, by, width * rnd.uniform(1.6, 2.6), ang,
                        rgb(rnd.choice(('#9ce02e', '#6fc42a', '#c8f04a'))))


def firefly(cr, x, y, r, c=None, a=1.0):
    c = c or rgb('#e8ff6a')
    halo(cr, x, y, r * 4, c, 0.45 * a)
    cr.arc(x, y, r, 0, TAU)
    cr.set_source_rgba(*_mix(c, (1, 1, 1), 0.6), a)
    cr.fill()


# ═══════════════════════════════════════════════════════════ Cosmos
def planet(cr, x, y, r, c1, c2, ring=True, tilt=-0.35, ring_c=None, a=1.0, bands=True):
    """A planet lit from the upper left, its ring behind and in front."""
    ring_c = ring_c or _mix(c1, (1, 1, 1), 0.35)
    halo(cr, x, y, r * 1.8, c1, 0.3 * a)

    def ring_half(front):
        cr.save()
        cr.translate(x, y)
        cr.rotate(tilt)
        cr.scale(r * 1.9, r * 0.42)
        cr.new_path()
        cr.arc(0, 0, 1, 0 if front else PI, PI if front else TAU)
        cr.restore()
        for lw, al in ((r * 0.32, 0.18), (r * 0.16, 0.45), (max(0.6, r * 0.05), 0.95)):
            cr.set_line_width(lw)
            cr.set_source_rgba(*ring_c, al * a)
            cr.stroke_preserve()
        cr.new_path()
    if ring:
        ring_half(False)
    cr.arc(x, y, r, 0, TAU)
    cr.set_source(_radial(x, y, r, _mix(c1, (1, 1, 1), 0.35), _mix(c2, (0, 0, 0.05), 0.45), a, a, -0.35, -0.35))
    cr.fill()
    if bands:
        cr.save()
        cr.arc(x, y, r, 0, TAU)
        cr.clip()
        cr.translate(x, y)
        cr.rotate(tilt)
        for k in (-0.5, -0.15, 0.25, 0.55):
            cr.rectangle(-r, k * r, 2 * r, r * 0.12)
        cr.set_source_rgba(*c2, 0.28 * a)
        cr.fill()
        cr.restore()
    if ring:
        ring_half(True)


def helmet(cr, x, y, s, a=1.0, glow=None):
    """An astronaut's helmet (s = its width), the visor reflecting stars."""
    shell, dark = rgb('#d6d8e4'), rgb('#4a4c62')
    glow = glow or rgb('#8a8cff')
    cr.arc(x, y, s * 0.5, 0, TAU)
    cr.set_source(_radial(x, y, s * 0.5, shell, dark, a, a, -0.35, -0.4))
    cr.fill()
    _ellipse(cr, x, y + s * 0.42, s * 0.36, s * 0.1)   # the neck ring
    cr.set_source_rgba(*_mix(dark, (0, 0, 0), 0.3), a)
    cr.fill()
    _ellipse(cr, x + s * 0.04, y + s * 0.02, s * 0.36, s * 0.3)   # visor
    path = cr.copy_path()
    g = cairo.LinearGradient(x - s * 0.3, y - s * 0.3, x + s * 0.3, y + s * 0.3)
    g.add_color_stop_rgba(0, *_mix(glow, (1, 1, 1), 0.2), a)
    g.add_color_stop_rgba(0.45, 0.04, 0.03, 0.12, a)
    g.add_color_stop_rgba(1, *_mix(glow, (0, 0, 0), 0.3), a)
    cr.set_source(g)
    cr.fill()
    cr.save()
    cr.new_path()
    cr.append_path(path)
    cr.clip()
    rnd = random.Random(int(s))
    for _ in range(7):
        cr.arc(x + rnd.uniform(-0.3, 0.35) * s, y + rnd.uniform(-0.2, 0.25) * s, max(0.3, s * 0.012), 0, TAU)
        cr.set_source_rgba(1, 1, 1, 0.8 * a)
        cr.fill()
    cr.restore()
    cr.new_path()
    cr.arc(x - s * 0.06, y - s * 0.04, s * 0.25, PI * 1.05, PI * 1.45)
    cr.set_line_width(max(0.5, s * 0.04))
    cr.set_source_rgba(1, 1, 1, 0.6 * a)
    cr.stroke()
    halo(cr, x + s * 0.42, y - s * 0.1, s * 0.12, rgb('#ff4a6a'), 0.9 * a)   # the side lamp


def asteroid(cr, x, y, r, rnd, c=None, a=1.0, rim=None):
    c = c or rgb('#4a4466')
    rim = rim or rgb('#8a7cff')
    pts = []
    for k in range(11):
        ang = k / 11 * TAU
        rr = r * rnd.uniform(0.75, 1.1)
        pts.append((x + math.cos(ang) * rr, y + math.sin(ang) * rr))
    _curve(cr, pts, True)
    path = cr.copy_path()
    cr.set_source(_radial(x, y, r * 1.1, _mix(c, (1, 1, 1), 0.2), _mix(c, (0, 0, 0), 0.6), a, a, -0.4, -0.4))
    cr.fill()
    cr.append_path(path)
    cr.set_line_width(0.8)
    cr.set_source_rgba(*rim, 0.4 * a)
    cr.stroke()
    for _ in range(3):
        cr.arc(x + rnd.uniform(-0.4, 0.4) * r, y + rnd.uniform(-0.4, 0.4) * r, r * rnd.uniform(0.1, 0.22), 0, TAU)
        cr.set_source_rgba(0, 0, 0, 0.25 * a)
        cr.fill()


def lights(cr, x0, x1, y, rnd, cols, a=1.0, every=40, w=6, h=1.6):
    """Short status light strips along a hull edge."""
    x = x0 + rnd.uniform(0, every)
    while x < x1 - w:
        col = rgb(rnd.choice(cols))
        cr.rectangle(x, y - h / 2, w * rnd.uniform(0.6, 1.4), h)
        cr.set_source_rgba(*col, a)
        cr.fill()
        halo(cr, x + w / 2, y, w, col, 0.35 * a)
        x += every * rnd.uniform(0.6, 1.4)


# ═══════════════════════════════════════════════════════════ Samurai
def katana(cr, x, y, ang, L, a=1.0):
    """A katana from its pommel at (x, y) along angle ang (L = its length):
    wrapped hilt, gold guard, curved blade with a temper line."""
    cr.save()
    cr.translate(x, y)
    cr.rotate(ang)
    hw = L * 0.022
    cr.new_path()   # hilt
    cr.move_to(0, -hw)
    cr.line_to(L * 0.25, -hw * 1.05)
    cr.line_to(L * 0.25, hw * 1.05)
    cr.line_to(0, hw)
    cr.close_path()
    cr.set_source_rgba(0.06, 0.04, 0.05, a)
    cr.fill()
    cr.set_line_width(max(0.4, hw * 0.35))   # the diamond wrap
    k = 0.0
    while k < L * 0.24:
        cr.move_to(k, -hw)
        cr.line_to(k + hw * 1.6, hw)
        cr.move_to(k, hw)
        cr.line_to(k + hw * 1.6, -hw)
        k += hw * 1.6
    cr.set_source_rgba(*rgb('#ffb43a'), 0.85 * a)
    cr.stroke()
    _ellipse(cr, 0, 0, hw * 0.5, hw * 1.15)   # pommel
    cr.set_source_rgba(*rgb('#d8a03a'), a)
    cr.fill()
    _ellipse(cr, L * 0.255, 0, hw * 0.55, hw * 2.6)   # tsuba
    cr.set_source(_vgrad(-hw * 2.6, hw * 2.6, rgb('#ffe08a'), rgb('#8a5a1a'), a))
    cr.fill()
    cr.new_path()   # the blade, with a little curve (sori)
    b0 = L * 0.27
    cr.move_to(b0, -hw * 0.9)
    cr.curve_to(L * 0.5, -hw * 1.3, L * 0.8, -hw * 1.6, L * 0.97, -hw * 2.6)
    cr.line_to(L, -hw * 1.6)
    cr.curve_to(L * 0.8, hw * 0.2, L * 0.5, hw * 0.75, b0, hw * 0.9)
    cr.close_path()
    g = cairo.LinearGradient(0, -hw * 1.6, 0, hw)
    g.add_color_stop_rgba(0, 0.55, 0.58, 0.66, a)
    g.add_color_stop_rgba(0.5, 0.92, 0.94, 1, a)
    g.add_color_stop_rgba(1, 0.75, 0.78, 0.86, a)
    cr.set_source(g)
    cr.fill()
    cr.move_to(b0, hw * 0.25)   # hamon, the temper line
    for i in range(1, 25):
        f = i / 24
        cr.line_to(b0 + (L * 0.95 - b0) * f, hw * (0.25 - 1.5 * f * f) + math.sin(i * 1.9) * hw * 0.18)
    cr.set_line_width(max(0.4, hw * 0.25))
    cr.set_source_rgba(1, 1, 1, 0.7 * a)
    cr.stroke()
    cr.restore()


def pagoda(cr, x, y, s, c, lit=None, a=1.0):
    """A three-roof pagoda standing on (x, y) (s = its height)."""
    lit = lit or rgb('#ffb84a')
    cr.new_path()
    widths = (0.62, 0.5, 0.38)
    yy = y
    for i, wv in enumerate(widths):
        wall = s * 0.14
        cr.rectangle(x - wv * s * 0.32, yy - wall, wv * s * 0.64, wall)
        ry = yy - wall
        cr.move_to(x - wv * s * 0.62, ry + s * 0.01)   # the roof, eaves curling up
        cr.curve_to(x - wv * s * 0.45, ry - s * 0.03, x - wv * s * 0.3, ry - s * 0.07, x - wv * s * 0.15, ry - s * 0.1)
        cr.line_to(x + wv * s * 0.15, ry - s * 0.1)
        cr.curve_to(x + wv * s * 0.3, ry - s * 0.07, x + wv * s * 0.45, ry - s * 0.03, x + wv * s * 0.62, ry + s * 0.01)
        cr.close_path()
        yy = ry - s * 0.1
    cr.rectangle(x - s * 0.012, yy - s * 0.16, s * 0.024, s * 0.16)   # the spire
    cr.set_source_rgba(*c, a)
    cr.fill()
    yy = y
    for i, wv in enumerate(widths):   # lit windows
        for k in (-1, 1):
            cr.rectangle(x + k * wv * s * 0.12 - s * 0.02, yy - s * 0.1, s * 0.04, s * 0.05)
        yy -= s * 0.24
    cr.set_source_rgba(*lit, 0.85 * a)
    cr.fill()


def stone_lantern(cr, x, y, s, c, lit=None, a=1.0):
    """A tōrō, the stone lantern of the gardens, its fire box lit."""
    lit = lit or rgb('#ffb84a')
    cr.new_path()
    cr.rectangle(x - s * 0.22, y - s * 0.08, s * 0.44, s * 0.08)
    cr.rectangle(x - s * 0.07, y - s * 0.45, s * 0.14, s * 0.37)
    cr.rectangle(x - s * 0.24, y - s * 0.5, s * 0.48, s * 0.06)
    cr.move_to(x - s * 0.36, y - s * 0.74)
    cr.line_to(x, y - s * 0.92)
    cr.line_to(x + s * 0.36, y - s * 0.74)
    cr.close_path()
    cr.set_source_rgba(*c, a)
    cr.fill()
    halo(cr, x, y - s * 0.62, s * 0.55, lit, 0.55 * a)
    cr.rectangle(x - s * 0.16, y - s * 0.74, s * 0.32, s * 0.24)
    cr.set_source(_vgrad(y - s * 0.74, y - s * 0.5, _mix(lit, (1, 1, 1), 0.5), lit, a))
    cr.fill()
    cr.rectangle(x - s * 0.02, y - s * 0.74, s * 0.04, s * 0.24)
    cr.set_source_rgba(*c, a)
    cr.fill()


def enso(cr, x, y, r, c, w, a=1.0, seed=4):
    """The zen circle, one brush stroke left open."""
    rnd = random.Random(seed)
    a0 = -PI * 0.42
    n = 40
    for i in range(n):
        f = i / n
        ang = a0 + f * TAU * 0.9
        cr.arc(x, y, r * (1 + 0.04 * math.sin(f * 9)), ang, ang + TAU * 0.9 / n + 0.02)
        cr.set_line_width(w * (0.35 + 0.65 * math.sin(f * PI) ** 0.6) * rnd.uniform(0.9, 1.1))
        cr.set_source_rgba(*c, a * (0.7 + 0.3 * math.sin(f * PI)))
        cr.stroke()


# ═══════════════════════════════════════════════════════════ Steampunk
def gear(cr, x, y, r, teeth, rot, a=1.0, face=None, hole=True, spokes=5, glow=None):
    """A brass cog: teeth, spoked wheel, hub and axle."""
    face = face or rgb('#d8962e')
    light, dark = _mix(face, (1, 0.95, 0.75), 0.45), _mix(face, (0.2, 0.08, 0), 0.6)
    if glow:
        halo(cr, x, y, r * 1.6, glow, 0.3 * a)
    cr.new_path()
    td = r * 0.2
    for i in range(teeth * 2):
        ang = rot + i * PI / teeth
        r0 = r if i % 2 == 0 else r - td
        a1 = ang - PI / teeth * (0.32 if i % 2 == 0 else 0.5)
        a2 = ang + PI / teeth * (0.32 if i % 2 == 0 else 0.5)
        if i == 0:
            cr.move_to(x + math.cos(a1) * r0, y + math.sin(a1) * r0)
        else:
            cr.line_to(x + math.cos(a1) * r0, y + math.sin(a1) * r0)
        cr.line_to(x + math.cos(a2) * r0, y + math.sin(a2) * r0)
    cr.close_path()
    cr.set_source(_radial(x, y, r, light, dark, a, a, -0.3, -0.35))
    cr.fill()
    if spokes and r > 5:   # the wheel between rim and hub
        ri, ro = r * 0.3, r * 0.62
        for k in range(spokes):
            a1 = rot + k * TAU / spokes + 0.22
            a2 = rot + (k + 1) * TAU / spokes - 0.22
            cr.new_path()
            cr.arc(x, y, ro, a1, a2)
            cr.arc_negative(x, y, ri, a2 - 0.08, a1 + 0.08)
            cr.close_path()
            cr.set_source_rgba(*_mix(dark, (0, 0, 0), 0.6), 0.85 * a)
            cr.fill()
    cr.arc(x, y, r * 0.22, 0, TAU)
    cr.set_source(_radial(x, y, r * 0.22, light, face, a, a, -0.3, -0.3))
    cr.fill()
    if hole:
        cr.arc(x, y, r * 0.08, 0, TAU)
        cr.set_source_rgba(0.08, 0.04, 0.02, a)
        cr.fill()


def rivet(cr, x, y, r, a=1.0):
    cr.arc(x, y, r, 0, TAU)
    cr.set_source(_radial(x, y, r, rgb('#ffe2a0'), rgb('#6a3a12'), a, a, -0.35, -0.35))
    cr.fill()


def gauge(cr, x, y, r, needle, a=1.0):
    """A pressure gauge: brass bezel, cream dial, red zone, needle."""
    cr.arc(x, y, r, 0, TAU)
    cr.set_source(_radial(x, y, r, rgb('#ffe2a0'), rgb('#7a4a14'), a, a, -0.3, -0.3))
    cr.fill()
    cr.arc(x, y, r * 0.78, 0, TAU)
    cr.set_source(_radial(x, y, r * 0.78, rgb('#fff4dc'), rgb('#c8b088'), a, a, -0.2, -0.3))
    cr.fill()
    cr.set_line_width(max(0.5, r * 0.12))
    cr.arc(x, y, r * 0.6, PI * 0.15, PI * 0.45)
    cr.set_source_rgba(*rgb('#d8302a'), 0.85 * a)
    cr.stroke()
    cr.set_line_width(max(0.3, r * 0.05))
    for k in range(9):   # ticks
        ang = PI * 0.75 + k * PI * 1.5 / 8
        cr.move_to(x + math.cos(ang) * r * 0.55, y + math.sin(ang) * r * 0.55)
        cr.line_to(x + math.cos(ang) * r * 0.7, y + math.sin(ang) * r * 0.7)
    cr.set_source_rgba(0.15, 0.08, 0.04, a)
    cr.stroke()
    cr.move_to(x - math.cos(needle) * r * 0.12, y - math.sin(needle) * r * 0.12)
    cr.line_to(x + math.cos(needle) * r * 0.62, y + math.sin(needle) * r * 0.62)
    cr.set_line_width(max(0.5, r * 0.08))
    cr.set_source_rgba(*rgb('#b0201a'), a)
    cr.stroke()
    cr.arc(x, y, r * 0.1, 0, TAU)
    cr.set_source_rgba(0.2, 0.1, 0.05, a)
    cr.fill()
    cr.arc(x - r * 0.15, y - r * 0.15, r * 0.6, PI * 1.05, PI * 1.5)
    cr.set_source_rgba(1, 1, 1, 0.45 * a)
    cr.stroke()


def airship(cr, x, y, s, a=1.0, c=None):
    """A dirigible heading left (s = its length): envelope, seams, fins,
    gondola and propeller."""
    c = c or rgb('#b07038')
    _ellipse(cr, x, y, s * 0.5, s * 0.17)
    cr.set_source(_vgrad(y - s * 0.17, y + s * 0.17, _mix(c, (1, 0.9, 0.7), 0.4), _mix(c, (0.1, 0.04, 0), 0.6), a))
    cr.fill()
    cr.save()
    _ellipse(cr, x, y, s * 0.5, s * 0.17)
    cr.clip()
    cr.set_line_width(max(0.4, s * 0.008))
    for k in range(-4, 5):   # ribs
        _ellipse(cr, x + k * s * 0.1, y, s * 0.04, s * 0.17)
    cr.set_source_rgba(0.15, 0.07, 0.02, 0.45 * a)
    cr.stroke()
    cr.move_to(x - s * 0.5, y)
    cr.line_to(x + s * 0.5, y)
    cr.stroke()
    cr.restore()
    cr.new_path()   # tail fins
    cr.move_to(x + s * 0.38, y - s * 0.08)
    cr.line_to(x + s * 0.56, y - s * 0.24)
    cr.line_to(x + s * 0.55, y - s * 0.04)
    cr.close_path()
    cr.move_to(x + s * 0.38, y + s * 0.08)
    cr.line_to(x + s * 0.56, y + s * 0.24)
    cr.line_to(x + s * 0.55, y + s * 0.04)
    cr.close_path()
    cr.set_source_rgba(*_mix(c, (0.1, 0.04, 0), 0.5), a)
    cr.fill()
    cr.set_line_width(max(0.4, s * 0.008))   # cables and gondola
    for k in (-0.12, 0.12):
        cr.move_to(x + k * s, y + s * 0.15)
        cr.line_to(x + k * s * 0.6, y + s * 0.26)
    cr.set_source_rgba(0.2, 0.1, 0.05, a)
    cr.stroke()
    rounded(cr, x - s * 0.12, y + s * 0.25, s * 0.24, s * 0.07, s * 0.02)
    cr.set_source_rgba(*rgb('#4a2a12'), a)
    cr.fill()
    for k in range(3):
        cr.rectangle(x - s * 0.08 + k * s * 0.06, y + s * 0.265, s * 0.025, s * 0.025)
    cr.set_source_rgba(*rgb('#ffc85a'), a)
    cr.fill()
    _ellipse(cr, x + s * 0.13, y + s * 0.285, s * 0.01, s * 0.045)   # propeller
    cr.set_source_rgba(0.7, 0.6, 0.4, 0.7 * a)
    cr.fill()


def steam(cr, x, y, r, a=1.0, seed=5, c=None):
    """A puff of steam (soft overlapping clouds)."""
    c = c or (0.95, 0.92, 0.86)
    rnd = random.Random(seed)
    for _ in range(6):
        halo(cr, x + rnd.uniform(-r, r) * 0.7, y + rnd.uniform(-r, r) * 0.5, r * rnd.uniform(0.5, 0.9), c,
             0.22 * a)


def brass_path(cr, path, width, a=1.0):
    """A brass pipe along path(): dark edge, metal body, a bright reflection."""
    brass, dark, light = rgb('#c8822a'), rgb('#3a1e08'), rgb('#ffe2a0')
    for lw, col, al in ((width + 2.4, dark, 0.95), (width, brass, 1.0), (width * 0.45, _mix(brass, light, 0.5), 0.9),
                        (width * 0.16, light, 0.95)):
        path()
        cr.set_line_width(lw)
        cr.set_source_rgba(*col, al * a)
        cr.stroke()


# ═══════════════════════════════════════════════════════════ Glacier
def ice_shard(cr, x, y, w, h, ang, c, a=1.0):
    """An ice crystal rising from (x, y): a pointed prism, a lit face and
    a shaded one."""
    cr.save()
    cr.translate(x, y)
    cr.rotate(ang)
    light, dark = _mix(c, (1, 1, 1), 0.55), _mix(c, (0, 0.05, 0.2), 0.45)
    cr.new_path()   # left face
    cr.move_to(-w / 2, 0)
    cr.line_to(-w / 2, -h * 0.72)
    cr.line_to(0, -h)
    cr.line_to(w * 0.08, 0)
    cr.close_path()
    cr.set_source(_vgrad(-h, 0, light, c, 0.85 * a))
    cr.fill()
    cr.new_path()   # right face
    cr.move_to(w * 0.08, 0)
    cr.line_to(0, -h)
    cr.line_to(w / 2, -h * 0.72)
    cr.line_to(w / 2, 0)
    cr.close_path()
    cr.set_source(_vgrad(-h, 0, c, dark, 0.8 * a))
    cr.fill()
    cr.new_path()
    cr.move_to(-w / 2, 0)
    cr.line_to(-w / 2, -h * 0.72)
    cr.line_to(0, -h)
    cr.line_to(w / 2, -h * 0.72)
    cr.line_to(w / 2, 0)
    cr.move_to(0, -h)
    cr.line_to(w * 0.08, 0)
    cr.set_line_width(max(0.4, w * 0.06))
    cr.set_source_rgba(*_mix(c, (1, 1, 1), 0.75), 0.9 * a)
    cr.stroke()
    cr.restore()


def crystal_cluster(cr, x, y, s, c, rnd, a=1.0, n=5, spread=0.9):
    """Ice crystals fanning out of (x, y) (s = height of the tallest)."""
    halo(cr, x, y - s * 0.4, s * 0.9, c, 0.35 * a)
    shards = []
    for i in range(n):
        f = i / max(1, n - 1) - 0.5
        shards.append((abs(f), f * spread + rnd.uniform(-0.1, 0.1), s * (1 - abs(f) * 0.8) * rnd.uniform(0.75, 1.0)))
    for _d, ang, hh in sorted(shards, reverse=True):
        ice_shard(cr, x + ang * s * 0.18, y, hh * 0.28, hh, ang, c, a)


def icicle(cr, x, y, L, w, c, a=1.0):
    cr.new_path()
    cr.move_to(x - w / 2, y)
    cr.curve_to(x - w * 0.4, y + L * 0.4, x - w * 0.1, y + L * 0.8, x, y + L)
    cr.curve_to(x + w * 0.1, y + L * 0.8, x + w * 0.4, y + L * 0.4, x + w / 2, y)
    cr.close_path()
    cr.set_source(_vgrad(y, y + L, _mix(c, (1, 1, 1), 0.5), c, 0.85 * a))
    cr.fill()
    cr.move_to(x - w * 0.15, y + 1)
    cr.line_to(x - w * 0.05, y + L * 0.7)
    cr.set_line_width(max(0.3, w * 0.12))
    cr.set_source_rgba(1, 1, 1, 0.7 * a)
    cr.stroke()


def snowflake(cr, x, y, r, c, a=1.0, width=None, glow=True, rot=0.0):
    width = width or max(0.6, r * 0.12)
    cr.save()
    cr.set_line_cap(cairo.LINE_CAP_ROUND)

    def path():
        cr.new_path()
        for k in range(6):
            ang = rot + k * PI / 3
            ca, sa = math.cos(ang), math.sin(ang)
            cr.move_to(x, y)
            cr.line_to(x + ca * r, y + sa * r)
            for f, L in ((0.45, 0.32), (0.72, 0.22)):
                bx, by = x + ca * r * f, y + sa * r * f
                for d in (-0.75, 0.75):
                    cr.move_to(bx, by)
                    cr.line_to(bx + math.cos(ang + d) * r * L, by + math.sin(ang + d) * r * L)
    if glow:
        neon(cr, path, c, width, a, 0.6, layers=((4, 0.08), (2, 0.2)))
    else:
        path()
        cr.set_line_width(width)
        cr.set_source_rgba(*c, a)
        cr.stroke()
    cr.restore()


def wolf(cr, x, y, s, c, rim, eye, a=1.0, facing=-1):
    """A wolf's head in profile, snarling (s = its height)."""
    pts = [(-1.0, -0.06), (-0.62, -0.2), (-0.32, -0.4), (-0.14, -0.48), (-0.02, -0.92), (0.16, -0.52),
           (0.3, -0.5), (0.42, -0.88), (0.56, -0.42), (0.76, -0.3), (0.68, -0.16), (0.92, -0.06), (0.78, 0.06),
           (0.98, 0.24), (0.8, 0.3), (0.92, 0.55), (0.56, 0.46), (0.22, 0.44), (0.0, 0.4), (-0.12, 0.28),
           (-0.5, 0.16), (-0.46, 0.06), (-0.92, 0.06)]
    P = [(x - px * s * 0.5 * facing, y + py * s * 0.5) for px, py in pts]
    _poly(cr, P, True)
    path = cr.copy_path()
    for extra, al in ((4, 0.12), (2, 0.3)):
        cr.new_path()
        cr.append_path(path)
        cr.set_line_width(extra)
        cr.set_source_rgba(*rim, al * a)
        cr.stroke()
    cr.new_path()
    cr.append_path(path)
    g = cairo.LinearGradient(x - s * 0.5, y - s * 0.5, x + s * 0.5, y + s * 0.5)
    g.add_color_stop_rgba(0, *_mix(c, (1, 1, 1), 0.25), a)
    g.add_color_stop_rgba(1, *_mix(c, (0, 0, 0), 0.55), a)
    cr.set_source(g)
    cr.fill_preserve()
    cr.set_line_width(0.9)
    cr.set_source_rgba(*rim, 0.85 * a)
    cr.stroke()
    cr.set_line_width(0.6)   # fur strokes
    for (px, py, L) in ((0.3, -0.1, 0.2), (0.45, 0.1, 0.25), (0.15, 0.2, 0.2), (0.55, -0.15, 0.2)):
        cr.move_to(x - px * s * 0.5 * facing, y + py * s * 0.5)
        cr.line_to(x - (px + L) * s * 0.5 * facing, y + (py + L * 0.4) * s * 0.5)
    cr.set_source_rgba(*rim, 0.5 * a)
    cr.stroke()
    ex, ey = x - (-0.3) * s * 0.5 * facing, y - 0.24 * s * 0.5
    halo(cr, ex, ey, s * 0.14, eye, 0.9 * a)
    cr.arc(ex, ey, max(0.6, s * 0.035), 0, TAU)
    cr.set_source_rgba(1, 1, 1, a)
    cr.fill()
    for k in range(3):   # fangs
        fx = x - (-0.85 + k * 0.14) * s * 0.5 * facing
        _poly(cr, [(fx - s * 0.02, y + s * 0.03), (fx + s * 0.02, y + s * 0.03), (fx, y + s * 0.09)], True)
        cr.set_source_rgba(1, 1, 1, 0.9 * a)
        cr.fill()


# ═══════════════════════════════════════════════════════════ Witchcraft
def pentagram(cr, x, y, r, c, width=1.2, a=1.0, glow=True, rot=0.0):
    def path():
        cr.new_path()
        for i in range(6):
            ang = rot - PI / 2 + (i * 2 % 5) * TAU / 5
            (cr.move_to if i == 0 else cr.line_to)(x + math.cos(ang) * r * 0.86, y + math.sin(ang) * r * 0.86)
        cr.close_path()
        cr.new_sub_path()
        cr.arc(x, y, r, 0, TAU)
    cr.save()
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    if glow:
        neon(cr, path, c, width, a)
    else:
        path()
        cr.set_line_width(width)
        cr.set_source_rgba(*c, a)
        cr.stroke()
    cr.restore()


def raven(cr, x, y, s, c=None, rim=None, eye=None, a=1.0, facing=-1):
    """A raven perched on (x, y) (its feet), looking to one side."""
    c = c or rgb('#0c0814')
    rim = rim or rgb('#b43cff')
    eye = eye or rgb('#e8c8ff')
    pts = [(-0.95, -0.62), (-0.66, -0.74), (-0.48, -0.86), (-0.28, -0.8), (-0.16, -0.62), (0.18, -0.46),
           (0.5, -0.12), (0.95, 0.3), (0.84, 0.38), (0.98, 0.5), (0.62, 0.36), (0.3, 0.16), (0.02, 0.1),
           (-0.3, -0.12), (-0.44, -0.4), (-0.64, -0.56)]
    P = [(x - px * s * 0.5 * facing, y - s * 0.12 + py * s * 0.5) for px, py in pts]
    _curve(cr, P, True)
    path = cr.copy_path()
    for extra, al in ((3, 0.15), (1.4, 0.4)):
        cr.new_path()
        cr.append_path(path)
        cr.set_line_width(extra)
        cr.set_source_rgba(*rim, al * a)
        cr.stroke()
    cr.new_path()
    cr.append_path(path)
    cr.set_source_rgba(*c, a)
    cr.fill()
    cr.set_line_width(0.7)   # wing feathers
    for k in range(4):
        cr.move_to(x - (-0.05 + k * 0.12) * s * 0.5 * facing, y - s * 0.12 + (-0.3 + k * 0.08) * s * 0.5)
        cr.line_to(x - (0.4 + k * 0.12) * s * 0.5 * facing, y - s * 0.12 + (0.0 + k * 0.1) * s * 0.5)
    cr.set_source_rgba(*rim, 0.35 * a)
    cr.stroke()
    cr.set_line_width(max(0.5, s * 0.03))   # legs
    for dx in (-0.02, 0.1):
        cr.move_to(x - dx * s * facing, y - s * 0.07)
        cr.line_to(x - dx * s * facing, y)
    cr.set_source_rgba(*c, a)
    cr.stroke()
    ex, ey = x - (-0.42) * s * 0.5 * facing, y - s * 0.12 - 0.72 * s * 0.5
    halo(cr, ex, ey, s * 0.08, eye, 0.9 * a)
    cr.arc(ex, ey, max(0.4, s * 0.025), 0, TAU)
    cr.set_source_rgba(*eye, a)
    cr.fill()


def spellbook(cr, x, y, s, a=1.0, glow=None):
    """An open grimoire lying on (x, y) (s = its width), its pages glowing."""
    glow = glow or rgb('#b43cff')
    page, cover = rgb('#efe0c0'), rgb('#3a1430')
    halo(cr, x, y - s * 0.2, s * 0.8, glow, 0.35 * a)
    for sx in (-1, 1):
        cr.new_path()   # cover under the pages
        cr.move_to(x, y + s * 0.04)
        cr.line_to(x + sx * s * 0.52, y - s * 0.02)
        cr.line_to(x + sx * s * 0.52, y + s * 0.06)
        cr.line_to(x, y + s * 0.1)
        cr.close_path()
        cr.set_source_rgba(*cover, a)
        cr.fill()
        cr.new_path()   # the pages, curving up from the spine
        cr.move_to(x, y)
        cr.curve_to(x + sx * s * 0.15, y - s * 0.14, x + sx * s * 0.35, y - s * 0.12, x + sx * s * 0.5, y - s * 0.08)
        cr.line_to(x + sx * s * 0.5, y + s * 0.0)
        cr.curve_to(x + sx * s * 0.35, y - s * 0.04, x + sx * s * 0.15, y - s * 0.04, x, y + s * 0.06)
        cr.close_path()
        cr.set_source(_vgrad(y - s * 0.14, y + s * 0.06, _mix(page, (1, 1, 1), 0.3), _mix(page, (0.5, 0.4, 0.3), 0.4),
                             a))
        cr.fill()
        cr.set_line_width(max(0.3, s * 0.01))   # glowing script
        for k in range(3):
            yy = y - s * 0.07 + k * s * 0.03
            cr.move_to(x + sx * s * 0.1, yy)
            for i in range(1, 7):
                cr.line_to(x + sx * s * (0.1 + i * 0.05), yy + math.sin(i * 2.3 + k) * s * 0.008)
        cr.set_source_rgba(*glow, 0.85 * a)
        cr.stroke()


def witch_hat(cr, x, y, s, c, band, a=1.0):
    """A pointed hat resting on (x, y) (s = its width), the tip bent."""
    _ellipse(cr, x, y, s * 0.5, s * 0.1)
    cr.set_source_rgba(*c, a)
    cr.fill()
    cr.new_path()
    cr.move_to(x - s * 0.26, y - s * 0.02)
    cr.curve_to(x - s * 0.16, y - s * 0.4, x - s * 0.02, y - s * 0.62, x + s * 0.3, y - s * 0.7)
    cr.curve_to(x + s * 0.08, y - s * 0.52, x + s * 0.16, y - s * 0.3, x + s * 0.26, y - s * 0.02)
    cr.close_path()
    cr.set_source(_vgrad(y - s * 0.7, y, _mix(c, (1, 1, 1), 0.15), c, a))
    cr.fill()
    cr.new_path()
    cr.move_to(x - s * 0.25, y - s * 0.06)
    cr.line_to(x + s * 0.25, y - s * 0.06)
    cr.line_to(x + s * 0.22, y - s * 0.15)
    cr.line_to(x - s * 0.21, y - s * 0.15)
    cr.close_path()
    cr.set_source_rgba(*band, a)
    cr.fill()


def thorns(cr, pts, rnd, c, every=9, size=3.0, a=1.0):
    """Thorns pointing out of a path (on its left side)."""
    n = len(pts)
    for i in range(2, n - 2, every):
        (ax, ay), (bx, by) = pts[i - 1], pts[i + 1]
        L = math.hypot(bx - ax, by - ay) or 1
        tx, ty = (bx - ax) / L, (by - ay) / L
        side = rnd.choice((-1, 1))
        nx, ny = -ty * side, tx * side
        px, py = pts[i]
        h = size * rnd.uniform(0.7, 1.2)
        _poly(cr, [(px - tx * h * 0.35, py - ty * h * 0.35), (px + tx * h * 0.35, py + ty * h * 0.35),
                   (px + nx * h + tx * h * 0.4, py + ny * h + ty * h * 0.4)], True)
        cr.set_source_rgba(*c, a)
        cr.fill()


def wisp(cr, x, y, s, c, a=1.0, lean=0.0):
    """A will-o'-the-wisp, a little ghostly flame (s = its height)."""
    flame(cr, x, y + s * 0.4, s, s * 0.32, c, a, lean)


def crescent(cr, x, y, r, c, a=1.0, glow=0.35):
    halo(cr, x, y, r * 2.2, c, glow * a)
    cr.push_group()
    cr.arc(x, y, r, 0, TAU)
    cr.set_source(_radial(x, y, r, _mix(c, (1, 1, 1), 0.5), c, a, a, -0.3, -0.3))
    cr.fill()
    cr.set_operator(cairo.OPERATOR_DEST_OUT)
    cr.arc(x + r * 0.45, y - r * 0.2, r * 0.85, 0, TAU)
    cr.set_source_rgba(0, 0, 0, 1)
    cr.fill()
    cr.pop_group_to_source()
    cr.paint()


# ═══════════════════════════════════════════════════════════ Golden dragon
GOLD, GOLD_LIGHT, GOLD_DARK = '#ffb22e', '#ffe68a', '#7a3a08'


def dragon_body(cr, pts, wmax, a=1.0, head=True, tail=True, spines=True, scale_k=1.0, head_k=2.2):
    """A golden dragon along pts (tail first): scaled body, belly plates,
    flame-red dorsal fins, a tufted tail and the head at the end."""
    gold, light, dark = rgb(GOLD), rgb(GOLD_LIGHT), rgb(GOLD_DARK)
    fin = rgb('#ff5a1a')
    n = len(pts)
    widths = []
    for i in range(n):
        f = i / max(1, n - 1)
        widths.append(wmax * (0.25 + 0.75 * math.sin(min(1.0, f * 1.15) * PI * 0.5)) * (0.92 if f > 0.9 else 1))
    left, right = [], []
    for i, (px, py) in enumerate(pts):
        ax, ay = pts[max(0, i - 1)]
        bx, by = pts[min(n - 1, i + 1)]
        L = math.hypot(bx - ax, by - ay) or 1
        nx, ny = -(by - ay) / L, (bx - ax) / L
        wd = widths[i] / 2
        left.append((px + nx * wd, py + ny * wd))
        right.append((px - nx * wd, py - ny * wd))
    if spines:   # flame-like fins on the back
        for i in range(3, n - 4, 3):
            (ax, ay), (bx, by) = pts[i - 1], pts[i + 1]
            L = math.hypot(bx - ax, by - ay) or 1
            nx, ny = -(by - ay) / L, (bx - ax) / L
            tx, ty = (bx - ax) / L, (by - ay) / L
            lx, ly = left[i]
            hgt = widths[i] * 0.85
            _poly(cr, [(lx - tx * widths[i] * 0.4, ly - ty * widths[i] * 0.4),
                       (lx + nx * hgt - tx * hgt * 0.6, ly + ny * hgt - ty * hgt * 0.6),
                       (lx + tx * widths[i] * 0.3, ly + ty * widths[i] * 0.3)], True)
            cr.set_source(_radial(lx, ly, hgt, rgb('#ffd23a'), fin, a, 0.85 * a))
            cr.fill()
    halo_pts = pts[::max(1, n // 6)]
    for hx, hy in halo_pts:
        halo(cr, hx, hy, wmax * 1.6, gold, 0.12 * a)
    _poly(cr, left + right[::-1], True)
    outline = cr.copy_path()
    g = cairo.LinearGradient(0, min(p[1] for p in pts) - wmax, 0, max(p[1] for p in pts) + wmax)
    g.add_color_stop_rgba(0, *light, a)
    g.add_color_stop_rgba(0.5, *gold, a)
    g.add_color_stop_rgba(1, *_mix(gold, dark, 0.6), a)
    cr.set_source(g)
    cr.fill()
    cr.save()
    cr.new_path()
    cr.append_path(outline)
    cr.clip()
    cr.set_line_width(max(0.4, wmax * 0.06))   # scales: little arcs along the body
    for i in range(1, n - 1):
        px, py = pts[i]
        (ax, ay), (bx, by) = pts[i - 1], pts[i + 1]
        ang = math.atan2(by - ay, bx - ax)
        for off in (-0.25, 0.0, 0.25):
            if (i + (1 if off else 0)) % 2:
                continue
            nx, ny = -math.sin(ang), math.cos(ang)
            sr = widths[i] * 0.2 * scale_k
            cr.new_sub_path()
            cr.arc(px + nx * off * widths[i], py + ny * off * widths[i], sr, ang - PI / 2, ang + PI / 2)
    cr.set_source_rgba(*dark, 0.5 * a)
    cr.stroke()
    cr.set_line_width(max(0.4, wmax * 0.05))   # belly plates
    for i in range(1, n - 1, 2):
        rx, ry = right[i]
        px, py = pts[i]
        cr.move_to(rx, ry)
        cr.line_to(px + (rx - px) * 0.35, py + (ry - py) * 0.35)
    cr.set_source_rgba(*light, 0.55 * a)
    cr.stroke()
    cr.restore()
    cr.new_path()
    cr.append_path(outline)
    cr.set_line_width(max(0.5, wmax * 0.07))
    cr.set_source_rgba(*dark, 0.8 * a)
    cr.stroke()
    _poly(cr, left)   # rim light
    cr.set_line_width(max(0.5, wmax * 0.06))
    cr.set_source_rgba(*light, 0.85 * a)
    cr.stroke()
    if tail and n > 3:   # a tuft of flame on the tail
        (ax, ay), (bx, by) = pts[1], pts[0]
        ang = math.atan2(by - ay, bx - ax)
        for d in (-0.6, -0.2, 0.25, 0.6):
            L = wmax * 1.4
            _poly(cr, [(bx + math.cos(ang + PI / 2) * wmax * 0.15, by + math.sin(ang + PI / 2) * wmax * 0.15),
                       (bx + math.cos(ang + d) * L, by + math.sin(ang + d) * L),
                       (bx - math.cos(ang + PI / 2) * wmax * 0.15, by - math.sin(ang + PI / 2) * wmax * 0.15)], True)
            cr.set_source(_radial(bx, by, L, rgb('#ffd23a'), fin, a, 0.6 * a))
            cr.fill()
    if head and n > 3:
        (ax, ay), (bx, by) = pts[-3], pts[-1]
        dragon_head(cr, bx, by, wmax * head_k, math.atan2(by - ay, bx - ax), a)


def dragon_head(cr, x, y, s, ang, a=1.0):
    """The head at the end of the neck (x, y), facing ang (s = its length):
    horns, a flowing mane, whiskers, an open jaw and a burning eye."""
    gold, light, dark = rgb(GOLD), rgb(GOLD_LIGHT), rgb(GOLD_DARK)
    fin = rgb('#ff5a1a')
    flip = -1 if math.cos(ang) < 0 else 1
    cr.save()
    cr.translate(x, y)
    cr.rotate(ang)
    cr.scale(s, s * flip)
    for k, (d, L) in enumerate(((-2.3, 0.62), (-2.6, 0.5), (-2.0, 0.45))):   # the mane
        _poly(cr, [(-0.05, -0.12), (math.cos(d) * L, math.sin(d) * L), (0.1, -0.22)], True)
        cr.set_source(_radial(0, -0.1, L, rgb('#ffd23a'), fin, a, 0.8 * a))
        cr.fill()
    for hy, L in ((-0.26, 0.55), (-0.18, 0.42)):   # horns, sweeping back
        cr.new_path()
        cr.move_to(0.08, hy + 0.02)
        cr.curve_to(-0.1, hy - 0.12, -0.3, hy - 0.2, -L, hy - 0.32)
        cr.curve_to(-0.28, hy - 0.12, -0.1, hy - 0.04, 0.12, hy + 0.08)
        cr.close_path()
        cr.set_source(_vgrad(hy - 0.3, hy + 0.08, light, _mix(gold, dark, 0.5), a))
        cr.fill()
    pts = [(-0.1, -0.2), (0.15, -0.28), (0.42, -0.24), (0.7, -0.16), (0.92, -0.12), (0.98, -0.04), (0.6, 0.0),
           (0.88, 0.1), (0.8, 0.18), (0.45, 0.2), (0.1, 0.24), (-0.1, 0.18)]
    _curve(cr, pts, True)
    path = cr.copy_path()
    cr.set_source(_vgrad(-0.28, 0.24, light, _mix(gold, dark, 0.45), a))
    cr.fill()
    cr.append_path(path)
    cr.set_line_width(0.035)
    cr.set_source_rgba(*dark, 0.85 * a)
    cr.stroke()
    _poly(cr, [(0.6, 0.0), (0.97, -0.03), (0.86, 0.1)], True)   # the open mouth
    cr.set_source_rgba(0.35, 0.02, 0.0, a)
    cr.fill()
    for tx in (0.66, 0.74, 0.82):   # fangs
        _poly(cr, [(tx, -0.01), (tx + 0.04, -0.01), (tx + 0.02, 0.05)], True)
        _poly(cr, [(tx - 0.02, 0.09), (tx + 0.02, 0.09), (tx, 0.04)], True)
    cr.set_source_rgba(1, 0.97, 0.9, a)
    cr.fill()
    cr.new_path()   # whiskers trailing back
    for wy, k in ((-0.08, 1), (0.02, -1)):
        cr.move_to(0.9, wy)
        cr.curve_to(0.6, wy + 0.25 * k, 0.1, wy - 0.05 * k, -0.6, wy + 0.3 * k)
    cr.set_line_width(0.025)
    cr.set_source_rgba(*light, 0.9 * a)
    cr.stroke()
    _ellipse(cr, 0.36, -0.12, 0.07, 0.045, -0.2)   # the eye
    cr.set_source_rgba(1, 0.85, 0.2, a)
    cr.fill()
    _ellipse(cr, 0.37, -0.12, 0.015, 0.04)
    cr.set_source_rgba(0.2, 0.0, 0.0, a)
    cr.fill()
    cr.restore()
    halo(cr, x + math.cos(ang) * s * 0.36, y + math.sin(ang) * s * 0.36, s * 0.25, rgb('#ffd23a'), 0.3 * a)


def cloud_scroll(cr, x, y, s, c, a=1.0, flip=1):
    """An auspicious cloud: a bank of curls, each a spiral."""
    for dx, dy, r in ((-0.35, 0.05, 0.22), (0.0, -0.08, 0.28), (0.36, 0.04, 0.2), (0.15, 0.14, 0.16),
                      (-0.15, 0.14, 0.16)):
        cr.arc(x + dx * s * flip, y + dy * s, r * s, 0, TAU)
        cr.set_source_rgba(*_mix(c, (0.1, 0.02, 0), 0.75), 0.85 * a)
        cr.fill()
    cr.set_line_width(max(0.5, s * 0.035))
    for dx, dy, r in ((-0.35, 0.05, 0.2), (0.0, -0.08, 0.26), (0.36, 0.04, 0.18)):
        cx, cy = x + dx * s * flip, y + dy * s
        cr.new_path()
        for i in range(40):   # a spiral curling in
            f = i / 39
            ang = f * TAU * 1.4 * flip
            rr = r * s * (1 - f * 0.85)
            (cr.move_to if i == 0 else cr.line_to)(cx + math.cos(ang) * rr, cy + math.sin(ang) * rr)
        cr.set_source_rgba(*c, 0.9 * a)
        cr.stroke()


def coin(cr, x, y, r, c, a=1.0, glow=True):
    """A Chinese cash coin: a gold disc with a square hole."""
    if glow:
        halo(cr, x, y, r * 2.0, c, 0.45 * a)
    cr.new_path()
    cr.arc(x, y, r, 0, TAU)
    q = r * 0.3
    cr.rectangle(x + q, y - q, -2 * q, 2 * q)
    cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    cr.set_source(_radial(x, y, r, _mix(c, (1, 1, 1), 0.45), _mix(c, (0.3, 0.1, 0), 0.45), a, a, -0.3, -0.3))
    cr.fill()
    cr.set_fill_rule(cairo.FILL_RULE_WINDING)
    cr.arc(x, y, r * 0.82, 0, TAU)
    cr.set_line_width(max(0.3, r * 0.07))
    cr.set_source_rgba(*_mix(c, (0.3, 0.1, 0), 0.55), a)
    cr.stroke()
    cr.rectangle(x - q * 1.25, y - q * 1.25, q * 2.5, q * 2.5)
    cr.stroke()


def lantern_cn(cr, x, y, s, a=1.0, c=None):
    """A red paper lantern hanging from (x, y) (s = its height)."""
    c = c or rgb('#e8322a')
    gold = rgb('#ffc42e')
    cy = y + s * 0.5
    halo(cr, x, cy, s * 1.1, c, 0.4 * a)
    cr.move_to(x, y - s * 0.3)
    cr.line_to(x, y + s * 0.1)
    cr.set_line_width(max(0.4, s * 0.03))
    cr.set_source_rgba(*gold, a)
    cr.stroke()
    _ellipse(cr, x, cy, s * 0.42, s * 0.36)
    cr.set_source(_radial(x, cy, s * 0.45, _mix(c, (1, 0.9, 0.5), 0.5), _mix(c, (0.2, 0, 0), 0.4), a, a))
    cr.fill()
    cr.save()
    _ellipse(cr, x, cy, s * 0.42, s * 0.36)
    cr.clip()
    cr.set_line_width(max(0.3, s * 0.025))
    for k in (-0.25, 0.0, 0.25):
        _ellipse(cr, x, cy, s * 0.42 * abs(math.cos(k * 3)) + 0.5, s * 0.36)
    cr.set_source_rgba(0.4, 0.05, 0.02, 0.5 * a)
    cr.stroke()
    cr.restore()
    for yy in (cy - s * 0.38, cy + s * 0.3):
        cr.rectangle(x - s * 0.18, yy, s * 0.36, s * 0.08)
    cr.set_source_rgba(*gold, a)
    cr.fill()
    cr.move_to(x, cy + s * 0.38)   # tassel
    cr.line_to(x, cy + s * 0.65)
    cr.set_line_width(max(0.5, s * 0.06))
    cr.set_source_rgba(*c, a)
    cr.stroke()


def meander(cr, x0, x1, y, h, c, width=0.8, a=1.0):
    """A key (meander) border along a line."""
    cr.new_path()
    u = h
    x = x0
    cr.move_to(x, y + h / 2)
    while x + u * 2 <= x1:
        cr.line_to(x, y - h / 2)
        cr.line_to(x + u, y - h / 2)
        cr.line_to(x + u, y + h * 0.15)
        cr.line_to(x + u * 0.45, y + h * 0.15)
        cr.line_to(x + u * 0.45, y - h * 0.1)
        cr.move_to(x + u, y + h / 2)
        cr.line_to(x + u * 2, y + h / 2)
        x += u * 2
        cr.move_to(x, y + h / 2)
    cr.set_line_width(width)
    cr.set_source_rgba(*c, a)
    cr.stroke()


def shou(cr, x, y, r, c, width=1.1, a=1.0):
    """A round longevity emblem: a ring around a knotted meander."""
    def path():
        cr.new_path()
        cr.arc(x, y, r, 0, TAU)
        q = r * 0.62
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):   # an angular hook in each quarter
            cr.move_to(x + sx * q * 0.15, y + sy * q * 0.15)
            cr.line_to(x + sx * q * 0.15, y + sy * q)
            cr.line_to(x + sx * q, y + sy * q)
            cr.line_to(x + sx * q, y + sy * q * 0.45)
            cr.line_to(x + sx * q * 0.5, y + sy * q * 0.45)
        cr.move_to(x - q, y)
        cr.line_to(x + q, y)
        cr.move_to(x, y - q)
        cr.line_to(x, y + q)
    cr.save()
    cr.set_line_join(cairo.LINE_JOIN_MITER)
    neon(cr, path, c, width, a)
    cr.restore()


# ═══════════════════════════════════════════════════════════ Graffiti
SPRAY = ['#25ebf5', '#eb1fed', '#ffe014', '#3aff6a', '#ff2a5a', '#3a8cff']


def splat(cr, x, y, r, c, rnd, a=1.0, drips=0, spikes=14):
    """A paint splat: a blob with spikes, droplets flung around it and
    drips running down."""
    pts = []
    for k in range(spikes * 2):
        ang = k / (spikes * 2) * TAU
        rr = r * (rnd.uniform(1.15, 1.6) if k % 2 == 0 and rnd.random() < 0.55 else rnd.uniform(0.7, 0.95))
        pts.append((x + math.cos(ang) * rr, y + math.sin(ang) * rr))
    _curve(cr, pts, True)
    cr.set_source(_radial(x, y, r * 1.4, _mix(c, (1, 1, 1), 0.3), c, a, a))
    cr.fill()
    for _ in range(int(spikes * 0.6)):   # droplets
        ang, d = rnd.uniform(0, TAU), r * rnd.uniform(1.5, 2.4)
        cr.arc(x + math.cos(ang) * d, y + math.sin(ang) * d, r * rnd.uniform(0.06, 0.16), 0, TAU)
        cr.set_source_rgba(*c, a)
        cr.fill()
    for _ in range(drips):
        w3.drip(cr, x + rnd.uniform(-r * 0.6, r * 0.6), y + r * 0.5, r * rnd.uniform(0.8, 2.2), r * 0.13, c, a)


def spray(cr, path, c, width, rnd, a=1.0, speckle=True):
    """A sprayed line along path(): soft overspray, a solid core and
    loose speckles of paint around it."""
    for lw, al in ((width * 3.6, 0.07), (width * 2.0, 0.16), (width, 0.95)):
        path()
        cr.set_line_width(lw)
        cr.set_source_rgba(*c, al * a)
        cr.stroke()
    if speckle:
        path()
        for px, py in _sample(cr, 3.0)[::2]:
            if rnd.random() < 0.5:
                cr.arc(px + rnd.gauss(0, width * 1.4), py + rnd.gauss(0, width * 1.4), rnd.uniform(0.2, 0.6), 0, TAU)
                cr.set_source_rgba(*c, rnd.uniform(0.3, 0.8) * a)
                cr.fill()


def crown(cr, x, y, s, c, width=1.2, a=1.0, rnd=None):
    """A hand-drawn street crown (s = its width), resting on (x, y)."""
    rnd = rnd or random.Random(7)

    def j(v):
        return v + rnd.uniform(-0.6, 0.6)
    pts = [(x - s * 0.5, y), (x - s * 0.55, y - s * 0.62), (x - s * 0.25, y - s * 0.3), (x, y - s * 0.78),
           (x + s * 0.25, y - s * 0.3), (x + s * 0.55, y - s * 0.62), (x + s * 0.5, y)]
    pts = [(j(px), j(py)) for px, py in pts]

    def path():
        _poly(cr, pts, True)
        for px, py in (pts[1], pts[3], pts[5]):
            cr.new_sub_path()
            cr.arc(px, py - s * 0.08, s * 0.07, 0, TAU)
    cr.save()
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    neon(cr, path, c, width, a)
    cr.restore()


def spray_can(cr, x, y, s, c, a=1.0):
    """A spray can standing on (x, y) (s = its height)."""
    w = s * 0.38
    rounded(cr, x - w / 2, y - s * 0.8, w, s * 0.8, w * 0.18)
    g = cairo.LinearGradient(x - w / 2, 0, x + w / 2, 0)
    g.add_color_stop_rgba(0, *_mix(c, (0, 0, 0), 0.5), a)
    g.add_color_stop_rgba(0.35, *_mix(c, (1, 1, 1), 0.35), a)
    g.add_color_stop_rgba(1, *_mix(c, (0, 0, 0), 0.6), a)
    cr.set_source(g)
    cr.fill()
    cr.rectangle(x - w / 2, y - s * 0.55, w, s * 0.2)
    cr.set_source_rgba(0.9, 0.9, 0.95, 0.8 * a)
    cr.fill()
    cr.new_path()   # shoulder, cap and nozzle
    cr.move_to(x - w / 2, y - s * 0.8)
    cr.curve_to(x - w / 2, y - s * 0.92, x + w / 2, y - s * 0.92, x + w / 2, y - s * 0.8)
    cr.close_path()
    cr.set_source_rgba(0.55, 0.55, 0.6, a)
    cr.fill()
    cr.rectangle(x - w * 0.18, y - s * 1.0, w * 0.36, s * 0.1)
    cr.set_source_rgba(*c, a)
    cr.fill()
    w3.drip(cr, x - w * 0.2, y - s * 0.8, s * 0.3, w * 0.08, c, a)


def bricks(cr, x0, y0, w, h, c, rnd, bw=34, bh=14, a=1.0):
    """A wall of bricks, each a little different."""
    for row in range(int(h / bh) + 2):
        off = (bw / 2) if row % 2 else 0
        for col in range(-1, int(w / bw) + 2):
            bx, by = x0 + col * bw + off, y0 + row * bh
            rounded(cr, bx + 1, by + 1, bw - 2, bh - 2, 1.5)
            k = rnd.uniform(-0.25, 0.2)
            cr.set_source_rgba(*_mix(c, (0, 0, 0) if k < 0 else (1, 1, 1), abs(k)), a)
            cr.fill()


# ═══════════════════════════════════════════════════════════ the styles
ws.STYLES += [
    ('halloween', 'Halloween', 'pumpkins, bats and a full moon'),
    ('desert', 'Desert', 'sunset, cacti and sand'),
    ('neotokyo', 'Neo Tokyo', 'neon city, torii and sakura'),
    ('abyss', 'Abyss', 'jellyfish and deep sea light'),
    ('forest', 'Enchanted Forest', 'mushrooms, fireflies and moss'),
    ('cosmos', 'Cosmos', 'planets, nebulae and stardust'),
    ('samurai', 'Samurai', 'blood moon, katana and sakura'),
    ('steampunk', 'Steampunk', 'brass gears, steam and airships'),
    ('glacier', 'Glacier', 'ice crystals and a frost wolf'),
    ('witch', 'Witchcraft', 'spellbooks, ravens and candles'),
    ('dragon', 'Golden Dragon', 'imperial gold among the clouds'),
    ('graffiti', 'Graffiti', 'spray paint and street crowns'),
]
ws.STYLE_IDS = [s[0] for s in ws.STYLES]
ws.COLORS.update({
    'halloween': ('#ffb347', '#ff8a1f', ['#ff7a1a', '#ff8a2a', '#ff9a3a', '#ffb347']),
    'desert': ('#ffd25a', '#ffc23a', ['#ffb52e', '#ffbe3a', '#ffc84a', '#ffd25a']),
    'neotokyo': ('#f070ff', '#c84dff', ['#b44dff', '#c84dff', '#dc4dff', '#ff4de0']),
    'abyss': ('#5ae8ff', '#3ad0ff', ['#2aa8ff', '#2ab8ff', '#2ac8ff', '#3ad8ff']),
    'forest': ('#c8ff5a', '#b0f02a', ['#9ce02e', '#a8e82e', '#b4f02e', '#c8ff5a']),
    'cosmos': ('#a8b0ff', '#8a90ff', ['#6a7aff', '#7a84ff', '#8a8eff', '#9a98ff']),
    'samurai': ('#ff5a4a', '#ff3a2a', ['#ff2a2a', '#ff3a30', '#ff4a38', '#ff5a40']),
    'steampunk': ('#ffb45a', '#ffa030', ['#e8903a', '#f09a3a', '#f8a83a', '#ffb84a']),
    'glacier': ('#7ae0ff', '#5ac8ff', ['#3ab0ff', '#4ac0ff', '#5ad0ff', '#7ae0ff']),
    'witch': ('#d070ff', '#c050ff', ['#a03cff', '#b43cff', '#c84cff', '#e060ff']),
    'dragon': ('#ffc84a', '#ffb02e', ['#ffa02a', '#ffae2e', '#ffbc34', '#ffca3a']),
    'graffiti': ('#25ebf5', '#eb1fed', ['#25ebf5', '#ffe014', '#3aff6a', '#ff2a8a']),
})
ws.GLOW.update({'halloween': 0.55, 'desert': 0.5, 'neotokyo': 0.55, 'abyss': 0.55, 'forest': 0.5, 'cosmos': 0.5,
                'samurai': 0.55, 'steampunk': 0.45, 'glacier': 0.5, 'witch': 0.55, 'dragon': 0.5, 'graffiti': 0.55})
ws.NATIVE.update({'halloween': '#ff7a1a', 'desert': '#ffb52e', 'neotokyo': '#e03cff', 'abyss': '#2ccfff',
                  'forest': '#b8f02e', 'cosmos': '#6a6cff', 'samurai': '#ff3a3a', 'steampunk': '#f0a13a',
                  'glacier': '#4fc8ff', 'witch': '#b43cff', 'dragon': '#ffb22e', 'graffiti': '#eb1fed'})


# ─────────────────────────────────────────────────────────── shared parts
def _dark(cr, x, y, w, h, col, a=0.93, shape=None):
    (shape or (lambda: rounded(cr, x, y, w, h, h / 2)))()
    cr.set_source_rgba(*rgb(col), a)
    cr.fill()


def _inner(cr, x, y, w, h, c, a=0.55, inset=3.0, width=0.9):
    """A thin glowing line just inside a capsule (the lit inner edge)."""
    for extra, al in ((3, 0.12), (0, 1.0)):
        rounded(cr, x + inset, y + inset, w - 2 * inset, h - 2 * inset, (h - 2 * inset) / 2)
        cr.set_line_width(width + extra)
        cr.set_source_rgba(*c, al * a)
        cr.stroke()


def _ring(x, y, w, h, amp, waves, phase, step=3.0):
    ring = w3.wavy_ring(x, y, w, h, amp, waves, phase, step)
    return [(px, py) for px, py, _a, _b in ring] + [(ring[0][0], ring[0][1])]


def _gnarl(cr, x, y, w, h, waves, glow_a=0.15):
    """Two twisting roots round a capsule, lit orange from inside."""
    bark, rim, orange = rgb('#1a0c08'), rgb('#ff8a2a'), rgb('#ff6a10')
    for amp, k, ph0, wd in ((1.8, 1.0, 0.0, 3.4), (2.2, 0.72, 2.2, 2.4)):
        pts = _ring(x - 1, y - 1, w + 2, h + 2, amp, max(3, round(waves * k)), ph0, 3)
        w3.tube(cr, pts, [wd] * len(pts), bark, rim, orange, glow_a)


def _vines(cr, x, y, w, h, waves, rnd, leaves=True):
    """Two mossy branches wound round a capsule, leaves sprouting."""
    for amp, k, ph0, wd in ((1.6, 1.0, 0.0, 3.2), (2.0, 0.7, 2.4, 2.4)):
        pts = _ring(x - 1, y - 1, w + 2, h + 2, amp, max(3, round(waves * k)), ph0, 3)
        vine(cr, pts, wd, rnd, leaves=leaves)


def _thorny(cr, x, y, w, h, waves, rnd):
    """Black thorn vines round a capsule, a violet light on them."""
    dark, rim, violet = rgb('#120820'), rgb('#c060ff'), rgb('#9a2cff')
    for amp, k, ph0, wd in ((1.7, 1.0, 0.5, 2.8), (2.1, 0.7, 2.7, 2.0)):
        pts = _ring(x - 1, y - 1, w + 2, h + 2, amp, max(3, round(waves * k)), ph0, 3)
        w3.tube(cr, pts, [wd] * len(pts), dark, rim, violet, 0.14)
        thorns(cr, pts, rnd, _mix(dark, rim, 0.25), every=7, size=2.6)


def _crust(cr, x, y, w, h, seed, c, width=3.6):
    """A rough crust of rock and coral round a capsule, barnacles on it."""
    rnd = random.Random(seed)
    pts = ws.capsule_points(x, y, w, h, 3)
    path = lambda: ws.jagged(cr, pts, random.Random(seed), 1.3, smooth=1)  # noqa: E731
    for lw, col, al in ((width + 3, (0, 0, 0), 0.5), (width, _mix(c, (0.02, 0.06, 0.14), 0.75), 1.0),
                        (width * 0.35, _mix(c, (1, 1, 1), 0.1), 0.55)):
        path()
        cr.set_line_width(lw)
        cr.set_source_rgba(*col, al)
        cr.stroke()
    for px_, py_, nx, ny in pts[::5]:
        if rnd.random() < 0.45:
            r = rnd.uniform(0.7, 1.6)
            cr.arc(px_ + nx * rnd.uniform(-1, 1.5), py_ + ny * rnd.uniform(-1, 1.5), r, 0, TAU)
            cr.set_source_rgba(*_mix(c, (1, 1, 1), 0.35), rnd.uniform(0.35, 0.8))
            cr.fill()


def _wood(cr, path, width, a=1.0):
    """A wooden rim along path(): dark edge, plank, grain highlight."""
    wood, dark, light = rgb('#7a4420'), rgb('#200e04'), rgb('#c88a4a')
    for lw, col, al in ((width + 2.4, dark, 0.95), (width, wood, 1.0), (width * 0.3, light, 0.55)):
        path()
        cr.set_line_width(lw)
        cr.set_source_rgba(*col, al * a)
        cr.stroke()
    path()
    cr.set_dash([7, 5, 2, 6], 0)   # grain
    cr.set_line_width(width * 0.15)
    cr.set_source_rgba(*dark, 0.6 * a)
    cr.stroke()
    cr.set_dash([])


def _ice_rim(cr, x, y, w, h, rnd, peaks=True, icicles=True, size=1.0):
    """A frozen rim: translucent ice, crystal peaks on top, icicles below."""
    ice, white = rgb('#4fc8ff'), (0.92, 0.98, 1)
    path = lambda: rounded(cr, x, y, w, h, h / 2)  # noqa: E731
    for lw, col, al in ((7, ice, 0.12), (4, ice, 0.3), (2.2, _mix(ice, white, 0.4), 0.85), (0.8, white, 0.95)):
        path()
        cr.set_line_width(lw)
        cr.set_source_rgba(*col, al)
        cr.stroke()
    if peaks:
        px_ = x + h * 0.6
        while px_ < x + w - h * 0.6:
            hh = rnd.uniform(3, 7) * size
            ice_shard(cr, px_, y + 1.2, hh * 0.55, hh, rnd.uniform(-0.25, 0.25), ice, 0.9)
            px_ += rnd.uniform(7, 22) * size
    if icicles:
        px_ = x + h * 0.6
        while px_ < x + w - h * 0.6:
            icicle(cr, px_, y + h - 0.5, rnd.uniform(2.5, 6) * size, rnd.uniform(1.6, 2.6) * size, ice, 0.9)
            px_ += rnd.uniform(6, 18) * size


def _seams(cr, x, y, w, h, c, every=26, a=0.2):
    """Hull panel seams inside a capsule."""
    cr.save()
    rounded(cr, x, y, w, h, h / 2)
    cr.clip()
    k = x + h / 2
    cr.set_line_width(0.7)
    while k < x + w:
        cr.move_to(k, y)
        cr.line_to(k, y + h)
        k += every
    cr.move_to(x, y + h * 0.5)
    cr.line_to(x + w, y + h * 0.5)
    cr.set_source_rgba(*c, a)
    cr.stroke()
    cr.restore()


def _chamfer(cr, x, y, w, h, c):
    cr.new_path()
    cr.move_to(x + c, y)
    cr.line_to(x + w - c, y)
    cr.line_to(x + w, y + h / 2)
    cr.line_to(x + w - c, y + h)
    cr.line_to(x + c, y + h)
    cr.line_to(x, y + h / 2)
    cr.close_path()


def _neon_split(cr, path, x, y, w, h, top, bottom, width=1.4, dash=None):
    """A neon rim whose top half is one color and bottom half another, in
    broken strips like the signs of the city."""
    for (cy0, cy1), col in (((y - 20, y + h / 2), top), ((y + h / 2, y + h + 20), bottom)):
        cr.save()
        cr.rectangle(x - 30, cy0, w + 60, cy1 - cy0)
        cr.clip()
        neon(cr, path, col, width, 0.35)
        if dash:
            cr.set_dash(dash, 0)
        neon(cr, path, col, width, 1.0)
        cr.set_dash([])
        cr.restore()


def _gold_rim(cr, path_outer, path_inner, a=1.0):
    gold, light, dark = rgb(GOLD), rgb(GOLD_LIGHT), rgb(GOLD_DARK)
    for lw, col, al in ((6, gold, 0.12), (3.2, dark, 0.95), (2.0, gold, 1.0), (0.7, light, 0.9)):
        path_outer()
        cr.set_line_width(lw)
        cr.set_source_rgba(*col, al * a)
        cr.stroke()
    path_inner()
    cr.set_line_width(0.8)
    cr.set_source_rgba(*gold, 0.75 * a)
    cr.stroke()


def _spray_rim(cr, x, y, w, h, rnd, splats=True, drip_k=1.0, size=1.0):
    """A sprayed outline (cyan and a magenta echo), paint splats on it and
    drips running down from the bottom."""
    path = lambda: rounded(cr, x, y, w, h, h / 2)  # noqa: E731
    cr.save()
    cr.translate(1.2, 1.0)
    spray(cr, path, rgb('#eb1fed'), 1.1, rnd, 0.75, speckle=False)
    cr.restore()
    spray(cr, path, rgb('#25ebf5'), 1.4, rnd)
    if splats:
        for px_, py_, nx, ny in ws.capsule_points(x, y, w, h, 9 * size)[::3]:
            if rnd.random() < 0.38:
                col = rgb(rnd.choice(SPRAY))
                splat(cr, px_ + nx * 0.5, py_ + ny * 0.5, rnd.uniform(1.6, 3.4) * size, col, rnd, 0.9, spikes=9)
                if ny > 0.5 and rnd.random() < 0.7 * drip_k:
                    w3.drip(cr, px_, py_ + 1, rnd.uniform(3, 9) * size, 0.9 * size, col, 0.9)


# ─────────────────────────────────────────────────────────── pill frames
def _geo(m):
    px, py, pw, ph = ws.pill_rect(m)
    return px, py, pw, ph, m['win_w'], m['win_h'], m['win_h'] / 2, m['side']


def frame_halloween(cr, m):
    px, py, pw, ph, W, Hh, cy, sd = _geo(m)
    rnd = random.Random(31)
    halo(cr, px + pw / 2, cy, pw * 0.55, rgb('#a83a08'), 0.22)
    halo(cr, px + pw + sd * 0.6, cy - 4, ph * 1.6, rgb('#9a3cff'), 0.28)
    moon(cr, px + pw + sd * 0.64, cy - 5, ph * 0.28, rgb('#ff6ad5'), glow=0.3)
    for bx, by, bs, fl, ang in ((sd * 0.34, -9, 7.5, 0.9, -0.15), (sd * 0.86, 3, 5, 0.25, 0.2),
                                (sd * 0.52, 9, 4, 0.6, 0.1)):
        bat(cr, px + pw + bx, cy + by, bs, ang, fl)
    tombstone(cr, px + pw + sd * 0.2, Hh - 1, 7, 13, rgb('#1c1024'), rgb('#9a3cff'), cross=True)
    _dark(cr, px, py, pw, ph, '#0c0610')
    _gnarl(cr, px, py, pw, ph, max(5, pw / 34))
    _inner(cr, px, py, pw, ph, rgb('#ff7a1a'), 0.6)
    for tx, ang in ((px + ph * 0.3, -2.3), (px + pw - ph * 0.4, -0.7)):   # twigs off the roots
        pts = [(tx + math.cos(ang) * k * 2.2 + math.sin(k) * 0.6, py + 2 + math.sin(ang) * k * 2.2) for k in range(7)]
        branch(cr, pts, 1.8, 0.5, rgb('#1a0c08'))
    candle(cr, px - sd * 0.8, Hh - 3, 11, 4.2)
    pumpkin(cr, px - sd * 0.4, cy + 4, ph * 0.36, lit=1.0)
    for _ in range(10):   # embers in the air
        cr.arc(rnd.uniform(4, W - 4), rnd.uniform(3, Hh - 3), rnd.uniform(0.4, 0.9), 0, TAU)
        cr.set_source_rgba(*rgb(rnd.choice(('#ff8a2a', '#ffc43d'))), rnd.uniform(0.4, 0.9))
        cr.fill()


def frame_desert(cr, m):
    px, py, pw, ph, W, Hh, cy, sd = _geo(m)
    sun_disc(cr, px - sd * 0.55, cy - 3, ph * 0.32)
    halo(cr, px + pw / 2, cy, pw * 0.55, rgb('#a85a10'), 0.2)
    cactus(cr, px - sd * 0.24, Hh - 1, ph * 0.95, arms=((-1, 0.45, 0.3), (1, 0.62, 0.22)))
    tumbleweed(cr, px - sd * 0.82, Hh - 6, 5, rgb('#b8844a'), seed=3)
    _dark(cr, px, py, pw, ph, '#180a04')
    _wood(cr, lambda: rounded(cr, px, py, pw, ph, ph / 2), 3.6)
    for k in range(int(pw / 30) + 1):   # nails along the boards
        nx_ = px + ph / 2 + k * (pw - ph) / max(1, int(pw / 30))
        for ny_ in (py, py + ph):
            cr.arc(nx_, ny_, 0.9, 0, TAU)
            cr.set_source_rgba(0.75, 0.7, 0.6, 0.9)
            cr.fill()
    _inner(cr, px, py, pw, ph, rgb('#ffb52e'), 0.55, inset=3.6)
    bull_skull(cr, px + pw + sd * 0.42, cy + 1, ph * 0.72, glow=rgb('#ffb52e'))
    cactus(cr, px + pw + sd * 0.86, Hh - 1, ph * 0.6, arms=((-1, 0.5, 0.25),))


def frame_neotokyo(cr, m):
    px, py, pw, ph, W, Hh, cy, sd = _geo(m)
    rnd = random.Random(41)
    magenta, pink, cyan = rgb('#e03cff'), rgb('#ff3ab4'), rgb('#3ad8ff')
    halo(cr, px - sd * 0.4, cy, ph * 1.4, magenta, 0.22)
    halo(cr, px + pw + sd * 0.4, cy, ph * 1.4, rgb('#3a6bff'), 0.22)
    skyline(cr, px - sd * 0.2, px + 4, Hh - 2, 5, Hh * 0.45, rnd, a=0.9, step=(4, 7), win=1.2)
    skyline(cr, px + pw - 4, px + pw + sd * 0.25, Hh - 2, 5, Hh * 0.45, rnd, a=0.9, step=(4, 7), win=1.2)
    torii(cr, px + pw + sd * 0.55, Hh - 1, ph * 0.95, ph * 0.85, rgb('#140620'), pink)
    c = ph * 0.42
    path = lambda: _chamfer(cr, px, py, pw, ph, c)  # noqa: E731
    _dark(cr, px, py, pw, ph, '#0a0620', 0.94, path)
    _neon_split(cr, path, px, py, pw, ph, pink, cyan, 1.3, dash=[18, 4, 6, 4])
    bx, by = px - sd * 0.42, cy - 15   # the vertical neon sign: 未来, the future
    rounded(cr, bx - 1, by - 1, 15, 31, 2)
    cr.set_source_rgba(*rgb('#12062a'), 0.95)
    cr.fill()
    neon(cr, lambda: rounded(cr, bx - 1, by - 1, 15, 31, 2), pink, 0.9, 0.9)
    kanji(cr, 'mi', bx + 1.2, by + 1.5, 10.5, pink, 0.9)
    kanji(cr, 'rai', bx + 1.2, by + 15.5, 10.5, pink, 0.9)
    blossom_branch(cr, px + pw - c * 0.7, py + 1, 30, -0.4, random.Random(5), n=6)
    for _ in range(6):
        petal(cr, rnd.uniform(px + pw, W - 4), rnd.uniform(4, Hh - 4), rnd.uniform(2, 3.2), rnd.uniform(0, 3))


def frame_abyss(cr, m):
    px, py, pw, ph, W, Hh, cy, sd = _geo(m)
    rnd = random.Random(43)
    cyan, deep = rgb('#2ccfff'), rgb('#0a3a8a')
    halo(cr, px + pw / 2, cy, pw * 0.6, deep, 0.35)
    seaweed(cr, px - sd * 0.18, Hh, ph * 0.7, rgb('#2affc8'), 0.4)
    seaweed(cr, px - sd * 0.08, Hh, ph * 0.5, rgb('#1ab890'), 2.0)
    coral(cr, px + pw + sd * 0.15, Hh, ph * 0.55, rgb('#ff5a9a'), random.Random(3), depth=2)
    _dark(cr, px, py, pw, ph, '#020c1e')
    _crust(cr, px, py, pw, ph, 7, rgb('#2ccfff'))
    _inner(cr, px, py, pw, ph, cyan, 0.5, inset=3.4)
    jellyfish(cr, px - sd * 0.52, cy - 6, ph * 0.5, rgb('#5ab8ff'), 0.3)
    jellyfish(cr, px - sd * 0.86, cy + 2, ph * 0.26, rgb('#b07cff'), 1.7, 0.85)
    base, rim = rgb('#06142a'), rgb('#3ad8ff')
    for i in range(3):   # tentacles curling out of the right end
        ang = rnd.uniform(-0.7, 0.7)
        L = rnd.uniform(sd * 0.45, sd * 0.75)
        pts = [(px + pw - 4 + math.cos(ang) * L * t / 17 + math.sin(t / 2.6 + i * 2) * 3.5 * t / 17,
                cy + math.sin(ang) * L * t / 17 * 0.45 + math.cos(t / 2.2 + i) * 3 * t / 17) for t in range(18)]
        tentacle(cr, pts, 3.6, base, rim, cyan)
    for _ in range(8):
        bubble(cr, rnd.uniform(px + pw + 6, W - 3), rnd.uniform(3, Hh - 4), rnd.uniform(0.8, 2.0), cyan, 0.8)


def frame_forest(cr, m):
    px, py, pw, ph, W, Hh, cy, sd = _geo(m)
    rnd = random.Random(47)
    lime, yellow = rgb('#b8f02e'), rgb('#ffe066')
    halo(cr, px + pw / 2, cy, pw * 0.55, rgb('#3a6a08'), 0.28)
    halo(cr, px - sd * 0.5, Hh, ph, rgb('#ff6a3a'), 0.15)
    _dark(cr, px, py, pw, ph, '#050d04')
    _vines(cr, px, py, pw, ph, max(5, pw / 32), rnd)
    _inner(cr, px, py, pw, ph, lime, 0.55, inset=3.4)
    mushroom(cr, px - sd * 0.62, Hh - 1, ph * 0.38)
    mushroom(cr, px - sd * 0.3, Hh - 1, ph * 0.62, tilt=0.08)
    mushroom(cr, px + pw + sd * 0.32, Hh - 1, ph * 0.5, tilt=-0.1)
    mushroom(cr, px + pw + sd * 0.56, Hh - 1, ph * 0.3, tilt=0.12)
    yb, ya = rgb('#ffe066'), rgb('#ffb000')
    w3.butterfly(cr, px - sd * 0.8, cy - 9, 6, -0.3, yb, ya)
    w3.butterfly(cr, px + pw + sd * 0.78, cy - 8, 7, 0.35, yb, ya)
    for _ in range(9):
        firefly(cr, rnd.choice((rnd.uniform(3, px - 6), rnd.uniform(px + pw + 6, W - 3))), rnd.uniform(3, Hh - 8),
                rnd.uniform(0.6, 1.1), yellow, rnd.uniform(0.6, 1))


def frame_cosmos(cr, m):
    px, py, pw, ph, W, Hh, cy, sd = _geo(m)
    violet, magenta = rgb('#6a6cff'), rgb('#c04dff')
    for fx, col in ((0.1, magenta), (0.9, rgb('#3a5aff'))):
        halo(cr, W * fx, cy, ph * 1.6, col, 0.25)
    ws.stars(cr, (0, 0, px, Hh), 16, 5, colors=('#ffffff', '#b8c0ff', '#ffb8f0'))
    ws.stars(cr, (px + pw, 0, sd, Hh), 16, 6, colors=('#ffffff', '#b8c0ff', '#ffb8f0'))
    path = lambda: rounded(cr, px, py, pw, ph, ph / 2)  # noqa: E731
    path()
    cr.set_source(_vgrad(py, py + ph, rgb('#141640'), rgb('#05061a'), 0.95))
    cr.fill()
    _seams(cr, px, py, pw, ph, rgb('#8a8cff'), 24, 0.16)
    lights(cr, px + ph * 0.6, px + pw - ph * 0.6, py + 2.2, random.Random(3), ['#ff3a6a', '#c04dff', '#8a8cff'],
           every=36, w=5, h=1.2)
    lights(cr, px + ph * 0.6, px + pw - ph * 0.6, py + ph - 2.2, random.Random(4), ['#c04dff', '#3ad8ff'],
           every=40, w=5, h=1.2)
    neon(cr, path, violet, 1.3, 0.95)
    helmet(cr, px - sd * 0.46, cy + 3, ph * 0.66)
    asteroid(cr, px - sd * 0.84, cy - 7, 3.5, random.Random(1))
    asteroid(cr, px + pw + sd * 0.88, cy + 9, 2.8, random.Random(2))
    planet(cr, px + pw + sd * 0.48, cy - 1, ph * 0.26, rgb('#9a8cff'), rgb('#3a2a9a'), ring_c=rgb('#d8b8ff'))


def frame_samurai(cr, m):
    px, py, pw, ph, W, Hh, cy, sd = _geo(m)
    rnd = random.Random(59)
    red = rgb('#ff2a2a')
    halo(cr, px + pw / 2, cy, pw * 0.55, rgb('#6a0010'), 0.3)
    moon(cr, px - sd * 0.58, cy - 5, ph * 0.32, rgb('#ff3a2a'), glow=0.4, craters=False)
    pagoda(cr, px - sd * 0.55, Hh, ph * 0.9, rgb('#12040a'), rgb('#ff6a3a'))
    blossom_branch(cr, px + 4, py + 2, 34, -2.6, random.Random(7), n=7)
    _dark(cr, px, py, pw, ph, '#0c0306')
    path = lambda: rounded(cr, px, py, pw, ph, ph / 2)  # noqa: E731
    for lw, col, al in ((5, (0, 0, 0), 0.6), (3.4, rgb('#1e0a0e'), 1.0), (0.8, rgb('#5a2028'), 0.9)):
        path()
        cr.set_line_width(lw)
        cr.set_source_rgba(*col, al)
        cr.stroke()
    for k in range(int(pw / 46) + 2):   # red-hot seams in the lacquer
        x0 = px + ph * 0.5 + rnd.uniform(0, pw - ph)
        side = rnd.choice((py + 0.8, py + ph - 0.8))
        pts = [(x0 + i * 2.2, side + math.sin(i * 1.7 + k) * 0.5) for i in range(int(rnd.uniform(4, 9)))]
        neon(cr, lambda: _poly(cr, pts), red, 0.8, 0.9, layers=((3, 0.15), (1.4, 0.4)))
    _inner(cr, px, py, pw, ph, red, 0.55, inset=3.2)
    katana(cr, px + pw - ph * 0.4, cy + ph * 0.42, -0.3, sd * 0.95)
    for _ in range(9):
        petal(cr, rnd.uniform(4, W - 4), rnd.uniform(3, Hh - 3), rnd.uniform(2, 3), rnd.uniform(0, 3),
              rgb(rnd.choice(('#ff8ab8', '#ffb0cc', '#ff6a9a'))), 0.9)


def frame_steampunk(cr, m):
    px, py, pw, ph, W, Hh, cy, sd = _geo(m)
    amber = rgb('#f0a13a')
    halo(cr, px + pw / 2, cy, pw * 0.55, rgb('#8a4a0a'), 0.25)
    steam(cr, px - sd * 0.6, 6, 7, 0.9, 3)
    steam(cr, px + pw + sd * 0.7, 7, 6, 0.8, 4)
    gear(cr, px - sd * 0.76, cy - 6, ph * 0.24, 8, 0.2)
    gear(cr, px - sd * 0.42, cy + 3, ph * 0.4, 12, 0.0, glow=amber)
    _dark(cr, px, py, pw, ph, '#0e0703')
    brass_path(cr, lambda: rounded(cr, px, py, pw, ph, ph / 2), 3.4)
    for k in range(int(pw / 22) + 1):   # rivets
        rx = px + ph / 2 + k * (pw - ph) / max(1, int(pw / 22))
        rivet(cr, rx, py, 1.1)
        rivet(cr, rx, py + ph, 1.1)
    for fx in (0.25, 0.75):   # flanges round the pipe
        fx_ = px + pw * fx
        for fy in (py, py + ph):
            rounded(cr, fx_ - 2, fy - 3.2, 4, 6.4, 1)
            cr.set_source(_vgrad(fy - 3, fy + 3, rgb('#ffd27a'), rgb('#6a3a12')))
            cr.fill()
    _inner(cr, px, py, pw, ph, amber, 0.45, inset=3.6)
    gauge(cr, px + pw + sd * 0.32, cy - 2, ph * 0.3, 0.5)
    airship(cr, px + pw + sd * 0.72, cy + 8, sd * 0.42)


def frame_glacier(cr, m):
    px, py, pw, ph, W, Hh, cy, sd = _geo(m)
    rnd = random.Random(67)
    ice = rgb('#4fc8ff')
    halo(cr, px + pw / 2, cy, pw * 0.6, rgb('#0a3a8a'), 0.3)
    crystal_cluster(cr, px - sd * 0.38, Hh - 1, ph * 0.95, ice, random.Random(2), n=5)
    crystal_cluster(cr, px - sd * 0.8, Hh - 1, ph * 0.45, ice, random.Random(9), n=3)
    path = lambda: rounded(cr, px, py, pw, ph, ph / 2)  # noqa: E731
    path()
    cr.set_source(_vgrad(py, py + ph, rgb('#0c2a4a'), rgb('#03101f'), 0.92))
    cr.fill()
    _ice_rim(cr, px, py, pw, ph, rnd)
    wolf(cr, px + pw + sd * 0.5, cy + 1, ph * 1.0, rgb('#1c3a66'), rgb('#9ae8ff'), rgb('#4fe0ff'))
    for _ in range(7):
        snowflake(cr, rnd.uniform(3, W - 3), rnd.uniform(3, Hh - 3), rnd.uniform(1.2, 2.2), rgb('#cdf6ff'),
                  rnd.uniform(0.5, 0.9), 0.5, rot=rnd.uniform(0, 1))


def frame_witch(cr, m):
    px, py, pw, ph, W, Hh, cy, sd = _geo(m)
    rnd = random.Random(71)
    violet = rgb('#b43cff')
    halo(cr, px + pw / 2, cy, pw * 0.55, rgb('#4a0a8a'), 0.3)
    halo(cr, px + pw + sd * 0.5, cy, ph * 1.2, violet, 0.2)
    pentagram(cr, px + pw / 2, cy, ph * 0.9, violet, 0.6, 0.18)
    spellbook(cr, px - sd * 0.46, Hh - 7, sd * 0.42)
    candle(cr, px - sd * 0.84, Hh - 2, 11, 3.8)
    candle(cr, px + pw + sd * 0.86, Hh - 2, 8, 3.4)
    _dark(cr, px, py, pw, ph, '#0a0418')
    _thorny(cr, px, py, pw, ph, max(5, pw / 34), rnd)
    _inner(cr, px, py, pw, ph, violet, 0.6, inset=3.2)
    raven(cr, px + pw + sd * 0.48, Hh - 3, ph * 0.95)
    for _ in range(10):   # sparks of magic
        x, y = rnd.uniform(3, W - 3), rnd.uniform(3, Hh - 3)
        if px - 2 < x < px + pw + 2:
            continue
        ws.sparkle(cr, x, y, rnd.uniform(1.0, 2.0), rgb(rnd.choice(('#e8b8ff', '#b43cff', '#ffffff'))), 0.85)


def frame_dragon(cr, m):
    px, py, pw, ph, W, Hh, cy, sd = _geo(m)
    rnd = random.Random(73)
    gold = rgb(GOLD)
    halo(cr, px + pw / 2, cy, pw * 0.55, rgb('#8a1a04'), 0.3)
    cloud_scroll(cr, px + pw + sd * 0.55, cy - 9, 12, rgb('#ffc42e'), 0.9)
    cloud_scroll(cr, px - sd * 0.85, cy + 8, 9, rgb('#ffc42e'), 0.75, flip=-1)
    _dark(cr, px, py, pw, ph, '#140604')
    _gold_rim(cr, lambda: rounded(cr, px, py, pw, ph, ph / 2),
              lambda: rounded(cr, px + 3, py + 3, pw - 6, ph - 6, (ph - 6) / 2))
    # the dragon: its tail on the right, the body along the bottom, the head
    # rising on the left towards the icons
    pts = [(px + pw + sd * 0.72, cy - 6), (px + pw + sd * 0.5, cy + 6), (px + pw + sd * 0.2, Hh - 4)]
    k = px + pw
    while k > px:
        pts.append((k, Hh - 3.2 + math.sin((k - px) / 9) * 0.9))
        k -= 6
    pts += [(px - sd * 0.15, Hh - 6), (px - sd * 0.38, cy + 4), (px - sd * 0.42, cy - 2), (px - sd * 0.3, cy - 6)]
    _curve(cr, pts)
    body = _sample(cr, 3.0)
    dragon_body(cr, body, 5.2, head_k=3.4)
    for _ in range(6):
        sakura(cr, rnd.uniform(3, W - 3), rnd.uniform(3, 9), rnd.uniform(1.4, 2.2), rgb('#ff6a8a'), rnd.uniform(0, 1))
    for _ in range(8):
        cr.arc(rnd.uniform(3, W - 3), rnd.uniform(3, Hh - 3), rnd.uniform(0.4, 0.8), 0, TAU)
        cr.set_source_rgba(*gold, rnd.uniform(0.4, 0.9))
        cr.fill()


def frame_graffiti(cr, m):
    px, py, pw, ph, W, Hh, cy, sd = _geo(m)
    rnd = random.Random(79)
    halo(cr, px + pw / 2, cy, pw * 0.55, rgb('#4a0a6a'), 0.3)
    splat(cr, px - sd * 0.55, cy + 2, 7, rgb('#ff2a5a'), random.Random(2), 0.9, drips=2)
    splat(cr, px + pw + sd * 0.5, cy + 4, 7, rgb('#ffe014'), random.Random(3), 0.9, drips=2)
    _dark(cr, px, py, pw, ph, '#0a0614')
    _spray_rim(cr, px, py, pw, ph, rnd)
    crown(cr, px - sd * 0.45, cy + 5, ph * 0.62, rgb('#eb1fed'), 1.1)
    skull(cr, px + pw + sd * 0.48, cy + 5, ph * 0.42, eyes=rgb('#25ebf5'))
    crown(cr, px + pw + sd * 0.48, cy - 3, ph * 0.45, rgb('#25ebf5'), 0.9)
    spray_can(cr, px - sd * 0.86, Hh - 1, ph * 0.62, rgb('#25ebf5'))


ws.FRAMES.update({'halloween': frame_halloween, 'desert': frame_desert, 'neotokyo': frame_neotokyo,
                  'abyss': frame_abyss, 'forest': frame_forest, 'cosmos': frame_cosmos, 'samurai': frame_samurai,
                  'steampunk': frame_steampunk, 'glacier': frame_glacier, 'witch': frame_witch,
                  'dragon': frame_dragon, 'graffiti': frame_graffiti})


# ─────────────────────────────────────────────────────────── bar skins
def _bar_fill(cr, x, y, w, h, col, a=0.93):
    ws._capsule(cr, x, y, w, h)
    cr.set_source_rgba(*rgb(col), a)
    cr.fill()


def _along(x, w, rnd, every, margin=24):
    """Random spots along a bar, every ~every px, away from its ends."""
    out = []
    k = x + margin + rnd.uniform(0, every)
    while k < x + w - margin:
        out.append(k)
        k += every * rnd.uniform(0.7, 1.4)
    return out


def bar_halloween(cr, x, y, w, h, cy):
    rnd = random.Random(131)
    for fx, col in ((0.05, '#ff6a10'), (0.5, '#7a2aff'), (0.95, '#ff6a10')):
        halo(cr, x + w * fx, cy, h * 2.2, rgb(col), 0.14)
    _bar_fill(cr, x, y, w, h, '#0c0610')
    _gnarl(cr, x, y, w, h, max(6, w / 36), 0.12)
    _inner(cr, x, y, w, h, rgb('#ff7a1a'), 0.5)
    for bx in _along(x, w, rnd, 260, 60):   # bats over the top edge
        bat(cr, bx, max(4, y - 1), rnd.uniform(4.5, 6.5), rnd.uniform(-0.3, 0.3), rnd.uniform(0.2, 1.0))
    pumpkin(cr, x + 2, cy + 2, h * 0.36)
    skull(cr, x + w + 6, cy + 1, h * 0.46, eyes=rgb('#ff8a2a'))
    candle(cr, x - 14, y + h, 9, 3.4)


def bar_desert(cr, x, y, w, h, cy):
    rnd = random.Random(137)
    halo(cr, x - 6, cy, h * 2.4, rgb('#ff8a1a'), 0.25)
    halo(cr, x + w * 0.5, cy, h * 3, rgb('#a85a10'), 0.12)
    _bar_fill(cr, x, y, w, h, '#180a04')
    path = lambda: ws._capsule(cr, x, y, w, h)  # noqa: E731
    _wood(cr, path, 3.4)
    for nx_ in _along(x, w, rnd, 34, h * 0.6):   # nails
        for ny_ in (y, y + h):
            cr.arc(nx_, ny_, 0.9, 0, TAU)
            cr.set_source_rgba(0.75, 0.7, 0.6, 0.9)
            cr.fill()
    _inner(cr, x, y, w, h, rgb('#ffb52e'), 0.45, inset=3.4)
    cactus(cr, x - 6, y + h + 3, h * 1.05, arms=((-1, 0.45, 0.28), (1, 0.62, 0.22)))
    bull_skull(cr, x + w + 10, cy + 1, h * 0.62, glow=rgb('#ffb52e'))
    tumbleweed(cr, x + w * 0.5 + rnd.uniform(-60, 60), y + h + 1, 4, rgb('#b8844a'), 0.8, 5)


def bar_neotokyo(cr, x, y, w, h, cy):
    rnd = random.Random(139)
    pink, cyan, magenta = rgb('#ff3ab4'), rgb('#3ad8ff'), rgb('#e03cff')
    halo(cr, x, cy, h * 2.2, magenta, 0.16)
    halo(cr, x + w, cy, h * 2.2, rgb('#3a6bff'), 0.16)
    skyline(cr, x - 12, x + 10, y + h + 2, 4, h * 0.55, rnd, a=0.9, step=(4, 7), win=1.2)
    skyline(cr, x + w - 10, x + w + 12, y + h + 2, 4, h * 0.55, rnd, a=0.9, step=(4, 7), win=1.2)
    path = lambda: ws._capsule(cr, x, y, w, h)  # noqa: E731
    _bar_fill(cr, x, y, w, h, '#0a0620', 0.94)
    _neon_split(cr, path, x, y, w, h, pink, cyan, 1.2, dash=[26, 5, 8, 5])
    rounded(cr, x + 4, y + 3, 9, h - 6, 1.5)   # a small vertical sign at the left end
    cr.set_source_rgba(*rgb('#12062a'), 0.95)
    cr.fill()
    if h > 22:
        kanji(cr, 'mi', x + 5, y + 4.5, 7, pink, 0.7)
        kanji(cr, 'rai', x + 5, y + h * 0.5, 7, pink, 0.7)
    torii(cr, x + w + 6, y + h + 2, h * 0.8, h * 0.72, rgb('#140620'), pink)
    blossom_branch(cr, x + w - h * 0.4, y + 1, 26, -0.6, random.Random(9), n=5)
    for px_ in _along(x, w, rnd, 160, 40):
        petal(cr, px_, max(3, y - rnd.uniform(0, 3)), rnd.uniform(1.8, 2.8), rnd.uniform(0, 3))


def bar_abyss(cr, x, y, w, h, cy):
    rnd = random.Random(149)
    cyan = rgb('#2ccfff')
    for fx in (0.1, 0.5, 0.9):
        halo(cr, x + w * fx, cy, h * 2.4, rgb('#0a3a8a'), 0.2)
    _bar_fill(cr, x, y, w, h, '#020c1e')
    _crust(cr, x, y, w, h, 11, cyan, 3.2)
    _inner(cr, x, y, w, h, cyan, 0.45, inset=3.2)
    jellyfish(cr, x - 2, cy - 3, h * 0.5, rgb('#5ab8ff'), 0.4)
    base, rim = rgb('#06142a'), rgb('#3ad8ff')
    for i in range(3):   # an octopus arm out of the right end
        ang = rnd.uniform(-0.6, 0.6)
        L = rnd.uniform(20, 34)
        pts = [(x + w - 4 + math.cos(ang) * L * t / 15 + math.sin(t / 2.4 + i * 2) * 3 * t / 15,
                cy + math.sin(ang) * L * t / 15 * 0.45 + math.cos(t / 2 + i) * 2.5 * t / 15) for t in range(16)]
        tentacle(cr, pts, 3.2, base, rim, cyan)
    for bx in _along(x, w, rnd, 90, 30):   # bubbles over the top edge
        bubble(cr, bx, max(2.5, y - rnd.uniform(0, 4)), rnd.uniform(0.9, 1.9), cyan, 0.8)


def bar_forest(cr, x, y, w, h, cy):
    rnd = random.Random(151)
    for fx in (0.05, 0.5, 0.95):
        halo(cr, x + w * fx, cy, h * 2.2, rgb('#3a6a08'), 0.16)
    _bar_fill(cr, x, y, w, h, '#050d04')
    _vines(cr, x, y, w, h, max(6, w / 34), rnd)
    _inner(cr, x, y, w, h, rgb('#b8f02e'), 0.45, inset=3.2)
    mushroom(cr, x - 2, y + h + 2, h * 0.62, tilt=0.12)
    mushroom(cr, x - 14, y + h + 2, h * 0.38, tilt=-0.1)
    mushroom(cr, x + w + 6, y + h + 2, h * 0.5, tilt=-0.1)
    w3.butterfly(cr, x + w + 16, cy - 6, 6, 0.35, rgb('#ffe066'), rgb('#ffb000'))
    for fx_ in _along(x, w, rnd, 70, 20):
        firefly(cr, fx_, max(2.5, y - rnd.uniform(-2, 4)), rnd.uniform(0.6, 1.0), rgb('#ffe066'), rnd.uniform(0.5, 1))


def bar_cosmos(cr, x, y, w, h, cy):
    violet = rgb('#6a6cff')
    for fx, col in ((0.05, '#c04dff'), (0.5, '#3a3aaa'), (0.95, '#3a5aff')):
        halo(cr, x + w * fx, cy, h * 2.2, rgb(col), 0.15)
    ws.stars(cr, (x - 20, 0, w + 40, y + h + 8), int(w / 18), 7, colors=('#ffffff', '#b8c0ff', '#ffb8f0'))
    path = lambda: ws._capsule(cr, x, y, w, h)  # noqa: E731
    path()
    cr.set_source(_vgrad(y, y + h, rgb('#141640'), rgb('#05061a'), 0.95))
    cr.fill()
    _seams(cr, x, y, w, h, rgb('#8a8cff'), 30, 0.12)
    lights(cr, x + h * 0.6, x + w - h * 0.6, y + 2.2, random.Random(3), ['#ff3a6a', '#c04dff', '#8a8cff'],
           every=60, w=6, h=1.2)
    lights(cr, x + h * 0.6, x + w - h * 0.6, y + h - 2.2, random.Random(4), ['#c04dff', '#3ad8ff'],
           every=70, w=6, h=1.2)
    neon(cr, path, violet, 1.2, 0.95)
    planet(cr, x + w + 10, cy, h * 0.24, rgb('#9a8cff'), rgb('#3a2a9a'), ring_c=rgb('#d8b8ff'))
    helmet(cr, x - 4, cy + 1, h * 0.6)


def bar_samurai(cr, x, y, w, h, cy):
    rnd = random.Random(163)
    red = rgb('#ff2a2a')
    for fx in (0.05, 0.5, 0.95):
        halo(cr, x + w * fx, cy, h * 2.2, rgb('#6a0010'), 0.18)
    moon(cr, x - 14, cy - 3, h * 0.26, rgb('#ff3a2a'), glow=0.35, craters=False)
    blossom_branch(cr, x + h * 0.3, y + 2, 28, -2.95, random.Random(11), n=6)
    _bar_fill(cr, x, y, w, h, '#0c0306')
    path = lambda: ws._capsule(cr, x, y, w, h)  # noqa: E731
    for lw, col, al in ((5, (0, 0, 0), 0.6), (3.2, rgb('#1e0a0e'), 1.0), (0.8, rgb('#5a2028'), 0.9)):
        path()
        cr.set_line_width(lw)
        cr.set_source_rgba(*col, al)
        cr.stroke()
    for x0 in _along(x, w, rnd, 120, h):   # red-hot seams
        side = rnd.choice((y + 0.8, y + h - 0.8))
        pts = [(x0 + i * 2.4, side + math.sin(i * 1.7 + x0) * 0.5) for i in range(int(rnd.uniform(5, 12)))]
        neon(cr, lambda: _poly(cr, pts), red, 0.8, 0.9, layers=((3, 0.15), (1.4, 0.4)))
    _inner(cr, x, y, w, h, red, 0.45, inset=3.0)
    katana(cr, x + w - h * 0.5, cy + h * 0.5, -0.38, 62)
    for px_ in _along(x, w, rnd, 110, 30):
        petal(cr, px_, max(3, y - rnd.uniform(-2, 3)), rnd.uniform(1.8, 2.8), rnd.uniform(0, 3),
              rgb(rnd.choice(('#ff8ab8', '#ffb0cc', '#ff6a9a'))), 0.9)


def bar_steampunk(cr, x, y, w, h, cy):
    rnd = random.Random(167)
    for fx in (0.05, 0.5, 0.95):
        halo(cr, x + w * fx, cy, h * 2.2, rgb('#8a4a0a'), 0.16)
    gear(cr, x - 14, cy - 5, h * 0.22, 8, 0.25)
    _bar_fill(cr, x, y, w, h, '#0e0703')
    brass_path(cr, lambda: ws._capsule(cr, x, y, w, h), 3.2)
    for rx in _along(x, w, rnd, 26, h * 0.6):
        rivet(cr, rx, y, 1.05)
        rivet(cr, rx, y + h, 1.05)
    for fx_ in _along(x, w, rnd, 220, 40):
        for fy in (y, y + h):
            rounded(cr, fx_ - 2, fy - 3, 4, 6, 1)
            cr.set_source(_vgrad(fy - 3, fy + 3, rgb('#ffd27a'), rgb('#6a3a12')))
            cr.fill()
        if rnd.random() < 0.5:
            steam(cr, fx_, max(3, y - 3), 4, 0.7, int(fx_))
    _inner(cr, x, y, w, h, rgb('#f0a13a'), 0.4, inset=3.4)
    gear(cr, x + 2, cy + 1, h * 0.38, 12, 0.0, glow=rgb('#f0a13a'))
    gauge(cr, x + w + 4, cy, h * 0.32, 0.6)


def bar_glacier(cr, x, y, w, h, cy):
    rnd = random.Random(173)
    ice = rgb('#4fc8ff')
    for fx in (0.05, 0.5, 0.95):
        halo(cr, x + w * fx, cy, h * 2.2, rgb('#0a3a8a'), 0.18)
    path = lambda: ws._capsule(cr, x, y, w, h)  # noqa: E731
    path()
    cr.set_source(_vgrad(y, y + h, rgb('#0c2a4a'), rgb('#03101f'), 0.92))
    cr.fill()
    _ice_rim(cr, x, y, w, h, rnd, size=0.9)
    crystal_cluster(cr, x - 4, y + h + 2, h * 0.9, ice, random.Random(2), n=5)
    snowflake(cr, x + w + 8, cy, h * 0.3, rgb('#cdf6ff'), 0.9)
    for sx in _along(x, w, rnd, 120, 30):
        snowflake(cr, sx, max(3, y - rnd.uniform(-1, 3)), rnd.uniform(1.4, 2.2), rgb('#cdf6ff'), 0.75, 0.5,
                  rot=rnd.uniform(0, 1))


def bar_witch(cr, x, y, w, h, cy):
    rnd = random.Random(179)
    violet = rgb('#b43cff')
    for fx in (0.05, 0.5, 0.95):
        halo(cr, x + w * fx, cy, h * 2.2, rgb('#4a0a8a'), 0.18)
    _bar_fill(cr, x, y, w, h, '#0a0418')
    _thorny(cr, x, y, w, h, max(6, w / 36), rnd)
    _inner(cr, x, y, w, h, violet, 0.5, inset=3.0)
    candle(cr, x - 2, y + h + 1, 10, 3.6)
    candle(cr, x - 10, y + h + 1, 7, 3.0, lean=0.1)
    raven(cr, x + w + 8, y + h, h * 0.9)
    for sx in _along(x, w, rnd, 60, 20):
        ws.sparkle(cr, sx, max(2.5, y - rnd.uniform(-1, 3)), rnd.uniform(1.0, 1.8),
                   rgb(rnd.choice(('#e8b8ff', '#b43cff', '#ffffff'))), 0.8)


def bar_dragon(cr, x, y, w, h, cy):
    rnd = random.Random(181)
    gold = rgb(GOLD)
    for fx in (0.05, 0.5, 0.95):
        halo(cr, x + w * fx, cy, h * 2.2, rgb('#8a1a04'), 0.2)
    _bar_fill(cr, x, y, w, h, '#140604')
    _gold_rim(cr, lambda: ws._capsule(cr, x, y, w, h), lambda: rounded(cr, x + 3, y + 3, w - 6, h - 6, (h - 6) / 2))
    if w > 160:   # a key border along the middle stretch
        meander(cr, x + w * 0.3, x + w * 0.7, y + 4.5, 3, gold, 0.6, 0.35)
    cloud_scroll(cr, x + w + 4, cy - 4, 10, rgb('#ffc42e'), 0.85)
    span = min(w * 0.45, 260)   # the dragon along the bottom of the left end, the head up at the end
    pts = []
    k = x + span
    while k > x + 8:
        pts.append((k, y + h + 0.5 + math.sin((k - x) / 11) * 1.2))
        k -= 5
    pts += [(x - 4, y + h - 3), (x - 9, cy + 2), (x - 8, cy - 4), (x - 2, cy - 7)]
    _curve(cr, pts)
    dragon_body(cr, _sample(cr, 3.0), 4.6, head_k=3.2)
    for _ in range(int(w / 140)):
        sakura(cr, rnd.uniform(x + 20, x + w - 20), max(3, y - rnd.uniform(-1, 2)), rnd.uniform(1.4, 2.2),
               rgb('#ff6a8a'), rnd.uniform(0, 1))


def bar_graffiti(cr, x, y, w, h, cy):
    rnd = random.Random(191)
    for fx, col in ((0.05, '#eb1fed'), (0.5, '#25ebf5'), (0.95, '#ffe014')):
        halo(cr, x + w * fx, cy, h * 2.2, rgb(col), 0.1)
    _bar_fill(cr, x, y, w, h, '#0a0614')
    _spray_rim(cr, x, y, w, h, rnd, size=0.85)
    crown(cr, x - 6, cy + 4, h * 0.55, rgb('#eb1fed'), 1.0)
    crown(cr, x + w + 8, cy + 4, h * 0.5, rgb('#25ebf5'), 1.0)


ws.BAR_SKINS.update({'halloween': bar_halloween, 'desert': bar_desert, 'neotokyo': bar_neotokyo, 'abyss': bar_abyss,
                     'forest': bar_forest, 'cosmos': bar_cosmos, 'samurai': bar_samurai, 'steampunk': bar_steampunk,
                     'glacier': bar_glacier, 'witch': bar_witch, 'dragon': bar_dragon, 'graffiti': bar_graffiti})
ws.BAR_MARGIN.update({'halloween': 44, 'desert': 44, 'neotokyo': 44, 'abyss': 48, 'forest': 40, 'cosmos': 40,
                      'samurai': 48, 'steampunk': 40, 'glacier': 40, 'witch': 44, 'dragon': 44, 'graffiti': 40})


# ═══════════════════════════════════════════════ themed icons
# fn(cr, kind, x, y, s, c): kind = 'ghost' | 'pac' | 'dot'; c = state color
_shape, _clip, _outline, _eyes = w3._shape, w3._clip, w3._outline, w3._eyes


def _body(cr, kind, x, y, s, top, bottom):
    _shape(cr, kind, x, y, s)
    cr.set_source(_vgrad(y - s / 2, y + s / 2, top, bottom))
    cr.fill()


def _anim():
    return ws.ANIM_T[0] or 0.0


def icon_halloween(cr, kind, x, y, s, c):
    fire = rgb('#ffe066')
    if kind == 'dot':   # candy corn
        halo(cr, x, y, s * 0.5, c, 0.4)
        tip, base = (x, y - s * 0.3), y + s * 0.2
        cr.save()
        _poly(cr, [tip, (x + s * 0.21, base), (x - s * 0.21, base)], True)
        cr.clip()
        for y0, y1, col in ((y - s * 0.32, y - s * 0.12, (1, 0.97, 0.9)), (y - s * 0.12, y + s * 0.05, c),
                            (y + s * 0.05, y + s * 0.22, rgb('#ffd23a'))):
            cr.rectangle(x - s * 0.3, y0, s * 0.6, y1 - y0)
            cr.set_source_rgba(*col, 1)
            cr.fill()
        cr.restore()
        return
    _body(cr, kind, x, y, s, _mix(c, (1, 0.9, 0.5), 0.3), _mix(c, (0.35, 0.06, 0), 0.5))
    if kind == 'pac':   # pumpkin ribs and a stem
        _clip(cr, kind, x, y, s)
        cr.set_line_width(max(0.5, s * 0.05))
        for k in (-0.3, 0.0, 0.3):
            _ellipse(cr, x + k * s, y, s * 0.2, s * 0.56)
        cr.set_source_rgba(0.35, 0.08, 0, 0.55)
        cr.stroke()
        cr.restore()
        cr.rectangle(x - s * 0.05, y - s * 0.68, s * 0.1, s * 0.16)
        cr.set_source_rgba(*rgb('#4a6a1c'), 1)
        cr.fill()
        _poly(cr, [(x - s * 0.02, y - s * 0.4), (x + s * 0.14, y - s * 0.4), (x + s * 0.06, y - s * 0.24)], True)
        cr.set_source_rgba(*fire, 1)
        cr.fill()
        _outline(cr, kind, x, y, s, _mix(c, (1, 0.8, 0.4), 0.3), 0.9)
        return
    _outline(cr, kind, x, y, s, _mix(c, (1, 0.8, 0.4), 0.3), 0.9)   # a carved ghost
    halo(cr, x, y - s * 0.05, s * 0.45, fire, 0.5)
    for sx in (-1, 1):
        _poly(cr, [(x + sx * s * 0.3, y - s * 0.02), (x + sx * s * 0.08, y - s * 0.02),
                   (x + sx * s * 0.2, y - s * 0.24)], True)
        cr.set_source_rgba(*fire, 1)
        cr.fill()
    pts = [(x - s * 0.24, y + s * 0.1)]
    for i in range(1, 6):
        pts.append((x - s * 0.24 + i * s * 0.096, y + s * (0.1 if i % 2 else 0.17)))
    pts += [(x + s * 0.2, y + s * 0.18), (x, y + s * 0.26), (x - s * 0.2, y + s * 0.18)]
    _poly(cr, pts, True)
    cr.set_source_rgba(*fire, 1)
    cr.fill()


def icon_desert(cr, kind, x, y, s, c):
    if kind == 'dot':
        sheriff_star(cr, x, y, s * 0.24, c)
        return
    _body(cr, kind, x, y, s, _mix(c, (1, 1, 0.8), 0.35), _mix(c, (0.5, 0.2, 0), 0.45))
    _clip(cr, kind, x, y, s)   # sand grain
    rnd = random.Random(int(x) + 1)
    for _ in range(10):
        cr.arc(x + rnd.uniform(-s / 2, s / 2), y + rnd.uniform(-s / 2, s / 2), max(0.3, s * 0.03), 0, TAU)
        cr.set_source_rgba(0.45, 0.22, 0.02, 0.5)
        cr.fill()
    cr.restore()
    _outline(cr, kind, x, y, s, _mix(c, (1, 1, 0.8), 0.4), 0.9)
    _eyes(cr, kind, x, y, s, (1, 1, 0.95), (0.3, 0.12, 0.02))
    if kind == 'ghost':
        cowboy_hat(cr, x, y - s * 0.4, s * 0.92)


def icon_neotokyo(cr, kind, x, y, s, c):
    if kind == 'dot':   # a neon ring
        neon(cr, lambda: (cr.new_path(), cr.arc(x, y, s * 0.18, 0, TAU)), c, max(0.8, s * 0.07), 1.0,
             layers=((4, 0.1), (2, 0.3)))
        cr.arc(x, y, s * 0.06, 0, TAU)
        cr.set_source_rgba(*_mix(c, (1, 1, 1), 0.5), 1)
        cr.fill()
        return
    _shape(cr, kind, x, y, s)
    cr.set_source(_vgrad(y - s / 2, y + s / 2, _mix(c, (0, 0, 0), 0.35), _mix(c, (0.05, 0, 0.15), 0.75), 0.9))
    cr.fill()
    _clip(cr, kind, x, y, s)   # scan lines
    cr.set_line_width(max(0.4, s * 0.04))
    k = y - s / 2
    while k < y + s / 2:
        cr.move_to(x - s, k)
        cr.line_to(x + s, k)
        k += max(1.6, s * 0.14)
    cr.set_source_rgba(*c, 0.35)
    cr.stroke()
    cr.restore()
    cr.save()   # a cyan echo, the sign a little out of register
    cr.translate(-max(0.6, s * 0.05), 0)
    _shape(cr, kind, x, y, s)
    cr.set_line_width(max(0.5, s * 0.05))
    cr.set_source_rgba(*rgb('#3ad8ff'), 0.6)
    cr.stroke()
    cr.restore()
    neon(cr, lambda: _shape(cr, kind, x, y, s), c, max(0.8, s * 0.075), 1.0, layers=((3, 0.12), (1.5, 0.3)))
    _eyes(cr, kind, x, y, s, (1, 1, 1), _mix(c, (0.1, 0, 0.3), 0.5))


def icon_abyss(cr, kind, x, y, s, c):
    if kind == 'dot':   # a glowing pearl
        halo(cr, x, y, s * 0.55, c, 0.55)
        cr.arc(x, y, s * 0.2, 0, TAU)
        cr.set_source(_radial(x, y, s * 0.2, (1, 1, 1), _mix(c, (0, 0.1, 0.3), 0.4), 1, 1, -0.35, -0.35))
        cr.fill()
        return
    if kind == 'ghost':   # a jellyfish ghost: trailing threads under the feet
        cr.set_line_width(max(0.4, s * 0.035))
        for k in (-0.25, 0.0, 0.25):
            cr.move_to(x + k * s, y + s * 0.4)
            for i in range(1, 6):
                f = i / 5
                cr.line_to(x + k * s + math.sin(f * 6 + _anim() * 3 + k * 9) * s * 0.06, y + s * (0.4 + 0.28 * f))
        cr.set_source_rgba(*c, 0.6)
        cr.stroke()
    _shape(cr, kind, x, y, s)
    cr.set_source(_radial(x, y - s * 0.2, s * 0.7, _mix(c, (1, 1, 1), 0.55), c, 0.95, 0.55))
    cr.fill()
    _clip(cr, kind, x, y, s)   # light rippling through
    cr.set_line_width(max(0.4, s * 0.04))
    for k in range(3):
        yy = y - s * 0.25 + k * s * 0.22
        cr.move_to(x - s * 0.6, yy)
        for i in range(1, 9):
            cr.line_to(x - s * 0.6 + i * s * 0.15, yy + math.sin(i * 1.4 + k * 2 + _anim() * 2) * s * 0.05)
    cr.set_source_rgba(1, 1, 1, 0.3)
    cr.stroke()
    cr.restore()
    _outline(cr, kind, x, y, s, _mix(c, (1, 1, 1), 0.4), 0.9)
    _eyes(cr, kind, x, y, s, (1, 1, 1), (0.0, 0.15, 0.35))


def icon_forest(cr, kind, x, y, s, c):
    if kind == 'dot':   # a firefly
        for sx in (-1, 1):
            _ellipse(cr, x + sx * s * 0.1, y - s * 0.1, s * 0.1, s * 0.05, sx * 0.5)
            cr.set_source_rgba(1, 1, 1, 0.45)
            cr.fill()
        firefly(cr, x, y + s * 0.02, s * 0.11, _mix(c, rgb('#ffe066'), 0.5))
        return
    _body(cr, kind, x, y, s, _mix(c, (1, 1, 0.6), 0.3), _mix(c, (0, 0.2, 0), 0.5))
    _clip(cr, kind, x, y, s)   # leaf veins
    cr.set_line_width(max(0.4, s * 0.04))
    vx = x if kind == 'ghost' else x - s * 0.05
    cr.move_to(vx, y + s * 0.6)
    cr.line_to(vx, y - s * 0.5)
    for k in range(4):
        yy = y + s * 0.35 - k * s * 0.22
        for sx in (-1, 1):
            cr.move_to(vx, yy)
            cr.line_to(vx + sx * s * 0.4, yy - s * 0.2)
    cr.set_source_rgba(0.05, 0.25, 0.02, 0.5)
    cr.stroke()
    cr.restore()
    _outline(cr, kind, x, y, s, _mix(c, (1, 1, 0.7), 0.35), 0.9)
    _eyes(cr, kind, x, y, s, (1, 1, 0.95), (0.05, 0.2, 0.02))
    if kind == 'ghost':   # a sprout on its head
        ws.leaf(cr, x, y - s * 0.47, s * 0.3, -1.1, rgb('#9ce02e'), vein=False)
        ws.leaf(cr, x, y - s * 0.47, s * 0.26, -2.1, rgb('#c8f04a'), vein=False)


def icon_cosmos(cr, kind, x, y, s, c):
    if kind == 'dot':   # a star
        ws.sparkle(cr, x, y, s * 0.3, _mix(c, (1, 1, 1), 0.25), 1.0)
        return
    if kind == 'pac':   # the moon, cratered
        _shape(cr, kind, x, y, s)
        cr.set_source(_radial(x, y, s * 0.6, _mix(c, (1, 1, 1), 0.55), _mix(c, (0.05, 0.03, 0.2), 0.45), 1, 1,
                              -0.3, -0.3))
        cr.fill()
        _clip(cr, kind, x, y, s)
        for dx, dy, r in ((-0.2, 0.15, 0.12), (0.05, 0.3, 0.08), (-0.3, -0.12, 0.07), (0.15, -0.3, 0.06)):
            cr.arc(x + dx * s, y + dy * s, r * s, 0, TAU)
            cr.set_source_rgba(0.05, 0.03, 0.2, 0.25)
            cr.fill()
        cr.restore()
        _outline(cr, kind, x, y, s, _mix(c, (1, 1, 1), 0.5), 0.8)
        _eyes(cr, kind, x, y, s)
        return
    _shape(cr, kind, x, y, s)   # a ghost full of nebula and stars
    g = cairo.LinearGradient(x - s / 2, y - s / 2, x + s / 2, y + s / 2)
    g.add_color_stop_rgb(0, *_mix(c, (1, 1, 1), 0.3))
    g.add_color_stop_rgb(0.6, *_mix(c, rgb('#c04dff'), 0.5))
    g.add_color_stop_rgb(1, *_mix(c, (0.05, 0, 0.2), 0.5))
    cr.set_source(g)
    cr.fill()
    _clip(cr, kind, x, y, s)
    rnd = random.Random(int(x) + 7)
    for _ in range(6):
        cr.arc(x + rnd.uniform(-s / 2, s / 2), y + rnd.uniform(-s / 2, s / 2), max(0.3, s * 0.035), 0, TAU)
        cr.set_source_rgba(1, 1, 1, 0.9)
        cr.fill()
    cr.restore()
    _outline(cr, kind, x, y, s, _mix(c, (1, 1, 1), 0.45), 0.9)
    _eyes(cr, kind, x, y, s, (1, 1, 1), (0.1, 0.05, 0.35))


def icon_samurai(cr, kind, x, y, s, c):
    if kind == 'dot':   # a red sun inside an open brush circle
        halo(cr, x, y, s * 0.5, c, 0.45)
        cr.arc(x, y, s * 0.13, 0, TAU)
        cr.set_source_rgba(*c, 1)
        cr.fill()
        cr.arc(x, y, s * 0.24, -1.2, 4.2)
        cr.set_line_width(max(0.6, s * 0.06))
        cr.set_source_rgba(*_mix(c, (1, 0.8, 0.8), 0.3), 0.85)
        cr.stroke()
        return
    _body(cr, kind, x, y, s, _mix(c, (1, 0.8, 0.7), 0.25), _mix(c, (0.2, 0, 0), 0.55))
    _clip(cr, kind, x, y, s)   # brush strokes
    cr.set_line_width(max(0.5, s * 0.06))
    for k in range(3):
        yy = y - s * 0.1 + k * s * 0.22
        cr.move_to(x - s * 0.5, yy + s * 0.12)
        cr.curve_to(x - s * 0.1, yy - s * 0.05, x + s * 0.2, yy + s * 0.05, x + s * 0.55, yy - s * 0.1)
    cr.set_source_rgba(0.15, 0, 0, 0.4)
    cr.stroke()
    cr.restore()
    _outline(cr, kind, x, y, s, _mix(c, (1, 0.7, 0.6), 0.35), 0.9)
    _eyes(cr, kind, x, y, s, (1, 1, 1), (0.25, 0, 0))
    if kind == 'ghost':   # a hachimaki: a white band with the red sun, its knot flying
        cr.save()
        _clip(cr, kind, x, y, s)
        cr.rectangle(x - s, y - s * 0.38, s * 2, s * 0.13)
        cr.set_source_rgba(0.96, 0.94, 0.92, 1)
        cr.fill()
        cr.restore()
        cr.restore()
        cr.arc(x, y - s * 0.315, s * 0.05, 0, TAU)
        cr.set_source_rgba(*rgb('#ff2a2a'), 1)
        cr.fill()
        cr.set_line_width(max(0.5, s * 0.06))
        for dy in (-0.02, 0.06):
            cr.move_to(x + s * 0.42, y - s * 0.33)
            cr.curve_to(x + s * 0.55, y - s * (0.36 - dy), x + s * 0.62, y - s * (0.26 - dy),
                        x + s * 0.72, y - s * (0.3 - dy * 2))
        cr.set_source_rgba(0.96, 0.94, 0.92, 1)
        cr.stroke()


def icon_steampunk(cr, kind, x, y, s, c):
    if kind == 'dot':   # a small cog, turning
        halo(cr, x, y, s * 0.45, c, 0.35)
        gear(cr, x, y, s * 0.24, 8, _anim() * 1.5, face=c, spokes=0)
        return
    _body(cr, kind, x, y, s, _mix(c, (1, 0.95, 0.75), 0.35), _mix(c, (0.25, 0.1, 0), 0.6))
    _clip(cr, kind, x, y, s)   # rivets along the bottom
    for k in range(-2, 3):
        rivet(cr, x + k * s * 0.18, y + s * 0.3, max(0.5, s * 0.045))
    cr.restore()
    _outline(cr, kind, x, y, s, _mix(c, (1, 0.9, 0.6), 0.35), 0.9)
    if kind == 'ghost':   # goggles, the lenses glowing amber
        cr.move_to(x - s * 0.46, y - s * 0.12)
        cr.line_to(x + s * 0.46, y - s * 0.12)
        cr.set_line_width(max(0.6, s * 0.07))
        cr.set_source_rgba(0.2, 0.1, 0.04, 1)
        cr.stroke()
        for sx in (-1, 1):
            cr.arc(x + sx * s * 0.19, y - s * 0.1, s * 0.15, 0, TAU)
            cr.set_source(_radial(x + sx * s * 0.19, y - s * 0.1, s * 0.15, rgb('#ffe2a0'), rgb('#6a3a12'),
                                  1, 1, -0.3, -0.3))
            cr.fill()
            cr.arc(x + sx * s * 0.19, y - s * 0.1, s * 0.1, 0, TAU)
            cr.set_source(_radial(x + sx * s * 0.19, y - s * 0.1, s * 0.1, (1, 0.95, 0.7), rgb('#ff8a1a'), 1, 1))
            cr.fill()
    else:
        _eyes(cr, kind, x, y, s, (1, 1, 1), (0.2, 0.08, 0.02))


def icon_glacier(cr, kind, x, y, s, c):
    if kind == 'dot':
        halo(cr, x, y, s * 0.5, c, 0.4)
        snowflake(cr, x, y, s * 0.26, _mix(c, (1, 1, 1), 0.4), 1.0, max(0.5, s * 0.05), glow=False,
                  rot=_anim() * 0.4)
        return
    _body(cr, kind, x, y, s, _mix(c, (1, 1, 1), 0.6), _mix(c, (0, 0.1, 0.3), 0.35))
    _clip(cr, kind, x, y, s)   # facets and cracks
    rnd = random.Random(int(x) + 11)
    cr.set_line_width(max(0.4, s * 0.035))
    for _ in range(4):
        x0, y0 = x + rnd.uniform(-s / 2, s / 2), y + rnd.uniform(-s / 2, s / 2)
        cr.move_to(x0, y0)
        for _k in range(3):
            x0 += rnd.uniform(-s * 0.25, s * 0.25)
            y0 += rnd.uniform(-s * 0.25, s * 0.25)
            cr.line_to(x0, y0)
    cr.set_source_rgba(1, 1, 1, 0.6)
    cr.stroke()
    _poly(cr, [(x - s * 0.5, y - s * 0.5), (x + s * 0.1, y - s * 0.5), (x - s * 0.5, y + s * 0.15)], True)
    cr.set_source_rgba(1, 1, 1, 0.22)
    cr.fill()
    cr.restore()
    _outline(cr, kind, x, y, s, (0.9, 0.98, 1), 0.9)
    _eyes(cr, kind, x, y, s, (1, 1, 1), (0.02, 0.15, 0.4))


def icon_witch(cr, kind, x, y, s, c):
    if kind == 'dot':
        wisp(cr, x, y - s * 0.04, s * 0.42, c, 1.0, 0.04 * math.sin(_anim() * 4 + x))
        return
    _body(cr, kind, x, y, s, _mix(c, (1, 0.9, 1), 0.3), _mix(c, (0.1, 0, 0.25), 0.55))
    _clip(cr, kind, x, y, s)   # a rune circle
    cr.set_line_width(max(0.4, s * 0.035))
    cr.arc(x + s * 0.05, y + s * 0.12, s * 0.3, 0, TAU)
    for k in range(6):
        ang = k * PI / 3 + 0.3
        cr.move_to(x + s * 0.05 + math.cos(ang) * s * 0.3, y + s * 0.12 + math.sin(ang) * s * 0.3)
        cr.line_to(x + s * 0.05 + math.cos(ang) * s * 0.4, y + s * 0.12 + math.sin(ang) * s * 0.4)
    cr.set_source_rgba(1, 0.9, 1, 0.35)
    cr.stroke()
    cr.restore()
    _outline(cr, kind, x, y, s, _mix(c, (1, 0.9, 1), 0.4), 0.9)
    _eyes(cr, kind, x, y, s, (1, 1, 1), (0.2, 0, 0.35))
    if kind == 'ghost':
        witch_hat(cr, x, y - s * 0.4, s * 0.95, rgb('#1c0a30'), c)


def icon_dragon(cr, kind, x, y, s, c):
    if kind == 'dot':
        coin(cr, x, y, s * 0.22, c)
        return
    _body(cr, kind, x, y, s, _mix(c, (1, 1, 0.75), 0.4), _mix(c, (0.45, 0.1, 0), 0.5))
    _clip(cr, kind, x, y, s)   # dragon scales
    r = s * 0.12
    cr.set_line_width(max(0.4, s * 0.035))
    for row in range(-5, 6):
        for col in range(-5, 6):
            cx = x + col * r * 1.6 + (row % 2) * r * 0.8
            cy = y + row * r * 0.9
            cr.new_sub_path()
            cr.arc(cx, cy, r, 0, PI)
    cr.set_source_rgba(0.45, 0.15, 0, 0.45)
    cr.stroke()
    cr.restore()
    _outline(cr, kind, x, y, s, _mix(c, (1, 1, 0.8), 0.4), 0.9)
    _eyes(cr, kind, x, y, s, (1, 0.95, 0.6), (0.45, 0.05, 0))


def icon_graffiti(cr, kind, x, y, s, c):
    if kind == 'dot':   # a little splat of paint
        rnd = random.Random(int(x))
        halo(cr, x, y, s * 0.45, c, 0.35)
        splat(cr, x, y, s * 0.15, c, rnd, 1.0, spikes=7)
        return
    _shape(cr, kind, x, y, s)
    cr.set_source_rgba(*c, 0.35)
    cr.fill()
    _clip(cr, kind, x, y, s)   # spray speckle
    rnd = random.Random(int(x) + 5)
    for _ in range(14):
        cr.arc(x + rnd.gauss(0, s * 0.25), y + rnd.gauss(0, s * 0.25), max(0.3, s * rnd.uniform(0.02, 0.05)), 0, TAU)
        cr.set_source_rgba(*_mix(c, (1, 1, 1), 0.3), rnd.uniform(0.4, 0.9))
        cr.fill()
    cr.restore()
    neon(cr, lambda: _shape(cr, kind, x, y, s), c, max(0.8, s * 0.075), 1.0, layers=((3, 0.12), (1.5, 0.3)))
    _eyes(cr, kind, x, y, s, (1, 1, 1), _mix(c, (0, 0, 0), 0.6))
    w3.drip(cr, x + s * (0.1 if kind == 'ghost' else -0.15), y + s * 0.42, s * 0.3, s * 0.05, c, 0.95)


ws.ICON_PAINTERS.update({
    'halloween': icon_halloween, 'desert': icon_desert, 'neotokyo': icon_neotokyo, 'abyss': icon_abyss,
    'forest': icon_forest, 'cosmos': icon_cosmos, 'samurai': icon_samurai, 'steampunk': icon_steampunk,
    'glacier': icon_glacier, 'witch': icon_witch, 'dragon': icon_dragon, 'graffiti': icon_graffiti,
})
