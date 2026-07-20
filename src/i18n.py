"""Internationalization setup using gettext.

Chinese strings are the msgid/keys. Only wrap rendered UI text with _(),
not logs or internal strings.
"""

import gettext
from collections.abc import Callable
from pathlib import Path


def setup_i18n(workspace_root: Path) -> Callable[[str], str]:
    """Setup i18n with Chinese as the default locale.

    Returns the _() function for wrapping user-facing strings.

    Args:
        workspace_root: Path to the workspace root

    Returns:
        The _() function for internationalization
    """
    # Use Chinese as the default locale (msgid = Chinese text)
    # When a .mo file exists for the locale, it will be used
    # Otherwise, the Chinese text is used directly as msgid

    # Try to find locale files (if we add Chinese localization later)
    locale_dir = workspace_root / "locales"

    # Setup gettext with Chinese as the default
    # The Chinese text in our source code IS the msgid
    _translator = gettext.translation(
        "manualaid",
        localedir=str(locale_dir) if locale_dir.exists() else None,
        languages=["zh_CN"],  # Chinese (Simplified)
        fallback=True,  # Fallback to msgid if .mo file not found
    )

    # The _() function is the translation function
    # When no .mo file exists, it returns the original Chinese text
    return _translator.gettext
