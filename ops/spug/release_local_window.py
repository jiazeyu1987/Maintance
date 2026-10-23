"""Consume the existing environment terminal evidence; never release server holds."""
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MONITOR = ROOT / 'doc/tasks/20260929-three-server-release-monitor'
TERMINAL = ROOT / 'doc/tasks/20261007-three-server-runtime-alignment/backup-onlyoffice-existing-readiness-runtime-actual-terminal-main-v4.json'

def main():
    terminal = json.loads(TERMINAL.read_text(encoding='utf-8-sig'))
    if not (terminal['scopeReleaseEligible'] and terminal['sameCIDTerminalRemovedAbsent']
            and terminal['allOwnedClientsReadersJobsHandlesClosed'] and not terminal['pendingCreatePossibility']):
        raise SystemExit('Local window terminal is not release eligible')
    for key in ('grant', 'intent', 'result', 'source'):
        ref = terminal[key]
        raw = Path(ref['path']).read_bytes()
        if len(raw) != ref['bytes'] or hashlib.sha256(raw).hexdigest() != ref['sha256']:
            raise SystemExit(f'Terminal reference changed: {key}')
    result = subprocess.run(['docker', 'ps', '-a', '--filter', 'id=' + terminal['exactKnownCID'], '--format', '{{.ID}}'],
                            capture_output=True, text=True, timeout=30, check=True)
    if result.stdout.strip():
        raise SystemExit('Environment runtime container still exists')
    state_path = MONITOR / 'task-state.json'
    state = json.loads(state_path.read_text(encoding='utf-8-sig'))
    window = state['current_coordinated_local_engine_window']
    if window['window_id'] != terminal['scopeId']:
        raise SystemExit('Another local window is current; no release performed')
    now = datetime.now(timezone.utc).isoformat()
    window.update(window_active=False, whole_engine_reserved=False, supervisorReleased=True,
                  actualStarted=True, actualFinished=True, status='FAILED_N02_TERMINAL_SCOPE_RELEASED',
                  released_at=now, terminal_evidence=str(TERMINAL), container_absence_independently_verified=True)
    state['spug_integration'] = dict(requested_at=now, status='INSTALLING_LOCAL_ONLY',
        task_path='doc/tasks/20261010-spug-integration', loopback_port=18080,
        server_windows_unchanged=True, executor_code_unchanged=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    with (MONITOR / 'execution-log.md').open('a', encoding='utf-8') as stream:
        stream.write(f'\n\n## {now} 用户新增 Spug 接入\n\n'
                     '已核环境 v4 终态四项原件 SHA/长度及精确容器不存在，释放该本地引擎窗口。'
                     '不改变 TEST 失败保留或正式暂停。独立 Spug 本机安装接入复用后端，'
                     '任务目录 20261010-spug-integration，端口 127.0.0.1:18080；不改执行者发布源码。\n')
    print('Environment v4 terminal consumed; local window released; server holds retained.')

if __name__ == '__main__':
    main()
