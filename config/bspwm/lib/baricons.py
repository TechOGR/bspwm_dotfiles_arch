# =============================================================
# Author:  TechOGR
# Repo:    https://github.com/TechOGR/bspwm_dotfiles_arch
#
# baricons - the polybar icons of every theme (Material Design Icons):
# the launcher becomes the theme's emblem (a lightning bolt, a skull, a
# butterfly, a snake, a flame, a leaf...) and the other modules take a
# glyph in the same spirit (chip / radar / atom / spider for the CPU,
# camera iris / target for the screenshot...). lib/barconf.py writes
# rices/<rice>/modules.themed.ini (what config.ini includes) from
# modules.ini with these glyphs; ModulesList shows them too.
#
# Copyright (C) 2021-2026 TechOGR <https://github.com/TechOGR>
# Licensed under GPL-3.0 license
# =============================================================

import re


def _g(cp):
    return chr(cp)


# the icons without a theme (the classic look of modules.ini)
BASE = {
    'emblem': 0xf08c7,   # arch
    'cpu': 0xf0ee0,      # cpu-64-bit
    'mem': 0xf035b,      # memory
    'disk': 0xf02ca,     # harddisk
    'vol': 0xf057e,      # volume-high
    'mute': 0xf075f,     # volume-mute
    'power': 0xf0425,    # power
    'help': 0xf02d7,     # help-circle
    'shot': 0xf0100,     # camera
    'user': 0xf0009,     # account-circle
    'music': 0xf0388,    # music-note
    'clip': 0xf014d,     # clipboard-text
    'monitor': 0xf0a07,  # monitor-dashboard
    'update': 0xf06b0,   # update
    'bright': 0xf00df,   # brightness-6
    'kb': 0xf030c,       # keyboard
    'picker': 0xf020a,   # eyedropper
}

THEMES = {
    'glass': dict(emblem=0xf0674, cpu=0xf061a, disk=0xf01bc, power=0xf0906, help=0xf0625, shot=0xf0d5d,
                  user=0xf0b55),
    'cyber': dict(emblem=0xf06a9, cpu=0xf061a, disk=0xf08f3, power=0xf06a5, help=0xf018d, shot=0xf0104),
    'minimal': dict(power=0xf0906, help=0xf0625, shot=0xf0d5d, user=0xf0b55),
    'pixel': dict(emblem=0xf0bc9, cpu=0xf1393, disk=0xf0249, help=0xf078b, user=0xf089a),
    'liquid': dict(emblem=0xf058c, cpu=0xf078d, mem=0xf01ab, disk=0xf1806, help=0xf02fd),
    'hud': dict(emblem=0xf01a4, cpu=0xf0437, disk=0xf01bc, help=0xf02fd, shot=0xf04fe, power=0xf0906),
    'fire': dict(emblem=0xf0238, cpu=0xf1807, disk=0xf01bc, power=0xf15d7, help=0xf0625),
    'nature': dict(emblem=0xf032a, cpu=0xf0e66, mem=0xf0531, disk=0xf0405, power=0xf0906, help=0xf0625),
    'sketch': dict(emblem=0xf03eb, cpu=0xf0f49, mem=0xf082e, disk=0xf0256, shot=0xf11e4, help=0xf0625),
    'crystal': dict(emblem=0xf01c8, cpu=0xf0b8a, mem=0xf01a7, disk=0xf0b2f, help=0xf0ae3),
    'lava': dict(emblem=0xf1a83, cpu=0xf0238, disk=0xf0629, power=0xf15d7),
    'neon': dict(emblem=0xf06e8, cpu=0xf032c, power=0xf0906, help=0xf0625),
    'holo': dict(emblem=0xf0018, cpu=0xf0768, mem=0xf1383, disk=0xf0471, shot=0xf10c5, help=0xf0ae2),
    'storm': dict(emblem=0xf0593, cpu=0xf0241, mem=0xf140b, disk=0xf0596, power=0xf06d5, help=0xf0ef7,
                  vol=0xf057e),
    'venom': dict(emblem=0xf068c, cpu=0xf11ea, mem=0xf00e4, disk=0xf0b7f, power=0xf0bc6, help=0xf0bca,
                  shot=0xf0bc8),
    'butterfly': dict(emblem=0xf1589, cpu=0xf024a, mem=0xf09f1, disk=0xf0fa1, power=0xf0d08, help=0xf158a,
                      shot=0xf09f0),
    'snake': dict(emblem=0xf150e, cpu=0xf06d0, mem=0xf0aaf, disk=0xf1952, power=0xf0906, help=0xf0208),
}


def icons(style):
    d = dict(BASE)
    d.update(THEMES.get(style or '', {}))
    return {k: _g(v) for k, v in d.items()}


# modules.ini: (section, key) -> icon, and the font key that must point at
# the Material Design font (font-2 = index 3) for it
SLOTS = [
    ('launcher', 'label', 'emblem', 'label-font'),
    ('cpu_wave', 'format-prefix', 'cpu', 'format-prefix-font'),
    ('cpu_bar', 'format-prefix', 'cpu', 'format-prefix-font'),
    ('memory_bar', 'format-prefix', 'mem', 'format-prefix-font'),
    ('filesystem', 'format-mounted-prefix', 'disk', 'format-mounted-prefix-font'),
    ('filesystem', 'format-unmounted-prefix', 'disk', 'format-unmounted-prefix-font'),
    ('pulseaudio', 'format-volume-prefix', 'vol', 'format-volume-prefix-font'),
    ('pulseaudio', 'format-muted-prefix', 'mute', 'format-muted-prefix-font'),
    ('power', 'label', 'power', 'label-font'),
    ('modules_help', 'label', 'help', 'label-font'),
    ('screenshot', 'label', 'shot', 'label-font'),
    ('usercard', 'label', 'user', 'label-font'),
    ('mplayer', 'label', 'music', 'label-font'),
    ('clipboard', 'label', 'clip', 'label-font'),
    ('sysmonitor', 'label', 'monitor', 'label-font'),
    ('updates', 'format-prefix', 'update', 'format-prefix-font'),
    ('xkeyboard', 'format-prefix', 'kb', 'format-prefix-font'),
    ('colorpicker', 'label', 'picker', 'label-font'),
]
MDI_FONT = 3


def themed_modules(text, style):
    """modules.ini with the theme's glyphs (and the Material font for them);
    without a theme it stays as it is."""
    if style not in THEMES:
        return text
    ic = icons(style)
    want = {}
    for sec, key, icon, fkey in SLOTS:
        want.setdefault(sec, []).append((key, ic[icon], fkey))
    out, sec, seen = [], None, set()

    def flush():
        # font keys the section did not have
        for key, _g_, fkey in want.get(sec, []):
            if (sec, fkey) not in seen and (sec, key) in seen:
                out.append(f'{fkey} = {MDI_FONT}\n')

    for line in text.splitlines(keepends=True):
        m = re.match(r'\s*\[module/([\w-]+)\]', line)
        if m:
            if sec:
                # before the blank lines that end the section
                tail = []
                while out and not out[-1].strip():
                    tail.append(out.pop())
                flush()
                out += tail[::-1]
            sec = m.group(1)
            out.append(line)
            continue
        m = re.match(r'(\s*)([\w-]+)(\s*=\s*)(.*?)(\s*)$', line)
        if sec in want and m:
            key = m.group(2)
            for k, glyph, fkey in want[sec]:
                if key == k:
                    val = m.group(4)
                    quoted = val.startswith('"') and val.endswith('"') and len(val) > 1
                    trail = ' ' if val.strip('"').endswith(' ') else ''
                    new = f'{glyph}{trail}'
                    line = f'{m.group(1)}{key}{m.group(3)}{chr(34) + new + chr(34) if quoted or trail else new}\n'
                    seen.add((sec, key))
                elif key == fkey:
                    if m.group(4).strip() not in ('3', '4'):   # already a Material font: keep its size
                        line = f'{m.group(1)}{key}{m.group(3)}{MDI_FONT}\n'
                    seen.add((sec, key))
        out.append(line)
    if sec:
        flush()
    return ''.join(out)
