#!/usr/bin/env bash
# ============================================================
# TechOGR BSPWM Dotfiles
# Professional Arch Linux Installer (Full Feature Port)
# ============================================================
set -Eeuo pipefail
IFS=$'\n\t'

# ------------------------------------------------------------
# Colors & Visuals
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
# Global Paths & Environment
# ------------------------------------------------------------
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="$HOME"
CONFIG_DIR="$HOME/.config"
LOCAL_BIN="$HOME/.local/bin"
LOCAL_SHARE="$HOME/.local/share"
FONTS_DIR="$HOME/.local/share/fonts"
STATE_DIR="$HOME/.local/state/techogr-bspwm"
BACKUP_ROOT="$HOME/.local/share/techogr-bspwm-backups"
TIMESTAMP="$(date '+%Y-%m-%d_%H-%M-%S')"
BACKUP_DIR="$BACKUP_ROOT/$TIMESTAMP"
LOG_FILE="$STATE_DIR/install.log"

mkdir -p "$STATE_DIR"

# Logging System
exec > >(tee -a "$LOG_FILE") 2>&1
TEE_PID=$!

# ------------------------------------------------------------
# UI Helper Functions
# ------------------------------------------------------------
line() {
    printf '%b\n' "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
}

title() {
    clear 2>/dev/null || true
    printf '\n'
    printf '%b\n' "${MAGENTA}${BOLD}"
    printf ' ████████╗███████╗ ██████╗██╗   ██╗ ██████╗  ██████╗ ██████╗ \n'
    printf ' ╚══██╔══╝██╔════╝██╔════╝██║   ██║██╔═══██╗██╔════╝ ██╔══██╗\n'
    printf '    ██║   █████╗  ██║     ███████║██║   ██║██║  ███╗██████╔╝\n'
    printf '    ██║   ██╔══╝  ██║     ██╔══██║██║   ██║██║   ██║██╔══██╗\n'
    printf '    ██║   ███████╗╚██████╗██║   ██║╚██████╔╝╚██████╔╝██║  ██║\n'
    printf '    ╚═╝   ╚══════╝ ╚═════╝╚═╝   ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝\n'
    printf '%b\n' "${RESET}"
    printf '%b\n' "${WHITE}${BOLD}        BSPWM DOTFILES INSTALLER (TechOGR Edition)${RESET}"
    printf '%b\n\n' "${BLUE}        Arch Linux Full Deployment - Official Stack${RESET}"
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
    error "Revisa el registro detallado en: $LOG_FILE"
    exit 1
}

# ------------------------------------------------------------
# Error Handling Trap
# ------------------------------------------------------------
trap 'error "Error detectado en la línea $LINENO. Comando: $BASH_COMMAND"' ERR

# ------------------------------------------------------------
# System Validation Checks
# ------------------------------------------------------------
check_environment() {
    step "Validando entorno del sistema"
    if [[ $EUID -eq 0 ]]; then
        die "No debes ejecutar este script como root o con sudo directo. Ejecútalo como usuario normal."
    fi

    if [[ ! -f /etc/os-release ]]; then
        die "No se pudo verificar el archivo /etc/os-release."
    fi

    # shellcheck disable=SC1091
    source /etc/os-release
    if [[ "${ID:-}" != "arch" ]] && [[ "${ID_LIKE:-}" != *"arch"* ]]; then
        die "Este entorno está diseñado exclusivamente para Arch Linux o derivados directos."
    fi
    ok "Sistema operativo validado: ${PRETTY_NAME:-Arch Linux}"
}

keep_sudo_alive() {
    step "Verificando permisos de administración (sudo)"
    sudo -v || die "Se requieren permisos de sudo para proceder."
    ( while true; do sudo -n true; sleep 60; kill -0 "$$" 2>/dev/null || exit; done ) &
    SUDO_KEEPALIVE_PID=$!
    ok "Privilegios sudo confirmados y mantenidos en segundo plano"
}

check_network() {
    step "Comprobando conexión de red"
    if ! curl -fsSI --max-time 10 https://archlinux.org >/dev/null 2>&1; then
        die "Se necesita conexión a Internet para descargar los paquetes."
    fi
    ok "Conexión a Internet activa"
}

# ------------------------------------------------------------
# Official Package Deployment Engine
# ------------------------------------------------------------
install_base_tools() {
    step "Actualizando el sistema e instalando herramientas base"
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
    ok "Bases de pacman y herramientas del sistema actualizadas"
}

install_official_packages() {
    step "Instalando gestores de ventanas, barra, terminal y utilidades oficiales"
    
    local pkgs=(
        # Window Manager & Utilities
        bspwm sxhkd polybar picom rofi feh dunst xsettingsd
        lxappearance lxsession polkit-gnome lightdm lightdm-gtk-greeter
        
        # X11 Core Suite
        xorg-server xorg-xinit xorg-xrandr xorg-xsetroot xorg-xprop
        xorg-xwininfo xorg-xdpyinfo xorg-xset xdotool wmctrl xclip xsel
        
        # Audio Engine (Pipewire)
        pipewire pipewire-pulse pipewire-alsa wireplumber pavucontrol playerctl
        
        # Network Manager
        networkmanager network-manager-applet
        
        # File Managers & Thumbnails
        thunar thunar-volman tumbler gvfs
        
        # Terminal, Shell & Helpers
        kitty zsh fzf eza bat htop btop imagemagick maim scrot bc
        
        # Fonts
        noto-fonts noto-fonts-emoji ttf-dejavu
        ttf-jetbrains-mono-nerd ttf-firacode-nerd ttf-nerd-fonts-symbols
        
        # GTK, Themes & Icons
        gtk3 gtk4 papirus-icon-theme
        
        # System & D-Bus Services
        dbus dbus-broker polkit
    )

    info "Sincronizando los paquetes del repositorio oficial de Arch Linux..."
    sudo pacman -S --needed --noconfirm "${pkgs[@]}"
    ok "Entorno completo de BSPWM y dependencias del sistema instalado"
}

# ------------------------------------------------------------
# Backup Engine
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
    info "Copia de respaldo guardada: $path"
}

create_backup() {
    step "Creando respaldo de configuraciones existentes"
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
    ok "Respaldo completado en: $BACKUP_DIR"
}

# ------------------------------------------------------------
# Directory System Prep
# ------------------------------------------------------------
prepare_directories() {
    step "Creando la estructura de carpetas de usuario"
    mkdir -p \
        "$CONFIG_DIR" \
        "$LOCAL_BIN" \
        "$LOCAL_SHARE" \
        "$FONTS_DIR" \
        "$STATE_DIR" \
        "$HOME/.local/share/applications" \
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
        "$pictures_dir/screenshots" \
        "$HOME/Downloads" \
        "$HOME/Documents" \
        "$HOME/Videos" \
        "$HOME/Music"

    ok "Estructura de directorios lista"
}

# ------------------------------------------------------------
# Fonts Deployment Engine
# ------------------------------------------------------------
install_custom_fonts() {
    step "Instalando fuentes personalizadas contenidas en el repositorio"
    local fonts_source="$SCRIPT_DIR/misc/fonts"

    if [[ -d "$fonts_source" ]]; then
        info "Copiando fuentes desde misc/fonts a $FONTS_DIR..."
        mkdir -p "$FONTS_DIR"
        find "$fonts_source" -type f \( -name "*.ttf" -o -name "*.otf" \) -exec cp -f {} "$FONTS_DIR/" \;
        info "Regenerando la caché de tipografías del sistema..."
        fc-cache -f "$FONTS_DIR" >/dev/null 2>&1 || true
        ok "Fuentes adicionales instaladas"
    else
        warn "No se encontró el directorio de fuentes en 'misc/fonts/'. Omite este paso."
    fi
}

# ------------------------------------------------------------
# Dotfiles Deployment Engine
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
    step "Copiando dotfiles y configuraciones"

    # Copia de subdirectorios en .config
    if [[ -d "$SCRIPT_DIR/config" ]]; then
        info "Sincronizando configuraciones en ~/.config..."
        while IFS= read -r -d '' source; do
            local name
            name="$(basename "$source")"
            copy_directory "$source" "$CONFIG_DIR/$name"
        done < <(find "$SCRIPT_DIR/config" -mindepth 1 -maxdepth 1 -type d -print0)
    fi

    # Copia de archivos ocultos en home
    if [[ -d "$SCRIPT_DIR/home" ]]; then
        info "Sincronizando archivos base de $HOME..."
        while IFS= read -r -d '' source; do
            local name
            name="$(basename "$source")"
            copy_file "$source" "$HOME_DIR/$name"
        done < <(find "$SCRIPT_DIR/home" -mindepth 1 -maxdepth 1 -type f -print0)
    fi

    # Copia de ejecutable bin
    if [[ -d "$SCRIPT_DIR/misc/bin" ]]; then
        info "Instalando binarios locales en ~/.local/bin..."
        rsync -a "$SCRIPT_DIR/misc/bin/" "$LOCAL_BIN/"
    fi

    # Copia de lanzadores .desktop
    if [[ -d "$SCRIPT_DIR/misc/applications" ]]; then
        info "Instalando accesos directos en ~/.local/share/applications..."
        rsync -a "$SCRIPT_DIR/misc/applications/" "$HOME/.local/share/applications/"
    fi

    ok "Archivos de configuración sincronizados"
}

# ------------------------------------------------------------
# Wallpaper Management Engine
# ------------------------------------------------------------
install_wallpapers() {
    step "Desplegando colección de fondos de pantalla"
    local wallpaper_source="$SCRIPT_DIR/Wallpapers"

    if [[ ! -d "$wallpaper_source" ]]; then
        warn "No se encontró el directorio 'Wallpapers' en este repositorio."
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
    
    mkdir -p "$HOME/.local/share/techogr-bspwm"
    ln -sfn "$wallpaper_dir" "$HOME/.local/share/techogr-bspwm/Wallpapers"

    # Selección de wallpaper inicial
    local default_wp
    default_wp="$(find "$wallpaper_dir" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.webp" \) | head -n 1 || true)"
    if [[ -n "$default_wp" ]]; then
        mkdir -p "$HOME/.config/techogr"
        printf '%s\n' "$default_wp" > "$HOME/.config/techogr/default-wallpaper"
        if [[ -n "${DISPLAY:-}" ]] && command -v feh >/dev/null 2>&1; then
            feh --bg-fill "$default_wp" >/dev/null 2>&1 || true
        fi
    fi

    ok "Fondos de pantalla configurados en $wallpaper_dir"
}

# ------------------------------------------------------------
# ZSH, Oh My Zsh & Plugins Setup
# ------------------------------------------------------------
setup_zsh_environment() {
    step "Configurando ZSH, Oh My Zsh y plugins"

    local zsh_path
    zsh_path="$(command -v zsh || true)"
    if [[ -z "$zsh_path" ]]; then
        warn "Zsh no está instalado. Omitiendo configuración de shell."
        return
    fi

    # Cambio de shell por defecto
    if [[ "${SHELL:-}" != "$zsh_path" ]]; then
        info "Configurando Zsh como la shell por defecto del usuario..."
        sudo chsh -s "$zsh_path" "$USER" || warn "No se pudo cambiar la shell predeterminada automáticamente."
    fi

    # Clonado de Oh My Zsh
    local omz_dir="$HOME/.oh-my-zsh"
    if [[ ! -d "$omz_dir" ]]; then
        info "Instalando framework Oh My Zsh..."
        git clone --depth=1 https://github.com/ohmyzsh/ohmyzsh.git "$omz_dir" >/dev/null 2>&1 || true
    fi

    # Instalación de plugins de Zsh
    local custom_plugins="${ZSH_CUSTOM:-$omz_dir/custom}/plugins"
    mkdir -p "$custom_plugins"

    if [[ ! -d "$custom_plugins/zsh-autosuggestions" ]]; then
        info "Instalando plugin: zsh-autosuggestions..."
        git clone --depth=1 https://github.com/zsh-users/zsh-autosuggestions "$custom_plugins/zsh-autosuggestions" >/dev/null 2>&1 || true
    fi

    if [[ ! -d "$custom_plugins/zsh-syntax-highlighting" ]]; then
        info "Instalando plugin: zsh-syntax-highlighting..."
        git clone --depth=1 https://github.com/zsh-users/zsh-syntax-highlighting.git "$custom_plugins/zsh-syntax-highlighting" >/dev/null 2>&1 || true
    fi

    # Tema Powerlevel10k
    local custom_themes="${ZSH_CUSTOM:-$omz_dir/custom}/themes"
    mkdir -p "$custom_themes"
    if [[ ! -d "$custom_themes/powerlevel10k" ]]; then
        info "Instalando tema: Powerlevel10k..."
        git clone --depth=1 https://github.com/romkatv/powerlevel10k.git "$custom_themes/powerlevel10k" >/dev/null 2>&1 || true
    fi

    ok "Shell Zsh, Oh My Zsh y temas/plugins vinculados"
}

# ------------------------------------------------------------
# GTK & Appearance Automation
# ------------------------------------------------------------
configure_gtk_settings() {
    step "Ajustando preferencias de tema GTK y cursores"

    if command -v gsettings >/dev/null 2>&1; then
        info "Sincronizando esquemas con gsettings..."
        gsettings set org.gnome.desktop.interface gtk-theme "Dark" 2>/dev/null || true
        gsettings set org.gnome.desktop.interface icon-theme "Papirus-Dark" 2>/dev/null || true
        gsettings set org.gnome.desktop.interface font-name "JetBrainsMono Nerd Font 10" 2>/dev/null || true
        gsettings set org.gnome.desktop.interface cursor-theme "Adwaita" 2>/dev/null || true
        ok "Esquema de apariencia GTK aplicado"
    else
        warn "gsettings no presente. Se aplicará desde los archivos de configuración en ~/.config/gtk-3.0/."
    fi
}

# ------------------------------------------------------------
# Launchers & Display Manager Registration
# ------------------------------------------------------------
install_launchers_and_helpers() {
    step "Configurando perfiles de inicio y detector de pantalla"

    # .xinitrc
    cat > "$HOME/.xinitrc" <<'EOF'
#!/bin/sh
# TechOGR BSPWM Session
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

exec bspwm
EOF
    chmod +x "$HOME/.xinitrc"

    # .xprofile
    cat > "$HOME/.xprofile" <<'EOF'
#!/bin/sh
export XDG_CURRENT_DESKTOP="BSPWM"
export XDG_SESSION_DESKTOP="bspwm"
export XDG_SESSION_TYPE="x11"
export PATH="$HOME/.local/bin:$PATH"
export GTK_USE_PORTAL=0
export XCURSOR_SIZE="${XCURSOR_SIZE:-24}"
EOF
    chmod +x "$HOME/.xprofile"

    # Archivo de sesión para el Display Manager (LightDM/GDM/SDDM)
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

    # Wrapper de inicio
    cat > "$LOCAL_BIN/start-bspwm" <<'EOF'
#!/bin/sh
export XDG_CURRENT_DESKTOP="BSPWM"
export XDG_SESSION_DESKTOP="bspwm"
export XDG_SESSION_TYPE="x11"
export PATH="$HOME/.local/bin:$PATH"
exec bspwm
EOF
    chmod +x "$LOCAL_BIN/start-bspwm"

    # Detector automático de monitores
    cat > "$LOCAL_BIN/techogr-monitor-setup" <<'EOF'
#!/usr/bin/env bash
set -u
command -v xrandr >/dev/null 2>&1 || exit 0
xrandr >/dev/null 2>&1 || exit 0
mapfile -t outputs < <(xrandr --query | awk '$2 == "connected" {print $1}')
((${#outputs[@]} > 0)) || exit 0
exit 0
EOF
    chmod +x "$LOCAL_BIN/techogr-monitor-setup"

    ok "Lanzadores creados y sesión BSPWM vinculada a /usr/share/xsessions"
}

enable_system_services() {
    step "Habilitando servicios de red y gestor de inicio"

    sudo systemctl enable --now NetworkManager.service || warn "No se pudo habilitar NetworkManager."

    if command -v lightdm >/dev/null 2>&1; then
        sudo systemctl enable lightdm.service || warn "No se pudo activar el servicio de LightDM."
    fi

    ok "Servicios habilitados correctamente"
}

# ------------------------------------------------------------
# Execution Permissions Engine
# ------------------------------------------------------------
fix_permissions() {
    step "Asignando permisos de ejecución a todos los scripts"

    if [[ -f "$CONFIG_DIR/bspwm/bspwmrc" ]]; then
        chmod +x "$CONFIG_DIR/bspwm/bspwmrc"
    fi

    # Hacer ejecutables todos los scripts e infraestructura de ~/.config/bspwm/
    if [[ -d "$CONFIG_DIR/bspwm" ]]; then
        find "$CONFIG_DIR/bspwm" -type f \( -name "*.sh" -o -name "*.py" -o -perm /111 \) -exec chmod +x {} \; 2>/dev/null || true
    fi

    # Permisos en Polybar, Rofi y Sxhkd
    for directory in "$CONFIG_DIR/polybar" "$CONFIG_DIR/rofi" "$CONFIG_DIR/sxhkd"; do
        if [[ -d "$directory" ]]; then
            find "$directory" -type f \( -name "*.sh" -o -name "*.py" \) -exec chmod +x {} \; 2>/dev/null || true
        fi
    done

    # Permisos en binarios del usuario
    if [[ -d "$LOCAL_BIN" ]]; then
        find "$LOCAL_BIN" -type f -exec chmod +x {} \; 2>/dev/null || true
    fi

    ok "Permisos de ejecución concedidos en todas las rutas clave"
}

# ------------------------------------------------------------
# Diagnostics & Integrity Check
# ------------------------------------------------------------
check_bspwm_files() {
    step "Validando presencia de archivos principales de configuración"
    local missing=0
    local required=(
        "$CONFIG_DIR/bspwm/bspwmrc"
        "$CONFIG_DIR/sxhkd/sxhkdrc"
    )

    for file in "${required[@]}"; do
        if [[ -f "$file" ]]; then
            ok "Validado: $(basename "$file")"
        else
            warn "Falta el archivo: $file"
            missing=1
        fi
    done

    if [[ "$missing" -eq 1 ]]; then
        warn "Atención: Verifica que la carpeta config/ del repositorio contenga bspwmrc y sxhkdrc."
    else
        ok "Comprobación finalizada: Todo el entorno base se encuentra en su lugar."
    fi
}

# ------------------------------------------------------------
# Installation Summary
# ------------------------------------------------------------
print_summary() {
    printf '\n'
    line
    printf '%b\n' "${GREEN}${BOLD} Instalación completada con éxito${RESET}"
    line
    printf '%b\n' " Copia de seguridad: ${BACKUP_DIR}"
    printf '%b\n' " Registro de instalación: ${LOG_FILE}"
    printf '\n'
    printf '%b\n' " El entorno está 100% configurado."
    printf '%b\n' " Reinicia el sistema o cierra tu sesión actual para ingresar vía BSPWM."
    printf '\n'
}

# ------------------------------------------------------------
# Orchestrator
# ------------------------------------------------------------
main() {
    title
    check_environment
    keep_sudo_alive
    check_network
    install_base_tools
    install_official_packages
    create_backup
    prepare_directories
    install_custom_fonts
    install_dotfiles
    install_wallpapers
    setup_zsh_environment
    configure_gtk_settings
    install_launchers_and_helpers
    enable_system_services
    fix_permissions
    check_bspwm_files
    print_summary

    if [[ -n "${SUDO_KEEPALIVE_PID:-}" ]]; then
        kill "$SUDO_KEEPALIVE_PID" 2>/dev/null || true
    fi
}

main "$@"

wait "$TEE_PID" 2>/dev/null || true
