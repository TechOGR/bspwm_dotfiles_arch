#!/usr/bin/env bash
# =============================================================
# Author:  TechOGR
# Repo:    https://github.com/TechOGR/bspwm_dotfiles_arch
#
# TechOGR login screen: LightDM + lightdm-webkit2-greeter with the
# "techogr" theme (the BetterLock card of super+shift+l, with user,
# password, session and power buttons).
#   sudo ./install-login.sh [USER]     install / update
#   sudo ./install-login.sh --revert   back to lightdm-gtk-greeter
# USER owns the theme's data/ folder, where BetterLock --prepare keeps
# the wallpaper, avatar and colors in sync.
# =============================================================
set -euo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
THEME=/usr/share/lightdm-webkit/themes/techogr
GREETER_CONF=/etc/lightdm/lightdm-webkit2-greeter.conf
SEAT_CONF=/etc/lightdm/lightdm.conf.d/50-bspwm.conf

[[ $EUID -eq 0 ]] || { echo "Run it with sudo: sudo $0 ${*:-}" >&2; exit 1; }

seat_conf() {
    install -d -m755 /etc/lightdm/lightdm.conf.d
    printf '[Seat:*]\nuser-session=bspwm\ngreeter-session=%s\n' "$1" > "$SEAT_CONF"
}

if [[ "${1:-}" == "--revert" ]]; then
    pacman -S --needed --noconfirm lightdm-gtk-greeter
    seat_conf lightdm-gtk-greeter
    echo "LightDM uses lightdm-gtk-greeter again (applies on the next login screen)."
    exit 0
fi

USER_NAME="${1:-${SUDO_USER:-}}"

pacman -S --needed --noconfirm lightdm lightdm-webkit2-greeter

install -d -m755 "$THEME"
install -m644 "$HERE/techogr/index.html" "$HERE/techogr/style.css" \
    "$HERE/techogr/greeter.js" "$HERE/techogr/index.theme" "$THEME/"
install -d -m755 "$THEME/data"
if [[ -n "$USER_NAME" ]] && id "$USER_NAME" >/dev/null 2>&1; then
    chown "$USER_NAME:$(id -gn "$USER_NAME")" "$THEME/data"
fi

# Only the keys we need; the rest of the packaged file stays as it is.
if [[ -f "$GREETER_CONF" ]]; then
    sed -i -E 's/^(\s*webkit_theme\s*=).*/\1 techogr/;
               s/^(\s*debug_mode\s*=).*/\1 false/;
               s/^(\s*detect_theme_errors\s*=).*/\1 true/' "$GREETER_CONF"
else
    printf '[greeter]\ndebug_mode = false\ndetect_theme_errors = true\nsecure_mode = true\nwebkit_theme = techogr\n' > "$GREETER_CONF"
fi

seat_conf lightdm-webkit2-greeter
systemctl is-enabled --quiet lightdm.service 2>/dev/null || systemctl enable lightdm.service ||
    echo "Warning: could not enable lightdm.service (another display manager enabled?)" >&2

echo "TechOGR login installed in $THEME"
