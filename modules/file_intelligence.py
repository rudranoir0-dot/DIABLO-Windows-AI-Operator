import os
import time
import stat
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

ROOTS = {
    "desktop": Path.home() / "Desktop",
    "documents": Path.home() / "Documents",
    "downloads": Path.home() / "Downloads",
}

MAX_SCAN_FILES = 50000
LARGE_FILE_DEFAULT_MB = 100

SKIP_DIRECTORIES = {
    "venv",
    ".git",
    "__pycache__",
    "node_modules",
    "$recycle.bin",
    "system volume information",
}

CATEGORY_MAP = {
    "Documents": {
        ".doc", ".docx", ".odt", ".rtf", ".pages"
    },
    "PDF": {".pdf"},
    "Spreadsheets": {
        ".xls", ".xlsx", ".xlsm", ".csv", ".ods"
    },
    "Presentations": {
        ".ppt", ".pptx", ".odp"
    },
    "Images": {
        ".jpg", ".jpeg", ".png", ".gif", ".bmp",
        ".webp", ".tiff", ".tif", ".heic", ".svg"
    },
    "Videos": {
        ".mp4", ".mkv", ".avi", ".mov", ".wmv",
        ".webm", ".mpeg", ".mpg"
    },
    "Audio": {
        ".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"
    },
    "Archives": {
        ".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"
    },
    "Executables": {
        ".exe", ".msi", ".bat", ".cmd", ".ps1", ".com"
    },
    "Code": {
        ".py", ".js", ".ts", ".html", ".css", ".java",
        ".cpp", ".c", ".h", ".cs", ".php", ".json",
        ".xml", ".yaml", ".yml", ".sql", ".sh"
    },
    "Text": {
        ".txt", ".md", ".log", ".ini", ".cfg"
    }
}


def _format_bytes(value):
    value = float(value)

    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.2f} {unit}"
        value /= 1024

    return f"{value:.2f} TB"


def _category(extension):
    extension = extension.lower()

    for category, extensions in CATEGORY_MAP.items():
        if extension in extensions:
            return category

    return "Other"


def _is_reparse_or_symlink(path):
    """Avoid following symbolic links and Windows junctions."""

    try:
        info = path.lstat()

        if path.is_symlink():
            return True

        attributes = getattr(info, "st_file_attributes", 0)
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)

        return bool(attributes & reparse_flag)

    except OSError:
        return True


def _scan(location="all", max_files=MAX_SCAN_FILES):
    """
    Scan approved folders using metadata only.
    Never opens document contents or follows links/reparse points.
    """

    location = str(location).lower().strip()

    if location == "all":
        roots = list(ROOTS.items())
    elif location in ROOTS:
        roots = [(location, ROOTS[location])]
    else:
        return [], 0, False, (
            "Invalid location. Use all, desktop, documents or downloads."
        )

    try:
        max_files = max(1, min(int(max_files), MAX_SCAN_FILES))
    except (TypeError, ValueError):
        max_files = MAX_SCAN_FILES

    records = []
    errors = 0
    truncated = False

    def record_error(_error):
        nonlocal errors
        errors += 1

    for root_name, root in roots:
        if not root.exists():
            errors += 1
            continue

        if _is_reparse_or_symlink(root):
            errors += 1
            continue

        for current, directories, filenames in os.walk(
            root,
            topdown=True,
            followlinks=False,
            onerror=record_error
        ):
            current_path = Path(current)

            # Skip generated folders and Windows reparse directories.
            safe_directories = []

            for directory in directories:
                candidate = current_path / directory

                if directory.lower() in SKIP_DIRECTORIES:
                    continue

                if _is_reparse_or_symlink(candidate):
                    continue

                safe_directories.append(directory)

            directories[:] = safe_directories

            for filename in filenames:
                if filename.startswith("~$"):
                    continue

                path = current_path / filename

                if _is_reparse_or_symlink(path):
                    continue

                try:
                    info = path.lstat()

                    if not stat.S_ISREG(info.st_mode):
                        continue

                    suffix = path.suffix.lower()

                    records.append({
                        "name": path.name,
                        "path": str(path),
                        "extension": suffix if suffix else "[no extension]",
                        "category": _category(suffix),
                        "size": info.st_size,
                        "modified": info.st_mtime,
                        "modified_date": datetime.fromtimestamp(
                            info.st_mtime
                        ).strftime("%Y-%m-%d %H:%M"),
                        "root": root_name,
                    })

                except (OSError, PermissionError):
                    errors += 1
                    continue

                if len(records) >= max_files:
                    truncated = True
                    break

            if truncated:
                break

        if truncated:
            break

    return records, errors, truncated, None


def get_file_audit_report(location="all"):
    """Read-only overview of file categories, sizes and dates."""

    records, errors, truncated, problem = _scan(location)

    if problem:
        return problem

    if not records:
        return "No accessible files were found in the selected location."

    total_size = sum(item["size"] for item in records)
    categories = Counter(item["category"] for item in records)
    extensions = Counter(item["extension"] for item in records)

    large_threshold = LARGE_FILE_DEFAULT_MB * 1024 * 1024
    large_files = [
        item for item in records if item["size"] >= large_threshold
    ]
    large_files.sort(key=lambda item: item["size"], reverse=True)

    old_cutoff = time.time() - (365 * 86400)
    old_files = [
        item for item in records if item["modified"] < old_cutoff
    ]
    old_files.sort(key=lambda item: item["modified"])

    lines = [
        "========== DIABLO SMART FILE AUDIT ==========",
        f"Location       : {location.title()}",
        f"Files scanned  : {len(records):,}",
        f"Total size     : {_format_bytes(total_size)}",
        f"Access errors  : {errors}",
        f"Scan limit hit : {'YES - results are incomplete' if truncated else 'NO'}",
        "",
        "--- FILE CATEGORIES ---",
    ]

    for category, count in categories.most_common():
        lines.append(f"{category:<18} {count:>8,} files")

    lines.extend([
        "",
        "--- MOST COMMON EXTENSIONS ---",
    ])

    for extension, count in extensions.most_common(15):
        lines.append(f"{extension:<18} {count:>8,} files")

    lines.extend([
        "",
        f"Files at least {LARGE_FILE_DEFAULT_MB} MB: {len(large_files):,}",
        f"Files not modified in 365+ days: {len(old_files):,}",
        "",
        "--- 8 LARGEST FILES ---",
    ])

    for item in large_files[:8]:
        lines.append(
            f"{_format_bytes(item['size']):>12} | {item['name']}"
        )
        lines.append(f"             {item['path']}")

    lines.extend([
        "",
        "--- 8 OLDEST FILES ---",
    ])

    for item in old_files[:8]:
        lines.append(
            f"{item['modified_date']} | {item['name']}"
        )
        lines.append(f"             {item['path']}")

    lines.extend([
        "",
        "READ-ONLY AUDIT: No files were changed.",
        "==============================================",
    ])

    return "\n".join(lines)


def get_file_types_report(location="all"):
    """Count files by extension and category."""

    records, errors, truncated, problem = _scan(location)

    if problem:
        return problem

    extensions = Counter(item["extension"] for item in records)
    categories = Counter(item["category"] for item in records)

    lines = [
        "========== FILE TYPE REPORT ==========",
        f"Location: {location.title()}",
        f"Files scanned: {len(records):,}",
        "",
        "--- CATEGORIES ---",
    ]

    for name, count in categories.most_common():
        lines.append(f"{name:<18} {count:>8,}")

    lines.extend(["", "--- EXTENSIONS ---"])

    for name, count in extensions.most_common(40):
        lines.append(f"{name:<18} {count:>8,}")

    lines.extend([
        "",
        f"Access errors: {errors}",
        f"Scan truncated: {'YES' if truncated else 'NO'}",
        "No file contents were opened.",
        "======================================",
    ])

    return "\n".join(lines)


def get_large_files_report(location="all", min_mb=100, limit=20):
    """Find the largest files without opening their contents."""

    try:
        min_mb = max(0, min(float(min_mb), 102400))
        limit = max(1, min(int(limit), 100))
    except (TypeError, ValueError):
        return "Invalid size threshold or result limit."

    records, errors, truncated, problem = _scan(location)

    if problem:
        return problem

    threshold = min_mb * 1024 * 1024

    found = [
        item for item in records if item["size"] >= threshold
    ]

    found.sort(key=lambda item: item["size"], reverse=True)

    lines = [
        "========== LARGE FILE REPORT ==========",
        f"Location: {location.title()}",
        f"Minimum size: {min_mb:g} MB",
        f"Matching files: {len(found):,}",
        "",
    ]

    for index, item in enumerate(found[:limit], 1):
        lines.append(
            f"{index}. {_format_bytes(item['size'])} | {item['name']}"
        )
        lines.append(f"   {item['path']}")

    if not found:
        lines.append("No files matched the selected size threshold.")

    if len(found) > limit:
        lines.append(f"Showing {limit} of {len(found)} matching files.")

    lines.extend([
        f"Access errors: {errors}",
        f"Scan truncated: {'YES - results may be incomplete' if truncated else 'NO'}",
        "No files were changed.",
        "======================================",
    ])

    return "\n".join(lines)


def get_old_files_report(location="all", days=365, limit=20):
    """Find files whose modification date is older than a threshold."""

    try:
        days = max(1, min(int(days), 36500))
        limit = max(1, min(int(limit), 100))
    except (TypeError, ValueError):
        return "Invalid age threshold or result limit."

    records, errors, truncated, problem = _scan(location)

    if problem:
        return problem

    cutoff = time.time() - (days * 86400)

    found = [
        item for item in records if item["modified"] < cutoff
    ]

    found.sort(key=lambda item: item["modified"])

    lines = [
        "========== OLD FILE REPORT ==========",
        f"Location: {location.title()}",
        f"Not modified in: {days} days or more",
        f"Matching files: {len(found):,}",
        "",
    ]

    for index, item in enumerate(found[:limit], 1):
        lines.append(
            f"{index}. {item['modified_date']} | "
            f"{_format_bytes(item['size'])} | {item['name']}"
        )
        lines.append(f"   {item['path']}")

    if not found:
        lines.append("No files matched the selected age threshold.")

    if len(found) > limit:
        lines.append(f"Showing {limit} of {len(found)} matching files.")

    lines.extend([
        f"Access errors: {errors}",
        f"Scan truncated: {'YES - results may be incomplete' if truncated else 'NO'}",
        "Old does not necessarily mean unused or safe to remove.",
        "No files were changed.",
        "=====================================",
    ])

    return "\n".join(lines)
