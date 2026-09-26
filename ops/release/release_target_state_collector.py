"""Validate read-only target evidence without reading or hashing secret-bearing .env."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit


TARGET_STATE_SCHEMA_VERSION = "release-deploy-target-state/v1"
NON_SECRET_CONFIG_KEYS = frozenset({
    "COMPOSE_PROJECT_NAME", "MYSQL_DATABASE", "REDIS_DATABASE", "MINIO_ENDPOINT",
    "EDHR_STORAGE_ENDPOINT", "EDHR_STORAGE_BUCKET", "EDHR_STORAGE_REGION", "EDHR_STORAGE_SECURE",
    "BACKEND_PORT", "FRONTEND_PORT", "WEBSITE_PORT", "ONLYOFFICE_PORT",
    "REMOTE_APP_DIR", "DATA_ROOT", "IMAGE_TAG",
})
LEDGER_FIELDS = frozenset({"migrationId", "sha256", "status", "releaseTag", "file", "operationId", "startedAt", "finishedAt"})


class TargetStateCollectionError(ValueError):
    pass


def read_json_evidence(path: Path | str) -> object:
    def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise TargetStateCollectionError("JSON_DUPLICATE_KEY: input must not shadow previously declared keys")
            result[key] = value
        return result

    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def evidence_digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip() or any(ord(char) < 32 for char in value):
        raise TargetStateCollectionError(f"TARGET_EVIDENCE_INVALID: {label} must be a non-empty string")
    return value


def validate_capture_time(value: object) -> str:
    value = _text(value, "capturedAt")
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TargetStateCollectionError("TARGET_CAPTURE_TIME_INVALID: capturedAt must be UTC ISO-8601") from exc
    if not value.endswith("Z") or timestamp.utcoffset() is None or timestamp.utcoffset().total_seconds() != 0:
        raise TargetStateCollectionError("TARGET_CAPTURE_TIME_INVALID: capturedAt must be UTC ISO-8601")
    return value


def _identity(raw: object, fields: tuple[str, ...], label: str) -> dict[str, str]:
    if not isinstance(raw, dict) or set(raw) != set(fields):
        raise TargetStateCollectionError(f"TARGET_IDENTITY_INVALID: {label} requires {','.join(fields)}")
    return {field: _text(raw[field], f"{label}.{field}") for field in fields}


def normalize_target_snapshot(raw: object, *, target_environment: str) -> dict[str, object]:
    if not isinstance(raw, dict) or raw.get("schemaVersion") != TARGET_STATE_SCHEMA_VERSION:
        raise TargetStateCollectionError(f"TARGET_SNAPSHOT_REQUIRED: schemaVersion must be {TARGET_STATE_SCHEMA_VERSION}")
    expected_fields = {"schemaVersion", "capturedAt", "targetEnvironment", "hostIdentity", "databaseIdentity",
                       "schemaEvidence", "migrationLedgerComplete", "migrationLedger", "nonSecretConfig",
                       "persistentMounts", "platformPrerequisites"}
    if set(raw) != expected_fields:
        raise TargetStateCollectionError("TARGET_SNAPSHOT_FIELDS_INVALID: complete declared evidence fields are required")
    if target_environment not in {"test", "prod", "backup"} or raw["targetEnvironment"] != target_environment:
        raise TargetStateCollectionError("TARGET_ENVIRONMENT_MISMATCH")
    captured_at = validate_capture_time(raw["capturedAt"])
    host = _identity(raw["hostIdentity"], ("host", "machineId"), "hostIdentity")
    database = _identity(raw["databaseIdentity"], ("name", "serverUuid"), "databaseIdentity")
    if not re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", database["serverUuid"]):
        raise TargetStateCollectionError("TARGET_DATABASE_IDENTITY_INVALID: serverUuid must be actual MySQL UUID")
    schema = raw["schemaEvidence"]
    if not isinstance(schema, dict) or not schema:
        raise TargetStateCollectionError("TARGET_SCHEMA_EVIDENCE_MISSING")
    if raw["migrationLedgerComplete"] is not True or not isinstance(raw["migrationLedger"], list):
        raise TargetStateCollectionError("TARGET_COMPLETE_LEDGER_REQUIRED: collect every relevant status as an array")
    ledger = []
    seen = set()
    for row in raw["migrationLedger"]:
        if not isinstance(row, dict) or not {"migrationId", "sha256", "status"} <= set(row) or set(row) - LEDGER_FIELDS:
            raise TargetStateCollectionError("LEDGER_ENTRY_INVALID: expected non-secret migration metadata")
        migration_id = _text(row["migrationId"], "migrationId")
        if migration_id in seen:
            raise TargetStateCollectionError(f"LEDGER_ID_DUPLICATE: {migration_id}")
        seen.add(migration_id)
        checksum = str(row["sha256"]).removeprefix("sha256:")
        if not re.fullmatch(r"[0-9a-f]{64}", checksum):
            raise TargetStateCollectionError(f"LEDGER_CHECKSUM_INVALID: {migration_id}")
        if not isinstance(row["status"], str):
            raise TargetStateCollectionError(f"LEDGER_STATUS_INVALID: {migration_id}")
        ledger.append({**row, "sha256": checksum})
    ledger.sort(key=lambda item: item["migrationId"])
    config = raw["nonSecretConfig"]
    if not isinstance(config, dict) or not config or set(config) - NON_SECRET_CONFIG_KEYS:
        raise TargetStateCollectionError("TARGET_CONFIG_NOT_ALLOWLISTED: collect only declared non-secret configuration")
    for name, value in config.items():
        _text(value, f"nonSecretConfig.{name}")
        if name.endswith("ENDPOINT"):
            endpoint = urlsplit(value)
            if endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
                raise TargetStateCollectionError("TARGET_CONFIG_CONTAINS_SECRET: endpoint must exclude credentials/query/fragment")
    if config.get("MYSQL_DATABASE") != database["name"]:
        raise TargetStateCollectionError("TARGET_DATABASE_CONFIG_MISMATCH")
    mounts = raw["persistentMounts"]
    if not isinstance(mounts, list) or not mounts:
        raise TargetStateCollectionError("TARGET_PERSISTENT_MOUNTS_MISSING")
    normalized_mounts = []
    seen_roles = set()
    for mount in mounts:
        value = _identity(mount, ("role", "type", "source", "destination", "identity"), "persistentMounts")
        if value["role"] in seen_roles or value["type"] not in {"bind", "volume"} or not value["destination"].startswith("/"):
            raise TargetStateCollectionError("TARGET_MOUNT_IDENTITY_INVALID")
        if value["type"] == "bind" and not value["source"].startswith("/"):
            raise TargetStateCollectionError("TARGET_MOUNT_IDENTITY_INVALID: bind source must be absolute")
        seen_roles.add(value["role"])
        normalized_mounts.append(value)
    if "mysql" not in seen_roles:
        raise TargetStateCollectionError("TARGET_MYSQL_MOUNT_MISSING")
    normalized_mounts.sort(key=lambda item: item["role"])
    prerequisites = raw["platformPrerequisites"]
    if not isinstance(prerequisites, list):
        raise TargetStateCollectionError("TARGET_PLATFORM_EVIDENCE_MISSING")
    platforms = []
    names = set()
    for prerequisite in prerequisites:
        if not isinstance(prerequisite, dict) or prerequisite.get("executable") is not True:
            raise TargetStateCollectionError("TARGET_PLATFORM_NOT_EXECUTABLE")
        value = _identity({key: val for key, val in prerequisite.items() if key != "executable"},
                          ("toolId", "path", "approvedSha256", "actualSha256"), "platformPrerequisites")
        if (value["toolId"] in names or not re.fullmatch(r"[0-9a-f]{64}", value["approvedSha256"])
                or value["actualSha256"] != value["approvedSha256"] or not value["path"].startswith("/")):
            raise TargetStateCollectionError("TARGET_PLATFORM_IDENTITY_INVALID")
        names.add(value["toolId"])
        platforms.append({**value, "executable": True})
    platforms.sort(key=lambda item: item["toolId"])
    return {
        "schemaVersion": TARGET_STATE_SCHEMA_VERSION, "capturedAt": captured_at,
        "targetEnvironment": target_environment, "hostIdentity": host, "databaseIdentity": database,
        "schemaEvidence": schema, "migrationLedgerComplete": True, "migrationLedger": ledger,
        "nonSecretConfig": config, "persistentMounts": normalized_mounts, "platformPrerequisites": platforms,
    }


def fingerprint_target_snapshot(snapshot: dict[str, object]) -> dict[str, str]:
    """Collection time is evidence, not part of the semantic drift comparison."""
    fields = ("schemaEvidence", "migrationLedger", "nonSecretConfig", "persistentMounts", "platformPrerequisites")
    fingerprints = {field: evidence_digest(snapshot[field]) for field in fields}
    fingerprints["targetState"] = evidence_digest({key: value for key, value in snapshot.items() if key != "capturedAt"})
    return fingerprints


def collect_target_state(target_root: Path | str, *, target_environment: str) -> dict[str, object]:
    """Load the collector's explicit snapshot; no legacy .env hashing or inferred state."""
    path = Path(target_root).resolve() / "target-state.json"
    if not path.is_file():
        raise TargetStateCollectionError("TARGET_SNAPSHOT_MISSING: read-only target-state.json collection is required")
    return normalize_target_snapshot(read_json_evidence(path), target_environment=target_environment)
