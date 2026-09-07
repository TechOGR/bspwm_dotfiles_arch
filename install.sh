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

SCRIPT_VERSION="6.0.0"
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
CURRENT_STEP=0
TOTAL_STEPS=12

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
    local label="$1"
    CURRENT_STEP=$((CURRENT_STEP + 1))
    local width=32 filled=0 pct=0
    (( TOTAL_STEPS > 0 )) && pct=$(( CURRENT_STEP * 100 / TOTAL_STEPS ))
    (( pct > 100 )) && pct=100
    filled=$(( pct * width / 100 ))
    local empty=$(( width - filled ))
    local bar=""
    (( filled > 0 )) && bar+=$(printf '%*s' "$filled" '' | tr ' ' '█')
    (( empty > 0 )) && bar+=$(printf '%*s' "$empty" '' | tr ' ' '░')
    printf '\n%s╭────────────────────────────────────────────────────────────╮%s\n' "$BLUE" "$RESET"
    printf '%s│%s %s%sPaso %02d/%02d%s  %-39s %s│%s\n' "$BLUE" "$RESET" "$BOLD" "$MAGENTA" "$CURRENT_STEP" "$TOTAL_STEPS" "$RESET" "$label" "$BLUE" "$RESET"
    printf '%s│%s %s%s%s %3d%%  %s│%s\n' "$BLUE" "$RESET" "$CYAN" "$bar" "$RESET" "$pct" "$BLUE" "$RESET"
    printf '%s╰────────────────────────────────────────────────────────────╯%s\n' "$BLUE" "$RESET"
    log STEP "$label"
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
    if [[ -t 1 && -n "${TERM:-}" ]]; then
        clear 2>/dev/null || true
    fi
    printf '%s%s' "$CYAN" "$BOLD"
    cat <<'BANNER'
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║   ████████╗███████╗ ██████╗██╗  ██╗ ██████╗  ██████╗ ██████╗    ║
║   ╚══██╔══╝██╔════╝██╔════╝██║  ██║██╔═══██╗██╔════╝ ██╔══██╗   ║
║      ██║   █████╗  ██║     ███████║██║   ██║██║  ███╗██████╔╝   ║
║      ██║   ██╔══╝  ██║     ██╔══██║██║   ██║██║   ██║██╔══██╗   ║
║      ██║   ███████╗╚██████╗██║  ██║╚██████╔╝╚██████╔╝██║  ██║   ║
║      ╚═╝   ╚══════╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝   ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
BANNER
    printf '%s%sTechOGR • BSPWM Dotfiles Installer v%s%s\n' "$BLUE" "$BOLD" "$SCRIPT_VERSION" "$RESET"
    printf '%sArch family • X11 • BSPWM • Eww • LightDM • AUR%s\n\n' "$DIM" "$RESET"
    printf '%s %s %s\n\n' "$CYAN" '╭────────────────────────────────────────────────────────────╮' "$RESET"
    printf '%s │ %sInstalación limpia, segura y fiel al repositorio%s │%s\n' "$CYAN" "$BOLD" "$RESET" "$CYAN"
    printf '%s │ %s• backups antes de reemplazar configuraciones%s        │%s\n' "$CYAN" "$DIM" "$RESET" "$CYAN"
    printf '%s │ %s• dotfiles copiados sin alterar su contenido%s         │%s\n' "$CYAN" "$DIM" "$RESET" "$CYAN"
    printf '%s │ %s• componentes opcionales aislados de fallos%s         │%s\n' "$CYAN" "$DIM" "$RESET" "$CYAN"
    printf '%s ╰────────────────────────────────────────────────────────────╯ %s\n\n' "$CYAN" "$RESET"
    log INFO "Installer v$SCRIPT_VERSION started from $SCRIPT_DIR"
}

check_execution() {
    step "1/12 - Verificación de ejecución y herramientas básicas"

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
    step "2/12 - Detección de Arch Linux y estado de pacman"

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
    step "3/12 - Dependencias base y compilación AUR"
    local pkgs=(base-devel git curl ca-certificates)
    local pkg
    for pkg in "${pkgs[@]}"; do
        install_repo_pkg "$pkg" yes || true
    done
    ((${#FAILED_REQUIRED[@]} == 0)) || fatal "No se pudieron instalar dependencias base: ${FAILED_REQUIRED[*]}"
    success "base-devel, git y utilidades requeridas están disponibles."
}

install_aur_helper() {
    step "4/12 - Detección / instalación del AUR helper"

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
    export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"

    if command_exists eww; then
        success "Eww ya está disponible: $(eww --version 2>/dev/null | head -n1 || printf '%s' 'versión instalada')"
        return 0
    fi

    if [[ -n "$AUR_HELPER" ]]; then
        info "Probando Eww desde AUR con $AUR_HELPER..."
        if "$AUR_HELPER" -S --needed --noconfirm eww >>"$LOG_FILE" 2>&1 && command_exists eww; then
            success "Eww instalado correctamente desde AUR."
            return 0
        fi
        warn "El paquete AUR de Eww no es compatible con el toolchain actual; activando fallback upstream."
    fi

    local build_dir="$HOME/.local/state/techogr-bspwm/build/eww-source"
    local eww_repo="https://github.com/elkowar/eww.git"
    local eww_deps=(pkgconf gtk3 gtk-layer-shell pango gdk-pixbuf2 cairo glib2 dbus libdbusmenu-gtk3)
    local dep

    for dep in "${eww_deps[@]}"; do
        if ! is_pkg_installed "$dep"; then
            install_repo_pkg "$dep" yes || true
        fi
    done

    if ! command_exists cargo; then
        if command_exists rustup; then
            info "Activando Rust stable mediante rustup..."
            rustup toolchain install stable --profile minimal >>"$LOG_FILE" 2>&1 || true
            rustup default stable >>"$LOG_FILE" 2>&1 || true
        else
            install_repo_pkg rust yes || true
        fi
    fi

    command_exists cargo || {
        warn "Cargo no está disponible; Eww no pudo compilarse."
        FAILED_OPTIONAL+=("eww")
        return 1
    }

    mkdir -p "$(dirname -- "$build_dir")"
    rm -rf -- "$build_dir"

    info "Clonando la fuente oficial de Eww..."
    if ! git clone --depth=1 https://github.com/elkowar/eww.git "$build_dir" >>"$LOG_FILE" 2>&1; then
        warn "No se pudo clonar Eww desde GitHub."
        FAILED_OPTIONAL+=("eww")
        return 1
    fi

    info "Compilando Eww para X11..."
    if ! (cd "$build_dir" && cargo build --release --no-default-features --features x11) >>"$LOG_FILE" 2>&1; then
        warn "La compilación de Eww falló. Revisa $LOG_FILE."
        FAILED_OPTIONAL+=("eww")
        return 1
    fi

    local built="$build_dir/target/release/eww"
    [[ -x "$built" ]] || {
        warn "Cargo terminó pero no produjo $built."
        FAILED_OPTIONAL+=("eww")
        return 1
    }

    # Install the fallback system-wide so the repository's ORIGINAL bspwmrc
    # can call `eww` without changing its PATH or modifying its contents.
    if sudo install -Dm755 "$built" /usr/local/bin/eww >>"$LOG_FILE" 2>&1; then
        hash -r 2>/dev/null || true
        export PATH="/usr/local/bin:$HOME/.local/bin:$PATH"
        if command_exists eww; then
            success "Eww compilado e instalado en /usr/local/bin/eww."
            return 0
        fi
    fi

    warn "No se pudo colocar el binario de Eww en /usr/local/bin."
    FAILED_OPTIONAL+=("eww")
    return 1
}

install_packages() {
    step "5/12 - Paquetes X11, BSPWM, audio, utilidades y estética"

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
    step "6/12 - Copia de seguridad de configuraciones existentes"

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

copy_exact() {
    local src="$1" dst="$2"
    [[ -e "$src" || -L "$src" ]] || return 0
    mkdir -p "$(dirname -- "$dst")"
    rm -rf -- "$dst"
    cp -a -- "$src" "$dst" >>"$LOG_FILE" 2>&1 || {
        warn "No se pudo desplegar exactamente: $src -> $dst"
        return 1
    }
    return 0
}

copy_tree_merge() {
    local src="$1" dst="$2"
    [[ -d "$src" ]] || return 0
    mkdir -p "$dst"
    cp -a -- "$src/." "$dst/" >>"$LOG_FILE" 2>&1 || {
        warn "No se pudo copiar completamente: $src -> $dst"
        return 1
    }
    return 0
}

setup_configs() {
    step "7/12 - Dotfiles — despliegue exacto del repositorio"

    mkdir -p "$HOME/.config" "$HOME/.local/bin" "$HOME/.local/share/applications" "$HOME/.local/share/fonts" "$HOME/Pictures/Wallpapers"

    # IMPORTANT: every config/<name> maps exactly to ~/.config/<name>.
    # The destination is removed only AFTER backup_user_configs() completed.
    # No sed/cat/append operation is allowed to modify repository-managed files.
    local src name rc=0
    if [[ -d "$SCRIPT_DIR/config" ]]; then
        while IFS= read -r -d '' src; do
            name="${src##*/}"
            copy_exact "$src" "$HOME/.config/$name" || rc=1
        done < <(find "$SCRIPT_DIR/config" -mindepth 1 -maxdepth 1 -print0 | sort -z)
    fi

    # home/* maps to $HOME/* exactly (.zshrc currently lives here).
    if [[ -d "$SCRIPT_DIR/home" ]]; then
        while IFS= read -r -d '' src; do
            name="${src##*/}"
            copy_exact "$src" "$HOME/$name" || rc=1
        done < <(find "$SCRIPT_DIR/home" -mindepth 1 -maxdepth 1 -print0 | sort -z)
    fi

    # Wallpapers are copied without changing filenames or image contents.
    if [[ -d "$SCRIPT_DIR/Wallpapers" ]]; then
        copy_tree_merge "$SCRIPT_DIR/Wallpapers" "$HOME/Pictures/Wallpapers" || rc=1
    fi

    # Miscellaneous repository payloads are copied file-for-file into their
    # intended locations without deleting unrelated user data in those folders.
    # File bytes and repository permissions are preserved by cp -a.
    copy_tree_merge "$SCRIPT_DIR/misc/applications" "$HOME/.local/share/applications" || rc=1
    copy_tree_merge "$SCRIPT_DIR/misc/asciiart" "$HOME/.local/share/techogr/asciiart" || rc=1
    copy_tree_merge "$SCRIPT_DIR/misc/bin" "$HOME/.local/bin" || rc=1
    copy_tree_merge "$SCRIPT_DIR/misc/firefox" "$HOME/.local/share/techogr/firefox" || rc=1
    copy_tree_merge "$SCRIPT_DIR/misc/fonts" "$HOME/.local/share/fonts" || rc=1
    copy_tree_merge "$SCRIPT_DIR/misc/startup-page" "$HOME/.local/share/techogr/startup-page" || rc=1

    # Pacman hook is a system-level payload from the repository. Copy it
    # byte-for-byte while keeping a backup of an existing hook.
    local hook="$SCRIPT_DIR/misc/polybar-update.hook"
    if [[ -f "$hook" ]]; then
        sudo install -d -m 755 /etc/pacman.d/hooks
        if [[ -f /etc/pacman.d/hooks/polybar-update.hook ]]; then
            sudo cp -a /etc/pacman.d/hooks/polybar-update.hook "$BACKUP_DIR/polybar-update.hook" 2>>"$LOG_FILE" || warn "No se pudo respaldar el hook de pacman existente."
        fi
        sudo install -m 644 "$hook" /etc/pacman.d/hooks/polybar-update.hook >>"$LOG_FILE" 2>&1 || rc=1
    fi

    # User systemd units are already part of config/systemd/user and therefore
    # were copied exactly above. Reload and enable the timer when a user bus is
    # available; never rewrite the unit contents.
    if [[ -d "$HOME/.config/systemd/user" ]]; then
        if systemctl --user daemon-reload >>"$LOG_FILE" 2>&1; then
            if [[ -f "$HOME/.config/systemd/user/ArchUpdates.timer" ]]; then
                systemctl --user start ArchUpdates.timer >>"$LOG_FILE" 2>&1 || warn "ArchUpdates.timer no pudo iniciarse en esta sesión; no se modificará su estado persistente."
            fi
        else
            warn "No hay bus systemd --user disponible durante la instalación; las unidades quedaron copiadas correctamente."
        fi
    fi

    # kitty/ is a top-level duplicate of config/kitty in the current repo.
    # Keep a divergence warning rather than silently inventing a merged config.
    if [[ -d "$SCRIPT_DIR/kitty" ]]; then
        if [[ -d "$SCRIPT_DIR/config/kitty" ]] && ! diff -qr "$SCRIPT_DIR/config/kitty" "$SCRIPT_DIR/kitty" >>"$LOG_FILE" 2>&1; then
            warn "config/kitty y kitty/ difieren en el repositorio; se conserva config/kitty como fuente canónica."
        fi
    fi

    command_exists update-desktop-database && update-desktop-database "$HOME/.local/share/applications" >>"$LOG_FILE" 2>&1 || true
    command_exists fc-cache && fc-cache -f >>"$LOG_FILE" 2>&1 || true

    (( rc == 0 )) || fatal "Uno o más árboles de dotfiles no pudieron copiarse exactamente."
    success "Dotfiles administrados por el repositorio desplegados sin modificar su contenido."
}

patch_session_safety() {
    step "8/12 - Entorno X11 — soporte extra sin tocar los dotfiles"

    # This function intentionally DOES NOT modify ~/.config/bspwm/*.
    # Repository-managed files must remain exact. Environment/service helpers live
    # outside the repository instead.
    cat > "$HOME/.xprofile" <<'EOF_XPROFILE'
#!/bin/sh
# TechOGR session environment (installer-managed, not repository-managed)
export PATH="/usr/local/bin:$HOME/.local/bin:$HOME/.config/bspwm/bin:$PATH"
export XDG_CURRENT_DESKTOP='bspwm'
export DESKTOP_SESSION='bspwm'
export XDG_SESSION_TYPE='x11'
export XCURSOR_SIZE="${XCURSOR_SIZE:-24}"
export _JAVA_AWT_WM_NONREPARENTING="${_JAVA_AWT_WM_NONREPARENTING:-1}"

[ -f "$HOME/.Xresources" ] && command -v xrdb >/dev/null 2>&1 && xrdb -merge "$HOME/.Xresources"

# Keep the original bspwmrc untouched while making helper services available.
if command -v xss-lock >/dev/null 2>&1 && command -v "$HOME/.local/bin/techogr_lock" >/dev/null 2>&1; then
    pkill -x xss-lock >/dev/null 2>&1 || true
    xss-lock --transfer-sleep-lock -- "$HOME/.local/bin/techogr_lock" >/dev/null 2>&1 &
fi
EOF_XPROFILE
    chmod 644 "$HOME/.xprofile"

    cat > "$HOME/.xinitrc" <<'EOF_XINITRC'
#!/bin/sh
[ -f "$HOME/.xprofile" ] && . "$HOME/.xprofile"
exec bspwm
EOF_XINITRC
    chmod 755 "$HOME/.xinitrc"

    success "Entorno X11 preparado sin modificar ningún archivo administrado por el repositorio."
}

configure_picom() {
    local conf="$HOME/.config/bspwm/config/picom/picom.conf"
    if [[ -f "$conf" ]]; then
        info "Picom: se conserva exactamente el archivo del repositorio ($conf)."
    else
        warn "No se encontró $conf; se mantiene el sistema sin inventar una configuración nueva."
    fi
}

configure_browser_default() {
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
    step "10/12 - Display Manager y sesión BSPWM"

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
    step "9/12 - Lockscreen — fondo, fallback y bloqueo automático"

    local lock_script="$HOME/.local/bin/techogr_lock"
    cat > "$lock_script" <<'EOF_LOCK'
#!/usr/bin/env bash
set -u

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

    if command_exists betterlockscreen; then
        local wall=""
        wall="$(find "$HOME/Pictures/Wallpapers" -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) -print -quit 2>/dev/null || true)"
        if [[ -n "$wall" ]]; then
            info "Generando caché inicial de betterlockscreen..."
            betterlockscreen -u "$wall" >>"$LOG_FILE" 2>&1 || warn "No se pudo generar la caché inicial; el fallback seguirá disponible."
        fi
    fi

    # Keybindings remain repository-owned and are therefore NEVER appended here.
    success "Lockscreen preparado sin modificar sxhkdrc ni bspwmrc."
}

verify_repo_integrity() {
    step "11/12 - Integridad — comprobando que el repositorio no fue alterado"
    local mismatches=()
    local src name

    if [[ -d "$SCRIPT_DIR/config" ]]; then
        while IFS= read -r -d '' src; do
            name="${src##*/}"
            if ! diff -qr "$src" "$HOME/.config/$name" >>"$LOG_FILE" 2>&1; then
                mismatches+=("config/$name")
            fi
        done < <(find "$SCRIPT_DIR/config" -mindepth 1 -maxdepth 1 -print0 | sort -z)
    fi

    if [[ -d "$SCRIPT_DIR/home" ]]; then
        while IFS= read -r -d '' src; do
            name="${src##*/}"
            if [[ -f "$src" ]] && ! cmp -s "$src" "$HOME/$name"; then
                mismatches+=("home/$name")
            elif [[ -d "$src" ]] && ! diff -qr "$src" "$HOME/$name" >>"$LOG_FILE" 2>&1; then
                mismatches+=("home/$name")
            fi
        done < <(find "$SCRIPT_DIR/home" -mindepth 1 -maxdepth 1 -print0 | sort -z)
    fi

    if [[ -f "$SCRIPT_DIR/misc/polybar-update.hook" ]]; then
        if ! sudo cmp -s "$SCRIPT_DIR/misc/polybar-update.hook" /etc/pacman.d/hooks/polybar-update.hook; then
            mismatches+=("misc/polybar-update.hook")
        fi
    fi

    if ((${#mismatches[@]} == 0)); then
        success "Integridad OK: los archivos administrados por el repositorio permanecen intactos."
    else
        error "Se detectaron diferencias tras el despliegue: ${mismatches[*]}"
        fatal "La instalación no puede considerarse íntegra; revisa $LOG_FILE"
    fi
}

post_install_fixes() {
    step "12/12 - Diagnóstico final - rutas, servicios y archivos críticos"

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
    printf '\n %sIntegridad:%s     archivos del repositorio preservados sin parches automáticos\n' "$CYAN" "$RESET"
    printf ' %sLockscreen:%s     helper generado fuera de ~/.config/bspwm\n' "$CYAN" "$RESET"

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
    verify_repo_integrity
    post_install_fixes
    show_summary
}

main "$@"
