# DIABLO
### The Windows AI Operator

**An evolving AI-powered desktop operator built with Python.**

DIABLO is a personal AI operator designed to interact with the Windows environment through specialized tools. Its purpose is to move beyond conversational assistance and toward practical computer operations, intelligent file management, system awareness and eventually multi-step desktop automation.

The project is being developed incrementally, prioritizing reliability, safety and real functionality.

---

## Vision

The long-term vision is to build an AI operator capable of understanding its environment, reasoning about user requests, selecting appropriate tools and executing approved operations.

DIABLO is being developed around five major capabilities:

| Stage | Capability | Objective |
|---|---|---|
| 01 | System Monitor | Understand the Windows environment |
| 02 | Smart File Intelligence | Understand, search and organize files |
| 03 | Workflow Engine | Execute multi-step tasks |
| 04 | Screen Awareness | Understand and interact with the desktop |
| 05 | Cybersecurity Toolkit | Perform security-focused analysis |

---

## Current Capabilities

### System Monitor

DIABLO can inspect important information about the computer:

- CPU utilization and processor information.
- RAM usage and availability.
- Running processes.
- Disk capacity and usage.
- Network interfaces.
- System uptime and battery status.

### Application and File Management

DIABLO has tools for working with applications and files:

- Discover and launch applications.
- Inspect running applications.
- List and search files.
- Read and create files.
- Create folders.
- Copy, move and rename files.
- Identify duplicate files.

### Smart File Intelligence

DIABLO can analyze files in approved user directories.

- File audits and storage analysis.
- File extension and category reports.
- Large-file identification.
- Old-file identification.
- Duplicate detection.
- Document text extraction.
- Document search.

### Three-Layer Document Search

A document should remain discoverable even when its contents cannot be extracted.

DIABLO's document search therefore checks:

1. Filename matching.
2. PDF metadata-title matching.
3. Extracted document-content matching.

This allows files to be discovered by name or PDF title even when text extraction fails. Content matching still depends on whether the document can be successfully extracted.

---

## Technology Stack

- Python
- Google Gemini API
- Groq API
- OpenAI-compatible API client
- psutil
- PyAutoGUI
- HTTPX
- pypdf
- python-docx
- openpyxl
- PowerShell
- Git

---

## Project Structure

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
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── PROJECT_HISTORY.md
```

---

## Installation

### Requirements

- Windows 11
- Python 3.13 or compatible version
- Git
- API credentials for the configured AI provider

### 1. Clone the repository

```powershell
git clone https://github.com/rudranoir0-dot/DIABLO-Windows-AI-Operator.git
cd DIABLO-Windows-AI-Operator
```

### 2. Create a virtual environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Configure API credentials

Create a local `.env` file using `.env.example` as a template.

Add your own API credentials locally.

**Never upload `.env` or API keys to GitHub.**

### 5. Launch DIABLO

```powershell
python agent.py
```

A PowerShell `diablo` launcher can also be configured for convenient startup.

---

## Command Reference

| Command | Description |
|---|---|
| `/system` | System information |
| `/processes` | Running process report |
| `/storage` | Storage information |
| `/network` | Network information |
| `/audit all` | Audit approved folders |
| `/filetypes all` | Analyze file types |
| `/largefiles all` | Locate large files |
| `/oldfiles all` | Identify old files |
| `/duplicates` | Identify duplicates |
| `/searchcontent cybersecurity all .pdf` | Search PDFs by filename, metadata title and content |

---

## Safety and Reliability

DIABLO is being developed with controlled execution in mind.

- File access is restricted by the current file-management tools.
- Document searching is read-only.
- Document extraction uses size and content limits.
- File audits do not automatically delete or move files.
- Old files are not automatically considered unnecessary.
- Sensitive file operations should require explicit approval.
- API credentials are kept outside the public source repository.

---

## Development Roadmap

### Stage 1 — System Monitor
Understand the computer, its hardware resources and current operating state.

### Stage 2 — Smart File Intelligence
Develop deeper file understanding, document search and intelligent organization.

### Stage 3 — Workflow Engine
Allow DIABLO to plan and execute multi-step tasks using its available tools.

### Stage 4 — Screen Awareness
Give DIABLO the ability to understand visible applications and interact with the desktop under user control.

### Stage 5 — Cybersecurity Toolkit
Introduce security-focused diagnostics and authorized system analysis.

---

## Development Status

DIABLO is an actively developed personal project.

The System Monitor and core Smart File Intelligence capabilities have been implemented and tested. The remaining stages are under development and should not be considered completed functionality.

The goal is not to build another chatbot.

The goal is to build an AI operator that can understand, plan and act.

**DIABLO — Powerful and reliable, built incrementally.**