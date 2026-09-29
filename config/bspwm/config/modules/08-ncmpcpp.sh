#!/bin/sh
# ncmpcpp in the theme: the visualizer of the theme (or the spectrum style
# chosen in RiceMusic) and its accent. The terminal's colors already follow
# the theme, so the accent is the name of one of them.

cfg="$HOME/.config/ncmpcpp/config"
[ -f "$cfg" ] || return 0 2>/dev/null || exit 0

kit="${RICE_KIT:-${WIN_SKIN:-}}"

# the spectrum style: RiceMusic's choice, else the theme's own (lib/ricespectrum.py)
spec=$(sed -n 's/.*"spectrum": *"\([a-z]*\)".*/\1/p' "$HOME/.config/bspwm/config/music.json" 2>/dev/null)
case "$spec" in bars|mirror|wave|radial|dots|blocks|terrain) ;; *)
    case "$kit" in
        pixel) spec=blocks ;; cyber|hud) spec=dots ;; glass|crystal|venom) spec=mirror ;;
        liquid|nature|lava) spec=terrain ;; holo|butterfly) spec=radial ;;
        storm|sketch|snake) spec=wave ;; *) spec=bars ;;
    esac ;;
esac
case "$spec" in
    dots)    vtype=spectrum; vlook="●●"; smooth=no ;;
    blocks)  vtype=spectrum; vlook="■■"; smooth=no ;;
    mirror)  vtype=spectrum; vlook="▮▮"; smooth=yes ;;
    wave)    vtype=wave; vlook="●●"; smooth=yes ;;
    terrain) vtype=wave_filled; vlook="▮▮"; smooth=yes ;;
    radial)  vtype=ellipse; vlook="●●"; smooth=yes ;;
    *)       vtype=spectrum; vlook="▮▮"; smooth=yes ;;
esac

# the accent: a terminal color name
case "$kit" in
    venom|fire|lava)            acc=red;     grad="red,magenta,yellow" ;;
    holo|butterfly)             acc=magenta; grad="magenta,blue,cyan" ;;
    cyber|neon|hud|liquid|crystal) acc=cyan; grad="cyan,blue,magenta" ;;
    nature|pixel|snake)         acc=green;   grad="green,cyan,yellow" ;;
    sketch)                     acc=white;   grad="white,cyan,blue" ;;
    *)                          acc=blue;    grad="blue,cyan,magenta" ;;
esac

# the same accent as a format code ($2 red ... $8 white)
case "$acc" in red) n=2 ;; green) n=3 ;; yellow) n=4 ;; blue) n=5 ;; magenta) n=6 ;; cyan) n=7 ;; *) n=8 ;; esac

{
    sed '/^# ── Theme (08-ncmpcpp.sh writes from here on)$/,$d' "$cfg"
    cat <<EOF
# ── Theme (08-ncmpcpp.sh writes from here on)
# (in formats: \$2 red \$3 green \$4 yellow \$5 blue \$6 magenta \$7 cyan \$8 white, \$9 back)
now_playing_prefix = "\$b\$$n 󰐊 "
now_playing_suffix = "\$9\$/b"
song_columns_list_format = "(6f)[default]{l} (46)[white]{t|f:Title} (28)[$acc]{a} (20)[default]{b}"
song_list_format = "{\$8%t\$9}|{\$8%f\$9}{ \$$n· %a\$9}\$R{\$$n%l\$9}"
song_status_format = "\$b{\$8%t\$9}|{\$8%f\$9}{ \$$n· %a\$9}\$/b"
alternative_header_first_line_format = "\$b\$8{%t}|{%f}\$9\$/b"
alternative_header_second_line_format = "{\$$n%a\$9}{ · %b}{ · %y}"
visualizer_type = "$vtype"
visualizer_look = "$vlook"
visualizer_spectrum_smooth_look = "$smooth"
visualizer_color = "$grad"
color1 = "white"
color2 = "$acc"
progressbar_look = "━━╸"
progressbar_color = "black"
progressbar_elapsed_color = "$acc"
statusbar_time_color = "$acc"
player_state_color = "$acc"
volume_color = "$acc"
state_line_color = "black"
state_flags_color = "$acc"
alternative_ui_separator_color = "black"
window_border_color = "$acc"
active_window_border = "$acc"
EOF
} > "$cfg.tmp" && mv "$cfg.tmp" "$cfg"
unset cfg kit spec vtype vlook smooth acc grad n
