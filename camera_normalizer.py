from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


CONFIG_DIR = Path(__file__).resolve().parent / "config"
CAMERA_PROFILES_FILE = CONFIG_DIR / "camera_profiles.json"


# =========================================================
# DATA STRUCTURES
# =========================================================

@dataclass(frozen=True)
class CameraProfile:
    raw_make: str
    raw_model: str
    display_make: str
    display_model: str


@dataclass(frozen=True)
class NormalizedCamera:
    make: str | None
    model: str | None
    profile_created: bool = False

    # Contains the profile when a new camera was discovered.
    # None for cameras that were already known.
    new_profile: CameraProfile | None = None


# =========================================================
# CAMERA NORMALIZER
# =========================================================

class CameraNormalizer:

    def __init__(
        self,
        profiles_path: Path | str | None = None,
    ) -> None:

        if profiles_path is None:
            profiles_path = CAMERA_PROFILES_FILE

        self.profiles_path = Path(profiles_path)

        self.profiles: dict[
            tuple[str, str],
            CameraProfile,
        ] = {}

        self._load_profiles()

    # =====================================================
    # PUBLIC API
    # =====================================================

    def normalize(
        self,
        make: str | None,
        model: str | None,
    ) -> NormalizedCamera:

        make = self._clean(make)
        model = self._clean(model)

        if not make and not model:
            return NormalizedCamera(
                make=None,
                model=None,
                profile_created=False,
                new_profile=None,
            )

        # -------------------------------------------------
        # Exact profile match
        # -------------------------------------------------

        if make and model:

            key = (
                self._normalize_key(make),
                self._normalize_key(model),
            )

            profile = self.profiles.get(key)

            if profile:

                return NormalizedCamera(
                    make=profile.display_make,
                    model=profile.display_model,
                    profile_created=False,
                    new_profile=None,
                )

        # -------------------------------------------------
        # Unknown camera
        # -------------------------------------------------

        if make and model:

            return NormalizedCamera(
                make=make,
                model=model,
                profile_created=True,
            )

        # -------------------------------------------------
        # Incomplete EXIF information
        # -------------------------------------------------

        normalized_make = self._normalize_make(make)

        normalized_model = self._normalize_model(
            normalized_make,
            model,
        )

        return NormalizedCamera(
            make=normalized_make,
            model=normalized_model,
            profile_created=False,
            new_profile=None,
        )

    def get_profiles(self) -> list[CameraProfile]:
        """
        Return all currently known camera profiles.

        A copy of the list is returned so callers cannot modify
        the internal profile dictionary directly.
        """
        return list(self.profiles.values())

    # =====================================================
    # PROFILE LOADING
    # =====================================================

    def _load_profiles(self) -> None:

        if not self.profiles_path.exists():
            return

        try:

            with self.profiles_path.open(
                "r",
                encoding="utf-8",
            ) as f:

                data = json.load(f)

        except (
            OSError,
            json.JSONDecodeError,
        ):
            return

        for entry in data.get("profiles", []):

            try:

                profile = CameraProfile(
                    raw_make=str(
                        entry["raw_make"]
                    ).strip(),

                    raw_model=str(
                        entry["raw_model"]
                    ).strip(),

                    display_make=str(
                        entry["display_make"]
                    ).strip(),

                    display_model=str(
                        entry["display_model"]
                    ).strip(),
                )

            except (
                KeyError,
                TypeError,
                ValueError,
            ):
                continue

            if not (
                profile.raw_make
                and profile.raw_model
                and profile.display_make
                and profile.display_model
            ):
                continue

            key = (
                self._normalize_key(
                    profile.raw_make
                ),
                self._normalize_key(
                    profile.raw_model
                ),
            )

            self.profiles[key] = profile

    # =====================================================
    # CREATE / FIND UNKNOWN PROFILE
    # =====================================================

    def _get_or_create_profile(
        self,
        raw_make: str,
        raw_model: str,
    ) -> tuple[CameraProfile, bool]:

        key = (
            self._normalize_key(raw_make),
            self._normalize_key(raw_model),
        )

        # -------------------------------------------------
        # Already known
        # -------------------------------------------------

        existing = self.profiles.get(key)

        if existing:
            return existing, False

        # -------------------------------------------------
        # Create new profile
        #
        # Initially the display values equal the raw EXIF
        # values. The user can customize them later.
        # -------------------------------------------------

        profile = CameraProfile(
            raw_make=raw_make,
            raw_model=raw_model,
            display_make=raw_make,
            display_model=raw_model,
        )

        self.profiles[key] = profile

        self._save_profiles()

        return profile, True

    def update_profile(
        self,
        raw_make: str,
        raw_model: str,
        display_make: str,
        display_model: str,
    ) -> CameraProfile:

        raw_make = self._clean(raw_make) or ""
        raw_model = self._clean(raw_model) or ""
        display_make = self._clean(display_make) or ""
        display_model = self._clean(display_model) or ""

        if not raw_make or not raw_model:
            raise ValueError(
                "Raw camera make and model are required."
            )

        if not display_make or not display_model:
            raise ValueError(
                "Display camera make and model are required."
            )

        key = (
            self._normalize_key(raw_make),
            self._normalize_key(raw_model),
        )

        profile = CameraProfile(
            raw_make=raw_make,
            raw_model=raw_model,
            display_make=display_make,
            display_model=display_model,
        )

        self.profiles[key] = profile

        self._save_profiles()

        return profile

    # =====================================================
    # PROFILE SAVING
    # =====================================================

    def _save_profiles(self) -> None:

        self.profiles_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        profiles = sorted(
            self.profiles.values(),
            key=lambda profile: (
                profile.raw_make.lower(),
                profile.raw_model.lower(),
            ),
        )

        data = {
            "profiles": [
                {
                    "raw_make": profile.raw_make,
                    "raw_model": profile.raw_model,
                    "display_make": profile.display_make,
                    "display_model": profile.display_model,
                }
                for profile in profiles
            ]
        }

        temporary_path = (
            self.profiles_path.with_suffix(".tmp")
        )

        try:

            with temporary_path.open(
                "w",
                encoding="utf-8",
            ) as f:

                json.dump(
                    data,
                    f,
                    indent=4,
                    ensure_ascii=False,
                )

                f.write("\n")

            temporary_path.replace(
                self.profiles_path
            )

        except OSError:

            try:

                if temporary_path.exists():
                    temporary_path.unlink()

            except OSError:
                pass

            raise

    # =====================================================
    # FALLBACK NORMALIZATION
    # =====================================================

    def _normalize_make(
        self,
        make: str | None,
    ) -> str | None:

        if not make:
            return None

        known_makes = {
            "nikon corporation": "Nikon",
            "sony": "SONY",
            "fujifilm": "FUJIFILM",
        }

        return known_makes.get(
            make.lower(),
            make,
        )

    def _normalize_model(
        self,
        make: str | None,
        model: str | None,
    ) -> str | None:

        if not model:
            return None

        if make == "Nikon":

            prefix = "Nikon "

            if model.lower().startswith(
                prefix.lower()
            ):
                model = model[len(prefix):]

            model = model.replace(" ", "")

        return model

    # =====================================================
    # STRING HELPERS
    # =====================================================

    def _clean(
        self,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = str(value).strip()

        if not value:
            return None

        return " ".join(value.split())

    def _normalize_key(
        self,
        value: str,
    ) -> str:

        return " ".join(
            value.strip().split()
        ).lower()
