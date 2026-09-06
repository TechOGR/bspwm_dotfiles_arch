#!/usr/bin/env bash
# =============================================================================
# TechOGR BSPWM Dotfiles Installer
# =============================================================================
# Repository:
#   https://github.com/TechOGR/bspwm_dotfiles_arch
#
# Goals:
#   - Arch Linux and Arch-based distributions
#   - Safe package installation with conflict handling
#   - Never install rust and rustup in the same pacman transaction
#   - Build Eww v0.6.0 with its upstream Rust toolchain (1.76.0)
#   - Never run cargo tree or mutate Cargo.lock
#   - Automatic backups before replacing dotfiles
#   - Hardware-safe BSPWM monitor setup
#   - Recoverable failures and detailed logs
# =============================================================================

set -Eeuo pipefail
IFS=$'\n\t'

readonly SCRIPT_VERSION="7.0.0"
readonly REPO_URL="https://github.com/TechOGR/bspwm_dotfiles_arch.git"
readonly EWW_REPO="https://github.com/elkowar/eww"
readonly EWW_VERSION="v0.6.0"
readonly EWW_TARBALL="https://github.com/elkowar/eww/archive/refs/tags/${EWW_VERSION}.tar.gz"
readonly EWW_RUST_VERSION="1.76.0"

readonly HOME_DIR="$HOME"
readonly CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}"
readonly DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}"
readonly STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/techogr-bspwm"
readonly BUILD_DIR="$STATE_DIR/build"
readonly LOCAL_BIN="$HOME/.local/bin"
readonly BACKUP_ROOT="$HOME/.RiceBackup"
readonly TIMESTAMP="$(date '+%Y-%m-%d_%H-%M-%S')"
readonly BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"
readonly LOG_FILE="$STATE_DIR/install-$TIMESTAMP.log"
readonly PACMAN_ERROR_FILE="$STATE_DIR/pacman-error-$TIMESTAMP.log"
readonly EWW_ERROR_FILE="$STATE_DIR/eww-build-$TIMESTAMP.log"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_DIR="$SCRIPT_DIR"

# Rust for Eww is installed directly from the official standalone Rust archive.
# The system Rust package is never modified.

SUDO_KEEPALIVE_PID=""
TEMP_DIR=""

DRY_RUN=0
NO_UPGRADE=0
NO_SHELL=0
NO_EWW=0
ENABLE_NETWORK=0
ENABLE_LIGHTDM=0

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
    error "Log: $LOG_FILE"
    exit 1
}

on_error() {
    local code=$?
    error "El instalador encontró un error no controlado."
    error "Línea: ${BASH_LINENO[0]:-desconocida}"
    error "Comando: ${BASH_COMMAND:-desconocido}"
    error "Código: $code"
    error "Log: $LOG_FILE"
    exit "$code"
}

trap on_error ERR

cleanup() {
    if [[ -n "$SUDO_KEEPALIVE_PID" ]]; then
        kill "$SUDO_KEEPALIVE_PID" 2>/dev/null || true
    fi

    if [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]]; then
        rm -rf -- "$TEMP_DIR"
    fi
}

trap cleanup EXIT

# -----------------------------------------------------------------------------
# UI / usage
# -----------------------------------------------------------------------------

print_banner() {
    printf '%b\n' "${MAGENTA}${BOLD}"
    printf '╔══════════════════════════════════════════════════════════════╗\n'
    printf '║                TECHOGR BSPWM DOTFILES                        ║\n'
    printf '║                    INSTALLER v%-26s║\n' "$SCRIPT_VERSION"
    printf '╚══════════════════════════════════════════════════════════════╝\n'
    printf '%b\n' "$RESET"
}

usage() {
    cat <<USAGE
Uso:
  ./install.sh [opciones]

Opciones:
  --no-upgrade        No ejecutar pacman -Syu.
  --no-shell          No cambiar el shell de login a zsh.
  --no-eww            No instalar Eww.
  --enable-network    Habilitar NetworkManager.
  --enable-lightdm    Instalar/activar LightDM si no hay otro display manager activo.
  --dry-run           Mostrar operaciones sin ejecutarlas.
  -h, --help          Mostrar esta ayuda.

Instalación normal:
  chmod +x install.sh
  ./install.sh
USAGE
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

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

pkg_installed() {
    pacman -Q "$1" >/dev/null 2>&1
}

pkg_available() {
    pacman -Si "$1" >/dev/null 2>&1
}

# -----------------------------------------------------------------------------
# Environment
# -----------------------------------------------------------------------------

check_environment() {
    step "Validando entorno"

    if (( EUID == 0 )); then
        fatal "Ejecuta este instalador como tu usuario normal, no como root."
    fi

    [[ -n "$HOME" ]] || fatal "HOME no está definido."
    [[ -r /etc/os-release ]] || fatal "No existe /etc/os-release."
    command_exists pacman || fatal "pacman no está instalado."
    command_exists sudo || fatal "sudo no está instalado."

    # shellcheck disable=SC1091
    source /etc/os-release

    local arch_family=0

    if [[ "${ID:-}" == "arch" ]]; then
        arch_family=1
    fi

    if [[ " ${ID_LIKE:-} " == *" arch "* ]]; then
        arch_family=1
    fi

    if (( arch_family == 0 )); then
        fatal "Se requiere Arch Linux o un derivado compatible con pacman. Detectado: ${PRETTY_NAME:-desconocido}"
    fi

    ok "Sistema: ${PRETTY_NAME:-Arch Linux}"
    ok "Usuario: $USER"
    ok "Arquitectura: $(uname -m)"
}

prepare_sudo() {
    step "Validando sudo"

    sudo -v || fatal "No se pudieron obtener privilegios sudo."

    if (( DRY_RUN == 0 )); then
        (
            while true; do
                sleep 45
                sudo -n true 2>/dev/null || exit 0
            done
        ) &
        SUDO_KEEPALIVE_PID=$!
    fi
}

bootstrap_tools() {
    step "Preparando herramientas del instalador"

    local wanted=()
    local pkg

    for pkg in pacman git curl rsync tar install awk sed grep find; do
        if command_exists "$pkg"; then
            continue
        fi

        case "$pkg" in
            pacman|install|awk|sed|grep|find)
                fatal "Falta una herramienta esencial del sistema: $pkg"
                ;;
            git|curl|rsync|tar)
                wanted+=("$pkg")
                ;;
        esac
    done

    if ((${#wanted[@]})); then
        pacman_install_safe "${wanted[@]}"
    fi

    command_exists git || fatal "git no está disponible."
    command_exists curl || fatal "curl no está disponible."
    command_exists rsync || fatal "rsync no está disponible."
    command_exists tar || fatal "tar no está disponible."
}

check_network() {
    step "Comprobando conectividad"

    if ! curl -fsS --max-time 12 https://archlinux.org/ >/dev/null; then
        fatal "No hay conectividad con archlinux.org."
    fi

    if ! curl -fsS --max-time 12 https://github.com/ >/dev/null; then
        fatal "No hay conectividad con GitHub."
    fi

    ok "Conectividad disponible"
}

validate_repo() {
    step "Validando repositorio"

    [[ -d "$REPO_DIR/config" ]] || fatal "No existe config/ en el repositorio."
    [[ -d "$REPO_DIR/home" ]] || fatal "No existe home/ en el repositorio."
    [[ -d "$REPO_DIR/misc" ]] || fatal "No existe misc/ en el repositorio."

    ok "Estructura del rice válida"
}

# -----------------------------------------------------------------------------
# Pacman installation with conflict recovery
# -----------------------------------------------------------------------------

extract_conflict_pairs() {
    local output="$1"
    local line left right

    while IFS= read -r line; do
        if [[ "$line" =~ ([A-Za-z0-9@._+:-]+)[[:space:]]+and[[:space:]]+([A-Za-z0-9@._+:-]+)[[:space:]]+are[[:space:]]+in[[:space:]]+conflict ]]; then
            left="${BASH_REMATCH[1]}"
            right="${BASH_REMATCH[2]}"
            printf '%s:%s\n' "$left" "$right"
            continue
        fi

        if [[ "$line" =~ ([A-Za-z0-9@._+:-]+)[[:space:]]+conflicts[[:space:]]+with[[:space:]]+([A-Za-z0-9@._+:-]+) ]]; then
            left="${BASH_REMATCH[1]}"
            right="${BASH_REMATCH[2]}"
            printf '%s:%s\n' "$left" "$right"
        fi
    done <<< "$output"
}

choose_conflict_action() {
    local left="$1"
    local right="$2"

    local left_installed=0
    local right_installed=0

    if pkg_installed "$left"; then
        left_installed=1
    fi

    if pkg_installed "$right"; then
        right_installed=1
    fi

    printf '\n'
    printf '%b\n' "${YELLOW}${BOLD}╔════════════════════════════════════════════════════════╗${RESET}"
    printf '%b\n' "${YELLOW}${BOLD}║                  CONFLICTO DE PACMAN                  ║${RESET}"
    printf '%b\n' "${YELLOW}${BOLD}╚════════════════════════════════════════════════════════╝${RESET}"
    printf '\n'
    printf 'Pacman detectó dos paquetes incompatibles:\n\n'
    printf '  [1] %-25s%s\n' "$left" "$([[ $left_installed == 1 ]] && printf '[INSTALADO]' || true)"
    printf '  [2] %-25s%s\n' "$right" "$([[ $right_installed == 1 ]] && printf '[INSTALADO]' || true)"
    printf '\n'

    if { [[ "$left" == "rust" ]] && [[ "$right" == "rustup" ]]; } ||
       { [[ "$left" == "rustup" ]] && [[ "$right" == "rust" ]]; }; then
        printf '%b\n' "${CYAN}${BOLD}Recomendación: conservar rust y no instalar rustup mediante pacman.${RESET}"
        printf 'El instalador usa un toolchain Rust privado para Eww y evita este conflicto.\n'
    elif (( left_installed == 1 && right_installed == 0 )); then
        printf '%b\n' "${CYAN}Recomendación: conservar $left porque ya está instalado.${RESET}"
    elif (( right_installed == 1 && left_installed == 0 )); then
        printf '%b\n' "${CYAN}Recomendación: conservar $right porque ya está instalado.${RESET}"
    else
        printf '%b\n' "${CYAN}Recomendación: no elimines nada si no conoces el propósito del paquete.${RESET}"
    fi

    printf '\n'

    while true; do
        printf '  [1] Eliminar %s y conservar/instalar %s\n' "$left" "$right"
        printf '  [2] Eliminar %s y conservar/instalar %s\n' "$right" "$left"
        printf '  [3] Cancelar instalación\n\n'

        read -r -p 'Selecciona [1/2/3]: ' choice

        case "$choice" in
            1)
                if pkg_installed "$left"; then
                    root_run pacman -Rns --noconfirm "$left"
                fi
                return 0
                ;;
            2)
                if pkg_installed "$right"; then
                    root_run pacman -Rns --noconfirm "$right"
                fi
                return 0
                ;;
            3)
                fatal "Instalación cancelada por el usuario."
                ;;
            *)
                warn "Opción inválida."
                ;;
        esac
    done
}

pacman_install_safe() {
    local requested=("$@")
    local available=()
    local missing=()
    local pkg
    local output
    local pairs
    local pair
    local left
    local right
    local attempts=0

    for pkg in "${requested[@]}"; do
        if pkg_installed "$pkg"; then
            continue
        fi

        if pkg_available "$pkg"; then
            available+=("$pkg")
        else
            missing+=("$pkg")
        fi
    done

    if ((${#missing[@]})); then
        warn "No encontrados en los repositorios configurados:"
        printf '  - %s\n' "${missing[@]}"
        printf '%s\n' "${missing[@]}" >> "$STATE_DIR/missing-packages.txt"
    fi

    if ((${#available[@]} == 0)); then
        return 0
    fi

    while (( attempts < 3 )); do
        attempts=$((attempts + 1))

        if output="$(sudo pacman -S --needed --noconfirm "${available[@]}" 2>&1)"; then
            printf '%s\n' "$output"
            return 0
        fi

        printf '%s\n' "$output"
        printf '%s\n' "$output" > "$PACMAN_ERROR_FILE"

        pairs="$(extract_conflict_pairs "$output" || true)"

        if [[ -n "$pairs" ]]; then
            while IFS= read -r pair; do
                [[ -n "$pair" ]] || continue

                left="${pair%%:*}"
                right="${pair#*:}"

                # The decision is made by the user. Nothing is removed blindly.
                choose_conflict_action "$left" "$right"
            done <<< "$pairs"

            continue
        fi

        warn "Pacman falló sin un conflicto que pueda resolver automáticamente."
        warn "No se eliminará ningún paquete a ciegas."
        fatal "No se pudo completar la instalación de paquetes. Revisa $PACMAN_ERROR_FILE"
    done

    fatal "Pacman sigue reportando un conflicto después de varios intentos. Revisa $PACMAN_ERROR_FILE"
}

# -----------------------------------------------------------------------------
# System update
# -----------------------------------------------------------------------------

full_upgrade() {
    if (( NO_UPGRADE == 1 )); then
        warn "Actualización completa omitida (--no-upgrade)."
        return 0
    fi

    step "Actualizando el sistema"

    local output

    if output="$(sudo pacman -Syu --noconfirm 2>&1)"; then
        printf '%s\n' "$output"
        ok "Sistema actualizado"
        return 0
    fi

    printf '%s\n' "$output"
    printf '%s\n' "$output" > "$PACMAN_ERROR_FILE"

    local pairs
    pairs="$(extract_conflict_pairs "$output" || true)"

    if [[ -n "$pairs" ]]; then
        local pair left right
        while IFS= read -r pair; do
            [[ -n "$pair" ]] || continue
            left="${pair%%:*}"
            right="${pair#*:}"
            choose_conflict_action "$left" "$right"
        done <<< "$pairs"

        if ! sudo pacman -Syu --noconfirm; then
            fatal "La actualización del sistema no pudo completarse. Revisa $PACMAN_ERROR_FILE"
        fi

        return 0
    fi

    fatal "pacman -Syu no pudo completarse. Revisa $PACMAN_ERROR_FILE"
}

# -----------------------------------------------------------------------------
# Dependencies
# -----------------------------------------------------------------------------

install_dependencies() {
    step "Instalando dependencias del rice"

    # IMPORTANT:
    # - rust is intentionally NOT here
    # - no Rust package is required here
    # Eww gets a dedicated isolated Rust toolchain below.
    # Eww gets its own standalone compiler below.

    pacman_install_safe \
        base-devel \
        git \
        curl \
        wget \
        rsync \
        tar \
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
        polkit \
        polkit-gnome \
        \
        clipcat \
        \
        python \
        python-pip \
        \
        noto-fonts \
        noto-fonts-emoji \
        ttf-dejavu \
        ttf-jetbrains-mono-nerd \
        ttf-firacode-nerd \
        ttf-nerd-fonts-symbols

    # pywal is currently an official Arch Extra package, but derivatives can
    # temporarily have stale/missing repositories. It is not allowed to abort
    # the complete rice installation.
    if pkg_available python-pywal; then
        pacman_install_safe python-pywal
    else
        warn "python-pywal no está disponible en los repositorios configurados."
        warn "La instalación continúa; el comando 'wal' puede faltar hasta instalar Pywal."
    fi

    ok "Dependencias principales procesadas"
}

# -----------------------------------------------------------------------------
# fzf-tab
# -----------------------------------------------------------------------------

install_fzf_tab() {
    step "Instalando fzf-tab desde upstream"

    local target="/usr/share/zsh/plugins/fzf-tab"
    local source_dir="$BUILD_DIR/fzf-tab"

    if [[ -f "$target/fzf-tab.zsh" ]]; then
        ok "fzf-tab ya está instalado"
        return 0
    fi

    rm -rf -- "$source_dir"
    mkdir -p "$BUILD_DIR"

    if ! git clone --depth=1 https://github.com/Aloxaf/fzf-tab.git "$source_dir"; then
        fatal "No se pudo descargar fzf-tab."
    fi

    root_run mkdir -p "$target"
    root_run rsync -a "$source_dir/" "$target/"

    [[ -f "$target/fzf-tab.zsh" ]] || fatal "fzf-tab no quedó instalado correctamente."

    ok "fzf-tab instalado"
}

# -----------------------------------------------------------------------------
# Private Rust toolchain / Eww
# -----------------------------------------------------------------------------

# Eww v0.6.0 was released with Rust 1.76.0. We install that exact standalone
# Standalone Rust distribution isolated under the user state directory.
# No rustup is used and the system Rust installation is never modified.

rust_target_triple() {
    case "$(uname -m)" in
        x86_64)
            printf '%s\n' 'x86_64-unknown-linux-gnu'
            ;;
        aarch64)
            printf '%s\n' 'aarch64-unknown-linux-gnu'
            ;;
        i686)
            printf '%s\n' 'i686-unknown-linux-gnu'
            ;;
        armv7l|armv7)
            printf '%s\n' 'armv7-unknown-linux-gnueabihf'
            ;;
        *)
            return 1
            ;;
    esac
}

install_private_rust() {
    local target
    local rust_root="$STATE_DIR/rust-$EWW_RUST_VERSION"
    local prefix="$rust_root/toolchain"
    local archive="$rust_root/rust-$EWW_RUST_VERSION.tar.xz"
    local extracted="$rust_root/source"
    local tar_root

    if [[ -x "$prefix/bin/cargo" && -x "$prefix/bin/rustc" ]]; then
        export EWW_CARGO="$prefix/bin/cargo"
        export EWW_RUSTC="$prefix/bin/rustc"
        ok "Rust privado $EWW_RUST_VERSION ya está instalado"
        return 0
    fi

    target="$(rust_target_triple)" || {
        fatal "Arquitectura $(uname -m) no está soportada para Rust $EWW_RUST_VERSION."
    }

    step "Instalando Rust $EWW_RUST_VERSION aislado para Eww"

    rm -rf -- "$rust_root"
    mkdir -p "$extracted"

    local url="https://static.rust-lang.org/dist/rust-${EWW_RUST_VERSION}-${target}.tar.xz"

    info "Descargando: $url"

    if ! curl -fL --retry 5 --retry-delay 2 \
        --connect-timeout 15 \
        --max-time 1200 \
        "$url" \
        -o "$archive"; then
        fatal "No se pudo descargar Rust $EWW_RUST_VERSION para $target."
    fi

    [[ -s "$archive" ]] || fatal "El archivo de Rust descargado está vacío."

    step "Extrayendo Rust $EWW_RUST_VERSION"

    tar -xJf "$archive" -C "$extracted"

    tar_root="$(find "$extracted" -mindepth 1 -maxdepth 1 -type d -name 'rust-*' -print -quit)"

    [[ -n "$tar_root" && -d "$tar_root" ]] || {
        fatal "No se pudo localizar el árbol de Rust $EWW_RUST_VERSION después de extraerlo."
    }

    [[ -x "$tar_root/install.sh" ]] || {
        fatal "El paquete de Rust no contiene su instalador oficial."
    }

    step "Instalando Rust en $prefix"

    # The official standalone installer supports a user-owned prefix and does
    # The system Rust installation is not modified.
    if ! (cd "$tar_root" && ./install.sh \
        --prefix="$prefix" \
        --disable-ldconfig \
        --without=rust-docs); then
        fatal "No se pudo instalar el toolchain privado Rust $EWW_RUST_VERSION."
    fi

    rm -f -- "$archive"

    [[ -x "$prefix/bin/cargo" ]] || fatal "No se encontró cargo tras instalar Rust $EWW_RUST_VERSION."
    [[ -x "$prefix/bin/rustc" ]] || fatal "No se encontró rustc tras instalar Rust $EWW_RUST_VERSION."

    export EWW_CARGO="$prefix/bin/cargo"
    export EWW_RUSTC="$prefix/bin/rustc"

    ok "Rust $EWW_RUST_VERSION instalado sin rustup"
}

prepare_eww_rust() {
    step "Preparando toolchain para Eww"

    # Do not use the system Rust. The standalone toolchain is isolated and
    # selected only for this Eww build.
    install_private_rust

    local actual
    actual="$($EWW_RUSTC --version 2>/dev/null || true)"

    [[ "$actual" == rustc\ $EWW_RUST_VERSION* ]] || {
        fatal "El rustc privado no corresponde a Rust $EWW_RUST_VERSION: ${actual:-desconocido}"
    }

    ok "Toolchain Eww: $actual"
}

# -----------------------------------------------------------------------------
# Eww source
# -----------------------------------------------------------------------------

prepare_eww_source() {
    local source_root="$BUILD_DIR/eww"
    local archive="$BUILD_DIR/eww-${EWW_VERSION}.tar.gz"
    local extract_root="$BUILD_DIR/eww-source"

    rm -rf -- "$source_root" "$extract_root"
    mkdir -p "$BUILD_DIR" "$extract_root"

    step "Descargando Eww $EWW_VERSION"

    if ! curl -fL --retry 5 --retry-delay 2 \
        --connect-timeout 15 \
        --max-time 1200 \
        "$EWW_TARBALL" \
        -o "$archive"; then
        fatal "No se pudo descargar Eww $EWW_VERSION."
    fi

    [[ -s "$archive" ]] || fatal "El archivo de Eww descargado está vacío."

    tar -xzf "$archive" -C "$extract_root"

    local extracted
    extracted="$(find "$extract_root" -mindepth 1 -maxdepth 1 -type d -print -quit)"

    [[ -n "$extracted" && -d "$extracted" ]] || {
        fatal "No se pudo extraer Eww $EWW_VERSION."
    }

    mv -- "$extracted" "$source_root"
    rm -f -- "$archive"

    [[ -f "$source_root/Cargo.lock" ]] || fatal "Eww $EWW_VERSION no contiene Cargo.lock."
    [[ -f "$source_root/rust-toolchain.toml" ]] || fatal "Eww $EWW_VERSION no contiene rust-toolchain.toml."
    [[ -f "$source_root/Cargo.toml" ]] || fatal "Eww $EWW_VERSION no contiene Cargo.toml."

    ok "Fuente Eww $EWW_VERSION preparada"
}

build_eww() {
    local source_root="$BUILD_DIR/eww"

    [[ -d "$source_root" ]] || fatal "No existe el árbol fuente de Eww."
    [[ -x "${EWW_CARGO:-}" ]] || fatal "Cargo privado de Eww no está disponible."
    [[ -x "${EWW_RUSTC:-}" ]] || fatal "Rustc privado de Eww no está disponible."

    step "Compilando Eww $EWW_VERSION para X11"

    : > "$EWW_ERROR_FILE"

    pushd "$source_root" >/dev/null

    info "Rust: $($EWW_RUSTC --version)"
    info "Cargo: $($EWW_CARGO --version)"
    info "Cargo.lock oficial: sí"
    info "Modo locked: sí"
    info "Backend: x11"

    # Completely isolate Cargo/Rust from the user's global toolchain.
    export PATH="$(dirname "$EWW_CARGO"):$PATH"
    export RUSTC="$EWW_RUSTC"
    export CARGO="$EWW_CARGO"

    # Keep Cargo's cache in the installer state directory. This makes the
    # installer resumable without polluting ~/.cargo with the legacy toolchain.
    export CARGO_HOME="$STATE_DIR/cargo"
    mkdir -p "$CARGO_HOME"

    # Eww v0.6.0 already ships a tested lockfile. Never update it here.
    if "$EWW_CARGO" build \
        --release \
        --locked \
        --no-default-features \
        --features x11 \
        >"$EWW_ERROR_FILE" 2>&1; then
        popd >/dev/null
        ok "Eww compilado correctamente"
        return 0
    fi

    popd >/dev/null

    warn "La compilación de Eww falló."
    warn "Log: $EWW_ERROR_FILE"

    # No speculative cargo-tree/cargo-update logic. Print the useful tail so the
    # actual compiler failure is visible immediately, while keeping the full log.
    printf '\n%b\n' "${YELLOW}----- Últimas líneas del error de Eww -----${RESET}"
    tail -n 80 "$EWW_ERROR_FILE" || true
    printf '%b\n\n' "${YELLOW}-------------------------------------------${RESET}"

    fatal "No se pudo compilar Eww $EWW_VERSION con Rust $EWW_RUST_VERSION."
}

install_eww() {
    if (( NO_EWW == 1 )); then
        warn "Eww omitido (--no-eww)."
        return 0
    fi

    step "Instalando Eww $EWW_VERSION"

    if command_exists eww; then
        local existing
        existing="$(eww --version 2>/dev/null || true)"
        ok "Eww ya está instalado: ${existing:-desconocido}"
        return 0
    fi

    prepare_eww_rust
    prepare_eww_source
    build_eww

    local binary="$BUILD_DIR/eww/target/release/eww"

    [[ -x "$binary" ]] || fatal "La compilación finalizó sin generar Eww."

    root_run install -Dm755 "$binary" /usr/local/bin/eww

    command_exists eww || fatal "Eww no aparece en PATH después de la instalación."

    local installed_version
    installed_version="$(eww --version 2>/dev/null || true)"

    ok "Eww instalado: ${installed_version:-$EWW_VERSION}"
}

# -----------------------------------------------------------------------------
# Backup / dotfiles
# -----------------------------------------------------------------------------

backup_one() {
    local target="$1"

    if [[ ! -e "$target" && ! -L "$target" ]]; then
        return 0
    fi

    local relative

    case "$target" in
        "$HOME_DIR"/*)
            relative="${target#"$HOME_DIR/"}"
            ;;
        *)
            relative="${target#/}"
            ;;
    esac

    local backup_target="$BACKUP_DIR/$relative"

    if [[ -e "$backup_target" || -L "$backup_target" ]]; then
        return 0
    fi

    mkdir -p "$(dirname -- "$backup_target")"
    cp -a -- "$target" "$backup_target"
}

backup_repo_config_entries() {
    local entry name

    shopt -s nullglob dotglob
    for entry in "$REPO_DIR/config"/*; do
        name="$(basename -- "$entry")"
        if [[ -e "$CONFIG_DIR/$name" || -L "$CONFIG_DIR/$name" ]]; then
            backup_one "$CONFIG_DIR/$name"
        fi
    done
    shopt -u nullglob dotglob
}

create_backup() {
    step "Creando backup antes de modificar configuraciones"

    mkdir -p "$BACKUP_DIR"

    # The repository mirrors ~/.config recursively. Back up every top-level
    # entry that this repository can replace, including nested paths such as:
    #   config/bspwm/eww      -> ~/.config/bspwm/eww
    #   config/bspwm/rices    -> ~/.config/bspwm/rices
    #   config/bspwm/config   -> ~/.config/bspwm/config
    backup_repo_config_entries

    local home_item
    shopt -s nullglob dotglob
    for home_item in "$REPO_DIR/home"/.* "$REPO_DIR/home"/*; do
        [[ -e "$home_item" || -L "$home_item" ]] || continue
        case "$(basename -- "$home_item")" in
            .|..) continue ;;
        esac
        if [[ -e "$HOME/$(basename -- "$home_item")" || -L "$HOME/$(basename -- "$home_item")" ]]; then
            backup_one "$HOME/$(basename -- "$home_item")"
        fi
    done
    shopt -u nullglob dotglob

    cat > "$BACKUP_DIR/backup.info" <<INFO
TechOGR BSPWM backup
Date: $TIMESTAMP
Installer: $SCRIPT_VERSION
Repository: $REPO_URL
Host: $(hostname)
User: $USER
INFO

    ok "Backup creado en $BACKUP_DIR"
}

deploy_config_tree() {
    local src="$REPO_DIR/config"
    local dest="$CONFIG_DIR"
    local entry name

    [[ -d "$src" ]] || fatal "No existe config/ en el repositorio."

    mkdir -p "$dest"

    shopt -s nullglob dotglob
    for entry in "$src"/*; do
        name="$(basename -- "$entry")"

        if [[ -d "$entry" ]]; then
            mkdir -p "$dest/$name"
            rsync -a -- "$entry/" "$dest/$name/"
        elif [[ -f "$entry" || -L "$entry" ]]; then
            install -Dm644 "$entry" "$dest/$name"
        fi
    done
    shopt -u nullglob dotglob
}

deploy_home_tree() {
    local src
    local name

    shopt -s nullglob dotglob
    for src in "$REPO_DIR/home"/.* "$REPO_DIR/home"/*; do
        [[ -e "$src" || -L "$src" ]] || continue

        name="$(basename -- "$src")"
        [[ "$name" != "." && "$name" != ".." ]] || continue

        if [[ -f "$src" || -L "$src" ]]; then
            install -Dm644 "$src" "$HOME/$name"
        elif [[ -d "$src" ]]; then
            mkdir -p "$HOME/$name"
            rsync -a -- "$src/" "$HOME/$name/"
        fi
    done
    shopt -u nullglob dotglob
}

deploy_merge() {
    local src="$1"
    local dest="$2"

    [[ -d "$src" ]] || return 0

    mkdir -p "$dest"

    # Merge without --delete. The repository owns only the files it ships;
    # unrelated user files are never removed by the installer.
    rsync -a -- "$src/" "$dest/"
}

install_dotfiles() {
    step "Instalando la estructura real del repositorio"

    mkdir -p \
        "$CONFIG_DIR" \
        "$LOCAL_BIN" \
        "$DATA_DIR/applications" \
        "$DATA_DIR/fonts"

    # IMPORTANT: config/ maps 1:1 to ~/.config.
    # This is the key layout of this repository.
    # Therefore config/bspwm/eww becomes ~/.config/bspwm/eww,
    # NOT ~/.config/eww.
    deploy_config_tree

    deploy_home_tree

    if [[ -d "$REPO_DIR/misc/bin" ]]; then
        deploy_merge "$REPO_DIR/misc/bin" "$LOCAL_BIN"
    fi

    if [[ -d "$REPO_DIR/misc/applications" ]]; then
        deploy_merge "$REPO_DIR/misc/applications" "$DATA_DIR/applications"
    fi

    if [[ -d "$REPO_DIR/misc/fonts" ]]; then
        deploy_merge "$REPO_DIR/misc/fonts" "$DATA_DIR/fonts"
    fi

    # The repository currently stores wallpapers at the root: Wallpapers/.
    # Keep misc/wallpapers supported too for future changes.
    if [[ -d "$REPO_DIR/Wallpapers" ]]; then
        deploy_merge "$REPO_DIR/Wallpapers" "$HOME/Wallpapers"
    elif [[ -d "$REPO_DIR/misc/wallpapers" ]]; then
        deploy_merge "$REPO_DIR/misc/wallpapers" "$HOME/Wallpapers"
    fi

    ok "Configuraciones instaladas respetando la estructura del repositorio"
}

# -----------------------------------------------------------------------------
# Permissions / hardware safety
# -----------------------------------------------------------------------------

fix_permissions() {
    step "Aplicando permisos de ejecución"

    if [[ -d "$LOCAL_BIN" ]]; then
        find "$LOCAL_BIN" -type f -exec chmod +x {} +
    fi

    # All executable BSPWM helper scripts live under ~/.config/bspwm/bin.
    if [[ -d "$CONFIG_DIR/bspwm/bin" ]]; then
        find "$CONFIG_DIR/bspwm/bin" -type f -exec chmod +x {} +
    fi

    [[ -f "$CONFIG_DIR/bspwm/bspwmrc" ]] && chmod +x "$CONFIG_DIR/bspwm/bspwmrc"

    # Bar.bash scripts are sourced by Theme.sh, not executed directly, but
    # executable permission is harmless and keeps the shipped rice usable.
    if [[ -d "$CONFIG_DIR/bspwm/rices" ]]; then
        find "$CONFIG_DIR/bspwm/rices" \
            -type f \
            \( -name '*.sh' -o -name '*.bash' \) \
            -exec chmod +x {} +
    fi

    # Eww helper scripts, when present, are executable.
    if [[ -d "$CONFIG_DIR/bspwm/eww" ]]; then
        find "$CONFIG_DIR/bspwm/eww" \
            -type f -name '*.sh' \
            -exec chmod +x {} + 2>/dev/null || true
    fi

    ok "Permisos aplicados"
}

patch_virtual_monitor() {
    local file="$CONFIG_DIR/bspwm/bspwmrc"

    [[ -f "$file" ]] || return 0

    if grep -Eq '^[[:space:]]*xrandr --output Virtual-1 --mode 1920x1080 --rate 60[[:space:]]*$' "$file"; then
        step "Haciendo segura la configuración Virtual-1"

        sed -i \
            's@^[[:space:]]*xrandr --output Virtual-1 --mode 1920x1080 --rate 60[[:space:]]*$@if xrandr --query 2>/dev/null | grep -q "^Virtual-1 connected"; then xrandr --output Virtual-1 --mode 1920x1080 --rate 60; fi@' \
            "$file"

        ok "Virtual-1 ahora es condicional"
    fi
}

# -----------------------------------------------------------------------------
# X session
# -----------------------------------------------------------------------------

setup_x_session() {
    step "Preparando sesión X11/BSPWM"

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

        root_run install -Dm644 "$tmp" "$desktop_file"
        rm -f -- "$tmp"
    fi

    ok "Sesión BSPWM preparada"
}

# -----------------------------------------------------------------------------
# Services
# -----------------------------------------------------------------------------

setup_services() {
    if (( ENABLE_NETWORK == 1 )); then
        step "Habilitando NetworkManager"

        if command_exists systemctl; then
            root_run systemctl enable --now NetworkManager.service
            ok "NetworkManager habilitado"
        else
            warn "systemctl no está disponible; NetworkManager quedó instalado sin habilitarse."
        fi
    fi

    if (( ENABLE_LIGHTDM == 1 )); then
        step "Configurando LightDM"

        pacman_install_safe lightdm lightdm-gtk-greeter

        if command_exists systemctl; then
            local active
            local enabled

            active="$(systemctl is-active display-manager.service 2>/dev/null || true)"
            enabled="$(systemctl is-enabled display-manager.service 2>/dev/null || true)"

            if [[ "$active" == "active" || "$enabled" == "enabled" ]]; then
                warn "Ya existe un display manager activo/habilitado. No se reemplazará."
            else
                root_run systemctl enable lightdm.service
                ok "LightDM habilitado"
            fi
        fi
    fi
}

# -----------------------------------------------------------------------------
# Shell
# -----------------------------------------------------------------------------

setup_zsh() {
    if (( NO_SHELL == 1 )); then
        warn "Cambio de shell omitido (--no-shell)."
        return 0
    fi

    if ! command_exists zsh; then
        warn "zsh no está disponible."
        return 0
    fi

    local zsh_path
    local current

    zsh_path="$(command -v zsh)"
    current="$(getent passwd "$USER" | awk -F: '{print $7}')"

    if [[ "$current" == "$zsh_path" ]]; then
        ok "zsh ya es el shell de login"
        return 0
    fi

    step "Configurando zsh como shell de login"

    if chsh -s "$zsh_path" "$USER"; then
        ok "Shell cambiado a zsh"
    else
        warn "No se pudo cambiar automáticamente el shell. Ejecuta: chsh -s $zsh_path"
    fi
}

patch_zsh_update_alias() {
    local zshrc="$HOME/.zshrc"

    [[ -f "$zshrc" ]] || return 0

    # Avoid breaking an existing user configuration. We only replace an alias
    # that explicitly depends on paru when paru is not installed.
    if command_exists paru; then
        return 0
    fi

    if grep -qE '^alias update="paru -Syu' "$zshrc"; then
        step "Eliminando dependencia innecesaria de paru en el alias update"

        sed -i \
            's/^alias update="paru -Syu[^\"]*"/alias update="sudo pacman -Syu"/' \
            "$zshrc"

        ok "Alias update ajustado a pacman"
    fi
}

# -----------------------------------------------------------------------------
# Fonts
# -----------------------------------------------------------------------------

refresh_fonts() {
    if ! command_exists fc-cache; then
        return 0
    fi

    step "Actualizando caché de fuentes"
    fc-cache -f
    ok "Caché de fuentes actualizado"
}

# -----------------------------------------------------------------------------
# Final validation
# -----------------------------------------------------------------------------

validate_installation() {
    step "Validando instalación contra la estructura real del repositorio"

    local required_paths=(
        "$CONFIG_DIR/bspwm/bspwmrc"
        "$CONFIG_DIR/bspwm/bin"
        "$CONFIG_DIR/bspwm/config/sxhkdrc"
        "$CONFIG_DIR/bspwm/config/picom/picom.conf"
        "$CONFIG_DIR/bspwm/config/rofi-themes"
        "$CONFIG_DIR/bspwm/eww"
        "$CONFIG_DIR/bspwm/eww/eww.yuck"
        "$CONFIG_DIR/bspwm/rices"
        "$CONFIG_DIR/bspwm/rices/emilia"
        "$CONFIG_DIR/bspwm/rices/emilia/Bar.bash"
        "$CONFIG_DIR/bspwm/rices/emilia/config.ini"
        "$CONFIG_DIR/bspwm/.rice"
        "$HOME/.zshrc"
        "$HOME/Wallpapers"
    )

    local failed=0
    local item

    for item in "${required_paths[@]}"; do
        if [[ -e "$item" ]]; then
            ok "Existe: $item"
        else
            warn "Falta: $item"
            failed=1
        fi
    done

    # Verify the actual repository layout instead of looking for directories
    # that this repo does not contain (for example ~/.config/eww or ~/.config/polybar).
    if [[ -d "$CONFIG_DIR/bspwm/eww" ]]; then
        ok "Eww config: $CONFIG_DIR/bspwm/eww"
    fi

    if [[ -d "$CONFIG_DIR/bspwm/rices" ]]; then
        ok "Rices: $CONFIG_DIR/bspwm/rices"
    fi

    if [[ -f "$CONFIG_DIR/bspwm/rices/emilia/config.ini" ]]; then
        ok "Polybar config: $CONFIG_DIR/bspwm/rices/emilia/config.ini"
    fi

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
        clipcatd
    )

    if (( NO_EWW == 0 )); then
        commands+=(eww)
    fi

    local cmd
    for cmd in "${commands[@]}"; do
        if command_exists "$cmd"; then
            ok "Disponible: $cmd"
        else
            warn "Falta comando: $cmd"
            failed=1
        fi
    done

    if command_exists wal; then
        ok "Disponible: wal (Pywal)"
    else
        warn "wal no está disponible; Pywal puede requerir instalación separada en este sistema."
    fi

    if (( failed == 0 )); then
        ok "Validación principal completada correctamente"
    else
        warn "La estructura del rice no quedó completa. Revisa $LOG_FILE"
        return 1
    fi
}

# -----------------------------------------------------------------------------
# Summary
# -----------------------------------------------------------------------------

print_summary() {
    printf '\n%b\n' "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════════╗${RESET}"
    printf '%b\n' "${GREEN}${BOLD}║                  INSTALACIÓN COMPLETADA                     ║${RESET}"
    printf '%b\n' "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════════╝${RESET}"
    printf '\n'
    printf '  Rice:       TechOGR BSPWM\n'
    printf '  Config:     %s\n' "$CONFIG_DIR"
    printf '  Backup:     %s\n' "$BACKUP_DIR"
    printf '  Log:        %s\n' "$LOG_FILE"
    printf '  Eww log:    %s\n' "$EWW_ERROR_FILE"
    printf '\n'
    printf '%b\n' "${CYAN}${BOLD}Siguiente paso:${RESET}"
    printf '  Cierra sesión y selecciona BSPWM en tu display manager.\n'
    printf '  O utiliza: startx\n'
    printf '\n'
    printf '%b\n' "${YELLOW}Nota:${RESET}"
    printf '  El instalador no reemplaza un display manager existente.\n'
    printf '  Para NetworkManager: ./install.sh --enable-network\n'
    printf '  Para LightDM:        ./install.sh --enable-lightdm\n'
    printf '  Para omitir update:  ./install.sh --no-upgrade\n'
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
            --no-eww)
                NO_EWW=1
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
                fatal "Opción desconocida: $1"
                ;;
        esac
        shift
    done

    print_banner

    check_environment
    prepare_sudo
    bootstrap_tools
    check_network
    validate_repo
    full_upgrade
    install_dependencies
    install_fzf_tab
    install_eww
    create_backup
    install_dotfiles
    fix_permissions
    patch_virtual_monitor
    setup_x_session
    setup_services
    setup_zsh
    patch_zsh_update_alias
    refresh_fonts
    validate_installation
    print_summary
}

main "$@"
