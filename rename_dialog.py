from __future__ import annotations

import tkinter as tk
import ttkbootstrap as ttk
from tkinter import messagebox

class RenameDialog(tk.Toplevel):

    def __init__(
        self,
        parent,
        original_name: str,
        current_name: str,
        extension: str,
        destination_folder: Path,
    ):

        super().__init__(parent)

        self.result = None

        self.destination_folder = destination_folder
        self.extension = extension

        self.title("Rename File")

        self.transient(parent)
        self.grab_set()

        self.geometry("620x280")
        self.resizable(False, False)

        self._build_ui(
            original_name,
            current_name,
            extension,
        )

        self.wait_window(self)

    # -----------------------------------------------------

    def _build_ui(
        self,
        original_name,
        current_name,
        extension,
    ):

        body = ttk.Frame(
            self,
            padding=15,
        )
        body.pack(fill="both", expand=True)

        ttk.Label(
            body,
            text="Original",
        ).pack(anchor="w")

        ttk.Label(
            body,
            text=original_name,
            font=("Menlo", 10),
        ).pack(anchor="w", pady=(0, 12))

        ttk.Separator(body).pack(fill="x", pady=(0, 12))

        ttk.Label(
            body,
            text="New filename",
        ).pack(anchor="w")

        row = ttk.Frame(body)
        row.pack(fill="x", pady=(4, 12))

        self.filename_var = tk.StringVar(value=current_name)

        entry = ttk.Entry(
            row,
            textvariable=self.filename_var,
            width=60,
        )

        entry.pack(side="left", fill="x", expand=True)

        ttk.Label(
            row,
            text=extension,
            font=("Menlo", 10),
        ).pack(side="left", padx=(8, 0))

        entry.focus_set()
        entry.select_range(0, "end")

        ttk.Separator(body).pack(fill="x", pady=(0, 12))

        buttons = ttk.Frame(body)
        buttons.pack(fill="x")

        ttk.Button(
            buttons,
            text="Cancel",
            command=self.destroy,
        ).pack(side="right")

        ttk.Button(
            buttons,
            text="Rename",
            command=self._accept,
        ).pack(side="right", padx=(0, 8))

    # -----------------------------------------------------
    def _validate_name(self, name: str) -> str | None:
        """
        Returns None if valid, otherwise an error message.
        """

        name = name.strip()

        if not name:
            return "Filename cannot be empty."

        invalid = '<>:"/\\|?*'

        for ch in invalid:
            if ch in name:
                return f'Filename cannot contain "{ch}".'

        if name.endswith("."):
            return "Filename cannot end with a period."

        if name.endswith(" "):
            return "Filename cannot end with a space."

        candidate = self.destination_folder / f"{name}{self.extension}"

        if candidate.exists():
            return (
                "A file with this name already exists "
                "in the destination folder."
            )

        return None

    def _accept(self):

        name = self.filename_var.get()

        error = self._validate_name(name)

        if error:
            messagebox.showerror(
                title="Invalid filename",
                message=error,
            )
            return

        self.result = name.strip()
        self.destroy()
