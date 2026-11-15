"""Fixed backup-host preparation. Installed private configuration owns all paths.

No command, path or container identifier is accepted from the browser. The caller
publishes the returned registration into Spug and verifies selections before READY.
"""
from contextlib import contextmanager, ExitStack
from copy import deepcopy
import datetime
import hashlib
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import time

HOST = '172.30.30.59'
ROLES = ('mysql', 'minio', 'redis', 'backend', 'frontend')
STAGES = ('dependencies', 'cleanup', 'initialize')


class PreparationError(RuntimeError):
    def __init__(self, code, failure=None):
        super().__init__(code)
        self.failure = failure


def require(value, code):
    if not value:
        raise PreparationError(code)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def pin(path):
    path = Path(path)
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return dict(path=path.as_posix(), bytes=path.stat().st_size, sha256=h.hexdigest())


def write(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.new')
    with temporary.open('xb') as stream:
        os.chmod(temporary, 0o600)
        stream.write(canonical(value)); stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)
    return pin(path)


def inside(path, root):
    path, root = Path(path), Path(root)
    return path == root or root in path.parents


def overlaps(left, right):
    return inside(left, right) or inside(right, left)


def plain_path(path):
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts and path.resolve() == path,
            'PREPARE_PATH_ALIAS_REFUSED')
    return path


def mount_entries():
    def decode(value):
        return re.sub(r'\\([0-7]{3})', lambda m: chr(int(m[1], 8)), value)
    result=[]
    for line in Path('/proc/self/mountinfo').read_text(encoding='utf-8').splitlines():
        fields=line.split();separator=fields.index('-')
        result.append(dict(device=fields[2],root=decode(fields[3]),target=decode(fields[4]),
                           filesystem=fields[separator+1],source=decode(fields[separator+2])))
    return result


def mount_paths():
    return [entry['target'] for entry in mount_entries()]


def volume_bind_unmounts(config, selected, volume_points, mounts):
    """Only declared local binds belonging to this deletion set may be unmounted."""
    expected={str(Path(config['dockerRoot'])/'volumes'/name/'_data'):name for name in selected['volumeNames']}
    protected=[config['toolRoot'],config['stateRoot'],config['dockerRoot'],*config['archiveRoots']]
    result=[]
    for binding in config['cleanup'].get('bindMounts',[]):
        target,source=plain_path(binding['target']),plain_path(binding['source'])
        name=expected.get(str(target))
        require(name is not None,'PREPARE_VOLUME_BIND_NOT_SELECTED')
        require(source!=Path(config['dataRoot']) and inside(source,config['dataRoot']) and
                not any(overlaps(source,path) for path in protected),'PREPARE_VOLUME_BIND_SOURCE_REFUSED')
        actual=[item for item in mounts if Path(item['target'])==target]
        if not actual:continue
        require(len(actual)==1 and volume_points.get(name)==str(target),'PREPARE_VOLUME_BIND_CHANGED')
        ancestors=[item for item in mounts if inside(source,item['target'])]
        require(ancestors,'PREPARE_VOLUME_BIND_SOURCE_REFUSED')
        origin=max(ancestors,key=lambda item:len(Path(item['target']).parts))
        expected_root=PurePosixPath(origin['root']).joinpath(*source.relative_to(origin['target']).parts).as_posix()
        require(origin['filesystem'] in ('ext4','xfs','btrfs') and origin['source'].startswith('/dev/') and
                actual[0]['device']==origin['device'] and actual[0]['root']==expected_root and
                actual[0]['filesystem']==origin['filesystem'],'PREPARE_VOLUME_BIND_CHANGED')
        require(not any(Path(item['target'])!=target and inside(item['target'],target) for item in mounts),
                'PREPARE_VOLUME_BIND_NESTED_MOUNT')
        result.append((str(target),name))
    return result


def validate_cleanup_paths(paths, data_root, protected, mounts):
    root = plain_path(data_root)
    result = []
    for name in paths:
        path = plain_path(name)
        require(path != root and inside(path, root), 'PREPARE_CLEANUP_OUTSIDE_DATA_ROOT')
        require(not any(overlaps(path, p) for p in protected), 'PREPARE_PROTECTED_PATH')
        require(not any(inside(m, path) for m in mounts), 'PREPARE_CLEANUP_MOUNT_REFUSED')
        require(not any(overlaps(path, p) for p in result), 'PREPARE_CLEANUP_OVERLAP')
        result.append(path)
    return result


def copy_dependencies(entries, tool_root):
    root = plain_path(tool_root)
    prepared = []
    # Check every input before writing any output. Source files may be in old data.
    for entry in entries:
        source = plain_path(entry['source'])
        relative = Path(entry['destination'])
        require(not relative.is_absolute() and '..' not in relative.parts,
                'PREPARE_DEPENDENCY_DESTINATION_INVALID')
        require(source.is_file(), 'PREPARE_DEPENDENCY_MISSING')
        destination = plain_path(root / relative)
        require(inside(destination, root) and destination != root, 'PREPARE_DEPENDENCY_DESTINATION_INVALID')
        prepared.append((source, destination, entry))
    result = {}
    for source, destination, entry in prepared:
        metadata = source.stat()
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if source != destination:
            shutil.copyfile(source, destination)
        os.chmod(destination, entry.get('mode', metadata.st_mode & 0o777))
        if os.name == 'posix':
            os.chown(destination, entry.get('uid', metadata.st_uid), entry.get('gid', metadata.st_gid))
        require(pin(source)['sha256'] == pin(destination)['sha256'], 'PREPARE_DEPENDENCY_COPY_FAILED')
        result[str(source)] = str(destination)
    return result


def mapped(value, changes):
    if isinstance(value, dict):
        result = {mapped(k, changes): mapped(v, changes) for k, v in value.items()}
        if set(result) == {'path', 'bytes', 'sha256'} and result['path'] != value['path']:
            return pin(result['path'])
        return result
    if isinstance(value, list):
        return [mapped(v, changes) for v in value]
    if isinstance(value, str):
        for old, new in sorted(changes.items(), key=lambda p: len(p[0]), reverse=True):
            value = value.replace(old, new)
    return value


def retained_dependencies(entries, tool_root, template_paths):
    """The first preparation moves inputs into their permanent private home."""
    root=plain_path(tool_root)/'prepared-inputs';manifest=root/'manifest.json'
    if manifest.exists():
        saved=read(manifest)
        require(saved['selection']==digest(dict(entries=entries,templates=template_paths)),
            'PREPARE_DEPENDENCY_SELECTION_CHANGED')
        for reference in saved['pins']:
            require(pin(reference['path'])==reference,'PREPARE_RETAINED_DEPENDENCY_CHANGED')
        return saved['changes'], {name:read(root/(name+'.json')) for name in template_paths}
    templates={name:read(path) for name,path in template_paths.items()}
    changes=copy_dependencies(entries,tool_root)
    # JSON dependency entries are explicitly ordered from leaves to their readers.
    for entry in entries:
        if entry.get('rewriteJson'):
            destination=changes[entry['source']];write(destination,mapped(read(destination),changes))
    root.mkdir(mode=0o700)
    pins=[pin(path) for path in changes.values()]
    for name,value in templates.items():pins.append(write(root/(name+'.json'),value))
    write(manifest,dict(selection=digest(dict(entries=entries,templates=template_paths)),changes=changes,pins=pins))
    return changes,templates


def fresh_target(template, observed, changes):
    changes = dict(changes)
    for key in ('targetId', 'dataRoot', 'networkId'):
        if template.get(key): changes[template[key]] = observed[key]
    old_uuid = template.get('dataPolicy', {}).get('databaseUuid')
    if old_uuid: changes[old_uuid] = observed['databaseUuid']
    services = {s['role']: s for s in observed['services']}
    for old in template['services']:
        for key in ('id', 'imageId', 'ip'):
            changes[old[key]] = services[old['role']][key]
    target = mapped(deepcopy(template), changes)
    target.update({k: observed[k] for k in ('targetId', 'dataRoot', 'networkId', 'services')})
    target['preparedEmptyTarget'] = True
    if 'dataPaths' in observed: target['dataPaths'] = observed['dataPaths']
    return target


def fresh_owner(original, target_ref, source_ref):
    """Reuse installed application settings; main-replacement history is inapplicable to new resources."""
    owner = deepcopy(original)
    owner['sources'] = {source_ref: owner['sources'][source_ref]}
    target = owner['targets'][target_ref]
    target.pop('mainApplication', None);target.pop('replacement', None)
    target['sourceConfigRef'] = source_ref
    owner['targets'] = {target_ref: target}
    for key in list(owner):
        if key.startswith('target') and key != 'targets': del owner[key]
    owner.pop('sourceProgramArchivePolicies', None)
    return owner


def control_arguments(python, engine, reference):
    return [python, '-B', str(Path(engine)/'control_entry.py'), 'serve', '--config-pin', canonical(reference).decode()]


def control_clients(setting):
    clients=setting.get('allowedClientAddresses')
    require(isinstance(clients,list) and clients,'PREPARE_CONTROL_CLIENTS_INVALID')
    try:valid=all(isinstance(value,str) and str(ipaddress.ip_address(value))==value for value in clients)
    except ValueError:valid=False
    require(valid,'PREPARE_CONTROL_CLIENTS_INVALID')
    return clients


def control_document(template, setting, root, result, changes):
    control=mapped(deepcopy(template),changes)
    control.update(taskRoot=str(root),registryRoot=str(root/'registry'),ledgerRoot=str(root/'ledger'),
        restoreConfigurations={result['sourceConfigRef']:{result['targetConfigRef']:result['ownerPin']}},
        listenAddress=setting['listenAddress'],listenPort=setting['listenPort'],
        allowedClientAddresses=control_clients(setting),
        workingDirectory=setting['engineDirectory'],pythonPin=pin(setting['pythonPath']))
    engine=Path(setting['engineDirectory'])
    old_roots={reference['path'].rsplit('/',1)[0]
               for reference in control.get('programPins',{}).values()}
    control['programPins']={}
    for role in ('recovery','repository'):
        entry=engine/(role+'_entry.py')
        require(entry.is_file(),'PREPARE_CONTROL_PROGRAM_MISSING')
        control['programPins'][role]=pin(entry)
    if 'PYTHONPATH' in control.get('environment',{}):
        paths=control['environment']['PYTHONPATH'].split(':')
        for index,path in enumerate(paths):
            for old in old_roots:
                if path==old or path.startswith(old+'/'):
                    paths[index]=engine.as_posix()+path[len(old):]
                    break
        control['environment']['PYTHONPATH']=':'.join(paths)
    return control


def command(argv, *, input=None, timeout=120, action='COMMAND', subject=None):
    failure=dict(action=action,object=subject,exitCode=None,reason='COMMAND_FAILED')
    try:
        result = subprocess.run(argv, input=input, capture_output=True, timeout=timeout)
    except (subprocess.TimeoutExpired,OSError) as error:
        failure['reason']='TIMEOUT' if isinstance(error,subprocess.TimeoutExpired) else 'EXEC_FAILED'
        raise PreparationError('PREPARE_NATIVE_COMMAND_FAILED',failure) from None
    if result.returncode:
        failure['exitCode']=result.returncode
        # Emit fixed categories only: raw argv/stderr can contain environment secrets.
        stderr=result.stderr.decode('utf-8',errors='replace').lower()
        for fragment,reason in [('device or resource busy','RESOURCE_BUSY'),('permission denied','PERMISSION_DENIED'),
                                ('cannot connect to the docker daemon','DAEMON_UNAVAILABLE'),('no such','NOT_FOUND')]:
            if fragment in stderr:failure['reason']=reason;break
        raise PreparationError('PREPARE_NATIVE_COMMAND_FAILED',failure)
    return result.stdout.decode('utf-8').strip()


@contextmanager
def exclusive(path):
    import fcntl
    path = plain_path(path)
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise PreparationError('PREPARE_TARGET_BUSY') from None
        yield
    finally:
        os.close(fd)


class NativePreparation:
    def __init__(self, config):
        require(config.get('host') == HOST, 'PREPARE_HOST_REFUSED')
        self.config = config

    def docker(self, *args, **kwargs):
        action='DOCKER';subject=None
        if args[0] in ('volume','network','image') and args[1] in ('ls','inspect','rm','load','create'):
            action+='_'+args[0].upper()+'_'+args[1].upper()
            if args[1]=='rm':subject=args[-1]
        elif args[0] in ('stop','rm','start','create','inspect','exec','info','ps'):
            action+='_'+args[0].upper()
            if args[0] in ('stop','rm','start'):subject=args[-1]
        return command([self.config.get('dockerPath', '/usr/bin/docker'), *args],action=action,subject=subject,**kwargs)

    def identity(self):
        require(os.name == 'posix' and os.geteuid() == 0, 'PREPARE_LINUX_ROOT_REQUIRED')
        require(Path('/etc/machine-id').read_text().strip() == self.config['machineId'], 'PREPARE_MACHINE_CHANGED')
        require(self.docker('info', '--format', '{{.ID}}') == self.config['dockerEngineId'], 'PREPARE_DOCKER_CHANGED')

    def cleanup_set(self):
        selected = {k:list(self.config['cleanup'].get(k, [])) for k in
                    ('directories','containerIds','volumeNames','networkIds','serviceNames')}
        previous = Path(self.config['stateRoot'])/'last-target.json'
        if previous.exists():
            for key, values in read(previous).items():
                require(key in selected, 'PREPARE_PREVIOUS_RESOURCES_INVALID')
                selected[key] = list(dict.fromkeys(selected[key] + values))
        return selected

    def plan(self, request):
        self.identity()
        c = self.config
        control_clients(c['control'])
        point = c['points'].get(request['recoveryPointRef'])
        require(point and point['applicationId'] == request['applicationId'], 'PREPARE_POINT_NOT_CONFIGURED')
        require(set(point['roleImages']) == set(ROLES), 'PREPARE_IMAGES_INCOMPLETE')
        protected = [c['toolRoot'], c['stateRoot'], c['dockerRoot'], *c['archiveRoots']]
        selected = self.cleanup_set()
        paths = validate_cleanup_paths(selected['directories'], c['dataRoot'], protected, mount_paths())
        for source in c['archiveRoots']:
            require(plain_path(source).is_dir(), 'PREPARE_ARCHIVE_UNAVAILABLE')
        require(plain_path(point['imageArchivePin']['path']).is_file(), 'PREPARE_IMAGES_UNAVAILABLE')
        require(inside(sys.executable, c['toolRoot']) and inside(__file__, c['toolRoot']),
                'PREPARE_RUNNER_NOT_PRESERVED')
        public = dict(host=HOST, applicationId=request['applicationId'], recoveryPointRef=request['recoveryPointRef'],
            cleanupSummary=[str(p) for p in paths] + [str(len(selected['containerIds'])) + ' containers',
                str(len(selected['volumeNames'])) + ' volumes', str(len(selected['networkIds'])) + ' networks'],
            preserveSummary=[c['toolRoot'], c['stateRoot'], *c['archiveRoots']], stages=list(STAGES))
        public['cleanupSummary'] += ['local bind: '+b['source']+' -> '+b['target'] for b in c['cleanup'].get('bindMounts',[])]
        public['planDigest'] = digest(dict(configuration=c, cleanup=selected,
            request={k: request[k] for k in ('applicationId', 'recoveryPointRef')}))
        return public

    def dependencies(self, request, operation_root):
        c = self.config
        changes,templates = retained_dependencies(c['dependencies'],c['toolRoot'],dict(
            owner=c['ownerTemplatePath'],control=c['control']['templatePath'],registration=c['control']['registrationPath']))
        point = c['points'][request['recoveryPointRef']]
        # Docker load checks the image contents; do not scan the same tar twice.
        require(Path(point['imageArchivePin']['path']).stat().st_size == point['imageArchivePin']['bytes'], 'PREPARE_IMAGE_ARCHIVE_CHANGED')
        self.docker('image', 'load', '--input', point['imageArchivePin']['path'], timeout=600)
        for identity in point['roleImages'].values():
            require(json.loads(self.docker('image', 'inspect', identity))[0]['Id'] == identity, 'PREPARE_IMAGE_MISSING')
        owner = fresh_owner(templates['owner'],c['ownerTemplateTargetRef'],point['sourceConfigRef'])
        template = owner['targets'][c['ownerTemplateTargetRef']]
        require(len(c['services']) == len(ROLES) and {s['role'] for s in c['services']} == set(ROLES), 'PREPARE_SERVICES_INCOMPLETE')
        for spec in c['services']:
            for mount in spec.get('binds', []):
                source = plain_path(Path(c['toolRoot']) / mount['source'])
                require(inside(source, c['toolRoot']) and source.is_file(), 'PREPARE_BIND_FILE_MISSING')
        # Snapshot installed templates before their original directories can be removed.
        write(operation_root/'owner-template.json', owner)
        write(operation_root/'control-template.json', templates['control'])
        write(operation_root/'registration-template.json', templates['registration'])
        write(operation_root/'dependency-map.json', changes)

    def cleanup(self):
        c = self.config
        selected = self.cleanup_set()
        protected = [c['toolRoot'], c['stateRoot'], c['dockerRoot'], *c['archiveRoots']]
        mounts = mount_paths()
        paths = validate_cleanup_paths(selected['directories'], c['dataRoot'], protected, mounts)
        # Successful inventory distinguishes an absent recorded ID from a daemon failure.
        containers=set(self.docker('ps','-a','--no-trunc','--format','{{.ID}}').splitlines())
        volumes=set(self.docker('volume','ls','-q').splitlines())
        networks=set(self.docker('network','ls','--no-trunc','--format','{{.ID}}').splitlines())
        # Inspect the explicit deletion set before its first destructive action.
        for name in selected['serviceNames']:
            require(re.fullmatch(r'spug-[a-zA-Z0-9_-]+\.service', name), 'PREPARE_SERVICE_INVALID')
        for identity in selected['containerIds']:
            require(re.fullmatch('[a-f0-9]{64}', identity), 'PREPARE_CONTAINER_ID_INVALID')
            if identity not in containers:continue
            container = json.loads(self.docker('inspect', identity))[0]
            require(container['Id'] == identity, 'PREPARE_CONTAINER_CHANGED')
        volume_points={}
        for name in selected['volumeNames']:
            require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,180}', name), 'PREPARE_VOLUME_INVALID')
            if name not in volumes:continue
            volume = json.loads(self.docker('volume', 'inspect', name))[0]
            volume_points[name]=volume['Mountpoint']
            require(not volume.get('Options'), 'PREPARE_MOUNTED_VOLUME_REFUSED')
            require(not any(overlaps(volume['Mountpoint'], p) for p in [c['toolRoot'], c['stateRoot'], *c['archiveRoots']]),
                    'PREPARE_PROTECTED_VOLUME')
        binds=volume_bind_unmounts(c,selected,volume_points,mount_entries()) if c['cleanup'].get('bindMounts') else []
        for identity in selected['networkIds']:
            require(re.fullmatch('[a-f0-9]{64}',identity),'PREPARE_NETWORK_ID_INVALID')
            if identity not in networks:continue
            members=json.loads(self.docker('network','inspect',identity))[0].get('Containers') or {}
            require(set(members) <= set(selected['containerIds']),'PREPARE_NETWORK_SHARED')
        for name in selected['serviceNames']:command(['systemctl', 'stop', name],action='SERVICE_STOP',subject=name)
        for identity in selected['containerIds']:
            if identity not in containers:continue
            self.docker('stop', '--time', '30', identity)
            self.docker('rm', identity)
        for target,name in binds:command(['umount','--',target],action='UNMOUNT',subject=name)
        for name in selected['volumeNames']:
            if name in volumes:self.docker('volume', 'rm', name)
        for identity in selected['networkIds']:
            if identity in networks:self.docker('network','rm',identity)
        mounts = mount_paths()
        for path in paths:
            # Python's fd-based Linux rmtree does not follow a substituted symlink.
            require(shutil.rmtree.avoids_symlink_attacks, 'PREPARE_SAFE_DELETE_UNAVAILABLE')
            validate_cleanup_paths([str(path)], c['dataRoot'], protected, mounts)
            if path.is_dir(): shutil.rmtree(path)
            elif path.exists(): path.unlink()

    def initialize(self, request, operation_root):
        c = self.config
        point = c['points'][request['recoveryPointRef']]
        target_ref = c['targetPrefix'] + '-' + hashlib.sha256(request['operationId'].encode()).hexdigest()[:12]
        require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,120}', target_ref), 'PREPARE_TARGET_NAME_INVALID')
        data = plain_path(Path(c['dataRoot']) / target_ref)
        require(not data.exists(), 'PREPARE_TARGET_EXISTS')
        data.mkdir(mode=0o700)
        (data/'config').mkdir(mode=0o700)
        resources=dict(directories=[str(data)],containerIds=[],volumeNames=[],networkIds=[],
            serviceNames=['spug-prepare59-restore.service'])
        last_target=Path(c['stateRoot'])/'last-target.json';write(last_target,resources)
        changes = read(operation_root/'dependency-map.json')
        if c.get('templateSubnet'): changes[c['templateSubnet']] = c['subnet']
        network = ipaddress.ip_network(c['subnet'])
        for value in json.loads(self.docker('network', 'inspect', *self.docker('network','ls','-q').splitlines())):
            for entry in value.get('IPAM', {}).get('Config') or []:
                if entry.get('Subnet'):
                    existing = ipaddress.ip_network(entry['Subnet'])
                    require(existing.version != network.version or not existing.overlaps(network), 'PREPARE_SUBNET_IN_USE')
        network_id = self.docker('network','create','--internal','--subnet',c['subnet'],
            '--label','intruoyi.recovery.target='+target_ref,target_ref)
        resources['networkIds'].append(network_id);write(last_target,resources)
        data_paths = {}; services = []
        for role in ('mysql','minio','redis'):
            path = data/role;path.mkdir(mode=0o700);data_paths[role]=str(path)
            spec=next(s for s in c['services'] if s['role']==role)
            uid,gid=spec['dataOwnership'];os.chown(path,uid,gid)
        for index, spec in enumerate(c['services']):
            role=spec['role']; ip=str(network.network_address+32+index)
            if spec.get('templateIp'): changes[spec['templateIp']] = ip
        # Materialize per-target config so IP substitution never edits kept tools.
        for spec in c['services']:
            for mount in spec.get('binds',[]):
                source=plain_path(Path(c['toolRoot'])/mount['source'])
                require(inside(source,c['toolRoot']) and source.is_file(),'PREPARE_BIND_FILE_MISSING')
                if mount.get('rewriteAddresses',False):
                    destination=data/'config'/(hashlib.sha256(str(source).encode()).hexdigest()[:12]+'-'+source.name)
                    destination.write_text(mapped(source.read_text(encoding='utf-8'),changes),encoding='utf-8')
                    metadata = source.stat()
                    os.chmod(destination, metadata.st_mode & 0o777)
                    os.chown(destination, metadata.st_uid, metadata.st_gid)
                    # Source pins in the owner must refer to the new configuration.
                    changes[str(source)]=str(destination)
        for index, spec in enumerate(c['services']):
            role=spec['role']; ip=str(network.network_address+32+index)
            env = mapped(spec.get('environment',[]),changes)
            require(all(isinstance(v,str) and '\n' not in v and '\r' not in v for v in env),'PREPARE_ENV_INVALID')
            env_file = data/(role+'.env');env_file.write_text('\n'.join(env)+'\n',encoding='utf-8');os.chmod(env_file,0o600)
            args=['create','--name',target_ref+'-'+role,'--network',network_id,'--network-alias',role,
                '--ip',ip,'--restart=no','--memory',str(spec['memoryBytes']),'--env-file',str(env_file),
                '--label','intruoyi.recovery.target='+target_ref,'--log-opt','max-size=5m','--log-opt','max-file=2']
            for mount in spec.get('binds',[]):
                source=plain_path(mapped(str(Path(c['toolRoot'])/mount['source']),changes))
                require((inside(source,c['toolRoot']) or inside(source,data)) and source.is_file(),'PREPARE_BIND_FILE_MISSING')
                args+=['--mount','type=bind,src='+str(source)+',dst='+mount['destination']+',readonly']
            if role in data_paths:
                args+=['--mount','type=bind,src='+data_paths[role]+',dst='+spec['dataDestination']]
            if role=='frontend':args+=['-p','127.0.0.1:'+str(c['frontendPort'])+':80']
            for key,flag in [('user','--user'),('workingDirectory','--workdir'),('entrypoint','--entrypoint')]:
                if spec.get(key): args += [flag,spec[key]]
            if spec.get('healthCommand'):args+=['--health-cmd',spec['healthCommand'],'--health-interval','10s']
            identity=self.docker(*args,point['roleImages'][role],*mapped(spec.get('command',[]),changes))
            resources['containerIds'].append(identity);write(last_target,resources)
            actual=json.loads(self.docker('inspect',identity))[0]
            services.append(dict(role=role,id=actual['Id'],imageId=actual['Image'],ip=str(network.network_address+32+index)))
        by_role={s['role']:s for s in services}
        for role in ('mysql','redis'):self.docker('start',by_role[role]['id'])
        database=c['database'];require(re.fullmatch('[A-Za-z0-9_-]{1,64}',database),'PREPARE_DATABASE_INVALID')
        query="SELECT @@server_uuid; SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='%s'; SELECT @@lower_case_table_names" % database
        end=time.monotonic()+180
        while True:
            try:
                values=self.docker('exec',by_role['mysql']['id'],'mysql','--defaults-extra-file='+c['mysqlClientFile'],'-Nse',query).splitlines()
                break
            except PreparationError:
                require(time.monotonic()<end,'PREPARE_MYSQL_INIT_TIMEOUT');time.sleep(2)
        require(len(values)==3 and values[1]=='0' and values[2]==str(c['mysqlCaseRule']),'PREPARE_DATABASE_NOT_EMPTY')
        password=(Path(c['toolRoot'])/c['redisSecret']).read_bytes().rstrip(b'\r\n')+b'\n'
        result=self.docker('exec','-i',by_role['redis']['id'],'redis-cli','--no-auth-warning','--askpass','DBSIZE',input=password)
        require(result.strip().splitlines()[-1]=='0','PREPARE_REDIS_NOT_EMPTY')
        require(not any(Path(data_paths['minio']).iterdir()),'PREPARE_MINIO_NOT_EMPTY')
        owner=read(operation_root/'owner-template.json');old_ref=c['ownerTemplateTargetRef'];old=owner['targets'][old_ref]
        observed=dict(targetId=target_ref,dataRoot=str(data),networkId=network_id,services=services,databaseUuid=values[0],
            dataPaths=[*data_paths.values(),str(data/'config'),str(Path(c['toolRoot'])/'private')])
        for role, path in data_paths.items():
            old_path=c.get('templateDataPaths',{}).get(role)
            if old_path:changes[old_path]=path
        changes[old_ref]=target_ref
        target=fresh_target(old,observed,changes)
        target['machineId']=c['machineId'];target['dockerEngineId']=c['dockerEngineId']
        target['resourceBudget']=c['resourceBudget']
        owner=mapped(owner,changes)
        owner['targets']={target_ref:target}
        owner['operationsRoot']=str(operation_root/'recovery-operations');Path(owner['operationsRoot']).mkdir(mode=0o700)
        owner['pythonPin']=pin(c['control']['pythonPath'])
        owner['formalModuleDirectory']=c['formalModuleDirectory']
        owner_pin=write(operation_root/'recovery.json',owner)
        result=dict(targetConfigRef=target_ref,sourceConfigRef=point['sourceConfigRef'],ownerPin=owner_pin,
            progressRoot=str(operation_root),pythonPath=c['control']['pythonPath'],observed=observed)
        result.update(self.install_control(request,operation_root,result,changes))
        return result

    def install_control(self,request,root,result,changes):
        """Start one dedicated restore control with the new immutable config pin."""
        setting=self.config['control']
        service=setting['serviceName']
        require(service=='spug-prepare59-restore.service','PREPARE_CONTROL_SERVICE_REFUSED')
        control=control_document(read(root/'control-template.json'),setting,root,result,changes)
        registration=read(root/'registration-template.json')
        require(registration['applicationId']==request['applicationId'] and
            registration['sourceConfigRef']==result['sourceConfigRef'],'PREPARE_REGISTRATION_MISMATCH')
        registration['allowedRestoreTargets']=[{'configRef':result['targetConfigRef']}]
        registration_pin=write(root/'registration.json',registration)
        registry=root/'registry';registry.mkdir(mode=0o700)
        for folder in ('applications','points'):(registry/folder).mkdir(mode=0o700)
        write(registry/'applications'/(request['applicationId']+'.pin.json'),registration_pin)
        (root/'ledger').mkdir(mode=0o700)
        require(inside(setting['engineDirectory'],self.config['toolRoot']) and
            inside(setting['pythonPath'],self.config['toolRoot']),'PREPARE_CONTROL_DEPENDENCY_OUTSIDE_TOOLS')
        entry=Path(setting['engineDirectory'])/'control_entry.py'
        require(entry.is_file() and Path(setting['pythonPath']).is_file(),'PREPARE_CONTROL_RUNTIME_MISSING')
        control_pin=write(root/'control.json',control)
        environment_path=root/'control.env'
        environment=[]
        for key,value in control['environment'].items():
            require(re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',key) and isinstance(value,str) and
                    not any(char in value for char in ('\x00','\r','\n')),'PREPARE_CONTROL_ENVIRONMENT_INVALID')
            environment.append(key+'="'+value.replace('\\','\\\\').replace('"','\\"')+'"\n')
        with environment_path.open('x',encoding='utf-8',newline='\n') as stream:
            os.chmod(environment_path,0o600)
            stream.write(''.join(environment))
        def quoted(value):return '"'+str(value).replace('%','%%').replace('\\','\\\\').replace('"','\\"')+'"'
        args=control_arguments(setting['pythonPath'],setting['engineDirectory'],control_pin)
        unit='[Unit]\nDescription=Spug backup host fresh restore control\nAfter=docker.service\n[Service]\nType=simple\nEnvironmentFile='+str(environment_path)+'\nExecStart='+ ' '.join(quoted(v) for v in args)+'\nRestart=no\nUMask=0077\n'
        path=Path('/etc/systemd/system')/service
        temporary=path.with_suffix('.service.new');temporary.write_text(unit,encoding='utf-8');os.chmod(temporary,0o600)
        os.replace(temporary,path)
        command(['systemctl','daemon-reload']);command(['systemctl','restart',service])
        require(command(['systemctl','is-active',service])=='active','PREPARE_CONTROL_NOT_ACTIVE')
        return dict(controlPin=control_pin,registrationPin=registration_pin,registrationSha256=registration_pin['sha256'],
            engineSelectionRef=control['engineSelectionRef'],listenAddress=setting['listenAddress'],listenPort=setting['listenPort'])

    def execute(self, request, emit):
        operation=request['operationId'];require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.:-]{7,159}',operation),'PREPARE_OPERATION_INVALID')
        root=plain_path(self.config['stateRoot'])/hashlib.sha256(operation.encode()).hexdigest()
        with ExitStack() as stack:
            stack.enter_context(self.host_lock())
            for path in sorted(self.config.get('sourceLockPaths',[])):stack.enter_context(exclusive(path))
            if root.exists():
                require(read(root/'request.json')==request,'PREPARE_OPERATION_REUSED')
                result=read(root/'result.json') if (root/'result.json').exists() else dict(operationId=operation,state='UNKNOWN',errorCode='PREPARE_PREVIOUS_OUTCOME_UNKNOWN')
                emit(dict(type='result',record=result));return result
            plan=self.plan(request)
            require(request.get('confirmed') is True and request.get('planDigest')==plan['planDigest'],'PREPARE_PLAN_CHANGED')
            retained=self.resettable_reservation()
            root.mkdir(mode=0o700);write(root/'request.json',request)
            return self.run_stages(request,root,emit,retained)

    def resettable_reservation(self):
        """The host lock is held: admit only our current target's exited failed worker."""
        active_path=Path(self.config['hostReservationRoot'])/'active.json'
        if not active_path.exists():return None
        code='PREPARE_RESTORE_ACTIVE';active=read(active_path)
        restore=plain_path(active['operationRoot']);previous=restore.parent.parent
        state=plain_path(self.config['stateRoot'])
        require(previous.parent==state and restore.parent.name=='recovery-operations' and
                restore.name==active['operationId'] and active['machineId']==self.config['machineId'],code)
        paths=[previous/'request.json',previous/'result.json',state/'last-target.json',
               *(restore/name for name in ('request.json','result.json','worker-result.json','child-exit.json','resource-reservation.json'))]
        require(all(path.is_file() for path in paths),code)
        prepared_request=read(previous/'request.json');prepared=read(previous/'result.json')
        expected_hash=hashlib.sha256(prepared_request['operationId'].encode()).hexdigest()
        target=self.config['targetPrefix']+'-'+expected_hash[:12]
        require(previous.name==expected_hash and active['targetConfigRef']==target and
                prepared.get('operationId')==prepared_request['operationId'] and
                prepared.get('state')=='INITIALIZED' and prepared.get('targetConfigRef')==target and
                read(state/'last-target.json').get('directories')==[str(Path(self.config['dataRoot'])/target)],code)
        original_request=read(restore/'request.json')
        require(original_request.get('operationId')==restore.name and original_request.get('action')=='RESTORE' and
                original_request.get('targetConfigRef')==target,code)
        result=read(restore/'result.json');worker=read(restore/'worker-result.json');exited=read(restore/'child-exit.json')
        for value in (result,worker):
            require(value.get('operationId')==restore.name and value.get('action')=='RESTORE' and
                    value.get('state')=='FAILED_RETAINED' and type(value.get('actualExitCode')) is int and
                    value['actualExitCode']==1 and value.get('finishedAt'),code)
        # recovery_minimal.run_child writes this only after wait/poll reports the original exit.
        require(exited.get('operation')=='W04_RESTORE_CHILD' and type(exited.get('actualExitCode')) is int and
                exited['actualExitCode']==1 and exited.get('timedOut') is False and exited.get('finishedAt'),code)
        worker_pin=pin(restore/'worker-result.json');exit_pin=pin(restore/'child-exit.json')
        reservation_pin=pin(restore/'resource-reservation.json')
        require(active.get('reservationPin')==reservation_pin and
                all(reference in result.get('originalResultPins',[]) for reference in (worker_pin,exit_pin,reservation_pin)),code)
        return dict(previousReservation=active,resultPin=pin(restore/'result.json'),workerResultPin=worker_pin,childExitPin=exit_pin)

    def release_reset_reservation(self, retained, root):
        active_path=Path(self.config['hostReservationRoot'])/'active.json'
        require(read(active_path)==retained['previousReservation'],'PREPARE_RESTORE_ACTIVE')
        write(root/'restore-reset.json',dict(retained,reason='PREPARED_TARGET_REINITIALIZATION',releasedAt=now()))
        active_path.unlink()

    def host_lock(self):
        require(self.config['hostReservationRoot']=='/var/lib/spug-restore-resources','PREPARE_SHARED_LOCK_REQUIRED')
        return exclusive(Path(self.config['hostReservationRoot'])/'lock')

    def query(self, request):
        """Prove the original stopped under its execution lock, fencing delayed starts."""
        operation=request['operationId']
        require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.:-]{7,159}',operation),'PREPARE_OPERATION_INVALID')
        root=plain_path(self.config['stateRoot'])/hashlib.sha256(operation.encode()).hexdigest()
        self.identity()
        try:
            with self.host_lock():
                if (root/'request.json').exists():
                    require(read(root/'request.json')==request,'PREPARE_OPERATION_REUSED')
                else:
                    root.mkdir(mode=0o700,exist_ok=True)
                    write(root/'request.json',request)
                if (root/'result.json').exists():
                    result=read(root/'result.json')
                else:
                    result=read(root/'status.json') if (root/'status.json').exists() else dict(
                        operationId=operation,host=HOST,applicationId=request['applicationId'],
                        recoveryPointRef=request['recoveryPointRef'],stages=[])
                    result.update(state='FAILED',errorCode='PREPARE_INTERRUPTED',finishedAt=now())
                    for stage in result['stages']:
                        if stage['state']=='RUNNING':stage.update(state='FAILED',errorCode='PREPARE_INTERRUPTED',finishedAt=now())
                    # execute returns this terminal if its SSH request arrives later.
                    write(root/'result.json',result)
                return dict(result,workerStopped=True)
        except PreparationError as error:
            if str(error)!='PREPARE_TARGET_BUSY':raise
            return dict(operationId=operation,state='UNKNOWN',workerStopped=False)

    def run_stages(self,request,root,emit,retained=None):
        record=dict(operationId=request['operationId'],host=HOST,applicationId=request['applicationId'],recoveryPointRef=request['recoveryPointRef'],
            state='RUNNING',startedAt=now(),finishedAt=None,errorCode=None,targetConfigRef=None,stages=[])
        try:
            for name in STAGES:
                stage=dict(name=name,state='RUNNING',startedAt=now(),finishedAt=None,errorCode=None)
                record['stages'].append(stage);write(root/'status.json',record);emit(dict(type='stage',stage=stage))
                if name=='dependencies':self.dependencies(request,root)
                elif name=='cleanup':
                    if retained:self.release_reset_reservation(retained,root)
                    self.cleanup()
                else:record.update(self.initialize(request,root))
                stage.update(state='SUCCEEDED',finishedAt=now());write(root/'status.json',record);emit(dict(type='stage',stage=stage))
            # Spug still has to publish its binding and verify authenticated selections.
            record.update(state='INITIALIZED',finishedAt=now())
        except Exception as error:
            code=str(error) if isinstance(error,PreparationError) else 'PREPARE_NATIVE_FAILED'
            record.update(state='FAILED',errorCode=code,finishedAt=now())
            if isinstance(error,PreparationError) and error.failure:record['failure']=error.failure
            if record['stages']:
                record['stages'][-1].update(state='FAILED',errorCode=code,finishedAt=now())
                if record.get('failure'):record['stages'][-1]['failure']=record['failure']
                emit(dict(type='stage',stage=record['stages'][-1]))
        write(root/'result.json',record);emit(dict(type='result',record=record));return record


def handle(payload, emit):
    reference=payload['configurationPin']
    require(pin(reference['path'])==reference,'PREPARE_CONFIGURATION_CHANGED')
    native=NativePreparation(read(reference['path']))
    action=payload['action']
    if action=='preview':return native.plan(payload['request'])
    if action=='execute':return native.execute(payload['request'],emit)
    require(action=='query','PREPARE_ACTION_INVALID')
    return native.query(payload['request'])


if __name__=='__main__':
    def emit(value):print(json.dumps(value,ensure_ascii=False),flush=True)
    try:
        payload=json.load(sys.stdin);result=handle(payload,emit)
        if payload['action']!='execute':emit(result)
    except Exception as error:
        emit(dict(errorCode=str(error) if isinstance(error,PreparationError) else 'PREPARE_NATIVE_FAILED'))
        sys.exit(1)
