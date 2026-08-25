"""Entry point for the Media Library Tracker application."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from media_library import MediaLibrary, MediaLibraryError  # noqa: E402
from gui import MediaLibraryApp  # noqa: E402

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "library.json")


def main() -> None:
    library = MediaLibrary(DATA_PATH)
    try:
        library.load()
    except MediaLibraryError as exc:
        print(f"Warning: failed to load existing library ({exc}). Starting with an empty library.")

    app = MediaLibraryApp(library)
    app.mainloop()


if __name__ == "__main__":
    main()
