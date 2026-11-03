from pathlib import Path
import ast,hashlib,json,subprocess,sys
repo=Path(__file__).resolve().parents[3]
root=Path('C:/SpugHandoff/release')
private=root/'private/backend-patch-full-release-20261102/runtime-stopped-patch'
candidate=private/'candidate-source/ops/spug/release-center'
live=root/'source/ops/spug/release-center'
names=['intruoyi_runtime_agent.py','intruoyi_executor.py']

def committed(ref,name):
    return subprocess.check_output(['git','-C',str(repo),'show',ref+':ops/spug/release-center/'+name]).decode('utf-8').replace('\r\n','\n')

def installed_contract(source,name):
    # These read-only dashboard features were already absent from the deployed
    # executor before this task. Preserve that exact installed feature boundary.
    omitted={'intruoyi_runtime_agent.py':{'read_versions'},'intruoyi_executor.py':{'current_versions','database_versions'}}[name]
    lines=source.splitlines(True)
    nodes=[n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.FunctionDef) and n.name in omitted]
    assert {n.name for n in nodes}==omitted
    for node in sorted(nodes,key=lambda n:n.lineno,reverse=True):
        start=node.lineno-1
        del lines[start:node.end_lineno]
        while start<len(lines) and not lines[start].strip(): del lines[start]
    source=''.join(lines)
    if name=='intruoyi_runtime_agent.py':
        source=source.replace("    if action == 'read-versions':\n        return read_versions(profile)\n    if action == 'read-database':\n        from database_versions import read_database\n        return read_database(remote, profile)\n",'')
    else:
        source=source.replace('nasPackageRetry=True,\n                                                 currentVersions=True, databaseVersions=True))','nasPackageRetry=True))')
    return source

if sys.argv[1]=='prepare':
    values={}
    for name in names:
        before=installed_contract(committed('af8ea76',name),name)
        assert (live/name).read_text('utf-8')==before,'Unexpected installed boundary: '+name
        values[name]=installed_contract(committed('a93fe3e',name),name)
    candidate.mkdir(parents=True,exist_ok=False)
    for name,value in values.items(): (candidate/name).write_text(value,encoding='utf-8',newline='\n')
    rows=[dict(name=n,beforeSha256=hashlib.sha256((live/n).read_bytes()).hexdigest(),afterSha256=hashlib.sha256((candidate/n).read_bytes()).hexdigest()) for n in names]
    (private/'code-update-plan.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    print(json.dumps(dict(status='prepared',files=len(names),sourceCommit='a93fe3e',existingFeatureBoundaryPreserved=True)))
else:
    source=(repo/'doc/tasks/20261102-spug-backend-jar-patch/apply-runtime-update.py').read_text('utf-8')
    source=source.replace("private=root/'private/backend-jar-patch-20261102'",'private=Path('+repr(private.as_posix())+')')
    source=source.replace("candidate=private/'candidate-source/ops/spug/release-center'",'candidate=Path('+repr(candidate.as_posix())+')')
    exec(compile(source,'reviewed-idle-runtime-installer.py','exec'))
