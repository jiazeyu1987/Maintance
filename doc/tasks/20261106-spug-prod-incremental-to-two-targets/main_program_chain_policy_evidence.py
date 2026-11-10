"""Pinned evidence for the reviewed incremental-chain admission change.

This module never builds, tests, installs or contacts a server. Old evidence
versions retain their original validators in the callers.
"""
import ast
import hashlib
import io
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import tarfile
import subprocess
from datetime import datetime
import xml.etree.ElementTree as ET

PROFILE = 'incremental-chain-policy-admission/v1'
DELTA_SCHEMA = 'MainProgramChainPolicyPackageDelta/v1'
COVERAGE_SCHEMA = 'MainProgramControlCoverage/v2'
MODULES = ('common/repository_records.py','common/repository_minimal.py',
           'control/recovery_control_incremental_plan.py')
VARIANTS = {'standard':147,'lightweight':146}
MAX_ORIGINAL = 64 * 1024 * 1024
MAX_MEMBER = 16 * 1024 * 1024
MAX_EXPANDED = 128 * 1024 * 1024
DELTA_FIELDS = {'schemaVersion','status','profile','sourceCommit','predecessorCommit','buildPin',
                'predecessorBuildPin','predecessorGenerationPin','sourceSnapshotPin','packages'}
PACKAGE_FIELDS = {'variant','packagePin','fileCount','fileManifestSha256'}
ROW_FIELDS = PACKAGE_FIELDS | {'predecessor','changedFileEvidence','unchangedFileSha256'}
TASK_RELATIVE = 'doc/tasks/20261106-spug-prod-incremental-to-two-targets'
SOURCE_MODULE_PATHS = dict(zip(MODULES,('ops/recovery/repository_records.py','ops/recovery/repository_minimal.py',
    'backend/src/main/resources/recovery_control_incremental_plan.py')))
SUITES = {'source-policy':['scripts/tests/test_incremental_chain_policy_admission.py'],
    'source-regression':['scripts/tests/'+name+'.py' for name in ('test_automatic_incremental_plan',
        'test_automatic_incremental_resilience','test_automatic_incremental_async_closure',
        'test_repository_root_identity','test_repository_operator_cancel','test_backup_variants')],
    'actual-package-policy':[TASK_RELATIVE+'/test_main_program_chain_policy_actual_packages.py']}
RUN_FIELDS = {'suiteId','mode','commandPin','inputPin','collectionPin','resultPin','stdoutPin','stderrPin',
              'exitReceiptPin','loadedModulePins','executionInputRoot'}
REQUIRED_SOURCE_FILES = tuple(dict.fromkeys([*SOURCE_MODULE_PATHS.values(),
    *(name for files in SUITES.values() for name in files),
    TASK_RELATIVE+'/main_program_chain_policy_evidence.py',TASK_RELATIVE+'/run_main_program_chain_policy_verification.py',
    'ops/backup_engine/build_variants.py','ops/backup_engine/files.json','ops/backup_engine/entry_lightweight.py',
    'ops/backup_engine/standard_fixes.py',
    'ops/backup_engine/baselines/backup-restore-standard-20261021.tgz']))


def suite_files(suite_id, mode):
    need(suite_id in SUITES and ((mode == 'source' and suite_id.startswith('source-')) or
        (mode in VARIANTS and suite_id == 'actual-package-policy')),'SUITE_INVALID')
    return SUITES[suite_id]


def pytest_command(python, root, files, output):
    return [str(python),'-B','-X','utf8','-m','pytest',*files,'-p','run_main_program_chain_policy_verification',
            '-p','no:cacheprovider','--rootdir='+str(root),'--junitxml='+str(output/'junit.xml'),'-q','--tb=short']


def runtime_path(value):
    need(type(value) is str and value and not any(ord(c) < 32 for c in value),'RUNTIME_PATH_INVALID')
    if value.startswith('/'):
        result = PurePosixPath(value)
        need('\\' not in value and not value.startswith('//'),'RUNTIME_PATH_INVALID')
        canonical_value = str(result)
    else:
        result = PureWindowsPath(value)
        need(re.match(r'^[A-Za-z]:[\\/]',value) is not None and not ('/' in value and '\\' in value),
             'RUNTIME_PATH_INVALID')
        canonical_value = result.as_posix() if '/' in value else str(result)
        need(all(not part.endswith(('.', ' ')) and ':' not in part and
             re.match(r'(?i)^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)',part) is None
             for part in result.parts[1:]),'RUNTIME_PATH_ALIAS')
    need(result.is_absolute() and canonical_value == value and '..' not in result.parts,'RUNTIME_PATH_INVALID')
    return result


def file_map(files): return {name:dict(bytes=len(raw),sha256=digest(raw)) for name,raw in files.items()}


def need(condition, code):
    if not condition: raise ValueError('CHAIN_POLICY_EVIDENCE_' + code)


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def digest(raw): return hashlib.sha256(raw).hexdigest()


def pairs(items):
    result = {}
    for key,value in items:
        need(key not in result,'DUPLICATE_JSON_KEY');result[key] = value
    return result


def sha(value): return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None
def commit(value): return type(value) is str and re.fullmatch('[0-9a-f]{40}',value) is not None


def relative(value):
    need(type(value) is str and bool(value) and '\\' not in value,'MEMBER_PATH_INVALID')
    path = PurePosixPath(value)
    need(not path.is_absolute() and str(path) == value and '..' not in path.parts and ':' not in value,
         'MEMBER_PATH_INVALID')
    return value


def pin(value, local=False, allow_empty=False):
    field = 'file' if local else 'path'
    need(type(value) is dict and set(value) == {field,'bytes','sha256'} and type(value['bytes']) is int and
         value['bytes'] >= (0 if allow_empty else 1) and sha(value['sha256']),'PIN_INVALID')
    name = value[field]
    if local:
        need(type(name) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]*',name) is not None and '..' not in name,
             'LOCAL_PIN_INVALID')
    else:
        runtime_path(name)
    return value


class EvidenceReader:
    """Full raw-byte pin reads; JSON is an explicit, separate operation."""
    def __init__(self, task, file_pin, *, roots=()):
        self.task = Path(task).resolve();self.file_pin = file_pin
        self.roots = (self.task,*(Path(root).resolve() for root in roots))
        self.pins = {};self.mapping = None

    def bind_mapping(self, value):
        need(type(value) is dict and set(value) == {'runtimeRoot','persistentRoot'} and self.mapping is None,
             'EVIDENCE_MAPPING_INVALID')
        runtime = runtime_path(value['runtimeRoot']);persistent = Path(value['persistentRoot'])
        need(persistent.is_absolute() and '..' not in persistent.parts and
             any(persistent.resolve().is_relative_to(root) for root in self.roots),'EVIDENCE_MAPPING_OUTSIDE_ROOTS')
        need(not any(p.is_symlink() for p in (persistent,*persistent.parents)),'EVIDENCE_MAPPING_ALIAS')
        self.mapping = (runtime,persistent.resolve())

    def physical_path(self, name):
        value = runtime_path(name)
        if self.mapping and type(value) is type(self.mapping[0]) and value.is_relative_to(self.mapping[0]):
            return self.mapping[1].joinpath(*value.relative_to(self.mapping[0]).parts)
        path = Path(name)
        need(path.is_absolute(),'UNMAPPED_RUNTIME_PATH')
        return path

    def raw(self, expected, *, empty=False):
        local = type(expected) is dict and 'file' in expected
        pin(expected,local=local,allow_empty=empty)
        path = self.task / expected['file'] if local else self.physical_path(expected['path'])
        need(any(path.resolve().is_relative_to(root) for root in self.roots),'ORIGINAL_OUTSIDE_ROOTS')
        need(not any(parent.is_symlink() for parent in (path,*path.parents)),'ORIGINAL_ALIAS')
        need(expected['bytes'] <= MAX_ORIGINAL,'ORIGINAL_TOO_LARGE')
        actual = self.file_pin(path)
        need(actual['bytes'] == expected['bytes'] and actual['sha256'] == expected['sha256'],'ORIGINAL_PIN_CHANGED')
        raw = path.read_bytes()
        need(len(raw) == expected['bytes'] and digest(raw) == expected['sha256'] and self.file_pin(path) == actual,
             'ORIGINAL_CHANGED_DURING_READ')
        key = str(path.resolve())
        need(key not in self.pins or self.pins[key] == actual,'ORIGINAL_REBOUND')
        self.pins[key] = actual
        return raw

    def document(self, expected):
        value = json.loads(self.raw(expected).decode('utf-8'),object_pairs_hook=pairs)
        need(type(value) is dict,'JSON_OBJECT_REQUIRED')
        return value

    def finish(self):
        for expected in self.pins.values():
            need(self.file_pin(Path(expected['path'])) == expected,'ORIGINAL_CHANGED_AT_CLOSE')
        return list(self.pins.values())


def archive_files(raw, *, package=False):
    files = {};total = 0
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
        for item in archive:
            relative(item.name)
            need(item.isfile() and item.name not in files and 0 <= item.size <= MAX_MEMBER,'ARCHIVE_MEMBER_INVALID')
            total += item.size;need(total <= MAX_EXPANDED,'ARCHIVE_TOO_LARGE')
            content = archive.extractfile(item).read()
            need(len(content) == item.size,'ARCHIVE_MEMBER_TRUNCATED');files[item.name] = content
    need(bool(files),'EMPTY_ARCHIVE')
    if package:
        need('package.json' in files,'PACKAGE_MANIFEST_MISSING')
        metadata = json.loads(files.pop('package.json').decode('utf-8'),object_pairs_hook=pairs)
        hashes = {name:digest(content) for name,content in files.items()}
        need(metadata.get('files') == hashes and metadata.get('packageSha256') == digest(canonical(hashes)),
             'PACKAGE_MANIFEST_CHANGED')
        compile_files(files)
    return files


def compile_files(files):
    for name,raw in files.items():
        relative(name);need(type(raw) is bytes and bool(raw),'PACKAGE_MEMBER_INVALID')
        if name.endswith('.py'): compile(raw,name,'exec',dont_inherit=True)


def read_package(reader, row, variant):
    need(variant in VARIANTS and row.get('variant') == variant and row.get('fileCount') == VARIANTS[variant],
         'PACKAGE_VARIANT_CHANGED')
    files = archive_files(reader.raw(row['packagePin']),package=True)
    need(len(files) == row['fileCount'] and digest(canonical({n:digest(b) for n,b in files.items()})) ==
         row['fileManifestSha256'],'PACKAGE_CONTENT_CHANGED')
    return files


def partition(files, previous):
    need(set(files) == set(previous),'PACKAGE_MEMBER_SET_CHANGED')
    compile_files(files);compile_files(previous)
    changed = {};unchanged = {};semantic = []
    for name,raw in files.items():
        old = previous[name]
        if old == raw: unchanged[name] = digest(raw);continue
        line_only = old.replace(b'\r\n',b'\n') == raw.replace(b'\r\n',b'\n')
        if line_only and name.endswith('.py'):
            need(ast.dump(ast.parse(old)) == ast.dump(ast.parse(raw)),'LINE_ENDING_AST_CHANGED')
        if not line_only: semantic.append(name)
        changed[name] = dict(oldBytes=len(old),newBytes=len(raw),oldSha256=digest(old),newSha256=digest(raw),
                             lineEndingOnly=line_only)
    need(set(semantic) == set(MODULES),'UNREVIEWED_SEMANTIC_FILES')
    return dict(changedFileEvidence=changed,unchangedFileSha256=unchanged)


def _row(row, variant):
    need(type(row) is dict and set(row) == ROW_FIELDS and row['variant'] == variant and
         type(row['fileCount']) is int and row['fileCount'] == VARIANTS[variant] and sha(row['fileManifestSha256']),
         'DELTA_PACKAGE_INVALID')
    pin(row['packagePin']);old = row['predecessor']
    need(type(old) is dict and set(old) == PACKAGE_FIELDS and old['variant'] == variant and
         type(old['fileCount']) is int and old['fileCount'] == VARIANTS[variant] and sha(old['fileManifestSha256']),
         'DELTA_PREDECESSOR_INVALID');pin(old['packagePin'])
    changed = row['changedFileEvidence'];unchanged = row['unchangedFileSha256']
    need(type(changed) is dict and type(unchanged) is dict and not set(changed)&set(unchanged) and
         len(changed)+len(unchanged) == VARIANTS[variant],'DELTA_PARTITION_INVALID')
    semantic = []
    for name,entry in changed.items():
        relative(name)
        need(type(entry) is dict and set(entry) == {'oldBytes','newBytes','oldSha256','newSha256','lineEndingOnly'} and
             all(type(entry[k]) is int and entry[k] > 0 for k in ('oldBytes','newBytes')) and
             all(sha(entry[k]) for k in ('oldSha256','newSha256')) and type(entry['lineEndingOnly']) is bool,
             'DELTA_MEMBER_INVALID')
        if not entry['lineEndingOnly']: semantic.append(name)
    need(set(semantic) == set(MODULES),'UNREVIEWED_SEMANTIC_FILES')
    for name,value in unchanged.items(): relative(name);need(sha(value),'DELTA_UNCHANGED_INVALID')


def validate_chain_policy_delta(delta, build, build_pin, old_build, old_build_pin,
                                files, previous_files, source_commit, previous_commit):
    need(type(delta) is dict and set(delta) == DELTA_FIELDS and delta['schemaVersion'] == DELTA_SCHEMA and
         delta['status'] == 'PASS' and delta['profile'] == PROFILE and commit(source_commit) and commit(previous_commit) and
         source_commit != previous_commit and delta['sourceCommit'] == source_commit and
         delta['predecessorCommit'] == previous_commit and delta['buildPin'] == build_pin and
         delta['predecessorBuildPin'] == old_build_pin,'DELTA_IDENTITY_CHANGED')
    for name in ('buildPin','predecessorBuildPin','predecessorGenerationPin','sourceSnapshotPin'):pin(delta[name],local=True)
    need(type(delta['packages']) is list and len(delta['packages']) == 2,'DELTA_VARIANTS_CHANGED')
    for row,variant in zip(delta['packages'],VARIANTS):_row(row,variant)
    row = delta['packages'][0]
    for report,material,revision,raws in ((build,row,source_commit,files),
            (old_build,row['predecessor'],previous_commit,previous_files)):
        need(report.get('status') == 'PASS' and report.get('targetCommit') == revision and
             report.get('allFilesShaAndCompileVerified') is True and type(report.get('fileCount')) is int and
             report['fileCount'] == len(raws) == 147 and report['packageSha256'] == material['packagePin']['sha256'] and
             report['fileManifestSha256'] == material['fileManifestSha256'] ==
             digest(canonical({n:digest(b) for n,b in raws.items()})),'DELTA_BUILD_CHANGED')
    need(partition(files,previous_files) == {k:row[k] for k in ('changedFileEvidence','unchangedFileSha256')},
         'DELTA_CONTENT_CHANGED')


def timestamp(value):
    need(type(value) is str,'TIMESTAMP_INVALID')
    result = datetime.fromisoformat(value.replace('Z','+00:00'))
    need(result.tzinfo is not None,'TIMESTAMP_INVALID')
    return result


def validate_run(reader, run, *, source_commit, input_pin, module_files, source_root, runner_pin, source_input_pin=None):
    need(type(run) is dict and set(run) == RUN_FIELDS,'RUN_FIELDS_INVALID')
    files = suite_files(run['suiteId'],run['mode'])
    need(run['inputPin'] == input_pin,'RUN_INPUT_CHANGED');reader.raw(input_pin);reader.raw(runner_pin)
    source_input_pin = input_pin if run['mode'] == 'source' and source_input_pin is None else source_input_pin
    scope = run['executionInputRoot']
    need(type(scope) is dict and set(scope) == {'schemaVersion','sourceRoot','moduleRoot','sourceInputPin','moduleInputPin'} and
         scope['schemaVersion'] == 'MainProgramExecutionInputRoot/v1' and scope['sourceInputPin'] == source_input_pin and
         scope['moduleInputPin'] == input_pin,'EXECUTION_SCOPE_CHANGED')
    root = runtime_path(scope['sourceRoot']);module_root = runtime_path(scope['moduleRoot'])
    source_files = archive_files(reader.raw(source_input_pin))
    program_files = source_files if run['mode'] == 'source' else archive_files(reader.raw(input_pin),package=True)
    if run['mode'] == 'source':need(module_root == root,'EXECUTION_SOURCE_ROOT_CHANGED')
    else:need(module_root.name == 'package' and not module_root.is_relative_to(root),'EXECUTION_PACKAGE_ROOT_INVALID')
    command = reader.document(run['commandPin']);terminal = reader.document(run['exitReceiptPin'])
    collection = reader.document(run['collectionPin']);result = reader.document(run['resultPin'])
    reader.raw(run['stdoutPin'],empty=True);reader.raw(run['stderrPin'],empty=True)
    need(set(command) == {'argv','cwd','mode','sourceCommit','inputPin','testFiles','startedAt'} and
         command['cwd'] == str(root) and command['sourceCommit'] == source_commit and command['mode'] == run['mode'] and
         command['inputPin'] == input_pin and command['testFiles'] == files and type(command['argv']) is list and
         len(command['argv']) > 0,'COMMAND_IDENTITY_CHANGED')
    runtime_path(command['argv'][0])
    junit_arguments = [arg[len('--junitxml='):] for arg in command['argv'] if arg.startswith('--junitxml=')]
    need(len(junit_arguments) == 1,'COMMAND_JUNIT_INVALID');output = runtime_path(junit_arguments[0]).parent
    need(not output.is_relative_to(root) and (run['mode'] == 'source' or module_root == output/'package'),
         'COMMAND_OUTPUT_SCOPE_INVALID')
    need(command['argv'] == pytest_command(command['argv'][0],root,files,output),'COMMAND_SELECTION_CHANGED')
    need(set(terminal) == {'commandPin','inputPin','startedAt','finishedAt','exitCode','timedOut','inputPinsBefore','inputPinsAfter',
         'runtimeInputPinsBefore','runtimeInputPinsAfter'} and
         terminal['commandPin'] == run['commandPin'] and terminal['inputPin'] == input_pin and
         terminal['startedAt'] == command['startedAt'] and timestamp(terminal['finishedAt']) >= timestamp(terminal['startedAt']) and
         type(terminal['exitCode']) is int and terminal['exitCode'] == 0 and terminal['timedOut'] is False,
         'PROCESS_NOT_SUCCEEDED')
    expected_inputs = [input_pin,runner_pin] if input_pin == source_input_pin else [input_pin,runner_pin,source_input_pin]
    need(terminal['inputPinsBefore'] == terminal['inputPinsAfter'] == expected_inputs,'PROCESS_INPUT_DRIFT')
    need(terminal['runtimeInputPinsBefore'] == terminal['runtimeInputPinsAfter'] ==
         dict(source=file_map(source_files),program=file_map(program_files)),'RUNTIME_INPUT_DRIFT')
    nodes = collection.get('nodeIds')
    need(set(collection) == {'suiteId','mode','testFiles','nodeIds'} and collection['suiteId'] == run['suiteId'] and
         collection['mode'] == run['mode'] and collection['testFiles'] == files and type(nodes) is list and nodes and
         all(type(n) is str and '::' in n and n.split('::',1)[0] in files for n in nodes) and
         len(nodes) == len(set(nodes)) and {n.split('::',1)[0] for n in nodes} == set(files),'COLLECTION_INCOMPLETE')
    need(set(result) == {'suiteId','mode','tests','failures','errors','skipped','nodeResults','junitPin'} and
         result['suiteId'] == run['suiteId'] and result['mode'] == run['mode'] and
         all(type(result[k]) is int for k in ('tests','failures','errors','skipped')) and
         result['tests'] == len(nodes) and result['failures'] == result['errors'] == result['skipped'] == 0 and
         type(result['nodeResults']) is list and len(result['nodeResults']) == len(nodes),'TESTS_NOT_SUCCEEDED')
    rows = result['nodeResults']
    need(all(type(row) is dict and set(row) == {'nodeId','setup','call','teardown'} and
         all(row[phase] == 'passed' for phase in ('setup','call','teardown')) for row in rows) and
         {row['nodeId'] for row in rows} == set(nodes),'TEST_NODE_TERMINAL_INVALID')
    junit = ET.fromstring(reader.raw(result['junitPin']));cases = junit.findall('.//testcase')
    suites = junit.findall('.//testsuite') if junit.tag != 'testsuite' else [junit]
    need(suites and all(int(s.get('failures','-1')) == int(s.get('errors','-1')) == int(s.get('skipped','-1')) == 0
         for s in suites) and sum(int(s.get('tests','-1')) for s in suites) == len(nodes) == len(cases),
         'JUNIT_NOT_SUCCEEDED')
    junit_nodes = []
    for case in cases:
        properties = [p.get('value') for p in case.findall('./properties/property') if p.get('name') == 'chain_node_id']
        need(len(properties) == 1 and not any(case.find(n) is not None for n in ('failure','error','skipped')),
             'JUNIT_NODE_INVALID');junit_nodes.extend(properties)
    need(len(set(junit_nodes)) == len(nodes) and set(junit_nodes) == set(nodes),'JUNIT_COLLECTION_CHANGED')
    need(type(run['loadedModulePins']) is dict and set(run['loadedModulePins']) == set(MODULES),'LOADED_MODULE_SET_CHANGED')
    for name,expected in run['loadedModulePins'].items():
        need(type(expected) is dict and set(expected) == {'path','bytes','sha256'} and type(expected['bytes']) is int and
             expected['bytes'] > 0 and sha(expected['sha256']),'LOADED_MODULE_PIN_INVALID')
        relative_name = SOURCE_MODULE_PATHS[name] if run['mode'] == 'source' else name
        need(runtime_path(expected['path']) == module_root/relative_name and relative_name in program_files and
             module_files[name] == program_files[relative_name] and expected['bytes'] == len(module_files[name]) and
             expected['sha256'] == digest(module_files[name]),'LOADED_MODULE_CHANGED')


def git(root, *args):
    process = subprocess.run(['git','-C',str(root),*args],capture_output=True,timeout=30)
    need(process.returncode == 0,'GIT_READ_FAILED')
    return process.stdout


def committed_files(root, source_commit):
    root = Path(root).resolve()
    need(commit(source_commit) and git(root,'rev-parse','HEAD').decode().strip() == source_commit and
         git(root,'status','--porcelain=v1','--untracked-files=all') == b'','COMMITTED_CLEAN_CHECKOUT_REQUIRED')
    tracked = git(root,'ls-tree','-r','--name-only','-z',source_commit).decode('utf-8').split('\0')
    selected = sorted(name for name in tracked if name and (name in REQUIRED_SOURCE_FILES or
        name.startswith(('ops/recovery/','ops/backup_engine/','backend/src/main/resources/')) or
        name.startswith('scripts/tests/') and name.endswith('.py')))
    need(set(REQUIRED_SOURCE_FILES) <= set(selected),'SOURCE_REQUIRED_INPUT_MISSING')
    files = {}
    for name in selected:
        relative(name);path = root/name
        need(not path.is_symlink() and path.is_file(),'SOURCE_ALIAS')
        raw = path.read_bytes()
        need(raw == git(root,'show',source_commit+':'+name),'SOURCE_COMMITTED_BYTES_CHANGED')
        files[name] = raw
    need(git(root,'rev-parse','HEAD').decode().strip() == source_commit and
         git(root,'status','--porcelain=v1','--untracked-files=all') == b'','SOURCE_CHANGED_DURING_READ')
    return files


def validate_source_snapshot(reader, value, *, source_commit, build_pin, root):
    need(set(value) == {'schemaVersion','sourceCommit','buildPin','archivePin','filePins','gitHeadPin','gitStatusPin','captureReceiptPin'} and
         value['schemaVersion'] == 'MainProgramChainPolicySourceSnapshot/v1' and value['sourceCommit'] == source_commit and
         value['buildPin'] == build_pin,'SOURCE_SNAPSHOT_IDENTITY_CHANGED')
    need(reader.raw(value['gitHeadPin']).decode().strip() == source_commit and
         reader.raw(value['gitStatusPin'],empty=True) == b'','SOURCE_GIT_ORIGINAL_INVALID')
    files = archive_files(reader.raw(value['archivePin']));committed = committed_files(root,source_commit)
    expected = {name:dict(bytes=len(raw),sha256=digest(raw)) for name,raw in files.items()}
    need(files == committed and value['filePins'] == expected,'SOURCE_ARCHIVE_CHANGED')
    terminal = reader.document(value['captureReceiptPin'])
    need(set(terminal) == {'sourceCommit','sourceRoot','startedAt','finishedAt','exitCode','timedOut',
         'inputPinsBefore','inputPinsAfter','gitHeadPin','gitStatusPin'} and terminal['sourceCommit'] == source_commit and
         reader.physical_path(terminal['sourceRoot']).resolve() == Path(root).resolve() and terminal['gitHeadPin'] == value['gitHeadPin'] and
         terminal['gitStatusPin'] == value['gitStatusPin'] and type(terminal['exitCode']) is int and
         terminal['exitCode'] == 0 and terminal['timedOut'] is False and
         timestamp(terminal['finishedAt']) >= timestamp(terminal['startedAt']) and
         terminal['inputPinsBefore'] == terminal['inputPinsAfter'] == expected,'SOURCE_CAPTURE_NOT_PROVEN')
    for name,entry in expected.items():reader.raw(dict(path=str(Path(root)/name),**entry),empty=entry['bytes'] == 0)
    return files


def validate_baseline(reader, coverage, predecessor, validate_initial_coverage):
    generation = predecessor['generation'];build = predecessor['build']
    need(coverage['baselineGenerationPin'] == predecessor['generationPin'] and
         coverage['baselineBuildPin'] == generation['buildPin'] and reader.document(predecessor['generationPin']) == generation and
         reader.document(generation['buildPin']) == build,'BASELINE_GENERATION_CHANGED')
    kind = coverage['baselineCoverageKind']
    if kind == 'INITIAL_FULL_COVERAGE':
        need(generation['predecessor']['kind'] == 'AUTOMATIC_INSTALLATION' and
             build.get('exactTestCoveragePin') == coverage['baselineCoveragePin'],'INITIAL_BASELINE_REQUIRED')
        validate_initial_coverage(build);return reader.document(coverage['baselineCoveragePin'])
    need(kind == 'CONTROL_GENERATION_COVERAGE' and generation['predecessor']['kind'] == 'CONTROL_GENERATION',
         'BASELINE_KIND_INVALID')
    original = reader.document(coverage['baselineCoveragePin'])
    need(original.get('schemaVersion') in ('MainProgramControlCoverage/v1',COVERAGE_SCHEMA) and
         original.get('status') == 'PASS' and original.get('candidateBuildPin') == generation['buildPin'],
         'BASELINE_COVERAGE_CHANGED')
    owned = predecessor['inputPins'];mapping = generation['activationEvidenceByHost']
    need(set(mapping) == {'57','58','59'},'BASELINE_HOST_SET_CHANGED')
    for host,roles in {'57':['source','target'],'58':['target'],'59':['target']}.items():
        need(type(mapping[host]) is list and len(mapping[host]) == len(roles),'BASELINE_RICH_COUNT_CHANGED')
        for reference,role in zip(mapping[host],roles):
            need(reference in owned,'BASELINE_RICH_NOT_OWNED');rich = reader.document(reference)
            need(rich.get('sourceCommit') == generation['sourceCommit'] and
                 rich.get('coveragePin') == coverage['baselineCoveragePin'] and
                 rich.get('previousControlGenerationPin') == generation['predecessor']['generationPin'] and
                 rich.get('revisionId') == predecessor['plan']['revisionId'],'BASELINE_RICH_CHANGED')
            inputs_ref = rich['activationInputsPin'];inputs = reader.document(inputs_ref)
            physical = dict(path=str(reader.task/inputs_ref['file']),bytes=inputs_ref['bytes'],sha256=inputs_ref['sha256'])
            need(physical in owned and all(inputs.get(k) == v for k,v in dict(sourceCommit=generation['sourceCommit'],
                buildPin=generation['buildPin'],coveragePin=coverage['baselineCoveragePin'],
                previousControlGenerationPin=generation['predecessor']['generationPin'],
                revisionId=predecessor['plan']['revisionId'],suffix=host,role=role).items()),'BASELINE_INPUTS_CHANGED')
    return original


VERIFICATION_FIELDS = {'schemaVersion','status','profile','sourceCommit','buildPin','packageDeltaPin','sourceSnapshotPin',
                       'runnerPin','runs','failedAttemptPins','evidenceRootMapping'}
COVERAGE_FIELDS = {'schemaVersion','status','profile','sourceCommit','baselineGenerationPin','baselineBuildPin',
    'baselineCoverageKind','baselineCoveragePin','candidateBuildPin','packagePartitions','deltaTestEvidencePins',
    'actualPackageEvidencePins','failedEvidencePins'}
REQUIRED_RUNS = [('source-policy','source'),('source-regression','source'),
                 ('actual-package-policy','standard'),('actual-package-policy','lightweight')]


def validate_failed_attempt(reader, reference):
    report = reader.document(reference)
    need(set(report) == VERIFICATION_FIELDS and report['schemaVersion'] == 'MainProgramChainPolicyVerification/v1' and
         report['profile'] == PROFILE and report['status'] == 'FAIL' and commit(report['sourceCommit']) and
         type(report['runs']) is list and report['runs'] and report['failedAttemptPins'] == [],'FAILED_ATTEMPT_INVALID')
    failed = False
    for run in report['runs']:
        need(type(run) is dict and set(run) == RUN_FIELDS,'FAILED_RUN_INVALID')
        suite_files(run['suiteId'],run['mode'])
        command = reader.document(run['commandPin']);terminal = reader.document(run['exitReceiptPin'])
        need(terminal.get('commandPin') == run['commandPin'] and terminal.get('inputPin') == run['inputPin'] and
             terminal.get('startedAt') == command.get('startedAt') and
             timestamp(terminal['finishedAt']) >= timestamp(terminal['startedAt']),'FAILED_TERMINAL_UNBOUND')
        need(type(terminal.get('timedOut')) is bool and (terminal.get('exitCode') is None or type(terminal['exitCode']) is int),
             'FAILED_TERMINAL_INVALID')
        failed |= terminal['timedOut'] or terminal['exitCode'] != 0
        reader.raw(run['stdoutPin'],empty=True);reader.raw(run['stderrPin'],empty=True)
        if run['collectionPin'] is not None:reader.document(run['collectionPin'])
        if run['resultPin'] is not None:
            result = reader.document(run['resultPin']);reader.raw(result['junitPin'])
            failed |= any(type(result.get(k)) is int and result[k] > 0 for k in ('failures','errors','skipped'))
    need(failed,'FAILED_ATTEMPT_NOT_FAILED')


def validate_verification(reader, report, *, inputs, delta, delta_pin, snapshot, source_files, packages, failed_refs):
    need(type(report) is dict and set(report) == VERIFICATION_FIELDS and
         report['schemaVersion'] == 'MainProgramChainPolicyVerification/v1' and report['status'] == 'PASS' and
         report['profile'] == PROFILE and report['sourceCommit'] == inputs['sourceCommit'] and
         report['buildPin'] == inputs['buildPin'] and report['packageDeltaPin'] == delta_pin and
         report['sourceSnapshotPin'] == delta['sourceSnapshotPin'] and report['failedAttemptPins'] == failed_refs,
         'VERIFICATION_IDENTITY_CHANGED')
    need(type(report['runs']) is list and [(r.get('suiteId'),r.get('mode')) for r in report['runs']] == REQUIRED_RUNS,
         'VERIFICATION_SUITES_INCOMPLETE')
    runner_name = TASK_RELATIVE+'/run_main_program_chain_policy_verification.py';runner_raw = source_files[runner_name]
    pin(report['runnerPin'])
    need(report['runnerPin']['bytes'] == len(runner_raw) and report['runnerPin']['sha256'] == digest(runner_raw),
         'RUNNER_SOURCE_CHANGED');reader.raw(report['runnerPin'])
    for run in report['runs']:
        mode = run['mode']
        expected_input = snapshot['archivePin'] if mode == 'source' else next(r['packagePin'] for r in delta['packages'] if r['variant'] == mode)
        raw_modules = {name:source_files[SOURCE_MODULE_PATHS[name]] for name in MODULES} if mode == 'source' else packages[mode]
        validate_run(reader,run,source_commit=inputs['sourceCommit'],input_pin=expected_input,
            module_files=raw_modules,source_root=None,runner_pin=report['runnerPin'],source_input_pin=snapshot['archivePin'])


def validate_predecessor_package(reader, old, expected, schema):
    """Bind an original predecessor archive without rewriting its path spelling."""
    need(schema in ('ArchiveCataloguePackageDelta/v2',DELTA_SCHEMA) and
         all(old.get(k) == expected[k] for k in ('variant','fileCount','fileManifestSha256')),
         'BASELINE_PACKAGE_CHANGED')
    expected_pin = pin(expected['packagePin'])
    if schema == DELTA_SCHEMA:
        original_pin = pin(old['packagePin'])
    else:
        # The old delta did not carry archive length. Read the real old archive
        # using the candidate's declared length and the original old SHA.
        original_pin = pin(dict(path=old['path'],bytes=expected_pin['bytes'],sha256=old['packageSha256']))
    original_path = runtime_path(original_pin['path']);expected_path = runtime_path(expected_pin['path'])
    need(type(original_path) is type(expected_path) and original_path == expected_path and
         all(original_pin[k] == expected_pin[k] for k in ('bytes','sha256')),'BASELINE_PACKAGE_CHANGED')
    reader.raw(original_pin)


def validate_chain_policy_coverage(records, inputs, predecessor, *, file_pin, validate_initial_coverage):
    report = records.pinned(inputs['coveragePin'])
    need(type(report) is dict and set(report) == COVERAGE_FIELDS and report['schemaVersion'] == COVERAGE_SCHEMA and
         report['status'] == 'PASS' and report['profile'] == PROFILE and report['sourceCommit'] == inputs['sourceCommit'] and
         report['candidateBuildPin'] == inputs['buildPin'],'COVERAGE_IDENTITY_CHANGED')
    tests = report['deltaTestEvidencePins'];artifacts = report['actualPackageEvidencePins'];failures = report['failedEvidencePins']
    need(type(tests) is list and len(tests) == 1 and type(artifacts) is list and len(artifacts) == 2 and
         artifacts[1] == tests[0] and type(failures) is list and len({canonical(p) for p in failures}) == len(failures),
         'COVERAGE_ORIGINAL_SET_INVALID')
    build = records.pinned(inputs['buildPin']);delta = records.pinned(artifacts[0])
    need(build.get('status') == 'PASS' and build.get('targetCommit') == inputs['sourceCommit'] and
         build.get('newCommits') is False and build.get('mergeRequired') is False and
         build.get('allFilesShaAndCompileVerified') is True,'CANDIDATE_BUILD_INVALID')
    private_roots = [Path(build['worktree']),Path(build['worktree']).parent]
    if predecessor['build'].get('worktree'):private_roots.append(Path(predecessor['build']['worktree']).parent)
    private_roots.extend(Path(p['path']).parent for p in predecessor['inputPins'])
    reader = EvidenceReader(records.task,file_pin,roots=private_roots)
    verification = reader.document(tests[0])
    need(set(verification) == VERIFICATION_FIELDS,'VERIFICATION_FIELDS_INVALID')
    reader.bind_mapping(verification['evidenceRootMapping'])
    reader.document(inputs['coveragePin']);reader.document(inputs['buildPin']);reader.document(artifacts[0])
    old_coverage = validate_baseline(reader,report,predecessor,lambda old:validate_initial_coverage(records,old))
    need(delta.get('predecessorGenerationPin') == predecessor['generationPin'],'DELTA_GENERATION_CHANGED')
    packages = {};previous = {}
    need(type(delta.get('packages')) is list and len(delta['packages']) == 2,'COVERAGE_PACKAGES_INVALID')
    # Both prior variants are bound to the already validated predecessor's own
    # package evidence. A caller cannot substitute an arbitrary lightweight base.
    prior_refs = old_coverage.get('actualPackageEvidencePins')
    need(type(prior_refs) is list and prior_refs,'BASELINE_PACKAGE_EVIDENCE_REQUIRED')
    prior_delta = reader.document(prior_refs[0])
    need(prior_delta.get('schemaVersion') in ('ArchiveCataloguePackageDelta/v2',DELTA_SCHEMA),'BASELINE_DELTA_INVALID')
    prior_rows = prior_delta.get('packages');need(type(prior_rows) is list and len(prior_rows) == 2,'BASELINE_VARIANTS_INVALID')
    for row,variant in zip(delta['packages'],VARIANTS):
        _row(row,variant);packages[variant] = read_package(reader,row,variant)
        previous[variant] = read_package(reader,row['predecessor'],variant)
        old = next((p for p in prior_rows if p.get('variant') == variant),None)
        need(old is not None,'BASELINE_VARIANT_MISSING')
        expected_old = row['predecessor']
        validate_predecessor_package(reader,old,expected_old,prior_delta['schemaVersion'])
        actual_partition = partition(packages[variant],previous[variant])
        need(actual_partition == {k:row[k] for k in ('changedFileEvidence','unchangedFileSha256')} and
             report['packagePartitions'].get(variant) == actual_partition,'COVERAGE_PARTITION_CHANGED')
    need(set(report['packagePartitions']) == set(VARIANTS),'COVERAGE_VARIANTS_CHANGED')
    validate_chain_policy_delta(delta,build,inputs['buildPin'],predecessor['build'],predecessor['generation']['buildPin'],
        packages['standard'],previous['standard'],inputs['sourceCommit'],predecessor['generation']['sourceCommit'])
    snapshot = reader.document(delta['sourceSnapshotPin'])
    source_files = validate_source_snapshot(reader,snapshot,source_commit=inputs['sourceCommit'],build_pin=inputs['buildPin'],root=build['worktree'])
    for ref in failures:validate_failed_attempt(reader,ref)
    validate_verification(reader,verification,inputs=inputs,delta=delta,delta_pin=artifacts[0],snapshot=snapshot,
        source_files=source_files,packages=packages,failed_refs=failures)
    return dict(coverage=report,build=build,delta=delta,packageFiles=packages['standard'],
        previousPackageFiles=previous['standard'],physicalPins=reader.finish())
