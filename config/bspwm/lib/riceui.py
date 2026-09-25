# =============================================================
# riceui - shared helpers for the rice's GTK/Cairo HUD apps
# (Dock, AppLauncher, KeyHelp). Keeps palette loading, drawing
# primitives, the blurred wallpaper backdrop and single-instance
# handling in one place so every app looks and behaves the same.
#
# Copyright (C) 2021-2026 TechOGR <https://github.com/TechOGR>
# Licensed under GPL-3.0 license
# =============================================================

import os
import json
import math
import fcntl
import signal
import hashlib
import subprocess

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Pango, PangoCairo  # noqa: E402
import cairo  # noqa: E402

HOME = os.path.expanduser('~')
BSPWM = os.path.join(HOME, '.config/bspwm')
FONT = 'JetBrainsMono Nerd Font'
DOCK_CONF = os.path.join(BSPWM, 'config/dock.json')
DOCK_DEFAULT = {
    'enabled': True,
    'apps': ['brave-browser.desktop', 'thunar.desktop', 'kitty.desktop'],
    'icon_size': 44,
    'magnify': True,
    'autohide': False,
    'show_launcher': True,
}
PALETTE_KEYS = ['bg', 'fg', 'black', 'blackb', 'red', 'green', 'yellow', 'blue',
                'magenta', 'cyan', 'white', 'accent_color']
PALETTE_DEFAULT = dict(bg='#1a1b26', fg='#c0caf5', black='#15161e', blackb='#414868',
                       red='#f7768e', green='#9ece6a', yellow='#e0af68', blue='#7aa2f7',
                       magenta='#bb9af7', cyan='#7dcfff', white='#a9b1d6', accent_color='#222330')


def rice():
    try:
        with open(os.path.join(BSPWM, '.rice')) as f:
            return f.read().strip()
    except OSError:
        return 'crackone'


def theme_cfg():
    return os.path.join(BSPWM, 'rices', rice(), 'theme-config.bash')


def palette_signature():
    """Changes whenever the rice palette may have changed."""
    sig = []
    for p in (os.path.join(BSPWM, '.rice'), theme_cfg(),
              os.path.join(BSPWM, 'rices', rice(), 'theme_colors.bash')):
        try:
            sig.append(os.path.getmtime(p))
        except OSError:
            sig.append(0)
    return tuple(sig)


def load_palette():
    """Hex colors of the active palette, as bash resolves them."""
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
        if len(v) == 7 and v.startswith('#'):
            pal[k] = v
    return pal


def hex_rgb(h, fallback=(0.5, 0.5, 0.5)):
    h = (h or '').lstrip('#')
    try:
        return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return fallback


def rgb_palette(pal):
    return {k: hex_rgb(v) for k, v in pal.items()}


# ─────────────────────────────────────────────────────────────── drawing
def rounded(cr, x, y, w, h, r):
    r = max(0, min(r, w / 2, h / 2))
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def text(cr, s, x, y, size, rgba, bold=False, align='left', spacing=0, valign='top'):
    layout = PangoCairo.create_layout(cr)
    layout.set_font_description(Pango.FontDescription(f'{FONT} {"Bold " if bold else ""}{size}'))
    if spacing:
        attrs = Pango.AttrList()
        attrs.insert(Pango.attr_letter_spacing_new(int(spacing * Pango.SCALE)))
        layout.set_attributes(attrs)
    layout.set_text(s, -1)
    w, h = layout.get_pixel_size()
    if align == 'center':
        x -= w / 2
    elif align == 'right':
        x -= w
    if valign == 'middle':
        y -= h / 2
    cr.move_to(x, y)
    cr.set_source_rgba(*rgba)
    PangoCairo.show_layout(cr, layout)
    return w, h


def current_wallpaper():
    link = os.path.join(HOME, '.cache/current_wall')
    p = os.path.realpath(link) if os.path.islink(link) else ''
    return p if os.path.isfile(p) else ''


def wall_thumb(path):
    """16:9 thumbnail shared with WallSelect/RiceEditor (created if missing)."""
    d = os.path.join(HOME, '.cache', os.environ.get('USER', 'user'), rice(), 'wallselect3d')
    thumb = os.path.join(d, hashlib.md5(path.encode()).hexdigest() + '.jpg')
    try:
        if os.path.getmtime(thumb) >= os.path.getmtime(path):
            return thumb
    except OSError:
        pass
    os.makedirs(d, exist_ok=True)
    subprocess.run(['magick', '-define', 'jpeg:size=1280x720', path + '[0]', '-strip',
                    '-thumbnail', '640x360^', '-gravity', 'center', '-extent', '640x360',
                    '-quality', '88', thumb], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return thumb if os.path.exists(thumb) else ''


def backdrop(W, H, pal, darken=0.62):
    """Full-screen layer: blurred current wallpaper, tinted + vignette."""
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    cr = cairo.Context(surf)
    bg = hex_rgb(pal['bg'])
    cr.set_source_rgb(*bg)
    cr.paint()
    wall = current_wallpaper()
    thumb = wall_thumb(wall) if wall else ''
    if thumb:
        try:
            pix = GdkPixbuf.Pixbuf.new_from_file(thumb)
            small = pix.scale_simple(32, 18, GdkPixbuf.InterpType.BILINEAR)
            blur = small.scale_simple(384, 216, GdkPixbuf.InterpType.BILINEAR)
            img = Gdk.cairo_surface_create_from_pixbuf(blur, 1, None)
            s = max(W / 384, H / 216) * 1.06
            cr.save()
            cr.translate(W / 2, H / 2)
            cr.scale(s, s)
            cr.set_source_surface(img, -192, -108)
            cr.get_source().set_filter(cairo.FILTER_BILINEAR)
            cr.paint()
            cr.restore()
        except GLib.Error:
            pass
    cr.set_source_rgba(*bg, darken)
    cr.paint()
    rg = cairo.RadialGradient(W / 2, H * 0.45, H * 0.2, W / 2, H * 0.45, max(W, H) * 0.75)
    rg.add_color_stop_rgba(0, 0, 0, 0, 0)
    rg.add_color_stop_rgba(1, 0, 0, 0, 0.7)
    cr.set_source(rg)
    cr.paint()
    # faint HUD grid
    acc = hex_rgb(pal['blue'])
    cr.set_line_width(1)
    for x in range(0, W, 64):
        cr.move_to(x + 0.5, 0)
        cr.line_to(x + 0.5, H)
    for y in range(0, H, 64):
        cr.move_to(0, y + 0.5)
        cr.line_to(W, y + 0.5)
    cr.set_source_rgba(*acc, 0.025)
    cr.stroke()
    return surf


def perf_profile():
    """'full' or 'lite' (see bin/PerfProfile), read without forking when
    PerfProfile already cached its guess for this boot."""
    try:
        with open(os.path.join(BSPWM, 'config/.perf_mode')) as f:
            mode = f.read().strip()
    except OSError:
        mode = 'auto'
    if mode in ('full', 'lite'):
        return mode
    cache = os.path.join(os.environ.get('XDG_RUNTIME_DIR', '/tmp'), f'bspwm-perf-{os.getuid()}')
    try:
        with open(cache) as f:
            return f.readline().strip() or 'full'
    except OSError:
        pass
    try:
        return subprocess.run([os.path.join(BSPWM, 'bin/PerfProfile')], capture_output=True,
                              text=True, timeout=10).stdout.strip() or 'full'
    except Exception:
        return 'full'


def monitor_geometry():
    display = Gdk.Display.get_default()
    seat = display.get_default_seat()
    _, px, py = seat.get_pointer().get_position()[0:3]
    mon = display.get_monitor_at_point(px, py) or display.get_primary_monitor() or display.get_monitor(0)
    return mon.get_geometry()


def grab_input(window, tries=0):
    """Keyboard+pointer grab for override-redirect popups (retry until mapped)."""
    gdkwin = window.get_window()
    if gdkwin is None:
        return False
    seat = Gdk.Display.get_default().get_default_seat()
    status = seat.grab(gdkwin, Gdk.SeatCapabilities.ALL, True, None, None, None, None)
    if status != Gdk.GrabStatus.SUCCESS and tries < 40:
        GLib.timeout_add(25, grab_input, window, tries + 1)
    return False


def rgba_window(window):
    window.set_app_paintable(True)
    screen = window.get_screen()
    visual = screen.get_rgba_visual()
    if visual and screen.is_composited():
        window.set_visual(visual)


# ────────────────────────────────────────────────────── single instance
def single_instance(name, toggle=False):
    """Hold a lock for the app's lifetime. With toggle=True a second launch
    closes the running instance instead of opening another one."""
    d = os.path.join(HOME, '.cache', os.environ.get('USER', 'user'))
    os.makedirs(d, exist_ok=True)
    lock = os.path.join(d, f'.{name}.lock')
    fd = open(lock, 'a+')
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        if toggle:
            fd.seek(0)
            try:
                os.kill(int(fd.read().strip() or 0), signal.SIGTERM)
            except (ValueError, ProcessLookupError, PermissionError):
                pass
        raise SystemExit(0)
    fd.seek(0)
    fd.truncate()
    fd.write(str(os.getpid()))
    fd.flush()
    return fd


def quit_on_sigterm(fn=None):
    def handler(*_):
        (fn or Gtk.main_quit)()
        return False
    GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGTERM, handler)
    GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGINT, handler)


# ───────────────────────────────────────────────────────────── dock conf
def load_dock_conf():
    conf = json.loads(json.dumps(DOCK_DEFAULT))  # deep copy: callers mutate 'apps'
    try:
        with open(DOCK_CONF) as f:
            conf.update(json.load(f))
    except (OSError, ValueError):
        pass
    return conf


def save_dock_conf(conf):
    tmp = DOCK_CONF + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(conf, f, indent=2)
        f.write('\n')
    os.replace(tmp, DOCK_CONF)


def hud_css(pal):
    """Base CSS shared by the HUD popups (launcher, key help)."""
    return f'''
@define-color bg {pal["bg"]};
@define-color fg {pal["fg"]};
@define-color black {pal["black"]};
@define-color blackb {pal["blackb"]};
@define-color accent {pal["blue"]};
@define-color accent2 {pal["magenta"]};
@define-color cyan {pal["cyan"]};
@define-color green {pal["green"]};
@define-color red {pal["red"]};
@define-color yellow {pal["yellow"]};

.hud, .hud label {{ font-family: "{FONT}"; color: @fg; }}
.hud .dim {{ color: alpha(@fg, 0.5); }}
.hud entry.search {{
    background-image: none; background-color: alpha(@black, 0.75);
    border: 1px solid alpha(@accent, 0.45); border-radius: 14px;
    color: @fg; caret-color: @accent; padding: 12px 18px; font-size: 14pt;
    box-shadow: 0 0 22px alpha(@accent, 0.18);
}}
.hud entry.search:focus {{ border-color: @accent; box-shadow: 0 0 26px alpha(@accent, 0.35); }}
.hud entry.search image {{ color: @accent; }}
.hud .panel {{
    background-color: alpha(@bg, 0.72);
    border: 1px solid alpha(@accent, 0.22); border-radius: 18px;
}}
.hud scrollbar {{ background: transparent; border: none; }}
.hud scrollbar slider {{ background-color: alpha(@accent, 0.35); border-radius: 6px; min-width: 4px; border: none; }}
.hud tooltip {{ background-color: @black; border: 1px solid alpha(@accent, 0.4); }}
'''
