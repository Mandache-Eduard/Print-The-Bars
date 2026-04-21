import math
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

from state import AppState

ISO_PORTRAIT_WIDTH = 1.0
ISO_PORTRAIT_HEIGHT = math.sqrt(2)
ISO_PORTRAIT_RATIO = ISO_PORTRAIT_WIDTH / ISO_PORTRAIT_HEIGHT


@dataclass(frozen=True)
class NormalizedSquareLayout:
    x: float
    y: float
    side: float


@dataclass(frozen=True)
class FittedPage:
    x: float
    y: float
    width: float
    height: float
    short_side: float


def validate_margin_ratio(margin_ratio: float) -> None:
    if not 0.05 <= margin_ratio <= 0.15:
        raise ValueError("margin_ratio must satisfy 0.05 <= margin_ratio <= 0.15")


def validate_border_ratio(border_ratio: float) -> None:
    if not 0.00 <= border_ratio <= 0.05:
        raise ValueError("border_ratio must satisfy 0.00 <= border_ratio <= 0.05")


def build_square_layout(margin_ratio: float) -> NormalizedSquareLayout:
    validate_margin_ratio(margin_ratio)
    side = ISO_PORTRAIT_WIDTH - (2 * margin_ratio)
    return NormalizedSquareLayout(x=margin_ratio, y=margin_ratio, side=side)


def fit_iso_portrait_page(
    output_width: float,
    output_height: float,
    padding: float = 0.0,
) -> FittedPage:
    if output_width <= 0 or output_height <= 0:
        raise ValueError("output size must be positive")
    if padding < 0:
        raise ValueError("padding must be non-negative")

    drawable_width = max(output_width - (2 * padding), 1.0)
    drawable_height = max(output_height - (2 * padding), 1.0)

    fitted_width = min(drawable_width, drawable_height * ISO_PORTRAIT_RATIO)
    fitted_height = fitted_width / ISO_PORTRAIT_RATIO

    x = (output_width - fitted_width) / 2
    y = (output_height - fitted_height) / 2
    return FittedPage(
        x=x,
        y=y,
        width=fitted_width,
        height=fitted_height,
        short_side=fitted_width,
    )


def normalized_square_to_output(
    square: NormalizedSquareLayout,
    page: FittedPage,
) -> tuple[float, float, float, float]:
    x1 = page.x + (square.x * page.short_side)
    y1 = page.y + (square.y * page.short_side)
    side_px = square.side * page.short_side
    x2 = x1 + side_px
    y2 = y1 + side_px
    return x1, y1, x2, y2


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
        self.border_ratio_value_var = tk.StringVar(value=f"{self.state.border_ratio_var.get():.3f}")
        self.margin_ratio_value_var = tk.StringVar(value=f"{self.state.margin_ratio_var.get():.2f}")
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
            from_=0.00,
            to=0.05,
            variable=self.state.border_ratio_var,
            orient="horizontal",
            command=self._on_border_ratio_change,
        ).grid(row=0, column=0, sticky="ew")

        ttk.Label(
            self.border_controls_frame,
            textvariable=self.border_ratio_value_var,
            width=6,
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

        ttk.Label(frame, text="Cover margin ratio").grid(row=4, column=0, sticky="w", pady=4)
        margin_controls = ttk.Frame(frame)
        margin_controls.grid(row=4, column=1, sticky="ew", padx=(10, 0), pady=4)
        margin_controls.columnconfigure(0, weight=1)

        ttk.Scale(
            margin_controls,
            from_=0.05,
            to=0.15,
            variable=self.state.margin_ratio_var,
            orient="horizontal",
            command=self._on_margin_ratio_change,
        ).grid(row=0, column=0, sticky="ew")

        ttk.Label(
            margin_controls,
            textvariable=self.margin_ratio_value_var,
            width=5,
        ).grid(row=0, column=1, padx=(8, 0))

        ttk.Checkbutton(
            frame,
            text="Album cover color gradient",
            variable=self.state.gradient_var,
            command=self._toggle_gradient_palette,
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(10, 4))

        self.gradient_palette_frame = ttk.Frame(frame)
        self.gradient_palette_frame.grid(
            row=6, column=0, columnspan=2, sticky="w", padx=(24, 0), pady=(0, 8)
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
        self._on_border_ratio_change(str(self.state.border_ratio_var.get()))
        self._on_margin_ratio_change(str(self.state.margin_ratio_var.get()))
        self._toggle_gradient_palette()
        self.bind_mousewheel_recursive(frame)
        return frame

    def _on_margin_ratio_change(self, value: str) -> None:
        try:
            ratio = round(min(0.15, max(0.05, float(value))), 2)
            validate_margin_ratio(ratio)
            self.state.margin_ratio_var.set(ratio)
            normalized_square = build_square_layout(ratio)
            self.margin_ratio_value_var.set(f"{normalized_square.x:.2f}")
        except (ValueError, tk.TclError):
            fallback = 0.12
            self.state.margin_ratio_var.set(fallback)
            self.margin_ratio_value_var.set(f"{fallback:.2f}")

    def _on_border_ratio_change(self, value: str) -> None:
        try:
            ratio = round(min(0.05, max(0.00, float(value))), 3)
            validate_border_ratio(ratio)
            self.state.border_ratio_var.set(ratio)
            self.border_ratio_value_var.set(f"{ratio:.3f}")
        except (ValueError, tk.TclError):
            fallback = 0.01
            self.state.border_ratio_var.set(fallback)
            self.border_ratio_value_var.set(f"{fallback:.3f}")

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


