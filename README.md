# SpriteLite
================

## Overview

<p align="center">
  <img src="icon.ico" alt="SpriteLite icon" width="96">
</p>

SpriteLite is a lightweight, performance-oriented pixel editor designed for older machines. Built with Tkinter, it aims to provide a responsive, compact, and easy-to-use interface for sprite work and small pixel art projects.

## Features
------------

### Drawing Tools

- Lightweight single-file desktop app built around Tkinter.
- Pixel-focused drawing tools including:
  - Pencil
  - Eraser
  - Bucket fill
  - Eyedropper
  - Selection
- Layer-based editing with:
  - Visibility toggles
  - Duplication
  - Renaming
  - Ordering

### File Support

- PNG import/export
- `.sprlite` project save/load support

### Editing Features

- Zoom
- Pan
- Grid display
- Undo/redo
- Palette loading

## Project Goal
--------------

SpriteLite prioritizes speed, simplicity, and focus on the core editing workflow. It is designed to start quickly, run well on older hardware, and maintain a direct approach to pixel editing.

## Requirements
--------------

- Python 3
- Pillow

### Installation

Install the dependency with:

```bash
pip install -r requirements.txt
```

## Running from Source
----------------------

```bash
python main.py
```

If your system uses the Python launcher instead of `python`, use:

```bash
py main.py
```

## Building
------------

### Windows

```bash
.\build-win.ps1
```

Build both Windows variants in separate output folders:

```bash
.\build-win.ps1 -Arch both
```

This writes the executables to `dist\win64\SpriteLite.exe` and `dist\win32\SpriteLite-win32.exe`.

### Linux

```bash
./build-linux.sh
```

## Download
------------

Download the latest built version from the releases page:

https://github.com/elevchyt/spritelite/releases

## License
--------

SpriteLite is released under the [GNU General Public License v3](LICENSE). See the `LICENSE` file for details.