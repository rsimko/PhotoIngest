from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

@dataclass
class SourceInput:
    mode: str  # "folder" | "files"

    folder: Optional[Path] = None
    files: Optional[List[Path]] = None

# =========================================================
# EXIF DATA MODEL
# =========================================================

@dataclass
class ExifData:
    capture_datetime: Optional[str] = None
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None


# =========================================================
# INGEST ITEM (ONE FILE)
# =========================================================

@dataclass
class IngestItem:
    raw_path: Path
    xmp_path: Optional[Path]
    has_xmp: bool = False
    exif: Optional[ExifData] = None


# =========================================================
# INGEST PLAN (FULL COLLECTION)
# =========================================================

@dataclass
class IngestPlan:
    items: list[IngestItem]
