import base64
import os
import re
from pathlib import Path
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk

try:
    from PIL import Image
    from PIL import ImageDraw
    from PIL import ImageFont
    from PIL import UnidentifiedImageError
    from PIL import features
except ImportError:
    Image = None
    ImageDraw = None
    ImageFont = None
    UnidentifiedImageError = OSError
    features = None

from state import AppState
from style_panel import build_square_layout
from style_panel import fit_iso_portrait_page
from style_panel import normalized_square_to_output
from style_panel import FittedPage

DEFAULT_EXPORT_DPI = 150

POSTER_SIZE_OPTIONS = [
    "A0 84.1 x 118.9 cm | 33.1 x 46.8 inches",
    "A1 59.4 x 84.1 cm | 23.4 x 33.1 inches",
    "A2 42 x 59.4 cm | 16.5 x 23.4 inches",
    "A3 29.7 x 42 cm | 11.7 x 16.5 inches",
    "A4 21 x 29.7 cm | 8.3 x 11.7 inches",
    "A5 14.85 x 21.0 cm | 5.8 x 8.3 inches",
    "A6 10.5 x 14.85 cm | 4.1 x 5.8 inches",
    "B0 100.0 x 141.4 cm | 39.4 x 55.7 inches",
    "B1 70.7 x 100.0 cm | 27.8 x 39.4 inches",
    "B2 50.0 x 70.7 cm | 19.7 x 27.8 inches",
    "B3 35.3 x 50.0 cm | 13.9 x 19.7 inches",
    "B4 25.0 x 35.3 cm | 9.8 x 13.9 inches",
    "B5 17.6 x 25.0 cm | 6.9 x 9.8 inches",
    "B6 12.5 x 17.6 cm | 4.9 x 6.9 inches",
]

FILE_FORMAT_OPTIONS = ["PNG", "JPEG", "WebP", "AVIF", "TIFF", "JPEG XL", "SVG"]

FILE_FORMAT_EXTENSIONS = {
    "PNG": ".png",
    "JPEG": ".jpg",
    "WEBP": ".webp",
    "AVIF": ".avif",
    "TIFF": ".tiff",
    "JPEG XL": ".jxl",
    "SVG": ".svg",
}

SVG_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".avif": "image/avif",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
    ".ico": "image/x-icon",
    ".ppm": "image/x-portable-pixmap",
    ".pgm": "image/x-portable-graymap",
}


def _parse_poster_size(value: str) -> tuple[float, float]:
    match = re.search(r"([\d.]+)\s*x\s*([\d.]+)\s*cm\s*\|", value)
    if not match:
        raise ValueError("Poster size selection is invalid")
    return float(match.group(1)), float(match.group(2))


def _poster_size_to_pixels(value: str, dpi: int = DEFAULT_EXPORT_DPI) -> tuple[int, int]:
    width_cm, height_cm = _parse_poster_size(value)
    width_px = max(1, round((width_cm / 2.54) * dpi))
    height_px = max(1, round((height_cm / 2.54) * dpi))
    return width_px, height_px


def _format_key(value: str) -> str:
    return value.strip().upper()


def _format_extension(value: str) -> str:
    return FILE_FORMAT_EXTENSIONS[_format_key(value)]


def _is_export_format_supported(value: str) -> bool:
    key = _format_key(value)
    if key in {"PNG", "JPEG", "WEBP", "TIFF", "SVG"}:
        return True
    if key == "AVIF":
        return bool(features and features.check("avif"))
    if key == "JPEG XL":
        return False
    return False


def _coerce_extension(path: str, extension: str) -> str:
    base, _current_ext = os.path.splitext(path)
    if not base:
        return path + extension
    return base + extension


def _load_preview_font(size: int, bold: bool = False):
    if ImageFont is None:
        return None

    font_candidates = []
    windows_fonts = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    if bold:
        font_candidates.extend([windows_fonts / "seguibd.ttf", windows_fonts / "arialbd.ttf"])
    else:
        font_candidates.extend([windows_fonts / "segoeui.ttf", windows_fonts / "arial.ttf"])

    for candidate in font_candidates:
        try:
            return ImageFont.truetype(str(candidate), size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_centered_text(draw, center_x: float, y: float, text: str, font, fill: str) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    draw.text((center_x - (text_width / 2), y), text, font=font, fill=fill)


def _build_svg_data_uri(path: str) -> str | None:
    file_path = Path(path)
    if not file_path.exists():
        return None
    mime = SVG_MIME_TYPES.get(file_path.suffix.lower())
    if mime is None:
        return None
    data = base64.b64encode(file_path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def _render_poster_image(state: AppState, dpi: int = DEFAULT_EXPORT_DPI):
    if Image is None or ImageDraw is None:
        raise RuntimeError("Pillow is required for raster export")

    output_width, output_height = _poster_size_to_pixels(state.poster_size_var.get(), dpi=dpi)
    fitted_page = fit_iso_portrait_page(output_width, output_height)
    cover_layout = build_square_layout(float(state.margin_ratio_var.get()))
    poster_page = FittedPage(
        x=fitted_page.x,
        y=fitted_page.y,
        width=fitted_page.width,
        height=fitted_page.height,
        short_side=fitted_page.short_side,
    )
    cover_x1, cover_y1, cover_x2, cover_y2 = normalized_square_to_output(cover_layout, poster_page)

    image = Image.new("RGBA", (output_width, output_height), "white")
    draw = ImageDraw.Draw(image)

    draw.rectangle(
        [poster_page.x, poster_page.y, poster_page.x + poster_page.width, poster_page.y + poster_page.height],
        fill="white",
        outline="#bbbbbb",
        width=max(1, round(output_width * 0.0015)),
    )

    cover_path = state.cover_image_path_var.get().strip()
    cover_w = max(1, round(cover_x2 - cover_x1))
    cover_h = max(1, round(cover_y2 - cover_y1))
    if cover_path and Image is not None:
        try:
            with Image.open(cover_path) as raw_image:
                source_w, source_h = raw_image.size
                image_to_paste = raw_image.convert("RGBA")
                resample = Image.Resampling.LANCZOS if source_w == source_h else Image.Resampling.BICUBIC
                image_to_paste = image_to_paste.resize((cover_w, cover_h), resample)
                image.paste(image_to_paste, (round(cover_x1), round(cover_y1)), image_to_paste)
        except (FileNotFoundError, OSError, UnidentifiedImageError):
            cover_path = ""

    if not cover_path:
        draw.rectangle([cover_x1, cover_y1, cover_x2, cover_y2], fill="#dcdcdc", outline="#999999")
        cover_font = _load_preview_font(max(12, round(output_width * 0.02)), bold=False)
        if cover_font is not None:
            bbox = draw.textbbox((0, 0), "Album Cover", font=cover_font)
            text_h = bbox[3] - bbox[1]
            _draw_centered_text(
                draw,
                (cover_x1 + cover_x2) / 2,
                (cover_y1 + cover_y2) / 2 - (text_h / 2),
                "Album Cover",
                cover_font,
                "#555555",
            )

    if state.border_enabled_var.get():
        border_ratio = min(0.05, max(0.0, float(state.border_ratio_var.get())))
        border_width = max(1, round(poster_page.short_side * border_ratio)) if border_ratio > 0 else 0
        if border_width > 0:
            inner_width = min(border_width, round(poster_page.width / 2), round(poster_page.height / 2))
            left = poster_page.x
            top = poster_page.y
            right = poster_page.x + poster_page.width
            bottom = poster_page.y + poster_page.height
            # Draw inset strips so border thickness grows inward only.
            draw.rectangle([left, top, right, top + inner_width], fill="#000000")
            draw.rectangle([left, bottom - inner_width, right, bottom], fill="#000000")
            draw.rectangle([left, top + inner_width, left + inner_width, bottom - inner_width], fill="#000000")
            draw.rectangle([right - inner_width, top + inner_width, right, bottom - inner_width], fill="#000000")

    title_font = _load_preview_font(max(18, round(output_width * 0.035)), bold=True)
    subtitle_font = _load_preview_font(max(12, round(output_width * 0.019)), bold=False)
    if title_font is not None:
        _draw_centered_text(draw, (poster_page.x + poster_page.width / 2), cover_y2 + (poster_page.short_side * 0.11), "Album Title", title_font, "#222222")
    if subtitle_font is not None:
        _draw_centered_text(draw, (poster_page.x + poster_page.width / 2), cover_y2 + (poster_page.short_side * 0.17), "Artist Name • Release Year", subtitle_font, "#666666")

    return image


def _render_poster_svg(state: AppState, dpi: int = DEFAULT_EXPORT_DPI) -> str:
    output_width, output_height = _poster_size_to_pixels(state.poster_size_var.get(), dpi=dpi)
    fitted_page = fit_iso_portrait_page(output_width, output_height)
    cover_layout = build_square_layout(float(state.margin_ratio_var.get()))
    poster_page = FittedPage(
        x=fitted_page.x,
        y=fitted_page.y,
        width=fitted_page.width,
        height=fitted_page.height,
        short_side=fitted_page.short_side,
    )
    cover_x1, cover_y1, cover_x2, cover_y2 = normalized_square_to_output(cover_layout, poster_page)
    cover_uri = _build_svg_data_uri(state.cover_image_path_var.get().strip())

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{output_width}" height="{output_height}" viewBox="0 0 {output_width} {output_height}">',
        f'<rect x="{poster_page.x}" y="{poster_page.y}" width="{poster_page.width}" height="{poster_page.height}" fill="white" stroke="#bbbbbb" stroke-width="2" />',
    ]
    if cover_uri:
        svg_parts.append(
            f'<image x="{cover_x1}" y="{cover_y1}" width="{cover_x2 - cover_x1}" height="{cover_y2 - cover_y1}" href="{cover_uri}" preserveAspectRatio="none" />'
        )
    else:
        svg_parts.append(
            f'<rect x="{cover_x1}" y="{cover_y1}" width="{cover_x2 - cover_x1}" height="{cover_y2 - cover_y1}" fill="#dcdcdc" stroke="#999999" />'
        )
        svg_parts.append(
            f'<text x="{(cover_x1 + cover_x2) / 2}" y="{(cover_y1 + cover_y2) / 2}" text-anchor="middle" dominant-baseline="middle" font-family="Segoe UI, Arial, sans-serif" font-size="{max(12, round(output_width * 0.02))}" fill="#555555">Album Cover</text>'
        )
    if state.border_enabled_var.get():
        border_ratio = min(0.05, max(0.0, float(state.border_ratio_var.get())))
        border_width = max(1, round(poster_page.short_side * border_ratio)) if border_ratio > 0 else 0
        if border_width > 0:
            inset = border_width / 2
            border_x = poster_page.x + inset
            border_y = poster_page.y + inset
            border_w = max(1.0, poster_page.width - border_width)
            border_h = max(1.0, poster_page.height - border_width)
            svg_parts.append(
                f'<rect x="{border_x}" y="{border_y}" width="{border_w}" height="{border_h}" fill="none" stroke="#000000" stroke-width="{border_width}" />'
            )
    svg_parts.append(
        f'<text x="{poster_page.x + (poster_page.width / 2)}" y="{cover_y2 + (poster_page.short_side * 0.11)}" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="{max(18, round(output_width * 0.035))}" font-weight="700" fill="#222222">Album Title</text>'
    )
    svg_parts.append(
        f'<text x="{poster_page.x + (poster_page.width / 2)}" y="{cover_y2 + (poster_page.short_side * 0.17)}" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="{max(12, round(output_width * 0.019))}" fill="#666666">Artist Name • Release Year</text>'
    )
    svg_parts.append("</svg>")
    return "\n".join(svg_parts)


class ExportPanel:
    def __init__(
        self,
        parent: ttk.Frame,
        state: AppState,
        bind_mousewheel_recursive,
    ) -> None:
        self.parent = parent
        self.state = state
        self.bind_mousewheel_recursive = bind_mousewheel_recursive

    def build(self, row: int) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(self.parent, text="5. Layout and export", padding=12)
        frame.grid(row=row, column=0, sticky="ew", pady=8)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Poster size:").grid(
            row=0, column=0, sticky="w", pady=4
        )
        ttk.Combobox(
            frame,
            textvariable=self.state.poster_size_var,
            values=POSTER_SIZE_OPTIONS,
            state="readonly",
        ).grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=4)

        ttk.Label(frame, text="File format:").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Combobox(
            frame,
            textvariable=self.state.export_format_var,
            values=FILE_FORMAT_OPTIONS,
            state="readonly",
        ).grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=4)

        ttk.Button(frame, text="Export to...", command=self._on_export_to).grid(
            row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0)
        )

        self.bind_mousewheel_recursive(frame)
        return frame

    def _on_export_to(self) -> None:
        selected_format = self.state.export_format_var.get().strip() or "PNG"
        extension = _format_extension(selected_format)
        filetypes = [(f"{selected_format} files", f"*{extension}"), ("All files", "*.*")]

        chosen_path = filedialog.asksaveasfilename(
            title="Export poster",
            defaultextension=extension,
            filetypes=filetypes,
        )
        if not chosen_path:
            return

        save_path = _coerce_extension(chosen_path, extension)
        if not _is_export_format_supported(selected_format):
            messagebox.showerror(
                "Export not supported",
                f"{selected_format} export is not available yet.\n\nThe format remains visible in the menu for future support.",
            )
            return

        try:
            self._save_export(save_path, selected_format)
        except Exception as exc:  # pragma: no cover - user-facing error path
            messagebox.showerror("Export failed", f"Could not export poster:\n{exc}")
            return

        messagebox.showinfo("Export complete", f"Poster exported to:\n{save_path}")

    def _save_export(self, save_path: str, selected_format: str) -> None:
        key = _format_key(selected_format)
        if key == "SVG":
            svg_content = _render_poster_svg(self.state)
            Path(save_path).write_text(svg_content, encoding="utf-8")
            return

        if Image is None:
            raise RuntimeError("Pillow is required for raster export")

        poster_image = _render_poster_image(self.state)
        pil_format_map = {
            "PNG": "PNG",
            "JPEG": "JPEG",
            "WEBP": "WEBP",
            "AVIF": "AVIF",
            "TIFF": "TIFF",
        }
        pil_format = pil_format_map.get(key)
        if pil_format is None:
            raise RuntimeError(f"Unsupported export format: {selected_format}")

        save_kwargs = {}
        if key == "JPEG":
            save_kwargs["quality"] = 95
            save_kwargs["subsampling"] = 0
            poster_image = poster_image.convert("RGB")

        poster_image.save(save_path, format=pil_format, **save_kwargs)

