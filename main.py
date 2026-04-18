import tkinter as tk
from tkinter import ttk


class AlbumPosterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Album Poster Builder")
        self.root.geometry("1280x780")
        self.root.minsize(980, 650)

        self._init_variables()
        self._configure_root()
        self._build_layout()
        self._build_menu_panel()
        self._build_preview_panel()

    def _init_variables(self) -> None:
        self.album_link_var = tk.StringVar()
        self.border_enabled_var = tk.BooleanVar(value=False)
        self.border_size_var = tk.IntVar(value=12)
        self.monochrome_var = tk.BooleanVar(value=False)
        self.theme_var = tk.StringVar(value="Light")
        self.font_var = tk.StringVar(value="Helvetica")
        self.show_genre_var = tk.BooleanVar(value=True)
        self.show_tracklist_var = tk.BooleanVar(value=True)
        self.tracklist_numbering_var = tk.StringVar(value="Standard numbers")
        self.show_features_var = tk.BooleanVar(value=False)
        self.show_certifications_var = tk.BooleanVar(value=False)
        self.certifications_link_var = tk.StringVar()
        self.gradient_var = tk.BooleanVar(value=False)
        self.qr_enabled_var = tk.BooleanVar(value=False)
        self.qr_link_var = tk.StringVar()
        self.spotify_enabled_var = tk.BooleanVar(value=False)
        self.spotify_link_var = tk.StringVar()
        self.message_var = tk.StringVar(value="Custom")
        self.custom_message_var = tk.StringVar()
        self.poster_size_var = tk.StringVar(
            value="A3 29.7 x 42 cm | 11.7 x 16.5 inches"
        )

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
        title = ttk.Label(
            self.menu_frame,
            text="Controls",
            font=("Segoe UI", 18, "bold")
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 12))

        self.menu_canvas = tk.Canvas(self.menu_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            self.menu_frame,
            orient="vertical",
            command=self.menu_canvas.yview
        )
        self.scrollable_menu = ttk.Frame(self.menu_canvas)

        self.scrollable_menu.bind(
            "<Configure>",
            lambda event: self.menu_canvas.configure(
                scrollregion=self.menu_canvas.bbox("all")
            )
        )

        self.menu_canvas.bind(
            "<Configure>",
            lambda event: self.menu_canvas.itemconfigure(
                self.menu_window,
                width=event.width
            )
        )

        self.menu_window = self.menu_canvas.create_window(
            (0, 0),
            window=self.scrollable_menu,
            anchor="nw"
        )
        self.menu_canvas.configure(yscrollcommand=scrollbar.set)

        self.menu_canvas.grid(row=1, column=0, sticky="nsew")
        scrollbar.grid(row=1, column=1, sticky="ns")

        self._bind_mousewheel(self.menu_frame)
        self._bind_mousewheel(self.menu_canvas)
        self._bind_mousewheel_recursive(self.scrollable_menu)

        row = 0
        self._create_album_source_section(row)
        row += 1
        self._create_poster_content_section(row)
        row += 1
        self._create_visual_style_section(row)
        row += 1
        self._create_codes_section(row)
        row += 1
        self._create_layout_section(row)

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

    def _create_section_frame(self, title_text: str, row: int) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(self.scrollable_menu, text=title_text, padding=12)
        frame.grid(row=row, column=0, sticky="ew", pady=8)
        frame.columnconfigure(1, weight=1)
        self.scrollable_menu.columnconfigure(0, weight=1)
        return frame

    def _create_album_source_section(self, row: int) -> None:
        frame = self._create_section_frame("1. Album source", row)

        ttk.Button(frame, text="Upload cover").grid(
            row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8)
        )

        ttk.Label(frame, text="Album link (optional)").grid(
            row=1, column=0, sticky="w", pady=4
        )
        ttk.Entry(frame, textvariable=self.album_link_var).grid(
            row=1, column=1, sticky="ew", padx=(10, 0), pady=4
        )

    def _create_poster_content_section(self, row: int) -> None:
        frame = self._create_section_frame("2. Poster content", row)

        ttk.Checkbutton(
            frame,
            text="Show music genre",
            variable=self.show_genre_var
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=3)

        self.tracklist_check = ttk.Checkbutton(
            frame,
            text="Show tracklist",
            variable=self.show_tracklist_var,
            command=self._toggle_tracklist_options
        )
        self.tracklist_check.grid(row=1, column=0, columnspan=2, sticky="w", pady=3)

        self.tracklist_options_frame = ttk.Frame(frame)
        self.tracklist_options_frame.grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=(24, 0), pady=(0, 6)
        )
        self.tracklist_options_frame.columnconfigure(1, weight=1)

        ttk.Label(self.tracklist_options_frame, text="Track numbering").grid(
            row=0, column=0, sticky="w", pady=2
        )
        ttk.Combobox(
            self.tracklist_options_frame,
            textvariable=self.tracklist_numbering_var,
            values=[
                "Standard numbers",
                "Zero-padded numbers",
                "Roman numerals"
            ],
            state="readonly"
        ).grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=2)

        ttk.Checkbutton(
            frame,
            text="Show featured artists",
            variable=self.show_features_var
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=3)

        ttk.Checkbutton(
            frame,
            text="Certifications",
            variable=self.show_certifications_var,
            command=self._toggle_certifications_entry
        ).grid(row=4, column=0, sticky="w", pady=3)
        self.certifications_entry = ttk.Entry(
            frame,
            textvariable=self.certifications_link_var
        )
        self.certifications_entry.grid(
            row=4, column=1, sticky="ew", padx=(10, 0), pady=3
        )

        ttk.Label(frame, text="Funny message").grid(
            row=5, column=0, sticky="w", pady=(10, 4)
        )
        message_options = [
            "Custom",
            "certified hood classic",
            "safe aux pick",
            "in your feelings",
            "main character energy",
            "no skips"
        ]
        message_menu = ttk.Combobox(
            frame,
            textvariable=self.message_var,
            values=message_options,
            state="readonly"
        )
        message_menu.grid(row=5, column=1, sticky="ew", padx=(10, 0), pady=(10, 4))
        message_menu.bind(
            "<<ComboboxSelected>>",
            lambda event: self._toggle_custom_message()
        )

        self.custom_message_label = ttk.Label(frame, text="Custom text")
        self.custom_message_entry = ttk.Entry(
            frame,
            textvariable=self.custom_message_var
        )

        self._toggle_tracklist_options()
        self._toggle_certifications_entry()
        self._toggle_custom_message()

        self._bind_mousewheel_recursive(frame)

    def _create_visual_style_section(self, row: int) -> None:
        frame = self._create_section_frame("3. Visual style", row)

        ttk.Label(frame, text="Theme").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Combobox(
            frame,
            textvariable=self.theme_var,
            values=["Light", "Dark"],
            state="readonly"
        ).grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=4)

        ttk.Checkbutton(
            frame,
            text="Borders",
            variable=self.border_enabled_var,
            command=self._toggle_border_controls
        ).grid(row=1, column=0, sticky="w", pady=6)

        self.border_controls_frame = ttk.Frame(frame)
        self.border_controls_frame.grid(
            row=1, column=1, sticky="ew", padx=(10, 0), pady=6
        )
        self.border_controls_frame.columnconfigure(0, weight=1)

        self.border_slider = ttk.Scale(
            self.border_controls_frame,
            from_=0,
            to=100,
            variable=self.border_size_var,
            orient="horizontal"
        )
        self.border_slider.grid(row=0, column=0, sticky="ew")
        self.border_value_label = ttk.Label(
            self.border_controls_frame,
            textvariable=self.border_size_var,
            width=4
        )
        self.border_value_label.grid(row=0, column=1, padx=(8, 0))

        ttk.Checkbutton(
            frame,
            text="Monochrome cover",
            variable=self.monochrome_var
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=6)

        ttk.Label(frame, text="Font").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Combobox(
            frame,
            textvariable=self.font_var,
            values=[
                "Helvetica",
                "Arial",
                "Times New Roman",
                "Georgia",
                "Courier New",
                "Verdana"
            ],
            state="readonly"
        ).grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=4)

        ttk.Checkbutton(
            frame,
            text="Album cover color gradient",
            variable=self.gradient_var,
            command=self._toggle_gradient_palette
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 4))

        self.gradient_palette_frame = ttk.Frame(frame)
        self.gradient_palette_frame.grid(
            row=5, column=0, columnspan=2, sticky="w", padx=(24, 0), pady=(0, 8)
        )
        palette_colors = ["#2c3e50", "#8e44ad", "#c0392b", "#f39c12", "#ecf0f1"]
        for index, color in enumerate(palette_colors):
            swatch = tk.Label(
                self.gradient_palette_frame,
                bg=color,
                width=5,
                height=2,
                relief="solid",
                bd=1
            )
            swatch.grid(row=0, column=index, padx=3)

        self._toggle_border_controls()
        self._toggle_gradient_palette()

        self._bind_mousewheel_recursive(frame)

    def _create_codes_section(self, row: int) -> None:
        frame = self._create_section_frame("4. Codes and links", row)

        ttk.Checkbutton(
            frame,
            text="QR code",
            variable=self.qr_enabled_var,
            command=self._toggle_qr_entry
        ).grid(row=0, column=0, sticky="w", pady=4)
        self.qr_entry = ttk.Entry(frame, textvariable=self.qr_link_var)
        self.qr_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=4)

        ttk.Checkbutton(
            frame,
            text="Spotify code",
            variable=self.spotify_enabled_var,
            command=self._toggle_spotify_entry
        ).grid(row=1, column=0, sticky="w", pady=4)
        self.spotify_entry = ttk.Entry(frame, textvariable=self.spotify_link_var)
        self.spotify_entry.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=4)

        self._toggle_qr_entry()
        self._toggle_spotify_entry()

        self._bind_mousewheel_recursive(self.scrollable_menu)

    def _create_layout_section(self, row: int) -> None:
        frame = self._create_section_frame("5. Layout and export", row)

        ttk.Label(frame, text="Poster size / format").grid(
            row=0, column=0, sticky="w", pady=4
        )
        size_options = [
            "A0 84.1 x 118.9 cm | 33.1 x 46.8 inches",
            "A1 59.4 x 84.1 cm | 23.4 x 33.1 inches",
            "A2 42 x 59.4 cm | 16.5 x 23.4 inches",
            "A3 29.7 x 42 cm | 11.7 x 16.5 inches",
            "A4 21 x 29.7 cm | 8.3 x 11.7 inches",
            "A5 14.85 x 21.0 cm | 5.8 x 8.3 inches",
            "A6 10.5 x 14.85 cm | 4.1 x 5.8 inches"
        ]
        ttk.Combobox(
            frame,
            textvariable=self.poster_size_var,
            values=size_options,
            state="readonly"
        ).grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=4)

    def _toggle_border_controls(self) -> None:
        state = "normal" if self.border_enabled_var.get() else "disabled"
        for child in self.border_controls_frame.winfo_children():
            child.configure(state=state)

    def _toggle_tracklist_options(self) -> None:
        if self.show_tracklist_var.get():
            self.tracklist_options_frame.grid()
        else:
            self.tracklist_options_frame.grid_remove()

    def _toggle_certifications_entry(self) -> None:
        self.certifications_entry.configure(
            state="normal" if self.show_certifications_var.get() else "disabled"
        )

    def _toggle_gradient_palette(self) -> None:
        if self.gradient_var.get():
            self.gradient_palette_frame.grid()
        else:
            self.gradient_palette_frame.grid_remove()

    def _toggle_qr_entry(self) -> None:
        self.qr_entry.configure(
            state="normal" if self.qr_enabled_var.get() else "disabled"
        )

    def _toggle_spotify_entry(self) -> None:
        self.spotify_entry.configure(
            state="normal" if self.spotify_enabled_var.get() else "disabled"
        )

    def _toggle_custom_message(self) -> None:
        show_custom = self.message_var.get() == "Custom"
        if show_custom:
            self.custom_message_label.grid(row=6, column=0, sticky="w", pady=4)
            self.custom_message_entry.grid(
                row=6, column=1, sticky="ew", padx=(10, 0), pady=4
            )
        else:
            self.custom_message_label.grid_remove()
            self.custom_message_entry.grid_remove()

    def _build_preview_panel(self) -> None:
        title = ttk.Label(
            self.preview_frame,
            text="Poster Preview",
            font=("Segoe UI", 18, "bold")
        )
        title.grid(row=0, column=0, sticky="w", pady=(0, 16))

        preview_canvas = tk.Canvas(
            self.preview_frame,
            bg="#f4f4f4",
            highlightthickness=1,
            highlightbackground="#cfcfcf"
        )
        preview_canvas.grid(row=1, column=0, sticky="nsew")

        self._draw_preview_placeholder(preview_canvas)
        preview_canvas.bind(
            "<Configure>",
            lambda event: self._redraw_preview(preview_canvas)
        )

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
            width=2
        )

        canvas.create_text(
            width / 2,
            80,
            text="Your poster preview will appear here",
            font=("Segoe UI", 16, "bold"),
            fill="#333333"
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
            outline="#999999"
        )
        canvas.create_text(
            width / 2,
            (cover_y1 + cover_y2) / 2,
            text="Album Cover",
            font=("Segoe UI", 14),
            fill="#555555"
        )

        canvas.create_text(
            width / 2,
            cover_y2 + 55,
            text="Album Title",
            font=("Segoe UI", 22, "bold"),
            fill="#222222"
        )
        canvas.create_text(
            width / 2,
            cover_y2 + 90,
            text="Artist Name • Release Year",
            font=("Segoe UI", 13),
            fill="#666666"
        )

    def _redraw_preview(self, canvas: tk.Canvas) -> None:
        self._draw_preview_placeholder(canvas)


def main() -> None:
    root = tk.Tk()
    app = AlbumPosterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
