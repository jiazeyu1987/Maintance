from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

if not __package__:
    # The CLI and file-location loader share the same sibling package contract.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ops.release.release_readonly_sql import (
    FORBIDDEN_PATTERN, _executable_sql, ReadonlySqlError as TargetPreflightContractError,
)


METADATA_PATTERN = re.compile(
    r"^\s*--\s*release-target-preflight:\s*"
    r"migrationId=(?P<migration_id>[A-Za-z0-9_.-]+);\s*"
    r"allowedEnvironments=(?P<environments>[A-Za-z0-9_,-]+)\s*$",
    re.MULTILINE,
)
ALLOWED_ENVIRONMENTS = {"test", "prod", "backup"}


def validate(path: Path, migration_id: str) -> None:
    if not path.is_file():
        raise TargetPreflightContractError(f"target preflight file missing: {path}")
    if path.name != f"{migration_id}.preflight.sql":
        raise TargetPreflightContractError(
            f"target preflight filename must be {migration_id}.preflight.sql: {path.name}"
        )
    text = path.read_text(encoding="utf-8")
    metadata_matches = list(METADATA_PATTERN.finditer(text))
    if len(metadata_matches) != 1:
        raise TargetPreflightContractError("exactly one release-target-preflight metadata line is required")
    metadata = metadata_matches[0]
    if metadata.group("migration_id") != migration_id:
        raise TargetPreflightContractError("metadata migrationId does not match the planned migration")
    environments = {item.strip() for item in metadata.group("environments").split(",") if item.strip()}
    if not environments or not environments <= ALLOWED_ENVIRONMENTS:
        raise TargetPreflightContractError("metadata allowedEnvironments is empty or unsupported")

    marker = f"TARGET_PREFLIGHT_PASS:{migration_id}"
    if text.count(marker) != 1:
        raise TargetPreflightContractError(f"exactly one success marker is required: {marker}")
    executable = _executable_sql(text).strip()
    if FORBIDDEN_PATTERN.search(executable):
        token = FORBIDDEN_PATTERN.search(executable)
        raise TargetPreflightContractError(f"write, DDL, transaction, or locking token is forbidden: {token.group(0)}")
    statements = [statement.strip() for statement in executable.split(";") if statement.strip()]
    if len(statements) != 1 or not re.match(r"^(?:select|with)\b", statements[0], re.IGNORECASE):
        raise TargetPreflightContractError("target preflight must contain exactly one SELECT or WITH statement")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--migration-id", required=True)
    parser.add_argument("--path", required=True)
    args = parser.parse_args(argv)
    try:
        validate(Path(args.path), args.migration_id)
        print(f"TARGET_PREFLIGHT_CONTRACT_PASS:{args.migration_id}")
        return 0
    except (OSError, UnicodeError, TargetPreflightContractError) as exc:
        print(f"TARGET_PREFLIGHT_CONTRACT_BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
