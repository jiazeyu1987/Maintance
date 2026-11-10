"""Read immutable control-only generations; never infer a Spug publication.

All I/O is local and pin-bound. Imports do not read evidence or call prepare.
Historical remote paths in custody are recipes, not claims of a fresh observation.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

import main_program_installation_selection as contract

MAX_GENERATIONS = 64
SCHEMA = 'MainProgramControlGeneration/v1'
FIELDS = {'schemaVersion','status','sourceCommit','buildPin','planPin','predecessor',
    'controllersByHost','activationEvidenceByHost','sourceBaselinePin','selectorsPublished',
    'spugResourceInstalled','backupDispatched','restoreDispatched'}
FALSE_FIELDS = ('selectorsPublished','spugResourceInstalled','backupDispatched','restoreDispatched')
SOURCES = ('intruoyi-57-safe-20261024-v1','intruoyi-59-safe-20261024-v1','intruoyi-PROD57-20261019')
SELECTION_CONTROLLER_KEYS = ('role',*contract.CONTROLLER_KEYS,'dropinPin')


def need(value, code):
    if not value: raise ValueError('MAIN_GENERATION_'+code)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')


def _private(private, reference, pins, *, name=None):
    # Existing loader includes duplicate-key, private-root and byte identity checks.
    from main_program_spug_publication import private_document
    need(type(reference) is dict and set(reference)=={'path','bytes','sha256'} and
        type(reference['bytes']) is int and 0<reference['bytes']<=16*1024*1024 and
        contract.sha(reference['sha256']), 'PRIVATE_PIN_INVALID')
    value=private_document(private,reference,name)
    pins.append(reference)
    return value


def _documents(private_plan):
    need(type(private_plan['documentsByHost']) is dict and set(private_plan['documentsByHost'])==set(contract.HOSTS),
        'DOCUMENT_HOSTS_INVALID')
    result={}
    for host,rows in private_plan['documentsByHost'].items():
        need(type(rows) is list,'DOCUMENTS_INVALID')
        result[host]={}
        for row in rows:
            need(type(row) is dict and set(row)=={'pin','value'},'DOCUMENT_INVALID')
            reference=contract.remote_pin(row['pin']);raw=canonical(row['value'])
            need(len(raw)==reference['bytes'] and hashlib.sha256(raw).hexdigest()==reference['sha256'],
                'DOCUMENT_PIN_CHANGED')
            need(reference['path'] not in result[host],'DOCUMENT_DUPLICATE')
            result[host][reference['path']]=row
    return result


def _plan(records,value,targets,previous):
    if previous is None:
        return contract._plan(records,value,targets)
    plan=records.pinned(value['planPin'])
    revision=plan.get('revisionId')
    need(plan.get('schemaVersion')=='MainProgramConfigurationPlan/v2' and
        type(revision) is str and re.fullmatch('r[1-9][0-9]*',revision) and
        value['planPin']['file']=='main-program-configuration-plan-'+value['sourceCommit'][:7]+'-'+revision+'.json',
        'PLAN_REVISION_INVALID')
    need(plan['predecessorGenerationPin']==previous['generationPin'] and
        plan['previousPlanPin']==previous['generation']['planPin'] and plan['buildPin']==value['buildPin'],
        'PLAN_PREDECESSOR_CHANGED')
    need(plan['sourceCommit']==value['sourceCommit'] and plan['status']=='PLAN_ONLY_NOT_ACTIVATED' and
        plan['hosts']==list(contract.HOSTS) and set(plan['controllers'])==set(contract.HOSTS) and
        plan['targetObjectsUnchanged'] is True and plan['restoreDispatched'] is False and
        plan['installationPerformed'] is False,'PLAN_NOT_PROVEN')
    need(all(type(plan[k]) is int and plan[k]==n for k,n in
        [('registrationCount',12),('applicationCount',33),('originalTaskCount',3),('sourceArchiveProtectionCount',9)]) and
        plan['sourceRefs']==list(SOURCES) and plan['programTargets']==[targets[h] for h in contract.HOSTS],
        'PLAN_COUNTS_CHANGED')
    return plan


def _upgrade_build(records,value):
    # Generic committed builds have no legacy packages list. The independent
    # coverage reader below verifies both actual packages, including every byte.
    reference=value['buildPin'];build=records.pinned(reference)
    need(reference['file']=='release-build-'+value['sourceCommit'][:7]+'.json' and
        build.get('status')=='PASS' and build.get('targetCommit')==value['sourceCommit'] and
        build.get('allFilesShaAndCompileVerified') is True and type(build.get('fileCount')) is int and
        build['fileCount']==147 and contract.sha(build.get('packageSha256')) and
        contract.sha(build.get('fileManifestSha256')) and build.get('newCommits') is False and
        build.get('mergeRequired') is False,'BUILD_NOT_PROVEN')
    return build


def _partition(plan,secret,previous,docs):
    need(all(secret[k]==plan[k] for k in ('revisionId','predecessorGenerationPin','previousPlanPin',
        'buildPin','packageDeltaPin')) and secret['currentSelections']==previous['selections'],
        'PRIVATE_PREDECESSOR_CHANGED')
    for group in ('newDocumentsByHost','retainedDocumentsByHost'):
        need(type(secret[group]) is dict and set(secret[group])==set(contract.HOSTS) and
            type(plan[group]) is dict and set(plan[group])==set(contract.HOSTS),'PARTITION_HOSTS_CHANGED')
    old_docs=_documents(previous['privatePlan'])
    for host in contract.HOSTS:
        fresh=secret['newDocumentsByHost'][host];retained=secret['retainedDocumentsByHost'][host]
        need(type(fresh) is list and type(retained) is list and len(fresh)==(4 if host=='57' else 2) and
            len(retained)==9 and secret['documentsByHost'][host]==fresh+retained,'PARTITION_CHANGED')
        paths=[r['pin']['path'] for r in fresh+retained]
        need(len(paths)==len(set(paths)) and set(paths)==set(docs[host]),'PARTITION_OVERLAP')
        need(all(plan[k][host]==[r['pin'] for r in secret[k][host]]
            for k in ('newDocumentsByHost','retainedDocumentsByHost')),'PUBLIC_PARTITION_CHANGED')
        old=previous['controllersByHost'][host]
        consumed={r[k]['path'] for r in old for k in ('ownerConfigurationPin','controlConfigurationPin')}
        need(retained==[r for path,r in old_docs[host].items() if path not in consumed],
            'RETAINED_DOCUMENT_CHANGED')
        wanted={row[k]['path'] for row in secret['controllers'][host] for k in ('ownerPin','controlPin')}
        need({r['pin']['path'] for r in fresh}==wanted and not wanted.intersection(old_docs[host]),
            'NEW_DOCUMENT_CHANGED')


def _upgrade_rich(records,private,reference,core,value,plan,previous,private_pins):
    from main_program_control_activation import validate_generation_inputs,predecessors
    from main_program_spug_publication import validate_activation_evidence
    host=core['host'].rsplit('.',1)[-1];role=core['role']
    name='main-program-control-activation-'+host+'-'+role+'-'+value['sourceCommit'][:7]+'-'+plan['revisionId']
    rich=_private(private,reference,private_pins,name=name+'.private.json')
    validate_activation_evidence(core,rich)
    need(rich.get('previousControlGenerationPin')==previous['generationPin'] and
        rich.get('revisionId')==plan['revisionId'],'ACTIVATION_PREDECESSOR_CHANGED')
    inputs=records.pinned(rich['activationInputsPin']);validate_generation_inputs(inputs)
    expected=dict(sourceCommit=value['sourceCommit'],suffix=host,role=role,revisionId=plan['revisionId'],
        buildPin=value['buildPin'],planPin=value['planPin'],previousControlGenerationPin=previous['generationPin'],
        coveragePin=rich['coveragePin'],sourceBaselinePin=value['sourceBaselinePin'],outputFile=name+'.json')
    need(all(inputs[k]==v for k,v in expected.items()),'ACTIVATION_INPUTS_CHANGED')
    need(inputs['precedingActivationPins']==[value['controllersByHost'][h][contract.ROLES[h].index(r)]
        for h,r in predecessors(host,role)],'ACTIVATION_ORDER_CHANGED')
    # These are original local reports, not fresh server observations. They all
    # remain in the final immutable input closure even when their JSON was cached.
    for key in ('engineStagedPin','configurationStagedPin','unitObservationPin',
        'originalEnvironmentObservationPin','coveragePin'):
        records.pinned(inputs[key])
    return rich,inputs


def _validate_upgrade_materials(records,private,inputs,build,previous,plan,secret):
    from main_program_control_activation import validate_generation_coverage
    from main_program_control_upgrade_plan import validate_control_upgrade_plan
    proof=validate_generation_coverage(records,inputs,previous)
    need(proof['build']==build and proof['coverage']['actualPackageEvidencePins'][0]==plan['packageDeltaPin'],
        'COVERAGE_PLAN_CHANGED')
    def material(reference):
        records.pinned(reference);raw=(records.task/reference['file']).read_bytes()
        need(len(raw)==reference['bytes'] and hashlib.sha256(raw).hexdigest()==reference['sha256'],
            'INPUT_CHANGED_DURING_READ')
        return dict(pin=reference,raw=raw)
    validate_control_upgrade_plan(plan,secret,source_commit=inputs['sourceCommit'],revision_id=plan['revisionId'],
        build_document=material(inputs['buildPin']),package_delta_document=material(plan['packageDeltaPin']),
        package_files=proof['packageFiles'],previous_package_files=proof['previousPackageFiles'],predecessor=previous,
        private_plan_path=plan['privatePlanPin']['path'],observed_at=plan['observedAt'])
    return proof['physicalPins']


def _baseline(records,reference):
    value=records.pinned(reference)
    need(value.get('status')=='PASS' and value.get('sourceConfigRef')==SOURCES[0] and
        value.get('pointType')=='INCREMENTAL' and value.get('state')=='SUCCEEDED' and
        type(value.get('actualExitCode')) is int and value['actualExitCode']==0 and value.get('sourceRestored') is True and
        type(value.get('chain')) is list and len(value['chain'])>=1 and
        value['chain'][-1]['operationId']==value['operationId'],'SOURCE_BASELINE_INVALID')
    return value


def _layered_observation(observation,custody,receipt):
    need(type(observation) is dict and observation.get('status')=='PASS' and
        type(observation.get('activationCount')) is int and
        observation['activationCount']==len(custody['legacyCustody']['steps'])+len(custody['mainSteps']) and
        type(observation.get('legacyActivationCount')) is int and
        observation['legacyActivationCount']==len(custody['legacyCustody']['steps']) and
        observation.get('selectedCurrentReceiptPin')==receipt and
        observation.get('originalInventoryVerified') is True and
        observation.get('allReceiptAndConfigurationPinsVerified') is True and
        observation.get('packageManifestsVerified') is True and observation.get('serverWrites') is False,
        'LAYERED_PROOF_CHANGED')


def _recipe(base,inventory,cores,riches,previous=None):
    core=cores[0];rich=riches[0]
    step={key:deepcopy(core[key]) for key in ('sourceCommit','engine','previousReceiptPin','currentReceiptPin',
        'ownerConfigurationPin','controlConfigurationPin','dropinPin')}
    package=contract.remote_pin(rich['packageJsonPin'])
    need(package['path']==core['engine']+'/package.json','PACKAGE_MANIFEST_PATH_CHANGED')
    step['packagePin']=package
    if previous is None:
        old=deepcopy(base['extendedCustody'])
        need(old['steps'][-1]['currentReceiptPin']==base['currentReceiptPin'],'LEGACY_TERMINAL_CHANGED')
        result=dict(schemaVersion='MainProgramReceiptCustody/v1',
            **{k:deepcopy(old[k]) for k in ('root','targetConfigRef','sourceConfigRef','service')},
            legacyCustody=old,originalInventory=deepcopy(inventory),mainSteps=[])
    else:result=deepcopy(previous)
    prior=result['mainSteps'][-1]['currentReceiptPin'] if result['mainSteps'] else result['legacyCustody']['steps'][-1]['currentReceiptPin']
    need(all(core['previousReceiptPin'][k]==prior[k] for k in ('bytes','sha256')) and
        core['currentReceiptPin']['path']==prior['path'],'RECEIPT_CHAIN_GAP')
    need(core['previousReceiptPin']['path']==str(PurePosixPath(result['root'])/'configuration'/
        ('target-installation-before-main-'+core['sourceCommit'][:7]+'.json')),'RECEIPT_ARCHIVE_PATH_CHANGED')
    refs=result['originalInventory']['evidencePins'];original=result['legacyCustody']['originalActiveReceiptPin']
    need(result['originalInventory']['status']=='PASS' and len(refs)==result['originalInventory']['protectedFiles'] and
        len({r['path'] for r in refs})==len(refs) and [r for r in refs if r['path']==original['path']]==[original],
        'ORIGINAL_INVENTORY_CHANGED')
    if previous is None:
        observation=rich.get('previousCustodyObservation')
        need(type(observation) is dict and observation.get('status')=='PASS' and
            observation.get('activationCount')==len(result['legacyCustody']['steps']) and
            observation.get('activatedGenerationCommits')==result['legacyCustody']['expectedGenerationCommits'] and
            observation.get('selectedCurrentReceiptPin')==prior and
            observation.get('originalActiveReceiptPin')==original and
            observation.get('allReceiptAndConfigurationPinsVerified') is True and
            observation.get('allHistoricalSourceAndTargetDefinitionsUnchanged') is True,'LEGACY_PROOF_CHANGED')
    else:
        _layered_observation(rich.get('previousCustodyObservation'),result,prior)
    result['mainSteps'].append(step)
    result.update(selectedOwnerPin=core['ownerConfigurationPin'],selectedControlPin=core['controlConfigurationPin'],
        selectedCurrentReceiptPin=core['currentReceiptPin'])
    if previous is not None:
        _layered_observation(rich.get('currentLayeredCustodyObservation'),result,core['currentReceiptPin'])
    return result


def _validate(records,private,value,generation_pin,trail):
    need(type(value) is dict and set(value)==FIELDS and value['schemaVersion']==SCHEMA and value['status']=='PASS' and
        type(value['sourceCommit']) is str and re.fullmatch('[0-9a-f]{40}',value['sourceCommit']) and
        all(value[k] is False for k in FALSE_FIELDS),'SCHEMA_INVALID')
    for key in ('controllersByHost','activationEvidenceByHost'):
        need(type(value[key]) is dict and set(value[key])==set(contract.HOSTS),'FOUR_CONTROLS_REQUIRED')
        need(all(type(value[key][host]) is list and len(value[key][host])==len(roles)
            for host,roles in contract.ROLES.items()),'FOUR_CONTROLS_REQUIRED')
    predecessor=value['predecessor'];need(type(predecessor) is dict,'PREDECESSOR_INVALID')
    previous=None;private_pins=[]
    if predecessor.get('kind')=='AUTOMATIC_INSTALLATION':
        need(set(predecessor)=={'kind','selectionPin'},'PREDECESSOR_INVALID')
        base_pin=predecessor['selectionPin'];base=contract._previous(records,base_pin)
        old_selection=records.pinned(base_pin);source=records.pinned(old_selection['source57'])
        old_controllers={'57':source['controllers'],**{h:[base[h]] for h in ('58','59')}}
        targets={'57':'intruoyi-main-57-safe-restore-20261105-v2',**{h:base[h]['targetConfigRef'] for h in base}}
    else:
        need(predecessor.get('kind')=='CONTROL_GENERATION' and set(predecessor)=={'kind','generationPin'},
            'PREDECESSOR_INVALID')
        # A predecessor's selection must not acquire the descendant files that
        # happened to be read before recursion. Its own closure is merged below.
        previous=_load(contract.Records(records.task),private,predecessor['generationPin'],trail=trail)
        need(previous['generation']['sourceCommit']!=value['sourceCommit'],'PREDECESSOR_COMMIT_REPEATED')
        base_pin=previous['selections']['57']['baseAutomaticSelectionPin'];base={}
        targets=previous['targets'];old_controllers=previous['controllersByHost'];private_pins+=previous['inputPins']
    build=contract._build(records,value) if previous is None else _upgrade_build(records,value)
    plan=_plan(records,value,targets,previous)
    need(plan.get('sourceRefs')==list(SOURCES) and plan.get('sourceArchiveProtectionCount')==9,'SOURCE_PLAN_CHANGED')
    filename=('main-program-configuration-plan-r4.private.json' if previous is None else
        'main-program-configuration-plan-'+value['sourceCommit'][:7]+'-'+plan['revisionId']+'.private.json')
    secret=_private(private,plan['privatePlanPin'],private_pins,name=filename)
    need(secret['schemaVersion']==('MainProgramConfigurationInstallationPlan/v1' if previous is None else
        'MainProgramConfigurationInstallationPlan/v2') and secret['sourceCommit']==value['sourceCommit'] and
        secret['status']==plan['status'] and secret['build']==build,'PRIVATE_PLAN_CHANGED')
    docs=_documents(secret)
    need(set(secret['controllers'])==set(contract.HOSTS),'PRIVATE_CONTROLS_CHANGED')
    if previous:_partition(plan,secret,previous,docs)
    cores={};riches={};custodies={};all_core_files=set();upgrade_inputs=None
    from main_program_spug_publication import load_activation_evidence
    for host,roles in contract.ROLES.items():
        planned=secret['controllers'][host]
        need([{k:r[k] for k in ('role','service','engine','controlPin','ownerPin')} for r in planned]==plan['controllers'][host] and
            len(docs[host])==plan['documents'][host],'PRIVATE_CONTROLS_CHANGED')
        selected=secret['currentSelections'][host]
        need(selected.get('currentInstallationSelectionPin' if previous is None else 'currentControlGenerationPin')==
            (base_pin if previous is None else previous['generationPin']),'PRIVATE_PREDECESSOR_CHANGED')
        if previous is not None:
            need(secret['predecessorGenerationPin']==previous['generationPin'] and
                secret['previousPlanPin']==previous['generation']['planPin'],'PRIVATE_PREDECESSOR_CHANGED')
        cores[host]=[];riches[host]=[]
        for index,role in enumerate(roles):
            row=planned[index];old=old_controllers[host][index]
            need(row['service']==old['service'],'PREDECESSOR_SERVICE_CHANGED')
            for field,old_field in [('previousControlPin','controlConfigurationPin'),('previousOwnerPin','ownerConfigurationPin')]:
                if previous is not None or field in row:
                    need(row[field]==old[old_field],'PREDECESSOR_CONFIGURATION_CHANGED')
            ref=value['controllersByHost'][host][index]
            ending='' if previous is None else '-'+plan['revisionId']
            need(ref['file']=='main-program-control-activation-'+host+'-'+role+'-'+value['sourceCommit'][:7]+ending+'.json' and
                ref['file'] not in all_core_files,'ACTIVATION_FILE_INVALID')
            all_core_files.add(ref['file'])
            old_target=(base[host] if previous is None else previous['controllersByHost'][host][0]) if host!='57' else None
            core=contract._activation(records,ref,value,build,row,host,None if role=='source' else targets[host],old_target)
            for key in ('controlConfigurationPin','ownerConfigurationPin'):
                need(docs[host][core[key]['path']]['pin']==core[key],'ACTIVE_CONFIGURATION_MISSING')
            if previous is None:
                rich,pins=load_activation_evidence(records,private,value['activationEvidenceByHost'][host][index],core)
                private_pins+=pins
            else:
                rich,inputs=_upgrade_rich(records,private,value['activationEvidenceByHost'][host][index],core,
                    value,plan,previous,private_pins)
                need(upgrade_inputs is None or inputs['coveragePin']==upgrade_inputs['coveragePin'],
                    'COVERAGE_GENERATION_CHANGED')
                upgrade_inputs=inputs
            need(rich.get('registrySelectorsPublished') is False,'PUBLICATION_STATE_CHANGED')
            cores[host].append(core);riches[host].append(rich)
        if host!='57':
            inventory=records.read('protected-history-'+host+'.json')
            custodies[host]=_recipe(base.get(host),inventory,cores[host],riches[host],
                previous['custodyByHost'][host] if previous else None)
    need(len({c['pid'] for c in cores['57']})==2,'CONTROLLER_PID_COLLISION')
    baseline=_baseline(records,value['sourceBaselinePin'])
    if previous:need(value['sourceBaselinePin']==previous['generation']['sourceBaselinePin'],'SOURCE_BASELINE_CHANGED')
    if previous:private_pins+=_validate_upgrade_materials(records,private,upgrade_inputs,build,previous,plan,secret)
    if previous:
        # Coverage is fully verified above. Only this explicitly reviewed profile
        # consumes the source-policy transition, without replanning old history.
        from main_program_control_activation import make_source_policy_transition,validate_source_policy_transition
        index=contract.ROLES['57'].index('source');rich=riches['57'][index]
        inputs=records.pinned(rich['activationInputsPin']);coverage=records.pinned(inputs['coveragePin'])
        old=previous['controllersByHost']['57'][index];current=cores['57'][index]
        old_owner=next(row['value'] for row in previous['privatePlan']['documentsByHost']['57']
            if row['pin']==old['ownerConfigurationPin'])
        owner=docs['57'][current['ownerConfigurationPin']['path']]['value']
        root_audit=records.read('automatic-full-audit.json') if coverage.get('schemaVersion')=='MainProgramControlCoverage/v2' else None
        transition=make_source_policy_transition(inputs,coverage,baseline,old_owner,owner,
            root_audit=root_audit,root_audit_pin=records.references.get('automatic-full-audit.json'))
        if transition is not None:validate_source_policy_transition(transition,rich)
    pins={}
    for pin in [*records.path_pins(),*private_pins]:
        # References retain their original bytes; this physical inventory uses
        # the host's path spelling so slash direction is not mistaken for drift.
        pin=dict(pin,path=str(Path(pin['path'])))
        need(pin['path'] not in pins or pins[pin['path']]==pin,'INPUT_PIN_CONFLICT')
        pins[pin['path']]=pin
    selections={}
    for host in contract.HOSTS:
        selections[host]=dict(host='172.30.30.'+host,suffix=host,sourceCommit=value['sourceCommit'],
            currentSourceCommit=value['sourceCommit'],currentControlGenerationPin=generation_pin,baseAutomaticSelectionPin=base_pin,
            controllers=[{key:c[key] for key in SELECTION_CONTROLLER_KEYS} for c in cores[host]],
            targetConfigRef=targets[host],activeReceiptPin=None if host=='57' else cores[host][0]['currentReceiptPin'],
            localInstallationPins=list(pins.values()))
    return dict(generationPin=generation_pin,generation=value,build=build,plan=plan,privatePlan=secret,
        controllersByHost=cores,selections=selections,inputPins=list(pins.values()),targets=targets,
        sourceBaseline=baseline,custodyByHost=custodies)


def _load(records,private,reference,*,trail=()):
    need(type(reference) is dict and type(reference.get('file')) is str,'PIN_INVALID')
    need(len(trail)<MAX_GENERATIONS and reference['file'] not in trail,'PREDECESSOR_CYCLE_OR_LIMIT')
    value=records.pinned(reference)
    return _validate(records,private,value,deepcopy(reference),(*trail,reference['file']))


def _finish(bundle):
    # Cached JSON never permits a changed input to escape at the end of a read.
    from main_program_control_activation import file_pin
    for reference in bundle['inputPins']:
        need(file_pin(reference['path'])==reference,'INPUT_CHANGED_DURING_READ')
    return deepcopy(bundle)


def load_control_generation(task,private,generation_pin):
    try:return _finish(_load(contract.Records(task),Path(private),generation_pin))
    except (KeyError,TypeError,IndexError,AttributeError) as error:
        raise ValueError('MAIN_GENERATION_FORMAT_INVALID') from error


def inspect_control_generation(value,task,private):
    """Validate an in-memory proposal without creating an actual generation."""
    try:return _finish(_validate(contract.Records(task),Path(private),deepcopy(value),None,()))
    except (KeyError,TypeError,IndexError,AttributeError) as error:
        raise ValueError('MAIN_GENERATION_FORMAT_INVALID') from error


def select_control_generation(suffix,task,private,*,generation_pin):
    need(suffix in contract.HOSTS,'HOST_REQUIRED')
    return load_control_generation(task,private,generation_pin)['selections'][suffix]
