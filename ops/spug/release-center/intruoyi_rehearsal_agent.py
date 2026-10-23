"""Python 3.6 remote implementation for owned, internal-network full-data copies."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import socket
import subprocess
import time
import tarfile
import posixpath
from urllib.parse import urlsplit
from urllib.request import urlopen

LABEL = 'intruoyi.release.rehearsal'
PREFIX = 'intruoyi-release-rehearsal'


def source_active_profiles(info):
    env = dict(value.split('=', 1) for value in info['Config']['Env'])
    values = []
    if env.get('SPRING_PROFILES_ACTIVE'):
        values.append(env['SPRING_PROFILES_ACTIVE'])
    for token in (info['Config'].get('Cmd') or []) + shlex.split(env.get('ARGS', '')):
        if token.startswith('--spring.profiles.active='):
            values.append(token.split('=', 1)[1])
    if len(set(values)) != 1 or not re.fullmatch(r'[A-Za-z0-9_,.-]+', values[0]):
        raise ValueError('One explicit, unambiguous source Spring profile is required')
    return values[0]


def source_backend_startup(info, remote, container):
    source_active_profiles(info)
    env = dict(value.split('=', 1) for value in info['Config']['Env'])
    args = shlex.split(env.get('ARGS', ''))
    if not args or any(not arg.startswith('--') or '=' not in arg for arg in args):
        raise ValueError('Source backend requires explicit property arguments')
    locations = [arg.split('=', 1)[1] for arg in args if arg.startswith('--spring.config.additional-location=')]
    if len(locations) != 1 or not locations[0].startswith('file:'):
        raise ValueError('One mounted source property file is required')
    path = locations[0][5:]
    if not path.endswith('.properties') or not any(m['Destination'] == path and m['Type'] == 'bind' for m in info['Mounts']):
        raise ValueError('Source property file is not an inspected bind mount')
    properties = remote.run(['docker', 'exec', container, 'cat', path]).decode('utf-8')
    return {'arguments': [arg for arg in args if not arg.startswith(('--spring.config.additional-location=', '--spring.profiles.active='))],
            'properties': properties}


def isolated_nginx_config(content, source_port, backend_upstreams, backend, minio_upstreams, minio):
    def listener(match):
        endpoint = match.group(2)
        port = endpoint.rsplit(':', 1)[-1]
        if not port.isdigit():
            raise ValueError('Unsupported source nginx listener')
        return match.group(1) + ('80' if int(port) == source_port else port)
    content, count = re.subn(r'(\blisten\s+)([^\s;]+)', listener, content)
    if not count:
        raise ValueError('Source nginx listeners missing')
    for upstreams, target in ((backend_upstreams, backend), (minio_upstreams, minio)):
        for old in sorted(upstreams, key=len, reverse=True):
            content = content.replace('http://' + old + ':', 'http://' + target + ':')
    return content


def apply_checked_batches(sql, statements, label, batch_size=100):
    batch, size = [], 0
    batches = []
    for statement in statements:
        statement_size = len(statement.encode('utf-8'))
        if statement_size > 4 * 1024 * 1024:
            raise ValueError(label + ' update exceeds the bounded SQL batch size')
        if batch and (len(batch) >= batch_size or size + statement_size > 4 * 1024 * 1024):
            batches.append(batch)
            batch, size = [], 0
        batch.append(statement)
        size += statement_size
    if batch:
        batches.append(batch)
    for batch in batches:
        result = sql('START TRANSACTION; ' + ' '.join(batch) + ' COMMIT;')
        if result.splitlines() != ['1'] * len(batch):
            raise ValueError(label + ' batch did not update each frozen row exactly once')


def process_start_identity(pid):
    try:
        fields = Path('/proc/%d/stat' % pid).read_text().rsplit(')',1)[1].split()
        return Path('/proc/sys/kernel/random/boot_id').read_text().strip() + ':' + fields[19]
    except (IOError, IndexError, OSError):
        return None



TRANSFER_BLOCK_BYTES = 4 * 1024 * 1024


def chunk_records(path):
    records = []
    with path.open('rb') as stream:
        offset = 0
        while True:
            content = stream.read(TRANSFER_BLOCK_BYTES)
            if not content:
                break
            records.append({'sha256':hashlib.sha256(content).hexdigest(), 'bytes':len(content), 'offset':offset})
            offset += len(content)
    return records


def transfer_artifact_path(profile, value):
    path = Path(value)
    root = Path(profile['stagingRoot']) / 'rehearsal-seed'
    if (not path.is_absolute() or path.parent.parent != root
            or not re.fullmatch(r'\d{4}(-\d{2}){5}',path.parent.name)
            or path.name not in ('minio.tar','recovery.sql','redis.jsonl','nginx.conf','historical-release-info.json','origin-images.tar','backend-startup.private.json')):
        raise ValueError('Transfer path is outside the registered rehearsal seed')
    marker = path.parent / 'rehearsal-owned.json'
    if json.loads(marker.read_text()).get('owner') != PREFIX or path.is_symlink():
        raise ValueError('Transfer seed ownership cannot be proved')
    return path


def transfer_dispatch(p, api):
    require, profile = api['require'], p['profile']
    action = p['action']
    require(re.fullmatch('JOB-[a-f0-9]{10}',p.get('jobId','')), 'Valid transfer job identity required')
    if action == 'rehearsal-local-copy':
        source = transfer_artifact_path(p['sourceProfile'], p['sourcePath'])
        target = transfer_artifact_path(profile, p['destinationPath'])
        require(p['sourceProfile']['host'] == profile['host'] and source != target, 'Local transfer requires distinct paths on the same host')
        import shutil
        fd = os.open(str(target),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        with source.open('rb') as reader, os.fdopen(fd,'wb') as writer:
            shutil.copyfileobj(reader,writer,TRANSFER_BLOCK_BYTES)
        require(api['file_sha'](target)==p['sha256'], 'Local snapshot copy checksum differs')
        return {'bytes':target.stat().st_size,'verified':True,'transport':'same-host-copy'}
    if action == 'rehearsal-transfer-index':
        source = transfer_artifact_path(profile,p['sourcePath'])
        require(source.name=='minio.tar' and api['file_sha'](source)==p['sha256'], 'Snapshot differs before incremental transfer')
        return {'chunks':chunk_records(source),'bytes':source.stat().st_size,'sha256':p['sha256']}
    if action == 'rehearsal-transfer-sender':
        source=transfer_artifact_path(profile,p['sourcePath'])
        require(source.name=='minio.tar','Only snapshot blocks may be streamed')
        script=source.parent/('send-'+p['jobId']+'.py')
        code="import sys\nfrom pathlib import Path\nitems="+repr(p['chunks'])+"\nwith Path("+repr(str(source))+").open('rb') as stream:\n for item in items:\n  stream.seek(item['offset'])\n  data=stream.read(item['bytes'])\n  if len(data)!=item['bytes']: raise RuntimeError('Snapshot truncated')\n  sys.stdout.buffer.write(data)\n"
        with script.open('x',encoding='utf-8') as out:out.write(code)
        script.chmod(0o600)
        return {'script':str(script)}
    target = transfer_artifact_path(profile,p['destinationPath'])
    require(target.name=='minio.tar', 'Incremental transfer is restricted to the complete media snapshot')
    cache = Path(profile['stagingRoot']) / 'rehearsal-transfer-cache'
    cache.mkdir(mode=0o700,parents=True,exist_ok=True)
    require(not cache.is_symlink(), 'Transfer cache must be a real directory')
    chunks = p['chunks']
    offset = 0
    for item in chunks:
        require(re.fullmatch('[a-f0-9]{64}',item['sha256']) and isinstance(item['bytes'],int)
                and 0<item['bytes']<=TRANSFER_BLOCK_BYTES and item['offset']==offset, 'Invalid ordered snapshot chunk')
        offset += item['bytes']
    require(chunks and offset==p['bytes'], 'Complete snapshot chunk inventory required')
    if action == 'rehearsal-transfer-plan':
        missing=[]
        for item in chunks:
            path=cache/item['sha256']
            if path.exists():
                require(not path.is_symlink() and path.is_file() and path.stat().st_size==item['bytes']
                        and api['file_sha'](path)==item['sha256'], 'Existing snapshot cache is corrupt; no reuse permitted')
            elif item['sha256'] not in missing:
                missing.append(item['sha256'])
        required=[next(item for item in chunks if item['sha256']==digest) for digest in missing]
        receiver=target.parent/('receive-'+p['jobId']+'.py')
        code="import sys,os,hashlib\nitems="+repr(required)+"\nroot="+repr(str(cache))+"\njob="+repr(p['jobId'])+"\nfor item in items:\n path=root+'/'+item['sha256']+'.'+job+'.partial'\n fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)\n data=sys.stdin.buffer.read(item['bytes'])\n with os.fdopen(fd,'wb') as out: out.write(data)\n if len(data)!=item['bytes'] or hashlib.sha256(data).hexdigest()!=item['sha256']: raise RuntimeError('Snapshot chunk transfer failed')\nif sys.stdin.buffer.read(1): raise RuntimeError('Unexpected snapshot bytes')\n"
        with receiver.open('x',encoding='utf-8') as out:out.write(code)
        receiver.chmod(0o600)
        return {'missing':required,'receiver':str(receiver)}
    require(action=='rehearsal-transfer-assemble','Unknown transfer action')
    # Uploaded files are private partials until independently hashed and sealed.
    for item in chunks:
        path=cache/item['sha256']; partial=cache/(item['sha256']+'.'+p['jobId']+'.partial')
        if not path.exists():
            require(partial.is_file() and not partial.is_symlink() and partial.stat().st_size==item['bytes']
                    and api['file_sha'](partial)==item['sha256'],'Transferred snapshot block is missing or corrupt')
            partial.rename(path)
    digest=hashlib.sha256()
    fd=os.open(str(target),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    with os.fdopen(fd,'wb') as output:
        for item in chunks:
            path=cache/item['sha256']
            require(not path.is_symlink() and path.stat().st_size==item['bytes'],'Snapshot cache identity changed')
            data=path.read_bytes()
            require(hashlib.sha256(data).hexdigest()==item['sha256'],'Snapshot cache content changed')
            output.write(data);digest.update(data)
    require(digest.hexdigest()==p['sha256'],'Assembled complete snapshot checksum mismatch')
    return {'verified':True,'bytes':offset,'sha256':digest.hexdigest()}

def redis_config_password(content):
    """Read only the explicitly registered native Redis requirepass format."""
    matches = []
    for line in content.splitlines():
        try:
            fields = shlex.split(line, comments=True, posix=True)
        except ValueError:
            raise ValueError('Registered Redis configuration syntax is invalid')
        if fields and fields[0].lower() == 'requirepass':
            if len(fields) != 2 or not fields[1]:
                raise ValueError('Registered Redis requirepass must have one nonempty value')
            matches.append(fields[1])
    if len(matches) != 1:
        raise ValueError('Registered Redis configuration must define requirepass exactly once')
    return matches[0]


def source_redis_auth(profile, remote):
    options = [profile.get('redisNoAuth') is True,
               bool(profile.get('redisPasswordEnv')), bool(profile.get('redisPasswordConfigFile'))]
    if sum(options) != 1:
        raise ValueError('Exactly one explicit Redis authentication source is required')
    if options[0]:
        return {'noauth': True}
    if options[1]:
        env = dict(v.split('=', 1) for v in remote.inspect(profile['redis'])['Config']['Env'])
        if not env.get(profile['redisPasswordEnv']):
            raise ValueError('Registered Redis password environment source is missing')
        return {'password': env[profile['redisPasswordEnv']]}
    path = profile['redisPasswordConfigFile']
    if not isinstance(path, str) or not path.startswith('/') or '..' in Path(path).parts:
        raise ValueError('Explicit absolute Redis configuration path required')
    content = remote.run(['docker', 'exec', profile['redis'], 'cat', path]).decode('utf-8')
    return {'password': redis_config_password(content)}


def isolated_backend_environment(profile, source, minio_password):
    properties = source['edhrProperties']
    required = {'EDHR_S3_BUCKET', 'EDHR_S3_REGION', 'EDHR_S3_RETENTION_MODE', 'EDHR_S3_RETAIN_UNTIL_DAYS', 'EDHR_S3_REQUIRE_LEGAL_HOLD'}
    if not required <= set(properties) or properties['EDHR_S3_BUCKET'] not in source['minioBuckets']:
        raise ValueError('Verified EDHR settings and owned bucket are required')
    if set(properties) - (required | {'EDHR_S3_ENABLE_PATH_STYLE_ACCESS'}):
        raise ValueError('Unregistered EDHR property')
    result = dict(properties, INTRUOYI_RELEASE_MAINTENANCE='false',
                  EDHR_S3_ENDPOINT='http://' + profile['minio'] + ':9000',
                  EDHR_S3_DOMAIN=profile['isolatedMinioPublicUrl'] + '/' + properties['EDHR_S3_BUCKET'],
                  EDHR_S3_ACCESS_KEY='release-isolation', EDHR_S3_SECRET_KEY=minio_password)
    return [key + '=' + str(value) for key, value in sorted(result.items())]


def local_media_prefixes(profile):
    hosts = profile['minioLocalEndpointHosts']
    buckets = profile['minioBuckets']
    return ['http://' + host + ':9000/' + bucket + '/' for host in hosts for bucket in buckets]


def rewrite_media_urls(value, profile, destination):
    """Change only registered local origins, preserving bucket/object bytes exactly."""
    if not isinstance(value, str):
        raise ValueError('Media URL conversion requires text')
    destination_url = urlsplit(destination)
    if destination_url.scheme != 'http' or not destination_url.hostname or destination_url.port != 39082 or destination_url.path:
        raise ValueError('Explicit isolated MinIO origin on port39082 required')
    hosts = '|'.join(re.escape(host) for host in profile['minioLocalEndpointHosts'])
    buckets = '|'.join(re.escape(bucket) for bucket in profile['minioBuckets'])
    plain = re.compile(r'http://(?:' + hosts + r'):9000/(?P<bucket>' + buckets + r')(?=/|[?\#]|$)', re.I)
    # JSON and editor content may retain JSON-style slash escapes inside text columns.
    escaped = re.compile(r'http:\\/\\/(?:' + hosts + r'):9000\\/(?P<bucket>' + buckets + r')(?=\\/|[?\#]|$)', re.I)
    for pattern in (plain, escaped):
        for match in pattern.finditer(value):
            boundary = re.search(r'''[\s"'<>]''', value[match.end():])
            end = len(value) if boundary is None else match.end() + boundary.start()
            if re.search(r'(?:X-Amz-Signature|X-Amz-Credential|AWSAccessKeyId|Signature)=', value[match.start():end], re.I):
                raise ValueError('Stored signed local media URL needs explicit re-signing; origin rewrite refused')
    value, ordinary_count = plain.subn(lambda match: destination + '/' + match.group('bucket'), value)
    value, escaped_count = escaped.subn(lambda match: (destination + '/' + match.group('bucket')).replace('/', '\\/'), value)
    return value, ordinary_count + escaped_count


def readonly_media_inventory(profile, api):
    """One aggregate scan per real table; return column/count metadata only."""
    r, require = api['remote'], api['require']
    tables = set(r.sql(profile, 'SHOW TABLES;').splitlines())
    metadata = r.sql(profile, "SELECT TABLE_NAME,COLUMN_NAME,DATA_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND DATA_TYPE IN ('char','varchar','text','tinytext','mediumtext','longtext','json') ORDER BY TABLE_NAME,ORDINAL_POSITION;")
    grouped = {}
    for row in metadata.splitlines():
        table, column, datatype = row.split('\t')
        require(table in tables and re.fullmatch('[A-Za-z0-9_]+', table) and re.fullmatch('[A-Za-z0-9_]+', column), 'Unsafe actual schema identifier')
        grouped.setdefault(table, []).append((column, datatype))
    prefixes = local_media_prefixes(profile)
    prefixes += [value.replace('/', '\\/') for value in prefixes]
    literal = lambda value: 'CONVERT(0x' + value.encode('utf-8').hex() + ' USING utf8mb4)'
    indexes = r.sql(profile, "SELECT TABLE_NAME,COLUMN_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND INDEX_NAME='PRIMARY' ORDER BY TABLE_NAME,SEQ_IN_INDEX;")
    primary_keys = {}
    for row in indexes.splitlines():
        table, column = row.split('\t')
        primary_keys.setdefault(table, []).append(column)
    matches = []
    scanned = 0
    # DESCRIBE each table before reading its actual business columns.
    for table, columns in sorted(grouped.items()):
        r.sql(profile, 'DESCRIBE `' + table + '`;')
        predicates = [' OR '.join('LOCATE(' + literal(prefix) + ',`' + column + '`)>0' for prefix in prefixes) for column, _ in columns]
        expressions = ['COALESCE(SUM(CASE WHEN ' + predicate + ' THEN 1 ELSE 0 END),0)' for predicate in predicates]
        counts = r.sql(profile, 'SET SESSION TRANSACTION READ ONLY; START TRANSACTION READ ONLY; SELECT ' + ','.join(expressions) + ' FROM `' + table + '`; ROLLBACK;').split('\t')
        require(len(counts) == len(columns) and all(value.isdigit() for value in counts), 'Malformed readonly media aggregate')
        for (column, datatype), count in zip(columns, counts):
            if int(count):
                matches.append({'table': table, 'column': column, 'dataType': datatype, 'matchingRows': int(count), 'primaryKey': primary_keys.get(table, [])})
        scanned += len(columns)
    return {'tablesScanned': len(grouped), 'columnsScanned': scanned, 'matches': matches,
            'prefixesSha256': api['sha'](prefixes), 'mutations': False}


def isolate_stored_media_urls(profile, source, api):
    """Only explicitly inventoried columns in the labelled isolated copy may change."""
    require, r = api['require'], api['remote']
    require(profile.get('environment') == 'rehearsal' and profile['database'].startswith(PREFIX + '-'), 'Stored media conversion is restricted to isolated DB')
    require(r.inspect(profile['database'])['Config'].get('Labels', {}).get(LABEL) == PREFIX, 'Isolated DB ownership label missing')
    registered = source.get('mediaUrlColumns')
    require(isinstance(registered, list) and registered, 'Explicit inventoried media URL columns required')
    indexed = {(entry['table'], entry['column']): entry for entry in registered}
    require(len(indexed) == len(registered), 'Duplicate registered media URL column')
    inspection_profile = dict(profile, minioLocalEndpointHosts=source['minioLocalEndpointHosts'], minioBuckets=source['minioBuckets'])
    actual = readonly_media_inventory(inspection_profile, api)
    require({(entry['table'], entry['column']) for entry in actual['matches']} <= set(indexed), 'New unregistered local-media URL column found in copied DB; no URL changed')
    evidence = []
    prefixes = local_media_prefixes(source)
    prefixes += [value.replace('/', '\\/') for value in prefixes]
    literal = lambda value: 'CONVERT(0x' + value.encode('utf-8').hex() + ' USING utf8mb4)'
    for hit in actual['matches']:
        table, column = hit['table'], hit['column']
        registration = indexed[(table, column)]
        require(hit['dataType'] == registration['dataType'] and hit['primaryKey'] == registration['primaryKey'] and hit['primaryKey'], 'Media column schema/primary key differs from real source inventory')
        keys = hit['primaryKey']
        require(all(re.fullmatch('[A-Za-z0-9_]+', value) for value in [table, column] + keys), 'Unsafe inventoried media identifier')
        predicate = ' OR '.join('LOCATE(' + literal(prefix) + ',`' + column + '`)>0' for prefix in prefixes)
        # Each iteration removes matching origins; LIMIT bounds private data in memory.
        updated, replacements, row_evidence, pending_updates = 0, 0, [], []
        while True:
            query = 'SELECT ' + ','.join('HEX(CAST(`' + key + '` AS CHAR))' for key in keys) + ',HEX(`' + column + '`) FROM `' + table + '` WHERE ' + predicate + ' ORDER BY ' + ','.join('`' + key + '`' for key in keys) + ' LIMIT 100;'
            rows = r.sql(profile, query)
            if not rows:
                break
            for row in rows.splitlines():
                fields = row.split('\t')
                require(len(fields) == len(keys) + 1, 'Malformed private media row')
                before = bytes.fromhex(fields[-1]).decode('utf-8')
                after, count = rewrite_media_urls(before, source, profile['isolatedMinioPublicUrl'])
                require(count > 0, 'Inventoried media origin could not be converted; copied data remains private')
                if hit['dataType'] == 'json':
                    json.loads(after)
                identity = ' AND '.join('`' + key + '`=CONVERT(0x' + value + ' USING utf8mb4) AND CAST(`' + key + '` AS BINARY)=0x' + value
                                        for key, value in zip(keys, fields[:-1]))
                statement = 'UPDATE `' + table + '` SET `' + column + '`=' + literal(after) + ' WHERE ' + identity + ' AND HEX(`' + column + '`)=' + "'" + fields[-1] + "'; SELECT ROW_COUNT();"
                pending_updates.append(statement)
                row_evidence.append([api['sha'](fields[:-1]), hashlib.sha256(before.encode()).hexdigest(), hashlib.sha256(after.encode()).hexdigest()])
                updated += 1
                replacements += count
            apply_checked_batches(lambda query:r.sql(profile, query), pending_updates, 'Isolated media')
            pending_updates = []
        require(updated == hit['matchingRows'], 'Isolated media conversion row count differs from frozen-copy inventory')
        evidence.append({'table': table, 'column': column, 'rows': updated, 'urlReplacements': replacements, 'rowEvidenceSha256': api['sha'](row_evidence)})
    return {'columns': evidence, 'sourceInventorySha256': api['sha'](registered), 'remainingRegisteredOrigins': 0}


def dispatch(p, api):
    r = api['remote']
    require, blocked = api['require'], api['RuntimeBlocked']
    profile, action = p['profile'], p['action']
    if action in ('rehearsal-local-copy','rehearsal-transfer-index','rehearsal-transfer-plan','rehearsal-transfer-assemble','rehearsal-transfer-sender'):
        return transfer_dispatch(p,api)
    if action == 'rehearsal-media-inventory':
        return readonly_media_inventory(profile, api)
    if action == 'rehearsal-daemon-identity':
        daemon_id = r.run(['docker', 'info', '--format', '{{.ID}}']).decode('ascii').strip()
        require(re.fullmatch('[A-Za-z0-9:-]+', daemon_id), 'Docker daemon identity is unavailable')
        return {'daemonId': daemon_id}
    if action == 'rehearsal-runtime-images':
        images = {role:r.inspect(profile[role])['Image'] for role in ('backend','frontend','database','redis','minio')}
        return {'images':images}
    if action == 'rehearsal-check-images':
        images = p.get('images')
        require(isinstance(images,dict) and set(images)=={'backend','frontend','database','redis','minio'}, 'Five source image identities required')
        for image in set(images.values()):
            require(re.fullmatch('sha256:[a-f0-9]{64}',image), 'Invalid source image identity')
            require(r.run(['docker','image','inspect','--format','{{.Id}}',image]).decode().strip()==image, 'Required source image missing from target daemon')
        return {'images':images}
    if action == 'rehearsal-job-progress':
        job_id, phase = p.get('jobId'), p.get('phase')
        require(isinstance(job_id,str) and re.fullmatch('JOB-[a-f0-9]{10}',job_id), 'Valid rehearsal job ID required')
        require(phase in ('capture-starting','capture-complete','restore-starting','completed','failed'), 'Known rehearsal phase required')
        directory = Path('/var/lib/docker/intruoyi-release-workflow/recovery-evidence') / job_id
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = directory / 'rehearsal-progress.private.json'
        if path.exists():
            current = json.loads(path.read_text())
            require(current.get('jobId') == job_id, 'Rehearsal progress belongs to another job')
        pid = os.getpid()
        value = {'jobId':job_id,'phase':phase,'pid':pid,'processStart':process_start_identity(pid),
                 'observedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
        require(value['processStart'] is not None, 'Remote process identity cannot be recorded')
        temporary = path.with_suffix('.new')
        temporary.write_text(json.dumps(value),encoding='utf-8')
        os.chmod(str(temporary),0o600)
        os.replace(str(temporary),str(path))
        return value
    if action == 'rehearsal-job-status':
        job_id = p.get('jobId')
        require(isinstance(job_id,str) and re.fullmatch('JOB-[a-f0-9]{10}',job_id), 'Valid rehearsal job ID required')
        path = Path('/var/lib/docker/intruoyi-release-workflow/recovery-evidence') / job_id / 'rehearsal-progress.private.json'
        require(path.is_file(), 'No remote rehearsal execution evidence for this job')
        value = json.loads(path.read_text())
        require(value.get('jobId') == job_id, 'Remote rehearsal evidence belongs to another job')
        current_start = process_start_identity(value.get('pid',-1))
        if value['phase'] in ('capture-complete','completed'):
            status = 'succeeded'
        elif value['phase'] == 'failed':
            status = 'failed'
        elif current_start is not None and current_start == value.get('processStart'):
            status = 'running'
        else:
            status = 'unknown'
        return dict(value, status=status)
    if action == 'rehearsal-media-column-proof':
        r.sql(profile, 'SHOW TABLES; DESCRIBE infra_file;')
        keys = r.sql(profile, "SELECT COLUMN_NAME FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='infra_file' AND INDEX_NAME='PRIMARY' ORDER BY SEQ_IN_INDEX;").splitlines()
        counts = r.sql(profile, "SET SESSION TRANSACTION READ ONLY; START TRANSACTION READ ONLY; SELECT COUNT(*),COALESCE(SUM(url REGEXP '(X-Amz-Signature|X-Amz-Credential|AWSAccessKeyId|Signature)='),0) FROM infra_file; ROLLBACK;").split('\t')
        backend = r.inspect(profile['backend'])
        env = dict(value.split('=', 1) for value in backend['Config']['Env'])
        allowed = ('EDHR_S3_BUCKET', 'EDHR_S3_REGION', 'EDHR_S3_RETENTION_MODE', 'EDHR_S3_RETAIN_UNTIL_DAYS', 'EDHR_S3_REQUIRE_LEGAL_HOLD', 'EDHR_S3_ENABLE_PATH_STYLE_ACCESS')
        return {'primaryKey': keys, 'totalRows': int(counts[0]), 'signedRows': int(counts[1]),
                'edhrProperties': {key: env[key] for key in allowed if key in env},
                'backendNetworkNames': sorted(backend['NetworkSettings']['Networks']), 'mutations': False}
    if action == 'rehearsal-writer-inventory':
        dependencies = {role: r.inspect(profile[role]) for role in ('database', 'redis', 'minio')}
        needles = {profile['host']} | {profile[role] for role in dependencies}
        for item in dependencies.values():
            needles.update(value['IPAddress'] for value in item['NetworkSettings']['Networks'].values() if value.get('IPAddress'))
        rows = []
        for name in r.run(['docker', 'ps', '-a', '--format', '{{.Names}}']).decode().splitlines():
            container = r.inspect(name)
            environment = dict(value.split('=', 1) for value in container['Config'].get('Env') or [])
            keys = sorted(key for key, value in environment.items() if any(needle in value for needle in needles))
            origins = []
            for key in keys:
                for match in re.finditer(r'(?:jdbc:)?(?:https?|mysql|redis)://[^\s;]+', environment[key]):
                    value = match.group(0)
                    parsed = urlsplit(value[5:] if value.startswith('jdbc:') else value)
                    if parsed.hostname in needles:
                        origins.append({'envName': key, 'scheme': parsed.scheme, 'host': parsed.hostname, 'port': parsed.port})
            command = ' '.join(container['Config'].get('Cmd') or [])
            rows.append({'container': name, 'running': container['State']['Running'],
                         'networks': sorted(container['NetworkSettings']['Networks']), 'dependencyReferenceEnvNames': keys,
                         'registeredDependencyOrigins': origins,
                         'networkAddresses': {network: {'address': values.get('IPAddress'), 'configuredAddress': (values.get('IPAMConfig') or {}).get('IPv4Address')} for network, values in container['NetworkSettings']['Networks'].items()},
                         'commandReferencesDependency': any(needle in command for needle in needles),
                         'dockerSocketMounted': any(mount['Destination'] == '/var/run/docker.sock' for mount in container['Mounts'])})
        r.sql(profile, 'SHOW TABLES;')
        connections = r.sql(profile, "SET SESSION TRANSACTION READ ONLY; START TRANSACTION READ ONLY; SELECT SUBSTRING_INDEX(HOST,':',1),COUNT(*) FROM information_schema.PROCESSLIST WHERE DB=DATABASE() AND ID<>CONNECTION_ID() GROUP BY SUBSTRING_INDEX(HOST,':',1); ROLLBACK;")
        return {'containers': rows, 'databaseClientAddresses': [{'address': row.split('\t')[0], 'connections': int(row.split('\t')[1])} for row in connections.splitlines()],
                'inventoryConfirmed': False, 'reason': 'Review exact registered endpoint ownership and map running-source DB/Redis clients to application containers before confirmation', 'mutations': False}

    def valid_name(value):
        require(isinstance(value, str) and re.fullmatch('[A-Za-z0-9_.-]+', value), 'Explicit valid dependency/resource name required')
        return value

    def source_check():
        api['check_storage'](profile)
        api['check_fence'](profile)
        require(profile.get('writerInventoryConfirmed') is True and profile['backend'] in profile.get('writers', []), 'Source writer closure must be explicitly registered')
        require(profile.get('dependencyWriterInventoryConfirmed') is True, 'Redis and MinIO writer closure must be explicitly confirmed; shared external writers forbid an inconsistent copy')
        for key in ('redis', 'minio'):
            item = r.inspect(valid_name(profile.get(key)))
            require(item['State']['Running'], 'Source dependency is not running: ' + key)
        backend_env = dict(value.split('=', 1) for value in r.inspect(profile['backend'])['Config']['Env'])
        source_backend_startup(r.inspect(profile['backend']), r, profile['backend'])
        require(profile.get('edhrProperties') and all(backend_env.get(key) == value for key, value in profile['edhrProperties'].items()), 'EDHR source configuration differs from verified registration')
        path = profile.get('minioDataPath')
        require(isinstance(path, str) and path.startswith('/') and '..' not in Path(path).parts, 'Explicit source MinIO data directory required')
        hosts = profile.get('minioLocalEndpointHosts')
        require(isinstance(hosts, list) and hosts and all(isinstance(value, str) and value for value in hosts), 'Explicit source MinIO endpoint host registration required')
        buckets = profile.get('minioBuckets')
        require(isinstance(buckets, list) and buckets and len(set(buckets)) == len(buckets) and all(re.fullmatch('[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]', b) for b in buckets), 'Explicit MinIO bucket whitelist required')
        fmt = json.loads(r.run(['docker', 'exec', profile['minio'], 'cat', path.rstrip('/') + '/.minio.sys/format.json']))
        require(fmt.get('format') == 'xl-single' and fmt.get('version') == '1' and fmt.get('xl', {}).get('version') == '3' and sum(len(v) for v in fmt.get('xl', {}).get('sets', [])) == 1, 'Only inspected xl-single v3 single-drive media copy is supported')
        redis_socket, redis_command = redis_connection(profile['redis'], **source_redis_auth(profile, r))
        try:
            require(redis_command('PING') == b'PONG', 'Registered Redis authentication did not return PONG')
        finally:
            redis_socket.close()
        for name in [profile['frontend']] + profile['writers']:
            require(r.inspect(valid_name(name))['State']['Running'], 'Source writer not running; reconcile before snapshot')
        return {'ready': True, 'mutations': False}

    def resources():
        for key in ('frontend', 'backend', 'database', 'redis', 'minio', 'network', 'acceptanceFrontend'):
            value = valid_name(profile.get(key))
            require(value.startswith(PREFIX + '-'), 'Resource is outside authorized rehearsal namespace')
        require(profile.get('environment') == 'rehearsal', 'Rehearsal environment required')
        require(profile.get('backendEntrypoint') is None or isinstance(profile['backendEntrypoint'], list), 'Explicit backendEntrypoint must be array or null')
        require('backendEntrypoint' in profile and isinstance(profile.get('backendCommand'), list) and profile['backendCommand'], 'Explicit isolated backend startup contract required')
        require(any('/run/release/application.properties' in value for value in profile['backendCommand']), 'Isolated backend must explicitly load private generated properties')
        require(profile.get('minioDataPath') == '/data', 'Isolated MinIO uses explicitly registered /data')
        return [profile[k] for k in ('frontend', 'backend', 'database', 'redis', 'minio', 'acceptanceFrontend')] + [PREFIX + '-gateway']

    def existing_names():
        return set(r.run(['docker', 'ps', '-a', '--format', '{{.Names}}']).decode().splitlines())

    def owned_check():
        names = resources()
        for name in set(names) & existing_names():
            require(r.inspect(name)['Config'].get('Labels', {}).get(LABEL) == PREFIX, 'Unowned resource conflict: ' + name)
        networks = r.run(['docker', 'network', 'ls', '--format', '{{.Name}}']).decode().splitlines()
        if profile['network'] in networks:
            net = json.loads(r.run(['docker', 'network', 'inspect', profile['network']]))[0]
            require(net.get('Labels', {}).get(LABEL) == PREFIX and net['Internal'], 'Unowned/nonisolated network conflict')
        volumes = set(r.run(['docker', 'volume', 'ls', '--format', '{{.Name}}']).decode().splitlines())
        for key in ('database', 'redis', 'minio'):
            name = profile[key] + '-data'
            if name in volumes:
                info = json.loads(r.run(['docker', 'volume', 'inspect', name]))[0]
                require((info.get('Labels') or {}).get(LABEL) == PREFIX, 'Unowned rehearsal data volume conflict')
        return names

    def target_check():
        api['check_storage'](profile)
        names = owned_check()
        require(not (set(names) & existing_names()), 'Rehearsal resources already exist; explicit reset required')
        require(profile['network'] not in r.run(['docker', 'network', 'ls', '--format', '{{.Name}}']).decode().splitlines(), 'Rehearsal network already exists; explicit reset required')
        volumes = set(r.run(['docker', 'volume', 'ls', '--format', '{{.Name}}']).decode().splitlines())
        require(not ({profile[k] + '-data' for k in ('database', 'redis', 'minio')} & volumes), 'Rehearsal data volume already exists; explicit reset required')
        for key, expected in (('entryUrl', 38082), ('acceptanceUrl', 38083), ('isolatedMinioPublicUrl', 39082)):
            u = urlsplit(profile[key])
            require(u.hostname == profile['host'] and u.port == expected, 'Unexpected registered rehearsal port')
            s = socket.socket()
            try:
                s.bind(('0.0.0.0', expected))
            except OSError:
                raise blocked('Rehearsal port already bound: ' + str(expected))
            finally:
                s.close()
        return {'ready': True, 'mutations': False}

    def root(tag):
        validated = api['directory'](profile, tag)
        return validated.parent / 'rehearsal-seed' / validated.name

    def new_seed(folder):
        if folder.exists():
            marker = folder / 'rehearsal-owned.json'
            require(marker.is_file() and json.loads(marker.read_text()).get('owner') == PREFIX, 'Existing seed directory ownership cannot be proved')
            retained = folder.with_name(folder.name + '-retained-' + str(int(time.time())) + '-' + secrets.token_hex(4))
            folder.rename(retained)
        folder.mkdir(mode=0o700, parents=True, exist_ok=False)
        api['private_json'](folder / 'rehearsal-owned.json', {'owner': PREFIX})

    def file_record(path):
        return {'name': path.name, 'path': str(path), 'sha256': api['file_sha'](path), 'bytes': path.stat().st_size}

    def stream_file(args, path, stdin=None):
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as out:
            result = subprocess.run(args, stdin=stdin, stdout=out, stderr=subprocess.PIPE, timeout=14400)
        require(result.returncode == 0 and path.stat().st_size > 0, 'Private full-data capture failed; source remains stopped')

    def redis_connection(container, noauth=False, password_env=None, password=None):
        info = r.inspect(container)
        env = dict(v.split('=', 1) for v in info['Config']['Env'])
        ips = [v['IPAddress'] for v in info['NetworkSettings']['Networks'].values() if v.get('IPAddress')]
        require(len(ips) == 1, 'Redis must have one unambiguous registered network address')
        connection = socket.create_connection((ips[0], 6379), 20)
        stream = connection.makefile('rb')
        def read():
            first = stream.read(1)
            line = stream.readline()
            require(first and line.endswith(b'\r\n'), 'Redis protocol incomplete')
            value = line[:-2]
            if first == b'-':
                raise blocked('Redis operation refused; details retained remotely')
            if first == b':':
                return int(value)
            if first == b'+':
                return value
            if first == b'$':
                length = int(value)
                if length == -1:
                    return None
                data = stream.read(length)
                require(len(data) == length and stream.read(2) == b'\r\n', 'Redis bulk data incomplete')
                return data
            if first == b'*':
                return [read() for _ in range(int(value))]
            raise blocked('Unexpected Redis protocol response')
        def command(*values):
            values = [v if isinstance(v, bytes) else str(v).encode() for v in values]
            connection.sendall(b'*' + str(len(values)).encode() + b'\r\n' + b''.join(b'$' + str(len(v)).encode() + b'\r\n' + v + b'\r\n' for v in values))
            return read()
        if not noauth:
            command('AUTH', password if password is not None else env[password_env])
        return connection, command

    def media_digest(stream):
        records = []
        with tarfile.open(fileobj=stream, mode='r|') as archive:
            for entry in archive:
                name = posixpath.normpath(entry.name)
                require(not name.startswith('/') and '..' not in name.split('/') and not entry.issym() and not entry.islnk(), 'Unsafe restored media path')
                if entry.isfile():
                    checksum = hashlib.sha256()
                    data = archive.extractfile(entry)
                    for chunk in iter(lambda: data.read(1024 * 1024), b''):
                        checksum.update(chunk)
                    records.append([name, entry.size, checksum.hexdigest()])
        require(records, 'Media copy contains no real files')
        return {'fileCount': len(records), 'bytes': sum(value[1] for value in records), 'sha256': api['sha'](sorted(records))}

    if action == 'rehearsal-verify-stopped':
        # Explicit technical resolution: prove quiescence, never infer success.
        blockers = []
        for entry in Path('/proc').iterdir():
            if not entry.name.isdigit() or int(entry.name) == os.getpid():
                continue
            try:
                args = (entry / 'cmdline').read_bytes().split(b'\0')
                comm = (entry / 'comm').read_text().strip()
            except FileNotFoundError:
                continue
            if ('python' in comm and b'-' in args[1:]) or any(
                    PREFIX.encode() in arg or b'/rehearsal-seed/' in arg for arg in args):
                # Service processes inside the labelled containers are stopped by reset.
                if comm not in ('mysqld', 'redis-server', 'minio', 'java', 'nginx'):
                    blockers.append(int(entry.name))
        require(not blockers, 'Rehearsal worker processes still exist; technical resolution refused')
        if p.get('checkProcessesOnly') is True:
            return {'stopped': True}
        folder = root(p['releaseTag'])
        marker = json.loads((folder / 'rehearsal-owned.json').read_text())
        require(marker.get('owner') == PREFIX, 'Capture ownership missing')
        capture = json.loads((folder / 'capture-complete.private.json').read_text())
        observation = api['observe'](profile)
        require(observation['fingerprint'] == capture['originFingerprint'], 'Source differs from completed capture origin')
        require(observation['backendHealth'].get('status') == 'UP' and observation['frontendHttpStatus'] == 200
                and not observation['maintenance'], 'Source business is not healthy and open')
        return {'stopped': True, 'originFingerprint': capture['originFingerprint'], 'sourceHealthy': True,
                'captureSha256': api['file_sha'](folder / 'capture-complete.private.json')}
    if action == 'rehearsal-source-check':
        return source_check()
    if action == 'rehearsal-redis-inventory':
        connection, command = redis_connection(profile['redis'], **source_redis_auth(profile, r))
        try:
            require(command('PING') == b'PONG', 'Registered Redis authentication did not return PONG')
            clients = []
            for line in command('CLIENT', 'LIST').decode('utf-8').splitlines():
                fields = dict(value.split('=', 1) for value in line.split() if '=' in value)
                clients.append({key: fields.get(key) for key in ('addr', 'laddr', 'db', 'cmd', 'user')})
            return {'authenticated': True, 'clients': clients, 'mutations': False}
        finally:
            connection.close()
    if action == 'rehearsal-target-check':
        return target_check()
    if action == 'rehearsal-create-stage':
        target_check()
        folder = root(p['releaseTag'])
        new_seed(folder)
        return {'directory': str(folder)}
    if action == 'rehearsal-capture':
        job_id = p.get('jobId')
        require(isinstance(job_id,str) and re.fullmatch('JOB-[a-f0-9]{10}',job_id), 'Valid rehearsal job ID required')
        dispatch(dict(p, action='rehearsal-job-progress', phase='capture-starting'), api)
        source_check()
        backend = r.inspect(profile['backend'])
        minio = r.inspect(profile['minio'])
        before = api['observe'](profile)
        require(before['fingerprint'] == p['originFingerprint'], 'Source fingerprint changed before snapshot')
        historical = p['historicalMetadata']
        metadata = json.loads(r.run(['docker', 'exec', profile['frontend'], 'cat', '/usr/share/nginx/html/release-info.json']))
        metadata_kind = historical.get('kind')
        require(metadata_kind in ('historical-original', 'image-embedded'), 'Explicit source metadata identity required')
        if metadata_kind == 'historical-original':
            manifest_path = Path(historical['directory']) / 'manifest.json'
            require(api['file_sha'](manifest_path) == historical['manifestSha256'] and json.loads(manifest_path.read_text()) == historical['manifest'], 'Source historical original manifest differs')
            require(before['images'] == {role: entry['id'] for role, entry in historical['images'].items()}, 'Historical metadata image identity differs')
            require(metadata == historical['info'], 'Historical metadata differs from proved original package')
        else:
            require(before['images'] == historical['images'] and before['releaseTag'] == historical['releaseTag'], 'Source image identity changed')
            image_metadata = json.loads(r.run(['docker', 'run', '--rm', '--pull=never', '--network', 'none', '--read-only',
                                               '--entrypoint', 'cat', before['images']['frontend'], '/usr/share/nginx/html/release-info.json']))
            require(metadata == image_metadata, 'Source container metadata differs from immutable image')
        require(metadata['releaseTag'] == before['releaseTag'], 'Source metadata release differs')
        folder = root(p['releaseTag'])
        new_seed(folder)
        api['private_json'](folder / 'capture-before.private.json', before)
        nginx = folder / 'nginx.conf'
        r.run(['docker', 'cp', profile['frontend'] + ':/etc/nginx/conf.d/default.conf', str(nginx)])
        nginx.chmod(0o600)
        metadata_path = folder / 'historical-release-info.json'
        api['private_json'](metadata_path, metadata)
        startup_path = folder / 'backend-startup.private.json'
        api['private_json'](startup_path, source_backend_startup(backend, r, profile['backend']))

        images = {role: r.inspect(profile[role])['Image'] for role in ('backend', 'frontend', 'database', 'redis', 'minio')}
        if p.get('reuseImages'):
            require(p.get('imageIds') == images, 'Same-daemon required image identities changed during capture')
        if not p.get('reuseImages'):
            image_archive = folder / 'origin-images.tar'
            stream_file(['docker', 'save'] + sorted(set(images.values())), image_archive)

        api['stop_writers'](profile)
        frozen = api['observe'](profile)
        for key in ('images', 'schemaSha256', 'ledgerSha256'):
            require(frozen[key] == before[key], 'Source origin changed during quiescence')
        artifacts = [file_record(Path(api['backup'](profile, folder)['path']))]
        connection, command = redis_connection(profile['redis'], **source_redis_auth(profile, r))
        redis_path = folder / 'redis.jsonl'
        fd = os.open(str(redis_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        count = 0
        with os.fdopen(fd, 'w') as output:
            database_count = command('CONFIG', 'GET', 'databases')
            require(len(database_count) == 2, 'Cannot establish complete Redis database inventory')
            for database_index in range(int(database_count[1])):
                command('SELECT', database_index)
                cursor = b'0'
                while True:
                    cursor, keys = command('SCAN', cursor, 'COUNT', 500)
                    for key in keys:
                        data = command('DUMP', key)
                        ttl = command('PTTL', key)
                        if data is not None and ttl != -2:
                            output.write(json.dumps({'database': database_index, 'key': base64.b64encode(key).decode(), 'value': base64.b64encode(data).decode(), 'expires': None if ttl == -1 else time.time() + ttl / 1000.0}) + '\n')
                            count += 1
                    if cursor == b'0':
                        break
        connection.close()
        artifacts.append(file_record(redis_path))
        media = folder / 'minio.tar'
        media_fd = os.open(str(media), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        selected = [(bucket, '') for bucket in profile['minioBuckets']]
        selected += [('.minio.sys/buckets/' + bucket, '.minio.sys/buckets') for bucket in profile['minioBuckets']]
        selected += [('.minio.sys/format.json', '.minio.sys')]
        with os.fdopen(media_fd, 'wb') as output, tarfile.open(fileobj=output, mode='w|') as assembled:
            for relative, prefix in selected:
                process = subprocess.Popen(['docker', 'cp', profile['minio'] + ':' + profile['minioDataPath'].rstrip('/') + '/' + relative, '-'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                try:
                    with tarfile.open(fileobj=process.stdout, mode='r|') as archive:
                        for entry in archive:
                            require(not entry.name.startswith('/') and '..' not in entry.name.split('/') and not entry.issym() and not entry.islnk(), 'Unsafe media archive member')
                            content = archive.extractfile(entry) if entry.isfile() else None
                            entry.name = posixpath.join(prefix, entry.name)
                            assembled.addfile(entry, content)
                    require(process.wait(timeout=60) == 0, 'Required whitelisted bucket or bucket metadata copy failed')
                finally:
                    process.stdout.close()
                    if process.poll() is None:
                        process.kill()
                        process.wait()

        artifacts.append(file_record(media))
        with media.open('rb') as content:
            media_identity = media_digest(content)
        artifacts.extend([file_record(nginx), file_record(metadata_path)])
        if not p.get('reuseImages'):
            artifacts.append(file_record(image_archive))
        db_env = dict(v.split('=', 1) for v in r.inspect(profile['database'])['Config']['Env'])
        database_name = db_env.get('MYSQL_DATABASE')
        require(database_name and re.fullmatch('[A-Za-z0-9_-]+', database_name), 'Explicit source database name missing')
        characteristics = r.sql(profile, 'SELECT @@lower_case_table_names,@@character_set_database,@@collation_database;').split('\t')
        require(len(characteristics) == 3 and characteristics[0] in ('0', '1', '2') and all(re.fullmatch('[A-Za-z0-9_]+', value) for value in characteristics[1:]), 'Unsupported source database characteristics')
        artifacts.append(file_record(startup_path))
        upstreams = [profile['backend']] + [v['IPAddress'] for v in backend['NetworkSettings']['Networks'].values() if v.get('IPAddress')]
        minio_upstreams = [profile['minio']] + [v['IPAddress'] for v in minio['NetworkSettings']['Networks'].values() if v.get('IPAddress')]
        result = {'originFingerprint': before['fingerprint'], 'origin': before, 'images': images, 'artifacts': artifacts,
                  'backendActiveProfiles': source_active_profiles(backend), 'minioUpstreams': minio_upstreams,
                  'databaseName': database_name, 'redisKeys': count, 'backendUpstreams': upstreams, 'mediaIdentity': media_identity, 'databaseCharacteristics': characteristics,
                  'historicalMetadata': {'persistedInImage': metadata_kind == 'image-embedded', 'restoredFromOriginalPackage': metadata_kind == 'historical-original', 'manifestSha256': historical.get('manifestSha256'), 'releaseTag': metadata['releaseTag'], 'contentSha256': api['file_sha'](metadata_path)}}
        api['private_json'](folder / 'capture-complete.private.json', result)
        # Source resume occurs only after every required artifact is complete and hashed.
        for name in profile['writers'] + [profile['frontend']]:
            api['docker']('POST', '/containers/' + name + '/start')
            require(r.inspect(name)['State']['Running'], 'Source writer failed to resume')
        dispatch(dict(p, action='rehearsal-job-progress', phase='capture-complete'), api)
        return result
    if action == 'rehearsal-restore':
        job_id = p.get('jobId')
        require(isinstance(job_id,str) and re.fullmatch('JOB-[a-f0-9]{10}',job_id), 'Valid rehearsal job ID required')
        dispatch(dict(p, action='rehearsal-job-progress', phase='restore-starting'), api)
        target_check()
        folder = root(p['releaseTag'])
        require(json.loads((folder / 'rehearsal-owned.json').read_text())['owner'] == PREFIX, 'Rehearsal staging ownership missing')
        capture = p['capture']
        for item in capture['artifacts']:
            path = folder / item['name']
            require(path.is_file() and api['file_sha'](path) == item['sha256'], 'Transferred full-data artifact checksum mismatch')
        if 'origin-images.tar' in [item['name'] for item in capture['artifacts']]:
            r.run(['docker', 'load', '-i', str(folder / 'origin-images.tar')], timeout=14400)
        for image in capture['images'].values():
            require(r.run(['docker', 'image', 'inspect', '--format', '{{.Id}}', image]).decode().strip() == image, 'Original image ID not preserved')
        r.run(['docker', 'network', 'create', '--internal', '--label', LABEL + '=' + PREFIX, profile['network']])
        for role in ('database', 'redis', 'minio'):
            r.run(['docker', 'volume', 'create', '--label', LABEL + '=' + PREFIX, profile[role] + '-data'])
        passwords = {key: secrets.token_hex(24) for key in ('mysql', 'redis', 'minio')}
        props = {'spring.datasource.dynamic.datasource.master.url': 'jdbc:mysql://' + profile['database'] + ':3306/' + capture['databaseName'] + '?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=Asia/Shanghai',
                 'spring.datasource.dynamic.datasource.master.username': 'root',
                 'spring.datasource.dynamic.datasource.master.password': passwords['mysql'],
                 'spring.data.redis.host': profile['redis'], 'spring.data.redis.port': '6379', 'spring.data.redis.password': passwords['redis'],
                 'spring.redis.host': profile['redis'], 'spring.redis.port': '6379', 'spring.redis.password': passwords['redis']}
        for key in ('url', 'username', 'password'):
            props['spring.datasource.dynamic.datasource.slave.' + key] = props['spring.datasource.dynamic.datasource.master.' + key]
        props.update({'spring.quartz.auto-startup': 'false', 'spring.task.scheduling.enabled': 'false',
                      'spring.boot.admin.client.enabled': 'false'})
        overrides = profile.get('isolatedProperties', {})
        require(isinstance(overrides, dict) and not set(overrides).intersection(props), 'Registered overrides cannot redirect isolated database or Redis')
        props.update(overrides)
        require(all('\n' not in str(k) + str(v) for k, v in props.items()), 'Invalid isolated property value')
        config = folder / 'application.properties'
        startup = json.loads((folder / 'backend-startup.private.json').read_text())
        fd = os.open(str(config), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as output:
            output.write(startup['properties'].rstrip() + '\n')
            output.write('\n'.join(str(k) + '=' + str(v) for k, v in sorted(props.items())) + '\n')
        def create(role, command, env=None, binds=None, ports=None, entrypoint=None, start=True):
            name = profile[role]
            value = {'Image': capture['images'][role], 'Cmd': command, 'Env': env or [], 'Labels': {LABEL: PREFIX},
                     'HostConfig': {'NetworkMode': profile['network'], 'Binds': binds or [], 'PortBindings': ports or {}, 'RestartPolicy': {'Name': 'no'}},
                     'NetworkingConfig': {'EndpointsConfig': {profile['network']: {'Aliases': [name]}}}}
            if role == 'backend':
                value['Entrypoint'] = entrypoint
            result = api['docker']('POST', '/containers/create?name=' + name, value)
            if start:
                api['docker']('POST', '/containers/' + result['Id'] + '/start')
            return result
        characteristics = capture['databaseCharacteristics']
        create('database', ['--event-scheduler=OFF', '--lower-case-table-names=' + characteristics[0], '--character-set-server=' + characteristics[1], '--collation-server=' + characteristics[2]], ['MYSQL_DATABASE=' + capture['databaseName'], 'MYSQL_ROOT_PASSWORD=' + passwords['mysql']], [profile['database'] + '-data:/var/lib/mysql'])
        deadline = time.monotonic() + 180
        while True:
            try:
                r.sql(profile, 'SHOW TABLES;')
                break
            except Exception:
                require(time.monotonic() < deadline, 'Isolated MySQL initialization timed out')
                time.sleep(2)
        auth = 'export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; exec mysql -uroot "$MYSQL_DATABASE"'
        with (folder / 'recovery.sql').open('rb') as data:
            result = subprocess.run(['docker', 'exec', '-i', profile['database'], 'sh', '-c', auth], stdin=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=14400)
        require(result.returncode == 0, 'Full database restore failed')
        create('redis', ['redis-server', '--requirepass', passwords['redis'], '--appendonly', 'yes'], binds=[profile['redis'] + '-data:/data'])
        deadline = time.monotonic() + 60
        while True:
            try:
                connection, command = redis_connection(profile['redis'], password=passwords['redis'])
                break
            except (OSError, ConnectionError):
                require(time.monotonic() < deadline, 'Isolated Redis initialization timed out')
                time.sleep(1)
        with (folder / 'redis.jsonl').open() as data:
            for line in data:
                item = json.loads(line)
                command('SELECT', item['database'])
                ttl = 0 if item['expires'] is None else int((item['expires'] - time.time()) * 1000)
                if item['expires'] is not None and ttl <= 0:
                    continue
                command('RESTORE', base64.b64decode(item['key']), ttl, base64.b64decode(item['value']), 'REPLACE')
        connection.close()
        create('minio', ['server', '/data'], ['MINIO_ROOT_USER=release-isolation', 'MINIO_ROOT_PASSWORD=' + passwords['minio']], [profile['minio'] + '-data:/data'], ports={'9000/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '39082'}]}, start=False)
        # Stop MinIO while restoring its actual backend files; it never sees a partial data tree.
        with (folder / 'minio.tar').open('rb') as data:
            result = subprocess.run(['docker', 'cp', '-', profile['minio'] + ':/data'], stdin=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=14400)
        require(result.returncode == 0, 'Full MinIO media restore failed')
        verification = subprocess.Popen(['docker', 'cp', profile['minio'] + ':/data/.', '-'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            restored_media = media_digest(verification.stdout)
            require(verification.wait(timeout=60) == 0 and restored_media == capture['mediaIdentity'], 'Restored whitelisted media bytes differ from source snapshot')
        finally:
            verification.stdout.close()
            if verification.poll() is None:
                verification.kill()
                verification.wait()
        api['private_json'](folder / 'verified-media-origin.json', restored_media)
        api['docker']('POST', '/containers/' + profile['minio'] + '/start')
        url_evidence = isolate_stored_media_urls(profile, p['sourceProfile'], api)
        api['private_json'](folder / 'isolated-media-url-transformations.json', url_evidence)
        source_hosts = p['sourceProfile'].get('minioLocalEndpointHosts')
        require(isinstance(source_hosts, list) and source_hosts and all(isinstance(value, str) for value in source_hosts), 'Explicit source MinIO endpoint hosts required for isolated config conversion')
        r.sql(profile, 'SHOW TABLES; DESCRIBE infra_file_config;')
        rows = r.sql(profile, "SELECT id,HEX(config) FROM infra_file_config WHERE deleted=b'0' ORDER BY id;")
        conversions = []
        config_updates = []
        for line in rows.splitlines():
            identifier, encoded = line.split('\t')
            require(identifier.isdigit(), 'Unexpected file configuration identity')
            original = bytes.fromhex(encoded).decode('utf-8')
            configuration = json.loads(original)
            if configuration.get('bucket') not in p['sourceProfile']['minioBuckets']:
                continue
            endpoint = urlsplit(configuration.get('endpoint', ''))
            if endpoint.hostname not in source_hosts:
                continue
            configuration.update(endpoint='http://' + profile['minio'] + ':9000', domain=profile['isolatedMinioPublicUrl'].rstrip('/') + '/' + configuration['bucket'], accessKey='release-isolation', accessSecret=passwords['minio'])
            changed = json.dumps(configuration, ensure_ascii=False, separators=(',', ':'))
            config_updates.append("UPDATE infra_file_config SET config=CONVERT(0x" + changed.encode('utf-8').hex() + " USING utf8mb4) WHERE id=" + identifier + '; SELECT ROW_COUNT();')
            conversions.append({'id': identifier, 'bucket': configuration['bucket'], 'beforeSha256': hashlib.sha256(original.encode('utf-8')).hexdigest(), 'afterSha256': hashlib.sha256(changed.encode('utf-8')).hexdigest()})
            if len(config_updates) == 100:
                apply_checked_batches(lambda query:r.sql(profile, query), config_updates, 'Isolated MinIO configuration')
                config_updates = []
        if config_updates:
            apply_checked_batches(lambda query:r.sql(profile, query), config_updates, 'Isolated MinIO configuration')
        require(conversions, 'No explicitly registered local MinIO configuration was isolated')
        api['private_json'](folder / 'isolated-config-transformations.json', conversions)
        # Internal network prevents restored business config from reaching production services.
        # Historical baseline has no supported quiescent-start protocol. Its normal
        # process can reach only independently restored services on this internal net.
        command = [arg for arg in profile['backendCommand'] if not arg.startswith('--spring.profiles.active=')]
        command.extend(arg for arg in startup['arguments'] if arg[2:].split('=', 1)[0] not in props)
        command.append('--spring.profiles.active=' + capture['backendActiveProfiles'])
        create('backend', command, isolated_backend_environment(profile, p['sourceProfile'], passwords['minio']), [str(config) + ':/run/release/application.properties:ro'], entrypoint=profile['backendEntrypoint'])
        nginx = isolated_nginx_config((folder / 'nginx.conf').read_text(), urlsplit(p['sourceProfile']['entryUrl']).port or 80,
                                     capture['backendUpstreams'], profile['backend'], capture['minioUpstreams'], profile['minio'])
        (folder / 'nginx.conf').write_text(nginx)
        create('frontend', None, binds=[str(folder / 'nginx.conf') + ':/etc/nginx/conf.d/default.conf:ro'], ports={'80/tcp': [{'HostIp': '0.0.0.0', 'HostPort': '38082'}]}, start=False)
        metadata_path = folder / 'historical-release-info.json'
        require(api['file_sha'](metadata_path) == capture['historicalMetadata']['contentSha256'], 'Historical metadata transfer differs')
        metadata_path.chmod(0o644)
        if capture['historicalMetadata']['restoredFromOriginalPackage']:
            r.run(['docker', 'cp', str(metadata_path), profile['frontend'] + ':/usr/share/nginx/html/release-info.json'])
        api['docker']('POST', '/containers/' + profile['frontend'] + '/start')
        # Docker does not publish ports on an internal-only network. A dedicated
        # nginx ingress joins both networks; business containers stay internal.
        gateway = folder / 'gateway-nginx.conf'
        servers = []
        for port, upstream in ((38082, profile['frontend'] + ':80'),
                               (38083, profile['acceptanceFrontend'] + ':80'),
                               (39082, profile['minio'] + ':9000')):
            servers.append('server { listen ' + str(port) + '; resolver 127.0.0.11 valid=5s; '
                           'client_max_body_size 0; location / { set $upstream "' + upstream + '"; '
                           'proxy_pass http://$upstream; proxy_set_header Host $http_host; '
                           'proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; '
                           'proxy_read_timeout 300s; } }')
        gateway.write_text('\n'.join(servers))
        gateway.chmod(0o644)
        name = PREFIX + '-gateway'
        value = {'Image': capture['images']['frontend'], 'Entrypoint': ['nginx'], 'Cmd': ['-g', 'daemon off;'],
                 'Labels': {LABEL: PREFIX},
                 'HostConfig': {'NetworkMode': 'bridge', 'Binds': [str(gateway) + ':/etc/nginx/conf.d/default.conf:ro'],
                                'Sysctls': {'net.ipv4.ip_forward': '0'},
                                'PortBindings': {str(port) + '/tcp': [{'HostIp': '0.0.0.0', 'HostPort': str(port)}]
                                                 for port in (38082, 38083, 39082)}},
                 'ExposedPorts': {str(port) + '/tcp': {} for port in (38082, 38083, 39082)}}
        api['docker']('POST', '/containers/create?name=' + name, value)
        api['docker']('POST', '/networks/' + profile['network'] + '/connect', {'Container': name})
        api['docker']('POST', '/containers/' + name + '/start')
        deadline = time.monotonic() + 240
        while True:
            isolated = api['observe'](profile)
            try:
                with urlopen(profile['isolatedMinioPublicUrl'] + '/minio/health/ready', timeout=5) as response:
                    media_ready = response.status == 200
            except Exception:
                media_ready = False
            if isolated['backendHealth'].get('status') == 'UP' and isolated['frontendHttpStatus'] == 200 and media_ready:
                break
            require(time.monotonic() < deadline, 'Isolated baseline backend/frontend/media health did not become ready')
            time.sleep(2)
        for key in ('images', 'schemaSha256', 'ledgerSha256'):
            require(isolated[key] == capture['origin'][key], 'Restored source origin mismatch: ' + key)
        api['private_json'](folder / 'restored-origin.json', {'originFingerprint': capture['originFingerprint'], 'verifiedOrigin': True, 'fingerprint': isolated['fingerprint']})
        dispatch(dict(p, action='rehearsal-job-progress', phase='completed'), api)
        return {'restored': True, 'originFingerprint': capture['originFingerprint'], 'verifiedOrigin': True}
    if action in ('rehearsal-reset-check', 'rehearsal-reset'):
        names = owned_check()
        if action.endswith('-check'):
            return {'ready': True, 'resources': names}
        for name in names:
            if name in existing_names():
                # Explicit owned resource deletion includes only its anonymous volumes.
                r.run(['docker', 'rm', '--force', '--volumes', name])
        if profile['network'] in r.run(['docker', 'network', 'ls', '--format', '{{.Name}}']).decode().splitlines():
            r.run(['docker', 'network', 'rm', profile['network']])
        volumes = set(r.run(['docker', 'volume', 'ls', '--format', '{{.Name}}']).decode().splitlines())
        for role in ('database', 'redis', 'minio'):
            name = profile[role] + '-data'
            if name in volumes:
                r.run(['docker', 'volume', 'rm', name])
        return {'reset': True, 'preservedPrivateEvidence': True}
    raise blocked('Unknown rehearsal operation')
