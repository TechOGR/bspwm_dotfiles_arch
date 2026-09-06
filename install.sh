#!/usr/bin/env bash
# ==============================================================================
#  🛠️ TECHOGR BSPWM DOTFILES - ADVANCED SYSTEM INSTALLER
# ==============================================================================
#  Compatible con: Arch Linux, CachyOS, EndeavourOS, Garuda, BlackArch, Manjaro, etc.
#  Licencia: GPL-3.0
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. PARÁMETROS GLOBALES Y CONFIGURACIÓN DE SEGURIDAD
# ------------------------------------------------------------------------------
set -o pipefail

SCRIPT_VERSION="2.5.0"
REPO_NAME="TechOGR/bspwm_dotfiles_arch"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$HOME/.techogr_install.log"
BACKUP_BASE_DIR="$HOME/.dotfiles_backup"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
TARGET_BACKUP="$BACKUP_BASE_DIR/backup_$TIMESTAMP"

# Limpiar archivo de log previo
echo "=== TechOGR BSPWM Installer Log - $(date) ===" > "$LOG_FILE"

# ------------------------------------------------------------------------------
# 2. PALETA DE COLORES ANSI Y GLIFOS
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
C_BG_BLUE="\e[44m"

ARROW="${C_CYAN}➜${C_RESET}"
CHECK="${C_GREEN}✔${C_RESET}"
CROSS="${C_RED}✖${C_RESET}"
WARN="${C_YELLOW}⚠${C_RESET}"
STAR="${C_MAGENTA}★${C_RESET}"

# ------------------------------------------------------------------------------
# 3. FUNCIONES DE INTERFAZ, SPINNER Y LOGGING
# ------------------------------------------------------------------------------
log_info() {
    echo -e " ${ARROW} ${C_BOLD}$1${C_RESET}"
    echo "[INFO] $(date +'%T') - $1" >> "$LOG_FILE"
}

log_success() {
    echo -e " ${CHECK} ${C_GREEN}${C_BOLD}$1${C_RESET}"
    echo "[SUCCESS] $(date +'%T') - $1" >> "$LOG_FILE"
}

log_warning() {
    echo -e " ${WARN} ${C_YELLOW}${C_BOLD}$1${C_RESET}"
    echo "[WARNING] $(date +'%T') - $1" >> "$LOG_FILE"
}

log_error() {
    echo -e " ${CROSS} ${C_RED}${C_BOLD}$1${C_RESET}"
    echo "[ERROR] $(date +'%T') - $1" >> "$LOG_FILE"
}

log_step() {
    echo -e "\n${C_MAGENTA}${C_BOLD}:: $1${C_RESET}"
    echo "==================== [STEP] $1 ====================" >> "$LOG_FILE"
}

spinner() {
    local pid=$1
    local delay=0.08
    local spinstr='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    while kill -0 "$pid" 2>/dev/null; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
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
    echo -e "  │      BSPWM Professional Environment Automated Installer     │"
    echo -e "  │            Author: TechOGR  |  Architecture: x86_64         │"
    echo -e "  │      Target: Arch Linux, CachyOS, Endeavour, Garuda, etc.   │"
    echo -e "  └─────────────────────────────────────────────────────────────┘${C_RESET}\n"
}

# ------------------------------------------------------------------------------
# 4. GESTIÓN DE PRIVILEGIOS Y SEÑALES DE SALIDA
# ------------------------------------------------------------------------------
cleanup_and_exit() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo ""
        log_error "La instalación fue cancelada o sufrió un error crítico (Código: $exit_code)."
        log_info "Consulta los detalles en el archivo de registro: ${C_CYAN}$LOG_FILE${C_RESET}"
    fi
    # Matar el bucle que mantiene vivo a sudo si existe
    if [ -n "$SUDO_PID" ] && kill -0 "$SUDO_PID" 2>/dev/null; then
        kill "$SUDO_PID" 2>/dev/null || true
    fi
    exit $exit_code
}
trap cleanup_and_exit EXIT INT TERM

check_privileges() {
    if [ "$EUID" -eq 0 ]; then
        echo -e "${C_RED}${C_BOLD}Error Crítico:${C_RESET} Este script ${C_BOLD}NO${C_RESET} debe ejecutarse como root ni usando 'sudo ./install.sh'."
        echo -e "Ejecútalo con tu usuario normal: ${C_CYAN}./install.sh${C_RESET}"
        echo -e "El instalador te solicitará la contraseña de administrador cuando sea estrictamente necesario."
        exit 1
    fi

    log_info "Solicitando privilegios de superusuario para tareas de administración..."
    sudo -v || { log_error "Autenticación fallida con sudo."; exit 1; }

    # Mantener el token de sudo activo en segundo plano
    while true; do
        sudo -n true
        sleep 50
        kill -0 "$$" || exit
    done 2>/dev/null &
    SUDO_PID=$!
}

# ------------------------------------------------------------------------------
# 5. VALIDACIÓN DEL SISTEMA, KERNEL Y ENTORNO
# ------------------------------------------------------------------------------
validate_system() {
    log_step "Comprobando compatibilidad de la distribución y arquitectura"

    # Arquitectura
    ARCH=$(uname -m)
    if [ "$ARCH" != "x86_64" ]; then
        log_error "Arquitectura '$ARCH' no soportada. Este entorno requiere x86_64."
        exit 1
    fi
    log_success "Arquitectura compatible: $ARCH"

    # Distribución base Arch
    if [ -f /etc/os-release ]; then
        # shellcheck disable=SC1091
        source /etc/os-release
        DISTRO_ID="${ID:-unknown}"
        DISTRO_LIKE="${ID_LIKE:-unknown}"
        DISTRO_NAME="${NAME:-Arch Linux}"

        if [[ "$DISTRO_ID" =~ (arch|cachyos|endeavouros|garuda|blackarch|manjaro|arcolinux) ]] || \
           [[ "$DISTRO_LIKE" =~ arch ]]; then
            log_success "Distribución soportada detectada: ${C_CYAN}$DISTRO_NAME${C_RESET}"
        else
            log_error "Esta distribución ($DISTRO_NAME) no está basada en Arch Linux."
            exit 1
        fi
    else
        log_error "No se pudo identificar la distribución del sistema (/etc/os-release ausente)."
        exit 1
    fi

    # Comprobar si pacman está bloqueado
    if [ -f /var/lib/pacman/db.lck ]; then
        log_warning "Se detectó el archivo de bloqueo /var/lib/pacman/db.lck."
        read -rp " ¿Deseas eliminar el bloqueo de pacman para continuar? [s/N]: " unlock_choice
        if [[ "$unlock_choice" =~ ^[sS]$ ]]; then
            sudo rm -f /var/lib/pacman/db.lck
            log_success "Bloqueo eliminado correctamente."
        else
            log_error "No se puede continuar mientras pacman esté bloqueado por otro proceso."
            exit 1
        fi
    fi

    # Conectividad a Internet
    log_info "Verificando conexión a internet..."
    local test_urls=("https://archlinux.org" "https://1.1.1.1" "https://github.com")
    local connected=false

    for url in "${test_urls[@]}"; do
        if curl -s --head --connect-timeout 4 "$url" &>/dev/null; then
            connected=true
            break
        fi
    done

    if [ "$connected" = true ]; then
        log_success "Conexión a internet verificada y activa."
    else
        log_error "No se detecta conexión a internet. Revisa tus interfaces de red."
        exit 1
    fi
}

# ------------------------------------------------------------------------------
# 6. DETECCIÓN DE HARDWARE Y MÁQUINAS VIRTUALES (OPTIMIZACIÓN DE COMPOSICIÓN)
# ------------------------------------------------------------------------------
detect_hardware_environment() {
    log_step "Analizando hardware y virtualización"

    IS_VM=false
    HYPERVISOR="Bare-Metal"

    if command -v systemd-detect-virt &>/dev/null; then
        VIRT_TYPE=$(systemd-detect-virt)
        if [ "$VIRT_TYPE" != "none" ]; then
            IS_VM=true
            HYPERVISOR="$VIRT_TYPE"
        fi
    elif grep -Eqi "(vmware|virtualbox|qemu|kvm)" /sys/class/dmi/id/product_name 2>/dev/null; then
        IS_VM=true
        HYPERVISOR="DMI-Detected-VM"
    fi

    if [ "$IS_VM" = true ]; then
        log_warning "Entorno virtualizado detectado: ${C_YELLOW}$HYPERVISOR${C_RESET}"
        log_info "Picom se configurará con backend 'xrender' y sin vsync forzado para evitar fallos de OpenGL."
        PICOM_BACKEND="xrender"
        PICOM_VSYNC="false"
    else
        log_success "Instalación en máquina física nativa ($HYPERVISOR)."
        # Chequear GPU
        if lspci -k 2>/dev/null | grep -EA3 -i "vga|3d|display" | grep -iq "nvidia"; then
            log_info "GPU NVIDIA detectada. Ajustando parámetros de composición glx."
            PICOM_BACKEND="glx"
            PICOM_VSYNC="true"
        else
            log_info "GPU Intel/AMD detectada. Ajustando parámetros de composición glx."
            PICOM_BACKEND="glx"
            PICOM_VSYNC="true"
        fi
    fi

    # Detección de Batería (Laptop)
    if [ -d "/sys/class/power_supply" ] && ls -A /sys/class/power_supply | grep -qE "BAT[0-9]|battery"; then
        log_info "Dispositivo portátil (Laptop/Batería) detectado."
        IS_LAPTOP=true
    else
        log_info "Dispositivo de escritorio (Desktop) detectado."
        IS_LAPTOP=false
    fi
}

# ------------------------------------------------------------------------------
# 7. GESTOR DE PAQUETES AUR (YAY / PARU / FALLBACK AUTOMATIZADO)
# ------------------------------------------------------------------------------
setup_aur_manager() {
    log_step "Configuración del Gestor de Paquetes AUR"

    if command -v yay &>/dev/null; then
        AUR_HELPER="yay"
        log_success "AUR Helper localizado: yay"
    elif command -v paru &>/dev/null; then
        AUR_HELPER="paru"
        log_success "AUR Helper localizado: paru"
    elif command -v pikaur &>/dev/null; then
        AUR_HELPER="pikaur"
        log_success "AUR Helper localizado: pikaur"
    else
        log_warning "No se encontró ningún gestor AUR. Procediendo a compilar 'yay-bin'..."

        log_info "Instalando paquetes base para compilación (base-devel, git)..."
        sudo pacman -S --needed --noconfirm base-devel git &>> "$LOG_FILE"

        local TMP_YAY="/tmp/yay-bin-installer-$$"
        rm -rf "$TMP_YAY"
        mkdir -p "$TMP_YAY"

        log_info "Clonando repositorio oficial de yay-bin desde AUR..."
        if git clone https://aur.archlinux.org/yay-bin.git "$TMP_YAY/yay-bin" &>> "$LOG_FILE"; then
            (
                cd "$TMP_YAY/yay-bin" || exit 1
                makepkg -si --noconfirm &>> "$LOG_FILE"
            )
            rm -rf "$TMP_YAY"

            if command -v yay &>/dev/null; then
                AUR_HELPER="yay"
                log_success "yay-bin fue compilado e instalado con éxito."
            else
                log_error "Falló la compilación de yay-bin. Consulta $LOG_FILE"
                exit 1
            fi
        else
            log_error "No se pudo clonar yay-bin desde AUR. Revisa la conectividad a aur.archlinux.org."
            exit 1
        fi
    fi
}

# ------------------------------------------------------------------------------
# 8. MATRIZ DE DEPENDENCIAS DEL SISTEMA
# ------------------------------------------------------------------------------
install_system_packages() {
    log_step "Instalación de Paquetes y Dependencias de Entorno"

    # Actualizar bases de datos
    log_info "Sincronizando repositorios oficiales..."
    sudo pacman -Sy &>> "$LOG_FILE"

    # 1. Dependencias Base y Window Manager
    local CORE_PKGS=(
        bspwm sxhkd polybar rofi picom
        kitty feh dunst libnotify jgmenu
        xclip xdotool xdo xorg-xsetroot xorg-xrandr xorg-xrdb
        xorg-xprop xorg-xdpyinfo xorg-xwininfo xsettingsd
        polkit-gnome lxsession
    )

    # 2. Utilidades de Sistema, Audio y Brillo
    local UTILS_PKGS=(
        brightnessctl pamixer playerctl maim viewnior
        imagemagick jq bc xfce4-power-manager
        xss-lock i3lock htop fastfetch
        zsh zsh-autosuggestions zsh-syntax-highlighting
        xdg-user-dirs xdg-utils
    )

    # 3. Tipografías, Iconos y Temas
    local FONT_PKGS=(
        ttf-jetbrains-mono-nerd
        ttf-font-awesome
        noto-fonts-emoji
        papirus-icon-theme
    )

    # 4. Paquetes desde AUR (Lockscreen gráfico avanzado)
    local AUR_TARGET_PKGS=(
        i3lock-color
        betterlockscreen
    )

    # Instalación de paquetes de Pacman con barra de progreso
    local ALL_OFFICIAL=("${CORE_PKGS[@]}" "${UTILS_PKGS[@]}" "${FONT_PKGS[@]}")
    local total_pkgs=${#ALL_OFFICIAL[@]}
    local current_idx=0
    local failed_packages=()

    log_info "Procesando $total_pkgs dependencias oficiales de Pacman..."

    for pkg in "${ALL_OFFICIAL[@]}"; do
        ((current_idx++))
        printf " [PACMAN] (%2d/%2d) %-30s" "$current_idx" "$total_pkgs" "$pkg"
        
        if pacman -Qi "$pkg" &>/dev/null; then
            echo -e " [ ${C_GREEN}INSTALADO${C_RESET} ]"
        else
            if sudo pacman -S --needed --noconfirm "$pkg" &>> "$LOG_FILE"; then
                echo -e " [   ${C_CYAN}NUEVO${C_RESET}   ]"
            else
                echo -e " [   ${C_RED}FALLÓ${C_RESET}   ]"
                failed_packages+=("$pkg")
            fi
        fi
    done

    # Reintento de fallos en Pacman
    if [ ${#failed_packages[@]} -gt 0 ]; then
        log_warning "Reintentando paquetes que reportaron alertas: ${failed_packages[*]}"
        for fpkg in "${failed_packages[@]}"; do
            sudo pacman -S --needed --noconfirm "$fpkg" &>> "$LOG_FILE" || log_warning "Paquete $fpkg omitido o no disponible en este repositorio."
        done
    fi

    # Instalación de paquetes AUR
    log_info "Instalando paquetes desde AUR con ${AUR_HELPER}..."
    for aur_pkg in "${AUR_TARGET_PKGS[@]}"; do
        printf " [AUR]    Procesando %-30s" "$aur_pkg"
        if pacman -Qi "$aur_pkg" &>/dev/null; then
            echo -e " [ ${C_GREEN}INSTALADO${C_RESET} ]"
        else
            if $AUR_HELPER -S --needed --noconfirm "$aur_pkg" &>> "$LOG_FILE"; then
                echo -e " [   ${C_CYAN}NUEVO${C_RESET}   ]"
            else
                echo -e " [  ${C_YELLOW}AVISO${C_RESET}   ]"
                log_warning "No se pudo compilar $aur_pkg desde AUR. Se utilizará i3lock nativo como respaldo."
            fi
        fi
    done

    # Inicializar directorios estándar XDG
    xdg-user-dirs-update &>> "$LOG_FILE" || true
    log_success "Dependencias del sistema configuradas."
}

# ------------------------------------------------------------------------------
# 9. MOTOR DE RESPALDO Y GENERADOR DE SCRIPT DE RESTAURACIÓN
# ------------------------------------------------------------------------------
perform_backup() {
    log_step "Creación de Copia de Seguridad Preventiva"

    mkdir -p "$TARGET_BACKUP"
    log_info "Directorio de respaldo asignado: ${C_CYAN}$TARGET_BACKUP${C_RESET}"

    local BACKUP_ITEMS=(
        "$HOME/.config/bspwm"
        "$HOME/.config/sxhkd"
        "$HOME/.config/polybar"
        "$HOME/.config/rofi"
        "$HOME/.config/picom"
        "$HOME/.config/kitty"
        "$HOME/.config/dunst"
        "$HOME/.config/jgmenu"
        "$HOME/.zshrc"
        "$HOME/.zprofile"
        "$HOME/.Xresources"
    )

    local backed_count=0
    for item in "${BACKUP_ITEMS[@]}"; do
        if [ -e "$item" ]; then
            cp -rf "$item" "$TARGET_BACKUP/" 2>> "$LOG_FILE"
            ((backed_count++))
            echo " - Respaldado: $(basename "$item")" >> "$LOG_FILE"
        fi
    done

    # Generar script de restauración automática en la carpeta de backup
    cat << EOF > "$TARGET_BACKUP/restore.sh"
#!/usr/bin/env bash
# Script de restauración generado automáticamente por TechOGR Installer
echo "Restaurando archivos de configuración del respaldo: $TIMESTAMP..."
cp -rf "$TARGET_BACKUP"/* "\$HOME/.config/" 2>/dev/null || true
[ -f "$TARGET_BACKUP/.zshrc" ] && cp -f "$TARGET_BACKUP/.zshrc" "\$HOME/"
[ -f "$TARGET_BACKUP/.zprofile" ] && cp -f "$TARGET_BACKUP/.zprofile" "\$HOME/"
[ -f "$TARGET_BACKUP/.Xresources" ] && cp -f "$TARGET_BACKUP/.Xresources" "\$HOME/"
echo "Restauración finalizada exitosamente."
EOF
    chmod +x "$TARGET_BACKUP/restore.sh"

    log_success "Se respaldaron $backed_count elementos. Script 'restore.sh' creado en el directorio de backup."
}

# ------------------------------------------------------------------------------
# 10. DESPLIEGUE DE ARCHIVOS DEL REPOSITORIO
# ------------------------------------------------------------------------------
deploy_dotfiles_repository() {
    log_step "Desplegando Archivos y Configuraciones de TechOGR"

    # Carpetas destino estándar
    mkdir -p "$HOME/.config"
    mkdir -p "$HOME/.local/bin"
    mkdir -p "$HOME/.local/share/fonts"
    mkdir -p "$HOME/Pictures/Wallpapers"

    # 1. Directorio config/
    if [ -d "$SCRIPT_DIR/config" ]; then
        log_info "Copiando carpetas maestras desde config/ a ~/.config/ ..."
        cp -rf "$SCRIPT_DIR/config/"* "$HOME/.config/" 2>> "$LOG_FILE"
    else
        log_warning "No se encontró el directorio 'config' en la raíz del repositorio."
    fi

    # 2. Directorio kitty/ (presente en la raíz del repo)
    if [ -d "$SCRIPT_DIR/kitty" ]; then
        log_info "Configurando Kitty Terminal..."
        mkdir -p "$HOME/.config/kitty"
        cp -rf "$SCRIPT_DIR/kitty/"* "$HOME/.config/kitty/" 2>> "$LOG_FILE"
    fi

    # 3. Directorio home/ (dotfiles de raíz como .zshrc)
    if [ -d "$SCRIPT_DIR/home" ]; then
        log_info "Copiando archivos de usuario desde home/ a $HOME/ ..."
        cp -rf "$SCRIPT_DIR/home/." "$HOME/" 2>> "$LOG_FILE"
    fi

    # 4. Directorio Wallpapers/
    if [ -d "$SCRIPT_DIR/Wallpapers" ]; then
        log_info "Instalando fondos de pantalla en ~/Pictures/Wallpapers/ ..."
        cp -rf "$SCRIPT_DIR/Wallpapers/"* "$HOME/Pictures/Wallpapers/" 2>> "$LOG_FILE"
        # Enlace simbólico de conveniencia
        [ ! -L "$HOME/Wallpapers" ] && ln -sf "$HOME/Pictures/Wallpapers" "$HOME/Wallpapers" 2>/dev/null || true
    fi

    # 5. Directorio misc/ (fuentes, scripts, temas locales)
    if [ -d "$SCRIPT_DIR/misc" ]; then
        log_info "Procesando recursos adicionales (misc)..."
        if [ -d "$SCRIPT_DIR/misc/fonts" ]; then
            cp -rf "$SCRIPT_DIR/misc/fonts/"* "$HOME/.local/share/fonts/" 2>> "$LOG_FILE"
        fi
        if [ -d "$SCRIPT_DIR/misc/bin" ]; then
            cp -rf "$SCRIPT_DIR/misc/bin/"* "$HOME/.local/bin/" 2>> "$LOG_FILE"
        fi
        cp -rf "$SCRIPT_DIR/misc/"* "$HOME/.local/share/" 2>/dev/null || true
    fi

    # 6. Otorgar permisos de ejecución estrictos
    log_info "Asignando permisos de ejecución a scripts del entorno..."
    find "$HOME/.config/bspwm" -type f -exec chmod +x {} + 2>/dev/null || true
    find "$HOME/.config/polybar" -type f \( -name "*.sh" -o -name "launch*" \) -exec chmod +x {} + 2>/dev/null || true
    find "$HOME/.local/bin" -type f -exec chmod +x {} + 2>/dev/null || true
    [ -f "$HOME/.config/sxhkd/sxhkdrc" ] && chmod 644 "$HOME/.config/sxhkd/sxhkdrc"

    # 7. Parches dinámicos de Picom según Hardware/VM
    local PICOM_CONF="$HOME/.config/picom/picom.conf"
    if [ -f "$PICOM_CONF" ]; then
        log_info "Optimizando picom.conf para $HYPERVISOR (backend: $PICOM_BACKEND, vsync: $PICOM_VSYNC)..."
        sed -i "s/backend = .*/backend = \"$PICOM_BACKEND\";/" "$PICOM_CONF" 2>/dev/null || true
        sed -i "s/vsync = .*/vsync = $PICOM_VSYNC;/" "$PICOM_CONF" 2>/dev/null || true
    fi

    # 8. Refrescar caché de fuentes
    log_info "Reconstruyendo caché de tipografías del sistema..."
    fc-cache -fv &>> "$LOG_FILE"

    log_success "Despliegue de archivos completado sin incidentes."
}

# ------------------------------------------------------------------------------
# 11. BLOQUEO DE PANTALLA GRÁFICO LIVIANO Y AUTOMATIZACIÓN
# ------------------------------------------------------------------------------
setup_lockscreen_subsystem() {
    log_step "Configuración del Sistema de Bloqueo Gráfico Liviano"

    # Crear script ejecutable principal: ~/.local/bin/techogr_lock
    local LOCK_BIN="$HOME/.local/bin/techogr_lock"
    cat << 'EOF' > "$LOCK_BIN"
#!/usr/bin/env bash
# Script de Bloqueo Gráfico Liviano con capas de respaldo para BSPWM
# TechOGR Dotfiles

# Colores y estilo
BLUR_RADIUS=0.5
TIME_FORMAT="%I:%M %p"
DATE_FORMAT="%A, %d de %B"

# Capa 1: Betterlockscreen (Elegante con Blur y caché nativo)
if command -v betterlockscreen &>/dev/null; then
    betterlockscreen -l dimblur --time-format "$TIME_FORMAT"
    exit 0
fi

# Capa 2: i3lock-color con UI circular moderna
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

# Capa 3: Fallback de ultra-emergencia con i3lock estándar
if command -v i3lock &>/dev/null; then
    i3lock -c 1a1b26
    exit 0
fi
EOF
    chmod +x "$LOCK_BIN"
    ln -sf "$LOCK_BIN" "$HOME/.local/bin/lockscreen" 2>/dev/null || true

    # Si betterlockscreen está instalado, generar la caché con uno de los fondos
    if command -v betterlockscreen &>/dev/null; then
        local SAMPLE_WALL
        SAMPLE_WALL=$(find "$HOME/Pictures/Wallpapers" -type f \( -name "*.jpg" -o -name "*.png" \) 2>/dev/null | head -n 1)
        if [ -n "$SAMPLE_WALL" ]; then
            log_info "Generando caché gráfico de bloqueo a partir de: $(basename "$SAMPLE_WALL")..."
            betterlockscreen -u "$SAMPLE_WALL" --blur 0.5 &>> "$LOG_FILE" || true
            log_success "Caché de imagen generada para Betterlockscreen."
        fi
    fi

    # Registrar el atajo de bloqueo en sxhkdrc
    local SXHKD_CONF="$HOME/.config/sxhkd/sxhkdrc"
    if [ -f "$SXHKD_CONF" ]; then
        if ! grep -q "techogr_lock" "$SXHKD_CONF" && ! grep -q "betterlockscreen" "$SXHKD_CONF"; then
            log_info "Vinculando atajo de teclado en sxhkdrc (Super + Alt + L)..."
            cat << 'EOF' >> "$SXHKD_CONF"

# ------------------------------------------------------------------------------
# Bloqueo de pantalla gráfico (TechOGR BSPWM)
# ------------------------------------------------------------------------------
super + alt + l
    $HOME/.local/bin/techogr_lock
EOF
        fi
    fi

    # Integrar xss-lock en bspwmrc para suspender o cerrar la tapa de la laptop
    local BSPWMRC="$HOME/.config/bspwm/bspwmrc"
    if [ -f "$BSPWMRC" ]; then
        if ! grep -q "xss-lock" "$BSPWMRC"; then
            log_info "Configurando bloqueo automático en suspensión con xss-lock en bspwmrc..."
            cat << 'EOF' >> "$BSPWMRC"

# Demonio de bloqueo de pantalla automático al suspender
killall -q xss-lock
xss-lock --transfer-sleep-lock -- $HOME/.local/bin/techogr_lock &
EOF
        fi
    fi

    log_success "Sistema de bloqueo configurado y vinculado correctamente."
}

# ------------------------------------------------------------------------------
# 12. CONFIGURACIÓN DEL SHELL PREDETERMINADO (ZSH)
# ------------------------------------------------------------------------------
configure_user_shell() {
    log_step "Verificación del Intérprete de Comandos (Shell)"

    CURRENT_SHELL=$(basename "$SHELL")
    ZSH_BINARY=$(command -v zsh 2>/dev/null || true)

    if [ -n "$ZSH_BINARY" ]; then
        if [ "$CURRENT_SHELL" != "zsh" ]; then
            log_info "Cambiando la shell predeterminada a ZSH ($ZSH_BINARY) para $USER..."
            
            # Asegurar que esté en /etc/shells
            if ! grep -Fxq "$ZSH_BINARY" /etc/shells; then
                echo "$ZSH_BINARY" | sudo tee -a /etc/shells >/dev/null
            fi

            # Cambiar shell de forma silenciosa
            sudo chsh -s "$ZSH_BINARY" "$USER" &>> "$LOG_FILE" || chsh -s "$ZSH_BINARY" &>> "$LOG_FILE" || true
            log_success "Shell predeterminada cambiada a ZSH."
        else
            log_success "ZSH ya es la shell predeterminada del usuario."
        fi
    else
        log_warning "ZSH no fue encontrado. Manteniendo la shell actual ($CURRENT_SHELL)."
    fi
}

# ------------------------------------------------------------------------------
# 13. RESUMEN FINAL Y CHEATSHEET
# ------------------------------------------------------------------------------
display_installation_summary() {
    echo ""
    echo -e "${C_GREEN}${C_BOLD}╔════════════════════════════════════════════════════════════════════╗${C_RESET}"
    echo -e "${C_GREEN}${C_BOLD}║       ¡INSTALACIÓN DE TECHOGR BSPWM COMPLETADA CON ÉXITO!          ║${C_RESET}"
    echo -e "${C_GREEN}${C_BOLD}╚════════════════════════════════════════════════════════════════════╝${C_RESET}"
    echo ""
    echo -e " ${C_CYAN}Resumen del Entorno Instalado:${C_RESET}"
    echo -e "   • Distribución:             ${DISTRO_NAME:-Arch Linux}"
    echo -e "   • Entorno de Hardware:      $HYPERVISOR (Picom: $PICOM_BACKEND)"
    echo -e "   • Gestor AUR:               $AUR_HELPER"
    echo -e "   • Registro de Instalación:  $LOG_FILE"
    echo -e "   • Copia de Seguridad:       $TARGET_BACKUP"
    echo ""
    echo -e " ${C_CYAN}Atajos de Teclado Esenciales:${C_RESET}"
    echo -e "   • ${C_YELLOW}Super + Enter${C_RESET}             Abrir Terminal Kitty"
    echo -e "   • ${C_YELLOW}Super + D${C_RESET}                 Lanzador de Aplicaciones (Rofi)"
    echo -e "   • ${C_YELLOW}Super + Alt + L${C_RESET}           ${C_BOLD}Bloqueo de Pantalla Gráfico${C_RESET}"
    echo -e "   • ${C_YELLOW}Super + Alt + R${C_RESET}           Reiniciar BSPWM y barras"
    echo -e "   • ${C_YELLOW}Super + W / C${C_RESET}             Cerrar Ventana Enfocada"
    echo -e "   • ${C_YELLOW}Super + 1 al 9${C_RESET}            Cambiar de Espacio de Trabajo"
    echo -e "   • ${C_YELLOW}Click Derecho Escritorio${C_RESET}  Menú JGmenu"
    echo ""
    echo -e "${C_YELLOW}${C_BOLD}AVISO IMPORTANTE:${C_RESET}"
    echo -e "Para garantizar que todas las variables XDG, temas de cursor y fuentes se carguen limpiamente,"
    echo -e "se recomienda reiniciar el equipo o cerrar la sesión gráfica actual."
    echo ""
    read -rp " ¿Deseas reiniciar el sistema ahora? [s/N]: " reboot_choice
    if [[ "$reboot_choice" =~ ^[sS]$ ]]; then
        log_info "Reiniciando equipo..."
        sudo reboot
    else
        log_info "Instalación concluida. ¡Disfruta de tu nuevo entorno BSPWM!"
    fi
}

# ------------------------------------------------------------------------------
# 14. ENTRADA PRINCIPAL (MAIN ENTRYPOINT)
# ------------------------------------------------------------------------------
main() {
    print_banner
    check_privileges
    validate_system
    detect_hardware_environment
    setup_aur_manager
    install_system_packages
    perform_backup
    deploy_dotfiles_repository
    setup_lockscreen_subsystem
    configure_user_shell
    display_installation_summary
}

main "$@"
