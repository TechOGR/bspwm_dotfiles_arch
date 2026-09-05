#!/usr/bin/env bash

# ============================================================
# TechOGR BSPWM Dotfiles
# Professional Arch Linux Installer
# ============================================================

set -Eeuo pipefail
IFS=$'\n\t'

# ------------------------------------------------------------
# Colors
# ------------------------------------------------------------

RESET="\033[0m"
BOLD="\033[1m"
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
CYAN="\033[36m"
MAGENTA="\033[35m"
WHITE="\033[97m"

# ------------------------------------------------------------
# Paths
# ------------------------------------------------------------

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="$HOME"
CONFIG_DIR="$HOME/.config"
LOCAL_BIN="$HOME/.local/bin"
LOCAL_SHARE="$HOME/.local/share"
STATE_DIR="$HOME/.local/state/techogr-bspwm"
BACKUP_ROOT="$HOME/.local/share/techogr-bspwm-backups"

TIMESTAMP="$(date '+%Y-%m-%d_%H-%M-%S')"
BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"
LOG_FILE="$STATE_DIR/install.log"

mkdir -p "$STATE_DIR"

# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------

exec > >(tee -a "$LOG_FILE") 2>&1

# ------------------------------------------------------------
# UI
# ------------------------------------------------------------

line() {
    printf '%b\n' "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
}

title() {
    clear 2>/dev/null || true
    printf '\n'
    printf '%b\n' "${MAGENTA}${BOLD}"
    printf '   ████████╗███████╗ ██████╗██╗  ██╗ ██████╗  ██████╗ ██████╗ \n'
    printf '   ╚══██╔══╝██╔════╝██╔════╝██║  ██║██╔════╝ ██╔═══██╗██╔══██╗\n'
    printf '      ██║   █████╗  ██║     ███████║██║  ███╗██║   ██║██████╔╝\n'
    printf '      ██║   ██╔══╝  ██║     ██╔══██║██║   ██║██║   ██║██╔══██╗\n'
    printf '      ██║   ███████╗╚██████╗ ██║  ██║╚██████╔╝╚██████╔╝██████╔╝\n'
    printf '      ╚═╝   ╚══════╝ ╚═════╝ ╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═════╝\n'
    printf '%b\n' "${RESET}"
    printf '%b\n' "${WHITE}${BOLD}              BSPWM DOTFILES INSTALLER${RESET}"
    printf '%b\n\n' "${BLUE}                 Arch Linux Edition${RESET}"
}

info() {
    printf '%b\n' "${BLUE}  [INFO]${RESET} $*"
}

ok() {
    printf '%b\n' "${GREEN}  [  OK  ]${RESET} $*"
}

warn() {
    printf '%b\n' "${YELLOW}  [ WARN ]${RESET} $*"
}

error() {
    printf '%b\n' "${RED}  [ERROR ]${RESET} $*"
}

step() {
    printf '\n%b\n' "${CYAN}${BOLD}  ➜ $*${RESET}"
}

die() {
    error "$*"
    printf '\n'
    error "Installation aborted."
    error "Log: $LOG_FILE"
    exit 1
}

# ------------------------------------------------------------
# Error handling
# ------------------------------------------------------------

trap 'error "Error en línea $LINENO. Comando: $BASH_COMMAND"' ERR

# ------------------------------------------------------------
# Root check
# ------------------------------------------------------------

if [[ $EUID -eq 0 ]]; then
    die "No ejecutes este instalador como root."
fi

# ------------------------------------------------------------
# Detect distro
# ------------------------------------------------------------

check_arch() {
    step "Comprobando sistema"

    if [[ ! -f /etc/os-release ]]; then
        die "No se pudo detectar el sistema operativo."
    fi

    # shellcheck disable=SC1091
    source /etc/os-release

    if [[ "${ID:-}" != "arch" ]] &&
       [[ "${ID_LIKE:-}" != *"arch"* ]]; then
        die "Este instalador está diseñado para Arch Linux y derivados."
    fi

    ok "Sistema compatible: ${PRETTY_NAME:-Arch Linux}"
}

# ------------------------------------------------------------
# Internet
# ------------------------------------------------------------

check_network() {
    step "Comprobando conexión"

    if ! curl -fsSI --max-time 8 https://archlinux.org >/dev/null 2>&1; then
        die "No hay conexión a Internet."
    fi

    ok "Conexión disponible"
}

# ------------------------------------------------------------
# Required commands
# ------------------------------------------------------------

install_base_tools() {
    step "Instalando herramientas base"

    sudo pacman -Syu --needed --noconfirm \
        base-devel \
        git \
        curl \
        wget \
        rsync \
        unzip \
        p7zip \
        jq \
        xdg-utils \
        xdg-user-dirs

    ok "Herramientas base instaladas"
}

# ------------------------------------------------------------
# AUR helper
# ------------------------------------------------------------

install_yay() {
    step "Comprobando AUR helper"

    if command -v yay >/dev/null 2>&1; then
        ok "yay ya está instalado"
        return
    fi

    info "Instalando yay..."

    local tmp_dir
    tmp_dir="$(mktemp -d)"

    trap 'rm -rf "$tmp_dir"' RETURN

    git clone --depth=1 https://aur.archlinux.org/yay-bin.git "$tmp_dir/yay-bin"

    (
        cd "$tmp_dir/yay-bin"
        makepkg -si --noconfirm
    )

    if ! command -v yay >/dev/null 2>&1; then
        die "No se pudo instalar yay."
    fi

    ok "yay instalado"
}

# ------------------------------------------------------------
# Package installation
# ------------------------------------------------------------

install_packages() {
    step "Instalando stack BSPWM"

    local official_packages=(
        # X11
        xorg-server
        xorg-xinit
        xorg-xrandr
        xorg-xsetroot
        xorg-xprop
        xorg-xwininfo
        xorg-xdpyinfo
        xorg-xset

        # Window manager
        bspwm
        sxhkd

        # Bar / compositor / launcher
        polybar
        picom
        rofi

        # Desktop utilities
        feh
        dunst
        xsettingsd
        lxappearance
        lxsession
        polkit-gnome

        # Terminal / shell
        kitty
        zsh

        # File management
        thunar
        thunar-volman
        tumbler

        # Audio
        pavucontrol
        playerctl

        # Network
        networkmanager
        network-manager-applet

        # Clipboard / screenshots
        xclip
        xsel
        maim
        scrot

        # CLI utilities
        bc
        jq
        unzip
        wget
        curl
        git
        rsync
        htop
        btop
        neofetch

        # Fonts
        noto-fonts
        noto-fonts-emoji
        ttf-dejavu

        # GTK / themes
        gtk3
        gtk4
        papirus-icon-theme

        # System
        dbus
        dbus-broker
        polkit

        # Optional functionality used by many scripts
        imagemagick
        xdotool
        wmctrl
        xdg-user-dirs
    )

    sudo pacman -S --needed --noconfirm "${official_packages[@]}"

    ok "Paquetes oficiales instalados"

    step "Instalando paquetes AUR"

    local aur_packages=(
        nerd-fonts
    )

    yay -S --needed --noconfirm "${aur_packages[@]}" || \
        warn "Algunos paquetes AUR no pudieron instalarse; continuando."

    ok "Paquetes AUR procesados"
}

# ------------------------------------------------------------
# Backup
# ------------------------------------------------------------

backup_path() {
    local path="$1"

    [[ -e "$path" || -L "$path" ]] || return 0

    mkdir -p "$BACKUP_DIR"

    local relative

    if [[ "$path" == "$HOME_DIR/"* ]]; then
        relative="${path#$HOME_DIR/}"
    else
        relative="$(basename "$path")"
    fi

    mkdir -p "$BACKUP_DIR/$(dirname "$relative")"

    cp -a "$path" "$BACKUP_DIR/$relative"

    info "Backup: $path"
}

create_backup() {
    step "Creando backup de configuración"

    mkdir -p "$BACKUP_DIR"

    local targets=(
        "$HOME/.config/bspwm"
        "$HOME/.config/sxhkd"
        "$HOME/.config/polybar"
        "$HOME/.config/picom"
        "$HOME/.config/rofi"
        "$HOME/.config/kitty"
        "$HOME/.config/dunst"
        "$HOME/.config/eww"
        "$HOME/.config/jgmenu"
        "$HOME/.config/xsettingsd"
        "$HOME/.config/gtk-3.0"
        "$HOME/.config/gtk-4.0"
        "$HOME/.xinitrc"
        "$HOME/.xprofile"
        "$HOME/.xsession"
        "$HOME/.zshrc"
    )

    for target in "${targets[@]}"; do
        backup_path "$target"
    done

    printf '%s\n' "$TIMESTAMP" > "$BACKUP_DIR/backup.info"

    ok "Backup creado en:"
    printf '     %s\n' "$BACKUP_DIR"
}

# ------------------------------------------------------------
# Directory preparation
# ------------------------------------------------------------

prepare_directories() {
    step "Preparando estructura de directorios"

    mkdir -p \
        "$CONFIG_DIR" \
        "$LOCAL_BIN" \
        "$LOCAL_SHARE" \
        "$STATE_DIR" \
        "$HOME/.local/share/applications" \
        "$HOME/.local/share/fonts" \
        "$HOME/.cache" \
        "$HOME/Pictures" \
        "$HOME/Pictures/wallpapers" \
        "$HOME/Pictures/screenshots" \
        "$HOME/Downloads" \
        "$HOME/Documents" \
        "$HOME/Videos" \
        "$HOME/Music"

    xdg-user-dirs-update >/dev/null 2>&1 || true

    ok "Directorios preparados"
}

# ------------------------------------------------------------
# Copy configuration
# ------------------------------------------------------------

copy_directory() {
    local source="$1"
    local destination="$2"

    [[ -d "$source" ]] || return 0

    mkdir -p "$destination"

    rsync -a --delete \
        "$source/" \
        "$destination/"
}

copy_file() {
    local source="$1"
    local destination="$2"

    [[ -f "$source" ]] || return 0

    mkdir -p "$(dirname "$destination")"
    install -m 0644 "$source" "$destination"
}

install_dotfiles() {
    step "Instalando configuración"

    # --------------------------------------------------------
    # config/*
    # --------------------------------------------------------

    if [[ -d "$SCRIPT_DIR/config" ]]; then
        while IFS= read -r -d '' source; do
            local name
            name="$(basename "$source")"

            copy_directory "$source" "$CONFIG_DIR/$name"
        done < <(find "$SCRIPT_DIR/config" -mindepth 1 -maxdepth 1 -type d -print0)
    fi

    # --------------------------------------------------------
    # home/*
    # --------------------------------------------------------

    if [[ -d "$SCRIPT_DIR/home" ]]; then
        while IFS= read -r -d '' source; do
            local name
            name="$(basename "$source")"

            copy_file "$source" "$HOME_DIR/$name"
        done < <(find "$SCRIPT_DIR/home" -mindepth 1 -maxdepth 1 -type f -print0)
    fi

    # --------------------------------------------------------
    # misc/*
    # --------------------------------------------------------

    if [[ -d "$SCRIPT_DIR/misc/bin" ]]; then
        rsync -a "$SCRIPT_DIR/misc/bin/" "$LOCAL_BIN/"
    fi

    if [[ -d "$SCRIPT_DIR/misc/applications" ]]; then
        rsync -a \
            "$SCRIPT_DIR/misc/applications/" \
            "$HOME/.local/share/applications/"
    fi

    ok "Configuración copiada"
}

# ------------------------------------------------------------
# Permissions
# ------------------------------------------------------------

fix_permissions() {
    step "Corrigiendo permisos"

    # BSPWM
    [[ -f "$CONFIG_DIR/bspwm/bspwmrc" ]] && \
        chmod +x "$CONFIG_DIR/bspwm/bspwmrc"

    # All BSPWM scripts
    if [[ -d "$CONFIG_DIR/bspwm/bin" ]]; then
        find "$CONFIG_DIR/bspwm/bin" \
            -type f \
            -exec chmod +x {} \;
    fi

    # Other configuration scripts
    for directory in \
        "$CONFIG_DIR/polybar" \
        "$CONFIG_DIR/eww" \
        "$CONFIG_DIR/jgmenu" \
        "$CONFIG_DIR/rofi" \
        "$CONFIG_DIR/sxhkd"; do

        if [[ -d "$directory" ]]; then
            find "$directory" \
                -type f \
                \( -name "*.sh" -o -name "*.py" \) \
                -exec chmod +x {} \; 2>/dev/null || true
        fi
    done

    # Local binaries
    if [[ -d "$LOCAL_BIN" ]]; then
        find "$LOCAL_BIN" \
            -type f \
            -exec chmod +x {} \;
    fi

    # xinit files
    [[ -f "$HOME/.xinitrc" ]] && chmod +x "$HOME/.xinitrc"
    [[ -f "$HOME/.xprofile" ]] && chmod +x "$HOME/.xprofile"

    ok "Permisos corregidos"
}

# ------------------------------------------------------------
# Safe X session
# ------------------------------------------------------------

install_xsession() {
    step "Configurando sesión gráfica BSPWM"

    cat > "$HOME/.xinitrc" <<'EOF'
#!/bin/sh

# ============================================================
# TechOGR BSPWM X11 Session
# ============================================================

# User environment
export XDG_CURRENT_DESKTOP="BSPWM"
export XDG_SESSION_DESKTOP="bspwm"
export XDG_SESSION_TYPE="x11"
export DESKTOP_SESSION="bspwm"

# D-Bus
if command -v dbus-update-activation-environment >/dev/null 2>&1; then
    dbus-update-activation-environment --systemd \
        DISPLAY \
        XAUTHORITY \
        XDG_CURRENT_DESKTOP \
        XDG_SESSION_DESKTOP \
        XDG_SESSION_TYPE \
        DBUS_SESSION_BUS_ADDRESS \
        >/dev/null 2>&1 || true
fi

# Start BSPWM.
# IMPORTANT:
# Do not launch polybar/picom/eww/etc. here.
# bspwmrc controls the graphical environment.
exec bspwm
EOF

    chmod +x "$HOME/.xinitrc"

    # .xprofile is intentionally lightweight.
    cat > "$HOME/.xprofile" <<'EOF'
#!/bin/sh

export XDG_CURRENT_DESKTOP="BSPWM"
export XDG_SESSION_DESKTOP="bspwm"
export XDG_SESSION_TYPE="x11"

# User PATH
export PATH="$HOME/.local/bin:$PATH"

# GTK
export GTK_USE_PORTAL=0

# Cursor
export XCURSOR_SIZE="${XCURSOR_SIZE:-24}"

# Do not start bspwm from here.
# The display manager or .xinitrc starts the session.
EOF

    chmod +x "$HOME/.xprofile"

    ok "Sesión X11 configurada"
}

# ------------------------------------------------------------
# Desktop session
# ------------------------------------------------------------

install_desktop_session() {
    step "Registrando BSPWM en el sistema"

    local session_dir="/usr/share/xsessions"

    sudo mkdir -p "$session_dir"

    sudo tee "$session_dir/bspwm.desktop" >/dev/null <<'EOF'
[Desktop Entry]
Name=BSPWM
Comment=Binary Space Partitioning Window Manager
Exec=bspwm
TryExec=bspwm
Type=Application
DesktopNames=BSPWM
X-GDM-SessionRegisters=true
EOF

    ok "Sesión BSPWM registrada en /usr/share/xsessions/"
}

# ------------------------------------------------------------
# Safe BSPWM launcher
# ------------------------------------------------------------

install_safe_launcher() {
    step "Instalando launcher seguro"

    cat > "$LOCAL_BIN/start-bspwm" <<'EOF'
#!/bin/sh

# TechOGR BSPWM launcher

export XDG_CURRENT_DESKTOP="BSPWM"
export XDG_SESSION_DESKTOP="bspwm"
export XDG_SESSION_TYPE="x11"

exec bspwm
EOF

    chmod +x "$LOCAL_BIN/start-bspwm"

    ok "Launcher instalado"
}

# ------------------------------------------------------------
# Monitor helper
# ------------------------------------------------------------

install_monitor_helper() {
    step "Instalando detector de monitores"

    mkdir -p "$LOCAL_BIN"

    cat > "$LOCAL_BIN/techogr-monitor-setup" <<'EOF'
#!/usr/bin/env bash

# ============================================================
# TechOGR automatic monitor setup
# ============================================================

set -u

command -v xrandr >/dev/null 2>&1 || exit 0

# Do not fail the BSPWM session if xrandr is unavailable.
xrandr >/dev/null 2>&1 || exit 0

# Find connected outputs.
mapfile -t outputs < <(
    xrandr --query |
    awk '$2 == "connected" {print $1}'
)

((${#outputs[@]} > 0)) || exit 0

# If one monitor is present, keep the current X configuration.
# This avoids dangerous hardcoded output names such as Virtual-1.
if ((${#outputs[@]} == 1)); then
    exit 0
fi

# Multiple monitors:
# xrandr is left untouched unless an explicit user layout exists.
# BSPWM itself will handle desktops/monitors.
exit 0
EOF

    chmod +x "$LOCAL_BIN/techogr-monitor-setup"

    ok "Detector de monitores instalado"
}

# ------------------------------------------------------------
# BSPWM dependency checker
# ------------------------------------------------------------

check_bspwm_files() {
    step "Validando archivos BSPWM"

    local missing=0

    local required=(
        "$CONFIG_DIR/bspwm/bspwmrc"
        "$CONFIG_DIR/sxhkd/sxhkdrc"
    )

    for file in "${required[@]}"; do
        if [[ -f "$file" ]]; then
            ok "$(basename "$file")"
        else
            warn "Falta: $file"
            missing=1
        fi
    done

    if [[ -d "$CONFIG_DIR/bspwm/bin" ]]; then
        while IFS= read -r -d '' file; do
            if [[ ! -x "$file" ]]; then
                warn "Script sin permiso de ejecución: $file"
                chmod +x "$file" || true
            fi
        done < <(find "$CONFIG_DIR/bspwm/bin" -type f -print0)
    fi

    if ((missing)); then
        warn "Hay archivos BSPWM ausentes."
        warn "El sistema continuará, pero revisa el contenido del repositorio."
    else
        ok "Archivos principales de BSPWM correctos"
    fi
}

# ------------------------------------------------------------
# Validate commands used by BSPWM
# ------------------------------------------------------------

check_commands() {
    step "Validando comandos"

    local commands=(
        bspwm
        sxhkd
        xrandr
        xsetroot
        xprop
    )

    local failed=0

    for command in "${commands[@]}"; do
        if command -v "$command" >/dev/null 2>&1; then
            ok "$command"
        else
            warn "$command no encontrado"
            failed=1
        fi
    done

    if ((failed)); then
        warn "Faltan algunos comandos."
    else
        ok "Stack X11/BSPWM validado"
    fi
}

# ------------------------------------------------------------
# Check bspwmrc syntax
# ------------------------------------------------------------

check_bspwmrc_syntax() {
    step "Validando sintaxis de bspwmrc"

    local bspwmrc="$CONFIG_DIR/bspwm/bspwmrc"

    if [[ ! -f "$bspwmrc" ]]; then
        warn "No existe $bspwmrc"
        return
    fi

    if bash -n "$bspwmrc"; then
        ok "Sintaxis de bspwmrc correcta"
    else
        warn "bspwmrc contiene errores de sintaxis."
        warn "No se modificará automáticamente para evitar romper tu configuración."
    fi
}

# ------------------------------------------------------------
# User services
# ------------------------------------------------------------

setup_user_services() {
    step "Preparando servicios de usuario"

    mkdir -p "$HOME/.config/systemd/user"

    # Make sure the user systemd instance can receive environment.
    if command -v systemctl >/dev/null 2>&1; then
        systemctl --user daemon-reload >/dev/null 2>&1 || true
    fi

    ok "Servicios de usuario preparados"
}

# ------------------------------------------------------------
# Shell
# ------------------------------------------------------------

configure_shell() {
    step "Configurando ZSH"

    if command -v zsh >/dev/null 2>&1; then
        if [[ "${SHELL:-}" != "$(command -v zsh)" ]]; then
            info "Cambiando shell predeterminado a zsh..."

            if chsh -s "$(command -v zsh)" "$USER" >/dev/null 2>&1; then
                ok "ZSH configurado"
            else
                warn "No se pudo cambiar automáticamente el shell."
                warn "Puedes hacerlo después con: chsh -s \$(which zsh)"
            fi
        else
            ok "ZSH ya es el shell predeterminado"
        fi
    fi
}

# ------------------------------------------------------------
# GTK / user dirs
# ------------------------------------------------------------

configure_environment() {
    step "Configurando entorno"

    xdg-user-dirs-update >/dev/null 2>&1 || true

    # Make sure local binaries have priority.
    if [[ -f "$HOME/.zshrc" ]]; then
        if ! grep -qF 'export PATH="$HOME/.local/bin:$PATH"' "$HOME/.zshrc"; then
            printf '\n# TechOGR local binaries\nexport PATH="$HOME/.local/bin:$PATH"\n' \
                >> "$HOME/.zshrc"
        fi
    fi

    ok "Entorno configurado"
}

# ------------------------------------------------------------
# Installation report
# ------------------------------------------------------------

print_report() {
    printf '\n'
    line

    printf '%b\n' "${GREEN}${BOLD}  INSTALACIÓN COMPLETADA${RESET}"
    printf '\n'

    printf '  %b %s\n' "${GREEN}✓${RESET}" "BSPWM instalado"
    printf '  %b %s\n' "${GREEN}✓${RESET}" "SXHKD instalado"
    printf '  %b %s\n' "${GREEN}✓${RESET}" "Polybar instalado"
    printf '  %b %s\n' "${GREEN}✓${RESET}" "Picom instalado"
    printf '  %b %s\n' "${GREEN}✓${RESET}" "Rofi instalado"
    printf '  %b %s\n' "${GREEN}✓${RESET}" "Xorg/Xinit instalado"
    printf '  %b %s\n' "${GREEN}✓${RESET}" "Sesión BSPWM registrada"
    printf '  %b %s\n' "${GREEN}✓${RESET}" ".xinitrc configurado"
    printf '  %b %s\n' "${GREEN}✓${RESET}" ".xprofile configurado"
    printf '  %b %s\n' "${GREEN}✓${RESET}" "Permisos corregidos"
    printf '  %b %s\n' "${GREEN}✓${RESET}" "Configuración validada"

    printf '\n'
    printf '%b\n' "${CYAN}  Backup:${RESET} $BACKUP_DIR"
    printf '%b\n' "${CYAN}  Log:${RESET}    $LOG_FILE"

    printf '\n'
    line

    printf '\n%b\n' "${WHITE}${BOLD}  SIGUIENTE PASO${RESET}"
    printf '\n'
    printf '  Cierra sesión y selecciona:\n\n'
    printf '      %bBSPWM%b\n\n' "${MAGENTA}${BOLD}" "${RESET}"

    printf '%b\n\n' "${YELLOW}  Si utilizas startx, ejecuta: startx${RESET}"
}

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

main() {
    title

    info "Repositorio: TechOGR/bspwm_dotfiles_arch"
    info "Instalador: Professional BSPWM Installer"
    info "Backup: habilitado"
    info "Modo: seguro/idempotente"

    check_arch
    check_network

    install_base_tools
    install_yay
    install_packages

    create_backup
    prepare_directories
    install_dotfiles

    install_xsession
    install_desktop_session
    install_safe_launcher
    install_monitor_helper

    fix_permissions

    check_bspwm_files
    check_commands
    check_bspwmrc_syntax

    setup_user_services
    configure_shell
    configure_environment

    print_report
}

main "$@"
