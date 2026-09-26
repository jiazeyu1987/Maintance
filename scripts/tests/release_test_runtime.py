"""Explicit, ownership-checked runtimes for local release integration tests."""
from __future__ import annotations

import json
import hashlib
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MySqlRuntime:
    task: str
    container_id: str
    container_name: str
    volume: str


OFFICIAL_DIND = 'docker.io/library/docker@sha256:dd43b430341a40d88f4f30edb03865daa9d6fa39c9b1da70f27e2a89cec3eae1'
OFFICIAL_SMOKE_CONFIG = 'sha256:ab853f51b03036cd52e74771c2dd07ee1471c408645048e928af67db6beae6d7'
OFFICIAL_BUSYBOX_SHA256 = '42de297577993675efecf295acf0260e26128458048b3081451e1ac43f611b49'
OFFICIAL_MUSL_SHA256 = '60d0ed88672b260b8337bf1e5b721f9ca9c877f4d901886472b8195a38ff3630'


@dataclass(frozen=True)
class RuntimeSettings:
    task: str
    task_cache: Path
    prefix: str


@dataclass(frozen=True)
class ClassicRuntime:
    task: str
    container_id: str
    container_name: str
    volume: str


def _configuration() -> dict:
    value = os.environ.get('RELEASE_TEST_MYSQL_RUNTIME_CONFIG')
    if not value:
        raise RuntimeError('RELEASE_TEST_MYSQL_RUNTIME_CONFIG is required')
    path = Path(value)
    if not path.is_absolute() or not path.is_file():
        raise RuntimeError('release test MySQL configuration must be an existing absolute file')
    def unique(pairs):
        result = {}
        for key, item in pairs:
            if key in result:
                raise RuntimeError('release test configuration contains duplicate fields')
            result[key] = item
        return result
    try:
        config = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique)
    except (ValueError, UnicodeError):
        raise RuntimeError('release test configuration must be valid UTF-8 JSON') from None
    if not isinstance(config, dict):
        raise RuntimeError('release test configuration must be a JSON object')
    return config


def _text(config: dict, field: str) -> str:
    value = config.get(field)
    if not isinstance(value, str) or not value or value != value.strip() or any(ord(c)<32 for c in value):
        raise RuntimeError(f'release test configuration requires {field}')
    if field=='task' and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}',value):
        raise RuntimeError('release test task must be a safe task identifier')
    return value


def runtime_settings() -> RuntimeSettings:
    config = _configuration()
    task = _text(config, 'task')
    cache = Path(_text(config, 'taskCache'))
    prefix = _text(config, 'prefix')
    if not cache.is_absolute() or not cache.is_dir() or cache.is_symlink():
        raise RuntimeError('release test taskCache must be an existing absolute directory')
    if not re.fullmatch(r'release-[a-z0-9][a-z0-9-]*-', prefix):
        raise RuntimeError('release test prefix must be a safe task-specific release prefix')
    return RuntimeSettings(task, cache, prefix)


def classic_configuration() -> ClassicRuntime:
    config = _configuration()
    task = _text(config, 'task')
    classic = config.get('classic')
    if not isinstance(classic, dict):
        raise RuntimeError('release test configuration requires classic')
    name = _text(classic, 'container')
    identifier = _text(classic, 'containerId')
    volume = _text(classic, 'volume')
    if not re.fullmatch(r'[0-9a-f]{64}', identifier):
        raise RuntimeError('release test classic containerId must be a complete immutable ID')
    if not all(re.fullmatch(r'release-[a-z0-9][a-z0-9-]*', item) for item in [name,volume]):
        raise RuntimeError('release test classic name and volume must be task-specific')
    return ClassicRuntime(task, identifier, name, volume)


def _docker_text(*args: str) -> str:
    result = subprocess.run(['docker',*args],capture_output=True,text=True,encoding='utf-8',errors='strict',timeout=40)
    if result.returncode:
        raise RuntimeError('release test runtime Docker command failed')
    return result.stdout.strip()


def classic_runtime() -> ClassicRuntime:
    runtime = classic_configuration()
    state = _docker_json('inspect','--type','container',runtime.container_name)[0]
    if state['Id'] != runtime.container_id or state['Name'].lstrip('/') != runtime.container_name:
        raise RuntimeError('release test classic instance identity mismatch')
    if (state['Config'].get('Labels') or {}).get('codex.task') != runtime.task:
        raise RuntimeError('release test classic container ownership mismatch')
    if not state['State'].get('Running'):
        raise RuntimeError('release test classic container is not running')
    if state['HostConfig'].get('NetworkMode') != 'none' or state['HostConfig'].get('PortBindings'):
        raise RuntimeError('release test classic must have no network or published ports')
    mounts = state.get('Mounts',[])
    if len(mounts)!=1 or not all(m.get('Type')=='volume' and m.get('Name')==runtime.volume
        and m.get('Destination')=='/var/lib/docker' and m.get('RW') is True for m in mounts):
        raise RuntimeError('release test classic data mount identity mismatch')
    if any('docker.sock' in str(m.get('Source','')) or 'docker.sock' in str(m.get('Destination','')) for m in mounts):
        raise RuntimeError('release test classic must not mount a host Docker socket')
    volume = _docker_json('volume','inspect',runtime.volume)[0]
    if volume.get('Name')!=runtime.volume:
        raise RuntimeError('release test classic volume identity mismatch')
    consumers=_docker_text('ps','-a','--no-trunc','--filter',f'volume={runtime.volume}','--format','{{.ID}}').split()
    if consumers!=[runtime.container_id]:
        raise RuntimeError('release test classic volume must be exclusively owned')
    official=_docker_json('image','inspect',OFFICIAL_DIND)[0]
    if state['Config'].get('Image')!=OFFICIAL_DIND or state['Image']!=official['Id']:
        raise RuntimeError('release test classic official dind identity mismatch')
    facts=_docker_text('exec',runtime.container_id,'docker','info','--format','{{.Driver}}|{{.ServerVersion}}|{{.OSType}}')
    if facts!='overlay2|26.1.4|linux':
        raise RuntimeError('release test classic requires Linux Docker 26.1.4 overlay2')
    loaded=json.loads(_docker_text('exec',runtime.container_id,'docker','image','inspect',OFFICIAL_SMOKE_CONFIG))[0]
    if loaded.get('Id')!=OFFICIAL_SMOKE_CONFIG or loaded.get('Os')!='linux' or loaded.get('Architecture')!='amd64':
        raise RuntimeError('release test official loaded smoke content identity mismatch')
    return runtime


def official_archive() -> Path:
    config=_configuration().get('officialArchive')
    if not isinstance(config,dict):
        raise RuntimeError('release test configuration requires officialArchive')
    archive=Path(_text(config,'path'))
    if not archive.is_absolute() or not archive.is_file() or archive.is_symlink():
        raise RuntimeError('release test archive path must be an existing absolute file')
    if _text(config,'configDigest')!=OFFICIAL_SMOKE_CONFIG:
        raise RuntimeError('release test official content identity mismatch')
    if type(config.get('bytes')) is not int or config['bytes']<=0 or archive.stat().st_size!=config['bytes']:
        raise RuntimeError('release test archive bytes mismatch')
    digest=_text(config,'sha256')
    if not re.fullmatch('[0-9a-f]{64}',digest):
        raise RuntimeError('release test archive sha256 must be a complete digest')
    with archive.open('rb') as stream:
        actual=hashlib.file_digest(stream,'sha256').hexdigest()
    if actual!=digest:
        raise RuntimeError('release test archive sha256 mismatch')
    # Descriptor/config/layer verification remains in the real production C5
    # governance invocation; byte validation never substitutes for it.
    return archive


def mysql_flock_directory(runtime: MySqlRuntime | None = None) -> str:
    config=_configuration()
    directory=_text(config,'mysqlFlockDirectory')
    if not re.fullmatch(r'/[A-Za-z0-9_./-]+',directory) or '..' in directory.split('/') or directory.endswith('/'):
        raise RuntimeError('release test flock directory must be a safe absolute container path')
    if not directory.rsplit('/',1)[-1].startswith(_text(config,'prefix')):
        raise RuntimeError('release test flock directory must belong to the explicit task prefix')
    if runtime is None:
        runtime=mysql_runtime()
    if runtime.task!=_text(config,'task'):
        raise RuntimeError('release test flock runtime ownership mismatch')
    # The two binaries are immutable official content. The wrapper is the
    # reviewed two-line task carrier whose absolute path is explicitly supplied.
    expected_wrapper=f'#!/bin/sh\nexec {directory}/ld-musl-x86_64.so.1 {directory}/busybox flock "$@"\n'.encode()
    expected=[OFFICIAL_BUSYBOX_SHA256,OFFICIAL_MUSL_SHA256,hashlib.sha256(expected_wrapper).hexdigest()]
    names=['busybox','ld-musl-x86_64.so.1','flock']
    command=f'set -eu\ntest "$(readlink -f {shlex.quote(directory)})" = {shlex.quote(directory)}\n'+''.join(f'test ! -L {shlex.quote(directory+"/"+n)}\ntest -x {shlex.quote(directory+"/"+n)}\nsha256sum {shlex.quote(directory+"/"+n)}\n' for n in names)
    result=subprocess.run(['docker','exec','-i',runtime.container_id,'sh','-s'],input=command.encode(),capture_output=True,timeout=30)
    if result.returncode or [line.split()[0] for line in result.stdout.decode().splitlines()]!=expected:
        raise RuntimeError('release test flock tools missing, not executable or identity mismatch')
    return directory


def _docker_json(*args: str) -> list[dict]:
    result = subprocess.run(
        ["docker", *args], capture_output=True, text=True, encoding="utf-8",
        errors="strict", check=False, timeout=30,
    )
    if result.returncode:
        raise RuntimeError("release test runtime Docker inspection failed")
    return json.loads(result.stdout)


def mysql_runtime() -> MySqlRuntime:
    config = _configuration()
    for field in ("task", "container", "volume", "password"):
        if not isinstance(config.get(field), str) or not config[field]:
            raise RuntimeError(f"release test MySQL configuration requires {field}")
    if not config["container"].startswith("release-") or not config["volume"].startswith("release-"):
        raise RuntimeError("release test runtime must use task-specific release container and volume")
    container = _docker_json("inspect", "--type", "container", config["container"])[0]
    volume = _docker_json("volume", "inspect", config["volume"])[0]
    if (container["Config"].get("Labels") or {}).get("codex.task") != config["task"]:
        raise RuntimeError("release test container ownership mismatch")
    if volume.get("Name") != config["volume"]:
        raise RuntimeError("release test volume identity mismatch")
    consumers = subprocess.run(
        ["docker", "ps", "-a", "--no-trunc", "--filter", f"volume={config['volume']}",
         "--format", "{{.ID}}"],
        capture_output=True, text=True, encoding="utf-8", errors="strict", check=False, timeout=30,
    )
    if consumers.returncode or consumers.stdout.split() != [container["Id"]]:
        raise RuntimeError("release test volume must be used exclusively by its task container")
    if not container["State"].get("Running"):
        raise RuntimeError("release test MySQL container is not running")
    if container["HostConfig"].get("NetworkMode") != "none" or container["HostConfig"].get("PortBindings"):
        raise RuntimeError("release test MySQL container must have no network or published ports")
    mounts = container.get("Mounts", [])
    if len(mounts) != 1 or not any(
        mount.get("Type") == "volume" and mount.get("Name") == config["volume"]
        and mount.get("Destination") == "/var/lib/mysql" for mount in mounts
    ):
        raise RuntimeError("release test MySQL data mount identity mismatch")
    environment = dict(item.split("=", 1) for item in container["Config"].get("Env", []) if "=" in item)
    if environment.get("MYSQL_ROOT_PASSWORD") != config["password"]:
        raise RuntimeError("release test MySQL credential configuration mismatch")
    return MySqlRuntime(config["task"], container["Id"], config["container"], config["volume"])


def run_mysql(script: str, database: str | None = None) -> subprocess.CompletedProcess[str]:
    runtime = mysql_runtime()
    if database and not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]{0,63}", database):
        raise ValueError("unsafe release test schema name")
    command = (
        'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" exec mysql -uroot '
        '--default-character-set=utf8mb4 --batch --skip-column-names'
        + (f" {shlex.quote(database)}" if database else "")
    )
    result = subprocess.run(
        ["docker", "exec", "-i", runtime.container_id, "sh", "-lc", command],
        input=script.encode("utf-8"), capture_output=True, check=False, timeout=30,
    )
    return subprocess.CompletedProcess(
        result.args, result.returncode, result.stdout.decode("utf-8"), result.stderr.decode("utf-8")
    )


def application_backend_root() -> Path:
    value = os.environ.get("RELEASE_TEST_APPLICATION_BACKEND_ROOT")
    if not value:
        raise RuntimeError("RELEASE_TEST_APPLICATION_BACKEND_ROOT is required")
    path = Path(value)
    if not path.is_absolute() or not (path / "sql/mysql").is_dir():
        raise RuntimeError("application backend must be an existing absolute source root with sql/mysql")
    return path


def preflight_summary() -> dict:
    settings=runtime_settings()
    mysql=mysql_runtime()
    classic=classic_runtime()
    directory=mysql_flock_directory(mysql)
    archive=official_archive()
    application_backend_root()
    smoke=settings.task_cache/'smoke-payload'
    if not smoke.is_dir():
        raise RuntimeError('release test real smoke-payload directory is required')
    schemas=run_mysql('SHOW DATABASES;')
    if schemas.returncode:
        raise RuntimeError('release test MySQL schema inventory failed')
    # Read only task fixture names at the two established fixture locations.
    def fixture_roots(container):
        script='set -eu\n'+''.join(f"if [ -d '{root}' ]; then find '{root}' -mindepth 1 -maxdepth 1 -name '{settings.prefix}t[567]-*' -print; fi\n" for root in ['/tmp','/var/lib/docker/task-inputs'])
        return _docker_text('exec',container,'sh','-c',script).splitlines()
    return dict(task=settings.task,taskCache=str(settings.task_cache),prefix=settings.prefix,smokePayload=str(smoke),
        mysql=dict(containerId=mysql.container_id,container=mysql.container_name,volume=mysql.volume),
        classic=dict(containerId=classic.container_id,container=classic.container_name,volume=classic.volume),
        mysqlFlockDirectory=directory,officialArchive=dict(path=str(archive),bytes=archive.stat().st_size,
        sha256=_configuration()['officialArchive']['sha256'],configDigest=OFFICIAL_SMOKE_CONFIG),
        classicContainers=_docker_text('exec',classic.container_id,'docker','ps','-a','--no-trunc','--format','{{.ID}} {{.Names}}').splitlines(),
        classicImages=_docker_text('exec',classic.container_id,'docker','images','--no-trunc','--format','{{.ID}} {{.Repository}}:{{.Tag}}').splitlines(),
        mysqlSchemas=schemas.stdout.splitlines(),classicFixtureRoots=fixture_roots(classic.container_id),
        mysqlFixtureRoots=fixture_roots(mysql.container_id))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--preflight',action='store_true')
    group.add_argument('--check',choices=['classic','archive','settings'])
    args=parser.parse_args()
    try:
        if args.preflight:
            print(json.dumps(preflight_summary()))
        else:
            {'classic':classic_runtime,'archive':official_archive,'settings':runtime_settings}[args.check]()
            print('configuration PASS')
    except (RuntimeError,OSError,ValueError):
        # Keep messages controlled; neither configuration repr nor subprocess
        # command/EncodedCommand is ever emitted by this private-config entry.
        error=sys.exc_info()[1]
        print(str(error) if isinstance(error,RuntimeError) else 'release test runtime prerequisite unavailable',file=sys.stderr)
        sys.exit(1)
