"""Execute target data checks before schema rehearsal or expensive release builds."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from release_build_preflight import build_evidence, assert_qualifies
from release_target_preflight_contract import validate, METADATA_PATTERN


class TargetDataPreflightError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError(f'JSON object required: {path.name}')
    return value


def _query(server: str, user: str, content: bytes) -> str:
    # Input bytes and credentials never become shell command arguments or logs.
    sql = b'SET SESSION TRANSACTION READ ONLY;\nSTART TRANSACTION READ ONLY;\n' + content + b'\nROLLBACK;\n'
    encoded = base64.b64encode(sql).decode('ascii')
    script = '''set -euo pipefail
mysql_password=$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' intruoyi-mysql | sed -n 's/^MYSQL_ROOT_PASSWORD=//p' | tail -n 1)
test -n "$mysql_password"
printf '%s' '__SQL__' | base64 -d | docker exec -i -e MYSQL_PWD="$mysql_password" intruoyi-mysql mysql --binary-mode --protocol=TCP -h127.0.0.1 -uroot --default-character-set=utf8mb4 --batch --raw --skip-column-names ruoyi-vue-pro
'''.replace('__SQL__', encoded)
    try:
        result = subprocess.run(
            ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
             '-o', 'ConnectTimeout=15', f'{user}@{server}', 'bash -s'],
            input=script.encode('utf-8'), capture_output=True, timeout=90, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise TargetDataPreflightError('TARGET_PREFLIGHT_TIMEOUT', 'read-only query exceeded 90 seconds') from exc
    if result.returncode != 0:
        # mysql/ssh errors may echo data or credentials: expose the failure category only.
        match = re.search(rb'ERROR\s+(\d+)\s+\(([A-Z0-9]+)\)', result.stderr)
        code = match.group(0).decode('ascii') if match else f'exit {result.returncode}'
        raise TargetDataPreflightError('TARGET_PREFLIGHT_QUERY_FAILED', f'read-only target query failed: {code}')
    return result.stdout.decode('utf-8', errors='strict').strip()


def run(args: argparse.Namespace, report: dict) -> None:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.-]*', args.server):
        raise ValueError('invalid target server')
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_-]*', args.user):
        raise ValueError('invalid SSH user')
    manifest_path = Path(args.prospective_manifest)
    evidence = build_evidence(manifest_path, Path(args.target_state), target_environment='test',
                              publish_scope='app-release', package_root=Path(args.package_root))
    assert_qualifies(evidence)
    if evidence != _read(Path(args.build_evidence)):
        raise ValueError('build evidence does not match recomputed source/SQL/target/plan bindings')
    report['preflightFingerprint'] = evidence['bindings']['preflightFingerprint']
    report['collectionId'] = evidence['collectionId']
    report['targetEnvironment'] = 'test'
    report['server'] = args.server
    manifest = _read(manifest_path)
    metadata = {item['migrationId']: item for item in manifest['requiredSql']}
    required = []
    for item in evidence['planner']['items']:
        if item['action'] != 'APPLY':
            continue
        entry = metadata[item['migrationId']]
        if entry['type'] != 'schema' or entry.get('requiresTargetPreflight') is True:
            required.append(item)
    report['requiredCount'] = len(required)
    checks_root = Path(args.checks_root).resolve()
    missing = [item['migrationId'] for item in required
               if not (checks_root / (item['migrationId'] + '.preflight.sql')).is_file()]
    if missing:
        report['missingMigrationIds'] = missing
        raise TargetDataPreflightError('TARGET_PREFLIGHT_MISSING', f'{len(missing)} planned migrations lack read-only checks')
    checks = []
    for item in required:
        migration_id = item['migrationId']
        path = checks_root / f'{migration_id}.preflight.sql'
        if path.is_symlink() or path.resolve().parent != checks_root:
            raise ValueError(f'target preflight escapes check root: {migration_id}')
        content = path.read_bytes()
        validate(path, migration_id)
        if content != path.read_bytes():
            raise ValueError(f'target preflight changed during validation: {migration_id}')
        metadata_line = METADATA_PATTERN.search(content.decode('utf-8'))
        if 'test' not in metadata_line.group('environments').split(','):
            raise ValueError(f'target preflight does not allow test: {migration_id}')
        checks.append((migration_id, content, item['sha256']))
    # Validate the complete set before connecting, so missing or unsafe SQL cannot be hidden.
    for migration_id, content, migration_digest in checks:
        report['failedMigrationId'] = migration_id
        report['sshStarted'] = True
        output = _query(args.server, args.user, content)
        if output != f'TARGET_PREFLIGHT_PASS:{migration_id}':
            raise TargetDataPreflightError('TARGET_PREFLIGHT_FAILED', f'target prerequisites failed: {migration_id}')
        report['checks'].append({'migrationId': migration_id, 'migrationSha256': migration_digest,
                                 'checkSha256': hashlib.sha256(content).hexdigest(), 'readOnly': True,
                                 'status': 'passed'})
        report['passedCount'] += 1
    report['failedMigrationId'] = None
    report['status'] = 'passed'


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    for name in ('prospective-manifest', 'target-state', 'build-evidence', 'package-root',
                 'checks-root', 'server', 'user', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args(argv)
    report = {'schemaVersion': 'release-target-data-preflight/v1', 'status': 'failed',
              'requiredCount': 0, 'passedCount': 0, 'checks': [], 'sshStarted': False}
    try:
        run(args, report)
    except TargetDataPreflightError as exc:
        report['errorCode'] = exc.code
        report['detail'] = str(exc)
    except (OSError, ValueError, RuntimeError) as exc:
        report['errorCode'] = 'TARGET_PREFLIGHT_INPUT_INVALID'
        report['detail'] = str(exc)
    report['completedAt'] = datetime.now(timezone.utc).isoformat()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(f"Target data preflight: {report['status']}; {report['passedCount']}/{report['requiredCount']} checks")
    if report['status'] != 'passed':
        print(f"{report['errorCode']}: {report['detail']}; report={output}", file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
