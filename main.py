"""
SpriteLite - A lightweight pixel art editor
Single entry point for the application
"""

import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox, simpledialog
import os
import json
import math
import struct
import sys

try:
    from PIL import Image as PILImage, ImageTk as PILImageTk
    PIL_AVAILABLE = True
    PILImage  # Prevent unused import warning
    PILImageTk  # Prevent unused import warning
except ImportError:
    PILImage = None
    PILImageTk = None
    PIL_AVAILABLE = False

if PIL_AVAILABLE:
    IMAGE_NEAREST = PILImage.Resampling.NEAREST if hasattr(
        PILImage, "Resampling") else PILImage.NEAREST
else:
    IMAGE_NEAREST = None


# Color scheme
BG_COLOR = "#1e1e1e"
PANEL_COLOR = "#252526"
BORDER_COLOR = "#3c3c3c"
TEXT_COLOR = "#d4d4d4"
ACCENT_COLOR = "#007acc"

ZOOM_LEVELS = [1, 2, 4, 8, 16]
DEFAULT_ZOOM = ZOOM_LEVELS[-1]

# Endesga 32
DEFAULT_PALETTE = [
    "#BE4A2F", "#D77643", "#EAD4AA", "#E4A672",
    "#B86F50", "#733E39", "#3E2731", "#A22633",
    "#E43B44", "#F77622", "#FEAE34", "#FEE761",
    "#63C74D", "#3E8948", "#265C42", "#193C3E",
    "#124E89", "#0099DB", "#2CE8F5", "#FFFFFF",
    "#C0CBDC", "#8B9BB4", "#5A6988", "#3A4466",
    "#262B44", "#181425", "#FF0044", "#68386C",
    "#B55088", "#F6757A", "#E8B796", "#C28569"
]


def resource_path(relative_path):
    """Resolve asset paths for both source runs and bundled executables."""
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


class HistoryManager:
    """Manages undo/redo operations with memory-efficient layer snapshots."""

    def __init__(self, max_levels=20):
        self.max_levels = max_levels
        self.undo_stack = []
        self.redo_stack = []

    def save_state(self, layer_index, pixel_data):
        """Save a snapshot of a single layer's pixel data."""
        self.undo_stack.append((layer_index, bytearray(pixel_data)))
        self.redo_stack.clear()
        if len(self.undo_stack) > self.max_levels:
            self.undo_stack.pop(0)

    def undo(self, layers):
        """Pop from undo stack, push current state to redo, return state to restore."""
        if not self.undo_stack:
            return None
        layer_index, pixel_data = self.undo_stack.pop()
        self.redo_stack.append(
            (layer_index, bytearray(layers[layer_index].pixels)))
        return layer_index, pixel_data

    def redo(self, layers):
        """Pop from redo stack, push current state to undo, return state to restore."""
        if not self.redo_stack:
            return None
        layer_index, pixel_data = self.redo_stack.pop()
        self.undo_stack.append(
            (layer_index, bytearray(layers[layer_index].pixels)))
        return layer_index, pixel_data

    def can_undo(self):
        return len(self.undo_stack) > 0

    def can_redo(self):
        return len(self.redo_stack) > 0


class Layer:
    """Represents a single layer with pixel data stored as flat bytearray."""

    def __init__(self, name, width, height):
        self.name = name
        self.width = width
        self.height = height
        self.visible = True
        self.pixels = bytearray(width * height * 4)  # RGBA

    def get_pixel(self, x, y):
        idx = (y * self.width + x) * 4
        return bytes(self.pixels[idx:idx + 4])

    def set_pixel(self, x, y, color):
        if 0 <= x < self.width and 0 <= y < self.height:
            idx = (y * self.width + x) * 4
            self.pixels[idx:idx + 4] = color

    def clear(self):
        self.pixels = bytearray(self.width * self.height * 4)

    def copy(self):
        new_layer = Layer(self.name, self.width, self.height)
        new_layer.pixels = bytearray(self.pixels)
        new_layer.visible = self.visible
        return new_layer


class LayerManager:
    """Manages multiple layers with proper compositing."""

    def __init__(self, width, height, history_manager):
        self.width = width
        self.height = height
        self.history = history_manager
        self.layers = [Layer("Layer 1", width, height)]
        self.active_layer_index = 0
        self._composite_cache = None
        self._composite_image_cache = None
        self._composite_dirty = True

    def mark_dirty(self):
        self._composite_dirty = True
        self._composite_cache = None
        self._composite_image_cache = None

    def get_active_layer(self):
        return self.layers[self.active_layer_index]

    def add_layer(self):
        new_layer = Layer(
            f"Layer {len(self.layers) + 1}", self.width, self.height)
        self.layers.append(new_layer)
        self.active_layer_index = len(self.layers) - 1
        self.mark_dirty()
        return self.active_layer_index

    def delete_layer(self, index=None):
        if len(self.layers) <= 1:
            return False

        if index is None:
            index = self.active_layer_index

        self.layers.pop(index)

        if self.active_layer_index > index:
            self.active_layer_index -= 1
        if self.active_layer_index >= len(self.layers):
            self.active_layer_index = len(self.layers) - 1
        self.mark_dirty()
        return True

    def duplicate_layer(self):
        layer = self.get_active_layer()
        new_layer = layer.copy()
        new_layer.name = f"{layer.name} Copy"
        self.layers.insert(self.active_layer_index + 1, new_layer)
        self.active_layer_index += 1
        self.mark_dirty()
        return self.active_layer_index

    def move_layer_up(self):
        if self.active_layer_index < len(self.layers) - 1:
            self.layers[self.active_layer_index], self.layers[self.active_layer_index + 1] = \
                self.layers[self.active_layer_index +
                            1], self.layers[self.active_layer_index]
            self.active_layer_index += 1
            self.mark_dirty()
            return True
        return False

    def move_layer_down(self):
        if self.active_layer_index > 0:
            self.layers[self.active_layer_index], self.layers[self.active_layer_index - 1] = \
                self.layers[self.active_layer_index -
                            1], self.layers[self.active_layer_index]
            self.active_layer_index -= 1
            self.mark_dirty()
            return True
        return False

    def toggle_visibility(self, index):
        self.layers[index].visible = not self.layers[index].visible
        self.mark_dirty()

    def render_composite(self):
        """Render all visible layers to a single RGBA image."""
        if not self._composite_dirty and self._composite_cache is not None:
            return self._composite_cache

        composite = bytearray(self.width * self.height * 4)
        for layer in reversed(self.layers):
            if layer.visible:
                for i in range(0, len(layer.pixels), 4):
                    if layer.pixels[i + 3] > 0:  # Alpha > 0
                        composite[i] = layer.pixels[i]
                        composite[i + 1] = layer.pixels[i + 1]
                        composite[i + 2] = layer.pixels[i + 2]
                        composite[i + 3] = layer.pixels[i + 3]
        self._composite_cache = bytes(composite)
        self._composite_image_cache = None
        self._composite_dirty = False
        return self._composite_cache

    def get_composite_image(self):
        if self._composite_dirty or self._composite_cache is None:
            self.render_composite()
        if self._composite_image_cache is None:
            self._composite_image_cache = PILImage.frombytes(
                "RGBA", (self.width, self.height), self._composite_cache)
        return self._composite_image_cache


class ToolManager:
    """Manages drawing tools."""

    def __init__(self):
        self.current_tool = "pencil"
        self.selection_start = None
        self.selection_end = None
        self.selection_rect = None

    @property
    def selection(self):
        if self.selection_start and self.selection_end:
            x1 = min(self.selection_start[0], self.selection_end[0])
            y1 = min(self.selection_start[1], self.selection_end[1])
            x2 = max(self.selection_start[0], self.selection_end[0])
            y2 = max(self.selection_start[1], self.selection_end[1])
            return (x1, y1, x2, y2)
        return None

    def clear_selection(self):
        self.selection_start = None
        self.selection_end = None

    def set_tool(self, tool):
        self.current_tool = tool
        self.clear_selection()


class PaletteManager:
    """Manages color palette and active colors."""

    def __init__(self):
        self.colors = DEFAULT_PALETTE[:]
        self.foreground = "#000000"
        self.background = "#FFFFFF"

    def load_palette_file(self, filepath):
        ext = os.path.splitext(filepath)[1].lower()
        if ext == ".gpl":
            return self._load_gpl(filepath)
        if ext == ".ase":
            return self._load_ase(filepath)
        elif ext == ".pal":
            return self._load_pal(filepath)
        if ext == ".png":
            return self._load_image_colors(filepath)
        raise ValueError("Unsupported palette format.")

    def _load_gpl(self, filepath):
        colors = []
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                    except ValueError:
                        continue
                    if all(0 <= channel <= 255 for channel in (r, g, b)):
                        colors.append(f"#{r:02X}{g:02X}{b:02X}")
        return self._set_colors(colors)

    def _load_pal(self, filepath):
        colors = []
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = [line.strip() for line in f if line.strip()]

        if lines and lines[0].upper() == "JASC-PAL":
            for line in lines[3:]:
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                    except ValueError:
                        continue
                    if all(0 <= channel <= 255 for channel in (r, g, b)):
                        colors.append(f"#{r:02X}{g:02X}{b:02X}")
        else:
            for line in lines:
                if line.startswith('#') and len(line) == 7:
                    colors.append(line.upper())
                    continue
                parts = line.replace(',', ' ').split()
                if len(parts) >= 3:
                    try:
                        r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                    except ValueError:
                        continue
                    if all(0 <= channel <= 255 for channel in (r, g, b)):
                        colors.append(f"#{r:02X}{g:02X}{b:02X}")

        return self._set_colors(colors)

    def _load_ase(self, filepath):
        colors = []
        with open(filepath, 'rb') as f:
            if f.read(4) != b'ASEF':
                raise ValueError("Invalid ASE file.")

            f.read(4)  # version
            block_count = struct.unpack('>I', f.read(4))[0]

            for _ in range(block_count):
                block_type_data = f.read(2)
                if len(block_type_data) < 2:
                    break

                block_type = struct.unpack('>H', block_type_data)[0]
                block_length = struct.unpack('>I', f.read(4))[0]
                block_data = f.read(block_length)

                if block_type != 0x0001:
                    continue

                color = self._parse_ase_color_block(block_data)
                if color:
                    colors.append(color)

        return self._set_colors(colors)

    def _parse_ase_color_block(self, block_data):
        name_length = struct.unpack('>H', block_data[:2])[0]
        name_end = 2 + name_length * 2
        offset = name_end

        color_model = block_data[offset:offset +
                                 4].decode('ascii', errors='ignore').strip()
        offset += 4

        if color_model == 'RGB':
            components = struct.unpack('>fff', block_data[offset:offset + 12])
            r, g, b = [max(0, min(255, round(component * 255)))
                       for component in components]
            return f"#{r:02X}{g:02X}{b:02X}"

        if color_model == 'GRAY':
            value = struct.unpack('>f', block_data[offset:offset + 4])[0]
            gray = max(0, min(255, round(value * 255)))
            return f"#{gray:02X}{gray:02X}{gray:02X}"

        if color_model == 'CMYK':
            c, m, y, k = struct.unpack('>ffff', block_data[offset:offset + 16])
            r = round(255 * (1 - c) * (1 - k))
            g = round(255 * (1 - m) * (1 - k))
            b = round(255 * (1 - y) * (1 - k))
            return f"#{max(0, min(255, r)):02X}{max(0, min(255, g)):02X}{max(0, min(255, b)):02X}"

        return None

    def _set_colors(self, colors):
        unique_colors = []
        seen_colors = set()
        for color in colors:
            normalized = color.upper()
            if normalized not in seen_colors:
                seen_colors.add(normalized)
                unique_colors.append(normalized)

        if not unique_colors:
            return False

        self.colors = unique_colors[:256]
        return True

    def _load_image_colors(self, filepath):
        if not PIL_AVAILABLE:
            return False
        img = PILImage.open(filepath)
        img = img.convert('RGBA')
        unique_colors = []
        seen_colors = set()
        for pixel in img.getdata():
            if pixel[3] > 0:
                color = f"#{pixel[0]:02X}{pixel[1]:02X}{pixel[2]:02X}"
                if color not in seen_colors:
                    seen_colors.add(color)
                    unique_colors.append(color)
                if len(unique_colors) >= 256:
                    break
        return self._set_colors(unique_colors)


class DrawingCanvas(tk.Canvas):
    """Main drawing canvas with zoom and transparency checkerboard."""

    def __init__(self, parent, layer_manager, tool_manager, history_manager):
        self.layer_manager = layer_manager
        self.tool_manager = tool_manager
        self.history = history_manager
        self.zoom = DEFAULT_ZOOM
        self.offset_x = 0
        self.offset_y = 0
        self.is_painting = False
        self.last_pos = None
        self.app = None

        super().__init__(parent, bg=BG_COLOR, highlightthickness=0)

        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Button-3>", self.on_right_click)
        self.bind("<B3-Motion>", self.on_right_drag)
        self.bind("<ButtonRelease-3>", self.on_right_release)
        self.bind("<MouseWheel>", self.on_mousewheel)
        self.bind("<Button-2>", self.on_middle_click)
        self.bind("<B2-Motion>", self.on_middle_drag)
        self.bind("<ButtonRelease-2>", self.on_middle_release)
        self.bind("<Enter>", lambda e: self.focus_set())

        self.bind("<space>", lambda e: self._start_pan(e))
        self.bind("<KeyRelease-space>", self._end_pan)

        self._start_pan_pos = None
        self._middle_dragging = False
        self._space_held = False
        self._line_start_pos = None
        self._stroke_snapshot = None
        self._checkerboard_photo = None
        self._composite_photo = None
        self._checkerboard_tile_cache = {}
        self._selection_drag_start = None
        self._selection_drag_offset = (0, 0)
        self._selection_drag_original_pixels = None
        self._selection_drag_base_pixels = None
        self._selection_drag_pixels = None
        self._selection_drag_bounds = None

    def _ctrl_pressed(self, event):
        return bool(event.state & 0x0004)

    def _point_in_selection(self, x, y):
        selection = self.tool_manager.selection
        if not selection:
            return False
        x1, y1, x2, y2 = selection
        return x1 <= x <= x2 and y1 <= y <= y2

    def _reset_selection_drag(self):
        self._selection_drag_start = None
        self._selection_drag_offset = (0, 0)
        self._selection_drag_original_pixels = None
        self._selection_drag_base_pixels = None
        self._selection_drag_pixels = None
        self._selection_drag_bounds = None

    def _build_selection_drag_data(self, layer, selection):
        x1, y1, x2, y2 = selection
        width = x2 - x1 + 1
        height = y2 - y1 + 1
        original_pixels = bytearray(layer.pixels)
        base_pixels = bytearray(original_pixels)
        selection_pixels = bytearray(width * height * 4)

        for row in range(height):
            src_y = y1 + row
            if not (0 <= src_y < layer.height):
                continue
            for col in range(width):
                src_x = x1 + col
                if not (0 <= src_x < layer.width):
                    continue
                src_idx = (src_y * layer.width + src_x) * 4
                dst_idx = (row * width + col) * 4
                selection_pixels[dst_idx:dst_idx +
                                 4] = original_pixels[src_idx:src_idx + 4]
                base_pixels[src_idx:src_idx + 4] = b"\x00\x00\x00\x00"

        return original_pixels, base_pixels, selection_pixels, selection

    def _begin_selection_drag(self, x, y):
        selection = self.tool_manager.selection
        if not selection:
            return False

        layer = self.layer_manager.get_active_layer()
        original_pixels, base_pixels, selection_pixels, bounds = self._build_selection_drag_data(
            layer, selection)
        self._selection_drag_original_pixels = original_pixels
        self._selection_drag_base_pixels = base_pixels
        self._selection_drag_pixels = selection_pixels
        self._selection_drag_bounds = bounds
        self._selection_drag_start = (x, y)
        self._selection_drag_offset = (0, 0)
        return True

    def _render_selection_drag(self, offset_x, offset_y):
        if self._selection_drag_base_pixels is None or self._selection_drag_pixels is None:
            return

        layer = self.layer_manager.get_active_layer()
        x1, y1, x2, y2 = self._selection_drag_bounds
        width = x2 - x1 + 1
        height = y2 - y1 + 1
        preview_pixels = bytearray(self._selection_drag_base_pixels)

        for row in range(height):
            dest_y = y1 + row + offset_y
            if not (0 <= dest_y < layer.height):
                continue
            for col in range(width):
                dest_x = x1 + col + offset_x
                if not (0 <= dest_x < layer.width):
                    continue
                src_idx = (row * width + col) * 4
                dst_idx = (dest_y * layer.width + dest_x) * 4
                preview_pixels[dst_idx:dst_idx +
                               4] = self._selection_drag_pixels[src_idx:src_idx + 4]

        layer.pixels = preview_pixels
        self.layer_manager.mark_dirty()

    def clear_selection(self):
        if self._selection_drag_original_pixels is not None:
            layer = self.layer_manager.get_active_layer()
            layer.pixels = bytearray(self._selection_drag_original_pixels)
            self.layer_manager.mark_dirty()
        self._reset_selection_drag()
        self.tool_manager.clear_selection()
        self.redraw()

    def _draw_line(self, x0, y0, x1, y1, color):
        layer = self.layer_manager.get_active_layer()
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            layer.set_pixel(x0, y0, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

        self.layer_manager.mark_dirty()

    def _start_pan(self, event):
        self._space_held = True
        self._start_pan_pos = (event.x, event.y)

    def _end_pan(self, event):
        self._space_held = False
        self._start_pan_pos = None

    def on_middle_click(self, event):
        self._middle_dragging = True
        self._start_pan_pos = (event.x, event.y)

    def on_middle_drag(self, event):
        if self._middle_dragging and self._start_pan_pos:
            dx = event.x - self._start_pan_pos[0]
            dy = event.y - self._start_pan_pos[1]
            self.offset_x += dx
            self.offset_y += dy
            self._clamp_offsets()
            self._start_pan_pos = (event.x, event.y)
            self.redraw()

    def on_middle_release(self, event):
        self._middle_dragging = False
        self._start_pan_pos = None

    def on_mousewheel(self, event):
        if event.delta > 0:
            self.zoom_in(event.x, event.y)
        elif event.delta < 0:
            self.zoom_out(event.x, event.y)

    def zoom_in(self, anchor_x=None, anchor_y=None):
        idx = ZOOM_LEVELS.index(self.zoom) if self.zoom in ZOOM_LEVELS else 1
        if idx < len(ZOOM_LEVELS) - 1:
            self.set_zoom(ZOOM_LEVELS[idx + 1], anchor_x, anchor_y)

    def zoom_out(self, anchor_x=None, anchor_y=None):
        idx = ZOOM_LEVELS.index(self.zoom) if self.zoom in ZOOM_LEVELS else 1
        if idx > 0:
            self.set_zoom(ZOOM_LEVELS[idx - 1], anchor_x, anchor_y)

    def screen_to_canvas(self, sx, sy):
        w = self.layer_manager.width
        h = self.layer_manager.height
        cx = (sx - self.offset_x) // self.zoom
        cy = (sy - self.offset_y) // self.zoom
        return cx, cy

    def center_document(self):
        canvas_width = self.winfo_width() or 800
        canvas_height = self.winfo_height() or 600
        document_width = self.layer_manager.width * self.zoom
        document_height = self.layer_manager.height * self.zoom
        self.offset_x = (canvas_width - document_width) // 2
        self.offset_y = (canvas_height - document_height) // 2
        self._clamp_offsets()

    def set_zoom(self, new_zoom, anchor_x=None, anchor_y=None):
        if new_zoom == self.zoom:
            return

        canvas_width = self.winfo_width() or 800
        canvas_height = self.winfo_height() or 600

        if anchor_x is None:
            anchor_x = canvas_width // 2
        if anchor_y is None:
            anchor_y = canvas_height // 2

        pixel_x = (anchor_x - self.offset_x) / self.zoom
        pixel_y = (anchor_y - self.offset_y) / self.zoom

        self.zoom = new_zoom
        self.offset_x = int(round(anchor_x - pixel_x * self.zoom))
        self.offset_y = int(round(anchor_y - pixel_y * self.zoom))
        self._clamp_offsets()
        self.redraw()

    def _clamp_offsets(self):
        canvas_width = self.winfo_width() or 800
        canvas_height = self.winfo_height() or 600
        document_width = self.layer_manager.width * self.zoom
        document_height = self.layer_manager.height * self.zoom

        if document_width <= canvas_width:
            self.offset_x = (canvas_width - document_width) // 2
        else:
            min_offset_x = canvas_width - document_width
            self.offset_x = min(0, max(min_offset_x, self.offset_x))

        if document_height <= canvas_height:
            self.offset_y = (canvas_height - document_height) // 2
        else:
            min_offset_y = canvas_height - document_height
            self.offset_y = min(0, max(min_offset_y, self.offset_y))

    def pan_by(self, dx, dy):
        self.offset_x += dx
        self.offset_y += dy
        self._clamp_offsets()
        self.redraw()

    def handle_resize(self, previous_width, previous_height, new_width, new_height):
        self.offset_x += int(round((new_width - previous_width) / 2))
        self.offset_y += int(round((new_height - previous_height) / 2))
        self._clamp_offsets()
        self.redraw()

    def on_click(self, event):
        if self._space_held or self._middle_dragging:
            return

        cx, cy = self.screen_to_canvas(event.x, event.y)
        tool = self.tool_manager.current_tool

        if tool == "selection":
            if self._ctrl_pressed(event) and self._point_in_selection(cx, cy):
                self._begin_selection_drag(cx, cy)
                return
            self.tool_manager.selection_start = (cx, cy)
            self.tool_manager.selection_end = (cx, cy)
            self._reset_selection_drag()
        else:
            self.is_painting = True
            self._line_start_pos = (cx, cy)
            self.last_pos = (cx, cy)
            if tool in ("pencil", "eraser"):
                layer = self.layer_manager.get_active_layer()
                self._stroke_snapshot = bytearray(layer.pixels)
            else:
                self._stroke_snapshot = None
            self.apply_tool(cx, cy, tool, is_click=True)

    def on_drag(self, event):
        if self._space_held or self._middle_dragging:
            return

        cx, cy = self.screen_to_canvas(event.x, event.y)
        tool = self.tool_manager.current_tool
        shift_held = bool(event.state & 0x0001)

        if tool == "selection":
            if self._selection_drag_start is not None:
                dx = cx - self._selection_drag_start[0]
                dy = cy - self._selection_drag_start[1]
                if (dx, dy) != self._selection_drag_offset:
                    self._selection_drag_offset = (dx, dy)
                    self._render_selection_drag(dx, dy)
                    self.redraw()
                return
            self.tool_manager.selection_end = (cx, cy)
            self.redraw()
        elif self.is_painting:
            if tool == "pencil" and shift_held and self._line_start_pos and self._stroke_snapshot is not None:
                layer = self.layer_manager.get_active_layer()
                layer.pixels = bytearray(self._stroke_snapshot)
                self._draw_line(
                    self._line_start_pos[0], self._line_start_pos[1], cx, cy, self.app.foreground_rgba)
                self.last_pos = (cx, cy)
                self.redraw()
            elif tool in ("pencil", "eraser") and self.last_pos and self.last_pos != (cx, cy):
                color = self.app.foreground_rgba if tool == "pencil" else (
                    0, 0, 0, 0)
                self._draw_line(self.last_pos[0],
                                self.last_pos[1], cx, cy, color)
                self.last_pos = (cx, cy)
                self.redraw()
            elif self.last_pos != (cx, cy):
                self.apply_tool(cx, cy, tool)
                self.last_pos = (cx, cy)

    def on_release(self, event):
        self.is_painting = False
        self.last_pos = None
        self._line_start_pos = None
        self._stroke_snapshot = None

        if self.tool_manager.current_tool == "selection":
            if self._selection_drag_start is not None and self._selection_drag_bounds is not None:
                dx, dy = self._selection_drag_offset
                layer = self.layer_manager.get_active_layer()
                if dx == 0 and dy == 0:
                    layer.pixels = bytearray(
                        self._selection_drag_original_pixels)
                    self.layer_manager.mark_dirty()
                else:
                    self.history.save_state(
                        self.layer_manager.active_layer_index,
                        self._selection_drag_original_pixels,
                    )
                    x1, y1, x2, y2 = self._selection_drag_bounds
                    self.tool_manager.selection_start = (x1 + dx, y1 + dy)
                    self.tool_manager.selection_end = (x2 + dx, y2 + dy)
                self._reset_selection_drag()
            self.redraw()

    def on_right_click(self, event):
        cx, cy = self.screen_to_canvas(event.x, event.y)
        tool = self.tool_manager.current_tool
        if tool == "eyedropper":
            layer = self.layer_manager.get_active_layer()
            color = layer.get_pixel(cx, cy)
            if color[3] > 0:
                self.app.set_background_color(
                    f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}")

    def on_right_drag(self, event):
        pass

    def on_right_release(self, event):
        pass

    def apply_tool(self, cx, cy, tool, is_click=False):
        layer = self.layer_manager.get_active_layer()
        app = self.app

        if tool == "pencil":
            if is_click:
                self.history.save_state(
                    self.layer_manager.active_layer_index, layer.pixels)
            layer.set_pixel(cx, cy, app.foreground_rgba)
            self.layer_manager.mark_dirty()
            self.redraw()

        elif tool == "eraser":
            if is_click:
                self.history.save_state(
                    self.layer_manager.active_layer_index, layer.pixels)
            layer.set_pixel(cx, cy, (0, 0, 0, 0))
            self.layer_manager.mark_dirty()
            self.redraw()

        elif tool == "bucket":
            if is_click:
                self._bucket_fill(layer, cx, cy, app.foreground_rgba)
                self.redraw()

        elif tool == "eyedropper":
            color = layer.get_pixel(cx, cy)
            if color[3] > 0:
                app.set_foreground_color(
                    f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}")

    def _bucket_fill(self, layer, start_x, start_y, fill_color):
        w, h = layer.width, layer.height
        if not (0 <= start_x < w and 0 <= start_y < h):
            return

        target_color = layer.get_pixel(start_x, start_y)
        if target_color == fill_color:
            return

        self.history.save_state(
            self.layer_manager.active_layer_index, layer.pixels)

        stack = [(start_x, start_y)]
        visited = set()

        while stack:
            x, y = stack.pop()
            if (x, y) in visited:
                continue
            if not (0 <= x < w and 0 <= y < h):
                continue
            current = layer.get_pixel(x, y)
            if current != target_color:
                continue
            visited.add((x, y))
            layer.set_pixel(x, y, fill_color)
            stack.append((x + 1, y))
            stack.append((x - 1, y))
            stack.append((x, y + 1))
            stack.append((x, y - 1))

        self.layer_manager.mark_dirty()

    def redraw(self):
        """Redraw the canvas with checkerboard and all layers."""
        self.delete("all")

        w = self.layer_manager.width
        h = self.layer_manager.height
        zoom = self.zoom

        canvas_width = self.winfo_width() or 800
        canvas_height = self.winfo_height() or 600

        if PIL_AVAILABLE:
            self._redraw_with_images(w, h, zoom, canvas_width, canvas_height)
        else:
            self._redraw_with_rectangles(w, h, zoom)

        if self.tool_manager.current_tool == "selection":
            start = self.tool_manager.selection_start
            end = self.tool_manager.selection_end
            if start and end:
                x1 = self.offset_x + min(start[0], end[0]) * zoom
                y1 = self.offset_y + min(start[1], end[1]) * zoom
                x2 = self.offset_x + (max(start[0], end[0]) + 1) * zoom
                y2 = self.offset_y + (max(start[1], end[1]) + 1) * zoom
                self.create_rectangle(
                    x1, y1, x2, y2, outline=ACCENT_COLOR, dash=(4, 4), width=2)

    def _redraw_with_images(self, w, h, zoom, canvas_width, canvas_height):
        visible = self._get_visible_pixel_bounds(
            w, h, zoom, canvas_width, canvas_height)
        self._checkerboard_photo = None
        self._composite_photo = None

        if not visible:
            return

        start_x, start_y, end_x, end_y = visible
        crop_width = end_x - start_x
        crop_height = end_y - start_y
        image_x = self.offset_x + start_x * zoom
        image_y = self.offset_y + start_y * zoom

        checkerboard = self._build_checkerboard_image(
            start_x, start_y, crop_width, crop_height, zoom)
        checkerboard = checkerboard.resize(
            (crop_width * zoom, crop_height * zoom), IMAGE_NEAREST)
        self._checkerboard_photo = PILImageTk.PhotoImage(checkerboard)
        self.create_image(image_x, image_y,
                          image=self._checkerboard_photo, anchor=tk.NW)

        source = self.layer_manager.get_composite_image()
        source = source.crop((start_x, start_y, end_x, end_y))
        scaled = source.resize(
            (crop_width * zoom, crop_height * zoom), IMAGE_NEAREST)
        self._composite_photo = PILImageTk.PhotoImage(scaled)
        self.create_image(image_x, image_y,
                          image=self._composite_photo, anchor=tk.NW)

        if self.app and self.app.show_grid:
            self._draw_grid_lines(start_x, start_y, end_x, end_y, zoom)

    def _redraw_with_rectangles(self, w, h, zoom):
        check_size = max(zoom // 4, 4)
        for y in range(h):
            for x in range(w):
                px = self.offset_x + x * zoom
                py = self.offset_y + y * zoom

                if (x // check_size + y // check_size) % 2 == 0:
                    self.create_rectangle(
                        px, py, px + zoom, py + zoom, fill="#2a2a2a", outline="")
                else:
                    self.create_rectangle(
                        px, py, px + zoom, py + zoom, fill="#333333", outline="")

        composite = self.layer_manager.render_composite()

        for y in range(h):
            for x in range(w):
                idx = (y * w + x) * 4
                r, g, b, a = composite[idx:idx + 4]
                if a > 0:
                    px = self.offset_x + x * zoom
                    py = self.offset_y + y * zoom
                    color = f"#{r:02X}{g:02X}{b:02X}"
                    self.create_rectangle(
                        px, py, px + zoom, py + zoom, fill=color, outline="")

        if self.app and self.app.show_grid:
            self._draw_grid_lines(0, 0, w, h, zoom)

    def _get_visible_pixel_bounds(self, width, height, zoom, canvas_width, canvas_height):
        start_x = max(0, math.floor(-self.offset_x / zoom))
        start_y = max(0, math.floor(-self.offset_y / zoom))
        end_x = min(width, math.ceil((canvas_width - self.offset_x) / zoom))
        end_y = min(height, math.ceil((canvas_height - self.offset_y) / zoom))

        if start_x >= end_x or start_y >= end_y:
            return None

        return start_x, start_y, end_x, end_y

    def _build_checkerboard_image(self, start_x, start_y, width, height, zoom):
        check_size = max(zoom // 4, 4)
        tile = self._get_checkerboard_tile(check_size)
        tile_size = tile.width
        image = PILImage.new("RGB", (width, height))

        x_offset = -((start_x % tile_size + tile_size) % tile_size)
        y_offset = -((start_y % tile_size + tile_size) % tile_size)

        for y in range(y_offset, height, tile_size):
            for x in range(x_offset, width, tile_size):
                image.paste(tile, (x, y))

        return image

    def _get_checkerboard_tile(self, check_size):
        tile = self._checkerboard_tile_cache.get(check_size)
        if tile is not None:
            return tile

        tile_size = check_size * 2
        tile = PILImage.new("RGB", (tile_size, tile_size), (42, 42, 42))
        light_tile = PILImage.new(
            "RGB", (check_size, check_size), (51, 51, 51))
        tile.paste(light_tile, (check_size, 0))
        tile.paste(light_tile, (0, check_size))
        self._checkerboard_tile_cache[check_size] = tile
        return tile

    def _draw_grid_lines(self, start_x, start_y, end_x, end_y, zoom):
        for x in range(start_x, end_x + 1):
            px = self.offset_x + x * zoom
            self.create_line(
                px, self.offset_y + start_y * zoom, px, self.offset_y + end_y * zoom, fill="#444444", width=1)
        for y in range(start_y, end_y + 1):
            py = self.offset_y + y * zoom
            self.create_line(
                self.offset_x + start_x * zoom, py, self.offset_x + end_x * zoom, py, fill="#444444", width=1)


class App:
    """Main application window."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("SpriteLite")
        self.root.geometry("1024x768")
        self.root.configure(bg=BG_COLOR)
        self._apply_window_icon()

        self.width = 16
        self.height = 16

        self.history = HistoryManager(20)
        self.layer_manager = LayerManager(
            self.width, self.height, self.history)
        self.tool_manager = ToolManager()
        self.palette_manager = PaletteManager()

        self.foreground = "#000000"
        self.background = "#FFFFFF"
        self.show_grid = True
        self.current_file = None
        self._pending_view_reset = True
        self._pending_layer_select_job = None
        self._last_canvas_size = None

        self._load_icons()
        self._setup_ui()
        self._setup_menu()
        self._setup_keybindings()
        self.root.after_idle(self._request_view_reset)

    def _apply_window_icon(self):
        icon_path = resource_path("icon.ico")
        if not os.path.exists(icon_path):
            return

        try:
            self.root.iconbitmap(icon_path)
        except Exception:
            pass

    def _load_icons(self):
        self.icons = {}
        icon_files = {
            "pencil": "icons/pencil.png",
            "eraser": "icons/eraser.png",
            "bucket": "icons/fill-bucket.png",
            "eyedropper": "icons/eyedropper.png",
            "selection": "icons/bounding-box.png",
            "eye_on": "icons/eye-on.png",
            "eye_off": "icons/eye-off.png",
            "trash": "icons/trash.png"
        }
        for key, path in icon_files.items():
            try:
                if PILImage:
                    img = PILImage.open(resource_path(path)).convert("RGBA")
                    img = img.resize((20, 20), PILImage.LANCZOS)
                    self.icons[key] = tk.PhotoImage(data=self._pil_to_tk(img))
            except Exception:
                pass

    def _pil_to_tk(self, pil_image):
        import io
        buffer = io.BytesIO()
        pil_image.save(buffer, format="PNG")
        return buffer.getvalue()

    def _setup_ui(self):
        """Setup the main UI layout."""
        main_container = tk.Frame(self.root, bg=BG_COLOR)
        main_container.pack(fill=tk.BOTH, expand=True)

        toolbar = tk.Frame(main_container, bg=PANEL_COLOR,
                           width=60, padx=2, pady=2)
        toolbar.pack(side=tk.LEFT, fill=tk.Y)
        toolbar.pack_propagate(False)

        self._setup_toolbar(toolbar)

        canvas_container = tk.Frame(main_container, bg=BG_COLOR)
        canvas_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas_frame = canvas_container
        self.canvas = DrawingCanvas(
            canvas_container, self.layer_manager, self.tool_manager, self.history)
        self.canvas.app = self
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self._set_cursor(self.tool_manager.current_tool)

        right_panel = tk.Frame(
            main_container, bg=PANEL_COLOR, width=200, padx=2, pady=2)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y)
        right_panel.pack_propagate(False)

        self._setup_layer_panel(right_panel)
        self._setup_palette_panel(right_panel)
        self._setup_color_picker(right_panel)

    def _setup_toolbar(self, parent):
        """Setup the tool toolbar."""
        tools = [
            ("pencil", "pencil", "Pencil (P)"),
            ("eraser", "eraser", "Eraser (E)"),
            ("bucket", "bucket", "Bucket Fill (B)"),
            ("eyedropper", "eyedropper", "Eyedropper (I)"),
            ("selection", "selection", "Selection (S)")
        ]

        self.tool_buttons = {}
        self.tooltip_window = None

        def show_tooltip(widget, text, event):
            if self.tooltip_window:
                self.tooltip_window.destroy()
            self.tooltip_window = tk.Toplevel(widget)
            self.tooltip_window.wm_overrideredirect(True)
            x = widget.winfo_rootx() + widget.winfo_width() // 2
            y = widget.winfo_rooty() - 30
            self.tooltip_window.wm_geometry(f"+{x}+{y}")
            label = tk.Label(self.tooltip_window, text=text, bg="#444444",
                             fg="white", padx=6, pady=2, font=("Arial", 8))
            label.pack()

        def hide_tooltip(event):
            if self.tooltip_window:
                self.tooltip_window.destroy()
                self.tooltip_window = None

        for icon_key, tool_id, tooltip in tools:
            icon = self.icons.get(icon_key)
            btn = tk.Button(
                parent, image=icon, bg=PANEL_COLOR,
                activebackground=ACCENT_COLOR,
                relief=tk.FLAT, width=28, height=28,
                command=lambda t=tool_id: self._select_tool(t)
            )
            if icon:
                btn.config(image=icon)
            else:
                btn.config(text=icon_key[0].upper(),
                           font=("Arial", 11, "bold"))
            btn.pack(pady=2, padx=2)
            btn.bind("<Enter>", lambda e, w=btn,
                     t=tooltip: show_tooltip(w, t, e))
            btn.bind("<Leave>", hide_tooltip)
            self.tool_buttons[tool_id] = btn

        spacer = tk.Frame(parent, bg=PANEL_COLOR)
        spacer.pack(fill=tk.BOTH, expand=True)

        self.canvas_size_var = tk.StringVar()
        self.canvas_size_label = tk.Label(
            parent,
            textvariable=self.canvas_size_var,
            bg=PANEL_COLOR,
            fg=TEXT_COLOR,
            font=("Arial", 8),
            anchor="center",
            justify="center"
        )
        self.canvas_size_label.pack(
            side=tk.BOTTOM, fill=tk.X, padx=2, pady=(6, 2))
        self._update_canvas_size_display()

        self._select_tool("pencil")

    CURSORS = {
        "pencil": "crosshair",
        "eraser": "crosshair",
        "bucket": "crosshair",
        "eyedropper": "crosshair",
        "eyedropper": "crosshair",
        "selection": "crosshair"
    }

    def _set_cursor(self, tool):
        cursor = self.CURSORS.get(tool, "arrow")
        if hasattr(self, 'canvas'):
            self.canvas.configure(cursor=cursor)

    def _setup_layer_panel(self, parent):
        """Setup the layer panel."""
        layer_frame = tk.LabelFrame(
            parent, text="Layers", bg=PANEL_COLOR, fg=TEXT_COLOR, padx=5, pady=5)
        layer_frame.pack(fill=tk.X, pady=(0, 10))

        self.layer_canvas = tk.Canvas(
            layer_frame, bg="#333333", height=160, highlightthickness=0)
        self.layer_scrollbar = tk.Scrollbar(
            layer_frame, orient=tk.VERTICAL, command=self.layer_canvas.yview)
        self.layer_canvas.configure(yscrollcommand=self.layer_scrollbar.set)

        self.layer_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.layer_canvas.pack(fill=tk.X, expand=False)

        self.layer_inner = tk.Frame(self.layer_canvas, bg="#333333")
        self.layer_canvas.create_window(
            (0, 0), window=self.layer_inner, anchor=tk.NW)

        self.layer_inner.bind("<Configure>", lambda e: self.layer_canvas.configure(
            scrollregion=self.layer_canvas.bbox("all")))

        btn_frame = tk.Frame(layer_frame, bg=PANEL_COLOR)
        btn_frame.pack(fill=tk.X, pady=2)

        def make_tooltip(widget, text):
            def show(event):
                if hasattr(self, 'tooltip_window') and self.tooltip_window:
                    self.tooltip_window.destroy()
                self.tooltip_window = tk.Toplevel(widget)
                self.tooltip_window.wm_overrideredirect(True)
                x = widget.winfo_rootx() + widget.winfo_width() // 2
                y = widget.winfo_rooty() - 25
                self.tooltip_window.wm_geometry(f"+{x}+{y}")
                label = tk.Label(self.tooltip_window, text=text, bg="#444444",
                                 fg="white", padx=6, pady=2, font=("Arial", 8))
                label.pack()

            def hide(event):
                if hasattr(self, 'tooltip_window') and self.tooltip_window:
                    self.tooltip_window.destroy()
                    self.tooltip_window = None
            widget.bind("<Enter>", show)
            widget.bind("<Leave>", hide)

        add_btn = tk.Button(btn_frame, text="+", width=3,
                            bg=PANEL_COLOR, fg=TEXT_COLOR, command=self._add_layer)
        add_btn.pack(side=tk.LEFT, padx=1)
        make_tooltip(add_btn, "Add Layer")

        dup_btn = tk.Button(btn_frame, text="D", width=3, bg=PANEL_COLOR,
                            fg=TEXT_COLOR, command=self._duplicate_layer)
        dup_btn.pack(side=tk.LEFT, padx=1)
        make_tooltip(dup_btn, "Duplicate Layer")

        up_btn = tk.Button(btn_frame, text="^", width=3, bg=PANEL_COLOR,
                           fg=TEXT_COLOR, command=self._move_layer_down)
        up_btn.pack(side=tk.LEFT, padx=1)
        make_tooltip(up_btn, "Move Layer Up")

        down_btn = tk.Button(btn_frame, text="v", width=3,
                             bg=PANEL_COLOR, fg=TEXT_COLOR, command=self._move_layer_up)
        down_btn.pack(side=tk.LEFT, padx=1)
        make_tooltip(down_btn, "Move Layer Down")

        self._update_layer_list()

    def _setup_palette_panel(self, parent):
        """Setup the color palette panel."""
        palette_frame = tk.LabelFrame(
            parent, text="Palette", bg=PANEL_COLOR, fg=TEXT_COLOR, padx=5, pady=5)
        palette_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        palette_content = tk.Frame(palette_frame, bg=PANEL_COLOR)
        palette_content.pack(fill=tk.BOTH, expand=True)

        self.palette_canvas = tk.Canvas(
            palette_content, bg=PANEL_COLOR, highlightthickness=0)
        self.palette_scrollbar = tk.Scrollbar(
            palette_content, orient=tk.VERTICAL, command=self.palette_canvas.yview)
        self.palette_canvas.configure(
            yscrollcommand=self.palette_scrollbar.set)

        self.palette_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.palette_canvas.pack(
            side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 0))

        self.palette_inner = tk.Frame(self.palette_canvas, bg=PANEL_COLOR)
        self.palette_canvas.create_window(
            (0, 0), window=self.palette_inner, anchor=tk.NW)

        self.palette_inner.bind("<Configure>", lambda e: self.palette_canvas.configure(
            scrollregion=self.palette_canvas.bbox("all")))

        tk.Button(palette_frame, text="Load Palette", bg=PANEL_COLOR,
                  fg=TEXT_COLOR, command=self._load_palette).pack(fill=tk.X, pady=(6, 0))

        self._update_palette()

    def _setup_color_picker(self, parent):
        """Setup the color picker display."""
        color_frame = tk.LabelFrame(
            parent, text="Color", bg=PANEL_COLOR, fg=TEXT_COLOR, padx=5, pady=5)
        color_frame.pack(fill=tk.X)

        self.fg_color_canvas = tk.Canvas(
            color_frame, width=50, height=50, bg=BG_COLOR, highlightthickness=1, highlightbackground=BORDER_COLOR)
        self.fg_color_canvas.pack(pady=2)
        self.fg_color_canvas.bind(
            "<Button-1>", lambda e: self._choose_color("foreground"))
        self.fg_color_canvas.bind(
            "<Button-3>", lambda e: self._choose_color("background"))

        self._update_color_display()

    def _update_color_display(self):
        self.fg_color_canvas.delete("all")
        bg = self.background
        fg = self.foreground
        self.fg_color_canvas.create_rectangle(
            5, 5, 45, 45, fill=bg, outline="")
        self.fg_color_canvas.create_rectangle(
            10, 10, 40, 40, fill=fg, outline="")

    def _choose_color(self, target):
        if target == "foreground":
            color = colorchooser.askcolor(
                self.foreground, title="Choose Foreground Color")
            if color[1]:
                self.set_foreground_color(color[1])
        else:
            color = colorchooser.askcolor(
                self.background, title="Choose Background Color")
            if color[1]:
                self.set_background_color(color[1])

    def set_foreground_color(self, color):
        self.foreground = color
        self._update_color_display()
        if hasattr(self, "palette_inner"):
            self._update_palette()

    def set_background_color(self, color):
        self.background = color
        self._update_color_display()

    @property
    def foreground_rgba(self):
        r = int(self.foreground[1:3], 16)
        g = int(self.foreground[3:5], 16)
        b = int(self.foreground[5:7], 16)
        return (r, g, b, 255)

    def _format_layer_name(self, name):
        if len(name) <= 18:
            return name
        return f"{name[:15]}..."

    def _update_canvas_size_display(self):
        if hasattr(self, "canvas_size_var"):
            self.canvas_size_var.set(f"{self.width}x{self.height}")

    def _update_layer_list(self):
        for widget in self.layer_inner.winfo_children():
            widget.destroy()

        for i, layer in enumerate(self.layer_manager.layers):
            is_active = i == self.layer_manager.active_layer_index
            bg_color = ACCENT_COLOR if is_active else "#333333"

            row_frame = tk.Frame(self.layer_inner, bg=bg_color, pady=1)
            row_frame.pack(fill=tk.X)

            eye_icon = self.icons.get("eye_on" if layer.visible else "eye_off")
            eye_btn = tk.Button(
                row_frame, image=eye_icon, width=18, height=18, bg=bg_color,
                relief=tk.FLAT,
                command=lambda idx=i: self._toggle_layer_visibility_by_index(
                    idx)
            )
            if eye_icon:
                eye_btn.config(image=eye_icon)
            else:
                eye_btn.config(text="O" if layer.visible else "x")
            eye_btn.pack(side=tk.LEFT, padx=(2, 5))

            trash_icon = self.icons.get("trash")
            delete_btn = tk.Button(
                row_frame, image=trash_icon, width=18, height=18, bg=bg_color,
                relief=tk.FLAT,
                command=lambda idx=i: self._delete_layer_by_index(idx)
            )
            if trash_icon:
                delete_btn.config(image=trash_icon)
            else:
                delete_btn.config(text="-", fg=TEXT_COLOR)
            delete_btn.pack(side=tk.RIGHT, padx=(5, 2))

            name_label = tk.Label(
                row_frame, text=self._format_layer_name(layer.name), bg=bg_color, fg=TEXT_COLOR,
                font=("Arial", 9), anchor="w"
            )
            name_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            name_label.bind("<Button-1>", lambda e,
                            idx=i: self._schedule_layer_select(idx))
            name_label.bind("<Double-Button-1>", lambda e,
                            idx=i: self._rename_layer_from_click(idx))

            row_frame.bind("<Button-1>", lambda e,
                           idx=i: self._schedule_layer_select(idx))
            row_frame.bind("<Double-Button-1>", lambda e,
                           idx=i: self._rename_layer_from_click(idx))

    def _select_layer(self, index):
        self.layer_manager.active_layer_index = index
        self._update_layer_list()

    def _schedule_layer_select(self, index):
        self._cancel_pending_layer_select()
        self._pending_layer_select_job = self.root.after(
            180, lambda idx=index: self._run_scheduled_layer_select(idx))

    def _run_scheduled_layer_select(self, index):
        self._pending_layer_select_job = None
        self._select_layer(index)

    def _cancel_pending_layer_select(self):
        if self._pending_layer_select_job is not None:
            self.root.after_cancel(self._pending_layer_select_job)
            self._pending_layer_select_job = None

    def _rename_layer_from_click(self, index):
        self._cancel_pending_layer_select()
        self._select_layer(index)
        self._rename_layer(index)

    def _toggle_layer_visibility_by_index(self, index):
        self.layer_manager.toggle_visibility(index)
        self._update_layer_list()
        self.canvas.redraw()

    def _on_layer_select(self, event):
        pass

    def _add_layer(self):
        self.layer_manager.add_layer()
        self._update_layer_list()
        self.canvas.redraw()

    def _delete_layer(self):
        if self.layer_manager.delete_layer():
            self._update_layer_list()
            self.canvas.redraw()

    def _delete_layer_by_index(self, index):
        if self.layer_manager.delete_layer(index):
            self._update_layer_list()
            self.canvas.redraw()

    def _duplicate_layer(self):
        self.layer_manager.duplicate_layer()
        self._update_layer_list()
        self.canvas.redraw()

    def _move_layer_up(self):
        if self.layer_manager.move_layer_up():
            self._update_layer_list()
            self.canvas.redraw()

    def _move_layer_down(self):
        if self.layer_manager.move_layer_down():
            self._update_layer_list()
            self.canvas.redraw()

    def _rename_layer(self, index):
        layer = self.layer_manager.layers[index]
        new_name = simpledialog.askstring(
            "Rename Layer",
            "Layer name (max 18 chars):",
            initialvalue=layer.name,
            parent=self.root
        )
        if new_name is None:
            return

        new_name = new_name.strip()[:18]
        if not new_name:
            return

        layer.name = new_name
        self._update_layer_list()

    def _rename_active_layer(self):
        focused_widget = self.root.focus_get()
        if isinstance(focused_widget, (tk.Entry, tk.Text, tk.Spinbox)):
            return

        self._rename_layer(self.layer_manager.active_layer_index)

    def _toggle_layer_visibility(self, event=None):
        self.layer_manager.toggle_visibility(
            self.layer_manager.active_layer_index)
        self._update_layer_list()
        self.canvas.redraw()

    def _update_palette(self):
        for widget in self.palette_inner.winfo_children():
            widget.destroy()

        colors = self.palette_manager.colors
        cols = 8
        for i, color in enumerate(colors):
            row = i // cols
            col = i % cols
            is_selected = color.upper() == self.foreground.upper()
            swatch = tk.Canvas(self.palette_inner, width=20, height=20, bg=color,
                               highlightthickness=2 if is_selected else 1,
                               highlightbackground=ACCENT_COLOR if is_selected else BORDER_COLOR,
                               highlightcolor=ACCENT_COLOR if is_selected else BORDER_COLOR)
            swatch.grid(row=row, column=col, padx=1, pady=1)
            swatch.bind("<Button-1>", lambda e, c=color: self._set_color(e, c))
            swatch.bind("<Button-3>", lambda e,
                        c=color: self._set_bg_color(e, c))

    def _set_color(self, event, color):
        self.set_foreground_color(color)

    def _set_bg_color(self, event, color):
        self.set_background_color(color)

    def _load_palette(self):
        filepath = filedialog.askopenfilename(
            title="Load Palette",
            filetypes=[("Palette Files", "*.pal *.gpl *.ase *.png"),
                       ("All Files", "*.*")]
        )
        if filepath:
            try:
                if not self.palette_manager.load_palette_file(filepath):
                    messagebox.showwarning(
                        "Load Palette", "No colors were found in the selected palette file.")
                    return
                self._update_palette()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load palette: {e}")

    def _select_tool(self, tool):
        self.tool_manager.set_tool(tool)
        for tid, btn in self.tool_buttons.items():
            if tid == tool:
                btn.configure(bg=ACCENT_COLOR)
            else:
                btn.configure(bg=PANEL_COLOR)
        self._set_cursor(tool)

    def _setup_menu(self):
        """Setup the menu bar."""
        menubar = tk.Menu(self.root, bg=PANEL_COLOR, fg=TEXT_COLOR)
        self.root.configure(menu=menubar)

        file_menu = tk.Menu(menubar, bg=PANEL_COLOR, fg=TEXT_COLOR, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(
            label="New", command=self._new_file, accelerator="Ctrl+N")
        file_menu.add_command(
            label="Open", command=self._open_file, accelerator="Ctrl+O")
        file_menu.add_command(
            label="Save", command=self._save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As", command=self._save_file_as)
        file_menu.add_command(label="Import PNG", command=self._import_png)
        file_menu.add_command(label="Export PNG", command=self._export_flat)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        view_menu = tk.Menu(menubar, bg=PANEL_COLOR, fg=TEXT_COLOR, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        self.grid_var = tk.BooleanVar(value=True)
        view_menu.add_checkbutton(
            label="Show Grid", variable=self.grid_var, command=self._toggle_grid, accelerator="Ctrl+H")
        view_menu.add_separator()
        view_menu.add_command(
            label="Zoom In", command=self.canvas.zoom_in, accelerator="Ctrl++")
        view_menu.add_command(
            label="Zoom Out", command=self.canvas.zoom_out, accelerator="Ctrl+-")

    def _setup_keybindings(self):
        """Setup keyboard shortcuts."""
        self.root.bind("<p>", lambda e: self._select_tool("pencil"))
        self.root.bind("<e>", lambda e: self._select_tool("eraser"))
        self.root.bind("<i>", lambda e: self._select_tool("eyedropper"))
        self.root.bind("<b>", lambda e: self._select_tool("bucket"))
        self.root.bind("<B>", lambda e: self._select_tool("bucket"))
        self.root.bind("<s>", lambda e: self._select_tool("selection"))
        self.root.bind("<Escape>", self._clear_selection)
        self.root.bind("<Control-d>", self._clear_selection)
        self.root.bind("<Control-D>", self._clear_selection)
        self.root.bind("<Control-plus>", lambda e: self.canvas.zoom_in())
        self.root.bind("<Control-equal>", lambda e: self.canvas.zoom_in())
        self.root.bind("<Control-KP_Add>", lambda e: self.canvas.zoom_in())
        self.root.bind("<Control-minus>", lambda e: self.canvas.zoom_out())
        self.root.bind("<Control-KP_Subtract>",
                       lambda e: self.canvas.zoom_out())

        self.root.bind("<Control-z>", lambda e: self._undo())
        self.root.bind("<Control-y>", lambda e: self._redo())
        self.root.bind("<Control-Y>", lambda e: self._redo())
        self.root.bind("<Control-Shift-Z>", lambda e: self._redo())
        self.root.bind("<Control-s>", lambda e: self._save_file())
        self.root.bind("<Control-o>", lambda e: self._open_file())
        self.root.bind("<Control-n>", lambda e: self._new_file())
        self.root.bind("<Control-a>", lambda e: self._select_all())
        self.root.bind("<Control-A>", lambda e: self._select_all())
        self.root.bind("<Control-h>", lambda e: self._toggle_grid())
        self.root.bind("<F2>", lambda e: self._rename_active_layer())
        self.root.bind("<Delete>", lambda e: self._delete_selection())
        self.root.bind("<BackSpace>", lambda e: self._delete_selection())
        self.root.bind("<Left>", lambda e: self._pan_canvas_by_keys(1, 0))
        self.root.bind("<Right>", lambda e: self._pan_canvas_by_keys(-1, 0))
        self.root.bind("<Up>", lambda e: self._pan_canvas_by_keys(0, 1))
        self.root.bind("<Down>", lambda e: self._pan_canvas_by_keys(0, -1))

    def _select_all(self):
        self.tool_manager.set_tool("selection")
        self.tool_manager.selection_start = (0, 0)
        self.tool_manager.selection_end = (self.width - 1, self.height - 1)
        for tid, btn in self.tool_buttons.items():
            if tid == "selection":
                btn.configure(bg=ACCENT_COLOR)
            else:
                btn.configure(bg=PANEL_COLOR)
        self._set_cursor("selection")
        self.canvas.redraw()

    def _toggle_grid(self):
        self.show_grid = not self.show_grid
        self.grid_var.set(self.show_grid)
        self.canvas.redraw()

    def _clear_selection(self, event=None):
        self.canvas.clear_selection()
        return "break"

    def _delete_selection(self):
        selection = self.canvas.tool_manager.selection
        if selection:
            x1, y1, x2, y2 = selection
            layer = self.layer_manager.get_active_layer()
            self.history.save_state(
                self.layer_manager.active_layer_index, layer.pixels)
            for y in range(max(0, y1), min(y2 + 1, layer.height)):
                for x in range(max(0, x1), min(x2 + 1, layer.width)):
                    layer.set_pixel(x, y, (0, 0, 0, 0))
            self.layer_manager.mark_dirty()
            self.canvas.tool_manager.clear_selection()
            self.canvas.redraw()

    def _pan_canvas_by_keys(self, direction_x, direction_y):
        focused_widget = self.root.focus_get()
        if isinstance(focused_widget, (tk.Entry, tk.Text, tk.Spinbox)):
            return

        pan_step = max(16, self.canvas.zoom * 2)
        self.canvas.pan_by(direction_x * pan_step, direction_y * pan_step)

    def _center_dialog(self, dialog):
        self.root.update_idletasks()
        dialog.update_idletasks()

        dialog_width = dialog.winfo_width()
        dialog_height = dialog.winfo_height()
        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty()
        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()

        x = root_x + max((root_width - dialog_width) // 2, 0)
        y = root_y + max((root_height - dialog_height) // 2, 0)
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

    def _new_file(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("New File")
        dialog.geometry("300x200")
        dialog.configure(bg=BG_COLOR)
        dialog.transient(self.root)
        dialog.bind("<Return>", lambda e: create_canvas())

        tk.Label(dialog, text="Width:", bg=BG_COLOR,
                 fg=TEXT_COLOR).pack(pady=5)
        width_var = tk.StringVar(value="16")
        width_entry = tk.Entry(dialog, textvariable=width_var, width=10)
        width_entry.pack()

        tk.Label(dialog, text="Height:", bg=BG_COLOR,
                 fg=TEXT_COLOR).pack(pady=5)
        height_var = tk.StringVar(value="16")
        tk.Entry(dialog, textvariable=height_var, width=10).pack()

        def create_canvas():
            try:
                w = min(128, max(1, int(width_var.get())))
                h = min(128, max(1, int(height_var.get())))
                self._load_empty_canvas(w, h)
                dialog.destroy()
            except ValueError:
                pass

        create_button = tk.Button(dialog, text="Create", command=create_canvas,
                                  bg=PANEL_COLOR, fg=TEXT_COLOR, default=tk.ACTIVE)
        create_button.pack(pady=20)
        self._center_dialog(dialog)
        width_entry.focus_set()

    def _open_file(self):
        filepath = filedialog.askopenfilename(
            title="Open Project",
            filetypes=[("SpriteLite Projects", "*.sprlite"),
                       ("All Files", "*.*")]
        )
        if not filepath:
            return

        try:
            self._load_project_file(filepath)
            self.current_file = filepath
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open project: {e}")

    def _save_file(self):
        if not self.current_file:
            self._save_file_as()
        else:
            self._save_to_file(self.current_file)

    def _save_file_as(self):
        filepath = filedialog.asksaveasfilename(
            title="Save Project",
            defaultextension=".sprlite",
            filetypes=[("SpriteLite Projects", "*.sprlite")]
        )
        if filepath:
            self.current_file = filepath
            self._save_to_file(filepath)

    def _save_to_file(self, filepath):
        try:
            if filepath.lower().endswith(".sprlite"):
                project_data = self._build_project_data()
                with open(filepath, "w", encoding="utf-8") as file_handle:
                    json.dump(project_data, file_handle)
            else:
                self._save_png(filepath)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save image: {e}")

    def _export_flat(self):
        filepath = filedialog.asksaveasfilename(
            title="Export PNG",
            defaultextension=".png",
            filetypes=[("PNG Files", "*.png")]
        )
        if filepath:
            try:
                self._save_png(filepath)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export PNG: {e}")

    def _import_png(self):
        if not PIL_AVAILABLE:
            messagebox.showerror("Error", "PIL not available")
            return

        filepath = filedialog.askopenfilename(
            title="Import PNG",
            filetypes=[("PNG Files", "*.png"), ("All Files", "*.*")]
        )
        if not filepath:
            return

        try:
            img = PILImage.open(filepath)
            if img.mode != "RGBA":
                img = img.convert("RGBA")

            self._load_empty_canvas(img.width, img.height)
            layer = self.layer_manager.layers[0]
            layer.pixels = bytearray(img.tobytes())
            self.layer_manager.mark_dirty()
            self.current_file = None
            self.canvas.redraw()
            self._update_layer_list()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import PNG: {e}")

    def _load_empty_canvas(self, width, height):
        history = HistoryManager(20)
        layer_manager = LayerManager(width, height, history)
        self.palette_manager.colors = DEFAULT_PALETTE[:]
        self._apply_document_state(layer_manager, history)
        self._update_palette()
        self.current_file = None

    def _request_view_reset(self):
        self._pending_view_reset = True
        if hasattr(self, "canvas"):
            self.canvas.redraw()

    def _on_canvas_configure(self, event):
        if event.width <= 1 or event.height <= 1:
            return

        if self._pending_view_reset:
            self._pending_view_reset = False
            self._reset_canvas_view()
        elif self._last_canvas_size is not None:
            previous_width, previous_height = self._last_canvas_size
            self.canvas.handle_resize(
                previous_width, previous_height, event.width, event.height)
        else:
            self.canvas.redraw()

        self._last_canvas_size = (event.width, event.height)

    def _reset_canvas_view(self):
        if self.canvas.winfo_width() <= 1 or self.canvas.winfo_height() <= 1:
            self._request_view_reset()
            return

        self.canvas.zoom = DEFAULT_ZOOM
        self.canvas.center_document()
        self.canvas.focus_set()
        self.canvas.redraw()
        self._last_canvas_size = (
            self.canvas.winfo_width(),
            self.canvas.winfo_height(),
        )

    def _apply_document_state(self, layer_manager, history):
        self.width = layer_manager.width
        self.height = layer_manager.height
        self._update_canvas_size_display()
        self.history = history
        self.layer_manager = layer_manager
        self.canvas.layer_manager = layer_manager
        self.canvas.history = history
        self.canvas.zoom = DEFAULT_ZOOM
        self.canvas.is_painting = False
        self.canvas.last_pos = None
        self.canvas._reset_selection_drag()
        self.canvas.tool_manager.clear_selection()
        self._last_canvas_size = None
        self._request_view_reset()
        self._update_layer_list()

    def _build_project_data(self):
        return {
            "format": "spritelite-project",
            "version": 1,
            "width": self.width,
            "height": self.height,
            "active_layer_index": self.layer_manager.active_layer_index,
            "foreground": self.foreground,
            "background": self.background,
            "show_grid": self.show_grid,
            "palette": self.palette_manager.colors,
            "layers": [
                {
                    "name": layer.name,
                    "visible": layer.visible,
                    "pixels": bytes(layer.pixels).hex()
                }
                for layer in self.layer_manager.layers
            ]
        }

    def _load_project_file(self, filepath):
        with open(filepath, "r", encoding="utf-8") as file_handle:
            project_data = json.load(file_handle)

        if project_data.get("format") != "spritelite-project":
            raise ValueError("Unsupported project file format.")

        width = int(project_data["width"])
        height = int(project_data["height"])
        if width < 1 or height < 1:
            raise ValueError("Project dimensions are invalid.")

        history = HistoryManager(20)
        layer_manager = LayerManager(width, height, history)
        layer_manager.layers = []

        expected_pixel_bytes = width * height * 4
        for layer_data in project_data.get("layers", []):
            layer = Layer(layer_data.get(
                "name", f"Layer {len(layer_manager.layers) + 1}"), width, height)
            layer.visible = bool(layer_data.get("visible", True))
            pixel_data = bytearray.fromhex(layer_data.get("pixels", ""))
            if len(pixel_data) != expected_pixel_bytes:
                raise ValueError(
                    "Layer pixel data does not match project size.")
            layer.pixels = pixel_data
            layer_manager.layers.append(layer)

        if not layer_manager.layers:
            layer_manager.layers = [Layer("Layer 1", width, height)]

        active_layer_index = int(project_data.get("active_layer_index", 0))
        layer_manager.active_layer_index = min(
            max(active_layer_index, 0), len(layer_manager.layers) - 1)

        self.foreground = project_data.get("foreground", "#000000")
        self.background = project_data.get("background", "#FFFFFF")
        self.show_grid = bool(project_data.get("show_grid", True))
        self.grid_var.set(self.show_grid)

        palette = project_data.get("palette")
        if isinstance(palette, list) and palette:
            self.palette_manager.colors = palette
        else:
            self.palette_manager.colors = DEFAULT_PALETTE[:]

        self._apply_document_state(layer_manager, history)
        self._update_palette()
        self._update_color_display()

    def _save_png(self, filepath):
        if not PIL_AVAILABLE:
            raise RuntimeError("PIL not available")

        img = PILImage.new("RGBA", (self.width, self.height))
        composite = self.layer_manager.render_composite()
        img.frombytes(composite)
        img.save(filepath, "PNG")

    def _undo(self):
        state = self.history.undo(self.layer_manager.layers)
        if state:
            layer_idx, pixel_data = state
            self.layer_manager.layers[layer_idx].pixels = bytearray(pixel_data)
            self.layer_manager.mark_dirty()
            self.canvas.redraw()

    def _redo(self):
        state = self.history.redo(self.layer_manager.layers)
        if state:
            layer_idx, pixel_data = state
            self.layer_manager.layers[layer_idx].pixels = bytearray(pixel_data)
            self.layer_manager.mark_dirty()
            self.canvas.redraw()

    def run(self):
        self.root.mainloop()


def main():
    """Entry point."""
    app = App()
    app.run()


if __name__ == "__main__":
    main()
