from pathlib import Path
import shutil
import hashlib

class Copier:

    def __init__(
        self,
        logger=None,
        progress=None,
        verify_checksum=True,
    ):
        self.logger = logger
        self.progress = progress
        self.verify_checksum = verify_checksum

        # Cancellation flag
        self.cancel_requested = False

    # =========================================================
    # PUBLIC API
    # =========================================================

    def execute(self, plan, mode="skip"):

        self.cancel_requested = False

        # -----------------------------------------------------
        # BACKUP SETTINGS
        # -----------------------------------------------------

        backup_enabled = plan.backup_enabled
        backup_destination = plan.backup_destination

        stats = {
            "copied_raw": 0,
            "copied_xmp": 0,
            "backup_raw": 0,
            "backup_xmp": 0,
            "backup_errors": 0,
            "renamed": 0,
            "skipped": 0,
            "errors": 0,
            "operations": [],
        }

        total = len(plan.items)
        current = 0
        cancelled = False

        # -----------------------------------------------------
        # Build lookup of review decisions
        # -----------------------------------------------------

        review_map = {}

        for review in plan.review_items or []:
            review_map[review.incoming.source_path] = review

        # -----------------------------------------------------
        # Process plan
        # -----------------------------------------------------

        for item in plan.items:

            if self.cancel_requested:
                cancelled = True
                break

            current += 1

            review = review_map.get(item.source_path)

            # -------------------------------------------------
            # Resolve review decision
            # -------------------------------------------------

            operation = "copied"

            if item.collision and review is not None:

                decision = review.incoming.decision

                # ---------------------------------------------
                # Skip
                # ---------------------------------------------

                if decision == "skip":

                    stats["operations"].append({
                        "filename": item.source_path.name,
                        "destination": str(item.relative_destination),
                        "result": "skipped",
                        "new_name": None,
                    })

                    self._log_operation(
                        filename=item.source_path.name,
                        destination=item.relative_destination,
                        result="skipped",
                    )

                    stats["skipped"] += 1
                    continue

                # ---------------------------------------------
                # Pending
                # ---------------------------------------------

                if decision == "pending":

                    stats["errors"] += 1

                    self._log(
                        f"[ERROR] Unresolved conflict: "
                        f"{item.source_path.name}"
                    )

                    continue

                # ---------------------------------------------
                # Rename
                # ---------------------------------------------

                if decision == "rename":

                    if not review.incoming.new_name:

                        stats["errors"] += 1

                        self._log(
                            f"[ERROR] Rename has no new name: "
                            f"{item.source_path.name}"
                        )

                        continue

                    try:
                        self._apply_rename(
                            item,
                            review.incoming.new_name,
                        )

                    except Exception as e:

                        stats["errors"] += 1

                        self._log(
                            f"[ERROR] Rename failed: "
                            f"{item.source_path.name} -> {e}"
                        )

                        continue

                    operation = "renamed"

                # ---------------------------------------------
                # Unknown decision
                # ---------------------------------------------

                else:

                    stats["errors"] += 1

                    self._log(
                        f"[ERROR] Unknown review decision "
                        f"'{decision}' for "
                        f"{item.source_path.name}"
                    )

                    continue

            # -------------------------------------------------
            # Progress
            # -------------------------------------------------

            if self.progress:

                self.progress(
                    current,
                    total,
                    item.source_path.name,
                )

            # -------------------------------------------------
            # Filesystem operation
            # -------------------------------------------------

            try:

                self._ensure_folder(
                    item.destination_path.parent
                )

                # -------------------------------------------------
                # RAW
                # -------------------------------------------------

                stats, raw_result = self._copy_file(
                    item.source_path,
                    item.destination_path,
                    mode,
                    stats,
                    "RAW",
                )

                # -------------------------------------------------
                # BACKUP RAW
                # -------------------------------------------------

                if backup_enabled and backup_destination:

                    try:

                        backup_raw_path = (
                            backup_destination
                            / item.relative_destination
                        )

                        self._ensure_folder(
                            backup_raw_path.parent
                        )

                        stats, backup_raw_result = self._copy_file(
                            item.source_path,
                            backup_raw_path,
                            mode,
                            stats,
                            "BACKUP RAW",
                        )

                    except Exception as e:

                        stats["backup_errors"] += 1

                        self._log(
                            f"[BACKUP ERROR] "
                            f"{item.source_path.name} -> {e}"
                        )

                # -------------------------------------------------
                # XMP
                # -------------------------------------------------

                if (
                    item.xmp_source
                    and item.xmp_destination
                ):

                    stats, xmp_result = self._copy_file(
                        item.xmp_source,
                        item.xmp_destination,
                        mode,
                        stats,
                        "XMP",
                    )

                    # ---------------------------------------------
                    # BACKUP XMP
                    # ---------------------------------------------

                    if (
                        backup_enabled
                        and backup_destination
                        and item.relative_xmp_destination
                    ):

                        try:

                            backup_xmp_path = (
                                backup_destination
                                / item.relative_xmp_destination
                            )

                            self._ensure_folder(
                                backup_xmp_path.parent
                            )

                            stats, backup_xmp_result = self._copy_file(
                                item.xmp_source,
                                backup_xmp_path,
                                mode,
                                stats,
                                "BACKUP XMP",
                            )

                        except Exception as e:

                            stats["backup_errors"] += 1

                            self._log(
                                f"[BACKUP ERROR] "
                                f"{item.xmp_source.name} -> {e}"
                            )

                # -------------------------------------------------
                # Operation log
                # -------------------------------------------------

                if operation == "renamed":

                    stats["renamed"] += 1

                    stats["operations"].append({
                        "filename": item.source_path.name,
                        "destination": str(item.relative_destination),
                        "result": "renamed",
                        "new_name": item.destination_path.name,
                    })

                    self._log_operation(
                        filename=item.source_path.name,
                        destination=item.relative_destination,
                        result="renamed",
                        new_name=item.destination_path.name,
                    )

                elif raw_result == "skipped":

                    stats["operations"].append({
                        "filename": item.source_path.name,
                        "destination": str(item.relative_destination),
                        "result": "skipped",
                        "new_name": None,
                    })

                    self._log_operation(
                        filename=item.source_path.name,
                        destination=item.relative_destination,
                        result="skipped",
                    )

                else:

                    stats["operations"].append({
                        "filename": item.source_path.name,
                        "destination": str(item.relative_destination),
                        "result": "copied",
                        "new_name": None,
                    })

                    self._log_operation(
                        filename=item.source_path.name,
                        destination=item.relative_destination,
                        result="copied",
                    )

            except Exception as e:

                stats["errors"] += 1

                self._log(
                    f"[ERROR] "
                    f"{item.source_path.name} -> {e}"
                )

        # =====================================================
        # SUMMARY
        # =====================================================

        stats["cancelled"] = cancelled

        return stats

    # =========================================================
    # APPLY REVIEW RENAME
    # =========================================================

    def _apply_rename(self, item, new_name):

        new_name = new_name.strip()

        if not new_name:
            raise ValueError(
                "New filename cannot be empty"
            )

        old_destination = item.destination_path
        old_relative = item.relative_destination

        new_destination = (
            old_destination.parent
            / f"{new_name}{old_destination.suffix}"
        )

        if (
            new_destination.exists()
            and new_destination != old_destination
        ):

            raise FileExistsError(
                f"Destination already exists: "
                f"{new_destination.name}"
            )

        # RAW destination
        item.destination_path = new_destination

        # Relative RAW destination
        item.relative_destination = (
            old_relative.parent
            / new_destination.name
        )

        # XMP follows RAW rename
        if item.xmp_source:

            item.relative_xmp_destination = (
                item.relative_destination.with_suffix(
                    item.relative_destination.suffix + ".xmp"
                )
            )

            item.xmp_destination = (
                new_destination.parent
                / item.relative_xmp_destination.name
            )

    # =========================================================
    # CANCEL COPY
    # =========================================================

    def cancel(self):
        self.cancel_requested = True

    # =========================================================
    # COPY ONE FILE
    # =========================================================

    def _copy_file(
        self,
        src,
        dst,
        mode,
        stats,
        label,
    ):
        if dst.exists():

            if mode == "skip":

                stats["skipped"] += 1

                self._log(
                    f"[WARNING] Destination exists: "
                    f"{dst.name}"
                )

                return stats, "skipped"

            elif mode == "replace":

                shutil.copy2(src, dst)

            else:

                raise FileExistsError(
                    f"Destination already exists: "
                    f"{dst}"
                )

        else:

            shutil.copy2(src, dst)

        # -----------------------------------------------------
        # Verify copy
        # -----------------------------------------------------

        if self.verify_checksum:

            if self._checksum(src) != self._checksum(dst):

                raise Exception(
                    "Checksum mismatch"
                )

        if label == "RAW":

            stats["copied_raw"] += 1

        elif label == "XMP":

            stats["copied_xmp"] += 1

        elif label == "BACKUP RAW":

            stats["backup_raw"] += 1

        elif label == "BACKUP XMP":

            stats["backup_xmp"] += 1

        return stats, "copied"

    # =========================================================
    # FILESYSTEM HELPERS
    # =========================================================

    def _ensure_folder(self, path: Path):

        path.mkdir(
            parents=True,
            exist_ok=True,
        )

    def _checksum(self, path: Path):

        h = hashlib.sha256()

        with open(path, "rb") as f:

            for chunk in iter(
                lambda: f.read(1024 * 1024),
                b"",
            ):

                h.update(chunk)

        return h.hexdigest()

    # =========================================================
    # LOGGING
    # =========================================================

    def _log(self, message):

        if self.logger:
            self.logger(message)

    def _log_operation(
        self,
        filename,
        destination,
        result,
        new_name=None,
    ):

        if not self.logger:
            return

        self.logger(
            {
                "type": "operation",
                "filename": filename,
                "destination": str(destination),
                "result": result,
                "new_name": new_name,
            }
        )
