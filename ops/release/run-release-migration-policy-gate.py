from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ops.release.release_migration_policy_gate import MigrationPolicyError, run_migration_policy_gate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sql-root", required=True)
    parser.add_argument("--sql-file", action="append", default=[])
    parser.add_argument("--file-prefix", default="sql/mysql")
    parser.add_argument("--frozen-registry")
    parser.add_argument("--output")
    args = parser.parse_args()

    try:
        report = run_migration_policy_gate(
            Path(args.sql_root),
            sql_paths=[Path(item) for item in args.sql_file] if args.sql_file else None,
            file_prefix=args.file_prefix,
            frozen_registry_path=Path(args.frozen_registry) if args.frozen_registry else None,
        )
    except MigrationPolicyError as exc:
        payload = {"status": "failed", "error": str(exc)}
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            Path(args.output).write_text(text, encoding="utf-8")
        sys.stderr.write(text)
        return 1

    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
