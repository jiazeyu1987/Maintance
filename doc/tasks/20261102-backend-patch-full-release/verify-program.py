"""Verify actual bytes, startup log and program mounts, without business writes."""
from pathlib import Path
import concurrent.futures,hashlib,json,sqlite3,subprocess,sys
root=Path('C:/SpugHandoff/release');source=root/'source/ops/spug/release-center';sys.path.insert(0,str(source))
from intruoyi_runtime import Runtime,ssh_source_bytes
from backend_patch_agent import verify_unchanged
phase=sys.argv[1];environments=sys.argv[2:] or ['test','prod','backup'];assert phase in ('patch','full')
selection=json.loads(Path(__file__).with_name('selected-release.json').read_text('utf-8'))
config=json.loads((root/'executor.private.json').read_text('utf-8'));runtime=Runtime(config)
with sqlite3.connect('file:'+str(root/'state/state.sqlite3').replace('\\','/')+'?mode=ro',uri=True) as db:
    state=json.loads(db.execute('SELECT payload FROM release_state WHERE id=1').fetchone()[0])
tag=selection['backendPatchTag' if phase=='patch' else 'fullReleaseTag']
package=next(p for p in state['backendPatches' if phase=='patch' else 'packages'] if p['releaseTag']==tag)
folder=Path(package['directory']);manifest=json.loads((folder/'manifest.json').read_text('utf-8'))
assert hashlib.sha256((folder/'manifest.json').read_bytes()).hexdigest()==package['manifestSha256']
expected_jar=package['jarSha256'] if phase=='patch' else json.loads((folder/'backend-artifact-contract.json').read_text('utf-8'))['jarSha256']
remote=(source/'intruoyi_remote.py').read_text('utf-8').split("if __name__ == '__main__':")[0]
inspection=r'''
p=PROFILE;backend=inspect(p['backend']);frontend=inspect(p['frontend'])
logs=subprocess.run(['docker','logs',p['backend']],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
assert logs.returncode==0
marker=b'IntRuoyi backend startup completed; release metadata: /actuator/release'
result=dict(startupLogCount=(logs.stdout+logs.stderr).count(marker),
    programMounts=[dict(source=m['Source'],destination=m['Destination'],rw=m['RW']) for m in backend['Mounts'] if m['Destination']=='/yudao-server' or m['Destination'].startswith('/yudao-server/')],
    backendImageReference=backend['Config']['Image'],frontendImageReference=frontend['Config']['Image'],
    readOnly=sql(p,'SELECT @@global.read_only,@@global.super_read_only;'),
    applicationPropertiesSha256={m['Destination']:hashlib.sha256(Path(m['Source']).read_bytes()).hexdigest() for m in backend['Mounts'] if m['Destination'].endswith('.properties')})
result['manifestTagImageIds']={}
for role,value in CANDIDATE_IMAGES.items():
    resolved=subprocess.run(['docker','image','inspect','--format','{{.Id}}',value['name']],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
    assert resolved.returncode==0
    result['manifestTagImageIds'][role]=resolved.stdout.decode().strip()
print(json.dumps(result))
'''
def verify(env):
    actual=runtime.call(env,'backend-patch-observe')
    profile=runtime.profile(env)
    result=subprocess.run(['ssh',*runtime.ssh_options(),'root@'+profile['host'],profile['python']+' -'],
        input=ssh_source_bytes(remote+'\nfrom pathlib import Path\nPROFILE='+repr(profile)+'\nCANDIDATE_IMAGES='+repr(manifest['images'] if phase=='full' else {})+'\n'+inspection),capture_output=True,timeout=90)
    assert result.returncode==0,env+': program evidence failed'
    evidence=json.loads(result.stdout)
    assert actual['backendJarSha256']==expected_jar,env+': actual JAR differs'
    assert actual['backendMetadata']['sourceCommit']==selection['commit'],env+': source differs'
    assert evidence['startupLogCount']==1,env+': startup marker missing or duplicated'
    assert evidence['readOnly']=='0\t0',env+': database fence not released'
    assert actual['backendHealth']=='UP' and actual['frontendHttpStatus']==200
    assert actual['gxpAuditMode']=='DEVELOPMENT_DISABLED'
    if phase=='patch':
        assert actual['backendPatchTag']==tag
        verify_unchanged(manifest['baseline']['origins'][env],actual)
        assert len(evidence['programMounts'])==2 and all(m['rw'] is False for m in evidence['programMounts'])
        assert actual['components']['backend']['imageId']==manifest['baseline']['origins'][env]['components']['backend']['imageId']
    else:
        assert actual['releaseTag']==tag and actual['backendPatchTag'] is None and actual['frontendPatchTag'] is None
        assert evidence['programMounts']==[],env+': old JAR mount shadows new image'
        for role in ('backend','frontend'):
            assert actual['components'][role]['imageId']==manifest['images'][role]['id']
            # The deployed Docker API pins Config.Image to the immutable ID.
            # Independently resolve the manifest tag too; neither a tag nor an unused .env is sufficient.
            assert evidence[role+'ImageReference'] in (manifest['images'][role]['name'],manifest['images'][role]['id'])
            assert evidence['manifestTagImageIds'][role]==manifest['images'][role]['id']
    return env,dict(status='PASS',phase=phase,tag=tag,observation=actual,**evidence)
with concurrent.futures.ThreadPoolExecutor(max_workers=len(environments)) as pool:result=dict(pool.map(verify,environments))
Path(__file__).with_name('program-'+phase+'-'+'-'.join(environments)+'.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({env:dict(status=v['status'],phase=phase,tag=tag,jarSha256=v['observation']['backendJarSha256'],startupLogCount=v['startupLogCount'],programMounts=v['programMounts'],schemaSha256=v['observation']['schemaSha256'],ledgerSha256=v['observation']['ledgerSha256']) for env,v in result.items()}))
