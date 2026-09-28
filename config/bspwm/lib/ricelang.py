# =============================================================
# Author:  TechOGR
# Repo:    https://github.com/TechOGR/bspwm_dotfiles_arch
#
# ricelang - the language of RiceEditor (English / Español). The editor
# is written in English; tr() gives the Spanish of a text shown on screen
# (labels, tooltips, list items, toasts). Unknown texts stay as they are.
# The choice lives in config/editor.json ({"lang": "es"}).
#
# Copyright (C) 2021-2026 TechOGR <https://github.com/TechOGR>
# Licensed under GPL-3.0 license
# =============================================================

import os
import re
import json

CONF = os.path.expanduser('~/.config/bspwm/config/editor.json')
LANGS = [('en', 'English'), ('es', 'Español')]


def get_lang():
    try:
        with open(CONF) as f:
            lang = json.load(f).get('lang', 'en')
        return lang if lang in dict(LANGS) else 'en'
    except (OSError, ValueError):
        return 'en'


def set_lang(lang):
    try:
        with open(CONF) as f:
            conf = json.load(f)
    except (OSError, ValueError):
        conf = {}
    conf['lang'] = lang
    tmp = CONF + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(conf, f, indent=2)
    os.replace(tmp, CONF)


ES = {
    # ── sections
    'Dashboard': 'Panel', 'Themes': 'Temas', 'Palette': 'Paleta', 'Windows': 'Ventanas', 'Display': 'Pantalla',
    'Compositor': 'Compositor', 'Terminal': 'Terminal', 'Wallpaper': 'Fondo', 'Dock': 'Dock', 'Polybar': 'Polybar',
    'Notifications': 'Notificaciones', 'Lockscreen': 'Bloqueo rápido', 'Login Lock': 'Bloqueo de inicio',
    'Appearance': 'Apariencia', 'Snapshots': 'Instantáneas', 'Help': 'Ayuda',
    'SYSTEM OVERVIEW': 'RESUMEN DEL SISTEMA', 'QUICK ACTIONS': 'ACCIONES RÁPIDAS',
    'WHOLE-RICE THEMES': 'TEMAS COMPLETOS', 'APPLY EVERYTHING OR BY PARTS': 'APLICA TODO O POR PARTES',
    'COLOR SCHEMES OF THE RICE': 'ESQUEMAS DE COLOR DEL RICE', 'APPLIED INSTANTLY': 'SE APLICAN AL INSTANTE',
    'BSPWM': 'BSPWM', 'BORDERS': 'BORDES', 'GAPS': 'ESPACIOS', 'BEHAVIOUR': 'COMPORTAMIENTO',
    'RESOLUTION': 'RESOLUCIÓN', 'REFRESH': 'FRECUENCIA', 'ROTATION': 'ROTACIÓN', 'MONITORS': 'MONITORES',
    'NIGHT LIGHT': 'LUZ NOCTURNA', 'PICOM': 'PICOM', 'CORNERS': 'ESQUINAS', 'SHADOWS': 'SOMBRAS', 'BLUR': 'DESENFOQUE',
    'OPACITY': 'OPACIDAD', 'SHELL': 'SHELL', 'ENGINE': 'MOTOR', 'GALLERY': 'GALERÍA', '3D SELECTOR': 'SELECTOR 3D',
    'PINNED APPS': 'APPS FIJADAS', 'SIZE': 'TAMAÑO', 'THEMES': 'TEMAS', 'STYLE': 'ESTILO', 'MODULES': 'MÓDULOS',
    'AUTO-HIDE': 'AUTO-OCULTAR', 'DUNST': 'DUNST', 'PLACEMENT': 'POSICIÓN', 'MOTION': 'MOVIMIENTO',
    'QUICK LOCK': 'BLOQUEO RÁPIDO', 'AVATAR CARD': 'TARJETA CON AVATAR', 'AUTO-LOCK': 'AUTO-BLOQUEO',
    'ICONS': 'ICONOS', 'CURSOR': 'CURSOR', 'ROFI': 'ROFI', 'SAVE': 'GUARDA', 'RESTORE THE WHOLE RICE STATE':
    'RESTAURA TODO EL ESTADO DEL RICE', 'SHORTCUTS': 'ATAJOS', 'HOW IT WORKS': 'CÓMO FUNCIONA',
    'LIVE MODE — every change is applied and saved instantly':
        'MODO EN VIVO — cada cambio se aplica y se guarda al instante',

    # ── card titles
    'QUICK ACTIONS ': 'ACCIONES RÁPIDAS', 'CURRENT RICE': 'RICE ACTUAL', 'ON SCREEN': 'EN PANTALLA',
    'NOW ON SCREEN': 'AHORA EN PANTALLA', 'COLOR SCHEMES': 'ESQUEMAS DE COLOR', 'APPLY A PALETTE TO': 'APLICAR UNA PALETA A',
    'WINDOW STYLE': 'ESTILO DE VENTANA', 'GAPS & PADDING': 'ESPACIOS Y MÁRGENES', 'WINDOW FRAMES': 'MARCOS DE VENTANA',
    'SCREENS': 'PANTALLAS', 'OUTPUT': 'SALIDA', 'COLOR': 'COLOR', 'CUSTOM RESOLUTION': 'RESOLUCIÓN PERSONALIZADA',
    'POWER & DPI': 'ENERGÍA Y DPI', 'BOOT & LOGIN SCREEN': 'ARRANQUE Y PANTALLA DE LOGIN', 'PERFORMANCE': 'RENDIMIENTO',
    'CORNERS & OPACITY': 'ESQUINAS Y OPACIDAD', 'BLUR & FADING': 'DESENFOQUE Y FUNDIDO', 'ANIMATIONS': 'ANIMACIONES',
    'LIVE PREVIEW': 'VISTA PREVIA', 'FONT': 'FUENTE', 'ENGINE ': 'MOTOR', 'GALLERY ': 'GALERÍA',
    'VIDEO WALLPAPERS': 'FONDOS DE VÍDEO', 'ADD APPS': 'AÑADIR APPS', 'BAR STYLE': 'ESTILO DE BARRA',
    'WORKSPACE STYLE': 'ESTILO DE WORKSPACES', 'LOOK': 'ASPECTO', 'ADD A MODULE': 'AÑADIR UN MÓDULO',
    'PREVIEW': 'VISTA PREVIA', 'CLOCK & RING': 'RELOJ Y ANILLO', 'CLOCK, RING & COLORS': 'RELOJ, ANILLO Y COLORES',
    'BACKGROUND': 'FONDO', 'LOGIN CARD': 'TARJETA DE LOGIN', 'AUTO-LOCK ': 'AUTO-BLOQUEO', 'PROFILE PICTURE': 'FOTO DE PERFIL',
    'SAVE STATE': 'GUARDAR ESTADO', 'TIMELINE': 'HISTORIAL', 'APPLY': 'APLICAR', 'LANGUAGE': 'IDIOMA',
    'RESOLUTION ': 'RESOLUCIÓN', 'SYSTEM': 'SISTEMA', 'GTK': 'GTK', 'MENUS': 'MENÚS',

    # ── dashboard
    'lock screen now': 'bloquear ahora', 'save rice state': 'guardar estado del rice', 'app launcher': 'lanzador de apps',
    'Soft reload': 'Recarga suave', 'Rice Editor': 'Rice Editor', 'Lock the screen': 'Bloquear la pantalla',
    'active setup': 'configuración activa', 'wallpaper · effect': 'fondo · efecto',
    'Reload': 'Recargar', 'Rebuild': 'Reconstruir', 'Soft reload: polybar, picom, dunst, sxhkd… (Ctrl+R)':
        'Recarga suave: polybar, picom, dunst, sxhkd… (Ctrl+R)', 'Re-apply the whole rice (Theme.sh)':
        'Volver a aplicar todo el rice (Theme.sh)',

    # ── themes
    'bar, workspaces, windows and colors in one style': 'barra, workspaces, ventanas y colores en un estilo',
    'pick the parts · a snapshot is saved first': 'elige las partes · antes se guarda una instantánea',
    'Colors': 'Colores', 'Bar': 'Barra', 'Workspaces': 'Workspaces',
    'palette: terminals, rofi, notifications, GTK, lockscreen': 'paleta: terminales, rofi, notificaciones, GTK, bloqueo',
    'polybar drawn in the style': 'polybar dibujada en el estilo', 'the pac-man pill of the bar':
        'la cápsula pac-man de la barra', 'borders, corners, gaps, glow, blur, opacity':
        'bordes, esquinas, espacios, brillo, desenfoque, opacidad',
    'Apply whole theme': 'Aplicar el tema completo', 'Apply selected parts': 'Aplicar las partes elegidas',
    'Everything is re-applied live: bar, windows, terminals, menus':
        'Todo se vuelve a aplicar en vivo: barra, ventanas, terminales, menús',
    'in use': 'en uso', 'Apply': 'Aplicar', 'Pick at least one part': 'Elige al menos una parte',
    'modern and clean': 'moderno y limpio', 'futuristic and striking': 'futurista y llamativo',
    'elegant and discreet': 'elegante y discreto',
    'retro and classic': 'retro y clásico',
    'fluid and original': 'fluido y original', 'tech and professional': 'tecnológico y profesional',
    'intense and different': 'intenso y diferente', 'calm and fresh': 'tranquilo y fresco',
    'hand drawn in graphite': 'dibujado a mano en grafito', 'frosted glass and light': 'vidrio esmerilado y luz',
    'cracked rock and fire': 'roca agrietada y fuego', 'clean neon outline': 'contorno de neón limpio',
    'space, orbits and particles': 'espacio, órbitas y partículas', 'polybar icons, palette colors':
        'iconos de polybar, colores de la paleta',
    'Pencil': 'Lápiz', 'Crystal': 'Cristal', 'Lava': 'Lava', 'Solid Neon': 'Neón sólido', 'Holographic': 'Holográfico',
    'Fire': 'Fuego', 'Nature': 'Naturaleza', 'Liquid': 'Líquido',
    'Storm': 'Tormenta', 'Venom': 'Veneno', 'Butterflies': 'Mariposas', 'Snakes': 'Serpientes',
    'lightning, pure energy': 'rayos, energía pura', 'moving shadows, venom': 'sombras en movimiento, veneno',
    'delicate, free, magic': 'delicado, libre, mágico', 'power, mystery, scales': 'poder, misterio, escamas',

    # ── palette
    'click to apply · the editor re-themes too': 'clic para aplicar · el editor también cambia',
    'the same theme style, in the new colors': 'el mismo estilo del tema, con los nuevos colores',
    'terminals, menus, notifications, GTK, bar text, this editor':
        'terminales, menús, notificaciones, GTK, texto de la barra, este editor',
    'the bar drawn in the theme style, in these colors': 'la barra en el estilo del tema, con estos colores',
    'the pac-man pill': 'la cápsula pac-man', 'Lock screens': 'Pantallas de bloqueo',
    'login lock card and quick lock panel': 'tarjeta del login y panel del bloqueo rápido',
    'Window frames': 'Marcos de ventana', 'the styled frames around windows': 'los marcos con estilo de las ventanas',
    "Theme's own colors": 'Colores propios del tema',
    'Undo the recolor of bar, workspaces, locks and frames':
        'Deshace el recoloreado de barra, workspaces, bloqueos y marcos',
    'Reset': 'Restablecer', "Back to the theme's own colors": 'De vuelta a los colores propios del tema',

    # ── windows
    'borders follow the palette · manual colors below = custom':
        'los bordes siguen la paleta · colores manuales abajo = personalizado',
    'Minimal': 'Mínimo', 'Neon': 'Neón', 'HUD': 'HUD', 'No borders · rounded corners · soft shadow':
        'Sin bordes · esquinas redondeadas · sombra suave',
    '2 px frame that glows on focus · palette colors': 'Marco de 2 px que brilla con el foco · colores de la paleta',
    '1 px sharp frame · square corners · accent glow': 'Marco fino de 1 px · esquinas rectas · brillo de acento',
    'Borders': 'Bordes', 'Border width': 'Grosor del borde', 'Width of the window border': 'Ancho del borde de la ventana',
    'Normal border': 'Borde normal', 'Unfocused windows': 'Ventanas sin foco', 'Focused border': 'Borde con foco',
    'The window with focus': 'La ventana con el foco', 'bspwmrc / theme-config': 'bspwmrc / theme-config',
    'Window gap': 'Espacio entre ventanas', 'Space between tiled windows': 'Separación entre ventanas en mosaico',
    'Screen padding': 'Margen de pantalla', 'Reserved space at each edge (the bar lives in TOP)':
        'Espacio reservado en cada borde (la barra va en TOP)',
    'the theme style around every window': 'el estilo del tema alrededor de cada ventana',
    'Frame style': 'Estilo del marco', 'None (plain border)': 'Ninguno (borde simple)',
    'Liquid glass, leaves, flames, HUD brackets… drawn around each window (unfocused ones dimmed)':
        'Vidrio líquido, hojas, llamas, escuadras HUD… alrededor de cada ventana (las sin foco, atenuadas)',
    'Behaviour': 'Comportamiento', 'Split ratio': 'Proporción de división',
    'Size of the new window when splitting': 'Tamaño de la nueva ventana al dividir',
    'Focus follows pointer': 'El foco sigue al puntero', 'Focus the window under the mouse':
        'Enfoca la ventana bajo el ratón', 'Pointer follows focus': 'El puntero sigue al foco',
    'Warp the mouse to the focused window': 'Lleva el ratón a la ventana enfocada', 'Single monocle': 'Monóculo único',
    'Monocle layout when only one window is open': 'Diseño monóculo cuando solo hay una ventana abierta',
    'Borderless monocle': 'Monóculo sin bordes', 'Remove borders in monocle layout': 'Quita los bordes en monóculo',
    'Gapless monocle': 'Monóculo sin espacios', 'Remove gaps in monocle layout': 'Quita los espacios en monóculo',
    'Automatic scheme': 'Esquema automático', 'Where new windows are inserted': 'Dónde se colocan las ventanas nuevas',
    'longest side': 'lado más largo', 'alternate': 'alterno', 'spiral': 'espiral',

    # ── display
    'click a screen to edit it · xrandr': 'clic en una pantalla para editarla · xrandr', 'Detect': 'Detectar',
    'Identify': 'Identificar', 'Automatic': 'Automático', 'Re-read the connected screens': 'Vuelve a leer las pantallas conectadas',
    "Show each screen's name on it": 'Muestra el nombre de cada pantalla sobre ella',
    'Forget the saved layout: preferred mode of every screen (MonitorSetup)':
        'Olvida la disposición guardada: modo preferido de cada pantalla (MonitorSetup)',
    'Resolution': 'Resolución', 'Size of the screen in pixels': 'Tamaño de la pantalla en píxeles',
    'Refresh rate': 'Frecuencia', 'Hz available for that resolution': 'Hz disponibles para esa resolución',
    'Rotation': 'Rotación', 'Turn the picture (portrait screens)': 'Gira la imagen (pantallas verticales)',
    'Normal': 'Normal', 'Left (90°)': 'Izquierda (90°)', 'Right (270°)': 'Derecha (270°)', 'Inverted (180°)': 'Invertida (180°)',
    'Reflection': 'Reflejo', 'Mirror the picture (projectors, rear screens)': 'Refleja la imagen (proyectores, pantallas traseras)',
    'None': 'Ninguno', 'Horizontal': 'Horizontal', 'Vertical': 'Vertical', 'Both': 'Ambos', 'Scale': 'Escala',
    'Render the desktop bigger or smaller than the mode (xrandr --scale)':
        'Dibuja el escritorio más grande o más pequeño que el modo (xrandr --scale)',
    'bigger UI (blurry)': 'interfaz más grande (borrosa)', 'more space': 'más espacio', 'native': 'nativa',
    'Preferred': 'Preferido', 'Discard': 'Descartar', 'Apply layout': 'Aplicar disposición',
    'Preferred mode and rate, no rotation, 1× scale': 'Modo y frecuencia preferidos, sin rotación, escala 1×',
    'You get 15 s to keep it, otherwise it goes back by itself': 'Tienes 15 s para mantenerla; si no, vuelve sola',
    'applied live · software gamma': 'en vivo · gamma por software', 'Brightness': 'Brillo',
    'Dims the picture (works on any screen / VM)': 'Atenúa la imagen (funciona en cualquier pantalla / VM)',
    'Night light': 'Luz nocturna', 'Warmer colors, easier on the eyes at night': 'Colores más cálidos, mejor para la vista de noche',
    'Backlight': 'Retroiluminación', 'Panel hardware brightness (brightnessctl)': 'Brillo del panel por hardware (brightnessctl)',
    'cvt · xrandr --newmode': 'cvt · xrandr --newmode', 'New mode': 'Modo nuevo', 'Add': 'Añadir',
    'For sizes the screen does not list (VMs, odd panels); saved and re-created at login':
        'Para tamaños que la pantalla no ofrece (VMs, paneles raros); se guarda y se recrea al iniciar sesión',
    'xset · Xresources · xsettingsd': 'xset · Xresources · xsettingsd', 'Turn screens off': 'Apagar pantallas',
    'Power the monitors down after this many idle minutes (idle LOCK is set in Login Lock)':
        'Apaga los monitores tras estos minutos sin uso (el BLOQUEO por inactividad está en Bloqueo de inicio)',
    'Font DPI': 'DPI de la fuente',
    'Text size of GTK / Qt / terminal apps (new windows); for HiDPI screens without changing the resolution':
        'Tamaño del texto de apps GTK / Qt / terminal (ventanas nuevas); para pantallas HiDPI sin cambiar la resolución',
    'DisplayBoot · asks for your password': 'DisplayBoot · pide tu contraseña',
    'Use saved resolution': 'Usar la resolución guardada', 'Resolution before the desktop': 'Resolución antes del escritorio',
    'Boot menu (Limine / GRUB), TTY consoles and the LightDM login screen use the resolution saved here. '
    'Applies from the next boot.': 'El menú de arranque (Limine / GRUB), las TTY y la pantalla de login de LightDM usan '
    'la resolución guardada aquí. Se aplica desde el próximo arranque.',
    'Keep this display configuration?': '¿Mantener esta configuración de pantalla?', 'Revert': 'Revertir',
    'Keep changes': 'Mantener', 'changes not applied yet': 'cambios aún sin aplicar',
    'Enabled': 'Activada', 'Switch this screen on or off': 'Enciende o apaga esta pantalla', 'Primary': 'Principal',
    'Main screen: sits at 0,0, holds the bar and the first desktops':
        'Pantalla principal: en 0,0, con la barra y los primeros escritorios',
    'Position': 'Posición', 'Right of': 'A la derecha de', 'Left of': 'A la izquierda de', 'Above': 'Encima de',
    'Below': 'Debajo de', 'Mirror of': 'Espejo de',

    # ── compositor
    'PERFORMANCE ': 'RENDIMIENTO', 'Lite': 'Lite', 'Mode': 'Modo',
    'Normal: every effect, full repaints for flawless frames · Lite: picom on xrender, no blur, no animations, '
    'lighter frames and bar pulse (shadows, corners, fading and the theme stay). For VMs without 3D':
        'Normal: todos los efectos, repintado completo para marcos impecables · Lite: picom con xrender, sin '
        'desenfoque ni animaciones, marcos y pulso de la barra más ligeros (se mantienen sombras, esquinas, '
        'fundido y el tema). Para VMs sin 3D',
    '(applied)': '(aplicado)',
    'suggested for this machine: Lite': 'recomendado para este equipo: Lite',
    'suggested for this machine: Normal': 'recomendado para este equipo: Normal',
    'Backend': 'Motor', 'glx is the fastest; xrender works everywhere': 'glx es el más rápido; xrender funciona en todas partes',
    'needs a picom restart': 'requiere reiniciar picom', 'Avoid tearing': 'Evitar tearing', 'Corner radius': 'Radio de esquinas',
    'Rounded window corners (0 = square)': 'Esquinas redondeadas (0 = rectas)', 'Focused opacity': 'Opacidad con foco',
    'Opacity of the focused window': 'Opacidad de la ventana enfocada', 'Unfocused opacity': 'Opacidad sin foco',
    'Opacity of the other windows': 'Opacidad de las demás ventanas', 'Shadows': 'Sombras',
    'Drop shadow under windows': 'Sombra bajo las ventanas', 'Shadow color': 'Color de la sombra',
    'Shadow radius': 'Radio de la sombra', 'Shadow opacity': 'Opacidad de la sombra', 'Blur': 'Desenfoque',
    'Frosted background behind transparent windows': 'Fondo esmerilado detrás de ventanas transparentes',
    'blur and animations are off in Lite mode': 'el desenfoque y las animaciones están apagados en modo Lite',
    'Blur method': 'Método de desenfoque', 'Blur size': 'Tamaño del desenfoque', 'Kernel size (gaussian / box)':
        'Tamaño del kernel (gaussiano / caja)', 'Blur deviation': 'Desviación del desenfoque', 'Softness (gaussian)':
        'Suavidad (gaussiano)', 'Fading': 'Fundido', 'Fade windows in and out': 'Fundido al abrir y cerrar ventanas',
    'Fade speed': 'Velocidad del fundido', 'Opacity step per frame': 'Paso de opacidad por fotograma',
    'picom animations': 'animaciones de picom', 'Animations': 'Animaciones',
    'Open/close/move animations (picom v12+)': 'Animaciones al abrir/cerrar/mover (picom v12+)',

    # ── terminal
    'Fake terminal over the wallpaper: shows opacity, font and colors live.':
        'Terminal de muestra sobre el fondo: opacidad, fuente y colores en vivo.',
    'Font': 'Fuente', 'Monospace family and size': 'Familia monoespaciada y tamaño',
    'Transparency': 'Transparencia', 'Background opacity': 'Opacidad del fondo',
    '1.0 = solid. Blur only shows through transparency': '1.0 = sólido. El desenfoque solo se ve con transparencia',
    'Shell': 'Shell', 'Run colorscript when a terminal opens': 'Ejecutar colorscript al abrir una terminal',
    'Disable fzf-tab': 'Desactivar fzf-tab', 'Use plain zsh completion instead of fzf-tab':
        'Usar el autocompletado normal de zsh en vez de fzf-tab',
    'kitty · alacritty · ghostty': 'kitty · alacritty · ghostty', 'Pixel-art on startup': 'Pixel-art al iniciar',

    # ── wallpaper
    'Wallpaper on screen': 'Fondo en pantalla', 'real render of your wallpaper': 'render real de tu fondo',
    'Wallpaper engine': 'Motor del fondo', 'how the wallpaper is chosen at login': 'cómo se elige el fondo al iniciar',
    'Default · fixed image': 'Predeterminado · imagen fija', 'Random · rice walls': 'Aleatorio · fondos del rice',
    'Random · custom folder': 'Aleatorio · carpeta propia', 'Slideshow · 15 min': 'Presentación · 15 min',
    'Video · walls/videos': 'Vídeo · walls/videos', 'Open 3D selector': 'Abrir el selector 3D',
    'Random wallpaper': 'Fondo aleatorio', 'Add video…': 'Añadir vídeo…', 'Stop · back to picture': 'Parar · volver a la imagen',
    'Use on the login lock': 'Usar en el bloqueo de inicio', 'Fill (crop the edges)': 'Rellenar (recorta los bordes)',
    'Fit (black bars)': 'Ajustar (barras negras)', 'Pause automatically': 'Pausar automáticamente',
    'Saves CPU/GPU: the video only plays when you can see it': 'Ahorra CPU/GPU: el vídeo solo se reproduce cuando se ve',
    'When windows cover the desktop': 'Cuando las ventanas cubren el escritorio', 'Only with a fullscreen window':
        'Solo con una ventana a pantalla completa', 'Never': 'Nunca', 'Speed': 'Velocidad', 'Play / pause': 'Reproducir / pausar',
    'No video playing': 'No hay vídeo reproduciéndose', 'paused by you': 'pausado por ti', 'paused: windows cover it':
        'en pausa: las ventanas lo tapan',

    # ── dock
    'bottom of the screen · follows the palette · saved in config/dock.json':
        'parte inferior de la pantalla · sigue la paleta · guardado en config/dock.json',
    'Show the dock': 'Mostrar el dock', 'Also starts with the session': 'También arranca con la sesión',
    'Icon size': 'Tamaño de iconos', 'Magnification': 'Ampliación', 'Wave zoom of the icons under the pointer':
        'Zoom en ola de los iconos bajo el puntero', 'Auto-hide': 'Auto-ocultar',
    'Slides away until the pointer touches the bottom edge and comes back over the windows; they then use the whole screen':
        'Se esconde hasta que el puntero toca el borde inferior y vuelve sobre las ventanas; así usan toda la pantalla',
    'Launcher button': 'Botón lanzador', 'Applications button at the left of the dock': 'Botón de aplicaciones a la izquierda del dock',
    'Dock process': 'Proceso del dock', 'Restart it if something looks off': 'Reinícialo si algo se ve raro',
    'Restart dock': 'Reiniciar dock', 'order = order in the dock': 'orden = orden en el dock', 'click to pin': 'clic para fijar',
    'Move left': 'Mover a la izquierda', 'Move right': 'Mover a la derecha', 'Unpin': 'Quitar',
    'No pinned apps yet: add some below': 'Aún no hay apps fijadas: añade alguna abajo',

    # ── polybar
    'bar + windows in one click · colors follow the palette': 'barra + ventanas en un clic · los colores siguen la paleta',
    'Classic': 'Clásico', 'Capsule bar · borderless windows': 'Barra cápsula · ventanas sin borde',
    'Neon HUD': 'HUD neón', 'Angled cyber plates · glowing window frames': 'Placas cyber en ángulo · marcos que brillan',
    'Islands': 'Islas', 'Floating neon pills · glowing frames': 'Cápsulas neón flotantes · marcos que brillan',
    'Mainframe': 'Mainframe', 'Edge to edge strip · sharp HUD windows': 'Franja de borde a borde · ventanas HUD rectas',
    'Capsule': 'Cápsula', 'one floating rounded bar': 'una barra redondeada flotante',
    'transparent bar, each group is a neon pill': 'barra transparente, cada grupo es una cápsula neón',
    'Cyber': 'Cyber', 'transparent bar, angled HUD plates': 'barra transparente, placas HUD en ángulo', 'Strip': 'Franja',
    'edge to edge panel with a neon line': 'panel de borde a borde con una línea neón',
    'pac-man = current · ghost = has windows · dot = empty': 'pac-man = actual · fantasma = con ventanas · punto = vacío',
    'Look': 'Aspecto', 'applied live': 'en vivo', 'Edge of the screen (windows make room for it)':
        'Borde de la pantalla (las ventanas le dejan sitio)', 'Top': 'Arriba', 'Bottom': 'Abajo', 'Height': 'Altura',
    'Bar thickness': 'Grosor de la barra', 'Distance from the edge': 'Distancia al borde',
    'Floating gap (not used by Strip)': 'Separación flotante (no se usa en Franja)', 'Side margins': 'Márgenes laterales',
    'Space at the left and right ends': 'Espacio en los extremos izquierdo y derecho', 'Capsule style roundness':
        'Redondez del estilo cápsula', 'Opacity': 'Opacidad', 'Background transparency (needs picom)':
        'Transparencia del fondo (requiere picom)', 'Bar skin': 'Piel de la barra', 'None (plain bar)': 'Ninguna (barra simple)',
    'The whole bar drawn in a style (Themes set it too)': 'Toda la barra dibujada en un estilo (los Temas también la ponen)',
    'Background color': 'Color de fondo', 'Palette color of the bar / pills': 'Color de la paleta para la barra / cápsulas',
    'Accent color': 'Color de acento', 'Border and neon line (palette color)': 'Borde y línea neón (color de la paleta)',
    'Border': 'Borde', 'Thin accent frame around the Capsule bar': 'Marco fino de acento alrededor de la barra cápsula',
    'Separators': 'Separadores', 'Thin lines between modules': 'Líneas finas entre módulos',
    'Hidden until the pointer touches its screen edge; then it slides in over the windows, which use the whole screen':
        'Oculta hasta que el puntero toca su borde; entonces aparece sobre las ventanas, que usan toda la pantalla',
    'Keyboard': 'Teclado', 'super + alt + u shows the bar (and keeps it pinned when auto-hide is on) · super + alt + h hides it':
        'super + alt + u muestra la barra (y la fija con auto-ocultar) · super + alt + h la oculta',
    'Bar process': 'Proceso de la barra', 'Regenerate bar.ini and restart polybar': 'Regenera bar.ini y reinicia polybar',
    'Restart bar': 'Reiniciar barra', 'Modules': 'Módulos', 'order = order on the bar · "Gap" splits a group':
        'orden = orden en la barra · "Gap" divide un grupo', 'click to add it': 'clic para añadirlo', 'Add to':
        'Añadir a', 'Group that receives the new module': 'Grupo que recibe el nuevo módulo', 'Left': 'Izquierda',
    'Center': 'Centro', 'Right': 'Derecha', 'Send to left': 'Enviar a la izquierda', 'Send to center': 'Enviar al centro',
    'Send to right': 'Enviar a la derecha', 'Bar style': 'Estilo de barra', 'Workspace style': 'Estilo de workspaces',

    # ── notifications
    'Corner of the screen': 'Esquina de la pantalla', 'Horizontal · vertical distance from the edge':
        'Distancia horizontal · vertical al borde', 'Offset X': 'Desplazamiento X', 'Offset Y': 'Desplazamiento Y',
    'Menu font': 'Fuente de menús', 'Used by every rofi menu of the rice': 'La usan todos los menús rofi del rice',
    'Open animation': 'Animación al abrir', 'Close animation': 'Animación al cerrar', 'Needs a compositor': 'Requiere compositor',
    'Test notification': 'Notificación de prueba', 'Send a sample notification': 'Envía una notificación de ejemplo',
    'Border color': 'Color del borde', 'Follow the palette': 'Seguir la paleta', 'Colors back to the palette of the rice (they change with it)':
        'Colores de vuelta a la paleta del rice (cambian con ella)', 'Reset colors': 'Restablecer colores',

    # ── lockscreen
    'real render · Super + Shift + L': 'render real · Super + Shift + L', 'Lock now': 'Bloquear ahora',
    'Random wall': 'Fondo aleatorio', 'The lockscreen always uses the wallpaper\nthat is on screen.':
        'El bloqueo usa siempre el fondo\nque está en pantalla.', 'Darken the wallpaper for readability':
        'Oscurece el fondo para que se lea mejor', '0 = sharp wallpaper': '0 = fondo nítido', 'Glass panel': 'Panel de vidrio',
    'Frosted HUD panel behind the clock': 'Panel HUD esmerilado detrás del reloj', 'Clock format': 'Formato del reloj',
    'Greeter text': 'Texto de bienvenida', 'Accent (keypress & glass border)': 'Acento (pulsaciones y borde del vidrio)',

    # ── login lock
    'Try it': 'Probar', 'Try it (8 s)': 'Probar (8 s)', 'Re-render': 'Volver a generar',
    'Locks for real and unlocks by itself after 8 seconds': 'Bloquea de verdad y se desbloquea solo a los 8 segundos',
    'What is behind the login card': 'Qué hay detrás de la tarjeta', 'Source': 'Origen', 'A picture of mine': 'Una imagen mía',
    'A video (plays behind the lock)': 'Un vídeo (se reproduce detrás del bloqueo)', 'Same as the video wallpaper':
        'El mismo que el fondo de vídeo', 'Random of the rice (each lock)': 'Aleatorio del rice (en cada bloqueo)',
    'Picture': 'Imagen', 'Used with "A picture of mine"': 'Se usa con "Una imagen mía"', 'Choose…': 'Elegir…',
    'Video': 'Vídeo', 'Play this video behind the betterlockscreen login card': 'Reproduce este vídeo detrás de la tarjeta',
    'Effect': 'Efecto', 'Used with "A video": the effect below is applied live (needs picom running, else a still of it)':
        'Con "Un vídeo": el efecto se aplica en vivo (requiere picom; si no, una imagen fija)',
    'Dim': 'Oscurecer', 'Dim + blur': 'Oscurecer + desenfocar', 'Pixelate': 'Pixelar', 'Dim + pixelate': 'Oscurecer + pixelar',
    'Solid palette color': 'Color sólido de la paleta', 'Pixel size': 'Tamaño de píxel',
    'Glass card': 'Tarjeta de vidrio', 'Frosted panel behind the avatar and the password field':
        'Panel esmerilado detrás del avatar y el campo de contraseña', 'Card tint': 'Tinte de la tarjeta',
    'How much palette color covers the glass': 'Cuánto color de la paleta cubre el vidrio',
    'Avatar': 'Avatar', 'The AvatarForge picture, the password ring goes around it':
        'La imagen de AvatarForge; el anillo de contraseña la rodea', 'Avatar shape': 'Forma del avatar', 'Circle': 'Círculo',
    'Squircle': 'Squircle', 'Hexagon': 'Hexágono', 'Change the avatar (AvatarForge)': 'Cambiar el avatar (AvatarForge)',
    'Name': 'Nombre', 'Big name under the avatar': 'Nombre grande bajo el avatar', 'Password field text':
        'Texto del campo de contraseña', 'Message': 'Mensaje', 'Bottom line, e.g. "If found call +00 000"':
        'Línea inferior, p. ej. "Si lo encuentras llama al +00 000"', 'Clock & date': 'Reloj y fecha',
    'Password indicator': 'Indicador de contraseña', 'Ring around the avatar, or bars under the field':
        'Anillo alrededor del avatar, o barras bajo el campo', 'Ring around the avatar': 'Anillo alrededor del avatar',
    'Under the password field': 'Bajo el campo de contraseña', 'Accent (ring · keypress · date)':
        'Acento (anillo · pulsaciones · fecha)', 'Second accent (border gradient)': 'Segundo acento (degradado del borde)',
    'Texts': 'Textos', 'Verifying': 'Verificando', 'Wrong password · Caps Lock': 'Contraseña incorrecta · Bloq Mayús',
    'Keyboard layout': 'Distribución de teclado', 'Active layout': 'Distribución activa', 'Now playing': 'Reproduciendo',
    'Song of playerctl at the bottom (taken when it locks)': 'Canción de playerctl abajo (se toma al bloquear)',
    'auto-lock · xss-lock': 'auto-bloqueo · xss-lock', 'Auto-lock when idle': 'Auto-bloqueo por inactividad',
    'Locks after this many minutes without input': 'Bloquea tras estos minutos sin actividad', 'Screen off': 'Pantalla apagada',
    'Display turns off after this while locked': 'La pantalla se apaga tras este tiempo bloqueada',
    'Lock before suspend': 'Bloquear antes de suspender', 'Suspending always wakes up locked': 'Al suspender siempre despierta bloqueado',

    # ── appearance
    'GTK theme': 'Tema GTK', 'Icon theme': 'Tema de iconos', 'Cursor theme': 'Tema del cursor',
    'xsettingsd · applied live': 'xsettingsd · en vivo', 'launcher · menus': 'lanzador · menús',
    'UserCard · RiceEditor · picture or ASCII art': 'UserCard · RiceEditor · imagen o arte ASCII',
    'Open AvatarForge': 'Abrir AvatarForge', 'Profile picture': 'Foto de perfil',

    # ── snapshots
    'theme-config · picom · bspwmrc · kitty · dock · bar': 'theme-config · picom · bspwmrc · kitty · dock · barra',
    'New snapshot': 'Nueva instantánea', 'Freeze the current rice so you can come back to it (Ctrl+S)':
        'Congela el rice actual para poder volver a él (Ctrl+S)', 'Save': 'Guardar', 'restore re-applies the whole rice':
        'restaurar vuelve a aplicar todo el rice', 'Restore': 'Restaurar', 'Delete': 'Borrar', 'No snapshots yet.':
        'Aún no hay instantáneas.',

    # ── help
    'Jump to a section': 'Ir a una sección', 'Save a snapshot': 'Guardar una instantánea',
    'Soft reload (bars, picom, dunst, sxhkd)': 'Recarga suave (barras, picom, dunst, sxhkd)',
    'Login lock (betterlockscreen)': 'Bloqueo de inicio (betterlockscreen)', 'Close RiceEditor': 'Cerrar RiceEditor',
    'Shortcuts': 'Atajos', 'How it works': 'Cómo funciona',
    'Themed terminal background': 'Fondo temático de la terminal',
    'Lava rock, liquid glass, leaves, circuits… under the terminals (they become slightly translucent)':
        'Roca de lava, vidrio líquido, hojas, circuitos… bajo las terminales (se vuelven algo translúcidas)',
    'A theme is still being applied…': 'Todavía se está aplicando un tema…',
    'Language': 'Idioma', 'Interface language of RiceEditor (it reopens itself)':
        'Idioma de la interfaz de RiceEditor (se vuelve a abrir sola)',
}

# toasts made with values: (English regex, Spanish template)
PATTERNS = [
    (r'^Palette (.+) applied$', 'Paleta {0} aplicada'),
    (r'^Applying (.+)…$', 'Aplicando {0}…'),
    (r'^(.+) applied \((.+)\)$', '{0} aplicado ({1})'),
    (r'^Snapshot "(.+)" saved$', 'Instantánea "{0}" guardada'),
    (r'^Window style → (.+)$', 'Estilo de ventana → {0}'),
    (r'^Window frames → (.+)$', 'Marcos de ventana → {0}'),
    (r'^Workspaces: (.+)$', 'Workspaces: {0}'),
]

ES.update({
    # bar modules (barconf.CATALOG)
    'Launcher': 'Lanzador', 'App launcher button': 'Botón del lanzador de apps', 'bspwm desktops': 'escritorios de bspwm',
    'CPU load': 'Carga de CPU', 'Memory': 'Memoria', 'RAM used / total': 'RAM usada / total', 'Disk': 'Disco',
    'Space used on /': 'Espacio usado en /', 'Network': 'Red', 'Traffic trace, ↓ ↑ in KB/s · MB/s':
    'Gráfica de tráfico, ↓ ↑ en KB/s · MB/s', 'Volume': 'Volumen', 'Audio level': 'Nivel de audio',
    'Microphone': 'Micrófono', 'Mute / unmute the mic': 'Silenciar / activar el micro', 'Clock': 'Reloj',
    'Time · click for the date': 'Hora · clic para la fecha', 'Caffeine': 'Cafeína', 'Keep the screen awake':
    'Mantiene la pantalla despierta', 'Screenshot': 'Captura', 'Capture HUD · right click: region':
    'HUD de captura · clic derecho: región', 'Module list': 'Lista de módulos', 'Power': 'Apagado',
    'Session menu': 'Menú de sesión', 'Uptime': 'Tiempo encendido', 'Time since boot': 'Tiempo desde el arranque',
    'Temperature': 'Temperatura', 'CPU temperature': 'Temperatura de la CPU', 'GPU usage and temperature':
    'Uso y temperatura de la GPU', 'Heartbeat': 'Latido', 'Decorative neon pulse': 'Pulso neón decorativo',
    'Now playing ': 'Reproduciendo', 'MPD song ticker': 'Canción de MPD', 'MPD control': 'Control de MPD',
    'Prev / play / next': 'Anterior / reproducir / siguiente', 'Short MPD status': 'Estado corto de MPD',
    'Player': 'Reproductor', 'Music player shortcut': 'Acceso al reproductor', 'Adapter status': 'Estado del adaptador',
    'Battery': 'Batería', 'Charge and state': 'Carga y estado', 'Screen backlight': 'Retroiluminación de la pantalla',
    'Updates': 'Actualizaciones', 'Pending packages': 'Paquetes pendientes', 'Weather': 'Clima',
    'Current weather': 'Clima actual', 'Color picker': 'Selector de color', 'Pick a color on screen':
    'Toma un color de la pantalla', 'Clipboard': 'Portapapeles', 'Clipboard history': 'Historial del portapapeles',
    'System monitor': 'Monitor del sistema', 'Process monitor': 'Monitor de procesos', 'User card': 'Tarjeta de usuario',
    'Profile widget': 'Widget de perfil', 'Tray': 'Bandeja', 'System tray icons': 'Iconos de la bandeja',
    'Gap': 'Separación', 'Splits a group: new pill / wider space': 'Divide un grupo: nueva cápsula / más espacio',
    # long texts
    '• Everything you touch is written to ~/.config/bspwm/rices/crackone/theme-config.bash (or picom.conf /\n'
    '  bspwmrc for global options) and applied at once: bspc for windows, a picom reload\n'
    '  for the compositor, and the rice modules for dunst, gtk, rofi and terminals.\n'
    '• You always edit the rice that was active when RiceEditor opened. After switching\n'
    '  rice, close and reopen it.\n'
    '• A snapshot is taken automatically the first time you open RiceEditor each day,\n'
    '  so a bad tweak is always one click away from being undone (Snapshots).\n'
    '• Palettes come from theme_colors.bash; the editor itself follows the active one.':
    '• Todo lo que tocas se escribe en ~/.config/bspwm/rices/crackone/theme-config.bash (o en picom.conf /\n'
    '  bspwmrc para opciones globales) y se aplica al momento: bspc para las ventanas, una recarga\n'
    '  de picom para el compositor, y los módulos del rice para dunst, gtk, rofi y terminales.\n'
    '• Siempre editas el rice que estaba activo al abrir RiceEditor. Si cambias de rice,\n'
    '  ciérralo y vuelve a abrirlo.\n'
    '• Cada día, la primera vez que abres RiceEditor se guarda una instantánea automática,\n'
    '  así un mal cambio siempre está a un clic de deshacerse (Instantáneas).\n'
    '• Las paletas vienen de theme_colors.bash; el editor sigue la activa.',
})
PATTERNS += [
    (r'^(\d+) walls · click to apply$', '{0} fondos · clic para aplicar'),
    (r'^(.+) · click to play$', '{0} · clic para reproducir'),
    (r'^Palettes live in (.+) — add your own cargar_<name>\(\) function and it shows up here\.$',
     'Las paletas están en {0} — añade tu propia función cargar_<nombre>() y aparecerá aquí.'),
    (r'^(Picture|ASCII art) of (.+) · the \.png files of (.+) \(click the logo too\)$',
     '{0} de {1} · los .png de {2} (también con clic en el logo)'),
    (r'^(.+) · written by BetterLock, so a plain "betterlockscreen -l" looks the same$',
     '{0} · lo escribe BetterLock, así un "betterlockscreen -l" normal se ve igual'),
    (r'^BL_\* in (.+)$', 'BL_* en {0}'),
]
ES.update({'Picture': 'Imagen', 'ASCII art': 'Arte ASCII'})

_ICON = re.compile(r'^([-\U000F0000-\U000FFFFF★●■•◉]+\s*)')

_UPPER = {k.upper(): v.upper() for k, v in ES.items()}


def _one(text):
    if text in ES:
        return ES[text]
    if text.isupper() and text in _UPPER:
        return _UPPER[text]
    return None


def tr(text, lang=None):
    """Spanish of an on-screen text (as is when unknown or in English)."""
    if not text or (lang or LANG) != 'es':
        return text
    m = _ICON.match(text)
    head, body = (m.group(1), text[m.end():]) if m else ('', text)
    t = _one(body.strip())
    if t is not None:
        return head + t
    if ' → ' in body:                        # "Border width → 2px"
        left, _, right = body.partition(' → ')
        t = _one(left.strip())
        if t is not None:
            return f'{head}{t} → {right}'
    if ' · ' in body:                        # "BSPWM · BORDERS · GAPS"
        parts = body.split(' · ')
        out = [_one(p.strip()) for p in parts]
        if any(o is not None for o in out):
            return head + ' · '.join(o if o is not None else p for o, p in zip(out, parts))
    for pat, tpl in PATTERNS:
        mm = re.match(pat, body)
        if mm:
            return head + tpl.format(*(_one(g) or g for g in mm.groups()))
    return text


LANG = get_lang()
