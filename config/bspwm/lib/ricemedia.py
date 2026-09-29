# =============================================================
# Author:  TechOGR
# Repo:    https://github.com/TechOGR/bspwm_dotfiles_arch
#
# ricemedia - what is playing, from where, and its controls. Shared by the
# music widget (bin/MusicPlayer) and the full player (bin/RiceMusic).
#   ✔ Every MPRIS player (browsers, Spotify, mpv, VLC...) via playerctl, and MPD via mpc
#   ✔ Where the music comes from: YouTube, YouTube Music (also its installed
#     app), Spotify, SoundCloud, Deezer, Twitch, Tidal... inside a browser
#   ✔ The active one: the one playing (the last that played when none does)
#   ✔ Cover art: MPRIS artUrl (file / http, cached) or the MPD file's own
#
# Copyright (C) 2021-2026 TechOGR <https://github.com/TechOGR>
# Licensed under GPL-3.0 license
# =============================================================

import hashlib
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request

HOME = os.path.expanduser('~')
CACHE = os.path.join(HOME, '.cache', os.environ.get('USER', 'user'), 'musicplayer')
SEP = '\x1f'
os.makedirs(CACHE, exist_ok=True)

BROWSERS = {'brave': 'Brave', 'chromium': 'Chromium', 'chrome': 'Chrome', 'firefox': 'Firefox',
            'vivaldi': 'Vivaldi', 'opera': 'Opera', 'edge': 'Edge', 'librewolf': 'LibreWolf', 'zen': 'Zen'}
APPS = {'mpd': ('\U000f075a', 'MPD'), 'spotify': ('\U000f04c7', 'Spotify'), 'mpv': ('\U000f040a', 'mpv'),
        'vlc': ('\U000f057c', 'VLC'), 'audacious': ('\U000f075a', 'Audacious'),
        'strawberry': ('\U000f075a', 'Strawberry'), 'rhythmbox': ('\U000f075a', 'Rhythmbox'),
        'elisa': ('\U000f075a', 'Elisa'), 'kdeconnect': ('\U000f0322', 'Phone')}
# a site inside a browser: (pattern in the window title, glyph, name)
SITES = [(r'youtube music', '\U000f0386', 'YouTube Music'), (r'youtube', '\U000f05c3', 'YouTube'),
         (r'spotify', '\U000f04c7', 'Spotify'), (r'soundcloud', '\U000f04c0', 'SoundCloud'),
         (r'deezer', '\U000f075a', 'Deezer'), (r'twitch', '\U000f0543', 'Twitch'), (r'tidal', '\U000f075a', 'Tidal'),
         (r'apple music', '\U000f075a', 'Apple Music'), (r'bandcamp', '\U000f075a', 'Bandcamp'),
         (r'netflix', '\U000f0746', 'Netflix'), (r'twitter|x\.com', '\U000f0544', 'X'),
         (r'tiktok', '\U000f075a', 'TikTok'), (r'kick', '\U000f075a', 'Kick')]
YTM_APP = 'cinhimbnkkaeohfgghhklpknlkffjgod'      # YouTube Music installed as an app (PWA)
WEB = '\U000f059f'


def run(cmd, timeout=3):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception:
        return ''


def fmt_time(s):
    s = max(0, int(s))
    return f'{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}' if s >= 3600 else f'{s // 60}:{s % 60:02d}'


def mpd_music_dir():
    try:
        for line in open(os.path.join(HOME, '.config/mpd/mpd.conf')):
            m = re.match(r'\s*music_directory\s+"([^"]+)"', line)
            if m:
                return os.path.expanduser(m.group(1))
    except OSError:
        pass
    return os.path.join(HOME, 'Music')


# ─────────────────────────────────────────────────────── windows (for the site)
_WIN = {'t': 0.0, 'list': []}


def windows():
    """[(class, instance, title)] of the X windows, cached 2 s."""
    if time.monotonic() - _WIN['t'] < 2.0:
        return _WIN['list']
    out = []
    ids = re.findall(r'0x[0-9a-f]+', run(['xprop', '-root', '_NET_CLIENT_LIST']))
    for wid in ids:
        info = run(['xprop', '-id', wid, 'WM_CLASS', '_NET_WM_NAME'], timeout=1)
        cls = re.search(r'WM_CLASS\(STRING\) = "([^"]*)", "([^"]*)"', info)
        name = re.search(r'_NET_WM_NAME\(UTF8_STRING\) = "(.*)"', info)
        if cls:
            out.append((cls.group(2), cls.group(1), name.group(1) if name else ''))
    _WIN.update(t=time.monotonic(), list=out)
    return out


def _site_of(text):
    low = text.lower()
    for pat, glyph, name in SITES:
        if re.search(pat, low):
            return glyph, name
    return None


def source(player, title=''):
    """(glyph, name, app): where it plays. name is the site for a browser."""
    base = player.split('.')[0].lower()
    if base in APPS:
        g, n = APPS[base]
        return g, n, n
    app = BROWSERS.get(base)
    if not app:
        return WEB, base.title(), base.title()
    wins = [w for w in windows() if base in (w[0] + w[1]).lower() or YTM_APP in w[1]]
    t = (title or '').strip().lower()
    # 1. the window showing this very song
    if t:
        for _c, _i, name in wins:
            if t[:40] and t[:40] in name.lower():
                s = _site_of(name)
                if s:
                    return s[0], s[1], app
    # 2. YouTube Music as an installed app
    if any(YTM_APP in w[1] or w[2].strip() == 'YouTube Music' for w in wins):
        return '\U000f0386', 'YouTube Music', app
    # 3. any window of the browser naming a site
    for _c, _i, name in wins:
        s = _site_of(name)
        if s:
            return s[0], s[1], app
    return WEB, app, app


def label(src):
    """'YouTube Music · Brave' / 'Spotify'."""
    glyph, name, app = src
    return name if name == app else f'{name} · {app}'


# ─────────────────────────────────────────────────────── players
class Backend:
    """playerctl for MPRIS players, mpc for MPD."""

    def __init__(self):
        self.caps = {}
        self.last_playing = None

    def supports(self, p, prop):
        """Browsers expose no Shuffle / LoopStatus: ask once per player."""
        key = (p, prop)
        if key not in self.caps:
            try:
                r = subprocess.run(['playerctl', '-p', p, prop], capture_output=True, text=True, timeout=3)
                self.caps[key] = r.returncode == 0 and 'could not' not in r.stdout.lower()
            except Exception:
                self.caps[key] = False
        return self.caps[key]

    @staticmethod
    def players():
        out = [p for p in run(['playerctl', '-l']).splitlines() if p]
        # MPD: whenever it runs with something queued (stopped too: play it from here)
        if not any(p.startswith('mpd') for p in out) and run(['mpc', 'playlist'], timeout=2):
            out.append('mpd')
        return out

    def active(self, players=None, current=None):
        """The player to show: the one playing (the current one first), else
        the last that played, else the current, else the first."""
        players = players if players is not None else self.players()
        if not players:
            return None
        playing = [p for p in players if self.status(p) == 'Playing']
        if current in playing:
            pick = current
        elif playing:
            pick = playing[0]
        elif self.last_playing in players:
            pick = self.last_playing
        elif current in players:
            pick = current
        else:
            pick = players[0]
        if pick in playing:
            self.last_playing = pick
        return pick

    @staticmethod
    def status(p):
        if p == 'mpd':
            out = run(['mpc', 'status'])
            return 'Playing' if '[playing]' in out else 'Paused' if '[paused]' in out else 'Stopped'
        return run(['playerctl', '-p', p, 'status'], timeout=2) or 'Stopped'

    def state(self, p):
        if p == 'mpd':
            st = self.mpd_state()
        else:
            fmt = SEP.join(['{{status}}', '{{title}}', '{{artist}}', '{{album}}', '{{mpris:artUrl}}',
                            '{{position}}', '{{mpris:length}}', '{{volume}}', '{{shuffle}}', '{{loop}}'])
            f = run(['playerctl', '-p', p, 'metadata', '--format', fmt]).split(SEP)
            if len(f) < 10:
                return None

            def num(v, div=1):
                try:
                    return float(v) / div
                except ValueError:
                    return 0.0
            st = dict(status=f[0] or 'Stopped', title=f[1] or '', artist=f[2], album=f[3],
                      art=f[4], position=num(f[5], 1e6), length=num(f[6], 1e6), volume=num(f[7]),
                      shuffle=f[8] == 'true', loop=f[9] if f[9] in ('Track', 'Playlist') else 'None',
                      can_shuffle=self.supports(p, 'shuffle'), can_loop=self.supports(p, 'loop'))
        if st:
            st['source'] = source(p, st.get('title', ''))
        return st

    def mpd_state(self):
        out = run(['mpc', '-f', SEP.join(['%title%', '%artist%', '%album%', '%file%']), 'status'])
        lines = out.splitlines()
        if not lines:
            return None
        st = dict(status='Stopped', title='', artist='', album='', art='', position=0,
                  length=0, volume=0.5, shuffle=False, loop='None', can_shuffle=True, can_loop=True)
        if len(lines) >= 3:
            f = lines[0].split(SEP) + ['', '', '', '']
            st.update(title=f[0] or os.path.basename(f[3]), artist=f[1], album=f[2], art=f'mpd:{f[3]}')
            st['status'] = 'Playing' if '[playing]' in lines[1] else 'Paused'
            try:
                cur, tot = lines[1].split()[2].split('/')

                def secs(t):
                    return sum(int(x) * 60 ** i for i, x in enumerate(reversed(t.split(':'))))
                st['position'], st['length'] = secs(cur), secs(tot)
            except (IndexError, ValueError):
                pass
        opts = lines[-1]
        st['shuffle'] = 'random: on' in opts
        st['loop'] = 'Playlist' if 'repeat: on' in opts else 'None'
        try:
            st['volume'] = int(opts.split('volume:')[1].split('%')[0]) / 100
        except (IndexError, ValueError):
            pass
        return st

    @staticmethod
    def cmd(p, action, arg=None):
        if p == 'mpd':
            m = {'toggle': ['toggle'], 'next': ['next'], 'prev': ['prev'], 'shuffle': ['random'],
                 'loop': ['repeat'], 'seek': ['seek', str(int(arg or 0))], 'stop': ['stop'],
                 'volume': ['volume', str(int((arg or 0) * 100))]}[action]
            subprocess.Popen(['mpc', '-q', *m], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        m = {'toggle': ['play-pause'], 'next': ['next'], 'prev': ['previous'], 'shuffle': ['shuffle', 'Toggle'],
             'loop': ['loop', {'None': 'Playlist', 'Playlist': 'Track'}.get(arg, 'None')], 'stop': ['stop'],
             'seek': ['position', f'{arg or 0:.2f}'], 'volume': ['volume', f'{arg or 0:.2f}']}[action]
        subprocess.Popen(['playerctl', '-p', p, *m], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    @staticmethod
    def art_path(url):
        """Local file for an MPRIS artUrl / an MPD file (cached)."""
        if not url:
            return ''
        if url.startswith('file://'):
            p = urllib.parse.unquote(url[7:])
            return p if os.path.isfile(p) else ''
        key = hashlib.md5(url.encode()).hexdigest()
        out = os.path.join(CACHE, key + '.png')
        if os.path.isfile(out):
            return out
        if url.startswith('mpd:'):
            src = os.path.join(mpd_music_dir(), url[4:])
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'quiet', '-i', src, '-an', '-frames:v', '1', out],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if not os.path.isfile(out):    # no embedded picture: cover.jpg / folder.jpg next to it
                d = os.path.dirname(src)
                for n in ('cover.jpg', 'cover.png', 'folder.jpg', 'folder.png', 'Cover.jpg', 'Folder.jpg'):
                    if os.path.isfile(os.path.join(d, n)):
                        return os.path.join(d, n)
            return out if os.path.isfile(out) else ''
        if url.startswith('http'):
            try:
                with urllib.request.urlopen(url.replace('open.spotify.com', 'i.scdn.co'), timeout=6) as r, \
                        open(out, 'wb') as f:
                    f.write(r.read())
                return out
            except Exception:
                return ''
        return ''
