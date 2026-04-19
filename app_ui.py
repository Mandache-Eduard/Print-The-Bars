import tkinter as tk
import re
from tkinter import ttk

try:
    from PIL import Image
    from PIL import ImageTk
    from PIL import UnidentifiedImageError
except ImportError:
    Image = None
    ImageTk = None
    UnidentifiedImageError = OSError

from codes_panel import CodesPanel
from content_panel import ContentPanel
from export_panel import ExportPanel
from source_panel import SourcePanel
from state import AppState
from style_panel import FittedPage
from style_panel import build_square_layout
from style_panel import fit_iso_portrait_page
from style_panel import normalized_square_to_output
from style_panel import StylePanel


class AlbumPosterAppUI:
    def __init__(self, root: tk.Tk, state: AppState) -> None:
        self.root = root
        self.state = state
        self._cover_preview_image: tk.PhotoImage | None = None

        self.root.title("Album Poster Builder")
        self.root.geometry("1280x780")
        self.root.minsize(980, 650)

        self._configure_root()
        self._build_layout()
        self._build_menu_panel()
        self._build_preview_panel()

    def _configure_root(self) -> None:
        self.root.columnconfigure(0, weight=25, uniform="layout")
        self.root.columnconfigure(1, weight=75, uniform="layout")
        self.root.rowconfigure(0, weight=1)

    def _build_layout(self) -> None:
        self.menu_frame = ttk.Frame(self.root, padding=16)
        self.preview_frame = ttk.Frame(self.root, padding=16)

        self.menu_frame.grid(row=0, column=0, sticky="nsew")
        self.preview_frame.grid(row=0, column=1, sticky="nsew")

        self.menu_frame.columnconfigure(0, weight=1)
        self.menu_frame.rowconfigure(1, weight=1)
        self.preview_frame.columnconfigure(0, weight=1)
        self.preview_frame.rowconfigure(1, weight=1)

    def _build_menu_panel(self) -> None:
        title = ttk.Label(self.menu_frame, text="Controls", font=("Segoe UI", 18, "bold"))
        title.grid(row=0, column=0, sticky="w", pady=(0, 12))

        self.menu_canvas = tk.Canvas(self.menu_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            self.menu_frame,
            orient="vertical",
            command=self.menu_canvas.yview,
        )
        self.scrollable_menu = ttk.Frame(self.menu_canvas)

        self.scrollable_menu.bind(
            "<Configure>",
            lambda _event: self.menu_canvas.configure(
                scrollregion=self.menu_canvas.bbox("all")
            ),
        )

        self.menu_window = self.menu_canvas.create_window(
            (0, 0),
            window=self.scrollable_menu,
            anchor="nw",
        )

        self.menu_canvas.bind(
            "<Configure>",
            lambda event: self.menu_canvas.itemconfigure(self.menu_window, width=event.width),
        )
        self.menu_canvas.configure(yscrollcommand=scrollbar.set)

        self.menu_canvas.grid(row=1, column=0, sticky="nsew")
        scrollbar.grid(row=1, column=1, sticky="ns")

        self._bind_mousewheel(self.menu_frame)
        self._bind_mousewheel(self.menu_canvas)

        self.scrollable_menu.columnconfigure(0, weight=1)

        SourcePanel(self.scrollable_menu, self.state, self._bind_mousewheel_recursive).build(0)
        ContentPanel(self.scrollable_menu, self.state, self._bind_mousewheel_recursive).build(1)
        StylePanel(self.scrollable_menu, self.state, self._bind_mousewheel_recursive).build(2)
        CodesPanel(self.scrollable_menu, self.state, self._bind_mousewheel_recursive).build(3)
        ExportPanel(self.scrollable_menu, self.state, self._bind_mousewheel_recursive).build(4)

        self._bind_mousewheel_recursive(self.scrollable_menu)

    def _bind_mousewheel(self, widget: tk.Misc) -> None:
        widget.bind("<MouseWheel>", self._on_mousewheel)
        widget.bind("<Button-4>", self._on_mousewheel_linux)
        widget.bind("<Button-5>", self._on_mousewheel_linux)

    def _bind_mousewheel_recursive(self, widget: tk.Misc) -> None:
        self._bind_mousewheel(widget)
        for child in widget.winfo_children():
            if isinstance(child, ttk.Combobox):
                continue
            self._bind_mousewheel_recursive(child)

    def _on_mousewheel(self, event: tk.Event) -> None:
        self.menu_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_linux(self, event: tk.Event) -> None:
        if event.num == 4:
            self.menu_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.menu_canvas.yview_scroll(1, "units")

    def _build_preview_panel(self) -> None:
        title = ttk.Label(
            self.preview_frame,
            text="Poster Preview",
            font=("Segoe UI", 18, "bold"),
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 16))

        self.preview_canvas = tk.Canvas(
            self.preview_frame,
            bg="#f4f4f4",
            highlightthickness=1,
            highlightbackground="#cfcfcf",
        )
        self.preview_canvas.grid(row=1, column=0, sticky="nsew")

        self._draw_preview_placeholder(self.preview_canvas)
        self.preview_canvas.bind(
            "<Configure>",
            lambda _event: self._redraw_preview(self.preview_canvas),
        )
        self.state.poster_size_var.trace_add("write", self._on_poster_size_change)
        self.state.margin_ratio_var.trace_add("write", self._on_margin_ratio_change)
        self.state.cover_image_path_var.trace_add("write", self._on_cover_image_change)

    def _on_poster_size_change(self, *_args: object) -> None:
        if hasattr(self, "preview_canvas"):
            self._redraw_preview(self.preview_canvas)

    def _on_margin_ratio_change(self, *_args: object) -> None:
        if hasattr(self, "preview_canvas"):
            self._redraw_preview(self.preview_canvas)

    def _on_cover_image_change(self, *_args: object) -> None:
        if hasattr(self, "preview_canvas"):
            self._redraw_preview(self.preview_canvas)

    def _get_selected_dimensions(self) -> tuple[str | None, str | None]:
        value = self.state.poster_size_var.get()
        match = re.search(r"([\d.]+)\s*x\s*([\d.]+)\s*cm\s*\|\s*([\d.]+)\s*x\s*([\d.]+)\s*inches", value)
        if not match:
            return None, None

        width_cm, height_cm, width_in, height_in = match.groups()
        width_text = f"{width_cm} cm | {width_in} inches"
        height_text = f"{height_cm} cm | {height_in} inches"
        return width_text, height_text

    def _draw_cover_image_or_placeholder(
        self,
        canvas: tk.Canvas,
        cover_x1: float,
        cover_y1: float,
        cover_x2: float,
        cover_y2: float,
    ) -> None:
        path = self.state.cover_image_path_var.get().strip()
        target_width = max(int(cover_x2 - cover_x1), 1)
        target_height = max(int(cover_y2 - cover_y1), 1)

        if path and Image is not None and ImageTk is not None:
            try:
                with Image.open(path) as raw_image:
                    source_width, source_height = raw_image.size
                    image = raw_image.convert("RGB")
                    if source_width == source_height:
                        image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)
                    else:
                        image = image.resize((target_width, target_height), Image.Resampling.BICUBIC)

                self._cover_preview_image = ImageTk.PhotoImage(image)
                canvas.create_image(cover_x1, cover_y1, image=self._cover_preview_image, anchor="nw")
                return
            except (FileNotFoundError, OSError, UnidentifiedImageError):
                pass

        self._cover_preview_image = None
        canvas.create_rectangle(
            cover_x1,
            cover_y1,
            cover_x2,
            cover_y2,
            fill="#dcdcdc",
            outline="#999999",
        )
        canvas.create_text(
            (cover_x1 + cover_x2) / 2,
            (cover_y1 + cover_y2) / 2,
            text="Album Cover",
            font=("Segoe UI", 14),
            fill="#555555",
        )

    def _draw_preview_placeholder(self, canvas: tk.Canvas) -> None:
        width = max(canvas.winfo_width(), 1)
        height = max(canvas.winfo_height(), 1)

        canvas.delete("all")

        margin = 24
        label_space_right = 155
        label_space_bottom = 44
        drawable_x = margin
        drawable_y = margin
        drawable_width = max(width - (2 * margin) - label_space_right, 1)
        drawable_height = max(height - (2 * margin) - label_space_bottom, 1)

        fitted_page = fit_iso_portrait_page(drawable_width, drawable_height)

        poster_x1 = drawable_x + fitted_page.x
        poster_y1 = drawable_y + fitted_page.y
        poster_x2 = poster_x1 + fitted_page.width
        poster_y2 = poster_y1 + fitted_page.height
        poster_center_x = (poster_x1 + poster_x2) / 2
        poster_height = poster_y2 - poster_y1
        poster_width = poster_x2 - poster_x1

        try:
            margin_ratio = float(self.state.margin_ratio_var.get())
            cover_layout = build_square_layout(margin_ratio)
        except (ValueError, tk.TclError):
            cover_layout = build_square_layout(0.12)

        poster_page = FittedPage(
            x=poster_x1,
            y=poster_y1,
            width=poster_width,
            height=poster_height,
            short_side=poster_width,
        )
        cover_x1, cover_y1, cover_x2, cover_y2 = normalized_square_to_output(
            cover_layout,
            poster_page,
        )

        # Subtle edge shadows for depth without reducing label readability.
        shadow_soft = "#e8e8e8"
        shadow_deep = "#d9d9d9"

        canvas.create_rectangle(
            poster_x1 - 6,
            poster_y1 + 4,
            poster_x1,
            poster_y2 + 8,
            fill=shadow_soft,
            outline="",
        )
        canvas.create_rectangle(
            poster_x1 - 3,
            poster_y1 + 2,
            poster_x1,
            poster_y2 + 6,
            fill=shadow_deep,
            outline="",
        )

        canvas.create_rectangle(
            poster_x2,
            poster_y1 + 4,
            poster_x2 + 8,
            poster_y2 + 8,
            fill=shadow_soft,
            outline="",
        )
        canvas.create_rectangle(
            poster_x2,
            poster_y1 + 2,
            poster_x2 + 5,
            poster_y2 + 6,
            fill=shadow_deep,
            outline="",
        )

        canvas.create_rectangle(
            poster_x1 + 4,
            poster_y2,
            poster_x2 + 8,
            poster_y2 + 8,
            fill=shadow_soft,
            outline="",
        )
        canvas.create_rectangle(
            poster_x1 + 2,
            poster_y2,
            poster_x2 + 6,
            poster_y2 + 5,
            fill=shadow_deep,
            outline="",
        )

        canvas.create_rectangle(
            poster_x1,
            poster_y1,
            poster_x2,
            poster_y2,
            fill="white",
            outline="#bbbbbb",
            width=2,
        )

        self._draw_cover_image_or_placeholder(
            canvas,
            cover_x1,
            cover_y1,
            cover_x2,
            cover_y2,
        )

        canvas.create_text(
            poster_center_x,
            cover_y2 + (poster_width * 0.18),
            text="Album Title",
            font=("Segoe UI", 22, "bold"),
            fill="#222222",
        )
        canvas.create_text(
            poster_center_x,
            cover_y2 + (poster_width * 0.28),
            text="Artist Name • Release Year",
            font=("Segoe UI", 13),
            fill="#666666",
        )

        width_text, height_text = self._get_selected_dimensions()
        if width_text is not None:
            canvas.create_text(
                poster_center_x,
                poster_y2 + 28,
                text=width_text,
                font=("Segoe UI", 10),
                fill="#444444",
            )
        if height_text is not None:
            canvas.create_text(
                poster_x2 + 22,
                (poster_y1 + poster_y2) / 2,
                text=height_text,
                font=("Segoe UI", 10),
                fill="#444444",
                anchor="w",
            )

    def _redraw_preview(self, canvas: tk.Canvas) -> None:
        self._draw_preview_placeholder(canvas)

