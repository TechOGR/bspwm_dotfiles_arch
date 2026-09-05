#!/usr/bin/env bash
# ============================================================================
# TechOGR BSPWM Dotfiles - Professional Installer
# Repository: https://github.com/TechOGR/bspwm_dotfiles_arch
#
# Designed for Arch Linux and Arch-based distributions using pacman.
#
# Eww note:
# The AUR package `eww` is intentionally NOT used. The package is stale
# (0.6.0-1) and has known build problems with modern Rust toolchains.
# This installer builds Eww directly from upstream for X11 instead.
# ============================================================================

set -Eeuo pipefail
IFS=$'\n\t'

readonly SCRIPT_VERSION="2.0.0"
readonly REPO_URL="https://github.com/TechOGR/bspwm_dotfiles_arch.git"
readonly EWW_REPO_URL="https://github.com/elkowar/eww.git"
readonly EWW_REF="v0.6.0"

readonly HOME_DIR="$HOME"
readonly CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}"
readonly LOCAL_BIN="$HOME/.local/bin"
readonly LOCAL_SHARE="$HOME/.local/share"
readonly STATE_DIR="$HOME/.local/state/techogr-bspwm"
readonly BACKUP_ROOT="$HOME/.RiceBackup"
readonly TIMESTAMP="$(date '+%Y-%m-%d_%H-%M-%S')"
readonly BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"
readonly LOG_FILE="$STATE_DIR/install-$TIMESTAMP.log"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_DIR="$SCRIPT_DIR"

TEMP_ROOT=""
SUDO_KEEPALIVE_PID=""

NO_UPGRADE=0
NO_SHELL=0
NO_AUR=0
ENABLE_NETWORK=0
ENABLE_LIGHTDM=0
DRY_RUN=0
INSTALL_EWW=1

# -----------------------------------------------------------------------------
# Colors
# -----------------------------------------------------------------------------

RESET='\033[0m'
BOLD='\033[1m'
RED='\033[31m'
GREEN='\033[32m'
YELLOW='\033[33m'
BLUE='\033[34m'
CYAN='\033[36m'
MAGENTA='\033[35m'
WHITE='\033[97m'

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------

mkdir -p "$STATE_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

info()  { printf '%b\n' "${BLUE}[INFO]${RESET} $*"; }
ok()    { printf '%b\n' "${GREEN}[ OK ]${RESET} $*"; }
warn()  { printf '%b\n' "${YELLOW}[WARN]${RESET} $*"; }
error() { printf '%b\n' "${RED}[ERROR]${RESET} $*" >&2; }
step()  { printf '\n%b\n' "${CYAN}${BOLD}==> $*${RESET}"; }

fatal() {
    error "$*"
    error "Instalación abortada."
    error "Log: $LOG_FILE"
    exit 1
}

on_error() {
    local code=$?
    error "Falló una operación en la línea ${BASH_LINENO[0]:-unknown}."
    error "Comando: ${BASH_COMMAND:-unknown}"
    error "Código de salida: $code"
    error "Log completo: $LOG_FILE"
    exit "$code"
}

trap on_error ERR

cleanup() {
    if [[ -n "$SUDO_KEEPALIVE_PID" ]]; then
        kill "$SUDO_KEEPALIVE_PID" 2>/dev/null || true
    fi

    if [[ -n "$TEMP_ROOT" && -d "$TEMP_ROOT" ]]; then
        rm -rf -- "$TEMP_ROOT"
    fi
}

trap cleanup EXIT

# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------

print_banner() {
    clear 2>/dev/null || true

    printf '%b\n' "${MAGENTA}${BOLD}"
    printf ' ████████╗███████╗ ██████╗██╗  ██╗ ██████╗  ██████╗ ██████╗  ███████╗\n'
    printf ' ╚══██╔══╝██╔════╝██╔════╝██║ ██╔╝██╔═══██╗██╔════╝ ██╔══██╗ ██╔════╝\n'
    printf '    ██║   █████╗  ██║     █████╔╝ ██║   ██║██║  ███╗██████╔╝ █████╗  \n'
    printf '    ██║   ██╔══╝  ██║     ██╔═██╗ ██║   ██║██║   ██║██╔══██╗ ██╔══╝  \n'
    printf '    ██║   ███████╗╚██████╗██║  ██╗╚██████╔╝╚██████╔╝██║  ██║ ███████╗\n'
    printf '    ╚═╝   ╚══════╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚══════╝\n'
    printf '%b\n' "$RESET"

    printf '%b\n' "${WHITE}${BOLD}             BSPWM DOTFILES INSTALLER — TechOGR v${SCRIPT_VERSION}${RESET}"
    printf '%b\n\n' "${BLUE}             Arch Linux / Arch-based deployment${RESET}"
}

usage() {
    cat <<USAGE
Uso:
  ./install.sh [opciones]

Opciones:
  --no-upgrade        No ejecuta pacman -Syu.
  --no-shell          No cambia el shell de login a zsh.
  --no-aur            Compatibilidad heredada; esta versión no depende del AUR.
  --enable-network    Habilita NetworkManager.
  --enable-lightdm    Instala/activa LightDM solamente si no hay DM activo.
  --no-eww            No instala Eww.
  --dry-run           Muestra acciones sin modificar el sistema.
  -h, --help          Muestra esta ayuda.

Uso recomendado:
  git clone $REPO_URL
  cd bspwm_dotfiles_arch
  chmod +x install.sh
  ./install.sh
USAGE
}

# -----------------------------------------------------------------------------
# Generic command helpers
# -----------------------------------------------------------------------------

run() {
    if (( DRY_RUN )); then
        printf '%b' "${YELLOW}[DRY-RUN]${RESET}"
        printf ' %q' "$@"
        printf '\n'
    else
        command "$@"
    fi
}

root_run() {
    if (( DRY_RUN )); then
        printf '%b' "${YELLOW}[DRY-RUN]${RESET} sudo"
        printf ' %q' "$@"
        printf '\n'
    else
        sudo "$@"
    fi
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

require_commands() {
    local missing=()
    local cmd

    for cmd in "$@"; do
        if ! command_exists "$cmd"; then
            missing+=("$cmd")
        fi
    done

    if ((${#missing[@]})); then
        fatal "Faltan comandos necesarios: ${missing[*]}"
    fi
}

# -----------------------------------------------------------------------------
# Environment validation
# -----------------------------------------------------------------------------

check_environment() {
    step "Validando entorno"

    (( EUID != 0 )) || fatal "Ejecuta este script como usuario normal, no como root."

    [[ -n "$HOME" ]] || fatal "HOME no está definido."

    [[ -r /etc/os-release ]] || fatal "No se encontró /etc/os-release."

    # shellcheck disable=SC1091
    source /etc/os-release

    local arch_family=0

    [[ "${ID:-}" == "arch" ]] && arch_family=1
    [[ " ${ID_LIKE:-} " == *" arch "* ]] && arch_family=1

    (( arch_family )) || \
        fatal "Este instalador requiere Arch Linux o un derivado basado en Arch/pacman. Detectado: ${PRETTY_NAME:-desconocido}"

    command_exists pacman || fatal "pacman no está disponible."
    command_exists sudo || fatal "sudo no está instalado."
    command_exists git || fatal "git no está instalado."

    ok "Sistema: ${PRETTY_NAME:-Arch Linux}"
    ok "Usuario: $USER"
    ok "Repositorio local: $REPO_DIR"
}

prepare_sudo() {
    step "Verificando permisos administrativos"

    sudo -v || fatal "No se pudieron validar privilegios sudo."

    if (( ! DRY_RUN )); then
        (
            while true; do
                sleep 45
                sudo -n true 2>/dev/null || exit 0
            done
        ) &

        SUDO_KEEPALIVE_PID=$!
    fi

    ok "sudo disponible"
}

check_network() {
    step "Comprobando conectividad"

    if command_exists curl; then
        curl -fsS --max-time 10 https://archlinux.org/ >/dev/null || \
            fatal "No hay conectividad hacia archlinux.org."
    else
        warn "curl aún no está instalado; la conectividad se comprobará al descargar fuentes."
    fi

    ok "Conectividad disponible"
}

# -----------------------------------------------------------------------------
# Repository validation
# -----------------------------------------------------------------------------

validate_repo() {
    step "Validando estructura del rice"

    local required=(
        "$REPO_DIR/config"
        "$REPO_DIR/home"
        "$REPO_DIR/misc"
    )

    local item

    for item in "${required[@]}"; do
        [[ -e "$item" ]] || fatal "Falta en el repositorio: $item"
    done

    ok "Estructura del repositorio correcta"
}

# -----------------------------------------------------------------------------
# Pacman
# -----------------------------------------------------------------------------

pacman_installed() {
    pacman -Q "$1" >/dev/null 2>&1
}

pacman_available() {
    pacman -Si "$1" >/dev/null 2>&1
}

install_official_packages() {
    local requested=("$@")
    local available=()
    local unavailable=()
    local pkg

    for pkg in "${requested[@]}"; do
        if pacman_installed "$pkg"; then
            continue
        fi

        if pacman_available "$pkg"; then
            available+=("$pkg")
        else
            unavailable+=("$pkg")
        fi
    done

    if ((${#available[@]})); then
        root_run pacman -S --needed --noconfirm "${available[@]}"
    fi

    if ((${#unavailable[@]})); then
        warn "No encontrados en los repositorios configurados:"
        printf '  - %s\n' "${unavailable[@]}"

        printf '%s\n' "${unavailable[@]}" \
            > "$STATE_DIR/missing-packages.txt"
    fi
}

full_system_upgrade() {
    if (( NO_UPGRADE )); then
        warn "Se omitió la actualización completa (--no-upgrade)."
        return 0
    fi

    step "Sincronizando y actualizando Arch"

    root_run pacman -Syu --noconfirm
}

# -----------------------------------------------------------------------------
# Third-party source components
# -----------------------------------------------------------------------------

install_fzf_tab() {
    step "Instalando fzf-tab desde upstream (sin AUR)"

    local target="/usr/share/zsh/plugins/fzf-tab"

    if [[ -f "$target/fzf-tab.zsh" ]]; then
        ok "fzf-tab ya está instalado"
        return 0
    fi

    require_commands git

    local build_root="$STATE_DIR/fzf-tab-build"

    rm -rf -- "$build_root"
    mkdir -p "$build_root"

    git clone \
        --depth=1 \
        https://github.com/Aloxaf/fzf-tab.git \
        "$build_root/fzf-tab"

    root_run mkdir -p "$target"
    root_run cp -a "$build_root/fzf-tab/." "$target/"

    [[ -f "$target/fzf-tab.zsh" ]] || \
        fatal "fzf-tab no se instaló correctamente."

    ok "fzf-tab instalado en $target"
}

# -----------------------------------------------------------------------------
# Eww installation — FIXED
# -----------------------------------------------------------------------------

install_eww() {
    (( INSTALL_EWW )) || {
        warn "Eww omitido (--no-eww)."
        return 0
    }

    if command_exists eww; then
        ok "Eww ya está instalado: $(eww --version 2>/dev/null || echo instalado)"
        return 0
    fi

    step "Instalando Eww desde upstream"

    install_official_packages \
        base-devel \
        git \
        curl \
        rustup \
        pkgconf \
        gtk3 \
        pango \
        gdk-pixbuf2 \
        libdbusmenu-gtk3 \
        cairo \
        glib2 \
        gcc-libs \
        glibc

    require_commands git rustup

    local build_root="$STATE_DIR/eww-build"

    rm -rf -- "$build_root"
    mkdir -p "$build_root"

    info "Fuente: $EWW_REPO_URL"
    info "Referencia: $EWW_REF"
    info "Backend: X11"
    info "Rust toolchain: 1.76.0"

    git clone \
        --depth=1 \
        --branch "$EWW_REF" \
        "$EWW_REPO_URL" \
        "$build_root/eww"

    pushd "$build_root/eww" >/dev/null

    if ! rustup toolchain list | awk '{print $1}' | grep -qx '1.76.0'; then
        step "Instalando Rust 1.76.0 para Eww"

        rustup toolchain install 1.76.0
    fi

    unset RUSTUP_TOOLCHAIN || true

    step "Compilando Eww para X11"

    rustup run 1.76.0 \
        cargo build \
        --release \
        --no-default-features \
        --features x11

    [[ -x target/release/eww ]] || \
        fatal "La compilación de Eww terminó sin generar target/release/eww."

    step "Instalando binario de Eww"

    root_run install \
        -Dm755 \
        target/release/eww \
        /usr/local/bin/eww

    popd >/dev/null

    command_exists eww || \
        fatal "Eww se compiló, pero no aparece en PATH."

    ok "Eww instalado en /usr/local/bin/eww"
}

# -----------------------------------------------------------------------------
# Dependencies
# -----------------------------------------------------------------------------

install_dependencies() {
    step "Instalando dependencias del rice"

    install_official_packages \
        base-devel \
        git \
        curl \
        wget \
        rsync \
        unzip \
        7zip \
        jq \
        bc \
        imagemagick \
        xdg-utils \
        xdg-user-dirs \
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
        pipewire \
        pipewire-pulse \
        pipewire-alsa \
        wireplumber \
        pavucontrol \
        playerctl \
        \
        networkmanager \
        network-manager-applet \
        \
        thunar \
        thunar-volman \
        tumbler \
        gvfs \
        \
        kitty \
        geany \
        neovim \
        firefox \
        viewnior \
        mpv \
        yazi \
        maim \
        scrot \
        \
        zsh \
        fzf \
        eza \
        bat \
        htop \
        btop \
        reflector \
        mpd \
        ncmpcpp \
        zsh-autosuggestions \
        zsh-syntax-highlighting \
        zsh-history-substring-search \
        \
        gtk3 \
        gtk4 \
        lxappearance \
        papirus-icon-theme \
        \
        dbus \
        dbus-broker \
        polkit \
        polkit-gnome \
        \
        clipcat \
        \
        python-pywal \
        \
        noto-fonts \
        noto-fonts-emoji \
        ttf-dejavu \
        ttf-jetbrains-mono-nerd \
        ttf-firacode-nerd \
        ttf-nerd-fonts-symbols

    ok "Dependencias principales instaladas"
}

# -----------------------------------------------------------------------------
# Backup
# -----------------------------------------------------------------------------

backup_one() {
    local target="$1"

    [[ -e "$target" || -L "$target" ]] || return 0

    local relative

    if [[ "$target" == "$HOME_DIR/"* ]]; then
        relative="${target#$HOME_DIR/}"
    else
        relative="$(basename -- "$target")"
    fi

    mkdir -p "$BACKUP_DIR/$(dirname -- "$relative")"

    cp -a \
        -- "$target" \
        "$BACKUP_DIR/$relative"

    info "Backup: $target"
}

create_backup() {
    step "Creando respaldo de configuraciones"

    mkdir -p "$BACKUP_DIR"

    local targets=(
        "$HOME/.config/bspwm"
        "$HOME/.config/sxhkd"
        "$HOME/.config/polybar"
        "$HOME/.config/picom"
        "$HOME/.config/rofi"
        "$HOME/.config/jgmenu"
        "$HOME/.config/kitty"
        "$HOME/.config/dunst"
        "$HOME/.config/xsettingsd"
        "$HOME/.config/gtk-3.0"
        "$HOME/.config/gtk-4.0"
        "$HOME/.config/zsh"
        "$HOME/.config/eww"
        "$HOME/.xinitrc"
        "$HOME/.xprofile"
        "$HOME/.zshrc"
    )

    local target

    for target in "${targets[@]}"; do
        backup_one "$target"
    done

    cat > "$BACKUP_DIR/backup.info" <<INFO
TechOGR BSPWM backup
Date: $TIMESTAMP
Repository: $REPO_URL
Installer: $SCRIPT_VERSION
Host: $(hostname)
User: $USER
INFO

    ok "Backup creado: $BACKUP_DIR"
}

# -----------------------------------------------------------------------------
# Deploy dotfiles
# -----------------------------------------------------------------------------

deploy_directory() {
    local src="$1"
    local dest="$2"

    [[ -d "$src" ]] || return 0

    mkdir -p "$(dirname -- "$dest")"

    backup_one "$dest"

    mkdir -p "$dest"

    rsync \
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

    backup_one "$dest"

    install \
        -Dm644 \
        "$src" \
        "$dest"
}

deploy_directory_merge() {
    local src="$1"
    local dest="$2"

    [[ -d "$src" ]] || return 0

    mkdir -p "$dest"

    while IFS= read -r -d '' item; do
        local rel="${item#$src/}"
        local target="$dest/$rel"

        if [[ -d "$item" ]]; then
            mkdir -p "$target"
            continue
        fi

        backup_one "$target"

        mkdir -p "$(dirname -- "$target")"

        install \
            -Dm644 \
            "$item" \
            "$target"

    done < <(find "$src" -type f -print0)
}

install_dotfiles() {
    step "Instalando configuraciones de TechOGR"

    mkdir -p \
        "$CONFIG_DIR" \
        "$LOCAL_BIN" \
        "$LOCAL_SHARE/applications" \
        "$HOME/.local/share/fonts"

    local src
    local name

    shopt -s nullglob dotglob

    # -------------------------------------------------------------------------
    # ~/.config
    # -------------------------------------------------------------------------

    for src in "$REPO_DIR/config"/*; do
        [[ -d "$src" ]] || continue

        name="$(basename -- "$src")"

        deploy_directory \
            "$src" \
            "$CONFIG_DIR/$name"
    done

    # -------------------------------------------------------------------------
    # Home files
    # -------------------------------------------------------------------------

    for src in "$REPO_DIR/home"/.* "$REPO_DIR/home"/*; do
        [[ -e "$src" || -L "$src" ]] || continue

        name="$(basename -- "$src")"

        [[ "$name" != "." && "$name" != ".." ]] || continue

        if [[ -f "$src" || -L "$src" ]]; then
            deploy_file \
                "$src" \
                "$HOME/$name"
        fi
    done

    # -------------------------------------------------------------------------
    # ~/.local/bin
    # -------------------------------------------------------------------------

    if [[ -d "$REPO_DIR/misc/bin" ]]; then
        deploy_directory_merge \
            "$REPO_DIR/misc/bin" \
            "$LOCAL_BIN"
    fi

    # -------------------------------------------------------------------------
    # Applications
    # -------------------------------------------------------------------------

    if [[ -d "$REPO_DIR/misc/applications" ]]; then
        deploy_directory_merge \
            "$REPO_DIR/misc/applications" \
            "$LOCAL_SHARE/applications"
    fi

    # -------------------------------------------------------------------------
    # Fonts
    # -------------------------------------------------------------------------

    if [[ -d "$REPO_DIR/misc/fonts" ]]; then
        deploy_directory_merge \
            "$REPO_DIR/misc/fonts" \
            "$HOME/.local/share/fonts"
    fi

    # -------------------------------------------------------------------------
    # Wallpapers
    # -------------------------------------------------------------------------

    if [[ -d "$REPO_DIR/misc/wallpapers" ]]; then
        deploy_directory_merge \
            "$REPO_DIR/misc/wallpapers" \
            "$HOME/Wallpapers"

    elif [[ -d "$REPO_DIR/Wallpapers" ]]; then
        deploy_directory_merge \
            "$REPO_DIR/Wallpapers" \
            "$HOME/Wallpapers"
    fi

    shopt -u nullglob dotglob

    ok "Configuraciones desplegadas"
}

# -----------------------------------------------------------------------------
# Permissions
# -----------------------------------------------------------------------------

fix_permissions() {
    step "Aplicando permisos de ejecución"

    if [[ -d "$LOCAL_BIN" ]]; then
        find "$LOCAL_BIN" \
            -type f \
            -exec chmod +x {} +
    fi

    if [[ -f "$CONFIG_DIR/bspwm/bspwmrc" ]]; then
        chmod +x "$CONFIG_DIR/bspwm/bspwmrc" || true
    fi

    if [[ -d "$CONFIG_DIR/bspwm/bin" ]]; then
        chmod +x \
            "$CONFIG_DIR/bspwm/bin"/* \
            2>/dev/null || true
    fi

    if [[ -d "$CONFIG_DIR/polybar" ]]; then
        find "$CONFIG_DIR/polybar" \
            -type f \
            -name '*.sh' \
            -exec chmod +x {} + \
            2>/dev/null || true
    fi

    if [[ -d "$CONFIG_DIR/eww" ]]; then
        find "$CONFIG_DIR/eww" \
            -type f \
            -name '*.sh' \
            -exec chmod +x {} + \
            2>/dev/null || true
    fi

    ok "Permisos aplicados"
}

# -----------------------------------------------------------------------------
# Hardware-safe BSPWM monitor configuration
# -----------------------------------------------------------------------------

patch_bspwm_monitor() {
    local bspwmrc="$CONFIG_DIR/bspwm/bspwmrc"

    [[ -f "$bspwmrc" ]] || return 0

    if grep -Eq \
        '^[[:space:]]*xrandr --output Virtual-1 --mode 1920x1080 --rate 60[[:space:]]*$' \
        "$bspwmrc"; then

        step "Protegiendo configuración de monitor Virtual-1"

        backup_one "$bspwmrc"

        if (( DRY_RUN )); then

            info "Se convertiría la llamada fija de Virtual-1 en condicional."

        else

            sed -i \
                's@^[[:space:]]*xrandr --output Virtual-1 --mode 1920x1080 --rate 60[[:space:]]*$@if xrandr --query 2>/dev/null | grep -q "^Virtual-1 connected"; then xrandr --output Virtual-1 --mode 1920x1080 --rate 60; fi@' \
                "$bspwmrc"

            ok "Virtual-1 ahora solo se usa cuando existe."
        fi
    fi
}

# -----------------------------------------------------------------------------
# ZSH compatibility
# -----------------------------------------------------------------------------

patch_zsh_update_alias() {
    local zshrc="$HOME/.zshrc"

    [[ -f "$zshrc" ]] || return 0

    # Your current .zshrc uses paru for updates.
    # This installer deliberately avoids the AUR, so make the alias usable
    # on a fresh machine where paru is not installed.

    if ! command_exists paru &&
       grep -qE '^alias update="paru -Syu' "$zshrc"; then

        backup_one "$zshrc"

        sed -i \
            's/^alias update="paru -Syu[^"]*"/alias update="sudo pacman -Syu"/' \
            "$zshrc"

        ok "Alias 'update' ajustado a pacman porque paru no está instalado."
    fi
}

# -----------------------------------------------------------------------------
# X session
# -----------------------------------------------------------------------------

setup_x_session() {
    step "Configurando sesión X11/BSPWM"

    if [[ ! -e "$HOME/.xinitrc" ]]; then

        cat > "$HOME/.xinitrc" <<'EOF_XINITRC'
#!/bin/sh

export PATH="$HOME/.local/bin:$HOME/.config/bspwm/bin:$PATH"
export XDG_CURRENT_DESKTOP="bspwm"
export XDG_SESSION_DESKTOP="bspwm"

exec bspwm
EOF_XINITRC

        chmod +x "$HOME/.xinitrc"
    fi

    if [[ ! -e "$HOME/.xprofile" ]]; then

        cat > "$HOME/.xprofile" <<'EOF_XPROFILE'
#!/bin/sh

export PATH="$HOME/.local/bin:$HOME/.config/bspwm/bin:$PATH"
export XDG_CURRENT_DESKTOP="bspwm"
export XDG_SESSION_DESKTOP="bspwm"
EOF_XPROFILE
    fi

    local desktop_file="/usr/share/xsessions/bspwm.desktop"

    if [[ ! -e "$desktop_file" ]]; then

        local tmp

        tmp="$(mktemp)"

        cat > "$tmp" <<'EOF_DESKTOP'
[Desktop Entry]
Name=BSPWM
Comment=Binary space partitioning window manager
Exec=bspwm
TryExec=bspwm
Type=Application
DesktopNames=bspwm
EOF_DESKTOP

        root_run install \
            -Dm644 \
            "$tmp" \
            "$desktop_file"

        rm -f -- "$tmp"
    fi

    ok "Sesión BSPWM preparada"
}

# -----------------------------------------------------------------------------
# Services
# -----------------------------------------------------------------------------

setup_services() {

    if (( ENABLE_NETWORK )); then

        step "Habilitando NetworkManager"

        if command_exists systemctl; then

            root_run systemctl \
                enable \
                --now \
                NetworkManager.service

            ok "NetworkManager habilitado"

        else

            warn "systemctl no está disponible; NetworkManager quedó instalado pero no habilitado."
        fi
    fi

    if (( ENABLE_LIGHTDM )); then

        step "Configurando LightDM"

        install_official_packages \
            lightdm \
            lightdm-gtk-greeter

        if command_exists systemctl; then

            local active_dm=""
            local enabled_dm=""

            active_dm="$(
                systemctl is-active \
                    display-manager.service \
                    2>/dev/null || true
            )"

            enabled_dm="$(
                systemctl is-enabled \
                    display-manager.service \
                    2>/dev/null || true
            )"

            if [[ "$active_dm" == "active" ||
                  "$enabled_dm" == "enabled" ]]; then

                warn "Ya existe un display manager activo/habilitado. No se reemplazará."

            else

                root_run systemctl \
                    enable \
                    lightdm.service

                ok "LightDM habilitado"
            fi
        fi
    fi
}

# -----------------------------------------------------------------------------
# ZSH shell
# -----------------------------------------------------------------------------

setup_zsh() {

    if (( NO_SHELL )); then
        warn "Cambio de shell omitido (--no-shell)."
        return 0
    fi

    command_exists zsh || {
        warn "zsh no está disponible; se omite cambio de shell."
        return 0
    }

    local zsh_path
    local current_shell

    zsh_path="$(command -v zsh)"

    current_shell="$(
        getent passwd "$USER" |
        awk -F: '{print $7}'
    )"

    if [[ "$current_shell" == "$zsh_path" ]]; then
        ok "zsh ya es el shell de login"
        return 0
    fi

    step "Configurando zsh como shell de login"

    if (( DRY_RUN )); then

        info "Se ejecutaría: chsh -s $zsh_path $USER"

        return 0
    fi

    if chsh -s "$zsh_path" "$USER"; then

        ok "Shell de login cambiado a zsh"

    else

        warn "No se pudo cambiar el shell automáticamente."
        warn "Ejecuta: chsh -s $zsh_path"
    fi
}

# -----------------------------------------------------------------------------
# Fonts
# -----------------------------------------------------------------------------

refresh_fonts() {

    command_exists fc-cache || return 0

    step "Actualizando caché de fuentes"

    run fc-cache -f

    ok "Caché de fuentes actualizada"
}

# -----------------------------------------------------------------------------
# Validation
# -----------------------------------------------------------------------------

validate_installation() {

    step "Validando instalación"

    local required_files=(
        "$CONFIG_DIR/bspwm/bspwmrc"
        "$CONFIG_DIR/bspwm/config/sxhkdrc"
        "$CONFIG_DIR/polybar"
        "$CONFIG_DIR/picom"
        "$CONFIG_DIR/rofi"
        "$CONFIG_DIR/eww"
        "$HOME/.zshrc"
    )

    local file
    local failed=0

    for file in "${required_files[@]}"; do

        if [[ -e "$file" ]]; then

            ok "Existe: $file"

        else

            warn "Falta: $file"
            failed=1
        fi
    done

    local commands=(
        bspwm
        sxhkd
        polybar
        picom
        rofi
        jgmenu
        dunst
        kitty
        zsh
        nvim
        thunar
        eww
        clipcatd
    )

    local cmd

    for cmd in "${commands[@]}"; do

        if command_exists "$cmd"; then

            ok "Disponible: $cmd"

        else

            warn "No disponible: $cmd"
            failed=1
        fi
    done

    if (( failed )); then

        warn "La instalación terminó, pero hay componentes ausentes."
        warn "Revisa: $LOG_FILE"

    else

        ok "Validación completada sin componentes críticos faltantes."
    fi
}

# -----------------------------------------------------------------------------
# Final summary
# -----------------------------------------------------------------------------

print_summary() {

    printf '\n%b\n' \
        "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════════╗${RESET}"

    printf '%b\n' \
        "${GREEN}${BOLD}║                 INSTALACIÓN COMPLETADA                     ║${RESET}"

    printf '%b\n' \
        "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════════╝${RESET}"

    printf '\n'

    printf '  Rice:       TechOGR BSPWM\n'
    printf '  Config:     %s\n' "$CONFIG_DIR"
    printf '  Backup:     %s\n' "$BACKUP_DIR"
    printf '  Log:        %s\n' "$LOG_FILE"
    printf '  Eww:        /usr/local/bin/eww\n'

    printf '\n'

    printf '%b\n' \
        "${CYAN}${BOLD}Siguiente paso:${RESET}"

    printf '  Cierra sesión y selecciona BSPWM en tu display manager.\n'
    printf '  O ejecuta: startx\n'

    printf '\n'

    printf '%b\n' \
        "${YELLOW}Importante:${RESET}"

    printf '  El instalador no reemplaza un display manager existente.\n'
    printf '  LightDM solo se habilita con --enable-lightdm.\n'
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

main() {

    while (($#)); do

        case "$1" in

            --no-upgrade)
                NO_UPGRADE=1
                ;;

            --no-shell)
                NO_SHELL=1
                ;;

            --no-aur)
                NO_AUR=1
                ;;

            --enable-network)
                ENABLE_NETWORK=1
                ;;

            --enable-lightdm)
                ENABLE_LIGHTDM=1
                ;;

            --no-eww)
                INSTALL_EWW=0
                ;;

            --dry-run)
                DRY_RUN=1
                ;;

            -h|--help)
                usage
                exit 0
                ;;

            *)
                fatal "Opción desconocida: $1"
                ;;
        esac

        shift
    done

    print_banner

    check_environment
    prepare_sudo

    mkdir -p \
        "$STATE_DIR" \
        "$BACKUP_ROOT" \
        "$CONFIG_DIR" \
        "$LOCAL_BIN" \
        "$LOCAL_SHARE"

    validate_repo
    check_network

    full_system_upgrade

    install_dependencies

    install_fzf_tab

    # IMPORTANT:
    # Never use the broken/stale AUR `eww` package.
    install_eww

    create_backup

    install_dotfiles

    fix_permissions

    patch_bspwm_monitor

    setup_x_session

    setup_services

    setup_zsh

    patch_zsh_update_alias

    refresh_fonts

    validate_installation

    print_summary
}

main "$@"
