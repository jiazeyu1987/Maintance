"""Windows SSH transport for Spug's fixed, read-only three-server query."""
import concurrent.futures
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parent


def collect(profile):
    source = (ROOT / 'runtime_versions.py').read_bytes()
    # Import the collector without invoking its standalone all-instances command.
    payload = ('scope={"__name__":"runtime_versions"};exec(' + repr(source) + ',scope);'
               'import json;print(json.dumps(scope["query_registered"](' + repr(profile) + '),ensure_ascii=True))')
    try:
        p = subprocess.run(['C:/Windows/System32/OpenSSH/ssh.exe', '-F', 'NUL',
                            '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
                            '-o', 'ConnectTimeout=8', 'root@' + profile['host'],
                            profile['python'] + ' -'], input=payload.encode(),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    except subprocess.TimeoutExpired:
        return dict(host=profile['host'], name=profile['name'], error='REMOTE_VERSION_QUERY_TIMEOUT')
    if p.returncode:
        return dict(host=profile['host'], name=profile['name'], error='REMOTE_VERSION_QUERY_FAILED',
                    exitCode=p.returncode)
    return json.loads(p.stdout)


def snapshot(config):
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(collect, config['profiles']))
    for row in rows:
        if 'error' not in row:
            for component in row['components'].values():
                component['versionName'] = config['knownImages'].get(component['imageId'], '未登记版本名称，以镜像摘要为准')
    good = [r for r in rows if 'error' not in r]
    same = {role: len(good) == 3 and len({r['components'][role]['imageId'] for r in good}) == 1
            for role in ('frontend', 'backend', 'database')}
    return dict(servers=rows, allSucceeded=len(good) == 3, sameImages=same,
                note='只核对登记的主系统运行镜像及数据库版本；不代表业务数据或展厅等配套配置一致。')


def serve(config_path):
    config = json.loads(Path(config_path).read_text(encoding='utf-8'))
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path != '/versions':
                self.send_error(404)
                return
            if not secrets.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + config['token']):
                self.send_error(403)
                return
            try:
                value = snapshot(config)
                code = 200 if value['allSucceeded'] else 502
            except (OSError, ValueError, subprocess.TimeoutExpired):
                value, code = {'error': 'VERSION_QUERY_FAILED'}, 502
            payload = json.dumps(value, ensure_ascii=False).encode('utf-8')
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
    ThreadingHTTPServer(('127.0.0.1', 18086), Handler).serve_forever()


if __name__ == '__main__':
    serve(sys.argv[1])
