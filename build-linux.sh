#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
dist_binary="$project_root/dist/SpriteLite"

cd "$project_root"

get_python_launcher() {
    if command -v python3 >/dev/null 2>&1; then
        printf '%s\n' "python3"
        return
    fi

    if command -v python >/dev/null 2>&1; then
        printf '%s\n' "python"
        return
    fi

    printf '%s\n' "Python was not found on PATH. Install Python 3 or activate your virtual environment first." >&2
    exit 1
}

clean_build() {
    rm -rf build dist SpriteLite.spec
}

if [[ "${1-}" == "--clean" ]]; then
    clean_build
fi

python_cmd="$(get_python_launcher)"

printf '%s\n' "Installing build dependencies..."
"$python_cmd" -m pip install -r requirements.txt pyinstaller

printf '%s\n' "Building SpriteLite Linux binary..."
"$python_cmd" -m PyInstaller \
    --noconfirm \
    --clean \
    --windowed \
    --onefile \
    --name SpriteLite \
    --add-data "icons:icons" \
    --add-data "icon.ico:." \
    --hidden-import PIL._tkinter_finder \
    main.py

if [[ ! -f "$dist_binary" ]]; then
    printf '%s\n' "Build finished but the binary was not found at $dist_binary" >&2
    exit 1
fi

printf '%s\n' "Build complete: $dist_binary"