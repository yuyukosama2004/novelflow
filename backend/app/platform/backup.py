from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from collections.abc import Sequence
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy.engine import make_url

from app.core.config import get_settings


class BackupError(RuntimeError):
    """Raised when a database backup cannot be created or verified."""


@dataclass(frozen=True)
class DatabaseSnapshot:
    path: Path
    sha256: str
    size_bytes: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }


def sqlite_path_from_url(database_url: str, base_dir: Path | None = None) -> Path:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        raise BackupError("database backup currently supports SQLite only")
    if not url.database or url.database == ":memory:":
        raise BackupError("an on-disk SQLite database is required")

    database_path = Path(url.database).expanduser()
    if not database_path.is_absolute():
        database_path = (base_dir or Path.cwd()) / database_path
    return database_path.resolve()


def verify_sqlite_database(database_path: Path) -> DatabaseSnapshot:
    resolved_path = database_path.expanduser().resolve()
    if not resolved_path.is_file():
        raise BackupError(f"SQLite database does not exist: {resolved_path}")

    try:
        with closing(sqlite3.connect(f"{resolved_path.as_uri()}?mode=ro", uri=True)) as connection:
            result = [row[0] for row in connection.execute("PRAGMA integrity_check")]
    except sqlite3.Error as exc:
        raise BackupError(f"SQLite integrity check failed: {resolved_path}") from exc

    if result != ["ok"]:
        raise BackupError(f"SQLite integrity check reported errors: {result}")

    return DatabaseSnapshot(
        path=resolved_path,
        sha256=_sha256(resolved_path),
        size_bytes=resolved_path.stat().st_size,
    )


def create_sqlite_backup(
    source_path: Path,
    destination_path: Path,
    *,
    overwrite: bool = False,
) -> DatabaseSnapshot:
    source = source_path.expanduser().resolve()
    destination = destination_path.expanduser().resolve()

    if not source.is_file():
        raise BackupError(f"SQLite database does not exist: {source}")
    if source == destination:
        raise BackupError("backup destination must differ from the source database")
    if destination.exists() and not overwrite:
        raise BackupError(f"backup destination already exists: {destination}")

    destination.parent.mkdir(parents=True, exist_ok=True)
    partial_path = destination.with_name(f".{destination.name}.{uuid4().hex}.partial")

    try:
        with closing(sqlite3.connect(source)) as source_connection:
            with closing(sqlite3.connect(partial_path)) as destination_connection:
                source_connection.backup(destination_connection)
        verify_sqlite_database(partial_path)
        os.replace(partial_path, destination)
    except (OSError, sqlite3.Error, BackupError) as exc:
        raise BackupError(f"failed to create SQLite backup: {destination}") from exc
    finally:
        partial_path.unlink(missing_ok=True)

    return verify_sqlite_database(destination)


def restore_sqlite_backup(
    backup_path: Path,
    destination_path: Path,
    *,
    overwrite: bool = False,
) -> DatabaseSnapshot:
    verify_sqlite_database(backup_path)
    return create_sqlite_backup(backup_path, destination_path, overwrite=overwrite)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create, verify, and restore NovelFlow SQLite backups.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create a consistent SQLite backup.")
    create_parser.add_argument(
        "--database-url",
        default=None,
        help="SQLAlchemy SQLite URL. Defaults to the configured DATABASE_URL.",
    )
    create_parser.add_argument("--output", type=Path, required=True, help="Backup file path.")
    create_parser.add_argument("--overwrite", action="store_true")

    verify_parser = subparsers.add_parser("verify", help="Verify a SQLite backup.")
    verify_parser.add_argument("backup", type=Path)

    restore_parser = subparsers.add_parser("restore", help="Restore a backup to a new database path.")
    restore_parser.add_argument("backup", type=Path)
    restore_parser.add_argument("--output", type=Path, required=True)
    restore_parser.add_argument("--overwrite", action="store_true")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)

    try:
        if arguments.command == "create":
            database_url = arguments.database_url or get_settings().database_url
            snapshot = create_sqlite_backup(
                sqlite_path_from_url(database_url),
                arguments.output,
                overwrite=arguments.overwrite,
            )
        elif arguments.command == "verify":
            snapshot = verify_sqlite_database(arguments.backup)
        else:
            snapshot = restore_sqlite_backup(
                arguments.backup,
                arguments.output,
                overwrite=arguments.overwrite,
            )
    except BackupError as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False))
        return 1

    print(json.dumps({"status": "ok", **snapshot.as_dict()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
