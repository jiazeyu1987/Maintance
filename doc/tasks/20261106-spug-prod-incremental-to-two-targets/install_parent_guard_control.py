"""Install a new committed source generation under the original source lock."""
import argparse
import base64
import datetime
import hashlib
import json
from pathlib import Path

from common import PRIVATE, SOURCE, TASK, remote, write
from install_source_control import SCRIPT as ORIGINAL_SCRIPT


def replace_once(text, before, after):
    assert text.count(before) == 1, 'INSTALLER_CONTEXT_CHANGED'
    return text.replace(before, after)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--commit', required=True)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    output = TASK / 'source-control-parent-installation.json'
    assert not output.exists(), 'INSTALLATION_ALREADY_RECORDED'
    build = json.loads((TASK / 'release-build-verification.json').read_text(encoding='utf-8'))
    assert build['status'] == 'PASS' and build['targetCommit'] == args.commit and build['fileCount'] == 127
    verified = json.loads((TASK / 'parent-guard-build-program-verification.json').read_text(encoding='utf-8'))
    assert verified['status'] == 'PASS' and verified['sourceCommit'] == args.commit
    assert verified['fileManifestSha256'] == build['fileManifestSha256'] and verified['allProgramASTsEqual']
    for name in ('parent-guard-red.json', 'parent-guard-red-init.json', 'parent-guard-green-4.json', 'parent-guard-regression.json'):
        report = json.loads((TASK / name).read_text(encoding='utf-8'))
        assert report['expectedResultObserved'] and report['containerRemoved']
    regression = json.loads((TASK / 'linux-affected-regression.json').read_text(encoding='utf-8'))
    assert regression['status'] == 'PASS' and regression['allFiveTestsActuallyExecuted']
    final_regression = json.loads((TASK / 'linux-parent-final-regression.json').read_text(encoding='utf-8'))
    assert final_regression['status'] == 'PASS' and final_regression['allTestsActuallyExecuted']
    health = json.loads((TASK / 'parent-install-pre-57.json').read_text(encoding='utf-8'))
    assert health['http']['backend']['status'] == 'UP' and health['http']['frontend']['httpStatus'] == 200
    assert not health['activeReservation'] and all(r['running'] for r in health['roles'])
    assert (datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(health['observedAt'])).total_seconds() < 900
    old = json.loads((TASK / 'source-control-installation.json').read_text(encoding='utf-8'))
    assert old['status'] == 'PASS' and old['sourceCommit'].startswith('6319024')
    package = Path(build['worktree']).parent / ('package-' + args.commit[:7]) / 'backup-restore-standard.tgz'
    raw = package.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == build['packageSha256']
    pins = json.loads((TASK / 'registered-binlog-tool-restored.json').read_text(encoding='utf-8'))['failedOriginalPins']
    retained = json.loads((PRIVATE / 'failed-365-all-pins.private.json').read_text(encoding='utf-8'))
    assert retained['status'] == 'PASS'
    pins += retained['pins']
    script = ORIGINAL_SCRIPT
    script = replace_once(script, "generation='incremental-'+COMMIT[:7]", "generation='incremental-parent-'+COMMIT[:7]")
    script = replace_once(script, "/(generation+'.conf')", "/('zz-'+generation+'.conf')")
    script = replace_once(script, "oldpath=root/'configuration/control-postboot-20261105.json'", "oldpath=pathlib.Path(CURRENT_CONTROL_PATH)")
    script = replace_once(script, "oldengine=root/'engine';oldversion=", "oldengine=pathlib.Path(CURRENT_ENGINE);oldversion=")
    script = replace_once(script, "oldpid>1,'OLD_CONTROL_NOT_RUNNING')", "oldpid==CURRENT_CONTROL_PID,'OLD_CONTROL_PID_CHANGED')\nneed(str(oldpath).encode() in (pathlib.Path('/proc')/str(oldpid)/'cmdline').read_bytes(),'OLD_CONTROL_NOT_ACTIVE')")
    verify_failures = """import stat
for retained in FAILED_PINS:
 path=pathlib.Path(retained['path']);before_stat=path.lstat();sha=hashlib.sha256();size=0
 def retained_identity(info):return (info.st_dev,info.st_ino,info.st_mode,info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
 need(path.resolve()==path and stat.S_ISREG(before_stat.st_mode) and before_stat.st_nlink==1,'FAILED_ORIGINAL_PATH_CHANGED')
 with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK),'rb') as stream:
  need(retained_identity(os.fstat(stream.fileno()))==retained_identity(before_stat),'FAILED_ORIGINAL_CHANGED')
  while True:
   chunk=stream.read(1024*1024)
   if not chunk:break
   sha.update(chunk);size+=len(chunk)
  need(retained_identity(os.fstat(stream.fileno()))==retained_identity(before_stat),'FAILED_ORIGINAL_CHANGED')
 need(retained_identity(path.lstat())==retained_identity(before_stat) and size==retained['bytes'] and sha.hexdigest()==retained['sha256'],'FAILED_ORIGINAL_CHANGED')
"""
    script = replace_once(script, "before=snapshot();fstab=pin('/etc/fstab');beforemounts=mounts()\n", verify_failures + "before=snapshot();fstab=pin('/etc/fstab');beforemounts=mounts()\n")
    script = replace_once(script, "with opener.open(urllib.request.Request(url,headers=headers),timeout=90) as response:\n need(response.status==200,'SOURCE_SELECTIONS_UNAVAILABLE');selections=json.load(response)\n", """import urllib.error
for readiness_attempt in range(1, 22):
 try:
  with opener.open(urllib.request.Request(url,headers=headers),timeout=90) as response:
   need(response.status==200,'SOURCE_SELECTIONS_UNAVAILABLE');selections=json.load(response)
  break
 except urllib.error.URLError as error:
  if not isinstance(error.reason,ConnectionRefusedError) or readiness_attempt==21:raise
  time.sleep(2)
""")
    script = replace_once(script, "need(snapshot()==before,'ORIGINAL_DOCKER_RUNTIME_CHANGED')\n", verify_failures + "need(snapshot()==before,'ORIGINAL_DOCKER_RUNTIME_CHANGED')\n")
    script = replace_once(script, "out=dict(status='PASS',", "application=next(a for a in selections['applications'] if a['sourceConfigRef']==SOURCE)\nneed(application['fullReady'] and not application['fullErrorCode'] and not application['historyErrorCode'] and 'smallapp-7fec29a3e132463096aec915c08acab3' in application['parentChainRefs'],'SOURCE_PARENT_NOT_ADMITTED')\nout=dict(status='PASS',")
    script = replace_once(script, "write_new(root/'configuration'/('installation-'+generation+'.json'),canonical(out));", "out.update(previousGeneration=CURRENT_ENGINE,failedOriginalFilesPreserved=len(FAILED_PINS),readinessAttempts=readiness_attempt)\nwrite_new(root/'configuration'/('installation-'+generation+'.json'),canonical(out));")
    variables = dict(COMMIT=args.commit, SOURCE=SOURCE,
                     OLD_CONTROL_PIN=old['controlConfigurationPin'], PACKAGE_SHA=build['packageSha256'],
                     PACKAGE=base64.b64encode(raw).decode(), CURRENT_ENGINE=old['engine'],
                     CURRENT_CONTROL_PATH=old['controlConfigurationPin']['path'], CURRENT_CONTROL_PID=old['pid'],
                     FAILED_PINS=pins)
    payload = '\n'.join(key + '=' + repr(value) for key, value in variables.items()) + '\n' + script
    compile(payload, '<parent-guard-source-installation>', 'exec')
    if args.prepare_only:
        report = dict(status='PASS', preparedOnly=True, sourceCommit=args.commit,
                      previousPid=old['pid'], retainedFiles=len(pins), packageSha256=build['packageSha256'],
                      remoteScriptSha256=hashlib.sha256(payload.encode()).hexdigest(), remoteWrites=False)
        write(TASK / 'parent-installation-preflight.json', report)
        print(json.dumps(report))
        raise SystemExit(0)
    value = remote('172.30.30.57', payload, 240)
    write(PRIVATE / 'source-control-parent-installation.private.json', value)
    public = {key: val for key, val in value.items() if key != 'sourceSelections'}
    write(output, public)
    print(json.dumps(public))
