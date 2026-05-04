# ManualAid

[中文](README_ZH.md) / English

A **local-only, human-in-the-loop** copypaste assistant for LLM workflows.

ManualAid provides a Textual-based TUI console that bridges your clipboard and
LLM chat interfaces. Paste LLM-generated tool calls (in XML format), review and
audit dangerous operations, and manage sessions with full history tracking --
all running locally on your machine.

> **Version**: 0.4.1 | **Python**: >=3.14

---

## Features

- **TUI Console** -- Four-tab Textual interface: RichLog, Tool Calls, Audit,
  Statistics
- **12 Built-in Tools** -- File system exploration, search, editing, Git
  integration
- **Safe Editing** -- Two-phase commit for write/edit operations with diff
  preview and manual approval
- **Git Integration** -- Whitelist-based Git command execution with safety
  filters
- **Session Management** -- Automatic session tracking, rename, delete, and
  switch
- **Tool Usage Analytics** -- Per-session and global tool call statistics with
  ranking
- **Audit System** -- Pending write/edit snapshots with approve/reject workflow
- **Result Caching** -- Auto-copy results to clipboard with configurable
  expiration
- **Multi-window Launch** -- Spawn new ManualAid windows for different
  workspaces
- **Cross-platform** -- Windows, macOS, and Linux support(These two haven't been
  tested.)

---

## Quick Start

### Prerequisites

- Python >= 3.14
- Node.js (for dev tooling: Prettier, markdownlint)

### Installation

```bash
# Clone the repository
git clone https://github.com/SunYanbox/ManualAid.git
cd ManualAid

# Create and activate virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
npm install
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
```

### Run

```bash
# Launch with folder picker dialog
python main.py

# Launch directly into a workspace
python main.py -p /path/to/your/project
```

Once running, paste XML-formatted tool calls from your LLM into the REPL input
area. The console parses, executes, and displays results in the appropriate
tabs.

---

## Console Interface

The TUI is built with [Textual](https://textual.textualize.io/) and has four
tabs:

| Tab        | Purpose                                              |
| ---------- | ---------------------------------------------------- |
| RichLog    | General log output and messages                      |
| Tool Calls | Collapsible tool execution results                   |
| Audit      | Pending write/edit operations awaiting approval      |
| Statistics | Session summaries, tool rankings, session management |

### Keyboard Shortcuts

- `Ctrl+Enter` / `Ctrl+J` -- Submit input
- `\` + `Enter` -- Insert newline in multi-line input

### Built-in Commands

| Command      | Aliases        | Description                                                                     |
| ------------ | -------------- | ------------------------------------------------------------------------------- |
| `/quit`      | `/q` / `/exit` | Exit the application                                                            |
| `/tools`     | `/t`           | List all available tools                                                        |
| `/tool`      | `/tool_detail` | Show tool detail by name                                                        |
| `/copy`      | `/c`           | Copy last result to clipboard                                                   |
| `/history`   |                | Show tool execution history                                                     |
| `/help`      | `/h` / `/?`    | Show help text                                                                  |
| `/cls`       |                | Clear the log display                                                           |
| `/workspace` | `/ws`          | Generate a system prompt containing workspace information and tool definitions. |
| `/new`       |                | Launch new ManualAid window                                                     |

---

## Available Tools

ManualAid registers 12 tools for LLM use via XML function calls:

### Query Tools (read-only)

| Tool           | Description                                      |
| -------------- | ------------------------------------------------ |
| `ls`           | List directory contents                          |
| `glob`         | Find files by glob pattern                       |
| `read`         | Read file contents with optional line range      |
| `stat`         | Get file/directory metadata (size, mtime, lines) |
| `exact_search` | Exact string search with case/whole-word options |
| `regex_search` | Regex search with context display                |
| `symbol_ref`   | Find symbol definitions and references in code   |

### Edit Tools (require audit approval)

| Tool    | Description                                         |
| ------- | --------------------------------------------------- |
| `write` | Write file content (creates if missing)             |
| `edit`  | Safe string replacement with diff preview and audit |

### Dangerous Tools (require audit approval)

| Tool  | Description                           |
| ----- | ------------------------------------- |
| `git` | Whitelist-based Git command execution |

> Tool calls use XML format. See `/help` in the console for syntax examples.

---

## Audit Workflow

Write and edit operations go through a two-phase safety workflow:

1. **Preview** -- The tool computes a diff and stores a snapshot with
   `PENDING_AUDIT` status
2. **Review** -- Switch to the Audit tab to review the diff
3. **Decide** -- Click Approve to commit the change, or Reject to discard it

Git commands that are not in the safe list (`status`, `diff`, `log`, `show`)
also require audit approval before execution.

---

## Configuration

Copy `.env.example` to `.env` and adjust as needed:

| Variable                       | Default | Description                               |
| ------------------------------ | ------- | ----------------------------------------- |
| `TOOL_MAX_RESULT_LENGTH`       | 30000   | Max characters in tool output             |
| `TOOL_LIST_TRUNCATE_THRESHOLD` | 100     | Max items in list results                 |
| `TOOL_DICT_TRUNCATE_THRESHOLD` | 100     | Max key-value pairs in dict results       |
| `MANUALAID_AUTO_COPY`          | true    | Auto-copy results to clipboard            |
| `RESULT_EXPIRE_MINUTES`        | 5       | Result cache expiration (minutes)         |
| `SESSION_UPDATE_INTERVAL`      | 30      | Session duration persistence interval (s) |
| `SESSION_FLAG_CHECK_INTERVAL`  | 5       | Deletion flag check & guard interval (s)  |

---

## Development

### Setup

```bash
npm install
pip install -r requirements.txt
```

### Code Quality

```bash
npm run format:check   # Check all formatting (fullwidth + markdown + ruff + prettier)
npm run format:fix     # Auto-fix most formatting issues.
npm run test           # Run tests with coverage report
npm run ci             # Full CI: format fix -> test -> format check
```

Individual checks:

```bash
npm run fw:format:check      # Fullwidth character check
npm run md:format:check      # Markdown lint
npm run ruff:format:check    # Python lint (Ruff)
npm run prettier:format:check# Code formatting (Prettier)
```

### Project Structure

```txt
ManualAid/
  src/
    console/          # Textual TUI application
      commands/       # Console command implementations
      handlers/       # Tool call and command handlers
      ui/             # TUI widgets (tabs, REPL, formatters)
    core/             # Core logic (registry, database, audit, launcher)
    models/           # Data models
    constants/        # Prompts, configuration
    utils/            # Utility functions
    workspace/        # Workspace and tool implementations
  tests/              # Test suite
  scripts/            # Helper scripts (e.g. fix_fullwidth.py)
  docs/               # Documentation and prompt templates
    CHANGELOG.md      # Version history and changelog
    CHANGELOG_ZH.md   # Chinese version of changelog
```

### Tech Stack

- **Python 3.14+** with [Textual](https://textual.textualize.io/) for TUI
- **SQLite3** (WAL mode) for session and tool call persistence
- **Rich** for terminal formatting
- **Ruff** for Python linting, **Prettier** + **markdownlint** for formatting

### Constraints

- `.py` and `.md` files must use halfwidth punctuation only
- Line length limit: 120 characters
- New features require tests

---

## ⚖️ Legal Disclaimer

ManualAid is a **local-only, human-in-the-loop assistant**. It is designed to
facilitate manual copypaste workflows and **does not support automated
interaction** with any LLM platform.

**Users are solely responsible for:**

1. Complying with the Terms of Service (ToS) of the LLM platforms they use.
2. Ensuring their usage does not violate rate limits, automation bans, or other
   policies.

**The author(s) of ManualAid explicitly disclaim any liability for:**

- Misuse of this tool to automate requests, bypass paywalls, or abuse LLM
  services.
- Any account suspensions, legal actions, or damages resulting from such misuse.

If you fork this project, you must retain this disclaimer and ensure your
modifications do not promote or enable automated abuse.
