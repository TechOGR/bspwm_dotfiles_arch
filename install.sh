#!/usr/bin/env bash

# ============================================================
# TechOGR BSPWM Dotfiles
# Professional Arch Linux installer
#
# Repository:
# https://github.com/TechOGR/bspwm_dotfiles_arch
#
# Inspired by the installation architecture of:
# https://github.com/Gabryel8818/bspwm-rice
# ============================================================

set -Eeuo pipefail

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_NAME="bspwm_dotfiles_arch"

BACKUP_ROOT="${HOME}/.local/share/${REPO_NAME}/backups"
TIMESTAMP="$(date '+%Y%m%d-%H%M%S')"
BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"

CONFIG_DIR="${HOME}/.config"
LOCAL_BIN="${HOME}/.local/bin"
LOCAL_SHARE="${HOME}/.local/share"
FONT_DIR="${LOCAL_SHARE}/fonts"
APPLICATION_DIR="${LOCAL_SHARE}/applications"

# ------------------------------------------------------------
# Colors
# ------------------------------------------------------------

if command -v tput >/dev/null 2>&1 && [[ -t 1 ]]; then
    RED="$(tput setaf 1)"
    GREEN="$(tput setaf 2)"
    YELLOW="$(tput setaf 3)"
    BLUE="$(tput setaf 4)"
    MAGENTA="$(tput setaf 5)"
    CYAN="$(tput setaf 6)"
    BOLD="$(tput bold)"
    RESET="$(tput sgr0)"
else
    RED=""
    GREEN=""
    YELLOW=""
    BLUE=""
    MAGENTA=""
    CYAN=""
    BOLD=""
    RESET=""
fi

# ------------------------------------------------------------
# Output helpers
# ------------------------------------------------------------

info() {
    printf '%b[INFO]%b %s\n' "${BLUE}" "${RESET}" "$1"
}

success() {
    printf '%b[ OK ]%b %s\n' "${GREEN}" "${RESET}" "$1"
}

warning() {
    printf '%b[WARN]%b %s\n' "${YELLOW}" "${RESET}" "$1"
}

error() {
    printf '%b[ERR ]%b %s\n' "${RED}" "${RESET}" "$1" >&2
}

die() {
    error "$1"
    exit 1
}

section() {
    printf '\n%b━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━%b\n' \
        "${MAGENTA}" "${RESET}"
    printf '%b  %s%b\n' "${BOLD}${CYAN}" "$1" "${RESET}"
    printf '%b━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━%b\n' \
        "${MAGENTA}" "${RESET}"
}

pause() {
    sleep 0.5
}

# ------------------------------------------------------------
# Error handler
# ------------------------------------------------------------

on_error() {
    local exit_code=$?
    error "La instalación se detuvo debido a un error."
    error "Línea: ${BASH_LINENO[0]:-unknown}"
    error "Código: ${exit_code}"
    error "Si el problema continúa, ejecuta:"
    printf '    bash -x ./install.sh\n'
    exit "${exit_code}"
}

trap on_error ERR

# ------------------------------------------------------------
# Banner
# ------------------------------------------------------------

clear

printf '%b\n' "${CYAN}${BOLD}"
cat <<'EOF'
   _______        __    ____  ____  ____
  /_  __/ /  ___  / /_  / __ \/ __ \/ __ \
   / / / _ \/ _ \/ __ \/ / / / /_/ / / / /
  / / /  __/  __/ / / / /_/ / ____/ /_/ /
 /_/  \___/\___/_/ /_/_____/_/    \____/

          TechOGR BSPWM Dotfiles
EOF
printf '%b\n' "${RESET}"

printf '%bArch Linux • BSPWM • Polybar • Rofi • Picom • SXHKD%b\n\n' \
    "${BOLD}" "${RESET}"

# ------------------------------------------------------------
# Safety checks
# ------------------------------------------------------------

section "Comprobaciones iniciales"

if [[ "${EUID}" -eq 0 ]]; then
    die "No ejecutes este instalador como root ni con sudo."
fi

if [[ ! -d "${SCRIPT_DIR}" ]]; then
    die "No se pudo determinar el directorio del repositorio."
fi

if [[ ! -f "${SCRIPT_DIR}/install.sh" ]]; then
    die "El instalador debe ejecutarse desde el repositorio."
fi

if [[ ! -d "${SCRIPT_DIR}/config" ]]; then
    die "No existe el directorio config/."
fi

if [[ ! -d "${SCRIPT_DIR}/home" ]]; then
    die "No existe el directorio home/."
fi

if [[ ! -d "${SCRIPT_DIR}/misc" ]]; then
    die "No existe el directorio misc/."
fi

success "Estructura del repositorio detectada."

# ------------------------------------------------------------
# Detect operating system
# ------------------------------------------------------------

if [[ ! -r /etc/os-release ]]; then
    die "No se puede detectar el sistema operativo."
fi

# shellcheck disable=SC1091
source /etc/os-release

if [[ "${ID:-}" != "arch" ]] && [[ "${ID_LIKE:-}" != *"arch"* ]]; then
    die "Este instalador está diseñado para Arch Linux y derivados."
fi

success "Sistema compatible: ${PRETTY_NAME:-Arch Linux}"

# ------------------------------------------------------------
# Check sudo
# ------------------------------------------------------------

section "Comprobando privilegios"

if ! command -v sudo >/dev/null 2>&1; then
    die "sudo no está instalado."
fi

if ! sudo -v; then
    die "No se pudo obtener privilegios mediante sudo."
fi

success "sudo disponible."

# Keep sudo alive while installing.
(
    while true; do
        sudo -n true
        sleep 50
        kill -0 "$$" 2>/dev/null || exit
    done
) 2>/dev/null &
SUDO_KEEPALIVE_PID=$!

cleanup() {
    if [[ -n "${SUDO_KEEPALIVE_PID:-}" ]]; then
        kill "${SUDO_KEEPALIVE_PID}" 2>/dev/null || true
    fi
}

trap cleanup EXIT

# ------------------------------------------------------------
# Package management
# ------------------------------------------------------------

section "Dependencias"

PACMAN_PACKAGES=(
    bspwm
    sxhkd
    polybar
    rofi
    dunst
    picom
    kitty
    feh
    xclip
    brightnessctl
    libnotify
    xorg-xsetroot
    xorg-xrandr
    xorg-xprop
    xorg-xwininfo
    xorg-xkill
    xdotool
    maim
    jq
    playerctl
    thunar
    ranger
    neovim
    zsh
    git
    curl
    rsync
    unzip
    unzip
    p7zip
    base-devel
    ttf-jetbrains-mono-nerd
    ttf-jetbrains-mono
    papirus-icon-theme
    xdg-user-dirs
    xdg-utils
)

install_pacman_packages() {
    local missing=()

    for package in "${PACMAN_PACKAGES[@]}"; do
        if pacman -Qi "${package}" >/dev/null 2>&1; then
            printf '  %b✓%b %-30s\n' "${GREEN}" "${RESET}" "${package}"
        else
            missing+=("${package}")
        fi
    done

    if ((${#missing[@]} > 0)); then
        printf '\n%bInstalando paquetes faltantes:%b\n' \
            "${YELLOW}" "${RESET}"

        sudo pacman -S --needed --noconfirm "${missing[@]}"
    else
        success "Todas las dependencias principales ya están instaladas."
    fi
}

install_pacman_packages

# ------------------------------------------------------------
# Optional AUR helper
# ------------------------------------------------------------

section "AUR"

install_yay() {
    if command -v yay >/dev/null 2>&1; then
        success "yay ya está instalado."
        return
    fi

    warning "yay no está instalado."
    info "Instalando yay desde AUR..."

    local tmp_dir
    tmp_dir="$(mktemp -d)"

    git clone --depth=1 https://aur.archlinux.org/yay.git "${tmp_dir}/yay"

    (
        cd "${tmp_dir}/yay"
        makepkg -si --noconfirm
    )

    rm -rf "${tmp_dir}"

    command -v yay >/dev/null 2>&1 || \
        die "No se pudo instalar yay."

    success "yay instalado correctamente."
}

install_yay

# ------------------------------------------------------------
# Optional packages
# ------------------------------------------------------------

AUR_PACKAGES=(
    jgmenu
)

for package in "${AUR_PACKAGES[@]}"; do
    if yay -Qi "${package}" >/dev/null 2>&1; then
        printf '  %b✓%b %-30s\n' "${GREEN}" "${RESET}" "${package}"
    else
        info "Instalando AUR: ${package}"
        yay -S --needed --noconfirm "${package}"
    fi
done

# ------------------------------------------------------------
# Prepare directories
# ------------------------------------------------------------

section "Preparando directorios"

mkdir -p \
    "${CONFIG_DIR}" \
    "${LOCAL_BIN}" \
    "${LOCAL_SHARE}" \
    "${FONT_DIR}" \
    "${APPLICATION_DIR}" \
    "${BACKUP_DIR}"

success "Directorios preparados."

# ------------------------------------------------------------
# Backup system
# ------------------------------------------------------------

section "Backup"

info "Backup: ${BACKUP_DIR}"

backup_path() {
    local source="$1"

    if [[ ! -e "${source}" && ! -L "${source}" ]]; then
        return 0
    fi

    local relative

    if [[ "${source}" == "${HOME}/"* ]]; then
        relative="${source#${HOME}/}"
    else
        relative="$(basename "${source}")"
    fi

    local destination="${BACKUP_DIR}/${relative}"

    mkdir -p "$(dirname "${destination}")"

    cp -a "${source}" "${destination}"

    success "Backup: ${relative}"
}

# ------------------------------------------------------------
# Configurations that belong to BSPWM environment
# ------------------------------------------------------------

CONFIG_TARGETS=(
    bspwm
    sxhkd
    polybar
    rofi
    dunst
    picom
    kitty
    jgmenu
    ranger
    nvim
    mpd
    ncmpcpp
    alacritty
    btop
    cava
    gtk-3.0
    gtk-4.0
    xsettingsd
)

for target in "${CONFIG_TARGETS[@]}"; do
    if [[ -e "${CONFIG_DIR}/${target}" || -L "${CONFIG_DIR}/${target}" ]]; then
        backup_path "${CONFIG_DIR}/${target}"
    fi
done

backup_path "${HOME}/.zshrc"

# ------------------------------------------------------------
# Install config files
# ------------------------------------------------------------

section "Instalando configuraciones"

copy_config() {
    local source="$1"
    local destination="$2"

    if [[ ! -e "${source}" ]]; then
        warning "No existe: ${source}"
        return 0
    fi

    mkdir -p "${destination}"

    rsync -a \
        --exclude='.git/' \
        "${source}/" "${destination}/"

    success "Instalado: ${destination}"
}

# Copy the config tree while preserving the repository structure.
copy_config "${SCRIPT_DIR}/config" "${CONFIG_DIR}"

# ------------------------------------------------------------
# Install home files
# ------------------------------------------------------------

section "Instalando archivos de Home"

if [[ -f "${SCRIPT_DIR}/home/.zshrc" ]]; then
    cp -a "${SCRIPT_DIR}/home/.zshrc" "${HOME}/.zshrc"
    success "Instalado: ~/.zshrc"
else
    warning "No existe home/.zshrc"
fi

# ------------------------------------------------------------
# Install local scripts
# ------------------------------------------------------------

section "Instalando scripts"

if [[ -d "${SCRIPT_DIR}/misc/bin" ]]; then
    rsync -a \
        "${SCRIPT_DIR}/misc/bin/" \
        "${LOCAL_BIN}/"

    find "${LOCAL_BIN}" \
        -type f \
        -exec chmod +x {} \;

    success "Scripts instalados en ~/.local/bin"
else
    warning "No existe misc/bin"
fi

# ------------------------------------------------------------
# Install desktop applications
# ------------------------------------------------------------

section "Instalando aplicaciones .desktop"

if [[ -d "${SCRIPT_DIR}/misc/applications" ]]; then
    rsync -a \
        "${SCRIPT_DIR}/misc/applications/" \
        "${APPLICATION_DIR}/"

    success "Archivos .desktop instalados."
fi

# ------------------------------------------------------------
# Install fonts
# ------------------------------------------------------------

section "Instalando fuentes"

if [[ -d "${SCRIPT_DIR}/misc/fonts" ]]; then
    rsync -a \
        "${SCRIPT_DIR}/misc/fonts/" \
        "${FONT_DIR}/"

    if command -v fc-cache >/dev/null 2>&1; then
        fc-cache -f "${FONT_DIR}" >/dev/null 2>&1 || true
        success "Caché de fuentes actualizada."
    fi
else
    warning "No existe misc/fonts"
fi

# ------------------------------------------------------------
# Firefox files
# ------------------------------------------------------------

section "Firefox"

if [[ -d "${SCRIPT_DIR}/misc/firefox" ]]; then
    FIREFOX_DIR=""

    if command -v firefox >/dev/null 2>&1; then
        FIREFOX_PROFILE_DIR="$(
            find "${HOME}/.mozilla/firefox" \
                -maxdepth 1 \
                -type d \
                \( -name '*.default-release' -o -name '*.default' \) \
                -print -quit 2>/dev/null || true
        )"

        if [[ -n "${FIREFOX_PROFILE_DIR}" ]]; then
            backup_path "${FIREFOX_PROFILE_DIR}"
            rsync -a \
                "${SCRIPT_DIR}/misc/firefox/" \
                "${FIREFOX_PROFILE_DIR}/"

            success "Configuración de Firefox instalada."
        else
            warning "No se encontró un perfil de Firefox."
            warning "Se omitió la configuración de Firefox."
        fi
    else
        info "Firefox no está instalado; se omite."
    fi
fi

# ------------------------------------------------------------
# Permissions
# ------------------------------------------------------------

section "Permisos"

# BSPWM
if [[ -f "${CONFIG_DIR}/bspwm/bspwmrc" ]]; then
    chmod +x "${CONFIG_DIR}/bspwm/bspwmrc"
    success "bspwmrc marcado como ejecutable."
fi

# BSPWM scripts
if [[ -d "${CONFIG_DIR}/bspwm/bin" ]]; then
    find "${CONFIG_DIR}/bspwm/bin" \
        -type f \
        -exec chmod +x {} \;
    success "Scripts BSPWM configurados."
fi

# SXHKD
if [[ -f "${CONFIG_DIR}/sxhkd/sxhkdrc" ]]; then
    chmod 644 "${CONFIG_DIR}/sxhkd/sxhkdrc"
    success "sxhkd configurado."
fi

# Local scripts
if [[ -d "${LOCAL_BIN}" ]]; then
    find "${LOCAL_BIN}" \
        -type f \
        -exec chmod +x {} \;
fi

# ------------------------------------------------------------
# User directories
# ------------------------------------------------------------

section "Directorios XDG"

if command -v xdg-user-dirs-update >/dev/null 2>&1; then
    xdg-user-dirs-update
    success "Directorios XDG actualizados."
fi

# ------------------------------------------------------------
# PATH
# ------------------------------------------------------------

section "PATH"

SHELL_CONFIG=""

case "${SHELL:-}" in
    */zsh)
        SHELL_CONFIG="${HOME}/.zshrc"
        ;;
    */bash)
        SHELL_CONFIG="${HOME}/.bashrc"
        ;;
esac

PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'

if [[ -n "${SHELL_CONFIG}" && -f "${SHELL_CONFIG}" ]]; then
    if ! grep -Fqx "${PATH_LINE}" "${SHELL_CONFIG}"; then
        printf '\n# TechOGR BSPWM Dotfiles\n%s\n' \
            "${PATH_LINE}" >> "${SHELL_CONFIG}"

        success "Añadido ~/.local/bin al PATH."
    else
        success "~/.local/bin ya está en el PATH."
    fi
else
    warning "No se pudo detectar .zshrc/.bashrc."
fi

# ------------------------------------------------------------
# Shell
# ------------------------------------------------------------

section "Shell"

if command -v zsh >/dev/null 2>&1; then
    CURRENT_SHELL="$(getent passwd "${USER}" | cut -d: -f7)"

    if [[ "${CURRENT_SHELL}" != "$(command -v zsh)" ]]; then
        warning "Tu shell actual no es Zsh."

        read -rp \
            "¿Quieres establecer Zsh como shell predeterminada? [Y/n]: " \
            CHANGE_SHELL

        CHANGE_SHELL="${CHANGE_SHELL:-Y}"

        if [[ "${CHANGE_SHELL}" =~ ^[Yy]$ ]]; then
            chsh -s "$(command -v zsh)"
            success "Zsh configurado como shell predeterminada."
        else
            info "Se mantiene la shell actual."
        fi
    else
        success "Zsh ya es la shell predeterminada."
    fi
fi

# ------------------------------------------------------------
# Validate configuration
# ------------------------------------------------------------

section "Validación"

VALIDATION_FAILED=0

check_file() {
    local file="$1"

    if [[ -f "${file}" ]]; then
        success "${file}"
    else
        error "Falta: ${file}"
        VALIDATION_FAILED=1
    fi
}

check_file "${CONFIG_DIR}/bspwm/bspwmrc"
check_file "${CONFIG_DIR}/sxhkd/sxhkdrc"

if [[ -f "${CONFIG_DIR}/polybar/config.ini" ]] || \
   [[ -d "${CONFIG_DIR}/polybar" ]]; then
    success "Polybar"
else
    warning "No se encontró configuración de Polybar."
fi

if [[ -d "${CONFIG_DIR}/rofi" ]]; then
    success "Rofi"
else
    warning "No se encontró configuración de Rofi."
fi

if [[ -d "${CONFIG_DIR}/picom" ]]; then
    success "Picom"
else
    warning "No se encontró configuración de Picom."
fi

# ------------------------------------------------------------
# Syntax checks
# ------------------------------------------------------------

section "Comprobación de sintaxis"

if [[ -f "${CONFIG_DIR}/bspwm/bspwmrc" ]]; then
    if bash -n "${CONFIG_DIR}/bspwm/bspwmrc"; then
        success "bspwmrc: sintaxis correcta."
    else
        error "bspwmrc contiene errores de sintaxis."
        VALIDATION_FAILED=1
    fi
fi

if [[ -f "${CONFIG_DIR}/sxhkd/sxhkdrc" ]]; then
    success "sxhkdrc instalado."
fi

# ------------------------------------------------------------
# Final summary
# ------------------------------------------------------------

section "Instalación finalizada"

if [[ "${VALIDATION_FAILED}" -ne 0 ]]; then
    warning "La instalación terminó con advertencias."
    warning "Revisa los elementos marcados anteriormente."
else
    success "Todas las comprobaciones principales fueron exitosas."
fi

printf '\n'
printf '%bBackup:%b %s\n' "${CYAN}" "${RESET}" "${BACKUP_DIR}"
printf '%bConfig:%b %s\n' "${CYAN}" "${RESET}" "${CONFIG_DIR}"
printf '%bScripts:%b %s\n' "${CYAN}" "${RESET}" "${LOCAL_BIN}"

printf '\n%bSiguiente paso:%b\n' "${BOLD}${GREEN}" "${RESET}"
printf '  1. Cierra tu sesión gráfica.\n'
printf '  2. Selecciona BSPWM en tu display manager.\n'
printf '  3. Inicia sesión.\n'

printf '\n%bAtajos básicos esperados:%b\n' "${BOLD}${CYAN}" "${RESET}"
printf '  Super + Enter   → Terminal\n'
printf '  Super + D       → Rofi\n'
printf '  Super + Alt + R → Reiniciar BSPWM\n'
printf '  Super + Alt + Q → Salir de BSPWM\n'

printf '\n%b¡Gracias por usar TechOGR BSPWM Dotfiles!%b\n\n' \
    "${BOLD}${MAGENTA}" "${RESET}"
