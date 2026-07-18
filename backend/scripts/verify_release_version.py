from __future__ import annotations

import json
import re
import sys
from pathlib import Path

VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def extract(pattern: str, path: Path) -> str:
    match = re.search(pattern, path.read_text(encoding="utf-8"), flags=re.MULTILINE)
    if match is None:
        raise RuntimeError(f"Could not read version from {path}")
    return match.group(1)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python backend/scripts/verify_release_version.py vX.Y.Z")

    release_tag = sys.argv[1]
    expected_version = release_tag.removeprefix("v")
    if release_tag != f"v{expected_version}" or VERSION_PATTERN.fullmatch(expected_version) is None:
        raise SystemExit(f"Release tag must use vX.Y.Z format, got: {release_tag}")

    repository_root = Path(__file__).resolve().parents[2]
    package_json = json.loads((repository_root / "frontend" / "package.json").read_text(encoding="utf-8"))
    package_lock = json.loads(
        (repository_root / "frontend" / "package-lock.json").read_text(encoding="utf-8")
    )
    versions = {
        "backend/pyproject.toml": extract(
            r'^version = "([^"]+)"$',
            repository_root / "backend" / "pyproject.toml",
        ),
        "backend/app/core/config.py": extract(
            r'^\s*app_version: str = "([^"]+)"$',
            repository_root / "backend" / "app" / "core" / "config.py",
        ),
        "frontend/package.json": package_json["version"],
        "frontend/package-lock.json": package_lock["version"],
        "frontend/package-lock.json root package": package_lock["packages"][""]["version"],
    }
    mismatches = {source: version for source, version in versions.items() if version != expected_version}
    if mismatches:
        details = ", ".join(f"{source}={version}" for source, version in mismatches.items())
        raise SystemExit(f"Release {release_tag} does not match project versions: {details}")

    print(f"Release version verification passed for {release_tag}.")


if __name__ == "__main__":
    main()
