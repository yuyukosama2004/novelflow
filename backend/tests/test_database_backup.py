from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from app.platform.backup import (
    BackupError,
    create_sqlite_backup,
    restore_sqlite_backup,
    sqlite_path_from_url,
    verify_sqlite_database,
)


def create_database(path: Path, value: str) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, content TEXT NOT NULL)")
    connection.execute("INSERT INTO notes (content) VALUES (?)", (value,))
    connection.commit()
    return connection


def read_note(path: Path) -> str:
    with closing(sqlite3.connect(path)) as connection:
        row = connection.execute("SELECT content FROM notes").fetchone()
    assert row is not None
    return str(row[0])


def test_create_backup_from_live_wal_database(tmp_path: Path) -> None:
    source_path = tmp_path / "source.db"
    backup_path = tmp_path / "backups" / "snapshot.db"

    source_connection = create_database(source_path, "保留这条正文")
    try:
        snapshot = create_sqlite_backup(source_path, backup_path)
    finally:
        source_connection.close()

    assert snapshot.path == backup_path.resolve()
    assert snapshot.size_bytes > 0
    assert len(snapshot.sha256) == 64
    assert read_note(backup_path) == "保留这条正文"
    assert verify_sqlite_database(backup_path) == snapshot


def test_backup_refuses_to_overwrite_existing_file(tmp_path: Path) -> None:
    source_path = tmp_path / "source.db"
    destination_path = tmp_path / "existing.db"

    create_database(source_path, "source").close()
    create_database(destination_path, "existing").close()

    with pytest.raises(BackupError, match="already exists"):
        create_sqlite_backup(source_path, destination_path)

    assert read_note(destination_path) == "existing"


def test_restore_creates_independent_verified_database(tmp_path: Path) -> None:
    source_path = tmp_path / "source.db"
    backup_path = tmp_path / "snapshot.db"
    restored_path = tmp_path / "restored" / "novelflow.db"

    create_database(source_path, "可恢复内容").close()
    create_sqlite_backup(source_path, backup_path)

    restored = restore_sqlite_backup(backup_path, restored_path)

    assert restored.path == restored_path.resolve()
    assert read_note(restored_path) == "可恢复内容"
    assert restored.sha256 == verify_sqlite_database(restored_path).sha256


def test_failed_backup_removes_partial_file(tmp_path: Path) -> None:
    invalid_source = tmp_path / "invalid.db"
    destination = tmp_path / "snapshot.db"
    invalid_source.write_text("not a sqlite database", encoding="utf-8")

    with pytest.raises(BackupError, match="failed to create"):
        create_sqlite_backup(invalid_source, destination)

    assert not destination.exists()
    assert list(tmp_path.glob(".*.partial")) == []


def test_sqlite_path_from_url_resolves_relative_path(tmp_path: Path) -> None:
    assert (
        sqlite_path_from_url(
            "sqlite+aiosqlite:///./data/novelflow.db",
            base_dir=tmp_path,
        )
        == (tmp_path / "data" / "novelflow.db").resolve()
    )


@pytest.mark.parametrize(
    "database_url",
    [
        "sqlite+aiosqlite:///:memory:",
        "postgresql+asyncpg://localhost/novelflow",
    ],
)
def test_sqlite_path_from_url_rejects_unsupported_database(database_url: str) -> None:
    with pytest.raises(BackupError):
        sqlite_path_from_url(database_url)
