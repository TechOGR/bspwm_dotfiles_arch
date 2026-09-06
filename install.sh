#!/usr/bin/env bash
# ==============================================================================
# Script de Instalación Automatizado - TechOGR BSPWM Dotfiles
# Compatible con: Arch Linux, CachyOS, EndeavourOS, Garuda, BlackArch, Manjaro, etc.
# ==============================================================================

set -o pipefail

# ----------------- Colores y Estilos -----------------
C_RESET="\e[0m"
C_BOLD="\e[1m"
C_RED="\e[31m"
C_GREEN="\e[32m"
C_YELLOW="\e[33m"
C_BLUE="\e[34m"
C_MAGENTA="\e[35m"
C_CYAN="\e[36m"

# ----------------- Funciones de Impresión -----------------
print_banner() {
    clear
    echo -e "${C_CYAN}${C_BOLD}"
    cat << "EOF"
  _______        _        ____   _____ _____  
 |__   __|      | |      / __ \ / ____|  __ \ 
    | | ___  ___| |__   | |  | | |  __| |__) |
    | |/ _ \/ __| '_ \  | |  | | | |_ |  _  / 
    | |  __/ (__| | | | | |__| | |__| | | \ \ 
    |_|\___|\___|_| |_|  \____/ \_____|_|  \_\
          BSPWM Setup Installer - Arch Linux & Derivatives
EOF
    echo -e "${C_RESET}"
}

msg_info()    { echo -e " ${C_BLUE}${C_BOLD}[*]${C_RESET} ${C_BOLD}$1${C_RESET}"; }
msg_ok()      { echo -e " ${C_GREEN}${C_BOLD}[✓]${C_RESET} ${C_BOLD}$1${C_RESET}"; }
msg_warn()    { echo -e " ${C_YELLOW}${C_BOLD}[!]${C_RESET} ${C_YELLOW}$1${C_RESET}"; }
msg_err()     { echo -e " ${C_RED}${C_BOLD}[✗]${C_RESET} ${C_RED}$1${C_RESET}"; }

# ----------------- Verificaciones Iniciales -----------------
check_environment() {
    # 1. No ejecutar como root
    if [ "$EUID" -eq 0 ]; then
        msg_err "Por favor, NO ejecutes este instalador como root o usando sudo."
        echo -e "   Ejecútalo como tu usuario habitual: ${C_CYAN}./install.sh${C_RESET}"
        exit 1
    fi

    # 2. Verificar que sea Arch o basado en Arch
    if [ ! -f /etc/arch-release ] && ! grep -qi "arch" /etc/os-release 2>/dev/null; then
        msg_err "Este script está optimizado exclusivamente para distribuciones basadas en Arch Linux."
        msg_warn "Distribuciones compatibles: Arch, CachyOS, EndeavourOS, Garuda, BlackArch, Manjaro, etc."
        exit 1
    fi

    # 3. Mantener privilegios sudo activos
    msg_info "Comprobando permisos de administrador..."
    sudo -v || { msg_err "Se requieren permisos de sudo para instalar dependencias."; exit 1; }
    while true; do
        sudo -n true
        sleep 60
        kill -0 "$$" || exit
    done 2>/dev/null &
}

# ----------------- Detección / Instalación de AUR Helper -----------------
setup_aur_helper() {
    msg_info "Detectando gestor de paquetes AUR..."
    if command -v yay &>/dev/null; then
        AUR_HELPER="yay"
        msg_ok "AUR Helper detectado: yay"
    elif command -v paru &>/dev/null; then
        AUR_HELPER="paru"
        msg_ok "AUR Helper detectado: paru"
    else
        msg_warn "No se encontró ningún AUR helper. Instalando yay-bin automáticamente..."
        sudo pacman -S --needed --noconfirm base-devel git || true
        
        local TEMP_DIR
        TEMP_DIR=$(mktemp -d)
        git clone https://aur.archlinux.org/yay-bin.git "$TEMP_DIR/yay-bin"
        (cd "$TEMP_DIR/yay-bin" && makepkg -si --noconfirm)
        rm -rf "$TEMP_DIR"

        if command -v yay &>/dev/null; then
            AUR_HELPER="yay"
            msg_ok "yay-bin se instaló con éxito."
        else
            msg_err "No se pudo compilar yay-bin. Verifica tu conexión a internet o base-devel."
            exit 1
        fi
    fi
}

# ----------------- Instalación de Paquetes -----------------
install_dependencies() {
    msg_info "Actualizando base de datos de repositorios..."
    sudo pacman -Sy

    # Dependencias oficiales
    local PACMAN_PKGS=(
        base-devel git curl wget
        bspwm sxhkd polybar rofi picom
        kitty feh dunst libnotify jgmenu
        xclip xdotool xdo xorg-xsetroot xorg-xrandr xorg-xrdb xorg-xprop xorg-xdpyinfo xsettingsd
        polkit-gnome brightnessctl pamixer playerctl maim viewnior imagemagick jq bc
        zsh zsh-autosuggestions zsh-syntax-highlighting fastfetch
        ttf-jetbrains-mono-nerd ttf-font-awesome noto-fonts-emoji papirus-icon-theme
        xss-lock i3lock
    )

    # Paquetes desde AUR (incluyendo el bloqueo de pantalla estético y ligero)
    local AUR_PKGS=(
        i3lock-color
        betterlockscreen
    )

    msg_info "Instalando paquetes desde repositorios oficiales..."
    local failed_pacman=()
    for pkg in "${PACMAN_PKGS[@]}"; do
        if ! sudo pacman -S --noconfirm --needed "$pkg" &>/dev/null; then
            failed_pacman+=("$pkg")
        fi
    done

    # Reintento de paquetes fallidos
    if [ ${#failed_pacman[@]} -gt 0 ]; then
        msg_warn "Reintentando instalar paquetes con advertencias: ${failed_pacman[*]}"
        for pkg in "${failed_pacman[@]}"; do
            sudo pacman -S --noconfirm --needed "$pkg" || true
        done
    fi

    msg_info "Instalando componentes AUR (Lockscreen gráfico y utilidades)..."
    for pkg in "${AUR_PKGS[@]}"; do
        $AUR_HELPER -S --noconfirm --needed "$pkg" || {
            msg_warn "No se pudo compilar $pkg directamente desde AUR. Se utilizará i3lock como alternativa estable."
        }
    done

    msg_ok "Dependencias de sistema procesadas."
}

# ----------------- Copia de Seguridad -----------------
backup_configs() {
    local DATE_NOW
    DATE_NOW=$(date +%Y%m%d_%H%M%S)
    local BACKUP_DIR="$HOME/.dotfiles_backup/backup_$DATE_NOW"

    msg_info "Creando copia de seguridad de configuraciones previas en:"
    echo -e "   ${C_CYAN}$BACKUP_DIR${C_RESET}"
    mkdir -p "$BACKUP_DIR"

    local TARGETS=(
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

    for item in "${TARGETS[@]}"; do
        if [ -e "$item" ]; then
            cp -r "$item" "$BACKUP_DIR/" 2>/dev/null || true
        fi
    done

    msg_ok "Copia de seguridad completada."
}

# ----------------- Despliegue de Archivos del Repositorio -----------------
deploy_dotfiles() {
    local SCRIPT_DIR
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    msg_info "Desplegando archivos desde: $SCRIPT_DIR"

    mkdir -p "$HOME/.config" "$HOME/.local/bin" "$HOME/.local/share/fonts" "$HOME/Pictures/Wallpapers"

    # 1. Copiar carpeta 'config' a ~/.config
    if [ -d "$SCRIPT_DIR/config" ]; then
        msg_info "Copiando carpetas de ~/.config/ ..."
        cp -rf "$SCRIPT_DIR/config/"* "$HOME/.config/"
    fi

    # 2. Copiar carpeta 'kitty' a ~/.config/kitty
    if [ -d "$SCRIPT_DIR/kitty" ]; then
        msg_info "Instalando configuración de Kitty..."
        mkdir -p "$HOME/.config/kitty"
        cp -rf "$SCRIPT_DIR/kitty/"* "$HOME/.config/kitty/"
    fi

    # 3. Copiar carpeta 'home' a $HOME (incluyendo dotfiles ocultos como .zshrc)
    if [ -d "$SCRIPT_DIR/home" ]; then
        msg_info "Copiando archivos a $HOME ..."
        cp -rf "$SCRIPT_DIR/home/." "$HOME/"
    fi

    # 4. Copiar Wallpapers
    if [ -d "$SCRIPT_DIR/Wallpapers" ]; then
        msg_info "Copiando fondos de pantalla a ~/Pictures/Wallpapers/ ..."
        cp -rf "$SCRIPT_DIR/Wallpapers/"* "$HOME/Pictures/Wallpapers/"
    fi

    # 5. Copiar misc (fonts, scripts, temas)
    if [ -d "$SCRIPT_DIR/misc" ]; then
        msg_info "Procesando carpeta misc..."
        if [ -d "$SCRIPT_DIR/misc/fonts" ]; then
            cp -rf "$SCRIPT_DIR/misc/fonts/"* "$HOME/.local/share/fonts/"
        fi
        if [ -d "$SCRIPT_DIR/misc/bin" ]; then
            cp -rf "$SCRIPT_DIR/misc/bin/"* "$HOME/.local/bin/"
        fi
        cp -rf "$SCRIPT_DIR/misc/"* "$HOME/.local/share/" 2>/dev/null || true
    fi

    # 6. Permisos de ejecución
    msg_info "Otorgando permisos de ejecución a scripts y configuraciones..."
    [ -d "$HOME/.config/bspwm" ]   && chmod -R +x "$HOME/.config/bspwm" 2>/dev/null || true
    [ -d "$HOME/.config/polybar" ] && chmod -R +x "$HOME/.config/polybar" 2>/dev/null || true
    [ -d "$HOME/.config/sxhkd" ]   && chmod -R +x "$HOME/.config/sxhkd" 2>/dev/null || true
    [ -d "$HOME/.local/bin" ]      && chmod -R +x "$HOME/.local/bin" 2>/dev/null || true

    # 7. Actualizar caché de fuentes
    msg_info "Actualizando caché de fuentes del sistema..."
    fc-cache -fv &>/dev/null

    msg_ok "Archivos de configuración y temas aplicados exitosamente."
}

# ----------------- Configuración del Bloqueo de Pantalla -----------------
setup_lockscreen() {
    msg_info "Configurando bloqueo de pantalla gráfico y ultraligero..."

    # Crear script envoltorio en ~/.local/bin/lockscreen
    cat << 'EOF' > "$HOME/.local/bin/lockscreen"
#!/usr/bin/env bash
# Lockscreen script universal
if command -v betterlockscreen &>/dev/null; then
    betterlockscreen -l dimblur --time-format "%I:%M %p"
elif command -v i3lock-color &>/dev/null; then
    i3lock-color --clock --indicator --time-str="%H:%M:%S" --date-str="%A, %d %B" --inside-color=00000088 --ring-color=7aa2f7ff --keyhl-color=bb9af7ff --line-uses-inside
else
    i3lock -c 1a1b26
fi
EOF
    chmod +x "$HOME/.local/bin/lockscreen"

    # Si se instaló betterlockscreen y hay wallpapers, generar caché inicial de blur
    if command -v betterlockscreen &>/dev/null; then
        local WP_SAMPLE
        WP_SAMPLE=$(find "$HOME/Pictures/Wallpapers" -type f \( -name "*.jpg" -o -name "*.png" \) 2>/dev/null | head -n 1)
        if [ -n "$WP_SAMPLE" ]; then
            msg_info "Generando caché gráfico de bloqueo con: $(basename "$WP_SAMPLE")"
            betterlockscreen -u "$WP_SAMPLE" --blur 0.5 &>/dev/null || true
        fi
    fi

    # Asegurar el atajo de bloqueo en sxhkdrc si no está presente
    local SXHKD_CONF="$HOME/.config/sxhkd/sxhkdrc"
    if [ -f "$SXHKD_CONF" ]; then
        if ! grep -q "lockscreen" "$SXHKD_CONF" && ! grep -q "betterlockscreen" "$SXHKD_CONF"; then
            cat << 'EOF' >> "$SXHKD_CONF"

# Lock screen (TechOGR Setup)
super + alt + l
    $HOME/.local/bin/lockscreen
EOF
            msg_ok "Atajo 'Super + Alt + L' configurado en sxhkdrc para bloquear la pantalla."
        fi
    fi

    # Configurar xss-lock en bspwmrc para suspender/cerrar tapa de laptop
    local BSPWMRC="$HOME/.config/bspwm/bspwmrc"
    if [ -f "$BSPWMRC" ]; then
        if ! grep -q "xss-lock" "$BSPWMRC"; then
            sed -i '/xsetroot/a xss-lock --transfer-sleep-lock -- $HOME/.local/bin/lockscreen &' "$BSPWMRC" 2>/dev/null || \
            echo -e "\nxss-lock --transfer-sleep-lock -- \$HOME/.local/bin/lockscreen &" >> "$BSPWMRC"
            msg_ok "Bloqueo automático en suspensión configurado con xss-lock."
        fi
    fi
}

# ----------------- Configuración de Shell (Zsh) -----------------
setup_shell() {
    local USER_SHELL
    USER_SHELL=$(basename "$SHELL")

    if [ "$USER_SHELL" != "zsh" ]; then
        if command -v zsh &>/dev/null; then
            msg_info "Cambiando shell por defecto a ZSH para el usuario: $USER..."
            local ZSH_PATH
            ZSH_PATH=$(which zsh)
            sudo chsh -s "$ZSH_PATH" "$USER" || chsh -s "$ZSH_PATH" || true
            msg_ok "Shell predeterminada cambiada a ZSH."
        fi
    fi
}

# ----------------- Flujo Principal -----------------
main() {
    print_banner
    check_environment
    setup_aur_helper
    install_dependencies
    backup_configs
    deploy_dotfiles
    setup_lockscreen
    setup_shell

    echo ""
    echo -e "${C_GREEN}${C_BOLD}======================================================${C_RESET}"
    echo -e "${C_GREEN}${C_BOLD}  ¡Instalación de TechOGR BSPWM completada con éxito! ${C_RESET}"
    echo -e "${C_GREEN}${C_BOLD}======================================================${C_RESET}"
    echo -e " ${C_CYAN}• Atajo Bloqueo de pantalla:${C_RESET} Super + Alt + L"
    echo -e " ${C_CYAN}• Terminal (Kitty):${C_RESET}          Super + Enter"
    echo -e " ${C_CYAN}• Lanzador (Rofi):${C_RESET}           Super + D"
    echo -e " ${C_CYAN}• Menú (JGmenu):${C_RESET}             Click derecho en el fondo"
    echo ""
    echo -e "${C_YELLOW}${C_BOLD}Te recomendamos cerrar sesión o reiniciar el sistema para disfrutar del nuevo entorno.${C_RESET}"
    echo ""
}

main "$@"
