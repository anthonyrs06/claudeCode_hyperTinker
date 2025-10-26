"""
Memory Manager
==============
Interface to Memory Tool storage for persistent state and learning.

This manager provides a simple file-based memory system for:
- Routing history tracking
- Agent performance metrics
- Error pattern learning
- Cross-session state persistence

Design Principles:
- File-based storage in /memories/ directory
- JSON format for human readability
- Atomic writes to prevent corruption
- TTL support for cache management
- Thread-safe operations
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import fcntl
from contextlib import contextmanager


class MemoryManager:
    """Manages reading/writing to Memory Tool storage."""

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize Memory Manager.

        Args:
            base_path: Base path for memory storage (defaults to project_root/memories)
        """
        if base_path is None:
            # Default to project root/memories
            self.base_path = Path(__file__).parent.parent / "memories"
        else:
            self.base_path = Path(base_path)

        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Initialize subdirectories
        self._init_directories()

    def _init_directories(self):
        """Initialize memory subdirectories."""
        subdirs = [
            "orchestrator",
            "validation",
            "market_data",
            "errors",
            "shared"
        ]

        for subdir in subdirs:
            (self.base_path / subdir).mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _file_lock(self, file_path: Path):
        """Context manager for file locking (thread-safe writes)."""
        lock_file = file_path.with_suffix('.lock')
        lock_file.touch(exist_ok=True)

        with open(lock_file, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def read(self, category: str, filename: str, default: Any = None) -> Any:
        """
        Read data from memory.

        Args:
            category: Memory category (orchestrator, validation, market_data, errors, shared)
            filename: Filename (e.g., "routing_history.json")
            default: Default value if file doesn't exist

        Returns:
            Parsed JSON data or default

        Example:
            history = memory.read("orchestrator", "routing_history.json", default=[])
        """
        file_path = self.base_path / category / filename

        if not file_path.exists():
            return default

        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to read {file_path}: {e}")
            return default

    def write(self, category: str, filename: str, data: Any):
        """
        Write data to memory (atomic write).

        Args:
            category: Memory category
            filename: Filename
            data: Data to write (must be JSON serializable)

        Example:
            memory.write("orchestrator", "routing_history.json", history_data)
        """
        file_path = self.base_path / category / filename

        # Atomic write: write to temp file, then rename
        temp_path = file_path.with_suffix('.tmp')

        try:
            with self._file_lock(file_path):
                with open(temp_path, 'w') as f:
                    json.dump(data, f, indent=2, default=str)

                # Atomic rename
                temp_path.replace(file_path)
        except Exception as e:
            # Clean up temp file on error
            if temp_path.exists():
                temp_path.unlink()
            raise Exception(f"Failed to write {file_path}: {e}")

    def append(self, category: str, filename: str, entry: Dict[str, Any], max_entries: int = 1000):
        """
        Append entry to a list in memory (with size limit).

        Args:
            category: Memory category
            filename: Filename
            entry: Entry to append
            max_entries: Maximum entries to keep (FIFO eviction)

        Example:
            memory.append("orchestrator", "routing_history.json", {
                "timestamp": "2025-10-26...",
                "request": "BTC price",
                "agent": "price_book"
            })
        """
        # Read existing data
        data = self.read(category, filename, default=[])

        if not isinstance(data, list):
            raise ValueError(f"File {filename} does not contain a list")

        # Append new entry
        data.append(entry)

        # Trim to max_entries (FIFO)
        if len(data) > max_entries:
            data = data[-max_entries:]

        # Write back
        self.write(category, filename, data)

    def update(self, category: str, filename: str, updates: Dict[str, Any]):
        """
        Update specific fields in memory (merge).

        Args:
            category: Memory category
            filename: Filename
            updates: Fields to update

        Example:
            memory.update("orchestrator", "learned_patterns.json", {
                "price_requests": "price_book_agent"
            })
        """
        # Read existing data
        data = self.read(category, filename, default={})

        if not isinstance(data, dict):
            raise ValueError(f"File {filename} does not contain a dict")

        # Merge updates
        data.update(updates)

        # Write back
        self.write(category, filename, data)

    def delete(self, category: str, filename: str):
        """
        Delete a memory file.

        Args:
            category: Memory category
            filename: Filename
        """
        file_path = self.base_path / category / filename

        if file_path.exists():
            file_path.unlink()

    def clear_category(self, category: str):
        """
        Clear all files in a category.

        Args:
            category: Memory category to clear
        """
        category_path = self.base_path / category

        if category_path.exists():
            for file_path in category_path.glob('*.json'):
                file_path.unlink()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about memory usage.

        Returns:
            {
                "total_files": 15,
                "total_size_bytes": 125000,
                "by_category": {
                    "orchestrator": {"files": 3, "size_bytes": 50000},
                    ...
                }
            }
        """
        stats = {
            "total_files": 0,
            "total_size_bytes": 0,
            "by_category": {}
        }

        for category in ["orchestrator", "validation", "market_data", "errors", "shared"]:
            category_path = self.base_path / category
            category_stats = {"files": 0, "size_bytes": 0}

            if category_path.exists():
                for file_path in category_path.glob('*.json'):
                    category_stats["files"] += 1
                    category_stats["size_bytes"] += file_path.stat().st_size
                    stats["total_files"] += 1
                    stats["total_size_bytes"] += file_path.stat().st_size

            stats["by_category"][category] = category_stats

        return stats

    def cleanup_old_entries(self, category: str, filename: str, max_age_days: int = 30):
        """
        Clean up old entries based on timestamp.

        Args:
            category: Memory category
            filename: Filename
            max_age_days: Maximum age in days

        Example:
            # Remove routing history older than 30 days
            memory.cleanup_old_entries("orchestrator", "routing_history.json", max_age_days=30)
        """
        data = self.read(category, filename, default=[])

        if not isinstance(data, list):
            return

        cutoff = datetime.now() - timedelta(days=max_age_days)

        # Filter entries
        filtered = []
        for entry in data:
            if "timestamp" in entry:
                try:
                    entry_time = datetime.fromisoformat(entry["timestamp"].replace('Z', '+00:00'))
                    if entry_time > cutoff:
                        filtered.append(entry)
                except (ValueError, AttributeError):
                    # Keep entries with invalid timestamps
                    filtered.append(entry)
            else:
                # Keep entries without timestamps
                filtered.append(entry)

        # Write back if changed
        if len(filtered) != len(data):
            self.write(category, filename, filtered)
            return len(data) - len(filtered)

        return 0


# Singleton instance for global access
_memory_manager_instance = None


def get_memory_manager() -> MemoryManager:
    """Get global MemoryManager instance."""
    global _memory_manager_instance
    if _memory_manager_instance is None:
        _memory_manager_instance = MemoryManager()
    return _memory_manager_instance
