#!/usr/bin/env bash
# =============================================================================
# TechOGR BSPWM Dotfiles Installer
# v3.0.0
# https://github.com/TechOGR/bspwm_dotfiles_arch
#
# Arch Linux / Arch-based distributions
# =============================================================================

set -Eeuo pipefail
IFS=$'\n\t'

SCRIPT_VERSION="3.1.0"
REPO_URL="https://github.com/TechOGR/bspwm_dotfiles_arch.git"
EWW_REPO_URL="https://github.com/elkowar/eww.git"
EWW_REF="v0.6.0"

HOME_DIR="$HOME"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}"
LOCAL_BIN="${XDG_BIN_HOME:-$HOME/.local/bin}"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/techogr-bspwm"
BACKUP_ROOT="$HOME/.RiceBackup"
TIMESTAMP="$(date '+%Y-%m-%d_%H-%M-%S')"
BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"
LOG_FILE="$STATE_DIR/install-$TIMESTAMP.log"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_DIR="$SCRIPT_DIR"
BUILD_DIR="$STATE_DIR/build"

DRY_RUN=0
NO_UPGRADE=0
NO_SHELL=0
NO_EWW=0
ENABLE_NETWORK=0
ENABLE_LIGHTDM=0

TEMP_DIR=""
SUDO_KEEPALIVE_PID=""

# ----------------------------------------------------------------------------
# Colors
# ----------------------------------------------------------------------------
RESET='\033[0m'
BOLD='\033[1m'
RED='\033[31m'
GREEN='\033[32m'
YELLOW='\033[33m'
BLUE='\033[34m'
CYAN='\033[36m'
MAGENTA='\033[35m'
WHITE='\033[97m'

mkdir -p "$STATE_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

# ----------------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------------
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
    error "Falló el comando en la línea ${BASH_LINENO[0]:-unknown}."
    error "Comando: ${BASH_COMMAND:-unknown}"
    error "Código de salida: $code"
    error "Log: $LOG_FILE"
    exit "$code"
}
trap on_error ERR

cleanup() {
    [[ -n "$SUDO_KEEPALIVE_PID" ]] && kill "$SUDO_KEEPALIVE_PID" 2>/dev/null || true
    [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]] && rm -rf -- "$TEMP_DIR"
}
trap cleanup EXIT

# ----------------------------------------------------------------------------
# UI / usage
# ----------------------------------------------------------------------------
print_banner() {
    printf '%b\n' "${MAGENTA}${BOLD}"
    printf '╔══════════════════════════════════════════════════════════════╗\n'
    printf '║             TechOGR BSPWM DOTFILES INSTALLER               ║\n'
    printf '║                         v%-33s║\n' "$SCRIPT_VERSION"
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
  --enable-lightdm    Instalar/activar LightDM solo si no hay DM activo.
  --dry-run           Mostrar acciones sin modificar el sistema.
  -h, --help          Mostrar esta ayuda.

Ejemplos:
  ./install.sh
  ./install.sh --no-upgrade
  ./install.sh --no-upgrade --no-shell
  ./install.sh --enable-network
USAGE
}

command_exists() { command -v "$1" >/dev/null 2>&1; }

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

# ----------------------------------------------------------------------------
# Environment
# ----------------------------------------------------------------------------
check_environment() {
    step "Validando entorno"

    (( EUID != 0 )) || fatal "Ejecuta el instalador como usuario normal, no como root."
    [[ -r /etc/os-release ]] || fatal "No existe /etc/os-release."

    # shellcheck disable=SC1091
    source /etc/os-release

    local arch_family=0
    [[ "${ID:-}" == "arch" ]] && arch_family=1
    [[ " ${ID_LIKE:-} " == *" arch "* ]] && arch_family=1
    (( arch_family )) || fatal "Se requiere Arch Linux o un derivado basado en Arch/pacman. Detectado: ${PRETTY_NAME:-desconocido}"

    command_exists pacman || fatal "pacman no está instalado."
    command_exists sudo || fatal "sudo no está instalado."
    command_exists git || fatal "git no está instalado."
    command_exists rsync || fatal "rsync no está instalado."

    ok "Sistema: ${PRETTY_NAME:-Arch Linux}"
    ok "Usuario: $USER"
}

prepare_sudo() {
    step "Validando sudo"
    sudo -v || fatal "No se pudieron obtener permisos sudo."

    if (( ! DRY_RUN )); then
        (
            while sleep 45; do
                sudo -n true 2>/dev/null || exit 0
            done
        ) &
        SUDO_KEEPALIVE_PID=$!
    fi
}

check_network() {
    step "Comprobando conectividad"
    if command_exists curl; then
        curl -fsS --max-time 10 https://archlinux.org/ >/dev/null || fatal "No hay conectividad con archlinux.org."
    else
        warn "curl aún no está instalado; se comprobará durante las descargas."
    fi
}

validate_repo() {
    step "Validando repositorio"

    [[ -d "$REPO_DIR/config" ]] || fatal "No existe config/ en el repositorio."
    [[ -d "$REPO_DIR/home" ]] || fatal "No existe home/ en el repositorio."
    [[ -d "$REPO_DIR/misc" ]] || fatal "No existe misc/ en el repositorio."

    ok "Estructura del rice válida"
}

# ----------------------------------------------------------------------------
# Package helpers
# ----------------------------------------------------------------------------
pkg_installed() { pacman -Q "$1" >/dev/null 2>&1; }
pkg_available() { pacman -Si "$1" >/dev/null 2>&1; }

# Detecta alternativas conflictivas antes de llamar a pacman.
# Esto evita el problema rust <-> rustup que ocurrió en la versión anterior.
choose_rust_provider() {
    local rust_installed=0
    local rustup_installed=0

    pkg_installed rust && rust_installed=1
    pkg_installed rustup && rustup_installed=1

    # Si solo una está instalada, la usamos.
    if (( rust_installed && !rustup_installed )); then
        echo "rust"
        return
    fi

    if (( rustup_installed && !rust_installed )); then
        echo "rustup"
        return
    fi

    # Si ninguna está instalada, usamos rust (el toolchain empaquetado por Arch)
    # para compilar proyectos modernos. Eww 0.6.0 trae Cargo.lock y no necesita
    # rustup como requisito de instalación.
    if (( !rust_installed && !rustup_installed )); then
        echo "rust"
        return
    fi

    # Ambos instalados: no tocar nada automáticamente.
    echo "both"
}

resolve_rust_conflict() {
    local provider
    provider="$(choose_rust_provider)"

    if [[ "$provider" != "both" ]]; then
        return 0
    fi

    step "Detectado conflicto entre rust y rustup"

    printf '\n'
    printf '%b\n' "${YELLOW}${BOLD}En este equipo están instalados ambos:${RESET}"
    printf '  1) rust   - toolchain gestionado por pacman\n'
    printf '  2) rustup  - gestor de toolchains de Rust\n'
    printf '\n'
    printf '%b\n' "${CYAN}Recomendación para este rice: conservar rust y eliminar rustup.${RESET}"
    printf '%b\n' "${WHITE}Motivo: el instalador usa el toolchain de Arch y así evita mantener dos gestores de Rust.${RESET}"
    printf '\n'

    while true; do
        read -r -p "¿Qué deseas eliminar? [1=rust, 2=rustup, 3=no eliminar/salir]: " choice

        case "$choice" in
            1)
                root_run pacman -Rns --noconfirm rust || fatal "No se pudo eliminar rust."
                ok "rust eliminado; se conservará rustup."
                return 0
                ;;
            2)
                root_run pacman -Rns --noconfirm rustup || fatal "No se pudo eliminar rustup."
                ok "rustup eliminado; se conservará rust."
                return 0
                ;;
            3)
                fatal "No se resolvió el conflicto rust/rustup."
                ;;
            *)
                warn "Opción inválida. Elige 1, 2 o 3."
                ;;
        esac
    done
}

# Instala paquetes oficiales de forma segura.
# Para los casos conocidos de alternativas/conflictos, pregunta al usuario.
# Si pacman devuelve un conflicto, se captura el mensaje y se intenta
# identificar el par conflictivo antes de abortar.
install_official_packages() {
    local requested=("$@")
    local available=()
    local missing=()
    local pkg

    for pkg in "${requested[@]}"; do
        pkg_installed "$pkg" && continue
        if pkg_available "$pkg"; then
            available+=("$pkg")
        else
            missing+=("$pkg")
        fi
    done

    ((${#missing[@]})) && {
        warn "Paquetes no encontrados en los repositorios configurados:"
        printf '  - %s\n' "${missing[@]}"
    }

    ((${#available[@]})) || return 0

    # Primero resuelve alternativas conocidas.
    local filtered=()
    for pkg in "${available[@]}"; do
        case "$pkg" in
            rust|rustup)
                # Se maneja por resolve_rust_conflict / ensure_rust.
                ;;
            *)
                filtered+=("$pkg")
                ;;
        esac
    done

    if ((${#filtered[@]})); then
        local pacman_output=""

        if pacman_output="$(sudo pacman -S --needed --noconfirm "${filtered[@]}" 2>&1)"; then
            printf '%s\n' "$pacman_output"
            return 0
        fi

        printf '%s\n' "$pacman_output"
        printf '%s\n' "$pacman_output" > "$STATE_DIR/pacman-conflict-$TIMESTAMP.txt"

        warn "pacman rechazó la transacción."
        resolve_conflict_from_output "$pacman_output" "${filtered[@]}"
    fi
}

# ----------------------------------------------------------------------------
# Generic conflict resolver
# ----------------------------------------------------------------------------
resolve_conflict_from_output() {
    local output="$1"
    shift
    local requested=("$@")

    local pairs=()
    local line
    local left
    local right

    # Detecta patrones típicos de pacman:
    #   foo and bar are in conflict
    #   foo conflicts with bar
    while IFS= read -r line; do
        if [[ "$line" =~ ([A-Za-z0-9@._+:-]+)[[:space:]]+and[[:space:]]+([A-Za-z0-9@._+:-]+)[[:space:]]+are[[:space:]]+in[[:space:]]+conflict ]]; then
            left="${BASH_REMATCH[1]}"
            right="${BASH_REMATCH[2]}"
            pairs+=("$left:$right")
        elif [[ "$line" =~ ([A-Za-z0-9@._+:-]+)[[:space:]]+conflicts[[:space:]]+with[[:space:]]+([A-Za-z0-9@._+:-]+) ]]; then
            left="${BASH_REMATCH[1]}"
            right="${BASH_REMATCH[2]}"
            pairs+=("$left:$right")
        fi
    done <<< "$output"

    # Conflicto conocido: rust/rustup.
    for pair in "${pairs[@]}"; do
        if [[ "$pair" == "rust:rustup" || "$pair" == "rustup:rust" ]]; then
            resolve_rust_conflict
            return 0
        fi
    done

    # Si no conseguimos parsear la salida, inspeccionamos metadatos de los
    # paquetes pedidos. Esto cubre cambios de formato de pacman.
    local pkg relation
    for pkg in "${requested[@]}"; do
        while IFS= read -r relation; do
            [[ -n "$relation" ]] || continue
            if [[ "$relation" == *"rust"* && "$relation" == *"rustup"* ]]; then
                resolve_rust_conflict
                return 0
            fi
        done < <(pacman -Si "$pkg" 2>/dev/null | awk -F': ' '/^Conflicts With/ {print $2}')
    done

    # Para cualquier par detectado, si uno o ambos paquetes están presentes,
    # ofrecemos una decisión explícita. Nunca eliminamos software a ciegas.
    if ((${#pairs[@]})); then
        local pair
        for pair in "${pairs[@]}"; do
            left="${pair%%:*}"
            right="${pair#*:}"

            local left_installed=0
            local right_installed=0
            pkg_installed "$left" && left_installed=1
            pkg_installed "$right" && right_installed=1

            printf '\n%b\n' "${YELLOW}${BOLD}Conflicto detectado: $left <-> $right${RESET}"

            if (( left_installed && right_installed )); then
                printf '  1) Eliminar %s y conservar %s\n' "$left" "$right"
                printf '  2) Eliminar %s y conservar %s\n' "$right" "$left"
                printf '  3) Cancelar instalación\n'
            elif (( left_installed )); then
                printf '  1) Eliminar %s y continuar con %s\n' "$left" "$right"
                printf '  2) Cancelar instalación\n'
            elif (( right_installed )); then
                printf '  1) Eliminar %s y continuar con %s\n' "$right" "$left"
                printf '  2) Cancelar instalación\n'
            else
                printf '  1) Intentar conservar %s\n' "$left"
                printf '  2) Intentar conservar %s\n' "$right"
                printf '  3) Cancelar instalación\n'
            fi

            # Recomendación conservadora: si el paquete solicitado está en la
            # transacción, conservar el solicitado y eliminar la alternativa
            # ya instalada. Para rust/rustup existe una recomendación explícita.
            if [[ "$left" == "rustup" || "$right" == "rustup" ]]; then
                warn "Para este rice recomiendo conservar 'rust' cuando sea posible y eliminar 'rustup'."
            else
                warn "Recomendación: conserva el paquete que ya utiliza tu sistema y elimina solo la alternativa que la nueva instalación necesita reemplazar."
            fi

            while true; do
                read -r -p "Selecciona una opción: " choice
                case "$choice" in
                    1)
                        if (( left_installed && right_installed )); then
                            root_run pacman -Rns --noconfirm "$left"
                        elif (( left_installed )); then
                            root_run pacman -Rns --noconfirm "$left"
                        elif (( right_installed )); then
                            root_run pacman -Rns --noconfirm "$right"
                        else
                            warn "Ninguno de los dos está instalado; no se elimina nada."
                            return 0
                        fi
                        return 0
                        ;;
                    2)
                        if (( left_installed && right_installed )); then
                            root_run pacman -Rns --noconfirm "$right"
                            return 0
                        elif (( left_installed || right_installed )); then
                            fatal "Instalación cancelada por el usuario."
                        else
                            if [[ "$left" == "rustup" || "$right" == "rustup" ]]; then
                                if [[ "$left" == "rust" ]]; then
                                    warn "Se conservará rust."
                                else
                                    warn "Se conservará rustup."
                                fi
                                return 0
                            fi
                            return 0
                        fi
                        ;;
                    3)
                        fatal "Instalación cancelada por el usuario."
                        ;;
                    *)
                        warn "Opción inválida."
                        ;;
                esac
            done
        done
    fi

    fatal "No se pudo resolver automáticamente el conflicto de pacman. Revisa $STATE_DIR/pacman-conflict-$TIMESTAMP.txt"
}

ensure_rust() {
    step "Preparando toolchain Rust"

    resolve_rust_conflict

    local provider
    provider="$(choose_rust_provider)"

    case "$provider" in
        rust)
            if ! pkg_installed rust; then
                install_official_packages rust
            fi
            ;;
        rustup)
            if ! pkg_installed rustup; then
                install_official_packages rustup
            fi
            ;;
        both)
            fatal "No se pudo resolver rust/rustup."
            ;;
    esac

    # Verificación final de herramientas.
    command_exists rustc || fatal "rustc no está disponible después de instalar Rust."
    command_exists cargo || fatal "cargo no está disponible después de instalar Rust."

    ok "Rust disponible: $(rustc --version)"
    ok "Cargo disponible: $(cargo --version)"
}

# ----------------------------------------------------------------------------
# System upgrade
# ----------------------------------------------------------------------------
full_upgrade() {
    (( NO_UPGRADE )) && {
        warn "Actualización completa omitida (--no-upgrade)."
        return 0
    }

    step "Actualizando el sistema"
    root_run pacman -Syu --noconfirm
}

# ----------------------------------------------------------------------------
# Dependencies
# ----------------------------------------------------------------------------
install_dependencies() {
    step "Instalando dependencias del rice"

    # IMPORTANTE: NO añadimos rust y rustup al mismo array.
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
        python-pywal \
        \
        noto-fonts \
        noto-fonts-emoji \
        ttf-dejavu \
        ttf-jetbrains-mono-nerd \
        ttf-firacode-nerd \
        ttf-nerd-fonts-symbols

    ensure_rust
    ok "Dependencias instaladas"
}

# ----------------------------------------------------------------------------
# fzf-tab
# ----------------------------------------------------------------------------
install_fzf_tab() {
    step "Instalando fzf-tab"

    local target="/usr/share/zsh/plugins/fzf-tab"

    if [[ -f "$target/fzf-tab.zsh" ]]; then
        ok "fzf-tab ya está instalado"
        return 0
    fi

    local src="$BUILD_DIR/fzf-tab"
    rm -rf -- "$src"
    mkdir -p "$BUILD_DIR"

    git clone --depth=1 https://github.com/Aloxaf/fzf-tab.git "$src"
    root_run mkdir -p "$target"
    root_run cp -a "$src/." "$target/"

    [[ -f "$target/fzf-tab.zsh" ]] || fatal "No se pudo instalar fzf-tab."
    ok "fzf-tab instalado"
}

# ----------------------------------------------------------------------------
# Eww
# ----------------------------------------------------------------------------
install_eww() {
    (( NO_EWW )) && {
        warn "Eww omitido (--no-eww)."
        return 0
    }

    step "Instalando Eww 0.6.0 desde upstream"

    if command_exists eww; then
        ok "Eww ya está instalado: $(eww --version 2>/dev/null || echo instalado)"
        return 0
    fi

    ensure_rust

    local src="$BUILD_DIR/eww"
    rm -rf -- "$src"
    mkdir -p "$BUILD_DIR"

    git clone --depth=1 --branch "$EWW_REF" "$EWW_REPO_URL" "$src"

    pushd "$src" >/dev/null

    # Eww 0.6.0 fue publicado en abril de 2024 y su documentación permite
    # compilar explícitamente con backend X11. Usamos el Cargo.lock del release.
    cargo build --release --locked --no-default-features --features x11

    [[ -x target/release/eww ]] || fatal "Cargo terminó sin generar target/release/eww."

    root_run install -Dm755 target/release/eww /usr/local/bin/eww

    popd >/dev/null

    command_exists eww || fatal "Eww no aparece en PATH después de la instalación."
    ok "Eww instalado: $(eww --version 2>/dev/null || echo 0.6.0)"
}

# ----------------------------------------------------------------------------
# Backup
# ----------------------------------------------------------------------------
backup_one() {
    local target="$1"
    [[ -e "$target" || -L "$target" ]] || return 0

    local rel
    if [[ "$target" == "$HOME_DIR/"* ]]; then
        rel="${target#$HOME_DIR/}"
    else
        rel="$(basename -- "$target")"
    fi

    mkdir -p "$BACKUP_DIR/$(dirname -- "$rel")"
    cp -a -- "$target" "$BACKUP_DIR/$rel"
}

create_backup() {
    step "Creando backup"
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
        "$HOME/.config/eww"
        "$HOME/.zshrc"
        "$HOME/.xinitrc"
        "$HOME/.xprofile"
    )

    local item
    for item in "${targets[@]}"; do
        backup_one "$item"
    done

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

# ----------------------------------------------------------------------------
# Deploy
# ----------------------------------------------------------------------------
deploy_directory() {
    local src="$1"
    local dest="$2"
    [[ -d "$src" ]] || return 0

    mkdir -p "$(dirname -- "$dest")"
    backup_one "$dest"
    mkdir -p "$dest"
    rsync -a --delete "$src/" "$dest/"
}

deploy_file() {
    local src="$1"
    local dest="$2"
    [[ -f "$src" ]] || return 0

    mkdir -p "$(dirname -- "$dest")"
    backup_one "$dest"
    install -Dm644 "$src" "$dest"
}

deploy_merge() {
    local src="$1"
    local dest="$2"
    [[ -d "$src" ]] || return 0

    mkdir -p "$dest"

    while IFS= read -r -d '' file; do
        local rel="${file#$src/}"
        local target="$dest/$rel"
        backup_one "$target"
        mkdir -p "$(dirname -- "$target")"
        install -Dm644 "$file" "$target"
    done < <(find "$src" -type f -print0)
}

install_dotfiles() {
    step "Instalando configuraciones de TechOGR"

    mkdir -p "$CONFIG_DIR" "$LOCAL_BIN" "$HOME/.local/share/applications" "$HOME/.local/share/fonts"

    shopt -s nullglob dotglob

    local src name
    for src in "$REPO_DIR/config"/*; do
        [[ -d "$src" ]] || continue
        name="$(basename -- "$src")"
        deploy_directory "$src" "$CONFIG_DIR/$name"
    done

    for src in "$REPO_DIR/home"/.* "$REPO_DIR/home"/*; do
        [[ -e "$src" || -L "$src" ]] || continue
        name="$(basename -- "$src")"
        [[ "$name" == "." || "$name" == ".." ]] && continue
        [[ -f "$src" || -L "$src" ]] && deploy_file "$src" "$HOME/$name"
    done

    deploy_merge "$REPO_DIR/misc/bin" "$LOCAL_BIN"
    deploy_merge "$REPO_DIR/misc/applications" "$HOME/.local/share/applications"
    deploy_merge "$REPO_DIR/misc/fonts" "$HOME/.local/share/fonts"

    if [[ -d "$REPO_DIR/misc/wallpapers" ]]; then
        deploy_merge "$REPO_DIR/misc/wallpapers" "$HOME/Wallpapers"
    elif [[ -d "$REPO_DIR/Wallpapers" ]]; then
        deploy_merge "$REPO_DIR/Wallpapers" "$HOME/Wallpapers"
    fi

    shopt -u nullglob dotglob
    ok "Configuraciones instaladas"
}

# ----------------------------------------------------------------------------
# Permissions / hardware safety
# ----------------------------------------------------------------------------
fix_permissions() {
    step "Aplicando permisos"

    [[ -d "$LOCAL_BIN" ]] && find "$LOCAL_BIN" -type f -exec chmod +x {} +
    [[ -f "$CONFIG_DIR/bspwm/bspwmrc" ]] && chmod +x "$CONFIG_DIR/bspwm/bspwmrc"
    [[ -d "$CONFIG_DIR/bspwm/bin" ]] && chmod +x "$CONFIG_DIR/bspwm/bin"/* 2>/dev/null || true
    [[ -d "$CONFIG_DIR/polybar" ]] && find "$CONFIG_DIR/polybar" -type f -name '*.sh' -exec chmod +x {} + 2>/dev/null || true
    [[ -d "$CONFIG_DIR/eww" ]] && find "$CONFIG_DIR/eww" -type f -name '*.sh' -exec chmod +x {} + 2>/dev/null || true

    ok "Permisos aplicados"
}

patch_virtual_monitor() {
    local file="$CONFIG_DIR/bspwm/bspwmrc"
    [[ -f "$file" ]] || return 0

    if grep -Eq '^[[:space:]]*xrandr --output Virtual-1 --mode 1920x1080 --rate 60[[:space:]]*$' "$file"; then
        step "Haciendo segura la configuración Virtual-1"
        backup_one "$file"
        sed -i \
            's@^[[:space:]]*xrandr --output Virtual-1 --mode 1920x1080 --rate 60[[:space:]]*$@if xrandr --query 2>/dev/null | grep -q "^Virtual-1 connected"; then xrandr --output Virtual-1 --mode 1920x1080 --rate 60; fi@' \
            "$file"
        ok "Virtual-1 ahora es condicional"
    fi
}

# ----------------------------------------------------------------------------
# X session
# ----------------------------------------------------------------------------
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
        root_run install -Dm644 "$tmp" "$desktop_file"
        rm -f "$tmp"
    fi

    ok "Sesión BSPWM preparada"
}

# ----------------------------------------------------------------------------
# Services / shell
# ----------------------------------------------------------------------------
setup_services() {
    if (( ENABLE_NETWORK )); then
        step "Habilitando NetworkManager"
        if command_exists systemctl; then
            root_run systemctl enable --now NetworkManager.service
            ok "NetworkManager habilitado"
        else
            warn "systemctl no está disponible."
        fi
    fi

    if (( ENABLE_LIGHTDM )); then
        step "Configurando LightDM"
        install_official_packages lightdm lightdm-gtk-greeter

        if command_exists systemctl; then
            local active="$(systemctl is-active display-manager.service 2>/dev/null || true)"
            local enabled="$(systemctl is-enabled display-manager.service 2>/dev/null || true)"

            if [[ "$active" == "active" || "$enabled" == "enabled" ]]; then
                warn "Ya existe un display manager activo/habilitado. No se reemplaza."
            else
                root_run systemctl enable lightdm.service
                ok "LightDM habilitado"
            fi
        fi
    fi
}

setup_zsh() {
    (( NO_SHELL )) && {
        warn "Cambio de shell omitido (--no-shell)."
        return 0
    }

    command_exists zsh || return 0

    local zsh_path="$(command -v zsh)"
    local current="$(getent passwd "$USER" | awk -F: '{print $7}')"

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

    if ! command_exists paru && grep -qE '^alias update="paru -Syu' "$zshrc"; then
        backup_one "$zshrc"
        sed -i 's/^alias update="paru -Syu[^\"]*"/alias update="sudo pacman -Syu"/' "$zshrc"
        ok "Alias update ajustado para no depender de paru"
    fi
}

refresh_fonts() {
    command_exists fc-cache || return 0
    step "Actualizando caché de fuentes"
    fc-cache -f
    ok "Caché de fuentes actualizado"
}

# ----------------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------------
validate_installation() {
    step "Validando instalación"

    local files=(
        "$CONFIG_DIR/bspwm/bspwmrc"
        "$CONFIG_DIR/bspwm/config/sxhkdrc"
        "$CONFIG_DIR/polybar"
        "$CONFIG_DIR/rofi"
        "$CONFIG_DIR/eww"
        "$HOME/.zshrc"
    )

    local failed=0 item
    for item in "${files[@]}"; do
        if [[ -e "$item" ]]; then
            ok "Existe: $item"
        else
            warn "Falta: $item"
            failed=1
        fi
    done

    local commands=(bspwm sxhkd polybar picom rofi jgmenu dunst kitty zsh nvim thunar)
    (( NO_EWW == 0 )) && commands+=(eww)

    local cmd
    for cmd in "${commands[@]}"; do
        if command_exists "$cmd"; then
            ok "Disponible: $cmd"
        else
            warn "Falta comando: $cmd"
            failed=1
        fi
    done

    (( failed == 0 )) && ok "Validación completada" || warn "La instalación terminó con avisos. Revisa $LOG_FILE"
}

# ----------------------------------------------------------------------------
# Final
# ----------------------------------------------------------------------------
print_summary() {
    printf '\n%b\n' "${GREEN}${BOLD}╔══════════════════════════════════════════════════════════════╗${RESET}"
    printf '%b\n' "${GREEN}${BOLD}║                  INSTALACIÓN COMPLETADA                     ║${RESET}"
    printf '%b\n' "${GREEN}${BOLD}╚══════════════════════════════════════════════════════════════╝${RESET}"
    printf '\n'
    printf '  Rice:     TechOGR BSPWM\n'
    printf '  Config:   %s\n' "$CONFIG_DIR"
    printf '  Backup:   %s\n' "$BACKUP_DIR"
    printf '  Log:      %s\n' "$LOG_FILE"
    printf '\n'
    printf '%b\n' "${CYAN}${BOLD}Siguiente paso:${RESET}"
    printf '  Cierra sesión y selecciona BSPWM en tu display manager.\n'
    printf '  O utiliza: startx\n'
}

# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
main() {
    while (($#)); do
        case "$1" in
            --no-upgrade) NO_UPGRADE=1 ;;
            --no-shell) NO_SHELL=1 ;;
            --no-eww) NO_EWW=1 ;;
            --enable-network) ENABLE_NETWORK=1 ;;
            --enable-lightdm) ENABLE_LIGHTDM=1 ;;
            --dry-run) DRY_RUN=1 ;;
            -h|--help)
                usage
                trap - ERR
                exit 0
                ;;
            *) fatal "Opción desconocida: $1" ;;
        esac
        shift
    done

    print_banner
    check_environment
    prepare_sudo
    mkdir -p "$STATE_DIR" "$BUILD_DIR" "$BACKUP_ROOT" "$CONFIG_DIR" "$LOCAL_BIN"
    validate_repo
    check_network
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
