from tkinter import ttk

from state import AppState


class CodesPanel:
    def __init__(
        self,
        parent: ttk.Frame,
        state: AppState,
        bind_mousewheel_recursive,
    ) -> None:
        self.parent = parent
        self.state = state
        self.bind_mousewheel_recursive = bind_mousewheel_recursive
        self.qr_entry: ttk.Entry | None = None
        self.spotify_entry: ttk.Entry | None = None

    def build(self, row: int) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(self.parent, text="4. Codes and links", padding=12)
        frame.grid(row=row, column=0, sticky="ew", pady=8)
        frame.columnconfigure(1, weight=1)

        ttk.Checkbutton(
            frame,
            text="QR code",
            variable=self.state.qr_enabled_var,
            command=self._toggle_qr_entry,
        ).grid(row=0, column=0, sticky="w", pady=4)
        self.qr_entry = ttk.Entry(frame, textvariable=self.state.qr_link_var)
        self.qr_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=4)

        ttk.Checkbutton(
            frame,
            text="Spotify code",
            variable=self.state.spotify_enabled_var,
            command=self._toggle_spotify_entry,
        ).grid(row=1, column=0, sticky="w", pady=4)
        self.spotify_entry = ttk.Entry(frame, textvariable=self.state.spotify_link_var)
        self.spotify_entry.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=4)

        self._toggle_qr_entry()
        self._toggle_spotify_entry()
        self.bind_mousewheel_recursive(frame)
        return frame

    def _toggle_qr_entry(self) -> None:
        if self.qr_entry is None:
            return
        self.qr_entry.configure(state="normal" if self.state.qr_enabled_var.get() else "disabled")

    def _toggle_spotify_entry(self) -> None:
        if self.spotify_entry is None:
            return
        self.spotify_entry.configure(
            state="normal" if self.state.spotify_enabled_var.get() else "disabled"
        )

