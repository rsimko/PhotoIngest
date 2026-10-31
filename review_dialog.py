from __future__ import annotations

import subprocess
from pathlib import Path
import tkinter as tk
import ttkbootstrap as ttk
from rename_dialog import RenameDialog

class ReviewDialog(tk.Toplevel):

    def __init__(self, parent, review_items):

        super().__init__(parent)

        self.review_items = review_items
        self.result = None
        self.index = 0

        self.title("Destination Conflicts")

        self.transient(parent)
        self.grab_set()

        self.resizable(False, False)
        self.geometry("760x500")

        self._build_ui()
        self._load_item()

        # Wait here until the dialog is closed.
        # Only then does execution continue in ui.py.
        self.wait_window(self)

    # -----------------------------------------------------

    def _build_ui(self):

        body = ttk.Frame(self, padding=15)
        body.pack(fill="both", expand=True)

        self.counter_label = ttk.Label(
            body,
            text="",
            font=("TkDefaultFont", 9, "bold"),
        )
        self.counter_label.pack(
            anchor="w",
            pady=(0, 12),
        )

        self.progress_label = ttk.Label(
            body,
            text="",
            font=("TkDefaultFont", 9),
        )
        self.progress_label.pack(
            anchor="w",
            pady=(0, 8),
        )

        self.status_label = ttk.Label(
            body,
            text="",
            font=("TkDefaultFont", 9, "italic"),
        )
        self.status_label.pack(
            anchor="w",
            pady=(0, 8),
        )

        self.rename_preview_label = ttk.Label(
            body,
            text="",
            font=("Menlo", 10),
        )
        self.rename_preview_label.pack(
            anchor="w",
            pady=(0, 10),
        )

        ttk.Separator(body).pack(
            fill="x",
            pady=(0, 12),
        )

        # =====================================================
        # Original
        # =====================================================

        ttk.Label(
            body,
            text="Original",
        ).pack(
            anchor="w",
            pady=(6, 3),
        )

        self.original_file_label = ttk.Label(
            body,
            text="",
            font=("Menlo", 10),
        )
        self.original_file_label.pack(
            anchor="w",
        )

        ttk.Separator(body).pack(
            fill="x",
            pady=(10, 12),
        )

        # =====================================================
        # Incoming
        # =====================================================

        ttk.Label(
            body,
            text="Incoming file",
        ).pack(anchor="w")

        incoming_row = ttk.Frame(body)
        incoming_row.pack(
            fill="x",
            pady=(4, 12),
        )

        self.incoming_folder_label = ttk.Label(
            incoming_row,
            text="",
            font=("Menlo", 10),
        )
        self.incoming_folder_label.pack(
            anchor="w",
        )

        incoming_file_row = ttk.Frame(incoming_row)
        incoming_file_row.pack(
            fill="x",
            pady=(2, 0),
        )

        self.incoming_file_label = ttk.Label(
            incoming_file_row,
            text="",
            font=("Menlo", 10),
        )
        self.incoming_file_label.pack(
            side="left",
            anchor="w",
        )

        self.reveal_incoming_button = ttk.Button(
            incoming_file_row,
            text="Reveal in Finder",
            command=self._reveal_incoming,
            #width=16,
        )
        self.reveal_incoming_button.pack(
            side="right",
            padx=(12, 0),
        )

        ttk.Separator(body).pack(
            fill="x",
            pady=(0, 12),
        )

        # =====================================================
        # Existing
        # =====================================================

        ttk.Label(
            body,
            text="Existing file",
        ).pack(anchor="w")

        existing_row = ttk.Frame(body)
        existing_row.pack(
            fill="x",
            pady=(4, 12),
        )

        self.existing_folder_label = ttk.Label(
            existing_row,
            text="",
            font=("Menlo", 10),
        )
        self.existing_folder_label.pack(
            anchor="w",
        )

        existing_file_row = ttk.Frame(existing_row)
        existing_file_row.pack(
            fill="x",
            pady=(2, 0),
        )

        self.existing_file_label = ttk.Label(
            existing_file_row,
            text="",
            font=("Menlo", 10),
        )
        self.existing_file_label.pack(
            side="left",
            anchor="w",
        )

        self.reveal_existing_button = ttk.Button(
            existing_file_row,
            text="Reveal in Finder",
            command=self._reveal_existing,
            #width=16,
        )
        self.reveal_existing_button.pack(
            side="right",
            padx=(12, 0),
        )

        ttk.Separator(body).pack(
            fill="x",
            pady=(0, 12),
        )

        # =====================================================
        # Bottom actions
        # =====================================================

        buttons = ttk.Frame(body)
        buttons.pack(
            fill="x",
            pady=(4, 0),
        )

        # Navigation
        self.prev_button = ttk.Button(
            buttons,
            text="◀ Previous",
            command=self._previous,
        )
        self.prev_button.pack(
            side="left",
        )

        self.next_button = ttk.Button(
            buttons,
            text="Next ▶",
            command=self._next,
        )
        self.next_button.pack(
            side="left",
            padx=(5, 20),
        )

        # Rename
        self.rename_button = ttk.Button(
            buttons,
            text="Rename",
            command=self._rename,
        )
        self.rename_button.pack(
            side="right",
            padx=(0, 5),
        )

        # Skip
        self.skip_button = ttk.Button(
            buttons,
            text="Skip",
            command=self._skip,
        )
        self.skip_button.pack(
            side="right",
            padx=(8, 8),
        )

        # Cancel
        self.finish_button = ttk.Button(
            buttons,
            text="Cancel Copy",
            command=self._cancel,
        )
        self.finish_button.pack(
            side="right",
        )

    # -----------------------------------------------------

    def _load_item(self):

        review = self.review_items[self.index]

        if review.incoming.decision == "pending":
            status = "Status: Pending"

        elif review.incoming.decision == "skip":
            status = "Status: Skipped"

        elif review.incoming.decision == "rename":
            status = "Status: Renamed"

        else:
            status = ""

        self.status_label.configure(
            text=status,
        )

        if (
            review.incoming.decision == "rename"
            and review.incoming.new_name
        ):

            suffix = review.incoming.destination_path.suffix

            self.rename_preview_label.configure(
                text=(
                    f"New filename: "
                    f"{review.incoming.new_name}{suffix}"
                ),
            )

        else:

            self.rename_preview_label.configure(
                text="",
            )

        self.original_file_label.configure(
            text=review.incoming.source_path.name,
        )

        self.counter_label.configure(
            text=(
                f"Conflict {self.index + 1} "
                f"of {len(self.review_items)}"
            ),
        )

        completed = sum(
            1
            for item in self.review_items
            if item.incoming.decision != "pending"
        )

        remaining = len(self.review_items) - completed

        self.progress_label.configure(
            text=(
                f"Completed: {completed}    "
                f"Remaining: {remaining}"
            ),
        )

        incoming = review.incoming.destination_path

        self.incoming_folder_label.configure(
            text=str(incoming.parent),
        )

        self.incoming_file_label.configure(
            text=incoming.name,
        )

        self.existing_folder_label.configure(
            text=str(review.existing_path.parent),
        )

        self.existing_file_label.configure(
            text=review.existing_path.name,
        )

        self.prev_button.configure(
            state=(
                "normal"
                if self.index > 0
                else "disabled"
            ),
        )

        self.next_button.configure(
            state=(
                "normal"
                if self.index < len(self.review_items) - 1
                else "disabled"
            ),
        )

    # -----------------------------------------------------

    def _finish(self):

        self.result = self.review_items
        self.destroy()

    # -----------------------------------------------------

    def _cancel(self):

        self.result = None
        self.destroy()

    # -----------------------------------------------------

    def _previous(self):

        if self.index > 0:
            self.index -= 1
            self._load_item()

    # -----------------------------------------------------

    def _next(self):

        if self.index < len(self.review_items) - 1:
            self.index += 1
            self._load_item()

    # -----------------------------------------------------

    def _skip(self):

        review = self.review_items[self.index]

        review.incoming.decision = "skip"

        remaining = sum(
            1
            for item in self.review_items
            if item.incoming.decision == "pending"
        )

        if remaining == 0:
            self._finish()
            return

        if self.index < len(self.review_items) - 1:
            self.index += 1

        self._load_item()

    # -----------------------------------------------------

    def _rename(self):

        review = self.review_items[self.index]

        current = review.incoming.destination_path

        dlg = RenameDialog(
            self,
            original_name=review.incoming.source_path.name,
            current_name=current.stem,
            extension=current.suffix,
            destination_folder=current.parent,
        )

        if dlg.result is None:
            return

        review.incoming.decision = "rename"
        review.incoming.new_name = dlg.result

        remaining = sum(
            1
            for item in self.review_items
            if item.incoming.decision == "pending"
        )

        if remaining == 0:
            self._finish()
            return

        if self.index < len(self.review_items) - 1:
            self.index += 1

        self._load_item()

    # -----------------------------------------------------

    def _reveal_incoming(self):

        review = self.review_items[self.index]

        self._reveal(
            review.incoming.source_path,
        )

    # -----------------------------------------------------

    def _reveal_existing(self):

        review = self.review_items[self.index]

        self._reveal(
            review.existing_path,
        )

    # -----------------------------------------------------

    def _reveal(self, path: Path):

        try:

            subprocess.run(
                ["open", "-R", str(path)],
                check=False,
            )

        except Exception:
            pass
