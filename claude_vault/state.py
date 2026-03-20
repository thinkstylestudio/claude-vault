import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np


class StateManager:
    """Manages the state database for tracking synced conversations"""

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.db_path = vault_path / ".claude-vault" / "state.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize state database with schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                uuid TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                last_synced TEXT NOT NULL,
                metadata TEXT
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_file_path
            ON conversations(file_path)
        """)

        # Embeddings table for semantic search
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_uuid TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                chunk_text TEXT NOT NULL,
                embedding BLOB NOT NULL,
                embedding_model TEXT NOT NULL,
                file_path TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(conversation_uuid, chunk_index)
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_embeddings_conv
            ON embeddings(conversation_uuid)
        """)

        # Migration: Add file_path column to existing embeddings table
        cursor.execute("PRAGMA table_info(embeddings)")
        columns = [row[1] for row in cursor.fetchall()]
        if "file_path" not in columns:
            cursor.execute("ALTER TABLE embeddings ADD COLUMN file_path TEXT")

        # Watch state table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watch_state (
                id INTEGER PRIMARY KEY,
                is_running BOOLEAN DEFAULT 0,
                pid INTEGER,
                last_started TEXT,
                last_stopped TEXT,
                total_syncs INTEGER DEFAULT 0,
                total_errors INTEGER DEFAULT 0
            )
        """)

        # Watch paths table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watch_paths (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                source_type TEXT NOT NULL,
                added_at TEXT NOT NULL,
                last_sync TEXT,
                is_active BOOLEAN DEFAULT 1
            )
        """)

        conn.commit()
        conn.close()

    def get_conversation(self, uuid: str) -> Optional[Dict]:
        """
        Get conversation state by UUID

        Args:
            uuid: Conversation UUID

        Returns:
            Dictionary with conversation state or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM conversations WHERE uuid = ?", (uuid,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "uuid": row[0],
                "file_path": row[1],
                "content_hash": row[2],
                "last_synced": row[3],
                "metadata": json.loads(row[4]) if row[4] else {},
            }
        return None

    def save_conversation(
        self,
        uuid: str,
        file_path: str,
        content_hash: str,
        metadata: Optional[Dict] = None,
    ):
        """
        Save or update conversation state

        Args:
            uuid: Conversation UUID
            file_path: Path to markdown file
            content_hash: SHA-256 hash of content
            metadata: Optional metadata dictionary
        """
        from datetime import datetime

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO conversations
            (uuid, file_path, content_hash, last_synced, metadata)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                uuid,
                file_path,
                content_hash,
                datetime.now().isoformat(),
                json.dumps(metadata or {}),
            ),
        )
        conn.commit()
        conn.close()

    def find_by_path(self, file_path: str) -> Optional[Dict]:
        """
        Find conversation by file path

        Args:
            file_path: Path to search for

        Returns:
            Dictionary with conversation state or None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM conversations WHERE file_path = ?", (file_path,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "uuid": row[0],
                "file_path": row[1],
                "content_hash": row[2],
                "last_synced": row[3],
                "metadata": json.loads(row[4]) if row[4] else {},
            }
        return None

    def get_all_conversations(self) -> List[Dict]:
        """Get all tracked conversations"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM conversations")
        rows = cursor.fetchall()
        conn.close()

        conversations = []
        for row in rows:
            conversations.append(
                {
                    "uuid": row[0],
                    "file_path": row[1],
                    "content_hash": row[2],
                    "last_synced": row[3],
                    "metadata": json.loads(row[4]) if row[4] else {},
                }
            )
        return conversations

    def delete_conversation(self, uuid: str):
        """Delete conversation from state"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE uuid = ?", (uuid,))
        conn.commit()
        conn.close()

    # Embedding methods
    def save_embedding(
        self,
        conversation_uuid: str,
        chunk_index: int,
        chunk_text: str,
        embedding: np.ndarray,
        model: str,
        file_path: str = "",
    ):
        """Save conversation chunk embedding"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO embeddings
            (conversation_uuid, chunk_index, chunk_text, embedding, embedding_model, file_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                conversation_uuid,
                chunk_index,
                chunk_text,
                embedding.tobytes(),
                model,
                file_path,
                datetime.now().isoformat(),
            ),
        )

        conn.commit()
        conn.close()

    def get_embeddings_for_conversation(self, conversation_uuid: str) -> List[Dict]:
        """Get all embeddings for a conversation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT chunk_index, chunk_text, embedding, embedding_model
            FROM embeddings
            WHERE conversation_uuid = ?
            ORDER BY chunk_index
        """,
            (conversation_uuid,),
        )

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "chunk_index": row[0],
                "chunk_text": row[1],
                "embedding": np.frombuffer(row[2], dtype=np.float32),
                "model": row[3],
            }
            for row in rows
        ]

    def get_all_embeddings(self) -> List[Dict]:
        """Get all embeddings for search"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Use LEFT JOIN to include files that aren't in conversations table
        cursor.execute("""
            SELECT e.conversation_uuid, e.chunk_index, e.chunk_text, e.embedding,
                   COALESCE(e.file_path, c.file_path, ''),
                   COALESCE(c.metadata, '{}')
            FROM embeddings e
            LEFT JOIN conversations c ON e.conversation_uuid = c.uuid
        """)

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "conversation_uuid": row[0],
                "chunk_index": row[1],
                "chunk_text": row[2],
                "embedding": np.frombuffer(row[3], dtype=np.float32),
                "file_path": row[4],
                "metadata": json.loads(row[5]) if row[5] else {},
            }
            for row in rows
        ]

    def delete_embeddings_for_conversation(self, conversation_uuid: str):
        """Delete all embeddings for a conversation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM embeddings WHERE conversation_uuid = ?", (conversation_uuid,)
        )
        conn.commit()
        conn.close()

    # Watch state methods
    def get_watch_state(self) -> Dict:
        """Get current watch state"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM watch_state WHERE id = 1")
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "is_running": bool(row[1]),
                "pid": row[2],
                "last_started": row[3],
                "last_stopped": row[4],
                "total_syncs": row[5],
                "total_errors": row[6],
            }
        return {
            "is_running": False,
            "pid": None,
            "last_started": None,
            "last_stopped": None,
            "total_syncs": 0,
            "total_errors": 0,
        }

    def save_watch_state(self, state: Dict):
        """Save watch state"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO watch_state
            (id, is_running, pid, last_started, last_stopped, total_syncs, total_errors)
            VALUES (1, ?, ?, ?, ?, ?, ?)
        """,
            (
                state.get("is_running", False),
                state.get("pid"),
                state.get("last_started"),
                state.get("last_stopped"),
                state.get("total_syncs", 0),
                state.get("total_errors", 0),
            ),
        )

        conn.commit()
        conn.close()

    def add_watch_path(self, path: str, source_type: str):
        """Add a path to watch list"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO watch_paths (path, source_type, added_at, is_active)
                VALUES (?, ?, ?, 1)
            """,
                (path, source_type, datetime.now().isoformat()),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            pass  # Path already exists
        finally:
            conn.close()

    def remove_watch_path(self, path: str):
        """Remove a path from watch list"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM watch_paths WHERE path = ?", (path,))
        conn.commit()
        conn.close()

    def get_watch_paths(self) -> List[Dict]:
        """Get all watch paths"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT path, source_type, added_at, last_sync, is_active
            FROM watch_paths
            WHERE is_active = 1
        """)

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "path": row[0],
                "source_type": row[1],
                "added_at": row[2],
                "last_sync": row[3],
                "is_active": bool(row[4]),
            }
            for row in rows
        ]

    def update_watch_path_sync_time(self, path: str):
        """Update last sync time for a watch path"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE watch_paths
            SET last_sync = ?
            WHERE path = ?
        """,
            (datetime.now().isoformat(), path),
        )

        conn.commit()
        conn.close()
