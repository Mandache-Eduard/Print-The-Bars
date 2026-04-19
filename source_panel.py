from tkinter import filedialog
from tkinter import ttk

from state import AppState


class SourcePanel:
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
        frame = ttk.LabelFrame(self.parent, text="1. Album source", padding=12)
        frame.grid(row=row, column=0, sticky="ew", pady=8)
        frame.columnconfigure(1, weight=1)

        ttk.Button(frame, text="Upload cover", command=self._upload_cover).grid(
            row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8)
        )

        ttk.Label(frame, text="Album link (optional)").grid(
            row=1, column=0, sticky="w", pady=4
        )
        ttk.Entry(frame, textvariable=self.state.album_link_var).grid(
            row=1, column=1, sticky="ew", padx=(10, 0), pady=4
        )

        self.bind_mousewheel_recursive(frame)
        return frame

    def _upload_cover(self) -> None:
        selected_path = filedialog.askopenfilename(
            title="Select album cover",
            filetypes=[
                (
                    "Image files",
                    "*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp *.ico *.ppm *.pgm",
                ),
                ("All files", "*.*"),
            ],
        )
        if selected_path:
            self.state.cover_image_path_var.set(selected_path)

