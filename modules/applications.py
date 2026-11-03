import os
import difflib
import ctypes
from ctypes import wintypes
from pathlib import Path
import psutil

def get_shortcuts():
    folders = [
        Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
        Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft/Windows/Start Menu/Programs"
    ]

    apps = {}
    for folder in folders:
        if not folder.exists():
            continue
        for shortcut in folder.rglob("*.lnk"):
            name = shortcut.stem.strip()
            if name:
                apps.setdefault(name.lower(), {
                    "name": name,
                    "path": str(shortcut)
                })
    return apps

def list_apps(query=""):
    apps = get_shortcuts()
    results = list(apps.values())

    if query.strip():
        q = query.lower().strip()
        results = [
            app for app in results
            if q in app["name"].lower()
        ]

    results.sort(key=lambda x: x["name"].lower())

    return {
        "count": len(results),
        "applications": results[:100]
    }

def find_app(name):
    apps = get_shortcuts()
    q = name.lower().strip()

    if q in apps:
        return apps[q]

    matches = [
        app for app in apps.values()
        if q in app["name"].lower()
    ]

    if not matches:
        names = [app["name"] for app in apps.values()]
        close = difflib.get_close_matches(name, names, n=5, cutoff=0.45)
        raise ValueError(
            "Application not found. Similar applications: "
            + (", ".join(close) if close else "none")
        )

    matches.sort(key=lambda x: len(x["name"]))
    if len(matches) > 1 and len(matches[0]["name"]) == len(matches[1]["name"]):
        raise ValueError("Multiple matches found: " + ", ".join(a["name"] for a in matches[:5]))

    return matches[0]

def open_app(name):
    app = find_app(name)
    os.startfile(app["path"])
    return f"Launch requested: {app['name']}"

def list_running_apps():
    user32 = ctypes.windll.user32
    results = []

    EnumWindows = user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
    )

    def callback(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd):
            return True

        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return True

        title_buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title_buffer, length + 1)
        title = title_buffer.value

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        try:
            process = psutil.Process(pid.value)
            process_name = process.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            process_name = "Unknown"

        results.append({
            "title": title,
            "process": process_name,
            "pid": pid.value
        })
        return True

    EnumWindows(EnumWindowsProc(callback), 0)
    return results[:100]

def close_app(name):
    user32 = ctypes.windll.user32
    WM_CLOSE = 0x0010
    q = name.lower().replace(" ", "").replace("_", "")

    windows = list_running_apps()
    matches = [
        w for w in windows
        if q in w["title"].lower().replace(" ", "").replace("_", "")
        or q in w["process"].lower().replace(" ", "").replace("_", "")
    ]

    if not matches:
        raise ValueError(f"No visible application window matched '{name}'.")

    closed = 0
    for item in matches:
        hwnd_match = {"hwnd": None}

        EnumWindowsProc = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
        )

        def callback(hwnd, lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == item["pid"]:
                length = user32.GetWindowTextLengthW(hwnd)
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                if buf.value == item["title"]:
                    hwnd_match["hwnd"] = hwnd
                    return False
            return True

        user32.EnumWindows(EnumWindowsProc(callback), 0)

        if hwnd_match["hwnd"]:
            user32.PostMessageW(hwnd_match["hwnd"], WM_CLOSE, 0, 0)
            closed += 1

    return f"Sent graceful close request to {closed} window(s) matching {name}."
