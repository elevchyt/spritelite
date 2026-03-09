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

## Build Script

This repo includes a Windows PowerShell build script at [build.ps1](build.ps1).

It does the following:

- Installs the runtime dependency from [requirements.txt](requirements.txt).
- Installs PyInstaller if needed.
- Builds a single-file Windows executable.
- Embeds [icon.ico](icon.ico) as the `.exe` icon.
- Bundles the `icons` folder and `icon.ico` so the packaged app can use the same assets at runtime.

Run the build script from PowerShell:

```powershell
.\build.ps1
```

To remove old build output first:

```powershell
.\build.ps1 -Clean
```

The generated executable will be written to:

```text
dist\SpriteLite.exe
```

## Export Pipeline

The `.exe` export flow is intentionally simple:

1. Start from the repo root.
2. Run [build.ps1](build.ps1).
3. The script installs dependencies and invokes PyInstaller.
4. PyInstaller packages [main.py](main.py), the toolbar icons in [icons](icons), and [icon.ico](icon.ico).
5. The finished executable is created at `dist\SpriteLite.exe`.

There are two separate icon steps in that pipeline:

- The window title-bar icon inside the running app is set by the Tkinter app code.
- The file icon shown for `SpriteLite.exe` in Windows Explorer is set by PyInstaller using [icon.ico](icon.ico).
