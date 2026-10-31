from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from constants import SETTINGS_FILE, RAW_EXTENSIONS


@dataclass
class Settings:
    default_source: str
    default_destination: str
    default_backup_destination: str
    reports_directory: str
    last_template: str
    duplicate_mode: str
    verify_checksum: bool
    xmp_naming: str
    window_width: int
    window_height: int
    raw_extensions: list[str]


class SettingsManager:
    def __init__(self, path: Path = SETTINGS_FILE) -> None:
        self.path = path
        self.settings: Settings | None = None

    # =====================================================
    # LOAD
    # =====================================================

    def load(self) -> Settings:

        defaults = self._create_default()

        if not self.path.exists():
            self.settings = defaults
            self.save(self.settings)
            return self.settings

        try:
            data = json.loads(
                self.path.read_text(
                    encoding="utf-8"
                )
            )

            # -------------------------------------------------
            # Add missing settings from older settings files
            # -------------------------------------------------

            data.setdefault(
                "default_source",
                defaults.default_source,
            )

            data.setdefault(
                "default_destination",
                defaults.default_destination,
            )

            # -------------------------------------------------
            # Backup destination migration
            #
            # Older versions used "secondary_destination".
            # Convert that value automatically.
            # -------------------------------------------------

            if "default_backup_destination" not in data:

                data["default_backup_destination"] = (
                    data.get(
                        "secondary_destination",
                        defaults.default_backup_destination,
                    )
                )

            # Remove obsolete settings keys before
            # constructing the Settings dataclass.
            data.pop(
                "secondary_destination",
                None,
            )

            data.pop(
                "secondary_destination_enabled",
                None,
            )

            data.setdefault(
                "reports_directory",
                defaults.reports_directory,
            )

            data.setdefault(
                "last_template",
                defaults.last_template,
            )

            data.setdefault(
                "duplicate_mode",
                defaults.duplicate_mode,
            )

            data.setdefault(
                "verify_checksum",
                defaults.verify_checksum,
            )

            data.setdefault(
                "xmp_naming",
                defaults.xmp_naming,
            )

            data.setdefault(
                "window_width",
                defaults.window_width,
            )

            data.setdefault(
                "window_height",
                defaults.window_height,
            )

            data.setdefault(
                "raw_extensions",
                sorted(RAW_EXTENSIONS),
                )

            self.settings = Settings(**data)

            # Save again so an old settings.json is
            # automatically upgraded to the new format.
            self.save(self.settings)

            return self.settings

        except Exception:

            self.settings = defaults

            return self.settings

    # =====================================================
    # SAVE
    # =====================================================

    def save(
        self,
        settings: Settings,
    ) -> None:

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.path.write_text(
            json.dumps(
                settings.__dict__,
                indent=4,
            ),
            encoding="utf-8",
        )

    # =====================================================
    # DEFAULTS
    # =====================================================

    def _create_default(self) -> Settings:

        return Settings(
            default_source=str(
                Path.home() / "Pictures"
            ),

            default_destination=str(
                Path.home() / "Pictures" / "Ingest"
            ),

            default_backup_destination=str(
                Path.home()
                / "Pictures"
                / "Ingest Backup"
            ),

            reports_directory=str(
                Path.home()
                / "PhotoIngestReports"
                / "reports"
            ),

            last_template="Default",

            duplicate_mode="skip",

            verify_checksum=True,

            xmp_naming="keep_extension",

            window_width=1100,

            window_height=760,

            raw_extensions=sorted(RAW_EXTENSIONS),
        )
