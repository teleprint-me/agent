"""
Module: agent.tools.memory
"""

import json
import sqlite3

from agent.config import DEFAULT_PATH_STOR, config

#
# Database operations
#

DB_PATH = config.get_value("database.path", default=DEFAULT_PATH_STOR)


def memory_connect() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


# this must be called by the user, not the agent
def memory_initialize() -> sqlite3.Cursor:
    with memory_connect() as conn:
        return conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT (datetime('now', 'localtime')),
                content TEXT NOT NULL
            )
            """
        )


#
# CRUD operations (internal)
#


def memory_create(content: str) -> str:
    with memory_connect() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO memories (content) VALUES (?)",
            (content,),
        )
        conn.commit()
        return f"Memory created (ID={cur.lastrowid})"


def memory_search(query: str, limit: int = 5) -> str:
    with memory_connect() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, content FROM memories WHERE content LIKE ? LIMIT ?",
            (f"%{query}%", limit),
        )
        rows = cur.fetchall()
        result = [{"id": r[0], "content": r[1]} for r in rows]
        return json.dumps(result, ensure_ascii=False)


def memory_update(query: str, new_content: str) -> str:
    """
    Updates the most relevant memory based on a simple LIKE search.
    If no result exists, creates a new memory.
    """
    results = json.loads(memory_search(query, limit=1))

    if results:
        mem = results[0]
        mem_id = mem["id"]

        with memory_connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE memories SET content = ?, timestamp = CURRENT_TIMESTAMP WHERE id = ?",
                (new_content, mem_id),
            )
            conn.commit()
            return f"Memory updated (ID={mem_id})"

    # No match, create new
    return memory_create(new_content)


def memory_delete(query: str) -> str:
    results = json.loads(memory_search(query, limit=1))

    if not results:
        return "No matching memory found."

    mem_id = results[0]["id"]

    with memory_connect() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM memories WHERE id = ?", (mem_id,))
        conn.commit()

    return f"Memory deleted (ID={mem_id})"


#
# Agent tools (external)
#


def memory_store(fact: str) -> str:
    return memory_update(fact, fact)


def memory_recall(query: str, limit: int = 5) -> str:
    return memory_search(query, limit)


def memory_forget(query: str) -> str:
    return memory_delete(query)
