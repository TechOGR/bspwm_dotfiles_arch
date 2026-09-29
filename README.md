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
| Música | `RiceMusic` (`Super + M`): controla lo que suene (YouTube, YouTube Music, Spotify, MPD…), espectro real con 7 estilos y ecualizador de 10 bandas para todo el sonido · widget `MusicPlayer` · `ncmpcpp` en el color del tema |
| Archivos / documentos | `yazi`, `zathura` |
| Portapapeles | `clipcat` |
| Bloqueo de pantalla | `ScreenLocker` (rápido) y `betterlockscreen` con tarjeta de login + avatar (`BetterLock`, editable en RiceEditor → Login Lock), auto-bloqueo con `xss-lock` |
| Navegador | `Brave` (predeterminado del sistema tras la instalación) |
| Fuentes / iconos | JetBrainsMono Nerd Font, Font Awesome, Papirus |

Todo se despliega desde este repositorio: el instalador **no clona ni copia archivos de ningún otro repositorio de dotfiles**.

---

## 🚀 Instalación

Requisitos: una distribución basada en Arch Linux (x86_64), conexión a internet y un usuario normal con `sudo`. Sirve igual en un equipo físico que en una máquina virtual (VMware, VirtualBox, QEMU/KVM, Hyper-V), y también desde un Arch mínimo recién instalado, sin escritorio.

```bash
git clone https://github.com/TechOGR/bspwm_dotfiles_arch.git
cd bspwm_dotfiles_arch
./install.sh
```

- Ejecútalo **sin `sudo`**: pide tu contraseña una sola vez y la mantiene activa hasta el final.
- Antes de empezar muestra tu equipo (sistema, GPU, VM o físico, batería, wifi, bluetooth) y te deja **elegir qué instalar** (login, música, herramientas, bóveda de contraseñas, Brave...) con las flechas y la barra espaciadora.
- Actualiza las llaves de firma y todo el sistema antes de instalar nada (evita las actualizaciones parciales y los conflictos de archivos).
- Decide solo qué paquetes vienen de los repositorios y cuáles de AUR (cambia entre Arch, CachyOS, EndeavourOS...) e instala `yay` si no tienes `yay`/`paru`.
- Detecta el hardware e instala lo que corresponde: microcódigo, mesa/vulkan, NVIDIA (rama correcta según la tarjeta; `chwd` en CachyOS), PipeWire, herramientas del invitado en máquinas virtuales, touchpad y energía en portátiles.
- Respalda tu configuración en `~/.dotfiles_backup/backup_<fecha>/` (con `restore.sh`) y, si reinstalas, **conserva tus ajustes del rice** (tema, fondos por tema, avatar, dock, barra).
- Si algo falla te muestra el error real con una pista de cómo arreglarlo y te deja **reintentar, saltar o parar**.
- Al final comprueba que todo esté en su sitio y guarda un registro completo en `~/.cache/techogr-install/`.

| Opción | Qué hace |
| :--- | :--- |
| `./install.sh --yes` | Sin preguntas: las opciones recomendadas |
| `./install.sh --deploy-only` | Solo copia el rice (sin paquetes ni cambios en el sistema) |
| `./install.sh --doctor` | Solo comprueba que todo lo que el rice necesita está instalado |
| `./install.sh --demo` | Una simulación para ver el instalador (no toca nada) |

Al terminar, reinicia y entra en la sesión **BSPWM** (o escribe `startx` si no usas pantalla de inicio).

> Para volver a tu configuración anterior: `~/.dotfiles_backup/backup_<fecha>/restore.sh`

---

## ⌨️ Atajos de teclado esenciales

La tecla principal (**Mod**) es **Super** (tecla Windows).

| Combinación | Acción |
| :--- | :--- |
| `Alt + F1` | Mostrar ayuda de atajos |
| `Super + Enter` | Abrir terminal |
| `Super + Alt + Enter` | Abrir terminal flotante |
| `Super + Space` | Lanzador de aplicaciones (Rofi) |
| `Alt + Space` | Cambiar de tema al momento, sin abrir RiceEditor |
| `Super + Alt + M` | Explorador/activador de módulos de la barra |
| `Super + R` | Editor del rice |
| `Super + Alt + T` | Selector de terminal |
| `Super + Alt + W` | Selector de wallpaper |
| `Super + Alt + S` | Captura de pantalla |
| `Super + Alt + P` | Menú de energía |
| `Super + Alt + C` | Historial del portapapeles |
| `Super + Alt + H` / `U` | Ocultar / mostrar la barra |
| `Super + X` / `Super + Shift + X` | Cerrar / matar la ventana enfocada |
| `Ctrl + arrastrar desde un borde` | Redimensionar la ventana (flotante o en mosaico) |
| `Alt + Tab` | Cambiar entre ventanas |
| `Super + ← / →` | Cambiar de escritorio |
| `Super + [1-9,0]` | Ir al escritorio N |
| `Super + Ctrl + [1-9,0]` | Enviar ventana al escritorio N |
| `Super + Alt + ← ↓ ↑ →` | Mover el foco entre ventanas |
| `Super + Alt + R` | Recargar BSPWM |
| `Ctrl + Super + Alt + Q` | Cerrar sesión |
| `Super + Shift + L` | Bloquear la pantalla (el estilo se elige en RiceEditor → Lockscreen) |
| `Click derecho en el escritorio` | Menú de aplicaciones (JGmenu) |

Atajos completos y personalizables en [`config/bspwm/config/sxhkdrc`](config/bspwm/config/sxhkdrc).

---

<p align="center"><sub>Desarrollado por <a href="https://github.com/TechOGR">TechOGR</a></sub></p>
