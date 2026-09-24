#############################
#    CrackOne Theme         #
#############################
# https://github.com/TechOGR/bspwm_dotfiles_arch.git

# Cargar Paletas de Colores
source "$HOME/.config/bspwm/rices/crackone/theme_colors.bash"
#--Tokyo Night--
cargar_tokyo_night
#--Obsidian Deep--
#cargar_obsidian_deep
#--Cyber Sunset--
#cargar_cyber_sunset
#--Deep Ocean--
#cargar_deep_ocean
#--Minimal Gold --
#cargar_minimal_gold
#-- Cold Frost--
#cargar_cold_frost


# Bspwm options
BORDER_WIDTH="0"		# Bspwm border
TOP_PADDING="30"
BOTTOM_PADDING="1"
LEFT_PADDING="1"
RIGHT_PADDING="1"
NORMAL_BC="#414868"		# Normal border color
FOCUSED_BC="#bb9af7"	# Focused border color

# Terminal font & size
term_font_size="10"
term_font_name="JetBrainsMono Nerd Font"

# Picom options
P_FADE="true"			# Fade true|false
P_SHADOWS="true"		# Shadows true|false
SHADOW_C="#000000"		# Shadow color
P_CORNER_R="10"			# Corner radius (0 = disabled)
P_BLUR="true"			# Blur true|false
P_ANIMATIONS="@"		# (@ = enable) (# = disable)
P_TERM_OPACITY="1.0"	# Terminal transparency. Range: 0.1 - 1.0 (1.0 = disabled)
P_ACTIVE_OPACITY="0.97"	# Focused windows opacity. Range: 0.5 - 1.0
P_INACTIVE_OPACITY="0.92"	# Unfocused windows opacity. Range: 0.5 - 1.0

# Dunst
dunst_offset='(20, 60)'
dunst_origin='top-right'
dunst_transparency='0'
dunst_corner_radius='6'
dunst_font='JetBrainsMono NF Medium 9'
dunst_border='0'
dunst_frame_color="$accent_color"
dunst_icon_theme="TokyoNight-SE"
# Dunst animations
dunst_close_preset="fly-out"
dunst_close_direction="up"
dunst_open_preset="fly-in"
dunst_open_direction="up"

# Jgmenu colors
jg_bg="$bg"
jg_fg="$fg"
jg_sel_bg="$accent_color"
jg_sel_fg="$fg"
jg_sep="$blackb"

# Rofi menu font and colors
rofi_font="JetBrainsMono NF Bold 9"
rofi_background="$bg"
rofi_bg_alt="$accent_color"
rofi_background_alt="${bg}E0"
rofi_fg="$fg"
rofi_selected="$blue"
rofi_active="$green"
rofi_urgent="$red"
rofi_border="$cyan"

# Screenlocker
sl_bg="${bg}"
sl_fg="${fg}"
sl_ring="${black}"
sl_wrong="${red}"
sl_date="${fg}"
sl_verify="${green}"
LOCK_ACCENT="${blue}"	# Ring highlight + glass panel border
LOCK_BLUR="0"			# Wallpaper blur on lockscreen (0-30)
LOCK_DIM="20"			# Wallpaper darkening in % (0-80)
LOCK_POS="left"			# Clock/ring position: left | center | right
LOCK_GLASS="true"		# Frosted glass panel behind the clock true|false
LOCK_CLOCK="%H:%M"		# Clock format (strftime)
LOCK_GREETER="Type the password to Unlock"

# Login lock (betterlockscreen + BetterLock, RiceEditor -> Login Lock)
BL_WALL="current"		# current | random | custom
BL_WALL_PATH=""			# Picture used when BL_WALL=custom
BL_FX="dimblur"			# none | dim | blur | dimblur | pixel | dimpixel | color
BL_DIM="35"				# Darkening in % (0-90)
BL_BLUR="10"			# Blur strength (1-40)
BL_PIXEL="14"			# Pixel block size (4-60)
BL_POS="center"			# Login card position: left | center | right
BL_CARD="true"			# Frosted glass login card true|false
BL_CARD_ALPHA="55"		# Card tint in % (0-95)
BL_RADIUS="28"			# Card corner radius
BL_AVATAR="true"		# AvatarForge avatar in the card true|false
BL_SHAPE="circle"		# Avatar shape: circle | squircle | hexagon
BL_NAME=""				# Name on the card (empty = user name)
BL_GREETER="Type your password"
BL_MESSAGE=""			# Bottom line, e.g. contact info
BL_CLOCK="%H:%M"		# Clock format (strftime)
BL_DATE="%A, %d %B"		# Date format (strftime)
BL_INDICATOR="ring"		# ring (around the avatar) | bar
BL_ACCENT="${blue}"		# Ring / keypress / date
BL_ACCENT2="${magenta}"	# Gradient of the card border, now playing
BL_FG="${fg}"			# Texts
BL_VERIFY="${green}"	# Verifying
BL_WRONG="${red}"		# Wrong password / Caps Lock
BL_LAYOUT="true"		# Keyboard layout under the password field
BL_MEDIA="true"			# Now playing (playerctl) at the bottom
BL_OFF="60"				# Seconds until the display turns off while locked
BL_IDLE="0"				# Auto-lock after N idle minutes (0 = never)
BL_SUSPEND="true"		# Lock before suspend (xss-lock)

# Gtk theme
gtk_theme="$gtk_themeb"
gtk_icons="TokyoNight-SE"
gtk_cursor="Bibata-Modern-Classic"
geany_theme="z0mbi3-TokyoNight"

# Wallpaper engine
# Available engines:
# - Random  (Set a random wallpaper from Walls rice directory)
# - CustomDir   (Set a random wallpaper from the directory you specified)
# - Default (Sets a specific image as wallpaper) *Default
# - Animated (Set an animated wallpaper. "mp4, mkv, gif")
# - Slideshow (Change randomly every 15 minutes your wallpaper from Walls rice directory)
ENGINE="Default"

CUSTOM_DIR="$HOME/Imágenes/Wallpapers"
DEFAULT_WALL="/home/t3ch0gr/.config/bspwm/rices/crackone/walls/pirate-ship-island-digital-art-4k-wallpaper-uhdpaper.com-659@2@b.jpg"
ANIMATED_WALL="$HOME/.config/bspwm/config/assets/animated_wall.mp4"
