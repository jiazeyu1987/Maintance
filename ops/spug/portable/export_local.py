"""Export a private, offline handoff archive. Never add its output to Git."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tarfile
import urllib.request
from contextlib import closing


def run(args, output=None):
    if output:
        with Path(output).open('wb') as stream:
            subprocess.run(args, stdout=stream, stderr=subprocess.PIPE, check=True)
    else:
        subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--inputs', required=True)
    p.add_argument('--repository', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--config', required=True)
    a = p.parse_args()
    root = Path(a.inputs).resolve()
    out = Path(a.output).resolve()
    out.mkdir(exist_ok=False)
    c = json.loads(Path(a.config).read_text('utf-8-sig'))
    req = urllib.request.Request('http://127.0.0.1:'+str(c['port'])+'/state', headers={'X-Release-Key': c['bridgeKey']})
    http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with http.open(req, timeout=60) as response:
        state = json.load(response)
    if any(j['status'] in ('running', 'queued') for j in state['jobs']):
        raise RuntimeError('Finish active jobs before exporting')
    shutil.copytree(root/'private', out/'private')
    (out/'private/executor.original.private.json').write_text(json.dumps(c,ensure_ascii=False),encoding='utf-8')
    shutil.copytree(root/'source', out/'source', ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copytree(Path(__file__).parent,out/'portable',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copyfile(Path(__file__).parent/'README.md',out/'README.md')
    cli=Path(c['loginVerification']['cliPath'])
    if cli.name!='playwright-cli.js' or cli.parents[2].name!='node_modules':
        raise RuntimeError('Explicit installed Playwright CLI node_modules directory required')
    shutil.copytree(cli.parents[2],out/'tools/playwright/node_modules')
    source = Path(c['stateDir'])
    with closing(sqlite3.connect((source/'state.sqlite3').as_uri()+'?mode=ro', uri=True)) as src:
        with closing(sqlite3.connect(out/'private/state.snapshot.sqlite3')) as dst:
            src.backup(dst)
    with closing(sqlite3.connect(out/'private/state.snapshot.sqlite3')) as db:
        original_state=db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0]
    history=json.loads(original_state)
    keep={v.get('releaseTag') for v in history['environments'].values() if v.get('releaseTag')}
    prod=history['environments']['prod']['releaseTag']
    previous=next((j.get('originState',{}).get('releaseTag') for j in history['jobs']
                   if j['action']=='promote-prod' and j.get('releaseTag')==prod and j.get('originState')),None)
    if not previous:
        raise RuntimeError('Previous stable production version is not identified')
    keep.add(previous)
    (out/'included-versions.json').write_text(json.dumps(sorted(keep)),encoding='utf-8')
    print('Exporting current and previous stable packages; retaining metadata for other history', flush=True)
    with tarfile.open(out/'release-state.tar.gz', 'w:gz', compresslevel=1) as tar:
        for package in history['packages']:
            folder=Path(package['directory'])
            tag=package['releaseTag']
            tar.add(folder/'manifest.json',arcname='packages/'+tag+'/manifest.json')
            if tag in keep:
                tar.add(folder/'release.tar',arcname='packages/'+tag+'/release.tar')
        for name in ('frontend-patches', 'db-password.txt', 'technical-evidence', 'restore-drill-evidence'):
            target = source/name
            if target.exists():
                tar.add(target, arcname=name)
    print('Exporting Spug database and application volumes', flush=True)
    info=json.loads(subprocess.check_output(['docker','inspect','intruoyi-spug-db-1']))[0]
    env=dict(item.split('=',1) for item in info['Config']['Env'])
    (out/'private/compose.env').write_text('SPUG_DB_PASSWORD='+env['MYSQL_PASSWORD']+'\nSPUG_DB_ROOT_PASSWORD='+env['MYSQL_ROOT_PASSWORD']+'\n',encoding='utf-8')
    run(['docker', 'exec', 'intruoyi-spug-db-1', 'sh', '-c',
         'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysqldump -uroot --single-transaction --routines --events spug'], out/'private/spug.sql')
    for name, directory in [('spug-data','/data/spug'), ('spug-records','/var/lib/intruoyi-spug')]:
        run(['docker','exec','intruoyi-spug-spug-1','tar','czf','-','-C',directory,'.'], out/(name+'.tar.gz'))
    # Preserve installed nginx/supervisor configuration; volume content is exported above.
    run(['docker','commit','--pause=false','intruoyi-spug-spug-1','intruoyi-spug-portable:20261030'])
    run(['docker','tag','mariadb@sha256:456709ab146585d6189da05669b84384518baecd83670c9e5221f8c20a47cf1e','intruoyi-spug-portable-db:20261030'])
    images = ['intruoyi-spug-portable:20261030',
              'intruoyi-spug-portable-db:20261030',
              *c['localRuntimeImages'].values()]
    print('Exporting pinned Spug and build images', flush=True)
    run(['docker','save','-o',str(out/'docker-images.tar'),*images])
    revision={'commit':subprocess.check_output(['git','-C',a.repository,'rev-parse','HEAD'],text=True).strip(),
              'origin':subprocess.check_output(['git','-C',a.repository,'remote','get-url','origin'],text=True).strip()}
    if revision['origin']!='https://github.com/jiazeyu1987/IntRuoyiAll.git':
        raise RuntimeError('Unexpected source origin; review before distributing')
    (out/'source-revision.json').write_text(json.dumps(revision,indent=2),encoding='utf-8')
    with closing(sqlite3.connect((source/'state.sqlite3').as_uri()+'?mode=ro',uri=True)) as db:
        if json.loads(original_state)!=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0]):
            raise RuntimeError('Release history changed during export; create a fresh handoff')
    manifest = {'format':1, 'scope':'intruoyi', 'sourceStateDir':str(source),
                'files':{str(f.relative_to(out)).replace('\\','/'):sha(f) for f in out.rglob('*') if f.is_file()}}
    (out/'integrity.json').write_text(json.dumps(manifest,indent=2), encoding='utf-8')
    print(json.dumps({'output':str(out),'files':len(manifest['files']), 'readyForImportValidation':True}))


if __name__ == '__main__':
    main()
