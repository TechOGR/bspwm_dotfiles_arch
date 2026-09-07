#!/usr/bin/env bash
# ==============================================================================
# TechOGR BSPWM Dotfiles Installer
# Arch Linux / CachyOS / EndeavourOS / Garuda / BlackArch / Manjaro / derivatives
# ==============================================================================
# Run as a normal user:
#   chmod +x install.sh
#   ./install.sh
#
# Design goals:
#   - Never run the installer itself as root.
#   - Use sudo only where system files/services require it.
#   - Preserve the repository's real config layout under ~/.config/bspwm/.
#   - Back up existing user configuration before overwriting it.
#   - Treat AUR-only/optional components as non-fatal.
#   - Avoid destructive "fixes" such as deleting pacman locks blindly.
# ==============================================================================

set -uo pipefail

SCRIPT_VERSION="5.0.0"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_URL="https://github.com/TechOGR/bspwm_dotfiles_arch.git"
LOG_FILE="$HOME/.techogr_install.log"
BACKUP_ROOT="$HOME/.dotfiles_backup"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$BACKUP_ROOT/backup_$TIMESTAMP"
AUR_HELPER=""
DM_NAME=""
FAILED_REQUIRED=()
FAILED_OPTIONAL=()

# ------------------------------- Colors --------------------------------------
if [[ -t 1 ]]; then
    RESET=$'\e[0m'; BOLD=$'\e[1m'; DIM=$'\e[2m'
    RED=$'\e[31m'; GREEN=$'\e[32m'; YELLOW=$'\e[33m'
    BLUE=$'\e[34m'; MAGENTA=$'\e[35m'; CYAN=$'\e[36m'
else
    RESET=''; BOLD=''; DIM=''; RED=''; GREEN=''; YELLOW=''; BLUE=''; MAGENTA=''; CYAN=''
fi

mkdir -p "$(dirname -- "$LOG_FILE")" 2>/dev/null || true
touch "$LOG_FILE" 2>/dev/null || {
    printf '%s\n' "ERROR: cannot write log file: $LOG_FILE" >&2
    exit 1
}

log() {
    printf '%s [%s] %s\n' "$(date '+%F %T')" "$1" "$2" >> "$LOG_FILE"
}

info() {
    printf ' %s[INFO]%s    %s\n' "$CYAN" "$RESET" "$1"
    log INFO "$1"
}

success() {
    printf ' %s[SUCCESS]%s %s\n' "$GREEN" "$RESET" "$1"
    log SUCCESS "$1"
}

warn() {
    printf ' %s[WARNING]%s %s\n' "$YELLOW" "$RESET" "$1"
    log WARNING "$1"
}

error() {
    printf ' %s[ERROR]%s   %s\n' "$RED" "$RESET" "$1" >&2
    log ERROR "$1"
}

step() {
    printf '\n%s%s==> %s%s\n' "$MAGENTA" "$BOLD" "$1" "$RESET"
    log STEP "$1"
}

fatal() {
    error "$1"
    error "Log: $LOG_FILE"
    exit 1
}

run_quiet() {
    # Run a command and capture all output in the installer log.
    "$@" >>"$LOG_FILE" 2>&1
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

is_pkg_installed() {
    pacman -Qq "$1" >/dev/null 2>&1
}

install_repo_pkg() {
    local pkg="$1" required="${2:-yes}"
    if is_pkg_installed "$pkg"; then
        printf '  %-34s %sinstalled%s\n' "$pkg" "$GREEN" "$RESET"
        return 0
    fi

    printf '  %-34s installing...\n' "$pkg"
    if sudo pacman -S --needed --noconfirm "$pkg" >>"$LOG_FILE" 2>&1; then
        printf '  %-34s %sOK%s\n' "$pkg" "$GREEN" "$RESET"
        return 0
    fi

    if [[ "$required" == yes ]]; then
        FAILED_REQUIRED+=("$pkg")
        printf '  %-34s %sFAILED%s\n' "$pkg" "$RED" "$RESET"
        return 1
    fi

    FAILED_OPTIONAL+=("$pkg")
    printf '  %-34s %swarn%s\n' "$pkg" "$YELLOW" "$RESET"
    return 1
}

install_aur_pkg() {
    local pkg="$1" required="${2:-no}"
    if is_pkg_installed "$pkg"; then
        printf '  AUR %-30s %sinstalled%s\n' "$pkg" "$GREEN" "$RESET"
        return 0
    fi

    [[ -n "$AUR_HELPER" ]] || {
        [[ "$required" == yes ]] && FAILED_REQUIRED+=("AUR:$pkg") || FAILED_OPTIONAL+=("AUR:$pkg")
        return 1
    }

    printf '  AUR %-30s installing...\n' "$pkg"
    if "$AUR_HELPER" -S --needed --noconfirm "$pkg" >>"$LOG_FILE" 2>&1; then
        printf '  AUR %-30s %sOK%s\n' "$pkg" "$GREEN" "$RESET"
        return 0
    fi

    if [[ "$required" == yes ]]; then
        FAILED_REQUIRED+=("AUR:$pkg")
        printf '  AUR %-30s %sFAILED%s\n' "$pkg" "$RED" "$RESET"
        return 1
    fi

    FAILED_OPTIONAL+=("AUR:$pkg")
    printf '  AUR %-30s %swarn%s\n' "$pkg" "$YELLOW" "$RESET"
    return 1
}

# --------------------------- Global error trap --------------------------------
on_error() {
    local rc=$?
    log ERROR "Unexpected command failure near line ${BASH_LINENO[0]:-unknown}, status=$rc"
}
trap 'on_error' ERR

print_banner() {
    clear 2>/dev/null || true
    printf '%s%s\n' "$CYAN" "$BOLD"
    cat <<'BANNER'
  ████████╗███████╗ ██████╗██╗  ██╗ ██████╗  ██████╗ ██████╗
  ╚══██╔══╝██╔════╝██╔════╝██║  ██║██╔═══██╗██╔════╝ ██╔══██╗
     ██║   █████╗  ██║     ███████║██║   ██║██║  ███╗██████╔╝
     ██║   ██╔══╝  ██║     ██╔══██║██║   ██║██║   ██║██╔══██╗
     ██║   ███████╗╚██████╗██║  ██║╚██████╔╝╚██████╔╝██║  ██║
     ╚═╝   ╚══════╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝
BANNER
    printf '%sTechOGR BSPWM Dotfiles Installer v%s%s\n' "$BLUE" "$SCRIPT_VERSION" "$RESET"
    printf '%sArch-family / X11 / BSPWM / LightDM / AUR%s\n\n' "$DIM" "$RESET"
    log INFO "Installer v$SCRIPT_VERSION started from $SCRIPT_DIR"
}

check_execution() {
    step "1/11 - Verificación de ejecución y herramientas básicas"

    [[ "$EUID" -ne 0 ]] || fatal "No ejecutes este instalador como root. Usa ./install.sh como usuario normal."
    [[ -n "${HOME:-}" && -d "$HOME" ]] || fatal "HOME no es válido."
    [[ -f "$SCRIPT_DIR/install.sh" ]] || fatal "No se encontró install.sh en $SCRIPT_DIR."

    local required_cmds=(pacman sudo systemctl awk sed grep find install cp mv rm mkdir tar date uname id)
    local missing=()
    local cmd
    for cmd in "${required_cmds[@]}"; do
        command_exists "$cmd" || missing+=("$cmd")
    done

    ((${#missing[@]} == 0)) || fatal "Faltan comandos básicos: ${missing[*]}"

    sudo -v || fatal "No fue posible autenticar sudo."
    success "Ejecutando correctamente como usuario: $USER"
}

check_arch() {
    step "2/11 - Detección de Arch Linux y estado de pacman"

    [[ -r /etc/os-release ]] || fatal "No existe /etc/os-release."
    # shellcheck disable=SC1091
    source /etc/os-release

    local id_lower="${ID,,}" like_lower="${ID_LIKE,,}"
    local arch_family=false
    [[ "$id_lower" == arch || "$id_lower" == cachyos || "$id_lower" == endeavouros || \
       "$id_lower" == garuda || "$id_lower" == blackarch || "$id_lower" == manjaro || \
       "$id_lower" == arcolinux || "$like_lower" == *arch* ]] && arch_family=true

    $arch_family || fatal "La distribución '$NAME' no parece pertenecer a la familia Arch Linux."
    [[ "$(uname -m)" == x86_64 ]] || fatal "Este rice está preparado para x86_64; arquitectura detectada: $(uname -m)."

    info "Distribución: ${NAME:-desconocida} (${VERSION_ID:-?})"
    info "Kernel: $(uname -r)"

    # Never remove pacman db.lck blindly. If a package process is active, abort.
    if [[ -e /var/lib/pacman/db.lck ]]; then
        local active_pkg_proc=false p
        for p in pacman makepkg yay paru; do
            if pgrep -x "$p" >/dev/null 2>&1; then
                active_pkg_proc=true
                break
            fi
        done

        if $active_pkg_proc; then
            fatal "pacman/AUR está ejecutándose y existe /var/lib/pacman/db.lck. Espera a que termine y vuelve a ejecutar el instalador."
        fi

        warn "Existe /var/lib/pacman/db.lck pero no se detecta un proceso activo. No se eliminará automáticamente."
        read -r -p " ¿Quieres eliminar este lock huérfano? [s/N]: " answer
        if [[ "$answer" =~ ^[sS]$ ]]; then
            sudo rm -f /var/lib/pacman/db.lck || fatal "No se pudo eliminar el lock huérfano de pacman."
            success "Lock huérfano eliminado por decisión del usuario."
        else
            fatal "No se puede continuar con un lock de pacman presente."
        fi
    fi

    info "Sincronizando repositorios (pacman -Sy)..."
    # Use -Syy only if normal sync fails; do not force a partial upgrade.
    if ! sudo pacman -Sy >>"$LOG_FILE" 2>&1; then
        warn "pacman -Sy falló. Reintentando con -Syy..."
        sudo pacman -Syy >>"$LOG_FILE" 2>&1 || fatal "No se pudo sincronizar pacman."
    fi

    success "Sistema Arch-family detectado y pacman operativo."
}

install_base_deps() {
    step "3/11 - Dependencias base y compilación AUR"
    local pkgs=(base-devel git curl ca-certificates)
    local pkg
    for pkg in "${pkgs[@]}"; do
        install_repo_pkg "$pkg" yes || true
    done
    ((${#FAILED_REQUIRED[@]} == 0)) || fatal "No se pudieron instalar dependencias base: ${FAILED_REQUIRED[*]}"
    success "base-devel, git y utilidades requeridas están disponibles."
}

install_aur_helper() {
    step "4/11 - Detección / instalación del AUR helper"

    if command_exists yay; then
        AUR_HELPER="yay"
    elif command_exists paru; then
        AUR_HELPER="paru"
    fi

    if [[ -n "$AUR_HELPER" ]]; then
        success "AUR helper detectado: $AUR_HELPER"
        return 0
    fi

    info "No se encontró yay ni paru; instalando yay-bin para el usuario actual."
    local build_dir="$(mktemp -d -p /tmp techogr-yay.XXXXXX)"
    local keep_dir=false

    if ! git clone --depth=1 https://aur.archlinux.org/yay-bin.git "$build_dir/yay-bin" >>"$LOG_FILE" 2>&1; then
        keep_dir=true
        [[ "$keep_dir" == true ]] && warn "No se pudo clonar yay-bin. Directorio temporal: $build_dir"
        rm -rf "$build_dir"
        fatal "No se pudo obtener yay-bin desde AUR."
    fi

    if ! (cd "$build_dir/yay-bin" && makepkg -si --noconfirm) >>"$LOG_FILE" 2>&1; then
        keep_dir=true
        warn "La compilación de yay-bin falló. Revisa el log para el error exacto."
        rm -rf "$build_dir"
        fatal "No se pudo instalar yay."
    fi

    rm -rf "$build_dir"
    command_exists yay || fatal "yay terminó de compilar pero no aparece en PATH."
    AUR_HELPER="yay"
    success "yay instalado y listo para el usuario $USER."
}

install_eww() {
    step "5.1/11 - Instalación robusta de Eww para X11"

    if command_exists eww; then
        success "Eww ya está instalado: $(eww --version 2>/dev/null | head -n1 || printf '%s' 'versión disponible')"
        return 0
    fi

    # Primero intentamos el paquete AUR, que es la vía más sencilla cuando el
    # PKGBUILD del momento es compatible con el sistema del usuario.
    if [[ -n "$AUR_HELPER" ]]; then
        info "Intentando instalar Eww desde AUR (${AUR_HELPER})..."
        if "$AUR_HELPER" -S --needed --noconfirm eww >>"$LOG_FILE" 2>&1; then
            if command_exists eww; then
                success "Eww instalado correctamente desde AUR."
                return 0
            fi
        fi
        warn "El paquete AUR de Eww no pudo instalarse. Se usará compilación desde el código fuente."
    fi

    # Fallback estable: compilar Eww directamente con el backend X11.
    # Eww es un proyecto Rust y su documentación recomienda cargo build para
    # compilarlo; para este rice no necesitamos Wayland.
    local build_dir="$HOME/.local/state/techogr-bspwm/build/eww-source"
    local eww_repo="https://github.com/elkowar/eww.git"
    # rust ya incluye cargo en Arch; no lo tratamos como un paquete separado.
    # Esto evita instalaciones redundantes y reduce los conflictos rust/rustup.
    local eww_deps=(pkgconf gtk3 gtk-layer-shell pango gdk-pixbuf2 cairo glib2 dbus libdbusmenu-gtk3)
    local dep

    info "Preparando dependencias de compilación de Eww..."

    if ! command_exists cargo; then
        if command_exists rustup; then
            info "rustup detectado; activando toolchain stable para Eww..."
            rustup toolchain install stable --profile minimal >>"$LOG_FILE" 2>&1 || true
            rustup default stable >>"$LOG_FILE" 2>&1 || true
        else
            install_repo_pkg rust yes || true
        fi
    fi

    for dep in "${eww_deps[@]}"; do
        if is_pkg_installed "$dep"; then
            continue
        fi
        if ! install_repo_pkg "$dep" yes; then
            warn "No se pudo instalar la dependencia de Eww: $dep"
        fi
    done

    # cargo puede ser proporcionado por rust o por rustup.
    command_exists cargo || {
        warn "cargo no está disponible; Eww no podrá compilarse en este intento."
        FAILED_OPTIONAL+=("eww")
        return 1
    }

    mkdir -p "$(dirname -- "$build_dir")"
    rm -rf -- "$build_dir"

    info "Clonando Eww desde upstream..."
    if ! git clone --depth=1 --filter=blob:none "$eww_repo" "$build_dir" >>"$LOG_FILE" 2>&1; then
        warn "No se pudo clonar Eww desde GitHub."
        FAILED_OPTIONAL+=("eww")
        return 1
    fi

    info "Compilando Eww con backend X11 (cargo build --release)..."
    if ! (
        cd "$build_dir" &&
        cargo build --release --no-default-features --features x11
    ) >>"$LOG_FILE" 2>&1; then
        warn "La compilación de Eww falló. Revisa $LOG_FILE para el error de Rust/dependencias."
        FAILED_OPTIONAL+=("eww")
        return 1
    fi

    [[ -x "$build_dir/target/release/eww" ]] || {
        warn "La compilación terminó sin generar target/release/eww."
        FAILED_OPTIONAL+=("eww")
        return 1
    }

    install -Dm755 "$build_dir/target/release/eww" "$HOME/.local/bin/eww" || {
        warn "No se pudo instalar Eww en ~/.local/bin/eww."
        FAILED_OPTIONAL+=("eww")
        return 1
    }

    if ! command_exists eww; then
        warn "Eww quedó instalado pero ~/.local/bin no está en PATH durante esta ejecución."
        export PATH="$HOME/.local/bin:$PATH"
    fi

    if command_exists eww; then
        success "Eww compilado e instalado en ~/.local/bin/eww."
        return 0
    fi

    warn "No fue posible verificar el binario de Eww."
    FAILED_OPTIONAL+=("eww")
    return 1
}

install_packages() {
    step "5/11 - Paquetes X11, BSPWM, audio, utilidades y estética"

    # Required official repository packages. Keep this list conservative and
    # avoid lib32/vendor packages that are absent when optional repos are disabled.
    local official=(
        xorg-server xorg-xinit xorg-xrandr xorg-xrdb xorg-xsetroot xorg-xset
        xorg-xprop xorg-xinput xorg-xauth xorg-xdpyinfo xorg-xwininfo
        xdotool xclip xsettingsd hsetroot
        bspwm sxhkd polybar rofi picom dunst libnotify jgmenu
        kitty feh imagemagick jq brightnessctl maim
        xdg-utils xdg-user-dirs fontconfig
        ttf-jetbrains-mono-nerd noto-fonts-emoji papirus-icon-theme
        xss-lock
        pipewire pipewire-pulse pipewire-alsa wireplumber
        pamixer playerctl alsa-utils
        dbus polkit-gnome lxsession accountsservice
    )

    # Network stack used by the rice's Rofi/network applets.
    # If a user already has another network manager, NetworkManager is not made
    # a hard dependency; the applet is optional.
    local optional_official=(networkmanager network-manager-applet)

    local pkg
    for pkg in "${official[@]}"; do
        install_repo_pkg "$pkg" yes || true
    done
    for pkg in "${optional_official[@]}"; do
        install_repo_pkg "$pkg" no || true
    done

    # Python/Pywal is optional: the current Arch package exists in Extra, but is
    # not required by the rice's startup path, so its status must not break setup.
    if ! is_pkg_installed python-pywal; then
        install_repo_pkg python-pywal no || true
    fi

    if ((${#FAILED_REQUIRED[@]} > 0)); then
        fatal "Paquetes oficiales críticos que fallaron: ${FAILED_REQUIRED[*]}"
    fi

    # Requested AUR software. betterlockscreen normally brings i3lock-color as
    # part of its dependency chain. Do NOT install i3lock-color and i3lock as
    # competing explicit targets at the same time.
    install_aur_pkg betterlockscreen no || true
    install_aur_pkg brave-bin no || true

    # Eww recibe un tratamiento especial: AUR primero y, si el PKGBUILD
    # falla por cambios de toolchain, compilación directa con backend X11.
    if ! install_eww; then
        warn "Eww no pudo instalarse en esta ejecución; el resto del rice continuará funcionando."
    fi

    # Fallback for a derivative exposing a native "brave" package.
    if ! command_exists brave-browser && ! command_exists brave; then
        if pacman -Si brave >/dev/null 2>&1; then
            install_repo_pkg brave no || true
        fi
    fi

    # NetworkManager should only be enabled when it was actually installed.
    if is_pkg_installed networkmanager; then
        sudo systemctl enable --now NetworkManager.service >>"$LOG_FILE" 2>&1 || warn "NetworkManager no pudo iniciarse; se conservará la configuración existente."
    fi

    # Asegurar el binario local durante el resto de la ejecución.
    export PATH="$HOME/.local/bin:$PATH"

    success "Paquetes principales instalados. Los elementos AUR opcionales no bloquean el rice."
}

backup_user_configs() {
    step "6/11 - Copia de seguridad de configuraciones existentes"

    mkdir -p "$BACKUP_DIR" || fatal "No se pudo crear $BACKUP_DIR"

    local targets=(
        .config/bspwm
        .config/alacritty
        .config/dunst
        .config/jgmenu
        .config/kitty
        .config/gtk-3.0
        .config/gtk-4.0
        .config/nvim
        .config/yazi
        .config/zsh
        .zshrc
        .xprofile
        .xinitrc
        .dmrc
        .config/mimeapps.list
    )

    local rel item copied=0
    for rel in "${targets[@]}"; do
        item="$HOME/$rel"
        if [[ -e "$item" || -L "$item" ]]; then
            mkdir -p "$BACKUP_DIR/$(dirname -- "$rel")"
            if cp -a "$item" "$BACKUP_DIR/$rel" >>"$LOG_FILE" 2>&1; then
                copied=$((copied + 1))
            else
                warn "No se pudo respaldar: $item"
            fi
        fi
    done

    cat > "$BACKUP_DIR/restore.sh" <<EOF_RESTORE
#!/usr/bin/env bash
set -u
BACKUP_DIR="\$(cd -- "\$(dirname -- "\${BASH_SOURCE[0]}")" && pwd -P)"
HOME_DIR="\$HOME"
restore_one() {
    local rel="\$1"
    [[ -e "\$BACKUP_DIR/\$rel" || -L "\$BACKUP_DIR/\$rel" ]] || return 0
    mkdir -p "\$HOME_DIR/\$(dirname -- "\$rel")"
    rm -rf "\$HOME_DIR/\$rel"
    cp -a "\$BACKUP_DIR/\$rel" "\$HOME_DIR/\$rel"
}
$(printf 'restore_one %q\n' "${targets[@]}")
echo "Restauración completada desde: \$BACKUP_DIR"
EOF_RESTORE
    chmod +x "$BACKUP_DIR/restore.sh"

    success "Backup creado: $BACKUP_DIR ($copied elementos respaldados)"
}

copy_tree_if_exists() {
    local src="$1" dst="$2"
    [[ -d "$src" ]] || return 0
    mkdir -p "$dst"
    cp -a "$src/." "$dst/" >>"$LOG_FILE" 2>&1 || {
        warn "No se pudo copiar completamente $src -> $dst"
        return 1
    }
    return 0
}

setup_configs() {
    step "7/11 - Despliegue correcto de dotfiles y permisos"

    mkdir -p \
        "$HOME/.config" \
        "$HOME/.local/bin" \
        "$HOME/.local/share/applications" \
        "$HOME/.local/share/fonts" \
        "$HOME/.local/share/techogr" \
        "$HOME/Pictures/Wallpapers"

    # IMPORTANT: preserve the repository's nested layout. In particular:
    #   config/bspwm/bspwmrc
    #   config/bspwm/config/sxhkdrc
    #   config/bspwm/config/picom/picom.conf
    #   config/bspwm/bin/*
    # are intentionally deployed as ~/.config/bspwm/...
    copy_tree_if_exists "$SCRIPT_DIR/config" "$HOME/.config" || true
    copy_tree_if_exists "$SCRIPT_DIR/home" "$HOME" || true

    if [[ -d "$SCRIPT_DIR/Wallpapers" ]]; then
        copy_tree_if_exists "$SCRIPT_DIR/Wallpapers" "$HOME/Pictures/Wallpapers" || true
    fi

    # Deploy misc/* without polluting ~/.local/share with unrelated folders.
    copy_tree_if_exists "$SCRIPT_DIR/misc/asciiart" "$HOME/.local/share/techogr/asciiart" || true
    copy_tree_if_exists "$SCRIPT_DIR/misc/firefox" "$HOME/.local/share/techogr/firefox" || true
    copy_tree_if_exists "$SCRIPT_DIR/misc/fonts" "$HOME/.local/share/fonts" || true
    copy_tree_if_exists "$SCRIPT_DIR/misc/bin" "$HOME/.local/bin" || true
    copy_tree_if_exists "$SCRIPT_DIR/misc/applications" "$HOME/.local/share/applications" || true

    # Also support a future repo layout that contains top-level kitty/ or
    # polkit/ trees without breaking the current layout.
    copy_tree_if_exists "$SCRIPT_DIR/kitty" "$HOME/.config/kitty" || true

    # Preserve executable bits where the repository expects shell helpers to run.
    if [[ -d "$HOME/.config/bspwm/bin" ]]; then
        find "$HOME/.config/bspwm/bin" -type f -exec chmod 755 {} + 2>>"$LOG_FILE" || true
    fi
    if [[ -d "$HOME/.local/bin" ]]; then
        find "$HOME/.local/bin" -type f -exec chmod 755 {} + 2>>"$LOG_FILE" || true
    fi
    [[ -f "$HOME/.config/bspwm/bspwmrc" ]] && chmod 755 "$HOME/.config/bspwm/bspwmrc"

    # Create/update the desktop launcher database and font cache.
    command_exists update-desktop-database && update-desktop-database "$HOME/.local/share/applications" >>"$LOG_FILE" 2>&1 || true
    command_exists fc-cache && fc-cache -f >>"$LOG_FILE" 2>&1 || true

    success "Dotfiles desplegados respetando la jerarquía real del repositorio."
}

patch_session_safety() {
    step "8/11 - Blindaje de sesión BSPWM (sin romper el rice)"

    local bspwmrc="$HOME/.config/bspwm/bspwmrc"
    [[ -f "$bspwmrc" ]] || fatal "No existe ~/.config/bspwm/bspwmrc después del despliegue."

    # The repository's bspwmrc already contains the correct relative paths.
    # Only add small, idempotent guards around optional programs.
    # Disable the repository's unconditional Eww starts; the guarded block below owns them.
    sed -i -E 's|^[[:space:]]*pidof -q eww \|\|.*$|# disabled by installer: Eww is started by TECHOGR_OPTIONAL_GUARDS|' "$bspwmrc"
    sed -i -E 's|^[[:space:]]*\[[^]]*\.first_run_done[^]]*\].*eww.*$|# disabled by installer: Eww first-run is handled by TECHOGR_OPTIONAL_GUARDS|' "$bspwmrc"

    if ! grep -q 'TECHOGR_OPTIONAL_GUARDS' "$bspwmrc"; then
        cat >> "$bspwmrc" <<'EOF_GUARDS'

# ============================================================================
# TECHOGR_OPTIONAL_GUARDS
# Keep optional components from producing fatal-looking startup errors.
# ============================================================================
if command -v dunst >/dev/null 2>&1; then
    if ! pgrep -x dunst >/dev/null 2>&1; then dunst >/dev/null 2>&1 & fi
fi

# eww is optional because it may fail to build on a particular Arch toolchain.
# Never call it when the binary is unavailable.
if command -v eww >/dev/null 2>&1; then
    eww -c "$HOME/.config/bspwm/eww" daemon >/dev/null 2>&1 &
    if [[ -f "$HOME/.config/bspwm/eww/eww.yuck" && ! -f "$HOME/.config/bspwm/config/.first_run_done" ]]; then
        ( eww -c "$HOME/.config/bspwm/eww" open --toggle welcome >/dev/null 2>&1 && touch "$HOME/.config/bspwm/config/.first_run_done" ) &
    fi
fi
EOF_GUARDS
    fi

    # The current repository intentionally keeps sxhkd and picom beneath
    # ~/.config/bspwm/config; do not manufacture duplicate ~/.config/sxhkd or
    # ~/.config/picom trees. This is a common source of broken clicks/shortcuts.
    local sxhkd_conf="$HOME/.config/bspwm/config/sxhkdrc"
    local picom_conf="$HOME/.config/bspwm/config/picom/picom.conf"
    [[ -f "$sxhkd_conf" ]] || warn "No se encontró $sxhkd_conf"
    [[ -f "$picom_conf" ]] || warn "No se encontró $picom_conf"

    # Avoid the old Virtual-1-only xrandr hard failure on physical hardware.
    # The line is commented only if it exactly matches the repository's forced
    # single-virtual-output command.
    if grep -Eq '^[[:space:]]*xrandr --output Virtual-1 --mode 1920x1080 --rate 60[[:space:]]*$' "$bspwmrc"; then
        sed -i 's/^[[:space:]]*xrandr --output Virtual-1 --mode 1920x1080 --rate 60[[:space:]]*$/# xrandr --output Virtual-1 --mode 1920x1080 --rate 60  # disabled by installer: hardware-independent startup/' "$bspwmrc"
        success "Se eliminó la dependencia de una salida Virtual-1 fija."
    fi

    # Ensure PATH contains the repo's BSPWM helper directory before sxhkd/theme scripts.
    if ! grep -q 'export PATH="\$HOME/.config/bspwm/bin:\$PATH"' "$bspwmrc"; then
        sed -i '2i export PATH="$HOME/.config/bspwm/bin:$PATH"' "$bspwmrc"
    fi

    # Configure a safe X11 profile for LightDM/xinit without attempting to start
    # bspwm twice. LightDM's Xsession will execute the selected .desktop session.
    cat > "$HOME/.xprofile" <<'EOF_XPROFILE'
#!/bin/sh
# TechOGR BSPWM session environment
export XDG_CURRENT_DESKTOP=bspwm
export DESKTOP_SESSION=bspwm
export XDG_SESSION_TYPE=x11
export XCURSOR_SIZE="${XCURSOR_SIZE:-24}"
export _JAVA_AWT_WM_NONREPARENTING="${_JAVA_AWT_WM_NONREPARENTING:-1}"
[ -f "$HOME/.Xresources" ] && command -v xrdb >/dev/null 2>&1 && xrdb -merge "$HOME/.Xresources"
EOF_XPROFILE
    chmod 644 "$HOME/.xprofile"

    # Keep xinit as a manual fallback only. LightDM does not use this file.
    cat > "$HOME/.xinitrc" <<'EOF_XINITRC'
#!/bin/sh
[ -f "$HOME/.xprofile" ] && . "$HOME/.xprofile"
exec bspwm
EOF_XINITRC
    chmod 755 "$HOME/.xinitrc"

    success "Sesión blindada sin duplicar servicios ni rutas de configuración."
}

configure_picom() {
    local conf="$HOME/.config/bspwm/config/picom/picom.conf"
    [[ -f "$conf" ]] || return 0

    # Picom backend compatibility: GLX is a good default for physical X11
    # systems, but xrender is safer on VMs. Do not force a backend if the config
    # doesn't already declare one.
    local backend="glx" vsync="true"
    if command_exists systemd-detect-virt && [[ "$(systemd-detect-virt)" != none ]]; then
        backend="xrender"
        vsync="false"
        warn "Máquina virtual detectada: Picom usará xrender/vsync=false."
    fi

    if grep -qE '^[[:space:]]*backend[[:space:]]*=' "$conf"; then
        sed -i -E "s|^[[:space:]]*backend[[:space:]]*=.*|backend = \"$backend\";|" "$conf"
    fi
    if grep -qE '^[[:space:]]*vsync[[:space:]]*=' "$conf"; then
        sed -i -E "s|^[[:space:]]*vsync[[:space:]]*=.*|vsync = $vsync;|" "$conf"
    fi
}

configure_browser_default() {
    step "9/11 - Navegador predeterminado y MIME handlers"

    local brave_desktop=""
    if [[ -f /usr/share/applications/brave-browser.desktop ]]; then
        brave_desktop="brave-browser.desktop"
    elif [[ -f /usr/share/applications/brave-browser-stable.desktop ]]; then
        brave_desktop="brave-browser-stable.desktop"
    fi

    if [[ -n "$brave_desktop" ]] && command_exists xdg-settings; then
        xdg-settings set default-web-browser "$brave_desktop" >>"$LOG_FILE" 2>&1 || true
        xdg-mime default "$brave_desktop" x-scheme-handler/http >>"$LOG_FILE" 2>&1 || true
        xdg-mime default "$brave_desktop" x-scheme-handler/https >>"$LOG_FILE" 2>&1 || true
        xdg-mime default "$brave_desktop" text/html >>"$LOG_FILE" 2>&1 || true
        success "Brave configurado como navegador predeterminado ($brave_desktop)."
    else
        warn "Brave no quedó instalado; no se modificará el navegador predeterminado."
    fi
}

install_display_manager() {
    step "10/11 - Display Manager y sesión BSPWM"

    # Always install the X session entry. This works with LightDM, GDM, SDDM,
    # Ly, etc., and is the real requirement for a selectable bspwm session.
    sudo install -d -m 755 /usr/share/xsessions
    sudo tee /usr/share/xsessions/bspwm.desktop >/dev/null <<'EOF_BSPWM_DESKTOP'
[Desktop Entry]
Name=bspwm
Comment=Binary Space Partitioning Window Manager
Exec=/usr/bin/bspwm
TryExec=/usr/bin/bspwm
Type=XSession
DesktopNames=bspwm
EOF_BSPWM_DESKTOP
    sudo chmod 644 /usr/share/xsessions/bspwm.desktop

    # Detect an already-running display manager and preserve it.
    local dm_target=""
    if [[ -e /etc/systemd/system/display-manager.service ]]; then
        dm_target="$(readlink -f /etc/systemd/system/display-manager.service 2>/dev/null || true)"
        DM_NAME="$(basename -- "$dm_target" .service)"
    fi

    if systemctl is-active --quiet display-manager.service; then
        [[ -n "$DM_NAME" ]] || DM_NAME="existing-display-manager"
        success "Display Manager activo detectado: $DM_NAME. No se reemplazará."
        return 0
    fi

    local known_enabled=""
    local dm
    for dm in gdm sddm lxdm ly greetd lightdm; do
        if systemctl is-enabled --quiet "$dm.service" 2>/dev/null; then
            known_enabled="$dm"
            break
        fi
    done

    if [[ -n "$known_enabled" ]]; then
        DM_NAME="$known_enabled"
        warn "Existe un Display Manager habilitado ($known_enabled), pero no está activo ahora. No se deshabilitará automáticamente."
        return 0
    fi

    # No DM: install and configure LightDM.
    local dm_pkgs=(lightdm lightdm-gtk-greeter)
    local pkg
    for pkg in "${dm_pkgs[@]}"; do
        install_repo_pkg "$pkg" yes || true
    done
    ((${#FAILED_REQUIRED[@]} == 0)) || fatal "No se pudo instalar el Display Manager: ${FAILED_REQUIRED[*]}"

    sudo install -d -m 755 /etc/lightdm
    sudo cp -an /etc/lightdm/lightdm.conf /etc/lightdm/lightdm.conf.techogr-original 2>/dev/null || true
    sudo cp -an /etc/lightdm/lightdm-gtk-greeter.conf /etc/lightdm/lightdm-gtk-greeter.conf.techogr-original 2>/dev/null || true

    sudo tee /etc/lightdm/lightdm.conf >/dev/null <<'EOF_LIGHTDM'
[LightDM]
run-directory=/run/lightdm

[Seat:*]
greeter-session=lightdm-gtk-greeter
user-session=bspwm
session-wrapper=/etc/lightdm/Xsession
allow-guest=false
allow-user-switching=true
EOF_LIGHTDM
    sudo chmod 644 /etc/lightdm/lightdm.conf

    # Modern dark GTK greeter. Background uses a copied repository wallpaper when available.
    local login_bg="/usr/share/backgrounds/techogr/login.jpg"
    local first_wall=""
    first_wall="$(find "$HOME/Pictures/Wallpapers" -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) -print -quit 2>/dev/null || true)"
    if [[ -n "$first_wall" ]]; then
        sudo install -d -m 755 /usr/share/backgrounds/techogr
        case "${first_wall##*.}" in
            png|PNG) login_bg="/usr/share/backgrounds/techogr/login.png" ;;
            jpg|JPG|jpeg|JPEG) login_bg="/usr/share/backgrounds/techogr/login.jpg" ;;
            *) login_bg="/usr/share/backgrounds/techogr/login.jpg" ;;
        esac
        sudo install -m 644 "$first_wall" "$login_bg"
    fi

    sudo tee /etc/lightdm/lightdm-gtk-greeter.conf >/dev/null <<EOF_GREETER
[greeter]
theme-name = Adwaita
icon-theme-name = Papirus-Dark
font-name = JetBrains Mono Nerd Font 10
background = ${login_bg}
hide-user-image = false
clock-format = %A %d %B  •  %H:%M
indicators = ~host;~spacer;~clock;~spacer;~session;~language;~a11y;~power
position = 50%,center 50%,center
EOF_GREETER
    sudo chmod 644 /etc/lightdm/lightdm-gtk-greeter.conf

    # Xsession exists in the LightDM package. Only create a fallback if absent.
    if [[ ! -x /etc/lightdm/Xsession ]]; then
        sudo tee /etc/lightdm/Xsession >/dev/null <<'EOF_XSESSION'
#!/bin/sh
# Minimal fallback wrapper for LightDM on Arch-family systems.
set +e
[ -f /etc/profile ] && . /etc/profile
[ -f "$HOME/.profile" ] && . "$HOME/.profile"
[ -f "$HOME/.xprofile" ] && . "$HOME/.xprofile"
exec "$@"
EOF_XSESSION
        sudo chmod 755 /etc/lightdm/Xsession
    fi

    sudo systemctl enable lightdm.service >>"$LOG_FILE" 2>&1 || fatal "No se pudo habilitar lightdm.service."
    DM_NAME="lightdm"

    # Make BSPWM the saved LightDM session for this user.
    cat > "$HOME/.dmrc" <<'EOF_DMRC'
[Desktop]
Session=bspwm
EOF_DMRC
    chmod 644 "$HOME/.dmrc"

    success "LightDM habilitado con LightDM GTK Greeter y BSPWM como sesión predeterminada."
}

setup_lockscreen() {
    step "11/11 - Lockscreen con fallback seguro y caché de wallpaper"

    local lock_script="$HOME/.local/bin/techogr_lock"
    cat > "$lock_script" <<'EOF_LOCK'
#!/usr/bin/env bash
set -u

# TechOGR lockscreen cascade:
# betterlockscreen -> i3lock-color -> i3lock

if command -v betterlockscreen >/dev/null 2>&1; then
    exec betterlockscreen -l dimblur
fi

if command -v i3lock-color >/dev/null 2>&1; then
    exec i3lock-color \
        --inside-color=1a1b26cc \
        --insidever-color=24283bcc \
        --insidewrong-color=f7768ecc \
        --ring-color=7aa2f7ff \
        --ringver-color=9ece6aff \
        --ringwrong-color=f7768eff \
        --keyhl-color=bb9af7ff \
        --bshl-color=f7768e \
        --separator-color=00000000 \
        --verif-color=c0caf5ff \
        --wrong-color=f7768eff \
        --time-color=c0caf5ff \
        --date-color=a9b1d6ff \
        --clock --indicator \
        --ring-width=8
fi

if command -v i3lock >/dev/null 2>&1; then
    exec i3lock -c 1a1b26
fi

echo "No se encontró un screen locker compatible (betterlockscreen/i3lock)." >&2
exit 1
EOF_LOCK
    chmod 755 "$lock_script"
    ln -sfn "$lock_script" "$HOME/.local/bin/lockscreen"

    # Cache initial wallpaper only when both commands/data exist.
    if command_exists betterlockscreen; then
        local wall=""
        wall="$(find "$HOME/Pictures/Wallpapers" -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) -print -quit 2>/dev/null || true)"
        if [[ -n "$wall" ]]; then
            info "Generando caché inicial de betterlockscreen..."
            betterlockscreen -u "$wall" >>"$LOG_FILE" 2>&1 || warn "betterlockscreen no pudo generar la caché; el lock seguirá usando su fallback."
        fi
    fi

    # Add idempotent sxhkd bindings to the repository's actual path.
    local sxhkd_conf="$HOME/.config/bspwm/config/sxhkdrc"
    if [[ -f "$sxhkd_conf" ]] && ! grep -q 'techogr_lock' "$sxhkd_conf"; then
        cat >> "$sxhkd_conf" <<'EOF_SXHKD'

# TechOGR lockscreen
super + alt + l
    $HOME/.local/bin/techogr_lock
EOF_SXHKD
    fi

    # Start xss-lock once per BSPWM session if available.
    local bspwmrc="$HOME/.config/bspwm/bspwmrc"
    if [[ -f "$bspwmrc" ]] && ! grep -q 'TECHOGR_XSS_LOCK' "$bspwmrc"; then
        cat >> "$bspwmrc" <<'EOF_XSS'

# TECHOGR_XSS_LOCK
if command -v xss-lock >/dev/null 2>&1 && command -v "$HOME/.local/bin/techogr_lock" >/dev/null 2>&1; then
    pkill -x xss-lock >/dev/null 2>&1 || true
    xss-lock --transfer-sleep-lock -- "$HOME/.local/bin/techogr_lock" >/dev/null 2>&1 &
fi
EOF_XSS
    fi

    success "Lockscreen configurado con fallback i3lock y bloqueo automático con xss-lock."
}

post_install_fixes() {
    step "Diagnóstico final - rutas, servicios y archivos críticos"

    configure_picom
    configure_browser_default

    local checks=(
        "$HOME/.config/bspwm/bspwmrc"
        "$HOME/.config/bspwm/config/sxhkdrc"
        "$HOME/.config/bspwm/bin/Theme.sh"
        "$HOME/.config/bspwm/config/picom/picom.conf"
        "$HOME/.local/bin/techogr_lock"
        "/usr/share/xsessions/bspwm.desktop"
    )

    local path
    for path in "${checks[@]}"; do
        if [[ -e "$path" ]]; then
            success "OK: $path"
        else
            warn "Falta: $path"
        fi
    done

    # Basic shell syntax check for our key shell scripts; do not execute them.
    local script
    for script in \
        "$HOME/.config/bspwm/bspwmrc" \
        "$HOME/.config/bspwm/bin/Theme.sh" \
        "$HOME/.config/bspwm/bin/SetSysVars" \
        "$HOME/.local/bin/techogr_lock"; do
        if [[ -f "$script" ]] && ! bash -n "$script" >>"$LOG_FILE" 2>&1; then
            warn "Sintaxis Bash sospechosa en: $script (revisa $LOG_FILE)"
        fi
    done

    if command_exists bspwm; then success "bspwm está instalado."; else error "bspwm no está disponible en PATH."; fi
    if command_exists sxhkd; then success "sxhkd está instalado."; else error "sxhkd no está disponible en PATH."; fi
    if command_exists Xorg; then success "Xorg está instalado."; else error "Xorg no está disponible."; fi

    if [[ "$DM_NAME" == lightdm ]]; then
        if systemctl is-enabled --quiet lightdm.service; then
            success "lightdm.service está habilitado."
        else
            error "lightdm.service NO está habilitado."
        fi
    else
        info "Display Manager preservado: ${DM_NAME:-ninguno detectado}."
    fi

    # No automatically force graphical.target when another display manager is in
    # use; systemd target selection belongs to the existing system policy.
    if [[ "$(systemctl get-default 2>/dev/null || true)" != "graphical.target" ]]; then
        warn "El target por defecto no es graphical.target. No se modificará automáticamente porque podría ser una política del usuario."
    fi
}

show_summary() {
    printf '\n%s%s══════════════════════════════════════════════════════════════%s\n' "$GREEN" "$BOLD" "$RESET"
    printf '%s%s        TECHOGR BSPWM - INSTALACIÓN COMPLETADA%s\n' "$GREEN" "$BOLD" "$RESET"
    printf '%s%s══════════════════════════════════════════════════════════════%s\n\n' "$GREEN" "$BOLD" "$RESET"

    printf ' %s•%s Backup:      %s\n' "$CYAN" "$RESET" "$BACKUP_DIR"
    printf ' %s•%s Log:         %s\n' "$CYAN" "$RESET" "$LOG_FILE"
    printf ' %s•%s DisplayMgr:  %s\n' "$CYAN" "$RESET" "${DM_NAME:-preservado/ninguno}"
    printf ' %s•%s Browser:     %s\n' "$CYAN" "$RESET" "$(command_exists brave-browser && echo Brave || command_exists brave && echo Brave || echo 'no instalado')"
    printf ' %s•%s Lockscreen:   %s\n' "$CYAN" "$RESET" "$(command_exists betterlockscreen && echo betterlockscreen || command_exists i3lock-color && echo i3lock-color || echo i3lock)"
    printf '\n %sRutas importantes:%s\n' "$CYAN" "$RESET"
    printf '   ~/.config/bspwm/bspwmrc\n'
    printf '   ~/.config/bspwm/config/sxhkdrc\n'
    printf '   ~/.config/bspwm/config/picom/picom.conf\n'
    printf '   ~/.config/bspwm/bin/*\n'
    printf '\n %sAtajos añadidos por el instalador:%s\n' "$CYAN" "$RESET"
    printf '   Super + Alt + L  -> bloquear pantalla\n'

    if ((${#FAILED_OPTIONAL[@]} > 0)); then
        printf '\n%sOpcionales que no se instalaron:%s %s\n' "$YELLOW" "$RESET" "${FAILED_OPTIONAL[*]}"
    fi

    if ((${#FAILED_REQUIRED[@]} > 0)); then
        printf '\n%sERROR: críticos fallidos:%s %s\n' "$RED" "$RESET" "${FAILED_REQUIRED[*]}"
    fi

    printf '\n%sReinicia la sesión o el equipo antes de probar el rice completo.%s\n' "$YELLOW" "$RESET"
    printf '%sEl instalador NO reinicia automáticamente.%s\n' "$DIM" "$RESET"
}

main() {
    print_banner
    check_execution
    check_arch
    install_base_deps
    install_aur_helper
    install_packages
    backup_user_configs
    setup_configs
    patch_session_safety
    setup_lockscreen
    install_display_manager
    post_install_fixes
    show_summary
}

main "$@"
