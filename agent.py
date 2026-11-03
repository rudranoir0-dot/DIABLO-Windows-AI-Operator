import os
import json
import re
from dotenv import load_dotenv
from openai import OpenAI
from tools import run_tool

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

CLIENTS = {}

if GEMINI_API_KEY and len(GEMINI_API_KEY) >= 20:
    CLIENTS["gemini"] = OpenAI(
        api_key=GEMINI_API_KEY,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        timeout=30.0,
        max_retries=0
    )

if GROQ_API_KEY and len(GROQ_API_KEY) >= 20:
    CLIENTS["groq"] = OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        timeout=30.0,
        max_retries=0
    )

if not CLIENTS:
    raise RuntimeError("No valid AI API keys found. Check your .env file.")

GROQ_MODEL_PRIORITY = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
]

GROQ_MODELS = []
GROQ_MODEL_DISCOVERY_ERROR = None

def refresh_groq_models():
    """Discover supported Groq models available to this API key."""
    global GROQ_MODELS, GROQ_MODEL_DISCOVERY_ERROR

    if "groq" not in CLIENTS:
        GROQ_MODELS = []
        GROQ_MODEL_DISCOVERY_ERROR = "Groq API key unavailable."
        return []

    try:
        result = CLIENTS["groq"].models.list()
        account_models = {item.id for item in result.data}

        GROQ_MODELS = [
            model for model in GROQ_MODEL_PRIORITY
            if model in account_models
        ]

        GROQ_MODEL_DISCOVERY_ERROR = None
        return GROQ_MODELS

    except Exception as error:
        GROQ_MODELS = []
        GROQ_MODEL_DISCOVERY_ERROR = (
            type(error).__name__ + ": " + str(error)
        )
        return []

if not CLIENTS:
    raise RuntimeError("No valid AI API keys found. Check your .env file.")

# Discover models at startup instead of assuming a model is available.
refresh_groq_models()

MODELS = {
    "gemini": "gemini-3.6-flash",
    "groq": GROQ_MODELS[0] if GROQ_MODELS else None
}

if not GROQ_MODELS and "gemini" not in CLIENTS:
    raise RuntimeError(
        "No supported Groq models were discovered and Gemini is unavailable. "
        "Check your API access."
    )

ENGINE_MODE = "groq" if GROQ_MODELS else "gemini"
active_engine = ENGINE_MODE
MODEL = MODELS[active_engine]



def schema(name, description, properties, required):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }
    }


string = {"type": "string"}

TOOLS = [
    schema(
        "get_system_report",
        "Read-only live Windows system report: processor, memory, OS, uptime and battery.",
        {},
        []
    ),
    schema(
        "get_process_report",
        "Read-only list of the highest-memory running processes. Never terminate processes.",
        {"limit": {"type": "integer"}},
        []
    ),
    schema(
        "get_storage_report",
        "Read-only report of storage drives, total capacity, used space and free space.",
        {},
        []
    ),
    schema(
        "get_network_report",
        "Read-only network adapter status and traffic totals.",
        {},
        []
    ),
    schema(
        "get_file_audit_report",
        "Read-only audit of approved user folders. Shows file categories, extensions, sizes, large files and old files. Never changes files.",
        {"location": {"type": "string", "enum": ["all", "desktop", "documents", "downloads"]}},
        ["location"]
    ),
    schema(
        "get_file_types_report",
        "Read-only report counting file extensions and categories in approved user folders.",
        {"location": {"type": "string", "enum": ["all", "desktop", "documents", "downloads"]}},
        ["location"]
    ),
    schema(
        "get_large_files_report",
        "Read-only search for large files. Default threshold 100 MB and maximum 100 results.",
        {
            "location": {"type": "string", "enum": ["all", "desktop", "documents", "downloads"]},
            "min_mb": {"type": "number", "minimum": 0},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100}
        },
        ["location"]
    ),
    schema(
        "get_old_files_report",
        "Read-only search for files not modified for a number of days. Old does not mean safe to delete.",
        {
            "location": {"type": "string", "enum": ["all", "desktop", "documents", "downloads"]},
            "days": {"type": "integer", "minimum": 1},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100}
        },
        ["location"]
    ),
    schema(
        "read_document",
        "Extract bounded text from a supported document inside approved folders.",
        {"path": string},
        ["path"]
    ),
    schema(
        "search_document_content",
        "Search inside supported local documents and return matching snippets.",
        {
            "query": string,
            "location": {
                "type": "string",
                "enum": ["all", "desktop", "documents", "downloads"]
            },
            "extension": string
        },
        ["query", "location", "extension"]
    ),
    schema("list_apps", "Discover Start Menu applications.", {"query": string}, ["query"]),
    schema("open_app", "Open an application.", {"name": string}, ["name"]),
    schema(
        "open_app_for",
        "Open an application, wait the requested number of seconds, then gracefully close it. Duration must be 1 to 60 seconds.",
        {"name": string, "seconds": {"type": "integer"}},
        ["name", "seconds"]
    ),
    schema("list_running_apps", "Show visible running application windows.", {}, []),
    schema("close_app", "Gracefully close a visible application.", {"name": string}, ["name"]),

    schema("list_files", "List files in an allowed user folder.", {"path": string}, ["path"]),
    schema("create_folder", "Create a folder in an allowed user directory.", {"path": string}, ["path"]),
    schema("create_file", "Create a text file without overwriting.", {"path": string, "content": string}, ["path", "content"]),
    schema("read_file", "Read a text file in an allowed directory.", {"path": string}, ["path"]),

    schema(
        "search_files",
        "Search filenames recursively. location must be all, desktop, documents or downloads. Extension is optional; use an empty string if not specified. max_results is normally 100.",
        {
            "query": string,
            "location": string,
            "extension": string,
            "max_results": {"type": "integer"}
        },
        ["query", "location", "extension", "max_results"]
    ),

    schema(
        "find_duplicates",
        "Find files with identical content using SHA-256. Choose all, desktop, documents or downloads.",
        {"location": string},
        ["location"]
    ),

    schema(
        "organize_duplicates",
        "In one batch, scan the selected location, retain one original from each identical group, and move redundant copies into Desktop Duplicate Review. Handles verification internally.",
        {"location": string},
        ["location"]
    ),

    schema(
        "move_file",
        "Move a file or folder. Destination can be a folder or full destination path.",
        {"source": string, "destination": string},
        ["source", "destination"]
    ),

    schema(
        "copy_file",
        "Copy a file or folder without overwriting an existing destination.",
        {"source": string, "destination": string},
        ["source", "destination"]
    ),

    schema(
        "rename_file",
        "Rename a file or folder. new_name must be a filename, not a path.",
        {"source": string, "new_name": string},
        ["source", "new_name"]
    )
]


SYSTEM = """

FILE AND APPLICATION TOOL RULES:

- When the user asks to list or inspect files in Desktop, Documents, or Downloads, use list_files directly.
- When the user asks to find files by name, extension, or search term, use search_files.
- For a read-only overview of their files, use get_file_audit_report.
- For file extensions or categories, use get_file_types_report.
- For large files, use get_large_files_report.
- For old files, use get_old_files_report. Never assume old files are safe to delete.
- Use search_document_content to search inside document contents.
- Use read_document to extract a specific document.
- Never claim to have read a document without a successful tool result.
- Document extraction is bounded and may omit pages, rows or text.
- AI-generated document summaries send extracted text to the selected AI provider.

- For duplicate files, use find_duplicates.
- Never move, rename, copy or delete files as part of an audit. Ask for separate approval before any changes.
- Never open File Explorer just to list or search files. Direct file tools are available.
- Use open_app only when the user explicitly asks to launch an application.
- For timed application use, call open_app_for with the requested application and duration.
- Use only exact tool names from the supplied tool definitions.
- Never append channel markers, internal tokens, explanations, or other text to a tool name.
- Do not claim to have inspected files unless a file tool actually returned the results.


You are Diablo, a capable personal computer assistant.

Speak naturally and concisely.
Use plain text by default.
Never use Markdown bold syntax or decorative formatting.
Avoid unnecessary headings and tables.

You are an operator, not just a chatbot.
Use tools to perform requested tasks.
Never claim success unless a tool confirms it.
You may execute multiple related steps in sequence.
Do not ask unnecessary questions.

APPLICATIONS:
Use list_apps to discover applications.
Use open_app to launch them.
Use list_running_apps to inspect visible windows.

FILE MANAGEMENT:
Search files with search_files.
Use list_files to inspect folders.
Use find_duplicates to identify identical files.
Use organize_duplicates when the user asks to separate, quarantine or organise duplicate copies.

DUPLICATE SEPARATION:
Call organize_duplicates directly for duplicate separation.
It performs one fresh scan, keeps one original per group, moves redundant copies into Desktop Duplicate Review, and verifies the result.
The execution layer asks for one batch approval.
Do not create the folder separately.
Do not call move_file separately for each duplicate.
Do not run find_duplicates again after organize_duplicates because the batch tool verifies its own moves.
Use create_folder to create folders.
Use move_file, copy_file and rename_file for file organisation.
Use read_file to inspect supported text files.

For organisation requests:
1. Search for the relevant files first.
2. Inspect the results.
3. Determine sensible categories from filenames and available context.
4. Explain the proposed organisation briefly.
5. Ask permission before moving or renaming files.
6. Execute only approved operations.
7. Verify the results.

For subject-based organisation, do not pretend to know a document's subject from its filename alone. Read the file when possible or ask when uncertain.

PERMISSIONS:
Always ask before creating files or folders.
Always ask before moving, copying or renaming files.
Always ask before closing applications.
Never delete files.
Never overwrite existing files.

FILE SAFETY:
Only access Desktop, Documents and Downloads.
Never invent paths or results.
Never move files outside the approved folders.
"""

messages = [{"role": "system", "content": SYSTEM}]

CONFIRMATION_REQUIRED = {
    "create_folder",
    "create_file",
    "close_app",
    "open_app_for",
    "organize_duplicates",
    "move_file",
    "copy_file",
    "rename_file"
}


def call_model():
    global active_engine, MODEL

    if ENGINE_MODE == "auto":
        providers = ["gemini", "groq"]
    else:
        providers = [ENGINE_MODE]

    failures = []

    for engine in providers:
        if engine not in CLIENTS:
            failures.append((engine, RuntimeError("Provider key unavailable.")))
            continue

        if engine == "groq":
            candidates = list(GROQ_MODELS)

            if not candidates:
                candidates = refresh_groq_models()

            if not candidates:
                failures.append((
                    engine,
                    RuntimeError(
                        "No supported Groq models available. "
                        + str(GROQ_MODEL_DISCOVERY_ERROR or "")
                    )
                ))
                continue
        else:
            candidates = [MODELS[engine]]

        for model in candidates:
            for attempt in range(2):
                request = {
                    "model": model,
                    "messages": messages,
                    "tools": TOOLS,
                    "tool_choice": "auto"
                }

                if engine == "gemini":
                    request.update({
                        "parallel_tool_calls": False,
                        "reasoning_effort": "low",
                        "temperature": max(0.1, 0.4 - attempt * 0.15),
                        "max_tokens": 1000
                    })
                else:
                    request.update({
                        "reasoning_effort": "low",
                        "max_completion_tokens": 1000
                    })

                try:
                    response = CLIENTS[engine].chat.completions.create(
                        **request
                    )

                    active_engine = engine
                    MODEL = model
                    MODELS[engine] = model
                    return response

                except Exception as error:
                    status = getattr(error, "status_code", None)
                    error_text = str(error).lower()

                    # Credential errors affect the whole provider.
                    if status in (401, 403):
                        raise

                    # Retry malformed tool output once on the same model.
                    if "tool_use_failed" in error_text and attempt == 0:
                        print(
                            f"{model} returned malformed tool output. "
                            "Retrying once..."
                        )
                        continue

                    failures.append((model, error))
                    break

            # This model failed. Try the next available Groq model.
            if engine == "groq" and model != candidates[-1]:
                print(f"{model} failed. Trying the next available Groq model...")

        if engine == "gemini" and ENGINE_MODE == "auto":
            print("Gemini failed. Trying the Groq model pool...")

    details = " | ".join(
        f"{name}: {type(error).__name__}: {error}"
        for name, error in failures
    )
    raise RuntimeError("All available AI models failed. " + details)


def execute_tool(name, arguments):
    if name in CONFIRMATION_REQUIRED:
        labels = {
            "create_folder": "Create folder",
            "create_file": "Create file",
            "close_app": "Close application",
            "open_app_for": "Open application and close it after a delay",
            "organize_duplicates": "Move duplicate files in one batch",
            "move_file": "Move file",
            "copy_file": "Copy file",
            "rename_file": "Rename file"
        }

        print(f"\nPermission required: {labels[name]}")
        print(json.dumps(arguments, indent=2, ensure_ascii=False))

        approval = input("Allow this action? (y/n): ").strip().lower()

        if approval not in ("y", "yes"):
            return "User denied permission. Action cancelled."

    try:
        result = run_tool(name, arguments)
        return str(result)
    except Exception as error:
        return f"Action failed: {error}"


print("=" * 48)
print("             DIABLO")
print("=" * 48)
print("AI Core  : " + MODEL)
print("Provider : " + active_engine.upper())
print("Mode     : " + ENGINE_MODE.upper())
print("Modules  : Application Manager, File Manager")
print("Commands : /audit | /filetypes | /largefiles | /oldfiles | /duplicates | /readfile | /searchcontent")
print("Type 'exit' to quit.")
print("=" * 48)


while True:
    try:
        user = input("\nYou > ").strip()

        if user.lower() in ("exit", "quit"):
            print("Operator stopped.")
            break

        if not user:
            continue

        command = user.lower()

        if command in ("/switch groq", "/groq"):
            if "groq" not in CLIENTS:
                print("Groq is unavailable. Check GROQ_API_KEY in .env.")
            else:
                if not GROQ_MODELS:
                    refresh_groq_models()

                if not GROQ_MODELS:
                    print("No supported Groq models are currently available.")
                    print(GROQ_MODEL_DISCOVERY_ERROR or "")
                else:
                    ENGINE_MODE = "groq"
                    active_engine = "groq"
                    MODEL = GROQ_MODELS[0]
                    print("DIABLO switched to GROQ.")
                    print("Selected model:", MODEL)
            continue

        if command in ("/switch gemini", "/gemini"):
            if "gemini" not in CLIENTS:
                print("Gemini is unavailable. Check GEMINI_API_KEY in .env.")
            else:
                ENGINE_MODE = "gemini"
                active_engine = "gemini"
                MODEL = MODELS["gemini"]
                print("DIABLO switched to GEMINI.")
            continue

        if command in ("/switch auto", "/auto"):
            if "gemini" not in CLIENTS:
                print("AUTO requires a Gemini API key.")
            else:
                if not GROQ_MODELS:
                    refresh_groq_models()

                if not GROQ_MODELS:
                    print("AUTO requires at least one available Groq model.")
                else:
                    ENGINE_MODE = "auto"
                    active_engine = "gemini"
                    MODEL = MODELS["gemini"]
                    print("AUTO enabled. Gemini primary; Groq model pool fallback.")
            continue

        if command == "/status":
            print("DIABLO STATUS")
            print("Mode     :", ENGINE_MODE.upper())
            print("Active   :", active_engine.upper())
            print("Model    :", MODEL)
            print("Available:", ", ".join(name.upper() for name in CLIENTS))
            print("Groq pool :", len(GROQ_MODELS), "available model(s)")
            continue

        if command == "/models":
            print("AVAILABLE GROQ MODELS")
            if GROQ_MODELS:
                for index, model in enumerate(GROQ_MODELS, 1):
                    label = "ACTIVE" if model == MODEL and active_engine == "groq" else "available"
                    print(f"{index}. {model} [{label}]")
            else:
                print("No supported Groq models discovered.")
                print(GROQ_MODEL_DISCOVERY_ERROR or "")
            continue

        if command == "/refreshmodels":
            refreshed = refresh_groq_models()
            if refreshed:
                MODELS["groq"] = refreshed[0]
                print("Groq model list refreshed:")
                for model in refreshed:
                    print("-", model)
                if ENGINE_MODE == "groq" and MODEL not in refreshed:
                    MODEL = refreshed[0]
                    active_engine = "groq"
                    print("Active model changed to:", MODEL)
            else:
                print("Could not discover supported Groq models.")
                print(GROQ_MODEL_DISCOVERY_ERROR or "")
            continue

        if command == "/help":
            print("/switch groq   - Use Groq")
            print("/switch gemini - Use Gemini")
            print("/switch auto   - Gemini with Groq model-pool fallback")
            print("/models        - List available Groq models")
            print("/refreshmodels - Refresh the Groq model list")
            print("/status        - Show current AI provider")
            print("/exit          - Exit DIABLO")
            continue

        # DIRECT SYSTEM MONITOR COMMANDS
        normalized_monitor_command = user.lower().strip()
        monitor_tool = None

        monitor_commands = {
            "/system": "get_system_report",
            "/monitor": "get_system_report",
            "/health": "get_system_report",
            "/processes": "get_process_report",
            "/storage": "get_storage_report",
            "/network": "get_network_report",
        }

        monitor_tool = monitor_commands.get(normalized_monitor_command)

        if monitor_tool is None:
            if any(term in normalized_monitor_command for term in (
                "cpu usage", "ram usage", "memory usage",
                "computer health", "system health", "system status",
                "computer status", "how is my computer",
                "how is my pc", "system information",
                "system info", "battery status"
            )):
                monitor_tool = "get_system_report"

            elif any(term in normalized_monitor_command for term in (
                "top processes", "running processes",
                "process list", "processes running"
            )):
                monitor_tool = "get_process_report"

            elif any(term in normalized_monitor_command for term in (
                "disk space", "storage space", "drive space",
                "storage usage", "how much space"
            )):
                monitor_tool = "get_storage_report"

            elif any(term in normalized_monitor_command for term in (
                "network status", "network usage",
                "network adapters", "network traffic"
            )):
                monitor_tool = "get_network_report"

        if monitor_tool:
            print("\nDIABLO SYSTEM MONITOR")
            try:
                monitor_result = run_tool(monitor_tool, {})
                print(str(monitor_result))
            except Exception as monitor_error:
                print(
                    "SYSTEM MONITOR ERROR:",
                    type(monitor_error).__name__,
                    str(monitor_error)
                )
            continue

        # DIRECT SMART FILE INTELLIGENCE
        normalized_file_query = user.lower().strip()
        file_tool = None
        file_arguments = {}

        valid_locations = ("all", "desktop", "documents", "downloads")
        query_parts = normalized_file_query.split()

        if normalized_file_query.startswith((
            "/audit", "/filetypes", "/largefiles",
            "/oldfiles", "/duplicates"
        )):
            command_name = query_parts[0]
            requested_location = (
                query_parts[1] if len(query_parts) > 1 else "all"
            )

            if requested_location not in valid_locations:
                print("Use location: all, desktop, documents or downloads.")
                continue

            if command_name == "/audit":
                file_tool = "get_file_audit_report"
                file_arguments = {"location": requested_location}

            elif command_name == "/filetypes":
                file_tool = "get_file_types_report"
                file_arguments = {"location": requested_location}

            elif command_name == "/largefiles":
                file_tool = "get_large_files_report"
                minimum_mb = 100
                if len(query_parts) > 2:
                    try:
                        minimum_mb = float(query_parts[2])
                    except ValueError:
                        print("Minimum size must be a number in MB.")
                        continue
                file_arguments = {
                    "location": requested_location,
                    "min_mb": minimum_mb,
                    "limit": 20
                }
                file_tool = "get_large_files_report"

            elif command_name == "/oldfiles":
                age_days = 365
                if len(query_parts) > 2:
                    try:
                        age_days = int(query_parts[2])
                    except ValueError:
                        print("Age must be a whole number of days.")
                        continue
                file_tool = "get_old_files_report"
                file_arguments = {
                    "location": requested_location,
                    "days": age_days,
                    "limit": 20
                }

            elif command_name == "/duplicates":
                file_tool = "find_duplicates"
                file_arguments = {"location": requested_location}

        else:
            requested_location = "all"

            if "desktop" in normalized_file_query:
                requested_location = "desktop"
            elif "documents" in normalized_file_query:
                requested_location = "documents"
            elif "download" in normalized_file_query:
                requested_location = "downloads"

            if (
                "duplicate" in normalized_file_query
                and any(word in normalized_file_query for word in ("find", "scan", "show", "identify", "check"))
            ):
                file_tool = "find_duplicates"
                file_arguments = {"location": requested_location}

            elif (
                any(word in normalized_file_query for word in ("large", "largest", "biggest", "space hog"))
                and "file" in normalized_file_query
            ):
                file_tool = "get_large_files_report"
                file_arguments = {
                    "location": requested_location,
                    "min_mb": 100,
                    "limit": 20
                }

            elif (
                any(phrase in normalized_file_query for phrase in (
                    "old files", "older files", "forgotten files",
                    "not modified", "haven't modified",
                    "have not been modified", "not been modified",
                    "have not changed", "not updated"
                ))
            ):
                file_tool = "get_old_files_report"
                file_arguments = {
                    "location": requested_location,
                    "days": 365,
                    "limit": 20
                }

            elif (
                any(phrase in normalized_file_query for phrase in (
                    "file types", "types of files", "file extensions",
                    "extension report", "categorize my files"
                ))
            ):
                file_tool = "get_file_types_report"
                file_arguments = {"location": requested_location}

            elif (
                any(phrase in normalized_file_query for phrase in (
                    "audit my files", "file audit", "audit files",
                    "analyze my files", "analyse my files",
                    "file organization audit", "file organisation audit",
                    "organize audit", "organization proposal"
                ))
            ):
                file_tool = "get_file_audit_report"
                file_arguments = {"location": requested_location}

        # DIRECT DOCUMENT CONTENT COMMANDS
        document_tool = None
        document_arguments = {}

        if normalized_file_query.startswith("/readfile "):
            requested_path = user[len("/readfile "):].strip().strip('"')

            if not requested_path:
                print('Usage: /readfile "full document path"')
                continue

            document_tool = "read_document"
            document_arguments = {"path": requested_path}

        elif normalized_file_query.startswith("/searchcontent "):
            payload = user[len("/searchcontent "):].strip()
            search_location = "all"
            search_extension = ""

            parts = payload.split()

            supported_extensions = (
                ".pdf", ".docx", ".xlsx", ".xlsm", ".csv",
                ".txt", ".md", ".log", ".json", ".xml",
                ".html", ".py", ".ps1", ".sql", ".yaml", ".yml"
            )

            if parts and parts[-1].lower() in supported_extensions:
                search_extension = parts[-1].lower()
                payload = payload.rsplit(maxsplit=1)[0]
                parts = payload.split()

            if parts and parts[-1].lower() in valid_locations:
                search_location = parts[-1].lower()
                payload = payload.rsplit(maxsplit=1)[0]

            search_phrase = payload.strip().strip('"')

            if len(search_phrase) < 2:
                print("Usage: /searchcontent <phrase> [location] [.pdf]")
                continue

            document_tool = "search_document_content"
            document_arguments = {
                "query": search_phrase,
                "location": search_location,
                "extension": search_extension
            }

        elif (
            any(phrase in normalized_file_query for phrase in (
                "search inside", "search within", "find text in",
                "look inside"
            ))
            and " for " in normalized_file_query
        ):
            search_phrase = user.rsplit(" for ", 1)[1].strip().strip('"')
            search_extension = ""

            if "pdf" in normalized_file_query:
                search_extension = ".pdf"
            elif "docx" in normalized_file_query or "word document" in normalized_file_query:
                search_extension = ".docx"
            elif "xlsx" in normalized_file_query or "spreadsheet" in normalized_file_query:
                search_extension = ".xlsx"

            if len(search_phrase) >= 2:
                document_tool = "search_document_content"
                document_arguments = {
                    "query": search_phrase,
                    "location": requested_location,
                    "extension": search_extension
                }

        elif normalized_file_query.startswith((
            "read this document:", "read document:", "read this file:"
        )):
            requested_path = user.split(":", 1)[1].strip().strip('"')

            if requested_path:
                document_tool = "read_document"
                document_arguments = {"path": requested_path}

        if document_tool:
            print("\nDIABLO DOCUMENT INTELLIGENCE")
            try:
                print(str(run_tool(document_tool, document_arguments)))
            except Exception as document_error:
                print(
                    "DOCUMENT INTELLIGENCE ERROR:",
                    type(document_error).__name__,
                    str(document_error)
                )
            continue

        if file_tool:
            print("\nDIABLO SMART FILE INTELLIGENCE")
            try:
                file_result = run_tool(file_tool, file_arguments)
                print(str(file_result))
            except Exception as file_error:
                print(
                    "FILE INTELLIGENCE ERROR:",
                    type(file_error).__name__,
                    str(file_error)
                )
            continue

                # DIRECT FILE DISPLAY: bypass the AI for explicit folder-list requests.
        normalized_user = user.lower().strip()
        requested_folder = None

        folder_aliases = {
            "desktop": ("desktop",),
            "documents": ("documents",),
            "downloads": ("downloads", "download", "dowloads")
        }

        if normalized_user.startswith("/files "):
            requested_name = normalized_user.split(maxsplit=1)[1].strip()
            for folder, aliases in folder_aliases.items():
                if requested_name in aliases:
                    requested_folder = folder.title()
                    break

            if requested_folder is None:
                print("Use: /files desktop, /files documents, or /files downloads")
                continue

        else:
            listing_phrases = (
                "list", "show", "display", "find all",
                "what is in", "what's in", "contents of",
                "show me the files", "get the files"
            )

            if any(phrase in normalized_user for phrase in listing_phrases):
                for folder, aliases in folder_aliases.items():
                    if any(alias in normalized_user for alias in aliases):
                        requested_folder = folder.title()
                        break

        if requested_folder:
            print(f"\\nDIABLO FILE MANAGER > {requested_folder}")
            try:
                direct_result = run_tool(
                    "list_files",
                    {"path": requested_folder}
                )
                print(str(direct_result))
            except Exception as file_error:
                print("FILE MANAGER ERROR:", type(file_error).__name__, str(file_error))
            continue

        messages = [messages[0]] + messages[-10:]

        messages.append({"role": "user", "content": user})

        for _ in range(8):
            response = call_model()
            message = response.choices[0].message

            messages.append(message.model_dump(exclude_none=True))

            if not message.tool_calls:
                cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", message.content or "Task completed.")
                print("\nAI > " + cleaned)
                break

            for call in message.tool_calls:
                name = call.function.name

                try:
                    arguments = json.loads(call.function.arguments or "{}")
                    result = execute_tool(name, arguments)
                except json.JSONDecodeError:
                    result = "Invalid tool arguments."
                except Exception as error:
                    result = f"Action failed: {error}"

                messages.append({
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": str(result)[:2500]
                })
        else:
            print("\nAI > I reached the execution limit for this request.")

        if len(messages) > 35:
            messages = [messages[0]] + messages[-24:]

    except KeyboardInterrupt:
        print("\nOperator stopped.")
        break

    except Exception as error:
        print("\nSomething went wrong:", type(error).__name__, str(error))
        print("HTTP STATUS:", getattr(error, "status_code", "not provided"))
        print("API DETAILS:", getattr(error, "body", "not provided"))
        response = getattr(error, "response", None)
        if response is not None:
            try:
                print("API RESPONSE:", response.text[:2000])
            except Exception:
                pass
