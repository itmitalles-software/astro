#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Install Astro into the current user's kitty configuration.
#
# Existing files that Astro replaces are moved to a timestamped backup
# directory next to the kitty configuration first.
set -eu

mode=install
restore_dir=
case "$#:${1-}" in
    0:) ;;
    1:--help|1:-h)
        printf '%s\n' \
            'Usage: ./install.sh [--restore BACKUP_DIR]' \
            'Install Astro for the current user; running panes and jobs stay open.' \
            'Use --restore BACKUP_DIR to restore files from an astro-backup-* directory.' \
            'Staging: KITTY_CONFIG_DIRECTORY, XDG_DATA_HOME, ASTRO_BIN_DIRECTORY, ASTRO_BASHRC.' \
            'Set ASTRO_REPLACE_SESSION=1 to replace the default session with a backup.'
        exit 0 ;;
    2:--restore)
        if [ -z "${2-}" ] || [ -L "$2" ] || [ ! -d "$2" ]; then
            printf 'Error: backup directory not found: %s\n' "${2-}" >&2
            exit 2
        fi
        mode=restore
        restore_dir=$(CDPATH='' cd -- "$2" && pwd) ;;
    *) printf '%s\n' 'Error: unexpected arguments. Run ./install.sh --help.' >&2; exit 2 ;;
esac

here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
if ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' 'Error: Python 3 is required for Astro. Nothing installed.' >&2
    exit 1
fi
# The helper holds stable private locks across this entire shell, including the
# hook update and cache refreshes. Passing the body avoids a bypass/re-entry flag.
exec python3 "$here/tools/install_bash_hook.py" --run-installer "$here" "$mode" "$restore_dir" <<'ASTRO_INSTALL_BODY'
here=$1
mode=${2:-install}
restore_dir=${3-}
config_dir=${KITTY_CONFIG_DIRECTORY:-${XDG_CONFIG_HOME:-$HOME/.config}/kitty}
data_dir=${XDG_DATA_HOME:-$HOME/.local/share}
font_dir=$data_dir/fonts/astro-pane-controls
bin_dir=${ASTRO_BIN_DIRECTORY:-$HOME/.local/bin}
bashrc=${ASTRO_BASHRC:-$HOME/.bashrc}
supported=0.49.2
config_files='kitty.conf window_title_bar.py reload_pane_controls.py astro_clipboard.py astro_remote.py ssh_input.conf astro_intro.py astro.bash astro_prompt.bash sessions/default.conf'
replace_session=${ASTRO_REPLACE_SESSION:-0}

if [ "$mode" = restore ]; then
    restore_entry() {
        if [ -e "$restore_dir/$2" ] || [ -L "$restore_dir/$2" ]; then
            mkdir -p "$(dirname "$1")"
            mv -f "$restore_dir/$2" "$1"
        fi
    }
    for file in $config_files; do
        restore_entry "$config_dir/$file" "$file"
    done
    restore_entry "$config_dir/kitty.app.png" kitty.app.png
    restore_entry "$data_dir/applications/astro.desktop" desktop/astro.desktop
    restore_entry "$bin_dir/astro" bin/astro
    restore_entry "$data_dir/icons/hicolor/scalable/apps/astro.svg" icons/astro.svg
    for size in 32 64 128 256 512; do
        restore_entry "$data_dir/icons/hicolor/${size}x${size}/apps/astro.png" "icons/astro-$size.png"
    done
    restore_entry "$font_dir/AstroPaneControls.ttf" fonts/AstroPaneControls.ttf
    python3 "$here/tools/install_bash_hook.py" --restore "$bashrc" "$restore_dir/bashrc"
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$data_dir/applications"
    fi
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -f -t "$data_dir/icons/hicolor" >/dev/null 2>&1 || :
    fi
    if command -v fc-cache >/dev/null 2>&1; then
        fc-cache -f "$font_dir"
    fi
    printf 'Restored backed-up files from: %s\n' "$restore_dir"
    exit 0
fi

case "$replace_session" in
    0|1) ;;
    *) printf '%s\n' 'Error: ASTRO_REPLACE_SESSION must be 0 or 1. Nothing installed.' >&2; exit 1 ;;
esac
# Check all packaged inputs and the managed hook before replacing user files.
require_source() {
    if [ ! -f "$1" ] || [ ! -r "$1" ]; then
        printf 'Error: missing or unreadable source: %s. Nothing installed.\n' "$1" >&2
        exit 1
    fi
}
for file in $config_files; do
    require_source "$here/config/$file"
    if [ -d "$config_dir/$file" ]; then
        printf 'Error: expected a file, found directory: %s. Nothing installed.\n' "$config_dir/$file" >&2
        exit 1
    fi
done
for file in assets/astro.desktop assets/astro.svg bin/astro fonts/AstroPaneControls.ttf tools/install_bash_hook.py; do
    require_source "$here/$file"
done
for size in 32 64 128 256 512; do require_source "$here/assets/astro-$size.png"; done
# Validate every output, including nested parents, before the first replacement.
set -- "$config_dir/kitty.app.png" "$data_dir/applications/astro.desktop" "$bin_dir/astro" \
    "$data_dir/icons/hicolor/scalable/apps/astro.svg" "$font_dir/AstroPaneControls.ttf"
for file in $config_files; do
    if [ "$file" = sessions/default.conf ] && [ "$replace_session" != 1 ] && { [ -e "$config_dir/$file" ] || [ -L "$config_dir/$file" ]; }; then
        continue
    fi
    set -- "$@" "$config_dir/$file"
done
for size in 32 64 128 256 512; do set -- "$@" "$data_dir/icons/hicolor/${size}x${size}/apps/astro.png"; done
python3 "$here/tools/install_bash_hook.py" --preflight "$here" "$@"
python3 "$here/tools/install_bash_hook.py" --check "$bashrc"

if command -v kitty >/dev/null 2>&1; then
    version=$(kitty --version | awk '{print $2}')
    if [ "$version" != "$supported" ]; then
        echo "Warning: Astro is tested with kitty $supported, found $version." >&2
        echo "The pane controls use internal kitty APIs and may not work." >&2
    fi
else
    echo "Warning: kitty not found on PATH." >&2
fi

mkdir -p "$config_dir/sessions" "$font_dir"
backup="$config_dir/astro-backup-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -m 700 "$backup"
report_failure() {
    status=$?
    if [ "$status" -ne 0 ] && [ -d "$backup" ]; then
        printf 'Installation stopped; backup directory: %s\n' "$backup" >&2
        printf 'Restore backed-up files with: %s/install.sh --restore %s\n' "$here" "$backup" >&2
    fi
    trap - EXIT
    exit "$status"
}
trap report_failure EXIT
for file in $config_files; do
    if [ "$file" = sessions/default.conf ] && [ "$replace_session" != 1 ] && { [ -e "$config_dir/$file" ] || [ -L "$config_dir/$file" ]; }; then
        printf 'Keeping personal workspace: %s\n' "$config_dir/$file"
        continue
    fi
    if [ -e "$config_dir/$file" ] || [ -L "$config_dir/$file" ]; then
        mkdir -p "$backup/$(dirname "$file")"
        mv "$config_dir/$file" "$backup/$file"
    fi
    if ! cp "$here/config/$file" "$config_dir/$file"; then
        rm -f "$config_dir/$file"
        exit 1
    fi
done
install_asset() {
    if [ -e "$2" ] || [ -L "$2" ]; then
        mkdir -p "$backup/$(dirname "$3")"
        mv "$2" "$backup/$3"
    fi
    mkdir -p "$(dirname "$2")"
    if ! install -m "$4" "$1" "$2"; then
        rm -f "$2"
        return 1
    fi
}
install_asset "$here/assets/astro-128.png" "$config_dir/kitty.app.png" kitty.app.png 644
install_asset "$here/assets/astro.desktop" "$data_dir/applications/astro.desktop" desktop/astro.desktop 644
install_asset "$here/bin/astro" "$bin_dir/astro" bin/astro 755
install_asset "$here/assets/astro.svg" "$data_dir/icons/hicolor/scalable/apps/astro.svg" icons/astro.svg 644
for size in 32 64 128 256 512; do
    install_asset "$here/assets/astro-$size.png" "$data_dir/icons/hicolor/${size}x${size}/apps/astro.png" "icons/astro-$size.png" 644
done
python3 "$here/tools/install_bash_hook.py" "$bashrc" "$backup/bashrc"
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$data_dir/applications"
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$data_dir/icons/hicolor" >/dev/null 2>&1 || :
fi
install_asset "$here/fonts/AstroPaneControls.ttf" "$font_dir/AstroPaneControls.ttf" fonts/AstroPaneControls.ttf 644
if command -v fc-cache >/dev/null 2>&1; then
    fc-cache -f "$font_dir"
fi

echo "Installation backup directory: $backup"
echo "Astro installed in $config_dir."
echo "Open Astro, or reload existing windows with Ctrl+Shift+F5 (twice when upgrading the default binding)."
echo "New Bash panes load the startup hook; running panes and jobs are not restarted."
ASTRO_INSTALL_BODY
