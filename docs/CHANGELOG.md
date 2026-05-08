<!-- markdownlint-disable MD024 -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0] - 2026-05-08

### Added

- **Agent System**: Introduced Agent configuration management with YAML
  frontmatter support for defining system prompts, constraints, and permissions.
  Implemented `AgentManager` singleton pattern supporting Agent loading,
  switching, and persistence
  ([#149](https://github.com/SunYanbox/ManualAid/issues/149)).
- **Skill System**: Added Skill management functionality supporting dynamic
  loading and execution of custom Shell scripts as extension tools. Includes
  `SkillManager`, `skill_tool`, and related TUI configuration interface
  ([#155](https://github.com/SunYanbox/ManualAid/issues/155)).
- **Shell Tool**: New `shell` tool for executing Shell commands with safety
  auditing ([#155](https://github.com/SunYanbox/ManualAid/issues/155)).
- **Path Validation Enhancement**: Introduced `ExclusionManager` class to unify
  performance exclusion (.gitignore rules) and security exclusion (sensitive
  file blocking). Added `SensitiveFileError` exception to directly block access
  to `.env`, `*.pem`, `id_rsa` and other sensitive files
  ([#151](https://github.com/SunYanbox/ManualAid/issues/151)).
- **Gitignore Support**: New `GitignoreLoader` module to parse `.gitignore`
  files and apply exclusion rules to search and file operation tools
  ([#151](https://github.com/SunYanbox/ManualAid/issues/151)).
- **Binary Detection Extension**: Extended binary file detector to support Godot
  project formats (.godot, .gd, .gd.uid, .tscn) and compilation artifacts (.pdb,
  .pyd, .o) ([#151](https://github.com/SunYanbox/ManualAid/issues/154)).
- **Search Tool Binary Filtering**: Integrated binary file detection mechanism
  in `regex_search` and `exact_search` tools to automatically skip binary files
  ([#154](https://github.com/SunYanbox/ManualAid/issues/154)).
- **Agent Command**: New `/agent` command supporting listing agents, switching
  current agent, copying agent configuration, and resetting default agent
  ([#149](https://github.com/SunYanbox/ManualAid/issues/149)).
- **Config Manager**: New `ConfigManager` class for unified environment variable
  configuration management
  ([#155](https://github.com/SunYanbox/ManualAid/issues/155)).
- **Audit Committer**: New `AuditCommitter` class to handle audit system commit
  logic ([#155](https://github.com/SunYanbox/ManualAid/issues/155)).
- **TUI Configuration Tabs**: New environment configuration and skill
  configuration tabs providing graphical configuration interface
  ([#155](https://github.com/SunYanbox/ManualAid/issues/155)).
- **Shell Result Tab**: New shell execution result tab displaying command output
  ([#155](https://github.com/SunYanbox/ManualAid/issues/155)).

### Changed

- **System Prompt Refactor**: Refactored system prompt assembly logic to support
  Agent-based dynamic overrides. Explicitly defined prompt assembly order: Role
  → Constraints → Agent Directive → Tool Rules → Tool Definitions → Workflow →
  Workspace Context → Augmentation → Extensions
  ([#149](https://github.com/SunYanbox/ManualAid/issues/149)).
- **Tool Permission Filtering**: `/ws` command now filters tool definitions
  based on current Agent's tool permission whitelist
  ([#149](https://github.com/SunYanbox/ManualAid/issues/149)).
- **Path Exclusion Logic Refactor**: Removed `PermissionManager` class and
  integrated sensitive file rules into `ExclusionManager`. Simplified search and
  traversal logic with unified `ExclusionManager` for path filtering
  ([#151](https://github.com/SunYanbox/ManualAid/issues/151)).
- **TUI Startup Initialization**: TUI now automatically initializes default
  agent on startup ([#149](https://github.com/SunYanbox/ManualAid/issues/149)).
- **Database Extension**: Extended database manager to support Agent and Skill
  related data persistence
  ([#155](https://github.com/SunYanbox/ManualAid/issues/155)).

### Fixed

- **Git Tool Output Preservation**: Fixed issue where Git commands returning
  non-zero exit code but still producing stdout (e.g., `git diff --exit-code`)
  would discard stdout entirely. Now always preserves stdout even when
  returncode != 0 ([#150](https://github.com/SunYanbox/ManualAid/issues/150)).

## [0.5.0] - 2026-05-05

### Added

- **Structured Tool Result**: Introduced `ToolResult` data class as the unified
  return type for all tools, replacing inconsistent string and list responses.
  The class includes `success`, `data`, `error`, and `response` attributes with
  built-in result compression and standardized XML formatting. All tools now
  return `ToolResult` objects, enabling consistent upstream error handling
  ([#133, #142](https://github.com/SunYanbox/ManualAid/issues/133)).
- **File Pattern Filtering for `exact_search`**: Added `file_pattern` parameter
  to `exact_search` (default `"*"`), matching the existing `regex_search`
  behavior. Allows filtering search scope by file extension or glob pattern
  ([#134, #140](https://github.com/SunYanbox/ManualAid/issues/134)).
- **Auto-Categorization of Tools**: Tools are now automatically classified as
  read-only or write based on the `write_permission` attribute, eliminating
  manual category registration and reducing maintenance overhead
  ([#135, #139](https://github.com/SunYanbox/ManualAid/issues/135)).
- **Range Reading in `read` Tool**: The `read` tool now supports precise line
  range reading via `start`, `end` (supports negative indexing), and `context`
  parameters, replacing the coarse `max_lines` approach. Display header now
  shows the actual line range read (`[Lines start-end / total_lines]`)
  ([#119, #128](https://github.com/SunYanbox/ManualAid/issues/119)).
- **Parameter Descriptions**: Introduced `param_descriptions` dictionary in
  `BaseTool` allowing each tool to provide human-readable parameter
  descriptions. Parameter documentation format changed from inline XML to
  Markdown list items (`- **name** (type, required/optional): description`)
  ([#127, #128](https://github.com/SunYanbox/ManualAid/issues/127)).
- **File Size Limit**: Added configurable max file size limit
  (`MAX_READ_FILE_SIZE`, default 10MB) to the `read` tool to prevent
  out-of-memory errors when reading large files
  ([#130, #141](https://github.com/SunYanbox/ManualAid/issues/130)).

### Changed

- **Tool Path Parameter Unification**: Renamed path parameters across all tools
  to a consistent `path` name — `file_path` (read, write, edit) and
  `folder_path` (ls, glob) are now uniformly `path`. This reduces LLM confusion
  and injection token length
  ([#127, #128](https://github.com/SunYanbox/ManualAid/issues/127)).
- **Tool Injection Optimization**: Removed redundant docstring `Parameters`
  sections from tool functions, shortened tool descriptions, and streamlined
  parameter documentation format. Combined with parameter unification, these
  changes significantly reduce system prompt injection length, lowering LLM
  hallucination risk
  ([#127, #128](https://github.com/SunYanbox/ManualAid/issues/127)).
- **Symbol Search Performance**: Replaced per-pattern file traversal with a
  single-pass multi-pattern search via `search_content_multi_pattern` API,
  eliminating N× I/O overhead. Results are now parsed as structured `list[dict]`
  instead of regex-parsing formatted text, fixing the "format-then-parse"
  anti-pattern
  ([#132, #137](https://github.com/SunYanbox/ManualAid/issues/132)).
- **Exception Handling Consolidation**: The `handle_tool_exceptions` decorator
  now uniformly wraps all exceptions into `ToolResult(success=False, error=...)`
  objects. Removed `ToolErrorResponse` dependency; error messages are now
  formatted as `ClassName: Message`
  ([#133, #142](https://github.com/SunYanbox/ManualAid/issues/133)).

### Fixed

- **`limit` Semantics in Search Tools**: Corrected the `limit` parameter in both
  `exact_search` and `regex_search` to count individual match results rather
  than files scanned, aligning behavior with user expectations
  ([#134, #140](https://github.com/SunYanbox/ManualAid/issues/134)).
- **Redundant Warnings in Input Parser**: Removed stale `warnings.warn` calls
  and the unused `import warnings` dependency from the input parser
  ([#138](https://github.com/SunYanbox/ManualAid/issues/138)).

### Removed

- **`read_lines` Tool**: Merged into the enhanced `read` tool with range-reading
  support. All `read_lines` functionality is now accessible via `read` with
  `start`/`end`/`context` parameters
  ([#119, #128](https://github.com/SunYanbox/ManualAid/issues/119)).

## [0.4.1] - 2026-05-04

### Added

- **Single File Search Support**: Extended search tools (`exact_search`,
  `regex_search`) to handle single file paths directly. The `files_to_search`
  initialization now includes `is_file()` branching with adjusted
  `relative_path` calculation for non-directory scenarios
  ([#110](https://github.com/SunYanbox/ManualAid/issues/110)).

### Fixed

- **Audit Tab MarkupError Crash**: Fixed Rich Markup parsing errors in the audit
  tab caused by unescaped text. Set `markup=False` on `Static` widgets and
  applied `rich.markup.escape()` to dynamically generated log results,
  preventing crashes when rendering approve/reject statuses containing special
  characters ([#124](https://github.com/SunYanbox/ManualAid/issues/124)).
- **Single File Search Failure**: Fixed a bug where `exact_search` and
  `regex_search` tools failed to read content when the search path pointed to a
  single file instead of a directory, due to the recursive glob (`rglob`) not
  handling file paths
  ([#110](https://github.com/SunYanbox/ManualAid/issues/110)).

## [0.4.0] - 2026-05-03

### Added

- **Session-Isolated File Read Cache**: File read records are now scoped by
  session via a `session_id` foreign key in `file_read_records`, preventing
  cross-session data pollution
  ([#95, #106](https://github.com/SunYanbox/ManualAid/issues/95)).
- **Tool Call Summary Table**: New `tool_call_summaries` table persists tool
  call results per session with upsert semantics. Read-only tool calls are
  automatically recorded for later retrieval
  ([#97, #107](https://github.com/SunYanbox/ManualAid/issues/97)).
- **Session Heartbeat**: A background daemon thread periodically persists
  session duration to prevent data loss on abnormal exit. Configurable via
  `SESSION_UPDATE_INTERVAL` env var (default: 30s)
  ([#87, #108](https://github.com/SunYanbox/ManualAid/issues/87)).
- **Async Session Deletion**: Sessions are marked with a `deleted` flag and
  physically removed by a background polling mechanism, preventing accidental
  data loss from concurrent access. Orphaned sessions are auto-cleaned on
  workspace initialization
  ([#91, #111](https://github.com/SunYanbox/ManualAid/issues/91)).
- **Session List Pagination**: The Statistics tab now supports paginated session
  lists (15 per page) with Prev/Next navigation and per-session call count
  display ([#92, #112](https://github.com/SunYanbox/ManualAid/issues/92)).
- **Total Duration Column**: The tool usage ranking table now includes a "Total
  Time" column showing cumulative duration per tool
  ([#86, #114](https://github.com/SunYanbox/ManualAid/issues/86)).
- **Version Display**: The application version is now shown in the console title
  bar (formatted as `v{__version__}`)
  ([#90, #115](https://github.com/SunYanbox/ManualAid/issues/90)).

### Changed

- **Args Storage Migration**: Tool call arguments are now stored as truncated
  JSON (`kwargs`) instead of SHA256 hash strings. The `args_hash` column in
  `tool_calls` has been renamed to `kwargs`; old data is dropped
  ([#96, #105](https://github.com/SunYanbox/ManualAid/issues/96)).
- **Database Connection Refactor**: Replaced `threading.local()` with
  instance-level `_conn` using `check_same_thread=False` and autocommit mode.
  Switched from `threading.Lock` to `RLock` for reentrant safety. Session
  deletion now uses `BEGIN IMMEDIATE` with explicit rollback on failure
  ([#113, #117](https://github.com/SunYanbox/ManualAid/issues/113)).
- **Deprecated Viewer Removal**: Removed the deprecated `InteractiveViewer`
  module and all related code (`ViewerItem`, global viewer functions,
  `MANUALAID_AUTO_VIEW` env var)
  ([#82, #121](https://github.com/SunYanbox/ManualAid/issues/82)).
- **Heartbeat Config Rename**: `SESSION_UPDATE_INTERVAL` env var renamed to
  `SESSION_FLAG_CHECK_INTERVAL` (default: 5s) in the async deletion system
  ([#111](https://github.com/SunYanbox/ManualAid/issues/111)).

### Fixed

- **XML Tag Format**: Unified `<func_call>` tag format to use `name` attribute
  (e.g. `<func_call name="read">`) instead of nested `<func_name>` elements,
  reducing LLM hallucination risk
  ([#99, #103](https://github.com/SunYanbox/ManualAid/issues/99)).
- **Binary Detection**: Rewrote binary file detection to use extension and MIME
  type instead of content sniffing. Fixed `.bat`, `.svg`, `.env`, `.vue`,
  `.svelte` being incorrectly classified as binary
  ([#94, #109](https://github.com/SunYanbox/ManualAid/issues/94)).
- **Test Resource Leaks**: Fixed database connection leaks in multi-threaded
  tests by adding proper `close()` calls and `reset_instances()` cleanup
  ([#104, #105](https://github.com/SunYanbox/ManualAid/issues/104)).

### Removed

- `MANUALAID_AUTO_VIEW` environment variable (along with the deprecated
  interactive viewer)
  ([#82, #121](https://github.com/SunYanbox/ManualAid/issues/82)).

## [0.3.0] - 2026-05-01

### Added

- **CI/CD**: GitHub Actions now supports triggering workflows on the `develop`
  branch for both `push` and `pull_request` events
  ([#66, #67](https://github.com/SunYanbox/ManualAid/issues/66)).

### Changed

- **Python Version**: Upgraded target Python version from 3.12 to **3.14**
  across `pyproject.toml`, `ruff.toml`, and GitHub Actions workflows
  ([#65](https://github.com/SunYanbox/ManualAid/issues/65)).
- **Type Annotations**: Migrated to native Python 3.10+ syntax (e.g.,
  `ClassName | None`, `warnings.deprecated`) and removed `typing_extensions`
  dependency.
- **Exception Handling**: Standardized exception handling across all tools using
  the new `handle_tool_exceptions` decorator in `BaseTool`. Removed repetitive
  four-step error handling blocks
  ([#54, #58, #76](https://github.com/SunYanbox/ManualAid/issues/54)).
- **Code Deduplication**:
  - Moved `_validate_mtime` and `_generate_diff` methods from `EditTool` and
    `WriteTool` to `BaseTool`
    ([#54, #58, #76](https://github.com/SunYanbox/ManualAid/issues/54)).
  - Consolidated `_record_read_meta` logic into `BaseTool` to eliminate
    duplication in `read_tool.py` and `read_lines_tool.py`
    ([#57, #75](https://github.com/SunYanbox/ManualAid/issues/57)).
- **Path Validation**: Removed redundant explicit path existence checks
  (`exists()`) in `stat_tool`, `regex_search_tool`, and `exact_search_tool`.
  Relied on `path_validator.validate()` to raise exceptions automatically
  ([#60, #71](https://github.com/SunYanbox/ManualAid/issues/60)).
- **Result Collection**: Simplified `add` method by leveraging
  `defaultdict(list)` behavior instead of explicit key existence checks
  ([#71](https://github.com/SunYanbox/ManualAid/issues/71)).
- **Documentation**: Standardized docstring punctuation to use English periods
  throughout ([#76](https://github.com/SunYanbox/ManualAid/issues/76)).
- **Imports**: Cleaned up unused imports (`PathNotFoundError`,
  `WorkspaceBoundaryError`, `ToolErrorResponse`) from various tool modules
  ([#76](https://github.com/SunYanbox/ManualAid/issues/76)).

### Fixed

- **XML Formatting**:
  - Fixed mismatched XML closing tags in `tool_handler.py` (`<ErrorExecute>` vs
    `/<ErrorExecute>`)
    ([#59, #69](https://github.com/SunYanbox/ManualAid/issues/59)).
  - Corrected `to_doc` method in `base_tool.py` to use dynamic `</func_name>`
    instead of hardcoded `</tool>`
    ([#68, #62](https://github.com/SunYanbox/ManualAid/issues/68)).
- **Package Identification**: Renamed `___init__.py` to `__init__.py` in
  `src/models/tools/` to fix module loading failures
  ([#55, #74](https://github.com/SunYanbox/ManualAid/issues/55)).
- **Variable Naming**: Corrected typo `paste_refence` to `paste_reference` in
  console handlers
  ([#56, #73](https://github.com/SunYanbox/ManualAid/issues/56)).
- **Empty Records**: Added null check in `get_avg_consume` to return `0.0` when
  no records exist, preventing exceptions
  ([#70, #72](https://github.com/SunYanbox/ManualAid/issues/70)).
- **Exception Syntax**: Updated exception handling to comply with PEP 654.
  Files: `file_tracker.py`, `stat_tool.py`, `regex_search_tool.py`,
  `exact_search_tool.py`. See
  [#65](https://github.com/SunYanbox/ManualAid/issues/65).

### Testing

- Updated `test_base_tool.py` assertions to match the corrected XML tag
  structure in `to_doc` method
  ([#68](https://github.com/SunYanbox/ManualAid/issues/68)).

---

## [0.2.0] - Previous Release

_Initial release features and history._

[0.6.0]: https://github.com/SunYanbox/ManualAid/releases/tag/v0.6.0
[0.5.0]: https://github.com/SunYanbox/ManualAid/releases/tag/v0.5.0
[0.4.1]: https://github.com/SunYanbox/ManualAid/releases/tag/v0.4.1
[0.4.0]: https://github.com/SunYanbox/ManualAid/releases/tag/v0.4.0
[0.3.0]: https://github.com/SunYanbox/ManualAid/releases/tag/v0.3.0
[0.2.0]: https://github.com/SunYanbox/ManualAid/releases/tag/v0.2.0
