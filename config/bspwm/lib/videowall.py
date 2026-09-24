# =============================================================
# Author:  TechOGR
# Repo:    https://github.com/TechOGR/bspwm_dotfiles_arch
#
# videowall - shared bits of the video wallpaper (VideoWall, RiceEditor,
#   BetterLock): the videos folder of the rice (walls/videos), frames and
#   thumbnails made with ffmpeg, the VIDEO_* options and the mpv filters
#   used by the lock screen. No GTK here.
#
# Copyright (C) 2021-2026 TechOGR <https://github.com/TechOGR>
# Licensed under GPL-3.0 license
# =============================================================

import os
import re
import glob
import hashlib
import subprocess

HOME = os.path.expanduser('~')
BSPWM = os.path.join(HOME, '.config/bspwm')
CACHE = os.path.join(os.environ.get('XDG_CACHE_HOME', os.path.join(HOME, '.cache')), 'videowall')
RUNTIME = os.environ.get('XDG_RUNTIME_DIR') or f'/tmp/videowall-{os.getuid()}'
VIDEO_EXT = ('.mp4', '.mkv', '.webm', '.mov', '.avi', '.gif')

OPTIONS = {
    'ENGINE': 'Default',
    'ANIMATED_WALL': '',
    'VIDEO_PAUSE': 'windows',    # never | windows | fullscreen
    'VIDEO_FIT': 'fill',         # fill | fit | stretch
    'VIDEO_SPEED': '1.0',        # 0.25 - 2.0
}


def rice():
    try:
        with open(os.path.join(BSPWM, '.rice')) as f:
            return f.read().strip()
    except OSError:
        return 'crackone'


def theme_cfg():
    return os.path.join(BSPWM, 'rices', rice(), 'theme-config.bash')


def videos_dir():
    """Videos live next to the pictures: rices/<rice>/walls/videos."""
    return os.path.join(BSPWM, 'rices', rice(), 'walls', 'videos')


def is_video(path):
    return bool(path) and path.lower().endswith(VIDEO_EXT)


def list_videos():
    return sorted((p for p in glob.glob(os.path.join(videos_dir(), '*')) if is_video(p)),
                  key=lambda p: os.path.basename(p).lower())


def pretty(path):
    name = os.path.splitext(os.path.basename(path or ''))[0]
    return re.sub(r'[-_]+', ' ', name).strip() or 'video'


def settings():
    """VIDEO_* options as bash sees them."""
    script = ('. "$1" >/dev/null 2>&1; shift; '
              'for v in "$@"; do printf "%s\\t%s\\n" "$v" "${!v}"; done')
    conf = dict(OPTIONS)
    try:
        out = subprocess.run(['bash', '-c', script, '_', theme_cfg(), *OPTIONS],
                             capture_output=True, text=True, timeout=4).stdout
        for line in out.splitlines():
            k, _, v = line.partition('\t')
            if v:
                conf[k] = v
    except Exception:
        pass
    return conf


def current_video():
    """The video wallpaper configured (ANIMATED_WALL), else the first one."""
    v = settings().get('ANIMATED_WALL', '')
    if os.path.isfile(v) and is_video(v):
        return v
    vids = list_videos()
    return vids[0] if vids else ''


def _key(path, extra=''):
    try:
        st = os.stat(path)
        stamp = f'{st.st_mtime}|{st.st_size}'
    except OSError:
        stamp = ''
    return hashlib.md5(f'{path}|{stamp}|{extra}'.encode()).hexdigest()


def frame(path, width=None):
    """A still of the video (1 s in, or the first frame), cached as PNG.
    width: scaled copy (thumbnails). Returns the path or None."""
    if not os.path.isfile(path or ''):
        return None
    os.makedirs(CACHE, exist_ok=True)
    out = os.path.join(CACHE, f'{"thumb" if width else "frame"}-{_key(path, width or "")}.png')
    if os.path.exists(out):
        return out
    vf = ['-vf', f'scale={int(width)}:-2'] if width else []
    tmp = out + '.tmp.png'
    for seek in (['-ss', '1'], []):       # short clips / gifs: first frame
        try:
            subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', *seek, '-i', path, '-frames:v', '1',
                            *vf, tmp], timeout=30, capture_output=True)
        except Exception:
            pass
        if os.path.exists(tmp) and os.path.getsize(tmp):
            os.replace(tmp, out)
            return out
    return None


def thumb(path):
    return frame(path, width=320)


def duration(path):
    try:
        out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of',
                              'default=nw=1:nk=1', path], capture_output=True, text=True, timeout=10).stdout
        return float(out.strip())
    except Exception:
        return 0.0


def lock_filter(fx, dim, blur, pixel):
    """mpv --vf for the lock screen: same effects as the pictures."""
    parts = []
    if 'blur' in fx:
        # blur a small copy: cheap, and mpv scales it back up smoothly
        parts.append(f'scale=trunc(iw/8)*2:-2,gblur=sigma={max(0.5, int(blur) / 4):.1f}')
    if 'pixel' in fx:
        p = max(2, int(pixel))
        parts.append(f'scale=trunc(iw/{p}):-2,scale=iw*{p}:-2:flags=neighbor')
    if fx.startswith('dim') and int(dim):
        k = max(0.0, 1 - int(dim) / 100)
        parts.append(f'colorchannelmixer=rr={k:.2f}:gg={k:.2f}:bb={k:.2f}')
    return f'lavfi=[{",".join(parts)}]' if parts else ''


def compositor():
    """Video under a transparent lock needs a compositor."""
    return subprocess.run(['pgrep', '-u', str(os.getuid()), '-x', 'picom'], capture_output=True).returncode == 0
