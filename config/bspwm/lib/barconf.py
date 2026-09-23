# =============================================================
# Author:  TechOGR
# Repo:    https://github.com/TechOGR/bspwm_dotfiles_arch
#
# barconf - polybar layout/style shared by BarCtl, RiceEditor and
# ModulesList. The user's choices live in config/polybar.json; render()
# turns them + the rice palette into rices/<rice>/bar.ini, which
# config.ini includes (bar/emi-bar inherits bar/look from it).
# No GTK here: BarCtl runs on every theme apply.
#
# Copyright (C) 2021-2026 TechOGR <https://github.com/TechOGR>
# Licensed under GPL-3.0 license
# =============================================================

import os
import re
import json
import subprocess

HOME = os.path.expanduser('~')
BSPWM = os.path.join(HOME, '.config/bspwm')
CONF = os.path.join(BSPWM, 'config/polybar.json')

DEFAULT = {
    'style': 'capsule',        # capsule | islands | cyber | strip
    'position': 'top',         # top | bottom
    'height': 30,
    'offset_y': 8,
    'margin_x': 5,             # px between the bar and the screen edges
    'radius': 16,
    'opacity': 100,            # background opacity %
    'bg_color': 'bg',          # palette key
    'accent': 'blue',          # palette key: border / strip line
    'border': False,
    'separators': True,
    'autohide': False,
    'modules': {
        'left': ['launcher', 'gap', 'cpu_wave', 'memory_bar', 'filesystem'],
        'center': ['bspwm'],
        'right': ['network', 'pulseaudio', 'date', 'gap', 'caffeine', 'screenshot', 'modules_help', 'power'],
    },
}

STYLES = [
    ('capsule', 'Capsule', 'one floating rounded bar'),
    ('islands', 'Islands', 'transparent bar, each group is a neon pill'),
    ('cyber', 'Cyber', 'transparent bar, angled HUD plates'),
    ('strip', 'Strip', 'edge to edge panel with a neon line'),
]

# id, icon, name, description  -- every module modules.ini knows about
CATALOG = [
    ('launcher', '󰣇', 'Launcher', 'App launcher button'),
    ('bspwm', '󰮯', 'Workspaces', 'bspwm desktops'),
    ('cpu_wave', '󰻠', 'CPU', 'CPU load'),
    ('memory_bar', '󰍛', 'Memory', 'RAM used / total'),
    ('filesystem', '󰋊', 'Disk', 'Space used on /'),
    ('network', '󰤨', 'Network', 'Traffic trace, ↓ ↑ in KB/s · MB/s'),
    ('pulseaudio', '󰕾', 'Volume', 'Audio level'),
    ('mic', '󰍬', 'Microphone', 'Mute / unmute the mic'),
    ('date', '󰥔', 'Clock', 'Time · click for the date'),
    ('caffeine', '󰅶', 'Caffeine', 'Keep the screen awake'),
    ('screenshot', '󰹑', 'Screenshot', 'Capture HUD · right click: region'),
    ('modules_help', '󰋗', 'Modules', 'Module list'),
    ('power', '󰐥', 'Power', 'Session menu'),
    ('uptime', '󰔟', 'Uptime', 'Time since boot'),
    ('sensors_temp', '󰔏', 'Temperature', 'CPU temperature'),
    ('gpu', '󰢮', 'GPU', 'GPU usage and temperature'),
    ('heartbeat', '󰣐', 'Heartbeat', 'Decorative neon pulse'),
    ('song_wave', '󰝚', 'Now playing', 'MPD song ticker'),
    ('mpd', '󰎈', 'MPD', 'Short MPD status'),
    ('mpd_control', '󰐊', 'MPD control', 'Prev / play / next'),
    ('mplayer', '󰎆', 'Player', 'Music player shortcut'),
    ('bluetooth', '󰂯', 'Bluetooth', 'Adapter status'),
    ('battery', '󰁹', 'Battery', 'Charge and state'),
    ('brightness', '󰃠', 'Brightness', 'Screen backlight'),
    ('updates', '󰚰', 'Updates', 'Pending packages'),
    ('weather', '󰖐', 'Weather', 'Current weather'),
    ('xkeyboard', '󰌌', 'Keyboard', 'Active layout'),
    ('colorpicker', '󰈊', 'Color picker', 'Pick a color on screen'),
    ('clipboard', '󰅍', 'Clipboard', 'Clipboard history'),
    ('sysmonitor', '󰨇', 'System monitor', 'Process monitor'),
    ('usercard', '󰀄', 'User card', 'Profile widget'),
    ('tray', '󰕰', 'Tray', 'System tray icons'),
    ('gap', '󰇘', 'Gap', 'Splits a group: new pill / wider space'),
]
FIXED = {'bspwm'}
# icon-only buttons: no separator line before them
BUTTONS = {'launcher', 'caffeine', 'screenshot', 'modules_help', 'power', 'clipboard', 'sysmonitor',
           'colorpicker', 'mplayer', 'usercard', 'tray'}

PALETTE_KEYS = ['bg', 'fg', 'black', 'blackb', 'red', 'green', 'yellow', 'blue',
                'magenta', 'cyan', 'white', 'accent_color']
PALETTE_DEFAULT = dict(bg='#1a1b26', fg='#c0caf5', black='#15161e', blackb='#414868',
                       red='#f7768e', green='#9ece6a', yellow='#e0af68', blue='#7aa2f7',
                       magenta='#bb9af7', cyan='#7dcfff', white='#a9b1d6', accent_color='#222330')

# (left cap, right cap) glyphs of MesloLGS NF for the pill styles
CAPS = {'islands': ('', ''), 'cyber': ('', '')}


def rice():
    try:
        with open(os.path.join(BSPWM, '.rice')) as f:
            return f.read().strip()
    except OSError:
        return 'crackone'


def rice_dir():
    return os.path.join(BSPWM, 'rices', rice())


def theme_cfg():
    return os.path.join(rice_dir(), 'theme-config.bash')


def load():
    conf = json.loads(json.dumps(DEFAULT))
    try:
        with open(CONF) as f:
            data = json.load(f)
        mods = data.pop('modules', None)
        conf.update(data)
        if isinstance(mods, dict):
            for k in ('left', 'center', 'right'):
                if isinstance(mods.get(k), list):
                    conf['modules'][k] = [str(m) for m in mods[k]]
    except (OSError, ValueError):
        pass
    return conf


def save(conf):
    tmp = CONF + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(conf, f, indent=2)
        f.write('\n')
    os.replace(tmp, CONF)


def load_palette():
    script = ('. "$1" >/dev/null 2>&1; shift; '
              'for v in "$@"; do printf "%s\\t%s\\n" "$v" "${!v}"; done')
    try:
        out = subprocess.run(['bash', '-c', script, '_', theme_cfg(), *PALETTE_KEYS],
                             capture_output=True, text=True, timeout=4).stdout
    except Exception:
        out = ''
    pal = dict(PALETTE_DEFAULT)
    for line in out.splitlines():
        k, _, v = line.partition('\t')
        if re.fullmatch(r'#[0-9a-fA-F]{6}', v):
            pal[k] = v
    return pal


def argb(hexv, opacity):
    a = max(0, min(255, round(opacity * 255 / 100)))
    return f'#{a:02x}{hexv.lstrip("#")}'


def active_modules(conf):
    m = conf['modules']
    return [x for k in ('left', 'center', 'right') for x in m[k] if x != 'gap']


def toggle(conf, mod):
    """Add to the right group or remove from wherever it is."""
    mods = conf['modules']
    if any(mod in mods[k] for k in mods):
        if mod in FIXED:
            return False
        for k in mods:
            mods[k] = [x for x in mods[k] if x != mod]
        return False
    right = mods['right']
    # keep the session buttons at the very end
    tail = next((i for i, x in enumerate(right) if x in ('modules_help', 'power')), len(right))
    right.insert(tail, mod)
    return True


def expand(mods, conf, pill):
    """Module list -> polybar modules-* value (separators, caps, gaps)."""
    out = []
    prev = None
    for m in mods:
        if m == 'gap':
            if pill and out:
                out += ['cap-r', 'spacer', 'cap-l']
            elif out:
                out.append('sep' if conf['separators'] else 'gap')
            prev = None
            continue
        if prev is not None and conf['separators'] and m not in BUTTONS:
            out.append('sep')
        out.append(m)
        prev = m
    while out and out[-1] in ('cap-l', 'spacer', 'gap'):
        out.pop()
    if pill and out:
        if out[0] != 'cap-l':
            out.insert(0, 'cap-l')
        out.append('cap-r')
    return ' '.join(out)


def reserve(conf):
    """Space bspwm must keep free for the bar."""
    if conf['style'] == 'strip':
        return conf['height'] - 8 + 6
    return max(1, conf['height'] + conf['offset_y'] - 8)


def render(conf=None, pal=None):
    conf = conf or load()
    pal = pal or load_palette()
    style = conf['style'] if conf['style'] in dict((s[0], 1) for s in STYLES) else 'capsule'
    pill = style in CAPS
    H = int(conf['height'])
    op = int(conf['opacity'])
    base = pal.get(conf['bg_color'], pal['bg'])
    accent = pal.get(conf['accent'], pal['blue'])
    bottom = conf['position'] == 'bottom'

    if pill:
        bar_bg, pod = '#00000000', argb(base, op)
    else:
        # polybar paints module backgrounds with SOURCE, not OVER: a
        # transparent one would punch holes in the bar, so reuse its color
        bar_bg = pod = argb(base, op)
    if style == 'strip':
        width, off_x, off_y, radius = '100%', '0', '0', 0
    else:
        width = f'100%:-{2 * int(conf["margin_x"])}'
        off_x, off_y, radius = str(int(conf['margin_x'])), str(int(conf['offset_y'])), conf['radius']
    if pill:
        radius = 0

    lines = [
        f'; GENERATED by BarCtl from config/polybar.json ({style}) -- use RiceEditor -> Polybar',
        '[pod]',
        f'bg = {pod}',
        f'accent = {accent}',
        '',
        '[bar/look]',
        f'bottom = {"true" if bottom else "false"}',
        f'width = {width}',
        f'height = {H}',
        f'offset-x = {off_x}',
        f'offset-y = {off_y}',
        f'radius = {radius}',
        f'background = {bar_bg}',
        'foreground = ${color.fg}',
        # pill caps must be exactly as tall as the bar
        f'font-5 = "MesloLGS NF:pixelsize={round(H * 0.79)};{round(H * 0.235)}"',
        f'padding = {1 if pill else (2 if style == "strip" else 5)}',
    ]
    if conf['autohide']:
        # no strut (bspwm would keep the space reserved) and mapped on top
        lines += ['override-redirect = true']
    else:
        lines += ['override-redirect = false', 'wm-restack = bspwm']
    if style == 'strip':
        side = 'top' if bottom else 'bottom'
        lines += [f'border-{side}-size = 2', f'border-{side}-color = {accent}']
    elif conf['border'] and not pill:
        lines += ['border-size = 1', f'border-color = {argb(accent, 85)}']
    else:
        lines += ['border-size = 0']
    for k in ('left', 'center', 'right'):
        lines.append(f'modules-{k} = {expand(conf["modules"][k], conf, pill)}')

    cap_l, cap_r = CAPS.get(style, ('', ''))
    lines += [
        '',
        '[module/sep]', 'type = custom/text', 'label = "│"',
        'label-foreground = ${color.trace}', f'format-background = {pod}',
        f'label-padding = {2 if pill else 3}',
        '',
        '[module/gap]', 'type = custom/text', 'label = " "', 'label-padding = 4',
        '',
        '[module/spacer]', 'type = custom/text', 'label = " "', 'label-padding = 1',
        '',
        '[module/cap-l]', 'type = custom/text', f'label = "{cap_l}"', 'label-font = 6',
        f'label-foreground = {pod}',
        '',
        '[module/cap-r]', 'type = custom/text', f'label = "{cap_r}"', 'label-font = 6',
        f'label-foreground = {pod}',
        '',
    ]
    path = os.path.join(rice_dir(), 'bar.ini')
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        f.write('\n'.join(lines))
    os.replace(tmp, path)
    return path


# ─────────────────────────────────────────────── theme-config paddings
def set_theme_var(key, value):
    """Change KEY="value" in the live theme-config.bash, keeping comments."""
    path = theme_cfg()
    try:
        text = open(path).read()
    except OSError:
        return
    new, n = re.subn(rf'^({key}=)"?[^"\s#]*"?', rf'\g<1>"{value}"', text, count=1, flags=re.M)
    if n and new != text:
        with open(path, 'w') as f:
            f.write(new)


def get_theme_var(key, default=''):
    try:
        m = re.search(rf'^{key}="?([^"\s#]*)', open(theme_cfg()).read(), re.M)
        return m.group(1) if m else default
    except OSError:
        return default


def paddings(conf):
    """(top, bottom) bspwm paddings for this bar config."""
    r = reserve(conf)
    edge = int(get_theme_var('LEFT_PADDING', '1') or 1)
    return (edge, r) if conf['position'] == 'bottom' else (r, edge)
