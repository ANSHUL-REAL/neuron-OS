from __future__ import annotations

import sqlite3
from collections import Counter
from pathlib import Path

from .schemas import ExecutionRecord, MemoryRecord


class MemoryStore:
    def __init__(self, db_path: Path, collection_path: Path | None = None):
        self.db_path = db_path
        self.collection_path = collection_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if self.collection_path:
            self.collection_path.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def save_conversation(self, role: str, content: str) -> None:
        with self._connect() as db:
            db.execute(
                "insert into conversations(role, content) values (?, ?)",
                (role, content),
            )

    def save_memory(self, kind: str, content: str) -> MemoryRecord:
        with self._connect() as db:
            existing = db.execute(
                "select id, kind, content, created_at from memories where kind = ? and content = ? order by id desc limit 1",
                (kind, content),
            ).fetchone()
            if existing:
                return _memory_from_row(existing)
            cursor = db.execute(
                "insert into memories(kind, content) values (?, ?)",
                (kind, content),
            )
            row = db.execute(
                "select id, kind, content, created_at from memories where id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        return _memory_from_row(row)

    def search(self, query: str, limit: int = 5) -> list[MemoryRecord]:
        terms = _terms(query)
        with self._connect() as db:
            rows = db.execute(
                "select id, kind, content, created_at from memories order by id desc"
            ).fetchall()
        ranked = sorted(
            ((_score(row["content"], terms), row["id"], row) for row in rows),
            key=lambda item: (item[0], item[1]),
        )
        return [
            _memory_from_row(row)
            for score, _, row in reversed(ranked)
            if score > 0
        ][:limit]

    def record_execution(
        self, step_id: str, tool: str, status: str, output: str
    ) -> ExecutionRecord:
        with self._connect() as db:
            cursor = db.execute(
                "insert into executions(step_id, tool, status, output) values (?, ?, ?, ?)",
                (step_id, tool, status, output),
            )
            row = db.execute(
                "select id, step_id, tool, status, output, created_at from executions where id = ?",
                (cursor.lastrowid,),
            ).fetchone()
        return _execution_from_row(row)

    def recent_executions(self, limit: int = 20) -> list[ExecutionRecord]:
        with self._connect() as db:
            rows = db.execute(
                "select id, step_id, tool, status, output, created_at from executions order by id desc limit ?",
                (limit,),
            ).fetchall()
        return [_execution_from_row(row) for row in rows]

    def recent_conversations(self, limit: int = 10) -> list[sqlite3.Row]:
        with self._connect() as db:
            return db.execute(
                "select role, content, created_at from conversations order by id desc limit ?",
                (limit,),
            ).fetchall()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        return db

    def _init_db(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                create table if not exists conversations (
                  id integer primary key autoincrement,
                  role text not null,
                  content text not null,
                  created_at text not null default current_timestamp
                );

                create table if not exists memories (
                  id integer primary key autoincrement,
                  kind text not null,
                  content text not null,
                  created_at text not null default current_timestamp
                );

                create table if not exists executions (
                  id integer primary key autoincrement,
                  step_id text not null,
                  tool text not null,
                  status text not null,
                  output text not null,
                  created_at text not null default current_timestamp
                );
                """
            )


def _terms(text: str) -> Counter[str]:
    words = [word.lower() for word in text.replace("\\", " ").split()]
    return Counter(word.strip(".,:;!?") for word in words if len(word.strip(".,:;!?")) > 2)


def _score(content: str, query_terms: Counter[str]) -> int:
    content_terms = _terms(content)
    return sum(min(content_terms[term], count) for term, count in query_terms.items())


def _memory_from_row(row: sqlite3.Row) -> MemoryRecord:
    return MemoryRecord(
        id=row["id"],
        kind=row["kind"],
        content=row["content"],
        created_at=row["created_at"],
    )


def _execution_from_row(row: sqlite3.Row) -> ExecutionRecord:
    return ExecutionRecord(
        id=row["id"],
        step_id=row["step_id"],
        tool=row["tool"],
        status=row["status"],
        output=row["output"],
        created_at=row["created_at"],
    )
