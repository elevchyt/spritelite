"""
SpriteLite - A lightweight pixel art editor
Single entry point for the application
"""

import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox
import os
import json

try:
    from PIL import Image as PILImage, ImageTk as PILImageTk
    PIL_AVAILABLE = True
    PILImage  # Prevent unused import warning
    PILImageTk  # Prevent unused import warning
except ImportError:
    PILImage = None
    PILImageTk = None
    PIL_AVAILABLE = False


# Color scheme
BG_COLOR = "#1e1e1e"
PANEL_COLOR = "#252526"
BORDER_COLOR = "#3c3c3c"
TEXT_COLOR = "#d4d4d4"
ACCENT_COLOR = "#007acc"

DEFAULT_ZOOM = 16
ZOOM_LEVELS = [8, 16, 32]

DEFAULT_PALETTE = [
    "#000000", "#1D2B53", "#7E2553", "#008751",
    "#AB5236", "#5F574F", "#C2C3C7", "#FFF1E8",
    "#FF004D", "#FFA300", "#FFEC27", "#00E436",
    "#29ADFF", "#83769C", "#FF77A8", "#FFCCAA"
]


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

    def undo(self):
        """Pop from undo stack, push current state to redo, return state to restore."""
        if not self.undo_stack:
            return None
        layer_index, pixel_data = self.undo_stack.pop()
        self.redo_stack.append((layer_index, bytearray(pixel_data)))
        return layer_index, pixel_data

    def redo(self):
        """Pop from redo stack, push current state to undo, return state to restore."""
        if not self.redo_stack:
            return None
        layer_index, pixel_data = self.redo_stack.pop()
        self.undo_stack.append((layer_index, bytearray(pixel_data)))
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

    def get_active_layer(self):
        return self.layers[self.active_layer_index]

    def add_layer(self):
        new_layer = Layer(f"Layer {len(self.layers) + 1}", self.width, self.height)
        self.layers.append(new_layer)
        self.active_layer_index = len(self.layers) - 1
        return self.active_layer_index

    def delete_layer(self):
        if len(self.layers) <= 1:
            return False
        self.layers.pop(self.active_layer_index)
        if self.active_layer_index >= len(self.layers):
            self.active_layer_index = len(self.layers) - 1
        return True

    def duplicate_layer(self):
        layer = self.get_active_layer()
        new_layer = layer.copy()
        new_layer.name = f"{layer.name} Copy"
        self.layers.insert(self.active_layer_index + 1, new_layer)
        self.active_layer_index += 1
        return self.active_layer_index

    def move_layer_up(self):
        if self.active_layer_index < len(self.layers) - 1:
            self.layers[self.active_layer_index], self.layers[self.active_layer_index + 1] = \
                self.layers[self.active_layer_index + 1], self.layers[self.active_layer_index]
            self.active_layer_index += 1
            return True
        return False

    def move_layer_down(self):
        if self.active_layer_index > 0:
            self.layers[self.active_layer_index], self.layers[self.active_layer_index - 1] = \
                self.layers[self.active_layer_index - 1], self.layers[self.active_layer_index]
            self.active_layer_index -= 1
            return True
        return False

    def toggle_visibility(self, index):
        self.layers[index].visible = not self.layers[index].visible

    def render_composite(self):
        """Render all visible layers to a single RGBA image."""
        composite = bytearray(self.width * self.height * 4)
        for layer in reversed(self.layers):
            if layer.visible:
                for i in range(0, len(layer.pixels), 4):
                    if layer.pixels[i + 3] > 0:  # Alpha > 0
                        composite[i] = layer.pixels[i]
                        composite[i + 1] = layer.pixels[i + 1]
                        composite[i + 2] = layer.pixels[i + 2]
                        composite[i + 3] = layer.pixels[i + 3]
        return bytes(composite)


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

    def set_tool(self, tool):
        self.current_tool = tool
        self.selection_start = None
        self.selection_end = None


class PaletteManager:
    """Manages color palette and active colors."""

    def __init__(self):
        self.colors = DEFAULT_PALETTE[:]
        self.foreground = "#000000"
        self.background = "#FFFFFF"

    def load_palette_file(self, filepath):
        ext = os.path.splitext(filepath)[1].lower()
        if ext == ".gpl":
            self._load_gpl(filepath)
        elif ext == ".pal":
            self._load_pal(filepath)
        else:
            self._load_image_colors(filepath)

    def _load_gpl(self, filepath):
        self.colors = []
        with open(filepath, 'r') as f:
            in_colors = False
            for line in f:
                if line.strip() == "BEGIN PALETTE":
                    in_colors = True
                elif line.strip() == "END PALETTE":
                    break
                elif in_colors:
                    parts = line.strip().split()
                    if len(parts) >= 4:
                        try:
                            r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                            self.colors.append(f"#{r:02X}{g:02X}{b:02X}")
                        except ValueError:
                            pass

    def _load_pal(self, filepath):
        self.colors = []
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('#') and len(line) == 7:
                    self.colors.append(line)

    def _load_image_colors(self, filepath):
        if not PIL_AVAILABLE:
            return
        img = PILImage.open(filepath)
        img = img.convert('RGBA')
        unique_colors = set()
        for pixel in img.getdata():
            if pixel[3] > 0:
                unique_colors.add(f"#{pixel[0]:02X}{pixel[1]:02X}{pixel[2]:02X}")
        self.colors = list(unique_colors)[:256]


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

        self.bind("<space>", lambda e: self._start_pan(e))
        self.bind("<KeyRelease-space>", self._end_pan)

        self._start_pan_pos = None
        self._middle_dragging = False
        self._space_held = False
        self._shift_held = False
        self._line_start_pos = None

        self.bind("<Shift-L>", lambda e: self._set_shift(True))
        self.bind("<Shift-R>", lambda e: self._set_shift(True))
        self.bind("<KeyRelease-Shift_L>", lambda e: self._set_shift(False))
        self.bind("<KeyRelease-Shift_R>", lambda e: self._set_shift(False))

    def _set_shift(self, state):
        self._shift_held = state

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
            self._start_pan_pos = (event.x, event.y)
            self.redraw()

    def on_middle_release(self, event):
        self._middle_dragging = False
        self._start_pan_pos = None

    def on_mousewheel(self, event):
        if event.delta > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def zoom_in(self):
        idx = ZOOM_LEVELS.index(self.zoom) if self.zoom in ZOOM_LEVELS else 1
        if idx < len(ZOOM_LEVELS) - 1:
            self.zoom = ZOOM_LEVELS[idx + 1]
            self.redraw()

    def zoom_out(self):
        idx = ZOOM_LEVELS.index(self.zoom) if self.zoom in ZOOM_LEVELS else 1
        if idx > 0:
            self.zoom = ZOOM_LEVELS[idx - 1]
            self.redraw()

    def screen_to_canvas(self, sx, sy):
        w = self.layer_manager.width
        h = self.layer_manager.height
        cx = (sx - self.offset_x) // self.zoom
        cy = (sy - self.offset_y) // self.zoom
        return cx, cy

    def on_click(self, event):
        if self._space_held or self._middle_dragging:
            return

        cx, cy = self.screen_to_canvas(event.x, event.y)
        tool = self.tool_manager.current_tool

        if tool == "selection":
            self.tool_manager.selection_start = (cx, cy)
            self.tool_manager.selection_end = (cx, cy)
        else:
            self.is_painting = True
            self._line_start_pos = (cx, cy)
            self.apply_tool(cx, cy, tool, is_click=True)

    def on_drag(self, event):
        if self._space_held or self._middle_dragging:
            return

        cx, cy = self.screen_to_canvas(event.x, event.y)
        tool = self.tool_manager.current_tool

        if tool == "selection":
            self.tool_manager.selection_end = (cx, cy)
            self.redraw()
        elif self.is_painting:
            if tool == "pencil" and self._shift_held and self._line_start_pos:
                layer = self.layer_manager.get_active_layer()
                self.history.save_state(self.layer_manager.active_layer_index, layer.pixels)
                self._draw_line(self._line_start_pos[0], self._line_start_pos[1], cx, cy, self.app.foreground_rgba)
                self._line_start_pos = (cx, cy)
                self.last_pos = (cx, cy)
                self.redraw()
            elif self.last_pos != (cx, cy):
                self.apply_tool(cx, cy, tool)
                self.last_pos = (cx, cy)

    def on_release(self, event):
        self.is_painting = False
        self.last_pos = None
        self._line_start_pos = None

        if self.tool_manager.current_tool == "selection":
            self.redraw()

    def on_right_click(self, event):
        cx, cy = self.screen_to_canvas(event.x, event.y)
        tool = self.tool_manager.current_tool
        if tool == "eyedropper":
            layer = self.layer_manager.get_active_layer()
            color = layer.get_pixel(cx, cy)
            if color[3] > 0:
                self.app.set_background_color(f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}")

    def on_right_drag(self, event):
        pass

    def on_right_release(self, event):
        pass

    def apply_tool(self, cx, cy, tool, is_click=False):
        layer = self.layer_manager.get_active_layer()
        app = self.app

        if tool == "pencil":
            if is_click:
                self.history.save_state(self.layer_manager.active_layer_index, layer.pixels)
            layer.set_pixel(cx, cy, app.foreground_rgba)
            self.redraw()

        elif tool == "eraser":
            if is_click:
                self.history.save_state(self.layer_manager.active_layer_index, layer.pixels)
            layer.set_pixel(cx, cy, (0, 0, 0, 0))
            self.redraw()

        elif tool == "bucket":
            if is_click:
                self._bucket_fill(layer, cx, cy, app.foreground_rgba)
                self.redraw()

        elif tool == "eyedropper":
            color = layer.get_pixel(cx, cy)
            if color[3] > 0:
                app.set_foreground_color(f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}")

    def _bucket_fill(self, layer, start_x, start_y, fill_color):
        w, h = layer.width, layer.height
        if not (0 <= start_x < w and 0 <= start_y < h):
            return
        
        target_color = layer.get_pixel(start_x, start_y)
        if target_color == fill_color:
            return
        
        self.history.save_state(self.layer_manager.active_layer_index, layer.pixels)
        
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

    def redraw(self):
        """Redraw the canvas with checkerboard and all layers."""
        self.delete("all")

        w = self.layer_manager.width
        h = self.layer_manager.height
        zoom = self.zoom

        canvas_width = self.winfo_width() or 800
        canvas_height = self.winfo_height() or 600

        check_size = max(zoom // 4, 4)
        for y in range(h):
            for x in range(w):
                px = self.offset_x + x * zoom
                py = self.offset_y + y * zoom

                if (x // check_size + y // check_size) % 2 == 0:
                    self.create_rectangle(px, py, px + zoom, py + zoom, fill="#2a2a2a", outline="")
                else:
                    self.create_rectangle(px, py, px + zoom, py + zoom, fill="#333333", outline="")

        composite = self.layer_manager.render_composite()

        for y in range(h):
            for x in range(w):
                idx = (y * w + x) * 4
                r, g, b, a = composite[idx:idx + 4]
                if a > 0:
                    px = self.offset_x + x * zoom
                    py = self.offset_y + y * zoom
                    color = f"#{r:02X}{g:02X}{b:02X}"
                    self.create_rectangle(px, py, px + zoom, py + zoom, fill=color, outline="")

        if self.tool_manager.current_tool == "selection":
            start = self.tool_manager.selection_start
            end = self.tool_manager.selection_end
            if start and end:
                x1 = self.offset_x + min(start[0], end[0]) * zoom
                y1 = self.offset_y + min(start[1], end[1]) * zoom
                x2 = self.offset_x + (max(start[0], end[0]) + 1) * zoom
                y2 = self.offset_y + (max(start[1], end[1]) + 1) * zoom
                self.create_rectangle(x1, y1, x2, y2, outline=ACCENT_COLOR, dash=(4, 4), width=2)

        if self.app and self.app.show_grid:
            for x in range(w + 1):
                px = self.offset_x + x * zoom
                self.create_line(px, self.offset_y, px, self.offset_y + h * zoom, fill="#444444", width=1)
            for y in range(h + 1):
                py = self.offset_y + y * zoom
                self.create_line(self.offset_x, py, self.offset_x + w * zoom, py, fill="#444444", width=1)

        self.tag_raise("selection")


class App:
    """Main application window."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("SpriteLite")
        self.root.geometry("1024x768")
        self.root.configure(bg=BG_COLOR)

        self.width = 32
        self.height = 32

        self.history = HistoryManager(20)
        self.layer_manager = LayerManager(self.width, self.height, self.history)
        self.tool_manager = ToolManager()
        self.palette_manager = PaletteManager()

        self.foreground = "#000000"
        self.background = "#FFFFFF"
        self.show_grid = True

        self._load_icons()
        self._setup_ui()
        self._setup_menu()
        self._setup_keybindings()

        self.canvas_frame.bind("<Configure>", lambda e: self.canvas.redraw())

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
                    img = PILImage.open(path).convert("RGBA")
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

        toolbar = tk.Frame(main_container, bg=PANEL_COLOR, width=60, padx=2, pady=2)
        toolbar.pack(side=tk.LEFT, fill=tk.Y)
        toolbar.pack_propagate(False)

        self._setup_toolbar(toolbar)

        canvas_container = tk.Frame(main_container, bg=BG_COLOR)
        canvas_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas_frame = canvas_container
        self.canvas = DrawingCanvas(canvas_container, self.layer_manager, self.tool_manager, self.history)
        self.canvas.app = self
        self.canvas.pack(fill=tk.BOTH, expand=True)

        right_panel = tk.Frame(main_container, bg=PANEL_COLOR, width=200, padx=2, pady=2)
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
            label = tk.Label(self.tooltip_window, text=text, bg="#444444", fg="white", padx=6, pady=2, font=("Arial", 8))
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
                btn.config(text=icon_key[0].upper(), font=("Arial", 11, "bold"))
            btn.pack(pady=2, padx=2)
            btn.bind("<Enter>", lambda e, w=btn, t=tooltip: show_tooltip(w, t, e))
            btn.bind("<Leave>", hide_tooltip)
            self.tool_buttons[tool_id] = btn

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
        layer_frame = tk.LabelFrame(parent, text="Layers", bg=PANEL_COLOR, fg=TEXT_COLOR, padx=5, pady=5)
        layer_frame.pack(fill=tk.X, pady=(0, 10))

        self.layer_canvas = tk.Canvas(layer_frame, bg="#333333", height=160, highlightthickness=0)
        self.layer_scrollbar = tk.Scrollbar(layer_frame, orient=tk.VERTICAL, command=self.layer_canvas.yview)
        self.layer_canvas.configure(yscrollcommand=self.layer_scrollbar.set)
        
        self.layer_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.layer_canvas.pack(fill=tk.X, expand=False)
        
        self.layer_inner = tk.Frame(self.layer_canvas, bg="#333333")
        self.layer_canvas.create_window((0, 0), window=self.layer_inner, anchor=tk.NW)
        
        self.layer_inner.bind("<Configure>", lambda e: self.layer_canvas.configure(scrollregion=self.layer_canvas.bbox("all")))

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
                label = tk.Label(self.tooltip_window, text=text, bg="#444444", fg="white", padx=6, pady=2, font=("Arial", 8))
                label.pack()
            def hide(event):
                if hasattr(self, 'tooltip_window') and self.tooltip_window:
                    self.tooltip_window.destroy()
                    self.tooltip_window = None
            widget.bind("<Enter>", show)
            widget.bind("<Leave>", hide)

        add_btn = tk.Button(btn_frame, text="+", width=3, bg=PANEL_COLOR, fg=TEXT_COLOR, command=self._add_layer)
        add_btn.pack(side=tk.LEFT, padx=1)
        make_tooltip(add_btn, "Add Layer")
        
        trash_icon = self.icons.get("trash")
        del_btn = tk.Button(btn_frame, image=trash_icon, width=20, height=18, bg=PANEL_COLOR, relief=tk.FLAT, command=self._delete_layer)
        if not trash_icon:
            del_btn.config(text="-", width=3, fg=TEXT_COLOR)
        del_btn.pack(side=tk.LEFT, padx=1)
        make_tooltip(del_btn, "Delete Layer")
        
        dup_btn = tk.Button(btn_frame, text="D", width=3, bg=PANEL_COLOR, fg=TEXT_COLOR, command=self._duplicate_layer)
        dup_btn.pack(side=tk.LEFT, padx=1)
        make_tooltip(dup_btn, "Duplicate Layer")
        
        up_btn = tk.Button(btn_frame, text="^", width=3, bg=PANEL_COLOR, fg=TEXT_COLOR, command=self._move_layer_down)
        up_btn.pack(side=tk.LEFT, padx=1)
        make_tooltip(up_btn, "Move Layer Up")
        
        down_btn = tk.Button(btn_frame, text="v", width=3, bg=PANEL_COLOR, fg=TEXT_COLOR, command=self._move_layer_up)
        down_btn.pack(side=tk.LEFT, padx=1)
        make_tooltip(down_btn, "Move Layer Down")

        self._update_layer_list()

    def _setup_palette_panel(self, parent):
        """Setup the color palette panel."""
        palette_frame = tk.LabelFrame(parent, text="Palette", bg=PANEL_COLOR, fg=TEXT_COLOR, padx=5, pady=5)
        palette_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.palette_canvas = tk.Canvas(palette_frame, bg=PANEL_COLOR, highlightthickness=0)
        self.palette_scrollbar = tk.Scrollbar(palette_frame, orient=tk.VERTICAL, command=self.palette_canvas.yview)
        self.palette_canvas.configure(yscrollcommand=self.palette_scrollbar.set)

        self.palette_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.palette_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.palette_inner = tk.Frame(self.palette_canvas, bg=PANEL_COLOR)
        self.palette_canvas.create_window((0, 0), window=self.palette_inner, anchor=tk.NW)

        self.palette_inner.bind("<Configure>", lambda e: self.palette_canvas.configure(scrollregion=self.palette_canvas.bbox("all")))

        tk.Button(palette_frame, text="Load Palette", bg=PANEL_COLOR, fg=TEXT_COLOR, command=self._load_palette).pack(fill=tk.X, pady=2)

        self._update_palette()

    def _setup_color_picker(self, parent):
        """Setup the color picker display."""
        color_frame = tk.LabelFrame(parent, text="Colors", bg=PANEL_COLOR, fg=TEXT_COLOR, padx=5, pady=5)
        color_frame.pack(fill=tk.X)

        self.fg_color_canvas = tk.Canvas(color_frame, width=50, height=50, bg=BG_COLOR, highlightthickness=1, highlightbackground=BORDER_COLOR)
        self.fg_color_canvas.pack(pady=2)
        self.fg_color_canvas.bind("<Button-1>", lambda e: self._choose_color("foreground"))
        self.fg_color_canvas.bind("<Button-3>", lambda e: self._choose_color("background"))

        self._update_color_display()

    def _update_color_display(self):
        self.fg_color_canvas.delete("all")
        bg = self.background
        fg = self.foreground
        self.fg_color_canvas.create_rectangle(5, 5, 45, 45, fill=bg, outline="")
        self.fg_color_canvas.create_rectangle(10, 10, 40, 40, fill=fg, outline="")

    def _choose_color(self, target):
        if target == "foreground":
            color = colorchooser.askcolor(self.foreground, title="Choose Foreground Color")
            if color[1]:
                self.set_foreground_color(color[1])
        else:
            color = colorchooser.askcolor(self.background, title="Choose Background Color")
            if color[1]:
                self.set_background_color(color[1])

    def set_foreground_color(self, color):
        self.foreground = color
        self._update_color_display()

    def set_background_color(self, color):
        self.background = color
        self._update_color_display()

    @property
    def foreground_rgba(self):
        r = int(self.foreground[1:3], 16)
        g = int(self.foreground[3:5], 16)
        b = int(self.foreground[5:7], 16)
        return (r, g, b, 255)

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
                command=lambda idx=i: self._toggle_layer_visibility_by_index(idx)
            )
            if eye_icon:
                eye_btn.config(image=eye_icon)
            else:
                eye_btn.config(text="O" if layer.visible else "x")
            eye_btn.pack(side=tk.LEFT, padx=(2, 5))
            
            name_label = tk.Label(
                row_frame, text=layer.name, bg=bg_color, fg=TEXT_COLOR,
                font=("Arial", 9), anchor="w"
            )
            name_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            name_label.bind("<Button-1>", lambda e, idx=i: self._select_layer(idx))
            
            row_frame.bind("<Button-1>", lambda e, idx=i: self._select_layer(idx))

    def _select_layer(self, index):
        self.layer_manager.active_layer_index = index
        self._update_layer_list()

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

    def _toggle_layer_visibility(self, event=None):
        self.layer_manager.toggle_visibility(self.layer_manager.active_layer_index)
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
            swatch = tk.Canvas(self.palette_inner, width=20, height=20, bg=color, highlightthickness=1, highlightbackground=BORDER_COLOR)
            swatch.grid(row=row, column=col, padx=1, pady=1)
            swatch.bind("<Button-1>", lambda e, c=color: self._set_color(e, c))
            swatch.bind("<Button-3>", lambda e, c=color: self._set_bg_color(e, c))

    def _set_color(self, event, color):
        self.set_foreground_color(color)

    def _set_bg_color(self, event, color):
        self.set_background_color(color)

    def _load_palette(self):
        filepath = filedialog.askopenfilename(
            title="Load Palette",
            filetypes=[("Palette Files", "*.gpl *.pal *.png"), ("All Files", "*.*")]
        )
        if filepath:
            self.palette_manager.load_palette_file(filepath)
            self._update_palette()

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
        file_menu.add_command(label="New", command=self._new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="Open", command=self._open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="Save", command=self._save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As", command=self._save_file_as)
        file_menu.add_command(label="Export Flat", command=self._export_flat)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        view_menu = tk.Menu(menubar, bg=PANEL_COLOR, fg=TEXT_COLOR, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        self.grid_var = tk.BooleanVar(value=True)
        view_menu.add_checkbutton(label="Show Grid    (Ctrl+H)", variable=self.grid_var, command=self._toggle_grid)
        view_menu.add_separator()
        view_menu.add_command(label="Zoom In", command=self.canvas.zoom_in, accelerator="+")
        view_menu.add_command(label="Zoom Out", command=self.canvas.zoom_out, accelerator="-")

    def _setup_keybindings(self):
        """Setup keyboard shortcuts."""
        self.root.bind("<p>", lambda e: self._select_tool("pencil"))
        self.root.bind("<e>", lambda e: self._select_tool("eraser"))
        self.root.bind("<i>", lambda e: self._select_tool("eyedropper"))
        self.root.bind("<b>", lambda e: self._select_tool("bucket"))
        self.root.bind("<B>", lambda e: self._select_tool("bucket"))
        self.root.bind("<s>", lambda e: self._select_tool("selection"))
        self.root.bind("<plus>", lambda e: self.canvas.zoom_in())
        self.root.bind("<KP_Add>", lambda e: self.canvas.zoom_in())
        self.root.bind("<minus>", lambda e: self.canvas.zoom_out())
        self.root.bind("<KP_Subtract>", lambda e: self.canvas.zoom_out())

        self.root.bind("<Control-z>", lambda e: self._undo())
        self.root.bind("<Control-y>", lambda e: self._redo())
        self.root.bind("<Control-s>", lambda e: self._save_file())
        self.root.bind("<Control-o>", lambda e: self._open_file())
        self.root.bind("<Control-n>", lambda e: self._new_file())
        self.root.bind("<Control-h>", lambda e: self._toggle_grid())
        self.root.bind("<Delete>", lambda e: self._delete_selection())
        self.root.bind("<BackSpace>", lambda e: self._delete_selection())

    def _toggle_grid(self):
        self.show_grid = not self.show_grid
        self.grid_var.set(self.show_grid)
        self.canvas.redraw()

    def _delete_selection(self):
        selection = self.canvas.tool_manager.selection
        if selection:
            x1, y1, x2, y2 = selection
            layer = self.layer_manager.get_active_layer()
            self.history.save_state(self.layer_manager.active_layer_index, layer.pixels)
            for y in range(max(0, y1), min(y2 + 1, layer.height)):
                for x in range(max(0, x1), min(x2 + 1, layer.width)):
                    layer.set_pixel(x, y, (0, 0, 0, 0))
            self.canvas.tool_manager.selection_start = None
            self.canvas.tool_manager.selection_end = None
            self.canvas.redraw()

    def _new_file(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("New Canvas")
        dialog.geometry("300x200")
        dialog.configure(bg=BG_COLOR)
        dialog.transient(self.root)

        tk.Label(dialog, text="Width:", bg=BG_COLOR, fg=TEXT_COLOR).pack(pady=5)
        width_var = tk.StringVar(value="32")
        tk.Entry(dialog, textvariable=width_var, width=10).pack()

        tk.Label(dialog, text="Height:", bg=BG_COLOR, fg=TEXT_COLOR).pack(pady=5)
        height_var = tk.StringVar(value="32")
        tk.Entry(dialog, textvariable=height_var, width=10).pack()

        def create_canvas():
            try:
                w = min(128, max(1, int(width_var.get())))
                h = min(128, max(1, int(height_var.get())))
                self.width = w
                self.height = h
                self.history = HistoryManager(20)
                self.layer_manager = LayerManager(w, h, self.history)
                self.canvas.layer_manager = self.layer_manager
                self.canvas.zoom = DEFAULT_ZOOM
                self.canvas.offset_x = 0
                self.canvas.offset_y = 0
                self.canvas.redraw()
                self._update_layer_list()
                dialog.destroy()
            except ValueError:
                pass

        tk.Button(dialog, text="Create", command=create_canvas, bg=PANEL_COLOR, fg=TEXT_COLOR).pack(pady=20)

    def _open_file(self):
        filepath = filedialog.askopenfilename(
            title="Open Image",
            filetypes=[("PNG Files", "*.png"), ("All Files", "*.*")]
        )
        if filepath and PIL_AVAILABLE:
            try:
                img = PILImage.open(filepath)
                if img.mode != "RGBA":
                    img = img.convert("RGBA")
                self.width = img.width
                self.height = img.height
                self.history = HistoryManager(20)
                self.layer_manager = LayerManager(self.width, self.height, self.history)
                layer = self.layer_manager.layers[0]
                layer.pixels = bytearray(img.tobytes())
                self.canvas.layer_manager = self.layer_manager
                self.canvas.zoom = DEFAULT_ZOOM
                self.canvas.offset_x = 0
                self.canvas.offset_y = 0
                self.canvas.redraw()
                self._update_layer_list()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open image: {e}")

    def _save_file(self):
        if not hasattr(self, 'current_file'):
            self._save_file_as()
        else:
            self._save_to_file(self.current_file)

    def _save_file_as(self):
        filepath = filedialog.asksaveasfilename(
            title="Save Image",
            defaultextension=".png",
            filetypes=[("PNG Files", "*.png")]
        )
        if filepath:
            self.current_file = filepath
            self._save_to_file(filepath)

    def _save_to_file(self, filepath):
        if not PIL_AVAILABLE:
            messagebox.showerror("Error", "PIL not available")
            return

        try:
            img = PILImage.new("RGBA", (self.width, self.height))
            composite = self.layer_manager.render_composite()
            img.frombytes(composite)
            img.save(filepath, "PNG")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save image: {e}")

    def _export_flat(self):
        self._save_file_as()

    def _undo(self):
        state = self.history.undo()
        if state:
            layer_idx, pixel_data = state
            self.layer_manager.layers[layer_idx].pixels = bytearray(pixel_data)
            self.canvas.redraw()

    def _redo(self):
        state = self.history.redo()
        if state:
            layer_idx, pixel_data = state
            self.layer_manager.layers[layer_idx].pixels = bytearray(pixel_data)
            self.canvas.redraw()

    def run(self):
        self.root.mainloop()


def main():
    """Entry point."""
    app = App()
    app.run()


if __name__ == "__main__":
    main()
