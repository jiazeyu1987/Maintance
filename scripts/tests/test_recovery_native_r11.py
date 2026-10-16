"""R11 semantic unit tests only; no Linux admission, real resources or browser."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
from types import SimpleNamespace
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'ops/recovery'))
sys.path.insert(0,str(ROOT/'doc/tasks/20261010-recovery-environment-dev/october-runtime-preparation-20261013'))
import recovery_native_launcher as launcher
from recovery_environment_contract import EnvironmentFailure
from test_recovery_native_r10 import phase_context, stamp, ref
import consume_october as consumer


@pytest.mark.parametrize('damage',[None,'private-vocabulary','unknown','duplicate','wrong-host','wrong-root','expired','wrong-source'])
def test_scope_business_vocabulary_and_current_signed_boundary(monkeypatch,damage):
    context,records=phase_context(monkeypatch)
    if damage=='private-vocabulary':context.scope['allowedActions'].append('BROWSER_ABOUT_BLANK')
    if damage=='unknown':context.scope['allowedActions']=['UNKNOWN']
    if damage=='duplicate':context.scope['allowedActions']*=2
    if damage=='wrong-host':context.scope['host']='172.30.30.57'
    if damage=='wrong-root':context.scope['root']='/tmp'
    if damage=='expired':context.scope['expiresAt']=stamp(-1)
    if damage=='wrong-source':
        records[context.intent['sourceScopePin']['path']]=dict(context.scope,sourceIdentityPin=ref('foreign'))
    if damage:
        with pytest.raises(EnvironmentFailure):context.guard()
    else:context.guard()


@pytest.mark.parametrize('damage',[None,'mixed-role','wrong-hash','wrong-vendor','unknown-member','outside-root'])
def test_resource_selector_consumes_exact_new_data_role(monkeypatch,damage):
    original=dict(path='/vendor/vk_swiftshader_icd.json',bytes=107,sha256='a'*64)
    archive=dict(path='/vendor/browser.zip',bytes=200,sha256='b'*64)
    inventory=SimpleNamespace(BROWSER_ROOT='/opt/brlab-browser',BROWSER_RESOURCE_ORIGINALS={'vk_swiftshader_icd.json':original},
                              BROWSER_VENDOR_ARCHIVE_PIN=archive)
    monkeypatch.setitem(sys.modules,'repository_native_browser_resources',inventory)
    pin=dict(original,path='/opt/brlab-browser/vk_swiftshader_icd.json')
    entry=dict(pin=pin,roles=['native-browser-resource'],vendorArtifactPins=[archive])
    trust=dict(nativeFilePins=[entry],vendorArtifactPins=[archive])
    if damage=='mixed-role':entry['roles'].append('native-tool')
    if damage=='wrong-hash':pin['sha256']='c'*64
    if damage=='wrong-vendor':entry['vendorArtifactPins']=[]
    if damage=='unknown-member':pin['path']='/opt/brlab-browser/control.json'
    if damage=='outside-root':pin['path']='/tmp/vk_swiftshader_icd.json'
    if damage:
        with pytest.raises(EnvironmentFailure):launcher.browser_resource_pins(trust)
    else:assert launcher.browser_resource_pins(trust)==[pin]


def role_input(role):
    """Explicit semantic fixtures never presented as prepared real credentials."""
    data=json.loads((consumer.HERE/'private-input-unresolved.json').read_text(encoding='utf-8'))
    b={k:'UNIT_FIXTURE' for k in data['backendBindings']}
    root=consumer.renderer.TASK_ROOT.as_posix()
    b.update(BRLAB_ROLE=role,BRLAB_BACKEND_PORT='38101' if role=='source' else '38102',
        BRLAB_REDIS_PORT='36379' if role=='source' else '36380',BRLAB_REDIS_HOST='127.0.0.1',BRLAB_REDIS_DATABASE='0',
        BRLAB_API_REQUEST_KEY='a'*32,BRLAB_API_RESPONSE_KEY='b'*32,
        BRLAB_MASTER_JDBC_URL='jdbc:mysql://127.0.0.1:'+('33301' if role=='source' else '33302')+'/unit',
        BRLAB_SLAVE_JDBC_URL='jdbc:mysql://127.0.0.1:'+('33301' if role=='source' else '33302')+'/unit',
        BRLAB_FRONTEND_ORIGIN='http://127.0.0.1:'+('38111' if role=='source' else '38112'))
    for k in ('BRLAB_LOG_FILE','BRLAB_DMR_PRIVATE_ROOT','BRLAB_INT_AUTH_PRIVATE_DB_PATH',
              'BRLAB_RUNTIME_CONTROL_REPO_ROOT','BRLAB_RUNTIME_CONTROL_STATE_DIR'):b[k]=root+'/'+role+'/'+k
    runtime=data['frontendRuntime'];runtime.update(apiOrigin='http://127.0.0.1:'+b['BRLAB_BACKEND_PORT'],
        objectOrigin='http://127.0.0.1:'+('39101' if role=='source' else '39102'))
    public=runtime['publicEnv']
    for k,v in public.items():
        if v is None:public[k]='UNIT_FIXTURE'
    public.update(VITE_APP_API_ENCRYPT_REQUEST_KEY='a'*32,VITE_APP_API_ENCRYPT_RESPONSE_KEY='b'*32)
    data['backendBindings']=b
    return data


def consumer_fixture():
    selection=dict(schemaVersion='W05OctoberConsumerSelection/v1',
        selectedCandidatePin=dict(path='/unit/candidate.jar',bytes=507559453,sha256=consumer.JAR_SHA),
        selectedAddendumPin=dict(path='/unit/addendum.yaml',bytes=195,sha256=consumer.ADDENDUM_SHA),
        originalSqlAndJimuArtifactSha256=consumer.ORIGINAL_JAR_SHA,
        rendererPin=consumer.file_pin(consumer.HERE/'render_runtime.py'),
        templatePin=consumer.file_pin(consumer.HERE/'application-isolated.yaml'),
        frontendGuardPin=dict(path='/unit/guard.js',bytes=3103,sha256=consumer.GUARD_SHA),roles={})
    docs={}
    for role in ('source','target'):
        entry={k:ref(role+'/'+k+'.json') for k in consumer.ROLE_FIELDS}
        entry.update(environment={},argv=None,outputDirectory=consumer.renderer.TASK_ROOT.as_posix()+'/secrets/'+role,
            installedJarPin=dict(selection['selectedCandidatePin'],path='/installed/'+role+'.jar'),
            installedAddendumPin=dict(selection['selectedAddendumPin'],path='/installed/'+role+'.yaml'),
            frontendGuardPin=selection['frontendGuardPin'])
        if role=='source':entry['protectionPin']=None
        data=role_input(role);b=data['backendBindings'];f=data['frontendRuntime']
        resources=dict(role=role,state='APPROVED',currentOwnershipVerified=True)
        endpoints={'database':b['BRLAB_MASTER_JDBC_URL'],'redis':b['BRLAB_REDIS_HOST']+':'+b['BRLAB_REDIS_PORT'],
            'object':f['objectOrigin'],'frontend':b['BRLAB_FRONTEND_ORIGIN'],'temporaryAuthenticationRedis':'127.0.0.1:'+('36381' if role=='source' else '36382')}
        for name,endpoint in endpoints.items():resources[name]=dict(instanceId=role+'-'+name,endpoint=endpoint,networkId=role+'-network')
        resources['database']['slaveEndpoint']=b['BRLAB_SLAVE_JDBC_URL'];resources['frontend']['apiOrigin']=f['apiOrigin']
        docs[role]=dict(input=data,resources=resources)
        selection['roles'][role]=entry
    return selection,docs


@pytest.mark.parametrize('damage',[None,'missing-binding','shared-db','shared-auth','wrong-role','old-jar','missing-false','env-true','not-owned'])
def test_october_actual_selection_and_resource_bindings(monkeypatch,damage):
    monkeypatch.setattr(consumer.renderer,'Path',PurePosixPath)
    selection,docs=consumer_fixture();entry=selection['roles']['target']
    if damage=='missing-binding':docs['target']['input']['backendBindings']['BRLAB_REDIS_HOST']=None
    if damage=='shared-db':docs['target']['resources']['database']=deepcopy(docs['source']['resources']['database'])
    if damage=='shared-auth':docs['target']['resources']['temporaryAuthenticationRedis']=deepcopy(docs['target']['resources']['redis'])
    if damage=='wrong-role':docs['target']['input']['backendBindings']['BRLAB_ROLE']='source'
    if damage=='old-jar':entry['installedJarPin']['sha256']=consumer.ORIGINAL_JAR_SHA
    if damage=='missing-false':entry['installedAddendumPin']['bytes']=0
    if damage=='env-true':entry['environment']={'JAVA_TOOL_OPTIONS':'-Dyudao.social.wechat.enabled=true'}
    if damage=='not-owned':docs['target']['resources']['currentOwnershipVerified']=False
    if damage:
        with pytest.raises(ValueError):consumer.validate_roles(selection,docs)
    else:
        configs,runtime=consumer.validate_roles(selection,docs)
        assert configs['target']['spring.profiles.active']=='brlab-target'
        assert len(configs['source']['spring.autoconfigure.exclude'])==43


def test_missing_real_inputs_fail_before_any_read_or_output():
    selection,_=consumer_fixture();selection['roles']['source']['privateInputPin']=None
    def forbidden(*args):raise AssertionError('Must not read before required material check')
    with pytest.raises(ValueError,match='MISSING_REAL_CONSUMER_MATERIALS'):
        consumer.prepare(selection,forbidden,deadline=999999999,guard=lambda:None)


@pytest.mark.parametrize('extra',[None,'application-brlab-target.yaml','application.properties','other.yml'])
def test_profile_siblings_cannot_override_selected_false(tmp_path,extra):
    selected=tmp_path/'application-wechat-disabled.yaml'
    selected.write_text('yudao.social.wechat.enabled: false',encoding='utf-8')
    if extra:
        (tmp_path/extra).write_text('yudao.social.wechat.enabled: true',encoding='utf-8')
        with pytest.raises(ValueError,match='CONSUMER_UNSELECTED_PROFILE_OR_CONFIG_FILE'):
            consumer.reject_unselected_config_siblings(str(selected))
    else:consumer.reject_unselected_config_siblings(str(selected))


@pytest.mark.parametrize('role',['source','target'])
@pytest.mark.parametrize('damage',[None,'missing-location','optional','import','additional','true-property','wrong-order','probe-main','jvm-override'])
def test_formal_jar_and_exact_single_ordered_mandatory_argv(role,damage):
    selection,_=consumer_fixture();entry=selection['roles'][role]
    boot=dict(schemaVersion='formal-maintenance-boot/v1',instanceId='brlab-20261012-'+role,
        artifactSha256=consumer.JAR_SHA,state='OPEN',epoch='',phase='NORMAL')
    control=dict(schemaVersion='W05OctoberFormalControlSelection/v1',instanceId=boot['instanceId'],role=role,
        artifactSha256=consumer.JAR_SHA,state='APPROVED',socketPath=consumer.renderer.TASK_ROOT.as_posix()+'/'+role+'/control.sock',
        sourcePins=[ref(role+'/formal-control.py')])
    protection=dict(schemaVersion='RecoveryProtectionConfig/v1',artifactSha256=consumer.JAR_SHA) if role=='target' else None
    argv=consumer.launch_argv(role,entry,dict(path='/approved/'+role+'/application.yaml'),boot,control,protection)
    assert argv[argv.index('-jar')+1]==entry['installedJarPin']['path']
    assert argv[-1]=='--spring.config.location=file:/approved/'+role+'/application.yaml,file:/installed/'+role+'.yaml'
    assert len([a for a in argv if a.startswith('--spring.config.location=')])==1
    assert not any('optional:' in a or 'import=' in a or 'additional-location' in a for a in argv)
    entry['argv']=list(argv)
    if damage=='missing-location':entry['argv'].pop()
    if damage=='optional':entry['argv'][-1]=entry['argv'][-1].replace('file:','optional:file:')
    if damage=='import':entry['argv'].append('--spring.config.import=file:/unselected')
    if damage=='additional':entry['argv'].append('--spring.config.additional-location=file:/unselected')
    if damage=='true-property':entry['argv'].append('--yudao.social.wechat.enabled=true')
    if damage=='wrong-order':
        loc=entry['argv'][-1].split('=',1)[1].split(',');entry['argv'][-1]='--spring.config.location='+','.join(reversed(loc))
    if damage=='probe-main':entry['argv']=['java','OctoberConfigCheck']+entry['argv'][-1:]
    if damage=='jvm-override':entry['argv'].insert(1,'-Dyudao.social.wechat.enabled=true')
    if damage:
        with pytest.raises(ValueError,match='CONSUMER_SELECTED_ARGV_MISMATCH'):
            consumer.selected_launch_argv(role,entry,dict(path='/approved/'+role+'/application.yaml'),boot,control,protection)
    else:assert consumer.selected_launch_argv(role,entry,dict(path='/approved/'+role+'/application.yaml'),boot,control,protection)==argv
