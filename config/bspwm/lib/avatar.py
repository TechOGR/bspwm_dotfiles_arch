# =============================================================
# Author:  TechOGR
# Repo:    https://github.com/TechOGR/bspwm_dotfiles_arch
#
# avatar - the profile picture of the rice (UserCard, RiceEditor)
#   Sources: every .png in rices/<rice>/user_icons (user_logo.png by
#   default). The choice lives in config/avatar.json and is rendered to
#   config/assets/avatar.png, either as the picture itself (scaled and
#   centered on a square) or as ASCII art drawn with JetBrainsMono.
#   No GTK here: AvatarForge, UserCard, RiceEditor and the theme module
#   (palette colors) all use it.
#
# Copyright (C) 2021-2026 TechOGR <https://github.com/TechOGR>
# Licensed under GPL-3.0 license
# =============================================================

import os
import re
import json
import glob
import subprocess

from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

HOME = os.path.expanduser('~')
BSPWM = os.path.join(HOME, '.config/bspwm')
CONF = os.path.join(BSPWM, 'config/avatar.json')
OUT = os.path.join(BSPWM, 'config/assets/avatar.png')
SIZE = 512

CHARSETS = {
    'classic': ' .:-=+*#%@',
    'detailed': ' .\'`^",:;Il!i><~+_-?][}{1)(|/tjfrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$',
    'blocks': ' ░▒▓█',
    'binary': ' 01',
    'dots': ' ·•●',
    'hacker': ' .:;+=xX$&#',
}
COLOR_MODES = [
    ('image', 'Picture colors'),
    ('neon', 'Palette gradient'),
    ('mono', 'Single color'),
]
DEFAULT = {
    'source': 'user_logo.png',
    'mode': 'image',          # image | ascii
    'cols': 48,               # ascii: characters per row
    'charset': 'classic',
    'color': 'image',         # image | neon | mono
    'invert': False,
    'contrast': 1.3,
    'background': True,       # ascii: solid palette bg behind the text
    'plate': False,           # picture: light rounded plate behind it (dark logos)
}


def rice():
    try:
        with open(os.path.join(BSPWM, '.rice')) as f:
            return f.read().strip()
    except OSError:
        return 'crackone'


def icons_dir():
    return os.path.join(BSPWM, 'rices', rice(), 'user_icons')


def list_icons():
    """Only .png files, as asked."""
    return sorted(glob.glob(os.path.join(icons_dir(), '*.png')), key=lambda p: os.path.basename(p).lower())


def load():
    conf = dict(DEFAULT)
    try:
        with open(CONF) as f:
            conf.update(json.load(f))
    except (OSError, ValueError):
        pass
    return conf


def save(conf):
    tmp = CONF + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(conf, f, indent=2)
        f.write('\n')
    os.replace(tmp, CONF)


def fallback():
    """The raw logo of the rice (user_logo.png, else any .png there)."""
    logo = os.path.join(icons_dir(), DEFAULT['source'])
    if os.path.isfile(logo):
        return logo
    icons = list_icons()
    return icons[0] if icons else None


def current_path():
    """What the widgets should show right now: the AvatarForge render,
    made on the fly the first time."""
    if not os.path.exists(OUT):
        try:
            render()
        except Exception:
            return fallback() or OUT
    return OUT


def palette():
    keys = ['bg', 'fg', 'black', 'blue', 'magenta', 'cyan']
    script = ('. "$1" >/dev/null 2>&1; shift; '
              'for v in "$@"; do printf "%s\\t%s\\n" "$v" "${!v}"; done')
    pal = dict(bg='#1a1b26', fg='#c0caf5', black='#15161e', blue='#7aa2f7', magenta='#bb9af7', cyan='#7dcfff')
    try:
        out = subprocess.run(['bash', '-c', script, '_',
                              os.path.join(BSPWM, 'rices', rice(), 'theme-config.bash'), *keys],
                             capture_output=True, text=True, timeout=4).stdout
        for line in out.splitlines():
            k, _, v = line.partition('\t')
            if re.fullmatch(r'#[0-9a-fA-F]{6}', v):
                pal[k] = v
    except Exception:
        pass
    return {k: tuple(int(v[i:i + 2], 16) for i in (1, 3, 5)) for k, v in pal.items()}


def _font(px):
    try:
        path = subprocess.run(['fc-match', '-f', '%{file}', 'JetBrainsMono Nerd Font:style=Bold'],
                              capture_output=True, text=True, timeout=3).stdout.strip()
        return ImageFont.truetype(path, px)
    except Exception:
        return ImageFont.load_default()


def _source(conf):
    path = os.path.join(icons_dir(), conf.get('source') or '')
    if not os.path.isfile(path):
        path = fallback()
    if not path:
        return Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    return Image.open(path).convert('RGBA')


def render_picture(img, size=SIZE, plate=False):
    """The picture as it is: fit inside a square, centered, smooth scaling.
    plate: a light square behind it, so dark logos stay visible."""
    pad = round(size * 0.12) if plate else 0
    img = ImageOps.contain(img, (size - 2 * pad, size - 2 * pad), Image.LANCZOS)
    bg = (*palette()['fg'], 255) if plate else (0, 0, 0, 0)
    out = Image.new('RGBA', (size, size), bg)
    out.paste(img, ((size - img.width) // 2, (size - img.height) // 2), img)
    return out


def render_ascii(img, conf, size=SIZE, pal=None):
    pal = pal or palette()
    chars = CHARSETS.get(conf.get('charset'), CHARSETS['classic'])
    cols = max(12, min(160, int(conf.get('cols', 48))))
    cell_w = size / cols
    font_px = max(4, round(cell_w / 0.6))          # JetBrainsMono advance ≈ 0.6 em
    font = _font(font_px)
    try:
        cw, ch = font.getbbox('M')[2], font_px * 1.18
    except Exception:
        cw, ch = cell_w, cell_w * 2
    cw = cw or cell_w
    rows = max(1, round(cols * img.height / img.width * cw / ch))

    small = img.resize((cols, rows), Image.LANCZOS)
    alpha = small.getchannel('A')
    rgb = Image.alpha_composite(Image.new('RGBA', small.size, (0, 0, 0, 255)), small).convert('RGB')
    rgb = ImageEnhance.Contrast(rgb).enhance(float(conf.get('contrast', 1.3)))
    lum = ImageOps.grayscale(rgb)

    invert = bool(conf.get('invert')) ^ dark_ink(lum, alpha)

    W, H = round(cols * cw), round(rows * ch)
    canvas = Image.new('RGBA', (W, H), (*pal['bg'], 255) if conf.get('background', True) else (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    n = len(chars) - 1
    for y in range(rows):
        for x in range(cols):
            a = alpha.getpixel((x, y))
            if a < 40:
                continue
            v = lum.getpixel((x, y)) / 255
            if invert:
                v = 1 - v
            c = chars[max(1, round(v * n))] if n else chars[0]
            mode = conf.get('color', 'image')
            if mode == 'image':
                r, g, b = rgb.getpixel((x, y))
                # lift dark pixels so they stay readable on the dark bg
                # dark ink would vanish on the dark background: pull it
                # towards the palette foreground, keep bright colors
                dark = 1 - max(r, g, b) / 255
                col = tuple(int(k + (f - k) * dark * 0.85) for k, f in zip((r, g, b), pal['fg']))
            elif mode == 'neon':
                t = (x / max(1, cols - 1) + y / max(1, rows - 1)) / 2
                c1, c2 = pal['cyan'], pal['magenta']
                col = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
            else:
                col = pal['fg']
            draw.text((x * cw, y * ch), c, font=font, fill=(*col, 255))
    return render_picture(canvas, size)


def dark_ink(lum, alpha):
    """True for dark drawings (black logos on transparency): the ASCII
    ramp is inverted automatically so the shape is drawn, not the hole."""
    total = count = 0
    for a, v in zip(alpha.getdata(), lum.getdata()):
        if a >= 40:
            total += v
            count += 1
    return bool(count) and total / count < 80


def render(conf=None, out=OUT, size=SIZE):
    conf = conf or load()
    img = _source(conf)
    res = (render_ascii(img, conf, size) if conf.get('mode') == 'ascii'
           else render_picture(img, size, conf.get('plate')))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + '.tmp.png'
    res.save(tmp)
    os.replace(tmp, out)
    return out


def ascii_text(conf=None):
    """Plain text version (for a terminal / fetch)."""
    conf = conf or load()
    img = _source(conf)
    chars = CHARSETS.get(conf.get('charset'), CHARSETS['classic'])
    cols = int(conf.get('cols', 48))
    rows = max(1, round(cols * img.height / img.width * 0.5))
    small = img.resize((cols, rows), Image.LANCZOS)
    alpha = small.getchannel('A')
    lum = ImageOps.grayscale(Image.alpha_composite(Image.new('RGBA', small.size, (0, 0, 0, 255)), small))
    n = len(chars) - 1
    invert = bool(conf.get('invert')) ^ dark_ink(lum, alpha)
    lines = []
    for y in range(rows):
        row = ''
        for x in range(cols):
            v = lum.getpixel((x, y)) / 255
            if invert:
                v = 1 - v
            row += ' ' if alpha.getpixel((x, y)) < 40 else chars[max(1, round(v * n))]
        lines.append(row.rstrip())
    return '\n'.join(lines)
