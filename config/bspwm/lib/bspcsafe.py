# =============================================================
# Author:  TechOGR
# Repo:    https://github.com/TechOGR/bspwm_dotfiles_arch
#
# bspcsafe - no bspc call of a daemon can wait forever.
#
# bspwm writes its events to every `bspc subscribe` synchronously. If a
# daemon stops reading its subscription while it waits for the answer of
# another bspc call, and bspwm is at that moment blocked writing to a full
# subscription, both wait for each other: bspwm freezes, and with it the
# whole desktop (it happened: black screen, nothing answered). Imported by
# the daemons that subscribe to bspwm, this gives every `bspc` run through
# subprocess.run a 2 s limit: a timeout gives an empty answer, the daemon
# goes back to reading its events and bspwm is free again.
#
# Copyright (C) 2021-2026 TechOGR <https://github.com/TechOGR>
# Licensed under GPL-3.0 license
# =============================================================

import subprocess

TIMEOUT = 2.0
_run = subprocess.run


def _safe_run(cmd, *args, **kw):
    if isinstance(cmd, (list, tuple)) and cmd and cmd[0] == 'bspc' and kw.get('timeout') is None:
        kw['timeout'] = TIMEOUT
        try:
            return _run(cmd, *args, **kw)
        except subprocess.TimeoutExpired:
            text = kw.get('text') or kw.get('universal_newlines') or kw.get('encoding')
            empty = '' if text else b''
            return subprocess.CompletedProcess(cmd, 124, empty, empty)
    return _run(cmd, *args, **kw)


if subprocess.run is not _safe_run and getattr(subprocess.run, '__name__', '') != '_safe_run':
    subprocess.run = _safe_run
