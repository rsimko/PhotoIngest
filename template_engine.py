from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TemplateContext:
    exif_datetime: datetime | None
    camera_make: str | None
    camera_model: str | None
    job_code: str
    custom_text: str
    counter: int
    original_name: str
    extension: str


class TemplateEngine:
    """
    Responsible for resolving folder and filename templates
    using EXIF + user inputs.
    """

    def render_folder(
        self,
        template: str,
        ctx: TemplateContext,
    ) -> str:
        return self._render(template, ctx)

    def render_filename(
        self,
        template: str,
        ctx: TemplateContext,
    ) -> str:
        return self._render(template, ctx)

    def render_filename_with_extension(
        self,
        template: str,
        ctx: TemplateContext,
    ) -> str:

        filename = self.render_filename(
            template,
            ctx,
        )

        ext = ctx.extension

        if (
            ext
            and not filename.lower().endswith(
                f".{ext.lower()}"
            )
        ):
            filename = f"{filename}.{ext}"

        return filename

    # =========================================================
    # CORE RENDERING
    # =========================================================

    def _render(
        self,
        template: str,
        ctx: TemplateContext,
    ) -> str:

        if not template:
            return ""

        def repl(match):
            token = match.group(1)

            return str(
                self._resolve_token(
                    token,
                    ctx,
                )
            )

        return re.sub(
            r"\{([^}]+)\}",
            repl,
            template,
        )

    # =========================================================
    # TOKEN RESOLUTION
    # =========================================================

    def _resolve_token(
        self,
        token: str,
        ctx: TemplateContext,
    ) -> str:

        dt = ctx.exif_datetime

        if token == "YYYY":
            return dt.strftime("%Y") if dt else ""

        if token == "MM":
            return dt.strftime("%m") if dt else ""

        if token == "DD":
            return dt.strftime("%d") if dt else ""

        if token == "hh":
            return dt.strftime("%H") if dt else ""

        if token == "mm":
            return dt.strftime("%M") if dt else ""

        if token == "ss":
            return dt.strftime("%S") if dt else ""

        if token.lower() in (
            "make",
            "cameramaker",
            "camera_maker",
        ):
            return ctx.camera_make or ""

        if token.lower() in (
            "model",
            "cameramodel",
            "camera_model",
        ):
            return ctx.camera_model or ""

        if token == "job_code":
            return ctx.job_code or ""

        if token == "custom_text":
            return ctx.custom_text or ""

        if token == "counter":
            return f"{ctx.counter:04d}"

        if token == "original":
            return ctx.original_name

        if token == "ext":
            return ctx.extension

        # Unknown token → keep visible for debugging.
        return f"{{{token}}}"
