#!/bin/sh

# ScreenLocker reads its colors/options straight from theme-config.bash.
# betterlockscreen (the login lock) is themed by BetterLock from the BL_*
# options: it writes ~/.config/betterlockscreen/betterlockscreenrc, renders
# the login card with the avatar and (re)starts the auto-lock (xss-lock).

BL="$HOME/.config/bspwm/bin/BetterLock"
"$BL" --config >/dev/null 2>&1
"$BL" --idle >/dev/null 2>&1

(sleep 3; ScreenLocker --prepare; nice -n 19 "$BL" --prepare) >/dev/null 2>&1 &
