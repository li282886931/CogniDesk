from __future__ import annotations

import os
import sys
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import SCHEMA


def main() -> None:
    load_dotenv()
    database = os.getenv("MYSQL_DATABASE", "cognidesk")
    connection = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
    )
    cursor = connection.cursor()
    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cursor.close()
    connection.close()

    connection = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=database,
    )
    cursor = connection.cursor()
    for statement in SCHEMA.split(";"):
        statement = statement.strip()
        if statement:
            cursor.execute(statement)
    connection.commit()
    cursor.close()
    connection.close()
    print(f"MySQL database ready: {database}")


if __name__ == "__main__":
    main()
