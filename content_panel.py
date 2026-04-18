import tkinter as tk
from tkinter import ttk

from state import AppState


class ContentPanel:
    def __init__(
        self,
        parent: ttk.Frame,
        state: AppState,
        bind_mousewheel_recursive,
    ) -> None:
        self.parent = parent
        self.state = state
        self.bind_mousewheel_recursive = bind_mousewheel_recursive
        self.tracklist_options_frame: ttk.Frame | None = None
        self.certifications_entry: ttk.Entry | None = None
        self.custom_message_label: ttk.Label | None = None
        self.custom_message_entry: ttk.Entry | None = None

    def build(self, row: int) -> ttk.LabelFrame:
        frame = ttk.LabelFrame(self.parent, text="2. Poster content", padding=12)
        frame.grid(row=row, column=0, sticky="ew", pady=8)
        frame.columnconfigure(1, weight=1)

        ttk.Checkbutton(
            frame,
            text="Show music genre",
            variable=self.state.show_genre_var,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=3)

        ttk.Checkbutton(
            frame,
            text="Show tracklist",
            variable=self.state.show_tracklist_var,
            command=self._toggle_tracklist_options,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=3)

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
            textvariable=self.state.tracklist_numbering_var,
            values=["Standard numbers", "Zero-padded numbers", "Roman numerals"],
            state="readonly",
        ).grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=2)

        ttk.Checkbutton(
            frame,
            text="Show featured artists",
            variable=self.state.show_features_var,
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=3)

        ttk.Checkbutton(
            frame,
            text="Certifications",
            variable=self.state.show_certifications_var,
            command=self._toggle_certifications_entry,
        ).grid(row=4, column=0, sticky="w", pady=3)

        self.certifications_entry = ttk.Entry(
            frame,
            textvariable=self.state.certifications_link_var,
        )
        self.certifications_entry.grid(row=4, column=1, sticky="ew", padx=(10, 0), pady=3)

        ttk.Label(frame, text="Funny message").grid(
            row=5, column=0, sticky="w", pady=(10, 4)
        )

        message_menu = ttk.Combobox(
            frame,
            textvariable=self.state.message_var,
            values=[
                "Custom",
                "certified hood classic",
                "safe aux pick",
                "in your feelings",
                "main character energy",
                "no skips",
            ],
            state="readonly",
        )
        message_menu.grid(row=5, column=1, sticky="ew", padx=(10, 0), pady=(10, 4))
        message_menu.bind("<<ComboboxSelected>>", self._on_message_selected)

        self.custom_message_label = ttk.Label(frame, text="Custom text")
        self.custom_message_entry = ttk.Entry(frame, textvariable=self.state.custom_message_var)

        self._toggle_tracklist_options()
        self._toggle_certifications_entry()
        self._toggle_custom_message()
        self.bind_mousewheel_recursive(frame)
        return frame

    def _on_message_selected(self, _event: tk.Event) -> None:
        self._toggle_custom_message()

    def _toggle_tracklist_options(self) -> None:
        if self.tracklist_options_frame is None:
            return
        if self.state.show_tracklist_var.get():
            self.tracklist_options_frame.grid()
        else:
            self.tracklist_options_frame.grid_remove()

    def _toggle_certifications_entry(self) -> None:
        if self.certifications_entry is None:
            return
        self.certifications_entry.configure(
            state="normal" if self.state.show_certifications_var.get() else "disabled"
        )

    def _toggle_custom_message(self) -> None:
        if self.custom_message_label is None or self.custom_message_entry is None:
            return
        if self.state.message_var.get() == "Custom":
            self.custom_message_label.grid(row=6, column=0, sticky="w", pady=4)
            self.custom_message_entry.grid(row=6, column=1, sticky="ew", padx=(10, 0), pady=4)
        else:
            self.custom_message_label.grid_remove()
            self.custom_message_entry.grid_remove()

