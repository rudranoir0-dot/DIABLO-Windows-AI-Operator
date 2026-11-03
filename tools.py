
import os
import platform
import ctypes
import psutil
import subprocess
import time
from pathlib import Path
from datetime import datetime
from difflib import get_close_matches


# ============================================================
# WINDOWS AI OPERATOR — TOOL MODULE
# ============================================================

# Only allow file operations in these folders.
SAFE_DIRECTORIES = [
    Path.home() / "Desktop",
    Path.home() / "Documents",
    Path.home() / "Downloads",
]

# Windows messages
WM_CLOSE = 0x0010


# ============================================================
# APPLICATION DISCOVERY
# ============================================================

def get_shortcuts():
    """Discover applications from Windows Start Menu shortcuts."""

    locations = [
        Path(os.environ.get("APPDATA", ""))
        / "Microsoft/Windows/Start Menu/Programs",

        Path(os.environ.get("PROGRAMDATA", ""))
        / "Microsoft/Windows/Start Menu/Programs",
    ]

    shortcuts = []

    for location in locations:
        if not location.exists():
            continue

        for shortcut in location.rglob("*.lnk"):
            name = shortcut.stem

            # Ignore some unnecessary shortcut entries.
            if name.lower().endswith("- shortcut"):
                name = name[:-9].strip()

            shortcuts.append({
                "name": name,
                "path": str(shortcut)
            })

    # Remove duplicate shortcut names.
    unique = {}

    for app in shortcuts:
        key = app["name"].lower()
        if key not in unique:
            unique[key] = app

    return sorted(
        unique.values(),
        key=lambda app: app["name"].lower()
    )


def list_apps(query=""):
    """List discovered applications without exposing file paths."""

    apps = get_shortcuts()

    if query:
        q = query.lower().strip()

        matches = [
            app for app in apps
            if q in app["name"].lower()
        ]

        if not matches:
            names = [app["name"] for app in apps]
            suggestions = get_close_matches(
                query, names, n=5, cutoff=0.35
            )

            if suggestions:
                return (
                    "No exact application match found.\n"
                    "Possible matches:\n"
                    + "\n".join(f"- {name}" for name in suggestions)
                )

            return f"No applications found matching '{query}'."

        apps = matches

    names = sorted(
        {app["name"] for app in apps},
        key=str.lower
    )

    if not names:
        return "No applications were found."

    output = [
        f"Applications found: {len(names)}",
        ""
    ]

    for index, name in enumerate(names, start=1):
        output.append(f"{index:>3}. {name}")

    return "\n".join(output)


# ============================================================
# OPEN APPLICATION
# ============================================================

def open_app(name):
    """Find and launch an application using its Start Menu shortcut."""

    if not name or not name.strip():
        return "Please provide an application name."

    query = name.lower().strip()

    # Windows Calculator may not have a normal Start Menu shortcut.
    if query in ("calculator", "calc", "windows calculator"):
        try:
            subprocess.Popen(["calc.exe"])
            return "Successfully launched Windows Calculator."
        except Exception as error:
            return f"Could not launch Windows Calculator: {error}"

    apps = get_shortcuts()

    # Exact match first.
    match = next(
        (app for app in apps
         if app["name"].lower() == query),
        None
    )

    # Partial match second.
    if not match:
        matches = [
            app for app in apps
            if query in app["name"].lower()
        ]

        if len(matches) == 1:
            match = matches[0]

        elif len(matches) > 1:
            choices = "\n".join(
                f"- {app['name']}" for app in matches[:10]
            )
            return (
                "I found multiple matching applications:\n"
                f"{choices}\n"
                "Please specify which one to open."
            )

    # Fuzzy matching last.
    if not match:
        names = [app["name"] for app in apps]
        suggestions = get_close_matches(
            name, names, n=3, cutoff=0.45
        )

        if suggestions:
            return (
                f"I couldn't find '{name}'. "
                f"Did you mean: {', '.join(suggestions)}?"
            )

        return f"Application '{name}' was not found."

    try:
        os.startfile(match["path"])
        return f"Successfully launched {match['name']}."

    except Exception as error:
        return f"Could not launch {match['name']}: {error}"


# ============================================================
# RUNNING APPLICATIONS
# ============================================================

def get_visible_windows():
    """Get visible Windows application windows and their process IDs."""

    windows = []

    user32 = ctypes.windll.user32
    EnumWindows = user32.EnumWindows
    IsWindowVisible = user32.IsWindowVisible
    GetWindowTextLengthW = user32.GetWindowTextLengthW
    GetWindowTextW = user32.GetWindowTextW
    GetWindowThreadProcessId = user32.GetWindowThreadProcessId

    CALLBACK = ctypes.WINFUNCTYPE(
        ctypes.c_bool,
        ctypes.c_void_p,
        ctypes.c_void_p
    )

    def callback(hwnd, _):
        if not IsWindowVisible(hwnd):
            return True

        length = GetWindowTextLengthW(hwnd)

        if length == 0:
            return True

        title_buffer = ctypes.create_unicode_buffer(length + 1)
        GetWindowTextW(hwnd, title_buffer, length + 1)

        title = title_buffer.value.strip()

        if not title:
            return True

        pid = ctypes.c_ulong()
        GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        windows.append({
            "hwnd": hwnd,
            "pid": pid.value,
            "title": title
        })

        return True

    EnumWindows(CALLBACK(callback), 0)

    return windows


def list_running_apps():
    """List visible application windows."""

    windows = get_visible_windows()

    if not windows:
        return "No visible application windows were detected."

    output = [
        f"Visible application windows: {len(windows)}",
        ""
    ]

    seen = set()
    index = 1

    for window in windows:
        try:
            process = psutil.Process(window["pid"])
            process_name = process.name()

            key = (window["pid"], window["title"])

            if key in seen:
                continue

            seen.add(key)

            output.append(
                f"{index}. {window['title']} "
                f"({process_name})"
            )

            index += 1

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return "\n".join(output)


# ============================================================
# CLOSE APPLICATION
# ============================================================

def close_app(name):
    """Request a graceful close of matching visible app windows."""

    if not name or not name.strip():
        return "Please provide an application name."

    query = name.lower().strip()
    windows = get_visible_windows()

    matched = []

    for window in windows:
        try:
            process = psutil.Process(window["pid"])
            process_name = process.name().lower()

            title_match = query in window["title"].lower()
            process_match = query in process_name

            if title_match or process_match:
                matched.append(window)

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if not matched:
        return f"No visible running window matching '{name}' was found."

    closed = 0

    for window in matched:
        try:
            ctypes.windll.user32.PostMessageW(
                window["hwnd"],
                WM_CLOSE,
                0,
                0
            )
            closed += 1

        except Exception:
            pass

    if closed:
        return (
            f"Sent a graceful close request to "
            f"{closed} window(s) matching '{name}'."
        )

    return f"Could not send a close request to '{name}'."


# ============================================================
# SAFE FILE MANAGEMENT
# ============================================================

def open_app_for(name, seconds=5):
    """Open an application, wait, then request a graceful close."""

    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return "Invalid duration. Use a whole number of seconds."

    if seconds < 1 or seconds > 60:
        return "Duration must be between 1 and 60 seconds."

    launched = open_app(name)

    if not launched.startswith("Successfully launched"):
        return launched

    time.sleep(seconds)

    query = str(name).lower().strip()
    close_name = (
        "calculator"
        if query in ("calculator", "calc", "windows calculator")
        else name
    )

    closed = close_app(close_name)

    return (
        f"{launched} Waited {seconds} seconds. "
        f"{closed}"
    )


def get_safe_path(path):
    """Resolve friendly Windows folder names inside approved directories."""

    try:
        raw = os.path.expandvars(str(path).strip().strip('"'))
        if not raw:
            return None

        requested = Path(raw).expanduser()

        if not requested.is_absolute():
            parts = requested.parts
            if not parts:
                return None

            aliases = {
                "desktop": Path.home() / "Desktop",
                "documents": Path.home() / "Documents",
                "downloads": Path.home() / "Downloads",
            }

            root = aliases.get(parts[0].lower())
            if root is None:
                return None

            requested = root.joinpath(*parts[1:])

        target = requested.resolve()

        for directory in SAFE_DIRECTORIES:
            allowed = directory.resolve()

            if target == allowed or allowed in target.parents:
                return target

        return None

    except Exception:
        return None


def list_files(path):
    """List files and folders inside an approved directory."""

    target = get_safe_path(path)

    if target is None:
        return "Access denied. Use Desktop, Documents, or Downloads."

    if not target.exists():
        return f"Folder not found: {target.name}"

    if not target.is_dir():
        return "The provided path is not a folder."

    try:
        items = sorted(
            target.iterdir(),
            key=lambda item: (not item.is_dir(), item.name.lower())
        )

        if not items:
            return "This folder is empty."

        output = [f"Contents of {target.name}:", ""]

        for item in items[:100]:
            kind = "[Folder]" if item.is_dir() else "[File]"
            output.append(f"{kind} {item.name}")

        if len(items) > 100:
            output.append(
                f"\nShowing 100 of {len(items)} items."
            )

        return "\n".join(output)

    except Exception as error:
        return f"Could not list folder: {error}"


def create_folder(path):
    """Create a folder inside an approved directory."""

    target = get_safe_path(path)

    if target is None:
        return "Access denied. Use Desktop, Documents, or Downloads."

    try:
        target.mkdir(parents=True, exist_ok=False)
        return f"Folder created successfully: {target.name}"

    except FileExistsError:
        return f"A folder or file already exists at {target.name}."

    except Exception as error:
        return f"Could not create folder: {error}"


def create_file(path, content=""):
    """Create a new text file inside an approved directory."""

    target = get_safe_path(path)

    if target is None:
        return "Access denied. Use Desktop, Documents, or Downloads."

    if target.exists():
        return f"File already exists: {target.name}. Nothing was overwritten."

    try:
        target.parent.mkdir(parents=True, exist_ok=True)

        with open(target, "x", encoding="utf-8") as file:
            file.write(content)

        return f"File created successfully: {target.name}"

    except Exception as error:
        return f"Could not create file: {error}"


def read_file(path):
    """Read a text file inside an approved directory."""

    target = get_safe_path(path)

    if target is None:
        return "Access denied. Use Desktop, Documents, or Downloads."

    if not target.exists() or not target.is_file():
        return "File not found."

    try:
        if target.stat().st_size > 500_000:
            return "File is too large to read (maximum 500 KB)."

        with open(target, "r", encoding="utf-8") as file:
            content = file.read()

        return content if content else "The file is empty."

    except UnicodeDecodeError:
        return "This file is not a readable UTF-8 text file."

    except Exception as error:
        return f"Could not read file: {error}"



# ============================================================
# SYSTEM MONITOR ? READ-ONLY WINDOWS INTELLIGENCE
# ============================================================

def _format_bytes(value):
    """Convert bytes into a readable storage unit."""
    value = float(value)

    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.2f} {unit}"
        value /= 1024

    return f"{value:.2f} TB"


def get_system_report():
    """Report live CPU, memory, Windows, uptime and battery status."""

    cpu_usage = psutil.cpu_percent(interval=0.5)
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()

    uptime_seconds = max(0, int(datetime.now().timestamp() - psutil.boot_time()))
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    try:
        cpu_frequency = psutil.cpu_freq()
        frequency_text = (
            f"{cpu_frequency.current:.0f} MHz"
            if cpu_frequency else "Unavailable"
        )
    except Exception:
        frequency_text = "Unavailable"

    try:
        battery = psutil.sensors_battery()
        if battery is None:
            battery_text = "No battery detected"
        else:
            battery_text = f"{battery.percent:.0f}%"
            if battery.power_plugged:
                battery_text += " (plugged in)"
            else:
                battery_text += " (on battery)"

            if battery.secsleft >= 0 and not battery.power_plugged:
                battery_text += (
                    f", approximately {battery.secsleft // 60} minutes remaining"
                )
    except Exception:
        battery_text = "Battery information unavailable"

    lines = [
        "========== DIABLO SYSTEM MONITOR ==========",
        f"Computer       : {platform.node()}",
        f"Operating System: {platform.system()} {platform.release()}",
        f"Windows Build  : {platform.version()}",
        f"Architecture   : {platform.machine()}",
        "",
        "--- PROCESSOR ---",
        f"CPU Usage      : {cpu_usage:.1f}%",
        f"Logical Cores  : {psutil.cpu_count(logical=True)}",
        f"Physical Cores : {psutil.cpu_count(logical=False) or 'Unavailable'}",
        f"CPU Frequency  : {frequency_text}",
        "",
        "--- MEMORY ---",
        f"RAM Total      : {_format_bytes(memory.total)}",
        f"RAM Used       : {_format_bytes(memory.used)}",
        f"RAM Available  : {_format_bytes(memory.available)}",
        f"RAM Usage      : {memory.percent:.1f}%",
        f"Swap Usage     : {swap.percent:.1f}%",
        "",
        "--- SYSTEM ---",
        f"Uptime         : {days} days, {hours} hours, {minutes} minutes",
        f"Battery        : {battery_text}",
        f"Report Time    : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "============================================"
    ]

    return "\n".join(lines)


def get_process_report(limit=12):
    """Show the highest-memory processes without changing them."""

    try:
        limit = max(1, min(int(limit), 30))
    except (TypeError, ValueError):
        limit = 12

    processes = []

    for process in psutil.process_iter(
        ["pid", "name", "memory_info", "status"]
    ):
        try:
            info = process.info
            memory_info = info.get("memory_info")
            memory_bytes = memory_info.rss if memory_info else 0

            processes.append({
                "pid": info.get("pid"),
                "name": info.get("name") or "Unknown",
                "memory": memory_bytes,
                "status": info.get("status") or "Unknown"
            })

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    processes.sort(key=lambda item: item["memory"], reverse=True)

    lines = [
        "========== TOP WINDOWS PROCESSES ==========",
        f"{'PID':<9} {'RAM':>11}  {'STATUS':<13} PROCESS",
        "-" * 65
    ]

    for item in processes[:limit]:
        lines.append(
            f"{str(item['pid']):<9} "
            f"{_format_bytes(item['memory']):>11}  "
            f"{item['status']:<13} "
            f"{item['name'][:30]}"
        )

    lines.extend([
        "-" * 65,
        f"Showing {min(limit, len(processes))} of {len(processes)} accessible processes.",
        "Processes were inspected only. Nothing was terminated."
    ])

    return "\n".join(lines)


def get_storage_report():
    """Report total, used and free storage on accessible drives."""

    lines = [
        "========== WINDOWS STORAGE MONITOR ==========",
    ]

    seen = set()
    found = 0

    for partition in psutil.disk_partitions(all=False):
        mount = partition.mountpoint

        if mount in seen:
            continue

        seen.add(mount)

        try:
            usage = psutil.disk_usage(mount)
            found += 1

            lines.extend([
                "",
                f"Drive          : {mount}",
                f"File System    : {partition.fstype or 'Unknown'}",
                f"Total          : {_format_bytes(usage.total)}",
                f"Used           : {_format_bytes(usage.used)}",
                f"Free           : {_format_bytes(usage.free)}",
                f"Usage          : {usage.percent:.1f}%"
            ])

        except (PermissionError, OSError):
            lines.extend([
                "",
                f"Drive          : {mount}",
                "Status         : Not accessible"
            ])

    if not found:
        lines.append("No accessible storage drives were detected.")

    lines.extend(["", "=============================================="])
    return "\n".join(lines)


def get_network_report():
    """Report network adapter state and total transferred data."""

    lines = ["========== WINDOWS NETWORK MONITOR =========="]

    try:
        interfaces = psutil.net_if_stats()
        counters = psutil.net_io_counters(pernic=True) or {}

        for name, stats in interfaces.items():
            received = counters.get(name)

            lines.extend([
                "",
                f"Adapter        : {name}",
                f"Status         : {'UP' if stats.isup else 'DOWN'}",
                f"Speed          : {stats.speed} Mbps" if stats.speed else "Speed          : Unknown"
            ])

            if received:
                lines.append(
                    f"Data Received  : {_format_bytes(received.bytes_recv)}"
                )
                lines.append(
                    f"Data Sent      : {_format_bytes(received.bytes_sent)}"
                )

        totals = psutil.net_io_counters()
        if totals:
            lines.extend([
                "",
                "--- TOTAL TRAFFIC SINCE BOOT ---",
                f"Received       : {_format_bytes(totals.bytes_recv)}",
                f"Sent           : {_format_bytes(totals.bytes_sent)}"
            ])

    except Exception as error:
        lines.append(f"Network inspection failed: {error}")

    lines.append("==============================================")
    return "\n".join(lines)



from modules.file_intelligence import (
    get_file_audit_report,
    get_file_types_report,
    get_large_files_report,
    get_old_files_report,
)

# ============================================================
# MODULE STATUS
# ============================================================

def get_status():
    return (
        "Windows AI Operator tools are ready.\n"
        "- Application discovery\n"
        "- Application launching\n"
        "- Running application detection\n"
        "- Graceful application closing\n"
        "- Safe file listing\n"
        "- Safe folder creation\n"
        "- Safe file creation\n"
        "- Safe text file reading"
    )

# ============================================================
# TOOL DISPATCHER — CONNECTS agent.py TO THE TOOL FUNCTIONS
# ============================================================

def run_tool(tool_name, arguments=None):
    """Execute an approved tool by name."""

    arguments = arguments or {}

    tool_functions = {
        "list_apps": list_apps,
        "open_app": open_app,
        "open_app_for": open_app_for,
        "list_running_apps": list_running_apps,
        "close_app": close_app,
        "list_files": list_files,
        "create_folder": create_folder,
        "create_file": create_file,
        "read_file": read_file,
        "get_status": get_status,
        "get_system_report": get_system_report,
        "get_process_report": get_process_report,
        "get_storage_report": get_storage_report,
        "get_network_report": get_network_report,
        "get_file_audit_report": get_file_audit_report,
        "get_file_types_report": get_file_types_report,
        "get_large_files_report": get_large_files_report,
        "get_old_files_report": get_old_files_report,
        "read_document": read_document,
        "search_document_content": search_document_content,
    }

    function = tool_functions.get(tool_name)

    if function is None:
        return f"Unknown tool: {tool_name}"

    try:
        return function(**arguments)
    except TypeError as error:
        return f"Invalid arguments for {tool_name}: {error}"
    except Exception as error:
        return f"Tool execution failed: {error}"


# ============================================================
# EXTENDED FILE MANAGER TOOLS
# ============================================================

from modules.file_manager import (
    search_files,
    find_duplicates,
    move_file,
    copy_file,
    rename_file
)
from modules.duplicate_organizer import organize_duplicates

_previous_run_tool = run_tool

def run_tool(tool_name, arguments=None):
    arguments = arguments or {}

    extra_tools = {
        "search_files": search_files,
        "find_duplicates": find_duplicates,
        "organize_duplicates": organize_duplicates,
        "move_file": move_file,
        "copy_file": copy_file,
        "rename_file": rename_file,
    }

    function = extra_tools.get(tool_name)

    if function:
        try:
            return function(**arguments)
        except Exception as error:
            return f"Tool execution failed: {error}"

    return _previous_run_tool(tool_name, arguments)



# Stage 2.2 document intelligence tools
from modules.document_intelligence import (
    read_document,
    search_document_content,
)
