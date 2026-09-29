#!/usr/bin/env bash
# ==============================================================================
#  TechOGR · BSPWM dotfiles installer (rice "crackone")
#  https://github.com/TechOGR/bspwm_dotfiles_arch
#
#    git clone https://github.com/TechOGR/bspwm_dotfiles_arch.git
#    cd bspwm_dotfiles_arch
#    ./install.sh
#
#  This only makes sure the installer can run (Arch-based system, your user,
#  Python) and then hands over to install.py, which does everything else.
#  Any option is passed along:  ./install.sh --help
#
#  Copyright (C) 2021-2026 TechOGR <https://github.com/TechOGR> · GPL-3.0
# ==============================================================================

set -uo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

if [[ -t 1 && "${TERM:-dumb}" != dumb ]]; then
    R=$'\e[0m' B=$'\e[1m' RED=$'\e[38;5;204m' YEL=$'\e[38;5;221m' VIO=$'\e[38;5;141m' DIM=$'\e[2m'
else
    R='' B='' RED='' YEL='' VIO='' DIM=''
fi

die() {
    printf '\n  %s%s✖ %s%s\n\n' "$RED" "$B" "$1" "$R" >&2
    exit 1
}

# ── the basics
[[ $EUID -ne 0 ]] || die "No lo ejecutes como root ni con sudo: ./install.sh (la contraseña se pide cuando hace falta)."
[[ "$(uname -m)" == x86_64 ]] || die "Arquitectura $(uname -m): el rice es para x86_64."
command -v pacman >/dev/null 2>&1 || die "No hay pacman: este instalador es para Arch Linux y derivadas."
command -v sudo >/dev/null 2>&1 || die "Falta sudo. Como root: pacman -S sudo, y añade tu usuario al grupo wheel."
[[ -f "$HERE/install.py" && -d "$HERE/config/bspwm" ]] ||
    die "Ejecútalo desde la carpeta del repositorio (falta install.py o config/bspwm)."

# ── what install.py itself needs, on a minimal Arch (a fresh archinstall)
need=()
command -v python3 >/dev/null 2>&1 || need+=(python)
command -v rsync >/dev/null 2>&1 || need+=(rsync)
command -v git >/dev/null 2>&1 || need+=(git)
command -v curl >/dev/null 2>&1 || need+=(curl)
command -v lspci >/dev/null 2>&1 || need+=(pciutils)
if ((${#need[@]})); then
    printf '\n  %s%s➜%s Preparando el instalador: %s%s%s\n' "$VIO" "$B" "$R" "$B" "${need[*]}" "$R"
    printf '  %sTu contraseña de administrador (sudo):%s\n' "$DIM" "$R"
    # the whole system: installing on a half-updated Arch (partial upgrade) breaks it
    sudo pacman -Syu --needed --noconfirm "${need[@]}" ||
        die "No se pudo instalar ${need[*]}. Revisa la conexión y los mirrors (/etc/pacman.d/mirrorlist)."
fi

# the terminal's language: accents and box drawing need UTF-8
if ! locale 2>/dev/null | grep -qi 'utf-\?8'; then
    for l in C.UTF-8 en_US.UTF-8 es_ES.UTF-8; do
        if locale -a 2>/dev/null | grep -qix "${l/UTF-8/utf8}"; then export LANG="$l" LC_ALL="$l"; break; fi
    done
    [[ -n "${LC_ALL:-}" ]] || printf '  %s▲ El idioma del sistema no es UTF-8: algunos símbolos pueden verse raros.%s\n' "$YEL" "$R"
fi

exec python3 "$HERE/install.py" "$@"
