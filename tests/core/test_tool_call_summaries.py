"""Test tool_call_summaries table functionality."""

import os
import sqlite3
import time

import pytest

from src.core.database_manager import DatabaseManager


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    temp_workspace = tmp_path / "workspace"
    os.makedirs(temp_workspace, exist_ok=True)
    db = DatabaseManager(str(temp_workspace))
    yield db
    db.close()
    DatabaseManager.reset_instances()


class TestToolCallSummariesTable:
    def test_table_exists(self, temp_db):
        cursor = temp_db._get_connection()
        tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tool_call_summaries'").fetchall()
        assert len(tables) == 1
        assert tables[0][0] == "tool_call_summaries"

    def test_primary_key_constraints(self, temp_db):
        session_id = temp_db.create_session()
        kwargs_json = '{"file_path": "test.txt"}'

        # Insert first record
        temp_db.record_tool_call_summary(session_id, "read", kwargs_json, "result1")

        # Insert with same primary key (should update)
        time.sleep(0.01)
        temp_db.record_tool_call_summary(session_id, "read", kwargs_json, "result2")

        # Should only have one record
        summaries = temp_db.get_tool_call_summaries(session_id)
        assert len(summaries) == 1
        assert summaries[0][3] == "result2"  # result updated
        assert summaries[0][4] > time.time() - 1  # timestamp updated

    def test_different_kwargs_create_new_records(self, temp_db):
        session_id = temp_db.create_session()
        kwargs1 = '{"file_path": "test.txt"}'
        kwargs2 = '{"file_path": "other.txt"}'

        temp_db.record_tool_call_summary(session_id, "read", kwargs1, "result1")
        temp_db.record_tool_call_summary(session_id, "read", kwargs2, "result2")

        summaries = temp_db.get_tool_call_summaries(session_id)
        assert len(summaries) == 2

    def test_different_func_names_create_new_records(self, temp_db):
        session_id = temp_db.create_session()
        kwargs_json = '{"query": "test"}'

        temp_db.record_tool_call_summary(session_id, "search", kwargs_json, "result1")
        temp_db.record_tool_call_summary(session_id, "stat", kwargs_json, "result2")

        summaries = temp_db.get_tool_call_summaries(session_id)
        assert len(summaries) == 2

    def test_get_tool_call_summaries_ordered_by_timestamp(self, temp_db):
        session_id = temp_db.create_session()
        kwargs_json = '{"file_path": "test.txt"}'

        time.sleep(0.01)
        temp_db.record_tool_call_summary(session_id, "read", kwargs_json, "result1")
        time.sleep(0.01)
        temp_db.record_tool_call_summary(session_id, "read", kwargs_json, "result2")
        time.sleep(0.01)
        temp_db.record_tool_call_summary(session_id, "read", kwargs_json, "result3")

        summaries = temp_db.get_tool_call_summaries(session_id)
        assert len(summaries) == 1

    def test_get_tool_call_summaries_from_different_sessions(self, temp_db):
        session_id1 = temp_db.create_session()
        session_id2 = temp_db.create_session()
        kwargs_json = '{"file_path": "test.txt"}'

        temp_db.record_tool_call_summary(session_id1, "read", kwargs_json, "result1")
        temp_db.record_tool_call_summary(session_id2, "read", kwargs_json, "result2")

        summaries1 = temp_db.get_tool_call_summaries(session_id1)
        summaries2 = temp_db.get_tool_call_summaries(session_id2)

        assert len(summaries1) == 1
        assert len(summaries2) == 1
        assert summaries1[0][3] != summaries2[0][3]

    def test_session_foreign_key_constraint(self, temp_db):
        kwargs_json = '{"file_path": "test.txt"}'
        # Trying to insert with non-existent session should raise FK constraint error
        # because PRAGMA foreign_keys=ON is enabled
        with pytest.raises(sqlite3.IntegrityError):
            temp_db.record_tool_call_summary(999, "read", kwargs_json, "result1")

        # No record should be inserted
        summaries = temp_db.get_tool_call_summaries(999)
        assert len(summaries) == 0

    def test_index_exists(self, temp_db):
        cursor = temp_db._get_connection()
        indexes = cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_tool_call_summaries_session'").fetchall()
        assert len(indexes) == 1


class TestToolCallSummariesIntegration:
    def test_record_tool_call_summary_stores_correct_data(self, temp_db):
        session_id = temp_db.create_session()
        func_name = "read"
        kwargs_json = '{"file_path": "test.txt"}'
        result = "file content here"

        temp_db.record_tool_call_summary(session_id, func_name, kwargs_json, result)

        summaries = temp_db.get_tool_call_summaries(session_id)
        assert len(summaries) == 1
        assert summaries[0][0] == session_id
        assert summaries[0][1] == func_name
        assert summaries[0][2] == kwargs_json
        assert summaries[0][3] == result
        assert summaries[0][4] > 0  # timestamp

    def test_multiple_sessions_isolated(self, temp_db):
        session_id1 = temp_db.create_session()
        session_id2 = temp_db.create_session()

        kwargs_json = '{"file_path": "test.txt"}'
        result1 = "result for session 1"
        result2 = "result for session 2"

        temp_db.record_tool_call_summary(session_id1, "read", kwargs_json, result1)
        temp_db.record_tool_call_summary(session_id2, "read", kwargs_json, result2)

        summaries1 = temp_db.get_tool_call_summaries(session_id1)
        summaries2 = temp_db.get_tool_call_summaries(session_id2)

        assert summaries1[0][3] == result1
        assert summaries2[0][3] == result2
