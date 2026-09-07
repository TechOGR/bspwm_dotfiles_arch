#!/usr/bin/env bash
# ==============================================================================
# TechOGR BSPWM Dotfiles Installer
# Version 8.0.0
# Arch Linux / CachyOS / EndeavourOS / Garuda / BlackArch / Manjaro / derivatives
#
# IMPORTANT:
#   This installer deploys ONLY the files present in THIS repository.
#   It does not clone gh0stzk/dotfiles or copy files from any other dotfiles repo.
#   Managed configuration files are copied as-is and are NEVER patched in place.
#
# Run:
#   chmod +x install.sh
#   ./install.sh
# ==============================================================================

set -Eeuo pipefail

SCRIPT_VERSION="8.0.0"
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
else
    RESET=''; BOLD=''; DIM=''; RED=''; GREEN=''; YELLOW=''; BLUE=''; MAGENTA=''; CYAN=''; WHITE=''; BG_BLUE=''
fi

mkdir -p -- "$(dirname -- "$LOG_FILE")"
printf '=== TechOGR BSPWM Installer %s - %s ===\n' "$SCRIPT_VERSION" "$(date)" > "$LOG_FILE"

# ------------------------------- Logging -------------------------------------
log() {
    printf '%s [%s] %s\n' "$(date '+%F %T')" "$1" "$2" >> "$LOG_FILE"
}

info() {
    printf '  %s➜%s %s\n' "$CYAN" "$RESET" "$1"
    log INFO "$1"
}

success() {
    printf '  %s✔%s %s\n' "$GREEN" "$RESET" "$1"
    log SUCCESS "$1"
}

warn() {
    printf '  %s⚠%s %s\n' "$YELLOW" "$RESET" "$1"
    log WARNING "$1"
}

error() {
    printf '  %s✖%s %s\n' "$RED" "$RESET" "$1" >&2
    log ERROR "$1"
}

step() {
    printf '\n%s%s╭─ %s%s\n' "$MAGENTA" "$BOLD" "$1" "$RESET"
    printf '%s%s│%s\n' "$MAGENTA" "$BOLD" "$RESET"
    log STEP "$1"
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
    printf '%s%s' "$CYAN" "$BOLD"
    cat <<'BANNER'
   ████████╗███████╗ ██████╗██╗  ██╗ ██████╗  ██████╗ ██████╗
   ╚══██╔══╝██╔════╝██╔════╝██║  ██║██╔═══██╗██╔════╝ ██╔══██╗
      ██║   █████╗  ██║     ███████║██║   ██║██║  ███╗██████╔╝
      ██║   ██╔══╝  ██║     ██╔══██║██║   ██║██║   ██║██╔══██╗
      ██║   ███████╗╚██████╗██║  ██║╚██████╔╝╚██████╔╝██║  ██║
      ╚═╝   ╚══════╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝
BANNER
    printf '%sTechOGR BSPWM Dotfiles Installer v%s%s\n' "$BLUE" "$SCRIPT_VERSION" "$RESET"
    printf '%sExact repository deployment • X11 • Eww • LightDM • AUR%s\n\n' "$DIM" "$RESET"
}

section_progress() {
    local current="$1" total="$2" title="$3"
    local width=46 filled=0 empty=0 i bar
    (( filled = current * width / total ))
    (( empty = width - filled ))
    bar=""
    for ((i=0; i<filled; i++)); do bar+='█'; done
    for ((i=0; i<empty; i++)); do bar+='░'; done
    printf '\n %s%s[%02d/%02d]%s %s\n' "$BOLD" "$CYAN" "$current" "$total" "$RESET" "$title"
    printf ' %s%s%s %3d%%\n' "$GREEN" "$bar" "$RESET" "$(( current * 100 / total ))"
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
        error "La instalación terminó con código $rc."
        printf '  %sLog:%s %s\n' "$YELLOW" "$RESET" "$LOG_FILE"
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
    step "1/12 · Comprobación del entorno"
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
    step "2/12 · Detección de Arch Linux"
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
install_pkg() {
    local pkg="$1" required="${2:-yes}"
    if is_pkg_installed "$pkg"; then return 0; fi
    if sudo pacman -S --needed --noconfirm "$pkg" >>"$LOG_FILE" 2>&1; then return 0; fi
    if [[ "$required" == yes ]]; then FAILED_REQUIRED+=("$pkg"); else FAILED_OPTIONAL+=("$pkg"); fi
    return 1
}

install_base_deps() {
    step "3/12 · Dependencias base"
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
    step "4/12 · Configuración de AUR"
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
    step "5/12 · Preparando Rust stable para Eww"

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
    step "6/12 · Instalación de Eww"
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
    step "7/12 · Paquetes del entorno TechOGR"

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
        zsh zsh-autosuggestions zsh-syntax-highlighting fzf
        yazi zathura zathura-pdf-mupdf
        clipcat
        ttf-jetbrains-mono-nerd ttf-font-awesome noto-fonts-emoji
        papirus-icon-theme
        xss-lock
        rsync
    )
    local optional=(networkmanager network-manager-applet pavucontrol)
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
}

install_lockscreen() {
    step "8/12 · Lockscreen"
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

    # Use the repository's exact default wallpaper for the lockscreen as well.
    local wallpaper="$HOME/Imágenes/Wallpapers/noche_car_man.jpg"
    if command_exists betterlockscreen && [[ -f "$wallpaper" ]]; then
        info "Preparando Betterlockscreen con el wallpaper predeterminado del rice..."
        if run_with_live_progress "Betterlockscreen → wallpaper" betterlockscreen -u "$wallpaper" --blur 0.5; then
            success "Lockscreen sincronizado con noche_car_man.jpg."
        else
            warn "No se pudo generar la caché de Betterlockscreen con el wallpaper predeterminado."
        fi
    elif [[ ! -f "$wallpaper" ]]; then
        warn "No se encontró el wallpaper predeterminado para el lockscreen: $wallpaper"
    fi
    success "Lockscreen preparado."
}

# ----------------------------- Backup / Deploy -------------------------------
backup_path() {
    local src="$1"
    local rel="$2"
    [[ -e "$src" || -L "$src" ]] || return 0
    mkdir -p -- "$BACKUP_DIR/$(dirname -- "$rel")"
    cp -a -- "$src" "$BACKUP_DIR/$rel"
}

create_backup() {
    step "9/12 · Respaldo de configuraciones existentes"
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
    step "10/12 · Despliegue exacto de TechOGR"

    prepare_wallpaper_dir
    mkdir -p -- "$HOME/.config" "$HOME/.local/bin" "$HOME/.local/share/fonts" "$HOME/.local/share/applications"

    # 1. config/ is the canonical source for ~/.config.
    sync_tree "$SCRIPT_DIR/config" "$HOME/.config" "config/ → ~/.config"

    # 2. Never deploy the repository's home/ directory into $HOME.
    #    The user's home and standard folders are managed by the OS.

    # 2. Wallpapers are copied only to the exact path used by the repository
    #    theme-config: ~/Imágenes/Wallpapers/noche_car_man.jpg.
    if [[ -d "$SCRIPT_DIR/Wallpapers" ]]; then
        mkdir -p -- "$HOME/Imágenes/Wallpapers"
        rsync -a --delete "$SCRIPT_DIR/Wallpapers/" "$HOME/Imágenes/Wallpapers/" >>"$LOG_FILE" 2>&1 || fatal "No se pudo desplegar Wallpapers/."
        success "Wallpapers/ desplegado únicamente en ~/Imágenes/Wallpapers."
    fi

    # 4. misc/ gets mapped according to the role of each directory in THIS repo.
    if [[ -d "$SCRIPT_DIR/misc/bin" ]]; then
        rsync -a --delete "$SCRIPT_DIR/misc/bin/" "$HOME/.local/bin/" >>"$LOG_FILE" 2>&1 || fatal "No se pudo desplegar misc/bin."
    fi
    if [[ -d "$SCRIPT_DIR/misc/fonts" ]]; then
        rsync -a --delete "$SCRIPT_DIR/misc/fonts/" "$HOME/.local/share/fonts/" >>"$LOG_FILE" 2>&1 || fatal "No se pudo desplegar misc/fonts."
    fi
    if [[ -d "$SCRIPT_DIR/misc/applications" ]]; then
        rsync -a --delete "$SCRIPT_DIR/misc/applications/" "$HOME/.local/share/applications/" >>"$LOG_FILE" 2>&1 || fatal "No se pudo desplegar misc/applications."
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
    step "10.5/12 · Aplicando archivos de home/ del repositorio"

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
    step "11/12 · Display Manager / sesión BSPWM"

    local active=""
    if systemctl is-active --quiet display-manager.service; then
        active="$(systemctl show -p Id --value display-manager.service 2>/dev/null || true)"
    fi

    if [[ -n "$active" ]]; then
        success "Display Manager existente conservado: $active"
    else
        info "No hay Display Manager activo; instalando LightDM + GTK greeter."
        install_pkg lightdm yes || true
        install_pkg lightdm-gtk-greeter yes || true
        ((${#FAILED_REQUIRED[@]} == 0)) || fatal "No se pudo instalar LightDM."
        sudo systemctl enable lightdm.service >>"$LOG_FILE" 2>&1 || fatal "No se pudo habilitar LightDM."
        success "LightDM habilitado."
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

    # Do not overwrite an existing DM configuration when one is active.
    # For a fresh LightDM install, select BSPWM as default session.
    if systemctl is-enabled --quiet lightdm.service 2>/dev/null; then
        sudo install -d -m755 /etc/lightdm/lightdm.conf.d
        sudo tee /etc/lightdm/lightdm.conf.d/50-bspwm.conf >/dev/null <<'EOF_DM'
[Seat:*]
user-session=bspwm
greeter-session=lightdm-gtk-greeter
EOF_DM

        # Give LightDM the exact same default wallpaper as the TechOGR rice.
        local wallpaper="$HOME/Imágenes/Wallpapers/noche_car_man.jpg"
        if [[ -f "$wallpaper" ]]; then
            sudo install -d -m755 /etc/lightdm/lightdm-gtk-greeter.conf.d
            {
                printf '%s\n' '[greeter]'
                printf 'background=%s\n' "$wallpaper"
            } | sudo tee /etc/lightdm/lightdm-gtk-greeter.conf.d/50-techogr-background.conf >/dev/null
            success "Fondo de LightDM sincronizado con noche_car_man.jpg."
        else
            warn "El wallpaper predeterminado aún no existe; LightDM conservará su fondo actual."
        fi
    fi
    success "Sesión BSPWM registrada en /usr/share/xsessions/bspwm.desktop."
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
}

# --------------------------- Integrity checks ---------------------------------
verify_repository_layout() {
    step "12/12 · Verificación final"

    local required=(
        "$HOME/.config/bspwm/bspwmrc"
        "$HOME/.config/bspwm/config/sxhkdrc"
        "$HOME/.config/bspwm/eww"
        "$HOME/.config/bspwm/rices/emilia/walls"
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

    # Warn, but do not mutate, repository files containing upstream credits.
    # The current repository itself includes some gh0stzk-origin references; the
    # installer deliberately leaves them untouched because the repository is the source of truth.
    local upstream_hits
    upstream_hits="$(grep -RIl --exclude-dir=.git 'gh0stzk/dotfiles\|Author: gh0stzk\|Copyright (C) 2021-2026 gh0stzk' "$SCRIPT_DIR/config" "$SCRIPT_DIR/misc" 2>/dev/null | head -n 8 || true)"
    if [[ -n "$upstream_hits" ]]; then
        warn "El repositorio contiene referencias a gh0stzk en archivos que se copian tal cual."
        log WARNING "Current TechOGR repository contains upstream gh0stzk references; installer did not alter them."
    fi
}

show_summary() {
    printf '\n%s%s╔══════════════════════════════════════════════════════════════╗%s\n' "$GREEN" "$BOLD" "$RESET"
    printf '%s%s║           TECHOGR BSPWM · INSTALACIÓN COMPLETADA             ║%s\n' "$GREEN" "$BOLD" "$RESET"
    printf '%s%s╚══════════════════════════════════════════════════════════════╝%s\n\n' "$GREEN" "$BOLD" "$RESET"
    printf '  %s✓%s Configuración: %s\n' "$GREEN" "$RESET" "$HOME/.config/bspwm"
    printf '  %s✓%s Wallpapers:    %s\n' "$GREEN" "$RESET" "$HOME/Imágenes/Wallpapers"
    printf '  %s✓%s Eww:            %s\n' "$GREEN" "$RESET" "$(command -v eww)"
    printf '  %s✓%s Backup:         %s\n' "$GREEN" "$RESET" "$BACKUP_DIR"
    printf '  %s✓%s Log:            %s\n\n' "$GREEN" "$RESET" "$LOG_FILE"
    printf '  %sPróximo paso:%s cierra la sesión y selecciona %sBSPWM%s en tu Display Manager.\n' "$CYAN" "$RESET" "$BOLD" "$RESET"
    printf '  %sPara restaurar tu configuración:%s %s/restore.sh%s\n\n' "$CYAN" "$RESET" "$BACKUP_DIR" "$RESET"
}

main() {
    print_banner
    check_execution
    check_arch
    install_base_deps
    install_aur_helper
    install_eww
    install_packages
    install_lockscreen
    create_backup
    copy_repository_content
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
