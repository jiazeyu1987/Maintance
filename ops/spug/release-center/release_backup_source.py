"""Explicit post-release backup source generation. No host-specific defaults."""
import pathlib, json, subprocess, sys, hashlib, copy, os, zipfile, tempfile
from pathlib import Path


def require(condition, code):
    if not condition:raise ValueError(code)

def update_image_tag(path, tag):
    import re
    path=Path(path)
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', tag): raise ValueError('INVALID_IMAGE_TAG')
    original_stat=path.stat()
    raw=path.read_bytes()
    pattern=rb'(?m)^IMAGE_TAG=[^\r\n]*'
    if len(re.findall(pattern,raw))!=1: raise ValueError('AMBIGUOUS_IMAGE_TAG')
    updated=re.sub(pattern,b'IMAGE_TAG='+tag.encode(),raw)
    if updated==raw:return
    fd,name=tempfile.mkstemp(prefix=path.name+'.release-binding-',suffix='.tmp',dir=path.parent)
    temp=Path(name)
    try:
        with os.fdopen(fd,'wb') as f:f.write(updated)
        if hasattr(os,'chown'):os.chown(temp,original_stat.st_uid,original_stat.st_gid)
        import stat
        temp.chmod(stat.S_IMODE(original_stat.st_mode))
        if path.read_bytes()!=raw:raise ValueError('ENVIRONMENT_CHANGED')
        os.replace(temp,path)
    finally:
        if temp.exists():temp.unlink()

def create_attempt(generation):
    generation=Path(generation)
    generation.mkdir(mode=0o700,parents=True,exist_ok=True)
    return Path(tempfile.mkdtemp(prefix='attempt-',dir=generation))


def stage(binding, manifest, original_control_pin):
    engine=Path(binding['engineRoot'])
    sys.path[:0]=[str(engine/x) for x in ('control','common','formal')]
    from recovery_engine import pin,pinned_json
    from recovery_main_target import capture_main_application
    from recovery_program_generation import resolve_capture
    from minimal_capture_support import Budget
    from minimal_capture_worker import Runtime
    read=lambda p:json.loads(Path(p).read_bytes())
    c=pinned_json(original_control_pin)
    ref=binding['sourceRef']; policy=c['sourceProgramPolicies'][ref]
    owner=pinned_json(c['sourceConfigurations'][ref]); cap=pinned_json(policy['captureConfigurationPins'][ref])
    if owner['sources'][ref]['configurationPath']!=policy['captureConfigurationPins'][ref]['path']:
        raise ValueError('SOURCE_OWNER_CAPTURE_MISMATCH')
    if cap['sourceLockPath']!=c['sourceEpochPolicies'][ref]['sourceLockPath']:
        raise ValueError('SOURCE_LOCK_MISMATCH')
    t=pinned_json(policy['baselineTargetPin'])
    generation=Path(binding['generationRoot'])/manifest['releaseTag']
    root=create_attempt(generation)
    def raw(name,data):
     p=root/name
     with p.open('xb') as f:f.write(data)
     p.chmod(0o600)
     return pin(p)
    def write(name,value):return raw(name,(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode())
    names=list(binding['containers'].values())
    rows=json.loads(subprocess.check_output(['docker','inspect',*names]))
    byname={r['Name'].lstrip('/'):r for r in rows}
    byrole={s['role']:byname[binding['containers'][s['role']]] for s in t['services']}
    expected={role:manifest['images'][role]['id'] for role in ('backend','frontend')}
    replacements={}
    for s in t['services']:
     r=byrole[s['role']]
     require(r['State']['Running'] and not r['State']['Paused'],'SOURCE_CONTAINER_NOT_RUNNING')
     if s['role'] in expected:
      require(r['Image']==expected[s['role']],'SOURCE_APPLICATION_IMAGE_MISMATCH')
      replacements[s['id']]=r['Id'];replacements[s['imageId']]=r['Image']
     else:
      require(s['id']==r['Id'] and s['imageId']==r['Image'],'SOURCE_DATA_SERVICE_CHANGED')
      require(t['replacement']['services'][s['role']]['mounts']==sorted(r['Mounts'],key=lambda m:m['Destination']),'SOURCE_DATA_MOUNTS_CHANGED')
     oldip=s['ip']; require(oldip=='127.0.0.1' or oldip in [v['IPAddress'] for v in r['NetworkSettings']['Networks'].values()],'SOURCE_ADDRESS_CHANGED')
     s.update(id=r['Id'],imageId=r['Image'])
     t['replacement']['services'][s['role']].update(id=r['Id'],imageId=r['Image'],labels=r['Config']['Labels'],mounts=sorted(r['Mounts'],key=lambda m:m['Destination']))
    release=json.loads(subprocess.check_output(['docker','exec',binding['containers']['backend'],'cat','/yudao-server/release-info.json']))
    require(release['releaseTag']==manifest['releaseTag'],'SOURCE_RELEASE_VERSION_MISMATCH')
    write('release-info.json',release)
    raw('previous-runtime.env',Path(binding['environmentFile']).read_bytes())
    update_image_tag(binding['environmentFile'],manifest['releaseTag'])
    current_env=Path(binding['environmentFile']).read_bytes()
    require(manifest['releaseTag'].encode() in current_env,'SOURCE_ENVIRONMENT_TAG_MISMATCH')
    materials={'application-config':raw('runtime.env',current_env),'runtime-compose':raw('docker-compose.yml',Path(binding['composeFile']).read_bytes())}
    nginx=next(m['Source'] for m in byrole['frontend']['Mounts'] if m['Destination']=='/etc/nginx/conf.d/default.conf')
    materials['frontend-config']=raw('source-nginx.conf',pathlib.Path(nginx).read_bytes())
    # Read the application configuration directly from the running release image.
    with tempfile.TemporaryDirectory(prefix='jar-read-',dir=str(root)) as temp:
     jar=pathlib.Path(temp)/'app.jar'
     subprocess.run(['docker','cp',binding['containers']['backend']+':/yudao-server/app.jar',str(jar)],check=True,stdout=subprocess.DEVNULL)
     with zipfile.ZipFile(jar) as z:
      for role,name in [('application-dev','application-dev.yaml'),('application-main','application.yaml')]:
       materials[role]=raw(name,z.read('BOOT-INF/classes/'+name))
    old_effective=pinned_json(next(x['reference'] for x in cap['source']['configurationPins'] if x['role']=='effective-runtime'))
    effective={}
    for name,r in byname.items():
     old=old_effective[name]
     env=r['Config']['Env']
     if isinstance(old['environment'],dict):env=dict(x.split('=',1) for x in env)
     effective[name]=dict(command=r['Config']['Cmd'],entrypoint=r['Config']['Entrypoint'],environment=env,imageId=r['Image'],imageReference=r['Config']['Image'],mounts=r['Mounts'])
     require(set(effective[name])==set(old),'SOURCE_EFFECTIVE_SCHEMA_MISMATCH')
    materials['effective-runtime']=write('runtime-effective.json',effective)
    for item in cap['source']['configurationPins']:item['reference']=materials[item['role']]
    for item in cap['source']['materialPins']:
     if item['purpose']=='container-inspects':item['reference']=write('container-inspects.json',rows)
    cap['source']['writerContainerIds']=[replacements.get(x,x) for x in cap['source']['writerContainerIds']]
    cap['source']['applicationImageIds']=[replacements.get(x,x) for x in cap['source']['applicationImageIds']]
    objects=pinned_json(cap['source']['objectSourcePin'])
    require(len(objects['versionPins'])==1,'SOURCE_VERSION_BINDING_AMBIGUOUS')
    version=pinned_json(objects['versionPins'][0]);version['releaseTag']=manifest['releaseTag']
    require(set(version['images'])==set(byname),'SOURCE_IMAGE_INVENTORY_CHANGED')
    version['images']={name:r['Image'] for name,r in byname.items()}
    objects['versionPins']=[write('images.json',version)]
    cap['source']['objectSourcePin']=write('objects.json',objects)
    main=t['mainApplication']; evidence=pinned_json(main['writerAdmission']['evidencePin'])
    evidence['writerContainerIds']=[replacements.get(x,x) for x in evidence['writerContainerIds']]
    writer=write('writer-evidence.json',evidence)
    for a in main['archiveImageBindings']:a['imageId']=byrole[a['role']]['Image']
    netids=sorted({v['NetworkID'] for r in rows for v in r['NetworkSettings']['Networks'].values()})
    nets=json.loads(subprocess.check_output(['docker','network','inspect',*netids]))
    newmain=capture_main_application(t,byrole,nets,main['archiveImageBindings'],[pin(p['path']) for p in main['configurationPins']],writer,redis_authentication=main.get('redisAuthentication'),published_data_endpoints=main.get('publishedDataEndpoints'))
    if 'archiveMountProtection' in main:newmain['archiveMountProtection']=main['archiveMountProtection']
    t['mainApplication']=newmain
    policy['baselineTargetPin']=write('baseline-target.json',t)
    cap['parent']=None
    cap_pin=write('capture.json',cap)
    policy['captureConfigurationPins'][ref]=cap_pin
    owner['sources'][ref]['configurationPath']=cap_pin['path']
    c['sourceConfigurations'][ref]=write('repository-source.json',owner)
    control_pin=write('control-source.json',c)
    resolved,evidence=resolve_capture(policy,ref,cap_pin,reader=pinned_json)
    require(resolved==cap_pin,'SOURCE_CAPTURE_RESOLUTION_MISMATCH')
    probe=root/'preflight';probe.mkdir(mode=0o700)
    runtime=Runtime(cap,Budget(probe,cap['limits']),probe);runtime.preflight()
    receipt=dict(originalControlPin=original_control_pin,releaseTag=version['releaseTag'],controlPin=control_pin,capturePin=cap_pin,preflight='PASS',sourceIdentity=cap['source']['sourceIdentity'],databaseUuid=cap['source']['databaseUuid'],evidenceCount=len(evidence),actualServices=[dict(role=k,id=v['Id'],imageId=v['Image']) for k,v in byrole.items()])
    receipt['environmentPin']=materials['application-config']
    private_write(generation/'staging-receipt.json',receipt)
    return receipt


def checked_pin(reference):
    raw=Path(reference['path']).read_bytes()
    if len(raw)!=reference['bytes'] or hashlib.sha256(raw).hexdigest()!=reference['sha256']:
        raise ValueError('SOURCE_BINDING_PIN_CHANGED')
    return json.loads(raw)


def private_write(path, value):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(value,f,sort_keys=True)


def controller(binding, run):
    pid=int(run(['systemctl','show',binding['serviceName'],'--property=MainPID','--value']).strip())
    if pid<=0:raise ValueError('SOURCE_CONTROLLER_NOT_RUNNING')
    args=(Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')
    if binding['pythonPath'].encode()!=args[0] or binding['controlEntryPath'].encode() not in args:
        raise ValueError('SOURCE_CONTROLLER_IDENTITY_CHANGED')
    pin=json.loads(args[args.index(b'--config-pin')+1])
    return pid,pin


def stage_in_runtime(binding, candidate, current_pin, program):
    """Use the source controller's runtime, not the deployment agent's Python."""
    control = checked_pin(current_pin)
    require(control['pythonPin']['path'] == binding['pythonPath'], 'SOURCE_PYTHON_MISMATCH')
    require(isinstance(program, str) and program, 'SOURCE_STAGE_PROGRAM_REQUIRED')
    bootstrap = ('import json,sys\n'
                 'request=json.load(sys.stdin)\n'
                 'namespace={"__name__":"release_source_stage"}\n'
                 'exec(compile(request["program"],"release_backup_source.py","exec"),namespace)\n'
                 'result=namespace["stage"](request["binding"],request["candidate"],request["pin"])\n'
                 'print(json.dumps(result))\n')
    request = dict(program=program, binding=binding, candidate=candidate, pin=current_pin)
    result = subprocess.run([binding['pythonPath'], '-B', '-c', bootstrap],
        input=json.dumps(request).encode('utf-8'), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=dict(os.environ, **control['environment']), timeout=1800)
    require(result.returncode == 0, 'SOURCE_STAGE_PROCESS_FAILED')
    return json.loads(result.stdout)


def synchronize(profile, candidate, *, run, inspect, stage_program=None):
    """Hold the source lock across generation and controller activation."""
    binding=profile.get('backupSourceBinding')
    if binding is None:return {'status':'NOT_CONFIGURED'}
    import fcntl,re,time
    if any(binding['containers'].get(role)!=profile[role] for role in ('backend','frontend')):
        raise ValueError('SOURCE_BINDING_APPLICATION_MISMATCH')
    tag=candidate['releaseTag']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+',tag):raise ValueError('INVALID_RELEASE_TAG')
    service=binding['serviceName']
    if not re.fullmatch(r'[A-Za-z0-9_.@-]+\.service',service):raise ValueError('INVALID_SOURCE_SERVICE')
    for key in ('engineRoot','generationRoot','environmentFile','composeFile','pythonPath','controlEntryPath','dropInDirectory'):
        if not Path(binding[key]).is_absolute():raise ValueError('SOURCE_BINDING_PATH_NOT_ABSOLUTE')
    if Path(binding['controlEntryPath'])!=Path(binding['engineRoot'])/'control_entry.py':
        raise ValueError('SOURCE_ENGINE_ENTRY_MISMATCH')
    root=Path(binding['generationRoot'])/tag
    original_pid,current_pin=controller(binding,run)
    current=checked_pin(current_pin)
    ref=binding['sourceRef']
    lock_path=current['sourceEpochPolicies'][ref]['sourceLockPath']
    with open(lock_path,'a+b') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        pid,actual_pin=controller(binding,run)
        if pid!=original_pid or actual_pin!=current_pin:raise ValueError('SOURCE_CONTROLLER_CHANGED')
        children=(Path('/proc')/str(pid)/'task'/str(pid)/'children').read_text().strip()
        if children:raise ValueError('SOURCE_OPERATION_ACTIVE')
        receipt_path=root/'staging-receipt.json'
        if receipt_path.exists():
            receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
            if receipt['releaseTag']!=tag or current_pin not in [receipt['originalControlPin'],receipt['controlPin']]:
                raise ValueError('SOURCE_GENERATION_MISMATCH')
            checked_pin(receipt['controlPin']);checked_pin(receipt['capturePin'])
            for item in receipt['actualServices']:
                observed=inspect(binding['containers'][item['role']])
                if observed['Id']!=item['id'] or observed['Image']!=item['imageId'] or not observed['State']['Running']:
                    raise ValueError('SOURCE_GENERATION_CONTAINER_CHANGED')
        else:
            receipt=stage_in_runtime(binding,candidate,current_pin,stage_program)
        target_pin=receipt['controlPin']
        if current_pin!=target_pin:
            active_pid,active_pin=controller(binding,run)
            if active_pid!=pid or active_pin!=current_pin:
                raise ValueError('SOURCE_CONTROLLER_CHANGED')
            if (Path('/proc')/str(pid)/'task'/str(pid)/'children').read_text().strip():
                raise ValueError('SOURCE_OPERATION_ACTIVE')
            drop=Path(binding['dropInDirectory'])
            if drop.name!=service+'.d':raise ValueError('SOURCE_DROPIN_SERVICE_MISMATCH')
            drop.mkdir(mode=0o700,parents=True,exist_ok=True)
            destination=drop/'zz-release-source-binding.conf'
            values=[binding['pythonPath'],binding['controlEntryPath']]
            if any(any(c in x for c in '\n\r"%') for x in values):raise ValueError('SOURCE_EXEC_PATH_INVALID')
            pin_text=json.dumps(target_pin,separators=(',',':'))
            if "'" in pin_text or '%' in pin_text:raise ValueError('SOURCE_PIN_PATH_INVALID')
            content='[Service]\nExecStart=\nExecStart="'+values[0]+'" -B "'+values[1]+'" serve --config-pin \''+pin_text+'\'\n'
            if destination.exists():
                previous=destination.read_text(encoding='utf-8')
                if previous!=content:
                    previous_text=content.replace(pin_text,json.dumps(current_pin,separators=(',',':')))
                    if previous!=previous_text:raise ValueError('SOURCE_DROPIN_CHANGED')
                    evidence=root/'previous-dropin.json'
                    if not evidence.exists():private_write(evidence,{'content':previous})
            if not destination.exists() or destination.read_text(encoding='utf-8')!=content:
                fd,temp=tempfile.mkstemp(prefix='.release-source-',dir=drop)
                with os.fdopen(fd,'w',encoding='utf-8') as f:f.write(content)
                os.replace(temp,destination)
            run(['systemctl','daemon-reload'])
            run(['systemctl','restart',service])
            for attempt in range(20):
                new_pid=int(run(['systemctl','show',service,'--property=MainPID','--value']).strip())
                if new_pid>0:break
                time.sleep(.25)
            _,activated=controller(binding,run)
            if activated!=target_pin:raise ValueError('SOURCE_ACTIVATION_PIN_MISMATCH')
        run(['systemctl','is-active','--quiet',service])
        environment=Path(receipt['environmentPin']['path']).read_bytes()
        if hashlib.sha256(environment).hexdigest()!=receipt['environmentPin']['sha256']:
            raise ValueError('SOURCE_ENVIRONMENT_PIN_CHANGED')
        if Path(binding['environmentFile']).read_bytes()!=environment:
            raise ValueError('SOURCE_ENVIRONMENT_CHANGED')
        result={'status':'SYNCHRONIZED','releaseTag':tag,'controlPin':target_pin,'capturePin':receipt['capturePin'],
                'actualServices':receipt['actualServices']}
        saved=root/'activation-receipt.json'
        if saved.exists():
            if json.loads(saved.read_text())!=result:raise ValueError('SOURCE_ACTIVATION_RECEIPT_CHANGED')
        else:private_write(saved,result)
        return result
