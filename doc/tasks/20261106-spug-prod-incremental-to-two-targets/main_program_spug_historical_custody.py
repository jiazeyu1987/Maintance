"""Read one explicitly bound completed Spug history; no transport or writes.

Historical logical inputs keep their original identities. Physical preserved
sources and current readers are checked separately and never replace a report.
"""
from copy import deepcopy
import hashlib
import importlib
from pathlib import Path

import main_program_installation_selection as contract
import main_program_spug_publication as publication
import main_program_spug_publication_continuation as continuation

SELECTOR='main-program-current-installations-45dd7dc-r6-v4.json'
READERS=('main_program_spug_publication_continuation.py','spug_runtime_dependency_completion.py',
         'main_program_spug_publication_verify_only.py','main_program_spug_resource_transition.py')
LABELS=('publication','continuation','dependency','resourceTransition','verification')
ACTIVATION_BYTES=107657
ACTIVATION_SHA='963bbe907d1d2f7334ee9fa5d8598a5659361ca512d23514d92d9721b91146bb'


def need(condition,code):
    if not condition:raise ValueError('SPUG_HISTORICAL_'+code)


def key(pin):
    need(type(pin) is dict and set(pin)=={'path','bytes','sha256'} and type(pin['path']) is str and
         type(pin['bytes']) is int and pin['bytes']>=0 and contract.sha(pin['sha256']),'PIN_INVALID')
    return pin['path'],pin['bytes'],pin['sha256']


class HistoricalReadContext:
    """Private invocation state, indexed by attempt and complete original pin."""
    def __init__(self,task,private,value,attempts,pins):
        self.task,self.private=task,private
        self.value=deepcopy(value);self.attempts=deepcopy(attempts)
        self.physical_pins=deepcopy(pins);self.current_pins=deepcopy(value['currentReaderPins'])
        self.mappings={name:{} for name in LABELS};self.consumed=set()
        required={str(task/name) for name in (*READERS,Path(__file__).name)}
        need(type(self.current_pins) is list and len(self.current_pins)==len(required) and
             {key(p)[0] for p in self.current_pins}==required,'CURRENT_READER_SET_INVALID')
        for name in READERS:
            loaded=importlib.import_module(Path(name).stem)
            need(Path(loaded.__file__).resolve(strict=True)==task/name,'LOADED_READER_CHANGED')
        for pin in self.current_pins:publication.verify_bytes(pin)
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
        need(len(actual)==len(originals) and len(derived)==len(expected) and set(actual)==set(derived),
             'EXPECTED_INPUT_SET_CHANGED')
        for path,old in actual.items():
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


def load_context(task,private,custody_pin):
    task=Path(task).resolve(strict=True);private=Path(private).resolve(strict=True)
    need(task==Path(__file__).resolve().parent,'TASK_SCOPE_INVALID')
    pins=[];value=continuation.private_json(private,custody_pin,pins)
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
    context=HistoricalReadContext(task,private,value,attempts,pins+records.path_pins())
    context.selected=deepcopy(selected);context.finish()
    return context


def load_historical_publication(task,private,custody_pin):
    from main_program_spug_publication_verify_only import validate_publication_v4,unique_pins
    context=load_context(task,private,custody_pin)
    verified=validate_publication_v4(contract.Records(task),Path(private),context.selected,historical=context)
    need(context.consumed==set(LABELS),'HISTORY_CONSUMPTION_INCOMPLETE')
    return dict(generation=verified['generation'],inputPins=unique_pins(verified['inputPins']+context.finish()))
