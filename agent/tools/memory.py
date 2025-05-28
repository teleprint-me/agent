import sqlite3
from typing import Dict, List, Optional

DB_PATH = ".agent/memory.sqlite3"


def get_db(db_path: Optional[str] = None):
    return sqlite3.connect(db_path if db_path is not None else DB_PATH)


def memory_create(content: str, tags: Optional[List[str]] = None) -> int:
    with get_db() as conn:
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
    with get_db() as conn:
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
    with get_db() as conn:
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
    with get_db() as conn:
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
