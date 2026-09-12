from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import uuid
from copy import deepcopy
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

from release_preflight_plan import (
    _attach_equivalent_sql_checksums,
    _extract_migrations,
    _normalize_target_state,
    build_preflight_plan,
)


SCHEMA_VERSION = "release-build-preflight/v1"
PROSPECTIVE_SCHEMA_VERSION = "release-build-prospective/v1"
TARGET_STATE_SCHEMA_VERSION = "release-target-state/v1"
ALLOWED_ACTIONS = {
    "APPLY",
    "SKIP_ALREADY_APPLIED",
    "SKIP_ENV_NOT_ALLOWED",
    "SKIP_SCOPE_EXCLUDED",
}
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40,64}$")


class BuildPreflightError(ValueError):
    pass


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _read_json_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise BuildPreflightError(f"{label} is missing: {path}")
    raw = path.read_bytes()
    if not raw.strip():
        raise BuildPreflightError(f"{label} is blank: {path}")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BuildPreflightError(f"{label} is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise BuildPreflightError(f"{label} must be a JSON object")
    return value


def _validate_source_repos(manifest: dict[str, Any]) -> tuple[list[dict[str, object]], dict[str, str]]:
    raw_repos = manifest.get("sourceRepos")
    if not isinstance(raw_repos, list) or not raw_repos:
        raise BuildPreflightError("prospective manifest sourceRepos must be a non-empty array")
    repos: list[dict[str, object]] = []
    commits: dict[str, str] = {}
    identities: set[tuple[str, str]] = set()
    for raw in raw_repos:
        if not isinstance(raw, dict):
            raise BuildPreflightError("prospective manifest sourceRepos items must be objects")
        name = str(raw.get("name") or "").strip()
        role = str(raw.get("pathRole") or "").strip()
        commit = str(raw.get("commit") or "").strip().lower()
        if not name or not role or not COMMIT_PATTERN.fullmatch(commit):
            raise BuildPreflightError("source repo requires name, pathRole, and a 40-64 character hexadecimal commit")
        if raw.get("dirty") is not False:
            raise BuildPreflightError(f"source repo must explicitly declare dirty=false: {name or '<unnamed>'}")
        identity = (name.casefold(), role.casefold())
        if identity in identities or name in commits:
            raise BuildPreflightError(f"duplicate source repo identity: {name}/{role}")
        identities.add(identity)
        commits[name] = commit
        repos.append({"name": name, "pathRole": role, "commit": commit, "dirty": False})
    repos.sort(key=lambda item: (item["pathRole"].casefold(), item["name"].casefold()))
    return repos, dict(sorted(commits.items()))


def _normalize_migration_contract(raw: object, label: str) -> dict[str, object]:
    if not isinstance(raw, dict):
        raise BuildPreflightError(f"{label} migration must be an object")
    required_string_fields = ("migrationId", "file", "sha256", "type", "riskLevel")
    normalized: dict[str, object] = {}
    for field in required_string_fields:
        value = str(raw.get(field) or "").strip()
        if not value:
            raise BuildPreflightError(f"{label} migration is missing {field}")
        normalized[field] = value
    normalized["file"] = PurePosixPath(str(normalized["file"]).replace("\\", "/")).as_posix()
    normalized["sha256"] = str(normalized["sha256"]).removeprefix("sha256:").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", str(normalized["sha256"])):
        raise BuildPreflightError(f"{label} migration sha256 is invalid")
    for field in ("allowedEnvironments", "dependsOn"):
        values = raw.get(field)
        if not isinstance(values, list):
            raise BuildPreflightError(f"{label} migration {field} must be an array")
        normalized[field] = sorted(str(value).strip() for value in values)
    target_required = raw.get('requiresTargetPreflight', False)
    if not isinstance(target_required, bool):
        raise BuildPreflightError(f'{label} requiresTargetPreflight must be a boolean')
    normalized['requiresTargetPreflight'] = target_required
    return normalized


def _assert_migration_contract_match(manifest: dict[str, Any]) -> None:
    database = manifest.get("database")
    raw_migrations = database.get("schemaMigrations") if isinstance(database, dict) else None
    raw_required_sql = manifest.get("requiredSql")
    if not isinstance(raw_migrations, list) or not isinstance(raw_required_sql, list):
        raise BuildPreflightError("prospective manifest requires database.schemaMigrations and requiredSql arrays")
    migrations = [
        _normalize_migration_contract(item, "database.schemaMigrations") for item in raw_migrations
    ]
    required_sql = [_normalize_migration_contract(item, "requiredSql") for item in raw_required_sql]
    if migrations != required_sql:
        raise BuildPreflightError(
            "prospective manifest database.schemaMigrations must exactly match requiredSql"
        )


def _validate_required_sql(manifest: dict[str, Any], package_root: Path) -> list[dict[str, object]]:
    raw_entries = manifest.get("requiredSql")
    if not isinstance(raw_entries, list) or not raw_entries:
        raise BuildPreflightError("prospective manifest requiredSql must be a non-empty array")
    root = package_root.resolve()
    records: list[dict[str, object]] = []
    seen_paths: set[str] = set()
    for raw in raw_entries:
        if not isinstance(raw, dict):
            raise BuildPreflightError("prospective manifest requiredSql items must be objects")
        relative = str(raw.get("file") or "").replace("\\", "/")
        pure = PurePosixPath(relative)
        if not relative or pure.is_absolute() or ".." in pure.parts:
            raise BuildPreflightError(f"unsafe required SQL path: {relative or '<blank>'}")
        normalized = pure.as_posix()
        folded = normalized.casefold()
        if folded in seen_paths:
            raise BuildPreflightError(f"duplicate required SQL path: {normalized}")
        seen_paths.add(folded)
        path = (root / Path(*pure.parts)).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise BuildPreflightError(f"required SQL escapes prospective manifest root: {normalized}") from exc
        if not path.is_file():
            raise BuildPreflightError(f"staged required SQL is missing: {normalized}")
        content = path.read_bytes()
        actual = "sha256:" + hashlib.sha256(content).hexdigest()
        expected = str(raw.get("sha256") or "").lower()
        if not SHA256_PATTERN.fullmatch(expected) or expected != actual:
            raise BuildPreflightError(f"staged required SQL digest mismatch: {normalized}")
        records.append({"path": normalized, "sha256": actual, "size": len(content)})
    records.sort(key=lambda item: str(item["path"]).casefold())
    return records


def _validate_target_state(
    target_state: dict[str, Any], expected_environment: str
) -> tuple[dict[str, dict[str, object]], str, str, dict[str, object]]:
    if target_state.get("schemaVersion") != TARGET_STATE_SCHEMA_VERSION:
        raise BuildPreflightError(f"target state schemaVersion must be {TARGET_STATE_SCHEMA_VERSION}")
    environment = str(target_state.get("targetEnvironment") or "")
    if environment != expected_environment:
        raise BuildPreflightError(
            f"target state environment mismatch: {environment or '<blank>'} != {expected_environment}"
        )
    collection_id = str(target_state.get("collectionId") or "")
    try:
        parsed_id = uuid.UUID(collection_id)
    except ValueError as exc:
        raise BuildPreflightError("target state collectionId must be a UUID") from exc
    if str(parsed_id) != collection_id.lower():
        raise BuildPreflightError("target state collectionId must use canonical UUID format")
    collected_at = str(target_state.get("collectedAt") or "")
    try:
        parsed_time = datetime.fromisoformat(collected_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BuildPreflightError("target state collectedAt must be an ISO-8601 timestamp") from exc
    if not collected_at.endswith("Z") or parsed_time.utcoffset() is None:
        raise BuildPreflightError("target state collectedAt must be UTC and end with Z")
    if "migrationLedger" not in target_state or not isinstance(target_state["migrationLedger"], dict):
        raise BuildPreflightError("target state migrationLedger must be present as an object")
    for migration_id, state in target_state["migrationLedger"].items():
        if not str(migration_id).strip() or not isinstance(state, dict):
            raise BuildPreflightError("target state migrationLedger entries require an id and object value")
        if state.get("status") != "APPLIED":
            raise BuildPreflightError(f"target state migration status must be APPLIED: {migration_id}")
        state_digest = str(state.get("sha256") or "").removeprefix("sha256:").lower()
        if not re.fullmatch(r"[0-9a-f]{64}", state_digest):
            raise BuildPreflightError(f"target state migration sha256 is invalid: {migration_id}")
    ledger = _normalize_target_state(target_state["migrationLedger"])
    normalized_state = {"targetEnvironment": environment, "migrationLedger": ledger}
    return ledger, collection_id, collected_at, normalized_state


def build_evidence(
    manifest_path: Path,
    target_state_path: Path,
    *,
    target_environment: str,
    publish_scope: str,
    package_root: Path | None = None,
) -> dict[str, object]:
    if target_environment != "test":
        raise BuildPreflightError("build preflight targetEnvironment must be test")
    manifest = _read_json_object(manifest_path, "prospective manifest")
    if manifest.get("schemaVersion") != PROSPECTIVE_SCHEMA_VERSION:
        raise BuildPreflightError(f"prospective manifest schemaVersion must be {PROSPECTIVE_SCHEMA_VERSION}")
    if manifest.get("publishScope") != publish_scope:
        raise BuildPreflightError("prospective manifest publishScope does not match command")
    _assert_migration_contract_match(manifest)
    source_repos, source_commits = _validate_source_repos(manifest)
    effective_package_root = package_root if package_root is not None else manifest_path.parent
    sql_records = _validate_required_sql(manifest, effective_package_root)
    target_state = _read_json_object(target_state_path, "target state")
    ledger, collection_id, collected_at, normalized_target_state = _validate_target_state(
        target_state, target_environment
    )

    migrations = deepcopy(_extract_migrations(manifest))
    if not migrations:
        raise BuildPreflightError("prospective manifest database.schemaMigrations must be non-empty")
    for migration in migrations:
        if "sha256" in migration:
            migration["sha256"] = str(migration["sha256"]).removeprefix("sha256:")
    planner_manifest_path = effective_package_root / manifest_path.name
    _attach_equivalent_sql_checksums(migrations, planner_manifest_path)
    plan = build_preflight_plan(
        migrations,
        ledger,
        target_environment=target_environment,
        publish_scope=publish_scope,
    )
    items = plan.get("items")
    if not isinstance(items, list):
        raise BuildPreflightError("planner items must be an array")

    bindings = {
        "sourceFingerprint": _digest(source_repos),
        "requiredSqlDigest": _digest(sql_records),
        "prospectiveManifestDigest": _digest(manifest),
        "targetStateDigest": _digest(normalized_target_state),
        "plannerItemsDigest": _digest(items),
        "plannerStatusItemsDigest": _digest({"status": plan.get("status"), "items": items}),
    }
    bindings["preflightFingerprint"] = _digest(
        {
            "sourceFingerprint": bindings["sourceFingerprint"],
            "requiredSqlDigest": bindings["requiredSqlDigest"],
            "prospectiveManifestDigest": bindings["prospectiveManifestDigest"],
            "targetStateDigest": bindings["targetStateDigest"],
            "targetEnvironment": target_environment,
            "publishScope": publish_scope,
            "plannerStatusItemsDigest": bindings["plannerStatusItemsDigest"],
        }
    )
    return {
        "schemaVersion": SCHEMA_VERSION,
        "status": plan.get("status"),
        "targetEnvironment": target_environment,
        "publishScope": publish_scope,
        "collectionId": collection_id,
        "collectedAt": collected_at,
        "sourceCommits": source_commits,
        "bindings": bindings,
        "planner": {
            "status": plan.get("status"),
            "items": items,
        },
    }


def assert_qualifies(evidence: dict[str, object]) -> None:
    if evidence.get("schemaVersion") != SCHEMA_VERSION:
        raise BuildPreflightError(f"evidence schemaVersion must be {SCHEMA_VERSION}")
    if evidence.get("status") != "passed":
        raise BuildPreflightError(f"build preflight status must be passed: {evidence.get('status')}")
    planner = evidence.get("planner")
    if not isinstance(planner, dict) or planner.get("status") != "passed":
        raise BuildPreflightError("planner status must be passed")
    items = planner.get("items")
    if not isinstance(items, list):
        raise BuildPreflightError("planner items must be an array")
    for item in items:
        action = str(item.get("action") if isinstance(item, dict) else "")
        if action.startswith("BLOCKED_") or action not in ALLOWED_ACTIONS:
            raise BuildPreflightError(f"planner action cannot qualify build: {action or '<blank>'}")
    bindings = evidence.get("bindings")
    required_bindings = {
        "sourceFingerprint",
        "requiredSqlDigest",
        "prospectiveManifestDigest",
        "targetStateDigest",
        "plannerItemsDigest",
        "plannerStatusItemsDigest",
        "preflightFingerprint",
    }
    if not isinstance(bindings, dict) or set(bindings) != required_bindings:
        raise BuildPreflightError("evidence bindings are incomplete or contain unsupported fields")
    if any(not SHA256_PATTERN.fullmatch(str(value)) for value in bindings.values()):
        raise BuildPreflightError("evidence binding digest is invalid")


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("run", "verify"))
    parser.add_argument("--prospective-manifest", required=True)
    parser.add_argument("--target-state", required=True)
    parser.add_argument("--target-environment", required=True)
    parser.add_argument("--publish-scope", required=True, choices=("app-release",))
    parser.add_argument("--package-root")
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    manifest_path = Path(args.prospective_manifest)
    target_state_path = Path(args.target_state)
    output_path = Path(args.output)
    try:
        expected = build_evidence(
            manifest_path,
            target_state_path,
            target_environment=args.target_environment,
            publish_scope=args.publish_scope,
            package_root=Path(args.package_root) if args.package_root else None,
        )
        if args.command == "run":
            _write_json(output_path, expected)
            assert_qualifies(expected)
        else:
            actual = _read_json_object(output_path, "build preflight evidence")
            assert_qualifies(actual)
            if _canonical_bytes(actual) != _canonical_bytes(expected):
                raise BuildPreflightError("build preflight evidence does not match recomputed bindings")
        return 0
    except (BuildPreflightError, ValueError, OSError) as exc:
        print(f"BUILD_PREFLIGHT_BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
