#!/usr/bin/env bash
# ==============================================================================
# TechOGR BSPWM Dotfiles Installer
# Version 8.2.0
# Arch Linux / CachyOS / EndeavourOS / Garuda / BlackArch / Manjaro / derivatives
#
# IMPORTANT:
#   This installer deploys ONLY the files present in THIS repository.
#   It does not clone any other dotfiles repository.
#   Managed configuration files are copied as-is and are NEVER patched in place.
#
# Run:
#   chmod +x install.sh
#   ./install.sh
# ==============================================================================

set -Eeuo pipefail

SCRIPT_VERSION="8.2.0"
REPO_URL="https://github.com/TechOGR/bspwm_dotfiles_arch.git"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
HOME="${HOME:?HOME is not set}"
LOG_FILE="$HOME/.techogr_install.log"
BACKUP_ROOT="$HOME/.dotfiles_backup"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$BACKUP_ROOT/backup_$TIMESTAMP"
AUR_HELPER=""
SUDO_KEEPALIVE_PID=""

FAILED_REQUIRED=()
FAILED_OPTIONAL=()

# ------------------------------- Colors --------------------------------------
if [[ -t 1 ]]; then
    RESET=$'\e[0m'
    BOLD=$'\e[1m'
    DIM=$'\e[2m'
    RED=$'\e[31m'
    GREEN=$'\e[32m'
    YELLOW=$'\e[33m'
    BLUE=$'\e[34m'
    MAGENTA=$'\e[35m'
    CYAN=$'\e[36m'
    WHITE=$'\e[37m'
    BG_BLUE=$'\e[44m'
    TC_SUPPORT=true
else
    RESET=''; BOLD=''; DIM=''; RED=''; GREEN=''; YELLOW=''; BLUE=''; MAGENTA=''; CYAN=''; WHITE=''; BG_BLUE=''
    TC_SUPPORT=false
fi

# 24-bit "rgb R G B" -> escape code. Falls back to plain BOLD when the
# terminal isn't a tty (piped output, CI logs, etc.).
rgb() {
    [[ "$TC_SUPPORT" == true ]] && printf '\e[38;2;%d;%d;%dm' "$1" "$2" "$3" || printf '%s' "$BOLD"
}

# Prints one line, colored as a linear interpolation between two RGB stops
# picked by how far `step`/`of` are along the sequence. Used to give the
# banner and the progress rail a smooth cyan -> violet gradient instead of a
# single flat color.
gradient_line() {
    local text="$1" step="$2" of="$3"
    local r1=125 g1=207 b1=255   # soft cyan
    local r2=189 g2=147 b2=249   # soft violet
    local t=0 r g b
    (( of > 0 )) && t=$(( step * 100 / of ))
    r=$(( r1 + (r2 - r1) * t / 100 ))
    g=$(( g1 + (g2 - g1) * t / 100 ))
    b=$(( b1 + (b2 - b1) * t / 100 ))
    printf '%s%s%s%s\n' "$BOLD" "$(rgb "$r" "$g" "$b")" "$text" "$RESET"
}

mkdir -p -- "$(dirname -- "$LOG_FILE")"
printf '=== TechOGR BSPWM Installer %s - %s ===\n' "$SCRIPT_VERSION" "$(date)" > "$LOG_FILE"

# ------------------------------- Logging -------------------------------------
CURRENT_STEP=0
TOTAL_STEPS=16
STEP_OPEN=false
STEP_START=0
RAIL="$MAGENTA│$RESET "

log() {
    printf '%s [%s] %s\n' "$(date '+%F %T')" "$1" "$2" >> "$LOG_FILE"
}

info() {
    printf ' %s%s➜%s %s\n' "$RAIL" "$CYAN" "$RESET" "$1"
    log INFO "$1"
}

success() {
    printf ' %s%s✔%s %s\n' "$RAIL" "$GREEN" "$RESET" "$1"
    log SUCCESS "$1"
}

warn() {
    printf ' %s%s⚠%s %s\n' "$RAIL" "$YELLOW" "$RESET" "$1"
    log WARNING "$1"
}

error() {
    printf ' %s%s✖%s %s\n' "$RAIL" "$RED" "$RESET" "$1" >&2
    log ERROR "$1"
}

# Renders a slim, filled/empty progress rail: [08/13] ██████░░░░░░░  62%
progress_rail() {
    local current="$1" total="$2" width=28 filled i bar
    (( filled = current * width / total ))
    bar=""
    for ((i = 0; i < width; i++)); do
        if (( i < filled )); then
            bar+="$(gradient_line "█" "$i" "$width")"
        else
            bar+="${DIM}░${RESET}"
        fi
    done
    printf ' %s%s%s %s%3d%%%s\n' "$DIM" "$bar" "$RESET" "$DIM" "$(( current * 100 / total ))" "$RESET"
}

# Opens a numbered step box, closing the previous one first (with its
# elapsed time) so the whole run reads as a continuous, connected tree
# instead of a flat wall of text.
step() {
    if [[ "$STEP_OPEN" == true ]]; then
        printf '%s%s╰─%s %sListo en %ss%s\n' "$MAGENTA" "$BOLD" "$RESET" "$DIM" "$(( $(date +%s) - STEP_START ))" "$RESET"
    fi
    CURRENT_STEP=$((CURRENT_STEP + 1))
    STEP_OPEN=true
    STEP_START=$(date +%s)
    printf '\n%s%s╭─ [%02d/%02d] %s%s\n' "$MAGENTA" "$BOLD" "$CURRENT_STEP" "$TOTAL_STEPS" "$1" "$RESET"
    progress_rail "$CURRENT_STEP" "$TOTAL_STEPS"
    log STEP "$1"
}

close_last_step() {
    [[ "$STEP_OPEN" == true ]] || return 0
    printf '%s%s╰─%s %sListo en %ss%s\n' "$MAGENTA" "$BOLD" "$RESET" "$DIM" "$(( $(date +%s) - STEP_START ))" "$RESET"
    STEP_OPEN=false
}

fatal() {
    error "$1"
    error "Consulta el log: $LOG_FILE"
    exit 1
}

command_exists() { command -v "$1" >/dev/null 2>&1; }
is_pkg_installed() { pacman -Qq "$1" >/dev/null 2>&1; }

# ------------------------------- UI -------------------------------------------
print_banner() {
    clear 2>/dev/null || true
    local lines=(
        '   ████████╗███████╗ ██████╗██╗  ██╗ ██████╗  ██████╗ ██████╗ '
        '   ╚══██╔══╝██╔════╝██╔════╝██║  ██║██╔═══██╗██╔════╝ ██╔══██╗'
        '      ██║   █████╗  ██║     ███████║██║   ██║██║  ███╗██████╔╝'
        '      ██║   ██╔══╝  ██║     ██╔══██║██║   ██║██║   ██║██╔══██╗'
        '      ██║   ███████╗╚██████╗██║  ██║╚██████╔╝╚██████╔╝██║  ██║'
        '      ╚═╝   ╚══════╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝'
    )
    local i
    printf '\n'
    for i in "${!lines[@]}"; do
        gradient_line "${lines[$i]}" "$i" "${#lines[@]}"
    done
    printf '   %s%s· BSPWM Dotfiles Installer · v%s%s\n' "$DIM" "$BOLD" "$SCRIPT_VERSION" "$RESET"
    printf '   %sX11 · Eww · Picom (animaciones) · Polybar · LightDM · AUR%s\n\n' "$DIM" "$RESET"
}

# Render progress for a long-running command while preserving full output in the log.
run_with_live_progress() {
    local label="$1"
    shift
    local tmp rc start now elapsed last line spinner index=0
    tmp="$(mktemp)"
    start="$(date +%s)"
    "$@" >"$tmp" 2>&1 &
    local pid=$!

    spinner=( '⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏' )
    while kill -0 "$pid" 2>/dev/null; do
        elapsed=$(( $(date +%s) - start ))
        last="$(tail -n 1 "$tmp" 2>/dev/null | tr -d '\r' | cut -c1-78)"
        printf '\r  %s%s%s %s  %02dm%02ds  %-78s' "$CYAN" "${spinner[$index]}" "$RESET" "$label" "$((elapsed/60))" "$((elapsed%60))" "$last"
        index=$(( (index + 1) % ${#spinner[@]} ))
        sleep 0.25
    done
    wait "$pid"; rc=$?
    printf '\r%*s\r' 150 ''
    cat "$tmp" >> "$LOG_FILE"
    rm -f -- "$tmp"
    return "$rc"
}

# --------------------------- Cleanup / signals -------------------------------
cleanup() {
    local rc=$?
    if [[ -n "$SUDO_KEEPALIVE_PID" ]] && kill -0 "$SUDO_KEEPALIVE_PID" 2>/dev/null; then
        kill "$SUDO_KEEPALIVE_PID" 2>/dev/null || true
    fi
    if (( rc != 0 )); then
        close_last_step
        error "La instalación terminó con código $rc."
        printf ' %s%sLog:%s %s\n' "$RAIL" "$YELLOW" "$RESET" "$LOG_FILE"
    fi
    exit "$rc"
}
trap cleanup EXIT

on_err() {
    local rc=$?
    log ERROR "Unexpected error near line ${BASH_LINENO[0]:-unknown}, status=$rc"
    return "$rc"
}
trap on_err ERR

# ---------------------------- Privileges -------------------------------------
check_execution() {
    step "Comprobación del entorno"
    [[ "$EUID" -ne 0 ]] || fatal "No ejecutes install.sh como root. Usa ./install.sh."
    [[ -d "$HOME" ]] || fatal "HOME no es válido."
    [[ -f "$SCRIPT_DIR/install.sh" ]] || fatal "install.sh no se encuentra en el directorio del repositorio."
    command_exists sudo || fatal "sudo no está instalado."
    command_exists pacman || fatal "pacman no está disponible; este instalador requiere Arch Linux o un derivado."
    command_exists systemctl || fatal "systemctl no está disponible; se requiere systemd."

    sudo -v || fatal "No fue posible autenticar sudo."
    while true; do
        sleep 45
        sudo -n true || break
    done 2>/dev/null &
    SUDO_KEEPALIVE_PID=$!

    success "Ejecutando como usuario normal: $USER"
}

check_arch() {
    step "Detección de Arch Linux"
    [[ -r /etc/os-release ]] || fatal "/etc/os-release no existe."
    # shellcheck disable=SC1091
    source /etc/os-release

    local id="${ID,,}" like="${ID_LIKE,,}"
    [[ "$(uname -m)" == "x86_64" ]] || fatal "Arquitectura no soportada: $(uname -m)."
    [[ "$id" == arch || "$id" == cachyos || "$id" == endeavouros || "$id" == garuda || \
       "$id" == blackarch || "$id" == manjaro || "$id" == arcolinux || "$like" == *arch* ]] || \
       fatal "'$NAME' no parece ser una distribución basada en Arch Linux."

    info "Distribución: ${NAME:-Arch Linux}"
    info "Kernel: $(uname -r)"

    if [[ -e /var/lib/pacman/db.lck ]]; then
        local active=false p
        for p in pacman makepkg yay paru; do
            if pgrep -x "$p" >/dev/null 2>&1; then active=true; break; fi
        done
        if [[ "$active" == true ]]; then
            fatal "pacman/AUR está ejecutándose y existe el lock /var/lib/pacman/db.lck."
        fi
        warn "Existe un lock huérfano de pacman."
        read -r -p "  ¿Eliminarlo? [s/N]: " answer
        [[ "$answer" =~ ^[sS]$ ]] || fatal "No se puede continuar con el lock presente."
        sudo rm -f /var/lib/pacman/db.lck || fatal "No se pudo eliminar el lock de pacman."
    fi

    command_exists curl || sudo pacman -S --needed --noconfirm curl >>"$LOG_FILE" 2>&1 || true
    if ! curl -fsS --connect-timeout 5 https://archlinux.org >/dev/null 2>&1; then
        fatal "No se detectó conexión funcional hacia archlinux.org."
    fi
    success "Sistema Arch-family y conectividad comprobados."
}

# ----------------------------- Packages -------------------------------------
sync_system() {
    step "Sincronización del sistema"
    # Installing new packages on a stale/partially-synced system is the most
    # common cause of "archivos en conflicto" errors (e.g. two shared library
    # packages like ffmpeg/vmaf disagreeing about which owns a file). A full
    # sync + upgrade before touching anything else keeps every package on the
    # same, consistent set of versions and avoids that class of failure.
    info "Sincronizando repositorios y actualizando paquetes existentes..."
    if ! run_with_live_progress "pacman -Syu" sudo pacman -Syu --noconfirm; then
        fatal "No se pudo sincronizar/actualizar el sistema. Revisa $LOG_FILE y vuelve a ejecutar el instalador."
    fi
    success "Sistema sincronizado y actualizado."
}

install_pkg() {
    local pkg="$1" required="${2:-yes}"
    if is_pkg_installed "$pkg"; then return 0; fi
    if sudo pacman -S --needed --noconfirm "$pkg" >>"$LOG_FILE" 2>&1; then return 0; fi

    # A system that wasn't fully synced/upgraded can leave files on disk that
    # pacman refuses to overwrite ("archivos en conflicto", e.g. ffmpeg/vmaf
    # shared libraries). sync_system() already mitigates this, but as a last
    # resort retry once forcing pacman to overwrite those stray files instead
    # of aborting the whole installation.
    log WARNING "pacman -S $pkg failed, retrying with --overwrite '*' (possible file conflict)."
    if sudo pacman -S --needed --noconfirm --overwrite '*' "$pkg" >>"$LOG_FILE" 2>&1; then
        log WARNING "Package '$pkg' required --overwrite to resolve file conflicts."
        return 0
    fi

    if [[ "$required" == yes ]]; then FAILED_REQUIRED+=("$pkg"); else FAILED_OPTIONAL+=("$pkg"); fi
    return 1
}

install_base_deps() {
    step "Dependencias base"
    local pkgs=(base-devel git rsync curl ca-certificates unzip xdg-utils xdg-user-dirs fontconfig)
    local pkg
    for pkg in "${pkgs[@]}"; do
        if install_pkg "$pkg" yes; then
            printf '  %-30s %s✔%s\n' "$pkg" "$GREEN" "$RESET"
        else
            printf '  %-30s %s✖%s\n' "$pkg" "$RED" "$RESET"
        fi
    done
    ((${#FAILED_REQUIRED[@]} == 0)) || fatal "Dependencias base faltantes: ${FAILED_REQUIRED[*]}"
    success "Dependencias base disponibles."
}

install_aur_helper() {
    step "Configuración de AUR"
    if command_exists yay; then AUR_HELPER="yay"; fi
    if [[ -z "$AUR_HELPER" ]] && command_exists paru; then AUR_HELPER="paru"; fi

    if [[ -n "$AUR_HELPER" ]]; then
        success "AUR helper detectado: $AUR_HELPER"
        return 0
    fi

    info "No se encontró yay/paru. Instalando yay-bin para $USER."
    local tmp="$(mktemp -d -p /tmp techogr-yay.XXXXXX)"
    if ! git clone --depth=1 https://aur.archlinux.org/yay-bin.git "$tmp/yay-bin" >>"$LOG_FILE" 2>&1; then
        rm -rf -- "$tmp"
        fatal "No se pudo clonar yay-bin desde AUR."
    fi
    if ! (cd "$tmp/yay-bin" && makepkg -si --noconfirm) >>"$LOG_FILE" 2>&1; then
        rm -rf -- "$tmp"
        fatal "No se pudo compilar/instalar yay-bin."
    fi
    rm -rf -- "$tmp"
    command_exists yay || fatal "yay no quedó disponible en PATH."
    AUR_HELPER="yay"
    success "yay instalado correctamente."
}

prepare_rust_for_eww() {
    step "Preparando Rust stable para Eww"

    # Exactly the sequence that works reliably on Arch for Eww:
    #   1) base-devel
    #   2) rustup (replacing rust if pacman reports the conflict)
    #   3) rustup default stable
    #
    # Every pacman call is non-interactive so the installer cannot appear frozen
    # waiting for an invisible confirmation.

    if ! command_exists rustup; then
        info "Instalando rustup (si existe rust, pacman resolverá el conflicto automáticamente)..."
        if ! run_with_live_progress "pacman → rustup" sudo pacman -S --needed --noconfirm rustup; then
            fatal "No se pudo instalar rustup. Revisa $LOG_FILE."
        fi
    fi

    export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"

    command_exists rustup || fatal "rustup no está disponible después de su instalación."

    if ! rustup toolchain list 2>/dev/null | grep -q '^stable'; then
        info "Instalando toolchain Rust stable (perfil minimal)..."
        if ! run_with_live_progress "rustup → stable" rustup toolchain install stable --profile minimal; then
            fatal "No se pudo instalar el toolchain Rust stable."
        fi
    fi

    info "Seleccionando Rust stable como toolchain predeterminado..."
    rustup default stable >>"$LOG_FILE" 2>&1 || fatal "No se pudo seleccionar Rust stable."

    command_exists cargo || fatal "Cargo no está disponible después de preparar Rust stable."
    success "Rust stable + Cargo están listos."
}

install_eww() {
    step "Instalación de Eww"
    export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"

    if command_exists eww; then
        success "Eww ya está instalado: $(eww --version 2>/dev/null | head -n1 || echo 'versión disponible')"
        return 0
    fi

    prepare_rust_for_eww

    # Dependencies used by Eww's X11 build.
    local deps=(pkgconf gtk3 gtk-layer-shell pango gdk-pixbuf2 cairo glib2 dbus libdbusmenu-gtk3)
    local dep
    info "Instalando dependencias de compilación de Eww..."
    for dep in "${deps[@]}"; do
        install_pkg "$dep" yes || true
    done
    ((${#FAILED_REQUIRED[@]} == 0)) || fatal "No se pudieron instalar dependencias de Eww: ${FAILED_REQUIRED[*]}"

    if [[ -n "$AUR_HELPER" ]]; then
        info "Instalando Eww desde AUR con $AUR_HELPER + Rust stable..."
        if run_with_live_progress "AUR → eww" "$AUR_HELPER" -S --needed --noconfirm eww; then
            command_exists eww || export PATH="$HOME/.local/bin:$PATH"
            if command_exists eww; then
                success "Eww instalado correctamente desde AUR."
                return 0
            fi
        fi
        warn "La instalación AUR de eww falló. Se probará eww-git como respaldo."

        if run_with_live_progress "AUR → eww-git" "$AUR_HELPER" -S --needed --noconfirm eww-git; then
            if command_exists eww; then
                success "Eww instalado correctamente mediante eww-git."
                return 0
            fi
        fi
    fi

    # Last-resort source build. Still uses the same Rust stable prepared above.
    info "AUR no pudo instalar Eww; compilando desde upstream con backend X11."
    local build_dir="$HOME/.local/state/techogr-bspwm/build/eww-source"
    mkdir -p -- "$(dirname -- "$build_dir")"
    rm -rf -- "$build_dir"

    if ! run_with_live_progress "Git → Eww upstream" git clone --depth=1 https://github.com/elkowar/eww.git "$build_dir"; then
        fatal "No se pudo descargar Eww desde upstream."
    fi

    if ! run_with_live_progress "Cargo → Eww X11" bash -lc "cd \"$build_dir\" && cargo build --release --no-default-features --features x11"; then
        fatal "No se pudo compilar Eww. Revisa $LOG_FILE."
    fi

    [[ -x "$build_dir/target/release/eww" ]] || fatal "La compilación terminó sin generar el binario Eww."
    install -Dm755 "$build_dir/target/release/eww" "$HOME/.local/bin/eww"
    command_exists eww || export PATH="$HOME/.local/bin:$PATH"
    command_exists eww || fatal "Eww no aparece después de instalar el binario."
    success "Eww compilado e instalado en ~/.local/bin/eww."
}

install_packages() {
    step "Paquetes del entorno TechOGR"

    # This list is based on commands referenced by THIS repository's config tree.
    # No packages from another dotfiles repository are added here.
    local official=(
        xorg-server xorg-xinit xorg-xrandr xorg-xrdb xorg-xsetroot xorg-xset
        xorg-xprop xorg-xinput xorg-xauth xorg-xdpyinfo xorg-xwininfo
        bspwm sxhkd polybar rofi picom dunst libnotify jgmenu
        kitty feh imagemagick jq maim xdotool xdo xclip xsettingsd hsetroot
        brightnessctl pamixer playerctl alsa-utils
        dbus polkit-gnome lxsession
        mpd mpc ncmpcpp mpv
        zsh zsh-autosuggestions zsh-syntax-highlighting zsh-history-substring-search fzf
        yazi zathura zathura-pdf-mupdf
        clipcat
        ttf-jetbrains-mono-nerd ttf-font-awesome noto-fonts-emoji
        papirus-icon-theme
        xss-lock
        rsync thunar eza bat
        python-gobject python-cairo python-pillow ffmpeg
        # HUD tools (Dock, AppLauncher, RiceEditor, UserCard, MusicPlayer,
        # ScreenShoTer, PowerMenu, AvatarForge, BarCtl auto-hide) are GTK3
        gtk3
        # system monitor (btop), night light, keyboard layout on the
        # lockscreen, screenshot sound (paplay)
        btop redshift xorg-setxkbmap libpulse
    )
    # bluez: Bluetooth toggles of UserCard / polybar module
    local optional=(networkmanager network-manager-applet pavucontrol bluez bluez-utils)
    local pkg

    for pkg in "${official[@]}"; do
        install_pkg "$pkg" yes || true
    done
    for pkg in "${optional[@]}"; do
        install_pkg "$pkg" no || true
    done

    ((${#FAILED_REQUIRED[@]} == 0)) || fatal "Paquetes obligatorios faltantes: ${FAILED_REQUIRED[*]}"
    success "Paquetes oficiales instalados."

    # Brave: prefer brave-bin from AUR. If an official/derivative brave package exists,
    # use it before falling back to the AUR binary package.
    if command_exists brave-browser || command_exists brave; then
        success "Brave ya está disponible."
    elif is_pkg_installed brave; then
        success "Brave ya está instalado."
    else
        info "Instalando Brave desde AUR..."
        if ! run_with_live_progress "AUR → brave-bin" "$AUR_HELPER" -S --needed --noconfirm brave-bin; then
            warn "No se pudo instalar brave-bin; el resto del rice puede continuar."
            FAILED_OPTIONAL+=("brave-bin")
        fi
    fi

    # fzf-tab is an AUR zsh completion plugin used by the repository's zsh setup.
    if is_pkg_installed fzf-tab; then
        success "fzf-tab ya está instalado."
    else
        info "Instalando fzf-tab desde AUR..."
        if run_with_live_progress "AUR → fzf-tab" "$AUR_HELPER" -S --needed --noconfirm fzf-tab; then
            success "fzf-tab instalado correctamente."
        else
            warn "No se pudo instalar fzf-tab desde AUR; se registró el fallo y se continúa."
            FAILED_OPTIONAL+=("fzf-tab")
        fi
    fi

    # Bibata-Modern-Classic is the cursor theme set in gtk-3.0/gtk-4.0,
    # xsettingsd, ~/.icons/default and bspwmrc. It is only packaged in AUR.
    if is_pkg_installed bibata-cursor-theme || is_pkg_installed bibata-cursor-theme-bin; then
        success "Bibata cursor theme ya está instalado."
    else
        info "Instalando Bibata cursor theme desde AUR..."
        if run_with_live_progress "AUR → bibata-cursor-theme-bin" "$AUR_HELPER" -S --needed --noconfirm bibata-cursor-theme-bin; then
            success "Bibata cursor theme instalado correctamente."
        else
            warn "No se pudo instalar bibata-cursor-theme-bin; el cursor usará el tema por defecto."
            FAILED_OPTIONAL+=("bibata-cursor-theme-bin")
        fi
    fi
}

install_lockscreen() {
    step "Lockscreen"
    # Prefer betterlockscreen + i3lock-color. Fall back to i3lock.
    local lock_ok=false
    if command_exists betterlockscreen; then lock_ok=true; fi
    if [[ "$lock_ok" == false ]]; then
        if run_with_live_progress "AUR → betterlockscreen" "$AUR_HELPER" -S --needed --noconfirm betterlockscreen; then
            command_exists betterlockscreen && lock_ok=true
        fi
    fi

    if [[ "$lock_ok" == false ]] && ! command_exists i3lock-color; then
        run_with_live_progress "AUR → i3lock-color" "$AUR_HELPER" -S --needed --noconfirm i3lock-color || true
    fi

    if [[ "$lock_ok" == false ]] && ! command_exists betterlockscreen && ! command_exists i3lock-color; then
        install_pkg i3lock yes || true
    fi

    # Use the rice's own default wallpaper (DEFAULT_WALL) for the lockscreen.
    # ScreenLocker keeps it in sync afterwards whenever the wallpaper changes.
    local rice_dir="$SCRIPT_DIR/config/bspwm/rices/crackone"
    local default_wall wallpaper
    default_wall=$(sed -n 's/^DEFAULT_WALL="\(.*\)"/\1/p' "$rice_dir/theme-config.bash")
    wallpaper="$rice_dir/walls/${default_wall##*/}"
    [[ -f "$wallpaper" ]] || wallpaper=$(find "$rice_dir/walls" -type f \( -iname '*.jpg' -o -iname '*.png' \) 2>/dev/null | sort | head -n1)
    if command_exists betterlockscreen && [[ -f "$wallpaper" ]]; then
        info "Preparando Betterlockscreen con el wallpaper predeterminado del rice..."
        if run_with_live_progress "Betterlockscreen → wallpaper" betterlockscreen -u "$wallpaper" --fx dim; then
            success "Lockscreen sincronizado con $(basename "$wallpaper")."
        else
            warn "No se pudo generar la caché de Betterlockscreen con el wallpaper predeterminado."
        fi
    elif [[ ! -f "$wallpaper" ]]; then
        warn "No se encontró el wallpaper predeterminado para el lockscreen: $wallpaper"
    fi
    success "Lockscreen preparado."
}

# ----------------------------- Backup / Deploy -------------------------------
# ------------------------- Hardware / drivers --------------------------------
# Filled by detect_hardware(); used by install_drivers(), setup_display_manager()
# and tune_for_hardware().
VIRT="none"; CPU_VENDOR=""; GPU_VENDORS=""; NVIDIA_IDS=()
HAS_BATTERY=false; HAS_BLUETOOTH=false; HAS_WIFI=false; HAS_TOUCHPAD=false

# pacman first, the AUR helper as a fallback (for packages that only some
# Arch derivatives ship, e.g. nvidia-580xx-* is in CachyOS but AUR on Arch).
install_any() {
    local pkg="$1" required="${2:-no}"
    is_pkg_installed "$pkg" && return 0
    sudo pacman -S --needed --noconfirm "$pkg" >>"$LOG_FILE" 2>&1 && return 0
    if [[ -n "$AUR_HELPER" ]] && "$AUR_HELPER" -S --needed --noconfirm "$pkg" >>"$LOG_FILE" 2>&1; then
        return 0
    fi
    if [[ "$required" == yes ]]; then FAILED_REQUIRED+=("$pkg"); else FAILED_OPTIONAL+=("$pkg"); fi
    return 1
}

pkg_status() {   # pkg_status <pkg> [required] -> prints a ✔/✖ row
    if install_any "$1" "${2:-no}"; then
        printf '  %-30s %s✔%s\n' "$1" "$GREEN" "$RESET"
    else
        printf '  %-30s %s✖%s\n' "$1" "$RED" "$RESET"
    fi
}

enable_service() {   # enable_service <unit>: only when it exists
    systemctl cat "$1" >/dev/null 2>&1 || return 0
    sudo systemctl enable --now "$1" >>"$LOG_FILE" 2>&1 && log INFO "enabled $1" ||
        warn "No se pudo habilitar $1."
}

detect_hardware() {
    step "Detección de hardware"
    install_pkg pciutils yes || true
    install_pkg usbutils no || true

    VIRT="$(systemd-detect-virt --vm 2>/dev/null || true)"
    [[ -n "$VIRT" ]] || VIRT="none"

    case "$(grep -m1 '^vendor_id' /proc/cpuinfo 2>/dev/null | awk '{print $3}')" in
        GenuineIntel) CPU_VENDOR=intel ;;
        AuthenticAMD) CPU_VENDOR=amd ;;
    esac

    # Display controllers: class 03xx (VGA 0300, 3D 0302, display 0380)
    local line id
    while read -r line; do
        case "${line,,}" in
            *'[10de:'*) GPU_VENDORS+=" nvidia"
                        id="$(grep -oE '\[10de:[0-9a-f]{4}\]' <<<"${line,,}" | tail -n1 | cut -c7-10)"
                        [[ -n "$id" ]] && NVIDIA_IDS+=("$id") ;;
            *'[1002:'*) GPU_VENDORS+=" amd" ;;
            *'[8086:'*) GPU_VENDORS+=" intel" ;;
            *'[15ad:'*) GPU_VENDORS+=" vmware" ;;
            *'[80ee:'*) GPU_VENDORS+=" vbox" ;;
            *'[1af4:'*|*'[1b36:'*|*'[1234:'*) GPU_VENDORS+=" qemu" ;;
        esac
    done < <(lspci -nn 2>/dev/null | grep -E '\[03[0-9a-f]{2}\]')

    compgen -G '/sys/class/power_supply/BAT*' >/dev/null && HAS_BATTERY=true
    compgen -G '/sys/class/bluetooth/*' >/dev/null && HAS_BLUETOOTH=true
    compgen -G '/sys/class/net/*/wireless' >/dev/null && HAS_WIFI=true
    grep -qiE 'touchpad|trackpad|synaptics|elan' /proc/bus/input/devices 2>/dev/null && HAS_TOUCHPAD=true

    info "Virtualización: $VIRT"
    info "CPU: ${CPU_VENDOR:-desconocida} · GPU:${GPU_VENDORS:- desconocida}${NVIDIA_IDS[*]:+ (nvidia ${NVIDIA_IDS[*]})}"
    info "Batería: $HAS_BATTERY · Wi-Fi: $HAS_WIFI · Bluetooth: $HAS_BLUETOOTH · Touchpad: $HAS_TOUCHPAD"
    log INFO "lspci: $(lspci -nn 2>/dev/null | grep -E '\[03[0-9a-f]{2}\]' | tr '\n' '|')"
    success "Hardware detectado."
}

# NVIDIA driver branch from the PCI device id:
#   >= 0x1e00 Turing and newer  -> open kernel modules (current driver)
#   >= 0x1340 Maxwell / Pascal / Volta -> 580xx legacy branch (last one with them)
#   older (Kepler, Fermi...)    -> nouveau (mesa); the blobs no longer build
nvidia_branch() {
    local id=$((16#$1))
    if (( id >= 0x1e00 )); then echo open
    elif (( id >= 0x1340 )); then echo 580xx
    else echo nouveau
    fi
}

# One headers package per installed kernel, needed by every *-dkms driver.
install_kernel_headers() {
    local base
    for base in /usr/lib/modules/*/pkgbase; do
        [[ -f "$base" ]] || continue
        pkg_status "$(cat "$base")-headers"
    done
}

install_nvidia() {
    local branch="open" id b
    # the oldest card decides (a hybrid laptop has only one NVIDIA anyway)
    for id in "${NVIDIA_IDS[@]}"; do
        b="$(nvidia_branch "$id")"
        [[ "$b" == nouveau ]] && branch=nouveau && break
        [[ "$b" == 580xx ]] && branch=580xx
    done
    info "NVIDIA: rama de driver '$branch'"

    # CachyOS: its hardware tool picks the right driver + kernel module package
    if command_exists chwd && [[ "$branch" != nouveau ]]; then
        if run_with_live_progress "chwd → NVIDIA" sudo chwd -a; then
            is_pkg_installed nvidia-utils || is_pkg_installed nvidia-580xx-utils &&
                { success "Driver NVIDIA instalado con chwd."; return 0; }
        fi
        warn "chwd no instaló el driver NVIDIA; se usa la instalación genérica."
    fi

    case "$branch" in
        open)
            install_kernel_headers
            pkg_status nvidia-open-dkms
            pkg_status nvidia-utils
            pkg_status nvidia-settings
            pkg_status libva-nvidia-driver ;;
        580xx)
            install_kernel_headers
            pkg_status nvidia-580xx-dkms
            pkg_status nvidia-580xx-utils
            pkg_status nvidia-580xx-settings ;;
        nouveau)
            warn "GPU NVIDIA antigua: se usa nouveau (mesa)."
            return 0 ;;
    esac

    # DRM KMS (needed for a smooth X/picom and suspend). Recent drivers
    # default to it, this makes it explicit for older ones.
    printf 'options nvidia_drm modeset=1 fbdev=1\n' |
        sudo tee /etc/modprobe.d/nvidia-techogr.conf >/dev/null
    local svc
    for svc in nvidia-suspend.service nvidia-hibernate.service nvidia-resume.service; do
        enable_service "$svc"
    done
    command_exists mkinitcpio && run_with_live_progress "mkinitcpio -P" sudo mkinitcpio -P || true
}

install_drivers() {
    step "Drivers y firmware"
    local gpu

    # Microcode (the bootloader/mkinitcpio pick it up on the next kernel update)
    if [[ "$VIRT" == none ]]; then
        case "$CPU_VENDOR" in
            intel) pkg_status intel-ucode ;;
            amd)   pkg_status amd-ucode ;;
        esac
        pkg_status linux-firmware
        pkg_status sof-firmware          # modern Intel/AMD laptop audio
        pkg_status alsa-firmware
    fi

    # Graphics: mesa is the base of every open driver (and of the VMs)
    pkg_status mesa yes
    pkg_status mesa-utils
    pkg_status vulkan-icd-loader
    pkg_status xf86-input-libinput yes
    for gpu in $GPU_VENDORS; do
        case "$gpu" in
            intel)  pkg_status vulkan-intel
                    pkg_status intel-media-driver ;;
            amd)    pkg_status vulkan-radeon
                    pkg_status xf86-video-amdgpu ;;
            nvidia) install_nvidia ;;
        esac
    done

    # Virtual machines: guest tools (clipboard, resize, time sync)
    case "$VIRT" in
        vmware)
            pkg_status open-vm-tools
            pkg_status xf86-input-vmmouse
            pkg_status gtkmm3                # vmware-user (copy/paste, drag & drop)
            enable_service vmtoolsd.service
            enable_service vmware-vmblock-fuse.service ;;
        oracle)
            pkg_status virtualbox-guest-utils
            enable_service vboxservice.service ;;
        kvm|qemu)
            pkg_status qemu-guest-agent
            pkg_status spice-vdagent
            enable_service qemu-guest-agent.service ;;
        microsoft)
            pkg_status hyperv
            enable_service hv_kvp_daemon.service
            enable_service hv_vss_daemon.service ;;
    esac

    # Audio: PipeWire (pamixer/paplay/playerctl talk to it through pipewire-pulse).
    # A system that already runs PulseAudio keeps it (both provide libpulse).
    if is_pkg_installed pulseaudio && ! is_pkg_installed pipewire-pulse; then
        info "PulseAudio ya instalado; se conserva."
    else
        local p
        for p in pipewire pipewire-pulse pipewire-alsa wireplumber; do pkg_status "$p"; done
        systemctl --user enable pipewire.socket pipewire-pulse.socket wireplumber.service >>"$LOG_FILE" 2>&1 || true
    fi

    # Network: NetworkManager, unless another manager already owns the links
    local other=""
    for svc in systemd-networkd.service iwd.service dhcpcd.service connman.service; do
        systemctl is-enabled --quiet "$svc" 2>/dev/null && other="$svc"
    done
    if [[ -n "$other" ]] && ! systemctl is-enabled --quiet NetworkManager.service 2>/dev/null; then
        warn "Red gestionada por $other; no se habilita NetworkManager."
    elif is_pkg_installed networkmanager; then
        enable_service NetworkManager.service
    fi

    # Bluetooth
    if [[ "$HAS_BLUETOOTH" == true ]] && is_pkg_installed bluez; then
        enable_service bluetooth.service
    fi

    # Laptop: power profiles + touchpad tap-to-click / natural scroll
    if [[ "$HAS_BATTERY" == true ]]; then
        if ! is_pkg_installed tlp && ! is_pkg_installed auto-cpufreq; then
            pkg_status power-profiles-daemon && enable_service power-profiles-daemon.service
        fi
        pkg_status acpi
    fi
    if [[ "$HAS_TOUCHPAD" == true && ! -e /etc/X11/xorg.conf.d/30-touchpad.conf ]]; then
        sudo install -Dm644 /dev/stdin /etc/X11/xorg.conf.d/30-touchpad.conf <<'EOF_TP'
Section "InputClass"
    Identifier "TechOGR touchpad"
    MatchIsTouchpad "on"
    Driver "libinput"
    Option "Tapping" "on"
    Option "NaturalScrolling" "true"
    Option "DisableWhileTyping" "on"
EndSection
EOF_TP
        success "Touchpad: tap-to-click y scroll natural."
    fi

    success "Drivers y servicios del hardware listos."
}

# Per-machine defaults for the deployed config (runs after config/ is copied).
tune_for_hardware() {
    local picom="$HOME/.config/bspwm/config/picom/picom.conf"
    # vmwgfx oopses with picom's GLX backend (NULL deref in
    # vmw_bo_dirty_transfer_to_res); xrender is stable in every VM.
    if [[ "$VIRT" != none && -f "$picom" ]]; then
        sed -i -E 's/^backend\s*=.*/backend = "xrender";/' "$picom"
        info "Máquina virtual: picom usa el backend xrender."
    fi
    # SetSysVars re-detects battery/backlight/network on the next login
    rm -f -- "$HOME/.config/bspwm/config/.sys"
}

# ------------------------------ Deploy ---------------------------------------
backup_path() {
    local src="$1"
    local rel="$2"
    [[ -e "$src" || -L "$src" ]] || return 0
    mkdir -p -- "$BACKUP_DIR/$(dirname -- "$rel")"
    cp -a -- "$src" "$BACKUP_DIR/$rel"
}

create_backup() {
    step "Respaldo de configuraciones existentes"
    mkdir -p -- "$BACKUP_DIR"

    # Only back up locations that this repository manages.
    local cfg_dirs=(
        bspwm alacritty cava clipcat dunst geany ghostty gtk-3.0 gtk-4.0
        jgmenu kitty mpd mpv ncmpcpp nvim paru st yazi zathura zsh
    )
    local cfg
    for cfg in "${cfg_dirs[@]}"; do
        backup_path "$HOME/.config/$cfg" ".config/$cfg"
    done
    backup_path "$HOME/.zshrc" ".zshrc"

    # Old standalone paths that may have been installed by previous installers.
    # They are backed up, not blindly deleted.
    local legacy=(sxhkd polybar rofi picom)
    for cfg in "${legacy[@]}"; do
        backup_path "$HOME/.config/$cfg" ".config/$cfg"
    done

    cat > "$BACKUP_DIR/restore.sh" <<RESTORE
#!/usr/bin/env bash
set -e
BACKUP_DIR="$(cd -- "$(dirname -- "\${BASH_SOURCE[0]}")" && pwd -P)"
mkdir -p "\$HOME/.config"
if [[ -d "\$BACKUP_DIR/.config" ]]; then
    cp -a "\$BACKUP_DIR/.config/." "\$HOME/.config/"
fi
for f in .zshrc; do
    [[ -e "\$BACKUP_DIR/\$f" ]] && cp -a "\$BACKUP_DIR/\$f" "\$HOME/\$f"
done
printf 'Restauración completada desde %s\n' "\$BACKUP_DIR"
RESTORE
    chmod +x "$BACKUP_DIR/restore.sh"
    success "Backup creado: $BACKUP_DIR"
}

sync_tree() {
    local src="$1" dst="$2" label="$3"
    [[ -d "$src" ]] || { warn "$label no existe en el repositorio; se omitirá."; return 0; }
    mkdir -p -- "$dst"
    if ! rsync -a --delete -- "$src/" "$dst/" >>"$LOG_FILE" 2>&1; then
        fatal "No se pudo desplegar $label desde el repositorio."
    fi
    success "$label desplegado exactamente."
}

prepare_wallpaper_dir() {
    # Do not deploy or modify anything else under $HOME.
    # The operating system already creates the user's home directory and its
    # standard XDG folders. We only ensure the exact wallpaper path required
    # by the TechOGR repository exists.
    mkdir -p -- "$HOME/Imágenes/Wallpapers"
}

copy_repository_content() {
    step "Despliegue exacto de TechOGR"

    prepare_wallpaper_dir
    mkdir -p -- "$HOME/.config" "$HOME/.local/bin" "$HOME/.local/share/fonts" "$HOME/.local/share/applications"

    # 1. config/ is the canonical source for ~/.config: each managed folder is
    #    mirrored exactly, the rest of ~/.config (browsers, other apps) is kept.
    #    systemd/ is merged (the user may have units of their own).
    local dir name
    for dir in "$SCRIPT_DIR"/config/*/; do
        name="$(basename -- "$dir")"
        if [[ "$name" == systemd ]]; then
            mkdir -p -- "$HOME/.config/systemd"
            rsync -a -- "$dir" "$HOME/.config/systemd/" >>"$LOG_FILE" 2>&1 || fatal "No se pudo desplegar config/systemd."
        else
            sync_tree "${dir%/}" "$HOME/.config/$name" "config/$name → ~/.config/$name" >/dev/null
        fi
    done
    success "config/ → ~/.config desplegado (${HOME}/.config conserva lo ajeno al rice)."

    # 2. Never deploy the repository's home/ directory into $HOME.
    #    The user's home and standard folders are managed by the OS.

    # 2. Wallpapers are copied only to the exact path used by the repository
    #    theme-config: ~/Imágenes/Wallpapers/noche_car_man.jpg.
    if [[ -d "$SCRIPT_DIR/Wallpapers" ]]; then
        mkdir -p -- "$HOME/Imágenes/Wallpapers"
        rsync -a "$SCRIPT_DIR/Wallpapers/" "$HOME/Imágenes/Wallpapers/" >>"$LOG_FILE" 2>&1 || fatal "No se pudo desplegar Wallpapers/."
        success "Wallpapers/ desplegado únicamente en ~/Imágenes/Wallpapers."
    fi

    # 4. misc/ gets mapped according to the role of each directory in THIS repo.
    if [[ -d "$SCRIPT_DIR/misc/bin" ]]; then
        rsync -a "$SCRIPT_DIR/misc/bin/" "$HOME/.local/bin/" >>"$LOG_FILE" 2>&1 || fatal "No se pudo desplegar misc/bin."
    fi
    if [[ -d "$SCRIPT_DIR/misc/fonts" ]]; then
        rsync -a "$SCRIPT_DIR/misc/fonts/" "$HOME/.local/share/fonts/" >>"$LOG_FILE" 2>&1 || fatal "No se pudo desplegar misc/fonts."
    fi
    if [[ -d "$SCRIPT_DIR/misc/applications" ]]; then
        rsync -a "$SCRIPT_DIR/misc/applications/" "$HOME/.local/share/applications/" >>"$LOG_FILE" 2>&1 || fatal "No se pudo desplegar misc/applications."
    fi
    if [[ -d "$SCRIPT_DIR/misc/asciiart" ]]; then
        rsync -a --delete "$SCRIPT_DIR/misc/asciiart/" "$HOME/.local/share/asciiart/" >>"$LOG_FILE" 2>&1 || fatal "No se pudo desplegar misc/asciiart."
    fi
    if [[ -d "$SCRIPT_DIR/misc/startup-page" ]]; then
        rsync -a --delete "$SCRIPT_DIR/misc/startup-page/" "$HOME/.local/share/startup-page/" >>"$LOG_FILE" 2>&1 || fatal "No se pudo desplegar misc/startup-page."
    fi

    # 5. The repository has a root kitty/ directory as well as config/kitty.
    #    config/kitty is canonical. If root kitty differs, report it but do not
    #    overwrite the canonical config with a second source of truth.
    if [[ -d "$SCRIPT_DIR/kitty" && -d "$SCRIPT_DIR/config/kitty" ]]; then
        if ! diff -qr -- "$SCRIPT_DIR/kitty" "$SCRIPT_DIR/config/kitty" >/dev/null 2>&1; then
            warn "Se detectaron diferencias entre kitty/ y config/kitty del propio repo; se conserva config/kitty como fuente canónica."
            log WARNING "Repository has two differing Kitty trees: kitty/ vs config/kitty"
        else
            info "kitty/ y config/kitty son idénticos; se evita copiar dos veces el mismo contenido."
        fi
    elif [[ -d "$SCRIPT_DIR/kitty" && ! -d "$SCRIPT_DIR/config/kitty" ]]; then
        rsync -a --delete "$SCRIPT_DIR/kitty/" "$HOME/.config/kitty/" >>"$LOG_FILE" 2>&1 || fatal "No se pudo desplegar kitty/."
    fi

    fc-cache -r >>"$LOG_FILE" 2>&1 || true
    success "Contenido de TechOGR desplegado sin modificar archivos versionados."
}

deploy_repository_home() {
    step "Aplicando archivos de home/ del repositorio"

    # The user's HOME directory already exists. We only deploy the CONTENTS
    # of this repository's home/ directory, after packages such as zsh and
    # fzf-tab are installed, so .zshrc can be loaded with its dependencies.
    if [[ ! -d "$SCRIPT_DIR/home" ]]; then
        warn "No existe home/ en el repositorio; se omite."
        return 0
    fi

    if rsync -a -- "$SCRIPT_DIR/home/" "$HOME/" >>"$LOG_FILE" 2>&1; then
        success "Contenido de home/ aplicado exactamente a $HOME."
    else
        fatal "No se pudo desplegar el contenido de home/."
    fi
}

install_pacman_hook() {
    [[ -f "$SCRIPT_DIR/misc/polybar-update.hook" ]] || return 0
    sudo install -Dm644 "$SCRIPT_DIR/misc/polybar-update.hook" /etc/pacman.d/hooks/polybar-update.hook || \
        fatal "No se pudo instalar misc/polybar-update.hook."
    success "Hook de pacman instalado desde misc/polybar-update.hook."
}

# -------------------------- Sessions / Services ------------------------------
setup_display_manager() {
    step "Display Manager / login TechOGR"

    local active=""
    active="$(systemctl show -p Id --value display-manager.service 2>/dev/null || true)"
    [[ "$active" == display-manager.service ]] && active=""

    # The TechOGR login lives in LightDM. Another DM (sddm, gdm, ly...) is
    # replaced only with the user's consent; default yes, non-interactive = keep.
    local use_lightdm=true
    if [[ -n "$active" && "$active" != lightdm.service ]]; then
        use_lightdm=false
        if [[ -t 0 ]]; then
            local answer
            read -r -p "  Display Manager actual: $active. ¿Reemplazarlo por el login TechOGR (LightDM)? [S/n]: " answer
            [[ "$answer" =~ ^[nN]$ ]] || use_lightdm=true
        fi
        if [[ "$use_lightdm" == true ]]; then
            sudo systemctl disable "$active" >>"$LOG_FILE" 2>&1 || warn "No se pudo deshabilitar $active."
        else
            success "Display Manager existente conservado: $active"
        fi
    fi

    sudo install -Dm644 /dev/stdin /usr/share/xsessions/bspwm.desktop <<EOF_BSPWM
[Desktop Entry]
Name=BSPWM
Comment=Binary Space Partitioning Window Manager
Exec=bspwm
TryExec=bspwm
Type=Application
DesktopNames=BSPWM
EOF_BSPWM
    success "Sesión BSPWM registrada en /usr/share/xsessions/bspwm.desktop."
    [[ "$use_lightdm" == true ]] || return 0

    install_pkg lightdm yes || true
    install_pkg lightdm-gtk-greeter yes || true
    ((${#FAILED_REQUIRED[@]} == 0)) || fatal "No se pudo instalar LightDM."
    install_any lightdm-webkit2-greeter no || true
    sudo systemctl enable -f lightdm.service >>"$LOG_FILE" 2>&1 || fatal "No se pudo habilitar LightDM."

    local seat=/etc/lightdm/lightdm.conf.d/50-bspwm.conf
    sudo install -d -m755 /etc/lightdm/lightdm.conf.d
    printf '[Seat:*]\nuser-session=bspwm\ngreeter-session=lightdm-gtk-greeter\n' | sudo tee "$seat" >/dev/null

    # TechOGR login screen: lightdm-webkit2-greeter + theme "techogr",
    # the BetterLock card (user, password, session, power buttons).
    if is_pkg_installed lightdm-webkit2-greeter &&
       sudo bash "$SCRIPT_DIR/misc/lightdm/install-login.sh" "$USER" >>"$LOG_FILE" 2>&1; then
        # wallpaper, avatar and colors of the rice -> the theme's data/
        "$HOME/.config/bspwm/bin/BetterLock" --greeter >>"$LOG_FILE" 2>&1 ||
            warn "BetterLock --greeter falló; el login usará sus colores por defecto."
        success "Pantalla de login TechOGR (lightdm-webkit2-greeter) instalada."
    else
        warn "No se pudo instalar el login TechOGR; LightDM usará lightdm-gtk-greeter."
        printf '[Seat:*]\nuser-session=bspwm\ngreeter-session=lightdm-gtk-greeter\n' | sudo tee "$seat" >/dev/null
    fi

    # Fallback greeter (lightdm-gtk-greeter): the rice wallpaper, from a
    # place the lightdm user can read (not ~, which is usually 0700).
    local wallpaper=/usr/share/lightdm-webkit/themes/techogr/data/background.jpg
    if [[ ! -f "$wallpaper" ]]; then
        wallpaper="$(find "$HOME/.config/bspwm/rices/crackone/walls" -maxdepth 1 -type f \
                     \( -iname '*.jpg' -o -iname '*.png' \) 2>/dev/null | sort | head -n1)"
        if [[ -f "$wallpaper" ]]; then
            sudo install -Dm644 "$wallpaper" /usr/share/backgrounds/techogr-login.${wallpaper##*.}
            wallpaper=/usr/share/backgrounds/techogr-login.${wallpaper##*.}
        fi
    fi
    if [[ -f "$wallpaper" ]]; then
        sudo install -d -m755 /etc/lightdm/lightdm-gtk-greeter.conf.d
        printf '[greeter]\nbackground=%s\n' "$wallpaper" |
            sudo tee /etc/lightdm/lightdm-gtk-greeter.conf.d/50-techogr-background.conf >/dev/null
    fi
    success "LightDM habilitado con la sesión BSPWM por defecto."
}

configure_services() {
    info "Recargando unidades de usuario del repositorio..."
    systemctl --user daemon-reload >>"$LOG_FILE" 2>&1 || true

    if [[ -f "$HOME/.config/systemd/user/ArchUpdates.timer" ]]; then
        systemctl --user enable --now ArchUpdates.timer >>"$LOG_FILE" 2>&1 || warn "ArchUpdates.timer no pudo iniciarse ahora."
    fi

    if is_pkg_installed mpd && [[ -f "$HOME/.config/mpd/mpd.conf" ]]; then
        systemctl --user enable --now mpd.service >>"$LOG_FILE" 2>&1 || warn "MPD user service no pudo iniciarse."
    fi

    # Update XDG MIME cache after .desktop files.
    if command_exists update-desktop-database; then
        update-desktop-database "$HOME/.local/share/applications" >>"$LOG_FILE" 2>&1 || true
    fi
}

set_default_browser() {
    if ! command_exists xdg-settings; then return 0; fi
    local desktop=""
    if [[ -f /usr/share/applications/brave-browser.desktop ]]; then
        desktop="brave-browser.desktop"
    elif [[ -f /usr/share/applications/com.brave.Browser.desktop ]]; then
        desktop="com.brave.Browser.desktop"
    fi

    if [[ -n "$desktop" ]]; then
        xdg-settings set default-web-browser "$desktop" >>"$LOG_FILE" 2>&1 || true
        xdg-mime default "$desktop" x-scheme-handler/http >>"$LOG_FILE" 2>&1 || true
        xdg-mime default "$desktop" x-scheme-handler/https >>"$LOG_FILE" 2>&1 || true
        xdg-mime default "$desktop" text/html >>"$LOG_FILE" 2>&1 || true
        success "Brave configurado como navegador predeterminado."
    else
        warn "No se encontró el .desktop de Brave; se omitió el navegador predeterminado."
    fi
}

configure_shell() {
    if ! command_exists zsh; then return 0; fi
    local zsh_path
    zsh_path="$(command -v zsh)"
    if ! grep -Fxq "$zsh_path" /etc/shells; then
        echo "$zsh_path" | sudo tee -a /etc/shells >/dev/null
    fi
    if [[ "$(getent passwd "$USER" | cut -d: -f7)" != "$zsh_path" ]]; then
        sudo chsh -s "$zsh_path" "$USER" >>"$LOG_FILE" 2>&1 || warn "No se pudo cambiar la shell predeterminada a Zsh."
    fi
    configure_root_shell "$zsh_path"
}

configure_root_shell() {
    # root gets the same zsh (prompt, plugins, aliases, colorscript).
    local zsh_path="$1"
    [[ -f "$SCRIPT_DIR/home/.zshrc" ]] || return 0
    sudo install -Dm644 "$SCRIPT_DIR/home/.zshrc" /root/.zshrc >>"$LOG_FILE" 2>&1 || {
        warn "No se pudo copiar .zshrc a /root."; return 0; }
    sudo install -d -m700 /root/.config/zsh
    # colorscript + its scripts, system-wide (root has no ~/.local copy)
    if [[ -f "$SCRIPT_DIR/misc/bin/colorscript" ]]; then
        sudo install -Dm755 "$SCRIPT_DIR/misc/bin/colorscript" /usr/local/bin/colorscript
    fi
    if [[ -d "$SCRIPT_DIR/misc/asciiart" ]]; then
        sudo install -d -m755 /usr/local/share/asciiart
        sudo rsync -a --delete --chown=root:root --chmod=D755,F755 \
            "$SCRIPT_DIR/misc/asciiart/" /usr/local/share/asciiart/ >>"$LOG_FILE" 2>&1 || true
    fi
    if [[ "$(getent passwd root | cut -d: -f7)" != "$zsh_path" ]]; then
        sudo chsh -s "$zsh_path" root >>"$LOG_FILE" 2>&1 || warn "No se pudo cambiar la shell de root a Zsh."
    fi
    success "Zsh de root configurada con el mismo estilo."
}

# --------------------------- Integrity checks ---------------------------------
verify_repository_layout() {
    step "Verificación final"

    local required=(
        "$HOME/.config/bspwm/bspwmrc"
        "$HOME/.config/bspwm/config/sxhkdrc"
        "$HOME/.config/bspwm/eww"
        "$HOME/.config/bspwm/rices/crackone/walls"
    )
    local f
    for f in "${required[@]}"; do
        if [[ -e "$f" ]]; then success "Verificado: ${f#"$HOME/"}"; else warn "Falta: ${f#"$HOME/"}"; fi
    done

    if [[ -f "$HOME/Imágenes/Wallpapers/noche_car_man.jpg" ]]; then
        success "Wallpaper por defecto encontrado: ~/Imágenes/Wallpapers/noche_car_man.jpg"
    else
        warn "No se encontró noche_car_man.jpg en ~/Imágenes/Wallpapers."
    fi

    if command_exists eww; then success "Eww operativo: $(command -v eww)"; else fatal "Eww no está operativo."
    fi
}

show_summary() {
    close_last_step
    local lines=(
        '  ╔════════════════════════════════════════════════════════════╗'
        '  ║           TECHOGR BSPWM · INSTALACIÓN COMPLETADA             ║'
        '  ╚════════════════════════════════════════════════════════════╝'
    )
    local i
    printf '\n'
    for i in "${!lines[@]}"; do
        gradient_line "${lines[$i]}" "$i" "${#lines[@]}"
    done
    printf '\n  %s✓%s Configuración:  %s\n' "$GREEN" "$RESET" "$HOME/.config/bspwm"
    printf '  %s✓%s Wallpapers:     %s\n' "$GREEN" "$RESET" "$HOME/Imágenes/Wallpapers"
    printf '  %s✓%s Eww:            %s\n' "$GREEN" "$RESET" "$(command -v eww)"
    printf '  %s✓%s Backup:         %s\n' "$GREEN" "$RESET" "$BACKUP_DIR"
    printf '  %s✓%s Log:            %s\n\n' "$GREEN" "$RESET" "$LOG_FILE"
    printf '  %sAtajos clave:%s Super+Alt+m módulos de la barra · Alt+F1 ayuda general\n' "$CYAN" "$RESET"
    printf '  %sPróximo paso:%s cierra la sesión y selecciona %sBSPWM%s en tu Display Manager.\n' "$CYAN" "$RESET" "$BOLD" "$RESET"
    printf '  %sPara restaurar tu configuración:%s %s/restore.sh%s\n\n' "$CYAN" "$RESET" "$BACKUP_DIR" "$RESET"
}

main() {
    print_banner
    check_execution
    check_arch
    sync_system
    install_base_deps
    install_aur_helper
    detect_hardware
    install_drivers
    install_eww
    install_packages
    install_lockscreen
    create_backup
    copy_repository_content
    tune_for_hardware
    deploy_repository_home
    install_pacman_hook
    setup_display_manager
    configure_services
    set_default_browser
    configure_shell
    verify_repository_layout
    show_summary
}

main "$@"
