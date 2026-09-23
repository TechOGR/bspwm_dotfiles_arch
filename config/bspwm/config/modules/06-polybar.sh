#!/bin/sh

# Polybar colors follow the active palette of the rice. config.ini
# includes this file, and Bar.bash (run right after the modules)
# relaunches the bar, so switching palette re-themes the bar too.
_write "$HOME/.config/bspwm/rices/${RICE}/colors.ini" << EOF2
; Generated for the ${RICE} theme by config/modules/06-polybar.sh -- do not edit.
[color]
bg = ${bg}
fg = ${fg}
mb = ${accent_color}

red = ${red}
pink = ${redb}
purple = ${magenta}
blue = ${blue}
blue-arch = ${arch_icon}
cyan = ${cyan}
teal = ${cyanb}
green = ${green}
lime = ${greenb}
yellow = ${yellow}
amber = ${yellowb}
orange = ${yellow}
brown = ${white}
grey = ${white}
indigo = ${magentab}
blue-gray = ${blackb}
trace = ${blackb}
EOF2
