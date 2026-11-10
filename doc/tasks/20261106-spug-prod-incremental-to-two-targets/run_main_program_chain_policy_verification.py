"""Local evidence writer and pytest recorder. No build, deployment or network.

The full entry requires a clean committed release checkout and frozen packages.
run_suite is also used with small real subprocess protocol tests; that alone is
not a product coverage report.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import io
import tarfile

from main_program_chain_policy_evidence import (MODULES, canonical, need, pytest_command as command_arguments, suite_files)


def stamp(): return datetime.now(timezone.utc).isoformat()


def physical(path):
    path = Path(path).resolve();before = path.stat();raw = path.read_bytes();after = path.stat()
    need(not path.is_symlink() and path.is_file() and
         (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns) ==
         (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns),'RUNNER_INPUT_CHANGED')
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def write(path, value, *, raw=False):
    path = Path(path)
    with path.open('xb') as output:output.write(value if raw else canonical(value))
    return physical(path)


_session = None
_nodes = []
_events = {}


def pytest_configure(config):
    global _session,_nodes,_events
    ref = os.environ.get('CHAIN_POLICY_RUN_COMMAND')
    if not ref: return
    _session = json.loads(Path(ref).read_bytes());_nodes = [];_events = {}


def pytest_collection_modifyitems(items):
    if _session is None:return
    for item in items:item.user_properties.append(('chain_node_id',item.nodeid))


def pytest_collection_finish(session):
    global _nodes
    if _session is None:return
    _nodes = [item.nodeid for item in session.items]
    write(Path(os.environ['CHAIN_POLICY_RUN_COMMAND']).parent/'collection.json',dict(
        suiteId=os.environ['CHAIN_POLICY_SUITE'],mode=_session['mode'],testFiles=_session['testFiles'],nodeIds=_nodes))


def pytest_runtest_logreport(report):
    if _session is None:return
    _events.setdefault(report.nodeid,{'nodeId':report.nodeid})[report.when] = report.outcome


def pytest_sessionfinish(session, exitstatus):
    if _session is None:return
    modules = {}
    for member in MODULES:
        module = sys.modules.get(Path(member).stem)
        if module is not None and getattr(module,'__file__',None):modules[member] = physical(module.__file__)
    write(Path(os.environ['CHAIN_POLICY_RUN_COMMAND']).parent/'events.json',dict(
        nodeResults=list(_events.values()),loadedModulePins=modules,exitStatus=int(exitstatus)))


def runtime_files(root, members):
    from main_program_chain_policy_evidence import file_map
    actual = {}
    for name in members:
        path = Path(root)/name;before = physical(path);raw = path.read_bytes()
        need(physical(path) == before,'RUNTIME_INPUT_CHANGED');actual[name] = raw
    return file_map(actual)


def run_suite(*, source_root, output, suite_id, mode, source_commit, input_pin, runner_path, timeout, source_input_pin=None):
    source_root = Path(source_root).resolve();output = Path(output).resolve()
    need(not output.exists(),'RUN_OUTPUT_EXISTS');output.mkdir(parents=True)
    files = suite_files(suite_id,mode);runner_pin = physical(runner_path)
    from main_program_chain_policy_evidence import archive_files
    source_input_pin = input_pin if mode == 'source' and source_input_pin is None else source_input_pin
    need(source_input_pin is not None,'SOURCE_INPUT_REQUIRED')
    before = [physical(input_pin['path']),runner_pin];need(before[0] == input_pin,'RUN_INPUT_CHANGED')
    if source_input_pin != input_pin:
        need(physical(source_input_pin['path']) == source_input_pin,'SOURCE_INPUT_CHANGED');before.append(source_input_pin)
    source_files = archive_files(Path(source_input_pin['path']).read_bytes())
    started = stamp();argv = command_arguments(sys.executable,source_root,files,output)
    command_pin = write(output/'command.json',dict(argv=argv,cwd=str(source_root),mode=mode,
        sourceCommit=source_commit,inputPin=input_pin,testFiles=files,startedAt=started))
    env = dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
        CHAIN_POLICY_RUN_COMMAND=command_pin['path'],CHAIN_POLICY_SUITE=suite_id,
        CHAIN_POLICY_PACKAGE_ROOT=str(output/'package'),CHAIN_POLICY_VARIANT=mode,
        CHAIN_POLICY_PACKAGE_ARCHIVE=input_pin['path'])
    env.pop('PYTEST_ADDOPTS',None);env.pop('PYTEST_PLUGINS',None)
    env['PYTHONPATH'] = os.pathsep.join([str(Path(runner_path).parent),str(source_root/'scripts/tests'),
        os.environ.get('PYTHONPATH','')])
    if mode != 'source':
        members = archive_files(Path(input_pin['path']).read_bytes(),package=True)
        for name,raw in members.items():
            path = output/'package'/name;path.parent.mkdir(parents=True,exist_ok=True);write(path,raw,raw=True)
    else:members = source_files
    module_root = source_root if mode == 'source' else output/'package'
    scope = dict(schemaVersion='MainProgramExecutionInputRoot/v1',sourceRoot=str(source_root),moduleRoot=str(module_root),
        sourceInputPin=source_input_pin,moduleInputPin=input_pin)
    runtime_before = dict(source=runtime_files(source_root,source_files),program=runtime_files(module_root,members))
    timed_out = False
    try:
        process = subprocess.run(argv,cwd=source_root,env=env,capture_output=True,timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        stdout,stderr,code = process.stdout,process.stderr,process.returncode
    except subprocess.TimeoutExpired as error:
        stdout,stderr,code,timed_out = error.stdout or b'',error.stderr or b'',None,True
    stdout_pin = write(output/'stdout.log',stdout,raw=True);stderr_pin = write(output/'stderr.log',stderr,raw=True)
    terminal = write(output/'exit.json',dict(commandPin=command_pin,inputPin=input_pin,startedAt=started,
        finishedAt=stamp(),exitCode=code,timedOut=timed_out,inputPinsBefore=before,
        inputPinsAfter=[physical(p['path']) for p in before],runtimeInputPinsBefore=runtime_before,
        runtimeInputPinsAfter=dict(source=runtime_files(source_root,source_files),program=runtime_files(module_root,members))))
    result_pin = None;collection_pin = None;modules = {}
    if (output/'events.json').exists() and (output/'collection.json').exists() and (output/'junit.xml').exists():
        events = json.loads((output/'events.json').read_bytes());collection_pin = physical(output/'collection.json')
        modules = events['loadedModulePins'];rows = events['nodeResults']
        import xml.etree.ElementTree as ET
        xml = ET.parse(output/'junit.xml');suites = xml.findall('.//testsuite')
        result_pin = write(output/'result.json',dict(suiteId=suite_id,mode=mode,
            tests=sum(int(s.get('tests','0')) for s in suites),
            failures=sum(int(s.get('failures','0')) for s in suites),errors=sum(int(s.get('errors','0')) for s in suites),
            skipped=sum(int(s.get('skipped','0')) for s in suites),nodeResults=rows,junitPin=physical(output/'junit.xml')))
    return dict(suiteId=suite_id,mode=mode,commandPin=command_pin,inputPin=input_pin,collectionPin=collection_pin,
        resultPin=result_pin,stdoutPin=stdout_pin,stderrPin=stderr_pin,exitReceiptPin=terminal,loadedModulePins=modules,
        executionInputRoot=scope)


def capture_snapshot(source_root, output, source_commit, build_pin):
    from main_program_chain_policy_evidence import committed_files, digest, git
    source_root = Path(source_root).resolve();output = Path(output).resolve()
    need(not output.is_relative_to(source_root) and not output.exists(),'SNAPSHOT_OUTPUT_INVALID')
    started = stamp();files = committed_files(source_root,source_commit);output.mkdir(parents=True)
    before = {name:dict(bytes=len(raw),sha256=digest(raw)) for name,raw in files.items()}
    head = write(output/'git-head.log',git(source_root,'rev-parse','HEAD'),raw=True)
    status = write(output/'git-status.log',git(source_root,'status','--porcelain=v1','--untracked-files=all'),raw=True)
    archive_path = output/'source.tgz'
    with archive_path.open('xb') as handle:
        with tarfile.open(fileobj=handle,mode='w:gz') as archive:
            for name,raw in files.items():
                info = tarfile.TarInfo(name);info.size = len(raw);info.mode = 0o600
                archive.addfile(info,io.BytesIO(raw))
    after_files = committed_files(source_root,source_commit)
    after = {name:dict(bytes=len(raw),sha256=digest(raw)) for name,raw in after_files.items()}
    need(before == after,'SOURCE_CHANGED_DURING_SNAPSHOT')
    terminal = write(output/'capture-exit.json',dict(sourceCommit=source_commit,sourceRoot=str(source_root),
        startedAt=started,finishedAt=stamp(),exitCode=0,timedOut=False,inputPinsBefore=before,inputPinsAfter=after,
        gitHeadPin=head,gitStatusPin=status))
    return dict(schemaVersion='MainProgramChainPolicySourceSnapshot/v1',sourceCommit=source_commit,buildPin=build_pin,
        archivePin=physical(archive_path),filePins=before,gitHeadPin=head,gitStatusPin=status,captureReceiptPin=terminal)


def run_verification(*, source_root, output, source_commit, build_pin, delta_pin, delta, snapshot_pin, snapshot,
                     evidence_root_mapping, timeout=1800):
    """Execute exactly the approved four suites over already frozen inputs.

    Returns an honest PASS/FAIL report, retaining failed original commands. It
    never writes coverage, modifies a build, retries a test or changes a package.
    The caller persists the returned report exclusively and then invokes the
    independent coverage reader before preparing an upgrade.
    """
    from main_program_chain_policy_evidence import (PROFILE, REQUIRED_RUNS, EvidenceReader, committed_files,
        validate_verification)
    source_root = Path(source_root).resolve();output = Path(output).resolve()
    need(not output.exists() and not output.is_relative_to(source_root),'VERIFICATION_OUTPUT_INVALID')
    source_files = committed_files(source_root,source_commit)
    need(snapshot['sourceCommit'] == source_commit and snapshot['buildPin'] == build_pin and
         delta['sourceCommit'] == source_commit and delta['buildPin'] == build_pin and
         delta['sourceSnapshotPin'] == snapshot_pin,'VERIFICATION_INPUT_BINDING_CHANGED')
    runner_path = source_root/'doc/tasks/20261106-spug-prod-incremental-to-two-targets/run_main_program_chain_policy_verification.py'
    need(Path(__file__).resolve() == runner_path and physical(runner_path)['sha256'] ==
         hashlib.sha256(source_files[str(runner_path.relative_to(source_root)).replace('\\','/')]).hexdigest(),
         'RUNNER_NOT_COMMITTED_INPUT')
    output.mkdir(parents=True);runs = []
    for suite,mode in REQUIRED_RUNS:
        selected = snapshot['archivePin'] if mode == 'source' else next(r['packagePin'] for r in delta['packages'] if r['variant'] == mode)
        run = run_suite(source_root=source_root,output=output/(suite+'-'+mode),suite_id=suite,mode=mode,
            source_commit=source_commit,input_pin=selected,source_input_pin=snapshot['archivePin'],
            runner_path=runner_path,timeout=timeout)
        runs.append(run)
        terminal = json.loads(Path(run['exitReceiptPin']['path']).read_bytes())
        if terminal['timedOut'] or terminal['exitCode'] != 0:break
    report = dict(schemaVersion='MainProgramChainPolicyVerification/v1',status='FAIL',profile=PROFILE,
        sourceCommit=source_commit,buildPin=build_pin,packageDeltaPin=delta_pin,sourceSnapshotPin=snapshot_pin,
        runnerPin=physical(runner_path),runs=runs,failedAttemptPins=[],evidenceRootMapping=evidence_root_mapping)
    # Validate against actual originals before emitting PASS. This reader uses
    # current runtime paths; the host later consumes the explicit mapping.
    if len(runs) == len(REQUIRED_RUNS):
        from main_program_chain_policy_evidence import archive_files
        packages = {row['variant']:archive_files(Path(row['packagePin']['path']).read_bytes(),package=True) for row in delta['packages']}
        reader = EvidenceReader(output,physical,roots=[source_root,Path(snapshot['archivePin']['path']).parent,
            *(Path(row['packagePin']['path']).parent for row in delta['packages'])])
        candidate = dict(report,status='PASS')
        try:
            validate_verification(reader,candidate,inputs=dict(sourceCommit=source_commit,buildPin=build_pin),
                delta=delta,delta_pin=delta_pin,snapshot=snapshot,source_files=source_files,packages=packages,failed_refs=[])
            reader.finish()
        except (ValueError,KeyError,TypeError):
            # Failed evidence is retained; the exception is not a success path.
            write(output/'verification-report.json',report)
            raise
        need(committed_files(source_root,source_commit) == source_files,'SOURCE_CHANGED_DURING_VERIFICATION')
        report = candidate
    write(output/'verification-report.json',report)
    return report


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--source-commit',required=True);parser.add_argument('--inputs',required=True)
    options = parser.parse_args()
    value = json.loads(Path(options.inputs).read_bytes())
    need(set(value) == {'buildPin','packageDeltaPin','packageDelta','sourceSnapshotPin','sourceSnapshot','evidenceRootMapping'},
         'VERIFICATION_REQUEST_INVALID')
    report = run_verification(source_root=options.source_root,output=options.output,source_commit=options.source_commit,
        build_pin=value['buildPin'],delta_pin=value['packageDeltaPin'],delta=value['packageDelta'],
        snapshot_pin=value['sourceSnapshotPin'],snapshot=value['sourceSnapshot'],evidence_root_mapping=value['evidenceRootMapping'])
    print(json.dumps(dict(status=report['status'],sourceCommit=report['sourceCommit'],runCount=len(report['runs']))))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':sys.exit(main())
