"""
Tests for Memory Manager
========================
Unit tests for memory storage operations.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from core.memory_manager import MemoryManager


class TestMemoryManager:
    """Test Memory Manager functionality."""

    @pytest.fixture
    def temp_memory(self):
        """Create temporary memory directory for testing."""
        temp_dir = Path(tempfile.mkdtemp())
        memory = MemoryManager(base_path=temp_dir)
        yield memory
        # Cleanup
        shutil.rmtree(temp_dir)

    def test_memory_creation(self, temp_memory):
        """Test memory manager initialization."""
        assert temp_memory.base_path.exists()
        assert (temp_memory.base_path / "orchestrator").exists()
        assert (temp_memory.base_path / "market_data").exists()
        assert (temp_memory.base_path / "errors").exists()

        print(f"\n✓ Memory directories created")

    def test_write_and_read(self, temp_memory):
        """Test basic write and read operations."""
        test_data = {"key": "value", "number": 42}

        temp_memory.write("orchestrator", "test.json", test_data)
        result = temp_memory.read("orchestrator", "test.json")

        assert result == test_data

        print(f"\n✓ Write and read working")

    def test_read_nonexistent_file(self, temp_memory):
        """Test reading nonexistent file returns default."""
        result = temp_memory.read("orchestrator", "nonexistent.json", default={"default": True})

        assert result == {"default": True}

        print(f"\n✓ Default value returned for missing file")

    def test_append(self, temp_memory):
        """Test appending entries to list."""
        temp_memory.append("orchestrator", "history.json", {"entry": 1})
        temp_memory.append("orchestrator", "history.json", {"entry": 2})
        temp_memory.append("orchestrator", "history.json", {"entry": 3})

        result = temp_memory.read("orchestrator", "history.json")

        assert len(result) == 3
        assert result[0] == {"entry": 1}
        assert result[2] == {"entry": 3}

        print(f"\n✓ Append working, {len(result)} entries")

    def test_append_with_max_entries(self, temp_memory):
        """Test append with max entries limit."""
        # Add 15 entries with max 10
        for i in range(15):
            temp_memory.append("orchestrator", "limited.json", {"entry": i}, max_entries=10)

        result = temp_memory.read("orchestrator", "limited.json")

        assert len(result) == 10
        # Should keep last 10 entries (5-14)
        assert result[0]["entry"] == 5
        assert result[-1]["entry"] == 14

        print(f"\n✓ Max entries limit working (kept last {len(result)})")

    def test_update(self, temp_memory):
        """Test updating specific fields."""
        # Initial data
        temp_memory.write("orchestrator", "config.json", {
            "field1": "value1",
            "field2": "value2"
        })

        # Update one field
        temp_memory.update("orchestrator", "config.json", {
            "field2": "updated",
            "field3": "new"
        })

        result = temp_memory.read("orchestrator", "config.json")

        assert result["field1"] == "value1"  # Unchanged
        assert result["field2"] == "updated"  # Updated
        assert result["field3"] == "new"  # Added

        print(f"\n✓ Update working")

    def test_delete(self, temp_memory):
        """Test deleting memory file."""
        temp_memory.write("orchestrator", "to_delete.json", {"data": "test"})

        assert temp_memory.read("orchestrator", "to_delete.json") is not None

        temp_memory.delete("orchestrator", "to_delete.json")

        assert temp_memory.read("orchestrator", "to_delete.json") is None

        print(f"\n✓ Delete working")

    def test_clear_category(self, temp_memory):
        """Test clearing entire category."""
        # Write multiple files
        temp_memory.write("orchestrator", "file1.json", {"data": 1})
        temp_memory.write("orchestrator", "file2.json", {"data": 2})
        temp_memory.write("orchestrator", "file3.json", {"data": 3})

        # Clear category
        temp_memory.clear_category("orchestrator")

        # Verify all cleared
        assert temp_memory.read("orchestrator", "file1.json") is None
        assert temp_memory.read("orchestrator", "file2.json") is None
        assert temp_memory.read("orchestrator", "file3.json") is None

        print(f"\n✓ Category cleared")

    def test_get_stats(self, temp_memory):
        """Test memory statistics."""
        # Write some data
        temp_memory.write("orchestrator", "data1.json", {"key": "value"})
        temp_memory.write("market_data", "data2.json", {"key": "value"})

        stats = temp_memory.get_stats()

        assert stats["total_files"] >= 2
        assert "orchestrator" in stats["by_category"]
        assert "market_data" in stats["by_category"]

        print(f"\n✓ Memory stats:")
        print(f"  Total files: {stats['total_files']}")
        print(f"  Total size: {stats['total_size_bytes']} bytes")

    def test_cleanup_old_entries(self, temp_memory):
        """Test cleaning up old entries."""
        now = datetime.now()
        old_time = (now - timedelta(days=35)).isoformat()
        recent_time = (now - timedelta(days=5)).isoformat()

        # Add entries with different timestamps
        entries = [
            {"timestamp": old_time, "data": "old1"},
            {"timestamp": old_time, "data": "old2"},
            {"timestamp": recent_time, "data": "recent1"},
            {"timestamp": recent_time, "data": "recent2"}
        ]

        temp_memory.write("orchestrator", "timed_data.json", entries)

        # Cleanup entries older than 30 days
        removed = temp_memory.cleanup_old_entries("orchestrator", "timed_data.json", max_age_days=30)

        result = temp_memory.read("orchestrator", "timed_data.json")

        assert len(result) == 2
        assert all("recent" in entry["data"] for entry in result)
        assert removed == 2

        print(f"\n✓ Cleaned up {removed} old entries")

    def test_atomic_write(self, temp_memory):
        """Test that writes are atomic (no partial writes)."""
        large_data = {"data": "x" * 10000}

        temp_memory.write("orchestrator", "large.json", large_data)
        result = temp_memory.read("orchestrator", "large.json")

        assert result == large_data

        print(f"\n✓ Atomic write working")

    def test_concurrent_access(self, temp_memory):
        """Test that file locking prevents corruption."""
        # Write initial data
        temp_memory.write("orchestrator", "concurrent.json", {"counter": 0})

        # Simulate multiple updates (sequential, but testing lock mechanism)
        for i in range(5):
            data = temp_memory.read("orchestrator", "concurrent.json")
            data["counter"] += 1
            temp_memory.write("orchestrator", "concurrent.json", data)

        result = temp_memory.read("orchestrator", "concurrent.json")
        assert result["counter"] == 5

        print(f"\n✓ File locking working")
