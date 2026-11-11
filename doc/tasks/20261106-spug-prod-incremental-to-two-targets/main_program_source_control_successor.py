"""Prepare a complete immutable source controller with unchanged physical bindings."""
from copy import deepcopy
import hashlib
import json
from pathlib import PurePosixPath

from main_program_control_staging import verify_package
from install_automatic_source_successor import validate_source_rebinding

SOURCE='intruoyi-57-safe-20261024-v1'
CHANGED_FILES={'control/recovery_control_smallapp.py','control/recovery_control_smallapp_native.py'}


def need(value,reason):
    if not value:raise ValueError('SOURCE_SUCCESSOR_'+reason)


def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def document_pin(path,value):
    raw=canonical(value)
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def validate_delta(before,after):
    need(set(before)==set(after) and {name for name in before if before[name]!=after[name]}==CHANGED_FILES,
         'PACKAGE_SCOPE_CHANGED')
    return sorted(CHANGED_FILES)


def systemd_properties_equal(before,after):
    """systemd dependency properties are sets; drop-in precedence stays ordered."""
    if type(before) is not dict or type(after) is not dict or set(before)!=set(after):return False
    for key in before:
        left,right=before[key],after[key]
        if type(left) is not str or type(right) is not str:return False
        if key in ('After','Requires'):
            a,b=left.split(),right.split()
            if len(a)!=len(set(a)) or len(b)!=len(set(b)) or set(a)!=set(b):return False
        elif left!=right:return False
    return True


def process_observation_equal(before,after):
    if type(before) is not dict or type(after) is not dict or set(before)!=set(after) or 'properties' not in before:return False
    return (systemd_properties_equal(before['properties'],after['properties']) and
        all(before[key]==after[key] for key in before if key!='properties'))


def prepare_candidate(*,previous,control,owner,previous_build,build,previous_package_raw,package_raw,engine=None):
    """Pure preparation; a BOUND result never asserts installation or a runtime PID."""
    for key,value in (('controlConfigurationPin',control),('ownerConfigurationPin',owner)):
        need(document_pin(previous[key]['path'],value)==previous[key],'ORIGINAL_CONFIGURATION_CHANGED')
    need(previous['role']=='source' and previous['sourceCommit']==previous_build['targetCommit'] and
         previous['fileCount']==previous_build['fileCount'] and
         previous['fileManifestSha256']==previous_build['fileManifestSha256'] and
         set(control['sourceConfigurations'])=={SOURCE} and
         control['sourceConfigurations'][SOURCE]==previous['ownerConfigurationPin'] and
         set(owner['sources'])=={SOURCE},'SOURCE_BINDING_CHANGED')
    old=verify_package(previous_package_raw,previous_build)
    new=verify_package(package_raw,build)
    changed=validate_delta(old['payloadFiles'],new['payloadFiles'])
    previous_engine=previous['engine'];parent=PurePosixPath(previous_engine).parent
    expected=str(parent/('engine-source-only-'+build['targetCommit'][:7]))
    engine=expected if engine is None else engine
    need(engine==expected and engine!=previous_engine and PurePosixPath(engine).is_absolute() and
         '..' not in PurePosixPath(engine).parts,'ENGINE_SCOPE_INVALID')
    def rebind(value):
        if type(value) is str:
            return value.replace(previous_engine+'/',engine+'/') if value.startswith(previous_engine+'/') else value
        if type(value) is list:return [rebind(item) for item in value]
        if type(value) is dict:
            result={key:rebind(item) for key,item in value.items()}
            if set(value)=={'path','bytes','sha256'} and result['path']!=value['path']:
                name=result['path'][len(engine)+1:]
                need(name in old['payloadFiles'] and name in new['payloadFiles'] and
                     old['payloadFiles'][name]==new['payloadFiles'][name],'PINNED_PROGRAM_CHANGED')
                raw=new['payloadFiles'][name]
                result.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
            return result
        return value
    candidate_owner=rebind(owner)
    sha=lambda files:{name:hashlib.sha256(raw).hexdigest() for name,raw in files.items()}
    movements=validate_source_rebinding(owner['sources'],candidate_owner['sources'],previous_engine,engine,
        sha(old['payloadFiles']),sha(new['payloadFiles']))
    root=PurePosixPath(previous['controlConfigurationPin']['path']).parent.parent/('source-only-'+build['targetCommit'][:7])
    owner_pin=document_pin(root/'repository-source.json',candidate_owner)
    candidate_control=rebind(control)
    candidate_control['sourceConfigurations']={SOURCE:owner_pin}
    need(candidate_control['sourceEpochPolicies']==control['sourceEpochPolicies'] and
         candidate_control['sourceProgramPolicies']==control['sourceProgramPolicies'],'PHYSICAL_SOURCE_POLICY_CHANGED')
    row=dict(schemaVersion='MainProgramSourceControllerBinding/v1',status='BOUND',role='source',host='172.30.30.57',
        sourceConfigRef=SOURCE,service=previous['service'],engine=engine,pid=None,sourceCommit=build['targetCommit'],
        fileCount=build['fileCount'],fileManifestSha256=build['fileManifestSha256'],packageSha256=build['packageSha256'],
        controlConfigurationPin=document_pin(root/'control-source.json',candidate_control),ownerConfigurationPin=owner_pin)
    return dict(controller=row,control=candidate_control,owner=candidate_owner,changedFiles=changed,
        sourceProgramPathMovements=movements,files=deepcopy(new['files']))
