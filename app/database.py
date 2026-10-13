"""Small SQLite persistence layer for Business connection and message snapshots."""
import sqlite3
from pathlib import Path
from typing import Any


class Database:
    def __init__(self, path: str):
        self.path = str(path)
        Path(self.path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _initialize(self) -> None:
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS business_connections (
                    connection_id TEXT PRIMARY KEY,
                    owner_user_id INTEGER NOT NULL,
                    is_enabled INTEGER NOT NULL DEFAULT 1,
                    can_reply INTEGER,
                    can_read_messages INTEGER,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_business_owner
                ON business_connections(owner_user_id)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS message_snapshots (
                    connection_id TEXT NOT NULL,
                    chat_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    owner_user_id INTEGER NOT NULL,
                    chat_title TEXT,
                    sender_label TEXT,
                    message_text TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (connection_id, chat_id, message_id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshot_owner
                ON message_snapshots(owner_user_id)
            """)
            # Backward-compatible migration for databases created by earlier versions.
            columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(message_snapshots)")
            }
            if "media_type" not in columns:
                conn.execute("ALTER TABLE message_snapshots ADD COLUMN media_type TEXT")
            if "file_id" not in columns:
                conn.execute("ALTER TABLE message_snapshots ADD COLUMN file_id TEXT")

    def upsert_connection(
        self,
        connection_id: str,
        owner_user_id: int,
        is_enabled: bool,
        can_reply: bool | None = None,
        can_read_messages: bool | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO business_connections (
                    connection_id, owner_user_id, is_enabled,
                    can_reply, can_read_messages, updated_at
                ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(connection_id) DO UPDATE SET
                    owner_user_id=excluded.owner_user_id,
                    is_enabled=excluded.is_enabled,
                    can_reply=excluded.can_reply,
                    can_read_messages=excluded.can_read_messages,
                    updated_at=CURRENT_TIMESTAMP
            """, (
                connection_id, owner_user_id, int(is_enabled),
                None if can_reply is None else int(can_reply),
                None if can_read_messages is None else int(can_read_messages),
            ))

    def get_connection(self, connection_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM business_connections WHERE connection_id = ?",
                (connection_id,),
            ).fetchone()
            return dict(row) if row else None

    def list_connections(self, owner_user_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT * FROM business_connections
                WHERE owner_user_id = ? ORDER BY updated_at DESC
            """, (owner_user_id,)).fetchall()
            return [dict(row) for row in rows]

    def close_connection(self, connection_id: str, owner_user_id: int) -> None:
        with self._connect() as conn:
            conn.execute("""
                UPDATE business_connections
                SET is_enabled = 0, updated_at = CURRENT_TIMESTAMP
                WHERE connection_id = ? AND owner_user_id = ?
            """, (connection_id, owner_user_id))

    def count_active_connections(self, owner_user_id: int) -> int:
        with self._connect() as conn:
            row = conn.execute("""
                SELECT COUNT(*) AS n FROM business_connections
                WHERE owner_user_id = ? AND is_enabled = 1
            """, (owner_user_id,)).fetchone()
            return int(row["n"])

    def get_message_snapshot(
        self, connection_id: str, chat_id: int, message_id: int
    ) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("""
                SELECT * FROM message_snapshots
                WHERE connection_id = ? AND chat_id = ? AND message_id = ?
            """, (connection_id, chat_id, message_id)).fetchone()
            return dict(row) if row else None

    def save_message_snapshot(
        self, connection_id: str, chat_id: int, message_id: int,
        owner_user_id: int, chat_title: str, sender_label: str, message_text: str,
        media_type: str | None = None, file_id: str | None = None
    ) -> None:
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO message_snapshots (
                    connection_id, chat_id, message_id, owner_user_id,
                    chat_title, sender_label, message_text, media_type, file_id, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(connection_id, chat_id, message_id) DO UPDATE SET
                    owner_user_id=excluded.owner_user_id,
                    chat_title=excluded.chat_title,
                    sender_label=excluded.sender_label,
                    message_text=excluded.message_text,
                    media_type=excluded.media_type,
                    file_id=excluded.file_id,
                    updated_at=CURRENT_TIMESTAMP
            """, (
                connection_id, chat_id, message_id, owner_user_id,
                chat_title, sender_label, message_text, media_type, file_id
            ))

    def delete_message_snapshot(
        self, connection_id: str, chat_id: int, message_id: int
    ) -> dict[str, Any] | None:
        # Read and delete atomically so the stored copy is removed after notification.
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("""
                SELECT * FROM message_snapshots
                WHERE connection_id = ? AND chat_id = ? AND message_id = ?
            """, (connection_id, chat_id, message_id)).fetchone()
            conn.execute("""
                DELETE FROM message_snapshots
                WHERE connection_id = ? AND chat_id = ? AND message_id = ?
            """, (connection_id, chat_id, message_id))
            return dict(row) if row else None
