# ManualAid

<!-- markdownlint-disable-file MD060 -->

中文 / [English](README.md)

一款**纯本地、需人工介入**的复制粘贴助手,专为 LLM 工作流设计.

ManualAid 提供了一个基于 Textual 的 TUI 控制台,在剪贴板和 LLM 聊天界面之间架起桥梁. 粘贴 LLM 生成的工具调用(XML 格式),审查和审计危险操作,并通过完整的历史追踪管理会话 -- 一切都在本地运行.

> **版本**: 0.2.0 | **Python**: >=3.12

---

## 功能特性

- **TUI 控制台** -- 四个标签页的 Textual 界面:RichLog、工具调用、审计、统计
- **12 个内置工具** -- 文件系统探索、搜索、编辑、Git 集成
- **安全编辑** -- 写入/编辑操作采用两阶段提交,包含 diff 预览和人工审批
- **Git 集成** -- 基于白名单的 Git 命令执行,带有安全过滤
- **会话管理** -- 自动会话追踪,支持重命名、删除和切换
- **工具使用分析** -- 按会话和全局的工具调用统计及排名
- **审计系统** -- 待处理的写入/编辑快照,支持批准/拒绝工作流
- **结果缓存** -- 自动将结果复制到剪贴板,可配置过期时间
- **多窗口启动** -- 为不同工作区生成新的 ManualAid 窗口
- **跨平台** -- 支持 Windows、macOS 和 Linux(后两个没测试)

---

## 快速开始

### 前置条件

- Python >= 3.12
- Node.js(用于开发工具:Prettier、markdownlint)

### 安装

```bash
# 克隆仓库
git clone https://github.com/SunYanbox/ManualAid.git
cd ManualAid

# 创建并激活虚拟环境
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 安装依赖
npm install
pip install -r requirements.txt

# 复制并配置环境变量
cp .env.example .env
```

### 运行

```bash
# 启动时弹出文件夹选择对话框
python main.py

# 直接进入指定工作区
python main.py -p /path/to/your/project
```

运行后,将从 LLM 获取的 XML 格式工具调用粘贴到 REPL 输入区域. 控制台将解析、执行并在相应标签页中显示结果.

---

## 控制台界面

TUI 基于 [Textual](https://textual.textualize.io/) 构建,包含四个标签页:

| 标签页   | 用途                         |
| -------- | ---------------------------- |
| RichLog  | 通用日志输出和消息           |
| 工具调用 | 可折叠的工具执行结果         |
| 审计     | 等待审批的写入/编辑操作      |
| 统计     | 会话摘要、工具排名、会话管理 |

### 键盘快捷键

- `Ctrl+Enter` / `Ctrl+J` -- 提交输入
- `\` + `Enter` -- 在多行输入中插入换行符

### 内置命令

| 命令         | 别名           | 描述                                     |
| ------------ | -------------- | ---------------------------------------- |
| `/quit`      | `/q` / `/exit` | 退出应用程序                             |
| `/tools`     | `/t`           | 列出所有可用工具                         |
| `/tool`      | `/tool_detail` | 按名称显示工具详情                       |
| `/copy`      | `/c`           | 将上次结果复制到剪贴板                   |
| `/history`   |                | 显示工具执行历史                         |
| `/help`      | `/h` / `/?`    | 显示帮助文本                             |
| `/cls`       |                | 清除日志显示                             |
| `/workspace` | `/ws`          | 生成包含工作区信息, 工具定义的系统提示词 |
| `/new`       | `/n`           | 启动新的 ManualAid 窗口                  |

---

## 可用工具

ManualAid 注册了 12 个工具供 LLM 通过 XML 函数调用使用:

### 查询工具(只读)

| 工具           | 描述                                      |
| -------------- | ----------------------------------------- |
| `ls`           | 列出目录内容                              |
| `glob`         | 通过 glob 模式查找文件                    |
| `read`         | 读取文件内容(可选行数限制)                |
| `read_lines`   | 读取文件中指定范围的行                    |
| `stat`         | 获取文件/目录元数据(大小、修改时间、行数) |
| `exact_search` | 精确字符串搜索,支持大小写/全词匹配        |
| `regex_search` | 正则表达式搜索,支持上下文显示             |
| `symbol_ref`   | 查找代码中的符号定义和引用                |

### 编辑工具(需审计审批)

| 工具    | 描述                                |
| ------- | ----------------------------------- |
| `write` | 写入文件内容(文件不存在时创建)      |
| `edit`  | 安全字符串替换,包含 diff 预览和审计 |

### 危险工具(需审计审批)

| 工具  | 描述                      |
| ----- | ------------------------- |
| `git` | 基于白名单的 Git 命令执行 |

> 工具调用使用 XML 格式. 在控制台中使用 `/help` 查看语法示例.

---

## 审计工作流

写入和编辑操作经过两阶段安全流程:

1. **预览** -- 工具计算 diff 并存储状态为 `PENDING_AUDIT` 的快照
2. **审查** -- 切换到审计标签页审查 diff
3. **决定** -- 点击批准提交更改,或点击拒绝放弃更改

不在安全列表(`status`、`diff`、`log`、`show`)中的 Git 命令也需在执行前通过审计审批.

---

## 配置

复制 `.env.example` 为 `.env` 并根据需要调整:

| 变量                           | 默认值 | 描述                   |
| ------------------------------ | ------ | ---------------------- |
| `TOOL_MAX_RESULT_LENGTH`       | 30000  | 工具输出的最大字符数   |
| `TOOL_LIST_TRUNCATE_THRESHOLD` | 100    | 列表结果的最大条目数   |
| `TOOL_DICT_TRUNCATE_THRESHOLD` | 100    | 字典结果的最大键值对数 |
| `MANUALAID_AUTO_COPY`          | true   | 自动将结果复制到剪贴板 |
| `MANUALAID_AUTO_VIEW`          | true   | 自动在查看器中显示结果 |
| `RESULT_EXPIRE_MINUTES`        | 5      | 结果缓存过期时间(分钟) |

---

## 开发

### 环境搭建

```bash
npm install
pip install -r requirements.txt
```

### 代码质量

```bash
npm run format:check   # 检查所有格式(全角字符 + markdown + ruff + prettier)
npm run format:fix     # 自动修复大部分格式问题
npm run test           # 运行测试并生成覆盖率报告
npm run ci             # 完整 CI: 格式修复 -> 测试 -> 格式检查
```

单独检查:

```bash
npm run fw:format:check      # 全角字符检查
npm run md:format:check      # Markdown 检查
npm run ruff:format:check    # Python 代码检查(Ruff)
npm run prettier:format:check# 代码格式化检查(Prettier)
```

### 项目结构

```txt
ManualAid/
  src/
    console/          # Textual TUI 应用
      commands/       # 控制台命令实现
      handlers/       # 工具调用和命令处理
      ui/             # TUI 组件(标签页、REPL、格式化器)
    core/             # 核心逻辑(注册表、数据库、审计、启动器)
    models/           # 数据模型
    constants/        # 提示词、配置
    utils/            # 工具函数
    workspace/        # 工作区和工具实现
  tests/              # 测试套件
  scripts/            # 辅助脚本(如 fix_fullwidth.py)
  docs/               # 文档和提示词模板
```

### 技术栈

- **Python 3.12+** 配合 [Textual](https://textual.textualize.io/) 构建 TUI
- **SQLite3**(WAL 模式)用于会话和工具调用持久化
- **Rich** 用于终端格式化
- **Ruff** 用于 Python 代码检查,**Prettier** + **markdownlint** 用于格式化

### 约束

- `.py` 和 `.md` 文件只能使用半角标点符号
- 行长度限制:120 字符
- 新功能需要补充测试

---

## 法律免责声明

ManualAid 是一款**纯本地、需人工介入的辅助工具**. 它旨在辅助手动复制粘贴工作流,**不支持**与任何 LLM 平台的自动化交互.

**用户须自行负责:**

1. 遵守所使用 LLM 平台的服务条款(ToS).
2. 确保使用方式不违反频率限制、自动化禁令或其他政策.

**ManualAid 的作者明确声明不承担以下责任:**

- 滥用本工具进行自动化请求、绕过付费墙或滥用 LLM 服务.
- 因上述滥用行为导致的任何账户封禁、法律诉讼或损害.

如果您 Fork 本项目,必须保留此免责声明,并确保您的修改不会促进或启用自动化滥用.
