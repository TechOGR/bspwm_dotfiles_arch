#!/usr/bin/env bash
# ============================================================
# TechOGR BSPWM Dotfiles
# Professional Arch Linux Installer (corregido)
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
# FIX: usamos `tee` con pipe simple y esperamos a que el pipe
# termine con `wait` al final del script, en vez de un process
# substitution "silencioso" que podía perder las últimas líneas.
# ------------------------------------------------------------
exec > >(tee -a "$LOG_FILE") 2>&1
TEE_PID=$!

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
    printf ' ████████╗███████╗ ██████╗██╗  ██╗ ██████╗  ██████╗ ██████╗ \n'
    printf ' ╚══██╔══╝██╔════╝██╔════╝██║  ██║██╔═══██╗██╔════╝ ██╔══██╗\n'
    printf '    ██║   █████╗  ██║     ███████║██║   ██║██║  ███╗██████╔╝\n'
    printf '    ██║   ██╔══╝  ██║     ██╔══██║██║   ██║██║   ██║██╔══██╗\n'
    printf '    ██║   ███████╗╚██████╗██║  ██║╚██████╔╝╚██████╔╝██║  ██║\n'
    printf '    ╚═╝   ╚══════╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝\n'
    printf '%b\n' "${RESET}"
    printf '%b\n' "${WHITE}${BOLD}        BSPWM DOTFILES INSTALLER${RESET}"
    printf '%b\n\n' "${BLUE}        Arch Linux Edition${RESET}"
}

info()  { printf '%b\n' "${BLUE} [INFO]${RESET} $*"; }
ok()    { printf '%b\n' "${GREEN} [ OK ]${RESET} $*"; }
warn()  { printf '%b\n' "${YELLOW} [ WARN ]${RESET} $*"; }
error() { printf '%b\n' "${RED} [ERROR ]${RESET} $*"; }
step()  { printf '\n%b\n' "${CYAN}${BOLD} ➜ $*${RESET}"; }

die() {
    error "$*"
    printf '\n'
    error "Instalación abortada."
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
# Sudo keep-alive
# FIX: pedimos la contraseña una sola vez al inicio y la
# mantenemos viva en segundo plano, para que no te la pida
# a mitad de una compilación larga (makepkg, pacman -Syu, etc.)
# ------------------------------------------------------------
keep_sudo_alive() {
    step "Solicitando permisos de administrador"
    sudo -v || die "No se pudieron obtener permisos de sudo."
    ( while true; do sudo -n true; sleep 60; kill -0 "$$" 2>/dev/null || exit; done ) &
    SUDO_KEEPALIVE_PID=$!
}

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
    if [[ "${ID:-}" != "arch" ]] && [[ "${ID_LIKE:-}" != *"arch"* ]]; then
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
# PARU (único ayudante de AUR necesario)
# FIX: se elimina install_yay(), que compilaba yay-bin sin
# usarlo nunca en el resto del script (perdía tiempo y era
# una fuente extra de posibles fallos de compilación).
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
        git clone --depth=1 https://aur.archlinux.org/paru-bin.git
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
# ------------------------------------------------------------
install_packages() {
    step "Instalando stack BSPWM"
    local official_packages=(
        # X11
        xorg-server xorg-xinit xorg-xrandr xorg-xsetroot
        xorg-xprop xorg-xwininfo xorg-xdpyinfo xorg-xset
        # Window manager
        bspwm sxhkd
        # Bar / compositor / launcher
        polybar picom rofi
        # Desktop utilities
        feh dunst xsettingsd lxappearance lxsession polkit-gnome
        # Terminal / shell
        kitty zsh fzf
        # File manager
        thunar thunar-volman tumbler gvfs
        # Audio
        pipewire pipewire-pulse pipewire-alsa wireplumber pavucontrol playerctl
        # Network
        networkmanager network-manager-applet
        # Clipboard / screenshots
        xclip xsel maim scrot
        # CLI
        bc jq unzip wget curl git rsync htop btop
        # Fonts (incluye Nerd Fonts desde repos oficiales, sin AUR)
        noto-fonts noto-fonts-emoji ttf-dejavu
        ttf-jetbrains-mono-nerd ttf-firacode-nerd ttf-nerd-fonts-symbols
        # GTK / themes
        gtk3 gtk4 papirus-icon-theme
        # System
        dbus dbus-broker polkit
        # Display manager (para poder elegir la sesión BSPWM al iniciar)
        lightdm lightdm-gtk-greeter
        # Utilidades usadas por los scripts
        imagemagick xdotool wmctrl eza bat
    )

    sudo pacman -S --needed --noconfirm "${official_packages[@]}"
    ok "Paquetes oficiales instalados"
}

# ------------------------------------------------------------
# AUR packages
# FIX: se quita "nerd-fonts" (meta-paquete AUR enorme e
# interactivo). Las fuentes Nerd necesarias ya se instalan
# arriba desde el repo oficial.
# ------------------------------------------------------------
install_aur_packages() {
    step "Instalando paquetes AUR"
    if ! command -v paru >/dev/null 2>&1; then
        die "paru no está disponible."
    fi

    local aur_packages=(
        fzf-tab-git
    )

    paru -S --needed --noconfirm "${aur_packages[@]}"
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
    printf '   %s\n' "$BACKUP_DIR"
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
    rsync -a --delete "$source/" "$destination/"
}

copy_file() {
    local source="$1"
    local destination="$2"
    [[ -f "$source" ]] || return 0
    mkdir -p "$(dirname "$destination")"
    install -m 0644 "$source" "$destination"
}

install_dotfiles() {
    step "Instalando configuración"

    # config/*
    if [[ -d "$SCRIPT_DIR/config" ]]; then
        while IFS= read -r -d '' source; do
            local name
            name="$(basename "$source")"
            copy_directory "$source" "$CONFIG_DIR/$name"
        done < <(find "$SCRIPT_DIR/config" -mindepth 1 -maxdepth 1 -type d -print0)
    fi

    # home/*
    if [[ -d "$SCRIPT_DIR/home" ]]; then
        while IFS= read -r -d '' source; do
            local name
            name="$(basename "$source")"
            copy_file "$source" "$HOME_DIR/$name"
        done < <(find "$SCRIPT_DIR/home" -mindepth 1 -maxdepth 1 -type f -print0)
    fi

    # misc/bin/*
    if [[ -d "$SCRIPT_DIR/misc/bin" ]]; then
        rsync -a "$SCRIPT_DIR/misc/bin/" "$LOCAL_BIN/"
    fi

    # misc/applications/*
    if [[ -d "$SCRIPT_DIR/misc/applications" ]]; then
        rsync -a "$SCRIPT_DIR/misc/applications/" "$HOME/.local/share/applications/"
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

    local pictures_dir
    pictures_dir="$(xdg-user-dir PICTURES 2>/dev/null || true)"
    if [[ -z "$pictures_dir" || "$pictures_dir" == "$HOME" ]]; then
        pictures_dir="$HOME/Pictures"
    fi

    local wallpaper_dir="$pictures_dir/Wallpapers"
    mkdir -p "$wallpaper_dir"

    rsync -av "$wallpaper_source/" "$wallpaper_dir/"

    ok "Wallpapers instalados en:"
    printf '   %s\n' "$wallpaper_dir"

    mkdir -p "$HOME/.local/share/techogr-bspwm"
    ln -sfn "$wallpaper_dir" "$HOME/.local/share/techogr-bspwm/Wallpapers"
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
    done < <(find "$wallpaper_dir" -type f \
        \( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" -o -iname "*.webp" \) \
        -print0 2>/dev/null)

    if [[ -z "$wallpaper" ]]; then
        warn "No se encontraron imágenes en Wallpapers."
        return
    fi

    mkdir -p "$HOME/.config/techogr"
    printf '%s\n' "$wallpaper" > "$HOME/.config/techogr/default-wallpaper"

    # FIX: aplicamos el wallpaper de inmediato con feh si hay
    # sesión X activa (útil si el script se corre dentro de X).
    if [[ -n "${DISPLAY:-}" ]] && command -v feh >/dev/null 2>&1; then
        feh --bg-fill "$wallpaper" >/dev/null 2>&1 || true
    fi

    ok "Wallpaper predeterminado:"
    printf '   %s\n' "$wallpaper"
}

# ------------------------------------------------------------
# Permissions
# ------------------------------------------------------------
fix_permissions() {
    step "Corrigiendo permisos"

    if [[ -f "$CONFIG_DIR/bspwm/bspwmrc" ]]; then
        chmod +x "$CONFIG_DIR/bspwm/bspwmrc"
    fi

    if [[ -d "$CONFIG_DIR/bspwm/bin" ]]; then
        find "$CONFIG_DIR/bspwm/bin" -type f -exec chmod +x {} \;
    fi

    for directory in \
        "$CONFIG_DIR/polybar" \
        "$CONFIG_DIR/rofi" \
        "$CONFIG_DIR/sxhkd"; do
        if [[ -d "$directory" ]]; then
            find "$directory" -type f \( -name "*.sh" -o -name "*.py" \) \
                -exec chmod +x {} \; 2>/dev/null || true
        fi
    done

    if [[ -d "$LOCAL_BIN" ]]; then
        find "$LOCAL_BIN" -type f -exec chmod +x {} \;
    fi

    [[ -f "$HOME/.xinitrc" ]] && chmod +x "$HOME/.xinitrc"
    [[ -f "$HOME/.xprofile" ]] && chmod +x "$HOME/.xprofile"

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
export PATH="$HOME/.local/bin:$PATH"

if command -v dbus-update-activation-environment >/dev/null 2>&1; then
    dbus-update-activation-environment --systemd \
        DISPLAY XAUTHORITY XDG_CURRENT_DESKTOP XDG_SESSION_DESKTOP \
        XDG_SESSION_TYPE DBUS_SESSION_BUS_ADDRESS \
        >/dev/null 2>&1 || true
fi

# No inicies aquí polybar, picom, sxhkd, etc.
# bspwmrc controla todo el entorno gráfico.
exec bspwm
EOF
    chmod +x "$HOME/.xinitrc"

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
# No inicies bspwm aquí; lo hace el display manager o .xinitrc.
EOF
    chmod +x "$HOME/.xprofile"

    ok "Sesión X11 configurada"
}

# ------------------------------------------------------------
# Desktop session (.desktop para el login manager)
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
set -u
command -v xrandr >/dev/null 2>&1 || exit 0
xrandr >/dev/null 2>&1 || exit 0

mapfile -t outputs < <(xrandr --query | awk '$2 == "connected" {print $1}')
((${#outputs[@]} > 0)) || exit 0

if ((${#outputs[@]} == 1)); then
    exit 0
fi

# Múltiples monitores: no forzar un output fijo (p. ej. Virtual-1).
# BSPWM gestiona los monitores sin tocar xrandr aquí.
exit 0
EOF
    chmod +x "$LOCAL_BIN/techogr-monitor-setup"
    ok "Detector de monitores instalado"
}

# ------------------------------------------------------------
# Zsh como shell por defecto
# FIX: el script instalaba zsh (paquete) pero nunca lo dejaba
# como shell por defecto del usuario.
# ------------------------------------------------------------
setup_shell() {
    step "Configurando Zsh como shell por defecto"
    local zsh_path
    zsh_path="$(command -v zsh || true)"

    if [[ -z "$zsh_path" ]]; then
        warn "zsh no está instalado, se omite este paso."
        return
    fi

    if [[ "$SHELL" != "$zsh_path" ]]; then
        chsh -s "$zsh_path" "$USER" || warn "No se pudo cambiar la shell por defecto automáticamente."
    fi

    ok "Zsh configurado como shell por defecto (efectivo en el próximo login)"
}

# ------------------------------------------------------------
# Servicios del sistema
# FIX: el script instalaba NetworkManager y lightdm pero nunca
# los habilitaba; sin esto no hay red ni login gráfico tras reiniciar.
# ------------------------------------------------------------
enable_services() {
    step "Habilitando servicios del sistema"

    sudo systemctl enable --now NetworkManager.service \
        || warn "No se pudo habilitar NetworkManager."

    if command -v lightdm >/dev/null 2>&1; then
        sudo systemctl enable lightdm.service \
            || warn "No se pudo habilitar lightdm."
    fi

    ok "Servicios habilitados"
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
                warn "Sin permiso de ejecución: $file"
                chmod +x "$file"
            fi
        done < <(find "$CONFIG_DIR/bspwm/bin" -type f -print0)
    fi

    if [[ "$missing" -eq 1 ]]; then
        warn "Faltan archivos de configuración. Revisa tu carpeta config/ antes de iniciar sesión."
    else
        ok "Archivos BSPWM validados"
    fi
}

# ------------------------------------------------------------
# Resumen final
# ------------------------------------------------------------
print_summary() {
    printf '\n'
    line
    printf '%b\n' "${GREEN}${BOLD} Instalación completada${RESET}"
    line
    printf '%b\n' " Backup guardado en: ${BACKUP_DIR}"
    printf '%b\n' " Log completo en:    ${LOG_FILE}"
    printf '\n'
    printf '%b\n' " Reinicia el sistema o cierra sesión."
    printf '%b\n' " En tu login manager (LightDM) selecciona la sesión ${BOLD}BSPWM${RESET}."
    printf '\n'
}

# ------------------------------------------------------------
# MAIN
# FIX: esta era la pieza más importante que faltaba: sin un
# main() que orqueste todo, el script no ejecutaba nada al
# correrlo (solo definía funciones).
# ------------------------------------------------------------
main() {
    title
    keep_sudo_alive
    check_arch
    check_network
    install_base_tools
    install_paru
    install_packages
    install_aur_packages
    create_backup
    prepare_directories
    install_dotfiles
    install_wallpapers
    configure_default_wallpaper
    fix_permissions
    install_xsession
    install_desktop_session
    install_safe_launcher
    install_monitor_helper
    setup_shell
    enable_services
    check_bspwm_files
    print_summary

    # Detiene el proceso de sudo keep-alive
    if [[ -n "${SUDO_KEEPALIVE_PID:-}" ]]; then
        kill "$SUDO_KEEPALIVE_PID" 2>/dev/null || true
    fi
}

main "$@"

# Espera a que `tee` termine de volcar el log antes de salir.
wait "$TEE_PID" 2>/dev/null || true
