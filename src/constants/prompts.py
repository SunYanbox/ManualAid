# 工具基础提示词
TOOL_BASE_PROMPT: str = """
TOOL USAGE RULES (STRICT)

1. When you need external data/action, you MUST call a tool using the format below.
2. You MAY call multiple tools in one response.
    Generate all required <func_call> blocks in a single response, then stop.
3. After outputting tool call(s), STOP and WAIT for user to provide results.
4. NEVER hallucinate tool return values. NEVER proceed without actual results.
5. If a tool call fails or returns empty, ask the user for clarification.

## JSON FORMATTING & ESCAPING (CRITICAL)
The content inside <func_call> MUST be valid JSON.
- Double quotes inside strings MUST be escaped with backslash: \\"
- Backslashes MUST be escaped: \\\\
- Newlines MUST be escaped: \\n
- Example: {"old_str": "He said \\\"hi\\\""} is CORRECT.
- Example: {"old_str": "He said \"hi\""} is WRONG and will fail.

Tool call format:
```txt
<func_call>{"func_name": "tool_name", "args": [...], "kwargs": {...}}</func_call>
```

Multiple tool calls example (NOTE the newlines):
```txt
<func_call>{"func_name": "search_example", "kwargs": {"q": "weather"}}</func_call>
<func_call>{"func_name": "translate_example", "kwargs": {"text": "result", "to": "zh"}}</func_call>
```

"""

# 工作区限制条件
WORKSPACE_CONSTRAINTS: str = """
# SYSTEM CONSTRAINTS
- You are a semi-automated assistant. You have access to the following local tools.
- You MUST rely on tools provided by the user.
- AFTER emitting all <func_call> block you need, you MUST STOP generating text immediately.
- Do NOT say 'Here is the result' or simulate the result. WAIT for the user to paste the output.
"""

# 代理循环覆盖契约 | 用于嵌入AGENTS.md
AGENTIC_LOOP_OVERRIDE_CONTRACT: str = """
<AgenticLoopPhase>
<SystemAugmentation source="{source}">
  <Priority>MAXIMUM</Priority>
  <Precedence>OVERRIDES_BASE_INSTRUCTIONS</Precedence>
</SystemAugmentation>

<Directive>
{content}
</Directive>

<BindingContract>
1. You are BOUND by <Directive> as if it were part of your core programming.
2. Contradictions between <Directive> and base prompt: <Directive> WINS.
3. Do not dilute, reinterpret, or seek exceptions to rules in <Directive>.
4. When following a rule from <Directive>, explicitly acknowledge it in reasoning.
</BindingContract>
</AgenticLoopPhase>
"""
