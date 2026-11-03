# DIABLO — PROJECT HISTORY
## Engineering Log, Implementation Record and Development Roadmap

**Project:** DIABLO — Windows AI Operator
**Development environment:** Windows 11, Python, PowerShell and Visual Studio Code
**Project directory:** `C:\Users\Administrator\Desktop\WindowsAI`

---

# 01. Project Origin

DIABLO began with the objective of creating an AI-powered Windows operator.

The original idea was to move beyond a conventional chatbot and build a system that could interact with the actual computer through Python functions and specialized modules.

The intended architecture:

1. User provides an instruction.
2. The AI interprets the request.
3. It selects an appropriate tool.
4. The tool interacts with Windows or local files.
5. The result is returned to the AI.
6. The AI reports the outcome.

The project was divided into incremental stages to avoid building too many untested capabilities simultaneously.

## Development principles

- Actual functionality over demonstrations.
- Modular Python architecture.
- Controlled tool execution.
- Restricted file access.
- Explicit approval for sensitive actions.
- Backups before important modifications.
- Syntax validation and functional testing.

---

# 02. Initial Environment Setup

The project was established in:

`C:\Users\Administrator\Desktop\WindowsAI`

### Development tools

| Component | Configuration |
|---|---|
| Operating system | Windows 11 |
| Programming language | Python |
| Python version observed | 3.13.7 |
| Editor | Visual Studio Code |
| Terminal | PowerShell |
| Version control | Git |
| Virtual environment | `venv` |

Python's virtual environment keeps the project's dependencies isolated.

The project uses:

`.\venv\Scripts\python.exe`

A PowerShell profile function named `diablo` was configured to launch the agent conveniently.

The launcher was successfully tested.

---

# 03. AI Provider Configuration

DIABLO was configured to work with AI providers using credentials stored locally.

The environment configuration includes:

- `GEMINI_API_KEY`
- `GROQ_API_KEY`

The project uses an OpenAI-compatible client for provider communication.

### Model discovery improvement

An initial fixed Groq model selection produced a 404 response because the model was unavailable.

Instead of relying entirely on a single hardcoded model, model discovery was introduced.

Models observed during discovery included:

- `openai/gpt-oss-120b`
- `openai/gpt-oss-20b`
- `qwen/qwen3.8-27b`

Gemini had also been tested using `gemini-3.6-flash`.

The intended provider strategy included Gemini as the primary engine in AUTO mode and Groq as a fallback pool.

### Tool-call validation

A malformed tool call containing an unwanted internal channel marker caused a Groq validation error.

This exposed the need for strict tool-name formatting.

The agent's instructions and tool flow were subsequently adjusted to use exact registered function names.

---

# 04. Application and File Management Foundation

The project established Python-based tools for interacting with Windows applications and user files.

### Application capabilities

- `list_apps`
- `open_app`
- `list_running_apps`
- `close_app`
- `open_app_for`

The timed application operation supports opening an application for a requested duration, followed by a graceful close attempt.

### File-management module

File-management functionality is located in:

`modules/file_manager.py`

Implemented operations include:

- `list_files`
- `create_folder`
- `create_file`
- `read_file`
- `search_files`
- `find_duplicates`
- `organize_duplicates`
- `move_file`
- `copy_file`
- `rename_file`

### Path restrictions

The approved roots are:

- Desktop
- Documents
- Downloads

The module uses path validation before file operations.

This was intended to prevent the tools from operating arbitrarily across the entire computer.

### Duplicate organization experiment

An earlier duplicate-organization operation moved 27 duplicate copies into:

`Desktop\Duplicate Review`

The result reported zero failures.

The purpose was to isolate duplicates for review instead of deleting files automatically.

---

# 05. STAGE 1 — SYSTEM MONITOR

**Objective:** Give DIABLO awareness of the computer's current operating state.

The System Monitor was implemented with the Python `psutil` library.

The following functions were added to `tools.py`:

- `get_system_report()`
- `get_process_report()`
- `get_storage_report()`
- `get_network_report()`
- `get_status()`

Tool definitions and dispatcher registration were added to the agent architecture.

## 5.1 CPU and system information

Implemented information:

- CPU usage.
- Logical processor count.
- Physical processor count.
- CPU frequency.
- System uptime.

## 5.2 Memory information

Implemented information:

- Total RAM.
- Used RAM.
- Available RAM.
- Percentage utilization.

## 5.3 Process monitoring

DIABLO can inspect running processes and report resource utilization.

This includes processes using significant memory.

## 5.4 Storage analysis

DIABLO can report disk partitions and their:

- Total capacity.
- Used storage.
- Free storage.
- Percentage utilization.

## 5.5 Network inspection

DIABLO can inspect network interfaces and related network information.

## 5.6 Commands

| Command | Function |
|---|---|
| `/system` | System report |
| `/processes` | Process report |
| `/storage` | Storage report |
| `/network` | Network report |

## 5.7 Testing

All five System Monitor functions were exercised successfully.

One historical test reported:

| Metric | Observed result |
|---|---:|
| CPU usage | 14.7% |
| Logical CPU cores | 4 |
| Physical CPU cores | 2 |
| CPU frequency | 2301 MHz |
| RAM total | 11.89 GB |
| RAM used | 5.70 GB |
| RAM available | 6.20 GB |
| RAM utilization | 47.9% |
| Battery | 100%, plugged in |

System uptime was approximately 17 days and 3 hours in that test.

The C: drive showed approximately 80% storage usage, while the G: drive showed approximately 81%.

These measurements were historical test results, not permanent hardware specifications or current readings.

### Stage 1 outcome

System Monitor implemented and tested.

DIABLO gained the ability to inspect major Windows resource categories through Python tools.

---

# 06. STAGE 2 — SMART FILE INTELLIGENCE

**Objective:** Enable DIABLO to understand file collections and identify useful storage information.

The principal module is:

`modules/file_intelligence.py`

This module performs metadata-based analysis of approved folders.

It provides file audits, category analysis, large-file detection and old-file identification.

## 6.1 File audit

Command:

`/audit all`

The audit reports:

- Total files.
- Total storage size.
- File categories.
- File extensions.
- Large files.
- Old files.
- Largest files.

### Historical test

One successful audit found:

- 1,652 files.
- 9.16 GB total.
- 12 files at least 100 MB.
- 1,175 files not modified for at least 365 days.

This established the initial file-audit capability.

## 6.2 File type analysis

Command:

`/filetypes all`

The tool categorizes files by their extensions.

Historical Documents-folder output:

- 74 files.
- 46 other.
- 22 PDFs.
- 5 text files.
- 1 executable.

## 6.3 Large-file detection

Command:

`/largefiles all`

The tool identifies files exceeding a size threshold.

A historical Desktop scan found no files at or above 100 MB.

## 6.4 Old-file detection

Command:

`/oldfiles all`

The tool finds files that have not been modified within a specified period.

The first broad test found 1,175 files not modified for at least 365 days.

An important rule was established:

Old files must not automatically be considered safe for deletion.

## 6.5 Duplicate detection

Command:

`/duplicates`

This identifies potential duplicate files.

The existing duplicate organizer can move copies into a review folder, but automatic deletion is not part of the auditing process.

### Stage 2 file-analysis outcome

File auditing, extension classification, large-file analysis, old-file analysis and duplicate detection were implemented and tested.

---

# 07. DOCUMENT INTELLIGENCE

**Objective:** Move beyond file metadata and allow DIABLO to inspect document contents.

Implementation module:

`modules/document_intelligence.py`

The tools were registered in `tools.py`:

- `read_document`
- `search_document_content`

The corresponding tool schemas and natural-language routing were added to `agent.py`.

## 7.1 Supported document formats

The module recognizes:

- PDF
- DOCX
- XLSX
- XLSM
- CSV
- TXT
- MD
- LOG
- JSON
- XML
- HTML
- PY
- PS1
- SQL
- YAML
- YML

## 7.2 Extraction libraries

| Library | Use |
|---|---|
| pypdf | PDF text extraction and metadata |
| python-docx | DOCX extraction |
| openpyxl | Spreadsheet extraction |

The installed dependencies were checked during development.

## 7.3 Extraction limits

The following limits were configured:

| Parameter | Configured value |
|---|---:|
| Maximum file size | 20 MB |
| Maximum extracted text | 12,000 characters |
| Maximum PDF pages | 30 |
| Default search document limit | 250 |

Spreadsheet extraction is also bounded by worksheet, row and column counts.

## 7.4 Read-document tool

The `read_document` function validates the document path and attempts bounded text extraction.

Its output can include:

- Document name.
- Full path.
- Extracted character count.
- Extracted text.
- Extraction limitations.

An important agent instruction was added:

DIABLO must never claim that it successfully read a document without a successful tool result.

## 7.5 Initial content search

Command:

`/searchcontent cybersecurity all .pdf`

The initial search implementation worked by extracting document text and searching for the requested phrase.

However, this exposed a discovery limitation.

---

# 08. DEBUGGING — PDF DISCOVERY FAILURE

During cybersecurity PDF search testing, DIABLO returned:

- Documents examined: 250.
- Matches found: 0.
- Extraction failures: 88.
- Access or scan errors: 0.
- Document limit reached: YES.

The terminal also displayed PDF parser warnings:

- Invalid PDF header.
- Incorrect startxref pointer.
- Object-stream parsing warnings.

The problem was not necessarily that the requested phrase was absent.

The original search flow skipped files whenever text extraction failed.

In practical terms:

1. Locate a document.
2. Extract its text.
3. If no text is returned, skip the document.
4. Otherwise, search its contents.

This meant a file named `Cybersecurity_Notes.pdf` could be missed simply because its PDF structure was corrupted or unsupported.

We identified that filename discovery and content extraction needed to operate independently.

---

# 09. LATEST UPGRADE — THREE-LAYER DOCUMENT SEARCH

The search implementation was upgraded inside:

`modules/document_intelligence.py`

We replaced only the `search_document_content()` function.

The existing extraction function was preserved.

The command parser in `agent.py` did not need modification.

## 9.1 Filename matching

The updated function searches filenames independently of document extraction.

Examples:

- `Cybersecurity.pdf`
- `Cybersecurity_Notes.pdf`
- `Introduction_to_Cybersecurity.pdf`

These can appear in search results even if the document cannot be opened or parsed.

## 9.2 PDF metadata-title matching

PDF metadata inspection was added.

DIABLO checks the internal PDF title field.

Example:

- Filename: `Document_01.pdf`
- Internal title: `Introduction to Cybersecurity`

This allows discovery through the internal document title even if the filename does not contain the requested phrase.

The implementation checks the PDF header (`%PDF-`) before asking pypdf to parse the file.

It also handles password-protected PDFs and metadata extraction errors.

## 9.3 Document-content matching

The original text-search capability was retained.

DIABLO extracts bounded content and finds the requested phrase.

When a match is found, it reports a nearby text snippet.

## 9.4 Improved result reporting

The new report separates the three match categories:

- Filename matches.
- PDF metadata-title matches.
- Document-content matches.

It also reports:

- Total files scanned.
- Number inspected for metadata and content.
- Extraction failures.
- Metadata extraction failures.
- Access and scan errors.
- Whether the document inspection limit was reached.

## 9.5 Safety and backup

The patch:

1. Located the search function exactly once.
2. Created a timestamped backup.
3. Replaced only the search function.
4. Ran Python syntax compilation.
5. Restored the backup automatically if compilation failed.

The syntax check passed.

The user subsequently tested the new implementation and confirmed:

**"great working"**

### Latest outcome

Three-layer document search implemented and confirmed working.

---

# 10. CURRENT COMMAND INVENTORY

| Command | Capability |
|---|---|
| `/system` | System monitoring |
| `/processes` | Process monitoring |
| `/storage` | Disk usage |
| `/network` | Network inspection |
| `/audit all` | File audit |
| `/filetypes all` | File type classification |
| `/largefiles all` | Large-file discovery |
| `/oldfiles all` | Old-file discovery |
| `/duplicates` | Duplicate detection |
| `/readfile` | Existing file-reading interface |
| `/searchcontent cybersecurity all .pdf` | Three-layer document search |

Natural-language routing also exists for several file-reporting and document operations.

---

# 11. DEVELOPMENT AND DEPENDENCY RECORD

The following dependencies were found available during development:

| Package | Function |
|---|---|
| psutil | System monitoring |
| openai | AI API client |
| python-dotenv | Environment configuration |
| pyautogui | Desktop automation foundation |
| httpx | HTTP communication |
| pypdf | PDF reading |
| python-docx | DOCX reading |
| openpyxl | Excel reading |

A `requirements.txt` was created during GitHub preparation containing these package names.

The exact dependency versions have not yet been pinned.

---

# 12. PROJECT STRUCTURE

The project currently includes these important files and directories:

```text
WindowsAI/
│
├── agent.py
├── tools.py
│
├── modules/
│   ├── file_manager.py
│   ├── file_intelligence.py
│   └── document_intelligence.py
│
├── logs/
├── tools/
├── venv/
│
├── .env
├── .env.example
├── .env.txt
├── .gitignore
├── requirements.txt
├── README.md
└── PROJECT_HISTORY.md
```

This is a working structural reference. Some additional backup and utility scripts also exist in the local project directory.

The virtual environment, credentials, logs and development backups should not be part of the public source history.

---

# 13. GIT AND GITHUB PREPARATION

Git was installed and verified.

Observed Git version:

`git version 2.51.0.windows.1`

A `.gitignore` was created to exclude:

- `.env`
- `.env.*`, except `.env.example`
- `.env.txt`
- Python virtual environments.
- Python cache files.
- Logs.
- Temporary files.
- Development backups.
- Local test and diagnostic scripts.
- Build output.
- Local editor configuration.

A blank `.env.example` was also created.

A README was prepared to describe the project.

### Important security discovery

The initial credential scan detected a Groq API key pattern in `.env.txt`.

That file must not be uploaded.

The real `.env` and `.env.txt` should remain local. Git should be checked to confirm both are ignored before any commit.

### GitHub status

At the time of this history update:

- Git was installed.
- Project preparation had started.
- `.gitignore` and `.env.example` were created.
- `README.md` creation was interrupted and was subsequently handled separately.
- The Git repository had not yet been verified as initialized.
- No successful GitHub push had been confirmed.

The first upload remains a pending task.

---

# 14. CURRENT IMPLEMENTATION STATUS

| Component | Implementation status |
|---|---|
| Python project environment | Established |
| PowerShell launcher | Tested |
| AI provider configuration | Established |
| Groq model discovery | Implemented |
| Application manager | Existing functional foundation |
| File manager | Implemented |
| System Monitor | Implemented and tested |
| File auditing | Implemented and tested |
| File type analysis | Implemented and tested |
| Large-file detection | Implemented and tested |
| Old-file detection | Implemented and tested |
| Duplicate detection | Implemented and tested |
| Document extraction | Implemented |
| Document-content search | Implemented |
| Filename matching | Implemented in upgraded search |
| PDF metadata-title matching | Implemented in upgraded search |
| Three-layer document search | User confirmed working |
| GitHub publication | Pending |
| Smart File Organizer | Not implemented |
| Workflow Engine | Not implemented |
| Screen Awareness | Not implemented |
| Cybersecurity Toolkit | Not implemented |

---

# 15. NEXT DEVELOPMENT TARGET — SMART FILE ORGANIZER

The next priority is to complete the remaining work in Stage 2.

The proposed Smart File Organizer should work as follows.

### Phase A — Analyze

DIABLO scans approved folders and identifies file categories.

Possible categories:

- Cybersecurity
- Programming
- Study Materials
- Documents
- Images
- Videos
- Audio
- Installers
- Archives
- Miscellaneous

### Phase B — Plan

DIABLO proposes a folder structure and maps the detected files to their proposed destinations.

### Phase C — Preview

Before performing any changes, DIABLO displays:

- Original location.
- Proposed destination.
- Reason for categorization.
- Potential naming conflicts.
- Files that require manual review.

### Phase D — Approval

The user reviews the proposed changes and explicitly approves them.

### Phase E — Execution

DIABLO performs only approved file moves and records the results.

No automatic deletion.

No silent moving.

No unapproved changes.

---

# 16. LONG-TERM ROADMAP

## Stage 1 — System Monitor
Status: Implemented and tested.

## Stage 2 — Smart File Intelligence
Status: Core capabilities implemented; Smart File Organizer remains to be built.

## Stage 3 — Workflow Engine
Planned.

Multi-step task planning, tool selection, execution, approval and operation logging.

## Stage 4 — Screen Awareness
Planned.

Visible desktop understanding, screenshot analysis and controlled application interaction.

## Stage 5 — Cybersecurity Toolkit
Planned.

Authorized Windows security checks, network posture analysis, configuration reviews and security reporting.

The future cybersecurity capabilities should begin with read-only diagnostics and controlled remediation.

---

# 17. ENGINEERING LESSONS

Several practical lessons emerged during development.

### 1. Do not trust fixed model names forever

Provider model availability can change. Model discovery is more flexible than relying entirely on one hardcoded identifier.

### 2. Tool calls need strict formatting

AI providers can reject malformed tool calls. Exact tool names and schemas matter.

### 3. File discovery must be independent of extraction

A file should remain searchable by name even if its contents cannot be extracted.

### 4. A failed extraction does not mean a file is irrelevant

Extraction errors must be reported separately from search results.

### 5. Read-only analysis should come first

It is safer to analyze and propose actions before modifying a user's files.

### 6. Test every upgrade

A patch is not complete merely because Python accepts the code. The actual operation must also be tested.

### 7. Preserve working functionality

New modules should be integrated without unnecessarily rewriting already working features.

---

# 18. DEVELOPMENT LOG — CURRENT MILESTONE

The initial foundation is in place.

DIABLO can inspect Windows system resources, examine file collections, identify duplicates and extract or search supported documents.

The latest major improvement was three-layer document search. Filename and PDF metadata matching provide discovery paths independent of text extraction, although some PDFs can still fail during content extraction.

The project is transitioning from basic intelligence toward more autonomous but controlled operations.

The next milestone is the Smart File Organizer.

The immediate repository milestone is to safely publish the existing source code and development documentation to GitHub.

**Project philosophy:**

Build capabilities one at a time. Make them work. Test them. Preserve what works. Then expand.

---

# DIABLO
### Powerful and reliable, built incrementally.
