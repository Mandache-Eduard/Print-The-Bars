import tkinter as tk
from tkinter import ttk

from codes_panel import CodesPanel
from content_panel import ContentPanel
from export_panel import ExportPanel
from source_panel import SourcePanel
from state import AppState
from style_panel import StylePanel


class AlbumPosterAppUI:
    def __init__(self, root: tk.Tk, state: AppState) -> None:
        self.root = root
        self.state = state

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

        preview_canvas = tk.Canvas(
            self.preview_frame,
            bg="#f4f4f4",
            highlightthickness=1,
            highlightbackground="#cfcfcf",
        )
        preview_canvas.grid(row=1, column=0, sticky="nsew")

        self._draw_preview_placeholder(preview_canvas)
        preview_canvas.bind("<Configure>", lambda _event: self._redraw_preview(preview_canvas))

    def _draw_preview_placeholder(self, canvas: tk.Canvas) -> None:
        width = max(canvas.winfo_width(), 1)
        height = max(canvas.winfo_height(), 1)

        canvas.delete("all")

        margin = 40
        poster_x1 = margin
        poster_y1 = margin
        poster_x2 = width - margin
        poster_y2 = height - margin

        canvas.create_rectangle(
            poster_x1,
            poster_y1,
            poster_x2,
            poster_y2,
            fill="white",
            outline="#bbbbbb",
            width=2,
        )

        canvas.create_text(
            width / 2,
            80,
            text="Your poster preview will appear here",
            font=("Segoe UI", 16, "bold"),
            fill="#333333",
        )

        cover_size = min(width, height) * 0.28
        cover_x1 = width / 2 - cover_size / 2
        cover_y1 = height / 2 - cover_size / 2 - 40
        cover_x2 = width / 2 + cover_size / 2
        cover_y2 = height / 2 + cover_size / 2 - 40

        canvas.create_rectangle(
            cover_x1,
            cover_y1,
            cover_x2,
            cover_y2,
            fill="#dcdcdc",
            outline="#999999",
        )
        canvas.create_text(
            width / 2,
            (cover_y1 + cover_y2) / 2,
            text="Album Cover",
            font=("Segoe UI", 14),
            fill="#555555",
        )

        canvas.create_text(
            width / 2,
            cover_y2 + 55,
            text="Album Title",
            font=("Segoe UI", 22, "bold"),
            fill="#222222",
        )
        canvas.create_text(
            width / 2,
            cover_y2 + 90,
            text="Artist Name • Release Year",
            font=("Segoe UI", 13),
            fill="#666666",
        )

    def _redraw_preview(self, canvas: tk.Canvas) -> None:
        self._draw_preview_placeholder(canvas)

