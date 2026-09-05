# 🛠️ TechOGR BSPWM Dotfiles (Arch Linux)

Mi configuración personalizada para el gestor de ventanas **BSPWM**, optimizada para un flujo de trabajo rápido, estético y minimalista en **Arch Linux**.

---

## 📦 Paquetes y Dependencias

El script de instalación automatizado se encargará de instalar todo lo necesario. Aquí tienes la lista de lo que incluye:

### Gestores de Ventanas y Atajos
* **bspwm**: El gestor de ventanas en mosaico (Tiling Window Manager).
* **sxhkd**: El demonio encargado de gestionar todos los atajos de teclado.

### Entorno y Utilidades Visuales
* **polybar**: La barra de estado superior/inferior altamente personalizable.
* **rofi**: El lanzador de aplicaciones y menú de búsqueda.
* **jgmenu**: El menú que aparece al hacer clic derecho en el escritorio.
* **dunst**: El servidor de notificaciones ligero.
* **picom**: El compositor para añadir transparencias, sombras y animaciones.
* **feh**: Utilidad para gestionar el fondo de pantalla.

### Terminal y Consola
* **kitty**: El emulador de terminal rápido y acelerado por GPU.
* **zsh**: La shell interactiva avanzada.
* **neovim**: El editor de texto moderno basado en Vim.
* **ranger**: El explorador de archivos en terminal.

### Herramientas del Sistema
* **thunar**: El explorador de archivos gráfico (entorno GTK).
* **ueberzug**: Para permitir la previsualización de imágenes dentro de ranger.
* **scrot**: Para realizar capturas de pantalla de manera nativa.
* **xclip**: Herramientas para interactuar con el portapapeles del sistema.
* **brightnessctl**: Control del brillo de la pantalla desde el teclado.
* **xorg-xsetroot** y **libnotify**: Dependencias esenciales del sistema y avisos.

---

## 🚀 Guía de Instalación

El proceso está completamente automatizado a través de un script seguro. Sigue estos sencillos pasos:

### 1. Clonar el repositorio
Abre tu terminal y clona este repositorio en tu máquina:
```bash
git clone https://github.com
cd bspwm_dotfiles_arch
```

### 2. Dar permisos de ejecución
Asegúrate de que el sistema te permita correr el script de instalación:
```bash
chmod +x install.sh
```

### 3. Ejecutar el instalador
Corre el script **sin usar sudo**. El script te pedirá tu contraseña de administrador automáticamente cuando necesite utilizar `pacman` o instalar `yay` si no lo tienes en tu sistema:
```bash
./install.sh
```

> ⚠️ **Nota de seguridad:** El instalador creará automáticamente una copia de respaldo (`backup`) de tus carpetas `.config` y tu archivo `.zshrc` actuales dentro de un directorio con la fecha de hoy en tu `$HOME`. No perderás tus configuraciones previas.

### 4. Reiniciar la sesión
Una vez que el instalador finalice correctamente, cierra tu sesión actual o reinicia tu computadora. En tu gestor de inicio (como SDDM, GDM o LightDM), selecciona la sesión **BSPWM** e ingresa.

---

## ⌨️ Atajos de Teclado Esenciales

La tecla principal (Mod) está configurada por defecto como la tecla Windows (**Super**).

| Combinación | Acción |
| :--- | :--- |
| `Super + Enter` | Abrir la terminal (**Kitty**) |
| `Super + d` | Abrir el lanzador de aplicaciones (**Rofi**) |
| `Super + Alt + r` | Reiniciar BSPWM y recargar configuraciones |
| `Super + Alt + q` | Cerrar sesión / Salir de BSPWM |
| `Super + w` / `c` | Cerrar la ventana actual enfocada |
| `Super + Flechas / HJKL` | Cambiar el foco entre ventanas |
| `Super + 1-9` | Cambiar de espacio de trabajo (Escritorio virtual) |
| `Click Derecho en Escritorio` | Desplegar el menú de aplicaciones (**JGmenu**) |

---
Desarrollado con ☕ por [TechOGR](https://github.com).
