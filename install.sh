#!/usr/bin/env bash

# Colores para la terminal (Salidas legibles)
VERDE="\e[0;32m"
AZUL="\e[0;34m"
AMARILLO="\e[0;33m"
ROJO="\e[0;31m"
RESET="\e[0m"

echo -e "${AZUL}=================================================="
echo -e "  Instalador de Dotfiles - TechOGR BSPWM (Arch)   "
echo -e "==================================================${RESET}\n"

# 1. Verificar si el script se ejecuta como usuario normal
if [ "$EUID" -eq 0 ]; then
    echo -e "${ROJO}[!] Por favor, no ejecutes este script como root o con sudo.${RESET}"
    exit 1
fi

# 2. Instalar el asistente de AUR (yay) si no existe
if ! command -v yay &> /dev/null; then
    echo -e "${AMARILLO}[*] 'yay' no está instalado. Instalándolo ahora...${RESET}"
    sudo pacman -S --needed --noconfirm base-devel git
    git clone https://aur.archlinux.org/yay.git /tmp/yay
    cd /tmp/yay && makepkg -si --noconfirm
    cd - || exit
fi

# 3. Listas de dependencias basadas en tu ecosistema (bspwm, kitty, polybar, etc.)
DEPENDENCIAS_PACMAN=(
    "bspwm" "sxhkd" "kitty" "polybar" "rofi" "dunst" "picom" 
    "ranger" "thunar" "feh" "zsh" "neovim" "xorg-xsetroot" 
    "libnotify" "ueberzug" "scrot" "xclip" "brightnessctl"
)

DEPENDENCIAS_AUR=(
    "jgmenu"
)

echo -e "${AZUL}[*] Actualizando repositorios e instalando dependencias de Pacman...${RESET}"
sudo pacman -Syu --needed --noconfirm "${DEPENDENCIAS_PACMAN[@]}"

echo -e "${AZUL}[*] Instalando dependencias desde AUR...${RESET}"
yay -S --needed --noconfirm "${DEPENDENCIAS_AUR[@]}"

# 4. Crear respaldos seguros de archivos existentes (.config y .zshrc)
echo -e "${AMARILLO}[*] Creando copias de respaldo de tus configuraciones previas...${RESET}"
RESPALDO_DIR="$HOME/dotfiles_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$RESPALDO_DIR"

[[ -d "$HOME/.config" ]] && cp -r "$HOME/.config" "$RESPALDO_DIR/.config_backup"
[[ -f "$HOME/.zshrc" ]] && cp "$HOME/.zshrc" "$RESPALDO_DIR/.zshrc_backup"
echo -e "${VERDE}[✓] Respaldos guardados de forma segura en: $RESPALDO_DIR${RESET}"

# 5. Desplegar los archivos de tu repositorio
echo -e "${AZUL}[*] Copiando tus configuraciones personalizadas...${RESET}"

# Copiar el contenido de la carpeta config a ~/.config/
if [ -d "config" ]; then
    mkdir -p "$HOME/.config"
    cp -r config/* "$HOME/.config/"
else
    echo -e "${ROJO}[!] No se encontró la carpeta 'config' en el directorio actual.${RESET}"
fi

# Copiar el archivo .zshrc al Home
if [ -f ".zshrc" ]; then
    cp .zshrc "$HOME/.zshrc"
else
    echo -e "${AMARILLO}[!] No se encontró el archivo '.zshrc' en el repositorio.${RESET}"
fi

# 6. Instalación automatizada de fuentes
if [ -d "fonts" ]; then
    echo -e "${AZUL}[*] Instalando fuentes en el sistema...${RESET}"
    mkdir -p "$HOME/.local/share/fonts"
    cp -r fonts/* "$HOME/.local/share/fonts/"
    echo -e "${AZUL}[*] Actualizando la caché de fuentes...${RESET}"
    fc-cache -fv &> /dev/null
    echo -e "${VERDE}[✓] Fuentes instaladas correctamente.${RESET}"
else
    echo -e "${AMARILLO}[!] Advertencia: No se encontró la carpeta 'fonts'. Te recomiendo añadir tus tipografías (ej. JetBrainsMono Nerd Font) al repositorio.${RESET}"
fi

# 7. Cambiar la Shell por defecto a Zsh si no lo está
if [ "$SHELL" != "/usr/bin/zsh" ] && [ "$SHELL" != "/bin/zsh" ]; then
    echo -e "${AMARILLO}[*] Cambiando tu shell predeterminada a Zsh...${RESET}"
    chsh -s "$(which zsh)"
fi

echo -e "\n${VERDE}=================================================="
echo -e "      ¡Instalación completada con éxito!          "
echo -e "  Reinicia tu sesión para ingresar a tu entorno.  "
echo -e "==================================================${RESET}"
