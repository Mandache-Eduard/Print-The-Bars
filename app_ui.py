import tkinter as tk
import re
from tkinter import font as tkfont
from tkinter import ttk

try:
    from PIL import Image
    from PIL import ImageOps
    from PIL import ImageTk
    from PIL import UnidentifiedImageError
except ImportError:
    Image = None
    ImageOps = None
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
            bg="#808080",
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
        self.state.theme_var.trace_add("write", self._on_theme_change)
        self.state.margin_ratio_var.trace_add("write", self._on_margin_ratio_change)
        self.state.border_enabled_var.trace_add("write", self._on_margin_ratio_change)
        self.state.border_ratio_var.trace_add("write", self._on_margin_ratio_change)
        self.state.monochrome_var.trace_add("write", self._on_cover_image_change)
        self.state.cover_image_path_var.trace_add("write", self._on_cover_image_change)
        self.state.album_metadata_version_var.trace_add("write", self._on_album_metadata_change)
        self.state.show_release_date_var.trace_add("write", self._on_album_metadata_change)
        self.state.release_date_format_var.trace_add("write", self._on_album_metadata_change)
        self.state.show_tracklist_var.trace_add("write", self._on_album_metadata_change)
        self.state.show_features_var.trace_add("write", self._on_album_metadata_change)
        self.state.tracklist_numbering_var.trace_add("write", self._on_album_metadata_change)

    def _on_poster_size_change(self, *_args: object) -> None:
        if hasattr(self, "preview_canvas"):
            self._redraw_preview(self.preview_canvas)

    def _on_margin_ratio_change(self, *_args: object) -> None:
        if hasattr(self, "preview_canvas"):
            self._redraw_preview(self.preview_canvas)

    def _on_theme_change(self, *_args: object) -> None:
        if hasattr(self, "preview_canvas"):
            self._redraw_preview(self.preview_canvas)

    def _on_cover_image_change(self, *_args: object) -> None:
        if hasattr(self, "preview_canvas"):
            self._redraw_preview(self.preview_canvas)

    def _on_album_metadata_change(self, *_args: object) -> None:
        if hasattr(self, "preview_canvas"):
            self._redraw_preview(self.preview_canvas)

    def _to_roman(self, number: int) -> str:
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
        result = []
        remainder = max(1, number)
        for value, symbol in numerals:
            while remainder >= value:
                result.append(symbol)
                remainder -= value
        return "".join(result)

    def _join_feature_names(self, artists: list[str]) -> str:
        if not artists:
            return ""
        if len(artists) == 1:
            return artists[0]
        if len(artists) == 2:
            return f"{artists[0]} & {artists[1]}"
        return f"{', '.join(artists[:-1])} & {artists[-1]}"

    def _format_tracklist(self, tracks: list[object]) -> list[str]:
        numbering = self.state.tracklist_numbering_var.get()
        if len(tracks) == 0:
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
                if self.state.show_features_var.get() and feature_names:
                    title = f"{title} ft. {self._join_feature_names(feature_names)}"
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
            return [f"{self._to_roman(index)}. {title}" for index, title in enumerate(display_tracks, start=1)]
        return [f"{index}. {title}" for index, title in enumerate(display_tracks, start=1)]

    def _get_preview_text_data(self) -> tuple[str, str, list[str]]:
        metadata = self.state.album_metadata if isinstance(self.state.album_metadata, dict) else {}

        title = str(metadata.get("title") or "").strip() or "Album Title"
        artist = str(metadata.get("artist") or "").strip() or "Artist Name"
        release_date = self._format_release_date(str(metadata.get("release_date") or "").strip())

        if self.state.show_release_date_var.get() and release_date:
            subtitle = f"{artist} • {release_date}"
        elif artist == "Artist Name":
            subtitle = "Artist Name • Release Year"
        else:
            subtitle = artist

        tracks = metadata.get("tracklist")
        normalized_tracks: list[object] = []
        if self.state.show_tracklist_var.get() and isinstance(tracks, list):
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
        return title, subtitle, self._format_tracklist(normalized_tracks)

    def _format_release_date(self, release_date: str) -> str:
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

        selected = self.state.release_date_format_var.get()

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

    def _get_selected_dimensions(self) -> tuple[str | None, str | None]:
        value = self.state.poster_size_var.get()
        match = re.search(r"([\d.]+)\s*x\s*([\d.]+)\s*cm\s*\|\s*([\d.]+)\s*x\s*([\d.]+)\s*inches", value)
        if not match:
            return None, None

        width_cm, height_cm, width_in, height_in = match.groups()
        width_text = f"{width_cm} cm | {width_in} inches"
        height_text = f"{height_cm} cm | {height_in} inches"
        return width_text, height_text

    def _get_theme_colors(self) -> tuple[str, str]:
        if self.state.theme_var.get() == "Dark":
            return "#111111", "#F5F4EF"
        return "#F7F7F2", "#111111"

    def _wrap_text_to_width(self, text: str, font: tkfont.Font, max_width: float) -> list[str]:
        if not text:
            return [""]
        if max_width <= 1:
            return [text]

        wrapped_lines: list[str] = []
        for paragraph in text.split("\n"):
            words = paragraph.split()
            if not words:
                wrapped_lines.append("")
                continue
            current = words[0]
            for word in words[1:]:
                candidate = f"{current} {word}"
                if font.measure(candidate) <= max_width:
                    current = candidate
                else:
                    wrapped_lines.append(current)
                    current = word
            wrapped_lines.append(current)
        return wrapped_lines

    def _truncate_to_width(self, text: str, font: tkfont.Font, max_width: float) -> str:
        if font.measure(text) <= max_width:
            return text
        ellipsis = "..."
        if font.measure(ellipsis) > max_width:
            return ""
        candidate = text
        while candidate and font.measure(f"{candidate}{ellipsis}") > max_width:
            candidate = candidate[:-1]
        return f"{candidate.rstrip()}{ellipsis}"

    def _fit_text_block(
        self,
        text: str,
        max_width: float,
        max_height: float,
        preferred_size: int,
        min_size: int,
        max_lines: int,
        weight: str = "normal",
    ) -> tuple[tkfont.Font, list[str], int]:
        for size in range(preferred_size, min_size - 1, -1):
            font = tkfont.Font(family="Segoe UI", size=size, weight=weight)
            lines = self._wrap_text_to_width(text, font, max_width)
            if max_lines > 0 and len(lines) > max_lines:
                continue
            line_height = font.metrics("linespace") + 2
            if (line_height * len(lines)) <= max_height:
                return font, lines, line_height

        font = tkfont.Font(family="Segoe UI", size=min_size, weight=weight)
        line_height = font.metrics("linespace") + 2
        lines = self._wrap_text_to_width(text, font, max_width)
        if max_lines > 0:
            lines = lines[:max_lines]
        max_height_lines = max(1, int(max_height // line_height))
        lines = lines[:max_height_lines]
        if lines and font.measure(lines[-1]) > max_width:
            lines[-1] = self._truncate_to_width(lines[-1], font, max_width)
        return font, lines, line_height

    def _build_track_blocks(
        self,
        tracks: list[str],
        font: tkfont.Font,
        column_width: float,
    ) -> list[list[str]]:
        blocks: list[list[str]] = []
        for track in tracks:
            wrapped = self._wrap_text_to_width(track, font, column_width)
            if not wrapped:
                continue
            block = [wrapped[0]]
            for segment in wrapped[1:]:
                block.append(f"    {segment}")
            blocks.append(block)
        return blocks

    def _layout_track_blocks_into_columns(
        self,
        blocks: list[list[str]],
        max_lines_per_column: int,
        column_count: int,
    ) -> list[list[str]] | None:
        columns: list[list[str]] = [[] for _ in range(column_count)]
        column_index = 0
        used_lines = 0

        for block in blocks:
            remaining_block = list(block)
            while remaining_block:
                if column_index >= column_count:
                    return None

                remaining_lines = max_lines_per_column - used_lines
                if remaining_lines <= 0:
                    column_index += 1
                    used_lines = 0
                    continue

                if len(remaining_block) <= remaining_lines:
                    columns[column_index].extend(remaining_block)
                    used_lines += len(remaining_block)
                    remaining_block = []
                    continue

                if used_lines == 0 or len(remaining_block) > max_lines_per_column:
                    take = max(1, remaining_lines)
                    columns[column_index].extend(remaining_block[:take])
                    remaining_block = remaining_block[take:]
                    used_lines += take
                    if remaining_block:
                        column_index += 1
                        used_lines = 0
                else:
                    column_index += 1
                    used_lines = 0

        while columns and not columns[-1]:
            columns.pop()
        return columns if columns else None

    def _fit_tracklist_lines(
        self,
        tracks: list[str],
        max_width: float,
        max_height: float,
        preferred_size: int,
        min_size: int,
    ) -> tuple[tkfont.Font, list[list[str]], int, float, float, bool]:
        effective_width = max(1.0, max_width)
        effective_height = max(1.0, max_height)

        for size in range(preferred_size, min_size - 1, -1):
            font = tkfont.Font(family="Segoe UI", size=size)
            line_height = font.metrics("linespace") + 1
            max_lines = max(1, int(effective_height // line_height))
            column_gap = max(6.0, min(14.0, effective_width * 0.024))
            min_column_width = max(62.0, font.measure("88. Very Long Track Name ft. Guest") * 0.38)
            max_columns_by_width = max(1, int((effective_width + column_gap) // (min_column_width + column_gap)))
            max_columns_by_width = min(8, max_columns_by_width)

            # Try denser layouts first to maximize vertical capacity.
            for column_count in range(max_columns_by_width, 0, -1):
                column_width = (effective_width - ((column_count - 1) * column_gap)) / column_count
                if column_width < 58.0:
                    continue
                blocks = self._build_track_blocks(tracks, font, column_width)
                total_block_lines = sum(len(block) for block in blocks)
                if total_block_lines > (max_lines * column_count):
                    continue
                columns = self._layout_track_blocks_into_columns(blocks, max_lines, column_count)
                if columns is not None:
                    total_lines_in_columns = sum(len(col) for col in columns)
                    if total_lines_in_columns == total_block_lines and total_lines_in_columns > 0:
                        return font, columns, line_height, column_width, column_gap, True

        font = tkfont.Font(family="Segoe UI", size=min_size)
        line_height = font.metrics("linespace") + 1
        max_lines = max(1, int(effective_height // line_height))
        column_gap = max(5.0, min(10.0, effective_width * 0.02))
        min_column_width = 60.0
        max_columns_by_width = max(1, int((effective_width + column_gap) // (min_column_width + column_gap)))
        column_count = min(8, max_columns_by_width)
        column_width = (effective_width - ((column_count - 1) * column_gap)) / column_count
        blocks = self._build_track_blocks(tracks, font, column_width)

        columns = [[] for _ in range(column_count)]
        flattened_lines: list[str] = []
        for block in blocks:
            flattened_lines.extend(block)

        lines_capacity = max_lines * max(1, column_count)
        if len(flattened_lines) > lines_capacity:
            flattened_lines = flattened_lines[:lines_capacity]
            if flattened_lines:
                flattened_lines[-1] = self._truncate_to_width(flattened_lines[-1], font, column_width)

        for index in range(column_count):
            start = index * max_lines
            end = start + max_lines
            segment = flattened_lines[start:end]
            if not segment:
                break
            columns[index] = segment
        columns = [column for column in columns if column]
        return font, columns, line_height, column_width, column_gap, False

    def _fit_preview_text_layout(
        self,
        title_text: str,
        subtitle_text: str,
        tracks: list[str],
        text_width: float,
        text_height: float,
        poster_width: float,
    ) -> tuple[
        tkfont.Font,
        list[str],
        int,
        tkfont.Font,
        list[str],
        int,
        float,
        tkfont.Font | None,
        list[list[str]],
        int,
        float,
        float,
        bool,
    ]:
        layout_steps = [
            (22, 12, 3, 13, 9, 2, 10, 7, 0.012),
            (20, 11, 3, 12, 8, 2, 9, 6, 0.010),
            (18, 10, 2, 11, 8, 2, 8, 6, 0.008),
            (16, 9, 2, 10, 7, 1, 7, 5, 0.006),
            (14, 8, 2, 9, 7, 1, 6, 5, 0.005),
        ]

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
            title_font, title_lines, title_line_height = self._fit_text_block(
                title_text,
                text_width,
                title_max_height,
                preferred_size=title_pref,
                min_size=title_min,
                max_lines=title_max_lines,
                weight="bold",
            )
            title_height = len(title_lines) * title_line_height

            remaining_for_subtitle = max(12.0, text_height - title_height - block_gap)
            subtitle_max_height = max(14.0, remaining_for_subtitle * 0.25)
            subtitle_font, subtitle_lines, subtitle_line_height = self._fit_text_block(
                subtitle_text,
                text_width,
                subtitle_max_height,
                preferred_size=subtitle_pref,
                min_size=subtitle_min,
                max_lines=subtitle_max_lines,
            )
            subtitle_height = len(subtitle_lines) * subtitle_line_height

            used_height = title_height + subtitle_height + (2 * block_gap)
            track_space = max(0.0, text_height - used_height)

            track_font: tkfont.Font | None = None
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
                ) = self._fit_tracklist_lines(
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

        assert fallback_layout is not None
        return fallback_layout

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
                    if self.state.monochrome_var.get() and ImageOps is not None:
                        image = ImageOps.grayscale(image)  # true grayscale, no autocontrast
                    else:
                        image = image.convert("RGB")
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
        label_space_right = 190
        label_space_bottom = 56
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
        poster_bg, poster_fg = self._get_theme_colors()

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

        canvas.create_rectangle(
            poster_x1,
            poster_y1,
            poster_x2,
            poster_y2,
            fill=poster_bg,
            outline=poster_fg if self.state.border_enabled_var.get() else "",
            width=2 if self.state.border_enabled_var.get() else 0,
        )

        self._draw_cover_image_or_placeholder(
            canvas,
            cover_x1,
            cover_y1,
            cover_x2,
            cover_y2,
        )

        border_inset = 0.0
        if self.state.border_enabled_var.get():
            border_ratio = min(0.05, max(0.0, float(self.state.border_ratio_var.get())))
            border_width = max(1.0, round(poster_page.short_side * border_ratio)) if border_ratio > 0 else 0.0
            if border_width > 0:
                inner_width = min(border_width, poster_width / 2, poster_height / 2)
                border_inset = inner_width
                # Draw border as inset strips so thickness grows inward only.
                canvas.create_rectangle(
                    poster_x1,
                    poster_y1,
                    poster_x2,
                    poster_y1 + inner_width,
                    fill=poster_fg,
                    outline="",
                )
                canvas.create_rectangle(
                    poster_x1,
                    poster_y2 - inner_width,
                    poster_x2,
                    poster_y2,
                    fill=poster_fg,
                    outline="",
                )
                canvas.create_rectangle(
                    poster_x1,
                    poster_y1 + inner_width,
                    poster_x1 + inner_width,
                    poster_y2 - inner_width,
                    fill=poster_fg,
                    outline="",
                )
                canvas.create_rectangle(
                    poster_x2 - inner_width,
                    poster_y1 + inner_width,
                    poster_x2,
                    poster_y2 - inner_width,
                    fill=poster_fg,
                    outline="",
                )

        title_text, subtitle_text, formatted_tracklist = self._get_preview_text_data()
        safe_padding = min(16.0, max(8.0, poster_width * 0.022))
        text_x1 = poster_x1 + border_inset + safe_padding
        text_x2 = poster_x2 - border_inset - safe_padding
        cover_title_gap = max(8.0, poster_width * 0.022)
        text_y1 = max(cover_y2 + cover_title_gap, poster_y1 + border_inset + safe_padding)
        text_y2 = poster_y2 - border_inset - safe_padding

        if text_x2 > text_x1 and text_y2 > text_y1:
            text_width = text_x2 - text_x1
            text_height = text_y2 - text_y1
            cursor_y = text_y1

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
            ) = self._fit_preview_text_layout(
                title_text,
                subtitle_text,
                formatted_tracklist,
                text_width,
                text_height,
                poster_width,
            )

            for line in title_lines:
                canvas.create_text(
                    poster_center_x,
                    cursor_y,
                    text=line,
                    font=title_font,
                    fill=poster_fg,
                    anchor="n",
                )
                cursor_y += title_line_height

            cursor_y += block_gap
            for line in subtitle_lines:
                canvas.create_text(
                    poster_center_x,
                    cursor_y,
                    text=line,
                    font=subtitle_font,
                    fill=poster_fg,
                    anchor="n",
                )
                cursor_y += subtitle_line_height

            cursor_y += block_gap
            if formatted_tracklist and track_font is not None:
                for column_index, track_lines in enumerate(track_columns):
                    column_x = text_x1 + (column_index * (column_width + column_gap))
                    line_y = cursor_y
                    for line in track_lines:
                        if line_y + track_line_height > text_y2 + 1:
                            break
                        canvas.create_text(
                            column_x,
                            line_y,
                            text=line,
                            font=track_font,
                            fill=poster_fg,
                            anchor="nw",
                        )
                        line_y += track_line_height

        width_text, height_text = self._get_selected_dimensions()
        dimension_color = "#FFFFFF"
        if width_text is not None:
            canvas.create_text(
                poster_center_x,
                poster_y2 + 28,
                text=width_text,
                font=("Segoe UI", 12, "bold"),
                fill=dimension_color,
            )
        if height_text is not None:
            canvas.create_text(
                poster_x2 + 22,
                (poster_y1 + poster_y2) / 2,
                text=height_text,
                font=("Segoe UI", 12, "bold"),
                fill=dimension_color,
                anchor="w",
            )

    def _redraw_preview(self, canvas: tk.Canvas) -> None:
        self._draw_preview_placeholder(canvas)

