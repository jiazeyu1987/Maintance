"""Read Docker runtime identities only; suitable for Spug remote manual tasks."""
import datetime
import json
import subprocess


def query():
    listing = subprocess.check_output([
        'docker', 'ps', '--format', '{{.ID}} {{.Names}} {{.Image}}'
    ], timeout=15).decode().splitlines()
    ids = [line.split()[0] for line in listing if 'intruoyi' in line.lower()
           and any(role in line.lower() for role in ('backend', 'frontend'))]
    observed = datetime.datetime.now(datetime.timezone.utc).isoformat()
    rows = []
    for container_id in ids:
        # Inspect individually: do not expose environment variables or credentials.
        raw = subprocess.check_output([
            'docker', 'inspect', '--format',
            '{{json .Name}}\n{{json .Config.Image}}\n{{json .Image}}\n'
            '{{json .State.Status}}\n{{json .Config.Labels}}', container_id
        ], timeout=15).decode().splitlines()
        name, image, digest, state, labels = [json.loads(v) for v in raw]
        name = name.lstrip('/')
        labels = labels or {}
        service = labels.get('com.docker.compose.service', '')
        if 'intruoyi' not in (name + ' ' + image).lower():
            continue
        if not any(role in (name + ' ' + image + ' ' + service).lower()
                   for role in ('backend', 'frontend')):
            continue
        rows.append(dict(container=name, image=image, imageId=digest, state=state,
                         project=labels.get('com.docker.compose.project', ''),
                         service=service, containerId=container_id))
    if not rows:
        raise RuntimeError('NO_RUNNING_INTRUOYI_FRONTEND_OR_BACKEND')
    return dict(observedAt=observed, readOnly=True, databaseQueried=False,
                scope='All running IntRuoyi frontend/backend containers; no automatic active-instance selection',
                containers=sorted(rows, key=lambda row: row['container']))


def query_registered(profile):
    """Only the explicitly registered main instances; no guess based on names/latest."""
    components = {}
    for role in ('frontend', 'backend', 'database'):
        item = json.loads(subprocess.check_output(['docker', 'inspect', profile[role]], timeout=15))[0]
        components[role] = dict(container=item['Name'].lstrip('/'), image=item['Config']['Image'],
                                imageId=item['Image'], state=item['State']['Status'])
    if any(x['state'] != 'running' for x in components.values()):
        raise RuntimeError('REGISTERED_INSTANCE_NOT_RUNNING')
    shell = ('if [ -n "$MYSQL_ROOT_PASSWORD_FILE" ]; then '
             'export MYSQL_PWD="$(cat "$MYSQL_ROOT_PASSWORD_FILE")"; '
             'else export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; fi; '
             'exec mysql -uroot --batch --skip-column-names')
    sql = ("SELECT VERSION(); SELECT COUNT(*) FROM information_schema.tables "
           "WHERE table_schema='ruoyi-vue-pro';\n")
    p = subprocess.run(['docker', 'exec', '-i', profile['database'], 'sh', '-c', shell],
                       input=sql.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
    if p.returncode:
        raise RuntimeError('MYSQL_VERSION_QUERY_FAILED')
    version, tables = p.stdout.decode().strip().splitlines()
    return dict(host=profile['host'], name=profile['name'], entryUrl=profile['entryUrl'],
                observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(), readOnly=True,
                components=components, mysqlVersion=version, database='ruoyi-vue-pro',
                tableCount=int(tables), businessRowsCompared=False)


if __name__ == '__main__':
    print(json.dumps(query(), ensure_ascii=False, indent=2))
