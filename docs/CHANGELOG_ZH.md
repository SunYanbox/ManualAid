# 更新日志 (Changelog)

本项目的所有重大变更都将记录在此文件中.

本项目的格式遵循
[Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/). 并采用
[语义化版本](https://semver.org/lang/Chinese/).

## [0.3.0] - 2026-05-01

### 新增 (Added)

- **CI/CD**: GitHub Actions 现已支持在 `develop` 分支上触发工作流程,包括 `push`
  和 `pull_request`
  事件 ([#66, #67](https://github.com/SunYanbox/ManualAid/issues/66)).

### 更改 (Changed)

- **Python 版本**: 将目标 Python 版本从 3.12 升级到 **3.14**,涵盖
  `pyproject.toml`、`ruff.toml` 和 GitHub
  Actions 工作流 ([#65](https://github.com/SunYanbox/ManualAid/issues/65)).
- **类型注解**: 迁移到原生 Python 3.10+ 语法(例如
  `ClassName | None`、`warnings.deprecated`),移除了 `typing_extensions` 依赖.
- **异常处理**: 使用 `BaseTool` 中的新 `handle_tool_exceptions`
  装饰器统一了所有工具的异常处理.移除了重复的四步错误处理块 ([#54, #58, #76](https://github.com/SunYanbox/ManualAid/issues/54)).
- **消除代码重复**:
  - 将 `_validate_mtime` 和 `_generate_diff` 方法从 `EditTool` 和 `WriteTool`
    移至 `BaseTool`
    ([#54, #58, #76](https://github.com/SunYanbox/ManualAid/issues/54)).
  - 将 `_record_read_meta` 逻辑整合到 `BaseTool` 中,消除了 `read_tool.py` 和
    `read_lines_tool.py`
    中的重复代码 ([#57, #75](https://github.com/SunYanbox/ManualAid/issues/57)).
- **路径验证**: 移除了 `stat_tool`、`regex_search_tool` 和 `exact_search_tool`
  中冗余的显式路径存在性检查 (`exists()`).依靠 `path_validator.validate()`
  自动抛出异常 ([#60, #71](https://github.com/SunYanbox/ManualAid/issues/60)).
- **结果收集**: 通过利用 `defaultdict(list)` 的行为简化了 `add`
  方法,无需显式的键存在性检查 ([#71](https://github.com/SunYanbox/ManualAid/issues/71)).
- **文档**: 统一了 docstring 标点符号,全文档使用英文句点 ([#76](https://github.com/SunYanbox/ManualAid/issues/76)).
- **导入清理**: 从各个工具模块中清理了未使用的导入 (`PathNotFoundError`,
  `WorkspaceBoundaryError`, `ToolErrorResponse`)
  ([#76](https://github.com/SunYanbox/ManualAid/issues/76)).

### 修复 (Fixed)

- **XML 格式**:
  - 修复了 `tool_handler.py` 中不匹配的 XML 闭合标签 (`<ErrorExecute>` vs
    `/<ErrorExecute>`)
    ([#59, #69](https://github.com/SunYanbox/ManualAid/issues/59)).
  - 更正了 `base_tool.py` 中 `to_doc` 方法,使用动态的 `</func_name>`
    代替硬编码的 `</tool>`
    ([#68, #62](https://github.com/SunYanbox/ManualAid/issues/68)).
- **包识别**: 将 `src/models/tools/` 中的 `___init__.py` 重命名为
  `__init__.py`,以修复模块加载失败的问题 ([#55, #74](https://github.com/SunYanbox/ManualAid/issues/55)).
- **变量命名**: 修正了控制台处理器中的拼写错误,将 `paste_refence` 改为
  `paste_reference`
  ([#56, #73](https://github.com/SunYanbox/ManualAid/issues/56)).
- **空记录**: 在 `get_avg_consume` 中添加了空值检查,当没有记录时返回
  `0.0`,防止异常发生 ([#70, #72](https://github.com/SunYanbox/ManualAid/issues/70)).
- **异常语法**: 更新了异常处理以符合 PEP 654(逗号分隔的元组),涉及
  `file_tracker.py`、`stat_tool.py`、 `regex_search_tool.py` 和
  `exact_search_tool.py`
  ([#65](https://github.com/SunYanbox/ManualAid/issues/65)).

### 测试 (Testing)

- 更新了 `test_base_tool.py` 中的断言,以匹配 `to_doc`
  方法中更正后的 XML 标签结构 ([#68](https://github.com/SunYanbox/ManualAid/issues/68)).

---

## [0.2.0] - 之前的版本

_初始发布的功能和历史记录._

[0.3.0]: https://github.com/SunYanbox/ManualAid/releases/tag/v0.3.0
[0.2.0]: https://github.com/SunYanbox/ManualAid/releases/tag/v0.2.0
