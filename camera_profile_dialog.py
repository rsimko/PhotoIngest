from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk


class CameraProfileDialog(tk.Toplevel):

    def __init__(
        self,
        parent: tk.Tk,
        cameras: list[tuple[str, str]],
    ) -> None:

        super().__init__(parent)

        self.cameras = cameras
        self.result: list[tuple[str, str, str, str]] | None = None

        self.title("Unknown Cameras")
        self.geometry("620x560")
        self.minsize(620, 450)
        self.resizable(True, True)

        self.transient(parent)
        self.grab_set()

        self.display_vars: list[
            tuple[
                str,
                str,
                tk.StringVar,
                tk.StringVar,
            ]
        ] = []

        self._build_ui()

        self.protocol(
            "WM_DELETE_WINDOW",
            self._cancel,
        )

    # =====================================================
    # UI
    # =====================================================

    def _build_ui(self) -> None:

        body = ttk.Frame(
            self,
            padding=15,
        )
        body.pack(
            fill="both",
            expand=True,
        )

        ttk.Label(
            body,
            text="Unknown cameras detected",
            font=("TkDefaultFont", 14, "bold"),
        ).pack(
            anchor="w",
            pady=(0, 5),
        )

        ttk.Label(
            body,
            text=(
                f"{len(self.cameras)} new camera"
                f"{'' if len(self.cameras) == 1 else 's'} "
                "were found.\n"
                "Review the display names below, then continue."
            ),
        ).pack(
            anchor="w",
            pady=(0, 12),
        )

        # -------------------------------------------------
        # Scrollable camera area
        # -------------------------------------------------

        container = ttk.Frame(body)
        container.pack(
            fill="both",
            expand=True,
        )

        canvas = tk.Canvas(
            container,
            highlightthickness=0,
        )

        scrollbar = ttk.Scrollbar(
            container,
            orient="vertical",
            command=canvas.yview,
        )

        self.camera_frame = ttk.Frame(canvas)

        self.camera_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            ),
        )

        canvas_window = canvas.create_window(
            (0, 0),
            window=self.camera_frame,
            anchor="nw",
        )

        def resize_frame(event):
            canvas.itemconfigure(
                canvas_window,
                width=event.width,
            )

        canvas.bind(
            "<Configure>",
            resize_frame,
        )

        canvas.configure(
            yscrollcommand=scrollbar.set,
        )

        canvas.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar.pack(
            side="right",
            fill="y",
        )

        # -------------------------------------------------
        # Camera entries
        # -------------------------------------------------

        for index, (raw_make, raw_model) in enumerate(
            self.cameras,
            start=1,
        ):

            self._add_camera(
                index,
                raw_make,
                raw_model,
            )

        # -------------------------------------------------
        # Bottom buttons
        # -------------------------------------------------

        button_frame = ttk.Frame(body)
        button_frame.pack(
            fill="x",
            pady=(12, 0),
        )

        ttk.Button(
            button_frame,
            text="Cancel",
            command=self._cancel,
        ).pack(
            side="right",
            padx=(8, 0),
        )

        ttk.Button(
            button_frame,
            text="Save & Continue",
            bootstyle="success",
            command=self._save,
        ).pack(
            side="right",
        )

    # =====================================================
    # CAMERA ENTRY
    # =====================================================

    def _add_camera(
    self,
    index: int,
    raw_make: str,
    raw_model: str,
    ) -> None:

        # -------------------------------------------------
        # Camera section
        # -------------------------------------------------

        frame = ttk.LabelFrame(
            self.camera_frame,
            text=f"Camera {index}",
        )

        frame.pack(
            fill="x",
            padx=2,
            pady=(0, 10),
        )

        # LabelFrame itself does not accept padding in
        # ttkbootstrap, so use an inner frame instead.
        content = ttk.Frame(
            frame,
            padding=10,
        )

        content.pack(
            fill="x",
            expand=True,
        )

        # -------------------------------------------------
        # EXIF identity
        # -------------------------------------------------

        ttk.Label(
            content,
            text="EXIF identity",
            font=("TkDefaultFont", 9, "bold"),
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 5),
        )

        ttk.Label(
            content,
            text=f"Make:  {raw_make}",
        ).grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="w",
        )

        ttk.Label(
            content,
            text=f"Model: {raw_model}",
        ).grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 10),
        )

        # -------------------------------------------------
        # Display values
        # -------------------------------------------------

        display_make_var = tk.StringVar(
            value=raw_make
        )

        display_model_var = tk.StringVar(
            value=raw_model
        )

        ttk.Label(
            content,
            text="Display Make",
        ).grid(
            row=3,
            column=0,
            sticky="w",
            padx=(0, 10),
            pady=(0, 5),
        )

        ttk.Entry(
            content,
            textvariable=display_make_var,
        ).grid(
            row=3,
            column=1,
            sticky="ew",
            pady=(0, 5),
        )

        ttk.Label(
            content,
            text="Display Model",
        ).grid(
            row=4,
            column=0,
            sticky="w",
            padx=(0, 10),
        )

        ttk.Entry(
            content,
            textvariable=display_model_var,
        ).grid(
            row=4,
            column=1,
            sticky="ew",
        )

        # -------------------------------------------------
        # Use EXIF button
        # -------------------------------------------------

        ttk.Button(
            content,
            text="Use EXIF Values",
            command=lambda: self._use_exif(
                display_make_var,
                display_model_var,
                raw_make,
                raw_model,
            ),
        ).grid(
            row=5,
            column=1,
            sticky="w",
            pady=(8, 0),
        )

        content.columnconfigure(
            1,
            weight=1,
        )

        # -------------------------------------------------
        # Store variables for Save
        # -------------------------------------------------

        self.display_vars.append(
            (
                raw_make,
                raw_model,
                display_make_var,
                display_model_var,
            )
        )


    # =====================================================
    # ACTIONS
    # =====================================================

    def _use_exif(
        self,
        display_make_var: tk.StringVar,
        display_model_var: tk.StringVar,
        raw_make: str,
        raw_model: str,
    ) -> None:

        display_make_var.set(raw_make)
        display_model_var.set(raw_model)

    def _save(self) -> None:

        result = []

        for (
            raw_make,
            raw_model,
            display_make_var,
            display_model_var,
        ) in self.display_vars:

            display_make = display_make_var.get().strip()
            display_model = display_model_var.get().strip()

            if not display_make:
                messagebox.showwarning(
                    "Display Make Required",
                    f"Please enter a display make for:\n"
                    f"{raw_make} / {raw_model}",
                    parent=self,
                )
                return

            if not display_model:
                messagebox.showwarning(
                    "Display Model Required",
                    f"Please enter a display model for:\n"
                    f"{raw_make} / {raw_model}",
                    parent=self,
                )
                return

            result.append(
                (
                    raw_make,
                    raw_model,
                    display_make,
                    display_model,
                )
            )

        self.result = result
        self.destroy()

    def _cancel(self) -> None:

        self.result = None
        self.destroy()
