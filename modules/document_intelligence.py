import os
import stat
from pathlib import Path

ROOTS = {
    "desktop": Path.home() / "Desktop",
    "documents": Path.home() / "Documents",
    "downloads": Path.home() / "Downloads",
}

SUPPORTED = {
    ".pdf", ".docx", ".xlsx", ".xlsm", ".csv",
    ".txt", ".md", ".log", ".json", ".xml",
    ".html", ".py", ".ps1", ".sql", ".yaml", ".yml"
}

MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_TEXT_CHARS = 12000
MAX_PDF_PAGES = 30
MAX_SEARCH_DOCUMENTS = 250

SKIP_DIRS = {
    "venv", ".git", "__pycache__", "node_modules",
    "$recycle.bin", "system volume information"
}


def safe_document_path(value):
    """Permit regular files only inside approved user folders."""
    try:
        raw = os.path.expandvars(str(value).strip().strip('"'))
        candidate = Path(raw).expanduser()

        if not candidate.is_absolute():
            parts = candidate.parts
            if not parts or parts[0].lower() not in ROOTS:
                return None
            candidate = ROOTS[parts[0].lower()].joinpath(*parts[1:])

        for component in (candidate, *candidate.parents):
            try:
                info = component.lstat()
            except OSError:
                return None

            attributes = getattr(info, "st_file_attributes", 0)
            flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)

            if component.is_symlink() or attributes & flag:
                return None

        target = candidate.resolve(strict=True)

        if not target.is_file():
            return None

        for root in ROOTS.values():
            allowed = root.resolve()
            if target == allowed or allowed in target.parents:
                return target

        return None

    except Exception:
        return None


def extract_text(path):
    path = Path(path)

    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return "", "File exceeds the 20 MB extraction limit."
    except OSError as error:
        return "", str(error)

    ext = path.suffix.lower()

    if ext not in SUPPORTED:
        return "", "Unsupported document format: " + ext

    truncated = False

    try:
        if ext == ".pdf":
            from pypdf import PdfReader

            reader = PdfReader(str(path), strict=False)

            if reader.is_encrypted:
                return "", "PDF is password protected."

            pieces = []

            for index, page in enumerate(reader.pages):
                if index >= MAX_PDF_PAGES:
                    truncated = True
                    break

                pieces.append(page.extract_text() or "")

                if sum(map(len, pieces)) >= MAX_TEXT_CHARS:
                    truncated = True
                    break

            content = "\n".join(pieces)

        elif ext == ".docx":
            from docx import Document

            document = Document(str(path))
            pieces = []

            for paragraph in document.paragraphs:
                if paragraph.text:
                    pieces.append(paragraph.text)

                if sum(map(len, pieces)) >= MAX_TEXT_CHARS:
                    truncated = True
                    break

            if not truncated:
                for table in document.tables[:20]:
                    for row in table.rows[:100]:
                        pieces.append(
                            " | ".join(cell.text for cell in row.cells[:20])
                        )

                        if sum(map(len, pieces)) >= MAX_TEXT_CHARS:
                            truncated = True
                            break

                    if truncated:
                        break

            content = "\n".join(pieces)

        elif ext in (".xlsx", ".xlsm"):
            from openpyxl import load_workbook

            workbook = load_workbook(
                filename=str(path),
                read_only=True,
                data_only=True
            )

            pieces = []

            try:
                for sheet in workbook.worksheets[:5]:
                    pieces.append("[SHEET: " + sheet.title + "]")

                    for row in sheet.iter_rows(
                        min_row=1,
                        max_row=min(sheet.max_row or 0, 100),
                        max_col=min(sheet.max_column or 0, 20),
                        values_only=True
                    ):
                        values = [
                            str(value)[:500]
                            for value in row if value is not None
                        ]

                        if values:
                            pieces.append(" | ".join(values))

                        if sum(map(len, pieces)) >= MAX_TEXT_CHARS:
                            truncated = True
                            break

                    if truncated:
                        break
            finally:
                workbook.close()

            content = "\n".join(pieces)

        else:
            with open(
                path, "r", encoding="utf-8-sig", errors="replace"
            ) as handle:
                content = handle.read(MAX_TEXT_CHARS + 1)

            truncated = len(content) > MAX_TEXT_CHARS

        content = content[:MAX_TEXT_CHARS]

        if not content.strip():
            return "", "No extractable text found."

        note = (
            "Extraction reached a configured limit."
            if truncated else None
        )

        return content, note

    except Exception as error:
        return "", f"{type(error).__name__}: {error}"


def read_document(path):
    target = safe_document_path(path)

    if target is None:
        return "Access denied or file not found inside approved folders."

    content, note = extract_text(target)

    if not content:
        return note or "No document text found."

    result = [
        "========== EXTRACTED DOCUMENT ==========",
        "Name: " + target.name,
        "Path: " + str(target),
        f"Characters extracted: {len(content):,}",
        "",
        content,
    ]

    if note:
        result.extend(["", note])

    result.extend([
        "",
        "Extracted locally. No file was modified.",
        "========================================"
    ])

    return "\n".join(result)


def search_document_content(
    query, location="all", extension="",
    max_documents=250, max_results=20
):
    query = str(query).strip()
    location = str(location).lower().strip()
    extension = str(extension).lower().strip()

    if len(query) < 2:
        return "Search phrase must contain at least two characters."

    if location != "all" and location not in ROOTS:
        return "Invalid location. Use all, desktop, documents or downloads."

    try:
        max_documents = max(1, min(int(max_documents), 500))
        max_results = max(1, min(int(max_results), 50))
    except (TypeError, ValueError):
        return "Invalid result limits."

    if extension and extension != "all" and not extension.startswith("."):
        extension = "." + extension

    if extension and extension != "all" and extension not in SUPPORTED:
        return "Unsupported extension: " + extension

    roots = list(ROOTS.items()) if location == "all" else [
        (location, ROOTS[location])
    ]

    needle = query.casefold()
    filename_matches = []
    other_candidates = []
    errors = 0
    total_documents = 0

    def on_error(_error):
        nonlocal errors
        errors += 1

    # Scan filenames throughout the approved folders.
    # Filename matches are collected even when a file is too large
    # or its document contents cannot be extracted.
    for root_name, root in roots:
        if not root.exists():
            errors += 1
            continue

        for current, directories, filenames in os.walk(
            root, topdown=True, followlinks=False, onerror=on_error
        ):
            current_path = Path(current)
            safe_dirs = []

            for directory in directories:
                if directory.lower() in SKIP_DIRS:
                    continue

                child = current_path / directory

                try:
                    info = child.lstat()
                    attributes = getattr(info, "st_file_attributes", 0)
                    flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)

                    if child.is_symlink() or attributes & flag:
                        continue

                    safe_dirs.append(directory)
                except OSError:
                    errors += 1

            directories[:] = safe_dirs

            for filename in filenames:
                child = current_path / filename

                if child.suffix.lower() not in SUPPORTED:
                    continue

                if extension and extension != "all":
                    if child.suffix.lower() != extension:
                        continue

                safe = safe_document_path(child)

                if safe is None:
                    errors += 1
                    continue

                total_documents += 1

                if needle in safe.name.casefold():
                    filename_matches.append(safe)
                elif len(other_candidates) < max_documents:
                    other_candidates.append(safe)

    # Prioritise filename matches for the bounded title/content inspection.
    selected = (filename_matches + other_candidates)[:max_documents]
    limited = total_documents > max_documents

    title_matches = []
    content_matches = []
    failed = 0
    metadata_failures = 0

    def get_pdf_title(path):
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                return "", "File exceeds the 20 MB metadata limit."

            # Reject files that only have a .pdf extension but are not PDFs.
            with path.open("rb") as handle:
                if handle.read(5) != b"%PDF-":
                    return "", "File does not have a valid PDF header."

            from pypdf import PdfReader

            reader = PdfReader(str(path), strict=False)

            if reader.is_encrypted:
                return "", "PDF is password protected."

            metadata = reader.metadata
            title = ""

            if metadata:
                title = str(metadata.title or "").strip()

            return title, ""

        except Exception as error:
            return "", str(error)

    for path in selected:
        if path.suffix.lower() == ".pdf":
            title, title_note = get_pdf_title(path)

            if title_note:
                metadata_failures += 1

            if title and needle in title.casefold():
                title_matches.append((path, title))

        content, note = extract_text(path)

        if not content:
            failed += 1
            continue

        position = content.casefold().find(needle)

        if position >= 0:
            start = max(0, position - 150)
            end = min(len(content), position + len(query) + 250)

            content_matches.append((
                path,
                content[start:end].replace("\n", " "),
                note
            ))

    lines = [
        "========== DOCUMENT SEARCH ==========",
        "Query: " + query,
        "Location: " + location,
        "Extension: " + (extension or "all supported formats"),
        f"Files scanned: {total_documents}",
        f"Documents inspected for title/content: {len(selected)}",
        "",
        f"Filename matches found: {len(filename_matches)}",
    ]

    for index, path in enumerate(filename_matches[:max_results], 1):
        lines.extend([
            f"  {index}. {path.name}",
            "     " + str(path)
        ])

    if len(filename_matches) > max_results:
        lines.append(
            f"  ... {len(filename_matches) - max_results} more filename matches"
        )

    lines.extend([
        "",
        f"PDF metadata-title matches found: {len(title_matches)}"
    ])

    for index, (path, title) in enumerate(title_matches[:max_results], 1):
        lines.extend([
            f"  {index}. {path.name}",
            "     PDF title: " + title,
            "     " + str(path)
        ])

    if len(title_matches) > max_results:
        lines.append(
            f"  ... {len(title_matches) - max_results} more title matches"
        )

    lines.extend([
        "",
        f"Document content matches found: {len(content_matches)}"
    ])

    for index, (path, snippet, note) in enumerate(
        content_matches[:max_results], 1
    ):
        lines.extend([
            f"  {index}. {path.name}",
            "     " + str(path),
            "     Match: ..." + snippet + "..."
        ])

        if note:
            lines.append("     Note: extraction was bounded.")

    if len(content_matches) > max_results:
        lines.append(
            f"  ... {len(content_matches) - max_results} more content matches"
        )

    if not filename_matches and not title_matches and not content_matches:
        lines.append("")
        lines.append("No filename, PDF title or document-content matches found.")

    lines.extend([
        "",
        f"Extraction failures: {failed}",
        f"PDF metadata extraction failures: {metadata_failures}",
        f"Access or scan errors: {errors}",
        f"Document inspection limit reached: {'YES' if limited else 'NO'}",
        "No files were modified.",
        "====================================="
    ])

    return "\n".join(lines)
