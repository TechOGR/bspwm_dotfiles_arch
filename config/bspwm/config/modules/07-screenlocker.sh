#!/bin/sh

# ScreenLocker reads its colors/options straight from theme-config.bash,
# so here we only keep betterlockscreen themed the same way and warm up
# the lock image cache for the current wallpaper.

mkdir -p "$HOME/.config/betterlockscreen"
_write "$HOME/.config/betterlockscreen/betterlockscreenrc" << EOF
# Generated for the ${RICE} theme by ~/.config/bspwm/config/modules/07-screenlocker.sh

fx_list=(dim)
dim_level=${LOCK_DIM:-20}
blur_level=1
quiet=true
span_image=false
wallpaper_cmd="feh --bg-fill"

loginbox=${bg#\#}99
loginshadow=00000000
locktext="${LOCK_GREETER:-Type the password to Unlock}"
font="JetBrainsMono NF"
ringcolor=${sl_ring#\#}ff
insidecolor=${sl_bg#\#}cc
separatorcolor=00000000
ringvercolor=${sl_verify#\#}ff
insidevercolor=${sl_bg#\#}cc
ringwrongcolor=${sl_wrong#\#}ff
insidewrongcolor=${sl_wrong#\#}ff
timecolor=${sl_date#\#}ff
time_format="${LOCK_CLOCK:-%H:%M}"
greetercolor=${sl_fg#\#}ff
layoutcolor=${sl_fg#\#}ff
keyhlcolor=${blue#\#}ff
bshlcolor=${sl_wrong#\#}ff
verifcolor=${sl_verify#\#}ff
wrongcolor=${sl_wrong#\#}ff
modifcolor=${sl_wrong#\#}ff
bgcolor=${bg#\#}ff
EOF

(sleep 3; ScreenLocker --prepare) >/dev/null 2>&1 &
