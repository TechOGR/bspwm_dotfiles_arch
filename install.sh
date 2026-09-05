#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

readonly SCRIPT_NAME="TechOGR BSPWM Installer"
readonly REPO_URL="https://github.com/TechOGR/bspwm_dotfiles_arch.git"
readonly REPO_RAW_URL="https://raw.githubusercontent.com/TechOGR/bspwm_dotfiles_arch/main/install.sh"

readonly INSTALL_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/techogr-bspwm"
readonly BACKUP_ROOT="$INSTALL_ROOT/backups"
readonly LOG_DIR="$INSTALL_ROOT/logs"
readonly TIMESTAMP="$(date '+%Y-%m-%d_%H-%M-%S')"

CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}"
LOCAL_BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"

REPO_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"
LOG_FILE="$LOG_DIR/install-$TIMESTAMP.log"

TEMP_DIR=""
DRY_RUN=0
SKIP_UPGRADE=0
SKIP_AUR=0
SKIP_SHELL=0
ENABLE_NETWORK=0
ENABLE_LIGHTDM=0
AUR_HELPER=""

mkdir -p "$LOG_DIR"

exec > >(tee -a "$LOG_FILE") 2>&1

# -----------------------------------------------------------------------------
# Colors
# -----------------------------------------------------------------------------

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------

info() {
    printf "${BLUE}[%s]${RESET} %s\n" "INFO" "$*"
}

ok() {
    printf "${GREEN}[%s]${RESET} %s\n" "OK" "$*"
}

warn() {
    printf "${YELLOW}[%s]${RESET} %s\n" "WARN" "$*"
}

die() {
    printf "${RED}[%s]${RESET} %s\n" "ERROR" "$*" >&2
    exit 1
}

step() {
    printf "\n${CYAN}${BOLD}==> %s${RESET}\n" "$*"
}

# -----------------------------------------------------------------------------
# Cleanup / traps
# -----------------------------------------------------------------------------

cleanup() {
    if [[ -n "${TEMP_DIR:-}" && -d "$TEMP_DIR" ]]; then
        rm -rf -- "$TEMP_DIR"
    fi
}

on_error() {
    local code=$?

    printf "\n${RED}${BOLD}Installer failed (exit %s).${RESET}\n" "$code" >&2
    printf "Log: %s\n" "$LOG_FILE" >&2

    exit "$code"
}

trap on_error ERR
trap cleanup EXIT

# -----------------------------------------------------------------------------
# Usage
# -----------------------------------------------------------------------------

usage() {
    cat <<'USAGE'
Usage: ./install.sh [options]

Install the TechOGR BSPWM dotfiles on Arch Linux and Arch-based distributions.

Options:

  --no-upgrade
        Do not run a full pacman system upgrade.

  --no-aur
        Do not install missing AUR packages.

  --no-shell
        Do not change the login shell to zsh.

  --enable-network
        Enable NetworkManager when systemd is available.

  --enable-lightdm
        Install and enable LightDM only when no display manager is active.

  --dry-run
        Show actions without changing the system.

  -h, --help
        Show this help.

Recommended usage:

  git clone https://github.com/TechOGR/bspwm_dotfiles_arch.git
  cd bspwm_dotfiles_arch
  ./install.sh

One-line installation:

  bash -c "$(curl -fsSL https://raw.githubusercontent.com/TechOGR/bspwm_dotfiles_arch/main/install.sh)"
USAGE
}

# -----------------------------------------------------------------------------
# Generic command runner
# -----------------------------------------------------------------------------

run() {
    if (( DRY_RUN )); then
        printf "${YELLOW}[DRY-RUN]${RESET}"
        printf " %q" "$@"
        printf "\n"
        return 0
    fi

    command "$@"
}

run_as_root() {
    if (( DRY_RUN )); then
        printf "${YELLOW}[DRY-RUN]${RESET} sudo"
        printf " %q" "$@"
        printf "\n"
        return 0
    fi

    sudo "$@"
}

# -----------------------------------------------------------------------------
# Environment detection
# -----------------------------------------------------------------------------

is_arch_family() {
    [[ -r /etc/os-release ]] || return 1

    # shellcheck disable=SC1091
    source /etc/os-release

    [[ "${ID:-}" == "arch" ]] && return 0

    [[ " ${ID_LIKE:-} " == *" arch "* ]] && return 0

    return 1
}

confirm_user() {
    [[ "$(id -u)" -ne 0 ]] || \
        die "Run this installer as your normal user, not as root."

    [[ -n "${HOME:-}" && -d "$HOME" ]] || \
        die "HOME is not set correctly."

    [[ -n "${USER:-}" ]] || \
        die "USER is not set correctly."
}

require_commands() {
    local missing=()
    local cmd

    for cmd in "$@"; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            missing+=("$cmd")
        fi
    done

    if ((${#missing[@]})); then
        die "Missing required command(s): ${missing[*]}"
    fi
}

prepare_sudo() {
    command -v sudo >/dev/null 2>&1 || \
        die "sudo is required. Install and configure sudo first."

    if (( ! DRY_RUN )); then
        sudo -v

        (
            while sleep 45; do
                sudo -n true 2>/dev/null || exit
            done
        ) &

        SUDO_KEEPALIVE_PID=$!

        trap 'kill "${SUDO_KEEPALIVE_PID:-0}" 2>/dev/null || true; cleanup' EXIT
    fi
}

# -----------------------------------------------------------------------------
# Repository handling
# -----------------------------------------------------------------------------

ensure_repo() {
    if [[ -d "$REPO_DIR/config" &&
          -d "$REPO_DIR/home" &&
          -d "$REPO_DIR/misc" ]]; then
        return 0
    fi

    step "Repository files not present; cloning TechOGR dotfiles"

    require_commands git

    TEMP_DIR="$(mktemp -d -t techogr-bspwm-XXXXXX)"

    git clone \
        --depth=1 \
        "$REPO_URL" \
        "$TEMP_DIR/repo"

    REPO_DIR="$TEMP_DIR/repo"

    [[ -d "$REPO_DIR/config" &&
       -d "$REPO_DIR/home" &&
       -d "$REPO_DIR/misc" ]] || \
        die "Cloned repository is missing config/home/misc"
}

# -----------------------------------------------------------------------------
# Pacman helpers
# -----------------------------------------------------------------------------

pacman_installed() {
    pacman -Q "$1" >/dev/null 2>&1
}

pacman_has_package() {
    pacman -Si "$1" >/dev/null 2>&1
}

install_official_packages() {
    local available=()
    local missing=()
    local pkg

    for pkg in "$@"; do
        if pacman_installed "$pkg"; then
            continue
        fi

        if pacman_has_package "$pkg"; then
            available+=("$pkg")
        else
            missing+=("$pkg")
        fi
    done

    if ((${#available[@]})); then
        step "Installing official repository packages"

        run_as_root \
            pacman \
            -S \
            --needed \
            --noconfirm \
            "${available[@]}"
    fi

    if ((${#missing[@]})); then
        printf '%s\n' "${missing[@]}" \
            > "$INSTALL_ROOT/missing-official-packages.txt"

        warn "These packages were not found in the configured pacman repositories:"
        printf '  - %s\n' "${missing[@]}"

        warn "They were not automatically guessed as AUR packages."
        warn "Check your distribution repositories/package names."
    fi
}

# -----------------------------------------------------------------------------
# System upgrade
# -----------------------------------------------------------------------------

full_upgrade() {
    if (( SKIP_UPGRADE )); then
        warn "Skipping full system upgrade (--no-upgrade)."
        return 0
    fi

    step "Synchronizing repositories and upgrading the system"

    run_as_root pacman -Syu --noconfirm
}

# -----------------------------------------------------------------------------
# AUR
# -----------------------------------------------------------------------------

ensure_aur_helper() {
    if (( SKIP_AUR )); then
        return 1
    fi

    if command -v paru >/dev/null 2>&1; then
        AUR_HELPER="paru"
        return 0
    fi

    if command -v yay >/dev/null 2>&1; then
        AUR_HELPER="yay"
        return 0
    fi

    step "Installing paru from the AUR"

    require_commands git makepkg

    local build_dir

    build_dir="$(mktemp -d -t techogr-paru-XXXXXX)"

    if ! git clone \
        --depth=1 \
        https://aur.archlinux.org/paru.git \
        "$build_dir/paru"; then

        rm -rf -- "$build_dir"

        warn "Could not clone paru from the AUR."
        return 1
    fi

    pushd "$build_dir/paru" >/dev/null

    makepkg -si --noconfirm

    popd >/dev/null

    rm -rf -- "$build_dir"

    command -v paru >/dev/null 2>&1 || \
        die "paru installation failed."

    AUR_HELPER="paru"
}

install_aur_packages() {
    (( SKIP_AUR )) && return 0

    local pkg

    ensure_aur_helper || {
        warn "AUR helper unavailable; could not install:"
        printf '  - %s\n' "$@"
        return 0
    }

    step "Installing AUR packages"

    for pkg in "$@"; do
        pacman_installed "$pkg" && continue

        run \
            "$AUR_HELPER" \
            -S \
            --needed \
            --noconfirm \
            "$pkg"
    done
}

# -----------------------------------------------------------------------------
# Backup helpers
# -----------------------------------------------------------------------------

backup_path() {
    local target="$1"
    local rel

    rel="${target#$HOME/}"

    printf '%s/%s' "$BACKUP_DIR" "$rel"
}

backup_existing() {
    local target="$1"
    local dest

    [[ -e "$target" || -L "$target" ]] || return 0

    dest="$(backup_path "$target")"

    mkdir -p "$(dirname -- "$dest")"

    run cp -a -- "$target" "$dest"
}

# -----------------------------------------------------------------------------
# Dotfile deployment
# -----------------------------------------------------------------------------

deploy_directory() {
    local src="$1"
    local dest="$2"

    [[ -d "$src" ]] || return 0

    mkdir -p "$(dirname -- "$dest")"

    backup_existing "$dest"

    run mkdir -p "$dest"

    run rsync \
        -a \
        --delete \
        "$src/" \
        "$dest/"
}

deploy_file() {
    local src="$1"
    local dest="$2"

    [[ -f "$src" ]] || return 0

    mkdir -p "$(dirname -- "$dest")"

    backup_existing "$dest"

    run install \
        -m 0644 \
        "$src" \
        "$dest"
}

deploy_tree_without_delete() {
    local src="$1"
    local dest="$2"

    [[ -d "$src" ]] || return 0

    mkdir -p "$dest"

    while IFS= read -r -d '' file; do
        local rel
        local target

        rel="${file#$src/}"
        target="$dest/$rel"

        mkdir -p "$(dirname -- "$target")"

        backup_existing "$target"

        if [[ -L "$file" ]]; then
            run rsync -a "$file" "$target"
        else
            run install -m 0644 "$file" "$target"
        fi

    done < <(find "$src" -type f -print0)
}

install_dotfiles() {
    step "Creating backup"

    mkdir -p "$BACKUP_DIR"

    info "Backup location:"
    info "$BACKUP_DIR"

    step "Deploying TechOGR configuration"

    local src
    local name

    shopt -s nullglob dotglob

    # -------------------------------------------------------------------------
    # ~/.config/*
    # -------------------------------------------------------------------------

    for src in "$REPO_DIR/config"/*/; do
        name="$(basename "$src")"

        deploy_directory \
            "$src" \
            "$CONFIG_DIR/$name"
    done

    # -------------------------------------------------------------------------
    # Home files
    # -------------------------------------------------------------------------

    for src in "$REPO_DIR/home"/.* "$REPO_DIR/home"/*; do
        [[ -e "$src" || -L "$src" ]] || continue

        name="$(basename "$src")"

        [[ "$name" == "." || "$name" == ".." ]] && continue

        if [[ -f "$src" ]]; then
            deploy_file \
                "$src" \
                "$HOME/$name"
        fi
    done

    # -------------------------------------------------------------------------
    # ~/.local/bin
    # -------------------------------------------------------------------------

    deploy_tree_without_delete \
        "$REPO_DIR/misc/bin" \
        "$LOCAL_BIN_DIR"

    # -------------------------------------------------------------------------
    # Desktop applications
    # -------------------------------------------------------------------------

    deploy_tree_without_delete \
        "$REPO_DIR/misc/applications" \
        "$HOME/.local/share/applications"

    # -------------------------------------------------------------------------
    # Wallpapers
    # -------------------------------------------------------------------------

    if [[ -d "$REPO_DIR/misc/wallpapers" ]]; then
        deploy_tree_without_delete \
            "$REPO_DIR/misc/wallpapers" \
            "$HOME/Wallpapers"

    elif [[ -d "$REPO_DIR/Wallpapers" ]]; then
        deploy_tree_without_delete \
            "$REPO_DIR/Wallpapers" \
            "$HOME/Wallpapers"
    fi

    # -------------------------------------------------------------------------
    # Fonts
    # -------------------------------------------------------------------------

    if [[ -d "$REPO_DIR/misc/fonts" ]]; then
        deploy_tree_without_delete \
            "$REPO_DIR/misc/fonts" \
            "$HOME/.local/share/fonts"
    fi

    shopt -u nullglob dotglob
}

# -----------------------------------------------------------------------------
# Permissions
# -----------------------------------------------------------------------------

set_permissions() {
    if [[ -d "$CONFIG_DIR/bspwm/bin" ]]; then
        run chmod +x \
            "$CONFIG_DIR/bspwm/bin"/* \
            2>/dev/null || true
    fi

    if [[ -d "$LOCAL_BIN_DIR" ]]; then
        run find \
            "$LOCAL_BIN_DIR" \
            -type f \
            -exec chmod +x {} +
    fi

    if [[ -d "$CONFIG_DIR/polybar" ]]; then
        run find \
            "$CONFIG_DIR/polybar" \
            -type f \
            -name '*.sh' \
            -exec chmod +x {} + \
            2>/dev/null || true
    fi

    if [[ -f "$CONFIG_DIR/bspwm/bspwmrc" ]]; then
        run chmod +x \
            "$CONFIG_DIR/bspwm/bspwmrc"
    fi

    if [[ -f "$CONFIG_DIR/bspwm/start-bspwm" ]]; then
        run chmod +x \
            "$CONFIG_DIR/bspwm/start-bspwm"
    fi
}

# -----------------------------------------------------------------------------
# Hardware-safe patch
# -----------------------------------------------------------------------------

patch_bspwm_virtual_output() {
    local file="$CONFIG_DIR/bspwm/bspwmrc"

    [[ -f "$file" ]] || return 0

    # Your repository currently contains:
    #
    # xrandr --output Virtual-1 --mode 1920x1080 --rate 60
    #
    # This can break BSPWM startup on real hardware because Virtual-1 may not
    # exist. We preserve the behavior for VMs while making it harmless elsewhere.

    if grep -Fq \
        'xrandr --output Virtual-1 --mode 1920x1080 --rate 60' \
        "$file"; then

        backup_existing "$file"

        if (( DRY_RUN )); then

            printf \
                "${YELLOW}[DRY-RUN]${RESET} patch Virtual-1 xrandr call in %s\n" \
                "$file"

        else

            sed -i \
                's@^[[:space:]]*xrandr --output Virtual-1 --mode 1920x1080 --rate 60$@if xrandr --query 2>/dev/null | grep -q "^Virtual-1 connected"; then xrandr --output Virtual-1 --mode 1920x1080 --rate 60; fi@' \
                "$file"

            ok "Made the Virtual-1 monitor command hardware-safe."
        fi
    fi
}

# -----------------------------------------------------------------------------
# ZSH fzf-tab compatibility
# -----------------------------------------------------------------------------

fix_fzf_tab_path() {
    local expected="/usr/share/zsh/plugins/fzf-tab/fzf-tab.zsh"

    [[ -e "$expected" ]] && return 0

    local found=""

    found="$(
        find \
            /usr/share/zsh \
            /usr/share \
            -type f \
            -name 'fzf-tab.zsh' \
            2>/dev/null |
            head -n1 || true
    )"

    if [[ -n "$found" ]]; then
        run_as_root mkdir -p \
            "$(dirname -- "$expected")"

        run_as_root ln -sfn \
            "$found" \
            "$expected"

        ok "Linked fzf-tab to the path expected by your .zshrc."

    else
        warn "fzf-tab.zsh was not found."
        warn "Your .zshrc may report an error until fzf-tab is installed."
    fi
}

# -----------------------------------------------------------------------------
# X session
# -----------------------------------------------------------------------------

setup_session_files() {
    step "Preparing X11/BSPWM session integration"

    # -------------------------------------------------------------------------
    # .xinitrc
    # -------------------------------------------------------------------------

    if [[ ! -e "$HOME/.xinitrc" ]]; then

        if (( DRY_RUN )); then
            printf \
                "${YELLOW}[DRY-RUN]${RESET} create ~/.xinitrc\n"

        else
            cat > "$HOME/.xinitrc" <<'EOF_XINITRC'
#!/bin/sh

export XDG_CURRENT_DESKTOP=bspwm

exec bspwm
EOF_XINITRC

            chmod +x "$HOME/.xinitrc"
        fi
    fi

    # -------------------------------------------------------------------------
    # .xprofile
    # -------------------------------------------------------------------------

    if [[ ! -e "$HOME/.xprofile" ]]; then

        if (( DRY_RUN )); then
            printf \
                "${YELLOW}[DRY-RUN]${RESET} create ~/.xprofile\n"

        else
            cat > "$HOME/.xprofile" <<'EOF_XPROFILE'
#!/bin/sh

export XDG_CURRENT_DESKTOP=bspwm
export XDG_SESSION_DESKTOP=bspwm
EOF_XPROFILE
        fi
    fi

    # -------------------------------------------------------------------------
    # BSPWM desktop entry
    # -------------------------------------------------------------------------

    local session_file="/usr/share/xsessions/bspwm.desktop"

    if [[ ! -e "$session_file" ]]; then

        if (( DRY_RUN )); then

            printf \
                "${YELLOW}[DRY-RUN]${RESET} create %s\n" \
                "$session_file"

        else

            run_as_root mkdir -p \
                /usr/share/xsessions

            local tmp_session

            tmp_session="$(mktemp)"

            cat > "$tmp_session" <<'EOF_DESKTOP'
[Desktop Entry]
Name=BSPWM
Comment=Binary space partitioning window manager
Exec=bspwm
TryExec=bspwm
Type=Application
DesktopNames=bspwm
EOF_DESKTOP

            run_as_root install \
                -m 0644 \
                "$tmp_session" \
                "$session_file"

            rm -f -- "$tmp_session"
        fi
    fi
}

# -----------------------------------------------------------------------------
# Optional services
# -----------------------------------------------------------------------------

setup_services() {
    # -------------------------------------------------------------------------
    # NetworkManager
    # -------------------------------------------------------------------------

    if (( ENABLE_NETWORK )); then

        step "Configuring NetworkManager"

        if command -v systemctl >/dev/null 2>&1; then

            if systemctl list-unit-files \
                NetworkManager.service \
                >/dev/null 2>&1; then

                run_as_root \
                    systemctl \
                    enable \
                    --now \
                    NetworkManager.service

                ok "NetworkManager enabled."

            else
                warn "NetworkManager service unit was not found."
            fi

        else
            warn "systemctl not found."
            warn "NetworkManager was installed but not enabled."
        fi
    fi

    # -------------------------------------------------------------------------
    # LightDM
    # -------------------------------------------------------------------------

    if (( ENABLE_LIGHTDM )); then

        step "Configuring LightDM"

        if ! pacman_installed lightdm; then
            install_official_packages lightdm
        fi

        if command -v systemctl >/dev/null 2>&1; then

            if systemctl is-enabled \
                display-manager.service \
                >/dev/null 2>&1 ||
               systemctl is-active \
                display-manager.service \
                >/dev/null 2>&1; then

                warn "A display manager is already enabled/active."
                warn "Leaving it untouched."

            else

                run_as_root \
                    systemctl \
                    enable \
                    lightdm.service

                ok "LightDM enabled."
            fi

        else
            warn "systemctl not found."
            warn "LightDM was installed but not enabled."
        fi
    fi
}

# -----------------------------------------------------------------------------
# ZSH shell
# -----------------------------------------------------------------------------

change_shell() {
    if (( SKIP_SHELL )); then
        warn "Skipping shell change (--no-shell)."
        return 0
    fi

    command -v zsh >/dev/null 2>&1 || {
        warn "zsh is not installed."
        return 0
    }

    local current_shell
    local zsh_path

    current_shell="$(
        getent passwd "$USER" |
        awk -F: '{print $7}'
    )"

    zsh_path="$(command -v zsh)"

    [[ "$current_shell" == "$zsh_path" ]] && return 0

    if command -v chsh >/dev/null 2>&1; then

        step "Setting zsh as the login shell"

        if (( DRY_RUN )); then

            printf \
                "${YELLOW}[DRY-RUN]${RESET} chsh -s %s %s\n" \
                "$zsh_path" \
                "$USER"

        else

            if chsh -s "$zsh_path" "$USER"; then

                ok "Login shell changed to zsh."

            else

                warn "Could not change the login shell automatically."
                warn "Run manually:"
                warn "chsh -s $zsh_path"
            fi
        fi

    else
        warn "chsh is unavailable; skipping shell change."
    fi
}

# -----------------------------------------------------------------------------
# Font cache
# -----------------------------------------------------------------------------

refresh_fonts() {
    if command -v fc-cache >/dev/null 2>&1; then

        step "Refreshing font cache"

        run fc-cache -f

    else
        warn "fc-cache not found; font cache was not refreshed."
    fi
}

# -----------------------------------------------------------------------------
# Validation
# -----------------------------------------------------------------------------

validate_install() {
    step "Validating installation"

    local required_files=(
        "$CONFIG_DIR/bspwm/bspwmrc"
        "$CONFIG_DIR/bspwm/config/sxhkdrc"
        "$CONFIG_DIR/polybar"
        "$HOME/.zshrc"
    )

    local file
    local failed=0

    # -------------------------------------------------------------------------
    # Files
    # -------------------------------------------------------------------------

    for file in "${required_files[@]}"; do

        if [[ -e "$file" ]]; then
            ok "Present: $file"
        else
            warn "Missing: $file"
            failed=1
        fi
    done

    # -------------------------------------------------------------------------
    # Commands
    # -------------------------------------------------------------------------

    local commands=(
        bspwm
        sxhkd
        polybar
        rofi
        jgmenu
        dunst
        picom
        kitty
        zsh
        nvim
        thunar
        eww
        clipcatd
        lxpolkit
    )

    local cmd

    for cmd in "${commands[@]}"; do

        if command -v "$cmd" >/dev/null 2>&1; then
            ok "Command available: $cmd"
        else
            warn "Command missing: $cmd"
            failed=1
        fi
    done

    if (( failed )); then

        warn "Some components are missing."
        warn "Check the log:"
        warn "$LOG_FILE"

    else

        ok "Core BSPWM configuration validated successfully."
    fi
}

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------

print_summary() {
    cat <<EOF_SUMMARY

${GREEN}${BOLD}╔════════════════════════════════════════════════════╗
║             INSTALLATION COMPLETE                  ║
╚════════════════════════════════════════════════════╝${RESET}

${BOLD}TechOGR BSPWM${RESET}

Config directory:
  $CONFIG_DIR

Backup:
  $BACKUP_DIR

Log:
  $LOG_FILE

Repository:
  $REPO_DIR

Next step:

  Log out and select ${BOLD}BSPWM${RESET} from your display manager.

  Or, when using startx:

  ${BOLD}startx${RESET}

Important:

  The installer does not forcibly replace an existing display manager.

  To explicitly configure LightDM:
      ./install.sh --enable-lightdm

  To explicitly enable NetworkManager:
      ./install.sh --enable-network

  To skip the system upgrade:
      ./install.sh --no-upgrade

  To skip AUR packages:
      ./install.sh --no-aur

  To avoid changing your shell:
      ./install.sh --no-shell

EOF_SUMMARY
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

main() {

    while (($#)); do

        case "$1" in

            --no-upgrade)
                SKIP_UPGRADE=1
                ;;

            --no-aur)
                SKIP_AUR=1
                ;;

            --no-shell)
                SKIP_SHELL=1
                ;;

            --enable-network)
                ENABLE_NETWORK=1
                ;;

            --enable-lightdm)
                ENABLE_LIGHTDM=1
                ;;

            --dry-run)
                DRY_RUN=1
                ;;

            -h|--help)
                usage
                exit 0
                ;;

            *)
                die "Unknown option: $1"
                ;;
        esac

        shift
    done

    # -------------------------------------------------------------------------
    # Banner
    # -------------------------------------------------------------------------

    printf "${CYAN}${BOLD}"
    printf '╔════════════════════════════════════════════════════╗\n'
    printf '║         TechOGR BSPWM Dotfiles Installer          ║\n'
    printf '╚════════════════════════════════════════════════════╝\n'
    printf "${RESET}\n"

    # -------------------------------------------------------------------------
    # Environment
    # -------------------------------------------------------------------------

    confirm_user

    is_arch_family || \
        die "This installer supports Arch Linux and Arch-based distributions using pacman."

    require_commands \
        pacman \
        awk \
        sed \
        grep \
        find \
        rsync \
        install

    prepare_sudo

    ensure_repo

    mkdir -p \
        "$INSTALL_ROOT" \
        "$LOG_DIR"

    # -------------------------------------------------------------------------
    # Upgrade
    # -------------------------------------------------------------------------

    full_upgrade

    # -------------------------------------------------------------------------
    # Core packages
    # -------------------------------------------------------------------------

    step "Installing TechOGR BSPWM dependencies"

    install_official_packages \
        base-devel \
        git \
        curl \
        rsync \
        unzip \
        7zip \
        jq \
        bc \
        rust \
        \
        zsh \
        zsh-autosuggestions \
        zsh-syntax-highlighting \
        zsh-history-substring-search \
        fzf \
        fzf-tab-git \
        \
        bspwm \
        sxhkd \
        polybar \
        picom \
        rofi \
        jgmenu \
        dunst \
        feh \
        xsettingsd \
        \
        xorg-server \
        xorg-xinit \
        xorg-xrandr \
        xorg-xsetroot \
        xorg-xprop \
        xorg-xwininfo \
        xorg-xdpyinfo \
        xorg-xset \
        xdotool \
        wmctrl \
        xclip \
        xsel \
        \
        dbus \
        dbus-broker \
        polkit \
        lxsession \
        gtk3 \
        gtk4 \
        lxappearance \
        papirus-icon-theme \
        \
        kitty \
        geany \
        firefox \
        thunar \
        thunar-volman \
        tumbler \
        gvfs \
        viewnior \
        mpv \
        yazi \
        imagemagick \
        maim \
        scrot \
        ueberzugpp \
        \
        pipewire \
        pipewire-pulse \
        pipewire-alsa \
        wireplumber \
        pavucontrol \
        playerctl \
        clipcat \
        \
        networkmanager \
        network-manager-applet \
        brightnessctl \
        libnotify \
        xdg-utils \
        xdg-user-dirs \
        \
        python-pywal \
        mpd \
        ncmpcpp \
        \
        noto-fonts \
        noto-fonts-emoji \
        ttf-dejavu \
        ttf-jetbrains-mono-nerd \
        ttf-firacode-nerd \
        ttf-nerd-fonts-symbols

    # -------------------------------------------------------------------------
    # AUR components
    # -------------------------------------------------------------------------

    # eww is used directly by bspwmrc.
    install_aur_packages \
        eww

    # -------------------------------------------------------------------------
    # Install configuration
    # -------------------------------------------------------------------------

    install_dotfiles

    # -------------------------------------------------------------------------
    # Make hardware-specific parts safe
    # -------------------------------------------------------------------------

    patch_bspwm_virtual_output

    # -------------------------------------------------------------------------
    # Executable permissions
    # -------------------------------------------------------------------------

    set_permissions

    # -------------------------------------------------------------------------
    # ZSH plugin compatibility
    # -------------------------------------------------------------------------

    fix_fzf_tab_path

    # -------------------------------------------------------------------------
    # X session
    # -------------------------------------------------------------------------

    setup_session_files

    # -------------------------------------------------------------------------
    # Optional services
    # -------------------------------------------------------------------------

    setup_services

    # -------------------------------------------------------------------------
    # Shell
    # -------------------------------------------------------------------------

    change_shell

    # -------------------------------------------------------------------------
    # Fonts
    # -------------------------------------------------------------------------

    refresh_fonts

    # -------------------------------------------------------------------------
    # Final validation
    # -------------------------------------------------------------------------

    validate_install

    # -------------------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------------------

    print_summary
}

main "$@"
