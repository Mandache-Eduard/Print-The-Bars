from tkinter import ttk

from state import AppState


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
            "A6 10.5 x 14.85 cm | 4.1 x 5.8 inches",
            "B0 100.0 x 141.4 cm | 39.4 x 55.7 inches",
            "B1 70.7 x 100.0 cm | 27.8 x 39.4 inches",
            "B2 50.0 x 70.7 cm | 19.7 x 27.8 inches",
            "B3 35.3 x 50.0 cm | 13.9 x 19.7 inches",
            "B4 25.0 x 35.3 cm | 9.8 x 13.9 inches",
            "B5 17.6 x 25.0 cm | 6.9 x 9.8 inches",
            "B6 12.5 x 17.6 cm | 4.9 x 6.9 inches",
        ]

        ttk.Combobox(
            frame,
            textvariable=self.state.poster_size_var,
            values=size_options,
            state="readonly",
        ).grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=4)

        self.bind_mousewheel_recursive(frame)
        return frame

