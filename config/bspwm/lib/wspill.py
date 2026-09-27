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


def rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


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
        if style == 'pixel':
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


def _capsule(cr, x, y, w, h, r=None):
    rounded(cr, x, y, w, h, h / 2 if r is None else r)


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
