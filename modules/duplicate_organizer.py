from pathlib import Path
import hashlib
import os
import time

from modules.file_manager import ROOTS, move_file


SKIP_DIRS = {
    "venv", ".git", "__pycache__", "node_modules",
    "duplicates", "duplicate review"
}


def unique_destination(folder, source):
    candidate = folder / source.name
    counter = 2

    while candidate.exists():
        candidate = folder / f"{source.stem} ({counter}){source.suffix}"
        counter += 1

    return candidate


def organize_duplicates(location="all"):
    location = (location or "all").strip().lower()

    if location == "all":
        root_names = ("desktop", "documents", "downloads")
    elif location in ROOTS:
        root_names = (location,)
    else:
        return "Invalid location. Choose all, desktop, documents or downloads."

    roots = [Path(ROOTS[name]).resolve() for name in root_names]
    desktop = Path(ROOTS["desktop"]).resolve()
    destination = desktop / "Duplicate Review"

    if not desktop.is_dir():
        return "Desktop folder is unavailable."

    if destination.exists() and not destination.is_dir():
        return "Cannot create Duplicate Review: a file with that name already exists."

    print("\nDuplicate separation started.")
    print("Phase 1/3: Discovering files...")

    size_groups = {}
    scanned = 0
    errors = 0
    skipped_temp = 0
    start = time.time()

    for root in roots:
        if not root.is_dir():
            continue

        for current, dirs, filenames in os.walk(root):
            current_path = Path(current).resolve()

            dirs[:] = [
                d for d in dirs
                if d.lower() not in SKIP_DIRS
                and (current_path / d).resolve() != destination.resolve()
            ]

            for filename in filenames:
                # Do not move temporary Microsoft Office lock files.
                if filename.startswith("~$"):
                    skipped_temp += 1
                    continue

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

    print(f"\rDiscovery complete: {scanned:,} files found.")

    candidates = [
        (size, paths)
        for size, paths in size_groups.items()
        if len(paths) > 1
    ]

    total_candidates = sum(len(paths) for _, paths in candidates)

    if not candidates:
        return (
            f"No duplicates found among {scanned:,} files. "
            "Nothing was moved."
        )

    print(
        f"Phase 2/3: Checking {total_candidates:,} candidate files..."
    )

    hashes = {}
    processed = 0

    for size, paths in candidates:
        for path in paths:
            processed += 1

            try:
                digest = hashlib.sha256()

                with open(path, "rb") as file:
                    for chunk in iter(
                        lambda: file.read(1024 * 1024), b""
                    ):
                        digest.update(chunk)

                key = (size, digest.hexdigest())
                hashes.setdefault(key, []).append(path)

            except OSError:
                errors += 1

            percent = processed * 100 / total_candidates
            print(
                f"\rHashing: {processed:,}/{total_candidates:,} "
                f"({percent:.1f}%)",
                end="", flush=True
            )

    duplicates = [
        (size, paths)
        for (size, digest), paths in hashes.items()
        if len(paths) > 1
    ]

    if not duplicates:
        return "No identical files found. Nothing was moved."

    # Prefer to keep the copy in the first selected root.
    root_priority = {
        root: index for index, root in enumerate(roots)
    }

    def keep_priority(path):
        resolved = path.resolve()

        for root, index in root_priority.items():
            try:
                resolved.relative_to(root)
                return (index, str(resolved).lower())
            except ValueError:
                continue

        return (999, str(resolved).lower())

    move_plan = []

    for size, paths in duplicates:
        ordered = sorted(paths, key=keep_priority)
        original = ordered[0]

        for redundant_copy in ordered[1:]:
            move_plan.append((redundant_copy, size, original))

    if not move_plan:
        return "No redundant copies need moving."

    print("\nPhase 3/3: Moving redundant copies...")

    try:
        destination.mkdir(exist_ok=True)
    except OSError as error:
        return f"Could not create review folder: {error}"

    moved = 0
    failed = []
    moved_bytes = 0

    for index, (source, size, original) in enumerate(move_plan, 1):
        target = unique_destination(destination, source)

        try:
            result = move_file(str(source), str(target))

            if not source.exists() and target.is_file():
                moved += 1
                moved_bytes += size
            else:
                failed.append(
                    f"{source.name}: {str(result)[:180]}"
                )

        except Exception as error:
            failed.append(f"{source.name}: {str(error)[:180]}")

        print(
            f"\rMoving: {index}/{len(move_plan)} "
            f"| Successful: {moved} | Failed: {len(failed)}",
            end="", flush=True
        )

    print()

    lines = [
        "Duplicate separation finished.",
        f"Files scanned: {scanned:,}",
        f"Duplicate groups: {len(duplicates):,}",
        f"Redundant copies identified: {len(move_plan):,}",
        f"Successfully moved: {moved:,}",
        f"Failed moves: {len(failed):,}",
        f"Storage relocated: {moved_bytes / (1024 ** 2):.2f} MB",
        f"Review folder: {destination}",
        "One original copy was retained from each duplicate group.",
        "No files were deleted or overwritten."
    ]

    if skipped_temp:
        lines.append(
            f"Temporary Office lock files skipped: {skipped_temp}"
        )

    if errors:
        lines.append(f"Files skipped due to access errors: {errors}")

    if failed:
        lines.append("Failed move details:")
        lines.extend(f" - {item}" for item in failed[:5])

    lines.append(
        f"Elapsed time: {time.time() - start:.1f} seconds."
    )

    return "\n".join(lines)
