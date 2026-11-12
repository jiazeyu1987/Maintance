"""Verify the explicit original381 archive-owner relation from actual metadata.

The product already verified real remote filesystem observations. This reader
hashes those original bytes and reconstructs its final owner projection only;
it grants no source, target, payload or restore authorization.
"""
import ast,base64,hashlib,json,re
from copy import deepcopy
from pathlib import Path,PurePosixPath

SCHEMA='MainTargetArchiveOwnerConfigurationVerification/v1'
PROFILE='MAIN58_PREPARATION381_ARCHIVE_OWNER/v1'
COMMIT='b10ba57bd107733d77d74b7494ef72f07ba09205'
OPERATION='smallapp-6546b96486f7413a84c7281c95131f1f'
SOURCE='intruoyi-57-safe-20261024-v1'
POINT='smallapp-e7b668792c8f4bce945a52f984d3c660'
TARGET='intruoyi-main-58-safe-restore-20261104-v1'
STDOUT_ID=(25522600,'61035c65218422394a5ba6ac4cba35aa38f88d418030a13ef697c9bef07d90cb')
HELPER_ID=(8807,'9b3743aa7634bd6aa695a308983aec3fd0e661a800c98bbcd3c9c6d127c3f5ce')
FIELDS={'schemaVersion','profileId','stdoutPin','stderrPin','collectorScriptPin','collectorHelperPin',
    'activationWrapperPin','originalsPacketPin','originalPlanningPin','transport'}

def need(value,code):
    if not value:raise ValueError('ARCHIVE_OWNER_'+code)
def canonical(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def same(left,right):return canonical(left)==canonical(right)
def document(pairs):
    value={}
    for key,item in pairs:need(key not in value,'DUPLICATE_JSON_KEY');value[key]=item
    return value
def decode(raw):return json.loads(raw.decode('utf-8'),object_pairs_hook=document)
def pin(path):
    raw=Path(path).read_bytes();return dict(path=str(Path(path)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def _content(reference,raw):
    need(type(reference) is dict and set(reference)=={'path','bytes','sha256'} and type(reference['bytes']) is int and
        len(raw)==reference['bytes'] and hashlib.sha256(raw).hexdigest()==reference['sha256'],'ORIGINAL_BYTES')
def _private(reference,root):
    p=Path(reference['path']);need(p.is_absolute() and p.resolve(strict=True).is_relative_to(root) and not p.is_symlink(),'PRIVATE_INPUT_SCOPE')
    need(type(reference['bytes']) is int and 0<reference['bytes']<=64*1024**2,'INPUT_LIMIT')
    raw=p.read_bytes();_content(reference,raw);return raw

def verify_materialization(collection,packet,result,base_owner,operation_owner,request):
    """Rebuild the precise final projection after the actual product proof."""
    need(request==dict(schemaVersion='SmallAppBackupUiRequest/v1',operationId=OPERATION,action='RESTORE',
        sourceConfigRef=SOURCE,parentChainRef=None,recoveryPointRef=POINT,targetConfigRef=TARGET),'EXACT_ORIGINAL_SCOPE')
    need(collection['status']=='PASS' and collection['schemaVersion']=='MainTargetArchiveOwnerCollection/v1' and
        collection['host']=='172.30.30.58' and collection['sourceCommit']==COMMIT and collection['serverWrites'] is False and
        collection['payloadReads']==0 and collection['discoveryPerformed'] is False,'ACTUAL_PRODUCT_OBSERVATION')
    need(result['host']=='172.30.30.58' and result['status']=='PASS' and result['sourceCommit']==COMMIT and result['targetConfigRef']==TARGET and
        collection['pid']==result['currentController']['pid'] and collection['controlPin']==result['candidate']['controller']['controlPin'] and
        collection['baseOwnerPin']==result['candidate']['controller']['previousOwnerPin'],'ACTUAL_CONTROLLER_BINDING')
    originals=packet['originals'];need(packet['operationId']==OPERATION and packet['targetConfigRef']==TARGET and
        packet['predecessorController']==result['candidate']['previousController'] and
        collection['requestPin']==originals['request']['pin'] and collection['operationConfigurationPin']==originals['configuration']['pin'],'PACKET_BINDING')
    values={};references=[]
    need(type(collection['metadataOriginals']) is list and len(collection['metadataOriginals'])==27,'COMPLETE_METADATA_SET')
    for row in collection['metadataOriginals']:
        need(type(row) is dict and set(row)=={'pin','rawBase64'},'METADATA_ROW')
        reference=row['pin'];raw=base64.b64decode(row['rawBase64'],validate=True);_content(reference,raw)
        need(reference['path'] not in values,'METADATA_DUPLICATE');values[reference['path']]=decode(raw);references.append(reference)
    verification=collection['verification']
    need(set(verification)=={'schemaVersion','baseOwnerPin','requestPin','originals','derivedOwner','originalResultPins',
        'payloadContentVerified','sourceAdmissionGranted','targetAdmitted','clearAuthorized'} and
        verification['schemaVersion']=='ArchiveRestoreInputsVerification/v1' and verification['originalResultPins']==references and
        all(verification[k] is False for k in ('payloadContentVerified','sourceAdmissionGranted','targetAdmitted','clearAuthorized')),'PRODUCT_PROOF_CONTRACT')
    need(verification['baseOwnerPin']==collection['baseOwnerPin'] and verification['requestPin']==collection['requestPin'] and
        verification['originals']==collection['originals'] and same(values[collection['baseOwnerPin']['path']],base_owner) and
        same(values[collection['requestPin']['path']],request),'ORIGINAL_BASE_AND_REQUEST')
    root=PurePosixPath(collection['requestConfigurationsRoot'])/OPERATION
    need(root==PurePosixPath(base_owner['operationsRoot']).parent/'request-configurations'/OPERATION,'REQUEST_CONFIGURATION_ROOT')
    for key,name in (('requestInputsPin','restore-inputs.json'),('pointBindingPin','archive-point.json'),('recoveryConfigurationPin','recovery.json')):
        need(PurePosixPath(collection['originals'][key]['path'])==root/name and collection['originals'][key] in references,'REQUEST_ORIGINAL_PATH')
    inputs=values[collection['originals']['requestInputsPin']['path']]
    need(same(inputs,dict(request=request,ownerConfigurationPin=collection['baseOwnerPin'])),'REQUEST_INPUTS_BINDING')
    binding=values[collection['originals']['pointBindingPin']['path']]
    need(set(binding)=={'schemaVersion','reference','sourceConfigRef','pointPin','evidencePins'} and binding['schemaVersion']=='SmallAppArchivePointBinding/v1' and
        binding['reference']==POINT and binding['sourceConfigRef']==SOURCE and all(p in references for p in binding['evidencePins']),'POINT_BINDING')
    selected=values[binding['pointPin']['path']];points=selected['parentPointPins']+[binding['pointPin']];bindings={};scope=None
    for reference in points:
        need(reference in references,'POINT_ORIGINAL');point=values[reference['path']]
        path=str(PurePosixPath(reference['path']).parent/'recovery-repository-binding.json')
        matches=[p for p in references if p['path']==path];need(len(matches)==1,'REPOSITORY_BINDING_ORIGINAL')
        item=values[path];need(item['repositoryPointPin']==reference and item['manifestPin']==point['manifestPin'],'REPOSITORY_BINDING')
        if scope is None:scope=item['sourceScopePin']
        need(item['sourceScopePin']==scope and point['manifestPin']['sha256'] not in bindings,'CHAIN_SCOPE_OR_MANIFEST')
        bindings[point['manifestPin']['sha256']]=matches[0]
    rebuilt=deepcopy(base_owner);source=rebuilt['sources'][SOURCE]
    need('archiveCatalogue' in source,'BASE_CATALOGUE_REQUIRED');source.pop('archiveCatalogue')
    source.update(sourceScopePin=scope,recoveryPoints={POINT:binding['pointPin']},repositoryPointPins=points,
        repositoryBindingPinsByManifestSha256=bindings,parentChains={})
    need(same(rebuilt,verification['derivedOwner']) and same(rebuilt,values[collection['originals']['recoveryConfigurationPin']['path']]) and
        same(rebuilt,operation_owner),'COMPLETE_OWNER_DERIVATION')
    return rebuilt

def collection_context(private):
    root=Path(private)
    names=dict(stdoutPin='collect-retry-archive-owner-r2-stdout.private.json',stderrPin='collect-retry-archive-owner-r2-stderr.private.log',
        collectorScriptPin='collect-retry-archive-owner-r2-remote.private.py',collectorHelperPin='collect-retry-archive-owner-r2.py',
        activationWrapperPin='target-control-successor-58-b10ba57-r1-activate-result.private.json',originalsPacketPin='retained-preparation-originals-r1.private.json',
        originalPlanningPin='program-retry-successor-b10ba57-planning-r1.private.json')
    return dict(schemaVersion=SCHEMA,profileId=PROFILE,**{key:pin(root/name) for key,name in names.items()},
        transport=dict(exitCode=None,stderrClassification='WINDOWS_OPENSSH_CLOSE_NOTICE',originalCarrierStatus='FAILED'))

def verify_context(context,*,private):
    need(type(context) is dict and set(context)==FIELDS and context['schemaVersion']==SCHEMA and context['profileId']==PROFILE,'TYPED_CONTEXT')
    need(context['transport']==dict(exitCode=None,stderrClassification='WINDOWS_OPENSSH_CLOSE_NOTICE',originalCarrierStatus='FAILED'),'UNKNOWN_EXIT_PRESERVED')
    root=Path(private).resolve(strict=True);raws={key:_private(context[key],root) for key in FIELDS if key.endswith('Pin')}
    need((len(raws['stdoutPin']),hashlib.sha256(raws['stdoutPin']).hexdigest())==STDOUT_ID and
        (len(raws['collectorHelperPin']),hashlib.sha256(raws['collectorHelperPin']).hexdigest())==HELPER_ID,'ACTUAL_COLLECTION_ORIGINAL')
    need(re.fullmatch(rb'close - IO is still pending on closed socket\. read:1, write:0, io:[0-9A-Fa-f]+\r?\n',raws['stderrPin']) is not None,'PRECISE_CLOSE_NOTICE')
    collection=decode(raws['stdoutPin']);packet=decode(raws['originalsPacketPin']);wrapper=decode(raws['activationWrapperPin']);planning=decode(raws['originalPlanningPin'])
    need(wrapper['status']=='PASS' and wrapper['mode']=='ACTIVATE' and wrapper['host']=='58' and wrapper['result']['stage']=='complete' and
        wrapper['result']['schemaVersion']=='MainProgramTargetControlSuccessorActivation/v3','ACTUAL_ACTIVATION')
    need(wrapper['result']['retainedFailureAdmission']['originalsPacketPin']==context['originalsPacketPin'],'ADMITTED_PACKET')
    tree=ast.parse(raws['collectorHelperPin'].decode('utf-8'));body=[ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='BODY' for t in n.targets)]
    tree=ast.parse(raws['collectorScriptPin'].decode('utf-8'));value=[ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='VALUE' for t in n.targets)]
    need(len(body)==len(value)==1 and raws['collectorScriptPin']==('VALUE='+repr(value[0])+'\n'+body[0]).encode('utf-8'),'EXACT_EXECUTED_SCRIPT')
    value=value[0];need(all(value[k]==collection[k] for k in ('sourceCommit','pid','controlPin','baseOwnerPin','requestPin','operationConfigurationPin','requestConfigurationsRoot','productModulePin','packageMembers')),'SCRIPT_RESULT_BINDING')
    import main_program_target_control_successor as successor
    package_raw=_private(planning['standardPackagePin'],root);build=decode((Path(__file__).parent/planning['buildPin']['file']).read_bytes())
    payload=successor._official_package(package_raw,build,payload_count=154)['payloadFiles'];engine=wrapper['result']['candidate']['controller']['engine']
    expected=[dict(path=engine+'/'+name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()) for name,raw in sorted(payload.items())]
    need(collection['packageMembers']==expected and collection['productModulePin'] in expected and collection['productModulePin']['path']==engine+'/common/recovery_restore_inputs.py','OFFICIAL_PRODUCT_MODULE')
    metadata={r['pin']['path']:decode(base64.b64decode(r['rawBase64'],validate=True)) for r in collection['metadataOriginals']}
    operation=decode(base64.b64decode(packet['originals']['configuration']['rawBase64'],validate=True));request=decode(base64.b64decode(packet['originals']['request']['rawBase64'],validate=True))
    verify_materialization(collection,packet,wrapper['result'],metadata[collection['baseOwnerPin']['path']],operation,request)
    return dict(collection=collection,packet=packet,activation=wrapper['result'],inputPins=[context[k] for k in sorted(FIELDS) if k.endswith('Pin')]+[planning['standardPackagePin']],metadataCount=27)

def verify_configuration_relation(result,base_owner,operation_owner,request,context):
    root=Path(context['stdoutPin']['path']).parent;verified=verify_context(context,private=root)
    need(same(result,verified['activation']),'EXACT_ACTIVATION_RESULT')
    verify_materialization(verified['collection'],verified['packet'],result,base_owner,operation_owner,request)
    return True
