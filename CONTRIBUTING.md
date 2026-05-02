# Contributing Guide

Thank you for your interest in ManualAid! This document will help you understand
how to contribute to the project.

Before you begin, please read the project's [README.md](README.md) to understand
the basic information and technical constraints.

---

## Legal Notice

ManualAid is a **purely local, human-assisted tool**. It is designed to
facilitate manual copy-paste workflows and **does not support** automated
interaction with LLM platforms.

**Users must take full responsibility for:**

1. Complying with the Terms of Service (ToS) of the LLM platforms they use.
2. Ensuring their usage does not violate rate limits, automation bans, or other
   policies.

**The author of ManualAid explicitly disclaims all liability for:**

- Misuse of this tool for automated requests, bypassing paywalls, or abusing LLM
  services.
- Any account suspensions, legal actions, or losses resulting from such misuse.

If you fork this project, **you must retain this disclaimer** and ensure that
your modifications do not facilitate or enable automated abuse.

---

## Issues and Pull Requests

### Issues

- **Titles and content must be bilingual (Chinese and English)**.
- Clearly describe the problem or suggestion, with reproduction steps (if
  applicable).

### Pull Requests

- PR titles should be bilingual (Chinese/English) or Chinese only.
- Ensure the local `npm run ci` check passes.
- Link related issues (e.g., `Closes #42`).
- Before contributing complex features, you must create an Issue to clarify the
  objective and avoid development directions that differ from the project's
  actual direction.

---

## Environment Setup

### Prerequisites

- **Python >= 3.14** (specified in `pyproject.toml`)
- **Node.js** (for development tools: Prettier, markdownlint)
- **Git**

### Clone the Repository

```bash
git clone https://github.com/SunYanbox/ManualAid.git
cd ManualAid
```

### Install Dependencies

> It is recommended to create a dedicated virtual environment.

```bash
pip install -r requirements.txt   # Python dependencies (including dev dependencies)
npm install                        # Node.js dev tools (for format checking)
```

### Environment Variables (Optional)

```bash
cp .env.example .env   # Modify the configuration as needed
```

---

## Development Workflow

The standard development workflow is as follows:

```bash
# 1. Write code (in src/ or tests/)

# 2. Auto-format
npm run format:fix

# 3. Run tests and check coverage
npm run test

# 4. Full pre-commit check (format fix -> test -> format check)
npm run ci
```

### NPM Script Quick Reference

| Command                | Description                                                          |
| :--------------------- | :------------------------------------------------------------------- |
| `npm run format:fix`   | Auto-fix all formatting issues (Python + Markdown + fullwidth chars) |
| `npm run format:check` | Check all formatting issues                                          |
| `npm run test`         | Run pytest with coverage report                                      |
| `npm run ci`           | Full CI pipeline: format fix -> test -> format check                 |

#### Running the Application

```bash
python main.py           # Launch with folder selection dialog
python main.py -p /path  # Launch with specified workspace path
```

#### Running the Application (After Packaging)

```bash
manualaid           # Launch with folder selection dialog
manualaid -p /path  # Launch with specified workspace path
```

---

## Code Style Standards

The project uses the following tools to ensure code style consistency:

### Ruff (Python Linting)

Configuration file: `ruff.toml`. Enabled rule sets: E, W, F, I, UP, B, SIM, RUF.

```bash
npm run ruff:format:check   # Check
npm run ruff:format:fix     # Fix (Ruff format)
```

### Prettier (Code Formatting)

Configuration file: `.prettierrc.yml`. Rules: printWidth 80, no semicolons,
single quotes.

```bash
npm run prettier:format:check   # Check
npm run prettier:format:fix     # Fix
```

### Markdown Lint (Markdown Syntax Check)

Configuration file: `.markdownlint.yml`. Key rules: MD004 use dashes, MD013 line
length 120.

```bash
npm run md:format:check   # Check
npm run md:format:fix     # Fix
```

For Chinese Markdown files, use `<!-- markdownlint-disable-file MD060 -->` below
the file title to ignore MD060 issues (while keeping table pipe `|` basically
aligned).

### Fullwidth Character Check

**`.py` and `.md` files must only use halfwidth punctuation**
(RUF001/RUF002/RUF003).

```bash
npm run fw:format:check   # Check
npm run fw:format:fix     # Fix (uses scripts/fix_fullwidth.py)
```

### Other Standards

- **Line length**: 120-character limit (Black configuration in `pyproject.toml`)
- **Import sorting**: Isort configured with `known-first-party = ["src"]` (see
  `ruff.toml`)

---

## Commit Convention

This project follows the **Conventional Commits** specification, with the
structure:

```txt
<type>(<scope>): <zh_desc> / <en_desc>
```

### Type

| Type       | Meaning       | Typical Scenario                                                                   |
| :--------- | :------------ | :--------------------------------------------------------------------------------- |
| `feat`     | New feature   | Adding features, tools, UI components, etc.                                        |
| `fix`      | Bug fix       | Fixing code logic errors, exception handling, config inconsistencies, etc.         |
| `refactor` | Code refactor | Code optimization and structural reorganization without changing external behavior |
| `chore`    | Miscellaneous | Dependency updates, version upgrades, cleaning up unused files                     |
| `docs`     | Documentation | Modifying comments, README, API docs, etc.                                         |
| `ci`       | CI/CD         | Modifying GitHub Actions, CI pipeline configuration                                |
| `test`     | Tests         | Adding or modifying test cases                                                     |

### Scope

| Scope       | Related Modules                                                              |
| :---------- | :--------------------------------------------------------------------------- |
| `console`   | Console interface, TUI layout, log output (`src/console/...`)                |
| `core`      | Core logic, input parsing, tool registration mechanism (`src/core/...`)      |
| `workspace` | Workspace operations, file I/O, path validation (`src/workspace/...`)        |
| `tools`     | Specific tool implementations (`read_tool`, `write_tool`, `edit_tool`, etc.) |
| `ui`        | UI component styles, layout (`src/console/ui/...`)                           |
| `models`    | Data models (`src/models/...`)                                               |
| `tests`     | Unit tests (`tests/...`)                                                     |

### Description (Subject)

- **Must include Chinese**, in the format `<Chinese>`. Optional bilingual
  format: `<Chinese> / <English>`.
- Use the imperative mood, capitalize the first letter of the English part, and
  do not end with a period.
- Breaking changes must be explicitly declared.
- Chinese is not strictly required for merge commits (e.g.,
  `Merge ... from branch ...`).

### Examples

```bash
# New feature
feat(console): new session statistics panel

# Bug fix
fix(tools): fix empty record exception in get_avg_consume

# Refactor
refactor(core): simplify input parser ID generation logic

# Documentation
docs(README): add contributing guide
```

---

## Project Architecture Overview

### Core Concepts

- **ToolRegistry**: Singleton pattern, manages registration and execution of all
  tools. Tools are invoked via `tool_registry.execute(name, **kwargs)`.
- **Workspace**: Singleton implemented per workspace path, provides file
  operations and security boundaries. All path operations are validated through
  `PathValidator`.
- **BaseTool**: Base class for all tools, defining tool name, documentation,
  permissions (read_permission / write_permission), and common methods.
- **Path Security**: `PathValidator` prevents path traversal attacks, ensuring
  all file operations are restricted within the workspace root directory.
- **Two-Phase Commit**: Write/edit operations first generate a diff preview and
  record a `PENDING_AUDIT` snapshot; actual disk writes only occur after manual
  review and approval.

---

## How to Add a New Tool

All tools are located in the `src/workspace/tools/` directory and inherit from
the `BaseTool` base class.

### Step Overview

1. **Create the tool file**: Create `your_tool.py` under `src/workspace/tools/`.

2. **Inherit from BaseTool**:

   ```python
   from src.workspace.tools.base_tool import BaseTool
   from src.workspace.workspace import Workspace

   class YourTool(BaseTool):
       def __init__(self, workspace: Workspace):
           super().__init__(
               workspace,
               name="your_tool_name",       # Tool name (unique)
               doc=self.your_method.__doc__, # Reference the method's docstring
               read_permission=True,         # Whether read permission is needed
               write_permission=False,       # Whether write permission is needed
           )
           self.func = self.your_method
           self.params = BaseTool.extract_params(self.your_method)

       @BaseTool.handle_tool_exceptions
       def your_method(self, param1: str, param2: int = 0) -> str:
           """
           Tool description -- will be generated as LLM-readable documentation.

           Parameters
           ----------
           param1: Parameter description
           param2: Parameter description (with default value)
           """
           # Path operations must be validated through PathValidator
           path = self.workspace.path_validator.validate(param1)
           # ... tool logic ...
           return f'{path}x{param2}'
   ```

3. **Special handling for write operations**: If the tool involves writing
   (`write_permission=True`), you need to:
   - Check if the file has been externally modified via
     `self._validate_mtime(path)`
   - Generate a diff and record a `PENDING_AUDIT` snapshot instead of writing
     directly to disk
   - Refer to the implementations of `WriteTool` and `EditTool`

4. **Register the tool**: Import and instantiate your tool in the `register()`
   method of `src/core/tool_registry.py`:

5. **Add tests**: Create corresponding test files under
   `tests/workspace/tools/`. At minimum, cover:
   - Normal execution paths
   - Parameter validation (e.g., empty parameters, invalid values)
   - Path security (e.g., out-of-bounds access)

---

## Testing Requirements

- Test files are located in the `tests/` directory, with a structure
  corresponding to `src/`.
- Pytest is configured with `pythonpath = ["."]`, allowing direct import of the
  `src` package.
- Coverage configuration: `--cov=src --cov-report=term-missing`.
- **New features require tests** -- at minimum, cover core paths and edge cases.

The project is currently in early development; 100% coverage is not strictly
required, but gradual improvement is encouraged.

### Running Tests

```bash
npm run test                        # All tests + coverage report
pytest tests/path/to/test_file.py -v  # Run a single test file
```

---

## License

ManualAid is licensed under the [AGPL-3.0](LICENSE) license. Contributing code
means you agree to release your code under this license.
