#!/usr/bin/env bash
# =============================================================================
# TechOGR BSPWM Dotfiles Installer
# v4.0.0
# https://github.com/TechOGR/bspwm_dotfiles_arch
#
# Arch Linux / Arch-based distributions
# =============================================================================

set -Eeuo pipefail
IFS=$'\n\t'

SCRIPT_VERSION="4.0.0"
REPO_URL="https://github.com/TechOGR/bspwm_dotfiles_arch.git"
EWW_REPO_URL="https://github.com/elkowar/eww.git"
EWW_REF="v0.6.0"
EWW_TIME_VERSION="0.3.34"

HOME_DIR="$HOME"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}"
LOCAL_BIN="${XDG_BIN_HOME:-$HOME/.local/bin}"
LOCAL_SHARE="${XDG_DATA_HOME:-$HOME/.local/share}"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/techogr-bspwm"
BACKUP_ROOT="$HOME/.RiceBackup"
TIMESTAMP="$(date '+%Y-%m-%d_%H-%M-%S')"
BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"
LOG_FILE="$STATE_DIR/install-$TIMESTAMP.log"
BUILD_DIR="$STATE_DIR/build"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_DIR="$SCRIPT_DIR"
TEMP_ROOT=""
SUDO_KEEPALIVE_PID=""

DRY_RUN=0
NO_UPGRADE=0
NO_SHELL=0
NO_EWW=0
ENABLE_NETWORK=0
ENABLE_LIGHTDM=0

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
    if [[ -n "$SUDO_KEEPALIVE_PID" ]]; then
        kill "$SUDO_KEEPALIVE_PID" 2>/dev/null || true
    fi
    if [[ -n "$TEMP_ROOT" && -d "$TEMP_ROOT" ]]; then
        rm -rf -- "$TEMP_ROOT"
    fi
}
trap cleanup EXIT

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

pkg_installed() { pacman -Q "$1" >/dev/null 2>&1; }
pkg_available() { pacman -Si "$1" >/dev/null 2>&1; }

# =============================================================================
# Environment
# =============================================================================
check_environment() {
    step "Validando entorno"

    (( EUID != 0 )) || fatal "Ejecuta el instalador como usuario normal, no como root."
    [[ -r /etc/os-release ]] || fatal "No existe /etc/os-release."
    command_exists pacman || fatal "pacman no está instalado."
    command_exists sudo || fatal "sudo no está instalado."

    # shellcheck disable=SC1091
    source /etc/os-release

    local arch_family=0
    [[ "${ID:-}" == "arch" ]] && arch_family=1
    [[ " ${ID_LIKE:-} " == *" arch "* ]] && arch_family=1

    (( arch_family )) || fatal "Se requiere Arch Linux o un derivado basado en Arch/pacman. Detectado: ${PRETTY_NAME:-desconocido}"

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

bootstrap_packages() {
    step "Preparando herramientas básicas"

    # These are the only tools the installer itself must have before proceeding.
    local wanted=()
    local pkg

    for pkg in git curl rsync; do
        pkg_installed "$pkg" || wanted+=("$pkg")
    done

    if ((${#wanted[@]})); then
        root_run pacman -S --needed --noconfirm "${wanted[@]}"
    fi

    command_exists git || fatal "git no está disponible."
    command_exists curl || fatal "curl no está disponible."
    command_exists rsync || fatal "rsync no está disponible."
}

check_network() {
    step "Comprobando conectividad"
    curl -fsS --max-time 10 https://archlinux.org/ >/dev/null || \
        fatal "No hay conectividad con archlinux.org."
    ok "Conectividad disponible"
}

# =============================================================================
# Repository
# =============================================================================
validate_repo() {
    step "Validando repositorio"

    [[ -d "$REPO_DIR/config" ]] || fatal "No existe config/ en el repositorio."
    [[ -d "$REPO_DIR/home" ]] || fatal "No existe home/ en el repositorio."
    [[ -d "$REPO_DIR/misc" ]] || fatal "No existe misc/ en el repositorio."

    ok "Estructura del rice válida"
}

# =============================================================================
# General conflict handling
# =============================================================================
extract_conflict_pairs() {
    local output="$1"
    local line left right

    while IFS= read -r line; do
        if [[ "$line" =~ ([A-Za-z0-9@._+:-]+)[[:space:]]+and[[:space:]]+([A-Za-z0-9@._+:-]+)[[:space:]]+are[[:space:]]+in[[:space:]]+conflict ]]; then
            left="${BASH_REMATCH[1]}"
            right="${BASH_REMATCH[2]}"
            printf '%s:%s\n' "$left" "$right"
        elif [[ "$line" =~ ([A-Za-z0-9@._+:-]+)[[:space:]]+conflicts[[:space:]]+with[[:space:]]+([A-Za-z0-9@._+:-]+) ]]; then
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

    pkg_installed "$left" && left_installed=1
    pkg_installed "$right" && right_installed=1

    printf '\n'
    printf '%b\n' "${YELLOW}${BOLD}╔══════════════════════════════════════════════════════╗${RESET}"
    printf '%b\n' "${YELLOW}${BOLD}║                 CONFLICTO DETECTADO                 ║${RESET}"
    printf '%b\n' "${YELLOW}${BOLD}╚══════════════════════════════════════════════════════╝${RESET}"
    printf '\n'
    printf 'Los paquetes en conflicto son:\n\n'
    printf '  1) %s%s\n' "$left" "$( (( left_installed )) && printf '  [INSTALADO]' || true )"
    printf '  2) %s%s\n' "$right" "$( (( right_installed )) && printf '  [INSTALADO]' || true )"
    printf '\n'

    # Explicit recommendation for rust/rustup.
    if [[ ("$left" == rust && "$right" == rustup) || ("$left" == rustup && "$right" == rust) ]]; then
        printf '%b\n' "${CYAN}${BOLD}Recomendación: conservar 'rust' y eliminar 'rustup'.${RESET}"
        printf 'El instalador compilará Eww con el toolchain de Rust disponible en el sistema.\n'
    elif (( left_installed && !right_installed )); then
        printf '%b\n' "${CYAN}Recomendación: conservar %s porque ya está instalado.${RESET}" "$left"
    elif (( right_installed && !left_installed )); then
        printf '%b\n' "${CYAN}Recomendación: conservar %s porque ya está instalado.${RESET}" "$right"
    else
        printf '%b\n' "${CYAN}Recomendación: no elimines un paquete que ya uses para otra parte del sistema. Si no sabes cuál conservar, cancela.${RESET}"
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

install_official_packages() {
    local requested=("$@")
    local available=()
    local missing=()
    local pkg output pairs pair left right

    for pkg in "${requested[@]}"; do
        pkg_installed "$pkg" && continue
        if pkg_available "$pkg"; then
            available+=("$pkg")
        else
            missing+=("$pkg")
        fi
    done

    if ((${#missing[@]})); then
        warn "No encontrados en los repositorios configurados:"
        printf '  - %s\n' "${missing[@]}"
        printf '%s\n' "${missing[@]}" > "$STATE_DIR/missing-packages.txt"
    fi

    ((${#available[@]})) || return 0

    # Never put rust and rustup in the same pacman transaction.
    local transaction=()
    for pkg in "${available[@]}"; do
        case "$pkg" in
            rust|rustup) ;;
            *) transaction+=("$pkg") ;;
        esac
    done

    if ((${#transaction[@]})); then
        output=""
        if ! output="$(sudo pacman -S --needed --noconfirm "${transaction[@]}" 2>&1)"; then
            printf '%s\n' "$output"
            printf '%s\n' "$output" > "$STATE_DIR/pacman-error-$TIMESTAMP.txt"

            pairs="$(extract_conflict_pairs "$output" || true)"
            if [[ -n "$pairs" ]]; then
                while IFS= read -r pair; do
                    [[ -n "$pair" ]] || continue
                    left="${pair%%:*}"
                    right="${pair#*:}"
                    choose_conflict_action "$left" "$right"
                done <<< "$pairs"
            else
                warn "No pude interpretar automáticamente el conflicto."
                warn "No se eliminará ningún paquete a ciegas."
                fatal "pacman no pudo completar la transacción. Revisa $STATE_DIR/pacman-error-$TIMESTAMP.txt"
            fi
        else
            printf '%s\n' "$output"
        fi
    fi
}

# =============================================================================
# Rust selection
# =============================================================================
get_rust_provider() {
    local has_rust=0
    local has_rustup=0

    pkg_installed rust && has_rust=1
    pkg_installed rustup && has_rustup=1

    if (( has_rust && has_rustup )); then
        printf 'both\n'
    elif (( has_rust )); then
        printf 'rust\n'
    elif (( has_rustup )); then
        printf 'rustup\n'
    else
        printf 'none\n'
    fi
}

resolve_rust_conflict() {
    local provider
    provider="$(get_rust_provider)"

    [[ "$provider" == both ]] || return 0

    choose_conflict_action rust rustup
}

# =============================================================================
# System upgrade
# =============================================================================
full_upgrade() {
    (( NO_UPGRADE )) && {
        warn "Actualización completa omitida (--no-upgrade)."
        return 0
    }

    step "Actualizando el sistema"
    root_run pacman -Syu --noconfirm
}

# =============================================================================
# Dependencies
# =============================================================================
install_dependencies() {
    step "Instalando dependencias del rice"

    # Rust/rustup are intentionally NOT included here. They are resolved in
    # ensure_eww_toolchain so conflicting alternatives never enter the same pacman transaction.
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

    ok "Dependencias principales instaladas"
}

# =============================================================================
# fzf-tab
# =============================================================================
install_fzf_tab() {
    step "Instalando fzf-tab desde upstream"

    local target="/usr/share/zsh/plugins/fzf-tab"

    if [[ -f "$target/fzf-tab.zsh" ]]; then
        ok "fzf-tab ya está instalado"
        return 0
    fi

    local src="$BUILD_DIR/fzf-tab"

    mkdir -p "$BUILD_DIR"
    rm -rf -- "$src"

    git clone --depth=1 https://github.com/Aloxaf/fzf-tab.git "$src"

    root_run mkdir -p "$target"
    root_run cp -a "$src/." "$target/"

    [[ -f "$target/fzf-tab.zsh" ]] || fatal "No se pudo instalar fzf-tab."
    ok "fzf-tab instalado"
}

# =============================================================================
# Eww
# =============================================================================
ensure_eww_toolchain() {
    step "Preparando toolchain para Eww"

    local has_rust=0
    local has_rustup=0

    pkg_installed rust && has_rust=1
    pkg_installed rustup && has_rustup=1

    if (( has_rust && has_rustup )); then
        printf '\n'
        printf '%b\n' "${YELLOW}${BOLD}Rust y rustup están instalados al mismo tiempo.${RESET}"
        printf 'Eww 0.6.0 incluye oficialmente rust-toolchain.toml y fija Rust 1.76.0.\n'
        printf '%b\n' "${CYAN}${BOLD}Recomendación: conservar rustup y eliminar rust.${RESET}"
        printf '\n'

        while true; do
            printf '  [1] Eliminar rust y conservar rustup  (RECOMENDADO)\n'
            printf '  [2] Eliminar rustup y conservar rust\n'
            printf '  [3] Cancelar instalación\n\n'
            read -r -p 'Selecciona [1/2/3]: ' choice
            case "$choice" in
                1)
                    root_run pacman -Rns --noconfirm rust
                    has_rust=0
                    break
                    ;;
                2)
                    root_run pacman -Rns --noconfirm rustup
                    has_rustup=0
                    break
                    ;;
                3)
                    fatal "Instalación cancelada por el usuario."
                    ;;
                *)
                    warn "Opción inválida."
                    ;;
            esac
        done
    fi

    if (( !has_rust && !has_rustup )); then
        printf '\n'
        printf '%b\n' "${CYAN}${BOLD}No se detectó Rust.${RESET}"
        printf 'Para Eww 0.6.0 recomiendo rustup porque el release trae\n'
        printf 'rust-toolchain.toml con Rust 1.76.0 fijado por upstream.\n\n'
        printf '  [1] Instalar rustup (RECOMENDADO)\n'
        printf '  [2] Instalar rust del sistema\n'
        printf '  [3] Cancelar instalación\n\n'

        while true; do
            read -r -p 'Selecciona [1/2/3]: ' choice
            case "$choice" in
                1)
                    install_official_packages rustup
                    has_rustup=1
                    break
                    ;;
                2)
                    install_official_packages rust
                    has_rust=1
                    break
                    ;;
                3)
                    fatal "Instalación cancelada por el usuario."
                    ;;
                *)
                    warn "Opción inválida."
                    ;;
            esac
        done
    fi

    if (( has_rustup )); then
        command_exists rustup || fatal "rustup se instaló pero no está disponible en PATH."
        command_exists cargo || fatal "cargo no está disponible."

        ok "Usando rustup para Eww; upstream fija Rust 1.76.0 en rust-toolchain.toml."
        return 0
    fi

    if (( has_rust )); then
        command_exists rustc || fatal "rustc no está disponible."
        command_exists cargo || fatal "cargo no está disponible."
        warn "Usando Rust del sistema. Si Eww falla por compatibilidad del toolchain, el instalador ofrecerá cambiar a rustup."
        return 0
    fi

    fatal "No se pudo preparar un toolchain Rust."
}

get_active_rust_version() {
    if command_exists rustup && [[ -f "rust-toolchain.toml" ]]; then
        rustup show active-toolchain 2>/dev/null | awk '{print $1}' || true
        return 0
    fi

    rustc --version 2>/dev/null || true
}

build_eww() {
    local src="$1"
    local build_log="$STATE_DIR/eww-build-$TIMESTAMP.log"

    pushd "$src" >/dev/null

    : > "$build_log"

    info "Toolchain activo: $(get_active_rust_version)"
    info "Cargo.lock oficial será respetado."
    info "No se ejecutará cargo tree ni se hará detección heurística del crate time."

    # Eww v0.6.0 ships rust-toolchain.toml with Rust 1.76.0.
    # When rustup is available, cargo automatically follows that file.
    if command_exists rustup && [[ -f rust-toolchain.toml ]]; then
        info "rust-toolchain.toml detectado; sincronizando el toolchain fijado por Eww."
        if ! rustup toolchain install 1.76.0 --component rust-src >/dev/null 2>&1; then
            warn "No se pudo instalar Rust 1.76.0 automáticamente."
        fi
    fi

    if cargo build --release --locked --no-default-features --features x11 >"$build_log" 2>&1; then
        popd >/dev/null
        return 0
    fi

    warn "La compilación de Eww falló."
    warn "Log: $build_log"

    # Do not inspect with cargo tree. Instead, look only at Cargo's actual error
    # output. If it is a Rust/MSRV/time problem and rustup is available, retry
    # explicitly with the toolchain fixed by upstream.
    if grep -Eiq 'time([[:space:]`]|-[[:digit:]]|[[:alnum:]_]|$)|requires.*rustc|rust-version|MSRV' "$build_log"; then
        warn "El error parece relacionado con Rust/MSRV o el crate time."
    fi

    if command_exists rustup && [[ -f rust-toolchain.toml ]]; then
        step "Reintentando Eww con el toolchain oficial 1.76.0"

        rustup toolchain install 1.76.0 --component rust-src >>"$build_log" 2>&1 || true

        if cargo +1.76.0 build --release --locked --no-default-features --features x11 >>"$build_log" 2>&1; then
            popd >/dev/null
            return 0
        fi
    else
        # If the user chose system Rust and the old release needs its pinned
        # toolchain, ask before installing rustup and replacing rust.
        if pkg_installed rust && !pkg_installed rustup; then
            popd >/dev/null

            printf '\n'
            printf '%b\n' "${YELLOW}${BOLD}Eww no pudo compilarse con el Rust del sistema.${RESET}"
            printf 'El release v0.6.0 de Eww incluye rust-toolchain.toml con Rust 1.76.0.\n'
            printf '%b\n' "${CYAN}${BOLD}Recomendación: cambiar de rust a rustup para usar exactamente el toolchain de Eww.${RESET}"
            printf '\n'

            while true; do
                printf '  [1] Eliminar rust, instalar rustup y reintentar (RECOMENDADO)\n'
                printf '  [2] Mantener rust y abortar\n\n'
                read -r -p 'Selecciona [1/2]: ' choice
                case "$choice" in
                    1)
                        root_run pacman -Rns --noconfirm rust
                        install_official_packages rustup
                        command_exists rustup || fatal "rustup no quedó disponible."
                        pushd "$src" >/dev/null
                        rustup toolchain install 1.76.0 --component rust-src
                        if cargo +1.76.0 build --release --locked --no-default-features --features x11 >>"$build_log" 2>&1; then
                            popd >/dev/null
                            return 0
                        fi
                        popd >/dev/null
                        fatal "Eww sigue sin compilar con Rust 1.76.0. Revisa $build_log"
                        ;;
                    2)
                        fatal "Instalación cancelada porque Eww no compila con el Rust del sistema."
                        ;;
                    *)
                        warn "Opción inválida."
                        ;;
                esac
            done
        fi
    fi

    popd >/dev/null
    return 1
}

install_eww() {
    (( NO_EWW )) && {
        warn "Eww omitido (--no-eww)."
        return 0
    }

    step "Instalando Eww $EWW_REF para X11"

    if command_exists eww; then
        ok "Eww ya está instalado: $(eww --version 2>/dev/null || echo instalado)"
        return 0
    fi

    ensure_eww_toolchain

    local src="$BUILD_DIR/eww"
    mkdir -p "$BUILD_DIR"
    rm -rf -- "$src"

    git clone --depth=1 --branch "$EWW_REF" "$EWW_REPO_URL" "$src"

    [[ -f "$src/Cargo.lock" ]] || fatal "Eww $EWW_REF no contiene Cargo.lock."
    [[ -f "$src/rust-toolchain.toml" ]] || warn "No se encontró rust-toolchain.toml en el release."

    info "Cargo.lock oficial detectado."

    if ! build_eww "$src"; then
        fatal "No se pudo compilar Eww $EWW_REF. Revisa: $STATE_DIR/eww-build-$TIMESTAMP.log"
    fi

    [[ -x "$src/target/release/eww" ]] || fatal "Cargo terminó sin generar target/release/eww."

    root_run install -Dm755 "$src/target/release/eww" /usr/local/bin/eww

    command_exists eww || fatal "Eww no aparece en PATH después de la instalación."
    ok "Eww instalado: $(eww --version 2>/dev/null || echo "$EWW_REF")"
}

# =============================================================================
# Backup
# =============================================================================
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

# =============================================================================
# Deploy
# =============================================================================
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
    [[ -f "$src" || -L "$src" ]] || return 0

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

    mkdir -p \
        "$CONFIG_DIR" \
        "$LOCAL_BIN" \
        "$LOCAL_SHARE/applications" \
        "$LOCAL_SHARE/fonts"

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
        deploy_file "$src" "$HOME/$name"
    done

    deploy_merge "$REPO_DIR/misc/bin" "$LOCAL_BIN"
    deploy_merge "$REPO_DIR/misc/applications" "$LOCAL_SHARE/applications"
    deploy_merge "$REPO_DIR/misc/fonts" "$LOCAL_SHARE/fonts"

    if [[ -d "$REPO_DIR/misc/wallpapers" ]]; then
        deploy_merge "$REPO_DIR/misc/wallpapers" "$HOME/Wallpapers"
    elif [[ -d "$REPO_DIR/Wallpapers" ]]; then
        deploy_merge "$REPO_DIR/Wallpapers" "$HOME/Wallpapers"
    fi

    shopt -u nullglob dotglob
    ok "Configuraciones instaladas"
}

# =============================================================================
# Permissions / hardware safety
# =============================================================================
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

# =============================================================================
# X session
# =============================================================================
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

# =============================================================================
# Services / shell
# =============================================================================
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
            local active enabled
            active="$(systemctl is-active display-manager.service 2>/dev/null || true)"
            enabled="$(systemctl is-enabled display-manager.service 2>/dev/null || true)"

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

    local zsh_path current
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

# =============================================================================
# Validation
# =============================================================================
validate_installation() {
    step "Validando instalación"

    local files=(
        "$CONFIG_DIR/bspwm/bspwmrc"
        "$CONFIG_DIR/bspwm/config/sxhkdrc"
        "$CONFIG_DIR/polybar"
        "$CONFIG_DIR/rofi"
        "$HOME/.zshrc"
    )

    (( NO_EWW == 0 )) && files+=("$CONFIG_DIR/eww")

    local failed=0 item

    for item in "${files[@]}"; do
        if [[ -e "$item" ]]; then
            ok "Existe: $item"
        else
            warn "Falta: $item"
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
        clipcatd
    )

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

    if (( failed == 0 )); then
        ok "Validación completada"
    else
        warn "La instalación terminó con avisos. Revisa $LOG_FILE"
    fi
}

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

main() {
    while (($#)); do
        case "$1" in
            --no-upgrade) NO_UPGRADE=1 ;;
            --no-shell) NO_SHELL=1 ;;
            --no-eww) NO_EWW=1 ;;
            --enable-network) ENABLE_NETWORK=1 ;;
            --enable-lightdm) ENABLE_LIGHTDM=1 ;;
            --dry-run) DRY_RUN=1 ;;
            -h|--help) usage; exit 0 ;;
            *) fatal "Opción desconocida: $1" ;;
        esac
        shift
    done

    print_banner
    check_environment
    prepare_sudo
    bootstrap_packages
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
