class ToolErrorResponse:
    def __init__(self, tool_name: str, errors: str | Exception):
        self.tool_name = tool_name
        self.errors = errors if isinstance(errors, str) else f"{errors.__class__.__name__}({errors})"

    def to_str(self):
        return str(self)

    def __str__(self):
        return f"<tool_name={self.tool_name}, errors={self.errors} />"
