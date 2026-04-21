import base64
import html
import io
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
    from PIL import ImageOps
    from PIL import UnidentifiedImageError
    from PIL import features
except ImportError:
    Image = None
    ImageDraw = None
    ImageFont = None
    ImageOps = None
    UnidentifiedImageError = OSError
    features = None

from state import AppState
from style_panel import build_square_layout
from style_panel import fit_iso_portrait_page
from style_panel import normalized_square_to_output
from style_panel import FittedPage

DEFAULT_EXPORT_DPI = 150
BASE_LAYOUT_RATIO_STEPS = [
    (0.0500, 0.0273, 3, 0.0295, 0.0205, 2, 0.0227, 0.0159, 0.012),
    (0.0455, 0.0250, 3, 0.0273, 0.0182, 2, 0.0205, 0.0136, 0.010),
    (0.0409, 0.0227, 2, 0.0250, 0.0182, 2, 0.0182, 0.0136, 0.008),
    (0.0364, 0.0205, 2, 0.0227, 0.0159, 1, 0.0159, 0.0114, 0.006),
    (0.0318, 0.0182, 2, 0.0205, 0.0159, 1, 0.0136, 0.0114, 0.005),
]
PRIMARY_FONT_RATIOS = {
    "title": 0.0500,
    "subtitle": 0.0295,
    "track": 0.0227,
}

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


def _size_from_width_ratio(poster_width: float, ratio: float) -> int:
    return max(1, round(poster_width * ratio))


def _build_scaled_layout_steps(poster_width: float):
    scaled_steps = []
    for (
        title_pref,
        title_min,
        title_max_lines,
        subtitle_pref,
        subtitle_min,
        subtitle_max_lines,
        track_pref,
        track_min,
        gap_ratio,
    ) in BASE_LAYOUT_RATIO_STEPS:
        scaled_steps.append(
            (
                _size_from_width_ratio(poster_width, title_pref),
                _size_from_width_ratio(poster_width, title_min),
                title_max_lines,
                _size_from_width_ratio(poster_width, subtitle_pref),
                _size_from_width_ratio(poster_width, subtitle_min),
                subtitle_max_lines,
                _size_from_width_ratio(poster_width, track_pref),
                _size_from_width_ratio(poster_width, track_min),
                gap_ratio,
            )
        )
    return scaled_steps


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


def _svg_escape(value: str) -> str:
    return html.escape(value, quote=True)


def _get_theme_colors(state: AppState) -> tuple[str, str]:
    if state.theme_var.get() == "Dark":
        return "#111111", "#F5F4EF"
    return "#F7F7F2", "#111111"


def _to_roman(number: int) -> str:
    numerals = [
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    ]
    result: list[str] = []
    remainder = max(1, number)
    for value, symbol in numerals:
        while remainder >= value:
            result.append(symbol)
            remainder -= value
    return "".join(result)


def _join_feature_names(artists: list[str]) -> str:
    if not artists:
        return ""
    if len(artists) == 1:
        return artists[0]
    if len(artists) == 2:
        return f"{artists[0]} & {artists[1]}"
    return f"{', '.join(artists[:-1])} & {artists[-1]}"


def _format_release_date(state: AppState, release_date: str) -> str:
    if not release_date:
        return ""

    match = re.match(r"^(\d{4})(?:[-/.](\d{1,2})(?:[-/.](\d{1,2}))?)?$", release_date)
    if not match:
        return release_date

    year_text, month_text, day_text = match.groups()
    month = int(month_text) if month_text is not None else None
    day = int(day_text) if day_text is not None else None

    if month is None:
        return year_text
    if month < 1 or month > 12:
        return release_date

    month_names = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    month_name = month_names[month - 1]
    month_two = f"{month:02d}"
    selected = state.release_date_format_var.get()

    if day is None:
        if selected in {"DD Month YYYY", "Month DD, YYYY"}:
            return f"{month_name} {year_text}"
        return f"{month_two}/{year_text}"

    if day < 1 or day > 31:
        return release_date

    day_two = f"{day:02d}"
    if selected == "DD/MM/YYYY":
        return f"{day_two}/{month_two}/{year_text}"
    if selected == "DD-MM-YYYY":
        return f"{day_two}-{month_two}-{year_text}"
    if selected == "DD.MM.YYYY":
        return f"{day_two}.{month_two}.{year_text}"
    if selected == "DD Month YYYY":
        return f"{day_two} {month_name} {year_text}"
    if selected == "MM/DD/YYYY":
        return f"{month_two}/{day_two}/{year_text}"
    if selected == "MM-DD-YYYY":
        return f"{month_two}-{day_two}-{year_text}"
    if selected == "MM.DD.YYYY":
        return f"{month_two}.{day_two}.{year_text}"
    if selected == "Month DD, YYYY":
        return f"{month_name} {day_two}, {year_text}"
    return f"{day_two}/{month_two}/{year_text}"


def _format_tracklist(state: AppState, tracks: list[object]) -> list[str]:
    numbering = state.tracklist_numbering_var.get()
    if not tracks:
        return []

    display_tracks: list[str] = []
    for entry in tracks:
        if isinstance(entry, dict):
            title = str(entry.get("title") or "").strip()
            if not title:
                continue
            features = entry.get("featured_artists")
            feature_names = [
                str(name).strip()
                for name in features
                if isinstance(name, str) and name.strip()
            ] if isinstance(features, list) else []
            if state.show_features_var.get() and feature_names:
                title = f"{title} ft. {_join_feature_names(feature_names)}"
            display_tracks.append(title)
        elif isinstance(entry, str) and entry.strip():
            display_tracks.append(entry.strip())

    if not display_tracks:
        return []
    count = len(display_tracks)
    if numbering == "Zero-padded numbers":
        width = max(2, len(str(count)))
        return [f"{index:0{width}d}. {title}" for index, title in enumerate(display_tracks, start=1)]
    if numbering == "Roman numerals":
        return [f"{_to_roman(index)}. {title}" for index, title in enumerate(display_tracks, start=1)]
    return [f"{index}. {title}" for index, title in enumerate(display_tracks, start=1)]


def _get_export_text_data(state: AppState) -> tuple[str, str, list[str]]:
    metadata = state.album_metadata if isinstance(state.album_metadata, dict) else {}
    title = str(metadata.get("title") or "").strip() or "Album Title"
    artist = str(metadata.get("artist") or "").strip() or "Artist Name"
    release_date = _format_release_date(state, str(metadata.get("release_date") or "").strip())

    if state.show_release_date_var.get() and release_date:
        subtitle = f"{artist} • {release_date}"
    elif artist == "Artist Name":
        subtitle = "Artist Name • Release Year"
    else:
        subtitle = artist

    tracks = metadata.get("tracklist")
    normalized_tracks: list[object] = []
    if state.show_tracklist_var.get() and isinstance(tracks, list):
        normalized_tracks = [
            track
            for track in tracks
            if (
                isinstance(track, str)
                and track.strip()
                or isinstance(track, dict)
                and isinstance(track.get("title"), str)
                and str(track.get("title")).strip()
            )
        ]
    return title, subtitle, _format_tracklist(state, normalized_tracks)


def _measure_text_width(draw: ImageDraw.ImageDraw, text: str, font) -> float:
    bbox = draw.textbbox((0, 0), text, font=font)
    return float(bbox[2] - bbox[0])


def _line_height(draw: ImageDraw.ImageDraw, font) -> int:
    if hasattr(font, "getmetrics"):
        try:
            ascent, descent = font.getmetrics()
            return int(ascent + descent + 2)
        except (TypeError, ValueError, OSError):
            pass
    bbox = draw.textbbox((0, 0), "Ag", font=font)
    return int((bbox[3] - bbox[1]) + 2)


def _wrap_text_to_width(draw: ImageDraw.ImageDraw, text: str, font, max_width: float) -> list[str]:
    if not text:
        return [""]
    if max_width <= 1:
        return [text]

    wrapped: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            wrapped.append("")
            continue
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if _measure_text_width(draw, candidate, font) <= max_width:
                current = candidate
            else:
                wrapped.append(current)
                current = word
        wrapped.append(current)
    return wrapped


def _truncate_to_width(draw: ImageDraw.ImageDraw, text: str, font, max_width: float) -> str:
    if _measure_text_width(draw, text, font) <= max_width:
        return text
    ellipsis = "..."
    if _measure_text_width(draw, ellipsis, font) > max_width:
        return ""
    candidate = text
    while candidate and _measure_text_width(draw, f"{candidate}{ellipsis}", font) > max_width:
        candidate = candidate[:-1]
    return f"{candidate.rstrip()}{ellipsis}"


def _fit_text_block(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: float,
    max_height: float,
    preferred_size: int,
    min_size: int,
    max_lines: int,
    bold: bool = False,
):
    for size in range(preferred_size, min_size - 1, -1):
        font = _load_preview_font(size, bold=bold)
        lines = _wrap_text_to_width(draw, text, font, max_width)
        if max_lines > 0 and len(lines) > max_lines:
            continue
        lh = _line_height(draw, font)
        if (lh * len(lines)) <= max_height:
            return font, lines, lh

    font = _load_preview_font(min_size, bold=bold)
    lh = _line_height(draw, font)
    lines = _wrap_text_to_width(draw, text, font, max_width)
    if max_lines > 0:
        lines = lines[:max_lines]
    max_height_lines = max(1, int(max_height // lh))
    lines = lines[:max_height_lines]
    if lines and _measure_text_width(draw, lines[-1], font) > max_width:
        lines[-1] = _truncate_to_width(draw, lines[-1], font, max_width)
    return font, lines, lh


def _build_track_blocks(draw: ImageDraw.ImageDraw, tracks: list[str], font, column_width: float) -> list[list[str]]:
    blocks: list[list[str]] = []
    for track in tracks:
        wrapped = _wrap_text_to_width(draw, track, font, column_width)
        if not wrapped:
            continue
        block = [wrapped[0]]
        for segment in wrapped[1:]:
            block.append(f"    {segment}")
        blocks.append(block)
    return blocks


def _layout_track_blocks_into_columns(
    blocks: list[list[str]],
    max_lines_per_column: int,
    column_count: int,
) -> list[list[str]] | None:
    columns: list[list[str]] = [[] for _ in range(column_count)]
    column_index = 0
    used_lines = 0

    for block in blocks:
        remaining = list(block)
        while remaining:
            if column_index >= column_count:
                return None
            remaining_lines = max_lines_per_column - used_lines
            if remaining_lines <= 0:
                column_index += 1
                used_lines = 0
                continue
            if len(remaining) <= remaining_lines:
                columns[column_index].extend(remaining)
                used_lines += len(remaining)
                remaining = []
                continue
            if used_lines == 0 or len(remaining) > max_lines_per_column:
                take = max(1, remaining_lines)
                columns[column_index].extend(remaining[:take])
                remaining = remaining[take:]
                used_lines += take
                if remaining:
                    column_index += 1
                    used_lines = 0
            else:
                column_index += 1
                used_lines = 0

    while columns and not columns[-1]:
        columns.pop()
    return columns if columns else None


def _fit_tracklist_lines(
    draw: ImageDraw.ImageDraw,
    tracks: list[str],
    max_width: float,
    max_height: float,
    preferred_size: int,
    min_size: int,
):
    effective_width = max(1.0, max_width)
    effective_height = max(1.0, max_height)

    for size in range(preferred_size, min_size - 1, -1):
        font = _load_preview_font(size, bold=False)
        lh = _line_height(draw, font) - 1
        max_lines = max(1, int(effective_height // max(1, lh)))
        column_gap = max(6.0, min(14.0, effective_width * 0.024))
        sample = max(62.0, _measure_text_width(draw, "88. Very Long Track Name ft. Guest", font) * 0.38)
        max_columns_by_width = max(1, int((effective_width + column_gap) // (sample + column_gap)))
        max_columns_by_width = min(8, max_columns_by_width)

        for column_count in range(max_columns_by_width, 0, -1):
            column_width = (effective_width - ((column_count - 1) * column_gap)) / column_count
            if column_width < 58.0:
                continue
            blocks = _build_track_blocks(draw, tracks, font, column_width)
            total_block_lines = sum(len(block) for block in blocks)
            if total_block_lines > (max_lines * column_count):
                continue
            columns = _layout_track_blocks_into_columns(blocks, max_lines, column_count)
            if columns is not None:
                total_lines = sum(len(col) for col in columns)
                if total_lines == total_block_lines and total_lines > 0:
                    return font, columns, lh, column_width, column_gap, True

    font = _load_preview_font(min_size, bold=False)
    lh = _line_height(draw, font) - 1
    max_lines = max(1, int(effective_height // max(1, lh)))
    column_gap = max(5.0, min(10.0, effective_width * 0.02))
    min_column_width = 60.0
    max_columns_by_width = max(1, int((effective_width + column_gap) // (min_column_width + column_gap)))
    column_count = min(8, max_columns_by_width)
    column_width = (effective_width - ((column_count - 1) * column_gap)) / column_count
    blocks = _build_track_blocks(draw, tracks, font, column_width)

    columns = [[] for _ in range(column_count)]
    flattened_lines: list[str] = []
    for block in blocks:
        flattened_lines.extend(block)
    lines_capacity = max_lines * max(1, column_count)
    if len(flattened_lines) > lines_capacity:
        flattened_lines = flattened_lines[:lines_capacity]
        if flattened_lines:
            flattened_lines[-1] = _truncate_to_width(draw, flattened_lines[-1], font, column_width)
    for index in range(column_count):
        start = index * max_lines
        end = start + max_lines
        segment = flattened_lines[start:end]
        if not segment:
            break
        columns[index] = segment
    columns = [column for column in columns if column]
    return font, columns, lh, column_width, column_gap, False


def _fit_export_text_layout(
    draw: ImageDraw.ImageDraw,
    title_text: str,
    subtitle_text: str,
    tracks: list[str],
    text_width: float,
    text_height: float,
    poster_width: float,
):
    layout_steps = _build_scaled_layout_steps(poster_width)

    fallback_layout = None
    for (
        title_pref,
        title_min,
        title_max_lines,
        subtitle_pref,
        subtitle_min,
        subtitle_max_lines,
        track_pref,
        track_min,
        gap_ratio,
    ) in layout_steps:
        block_gap = max(2.0, poster_width * gap_ratio)
        title_max_height = max(20.0, text_height * 0.28)
        title_font, title_lines, title_line_height = _fit_text_block(
            draw,
            title_text,
            text_width,
            title_max_height,
            preferred_size=title_pref,
            min_size=title_min,
            max_lines=title_max_lines,
            bold=True,
        )
        title_height = len(title_lines) * title_line_height

        remaining_for_subtitle = max(12.0, text_height - title_height - block_gap)
        subtitle_max_height = max(14.0, remaining_for_subtitle * 0.25)
        subtitle_font, subtitle_lines, subtitle_line_height = _fit_text_block(
            draw,
            subtitle_text,
            text_width,
            subtitle_max_height,
            preferred_size=subtitle_pref,
            min_size=subtitle_min,
            max_lines=subtitle_max_lines,
            bold=False,
        )
        subtitle_height = len(subtitle_lines) * subtitle_line_height

        used_height = title_height + subtitle_height + (2 * block_gap)
        track_space = max(0.0, text_height - used_height)
        track_font = None
        track_columns: list[list[str]] = []
        track_line_height = 0
        column_width = text_width
        column_gap = 0.0
        tracks_complete = True

        if tracks and track_space > 6.0:
            (
                track_font,
                track_columns,
                track_line_height,
                column_width,
                column_gap,
                tracks_complete,
            ) = _fit_tracklist_lines(
                draw,
                tracks,
                text_width,
                track_space,
                preferred_size=track_pref,
                min_size=track_min,
            )
        elif tracks:
            tracks_complete = False

        candidate_layout = (
            title_font,
            title_lines,
            title_line_height,
            subtitle_font,
            subtitle_lines,
            subtitle_line_height,
            block_gap,
            track_font,
            track_columns,
            track_line_height,
            column_width,
            column_gap,
            tracks_complete,
        )
        if fallback_layout is None:
            fallback_layout = candidate_layout
        if tracks_complete or not tracks:
            return candidate_layout

    return fallback_layout


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
    poster_bg, poster_fg = _get_theme_colors(state)

    draw.rectangle(
        [poster_page.x, poster_page.y, poster_page.x + poster_page.width, poster_page.y + poster_page.height],
        fill=poster_bg,
        outline=poster_fg if state.border_enabled_var.get() else None,
        width=max(1, round(output_width * 0.0015)) if state.border_enabled_var.get() else 0,
    )

    cover_path = state.cover_image_path_var.get().strip()
    cover_w = max(1, round(cover_x2 - cover_x1))
    cover_h = max(1, round(cover_y2 - cover_y1))
    if cover_path and Image is not None:
        try:
            with Image.open(cover_path) as raw_image:
                source_w, source_h = raw_image.size
                image_to_paste = raw_image.convert("RGB")
                if state.monochrome_var.get() and ImageOps is not None:
                    image_to_paste = ImageOps.grayscale(image_to_paste)
                image_to_paste = image_to_paste.convert("RGBA")
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
            draw.rectangle([left, top, right, top + inner_width], fill=poster_fg)
            draw.rectangle([left, bottom - inner_width, right, bottom], fill=poster_fg)
            draw.rectangle([left, top + inner_width, left + inner_width, bottom - inner_width], fill=poster_fg)
            draw.rectangle([right - inner_width, top + inner_width, right, bottom - inner_width], fill=poster_fg)

    border_inset = 0.0
    if state.border_enabled_var.get():
        border_ratio = min(0.05, max(0.0, float(state.border_ratio_var.get())))
        border_width = max(1.0, round(poster_page.short_side * border_ratio)) if border_ratio > 0 else 0.0
        if border_width > 0:
            border_inset = min(border_width, poster_page.width / 2, poster_page.height / 2)

    title_text, subtitle_text, formatted_tracklist = _get_export_text_data(state)
    safe_padding = min(16.0, max(8.0, poster_page.width * 0.022))
    text_x1 = poster_page.x + border_inset + safe_padding
    text_x2 = poster_page.x + poster_page.width - border_inset - safe_padding
    cover_title_gap = max(8.0, poster_page.width * 0.022)
    text_y1 = max(cover_y2 + cover_title_gap, poster_page.y + border_inset + safe_padding)
    text_y2 = poster_page.y + poster_page.height - border_inset - safe_padding

    if text_x2 > text_x1 and text_y2 > text_y1:
        text_width = text_x2 - text_x1
        text_height = text_y2 - text_y1
        cursor_y = text_y1
        layout = _fit_export_text_layout(
            draw,
            title_text,
            subtitle_text,
            formatted_tracklist,
            text_width,
            text_height,
            poster_page.width,
        )
        if layout is not None:
            (
                title_font,
                title_lines,
                title_line_height,
                subtitle_font,
                subtitle_lines,
                subtitle_line_height,
                block_gap,
                track_font,
                track_columns,
                track_line_height,
                column_width,
                column_gap,
                _tracks_complete,
            ) = layout

            center_x = poster_page.x + (poster_page.width / 2)
            for line in title_lines:
                _draw_centered_text(draw, center_x, cursor_y, line, title_font, poster_fg)
                cursor_y += title_line_height

            cursor_y += block_gap
            for line in subtitle_lines:
                _draw_centered_text(draw, center_x, cursor_y, line, subtitle_font, poster_fg)
                cursor_y += subtitle_line_height

            cursor_y += block_gap
            if formatted_tracklist and track_font is not None:
                for column_index, track_lines in enumerate(track_columns):
                    column_x = text_x1 + (column_index * (column_width + column_gap))
                    line_y = cursor_y
                    for line in track_lines:
                        if line_y + track_line_height > text_y2 + 1:
                            break
                        draw.text((column_x, line_y), line, font=track_font, fill=poster_fg)
                        line_y += track_line_height

    return image


def _render_poster_svg(state: AppState, dpi: int = DEFAULT_EXPORT_DPI) -> str:
    output_width, output_height = _poster_size_to_pixels(state.poster_size_var.get(), dpi=dpi)
    if Image is not None:
        poster_image = _render_poster_image(state, dpi=dpi).convert("RGB")
        buffer = io.BytesIO()
        poster_image.save(buffer, format="PNG")
        data = base64.b64encode(buffer.getvalue()).decode("ascii")
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{output_width}" height="{output_height}" '
            f'viewBox="0 0 {output_width} {output_height}">'
            f'<image x="0" y="0" width="{output_width}" height="{output_height}" '
            f'href="data:image/png;base64,{data}" preserveAspectRatio="none" />'
            "</svg>"
        )

    # Limited fallback path when Pillow is unavailable: use themed metadata rendering
    # without font metrics so output remains usable and closer to raster export.
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
    poster_bg, poster_fg = _get_theme_colors(state)

    poster_stroke = poster_fg if state.border_enabled_var.get() else "none"
    poster_stroke_width = max(1, round(output_width * 0.0015)) if state.border_enabled_var.get() else 0

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{output_width}" height="{output_height}" viewBox="0 0 {output_width} {output_height}">',
        f'<rect x="{poster_page.x}" y="{poster_page.y}" width="{poster_page.width}" height="{poster_page.height}" fill="{poster_bg}" stroke="{poster_stroke}" stroke-width="{poster_stroke_width}" />',
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

    border_inset = 0.0
    if state.border_enabled_var.get():
        border_ratio = min(0.05, max(0.0, float(state.border_ratio_var.get())))
        border_width = max(1, round(poster_page.short_side * border_ratio)) if border_ratio > 0 else 0
        if border_width > 0:
            inner_width = min(border_width, poster_page.width / 2, poster_page.height / 2)
            border_inset = inner_width
            left = poster_page.x
            top = poster_page.y
            right = poster_page.x + poster_page.width
            bottom = poster_page.y + poster_page.height
            svg_parts.append(
                f'<rect x="{left}" y="{top}" width="{right - left}" height="{inner_width}" fill="{poster_fg}" />'
            )
            svg_parts.append(
                f'<rect x="{left}" y="{bottom - inner_width}" width="{right - left}" height="{inner_width}" fill="{poster_fg}" />'
            )
            svg_parts.append(
                f'<rect x="{left}" y="{top + inner_width}" width="{inner_width}" height="{(bottom - inner_width) - (top + inner_width)}" fill="{poster_fg}" />'
            )
            svg_parts.append(
                f'<rect x="{right - inner_width}" y="{top + inner_width}" width="{inner_width}" height="{(bottom - inner_width) - (top + inner_width)}" fill="{poster_fg}" />'
            )

    title_text, subtitle_text, formatted_tracklist = _get_export_text_data(state)
    safe_padding = min(16.0, max(8.0, poster_page.width * 0.022))
    text_x1 = poster_page.x + border_inset + safe_padding
    text_x2 = poster_page.x + poster_page.width - border_inset - safe_padding
    cover_title_gap = max(8.0, poster_page.width * 0.022)
    text_y1 = max(cover_y2 + cover_title_gap, poster_page.y + border_inset + safe_padding)
    text_y2 = poster_page.y + poster_page.height - border_inset - safe_padding

    title_size = _size_from_width_ratio(poster_page.width, PRIMARY_FONT_RATIOS["title"])
    subtitle_size = _size_from_width_ratio(poster_page.width, PRIMARY_FONT_RATIOS["subtitle"])
    track_size = _size_from_width_ratio(poster_page.width, PRIMARY_FONT_RATIOS["track"])
    title_lh = max(1.0, title_size * 1.2)
    subtitle_lh = max(1.0, subtitle_size * 1.2)
    track_lh = max(1.0, track_size * 1.22)
    cursor_y = text_y1

    if text_x2 > text_x1 and text_y2 > text_y1:
        center_x = poster_page.x + (poster_page.width / 2)
        svg_parts.append(
            f'<text x="{center_x}" y="{cursor_y}" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="{title_size}" font-weight="700" fill="{poster_fg}">{_svg_escape(title_text)}</text>'
        )
        cursor_y += title_lh
        svg_parts.append(
            f'<text x="{center_x}" y="{cursor_y}" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="{subtitle_size}" fill="{poster_fg}">{_svg_escape(subtitle_text)}</text>'
        )
        cursor_y += subtitle_lh + max(2.0, poster_page.width * 0.012)

        for line in formatted_tracklist:
            if cursor_y + track_lh > text_y2:
                break
            svg_parts.append(
                f'<text x="{text_x1}" y="{cursor_y}" font-family="Segoe UI, Arial, sans-serif" font-size="{track_size}" fill="{poster_fg}">{_svg_escape(line)}</text>'
            )
            cursor_y += track_lh

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

