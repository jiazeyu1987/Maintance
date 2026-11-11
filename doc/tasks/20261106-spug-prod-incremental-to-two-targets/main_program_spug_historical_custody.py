"""Read one explicitly bound completed Spug history; no transport or writes.

Historical logical inputs keep their original identities. Physical preserved
sources and current readers are checked separately and never replace a report.
"""
from copy import deepcopy
import hashlib
import importlib
from pathlib import Path
import shutil
import subprocess

import main_program_installation_selection as contract
import main_program_spug_publication as publication
import main_program_spug_publication_continuation as continuation

SELECTOR='main-program-current-installations-45dd7dc-r6-v4.json'
READERS=('main_program_spug_publication_continuation.py','spug_runtime_dependency_completion.py',
         'main_program_spug_publication_verify_only.py','main_program_spug_resource_transition.py')
LABELS=('publication','continuation','dependency','resourceTransition','verification')
ACTIVATION_BYTES=107657
ACTIVATION_SHA='963bbe907d1d2f7334ee9fa5d8598a5659361ca512d23514d92d9721b91146bb'
SOURCE_ROLE_READERS=('main_program_spug_historical_custody.py',
    'main_program_spug_control_generation_acceptance.py','main_program_current_installation.py')
CATALOGUE_PATH='backend/src/main/resources/recovery_control_restore_catalogue.py'
CATALOGUE_SHA='d6dfd4701a5a6343af71329167b1167952b3328b4a52568e9ff21ae060c84ab9'
ACCEPTANCE_ACTIVATION_SHA='ef070f77fd7c8f5753a5eead343d2e49e20e52e45cc4aabc5601f7e1d0726f69'
ACCEPTANCE_ACTIVATION_COMMIT='78de6dc6308c88020b149b1a656540e94b7e097f'


def need(condition,code):
    if not condition:raise ValueError('SPUG_HISTORICAL_'+code)


def key(pin):
    need(type(pin) is dict and set(pin)=={'path','bytes','sha256'} and type(pin['path']) is str and
         type(pin['bytes']) is int and pin['bytes']>=0 and contract.sha(pin['sha256']),'PIN_INVALID')
    return pin['path'],pin['bytes'],pin['sha256']


class SourceRoles:
    """Two proven source roles, separate from immutable logical input sets."""
    def __init__(self,task,private,value,pins,records,attempt,base):
        self.task,self.private=task,private
        self.value=deepcopy(value);self.acceptance_attempt=deepcopy(attempt)
        self.source_roles=deepcopy(value['sourceRoles']);self.physical_pins=pins
        self.current_pins=deepcopy(value['currentReaderPins']);self.private_pins=[]
        need(type(self.source_roles) is dict and set(self.source_roles)=={'catalogue','acceptanceActivation'},'SOURCE_ROLE_SET')
        expected_current={str(task/name) for name in SOURCE_ROLE_READERS}
        need(type(self.current_pins) is list and len(self.current_pins)==3 and
             {key(p)[0] for p in self.current_pins}==expected_current,'SOURCE_CURRENT_READERS')
        for name in SOURCE_ROLE_READERS:
            module=importlib.import_module(Path(name).stem)
            need(Path(module.__file__).resolve(strict=True)==task/name,'SOURCE_LOADED_READER')
        for reference in self.current_pins:publication.verify_bytes(reference)
        self.reader_rows={}
        rows=value['readerCustodies']
        need(type(rows) is list and len(rows)==2,'SOURCE_READER_SET')
        for row in rows:
            need(type(row) is dict and set(row)=={'originalPin','preservedPin'},'SOURCE_READER_FIELDS')
            old=row['originalPin'];path=key(old)[0]
            need(path in {str(task/name) for name in SOURCE_ROLE_READERS[:2]} and
                 path not in self.reader_rows and old in attempt['inputPins'],'SOURCE_READER_SCOPE')
            self.preserved(row);self.reader_rows[path]=deepcopy(row)
        need(set(self.reader_rows)=={str(task/name) for name in SOURCE_ROLE_READERS[:2]},'SOURCE_READER_SET')
        for role,row in self.source_roles.items():
            need(type(row) is dict and set(row)=={'originalPin','preservedPin','provenance'},'SOURCE_ROLE_FIELDS')
            self.preserved(row)
        root=task.parents[2];catalogue=self.source_roles['catalogue'];activation=self.source_roles['acceptanceActivation']
        need(catalogue['originalPin']==dict(path=str(root/CATALOGUE_PATH),bytes=20770,sha256=CATALOGUE_SHA) and
             type(catalogue['originalPin']['bytes']) is int,'SOURCE_CATALOGUE_IDENTITY')
        need(activation['originalPin']==dict(path=str(task/'main_program_control_activation.py'),bytes=121760,
             sha256=ACCEPTANCE_ACTIVATION_SHA) and type(activation['originalPin']['bytes']) is int,'SOURCE_ACTIVATION_IDENTITY')
        for row in self.source_roles.values():
            need(sum(p==row['originalPin'] for p in attempt['inputPins'])==1,'SOURCE_ACCEPTANCE_BINDING')
        for label,reference in value['attemptPins'].items():
            old_attempt=self.document(reference)
            need(sum(p==catalogue['originalPin'] for p in old_attempt['inputPins'])==1 and
                 activation['originalPin'] not in old_attempt['inputPins'],'SOURCE_ATTEMPT_BINDING')
        prov=activation['provenance'];need(type(prov) is dict and set(prov)=={'gitNativePin'},'SOURCE_GIT_FIELDS')
        native=self.document(prov['gitNativePin'])
        fields={'schemaVersion','argv','cwd','timeoutSeconds','actualExitCode','timedOut','stdoutPin','stderrPin',
                'executablePin','sourceCommit','relativePath'}
        relative='doc/tasks/'+task.name+'/main_program_control_activation.py'
        executable=Path(shutil.which('git')).resolve(strict=True)
        argv=[str(executable),'--no-replace-objects','-C',str(root),'cat-file','blob',ACCEPTANCE_ACTIVATION_COMMIT+':'+relative]
        need(type(native) is dict and set(native)==fields and native['schemaVersion']=='SpugHistoricalGitBlobCapture/v1' and
             native['argv']==argv and native['cwd']==str(root) and native['timeoutSeconds']==30 and
             type(native['timeoutSeconds']) is int and native['actualExitCode']==0 and type(native['actualExitCode']) is int and
             native['timedOut'] is False and native['sourceCommit']==ACCEPTANCE_ACTIVATION_COMMIT and
             native['relativePath']==relative and native['stdoutPin']==activation['preservedPin'] and
             native['executablePin']==publication.file_pin(executable),'SOURCE_GIT_NATIVE')
        need(self.raw(native['stderrPin'])==b'','SOURCE_GIT_STDERR')
        self.physical_pins.append(native['executablePin'])
        # Re-read the exact committed object; a self-reported exit0 is insufficient.
        actual=subprocess.run(argv,cwd=root,capture_output=True,timeout=30)
        need(actual.returncode==0 and not actual.stderr and actual.stdout==self.raw(activation['preservedPin']),
             'SOURCE_GIT_BLOB_CHANGED')
        self.git_evidence=dict(actualExitCode=actual.returncode,timedOut=False,
            stdoutSha256=hashlib.sha256(actual.stdout).hexdigest(),sourceCommit=ACCEPTANCE_ACTIVATION_COMMIT,relativePath=relative)
        prov=catalogue['provenance']
        need(type(prov) is dict and set(prov)=={'sourceCommit','relativePath','originalBuildPin','registeredBuildPin'} and
             prov['sourceCommit']=='45dd7dc65409c87fe856584b85873ea96c0b830e' and prov['relativePath']==CATALOGUE_PATH,
             'SOURCE_CATALOGUE_PROVENANCE')
        old_selection=records.pinned(base['selectionPin']);old_generation=records.pinned(old_selection['controlGenerationPin'])
        selected=records.pinned(value['selectionPin']);generation=records.pinned(selected['controlGenerationPin'])
        need(prov['originalBuildPin']==old_generation['buildPin'] and prov['registeredBuildPin']==generation['buildPin'],
             'SOURCE_BUILD_BINDING')
        original_build=records.pinned(prov['originalBuildPin']);registered_build=records.pinned(prov['registeredBuildPin'])
        need(original_build['targetCommit']==prov['sourceCommit'] and registered_build['targetCommit']==selected['sourceCommit'] and
             catalogue['preservedPin'] in attempt['inputPins'] and catalogue['preservedPin']['path']==
             str(Path(registered_build['worktree'])/CATALOGUE_PATH),'SOURCE_REGISTERED_ORIGINAL')
        cat_argv=[str(executable),'--no-replace-objects','-C',str(root),'cat-file','blob',prov['sourceCommit']+':'+CATALOGUE_PATH]
        original=subprocess.run(cat_argv,cwd=root,capture_output=True,timeout=30)
        need(original.returncode==0 and not original.stderr and original.stdout==self.raw(catalogue['preservedPin']),
             'SOURCE_CATALOGUE_BLOB_CHANGED')
        self.physical_pins.extend(records.path_pins())

    def raw(self,reference):
        raw=continuation.private_raw(self.private,reference,self.physical_pins)
        self.private_pins.append(deepcopy(reference));return raw

    def document(self,reference):
        import json
        value=json.loads(self.raw(reference).decode('utf-8'),object_pairs_hook=contract.document)
        need(type(value) is dict,'SOURCE_DOCUMENT_INVALID');return value

    def preserved(self,row):
        old,kept=row['originalPin'],row['preservedPin']
        need(key(old)[0]!=key(kept)[0] and key(old)[1:]==key(kept)[1:],'SOURCE_PRESERVED_IDENTITY')
        self.raw(kept)

    def reader_pin(self,original):
        row=self.reader_rows.get(original['path'])
        if row is None:publication.verify_bytes(original);return original
        need(row['originalPin']==original,'SOURCE_READER_ORIGINAL_CHANGED');self.preserved(row)
        return next(p for p in self.current_pins if p['path']==original['path'])

    def verify_acceptance_inputs(self,originals,derived):
        need(originals==self.acceptance_attempt['inputPins'],'SOURCE_LOGICAL_ORIGINAL_CHANGED')
        old={key(p)[0]:p for p in originals};new={key(p)[0]:p for p in derived}
        need(len(old)==len(originals) and len(new)==len(derived),'SOURCE_LOGICAL_DUPLICATE')
        physical={p['path']:p for p in self.finish()}
        allowed={r['originalPin']['path']:r for r in [*self.source_roles.values(),*self.reader_rows.values()]}
        for path,reference in old.items():
            if new.get(path)==reference:continue
            row=allowed.get(path)
            need(row is not None and row['originalPin']==reference,'SOURCE_LOGICAL_INPUT_CHANGED')
            self.preserved(row)
            if path==self.source_roles['catalogue']['originalPin']['path']:
                need(path not in new,'SOURCE_LOGICAL_CATALOGUE_CHANGED')
            else:need(new.get(path)==publication.file_pin(path),'SOURCE_LOGICAL_READER_CHANGED')
        for path,reference in new.items():
            if path not in old:need(physical.get(path)==reference,'SOURCE_LOGICAL_EXTRA_INPUT')

    def finish(self):
        for reference in self.private_pins:continuation.private_raw(self.private,reference,[])
        unique={}
        for reference in [*self.physical_pins,*self.current_pins]:
            publication.verify_bytes(reference)
            need(reference['path'] not in unique or unique[reference['path']]==reference,'SOURCE_PHYSICAL_CONFLICT')
            unique[reference['path']]=reference
        return list(unique.values())


def load_source_roles(task,private,custody_pin):
    task=Path(task).resolve(strict=True);private=Path(private).resolve(strict=True)
    need(task==Path(__file__).resolve().parent,'SOURCE_TASK_SCOPE')
    records=contract.Records(task);pins=[];value=continuation.private_json(private,custody_pin,pins)
    fields={'schemaVersion','selectionPin','baseHistoricalCustodyPin','acceptanceInputsPin','acceptanceAttemptPin',
            'attemptPins','sourceRoles','readerCustodies','currentReaderPins'}
    need(type(value) is dict and set(value)==fields and value['schemaVersion']=='MainProgramSpugHistoricalSourceRoles/v1',
         'SOURCE_FIELDS_INVALID')
    need(value['selectionPin']['file']=='main-program-current-installations-b5fa4c5-r7-v4.json','SOURCE_SELECTION_SCOPE')
    selected=records.pinned(value['selectionPin']);inputs=records.pinned(selected['verificationInputsPin'])
    need(selected['schemaVersion']=='TaskMainProgramInstallations/v4' and
         value['acceptanceInputsPin']==selected['verificationInputsPin'] and
         inputs['schemaVersion']=='MainProgramSpugControlGenerationAcceptanceInputs/v1' and
         inputs['historicalReadCustodyPin']==value['baseHistoricalCustodyPin'],'SOURCE_INPUT_BINDING')
    base=continuation.private_json(private,value['baseHistoricalCustodyPin'],pins)
    need(base['schemaVersion']=='MainProgramSpugHistoricalReadCustody/v1' and value['attemptPins']==base['attemptPins'] and
         set(value['attemptPins'])==set(LABELS),'SOURCE_ATTEMPT_SET')
    core=records.pinned(selected['spugInstallationPin']);rich=continuation.private_json(private,core['privateEvidencePin'],pins)
    need(core['acceptanceInputsPin']==value['acceptanceInputsPin'] and rich['attemptPin']==value['acceptanceAttemptPin'] and
         core['attemptPin']==value['acceptanceAttemptPin'],'SOURCE_ACCEPTANCE_ATTEMPT')
    attempt=continuation.private_json(private,value['acceptanceAttemptPin'],pins)
    need(attempt['schemaVersion']=='MainProgramSpugControlGenerationAcceptance/v1' and attempt['recordType']=='attempt' and
         attempt['acceptanceInputsPin']==value['acceptanceInputsPin'] and
         attempt['historicalReadCustodyPin']==value['baseHistoricalCustodyPin'],'SOURCE_ACCEPTANCE_BINDING')
    result=SourceRoles(task,private,value,pins,records,attempt,base);result.finish();return result


class HistoricalReadContext:
    """Private invocation state, indexed by attempt and complete original pin."""
    def __init__(self,task,private,value,attempts,pins,*,source_roles=None):
        self.task,self.private=task,private
        self.value=deepcopy(value);self.attempts=deepcopy(attempts)
        self.physical_pins=deepcopy(pins);self.current_pins=deepcopy(value['currentReaderPins'])
        self.source_roles=source_roles
        self.mappings={name:{} for name in LABELS};self.consumed=set()
        required={str(task/name) for name in (*READERS,Path(__file__).name)}
        need(type(self.current_pins) is list and len(self.current_pins)==len(required) and
             {key(p)[0] for p in self.current_pins}==required,'CURRENT_READER_SET_INVALID')
        for name in READERS:
            loaded=importlib.import_module(Path(name).stem)
            need(Path(loaded.__file__).resolve(strict=True)==task/name,'LOADED_READER_CHANGED')
        if source_roles is None:
            for pin in self.current_pins:publication.verify_bytes(pin)
        else:
            need(type(source_roles) is SourceRoles and source_roles.value['attemptPins']==value['attemptPins'],
                 'SOURCE_CONTEXT_BINDING')
            self.current_pins=[source_roles.reader_pin(pin) for pin in self.current_pins]
        source=value['activationSource']
        need(type(source) is dict and set(source)=={'originalPin','preservedPin'},'ACTIVATION_FIELDS_INVALID')
        need(source['originalPin']==dict(path=str(task/'main_program_control_activation.py'),bytes=ACTIVATION_BYTES,
             sha256=ACTIVATION_SHA) and type(source['originalPin']['bytes']) is int,'ACTIVATION_IDENTITY_INVALID')
        for label in LABELS:self._add(label,source)
        rows=value['readerCustodies']
        need(type(rows) is list,'READER_CUSTODY_INVALID')
        seen=set();names=set()
        for row in rows:
            need(type(row) is dict and set(row)=={'attempt','originalPin','preservedPin','currentPin'},'READER_ROW_INVALID')
            label=row['attempt'];old=row['originalPin'];current=row['currentPin']
            need(label in LABELS and key(old)[0] in {str(task/name) for name in READERS},'READER_SCOPE_INVALID')
            identity=(label,key(old));need(identity not in seen,'READER_DUPLICATE');seen.add(identity)
            need(current in self.current_pins and current['path']==old['path'],'CURRENT_READER_CHANGED')
            self._add(label,{k:row[k] for k in ('originalPin','preservedPin')});names.add(Path(old['path']).name)
        need(names==set(READERS),'READER_SET_INCOMPLETE')
        if source_roles is not None:
            for label in LABELS:self._add(label,source_roles.source_roles['catalogue'])

    def _add(self,label,row):
        old,kept=row['originalPin'],row['preservedPin'];identity=key(old)
        originals=self.attempts[label]['inputPins']
        need(sum(p==old for p in originals)==1,'SOURCE_NOT_IN_ATTEMPT')
        need(identity not in self.mappings[label],'MAPPING_CONFLICT')
        need(key(kept)[0]!=old['path'] and key(kept)[1:]==identity[1:],'PRESERVED_IDENTITY_CHANGED')
        raw=continuation.private_raw(self.private,kept,self.physical_pins)
        need(len(raw)==old['bytes'] and hashlib.sha256(raw).hexdigest()==old['sha256'],'PRESERVED_BYTES_CHANGED')
        self.mappings[label][identity]=deepcopy(row)

    def verify_reference(self,label,reference,pins):
        need(label in LABELS and reference in self.attempts[label]['inputPins'],'ORIGINAL_NOT_BOUND')
        row=self.mappings[label].get(key(reference))
        if row is None:
            publication.verify_bytes(reference);pins.append(reference)
        else:
            # Additional custody stays outside the old derived logical input set.
            continuation.private_raw(self.private,row['preservedPin'],self.physical_pins)

    def verify_inputs(self,label,attempt_pin,originals,existing,pins):
        need(label in LABELS and attempt_pin==self.value['attemptPins'][label] and
             originals==self.attempts[label]['inputPins'],'ATTEMPT_INPUT_CHANGED')
        need(type(existing) is dict and len({key(p)[0] for p in originals})==len(originals),'ORIGINAL_INPUT_SET_INVALID')
        indexed={p['path']:p for p in originals}
        for path,row in existing.items():
            need(type(row) is dict and set(row)=={'originalPin','preservedPin'} and
                 path in indexed and row['originalPin']==indexed[path],'EXISTING_MAPPING_NOT_BOUND')
            need(key(row['originalPin']) not in self.mappings[label],'MAPPING_CONFLICT')
        for old in originals:
            if old['path'] in existing:
                row=existing[old['path']]
                raw=continuation.private_raw(self.private,row['preservedPin'],pins)
                need(len(raw)==old['bytes'] and hashlib.sha256(raw).hexdigest()==old['sha256'],'EXISTING_BYTES_CHANGED')
            else:self.verify_reference(label,old,pins)
        self.consumed.add(label)

    def assert_expected_inputs(self,label,originals,expected):
        """Compare derived and immutable sets without rewriting either set."""
        need(originals==self.attempts[label]['inputPins'],'ORIGINAL_INPUT_CHANGED')
        actual={key(p)[0]:p for p in originals};derived={key(p)[0]:p for p in expected}
        omitted=set()
        if self.source_roles is not None:
            catalogue=self.source_roles.source_roles['catalogue']['originalPin']
            if catalogue in originals and catalogue['path'] not in derived:omitted.add(catalogue['path'])
        need(len(actual)==len(originals) and len(derived)==len(expected) and set(actual)-omitted==set(derived),
             'EXPECTED_INPUT_SET_CHANGED')
        for path,old in actual.items():
            if path in omitted:self.verify_reference(label,old,[]);continue
            if old==derived[path]:continue
            need(key(old) in self.mappings[label] and publication.file_pin(path)==derived[path],
                 'EXPECTED_LOGICAL_INPUT_CHANGED')
            self.verify_reference(label,old,[])

    def reader_version(self,old,current):
        need(current in self.current_pins and old['path']==current['path'],'READER_CURRENT_CHANGED')
        publication.verify_bytes(current)
        matches=[label for label in LABELS if key(old) in self.mappings[label]]
        need(matches and Path(old['path']).name in READERS,'READER_VERSION_NOT_BOUND')
        for label in matches:self.verify_reference(label,old,[])
        return old

    def finish(self):
        for reference in [*self.physical_pins,*self.current_pins]:publication.verify_bytes(reference)
        unique={}
        for pin in [*self.physical_pins,*self.current_pins]:
            need(pin['path'] not in unique or unique[pin['path']]==pin,'PHYSICAL_INPUT_CONFLICT');unique[pin['path']]=pin
        return list(unique.values())


def load_context(task,private,custody_pin,*,source_roles=None):
    task=Path(task).resolve(strict=True);private=Path(private).resolve(strict=True)
    need(task==Path(__file__).resolve().parent,'TASK_SCOPE_INVALID')
    pins=[];value=continuation.private_json(private,custody_pin,pins)
    if source_roles is not None:
        need(type(source_roles) is SourceRoles and source_roles.value['baseHistoricalCustodyPin']==custody_pin,
             'SOURCE_BASE_CUSTODY_CHANGED')
    fields={'schemaVersion','selectionPin','verificationInputsPin','verificationCorePin','resourceTransitionReferencePin',
            'attemptPins','activationSource','readerCustodies','currentReaderPins'}
    need(type(value) is dict and set(value)==fields and value['schemaVersion']=='MainProgramSpugHistoricalReadCustody/v1',
         'CUSTODY_FIELDS_INVALID')
    records=contract.Records(task)
    need(value['selectionPin']['file']==SELECTOR,'SELECTION_SCOPE_INVALID')
    selected=records.pinned(value['selectionPin'])
    need(selected.get('schemaVersion')=='TaskMainProgramInstallations/v4' and
         value['verificationInputsPin']==selected['verificationInputsPin'] and
         value['verificationCorePin']==selected['spugInstallationPin'],'SELECTION_BINDING_CHANGED')
    vi=records.pinned(value['verificationInputsPin']);core=records.pinned(value['verificationCorePin'])
    need(vi.get('schemaVersion')=='MainProgramSpugPublicationVerificationInputs/v2' and
         vi['resourceTransitionPin']==value['resourceTransitionReferencePin'] and
         vi['outputFile']==value['verificationCorePin']['file'] and core.get('status')=='PASS','VERIFICATION_BINDING_CHANGED')
    base=records.pinned(vi['baseVerificationInputsPin'])
    need(base.get('schemaVersion')=='MainProgramSpugPublicationVerificationInputs/v1' and
         base['controlGenerationPin']==selected['controlGenerationPin'],'BASE_BINDING_CHANGED')
    c1=records.pinned(base['continuationInputsPin']);dep=records.pinned(base['dependencyActivationPin'])
    wrapper=records.pinned(vi['resourceTransitionPin'])
    need(wrapper.get('schemaVersion')=='MainProgramSpugResourceTransitionReaderCustody/v1','TRANSITION_WRAPPER_REQUIRED')
    transition=records.pinned(wrapper['transitionCorePin'])
    need(wrapper['attemptPin']==transition['attemptPin'],'TRANSITION_ATTEMPT_CHANGED')
    rich_pin=publication.file_pin(private/(value['verificationCorePin']['file'][:-5]+'.private.json'))
    rich=continuation.private_json(private,rich_pin,pins)
    expected=dict(publication=c1['originalAttemptPin'],continuation=base['continuationAttemptPin'],
        dependency=dep['attemptPin'],resourceTransition=transition['attemptPin'],verification=rich['attemptPin'])
    need(value['attemptPins']==expected and len({key(p)[0] for p in expected.values()})==5,'ATTEMPT_SET_CHANGED')
    schemas=('MainProgramSpugPublicationAttempt/v2','MainProgramSpugPublicationAttempt/v3',
        'MainProgramSpugRuntimeDependencyAttempt/v1','MainProgramSpugResourceTransitionAttempt/v1','MainProgramSpugVerificationAttempt/v1')
    attempts={}
    for (label,reference),schema in zip(expected.items(),schemas):
        attempt=continuation.private_json(private,reference,pins)
        need(attempt.get('schemaVersion')==schema and type(attempt.get('inputPins')) is list and
             len({key(p)[0] for p in attempt['inputPins']})==len(attempt['inputPins']),'ATTEMPT_SCHEMA_INVALID')
        attempts[label]=attempt
    context=HistoricalReadContext(task,private,value,attempts,pins+records.path_pins(),source_roles=source_roles)
    context.selected=deepcopy(selected);context.finish()
    return context


def load_historical_publication(task,private,custody_pin):
    from main_program_spug_publication_verify_only import validate_publication_v4,unique_pins
    context=load_context(task,private,custody_pin)
    verified=validate_publication_v4(contract.Records(task),Path(private),context.selected,historical=context)
    need(context.consumed==set(LABELS),'HISTORY_CONSUMPTION_INCOMPLETE')
    return dict(generation=verified['generation'],inputPins=unique_pins(verified['inputPins']+context.finish()))
