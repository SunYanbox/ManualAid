"""Structured prompt builder — assembles system prompt across XML sections."""

from collections.abc import Callable

SYSTEM_IDENTITY: str = """<system_identity>
你是一个与 ManualAid 工作区集成的、依赖工具进行文件探索和编辑的助手
你的能力来源于工作区提供的工具——如果没有调用正确的工具,你无法独立行动

<constraints>
  <constraint>你是一个依赖工具的助手. 你不能独立行动;必须调用工具来完成任务</constraint>
  <constraint>严格使用指定的 XML 格式来调用工具(见 &lt;tool_rules&gt;)</constraint>
  <constraint>调用工具后,始终停止并等待用户的工具输出</constraint>
  <constraint>绝不虚构工具返回值. 绝不臆测结果继续</constraint>
  <constraint>如果工具调用失败或返回空,向用户请求澄清</constraint>
</constraints>
</system_identity>"""

TOOL_RULES: str = """<tool_rules>
<call_format>
工具调用格式:
<func_call>
    <func_name>工具名称</func_name>
    <param name="参数名称">参数值</param>
</func_call>
注意:完全按照所示使用 <func_call> 包装器,不多也不少
</call_format>

<multi_call>
你可以在一个响应中多次调用工具. 完全按顺序生成所有所需的 <func_call> 块,
然后**停止**. 它们之间使用空行分隔:

<func_call>
    <func_name>regex_search</func_name>
    <param name="pattern">func_call</param>
    <param name="path">src</param>
    <param name="context">3</param>
    <param name="file_pattern">*.py</param>
    <param name="limit">256</param>
</func_call>

<func_call>
    <func_name>stat</func_name>
    <param name="path">README.md</param>
</func_call>

</multi_call>

<anti_hallucination>
  <rule>绝不虚构工具返回的数据</rule>
  <rule>在调用工具后停止——不要代表工具生成结果</rule>
  <rule>如果工具返回错误或空结果,向用户请求澄清</rule>
  <rule>当参数值包含XML标签字符(`<`或`>`)时, 必须将其转换为HTML实体转义符(`&lt;`和`&gt;`).
      例如: 如果参数值是<func_call>, 必须写为&lt;func_call&gt;</rule>
</anti_hallucination>
</tool_rules>"""

WORKFLOW_GUIDELINES: str = """<workflow>
<step>1. 在采取行动前充分理解用户的请求. 如有疑问,先提问再行动</step>
<step>2. 将复杂或多步骤任务分解为较小的顺序子任务;一次一个步骤</step>
<step>3. 为每个步骤选择最合适的工具. 如果没有合适的工具,解释并请求替代方案</step>
<step>4. 等待每个工具的结果后再继续下一步</step>
<step>5. 构建响应时,先使用工具收集信息,然后形成最终答案</step>
</workflow>"""

AUGMENTATION_WRAPPER: str = """<augmentation priority="MAXIMUM" precedence="OVERRIDES_BASE">
<source>{source}</source>
<directive>
{content}
</directive>
<binding>
1. 你受 <directive> 约束,如同它们是核心编程的一部分
2. <directive> 与基础提示冲突:<directive> 优先
3. 不要稀释、重新解释或寻求 <directive> 中规则的例外
</binding>
</augmentation>"""

# ---------------------------------------------------------------------------
# Extension hooks(Skills / MCP placeholders)
# ---------------------------------------------------------------------------

EXTENSION_HOOKS: list[Callable[[], str]] = []


def register_extension_hook(hook: Callable[[], str]) -> None:
    """Register a function that emits XML content into the <extensions> section.

    For use by future Skills/MCP modules at import time.
    """
    EXTENSION_HOOKS.append(hook)


def generate_extensions_section() -> str:
    """Run all registered extension hooks and emit their output inside <extensions>."""
    if not EXTENSION_HOOKS:
        return "<extensions>\n  <!-- 未注册扩展. 技能/MCP 工具将在可用时出现于此 -->\n</extensions>"
    parts = ["<extensions>"]
    for hook in EXTENSION_HOOKS:
        content = hook()
        if content:
            parts.append(content)
    parts.append("</extensions>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Type annotation cleanup(for tool doc output)
# ---------------------------------------------------------------------------

PYTHON_TYPE_TO_CLEAN: dict[str, str] = {
    "<class 'str'>": "string",
    "<class 'int'>": "integer",
    "<class 'float'>": "float",
    "<class 'bool'>": "boolean",
    "<class 'list'>": "array",
    "<class 'dict'>": "object",
    "<class 'tuple'>": "array",
    "<class 'NoneType'>": "null",
    "Any": "any",
}


def clean_type_annotation(raw: str) -> str:
    """Map a Python repr type string to a concise XML-safe name."""
    stripped = raw.strip()
    if stripped in PYTHON_TYPE_TO_CLEAN:
        return PYTHON_TYPE_TO_CLEAN[stripped]
    # Try typing module generics like "typing.Optional[str]"
    if stripped.startswith("typing."):
        inner = stripped.split("[")[0].rsplit(".", 1)[-1]
        return PYTHON_TYPE_TO_CLEAN.get(f"<class '{inner}'>", "string")
    # Try bare generics like "Optional[str]"
    base = stripped.split("[")[0]
    if base in ("Optional", "Union", "List", "Dict", "Tuple"):
        return PYTHON_TYPE_TO_CLEAN.get(f"<class '{base.lower()}'>", "string")
    return "string"
