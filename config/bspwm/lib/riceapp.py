# =============================================================
# Author:  TechOGR
# Repo:    https://github.com/TechOGR/bspwm_dotfiles_arch
#
# riceapp - the pieces of the rice's "center" windows (UpdateCenter,
# BtCenter...): a normal window framed by RoundBorders with the theme's
# scene behind its content, the HUD CSS in the theme's accents, labels,
# buttons, cards, a status line and work run in the background (the
# window never freezes on a slow command).
#
# Copyright (C) 2021-2026 TechOGR <https://github.com/TechOGR>
# Licensed under GPL-3.0 license
# =============================================================

import os
import subprocess
import threading

import riceui as ui
from riceui import Gtk, Gdk, GLib, Pango, cairo


def lang_es():
    try:
        import ricelang
        return ricelang.get_lang() == 'es'
    except Exception:
        return True


def translator(table):
    es = lang_es()
    return lambda s: table.get(s, s) if es else s


def run_bg(fn, done=None):
    """fn() in a thread, done(result) back in the GTK loop."""
    def work():
        try:
            r = fn()
        except Exception as e:   # noqa: BLE001 - shown to the user
            r = e
        if done:
            GLib.idle_add(lambda: (done(r), False)[1])
    threading.Thread(target=work, daemon=True).start()


def cmd(args, timeout=60, env=None, input_=None):
    """(rc, stdout, stderr) of a command, never raising."""
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, input=input_,
                           env={**os.environ, 'LC_ALL': 'C', **(env or {})})
        return p.returncode, p.stdout, p.stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, '', str(e)


def label(text, cls=None, xalign=0.0, wrap=False, ellipsize=False, markup=False):
    lb = Gtk.Label(xalign=xalign)
    (lb.set_markup if markup else lb.set_text)(text)
    for c in (cls or '').split():
        lb.get_style_context().add_class(c)
    if wrap:
        lb.set_line_wrap(True)
    elif ellipsize:
        lb.set_ellipsize(Pango.EllipsizeMode.END)
    return lb


def button(text, cb, cls='nbtn', glyph=None, tooltip=None):
    b = Gtk.Button()
    box = Gtk.Box(spacing=8)
    if glyph:
        box.pack_start(label(glyph, 'bglyph'), False, False, 0)
    if text:
        box.pack_start(label(text), False, False, 0)
    box.set_halign(Gtk.Align.CENTER)
    b.add(box)
    for c in cls.split():
        b.get_style_context().add_class(c)
    if tooltip:
        b.set_tooltip_text(tooltip)
    b.connect('clicked', lambda *_: cb())
    return b


def section(title, glyph=None):
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
    box.get_style_context().add_class('card')
    head = Gtk.Box(spacing=8)
    if glyph:
        head.pack_start(label(glyph, 'sglyph'), False, False, 0)
    head.pack_start(label(title.upper(), 'stitle'), False, False, 0)
    box.pack_start(head, False, False, 0)
    box.head = head
    return box


def clear(box):
    for ch in box.get_children():
        ch.destroy()


class CenterWindow(Gtk.Window):
    """A themed center window: header (glyph, title, subtitle, right-side
    widgets), scrollable body, status line. Esc closes it."""

    def __init__(self, cls, title, glyph, size=(1000, 720)):
        super().__init__(title=title)
        self.set_wmclass(cls, cls)
        self.pal = ui.load_palette()
        self.c = ui.rgb_palette(self.pal)
        self.fg = self.c['fg']
        self.style = ui.theme_style()
        self.acc = ui.style_accent(self.style, self.pal) if self.style else self.c['blue']
        self.acc2 = self.c['magenta']
        self.bg = None
        self.set_default_size(*size)
        self.install_css()
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        root.get_style_context().add_class('ncroot')
        root.set_border_width(26)
        self.add(root)
        head = Gtk.Box(spacing=14)
        head.pack_start(label(glyph, 'hglyph'), False, False, 0)
        tt = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        tt.set_valign(Gtk.Align.CENTER)
        tt.pack_start(label(title.upper(), 'title'), False, False, 0)
        self.subtitle = label('', 'sub')
        tt.pack_start(self.subtitle, False, False, 0)
        head.pack_start(tt, False, False, 0)
        head.pack_start(Gtk.Box(), True, True, 0)
        self.head_right = Gtk.Box(spacing=10)
        self.head_right.set_valign(Gtk.Align.CENTER)
        head.pack_start(self.head_right, False, False, 0)
        root.pack_start(head, False, False, 0)
        self.body = Gtk.Box(spacing=16)
        root.pack_start(self.body, True, True, 0)
        self.status = label('', 'status', ellipsize=True)
        root.pack_start(self.status, False, False, 0)
        self.connect('draw', self.on_draw)
        self.connect('key-press-event', self.on_key)
        self.connect('destroy', Gtk.main_quit)

    def scroller(self, child):
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.add(child)
        return sw

    def install_css(self):
        hexa = '#%02x%02x%02x' % tuple(int(v * 255) for v in self.acc)
        hexb = '#%02x%02x%02x' % tuple(int(v * 255) for v in self.acc2)
        css = Gtk.CssProvider()
        css.load_from_data((ui.hud_css(self.pal) + f'''
@define-color acc {hexa};
@define-color acc2 {hexb};
window, .ncroot {{ background: transparent; }}
.ncroot, .ncroot label {{ font-family: "{ui.FONT}"; color: @fg; }}
.title {{ font-size: 17pt; font-weight: 800; letter-spacing: 3px; }}
.sub {{ font-size: 8pt; color: alpha(@fg, 0.55); letter-spacing: 1px; }}
.hglyph {{ font-family: "{ui.ICON_FONT}"; font-size: 28pt; color: @acc; }}
.sglyph, .bglyph, .rglyph {{ font-family: "{ui.ICON_FONT}"; color: @acc; }}
.sglyph {{ font-size: 13pt; }}
.bglyph {{ font-size: 11pt; }}
.rglyph {{ font-size: 16pt; }}
.rglyph.warn {{ color: @yellow; }}
.rglyph.crit {{ color: @red; }}
.stitle {{ font-size: 8pt; font-weight: 800; letter-spacing: 3px; color: alpha(@fg, 0.75); }}
.card {{ background-color: alpha(@bg, 0.55); border: 1px solid alpha(@acc, 0.22);
    border-radius: 16px; padding: 16px 18px; }}
.chip {{ font-size: 8pt; font-weight: 800; letter-spacing: 1px; padding: 3px 10px; border-radius: 10px;
    background-color: alpha(@acc, 0.16); color: @acc; }}
.chip.bad {{ background-color: alpha(@red, 0.16); color: @red; }}
.chip.mid {{ background-color: alpha(@yellow, 0.16); color: @yellow; }}
.chip.ok {{ background-color: alpha(@green, 0.16); color: @green; }}
.key {{ font-size: 8pt; color: alpha(@fg, 0.5); letter-spacing: 1px; }}
.val {{ font-size: 9pt; font-weight: 700; }}
.mono {{ font-size: 8pt; }}
.old {{ font-size: 8pt; color: alpha(@fg, 0.45); }}
.new {{ font-size: 8pt; font-weight: 800; color: @acc; }}
.big {{ font-size: 22pt; font-weight: 800; color: @acc; }}
.status {{ font-size: 8pt; color: alpha(@fg, 0.6); letter-spacing: 1px; }}
.status.bad {{ color: @red; }}
button.nbtn, button.row {{ background-image: none; box-shadow: none; text-shadow: none;
    background-color: alpha(@black, 0.55); border: 1px solid alpha(@acc, 0.3); border-radius: 12px;
    padding: 7px 14px; color: @fg; transition: all 140ms ease; }}
button.nbtn:hover, button.row:hover {{ border-color: @acc; background-color: alpha(@acc, 0.14); }}
button.nbtn.accent {{ background-color: alpha(@acc, 0.22); border-color: @acc; }}
button.nbtn.danger {{ border-color: alpha(@red, 0.6); }}
button.nbtn.danger:hover {{ background-color: alpha(@red, 0.18); }}
button.row {{ padding: 9px 12px; border-color: alpha(@acc, 0.12); }}
button.row.sel {{ background-color: alpha(@acc, 0.18); border-color: @acc; }}
entry {{ background-image: none; background-color: alpha(@black, 0.7); color: @fg; caret-color: @acc;
    border: 1px solid alpha(@acc, 0.3); border-radius: 10px; padding: 6px 10px; box-shadow: none; }}
entry:focus {{ border-color: @acc; }}
switch {{ background-image: none; background-color: alpha(@black, 0.7); border: 1px solid alpha(@acc, 0.35);
    border-radius: 14px; }}
switch:checked {{ background-color: alpha(@acc, 0.55); }}
switch slider {{ background-image: none; background-color: @fg; border-radius: 12px; border: none;
    box-shadow: none; min-width: 20px; min-height: 20px; }}
scrolledwindow, viewport {{ background: transparent; border: none; }}
''').encode())
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css,
                                                 Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def on_draw(self, _w, cr):
        W, H = self.get_allocated_width(), self.get_allocated_height()
        if self.bg is None or (self.bg.get_width(), self.bg.get_height()) != (W, H):
            self.bg = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
            bc = cairo.Context(self.bg)
            try:
                if not self.style:
                    raise ValueError
                import wsback
                import wscard
                bc.set_source_surface(wsback.render(self.style, W, H, wscard.ws.tint_target('windows')), 0, 0)
                bc.paint()
                bc.set_source_rgba(*self.c['bg'], 0.64)
                bc.paint()
            except Exception:
                bc.set_source_rgb(*self.c['bg'])
                bc.paint()
        cr.set_source_surface(self.bg, 0, 0)
        cr.paint()
        return False

    def say(self, text, bad=False):
        self.status.set_text(text)
        ctx = self.status.get_style_context()
        (ctx.add_class if bad else ctx.remove_class)('bad')

    def on_key(self, _w, ev):
        if Gdk.keyval_name(ev.keyval) == 'Escape':
            self.destroy()
            return True
        return False


def float_rule(cls):
    """Open floating and centered (the theme frames it like any window)."""
    subprocess.run(['bspc', 'rule', '-r', cls], capture_output=True)
    subprocess.run(['bspc', 'rule', '-a', cls, 'state=floating', 'center=on'], capture_output=True)


def terminal(command, title='RiceTask'):
    """Run command in a floating terminal that stays open at the end."""
    sh = f'{command}; printf "\\n\\033[1mDone. Press Enter to close.\\033[0m"; read _'
    for term in (['alacritty', '--class', 'FloaTerm,FloaTerm', '-T', title, '-e', 'sh', '-c', sh],
                 ['kitty', '--class', 'FloaTerm', '-T', title, 'sh', '-c', sh]):
        try:
            return subprocess.Popen(term, start_new_session=True)
        except OSError:
            continue
    return None
