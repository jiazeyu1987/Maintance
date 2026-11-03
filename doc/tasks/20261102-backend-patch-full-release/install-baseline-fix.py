"""Reuse the reviewed idle-process installer for one committed code-only fix."""
from pathlib import Path
import hashlib,json,subprocess,sys

repo=Path(__file__).resolve().parents[3]
private=Path('C:/SpugHandoff/release/private/backend-patch-full-release-20261102')
live=Path('C:/SpugHandoff/release/source/ops/spug/release-center')
candidate=repo/'ops/spug/release-center'
name='backend_patch_agent.py'
before_ref='b8c3c70'
if len(sys.argv)>2 and sys.argv[2]=='runtime-identity':
    private=private/'runtime-identity'
    name='backend_patch_build.py'
if len(sys.argv)>2 and sys.argv[2]=='runtime-reference':
    private=private/'runtime-reference'
    name='backend_patch_build.py'
    before_ref='eada6d8'
if len(sys.argv)>2 and sys.argv[2]=='runtime-history':
    private=private/'runtime-history'
    name='frontend_patch.py'
if len(sys.argv)>2 and sys.argv[2]=='runtime-restore':
    private=private/'runtime-restore'
    name='backend_patch_agent.py'
    before_ref='fa4642a'
if len(sys.argv)>2 and sys.argv[2]=='runtime-ascii':
    private=private/'runtime-ascii'
    name='intruoyi_runtime.py'
if len(sys.argv)>2 and sys.argv[2]=='runtime-interruption':
    private=private/'runtime-interruption'
    name='interruption.py'
if len(sys.argv)>2 and sys.argv[2]=='runtime-catalog':
    private=private/'runtime-catalog'
    name='executor.py'
if len(sys.argv)>2 and sys.argv[2]=='runtime-release-info':
    private=private/'runtime-release-info'
    name='intruoyi_build.py'
if len(sys.argv)>2 and sys.argv[2]=='runtime-untouched-restore':
    private=private/'runtime-untouched-restore'
    name='backend_patch_agent.py'
    before_ref='3b5aa54'
def normalized(data):return data.decode('utf-8').replace('\r\n','\n')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def git_file(ref):
    return subprocess.check_output(['git','-C',str(repo),'show',ref+':ops/spug/release-center/'+name])
if sys.argv[1]=='prepare':
    expected=normalized(git_file(before_ref))
    if len(sys.argv)>2 and sys.argv[2]=='runtime-catalog':
        fragment=("                if self.command == 'GET' and self.path == '/current-versions':\n"
                  "                    require(callable(getattr(executor, 'current_versions', None)), 'Current version inspection is not supported')\n"
                  "                    return self.reply(200, executor.current_versions())\n"
                  "                if self.command == 'GET' and self.path == '/database-versions':\n"
                  "                    require(callable(getattr(executor, 'database_versions', None)), 'Database inspection is not supported')\n"
                  "                    return self.reply(200, executor.database_versions())\n")
        assert expected.count(fragment)==1
        expected=expected.replace(fragment,'')
        assert normalized((live/name).read_bytes())==expected,'Unknown installed catalog variant'
        before="'log', '-20', '--format=%H%x09%s'"
        after="'log', '--all', '--date-order', '-20', '--format=%H%x09%s'"
        assert expected.count(before)==1 and after in normalized(git_file('HEAD'))
        updated=expected.replace(before,after)
        private.mkdir(exist_ok=False);candidate=private/'candidate-code';candidate.mkdir()
        (candidate/name).write_text(updated,encoding='utf-8')
    elif len(sys.argv)>2 and sys.argv[2]=='runtime-ascii':
        # Preserve the previously installed variant: database-version UI
        # dependencies are deliberately absent from this running installation.
        fragments=[
            "        database_versions = (self.sources / 'database_versions.py').read_text('utf-8')\n",
            "                  '_database=types.ModuleType(\"database_versions\")\\n'\n                  'sys.modules[\"database_versions\"]=_database\\n'\n                  'exec(compile(' + repr(database_versions) + ',\"database_versions.py\",\"exec\"),_database.__dict__)\\n'\n",
            "                              else 45 if action == 'read-database'\n                              else 15 if action == 'read-versions'\n"]
        for fragment in fragments:
            assert expected.count(fragment)==1,'Unknown installed variant'
            expected=expected.replace(fragment,'')
        assert normalized((live/name).read_bytes())==expected,'Unexpected live source'
        committed=normalized(git_file('HEAD'))
        helper=committed[committed.index('def ssh_source_bytes('):committed.index('class Runtime:')]
        updated=expected.replace('class Runtime:',helper+'class Runtime:')
        assert updated.count("input=source.encode('utf-8')")==1
        updated=updated.replace("input=source.encode('utf-8')",'input=ssh_source_bytes(source)')
        private.mkdir(exist_ok=False)
        candidate=private/'candidate-code';candidate.mkdir()
        (candidate/name).write_text(updated,encoding='utf-8')
    else:
        assert normalized((live/name).read_bytes())==expected, 'Unexpected live source'
        assert normalized((candidate/name).read_bytes())==normalized(git_file('HEAD')), 'Uncommitted candidate'
        private.mkdir(exist_ok=False)
    (private/'code-update-plan.json').write_text(json.dumps([dict(name=name,beforeSha256=sha(live/name),
        afterSha256=sha(candidate/name))],indent=2),encoding='utf-8')
    print(json.dumps(dict(status='prepared',files=1)))
else:
    if len(sys.argv)>2 and sys.argv[2] in ('runtime-ascii','runtime-catalog'):candidate=private/'candidate-code'
    original=(repo/'doc/tasks/20261102-spug-backend-jar-patch/apply-runtime-update.py').read_text('utf-8')
    original=original.replace("private=root/'private/backend-jar-patch-20261102'",'private=Path('+repr(private.as_posix())+')')
    original=original.replace("candidate=private/'candidate-source/ops/spug/release-center'",'candidate=Path('+repr(candidate.as_posix())+')')
    exec(compile(original,'reviewed-idle-runtime-installer.py','exec'))
