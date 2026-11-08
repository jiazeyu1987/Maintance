"""Run the image import contract in a task-owned classic Docker daemon.

The helper has no host Docker socket or business mounts. Its parent runner
records the immutable static binaries and seed tar before launching it.
"""
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import tarfile
import time


def main():
    evidence = Path('/evidence')
    binaries = Path('/tmp/classic-bin')
    binaries.mkdir(mode=0o700)
    expected = {'docker', 'dockerd', 'docker-init', 'docker-proxy', 'containerd',
                'containerd-shim-runc-v2', 'ctr', 'runc'}
    with tarfile.open('/fixtures/docker.tgz') as archive:
        files = [row for row in archive if row.isfile()]
        assert {row.name for row in files} == {'docker/'+name for name in expected}
        assert all(row.size > 0 and not row.issparse() for row in files)
        for row in files:
            path = binaries/Path(row.name).name
            with archive.extractfile(row) as source, path.open('xb') as target:
                while True:
                    value = source.read(1024*1024)
                    if not value:
                        break
                    target.write(value)
            path.chmod(0o700)
    os.environ['PATH'] = str(binaries)+':'+os.environ['PATH']

    def api(path):
        transport = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connection = http.client.HTTPConnection('localhost', timeout=3)
        try:
            transport.settimeout(3)
            transport.connect('/var/run/docker.sock')
            connection.sock = transport
            connection.request('GET', path)
            response = connection.getresponse()
            data = response.read(1024*1024)
            assert response.status == 200, (response.status, data)
            return json.loads(data)
        finally:
            connection.close()
            transport.close()

    command = [str(binaries/'dockerd'), '--host=unix:///var/run/docker.sock',
        '--data-root=/tmp/classic-data', '--exec-root=/tmp/classic-exec',
        '--pidfile=/tmp/classic-dockerd.pid', '--storage-driver=vfs',
        '--bridge=none', '--iptables=false', '--ip6tables=false',
        '--ip-forward=false', '--ip-masq=false',
        '--exec-opt=native.cgroupdriver=cgroupfs']
    daemon = None
    status = dict(schemaVersion='ClassicDockerTestIsolation/v1', status='RUNNING',
        hostDockerSocketMounted=False, networkMode='none', publishedPorts=[],
        productionServerTouched=False, command=command)
    try:
        with (evidence/'daemon.log').open('xb') as log:
            daemon = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            deadline = time.monotonic()+40
            while True:
                assert daemon.poll() is None, 'classic daemon exited during startup'
                try:
                    version = api('/version')
                    break
                except (OSError, http.client.HTTPException):
                    if time.monotonic() >= deadline:
                        raise TimeoutError('classic daemon readiness')
                    time.sleep(0.1)
            info = api('/info')
            assert version['Version'] == '27.5.1'
            assert info['Driver'] == 'vfs'
            assert info['DockerRootDir'] == '/tmp/classic-data'
            assert not any(row[0] == 'driver-type' and row[1] == 'io.containerd.snapshotter.v1'
                           for row in (info.get('DriverStatus') or []))
            status.update(version=version, storageDriver=info['Driver'],
                          dataRoot=info['DockerRootDir'])
            result = subprocess.run([str(binaries/'docker'), '--host=unix:///var/run/docker.sock',
                'load', '--input=/fixtures/seed.tar'], capture_output=True, timeout=120)
            (evidence/'seed-load.log').write_bytes(result.stdout+result.stderr)
            assert result.returncode == 0, result.stderr
            with tarfile.open('/fixtures/seed.tar') as archive:
                manifest = json.load(archive.extractfile('manifest.json'))
                assert len(manifest) == 1
                raw = archive.extractfile(manifest[0]['Config']).read()
                identity = 'sha256:'+hashlib.sha256(raw).hexdigest()
            assert api('/images/'+identity+'/json')['Id'] == identity
            os.environ.update(PROGRAM_TEST_API=version['ApiVersion'],
                PROGRAM_TEST_BASE_IMAGE=identity, PROGRAM_TEST_EVIDENCE_DIR=str(evidence))
            from program_import_native_check import main as check_import
            check_import()
            status['status'] = 'PASS'
    except BaseException as error:
        status.update(status='FAIL', failureCode=type(error).__name__, failure=str(error))
        raise
    finally:
        if daemon is not None:
            if daemon.poll() is None:
                daemon.terminate()
                try:
                    daemon.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    daemon.kill()
                    daemon.wait(timeout=10)
                    status['status'] = 'FAIL'
                    status['forcedDaemonTermination'] = True
            status['daemonStopped'] = daemon.poll() is not None
            status['daemonExitCode'] = daemon.returncode
        (evidence/'isolation-report.json').write_text(json.dumps(status, indent=2), encoding='utf-8')
    assert status['status'] == 'PASS', status


if __name__ == '__main__':
    main()
