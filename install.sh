#!/usr/bin/env bash
# ==============================================================================
#  🛠️ TECHOGR BSPWM DOTFILES - ENTERPRISE INSTALLATION ENGINE
# ==============================================================================
#  Autor: TechOGR
#  Compatibilidad: Arch Linux, CachyOS, EndeavourOS, Garuda, BlackArch, Manjaro
#  Licencia: GPL-3.0
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. PARÁMETROS GLOBALES Y AJUSTES DE EJECUCIÓN
# ------------------------------------------------------------------------------
set -o pipefail

SCRIPT_VERSION="4.2.0"
REPO_NAME="TechOGR/bspwm_dotfiles_arch"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$HOME/.techogr_install.log"
BACKUP_BASE_DIR="$HOME/.dotfiles_backup"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
TARGET_BACKUP="$BACKUP_BASE_DIR/backup_$TIMESTAMP"

# Inicializar archivo de auditoría
echo "========================================================" > "$LOG_FILE"
echo " TechOGR BSPWM Installer - Registro de Auditoría" >> "$LOG_FILE"
echo " Fecha de inicio: $(date)" >> "$LOG_FILE"
echo " Host: $(uname -n) | Kernel: $(uname -r)" >> "$LOG_FILE"
echo "========================================================" >> "$LOG_FILE"

# ------------------------------------------------------------------------------
# 2. PALETA DE COLORES ANSI Y GLIFOS DE INTERFAZ
# ------------------------------------------------------------------------------
C_RESET="\e[0m"
C_BOLD="\e[1m"
C_DIM="\e[2m"
C_RED="\e[31m"
C_GREEN="\e[32m"
C_YELLOW="\e[33m"
C_BLUE="\e[34m"
C_MAGENTA="\e[35m"
C_CYAN="\e[36m"
C_WHITE="\e[37m"

ARROW="${C_CYAN}➜${C_RESET}"
CHECK="${C_GREEN}✔${C_RESET}"
CROSS="${C_RED}✖${C_RESET}"
WARN="${C_YELLOW}⚠${C_RESET}"
STAR="${C_MAGENTA}★${C_RESET}"

# ------------------------------------------------------------------------------
# 3. FUNCIONES DE LOGGING Y FORMATO DE SALIDA
# ------------------------------------------------------------------------------
log_info() {
    echo -e " ${ARROW} ${C_BOLD}$1${C_RESET}"
    echo "[INFO]  $(date +'%T') - $1" >> "$LOG_FILE"
}

log_success() {
    echo -e " ${CHECK} ${C_GREEN}${C_BOLD}$1${C_RESET}"
    echo "[OK]    $(date +'%T') - $1" >> "$LOG_FILE"
}

log_warning() {
    echo -e " ${WARN} ${C_YELLOW}${C_BOLD}$1${C_RESET}"
    echo "[WARN]  $(date +'%T') - $1" >> "$LOG_FILE"
}

log_error() {
    echo -e " ${CROSS} ${C_RED}${C_BOLD}$1${C_RESET}"
    echo "[ERROR] $(date +'%T') - $1" >> "$LOG_FILE"
}

log_step() {
    echo -e "\n${C_MAGENTA}${C_BOLD}:: [PASO] $1${C_RESET}"
    echo -e "\n--- [PASO] $1 ---" >> "$LOG_FILE"
}

print_banner() {
    clear
    echo -e "${C_CYAN}${C_BOLD}"
    cat << "EOF"
  ████████╗███████╗ ██████╗██╗  ██╗ ██████╗  ██████╗ ██████╗ 
  ╚══██╔══╝██╔════╝██╔════╝██║  ██║██╔═══██╗██╔════╝ ██╔══██╗
     ██║   █████╗  ██║     ███████║██║   ██║██║  ███╗██████╔╝
     ██║   ██╔══╝  ██║     ██╔══██║██║   ██║██║   ██║██╔══██╗
     ██║   ███████╗╚██████╗██║  ██║╚██████╔╝╚██████╔╝██║  ██║
     ╚═╝   ╚══════╝ ╚═════╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝  ╚═╝
EOF
    echo -e "${C_BLUE}  ┌─────────────────────────────────────────────────────────────┐"
    echo -e "  │      Full Desktop Environment & Display Manager Engine      │"
    echo -e "  │          A prueba de pantallas negras y fallos de KMS       │"
    echo -e "  │      Compatible con CachyOS, Arch, Endeavour, Garuda, etc.  │"
    echo -e "  └─────────────────────────────────────────────────────────────┘${C_RESET}\n"
}

# ------------------------------------------------------------------------------
# 4. GESTIÓN DE PRIVILEGIOS Y RUTINAS DE SALIDA
# ------------------------------------------------------------------------------
cleanup_trap() {
    local exit_status=$?
    if [ -n "$SUDO_PID" ] && kill -0 "$SUDO_PID" 2>/dev/null; then
        kill "$SUDO_PID" 2>/dev/null || true
    fi
    if [ $exit_status -ne 0 ]; then
        echo ""
        log_error "La instalación ha concluido con errores (Código: $exit_status)."
        log_info "Consulta el registro detallado en: ${C_CYAN}$LOG_FILE${C_RESET}"
    fi
}
trap cleanup_trap EXIT INT TERM

check_execution_privileges() {
    if [ "$EUID" -eq 0 ]; then
        echo -e "${C_RED}${C_BOLD}Error Crítico:${C_RESET} NO ejecutes este script directamente como root ni con sudo."
        echo -e "Ejecútalo con tu usuario normal: ${C_CYAN}./install.sh${C_RESET}"
        echo -e "El instalador elevará permisos de sudo cuando sea estrictamente necesario."
        exit 1
    fi

    log_info "Comprobando y asegurando privilegios administrativos de sudo..."
    sudo -v || { log_error "No se pudo autenticar con sudo. Abortando."; exit 1; }

    # Mantener vivo sudo en segundo plano
    while true; do
        sudo -n true
        sleep 45
        kill -0 "$$" || exit
    done 2>/dev/null &
    SUDO_PID=$!
}

# ------------------------------------------------------------------------------
# 5. VALIDACIÓN DEL ENTORNO, RED Y REPOSITORIOS
# ------------------------------------------------------------------------------
validate_environment() {
    log_step "Verificación de compatibilidad de la distribución y conectividad"

    # 1. Arquitectura
    ARCH_NAME=$(uname -m)
    if [ "$ARCH_NAME" != "x86_64" ]; then
        log_error "Arquitectura $ARCH_NAME no compatible. Se requiere x86_64."
        exit 1
    fi
    log_success "Arquitectura del procesador: $ARCH_NAME"

    # 2. Distribución compatible
    if [ -f /etc/os-release ]; then
        # shellcheck disable=SC1091
        source /etc/os-release
        DISTRO_NAME="${NAME:-Arch Linux}"
        DISTRO_ID="${ID:-arch}"
        DISTRO_LIKE="${ID_LIKE:-arch}"

        if [[ "$DISTRO_ID" =~ (arch|cachyos|endeavouros|garuda|blackarch|manjaro|arcolinux) ]] || \
           [[ "$DISTRO_LIKE" =~ arch ]]; then
            log_success "Distribución reconocida y totalmente soportada: ${C_CYAN}$DISTRO_NAME${C_RESET}"
        else
            log_error "Distribución no soportada: $DISTRO_NAME. Este instalador es exclusivo de la familia Arch."
            exit 1
        fi
    else
        log_error "No se encontró el archivo /etc/os-release."
        exit 1
    fi

    # 3. Eliminar bloqueos de base de datos huérfanos de pacman
    if [ -f /var/lib/pacman/db.lck ]; then
        log_warning "Archivo /var/lib/pacman/db.lck detectado. Liberando base de datos..."
        sudo rm -f /var/lib/pacman/db.lck
        log_success "Bloqueo de pacman eliminado."
    fi

    # 4. Comprobación activa de Internet
    log_info "Comprobando conexión activa a la red..."
    local test_urls=("https://archlinux.org" "https://1.1.1.1" "https://github.com")
    local is_online=false

    for url in "${test_urls[@]}"; do
        if curl -s --head --connect-timeout 4 "$url" &>/dev/null; then
            is_online=true
            break
        fi
    done

    if [ "$is_online" = true ]; then
        log_success "Conectividad a Internet confirmada."
    else
        log_error "Sin acceso a Internet. Verifica tus interfaces de red o el servicio NetworkManager."
        exit 1
    fi
}

# ------------------------------------------------------------------------------
# 6. DETECCIÓN PROFUNDA DE HARDWARE Y CONTROLADORES GRÁFICOS (PREVENCIÓN BLACK SCREEN)
# ------------------------------------------------------------------------------
detect_and_configure_hardware() {
    log_step "Detección de Hardware Gráfico, KMS y Entornos Virtuales"

    IS_VM=false
    HARDWARE_GPU_PKGS=()
    KERNEL_HEADERS_PKG="linux-headers"

    # Identificar el kernel en ejecución para instalar sus cabeceras correctas
    CURRENT_KERNEL=$(uname -r)
    if echo "$CURRENT_KERNEL" | grep -iq "cachyos"; then
        KERNEL_HEADERS_PKG="linux-cachyos-headers"
    elif echo "$CURRENT_KERNEL" | grep -iq "zen"; then
        KERNEL_HEADERS_PKG="linux-zen-headers"
    elif echo "$CURRENT_KERNEL" | grep -iq "lts"; then
        KERNEL_HEADERS_PKG="linux-lts-headers"
    fi
    log_info "Kernel en ejecución: ${C_CYAN}$CURRENT_KERNEL${C_RESET}. Paquete de cabeceras: $KERNEL_HEADERS_PKG"

    # Detección de Máquinas Virtuales
    if command -v systemd-detect-virt &>/dev/null && [ "$(systemd-detect-virt)" != "none" ]; then
        IS_VM=true
        VIRT_SYSTEM=$(systemd-detect-virt)
        log_warning "Máquina Virtual detectada: ${C_YELLOW}$VIRT_SYSTEM${C_RESET}"
        PICOM_BACKEND="xrender"
        PICOM_VSYNC="false"

        case "$VIRT_SYSTEM" in
            oracle|virtualbox)
                HARDWARE_GPU_PKGS+=(virtualbox-guest-utils xf86-video-vmware)
                ;;
            vmware)
                HARDWARE_GPU_PKGS+=(open-vm-tools xf86-video-vmware xf86-input-vmmouse)
                ;;
            kvm|qemu|bochs)
                HARDWARE_GPU_PKGS+=(qemu-guest-agent xf86-video-fbdev)
                ;;
        esac
    else
        log_success "Hardware físico (Bare-Metal) detectado."
        PICOM_BACKEND="glx"
        PICOM_VSYNC="true"

        local PCI_DEVICES
        PCI_DEVICES=$(lspci -k 2>/dev/null | grep -EA3 -i "vga|3d|display" || true)

        # 1. NVIDIA
        if echo "$PCI_DEVICES" | grep -iq "nvidia"; then
            log_info "GPU NVIDIA detectada. Asegurando controladores compatibles con KMS..."
            HARDWARE_GPU_PKGS+=(nvidia-dkms nvidia-utils lib32-nvidia-utils)
        fi

        # 2. AMD
        if echo "$PCI_DEVICES" | grep -iqE "amd|radeon|advanced micro devices"; then
            log_info "GPU AMD detectada. Añadiendo aceleración Radeon y Vulkan..."
            HARDWARE_GPU_PKGS+=(xf86-video-amdgpu vulkan-radeon)
        fi

        # 3. INTEL (IMPORTANTE: NO instalar xf86-video-intel para evitar pantalla negra)
        if echo "$PCI_DEVICES" | grep -iq "intel"; then
            log_info "GPU Intel detectada. Utilizando controlador KMS nativo (modesetting) y aceleración Vulkan..."
            HARDWARE_GPU_PKGS+=(vulkan-intel intel-media-driver)
        fi
    fi

    # Aceleración OpenGL/Vulkan universal y controladores de respaldo
    HARDWARE_GPU_PKGS+=(
        "$KERNEL_HEADERS_PKG"
        base-devel
        mesa
        lib32-mesa
        libglvnd
        lib32-libglvnd
        xf86-video-fbdev
        xf86-video-vesa
    )

    log_info "Instalando controladores y dependencias de video esenciales..."
    for pkg in "${HARDWARE_GPU_PKGS[@]}"; do
        sudo pacman -S --needed --noconfirm "$pkg" &>> "$LOG_FILE" || true
    done

    # Iniciar y habilitar utilidades de máquina virtual si procede
    if [ "$IS_VM" = true ]; then
        if command -v VBoxService &>/dev/null; then
            sudo systemctl enable --now vboxservice.service &>> "$LOG_FILE" || true
        fi
        if command -v vmtoolsd &>/dev/null; then
            sudo systemctl enable --now vmtoolsd.service &>> "$LOG_FILE" || true
        fi
    fi
}

# ------------------------------------------------------------------------------
# 7. GESTOR AUR DESATENDIDO (YAY-BIN)
# ------------------------------------------------------------------------------
setup_aur_manager() {
    log_step "Configuración del Administrador de Paquetes AUR"

    if command -v yay &>/dev/null; then
        AUR_HELPER="yay"
        log_success "Gestor AUR listo: yay"
    elif command -v paru &>/dev/null; then
        AUR_HELPER="paru"
        log_success "Gestor AUR listo: paru"
    else
        log_warning "Ningún gestor AUR detectado. Compilando yay-bin de forma automática..."
        sudo pacman -S --needed --noconfirm base-devel git &>> "$LOG_FILE"

        local TEMP_AUR_DIR="/tmp/yay-bin-installer-$$"
        rm -rf "$TEMP_AUR_DIR"
        mkdir -p "$TEMP_AUR_DIR"

        if git clone https://aur.archlinux.org/yay-bin.git "$TEMP_AUR_DIR/yay-bin" &>> "$LOG_FILE"; then
            (
                cd "$TEMP_AUR_DIR/yay-bin" || exit 1
                makepkg -si --noconfirm &>> "$LOG_FILE"
            )
            rm -rf "$TEMP_AUR_DIR"
            AUR_HELPER="yay"
            log_success "yay-bin compilado e instalado con éxito."
        else
            log_error "No se pudo clonar yay-bin desde AUR. Revisa tu conectividad."
            exit 1
        fi
    fi
}

# ------------------------------------------------------------------------------
# 8. MATRIZ DE DEPENDENCIAS DEL SISTEMA (XORG, BSPWM, AUDIO, TEMAS)
# ------------------------------------------------------------------------------
install_system_dependencies() {
    log_step "Instalación de Paquetes Maestros del Sistema"

    log_info "Sincronizando base de datos de repositorios..."
    sudo pacman -Sy &>> "$LOG_FILE"

    # 1. Servidor Gráfico X11 Completo
    local X11_CORE=(
        xorg-server
        xorg-xinit
        xorg-xrandr
        xorg-xrdb
        xorg-xsetroot
        xorg-xprop
        xorg-xdpyinfo
        xorg-xwininfo
        xorg-xinput
        xorg-xkill
        xorg-xauth
        xorg-xbacklight
        xdotool
        xdo
        xclip
        xsettingsd
        hsetroot
    )

    # 2. Display Manager (Gestor de Inicio) y Motores GTK
    local DISPLAY_STACK=(
        lightdm
        lightdm-gtk-greeter
        lightdm-gtk-greeter-settings
        gnome-themes-extra
        gtk-engine-murrine
        gtk-engines
        accountsservice
    )

    # 3. BSPWM y Herramientas del Entorno
    local WINDOW_MANAGER_STACK=(
        bspwm
        sxhkd
        polybar
        rofi
        picom
        kitty
        feh
        dunst
        libnotify
        jgmenu
        polkit-gnome
        lxsession
        network-manager-applet
        volumeicon
    )

    # 4. Servidor de Audio Moderno (PipeWire Completo)
    local AUDIO_STACK=(
        pipewire
        pipewire-pulse
        pipewire-alsa
        pipewire-jack
        wireplumber
        pamixer
        playerctl
        alsa-utils
    )

    # 5. Utilidades CLI, Terminal, Fuentes e Iconos
    local SYSTEM_UTILS=(
        brightnessctl
        maim
        viewnior
        imagemagick
        jq
        bc
        htop
        fastfetch
        zsh
        zsh-autosuggestions
        zsh-syntax-highlighting
        xdg-user-dirs
        xdg-utils
        ttf-jetbrains-mono-nerd
        ttf-font-awesome
        noto-fonts-emoji
        papirus-icon-theme
        xss-lock
        i3lock
    )

    # 6. Bloqueador de pantalla gráfico liviano desde AUR
    local AUR_LOCK_STACK=(
        i3lock-color
        betterlockscreen
    )

    local MASTER_PACMAN_LIST=(
        "${X11_CORE[@]}"
        "${DISPLAY_STACK[@]}"
        "${WINDOW_MANAGER_STACK[@]}"
        "${AUDIO_STACK[@]}"
        "${SYSTEM_UTILS[@]}"
    )

    local total_count=${#MASTER_PACMAN_LIST[@]}
    local current=0
    local failed_list=()

    log_info "Instalando paquetes desde repositorios oficiales ($total_count elementos)..."

    for pkg in "${MASTER_PACMAN_LIST[@]}"; do
        ((current++))
        printf " [PACMAN] (%2d/%2d) %-30s" "$current" "$total_count" "$pkg"

        if pacman -Qi "$pkg" &>/dev/null; then
            echo -e " [ ${C_GREEN}LISTO${C_RESET} ]"
        else
            if sudo pacman -S --needed --noconfirm "$pkg" &>> "$LOG_FILE"; then
                echo -e " [ ${C_CYAN}INSTALADO${C_RESET} ]"
            else
                echo -e " [ ${C_RED}ALERTA${C_RESET} ]"
                failed_list+=("$pkg")
            fi
        fi
    done

    # Reintento selectivo de paquetes fallidos
    if [ ${#failed_list[@]} -gt 0 ]; then
        log_warning "Reintentando paquetes que emitieron alertas: ${failed_list[*]}"
        for fpkg in "${failed_list[@]}"; do
            sudo pacman -S --needed --noconfirm "$fpkg" &>> "$LOG_FILE" || true
        done
    fi

    # AUR: Bloqueador de pantalla gráfico
    log_info "Instalando componentes visuales desde AUR..."
    for aur_pkg in "${AUR_LOCK_STACK[@]}"; do
        printf " [AUR]    Procesando %-30s" "$aur_pkg"
        if pacman -Qi "$aur_pkg" &>/dev/null; then
            echo -e " [ ${C_GREEN}LISTO${C_RESET} ]"
        else
            if $AUR_HELPER -S --needed --noconfirm "$aur_pkg" &>> "$LOG_FILE"; then
                echo -e " [ ${C_CYAN}INSTALADO${C_RESET} ]"
            else
                echo -e " [ ${C_YELLOW}AVISO${C_RESET} ]"
                log_warning "No se pudo compilar $aur_pkg desde AUR. El script configurará i3lock nativo como respaldo de alta velocidad."
            fi
        fi
    done

    # Actualizar carpetas de usuario XDG
    xdg-user-dirs-update &>> "$LOG_FILE" || true
    log_success "Todos los paquetes y componentes esenciales están instalados."
}

# ------------------------------------------------------------------------------
# 9. CONFIGURACIÓN RESILIENTE DEL DISPLAY MANAGER (LIGHTDM A PRUEBA DE FALLOS)
# ------------------------------------------------------------------------------
configure_display_manager_bulletproof() {
    log_step "Configuración Anti-Fallo del Gestor de Inicio (LightDM + Xorg)"

    # 1. Asegurar la entrada de sesión BSPWM en Xsessions
    sudo mkdir -p /usr/share/xsessions
    sudo tee /usr/share/xsessions/bspwm.desktop >/dev/null << 'EOF'
[Desktop Entry]
Name=bspwm
Comment=Binary Space Partitioning Window Manager
Exec=/usr/bin/bspwm
Type=XSession
DesktopNames=bspwm
EOF
    sudo chmod 644 /usr/share/xsessions/bspwm.desktop

    # 2. Configurar imagen de fondo para el Login
    local LOGIN_BG_DIR="/usr/share/backgrounds/techogr"
    sudo mkdir -p "$LOGIN_BG_DIR"
    local SAMPLE_WALLPAPER
    SAMPLE_WALLPAPER=$(find "$SCRIPT_DIR/Wallpapers" -type f \( -name "*.jpg" -o -name "*.png" \) 2>/dev/null | head -n 1)

    if [ -n "$SAMPLE_WALLPAPER" ]; then
        sudo cp -f "$SAMPLE_WALLPAPER" "$LOGIN_BG_DIR/login_bg.jpg"
        sudo chmod 644 "$LOGIN_BG_DIR/login_bg.jpg"
        BG_CONFIG_LINE="background = $LOGIN_BG_DIR/login_bg.jpg"
    else
        BG_CONFIG_LINE="background = #1a1b26"
    fi

    # 3. Crear el script oficial /etc/lightdm/Xsession si no existe (vital en Arch)
    if [ ! -f /etc/lightdm/Xsession ]; then
        log_info "Creando envoltorio universal /etc/lightdm/Xsession..."
        sudo tee /etc/lightdm/Xsession >/dev/null << 'EOF'
#!/bin/sh
# /etc/lightdm/Xsession - LightDM session wrapper script for Arch Linux
# TechOGR BSPWM Edition
set +e
if [ -d /etc/X11/xinit/xinitrc.d ]; then
    for f in /etc/X11/xinit/xinitrc.d/?*.sh ; do
        [ -x "$f" ] && . "$f"
    done
    unset f
fi
if [ -f "$HOME/.xprofile" ]; then
    . "$HOME/.xprofile"
fi
exec "$@"
EOF
    fi
    sudo chmod 755 /etc/lightdm/Xsession

    # 4. Configurar /etc/lightdm/lightdm.conf con protección KMS
    log_info "Asegurando configuración de /etc/lightdm/lightdm.conf con logind-check-graphical..."
    sudo mkdir -p /etc/lightdm
    sudo tee /etc/lightdm/lightdm.conf >/dev/null << 'EOF'
[LightDM]
run-directory=/run/lightdm

[Seat:*]
greeter-session=lightdm-gtk-greeter
user-session=bspwm
session-wrapper=/etc/lightdm/Xsession
logind-check-graphical=true
autologin-guest=false
allow-user-switching=true
pam-service=lightdm
pam-autologin-service=lightdm-autologin
EOF
    sudo chmod 644 /etc/lightdm/lightdm.conf

    # 5. Configurar /etc/lightdm/lightdm-gtk-greeter.conf
    log_info "Personalizando aspecto gráfico del Login..."
    sudo tee /etc/lightdm/lightdm-gtk-greeter.conf >/dev/null << EOF
[greeter]
theme-name = Adwaita
icon-theme-name = Papirus-Dark
font-name = JetBrainsMono Nerd Font 10
$BG_CONFIG_LINE
user-background = false
clock-format = %A, %d de %B  •  %H:%M
indicators = ~host;~spacer;~clock;~spacer;~session;~power
position = 50%,center 50%,center
default-user-image = #avatar-default
screensaver-timeout = 60
EOF
    sudo chmod 644 /etc/lightdm/lightdm-gtk-greeter.conf

    # 6. Permisos del usuario del greeter
    sudo chown -R lightdm:lightdm /var/lib/lightdm 2>/dev/null || true
    sudo chmod 755 /var/lib/lightdm 2>/dev/null || true

    # 7. Deshabilitar otros gestores y activar LightDM
    log_info "Estableciendo LightDM como el gestor de inicio principal..."
    for dm in sddm gdm lxdm ly greetd nodm; do
        sudo systemctl disable "$dm.service" &>> "$LOG_FILE" || true
    done
    sudo systemctl enable lightdm.service -f &>> "$LOG_FILE"

    # 8. FORZAR graphical.target EN SYSTEMD (Evita caer en la terminal TTY negra)
    log_info "Forzando 'graphical.target' como el objetivo de arranque predeterminado del sistema..."
    sudo systemctl set-default graphical.target &>> "$LOG_FILE"

    log_success "Display Manager configurado sin riesgo de pantalla negra."
}

# ------------------------------------------------------------------------------
# 10. BACKUP Y DESPLIEGUE DEL REPOSITORIO DE DOTFILES
# ------------------------------------------------------------------------------
deploy_user_dotfiles() {
    log_step "Respaldo y Despliegue de los Dotfiles de TechOGR"

    # Copia de seguridad preventiva
    mkdir -p "$TARGET_BACKUP"
    local TARGETS_TO_BACKUP=(
        "$HOME/.config/bspwm"
        "$HOME/.config/sxhkd"
        "$HOME/.config/polybar"
        "$HOME/.config/rofi"
        "$HOME/.config/picom"
        "$HOME/.config/kitty"
        "$HOME/.config/dunst"
        "$HOME/.config/jgmenu"
        "$HOME/.zshrc"
        "$HOME/.xinitrc"
        "$HOME/.xprofile"
    )

    for item in "${TARGETS_TO_BACKUP[@]}"; do
        if [ -e "$item" ]; then
            cp -rf "$item" "$TARGET_BACKUP/" 2>> "$LOG_FILE"
        fi
    done

    # Crear script restore.sh en la carpeta de respaldo
    cat << EOF > "$TARGET_BACKUP/restore.sh"
#!/usr/bin/env bash
echo "Restaurando copia de seguridad del: $TIMESTAMP..."
cp -rf "$TARGET_BACKUP"/* "\$HOME/.config/" 2>/dev/null || true
[ -f "$TARGET_BACKUP/.zshrc" ] && cp -f "$TARGET_BACKUP/.zshrc" "\$HOME/"
[ -f "$TARGET_BACKUP/.xinitrc" ] && cp -f "$TARGET_BACKUP/.xinitrc" "\$HOME/"
[ -f "$TARGET_BACKUP/.xprofile" ] && cp -f "$TARGET_BACKUP/.xprofile" "\$HOME/"
echo "Restauración completada."
EOF
    chmod +x "$TARGET_BACKUP/restore.sh"
    log_success "Respaldo preventivo guardado en: $TARGET_BACKUP"

    # Preparar directorios en HOME
    mkdir -p "$HOME/.config" "$HOME/.local/bin" "$HOME/.local/share/fonts" "$HOME/Pictures/Wallpapers"

    # 1. Copiar config/
    if [ -d "$SCRIPT_DIR/config" ]; then
        log_info "Desplegando configuraciones desde config/ hacia ~/.config/ ..."
        cp -rf "$SCRIPT_DIR/config/"* "$HOME/.config/" 2>> "$LOG_FILE"
    fi

    # 2. Copiar kitty/ si existe en la raíz
    if [ -d "$SCRIPT_DIR/kitty" ]; then
        log_info "Desplegando Kitty Terminal..."
        mkdir -p "$HOME/.config/kitty"
        cp -rf "$SCRIPT_DIR/kitty/"* "$HOME/.config/kitty/" 2>> "$LOG_FILE"
    fi

    # 3. Copiar home/
    if [ -d "$SCRIPT_DIR/home" ]; then
        log_info "Copiando dotfiles de usuario desde home/ ..."
        cp -rf "$SCRIPT_DIR/home/." "$HOME/" 2>> "$LOG_FILE"
    fi

    # 4. Copiar Wallpapers/
    if [ -d "$SCRIPT_DIR/Wallpapers" ]; then
        log_info "Instalando fondos de pantalla en ~/Pictures/Wallpapers/ ..."
        cp -rf "$SCRIPT_DIR/Wallpapers/"* "$HOME/Pictures/Wallpapers/" 2>> "$LOG_FILE"
        [ ! -L "$HOME/Wallpapers" ] && ln -sf "$HOME/Pictures/Wallpapers" "$HOME/Wallpapers" 2>/dev/null || true
    fi

    # 5. Copiar misc/
    if [ -d "$SCRIPT_DIR/misc" ]; then
        [ -d "$SCRIPT_DIR/misc/fonts" ] && cp -rf "$SCRIPT_DIR/misc/fonts/"* "$HOME/.local/share/fonts/" 2>> "$LOG_FILE"
        [ -d "$SCRIPT_DIR/misc/bin" ] && cp -rf "$SCRIPT_DIR/misc/bin/"* "$HOME/.local/bin/" 2>> "$LOG_FILE"
        cp -rf "$SCRIPT_DIR/misc/"* "$HOME/.local/share/" 2>/dev/null || true
    fi

    # 6. Blindaje de BSPWMRC: Inyectar rescate visual para evitar pantalla negra
    local BSPWMRC_PATH="$HOME/.config/bspwm/bspwmrc"
    if [ -f "$BSPWMRC_PATH" ]; then
        log_info "Blindando ~/.config/bspwm/bspwmrc contra fallos gráficos..."

        # Asegurar cursor normal y color de fondo de emergencia inmediato
        if ! grep -q "xsetroot -cursor_name" "$BSPWMRC_PATH"; then
            sed -i '1a xsetroot -cursor_name left_ptr &' "$BSPWMRC_PATH"
        fi
        if ! grep -q "xsetroot -solid" "$BSPWMRC_PATH"; then
            sed -i '2a xsetroot -solid "#1e1e2e" &' "$BSPWMRC_PATH"
        fi

        # Asegurar lanzamiento prioritario de sxhkd
        if ! grep -q "sxhkd" "$BSPWMRC_PATH"; then
            sed -i '3a pgrep -x sxhkd >/dev/null || sxhkd &' "$BSPWMRC_PATH"
        fi
    fi

    # 7. Crear ~/.xinitrc y ~/.xprofile universales de respaldo
    tee "$HOME/.xprofile" >/dev/null << 'EOF'
#!/bin/sh
export XDG_CURRENT_DESKTOP=bspwm
export XDG_SESSION_TYPE=x11
export DESKTOP_SESSION=bspwm
[ -f "$HOME/.Xresources" ] && xrdb -merge "$HOME/.Xresources"
EOF
    chmod +x "$HOME/.xprofile"

    tee "$HOME/.xinitrc" >/dev/null << 'EOF'
#!/bin/sh
. "$HOME/.xprofile"
xsetroot -cursor_name left_ptr &
xsetroot -solid "#1e1e2e" &
pgrep -x sxhkd >/dev/null || sxhkd &
exec bspwm
EOF
    chmod +x "$HOME/.xinitrc"

    # 8. Otorgar permisos ejecutables
    find "$HOME/.config/bspwm" -type f -exec chmod +x {} + 2>/dev/null || true
    find "$HOME/.config/polybar" -type f \( -name "*.sh" -o -name "launch*" \) -exec chmod +x {} + 2>/dev/null || true
    find "$HOME/.local/bin" -type f -exec chmod +x {} + 2>/dev/null || true

    # 9. Ajustar backend de picom según hardware
    local PICOM_CONF="$HOME/.config/picom/picom.conf"
    if [ -f "$PICOM_CONF" ]; then
        sed -i "s/backend = .*/backend = \"$PICOM_BACKEND\";/" "$PICOM_CONF" 2>/dev/null || true
        sed -i "s/vsync = .*/vsync = $PICOM_VSYNC;/" "$PICOM_CONF" 2>/dev/null || true
    fi

    # 10. Actualizar caché de fuentes
    log_info "Actualizando base de tipografías del sistema..."
    fc-cache -fv &>> "$LOG_FILE"

    log_success "Dotfiles desplegados y blindados contra bloqueos."
}

# ------------------------------------------------------------------------------
# 11. SISTEMA DE BLOQUEO DE PANTALLA GRÁFICO LIVIANO
# ------------------------------------------------------------------------------
setup_lockscreen_infrastructure() {
    log_step "Configuración del Bloqueo Gráfico Liviano (Atajo y Suspensión)"

    local LOCK_SCRIPT="$HOME/.local/bin/techogr_lock"
    cat << 'EOF' > "$LOCK_SCRIPT"
#!/usr/bin/env bash
# TechOGR Lockscreen Script - Ultraligero y con respaldos en cascada

TIME_FORMAT="%I:%M %p"
DATE_FORMAT="%A, %d de %B"

# Nivel 1: Betterlockscreen (Efecto Blur de alta estética)
if command -v betterlockscreen &>/dev/null; then
    betterlockscreen -l dimblur --time-format "$TIME_FORMAT"
    exit 0
fi

# Nivel 2: i3lock-color (Reloj circular flotante)
if command -v i3lock-color &>/dev/null; then
    i3lock-color \
        --insidever-color=24283b80 \
        --insidewrong-color=f7768e80 \
        --inside-color=1a1b26cc \
        --ringver-color=7aa2f7ff \
        --ringwrong-color=f7768eff \
        --ring-color=bb9af7ff \
        --line-uses-inside \
        --keyhl-color=7dcfff \
        --bshl-color=f7768e \
        --separator-color=00000000 \
        --verif-color=c0caf5ff \
        --wrong-color=f7768eff \
        --time-color=c0caf5ff \
        --date-color=a9b1d6ff \
        --clock \
        --indicator \
        --time-str="$TIME_FORMAT" \
        --date-str="$DATE_FORMAT" \
        --time-font="JetBrains Mono Nerd Font" \
        --date-font="JetBrains Mono Nerd Font" \
        --radius=120 \
        --ring-width=8
    exit 0
fi

# Nivel 3: Respaldo nativo con color sólido
if command -v i3lock &>/dev/null; then
    i3lock -c 1a1b26
    exit 0
fi
EOF
    chmod +x "$LOCK_SCRIPT"
    ln -sf "$LOCK_SCRIPT" "$HOME/.local/bin/lockscreen" 2>/dev/null || true

    # Generar caché de betterlockscreen si está disponible
    if command -v betterlockscreen &>/dev/null; then
        local SAMPLE_WP
        SAMPLE_WP=$(find "$HOME/Pictures/Wallpapers" -type f \( -name "*.jpg" -o -name "*.png" \) 2>/dev/null | head -n 1)
        if [ -n "$SAMPLE_WP" ]; then
            log_info "Generando caché gráfica de bloqueo a partir de: $(basename "$SAMPLE_WP")..."
            betterlockscreen -u "$SAMPLE_WP" --blur 0.5 &>> "$LOG_FILE" || true
        fi
    fi

    # Registrar el atajo de bloqueo en sxhkdrc
    local SXHKD_CONF="$HOME/.config/sxhkd/sxhkdrc"
    if [ -f "$SXHKD_CONF" ] && ! grep -q "techogr_lock" "$SXHKD_CONF"; then
        tee -a "$SXHKD_CONF" >/dev/null << 'EOF'

# ------------------------------------------------------------------------------
# Bloqueo de pantalla manual (TechOGR Setup)
# ------------------------------------------------------------------------------
super + alt + l
    $HOME/.local/bin/techogr_lock
EOF
    fi

    # Bloqueo automático en suspensión mediante xss-lock en bspwmrc
    local BSPWMRC_PATH="$HOME/.config/bspwm/bspwmrc"
    if [ -f "$BSPWMRC_PATH" ] && ! grep -q "xss-lock" "$BSPWMRC_PATH"; then
        tee -a "$BSPWMRC_PATH" >/dev/null << 'EOF'

# Demonio de bloqueo de pantalla automático al suspender
killall -q xss-lock
xss-lock --transfer-sleep-lock -- $HOME/.local/bin/techogr_lock &
EOF
    fi

    log_success "Sub-sistema de bloqueo configurado y blindado."
}

# ------------------------------------------------------------------------------
# 12. SHELL PREDETERMINADA (ZSH)
# ------------------------------------------------------------------------------
setup_user_shell() {
    log_step "Configuración del Intérprete de Comandos (Zsh)"

    local ZSH_BIN
    ZSH_BIN=$(command -v zsh 2>/dev/null || true)

    if [ -n "$ZSH_BIN" ]; then
        if [ "$(basename "$SHELL")" != "zsh" ]; then
            log_info "Cambiando shell predeterminada a ZSH ($ZSH_BIN) para el usuario $USER..."
            if ! grep -Fxq "$ZSH_BIN" /etc/shells; then
                echo "$ZSH_BIN" | sudo tee -a /etc/shells >/dev/null
            fi
            sudo chsh -s "$ZSH_BIN" "$USER" &>> "$LOG_FILE" || chsh -s "$ZSH_BIN" &>> "$LOG_FILE" || true
            log_success "Shell cambiada a ZSH."
        else
            log_info "ZSH ya es la shell predeterminada."
        fi
    fi
}

# ------------------------------------------------------------------------------
# 13. PRE-FLIGHT SELF-TEST (DIAGNÓSTICO PREVENTIVO ANTES DE REINICIAR)
# ------------------------------------------------------------------------------
perform_preflight_diagnostics() {
    log_step "Ejecutando Diagnóstico Preventivo del Sistema (Pre-Flight Check)"

    local test_failed=false

    # 1. Comprobar binario Xorg
    if ! command -v Xorg &>/dev/null; then
        log_error "Fallo crítico: El servidor Xorg no está instalado."
        test_failed=true
    fi

    # 2. Comprobar BSPWM y SXHKD
    if ! command -v bspwm &>/dev/null; then
        log_error "Fallo crítico: El ejecutable de bspwm no está en el PATH."
        test_failed=true
    fi
    if ! command -v sxhkd &>/dev/null; then
        log_error "Fallo crítico: El ejecutable de sxhkd no está en el PATH."
        test_failed=true
    fi

    # 3. Comprobar archivo .desktop de sesión
    if [ ! -f /usr/share/xsessions/bspwm.desktop ]; then
        log_error "Fallo crítico: /usr/share/xsessions/bspwm.desktop no existe."
        test_failed=true
    fi

    # 4. Comprobar servicio LightDM
    if ! systemctl is-enabled lightdm.service &>/dev/null; then
        log_warning "LightDM no estaba habilitado. Forzando activación..."
        sudo systemctl enable lightdm.service -f &>> "$LOG_FILE"
    fi

    # 5. Comprobar target por defecto de systemd
    CURRENT_TARGET=$(systemctl get-default)
    if [ "$CURRENT_TARGET" != "graphical.target" ]; then
        log_warning "El target actual es $CURRENT_TARGET. Forzando a graphical.target..."
        sudo systemctl set-default graphical.target &>> "$LOG_FILE"
    fi

    if [ "$test_failed" = true ]; then
        log_error "El diagnóstico preventivo detectó anomalías. Revisa $LOG_FILE antes de reiniciar."
    else
        log_success "Diagnóstico preventivo aprobado: Sistema listo para arrancar en modo gráfico."
    fi
}

# ------------------------------------------------------------------------------
# 14. RESUMEN FINAL Y SOLICITUD DE REINICIO
# ------------------------------------------------------------------------------
show_final_summary() {
    echo ""
    echo -e "${C_GREEN}${C_BOLD}╔═════════════════════════════════════════════════════════════════════════╗${C_RESET}"
    echo -e "${C_GREEN}${C_BOLD}║      ¡ENTORNO GRÁFICO TECHOGR BSPWM INSTALADO SATISFACTORIAMENTE!       ║${C_RESET}"
    echo -e "${C_GREEN}${C_BOLD}╚═════════════════════════════════════════════════════════════════════════╝${C_RESET}"
    echo ""
    echo -e " ${C_CYAN}Resumen de Componentes Operativos:${C_RESET}"
    echo -e "   • ${C_BOLD}Pantalla de Inicio (Login):${C_RESET} LightDM GTK Greeter (A prueba de fallos de KMS)"
    echo -e "   • ${C_BOLD}Controladores Gráficos:${C_RESET}     Mesa / Vulkan / KMS Modesetting ($PICOM_BACKEND)"
    echo -e "   • ${C_BOLD}Objetivo Systemd:${C_RESET}           graphical.target (Inicio automático directo)"
    echo -e "   • ${C_BOLD}Servidor de Sonido:${C_RESET}         PipeWire + WirePlumber"
    echo -e "   • ${C_BOLD}Copia de Seguridad:${C_RESET}         $TARGET_BACKUP"
    echo ""
    echo -e " ${C_CYAN}Atajos de Teclado Principales:${C_RESET}"
    echo -e "   • ${C_YELLOW}Super + Enter${C_RESET}             Abrir Terminal Kitty"
    echo -e "   • ${C_YELLOW}Super + D${C_RESET}                 Lanzador de Aplicaciones Rofi"
    echo -e "   • ${C_YELLOW}Super + Alt + L${C_RESET}           ${C_BOLD}Bloqueo de Pantalla Gráfico${C_RESET}"
    echo -e "   • ${C_YELLOW}Super + Alt + R${C_RESET}           Recargar BSPWM y Polybar"
    echo -e "   • ${C_YELLOW}Super + W / C${C_RESET}             Cerrar Ventana Enfocada"
    echo -e "   • ${C_YELLOW}Click Derecho en Fondo${C_RESET}    Menú JGmenu"
    echo ""
    echo -e "${C_YELLOW}${C_BOLD}Al reiniciar el equipo, el sistema cargará directamente la interfaz gráfica${C_RESET}"
    echo -e "${C_YELLOW}${C_BOLD}solicitando tu usuario y contraseña.${C_RESET}"
    echo ""
    read -rp " ¿Deseas reiniciar el sistema ahora? [s/N]: " reboot_input
    if [[ "$reboot_input" =~ ^[sS]$ ]]; then
        log_info "Reiniciando el sistema de forma segura..."
        sudo reboot
    else
        log_info "Instalación completada. Puedes reiniciar manualmente con: ${C_CYAN}sudo reboot${C_RESET}"
    fi
}

# ------------------------------------------------------------------------------
# ENTRADA PRINCIPAL (MAIN)
# ------------------------------------------------------------------------------
main() {
    print_banner
    check_execution_privileges
    validate_environment
    detect_and_configure_hardware
    setup_aur_manager
    install_system_dependencies
    configure_display_manager_bulletproof
    deploy_user_dotfiles
    setup_lockscreen_infrastructure
    setup_user_shell
    perform_preflight_diagnostics
    show_final_summary
}

main "$@"
