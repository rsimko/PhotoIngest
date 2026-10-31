from __future__ import annotations

from pathlib import Path
from typing import Any
from constants import RAW_EXTENSIONS, SIDECAR_EXTENSION
from exif import ExifToolReader
from models import SourceInput, IngestPlan, IngestItem


class Scanner:
    def __init__(
        self,
        raw_extensions: set[str] | None = None,
    ) -> None:
        self.raw_extensions = (
            raw_extensions
            if raw_extensions is not None
            else set(RAW_EXTENSIONS)
        )

        self.exif_reader = ExifToolReader()

        # event callback (UI attaches to this)
        self.on_event: Callable[[str, Any], None] | None = None

    # =========================================================
    # CORE SCAN LOGIC (shared)
    # =========================================================

    def scan(self, source: SourceInput) -> IngestPlan:

        self._emit("scan_start", source.mode)

        self._emit(
            "scan_status",
            (
                1,
                4,
                "Finding RAW files...",
                "",
            ),
        )

        raw_files = self._collect_raw_files(source)

        self._emit(
            "scan_status",
            (
                2,
                4,
                "Reading EXIF metadata...",
                f"{len(raw_files)} RAW files\nThis may take a while.",
            ),
        )

        self._emit("scan_progress_init", len(raw_files))

        if not raw_files:
            self._emit("scan_error", "No valid RAW files found")
            return IngestPlan(items=[])

        # ---- continue existing pipeline ----

        items = []

        total = len(raw_files)

        for index, raw in enumerate(raw_files, start=1):

            self._emit(
                "scan_progress",
                (
                    index,
                    total,
                    raw.name,
                ),
            )

            xmp = self._find_xmp_for_raw(raw)

            items.append(
                IngestItem(
                    raw_path=raw,
                    xmp_path=xmp,
                    has_xmp=xmp is not None,
                )
            )

        self._emit("scan_exif_start", len(raw_files))
        exif_map = self.exif_reader.read_batch(raw_files)
        self._emit("scan_exif_done", len(exif_map))

        for item in items:
            key = str(item.raw_path)
            if key in exif_map:
                item.exif = exif_map[key]

        plan = IngestPlan(items=items)

        self._emit("scan_done", len(items))

        return plan

    # =========================================================
    # FILE DISCOVERY (folder mode only)
    # =========================================================

    def _find_raw_files(self, folder: Path) -> list[Path]:
        results: List[Path] = []

        for path in folder.rglob("*"):
            if path.is_file() and path.suffix.lower() in self.raw_extensions:
                results.append(path)

        return sorted(results)

    def _find_xmp_for_raw(self, raw: Path) -> Path | None:
        direct = Path(str(raw) + SIDECAR_EXTENSION)
        if direct.exists():
            return direct

        alt = raw.with_suffix("").with_suffix(SIDECAR_EXTENSION)
        if alt.exists():
            return alt

        return None

    # =========================================================
    # EVENTS
    # =========================================================

    def _emit(self, event: str, data: Any = None) -> None:
        if self.on_event:
            self.on_event(event, data)

    def _collect_raw_files(self, source: SourceInput) -> list[Path]:
        raw_files: list[Path] = []

        for p in source.files:

            p = Path(p)

            if not p.exists():
                continue

            # CASE 1: folder → expand
            if p.is_dir():
                raw_files.extend(self._find_raw_files(p))

            # CASE 2: file → accept directly
            elif p.is_file():
                if p.suffix.lower() in self.raw_extensions:
                    raw_files.append(p)

        raw_files = sorted(set(raw_files))

        return raw_files
