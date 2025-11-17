"""
Module: agent.tools.memory
"""

import json
import sqlite3
from typing import Dict, List, Optional

from agent.config import DEFAULT_PATH_MEM, config

DB_PATH = config.get_value("memory.db.path", default=DEFAULT_PATH_MEM)


def memory_connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def memory_initialize() -> sqlite3.Cursor:
    with memory_connect() as conn:
        return conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT (datetime('now', 'localtime')),
                content TEXT NOT NULL,
                tags TEXT,
                user TEXT
            );
        """
        )


def memory_create(content: str, tags: Optional[List[str]] = None) -> str:
    with memory_connect() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO memories (content, tags) VALUES (?, ?)",
            (content, ",".join(tags) if tags else None),
        )
        conn.commit()
        return f"Memory Created: ID={cur.lastrowid}, Tags={','.join(tags)}"


def memory_search(query: str, limit: int = 5) -> str:
    with memory_connect() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, content, tags FROM memories WHERE content LIKE ? LIMIT ?",
            (f"%{query}%", limit),
        )
        rows = cur.fetchall()
        return "\n".join(
            json.dumps(
                {
                    "id": r[0],
                    "content": r[1],
                    "tags": r[2].split(",") if r[2] else [],
                }
            )
            for r in rows
        )


def memory_read(
    id: Optional[int] = None,
    tags: Optional[List[str]] = None,
    limit: int = 10,
    offset: int = 0,
) -> str:
    with memory_connect() as conn:
        cur = conn.cursor()
        query = "SELECT id, timestamp, content, tags FROM memories"
        params = []
        if id:
            query += " WHERE id = ?"
            params.append(id)
        elif tags:
            query += " WHERE " + " OR ".join(["tags LIKE ?"] * len(tags))
            params += [f"%{tag}%" for tag in tags]
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        cur.execute(query, params)
        rows = cur.fetchall()
        if not rows:
            return "No memories found."
        return "\n".join(
            json.dumps(
                {
                    "id": r[0],
                    "timestamp": r[1],
                    "content": r[2],
                    "tags": r[3].split(",") if r[3] else [],
                }
            )
            for r in rows
        )


def memory_update(
    id: int,
    content: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> str:
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
            return "No update fields provided. Please specify content and/or tags to update."
        params.append(id)
        query = f"UPDATE memories SET {', '.join(fields)}, timestamp = CURRENT_TIMESTAMP WHERE id = ?"
        cur.execute(query, params)
        conn.commit()
        if cur.rowcount > 0:
            tag_str = ",".join(tags) if tags else "(unchanged)"
            return f"Memory Updated: ID={id}, Tags={tag_str}"
        return "No memories were modified."


def memory_delete(id: Optional[int] = None, tags: Optional[List[str]] = None) -> str:
    with memory_connect() as conn:
        cur = conn.cursor()
        if id is not None:
            cur.execute("DELETE FROM memories WHERE id = ?", (id,))
            conn.commit()
            if cur.rowcount > 0:
                return f"Memory Deleted: ID={id}"
            else:
                return f"No memory found with ID={id}."
        elif tags:
            query = "DELETE FROM memories WHERE " + " OR ".join(
                ["tags LIKE ?"] * len(tags)
            )
            cur.execute(query, [f"%{tag}%" for tag in tags])
            conn.commit()
            if cur.rowcount > 0:
                tag_str = ", ".join(tags)
                return f"Memories Deleted: {cur.rowcount} entries with tags matching [{tag_str}]"
            else:
                return f"No memories found with tags matching [{', '.join(tags)}]."
        else:
            return "No memories were deleted. Specify an ID or tags."
