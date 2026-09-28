# =============================================================
# Author:  TechOGR
# Repo:    https://github.com/TechOGR/bspwm_dotfiles_arch
#
# riceanim - the motion of the themes in the Normal performance mode
# (bin/PerfProfile full): light running along the bar, the workspace
# pill and the focused window's frame, the pac-man chomping, ghosts
# floating, a slow light crossing the terminal textures. Each style has
# its own rhythm (Storm fast and flickering, Fire trembling, Nature slow).
# Lite keeps everything still. RICE_ANIM=1 / 0 forces it on / off.
#
# Copyright (C) 2021-2026 TechOGR <https://github.com/TechOGR>
# Licensed under GPL-3.0 license
# =============================================================

import math
import os
import random

FPS = 24

# style: (comets, seconds per lap, comet length (fraction of the outline),
#         flicker 0..1, color)  -- color None: the style's accent (NATIVE)
STYLE = {
    'glass': (1, 7.0, 0.10, 0.0, '#ffffff'),
    'cyber': (2, 3.5, 0.08, 0.15, None),
    'minimal': (1, 12.0, 0.06, 0.0, None),
    'pixel': (2, 5.0, 0.05, 0.0, None),
    'liquid': (2, 6.0, 0.14, 0.0, '#8fe6ff'),
    'hud': (2, 4.0, 0.07, 0.1, None),
    'fire': (3, 4.5, 0.10, 0.45, '#ffc400'),
    'nature': (1, 10.0, 0.12, 0.0, '#b9ff66'),
    'sketch': (1, 9.0, 0.08, 0.0, '#ffffff'),
    'crystal': (2, 6.0, 0.06, 0.1, '#ffffff'),
    'lava': (2, 7.0, 0.12, 0.35, '#ffd040'),
    'neon': (2, 4.0, 0.12, 0.05, None),
    'holo': (2, 6.5, 0.10, 0.1, '#ff8ae0'),
    'storm': (3, 2.2, 0.09, 0.6, '#dff0ff'),
    'venom': (2, 5.5, 0.12, 0.2, '#ff3a3a'),
    'butterfly': (2, 7.5, 0.11, 0.05, '#ffb8f0'),
    'snake': (1, 5.0, 0.18, 0.0, '#e8ff5a'),
}
DEFAULT = (1, 8.0, 0.08, 0.0, None)


def enabled():
    """Animations on? Normal mode (PerfProfile full), or forced by RICE_ANIM."""
    env = os.environ.get('RICE_ANIM')
    if env in ('0', '1'):
        return env == '1'
    try:
        import riceui
        return riceui.perf_profile() == 'full'
    except Exception:
        return False


def color(style):
    import wspill as ws
    c = STYLE.get(style, DEFAULT)[4] or ws.NATIVE.get(style, '#6fa8ff')
    return ws.rgb(c)


def flat_points(cr):
    """The current path as a flat list of (x, y) with cumulative lengths."""
    import cairo
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


def _segment(outline, a, b):
    """Points of the outline between lengths a and b (wrapping)."""
    pts, lens, total = outline
    if total <= 0:
        return []
    out = []
    for i in range(len(pts)):
        d = lens[i]
        rel = (d - a) % total
        if rel <= (b - a):
            out.append((rel, pts[i]))
    out.sort()
    return [p for _r, p in out]


def comets(style, outline, t, seed=0):
    """[(points, alpha)] of the style's comets at time t on the outline."""
    n, lap, frac, flick, _c = STYLE.get(style, DEFAULT)
    pts, lens, total = outline
    if total <= 0 or n <= 0:
        return []
    out = []
    length = total * frac
    for k in range(n):
        head = ((t / lap + k / n + seed * 0.137) % 1.0) * total
        seg = _segment(outline, head - length, head)
        if len(seg) < 2:
            continue
        a = 1.0
        if flick:
            rnd = random.Random(int(t * FPS) * 7 + k + seed)
            a = 1.0 - flick * rnd.random()
        out.append((seg, a))
    return out


def draw_comets(cr, style, outline, t, width=2.0, seed=0, scale=1.0):
    """Glowing tails of light running along the outline; returns the bbox
    (x0, y0, x1, y1) of what was drawn (to repaint only that), or None."""
    col = color(style)
    box = None
    for seg, a in comets(style, outline, t, seed):
        n = len(seg)
        chunks = min(8, n - 1)   # the tail in a few pieces, fading towards its end
        bounds = [round(i * (n - 1) / chunks) for i in range(chunks + 1)]
        cr.set_line_cap(1)   # round
        core = tuple(v + (1 - v) * 0.6 for v in col)   # nearly white: it reads over any frame
        for lw, al, cc in ((11 * scale, 0.14, col), (5.5 * scale, 0.32, col), (width * 1.3 * scale, 1.0, core)):
            cr.set_line_width(lw)
            for c in range(chunks):
                i0, i1 = bounds[c], bounds[c + 1]
                if i1 <= i0:
                    continue
                f = (c + 1) / chunks
                cr.move_to(*seg[i0])
                for pnt in seg[i0 + 1:i1 + 1]:
                    cr.line_to(*pnt)
                cr.set_source_rgba(*cc, al * a * f * f)
                cr.stroke()
        hx, hy = seg[-1]   # the head: a small bright spark
        import cairo
        g = cairo.RadialGradient(hx, hy, 0, hx, hy, 13 * scale)
        g.add_color_stop_rgba(0, 1, 1, 1, 1.0 * a)
        g.add_color_stop_rgba(0.25, *col, 0.75 * a)
        g.add_color_stop_rgba(1, *col, 0)
        cr.set_source(g)
        cr.arc(hx, hy, 13 * scale, 0, 2 * math.pi)
        cr.fill()
        xs = [p[0] for p in seg]
        ys = [p[1] for p in seg]
        pad = 15 * scale
        b = (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad)
        box = b if box is None else (min(box[0], b[0]), min(box[1], b[1]), max(box[2], b[2]), max(box[3], b[3]))
    return box


def mouth(t):
    """Pac-man's mouth opening (radians) at time t: chomping."""
    return 0.08 + 0.9 * abs(math.sin(t * 7.0))


def bob(t, i):
    """A ghost's float offset (px) at time t (i: its place, out of phase)."""
    return 1.3 * math.sin(t * 2.4 + i * 1.1)


def sweep(cr, style, w, h, t, period=9.0):
    """A soft diagonal band of light crossing a w x h area every period s
    (the terminal textures)."""
    import cairo
    col = color(style)
    u = (t % period) / period
    x = -0.4 * w + u * 1.8 * w
    g = cairo.LinearGradient(x - w * 0.18, 0, x + w * 0.18, h * 0.35)
    g.add_color_stop_rgba(0, *col, 0)
    g.add_color_stop_rgba(0.5, *col, 0.07)
    g.add_color_stop_rgba(1, *col, 0)
    cr.set_source(g)
    cr.paint()
