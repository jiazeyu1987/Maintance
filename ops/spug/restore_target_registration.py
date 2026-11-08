"""Prepare an explicit, reviewable one-time registration; never install or restore.

Inputs are private administrator observations, not browser request fields. A plan
contains compare-before-write hashes so installation cannot overwrite a newer
configuration. Existing historical target references and routes are retained.
"""
from copy import deepcopy
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re


def need(condition, message):
    if not condition: raise ValueError(message)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')


def sha(value): return hashlib.sha256(canonical(value)).hexdigest()


def remote_pin(path,value):
    need(PurePosixPath(path).is_absolute() and '..' not in PurePosixPath(path).parts,
         'REGISTRATION_DESTINATION_INVALID')
    raw=canonical(value)
    return dict(path=path,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def plan(value):
    need(value.get('schemaVersion') == 'SpugMainRestoreRegistrationInputs/v1', 'REGISTRATION_INPUT_INVALID')
    source, app_id = value['sourceConfigRef'], value['applicationId']
    simple, entry, bridge = (deepcopy(value[key]) for key in ('simpleSettings','entrySettings','bridgeSettings'))
    bindings=[b for b in simple['bindings'] if b['applicationId']==app_id]
    apps=[a for a in entry['applications'] if a['applicationId']==app_id]
    routes=simple.get('catalogueRestoreBindings',{})
    safe_apps={b['applicationId'] for b in simple['bindings'] if b['mode']=='safe'} & {
        a['applicationId'] for a in entry['applications']}
    need(type(routes) is dict and len(routes)<=1000 and all(
        type(point) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}',point) and
        type(app) is str and app in safe_apps for point,app in routes.items()),
        'SIMPLE_CATALOGUE_RESTORE_BINDING_INVALID')
    historical=app_id in routes.values()
    need(len(bindings)==len(apps)==1 and (bindings[0]['selectable'] is True or
         bindings[0]['selectable'] is False and historical) and bindings[0]['mode']=='safe'
         and apps[0]['sourceConfigRef']==source, 'SAFE_SOURCE_BINDING_REQUIRED')
    targets=value['targets']
    servers={row['value'] if 'value' in row else row['address'] for row in simple['servers']}
    need(len(targets)==3 and {t['server'] for t in targets}==servers and
         len({t['targetConfigRef'] for t in targets})==3, 'THREE_DISTINCT_REGISTERED_TARGETS_REQUIRED')
    refs=[t['targetConfigRef'] for t in targets]
    need(source not in refs and all(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}',r) for r in refs),
         'TARGET_REFERENCE_INVALID')
    registration=deepcopy(value['registration'])
    need(registration['applicationId']==app_id and registration['sourceConfigRef']==source,
         'SOURCE_REGISTRATION_MISMATCH')
    current={row['configRef'] for row in registration['allowedRestoreTargets']}
    registration['allowedRestoreTargets'].extend({'configRef':r} for r in refs if r not in current)
    apps[0]['registrationSha256']=sha(registration)
    apps[0]['targetConfigRefs']=list(dict.fromkeys(apps[0]['targetConfigRefs']+refs))
    outputs=[]
    for target in targets:
        ref=target['targetConfigRef']; owner=deepcopy(target['ownerConfiguration'])
        need(owner.get('schemaVersion')=='RecoveryMinimalConfiguration/v1' and
             ref in owner['targets'] and source in owner['sources'], 'RECOVERY_OWNER_CONFIGURATION_REQUIRED')
        instance=owner['targets'][ref]
        need(instance.get('sourceConfigRef')==source and instance.get('mainApplication',{}).get('schemaVersion') in
             ('RegisteredMainApplication/v1','RegisteredMainApplication/v2') and instance.get('replacement',{}).get('schemaVersion')==
             'RegisteredApplicationReplacement/v2', 'REGISTERED_MAIN_TARGET_REQUIRED')
        need(owner['sources'][source].get('archiveCatalogue',{}).get('schemaVersion') in
             ('RecoveryArchiveCatalogue/v1','RecoveryArchiveCatalogue/v2'),
             'DYNAMIC_ARCHIVE_CATALOGUE_REQUIRED')
        need(type(instance.get('resourceBudget')) is dict, 'RESTORE_RESOURCE_BUDGET_REQUIRED')
        control=deepcopy(target['controlConfiguration'])
        need(target['engineVariant']=='standard' and 'recovery' in control['programPins'], 'SAFE_RECOVERY_ENGINE_REQUIRED')
        archive_admission=control.get('archiveRestoreCatalogues',{}).get(source)
        archive_only=(type(archive_admission) is dict and set(archive_admission)=={'path','bytes','sha256'} and
            type(archive_admission['path']) is str and PurePosixPath(archive_admission['path']).is_absolute() and
            '..' not in PurePosixPath(archive_admission['path']).parts and
            type(archive_admission['bytes']) is int and archive_admission['bytes']>=0 and
            type(archive_admission['sha256']) is str and re.fullmatch('[a-f0-9]{64}',archive_admission['sha256']))
        need(source in control['sourceConfigurations'] or archive_only, 'SOURCE_CONFIGURATION_REQUIRED_ON_DESTINATION')
        root=target['configurationRoot'].rstrip('/')
        owner_pin=remote_pin(root+'/main-restore-'+ref+'.json',owner)
        registration_pin=remote_pin(root+'/main-restore-registration.json',registration)
        control['restoreConfigurations'].setdefault(source,{})[ref]=owner_pin
        selector=str(PurePosixPath(control['registryRoot'])/'applications'/(app_id+'.pin.json'))
        connection=deepcopy(target['bridgeConfiguration'])
        connection['selectedTargetPreflight']=True
        connection['sourceConfigRefs']=list(dict.fromkeys(connection['sourceConfigRefs']+[source]))
        connection['targetConfigRefs']=list(dict.fromkeys(connection['targetConfigRefs']+[ref]))
        filename=target['bridgeFile']
        need(re.fullmatch(r'[A-Za-z0-9_.-]+\.json',filename), 'TARGET_BRIDGE_FILE_INVALID')
        bridge.setdefault('targetConnections',{})[ref]=filename
        bindings[0]['overwriteTargetServers'][target['server']]=ref
        bindings[0].setdefault('restoreProgressBindings',{})[ref]=deepcopy(target['progressBinding'])
        outputs.append(dict(server=target['server'],targetConfigRef=ref,
            controlExpectedSha256=sha(target['controlConfiguration']),controlConfiguration=control,
            registration=registration,registrationPin=registration_pin,registrationSelectorPath=selector,
            recoveryConfiguration=owner,recoveryConfigurationPin=owner_pin,bridgeFile=filename,
            bridgeConfiguration=connection,preflightEvidencePin=target['preflightEvidencePin']))
    return dict(schemaVersion='SpugMainRestoreRegistrationPlan/v1',state='PLAN_ONLY',
        sourceConfigRef=source,applicationId=app_id,
        expectedSha256={key:sha(value[key]) for key in ('simpleSettings','entrySettings','bridgeSettings')},
        simpleSettings=simple,entrySettings=entry,bridgeSettings=bridge,targets=outputs,
        requiredInstallationChecks=['verify-safe-package-and-program-pins','verify-live-main-identity-storage-writers',
            'verify-canonical-source-metadata-and-readonly-archives','verify-source-and-target-locks',
            'verify-private-credentials-and-network-reachability','compare-original-configuration-hashes',
            'publish-registration-selectors-with-original-pin-check','restart-only-owned-control-services',
            'verify-authenticated-selections-and-spug-choose-cancel'])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args()
    value=json.loads(Path(args.input).read_text(encoding='utf-8'))
    result=plan(value)
    fd=os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(canonical(result));stream.flush();os.fsync(stream.fileno())
    need(json.loads(Path(args.output).read_text(encoding='utf-8'))==result,'PLAN_READBACK_FAILED')
    print(json.dumps(dict(state='PLAN_ONLY',targets=[t['server'] for t in result['targets']],
                          installationPerformed=False,restorePerformed=False)))


if __name__=='__main__':main()
