"""Narrow standalone-assistant remote operations, compatible with Python 2.7/3.

Never reads IntRuoyi credentials, mutates its containers or imports local business data.
"""
from __future__ import print_function
import hashlib
import io
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import tarfile
import time


def require(ok, message):
    if not ok:
        raise ValueError(message)


def run(args):
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = process.communicate()
    require(process.returncode == 0, 'Command failed: ' + args[0] + ' (exit ' + str(process.returncode) + ')')
    return out.decode('utf-8')


def sha(path):
    result = hashlib.sha256()
    with open(path, 'rb') as stream:
        while True:
            data = stream.read(1024 * 1024)
            if not data:
                break
            result.update(data)
    return result.hexdigest()


def mkdir(path):
    if not os.path.isdir(path):
        os.makedirs(path)


def write_json(path, value):
    temporary = path + '.new'
    with open(temporary, 'wb') as stream:
        stream.write(json.dumps(value, ensure_ascii=True).encode('utf-8'))
        stream.flush()
        os.fsync(stream.fileno())
    os.rename(temporary, path)


def read_json(path):
    with io.open(path, encoding='utf-8') as stream:
        return json.load(stream)


def info(name):
    names = run(['docker', 'ps', '-a', '--format', '{{.Names}}']).splitlines()
    if name not in names:
        return None
    value = json.loads(run(['docker', 'inspect', name]))[0]
    require(value['Config'].get('Labels', {}).get('release.application') == 'fenbeitong',
            'Container name is owned by another application')
    return value


def identity(value):
    if value is None:
        return dict(status='not-installed', releaseTag=None, imageId=None)
    labels = value['Config']['Labels']
    return dict(status='running' if value['State']['Running'] else 'stopped',
                releaseTag=labels['release.version'], imageId=value['Image'],
                containerId=value['Id'], packageSha256=labels['release.package'])


def health(name, manifest):
    code = ('const fs=require("fs");const x=JSON.parse(fs.readFileSync("/app/release-info.json","utf8"));'
            'if(x.releaseTag!==' + json.dumps(manifest['releaseTag']) + ')process.exit(2);'
            'fetch("http://127.0.0.1:18734/api/health").then(async r=>{const b=await r.json();'
            'if(!r.ok||b.success!==true||b.status!=="ok")process.exit(3);console.log(JSON.stringify(x))'
            '}).catch(()=>process.exit(4));')
    for unused in range(30):
        process = subprocess.Popen(['docker', 'exec', name, 'node', '-e', code], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = process.communicate()
        if process.returncode == 0:
            require(json.loads(out.decode('utf-8'))['sourceSha256'] == manifest['sourceSha256'], 'Source identity differs')
            require(info(name)['Image'] == manifest['imageId'], 'Actual image differs')
            return
        current = info(name)
        require(current is not None and current['State']['Running'], 'Assistant container stopped before health check')
        time.sleep(1)
    raise ValueError('Assistant health/version check timed out')


def available_network_address(network):
    """Respect static addresses on stopped containers, which Docker IPAM releases."""
    info = json.loads(run(['docker', 'network', 'inspect', network]))[0]
    ranges = [item for item in info['IPAM']['Config'] if ':' not in item['Subnet']]
    require(len(ranges) == 1, 'One explicit IPv4 integration subnet required')
    subnet = ranges[0]
    address, prefix = subnet['Subnet'].split('/')
    numeric = lambda ip: struct.unpack('!I', socket.inet_aton(ip))[0]
    mask = (0xffffffff << (32 - int(prefix))) & 0xffffffff
    first = numeric(address) & mask
    last = first | (0xffffffff ^ mask)
    used = set([first, last])
    bridge = info.get('Options', {}).get('com.docker.network.bridge.name') or 'br-' + info['Id'][:12]
    addresses = run(['ip', '-o', '-4', 'addr', 'show', 'dev', bridge])
    for ip in re.findall(r'\binet\s+([0-9.]+)/', addresses):
        used.add(numeric(ip))
    if subnet.get('Gateway'):
        used.add(numeric(subnet['Gateway']))
    for ip in subnet.get('AuxiliaryAddresses', {}).values():
        used.add(numeric(ip))
    for endpoint in info.get('Containers', {}).values():
        if endpoint.get('IPv4Address'):
            used.add(numeric(endpoint['IPv4Address'].split('/')[0]))
    ids = run(['docker', 'ps', '-aq']).split()
    if ids:
        for container in json.loads(run(['docker', 'inspect'] + ids)):
            endpoint = container['NetworkSettings']['Networks'].get(network, {})
            reserved = (endpoint.get('IPAMConfig') or {}).get('IPv4Address')
            if reserved:
                used.add(numeric(reserved))
    candidate = first + 1
    while candidate < last and candidate in used:
        candidate += 1
    require(candidate < last, 'No unreserved IPv4 address in integration network')
    return socket.inet_ntoa(struct.pack('!I', candidate))


def start(config, name, manifest, data, isolated=False):
    integration_ip = None if isolated else available_network_address(config['integrationNetwork'])
    args = ['docker', 'run', '-d', '--name', name, '--label', 'release.application=fenbeitong',
            '--label', 'release.version=' + manifest['releaseTag'], '--label', 'release.package=' + config['packageSha256'],
            '--mount', 'type=bind,source=' + data + ',target=/data',
            '-e', 'APP_DATA_DIR=/data', '-e', 'FENBEITONG_MODE=real', '-e', 'KINGDEE_MODE=real',
            '-e', 'SCHEDULER_ENABLED=false', '-e', 'PAYMENT_STATUS_SYNC_ENABLED=false',
            '-e', 'FENBEITONG_ASSISTANT_HOST=0.0.0.0',
            '-e', 'FENBEITONG_ASSISTANT_TICKET_VALIDATE_URL=' + config['ticketValidateUrl']]
    if isolated:
        args.extend(['--network', 'none'])
    else:
        args.extend(['--restart', 'unless-stopped', '-p', str(config['port']) + ':18734'])
    args.append(manifest['imageId'])
    run(args)
    if not isolated:
        run(['docker','network','connect','--ip',integration_ip,'--alias','fenbeitong-assistant',config['integrationNetwork'],name])


def manifest(config):
    folder = os.path.join(config['root'], 'uploads', config['jobId'])
    archive_path = os.path.join(folder, 'release.tar')
    require(sha(archive_path) == config['packageSha256'], 'Transferred archive checksum mismatch')
    with tarfile.open(archive_path, 'r:') as archive:
        members = archive.getmembers()
        require(sorted(m.name for m in members) == ['image.tar', 'manifest.json'] and all(m.isfile() for m in members),
                'Unexpected release archive members')
        archive.extractall(folder)
    require(sha(os.path.join(folder, 'manifest.json')) == config['manifestSha256'], 'Manifest checksum mismatch')
    value = read_json(os.path.join(folder, 'manifest.json'))
    require(value['applicationId'] == 'fenbeitong' and value['releaseTag'] == config['releaseTag'], 'Package identity mismatch')
    require(sha(os.path.join(folder, 'image.tar')) == value['files'][0]['sha256'], 'Image archive checksum mismatch')
    run(['docker', 'load', '-i', os.path.join(folder, 'image.tar')])
    actual = json.loads(run(['docker', 'image', 'inspect', value['image']]))[0]
    require(actual['Id'] == value['imageId'], 'Loaded image identity mismatch')
    return value


def precheck(config):
    current = info(config['container'])
    backend = json.loads(run(['docker','inspect',config['intRuoyiBackend']]))[0]
    require(config['integrationNetwork'] in backend['NetworkSettings']['Networks'], 'Registered IntRuoyi network differs')
    run(['docker','network','inspect',config['integrationNetwork']])
    disk = json.loads(run(['docker', 'info', '--format', '{{json .DockerRootDir}}']))
    space = os.statvfs(disk)
    require(space.f_bavail * space.f_frsize >= config['requiredBytes'], 'Insufficient Docker disk space')
    listeners = run(['ss', '-lnt']).splitlines()
    if current is None:
        require(not any(re.search(r':' + str(config['port']) + r'\s', line) for line in listeners), 'Assistant port already occupied')
    # Do not probe an authenticated business endpoint or fabricate a login result.
    return dict(environment=identity(current), freeBytes=space.f_bavail * space.f_frsize, status='passed')


def execute(config):
    root = config['root']
    require(root in ('/var/lib/docker/fenbeitong-release', '/mnt/intruoyi-data/fenbeitong-release'), 'Unregistered application root')
    require(config['container'] == 'fenbeitong-assistant', 'Unregistered container identity')
    require(config['port'] == 18734, 'Unexpected assistant port')
    require(re.match(r'^JOB-[a-f0-9]{10}$', config['jobId']) is not None, 'Invalid job identity')
    require(not os.path.islink(root), 'Application root must not be a link')
    action = config['action']
    if action == 'observe':
        return dict(environment=identity(info(config['container'])))
    if action == 'precheck':
        return precheck(config)
    if action == 'receipt':
        path = os.path.join(root, 'jobs', config['originalJobId'] + '.json')
        require(re.match(r'^JOB-[a-f0-9]{10}$', config['originalJobId']) is not None, 'Invalid original job')
        require(os.path.isfile(path), 'Original remote receipt missing; do not repeat effects')
        return read_json(path)
    mkdir(root)
    for name in ('jobs', 'data', 'recovery', 'rehearsals'):
        mkdir(os.path.join(root, name))
    import fcntl
    lock = open(os.path.join(root, 'release.lock'), 'a+')
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    receipt_path = os.path.join(root, 'jobs', config['jobId'] + '.json')
    require(not os.path.exists(receipt_path), 'Remote job already exists; inspect its receipt')
    receipt = dict(jobId=config['jobId'], status='running', effectsStarted=False,
                   action=action, packageSha256=config.get('packageSha256'))
    write_json(receipt_path, receipt)
    source_stopped = False
    try:
        precheck(config)
        current = info(config['container'])
        before = identity(current)
        if action == 'verify':
            require(before['status'] == 'running' and before['packageSha256'] == config['packageSha256'], 'Acceptance target differs')
            value = dict(releaseTag=config['releaseTag'], sourceSha256=config['sourceSha256'], imageId=config['imageId'])
            health(config['container'], value)
        else:
            require(action in ('deploy', 'rehearse'), 'Unknown remote operation')
            if action == 'deploy':
                require(not before['releaseTag'] or before['releaseTag'] < config['releaseTag'], 'Target has the same or a newer version')
                if config.get('expectedOrigin') is not None:
                    require(before == config['expectedOrigin'], 'Production origin changed since rehearsal')
            value = manifest(config)
            receipt.update(effectsStarted=True, origin=before, phase='capture-data')
            write_json(receipt_path, receipt)
            if current:
                require(current['State']['Running'], 'Current assistant must be running before capture')
                run(['docker', 'stop', config['container']])
                source_stopped = True
            recovery = os.path.join(root, 'recovery', config['jobId'] + '.tar.gz')
            run(['tar', '-czf', recovery, '-C', os.path.join(root, 'data'), '.'])
            receipt['recovery'] = recovery
            write_json(receipt_path, receipt)
            if action == 'rehearse':
                if source_stopped:
                    run(['docker', 'start', config['container']])
                    source_stopped = False
                copy = os.path.join(root, 'rehearsals', config['jobId'])
                mkdir(copy)
                run(['tar', '-xzf', recovery, '-C', copy])
                name = config['container'] + '-rehearsal-' + config['jobId']
                start(config, name, value, copy, True)
                try:
                    health(name, value)
                finally:
                    run(['docker', 'stop', name])
                receipt['origin'] = before
                receipt['isolatedContainer'] = name
            else:
                if current:
                    old = config['container'] + '-before-' + config['jobId']
                    run(['docker', 'rename', config['container'], old])
                    source_stopped = False
                    receipt['previousContainer'] = old
                receipt['phase'] = 'start-candidate'
                write_json(receipt_path, receipt)
                start(config, config['container'], value, os.path.join(root, 'data'))
                health(config['container'], value)
        receipt.update(status='succeeded', phase='complete', environment=identity(info(config['container'])))
        write_json(receipt_path, receipt)
        return receipt
    except Exception as error:
        receipt.update(status='failed', error=str(error))
        write_json(receipt_path, receipt)
        raise
    finally:
        if source_stopped and action == 'rehearse':
            run(['docker', 'start', config['container']])
        lock.close()


if __name__ == '__main__':
    try:
        print(json.dumps(execute(json.load(sys.stdin)), ensure_ascii=True))
    except Exception as error:
        print(json.dumps(dict(error=str(error)), ensure_ascii=True))
        sys.exit(1)
