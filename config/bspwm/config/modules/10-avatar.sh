#!/bin/sh

# The ASCII avatar (AvatarForge) can use the palette colors: re-render it
# with the new ones. Also rebuilds it after a RiceEditor snapshot restore.
[ -f "$HOME/.config/bspwm/config/avatar.json" ] &&
    "$HOME"/.config/bspwm/bin/AvatarForge --apply >/dev/null 2>&1 &
