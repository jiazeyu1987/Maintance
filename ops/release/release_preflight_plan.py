from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import re
import sys
from copy import deepcopy
from collections import defaultdict
from pathlib import Path

if __package__:
    from .release_digest import _normalise_path, _ascii_case_fold
    from .release_target_state_collector import (
        evidence_digest, fingerprint_target_snapshot, normalize_target_snapshot, read_json_evidence, validate_capture_time,
    )
else:
    from release_digest import _normalise_path, _ascii_case_fold
    from release_target_state_collector import (
        evidence_digest, fingerprint_target_snapshot, normalize_target_snapshot, read_json_evidence, validate_capture_time,
    )

DEPLOY_PLAN_SCHEMA_VERSION = "release-deploy-plan/v1"

BLOCKED_ACTIONS = {
    "BLOCKED_LEDGER_STATE",
    "BLOCKED_CHECKSUM_MISMATCH",
    "BLOCKED_DEPENDENCY_MISSING",
    "BLOCKED_PREREQUISITE_MISSING",
    "BLOCKED_SCOPE_DEPENDENCY",
}
SKIP_ENV_NOT_ALLOWED = "SKIP_ENV_NOT_ALLOWED"
SKIP_SCOPE_EXCLUDED = "SKIP_SCOPE_EXCLUDED"
SKIP_IMMUTABLE = "SKIP_IMMUTABLE"
SUPPORTED_PUBLISH_SCOPES = {"app-release"}
SUPPORTED_MIGRATION_TYPES = {"schema", "data", "menu", "config", "permission", "seed"}
RESOLVED_LEDGER_STATUSES = {"APPLIED", "SKIPPED_ALREADY_APPLIED", "SKIPPED_ENV_NOT_ALLOWED", "SKIPPED_SCOPE_EXCLUDED", "SKIPPED_IMMUTABLE"}


class _VerifiedMetadataChecksum(str):
    """Equivalence comes only from verified SQL bytes, never manifest declarations."""

    def __new__(cls, checksum: str, executable_checksum: str):
        value = super().__new__(cls, checksum)
        value.executable_checksum = executable_checksum
        return value


def _state_for(target_state: dict[str, dict[str, object]], migration_id: str) -> dict[str, object] | None:
    value = target_state.get(migration_id)
    return value if isinstance(value, dict) else None


def _item(migration: dict[str, object], action: str, reason: str) -> dict[str, object]:
    item = {
        "migrationId": migration["migrationId"],
        "file": migration.get("file"),
        "sha256": str(migration["sha256"]) if migration.get("sha256") is not None else None,
        "supersedes": list(migration.get("supersedes", []) or []),
        "allowedPublishScopes": list(migration.get("allowedPublishScopes", []) or []),
        "scopeReason": migration.get("scopeReason", ""),
        "type": migration.get("type"),
        "requiresTargetPreflight": bool(migration.get("requiresTargetPreflight", False)),
        "applyOrder": migration.get("applyOrder"),
        "sessionProfile": migration.get("sessionProfile", ""),
        "approvedHook": migration.get("approvedHook", ""),
        "resultAssertion": migration.get("resultAssertion", ""),
        "action": action,
        "reason": reason,
    }
    if "targetPreflight" in migration:
        item["targetPreflight"] = deepcopy(migration["targetPreflight"])
    return item


def _order_migrations_by_dependencies(
    migrations: list[dict[str, object]],
    supersession_owners: dict[str, str] | None = None,
) -> list[dict[str, object]]:
    migration_by_id = {str(migration["migrationId"]): migration for migration in migrations}
    original_index = {str(migration["migrationId"]): index for index, migration in enumerate(migrations)}
    indegree = {migration_id: 0 for migration_id in migration_by_id}
    edges: dict[str, list[str]] = defaultdict(list)
    supersession_owners = supersession_owners or {}

    def sort_key(migration_id: str) -> tuple[int, int]:
        migration = migration_by_id[migration_id]
        apply_order = migration.get("applyOrder")
        if isinstance(apply_order, int) and not isinstance(apply_order, bool):
            return apply_order, original_index[migration_id]
        return 1000 + original_index[migration_id], original_index[migration_id]

    for migration in migrations:
        migration_id = str(migration["migrationId"])
        dependencies = list(migration.get("dependsOn", []) or [])
        dependencies.extend(
            supersession_owners[dependency]
            for dependency in list(dependencies)
            if dependency in supersession_owners and supersession_owners[dependency] not in dependencies
        )
        for dependency in dependencies:
            dependency_id = str(dependency)
            if dependency_id not in migration_by_id:
                continue
            edges[dependency_id].append(migration_id)
            indegree[migration_id] += 1

    ready = [
        (*sort_key(migration_id), migration_id)
        for migration_id, degree in sorted(indegree.items(), key=lambda item: original_index[item[0]])
        if degree == 0
    ]
    heapq.heapify(ready)
    ordered_ids: list[str] = []
    while ready:
        _, _, migration_id = heapq.heappop(ready)
        ordered_ids.append(migration_id)
        for child_id in sorted(edges.get(migration_id, []), key=sort_key):
            indegree[child_id] -= 1
            if indegree[child_id] == 0:
                heapq.heappush(ready, (*sort_key(child_id), child_id))

    if len(ordered_ids) != len(migrations):
        raise ValueError("MIGRATION_DEPENDENCY_CYCLE: migration dependency graph contains a cycle")
    return [migration_by_id[migration_id] for migration_id in ordered_ids]


def _validate_supersession_graph(
    migrations: list[dict[str, object]],
    supersession_owners: dict[str, str],
    *,
    target_environment: str,
    publish_scope: str,
) -> None:
    migration_by_id = {str(migration["migrationId"]): migration for migration in migrations}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(migration_id: str) -> None:
        if migration_id in visiting:
            raise ValueError(f"supersession cycle detected at '{migration_id}'")
        if migration_id in visited:
            return
        visiting.add(migration_id)
        successor = supersession_owners.get(migration_id)
        if successor is not None:
            visit(successor)
        visiting.remove(migration_id)
        visited.add(migration_id)

    for migration_id in migration_by_id:
        visit(migration_id)

    for successor_id in supersession_owners.values():
        if successor_id in supersession_owners:
            raise ValueError(
                f"multi-level supersession is not supported: '{successor_id}' is also superseded"
            )
        successor = migration_by_id[successor_id]
        allowed_environments = {str(value) for value in successor.get("allowedEnvironments", [])}
        if target_environment not in allowed_environments:
            raise ValueError(
                f"supersession target '{successor_id}' not allowed for environment '{target_environment}'"
            )
        declared_scopes = list(successor.get("allowedPublishScopes", []) or [])
        allowed_scopes = (
            {str(value) for value in declared_scopes}
            if declared_scopes
            else {publish_scope}
        )
        if publish_scope not in allowed_scopes:
            raise ValueError(
                f"supersession target '{successor_id}' not allowed for publish scope '{publish_scope}'"
            )


def build_preflight_plan(
    migrations: list[dict[str, object]],
    target_state: dict[str, dict[str, object]],
    *,
    target_environment: str,
    publish_scope: str,
) -> dict[str, object]:
    if publish_scope not in SUPPORTED_PUBLISH_SCOPES:
        raise ValueError(f"unsupported publish scope: {publish_scope}")

    items: list[dict[str, object]] = []
    seen_ids: set[str] = set()
    for migration in migrations:
        migration_id = migration.get("migrationId")
        if not isinstance(migration_id, str) or not migration_id.strip() or migration_id != migration_id.strip():
            raise ValueError("MIGRATION_ID_INVALID: migrationId must be a non-empty string")
        if migration_id in seen_ids:
            raise ValueError(f"MIGRATION_ID_DUPLICATE: {migration_id}")
        seen_ids.add(migration_id)
        dependencies = migration.get("dependsOn", [])
        if not isinstance(dependencies, list) or any(not isinstance(value, str) or not value.strip() for value in dependencies):
            raise ValueError(f"MIGRATION_DEPENDENCY_INVALID: {migration_id}")
        if len(dependencies) != len(set(dependencies)):
            raise ValueError(f"MIGRATION_DEPENDENCY_DUPLICATE: {migration_id}")
    target_state = _normalize_target_state(target_state)
    known_migrations = {str(migration["migrationId"]) for migration in migrations}
    supersession_owners: dict[str, str] = {}
    for migration in migrations:
        migration_id = str(migration["migrationId"])
        supersedes = migration.get("supersedes", []) or []
        if not isinstance(supersedes, list):
            raise ValueError(f"supersedes must be an array for migrationId '{migration_id}'")
        if supersedes and not bool(migration.get("requiresTargetPreflight", False)):
            raise ValueError(f"superseding migration '{migration_id}' requires target preflight")
        for legacy_value in supersedes:
            legacy_id = str(legacy_value).strip()
            if not legacy_id:
                raise ValueError(f"supersedes contains an empty migrationId for '{migration_id}'")
            if legacy_id == migration_id:
                raise ValueError(f"migrationId '{migration_id}' cannot supersede itself")
            if legacy_id not in known_migrations:
                raise ValueError(
                    f"supersedes missing migration '{legacy_id}' for migrationId '{migration_id}'"
                )
            previous_owner = supersession_owners.get(legacy_id)
            if previous_owner is not None and previous_owner != migration_id:
                raise ValueError(
                    f"multiple supersession owners for migration '{legacy_id}': "
                    f"'{previous_owner}' and '{migration_id}'"
                )
            supersession_owners[legacy_id] = migration_id
    _validate_supersession_graph(
        migrations,
        supersession_owners,
        target_environment=target_environment,
        publish_scope=publish_scope,
    )
    ordered_migrations = _order_migrations_by_dependencies(migrations, supersession_owners)
    unresolved = {
        migration_id: state for migration_id, state in target_state.items()
        if state["status"] not in RESOLVED_LEDGER_STATUSES
    }
    for migration_id in sorted(set(unresolved) - known_migrations):
        items.append(_item({"migrationId": migration_id}, "BLOCKED_LEDGER_STATE",
                           f"unresolved historical ledger status: {unresolved[migration_id]['status'] or '<blank>'}"))
    planned_actions: dict[str, str] = {}
    scope_dependency_paths: dict[str, list[str]] = {}
    satisfied_migrations = {
        migration_id
        for migration_id, state in target_state.items()
        if state.get("status") == "APPLIED" and migration_id not in known_migrations
    }
    for migration in ordered_migrations:
        migration_id = str(migration["migrationId"])
        migration_type = str(migration.get("type", "")).strip()
        if migration_type not in SUPPORTED_MIGRATION_TYPES:
            raise ValueError(f"unsupported migration type for {migration_id}: {migration_type or '<blank>'}")
        if migration_id in unresolved:
            items.append(_item(migration, "BLOCKED_LEDGER_STATE",
                               f"unresolved ledger status: {unresolved[migration_id]['status'] or '<blank>'}"))
            planned_actions[migration_id] = "BLOCKED_LEDGER_STATE"
            continue
        superseding_migration_id = supersession_owners.get(migration_id)
        if superseding_migration_id is not None:
            items.append(
                _item(
                    migration,
                    SKIP_IMMUTABLE,
                    f"superseded by {superseding_migration_id}; legacy migration is immutable",
                )
            )
            planned_actions[migration_id] = SKIP_IMMUTABLE
            continue
        state = _state_for(target_state, migration_id)
        if state and state.get("status") == "APPLIED":
            accepted_checksums = {str(migration.get("sha256"))}
            if isinstance(migration.get("sha256"), _VerifiedMetadataChecksum):
                accepted_checksums.add(migration["sha256"].executable_checksum)
            if str(state.get("sha256")) in accepted_checksums:
                items.append(_item(migration, "SKIP_ALREADY_APPLIED", "migration already applied with matching checksum"))
                satisfied_migrations.add(migration_id)
                planned_actions[migration_id] = "SKIP_ALREADY_APPLIED"
                continue
            items.append(_item(migration, "BLOCKED_CHECKSUM_MISMATCH", "APPLIED checksum differs from verified immutable SQL; explicit migration review required"))
            planned_actions[migration_id] = "BLOCKED_CHECKSUM_MISMATCH"
            continue

        allowed = [str(item) for item in migration.get("allowedEnvironments", [])]
        if target_environment not in allowed:
            items.append(_item(migration, SKIP_ENV_NOT_ALLOWED, f"{target_environment} is not allowed"))
            planned_actions[migration_id] = SKIP_ENV_NOT_ALLOWED
            continue

        declared_scopes = list(migration.get("allowedPublishScopes", []) or [])
        if declared_scopes and publish_scope not in declared_scopes:
            reason = f"{publish_scope} is not allowed"
            if migration.get('scopeReason'):
                reason += ': ' + str(migration['scopeReason'])
            items.append(_item(migration, SKIP_SCOPE_EXCLUDED, reason))
            planned_actions[migration_id] = SKIP_SCOPE_EXCLUDED
            scope_dependency_paths[migration_id] = [migration_id]
            continue

        missing_dependencies = []
        scope_dependency_path: list[str] | None = None
        for dependency in migration.get("dependsOn", []):
            # An immutable legacy row is not proof that its replacement can run.
            dependency_id = supersession_owners.get(str(dependency), str(dependency))
            if dependency_id in satisfied_migrations:
                continue
            if dependency_id in scope_dependency_paths:
                candidate_path = [migration_id, *scope_dependency_paths[dependency_id]]
                if scope_dependency_path is None or len(candidate_path) < len(scope_dependency_path):
                    scope_dependency_path = candidate_path
                continue
            dependency_action = planned_actions.get(dependency_id)
            if dependency_action == SKIP_ENV_NOT_ALLOWED:
                missing_dependencies.append(f"{dependency_id} (skipped for environment)")
                continue
            if dependency_action is not None:
                missing_dependencies.append(f"{dependency_id} ({dependency_action})")
                continue
            if dependency_id in known_migrations:
                missing_dependencies.append(dependency_id)
                continue
            missing_dependencies.append(dependency_id)
        if scope_dependency_path is not None:
            items.append(
                _item(
                    migration,
                    "BLOCKED_SCOPE_DEPENDENCY",
                    f"publish scope {publish_scope} excludes required dependency path: "
                    + " -> ".join(scope_dependency_path),
                )
            )
            planned_actions[migration_id] = "BLOCKED_SCOPE_DEPENDENCY"
            scope_dependency_paths[migration_id] = scope_dependency_path
            continue
        if missing_dependencies:
            items.append(
                _item(
                    migration,
                    "BLOCKED_DEPENDENCY_MISSING",
                    "missing applied dependencies: " + ", ".join(missing_dependencies),
                )
            )
            planned_actions[migration_id] = "BLOCKED_DEPENDENCY_MISSING"
            continue

        items.append(_item(migration, "APPLY", "migration is pending and prerequisites are satisfied"))
        satisfied_migrations.add(migration_id)
        planned_actions[migration_id] = "APPLY"

    return {
        "planKind": "prospective",
        "status": "blocked" if any(item["action"] in BLOCKED_ACTIONS for item in items) else "passed",
        "targetEnvironment": target_environment,
        "publishScope": publish_scope,
        "items": items,
    }


def _normalize_sha256(value: object) -> str:
    text = str(value or "")
    return text.removeprefix("sha256:")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sql_without_release_metadata(value: bytes) -> bytes:
    return b"".join(
        line
        for line in value.splitlines(keepends=True)
        if not line.lstrip().startswith(b"-- release-migration:")
    )


def _load_json(path: Path) -> object:
    return read_json_evidence(path)


def _extract_migrations(manifest: object) -> list[dict[str, object]]:
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be a JSON object")
    database = manifest.get("database")
    if isinstance(database, dict) and "schemaMigrations" in database:
        migrations = database.get("schemaMigrations", [])
    else:
        migrations = manifest.get("schemaMigrations", manifest.get("requiredSql", []))
    if not isinstance(migrations, list):
        raise ValueError("manifest schema migrations must be an array")
    if any(not isinstance(migration, dict) for migration in migrations):
        raise ValueError("MIGRATION_INVALID: manifest migration entries must be objects")
    return migrations


def _normalize_target_state(raw_state: object) -> dict[str, dict[str, object]]:
    if not isinstance(raw_state, dict):
        raise ValueError("target state must be a JSON object")
    normalized: dict[str, dict[str, object]] = {}
    for migration_id, state in raw_state.items():
        if not isinstance(migration_id, str) or not migration_id.strip() or not isinstance(state, dict):
            raise ValueError("LEDGER_ENTRY_INVALID: each ledger entry requires migrationId and object state")
        checksum = _normalize_sha256(state.get("sha256"))
        if not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise ValueError(f"LEDGER_CHECKSUM_INVALID: {migration_id}")
        status = str(state.get("status", ""))
        normalized[migration_id] = {
            "status": "APPLIED" if status == "SKIPPED_ALREADY_APPLIED" else status,
            "sha256": checksum,
        }
    return normalized


def _attach_equivalent_sql_checksums(migrations: list[dict[str, object]], manifest_path: Path) -> None:
    package_root = manifest_path.parent
    for migration in migrations:
        relative_file = migration.get("file")
        if not relative_file:
            continue
        sql_path = (package_root / str(relative_file)).resolve()
        if not sql_path.is_relative_to(package_root.resolve()):
            raise ValueError("MIGRATION_PATH_INVALID: SQL escapes package root")
        if not sql_path.is_file():
            raise ValueError(f"MIGRATION_SQL_MISSING: {relative_file}")
        sql_bytes = sql_path.read_bytes()
        actual_checksum = _sha256_bytes(sql_bytes)
        if actual_checksum != _normalize_sha256(migration.get("sha256")):
            raise ValueError(f"MIGRATION_SQL_CHECKSUM_MISMATCH: {relative_file}")
        executable_bytes = _sql_without_release_metadata(sql_bytes)
        if executable_bytes == sql_bytes:
            continue
        executable_sha256 = _sha256_bytes(executable_bytes)
        if executable_sha256 != str(migration.get("sha256")):
            migration["sha256"] = _VerifiedMetadataChecksum(actual_checksum, executable_sha256)


def _file_digest(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"REQUIRED_INPUT_MISSING: {path.name}")
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _package_identity(manifest_path: Path, manifest: dict) -> dict[str, str]:
    """Recheck immutable bytes using the existing UTF-8 path/tab/size/digest contract."""
    root = manifest_path.parent.resolve()
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("PACKAGE_ARTIFACTS_REQUIRED")
    records = []
    seen = set()
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            raise ValueError("PACKAGE_ARTIFACT_INVALID")
        relative = _normalise_path(artifact.get("path"))
        folded = _ascii_case_fold(relative)
        if folded in seen:
            raise ValueError("PACKAGE_ARTIFACT_DUPLICATE")
        seen.add(folded)
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or path == manifest_path.resolve():
            raise ValueError("PACKAGE_PATH_INVALID: artifact must stay inside package")
        actual_sha256 = _file_digest(path)
        size = path.stat().st_size
        if type(artifact.get("bytes")) is not int or artifact["bytes"] != size or artifact.get("sha256") != actual_sha256:
            raise ValueError(f"PACKAGE_ARTIFACT_MISMATCH: {relative}")
        records.append((relative, size, actual_sha256))
    records.sort(key=lambda item: item[0].encode("utf-8"))
    calculated = _sha256_bytes("".join(f"{name}\t{size}\t{checksum}\n" for name, size, checksum in records).encode("utf-8"))
    if manifest.get("packageDigest") != calculated:
        raise ValueError("PACKAGE_DIGEST_MISMATCH")
    for migration in _extract_migrations(manifest):
        if _ascii_case_fold(_normalise_path(migration.get("file"))) not in seen:
            raise ValueError("MIGRATION_ARTIFACT_MISSING: every migration must be covered by packageDigest")
    release_tag = manifest.get("releaseTag")
    if not isinstance(release_tag, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", release_tag):
        raise ValueError("RELEASE_TAG_INVALID")
    return {"packageDigest": calculated, "manifestDigest": _file_digest(manifest_path), "releaseTag": release_tag}


def planner_identity() -> str:
    root = Path(__file__).resolve().parent
    names = ("release_preflight_plan.py", "release_target_state_collector.py", "release_deploy_executor.py", "release_digest.py")
    return evidence_digest({name: _file_digest(root / name) for name in names})


def build_target_bound_plan(
    manifest_path: Path | str,
    target_snapshot: dict,
    *,
    executor_path: Path | str,
    target_environment: str,
    publish_scope: str,
) -> dict[str, object]:
    manifest_path = Path(manifest_path).resolve()
    manifest = _load_json(manifest_path)
    if not isinstance(manifest, dict) or manifest.get("publishScope") != publish_scope:
        raise ValueError("MANIFEST_SCOPE_MISMATCH")
    identity = _package_identity(manifest_path, manifest)
    snapshot = normalize_target_snapshot(target_snapshot, target_environment=target_environment)
    requirements = manifest.get("targetRequirements", {}).get("platformPrerequisites", [])
    if not isinstance(requirements, list):
        raise ValueError("PACKAGE_PLATFORM_REQUIREMENTS_INVALID")
    required_tools = [requirement.get("toolId") for requirement in requirements if isinstance(requirement, dict)]
    if len(required_tools) != len(requirements) or len(required_tools) != len(set(required_tools)) or any(not item for item in required_tools):
        raise ValueError("PACKAGE_PLATFORM_REQUIREMENTS_INVALID")
    observed_tools = {item["toolId"] for item in snapshot["platformPrerequisites"]}
    if set(required_tools) - observed_tools:
        raise ValueError("TARGET_PLATFORM_PREREQUISITE_MISSING: collect every manifest-declared tool")
    migrations = deepcopy(_extract_migrations(manifest))
    for migration in migrations:
        migration["sha256"] = _normalize_sha256(migration.get("sha256"))
    _attach_equivalent_sql_checksums(migrations, manifest_path)
    ledger = {item["migrationId"]: item for item in snapshot["migrationLedger"]}
    plan = build_preflight_plan(migrations, ledger, target_environment=target_environment, publish_scope=publish_scope)
    plan.update({
        "schemaVersion": DEPLOY_PLAN_SCHEMA_VERSION,
        "planKind": "deploy",
        "binding": {
            **identity, "targetEnvironment": target_environment,
            "hostIdentity": snapshot["hostIdentity"], "databaseIdentity": snapshot["databaseIdentity"],
            "executorDigest": _file_digest(Path(executor_path)), "plannerDigest": planner_identity(),
            "capturedAt": snapshot["capturedAt"], "fingerprints": fingerprint_target_snapshot(snapshot),
        },
    })
    plan["planDigest"] = evidence_digest(plan)
    return plan


def verify_target_bound_plan(
    plan: dict,
    manifest_path: Path | str,
    target_snapshot: dict,
    *,
    executor_path: Path | str,
    target_environment: str,
    publish_scope: str,
) -> dict[str, object]:
    if not isinstance(plan, dict) or plan.get("schemaVersion") != DEPLOY_PLAN_SCHEMA_VERSION or plan.get("planKind") != "deploy":
        raise ValueError("TARGET_BOUND_PLAN_REQUIRED: prospective or legacy plans cannot authorize deployment")
    binding = plan.get("binding")
    if not isinstance(binding, dict):
        raise ValueError("TARGET_BOUND_PLAN_REQUIRED: binding is missing")
    validate_capture_time(binding.get("capturedAt"))
    payload = {key: value for key, value in plan.items() if key != "planDigest"}
    if plan.get("planDigest") != evidence_digest(payload):
        raise ValueError("PLAN_DIGEST_MISMATCH")
    expected = build_target_bound_plan(manifest_path, target_snapshot, executor_path=executor_path,
                                      target_environment=target_environment, publish_scope=publish_scope)
    expected_payload = deepcopy({key: value for key, value in expected.items() if key != "planDigest"})
    # Recollection has a new time; all target evidence and the ordered actions must remain identical.
    comparable = deepcopy(payload)
    comparable["binding"].pop("capturedAt")
    expected_payload["binding"].pop("capturedAt")
    if comparable != expected_payload:
        raise ValueError("PLAN_INPUT_DRIFT: package, target state, executor, planner or ordered actions changed")
    if plan.get("status") != "passed":
        raise ValueError("PLAN_BLOCKED: target plan is not executable")
    return expected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--target-state", required=True)
    parser.add_argument("--target-environment", required=True)
    parser.add_argument("--publish-scope", required=True, choices=sorted(SUPPORTED_PUBLISH_SCOPES))
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=("deploy", "prospective"), default="deploy")
    parser.add_argument("--executor")
    parser.add_argument("--verify", action="store_true", help="verify the existing output against freshly collected target inputs")
    args = parser.parse_args(argv)

    manifest_path = Path(args.manifest)
    output_path = Path(args.output).resolve()
    if output_path.is_relative_to(manifest_path.resolve().parent):
        raise ValueError("PLAN_OUTPUT_INSIDE_PACKAGE: plans must be written outside the immutable package")
    if args.mode == "deploy":
        if not args.executor:
            raise ValueError("TARGET_BOUND_PLAN_REQUIRED: --executor is required for deploy planning")
        inputs = dict(executor_path=args.executor, target_environment=args.target_environment, publish_scope=args.publish_scope)
        snapshot = _load_json(Path(args.target_state))
        if args.verify:
            verify_target_bound_plan(_load_json(output_path), manifest_path, snapshot, **inputs)
            return 0
        plan = build_target_bound_plan(manifest_path, snapshot, **inputs)
        output_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if plan["status"] == "passed" else 2
    if args.verify or args.executor:
        raise ValueError("PROSPECTIVE_MODE_INVALID: use release_build_preflight.py for prospective evidence verification")
    manifest = _load_json(manifest_path)
    target_state = _normalize_target_state(_load_json(Path(args.target_state)))
    migrations = _extract_migrations(manifest)
    for migration in migrations:
        if "sha256" in migration:
            migration["sha256"] = _normalize_sha256(migration["sha256"])
    _attach_equivalent_sql_checksums(migrations, manifest_path)

    plan = build_preflight_plan(
        migrations,
        target_state,
        target_environment=args.target_environment,
        publish_scope=args.publish_scope,
    )
    output_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if plan["status"] == "passed" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2)
