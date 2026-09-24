#!/bin/sh

pick_random_wall() {
    find "$1" -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.webp' \) | shuf -n 1
}

set_wall() {
    VideoWall --stop    # a picture replaces the video wallpaper
    feh --bg-fill "$1"
    WallSync &
}

    case $ENGINE in
        "Random")
            set_wall "$(pick_random_wall "$HOME/.config/bspwm/rices/$RICE/walls")"
            ;;
        "CustomDir")
            set_wall "$(pick_random_wall "$CUSTOM_DIR")"
            ;;
        "Default")
            set_wall "$DEFAULT_WALL"
            ;;
        "Animated")
            # video of walls/videos (VideoWall sets a still of it as the
            # picture wallpaper + WallSync by itself)
            VideoWall --start "$ANIMATED_WALL"
            ;;
        "Slideshow")
            (
                while :; do
                    set_wall "$(pick_random_wall "$HOME/.config/bspwm/rices/$RICE/walls")"
                    sleep 900  # 15 minutos
                    WallSync &
                done
            ) &
            echo $! > /tmp/wall_refresh.pid
            ;;
        *)
            set_wall "$(pick_random_wall "$HOME/.config/bspwm/rices/$RICE/walls")"
            ;;
    esac
