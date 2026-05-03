<!-- markdownlint-disable MD024 -->

# 更新日志

本项目的所有重大变更都将记录在此文件中.

本项目的格式遵循
[Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/). 并采用
[语义化版本](https://semver.org/lang/Chinese/).

## [0.4.0] - 2026-05-03

### 新增

- **按会话隔离的文件读取缓存**: 通过 `file_read_records` 表中的 `session_id`
  外键将文件读取记录按会话隔离,防止跨会话数据污染 ([#95, #106](https://github.com/SunYanbox/ManualAid/issues/95)).
- **工具调用摘要表**: 新增 `tool_call_summaries`
  表持久化每个会话的工具调用结果,支持 upsert 语义. 只读工具调用自动记录以便后续检索 ([#97, #107](https://github.com/SunYanbox/ManualAid/issues/97)).
- **会话心跳机制**: 后台守护线程定期持久化会话持续时间,防止异常退出时数据丢失. 通过
  `SESSION_UPDATE_INTERVAL` 环境变量配置(默认 30 秒)
  ([#87, #108](https://github.com/SunYanbox/ManualAid/issues/87)).
- **异步会话删除**: 会话使用 `deleted`
  标志标记,由后台轮询机制执行物理删除, 防止并发访问导致的数据意外丢失. 工作区初始化时自动清理孤立会话 ([#91, #111](https://github.com/SunYanbox/ManualAid/issues/91)).
- **会话列表分页**: 统计标签页现已支持分页会话列表(每页 15 条),包含上一页/下一页导航及每个会话的调用次数显示 ([#92, #112](https://github.com/SunYanbox/ManualAid/issues/92)).
- **总耗时列**: 工具使用排名表现在包含"Total
  Time"列,展示每个工具的累计耗时 ([#86, #114](https://github.com/SunYanbox/ManualAid/issues/86)).
- **版本显示**: 控制台标题栏现已展示应用版本号(格式为 `v{__version__}`)
  ([#90, #115](https://github.com/SunYanbox/ManualAid/issues/90)).

### 更改

- **参数存储迁移**: 工具调用参数现存储为截断后的 JSON
  (`kwargs`)而非 SHA256哈希字符串. `tool_calls` 表的 `args_hash` 列已重命名为
  `kwargs`;旧数据已清空 ([#96, #105](https://github.com/SunYanbox/ManualAid/issues/96)).
- **数据库连接重构**: 用实例级 `_conn` 替换 `threading.local()`,使用
  `check_same_thread=False` 和自动提交模式. 锁从 `threading.Lock` 切换为 `RLock`
  以支持重入安全. 会话删除现使用 `BEGIN IMMEDIATE`
  并在失败时显式回滚 ([#113, #117](https://github.com/SunYanbox/ManualAid/issues/113)).
- **移除已弃用的查看器**: 删除已弃用的 `InteractiveViewer`
  模块及所有相关代码 (`ViewerItem`、全局查看器函数、`MANUALAID_AUTO_VIEW`
  环境变量) ([#82, #121](https://github.com/SunYanbox/ManualAid/issues/82)).
- **心跳配置重命名**: `SESSION_UPDATE_INTERVAL` 环境变量在异步删除系统中重命名为
  `SESSION_FLAG_CHECK_INTERVAL`(默认 5 秒)
  ([#111](https://github.com/SunYanbox/ManualAid/issues/111)).

### 修复

- **XML 标签格式**: 统一 `<func_call>` 标签格式为使用 `name` 属性 (如
  `<func_call name="read">`)而非嵌套的 `<func_name>`
  元素,降低 LLM 幻觉风险 ([#99, #103](https://github.com/SunYanbox/ManualAid/issues/99)).
- **二进制文件检测**: 重写二进制文件检测逻辑,使用扩展名和 MIME 类型替代内容嗅探. 修复了
  `.bat`、`.svg`、`.env`、`.vue`、`.svelte`
  被错误分类为二进制文件的问题 ([#94, #109](https://github.com/SunYanbox/ManualAid/issues/94)).
- **测试资源泄漏**: 通过添加适当的 `close()` 调用和 `reset_instances()`
  清理逻辑,修复了多线程测试中的数据库连接泄漏问题 ([#104, #105](https://github.com/SunYanbox/ManualAid/issues/104)).

### 移除

- `MANUALAID_AUTO_VIEW` 环境变量(随已弃用的交互式查看器一起移除)
  ([#82, #121](https://github.com/SunYanbox/ManualAid/issues/82)).

## [0.3.0] - 2026-05-01

### 新增

- **CI/CD**: GitHub Actions 现已支持在 `develop` 分支上触发工作流程,包括 `push`
  和 `pull_request`
  事件 ([#66, #67](https://github.com/SunYanbox/ManualAid/issues/66)).

### 更改

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

### 修复

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

### 测试

- 更新了 `test_base_tool.py` 中的断言,以匹配 `to_doc`
  方法中更正后的 XML 标签结构 ([#68](https://github.com/SunYanbox/ManualAid/issues/68)).

---

## [0.2.0] - 之前的版本

_初始发布的功能和历史记录._

[0.3.0]: https://github.com/SunYanbox/ManualAid/releases/tag/v0.3.0
[0.2.0]: https://github.com/SunYanbox/ManualAid/releases/tag/v0.2.0
