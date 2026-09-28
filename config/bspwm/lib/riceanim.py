# =============================================================
# Author:  TechOGR
# Repo:    https://github.com/TechOGR/bspwm_dotfiles_arch
#
# riceanim - the themes in motion. Three sectors, each with its own
# effect (RiceEditor -> Compositor -> Animations, theme-config.bash):
#   ANIM_BAR   the polybar skin and the workspace pill
#   ANIM_WIN   the focused window's frame
#   ANIM_BACK  the texture behind the terminals
# Each one is "theme" (the effect that suits the theme: Storm crackles,
# Fire throws embers, Butterflies fly around the edges, Liquid flows...),
# "off", or an effect by name. ANIM_MODE: auto (only in the Normal
# performance mode), on (Lite too: a VM can show them), off.
# RICE_ANIM=1 / 0 in the environment forces them on / off.
#
# An effect draws on an outline (flat points of the bar / frame shape)
# and returns the box it drew in, so the daemons repaint only that.
#
# Copyright (C) 2021-2026 TechOGR <https://github.com/TechOGR>
# Licensed under GPL-3.0 license
# =============================================================

import math
import os
import random
import re

import cairo

FPS = 24


def fps():
    """24 frames a second in Normal; 12 in Lite (xrender repaints the whole
    screen for every frame: half the frames, half the cost, still smooth
    for these slow effects)."""
    try:
        import riceui
        return 24 if riceui.perf_profile() == 'full' else 12
    except Exception:
        return 12

# ── the effects, with their names in RiceEditor
EDGE_EFFECTS = [
    ('spark', 'Electric crackle'), ('embers', 'Rising embers'), ('petals', 'Flying butterflies / leaves'),
    ('flow', 'Flowing edge'), ('shimmer', 'Soft shimmer'), ('pulse', 'Breathing glow'),
    ('comets', 'Running lights'),
]
BACK_EFFECTS = [('drift', 'Floating motes'), ('flash', 'Lightning flashes'), ('sweep', 'Light sweep')]
FULL = {'pulse', 'flow'}   # redraw the whole outline every frame (drawn at half rate)

WIN_THEME = {
    'storm': 'spark', 'fire': 'embers', 'lava': 'embers', 'butterfly': 'petals', 'nature': 'petals',
    'liquid': 'flow', 'venom': 'flow', 'snake': 'shimmer', 'holo': 'shimmer', 'glass': 'shimmer',
    'crystal': 'shimmer', 'neon': 'pulse', 'cyber': 'pulse', 'hud': 'pulse', 'minimal': 'pulse',
    'sketch': 'shimmer', 'pixel': 'pulse',
}
BAR_THEME = dict(WIN_THEME, butterfly='comets', snake='flow', holo='comets')
BACK_THEME = {'storm': 'flash', 'fire': 'drift', 'lava': 'drift', 'butterfly': 'drift', 'nature': 'drift',
              'venom': 'drift', 'holo': 'drift', 'liquid': 'drift', 'snake': 'drift'}

# style: (items, seconds per lap, length (fraction of the outline), flicker, color)
STYLE = {
    'glass': (1, 7.0, 0.10, 0.0, '#ffffff'), 'cyber': (2, 3.5, 0.08, 0.15, None),
    'minimal': (1, 12.0, 0.06, 0.0, None), 'pixel': (2, 5.0, 0.05, 0.0, None),
    'liquid': (2, 6.0, 0.14, 0.0, '#8fe6ff'), 'hud': (2, 4.0, 0.07, 0.1, None),
    'fire': (3, 4.5, 0.10, 0.45, '#ffc400'), 'nature': (1, 10.0, 0.12, 0.0, '#b9ff66'),
    'sketch': (1, 9.0, 0.08, 0.0, '#ffffff'), 'crystal': (2, 6.0, 0.06, 0.1, '#ffffff'),
    'lava': (2, 7.0, 0.12, 0.35, '#ffd040'), 'neon': (2, 4.0, 0.12, 0.05, None),
    'holo': (2, 6.5, 0.10, 0.1, '#ff8ae0'), 'storm': (3, 2.2, 0.09, 0.6, '#dff0ff'),
    'venom': (2, 5.5, 0.12, 0.2, '#ff3a3a'), 'butterfly': (2, 7.5, 0.11, 0.05, '#ffb8f0'),
    'snake': (1, 5.0, 0.18, 0.0, '#e8ff5a'),
}
DEFAULT = (1, 8.0, 0.08, 0.0, None)


# ═══════════════════════════════════════════════════════════ settings
def _theme_var(name, default):
    try:
        rice = open(os.path.expanduser('~/.config/bspwm/.rice')).read().strip()
        text = open(os.path.expanduser(f'~/.config/bspwm/rices/{rice}/theme-config.bash')).read()
        m = re.search(rf'^{name}=["\']?([\w-]*)', text, re.M)
        return m.group(1) if m and m.group(1) else default
    except OSError:
        return default


def mode_on():
    env = os.environ.get('RICE_ANIM')
    if env in ('0', '1'):
        return env == '1'
    mode = _theme_var('ANIM_MODE', 'auto')
    if mode in ('on', 'off'):
        return mode == 'on'
    try:
        import riceui
        return riceui.perf_profile() == 'full'
    except Exception:
        return False


enabled = mode_on   # older callers


def effect(sector, style):
    """The effect of a sector ('bar' | 'win' | 'back') for a style, or None."""
    if not mode_on() or not style:
        return None
    val = _theme_var({'bar': 'ANIM_BAR', 'win': 'ANIM_WIN', 'back': 'ANIM_BACK'}[sector], 'theme')
    if val == 'off':
        return None
    if val == 'theme':
        if sector == 'back':
            return BACK_THEME.get(style, 'sweep')
        return (BAR_THEME if sector == 'bar' else WIN_THEME).get(style, 'shimmer')
    return val


def color(style):
    import wspill as ws
    c = STYLE.get(style, DEFAULT)[4] or ws.NATIVE.get(style, '#6fa8ff')
    return ws.rgb(c)


# ═══════════════════════════════════════════════════════════ outlines
def flat_points(cr):
    """The current path as (points, cumulative lengths, total length)."""
    pts, lens, total = [], [], 0.0
    start = None
    for kind, p in cr.copy_path_flat():
        if kind in (cairo.PATH_MOVE_TO, cairo.PATH_LINE_TO):
            if pts:
                total += math.hypot(p[0] - pts[-1][0], p[1] - pts[-1][1])
            pts.append(p)
            lens.append(total)
            if start is None:
                start = p
        elif kind == cairo.PATH_CLOSE_PATH and start and pts:
            total += math.hypot(start[0] - pts[-1][0], start[1] - pts[-1][1])
            pts.append(start)
            lens.append(total)
    cr.new_path()
    return pts, lens, total


def point_at(outline, d):
    """(x, y, nx, ny): the point at length d and the normal there."""
    import bisect
    pts, lens, total = outline
    d %= total
    i = max(1, min(len(pts) - 1, bisect.bisect_left(lens, d)))
    (ax, ay), (bx, by) = pts[i - 1], pts[i]
    seg = lens[i] - lens[i - 1] or 1
    f = (d - lens[i - 1]) / seg
    L = math.hypot(bx - ax, by - ay) or 1
    return ax + (bx - ax) * f, ay + (by - ay) * f, (by - ay) / L, -(bx - ax) / L


def _outward(outline):
    """+1 or -1: the sign that makes point_at's normal point out of the shape."""
    pts = outline[0]
    area = sum(pts[i][0] * pts[i + 1][1] - pts[i + 1][0] * pts[i][1] for i in range(len(pts) - 1))
    return -1 if area > 0 else 1


def _box(points, pad):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)


def _union(a, b):
    if a is None:
        return b
    if b is None:
        return a
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def _segment(outline, a, b):
    pts, lens, total = outline
    out = []
    for i in range(len(pts)):
        rel = (lens[i] - a) % total
        if rel <= (b - a):
            out.append((rel, pts[i]))
    out.sort()
    return [p for _r, p in out]


def _trail(cr, seg, col, a, width, scale, head=True, soft=False):
    n = len(seg)
    chunks = min(8, n - 1)
    bounds = [round(i * (n - 1) / chunks) for i in range(chunks + 1)]
    cr.set_line_cap(1)
    core = tuple(v + (1 - v) * 0.6 for v in col)
    layers = ((16 * scale, 0.16, col), (8 * scale, 0.32, col), (width * scale, 0.75, core)) if soft else \
        ((11 * scale, 0.14, col), (5.5 * scale, 0.32, col), (width * 1.3 * scale, 1.0, core))
    for lw, al, cc in layers:
        cr.set_line_width(lw)
        for c in range(chunks):
            i0, i1 = bounds[c], bounds[c + 1]
            if i1 <= i0:
                continue
            f = (c + 1) / chunks
            f = math.sin(f * math.pi) if soft else f * f   # soft: bright in the middle
            cr.move_to(*seg[i0])
            for pnt in seg[i0 + 1:i1 + 1]:
                cr.line_to(*pnt)
            cr.set_source_rgba(*cc, al * a * f)
            cr.stroke()
    if head:
        hx, hy = seg[-1]
        g = cairo.RadialGradient(hx, hy, 0, hx, hy, 13 * scale)
        g.add_color_stop_rgba(0, 1, 1, 1, a)
        g.add_color_stop_rgba(0.25, *col, 0.75 * a)
        g.add_color_stop_rgba(1, *col, 0)
        cr.set_source(g)
        cr.arc(hx, hy, 13 * scale, 0, 2 * math.pi)
        cr.fill()


def _glow_dot(cr, x, y, r, col, a):
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0, 1, 1, 0.9, a)
    g.add_color_stop_rgba(0.35, *col, 0.8 * a)
    g.add_color_stop_rgba(1, *col, 0)
    cr.set_source(g)
    cr.arc(x, y, r, 0, 2 * math.pi)
    cr.fill()


# ═══════════════════════════════════════════════════════ edge effects
def fx_comets(cr, style, outline, t, seed, scale):
    n, lap, frac, flick, _c = STYLE.get(style, DEFAULT)
    total = outline[2]
    col = color(style)
    box = None
    for k in range(n):
        head = ((t / lap + k / n + seed * 0.137) % 1.0) * total
        seg = _segment(outline, head - total * frac, head)
        if len(seg) < 2:
            continue
        a = 1.0 - flick * random.Random(int(t * FPS) * 7 + k + seed).random() if flick else 1.0
        _trail(cr, seg, col, a, 1.8, scale)
        box = _union(box, _box(seg, 15 * scale))
    return box


def fx_shimmer(cr, style, outline, t, seed, scale):
    """Two long, soft bands of light gliding along the edge (no spark)."""
    lap = STYLE.get(style, DEFAULT)[1]
    total = outline[2]
    col = color(style)
    box = None
    for k in range(2):
        head = ((t / (lap * 1.6) + k / 2 + seed * 0.21) % 1.0) * total
        seg = _segment(outline, head - total * 0.28, head)
        if len(seg) < 2:
            continue
        _trail(cr, seg, col, 0.9, 2.2, scale, head=False, soft=True)
        box = _union(box, _box(seg, 16 * scale))
    return box


def fx_pulse(cr, style, outline, t, seed, scale):
    """The whole edge breathing: its glow swells and fades."""
    _n, lap, _f, flick, _c = STYLE.get(style, DEFAULT)
    col = color(style)
    v = 0.5 + 0.5 * math.sin(t * 2 * math.pi / max(2.0, lap * 0.6) + seed)
    if flick:
        v *= 1 - flick * 0.5 * random.Random(int(t * 12) + seed).random()
    pts = outline[0]
    cr.set_line_join(1)
    for lw, al in ((16 * scale, 0.08), (8 * scale, 0.16), (2.2 * scale, 0.55)):
        cr.move_to(*pts[0])
        for p in pts[1:]:
            cr.line_to(*p)
        cr.set_line_width(lw * (0.6 + 0.4 * v))
        cr.set_source_rgba(*col, al * v)
        cr.stroke()
    return _box(pts, 18 * scale)


def fx_flow(cr, style, outline, t, seed, scale):
    """Two strands winding along the edge, their waves travelling: the edge
    looks alive (water, venom, a snake's body)."""
    pts, lens, total = outline
    col = color(style)
    sgn = _outward(outline)
    step = max(1, len(pts) // 360)
    for k, (amp, wl, sp, al) in enumerate(((3.2, 70, 40, 0.55), (2.2, 45, -28, 0.35))):
        cr.new_path()
        first = True
        for i in range(0, len(pts), step):
            x, y, nx, ny = point_at(outline, lens[i])
            o = sgn * amp * scale * math.sin((lens[i] - t * sp) / wl * 2 * math.pi + k * 1.7 + seed)
            (cr.move_to if first else cr.line_to)(x + nx * o, y + ny * o)
            first = False
        cr.close_path()
        for lw, a in ((6 * scale, al * 0.25), (1.6 * scale, al)):
            cr.set_line_width(lw)
            cr.set_source_rgba(*col, a)
            cr.stroke_preserve()
        cr.new_path()
    return _box(pts, 12 * scale)


def fx_spark(cr, style, outline, t, seed, scale):
    """Electric crackle: short bolts jump out of the edge, a few at a time,
    every frame somewhere else."""
    total = outline[2]
    col = color(style)
    sgn = _outward(outline)
    rnd = random.Random(int(t * 14) * 31 + seed)
    box = None
    for _ in range(rnd.randint(1, 3)):
        d = rnd.uniform(0, total)
        x, y, nx, ny = point_at(outline, d)
        nx, ny = nx * sgn, ny * sgn
        L = rnd.uniform(10, 26) * scale
        tx, ty = -ny, nx
        pts = [(x, y)]
        for i in range(1, 6):
            f = i / 5
            j = rnd.uniform(-5, 5) * scale
            pts.append((x + nx * L * f + tx * j, y + ny * L * f + ty * j))
        if rnd.random() < 0.6:   # it also runs a bit along the edge
            for i in range(1, 5):
                px_, py_, _a, _b = point_at(outline, d + i * rnd.uniform(4, 9) * scale)
                pts.insert(0, (px_ + rnd.uniform(-2, 2), py_ + rnd.uniform(-2, 2)))
        for lw, a in ((7 * scale, 0.12), (3.5 * scale, 0.3), (1.3 * scale, 1.0)):
            cr.move_to(*pts[0])
            for p in pts[1:]:
                cr.line_to(*p)
            cr.set_line_width(lw)
            cr.set_source_rgba(*(col if lw > 2 else (0.95, 0.98, 1)), a)
            cr.stroke()
        _glow_dot(cr, *pts[-1], 6 * scale, col, 0.8)
        box = _union(box, _box(pts, 10 * scale))
    return box


def fx_embers(cr, style, outline, t, seed, scale):
    """Embers leave the edge and rise, swaying and fading."""
    total = outline[2]
    col = color(style)
    sgn = _outward(outline)
    box = None
    n = max(8, min(22, int(total / 110)))
    for k in range(n):
        rnd = random.Random(k * 97 + seed)
        life = rnd.uniform(1.6, 2.8)
        age = (t + rnd.uniform(0, life)) % life
        f = age / life
        for _try in range(12):   # from the top edge and the sides only: they rise away from the window
            x, y, nx, ny = point_at(outline, rnd.uniform(0, total))
            nx, ny = nx * sgn, ny * sgn
            if ny < 0.3:
                break
        side = abs(nx) > 0.6
        x += nx * 4
        y += ny * 4
        drift = nx * f * rnd.uniform(6, 16) * scale if side else 0   # side embers lean outwards
        ex = x + drift + math.sin(age * 3 + k) * 4 * scale
        ey = y - f * rnd.uniform(30, 50) * scale
        a = math.sin(f * math.pi) * rnd.uniform(0.7, 1.0)
        r = rnd.uniform(3.0, 5.0) * scale * (1 - 0.4 * f)
        _glow_dot(cr, ex, ey, r * 2.2, col, a * 0.6)
        cr.arc(ex, ey, r * 0.5, 0, 2 * math.pi)
        cr.set_source_rgba(1, 0.85 - 0.5 * f, 0.4 - 0.3 * f, a)
        cr.fill()
        box = _union(box, (ex - r * 3, ey - r * 3, ex + r * 3, ey + r * 3))
    return box


def fx_petals(cr, style, outline, t, seed, scale):
    """Little butterflies (or leaves) travel along the edge, fluttering in
    and out of it."""
    import wspill as ws
    total = outline[2]
    col = color(style)
    sgn = _outward(outline)
    box = None
    n = max(3, min(8, int(total / 450)))
    for k in range(n):
        rnd = random.Random(k * 53 + seed)
        speed = rnd.uniform(18, 34) * scale * (1 if k % 2 else -1)
        x, y, nx, ny = point_at(outline, rnd.uniform(0, total) + t * speed)
        off = (6 + 7 * math.sin(t * rnd.uniform(1.2, 2.0) + k)) * scale * sgn
        x, y = x + nx * off, y + ny * off
        size = rnd.uniform(8, 11) * scale
        flap = 0.55 + 0.45 * abs(math.sin(t * 9 + k))   # wings opening and closing
        cr.save()
        cr.translate(x, y)
        cr.scale(flap, 1)
        if style == 'nature':
            ws.leaf(cr, 0, 0, size * 2.2, t * 0.8 + k, ws.rgb(rnd.choice(('#2fbf55', '#6fdc7f', '#b9ff66'))))
        else:
            import wsthree
            c2 = ws.rgb(rnd.choice(('#b07cff', '#8fb8ff', '#ff7ae0')))
            wsthree.butterfly(cr, 0, 0, size, math.sin(t + k) * 0.4, col, c2, 0.95)
        cr.restore()
        box = _union(box, (x - size * 2.2, y - size * 2.2, x + size * 2.2, y + size * 2.2))
    return box


EDGE_FNS = {'comets': fx_comets, 'shimmer': fx_shimmer, 'pulse': fx_pulse, 'flow': fx_flow,
            'spark': fx_spark, 'embers': fx_embers, 'petals': fx_petals}


def draw_edge(cr, name, style, outline, t, seed=0, scale=1.0):
    """Draw an edge effect; returns the box it drew in (or None)."""
    fn = EDGE_FNS.get(name)
    if not fn or not outline or outline[2] <= 0:
        return None
    return fn(cr, style, outline, t, seed, scale)


def draw_comets(cr, style, outline, t, width=2.0, seed=0, scale=1.0):   # older callers
    return fx_comets(cr, style, outline, t, seed, scale)


# ═════════════════════════════════════════════════ texture effects
def draw_back(cr, name, style, w, h, t):
    col = color(style)
    if name == 'sweep':
        u = (t % 9.0) / 9.0
        x = -0.4 * w + u * 1.8 * w
        g = cairo.LinearGradient(x - w * 0.18, 0, x + w * 0.18, h * 0.35)
        g.add_color_stop_rgba(0, *col, 0)
        g.add_color_stop_rgba(0.5, *col, 0.07)
        g.add_color_stop_rgba(1, *col, 0)
        cr.set_source(g)
        cr.paint()
    elif name == 'drift':   # motes of light rising slowly through the texture
        for k in range(max(14, int(w * h / 40000))):
            rnd = random.Random(k * 13 + 7)
            life = rnd.uniform(9, 16)
            age = (t + rnd.uniform(0, life)) % life
            f = age / life
            x = rnd.uniform(0, w) + math.sin(age * 0.8 + k) * 18
            y = h * (1.05 - f * 1.1)
            a = math.sin(f * math.pi) * rnd.uniform(0.10, 0.28)
            r = rnd.uniform(2, 6)
            g = cairo.RadialGradient(x, y, 0, x, y, r * 3)
            g.add_color_stop_rgba(0, *col, a)
            g.add_color_stop_rgba(1, *col, 0)
            cr.set_source(g)
            cr.arc(x, y, r * 3, 0, 2 * math.pi)
            cr.fill()
    elif name == 'flash':   # now and then the storm lights the texture up
        beat = t % 5.5
        a = 0.0
        for start in (0.0, 0.18):
            if start <= beat < start + 0.12:
                a = 0.10 * (1 - (beat - start) / 0.12)
        if a:
            cr.set_source_rgba(*col, a)
            cr.paint()
            rnd = random.Random(int(t / 5.5))
            pts = [(rnd.uniform(0.2, 0.8) * w, 0)]
            for i in range(1, 9):
                pts.append((pts[-1][0] + rnd.uniform(-40, 40), h * 0.6 * i / 8))
            for lw, al in ((6, a * 1.5), (1.5, a * 6)):
                cr.move_to(*pts[0])
                for p in pts[1:]:
                    cr.line_to(*p)
                cr.set_line_width(lw)
                cr.set_source_rgba(0.9, 0.95, 1, min(1, al))
                cr.stroke()


def sweep(cr, style, w, h, t, period=9.0):   # older callers
    draw_back(cr, 'sweep', style, w, h, t)


def mouth(t):
    """Pac-man's mouth opening (radians) at time t: chomping."""
    return 0.08 + 0.9 * abs(math.sin(t * 7.0))
