#!/usr/bin/env bash
# ==============================================================================
# Script de Instalación y Despliegue de Dotfiles BSPWM
# Repositorio: https://github.com/TechOGR/bspwm_dotfiles_arch
# Compatibilidad: Arch Linux, CachyOS, EndeavourOS, Garuda, BlackArch, Archcraft
# ==============================================================================

set -eo pipefail

# ------------------------------------------------------------------------------
# 1. CONSTANTES, RUTAS Y PALETA DE COLORES ANSI
# ------------------------------------------------------------------------------
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_URL="https://github.com/TechOGR/bspwm_dotfiles_arch.git"
readonly TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
readonly BACKUP_DIR="${HOME}/.config/dotfiles_backup_${TIMESTAMP}"
readonly FONT_DIR="${HOME}/.local/share/fonts"

# Colores y Formatos ANSI
C_RESET=$'\e[0m'
C_BOLD=$'\e[1m'
C_RED=$'\e[31m'
C_GREEN=$'\e[32m'
C_YELLOW=$'\e[33m'
C_BLUE=$'\e[34m'
C_MAGENTA=$'\e[35m'
C_CYAN=$'\e[36m'
C_WHITE=$'\e[37m'

# Indicadores de estado visuales
msg_info()    { printf "${C_BOLD}${C_BLUE}[INFO]${C_RESET} %s\n" "$1"; }
msg_success() { printf "${C_BOLD}${C_GREEN}[SUCCESS]${C_RESET} %s\n" "$1"; }
msg_warn()    { printf "${C_BOLD}${C_YELLOW}[WARNING]${C_RESET} %s\n" "$1"; }
msg_error()   { printf "${C_BOLD}${C_RED}[ERROR]${C_RESET} %s\n" "$1" >&2; }
msg_step()    { printf "\n${C_BOLD}${C_MAGENTA}::${C_RESET} ${C_BOLD}%s${C_RESET}\n" "$1"; }

# ------------------------------------------------------------------------------
# 2. CONTROL DE LIMPIEZA Y MANEJO DE ERRORES (TRAPS)
# ------------------------------------------------------------------------------
cleanup() {
    local exit_code=$?
    # Restaurar cursor en terminal si fue ocultado
    printf "\e[?25h"
    # Finalizar el demonio keepalive de sudo si existe
    if [[ -n "${SUDO_PID:-}" ]] && kill -0 "$SUDO_PID" 2>/dev/null; then
        kill "$SUDO_PID" 2>/dev/null || true
    fi

    if [ "$exit_code" -ne 0 ]; then
        msg_error "La instalación finalizó de forma inesperada (Código de salida: $exit_code)."
    fi
}
trap cleanup EXIT INT TERM ERR

# ------------------------------------------------------------------------------
# 3. VERIFICACIONES DE ENTORNO Y PRIVILEGIOS
# ------------------------------------------------------------------------------
banner() {
    clear
    printf "${C_CYAN}${C_BOLD}"
    cat << "EOF"
  ____  ____  ______        ____  __  __   ____   ___ _____ _____ ___ _     _____ ____  
 | __ )/ ___||  _ \ \      / /  \/  | \ \ / / \ / _ \_   _|  ___|_ _| |   | ____/ ___| 
 |  _ \\___ \| |_) \ \ /\ / /| |\/| |  \ V / _ \ | | || | | |_   | || |   |  _| \___ \ 
 | |_) |___) |  __/ \ V  V / | |  | |   | / ___ \| |_| || | |  _|  | || |___| |___ ___) |
 |____/|____/|_|     \_/\_/  |_|  |_|   |/_/   \_\\___/ |_| |_|   |___|_____|_____|____/ 
EOF
    printf "${C_RESET}\n"
    printf " %b\n\n" "${C_WHITE}Instalador Automático para Arch Linux y Derivados${C_RESET}"
}

check_root() {
    if [ "$(id -u)" -eq 0 ]; then
        msg_error "Este script NO debe ejecutarse directamente como root."
        msg_info "Ejecútalo como tu usuario habitual. El script solicitará privilegios de sudo cuando sea necesario."
        exit 1
    fi
}

check_sudo() {
    msg_info "Validando privilegios administrativos de sudo..."
    if ! sudo -v; then
        msg_error "El usuario actual no posee permisos en /etc/sudoers."
        exit 1
    fi

    # Bucle keepalive en segundo plano para evitar timeout de sudo durante instalaciones extensas
    ( while true; do sudo -n true; sleep 45; kill -0 "$$" || exit; done ) 2>/dev/null &
    SUDO_PID=$!
}

check_arch() {
    msg_step "Verificando compatibilidad de la distribución..."
    if [ ! -f /etc/os-release ]; then
        msg_error "No se pudo detectar el sistema (/etc/os-release ausente)."
        exit 1
    fi

    # shellcheck disable=SC1091
    source /etc/os-release

    local is_arch_based=false
    if [[ "${ID:-}" == "arch" || "${ID_LIKE:-}" =~ "arch" || -f /etc/arch-release ]]; then
        is_arch_based=true
    fi

    if [ "$is_arch_based" = false ]; then
        msg_error "Distribución no compatible: ${NAME:-Desconocida}"
        msg_error "Este instalador solo admite Arch Linux y derivados (CachyOS, EndeavourOS, Garuda, BlackArch, etc.)."
        exit 1
    fi

    msg_success "Sistema detectado y validado: ${NAME:-Arch Linux}"
}

check_internet() {
    msg_info "Comprobando conectividad con la red..."
    if ! ping -c 1 -W 3 1.1.1.1 &>/dev/null && ! curl -s --head https://archlinux.org | head -n 1 &>/dev/null; then
        msg_error "No se detectó conexión a internet activa. Revisa tu interfaz de red."
        exit 1
    fi
    msg_success "Conectividad a internet confirmada."
}

# ------------------------------------------------------------------------------
# 4. PREPARACIÓN DE PACMAN Y GESTOR DE AUR (yay / paru)
# ------------------------------------------------------------------------------
optimize_pacman() {
    msg_step "Optimizando configuración de Pacman..."
    
    # Habilitar descargas paralelas y colores si están comentados
    if grep -q "^#ParallelDownloads" /etc/pacman.conf; then
        sudo sed -i 's/^#ParallelDownloads = [0-9]*/ParallelDownloads = 5/' /etc/pacman.conf
        msg_info "ParallelDownloads activado (5 hilos)."
    fi

    if grep -q "^#Color" /etc/pacman.conf; then
        sudo sed -i 's/^#Color/Color/' /etc/pacman.conf
        msg_info "Salida con colores activada en pacman.conf."
    fi

    # Resolver dependencias esenciales de compilación
    msg_info "Sincronizando repositorios y asegurando 'base-devel' y 'git'..."
    sudo pacman -Sy --needed --noconfirm base-devel git curl wget
}

install_aur_helper() {
    msg_step "Detectando e instalando AUR Helper..."

    if command -v yay &>/dev/null; then
        AUR_HELPER="yay"
        msg_success "AUR Helper encontrado: yay"
        return 0
    elif command -v paru &>/dev/null; then
        AUR_HELPER="paru"
        msg_success "AUR Helper encontrado: paru"
        return 0
    fi

    msg_warn "No se detectó ningún gestor de AUR. Procediendo a compilar e instalar 'yay-bin'..."
    local tmp_dir
    tmp_dir=$(mktemp -d)

    # yay-bin evita compilar todo el toolchain de Go en máquinas de bajos recursos
    if git clone --depth=1 https://aur.archlinux.org/yay-bin.git "$tmp_dir/yay-bin"; then
        (
            cd "$tmp_dir/yay-bin"
            makepkg -si --noconfirm
        )
    else
        msg_warn "Fallo clonando yay-bin, intentando con paquete fuente 'yay'..."
        git clone --depth=1 https://aur.archlinux.org/yay.git "$tmp_dir/yay"
        (
            cd "$tmp_dir/yay"
            makepkg -si --noconfirm
        )
    fi

    rm -rf "$tmp_dir"

    if command -v yay &>/dev/null; then
        AUR_HELPER="yay"
        msg_success "yay instalado exitosamente."
    else
        msg_error "No fue posible instalar el gestor de AUR automáticamente."
        exit 1
    fi
}

# ------------------------------------------------------------------------------
# 5. INSTALACIÓN DE DEPENDENCIAS Y PAQUETES ESENCIALES
# ------------------------------------------------------------------------------
install_packages() {
    msg_step "Instalando paquetes del entorno BSPWM y dependencias gráficas..."

    # Detección inteligente del navegador Brave (repo nativo de derivados o AUR)
    local brave_pkg="brave-bin"
    if pacman -Si brave &>/dev/null; then
        brave_pkg="brave"
    fi

    # Lista consolidada de paquetes
    local packages=(
        # Window Manager & Servidor X11
        "bspwm"
        "sxhkd"
        "xorg-server"
        "xorg-xinit"
        "xorg-xrandr"
        "xorg-xsetroot"
        "xorg-xprop"
        "xorg-xdpyinfo"
        "xdotool"
        "xclip"
        "xsel"

        # Compositor y Efectos Gráficos
        "picom"

        # Barra de estado, lanzador y notificaciones
        "polybar"
        "rofi"
        "dunst"
        "libnotify"

        # Lockscreen elegante con soporte Blur
        "betterlockscreen"
        "i3lock-color"
        "imagemagick"

        # Terminal, Navegador y Gestor de Archivos
        "alacritty"
        "$brave_pkg"
        "thunar"
        "thunar-archive-plugin"
        "file-roller"

        # Fuentes tipográficas e Iconos (Nerd Fonts)
        "ttf-jetbrains-mono-nerd"
        "ttf-font-awesome"
        "noto-fonts-emoji"
        "papirus-icon-theme"

        # Audio, Brillo y Multimedia
        "pipewire"
        "pipewire-pulse"
        "pipewire-alsa"
        "wireplumber"
        "pamixer"
        "pavucontrol"
        "brightnessctl"
        "playerctl"
        "viewnior"
        "mpv"

        # Fondo de pantalla y Personalización GTK
        "feh"
        "nitrogen"
        "lxappearance"
        "polkit-gnome"

        # Utilidades del sistema y Capturas
        "maim"
        "scrot"
        "fastfetch"
        "htop"
        "jq"
        "unzip"
        "xdg-user-dirs"
        "xdg-utils"
    )

    local to_install=()
    for pkg in "${packages[@]}"; do
        if ! pacman -Qi "$pkg" &>/dev/null && ! $AUR_HELPER -Qi "$pkg" &>/dev/null; then
            to_install+=("$pkg")
        fi
    done

    if [ ${#to_install[@]} -gt 0 ]; then
        msg_info "Paquetes pendientes por instalar: ${#to_install[@]}"
        $AUR_HELPER -S --needed --noconfirm "${to_install[@]}"
        msg_success "Todos los paquetes y dependencias se instalaron correctamente."
    else
        msg_success "Todos los paquetes del sistema ya se encuentran instalados."
    fi
}

# ------------------------------------------------------------------------------
# 6. GESTIÓN Y MEJORA DE CONFIGURACIONES (DOTFILES & BACKUP)
# ------------------------------------------------------------------------------
setup_configs() {
    msg_step "Desplegando archivos de configuración en ~/.config..."

    local source_dir="$SCRIPT_DIR"

    # Si se ejecutó directamente mediante curl o fuera de un clon git local
    if [ ! -d "$source_dir/.config" ]; then
        msg_warn "No se localizó la carpeta .config en el directorio actual."
        local clone_target="${HOME}/bspwm_dotfiles_arch"
        if [ ! -d "$clone_target" ]; then
            msg_info "Clonando repositorio oficial en $clone_target..."
            git clone --depth=1 "$REPO_URL" "$clone_target"
        fi
        source_dir="$clone_target"
    fi

    mkdir -p "${HOME}/.config"
    mkdir -p "$BACKUP_DIR"
    local backed_up=false

    # Modulos a desplegar
    local configs=("bspwm" "sxhkd" "polybar" "rofi" "dunst" "picom" "alacritty")

    for cfg in "${configs[@]}"; do
        local target_path="${HOME}/.config/${cfg}"
        local repo_cfg_path="${source_dir}/.config/${cfg}"

        # Realizar backup si ya existe una configuración previa
        if [ -d "$target_path" ] || [ -f "$target_path" ]; then
            mv "$target_path" "${BACKUP_DIR}/"
            backed_up=true
        fi

        # Copiar configuración del repositorio si existe
        if [ -e "$repo_cfg_path" ]; then
            cp -r "$repo_cfg_path" "${HOME}/.config/"
            msg_info "Configuración instalada: $cfg"
        fi
    done

    if [ "$backed_up" = true ]; then
        msg_success "Respaldos generados satisfactoriamente en: $BACKUP_DIR"
    else
        rm -rf "$BACKUP_DIR"
    fi

    # Aplicar permisos de ejecución estrictos a scripts de bspwm y polybar
    msg_info "Asegurando permisos de ejecución en scripts..."
    [[ -f "${HOME}/.config/bspwm/bspwmrc" ]] && chmod +x "${HOME}/.config/bspwm/bspwmrc"
    find "${HOME}/.config/bspwm" "${HOME}/.config/polybar" -type f -name "*.sh" -exec chmod +x {} + 2>/dev/null || true

    # Si el repo contiene fuentes en local o dentro del árbol
    if [ -d "${source_dir}/fonts" ]; then
        msg_info "Instalando fuentes adicionales del repositorio..."
        mkdir -p "$FONT_DIR"
        cp -rn "${source_dir}/fonts/"* "$FONT_DIR/" 2>/dev/null || true
    fi

    msg_info "Actualizando la caché del sistema de fuentes..."
    fc-cache -f -v &>/dev/null
    msg_success "Fuentes del sistema sincronizadas (evita iconos rotos en Polybar/Rofi)."
}

# ------------------------------------------------------------------------------
# 7. REFINAMIENTO DE PICOM Y AGENTE DE POLKIT
# ------------------------------------------------------------------------------
refine_desktop_configs() {
    msg_step "Comprobando optimizaciones para Picom y Polkit..."

    local picom_conf="${HOME}/.config/picom/picom.conf"
    if [ ! -f "$picom_conf" ]; then
        mkdir -p "${HOME}/.config/picom"
        msg_info "Generando picom.conf moderno optimizado (blur dual_kawase y animaciones)..."
        cat > "$picom_conf" << 'EOF'
backend = "glx";
glx-no-stencil = true;
glx-copy-from-front = false;
vsync = true;

# Sombras suaves
shadow = true;
shadow-radius = 12;
shadow-offset-x = -12;
shadow-offset-y = -12;
shadow-opacity = 0.5;
shadow-exclude = [
  "name = 'Notification'",
  "class_g = 'Polybar'",
  "class_g ?= 'Notify-osd'",
  "_GTK_FRAME_EXTENTS@:c"
];

# Fading suave
fading = true;
fade-in-step = 0.03;
fade-out-step = 0.03;

# Transparencias y Blur
inactive-opacity = 0.90;
active-opacity = 1.0;
frame-opacity = 1.0;

blur: {
  method = "dual_kawase";
  strength = 5;
  background = true;
  background-frame = false;
  background-fixed = false;
}
blur-background-exclude = [
  "window_type = 'dock'",
  "window_type = 'desktop'",
  "_GTK_FRAME_EXTENTS@:c"
];

# Bordes redondeados
corner-radius = 8;
rounded-corners-exclude = [
  "window_type = 'dock'",
  "window_type = 'desktop'"
];
EOF
    fi

    # Verificar que el agente de autenticación Polkit esté presente en bspwmrc
    local bspwmrc="${HOME}/.config/bspwm/bspwmrc"
    if [ -f "$bspwmrc" ]; then
        if ! grep -q "polkit-gnome-authentication-agent-1" "$bspwmrc"; then
            msg_info "Añadiendo agente Polkit a bspwmrc para diálogos de elevación de privilegios..."
            sed -i '/bspc monitor/i \
# Agente de autenticacion Polkit\n/usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1 &\n' "$bspwmrc"
        fi
    fi
}

# ------------------------------------------------------------------------------
# 8. CONFIGURACIÓN DEL LOCKSCREEN (BETTERLOCKSCREEN)
# ------------------------------------------------------------------------------
setup_lockscreen() {
    msg_step "Configurando el gestor de bloqueo de pantalla (Betterlockscreen)..."

    local wp_dir="${HOME}/.config/bspwm/wallpapers"
    local selected_wallpaper=""

    # 1. Buscar si ya existe un wallpaper en la configuración o el repositorio
    if [ -d "$wp_dir" ]; then
        selected_wallpaper=$(find "$wp_dir" -type f \( -name "*.jpg" -o -name "*.png" -o -name "*.webp" \) | head -n 1)
    fi

    # 2. Si no hay wallpaper, descargar uno minimalista de alta resolución
    if [ -z "$selected_wallpaper" ] || [ ! -f "$selected_wallpaper" ]; then
        mkdir -p "$wp_dir"
        selected_wallpaper="${wp_dir}/default_wallpaper.jpg"
        msg_info "Descargando fondo de pantalla estético inicial..."
        curl -sL "https://raw.githubusercontent.com/TechOGR/bspwm_dotfiles_arch/main/.config/bspwm/wallpapers/default.jpg" -o "$selected_wallpaper" 2>/dev/null || \
        curl -sL "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1920&q=80" -o "$selected_wallpaper"
    fi

    # 3. Precompilar el caché de desenfoque (Blur) para desbloqueo instantáneo
    if [ -f "$selected_wallpaper" ] && command -v betterlockscreen &>/dev/null; then
        msg_info "Generando caché de imágenes con desenfoque (efecto Blur)..."
        betterlockscreen -u "$selected_wallpaper" --blur 0.5 &>/dev/null || true
        msg_success "Caché de Betterlockscreen generado correctamente."
    else
        msg_warn "No se pudo compilar el caché de Betterlockscreen automáticamente."
    fi

    # 4. Asegurar atajo en sxhkdrc (super + x)
    local sxhkdrc="${HOME}/.config/sxhkd/sxhkdrc"
    if [ -f "$sxhkdrc" ] && ! grep -q "betterlockscreen" "$sxhkdrc"; then
        msg_info "Vinculando atajo [Super + x] a Betterlockscreen en sxhkdrc..."
        cat >> "$sxhkdrc" << 'EOF'

# Bloqueo de pantalla con efecto Blur
super + x
    betterlockscreen -l blur
EOF
    fi
}

# ------------------------------------------------------------------------------
# 9. ASIGNACIÓN DEL NAVEGADOR PREDETERMINADO (BRAVE)
# ------------------------------------------------------------------------------
setup_browser() {
    msg_step "Configurando Brave Browser como navegador predeterminado..."

    local desktop_entry="brave-browser.desktop"

    if command -v brave &>/dev/null || command -v brave-browser &>/dev/null; then
        # Establecer mediante xdg-settings
        xdg-settings set default-web-browser "$desktop_entry" 2>/dev/null || true

        # Asociar manejadores de protocolos MIME
        xdg-mime default "$desktop_entry" x-scheme-handler/http 2>/dev/null || true
        xdg-mime default "$desktop_entry" x-scheme-handler/https 2>/dev/null || true
        xdg-mime default "$desktop_entry" text/html 2>/dev/null || true
        xdg-mime default "$desktop_entry" application/xhtml+xml 2>/dev/null || true

        # Persistir variable BROWSER en perfiles de shell
        for profile in "${HOME}/.bashrc" "${HOME}/.zshrc" "${HOME}/.profile"; do
            if [ -f "$profile" ] && ! grep -q "BROWSER=brave" "$profile"; then
                printf "\nexport BROWSER=brave\n" >> "$profile"
            fi
        done

        msg_success "Brave Browser asignado como navegador predeterminado del sistema."
    else
        msg_warn "Brave Browser no se detectó en el PATH tras la instalación."
    fi
}

# ------------------------------------------------------------------------------
# 10. FINALIZACIÓN Y CONFIGURACIÓN DE INICIO (XINIT / BSPWM)
# ------------------------------------------------------------------------------
finalize_installation() {
    msg_step "Comprobando entorno de inicio del usuario..."

    # Actualizar directorios de usuario (Descargas, Documentos, etc.)
    xdg-user-dirs-update

    # Configuración de ~/.xinitrc para arranques vía 'startx'
    local xinitrc="${HOME}/.xinitrc"
    if [ ! -f "$xinitrc" ]; then
        msg_info "Creando archivo ~/.xinitrc con inicio de BSPWM..."
        cat > "$xinitrc" << 'EOF'
#!/bin/sh
userresources=$HOME/.Xresources
usermodmap=$HOME/.Xmodmap
sysresources=/etc/X11/xinit/.Xresources
sysmodmap=/etc/X11/xinit/.Xmodmap

# Mezclar recursos del sistema
if [ -f $sysresources ]; then
    xrdb -merge $sysresources
fi

if [ -f $sysmodmap ]; then
    xmodmap $sysmodmap
fi

if [ -f "$userresources" ]; then
    xrdb -merge "$userresources"
fi

if [ -f "$usermodmap" ]; then
    xmodmap "$usermodmap"
fi

if [ -d /etc/X11/xinit/xinitrc.d ] ; then
 for f in /etc/X11/xinit/xinitrc.d/?*.sh ; do
  [ -x "$f" ] && . "$f"
 done
 unset f
fi

exec bspwm
EOF
        chmod +x "$xinitrc"
    fi

    msg_success "Despliegue finalizado con éxito."
    printf "\n"
    printf "${C_BOLD}${C_GREEN}======================================================${C_RESET}\n"
    printf "${C_BOLD}${C_WHITE}    ¡Instalación de BSPWM completada con éxito!      ${C_RESET}\n"
    printf "${C_BOLD}${C_GREEN}======================================================${C_RESET}\n"
    printf " %b Atajo de bloqueo:   ${C_CYAN}Super + x${C_RESET} (Betterlockscreen Blur)\n"
    printf " %b Navegador web:      ${C_CYAN}Brave${C_RESET}\n"
    printf " %b Terminal:           ${C_CYAN}Alacritty${C_RESET}\n"
    printf " %b Lanzador de apps:   ${C_CYAN}Super + d${C_RESET} (Rofi)\n"
    printf " %b Respaldos:          ${C_YELLOW}%s${C_RESET}\n" "$BACKUP_DIR"
    printf "\n${C_BOLD}Se recomienda reiniciar el sistema o cerrar sesión para aplicar cambios.${C_RESET}\n\n"
}

# ------------------------------------------------------------------------------
# EJECUCIÓN PRINCIPAL
# ------------------------------------------------------------------------------
main() {
    banner
    check_root
    check_sudo
    check_arch
    check_internet
    optimize_pacman
    install_aur_helper
    install_packages
    setup_configs
    refine_desktop_configs
    setup_lockscreen
    setup_browser
    finalize_installation
}

main "$@"
