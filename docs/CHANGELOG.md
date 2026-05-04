<!-- markdownlint-disable MD024 -->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.4.1]: https://github.com/SunYanbox/ManualAid/releases/tag/v0.4.1
[0.4.0]: https://github.com/SunYanbox/ManualAid/releases/tag/v0.4.0
[0.3.0]: https://github.com/SunYanbox/ManualAid/releases/tag/v0.3.0
[0.2.0]: https://github.com/SunYanbox/ManualAid/releases/tag/v0.2.0
