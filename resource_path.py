from pathlib import Path
import sys


def resource_path(relative_path: str) -> Path:
    """
    Return the correct path to bundled resources.

    Development:
        project/config/settings.json

    PyInstaller:
        Photo Ingest.app/Contents/Resources/config/settings.json
    """

    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).parent

    return base / relative_path
