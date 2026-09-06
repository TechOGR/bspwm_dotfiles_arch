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
# Base tools
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
# PARU
#
# FIX: se elimina install_yay(). Compilaba yay-bin desde AUR
# pero nunca se usaba en el resto del script (solo paru se usa
# en install_aur_packages), así que solo añadía tiempo de
# compilación y una fuente extra de posibles fallos sin
# ningún beneficio real.
#
# NOTA: tu README actual todavía dice "instalar yay si no lo
# tienes" — convendría actualizar ese texto a "paru", ya que
# es lo que el script realmente usa.
# ------------------------------------------------------------

install_paru() {
    step "Comprobando paru"

    if command -v paru >/dev/null 2>&1; then
        ok "paru ya está instalado"
        return
    fi

    info "Instalando paru..."

    local tmp_dir
    tmp_dir="$(mktemp -d)"

    (
        cd "$tmp_dir"

        git clone --depth=1 \
            https://aur.archlinux.org/paru-bin.git

        cd paru-bin

        makepkg -si --noconfirm
    )

    rm -rf "$tmp_dir"

    if command -v paru >/dev/null 2>&1; then
        ok "paru instalado correctamente"
    else
        die "No se pudo instalar paru."
    fi
}

# ------------------------------------------------------------
# Official packages
#
# FIX 1: se añaden las fuentes Nerd Font como paquetes explícitos
# del repo oficial (extra), en vez de dejarlas en AUR bajo el
# nombre ambiguo "nerd-fonts" (ver install_aur_packages más abajo
# para el detalle del problema que esto causaba).
#
# FIX 2 (NUEVO): se añade "jgmenu". Tu propio README documenta
# "Click Derecho en Escritorio -> Desplegar el menú de aplicaciones
# (JGmenu)" como atajo, pero el paquete nunca se instalaba. Está
# disponible en el repo oficial "extra", sin necesidad de AUR.
# ------------------------------------------------------------

install_packages() {
    step "Instalando stack BSPWM"

    local official_packages=(
        # ----------------------------------------------------
        # X11
        # ----------------------------------------------------
        xorg-server
        xorg-xinit
        xorg-xrandr
        xorg-xsetroot
        xorg-xprop
        xorg-xwininfo
        xorg-xdpyinfo
        xorg-xset

        # ----------------------------------------------------
        # Window manager
        # ----------------------------------------------------
        bspwm
        sxhkd

        # ----------------------------------------------------
        # Bar / compositor / launcher / menu
        # ----------------------------------------------------
        polybar
        picom
        rofi
        jgmenu

        # ----------------------------------------------------
        # Desktop utilities
        # ----------------------------------------------------
        feh
        dunst
        xsettingsd
        lxappearance
        lxsession
        polkit-gnome

        # ----------------------------------------------------
        # Terminal / shell
        # ----------------------------------------------------
        kitty
        zsh
        fzf

        # ----------------------------------------------------
        # File manager
        # ----------------------------------------------------
        thunar
        thunar-volman
        tumbler

        # ----------------------------------------------------
        # Audio
        # ----------------------------------------------------
        pavucontrol
        playerctl

        # ----------------------------------------------------
        # Network
        # ----------------------------------------------------
        networkmanager
        network-manager-applet

        # ----------------------------------------------------
        # Clipboard / screenshots
        # ----------------------------------------------------
        xclip
        xsel
        maim
        scrot

        # ----------------------------------------------------
        # CLI
        # ----------------------------------------------------
        bc
        jq
        unzip
        wget
        curl
        git
        rsync
        htop
        btop

        # ----------------------------------------------------
        # Fonts
        #
        # FIX: fuentes Nerd Font explícitas desde el repo oficial
        # "extra", en lugar de instalarlas vía AUR bajo el nombre
        # ambiguo "nerd-fonts" (ver nota en install_aur_packages).
        # ----------------------------------------------------
        noto-fonts
        noto-fonts-emoji
        ttf-dejavu
        ttf-jetbrains-mono-nerd
        ttf-firacode-nerd
        ttf-nerd-fonts-symbols

        # ----------------------------------------------------
        # GTK / themes
        # ----------------------------------------------------
        gtk3
        gtk4
        papirus-icon-theme

        # ----------------------------------------------------
        # System
        # ----------------------------------------------------
        dbus
        dbus-broker
        polkit

        # ----------------------------------------------------
        # Utilities used by scripts
        # ----------------------------------------------------
        imagemagick
        xdotool
        wmctrl
        eza
        bat
    )

    sudo pacman -S --needed --noconfirm \
        "${official_packages[@]}"

    ok "Paquetes oficiales instalados"
}

# ------------------------------------------------------------
# AUR packages
#
# FIX: se elimina "nerd-fonts" de este arreglo. Ese nombre ya
# no resuelve a un paquete único: en los repos de Arch es un
# GRUPO donde varios paquetes distintos "proveen" el mismo
# nombre virtual "nerd-fonts" (p. ej. ttf-nerd-fonts-symbols vs
# ttf-nerd-fonts-symbols-mono). Con --noconfirm, pacman/paru no
# se cuelga, pero resuelve el conflicto de forma arbitraria e
# instala solo un paquete de símbolos sueltos, NO las fuentes
# monoespaciadas parcheadas (JetBrains Mono Nerd, FiraCode Nerd,
# etc.) que tu Polybar/Rofi probablemente necesitan para los
# íconos. Esas fuentes ahora se piden explícitamente en
# install_packages(), desde el repo oficial, sin pasar por AUR.
# ------------------------------------------------------------

install_aur_packages() {
    step "Instalando paquetes AUR"

    if ! command -v paru >/dev/null 2>&1; then
        die "paru no está disponible."
    fi

    local aur_packages=(
        fzf-tab-git
    )

    paru -S --needed --noconfirm \
        "${aur_packages[@]}"

    ok "Paquetes AUR instalados"
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
        "$HOME/.cache"

    # --------------------------------------------------------
    # XDG user directories
    # --------------------------------------------------------

    xdg-user-dirs-update >/dev/null 2>&1 || true

    local pictures_dir

    pictures_dir="$(xdg-user-dir PICTURES 2>/dev/null || true)"

    if [[ -z "$pictures_dir" || "$pictures_dir" == "$HOME" ]]; then
        pictures_dir="$HOME/Pictures"
    fi

    mkdir -p \
        "$pictures_dir" \
        "$pictures_dir/Wallpapers" \
        "$pictures_dir/screenshots"

    mkdir -p \
        "$HOME/Downloads" \
        "$HOME/Documents" \
        "$HOME/Videos" \
        "$HOME/Music"

    ok "Directorios preparados"
}

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

copy_directory() {
    local source="$1"
    local destination="$2"

    [[ -d "$source" ]] || return 0

    mkdir -p "$destination"

    rsync -a \
        --delete \
        "$source/" \
        "$destination/"
}

copy_file() {
    local source="$1"
    local destination="$2"

    [[ -f "$source" ]] || return 0

    mkdir -p "$(dirname "$destination")"

    install -m 0644 \
        "$source" \
        "$destination"
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

            copy_directory \
                "$source" \
                "$CONFIG_DIR/$name"

        done < <(
            find "$SCRIPT_DIR/config" \
                -mindepth 1 \
                -maxdepth 1 \
                -type d \
                -print0
        )

    fi

    # --------------------------------------------------------
    # home/*
    # --------------------------------------------------------

    if [[ -d "$SCRIPT_DIR/home" ]]; then

        while IFS= read -r -d '' source; do

            local name
            name="$(basename "$source")"

            copy_file \
                "$source" \
                "$HOME_DIR/$name"

        done < <(
            find "$SCRIPT_DIR/home" \
                -mindepth 1 \
                -maxdepth 1 \
                -type f \
                -print0
        )

    fi

    # --------------------------------------------------------
    # misc/bin/*
    # --------------------------------------------------------

    if [[ -d "$SCRIPT_DIR/misc/bin" ]]; then

        rsync -a \
            "$SCRIPT_DIR/misc/bin/" \
            "$LOCAL_BIN/"

    fi

    # --------------------------------------------------------
    # misc/applications/*
    # --------------------------------------------------------

    if [[ -d "$SCRIPT_DIR/misc/applications" ]]; then

        rsync -a \
            "$SCRIPT_DIR/misc/applications/" \
            "$HOME/.local/share/applications/"

    fi

    ok "Configuración copiada"
}

# ------------------------------------------------------------
# Wallpapers
# ------------------------------------------------------------

install_wallpapers() {
    step "Instalando wallpapers"

    local wallpaper_source="$SCRIPT_DIR/Wallpapers"

    if [[ ! -d "$wallpaper_source" ]]; then
        warn "No existe la carpeta Wallpapers en el repositorio."
        warn "Se continuará sin instalar wallpapers."
        return
    fi

    # --------------------------------------------------------
    # Detect the user's real Pictures directory.
    # Works with:
    #
    # ~/Pictures
    # ~/Imágenes
    # ~/Bilder
    # etc.
    # --------------------------------------------------------

    local pictures_dir

    pictures_dir="$(xdg-user-dir PICTURES 2>/dev/null || true)"

    if [[ -z "$pictures_dir" || "$pictures_dir" == "$HOME" ]]; then
        pictures_dir="$HOME/Pictures"
    fi

    local wallpaper_dir="$pictures_dir/Wallpapers"

    mkdir -p "$wallpaper_dir"

    # --------------------------------------------------------
    # Copy wallpapers.
    # Existing files are kept.
    # --------------------------------------------------------

    rsync -av \
        "$wallpaper_source/" \
        "$wallpaper_dir/"

    ok "Wallpapers instalados en:"
    printf '     %s\n' "$wallpaper_dir"

    # --------------------------------------------------------
    # Stable path for scripts/configuration.
    # --------------------------------------------------------

    mkdir -p "$HOME/.local/share/techogr-bspwm"

    ln -sfn \
        "$wallpaper_dir" \
        "$HOME/.local/share/techogr-bspwm/Wallpapers"

    ok "Ruta estable de wallpapers creada"
}

# ------------------------------------------------------------
# Default wallpaper
# ------------------------------------------------------------

configure_default_wallpaper() {
    step "Configurando wallpaper predeterminado"

    local pictures_dir

    pictures_dir="$(xdg-user-dir PICTURES 2>/dev/null || true)"

    if [[ -z "$pictures_dir" || "$pictures_dir" == "$HOME" ]]; then
        pictures_dir="$HOME/Pictures"
    fi

    local wallpaper_dir="$pictures_dir/Wallpapers"

    if [[ ! -d "$wallpaper_dir" ]]; then
        warn "No existe $wallpaper_dir"
        return
    fi

    local wallpaper=""

    while IFS= read -r -d '' file; do
        wallpaper="$file"
        break
    done < <(
        find "$wallpaper_dir" \
            -type f \
            \( \
                -iname "*.jpg" \
                -o -iname "*.jpeg" \
                -o -iname "*.png" \
                -o -iname "*.webp" \
            \) \
            -print0 \
            2>/dev/null
    )

    if [[ -z "$wallpaper" ]]; then
        warn "No se encontraron imágenes en Wallpapers."
        return
    fi

    mkdir -p "$HOME/.config/techogr"

    printf '%s\n' "$wallpaper" \
        > "$HOME/.config/techogr/default-wallpaper"

    ok "Wallpaper predeterminado:"
    printf '     %s\n' "$wallpaper"
}

# ------------------------------------------------------------
# Permissions
# ------------------------------------------------------------

fix_permissions() {
    step "Corrigiendo permisos"

    # BSPWM
    if [[ -f "$CONFIG_DIR/bspwm/bspwmrc" ]]; then
        chmod +x "$CONFIG_DIR/bspwm/bspwmrc"
    fi

    # BSPWM scripts
    if [[ -d "$CONFIG_DIR/bspwm/bin" ]]; then

        find "$CONFIG_DIR/bspwm/bin" \
            -type f \
            -exec chmod +x {} \;

    fi

    # Other shell/python scripts
    for directory in \
        "$CONFIG_DIR/polybar" \
        "$CONFIG_DIR/eww" \
        "$CONFIG_DIR/jgmenu" \
        "$CONFIG_DIR/rofi" \
        "$CONFIG_DIR/sxhkd"; do

        if [[ -d "$directory" ]]; then

            find "$directory" \
                -type f \
                \( \
                    -name "*.sh" \
                    -o -name "*.py" \
                \) \
                -exec chmod +x {} \; \
                2>/dev/null || true

        fi

    done

    # Local binaries
    if [[ -d "$LOCAL_BIN" ]]; then

        find "$LOCAL_BIN" \
            -type f \
            -exec chmod +x {} \;

    fi

    # X session files
    [[ -f "$HOME/.xinitrc" ]] && \
        chmod +x "$HOME/.xinitrc"

    [[ -f "$HOME/.xprofile" ]] && \
        chmod +x "$HOME/.xprofile"

    ok "Permisos corregidos"
}

# ------------------------------------------------------------
# X session
# ------------------------------------------------------------

install_xsession() {
    step "Configurando sesión gráfica BSPWM"

    cat > "$HOME/.xinitrc" <<'EOF'
#!/bin/sh

# ============================================================
# TechOGR BSPWM X11 Session
# ============================================================

export XDG_CURRENT_DESKTOP="BSPWM"
export XDG_SESSION_DESKTOP="bspwm"
export XDG_SESSION_TYPE="x11"
export DESKTOP_SESSION="bspwm"

# ------------------------------------------------------------
# User PATH
# ------------------------------------------------------------

export PATH="$HOME/.local/bin:$PATH"

# ------------------------------------------------------------
# D-Bus environment
# ------------------------------------------------------------

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

# ------------------------------------------------------------
# Start BSPWM
#
# Do NOT start polybar, picom, eww, sxhkd, etc. here.
# bspwmrc controls the graphical environment.
# ------------------------------------------------------------

exec bspwm
EOF

    chmod +x "$HOME/.xinitrc"

    # --------------------------------------------------------
    # .xprofile
    # --------------------------------------------------------

    cat > "$HOME/.xprofile" <<'EOF'
#!/bin/sh

# ============================================================
# TechOGR BSPWM X11 Environment
# ============================================================

export XDG_CURRENT_DESKTOP="BSPWM"
export XDG_SESSION_DESKTOP="bspwm"
export XDG_SESSION_TYPE="x11"

export PATH="$HOME/.local/bin:$PATH"

export GTK_USE_PORTAL=0

export XCURSOR_SIZE="${XCURSOR_SIZE:-24}"

# Do not start bspwm here.
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

    ok "Sesión BSPWM registrada"
}

# ------------------------------------------------------------
# Safe BSPWM launcher
# ------------------------------------------------------------

install_safe_launcher() {
    step "Instalando launcher seguro"

    cat > "$LOCAL_BIN/start-bspwm" <<'EOF'
#!/bin/sh

# ============================================================
# TechOGR BSPWM Launcher
# ============================================================

export XDG_CURRENT_DESKTOP="BSPWM"
export XDG_SESSION_DESKTOP="bspwm"
export XDG_SESSION_TYPE="x11"

export PATH="$HOME/.local/bin:$PATH"

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

    cat > "$LOCAL_BIN/techogr-monitor-setup" <<'EOF'
#!/usr/bin/env bash

# ============================================================
# TechOGR Automatic Monitor Setup
# ============================================================

set -u

command -v xrandr >/dev/null 2>&1 || exit 0

xrandr >/dev/null 2>&1 || exit 0

mapfile -t outputs < <(
    xrandr --query |
        awk '$2 == "connected" {print $1}'
)

((${#outputs[@]} > 0)) || exit 0

# One monitor:
# keep the configuration supplied by X.
if ((${#outputs[@]} == 1)); then
    exit 0
fi

# Multiple monitors:
# Do not force a hardcoded output such as Virtual-1.
# BSPWM can handle the monitors without modifying Xrandr.
exit 0
EOF

    chmod +x "$LOCAL_BIN/techogr-monitor-setup"

    ok "Detector de monitores instalado"
}

# ------------------------------------------------------------
# BSPWM file validation
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

        done < <(
            find "$CONFIG_DIR/bspwm/bin" \
                -type f \
                -print0
        )

    fi

    if ((missing)); then
        warn "Hay archivos BSPWM ausentes."
    else
        ok "Archivos principales de BSPWM correctos"
    fi
}

# ------------------------------------------------------------
# Command validation
#
# FIX: se renombra la variable de bucle "command" a "cmd" para
# no reutilizar el mismo nombre que el builtin de bash "command"
# que se invoca justo debajo. Funcionalmente no rompía nada,
# pero es un nombre confuso que conviene evitar.
# ------------------------------------------------------------

check_commands() {
    step "Validando comandos"

    local commands=(
        bspwm
        sxhkd
        xrandr
        xsetroot
        xprop
        polybar
        picom
        rofi
        jgmenu
        kitty
        zsh
        fzf
        paru
    )

    local failed=0

    for cmd in "${commands[@]}"; do

        if command -v "$cmd" >/dev/null 2>&1; then
            ok "$cmd"
        else
            warn "$cmd no encontrado"
            failed=1
        fi

    done

    if ((failed)); then
        warn "Faltan algunos comandos."
    else
        ok "Stack BSPWM validado"
    fi
}

# ------------------------------------------------------------
# bspwmrc syntax
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
        warn "No se modificará automáticamente."
    fi
}

# ------------------------------------------------------------
# User services
# ------------------------------------------------------------

setup_user_services() {
    step "Preparando servicios de usuario"

    mkdir -p "$HOME/.config/systemd/user"

    if command -v systemctl >/dev/null 2>&1; then
        systemctl --user daemon-reload \
            >/dev/null 2>&1 || true
    fi

    ok "Servicios de usuario preparados"
}

# ------------------------------------------------------------
# ZSH
#
# FIX: se usa la variable ya resuelta $zsh_path en el mensaje
# de ayuda en vez de volver a llamar a `which zsh`, que no
# siempre está instalado en una base de Arch mínima.
# ------------------------------------------------------------

configure_shell() {
    step "Configurando ZSH"

    if ! command -v zsh >/dev/null 2>&1; then
        warn "ZSH no está disponible."
        return
    fi

    local zsh_path
    zsh_path="$(command -v zsh)"

    if [[ "${SHELL:-}" != "$zsh_path" ]]; then

        info "Cambiando shell predeterminado a ZSH..."

        if chsh -s "$zsh_path" "$USER" >/dev/null 2>&1; then
            ok "ZSH configurado"
        else
            warn "No se pudo cambiar automáticamente el shell."
            warn "Puedes hacerlo con: chsh -s $zsh_path"
        fi

    else
        ok "ZSH ya es el shell predeterminado"
    fi
}

# ------------------------------------------------------------
# fzf-tab
#
# FIX CRÍTICO: la regex de cierre del bloque awk tenía un
# espacio de más antes de la barra final:
#
#   /^# <<< TechOGR fzf-tab <<<$ / {   (versión rota)
#
# Ese espacio hacía que el patrón NUNCA coincidiera con la
# línea real del marcador de cierre (que no tiene espacio al
# final). Efecto real: la primera vez que corrías el instalador
# no pasaba nada raro, pero en la SEGUNDA ejecución (o cualquier
# re-ejecución posterior), el awk entraba en modo "skip" al
# encontrar el marcador de apertura y nunca lo desactivaba,
# por lo que borraba en silencio TODO lo que tuvieras después
# de ese bloque en tu .zshrc (alias, funciones, configuración
# propia, etc.). Se corrige quitando el espacio sobrante.
# ------------------------------------------------------------

configure_fzf_tab() {
    step "Configurando fzf-tab para ZSH"

    local zshrc="$HOME/.zshrc"

    if [[ ! -f "$zshrc" ]]; then
        warn "No existe $zshrc"
        return
    fi

    # --------------------------------------------------------
    # Remove previously generated TechOGR fzf-tab block.
    # This makes the installer idempotent.
    # --------------------------------------------------------

    local temp_file
    temp_file="$(mktemp)"

    awk '
        BEGIN { skip=0 }

        /^# >>> TechOGR fzf-tab >>>$/ {
            skip=1
            next
        }

        /^# <<< TechOGR fzf-tab <<<$/ {
            skip=0
            next
        }

        !skip {
            print
        }
    ' "$zshrc" > "$temp_file"

    mv "$temp_file" "$zshrc"

    # --------------------------------------------------------
    # Add configuration.
    # --------------------------------------------------------

    cat >> "$zshrc" <<'EOF'

# >>> TechOGR fzf-tab >>>
# ============================================================
# fzf-tab
# ============================================================

# fzf-tab installed from AUR.
# Load it when the plugin file exists.

if [[ -f /usr/share/zsh/plugins/fzf-tab-git/fzf-tab.plugin.zsh ]]; then
    source /usr/share/zsh/plugins/fzf-tab-git/fzf-tab.plugin.zsh
elif [[ -f /usr/share/zsh/plugins/fzf-tab/fzf-tab.plugin.zsh ]]; then
    source /usr/share/zsh/plugins/fzf-tab/fzf-tab.plugin.zsh
elif [[ -f /usr/share/zsh/site-functions/fzf-tab.plugin.zsh ]]; then
    source /usr/share/zsh/site-functions/fzf-tab.plugin.zsh
fi

# ------------------------------------------------------------
# Completion style
# ------------------------------------------------------------

zstyle ':completion:*' menu no

zstyle ':fzf-tab:*' fzf-flags \
    '--height=40%' \
    '--layout=reverse' \
    '--border=rounded'

# ------------------------------------------------------------
# Directory preview
# ------------------------------------------------------------

if (( $+commands[eza] )); then

    zstyle ':fzf-tab:complete:cd:*' fzf-preview \
        'eza --tree --level=2 --color=always --icons "$realpath"'

    zstyle ':fzf-tab:complete:*:*' fzf-preview \
        'if [[ -d "$realpath" ]]; then
            eza --tree --level=2 --color=always --icons "$realpath"
        elif [[ -f "$realpath" ]] && (( $+commands[bat] )); then
            bat --color=always --style=numbers "$realpath"
        fi'

fi

# <<< TechOGR fzf-tab <<<
EOF

    ok "fzf-tab configurado"
}

# ------------------------------------------------------------
# Environment
# ------------------------------------------------------------

configure_environment() {
    step "Configurando entorno"

    xdg-user-dirs-update \
        >/dev/null 2>&1 || true

    if [[ -f "$HOME/.zshrc" ]]; then

        if ! grep -qF \
            'export PATH="$HOME/.local/bin:$PATH"' \
            "$HOME/.zshrc"; then

            printf '\n# TechOGR local binaries\nexport PATH="$HOME/.local/bin:$PATH"\n' \
                >> "$HOME/.zshrc"

        fi

    fi

    ok "Entorno configurado"
}

# ------------------------------------------------------------
# Final report
#
# FIX: se quita la línea de "yay" del resumen, ya que install_yay
# fue eliminado (ver nota en la sección PARU más arriba). Se añade
# "JGmenu" ya que ahora sí se instala.
# ------------------------------------------------------------

print_report() {
    printf '\n'

    line

    printf '%b\n' \
        "${GREEN}${BOLD}  INSTALACIÓN COMPLETADA${RESET}"

    printf '\n'

    printf '  %b %s\n' "${GREEN}✓${RESET}" "BSPWM"
    printf '  %b %s\n' "${GREEN}✓${RESET}" "SXHKD"
    printf '  %b %s\n' "${GREEN}✓${RESET}" "Polybar"
    printf '  %b %s\n' "${GREEN}✓${RESET}" "Picom"
    printf '  %b %s\n' "${GREEN}✓${RESET}" "Rofi"
    printf '  %b %s\n' "${GREEN}✓${RESET}" "JGmenu"
    printf '  %b %s\n' "${GREEN}✓${RESET}" "Kitty"
    printf '  %b %s\n' "${GREEN}✓${RESET}" "Xorg/Xinit"
    printf '  %b %s\n' "${GREEN}✓${RESET}" "ZSH"
    printf '  %b %s\n' "${GREEN}✓${RESET}" "fzf"
    printf '  %b %s\n' "${GREEN}✓${RESET}" "fzf-tab"
    printf '  %b %s\n' "${GREEN}✓${RESET}" "paru"
    printf '  %b %s\n' "${GREEN}✓${RESET}" "Sesión BSPWM"
    printf '  %b %s\n' "${GREEN}✓${RESET}" "Wallpapers"
    printf '  %b %s\n' "${GREEN}✓${RESET}" "Permisos"
    printf '  %b %s\n' "${GREEN}✓${RESET}" "Validaciones"

    printf '\n'

    local pictures_dir
    pictures_dir="$(xdg-user-dir PICTURES 2>/dev/null || true)"

    if [[ -z "$pictures_dir" || "$pictures_dir" == "$HOME" ]]; then
        pictures_dir="$HOME/Pictures"
    fi

    printf '%b\n' \
        "${CYAN}  Wallpapers:${RESET} $pictures_dir/Wallpapers"

    printf '%b\n' \
        "${CYAN}  Backup:${RESET}     $BACKUP_DIR"

    printf '%b\n' \
        "${CYAN}  Log:${RESET}        $LOG_FILE"

    printf '\n'

    line

    printf '\n%b\n' \
        "${WHITE}${BOLD}  SIGUIENTE PASO${RESET}"

    printf '\n'

    printf '  Cierra sesión y selecciona:\n\n'

    printf '      %bBSPWM%b\n\n' \
        "${MAGENTA}${BOLD}" \
        "${RESET}"

    printf '%b\n\n' \
        "${YELLOW}  Si utilizas startx: startx${RESET}"
}

# ------------------------------------------------------------
# Main
#
# FIX: se elimina la llamada a install_yay (función eliminada,
# ver nota más arriba). El resto del orden de ejecución se
# mantiene igual porque ya era correcto.
# ------------------------------------------------------------

main() {

    title

    info "Repositorio: TechOGR/bspwm_dotfiles_arch"
    info "Instalador: Professional BSPWM Installer"
    info "Backup: habilitado"
    info "Wallpapers: habilitados"
    info "Paru: habilitado"
    info "fzf-tab: habilitado"
    info "Modo: seguro/idempotente"

    # --------------------------------------------------------
    # System
    # --------------------------------------------------------

    check_arch
    check_network

    # --------------------------------------------------------
    # Package managers
    # --------------------------------------------------------

    install_base_tools

    install_paru

    # --------------------------------------------------------
    # Packages
    # --------------------------------------------------------

    install_packages
    install_aur_packages

    # --------------------------------------------------------
    # Backup + directories
    # --------------------------------------------------------

    create_backup
    prepare_directories

    # --------------------------------------------------------
    # Dotfiles
    # --------------------------------------------------------

    install_dotfiles

    # --------------------------------------------------------
    # Wallpapers
    # --------------------------------------------------------

    install_wallpapers
    configure_default_wallpaper

    # --------------------------------------------------------
    # X11 / BSPWM session
    # --------------------------------------------------------

    install_xsession
    install_desktop_session
    install_safe_launcher
    install_monitor_helper

    # --------------------------------------------------------
    # Permissions
    # --------------------------------------------------------

    fix_permissions

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    check_bspwm_files
    check_commands
    check_bspwmrc_syntax

    # --------------------------------------------------------
    # Services / shell
    # --------------------------------------------------------

    setup_user_services
    configure_shell
    configure_fzf_tab
    configure_environment

    # --------------------------------------------------------
    # Done
    # --------------------------------------------------------

    print_report
}

main "$@"
