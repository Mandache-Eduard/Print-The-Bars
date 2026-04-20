import tkinter as tk


class AppState:
    def __init__(self, root: tk.Misc) -> None:
        self.album_link_var = tk.StringVar(root)
        self.album_validation_status_var = tk.StringVar(root, value="idle")
        self.album_validation_message_var = tk.StringVar(root, value="")
        self.album_loading_var = tk.BooleanVar(root, value=False)
        self.album_metadata_version_var = tk.IntVar(root, value=0)
        self.album_metadata: dict[str, object] = {
            "title": "",
            "artist": "",
            "release_date": "",
            "tracklist": [],
            "cover_url": "",
            "source_provider": "",
            "source_id": "",
            "validation_status": "idle",
            "error_message": "",
        }
        self.cover_image_path_var = tk.StringVar(root, value="")
        self.border_enabled_var = tk.BooleanVar(root, value=False)
        self.border_size_var = tk.IntVar(root, value=12)
        self.margin_ratio_var = tk.DoubleVar(root, value=0.12)
        self.monochrome_var = tk.BooleanVar(root, value=False)
        self.theme_var = tk.StringVar(root, value="Light")
        self.font_var = tk.StringVar(root, value="Helvetica")
        self.show_release_date_var = tk.BooleanVar(root, value=False)
        self.show_genre_var = tk.BooleanVar(root, value=True)
        self.show_tracklist_var = tk.BooleanVar(root, value=True)
        self.tracklist_numbering_var = tk.StringVar(root, value="Standard numbers")
        self.show_features_var = tk.BooleanVar(root, value=False)
        self.show_certifications_var = tk.BooleanVar(root, value=False)
        self.certifications_link_var = tk.StringVar(root)
        self.gradient_var = tk.BooleanVar(root, value=False)
        self.qr_enabled_var = tk.BooleanVar(root, value=False)
        self.qr_link_var = tk.StringVar(root)
        self.spotify_enabled_var = tk.BooleanVar(root, value=False)
        self.spotify_link_var = tk.StringVar(root)
        self.message_var = tk.StringVar(root, value="Custom")
        self.custom_message_var = tk.StringVar(root)
        self.poster_size_var = tk.StringVar(
            root,
            value="A3 29.7 x 42 cm | 11.7 x 16.5 inches",
        )
        self.export_format_var = tk.StringVar(root, value="PNG")

