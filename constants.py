from __future__ import annotations

from pathlib import Path

from resource_path import resource_path

# =========================================================
# APPLICATION
# =========================================================

APP_NAME = "Photo Ingest"
APP_VERSION = "2.0.0"

# =========================================================
# RESOURCES
# =========================================================

CONFIG_DIR = resource_path("config")

SETTINGS_FILE = CONFIG_DIR / "settings.json"
TEMPLATES_FILE = CONFIG_DIR / "templates.json"

ICON_FILE = resource_path("PhotoIngest.icns")

# Will be used in Version 1.1
EXIFTOOL = Path("exiftool")

LOG_DIR = resource_path("logs")

# =========================================================
# FILE NAMING
# =========================================================

COUNTER_PADDING = 4

SIDECAR_EXTENSION = ".xmp"

# =========================================================
# RAW FORMATS
# =========================================================

RAW_EXTENSIONS = {
    ".raf",
    ".cr2",
    ".cr3",
    ".nef",
    ".arw",
    ".rw2",
    ".orf",
    ".dng",
    ".pef",
    ".srw",
}

# =========================================================
# TEMPLATE TOKENS
# =========================================================

TOKENS = [
    "{YYYY}",
    "{MM}",
    "{DD}",
    "{HH}",
    "{mm}",
    "{ss}",
    "{job_code}",
    "{custom_text}",
    "{original}",
    "{counter}",
    "{make}",
    "{model}",
]
