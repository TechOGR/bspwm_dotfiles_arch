# ─── ❖ ─── bspwm_dotfiles_arch ─── ❖ ───

<p align="center">
  <img src="https://githubusercontent.com" alt="Arch Linux" width="150"/>
</p>

<p align="center">
  <strong>Mis archivos de configuración personal (Dotfiles) para un entorno minimalista y eficiente en Arch Linux.</strong>
</p>

<p align="center">
  <a href="https://github.com"><img src="https://shields.io" alt="Stars"/></a>
  <a href="https://github.com"><img src="https://shields.io" alt="Forks"/></a>
  <img src="https://shields.io" alt="Arch Linux"/>
  <img src="https://shields.io" alt="bspwm"/>
</p>

---

## 💻 Componentes del Entorno

* **Window Manager:** `bspwm` (Tiling Window Manager basado en posiciones binarias)
* **Hotkeys:** `sxhkd` (Gestor de atajos de teclado independiente)
* **Terminal:** `alacritty` / `kitty` (Acelerada por GPU)
* **Shell:** `zsh` + `Oh My Zsh`
* **Barra de Estado:** `polybar`
* **Lanzador de Apps:** `rofi`
* **Compositor:** `picom` (Para transparencias y sombras)

---

## 🚀 Instalación y Uso

Si quieres replicar o usar partes de esta configuración en tu sistema Arch Linux:

### 1. Clonar el repositorio
```bash
git clone git@github.com:TechOGR/bspwm_dotfiles_arch.git
cd bspwm_dotfiles_arch
```

### 2. Copiar configuraciones al sistema
Asegúrate de respaldar tus archivos actuales antes de copiar nada:
```bash
# Ejemplo para copiar la configuración de bspwm y sxhkd
cp -r .config/* ~/.config/
```

---

## ⌨️ Atajos de Teclado Principales (Ajustar al gusto)

| Combinación | Acción |
| :--- | :--- |
| `Super + Enter` | Abrir la terminal |
| `Super + d` | Abrir lanzador de aplicaciones (Rofi) |
| `Super + Alt + q` | Cerrar / Salir de bspwm |
| `Super + {1-9}` | Cambiar de escritorio |
| `Super + q` | Cerrar la ventana enfocada |

---

<p align="center">🛠️ Mantenido con ❤️ por <a href="https://github.com">TechOGR</a></p>
