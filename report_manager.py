from __future__ import annotations

from datetime import datetime
from pathlib import Path


class ReportManager:
    MAX_REPORTS = 5

    def __init__(self, reports_dir: str | Path) -> None:
        self.reports_dir = Path(reports_dir)

    # =========================================================
    # DIRECTORY
    # =========================================================

    def ensure_directory(self) -> None:
        self.reports_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    # =========================================================
    # CREATE REPORT PATH
    # =========================================================

    def create_report_path(self) -> Path:
        self.ensure_directory()

        timestamp = datetime.now().strftime(
            "%Y-%m-%d_%H-%M-%S"
        )

        return self.reports_dir / f"{timestamp}_ingest-report.txt"

    # =========================================================
    # WRITE REPORT
    # =========================================================

    def write_report(
        self,
        content: str,
        report_path: Path | None = None,
    ) -> Path:

        self.ensure_directory()

        if report_path is None:
            report_path = self.create_report_path()

        report_path.write_text(
            content,
            encoding="utf-8",
        )

        self._cleanup_old_reports()

        return report_path

    # =========================================================
    # LIST REPORTS
    # =========================================================

    def list_reports(self) -> list[Path]:
        reports = list(
            self.reports_dir.glob("*_ingest-report.txt")
        )

        return sorted(
            reports,
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

    # =========================================================
    # CLEANUP
    # =========================================================

    def _cleanup_old_reports(self) -> None:

        for report in self.list_reports()[self.MAX_REPORTS:]:
            try:
                report.unlink()
            except OSError:
                pass
