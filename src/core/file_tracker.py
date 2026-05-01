import hashlib
from pathlib import Path


class FileTracker:
    """Static utility methods for file mtime/checksum tracking."""

    @staticmethod
    def compute_checksum(file_path: Path) -> str:
        """Compute BLAKE2b hex digest of file content. Returns '' on error."""
        try:
            content = file_path.read_bytes()
            return hashlib.blake2b(content).hexdigest()
        except OSError, PermissionError:
            return ""

    @staticmethod
    def compute_checksum_from_string(content: str) -> str:
        """Compute BLAKE2b hex digest of a string."""
        return hashlib.blake2b(content.encode("utf-8")).hexdigest()

    @staticmethod
    def get_file_meta(file_path: Path) -> dict:
        """Return {mtime, size, checksum} for a file, or empty dict on failure."""
        try:
            stat = file_path.stat()
            return {
                "mtime": stat.st_mtime,
                "size": stat.st_size,
                "checksum": FileTracker.compute_checksum(file_path),
            }
        except OSError, PermissionError:
            return {}
