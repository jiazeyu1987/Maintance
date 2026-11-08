"""Read-only acceptance of the same existing target transport after runtime recovery."""
import hashlib
import json
import socket
import subprocess
from pathlib import Path

from common import PRIVATE, TASK, now, write
from verify_stable_controls import SCRIPT


if __name__ == '__main__':
    baseline = json.loads((TASK / 'target-transports-current-baseline.json').read_text(encoding='utf-8'))
    assert baseline['status'] == 'PASS' and baseline['target58And59ForwardingSemanticsReviewed']
    pin = baseline['stableTransportPin']
    installed = Path(pin['path']).read_bytes()
    assert len(installed) == pin['bytes'] and hashlib.sha256(installed).hexdigest() == pin['sha256']
    script = SCRIPT.replace('TRANSPORT_SHA_LITERAL', pin['sha256']).replace('TRANSPORT_BYTES_LITERAL', str(pin['bytes']))
    script = script.replace("foreach($suffix in @('58','59'))", "foreach($suffix in @('58'))")
    result = subprocess.run([
        'C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe',
        '-NoProfile', '-NonInteractive', '-Command', script,
    ], capture_output=True, timeout=120)
    write(PRIVATE / 'transport-58-recovery-inspection.private.json', {
        'observedAt': now(), 'exitCode': result.returncode,
        'stdout': result.stdout.decode('utf-8-sig'), 'stderr': result.stderr.decode('utf-8-sig'),
    })
    assert result.returncode == 0, 'EXISTING_TARGET_TRANSPORT_NOT_ACCEPTED'
    route = json.loads(result.stdout.decode('utf-8-sig'))
    assert route['host'] == '172.30.30.58' and route['exactForwardingVerified']
    for port in (42657, 43658, 33659):
        with socket.create_connection(('127.0.0.1', port), timeout=3):
            pass
    ui = json.loads((TASK / 'restore-58-live-progress.json').read_text(encoding='utf-8'))
    submission = json.loads((TASK / 'restore-58-ui-submission.json').read_text(encoding='utf-8'))
    assert ui['operationId'] == submission['request']['operationId']
    assert not ui['errorCode'] and not ui['queryError'] and ui['writes'] == 0
    report = {
        'status': 'PASS', 'observedAt': now(), 'installedPin': pin, 'route': route,
        'sameSpugOperationId': ui['operationId'], 'spugObservationTime': ui['observedAt'],
        'sameOperationReadOnlyQueryRecovered': True, 'allThreeControlPortsReachable': True,
        'productionCodeOrConfigurationChanged': False, 'newRestoreDispatched': False,
        'completeRestoreAcceptance': False,
    }
    write(TASK / 'restore-58-transport-runtime-recovery.json', report)
    print(json.dumps(report))
