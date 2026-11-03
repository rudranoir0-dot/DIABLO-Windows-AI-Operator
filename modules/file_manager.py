import os
import hashlib
import shutil
from pathlib import Path

ROOTS = {
    "desktop": Path.home() / "Desktop",
    "documents": Path.home() / "Documents",
    "downloads": Path.home() / "Downloads",
}

def safe_path(value):
    path = Path(value).expanduser().resolve()

    for root in ROOTS.values():
        root = root.resolve()
        if path == root or root in path.parents:
            return path

    return None


def search_files(query="", location="all", extension="", max_results=100):
    """Search files recursively in approved user folders."""

    locations = (
        list(ROOTS.values())
        if location.lower() == "all"
        else [ROOTS[location.lower()]]
        if location.lower() in ROOTS
        else []
    )

    if not locations:
        return "Invalid location. Use all, desktop, documents or downloads."

    query = query.lower().strip()
    extension = extension.lower().strip()

    if extension and not extension.startswith("."):
        extension = "." + extension

    results = []

    for root in locations:
        if not root.exists():
            continue

        try:
            for current, dirs, files in os.walk(root):
                dirs[:] = [
                    d for d in dirs
                    if d.lower() not in {
                        "venv", ".git", "__pycache__", "node_modules"
                    }
                ]

                for filename in files:
                    path = Path(current) / filename

                    if query and query not in filename.lower():
                        continue

                    if extension and path.suffix.lower() != extension:
                        continue

                    results.append(path)

                    if len(results) >= max_results:
                        break

                if len(results) >= max_results:
                    break

        except PermissionError:
            continue

        if len(results) >= max_results:
            break

    if not results:
        return "No matching files found."

    lines = [f"Found {len(results)} file(s):", ""]

    for i, path in enumerate(results, 1):
        try:
            size = path.stat().st_size
            lines.append(
                f"{i}. {path.name} | {size:,} bytes\n   {path}"
            )
        except OSError:
            lines.append(f"{i}. {path.name}\n   {path}")

    return "\n".join(lines)



def find_duplicates(location="all"):
    """Find identical files with live progress and size pre-filtering."""

    import time

    locations = (
        list(ROOTS.values())
        if location.lower() == "all"
        else [ROOTS[location.lower()]]
        if location.lower() in ROOTS
        else []
    )

    if not locations:
        return "Invalid location. Use all, desktop, documents or downloads."

    print("\nDuplicate scanner started.")
    print("Phase 1/2: Discovering files...")

    size_groups = {}
    scanned = 0
    errors = 0
    start_time = time.time()

    for root in locations:
        if not root.exists():
            continue

        for current, dirs, files in os.walk(root):
            dirs[:] = [
                d for d in dirs
                if d.lower() not in {
                    "venv", ".git", "__pycache__", "node_modules", "duplicates", "duplicate review"
                }
            ]

            for filename in files:
                path = Path(current) / filename

                try:
                    size = path.stat().st_size
                    scanned += 1

                    if size > 0:
                        size_groups.setdefault(size, []).append(path)

                    if scanned % 100 == 0:
                        print(
                            f"\rDiscovered {scanned:,} files...",
                            end="", flush=True
                        )

                except OSError:
                    errors += 1

    print(f"\rDiscovery complete: {scanned:,} files found.          ")

    candidates = [
        (size, paths)
        for size, paths in size_groups.items()
        if len(paths) > 1
    ]

    total_candidates = sum(len(paths) for _, paths in candidates)

    if not candidates:
        return (
            f"No possible duplicates found among {scanned:,} files.\n"
            f"Elapsed time: {time.time() - start_time:.1f} seconds."
        )

    print(
        f"Phase 2/2: Checking {total_candidates:,} candidate files "
        f"across {len(candidates):,} matching-size groups..."
    )

    hashes = {}
    processed = 0
    total_bytes = 0

    for size, paths in candidates:
        for file_path in paths:
            processed += 1

            try:
                digest = hashlib.sha256()

                with open(file_path, "rb") as f:
                    for chunk in iter(
                        lambda: f.read(1024 * 1024), b""
                    ):
                        digest.update(chunk)

                key = (size, digest.hexdigest())
                hashes.setdefault(key, []).append(file_path)
                total_bytes += size

            except OSError:
                errors += 1

            percent = processed * 100 / total_candidates

            print(
                f"\rHashing: {processed:,}/{total_candidates:,} "
                f"({percent:.1f}%) | "
                f"Duplicate groups: "
                f"{sum(1 for v in hashes.values() if len(v) > 1)}",
                end="", flush=True
            )

    print("\n")

    duplicates = [
        (size, paths)
        for (size, digest), paths in hashes.items()
        if len(paths) > 1
    ]

    if not duplicates:
        return (
            f"No identical files found among {scanned:,} scanned files.\n"
            f"Elapsed time: {time.time() - start_time:.1f} seconds."
        )

    duplicate_bytes = sum(
        size * (len(paths) - 1)
        for size, paths in duplicates
    )

    lines = [
        f"Duplicate scan complete.",
        f"Files discovered: {scanned:,}",
        f"Duplicate groups: {len(duplicates):,}",
        f"Extra storage occupied: {duplicate_bytes:,} bytes "
        f"({duplicate_bytes / (1024 ** 2):.2f} MB)",
        f"Elapsed time: {time.time() - start_time:.1f} seconds.",
        ""
    ]

    for index, (size, paths) in enumerate(duplicates, 1):
        lines.append(
            f"Group {index} | {len(paths)} identical files | "
            f"{size:,} bytes each"
        )

        for file_path in paths:
            lines.append(f"  {file_path}")

        lines.append("")

    if errors:
        lines.append(f"Files skipped due to access errors: {errors}")

    return "\n".join(lines)


def move_file(source, destination):
    """Move a file or folder within approved directories."""

    src = safe_path(source)
    dst = safe_path(destination)

    if src is None or dst is None:
        return "Access denied. Only Desktop, Documents and Downloads are allowed."

    if not src.exists():
        return "Source does not exist."

    if dst.exists() and dst.is_dir():
        dst = dst / src.name

    if dst.exists():
        return "Destination already exists. Nothing was overwritten."

    if dst == src or src in dst.parents:
        return "Cannot move a folder into itself."

    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))

        if dst.exists():
            return f"Move verified successfully: {src.name} -> {dst}"

        return "Move could not be verified."

    except Exception as error:
        return f"Move failed: {error}"


def copy_file(source, destination):
    """Copy a file or folder within approved directories."""

    src = safe_path(source)
    dst = safe_path(destination)

    if src is None or dst is None:
        return "Access denied."

    if not src.exists():
        return "Source does not exist."

    if dst.exists() and dst.is_dir():
        dst = dst / src.name

    if dst.exists():
        return "Destination already exists. Nothing was overwritten."

    if src.is_dir() and (dst == src or src in dst.parents):
        return "Cannot copy a folder into itself."

    try:
        dst.parent.mkdir(parents=True, exist_ok=True)

        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

        if dst.exists():
            return f"Copy verified successfully: {dst}"

        return "Copy could not be verified."

    except Exception as error:
        return f"Copy failed: {error}"


def rename_file(source, new_name):
    """Rename a file or folder without overwriting."""

    src = safe_path(source)

    if src is None:
        return "Access denied."

    if not src.exists():
        return "Source does not exist."

    if not new_name or new_name in (".", ".."):
        return "Invalid new name."

    if Path(new_name).name != new_name or "/" in new_name or "\\" in new_name:
        return "Provide only a new filename, not a path."

    dst = src.with_name(new_name)

    if dst.exists():
        return "A file or folder with that name already exists."

    try:
        src.rename(dst)

        if dst.exists():
            return f"Rename verified: {src.name} -> {dst.name}"

        return "Rename could not be verified."

    except Exception as error:
        return f"Rename failed: {error}"
