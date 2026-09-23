#!/bin/sh

_write "$HOME/.config/bspwm/eww/colors.scss" << EOF
\$bg: ${bg};
\$bg-alt: ${accent_color};
\$fg: ${fg};
\$black: ${blackb};
\$red: ${red};
\$green: ${green};
\$yellow: ${yellow};
\$blue: ${blue};
\$magenta: ${magenta};
\$cyan: ${cyan};
\$archicon: ${arch_icon};

// Glass surfaces shared by the widgets (derived from the palette)
\$glass-bg: rgba(${bg}, 0.92);
\$glass-panel: rgba(${accent_color}, 0.85);
\$border-glow: rgba(${blue}, 0.35);
EOF
