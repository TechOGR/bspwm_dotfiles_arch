#!/bin/sh

# The HUD window style glows with the accent color instead of a shadow
[ "${WIN_STYLE}" = "hud" ] && SHADOW_C=${blue}

# Without hardware OpenGL (VMs) blur and animations are repainted on the
# CPU and make everything lag: the "lite" profile drops them here (the
# rules file is generated, theme-config keeps the user's choice) and
# PicomStart moves picom to xrender with smaller shadows.
if [ "$("$HOME"/.config/bspwm/bin/PerfProfile)" = lite ]; then
    P_BLUR=false
    P_ANIMATIONS="#"
fi

sed -i "$HOME/.config/bspwm/config/picom/picom.conf" \
    -e "s/shadow-color = .*/shadow-color = \"${SHADOW_C}\"/" \
    -e "s/^corner-radius = .*/corner-radius = ${P_CORNER_R}/"

sed -i "$HOME/.config/bspwm/config/picom/picom-rules.conf" \
    -e "/#-shadow-switch/s/.*#-/\t\tshadow = ${P_SHADOWS};\t#-/" \
    -e "/#-fade-switch/s/.*#-/\t\tfade = ${P_FADE};\t#-/" \
    -e "/#-blur-switch/s/.*#-/\t\tblur-background = ${P_BLUR};\t#-/" \
    -e "/picom-animations/c\\        ${P_ANIMATIONS}include \"picom-animations.conf\"" \
    -e "/#-active-opacity/s/.*#-/\t\topacity = ${P_ACTIVE_OPACITY:-0.97};\t#-/" \
    -e "/#-inactive-opacity/s/.*#-/\t\topacity = ${P_INACTIVE_OPACITY:-0.92};\t#-/"

_write "$HOME/.config/bspwm/config/picom/picom-dunst-animations.conf" <<-EOF
    animations = (

        {
            triggers = ["close", "hide"];
            preset = "${dunst_close_preset}";
            direction = "${dunst_close_direction}";
            duration = 0.2;
        },

        {
            triggers = ["open", "show"];
            preset = "${dunst_open_preset}";
            direction = "${dunst_open_direction}";
            duration = 0.2;
        }
    )
EOF
