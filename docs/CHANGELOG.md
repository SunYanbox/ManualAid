# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.3.0]: https://github.com/SunYanbox/ManualAid/releases/tag/v0.3.0
[0.2.0]: https://github.com/SunYanbox/ManualAid/releases/tag/v0.2.0
