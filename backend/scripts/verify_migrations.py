from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


def run_alembic(
    backend_root: Path,
    database_url: str,
    label: str,
    *arguments: str,
) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url
    environment["PYTHONUTF8"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=backend_root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        output = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
        raise RuntimeError(f"{label} failed:\n{output}")
    print(f"[ok] {label}")


def main() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    with TemporaryDirectory(prefix="novelflow-migrations-") as temporary_directory:
        database_path = Path(temporary_directory) / "roundtrip.db"
        database_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
        run_alembic(backend_root, database_url, "upgrade base to head", "upgrade", "head")
        run_alembic(backend_root, database_url, "check metadata matches head", "check")
        run_alembic(backend_root, database_url, "downgrade head to base", "downgrade", "base")
        run_alembic(backend_root, database_url, "re-upgrade base to head", "upgrade", "head")
    print("Alembic round-trip verification passed.")


if __name__ == "__main__":
    main()
