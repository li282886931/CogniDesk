from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Iterable, Optional

from dotenv import load_dotenv

load_dotenv()


class Row(dict):
    """Mapping rows that retain sqlite's integer-index access pattern."""

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


class Cursor:
    def __init__(self, cursor: Any):
        self._cursor = cursor

    def fetchone(self) -> Optional[Row]:
        row = self._cursor.fetchone()
        return Row(row) if row is not None and not isinstance(row, Row) else row

    def fetchall(self) -> list[Row]:
        rows = self._cursor.fetchall()
        return [Row(row) if not isinstance(row, Row) else row for row in rows]


class Connection:
    def __init__(self, raw: Any, backend: str):
        self.raw = raw
        self.backend = backend

    def execute(self, query: str, args: Iterable[Any] = ()) -> Cursor:
        if self.backend == "mysql":
            query = query.replace("?", "%s")
            cursor = self.raw.cursor(dictionary=True)
            cursor.execute(query, tuple(args))
            return Cursor(cursor)
        return Cursor(self.raw.execute(query, tuple(args)))

    def executescript(self, script: str) -> None:
        if self.backend == "mysql":
            cursor = self.raw.cursor()
            for statement in script.split(";"):
                statement = statement.strip()
                if statement:
                    cursor.execute(statement)
            cursor.close()
        else:
            self.raw.executescript(script)

    def commit(self) -> None:
        self.raw.commit()

    def close(self) -> None:
        self.raw.close()


def connect(database_path: Optional[Path] = None) -> Connection:
    if database_path is not None:
        raw = sqlite3.connect(database_path)
        raw.row_factory = sqlite3.Row
        return Connection(raw, "sqlite")

    import mysql.connector

    raw = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "cognidesk"),
        autocommit=False,
    )
    return Connection(raw, "mysql")
