# =============================================================
# Author:  TechOGR
# Repo:    https://github.com/TechOGR/bspwm_dotfiles_arch
#
# wspill - the workspace "pill" of the bar, drawn with cairo in ten
# styles (Glassmorphism, Neon Cyberpunk, Minimal Dark, Gradient Pop,
# Pixel, macOS, Liquid, HUD, Fire, Nature). Shared by bin/WorkspacePill
# (the live widget over polybar) and RiceEditor (the style previews), so
# a preview is exactly what the bar shows.
#   focused desktop = pac-man · occupied = ghost · empty = dot
# No GTK here: only cairo + Pango for nothing but shapes.
#
# Copyright (C) 2021-2026 TechOGR <https://github.com/TechOGR>
# Licensed under GPL-3.0 license
# =============================================================

import math
import random

import cairo

PI = math.pi

# id, name, tagline -- 'classic' is polybar's own module (no widget)
STYLES = [
    ('classic', 'Classic', 'polybar icons, palette colors'),
    ('glass', 'Glassmorphism', 'modern and clean'),
    ('cyber', 'Neon Cyberpunk', 'futuristic and striking'),
    ('minimal', 'Minimal Dark', 'elegant and discreet'),
    ('gradient', 'Gradient Pop', 'modern and creative'),
    ('pixel', 'Pixel', 'retro and classic'),
    ('macos', 'macOS', 'simple and elegant'),
    ('liquid', 'Liquid', 'fluid and original'),
    ('hud', 'HUD', 'tech and professional'),
    ('fire', 'Fire', 'intense and different'),
    ('nature', 'Nature', 'calm and fresh'),
]
STYLE_IDS = [s[0] for s in STYLES]


def _parse(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def rgb(h):
    c = _parse(h)
    return _recolor(c) if _TINT[0] else c


# ─────────────────────────────────────────────────────────── recolor
# A style drawn with the colors of another palette (RiceEditor -> Palette):
# every color turns around the style's own accent hue towards the
# palette's accent, keeping its light and a part of its hue spread, so
# Nature's greens become Fire's oranges and ambers, leaves included.
import colorsys  # noqa: E402

_TINT = [None]   # (native hue, target hue, target saturation, target rgb)
NATIVE = {
    'glass': '#6fa8ff', 'cyber': '#19e6ff', 'minimal': '#a9c2ff', 'gradient': '#6a3cf5',
    'pixel': '#1f5bff', 'macos': '#5b8cff', 'liquid': '#3b6bff', 'hud': '#2d8cff',
    'fire': '#ff6a00', 'nature': '#2ee06f', 'sketch': '#d6d6d6', 'crystal': '#2f8cff',
    'lava': '#ff6a00', 'neon': '#2f6bff', 'holo': '#6a3cff',
}


def _recolor(c):
    nh, th, k, trgb, grey = _TINT[0]
    h, l, sat = colorsys.rgb_to_hls(*c)
    if grey:
        # a grey palette (Pencil, Minimal…): the style in monochrome, a hint
        # of the palette's own tone, the light kept
        y = 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]
        return tuple(y + (t - y) * 0.12 * min(1.0, l * 1.5) for t in trgb)
    if sat < 0.15 or nh is None:
        # greys of the style: a touch of the new color, more on light lines
        # than on dark fills (a dark card must stay dark)
        kk = (0.45 if nh is None else 0.25) * min(1.0, l * 1.4)
        return tuple(a + (b - a) * kk for a, b in zip(c, trgb))
    d = (h - nh + 0.5) % 1.0 - 0.5
    # the hue turns to the palette's, keeping some of the style's spread; the
    # saturation follows how vivid the palette is next to the style's accent
    return colorsys.hls_to_rgb((th + d * 0.35) % 1.0, l, max(0.0, min(1.0, sat * k)))


class tinted:
    """with tinted(style, '#ff7a18'): paint in that color (None: as is)."""

    def __init__(self, style, target):
        self.args = None
        if target and style in NATIVE and target.lower() != NATIVE[style]:
            n = _parse(NATIVE[style])
            t = _parse(target)
            nh, _l, ns = colorsys.rgb_to_hls(*n)
            th, _tl, _ts = colorsys.rgb_to_hls(*t)
            n_sv = colorsys.rgb_to_hsv(*n)[1]
            t_sv = colorsys.rgb_to_hsv(*t)[1]
            grey = t_sv < 0.12
            k = max(0.25, min(1.2, t_sv / max(0.2, n_sv)))
            self.args = (nh if ns >= 0.15 else None, th, k, t, grey)

    def __enter__(self):
        self.prev = _TINT[0]
        _TINT[0] = self.args
        return self

    def __exit__(self, *_):
        _TINT[0] = self.prev
        return False


def recolor_hex(style, target, hexv):
    """One '#hex' of a style in another palette (window border colors…)."""
    with tinted(style, target):
        r, g, b = rgb(hexv)
    return '#%02x%02x%02x' % tuple(max(0, min(255, round(v * 255))) for v in (r, g, b))


TINT_CONF = __import__('os').path.expanduser('~/.config/bspwm/config/tint.json')
TINT_PARTS = ['bar', 'workspaces', 'locks', 'windows']


def tint_target(part):
    """'#rrggbb' a part of the theme is recolored to, or None."""
    import json
    try:
        with open(TINT_CONF) as f:
            v = json.load(f).get(part)
        return v if isinstance(v, str) and len(v) == 7 and v.startswith('#') else None
    except (OSError, ValueError):
        return None


def set_tint(parts, target):
    """Recolor these parts to target ('#hex'), or back to the style's own (None)."""
    import json
    import os
    try:
        with open(TINT_CONF) as f:
            conf = json.load(f)
    except (OSError, ValueError):
        conf = {}
    for part in parts:
        if target:
            conf[part] = target
        else:
            conf.pop(part, None)
    tmp = TINT_CONF + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(conf, f, indent=2)
    os.replace(tmp, TINT_CONF)


# icon colors of each style: ghost, pac-man, dots (left -> right gradient)
COLORS = {
    'glass': ('#7fdcff', '#ffa3c8', ['#4fb4ff', '#3f9bff', '#8f7dff', '#e98bff']),
    'cyber': ('#28d9ff', '#ff2bd6', ['#a24dff', '#b43cff', '#d23cf0', '#ff2bd6']),
    'minimal': ('#a9c8ff', '#efe3cf', ['#9fb8ff', '#a9c2ff', '#b5c8ff', '#e8ecff']),
    'gradient': ('#6ff0ff', '#ffb8dc', ['#8fb4ff', '#a3adff', '#d6a6ff', '#ffe0f4']),
    'pixel': ('#1ea0ff', '#ffd21e', ['#ffffff', '#ffffff', '#ffffff', '#ffffff']),
    'macos': ('#c9f3ff', '#ffc2cf', ['#3d8bff', '#3f6dff', '#9c5cff', '#ff8ad8']),
    'liquid': ('#0b5cff', '#ff8fd0', ['#1235e0', '#1a2fd8', '#3a24c8', '#ff7ad9']),
    'hud': ('#39d0ff', '#ffb3c7', ['#7fc6ff', '#8fd0ff', '#9fd8ff', '#ffe3f0']),
    'fire': ('#ff8a1f', '#ffb300', ['#ff9a2e', '#ff9a2e', '#ff9a2e', '#ffa53a']),
    'nature': ('#7ff5d6', '#b9ff66', ['#42d9c6', '#3fe0b0', '#4de8a0', '#35f0b8']),
}
URGENT = '#ff4f6d'


def metrics(n, H):
    """Geometry for n desktops on a bar H px tall. win_* is the widget
    window; the pill sits in its middle with room for the decorations."""
    n = max(1, n)
    size = max(10, round(H * 0.56))
    step = max(size + 6, round(H * 1.12))
    pad = round(H * 0.72)
    pill_w = 2 * pad + step * (n - 1) + size
    side = round(H * 2.6)
    ext = 6
    return {'size': size, 'step': step, 'pad': pad, 'pill_w': pill_w, 'side': side, 'ext': ext,
            'win_w': pill_w + 2 * side, 'win_h': H + 2 * ext, 'H': H, 'n': n}


def color_at(stops, t):
    t = max(0.0, min(1.0, t)) * (len(stops) - 1)
    i = min(int(t), len(stops) - 2) if len(stops) > 1 else 0
    if len(stops) == 1:
        return rgb(stops[0])
    a, b = rgb(stops[i]), rgb(stops[i + 1])
    f = t - i
    return tuple(x + (y - x) * f for x, y in zip(a, b))


# ─────────────────────────────────────────────────────────── primitives
def rounded(cr, x, y, w, h, r):
    r = max(0, min(r, w / 2, h / 2))
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -PI / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, PI / 2)
    cr.arc(x + r, y + h - r, r, PI / 2, PI)
    cr.arc(x + r, y + r, r, PI, 3 * PI / 2)
    cr.close_path()


def halo(cr, x, y, r, c, a):
    g = cairo.RadialGradient(x, y, 0, x, y, r)
    g.add_color_stop_rgba(0, *c, a)
    g.add_color_stop_rgba(1, *c, 0)
    cr.set_source(g)
    cr.arc(x, y, r, 0, 2 * PI)
    cr.fill()


def glow_stroke(cr, path, c, width, layers=((9, 0.06), (5, 0.12), (2.5, 0.25)), source=None):
    for extra, a in layers:
        path()
        cr.set_line_width(width + extra)
        cr.set_source_rgba(*c, a)
        cr.stroke()
    path()
    cr.set_line_width(width)
    if source is not None:
        cr.set_source(source)
    else:
        cr.set_source_rgba(*c, 1)
    cr.stroke()


def hfade(x0, x1, c, a0, a1):
    g = cairo.LinearGradient(x0, 0, x1, 0)
    g.add_color_stop_rgba(0, *c, a0)
    g.add_color_stop_rgba(1, *c, a1)
    return g


def hline(cr, x0, x1, y, c, a_out, a_in, w=1.0):
    cr.move_to(x0, y)
    cr.line_to(x1, y)
    cr.set_line_width(w)
    cr.set_source(hfade(x0, x1, c, a_out, a_in))
    cr.stroke()


# ──────────────────────────────────────────────────────────────── icons
def ghost_path(cr, cx, cy, s):
    w, h = s * 0.92, s * 1.0
    x0, top, bot = cx - w / 2, cy - h / 2, cy + h / 2
    r = w / 2
    cr.new_path()
    cr.move_to(x0, top + r)
    cr.arc(cx, top + r, r, PI, 2 * PI)
    cr.line_to(x0 + w, bot)
    feet = 3
    fw = w / feet
    for i in range(feet):
        xr = x0 + w - i * fw
        cr.line_to(xr - fw / 2, bot - s * 0.17)
        cr.line_to(xr - fw, bot)
    cr.close_path()


def ghost(cr, cx, cy, s, c, alpha=1.0):
    ghost_path(cr, cx, cy, s)
    cr.set_source_rgba(*c, alpha)
    cr.fill()
    ey, ex = cy - s * 0.1, s * 0.2
    for dx in (-ex, ex):
        cr.save()
        cr.translate(cx + dx, ey)
        cr.scale(s * 0.13, s * 0.17)
        cr.arc(0, 0, 1, 0, 2 * PI)
        cr.restore()
        cr.set_source_rgba(1, 1, 1, 0.95 * alpha)
        cr.fill()
        cr.arc(cx + dx + s * 0.05, ey + s * 0.03, s * 0.075, 0, 2 * PI)
        cr.set_source_rgba(0.05, 0.08, 0.2, alpha)
        cr.fill()


def pac_path(cr, cx, cy, r, mouth=0.62):
    cr.new_path()
    cr.move_to(cx, cy)
    cr.arc(cx, cy, r, mouth / 2, 2 * PI - mouth / 2)
    cr.close_path()


def pacman(cr, cx, cy, s, c, alpha=1.0):
    r = s * 0.55
    pac_path(cr, cx, cy, r)
    cr.set_source_rgba(*c, alpha)
    cr.fill()
    cr.arc(cx + r * 0.08, cy - r * 0.5, r * 0.13, 0, 2 * PI)
    cr.set_source_rgba(0.08, 0.06, 0.12, 0.85 * alpha)
    cr.fill()


def dot(cr, cx, cy, s, c, alpha=1.0):
    cr.arc(cx, cy, s * 0.2, 0, 2 * PI)
    cr.set_source_rgba(*c, alpha)
    cr.fill()


SPRITES = {
    'ghost': ["...####...",
              ".########.",
              "##########",
              "#WWP##WWP#",
              "#WWP##WWP#",
              "##########",
              "##########",
              "##########",
              "##########",
              "#.##..##.#"],
    'pac': ["...####...",
            ".########.",
            "#####E##..",
            "######....",
            "####......",
            "####......",
            "######....",
            "########..",
            ".########.",
            "...####..."],
}


def pixel_icon(cr, kind, cx, cy, s, c):
    rows = SPRITES[kind]
    grid = len(rows)
    q = max(2, round(s * 1.1 / grid))
    x0, y0 = round(cx - q * grid / 2), round(cy - q * grid / 2)
    for r, line in enumerate(rows):
        for col, ch in enumerate(line):
            if ch == '.':
                continue
            cr.rectangle(x0 + col * q, y0 + r * q, q, q)
            if ch == 'W':
                cr.set_source_rgb(1, 1, 1)
            elif ch in 'PE':
                cr.set_source_rgb(0.05, 0.1, 0.35)
            else:
                cr.set_source_rgb(*c)
            cr.fill()


# ─────────────────────────────────────────────────────────────── frames
def pill_rect(m):
    ph = m['H'] + 2
    return m['side'], (m['win_h'] - ph) / 2, m['pill_w'], ph


def frame_glass(cr, m):
    px, py, pw, ph = pill_rect(m)
    W, cy = m['win_w'], m['win_h'] / 2
    blue = rgb('#6fa8ff')
    g = cairo.LinearGradient(0, 0, W, 0)
    for t, a in ((0, 0), (0.25, 0.10), (0.5, 0.16), (0.75, 0.10), (1, 0)):
        g.add_color_stop_rgba(t, *rgb('#3b5bdb'), a)
    cr.rectangle(0, cy - ph * 0.42, W, ph * 0.84)
    cr.set_source(g)
    cr.fill()
    for dy in (-ph * 0.2, ph * 0.2):
        hline(cr, 0, px, cy + dy, blue, 0, 0.55)
        hline(cr, px + pw, W, cy + dy, blue, 0.55, 0)
    path = lambda: rounded(cr, px, py, pw, ph, ph / 2)  # noqa: E731
    glow_stroke(cr, path, blue, 1, layers=((8, 0.05), (4, 0.10)))
    path()
    fill = cairo.LinearGradient(0, py, 0, py + ph)
    fill.add_color_stop_rgba(0, 0.75, 0.85, 1, 0.22)
    fill.add_color_stop_rgba(1, 0.35, 0.45, 0.9, 0.10)
    cr.set_source(fill)
    cr.fill()
    path()
    edge = cairo.LinearGradient(0, py, 0, py + ph)
    edge.add_color_stop_rgba(0, 1, 1, 1, 0.55)
    edge.add_color_stop_rgba(1, 0.7, 0.8, 1, 0.25)
    cr.set_source(edge)
    cr.set_line_width(1.2)
    cr.stroke()


def frame_cyber(cr, m):
    px, py, pw, ph = pill_rect(m)
    W, cy = m['win_w'], m['win_h'] / 2
    cyan, mag = rgb('#19e6ff'), rgb('#ff2bd6')
    c = ph * 0.5

    def path():
        cr.new_path()
        cr.move_to(px, cy)
        cr.line_to(px + c, py)
        cr.line_to(px + pw - c, py)
        cr.line_to(px + pw, cy)
        cr.line_to(px + pw - c, py + ph)
        cr.line_to(px + c, py + ph)
        cr.close_path()
    path()
    cr.set_source_rgba(*rgb('#0b0620'), 0.9)
    cr.fill()
    grad = cairo.LinearGradient(px, 0, px + pw, 0)
    grad.add_color_stop_rgba(0, *cyan, 1)
    grad.add_color_stop_rgba(1, *mag, 1)
    for extra, a in ((8, 0.07), (4, 0.16)):
        path()
        cr.set_line_width(1.8 + extra)
        g2 = cairo.LinearGradient(px, 0, px + pw, 0)
        g2.add_color_stop_rgba(0, *cyan, a)
        g2.add_color_stop_rgba(1, *mag, a)
        cr.set_source(g2)
        cr.stroke()
    path()
    cr.set_line_width(1.8)
    cr.set_source(grad)
    cr.stroke()
    # outer brackets
    o = 5
    for sgn, col, x_end in ((1, cyan, px), (-1, mag, px + pw)):
        for vy in (-1, 1):
            cr.move_to(x_end - sgn * o, cy)
            cr.line_to(x_end - sgn * o + sgn * c, cy + vy * (ph / 2 + 4))
            cr.line_to(x_end - sgn * o + sgn * (c + 26), cy + vy * (ph / 2 + 4))
        cr.set_line_width(1.4)
        cr.set_source_rgba(*col, 0.8)
        cr.stroke()
    # rails with dashes
    hline(cr, 14, px - o - 3, cy, cyan, 0.1, 0.85, 1.4)
    hline(cr, px + pw + o + 3, W - 14, cy, mag, 0.85, 0.1, 1.4)
    for i in range(3):
        cr.rectangle(8 + i * 7, cy - 1, 4, 2)
        cr.set_source_rgba(*cyan, 0.7 - i * 0.15)
        cr.fill()
    for i in range(3):
        x = W - 12 - i * 6
        cr.move_to(x, cy + 3)
        cr.line_to(x + 3, cy - 3)
        cr.set_line_width(1.5)
        cr.set_source_rgba(*mag, 0.8 - i * 0.2)
        cr.stroke()


def frame_minimal(cr, m):
    px, py, pw, ph = pill_rect(m)
    W, cy = m['win_w'], m['win_h'] / 2
    line = rgb('#3a4058')
    hline(cr, 0, px - 6, cy, line, 0, 0.8)
    hline(cr, px + pw + 6, W, cy, line, 0.8, 0)
    rounded(cr, px, py, pw, ph, ph / 2)
    cr.set_source_rgba(*rgb('#11141d'), 0.95)
    cr.fill_preserve()
    cr.set_source_rgba(*rgb('#3a4058'), 1)
    cr.set_line_width(1.2)
    cr.stroke()
    rounded(cr, px + 1.5, py + 1.5, pw - 3, ph - 3, ph / 2 - 1.5)
    cr.set_source_rgba(1, 1, 1, 0.04)
    cr.set_line_width(1)
    cr.stroke()


def frame_gradient(cr, m):
    px, py, pw, ph = pill_rect(m)
    path = lambda: rounded(cr, px, py, pw, ph, ph / 2)  # noqa: E731
    for extra, a in ((12, 0.05), (7, 0.10), (3, 0.18)):
        path()
        cr.set_line_width(extra)
        g = cairo.LinearGradient(px, 0, px + pw, 0)
        g.add_color_stop_rgba(0, *rgb('#2f6bff'), a)
        g.add_color_stop_rgba(1, *rgb('#e040fb'), a)
        cr.set_source(g)
        cr.stroke()
    path()
    g = cairo.LinearGradient(px, 0, px + pw, 0)
    g.add_color_stop_rgb(0, *rgb('#2462ff'))
    g.add_color_stop_rgb(0.5, *rgb('#6a3cf5'))
    g.add_color_stop_rgb(1, *rgb('#d63cf5'))
    cr.set_source(g)
    cr.fill()
    rounded(cr, px + 3, py + 2, pw - 6, ph * 0.46, ph * 0.23)
    gl = cairo.LinearGradient(0, py, 0, py + ph * 0.5)
    gl.add_color_stop_rgba(0, 1, 1, 1, 0.28)
    gl.add_color_stop_rgba(1, 1, 1, 1, 0)
    cr.set_source(gl)
    cr.fill()


def frame_pixel(cr, m):
    px, py, pw, ph = pill_rect(m)
    W, cy = m['win_w'], m['win_h'] / 2
    q = max(2, round(m['H'] / 10))
    x0, y0 = round(px), round(py)
    w, h = round(pw / q) * q, round(ph / q) * q
    blue, light, dark = rgb('#1f5bff'), rgb('#4f86ff'), rgb('#040a24')

    def notched(x, y, ww, hh, k):
        cr.new_path()
        cr.move_to(x + 2 * k, y)
        cr.line_to(x + ww - 2 * k, y)
        cr.line_to(x + ww - 2 * k, y + k)
        cr.line_to(x + ww - k, y + k)
        cr.line_to(x + ww - k, y + 2 * k)
        cr.line_to(x + ww, y + 2 * k)
        cr.line_to(x + ww, y + hh - 2 * k)
        cr.line_to(x + ww - k, y + hh - 2 * k)
        cr.line_to(x + ww - k, y + hh - k)
        cr.line_to(x + ww - 2 * k, y + hh - k)
        cr.line_to(x + ww - 2 * k, y + hh)
        cr.line_to(x + 2 * k, y + hh)
        cr.line_to(x + 2 * k, y + hh - k)
        cr.line_to(x + k, y + hh - k)
        cr.line_to(x + k, y + hh - 2 * k)
        cr.line_to(x, y + hh - 2 * k)
        cr.line_to(x, y + 2 * k)
        cr.line_to(x + k, y + 2 * k)
        cr.line_to(x + k, y + k)
        cr.line_to(x + 2 * k, y + k)
        cr.close_path()
    notched(x0, y0, w, h, q)
    cr.set_source_rgb(*blue)
    cr.fill()
    notched(x0 + q, y0 + q, w - 2 * q, h - 2 * q, q)
    cr.set_source_rgb(*light)
    cr.fill()
    notched(x0 + 2 * q, y0 + 2 * q, w - 4 * q, h - 4 * q, q)
    cr.set_source_rgb(*dark)
    cr.fill()
    yy = round(cy - q / 2)
    for sgn, start in ((-1, x0 - q), (1, x0 + w)):
        cr.rectangle(start if sgn > 0 else start - 6 * q + q, yy, 6 * q, q)
        cr.set_source_rgba(*blue, 0.9)
        cr.fill()
        for i in range(8):
            x = start + sgn * (7 + i * 2) * q
            cr.rectangle(x, yy, q, q)
            cr.set_source_rgba(*light, max(0.08, 0.7 - i * 0.09))
            cr.fill()


def frame_macos(cr, m):
    px, py, pw, ph = pill_rect(m)
    W, cy = m['win_w'], m['win_h'] / 2
    line = rgb('#4a5272')
    hline(cr, 0, px - 4, cy, line, 0, 0.6)
    hline(cr, px + pw + 4, W, cy, line, 0.6, 0)
    for i, a in enumerate((0.10, 0.07, 0.04)):
        rounded(cr, px - i, py + 2 + i, pw + 2 * i, ph, ph / 2 + i)
        cr.set_source_rgba(0, 0, 0, a)
        cr.fill()
    rounded(cr, px, py, pw, ph, ph / 2)
    g = cairo.LinearGradient(0, py, 0, py + ph)
    g.add_color_stop_rgba(0, *rgb('#454d6c'), 0.92)
    g.add_color_stop_rgba(1, *rgb('#2a3048'), 0.92)
    cr.set_source(g)
    cr.fill_preserve()
    cr.set_source_rgba(1, 1, 1, 0.22)
    cr.set_line_width(1)
    cr.stroke()
    rounded(cr, px + 1.5, py + 1.2, pw - 3, ph * 0.5, ph * 0.25)
    gl = cairo.LinearGradient(0, py, 0, py + ph * 0.5)
    gl.add_color_stop_rgba(0, 1, 1, 1, 0.10)
    gl.add_color_stop_rgba(1, 1, 1, 1, 0)
    cr.set_source(gl)
    cr.fill()


def frame_liquid(cr, m):
    px, py, pw, ph = pill_rect(m)
    cy = m['win_h'] / 2
    r = ph * 0.58
    top, bot = py - 1, py + ph + 1
    x0, x1 = px + r * 0.4, px + pw - r * 0.4

    def bump(t, at, width, height):
        return height * math.exp(-((t - at) / width) ** 2)

    def blob():
        cr.new_path()
        n = 60
        pts_top, pts_bot = [], []
        for i in range(n + 1):
            t = i / n
            x = x0 + (x1 - x0) * t
            pts_top.append((x, top - bump(t, 0.62, 0.16, 4) + bump(t, 0.33, 0.12, 2)))
            pts_bot.append((x, bot + bump(t, 0.30, 0.14, 4) - bump(t, 0.7, 0.12, 2)))
        cr.move_to(*pts_top[0])
        for pt in pts_top[1:]:
            cr.line_to(*pt)
        # bulbous right end
        cr.curve_to(x1 + r * 1.3, top - 2, x1 + r * 1.3, bot + 2, *pts_bot[-1])
        for pt in reversed(pts_bot[:-1]):
            cr.line_to(*pt)
        cr.curve_to(x0 - r * 1.3, bot + 2, x0 - r * 1.3, top - 2, *pts_top[0])
        cr.close_path()
    halo(cr, px + pw * 0.15, cy, ph * 1.3, rgb('#20c8ff'), 0.22)
    halo(cr, px + pw * 0.85, cy, ph * 1.3, rgb('#a45bff'), 0.22)
    for extra, a in ((8, 0.10), (4, 0.18)):
        blob()
        cr.set_line_width(extra)
        cr.set_source_rgba(*rgb('#5b7bff'), a)
        cr.stroke()
    g = cairo.LinearGradient(px, 0, px + pw, 0)
    g.add_color_stop_rgb(0, *rgb('#34dcff'))
    g.add_color_stop_rgb(0.5, *rgb('#5c86ff'))
    g.add_color_stop_rgb(1, *rgb('#b37cff'))
    blob()
    cr.set_source(g)
    cr.fill()
    cr.save()
    blob()
    cr.clip()
    hl = cairo.LinearGradient(0, py - 4, 0, cy)
    hl.add_color_stop_rgba(0, 1, 1, 1, 0.45)
    hl.add_color_stop_rgba(1, 1, 1, 1, 0)
    cr.rectangle(px - ph, py - 6, pw + 2 * ph, ph / 2 + 4)
    cr.set_source(hl)
    cr.fill()
    cr.restore()
    for x, y, rr, c in ((px - r * 1.05, cy + ph * 0.3, ph * 0.13, '#34dcff'),
                        (px - r * 1.45, cy - ph * 0.12, ph * 0.07, '#34dcff'),
                        (px + pw + r * 1.0, cy + ph * 0.18, ph * 0.12, '#b37cff'),
                        (px + pw + r * 1.35, cy - ph * 0.28, ph * 0.06, '#b37cff')):
        cr.arc(x, y, rr, 0, 2 * PI)
        cr.set_source_rgba(*rgb(c), 0.95)
        cr.fill()


def frame_hud(cr, m, focus_x=None):
    px, py, pw, ph = pill_rect(m)
    W, cy = m['win_w'], m['win_h'] / 2
    blue, soft = rgb('#2d8cff'), rgb('#7fc6ff')
    c = ph * 0.32

    def plate():
        cr.new_path()
        cr.move_to(px + c, py)
        cr.line_to(px + pw - c, py)
        cr.line_to(px + pw, py + c)
        cr.line_to(px + pw, py + ph - c)
        cr.line_to(px + pw - c, py + ph)
        cr.line_to(px + c, py + ph)
        cr.line_to(px, py + ph - c)
        cr.line_to(px, py + c)
        cr.close_path()
    plate()
    cr.set_source_rgba(*rgb('#061226'), 0.9)
    cr.fill()
    glow_stroke(cr, plate, blue, 1, layers=((5, 0.07), (2, 0.15)))
    # inner accent ticks
    for x in (px + c + 6, px + pw - c - 26):
        cr.move_to(x, py + 2.5)
        cr.line_to(x + 20, py + 2.5)
    cr.set_line_width(1.5)
    cr.set_source_rgba(*soft, 0.6)
    cr.stroke()
    # tech lines
    hline(cr, 4, px - 4, cy, blue, 0.15, 0.9)
    hline(cr, px + pw + 4, W - 4, cy, blue, 0.9, 0.15)
    for i in range(4):
        cr.rectangle(10 + i * 9, cy - 1.5, 5, 3)
        cr.rectangle(W - 15 - i * 9, cy - 1.5, 5, 3)
    cr.set_source_rgba(*soft, 0.55)
    cr.fill()
    cr.move_to(px + pw + 4, cy)
    cr.line_to(px + pw + 18, cy - 7)
    cr.line_to(W - 50, cy - 7)
    cr.set_line_width(1)
    cr.set_source_rgba(*blue, 0.6)
    cr.stroke()
    # targeting ring on the focused desktop
    if focus_x is not None:
        r = m['win_h'] / 2 - 1.5
        cr.arc(focus_x, cy, r - 3, 0, 2 * PI)
        cr.set_source_rgba(*rgb('#04101f'), 0.95)
        cr.fill()
        glow_stroke(cr, lambda: (cr.new_path(), cr.arc(focus_x, cy, r - 3, 0, 2 * PI)), blue, 1.4,
                    layers=((4, 0.1), (2, 0.2)))
        for a0, a1 in ((0.15, 1.2), (1.6, 2.6), (3.3, 4.3), (4.7, 5.9)):
            cr.new_path()
            cr.arc(focus_x, cy, r, a0, a1)
            cr.set_line_width(1.6)
            cr.set_source_rgba(*soft, 0.85)
            cr.stroke()
        cr.new_path()
        cr.arc(focus_x, cy, r - 6.5, 0, 2 * PI)
        cr.set_line_width(0.8)
        cr.set_source_rgba(*blue, 0.5)
        cr.stroke()


def frame_fire(cr, m):
    px, py, pw, ph = pill_rect(m)
    cy = m['win_h'] / 2
    rnd = random.Random(7)
    orange, yellow, red = rgb('#ff6a00'), rgb('#ffc400'), rgb('#ff2a00')
    halo(cr, px + pw * 0.15, cy, ph * 1.6, red, 0.22)
    halo(cr, px + pw * 0.85, cy, ph * 1.6, red, 0.22)

    def flame(x, y, dx, dy, length, width):
        # a tongue from (x, y) pointing along (dx, dy)
        nx, ny = -dy, dx
        tx, ty = x + dx * length, y + dy * length
        cr.new_path()
        cr.move_to(x + nx * width, y + ny * width)
        cr.curve_to(x + nx * width + dx * length * 0.5, y + ny * width + dy * length * 0.5,
                    tx + nx * width * 0.4, ty + ny * width * 0.4, tx, ty)
        cr.curve_to(tx - nx * width * 0.2, ty - ny * width * 0.2,
                    x - nx * width + dx * length * 0.3, y - ny * width + dy * length * 0.3,
                    x - nx * width, y - ny * width)
        cr.close_path()
        g = cairo.LinearGradient(x, y, tx, ty)
        g.add_color_stop_rgba(0, *orange, 0.95)
        g.add_color_stop_rgba(0.6, *yellow, 0.6)
        g.add_color_stop_rgba(1, *yellow, 0)
        cr.set_source(g)
        cr.fill()
    ext = m['ext']
    rounded(cr, px - 2, py - 2, pw + 4, ph + 4, ph / 2 + 2)
    cr.set_source_rgba(*orange, 0.18)
    cr.set_line_width(7)
    cr.stroke()
    x = px + ph * 0.6
    while x < px + pw - ph * 0.6:
        tall = rnd.random() < 0.4
        flame(x, py + 2, rnd.uniform(-0.35, 0.35), -1,
              rnd.uniform(ext + 1, ext + 5) if tall else rnd.uniform(2, ext), rnd.uniform(2.5, 4.5))
        if rnd.random() < 0.6:
            flame(x + rnd.uniform(-3, 3), py + ph - 2, rnd.uniform(-0.35, 0.35), 1,
                  rnd.uniform(2, ext + 2), rnd.uniform(2.5, 4))
        x += rnd.uniform(9, 17)
    for sgn, ex in ((-1, px + 2), (1, px + pw - 2)):
        for i in range(7):
            a = rnd.uniform(-1.0, 1.0)
            flame(ex, cy + a * ph * 0.3, sgn * math.cos(a * 0.5), math.sin(a * 0.9) * 0.7,
                  rnd.uniform(10, m['side'] * 0.45), rnd.uniform(2.5, 4.5))
    path = lambda: rounded(cr, px, py, pw, ph, ph / 2)  # noqa: E731
    path()
    cr.set_source_rgba(*rgb('#140704'), 0.94)
    cr.fill()
    grad = cairo.LinearGradient(0, py, 0, py + ph)
    grad.add_color_stop_rgb(0, *yellow)
    grad.add_color_stop_rgb(1, *orange)
    glow_stroke(cr, path, orange, 1.8, layers=((8, 0.10), (4, 0.22)), source=grad)


def leaf(cr, x, y, length, angle, c, vein=True):
    cr.save()
    cr.translate(x, y)
    cr.rotate(angle)
    w = length * 0.36
    cr.new_path()
    cr.move_to(0, 0)
    cr.curve_to(length * 0.3, -w, length * 0.75, -w * 0.9, length, 0)
    cr.curve_to(length * 0.75, w * 0.9, length * 0.3, w, 0, 0)
    cr.close_path()
    g = cairo.LinearGradient(0, -w, 0, w)
    g.add_color_stop_rgb(0, *[min(1, v * 1.25) for v in c])
    g.add_color_stop_rgb(1, *[v * 0.7 for v in c])
    cr.set_source(g)
    cr.fill()
    if vein:
        cr.move_to(0, 0)
        cr.line_to(length * 0.9, 0)
        cr.set_line_width(0.8)
        cr.set_source_rgba(0.02, 0.15, 0.05, 0.55)
        cr.stroke()
    cr.restore()


def frame_nature(cr, m):
    px, py, pw, ph = pill_rect(m)
    cy = m['win_h'] / 2
    green = rgb('#2ee06f')
    halo(cr, px + pw / 2, cy, pw * 0.55, rgb('#0c5a2a'), 0.35)
    path = lambda: rounded(cr, px, py, pw, ph, ph / 2)  # noqa: E731
    path()
    cr.set_source_rgba(*rgb('#04140a'), 0.92)
    cr.fill()
    glow_stroke(cr, path, green, 1.8, layers=((8, 0.07), (4, 0.18)))
    rounded(cr, px + 3, py + 3, pw - 6, ph - 6, (ph - 6) / 2)
    cr.set_source_rgba(*green, 0.25)
    cr.set_line_width(0.8)
    cr.stroke()
    L = m['side'] * 0.5
    leaves = [(-0.35, 1.0, '#2fbf55'), (0.45, 0.85, '#1f8f3a'), (-0.9, 0.7, '#6fdc7f'),
              (0.05, 0.62, '#3fd46a'), (1.1, 0.55, '#58c96a')]
    for ang, k, col in leaves:
        leaf(cr, px + 4, cy + ang * 3, L * k, PI + ang, rgb(col))
        leaf(cr, px + pw - 4, cy - ang * 3, L * k, -ang, rgb(col))


FRAMES = {'glass': frame_glass, 'cyber': frame_cyber, 'minimal': frame_minimal,
          'gradient': frame_gradient, 'pixel': frame_pixel, 'macos': frame_macos,
          'liquid': frame_liquid, 'hud': frame_hud, 'fire': frame_fire, 'nature': frame_nature}
GLOW = {'glass': 0.35, 'cyber': 0.5, 'gradient': 0.3, 'macos': 0.25, 'liquid': 0.3, 'hud': 0.45,
        'fire': 0.5, 'nature': 0.45, 'minimal': 0.12, 'pixel': 0}


# styles that draw their icons themselves: fn(cr, kind, x, y, s, rgb)
ICON_PAINTERS = {}


# ─────────────────────────────────────────────────────────────── public
def icon_centers(m):
    cy = m['win_h'] / 2
    x0 = m['side'] + m['pad'] + m['size'] / 2
    return [(x0 + i * m['step'], cy) for i in range(m['n'])]


def paint(cr, style, m, states, pal=None):
    """Draw the widget. states: 'focused' | 'occupied' | 'urgent' | 'empty'
    per desktop. pal (rgb palette) is only used by 'classic' previews."""
    centers = icon_centers(m)
    if style == 'classic':
        pal = pal or {}
        px, py, pw, ph = pill_rect(m)
        rounded(cr, px - 10, py, pw + 20, ph, 8)
        cr.set_source_rgba(*pal.get('bg', rgb('#1a1b26')), 1)
        cr.fill()
        for (x, y), st in zip(centers, states):
            s = m['size']
            if st == 'focused':
                pacman(cr, x, y, s * 0.85, pal.get('yellow', rgb('#e0af68')))
            elif st in ('occupied', 'urgent'):
                ghost(cr, x, y, s * 0.8, pal.get('red' if st == 'urgent' else 'blue', rgb('#7aa2f7')))
            else:
                dot(cr, x, y, s * 0.9, pal.get('magenta', rgb('#bb9af7')))
        return centers
    focus_x = next((x for (x, _y), st in zip(centers, states) if st == 'focused'), None)
    if style == 'hud':
        frame_hud(cr, m, focus_x)
    else:
        FRAMES[style](cr, m)
    ghost_c, pac_c, dots = COLORS[style]
    n = len(centers)
    for i, ((x, y), st) in enumerate(zip(centers, states)):
        s = m['size']
        t = i / max(1, n - 1)
        if st == 'focused':
            c = rgb(pac_c)
        elif st == 'urgent':
            c = rgb(URGENT)
        elif st == 'occupied':
            c = rgb(ghost_c)
        else:
            c = color_at(dots, t)
        g = GLOW[style]
        if g and st != 'empty':
            halo(cr, x, y, s * 1.0, c, g)
        elif g:
            halo(cr, x, y, s * 0.55, c, g * 0.8)
        kind = 'pac' if st == 'focused' else ('dot' if st == 'empty' else 'ghost')
        if style in ICON_PAINTERS:
            ICON_PAINTERS[style](cr, kind, x, y, s, c)
        elif style == 'pixel':
            if st == 'empty':
                q = max(2, round(s / 8))
                cr.rectangle(round(x - q), round(y - q), 2 * q, 2 * q)
                cr.set_source_rgb(*c)
                cr.fill()
            else:
                pixel_icon(cr, 'pac' if st == 'focused' else 'ghost', x, y, s, c)
        elif st == 'focused':
            pacman(cr, x, y, s * 1.05, c)
        elif st in ('occupied', 'urgent'):
            ghost(cr, x, y, s * 0.95, c)
        else:
            dot(cr, x, y, s * (1.1 if style in ('gradient', 'macos', 'liquid') else 0.95), c)
    return centers


# ═══════════════════════════════════════════════════════════ bar skins
# The whole polybar background in a style (bar_skin in polybar.json):
# polybar is made transparent and bin/WorkspacePill draws this under it.
def paint_bar(cr, style, W, rect, pal=None):
    """rect = (x, y, w, h) of the bar inside a window W px wide."""
    x, y, w, h = rect
    cy = y + h / 2
    BAR_SKINS.get(style, bar_minimal)(cr, x, y, w, h, cy)


_SHAPE = ['capsule']   # capsule | chamfer (Cyber bar style) | square (Strip)


def _capsule(cr, x, y, w, h, r=None):
    if _SHAPE[0] == 'square':
        rounded(cr, x, y, w, h, 2)
    elif _SHAPE[0] == 'chamfer':
        c = h * 0.45
        cr.new_path()
        cr.move_to(x + c, y)
        cr.line_to(x + w, y)
        cr.line_to(x + w - c, y + h)
        cr.line_to(x, y + h)
        cr.close_path()
    else:
        rounded(cr, x, y, w, h, h / 2 if r is None else r)


class bar_shape:
    """with bar_shape('chamfer'): the skins' capsules become that shape."""

    def __init__(self, shape):
        self.shape = shape

    def __enter__(self):
        self.prev, _SHAPE[0] = _SHAPE[0], self.shape

    def __exit__(self, *_):
        _SHAPE[0] = self.prev
        return False


def bar_glass(cr, x, y, w, h, cy):
    path = lambda: _capsule(cr, x, y, w, h)  # noqa: E731
    glow_stroke(cr, path, rgb('#6fa8ff'), 1, layers=((8, 0.05), (4, 0.09)))
    path()
    cr.set_source_rgba(*rgb('#0f1530'), 0.62)
    cr.fill()
    path()
    g = cairo.LinearGradient(0, y, 0, y + h)
    g.add_color_stop_rgba(0, 0.75, 0.85, 1, 0.16)
    g.add_color_stop_rgba(1, 0.35, 0.45, 0.9, 0.06)
    cr.set_source(g)
    cr.fill()
    # light sweeping across the glass
    sweep = cairo.LinearGradient(x, 0, x + w, 0)
    for t, a in ((0, 0), (0.18, 0.10), (0.3, 0), (0.7, 0), (0.82, 0.08), (1, 0)):
        sweep.add_color_stop_rgba(t, 0.7, 0.8, 1, a)
    path()
    cr.set_source(sweep)
    cr.fill()
    path()
    edge = cairo.LinearGradient(0, y, 0, y + h)
    edge.add_color_stop_rgba(0, 1, 1, 1, 0.45)
    edge.add_color_stop_rgba(1, 0.7, 0.8, 1, 0.18)
    cr.set_source(edge)
    cr.set_line_width(1.1)
    cr.stroke()


def bar_cyber(cr, x, y, w, h, cy):
    cyan, mag = rgb('#19e6ff'), rgb('#ff2bd6')
    c = h * 0.55

    def path():
        cr.new_path()
        cr.move_to(x, cy)
        cr.line_to(x + c, y)
        cr.line_to(x + w - c, y)
        cr.line_to(x + w, cy)
        cr.line_to(x + w - c, y + h)
        cr.line_to(x + c, y + h)
        cr.close_path()
    path()
    cr.set_source_rgba(*rgb('#0a0614'), 0.92)
    cr.fill()
    for extra, a in ((8, 0.06), (4, 0.14), (0, 1)):
        path()
        cr.set_line_width(1.6 + extra)
        g = cairo.LinearGradient(x, 0, x + w, 0)
        g.add_color_stop_rgba(0, *cyan, a)
        g.add_color_stop_rgba(0.5, *rgb('#8f3bff'), a)
        g.add_color_stop_rgba(1, *mag, a)
        cr.set_source(g)
        cr.stroke()
    # HUD notches on the edges
    for px_, col in ((x + w * 0.22, cyan), (x + w * 0.78, mag)):
        cr.move_to(px_ - 30, y + 2.5)
        cr.line_to(px_ + 30, y + 2.5)
        cr.move_to(px_ - 18, y + h - 2.5)
        cr.line_to(px_ + 18, y + h - 2.5)
        cr.set_line_width(1.5)
        cr.set_source_rgba(*col, 0.7)
        cr.stroke()
    for i in range(3):
        cr.move_to(x + c + 8 + i * 6, y + h - 3)
        cr.line_to(x + c + 11 + i * 6, y + 3)
        cr.move_to(x + w - c - 8 - i * 6, y + h - 3)
        cr.line_to(x + w - c - 11 - i * 6, y + 3)
    cr.set_line_width(1.4)
    cr.set_source_rgba(1, 1, 1, 0.25)
    cr.stroke()


def bar_minimal(cr, x, y, w, h, cy):
    _capsule(cr, x, y, w, h, 12)
    cr.set_source_rgba(*rgb('#0e1016'), 0.96)
    cr.fill_preserve()
    cr.set_source_rgba(*rgb('#2a2f42'), 1)
    cr.set_line_width(1)
    cr.stroke()
    rounded(cr, x + 1.5, y + 1.5, w - 3, h - 3, 10.5)
    cr.set_source_rgba(1, 1, 1, 0.03)
    cr.stroke()


def bar_gradient(cr, x, y, w, h, cy):
    path = lambda: _capsule(cr, x, y, w, h)  # noqa: E731
    for extra, a in ((10, 0.05), (5, 0.10)):
        path()
        cr.set_line_width(extra)
        g = cairo.LinearGradient(x, 0, x + w, 0)
        g.add_color_stop_rgba(0, *rgb('#2f6bff'), a)
        g.add_color_stop_rgba(1, *rgb('#e040fb'), a)
        cr.set_source(g)
        cr.stroke()
    path()
    g = cairo.LinearGradient(x, 0, x + w, 0)
    g.add_color_stop_rgba(0, *rgb('#1b3bc8'), 0.94)
    g.add_color_stop_rgba(0.5, *rgb('#4a22b8'), 0.94)
    g.add_color_stop_rgba(1, *rgb('#9a22b8'), 0.94)
    cr.set_source(g)
    cr.fill()
    rounded(cr, x + 4, y + 2, w - 8, h * 0.45, h * 0.22)
    gl = cairo.LinearGradient(0, y, 0, y + h * 0.5)
    gl.add_color_stop_rgba(0, 1, 1, 1, 0.18)
    gl.add_color_stop_rgba(1, 1, 1, 1, 0)
    cr.set_source(gl)
    cr.fill()


def bar_pixel(cr, x, y, w, h, cy):
    q = max(2, round(h / 10))
    x0, y0 = round(x), round(y)
    ww, hh = round(w / q) * q, round(h / q) * q
    for inset, col in ((0, '#1f5bff'), (q, '#4f86ff'), (2 * q, '#050a1f')):
        xx, yy, w2, h2 = x0 + inset, y0 + inset, ww - 2 * inset, hh - 2 * inset
        cr.new_path()
        cr.move_to(xx + 2 * q, yy)
        cr.line_to(xx + w2 - 2 * q, yy)
        cr.line_to(xx + w2 - 2 * q, yy + q)
        cr.line_to(xx + w2 - q, yy + q)
        cr.line_to(xx + w2 - q, yy + 2 * q)
        cr.line_to(xx + w2, yy + 2 * q)
        cr.line_to(xx + w2, yy + h2 - 2 * q)
        cr.line_to(xx + w2 - q, yy + h2 - 2 * q)
        cr.line_to(xx + w2 - q, yy + h2 - q)
        cr.line_to(xx + w2 - 2 * q, yy + h2 - q)
        cr.line_to(xx + w2 - 2 * q, yy + h2)
        cr.line_to(xx + 2 * q, yy + h2)
        cr.line_to(xx + 2 * q, yy + h2 - q)
        cr.line_to(xx + q, yy + h2 - q)
        cr.line_to(xx + q, yy + h2 - 2 * q)
        cr.line_to(xx, yy + h2 - 2 * q)
        cr.line_to(xx, yy + 2 * q)
        cr.line_to(xx + q, yy + 2 * q)
        cr.line_to(xx + q, yy + q)
        cr.line_to(xx + 2 * q, yy + q)
        cr.close_path()
        cr.set_source_rgba(*rgb(col), 0.97)
        cr.fill()
    # scanline dots along the bottom
    for i in range(int(ww / (6 * q))):
        cr.rectangle(x0 + 4 * q + i * 6 * q, y0 + hh - 3 * q, q, q)
    cr.set_source_rgba(*rgb('#1f5bff'), 0.35)
    cr.fill()


def bar_macos(cr, x, y, w, h, cy):
    for i, a in enumerate((0.12, 0.08, 0.05, 0.03)):
        _capsule(cr, x - i, y + 2 + i, w + 2 * i, h)
        cr.set_source_rgba(0, 0, 0, a)
        cr.fill()
    _capsule(cr, x, y, w, h)
    g = cairo.LinearGradient(0, y, 0, y + h)
    g.add_color_stop_rgba(0, *rgb('#3c4462'), 0.88)
    g.add_color_stop_rgba(1, *rgb('#252a40'), 0.88)
    cr.set_source(g)
    cr.fill_preserve()
    cr.set_source_rgba(1, 1, 1, 0.20)
    cr.set_line_width(1)
    cr.stroke()
    rounded(cr, x + 2, y + 1.2, w - 4, h * 0.5, h * 0.25)
    gl = cairo.LinearGradient(0, y, 0, y + h * 0.5)
    gl.add_color_stop_rgba(0, 1, 1, 1, 0.08)
    gl.add_color_stop_rgba(1, 1, 1, 1, 0)
    cr.set_source(gl)
    cr.fill()


def bar_liquid(cr, x, y, w, h, cy):
    r = h / 2

    def path():
        cr.new_path()
        n = 120
        top, bot = [], []
        for i in range(n + 1):
            t = i / n
            xx = x + r + (w - 2 * r) * t
            top.append((xx, y - 1.5 * math.sin(t * PI * 7) - 1.2 * math.sin(t * PI * 3 + 1)))
            bot.append((xx, y + h + 1.5 * math.sin(t * PI * 6 + 2) + 1.0 * math.sin(t * PI * 2.5)))
        cr.move_to(*top[0])
        for pt in top[1:]:
            cr.line_to(*pt)
        cr.curve_to(x + w + r * 0.3, top[-1][1], x + w + r * 0.3, bot[-1][1], *bot[-1])
        for pt in reversed(bot[:-1]):
            cr.line_to(*pt)
        cr.curve_to(x - r * 0.3, bot[0][1], x - r * 0.3, top[0][1], *top[0])
        cr.close_path()
    for extra, a in ((8, 0.08), (4, 0.14)):
        path()
        cr.set_line_width(extra)
        cr.set_source_rgba(*rgb('#3b6bff'), a)
        cr.stroke()
    path()
    g = cairo.LinearGradient(x, 0, x + w, 0)
    g.add_color_stop_rgba(0, *rgb('#0b6fa8'), 0.93)
    g.add_color_stop_rgba(0.5, *rgb('#1f2f9a'), 0.93)
    g.add_color_stop_rgba(1, *rgb('#5a2aa0'), 0.93)
    cr.set_source(g)
    cr.fill()
    cr.save()
    path()
    cr.clip()
    hl = cairo.LinearGradient(0, y - 3, 0, cy)
    hl.add_color_stop_rgba(0, 1, 1, 1, 0.28)
    hl.add_color_stop_rgba(1, 1, 1, 1, 0)
    cr.rectangle(x, y - 4, w, h / 2 + 4)
    cr.set_source(hl)
    cr.fill()
    cr.restore()


def bar_hud(cr, x, y, w, h, cy):
    blue, soft = rgb('#2d8cff'), rgb('#7fc6ff')
    c = h * 0.35

    def plate():
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
    plate()
    cr.set_source_rgba(*rgb('#050c18'), 0.93)
    cr.fill()
    glow_stroke(cr, plate, blue, 1, layers=((5, 0.07), (2, 0.14)))
    # corner brackets
    L = 16
    for sx, sy in ((x + 3, y + 3), (x + w - 3, y + 3), (x + 3, y + h - 3), (x + w - 3, y + h - 3)):
        dx = 1 if sx < x + w / 2 else -1
        dy = 1 if sy < cy else -1
        cr.move_to(sx + dx * (c * 0.6), sy)
        cr.line_to(sx + dx * (c * 0.6 + L), sy)
        cr.move_to(sx, sy + dy * (c * 0.6))
        cr.line_to(sx, sy + dy * min(h / 2 - 4, c * 0.6 + 4))
    cr.set_line_width(1.6)
    cr.set_source_rgba(*soft, 0.8)
    cr.stroke()
    # ticks along the bottom
    for i in range(int(w / 24)):
        tx = x + 40 + i * 24
        if tx > x + w - 40:
            break
        cr.move_to(tx, y + h - 1.5)
        cr.line_to(tx, y + h - (4 if i % 4 == 0 else 2.5))
    cr.set_line_width(1)
    cr.set_source_rgba(*blue, 0.45)
    cr.stroke()


def bar_fire(cr, x, y, w, h, cy):
    orange, yellow = rgb('#ff6a00'), rgb('#ffc400')
    rnd = random.Random(11)
    path = lambda: _capsule(cr, x, y, w, h)  # noqa: E731

    def flame(fx, fy, length, width):
        tx, ty = fx + rnd.uniform(-3, 3), fy - length
        cr.new_path()
        cr.move_to(fx - width, fy)
        cr.curve_to(fx - width, fy - length * 0.5, tx - width * 0.3, ty + length * 0.3, tx, ty)
        cr.curve_to(tx + width * 0.3, ty + length * 0.3, fx + width, fy - length * 0.5, fx + width, fy)
        cr.close_path()
        g = cairo.LinearGradient(fx, fy, tx, ty)
        g.add_color_stop_rgba(0, *orange, 0.9)
        g.add_color_stop_rgba(0.6, *yellow, 0.5)
        g.add_color_stop_rgba(1, *yellow, 0)
        cr.set_source(g)
        cr.fill()
    fx = x + h
    while fx < x + w - h:
        if rnd.random() < 0.55:
            flame(fx, y + 2, rnd.uniform(3, y + 1), rnd.uniform(2, 3.5))
        fx += rnd.uniform(14, 34)
    path()
    cr.set_source_rgba(*rgb('#120604'), 0.94)
    cr.fill()
    grad = cairo.LinearGradient(0, y, 0, y + h)
    grad.add_color_stop_rgb(0, *yellow)
    grad.add_color_stop_rgb(1, *orange)
    glow_stroke(cr, path, orange, 1.5, layers=((8, 0.08), (4, 0.18)), source=grad)
    for _ in range(18):   # embers
        cr.arc(rnd.uniform(x + h, x + w - h), rnd.uniform(y + h * 0.7, y + h - 3), rnd.uniform(0.6, 1.3), 0, 2 * PI)
        cr.set_source_rgba(*yellow, rnd.uniform(0.3, 0.7))
        cr.fill()


def bar_nature(cr, x, y, w, h, cy):
    green = rgb('#2ee06f')
    path = lambda: _capsule(cr, x, y, w, h)  # noqa: E731
    path()
    cr.set_source_rgba(*rgb('#06140c'), 0.93)
    cr.fill()
    glow_stroke(cr, path, green, 1.5, layers=((8, 0.06), (4, 0.14)))
    L = h * 0.9
    for ang, kk, col in ((-0.5, 1.0, '#2fbf55'), (0.5, 0.8, '#1f8f3a'), (-1.1, 0.7, '#6fdc7f'), (1.2, 0.6, '#58c96a')):
        leaf(cr, x + h * 0.35, cy + ang * 2, L * kk, PI + ang * 0.8, rgb(col))
        leaf(cr, x + w - h * 0.35, cy - ang * 2, L * kk, -ang * 0.8, rgb(col))
    # a small vine sprig every so often
    rnd = random.Random(5)
    vx = x + w * 0.12
    while vx < x + w * 0.9:
        if not (x + w * 0.35 < vx < x + w * 0.65):
            leaf(cr, vx, y + 1, rnd.uniform(6, 9), -PI / 2 + rnd.uniform(-0.8, 0.8), rgb('#2fbf55'), vein=False)
        vx += rnd.uniform(60, 120)


BAR_SKINS = {'glass': bar_glass, 'cyber': bar_cyber, 'minimal': bar_minimal, 'gradient': bar_gradient,
             'pixel': bar_pixel, 'macos': bar_macos, 'liquid': bar_liquid, 'hud': bar_hud,
             'fire': bar_fire, 'nature': bar_nature}


# ═════════════════════════════════════════════════ styles, second set
# Pencil / graphite, Crystal, Lava, Solid neon, Holographic
STYLES += [
    ('sketch', 'Pencil', 'hand drawn in graphite'),
    ('crystal', 'Crystal', 'frosted glass and light'),
    ('lava', 'Lava', 'cracked rock and fire'),
    ('neon', 'Solid Neon', 'clean neon outline'),
    ('holo', 'Holographic', 'space, orbits and particles'),
]
STYLE_IDS = [st[0] for st in STYLES]
COLORS.update({
    'sketch': ('#d4d4d4', '#dedede', ['#bdbdbd', '#c4c4c4', '#c9c9c9', '#cfcfcf']),
    'crystal': ('#c4e8ff', '#e8f5ff', ['#35c8ff', '#2fb4ff', '#4f9bff', '#9a8cff', '#e78cff']),
    'lava': ('#ff8a1f', '#ffa51f', ['#ff7a1a', '#ff7f1c', '#ff841e', '#ff8a20']),
    'neon': ('#1ec8ff', '#a855f7', ['#1e90ff', '#1ec8ff', '#6b6bff', '#a855f7', '#ff4fd8']),
    'holo': ('#cdbcff', '#eaf2ff', ['#6aa8ff', '#4fd8ff', '#5ff0e0', '#e3b3ff', '#ff8ae0']),
})
GLOW.update({'sketch': 0, 'crystal': 0.4, 'lava': 0.55, 'neon': 0.55, 'holo': 0.45})


# ───────────────────────────────────────────────────────────── helpers
def sketch_stroke(cr, path, c, passes=4, jitter=0.9, width=1.1, alpha=0.6, seed=3):
    """A path redrawn a few times off by a hair: a pencil line."""
    rnd = random.Random(seed)
    for _ in range(passes):
        cr.save()
        cr.translate(rnd.uniform(-jitter, jitter), rnd.uniform(-jitter, jitter))
        path()
        cr.restore()
        cr.set_line_width(width * rnd.uniform(0.6, 1.25))
        cr.set_source_rgba(*c, alpha * rnd.uniform(0.55, 1))
        cr.stroke()


def hatch(cr, clip, box, c, spacing=3.0, alpha=0.3, width=0.7):
    x, y, w, h = box
    cr.save()
    clip()
    cr.clip()
    i = -h
    while i < w:
        cr.move_to(x + i, y + h)
        cr.line_to(x + i + h, y)
        i += spacing
    cr.set_line_width(width)
    cr.set_source_rgba(*c, alpha)
    cr.stroke()
    cr.restore()


def capsule_points(x, y, w, h, step=3.0):
    """Points around a capsule, clockwise from the top-left, with the
    outward normal of each one."""
    r = h / 2
    pts = []
    n = max(2, int((w - 2 * r) / step))
    for i in range(n + 1):
        pts.append((x + r + (w - 2 * r) * i / n, y, 0, -1))
    k = max(6, int(PI * r / step))
    for i in range(1, k):
        a = -PI / 2 + PI * i / k
        pts.append((x + w - r + r * math.cos(a), y + r + r * math.sin(a), math.cos(a), math.sin(a)))
    for i in range(n + 1):
        pts.append((x + w - r - (w - 2 * r) * i / n, y + h, 0, 1))
    for i in range(1, k):
        a = PI / 2 + PI * i / k
        pts.append((x + r + r * math.cos(a), y + r + r * math.sin(a), math.cos(a), math.sin(a)))
    return pts


def jagged(cr, pts, rnd, amp, smooth=2):
    """Closed path through the points pushed out/in by a smoothed random."""
    raw = [rnd.uniform(-amp, amp) for _ in pts]
    offs = []
    for i in range(len(raw)):
        acc = [raw[(i + d) % len(raw)] for d in range(-smooth, smooth + 1)]
        offs.append(sum(acc) / len(acc))
    cr.new_path()
    for i, ((px, py, nx, ny), o) in enumerate(zip(pts, offs)):
        (cr.move_to if i == 0 else cr.line_to)(px + nx * o, py + ny * o)
    cr.close_path()


def sparkle(cr, x, y, r, c, a=1.0):
    cr.new_path()
    for i in range(8):
        ang = i * PI / 4
        rr = r if i % 2 == 0 else r * 0.22
        (cr.move_to if i == 0 else cr.line_to)(x + rr * math.cos(ang), y + rr * math.sin(ang))
    cr.close_path()
    cr.set_source_rgba(*c, a)
    cr.fill()
    halo(cr, x, y, r * 1.6, c, a * 0.35)


def neon_grad(x0, x1, stops, a=1.0):
    g = cairo.LinearGradient(x0, 0, x1, 0)
    for i, col in enumerate(stops):
        g.add_color_stop_rgba(i / max(1, len(stops) - 1), *rgb(col), a)
    return g


# ─────────────────────────────────────────────────────── sketch icons
def sketch_icons(cr, kind, x, y, s, c):
    ink = rgb('#f2f2f2')
    if kind == 'dot':
        cr.arc(x, y, s * 0.22, 0, 2 * PI)
        cr.set_source_rgba(*c, 0.9)
        cr.fill()
        sketch_stroke(cr, lambda: (cr.new_path(), cr.arc(x, y, s * 0.23, 0, 2 * PI)), ink, passes=2,
                      jitter=0.4, width=0.8, seed=int(x))
        return
    if kind == 'ghost':
        shape = lambda: ghost_path(cr, x, y, s * 0.95)  # noqa: E731
    else:
        shape = lambda: pac_path(cr, x, y, s * 0.55)  # noqa: E731
    shape()
    cr.set_source_rgba(*c, 0.95)
    cr.fill()
    hatch(cr, shape, (x - s, y - s, 2 * s, 2 * s), rgb('#3a3a3a'), spacing=2.4, alpha=0.35)
    sketch_stroke(cr, shape, ink, passes=3, jitter=0.5, width=0.9, seed=int(x))
    if kind == 'ghost':
        for dx in (-s * 0.19, s * 0.19):
            cr.save()
            cr.translate(x + dx, y - s * 0.1)
            cr.scale(s * 0.1, s * 0.15)
            cr.arc(0, 0, 1, 0, 2 * PI)
            cr.restore()
            cr.set_source_rgba(0.08, 0.08, 0.08, 0.95)
            cr.fill()
    else:
        cr.arc(x + s * 0.05, y - s * 0.28, s * 0.07, 0, 2 * PI)
        cr.set_source_rgba(0.08, 0.08, 0.08, 0.95)
        cr.fill()


ICON_PAINTERS['sketch'] = sketch_icons


# ─────────────────────────────────────────────────────────── pill frames
def frame_sketch(cr, m):
    px, py, pw, ph = pill_rect(m)
    W, cy = m['win_w'], m['win_h'] / 2
    lead = rgb('#d6d6d6')
    outer = lambda: rounded(cr, px, py, pw, ph, ph / 2)  # noqa: E731
    outer()
    cr.set_source_rgba(*rgb('#141414'), 0.94)
    cr.fill()
    hatch(cr, outer, (px, py + ph * 0.55, pw, ph * 0.45), lead, spacing=5, alpha=0.08)
    sketch_stroke(cr, outer, lead, passes=5, jitter=1.1, width=1.2, alpha=0.7, seed=1)
    sketch_stroke(cr, lambda: rounded(cr, px + 3.5, py + 3.5, pw - 7, ph - 7, (ph - 7) / 2), lead,
                  passes=3, jitter=0.7, width=0.8, alpha=0.45, seed=2)
    # construction lines past the pill, like a draft
    rnd = random.Random(9)
    for yy in (py - 0.5, py + ph + 0.5):
        cr.move_to(px - rnd.uniform(14, 26), yy + rnd.uniform(-0.6, 0.6))
        cr.line_to(px + pw + rnd.uniform(14, 26), yy + rnd.uniform(-0.6, 0.6))
    for xx in (px + ph * 0.5, px + pw - ph * 0.5):
        cr.move_to(xx + rnd.uniform(-1, 1), py - 5)
        cr.line_to(xx + rnd.uniform(-1, 1), py + ph + 5)
    cr.set_line_width(0.6)
    cr.set_source_rgba(*lead, 0.28)
    cr.stroke()
    # doodles: a crown on the right, scribbles on the left
    kx, ky = px + pw + m['side'] * 0.45, cy - 5
    crown = lambda: (cr.new_path(), cr.move_to(kx - 9, ky + 7), cr.line_to(kx - 9, ky - 3),  # noqa: E731
                     cr.line_to(kx - 4, ky + 2), cr.line_to(kx, ky - 6), cr.line_to(kx + 4, ky + 2),
                     cr.line_to(kx + 9, ky - 3), cr.line_to(kx + 9, ky + 7), cr.close_path())
    sketch_stroke(cr, crown, lead, passes=3, jitter=0.5, width=0.9, alpha=0.8, seed=4)
    for i in range(5):
        sx = px - 10 - i * 5
        cr.move_to(sx, cy + 6)
        cr.line_to(sx + 4, cy + 1)
    cr.set_line_width(0.8)
    cr.set_source_rgba(*lead, 0.35)
    cr.stroke()


def frame_crystal(cr, m):
    px, py, pw, ph = pill_rect(m)
    W, cy = m['win_w'], m['win_h'] / 2
    ice, blue = rgb('#bfe6ff'), rgb('#2f8cff')
    path = lambda: rounded(cr, px, py, pw, ph, ph / 2)  # noqa: E731
    halo(cr, px + pw * 0.2, cy, ph * 1.5, blue, 0.18)
    halo(cr, px + pw * 0.85, cy, ph * 1.5, rgb('#8a5cff'), 0.14)
    glow_stroke(cr, path, blue, 1, layers=((10, 0.05), (5, 0.10)))
    path()
    g = cairo.LinearGradient(0, py, 0, py + ph)
    g.add_color_stop_rgba(0, 0.85, 0.93, 1, 0.20)
    g.add_color_stop_rgba(0.5, 0.35, 0.55, 0.95, 0.10)
    g.add_color_stop_rgba(1, 0.55, 0.75, 1, 0.18)
    cr.set_source(g)
    cr.fill()
    # thick bright rim, cold at the bottom
    path()
    rim = cairo.LinearGradient(0, py, 0, py + ph)
    rim.add_color_stop_rgba(0, 1, 1, 1, 0.95)
    rim.add_color_stop_rgba(0.5, *ice, 0.45)
    rim.add_color_stop_rgba(1, *rgb('#6fc8ff'), 0.85)
    cr.set_source(rim)
    cr.set_line_width(2.2)
    cr.stroke()
    rounded(cr, px + 3, py + 3, pw - 6, ph - 6, (ph - 6) / 2)
    cr.set_source_rgba(1, 1, 1, 0.22)
    cr.set_line_width(0.9)
    cr.stroke()
    # specular streak along the top and a sparkle on the right end
    cr.move_to(px + ph * 0.55, py + 3.2)
    cr.line_to(px + pw * 0.45, py + 3.2)
    cr.set_line_width(1.6)
    cr.set_source(hfade(px + ph * 0.55, px + pw * 0.45, (1, 1, 1), 0.85, 0))
    cr.stroke()
    sparkle(cr, px + pw - ph * 0.35, py + 2, 5, (1, 1, 1), 0.95)
    # reflection on the "floor"
    cr.move_to(px + ph * 0.5, py + ph + 3.5)
    cr.line_to(px + pw - ph * 0.5, py + ph + 3.5)
    cr.set_line_width(1.2)
    rg = cairo.LinearGradient(px, 0, px + pw, 0)
    for t, a in ((0, 0), (0.3, 0.35), (0.7, 0.35), (1, 0)):
        rg.add_color_stop_rgba(t, *rgb('#6fc8ff'), a)
    cr.set_source(rg)
    cr.stroke()


def lava_rim(cr, x, y, w, h, seed, amp_rock=3.0, cracks=True):
    rnd = random.Random(seed)
    pts = capsule_points(x, y, w, h, 2.5)
    # rock ring
    jagged(cr, [(px + nx * 5.5, py + ny * 5.5, nx, ny) for px, py, nx, ny in pts], rnd, amp_rock + 1, smooth=1)
    g = cairo.LinearGradient(0, y - 4, 0, y + h + 4)
    g.add_color_stop_rgb(0, *rgb('#3a2319'))
    g.add_color_stop_rgb(1, *rgb('#1a0d08'))
    cr.set_source(g)
    cr.fill()
    # molten seam
    seam = lambda: jagged(cr, pts, random.Random(seed + 1), 1.4, smooth=1)  # noqa: E731
    for extra, a, col in ((9, 0.10, '#ff2a00'), (5, 0.22, '#ff4a00'), (2.2, 0.9, '#ff6a00'), (0.9, 1, '#ffd23a')):
        seam()
        cr.set_line_width(extra)
        cr.set_source_rgba(*rgb(col), a)
        cr.stroke()
    # inner dark basin
    rounded(cr, x + 2.5, y + 2.5, w - 5, h - 5, (h - 5) / 2)
    cr.set_source_rgba(*rgb('#0d0604'), 0.96)
    cr.fill()
    if cracks:   # glowing cracks running into the rock
        for px_, py_, nx, ny in pts[::9]:
            if rnd.random() < 0.55:
                length = rnd.uniform(3, 7)
                cr.move_to(px_, py_)
                cr.line_to(px_ + nx * length * 0.5 + rnd.uniform(-2, 2), py_ + ny * length * 0.5)
                cr.line_to(px_ + nx * length + rnd.uniform(-2, 2), py_ + ny * length)
        cr.set_line_width(1)
        cr.set_source_rgba(*rgb('#ff7a18'), 0.85)
        cr.stroke()


def rock_shard(cr, x, y, r, rnd):
    cr.new_path()
    k = rnd.randint(4, 6)
    a0 = rnd.uniform(0, PI)
    for i in range(k):
        a = a0 + 2 * PI * i / k
        rr = r * rnd.uniform(0.6, 1.1)
        (cr.move_to if i == 0 else cr.line_to)(x + rr * math.cos(a), y + rr * math.sin(a))
    cr.close_path()
    cr.set_source_rgb(*rgb('#2a1710'))
    cr.fill_preserve()
    cr.set_source_rgba(*rgb('#ff5a00'), 0.7)
    cr.set_line_width(0.8)
    cr.stroke()


def frame_lava(cr, m):
    px, py, pw, ph = pill_rect(m)
    W, cy = m['win_w'], m['win_h'] / 2
    halo(cr, px + pw * 0.15, cy, ph * 1.5, rgb('#ff2a00'), 0.25)
    halo(cr, px + pw * 0.85, cy, ph * 1.5, rgb('#ff2a00'), 0.25)
    lava_rim(cr, px, py + 1, pw, ph - 2, seed=21)
    rnd = random.Random(8)
    for side in (-1, 1):
        base = px - 8 if side < 0 else px + pw + 8
        for i in range(4):
            rock_shard(cr, base + side * rnd.uniform(4, m['side'] * 0.6), cy + rnd.uniform(-8, 8),
                       rnd.uniform(2, 4.5), rnd)
        for i in range(10):
            cr.arc(base + side * rnd.uniform(0, m['side'] * 0.8), cy + rnd.uniform(-12, 12),
                   rnd.uniform(0.5, 1.2), 0, 2 * PI)
            cr.set_source_rgba(*rgb(rnd.choice(['#ff7a18', '#ffc400', '#ff3a00'])), rnd.uniform(0.4, 0.9))
            cr.fill()


def frame_neon(cr, m):
    px, py, pw, ph = pill_rect(m)
    path = lambda: rounded(cr, px + 1, py + 1, pw - 2, ph - 2, (ph - 2) / 2)  # noqa: E731
    stops = ['#19d4ff', '#2f6bff', '#8b3dff', '#ff3fd8']
    path()
    cr.set_source_rgba(*rgb('#070a18'), 0.94)
    cr.fill()
    for extra, a in ((16, 0.05), (10, 0.10), (5, 0.22)):
        path()
        cr.set_line_width(2.6 + extra)
        cr.set_source(neon_grad(px, px + pw, stops, a))
        cr.stroke()
    path()
    cr.set_line_width(2.6)
    cr.set_source(neon_grad(px, px + pw, stops))
    cr.stroke()
    path()
    cr.set_line_width(0.8)
    cr.set_source_rgba(1, 1, 1, 0.55)
    cr.stroke()


def orbit(cr, cx, cy, rx, ry, rot, a, width=1.0, beads=True, rnd=None):
    cr.save()
    cr.translate(cx, cy)
    cr.rotate(rot)
    cr.scale(rx, ry)
    cr.new_path()
    cr.arc(0, 0, 1, 0, 2 * PI)
    cr.restore()
    g = cairo.LinearGradient(cx - rx, 0, cx + rx, 0)
    g.add_color_stop_rgba(0, *rgb('#4fd8ff'), a)
    g.add_color_stop_rgba(0.5, *rgb('#b07cff'), a * 0.5)
    g.add_color_stop_rgba(1, *rgb('#ff6ad5'), a)
    cr.set_source(g)
    cr.set_line_width(width)
    cr.stroke()
    if beads:
        for t, col in ((PI + 0.25, '#4fd8ff'), (-0.3, '#ff8ae0')):
            bx = cx + rx * math.cos(t) * math.cos(rot) - ry * math.sin(t) * math.sin(rot)
            by = cy + rx * math.cos(t) * math.sin(rot) + ry * math.sin(t) * math.cos(rot)
            halo(cr, bx, by, 6, rgb(col), 0.5)
            cr.arc(bx, by, 2.2, 0, 2 * PI)
            cr.set_source_rgba(*rgb(col), 1)
            cr.fill()


def stars(cr, box, n, seed, colors=('#ffffff', '#9fd8ff', '#ffb8f0')):
    x, y, w, h = box
    rnd = random.Random(seed)
    for _ in range(n):
        sx, sy = rnd.uniform(x, x + w), rnd.uniform(y, y + h)
        r = rnd.uniform(0.4, 1.1)
        cr.arc(sx, sy, r, 0, 2 * PI)
        cr.set_source_rgba(*rgb(rnd.choice(colors)), rnd.uniform(0.35, 0.9))
        cr.fill()


def frame_holo(cr, m):
    px, py, pw, ph = pill_rect(m)
    W, cy = m['win_w'], m['win_h'] / 2
    stars(cr, (0, 0, W, m['win_h']), 40, 13)
    halo(cr, px + pw * 0.2, cy, ph * 1.6, rgb('#3b5bff'), 0.25)
    halo(cr, px + pw * 0.8, cy, ph * 1.6, rgb('#c03cff'), 0.25)
    for i, (dx, dy, rot, a) in enumerate(((26, 3, -0.035, 0.55), (16, 5, 0.03, 0.4), (36, 1, 0.012, 0.3))):
        orbit(cr, px + pw / 2, cy, pw / 2 + dx, ph / 2 + dy, rot, a, beads=(i == 0))
    path = lambda: rounded(cr, px, py, pw, ph, ph / 2)  # noqa: E731
    path()
    cr.set_source(neon_grad(px, px + pw, ['#1b3cff', '#6a3cff', '#c43cf0', '#ff4fd8'], 0.38))
    cr.fill()
    path()
    cr.set_source_rgba(*rgb('#0a0820'), 0.35)
    cr.fill()
    rounded(cr, px + 3, py + 2, pw - 6, ph * 0.45, ph * 0.22)
    gl = cairo.LinearGradient(0, py, 0, py + ph * 0.5)
    gl.add_color_stop_rgba(0, 1, 1, 1, 0.28)
    gl.add_color_stop_rgba(1, 1, 1, 1, 0)
    cr.set_source(gl)
    cr.fill()
    glow_stroke(cr, path, rgb('#b07cff'), 1.4, layers=((8, 0.08), (4, 0.18)),
                source=neon_grad(px, px + pw, ['#8fe6ff', '#ffffff', '#ffb8f0'], 0.9))


FRAMES.update({'sketch': frame_sketch, 'crystal': frame_crystal, 'lava': frame_lava,
               'neon': frame_neon, 'holo': frame_holo})


# ─────────────────────────────────────────────────────────── bar skins
def bar_sketch(cr, x, y, w, h, cy):
    lead = rgb('#d6d6d6')
    outer = lambda: _capsule(cr, x, y, w, h)  # noqa: E731
    outer()
    cr.set_source_rgba(*rgb('#141414'), 0.95)
    cr.fill()
    hatch(cr, outer, (x, y + h * 0.6, w, h * 0.4), lead, spacing=6, alpha=0.06)
    sketch_stroke(cr, outer, lead, passes=5, jitter=1.2, width=1.2, alpha=0.65, seed=31)
    sketch_stroke(cr, lambda: _capsule(cr, x + 3.5, y + 3.5, w - 7, h - 7), lead, passes=2, jitter=0.8,
                  width=0.8, alpha=0.35, seed=32)
    rnd = random.Random(33)
    for yy in (y - 0.5, y + h + 0.5):   # construction lines overshooting the ends
        cr.move_to(x - rnd.uniform(10, 22), yy)
        cr.line_to(x + h, yy)
        cr.move_to(x + w - h, yy)
        cr.line_to(x + w + rnd.uniform(10, 22), yy)
    for xx in (x + h / 2, x + w - h / 2):
        cr.move_to(xx, y - 6)
        cr.line_to(xx, y + h + 6)
    cr.set_line_width(0.6)
    cr.set_source_rgba(*lead, 0.3)
    cr.stroke()
    for i in range(6):   # pencil scribbles past the ends
        cr.move_to(x - 6 - i * 4, cy + 5)
        cr.line_to(x - 3 - i * 4, cy - 1)
        cr.move_to(x + w + 3 + i * 4, cy + 5)
        cr.line_to(x + w + 6 + i * 4, cy - 1)
    cr.set_line_width(0.8)
    cr.set_source_rgba(*lead, 0.3)
    cr.stroke()


def bar_crystal(cr, x, y, w, h, cy):
    ice, blue = rgb('#bfe6ff'), rgb('#2f8cff')
    path = lambda: _capsule(cr, x, y, w, h)  # noqa: E731
    glow_stroke(cr, path, blue, 1, layers=((10, 0.05), (5, 0.10)))
    path()
    cr.set_source_rgba(*rgb('#0a1228'), 0.55)
    cr.fill()
    path()
    g = cairo.LinearGradient(0, y, 0, y + h)
    g.add_color_stop_rgba(0, 0.85, 0.93, 1, 0.18)
    g.add_color_stop_rgba(0.5, 0.35, 0.55, 0.95, 0.06)
    g.add_color_stop_rgba(1, 0.55, 0.75, 1, 0.14)
    cr.set_source(g)
    cr.fill()
    path()
    rim = cairo.LinearGradient(0, y, 0, y + h)
    rim.add_color_stop_rgba(0, 1, 1, 1, 0.9)
    rim.add_color_stop_rgba(0.5, *ice, 0.35)
    rim.add_color_stop_rgba(1, *rgb('#6fc8ff'), 0.8)
    cr.set_source(rim)
    cr.set_line_width(2)
    cr.stroke()
    for x0, x1 in ((x + h * 0.6, x + w * 0.3), (x + w * 0.55, x + w * 0.7)):
        cr.move_to(x0, y + 3)
        cr.line_to(x1, y + 3)
        cr.set_line_width(1.4)
        cr.set_source(hfade(x0, x1, (1, 1, 1), 0.7, 0))
        cr.stroke()
    sparkle(cr, x + w - h * 0.4, y + 2, 5, (1, 1, 1), 0.95)
    sparkle(cr, x + h * 0.3, y + h - 2, 3.5, ice, 0.8)
    cr.move_to(x + h, y + h + 3.5)
    cr.line_to(x + w - h, y + h + 3.5)
    rg = cairo.LinearGradient(x, 0, x + w, 0)
    for t, a in ((0, 0), (0.2, 0.3), (0.8, 0.3), (1, 0)):
        rg.add_color_stop_rgba(t, *rgb('#6fc8ff'), a)
    cr.set_source(rg)
    cr.set_line_width(1.1)
    cr.stroke()


def bar_lava(cr, x, y, w, h, cy):
    rnd = random.Random(41)
    for fx in (0.08, 0.35, 0.65, 0.92):
        halo(cr, x + w * fx, cy, h * 1.4, rgb('#ff2a00'), 0.14)
    lava_rim(cr, x, y + 1, w, h - 2, seed=42)
    for side, base in ((-1, x - 4), (1, x + w + 4)):
        for i in range(5):
            rock_shard(cr, base + side * rnd.uniform(2, 26), cy + rnd.uniform(-9, 9), rnd.uniform(2, 4.5), rnd)
    for _ in range(40):   # embers floating over the bar
        cr.arc(rnd.uniform(x, x + w), rnd.uniform(max(0, y - 7), y + 1), rnd.uniform(0.5, 1.2), 0, 2 * PI)
        cr.set_source_rgba(*rgb(rnd.choice(['#ff7a18', '#ffc400', '#ff3a00'])), rnd.uniform(0.35, 0.9))
        cr.fill()


def bar_neon(cr, x, y, w, h, cy):
    path = lambda: _capsule(cr, x + 1, y + 1, w - 2, h - 2)  # noqa: E731
    stops = ['#19d4ff', '#2f6bff', '#8b3dff', '#ff3fd8']
    path()
    cr.set_source_rgba(*rgb('#070a18'), 0.94)
    cr.fill()
    for extra, a in ((14, 0.05), (8, 0.10), (4, 0.22)):
        path()
        cr.set_line_width(2.4 + extra)
        cr.set_source(neon_grad(x, x + w, stops, a))
        cr.stroke()
    path()
    cr.set_line_width(2.4)
    cr.set_source(neon_grad(x, x + w, stops))
    cr.stroke()
    path()
    cr.set_line_width(0.7)
    cr.set_source_rgba(1, 1, 1, 0.5)
    cr.stroke()


def bar_holo(cr, x, y, w, h, cy):
    stars(cr, (x - 20, max(0, y - 8), w + 40, h + 14), int(w / 18), 51)
    for fx, col in ((0.1, '#3b5bff'), (0.5, '#6a3cff'), (0.9, '#c03cff')):
        halo(cr, x + w * fx, cy, h * 2, rgb(col), 0.14)
    for dx, dy, rot, a in ((18, 3, -0.004, 0.5), (10, 5, 0.003, 0.35)):
        orbit(cr, x + w / 2, cy, w / 2 + dx, h / 2 + dy, rot, a, beads=(dx == 18))
    path = lambda: _capsule(cr, x, y, w, h)  # noqa: E731
    path()
    cr.set_source_rgba(*rgb('#0a0820'), 0.72)
    cr.fill()
    path()
    cr.set_source(neon_grad(x, x + w, ['#1b3cff', '#6a3cff', '#c43cf0', '#ff4fd8'], 0.22))
    cr.fill()
    rounded(cr, x + 4, y + 2, w - 8, h * 0.45, h * 0.22)
    gl = cairo.LinearGradient(0, y, 0, y + h * 0.5)
    gl.add_color_stop_rgba(0, 1, 1, 1, 0.16)
    gl.add_color_stop_rgba(1, 1, 1, 1, 0)
    cr.set_source(gl)
    cr.fill()
    glow_stroke(cr, path, rgb('#b07cff'), 1.3, layers=((8, 0.06), (4, 0.14)),
                source=neon_grad(x, x + w, ['#8fe6ff', '#ffffff', '#ffb8f0'], 0.85))


# ───────────────────────────── first-set skins redone to match the pills
def bar_liquid(cr, x, y, w, h, cy):
    """Same glossy candy as the Liquid pill: bright gradient, wavy edges,
    droplets past both ends (a deeper tone keeps the bar text readable)."""
    r = h / 2

    def path():
        cr.new_path()
        n = 160
        top, bot = [], []
        for i in range(n + 1):
            t = i / n
            xx = x + r + (w - 2 * r) * t
            top.append((xx, y - 1.8 * math.sin(t * PI * 9) - 1.4 * math.sin(t * PI * 4 + 1)))
            bot.append((xx, y + h + 1.8 * math.sin(t * PI * 8 + 2) + 1.2 * math.sin(t * PI * 3)))
        cr.move_to(*top[0])
        for pt in top[1:]:
            cr.line_to(*pt)
        cr.curve_to(x + w + r * 0.35, top[-1][1] - 2, x + w + r * 0.35, bot[-1][1] + 2, *bot[-1])
        for pt in reversed(bot[:-1]):
            cr.line_to(*pt)
        cr.curve_to(x - r * 0.35, bot[0][1] + 2, x - r * 0.35, top[0][1] - 2, *top[0])
        cr.close_path()
    for fx, col in ((0.05, '#20c8ff'), (0.5, '#3b5bff'), (0.95, '#a45bff')):
        halo(cr, x + w * fx, cy, h * 1.8, rgb(col), 0.18)
    for extra, a in ((10, 0.08), (5, 0.16)):
        path()
        cr.set_line_width(extra)
        cr.set_source(neon_grad(x, x + w, ['#34dcff', '#5c86ff', '#b37cff'], a))
        cr.stroke()
    path()
    cr.set_source(neon_grad(x, x + w, ['#12a8e8', '#2f5cf0', '#4a44e8', '#8a4dff'], 0.95))
    cr.fill()
    cr.save()
    path()
    cr.clip()
    hl = cairo.LinearGradient(0, y - 4, 0, cy)
    hl.add_color_stop_rgba(0, 1, 1, 1, 0.42)
    hl.add_color_stop_rgba(1, 1, 1, 1, 0)
    cr.rectangle(x, y - 5, w, h / 2 + 5)
    cr.set_source(hl)
    cr.fill()
    rnd = random.Random(61)
    for _ in range(int(w / 70)):   # bubbles inside the liquid
        bx, by, br = rnd.uniform(x + h, x + w - h), rnd.uniform(y + 5, y + h - 5), rnd.uniform(1.2, 2.6)
        cr.arc(bx, by, br, 0, 2 * PI)
        cr.set_source_rgba(1, 1, 1, 0.18)
        cr.fill()
    cr.restore()
    for bx, by, br, col in ((x - 10, cy + 6, 4, '#34dcff'), (x - 20, cy - 3, 2.2, '#34dcff'),
                            (x - 5, y - 3, 1.6, '#34dcff'), (x + w + 10, cy + 4, 3.6, '#b37cff'),
                            (x + w + 19, cy - 5, 2, '#b37cff'), (x + w + 4, y + h + 3, 1.5, '#b37cff')):
        halo(cr, bx, by, br * 2.4, rgb(col), 0.4)
        cr.arc(bx, by, br, 0, 2 * PI)
        cr.set_source_rgba(*rgb(col), 0.95)
        cr.fill()
        cr.arc(bx - br * 0.3, by - br * 0.35, br * 0.35, 0, 2 * PI)
        cr.set_source_rgba(1, 1, 1, 0.6)
        cr.fill()


def bar_nature(cr, x, y, w, h, cy):
    """Glowing green bar with leaf bunches spilling past both ends and small
    sprigs along the top (the bar leaves room for them, see ricekit)."""
    green = rgb('#2ee06f')
    halo(cr, x + 10, cy, h * 2, rgb('#0c5a2a'), 0.35)
    halo(cr, x + w - 10, cy, h * 2, rgb('#0c5a2a'), 0.35)
    path = lambda: _capsule(cr, x, y, w, h)  # noqa: E731
    path()
    cr.set_source_rgba(*rgb('#06140c'), 0.93)
    cr.fill()
    glow_stroke(cr, path, green, 1.6, layers=((9, 0.06), (4, 0.15)))
    _capsule(cr, x + 3, y + 3, w - 6, h - 6)
    cr.set_source_rgba(*green, 0.22)
    cr.set_line_width(0.8)
    cr.stroke()
    L = h * 1.25
    bunch = [(-0.55, 1.0, '#2fbf55'), (0.45, 0.9, '#1f8f3a'), (-1.15, 0.72, '#6fdc7f'),
             (0.05, 0.8, '#3fd46a'), (1.05, 0.62, '#58c96a'), (-0.2, 0.55, '#8ff09a')]
    for ang, k, col in bunch:
        leaf(cr, x + h * 0.25, cy + ang * 3, L * k, PI + ang * 0.85, rgb(col))
        leaf(cr, x + w - h * 0.25, cy - ang * 3, L * k, -ang * 0.85, rgb(col))
    rnd = random.Random(5)
    vx = x + w * 0.08
    while vx < x + w * 0.92:
        if not (x + w * 0.36 < vx < x + w * 0.64):
            for a in (-0.6, 0.6):
                leaf(cr, vx, y + 1, rnd.uniform(6, 9), -PI / 2 + a + rnd.uniform(-0.2, 0.2), rgb('#2fbf55'),
                     vein=False)
        vx += rnd.uniform(70, 130)


def bar_fire(cr, x, y, w, h, cy):
    """Burning edges: small tongues along the top and big flames licking
    out of both ends (the bar leaves room for them, see ricekit)."""
    orange, yellow, red = rgb('#ff6a00'), rgb('#ffc400'), rgb('#ff2a00')
    rnd = random.Random(11)
    halo(cr, x + 12, cy, h * 2, red, 0.25)
    halo(cr, x + w - 12, cy, h * 2, red, 0.25)

    def flame(fx, fy, dx, dy, length, width):
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
        g.add_color_stop_rgba(0, *orange, 0.95)
        g.add_color_stop_rgba(0.6, *yellow, 0.55)
        g.add_color_stop_rgba(1, *yellow, 0)
        cr.set_source(g)
        cr.fill()
    fx = x + h
    while fx < x + w - h:
        if rnd.random() < 0.6:
            flame(fx, y + 2, rnd.uniform(-0.3, 0.3), -1, rnd.uniform(3, max(4, y + 1)), rnd.uniform(2, 3.5))
        fx += rnd.uniform(12, 30)
    for sgn, ex in ((-1, x + 3), (1, x + w - 3)):
        for _ in range(9):
            a = rnd.uniform(-1.0, 1.0)
            flame(ex, cy + a * h * 0.3, sgn * math.cos(a * 0.5), math.sin(a * 0.9) * 0.6 - 0.15,
                  rnd.uniform(10, 26), rnd.uniform(2.5, 4.5))
    path = lambda: _capsule(cr, x, y, w, h)  # noqa: E731
    path()
    cr.set_source_rgba(*rgb('#120604'), 0.94)
    cr.fill()
    grad = cairo.LinearGradient(0, y, 0, y + h)
    grad.add_color_stop_rgb(0, *yellow)
    grad.add_color_stop_rgb(1, *orange)
    glow_stroke(cr, path, orange, 1.5, layers=((8, 0.08), (4, 0.18)), source=grad)
    for _ in range(22):
        cr.arc(rnd.uniform(x + h, x + w - h), rnd.uniform(y + h * 0.7, y + h - 3), rnd.uniform(0.6, 1.3), 0, 2 * PI)
        cr.set_source_rgba(*yellow, rnd.uniform(0.3, 0.7))
        cr.fill()


BAR_SKINS.update({'sketch': bar_sketch, 'crystal': bar_crystal, 'lava': bar_lava, 'neon': bar_neon,
                  'holo': bar_holo, 'liquid': bar_liquid, 'nature': bar_nature, 'fire': bar_fire})


# ═══════════════════════════════════════ bar ends: what sticks out
# Lines, rails and nodes past both ends of the bar, like the pills have.
def _ends(cr, x, w, cy, draw):
    for side, bx in ((-1, x), (1, x + w)):
        draw(side, bx)


def ends_hud(cr, x, y, w, h, cy):
    blue, soft = rgb('#2d8cff'), rgb('#7fc6ff')

    def one(side, bx):
        L = 40
        x1 = bx + side * L
        hline(cr, *sorted((bx, x1)), cy, blue, *((0.15, 0.95) if side < 0 else (0.95, 0.15)), 1.3)
        cr.move_to(bx + side * 2, cy + 5)
        cr.line_to(bx + side * 10, cy + 5)
        cr.line_to(bx + side * 15, cy + 9)
        cr.line_to(bx + side * 28, cy + 9)
        cr.set_line_width(1)
        cr.set_source_rgba(*blue, 0.6)
        cr.stroke()
        for i in range(3):
            cr.rectangle(bx + side * (16 + i * 7) - (4 if side < 0 else 0), cy - 5, 4, 2)
        cr.set_source_rgba(*soft, 0.7)
        cr.fill()
        halo(cr, x1, cy, 6, blue, 0.5)
        cr.arc(x1, cy, 2, 0, 2 * PI)
        cr.set_source_rgba(*soft, 1)
        cr.fill()
    _ends(cr, x, w, cy, one)


def ends_cyber(cr, x, y, w, h, cy):
    def one(side, bx):
        col = rgb('#19e6ff') if side < 0 else rgb('#ff2bd6')
        L = 40
        hline(cr, *sorted((bx, bx + side * L)), cy, col, *((0.1, 0.9) if side < 0 else (0.9, 0.1)), 1.4)
        for i in range(3):   # slashes near the outer end
            sx = bx + side * (24 + i * 5)
            cr.move_to(sx, cy + 4)
            cr.line_to(sx + 3, cy - 4)
        cr.set_line_width(1.4)
        cr.set_source_rgba(*col, 0.8)
        cr.stroke()
        for vy in (-1, 1):   # chevron hugging the tip
            cr.move_to(bx + side * 4, cy + vy * (h / 2 + 3))
            cr.line_to(bx + side * 10, cy + vy * 2)
        cr.set_line_width(1.3)
        cr.set_source_rgba(*col, 0.75)
        cr.stroke()
    _ends(cr, x, w, cy, one)


def ends_glass(cr, x, y, w, h, cy):
    blue = rgb('#6fa8ff')

    def one(side, bx):
        for dy in (-h * 0.22, h * 0.22):
            a = (0, 0.6) if side < 0 else (0.6, 0)
            hline(cr, *sorted((bx, bx + side * 32)), cy + dy, blue, *a)
    _ends(cr, x, w, cy, one)


def ends_pixel(cr, x, y, w, h, cy):
    q = max(2, round(h / 10))
    yy = round(cy - q / 2)

    def one(side, bx):
        cr.rectangle(bx if side > 0 else bx - 3 * q, yy, 3 * q, q)
        cr.set_source_rgba(*rgb('#1f5bff'), 0.95)
        cr.fill()
        for i in range(6):
            px = bx + side * (4 + i * 2) * q - (q if side < 0 else 0)
            cr.rectangle(px, yy, q, q)
            cr.set_source_rgba(*rgb('#4f86ff'), max(0.1, 0.75 - i * 0.12))
            cr.fill()
    _ends(cr, x, w, cy, one)


def _ends_line(color, length):
    def ends(cr, x, y, w, h, cy):
        def one(side, bx):
            a = (0, 0.7) if side < 0 else (0.7, 0)
            hline(cr, *sorted((bx, bx + side * length)), cy, rgb(color), *a)
        _ends(cr, x, w, cy, one)
    return ends


def _with_ends(body, ends):
    def skin(cr, x, y, w, h, cy):
        ends(cr, x, y, w, h, cy)
        body(cr, x, y, w, h, cy)
    return skin


BAR_SKINS.update({
    'hud': _with_ends(bar_hud, ends_hud),
    'cyber': _with_ends(bar_cyber, ends_cyber),
    'glass': _with_ends(bar_glass, ends_glass),
    'pixel': _with_ends(bar_pixel, ends_pixel),
    'minimal': _with_ends(bar_minimal, _ends_line('#3a4058', 24)),
    'macos': _with_ends(bar_macos, _ends_line('#4a5272', 24)),
})

# Minimum side margin of the bar for each skin, so what it draws past the
# ends (lines, leaves, flames, droplets, rocks, orbits) stays on screen.
BAR_MARGIN = {
    'glass': 36, 'cyber': 46, 'minimal': 28, 'gradient': 14, 'pixel': 36, 'macos': 28,
    'liquid': 30, 'hud': 46, 'fire': 34, 'nature': 52, 'sketch': 36, 'crystal': 16,
    'lava': 38, 'neon': 16, 'holo': 42,
}
