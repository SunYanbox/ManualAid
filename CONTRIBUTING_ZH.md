# 贡献指南 (Contributing Guide)

感谢你对 ManualAid 的关注! 本文档将帮助你了解如何参与项目贡献.

在开始之前,请先阅读项目的 [README_ZH.md](README_ZH.md)
和,了解项目的基本信息和技术约束.

---

## 法律声明

ManualAid 是一款**纯本地、需人工介入的辅助工具**. 它设计用于促进手动复制粘贴工作流,**不支持**与大模型平台的自动化交互.

**用户必须自行承担以下责任:**

1. 遵守所使用的大模型平台服务条款 (ToS).
2. 确保使用行为不违反频率限制、自动化禁令或其他政策.

**ManualAid 作者明确不承担以下责任:**

- 滥用本工具进行自动化请求、绕过付费墙或滥用 LLM 服务.
- 因此类滥用导致的任何账户暂停、法律诉讼或损失.

如果你 Fork 本项目,**必须保留此免责声明**,并确保你的修改不会促进或启用自动化滥用.

---

## Issue 与 Pull Request

### Issue

- **标题和内容必须使用中英双语**.
- 清晰描述问题或建议,附带复现步骤(如适用).
- 贡献复杂功能前, 必须创建Issue已明确目标, 避免开发方向与本项目实际方向不同

### Pull Request

- PR 标题使用中英双语,或纯中文皆可.
- 确保本地通过 `npm run ci` 检查.
- 关联相关 Issue(如 `Closes #42`).
- PR的目标分支必须是develop分支

---

## 开发工作流

标准的开发流程如下:

```bash
# 1. 编写代码(在 src/ 或 tests/ 中)

# 2. 自动格式化
npm run format:fix

# 3. 运行测试并查看覆盖率
npm run test

# 4. 提交前完整检查(格式修复 -> 测试 -> 格式检查)
npm run ci
```

---

## 代码风格规范

项目使用以下工具确保代码风格一致:

### Ruff(Python 代码检查)

配置文件: `ruff.toml`. 启用的规则集: E, W, F, I, UP, B, SIM, RUF.

```bash
npm run ruff:format:check   # 检查
npm run ruff:format:fix     # 修复(Ruff format)
```

### Prettier(代码格式化)

配置文件: `.prettierrc.yml`. 规则: printWidth 80, 无分号, 单引号.

```bash
npm run prettier:format:check   # 检查
npm run prettier:format:fix     # 修复
```

### Markdown lint(Markdown 语法检查)

配置文件: `.markdownlint.yml`. 关键规则: MD004 使用短横线, MD013 行长度 120.

```bash
npm run md:format:check   # 检查
npm run md:format:fix     # 修复
```

中文Markdown需要在文件标题下方使用`<!-- markdownlint-disable-file MD060 -->`忽略MD060的问题(仍然保持表格的管道符|基本对齐)

### 全角字符检查

**`.py` 和 `.md` 文件只能使用半角标点符号**(RUF001/RUF002/RUF003).

```bash
npm run fw:format:check   # 检查
npm run fw:format:fix     # 修复(使用 scripts/fix_fullwidth.py)
```

### 其他规范

- **行长度**: 120 字符限制(`pyproject.toml` 中的 Black 配置)
- **导入排序**: Isort 配置了 `known-first-party = ["src"]`(见 `ruff.toml`)

---

## 提交规范

本项目遵循 **Conventional Commits** 规范,结构为:

```txt
<type>(<scope>): <desc>
```

如果使用英文, 则为:

```txt
<type>(<scope>): <zh_desc>(使用AI翻译即可) / <en_desc>
```

### 类型 (Type)

| 类型       | 含义     | 典型场景                                 |
| :--------- | :------- | :--------------------------------------- |
| `feat`     | 新功能   | 新增功能、工具、UI 组件等                |
| `fix`      | 缺陷修复 | 修复代码逻辑错误、异常处理、配置不一致等 |
| `refactor` | 代码重构 | 不改变外部行为的代码优化、结构重组       |
| `chore`    | 杂项     | 依赖更新、版本升级、清理无用文件         |
| `docs`     | 文档     | 修改注释、README、API 文档等             |
| `ci`       | CI/CD    | 修改 GitHub Actions、CI 流程配置         |
| `test`     | 测试     | 添加或修改测试用例                       |

### 作用域 (Scope)

| 作用域      | 涉及模块                                                 |
| :---------- | :------------------------------------------------------- |
| `console`   | 控制台界面、TUI 布局、日志输出 (`src/console/...`)       |
| `core`      | 核心逻辑、输入解析、工具注册机制 (`src/core/...`)        |
| `workspace` | 工作区操作、文件读写、路径验证 (`src/workspace/...`)     |
| `tools`     | 具体工具实现 (`read_tool`, `write_tool`, `edit_tool` 等) |
| `ui`        | 用户界面组件样式、布局 (`src/console/ui/...`)            |
| `models`    | 数据模型 (`src/models/...`)                              |
| `tests`     | 单元测试 (`tests/...`)                                   |

### 描述 (Subject)

- **必须包含中文**, 格式为 `<中文>`. 可选双语格式: `<中文> / <英文>`
- 使用动词原形(祈使语气), 英文部分首字母大写, 结尾不加句号.
- 涉及破坏性变更需显式声明.
- 合并时不强制要求中文(例如`Merge ... from branch ...`)

### 示例

```bash
# 新功能
feat(console): 新增会话统计面板 / add session statistics panel

# 修复 Bug
fix(tools): 修复空记录异常 / fix empty record exception in get_avg_consume

# 重构
refactor(core): 简化输入解析器 ID 生成逻辑 / simplify input parser ID generation

# 文档
docs(README): 添加贡献指南 / add contributing guide
```

---

## 项目架构概览

### 核心概念

- **ToolRegistry**: 单例模式,管理所有工具的注册和执行. 通过
  `tool_registry.execute(name, **kwargs)` 调用工具.
- **Workspace**: 按工作区路径实现的单例,提供文件操作和安全边界. 所有路径操作都经过
  `PathValidator` 验证.
- **BaseTool**: 所有工具的基类,定义工具的名称、文档、权限(read_permission /
  write_permission)以及通用方法.
- **路径安全**: `PathValidator`
  防止路径遍历攻击,确保所有文件操作限制在工作区根目录内.
- **两阶段提交**: 写入/编辑操作首先生成 diff 预览并记录 `PENDING_AUDIT`
  快照,经人工审核批准后才实际写入磁盘.

---

## 如何添加新工具

所有工具位于 `src/workspace/tools/` 目录,继承 `BaseTool`
基类. 所有工具方法必须返回 `ToolResult` 对象(位于
`src/models/tools/tool_result.py`).

### ToolResult 模型

`ToolResult` 是统一的工具执行结果包装器:

| 字段          | 说明                                     |
| :------------ | :--------------------------------------- |
| `success`     | 执行是否成功 (`bool`)                    |
| `func_name`   | 工具方法名 (`str`)                       |
| `func_kwargs` | 调用参数字典 (`dict`)                    |
| `data`        | 成功时的返回数据 (`Any`)                 |
| `error`       | 失败时的错误消息 (`str\|None`)           |
| `response`    | 自动生成的 XML 格式字符串(用于 LLM 消费) |

### 步骤概述

1. **创建工具文件**: 在 `src/workspace/tools/` 下新建 `your_tool.py`.

2. **继承 BaseTool**:

   ```python
   from src.models.tools.tool_result import ToolResult
   from src.workspace.tools.base_tool import BaseTool
   from src.workspace.workspace import Workspace

   class YourTool(BaseTool):
       def __init__(self, workspace: Workspace):
           super().__init__(
               workspace,
               name="your_tool_name",       # 工具名称(唯一)
               doc=self.your_method.__doc__, # 引用方法的 docstring
               read_permission=True,         # 是否需要读权限
               write_permission=False,       # 是否需要写权限
           )
           self.func = self.your_method
           self.params = BaseTool.extract_params(self.your_method)
           self.param_descriptions = {
               "param1": "参数说明",
               "param2": "参数说明"
           }

       @BaseTool.handle_tool_exceptions
       def your_method(self, param1: str, param2: int = 0) -> ToolResult:
           """
           工具描述 -- 会生成为 LLM 可读的文档.
           """
           # 路径操作必须通过 PathValidator 验证
           path = self.workspace.path_validator.validate(param1)

           # 注意: 返回 ToolResult 而非原始数据
           # 成功时使用 make_success_response
           return self.make_success_response(
               kwargs=locals().copy(),
               data=f'{path}x{param2}'
           )

           # 失败时使用 make_failed_response
           # return self.make_failed_response(
           #     kwargs=locals().copy(),
           #     error="具体的错误描述"
           # )
   ```

3. **写入操作的特殊处理**: 如果工具涉及写入(`write_permission=True`),需要:
   - 通过 `self._validate_mtime(path)` 检查文件是否被外部修改
   - 生成 diff 并记录 `PENDING_AUDIT` 快照,而非直接写入磁盘
   - 返回格式仍然使用
     `self.make_success_response(kwargs=locals().copy(), data=...)` 或
     `self.make_failed_response(kwargs=locals().copy(), error=...)`
   - 参考 `WriteTool` 和 `EditTool` 的实现

4. **注册工具**: 在 `src/core/tool_registry.py` 的 `register()`
   方法中导入并实例化你的工具:

   ```python
   def register(self, workspace: Workspace) -> None:
       from src.workspace.tools.your_tool import YourTool

       self._workspace = workspace

       for cls in (
           # ... 其他已有的工具类 ...
           YourTool,
       ):
           try:
               tool = cls(workspace)
               if tool.func is None or tool.params is None:
                   warnings.warn(f"工具{tool.name}没有注册功能回调和参数", stacklevel=2)
                   continue
               self._tools[tool.name] = tool
               self._set_tool_category(tool)
           except ValueError:
               pass
   ```

5. **补充测试**: 在 `tests/workspace/tools/` 下创建对应的测试文件. 至少覆盖:
   - 正常执行路径(断言 `result.success is True`, 检查 `result.data`)
   - 失败场景(断言 `result.success is False`, 检查 `result.error`)
   - 参数验证(如空参数、非法值)
   - 路径安全(如越界访问)

   测试示例:

   ```python
   def test_your_tool_success(workspace):
       tool = YourTool(workspace)
       result = tool.your_method(param1="valid_path", param2=42)
       assert result.success is True
       assert result.data is not None

   def test_your_tool_failure(workspace):
       tool = YourTool(workspace)
       result = tool.your_method(param1="../outside_path", param2=42)
       assert result.success is False
       assert "WorkspaceBoundaryError" in result.error
   ```

---

## 测试要求

- 测试文件位于 `tests/` 目录,结构与 `src/` 对应.
- Pytest 配置了 `pythonpath = ["."]`,可以直接导入 `src` 包.
- 覆盖率配置: `--cov=src --cov-report=term-missing`.
- **新增功能需要补充测试** -- 至少覆盖核心路径和边界情况.

项目目前处于开发早期,覆盖率不强求 100%,但鼓励逐步提升.

### 运行测试

```bash
npm run test                    # 全部测试 + 覆盖率报告
pytest tests/路径/测试文件.py -v  # 运行单个测试文件
```

---

## 许可证

ManualAid 遵循 [AGPL-3.0](LICENSE)
许可证. 贡献代码即表示你同意将代码按此许可证发布.
