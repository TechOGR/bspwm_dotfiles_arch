# =============================================================
# Author:  TechOGR
# Repo:    https://github.com/TechOGR/bspwm_dotfiles_arch
#
# ricekit - whole-rice themes built on the workspace styles of
# lib/wspill.py (Neon Cyberpunk, Minimal Dark, Pixel, Liquid, HUD,
# Nature, Pencil, Lava, Solid Neon, Holographic, Storm, Venom,
# Butterflies, Snakes, and lib/wsfour.py: Halloween, Desert, Neo Tokyo,
# Abyss, Enchanted Forest, Cosmos, Samurai, Steampunk, Glacier,
# Witchcraft, Golden Dragon, Graffiti). A theme is made of
# parts that can be applied together or one by one:
#   colors      palette -> terminals, rofi, dunst, GTK, lockscreen, bar
#               text, RiceEditor itself (theme_colors.bash cargar_*)
#   bar         the polybar background drawn in the style (bar skin)
#   workspaces  the workspace pill of the bar
#   windows     borders, corners, gaps, opacity, glow shadow, blur,
#               notification corners
#   cursor      the theme's animated cursor (bin/ThemeCursor)
# Used by RiceEditor -> Themes and bin/RiceKit.
#
# Copyright (C) 2021-2026 TechOGR <https://github.com/TechOGR>
# Licensed under GPL-3.0 license
# =============================================================

import os
import re
import subprocess

import barconf as bc

PARTS = [
    ('colors', '󰏘', 'Colors', 'palette: terminals, rofi, notifications, GTK, lockscreen'),
    ('bar', '󱔓', 'Bar', 'polybar drawn in the style'),
    ('workspaces', '󰮯', 'Workspaces', 'the pac-man pill of the bar'),
    ('windows', '󰖲', 'Windows', 'borders, corners, gaps, glow, blur, opacity'),
    ('cursor', '󰇀', 'Cursor', "the theme's animated cursor, in its colors"),
    ('wallpaper', '󰸉', 'Wallpaper', "the theme's wallpaper (changeable in Themes)"),
]
STYLE_PARTS = ('colors', 'bar', 'workspaces', 'windows')   # all of them = the whole theme (RICE_KIT)

# The wallpaper each theme brings (rices/<rice>/walls). RiceEditor -> Themes
# changes it per theme; the choice is kept in config/theme-walls.json.
THEME_WALLS = {
    'cyber': 'neon-pink-sunset-scenery-digital-art-4k-wallpaper-uhdpaper.com-439@5@r.jpg',
    'minimal': 'anime-girl-sunrise-4k-wallpaper-uhdpaper.com-507@5@f.jpg',
    'pixel': 'spongebob-sponge-on-the-run-houses-uhdpaper.com-4K-7.355.jpg',
    'liquid': 'pirate-ship-island-digital-art-4k-wallpaper-uhdpaper.com-659@2@b.jpg',
    'hud': 'muichiro-tokito-demon-slayer-4k-wallpaper-uhdpaper.com-907@5@g.jpg',
    'nature': 'anime-girl-alone-sunflower-4k-wallpaper-uhdpaper.com-462@5@r.jpg',
    'sketch': 'kenpachi-bleach-anime-4k-wallpaper-uhdpaper.com-143@5@q.jpg',
    'lava': 'itachi-uchiha-crow-akatsuki-4k-wallpaper-uhdpaper.com-760@5@r.jpg',
    'neon': 'super-saiyan-rose-dragon-ball-4k-wallpaper-uhdpaper.com-92@5@r.jpg',
    'holo': 'alone-anime-girl-starry-night-sky-stars-scenery-4k-wallpaper-uhdpaper.com-225@5@i.jpg',
    'storm': 'kakashi-hatake-4k-wallpaper-uhdpaper.com-89@5@r.jpg',
    'venom': 'muzan-demon-slayer-4k-wallpaper-uhdpaper.com-916@5@g.jpg',
    'butterfly': 'shinobu-kocho-demon-slayer-4k-wallpaper-uhdpaper.com-843@5@h.jpg',
    'snake': 'sukuna-jujutsu-kaisen-4k-wallpaper-uhdpaper.com-765@5@r.jpg',
    'halloween': 'night-moon-reflection-scenery-digital-art-4k-wallpaper-uhdpaper.com-869@5@m.jpg',
    'desert': 'anime-girl-sunrise-4k-wallpaper-uhdpaper.com-146@5@l.jpg',
    'neotokyo': 'satoru-gojo-neon-jjk-4k-wallpaper-uhdpaper.com-338@5@i.jpg',
    'abyss': 'anime-girl-silhoutte-moon-sea-night-moon-4k-wallpaper-uhdpaper.com-756@5@r.jpg',
    'forest': 'broly-eyes-dragon-ball-4k-wallpaper-uhdpaper.com-85@5@o.jpg',
    'cosmos': 'shooting-star-comet-anime-girl-night-sky-scenery-4k-wallpaper-uhdpaper.com-522@5@k.jpg',
    'samurai': 'kyojuro-rengoku-demon-slayer-4k-wallpaper-uhdpaper.com-844@5@h.jpg',
    'steampunk': 'kratos-axe-god-of-war-4k-wallpaper-uhdpaper.com-804@5@k.jpg',
    'glacier': 'rukia-bankai-bleach-tybw-art-4k-wallpaper-uhdpaper.com-280@5@r.jpg',
    'witch': 'orochimaru.jpg',
    'dragon': 'hanzo-mlbb-soul-fire-splash-art-4k-wallpaper-uhdpaper.com-472@5@q.jpg',
    'graffiti': 'toji-jjk-4k-wallpaper-uhdpaper.com-444@5@l.jpg',
}
WALLS_CONF = os.path.join(os.path.expanduser('~/.config/bspwm'), 'config/theme-walls.json')


def _walls_conf():
    try:
        import json
        with open(WALLS_CONF) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def theme_wall(kit):
    """The wallpaper of a theme (absolute path, '' when there is none):
    the one chosen in RiceEditor, else the theme's own from the rice walls."""
    walls = os.path.join(bc.rice_dir(), 'walls')
    for cand in (_walls_conf().get(kit), THEME_WALLS.get(kit)):
        if not cand:
            continue
        path = cand if os.path.isabs(cand) else os.path.join(walls, cand)
        if os.path.isfile(path):
            return path
    return ''


def set_theme_wall(kit, path):
    """Keep path as the wallpaper of kit (None: back to the theme's own)."""
    import json
    d = _walls_conf()
    walls = os.path.join(bc.rice_dir(), 'walls')
    if path is None:
        d.pop(kit, None)
    else:
        d[kit] = os.path.basename(path) if os.path.dirname(os.path.abspath(path)) == walls else path
    tmp = WALLS_CONF + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(d, f, indent=2, sort_keys=True)
        f.write('\n')
    os.replace(tmp, WALLS_CONF)


def paint_wall(path):
    """Put path on screen now (like WallSelect): stops a video / slideshow
    wallpaper, paints it and refreshes what follows the wallpaper."""
    subprocess.Popen(['sh', '-c', '''
        VideoWall --stop 2>/dev/null
        [ -f /tmp/wall_refresh.pid ] && kill "$(cat /tmp/wall_refresh.pid)" 2>/dev/null
        rm -f /tmp/wall_refresh.pid
        feh --bg-fill "$1" && WallSync
    ''', '_', path], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# id: name, tagline, palette function, windows settings, dunst radius
KITS = {
    'cyber': dict(
        name='Neon Cyberpunk', tagline='futuristic and striking', palette='cargar_neon_cyberpunk',
        win=dict(BORDER_WIDTH=2, FOCUSED_BC='#ff2bd6', NORMAL_BC='#2a1850', P_CORNER_R=0, gap=10,
                 SHADOW_C='#ff2bd6', P_BLUR='false', P_ACTIVE_OPACITY='0.97', P_INACTIVE_OPACITY='0.90'),
        dunst_r=0),
    'minimal': dict(
        name='Minimal Dark', tagline='elegant and discreet', palette='cargar_minimal_dark',
        win=dict(BORDER_WIDTH=1, FOCUSED_BC='#5a6385', NORMAL_BC='#1e222e', P_CORNER_R=10, gap=6,
                 SHADOW_C='#000000', P_BLUR='false', P_ACTIVE_OPACITY='1.0', P_INACTIVE_OPACITY='0.95'),
        dunst_r=10),
    'pixel': dict(
        name='Pixel', tagline='retro and classic', palette='cargar_pixel_retro',
        win=dict(BORDER_WIDTH=3, FOCUSED_BC='#1f5bff', NORMAL_BC='#0c1a4d', P_CORNER_R=0, gap=8,
                 SHADOW_C='#000000', P_BLUR='false', P_ACTIVE_OPACITY='1.0', P_INACTIVE_OPACITY='0.94'),
        dunst_r=0),
    'liquid': dict(
        name='Liquid', tagline='fluid and original', palette='cargar_liquid',
        win=dict(BORDER_WIDTH=2, FOCUSED_BC='#34dcff', NORMAL_BC='#23305a', P_CORNER_R=18, gap=12,
                 SHADOW_C='#3656ff', P_BLUR='true', P_ACTIVE_OPACITY='0.96', P_INACTIVE_OPACITY='0.88'),
        dunst_r=18),
    'hud': dict(
        name='HUD', tagline='tech and professional', palette='cargar_hud',
        win=dict(BORDER_WIDTH=1, FOCUSED_BC='#2d8cff', NORMAL_BC='#12294a', P_CORNER_R=0, gap=8,
                 SHADOW_C='#2d8cff', P_BLUR='false', P_ACTIVE_OPACITY='0.97', P_INACTIVE_OPACITY='0.90'),
        dunst_r=0),
    'nature': dict(
        name='Nature', tagline='calm and fresh', palette='cargar_nature',
        win=dict(BORDER_WIDTH=2, FOCUSED_BC='#2ee06f', NORMAL_BC='#16402a', P_CORNER_R=14, gap=10,
                 SHADOW_C='#1f8f3a', P_BLUR='false', P_ACTIVE_OPACITY='0.97', P_INACTIVE_OPACITY='0.90'),
        dunst_r=14),
}
KITS.update({
    'sketch': dict(
        name='Pencil', tagline='hand drawn in graphite', palette='cargar_pencil_graphite',
        win=dict(BORDER_WIDTH=2, FOCUSED_BC='#d6d6d6', NORMAL_BC='#333333', P_CORNER_R=8, gap=10,
                 SHADOW_C='#000000', P_BLUR='false', P_ACTIVE_OPACITY='0.98', P_INACTIVE_OPACITY='0.92'),
        dunst_r=8),
    'lava': dict(
        name='Lava', tagline='cracked rock and fire', palette='cargar_lava',
        win=dict(BORDER_WIDTH=2, FOCUSED_BC='#ff5a00', NORMAL_BC='#2a1208', P_CORNER_R=6, gap=10,
                 SHADOW_C='#ff3a00', P_BLUR='false', P_ACTIVE_OPACITY='0.97', P_INACTIVE_OPACITY='0.90'),
        dunst_r=6),
    'neon': dict(
        name='Solid Neon', tagline='clean neon outline', palette='cargar_solid_neon',
        win=dict(BORDER_WIDTH=2, FOCUSED_BC='#1ec8ff', NORMAL_BC='#1f1a4a', P_CORNER_R=12, gap=10,
                 SHADOW_C='#8b5cf6', P_BLUR='false', P_ACTIVE_OPACITY='0.97', P_INACTIVE_OPACITY='0.90'),
        dunst_r=12),
    'holo': dict(
        name='Holographic', tagline='space, orbits and particles', palette='cargar_holographic',
        win=dict(BORDER_WIDTH=2, FOCUSED_BC='#c77dff', NORMAL_BC='#2a2458', P_CORNER_R=16, gap=12,
                 SHADOW_C='#7b4dff', P_BLUR='true', P_ACTIVE_OPACITY='0.95', P_INACTIVE_OPACITY='0.88'),
        dunst_r=16),
    'storm': dict(
        name='Storm', tagline='lightning, pure energy', palette='cargar_storm',
        win=dict(BORDER_WIDTH=2, FOCUSED_BC='#7fd8ff', NORMAL_BC='#1a2a5a', P_CORNER_R=12, gap=10,
                 SHADOW_C='#3d8bff', P_BLUR='false', P_ACTIVE_OPACITY='0.97', P_INACTIVE_OPACITY='0.90'),
        dunst_r=12),
    'venom': dict(
        name='Venom', tagline='moving shadows, venom', palette='cargar_venom',
        win=dict(BORDER_WIDTH=2, FOCUSED_BC='#ff1a2e', NORMAL_BC='#2a0a0e', P_CORNER_R=14, gap=10,
                 SHADOW_C='#ff0020', P_BLUR='false', P_ACTIVE_OPACITY='0.97', P_INACTIVE_OPACITY='0.90'),
        dunst_r=14),
    'butterfly': dict(
        name='Butterflies', tagline='delicate, free, magic', palette='cargar_butterflies',
        win=dict(BORDER_WIDTH=2, FOCUSED_BC='#ff9ae8', NORMAL_BC='#2e1a52', P_CORNER_R=18, gap=12,
                 SHADOW_C='#c77dff', P_BLUR='true', P_ACTIVE_OPACITY='0.95', P_INACTIVE_OPACITY='0.88'),
        dunst_r=18),
    'snake': dict(
        name='Snakes', tagline='power, mystery, scales', palette='cargar_snakes',
        win=dict(BORDER_WIDTH=2, FOCUSED_BC='#7dff2e', NORMAL_BC='#12301a', P_CORNER_R=12, gap=10,
                 SHADOW_C='#3aff2e', P_BLUR='false', P_ACTIVE_OPACITY='0.97', P_INACTIVE_OPACITY='0.90'),
        dunst_r=12),
})
# the fourth set (lib/wsfour.py): twelve neon scenes
KITS.update({
    'halloween': dict(
        name='Halloween', tagline='pumpkins, bats and a full moon', palette='cargar_halloween',
        win=dict(BORDER_WIDTH=2, FOCUSED_BC='#ff7a1a', NORMAL_BC='#2a1430', P_CORNER_R=14, gap=10,
                 SHADOW_C='#ff5a10', P_BLUR='false', P_ACTIVE_OPACITY='0.97', P_INACTIVE_OPACITY='0.90'),
        dunst_r=14),
    'desert': dict(
        name='Desert', tagline='sunset, cacti and sand', palette='cargar_desert',
        win=dict(BORDER_WIDTH=2, FOCUSED_BC='#ffb52e', NORMAL_BC='#3a1e0c', P_CORNER_R=10, gap=10,
                 SHADOW_C='#ff8a1a', P_BLUR='false', P_ACTIVE_OPACITY='0.97', P_INACTIVE_OPACITY='0.90'),
        dunst_r=10),
    'neotokyo': dict(
        name='Neo Tokyo', tagline='neon city, torii and sakura', palette='cargar_neo_tokyo',
        win=dict(BORDER_WIDTH=2, FOCUSED_BC='#e03cff', NORMAL_BC='#22124a', P_CORNER_R=6, gap=10,
                 SHADOW_C='#ff3ab4', P_BLUR='false', P_ACTIVE_OPACITY='0.96', P_INACTIVE_OPACITY='0.89'),
        dunst_r=6),
    'abyss': dict(
        name='Abyss', tagline='jellyfish and deep sea light', palette='cargar_abyss',
        win=dict(BORDER_WIDTH=2, FOCUSED_BC='#2ccfff', NORMAL_BC='#0c2a4a', P_CORNER_R=18, gap=12,
                 SHADOW_C='#1a8aff', P_BLUR='true', P_ACTIVE_OPACITY='0.95', P_INACTIVE_OPACITY='0.87'),
        dunst_r=18),
    'forest': dict(
        name='Enchanted Forest', tagline='mushrooms, fireflies and moss', palette='cargar_enchanted_forest',
        win=dict(BORDER_WIDTH=2, FOCUSED_BC='#b8f02e', NORMAL_BC='#1e3410', P_CORNER_R=16, gap=10,
                 SHADOW_C='#7ac81a', P_BLUR='false', P_ACTIVE_OPACITY='0.97', P_INACTIVE_OPACITY='0.90'),
        dunst_r=16),
    'cosmos': dict(
        name='Cosmos', tagline='planets, nebulae and stardust', palette='cargar_cosmos',
        win=dict(BORDER_WIDTH=2, FOCUSED_BC='#8a8cff', NORMAL_BC='#1c1e4a', P_CORNER_R=14, gap=12,
                 SHADOW_C='#6a4dff', P_BLUR='true', P_ACTIVE_OPACITY='0.95', P_INACTIVE_OPACITY='0.88'),
        dunst_r=14),
    'samurai': dict(
        name='Samurai', tagline='blood moon, katana and sakura', palette='cargar_samurai',
        win=dict(BORDER_WIDTH=2, FOCUSED_BC='#ff3a3a', NORMAL_BC='#2e0c12', P_CORNER_R=8, gap=10,
                 SHADOW_C='#ff1a1a', P_BLUR='false', P_ACTIVE_OPACITY='0.97', P_INACTIVE_OPACITY='0.90'),
        dunst_r=8),
    'steampunk': dict(
        name='Steampunk', tagline='brass gears, steam and airships', palette='cargar_steampunk',
        win=dict(BORDER_WIDTH=3, FOCUSED_BC='#f0a13a', NORMAL_BC='#3a2410', P_CORNER_R=10, gap=10,
                 SHADOW_C='#c8622a', P_BLUR='false', P_ACTIVE_OPACITY='0.98', P_INACTIVE_OPACITY='0.92'),
        dunst_r=10),
    'glacier': dict(
        name='Glacier', tagline='ice crystals and a frost wolf', palette='cargar_glacier',
        win=dict(BORDER_WIDTH=2, FOCUSED_BC='#7ae0ff', NORMAL_BC='#14305a', P_CORNER_R=12, gap=12,
                 SHADOW_C='#2a8aff', P_BLUR='true', P_ACTIVE_OPACITY='0.94', P_INACTIVE_OPACITY='0.86'),
        dunst_r=12),
    'witch': dict(
        name='Witchcraft', tagline='spellbooks, ravens and candles', palette='cargar_witchcraft',
        win=dict(BORDER_WIDTH=2, FOCUSED_BC='#c84cff', NORMAL_BC='#2a1448', P_CORNER_R=14, gap=10,
                 SHADOW_C='#9a2cff', P_BLUR='false', P_ACTIVE_OPACITY='0.97', P_INACTIVE_OPACITY='0.90'),
        dunst_r=14),
    'dragon': dict(
        name='Golden Dragon', tagline='imperial gold among the clouds', palette='cargar_golden_dragon',
        win=dict(BORDER_WIDTH=2, FOCUSED_BC='#ffc42e', NORMAL_BC='#3a1408', P_CORNER_R=12, gap=10,
                 SHADOW_C='#ff7a1a', P_BLUR='false', P_ACTIVE_OPACITY='0.97', P_INACTIVE_OPACITY='0.90'),
        dunst_r=12),
    'graffiti': dict(
        name='Graffiti', tagline='spray paint and street crowns', palette='cargar_graffiti',
        win=dict(BORDER_WIDTH=2, FOCUSED_BC='#25ebf5', NORMAL_BC='#2a1a44', P_CORNER_R=16, gap=12,
                 SHADOW_C='#eb1fed', P_BLUR='false', P_ACTIVE_OPACITY='0.97', P_INACTIVE_OPACITY='0.90'),
        dunst_r=16),
})

ORDER = ['cyber', 'minimal', 'pixel', 'liquid', 'hud', 'nature',
         'sketch', 'lava', 'neon', 'holo', 'storm', 'venom', 'butterfly', 'snake',
         'halloween', 'desert', 'neotokyo', 'abyss', 'forest', 'cosmos',
         'samurai', 'steampunk', 'glacier', 'witch', 'dragon', 'graffiti']

# Bar geometry per theme: the side margins come from the skin (what it
# draws past the bar's ends must stay on screen)
def _bar_geometry():
    import wspill
    return {k: dict(margin_x=v) for k, v in wspill.BAR_MARGIN.items()}


BAR_GEOMETRY = _bar_geometry()

# The palettes (also written to theme_colors.bash): bg fg black blackb red
# green yellow blue magenta cyan white accent_color arch_icon
PALETTES = {
    'cyber': ('#0a0614', '#f2e9ff', '#140c26', '#3a2466', '#ff2b6e', '#2bffb1', '#ffe14d', '#19b8ff',
              '#ff2bd6', '#19e6ff', '#c9b8ff', '#1a0f33', '#19e6ff'),
    'minimal': ('#0e1016', '#d8dce6', '#151821', '#3a4058', '#e27d8b', '#9cc9a0', '#e6d3a3', '#a9c2ff',
                '#c3b1e1', '#a3d4e6', '#b8bfcc', '#1a1d27', '#a9c2ff'),
    'pixel': ('#050a1f', '#f2f5ff', '#0a1433', '#1f3a8a', '#ff3b3b', '#3bff6e', '#ffd21e', '#1f5bff',
              '#ff7ad9', '#1ea0ff', '#c8d4ff', '#0c1a4d', '#ffd21e'),
    'liquid': ('#0b1030', '#eaf2ff', '#121a45', '#34408a', '#ff6fb5', '#4fe3d0', '#ffd27a', '#3b6bff',
               '#b37cff', '#34dcff', '#c8d6ff', '#18225e', '#34dcff'),
    'hud': ('#050c18', '#d6ecff', '#08162a', '#16304f', '#ff5c7a', '#3fe0a8', '#ffd166', '#2d8cff',
            '#ffb3c7', '#39d0ff', '#9fc6e8', '#0a1c33', '#39d0ff'),
    'nature': ('#06140c', '#e3ffe9', '#0b1f12', '#1f4a2c', '#ff7a6b', '#2ee06f', '#d9f26b', '#42d9c6',
               '#9be07a', '#7ff5d6', '#bfe8c8', '#0f2a18', '#b9ff66'),
    'sketch': ('#121212', '#e8e8e8', '#1a1a1a', '#4a4a4a', '#d98080', '#a8c8a0', '#e0d4a8', '#b8c4d8',
               '#c8b8d8', '#b0d0d0', '#bdbdbd', '#1f1f1f', '#e8e8e8'),
    'lava': ('#0e0605', '#ffe6d0', '#180a07', '#4a2014', '#ff3a10', '#ffb020', '#ffd040', '#ff6a10',
             '#ff4a2a', '#ff9a3a', '#e8c0a0', '#261008', '#ff8a1f'),
    'neon': ('#070a18', '#eef0ff', '#0c1024', '#2a2f5a', '#ff4f8a', '#3fffc0', '#ffe45c', '#1e90ff',
             '#d946ef', '#1ec8ff', '#c8ccff', '#12163a', '#1ec8ff'),
    'holo': ('#0a0820', '#f4efff', '#120f30', '#3d3570', '#ff6ab0', '#5ff0e0', '#ffd98a', '#6aa8ff',
             '#c77dff', '#4fd8ff', '#d4ccff', '#1a1545', '#ff8ae0'),
    'storm': ('#060b1c', '#e6f0ff', '#0a1230', '#2a3a70', '#ff5a7a', '#5affc8', '#fff27a', '#3d8bff',
              '#9f7bff', '#7fd8ff', '#cfe0ff', '#0e1a40', '#7fd8ff'),
    'venom': ('#0a0405', '#ffe6e6', '#140608', '#3a1014', '#ff1a2e', '#ff8a5a', '#ffb04a', '#ff2a3a',
              '#d0103a', '#ff6a6a', '#e8c0c0', '#1c0709', '#ff2a3a'),
    'butterfly': ('#120a24', '#fbeaff', '#1a0f33', '#4a2a70', '#ff6ab0', '#9affd0', '#ffe08a', '#c77dff',
                  '#ff7ae0', '#9fb8ff', '#e8d6ff', '#22123f', '#ff9ae8'),
    'snake': ('#040f06', '#e8ffe0', '#08180a', '#1f4a22', '#ff6a4a', '#7dff2e', '#e8ff5a', '#5aff7a',
              '#b8ff3a', '#3affc8', '#c8f0c0', '#0a2410', '#9dff3a'),
    'halloween': ('#0d0612', '#ffe8d6', '#170a1c', '#3e2346', '#ff3b2f', '#9cff57', '#ffc43d', '#ff7a1a',
                  '#c04dff', '#ff9e4a', '#e8cfc0', '#1f0e26', '#ff7a1a'),
    'desert': ('#140904', '#ffeccc', '#1f1007', '#5a3418', '#e8502a', '#7fbf4a', '#ffd25a', '#ffb52e',
               '#e8763a', '#f2c27a', '#e8d2b0', '#2a160a', '#ffb52e'),
    'neotokyo': ('#07041a', '#f4e8ff', '#0e0828', '#3a2466', '#ff3a7a', '#3affc8', '#ffd23a', '#e03cff',
                 '#ff3ab4', '#3ad8ff', '#cdb8ff', '#160c3a', '#e03cff'),
    'abyss': ('#010a1c', '#dff8ff', '#04142c', '#14406a', '#ff5a7a', '#2affc8', '#c8ff6a', '#2ccfff',
              '#4a8cff', '#5af0ff', '#a8d8f0', '#06203e', '#2ccfff'),
    'forest': ('#060f04', '#efffd8', '#0c1a08', '#2e4a18', '#ff5a3a', '#b8f02e', '#ffe066', '#9ce02e',
               '#e8a03a', '#7af0a0', '#cfe8b0', '#13260a', '#b8f02e'),
    'cosmos': ('#04051a', '#e8ecff', '#0a0c2a', '#2a2e6a', '#ff5a8a', '#5affd8', '#ffe08a', '#6a6cff',
               '#c04dff', '#5ac8ff', '#c8ccff', '#12144a', '#8a8cff'),
    'samurai': ('#0e0406', '#ffe8e8', '#1a080b', '#4a1a22', '#ff2a2a', '#ff8ab0', '#ffb84a', '#ff3a3a',
                '#c04a8a', '#ff6a5a', '#e8c8c8', '#260a10', '#ff3a3a'),
    'steampunk': ('#0f0804', '#ffe8c8', '#1a0f07', '#5a3a1a', '#d8502a', '#5ab89a', '#ffc85a', '#f0a13a',
                  '#c8622a', '#e8b878', '#d8c0a0', '#24140a', '#f0a13a'),
    'glacier': ('#030a18', '#e8f6ff', '#071428', '#24406a', '#ff6a8a', '#6affe0', '#ffe8a8', '#4fc8ff',
                '#8aa8ff', '#8af0ff', '#b8d8f0', '#0c1e3a', '#4fc8ff'),
    'witch': ('#0a0418', '#f4e8ff', '#130a26', '#3a2066', '#ff4a6a', '#7aff9a', '#ffb347', '#b43cff',
              '#ef57f9', '#9a7aff', '#d0b8f0', '#1c0e36', '#b43cff'),
    'dragon': ('#120503', '#fff0d0', '#1e0a05', '#5a2410', '#e8322a', '#f0b030', '#ffd84a', '#ffb22e',
               '#ff5a3a', '#ffc87a', '#f0d0a8', '#2a0e06', '#ffc42e'),
    'graffiti': ('#0a0614', '#f8f0ff', '#120c22', '#3a2a5a', '#ff2a5a', '#3aff6a', '#ffe014', '#25ebf5',
                 '#eb1fed', '#3ab0ff', '#d8d0f0', '#1a1030', '#eb1fed'),
}
PAL_KEYS = ['bg', 'fg', 'black', 'blackb', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white',
            'accent_color', 'arch_icon']


def palette(kit):
    return dict(zip(PAL_KEYS, PALETTES[kit]))


def palette_bash(kit):
    """The cargar_* function of a kit for theme_colors.bash."""
    p = palette(kit)
    lines = [f'# {KITS[kit]["name"]} ({KITS[kit]["tagline"]}) -- RiceEditor -> Themes',
             f'{KITS[kit]["palette"]}() {{']
    for k in ('bg', 'fg', 'black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white', 'blackb'):
        lines.append(f'    {k}="{p[k]}"')
    for k in ('red', 'green', 'yellow', 'blue', 'magenta', 'cyan'):
        lines.append(f'    {k}b="{p[k]}"')
    lines += [f'    whiteb="{p["fg"]}"', f'    accent_color="{p["accent_color"]}"',
              f'    arch_icon="{p["arch_icon"]}"', '    gtk_themeb="TokyoNight-zk"', '}']
    return '\n'.join(lines) + '\n'


def ensure_palettes():
    """Append the kits' palettes to theme_colors.bash and list them in
    theme-config.bash (commented) when they are missing."""
    colors = os.path.join(bc.rice_dir(), 'theme_colors.bash')
    text = open(colors).read()
    add = ''.join('\n' + palette_bash(k) for k in ORDER if f'{KITS[k]["palette"]}()' not in text)
    if add:
        with open(colors, 'a') as f:
            f.write(add)
    cfg = bc.theme_cfg()
    lines = open(cfg).read().splitlines(keepends=True)
    have = {m.group(1) for ln in lines for m in [re.match(r'^#?(cargar_\w+)\s*$', ln)] if m}
    missing = [KITS[k]['palette'] for k in ORDER if KITS[k]['palette'] not in have]
    if missing:
        last = max(i for i, ln in enumerate(lines) if re.match(r'^#?cargar_\w+\s*$', ln))
        lines[last + 1:last + 1] = [f'\n#{fn}\n' for fn in missing]
        _write(cfg, ''.join(lines))


def _write(path, text):
    tmp = path + '.ricekit.tmp'
    with open(tmp, 'w') as f:
        f.write(text)
    try:
        import shutil
        shutil.copymode(path, tmp)
    except OSError:
        pass
    os.replace(tmp, path)


def set_var(name, value):
    """NAME="value" in theme-config.bash (added at the end when missing)."""
    path = bc.theme_cfg()
    text = open(path).read()
    pat = re.compile(rf'^({re.escape(name)}=)("[^"]*"|\'[^\']*\'|[^\s#]*)(.*)$', re.M)
    m = pat.search(text)
    if m:
        q = m.group(2)[:1] if m.group(2)[:1] in '"\'' else '"'
        text = text[:m.start()] + f'{name}={q}{value}{q}{m.group(3)}' + text[m.end():]
    else:
        text = text.rstrip('\n') + f'\n{name}="{value}"\n'
    _write(path, text)


def get_var(name, default=''):
    m = re.search(rf'^{re.escape(name)}=["\']?([^"\'\s#]*)', open(bc.theme_cfg()).read(), re.M)
    return m.group(1) if m else default


def set_palette(func):
    path = bc.theme_cfg()
    lines = open(path).read().splitlines(keepends=True)
    for i, line in enumerate(lines):
        m = re.match(r'^#?(cargar_\w+)\s*$', line)
        if m:
            lines[i] = (m.group(1) if m.group(1) == func else '#' + m.group(1)) + '\n'
    _write(path, ''.join(lines))


def set_gap(gap):
    rc = os.path.join(bc.BSPWM, 'bspwmrc')
    text = open(rc).read()
    new = re.sub(r'^(bspc config window_gap\s+)\S+', rf'\g<1>{gap}', text, count=1, flags=re.M)
    if new != text:
        _write(rc, new)
    subprocess.run(['bspc', 'config', 'window_gap', str(gap)], capture_output=True)


def palette_accent(func):
    """The color a palette recolors the theme's decorations to: a theme's
    palette gives that theme's own accent, others their blue."""
    import wspill
    for k, kit in KITS.items():
        if kit['palette'] == func:
            return wspill.NATIVE[k]
    text = open(os.path.join(bc.rice_dir(), 'theme_colors.bash')).read()
    m = re.search(rf'^{re.escape(func)}\s*\(\)\s*\{{(.*?)^\}}', text, re.M | re.S)
    blue = re.search(r'\bblue="(#[0-9A-Fa-f]{6})"', m.group(1)) if m else None
    return blue.group(1).lower() if blue else None


def current():
    return get_var('RICE_KIT', '')


def apply(kit, parts, run=True):
    """Write every file the chosen parts touch, then re-apply the rice
    (Theme.sh when colors/windows changed, BarCtl otherwise). One at a time."""
    import fcntl
    lock = open(os.path.join(os.environ.get('XDG_RUNTIME_DIR', '/tmp'), f'ricekit-{os.getuid()}.lock'), 'w')
    fcntl.flock(lock, fcntl.LOCK_EX)
    try:
        _apply(kit, parts, run)
    finally:
        lock.close()


def _apply(kit, parts, run):
    k = KITS[kit]
    parts = [p for p, *_ in PARTS if p in parts]
    ensure_palettes()
    # a theme brings its own colors back to what it applies
    import wspill
    wspill.set_tint([{'colors': 'locks'}.get(p, p) for p in parts if p not in ('wallpaper', 'cursor')], None)
    if 'colors' in parts:
        set_palette(k['palette'])
        pal = palette(kit)
        set_var('dunst_frame_color', pal['blue'])
    if 'windows' in parts:
        set_var('WIN_STYLE', 'custom')
        for name, value in k['win'].items():
            if name == 'gap':
                set_gap(value)
            else:
                set_var(name, value)
        set_var('P_SHADOWS', 'true')
        set_var('WIN_SKIN', kit)   # styled frames around the windows (bin/RoundBorders)
        # the theme's background shows through slightly translucent terminals
        set_var('WIN_BACKDROP', 'true')
        set_var('P_TERM_OPACITY', '0.45')
        set_var('dunst_corner_radius', k['dunst_r'])
    if 'bar' in parts or 'workspaces' in parts:
        conf = bc.load()
        if 'bar' in parts:
            conf['bar_skin'] = kit
            conf['border'] = False
            conf.update(BAR_GEOMETRY.get(kit, {}))
        if 'workspaces' in parts:
            conf['ws_style'] = kit
        bc.save(conf)
    if 'cursor' in parts:
        # the theme's own animated cursor (config/modules/03-gtk.sh draws it)
        set_var('gtk_cursor', 'Rice-Animated')
        set_var('CURSOR_KIT', kit)
    wall = theme_wall(kit) if 'wallpaper' in parts else ''
    if wall:
        set_var('ENGINE', 'Default')
        set_var('DEFAULT_WALL', wall)
    if all(p in parts for p in STYLE_PARTS):
        set_var('RICE_KIT', kit)
    if not run:
        return
    theme = os.path.join(bc.BSPWM, 'bin/Theme.sh')
    if 'colors' in parts or 'windows' in parts or 'cursor' in parts:
        cmd = [theme]   # its wallpaper module paints DEFAULT_WALL too
    elif 'bar' in parts or 'workspaces' in parts:
        cmd = [os.path.join(bc.BSPWM, 'bin/BarCtl'), 'apply']
    else:
        cmd = None
    if wall and cmd != [theme]:
        paint_wall(wall)
    if not cmd:
        return
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90,
                       start_new_session=True)
    except subprocess.TimeoutExpired:
        pass   # it keeps going on its own; the files are already written


# ═══════════════════════════════════════════════════════════ preview
def preview(cr, kit, W, H, wall=None):
    """A small desktop in the theme: its wallpaper (a cairo surface, else
    palette tones), bar, workspaces and two tiled windows (RiceEditor ->
    Themes tiles)."""
    import math
    import cairo
    import wspill as ws
    pal = {k: ws.rgb(v) for k, v in palette(kit).items()}
    k = KITS[kit]
    cr.set_source_rgb(*pal['bg'])
    cr.paint()
    if wall is not None:   # the theme's wallpaper, cover-scaled, a bit darker
        sw, sh = wall.get_width(), wall.get_height()
        sc = max(W / sw, H / sh)
        cr.save()
        cr.scale(sc, sc)
        cr.set_source_surface(wall, (W / sc - sw) / 2, (H / sc - sh) / 2)
        cr.paint()
        cr.restore()
        cr.set_source_rgba(*pal['bg'], 0.25)
        cr.paint()
    else:   # palette glow blobs
        for fx, fy, key, a in ((0.2, 0.9, 'blue', 0.35), (0.85, 0.25, 'magenta', 0.30), (0.55, 0.6, 'cyan', 0.12)):
            g = cairo.RadialGradient(W * fx, H * fy, 0, W * fx, H * fy, W * 0.55)
            g.add_color_stop_rgba(0, *pal[key], a)
            g.add_color_stop_rgba(1, *pal[key], 0)
            cr.set_source(g)
            cr.paint()
    # bar + workspaces at a 1280 px wide virtual screen
    s = W / 820
    cr.save()
    cr.scale(s, s)
    VW, bar_h, off = 820, 30, 8
    m = ws.metrics(6, bar_h)
    mx = BAR_GEOMETRY.get(kit, {}).get('margin_x', 12) * 0.6
    ws.paint_bar(cr, kit, VW, (mx, off, VW - 2 * mx, bar_h), pal)
    cr.save()
    cr.translate((VW - m['win_w']) / 2, off - m['ext'])
    ws.paint(cr, kit, m, ['occupied', 'focused', 'empty', 'empty', 'occupied', 'empty'])
    cr.restore()
    # windows
    gap = k['win']['gap'] * 1.4
    top = off + bar_h + gap + 6
    VH = H / s
    wr = k['win']['P_CORNER_R']
    bw = max(1, k['win']['BORDER_WIDTH'])
    colw = (VW - 3 * gap) / 2
    for i, (x, focused) in enumerate(((gap, True), (gap * 2 + colw, False))):
        y, h = top, VH - top - gap
        bc_ = ws.rgb(k['win']['FOCUSED_BC' if focused else 'NORMAL_BC'])
        glow = ws.rgb(k['win']['SHADOW_C'])
        for e, a in ((24, 0.10), (12, 0.16)):
            ws.rounded(cr, x - e / 2, y - e / 2 + 6, colw + e, h + e, wr + e / 2)
            cr.set_source_rgba(*glow, a if focused else a * 0.5)
            cr.fill()
        ws.rounded(cr, x, y, colw, h, wr)
        alpha = float(k['win']['P_ACTIVE_OPACITY' if focused else 'P_INACTIVE_OPACITY'])
        if wall is not None:   # let the theme's wallpaper show through the windows
            alpha *= 0.5
        cr.set_source_rgba(*pal['black'], alpha)
        cr.fill()
        if k['win']['BORDER_WIDTH']:
            ws.rounded(cr, x + bw / 2, y + bw / 2, colw - bw, h - bw, max(0, wr - bw / 2))
            cr.set_source_rgb(*bc_)
            cr.set_line_width(bw * 2)
            cr.stroke()
        # fake terminal / editor lines in palette colors
        keys = ['blue', 'magenta', 'cyan', 'green', 'yellow', 'red']
        if i == 0:   # a terminal: prompt + a few output lines
            for r in range(min(7, int((h - 50) / 34))):
                ly = y + 30 + r * 34
                ws.rounded(cr, x + 22, ly, 34, 12, 6)
                cr.set_source_rgba(*pal[keys[r % 3]], 0.9)
                cr.fill()
                width = colw * (0.2 + 0.35 * abs(math.sin(r * 1.7)))
                ws.rounded(cr, x + 64, ly, width, 12, 6)
                cr.set_source_rgba(*pal['fg'], 0.35)
                cr.fill()
        else:        # color swatches of the palette
            sw = (colw - 60) / 6
            for n, key in enumerate(keys):
                ws.rounded(cr, x + 30 + n * sw, y + 30, sw - 8, sw - 8, 8 if wr else 0)
                cr.set_source_rgb(*pal[key])
                cr.fill()
            for r in range(3):
                ws.rounded(cr, x + 30, y + 50 + sw + r * 30, colw * (0.7 - r * 0.15), 12, 6)
                cr.set_source_rgba(*pal['fg'], 0.25)
                cr.fill()
    cr.restore()
