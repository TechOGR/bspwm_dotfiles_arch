#!/usr/bin/env python3
# ==============================================================================
#  TechOGR · BSPWM dotfiles installer  (rice "crackone")
#  https://github.com/TechOGR/bspwm_dotfiles_arch
#
#  Arch Linux and derivatives: CachyOS, EndeavourOS, Garuda, Manjaro, BlackArch...
#  Physical machines and VMs (VMware, VirtualBox, QEMU/KVM, Hyper-V).
#
#    ./install.sh                  the normal way (it checks the basics, then runs this)
#    ./install.py                  the same, directly
#    ./install.py --yes            no questions: the recommended choices
#    ./install.py --deploy-only    only copy the rice (no packages, no system changes)
#    ./install.py --doctor         only check that everything is in place
#    ./install.py --demo           a simulated run, to see it (touches nothing)
#
#  Everything it runs goes to the log (~/.cache/techogr-install/). Your current
#  configuration is backed up first, with a restore.sh to go back.
#
#  Copyright (C) 2021-2026 TechOGR <https://github.com/TechOGR> · GPL-3.0
# ==============================================================================

import argparse
import atexit
import datetime
import glob
import os
import re
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import termios
import threading
import time
import tty
import unicodedata

VERSION = '9.0.0'
REPO = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser('~')
USER = os.environ.get('USER') or os.path.basename(HOME)
UID = os.getuid()
STAMP = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
LOG_DIR = os.path.join(HOME, '.cache', 'techogr-install')
LOG = os.path.join(LOG_DIR, f'install-{STAMP}.log')
BACKUP = os.path.join(HOME, '.dotfiles_backup', f'backup_{STAMP}')
ENV_C = {**os.environ, 'LC_ALL': 'C', 'LANG': 'C'}

# ════════════════════════════════════════════════════════════════ terminal
TTY_OUT = sys.stdout.isatty()
LINUX_VT = os.environ.get('TERM', '') == 'linux'          # the text console (limited font)
TRUECOLOR = TTY_OUT and not LINUX_VT and (
    os.environ.get('COLORTERM', '') in ('truecolor', '24bit') or
    any(t in os.environ.get('TERM', '') for t in ('kitty', 'alacritty', 'ghostty', 'direct', 'foot', 'wezterm')))
COLOR256 = TTY_OUT and not LINUX_VT and not TRUECOLOR and '256' in os.environ.get('TERM', '')

# the rice's neon palette
PAL = {
    'cyan': (125, 207, 255), 'violet': (187, 154, 247), 'pink': (255, 121, 198), 'red': (255, 72, 96),
    'green': (158, 206, 106), 'yellow': (255, 199, 119), 'fg': (220, 222, 245), 'dim': (110, 116, 150),
    'blood': (255, 30, 50), 'white': (255, 255, 255), 'track': (52, 56, 82),
}
BASIC = {'cyan': 36, 'violet': 35, 'pink': 35, 'red': 31, 'green': 32, 'yellow': 33, 'fg': 37, 'dim': 90,
         'blood': 91, 'white': 97, 'track': 90}

RESET = '\033[0m' if TTY_OUT else ''
BOLD = '\033[1m' if TTY_OUT else ''
DIM = '\033[2m' if TTY_OUT else ''


def rgb(c):
    """Foreground escape for an (r, g, b) or a palette name."""
    if not TTY_OUT:
        return ''
    name = c if isinstance(c, str) else None
    r, g, b = PAL[c] if name else c
    if TRUECOLOR:
        return f'\033[38;2;{r};{g};{b}m'
    if COLOR256:
        q = lambda v: max(0, min(5, round((v - 35) / 40)))   # noqa: E731
        return f'\033[38;5;{16 + 36 * q(r) + 6 * q(g) + q(b)}m'
    if name:
        return f'\033[{BASIC[name]}m'
    # nearest of the basic ones
    best = min(BASIC, key=lambda k: sum((a - b_) ** 2 for a, b_ in zip(PAL[k], (r, g, b))))
    return f'\033[{BASIC[best]}m'


def mix(a, b, t):
    a = PAL[a] if isinstance(a, str) else a
    b = PAL[b] if isinstance(b, str) else b
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def grad(stops, t):
    """Color at t in [0, 1] along several stops."""
    t = max(0.0, min(1.0, t))
    n = len(stops) - 1
    i = min(int(t * n), n - 1)
    return mix(stops[i], stops[i + 1], t * n - i)


def paint(text, stops, bold=False):
    """Text with a horizontal gradient (one color when the terminal can't)."""
    if not TTY_OUT:
        return text
    if not TRUECOLOR:
        return (BOLD if bold else '') + rgb(stops[0]) + text + RESET
    n = max(1, len(text) - 1)
    return (BOLD if bold else '') + ''.join(rgb(grad(stops, i / n)) + ch for i, ch in enumerate(text)) + RESET


def c(name, text, bold=False):
    return (BOLD if bold else '') + rgb(name) + text + RESET


# symbols: the text console's font has box drawing and blocks, not the rest
if LINUX_VT or not TTY_OUT:
    SYM = dict(ok='+', fail='x', warn='!', info='>', dot='*', arrow='>', spin='|/-\\', sep='-', bullet='*',
               lock='#', skull='X', tl='┌', tr='┐', bl='└', br='┘', eye='o', dash='─', more='..')
else:
    SYM = dict(ok='✔', fail='✖', warn='▲', info='›', dot='●', arrow='➜', spin='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏', sep='·',
               bullet='◆', lock='', skull='☠', tl='╭', tr='╮', bl='╰', br='╯', eye='◉', dash='┄', more='…')

RAIL = '│'
ANSI = re.compile(r'\033\[[0-9;?]*[A-Za-z]')


def vlen(s):
    """Visible width of a string (escapes out, wide characters as 2)."""
    s = ANSI.sub('', s)
    return sum(2 if unicodedata.east_asian_width(ch) in 'WF' else 0 if unicodedata.combining(ch) else 1 for ch in s)


def vcut(s, width):
    """Cut to a visible width, keeping the escapes."""
    out, w, i = [], 0, 0
    while i < len(s):
        m = ANSI.match(s, i)
        if m:
            out.append(m.group())
            i = m.end()
            continue
        ch = s[i]
        cw = 2 if unicodedata.east_asian_width(ch) in 'WF' else 1
        if w + cw > width:
            if w < width:
                out.append(SYM['more'][:width - w])
            break
        out.append(ch)
        w += cw
        i += 1
    return ''.join(out) + (RESET if TTY_OUT else '')


def cols():
    return max(40, min(shutil.get_terminal_size((100, 30)).columns, 140))


def out(s=''):
    sys.stdout.write(s + '\n')
    sys.stdout.flush()


def cursor(show):
    if TTY_OUT:
        sys.stdout.write('\033[?25h' if show else '\033[?25l')
        sys.stdout.flush()


atexit.register(lambda: cursor(True))


# ════════════════════════════════════════════════════════════════ log
os.makedirs(LOG_DIR, exist_ok=True)
_logf = open(LOG, 'a', buffering=1)
try:   # the old path, for whoever looks there
    link = os.path.join(HOME, '.techogr_install.log')
    if os.path.islink(link) or not os.path.exists(link):
        if os.path.islink(link):
            os.unlink(link)
        os.symlink(LOG, link)
except OSError:
    pass


def log(*parts):
    _logf.write(f'[{datetime.datetime.now():%H:%M:%S}] ' + ' '.join(str(p) for p in parts) + '\n')


log(f'=== TechOGR BSPWM installer {VERSION} · {datetime.datetime.now()} · user {USER} uid {UID}')


# ════════════════════════════════════════════════════════════════ art
SKULL_HALF = [
    "        ▄▄▄▄████",
    "     ▄██████████",
    "   ▄████████████",
    "  ██████████████",
    " █████▀▀▀▀▀▀████",
    " ███▀        ▀██",
    " ███    ◉     ██",
    " ████▄      ▄███",
    "  ████████████▀▌",
    "   ▀████████▀   ",
    "     ▀██████▄▄▄▄",
    "      ▐█▀█▀█▀█▀█",
    "      ▐█▄█▄█▄█▄█",
    "        ▀▀▀▀▀▀▀▀",
]
_MIRROR = {'▌': '▐', '▐': '▌'}
SKULL = [h + ''.join(_MIRROR.get(ch, ch) for ch in reversed(h)) for h in SKULL_HALF]

LOGO = [
    '████████╗███████╗ ██████╗██╗  ██╗ ██████╗  ██████╗ ██████╗ ',
    '╚══██╔══╝██╔════╝██╔════╝██║  ██║██╔═══██╗██╔════╝ ██╔══██╗',
    '   ██║   █████╗  ██║     ███████║██║   ██║██║  ███╗██████╔╝',
    '   ██║   ██╔══╝  ██║     ██╔══██║██║   ██║██║   ██║██╔══██╗',
    '   ██║   ███████╗╚██████╗██║  ██║╚██████╔╝╚██████╔╝██║  ██║',
    '   ╚═╝   ╚══════╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝',
]
LOGO_STOPS = ['cyan', 'violet', 'pink']
SKULL_STOPS = [(255, 64, 96), (214, 62, 170), (176, 80, 240)]


def skull_line(i, eyes=1.0):
    col = rgb(grad(SKULL_STOPS, i / (len(SKULL) - 1)))
    eye = rgb(mix((70, 10, 20), 'blood', eyes)) + (SYM['eye'] if eyes > 0.15 else ' ') + col
    return col + SKULL[i].replace('◉', eye) + RESET


def logo_line(j, shine=None):
    """A logo row; shine = the column of a light sweeping it."""
    text = LOGO[j]
    if not TRUECOLOR:
        return paint(text, LOGO_STOPS, bold=True)
    n = len(text) - 1
    s = []
    for i, ch in enumerate(text):
        col = grad(LOGO_STOPS, i / n)
        if shine is not None:
            d = abs(i - shine)
            if d < 7:
                col = mix(col, 'white', (1 - d / 7) ** 1.6 * 0.9)
        s.append(rgb(col) + ch)
    return BOLD + ''.join(s) + RESET


def banner(animate=True, sub=''):
    """The skull beside TechOGR, the light sweeping the letters, the eyes lighting."""
    width = cols()
    wide = width >= vlen(SKULL[0]) + len(LOGO[0]) + 6
    tagline = [paint('BSPWM DOTFILES  ' + SYM['sep'] + '  rice crackone  ' + SYM['sep'] + f'  installer v{VERSION}',
                     ['fg', 'violet'], bold=True),
               c('dim', 'Arch ' + SYM['sep'] + ' CachyOS ' + SYM['sep'] + ' EndeavourOS ' + SYM['sep'] +
                 ' Garuda ' + SYM['sep'] + ' Manjaro ' + SYM['sep'] + ' BlackArch')]
    if sub:
        tagline.append(c('dim', sub))
    top = 3                      # the logo starts on this skull row

    def frame(shine=None, eyes=1.0):
        rows = []
        if wide:
            for i in range(len(SKULL)):
                right = ''
                j = i - top
                if 0 <= j < len(LOGO):
                    right = logo_line(j, shine)
                elif j - len(LOGO) - 1 in range(len(tagline)):
                    right = tagline[j - len(LOGO) - 1]
                rows.append('  ' + skull_line(i, eyes) + '    ' + right)
        else:
            rows += ['  ' + skull_line(i, eyes) for i in range(len(SKULL))]
            if width >= len(LOGO[0]) + 2:
                rows += ['  ' + logo_line(j, shine) for j in range(len(LOGO))]
            else:
                rows.append('  ' + paint('T E C H O G R', LOGO_STOPS, bold=True))
            rows += ['  ' + t for t in tagline]
        return rows

    out()
    if not (animate and TTY_OUT and TRUECOLOR):
        for r in frame():
            out(r)
        out()
        return
    cursor(False)
    rows = frame(shine=-10, eyes=0)
    for r in rows:        # the skull comes up line by line, eyes off
        out(r)
        time.sleep(0.018)
    steps = 26
    for k in range(steps + 1):   # the light across the letters, then the eyes
        shine = -8 + (len(LOGO[0]) + 16) * k / steps
        eyes = max(0.0, (k - steps * 0.55) / (steps * 0.45))
        sys.stdout.write(f'\033[{len(rows)}A')
        for r in frame(shine, eyes):
            sys.stdout.write('\r\033[2K' + r + '\n')
        sys.stdout.flush()
        time.sleep(0.03)
    for e in (0.3, 1.0):         # a blink
        sys.stdout.write(f'\033[{len(rows)}A')
        for r in frame(None, e):
            sys.stdout.write('\r\033[2K' + r + '\n')
        sys.stdout.flush()
        time.sleep(0.09)
    out()


def rule(title='', stops=('violet', 'pink')):
    w = min(cols() - 4, 96)
    if not title:
        out('  ' + paint('─' * w, list(stops)))
        return
    t = f' {title} '
    left = 3
    out('  ' + paint('─' * left, list(stops)) + c('fg', t, True) + paint('─' * max(0, w - left - vlen(t)), list(stops)))


def box(lines, stops=('cyan', 'violet'), title='', pad=2):
    """A rounded card around some lines."""
    w = min(cols() - 4, max([vlen(l_) for l_ in lines] + [vlen(title) + 4, 40]) + pad * 2 + 2)
    edge = lambda s: paint(s, list(stops))   # noqa: E731
    head = SYM['tl'] + '─' * (w - 2) + SYM['tr']
    if title:
        t = f' {title} '
        out('  ' + edge(SYM['tl'] + '──') + c('fg', t, True) + edge('─' * max(0, w - 4 - vlen(t)) + SYM['tr']))
    else:
        out('  ' + edge(head))
    for l_ in lines:
        l_ = vcut(l_, w - 2 - pad * 2)
        out('  ' + edge('│') + ' ' * pad + l_ + ' ' * max(0, w - 2 - pad * 2 - vlen(l_)) + ' ' * pad + edge('│'))
    out('  ' + edge(SYM['bl'] + '─' * (w - 2) + SYM['br']))


def bar(frac, width, t=0.0, stops=('cyan', 'violet', 'pink'), indeterminate=False):
    """The progress bar: gradient fill with eighth blocks, a light gliding on it."""
    width = max(8, width)
    if LINUX_VT or not TTY_OUT:
        n = int(frac * width)
        if indeterminate:
            p = int((t * 12) % (width + 6)) - 3
            return '[' + ''.join('=' if 0 <= i - p < 4 else '-' for i in range(width)) + ']'
        return '[' + '#' * n + '-' * (width - n) + ']'
    cells = []
    if indeterminate:    # a comet going back and forth
        u = (t * 0.7) % 2
        u = u if u < 1 else 2 - u
        head = u * (width + 8) - 4
        for i in range(width):
            d = head - i
            a = max(0.0, 1 - abs(d) / 6)
            col = mix('track', grad(stops, i / width), a)
            cells.append(rgb(col) + ('█' if a > 0.5 else '▆' if a > 0.1 else '▁'))
        return ''.join(cells) + RESET
    full = frac * width
    glide = (t * 0.55) % 1.4 * full - 0.2 * full
    eighths = ' ▏▎▍▌▋▊▉█'
    for i in range(width):
        base = grad(stops, i / max(1, width - 1))
        if i < int(full):
            d = abs(i - glide)
            col = mix(base, 'white', max(0.0, 1 - d / 4) * 0.55) if TRUECOLOR else base
            cells.append(rgb(col) + '█')
        elif i == int(full) and full - i > 0.02:
            cells.append(rgb(base) + eighths[int((full - i) * 8)])
        else:
            cells.append(rgb('track') + '▁')
    return ''.join(cells) + RESET


def fmt_time(s):
    s = int(s)
    return f'{s // 60}m{s % 60:02d}s' if s >= 60 else f'{s}s'


# ════════════════════════════════════════════════════════════════ live panel
class Live:
    """The lines at the bottom that move: the current step, its bar and the
    whole install's bar. Messages print above them."""

    def __init__(self):
        self.lock = threading.RLock()
        self.drawn = 0
        self.active = False
        self.title = ''
        self.detail = ''
        self.frac = 0.0
        self.shown = 0.0
        self.indeterminate = True
        self.total = 0.0
        self.t0 = time.monotonic()
        self.step_t0 = time.monotonic()
        self.step_no = (0, 0)
        self.thread = None

    def start(self, no, total, title):
        with self.lock:
            self.step_no = (no, total)
            self.title = title
            self.detail = ''
            self.frac = self.shown = 0.0
            self.indeterminate = True
            self.step_t0 = time.monotonic()
            self.active = True
        if TTY_OUT and not self.thread:
            cursor(False)
            self.thread = threading.Thread(target=self.loop, daemon=True)
            self.thread.start()
        self.draw()

    def set(self, frac=None, detail=None, indeterminate=None):
        with self.lock:
            if frac is not None:
                self.frac = max(self.frac, min(1.0, frac))
                self.indeterminate = False
            if indeterminate is not None:
                self.indeterminate = indeterminate
            if detail is not None:
                self.detail = detail

    def loop(self):
        while True:
            time.sleep(0.07)
            if self.active:
                self.draw()

    def lines(self):
        t = time.monotonic() - self.t0
        w = cols()
        no, total = self.step_no
        spin = SYM['spin'][int(t * 12) % len(SYM['spin'])]
        self.shown += (self.frac - self.shown) * 0.25
        rail = '  ' + rgb('violet') + RAIL + RESET
        bw = max(10, min(w - 26, 64))
        pct = c('dim', ' ···') if self.indeterminate else c('fg', f'{self.shown * 100:5.1f}%', True)
        el = c('dim', fmt_time(time.monotonic() - self.step_t0))
        line1 = rail + '  ' + c('pink', spin, True) + ' ' + bar(self.shown, bw, t, indeterminate=self.indeterminate) + \
            ' ' + pct + '  ' + el
        line2 = rail + '    ' + c('dim', self.detail or SYM['more'])
        overall = ((no - 1) + (self.shown if not self.indeterminate else 0.3)) / max(1, total)
        ow = max(10, min(w - 36, 44))
        line3 = ('  ' + rgb('violet') + SYM['bl'] + SYM['dash'] + RESET + ' ' + c('dim', f'total {no}/{total} ') +
                 bar(overall, ow, t, stops=('violet', 'pink')) + ' ' + c('dim', f'{overall * 100:3.0f}%  {SYM["sep"]}  '
                                                                     f'{fmt_time(t)}'))
        return [vcut(x, w - 1) for x in (line1, line2, line3)]

    def draw(self):
        if not TTY_OUT:
            return
        with self.lock:
            ls = self.lines() if self.active else []
            buf = []
            if self.drawn:
                buf.append(f'\033[{self.drawn}A')
            for l_ in ls:
                buf.append('\r\033[2K' + l_ + '\n')
            for _ in range(max(0, self.drawn - len(ls))):
                buf.append('\r\033[2K\n')
            if self.drawn > len(ls):
                buf.append(f'\033[{self.drawn - len(ls)}A')
            self.drawn = len(ls)
            sys.stdout.write(''.join(buf))
            sys.stdout.flush()

    def clear(self):
        with self.lock:
            if TTY_OUT and self.drawn:
                sys.stdout.write(f'\033[{self.drawn}A' + '\r\033[J')
                sys.stdout.flush()
            self.drawn = 0

    def say(self, text):
        """A line that stays, above the moving panel."""
        with self.lock:
            self.clear()
            out(text)
            if self.active:
                self.draw()
        log('  ' + ANSI.sub('', text).strip())

    def stop(self):
        with self.lock:
            self.clear()
            self.active = False


LIVE = Live()


def _rail():
    return '  ' + rgb('violet') + RAIL + RESET + '  '


def ok(msg):
    LIVE.say(_rail() + c('green', SYM['ok'], True) + ' ' + c('fg', msg))


def warn(msg, keep=True):
    LIVE.say(_rail() + c('yellow', SYM['warn'], True) + ' ' + c('yellow', msg))
    if keep:
        STATE['warnings'].append(ANSI.sub('', msg))


def info(msg):
    LIVE.say(_rail() + c('cyan', SYM['info']) + ' ' + c('dim', msg))


def fail(msg):
    LIVE.say(_rail() + c('red', SYM['fail'], True) + ' ' + c('red', msg))


STATE = {'warnings': [], 'failed_optional': [], 'failed_required': [], 'installed': 0, 'aur': None, 'errors': [],
         'hw': {}, 'steps': [], 'reboot': False}


# ════════════════════════════════════════════════════════════════ running things
class Aborted(Exception):
    pass


CHILD = {'proc': None}


def run(cmd, parse=None, sudo=False, check=False, input_=None, env=None, cwd=None, timeout=None):
    """Run a command with its output in the log (never on the screen); each
    line goes to parse(line) to move the bar. -> (rc, last lines)."""
    if sudo:
        cmd = ['sudo', '-n', *cmd] if not ARGS.demo else cmd
    log('$ ' + ' '.join(cmd))
    if ARGS.demo:
        return demo_run(cmd, parse)
    tail = []
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.PIPE if input_
                             else subprocess.DEVNULL, env=env or ENV_C, cwd=cwd, text=True, errors='replace',
                             bufsize=1, process_group=0)
    except OSError as e:
        log(f'  ! {e}')
        return 127, [str(e)]
    CHILD['proc'] = p
    if input_:
        try:
            p.stdin.write(input_)
            p.stdin.close()
        except OSError:
            pass
    t0 = time.monotonic()
    for line in p.stdout:
        line = line.rstrip('\n')
        for part in line.split('\r'):
            if not part.strip():
                continue
            _logf.write('    ' + part + '\n')
            tail.append(part)
            del tail[:-40]
            if parse:
                try:
                    parse(part)
                except Exception as e:   # a parser never stops an install
                    log(f'  (parser: {e})')
        if timeout and time.monotonic() - t0 > timeout:
            p.kill()
    rc = p.wait()
    CHILD['proc'] = None
    log(f'  → rc {rc}')
    if check and rc != 0:
        raise RuntimeError(f'{" ".join(cmd)} → {rc}')
    return rc, tail


def quiet(cmd, sudo=False):
    """A short command whose output doesn't matter; True when it worked."""
    return run(cmd, sudo=sudo)[0] == 0


def have(cmd):
    return shutil.which(cmd) is not None


def capture(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, env=ENV_C, timeout=60).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ''


# ── pacman / AUR progress, from their own output
class PacmanProgress:
    """sync → download → verify → install → hooks, each a part of the bar."""
    SPAN = {'sync': (0.0, 0.05), 'resolve': (0.05, 0.08), 'download': (0.08, 0.45), 'verify': (0.45, 0.52),
            'install': (0.52, 0.93), 'hooks': (0.93, 1.0)}
    NAMES = {'sync': 'sincronizando repositorios', 'resolve': 'resolviendo dependencias', 'download': 'descargando',
             'verify': 'verificando firmas y conflictos', 'install': 'instalando', 'hooks': 'ejecutando hooks'}

    def __init__(self, lo=0.0, hi=1.0):
        self.lo, self.hi = lo, hi
        self.n = 0
        self.dl = 0
        self.done = 0
        self.phase = 'sync'
        self.nothing = False

    def to(self, phase, inner=0.0, detail=None):
        self.phase = phase
        a, b = self.SPAN[phase]
        f = a + (b - a) * max(0.0, min(1.0, inner))
        LIVE.set(self.lo + (self.hi - self.lo) * f, detail if detail is not None else self.NAMES[phase])

    def __call__(self, line):
        low = line.lower().strip()
        m = re.match(r'^packages \((\d+)\)', low)
        if m:
            self.n = int(m.group(1))
            self.to('resolve', 1, f'{self.n} paquetes')
        elif 'synchronizing package databases' in low:
            self.to('sync', 0)
        elif re.match(r'^\S+ downloading\.\.\.$', low) or low.endswith(' downloading...'):
            name = low.split()[0]
            if self.phase in ('sync',):
                self.to('sync', 0.5, f'base de datos {name}')
                return
            self.dl += 1
            self.to('download', self.dl / max(1, self.n), f'descargando {name}')
        elif 'retrieving packages' in low:
            self.to('download', 0)
        elif 'starting full system upgrade' in low or 'resolving dependencies' in low:
            self.to('resolve', 0)
        elif any(k in low for k in ('checking keyring', 'checking package integrity', 'loading package files',
                                    'checking for file conflicts', 'checking available disk space')):
            self.to('verify', 0.5, low.rstrip('.'))
        elif re.match(r'^(installing|upgrading|reinstalling|downgrading|removing) \S+\.\.\.$', low):
            verb, name = low.split()[0], low.split()[1].rstrip('.')
            self.done += 1
            STATE['installed'] += verb != 'removing'
            es = {'installing': 'instalando', 'upgrading': 'actualizando', 'reinstalling': 'reinstalando',
                  'downgrading': 'bajando versión', 'removing': 'quitando'}[verb]
            self.to('install', self.done / max(1, self.n), f'{es} {name}  ({self.done}/{self.n or "?"})')
        elif 'running post-transaction hooks' in low:
            self.to('hooks', 0)
        elif self.phase == 'hooks' and re.match(r'^\((\d+)/(\d+)\) ', low):
            i, n = map(int, re.match(r'^\((\d+)/(\d+)\) ', low).groups())
            self.to('hooks', i / n, line.split(') ', 1)[1].rstrip('.').strip())
        elif 'there is nothing to do' in low:
            self.nothing = True
            LIVE.set(self.hi, 'nada que hacer: ya estaba al día')


class AurProgress:
    """One AUR package: fetch → build → install."""

    def __init__(self, name, lo, hi):
        self.name, self.lo, self.hi = name, lo, hi
        self.f = 0.0

    def at(self, f, detail):
        self.f = max(self.f, f)
        LIVE.set(self.lo + (self.hi - self.lo) * self.f, f'{self.name}: {detail}')

    def __call__(self, line):
        low = line.lower()
        if 'cloning' in low or 'downloading' in low or 'retrieving' in low:
            self.at(0.1, 'descargando')
        elif '==> making package' in low:
            self.at(0.2, 'compilando')
        elif '==> starting build()' in low or 'compiling' in low:
            self.at(min(0.75, self.f + 0.01), 'compilando  ' + line.strip()[:50])
        elif '==> starting package()' in low or '==> tidying' in low:
            self.at(0.8, 'empaquetando')
        elif '==> finished making' in low:
            self.at(0.85, 'instalando')
        elif re.match(r'^(installing|upgrading) \S+\.\.\.$', low.strip()):
            self.at(0.95, 'instalando')


# ════════════════════════════════════════════════════════════════ demo mode
def demo_run(cmd, parse):
    """What the real commands would print, slowly, to see the installer."""
    joined = ' '.join(cmd)
    lines = []
    if 'pacman' in joined and ('-S' in cmd or '-Syu' in cmd or '-Su' in cmd):
        skip = {cmd[i + 1] for i, a in enumerate(cmd[:-1]) if a in ('--color', '--ask', '--overwrite')}
        pk = [a for a in cmd if not a.startswith('-') and a not in ('pacman', 'sudo') and a not in skip][:60] or \
            ['linux', 'mesa', 'glibc', 'systemd', 'python']
        n = len(pk)
        if '-Syu' in cmd or '-Sy' in cmd:
            lines += [':: Synchronizing package databases...', ' core downloading...', ' extra downloading...']
        lines += ['resolving dependencies...', 'looking for conflicting packages...', '',
                  f'Packages ({n}) ' + ' '.join(pk), '', 'Total Download Size:  120.00 MiB',
                  ':: Retrieving packages...']
        lines += [f' {p}-1.0-1-x86_64 downloading...' for p in pk]
        lines += ['checking keyring...', 'checking package integrity...', 'loading package files...',
                  'checking for file conflicts...', ':: Processing package changes...']
        lines += [f'installing {p}...' for p in pk]
        lines += [':: Running post-transaction hooks...', '(1/3) Arming ConditionNeedsUpdate...',
                  '(2/3) Updating icon theme caches...', '(3/3) Updating fontconfig cache...']
        delay = min(0.06, 6 / max(1, len(lines)))
    elif cmd[0] in ('yay', 'paru') or 'makepkg' in joined:
        lines = [':: Cloning ' + cmd[-1], '==> Making package: ' + cmd[-1], '==> Starting build()...'] + \
                [f'   Compiling crate-{i} v0.{i}.0' for i in range(18)] + \
                ['==> Starting package()...', '==> Finished making: ' + cmd[-1], f'installing {cmd[-1]}...']
        delay = 0.09
    else:
        delay = 0.05
        lines = [joined[:60]]
    for ln in lines:
        _logf.write('    ' + ln + '\n')
        if parse:
            parse(ln)
        time.sleep(delay)
    fail_it = any(x in joined for x in ('xcolor',))       # one optional failure, to see it
    # TECHOGR_DEMO_FAIL=<text>: the first command with it fails (to see the error card)
    want = os.environ.get('TECHOGR_DEMO_FAIL')
    if want and want in joined and len(DEMO_FAILED) < 2:   # the batch and the retry alone
        DEMO_FAILED.append(joined)
        for ln in ('error: failed retrieving file \'mesa-1.0-1-x86_64.pkg.tar.zst\' from mirror.example.org : '
                   'Operation too slow', 'warning: failed to retrieve some files',
                   'error: failed to commit transaction (failed to retrieve some files)', 'Errors occurred, no packages '
                   'were upgraded.'):
            _logf.write('    ' + ln + '\n')
        return 1, ['error: failed to commit transaction']
    return (1 if fail_it else 0), lines[-5:]


DEMO_FAILED = []


# ════════════════════════════════════════════════════════════════ questions
def read_key():
    """One key from the keyboard: 'up', 'down', 'space', 'enter', 'esc' or the char."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = os.read(fd, 1).decode(errors='ignore')
        if ch == '\x1b':
            if select.select([fd], [], [], 0.03)[0]:
                seq = os.read(fd, 2).decode(errors='ignore')
                return {'[A': 'up', '[B': 'down', '[C': 'right', '[D': 'left'}.get(seq, 'esc')
            return 'esc'
        if ch in ('\r', '\n'):
            return 'enter'
        if ch == ' ':
            return 'space'
        if ch == '\x03':
            raise KeyboardInterrupt
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def ask_yes(question, default=True):
    if ARGS.yes or not sys.stdin.isatty():
        return default
    hint = 'S/n' if default else 's/N'
    sys.stdout.write('   ' + c('pink', SYM['arrow'], True) + ' ' + c('fg', question, True) + ' ' + c('dim', f'[{hint}] '))
    sys.stdout.flush()
    cursor(True)
    try:
        ans = input().strip().lower()
    except EOFError:
        ans = ''
    return default if not ans else ans in ('s', 'si', 'sí', 'y', 'yes')


def checklist(title, items):
    """items: [dict(key, label, desc, on, locked)] -> {key: on}. Arrows, space, enter."""
    if ARGS.yes or not sys.stdin.isatty() or not TTY_OUT:
        return {it['key']: it['on'] for it in items}
    pos = 0
    cursor(False)
    n_lines = len(items) + 4

    def draw(first=False):
        if not first:
            sys.stdout.write(f'\033[{n_lines}A')
        buf = ['\r\033[2K  ' + c('fg', title, True),
               '\r\033[2K  ' + c('dim', '↑↓ moverse   espacio marcar   enter continuar'), '\r\033[2K']
        for i, it in enumerate(items):
            here = i == pos
            mark = (c('green', '[' + SYM['ok'] + ']', True) if it['on'] else c('dim', '[ ]'))
            if it.get('locked'):
                mark = c('dim', '[' + SYM['lock'] + ']') if LINUX_VT else c('violet', '[' + SYM['ok'] + ']')
            ptr = c('pink', SYM['arrow'], True) if here else ' '
            label = c('white' if here else 'fg', it['label'], here)
            desc = c('dim', '  ' + it['desc'])
            buf.append('\r\033[2K  ' + vcut(f'{ptr} {mark} {label}{desc}', cols() - 3))
        buf.append('\r\033[2K')
        sys.stdout.write('\n'.join(buf) + '\n')
        sys.stdout.flush()

    draw(True)
    while True:
        k = read_key()
        if k in ('up', 'k'):
            pos = (pos - 1) % len(items)
        elif k in ('down', 'j', '\t'):
            pos = (pos + 1) % len(items)
        elif k == 'space' and not items[pos].get('locked'):
            items[pos]['on'] = not items[pos]['on']
        elif k == 'enter':
            break
        elif k in ('esc', 'q'):
            raise KeyboardInterrupt
        draw()
    return {it['key']: it['on'] for it in items}


def choose(question, options, default=0):
    """options: [(key, label)] -> key. Arrows and enter."""
    if ARGS.yes or not sys.stdin.isatty() or not TTY_OUT:
        return options[default][0]
    pos = default
    cursor(False)

    def draw(first=False):
        if not first:
            sys.stdout.write(f'\033[{len(options) + 1}A')
        sys.stdout.write('\r\033[2K   ' + c('pink', SYM['arrow'], True) + ' ' + c('fg', question, True) + '\n')
        for i, (_k, label) in enumerate(options):
            sel = i == pos
            sys.stdout.write('\r\033[2K      ' + (c('pink', SYM['dot']) if sel else c('dim', '○' if not LINUX_VT else 'o'))
                             + ' ' + c('white' if sel else 'dim', label, sel) + '\n')
        sys.stdout.flush()

    draw(True)
    while True:
        k = read_key()
        if k in ('up', 'k', 'left'):
            pos = (pos - 1) % len(options)
        elif k in ('down', 'j', 'right', '\t'):
            pos = (pos + 1) % len(options)
        elif k == 'enter':
            return options[pos][0]
        elif k in ('esc', 'q'):
            raise KeyboardInterrupt
        draw()


# ════════════════════════════════════════════════════════════════ packages
# Every one that the rice uses. Where each comes from (official repos or AUR) is
# decided on the machine: CachyOS has in its repos several that Arch keeps in AUR.
CORE = [
    # X11
    'xorg-server', 'xorg-xinit', 'xorg-xrandr', 'xorg-xrdb', 'xorg-xsetroot', 'xorg-xset', 'xorg-xprop',
    'xorg-xinput', 'xorg-xauth', 'xorg-xdpyinfo', 'xorg-xwininfo', 'xorg-setxkbmap', 'libxcvt',
    'xf86-input-libinput',
    # the desktop
    'bspwm', 'sxhkd', 'polybar', 'rofi', 'picom', 'dunst', 'libnotify', 'jgmenu', 'xsettingsd', 'hsetroot',
    'feh', 'imagemagick', 'jq', 'xdotool', 'xdo', 'xclip', 'maim', 'ffmpeg', 'mpv', 'clipcat', 'xss-lock',
    'pacman-contrib', 'bc', 'wget', 'curl', 'rsync', 'unzip', 'git', 'xdg-utils', 'xdg-user-dirs',
    # the rice's own windows (GTK3 + cairo in Python)
    'python', 'python-gobject', 'python-cairo', 'python-pillow', 'python-numpy', 'gtk3', 'librsvg',
    # terminals, shell
    'alacritty', 'kitty', 'zsh', 'zsh-autosuggestions', 'zsh-syntax-highlighting',
    'zsh-history-substring-search', 'fzf', 'eza', 'bat',
    # sound, brightness, media keys
    'brightnessctl', 'pamixer', 'playerctl', 'alsa-utils', 'libpulse',
    # session
    'polkit', 'lxsession', 'dbus', 'networkmanager', 'network-manager-applet',
    # files
    'thunar', 'tumbler', 'gvfs', 'ffmpegthumbnailer',
    # looks
    'papirus-icon-theme', 'ttf-jetbrains-mono-nerd', 'ttf-font-awesome', 'noto-fonts', 'noto-fonts-emoji',
]
# (AUR on Arch; a failure here is reported but does not stop the install)
CORE_AUR = ['eww', 'i3lock-color', 'betterlockscreen', 'bibata-cursor-theme-bin', 'fzf-tab']

GROUPS = [
    dict(key='login', label='Login TechOGR', desc='LightDM con la pantalla de inicio del rice', on=True,
         pkgs=['lightdm', 'lightdm-gtk-greeter', 'lightdm-webkit2-greeter']),
    dict(key='media', label='Música y visuales', desc='mpd, ncmpcpp, cava, yt-dlp', on=True,
         pkgs=['mpd', 'mpc', 'ncmpcpp', 'cava', 'yt-dlp']),
    dict(key='tools', label='Herramientas', desc='yazi, zathura, btop, fastfetch, neovim, sensores, xcolor',
         on=True, pkgs=['yazi', 'zathura', 'zathura-pdf-mupdf', 'btop', 'fastfetch', 'neovim', 'lm_sensors',
                        'redshift', 'xcolor', '7zip', 'tree', 'pavucontrol']),
    dict(key='terms', label='Más terminales', desc='ghostty y geany (el selector de terminal los muestra)',
         on=False, pkgs=['ghostty', 'geany']),
    dict(key='vault', label='Bóveda de contraseñas', desc='pass + pass-otp (super+alt+x)', on=True,
         pkgs=['pass', 'pass-otp', 'gnupg', 'pinentry']),
    dict(key='bluetooth', label='Bluetooth', desc='bluez (se detecta si hay adaptador)', on=False,
         pkgs=['bluez', 'bluez-utils']),
    dict(key='browser', label='Brave', desc='navegador predeterminado', on=True, pkgs=['brave-bin']),
    dict(key='rootzsh', label='Zsh también para root', desc='mismo prompt y estilo con sudo -i', on=True, pkgs=[]),
]

# packages that others replace (the new one wins, pacman asks and --ask 4 says yes)
REPLACES = {'i3lock-color': ['i3lock'], 'pipewire-pulse': ['pulseaudio', 'pulseaudio-bluetooth']}


def repo_packages():
    """Names in the enabled repos (a set)."""
    return set(capture(['pacman', '-Slq']).split())


def missing(pkgs):
    """Which of pkgs are not satisfied (installed, or provided by something installed)."""
    if not pkgs:
        return []
    r = subprocess.run(['pacman', '-T', *pkgs], capture_output=True, text=True, env=ENV_C)
    return [p for p in r.stdout.split() if p]


def pacman_install(pkgs, lo, hi, required=True, what='paquetes'):
    """All of them in one transaction (fast), each alone when that fails to
    find which one can't be installed. -> the ones that failed."""
    pkgs = [p for p in pkgs if p]
    if not pkgs:
        LIVE.set(hi)
        return []
    todo = missing(pkgs) if not ARGS.demo else pkgs
    if not todo:
        LIVE.set(hi, f'{len(pkgs)} {what} ya instalados')
        return []
    for new, olds in REPLACES.items():   # a conflicting one out first (i3lock → i3lock-color)
        if new in todo:
            for old in olds:
                if not ARGS.demo and subprocess.run(['pacman', '-Qq', old], capture_output=True).returncode == 0:
                    quiet(['pacman', '-Rdd', '--noconfirm', old], sudo=True)
    base = ['pacman', '-S', '--needed', '--noconfirm', '--noprogressbar', '--color', 'never', '--ask', '4']
    rc, tail = run(base + todo, parse=PacmanProgress(lo, hi), sudo=True)
    if rc == 0:
        return []
    log(f'  batch failed ({rc}); one by one')
    failed = []
    for i, p in enumerate(todo):
        if not ARGS.demo and not missing([p]):
            continue
        span = (hi - lo) / len(todo)
        rc, tail = run(base + [p], parse=PacmanProgress(lo + span * i, lo + span * (i + 1)), sudo=True)
        if rc != 0 and any('exists in filesystem' in t for t in tail):
            # files left by something removed by hand: pacman owns them now
            log(f'  {p}: file conflicts, retrying with --overwrite')
            rc, tail = run(base + ['--overwrite', '*', p], sudo=True)
        if rc != 0:
            failed.append(p)
            (STATE['failed_required'] if required else STATE['failed_optional']).append(p)
            remember_errors(p, tail)
    return failed


def remember_errors(what, tail):
    errs = [t.strip() for t in tail if re.match(r'\s*(error|warning|==> error|:: .*conflict)', t, re.I)]
    STATE['errors'].extend(f'{what}: {e}' for e in (errs or tail[-3:])[-4:])


# what to do about the usual pacman / makepkg errors
HINTS = [
    (r'failed retrieving file|operation too slow|could not resolve host|timeout',
     'Un mirror lento o caído. Reintenta; si sigue, actualiza los mirrors (sudo reflector --latest 10 '
     '--sort rate --save /etc/pacman.d/mirrorlist, o cachyos-rate-mirrors en CachyOS).'),
    (r'invalid or corrupted package|signature .* is (unknown trust|invalid)|pgp signature',
     'Llaves de firma viejas: sudo pacman -Sy archlinux-keyring y reintenta.'),
    (r'unable to lock database', 'Otro gestor de paquetes está en uso: espera a que termine y reintenta.'),
    (r'exists in filesystem|conflicting files', 'Archivos de otro paquete en conflicto: el reintento los resuelve.'),
    (r'could not satisfy dependencies|unable to satisfy dependency|breaks dependency',
     'Dependencias rotas: actualiza el sistema (sudo pacman -Syu) y reintenta.'),
    (r'not enough free disk space|no space left', 'Sin espacio en disco: libera espacio (sudo pacman -Scc) y reintenta.'),
    (r'target not found', 'Ese paquete no existe en tus repositorios: se puede saltar.'),
]


def aur_install(pkgs, lo, hi, required=False):
    helper = STATE['aur']
    todo = missing(pkgs) if not ARGS.demo else pkgs
    if not todo:
        LIVE.set(hi)
        return []
    if not helper:
        for p in todo:
            (STATE['failed_required'] if required else STATE['failed_optional']).append(p)
        return todo
    failed = []
    span = (hi - lo) / len(todo)
    for i, p in enumerate(todo):
        for new, olds in REPLACES.items():
            if new == p:
                for old in olds:
                    if not ARGS.demo and subprocess.run(['pacman', '-Qq', old], capture_output=True).returncode == 0:
                        quiet(['pacman', '-Rdd', '--noconfirm', old], sudo=True)
        if helper == 'paru':
            cmd = ['paru', '-S', '--needed', '--noconfirm', '--skipreview', '--removemake', '--sudoloop', p]
        else:
            cmd = ['yay', '-S', '--needed', '--noconfirm', '--answerdiff', 'None', '--answerclean', 'None',
                   '--answeredit', 'None', '--removemake', '--cleanafter', '--sudoloop', p]
        rc, tail = run(cmd, parse=AurProgress(p, lo + span * i, lo + span * (i + 1)), env={**ENV_C})
        if rc != 0:
            remember_errors(p, tail)
            failed.append(p)
            (STATE['failed_required'] if required else STATE['failed_optional']).append(p)
        LIVE.set(lo + span * (i + 1))
    return failed


def install_set(pkgs, lo, hi, required=True, what='paquetes'):
    """Repo ones with pacman, the rest from AUR."""
    in_repo = REPO_PKGS if not ARGS.demo else set(pkgs) - {'eww', 'bibata-cursor-theme-bin', 'fzf-tab',
                                                          'betterlockscreen', 'xcolor'}
    official = [p for p in pkgs if p in in_repo]
    aur = [p for p in pkgs if p not in in_repo]
    mid = lo + (hi - lo) * (len(official) / max(1, len(pkgs)))
    failed = pacman_install(official, lo, mid, required, what)
    failed += aur_install(aur, mid, hi, required)
    return failed


REPO_PKGS = set()


# ════════════════════════════════════════════════════════════════ steps
def step_checks():
    """The machine can take the rice."""
    if UID == 0:
        raise Aborted('No lo ejecutes como root: usa tu usuario normal (./install.sh). sudo se pide solo.')
    osr = {}
    try:
        for line in open('/etc/os-release'):
            k, _, v = line.strip().partition('=')
            osr[k] = v.strip('"')
    except OSError:
        pass
    ident = (osr.get('ID', '') + ' ' + osr.get('ID_LIKE', '')).lower()
    if not ARGS.demo and ('arch' not in ident and not any(d in ident for d in (
            'cachyos', 'endeavouros', 'garuda', 'manjaro', 'blackarch', 'arcolinux', 'artix'))):
        raise Aborted(f'"{osr.get("PRETTY_NAME", "?")}" no es una distribución basada en Arch.')
    ok(f'Sistema: {osr.get("PRETTY_NAME", "Arch Linux")}  {SYM["sep"]}  kernel {os.uname().release}')
    LIVE.set(0.2)
    if os.uname().machine != 'x86_64':
        raise Aborted(f'Arquitectura {os.uname().machine}: solo x86_64.')
    for need in ('pacman', 'sudo', 'systemctl'):
        if not have(need) and not ARGS.demo:
            raise Aborted(f'Falta {need}.')
    # space: the packages need a few GB
    free_root = shutil.disk_usage('/').free / 2 ** 30
    free_home = shutil.disk_usage(HOME).free / 2 ** 30
    if free_root < 4 and not ARGS.demo:
        raise Aborted(f'Solo {free_root:.1f} GiB libres en /: hacen falta al menos 4 GiB.')
    ok(f'Espacio libre: {free_root:.1f} GiB en /  {SYM["sep"]}  {free_home:.1f} GiB en tu home')
    LIVE.set(0.4, 'comprobando la conexión')
    # network
    net = ARGS.demo
    for url in ('https://archlinux.org', 'https://aur.archlinux.org', 'https://github.com'):
        if net:
            break
        try:
            import urllib.request
            urllib.request.urlopen(url, timeout=8)
            net = True
        except Exception as e:   # noqa: BLE001
            log(f'  net {url}: {e}')
    if not net:
        raise Aborted('Sin conexión a internet (archlinux.org no responde). Conecta la red y vuelve a ejecutarlo.')
    ok('Conexión a internet')
    LIVE.set(0.6, 'comprobando pacman')
    # pacman lock
    if os.path.exists('/var/lib/pacman/db.lck') and not ARGS.demo:
        busy = any(capture(['pgrep', '-x', p]).strip() for p in ('pacman', 'yay', 'paru', 'makepkg', 'pamac'))
        if busy:
            raise Aborted('Otro gestor de paquetes está en uso: espera a que termine y vuelve a ejecutarlo.')
        LIVE.stop()
        if not ask_yes('pacman quedó bloqueado por una operación interrumpida. ¿Quitar el bloqueo?', True):
            raise Aborted('pacman bloqueado (/var/lib/pacman/db.lck).')
        run(['rm', '-f', '/var/lib/pacman/db.lck'], sudo=True)
        LIVE.active = True
        ok('Bloqueo de pacman quitado')
    LIVE.set(1.0)


def sudo_auth():
    """The password once, then kept alive until the end."""
    if ARGS.demo:
        ok('sudo autorizado (demo)')
        return
    if subprocess.run(['sudo', '-n', 'true'], capture_output=True).returncode != 0:
        LIVE.stop()
        cursor(True)
        out('   ' + c('pink', SYM['lock'] + ' ' if not LINUX_VT else '', True) +
            c('fg', 'El instalador necesita tu contraseña de administrador (sudo), solo esta vez.'))
        prompt = '   ' + rgb('violet') + BOLD + '   contraseña de ' + USER + ': ' + RESET
        for _ in range(3):
            if subprocess.run(['sudo', '-v', '-p', prompt]).returncode == 0:
                break
        else:
            raise Aborted('No se pudo autenticar con sudo.')
        if subprocess.run(['sudo', '-n', 'true'], capture_output=True).returncode != 0:
            raise Aborted('sudo está configurado para pedir la contraseña en cada orden (timestamp_timeout=0). '
                          'Para instalar, quita esa línea con "sudo visudo" y vuelve a ejecutar ./install.sh.')
        LIVE.active = True
    ok('sudo autorizado (se mantiene activo hasta el final)')

    def keep():
        while True:
            time.sleep(50)
            subprocess.run(['sudo', '-n', '-v'], capture_output=True)
    threading.Thread(target=keep, daemon=True).start()


def step_sync():
    """Keyrings first (an old ISO has expired keys), then the whole system:
    installing on a half-updated Arch breaks things (partial upgrades)."""
    global REPO_PKGS
    rc, _t = run(['pacman', '-Sy', '--noprogressbar', '--color', 'never'], parse=PacmanProgress(0, 0.08), sudo=True)
    if rc != 0:
        raise RuntimeError('No se pudieron sincronizar los repositorios (¿mirrors caídos?).')
    REPO_PKGS = repo_packages()
    keyrings = [k for k in ('archlinux-keyring', 'cachyos-keyring', 'endeavouros-keyring', 'manjaro-keyring',
                            'chaotic-keyring', 'blackarch-keyring') if k in REPO_PKGS or ARGS.demo][:2]
    if keyrings:
        LIVE.set(0.1, 'actualizando llaves de firma: ' + ', '.join(keyrings))
        run(['pacman', '-S', '--needed', '--noconfirm', '--noprogressbar', '--color', 'never', *keyrings],
            parse=PacmanProgress(0.08, 0.15), sudo=True)
    rc, tail = run(['pacman', '-Su', '--noconfirm', '--noprogressbar', '--color', 'never', '--ask', '4'],
                   parse=PacmanProgress(0.15, 1.0), sudo=True)
    if rc != 0:
        raise RuntimeError('La actualización del sistema falló: ' + ' '.join(tail[-2:]))
    ok('Sistema actualizado')


def step_aur_helper():
    for h in ('paru', 'yay'):
        if have(h) and not ARGS.demo:
            STATE['aur'] = h
            ok(f'Ayudante de AUR: {h}')
            LIVE.set(1.0)
            return
    pacman_install(['base-devel', 'git'], 0, 0.3)
    if 'yay' in REPO_PKGS:          # CachyOS, EndeavourOS... ship it
        pacman_install(['yay'], 0.3, 1.0)
    else:
        LIVE.set(0.35, 'descargando yay-bin de AUR')
        tmp = tempfile.mkdtemp(prefix='techogr-yay.')
        rc, _t = run(['git', 'clone', '--depth=1', 'https://aur.archlinux.org/yay-bin.git', tmp + '/yay-bin'])
        if rc == 0:
            LIVE.set(0.5, 'compilando yay-bin')
            rc, _t = run(['makepkg', '-si', '--noconfirm', '--needed'], cwd=tmp + '/yay-bin',
                         parse=AurProgress('yay-bin', 0.5, 1.0))
        shutil.rmtree(tmp, ignore_errors=True)
    if have('yay') or ARGS.demo:
        STATE['aur'] = 'yay'
        ok('yay instalado')
    else:
        warn('No se pudo instalar un ayudante de AUR: los paquetes de AUR se omitirán.')


def detect_hardware():
    hw = {'virt': 'none', 'cpu': '', 'gpus': [], 'nvidia_ids': [], 'battery': False, 'bluetooth': False,
          'wifi': False, 'touchpad': False}
    v = capture(['systemd-detect-virt', '--vm']).strip()
    hw['virt'] = v if v and v != 'none' else 'none'
    try:
        cpu = open('/proc/cpuinfo').read()
        hw['cpu'] = 'intel' if 'GenuineIntel' in cpu else 'amd' if 'AuthenticAMD' in cpu else ''
    except OSError:
        pass
    lspci = capture(['lspci', '-nn']) if have('lspci') else ''
    for line in lspci.lower().splitlines():
        if not re.search(r'\[03[0-9a-f]{2}\]', line):
            continue
        for vid, name in (('10de', 'nvidia'), ('1002', 'amd'), ('8086', 'intel'), ('15ad', 'vmware'),
                          ('80ee', 'vbox'), ('1af4', 'qemu'), ('1b36', 'qemu'), ('1234', 'qemu')):
            if f'[{vid}:' in line:
                hw['gpus'].append(name)
                if name == 'nvidia':
                    m = re.findall(r'\[10de:([0-9a-f]{4})\]', line)
                    if m:
                        hw['nvidia_ids'].append(m[-1])
    hw['battery'] = bool(glob.glob('/sys/class/power_supply/BAT*'))
    hw['bluetooth'] = bool(glob.glob('/sys/class/bluetooth/*'))
    hw['wifi'] = bool(glob.glob('/sys/class/net/*/wireless'))
    try:
        hw['touchpad'] = bool(re.search(r'touchpad|trackpad|synaptics|elan', open('/proc/bus/input/devices').read(), re.I))
    except OSError:
        pass
    if ARGS.demo and not hw['gpus']:
        hw['gpus'] = ['vmware']
    return hw


def nvidia_branch(dev_id):
    i = int(dev_id, 16)
    return 'open' if i >= 0x1e00 else '580xx' if i >= 0x1340 else 'nouveau'


def step_drivers():
    if not have('lspci') and not ARGS.demo:       # a minimal Arch: needed to see the GPU
        pacman_install(['pciutils'], 0, 0.05, required=False)
        STATE['hw'] = detect_hardware()
    hw = STATE['hw']
    pk = ['mesa', 'mesa-utils', 'vulkan-icd-loader']
    if hw['virt'] == 'none':
        pk += {'intel': ['intel-ucode'], 'amd': ['amd-ucode']}.get(hw['cpu'], [])
        pk += ['linux-firmware', 'sof-firmware', 'alsa-firmware']
    for g in set(hw['gpus']):
        pk += {'intel': ['vulkan-intel', 'intel-media-driver'], 'amd': ['vulkan-radeon', 'xf86-video-amdgpu']}.get(g, [])
    vm = {'vmware': ['open-vm-tools', 'xf86-input-vmmouse', 'gtkmm3'], 'oracle': ['virtualbox-guest-utils'],
          'kvm': ['qemu-guest-agent', 'spice-vdagent'], 'qemu': ['qemu-guest-agent', 'spice-vdagent'],
          'microsoft': ['hyperv']}.get(hw['virt'], [])
    pk += vm
    # sound: PipeWire, unless the system already runs PulseAudio on purpose
    if ARGS.demo or subprocess.run(['pacman', '-Qq', 'pulseaudio'], capture_output=True).returncode != 0:
        pk += ['pipewire', 'pipewire-pulse', 'pipewire-alsa', 'wireplumber']
    if hw['battery']:
        pk += ['acpi']
        if not any(subprocess.run(['pacman', '-Qq', x], capture_output=True).returncode == 0
                   for x in ('tlp', 'auto-cpufreq')):
            pk += ['power-profiles-daemon']
    pk = [p for p in pk if p in REPO_PKGS or ARGS.demo]
    pacman_install(pk, 0, 0.7, required=False, what='drivers')
    # NVIDIA
    if 'nvidia' in hw['gpus']:
        branch = 'open'
        for i in hw['nvidia_ids']:
            b = nvidia_branch(i)
            if b == 'nouveau':
                branch = 'nouveau'
                break
            if b == '580xx':
                branch = '580xx'
        info(f'NVIDIA: rama del driver "{branch}"')
        if branch != 'nouveau':
            done = False
            if have('chwd'):          # CachyOS picks the right one itself
                LIVE.set(0.75, 'chwd: driver NVIDIA')
                done = quiet(['chwd', '-a'], sudo=True)
            if not done:
                headers = []
                for base in glob.glob('/usr/lib/modules/*/pkgbase'):
                    try:
                        headers.append(open(base).read().strip() + '-headers')
                    except OSError:
                        pass
                nv = (['nvidia-open-dkms', 'nvidia-utils', 'nvidia-settings', 'libva-nvidia-driver']
                      if branch == 'open' else ['nvidia-580xx-dkms', 'nvidia-580xx-utils', 'nvidia-580xx-settings'])
                install_set(headers + nv, 0.75, 0.95, required=False, what='drivers NVIDIA')
            run(['sh', '-c', 'printf "options nvidia_drm modeset=1 fbdev=1\\n" > /etc/modprobe.d/nvidia-techogr.conf'],
                sudo=True)
            for svc in ('nvidia-suspend.service', 'nvidia-hibernate.service', 'nvidia-resume.service'):
                enable(svc)
            if have('mkinitcpio'):
                LIVE.set(0.96, 'regenerando initramfs')
                quiet(['mkinitcpio', '-P'], sudo=True)
            STATE['reboot'] = True
        else:
            warn('GPU NVIDIA antigua: se usa el driver libre nouveau (mesa).')
    # VM services
    for svc in {'vmware': ['vmtoolsd.service', 'vmware-vmblock-fuse.service'], 'oracle': ['vboxservice.service'],
                'kvm': ['qemu-guest-agent.service'], 'qemu': ['qemu-guest-agent.service'],
                'microsoft': ['hv_kvp_daemon.service', 'hv_vss_daemon.service']}.get(hw['virt'], []):
        enable(svc)
    ok('Drivers: ' + (', '.join(sorted(set(hw['gpus']))) or 'mesa') +
       (f'  {SYM["sep"]}  invitado {hw["virt"]}' if hw['virt'] != 'none' else ''))


def enable(unit, user=False, now=True):
    if ARGS.demo:
        return True
    if user:
        return quiet(['systemctl', '--user', 'enable', *(['--now'] if now else []), unit])
    if subprocess.run(['systemctl', 'cat', unit], capture_output=True).returncode != 0:
        return False
    return quiet(['systemctl', 'enable', *(['--now'] if now else []), unit], sudo=True)


def split_packages():
    """(core from repos, extras from repos, everything that has to come from AUR)."""
    extra = [p for g in GROUPS if CHOICE.get(g['key']) for p in g['pkgs']]
    if ARGS.demo:
        known_aur = set(CORE_AUR) | {'brave-bin', 'xcolor', 'lightdm-webkit2-greeter'}
        in_repo = lambda p: p not in known_aur   # noqa: E731
    else:
        in_repo = lambda p: p in REPO_PKGS       # noqa: E731
    core = [p for p in CORE + CORE_AUR if in_repo(p)]
    extras = [p for p in extra if in_repo(p)]
    aur = [p for p in CORE + CORE_AUR + extra if not in_repo(p)]
    return core, extras, list(dict.fromkeys(aur))


def step_packages():
    core, extras, _aur = split_packages()
    core_needed = [p for p in core if p not in CORE_AUR]     # CORE_AUR ones never stop the install
    failed = pacman_install(core_needed, 0, 0.6, required=True)
    failed_soft = pacman_install([p for p in core if p in CORE_AUR], 0.6, 0.65, required=False)
    failed_opt = pacman_install(extras, 0.65, 1.0, required=False, what='extras')
    if failed:
        STATE['failed_required'] = [p for p in STATE['failed_required'] if p not in failed]
        raise RuntimeError('No se pudieron instalar: ' + ', '.join(failed))
    ok(f'Paquetes de los repositorios: {len(core) + len(extras)}' +
       (f'  {SYM["sep"]}  sin instalar: {", ".join(failed_soft + failed_opt)}' if failed_soft + failed_opt else ''))


def step_aur():
    _core, _extras, want = split_packages()
    # eww builds with Rust: rustup without a default toolchain makes it fail
    if 'eww' in want and have('rustup') and 'stable' not in capture(['rustup', 'toolchain', 'list']):
        LIVE.set(0.02, 'preparando Rust estable para compilar eww')
        run(['rustup', 'default', 'stable'])
    if not want:
        ok('Nada que instalar desde AUR: todo estaba en los repositorios')
        LIVE.set(1.0)
        return
    failed = aur_install(want, 0.05, 1.0)
    got = [p for p in want if p not in failed]
    if got:
        ok('AUR: ' + ', '.join(got))
    for p in failed:
        warn(f'{p} no se pudo instalar desde AUR (detalle en el registro)', keep=False)


# ── deploy
# Files the rice writes while you use it: a reinstall keeps them (your theme,
# avatar, dock, bar, walls...). Only what came from the repo is replaced.
USER_STATE = [
    '.rice', 'config/avatar.json', 'config/editor.json', 'config/monitors.conf', 'config/.perf_mode',
    'config/theme-walls.json', 'config/tint.json', 'config/dock.json', 'config/polybar.json',
    'config/.first_run_done', 'config/.sys', 'config/.launcher', 'config/.term', 'config/.ws_preview_enabled',
    'config/assets/avatar.png', 'rices/*/theme-config.bash', 'rices/*/user_icons/*',
]
# folders where you add your own files: never emptied (the repo's still arrive)
USER_DIRS = ['/rices/*/walls/***', '/rices/*/user_icons/***']
MIRRORED = {'bspwm'}   # the rest: updated, never emptied (bookmarks, lyrics, plugins... are yours)


def rsync(src, dst, delete=False, keep=(), protect=(), excludes=()):
    """keep: files of yours not overwritten nor deleted; protect: not deleted."""
    cmd = ['rsync', '-a', '--no-owner', '--no-group']
    if delete:
        cmd.append('--delete')
    for k in list(keep) + list(protect):
        cmd += ['--filter', f'P {k}']
    for k in keep:
        cmd += ['--exclude', k]
    for e in ('__pycache__/', *excludes):
        cmd += ['--exclude', e]
    os.makedirs(dst, exist_ok=True)
    return run(cmd + [src.rstrip('/') + '/', dst.rstrip('/') + '/'])[0] == 0


MANAGED = ['bspwm', 'alacritty', 'cava', 'clipcat', 'dunst', 'geany', 'ghostty', 'gtk-3.0', 'gtk-4.0', 'jgmenu',
           'kitty', 'mpd', 'mpv', 'ncmpcpp', 'nvim', 'paru', 'st', 'yazi', 'zathura', 'zsh', 'sxhkd', 'polybar',
           'rofi', 'picom']


def step_backup():
    existing = [d for d in MANAGED if os.path.exists(os.path.join(HOME, '.config', d))]
    files = [f for f in ('.zshrc', '.xinitrc', '.Xresources') if os.path.exists(os.path.join(HOME, f))]
    if not existing and not files:
        ok('No había configuración previa: nada que respaldar')
        LIVE.set(1.0)
        return
    os.makedirs(os.path.join(BACKUP, '.config'), exist_ok=True)
    size = 0
    for i, d in enumerate(existing):
        LIVE.set(i / max(1, len(existing)), f'~/.config/{d}')
        src = os.path.join(HOME, '.config', d)
        if ARGS.demo:
            time.sleep(0.03)
            continue
        run(['cp', '-a', src, os.path.join(BACKUP, '.config', d)])
    if ARGS.demo:
        ok(f'Respaldo: ~/{os.path.relpath(BACKUP, HOME)}  (demo: no se escribe)')
        return
    for f in files:
        if True:
            shutil.copy2(os.path.join(HOME, f), os.path.join(BACKUP, f), follow_symlinks=False)
    size = sum(os.path.getsize(os.path.join(r, f_)) for r, _d, fs in os.walk(BACKUP) for f_ in fs
               if not os.path.islink(os.path.join(r, f_)))
    with open(os.path.join(BACKUP, 'restore.sh'), 'w') as fh:
        fh.write('#!/usr/bin/env bash\n# Puts back the configuration you had before installing TechOGR.\n'
                 'set -e\nB="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"\n'
                 'for d in "$B"/.config/*/; do n=$(basename "$d"); rm -rf "$HOME/.config/$n"; '
                 'cp -a "$d" "$HOME/.config/$n"; done\n'
                 'for f in .zshrc .xinitrc .Xresources; do [[ -e "$B/$f" ]] && cp -a "$B/$f" "$HOME/$f"; done\n'
                 'echo "Configuración restaurada desde $B (cierra sesión para aplicarla)."\n')
    os.chmod(os.path.join(BACKUP, 'restore.sh'), 0o755)
    ok(f'Respaldo: ~/{os.path.relpath(BACKUP, HOME)}  ({size / 2 ** 20:.1f} MiB, con restore.sh)')
    STATE['backup'] = BACKUP


def step_deploy():
    base = os.path.join(HOME, '.config/bspwm')
    # only the ones you already have: on a first install every file of the repo arrives
    keep = ['/' + os.path.relpath(f, base) for pat in USER_STATE for f in glob.glob(os.path.join(base, pat))
            ] if CHOICE.get('keep', True) else []
    dirs = sorted(d for d in os.listdir(os.path.join(REPO, 'config')) if os.path.isdir(os.path.join(REPO, 'config', d)))
    for i, d in enumerate(dirs):
        LIVE.set(0.6 * i / len(dirs), f'config/{d}  {SYM["arrow"]}  ~/.config/{d}')
        src, dst = os.path.join(REPO, 'config', d), os.path.join(HOME, '.config', d)
        if ARGS.demo:
            time.sleep(0.04)
            continue
        if d == 'bspwm':
            okd = rsync(src, dst, delete=True, keep=keep, protect=USER_DIRS)
        elif d == 'zsh':      # history and completion cache are yours
            okd = rsync(src, dst, excludes=('zhistory', 'zcompdump*'))
        else:
            okd = rsync(src, dst, delete=d in MIRRORED)
        if not okd:
            raise RuntimeError(f'No se pudo copiar config/{d}')
    ok(f'Configuración del rice copiada a ~/.config ({len(dirs)} carpetas)' +
       ('  ' + SYM['sep'] + '  tus ajustes del rice conservados' if keep and os.path.exists(
           os.path.join(HOME, '.config/bspwm/.rice')) else ''))
    # files that carry this machine's user id
    if UID != 1000 and not ARGS.demo:
        for f in glob.glob(os.path.join(HOME, '.config/clipcat/*.toml')):
            s = open(f).read()
            if '/run/user/1000/' in s:
                open(f, 'w').write(s.replace('/run/user/1000/', f'/run/user/{UID}/'))
    LIVE.set(0.65, 'home, fuentes, aplicaciones')
    if not ARGS.demo:
        rsync(os.path.join(REPO, 'home'), HOME)
        rsync(os.path.join(REPO, 'misc/bin'), os.path.join(HOME, '.local/bin'))
        rsync(os.path.join(REPO, 'misc/fonts'), os.path.join(HOME, '.local/share/fonts'))
        rsync(os.path.join(REPO, 'misc/applications'), os.path.join(HOME, '.local/share/applications'))
        rsync(os.path.join(REPO, 'misc/asciiart'), os.path.join(HOME, '.local/share/asciiart'), delete=True)
        rsync(os.path.join(REPO, 'misc/startup-page'), os.path.join(HOME, '.local/share/startup-page'), delete=True)
        # the wallpapers folder of theme-config (CUSTOM_DIR)
        rsync(os.path.join(REPO, 'Wallpapers'), os.path.join(HOME, 'Imágenes/Wallpapers'))
        for d in ('.config/mpd/playlists', 'Música'):
            os.makedirs(os.path.join(HOME, d), exist_ok=True)
        if have('xdg-user-dirs-update'):
            quiet(['xdg-user-dirs-update'])
    ok('Fondos, fuentes, iconos del cursor y lanzadores')
    if os.environ.get('DISPLAY') and capture(['pgrep', '-x', 'bspwm']).strip() and not ARGS.demo:
        # installed from inside the rice: the files each theme generates are back to the
        # repo's; applying the theme now writes them again (bar, borders, colors)
        subprocess.Popen([os.path.join(HOME, '.config/bspwm/bin/Theme.sh')], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
        info('Sesión BSPWM abierta: el tema se vuelve a aplicar')
    LIVE.set(0.85, 'caché de fuentes')
    quiet(['fc-cache', '-f'])
    if have('update-desktop-database') and not ARGS.demo:
        quiet(['update-desktop-database', os.path.join(HOME, '.local/share/applications')])
    LIVE.set(1.0)


def step_system():
    """The session, the login screen, services, the shell."""
    hw = STATE['hw']
    # the X session entry (bspwm's package ships one; write it only when missing)
    if not os.path.exists('/usr/share/xsessions/bspwm.desktop') and not ARGS.demo:
        run(['install', '-Dm644', '/dev/stdin', '/usr/share/xsessions/bspwm.desktop'], sudo=True,
            input_='[Desktop Entry]\nName=BSPWM\nComment=Binary Space Partitioning Window Manager\n'
                   'Exec=bspwm\nTryExec=bspwm\nType=Application\nDesktopNames=BSPWM\n')
    ok('Sesión BSPWM registrada')
    LIVE.set(0.1, 'hook de pacman y ajustes de la máquina')
    if not ARGS.demo:
        run(['install', '-Dm644', os.path.join(REPO, 'misc/polybar-update.hook'),
             '/etc/pacman.d/hooks/polybar-update.hook'], sudo=True)
        if hw['virt'] == 'vmware':   # glamor on SVGA3D made vmwgfx crash the kernel
            run(['install', '-Dm644', os.path.join(REPO, 'misc/vm/20-vmware-noglamor.conf'),
                 '/etc/X11/xorg.conf.d/20-vmware-noglamor.conf'], sudo=True)
            info('VMware: glamor desactivado (evita cuelgues de vmwgfx)')
        if hw['touchpad'] and not os.path.exists('/etc/X11/xorg.conf.d/30-touchpad.conf'):
            run(['install', '-Dm644', '/dev/stdin', '/etc/X11/xorg.conf.d/30-touchpad.conf'], sudo=True,
                input_='Section "InputClass"\n    Identifier "TechOGR touchpad"\n    MatchIsTouchpad "on"\n'
                       '    Driver "libinput"\n    Option "Tapping" "on"\n    Option "NaturalScrolling" "true"\n'
                       '    Option "DisableWhileTyping" "on"\nEndSection\n')
            info('Touchpad: toque para clic y desplazamiento natural')
        try:
            os.remove(os.path.join(HOME, '.config/bspwm/config/.sys'))   # SetSysVars looks again at login
        except OSError:
            pass
    # services
    LIVE.set(0.25, 'servicios')
    other_net = [s for s in ('systemd-networkd.service', 'iwd.service', 'dhcpcd.service', 'connman.service')
                 if not ARGS.demo and subprocess.run(['systemctl', 'is-enabled', '--quiet', s]).returncode == 0]
    if other_net and subprocess.run(['systemctl', 'is-enabled', '--quiet', 'NetworkManager.service']).returncode:
        info(f'La red la gestiona {other_net[0]}: NetworkManager no se activa')
    else:
        enable('NetworkManager.service')
    if hw['bluetooth'] and (CHOICE.get('bluetooth') or ARGS.demo):
        enable('bluetooth.service')
    if hw['battery']:
        enable('power-profiles-daemon.service')
    if not ARGS.demo:
        quiet(['systemctl', '--user', 'daemon-reload'])
        for u in ('pipewire.socket', 'pipewire-pulse.socket', 'wireplumber.service'):
            quiet(['systemctl', '--user', 'enable', u])
    enable('ArchUpdates.timer', user=True)
    if CHOICE.get('media'):
        enable('mpd.service', user=True)
    ok('Servicios: red, sonido, actualizaciones' + (', bluetooth' if hw['bluetooth'] else '') +
       (', música' if CHOICE.get('media') else ''))
    # login screen
    if CHOICE.get('login'):
        LIVE.set(0.45, 'pantalla de inicio')
        setup_login()
    # no login screen at all (a minimal Arch without one): startx starts bspwm
    if not ARGS.demo and not active_dm() and not os.path.exists(os.path.join(HOME, '.xinitrc')):
        with open(os.path.join(HOME, '.xinitrc'), 'w') as fh:
            fh.write('#!/bin/sh\n# TechOGR: startx starts bspwm\n[ -f ~/.Xresources ] && xrdb -merge ~/.Xresources\n'
                     'exec dbus-run-session bspwm\n')
        info('Sin pantalla de inicio: entra con startx (ya arranca bspwm)')
        STATE['startx'] = True
    # browser
    if CHOICE.get('browser') and not ARGS.demo:
        for desk in ('brave-browser.desktop', 'com.brave.Browser.desktop'):
            if os.path.exists('/usr/share/applications/' + desk):
                quiet(['xdg-settings', 'set', 'default-web-browser', desk])
                for mime in ('x-scheme-handler/http', 'x-scheme-handler/https', 'text/html'):
                    quiet(['xdg-mime', 'default', desk, mime])
                ok('Brave es el navegador predeterminado')
                break
    # shell
    LIVE.set(0.8, 'zsh')
    zsh = shutil.which('zsh') or '/usr/bin/zsh'
    if not ARGS.demo:
        if zsh not in open('/etc/shells').read().split():
            run(['sh', '-c', f'echo {zsh} >> /etc/shells'], sudo=True)
        import pwd
        if pwd.getpwuid(UID).pw_shell != zsh:
            if not quiet(['chsh', '-s', zsh, USER], sudo=True):
                warn('No se pudo cambiar tu shell a zsh (hazlo con: chsh -s /usr/bin/zsh)')
        if CHOICE.get('rootzsh'):
            run(['install', '-Dm644', os.path.join(REPO, 'home/.zshrc'), '/root/.zshrc'], sudo=True)
            run(['install', '-d', '-m700', '/root/.config/zsh'], sudo=True)
            if os.path.exists(os.path.join(REPO, 'misc/bin/colorscript')):
                run(['install', '-Dm755', os.path.join(REPO, 'misc/bin/colorscript'), '/usr/local/bin/colorscript'],
                    sudo=True)
            run(['rsync', '-a', '--delete', '--chown=root:root', '--chmod=D755,F755',
                 os.path.join(REPO, 'misc/asciiart') + '/', '/usr/local/share/asciiart/'], sudo=True)
            if pwd.getpwnam('root').pw_shell != zsh:
                quiet(['chsh', '-s', zsh, 'root'], sudo=True)
    ok('Zsh como shell' + (' (tú y root)' if CHOICE.get('rootzsh') else ''))
    LIVE.set(1.0)


def active_dm():
    try:
        return os.path.basename(os.readlink('/etc/systemd/system/display-manager.service'))
    except OSError:
        return ''


def setup_login():
    dm = active_dm() if not ARGS.demo else ''
    if dm and dm != 'lightdm.service':
        if not CHOICE.get('replace_dm'):
            info(f'Se conserva tu pantalla de inicio actual ({dm.replace(".service", "")})')
            return
        quiet(['systemctl', 'disable', dm], sudo=True)
    if ARGS.demo:
        ok('Pantalla de inicio TechOGR (LightDM)')
        return
    if not have('lightdm'):
        warn('LightDM no está instalado: se omite la pantalla de inicio.')
        return
    run(['install', '-d', '-m755', '/etc/lightdm/lightdm.conf.d'], sudo=True)
    run(['install', '-Dm644', '/dev/stdin', '/etc/lightdm/lightdm.conf.d/50-bspwm.conf'], sudo=True,
        input_='[Seat:*]\nuser-session=bspwm\ngreeter-session=lightdm-gtk-greeter\n')
    webkit = subprocess.run(['pacman', '-Qq', 'lightdm-webkit2-greeter'], capture_output=True).returncode == 0
    themed = webkit and quiet(['bash', os.path.join(REPO, 'misc/lightdm/install-login.sh'), USER], sudo=True)
    if themed:
        rc, _t = run([os.path.join(HOME, '.config/bspwm/bin/BetterLock'), '--greeter'])
        if rc != 0:
            warn('El login usará sus colores por defecto (BetterLock --greeter falló)')
    # the plain greeter's background (from a place the lightdm user can read)
    walls = sorted(glob.glob(os.path.join(REPO, 'config/bspwm/rices/crackone/walls/*.[jp][pn]g')))
    if walls:
        ext = walls[0].rsplit('.', 1)[1]
        run(['install', '-Dm644', walls[0], f'/usr/share/backgrounds/techogr-login.{ext}'], sudo=True)
        run(['install', '-Dm644', '/dev/stdin', '/etc/lightdm/lightdm-gtk-greeter.conf.d/50-techogr.conf'], sudo=True,
            input_=f'[greeter]\nbackground=/usr/share/backgrounds/techogr-login.{ext}\n'
                   'theme-name=Adwaita-dark\nicon-theme-name=Papirus-Dark\nfont-name=JetBrainsMono Nerd Font 11\n')
    quiet(['systemctl', 'enable', '-f', 'lightdm.service'], sudo=True)
    ok('Pantalla de inicio TechOGR (LightDM' + (' + tema del rice' if themed else '') + ')')


# ── the check
def doctor(quiet_ok=False):
    """Everything the rice needs, in place. -> (passed, problems)."""
    checks = []

    def chk(name, good, hint=''):
        checks.append((name, bool(good), hint))

    for cmd in ('bspwm', 'sxhkd', 'polybar', 'rofi', 'picom', 'dunst', 'jgmenu', 'eww', 'alacritty', 'zsh', 'feh',
                'xdotool', 'xsettingsd', 'clipcatd', 'checkupdates', 'maim', 'mpv', 'hsetroot', 'playerctl',
                'pamixer', 'brightnessctl', 'nmcli', 'xss-lock'):
        chk(cmd, have(cmd), f'falta el programa {cmd}')
    lock = have('betterlockscreen') or have('i3lock')
    chk('bloqueo de pantalla', lock, 'falta betterlockscreen / i3lock')
    py = subprocess.run([sys.executable, '-c', "import gi; gi.require_version('Gtk', '3.0'); "
                         "gi.require_version('PangoCairo', '1.0'); "
                         "from gi.repository import Gtk, Gdk, Pango, PangoCairo, GLib; import cairo, PIL"],
                        capture_output=True, text=True)
    chk('Python GTK3 + cairo + Pillow', py.returncode == 0, py.stderr.strip().splitlines()[-1] if py.stderr else '')
    fonts = capture(['fc-list', ':', 'family'])
    chk('JetBrainsMono Nerd Font', 'JetBrainsMono Nerd Font' in fonts, 'ttf-jetbrains-mono-nerd')
    chk('Material Design Icons', 'Material Design Icons' in fonts or 'MaterialDesignIcons' in fonts.replace(' ', ''),
        'misc/fonts')
    base = os.path.join(HOME, '.config/bspwm')
    for f in ('bspwmrc', 'config/sxhkdrc', 'bin/Theme.sh', 'rices/crackone/theme-config.bash'):
        chk('~/.config/bspwm/' + f, os.path.exists(os.path.join(base, f)), 'vuelve a copiar la configuración')
    chk('bspwmrc ejecutable', os.access(os.path.join(base, 'bspwmrc'), os.X_OK), 'chmod +x ~/.config/bspwm/bspwmrc')
    # every script compiles / parses
    bad = []
    for f in sorted(glob.glob(os.path.join(base, 'bin/*')) + glob.glob(os.path.join(base, 'lib/*.py'))):
        if not os.path.isfile(f):
            continue
        try:
            head = open(f, 'rb').read(120)
        except OSError:
            continue
        if b'python' in head.split(b'\n')[0] or f.endswith('.py'):
            r = subprocess.run([sys.executable, '-c', 'import ast,sys; ast.parse(open(sys.argv[1]).read())', f],
                               capture_output=True)
        elif head.startswith(b'#!') and (b'sh' in head.split(b'\n')[0]):
            r = subprocess.run(['bash' if b'bash' in head.split(b'\n')[0] else 'sh', '-n', f], capture_output=True)
        else:
            continue
        if r.returncode != 0:
            bad.append(os.path.basename(f))
    chk('scripts del rice sin errores de sintaxis', not bad, ', '.join(bad))
    chk('sesión BSPWM', os.path.exists('/usr/share/xsessions/bspwm.desktop'), 'falta bspwm.desktop')
    chk('.zshrc', os.path.exists(os.path.join(HOME, '.zshrc')), 'copia home/.zshrc')
    return checks


def step_verify():
    checks = doctor()
    good = [c_ for c_ in checks if c_[1]]
    badl = [c_ for c_ in checks if not c_[1]]
    LIVE.set(1.0)
    ok(f'{len(good)} de {len(checks)} comprobaciones correctas')
    for name, _g, hint in badl:
        warn(f'{name}: {hint}')
    STATE['doctor'] = (len(good), len(checks))


# ════════════════════════════════════════════════════════════════ the flow
def run_steps(steps):
    total = len(steps)
    for no, (title, fn, required) in enumerate(steps, 1):
        while True:
            out('  ' + rgb('violet') + SYM['tl'] + '─' + RESET + ' ' + c('pink', f'{no:02d}', True) + '  ' +
                c('fg', title, True))
            LIVE.start(no, total, title)
            t0 = time.monotonic()
            log(f'━━ {no}/{total} {title}')
            try:
                fn()
                LIVE.stop()
                out('  ' + rgb('violet') + SYM['bl'] + '─' + RESET + ' ' + c('green', SYM['ok'] + ' listo', True) +
                    '  ' + c('dim', fmt_time(time.monotonic() - t0)))
                STATE['steps'].append((title, True))
                break
            except Aborted:
                LIVE.stop()
                raise
            except Exception as e:   # noqa: BLE001
                LIVE.stop()
                log(f'  !! {type(e).__name__}: {e}')
                out('  ' + rgb('violet') + SYM['bl'] + '─' + RESET + ' ' + c('red', SYM['fail'] + ' falló', True))
                error_card(title, e)
                if not required:
                    STATE['steps'].append((title, False))
                    STATE['warnings'].append(f'{title}: {e}')
                    break
                act = choose('¿Qué hacemos?', [('retry', 'Reintentar este paso'), ('skip', 'Saltarlo y seguir'),
                                               ('abort', 'Parar la instalación')], 0)
                if act == 'retry':
                    continue
                if act == 'skip':
                    STATE['steps'].append((title, False))
                    STATE['warnings'].append(f'{title}: saltado ({e})')
                    break
                raise Aborted(str(e))


def error_card(title, e):
    errs = STATE['errors'][-6:]
    STATE['errors'] = []
    if not errs:
        try:
            errs = [ln.strip() for ln in open(LOG).read().splitlines()[-10:] if ln.strip()][-6:]
        except OSError:
            pass
    lines = [c('red', str(e), True), ''] + [c('dim', ln[:110]) for ln in errs]
    blob = ' '.join(errs + [str(e)]).lower()
    hint = next((h for pat, h in HINTS if re.search(pat, blob)), '')
    if hint:
        import textwrap
        wrapped = textwrap.wrap(hint, max(30, min(cols() - 16, 96)))
        lines += [''] + [(c('yellow', SYM['arrow'] + ' ', True) if i == 0 else '  ') + c('fg', w_)
                         for i, w_ in enumerate(wrapped)]
    lines += ['', c('fg', 'Registro completo: ') + c('cyan', LOG)]
    box(lines, stops=('red', 'pink'), title='Algo falló en: ' + title)


def summary(t0):
    out()
    rule()
    n_ok = sum(1 for _t, good in STATE['steps'] if good)
    clean = n_ok == len(STATE['steps']) and not STATE['failed_required']
    title = 'INSTALACIÓN COMPLETADA' if clean else 'INSTALACIÓN TERMINADA CON AVISOS'
    K = lambda k: c('dim', k.ljust(16))   # noqa: E731
    right = [paint(title, ['cyan', 'violet', 'pink'], bold=True), '',
             K('Tiempo') + c('fg', fmt_time(time.monotonic() - t0)),
             ] + ([K('Paquetes') + c('fg', f"{STATE['installed']} instalados o actualizados")] if STATE['installed'] else [])
    if STATE.get('doctor'):
        g, n = STATE['doctor']
        right.append(K('Comprobaciones') + c('green' if g == n else 'yellow', f'{g}/{n} correctas'))
    if STATE.get('backup'):
        right.append(K('Respaldo') + c('fg', '~/' + os.path.relpath(STATE['backup'], HOME)))
    right.append(K('Registro') + c('fg', '~/' + os.path.relpath(LOG, HOME)))
    opt = list(dict.fromkeys(STATE['failed_optional']))
    req = list(dict.fromkeys(STATE['failed_required']))
    if opt:
        right.append(c('yellow', 'Sin instalar    ') + c('fg', ', '.join(opt)))
    if req:
        right.append(c('red', 'Faltan          ') + c('fg', ', '.join(req)))
    if STATE.get('startx'):
        right += ['', c('pink', SYM['arrow'] + ' ', True) + c('fg', 'Reinicia, entra con tu usuario y escribe ') +
                  c('violet', 'startx', True)]
    else:
        right += ['', c('pink', SYM['arrow'] + ' ', True) + c('fg', 'Reinicia y entra en la sesión ') +
                  c('violet', 'BSPWM', True)]
    out()
    top = max(0, (len(SKULL) - len(right)) // 2)
    width = cols()
    side = width >= vlen(SKULL[0]) + 70
    rows = max(len(SKULL), top + len(right)) if side else len(right)

    def frame(eyes):
        lines = []
        for i in range(rows):
            left = skull_line(i, eyes) if side and i < len(SKULL) else (' ' * vlen(SKULL[0]) if side else '')
            j = i - top if side else i
            r = right[j] if 0 <= j < len(right) else ''
            lines.append('  ' + left + ('    ' if side else '') + r)
        return lines

    for l_ in frame(1.0):
        out(vcut(l_, width - 1))
    if side and TRUECOLOR and TTY_OUT:      # a wink at the end
        for e in (0.2, 1.0, 0.2, 1.0):
            time.sleep(0.12)
            sys.stdout.write(f'\033[{rows}A')
            for l_ in frame(e):
                sys.stdout.write('\r\033[2K' + vcut(l_, width - 1) + '\n')
            sys.stdout.flush()
    out()
    keys = [('super + enter', 'terminal'), ('super + space', 'lanzador de apps'),
            ('super + r', 'editor del rice: temas, fondos, barra, animaciones'),
            ('super + alt + m', 'módulos de la barra'), ('alt + space', 'cambiar de tema'),
            ('super + alt + x / c', 'contraseñas / portapapeles'), ('alt + F1', 'todos los atajos')]
    box([c('cyan', k.ljust(22)) + c('fg', d) for k, d in keys], stops=('cyan', 'violet'), title='Para empezar')
    if STATE['warnings']:
        out()
        out('  ' + c('yellow', 'Avisos', True))
        for w in dict.fromkeys(STATE['warnings']):
            out('   ' + c('yellow', SYM['warn']) + ' ' + c('dim', w))
    out()


def plan_menu():
    """What to install: the essentials always, the rest to choose."""
    global CHOICE
    hw = STATE['hw']
    for g in GROUPS:
        if g['key'] == 'bluetooth':
            g['on'] = hw['bluetooth']
            g['desc'] = 'bluez · adaptador detectado' if hw['bluetooth'] else 'bluez · no se detectó adaptador'
    items = [dict(key='core', label='El rice completo', desc='bspwm, barra, ventanas del tema, terminal, zsh',
                  on=True, locked=True)]
    items += [dict(key=g['key'], label=g['label'], desc=g['desc'], on=g['on']) for g in GROUPS]
    if os.path.exists(os.path.join(HOME, '.config/bspwm/.rice')):
        items.insert(1, dict(key='keep', label='Conservar mis ajustes del rice',
                             desc='tema, fondos por tema, avatar, dock y barra actuales', on=True))
    CHOICE = checklist('¿Qué instalamos?', items)
    dm = active_dm()
    if CHOICE.get('login') and dm and dm != 'lightdm.service' and not ARGS.demo:
        CHOICE['replace_dm'] = ask_yes(f'Tienes {dm.replace(".service", "")} como pantalla de inicio. '
                                       '¿Cambiarla por la de TechOGR?', True)


CHOICE = {}


def system_card():
    hw = STATE['hw']
    osname = 'Arch Linux'
    try:
        osname = re.search(r'^PRETTY_NAME="?([^"\n]+)', open('/etc/os-release').read(), re.M).group(1)
    except (OSError, AttributeError):
        pass
    try:
        mem = int(re.search(r'MemTotal:\s+(\d+)', open('/proc/meminfo').read()).group(1)) / 2 ** 20
    except (OSError, AttributeError):
        mem = 0
    gpu = ', '.join(sorted(set(hw['gpus']))) or '?'
    kind = 'máquina virtual ' + hw['virt'] if hw['virt'] != 'none' else 'equipo físico'
    extras = [n for n, on in (('batería', hw['battery']), ('wifi', hw['wifi']), ('bluetooth', hw['bluetooth']),
                              ('touchpad', hw['touchpad'])) if on]
    rows = [('Sistema', osname), ('Equipo', kind), ('CPU', (hw['cpu'] or '?').upper() + f'  {SYM["sep"]}  '
                                                    f'{os.cpu_count()} hilos  {SYM["sep"]}  {mem:.1f} GiB RAM'),
            ('Gráficos', gpu), ('Extras', ', '.join(extras) or 'ninguno'), ('Usuario', f'{USER}  (uid {UID})')]
    box([c('dim', k.ljust(10)) + c('fg', v) for k, v in rows], stops=('violet', 'pink'), title='Tu equipo')


def main():
    t0 = time.monotonic()
    banner(animate=not ARGS.no_anim, sub='modo demostración: no se toca nada' if ARGS.demo else '')
    if ARGS.doctor:
        rule('Comprobación del rice')
        out()
        sys.stdout.write('   ' + c('dim', 'comprobando programas, fuentes, Python y los scripts del rice…'))
        sys.stdout.flush()
        checks = doctor()
        sys.stdout.write('\r\033[2K' if TTY_OUT else '\n')
        good_ones = [n for n, g_, _h in checks if g_]
        short = [n for n in good_ones if len(n) <= 16]
        cw = max(map(len, short)) + 5 if short else 20
        per = max(1, min(6, (cols() - 4) // cw))
        cell = lambda n: c('green', SYM['ok']) + ' ' + c('fg', n) + ' ' * (cw - 2 - len(n))   # noqa: E731
        for i in range(0, len(short), per):
            out('   ' + ''.join(cell(n) for n in short[i:i + per]))
        for n in good_ones:
            if n not in short:
                out('   ' + c('green', SYM['ok']) + ' ' + c('fg', n))
        for name, good, hint in checks:
            if not good:
                out('   ' + c('red', SYM['fail'], True) + ' ' + c('fg', name, True) + '  ' + c('dim', hint))
        g = sum(1 for x in checks if x[1])
        out()
        out('   ' + c('green' if g == len(checks) else 'yellow', f'{g}/{len(checks)} correctas', True))
        out()
        return 0 if g == len(checks) else 1
    STATE['hw'] = detect_hardware()
    system_card()
    out()
    if ARGS.deploy_only:
        CHOICE.update(keep=True)
        steps = [('Respaldo de tu configuración', step_backup, True),
                 ('Copiando el rice', step_deploy, True),
                 ('Comprobación final', step_verify, False)]
    else:
        plan_menu()
        out()
        steps = [('Comprobando el equipo', step_checks, True),
                 ('Permiso de administrador', sudo_auth, True),
                 ('Actualizando el sistema', step_sync, True),
                 ('Ayudante de AUR', step_aur_helper, False),
                 ('Drivers y firmware', step_drivers, False),
                 ('Paquetes del rice', step_packages, True),
                 ('Paquetes de AUR', step_aur, False),
                 ('Respaldo de tu configuración', step_backup, True),
                 ('Copiando el rice', step_deploy, True),
                 ('Sistema: sesión, login, servicios, shell', step_system, False),
                 ('Comprobación final', step_verify, False)]
    rule('Instalación')
    out()
    run_steps(steps)
    summary(t0)
    if not ARGS.deploy_only and not ARGS.demo and sys.stdin.isatty() and not ARGS.yes:  # noqa
        if ask_yes('¿Reiniciar ahora para entrar en BSPWM?', False):
            subprocess.run(['systemctl', 'reboot'])
    return 0


def on_signal(*_):
    p = CHILD.get('proc')
    if p and p.poll() is None:
        try:
            os.killpg(p.pid, signal.SIGINT)
        except OSError:
            pass
    raise KeyboardInterrupt


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='TechOGR BSPWM installer')
    ap.add_argument('--yes', '-y', action='store_true', help='sin preguntas: las opciones recomendadas')
    ap.add_argument('--deploy-only', action='store_true', help='solo copiar el rice (sin paquetes)')
    ap.add_argument('--doctor', action='store_true', help='solo comprobar que todo está en su sitio')
    ap.add_argument('--demo', action='store_true', help='simulación, para ver el instalador')
    ap.add_argument('--no-anim', action='store_true', help='sin animación en el logo')
    ARGS = ap.parse_args()
    signal.signal(signal.SIGTERM, on_signal)
    try:
        rc = main()
    except KeyboardInterrupt:
        p = CHILD.get('proc')
        if p and p.poll() is None:      # pacman / yay stop too
            try:
                os.killpg(p.pid, signal.SIGINT)
                p.wait(timeout=15)
            except (OSError, subprocess.TimeoutExpired):
                pass
        LIVE.stop()
        out()
        out('  ' + c('yellow', SYM['warn'] + ' Instalación cancelada.', True) + ' ' + c('dim', 'Registro: ' + LOG))
        rc = 130
    except Aborted as e:
        LIVE.stop()
        out()
        box([c('red', str(e), True), '', c('dim', 'Registro: ') + c('cyan', LOG)], stops=('red', 'pink'),
            title='Instalación detenida')
        rc = 1
    finally:
        cursor(True)
        log(f'=== end rc={locals().get("rc")}')
    sys.exit(rc)
