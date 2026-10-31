from __future__ import annotations
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import subprocess
from ttkbootstrap import Bootstyle
from settings import SettingsManager
from templates import TemplateManager
from scanner import Scanner
from planner import Planner
from copier import Copier
from constants import APP_NAME, APP_VERSION
from models import SourceInput
from pathlib import Path
from constants import RAW_EXTENSIONS
from constants import TOKENS
from datetime import datetime
from template_engine import TemplateEngine, TemplateContext
from typing import Any
import time
from preferences_dialog import PreferencesDialog
from review_dialog import ReviewDialog
from camera_profile_dialog import CameraProfileDialog
from help_dialog import HelpDialog
from report_manager import ReportManager


class PhotoIngestUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root

        # Tell Tk the application name (mainly for macOS)
        try:
            self.root.tk.call("tk", "appname", APP_NAME)
        except Exception:
            pass

        # ---------------- CORE ----------------
        self.current_report_path = None
        self.settings_manager = SettingsManager()
        self.settings = self.settings_manager.load()

        self.template_manager = TemplateManager()
        self.templates = self.template_manager.load()

        self.scanner = Scanner(
            raw_extensions=set(
                self.settings.raw_extensions
            )
        )

        self.scanner.on_event = (
            lambda event, data:
                self.root.after(
                    0,
                    lambda e=event, d=data: self._handle_scan_event(e, d)
                )
        )
        self.planner = Planner()
        self.planner.progress_callback = self._planner_progress
        self.planner.unknown_camera_callback = (
            self._unknown_camera_profile
        )
        self.engine = TemplateEngine()

        self.current_plan = None

        self.session_header_logged = False

        self.manifest_entries = []

        # ---------------- STATE ----------------
        self.root.title(f"{APP_NAME} {APP_VERSION}")

        self.selected_files: list[str] = []

        # ---------------- BUILD UI ----------------
        self._build_ui()
        self._apply_initial_state()
        self._set_default_source()

        # ---------------- COPIER (after UI exists) ----------------
        self.copier = Copier(
            logger=self._log,
            verify_checksum=self.settings.verify_checksum,
        )
        self.progress_var = tk.StringVar(value="")

        # ================= TEMPLATE TOKENS ===================
        self.active_template_entry = self.folder_template_entry

        # ================= REPORT MANAGER ===================
        self.report_manager = ReportManager(
            self.settings.reports_directory
        )


    # =========================================================
    # UI BUILD
    # =========================================================
    def _build_ui(self) -> None:
        self.root.geometry(
            f"{self.settings.window_width}x{self.settings.window_height}"
        )
        # =====================================================
        # ROOT LAYOUT
        # =====================================================
        self.main = ttk.Frame(self.root, padding=20)
        self.main.pack(fill="both", expand=True)

        self.main.columnconfigure(
            0,
            weight=5,
            uniform="main_panels",
        )

        self.main.columnconfigure(
            1,
            weight=4,
            uniform="main_panels",
        )

        self.main.columnconfigure(0, weight=1)
        self.main.columnconfigure(1, weight=1)

        self._build_source_panel(self.main)
        self._build_template_panel(self.main)
        self._build_progress_bar(self.main)
        self._build_log_panel(self.main)
        self._build_action_buttons(self.main)
        self._build_status_bar(self.main)

    # =========================================================
    # ==================    UI BUILDERS    ====================
    # =========================================================

    def _build_source_panel(self, parent):

        left = ttk.LabelFrame(
            parent,
            text="Source & destination",
            padding=10,
        )

        left.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 5),
        )

        # -------------------------------------------------
        # Layout
        # -------------------------------------------------

        left.columnconfigure(
            0,
            weight=1,
        )

        left.columnconfigure(
            1,
            weight=0,
        )


        # =====================================================
        # INPUT LIST
        # =====================================================

        self.file_listbox = tk.Listbox(
            left,
            height=5,
        )

        self.file_listbox.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="nsew",
            pady=(5, 5),
        )

        # =====================================================
        # ACTION BUTTONS
        # =====================================================

        btn_frame = ttk.Frame(left)

        btn_frame.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
        )

        self.add_files_button = ttk.Button(
            btn_frame,
            text="Add Files",
            command=self._add_files,
            width=10,
        )

        self.add_files_button.pack(
            side="left",
            padx=(5, 0),
        )

        self.add_folder_button = ttk.Button(
            btn_frame,
            text="Add Folder",
            command=self._add_folder,
            width=10,
        )

        self.add_folder_button.pack(
            side="left",
            padx=(5, 0),
        )

        self.clear_button = ttk.Button(
            btn_frame,
            text="Clear",
            command=self._clear_files,
            width=10,
        )

        self.clear_button.pack(
            side="right",
            padx=(5, 0),
        )

        # =====================================================
        # PRIMARY DESTINATION
        # =====================================================

        ttk.Label(
            left,
            text="Destination folder",
        ).grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(10, 0),
        )

        self.dest_var = tk.StringVar(
            value=self.settings.default_destination,
        )

        self.dest_var.trace_add(
            "write",
            lambda *_: self._invalidate_ingest_plan(),
        )

        ttk.Entry(
            left,
            textvariable=self.dest_var,
        ).grid(
            row=4,
            column=0,
            sticky="ew",
            padx=(0, 6),
        )

        ttk.Button(
            left,
            text="Browse",
            command=self._browse_destination,
        ).grid(
            row=4,
            column=1,
            sticky="ew",
            padx=(0, 6),
        )

        # =====================================================
        # BACKUP
        # =====================================================

        self.backup_enabled_var = tk.BooleanVar(
            value=False,
        )

        self.backup_enabled_var.trace_add(
            "write",
            lambda *_: self._backup_settings_changed(),
        )

        self.backup_enabled_check = ttk.Checkbutton(
            left,
            text="Enable backup destination",
            variable=self.backup_enabled_var,
            command=self._update_backup_controls,
        )

        self.backup_enabled_check.grid(
            row=5,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(10, 0),
        )

        ttk.Label(
            left,
            text="Backup destination folder",
        ).grid(
            row=6,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(5, 0),
        )

        self.backup_dest_var = tk.StringVar(
            value=self.settings.default_backup_destination,
        )

        self.backup_dest_var.trace_add(
            "write",
            lambda *_: self._invalidate_ingest_plan(),
        )

        self.backup_dest_entry = ttk.Entry(
            left,
            textvariable=self.backup_dest_var,
        )

        self.backup_dest_entry.grid(
            row=7,
            column=0,
            sticky="ew",
            padx=(0, 6),
        )

        self.backup_browse_button = ttk.Button(
            left,
            text="Browse",
            command=self._browse_backup_destination,
        )

        self.backup_browse_button.grid(
            row=7,
            column=1,
            sticky="ew",
        )

        # =====================================================
        # JOB
        # =====================================================

        ttk.Label(
            left,
            text="Job Code",
        ).grid(
            row=8,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(10, 0),
        )

        self.job_var = tk.StringVar()

        self.job_var.trace_add(
            "write",
            lambda *_: self._invalidate_ingest_plan(),
        )

        ttk.Entry(
            left,
            textvariable=self.job_var,
        ).grid(
            row=9,
            column=0,
            columnspan=2,
            sticky="ew",
        )

        # =====================================================
        # CUSTOM
        # =====================================================

        ttk.Label(
            left,
            text="Custom Text",
        ).grid(
            row=10,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(10, 0),
        )

        self.custom_var = tk.StringVar()

        self.custom_var.trace_add(
            "write",
            lambda *_: self._invalidate_ingest_plan(),
        )

        ttk.Entry(
            left,
            textvariable=self.custom_var,
        ).grid(
            row=11,
            column=0,
            columnspan=2,
            sticky="ew",
        )

        # =====================================================
        # COUNTER
        # =====================================================

        ttk.Label(
            left,
            text="Counter",
        ).grid(
            row=12,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(10, 0),
        )

        self.counter_var = tk.IntVar(
            value=1,
        )

        self.counter_var.trace_add(
            "write",
            lambda *_: self._invalidate_ingest_plan(),
        )

        ttk.Spinbox(
            left,
            from_=1,
            to=999999,
            textvariable=self.counter_var,
            width=10,
        ).grid(
            row=13,
            column=0,
            sticky="w",
        )

        # =====================================================
        # INITIAL BACKUP STATE
        # =====================================================

        self._update_backup_controls()

    def _build_template_panel(self,parent):
        right = ttk.LabelFrame(
            parent,
            text="Templates",
            padding=10
        )
        right.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        right.columnconfigure(0, weight=1)

        self.template_var = tk.StringVar(value=self.settings.last_template)

        self.template_combo = ttk.Combobox(
            right,
            values=[t.name for t in self.templates],
            textvariable=self.template_var,
            state="readonly"
        )
        self.template_combo.grid(row=0, column=0, sticky="ew")
        self.template_combo.bind("<<ComboboxSelected>>", self._on_template_change)

        self.folder_template_var = tk.StringVar()
        self.filename_template_var = tk.StringVar()

        # ===== TOKEN STUFF =========
        ttk.Label(right, text="Folder").grid(row=1, column=0, sticky="w")

        self.folder_template_entry = ttk.Entry(
            right,
            font=("Menlo", 10),
            textvariable=self.folder_template_var
        )
        self.folder_template_entry.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(0, 12),
        )

        ttk.Label(right, text="Filename").grid(row=3, column=0, sticky="w")

        self.filename_template_entry = ttk.Entry(
            right,
            font=("Menlo", 10 ),
            textvariable=self.filename_template_var
        )
        self.filename_template_entry.grid(
            row=4,
            column=0,
            sticky="ew",
            pady=(0, 10)
        )

        self.folder_template_entry.bind(
            "<FocusIn>",
            self._set_active_template_entry
        )

        self.filename_template_entry.bind(
            "<FocusIn>",
            self._set_active_template_entry
        )

        # ================= TEMPLATE BUTTONS =================

        button_frame = ttk.Frame(right)
        button_frame.grid(
            row=6,
            column=0,
            sticky="w",
            pady=(12, 0),
        )

        self.save_template_button = ttk.Button(
            button_frame,
            text="Save",
            command=self._save_template,
            width=10,
        )
        self.save_template_button.pack(
            side="left",
            padx=(0, 5),
        )

        self.save_as_button = ttk.Button(
            button_frame,
            text="Save As...",
            command=self._save_template_as,
            width=10,
        )
        self.save_as_button.pack(
            side="left",
            padx=(0, 5),
        )

        self.delete_template_button = ttk.Button(
            button_frame,
            text="Delete",
            command=self._delete_template,
            width=10,
        )
        self.delete_template_button.pack(
            side="left",
            padx=(0, 5),
        )

        self.clear_template_button = ttk.Button(
            button_frame,
            text="Clear",
            width=10,
            command=self._clear_active_template,
        )
        self.clear_template_button.pack(
            side="left",
        )

        # ================= AVAILABLE TOKENS =================

        token_frame = ttk.LabelFrame(
            right,
            text="Available Tokens",
            padding=0,
            relief="flat",
        )
        token_frame.grid(
            row=7,
            column=0,
            sticky="ew",
            pady=(15, 15),
        )

        cols = 4

        # IMPORTANT: prevent columns stretching
        for c in range(cols):
            token_frame.columnconfigure(c, weight=0)

        for i, token in enumerate(TOKENS):
            r = i // cols
            c = i % cols

            ttk.Button(
                token_frame,
                text=token,
                width=10,
                command=lambda t=token: self._insert_token(t),
                bootstyle="secondary",
            ).grid(
                row=r,
                column=c,
                padx=2,
                pady=2,
                sticky="w",
            )

        helper_buttons = [
            ("/", "/"),
            ("_", "_"),
            ("-", "-"),
        ]

        start = len(TOKENS)

        for i, (text, value) in enumerate(helper_buttons):

            index = start + i

            r = index // cols
            c = index % cols

            button = ttk.Button(
                token_frame,
                text=text,
                width=10,
                bootstyle="secondary",
                command=lambda v=value: self._insert_token(v),
            )

            button.grid(
                row=r,
                column=c,
                padx=2,
                pady=2,
                sticky="w",
            )

            if value == "/":
                self.slash_helper_button = button


        # =============== TEMPLATE PREVIEW ===============
        self.folder_preview_var = tk.StringVar()
        self.filename_preview_var = tk.StringVar()

        ttk.Label(right, text="Output Preview").grid(
            row=9,
            column=0,
            sticky="w",
            pady=(10, 0)
        )

        preview_frame = ttk.Frame(right)
        preview_frame.grid(
            row=10,
            column=0,
            sticky="ew",
            pady=(5, 0)
        )

        preview_frame.columnconfigure(0, weight=1)

        #ttk.Label(
        #    preview_frame,
        #    text="Folder:",
        #).grid(row=0, column=0, sticky="w")

        ttk.Label(
            preview_frame,
            font=("Menlo", 10),
            textvariable=self.folder_preview_var,
        ).grid(row=1, column=0, sticky="w", pady=(0, 6))

        #ttk.Label(
        #    preview_frame,
        #    text="Filename:",
        #).grid(row=2, column=0, sticky="w")

        ttk.Label(
            preview_frame,
            font=("Menlo", 10),
            textvariable=self.filename_preview_var,
        ).grid(row=3, column=0, sticky="w")

        # =========================================================
        # LIVE PREVIEW
        # =========================================================

        self.folder_template_var.trace_add("write", self._update_preview)
        self.filename_template_var.trace_add("write", self._update_preview)
        self.job_var.trace_add("write", self._update_preview)
        self.custom_var.trace_add("write", self._update_preview)
        self.counter_var.trace_add("write", self._update_preview)

        self._update_preview()

    def _build_action_buttons(self, parent):

        btn_frame = ttk.Frame(self.main)
        btn_frame.grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=15,
        )

        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=0)

        # -------------------------------------------------
        # LEFT BUTTONS
        # -------------------------------------------------

        left_frame = ttk.Frame(btn_frame)
        left_frame.grid(row=0, column=0, sticky="w")

        ttk.Button(
            left_frame,
            text="New Session",
            command=self._new_session,
            bootstyle="success",
        ).pack(
            side="left",
            padx=(0, 8),
        )

        self.scan_button = ttk.Button(
            left_frame,
            text="Scan",
            command=self._scan,
        )
        self.scan_button.pack(
            side="left",
            padx=5,
        )

        self.dry_run_button = ttk.Button(
            left_frame,
            text="Dry Run",
            command=self._dry_run,
        )
        self.dry_run_button.pack(
            side="left",
            padx=5,
        )

        self.copy_button_text = tk.StringVar(value="Copy")

        self.copy_button = ttk.Button(
            left_frame,
            textvariable=self.copy_button_text,
            command=self._copy_pressed,
        )
        self.copy_button.pack(
            side="left",
            padx=5,
        )

        self.open_report_button = ttk.Button(
            left_frame,
            text="Open Last Report",
            command=self._open_last_report,
        )
        self.open_report_button.pack(
            side="left",
            padx=5,
        )

        self.history_button = ttk.Button(
            left_frame,
            text="Ingest History",
            command=self._open_ingest_history,
        )
        self.history_button.pack(
            side="left",
            padx=5,
        )

        # -------------------------------------------------
        # RIGHT BUTTONS
        # -------------------------------------------------

        right_frame = ttk.Frame(btn_frame)
        right_frame.grid(row=0, column=1, sticky="e")

        self.preferences_button = ttk.Button(
            right_frame,
            text="⚙",
            width=3,
            command=self._preferences,
            bootstyle=("secondary", "ghost"),
        )
        self.preferences_button.pack(side="left", padx=(0, 5))

        self.help_button = ttk.Button(
            right_frame,
            text="?",
            width=3,
            command=self._help,
            bootstyle=("secondary", "ghost"),
        )
        self.help_button.pack(side="left", padx=(0, 5))

        self.about_button = ttk.Button(
            right_frame,
            text="ℹ",
            width=3,
            command=self._about,
            bootstyle=("secondary", "ghost"),
        )
        self.about_button.pack(side="left")


    def _build_progress_bar(self, parent):
        self.progress = ttk.Progressbar(
            self.main,
            orient="horizontal",
            mode="determinate",
            bootstyle="info, stripped",
        )

        self.progress.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(20, 10)
        )

    def _build_log_panel(self, parent):

        log_frame = ttk.LabelFrame(
            self.main,
            text="Log output",
            padding=10,
        )

        log_frame.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="nsew",
        )

        # -------------------------------------------------
        # Log / Final Structure tabs
        # -------------------------------------------------

        self.output_notebook = ttk.Notebook(
            log_frame,
        )

        self.output_notebook.pack(
            fill="both",
            expand=True,
        )

        log_tab = ttk.Frame(
            self.output_notebook,
        )

        structure_tab = ttk.Frame(
            self.output_notebook,
        )

        self.output_notebook.add(
            log_tab,
            text="Log",
        )

        self.output_notebook.add(
            structure_tab,
            text="Final Structure",
        )

        # -------------------------------------------------
        # LOG TAB
        # -------------------------------------------------

        log_container = ttk.Frame(
            log_tab,
        )

        log_container.pack(
            fill="both",
            expand=True,
            padx=3,
            pady=3,
        )

        self.log = tk.Text(
            log_container,
            height=12,
            state="disabled",
            font=("Menlo", 10),
            wrap="none",
        )

        scrollbar = ttk.Scrollbar(
            log_container,
            orient="vertical",
            command=self.log.yview,
        )

        self.log.configure(
            yscrollcommand=scrollbar.set,
            padx=15,
            pady=15,
        )

        self.log.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar.pack(
            side="right",
            fill="y",
        )

        self.log.tag_configure(
            "header",
            foreground="#909090",
            font=("Menlo", 10, "bold"),
        )

        self.log.tag_configure(
            "success",
            foreground="#3FB950",
        )

        self.log.tag_configure(
            "warning",
            foreground="#E3B341",
        )

        self.log.tag_configure(
            "error",
            foreground="#F85149",
        )

        self.log.tag_configure(
            "copy",
            foreground="#58A6FF",
        )

        self.log.tag_configure(
            "rename",
            foreground="#58A6FF",
        )

        # -------------------------------------------------
        # FINAL STRUCTURE TAB
        # -------------------------------------------------

        structure_header = ttk.Frame(
            structure_tab,
        )

        structure_header.pack(
            fill="x",
            pady=(0, 8),
        )

        ttk.Label(
            structure_header,
            text="Final file structure",
            font=("TkDefaultFont", 10, "bold"),
        ).pack(
            side="left",
        )

        self.final_structure_button = ttk.Button(
            structure_header,
            text="Open in Window",
            command=self._open_final_structure_window,
            state="disabled",
        )

        self.final_structure_button.pack(
            side="right",
        )



        structure_container = ttk.Frame(
            structure_tab,
        )

        structure_container.pack(
            fill="both",
            expand=True,
            padx=3,
            pady=3,
        )

        self.structure_tree = ttk.Treeview(
            structure_container,
            show="tree",
        )

        structure_scrollbar_y = ttk.Scrollbar(
            structure_container,
            orient="vertical",
            command=self.structure_tree.yview,
        )

        structure_scrollbar_x = ttk.Scrollbar(
            structure_container,
            orient="horizontal",
            command=self.structure_tree.xview,
        )

        self.structure_tree.configure(
            yscrollcommand=structure_scrollbar_y.set,
            xscrollcommand=structure_scrollbar_x.set,
        )

        self.structure_tree.grid(
            row=0,
            column=0,
            sticky="nsew",
        )

        structure_scrollbar_y.grid(
            row=0,
            column=1,
            sticky="ns",
        )

        structure_scrollbar_x.grid(
            row=1,
            column=0,
            sticky="ew",
        )

        structure_container.rowconfigure(
            0,
            weight=1,
        )

        structure_container.columnconfigure(
            0,
            weight=1,
        )

    def _build_status_bar(self, parent):
        self.status_var = tk.StringVar(value="Ready")

        ttk.Label(
            self.root,
            textvariable=self.status_var,
            anchor="w"
        ).pack(side="bottom", fill="x", padx=10, pady=(0, 4))

        self.main.rowconfigure(2, weight=1)

    def _preferences(self):

        dlg = PreferencesDialog(
            self.root,
            self.settings_manager,
        )

        self.root.wait_window(dlg)

        if not dlg.saved:
            return

        # Reload the newly saved settings.
        self.settings = self.settings_manager.load()

        # Update the main-window default source.
        self._set_default_source()

        # Update the main-window destination fields.
        self.dest_var.set(
            self.settings.default_destination
        )

        self.backup_dest_var.set(
            self.settings.default_backup_destination
        )

        # Update dependent components.
        self.copier.verify_checksum = (
            self.settings.verify_checksum
        )

        self.report_manager = ReportManager(
            self.settings.reports_directory
        )

        self._invalidate_ingest_plan()

    def _open_last_report(self):

        if not self.current_report_path:
            self._log("No report available for this session.")
            return

        if not self.current_report_path.exists():
            self._log(
                f"[ERROR] Report not found: "
                f"{self.current_report_path}"
            )
            return

        try:
            subprocess.run(
                ["open", str(self.current_report_path)],
                check=False,
            )

        except Exception as e:
            self._log(
                f"[ERROR] Could not open report: {e}"
            )

    def _open_ingest_history(self):

        reports = self.report_manager.list_reports()

        if not reports:
            self._log("No ingest reports available.")
            return

        window = tk.Toplevel(self.root)
        window.title("Ingest History")
        window.geometry("650x230")
        window.resizable(False, False)
        window.transient(self.root)

        frame = ttk.Frame(
            window,
            padding=15,
        )

        frame.pack(
            fill="both",
            expand=True,
        )

        ttk.Label(
            frame,
            text="Previous Ingest Reports",
            font=("TkDefaultFont", 11, "bold"),
        ).pack(
            anchor="w",
            pady=(0, 10),
        )

        # -------------------------------------------------
        # REPORT TABLE
        # -------------------------------------------------

        table_frame = ttk.Frame(frame)

        table_frame.pack(
            fill="both",
            expand=True,
        )

        report_tree = ttk.Treeview(
            table_frame,
            columns=("date", "report"),
            show="headings",
            selectmode="browse",
            height=5,
        )

        report_tree.heading(
            "date",
            text="Date / Time",
            anchor="w",
        )

        report_tree.heading(
            "report",
            text="Report",
            anchor="w",
        )

        report_tree.column(
            "date",
            anchor="w",
            width=150,
            stretch=False,
        )

        report_tree.column(
            "report",
            anchor="w",
            width=430,
        )

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=report_tree.yview,
        )

        report_tree.configure(
            yscrollcommand=scrollbar.set,
        )

        report_tree.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar.pack(
            side="right",
            fill="y",
        )

        # -------------------------------------------------
        # REPORTS
        # -------------------------------------------------

        for index, report in enumerate(reports):

            try:
                modified_time = report.stat().st_mtime

                date_time = datetime.fromtimestamp(
                    modified_time
                ).strftime(
                    "%Y-%m-%d %H:%M"
                )

            except OSError:
                date_time = "Unknown"

            report_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    date_time,
                    report.name,
                ),
            )

        # -------------------------------------------------
        # OPEN REPORT
        # -------------------------------------------------

        def open_selected_report(event=None):

            selection = report_tree.selection()

            if not selection:
                return

            index = int(selection[0])
            report_path = reports[index]

            try:

                subprocess.run(
                    ["open", str(report_path)],
                    check=False,
                )

            except Exception as e:

                self._log(
                    f"[ERROR] Could not open report: {e}"
                )

        report_tree.bind(
            "<Double-1>",
            open_selected_report,
        )

        # -------------------------------------------------
        # CLOSE BUTTON
        # -------------------------------------------------

        button_frame = ttk.Frame(frame)

        button_frame.pack(
            fill="x",
            pady=(12, 0),
        )

        ttk.Button(
            button_frame,
            text="Close",
            command=window.destroy,
        ).pack(
            side="right",
        )

    def _about(self):
        from tkinter import messagebox

        messagebox.showinfo(
            "About Photo Ingest",
            f"{APP_NAME}\n"
            f"Version {APP_VERSION}\n\n"
            "A lightweight photo ingest application "
            "for organizing and copying RAW images."
        )

    def _help(self):
        HelpDialog(self.root)

    def _unknown_camera_profile(
        self,
        raw_make: str,
        raw_model: str,
    ) -> tuple[str, str] | None:

        result_holder = {
            "result": None,
        }

        done = threading.Event()

        def show_dialog():

            try:

                dialog = CameraProfileDialog(
                    self.root,
                    raw_make=raw_make,
                    raw_model=raw_model,
                )

                self.root.wait_window(dialog)

                result_holder["result"] = dialog.result

            finally:

                done.set()

        self.root.after(
            0,
            show_dialog,
        )

        done.wait()

        return result_holder["result"]

    # =========================================================
    # SOURCE MODE HANDLER (ADD THIS HERE)
    # =========================================================

    def _add_files(self):
        self._invalidate_ingest_plan()

        from tkinter import filedialog

        files = filedialog.askopenfilenames()

        for f in files:
            p = Path(f)

            # Only allow configured RAW extensions
            if p.suffix.lower() not in self.settings.raw_extensions:
                continue

            if f not in self.selected_files:
                self.selected_files.append(f)
                self.file_listbox.insert("end", p.name)

        self._update_preview()

    def _add_folder(self):
        self._invalidate_ingest_plan()

        from tkinter import filedialog
        from pathlib import Path

        folder = filedialog.askdirectory()

        if not folder:
            return

        p = Path(folder)

        if str(p) not in self.selected_files:
            self.selected_files.append(str(p))
            self.file_listbox.insert("end", f"[FOLDER] {p.name}")

        self._update_preview()

    def _invalidate_ingest_plan(self):

        self.current_plan = None
        self.manifest_entries = []
        self.session_header_logged = False

        self.progress["value"] = 0

        if hasattr(self, "progress_var"):
            self.progress_var.set("")

        # Reset Copy / Cancel UI state
        if hasattr(self, "copy_button_text"):
            self.copy_button_text.set("Copy")

        if hasattr(self, "copy_in_progress"):
            self.copy_in_progress = False

        if hasattr(self, "_set_copy_mode"):
            self._set_copy_mode(False)

        if hasattr(self, "structure_tree"):
            for item in self.structure_tree.get_children():
                self.structure_tree.delete(item)

        self._set_final_structure_available(False)

        self._set_status("Ready")

    def _new_session(self):

        self._invalidate_ingest_plan()

        # Reload settings so the current saved defaults are used.
        self.settings = self.settings_manager.load()

        # Clear current source selection.
        self.selected_files.clear()
        self.file_listbox.delete(0, "end")

        # Restore saved default source folder.
        default_source = self.settings.default_source

        if default_source:
            self.selected_files.append(default_source)

            source_path = Path(default_source)

            self.file_listbox.insert(
                "end",
                f"[FOLDER] {source_path.name}",
            )

        # Restore saved default destinations.
        self.dest_var.set(
            self.settings.default_destination
        )

        self.backup_dest_var.set(
            self.settings.default_backup_destination
        )

        # Clear current report association.
        self.current_report_path = None

        # Clear log.
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

        # Reset progress.
        self.progress["value"] = 0
        self.progress_var.set("")

        # Reset status.
        self._set_status("Ready")

        # Visual feedback.
        self._log("New ingest session started.")

    def _clear_files(self):
        self._invalidate_ingest_plan()

        self.selected_files = []
        self.file_listbox.delete(0, "end")

        self._update_preview()

        self.session_header_logged = False

        self._log("")
        self._log("Source selection cleared.")

    def _set_default_source(self):

        default_source = self.settings.default_source

        self.selected_files.clear()
        self.file_listbox.delete(0, "end")

        if not default_source:
            return

        source_path = Path(default_source)

        self.selected_files.append(
            str(source_path)
        )

        self.file_listbox.insert(
            "end",
            f"[FOLDER] {source_path.name}"
        )

    # =========================================================
    # INIT
    # =========================================================

    def _apply_initial_state(self):

        # Load last template
        self._load_template(self.template_var.get())

        # Restore default destination
        self.dest_var.set(self.settings.default_destination)

        # Restore default source
        self.selected_files = []

        self.file_listbox.delete(0, "end")

        source = Path(self.settings.default_source)

        if source.exists():

            self.selected_files.append(str(source))

            if source.is_dir():
                self.file_listbox.insert(
                    "end",
                    f"[FOLDER] {source.name}"
                )
            else:
                self.file_listbox.insert(
                    "end",
                    source.name
                )

        self._update_preview()

    # =========================================================
    # TEMPLATE
    # =========================================================

    def _on_template_change(self, _=None):
        self._invalidate_ingest_plan()

        self._load_template(self.template_var.get())
        self.settings.last_template = self.template_var.get()
        self.settings_manager.save(self.settings)

    def _load_template(self, name):
        t = next((x for x in self.templates if x.name == name), None)
        if not t:
            self.folder_template_var.set("")
            self.filename_template_var.set("")
            return
        self.folder_template_var.set(t.folder_template)
        self.filename_template_var.set(t.filename_template)

    # =========================================================
    # BROWSE
    # =========================================================

    def _browse_destination(self):
        path = filedialog.askdirectory()

        if path:
            self._invalidate_ingest_plan()
            self.dest_var.set(path)

    def _create_or_open_destination(self):

        folder_text = self.dest_var.get().strip()

        if not folder_text:
            messagebox.showwarning(
                "Destination Folder",
                "Select or enter a destination folder first.",
                parent=self.root,
            )
            return

        folder = Path(folder_text).expanduser()

        try:

            if not folder.exists():

                folder.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                self._log(
                    f"Created destination folder: {folder}"
                )

            else:

                self._log(
                    f"Opened destination folder: {folder}"
                )

            self.root.after(
                0,
                lambda: subprocess.run(
                    ["open", str(folder)],
                    check=False,
                )
            )

        except Exception as e:

            messagebox.showerror(
                "Destination Folder Error",
                (
                    "Could not create or open "
                    f"the destination folder:\n\n{e}"
                ),
                parent=self.root,
            )

    def _update_backup_controls(self):

        enabled = self.backup_enabled_var.get()

        state = "normal" if enabled else "disabled"

        self.backup_dest_entry.configure(
            state=state
        )

        self.backup_browse_button.configure(
            state=state
        )

    def _backup_settings_changed(self):

        self._invalidate_ingest_plan()
        self._update_backup_controls()

    def _browse_backup_destination(self):

        initial_dir = self.backup_dest_var.get().strip()

        if not initial_dir:
            initial_dir = self.dest_var.get().strip()

        folder = filedialog.askdirectory(
            parent=self.root,
            initialdir=initial_dir,
            title="Select Backup Destination",
        )

        if folder:
            self.backup_dest_var.set(folder)

    # =========================================================
    # SCAN
    # =========================================================

    def _scan(self):

        self._set_status("Scanning...")

        self.progress_var.set("Starting scan...")

        thread = threading.Thread(
            target=self._scan_worker,
            daemon=True,
        )

        thread.start()

    def _scan_worker(self):

        try:
            self._set_status("Scanning...")

            self.root.after(
                0,
                lambda: self.copy_button_text.set("Copy")
            )

            self.root.after(
                0,
                lambda: self._set_copy_mode(False)
            )

            # -------------------------------------------------
            # VALIDATION
            # -------------------------------------------------

            if not self.selected_files:
                raise ValueError("No inputs selected.")

            if not self.dest_var.get().strip():
                raise ValueError("Destination folder is empty.")

            if not self.session_header_logged:
                self._log_session_header()
                self.session_header_logged = True

            source = SourceInput(
                mode="files",
                files=[Path(f) for f in self.selected_files],
            )

            job_code = self.job_var.get().strip()

            if job_code:
                if not re.fullmatch(
                    r"[A-Za-z0-9_-]+",
                    job_code,
                ):
                    raise ValueError(
                        "Job Code may only contain letters, "
                        "numbers, '-' and '_'."
                    )

            custom = self.custom_var.get().strip()

            invalid = '<>:"/\\|?*'

            if any(ch in invalid for ch in custom):
                raise ValueError(
                    "Custom Text contains invalid filename characters."
                )

            # -------------------------------------------------
            # LOG SCAN START
            # -------------------------------------------------

            self._log_header("SCAN")

            self._log("")
            self._log("Input")
            self._log(
                f"  Sources ............. "
                f"{len(self.selected_files)}"
            )

            # -------------------------------------------------
            # SCAN
            # -------------------------------------------------

            scan = self.scanner.scan(source)


            # -------------------------------------------------
            # UNKNOWN CAMERA CHECK
            #
            # This is the ONLY unknown-camera check.
            # -------------------------------------------------

            unknown_cameras = self.planner.find_unknown_cameras(
                scan
            )

            # -------------------------------------------------
            # CAMERA PROFILE DIALOG
            # -------------------------------------------------

            if unknown_cameras:

                result_holder = {
                    "result": None,
                }

                done = threading.Event()

                def show_camera_dialog():

                    try:

                        dialog = CameraProfileDialog(
                            self.root,
                            cameras=unknown_cameras,
                        )

                        self.root.wait_window(dialog)

                        result_holder["result"] = dialog.result

                    finally:

                        done.set()

                self.root.after(
                    0,
                    show_camera_dialog,
                )

                done.wait()

                profile_result = result_holder["result"]

                if profile_result is None:
                    raise ValueError(
                        "Camera profile setup cancelled."
                    )

                # ---------------------------------------------
                # Save new camera profiles into the normalizer
                # ---------------------------------------------

                for (
                    raw_make,
                    raw_model,
                    display_make,
                    display_model,
                ) in profile_result:

                    self.planner.camera_normalizer.update_profile(
                        raw_make=raw_make,
                        raw_model=raw_model,
                        display_make=display_make,
                        display_model=display_model,
                    )

            # -------------------------------------------------
            # TEMPLATES
            # -------------------------------------------------

            folder_template = (
                self.folder_template_var.get().strip()
            )

            file_template = (
                self.filename_template_var.get().strip()
            )

            if not folder_template:
                raise ValueError(
                    "Folder template is empty."
                )

            if not file_template:
                raise ValueError(
                    "Filename template is empty."
                )

            if not folder_template.replace("/", "").strip():
                raise ValueError(
                    "Folder template is invalid."
                )

            if (
                "{original}" not in file_template
                and "{counter}" not in file_template
            ):
                raise ValueError(
                    "Filename template must contain "
                    "{original} or {counter}."
                )

            # -------------------------------------------------
            # BUILD PLAN
            #
            # Build exactly ONCE.
            #
            # If new camera profiles were added above, they are
            # already available to the planner here.
            # -------------------------------------------------

            self.current_plan = self.planner.build(
                scan_result=scan,
                destination_root=self.dest_var.get().strip(),
                folder_template=folder_template,
                file_template=file_template,
                job_code=self.job_var.get(),
                custom_text=self.custom_var.get(),
                start_counter=self.counter_var.get(),
                duplicate_mode=self.settings.duplicate_mode,
                xmp_naming=self.settings.xmp_naming,
                backup_enabled=self.backup_enabled_var.get(),
                backup_destination=self.backup_dest_var.get().strip(),
            )

            # -------------------------------------------------
            # FINALISING
            # -------------------------------------------------

            self.root.after(
                0,
                lambda: self._set_status(
                    "Finalising scan..."
                ),
            )

            if self.current_plan.duplicate_collisions:

                raise ValueError(
                    f"{self.current_plan.duplicate_collisions} "
                    "duplicate destination filename(s) detected.\n\n"
                    "Please modify the filename template."
                )

            # -------------------------------------------------
            # RESULTS
            # -------------------------------------------------

            self._log("")
            self._log("Results")

            self._log(
                f"  Files to process .... "
                f"{len(self.current_plan.items)}"
            )

            self._log(
                f"  Existing files ...... "
                f"{self.current_plan.existing_collisions}"
            )

            self._log(
                f"  Duplicate outputs ... "
                f"{self.current_plan.duplicate_collisions}"
            )

            if self.current_plan.review_items:

                self._log(
                    f"  Review queue ........ "
                    f"{len(self.current_plan.review_items)}"
                )

            self._log("")
            self._log("Status")
            self._log("  Scan complete.")

            self._set_status("Scan complete")

            self.root.after(
                0,
                lambda: self.progress_var.set(""),
            )

            self.root.after(
                0,
                lambda: self.progress.configure(value=0),
            )

        except Exception as e:

            self._log(
                f"[ERROR] {e}"
            )

            self._set_status("Error")

    # =========================================================
    # DRY RUN
    # =========================================================

    def _dry_run(self):

        if not self.current_plan:
            self._log("No plan available. Run Scan first.")
            return

        self._set_status("Dry Run...")

        collisions = sum(
            1
            for item in self.current_plan.items
            if item.collision
        )

        self._log_header("DRY RUN")

        self._log("")
        self._log("Input")
        self._log(f"  Sources ............. {len(self.selected_files)}")

        self._log("")
        self._log("Results")
        self._log(f"  Files to process .... {len(self.current_plan.items)}")
        self._log(f"  Collisions .......... {collisions}")

        self._log("")
        self._log("Plan")
        self._log("-" * 80)

        for item in self.current_plan.items:

            self._log(item.source_path.name)

            self._log(
                f"Destination : {item.relative_destination}"
            )

            if item.relative_xmp_destination:
                self._log(
                    f"XMP         : {item.relative_xmp_destination}"
                )

            if item.collision:
                self._log(
                    "⚠ Destination already exists",
                    "warning",
                )

            self._log("○ Planned", "copy")
            self._log("")

        self._log("-" * 80)

        self._log("")
        self._log("Summary")
        self._log(f"  Files ............... {len(self.current_plan.items)}")
        self._log(f"  Existing files ...... {self.current_plan.existing_collisions}")
        self._log(f"  Duplicate outputs ... {self.current_plan.duplicate_collisions}")

        self._log("")
        self._log("Status")
        self._log("  Dry run complete.")

        try:
            report_content = self._build_dry_run_report()

            self.current_report_path = self.report_manager.write_report(
                report_content
            )

            self._log(
                f"Report created: {self.current_report_path}"
            )

        except Exception as e:
            self._log(
                f"[ERROR] Could not create dry-run report: {e}"
            )

        self._refresh_final_structure()
        self._set_final_structure_available(True)


    def _refresh_final_structure(self):

        if not hasattr(self, "structure_tree"):
            return

        self._populate_structure_tree(
            self.structure_tree
        )

    def _populate_structure_tree(self, tree):

        for item in tree.get_children():
            tree.delete(item)

        tree.tag_configure(
                    "monospace",
                    font=("Menlo", 10),
                )

        if not self.current_plan:
            return

        node_ids = {}

        def add_file(relative_path):

            parent_id = ""
            current_path = []

            for part in relative_path.parts[:-1]:

                current_path.append(part)

                path_key = tuple(current_path)

                if path_key not in node_ids:

                    node_id = tree.insert(
                        parent_id,
                        "end",
                        text=part,
                        open=True,
                        tags=("monospace",),
                    )

                    node_ids[path_key] = node_id

                parent_id = node_ids[path_key]

            tree.insert(
                parent_id,
                "end",
                text=relative_path.name,
                tags=("monospace",),
            )

        for item in self.current_plan.items:

            add_file(
                item.relative_destination
            )

            if item.relative_xmp_destination:

                add_file(
                    item.relative_xmp_destination
                )

    def _open_final_structure_window(self):

        window = tk.Toplevel(self.root)

        window.title("Final Structure")
        window.geometry("1000x700")
        window.minsize(600, 400)

        tree_frame = ttk.Frame(
            window,
            padding=15,
        )

        tree_frame.pack(
            fill="both",
            expand=True,
        )


        structure_tree = ttk.Treeview(
            tree_frame,
            show="tree",
        )

        scrollbar = ttk.Scrollbar(
            tree_frame,
            orient="vertical",
            command=structure_tree.yview,
        )

        structure_tree.configure(
            yscrollcommand=scrollbar.set,
        )

        structure_tree.pack(
            side="left",
            fill="both",
            expand=True,
        )

        scrollbar.pack(
            side="right",
            fill="y",
        )

        self._populate_structure_tree(
            structure_tree
        )


    # =========================================================
    # REPORT BUILDING
    # =========================================================

    def _build_dry_run_report(self) -> str:
        plan = self.current_plan

        lines = []

        lines.append("=" * 80)
        lines.append("PHOTO INGEST REPORT — DRY RUN")
        lines.append("=" * 80)
        lines.append("")

        lines.append(
            f"Started      : {datetime.now():%Y-%m-%d %H:%M:%S}"
        )

        folders = sum(
            Path(p).is_dir()
            for p in self.selected_files
        )

        files = len(self.selected_files) - folders

        if folders:
            lines.append(f"Folders      : {folders}")

        if files:
            lines.append(f"Files        : {files}")

        lines.append("Destination  :")

        lines.append(f"  {self.dest_var.get()}")

        if self.job_var.get():
            lines.append(f"Job Code     : {self.job_var.get()}")

        if self.custom_var.get():
            lines.append(f"Custom Text  : {self.custom_var.get()}")

        lines.append(
            f"Counter      : {self.counter_var.get()}"
        )

        lines.append("")

        lines.append("-" * 80)

        lines.append("DRY RUN")

        lines.append("-" * 80)

        lines.append("")

        lines.append("Results")

        lines.append(
            f"  Files to process .... {len(plan.items)}"
        )
        lines.append(
            f"  Existing files ...... {plan.existing_collisions}"
        )
        lines.append(
            f"  Duplicate outputs ... {plan.duplicate_collisions}"
        )

        if plan.review_items:
            lines.append(
                f"  Review queue ........ {len(plan.review_items)}"
            )

        lines.append("")

        lines.append("-" * 80)

        lines.append("PLAN")

        lines.append("-" * 80)

        lines.append("")

        for index, item in enumerate(plan.items, start=1):

            lines.append(
                f"{index:04d}"
            )

            lines.append(
                f"{'Source':<12}: {item.source_path.name}"
            )

            lines.append(
                f"{'Destination':<12}: {item.relative_destination}"
            )

            if item.relative_xmp_destination:
                lines.append(
                    f"{'XMP':<12}: {item.relative_xmp_destination}"
                )

            if item.collision:
                lines.append(
                    f"{'Status':<12}: COLLISION"
                )
            else:
                lines.append(
                    f"{'Status':<12}: PLANNED"
                )

            lines.append("")

        lines.append("-" * 80)
        lines.append("")
        lines.append("Status")
        lines.append("  Dry run complete.")
        lines.append("")

        return "\n".join(lines)

    def _build_copy_report_section(self, stats) -> str:
        lines = []

        lines.append("")
        lines.append("=" * 80)
        lines.append("COPY RESULTS")
        lines.append("=" * 80)
        lines.append("")

        lines.append(
            f"Completed    : {datetime.now():%Y-%m-%d %H:%M:%S}"
        )

        lines.append("")
        lines.append(
            "Checksum verification : "
            + (
                "ON"
                if self.copier.verify_checksum
                else "OFF"
            )
        )
        lines.append("")

        # =====================================================
        # OPERATIONS
        # =====================================================

        lines.append("Operations")
        lines.append("-" * 80)
        lines.append("")

        operations = stats.get("operations", [])

        for index, operation in enumerate(
            operations,
            start=1,
        ):
            lines.append(
                f"{index:04d}"
            )

            lines.append(
                f"Source      : {operation['filename']}"
            )

            lines.append(
                f"Destination : {operation['destination']}"
            )

            if operation.get("new_name"):
                lines.append(
                    f"New Name    : {operation['new_name']}"
                )

            result_labels = {
                "copied": "COPIED",
                "renamed": "RENAMED",
                "skipped": "SKIPPED",
                "replaced": "REPLACED",
                "planned": "PLANNED",
                "error": "ERROR",
            }

            result = result_labels.get(
                operation["result"],
                operation["result"].upper(),
            )

            lines.append(
                f"Status      : {result}"
            )

            lines.append("")

        # =====================================================
        # SUMMARY
        # =====================================================

        lines.append("-" * 80)
        lines.append("Summary")
        lines.append("")

        for line in self._build_copy_summary_lines(stats):
            lines.append(
                f"  {line}"
            )

        lines.append("")

        return "\n".join(lines)

        # =====================================================
        # UNSORTED COUNT
        # =====================================================

        unsorted_count = sum(
            1
            for operation in operations
            if str(
                operation.get("destination", "")
            ).replace("\\", "/").startswith("Unsorted/")
        )

        # =====================================================
        # SUMMARY
        # =====================================================

        lines.append("-" * 80)
        lines.append("Summary")
        lines.append("")

        lines.append(
            f"  RAW copied ........ {stats['copied_raw']}"
        )

        lines.append(
            f"  XMP copied ........ {stats['copied_xmp']}"
        )

        lines.append(
            f"  Unsorted .......... {unsorted_count}"
        )

        lines.append(
            f"  Backup RAW copied . {stats['backup_raw']}"
        )

        lines.append(
            f"  Backup XMP copied . {stats['backup_xmp']}"
        )

        lines.append(
            f"  Backup errors ..... {stats['backup_errors']}"
        )

        lines.append(
            f"  Renamed ........... {stats['renamed']}"
        )

        lines.append(
            f"  Skipped ........... {stats['skipped']}"
        )

        lines.append(
            f"  Errors ............ {stats['errors']}"
        )

        if stats.get("cancelled"):
            lines.append(
                "  Status ............ CANCELLED"
            )
        else:
            lines.append(
                "  Status ............ COMPLETE"
            )

        lines.append("")

        return "\n".join(lines)

    # =========================================================
    # COPY
    # =========================================================

    def _validate_plan_sources(self) -> bool:

        if not self.current_plan:
            return False

        missing_files = [
            item.source_path
            for item in self.current_plan.items
            if not item.source_path.exists()
        ]

        if not missing_files:
            return True

        self._log("")
        self._log("COPY VALIDATION", "warning")
        self._log("-" * 80, "warning")
        self._log("")
        self._log("The copy plan is no longer valid.", "warning")
        self._log("")
        self._log(
            f"Missing source files ... {len(missing_files)}",
            "warning",
        )

        for path in missing_files:
            self._log(
                f"Missing : {path}",
                "warning",
            )

        self._log("")
        self._log(
            "Run Scan again before copying.",
            "warning",
        )

        self._set_status("Plan invalid")

        return False

    def _copy(self):
        try:
            if not self.current_plan:
                self._log("No plan available. Run Scan first.")
                return

            if not self._validate_plan_sources():
                return

            self._log_header("COPY")

            self._log("")
            self._log(
                "Checksum verification : "
                + (
                    "ON"
                    if self.copier.verify_checksum
                    else "OFF"
                )
            )
            self._log("")

            self._set_status("Copying...")
            self.progress_var.set("Starting copy...")
            self._set_copy_mode(True)

            thread = threading.Thread(
                target=self._copy_worker,
                daemon=True
            )
            thread.start()

        except Exception as e:
            self._log(f"[ERROR] {e}")
            self._set_status("Error")

    # ---------------- THREADING ----------------
    # =========================================================
    # COPY WORKER
    # =========================================================

    def _copy_worker(self):
        try:
            def progress_callback(current, total, filename):
                self.root.after(
                    0,
                    lambda: self._set_progress(current, total, filename)
                )

            def log_callback(msg):

                if isinstance(msg, dict) and msg.get("type") == "operation":

                    self.root.after(
                        0,
                        lambda: self._log_operation(
                            filename=msg["filename"],
                            destination=msg["destination"],
                            result=msg["result"],
                            new_name=msg.get("new_name"),
                        )
                    )

                else:

                    self.root.after(
                        0,
                        lambda: self._log(msg)
                    )

            self.copier.logger = log_callback
            self.copier.progress = progress_callback

            stats = self.copier.execute(self.current_plan)

            self._log("")
            self._log("Summary")

            for line in self._build_copy_summary_lines(stats):
                self._log(
                    f"  {line}"
                )

            self._log("")

            if stats["cancelled"]:

                self._log(
                    "COPY CANCELLED"
                )

            elif stats["errors"] or stats["backup_errors"]:

                self._log(
                    "COPY COMPLETED WITH ERRORS"
                )

            else:

                self._log(
                    "COPY COMPLETE"
                )

                self._set_final_structure_available(False)

            self._log("")

            copy_section = self._build_copy_report_section(stats)

            if self.current_report_path is not None:
                existing_report = self.current_report_path.read_text(
                    encoding="utf-8"
                )

                updated_report = (
                    existing_report.rstrip()
                    + "\n\n"
                    + copy_section
                    + "\n"
                )

                self.report_manager.write_report(
                    updated_report,
                    report_path=self.current_report_path,
                )

            # A clean, successful copy consumes the current plan.
            # Cancelled copies and copies with errors keep the plan
            # available for retry/review.
            if (
                not stats["cancelled"]
                and stats["errors"] == 0
                and stats["backup_errors"] == 0
            ):
                self.current_plan = None

                self.root.after(
                    0,
                    self._refresh_final_structure
                )

            status = (
                "Copy cancelled"
                if stats["cancelled"]
                else (
                    "Copy completed with errors"
                    if stats["errors"] or stats["backup_errors"]
                    else "Copy complete"
                )
            )

            self.root.after(
                0,
                lambda: self._set_status(status)
            )

            def show_completion_dialog():
                self._show_copy_completion_dialog(stats)
                self._reset_progress()

            self.root.after(
                0,
                show_completion_dialog
            )

            self.root.after(
                0,
                lambda: self.copy_button_text.set("Copy")
            )

            self.root.after(
                0,
                lambda: self._set_copy_mode(False)
            )

        except Exception as e:

            self.root.after(
                0,
                lambda msg=str(e): self._log(f"[ERROR] {msg}")
            )

            self.root.after(
                0,
                lambda msg=str(e): self._set_status("Error")
            )

            self.root.after(
                0,
                lambda: self.copy_button_text.set("Copy")
            )

            self.root.after(
                0,
                lambda: self._set_copy_mode(False)
            )

    def _build_copy_summary_lines(self, stats):

        unsorted_count = sum(
            1
            for operation in stats.get("operations", [])
            if str(
                operation.get("destination", "")
            ).replace("\\", "/").startswith("Unsorted/")
        )

        return [
            f"RAW copied ........ {stats['copied_raw']}",
            f"XMP copied ........ {stats['copied_xmp']}",
            f"Unsorted .......... {unsorted_count}",
            f"Backup RAW copied . {stats['backup_raw']}",
            f"Backup XMP copied . {stats['backup_xmp']}",
            f"Backup errors ..... {stats['backup_errors']}",
            f"Renamed ........... {stats['renamed']}",
            f"Skipped ........... {stats['skipped']}",
            f"Errors ............ {stats['errors']}",
        ]

    def _show_copy_completion_dialog(self, stats):

        if stats["cancelled"]:
            title = "Copy Cancelled"
            message = "The copy operation was cancelled."

        elif stats["errors"] or stats["backup_errors"]:
            title = "Copy Completed with Errors"
            message = "The copy operation completed with errors."

        else:
            title = "Copy Complete"
            message = "The copy operation completed successfully."

        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        frame = ttk.Frame(
            dialog,
            padding=20,
        )
        frame.pack(
            fill="both",
            expand=True,
        )

        ttk.Label(
            frame,
            text=message,
            font=("TkDefaultFont", 12),
        ).pack(
            anchor="w",
            pady=(0, 15),
        )

        summary_lines = self._build_copy_summary_lines(
            stats
        )

        details = "\n".join(
            summary_lines
        )

        ttk.Label(
            frame,
            text=details,
            font=("Menlo", 12),
            justify="left",
        ).pack(
            anchor="w",
            pady=(0, 20),
        )

        ttk.Button(
            frame,
            text="OK",
            command=dialog.destroy,
            width=10,
        ).pack(
            anchor="e",
        )

        dialog.update_idletasks()

        x = (
            self.root.winfo_rootx()
            + (self.root.winfo_width() - dialog.winfo_width()) // 2
        )

        y = (
            self.root.winfo_rooty()
            + (self.root.winfo_height() - dialog.winfo_height()) // 2
        )

        dialog.geometry(
            f"+{x}+{y}"
        )

        dialog.focus_set()
        dialog.wait_window()

    # =========================================================
    # SAVE TEMPLATE
    # =========================================================
    def _save_template(self):
        from templates import Template

        name = self.template_var.get().strip()

        if not name:
            self._log("No template selected.")
            return

        folder_template = self.folder_template_var.get().strip()
        filename_template = self.filename_template_var.get().strip()

        if not folder_template or not filename_template:
            self._log("Template cannot be empty.")
            return

        template = Template(
            name=name,
            folder_template=folder_template,
            filename_template=filename_template,
        )

        # SINGLE SOURCE OF TRUTH
        self.template_manager.upsert(template)

        # reload AFTER disk write (authoritative state)
        self.templates = self.template_manager.load()

        # ONE unified refresh (no duplication)
        self._refresh_templates_ui()

        # ensure selection stays correct
        self.template_var.set(name)

        self._log(f"Template saved: {name}")

    # =========================================================
    # SAVE TEMPLATE AS
    # =========================================================

    def _save_template_as(self):
        from tkinter import simpledialog, messagebox
        from templates import Template

        from ttkbootstrap.dialogs import Querybox

        name = Querybox.get_string(
            prompt="Enter new template name:",
            title="Save Template As",
        )

        if not name:
            return

        name = name.strip()

        # -------------------------
        # duplicate protection
        # -------------------------
        existing_names = {t.name.strip().lower() for t in self.templates}

        if name.lower() in existing_names:
            messagebox.showerror(
                "Template Exists",
                f'A template named "{name}" already exists.'
            )
            return

        folder_template = self.folder_template_var.get().strip()
        filename_template = self.filename_template_var.get().strip()

        if not folder_template or not filename_template:
            self._log("Template cannot be empty.")
            return

        template = Template(
            name=name,
            folder_template=folder_template,
            filename_template=filename_template,
        )

        # single source of truth
        self.template_manager.upsert(template)

        # reload from disk
        self.templates = self.template_manager.load()

        # refresh UI
        self._refresh_templates_ui()

        # select newly created template
        self.template_var.set(name)
        self._load_template(name)

        self._log(f"Template created: {name}")

    # =========================================================
    # DELETE TEMPLATE
    # =========================================================

    def _delete_template(self):
        from tkinter import messagebox

        name = self.template_var.get().strip()

        if not name:
            self._log("No template selected.")
            return

        # prevent deleting last template
        if len(self.templates) <= 1:
            messagebox.showwarning(
                "Cannot Delete",
                "At least one template must exist."
            )
            return

        confirm = messagebox.askyesno(
            "Delete Template",
            f'Delete template "{name}"?'
        )

        if not confirm:
            return

        # remove from manager
        self.template_manager.templates = [
            t for t in self.template_manager.templates
            if t.name.strip().lower() != name.lower()
        ]

        self.template_manager.save(self.template_manager.templates)

        # reload state
        self.templates = self.template_manager.load()

        # refresh UI
        self._refresh_templates_ui()

        # select first available template
        first = self.templates[0].name
        self.template_var.set(first)
        self._load_template(first)

        self._log(f"Template deleted: {name}")

    # =========================================================
    # REFRESH TEMPLATE UI
    # =========================================================

    def _refresh_templates_ui(self, selected_name=None):

        self.templates = self.template_manager.load()

        self.template_names = [t.name for t in self.templates]
        self.template_combo["values"] = self.template_names

        if not self.templates:
            self.template_var.set("")
            self.folder_template_var.set("")
            self.filename_template_var.set("")
            return

        valid_names = {t.name for t in self.templates}

        # Which template should be selected?
        if selected_name and selected_name in valid_names:
            self.template_var.set(selected_name)

        elif self.template_var.get() not in valid_names:
            self.template_var.set(self.templates[0].name)

        # Load selected template into the UI
        self._load_template(self.template_var.get())

    # =========================================================
    # ACTIVE TEMPLATE ENTRY
    # =========================================================

    def _set_active_template_entry(self, event):

        self.active_template_entry = event.widget

        if event.widget == self.filename_template_entry:
            self.slash_helper_button.config(state="disabled")
        else:
            self.slash_helper_button.config(state="normal")

    # =========================================================
    # INSERT TEMPLATE TOKEN
    # =========================================================

    def _insert_token(self, token):

        if self.active_template_entry == self.filename_template_entry:

            current = self.filename_template_var.get()
            self.filename_template_var.set(current + token)

        else:

            current = self.folder_template_var.get()
            self.folder_template_var.set(current + token)

        self._update_preview()

    # ==========================================================
    # UPDATE PREVIEW
    # ==========================================================

    def _update_preview(self, *_):

        try:
            counter = self.counter_var.get()
        except Exception:
            counter = 1

        now = datetime.now()

        # -------------------------------------------------
        # Default preview values
        # -------------------------------------------------

        original = "DSF1234"
        extension = "RAF"

        camera_make = ""
        camera_model = ""
        capture_datetime = now

        preview_file = None

        # -------------------------------------------------
        # Use first selected RAW FILE only
        #
        # IMPORTANT:
        # Never scan folders from the preview function.
        # Folder scanning belongs to the Scan workflow.
        # -------------------------------------------------

        if self.selected_files:

            first = Path(self.selected_files[0])

            if (
                first.is_file()
                and first.suffix.lower() in RAW_EXTENSIONS
            ):
                preview_file = first

        # -------------------------------------------------
        # Read EXIF only from an explicitly selected file
        # -------------------------------------------------

        if preview_file:

            original = preview_file.stem
            extension = preview_file.suffix.lstrip(".")

            try:

                exif_map = self.scanner.exif_reader.read_batch(
                    [preview_file]
                )

                exif = exif_map.get(
                    str(preview_file)
                )

                if exif:

                    camera_make = (
                        exif.camera_make or ""
                    )

                    camera_model = (
                        exif.camera_model or ""
                    )

                    if exif.capture_datetime:

                        parsed = self._parse_exif_datetime(
                            exif.capture_datetime
                        )

                        if parsed:
                            capture_datetime = parsed

            except Exception:
                pass

        # -------------------------------------------------
        # Build preview context
        # -------------------------------------------------

        ctx = TemplateContext(
            exif_datetime=capture_datetime,
            camera_make=camera_make,
            camera_model=camera_model,
            job_code=self.job_var.get(),
            custom_text=self.custom_var.get(),
            counter=counter,
            original_name=original,
            extension=extension,
        )

        folder = self.engine.render_folder(
            self.folder_template_var.get(),
            ctx,
        )

        filename = self.engine.render_filename_with_extension(
            self.filename_template_var.get(),
            ctx,
        )

        self.folder_preview_var.set(folder)
        self.filename_preview_var.set(filename)

    # =========================================================
    # CLEAR ACTIVE TEMPLATE
    # =========================================================

    def _clear_active_template(self):
        self.folder_template_var.set("")
        self.filename_template_var.set("")

    # =========================================================
    # COPY BUTTON
    # =========================================================

    def _copy_pressed(self):

        if self.copy_button_text.get() == "Copy":

            if (
                self.settings.duplicate_mode == "review"
                and self.current_plan
                and self.current_plan.review_items
            ):

                dlg = ReviewDialog(
                    self.root,
                    self.current_plan.review_items,
                )

                if dlg.result is None:

                    self.copy_button_text.set("Copy")
                    self._set_status("Ready")
                    self.progress_var.set("")

                    return

                self.current_plan.review_items = dlg.result

                for review in self.current_plan.review_items:

                    planned = review.incoming

                    if planned.decision != "rename":
                        continue

                    old_destination = planned.destination_path

                    new_filename = (
                        review.incoming.new_name
                        + old_destination.suffix
                    )

                    planned.destination_path = (
                        old_destination.parent / new_filename
                    )

                    planned.relative_destination = (
                        planned.relative_destination.parent / new_filename
                    )

                    if planned.xmp_destination:

                        planned.xmp_destination = (
                            planned.xmp_destination.parent
                            / (new_filename + ".xmp")
                        )

                        planned.relative_xmp_destination = (
                            planned.relative_xmp_destination.parent
                            / (new_filename + ".xmp")
                        )

                renamed = sum(
                    1
                    for item in dlg.result
                    if item.incoming.decision == "rename"
                )

                skipped = sum(
                    1
                    for item in dlg.result
                    if item.incoming.decision == "skip"
                )

                self._log("")
                self._log("------------------------------------------------------------")
                self._log("REVIEW")
                self._log("------------------------------------------------------------")
                self._log("")
                self._log(f"Conflicts ........... {len(dlg.result)}")
                self._log(f"Renamed ............ {renamed}")
                self._log(f"Skipped ............ {skipped}")
                self._log("")
                self._log("✓ Review complete.")
                self._log("")

                self.copy_button_text.set("Cancel")
                self._copy()

                return

            self.copy_button_text.set("Cancel")
            self._copy()

        else:

            self._log("")
            self._log("Cancellation requested...")

            self._set_status(
                "Cancelling..."
            )

            self.progress_var.set(
                "Cancelling after current file..."
            )

            self.copier.cancel()

    # =========================================================
    # ENABLE / DISABLE UI DURING COPY
    # =========================================================

    def _set_copy_mode(self, copying: bool):

        state = "disabled" if copying else "normal"

        self.scan_button.config(state=state)
        self.dry_run_button.config(state=state)
        self.add_files_button.config(state=state)
        self.add_folder_button.config(state=state)
        self.clear_button.config(state=state)
        self.save_template_button.config(state=state)
        self.save_as_button.config(state=state)
        self.delete_template_button.config(state=state)
        self.folder_template_entry.config(state=state)
        self.filename_template_entry.config(state=state)
        self.template_combo.config(
                state="disabled" if copying else "readonly"
        )

        # Copy button stays enabled because it becomes Cancel

     # =========================================================
     # LOG SESSION HEADER
     # =========================================================
    def _log_session_header(self):

        self._log("=" * 80)
        self._log("Photo Ingest 2.0")
        self._log("=" * 80)
        self._log("")

        self._log(f"Started      : {datetime.now():%Y-%m-%d %H:%M:%S}")
        folders = sum(Path(p).is_dir() for p in self.selected_files)
        files = len(self.selected_files) - folders

        if folders:
            self._log(f"Folders      : {folders}")

        if files:
            self._log(f"Files        : {files}")

        self._log(f"Destination  : {self.dest_var.get()}")

        if self.job_var.get():
            self._log(f"Job Code     : {self.job_var.get()}")

        if self.custom_var.get():
            self._log(f"Custom Text  : {self.custom_var.get()}")

        self._log(f"Counter      : {self.counter_var.get()}")

        self._log("")

     # =========================================================
     # PARSE EXIF
     # =========================================================

    def _parse_exif_datetime(self, value):

        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            try:
                return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
            except Exception:
                return None

        return None

    # =========================================================
    # CALLBACKS
    # =========================================================

    def _planner_progress(self, current, total, filename):

        def update():

            self.progress["mode"] = "determinate"
            self.progress["maximum"] = total
            self.progress["value"] = current

            self._set_progress_message(
                "Step 3 of 4\n\nBuilding ingest plan...",
                f"{current} / {total}\n{filename}"
            )

        self.root.after(0, update)


    def _set_progress(self, current, total, filename):
        def update_ui():

            self.progress["maximum"] = total
            self.progress["value"] = current

            self._set_progress_message(
                "Step 3 of 4\n\nBuilding ingest plan...",
                f"{current} / {total}\n{filename}"
            )

        self.root.after(0, update_ui)

    def _set_progress_message(
        self,
        title: str,
        subtitle: str = "",
    ) -> None:
        """
        Updates the progress text shown under the progress bar.
        """

        if subtitle:
            self.progress_var.set(
                f"{title}\n{subtitle}"
            )
        else:
            self.progress_var.set(title)

    def _log(self, message, tag=None):

        # ---------------------------------------------------------
        # Structured file operation
        # ---------------------------------------------------------

        if isinstance(message, dict):

            if message.get("type") == "operation":

                self.manifest_entries.append(message)

                self._log_operation(
                    filename=message["filename"],
                    destination=message["destination"],
                    result=message["result"],
                    new_name=message.get("new_name"),
                )

                return

        # ---------------------------------------------------------
        # Normal text message
        # ---------------------------------------------------------

        self.log.configure(state="normal")

        if tag:
            self.log.insert(
                "end",
                message + "\n",
                tag,
            )
        else:
            self.log.insert(
                "end",
                message + "\n",
            )

        self.log.see("end")
        self.log.configure(state="disabled")

    def _log_operation(
            self,
            filename,
            destination,
            result,
            new_name=None,
        ):

            self.log.configure(state="normal")

            # Filename
            self.log.insert(
                "end",
                f"{filename}\n",
            )

            # Destination
            self.log.insert(
                "end",
                f"Destination : {destination}\n",
            )

            # Result
            if result == "copied":

                self.log.insert(
                    "end",
                    "✓ Copied\n",
                    "success",
                )

            elif result == "renamed":

                self.log.insert(
                    "end",
                    "→ Renamed\n",
                    "rename",
                )

                if new_name:
                    self.log.insert(
                        "end",
                        f"New name    : {new_name}\n",
                    )

            elif result == "skipped":

                self.log.insert(
                    "end",
                    "→ Skipped\n",
                    "warning",
                )

            elif result == "replaced":

                self.log.insert(
                    "end",
                    "→ Replaced\n",
                    "copy",
                )

            elif result == "planned":

                self.log.insert(
                    "end",
                    "○ Planned\n",
                    "copy",
                )

            elif result == "error":

                self.log.insert(
                    "end",
                    "✗ Error\n",
                    "error",
                )

            self.log.insert(
                "end",
                "\n",
            )

            self.log.see("end")
            self.log.configure(state="disabled")

    def _set_status(self, msg):
        self.status_var.set(msg)

    def _dispatch_scan_event(self, event: str, data: Any) -> None:
        self.root.after(
            0,
            lambda: self._handle_scan_event(event, data)
        )

    def _handle_scan_event(self, event: str, data: Any):
        if event == "scan_progress_init":

            self.progress["maximum"] = max(data, 1)
            self.progress["value"] = 0

            self._set_progress_message(
                "Scanning...",
                f"0 / {data}"
            )

            self._set_status("Scanning...")

            return

        elif event == "scan_progress":

            current, total, filename = data

            self.progress["maximum"] = total
            self.progress["value"] = current

            self._set_progress_message(
                "Scanning...",
                f"{current} / {total}\n{filename}"
            )
        elif event == "scan_exif_start":

            self.progress.configure(mode="indeterminate")

            self.progress.start(12)

            self._set_progress_message(
                "Step 2 of 4\n\nReading EXIF metadata...",
                f"{data} RAW files\n\nThis may take a while."
            )

            self._set_status("Reading EXIF metadata...")

        elif event == "scan_exif_done":

            self.progress.stop()

            self.progress.configure(mode="determinate")

            self._set_progress_message(
                "Step 3 of 4\n\nBuilding ingest plan..."
            )

            self._set_status("Building ingest plan...")

        if event == "scan_info":
            self._log(str(data))

    def run(self):
        self.root.mainloop()

    def _log_header(self, title):
        self._log("")
        self._log("-" * 80)
        self._log(title)
        self._log("-" * 80)

    def _reset_progress(self):
        self.progress.configure(value=0)
        self.progress_var.set("")

    def _set_final_structure_available(self, available: bool):
        self.final_structure_button.configure(
            state="normal" if available else "disabled"
        )
