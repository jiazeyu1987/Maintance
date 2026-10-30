"""Explicit recovery of an unopened release, using a complete bound checkpoint.

Private container snapshots and data never leave the registered target. Failed
data is retained; neither failed SQL nor migration-success markers are replayed.
"""
import copy
import hashlib
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tarfile
from urllib.parse import quote

from intruoyi_runtime import require, file_sha, package_identity, runtime_config_snapshot, sha
from intruoyi_runtime import restore_sql_snapshot, database_snapshot_path


def now():
    return datetime.now(timezone.utc).isoformat()


def inventory(profile, api):
    require(profile.get('recoveryInventoryConfirmed') is True,
            'Explicit recovery data inventory required before deployment')
    rows = profile.get('recoveryDataMounts')
    require(isinstance(rows, list) and {x.get('role') for x in rows} == {'redis','minio'},
            'Recovery inventory must include registered Redis and MinIO data mounts')
    result, seen = [], set()
    for row in rows:
        role, destination = row['role'], row.get('destination')
        require(isinstance(destination, str) and destination.startswith('/') and destination != '/', 'Explicit data mount destination required')
        info = api['remote'].inspect(profile[role])
        matches = [m for m in info['Mounts'] if m['Destination'] == destination and m.get('RW')]
        require(len(matches) == 1 and matches[0]['Type'] in ('bind','volume'), 'Recovery requires an exact writable data mount: '+role)
        mount = matches[0]
        source = Path(mount['Source'])
        require(source.is_dir() and not source.is_symlink() and source.resolve() == source
                and len(source.parts) >= 4, 'Unsafe recovery data directory')
        require(not any(source == previous or source in previous.parents or previous in source.parents for previous in seen),
                'Recovery data directories overlap')
        require(source not in Path(profile['stagingRoot']).parents and source != Path(profile['stagingRoot']),
                'Recovery evidence cannot be inside recovered data')
        seen.add(source)
        result.append(dict(role=role, containerId=info['Id'], mount=mount))
    return result


def checksums(profile, api):
    sql = api['remote'].sql
    sql(profile, 'SHOW TABLES;')
    tables = sql(profile, "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA=DATABASE() AND TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME;").splitlines()
    result = {}
    for table in tables:
        require(re.fullmatch('[A-Za-z0-9_]+', table), 'Unsafe table in recovery inventory')
        sql(profile, 'DESCRIBE `'+table+'`;')
        row = sql(profile, 'CHECKSUM TABLE `'+table+'` EXTENDED;').split('\t')
        require(len(row) == 2 and row[1].isdigit(), 'Table cannot be verified for recovery: '+table)
        result[table] = row[1]
    return result


def recovery_runtime_config_sha(profile, containers, backend_maintenance):
    result={}
    for role in ('frontend','backend','database'):
        info=containers[profile[role]]
        snapshot=copy.deepcopy(runtime_config_snapshot(info))
        config=snapshot['Config']
        config['Image']=info['Image']
        config['Labels']={key:value for key,value in (config.get('Labels') or {}).items()
                          if not key.startswith('intruoyi.recovery.')}
        environment=[value for value in config.get('Env',[])
                     if not (role=='backend' and value.startswith('INTRUOYI_RELEASE_MAINTENANCE='))]
        if role=='backend':
            environment.append('INTRUOYI_RELEASE_MAINTENANCE='+str(backend_maintenance).lower())
        config['Env']=sorted(environment)
        snapshot['HostConfig'].pop('ContainerIDFile',None)
        # Docker may serialize the unset OOM-killer override as null on the
        # original and false on recreation. Both keep the OOM killer enabled;
        # true must remain a configuration difference.
        if snapshot['HostConfig'].get('OomKillDisable') is None:
            snapshot['HostConfig']['OomKillDisable']=False
        result[role]=snapshot
    return sha(result)


def actual_runtime_config_sha(profile, api, backend_maintenance):
    containers={name:api['remote'].inspect(name) for name in
                (profile['frontend'],profile['backend'],profile['database'])}
    return recovery_runtime_config_sha(profile,containers,backend_maintenance)


def archive_data(source, destination):
    # Data inventory is ordinary files/directories. No dereferenced links or
    # special device members are admitted to the restore boundary.
    with tarfile.open(destination, 'x:') as archive:
        os.chmod(destination, 0o600)
        for path in sorted(source.rglob('*')):
            require(not path.is_symlink() and (path.is_file() or path.is_dir()), 'Unsupported recovery data member')
            archive.add(path, arcname=path.relative_to(source).as_posix(), recursive=False)
    return dict(path=str(destination), sha256=file_sha(destination), bytes=destination.stat().st_size)


def validate_archive(path):
    with tarfile.open(path, 'r:') as archive:
        names = set()
        for member in archive:
            name = PurePosixPath(member.name)
            require(member.name and not name.is_absolute() and '..' not in name.parts
                    and str(name) == member.name and member.name not in names
                    and (member.isdir() or member.isfile()) and not member.issparse(), 'Unsafe recovery archive member')
            names.add(member.name)
        return names


def verify_data(source, archive_path):
    with tarfile.open(archive_path,'r:') as archive:
        members=archive.getmembers()
        require({p.relative_to(source).as_posix() for p in source.rglob('*')} == {m.name for m in members},
                'Recovered data directory contains missing or extra members')
        for member in members:
            target=source/member.name
            require(not target.is_symlink() and (target.is_dir() if member.isdir() else target.is_file()),
                    'Recovered data member type differs')
            if member.isfile():
                expected=hashlib.sha256()
                with archive.extractfile(member) as stream:
                    for data in iter(lambda:stream.read(1024*1024),b''):
                        expected.update(data)
                require(file_sha(target)==expected.hexdigest(), 'Recovered file checksum differs')


def restore_data(source, archive_path, attempt_id):
    """Resume only this bound attempt; never discard partial candidate data.

    Extract and verify first, then journal each set of top-level renames. A
    worker can die on either side of a rename without losing which tree owns
    the failed data. Callers must keep every data-service writer stopped.
    """
    require(re.fullmatch('JOB-[a-f0-9]{10}',attempt_id), 'Valid data recovery attempt required')
    require(source.is_dir() and not source.is_symlink(), 'Recovery data directory missing or redirected')
    members=validate_archive(archive_path)
    retained=source.parent/(source.name+'.failed-'+attempt_id)
    staging=source.parent/(source.name+'.restore-'+attempt_id)
    journal=source.parent/(source.name+'.restore-'+attempt_id+'.json')
    binding=dict(source=str(source.resolve()),archiveSha256=file_sha(archive_path),attemptId=attempt_id)
    for path in (retained,staging,journal):
        require(not path.is_symlink(), 'Recovery journal or directory redirected')
    def save():
        temporary=journal.with_suffix('.next')
        require(not temporary.is_symlink(), 'Recovery journal temporary file redirected')
        descriptor=os.open(str(temporary),os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
        with os.fdopen(descriptor,'w') as stream:
            json.dump(state,stream)
            stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,journal)
    if journal.exists():
        state=json.loads(journal.read_text())
        require(state.get('binding')==binding, 'Data recovery journal binding changed')
    else:
        require(not retained.exists() and not staging.exists(), 'Unowned recovery data directory already exists')
        with tarfile.open(archive_path,'r:') as archive:
            required=sum(member.size for member in archive if member.isfile())
        require(shutil.disk_usage(source).free > required, 'Insufficient space to restore data while retaining failed contents')
        state=dict(binding=binding,phase='extracting')
        save()
    require(state['phase'] in ('extracting','retaining','installing','complete'), 'Unknown data recovery phase')
    if state['phase']=='extracting':
        staging.mkdir(mode=0o700,exist_ok=True)
        require(all(not p.is_symlink() and (p.is_dir() or p.is_file()) for p in staging.rglob('*')),
                'Unexpected recovery staging member')
        with tarfile.open(archive_path,'r:') as archive:
            archive.extractall(staging)
        verify_data(staging,archive_path)
        state.update(phase='retaining',failedEntries=sorted(p.name for p in source.iterdir()))
        save()
    if state['phase']=='retaining':
        retained.mkdir(mode=0o700,exist_ok=True)
        require({p.name for p in source.iterdir()} | {p.name for p in retained.iterdir()} == set(state['failedEntries']),
                'Failed data entries changed during recovery')
        for name in state['failedEntries']:
            current,previous=source/name,retained/name
            require(current.exists()!=previous.exists(), 'Failed data rename has ambiguous ownership')
            if current.exists():
                os.rename(current,previous)
        state['phase']='installing';save()
    if state['phase']=='installing':
        for name in sorted({PurePosixPath(member).parts[0] for member in members}):
            staged,current=staging/name,source/name
            require(staged.exists()!=current.exists(), 'Restored data rename has ambiguous ownership')
            if staged.exists():
                os.rename(staged,current)
        verify_data(source,archive_path)
        state['phase']='complete';save()
    require(retained.is_dir(), 'Retained failed data is missing')
    verify_data(source,archive_path)
    return str(retained)


def validate_database_identity(database):
    require(len(database) == 3
            and re.fullmatch(r'[A-Za-z0-9_-]+', database[0])
            and all(re.fullmatch(r'[A-Za-z0-9_]+', value) for value in database[1:]),
            'Explicit safe database identity required')
    return database


def capture(profile, root, manifest, origin, api):
    resources = inventory(profile, api)
    remote = api['remote']
    progress = json.loads((root/'deployment-progress.private.json').read_text())
    containers = {name:remote.inspect(name) for name in dict.fromkeys(
        [profile['frontend'],profile['backend'],profile['database'],profile['redis'],profile['minio']] + profile['writers'])}
    # Captured after writer drain; configured networking remains available even
    # when an observed running IP has disappeared.
    api['private_json'](root/'recovery-containers.private.json', containers)
    total = 0
    for resource in resources:
        source = Path(resource['mount']['Source'])
        total += sum(p.stat().st_size for p in source.rglob('*') if p.is_file() and not p.is_symlink())
    require(shutil.disk_usage(root).free > total + profile['minimumDockerRuntimeFreeBytes'], 'Insufficient checkpoint storage for all registered data volumes')
    for role in ('redis','minio'):
        remote.run(['docker','stop','--time','90',profile[role]], timeout=120)
        state = remote.inspect(profile[role])['State']
        require(not state['Running'] and state['ExitCode'] != 137, 'Data service did not stop gracefully: '+role)
    recovery = api['backup'](profile, root)
    table_checksums = checksums(profile, api)
    require(shutil.disk_usage(root).free > total + profile['minimumDockerRuntimeFreeBytes'], 'Insufficient checkpoint storage after database backup')
    for index, resource in enumerate(resources):
        resource['artifact'] = archive_data(Path(resource['mount']['Source']), root/('recovery-volume-'+str(index)+'.tar'))
    db = remote.sql(profile, 'SELECT DATABASE(),DEFAULT_CHARACTER_SET_NAME,DEFAULT_COLLATION_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME=DATABASE();').split('\t')
    validate_database_identity(db)
    staged = json.loads((root/'stage-verified.json').read_text())
    recovery.update(version=1, jobId=progress['jobId'], releaseTag=manifest['releaseTag'],
                    packageIdentity=package_identity(manifest), packageSha256=staged['archive']['archiveSha256'],
                    manifestSha256=staged['archive']['manifestSha256'], origin=origin, database=db,
                    databaseContainerId=containers[profile['database']]['Id'], resources=resources,
                    tableChecksums=table_checksums,
                    recoveryRuntimeConfigSha256=recovery_runtime_config_sha(profile,containers,True),
                    openRuntimeConfigSha256=recovery_runtime_config_sha(profile,containers,False),
                    containersSha256=file_sha(root/'recovery-containers.private.json'), capturedAt=now())
    api['private_json'](root/'recovery-record.private.json', recovery)
    for role in ('redis','minio'):
        api['docker']('POST','/containers/'+quote(profile[role])+'/start')
    return recovery


def read_bound(profile, payload, api, opening=False):
    root = api['directory'](profile, payload['releaseTag'])
    record = json.loads((root/'recovery-record.private.json').read_text())
    require(record.get('version') == 1 and record.get('jobId') == payload.get('originalJobId')
            and record['releaseTag'] == payload['releaseTag'] and record['packageSha256'] == payload.get('packageSha256')
            and record['origin']['fingerprint'] == payload.get('originFingerprint'), 'Complete recovery point does not belong to this deployment')
    database_snapshot_path(root, record)
    require(file_sha(root/'manifest.json') == record['manifestSha256']
            and file_sha(root/'release.tar') == record['packageSha256'], 'Original immutable release bytes changed')
    require(file_sha(root/'recovery-containers.private.json') == record['containersSha256'], 'Original container configuration changed')
    artifacts = [dict(path=record['path'],sha256=record['sha256'])] + [r['artifact'] for r in record['resources']]
    for item in artifacts:
        path = Path(item['path'])
        require(path.parent == root and path.is_file() and not path.is_symlink()
                and file_sha(path) == item['sha256'], 'Recovery artifact missing or changed')
    for resource in record['resources']:
        validate_archive(resource['artifact']['path'])
    require(api['remote'].inspect(profile['database'])['Id'] == record['databaseContainerId'], 'Database container identity changed')
    current_resources = inventory(profile, api)
    require(len(record['resources']) == len(current_resources), 'Recovery inventory changed')
    for old, current in zip(record['resources'], current_resources):
        require(old['containerId'] == current['containerId'] and old['mount'] == current['mount'], 'Recovery data mount identity changed')
    from intruoyi_rehearsal_agent import process_start_identity
    progress = json.loads((root/'deployment-progress.private.json').read_text())
    require(progress['jobId'] == record['jobId'] and process_start_identity(progress['pid']) != progress['processStart'],
            'Original deployment worker remains active or belongs to another task')
    require(opening or not (root/'business-opened.private.json').exists(),
            'Business was already opened; restoring this point could discard new business data')
    return root, record


def migration_status(profile, payload, api):
    root = api['directory'](profile, payload['releaseTag'])
    progress = json.loads((root/'deployment-progress.private.json').read_text())
    require(progress['jobId'] == payload['originalJobId'], 'Original deployment journal required')
    rows = api['remote'].sql(profile, "SELECT migration_id,sha256,status FROM infra_release_migration WHERE deleted=b'0' ORDER BY id;")
    records = {}
    for row in rows.splitlines():
        mid, digest, status = row.split('\t')
        records.setdefault(mid, []).append((digest,status))
    result = []
    for item in payload['plan']:
        if item['action'] != 'APPLY':
            continue
        states = records.get(item['migrationId'], [])
        require(all(digest == item['sha256'] for digest,_ in states), 'Migration checksum conflict')
        status = 'pending' if not states else 'applied' if all(s == 'APPLIED' for _,s in states) else 'failed-or-unknown'
        result.append(dict(migrationId=item['migrationId'], status=status))
    return dict(originalJobId=progress['jobId'], migrations=result,
                recoveryAvailable=(root/'recovery-record.private.json').is_file())


def restore_database(profile, record, api):
    """Replace all database objects, including removal of partially added DDL."""
    database,charset,collation=record['database']
    validate_database_identity([database, charset, collation])
    remote=api['remote']
    environment=dict(v.split('=',1) for v in remote.inspect(profile['database'])['Config']['Env'])
    require(environment.get('MYSQL_DATABASE')==database, 'Recovery database differs from registered container')
    auth='export MYSQL_PWD="$(cat "$MYSQL_ROOT_PASSWORD_FILE")"; ' if 'MYSQL_ROOT_PASSWORD_FILE' in environment else 'export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; '
    # The administrative connection deliberately selects no default database:
    # a failed earlier restore may have stopped between DROP and CREATE.
    remote.run(['docker','exec','-i',profile['database'],'sh','-c',auth+'exec mysql -uroot --default-character-set=utf8mb4'],
               data=('DROP DATABASE IF EXISTS `'+database+'`; CREATE DATABASE `'+database+'` CHARACTER SET '+charset+' COLLATE '+collation+';').encode(),timeout=120)
    restore_sql_snapshot(record['path'], ['docker','exec','-i',profile['database'],'sh','-c',
                         auth+'exec mysql -uroot --default-character-set=utf8mb4 "$MYSQL_DATABASE"'])
    require(checksums(profile,api) == record['tableChecksums'], 'Restored database data checksum differs')


def administrative_sql(profile, statement, api):
    """Recovery checks must still work after an interrupted DROP DATABASE."""
    environment=dict(value.split('=',1) for value in api['remote'].inspect(profile['database'])['Config']['Env'])
    require('MYSQL_ROOT_PASSWORD_FILE' in environment or environment.get('MYSQL_ROOT_PASSWORD'),
            'Root credential source not configured')
    auth='export MYSQL_PWD="$(cat "$MYSQL_ROOT_PASSWORD_FILE")"; ' if 'MYSQL_ROOT_PASSWORD_FILE' in environment else 'export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; '
    result=api['remote'].run(['docker','exec','-i',profile['database'],'sh','-c',
        auth+'exec mysql -uroot --batch --skip-column-names --default-character-set=utf8mb4'],data=statement.encode(),timeout=120)
    return result.decode('utf-8').strip()


def recover(profile, payload, api):
    import fcntl
    from intruoyi_rehearsal_agent import process_start_identity
    root = api['directory'](profile,payload['releaseTag'])
    attempt = payload['jobId']
    require(re.fullmatch('JOB-[a-f0-9]{10}',attempt), 'Valid recovery job ID required')
    descriptor = os.open(str(root/'recovery.lock'),os.O_WRONLY|os.O_CREAT,0o600)
    with os.fdopen(descriptor,'w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        root, record = read_bound(profile,payload,api)
        remote = api['remote']
        receipts = list(root.glob('recovery-JOB-*/receipt.private.json'))
        require(len(receipts)<=1, 'Multiple recovery attempts require explicit reconciliation')
        for path in receipts:
            prior = json.loads(path.read_text())
            require(prior['originalJobId']==record['jobId'] and prior['releaseTag']==record['releaseTag']
                    and prior['packageSha256']==record['packageSha256']
                    and prior['originFingerprint']==record['origin']['fingerprint']
                    and path.parent.name=='recovery-'+prior['jobId'], 'Prior recovery binding differs')
            require(process_start_identity(prior['pid']) != prior['processStart'], 'Previous recovery worker is still active')
            require(prior['phase'] not in ('opening','opened'), 'Recovery opening began; reconcile opening without restoring data again')
            if prior['phase'] == 'restored':
                api['health'](profile,record['origin']['releaseTag'],True)
                result = api['observe'](profile)
                require(result['releaseTag'] == record['origin']['releaseTag'] and result['maintenance'] is True
                        and result['schemaSha256'] == record['origin']['schemaSha256']
                        and result['ledgerSha256'] == record['origin']['ledgerSha256']
                        and result['images']==record['origin']['images'], 'Restored pending origin changed')
                require(actual_runtime_config_sha(profile,api,True)==record['recoveryRuntimeConfigSha256'],
                        'Restored pending container configuration changed')
                return dict(observation=result,receipt=prior)
        if receipts:
            folder=receipts[0].parent
            receipt=prior
            attempt=receipt['jobId']
            require(receipt['phase'] in ('stopping','restoring-database','restoring-data-volumes','restoring-program'),
                    'Unknown interrupted recovery phase')
        else:
            folder = root/('recovery-'+attempt)
            folder.mkdir(mode=0o700)
            receipt = dict(jobId=attempt,originalJobId=record['jobId'],releaseTag=record['releaseTag'],
                           packageSha256=record['packageSha256'],originFingerprint=record['origin']['fingerprint'],
                           phase='stopping',startedAt=now())
        receipt.setdefault('workers',[]).append(dict(jobId=payload['jobId'],startedAt=now(),phase=receipt['phase']))
        receipt.update(pid=os.getpid(),processStart=process_start_identity(os.getpid()),status='running')
        def save():
            api['resume_receipt'](folder/'receipt.private.json',receipt)
        save()
        try:
            require(administrative_sql(profile,'SELECT @@global.read_only,@@global.super_read_only;',api)=='0\t0',
                    'External database write fence active; recovery refused without changing protection')
            # A normal candidate backend means reopening started; do not erase
            # data on a possibly open target even if the local task is failed.
            origin_containers = json.loads((root/'recovery-containers.private.json').read_text())
            names = {info['Name'].lstrip('/'):info for info in [remote.inspect(x['Id']) for x in api['docker']('GET','/containers/json?all=1')]}
            for name in dict.fromkeys([profile['frontend'],profile['backend']]+profile['writers']):
                info=names.get(name)
                if info is None:
                    role=next((r for r in ('backend','frontend') if profile[r]==name),None)
                    require(receipt['phase']=='restoring-program' and role
                            and (folder/(role+'-replacement.private.json')).is_file(),
                            'Registered writer missing without a recovery replacement journal')
                    replacement=json.loads((folder/(role+'-replacement.private.json')).read_text())
                    retained=remote.inspect(replacement['retainedId'])
                    require(not retained['State']['Running'] and retained['Name']=='/'+name+'-failed-'+attempt,
                            'Interrupted replacement has an unconfirmed retained writer')
                    continue
                if name==profile['backend']:
                    if info['Id']!=origin_containers[name]['Id']:
                        require('INTRUOYI_RELEASE_MAINTENANCE=true' in info['Config']['Env'],
                                'Candidate already left maintenance; data restoration refused')
                    else:
                        require(not info['State']['Running'], 'Original writer restarted after failed migration')
                if name==profile['frontend']:
                    require(not info['State']['Running'], 'Public frontend must remain closed before recovery')
                if info['State']['Running']:
                    remote.run(['docker','stop','--time','90',info['Id']],timeout=120)
                state=remote.inspect(info['Id'])['State']
                require(not state['Running'] and state['ExitCode']!=137, 'Writer did not stop gracefully: '+name)
            if receipt['phase']!='restoring-program':
                for role in ('redis','minio'):
                    remote.run(['docker','stop','--time','90',profile[role]],timeout=120)
                    state = remote.inspect(profile[role])['State']
                    require(not state['Running'] and state['ExitCode'] != 137, 'Data service did not stop gracefully: '+role)
            database=record['database'][0]
            require(re.fullmatch('[A-Za-z0-9_]+',database), 'Unsafe recovery database identity')
            require(administrative_sql(profile,"SELECT COUNT(*) FROM information_schema.INNODB_TRX; SELECT COUNT(*) FROM information_schema.PROCESSLIST WHERE ID<>CONNECTION_ID() AND DB='"+database+"' AND COMMAND<>'Sleep';",api)=='0\n0',
                    'Active database statements or transactions prevent recovery')
            # Preserve the partial migration data and original FAILED/RUNNING
            # ledger before restoring the old schema. This is not a new origin.
            if receipt['phase']=='stopping':
                acceptance = names.get(profile['acceptanceFrontend'])
                if acceptance:
                    require(acceptance['Config'].get('Labels',{}).get('intruoyi.release.acceptance') == 'true', 'Unowned acceptance resource')
                    remote.run(['docker','stop','--time','30',acceptance['Id']])
                    api['docker']('POST','/containers/'+acceptance['Id']+'/rename?name='+quote(profile['acceptanceFrontend']+'-failed-'+attempt))
                # A terminated dump is retained separately. Only a completed,
                # hashed dump authorizes the first destructive restore step.
                failed_folder=folder/('failed-database-'+str(len(receipt['workers'])))
                failed_folder.mkdir(mode=0o700)
                receipt['failedDatabase'] = api['backup'](profile, failed_folder)
                receipt['phase']='restoring-database';save()
            failed=receipt['failedDatabase']
            require(file_sha(failed['path'])==failed['sha256'], 'Retained failed database snapshot changed')
            if receipt['phase']=='restoring-database':
                restore_database(profile,record,api)
                receipt['phase']='restoring-data-volumes';save()
            require(checksums(profile,api)==record['tableChecksums'], 'Restored database changed before recovery completion')
            if receipt['phase']=='restoring-data-volumes':
                receipt['retainedData']=[]
                for resource in record['resources']:
                    retained=restore_data(Path(resource['mount']['Source']),resource['artifact']['path'],attempt)
                    receipt['retainedData'].append(retained);save()
                receipt['phase']='restoring-program';save()
            for role in ('redis','minio'):
                if not remote.inspect(profile[role])['State']['Running']:
                    api['docker']('POST','/containers/'+quote(profile[role])+'/start')
            candidate_manifest=json.loads((root/'manifest.json').read_text())
            for role in ('backend','frontend'):
                restore_container(profile,role,origin_containers[profile[role]],attempt,api,maintenance=role=='backend',journal=folder,
                                 candidate_image=candidate_manifest['images'][role]['id'],recovery_record=record)
            api['docker']('POST','/containers/'+quote(profile['backend'])+'/start')
            api['acceptance_frontend'](profile,folder,resume=True)
            api['health'](profile,record['origin']['releaseTag'],True)
            observed=api['observe'](profile)
            require(observed['images']==record['origin']['images'] and observed['schemaSha256']==record['origin']['schemaSha256']
                    and observed['ledgerSha256']==record['origin']['ledgerSha256'], 'Recovered program/schema/ledger differs from origin')
            require(actual_runtime_config_sha(profile,api,True)==record['recoveryRuntimeConfigSha256'],
                    'Recovered container runtime configuration differs from the registered origin')
            receipt.update(phase='restored',status='succeeded',finishedAt=now());save()
            return dict(observation=observed,receipt=receipt)
        except Exception as error:
            receipt.update(status='failed',errorCategory=type(error).__name__,finishedAt=now());save()
            raise


def restore_container(profile,role,original,attempt,api,maintenance,journal,candidate_image=None,recovery_record=None,
                      allowed_opening_attempt=None):
    name=profile[role]
    suffix='-opening' if role=='backend' and not maintenance else ''
    path=journal/(role+suffix+'-replacement.private.json')
    containers=api['docker']('GET','/containers/json?all=1')
    named=[item for item in containers if '/'+name in item.get('Names',[])]
    require(len(named)<=1, 'Ambiguous recovery container name')
    labels={'intruoyi.recovery.attempt':attempt,'intruoyi.recovery.role':role}
    if path.exists():
        record=json.loads(path.read_text())
        require(record['originalId']==original['Id'] and record['maintenance']==maintenance and record['name']==name,
                'Recovery replacement journal binding changed')
    else:
        require(len(named)==1, 'Registered container missing before recovery replacement')
        current=api['remote'].inspect(named[0]['Id'])
        require(not current['State']['Running'], 'Container must be stopped before recovery replacement')
        if current['Id']!=original['Id'] and current['Image']!=candidate_image:
            current_labels=current['Config'].get('Labels',{})
            prior_attempt=current_labels.get('intruoyi.recovery.attempt')
            prior_role=current_labels.get('intruoyi.recovery.role')
            prior_path=journal.parent/('recovery-'+str(prior_attempt))/'receipt.private.json'
            require(recovery_record and prior_role==role and re.fullmatch('JOB-[a-f0-9]{10}',prior_attempt or '')
                    and prior_path.is_file(), 'Registered container is not the original, candidate, or a recorded recovery replacement')
            prior=json.loads(prior_path.read_text())
            phase_matches=prior.get('phase') not in ('opening','opened') or (
                prior_attempt==allowed_opening_attempt and prior.get('phase')=='opening'
                and prior.get('openingJobId')==attempt)
            require(prior.get('jobId')==prior_attempt and prior.get('originalJobId')==recovery_record['jobId']
                    and prior.get('releaseTag')==recovery_record['releaseTag']
                    and prior.get('packageSha256')==recovery_record['packageSha256']
                    and prior.get('originFingerprint')==recovery_record['origin']['fingerprint']
                    and prior.get('status') in ('failed','succeeded') and phase_matches
                    and current['Image']==original['Image'], 'Prior recovery container ownership or origin binding differs')
        record=dict(originalId=original['Id'],maintenance=maintenance,name=name,retainedId=current['Id'],retainedImage=current['Image'])
        api['private_json'](path,record)
    if named and named[0]['Id']!=record['retainedId']:
        current=api['remote'].inspect(named[0]['Id'])
        require(current['Image']==original['Image'] and all(current['Config'].get('Labels',{}).get(k)==v for k,v in labels.items()),
                'Replacement name is owned by another operation')
        created={'Id':current['Id']}
    else:
        created=None
    retained=api['remote'].inspect(record['retainedId'])
    require(not retained['State']['Running'] and retained['Image']==record['retainedImage'],
            'Retained container restarted or its image identity changed during recovery')
    if retained['Name']=='/'+name:
        api['docker']('POST','/containers/'+retained['Id']+'/rename?name='+quote(name+'-failed-'+attempt))
    else:
        require(retained['Name']=='/'+name+'-failed-'+attempt, 'Retained recovery container identity changed')
    for network in retained['NetworkSettings']['Networks']:
        if network not in ('host','none'):
            api['docker']('POST','/networks/'+quote(network)+'/disconnect',{'Container':retained['Id'],'Force':True})
    if created is None:
        config=api['clone_config'](original,original['Image'],True if maintenance else None)
        config['Labels']=dict(config.get('Labels') or {},**labels)
        created=api['docker']('POST','/containers/create?name='+quote(name),config)
    # Copy the original frontend nginx file when it lived in the container layer.
    if role=='frontend' and not any(m['Destination']=='/etc/nginx/conf.d/default.conf' for m in original['Mounts']):
        content=api['remote'].run(['docker','cp',original['Id']+':/etc/nginx/conf.d/default.conf','-'])
        api['remote'].run(['docker','cp','-',created['Id']+':/etc/nginx/conf.d/'],data=content)
    return created['Id']


def accept(profile,payload,api):
    import fcntl
    root=api['directory'](profile,payload['releaseTag'])
    descriptor=os.open(str(root/'recovery.lock'),os.O_WRONLY|os.O_CREAT,0o600)
    with os.fdopen(descriptor,'w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        root,record=read_bound(profile,payload,api,opening=True)
        require(re.fullmatch('JOB-[a-f0-9]{10}',payload['recoveryJobId']), 'Bound recovery job ID required')
        path=root/('recovery-'+payload['recoveryJobId'])/'receipt.private.json'
        receipt=json.loads(path.read_text())
        require(receipt['phase'] in ('restored','opening','opened') and receipt['status']=='succeeded', 'Completed recovery required')
        if receipt['phase']=='restored':
            api['health'](profile,record['origin']['releaseTag'],True)
            receipt.update(phase='opening',openingJobId=payload['jobId']);api['resume_receipt'](path,receipt)
            api['remote'].run(['docker','stop','--time','90',profile['backend']],timeout=120)
        if receipt['phase']=='opening' and not receipt.get('openingBackendId'):
            names=api['docker']('GET','/containers/json?all=1')
            named=[item for item in names if '/'+profile['backend'] in item.get('Names',[])]
            if named:
                current=api['remote'].inspect(named[0]['Id'])
                if 'INTRUOYI_RELEASE_MAINTENANCE=true' in current['Config']['Env'] and current['State']['Running']:
                    api['remote'].run(['docker','stop','--time','90',current['Id']],timeout=120)
            containers=json.loads((root/'recovery-containers.private.json').read_text())
            candidate_manifest=json.loads((root/'manifest.json').read_text())
            restored_id=restore_container(profile,'backend',containers[profile['backend']],receipt['openingJobId'],api,
                maintenance=False,journal=path.parent,candidate_image=candidate_manifest['images']['backend']['id'],
                recovery_record=record,allowed_opening_attempt=payload['recoveryJobId'])
            receipt['openingBackendId']=restored_id;api['resume_receipt'](path,receipt)
        backend=api['remote'].inspect(profile['backend'])
        require(receipt.get('openingBackendId')==backend['Id'] and backend['Image']==record['origin']['images']['backend']
                and 'INTRUOYI_RELEASE_MAINTENANCE=true' not in backend['Config']['Env'], 'Recovery opening backend identity is unconfirmed')
        if not backend['State']['Running']:
            api['docker']('POST','/containers/'+backend['Id']+'/start')
        if receipt['phase']=='opened':
            api['health'](profile,record['origin']['releaseTag'],False)
            result=api['observe'](profile)
            require(result['images']==record['origin']['images'] and result['schemaSha256']==record['origin']['schemaSha256']
                    and result['ledgerSha256']==record['origin']['ledgerSha256'], 'Opened recovery origin changed')
            require(actual_runtime_config_sha(profile,api,False)==record['openRuntimeConfigSha256'],
                    'Opened recovery container runtime configuration differs from the registered origin')
            return dict(observation=result,receipt=dict(receipt,confirmedByJobId=payload['jobId']))
        opened_path=root/'business-opened.private.json'
        if opened_path.exists():
            mark=json.loads(opened_path.read_text())
            require(mark.get('kind')=='recovered-origin' and mark.get('jobId')==receipt['openingJobId'], 'Business opening marker belongs to another operation')
        else:
            api['health'](profile,record['origin']['releaseTag'],False,through_acceptance=True)
            api['private_json'](opened_path,dict(kind='recovered-origin',jobId=receipt['openingJobId'],time=now()))
        for name in profile['writers']+[profile['frontend']]:
            if not api['remote'].inspect(name)['State']['Running']:
                api['docker']('POST','/containers/'+quote(name)+'/start')
        api['health'](profile,record['origin']['releaseTag'],False)
        result=api['observe'](profile)
        require(result['images']==record['origin']['images'] and result['schemaSha256']==record['origin']['schemaSha256']
                and result['ledgerSha256']==record['origin']['ledgerSha256'] and result['maintenance'] is False,
                'Opened recovery identity differs')
        require(actual_runtime_config_sha(profile,api,False)==record['openRuntimeConfigSha256'],
                'Opened recovery container runtime configuration differs from the registered origin')
        containers=api['docker']('GET','/containers/json?all=1')
        active=[item for item in containers if '/'+profile['acceptanceFrontend'] in item.get('Names',[])]
        retained_name=profile['acceptanceFrontend']+'-recovered-'+receipt['jobId']
        if active:
            acceptance=api['remote'].inspect(active[0]['Id'])
            require(acceptance['Config'].get('Labels',{}).get('intruoyi.release.acceptance')=='true', 'Unowned recovery acceptance resource')
            api['remote'].run(['docker','stop','--time','30',acceptance['Id']])
            api['docker']('POST','/containers/'+acceptance['Id']+'/rename?name='+quote(retained_name))
        else:
            require(any('/'+retained_name in item.get('Names',[]) for item in containers), 'Recovery acceptance cleanup cannot be confirmed')
        receipt.update(phase='opened',openingStatus='succeeded',openedAt=now());api['resume_receipt'](path,receipt)
        return dict(observation=result,receipt=dict(receipt,confirmedByJobId=payload['jobId']))
