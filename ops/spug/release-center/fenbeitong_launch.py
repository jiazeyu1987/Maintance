"""Launch a frozen per-user executor; suitable for pythonw and Windows logon."""
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.request
import urllib.error


def launch():
    root = Path(__file__).resolve().parent
    config = json.loads((root / 'executor.private.json').read_text('utf-8'))
    for relative, expected in json.loads((root / 'source-sha256.json').read_text('utf-8')).items():
        path = root / 'source' / relative
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError('Frozen executor source changed: ' + relative)
    os.environ['PATH'] = config['toolPath']
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request('http://127.0.0.1:' + str(config['port']) + '/state', headers={'X-Release-Key': config['bridgeKey']})
    try:
        with opener.open(request, timeout=3) as response:
            state = json.load(response)
    except urllib.error.URLError as error:
        # Only a refused connection means no executor. Authentication failures,
        # timeouts and other errors must not cause a competing process to start.
        if not isinstance(error.reason, ConnectionRefusedError):
            raise
    else:
        if state['application']['id'] != 'fenbeitong' or state['application']['executorSourceSha256'] != config['executorSourceSha256']:
            raise RuntimeError('A different executor is using the configured port')
        return
    sys.path.insert(0, str(root / 'source'))
    from executor import create_server
    from fenbeitong_executor import FenbeitongExecutor
    executor = FenbeitongExecutor(config)
    server = create_server(executor, config)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        executor.process_lock.close()


if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    sys.stdout = (root / 'executor.stdout.log').open('a', encoding='utf-8', buffering=1)
    sys.stderr = (root / 'executor.stderr.log').open('a', encoding='utf-8', buffering=1)
    launch()
