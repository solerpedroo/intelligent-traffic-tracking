"""SQLite migrations and connections. Each call opens its own connection."""

import sqlite3
from pathlib import Path

MIGRATIONS = (
    """
    CREATE TABLE videos (
      id TEXT PRIMARY KEY,
      filename TEXT NOT NULL,
      sha256 TEXT NOT NULL,
      size_bytes INTEGER NOT NULL,
      width INTEGER,
      height INTEGER,
      fps REAL,
      duration_s REAL,
      frame_count INTEGER,
      created_at TEXT NOT NULL,
      preview_ready INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE jobs (
      id TEXT PRIMARY KEY,
      video_id TEXT NOT NULL REFERENCES videos(id),
      state TEXT NOT NULL,
      stage TEXT NOT NULL,
      processed_frames INTEGER NOT NULL DEFAULT 0,
      total_frames INTEGER,
      error_code TEXT,
      error TEXT,
      config_json TEXT NOT NULL,
      summary_status TEXT,
      created_at TEXT NOT NULL,
      started_at TEXT,
      finished_at TEXT,
      heartbeat_at TEXT,
      cancel_requested INTEGER NOT NULL DEFAULT 0,
      attempt INTEGER NOT NULL DEFAULT 0
    );
    """,
)


def connect(database: Path) -> sqlite3.Connection:
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database, timeout=30, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA journal_mode=WAL")
    migrate(connection)
    return connection


def migrate(connection: sqlite3.Connection) -> None:
    connection.execute("BEGIN IMMEDIATE")
    try:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)"
        )
        query = "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
        current = connection.execute(query).fetchone()[0]
        for version, script in enumerate(MIGRATIONS, start=1):
            if version <= current:
                continue
            for statement in script.split(";"):
                statement = statement.strip()
                if statement:
                    connection.execute(statement)
            connection.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise


def database_path(data_dir: Path) -> Path:
    return data_dir / "traffic.sqlite"
