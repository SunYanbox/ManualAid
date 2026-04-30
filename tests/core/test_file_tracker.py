import hashlib
from pathlib import Path

from src.core.file_tracker import FileTracker


class TestComputeChecksum:
    def test_existing_file(self, tmp_path: Path):
        file = tmp_path / "test.txt"
        content = "hello world"
        file.write_text(content, encoding="utf-8")

        result = FileTracker.compute_checksum(file)
        expected = hashlib.blake2b(content.encode("utf-8")).hexdigest()
        assert result == expected

    def test_empty_file(self, tmp_path: Path):
        file = tmp_path / "empty.txt"
        file.write_text("", encoding="utf-8")

        result = FileTracker.compute_checksum(file)
        expected = hashlib.blake2b(b"").hexdigest()
        assert result == expected

    def test_missing_file(self, tmp_path: Path):
        file = tmp_path / "nonexistent.txt"

        result = FileTracker.compute_checksum(file)
        assert result == ""

    def test_binary_file(self, tmp_path: Path):
        file = tmp_path / "binary.bin"
        content = b"\x00\x01\x02\xff"
        file.write_bytes(content)

        result = FileTracker.compute_checksum(file)
        expected = hashlib.blake2b(content).hexdigest()
        assert result == expected


class TestComputeChecksumFromString:
    def test_known_content(self):
        content = "test content"
        result = FileTracker.compute_checksum_from_string(content)
        expected = hashlib.blake2b(content.encode("utf-8")).hexdigest()
        assert result == expected

    def test_empty_string(self):
        result = FileTracker.compute_checksum_from_string("")
        expected = hashlib.blake2b(b"").hexdigest()
        assert result == expected

    def test_deterministic(self):
        content = "deterministic test"
        result1 = FileTracker.compute_checksum_from_string(content)
        result2 = FileTracker.compute_checksum_from_string(content)
        assert result1 == result2


class TestGetFileMeta:
    def test_existing_file(self, tmp_path: Path):
        file = tmp_path / "meta.txt"
        content = "metadata test"
        file.write_text(content, encoding="utf-8")

        meta = FileTracker.get_file_meta(file)

        assert "mtime" in meta
        assert "size" in meta
        assert "checksum" in meta
        assert meta["size"] == len(content.encode("utf-8"))
        assert meta["checksum"] == hashlib.blake2b(content.encode("utf-8")).hexdigest()
        assert isinstance(meta["mtime"], float)
        assert meta["mtime"] > 0

    def test_missing_file(self, tmp_path: Path):
        file = tmp_path / "nonexistent.txt"

        meta = FileTracker.get_file_meta(file)

        assert meta == {}

    def test_checksum_matches_compute_checksum(self, tmp_path: Path):
        file = tmp_path / "consistency.txt"
        file.write_text("consistency check", encoding="utf-8")

        meta = FileTracker.get_file_meta(file)
        direct = FileTracker.compute_checksum(file)

        assert meta["checksum"] == direct
