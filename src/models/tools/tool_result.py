import json
import os
import warnings
from typing import Any, ClassVar

from src.utils.string_snapshot import truncate_params_string


def to_xml_string(func_name: str, params: dict, data: Any = None, err: str | None = None) -> str:
    params = params.copy()
    params.pop("self", None)

    try:
        messages: list[str] = []
        if data is not None:
            messages.append("<result_response>")
            if isinstance(data, str):
                messages.append(data)
            elif isinstance(data, (dict, list, tuple)):
                messages.append(json.dumps(data))
            else:
                messages.append(f"<not_support_type>{data.__class__.__name__}({data})</not_support_type>")
            messages.append("</result_response>")
        if err:
            messages.extend(
                [
                    "<error_response>",
                    err,
                    "</error_response>",
                ]
            )
        if data is None and not err:
            messages.append("没有任何工具调用数据或错误详情, 请提示用户检查工具是否正常")

        temp_result = [
            "",
            f"<func_result name={func_name} parms={truncate_params_string(str(params))}>",
            *messages,
            "</func_result>",
            "",
        ]
        func_result = str.join("\n", temp_result)
    except Exception as e:
        import traceback

        func_result = "\n".join(
            [
                "",
                f"<ErrorExecute name={func_name} parms={truncate_params_string(str(params))}>",
                f"Error={e.__class__.__name__}({e}, {traceback.format_exc()})",
                err if err else "",
                "</ErrorExecute>",
                "",
            ]
        )
    return func_result


class ToolResult:
    """工具执行结果的结构化包装,显式区分成功与失败.

    所有被 @handle_tool_exceptions 装饰的工具方法均返回此类型,
    调用方可通过 success 标志可靠判断执行状态,无需依赖隐式类型约定.
    """

    __slots__ = ("data", "error", "func_kwargs", "func_name", "response", "success")

    HAD_VALIDATE: ClassVar[bool] = False
    MAX_RESULT_LENGTH: ClassVar[int] = int(os.getenv("TOOL_MAX_RESULT_LENGTH", "30000"))
    LIST_TRUNCATE_THRESHOLD: ClassVar[int] = int(os.getenv("TOOL_LIST_TRUNCATE_THRESHOLD", "100"))
    DICT_TRUNCATE_THRESHOLD: ClassVar[int] = int(os.getenv("TOOL_DICT_TRUNCATE_THRESHOLD", "100"))

    def __init__(
        self, success: bool, func_name: str, func_kwargs: dict, data: Any = None, error: str | None = None
    ) -> None:
        self.success: bool = success
        self.func_name: str = func_name
        self.func_kwargs: dict = func_kwargs
        self.data: Any = data
        self.error: str | None = error
        self.response: str = to_xml_string(self.func_name, self.func_kwargs, self.data, self.error)
        ToolResult._validate_config()

    def __repr__(self) -> str:
        if self.success:
            return f"ToolResult(success=True, data={self.data!r})"
        return f"ToolResult(success=False, error={self.error!r})"

    @property
    def status(self) -> str:
        return "success" if self.success else "error"

    @classmethod
    def _compress_result(cls, result: Any) -> Any:
        """压缩过长的结果"""
        result_length = len(result)
        if isinstance(result, str):
            if result_length > cls.MAX_RESULT_LENGTH:
                return (
                    result[: cls.MAX_RESULT_LENGTH]
                    + f"... [字符串结果已截断 显示的字符数: {cls.LIST_TRUNCATE_THRESHOLD} / {result_length}]"
                )
        elif isinstance(result, (list, tuple)):
            if result_length > cls.LIST_TRUNCATE_THRESHOLD:
                return [
                    *list(result[: cls.LIST_TRUNCATE_THRESHOLD]),
                    f"... [列表已截断 显示的项: {cls.LIST_TRUNCATE_THRESHOLD} / {result_length}]",
                ]
        elif isinstance(result, dict) and result_length > cls.DICT_TRUNCATE_THRESHOLD:
            compressed = {k: result[k] for k in list(result.keys())[: cls.DICT_TRUNCATE_THRESHOLD]}
            compressed["..."] = f"[字典已截断 显示的项: {cls.DICT_TRUNCATE_THRESHOLD} / {result_length}]"
            return compressed

        return result

    @classmethod
    def _validate_config(cls) -> None:
        """验证配置值确保在合理范围内"""
        if cls.HAD_VALIDATE:
            return None
        if cls.MAX_RESULT_LENGTH < 10:
            warnings.warn(
                f"TOOL_MAX_RESULT_LENGTH 过小({cls.MAX_RESULT_LENGTH}),建议至少为100", UserWarning, stacklevel=2
            )
            cls.MAX_RESULT_LENGTH = 100

        if cls.LIST_TRUNCATE_THRESHOLD < 10:
            warnings.warn(
                f"TOOL_LIST_TRUNCATE_THRESHOLD 过小({cls.LIST_TRUNCATE_THRESHOLD}),建议至少为50",
                UserWarning,
                stacklevel=2,
            )
            cls.LIST_TRUNCATE_THRESHOLD = 50

        if cls.DICT_TRUNCATE_THRESHOLD < 10:
            warnings.warn(
                f"TOOL_DICT_TRUNCATE_THRESHOLD 过小({cls.DICT_TRUNCATE_THRESHOLD}),建议至少为50",
                UserWarning,
                stacklevel=2,
            )
            cls.DICT_TRUNCATE_THRESHOLD = 50
        cls.HAD_VALIDATE = True
        return None
