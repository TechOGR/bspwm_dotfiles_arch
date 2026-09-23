#!/bin/sh
# jgmenu follows the rice palette: the colors block of jgmenurc, the
# HUD menu (menu.csv template -> prepend.csv) and the search glyph.

_dir="$HOME/.config/jgmenu"
_target="$_dir/jgmenurc"
_prepend="$_dir/prepend.csv"
_template="$_dir/menu.csv"

{
    sed '/^# Colors$/,$d' "$_target"
    cat << EOF
# Colors
color_menu_bg = ${jg_bg:-$bg} 98
color_menu_border = ${blue} 80
color_norm_bg = #000000 0
color_norm_fg = ${jg_fg:-$fg}
color_sel_bg = ${blue} 16
color_sel_fg = ${cyan}
color_sel_border = ${cyan} 70
color_sep_fg = ${blackb} 45
color_title_fg = ${magenta}
color_title_bg = #000000 0
color_title_border = #000000 0
color_scroll_ind = ${cyan} 60
sep_markup = font="JetBrainsMono Nerd Font ExtraBold 7.5" letter_spacing="2600" foreground="${magenta}"
EOF
} | _write "$_target"

if [ -f "$_template" ]; then
    _rice=$(printf '%s' "${RICE:-rice}" | tr '[:lower:]' '[:upper:]')
    {
        echo "# GENERATED from menu.csv by 06-jgmenu.sh -- edit menu.csv instead"
        grep -v '^#' "$_template" | sed \
            -e "s|{bg}|${bg}|g" -e "s|{fg}|${fg}|g" \
            -e "s|{black}|${black}|g" -e "s|{blackb}|${blackb}|g" \
            -e "s|{red}|${red}|g" -e "s|{green}|${green}|g" \
            -e "s|{yellow}|${yellow}|g" -e "s|{blue}|${blue}|g" \
            -e "s|{magenta}|${magenta}|g" -e "s|{cyan}|${cyan}|g" \
            -e "s|{white}|${white}|g" -e "s|{rice}|${_rice}|g"
    } | _write "$_prepend"
else
    awk -F',' -v OFS=',' -v color="$jg_fg" '
        /^@search,/ { $10 = color }
        { print }
    ' "$_prepend" | _write "$_prepend"
fi

_write "$_dir/search.svg" << EOF
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="32" height="32">
  <circle cx="10.5" cy="10.5" r="6.5" fill="none" stroke="${cyan}" stroke-width="2.4"/>
  <path d="M15.4 15.4 21 21" stroke="${magenta}" stroke-width="2.8" stroke-linecap="round"/>
</svg>
EOF
