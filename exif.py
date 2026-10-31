from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

from constants import EXIFTOOL
from models import ExifData


class ExifToolReader:
    def __init__(self, exiftool_path: Path = EXIFTOOL) -> None:

        # -----------------------------------------------------
        # 1. Use a system ExifTool if one is available.
        # -----------------------------------------------------

        discovered = shutil.which("exiftool")

        if discovered:
            self.exiftool_path = Path(discovered)
            return

        # -----------------------------------------------------
        # 2. When running as a PyInstaller application,
        #    look inside the bundled application directory.
        # -----------------------------------------------------

        if getattr(sys, "frozen", False):

            bundled_exiftool = (
                Path(sys.executable).resolve().parent.parent
                / "Resources"
                / "bin"
                / "exiftool"
            )

            if bundled_exiftool.exists():
                self.exiftool_path = bundled_exiftool
                return

        # -----------------------------------------------------
        # 3. Normal source-code execution.
        # -----------------------------------------------------

        self.exiftool_path = Path(exiftool_path)

    def read_batch(
        self,
        files: List[Path],
    ) -> Dict[str, ExifData]:

        if not files:
            return {}

        cmd = [
            str(self.exiftool_path),
            "-json",
            "-DateTimeOriginal",
            "-Make",
            "-Model",
        ] + [str(f) for f in files]

        try:

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            if not result.stdout.strip():

                print(
                    "========== EXIF DEBUG =========="
                )

                print(
                    "Command:",
                    cmd,
                )

                print(
                    "STDERR:"
                )

                print(
                    result.stderr
                )

                print(
                    "==============================="
                )

                return {}

            data = json.loads(
                result.stdout
            )

            return self._parse(data)

        except FileNotFoundError:

            print(
                "[ExifTool ERROR] "
                f"ExifTool not found: "
                f"{self.exiftool_path}"
            )

            return {}

        except Exception as e:

            print(
                f"[ExifTool ERROR] {e}"
            )

            return {}

    def _parse(
        self,
        json_data: List[dict],
    ) -> Dict[str, ExifData]:

        output: Dict[str, ExifData] = {}

        for item in json_data:

            source = item.get(
                "SourceFile"
            )

            if not source:
                continue

            output[source] = ExifData(
                capture_datetime=item.get(
                    "DateTimeOriginal"
                ),
                camera_make=item.get(
                    "Make"
                ),
                camera_model=item.get(
                    "Model"
                ),
            )

        return output
