"""Pure local immutable per-stage installation selection; no runtime calls."""
import copy
import hashlib
import json
from pathlib import Path
import re

HISTORICAL_COMMIT='0d445782dc06995b3c84b1b45146ea4b75483f92'
SOURCE='intruoyi-57-safe-20261024-v1'
SPUG_FILES=frozenset(('smallapp_entry.py','smallapp_adapter.py','smallapp-entry.locations.conf',
    'smallapp-ui/app.js','smallapp-ui/simple.js','smallapp-ui/index.html','smallapp-ui/simple.css',
    'smallapp-ui/embedded.js','smallapp-ui/embedded.css','smallapp-ui/package-catalog.js','smallapp-ui/package-catalog.css'))


def need(condition,code):
    if not condition:raise ValueError(code)


def file_pin(root,name):
    raw=(Path(root)/name).read_bytes()
    return dict(file=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def pinned(root,pin,name=None):
    need(isinstance(pin,dict) and set(pin)=={'file','bytes','sha256'},'STAGE_PIN_INVALID')
    filename=pin['file']
    need(isinstance(filename,str) and re.fullmatch(r'[a-z0-9][a-z0-9.-]*\.json',filename),'STAGE_PIN_PATH_INVALID')
    need(name is None or filename==name,'STAGE_PIN_FILE_MISMATCH')
    need(file_pin(root,filename)==pin,'STAGE_PIN_CHANGED')
    return json.loads((Path(root)/filename).read_text(encoding='utf-8'))


def generation(role,install,build_pin,installation_pin=None):
    value=dict(role=role,sourceCommit=install['sourceCommit'],fileManifestSha256=install['fileManifestSha256'],
               fileCount=install['fileCount'],packageSha256=install['packageSha256'],buildPin=build_pin)
    if installation_pin:value['installationPin']=installation_pin
    return value


def check_build(task,pin,commit,installation):
    build=pinned(task,pin,'release-build-'+commit[:7]+'.json')
    need(build.get('status')=='PASS' and build.get('targetCommit')==commit,'STAGE_BUILD_NOT_VERIFIED')
    need(all(build.get(key)==installation.get(key) for key in ('packageSha256','fileManifestSha256','fileCount')),'STAGE_BUILD_IDENTITY_CHANGED')
    return build


def load_stage_deployment(task,private,kind):
    task,private=Path(task),Path(private)
    need(kind in ('FULL','I1','I2'),'STAGE_KIND_INVALID')
    filename='automatic-'+kind.lower()+'-deployment-selection.json'
    selected=json.loads((task/filename).read_text(encoding='utf-8'))
    need(selected.get('schemaVersion')=='AutomaticStageDeployment/v1','STAGE_SELECTION_SCHEMA_INVALID')
    need(selected.get('kind')==kind and selected.get('sourceConfigRef')==SOURCE,'STAGE_IDENTITY_CHANGED')
    commit=selected.get('sourceCommit')
    need(isinstance(commit,str) and re.fullmatch('[a-f0-9]{40}',commit),'STAGE_SOURCE_COMMIT_INVALID')
    need(selected.get('spugCommit')==HISTORICAL_COMMIT,'STAGE_SPUG_GENERATION_NOT_APPROVED')
    old=commit==HISTORICAL_COMMIT
    install_name='automatic-control-installation-57.json' if old else 'automatic-source-control-installation-'+commit[:7]+'.json'
    private_name=install_name[:-5]+'.private.json'
    install=pinned(task,selected.get('sourceInstallationPin'),install_name)
    privileged=pinned(private,selected.get('sourcePrivateInstallationPin'),private_name)
    need(install.get('status')==privileged.get('status')=='PASS' and install.get('sourceCommit')==privileged.get('sourceCommit')==commit,'STAGE_SOURCE_NOT_INSTALLED')
    need(len(install.get('controllers',[]))==len(privileged.get('controllers',[]))==2,'STAGE_CONTROLLERS_INVALID')
    public_private=copy.deepcopy(privileged)
    for controller in public_private['controllers']:
        need(isinstance(controller.pop('control',None),dict),'STAGE_PRIVATE_CONTROL_MISSING')
    need(public_private==install,'STAGE_PUBLIC_PRIVATE_MISMATCH')
    build=check_build(task,selected['sourceBuildPin'],commit,install)
    if old:
        need(kind=='FULL' and 'schemaVersion' not in install,'HISTORICAL_STAGE_ONLY_FULL')
        generations=[generation('SOURCE',install,selected['sourceBuildPin']),
                     generation('MAIN_TARGET',install,selected['sourceBuildPin'],selected['sourceInstallationPin'])]
    else:
        need(install.get('schemaVersion')=='AutomaticSourceControlUpgrade/v1','STAGE_UPGRADE_SCHEMA_REQUIRED')
        need(install.get('buildPin')==selected['sourceBuildPin'],'STAGE_UPGRADE_BUILD_PIN_CHANGED')
        need(all(install.get(key) is True for key in ('retainedTargetControlUnchanged','epochUnchanged',
             'noBackupDispatched','noRestoreDispatched','previousGenerationsRetained')),'STAGE_UPGRADE_PROTECTION_NOT_VERIFIED')
        previous=pinned(task,install.get('predecessorInstallationPin'))
        need(previous.get('status')=='PASS','STAGE_PREDECESSOR_NOT_VERIFIED')
        need(install['controllers'][0].get('previousPid')==previous['controllers'][0]['pid'], 'STAGE_PREVIOUS_SOURCE_PID_CHANGED')
        need(install['policy']==previous['policy'] and install['epoch']==previous['epoch'],'STAGE_PREVIOUS_SOURCE_EPOCH_CHANGED')
        generations=install.get('controllerGenerations')
        need(isinstance(generations,list) and len(generations)==2,'STAGE_CONTROLLER_GENERATIONS_REQUIRED')
        need(generations[0]==generation('SOURCE',install,selected['sourceBuildPin']),'STAGE_SOURCE_GENERATION_CHANGED')
        target_generation=generations[1]
        historical=pinned(task,target_generation.get('installationPin'),'automatic-control-installation-57.json')
        need(historical.get('status')=='PASS' and historical.get('sourceCommit')==HISTORICAL_COMMIT,'STAGE_TARGET_HISTORICAL_IDENTITY_CHANGED')
        check_build(task,target_generation.get('buildPin'),HISTORICAL_COMMIT,historical)
        need(target_generation==generation('MAIN_TARGET',historical,target_generation['buildPin'],target_generation['installationPin']),'STAGE_TARGET_GENERATION_CHANGED')
        need(install['controllers'][1]==historical['controllers'][1] and install['policy']==historical['policy']
             and install['epoch']==historical['epoch'],'STAGE_RETAINED_TARGET_OR_EPOCH_CHANGED')
    spug=pinned(task,selected.get('spugInstallationPin'),'automatic-spug-installation-0d44578.json')
    need(spug.get('status')=='PASS' and spug.get('sourceCommit')==HISTORICAL_COMMIT,'STAGE_SPUG_NOT_INSTALLED')
    need(set(spug.get('files',{}))==SPUG_FILES,'STAGE_SPUG_FILE_SCOPE_CHANGED')
    normalized=copy.deepcopy(privileged)
    normalized['controllerGenerations']=generations
    return dict(selection=selected,selectionPin=file_pin(task,filename),sourceCommit=commit,spugCommit=HISTORICAL_COMMIT,
                sourceInstallation=install,privateSourceInstallation=normalized,sourceBuild=build,
                spugInstallation=spug,controllerGenerations=generations)
