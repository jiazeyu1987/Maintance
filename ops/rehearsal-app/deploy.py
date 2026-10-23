"""Install one immutable release into a NEW, isolated lab directory. Run on host.

Credentials remain in mode-0600 files, never in command output or this repository.
This installer never replaces containers or deletes volumes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import time


def run(args, **kw):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)
    if result.returncode:
        # Docker stderr may contain environment values; keep it private for diagnosis.
        (ROOT / 'last-command-error.private.txt').write_bytes(result.stderr)
        os.chmod(ROOT / 'last-command-error.private.txt', 0o600)
        raise RuntimeError('INSTALL_COMMAND_FAILED: ' + args[0] + ' ' + args[1])
    return result.stdout


def docker(*args):
    return run(['docker', *args]).decode().strip()


def private(name, values):
    path = ROOT / name
    with path.open('x', encoding='utf-8') as stream:
        for key, value in values.items():
            stream.write(key + '=' + value + '\n')
    path.chmod(0o600)
    return str(path)


def healthy(name, seconds=180):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        state = json.loads(docker('inspect', '--format', '{{json .State}}', name))
        if state.get('Health', {}).get('Status') == 'healthy':
            return
        if not state['Running'] or state.get('Health', {}).get('Status') == 'unhealthy':
            raise RuntimeError('CONTAINER_UNHEALTHY: ' + name)
        time.sleep(3)
    raise RuntimeError('CONTAINER_HEALTH_TIMEOUT: ' + name)


def install(args):
    manifest = json.loads(Path(args.manifest).read_text())
    tag = manifest['releaseTag']
    for image in manifest['images']:
        actual = docker('image', 'inspect', '--format', '{{.Id}}', image['name'])
        if actual != image['id']:
            raise RuntimeError('IMAGE_ID_MISMATCH: ' + image['name'])
    with socket.socket() as sock:
        sock.bind((args.host, 38082))
    network = 'rehearsal-smallapp-20261022'
    if docker('ps', '-a', '--filter', 'name=^/' + network + '-', '--format', '{{.Names}}'):
        raise RuntimeError('LAB_CONTAINERS_ALREADY_EXIST')
    if docker('network', 'ls', '--filter', 'name=^' + network + '$', '--format', '{{.Name}}'):
        raise RuntimeError('LAB_NETWORK_ALREADY_EXISTS')
    if docker('network', 'ls', '--filter', 'name=^' + network + '-ingress$', '--format', '{{.Name}}'):
        raise RuntimeError('LAB_INGRESS_NETWORK_ALREADY_EXISTS')
    data = ROOT / 'data'
    data.mkdir(exist_ok=False)
    db_password, root_password, redis_password, minio_password, login_password, secondary_password = [secrets.token_urlsafe(24) for _ in range(6)]
    database = private('mysql.env', dict(MYSQL_DATABASE='rehearsal', MYSQL_USER='rehearsal', MYSQL_PASSWORD=db_password, MYSQL_ROOT_PASSWORD=root_password))
    minio = private('minio.env', dict(MINIO_ROOT_USER='rehearsal', MINIO_ROOT_PASSWORD=minio_password))
    backend = private('backend.env', dict(DB_PASSWORD=db_password, REDIS_PASSWORD=redis_password, MINIO_ROOT_USER='rehearsal', MINIO_ROOT_PASSWORD=minio_password, LAB_PASSWORD=login_password, LAB_SECONDARY_PASSWORD=secondary_password, LAB_SERVER=args.host, RELEASE_TAG=tag))
    credentials = ROOT / 'login.private.json'
    credentials.write_text(json.dumps(dict(username='aoteman', password=login_password, tenantId=122,
        secondary=dict(username='recovery_tenant123',password=secondary_password,tenantId=123))))
    credentials.chmod(0o600)
    redis_config = ROOT / 'redis.conf'
    redis_config.write_text('bind 0.0.0.0\nprotected-mode yes\nappendonly yes\nrequirepass ' + redis_password + '\n')
    redis_config.chmod(0o644)  # Parent directory is mode 0700; container must read the bind mount.
    private('redis.env', dict(REDISCLI_AUTH=redis_password))
    for component in ('mysql', 'redis', 'minio'):
        (data / component).mkdir()
    docker('network', 'create', '--internal', '--label', 'owner=rehearsal-smallapp-20261022', network)
    docker('network', 'create', '--label', 'owner=rehearsal-smallapp-20261022', network + '-ingress')

    def start(component, image, extra, command=()):
        name = network + '-' + component
        docker('run', '-d', '--name', name, '--network', network, '--network-alias', component,
               '--restart', 'unless-stopped', '--label', 'owner=rehearsal-smallapp-20261022',
               '--log-opt', 'max-size=5m', '--log-opt', 'max-file=2', *extra, image, *command)
        return name

    mysql_name = start('mysql', 'mysql:8.0.39', ['--memory=512m', '--cpus=1', '--env-file', database,
        '-v', str(data / 'mysql') + ':/var/lib/mysql', '--health-cmd', 'MYSQL_PWD="$MYSQL_PASSWORD" mysql -h127.0.0.1 -u"$MYSQL_USER" rehearsal -Nse "SELECT 1"',
        '--health-interval=5s', '--health-start-period=60s', '--health-retries=24'],
        ['--innodb-buffer-pool-size=64M', '--max-connections=30', '--performance-schema=OFF',
         '--server-id=' + args.host.split('.')[-1], '--log-bin=mysql-bin', '--binlog-format=ROW', '--binlog-expire-logs-seconds=604800'])
    redis_name = start('redis', 'redis:7-alpine', ['--memory=96m', '--cpus=0.25', '--env-file', str(ROOT / 'redis.env'),
        '-v', str(data / 'redis') + ':/data', '-v', str(redis_config) + ':/etc/redis/redis.conf:ro',
        '--health-cmd', 'redis-cli ping | grep -q PONG', '--health-interval=5s', '--health-retries=12'], ['redis-server', '/etc/redis/redis.conf'])
    minio_name = start('minio', 'quay.io/minio/minio:RELEASE.2025-06-13T11-33-47Z', ['--memory=384m', '--cpus=0.5', '--env-file', minio,
        '-v', str(data / 'minio') + ':/data', '--health-cmd', 'curl -fsS http://127.0.0.1:9000/minio/health/live',
        '--health-interval=5s', '--health-retries=12'], ['server', '/data', '--console-address', ':9001'])
    for name in (mysql_name, redis_name, minio_name):
        healthy(name)
    backend_name = start('backend', 'rehearsal-smallapp-backend:' + tag, ['--memory=512m', '--cpus=1', '--env-file', backend])
    healthy(backend_name)
    frontend_name = start('frontend', 'rehearsal-smallapp-frontend:' + tag, ['--memory=64m', '--cpus=0.25', '-p', args.host + ':38082:80'])
    docker('network', 'connect', network + '-ingress', frontend_name)
    healthy(frontend_name)
    receipt = dict(host=args.host, releaseTag=tag, gitCommit=manifest['gitCommit'], url='http://' + args.host + ':38082',
                   containers=[mysql_name, redis_name, minio_name, backend_name, frontend_name], status='healthy')
    (ROOT / 'deployment.json').write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--host', choices=['172.30.30.58','172.30.30.57','172.30.30.59'], required=True)
    parser.add_argument('--manifest', required=True)
    args = parser.parse_args()
    ROOT = Path(args.root)
    if ROOT.exists():
        raise SystemExit('INSTALL_ROOT_ALREADY_EXISTS')
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=False)
    install(args)
