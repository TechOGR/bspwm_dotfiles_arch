# =============================================================
# Author:  TechOGR
# Repo:    https://github.com/TechOGR/bspwm_dotfiles_arch
#
# ricespectrum - the REAL spectrum of what is playing (any app: browser,
# Spotify, mpv, MPD...). It listens to the default output's monitor
# (parec @DEFAULT_MONITOR@), FFT with numpy, log-spaced bands, auto gain,
# fast rise / slow fall and falling peaks. Drawn in several styles, each
# theme with its own by default:
#   bars · mirror · wave · radial · dots · blocks · terrain
#
#   an = Analyzer(bands=48); an.start()
#   levels, peaks, wave = an.frame()      # 0..1 each
#   draw(cr, 'bars', x, y, w, h, an, colors, t)
#
# Copyright (C) 2021-2026 TechOGR <https://github.com/TechOGR>
# Licensed under GPL-3.0 license
# =============================================================

import math
import subprocess
import threading
import time

import cairo

try:
    import numpy as np
except ImportError:   # no numpy: a quiet analyzer (the styles still draw)
    np = None

RATE = 44100
FFT = 2048
HOP = 735            # 60 reads a second

STYLES = ['bars', 'mirror', 'wave', 'radial', 'dots', 'blocks', 'terrain']
STYLE_NAMES = {'bars': ('Bars', 'Barras'), 'mirror': ('Mirror', 'Espejo'), 'wave': ('Wave', 'Onda'),
               'radial': ('Radial', 'Radial'), 'dots': ('LEDs', 'LEDs'), 'blocks': ('Blocks', 'Bloques'),
               'terrain': ('Terrain', 'Relieve')}
# each theme's own spectrum
THEME_STYLE = {'pixel': 'blocks', 'cyber': 'dots', 'hud': 'dots', 'neon': 'bars', 'glass': 'mirror',
               'crystal': 'mirror', 'liquid': 'terrain', 'nature': 'terrain', 'holo': 'radial',
               'storm': 'wave', 'venom': 'mirror', 'lava': 'terrain', 'fire': 'bars', 'sketch': 'wave',
               'butterfly': 'radial', 'snake': 'wave', 'minimal': 'bars'}


class Analyzer:
    """parec -> numpy FFT on a thread; frame() is cheap and thread-safe."""

    def __init__(self, bands=48, fmin=35.0, fmax=16000.0, device='@DEFAULT_MONITOR@'):
        self.device = device
        self.n = bands
        self.lock = threading.Lock()
        self.levels = [0.0] * bands
        self.peaks = [0.0] * bands
        self.peak_t = [0.0] * bands
        self.wave = [0.0] * 128
        self.alive = False
        self.proc = None
        self.gain = 1e-3
        self.last = 0.0
        if np is not None:
            freqs = np.fft.rfftfreq(FFT, 1 / RATE)
            edges = np.geomspace(fmin, fmax, bands + 1)
            # each band: its FFT bins (at least one)
            self.bins = []
            for i in range(bands):
                idx = np.where((freqs >= edges[i]) & (freqs < edges[i + 1]))[0]
                if len(idx) == 0:
                    idx = np.array([int(np.argmin(np.abs(freqs - (edges[i] + edges[i + 1]) / 2)))])
                self.bins.append(idx)
            self.win = np.hanning(FFT).astype(np.float32)
            # a gentle tilt: highs have less energy, show them anyway
            self.tilt = np.linspace(0.8, 1.9, bands)

    def start(self):
        if self.alive or np is None:
            return self
        self.alive = True
        threading.Thread(target=self._run, daemon=True).start()
        return self

    def stop(self):
        self.alive = False
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()

    def _run(self):
        buf = np.zeros(FFT, dtype=np.float32)
        while self.alive:
            try:
                self.proc = subprocess.Popen(
                    ['parec', '-d', self.device, '--raw', '--format=float32le', f'--rate={RATE}',
                     '--channels=1', '--latency-msec=25', '--client-name=Rice spectrum',
                     '--stream-name=spectrum'],
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
            except OSError:
                return
            out = self.proc.stdout
            need = HOP * 4
            pend = b''
            while self.alive:
                data = out.read(need - len(pend))     # a pipe gives partial reads: gather a block
                if not data:
                    break
                pend += data
                if len(pend) < need:
                    continue
                chunk = np.frombuffer(pend, dtype=np.float32)
                pend = b''
                buf = np.roll(buf, -len(chunk))
                buf[-len(chunk):] = chunk
                self._analyze(buf)
            if self.proc.poll() is None:
                self.proc.terminate()
            if self.alive:
                time.sleep(1.0)       # the output changed / pipewire restarted: listen again

    def _analyze(self, buf):
        mag = np.abs(np.fft.rfft(buf * self.win))
        raw = np.array([mag[b].max() for b in self.bins]) * self.tilt
        # auto gain: follows the loud parts fast, quiet ones slowly
        top = float(raw.max())
        self.gain = max(top, self.gain * 0.995, 1e-3)
        vals = np.clip(np.sqrt(raw / self.gain), 0, 1)
        silent = top < 0.02
        now = time.monotonic()
        wave = buf[-512::4]
        wmax = float(np.abs(wave).max()) or 1.0
        with self.lock:
            for i, v in enumerate(vals):
                v = 0.0 if silent else float(v)
                cur = self.levels[i]
                self.levels[i] = v if v > cur else cur * 0.86 + v * 0.14       # fast up, slow down
                if self.levels[i] >= self.peaks[i]:
                    self.peaks[i], self.peak_t[i] = self.levels[i], now
                elif now - self.peak_t[i] > 0.25:
                    self.peaks[i] = max(self.levels[i], self.peaks[i] - 0.018)
            self.wave = [0.0] * 128 if silent else [float(x) / max(wmax, 0.25) for x in wave]
            self.last = now

    def frame(self):
        with self.lock:
            stale = time.monotonic() - self.last > 0.3      # nothing coming: fall down
            if stale:
                self.levels = [v * 0.9 for v in self.levels]
                self.peaks = [max(0.0, p - 0.02) for p in self.peaks]
                self.wave = [w * 0.8 for w in self.wave]
            return list(self.levels), list(self.peaks), list(self.wave)

    def active(self):
        return any(v > 0.02 for v in self.levels)


# ═══════════════════════════════════════════════════════════ drawing
def _grad(cr, x0, y0, x1, y1, cols, a=1.0):
    g = cairo.LinearGradient(x0, y0, x1, y1)
    n = len(cols) - 1
    for i, c in enumerate(cols):
        g.add_color_stop_rgba(i / max(1, n), *c, a)
    return g


def _col(cols, t):
    t = max(0.0, min(1.0, t))
    n = len(cols) - 1
    i = min(int(t * n), n - 1) if n else 0
    if not n:
        return cols[0]
    u = t * n - i
    a, b = cols[i], cols[i + 1]
    return tuple(a[k] + (b[k] - a[k]) * u for k in range(3))


def _rr(cr, x, y, w, h, r):
    r = max(0.0, min(r, w / 2, h / 2))
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi)
    cr.close_path()


def resample(vals, n):
    if len(vals) == n or not vals:
        return list(vals)
    out = []
    for i in range(n):
        f = i * (len(vals) - 1) / max(1, n - 1)
        a = int(f)
        b = min(a + 1, len(vals) - 1)
        out.append(vals[a] + (vals[b] - vals[a]) * (f - a))
    return out


def draw(cr, style, x, y, w, h, an, cols, t=0.0, bands=None, glow=True, center=None, radius=None):
    """cols: 2-4 rgb tuples (low -> high). center/radius for 'radial'."""
    levels, peaks, wave = an.frame() if an else ([0.0] * 48, [0.0] * 48, [0.0] * 128)
    if bands:
        levels, peaks = resample(levels, bands), resample(peaks, bands)
    fn = {'bars': _bars, 'mirror': _mirror, 'wave': _wave, 'radial': _radial, 'dots': _dots,
          'blocks': _blocks, 'terrain': _terrain}.get(style, _bars)
    cr.save()
    if style == 'radial':
        fn(cr, x, y, w, h, levels, peaks, wave, cols, t, glow, center, radius)
    else:
        fn(cr, x, y, w, h, levels, peaks, wave, cols, t, glow)
    cr.restore()


def _bars(cr, x, y, w, h, lv, pk, _wv, cols, _t, glow):
    n = len(lv)
    step = w / n
    bw = max(1.5, step * 0.62)
    if glow:
        cr.set_source(_grad(cr, x, 0, x + w, 0, cols, 0.18))
        for i, v in enumerate(lv):
            bh = max(2, v * h)
            _rr(cr, x + i * step + (step - bw) / 2 - 1.5, y + h - bh - 1.5, bw + 3, bh + 3, bw / 2 + 1.5)
        cr.fill()
    cr.set_source(_grad(cr, x, 0, x + w, 0, cols))
    for i, v in enumerate(lv):
        bh = max(2, v * h)
        _rr(cr, x + i * step + (step - bw) / 2, y + h - bh, bw, bh, bw / 2)
    cr.fill()
    for i, p in enumerate(pk):    # falling peaks
        if p > 0.03:
            cr.set_source_rgba(*_col(cols, i / max(1, n - 1)), 0.9)
            cr.rectangle(x + i * step + (step - bw) / 2, y + h - p * h - 3, bw, 2)
            cr.fill()


def _mirror(cr, x, y, w, h, lv, _pk, _wv, cols, _t, glow):
    n = len(lv)
    step = w / n
    bw = max(1.5, step * 0.55)
    cy = y + h / 2
    for a, pad in ((0.16, 2.0), (1.0, 0.0)) if glow else ((1.0, 0.0),):
        cr.set_source(_grad(cr, x, 0, x + w, 0, cols, a))
        for i, v in enumerate(lv):
            half = max(1.0, v * h / 2)
            _rr(cr, x + i * step + (step - bw) / 2 - pad, cy - half - pad, bw + 2 * pad, 2 * half + 2 * pad,
                bw / 2 + pad)
        cr.fill()
    cr.set_source_rgba(1, 1, 1, 0.25)   # the center line
    cr.rectangle(x, cy - 0.5, w, 1)
    cr.fill()


def _smooth(cr, pts):
    cr.move_to(*pts[0])
    for i in range(1, len(pts) - 1):
        mx, my = (pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2
        cr.curve_to(pts[i][0], pts[i][1], pts[i][0], pts[i][1], mx, my)
    cr.line_to(*pts[-1])


def _wave(cr, x, y, w, h, lv, _pk, wv, cols, t, glow):
    cy = y + h / 2
    n = len(wv)
    energy = sum(lv) / max(1, len(lv))
    pts = [(x + i * w / (n - 1), cy + wv[i] * h * 0.42 * min(1.0, 0.35 + energy * 1.6)) for i in range(n)]
    for lw, a in ((7, 0.12), (4, 0.25), (2, 1.0)) if glow else ((2, 1.0),):
        _smooth(cr, pts)
        cr.set_source(_grad(cr, x, 0, x + w, 0, cols, a))
        cr.set_line_width(lw)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.stroke()


def _radial(cr, x, y, w, h, lv, pk, _wv, cols, t, glow, center=None, radius=None):
    cx, cy = center or (x + w / 2, y + h / 2)
    r0 = radius or min(w, h) * 0.28
    reach = min(w, h) / 2 - r0 - 2
    n = len(lv)
    rot = t * 0.15
    for i in range(n * 2):       # both halves: symmetric
        v = lv[i % n] if i < n else lv[n - 1 - (i - n)]
        a = rot + i / (n * 2) * 2 * math.pi
        l = 2 + v * reach
        c = _col(cols, (i % n) / max(1, n - 1) if i < n else (n - 1 - (i - n)) / max(1, n - 1))
        x0, y0 = cx + math.cos(a) * r0, cy + math.sin(a) * r0
        x1, y1 = cx + math.cos(a) * (r0 + l), cy + math.sin(a) * (r0 + l)
        if glow:
            cr.set_source_rgba(*c, 0.18)
            cr.set_line_width(max(2.5, 2 * math.pi * r0 / (n * 2) * 0.9))
            cr.move_to(x0, y0)
            cr.line_to(x1, y1)
            cr.stroke()
        cr.set_source_rgba(*c, 0.95)
        cr.set_line_width(max(1.5, 2 * math.pi * r0 / (n * 2) * 0.5))
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.move_to(x0, y0)
        cr.line_to(x1, y1)
        cr.stroke()
    cr.arc(cx, cy, r0 - 1, 0, 2 * math.pi)
    cr.set_source_rgba(*cols[-1], 0.35)
    cr.set_line_width(1.2)
    cr.stroke()


def _dots(cr, x, y, w, h, lv, pk, _wv, cols, _t, glow):
    n = len(lv)
    step = w / n
    rows = max(4, int(h / max(4.0, step * 0.9)))
    dy = h / rows
    rad = max(1.0, min(step, dy) * 0.32)
    for i, v in enumerate(lv):
        lit = int(round(v * rows))
        px = x + i * step + step / 2
        for k in range(rows):
            py = y + h - (k + 0.5) * dy
            c = _col(cols, k / max(1, rows - 1))       # green -> yellow -> red like a VU
            on = k < lit
            if on and glow:
                cr.arc(px, py, rad * 2.1, 0, 2 * math.pi)
                cr.set_source_rgba(*c, 0.14)
                cr.fill()
            cr.arc(px, py, rad, 0, 2 * math.pi)
            cr.set_source_rgba(*c, 0.95 if on else 0.08)
            cr.fill()
        pr = int(round(pk[i] * rows))
        if 0 < pr <= rows:
            cr.arc(px, y + h - (pr - 0.5) * dy, rad, 0, 2 * math.pi)
            cr.set_source_rgba(1, 1, 1, 0.8)
            cr.fill()


def _blocks(cr, x, y, w, h, lv, pk, _wv, cols, _t, _glow):
    n = len(lv)
    step = w / n
    q = max(3.0, round(min(step, h / 10) * 0.82))
    rows = int(h // (q + 1))
    for i, v in enumerate(lv):
        lit = int(v * rows + 0.5)
        bx = round(x + i * step + (step - q) / 2)
        for k in range(rows):
            by = round(y + h - (k + 1) * (q + 1))
            c = _col(cols, k / max(1, rows - 1))
            cr.rectangle(bx, by, q, q)
            cr.set_source_rgba(*c, 1.0 if k < lit else 0.07)
            cr.fill()
        pr = int(pk[i] * rows + 0.5)
        if 0 < pr <= rows:
            cr.rectangle(bx, round(y + h - pr * (q + 1)), q, max(1, q // 3))
            cr.set_source_rgba(1, 1, 1, 0.9)
            cr.fill()


def _terrain(cr, x, y, w, h, lv, _pk, _wv, cols, t, glow):
    n = len(lv)
    pts = [(x + i * w / (n - 1), y + h - max(0.02, v) * h * 0.95) for i, v in enumerate(lv)]
    _smooth(cr, pts)
    cr.line_to(x + w, y + h)
    cr.line_to(x, y + h)
    cr.close_path()
    g = cairo.LinearGradient(0, y, 0, y + h)
    g.add_color_stop_rgba(0, *cols[-1], 0.75)
    g.add_color_stop_rgba(0.6, *cols[len(cols) // 2], 0.35)
    g.add_color_stop_rgba(1, *cols[0], 0.05)
    cr.set_source(g)
    cr.fill()
    for lw, a in ((6, 0.15), (2, 1.0)) if glow else ((2, 1.0),):
        _smooth(cr, pts)
        cr.set_source(_grad(cr, x, 0, x + w, 0, cols, a))
        cr.set_line_width(lw)
        cr.stroke()
