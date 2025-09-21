import json
import os
import platform
import queue
import shutil
import signal
import subprocess
import sys
import threading
from pathlib import Path
from datetime import datetime

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# -------------------------------
# Persistent config (per-user)
# -------------------------------
APP_NAME = "WatchGCG-GUI"
CONFIG_DIR = os.path.join(Path.home(), f".{APP_NAME.lower()}")
CONFIG_FILE = os.path.join(CONFIG_DIR, "folders.json")

FOLDER_KEYS = {
    "gcg":   "Last folder used for GCG files",
    "lex":   "Last folder used for Lexicon CSV/TXT",
    "score": "Last folder used for Score output",
    "unseen":"Last folder used for Unseen tiles output",
    "count": "Last folder used for Unseen count output",
    "lp":    "Last folder used for Last-play output",
}

SUCCESS_MARK = "To stop execution, hit control-C."  # used to gate log output

# -------------------------------
# Folder memory helpers
# -------------------------------
def load_all_folders():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_last_folder(folder_path, key="last_folder"):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    data = load_all_folders()
    data[key] = folder_path
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def load_last_folder(key="last_folder"):
    data = load_all_folders()
    return data.get(key)

# -------------------------------
# Dependency: watchfiles
# -------------------------------
def has_watchfiles():
    try:
        import watchfiles  # noqa: F401
        return True
    except Exception:
        return False


def install_watchfiles(parent):
    py = sys.executable or "python"
    cmd = [py, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"]
    try:
        subprocess.check_call(cmd)
    except Exception:
        # Not fatal; try to install watchfiles anyway
        pass

    try:
        subprocess.check_call([py, "-m", "pip", "install", "watchfiles"])
        messagebox.showinfo("Installation complete", "Installed 'watchfiles' successfully.")
        return True
    except subprocess.CalledProcessError as e:
        messagebox.showerror(
            "Installation failed",
            f"Automatic install of 'watchfiles' failed.\n\nError:\n{e}\n\n"
            "Please run:\npython -m pip install watchfiles"
        )
        return False

# -------------------------------
# Runner that spawns watch_gcg.py (shows only post-success logs)
# -------------------------------
class TailRunner:
    def __init__(self, on_log):
        self.on_log = on_log
        self.proc = None
        self.q = queue.Queue()
        self.thread = None
        self.show_after_success = False
        self._gcg_display = None

    def start(self, python_exe, script_path, args, gcg_path=None):
        if self.proc:
            self.on_log("[warn] Already running.\n")
            return
        self._gcg_display = Path(gcg_path).name if gcg_path else None
        cmd = [python_exe, "-u", script_path] + args
        self.on_log(f"[info] Launching: {' '.join(cmd)}\n")

        def reader():
            try:
                self.proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                    bufsize=1,
                )
                # Stream stdout lines
                for raw in self.proc.stdout:
                    line = raw if raw is not None else ""
                    if not self.show_after_success and SUCCESS_MARK in line:
                        self.show_after_success = True
                        gcg_filename = self._gcg_display or "the selected GCG file"
                        self.q.put(f"\n\n\n!!! SUCCESS !!!\nSuccessfully starting watching {gcg_filename} for changes.\n"
                                   "Any syntax or error messages after this message are legitimate and should be reported to the developer.\n"
                                   "To stop execution, exit out of this window.\n")
                        continue
                    if self.show_after_success:
                        self.q.put(line)
            except FileNotFoundError:
                self.q.put("[error] Could not start Python or script.\n")
            finally:
                self.q.put("[info] Process exited.\n")

        self.thread = threading.Thread(target=reader, daemon=True)
        self.thread.start()

    def poll(self):
        try:
            while True:
                self.on_log(self.q.get_nowait())
        except queue.Empty:
            pass

    def stop(self):
        if not self.proc:
            return
        try:
            if os.name == "nt":
                # Graceful on Windows
                self.proc.terminate()
            else:
                self.proc.send_signal(signal.SIGTERM)
        except Exception:
            pass
        self.proc = None
        self.thread = None
        self.show_after_success = False

# -------------------------------
# Main GUI
# -------------------------------
class App(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        master.title("WatchGCG")
        master.geometry("780x560")
        master.minsize(700, 520)
        self.pack(fill="both", expand=True)

        os.makedirs(CONFIG_DIR, exist_ok=True)

        # Build UI
        self._make_file_picker_section()
        self._make_controls()
        self._make_log()

        # Runner + polling
        self.runner = TailRunner(self._append_log)
        self.after(120, self._poll_runner)

        # Dependency check on startup
        self._refresh_watchfiles_state(first_run=True)

        # Stop child on window close
        master.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- UI: file pickers ----------
    def _make_file_picker_section(self):
        self.inputs = {}
        fields = [
            ("gcg",   "GCG file (.gcg)",          [("GCG files", "*.gcg")]),
            ("lex",   "Lexicon file (.csv)", [("CSV", "*.csv")]),
            ("score", "Score (.txt)",      [("Text", "*.txt")]),
            ("unseen","Unseen tiles (.txt)",[("Text", "*.txt")]),
            ("count", "Unseen count (.txt)",[("Text", "*.txt")]),
            ("lp",    "Last play (.txt)",  [("Text", "*.txt")]),
        ]

        frm = ttk.LabelFrame(self, text="Paths")
        frm.pack(fill="x", padx=10, pady=10)

        for key, label, patterns in fields:
            row = ttk.Frame(frm)
            row.pack(fill="x", padx=8, pady=6)

            ttk.Label(row, text=label, width=28).pack(side="left")
            var = tk.StringVar()
            ent = ttk.Entry(row, textvariable=var)
            ent.pack(side="left", fill="x", expand=True, padx=(0, 8))

            def make_browse(k=key, pats=patterns, evar=var, dialog_label=label):
                def browse():
                    lastdir = load_last_folder(k) or os.getcwd()
                    path = filedialog.askopenfilename(
                        parent=self,
                        title=f"Choose {dialog_label}",
                        initialdir=lastdir,
                        filetypes=pats
                    )

                    if path:
                        evar.set(path)
                        save_last_folder(os.path.dirname(path), k)
                return browse

            ttk.Button(row, text="Browse…", command=make_browse()).pack(side="left")

            self.inputs[key] = var


    # ---------- UI: controls ----------
    def _make_controls(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=10, pady=(0, 10))

        self.python_var = tk.StringVar(value=sys.executable or "python")
        ttk.Label(bar, text="Python exe:").pack(side="left")
        py_entry = ttk.Entry(bar, textvariable=self.python_var, width=42)
        py_entry.pack(side="left", padx=(4, 10))

        def choose_python():
            path = filedialog.askopenfilename(title="Choose Python executable")
            if path:
                self.python_var.set(path)
        ttk.Button(bar, text="Find…", command=choose_python).pack(side="left", padx=(0, 12))

        ttk.Button(bar, text="Start", command=self.on_start).pack(side="right")
        # Install button appears ONLY when watchfiles is missing
        self.install_btn = ttk.Button(bar, text="Install 'watchfiles'…", command=self._install_now)
        # Don’t pack it yet; we’ll pack when needed

    # ---------- UI: log ----------
    def _make_log(self):
        logfrm = ttk.LabelFrame(self, text="Log")
        logfrm.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        btnbar = ttk.Frame(logfrm)
        btnbar.pack(side="bottom",fill="x", padx=8, pady=(0, 8))
        ttk.Button(btnbar, text="Copy log", command=self._copy_log).pack(side="left")
        ttk.Button(btnbar, text="Clear", command=self._clear_log).pack(side="left", padx=(6, 0))

        self.log_text = tk.Text(logfrm, wrap="word", height=18, state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=8, pady=8)


    def _append_log(self, s: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{ts}] {s}")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _copy_log(self):
        text = self.log_text.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("Copied", "Log copied to clipboard.")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    # ---------- Start / stop ----------
    def on_start(self):
        # If watchfiles isn't installed, prompt now
        if not has_watchfiles():
            if messagebox.askyesno("Missing dependency", "The 'watchfiles' package is required. Install it now?"):
                if not install_watchfiles():
                    return
                self._refresh_watchfiles_state()  # hide the button if succeed
            else:
                return

        vals = {k: v.get().strip() for k, v in self.inputs.items()}
        missing = [k for k in ("gcg", "lex", "score", "unseen", "count", "lp") if not vals.get(k)]
        if missing:
            messagebox.showwarning("Missing fields", f"Please choose files for: {', '.join(missing)}")
            return

        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "watch_gcg.py")
        if not os.path.exists(script_path):
            messagebox.showerror("Not found", f"Could not find watch_gcg.py next to this file.\n\nTried: {script_path}")
            return

        args = [
            "--gcg", vals["gcg"],
            "--lex", vals["lex"],
            "--score", vals["score"],
            "--unseen", vals["unseen"],
            "--count", vals["count"],
            "--lp", vals["lp"],
        ]

        # Persist directories again (covers manual edits)
        for k, v in vals.items():
            if v:
                save_last_folder(os.path.dirname(v), k)

        self.runner.start(self.python_var.get(), script_path, args, gcg_path=vals["gcg"])

    def _on_close(self):
        self.runner.stop()
        self.master.destroy()

    # ---------- Poll runner ----------
    def _poll_runner(self):
        self.runner.poll()
        self.after(120, self._poll_runner)

    # ---------- Dependency UI state ----------
    def _refresh_watchfiles_state(self, first_run=False):
        ok = has_watchfiles()
        if ok:
            # Hide install button if it was visible
            try:
                self.install_btn.pack_forget()
            except Exception:
                pass
            if first_run is False:
                messagebox.showinfo("Ready", "'watchfiles' is installed. You can press Start.")
        else:
            # Offer install immediately on first run
            if first_run:
                if messagebox.askyesno(
                    "Missing dependency",
                    "WatchGCG requires the 'watchfiles' package.\n\nInstall it now?"
                ):
                    if install_watchfiles():
                        self._refresh_watchfiles_state()
                        return
            # If still missing, show the button
            self.install_btn.pack(side="left")

    def _install_now(self):
        if install_watchfiles():
            self._refresh_watchfiles_state()

# -------------------------------
# main
# -------------------------------
def main():
    root = tk.Tk()
    # Slightly larger default scaling, if supported
    try:
        root.call("tk", "scaling", 1.25)
    except Exception:
        pass
    style = ttk.Style(root)
    if "vista" in style.theme_names():
        style.theme_use("vista")
    App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
