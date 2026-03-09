# SpriteLite

<p align="center">
  <img src="icon.ico" alt="SpriteLite icon" width="96">
</p>

SpriteLite is a simple, lightweight pixel editor built with Tkinter and designed with performance in mind for older machines. The goal is to keep the editor responsive, compact, and easy to use while still covering the core workflow needed for sprite work and small pixel art projects.

## Features

- Lightweight single-file desktop app built around Tkinter.
- Pixel-focused drawing tools including pencil, eraser, bucket fill, eyedropper, and selection.
- Layer-based editing with visibility toggles, duplication, renaming, and ordering.
- PNG import/export and `.sprlite` project save/load support.
- Zoom, pan, grid display, undo/redo, and palette loading.

## Project Goal

SpriteLite is meant to stay small, direct, and fast. The emphasis is not on a huge feature surface, but on making a pixel editor that starts quickly, runs well on older hardware, and stays focused on the core editing workflow.

## Requirements

- Python 3
- Pillow

Install the dependency with:

```powershell
pip install -r requirements.txt
```

## Run From Source

```powershell
python main.py
```

If your system uses the Python launcher instead of `python`, use:

```powershell
py main.py
```

## Build

Windows:

```powershell
.\build-win.ps1
```

Build both Windows variants in separate output folders:

```powershell
.\build-win.ps1 -Arch both
```

This writes the executables to `dist\win64\SpriteLite.exe` and `dist\win32\SpriteLite-win32.exe`.
Each build still requires the matching Python interpreter to be installed locally because PyInstaller cannot cross-compile.

Linux:

```bash
./build-linux.sh
```

## Download

Download the latest built version from the releases page:

https://github.com/elevchyt/spritelite/releases
