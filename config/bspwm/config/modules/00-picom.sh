#!/bin/sh

# The HUD window style glows with the accent color instead of a shadow
[ "${WIN_STYLE}" = "hud" ] && SHADOW_C=${blue}

# Without hardware OpenGL (VMs) blur and animations are repainted on the
# CPU and make everything lag: the "lite" profile drops them here (the
# rules file is generated, theme-config keeps the user's choice) and
# PicomStart moves picom to xrender. Shadows stay: they cost ~1%.
PERF=$("$HOME"/.config/bspwm/bin/PerfProfile)
if [ "$PERF" = lite ]; then
    P_BLUR=false
    P_ANIMATIONS="#"
fi

# Windows in a theme frame (WIN_SKIN): no size / position / scale
# animations, the frame and shape drawn by RoundBorders follow the real
# geometry and would be left behind (picom-animations-framed.conf)
if [ -n "${WIN_SKIN}" ]; then P_ANIM_FILE="picom-animations-framed.conf"; else P_ANIM_FILE="picom-animations.conf"; fi

# ...and picom repaints the whole screen instead of only the damaged
# parts: with the translucent frame overlays its damage tracking left
# stale pixels (a frame's band showing the wallpaper after a restack, the
# frame's top line missing under a bar that had just been redrawn). On
# xrender (Lite) it costs a few % more CPU; quality comes first.
if [ -n "${WIN_SKIN}" ]; then P_DAMAGE=false; else P_DAMAGE=true; fi

sed -i "$HOME/.config/bspwm/config/picom/picom.conf" \
    -e "s/shadow-color = .*/shadow-color = \"${SHADOW_C}\"/" \
    -e "s/^corner-radius = .*/corner-radius = ${P_CORNER_R}/" \
    -e "s/^use-damage = .*/use-damage = ${P_DAMAGE};/"

# Terminals over the theme's background keep one opacity (no focus pulse)
if [ "${WIN_BACKDROP:-false}" = "true" ]; then P_TERM_LOCK=""; else P_TERM_LOCK="#"; fi

sed -i "$HOME/.config/bspwm/config/picom/picom-rules.conf" \
    -e "/#-term-opacity-lock/s/.*#-/\t\t${P_TERM_LOCK}opacity = 1;\t#-/" \
    -e "/#-shadow-switch/s/.*#-/\t\tshadow = ${P_SHADOWS};\t#-/" \
    -e "/#-fade-switch/s/.*#-/\t\tfade = ${P_FADE};\t#-/" \
    -e "/#-blur-switch/s/.*#-/\t\tblur-background = ${P_BLUR};\t#-/" \
    -e "/picom-animations/c\\        ${P_ANIMATIONS}include \"${P_ANIM_FILE}\"" \
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
