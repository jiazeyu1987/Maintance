"""C: scoped Spug restore. Does not migrate SSH identities or start host executors."""
import argparse
import ast
import importlib.util
import json
import socket
import subprocess
import sys
import tarfile
from pathlib import Path

PROJECT = 'intruoyi-spug-transfer'


def validate_destination(root, names, volumes, occupied):
    if root.exists() or occupied or any(n.startswith(('intruoyi-spug-', PROJECT)) for n in names) or any(v.startswith(PROJECT + '_') for v in volumes):
        raise RuntimeError('Destination, Spug resources or port conflict; refuse overwrite')


def make_config(root, package, plan, env):
    return {'name': PROJECT, 'services': {
        'db': {'image': plan['dbImage'], 'restart': 'unless-stopped', 'mem_limit': '512m', 'cpus': 1,
               'command': ['--character-set-server=utf8mb4', '--collation-server=utf8mb4_unicode_ci'],
               'environment': {'MYSQL_DATABASE': 'spug', 'MYSQL_USER': 'spug',
                               'MYSQL_PASSWORD': env['SPUG_DB_PASSWORD'], 'MYSQL_ROOT_PASSWORD': env['SPUG_DB_ROOT_PASSWORD']},
               'volumes': ['database:/var/lib/mysql']},
        'spug': {'image': plan['spugImage'], 'restart': 'unless-stopped', 'mem_limit': '1536m', 'cpus': 2, 'pids_limit': 256,
                 'entrypoint': ['/bin/sh', '/transfer/transfer-bootstrap.sh'],
                 'extra_hosts': ['host.docker.internal:host-gateway'], 'ports': ['127.0.0.1:18080:80'],
                 'environment': {'SPUG_DOCKER_VERSION': 'v4.0.1', 'MYSQL_DATABASE': 'spug', 'MYSQL_USER': 'spug',
                                 'MYSQL_PASSWORD': env['SPUG_DB_PASSWORD'], 'MYSQL_HOST': 'db', 'MYSQL_PORT': '3306'},
                 'volumes': ['service:/data/spug', 'repositories:/data/repos', 'integration_records:/var/lib/intruoyi-spug', 'data:/data',
                             (root / 'ops/spug').as_posix() + ':/opt/intruoyi-spug:ro',
                             (root / 'private').as_posix() + ':/run/intruoyi-spug:ro', package.as_posix() + ':/transfer:ro']}
    }, 'volumes': {v: {} for v in ['database', 'service', 'repositories', 'integration_records', 'data']}}


def install(package, root):
    spec = importlib.util.spec_from_file_location('upstream_transfer', package / 'transfer.py')
    upstream = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(upstream)
    run = upstream.cmd
    run(['docker', 'version', '--format', '{{.Server.Version}}'])
    names = run(['docker', 'ps', '-a', '--format', '{{.Names}}']).decode().splitlines()
    volumes = run(['docker', 'volume', 'ls', '--format', '{{.Name}}']).decode().splitlines()
    probe = socket.socket()
    try:
        probe.bind(('0.0.0.0', 18080))
        occupied = False
    except OSError:
        occupied = True
    finally:
        probe.close()
    validate_destination(root, names, volumes, occupied)
    upstream.verify()
    root.mkdir(parents=True)
    plan = upstream.read(package / 'installation-plan.json')
    for archive, target in [('source-ops.tgz', root / 'ops'), ('spug-private.tgz', root / 'private')]:
        with tarfile.open(package / 'filesystems' / archive) as tf:
            tf.extractall(target, filter='data')
    env = {}
    for line in (root / 'private/compose.private.env').read_text('utf-8-sig').splitlines():
        if line and not line.lstrip().startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            env[k] = v.strip().strip('"').strip("'")
    # Use the upstream literal bootstrap, including scheduler disable and Redis queue fencing.
    tree = ast.parse((package / 'transfer.py').read_text('utf-8-sig'))
    boot = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == 'write_text' and isinstance(n.func.value, ast.Name) and n.func.value.id == 'boot']
    if len(boot) != 1:
        raise RuntimeError('Upstream bootstrap contract changed')
    bootstrap = ast.literal_eval(boot[0].args[0])
    if 'autostart = false' not in bootstrap or 'dump.rdb.transfer-original' not in bootstrap:
        raise RuntimeError('Missing scheduler or queue fencing')
    (package / 'transfer-bootstrap.sh').write_text(bootstrap, encoding='utf-8', newline='\n')
    config = make_config(root, package, plan, env)
    (package / 'compose.transfer.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
    print('Loading verified offline images', flush=True)
    run(['docker', 'load', '-i', package / 'images.tar'])
    for image in plan['images']:
        actual = json.loads(run(['docker', 'image', 'inspect', image['reference']]))[0]['Id']
        if actual != image['id']:
            raise RuntimeError('Loaded image identity mismatch')
    for name in ['service', 'repositories', 'integration_records', 'data']:
        volume = PROJECT + '_' + name
        run(['docker', 'volume', 'create', volume])
        run(['docker', 'run', '--rm', '--network', 'none', '--entrypoint', 'tar', '-v', volume + ':/restore',
             '-v', package.as_posix() + ':/transfer:ro', plan['spugImage'], '-xzf', '/transfer/volumes/' + name + '.tgz', '-C', '/restore'])
    upstream.compose('up', '-d', '--pull', 'never', 'db')
    db = upstream.compose('ps', '-q', 'db').decode().strip()
    upstream.wait_db(db)
    with (package / 'spug.sql').open('rb') as sql:
        result = subprocess.run(['docker', 'exec', '-i', db, 'sh', '-c', 'exec mariadb -u root -p"$MYSQL_ROOT_PASSWORD"'],
                                stdin=sql, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise RuntimeError('SQL import failed; raw output withheld')
    (package / 'installed.json').write_text(json.dumps({'scope': 'spug-only', 'runtimeRoot': str(root),
        'scheduler': 'disabled', 'executors': 'not started', 'sshIdentity': 'not migrated'}), encoding='utf-8')
    upstream.start()
    upstream.check()
    subprocess.run([sys.executable, str(Path(__file__).with_name('verify_runtime.py'))], check=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--runtime', type=Path, required=True)
    args = parser.parse_args()
    install(args.package.resolve(), args.runtime.resolve())
