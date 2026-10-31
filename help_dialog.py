from __future__ import annotations

import tkinter as tk
import ttkbootstrap as ttk


class HelpDialog(tk.Toplevel):

    def __init__(
        self,
        parent: tk.Tk,
    ) -> None:

        super().__init__(parent)

        self.title("Photo Ingest Help")
        self.geometry("760x700")
        self.minsize(650, 500)
        self.resizable(True, True)

        self.transient(parent)
        self.grab_set()

        self._build_ui()

        self.protocol(
            "WM_DELETE_WINDOW",
            self._close,
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

        # -------------------------------------------------
        # Scrollable help area
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

        content = ttk.Frame(canvas)

        canvas_window = canvas.create_window(
            (0, 0),
            window=content,
            anchor="nw",
        )

        content.bind(
            "<Configure>",
            lambda event: canvas.configure(
                scrollregion=canvas.bbox("all")
            ),
        )

        def resize_content(event):
            canvas.itemconfigure(
                canvas_window,
                width=event.width,
            )

        canvas.bind(
            "<Configure>",
            resize_content,
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

        content.columnconfigure(0, weight=1)

        # -------------------------------------------------
        # Help content
        # -------------------------------------------------

        self._add_title(
            content,
            "Photo Ingest Help",
        )

        self._add_text(
            content,
            (
                "Photo Ingest is a lightweight application for "
                "ingesting RAW photographs and other supported "
                "media files into an organized destination folder.\n\n"
                "The application scans selected files or folders, "
                "reads available EXIF metadata, applies folder and "
                "filename templates when possible, handles XMP "
                "sidecar files, checks for destination conflicts, "
                "and then copies the files to their planned "
                "destinations.\n\n"
                "Files without usable EXIF metadata are placed "
                "in the Unsorted folder so they can be dealt with "
                "manually later."
            ),
        )

        self._add_section(
            content,
            "Basic Workflow",
            (
                "The normal workflow is:\n\n"
                "1. Add Files or Add Folder\n"
                "2. Select a Destination\n"
                "3. Enter Job Information\n"
                "4. Select or Edit a Template\n"
                "5. Scan\n"
                "6. Review new camera profiles if necessary\n"
                "7. Dry Run\n"
                "8. Copy"
            ),
        )

        self._add_section(
            content,
            "Source",
            (
                "Use Add Files to select individual supported "
                "files, or Add Folder to select a folder containing "
                "supported files.\n\n"
                "Photo Ingest only accepts files whose extensions "
                "are configured in Preferences.\n\n"
                "Use Clear to remove the current source selection."
            ),
        )

        self._add_section(
            content,
            "Supported File Extensions",
            (
                "The list of supported file extensions can be "
                "managed through Preferences without modifying "
                "the application source code.\n\n"
                "Use Add to add a new extension, Remove to remove "
                "the selected extension, or Reset to restore the "
                "built-in default extension list.\n\n"
                "Extensions should include the leading dot, for "
                "example:\n\n"
                ".raf\n"
                ".nef\n"
                ".arw\n\n"
                "The same mechanism can be used to support other "
                "file types, including video files, when their "
                "extensions are added to the configured list."
            ),
        )

        self._add_section(
            content,
            "Destination",
            (
                "Choose the destination folder where the "
                "ingested files will be stored.\n\n"
                "The default destination can be configured in "
                "Preferences."
            ),
        )

        self._add_section(
            content,
            "Backup Destination",
            (
                "An optional backup destination can be enabled "
                "for the ingest.\n\n"
                "When enabled, copied files are also copied to "
                "the configured backup destination.\n\n"
                "The default backup destination can be configured "
                "in Preferences."
            ),
        )

        self._add_section(
            content,
            "Job Information",
            (
                "You can optionally enter:\n\n"
                "• Job Code\n"
                "• Custom Text\n"
                "• Counter\n\n"
                "The counter determines the starting number "
                "used by the filename template."
            ),
        )

        self._add_section(
            content,
            "Templates",
            (
                "Templates define how destination folders and "
                "filenames are created.\n\n"
                "A template contains a Folder template and a "
                "Filename template.\n\n"
                "For example:\n\n"
                "{YYYY}/{job_code}/{MM}/{DD}\n\n"
                "can create a folder structure such as:\n\n"
                "2025/job123/07/12\n\n"
                "Templates can be edited directly in the "
                "Templates panel.\n\n"
                "Save updates the current template.\n"
                "Save As... creates a new template.\n"
                "Delete removes a template.\n\n"
                "At least one template must remain available."
            ),
        )

        self._add_section(
            content,
            "Template Tokens",
            (
                "The Available Tokens buttons insert supported "
                "metadata and naming values into the active "
                "template.\n\n"
                "Available tokens include date and time values, "
                "job information, the original filename, the "
                "counter, and camera make and model.\n\n"
                "Helper buttons are also available for:\n\n"
                "/    _    -\n\n"
                "The Output Preview shows an example of what "
                "the current template will produce."
            ),
        )

        self._add_section(
            content,
            "Scan",
            (
                "Press Scan to inspect the selected source.\n\n"
                "The application finds files with configured "
                "extensions, reads available EXIF metadata, "
                "identifies camera make and model when available, "
                "normalizes camera information, determines "
                "whether XMP sidecars are present, builds the "
                "planned destination paths, and checks for "
                "destination conflicts and duplicate outputs.\n\n"
                "Scanning does not copy files."
            ),
        )

        self._add_section(
            content,
            "Files Without EXIF Data",
            (
                "Some files may not contain usable EXIF metadata. "
                "When the metadata required to construct the "
                "normal folder structure and filename is missing, "
                "Photo Ingest does not attempt to invent those "
                "values.\n\n"
                "Instead, the file is placed directly in an "
                "Unsorted folder below the selected destination "
                "and retains its original filename.\n\n"
                "This allows the ingest to continue while leaving "
                "the file available for manual organization later."
            ),
        )

        self._add_section(
            content,
            "Camera Profiles",
            (
                "Photo Ingest uses camera profiles to translate "
                "the camera identity reported by EXIF into the "
                "display name used by the application.\n\n"
                "When a new camera is encountered, all new "
                "camera identities detected during the scan are "
                "presented together in one dialog.\n\n"
                "The dialog shows the EXIF Make and Model and "
                "provides editable Display Make and Display "
                "Model fields.\n\n"
                "The fields initially contain the EXIF values. "
                "You can edit them or use Use EXIF Values when "
                "the original values are already suitable.\n\n"
                "Save & Continue stores the profiles and "
                "continues the ingest automatically.\n\n"
                "Once a camera has a profile, it will not require "
                "this dialog again unless its profile is removed."
            ),
        )

        self._add_section(
            content,
            "Dry Run",
            (
                "Dry Run shows the planned result without "
                "copying anything.\n\n"
                "It displays the files that will be processed, "
                "planned destinations, XMP destinations, "
                "existing collisions, duplicate outputs, "
                "Unsorted files, and the final ingest plan.\n\n"
                "Use Dry Run to check the result before copying."
            ),
        )

        self._add_section(
            content,
            "XMP Sidecar Files",
            (
                "When a supported file has an associated XMP "
                "sidecar file, Photo Ingest keeps the sidecar "
                "together with the source file.\n\n"
                "The XMP destination follows the renamed file "
                "filename.\n\n"
                "For example:\n\n"
                "original.RAF\n"
                "original.RAF.xmp\n\n"
                "can become:\n\n"
                "new_name.RAF\n"
                "new_name.RAF.xmp"
            ),
        )

        self._add_section(
            content,
            "Duplicate Handling",
            (
                "Photo Ingest can handle destination conflicts "
                "using the configured duplicate handling mode.\n\n"
                "Skip duplicates\n"
                "Existing destination files are skipped.\n\n"
                "Rename automatically\n"
                "A unique filename is generated when a "
                "destination already exists.\n\n"
                "Review duplicates\n"
                "Conflicting files are placed into a review queue "
                "before copying."
            ),
        )

        self._add_section(
            content,
            "Copy",
            (
                "After reviewing the plan, press Copy to begin "
                "the actual ingest.\n\n"
                "Supported files and associated XMP sidecars are "
                "copied where applicable.\n\n"
                "The log records results such as:\n\n"
                "• Copied\n"
                "• Renamed\n"
                "• Skipped\n"
                "• Replaced\n"
                "• Error\n\n"
                "The Copy button changes to Cancel while a copy "
                "operation is running."
            ),
        )

        self._add_section(
            content,
            "Verification",
            (
                "Photo Ingest can verify copied files using "
                "checksum verification.\n\n"
                "This option is controlled through Preferences."
            ),
        )

        self._add_section(
            content,
            "Preferences",
            (
                "Preferences provide application-wide settings "
                "such as:\n\n"
                "• Default Source Folder\n"
                "• Default Destination Folder\n"
                "• Default Backup Destination\n"
                "• Reports Folder\n"
                "• Duplicate Handling\n"
                "• Checksum Verification\n"
                "• XMP Naming\n"
                "• Supported File Extensions\n\n"
                "Changes are saved to the application's settings "
                "file and are used by subsequent sessions."
            ),
        )

        self._add_section(
            content,
            "New Session",
            (
                "New Session clears the current source selection, "
                "log, report association, and ingest plan.\n\n"
                "The saved default source, destination, and backup "
                "destination settings are then restored so the "
                "application is ready for a new ingest."
            ),
        )

        self._add_section(
            content,
            "Log",
            (
                "The Log output panel provides a running record "
                "of the current session.\n\n"
                "It includes information such as session start, "
                "selected sources, destination, job information, "
                "scan results, collision information, Dry Run "
                "results, and copy results.\n\n"
                "The copy summary includes the number of files "
                "copied, XMP files copied, backup results, renamed "
                "and skipped files, errors, and files placed in "
                "Unsorted."
            ),
        )

        self._add_section(
            content,
            "Reports",
            (
                "Photo Ingest creates a report containing the "
                "ingest information and copy results.\n\n"
                "The copy results include the individual file "
                "operations and a final summary, including the "
                "number of files placed in Unsorted."
            ),
        )

        self._add_section(
            content,
            "Recommended Workflow",
            (
                "For important jobs, the recommended workflow is:\n\n"
                "Add source → Check destination → Select template "
                "→ Enter job information → Scan → Resolve new "
                "camera profiles if necessary → Dry Run → Review "
                "the plan → Copy\n\n"
                "Dry Run is especially useful for catching "
                "unexpected folder structures, filenames, "
                "destination conflicts, or files that will be "
                "placed in Unsorted before anything is copied."
            ),
        )

        # -------------------------------------------------
        # Close button
        # -------------------------------------------------

        button_frame = ttk.Frame(body)
        button_frame.pack(
            fill="x",
            pady=(12, 0),
        )

        ttk.Button(
            button_frame,
            text="Close",
            command=self._close,
        ).pack(
            side="right",
        )

    # =====================================================
    # CONTENT HELPERS
    # =====================================================

    def _add_title(
        self,
        parent,
        text: str,
    ) -> None:

        ttk.Label(
            parent,
            text=text,
            font=("TkDefaultFont", 18, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 15),
        )

    def _add_section(
        self,
        parent,
        title: str,
        text: str,
    ) -> None:

        row = parent.grid_size()[1]

        ttk.Label(
            parent,
            text=title,
            font=("TkDefaultFont", 12, "bold"),
        ).grid(
            row=row,
            column=0,
            sticky="w",
            pady=(12, 4),
        )

        ttk.Label(
            parent,
            text=text,
            justify="left",
            anchor="w",
            wraplength=680,
        ).grid(
            row=row + 1,
            column=0,
            sticky="ew",
            pady=(0, 4),
        )

    def _add_text(
        self,
        parent,
        text: str,
    ) -> None:

        row = parent.grid_size()[1]

        ttk.Label(
            parent,
            text=text,
            justify="left",
            anchor="w",
            wraplength=680,
        ).grid(
            row=row,
            column=0,
            sticky="ew",
            pady=(0, 8),
        )

    # =====================================================
    # CLOSE
    # =====================================================

    def _close(self) -> None:

        self.grab_release()
        self.destroy()
