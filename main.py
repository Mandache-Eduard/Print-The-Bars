import tkinter as tk

from app_ui import AlbumPosterAppUI
from state import AppState


def main() -> None:
    root = tk.Tk()
    state = AppState(root)
    AlbumPosterAppUI(root, state)
    root.mainloop()


if __name__ == "__main__":
    main()
