#!/usr/bin/env python3
import argparse
import copy
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set, Tuple


SUPPORTED_MODES = {"backup-now", "backup-scheduled", "restore-data", "rollback-app", "rehearsal"}


class BackupOpsError(RuntimeError):
    def __init__(self, code: str, status: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.message = message


def now_sequence() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def backup_sequence() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def is_backup_point_name(name: str) -> bool:
    return re.fullmatch(r"\d{8}-\d{6}", name) is not None


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def require_executable(path: str, code: str, message: str) -> str:
    executable = Path(path)
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise BackupOpsError(code, "blocked", message)
    return str(executable)


CP_PATH = "/bin/cp"



def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def get_required(obj: dict, path: list, field_name: str) -> str:
    current = obj
    for segment in path:
        if not isinstance(current, dict) or segment not in current:
            raise BackupOpsError("INTBK-1003", "blocked", f"Required configuration is missing: {field_name}")
        current = current[segment]
    if current is None or (isinstance(current, str) and not current.strip()):
        raise BackupOpsError("INTBK-1003", "blocked", f"Required configuration is missing: {field_name}")
    return current


def get_optional_string(obj: dict, path: list, default: str = "") -> str:
    current = obj
    for segment in path:
        if not isinstance(current, dict) or segment not in current:
            return default
        current = current[segment]
    if current is None:
        return default
    text = str(current).strip()
    return text or default


def is_truthy_config(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def resolve_mysql_backup_mode(config: dict) -> str:
    explicit_mode = get_optional_string(config, ["backup", "mysqlBackupMode"])
    if explicit_mode:
        return explicit_mode.lower()
    mysql_incremental = config.get("backup", {}).get("mysqlIncremental", {})
    if isinstance(mysql_incremental, dict) and is_truthy_config(mysql_incremental.get("enabled")):
        return get_optional_string(config, ["backup", "mysqlIncremental", "strategy"], "incremental").lower()
    return "full-dump-baseline"


def assert_mysql_backup_mode_supported(config: dict, workspace: Optional[Path] = None) -> str:
    mode = resolve_mysql_backup_mode(config)
    if mode in {"full-dump-baseline", "full-dump", "logical-full-dump"}:
        return mode
    if mode.startswith("binlog"):
        segment_manifest_path = workspace / "mysql" / "binlog-segment-manifest.json" if workspace is not None else None
        if segment_manifest_path is not None and segment_manifest_path.is_file():
            return mode
        raise BackupOpsError(
            "INTBK-6001",
            "blocked",
            "MySQL incremental backup requested: "
            f"mysqlBackupMode={mode}. mysql/binlog-segment-manifest.json is required before writing a success "
            "backup manifest. No silent full dump fallback is allowed for an incremental MySQL backup request.",
        )
    raise BackupOpsError(
        "INTBK-6001",
        "blocked",
        "MySQL incremental backup requested: "
        f"mysqlBackupMode={mode}. Current backup flow only supports binlog segment evidence before manifest success. "
        "No silent full dump fallback is allowed for an incremental MySQL backup request.",
    )


def build_backup_strategy(mysql_backup_mode: str, workspace: Optional[Path] = None) -> dict:
    strategy = {
        "mode": "incremental-manifest",
        "mysqlBackupMode": mysql_backup_mode,
        "mysqlBaseline": "full-dump",
        "mysqlIncrementalPlan": {
            "binlog": {
                "status": "requires-prerequisite",
                "required": [
                    "log_bin=ON",
                    "ROW binlog_format",
                    "REPLICATION CLIENT or equivalent binlog read permission",
                    "mysqlbinlog available",
                ],
                "requiredEvidence": [
                    "binlogEnabled",
                    "binlogFormatRow",
                    "binlogPosition",
                    "binlogRetentionWindow",
                    "mysqlbinlogExecutable",
                    "restoreReplayRehearsal",
                ],
                "failFastRule": (
                    "Do not claim binlog incremental backup until every prerequisite is proven on the target environment."
                ),
            },
            "xtrabackup": {
                "status": "requires-prerequisite",
                "required": [
                    "Percona XtraBackup installed",
                    "physical backup volume path available",
                    "backup user has required privileges",
                    "restore rehearsal storage sized for physical backup",
                ],
                "requiredEvidence": [
                    "xtrabackupExecutable",
                    "xtrabackupCheckpoint",
                    "physicalBackupVolume",
                    "backupLockPrivilege",
                    "restorePrepareRehearsal",
                ],
                "failFastRule": "Do not claim physical incremental backup until dependency and privilege checks pass.",
            },
            "noFallbackRule": "No silent full dump fallback is allowed for an incremental MySQL backup request.",
        },
    }
    if mysql_backup_mode.startswith("binlog") and workspace is not None:
        preflight_path = workspace / "mysql" / "binlog-preflight.json"
        segment_manifest_path = workspace / "mysql" / "binlog-segment-manifest.json"
        if segment_manifest_path.is_file():
            segment_manifest = read_json(segment_manifest_path)
            preflight = read_json(preflight_path) if preflight_path.is_file() else {}
            evidence = preflight.get("evidence", {}) if isinstance(preflight.get("evidence"), dict) else {}
            strategy["mysqlIncrementalPlan"]["binlog"] = {
                "status": "requires-rehearsal",
                "required": [
                    "binlog segment exported",
                    "restore rehearsal replay passed",
                ],
                "requiredEvidence": [
                    "binlogPosition",
                    "binlogSegmentManifest",
                    "restoreReplayRehearsal",
                ],
                "evidence": {
                    "binlogEnabled": str(evidence.get("binlogEnabled", "") or ""),
                    "binlogFormat": str(evidence.get("binlogFormat", "") or ""),
                    "binlogPosition": str(evidence.get("binlogPosition", "") or ""),
                    "binlogRetentionWindow": str(evidence.get("binlogRetentionWindow", "") or ""),
                    "mysqlbinlogExecutable": "verified-by-export",
                    "restoreReplayRehearsal": "not-run",
                },
                "segmentManifestPath": "mysql/binlog-segment-manifest.json",
                "segmentStatus": str(segment_manifest.get("status", "") or ""),
                "replayStatus": str(segment_manifest.get("replayStatus", "") or "not-run"),
                "failFastRule": "Do not allow restore-data until rehearsal replays binlog segments and writes replay evidence.",
            }
    return strategy


def write_mysql_binlog_preflight(workspace: Path, config: dict, runner: "Runner", mysql_container: str, mysql_password: str) -> dict:
    command = (
        "docker exec {0} sh -lc {1}".format(
            shlex.quote(mysql_container),
            shlex.quote(
                "mysql -uroot -p{0} -N -B -e {1}".format(
                    shlex.quote(mysql_password),
                    shlex.quote(
                        "SELECT @@global.log_bin, @@global.binlog_format, @@global.binlog_expire_logs_seconds; "
                        "SHOW MASTER STATUS;"
                    ),
                )
            ),
        )
    )
    output = runner.run(command, "INTBK-6001", "MySQL binlog preflight query failed.")
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if len(lines) < 2:
        raise BackupOpsError("INTBK-6001", "blocked", "MySQL binlog preflight output is incomplete.")
    variables = lines[0].split("\t")
    position = lines[1].split("\t")
    if len(variables) < 3 or len(position) < 2:
        raise BackupOpsError("INTBK-6001", "blocked", "MySQL binlog preflight output format is invalid.")
    evidence = {
        "binlogEnabled": variables[0],
        "binlogFormat": variables[1],
        "binlogRetentionWindow": variables[2],
        "binlogPosition": f"{position[0]}:{position[1]}",
        "mysqlbinlogExecutable": "not-verified",
        "restoreReplayRehearsal": "not-run",
    }
    if evidence["binlogEnabled"] not in {"1", "ON", "on", "TRUE", "true"}:
        raise BackupOpsError("INTBK-6001", "blocked", "MySQL binlog preflight failed: log_bin is not enabled.")
    if evidence["binlogFormat"].upper() != "ROW":
        raise BackupOpsError("INTBK-6001", "blocked", f"MySQL binlog preflight failed: binlog_format={evidence['binlogFormat']} is not ROW.")
    payload = {
        "schemaVersion": "mysql-binlog-preflight-v1",
        "status": "preflight-passed",
        "mode": "binlog-incremental",
        "evidence": evidence,
        "blockedReason": "binlog export and restore replay are not implemented yet; no silent full dump fallback is allowed.",
    }
    output_path = workspace / "mysql" / "binlog-preflight.json"
    ensure_dir(output_path.parent)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def export_mysql_binlog_segment(workspace: Path, runner: "Runner", mysql_container: str, mysql_password: str, preflight: dict) -> dict:
    evidence = preflight.get("evidence")
    if not isinstance(evidence, dict):
        raise BackupOpsError("INTBK-6001", "blocked", "MySQL binlog segment export requires preflight evidence.")
    position = str(evidence.get("binlogPosition", "") or "")
    match = re.fullmatch(r"([^:]+):(\d+)", position)
    if not match:
        raise BackupOpsError("INTBK-6001", "blocked", f"MySQL binlog preflight position is invalid: {position}")
    binlog_file = match.group(1)
    stop_position = int(match.group(2))
    start_position = 4
    output_dir = workspace / "mysql" / "binlog"
    ensure_dir(output_dir)
    output_path = output_dir / f"{binlog_file}.sql"
    command = (
        "docker exec {0} sh -lc {1} > {2}".format(
            shlex.quote(mysql_container),
            shlex.quote(
                "mysqlbinlog --read-from-remote-server --host=127.0.0.1 --user=root --password={0} "
                "--start-position={1} --stop-position={2} {3}".format(
                    shlex.quote(mysql_password),
                    start_position,
                    stop_position,
                    shlex.quote(binlog_file),
                )
            ),
            shlex.quote(str(output_path)),
        )
    )
    runner.run(command, "INTBK-6001", "MySQL binlog segment export failed.")
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise BackupOpsError("INTBK-6001", "blocked", f"MySQL binlog segment export produced an empty file: {output_path}")
    segment = {
        "schemaVersion": "mysql-binlog-segment-v1",
        "status": "exported",
        "mode": "binlog-incremental",
        "replayStatus": "not-run",
        "segments": [
            {
                "binlogFile": binlog_file,
                "path": f"mysql/binlog/{binlog_file}.sql",
                "startPosition": start_position,
                "stopPosition": stop_position,
                "sha256": sha256_file(output_path),
            }
        ],
        "blockedReason": "restore replay is not implemented yet; no silent full dump fallback is allowed.",
    }
    manifest_path = workspace / "mysql" / "binlog-segment-manifest.json"
    manifest_path.write_text(json.dumps(segment, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return segment


def replay_mysql_binlog_segments(backup_root: Path, runner: "Runner", mysql_container: str, mysql_password: str, db_name: str) -> dict:
    manifest_path = backup_root / "mysql" / "binlog-segment-manifest.json"
    if not manifest_path.is_file():
        return {"status": "not-applicable", "segments": []}
    manifest = read_json(manifest_path)
    if manifest.get("schemaVersion") != "mysql-binlog-segment-v1":
        raise BackupOpsError("INTBK-7001", "blocked", "MySQL binlog segment manifest schemaVersion is invalid.")
    replayed_segments = []
    for segment in as_manifest_list(manifest.get("segments")):
        if not isinstance(segment, dict):
            raise BackupOpsError("INTBK-7001", "blocked", "MySQL binlog segment manifest contains an invalid segment.")
        relative_path = normalize_dcc_object_path(str(segment.get("path", "") or ""))
        if not relative_path:
            raise BackupOpsError("INTBK-7001", "blocked", "MySQL binlog segment path is missing.")
        segment_path = backup_root / Path(relative_path)
        if not segment_path.is_file():
            raise BackupOpsError("INTBK-7001", "blocked", f"MySQL binlog segment file is missing: {relative_path}")
        expected_sha = str(segment.get("sha256", "") or "")
        actual_sha = sha256_file(segment_path)
        if expected_sha and expected_sha != actual_sha:
            raise BackupOpsError("INTBK-7001", "blocked", f"MySQL binlog segment checksum mismatch: {relative_path}")
        runner.run(
            "cat {0} | docker exec -i {1} mysql -uroot -p{2} {3}".format(
                shlex.quote(str(segment_path)),
                shlex.quote(mysql_container),
                shlex.quote(mysql_password),
                shlex.quote(db_name),
            ),
            "INTBK-7001",
            "Failed to replay MySQL binlog segment.",
        )
        replayed_at = datetime.now().isoformat()
        segment["replayStatus"] = "passed"
        segment["replayedAt"] = replayed_at
        replayed_segments.append(
            {
                "path": relative_path,
                "sha256": actual_sha,
                "replayedAt": replayed_at,
            }
        )
    manifest["replayStatus"] = "passed"
    manifest["replayedAt"] = datetime.now().isoformat()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": "passed", "segments": replayed_segments}


def read_env_lines(env_path: Path) -> list:
    return env_path.read_text(encoding="utf-8").splitlines()


def get_env_value(lines: list, key: str) -> str:
    prefix = key + "="
    for line in lines:
        if line.startswith(prefix):
            return line[len(prefix):]
    return ""


def get_required_runtime_port(lines: list, key: str, code: str) -> int:
    value = get_env_value(lines, key)
    if not value.strip():
        raise BackupOpsError(code, "blocked", f"Missing {key} in runtime .env")
    try:
        return int(value.strip())
    except ValueError as exc:
        raise BackupOpsError(code, "blocked", f"Invalid {key} in runtime .env: {value}") from exc


def assert_restore_recovery_set_scope(recovery_set: dict, current_image_tag: str) -> None:
    program = recovery_set.get("program")
    if not isinstance(program, dict) or not str(program.get("imageTag", "")).strip():
        raise BackupOpsError("INTBK-3002", "blocked", "Restore manifest recoverySet.program.imageTag is missing.")
    recovery_image_tag = str(program["imageTag"]).strip()
    current_image_tag = current_image_tag.strip()
    if not current_image_tag:
        raise BackupOpsError("INTBK-3002", "blocked", "Current runtime IMAGE_TAG is missing; restore-data cannot prove program compatibility.")
    if recovery_image_tag != current_image_tag:
        raise BackupOpsError(
            "INTBK-3002",
            "blocked",
            "Restore manifest recoverySet.program.imageTag {0} does not match current runtime IMAGE_TAG {1}.".format(
                recovery_image_tag,
                current_image_tag,
            ),
        )
    redis = recovery_set.get("redis")
    if not isinstance(redis, dict) or not str(redis.get("policy", "")).strip():
        raise BackupOpsError("INTBK-3002", "blocked", "Restore manifest recoverySet.redis.policy is missing.")
    configuration = recovery_set.get("configuration")
    if not isinstance(configuration, dict) or not str(configuration.get("manifestPath", "")).strip():
        raise BackupOpsError("INTBK-3002", "blocked", "Restore manifest recoverySet.configuration.manifestPath is missing.")
    if not str(configuration.get("composePath", "")).strip():
        raise BackupOpsError("INTBK-3002", "blocked", "Restore manifest recoverySet.configuration.composePath is missing.")


def assert_restore_manifest_rehearsed(manifest: dict) -> None:
    validation = manifest.get("validation")
    if not isinstance(validation, dict):
        raise BackupOpsError(
            "INTBK-3002",
            "blocked",
            "backupManifest validation.rehearsalStatus must be PASSED and lastRehearsedAt must be present before restore-data.",
        )
    rehearsal_status = str(validation.get("rehearsalStatus", "")).strip()
    last_rehearsed_at = str(validation.get("lastRehearsedAt", "") or "").strip()
    if rehearsal_status not in {"PASSED", "passed", "pass"} or not last_rehearsed_at:
        raise BackupOpsError(
            "INTBK-3002",
            "blocked",
            "backupManifest validation.rehearsalStatus must be PASSED and lastRehearsedAt must be present before restore-data.",
        )


def assert_restore_manifest_backup_strategy(manifest: dict) -> None:
    backup_strategy = manifest.get("backupStrategy")
    if not isinstance(backup_strategy, dict):
        raise BackupOpsError("INTBK-3002", "blocked", "Restore manifest backupStrategy is missing.")
    if not str(backup_strategy.get("mode", "")).strip():
        raise BackupOpsError("INTBK-3002", "blocked", "Restore manifest backupStrategy.mode is missing.")
    mysql_backup_mode = str(backup_strategy.get("mysqlBackupMode", "")).strip().lower()
    if not mysql_backup_mode:
        raise BackupOpsError("INTBK-3002", "blocked", "Restore manifest backupStrategy.mysqlBackupMode is missing.")
    if mysql_backup_mode in {"full-dump-baseline", "full-dump", "logical-full-dump"}:
        return
    incremental_plan = backup_strategy.get("mysqlIncrementalPlan")
    if not isinstance(incremental_plan, dict):
        raise BackupOpsError(
            "INTBK-3002",
            "blocked",
            f"Restore manifest mysqlBackupMode={mysql_backup_mode} requires backupStrategy.mysqlIncrementalPlan.",
        )
    if mysql_backup_mode.startswith("binlog"):
        assert_restore_mysql_incremental_plan_ready(
            incremental_plan,
            "binlog",
            mysql_backup_mode,
            ["binlogPosition", "binlogRetentionWindow", "mysqlbinlogExecutable", "restoreReplayRehearsal"],
        )
        return
    if mysql_backup_mode.startswith("xtrabackup"):
        assert_restore_mysql_incremental_plan_ready(
            incremental_plan,
            "xtrabackup",
            mysql_backup_mode,
            ["xtrabackupExecutable", "xtrabackupCheckpoint", "physicalBackupVolume", "backupLockPrivilege", "restorePrepareRehearsal"],
        )
        return
    raise BackupOpsError(
        "INTBK-3002",
        "blocked",
        f"Restore manifest mysqlBackupMode={mysql_backup_mode} is unsupported; no silent full dump fallback is allowed.",
    )


def assert_restore_mysql_incremental_plan_ready(
    incremental_plan: dict,
    plan_key: str,
    mysql_backup_mode: str,
    required_evidence: List[str],
) -> None:
    plan = incremental_plan.get(plan_key)
    if not isinstance(plan, dict):
        raise BackupOpsError(
            "INTBK-3002",
            "blocked",
            f"Restore manifest mysqlBackupMode={mysql_backup_mode} requires mysqlIncrementalPlan.{plan_key}.",
        )
    status = str(plan.get("status", "")).strip().lower()
    if status not in {"ready", "complete", "verified"}:
        raise BackupOpsError(
            "INTBK-3002",
            "blocked",
            "Restore manifest mysqlBackupMode={0} has mysqlIncrementalPlan.{1}.status={2}; required evidence: {3}.".format(
                mysql_backup_mode,
                plan_key,
                status or "missing",
                ", ".join(required_evidence),
            ),
        )
    evidence = plan.get("evidence")
    if not isinstance(evidence, dict):
        raise BackupOpsError(
            "INTBK-3002",
            "blocked",
            "Restore manifest mysqlBackupMode={0} requires mysqlIncrementalPlan.{1}.evidence: {2}.".format(
                mysql_backup_mode,
                plan_key,
                ", ".join(required_evidence),
            ),
        )
    missing = [key for key in required_evidence if not str(evidence.get(key, "") or "").strip()]
    if missing:
        raise BackupOpsError(
            "INTBK-3002",
            "blocked",
            "Restore manifest mysqlBackupMode={0} missing mysqlIncrementalPlan.{1}.evidence: {2}.".format(
                mysql_backup_mode,
                plan_key,
                ", ".join(missing),
            ),
        )


def as_manifest_list(value: object) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def dcc_event_exists(manifest: dict, restore_point_id: str, file_key: str, event_type: str) -> bool:
    for event in as_manifest_list(manifest.get("dccEvents")):
        if not isinstance(event, dict):
            continue
        if (
            str(event.get("restorePointId", "")) == restore_point_id
            and str(event.get("fileKey", "")) == file_key
            and str(event.get("eventType", "")) == event_type
        ):
            return True
    return False


def is_sha256_manifest_value(value: str) -> bool:
    return bool(re.match(r"^sha256:[0-9a-fA-F]{64}$", str(value or "")))


def validate_dcc_backup_manifest_contract(manifest: dict) -> List[str]:
    errors: List[str] = []
    if manifest.get("targetEnvironment") != "test":
        errors.append("target_environment_invalid")
    if manifest.get("schemaVersion") != "dcc-backup-manifest-v1":
        errors.append("schema_version_invalid")
    if manifest.get("chainStatus") != "COMPLETE":
        errors.append("chain_status_incomplete")
    if manifest.get("backupMode") == "incremental":
        if (
            not str(manifest.get("baselineBackupId", "") or "").strip()
            or not str(manifest.get("baselineRestorePointId", "") or "").strip()
            or not str(manifest.get("previousBackupId", "") or "").strip()
            or not str(manifest.get("previousRestorePointId", "") or "").strip()
        ):
            errors.append("previous_pointer_missing")

    if manifest.get("restoreVerified") is True:
        rehearsal = manifest.get("restoreRehearsal")
        if not isinstance(rehearsal, dict) or str(rehearsal.get("status", "")) != "passed":
            errors.append("restore_rehearsal_missing")

    full_baseline = manifest.get("fullBaseline")
    expected_from = ""
    if isinstance(full_baseline, dict):
        expected_from = str(full_baseline.get("restorePointId", "") or "")
        baseline_checksum = str(full_baseline.get("checksum", "") or "")
        if not is_sha256_manifest_value(baseline_checksum):
            errors.append("baseline_checksum_invalid")
    if not expected_from.strip():
        errors.append("full_baseline_missing")
        return errors

    seen_targets: Set[str] = set()
    for segment in as_manifest_list(manifest.get("incrementalChain")):
        if not isinstance(segment, dict):
            errors.append("incremental_chain_broken")
            return errors
        from_point = str(segment.get("from", "") or "")
        to_point = str(segment.get("to", "") or "")
        checksum = str(segment.get("checksum", "") or "")
        if not is_sha256_manifest_value(checksum):
            errors.append("segment_checksum_invalid")
            return errors
        if from_point != expected_from or not to_point.strip() or not checksum.strip() or to_point in seen_targets:
            errors.append("incremental_chain_broken")
            return errors
        seen_targets.add(to_point)
        expected_from = to_point

    inventory_by_restore_point = {}
    for inventory in as_manifest_list(manifest.get("objectInventories")):
        if isinstance(inventory, dict):
            restore_point_id = str(inventory.get("restorePointId", "") or "")
            if restore_point_id:
                inventory_by_restore_point[restore_point_id] = inventory

    for restore_point in as_manifest_list(manifest.get("restorePoints")):
        if not isinstance(restore_point, dict):
            continue
        restore_point_id = str(restore_point.get("id", "") or "")
        if not restore_point_id:
            continue
        if (
            str(restore_point.get("databaseRestorePointId", "") or "") != restore_point_id
            or str(restore_point.get("objectInventoryRestorePointId", "") or "") != restore_point_id
        ):
            errors.append("restore_point_inconsistent")
        if restore_point_id not in inventory_by_restore_point:
            errors.append("object_inventory_missing")

    for inventory in as_manifest_list(manifest.get("objectInventories")):
        if not isinstance(inventory, dict):
            continue
        restore_point_id = str(inventory.get("restorePointId", "") or "")
        for dcc_object in as_manifest_list(inventory.get("objects")):
            if not isinstance(dcc_object, dict):
                continue
            file_key = str(dcc_object.get("fileKey", "") or "")
            state = str(dcc_object.get("state", "") or "")
            content_hash = str(dcc_object.get("contentHash", "") or "")
            stored_hash = str(dcc_object.get("storedHash", "") or "")
            if state == "active":
                if dcc_object.get("present") is not True:
                    errors.append("object_missing")
                if content_hash != stored_hash:
                    errors.append("object_hash_mismatch")
            if state == "deleted" and not dcc_event_exists(manifest, restore_point_id, file_key, "delete"):
                errors.append("dcc_delete_event_missing")
            if state == "voided" and not dcc_event_exists(manifest, restore_point_id, file_key, "void"):
                errors.append("void_event_missing")
            if state == "archived" and not dcc_event_exists(manifest, restore_point_id, file_key, "archive"):
                errors.append("archive_event_missing")

    for record in as_manifest_list(manifest.get("databaseRecords")):
        if not isinstance(record, dict) or record.get("permissionChanged") is not True:
            continue
        restore_point_id = str(record.get("restorePointId", "") or "")
        file_key = str(record.get("fileKey", "") or "")
        if not dcc_event_exists(manifest, restore_point_id, file_key, "permission_change"):
            errors.append("permission_event_missing")

    return errors


def assert_restore_dcc_manifest_scope(recovery_set: dict, backup_root: Path) -> None:
    dcc = recovery_set.get("dcc")
    if not isinstance(dcc, dict) or not str(dcc.get("manifestPath", "")).strip():
        raise BackupOpsError("INTBK-3002", "blocked", "Restore manifest recoverySet.dcc.manifestPath is missing.")
    manifest_relative_path = str(dcc["manifestPath"]).strip()
    if manifest_relative_path != "manifest/dcc-backup-manifest.json":
        raise BackupOpsError(
            "INTBK-3002",
            "blocked",
            "Restore manifest recoverySet.dcc.manifestPath must be manifest/dcc-backup-manifest.json.",
        )
    dcc_manifest_path = backup_root / manifest_relative_path
    if not dcc_manifest_path.is_file():
        raise BackupOpsError("INTBK-3002", "blocked", f"DCC backup manifest is missing: {dcc_manifest_path}")
    try:
        dcc_manifest = read_json(dcc_manifest_path)
    except Exception as exc:
        raise BackupOpsError("INTBK-3002", "blocked", f"DCC backup manifest cannot be parsed: {exc}") from exc
    errors = validate_dcc_backup_manifest_contract(dcc_manifest)
    if errors:
        raise BackupOpsError(
            "INTBK-3002",
            "blocked",
            "DCC backup manifest validation failed: " + ", ".join(sorted(set(errors))),
        )


def set_env_value(lines: list, key: str, value: str) -> list:
    prefix = key + "="
    updated = []
    replaced = False
    for line in lines:
        if line.startswith(prefix):
            updated.append(prefix + value)
            replaced = True
        else:
            updated.append(line)
    if not replaced:
        updated.append(prefix + value)
    return updated


class Runner:
    def __init__(self, config: dict, mode: str) -> None:
        self.config = config
        self.mode = mode
        self.started_at = datetime.now()
        log_root = Path(get_required(config, ["console", "logRoot"], "console.logRoot"))
        ensure_dir(log_root / self.started_at.strftime("%Y%m"))
        self.sequence = now_sequence()
        self.log_path = log_root / self.started_at.strftime("%Y%m") / f"{self.sequence}_{mode}_running.log"
        self.report_path = log_root / self.started_at.strftime("%Y%m") / f"{self.sequence}_{mode}_running.report.md"
        self.report_json_path = log_root / self.started_at.strftime("%Y%m") / f"{self.sequence}_{mode}_running.report.json"
        self.log_path.write_text(
            "mode={0}\nstartedAt={1}\n".format(mode, self.started_at.isoformat()),
            encoding="utf-8",
        )

    def log(self, message: str) -> None:
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"[{datetime.now().isoformat()}] {message}\n")

    def run(self, command: str, code: str, failure: str) -> str:
        self.log("RUN " + command)
        result = subprocess.run(
            command,
            shell=True,
            executable="/bin/bash",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            universal_newlines=True,
        )
        output = result.stdout or ""
        if output:
            self.log(output.rstrip())
        if result.returncode != 0:
            raise BackupOpsError(code, "fail", f"{failure}\n{output.strip()}".strip())
        return output

    def finalize(self, status: str, code: str, message: str, context: dict) -> int:
        completed_at = datetime.now()
        final_log_path = self.log_path.with_name(self.log_path.name.replace("_running.", f"_{status}."))
        final_report_md = self.report_path.with_name(self.report_path.name.replace("_running.", f"_{status}."))
        final_report_json = self.report_json_path.with_name(self.report_json_path.name.replace("_running.", f"_{status}."))

        report = {
            "action": self.mode,
            "status": status,
            "code": code,
            "message": message,
            "startedAt": self.started_at.isoformat(),
            "completedAt": completed_at.isoformat(),
            "context": context,
            "logPath": str(final_log_path),
            "reportPath": str(final_report_md),
        }
        shutil.move(str(self.log_path), str(final_log_path))
        final_report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        final_report_md.write_text(
            "# Linux Backup Ops Report\n\n"
            f"- action: `{self.mode}`\n"
            f"- status: `{status}`\n"
            f"- code: `{code}`\n"
            f"- message: {message}\n",
            encoding="utf-8",
        )
        print(f"操作完成：{'成功' if status == 'success' else '失败'}")
        print(f"动作类型：{self.mode}")
        print(f"结果代码：{code}")
        print(f"结果说明：{message}")
        if context.get("backupId"):
            print(f"备份点：{context['backupId']}")
        if context.get("restorePoint"):
            print(f"恢复点：{context['restorePoint']}")
        print(f"日志路径：{final_log_path}")
        print(f"报告路径：{final_report_md}")
        return 0 if status == "success" else 1


def get_runtime_paths(config: dict) -> dict:
    app_dir = Path(get_required(config, ["servers", "production", "appDir"], "servers.production.appDir"))
    return {
        "app_dir": app_dir,
        "env": app_dir / ".env",
        "compose": app_dir / "docker-compose.yml",
    }


def get_minio_creds(container_name: str) -> tuple:
    output = subprocess.check_output(
        f"docker inspect --format '{{{{range .Config.Env}}}}{{{{println .}}}}{{{{end}}}}' {container_name}",
        shell=True,
        executable="/bin/bash",
        encoding="utf-8",
        universal_newlines=True,
    )
    access = ""
    secret = ""
    for line in output.splitlines():
        if line.startswith("MINIO_ROOT_USER="):
            access = line.split("=", 1)[1]
        elif line.startswith("MINIO_ROOT_PASSWORD="):
            secret = line.split("=", 1)[1]
    if not access or not secret:
        raise BackupOpsError("INTBK-4001", "blocked", "Unable to resolve local MinIO credentials from container environment.")
    return access, secret


def sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def repository_path_from_sha256(repository_key: str) -> str:
    value = str(repository_key or "").strip()
    if not value.startswith("sha256:"):
        raise BackupOpsError("INTBK-4001", "blocked", f"Unsupported object repository key: {value}")
    digest = value.split(":", 1)[1]
    if len(digest) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in digest):
        raise BackupOpsError("INTBK-4001", "blocked", f"Invalid sha256 object repository key: {value}")
    digest = digest.lower()
    return "sha256/{0}/{1}".format(digest[:2], digest)


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def normalize_dcc_object_path(path: str) -> str:
    return (path or "").replace("\\", "/").lstrip("/").strip()


def parse_minio_object_metadata(output: str) -> List[dict]:
    objects = []
    for raw_line in (output or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except Exception:
            continue
        key = normalize_dcc_object_path(str(payload.get("key", "") or ""))
        if not key:
            continue
        etag = str(payload.get("etag", "") or "").strip().strip('"')
        objects.append(
            {
                "path": key,
                "sourceEtag": etag,
                "size": payload.get("size", 0),
                "lastModified": str(payload.get("lastModified", "") or ""),
                "status": "active",
            }
        )
    return objects


def latest_object_inventory(backup_points_root: Path, current_backup_id: str) -> Optional[dict]:
    if not backup_points_root.is_dir():
        return None
    for candidate in sorted(backup_points_root.iterdir(), key=lambda item: item.name, reverse=True):
        if not candidate.is_dir() or candidate.name >= current_backup_id:
            continue
        inventory_path = candidate / "objects" / "manifest-object-inventory.json"
        if inventory_path.is_file():
            return read_json(inventory_path)
    return None


def build_incremental_object_inventory(workspace: Path, config: dict, backup_id: str, metadata_output: str, runner: Optional["Runner"] = None) -> dict:
    bucket = get_required(config, ["backup", "objectBucket"], "backup.objectBucket")
    backup_points_root = Path(get_required(config, ["servers", "test", "backupPointsRoot"], "servers.test.backupPointsRoot"))
    object_store_root = backup_points_root / "object-store"
    previous_inventory = latest_object_inventory(backup_points_root, backup_id)
    previous_by_path = {}
    if previous_inventory:
        for item in as_manifest_list(previous_inventory.get("objects")):
            if not isinstance(item, dict):
                continue
            status = str(item.get("status", "") or "active")
            path = normalize_dcc_object_path(str(item.get("path", "") or ""))
            if path and status not in {"deleted", "tombstone", "invalidated"}:
                previous_by_path[path] = item
    objects = parse_minio_object_metadata(metadata_output)
    if runner is not None:
        preview = ", ".join(item["path"] for item in objects[:5]) if objects else "<none>"
        runner.log(
            "inventory-metadata bucket={0} object_count={1} preview={2}".format(
                bucket,
                len(objects),
                preview,
            )
        )
    if not objects:
        raise BackupOpsError(
            "INTBK-4001",
            "blocked",
            f"Object bucket snapshot is empty for bucket {bucket}; cannot build DCC object inventory.",
        )
    active_paths = set()
    incremental_objects = []
    stats = {"addedCount": 0, "modifiedCount": 0, "deletedCount": 0, "reusedCount": 0}
    for item in objects:
        object_path = normalize_dcc_object_path(str(item.get("path", "") or ""))
        active_paths.add(object_path)
        previous = previous_by_path.get(object_path)
        source_etag = str(item.get("sourceEtag", "") or "")
        size = item.get("size", 0)
        can_reuse = (
            previous is not None
            and str(previous.get("sourceEtag", "") or "") == source_etag
            and previous.get("size", 0) == size
            and str(previous.get("repositoryPath", "") or "")
            and (object_store_root / Path(normalize_dcc_object_path(str(previous.get("repositoryPath", "") or "")))).is_file()
        )
        next_item = dict(item)
        if can_reuse:
            next_item["sha256"] = str(previous.get("sha256", "") or previous.get("repositoryKey", "") or "")
            next_item["repositoryKey"] = str(previous.get("repositoryKey", "") or previous.get("sha256", "") or "")
            next_item["repositoryPath"] = str(previous.get("repositoryPath", "") or "")
            next_item["changeType"] = "reused"
            stats["reusedCount"] += 1
        else:
            next_item["changeType"] = "modified" if previous is not None else "added"
            if previous is not None:
                stats["modifiedCount"] += 1
            else:
                stats["addedCount"] += 1
        incremental_objects.append(next_item)
    for previous_path, previous in previous_by_path.items():
        if previous_path in active_paths:
            continue
        deleted_item = dict(previous)
        deleted_item["path"] = previous_path
        deleted_item["status"] = "deleted"
        deleted_item["changeType"] = "deleted"
        incremental_objects.append(deleted_item)
        stats["deletedCount"] += 1
    inventory = {
        "mode": "incremental-manifest",
        "bucket": bucket,
        "objectStoreRoot": str(object_store_root),
        "stats": stats,
        "objects": incremental_objects,
    }
    output_path = workspace / "objects" / "manifest-object-inventory.json"
    output_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return inventory


def copy_incremental_objects_from_minio(workspace: Path, config: dict, inventory: dict, access_key: str, secret_key: str, runner: "Runner") -> None:
    bucket = str(inventory.get("bucket") or get_required(config, ["backup", "objectBucket"], "backup.objectBucket"))
    minio_client_image = get_required(config, ["tools", "minioClientImage"], "tools.minioClientImage")
    objects_path = workspace / "objects"
    ensure_dir(objects_path / bucket)
    for item in as_manifest_list(inventory.get("objects")):
        if not isinstance(item, dict):
            continue
        status = str(item.get("status", "") or "active")
        change_type = str(item.get("changeType", "") or "")
        if status in {"deleted", "tombstone", "invalidated"} or change_type == "reused":
            continue
        object_path = normalize_dcc_object_path(str(item.get("path", "") or ""))
        if not object_path:
            raise BackupOpsError("INTBK-4001", "blocked", "Object copy plan contains an empty object path.")
        target_parent = objects_path / bucket / Path(object_path).parent
        ensure_dir(target_parent)
        object_command = "mc alias set src http://127.0.0.1:9000 {0} {1} >/dev/null && mc cp src/{2}/{3} /backup/{2}/{3}".format(
            shlex.quote(access_key),
            shlex.quote(secret_key),
            shlex.quote(bucket),
            shlex.quote(object_path),
        )
        runner.run(
            "docker run --rm --network host --entrypoint /bin/sh -v {0}:/backup {1} -c {2}".format(
                shlex.quote(str(objects_path)),
                shlex.quote(minio_client_image),
                shlex.quote(object_command),
            ),
            "INTBK-4001",
            f"Object copy failed: {object_path}",
        )


def write_object_inventory(workspace: Path, config: dict, runner: Optional["Runner"] = None) -> dict:
    bucket = get_required(config, ["backup", "objectBucket"], "backup.objectBucket")
    bucket_root = workspace / "objects" / bucket
    if not bucket_root.is_dir():
        raise BackupOpsError("INTBK-4001", "blocked", f"Object bucket snapshot directory is missing: {bucket_root}")
    objects = []
    for attempt in range(31):
        objects = []
        file_paths = []
        for path in sorted(bucket_root.rglob("*")):
            if not path.is_file():
                continue
            file_paths.append(path.relative_to(bucket_root).as_posix())
            relative = path.relative_to(bucket_root).as_posix()
            digest = sha256_file(path)
            stat = path.stat()
            objects.append(
                {
                    "path": relative,
                    "sha256": digest,
                    "repositoryKey": digest,
                    "repositoryPath": repository_path_from_sha256(digest),
                    "size": stat.st_size,
                    "lastModified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "status": "active",
                }
            )
        if runner is not None:
            preview = ", ".join(file_paths[:5]) if file_paths else "<none>"
            runner.log(
                "inventory-scan attempt={0} bucket_root={1} exists={2} file_count={3} preview={4}".format(
                    attempt + 1,
                    bucket_root,
                    bucket_root.is_dir(),
                    len(file_paths),
                    preview,
                )
            )
        if objects:
            break
        if attempt < 30:
            time.sleep(2)
    if not objects:
        raise BackupOpsError(
            "INTBK-4001",
            "blocked",
            f"Object bucket snapshot is empty for bucket {bucket}; cannot build DCC object inventory.",
        )
    inventory = {
        "mode": "incremental-manifest",
        "bucket": bucket,
        "objectStoreRoot": str(Path(get_required(config, ["servers", "test", "backupPointsRoot"], "servers.test.backupPointsRoot")) / "object-store"),
        "stats": {
            "addedCount": len(objects),
            "modifiedCount": 0,
            "deletedCount": 0,
            "reusedCount": 0,
        },
        "objects": objects,
    }
    output_path = workspace / "objects" / "manifest-object-inventory.json"
    output_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return inventory


def publish_object_inventory_to_store(workspace: Path, config: dict, inventory: dict) -> dict:
    bucket = str(inventory.get("bucket") or get_required(config, ["backup", "objectBucket"], "backup.objectBucket"))
    bucket_root = workspace / "objects" / bucket
    if not bucket_root.is_dir():
        raise BackupOpsError("INTBK-4001", "blocked", f"Object bucket snapshot directory is missing: {bucket_root}")
    backup_points_root = Path(get_required(config, ["servers", "test", "backupPointsRoot"], "servers.test.backupPointsRoot"))
    object_store_root = backup_points_root / "object-store"
    ensure_dir(object_store_root)
    added_count = 0
    reused_count = 0
    published_objects = []
    for item in as_manifest_list(inventory.get("objects")):
        if not isinstance(item, dict):
            continue
        object_path = normalize_dcc_object_path(str(item.get("path", "") or ""))
        if not object_path:
            raise BackupOpsError("INTBK-4001", "blocked", "Object inventory contains an empty object path.")
        status = str(item.get("status", "") or "active")
        change_type = str(item.get("changeType", "") or "")
        if status in {"deleted", "tombstone", "invalidated"}:
            next_item = dict(item)
            next_item["path"] = object_path
            next_item["status"] = "deleted"
            next_item["changeType"] = change_type or "deleted"
            published_objects.append(next_item)
            continue
        if change_type == "reused":
            repository_path = normalize_dcc_object_path(str(item.get("repositoryPath", "") or ""))
            if not repository_path:
                raise BackupOpsError("INTBK-4001", "blocked", f"Reused object is missing repositoryPath: {object_path}")
            if not (object_store_root / Path(repository_path)).is_file():
                raise BackupOpsError("INTBK-4001", "blocked", f"Reused object store file is missing: {repository_path}")
            next_item = dict(item)
            next_item["path"] = object_path
            next_item["status"] = status
            published_objects.append(next_item)
            reused_count += 1
            continue
        source_path = bucket_root / object_path
        if not source_path.is_file():
            raise BackupOpsError("INTBK-4001", "blocked", f"Object inventory source is missing: {source_path}")
        digest = sha256_file(source_path)
        repository_path = repository_path_from_sha256(digest)
        target_path = object_store_root / Path(repository_path)
        ensure_dir(target_path.parent)
        if target_path.exists():
            reused_count += 1
        else:
            shutil.copy2(str(source_path), str(target_path))
            added_count += 1
        next_item = dict(item)
        next_item["path"] = object_path
        next_item["sha256"] = digest
        next_item["repositoryKey"] = digest
        next_item["repositoryPath"] = repository_path
        next_item["status"] = str(next_item.get("status", "") or "active")
        next_item["changeType"] = change_type or "added"
        published_objects.append(next_item)
    if not published_objects:
        raise BackupOpsError("INTBK-4001", "blocked", f"Object bucket snapshot is empty for bucket {bucket}; cannot publish object inventory.")
    inventory["objectStoreRoot"] = str(object_store_root)
    inventory["stats"] = {
        "addedCount": added_count,
        "modifiedCount": 0,
        "deletedCount": 0,
        "reusedCount": reused_count,
    }
    inventory["objects"] = published_objects
    output_path = workspace / "objects" / "manifest-object-inventory.json"
    output_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    shutil.rmtree(bucket_root)
    return inventory


def materialize_restore_objects_from_inventory(backup_root: Path, config: dict, backup_points_root: Path) -> Path:
    inventory_path = backup_root / "objects" / "manifest-object-inventory.json"
    if not inventory_path.is_file():
        raise BackupOpsError("INTBK-4002", "blocked", f"Object inventory is missing: {inventory_path}")
    inventory = read_json(inventory_path)
    bucket = str(inventory.get("bucket") or get_required(config, ["backup", "objectBucket"], "backup.objectBucket"))
    restore_root = backup_root / "objects" / "_restore-materialized" / bucket
    if restore_root.exists():
        shutil.rmtree(restore_root)
    ensure_dir(restore_root)
    object_store_root = backup_points_root / "object-store"
    for item in as_manifest_list(inventory.get("objects")):
        if not isinstance(item, dict):
            continue
        status = str(item.get("status", "") or "active")
        if status in {"deleted", "tombstone", "invalidated"}:
            continue
        object_path = normalize_dcc_object_path(str(item.get("path", "") or ""))
        repository_path = normalize_dcc_object_path(str(item.get("repositoryPath", "") or ""))
        if not object_path:
            raise BackupOpsError("INTBK-4002", "blocked", "Object inventory contains an empty restore path.")
        if not repository_path:
            raise BackupOpsError("INTBK-4002", "blocked", f"Object inventory is missing repositoryPath for object: {object_path}")
        source_path = object_store_root / Path(repository_path)
        if not source_path.is_file():
            raise BackupOpsError("INTBK-4002", "blocked", f"Object store file is missing: {source_path}")
        target_path = restore_root / object_path
        ensure_dir(target_path.parent)
        shutil.copy2(str(source_path), str(target_path))
    return restore_root


def assert_restore_object_inventory_ready(backup_root: Path, config: dict, backup_points_root: Path) -> None:
    inventory_path = backup_root / "objects" / "manifest-object-inventory.json"
    if not inventory_path.is_file():
        raise BackupOpsError("INTBK-4002", "blocked", f"Object inventory is missing: {inventory_path}")
    inventory = read_json(inventory_path)
    object_store_root = backup_points_root / "object-store"
    for item in as_manifest_list(inventory.get("objects")):
        if not isinstance(item, dict):
            continue
        status = str(item.get("status", "") or "active")
        if status in {"deleted", "tombstone", "invalidated"}:
            continue
        object_path = normalize_dcc_object_path(str(item.get("path", "") or ""))
        repository_path = normalize_dcc_object_path(str(item.get("repositoryPath", "") or ""))
        if not object_path:
            raise BackupOpsError("INTBK-4002", "blocked", "Object inventory contains an empty restore path.")
        if not repository_path:
            raise BackupOpsError("INTBK-4002", "blocked", f"Object inventory is missing repositoryPath for object: {object_path}")
        source_path = object_store_root / Path(repository_path)
        if not source_path.is_file():
            raise BackupOpsError("INTBK-4002", "blocked", f"Object store file is missing: {source_path}")


def write_object_inventory_from_minio_metadata(workspace: Path, config: dict, metadata_output: str, runner: Optional["Runner"] = None) -> dict:
    bucket = get_required(config, ["backup", "objectBucket"], "backup.objectBucket")
    objects = parse_minio_object_metadata(metadata_output)
    if runner is not None:
        preview = ", ".join(item["path"] for item in objects[:5]) if objects else "<none>"
        runner.log(
            "inventory-metadata bucket={0} object_count={1} preview={2}".format(
                bucket,
                len(objects),
                preview,
            )
        )
    if not objects:
        raise BackupOpsError(
            "INTBK-4001",
            "blocked",
            f"Object bucket snapshot is empty for bucket {bucket}; cannot build DCC object inventory.",
        )
    inventory = {
        "mode": "incremental-manifest",
        "bucket": bucket,
        "objectStoreRoot": str(Path(get_required(config, ["servers", "test", "backupPointsRoot"], "servers.test.backupPointsRoot")) / "object-store"),
        "stats": {
            "addedCount": len(objects),
            "modifiedCount": 0,
            "deletedCount": 0,
            "reusedCount": 0,
        },
        "objects": objects,
    }
    output_path = workspace / "objects" / "manifest-object-inventory.json"
    output_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return inventory


def dcc_database_snapshot_sql(tenant_id: int) -> str:
    return f"""
SELECT
  cf.id AS controlledFileId,
  cf.tenant_id AS tenantId,
  cf.file_number AS fileNumber,
  cf.version_no AS versionNo,
  cf.status AS status,
  COALESCE(DATE_FORMAT(cf.update_time, '%Y-%m-%dT%H:%i:%s+08:00'), '') AS updatedAt,
  refs.object_role AS objectRole,
  refs.object_file_id AS objectFileId,
  COALESCE(REPLACE(REPLACE(REPLACE(f.path, CHAR(9), ' '), CHAR(13), ''), CHAR(10), ''), '') AS objectPath,
  '' AS objectSha256,
  COALESCE(
    CONCAT('sha256:', SHA2(GROUP_CONCAT(DISTINCT CONCAT_WS(':', pr.action_type, pr.subject_type, pr.subject_id, pr.active) ORDER BY pr.action_type, pr.subject_type, pr.subject_id SEPARATOR '|'), 256)),
    CONCAT('sha256:', SHA2('no-permission', 256))
  ) AS permissionDigest
FROM dcc_controlled_file cf
LEFT JOIN (
  SELECT id AS controlled_file_id, 'source' AS object_role, source_file_id AS object_file_id FROM dcc_controlled_file WHERE tenant_id = {tenant_id} AND source_file_id IS NOT NULL AND deleted = b'0'
  UNION ALL SELECT id, 'original', original_file_id FROM dcc_controlled_file WHERE tenant_id = {tenant_id} AND original_file_id IS NOT NULL AND deleted = b'0'
  UNION ALL SELECT id, 'drawing_pdf', drawing_pdf_file_id FROM dcc_controlled_file WHERE tenant_id = {tenant_id} AND drawing_pdf_file_id IS NOT NULL AND deleted = b'0'
  UNION ALL SELECT id, 'training_record', training_record_file_id FROM dcc_controlled_file WHERE tenant_id = {tenant_id} AND training_record_file_id IS NOT NULL AND deleted = b'0'
  UNION ALL SELECT id, 'published', published_file_id FROM dcc_controlled_file WHERE tenant_id = {tenant_id} AND published_file_id IS NOT NULL AND deleted = b'0'
  UNION ALL SELECT id, 'stamped', stamped_file_id FROM dcc_controlled_file WHERE tenant_id = {tenant_id} AND stamped_file_id IS NOT NULL AND deleted = b'0'
) refs ON refs.controlled_file_id = cf.id
LEFT JOIN infra_file f ON f.id = refs.object_file_id AND f.deleted = b'0'
LEFT JOIN dcc_file_category_permission_rule pr
  ON pr.category_id = cf.category_id
 AND pr.tenant_id = cf.tenant_id
 AND pr.deleted = b'0'
 AND pr.active = 1
WHERE cf.tenant_id = {tenant_id}
  AND cf.deleted = b'0'
GROUP BY
  cf.id, cf.tenant_id, cf.file_number, cf.version_no, cf.status, cf.update_time,
  refs.object_role, refs.object_file_id, f.path
ORDER BY cf.id, refs.object_role, refs.object_file_id
""".strip() + "\n"


def parse_mysql_tsv(path: Path) -> List[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return []
    headers = lines[0].split("\t")
    rows = []
    for index, line in enumerate(lines[1:], start=2):
        values = line.split("\t")
        if len(values) != len(headers):
            raise BackupOpsError(
                "INTBK-6001",
                "blocked",
                f"DCC MySQL CLI output row {index} has {len(values)} columns; expected {len(headers)}.",
            )
        row = {}
        for header, value in zip(headers, values):
            row[header] = "" if value in {"NULL", "\\N"} else value
        rows.append(row)
    return rows


def write_dcc_database_query(workspace: Path, config: dict, runner: Runner, mysql_password: str) -> Path:
    tenant_id = int(get_required(config, ["backup", "dccTenantId"], "backup.dccTenantId"))
    target_environment = str(config.get("environment", ""))
    target_host = get_required(config, ["servers", "production", "host"], "servers.production.host")
    if target_environment != "test" or target_host != "172.30.30.58":
        raise BackupOpsError(
            "INTBK-6001",
            "blocked",
            f"DCC database snapshot requires targetEnvironment=test and targetHost=172.30.30.58; got {target_environment}/{target_host}.",
        )
    manifest_dir = workspace / "manifest"
    ensure_dir(manifest_dir)
    query_path = manifest_dir / "dcc-database-query.sql"
    output_path = manifest_dir / "dcc-database-query.tsv"
    query_path.write_text(dcc_database_snapshot_sql(tenant_id), encoding="utf-8")
    mysql_container = get_required(config, ["containers", "mysql"], "containers.mysql")
    db_name = get_required(config, ["backup", "mysqlDatabase"], "backup.mysqlDatabase")
    runner.run(
        "docker exec -i {0} mysql --batch --raw --default-character-set=utf8mb4 -uroot {1} {2} < {3} > {4}".format(
            shlex.quote(mysql_container),
            shlex.quote("-p" + mysql_password),
            shlex.quote(db_name),
            shlex.quote(str(query_path)),
            shlex.quote(str(output_path)),
        ),
        "INTBK-6001",
        "DCC database snapshot query failed.",
    )
    return output_path


def build_dcc_database_snapshot(rows: List[dict], target_environment: str, target_host: str, tenant_id: int) -> dict:
    required_fields = [
        "controlledFileId",
        "tenantId",
        "fileNumber",
        "versionNo",
        "status",
        "updatedAt",
        "objectRole",
        "objectFileId",
        "objectPath",
        "objectSha256",
        "permissionDigest",
    ]
    errors = []
    file_map: dict[str, dict] = {}
    for row in rows:
        missing = [field for field in required_fields if field not in row]
        if missing:
            errors.append(f"dcc_query_missing_fields:{','.join(missing)}")
            continue
        try:
            controlled_file_id = int(str(row["controlledFileId"]).strip())
            row_tenant_id = int(str(row["tenantId"]).strip())
        except ValueError:
            errors.append("dcc_query_field_invalid:id")
            continue
        if row_tenant_id != tenant_id:
            errors.append(f"tenant_id_mismatch:{controlled_file_id}")
            continue
        file_key = f"controlled-file:{controlled_file_id}"
        record = file_map.setdefault(
            file_key,
            {
                "fileKey": file_key,
                "controlledFileId": controlled_file_id,
                "tenantId": tenant_id,
                "fileNumber": str(row["fileNumber"]).strip(),
                "versionNo": str(row["versionNo"]).strip(),
                "status": str(row["status"]).strip(),
                "state": "active",
                "permissionDigest": str(row["permissionDigest"]).strip(),
                "updatedAt": str(row["updatedAt"]).strip(),
                "objects": [],
            },
        )
        for field in ["fileNumber", "versionNo", "status", "permissionDigest", "updatedAt"]:
            value = str(row[field]).strip()
            if not value:
                errors.append(f"dcc_query_field_empty:{file_key}.{field}")
            elif record[field] != value:
                errors.append(f"dcc_query_metadata_conflict:{file_key}.{field}")
        object_role = str(row["objectRole"]).strip()
        object_file_id = str(row["objectFileId"]).strip()
        object_path = normalize_dcc_object_path(str(row["objectPath"]))
        if not object_role or not object_file_id:
            errors.append(f"dcc_active_object_reference_missing:{file_key}")
            continue
        if not object_path:
            errors.append(f"dcc_active_object_path_missing:{file_key}.{object_role}")
            continue
        try:
            parsed_object_file_id = int(object_file_id)
        except ValueError:
            errors.append(f"dcc_query_field_invalid:{file_key}.objectFileId")
            continue
        object_payload = {
            "role": object_role,
            "fileId": parsed_object_file_id,
            "path": object_path,
        }
        object_sha = str(row.get("objectSha256", "")).strip()
        if object_sha:
            object_payload["sha256"] = object_sha
        record["objects"].append(object_payload)

    controlled_files = []
    for file_key in sorted(file_map):
        record = file_map[file_key]
        if not record["objects"]:
            errors.append(f"dcc_active_object_path_missing:{file_key}.objects")
            continue
        objects = sorted(record["objects"], key=lambda item: (item["role"], item["fileId"], item["path"]))
        database_digest_input = (
            record["fileKey"]
            + "|"
            + str(record["tenantId"])
            + "|"
            + record["fileNumber"]
            + "|"
            + record["versionNo"]
            + "|"
            + record["status"]
            + "|"
            + record["updatedAt"]
            + "|"
            + record["permissionDigest"]
            + "|"
            + canonical_json(objects)
        )
        primary = objects[0]
        payload = {
            "fileKey": record["fileKey"],
            "controlledFileId": record["controlledFileId"],
            "tenantId": record["tenantId"],
            "fileNumber": record["fileNumber"],
            "versionNo": record["versionNo"],
            "status": record["status"],
            "state": record["state"],
            "permissionDigest": record["permissionDigest"],
            "databaseDigest": sha256_text(database_digest_input),
            "updatedAt": record["updatedAt"],
            "objectPath": primary["path"],
            "objects": objects,
        }
        if primary.get("sha256"):
            payload["objectSha256"] = primary["sha256"]
        controlled_files.append(payload)

    if not controlled_files and not errors:
        errors.append("dcc_snapshot_no_records")
    if errors:
        raise BackupOpsError(
            "INTBK-6001",
            "blocked",
            "DCC database snapshot export failed: " + ", ".join(errors),
        )
    return {
        "schemaVersion": "dcc-snapshot-v1",
        "schemaVersionTag": "dcc-database-snapshot-v1",
        "snapshotId": "dcc-snapshot-linux-local",
        "targetEnvironment": target_environment,
        "targetHost": target_host,
        "tenantId": tenant_id,
        "capturedAt": datetime.now().isoformat(),
        "controlledFiles": controlled_files,
    }


def write_dcc_database_snapshot(workspace: Path, config: dict, runner: Runner, mysql_password: str) -> dict:
    tenant_id = int(get_required(config, ["backup", "dccTenantId"], "backup.dccTenantId"))
    target_environment = str(config.get("environment", ""))
    target_host = get_required(config, ["servers", "production", "host"], "servers.production.host")
    query_output = write_dcc_database_query(workspace, config, runner, mysql_password)
    snapshot = build_dcc_database_snapshot(parse_mysql_tsv(query_output), target_environment, target_host, tenant_id)
    output_path = workspace / "manifest" / "dcc-database-snapshot.json"
    output_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return snapshot


def object_map_by_path(inventory: dict) -> dict:
    result = {}
    for item in as_manifest_list(inventory.get("objects")):
        if isinstance(item, dict):
            path = normalize_dcc_object_path(str(item.get("path", "") or ""))
            if path:
                result[path] = item
    return result


def dcc_record_state(record: Optional[dict]) -> str:
    if not isinstance(record, dict):
        return "active"
    state = str(record.get("state", "") or "").strip().lower()
    return state or "active"


def last_dcc_restore_point_id(manifest: dict) -> str:
    chain = as_manifest_list(manifest.get("incrementalChain"))
    if chain:
        last = chain[-1]
        if isinstance(last, dict):
            point = str(last.get("to", "") or "").strip()
            if point:
                return point
    baseline = manifest.get("fullBaseline")
    if isinstance(baseline, dict):
        return str(baseline.get("restorePointId", "") or "").strip()
    return ""


def records_for_restore_point(manifest: dict, restore_point_id: str) -> dict:
    result = {}
    for record in as_manifest_list(manifest.get("databaseRecords")):
        if not isinstance(record, dict):
            continue
        if str(record.get("restorePointId", "") or "") != restore_point_id:
            continue
        file_key = str(record.get("fileKey", "") or "").strip()
        if file_key:
            result[file_key] = record
    return result


def objects_for_restore_point(manifest: dict, restore_point_id: str) -> dict:
    result = {}
    for inventory in as_manifest_list(manifest.get("objectInventories")):
        if not isinstance(inventory, dict):
            continue
        if str(inventory.get("restorePointId", "") or "") != restore_point_id:
            continue
        for item in as_manifest_list(inventory.get("objects")):
            if not isinstance(item, dict):
                continue
            file_key = str(item.get("fileKey", "") or "").strip()
            if file_key:
                result[file_key] = item
    return result


def latest_previous_dcc_manifest(config: dict, current_backup_id: str) -> Optional[dict]:
    backup_root = Path(get_required(config, ["servers", "test", "backupPointsRoot"], "servers.test.backupPointsRoot"))
    if not backup_root.exists():
        return None
    for child in sorted(backup_root.iterdir(), reverse=True):
        if not child.is_dir() or child.name >= current_backup_id or not is_backup_point_name(child.name):
            continue
        manifest_path = child / "manifest" / "dcc-backup-manifest.json"
        if not manifest_path.is_file():
            continue
        try:
            manifest = read_json(manifest_path)
        except Exception:
            continue
        if manifest.get("schemaVersion") == "dcc-backup-manifest-v1" and manifest.get("status") == "success" and last_dcc_restore_point_id(manifest):
            return manifest
    return None


def build_dcc_current_models(snapshot: dict, inventory: dict, restore_point_id: str, previous_records: dict, previous_objects: dict) -> Tuple[List[object], List[object], dict, dict]:
    object_by_path = object_map_by_path(inventory)
    current_record_map = {}
    current_object_map = {}
    database_records = []
    inventory_objects = []
    errors = []
    for record in as_manifest_list(snapshot.get("controlledFiles")):
        if not isinstance(record, dict):
            continue
        file_key = str(record.get("fileKey", "") or "").strip()
        if not file_key:
            errors.append("dcc_file_key_missing")
            continue
        state = dcc_record_state(record)
        object_refs = []
        hash_parts = []
        for ref in as_manifest_list(record.get("objects")):
            if not isinstance(ref, dict):
                continue
            path = normalize_dcc_object_path(str(ref.get("path", "") or ""))
            if not path:
                continue
            inventory_object = object_by_path.get(path)
            if inventory_object is None and state != "deleted":
                errors.append(f"dcc_object_inventory_missing:{file_key}:{path}")
                continue
            if inventory_object is not None:
                sha = str(inventory_object.get("sha256", "") or inventory_object.get("etag", "") or "").strip()
                repository_key = str(inventory_object.get("repositoryKey", "") or sha).strip()
                role = str(ref.get("role", "") or "file").strip()
                hash_parts.append(f"{role}|{path}|{sha}")
                object_refs.append(
                    {
                        "role": role,
                        "path": path,
                        "sha256": sha,
                        "repositoryKey": repository_key,
                        "size": inventory_object.get("size"),
                        "lastModified": str(inventory_object.get("lastModified", "") or ""),
                    }
                )
        database_digest = str(record.get("databaseDigest", "") or "").strip()
        permission_digest = str(record.get("permissionDigest", "") or "").strip()
        content_hash = sha256_text(file_key + "|" + database_digest + "|" + ";".join(sorted(hash_parts)))
        present = state != "deleted" and bool(object_refs)
        database_record = {
            "restorePointId": restore_point_id,
            "fileKey": file_key,
            "controlledFileId": record.get("controlledFileId"),
            "tenantId": record.get("tenantId"),
            "fileNumber": str(record.get("fileNumber", "") or ""),
            "versionNo": str(record.get("versionNo", "") or ""),
            "state": state,
            "databaseDigest": database_digest,
            "permissionDigest": permission_digest,
            "permissionChanged": False,
        }
        inventory_object = {
            "fileKey": file_key,
            "state": state,
            "contentHash": content_hash,
            "storedHash": content_hash,
            "present": present,
            "objectRefs": object_refs,
        }
        current_record_map[file_key] = database_record
        current_object_map[file_key] = inventory_object
        database_records.append(database_record)
        inventory_objects.append(inventory_object)

    for previous_key, previous_record in previous_records.items():
        if previous_key in current_record_map or dcc_record_state(previous_record) == "deleted":
            continue
        previous_object = previous_objects.get(previous_key, {})
        content_hash = str(previous_object.get("contentHash", "") or "").strip() or sha256_text(previous_key + "|deleted")
        deleted_record = {
            "restorePointId": restore_point_id,
            "fileKey": previous_key,
            "controlledFileId": previous_record.get("controlledFileId"),
            "tenantId": previous_record.get("tenantId"),
            "fileNumber": str(previous_record.get("fileNumber", "") or ""),
            "versionNo": str(previous_record.get("versionNo", "") or ""),
            "state": "deleted",
            "databaseDigest": str(previous_record.get("databaseDigest", "") or ""),
            "permissionDigest": str(previous_record.get("permissionDigest", "") or ""),
            "permissionChanged": False,
        }
        deleted_object = {
            "fileKey": previous_key,
            "state": "deleted",
            "contentHash": content_hash,
            "storedHash": content_hash,
            "present": False,
            "objectRefs": [],
        }
        current_record_map[previous_key] = deleted_record
        current_object_map[previous_key] = deleted_object
        database_records.append(deleted_record)
        inventory_objects.append(deleted_object)

    if errors:
        raise BackupOpsError("INTBK-6001", "blocked", "DCC backup manifest build failed: " + ", ".join(errors))
    return (
        sorted(database_records, key=lambda item: item["fileKey"]),
        sorted(inventory_objects, key=lambda item: item["fileKey"]),
        current_record_map,
        current_object_map,
    )


def build_dcc_events(current_records: dict, current_objects: dict, previous_records: dict, previous_objects: dict, restore_point_id: str) -> list:
    events = []
    for file_key in sorted(current_records):
        current_record = current_records[file_key]
        current_object = current_objects[file_key]
        current_state = dcc_record_state(current_record)
        previous_record = previous_records.get(file_key)
        previous_object = previous_objects.get(file_key)
        previous_state = dcc_record_state(previous_record)
        event_types = []
        if previous_record is None:
            event_types.append("delete" if current_state == "deleted" else "add")
        elif current_state != previous_state:
            if current_state == "deleted":
                event_types.append("delete")
            elif current_state == "voided":
                event_types.append("void")
            elif current_state == "archived":
                event_types.append("archive")
            else:
                event_types.append("modify")
        current_hash = str(current_object.get("contentHash", "") or "")
        previous_hash = str((previous_object or {}).get("contentHash", "") or "")
        if previous_record is not None and current_state != "deleted" and current_hash != previous_hash:
            event_types.append("modify")
        current_permission = str(current_record.get("permissionDigest", "") or "")
        previous_permission = str((previous_record or {}).get("permissionDigest", "") or "")
        if previous_record is not None and current_permission != previous_permission:
            event_types.append("permission_change")
            current_record["permissionChanged"] = True
        for event_type in sorted(set(event_types)):
            events.append({"restorePointId": restore_point_id, "fileKey": file_key, "eventType": event_type})
    return events


def build_dcc_change_summary(current_records: dict, current_objects: dict, previous_records: dict, previous_objects: dict) -> dict:
    summary = {
        "addedRecords": 0,
        "changedRecords": 0,
        "deletedRecords": 0,
        "invalidatedRecords": 0,
        "addedObjects": 0,
        "changedObjects": 0,
        "reusedObjects": 0,
        "tombstoneObjects": 0,
    }
    for file_key in sorted(current_records):
        current_record = current_records[file_key]
        current_object = current_objects.get(file_key, {})
        previous_record = previous_records.get(file_key)
        previous_object = previous_objects.get(file_key, {})
        current_state = dcc_record_state(current_record)
        previous_state = dcc_record_state(previous_record)
        current_hash = str(current_object.get("contentHash", "") or "")
        previous_hash = str(previous_object.get("contentHash", "") or "")
        current_database_digest = str(current_record.get("databaseDigest", "") or "")
        previous_database_digest = str((previous_record or {}).get("databaseDigest", "") or "")
        current_permission_digest = str(current_record.get("permissionDigest", "") or "")
        previous_permission_digest = str((previous_record or {}).get("permissionDigest", "") or "")

        if current_state == "deleted":
            summary["tombstoneObjects"] += 1
            if previous_record is not None and previous_state != "deleted":
                summary["deletedRecords"] += 1
            continue
        if current_state in {"voided", "archived"}:
            summary["invalidatedRecords"] += 1

        if previous_record is None:
            summary["addedRecords"] += 1
            if current_hash:
                summary["addedObjects"] += 1
            continue

        record_changed = (
            current_state != previous_state
            or current_database_digest != previous_database_digest
            or current_permission_digest != previous_permission_digest
        )
        object_changed = current_hash != previous_hash
        if record_changed or object_changed:
            summary["changedRecords"] += 1
        if object_changed:
            summary["changedObjects"] += 1
        elif current_hash:
            summary["reusedObjects"] += 1
    return summary


def write_dcc_backup_manifest(workspace: Path, backup_id: str, config: dict, snapshot: dict, object_inventory: dict) -> dict:
    target_environment = str(config.get("environment", ""))
    target_host = get_required(config, ["servers", "production", "host"], "servers.production.host")
    if target_environment != "test" or target_host != "172.30.30.58":
        raise BackupOpsError(
            "INTBK-6001",
            "blocked",
            f"DCC backup manifest requires targetEnvironment=test and targetHost=172.30.30.58; got {target_environment}/{target_host}.",
        )
    previous_manifest = latest_previous_dcc_manifest(config, backup_id)
    previous_point = last_dcc_restore_point_id(previous_manifest) if previous_manifest else ""
    previous_records = records_for_restore_point(previous_manifest, previous_point) if previous_manifest else {}
    previous_objects = objects_for_restore_point(previous_manifest, previous_point) if previous_manifest else {}
    database_records, inventory_objects, current_record_map, current_object_map = build_dcc_current_models(
        snapshot,
        object_inventory,
        backup_id,
        previous_records,
        previous_objects,
    )
    current_events = build_dcc_events(current_record_map, current_object_map, previous_records, previous_objects, backup_id)
    change_summary = build_dcc_change_summary(current_record_map, current_object_map, previous_records, previous_objects)
    segment_checksum = sha256_text(backup_id + "|" + canonical_json(database_records) + "|" + canonical_json(inventory_objects))
    backup_scope_type = str(config.get("backup", {}).get("dccBackupScopeType", "") or "target-dataset")
    backup_scope_id = str(
        config.get("backup", {}).get("dccBackupScopeId", "")
        or ("dcc-tenant-" + str(config.get("backup", {}).get("dccTenantId", "") or "").strip())
    ).strip()
    if not backup_scope_id:
        raise BackupOpsError("INTBK-6001", "blocked", "DCC backup manifest requires backupScopeId.")
    if previous_manifest:
        full_baseline = previous_manifest.get("fullBaseline")
        baseline_restore_point_id = str((full_baseline or {}).get("restorePointId", "") or "")
        incremental_chain = as_manifest_list(previous_manifest.get("incrementalChain")) + [
            {
                "from": previous_point,
                "to": backup_id,
                "checksum": segment_checksum,
                "schemaFrom": str((full_baseline or {}).get("schemaVersion", "") or ""),
                "schemaTo": str(snapshot.get("schemaVersionTag", "") or ""),
            }
        ]
        restore_points = as_manifest_list(previous_manifest.get("restorePoints"))
        object_inventories = as_manifest_list(previous_manifest.get("objectInventories"))
        all_database_records = as_manifest_list(previous_manifest.get("databaseRecords"))
        dcc_events = as_manifest_list(previous_manifest.get("dccEvents"))
    else:
        full_baseline = {
            "restorePointId": backup_id,
            "checksum": segment_checksum,
            "schemaVersion": str(snapshot.get("schemaVersionTag", "") or ""),
        }
        baseline_restore_point_id = backup_id
        incremental_chain = []
        restore_points = []
        object_inventories = []
        all_database_records = []
        dcc_events = []
    restore_points = restore_points + [
        {"id": backup_id, "databaseRestorePointId": backup_id, "objectInventoryRestorePointId": backup_id}
    ]
    object_inventories = object_inventories + [
        {
            "restorePointId": backup_id,
            "bucket": str(object_inventory.get("bucket", "") or ""),
            "objectStoreRoot": str(object_inventory.get("objectStoreRoot", "") or ""),
            "objects": inventory_objects,
        }
    ]
    manifest = {
        "schemaVersion": "dcc-backup-manifest-v1",
        "backupId": backup_id,
        "targetEnvironment": target_environment,
            "targetHost": target_host,
            "status": "success",
            "chainStatus": "COMPLETE",
            "backupScopeType": backup_scope_type,
            "backupScopeId": backup_scope_id,
            "backupMode": "incremental" if previous_manifest else "full",
            "baselineBackupId": baseline_restore_point_id,
            "baselineRestorePointId": baseline_restore_point_id,
            "previousBackupId": previous_point if previous_manifest else "",
            "previousRestorePointId": previous_point if previous_manifest else "",
            "changeSummary": change_summary,
            "restoreVerified": False,
            "restoreRehearsal": {"status": "not-run"},
        "fullBaseline": full_baseline,
        "incrementalChain": incremental_chain,
        "restorePoints": restore_points,
        "objectInventories": object_inventories,
        "databaseRecords": all_database_records + database_records,
        "dccEvents": dcc_events + current_events,
    }
    errors = validate_dcc_backup_manifest_contract(manifest)
    if errors:
        raise BackupOpsError(
            "INTBK-6001",
            "blocked",
            "DCC backup manifest validation failed: " + ", ".join(sorted(set(errors))),
        )
    output_path = workspace / "manifest" / "dcc-backup-manifest.json"
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def write_dcc_backup_contract(workspace: Path, backup_id: str, config: dict, runner: Runner, mysql_password: str, object_inventory: Optional[dict] = None) -> None:
    if object_inventory is None:
        object_inventory = write_object_inventory(workspace, config, runner)
    snapshot = write_dcc_database_snapshot(workspace, config, runner, mysql_password)
    write_dcc_backup_manifest(workspace, backup_id, config, snapshot, object_inventory)


def write_checksums(workspace: Path) -> None:
    lines = []
    for relative in [
        Path("mysql/ruoyi-vue-pro.sql.gz"),
        Path("mysql/binlog-preflight.json"),
        Path("mysql/binlog-segment-manifest.json"),
        Path("deploy/docker-compose.yml"),
        Path("deploy/runtime.env"),
        Path("deploy/image-tag.txt"),
        Path("objects/manifest-object-inventory.json"),
        Path("manifest/dcc-backup-manifest.json"),
    ]:
        target = workspace / relative
        if target.exists():
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            lines.append(f"{digest}  {relative.as_posix()}")
    ensure_dir(workspace / "manifest")
    (workspace / "manifest" / "checksums.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(workspace: Path, backup_id: str, backup_type: str, config: dict, image_tag: str, backend_port: int, frontend_port: int) -> None:
    db_name = get_required(config, ["backup", "mysqlDatabase"], "backup.mysqlDatabase")
    bucket = get_required(config, ["backup", "objectBucket"], "backup.objectBucket")
    target_environment = str(config.get("environment", ""))
    target_host = get_required(config, ["servers", "production", "host"], "servers.production.host")
    if target_environment != "test" or target_host != "172.30.30.58":
        raise BackupOpsError(
            "INTBK-1003",
            "blocked",
            "Cannot write success manifest: targetEnvironment=test and targetHost=172.30.30.58 are required; "
            f"current targetEnvironment={target_environment} targetHost={target_host}.",
        )
    mysql_backup_mode = assert_mysql_backup_mode_supported(config, workspace)
    checksums_path = workspace / "manifest" / "checksums.txt"
    dcc_manifest_path = workspace / "manifest" / "dcc-backup-manifest.json"
    if not dcc_manifest_path.is_file():
        raise BackupOpsError(
            "INTBK-6001",
            "blocked",
            f"DCC backup manifest is missing: {dcc_manifest_path}. "
            "Generate manifest/dcc-backup-manifest.json before writing a success backup manifest.",
        )
    required_files = [
        workspace / "mysql" / f"{db_name}.sql.gz",
        workspace / "objects" / "manifest-object-inventory.json",
        dcc_manifest_path,
        workspace / "deploy" / "docker-compose.yml",
        workspace / "deploy" / "runtime.env",
        checksums_path,
    ]
    recovery_set_complete = all(path.is_file() for path in required_files)
    checksums_hash = hashlib.sha256(checksums_path.read_bytes()).hexdigest() if checksums_path.is_file() else ""
    manifest = {
        "schemaVersion": "v2",
        "backupId": backup_id,
        "targetEnvironment": target_environment,
        "targetHost": target_host,
        "backupType": backup_type,
        "environment": target_environment,
        "status": "success",
        "source": {
            "serverHost": target_host,
            "appDir": get_required(config, ["servers", "production", "appDir"], "servers.production.appDir"),
            "minioBucket": get_required(config, ["backup", "objectBucket"], "backup.objectBucket"),
        },
        "operator": {"mode": "linux-local", "name": os.environ.get("USER", "linux-local")},
        "time": {"startedAt": datetime.now().isoformat(), "completedAt": datetime.now().isoformat()},
        "artifacts": {
            "mysqlDump": "mysql/ruoyi-vue-pro.sql.gz",
            "objectSnapshot": "objects/manifest-object-inventory.json",
            "dccBackupManifest": "manifest/dcc-backup-manifest.json",
            "composeFile": "deploy/docker-compose.yml",
            "runtimeEnv": "deploy/runtime.env",
            "imageTagFile": "deploy/image-tag.txt",
            "checksumsFile": "manifest/checksums.txt",
        },
        "deploy": {"imageTag": image_tag, "backendPort": backend_port, "frontendPort": frontend_port},
        "recoverySet": {
            "id": backup_id,
            "status": "COMPLETE" if recovery_set_complete else "BLOCKED",
            "program": {"imageTag": image_tag},
            "mysql": {"dumpPath": f"mysql/{db_name}.sql.gz"},
            "minio": {"bucket": bucket, "snapshotPath": "objects/manifest-object-inventory.json"},
            "businessFiles": {"snapshotPath": "objects/manifest-object-inventory.json"},
            "dcc": {"manifestPath": "manifest/dcc-backup-manifest.json"},
            "redis": {"policy": "CLEAR_AND_REBUILD"},
            "configuration": {"manifestPath": "deploy/runtime.env", "composePath": "deploy/docker-compose.yml"},
            "checksums": {"path": "manifest/checksums.txt", "sha256": checksums_hash},
        },
        "backupStrategy": build_backup_strategy(mysql_backup_mode, workspace),
        "validation": {
            "mysqlDumpCreated": True,
            "objectBackupCreated": True,
            "checksumsGenerated": True,
            "syncedToTestServer": True,
            "rehearsalStatus": "not-run",
            "lastRehearsedAt": None,
        },
        "notes": [],
    }
    ensure_dir(workspace / "manifest")
    (workspace / "manifest" / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def assert_backup_success_artifacts(workspace: Path, config: dict) -> None:
    db_name = get_required(config, ["backup", "mysqlDatabase"], "backup.mysqlDatabase")
    manifest_path = workspace / "manifest" / "manifest.json"
    required_files = [
        workspace / "deploy" / "docker-compose.yml",
        workspace / "deploy" / "runtime.env",
        workspace / "deploy" / "image-tag.txt",
        workspace / "mysql" / f"{db_name}.sql.gz",
        workspace / "objects" / "manifest-object-inventory.json",
        workspace / "manifest" / "dcc-database-snapshot.json",
        workspace / "manifest" / "dcc-backup-manifest.json",
        workspace / "manifest" / "checksums.txt",
        manifest_path,
    ]
    missing = [str(path) for path in required_files if not path.is_file()]
    empty = [str(path) for path in required_files if path.is_file() and path.stat().st_size <= 0]
    if missing or empty:
        raise BackupOpsError(
            "INTBK-6002",
            "blocked",
            "Backup success artifact validation failed. "
            f"missing={missing}; empty={empty}. "
            "Do not mark backup-now as success until the recovery set is complete.",
        )
    manifest = read_json(manifest_path)
    recovery_set = manifest.get("recoverySet", {})
    if manifest.get("status") != "success" or recovery_set.get("status") != "COMPLETE":
        raise BackupOpsError(
            "INTBK-6002",
            "blocked",
            "Backup success manifest is not complete: "
            f"status={manifest.get('status')} recoverySet.status={recovery_set.get('status')}.",
        )


def assert_runtime_images_available(image_tag: str, runner: Runner) -> None:
    missing = []
    for image_name in ["intruoyi-backend", "intruoyi-frontend"]:
        command = (
            "docker image inspect {0}:{1} >/dev/null 2>&1".format(
                shlex.quote(image_name),
                shlex.quote(image_tag),
            )
        )
        try:
            runner.run(command, "INTBK-6003", f"Missing runtime image {image_name}:{image_tag}")
        except BackupOpsError:
            missing.append(f"{image_name}:{image_tag}")
    if missing:
        raise BackupOpsError(
            "INTBK-6003",
            "blocked",
            "Runtime image version contract is incomplete. "
            f"Missing local image(s): {missing}. "
            "Build or deploy backend and frontend with the same IMAGE_TAG before creating a recoverable backup.",
        )
    runner.log(f"runtime-image-contract imageTag={image_tag} components=intruoyi-backend,intruoyi-frontend")


def publish_backup_workspace(staging_root: Path, final_root: Path, config: dict, runner: Runner) -> None:
    if final_root.exists():
        raise BackupOpsError(
            "INTBK-6002",
            "blocked",
            f"Backup target already exists and will not be overwritten: {final_root}",
        )
    assert_backup_success_artifacts(staging_root, config)
    ensure_dir(final_root.parent)
    cp_path = require_executable(
        CP_PATH,
        "INTBK-6002",
        f"{CP_PATH} is required to publish backup workspace to NAS without losing staging data.",
    )
    runner.run(
        "{0} -a {1} {2}".format(
            shlex.quote(cp_path),
            shlex.quote(str(staging_root)),
            shlex.quote(str(final_root)),
        ),
        "INTBK-6002",
        "Failed to publish backup workspace to backup root.",
    )
    runner.run("sync", "INTBK-6002", "Failed to flush backup workspace after NAS publish.")
    time.sleep(5)
    parent_entries = [path.name for path in final_root.parent.iterdir()]
    if final_root.name not in parent_entries:
        raise BackupOpsError(
            "INTBK-6002",
            "blocked",
            f"Backup target disappeared after NAS publish: {final_root}. "
            f"Source staging is preserved at {staging_root}.",
        )
    assert_backup_success_artifacts(final_root, config)
    shutil.rmtree(staging_root)


def write_rehearsal_evidence(backup_root: Path, backup_id: str, status: str, verified_at: str, checks: dict, error_message: str = "") -> None:
    if status not in {"PASSED", "FAILED"}:
        raise BackupOpsError("INTBK-7002", "fail", f"Unsupported rehearsal evidence status: {status}")

    manifest_dir = backup_root / "manifest"
    manifest_path = manifest_dir / "manifest.json"
    if not manifest_path.exists():
        raise BackupOpsError("INTBK-7002", "blocked", f"Backup manifest is missing: {manifest_path}")

    ensure_dir(manifest_dir)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    validation = manifest.setdefault("validation", {})
    validation["rehearsalStatus"] = status
    validation["lastRehearsedAt"] = verified_at
    validation["rehearsalChecks"] = checks
    if error_message:
        validation["rehearsalError"] = error_message
    elif "rehearsalError" in validation:
        del validation["rehearsalError"]
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    report = {
        "status": status,
        "backupId": backup_id,
        "verifiedAt": verified_at,
        "checks": checks,
    }
    if error_message:
        report["error"] = error_message
    (manifest_dir / "rehearsal-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    summary_lines = [
        "# 现场快照",
        "",
        f"- 演练对象: Linux backup-ops rehearsal",
        f"- 备份点: {backup_id}",
        f"- 时间: {verified_at}",
        f"- 结果: {status}",
        "- 关键校验摘要:",
    ]
    for name, result in checks.items():
        summary_lines.append(f"  - {name}: {result}")
    if error_message:
        summary_lines.append(f"- 失败原因: {error_message}")
    (manifest_dir / "现场快照.md").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")


def pick_latest_backup(backup_root: Path) -> str:
    candidates = []
    for child in sorted(backup_root.iterdir(), reverse=True):
        if not child.is_dir() or not is_backup_point_name(child.name):
            continue
        manifest_path = child / "manifest" / "manifest.json"
        if not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        validation = manifest.get("validation", {})
        if manifest.get("status") != "success":
            continue
        if not validation.get("mysqlDumpCreated") or not validation.get("objectBackupCreated") or not validation.get("checksumsGenerated"):
            continue
        candidates.append(child.name)
    if not candidates:
        raise BackupOpsError("INTBK-1004", "blocked", "No valid backup point exists for restore-data.")
    return candidates[0]


def is_scheduled_rehearsal_operator(operator_name: str) -> bool:
    return (operator_name or "").strip().lower() == "scheduler"


def get_rehearsal_config(config: dict) -> dict:
    return get_required(config, ["rehearsal"], "rehearsal")


def get_rehearsal_validation(config: dict) -> dict:
    return get_required(config, ["rehearsal", "validation"], "rehearsal.validation")


def get_rollback_candidates(config: dict) -> list:
    runtime = get_runtime_paths(config)
    current_image_tag = get_env_value(read_env_lines(runtime["env"]), "IMAGE_TAG")
    backup_root = Path(get_required(config, ["servers", "test", "backupPointsRoot"], "servers.test.backupPointsRoot"))
    candidates = []
    seen = set()
    for child in sorted(backup_root.iterdir(), reverse=True):
        if not child.is_dir() or not is_backup_point_name(child.name):
            continue
        image_tag_path = child / "deploy" / "image-tag.txt"
        if not image_tag_path.exists():
            continue
        tag = image_tag_path.read_text(encoding="utf-8").strip()
        if not tag or tag == current_image_tag or tag in seen:
            continue
        seen.add(tag)
        candidates.append(tag)
    return candidates


def wait_http_ok(url: str, timeout: int = 180) -> None:
    deadline = time.time() + timeout
    last_error = "unknown"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if 200 <= response.getcode() < 400:
                    return
                last_error = f"HTTP {response.getcode()}"
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
        time.sleep(3)
    raise BackupOpsError("INTBK-5003", "fail", f"Health check timed out for {url}. Last error: {last_error}")


def backup_now(config: dict, runner: Runner) -> dict:
    runtime = get_runtime_paths(config)
    env_lines = read_env_lines(runtime["env"])
    image_tag = get_env_value(env_lines, "IMAGE_TAG")
    if not image_tag:
        raise BackupOpsError("INTBK-5001", "blocked", "Missing IMAGE_TAG in runtime .env")
    backend_port = get_required_runtime_port(env_lines, "BACKEND_HOST_PORT", "INTBK-5003")
    frontend_port = get_required_runtime_port(env_lines, "FRONTEND_HOST_PORT", "INTBK-5003")
    assert_runtime_images_available(image_tag, runner)
    mysql_password = get_env_value(env_lines, "MYSQL_ROOT_PASSWORD")
    if not mysql_password:
        raise BackupOpsError("INTBK-3001", "blocked", "Missing MYSQL_ROOT_PASSWORD in runtime .env")

    backup_id = backup_sequence()
    backup_points_root = Path(get_required(config, ["servers", "test", "backupPointsRoot"], "servers.test.backupPointsRoot"))
    staging_base = Path(get_required(config, ["servers", "test", "tmpRoot"], "servers.test.tmpRoot")) / "backup-now-staging"
    backup_root = staging_base / backup_id
    final_backup_root = backup_points_root / backup_id
    if backup_root.exists():
        raise BackupOpsError(
            "INTBK-6002",
            "blocked",
            f"Backup staging target already exists and will not be overwritten: {backup_root}",
        )
    ensure_dir(backup_root / "deploy")
    ensure_dir(backup_root / "mysql")
    ensure_dir(backup_root / "objects")

    shutil.copy2(str(runtime["compose"]), str(backup_root / "deploy" / "docker-compose.yml"))
    shutil.copy2(str(runtime["env"]), str(backup_root / "deploy" / "runtime.env"))
    (backup_root / "deploy" / "image-tag.txt").write_text(image_tag + "\n", encoding="utf-8")

    db_name = get_required(config, ["backup", "mysqlDatabase"], "backup.mysqlDatabase")
    mysql_container = get_required(config, ["containers", "mysql"], "containers.mysql")
    mysql_backup_mode = resolve_mysql_backup_mode(config)
    if mysql_backup_mode.startswith("binlog"):
        preflight = write_mysql_binlog_preflight(backup_root, config, runner, mysql_container, mysql_password)
        export_mysql_binlog_segment(backup_root, runner, mysql_container, mysql_password, preflight)
    dump_path = backup_root / "mysql" / f"{db_name}.sql.gz"
    dump_command = "mysqldump --single-transaction --routines --triggers --hex-blob -uroot -p{0} {1} | gzip -c".format(
        shlex.quote(mysql_password),
        shlex.quote(db_name),
    )
    runner.run(
        "docker exec {0} sh -lc {1} > {2}".format(
            shlex.quote(mysql_container),
            shlex.quote(dump_command),
            shlex.quote(str(dump_path)),
        ),
        "INTBK-3001",
        "MySQL dump export failed.",
    )

    bucket = get_required(config, ["backup", "objectBucket"], "backup.objectBucket")
    minio_client_image = get_required(config, ["tools", "minioClientImage"], "tools.minioClientImage")
    minio_container = get_required(config, ["containers", "minio"], "containers.minio")
    access_key, secret_key = get_minio_creds(minio_container)
    metadata_command = "mc alias set src http://127.0.0.1:9000 {0} {1} >/dev/null && mc ls --recursive --json src/{2}".format(
        shlex.quote(access_key),
        shlex.quote(secret_key),
        shlex.quote(bucket),
    )
    metadata_output = runner.run(
        "docker run --rm --network host --entrypoint /bin/sh {0} -c {1}".format(
            shlex.quote(minio_client_image),
            shlex.quote(metadata_command),
        ),
        "INTBK-4001",
        "Object bucket metadata scan failed.",
    )
    object_inventory = build_incremental_object_inventory(backup_root, config, backup_id, metadata_output, runner)
    copy_incremental_objects_from_minio(backup_root, config, object_inventory, access_key, secret_key, runner)
    object_inventory = publish_object_inventory_to_store(backup_root, config, object_inventory)

    write_dcc_backup_contract(backup_root, backup_id, config, runner, mysql_password, object_inventory)
    write_checksums(backup_root)
    write_manifest(backup_root, backup_id, "manual", config, image_tag, backend_port, frontend_port)
    publish_backup_workspace(backup_root, final_backup_root, config, runner)
    return {"backupId": backup_id, "imageTag": image_tag, "stagingRoot": str(backup_root), "backupRoot": str(final_backup_root)}


def restore_data(config: dict, runner: Runner, selected_backup_id: str) -> dict:
    if config.get("environment") not in {"test", "backup"}:
        raise BackupOpsError(
            "INTBK-3002",
            "blocked",
            "restore-data only supports --target-environment test or backup; production restore-data is forbidden.",
        )
    if not selected_backup_id:
        raise BackupOpsError("INTBK-3002", "blocked", "restore-data requires explicit selected_backup_id.")
    runtime = get_runtime_paths(config)
    env_lines = read_env_lines(runtime["env"])
    current_image_tag = get_env_value(env_lines, "IMAGE_TAG")
    mysql_password = get_env_value(env_lines, "MYSQL_ROOT_PASSWORD")
    if not mysql_password:
        raise BackupOpsError("INTBK-3002", "blocked", "Missing MYSQL_ROOT_PASSWORD in runtime .env")
    backend_port = get_required_runtime_port(env_lines, "BACKEND_HOST_PORT", "INTBK-5003")
    frontend_port = get_required_runtime_port(env_lines, "FRONTEND_HOST_PORT", "INTBK-5003")
    backup_points_root = Path(get_required(config, ["servers", "test", "backupPointsRoot"], "servers.test.backupPointsRoot"))
    backup_id = selected_backup_id
    backup_root = backup_points_root / backup_id
    manifest_path = backup_root / "manifest" / "manifest.json"
    if not manifest_path.is_file():
        raise BackupOpsError("INTBK-3002", "blocked", f"Restore manifest is missing: {manifest_path}")
    manifest = read_json(manifest_path)
    recovery_set = manifest.get("recoverySet")
    if not isinstance(recovery_set, dict):
        raise BackupOpsError("INTBK-3002", "blocked", "Restore manifest is missing recoverySet.")
    if recovery_set.get("id") != backup_id:
        raise BackupOpsError("INTBK-3002", "blocked", "Restore manifest recoverySet.id does not match selected backup id.")
    if recovery_set.get("status") != "COMPLETE":
        raise BackupOpsError("INTBK-3002", "blocked", f"Restore manifest recoverySet is not COMPLETE: {recovery_set.get('status')}")
    if not recovery_set.get("checksums", {}).get("sha256"):
        raise BackupOpsError("INTBK-3002", "blocked", "Restore manifest recoverySet.checksums.sha256 is missing.")
    assert_restore_manifest_rehearsed(manifest)
    assert_restore_manifest_backup_strategy(manifest)
    assert_restore_dcc_manifest_scope(recovery_set, backup_root)
    assert_restore_recovery_set_scope(recovery_set, current_image_tag)
    assert_restore_object_inventory_ready(backup_root, config, backup_points_root)
    db_name = get_required(config, ["backup", "mysqlDatabase"], "backup.mysqlDatabase")
    mysql_container = get_required(config, ["containers", "mysql"], "containers.mysql")
    dump_path = backup_root / "mysql" / f"{db_name}.sql.gz"
    if not dump_path.exists():
        raise BackupOpsError("INTBK-3002", "blocked", f"Restore dump is missing: {dump_path}")

    pre_restore_root = Path(get_required(config, ["servers", "production", "tmpRoot"], "servers.production.tmpRoot")) / backup_id / "pre-restore" / f"{now_sequence()}_pre-restore"
    ensure_dir(pre_restore_root)
    shutil.copy2(str(runtime["compose"]), str(pre_restore_root / "docker-compose.yml"))
    shutil.copy2(str(runtime["env"]), str(pre_restore_root / "runtime.env"))

    runner.run(
        "cd {0} && docker compose stop backend frontend".format(shlex.quote(str(runtime["app_dir"]))),
        "INTBK-5002",
        "Failed to stop backend/frontend before restore.",
    )

    reset_sql = pre_restore_root / "reset-db.sql"
    reset_sql.write_text(
        "DROP DATABASE IF EXISTS `{0}`;\nCREATE DATABASE `{0}` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;\n".format(db_name),
        encoding="utf-8",
    )
    runner.run(
        "docker exec -i {0} mysql -uroot -p{1} < {2}".format(
            shlex.quote(mysql_container),
            shlex.quote(mysql_password),
            shlex.quote(str(reset_sql)),
        ),
        "INTBK-3002",
        "Failed to reset target database before import.",
    )
    runner.run(
        "gunzip -c {0} | docker exec -i {1} mysql -uroot -p{2} {3}".format(
            shlex.quote(str(dump_path)),
            shlex.quote(mysql_container),
            shlex.quote(mysql_password),
            shlex.quote(db_name),
        ),
        "INTBK-3002",
        "MySQL restore failed.",
    )

    bucket = get_required(config, ["backup", "objectBucket"], "backup.objectBucket")
    minio_client_image = get_required(config, ["tools", "minioClientImage"], "tools.minioClientImage")
    minio_container = get_required(config, ["containers", "minio"], "containers.minio")
    access_key, secret_key = get_minio_creds(minio_container)
    objects_source = materialize_restore_objects_from_inventory(backup_root, config, backup_points_root)
    restore_command = "mc alias set dst http://127.0.0.1:9000 {0} {1} && mc mb --ignore-existing dst/{2} && mc mirror --overwrite --remove /restore dst/{2}".format(
        shlex.quote(access_key),
        shlex.quote(secret_key),
        shlex.quote(bucket),
    )
    runner.run(
        "docker run --rm --network host --entrypoint /bin/sh -v {0}:/restore {1} -c {2}".format(
            shlex.quote(str(objects_source)),
            shlex.quote(minio_client_image),
            shlex.quote(restore_command),
        ),
        "INTBK-4002",
        "Object restore failed.",
    )

    runner.run(
        "cd {0} && docker compose up -d backend frontend".format(shlex.quote(str(runtime["app_dir"]))),
        "INTBK-5002",
        "Failed to start backend/frontend after restore.",
    )
    wait_http_ok(f"http://127.0.0.1:{backend_port}/actuator/health")
    wait_http_ok(f"http://127.0.0.1:{frontend_port}/")
    return {"restorePoint": backup_id}


def rollback_app(config: dict, runner: Runner, selected_image_tag: str) -> dict:
    if not selected_image_tag:
        raise BackupOpsError("INTBK-5001", "blocked", "rollback-app requires explicit selected_image_tag.")
    target_environment = config.get("environment", "test")
    release_packages_root = Path(get_required(
        config,
        ["servers", target_environment, "releasePackagesRoot"],
        f"servers.{target_environment}.releasePackagesRoot",
    ))
    runtime = get_runtime_paths(config)
    env_path = runtime["env"]
    env_lines = read_env_lines(env_path)
    backend_port = get_required_runtime_port(env_lines, "BACKEND_HOST_PORT", "INTBK-5003")
    frontend_port = get_required_runtime_port(env_lines, "FRONTEND_HOST_PORT", "INTBK-5003")
    image_tag = selected_image_tag
    compatibility_path = release_packages_root / image_tag / "rollback-compatibility.json"
    if not compatibility_path.is_file():
        raise BackupOpsError("INTBK-5001", "blocked", f"rollback-compatibility.json is required for rollback image tag: {image_tag}")
    compatibility = read_json(compatibility_path)
    if compatibility.get("status") != "COMPATIBLE":
        raise BackupOpsError("INTBK-5001", "blocked", f"rollback compatibility status is not COMPATIBLE: {compatibility.get('status')}")

    tmp_root = Path(get_required(config, ["servers", "production", "tmpRoot"], "servers.production.tmpRoot"))
    backup_dir = tmp_root / "rollback-app" / now_sequence()
    ensure_dir(backup_dir)
    shutil.copy2(str(env_path), str(backup_dir / "runtime.env"))

    updated_lines = set_env_value(env_lines, "IMAGE_TAG", image_tag)
    env_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")

    runner.run(
        "cd {0} && docker compose up -d backend frontend".format(shlex.quote(str(runtime["app_dir"]))),
        "INTBK-5002",
        "Failed to restart backend/frontend for rollback-app.",
    )
    wait_http_ok(f"http://127.0.0.1:{backend_port}/actuator/health")
    wait_http_ok(f"http://127.0.0.1:{frontend_port}/")
    return {"imageTag": image_tag}


def rehearsal(config: dict, runner: Runner, selected_backup_id: str, operator_name: str = "") -> dict:
    if not selected_backup_id and not is_scheduled_rehearsal_operator(operator_name):
        raise BackupOpsError(
            "INTBK-7001",
            "blocked",
            "rehearsal requires explicit selected_backup_id unless operator_name is scheduler.",
        )
    runtime = get_runtime_paths(config)
    env_lines = read_env_lines(runtime["env"])
    mysql_password = get_env_value(env_lines, "MYSQL_ROOT_PASSWORD")
    if not mysql_password:
        raise BackupOpsError("INTBK-7001", "blocked", "Missing MYSQL_ROOT_PASSWORD in runtime .env")

    rehearsal_cfg = get_rehearsal_config(config)
    validation = get_rehearsal_validation(config)
    backup_points_root = Path(get_required(config, ["servers", "test", "backupPointsRoot"], "servers.test.backupPointsRoot"))
    backup_id = selected_backup_id or pick_latest_backup(backup_points_root)
    backup_root = backup_points_root / backup_id
    rehearsal_root = Path(get_required(config, ["servers", "test", "rehearsalRoot"], "servers.test.rehearsalRoot"))
    backend_port = int(get_required(config, ["servers", "test", "rehearsalBackendPort"], "servers.test.rehearsalBackendPort"))
    frontend_port = int(get_required(config, ["servers", "test", "rehearsalFrontendPort"], "servers.test.rehearsalFrontendPort"))
    db_name = get_required(config, ["backup", "mysqlDatabase"], "backup.mysqlDatabase")
    bucket = get_required(config, ["backup", "objectBucket"], "backup.objectBucket")
    minio_client_image = get_required(config, ["tools", "minioClientImage"], "tools.minioClientImage")
    target_bucket = get_required(config, ["rehearsal", "bucket"], "rehearsal.bucket")
    runtime_name = get_required(config, ["rehearsal", "runtimeNamePrefix"], "rehearsal.runtimeNamePrefix")
    mysql_container = get_required(config, ["containers", "mysql"], "containers.mysql")
    minio_container = get_required(config, ["containers", "minio"], "containers.minio")

    existing_compose = rehearsal_root / "docker-compose.yml"
    if existing_compose.exists():
        runner.run(
            "cd {0} && docker compose down -v --remove-orphans || true".format(shlex.quote(str(rehearsal_root))),
            "INTBK-7001",
            "Failed to stop existing rehearsal runtime.",
        )
    if rehearsal_root.exists():
        shutil.rmtree(rehearsal_root)
    ensure_dir(rehearsal_root / "tmp")

    source_compose = backup_root / "deploy" / "docker-compose.yml"
    source_env = backup_root / "deploy" / "runtime.env"
    image_tag = (backup_root / "deploy" / "image-tag.txt").read_text(encoding="utf-8").strip()
    local_compose = rehearsal_root / "docker-compose.yml"
    local_env = rehearsal_root / ".env"
    shutil.copy2(str(source_compose), str(local_compose))
    shutil.copy2(str(source_env), str(local_env))

    env_lines = read_env_lines(local_env)
    env_lines = set_env_value(env_lines, "IMAGE_TAG", image_tag)
    env_lines = set_env_value(env_lines, "SERVER_HOST", get_required(config, ["servers", "test", "host"], "servers.test.host"))
    env_lines = set_env_value(env_lines, "BACKEND_HOST_PORT", str(backend_port))
    env_lines = set_env_value(env_lines, "FRONTEND_HOST_PORT", str(frontend_port))
    local_env.write_text("\n".join(env_lines) + "\n", encoding="utf-8")

    compose_text = local_compose.read_text(encoding="utf-8")
    compose_text = compose_text.replace("name: intruoyi-runtime", f"name: {runtime_name}")
    compose_text = compose_text.replace("container_name: intruoyi-mysql", f"container_name: {runtime_name}-mysql")
    compose_text = compose_text.replace("container_name: intruoyi-redis", f"container_name: {runtime_name}-redis")
    compose_text = compose_text.replace("container_name: intruoyi-backend", f"container_name: {runtime_name}-backend")
    compose_text = compose_text.replace("container_name: intruoyi-frontend", f"container_name: {runtime_name}-frontend")
    compose_text = compose_text.replace(
        "      onlyoffice:\n"
        "        condition: service_healthy\n",
        "",
    )
    onlyoffice_start = compose_text.find("\n  onlyoffice:\n")
    frontend_start = compose_text.find("\n  frontend:\n")
    if onlyoffice_start != -1 and frontend_start != -1 and onlyoffice_start < frontend_start:
        compose_text = compose_text[:onlyoffice_start] + compose_text[frontend_start:]
    local_compose.write_text(compose_text, encoding="utf-8")

    runner.run(
        "cd {0} && docker compose up -d mysql redis".format(shlex.quote(str(rehearsal_root))),
        "INTBK-7001",
        "Failed to start rehearsal mysql/redis.",
    )
    wait_container = "{0}-mysql".format(runtime_name)
    deadline = time.time() + 180
    while time.time() < deadline:
        health = subprocess.run(
            "docker inspect --format {0} {1}".format(
                shlex.quote("{{.State.Health.Status}}"),
                shlex.quote(wait_container),
            ),
            shell=True,
            executable="/bin/bash",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            universal_newlines=True,
        )
        status = subprocess.run(
            "docker exec {0} mysql -h127.0.0.1 -uroot -p{1} -e {2}".format(
                shlex.quote(wait_container),
                shlex.quote(mysql_password),
                shlex.quote("SELECT 1"),
            ),
            shell=True,
            executable="/bin/bash",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            universal_newlines=True,
        )
        if health.returncode == 0 and health.stdout.strip() == "healthy" and status.returncode == 0:
            break
        time.sleep(3)
    else:
        raise BackupOpsError("INTBK-7001", "fail", "Rehearsal MySQL did not become ready in time.")

    dump_path = backup_root / "mysql" / "{0}.sql.gz".format(db_name)
    reset_sql = rehearsal_root / "tmp" / "reset-db.sql"
    reset_sql.write_text(
        "DROP DATABASE IF EXISTS `{0}`;\nCREATE DATABASE `{0}` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;\n".format(db_name),
        encoding="utf-8",
    )
    rehearsal_mysql = "{0}-mysql".format(runtime_name)
    runner.run(
        "docker exec -i {0} mysql -h127.0.0.1 -uroot -p{1} < {2}".format(
            shlex.quote(rehearsal_mysql),
            shlex.quote(mysql_password),
            shlex.quote(str(reset_sql)),
        ),
        "INTBK-7001",
        "Failed to reset rehearsal database.",
    )
    runner.run(
        "gunzip -c {0} | docker exec -i {1} mysql -h127.0.0.1 -uroot -p{2} {3}".format(
            shlex.quote(str(dump_path)),
            shlex.quote(rehearsal_mysql),
            shlex.quote(mysql_password),
            shlex.quote(db_name),
        ),
        "INTBK-7001",
        "Failed to import rehearsal database.",
    )
    binlog_replay = replay_mysql_binlog_segments(backup_root, runner, rehearsal_mysql, mysql_password, db_name)

    access_key, secret_key = get_minio_creds(minio_container)
    objects_source = backup_root / "objects" / bucket
    restore_command = "mc alias set dst http://127.0.0.1:9000 {0} {1} && mc mb --ignore-existing dst/{2} && mc mirror --overwrite /restore dst/{2}".format(
        shlex.quote(access_key),
        shlex.quote(secret_key),
        shlex.quote(target_bucket),
    )
    runner.run(
        "docker run --rm --network host --entrypoint /bin/sh -v {0}:/restore {1} -c {2}".format(
            shlex.quote(str(objects_source)),
            shlex.quote(minio_client_image),
            shlex.quote(restore_command),
        ),
        "INTBK-7001",
        "Failed to restore rehearsal object bucket.",
    )

    patch_sql = rehearsal_root / "tmp" / "rehearsal-post-import.sql"
    domain = "http://127.0.0.1:9000/{0}".format(target_bucket)
    patch_sql.write_text(
        (
            "UPDATE infra_file_config\n"
            "SET config = REPLACE(REPLACE(config, '\"bucket\":\"yudao\"', '\"bucket\":\"{bucket}\"'), '\"domain\":\"http:///yudao\"', '\"domain\":\"{domain}\"')\n"
            "WHERE id = {config_id};\n"
            "UPDATE infra_file SET url = CONCAT('{domain}/', path) WHERE config_id = {config_id};\n"
        ).format(bucket=target_bucket, domain=domain, config_id=validation["fileConfigId"]),
        encoding="utf-8",
    )
    runner.run(
        "docker exec -i {0} mysql -h127.0.0.1 -uroot -p{1} {2} < {3}".format(
            shlex.quote(rehearsal_mysql),
            shlex.quote(mysql_password),
            shlex.quote(db_name),
            shlex.quote(str(patch_sql)),
        ),
        "INTBK-7001",
        "Failed to patch rehearsal file metadata.",
    )

    runner.run(
        "cd {0} && docker compose up -d backend frontend".format(shlex.quote(str(rehearsal_root))),
        "INTBK-7001",
        "Failed to start rehearsal backend/frontend.",
    )
    host_gateway = "host.docker.internal"
    backend_origin = f"http://{host_gateway}:{backend_port}"
    frontend_origin = f"http://{host_gateway}:{frontend_port}"
    wait_http_ok(f"{backend_origin}/actuator/health")
    wait_http_ok(f"{frontend_origin}/")

    login_body = json.dumps({"username": validation["username"], "password": validation["password"]}).encode("utf-8")
    request = urllib.request.Request(
        f"{backend_origin}/admin-api/system/auth/login",
        data=login_body,
        headers={"Content-Type": "application/json", "tenant-id": str(validation["tenantId"])},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("code") != 0 or not payload.get("data", {}).get("accessToken"):
        raise BackupOpsError("INTBK-7002", "fail", "Rehearsal login validation failed.")

    sample_request = urllib.request.Request(
        "{0}/admin-api/infra/file/{1}/get/{2}".format(
            backend_origin,
            validation["fileConfigId"],
            validation["sampleFilePath"],
        ),
        headers={"Authorization": "Bearer " + payload["data"]["accessToken"]},
        method="HEAD",
    )
    with urllib.request.urlopen(sample_request, timeout=10) as response:
        if response.getcode() < 200 or response.getcode() >= 400:
            raise BackupOpsError("INTBK-7002", "fail", "Rehearsal sample file validation failed.")

    verified_at = datetime.now().isoformat()
    checks = {
        "backendHealth": "pass",
        "frontendHttp200": "pass",
        "loginReachable": "pass",
        "fileDownloadSample": "pass",
        "mysqlBinlogReplay": binlog_replay["status"],
    }
    write_rehearsal_evidence(backup_root, backup_id, "PASSED", verified_at, checks)

    return {
        "backupId": backup_id,
        "verifiedAt": verified_at,
        "checks": checks,
    }


def validate_linux_local_config(config: dict) -> None:
    mode = get_required(config, ["execution", "mode"], "execution.mode")
    if mode != "linux-local":
        raise BackupOpsError("INTBK-1003", "blocked", f"Unsupported execution.mode for linux runtime: {mode}")


def assert_production_backup_confirmation(confirm_text: str) -> None:
    expected_confirm_text = "PROD-BACKUP-172.30.30.57"
    if not confirm_text.strip():
        raise BackupOpsError(
            "INTBK-1003",
            "blocked",
            "Production backup confirmation is required before running backup-now or backup-scheduled "
            f"against --target-environment prod. Rerun with --production-backup-confirm-text {expected_confirm_text}.",
        )
    if confirm_text.strip() != expected_confirm_text:
        raise BackupOpsError(
            "INTBK-1003",
            "blocked",
            "Production backup confirmation text is incorrect; expected "
            f"{expected_confirm_text}.",
        )


def project_target_environment(config: dict, mode: str, target_environment: str, production_backup_confirm_text: str) -> dict:
    if mode == "restore-data" and target_environment == "prod":
        raise BackupOpsError(
            "INTBK-1003",
            "blocked",
            "restore-data only supports --target-environment test or backup; production restore-data is forbidden.",
        )
    if mode in {"backup-now", "backup-scheduled"} and target_environment == "prod":
        assert_production_backup_confirmation(production_backup_confirm_text)
    if target_environment == "prod":
        return config
    if target_environment not in {"test", "backup"}:
        raise BackupOpsError("INTBK-1003", "blocked", "target-environment must be prod, test, or backup")
    if mode not in {"backup-now", "backup-scheduled", "rollback-app", "restore-data"}:
        raise BackupOpsError(
            "INTBK-1003",
            "blocked",
            "target-environment test/backup is only supported for backup-now, backup-scheduled, rollback-app and restore-data",
        )

    target_host = get_required(config, ["servers", target_environment, "host"], f"servers.{target_environment}.host")
    target_runtime_dir = get_required(
        config,
        ["servers", target_environment, "runtimeDir"],
        f"servers.{target_environment}.runtimeDir",
    )
    target_tmp_root = get_required(
        config,
        ["servers", target_environment, "tmpRoot"],
        f"servers.{target_environment}.tmpRoot",
    )
    target_minio_container = get_required(
        config,
        ["servers", target_environment, "minioContainer"],
        f"servers.{target_environment}.minioContainer",
    )
    projected = copy.deepcopy(config)
    projected["environment"] = target_environment
    projected["servers"]["production"]["host"] = target_host
    projected["servers"]["production"]["appDir"] = target_runtime_dir
    projected["servers"]["production"]["tmpRoot"] = target_tmp_root
    projected["containers"]["minio"] = target_minio_container
    return projected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--secrets", required=False, default="")
    parser.add_argument("--selected-backup-id", default="")
    parser.add_argument("--selected-image-tag", default="")
    parser.add_argument("--operator-name", default="")
    parser.add_argument("--target-environment", choices=["prod", "test", "backup"], default="prod")
    parser.add_argument("--production-backup-confirm-text", default="")
    parser.add_argument("--non-interactive", action="store_true")
    args = parser.parse_args()

    if args.mode not in SUPPORTED_MODES:
        print(f"Unsupported linux-local mode: {args.mode}")
        return 2

    config = read_json(Path(args.config))
    validate_linux_local_config(config)
    runner = Runner(config, args.mode)
    try:
        config = project_target_environment(
            config,
            args.mode,
            args.target_environment,
            args.production_backup_confirm_text,
        )
        if args.mode in {"backup-now", "backup-scheduled"}:
            context = backup_now(config, runner)
            return runner.finalize("success", "INTBK-0000", "Linux local backup completed successfully.", context)
        if args.mode == "rollback-app":
            context = rollback_app(config, runner, args.selected_image_tag)
            return runner.finalize("success", "INTBK-0000", "Linux local rollback completed successfully.", context)
        if args.mode == "rehearsal":
            context = rehearsal(config, runner, args.selected_backup_id, args.operator_name)
            return runner.finalize("success", "INTBK-0000", "Linux local rehearsal completed successfully.", context)
        context = restore_data(config, runner, args.selected_backup_id)
        return runner.finalize("success", "INTBK-0000", "Linux local restore completed successfully.", context)
    except BackupOpsError as exc:
        return runner.finalize(exc.status, exc.code, exc.message, {})


if __name__ == "__main__":
    sys.exit(main())
