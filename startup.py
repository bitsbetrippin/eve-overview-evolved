"""Portable entry point: use the included interpreter, packages and Tk files."""
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import runpy
import sys
import traceback

ROOT = Path(__file__).resolve().parent


def prepare():
    os.chdir(ROOT)
    # -I ignores external Python settings; explicitly allow our source modules.
    sys.path.insert(0, str(ROOT))
    os.environ["TCL_LIBRARY"] = "runtime/tcl/tcl8.6"
    os.environ["TK_LIBRARY"] = "runtime/tcl/tk8.6"
    os.environ.pop("TCLLIBPATH", None)
    for name in ("app_info.py", "ratting.py", "eve_paths.py", "combat_meter.py", "window_placement.py", "neut_meter.py", "ewar_alerts.py", "runtime/tcl/tcl8.6/init.tcl",
                 "runtime/tcl/tk8.6/tk.tcl", "assets/initiative.png", "assets/scrambled.wav",
                 "assets/pointed.wav", "assets/webbed.wav"):
        if not (ROOT / name).is_file():
            raise FileNotFoundError(f"Missing {name}. Extract the entire portable release ZIP.")


def self_test():
    """Offline check; does not open EVE logs or read the clipboard."""
    for module in ("tkinter", "ssl", "pyperclip", "pystray", "PIL.Image", "watchdog.observers"):
        importlib.import_module(module)
    import tkinter
    from eve_paths import find_eve_log_path
    from app_info import APP_NAME, RELEASE_TAG, REPOSITORY_URL, CONTRIBUTOR
    root = tkinter.Tk()
    root.withdraw()
    try:
        tk_version = root.tk.call("info", "patchlevel")
        root.update_idletasks()
    finally:
        root.destroy()
    for name in ("ratting.py", "combat_meter.py", "window_placement.py", "neut_meter.py", "ewar_alerts.py", "eve_paths.py", "app_info.py"):
        compile((ROOT / name).read_bytes(), name, "exec")
    print(json.dumps({
        "status": "ok", "app": APP_NAME, "release": RELEASE_TAG,
        "repository": REPOSITORY_URL, "contributor": CONTRIBUTOR,
        "python": sys.version.split()[0],
        "executable": sys.executable, "folder": str(ROOT), "tk": tk_version,
        "eve_logs": find_eve_log_path("Gamelogs"),
        "packages": {name: importlib.metadata.version(name)
                     for name in ("pyperclip", "pystray", "Pillow", "watchdog", "six")},
    }, indent=2))


def main():
    try:
        prepare()
        if sys.argv[1:] == ["--self-test"]:
            self_test()
        elif sys.argv[1:]:
            raise ValueError("Launch START.bat with no arguments to open Eve-Overlay-Evolved.")
        else:
            runpy.run_path(str(ROOT / "ratting.py"), run_name="__main__")
        return 0
    except Exception:
        details = traceback.format_exc()
        print(details, file=sys.stderr)
        try:
            (ROOT / "startup.log").write_text(details, encoding="utf-8")
        except OSError:
            print("Cannot write startup.log. Extract to a writable folder.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
