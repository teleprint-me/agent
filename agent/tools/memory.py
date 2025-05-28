"""
Module: agent.tools.memory
"""

import sqlite3
from typing import Dict, List, Optional

from agent.config import DEFAULT_PATH_MEM, config

DB_PATH = config.get_value("memory.db.path", default=DEFAULT_PATH_MEM)


def memory_connect() -> sqlite3.Connection:
    return sqlite3.connect()


def memory_initialize() -> sqlite3.Cursor:
    with memory_connect() as conn:
        return conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                content TEXT NOT NULL,
                tags TEXT,
                user TEXT
            );
        """
        )


def memory_create(content: str, tags: Optional[List[str]] = None) -> int:
    with memory_connect() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO memories (content, tags) VALUES (?, ?)",
            (content, ",".join(tags) if tags else None),
        )
        conn.commit()
        return cur.lastrowid


def memory_read(
    id: Optional[int] = None,
    tags: Optional[List[str]] = None,
    limit: int = 10,
    offset: int = 0,
) -> List[Dict]:
    with memory_connect() as conn:
        cur = conn.cursor()
        query = "SELECT id, timestamp, content, tags FROM memories"
        params = []
        if id:
            query += " WHERE id = ?"
            params.append(id)
        elif tags:
            # Simple CSV search; for better, use a tags table or FTS
            query += " WHERE " + " OR ".join(["tags LIKE ?"] * len(tags))
            params += [f"%{tag}%" for tag in tags]
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        cur.execute(query, params)
        rows = cur.fetchall()
        return [
            {
                "id": r[0],
                "timestamp": r[1],
                "content": r[2],
                "tags": r[3].split(",") if r[3] else [],
            }
            for r in rows
        ]


def memory_update(
    id: int, content: Optional[str] = None, tags: Optional[List[str]] = None
) -> bool:
    with memory_connect() as conn:
        cur = conn.cursor()
        fields = []
        params = []
        if content is not None:
            fields.append("content = ?")
            params.append(content)
        if tags is not None:
            fields.append("tags = ?")
            params.append(",".join(tags))
        if not fields:
            return False
        params.append(id)
        query = f"UPDATE memories SET {', '.join(fields)}, timestamp = CURRENT_TIMESTAMP WHERE id = ?"
        cur.execute(query, params)
        conn.commit()
        return cur.rowcount > 0


def memory_delete(id: Optional[int] = None, tags: Optional[List[str]] = None) -> int:
    with memory_connect() as conn:
        cur = conn.cursor()
        if id:
            cur.execute("DELETE FROM memories WHERE id = ?", (id,))
        elif tags:
            # Caution: broad delete if multiple tags
            query = "DELETE FROM memories WHERE " + " OR ".join(
                ["tags LIKE ?"] * len(tags)
            )
            cur.execute(query, [f"%{tag}%" for tag in tags])
        else:
            return 0
        conn.commit()
        return cur.rowcount
