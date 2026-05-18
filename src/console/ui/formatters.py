"""Output formatting utilities"""

from src.constants.files import EXTENSION_TO_LANGUAGE
from src.utils.string_snapshot import truncate_params_string, truncate_single_string


class OutputFormatter:
    """Formatter for console output"""

    @staticmethod
    def format_tool_params(args: list, kwargs: dict) -> str:
        """Format tool parameters as concise string

        Args:
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Formatted parameter string
        """
        parts = []

        # Positional arguments
        for arg in args:
            if isinstance(arg, str):
                parts.append(f'"{truncate_single_string(arg)}"')
            else:
                parts.append(str(arg))

        # Keyword arguments
        for key, value in kwargs.items():
            if isinstance(value, str):
                parts.append(f'{key}="{truncate_single_string(value)}"')
            else:
                parts.append(f"{key}={value}")

        if not parts:
            return "no parameters"

        params_str = ", ".join(parts)

        return truncate_params_string(params_str)

    @staticmethod
    def create_result_title(
        index: int,
        func_name: str,
        args: list,
        kwargs: dict,
        lines_count: int,
    ) -> str:
        """Create result title with Rich markup

        Args:
            index: Result index
            func_name: Function name
            args: Positional arguments
            kwargs: Keyword arguments
            lines_count: Number of lines in result

        Returns:
            Rich markup formatted title
        """
        params_str = OutputFormatter.format_tool_params(args, kwargs)
        return f"[bold cyan]##{index}[/bold cyan] [bold green]{func_name}[/bold green]([dim]{params_str}[/dim])" + f" [yellow]({lines_count} lines)[/yellow]"

    @staticmethod
    def detect_language(file_path: str) -> str:
        """Detect programming language from file extension

        Args:
            file_path: Path to file

        Returns:
            Language identifier for syntax highlighting
        """
        ext_map = EXTENSION_TO_LANGUAGE

        for ext, lang in ext_map.items():
            if file_path.lower().endswith(ext):
                return lang

        return "text"

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Format file size in human-readable format

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted size string
        """
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    @staticmethod
    def truncate_string(text: str, max_length: int = 100) -> str:
        """Truncate string to maximum length

        Args:
            text: Input text
            max_length: Maximum length

        Returns:
            Truncated string with ellipsis if needed
        """
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."
