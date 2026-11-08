"""Read-only route timings and persistent-state size; no service construction."""
import collections
import json
import sqlite3
import time
import urllib.request
from pathlib import Path

from common import PRIVATE, TASK, now, write


def main():
    config = json.loads(Path('C:/SpugHandoff/release/executor.private.json').read_text('utf-8-sig'))
    db = Path(config['stateDir']) / 'state.sqlite3'
    started = time.monotonic()
    with sqlite3.connect(db.as_uri() + '?mode=ro', uri=True) as connection:
        payload, = connection.execute('SELECT payload FROM release_state WHERE id=1').fetchone()
    state = json.loads(payload)
    sizes = {key: len(json.dumps(value, ensure_ascii=False).encode('utf-8')) for key, value in state.items()}
    jobs = state['jobs']
    eligible = [j for j in jobs if j.get('action') == 'prepare-rehearsal' and j.get('remoteStatusRequired')
                and j.get('sourceEnv') in ('test', 'prod', 'backup')
                and j.get('continuationRemotePhase', j.get('remotePhase')) in ('capture-starting', 'capture-complete', 'restore-starting')
                and j.get('status') in ('running', 'failed', 'interrupted') and not j.get('resolution')]
    summary = dict(observedAt=now(), databaseBytes=db.stat().st_size, payloadBytes=len(payload.encode('utf-8')),
                   readAndSizeSeconds=round(time.monotonic()-started, 3), sectionBytes=sizes,
                   jobCount=len(jobs), jobStatusCounts=dict(collections.Counter(j.get('status') for j in jobs)),
                   activeRemotePollingJobs=[{'id': j['id'], 'status': j['status'], 'phase': j.get('continuationRemotePhase', j.get('remotePhase'))} for j in eligible],
                   catalogueRootCount=len(config.get('packageCatalogRoots', [])),
                   configurationHasBackupSourceConnections='sourceConnections' in config,
                   configurationHasSelectableBindings='bindings' in config,
                   measurements=[], businessWrites=0)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    origin = 'http://127.0.0.1:' + str(config['port'])
    for route in ('/package-catalog', '/state', '/package-catalog'):
        began = time.monotonic()
        row = {'route': route}
        try:
            request = urllib.request.Request(origin+route, headers={'X-Release-Key': config['bridgeKey']})
            with opener.open(request, timeout=25) as response:
                row['headerSeconds'] = round(time.monotonic()-began, 3)
                raw = response.read()
                row.update(httpStatus=response.status, bytes=len(raw), elapsedSeconds=round(time.monotonic()-began, 3))
            name = 'catalogue-504-upstream-' + str(len(summary['measurements'])) + '.private.json'
            (PRIVATE / name).write_bytes(raw)
            value = json.loads(raw)
            if route == '/package-catalog':
                row.update(itemCount=len(value.get('items', [])), refreshing=value.get('refreshing'), complete=value.get('complete'), errorCount=len(value.get('errors', [])))
        except Exception as exc:
            row.update(errorType=type(exc).__name__, elapsedSeconds=round(time.monotonic()-began, 3))
        summary['measurements'].append(row)
        write(TASK / 'catalogue-504-upstream-timings.json', summary)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    print(json.dumps({k:v for k,v in summary.items() if k!='measurements'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
