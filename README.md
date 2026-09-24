# TechOGR · BSPWM Dotfiles

Configuración personal de escritorio para **BSPWM** sobre **Arch Linux** y derivados (CachyOS, EndeavourOS, Garuda, BlackArch, Manjaro...). Rice `crackone`: HUD cyberpunk/neon animado, con Polybar + Eww, Picom con animaciones y un instalador que deja el sistema listo en un solo comando.

<p align="center">
  <img src="Wallpapers/noche_car_man.jpg" alt="Wallpaper por defecto del rice crackone" width="100%">
  <br>
  <sub>Wallpaper por defecto incluido (<code>noche_car_man.jpg</code>). El instalador lo aplica automáticamente al fondo y al lockscreen.</sub>
</p>

---

## ✨ Qué incluye

| Categoría | Herramientas |
| :--- | :--- |
| Gestor de ventanas | `bspwm` + `sxhkd` |
| Barra / widgets | `polybar`, `eww` (perfil, módulos animados) |
| Compositor | `picom` con animaciones |
| Fondos de video | `VideoWall` (mpv): videos de `rices/<rice>/walls/videos`, pausa automática bajo ventanas, también de fondo en el login lock — RiceEditor → Wallpaper |
| Lanzador / menús | `rofi`, `jgmenu` |
| Notificaciones | `dunst` |
| Terminales | `alacritty` (por defecto), `kitty`, `st`, `ghostty` — selector con `Super+Alt+T` |
| Shell | `zsh` + autosugerencias, resaltado de sintaxis, `fzf`/`fzf-tab` |
| Multimedia | `mpd`, `ncmpcpp`, `mpv`, control de volumen/brillo/reproducción |
| Archivos / documentos | `yazi`, `zathura` |
| Portapapeles | `clipcat` |
| Bloqueo de pantalla | `ScreenLocker` (rápido) y `betterlockscreen` con tarjeta de login + avatar (`BetterLock`, editable en RiceEditor → Login Lock), auto-bloqueo con `xss-lock` |
| Navegador | `Brave` (predeterminado del sistema tras la instalación) |
| Fuentes / iconos | JetBrainsMono Nerd Font, Font Awesome, Papirus |

Todo se despliega desde este repositorio: el instalador **no clona ni copia archivos de ningún otro repositorio de dotfiles**.

---

## 🚀 Instalación

Requisitos: una distribución basada en Arch Linux (x86_64), conexión a internet y un usuario normal con acceso a `sudo`.

```bash
git clone https://github.com/TechOGR/bspwm_dotfiles_arch.git
cd bspwm_dotfiles_arch
chmod +x install.sh
./install.sh
```

- Ejecuta el script **sin `sudo`**; te pedirá la contraseña automáticamente cuando la necesite.
- Antes de tocar nada, sincroniza y actualiza todo el sistema (`pacman -Syu`) para evitar conflictos de archivos entre paquetes (por ejemplo entre librerías compartidas como `ffmpeg`/`vmaf`).
- Instala `yay` si no tienes ya `yay`/`paru`, prepara Rust estable para compilar Eww si hace falta, y resuelve automáticamente cualquier paquete que quede en conflicto reintentando la instalación.
- Antes de desplegar nada crea un **backup** completo de tu `~/.config` actual y tu `.zshrc` en `~/.dotfiles_backup/backup_<fecha>/`, con un script `restore.sh` listo para revertir todo.
- Registra la sesión **BSPWM** en tu Display Manager (instala LightDM si no tienes ninguno activo) y deja tu shell en Zsh.
- Guarda un log detallado de todo el proceso en `~/.techogr_install.log`, útil para depurar si algo falla.

Al terminar, cierra sesión (o reinicia) y selecciona **BSPWM** en la pantalla de inicio.

> Para restaurar tu configuración anterior en cualquier momento: `~/.dotfiles_backup/backup_<fecha>/restore.sh`

---

## ⌨️ Atajos de teclado esenciales

La tecla principal (**Mod**) es **Super** (tecla Windows).

| Combinación | Acción |
| :--- | :--- |
| `Alt + F1` | Mostrar ayuda de atajos |
| `Super + Enter` | Abrir terminal |
| `Super + Alt + Enter` | Abrir terminal flotante |
| `Super + Space` | Lanzador de aplicaciones (Rofi) |
| `Alt + Space` | Selector de rice (tema completo bspwm/polybar/eww) |
| `Super + Alt + M` | Explorador/activador de módulos de la barra |
| `Super + R` | Editor del rice |
| `Super + Alt + T` | Selector de terminal |
| `Super + Alt + W` | Selector de wallpaper |
| `Super + Alt + S` | Captura de pantalla |
| `Super + Alt + P` | Menú de energía |
| `Super + Alt + C` | Historial del portapapeles |
| `Super + Alt + H` / `U` | Ocultar / mostrar la barra |
| `Super + X` / `Super + Shift + X` | Cerrar / matar la ventana enfocada |
| `Alt + Tab` | Cambiar entre ventanas |
| `Super + ← / →` | Cambiar de escritorio |
| `Super + [1-9,0]` | Ir al escritorio N |
| `Super + Ctrl + [1-9,0]` | Enviar ventana al escritorio N |
| `Super + Alt + ← ↓ ↑ →` | Mover el foco entre ventanas |
| `Super + Alt + R` | Recargar BSPWM |
| `Ctrl + Super + Alt + Q` | Cerrar sesión |
| `Ctrl + Super + Alt + L` / `Super + Shift + S` | Bloquear pantalla (ScreenLocker) |
| `Super + Shift + L` | Pantalla de login (betterlockscreen · BetterLock) |
| `Click derecho en el escritorio` | Menú de aplicaciones (JGmenu) |

Atajos completos y personalizables en [`config/bspwm/config/sxhkdrc`](config/bspwm/config/sxhkdrc).

---

<p align="center"><sub>Desarrollado por <a href="https://github.com/TechOGR">TechOGR</a></sub></p>
