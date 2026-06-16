# Changelog

All notable changes to SpriteLite are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project uses a simple `MAJOR.MINOR` versioning scheme.

## [1.1] - 2026-06-16

### Added

- Frame-based animation: a timeline at the bottom of the canvas for adding and
  managing frames, a play/stop control, an adjustable playback-speed selector
  (10%–100%), and export to either a spritesheet or individual frame PNGs.
  Existing single-frame projects are migrated automatically. (#6)
- Copy and paste for the selection tool (`Ctrl+C` / `Ctrl+V`), with a small
  offset on paste so a pasted copy doesn't perfectly cover the original. (#1)
- Built-in palette selector that auto-detects palettes from a `palettes` folder
  next to the app and ships with Endesga 32 (default), PICO-8, Paperback-2,
  Miyazaki 16, AGB, and NaNoNES. (#10)
- `Alt+Backspace` fills the active layer with the foreground color, or just the
  selected region when a selection is active. (#2)

### Changed

- Undo/redo now covers layer operations (add, delete, reorder, rename,
  visibility) and animation frame changes, not only canvas edits. (#3)
- Layer items now fill the full width of the layers panel regardless of layer
  name length. (#5)
- The eyedropper tooltip now indicates that holding `Alt` toggles the tool for
  rapid color picking. (#4)

### Fixed

- The eyedropper now samples the composited color across all visible layers
  instead of failing or only reading the active layer. (#12)
- SpriteLite now prompts to save unsaved changes before closing. (#11)

## [1.0] - 2026-03-09

- Initial release: Tkinter-based pixel editor with pencil, eraser, bucket fill,
  eyedropper, and selection tools; layer-based editing; PNG import/export and
  `.sprlite` project save/load; zoom, pan, grid, undo/redo, and palette loading.
- Windows 64-bit, Windows 32-bit, and Linux builds.
