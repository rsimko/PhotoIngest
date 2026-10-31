from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from camera_normalizer import CameraNormalizer, CameraProfile
from template_engine import TemplateContext, TemplateEngine


# =========================================================
# DATA STRUCTURES
# =========================================================

@dataclass
class PlannedItem:
    source_path: Path

    destination_path: Path
    relative_destination: Path

    xmp_source: Path | None
    xmp_destination: Path | None
    relative_xmp_destination: Path | None

    counter: int
    collision: bool = False

    # Review state
    decision: str = "pending"
    new_name: str | None = None


@dataclass
class ReviewItem:
    """
    Represents one duplicate requiring user review.
    """

    incoming: PlannedItem
    existing_path: Path

    reason: str = "duplicate"


@dataclass
class IngestPlan:
    items: list[PlannedItem]

    existing_collisions: int = 0
    duplicate_collisions: int = 0

    review_items: list[ReviewItem] | None = None

    backup_enabled: bool = False
    backup_destination: Path | None = None


# =========================================================
# PLANNER
# =========================================================

class Planner:
    """
    Converts scan results into a fully resolved ingest plan.

    All paths are absolute and ready for filesystem operations.

    EXIF camera information is passed through CameraNormalizer
    before being given to the template engine.
    """

    def __init__(self):
        self.engine = TemplateEngine()
        self.camera_normalizer = CameraNormalizer()

        self.progress_callback: Callable[
            [int, int, str], None
        ] | None = None

        self.unknown_cameras: list[tuple[str, str]] = []

    # =====================================================
    # PUBLIC API
    # =====================================================

    def find_unknown_cameras(
        self,
        scan_result,
    ) -> list[tuple[str, str]]:

        unknown: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()

        for item in scan_result.items:

            if not item.exif:
                continue

            raw_make = item.exif.camera_make
            raw_model = item.exif.camera_model

            if not raw_make or not raw_model:
                continue

            key = (
                raw_make.strip().lower(),
                raw_model.strip().lower(),
            )

            if key in seen:
                continue

            camera = self.camera_normalizer.normalize(
                make=raw_make,
                model=raw_model,
            )

            if camera.profile_created:

                seen.add(key)

                unknown.append(
                    (
                        raw_make.strip(),
                        raw_model.strip(),
                    )
                )

        return unknown

    def build(
        self,
        scan_result,
        destination_root: str,
        folder_template: str,
        file_template: str,
        job_code: str,
        custom_text: str,
        start_counter: int = 1,
        duplicate_mode: str = "skip",
        xmp_naming: str = "keep_extension",
        backup_enabled: bool = False,
        backup_destination: str | None = None,
    ) -> IngestPlan:

        self.unknown_cameras = []

        items: list[PlannedItem] = []
        review_items: list[ReviewItem] = []

        counter = start_counter
        planned_destinations: set[Path] = set()

        existing_collisions = 0
        duplicate_outputs = 0

        dest_root = Path(destination_root)
        total = len(scan_result.items)

        # =================================================
        # PROCESS SCANNED FILES
        # =================================================

        for index, item in enumerate(
            scan_result.items,
            start=1,
        ):

            if self.progress_callback:
                self.progress_callback(
                    index,
                    total,
                    item.raw_path.name,
                )

            # -------------------------------------------------
            # EXIF DATETIME
            # -------------------------------------------------

            exif_dt = self._parse_exif_datetime(
                getattr(
                    item.exif,
                    "capture_datetime",
                    None,
                )
                if item.exif
                else None
            )

            # -------------------------------------------------
            # CAMERA NORMALIZATION
            # -------------------------------------------------

            raw_camera_make = (
                item.exif.camera_make
                if item.exif
                else None
            )

            raw_camera_model = (
                item.exif.camera_model
                if item.exif
                else None
            )

            camera = self.camera_normalizer.normalize(
                make=raw_camera_make,
                model=raw_camera_model,
            )

            # -------------------------------------------------
            # UNKNOWN CAMERA PROFILE
            # -------------------------------------------------

            if (
                camera.profile_created
                and raw_camera_make
                and raw_camera_model
            ):

                camera_key = (
                    raw_camera_make.strip().lower(),
                    raw_camera_model.strip().lower(),
                )

                existing_keys = {
                    (
                        make.strip().lower(),
                        model.strip().lower(),
                    )
                    for make, model in self.unknown_cameras
                }

                if camera_key not in existing_keys:

                    self.unknown_cameras.append(
                        (
                            raw_camera_make,
                            raw_camera_model,
                        )
                    )

            camera_make = camera.make
            camera_model = camera.model

            # -------------------------------------------------
            # DESTINATION
            # -------------------------------------------------

            if exif_dt is None:

                relative_destination = (
                    Path("Unsorted")
                    / item.raw_path.name
                )

                destination_path = (
                    dest_root
                    / relative_destination
                )

            else:

                ctx = TemplateContext(
                    exif_datetime=exif_dt,
                    camera_make=camera_make,
                    camera_model=camera_model,
                    job_code=job_code,
                    custom_text=custom_text,
                    counter=counter,
                    original_name=item.raw_path.stem,
                    extension=item.raw_path.suffix.lstrip("."),
                )

                folder_rel = self.engine.render_folder(
                    folder_template,
                    ctx,
                )

                filename = (
                    self.engine.render_filename_with_extension(
                        file_template,
                        ctx,
                    )
                )

                relative_destination = (
                    Path(folder_rel)
                    / filename
                )

                destination_path = (
                    dest_root
                    / relative_destination
                )

            # -------------------------------------------------
            # COLLISION DETECTION
            # -------------------------------------------------

            existing_collision = destination_path.exists()

            duplicate_collision = (
                destination_path
                in planned_destinations
            )

            if existing_collision:
                existing_collisions += 1

            if duplicate_collision:
                duplicate_outputs += 1

            collision = (
                existing_collision
                or duplicate_collision
            )

            # -------------------------------------------------
            # AUTOMATIC RENAME MODE
            # -------------------------------------------------

            if (
                collision
                and duplicate_mode == "rename"
            ):

                destination_path = self._make_unique_path(
                    destination_path,
                    planned_destinations,
                )

                relative_destination = (
                    destination_path.relative_to(
                        dest_root
                    )
                )

                collision = False

            planned_destinations.add(
                destination_path
            )

            # -------------------------------------------------
            # XMP HANDLING
            # -------------------------------------------------

            xmp_source = (
                item.xmp_path
                if item.has_xmp
                else None
            )

            xmp_destination = None
            relative_xmp_destination = None

            if xmp_source:

                if xmp_naming == "remove_extension":

                    relative_xmp_destination = (
                        relative_destination.with_suffix(
                            ".xmp"
                        )
                    )

                else:

                    relative_xmp_destination = (
                        relative_destination.with_suffix(
                            relative_destination.suffix
                            + ".xmp"
                        )
                    )

                xmp_destination = (
                    dest_root
                    / relative_xmp_destination
                )

            # -------------------------------------------------
            # CREATE PLANNED ITEM
            # -------------------------------------------------

            planned_item = PlannedItem(
                source_path=item.raw_path,

                destination_path=destination_path,
                relative_destination=relative_destination,

                xmp_source=xmp_source,
                xmp_destination=xmp_destination,
                relative_xmp_destination=(
                    relative_xmp_destination
                ),

                counter=counter,
                collision=collision,
            )

            # -------------------------------------------------
            # REVIEW MODE
            # -------------------------------------------------

            if (
                collision
                and duplicate_mode == "review"
            ):

                review_items.append(
                    ReviewItem(
                        incoming=planned_item,
                        existing_path=destination_path,
                    )
                )

            # -------------------------------------------------
            # STORE ITEM
            # -------------------------------------------------

            items.append(planned_item)

            counter += 1

        # =====================================================
        # RETURN PLAN
        # =====================================================

        return IngestPlan(
            items=items,
            existing_collisions=existing_collisions,
            duplicate_collisions=duplicate_outputs,
            review_items=review_items,
            backup_enabled=backup_enabled,
            backup_destination=(
                Path(backup_destination)
                if backup_enabled and backup_destination
                else None
            ),
        )

    # =========================================================
    # UNIQUE DESTINATION
    # =========================================================

    def _make_unique_path(
        self,
        destination: Path,
        planned_destinations: set[Path],
    ) -> Path:
        """
        Returns a unique destination filename by appending
        _0002, _0003, ... before the extension.
        """

        if (
            not destination.exists()
            and destination not in planned_destinations
        ):
            return destination

        stem = destination.stem
        suffix = destination.suffix
        parent = destination.parent

        counter = 2

        while True:

            candidate = (
                parent
                / f"{stem}_{counter}{suffix}"
            )

            if (
                not candidate.exists()
                and candidate not in planned_destinations
            ):
                return candidate

            counter += 1

    # =========================================================
    # EXIF DATETIME
    # =========================================================

    def _parse_exif_datetime(
        self,
        value,
    ):
        """
        Accepts:

        - datetime object
        - EXIF string:
          YYYY:MM:DD HH:MM:SS
        - None
        """

        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, str):

            try:
                return datetime.strptime(
                    value,
                    "%Y:%m:%d %H:%M:%S",
                )

            except ValueError:
                return None

        return None
