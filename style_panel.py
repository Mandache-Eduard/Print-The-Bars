import tkinter as tk
from tkinter import ttk

from state import AppState


class StylePanel:
    def __init__(
        self,
        parent: ttk.Frame,
        state: AppState,
        bind_mousewheel_recursive,
    ) -> None:
        self.parent = parent
        self.state = state
        self.bind_mousewheel_recursive = bind_mousewheel_recursive
        self.border_controls_frame: ttk.Frame | None = None
        self.gradient_palette_frame: ttk.Frame | None = None

    def build(self, row: int) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(self.parent, text="3. Visual style", padding=12)
        frame.grid(row=row, column=0, sticky="ew", pady=8)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Theme").grid(row=0, column=0, sticky="w", pady=4)
        ttk.Combobox(
            frame,
            textvariable=self.state.theme_var,
            values=["Light", "Dark"],
            state="readonly",
        ).grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=4)

        ttk.Checkbutton(
            frame,
            text="Borders",
            variable=self.state.border_enabled_var,
            command=self._toggle_border_controls,
        ).grid(row=1, column=0, sticky="w", pady=6)

        self.border_controls_frame = ttk.Frame(frame)
        self.border_controls_frame.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=6)
        self.border_controls_frame.columnconfigure(0, weight=1)

        ttk.Scale(
            self.border_controls_frame,
            from_=0,
            to=100,
            variable=self.state.border_size_var,
            orient="horizontal",
        ).grid(row=0, column=0, sticky="ew")

        ttk.Label(
            self.border_controls_frame,
            textvariable=self.state.border_size_var,
            width=4,
        ).grid(row=0, column=1, padx=(8, 0))

        ttk.Checkbutton(
            frame,
            text="Monochrome cover",
            variable=self.state.monochrome_var,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=6)

        ttk.Label(frame, text="Font").grid(row=3, column=0, sticky="w", pady=4)
        ttk.Combobox(
            frame,
            textvariable=self.state.font_var,
            values=[
                "Helvetica",
                "Arial",
                "Times New Roman",
                "Georgia",
                "Courier New",
                "Verdana",
            ],
            state="readonly",
        ).grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=4)

        ttk.Checkbutton(
            frame,
            text="Album cover color gradient",
            variable=self.state.gradient_var,
            command=self._toggle_gradient_palette,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 4))

        self.gradient_palette_frame = ttk.Frame(frame)
        self.gradient_palette_frame.grid(
            row=5, column=0, columnspan=2, sticky="w", padx=(24, 0), pady=(0, 8)
        )

        for index, color in enumerate(["#2c3e50", "#8e44ad", "#c0392b", "#f39c12", "#ecf0f1"]):
            swatch = tk.Label(
                self.gradient_palette_frame,
                bg=color,
                width=5,
                height=2,
                relief="solid",
                bd=1,
            )
            swatch.grid(row=0, column=index, padx=3)

        self._toggle_border_controls()
        self._toggle_gradient_palette()
        self.bind_mousewheel_recursive(frame)
        return frame

    def _toggle_border_controls(self) -> None:
        if self.border_controls_frame is None:
            return
        state = "normal" if self.state.border_enabled_var.get() else "disabled"
        for child in self.border_controls_frame.winfo_children():
            child.configure({"state": state})

    def _toggle_gradient_palette(self) -> None:
        if self.gradient_palette_frame is None:
            return
        if self.state.gradient_var.get():
            self.gradient_palette_frame.grid()
        else:
            self.gradient_palette_frame.grid_remove()


