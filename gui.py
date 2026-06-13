#!/usr/bin/env python3
"""
gui.py — Tkinter GUI wrapper for the file_analyzer CLI tool.
Run:  python3 gui.py
The binary is expected at  bin/file_analyzer  relative to this script,
or set the environment variable FILE_ANALYZER_BIN to point elsewhere.
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, font, messagebox, ttk
from datetime import datetime

# ──────────────────────────────────────────────────────────────────────────────
#  Locate the binary
# ──────────────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BIN = os.path.join(SCRIPT_DIR, "bin", "file_analyzer")
BIN = os.environ.get("FILE_ANALYZER_BIN", DEFAULT_BIN)

# ──────────────────────────────────────────────────────────────────────────────
#  Colour & font tokens  (dark terminal aesthetic, feels native to the tool)
# ──────────────────────────────────────────────────────────────────────────────
BG          = "#0f1117"   # near-black background
BG2         = "#1a1d27"   # card / panel background
BG3         = "#23263a"   # subtle raised surface
ACCENT      = "#5b6af0"   # indigo – primary interactive
ACCENT_HOV  = "#7b8bf7"
GREEN       = "#3dd68c"   # positive / success
YELLOW      = "#f5c842"   # warning / timing
RED         = "#f05b5b"   # error
TEXT        = "#e8eaf6"   # primary text
MUTED       = "#7e84a3"   # secondary / label text
BORDER      = "#2a2d42"   # divider lines
WHITE       = "#ffffff"

FONT_MONO   = ("JetBrains Mono", 11) if sys.platform != "darwin" else ("Menlo", 12)
FONT_BODY   = ("Inter", 11)          if sys.platform != "darwin" else ("SF Pro Text", 12)
FONT_HEAD   = ("Inter", 13, "bold")  if sys.platform != "darwin" else ("SF Pro Display", 13, "bold")
FONT_TITLE  = ("Inter", 20, "bold")  if sys.platform != "darwin" else ("SF Pro Display", 20, "bold")
FONT_LABEL  = ("Inter", 10)          if sys.platform != "darwin" else ("SF Pro Text", 11)

# ──────────────────────────────────────────────────────────────────────────────
#  Output parser
# ──────────────────────────────────────────────────────────────────────────────
def parse_output(raw: str, directory: str = "") -> dict:
    """
    Parse the stdout of file_analyzer into a structured dict.
    The binary format is:  'Files   : 18'  (padded spaces before the colon).
    Returns keys: files, bytes_mb, lines, words, largest, exec_ms, file_list, raw
    """
    result = {
        "files": "—", "bytes_mb": "—", "lines": "—",
        "words": "—", "largest": "—", "exec_ms": "—",
        "file_list": [], "raw": raw,
    }

    for line in raw.splitlines():
        line = line.strip()

        # Pattern: 'Files   : 18'  — any amount of whitespace around the colon
        m = re.match(r"Files\s*:\s*(\d+)", line)
        if m:
            result["files"] = int(m.group(1))

        m = re.match(r"Bytes\s*:\s*(\d+)", line)
        if m:
            b = int(m.group(1))
            result["bytes_mb"] = f"{b / 1_048_576:.3f} MB"

        m = re.match(r"Lines\s*:\s*(\d+)", line)
        if m:
            result["lines"] = int(m.group(1))

        m = re.match(r"Words\s*:\s*(\d+)", line)
        if m:
            result["words"] = int(m.group(1))

        # 'Largest : /some/path (N bytes)'
        m = re.match(r"Largest\s*:\s*(.+)", line)
        if m:
            result["largest"] = m.group(1).strip()

        # 'Execution Time: 16.579 ms'
        m = re.match(r"Execution\s+Time\s*:\s*([\d.]+)\s*ms", line, re.IGNORECASE)
        if m:
            result["exec_ms"] = f"{float(m.group(1)):.3f} ms"

    # The binary never prints individual paths — collect them via os.walk
    if directory and os.path.isdir(directory):
        for root, _dirs, filenames in os.walk(directory):
            for fname in sorted(filenames):
                result["file_list"].append(os.path.join(root, fname))

    return result


# ──────────────────────────────────────────────────────────────────────────────
#  Styled widgets helpers
# ──────────────────────────────────────────────────────────────────────────────
def _styled_button(parent, text, command, width=14, bg=ACCENT, fg=WHITE):
    btn = tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=fg, activebackground=ACCENT_HOV, activeforeground=WHITE,
        relief="flat", cursor="hand2", padx=12, pady=6,
        font=FONT_BODY, width=width, bd=0,
    )
    btn.bind("<Enter>", lambda e: btn.config(bg=ACCENT_HOV))
    btn.bind("<Leave>", lambda e: btn.config(bg=bg))
    return btn


def _label(parent, text, **kw):
    defaults = dict(bg=BG2, fg=MUTED, font=FONT_LABEL, anchor="w")
    defaults.update(kw)
    return tk.Label(parent, text=text, **defaults)


def _value_label(parent, text="—", **kw):
    defaults = dict(bg=BG2, fg=TEXT, font=FONT_HEAD, anchor="w")
    defaults.update(kw)
    return tk.Label(parent, text=text, **defaults)


def _stat_card(parent, title, row, col, colspan=1):
    """Returns (frame, value_var) for a single stat card."""
    frame = tk.Frame(parent, bg=BG3, padx=14, pady=10)
    frame.grid(row=row, column=col, columnspan=colspan,
               padx=6, pady=6, sticky="nsew")
    tk.Label(frame, text=title, bg=BG3, fg=MUTED, font=FONT_LABEL).pack(anchor="w")
    var = tk.StringVar(value="—")
    tk.Label(frame, textvariable=var, bg=BG3, fg=TEXT, font=FONT_HEAD).pack(anchor="w", pady=(2, 0))
    return frame, var


# ──────────────────────────────────────────────────────────────────────────────
#  Main application
# ──────────────────────────────────────────────────────────────────────────────
class FileAnalyzerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("File Analyzer")
        self.configure(bg=BG)
        self.geometry("1080x760")
        self.minsize(860, 620)
        self.resizable(True, True)

        self._scan_history: list[dict] = []   # list of result dicts
        self._scanning = False

        self._build_ui()

    # ── UI construction ────────────────────────────────────────────────────────
    def _build_ui(self):
        # Top title bar
        title_bar = tk.Frame(self, bg=BG, pady=16)
        title_bar.pack(fill="x", padx=28)
        tk.Label(title_bar, text="File Analyzer", bg=BG, fg=WHITE,
                 font=FONT_TITLE).pack(side="left")
        tk.Label(title_bar, text="PDC Project by LabaikGroup",
                 bg=BG, fg=MUTED, font=FONT_LABEL).pack(side="left", padx=12, pady=4)

        # Main notebook (tabs)
        style = ttk.Style(self)
        style.theme_use("default")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab",
                        background=BG3, foreground=MUTED,
                        padding=[16, 8], font=FONT_BODY, borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", WHITE)])

        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill="both", expand=True, padx=20, pady=(0, 16))

        # Tab 1 – Scanner
        self._tab_scan = tk.Frame(self._notebook, bg=BG)
        self._notebook.add(self._tab_scan, text="  Scanner  ")
        self._build_scanner_tab(self._tab_scan)

        # Tab 2 – Scan History
        self._tab_history = tk.Frame(self._notebook, bg=BG)
        self._notebook.add(self._tab_history, text="  Scan History  ")
        self._build_history_tab(self._tab_history)

    # ── Scanner tab ────────────────────────────────────────────────────────────
    def _build_scanner_tab(self, parent):
        # ── Controls row ──────────────────────────────────────────────────────
        ctrl = tk.Frame(parent, bg=BG2, padx=18, pady=14)
        ctrl.pack(fill="x", padx=16, pady=(14, 0))

        # Directory row
        dir_row = tk.Frame(ctrl, bg=BG2)
        dir_row.pack(fill="x")

        _label(dir_row, "Directory", bg=BG2).pack(side="left")

        self._dir_var = tk.StringVar()
        dir_entry = tk.Entry(
            dir_row, textvariable=self._dir_var,
            bg=BG3, fg=TEXT, insertbackground=TEXT,
            relief="flat", font=FONT_MONO, bd=0,
        )
        dir_entry.pack(side="left", fill="x", expand=True, padx=(8, 8), ipady=6)

        browse_btn = _styled_button(dir_row, "Browse…", self._browse, width=10, bg=BG3, fg=TEXT)
        browse_btn.pack(side="left")

        # Options row
        opts_row = tk.Frame(ctrl, bg=BG2, pady=10)
        opts_row.pack(fill="x")

        _label(opts_row, "Scan Mode", bg=BG2).pack(side="left")

        self._mode_var = tk.StringVar(value="Sequential Scan")
        mode_menu = ttk.Combobox(
            opts_row, textvariable=self._mode_var,
            values=[
                "Sequential Scan",
                "Parallel Scan (Pthreads)",
                "Parallel Scan (OpenMP)",
            ],
            state="readonly", width=26,
            font=FONT_BODY,
        )
        style = ttk.Style()
        style.configure("TCombobox",
                        fieldbackground=BG3, background=BG3,
                        foreground=TEXT, selectbackground=ACCENT,
                        selectforeground=WHITE)
        mode_menu.pack(side="left", padx=(8, 16), ipady=4)
        mode_menu.bind("<<ComboboxSelected>>", self._on_mode_change)

        # Workers (hidden until Pthreads selected)
        self._workers_frame = tk.Frame(opts_row, bg=BG2)
        _label(self._workers_frame, "Workers", bg=BG2).pack(side="left")
        self._workers_var = tk.StringVar(value="4")
        workers_entry = tk.Entry(
            self._workers_frame, textvariable=self._workers_var,
            bg=BG3, fg=TEXT, insertbackground=TEXT,
            relief="flat", font=FONT_MONO, width=5, bd=0,
        )
        workers_entry.pack(side="left", padx=(8, 0), ipady=6)

        # Scan button
        self._scan_btn = _styled_button(opts_row, "Scan", self._start_scan, width=10)
        self._scan_btn.pack(side="right")

        # Status bar
        self._status_var = tk.StringVar(value="Ready")
        status_bar = tk.Frame(parent, bg=BG2, pady=6)
        status_bar.pack(fill="x", padx=16, pady=(2, 0))
        self._status_label = tk.Label(
            status_bar, textvariable=self._status_var,
            bg=BG2, fg=MUTED, font=FONT_LABEL, anchor="w"
        )
        self._status_label.pack(side="left", padx=10)

        self._exec_var = tk.StringVar(value="")
        tk.Label(status_bar, textvariable=self._exec_var,
                 bg=BG2, fg=YELLOW, font=FONT_LABEL).pack(side="right", padx=10)

        # ── Results area ──────────────────────────────────────────────────────
        results_outer = tk.Frame(parent, bg=BG)
        results_outer.pack(fill="both", expand=True, padx=16, pady=10)

        # Stats grid (left column)
        stats_col = tk.Frame(results_outer, bg=BG, width=320)
        stats_col.pack(side="left", fill="y", padx=(0, 10))
        stats_col.pack_propagate(False)

        tk.Label(stats_col, text="Analysis Summary",
                 bg=BG, fg=MUTED, font=FONT_LABEL, anchor="w").pack(anchor="w", pady=(0, 4))

        stats_grid = tk.Frame(stats_col, bg=BG)
        stats_grid.pack(fill="x")
        stats_grid.columnconfigure(0, weight=1)
        stats_grid.columnconfigure(1, weight=1)

        _, self._sv_files   = _stat_card(stats_grid, "Files",      0, 0)
        _, self._sv_bytes   = _stat_card(stats_grid, "Size",        0, 1)
        _, self._sv_lines   = _stat_card(stats_grid, "Lines",       1, 0)
        _, self._sv_words   = _stat_card(stats_grid, "Words",       1, 1)
        _, self._sv_exec    = _stat_card(stats_grid, "Exec Time",   2, 0)
        _, self._sv_largest = _stat_card(stats_grid, "Largest File", 2, 1)

        # Separator
        sep = tk.Frame(results_outer, bg=BORDER, width=1)
        sep.pack(side="left", fill="y", padx=(0, 10))

        # File list (right column)
        files_col = tk.Frame(results_outer, bg=BG)
        files_col.pack(side="left", fill="both", expand=True)

        tk.Label(files_col, text="Files in Directory",
                 bg=BG, fg=MUTED, font=FONT_LABEL, anchor="w").pack(anchor="w", pady=(0, 4))

        list_frame = tk.Frame(files_col, bg=BG3)
        list_frame.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(list_frame, bg=BG3, troughcolor=BG3,
                                 activebackground=ACCENT, relief="flat")
        scrollbar.pack(side="right", fill="y")

        self._file_listbox = tk.Listbox(
            list_frame,
            bg=BG3, fg=TEXT, selectbackground=ACCENT, selectforeground=WHITE,
            relief="flat", bd=0, font=FONT_MONO,
            activestyle="none", yscrollcommand=scrollbar.set,
            highlightthickness=0,
        )
        self._file_listbox.pack(fill="both", expand=True, padx=4, pady=4)
        scrollbar.config(command=self._file_listbox.yview)

    # ── History tab ────────────────────────────────────────────────────────────
    def _build_history_tab(self, parent):
        pane = tk.PanedWindow(parent, orient="horizontal", bg=BG,
                              sashwidth=4, sashrelief="flat")
        pane.pack(fill="both", expand=True, padx=16, pady=14)

        # Left: history list
        left = tk.Frame(pane, bg=BG2, width=280)
        pane.add(left, minsize=200)

        header = tk.Frame(left, bg=BG2)
        header.pack(fill="x", padx=10, pady=(10, 6))
        tk.Label(header, text="Scan History", bg=BG2, fg=TEXT,
                 font=FONT_HEAD, anchor="w").pack(side="left")

        clear_btn = _styled_button(header, "Clear", self._clear_history,
                                   width=6, bg=RED, fg=WHITE)
        clear_btn.pack(side="right")

        list_scroll = tk.Scrollbar(left, bg=BG2, troughcolor=BG2,
                                   activebackground=ACCENT, relief="flat")
        list_scroll.pack(side="right", fill="y")

        self._hist_listbox = tk.Listbox(
            left, bg=BG2, fg=TEXT, selectbackground=ACCENT, selectforeground=WHITE,
            relief="flat", bd=0, font=FONT_BODY, activestyle="none",
            highlightthickness=0, yscrollcommand=list_scroll.set,
        )
        self._hist_listbox.pack(fill="both", expand=True, padx=6, pady=(0, 8))
        list_scroll.config(command=self._hist_listbox.yview)
        self._hist_listbox.bind("<<ListboxSelect>>", self._on_history_select)

        # Right: history detail
        right = tk.Frame(pane, bg=BG)
        pane.add(right, minsize=400)

        self._hist_detail_frame = tk.Frame(right, bg=BG)
        self._hist_detail_frame.pack(fill="both", expand=True)
        self._build_history_detail_empty()

    def _build_history_detail_empty(self):
        for w in self._hist_detail_frame.winfo_children():
            w.destroy()
        tk.Label(self._hist_detail_frame,
                 text="Select a scan from the list to view details.",
                 bg=BG, fg=MUTED, font=FONT_BODY).pack(pady=40)

    def _build_history_detail(self, entry: dict):
        for w in self._hist_detail_frame.winfo_children():
            w.destroy()

        f = self._hist_detail_frame

        # Header
        meta = tk.Frame(f, bg=BG2, padx=14, pady=12)
        meta.pack(fill="x", pady=(0, 8))
        tk.Label(meta, text=entry["directory"], bg=BG2, fg=WHITE,
                 font=FONT_HEAD, anchor="w", wraplength=500).pack(anchor="w")
        sub = f"{entry['mode']}  ·  {entry['timestamp']}"
        tk.Label(meta, text=sub, bg=BG2, fg=MUTED, font=FONT_LABEL).pack(anchor="w")

        # Stats cards
        sg = tk.Frame(f, bg=BG)
        sg.pack(fill="x", padx=0, pady=(0, 8))
        sg.columnconfigure(0, weight=1); sg.columnconfigure(1, weight=1)
        sg.columnconfigure(2, weight=1); sg.columnconfigure(3, weight=1)

        def _hcard(parent, title, val, row, col):
            card = tk.Frame(parent, bg=BG3, padx=12, pady=8)
            card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            tk.Label(card, text=title, bg=BG3, fg=MUTED, font=FONT_LABEL).pack(anchor="w")
            tk.Label(card, text=str(val), bg=BG3, fg=TEXT, font=FONT_HEAD).pack(anchor="w")

        r = entry["result"]
        _hcard(sg, "Files",     r["files"],    0, 0)
        _hcard(sg, "Size",      r["bytes_mb"], 0, 1)
        _hcard(sg, "Lines",     r["lines"],    0, 2)
        _hcard(sg, "Words",     r["words"],    0, 3)
        _hcard(sg, "Exec Time", r["exec_ms"],  1, 0)

        largest = tk.Frame(f, bg=BG3, padx=14, pady=10)
        largest.pack(fill="x", padx=4, pady=(0, 8))
        tk.Label(largest, text="Largest File", bg=BG3, fg=MUTED, font=FONT_LABEL).pack(anchor="w")
        tk.Label(largest, text=r["largest"], bg=BG3, fg=GREEN,
                 font=FONT_MONO, wraplength=600, anchor="w").pack(anchor="w")

        # File list
        tk.Label(f, text=f"Files ({len(r['file_list'])})",
                 bg=BG, fg=MUTED, font=FONT_LABEL, anchor="w").pack(anchor="w", padx=4)

        lf = tk.Frame(f, bg=BG3)
        lf.pack(fill="both", expand=True, padx=4, pady=(2, 0))
        sb = tk.Scrollbar(lf, bg=BG3, troughcolor=BG3,
                          activebackground=ACCENT, relief="flat")
        sb.pack(side="right", fill="y")
        lb = tk.Listbox(lf, bg=BG3, fg=TEXT, selectbackground=ACCENT,
                        relief="flat", bd=0, font=FONT_MONO, activestyle="none",
                        highlightthickness=0, yscrollcommand=sb.set)
        lb.pack(fill="both", expand=True, padx=4, pady=4)
        sb.config(command=lb.yview)
        for p in r["file_list"]:
            lb.insert("end", p)

    # ── Event handlers ─────────────────────────────────────────────────────────
    def _browse(self):
        d = filedialog.askdirectory(title="Select Directory to Scan")
        if d:
            self._dir_var.set(d)

    def _on_mode_change(self, _event=None):
        mode = self._mode_var.get()
        if "Pthreads" in mode:
            self._workers_frame.pack(side="left", padx=(0, 16))
        else:
            self._workers_frame.pack_forget()

    def _start_scan(self):
        if self._scanning:
            return

        path = self._dir_var.get().strip()
        if not path:
            messagebox.showwarning("No Directory", "Please enter or browse to a directory.")
            return
        if not os.path.isdir(path):
            messagebox.showerror("Invalid Directory", f"'{path}' is not a valid directory.")
            return
        if not os.path.isfile(BIN):
            messagebox.showerror(
                "Binary Not Found",
                f"file_analyzer binary not found at:\n{BIN}\n\nRun `make` to build it first."
            )
            return

        mode_str = self._mode_var.get()
        if "Pthreads" in mode_str:
            mode_flag = "2"
        elif "OpenMP" in mode_str:
            mode_flag = "3"
        else:
            mode_flag = "1"

        workers = None
        if mode_flag == "2":
            try:
                workers = int(self._workers_var.get())
                if workers < 1:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid Workers", "Workers must be a positive integer.")
                return

        self._scanning = True
        self._scan_btn.config(state="disabled", bg=MUTED)
        self._status_var.set("Scanning…")
        self._status_label.config(fg=YELLOW)
        self._exec_var.set("")
        self._clear_results()

        threading.Thread(
            target=self._run_scan,
            args=(path, mode_flag, workers, mode_str),
            daemon=True,
        ).start()

    def _run_scan(self, path: str, mode: str, workers, mode_label: str):
        cmd = [BIN, "--mode", mode, "--path", path]
        if workers is not None:
            cmd += ["--workers", str(workers)]

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300
            )
            output = proc.stdout + proc.stderr
        except subprocess.TimeoutExpired:
            output = "ERROR: scan timed out after 300 s"
        except Exception as exc:
            output = f"ERROR: {exc}"

        result = parse_output(output, path)
        self.after(0, self._on_scan_done, result, mode_label, path)

    def _on_scan_done(self, result: dict, mode_label: str, path: str):
        self._scanning = False
        self._scan_btn.config(state="normal", bg=ACCENT)
        self._status_var.set("Scan complete")
        self._status_label.config(fg=GREEN)
        self._exec_var.set(f"⏱  {result['exec_ms']}")

        # Update stat cards
        self._sv_files.set(str(result["files"]))
        self._sv_bytes.set(result["bytes_mb"])
        self._sv_lines.set(str(result["lines"]))
        self._sv_words.set(str(result["words"]))
        self._sv_exec.set(result["exec_ms"])
        self._sv_largest.set(result["largest"])

        # File list
        self._file_listbox.delete(0, "end")
        for p in result["file_list"]:
            self._file_listbox.insert("end", p)

        # Save to history
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "mode": mode_label,
            "directory": path,
            "result": result,
        }
        self._scan_history.append(entry)
        label = f"#{len(self._scan_history)}  {mode_label[:12]}…  {result['exec_ms']}"
        self._hist_listbox.insert("end", label)

    def _clear_results(self):
        for var in (self._sv_files, self._sv_bytes, self._sv_lines,
                    self._sv_words, self._sv_exec, self._sv_largest):
            var.set("—")
        self._file_listbox.delete(0, "end")

    def _on_history_select(self, _event=None):
        sel = self._hist_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < len(self._scan_history):
            self._build_history_detail(self._scan_history[idx])

    def _clear_history(self):
        if not self._scan_history:
            return
        if messagebox.askyesno("Clear History", "Delete all scan history?"):
            self._scan_history.clear()
            self._hist_listbox.delete(0, "end")
            self._build_history_detail_empty()


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = FileAnalyzerApp()
    app.mainloop()