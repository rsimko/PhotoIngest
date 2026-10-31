from __future__ import annotations

import tkinter as tk

from tkinter import filedialog, messagebox, simpledialog

import ttkbootstrap as ttk

from settings import SettingsManager, Settings

from camera_normalizer import CameraNormalizer, CameraProfile

from constants import RAW_EXTENSIONS


class PreferencesDialog(tk.Toplevel):

    def __init__(
        self,
        parent: tk.Tk,
        settings_manager: SettingsManager,
    ) -> None:

        super().__init__(parent)

        self.settings_manager = settings_manager
        self.settings = settings_manager.load()

        self.title("Preferences")
        self.geometry("760x900")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self.unsaved_changes = False
        self.saved = False

        # -------------------------------------------------
        # General settings
        # -------------------------------------------------

        self.source_var = tk.StringVar(
            value=self.settings.default_source
        )

        self.destination_var = tk.StringVar(
            value=self.settings.default_destination
        )

        self.secondary_destination_var = tk.StringVar(
            value=self.settings.default_backup_destination
        )

        self.duplicate_var = tk.StringVar(
            value=self.settings.duplicate_mode
        )

        self.checksum_var = tk.BooleanVar(
            value=self.settings.verify_checksum
        )

        self.reports_directory_var = tk.StringVar(
            value=self.settings.reports_directory
        )

        self.xmp_naming_var = tk.StringVar(
            value=self.settings.xmp_naming
        )

        self.raw_extensions = list(
            self.settings.raw_extensions
        )

        for variable in (
            self.source_var,
            self.destination_var,
            self.secondary_destination_var,
            self.duplicate_var,
            self.checksum_var,
            self.reports_directory_var,
            self.xmp_naming_var,
        ):
            variable.trace_add(
                "write",
                lambda *_: self._mark_unsaved(),
            )

        # -------------------------------------------------
        # Camera profiles
        # -------------------------------------------------

        self.camera_normalizer = CameraNormalizer()

        self.camera_profiles: list[CameraProfile] = (
            self.camera_normalizer.get_profiles()
        )

        self._build_ui()

        self.protocol(
            "WM_DELETE_WINDOW",
            self._on_close,
        )

    # =====================================================
    # UI
    # =====================================================

    def _build_ui(self):

        body = ttk.Frame(
            self,
            padding=15,
        )

        body.pack(
            fill="both",
            expand=True,
        )

        notebook = ttk.Notebook(body)
        notebook.pack(
            fill="both",
            expand=True,
        )

        general_tab = ttk.Frame(
            notebook,
            padding=15,
        )

        camera_tab = ttk.Frame(
            notebook,
            padding=15,
        )

        notebook.add(
            general_tab,
            text="General",
        )

        notebook.add(
            camera_tab,
            text="Camera Profiles",
        )

        self._build_general_tab(general_tab)
        self._build_camera_profiles_tab(camera_tab)

    # =====================================================
    # GENERAL TAB
    # =====================================================

    def _build_general_tab(self, body):

        # -------------------------------------------------
        # Default Source
        # -------------------------------------------------

        ttk.Label(
            body,
            text="Default Source Folder",
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 5),
        )

        ttk.Entry(
            body,
            textvariable=self.source_var,
            width=60,
        ).grid(
            row=1,
            column=0,
            sticky="ew",
        )

        ttk.Button(
            body,
            text="Browse...",
            command=self._browse_source,
        ).grid(
            row=1,
            column=1,
            padx=(8, 0),
        )

        # -------------------------------------------------
        # Default Destination
        # -------------------------------------------------

        ttk.Label(
            body,
            text="Default Destination Folder",
        ).grid(
            row=2,
            column=0,
            sticky="w",
            pady=(15, 5),
        )

        ttk.Entry(
            body,
            textvariable=self.destination_var,
            width=60,
        ).grid(
            row=3,
            column=0,
            sticky="ew",
        )

        ttk.Button(
            body,
            text="Browse...",
            command=self._browse_destination,
        ).grid(
            row=3,
            column=1,
            padx=(8, 0),
        )

        # -------------------------------------------------
        # Default Backup Destination
        # -------------------------------------------------

        ttk.Label(
            body,
            text="Default Backup Destination",
        ).grid(
            row=4,
            column=0,
            sticky="w",
            pady=(15, 5),
        )

        ttk.Entry(
            body,
            textvariable=self.secondary_destination_var,
            width=60,
        ).grid(
            row=5,
            column=0,
            sticky="ew",
        )

        ttk.Button(
            body,
            text="Browse...",
            command=self._browse_secondary_destination,
        ).grid(
            row=5,
            column=1,
            padx=(8, 0),
        )

        # -------------------------------------------------
        # Reports Folder
        # -------------------------------------------------

        ttk.Label(
            body,
            text="Reports Folder",
        ).grid(
            row=6,
            column=0,
            sticky="w",
            pady=(15, 5),
        )

        ttk.Entry(
            body,
            textvariable=self.reports_directory_var,
            width=60,
        ).grid(
            row=7,
            column=0,
            sticky="ew",
        )

        ttk.Button(
            body,
            text="Browse...",
            command=self._browse_reports,
        ).grid(
            row=7,
            column=1,
            padx=(8, 0),
        )

        # -------------------------------------------------
        # XMP Naming
        # -------------------------------------------------

        xmp_frame = ttk.LabelFrame(
            body,
            text="XMP sidecar naming",
            relief="flat",
        )

        xmp_frame.grid(
            row=8,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(20, 10),
        )

        xmp_inner = ttk.Frame(
            xmp_frame,
            padding=10,
        )

        xmp_inner.pack(
            fill="both",
            expand=True,
        )

        ttk.Radiobutton(
            xmp_inner,
            text="Keep RAW extension     DSF8721.RAF.xmp",
            variable=self.xmp_naming_var,
            value="keep_extension",
        ).pack(
            anchor="w",
            pady=(0, 8),
        )

        ttk.Radiobutton(
            xmp_inner,
            text="Remove RAW extension   DSF8721.xmp",
            variable=self.xmp_naming_var,
            value="remove_extension",
        ).pack(
            anchor="w",
        )

        # -------------------------------------------------
        # Duplicate Handling
        # -------------------------------------------------

        duplicate_frame = ttk.LabelFrame(
            body,
            text="Duplicate handling",
            relief="flat",
            pady=10,
        )

        duplicate_frame.grid(
            row=9,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(20, 10),
        )

        ttk.Radiobutton(
            duplicate_frame,
            text="Skip duplicates",
            variable=self.duplicate_var,
            value="skip",
        ).pack(
            anchor="w",
            pady=(0, 8),
        )

        ttk.Radiobutton(
            duplicate_frame,
            text="Rename automatically",
            variable=self.duplicate_var,
            value="rename",
        ).pack(
            anchor="w",
            pady=(0, 8),
        )

        ttk.Radiobutton(
            duplicate_frame,
            text="Review duplicates",
            variable=self.duplicate_var,
            value="review",
        ).pack(
            anchor="w",
        )

        # -------------------------------------------------
        # Checksum
        # -------------------------------------------------

        ttk.Checkbutton(
            body,
            text="Verify checksum after copy",
            variable=self.checksum_var,
        ).grid(
            row=10,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(5, 15),
        )

        # -------------------------------------------------
        # RAW File Extensions
        # -------------------------------------------------

        raw_frame = ttk.LabelFrame(
            body,
            text="RAW file extensions",
            relief="flat",
        )

        raw_frame.grid(
            row=11,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(5, 10),
        )

        raw_inner = ttk.Frame(
            raw_frame,
            padding=10,
        )

        raw_inner.pack(
            fill="both",
            expand=True,
        )

        raw_list_frame = ttk.Frame(raw_inner)

        raw_list_frame.pack(
            side="left",
            fill="both",
            expand=True,
        )

        self.raw_extensions_listbox = tk.Listbox(
            raw_list_frame,
            height=4,
            exportselection=False,
        )

        self.raw_extensions_listbox.pack(
            side="left",
            fill="both",
            expand=True,
        )

        raw_scrollbar = ttk.Scrollbar(
            raw_list_frame,
            orient="vertical",
            command=self.raw_extensions_listbox.yview,
        )

        raw_scrollbar.pack(
            side="right",
            fill="y",
        )

        self.raw_extensions_listbox.configure(
            yscrollcommand=raw_scrollbar.set,
        )

        raw_buttons = ttk.Frame(raw_inner)

        raw_buttons.pack(
            side="left",
            fill="y",
            padx=(10, 0),
        )

        ttk.Button(
            raw_buttons,
            text="Add",
            width=10,
            command=self._add_raw_extension,
        ).pack(
            pady=(0, 5),
        )

        ttk.Button(
            raw_buttons,
            text="Remove",
            width=10,
            command=self._remove_raw_extension,
        ).pack(
            pady=(0, 5),
        )

        ttk.Button(
            raw_buttons,
            text="Reset",
            width=10,
            command=self._reset_raw_extensions,
        ).pack()

        for extension in self.raw_extensions:
            self.raw_extensions_listbox.insert(
                "end",
                extension,
            )

        # -------------------------------------------------
        # Save Status
        # -------------------------------------------------

        self.save_status_var = tk.StringVar(value="")

        ttk.Label(
            body,
            textvariable=self.save_status_var,
            bootstyle="success",
        ).grid(
            row=12,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(5, 0),
        )

        # -------------------------------------------------
        # Buttons
        # -------------------------------------------------

        button_frame = ttk.Frame(body)

        button_frame.grid(
            row=13,
            column=0,
            columnspan=2,
            sticky="e",
            pady=(10, 0),
        )

        ttk.Button(
            button_frame,
            text="Cancel",
            command=self._cancel,
        ).pack(
            side="left",
            padx=(0, 10),
        )

        ttk.Button(
            button_frame,
            text="Save",
            command=self._save,
        ).pack(
            side="left",
            padx=(0, 10),
        )

        ttk.Button(
            button_frame,
            text="Save & Close",
            bootstyle="success",
            command=self._save_and_close,
        ).pack(
            side="left",
        )

        # -------------------------------------------------
        # Layout
        # -------------------------------------------------

        body.columnconfigure(
            0,
            weight=1,
        )

    # =====================================================
    # CAMERA PROFILES TAB
    # =====================================================

    def _build_camera_profiles_tab(self, body):

        ttk.Label(
            body,
            text="Camera Profiles",
            font=("TkDefaultFont", 11, "bold"),
        ).pack(
            anchor="w",
        )

        ttk.Label(
            body,
            text=(
                "Map raw EXIF camera names to clean display names "
                "used by templates."
            ),
        ).pack(
            anchor="w",
            pady=(2, 12),
        )

        # -------------------------------------------------
        # Table
        # -------------------------------------------------

        table_frame = ttk.Frame(body)

        table_frame.pack(
            fill="both",
            expand=True,
        )

        columns = (
            "raw_make",
            "raw_model",
            "display_make",
            "display_model",
        )

        self.profile_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=12,
            selectmode="browse",
        )

        self.profile_tree.heading(
            "raw_make",
            text="Raw Make",
        )

        self.profile_tree.heading(
            "raw_model",
            text="Raw Model",
        )

        self.profile_tree.heading(
            "display_make",
            text="Display Make",
        )

        self.profile_tree.heading(
            "display_model",
            text="Display Model",
        )

        self.profile_tree.column(
            "raw_make",
            width=150,
            anchor="w",
        )

        self.profile_tree.column(
            "raw_model",
            width=190,
            anchor="w",
        )

        self.profile_tree.column(
            "display_make",
            width=120,
            anchor="w",
        )

        self.profile_tree.column(
            "display_model",
            width=150,
            anchor="w",
        )

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=self.profile_tree.yview,
        )

        self.profile_tree.configure(
            yscrollcommand=scrollbar.set,
        )

        self.profile_tree.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar.pack(
            side="right",
            fill="y",
        )

        self.profile_tree.bind(
            "<Double-1>",
            lambda event: self._edit_profile(),
        )

        # -------------------------------------------------
        # Profile buttons
        # -------------------------------------------------

        profile_buttons = ttk.Frame(body)

        profile_buttons.pack(
            fill="x",
            pady=(12, 0),
        )

        ttk.Button(
            profile_buttons,
            text="New",
            command=self._new_profile,
        ).pack(
            side="left",
        )

        ttk.Button(
            profile_buttons,
            text="Edit",
            command=self._edit_profile,
        ).pack(
            side="left",
            padx=(6, 0),
        )

        ttk.Button(
            profile_buttons,
            text="Delete",
            command=self._delete_profile,
        ).pack(
            side="left",
            padx=(6, 0),
        )

        # -------------------------------------------------
        # Save Status
        # -------------------------------------------------

        self.camera_save_status_var = tk.StringVar(value="")

        ttk.Label(
            body,
            textvariable=self.camera_save_status_var,
            bootstyle="success",
        ).pack(
            anchor="w",
            pady=(10, 0),
        )

        # -------------------------------------------------
        # Bottom buttons
        # -------------------------------------------------

        bottom = ttk.Frame(body)

        bottom.pack(
            fill="x",
            pady=(15, 0),
        )

        ttk.Button(
            bottom,
            text="Cancel",
            command=self._cancel,
        ).pack(
            side="right",
            padx=(0, 10),
        )

        ttk.Button(
            bottom,
            text="Save",
            command=self._save,
        ).pack(
            side="right",
            padx=(0, 10),
        )

        ttk.Button(
            bottom,
            text="Save & Close",
            bootstyle="success",
            command=self._save_and_close,
        ).pack(
            side="right",
        )

        self._refresh_profile_tree()

    # =====================================================
    # PROFILE TABLE
    # =====================================================

    def _refresh_profile_tree(self):

        for child in self.profile_tree.get_children():
            self.profile_tree.delete(child)

        for index, profile in enumerate(self.camera_profiles):

            self.profile_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    profile.raw_make,
                    profile.raw_model,
                    profile.display_make,
                    profile.display_model,
                ),
            )

    def _selected_profile_index(self) -> int | None:

        selection = self.profile_tree.selection()

        if not selection:
            return None

        try:
            return int(selection[0])

        except ValueError:
            return None

    # =====================================================
    # NEW PROFILE
    # =====================================================

    def _new_profile(self):

        result = self._profile_editor()

        if result is None:
            return

        if self._profile_exists(
            result.raw_make,
            result.raw_model,
        ):

            messagebox.showerror(
                "Duplicate Camera Profile",
                (
                    "A profile for this raw EXIF "
                    "Make / Model already exists."
                ),
                parent=self,
            )

            return

        self.camera_profiles.append(result)

        self._refresh_profile_tree()

        self.profile_tree.selection_set(
            str(len(self.camera_profiles) - 1)
        )

        self._mark_unsaved()

    # =====================================================
    # EDIT PROFILE
    # =====================================================

    def _edit_profile(self):

        index = self._selected_profile_index()

        if index is None:
            messagebox.showinfo(
                "Edit Camera Profile",
                "Select a camera profile first.",
                parent=self,
            )

            return

        current = self.camera_profiles[index]

        result = self._profile_editor(current)

        if result is None:
            return

        for other_index, profile in enumerate(
            self.camera_profiles
        ):

            if other_index == index:
                continue

            if (
                self._normalize_key(profile.raw_make)
                == self._normalize_key(result.raw_make)
                and
                self._normalize_key(profile.raw_model)
                == self._normalize_key(result.raw_model)
            ):

                messagebox.showerror(
                    "Duplicate Camera Profile",
                    (
                        "Another profile already uses this "
                        "raw EXIF Make / Model."
                    ),
                    parent=self,
                )

                return

        self.camera_profiles[index] = result

        self._refresh_profile_tree()

        self.profile_tree.selection_set(
            str(index)
        )

        self._mark_unsaved()

    # =====================================================
    # DELETE PROFILE
    # =====================================================

    def _delete_profile(self):

        index = self._selected_profile_index()

        if index is None:
            messagebox.showinfo(
                "Delete Camera Profile",
                "Select a camera profile first.",
                parent=self,
            )

            return

        profile = self.camera_profiles[index]

        confirmed = messagebox.askyesno(
            "Delete Camera Profile",
            (
                "Delete this camera profile?\n\n"
                f"{profile.raw_make} / "
                f"{profile.raw_model}"
            ),
            parent=self,
        )

        if not confirmed:
            return

        del self.camera_profiles[index]

        self._refresh_profile_tree()

        self._mark_unsaved()

    # =====================================================
    # PROFILE EDITOR
    # =====================================================

    def _profile_editor(
        self,
        profile: CameraProfile | None = None,
    ) -> CameraProfile | None:

        dialog = CameraProfileDialog(
            self,
            profile,
        )

        self.wait_window(dialog)

        return dialog.result

    # =====================================================
    # PROFILE HELPERS
    # =====================================================

    def _profile_exists(
        self,
        raw_make: str,
        raw_model: str,
    ) -> bool:

        raw_make_key = self._normalize_key(raw_make)
        raw_model_key = self._normalize_key(raw_model)

        for profile in self.camera_profiles:

            if (
                self._normalize_key(profile.raw_make)
                == raw_make_key
                and
                self._normalize_key(profile.raw_model)
                == raw_model_key
            ):

                return True

        return False

    @staticmethod
    def _normalize_key(value: str) -> str:

        return " ".join(
            value.strip().split()
        ).lower()

    # =====================================================
    # BROWSERS
    # =====================================================

    def _browse_source(self):

        folder = filedialog.askdirectory(
            initialdir=self.source_var.get(),
        )

        if folder:
            self.source_var.set(folder)

    def _browse_destination(self):

        folder = filedialog.askdirectory(
            initialdir=self.destination_var.get(),
        )

        if folder:
            self.destination_var.set(folder)

    def _browse_secondary_destination(self):

        folder = filedialog.askdirectory(
            initialdir=self.secondary_destination_var.get(),
        )

        if folder:
            self.secondary_destination_var.set(folder)

    def _browse_reports(self):

        folder = filedialog.askdirectory(
            initialdir=self.reports_directory_var.get(),
        )

        if folder:
            self.reports_directory_var.set(folder)

    def _mark_unsaved(self):

        if self.unsaved_changes:
            return

        self.unsaved_changes = True
        self.title("Preferences *")

    def _cancel(self):

        if not self.unsaved_changes:
            self.destroy()
            return

        confirmed = messagebox.askyesno(
            "Discard Changes?",
            "You have unsaved changes.\n\n"
            "Are you sure you want to discard them?",
            parent=self,
        )

        if confirmed:
            self.destroy()

    # =====================================================
    # RAW EXTENSIONS
    # =====================================================

    def _add_raw_extension(self):

        extension = simpledialog.askstring(
            "Add RAW Extension",
            "Enter file extension:",
            parent=self,
        )

        if extension is None:
            return

        extension = extension.strip().lower()

        if not extension:
            return

        if not extension.startswith("."):
            extension = "." + extension

        if extension in self.raw_extensions:
            messagebox.showinfo(
                "RAW Extension",
                f"{extension} is already in the list.",
                parent=self,
            )
            return

        self.raw_extensions.append(extension)
        self.raw_extensions.sort()

        self.raw_extensions_listbox.delete(
            0,
            "end",
        )

        for value in self.raw_extensions:
            self.raw_extensions_listbox.insert(
                "end",
                value,
            )

        self._mark_unsaved()

    def _remove_raw_extension(self):

        selection = self.raw_extensions_listbox.curselection()

        if not selection:
            return

        index = selection[0]

        self.raw_extensions_listbox.delete(index)

        self.raw_extensions = [
            self.raw_extensions_listbox.get(i)
            for i in range(
                self.raw_extensions_listbox.size()
            )
        ]

        self._mark_unsaved()

    def _reset_raw_extensions(self):

        self.raw_extensions = list(RAW_EXTENSIONS)
        self.raw_extensions.sort()

        self.raw_extensions_listbox.delete(
            0,
            "end",
        )

        for extension in self.raw_extensions:
            self.raw_extensions_listbox.insert(
                "end",
                extension,
            )

        self._mark_unsaved()

    # =====================================================
    # SAVE
    # =====================================================

    def _save(self) -> bool:

        updated = Settings(
            default_source=self.source_var.get(),
            default_destination=self.destination_var.get(),
            default_backup_destination=self.secondary_destination_var.get(),
            last_template=self.settings.last_template,
            duplicate_mode=self.duplicate_var.get(),
            verify_checksum=self.checksum_var.get(),
            window_width=self.settings.window_width,
            window_height=self.settings.window_height,
            reports_directory=self.reports_directory_var.get(),
            xmp_naming=self.xmp_naming_var.get(),
            raw_extensions=self.raw_extensions,
        )

        self.settings_manager.save(updated)

        try:

            self.camera_normalizer.profiles = {
                (
                    self._normalize_key(profile.raw_make),
                    self._normalize_key(profile.raw_model),
                ): profile
                for profile in self.camera_profiles
            }

            self.camera_normalizer._save_profiles()

        except Exception as e:

            messagebox.showerror(
                "Save Error",
                f"Could not save camera profiles:\n\n{e}",
                parent=self,
            )

            return False

        self.unsaved_changes = False
        self.saved = True
        self.title("Preferences")

        self.save_status_var.set(
            "Preferences saved."
        )

        self.camera_save_status_var.set(
            "Camera profiles saved."
        )

        self.after(
            2000,
            lambda: self.save_status_var.set("")
        )

        self.after(
            2000,
            lambda: self.camera_save_status_var.set("")
        )

        return True

    def _save_and_close(self):

        if self._save():
            self.destroy()

    # =====================================================
    # CLOSE
    # =====================================================

    def _on_close(self):

        if not self.unsaved_changes:
            self.destroy()
            return

        result = messagebox.askyesnocancel(
            "Unsaved Changes",
            "You have unsaved changes.\n\n"
            "Would you like to save them before closing?",
            parent=self,
        )

        if result is None:
            return

        if result:
            if self._save():
                self.destroy()
        else:
            self.destroy()


# =========================================================
# CAMERA PROFILE DIALOG
# =========================================================


class CameraProfileDialog(tk.Toplevel):

    def __init__(
        self,
        parent,
        profile: CameraProfile | None = None,
    ) -> None:

        super().__init__(parent)

        self.result: CameraProfile | None = None

        self.title(
            "Edit Camera Profile"
            if profile
            else "New Camera Profile"
        )

        self.geometry("560x330")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self.raw_make_var = tk.StringVar(
            value=profile.raw_make if profile else ""
        )

        self.raw_model_var = tk.StringVar(
            value=profile.raw_model if profile else ""
        )

        self.display_make_var = tk.StringVar(
            value=profile.display_make if profile else ""
        )

        self.display_model_var = tk.StringVar(
            value=profile.display_model if profile else ""
        )

        self._build_ui()

    # =====================================================
    # UI
    # =====================================================

    def _build_ui(self):

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
            text="Raw EXIF identity",
            font=("TkDefaultFont", 10, "bold"),
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 10),
        )

        self._add_field(
            body,
            1,
            "Raw Make",
            self.raw_make_var,
        )

        self._add_field(
            body,
            2,
            "Raw Model",
            self.raw_model_var,
        )

        ttk.Separator(body).grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=15,
        )

        ttk.Label(
            body,
            text="Display identity",
            font=("TkDefaultFont", 10, "bold"),
        ).grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(0, 10),
        )

        self._add_field(
            body,
            5,
            "Display Make",
            self.display_make_var,
        )

        self._add_field(
            body,
            6,
            "Display Model",
            self.display_model_var,
        )

        buttons = ttk.Frame(body)

        buttons.grid(
            row=7,
            column=0,
            columnspan=2,
            sticky="e",
            pady=(20, 0),
        )

        ttk.Button(
            buttons,
            text="Cancel",
            command=self._cancel,
        ).pack(
            side="left",
            padx=(0, 8),
        )

        ttk.Button(
            buttons,
            text="Save",
            bootstyle="success",
            command=self._accept,
        ).pack(
            side="left",
        )

        body.columnconfigure(
            1,
            weight=1,
        )

    def _add_field(
        self,
        parent,
        row,
        label,
        variable,
    ):

        ttk.Label(
            parent,
            text=label,
        ).grid(
            row=row,
            column=0,
            sticky="w",
            pady=5,
        )

        ttk.Entry(
            parent,
            textvariable=variable,
            width=55,
        ).grid(
            row=row,
            column=1,
            sticky="ew",
            padx=(15, 0),
            pady=5,
        )

    # =====================================================
    # ACCEPT
    # =====================================================

    def _accept(self):

        raw_make = self.raw_make_var.get().strip()
        raw_model = self.raw_model_var.get().strip()
        display_make = self.display_make_var.get().strip()
        display_model = self.display_model_var.get().strip()

        if not raw_make:
            self._error("Raw Make cannot be empty.")
            return

        if not raw_model:
            self._error("Raw Model cannot be empty.")
            return

        if not display_make:
            self._error("Display Make cannot be empty.")
            return

        if not display_model:
            self._error("Display Model cannot be empty.")
            return

        self.result = CameraProfile(
            raw_make=raw_make,
            raw_model=raw_model,
            display_make=display_make,
            display_model=display_model,
        )

        self.destroy()

    def _cancel(self):
        self.destroy()

    def _error(self, message):

        messagebox.showerror(
            "Invalid Camera Profile",
            message,
            parent=self,
        )
