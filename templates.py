from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from constants import TEMPLATES_FILE


@dataclass
class Template:
    name: str
    folder_template: str
    filename_template: str


class TemplateManager:
    def __init__(self, path: Path = TEMPLATES_FILE) -> None:
        self.path = path
        self.templates: list[Template] = []

    def load(self) -> list[Template]:
        if not self.path.exists():
            self.templates = self._default_templates()
            self.save(self.templates)
            return self.templates

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.templates = [Template(**t) for t in data]
            return self.templates

        except Exception:
            self.templates = self._default_templates()
            return self.templates

    def save(self, templates: list[Template]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)

        self.path.write_text(
            json.dumps(
                [t.__dict__ for t in templates],
                indent=4,
            ),
            encoding="utf-8",
        )

    def _default_templates(self) -> list[Template]:
        return [
            Template(
                name="Default",
                folder_template="{YYYY}/{job_code}/{MM}/{DD}",
                filename_template="{YYYY}_{MM}_{DD}_{job_code}_{original}_{counter}",
            )
        ]

    def upsert(self, template: Template) -> None:
        name = template.name.strip().lower()

        for i, t in enumerate(self.templates):
            if t.name.strip().lower() == name:
                self.templates[i] = template
                self.save(self.templates)
                return

        self.templates.append(template)
        self.save(self.templates)

    def delete(self, name: str) -> None:
        target = name.strip().lower()

        self.templates = [
            t
            for t in self.templates
            if t.name.strip().lower() != target
        ]

        self.save(self.templates)
