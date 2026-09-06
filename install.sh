#!/usr/bin/env bash
# ==============================================================================
#  🛠️ TECHOGR BSPWM DOTFILES - FULL SYSTEM & DISPLAY MANAGER INSTALLER
# ==============================================================================
#  Convierte una instalación CLI/Mínima en un entorno de escritorio completo.
#  Compatible con: Arch Linux, CachyOS, EndeavourOS, Garuda, BlackArch, Manjaro, etc.
#  Licencia: GPL-3.0
# ==============================================================================

set -o pipefail

# ------------------------------------------------------------------------------
# 1. PARÁMETROS GLOBALES Y LOGGING
# ------------------------------------------------------------------------------
SCRIPT_VERSION="3.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$HOME/.techogr_install.log"
BACKUP_BASE_DIR="$HOME/.dotfiles_backup"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
TARGET_BACKUP="$BACKUP_BASE_DIR/backup_$TIMESTAMP"

echo "=== TechOGR BSPWM Installer Log - $(date) ===" > "$LOG_FILE"

# ------------------------------------------------------------------------------
# 2. COLORES Y GLIFOS
# ------------------------------------------------------------------------------
C_RESET="\e[0m"
C_BOLD="\e[1m"
C_RED="\e[31m"
C_GREEN="\e[32m"
C_YELLOW="\e[33m"
C_BLUE="\e[34m"
C_MAGENTA="\e[35m"
C_CYAN="\e[36m"

ARROW="${C_CYAN}➜${C_RESET}"
CHECK="${C_GREEN}✔${C_RESET}"
CROSS="${C_RED}✖${C_RESET}"
WARN="${C_YELLOW}⚠${C_RESET}"

log_info()    { echo -e " ${ARROW} ${C_BOLD}$1${C_RESET}"; echo "[INFO] $(date +'%T') - $1" >> "$LOG_FILE"; }
log_success() { echo -e " ${CHECK} ${C_GREEN}${C_BOLD}$1${C_RESET}"; echo "[SUCCESS] $(date +'%T') - $1" >> "$LOG_FILE"; }
log_warning() { echo -e " ${WARN} ${C_YELLOW}${C_BOLD}$1${C_RESET}"; echo "[WARNING] $(date +'%T') - $1" >> "$LOG_FILE"; }
log_error()   { echo -e " ${CROSS} ${C_RED}${C_BOLD}$1${C_RESET}"; echo "[ERROR] $(date +'%T') - $1" >> "$LOG_FILE"; }
log_step()    { echo -e "\n${C_MAGENTA}${C_BOLD}:: $1${C_RESET}"; echo "========== [STEP] $1 ==========" >> "$LOG_FILE"; }

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
    echo -e "  │      Full Desktop & Display Manager Automated Installer     │"
    echo -e "  │       Transforma sistemas mínimos (CLI) en BSPWM puro       │"
    echo -e "  │        Compatible con CachyOS, Arch, EndeavourOS, etc.      │"
    echo -e "  └─────────────────────────────────────────────────────────────┘${C_RESET}\n"
}

# ------------------------------------------------------------------------------
# 3. CONTROL DE PRIVILEGIOS Y LIMPIEZA
# ------------------------------------------------------------------------------
cleanup() {
    local code=$?
    if [ -n "$SUDO_PID" ] && kill -0 "$SUDO_PID" 2>/dev/null; then
        kill "$SUDO_PID" 2>/dev/null || true
    fi
    if [ $code -ne 0 ]; then
        echo ""
        log_error "Instalación interrumpida (Código: $code). Revisa el registro en: $LOG_FILE"
    fi
}
trap cleanup EXIT INT TERM

check_privileges() {
    if [ "$EUID" -eq 0 ]; then
        echo -e "${C_RED}${C_BOLD}Error:${C_RESET} No ejecutes este script como root o usando sudo."
        echo -e "Ejecútalo como usuario normal: ${C_CYAN}./install.sh${C_RESET}"
        exit 1
    fi

    log_info "Solicitando credenciales de administrador..."
    sudo -v || { log_error "No se pudieron obtener permisos sudo."; exit 1; }

    # Mantener vivo sudo
    while true; do
        sudo -n true
        sleep 50
        kill -0 "$$" || exit
    done 2>/dev/null &
    SUDO_PID=$!
}

# ------------------------------------------------------------------------------
# 4. COMPROBACIÓN DEL SISTEMA Y RED
# ------------------------------------------------------------------------------
validate_environment() {
    log_step "Verificando compatibilidad de la distribución y red"

    ARCH=$(uname -m)
    if [ "$ARCH" != "x86_64" ]; then
        log_error "Arquitectura no soportada: $ARCH (se requiere x86_64)."
        exit 1
    fi

    if [ -f /etc/os-release ]; then
        # shellcheck disable=SC1091
        source /etc/os-release
        DISTRO_NAME="${NAME:-Arch Linux}"
        if [[ "${ID:-}" =~ (arch|cachyos|endeavouros|garuda|blackarch|manjaro|arcolinux) ]] || \
           [[ "${ID_LIKE:-}" =~ arch ]]; then
            log_success "Distribución compatible detectada: ${C_CYAN}$DISTRO_NAME${C_RESET}"
        else
            log_error "Esta distribución ($DISTRO_NAME) no está basada en Arch Linux."
            exit 1
        fi
    else
        log_error "No se pudo leer /etc/os-release."
        exit 1
    fi

    # Desbloquear pacman si quedó trabado
    if [ -f /var/lib/pacman/db.lck ]; then
        log_warning "Base de datos de pacman bloqueada (/var/lib/pacman/db.lck)."
        sudo rm -f /var/lib/pacman/db.lck
        log_success "Bloqueo de pacman eliminado."
    fi

    # Conectividad
    log_info "Verificando acceso a internet..."
    if curl -s --head --connect-timeout 4 "https://archlinux.org" &>/dev/null || \
       curl -s --head --connect-timeout 4 "https://1.1.1.1" &>/dev/null; then
        log_success "Conexión a internet confirmada."
    else
        log_error "No hay conexión a internet activa."
        exit 1
    fi
}

# ------------------------------------------------------------------------------
# 5. DETECCIÓN DE HARDWARE Y CONTROLADORES GRÁFICOS (XORG + GPU)
# ------------------------------------------------------------------------------
detect_and_install_hardware_drivers() {
    log_step "Detección de Hardware y Controladores de Video"

    IS_VM=false
    GPU_PACKAGES=()

    if command -v systemd-detect-virt &>/dev/null && [ "$(systemd-detect-virt)" != "none" ]; then
        IS_VM=true
        VIRT_NAME=$(systemd-detect-virt)
        log_warning "Máquina Virtual detectada: $VIRT_NAME"
        PICOM_BACKEND="xrender"
        PICOM_VSYNC="false"

        case "$VIRT_NAME" in
            oracle|virtualbox)
                GPU_PACKAGES+=(virtualbox-guest-utils xf86-video-vmware)
                ;;
            vmware)
                GPU_PACKAGES+=(open-vm-tools xf86-video-vmware xf86-input-vmmouse)
                ;;
            kvm|qemu|bochs)
                GPU_PACKAGES+=(qemu-guest-agent)
                ;;
        esac
    else
        log_success "Instalación en máquina física (Bare-Metal)."
        PICOM_BACKEND="glx"
        PICOM_VSYNC="true"

        # Detección de GPU
        local VGA_INFO
        VGA_INFO=$(lspci -k 2>/dev/null | grep -EA3 -i "vga|3d|display" || true)

        if echo "$VGA_INFO" | grep -iq "nvidia"; then
            log_info "GPU NVIDIA detectada. Asegurando utilidades compatibles."
            GPU_PACKAGES+=(nvidia-utils)
        fi
        if echo "$VGA_INFO" | grep -iq "intel"; then
            log_info "GPU Intel detectada. Añadiendo aceleración Vulkan/OpenGL."
            GPU_PACKAGES+=(vulkan-intel intel-media-driver)
        fi
        if echo "$VGA_INFO" | grep -iq "amd|radeon|advanced micro devices"; then
            log_info "GPU AMD detectada. Añadiendo aceleración Vulkan/Radeon."
            GPU_PACKAGES+=(xf86-video-amdgpu vulkan-radeon)
        fi
    fi

    # Controladores base Xorg y Mesa universal
    GPU_PACKAGES+=(mesa libglvnd xf86-video-fbdev xf86-video-vesa)

    log_info "Instalando paquetes gráficos esenciales..."
    sudo pacman -S --needed --noconfirm "${GPU_PACKAGES[@]}" &>> "$LOG_FILE" || true

    # Habilitar servicios de VM si aplica
    if [ "$IS_VM" = true ]; then
        command -v VBoxService &>/dev/null && sudo systemctl enable --now vboxservice.service &>> "$LOG_FILE" || true
        command -v vmtoolsd &>/dev/null && sudo systemctl enable --now vmtoolsd.service &>> "$LOG_FILE" || true
    fi
}

# ------------------------------------------------------------------------------
# 6. CONFIGURACIÓN DE AUR HELPER (YAY-BIN)
# ------------------------------------------------------------------------------
setup_aur_helper() {
    log_step "Verificación / Instalación del Administrador AUR"

    if command -v yay &>/dev/null; then
        AUR_HELPER="yay"
        log_success "AUR Helper detectado: yay"
    elif command -v paru &>/dev/null; then
        AUR_HELPER="paru"
        log_success "AUR Helper detectado: paru"
    else
        log_warning "No se detectó ningún gestor AUR. Instalando yay-bin automáticamente..."
        sudo pacman -S --needed --noconfirm base-devel git &>> "$LOG_FILE"

        local TMP_DIR="/tmp/yay-bin-installer-$$"
        rm -rf "$TMP_DIR"
        mkdir -p "$TMP_DIR"

        if git clone https://aur.archlinux.org/yay-bin.git "$TMP_DIR/yay-bin" &>> "$LOG_FILE"; then
            (
                cd "$TMP_DIR/yay-bin" || exit 1
                makepkg -si --noconfirm &>> "$LOG_FILE"
            )
            rm -rf "$TMP_DIR"
            AUR_HELPER="yay"
            log_success "yay-bin instalado correctamente."
        else
            log_error "No se pudo clonar yay-bin de AUR. Revisa tu conexión a internet."
            exit 1
        fi
    fi
}

# ------------------------------------------------------------------------------
# 7. MATRIZ INTEGRAL DE PAQUETES (SERVIDOR GRÁFICO, AUDIO, WM, LIGHTDM)
# ------------------------------------------------------------------------------
install_full_system_stack() {
    log_step "Instalando Servidor Gráfico, Display Manager y BSPWM"

    log_info "Sincronizando base de datos de repositorios..."
    sudo pacman -Sy &>> "$LOG_FILE"

    # 1. Servidor Gráfico X11 Base
    local XORG_STACK=(
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
        xdotool
        xdo
        xclip
        xsettingsd
    )

    # 2. Display Manager (Inicio de Sesión Gráfico)
    local DISPLAY_MANAGER_STACK=(
        lightdm
        lightdm-gtk-greeter
        lightdm-gtk-greeter-settings
    )

    # 3. BSPWM y Herramientas del Entorno
    local DESKTOP_STACK=(
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

    # 4. Servidor de Sonido Moderno (PipeWire)
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

    # 5. Utilidades del Sistema, Terminal y Apariencia
    local UTILS_STACK=(
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

    # Paquetes AUR para Lockscreen de sesión
    local AUR_STACK=(
        i3lock-color
        betterlockscreen
    )

    local MASTER_PACMAN_LIST=(
        "${XORG_STACK[@]}"
        "${DISPLAY_MANAGER_STACK[@]}"
        "${DESKTOP_STACK[@]}"
        "${AUDIO_STACK[@]}"
        "${UTILS_STACK[@]}"
    )

    local total_pkgs=${#MASTER_PACMAN_LIST[@]}
    local count=0
    local failed=()

    log_info "Instalando dependencias oficiales ($total_pkgs paquetes)..."
    for pkg in "${MASTER_PACMAN_LIST[@]}"; do
        ((count++))
        printf " [PACMAN] (%2d/%2d) %-30s" "$count" "$total_pkgs" "$pkg"
        if pacman -Qi "$pkg" &>/dev/null; then
            echo -e " [ ${C_GREEN}LISTO${C_RESET} ]"
        else
            if sudo pacman -S --needed --noconfirm "$pkg" &>> "$LOG_FILE"; then
                echo -e " [ ${C_CYAN}INSTALADO${C_RESET} ]"
            else
                echo -e " [ ${C_RED}FALLÓ${C_RESET} ]"
                failed+=("$pkg")
            fi
        fi
    done

    # Reintento selectivo
    if [ ${#failed[@]} -gt 0 ]; then
        log_warning "Reintentando paquetes pendientes: ${failed[*]}"
        for f in "${failed[@]}"; do
            sudo pacman -S --needed --noconfirm "$f" &>> "$LOG_FILE" || true
        done
    fi

    # AUR
    log_info "Instalando paquetes visuales desde AUR..."
    for apkg in "${AUR_STACK[@]}"; do
        printf " [AUR]    Procesando %-30s" "$apkg"
        if pacman -Qi "$apkg" &>/dev/null; then
            echo -e " [ ${C_GREEN}LISTO${C_RESET} ]"
        else
            if $AUR_HELPER -S --needed --noconfirm "$apkg" &>> "$LOG_FILE"; then
                echo -e " [ ${C_CYAN}INSTALADO${C_RESET} ]"
            else
                echo -e " [ ${C_YELLOW}AVISO${C_RESET} ]"
                log_warning "$apkg no disponible por AUR. Se usará el respaldo con i3lock nativo."
            fi
        fi
    done

    # Crear carpetas XDG estándar
    xdg-user-dirs-update &>> "$LOG_FILE" || true
    log_success "Pila de paquetes del sistema instalada con éxito."
}

# ------------------------------------------------------------------------------
# 8. CONFIGURACIÓN PROFESIONAL DEL DISPLAY MANAGER (LIGHTDM)
# ------------------------------------------------------------------------------
setup_display_manager() {
    log_step "Configuración del Gestor de Inicio Gráfico (LightDM)"

    # Asegurar sesión Xsession para BSPWM en /usr/share/xsessions/bspwm.desktop
    sudo mkdir -p /usr/share/xsessions
    sudo tee /usr/share/xsessions/bspwm.desktop >/dev/null << 'EOF'
[Desktop Entry]
Name=BSPWM
Comment=Binary space partitioning window manager
Exec=bspwm
Type=XSession
DesktopNames=bspwm
EOF

    # Configurar fondo para la pantalla de inicio de sesión
    local BG_TARGET_DIR="/usr/share/backgrounds/techogr"
    sudo mkdir -p "$BG_TARGET_DIR"
    local SAMPLE_WALL
    SAMPLE_WALL=$(find "$SCRIPT_DIR/Wallpapers" -type f \( -name "*.jpg" -o -name "*.png" \) 2>/dev/null | head -n 1)

    if [ -n "$SAMPLE_WALL" ]; then
        sudo cp -f "$SAMPLE_WALL" "$BG_TARGET_DIR/login_background.jpg"
        sudo chmod 644 "$BG_TARGET_DIR/login_background.jpg"
    fi

    # Configurar /etc/lightdm/lightdm.conf
    log_info "Estableciendo BSPWM como sesión predeterminada en LightDM..."
    sudo mkdir -p /etc/lightdm
    sudo tee /etc/lightdm/lightdm.conf >/dev/null << 'EOF'
[LightDM]
run-directory=/run/lightdm

[Seat:*]
greeter-session=lightdm-gtk-greeter
user-session=bspwm
session-wrapper=/etc/lightdm/Xsession
autologin-guest=false
EOF

    # Configurar /etc/lightdm/lightdm-gtk-greeter.conf con estética cuidada
    log_info "Personalizando aspecto visual de la pantalla de bienvenida..."
    sudo tee /etc/lightdm/lightdm-gtk-greeter.conf >/dev/null << EOF
[greeter]
theme-name = Adwaita-dark
icon-theme-name = Papirus-Dark
font-name = JetBrainsMono Nerd Font 10
background = $BG_TARGET_DIR/login_background.jpg
user-background = false
clock-format = %A, %d %B  •  %H:%M
indicators = ~host;~spacer;~clock;~spacer;~session;~power
position = 50%,center 50%,center
default-user-image = #avatar-default
screensaver-timeout = 60
EOF

    # Deshabilitar otros gestores de pantalla en conflicto y habilitar LightDM
    log_info "Activando servicio systemd de LightDM..."
    for dm in sddm gdm lxdm ly greetd; do
        sudo systemctl disable "$dm.service" &>> "$LOG_FILE" || true
    done
    sudo systemctl enable lightdm.service -f &>> "$LOG_FILE"
    log_success "LightDM configurado. Tu PC iniciará en la pantalla gráfica directamente."
}

# ------------------------------------------------------------------------------
# 9. BACKUP PREVENTIVO Y DESPLIEGUE DE DOTFILES
# ------------------------------------------------------------------------------
backup_and_deploy() {
    log_step "Respaldo y Despliegue de Archivos de Configuración"

    # Backup
    mkdir -p "$TARGET_BACKUP"
    local ITEMS=(
        "$HOME/.config/bspwm"
        "$HOME/.config/sxhkd"
        "$HOME/.config/polybar"
        "$HOME/.config/rofi"
        "$HOME/.config/picom"
        "$HOME/.config/kitty"
        "$HOME/.config/dunst"
        "$HOME/.config/jgmenu"
        "$HOME/.zshrc"
    )
    for it in "${ITEMS[@]}"; do
        [ -e "$it" ] && cp -rf "$it" "$TARGET_BACKUP/" 2>> "$LOG_FILE" || true
    done
    log_success "Respaldo preventivo guardado en: $TARGET_BACKUP"

    # Carpetas destino
    mkdir -p "$HOME/.config" "$HOME/.local/bin" "$HOME/.local/share/fonts" "$HOME/Pictures/Wallpapers"

    # 1. config/ -> ~/.config/
    [ -d "$SCRIPT_DIR/config" ] && cp -rf "$SCRIPT_DIR/config/"* "$HOME/.config/" 2>> "$LOG_FILE"

    # 2. kitty/ -> ~/.config/kitty/
    if [ -d "$SCRIPT_DIR/kitty" ]; then
        mkdir -p "$HOME/.config/kitty"
        cp -rf "$SCRIPT_DIR/kitty/"* "$HOME/.config/kitty/" 2>> "$LOG_FILE"
    fi

    # 3. home/ -> $HOME/ (archivos ocultos incluidos)
    [ -d "$SCRIPT_DIR/home" ] && cp -rf "$SCRIPT_DIR/home/." "$HOME/" 2>> "$LOG_FILE"

    # 4. Wallpapers/ -> ~/Pictures/Wallpapers/
    if [ -d "$SCRIPT_DIR/Wallpapers" ]; then
        cp -rf "$SCRIPT_DIR/Wallpapers/"* "$HOME/Pictures/Wallpapers/" 2>> "$LOG_FILE"
        [ ! -L "$HOME/Wallpapers" ] && ln -sf "$HOME/Pictures/Wallpapers" "$HOME/Wallpapers" 2>/dev/null || true
    fi

    # 5. misc/
    if [ -d "$SCRIPT_DIR/misc" ]; then
        [ -d "$SCRIPT_DIR/misc/fonts" ] && cp -rf "$SCRIPT_DIR/misc/fonts/"* "$HOME/.local/share/fonts/" 2>> "$LOG_FILE"
        [ -d "$SCRIPT_DIR/misc/bin" ] && cp -rf "$SCRIPT_DIR/misc/bin/"* "$HOME/.local/bin/" 2>> "$LOG_FILE"
        cp -rf "$SCRIPT_DIR/misc/"* "$HOME/.local/share/" 2>/dev/null || true
    fi

    # 6. ~/.xinitrc de respaldo (para arrancar con 'startx' si se apaga LightDM)
    tee "$HOME/.xinitrc" >/dev/null << 'EOF'
#!/bin/sh
userresources=$HOME/.Xresources
usermodmap=$HOME/.Xmodmap
[ -f "$userresources" ] && xrdb -merge "$userresources"
[ -f "$usermodmap" ] && xmodmap "$usermodmap"
sxhkd &
exec bspwm
EOF
    chmod +x "$HOME/.xinitrc"

    # 7. Permisos de ejecución
    find "$HOME/.config/bspwm" -type f -exec chmod +x {} + 2>/dev/null || true
    find "$HOME/.config/polybar" -type f \( -name "*.sh" -o -name "launch*" \) -exec chmod +x {} + 2>/dev/null || true
    find "$HOME/.local/bin" -type f -exec chmod +x {} + 2>/dev/null || true

    # 8. Ajuste Picom según hardware
    local PICOM_FILE="$HOME/.config/picom/picom.conf"
    if [ -f "$PICOM_FILE" ]; then
        sed -i "s/backend = .*/backend = \"$PICOM_BACKEND\";/" "$PICOM_FILE" 2>/dev/null || true
        sed -i "s/vsync = .*/vsync = $PICOM_VSYNC;/" "$PICOM_FILE" 2>/dev/null || true
    fi

    # 9. Caché de fuentes
    fc-cache -fv &>> "$LOG_FILE"
    log_success "Archivos del repositorio desplegados y permisos asignados."
}

# ------------------------------------------------------------------------------
# 10. BLOQUEO DE PANTALLA DE SESIÓN (BETTERLOCKSCREEN / I3LOCK-COLOR)
# ------------------------------------------------------------------------------
setup_session_lockscreen() {
    log_step "Configuración del Bloqueo Gráfico de Sesión (Atajo y Suspensión)"

    # Script principal de bloqueo en ~/.local/bin/lockscreen
    tee "$HOME/.local/bin/lockscreen" >/dev/null << 'EOF'
#!/usr/bin/env bash
if command -v betterlockscreen &>/dev/null; then
    betterlockscreen -l dimblur --time-format "%I:%M %p"
elif command -v i3lock-color &>/dev/null; then
    i3lock-color --clock --indicator --time-str="%H:%M" --date-str="%A, %d %B" \
                 --inside-color=1a1b26bb --ring-color=7aa2f7ff --keyhl-color=bb9af7ff \
                 --line-uses-inside --time-font="JetBrains Mono Nerd Font"
else
    i3lock -c 1a1b26
fi
EOF
    chmod +x "$HOME/.local/bin/lockscreen"

    # Generar caché de imagen si betterlockscreen está disponible
    if command -v betterlockscreen &>/dev/null; then
        local WALL_PICK
        WALL_PICK=$(find "$HOME/Pictures/Wallpapers" -type f \( -name "*.jpg" -o -name "*.png" \) 2>/dev/null | head -n 1)
        if [ -n "$WALL_PICK" ]; then
            betterlockscreen -u "$WALL_PICK" --blur 0.5 &>> "$LOG_FILE" || true
        fi
    fi

    # Atajo en sxhkdrc (Super + Alt + L)
    local SXHKD_CONF="$HOME/.config/sxhkd/sxhkdrc"
    if [ -f "$SXHKD_CONF" ] && ! grep -q "lockscreen" "$SXHKD_CONF"; then
        tee -a "$SXHKD_CONF" >/dev/null << 'EOF'

# Bloqueo de pantalla manual (TechOGR)
super + alt + l
    $HOME/.local/bin/lockscreen
EOF
    fi

    # Bloqueo automático en suspensión con xss-lock en bspwmrc
    local BSPWMRC="$HOME/.config/bspwm/bspwmrc"
    if [ -f "$BSPWMRC" ] && ! grep -q "xss-lock" "$BSPWMRC"; then
        tee -a "$BSPWMRC" >/dev/null << 'EOF'

# Demonio de bloqueo de pantalla al suspender / cerrar tapa
killall -q xss-lock
xss-lock --transfer-sleep-lock -- $HOME/.local/bin/lockscreen &
EOF
    fi

    log_success "Bloqueo de sesión configurado para atajo y suspensión."
}

# ------------------------------------------------------------------------------
# 11. SHELL PREDETERMINADA (ZSH)
# ------------------------------------------------------------------------------
setup_user_shell() {
    log_step "Configuración del Intérprete de Comandos (Zsh)"

    local ZSH_BIN
    ZSH_BIN=$(command -v zsh 2>/dev/null || true)
    if [ -n "$ZSH_BIN" ] && [ "$(basename "$SHELL")" != "zsh" ]; then
        if ! grep -Fxq "$ZSH_BIN" /etc/shells; then
            echo "$ZSH_BIN" | sudo tee -a /etc/shells >/dev/null
        fi
        sudo chsh -s "$ZSH_BIN" "$USER" &>> "$LOG_FILE" || chsh -s "$ZSH_BIN" &>> "$LOG_FILE" || true
        log_success "Shell predeterminada cambiada a ZSH."
    else
        log_info "ZSH ya está configurado como predeterminado."
    fi
}

# ------------------------------------------------------------------------------
# 12. RESUMEN FINAL Y REINICIO
# ------------------------------------------------------------------------------
show_summary() {
    echo ""
    echo -e "${C_GREEN}${C_BOLD}╔═════════════════════════════════════════════════════════════════════════╗${C_RESET}"
    echo -e "${C_GREEN}${C_BOLD}║          ¡SISTEMA GRÁFICO COMPLETO INSTALADO CORRECTAMENTE!            ║${C_RESET}"
    echo -e "${C_GREEN}${C_BOLD}╚═════════════════════════════════════════════════════════════════════════╝${C_RESET}"
    echo ""
    echo -e " ${C_CYAN}Características configuradas:${C_RESET}"
    echo -e "   • ${C_BOLD}Pantalla de Inicio (Login):${C_RESET} LightDM con tema Adwaita-dark y fondo personalizado."
    echo -e "   • ${C_BOLD}Gestor de Ventanas:${C_RESET}         BSPWM como sesión predeterminada."
    echo -e "   • ${C_BOLD}Bloqueo en Sesión:${C_RESET}          Super + Alt + L (o al suspender la PC)."
    echo -e "   • ${C_BOLD}Terminal Kitty:${C_RESET}             Super + Enter."
    echo -e "   • ${C_BOLD}Lanzador Rofi:${C_RESET}              Super + D."
    echo -e "   • ${C_BOLD}Servidor de Sonido:${C_RESET}         PipeWire + WirePlumber activo."
    echo ""
    echo -e "${C_YELLOW}${C_BOLD}¡TODO LISTO! Al reiniciar el equipo, verás la pantalla de inicio de sesión${C_RESET}"
    echo -e "${C_YELLOW}${C_BOLD}pidiendo tu usuario y contraseña para entrar directo a BSPWM.${C_RESET}"
    echo ""
    read -rp " ¿Deseas reiniciar el sistema ahora mismo? [s/N]: " reboot_choice
    if [[ "$reboot_choice" =~ ^[sS]$ ]]; then
        log_info "Reiniciando equipo..."
        sudo reboot
    else
        log_info "Puedes reiniciar más tarde escribiendo: ${C_CYAN}sudo reboot${C_RESET}"
    fi
}

# ------------------------------------------------------------------------------
# ENTRADA PRINCIPAL
# ------------------------------------------------------------------------------
main() {
    print_banner
    check_privileges
    validate_environment
    detect_and_install_hardware_drivers
    setup_aur_helper
    install_full_system_stack
    setup_display_manager
    backup_and_deploy
    setup_session_lockscreen
    setup_user_shell
    show_summary
}

main "$@"
