# noinspection SpellCheckingInspection
def _copy_fallback(text) -> bool:
    """Fallback clipboard copy using system commands"""
    import subprocess
    import sys

    try:
        if sys.platform == "win32":
            # Windows: 使用 clip 命令
            process = subprocess.Popen(["clip"], stdin=subprocess.PIPE, shell=True)
            process.communicate(input=text.encode("utf-8"))
        elif sys.platform == "darwin":
            # macOS: 使用 pbcopy
            process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            process.communicate(input=text.encode("utf-8"))
        else:
            # Linux: 使用 xclip 或 xsel
            process = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
            process.communicate(input=text.encode("utf-8"))
        return True
    except Exception as e:
        print(f"复制过程中出现错误: {e.__class__.__name__}({e})")
        return False


def copy_to_clipboard(text: str) -> bool:
    """将文本复制到剪切板"""
    try:
        import pyperclip

        pyperclip.copy(text)
        return True
    except ImportError:
        # 降级到系统命令
        return _copy_fallback(text)
