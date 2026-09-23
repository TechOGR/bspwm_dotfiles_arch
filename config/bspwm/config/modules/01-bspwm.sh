#!/bin/sh

# Window styles (RiceEditor -> Windows) take the border colors from the
# palette, so they follow it; "custom" keeps NORMAL_BC / FOCUSED_BC.
case ${WIN_STYLE:-custom} in
    neon) NORMAL_BC=${blackb}; FOCUSED_BC=${cyan} ;;
    hud)  NORMAL_BC=${black};  FOCUSED_BC=${blue} ;;
esac

bspc config border_width ${BORDER_WIDTH}
bspc config top_padding ${TOP_PADDING}
bspc config bottom_padding ${BOTTOM_PADDING}
bspc config left_padding ${LEFT_PADDING}
bspc config right_padding ${RIGHT_PADDING}
bspc config normal_border_color "${NORMAL_BC}"
bspc config focused_border_color "${FOCUSED_BC}"
bspc config presel_feedback_color "${blue}"
