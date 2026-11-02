"""Prepare NEW PROD57 resources from inspected rehearsal configuration only.

No backup/restore is invoked. No existing resource is removed or changed.
Failures retain new resources and a private command log for diagnosis.
Default mode is read-only; --create is required for provisioning.
"""
import argparse,hashlib,ipaddress,json,os,shutil,socket,subprocess,time
from pathlib import Path

BASE=Path('/var/lib/docker/intruoyi-data/prod57-optimized-rehearsal-20261021')
OLD=BASE/'target-r1'
NEW=Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-restore-20261024-r1')
TARGET='intruoyi-57-retest-safe-20261024-r1'
PORT=53057
SUBNET='172.28.141.0/24'

def run(argv,**kwargs):
    p=subprocess.run(argv,capture_output=True,timeout=60,**kwargs)
    if p.returncode:
        if NEW.is_dir():
            f=NEW/'command-error.private.json'
            f.write_text(json.dumps(dict(program=argv[0],exitCode=p.returncode,stderr=p.stderr.decode('utf-8',errors='replace'))),encoding='utf-8');f.chmod(0o600)
        raise RuntimeError('PREPARE_COMMAND_FAILED:'+argv[0])
    return p.stdout

def docker(*args):return run(['docker',*args]).decode().strip()
def pin(p):
    p=Path(p);raw=p.read_bytes()
    return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def write(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,sort_keys=True,separators=(',',':'))
    p.chmod(0o600)
    return pin(p)

def normalize_attachment_route(raw,minio_ip):
    """Require the known template contract and keep attachments on the target origin."""
    proxy=b'proxy_pass http://'+str(ipaddress.ip_address(minio_ip)).encode()+b':9000;'
    if b'location /yudao/' not in raw or proxy not in raw:
        raise ValueError('TARGET_MINIO_ROUTE_MISSING')
    sources=(b'http://127.0.0.1:9000/yudao/',b'http://172.30.30.57:9000/yudao/')
    old=b'"http://127.0.0.1:18322/yudao/"'
    new=b'"/yudao/"'
    rules=[line.strip() for line in raw.splitlines() if line.strip().startswith(b'sub_filter ')]
    old_rules=[b'sub_filter "'+source+b'" '+old+b';' for source in sources]
    new_rules=[b'sub_filter "'+source+b'" '+new+b';' for source in sources]
    if sorted(rules)==sorted(new_rules*2):
        return raw
    if sorted(rules)!=sorted(old_rules*2) or raw.count(old)!=4:
        raise ValueError('ATTACHMENT_REWRITE_CONTRACT')
    return raw.replace(old,new)

def main(create):
    assert os.geteuid()==0 and Path('/etc/machine-id').read_text().strip()=='f90361360b284aeb8a9ba727db31e434','PROD57_MACHINE_MISMATCH'
    assert not NEW.exists(),'NEW_TARGET_ROOT_EXISTS'
    template=json.loads((BASE/'configuration/recovery.json').read_text())
    target=template['targets']['intruoyi-PROD57-optimized-target-20261021-r1']
    for values in target['secrets'].values():
        for expected in values.values():assert pin(expected['path'])==expected,'TEMPLATE_SECRET_PIN_CHANGED'
    for binding in target['application']['configurationBindings']:
        expected=binding['targetPin'];assert pin(expected['path'])==expected,'TEMPLATE_CONFIGURATION_PIN_CHANGED'
    assert docker('info','--format','{{.ID}}')==target['dockerEngineId'],'DOCKER_ID_MISMATCH'
    ids=docker('network','ls','-q').splitlines()
    networks=json.loads(docker('network','inspect',*ids))
    candidate=ipaddress.ip_network(SUBNET)
    for network in networks:
        for cfg in network['IPAM']['Config'] or []:
            if cfg.get('Subnet'):
                old=ipaddress.ip_network(cfg['Subnet'])
                assert old.version!=4 or not candidate.overlaps(old),'NEW_SUBNET_OVERLAP'
    with socket.socket() as s:s.bind(('127.0.0.1',PORT))
    assert shutil.disk_usage(BASE).free>80*1024**3,'DATA_DISK_FREE_TOO_LOW'
    memory=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))
    assert memory>7*1024**2,'MEMORY_AVAILABLE_TOO_LOW'
    source_root=Path('/var/lib/docker/intruoyi-data/spug-intruoyi-57-safe-20261024-v1')
    source_receipt=json.loads((source_root/'registration-receipt.json').read_bytes())
    source_capture=json.loads((source_root/'configuration/capture.json').read_bytes())
    captured=json.loads((source_root/'private/container-inspects.json').read_bytes())
    assert [v['Id'] for v in captured]==source_receipt['containerIds'],'SOURCE_SNAPSHOT_ORDER_CHANGED'
    source_meta=source_capture['source']
    source_password=Path(source_meta['passwordPin']['path']).read_bytes().rstrip(b'\r\n')+b'\n'
    source_sql='IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec mysql --protocol=socket --user=root --batch --skip-column-names -e "SELECT @@lower_case_table_names"'
    source_case=run(['docker','exec','-i',source_meta['mysqlContainerId'],'sh','-c',source_sql],input=source_password).decode().strip()
    assert source_case in ('0','1','2'),'SOURCE_CASE_RULE_INVALID'
    source_images={role:v['Image'] for role,v in zip(('mysql','minio','redis','backend','frontend'),captured)}
    assert set(source_images.values())==set(source_capture['source']['applicationImageIds']),'SOURCE_IMAGE_SCOPE_CHANGED'
    for role,image in source_images.items():
        assert json.loads(docker('image','inspect',image))[0]['Id']==image,'SOURCE_IMAGE_MISSING'
    originals=[];files={};old_ips={}
    for values in target['secrets'].values():
        for expected in values.values():
            p=Path(expected['path']);assert OLD in p.parents
            files[str(p)]=p.read_bytes()
    for index,service in enumerate(target['services']):
        v=json.loads(docker('inspect',service['id']))[0]
        assert v['Id']==service['id'] and v['Image']==service['imageId'],'TEMPLATE_IDENTITY_CHANGED'
        assert v['Config']['Labels']['intruoyi.recovery.target']==target['targetId'],'TEMPLATE_NOT_REHEARSAL'
        assert not v['HostConfig']['Privileged'] and not v['HostConfig']['CapAdd'],'TEMPLATE_PRIVILEGE_INVALID'
        assert v['HostConfig']['RestartPolicy']['Name']=='no','TEMPLATE_AUTORESTART_INVALID'
        health=v['Config'].get('Healthcheck')
        assert not health or health['Test'][0] in ('NONE','CMD-SHELL'),'HEALTHCHECK_COMMAND_TYPE_UNSUPPORTED'
        for m in v['Mounts']:
            if m['Type']=='bind':
                p=Path(m['Source'])
                assert not m['RW'] and OLD in p.parents and p.is_file() and not p.is_symlink(),'TEMPLATE_BIND_SCOPE_INVALID'
                files[str(p)]=p.read_bytes()
            else:
                assert m['Type']=='volume' and m['RW'],'TEMPLATE_DATA_MOUNT_INVALID'
        for field in ('Devices','DeviceRequests'):
            assert not v['HostConfig'].get(field),'TEMPLATE_DEVICE_INVALID'
        originals.append((service,v));old_ips[service['ip']]=str(candidate.network_address+32+index)
        assert not docker('ps','-a','--filter','name=^/'+TARGET+'-'+service['role']+'$','--format','{{.ID}}'),'NEW_CONTAINER_EXISTS'
    assert not docker('network','ls','--filter','name=^'+TARGET+'$','--format','{{.ID}}'),'NEW_NETWORK_EXISTS'
    for role in ('mysql','minio','redis'):
        assert not docker('volume','ls','--filter','name=^'+TARGET+'-'+role+'$','--format','{{.Name}}'),'NEW_VOLUME_EXISTS'
    # Validate all copied configuration before creating any target resource.
    prepared_files={}
    nginx_path=str(OLD/'config/nginx.conf')
    assert nginx_path in files,'TARGET_NGINX_CONFIG_MISSING'
    minio_ip=next(old_ips[s['ip']] for s,_ in originals if s['role']=='minio')
    for old_path,raw in files.items():
        for a,b in old_ips.items():raw=raw.replace(a.encode(),b.encode())
        if old_path==nginx_path:raw=normalize_attachment_route(raw,minio_ip)
        prepared_files[old_path]=raw
    plan=dict(host='172.30.30.57',targetId=TARGET,dataRoot=str(NEW),subnet=SUBNET,port=PORT,sourceConfigRef='intruoyi-57-safe-20261024-v1',templateTarget=target['targetId'],templateServices=[dict(role=s['role'],id=s['id'],image=s['imageId']) for s,_ in originals],readOnlyConfigurationFiles=len(files),freeMemoryKiB=memory,create=create,currentSourceImages=source_images,attachmentRoute='/yudao/',nginxConfigurationSha256=hashlib.sha256(prepared_files[nginx_path]).hexdigest())
    if not create:
        print(json.dumps(plan));return
    NEW.mkdir(mode=0o700);(NEW/'private').mkdir(mode=0o700);(NEW/'config').mkdir(mode=0o700)
    write(NEW/'preparation-plan.json',plan)
    for old_path,raw in prepared_files.items():
        destination=NEW/Path(old_path).relative_to(OLD)
        with destination.open('xb') as f:f.write(raw)
        destination.chmod(Path(old_path).stat().st_mode&0o777)
        metadata=Path(old_path).stat()
        os.chown(destination,metadata.st_uid,metadata.st_gid)
    network_id=docker('network','create','--internal','--subnet',SUBNET,'--label','intruoyi.recovery.target='+TARGET,TARGET)
    volumes={role:json.loads(docker('volume','inspect',docker('volume','create','--label','intruoyi.recovery.target='+TARGET,TARGET+'-'+role)))[0] for role in ('mysql','minio','redis')}
    services=[]
    for service,v in originals:
        role=service['role'];cfg=v['Config'];host=v['HostConfig']
        env=[]
        for entry in cfg['Env'] or []:
            for a,b in old_ips.items():entry=entry.replace(a,b)
            assert '\n' not in entry and '\r' not in entry,'ENV_NEWLINE_INVALID'
            env.append(entry)
        envfile=NEW/'private'/(role+'.env')
        envfile.write_text('\n'.join(env)+'\n',encoding='utf-8');envfile.chmod(0o600)
        cmd=['docker','create','--name',TARGET+'-'+role,'--network',network_id,'--network-alias',role,'--ip',old_ips[service['ip']],'--restart=no','--memory',str(host['Memory'] or 512*1024**2),'--env-file',str(envfile),'--log-opt','max-size=5m','--log-opt','max-file=2']
        labels=dict(cfg.get('Labels') or {});labels['intruoyi.recovery.target']=TARGET
        for k,val in labels.items():cmd+=['--label',k+'='+val]
        for m in v['Mounts']:
            if m['Type']=='bind':
                spec='type=bind,src='+str(NEW/Path(m['Source']).relative_to(OLD))+',dst='+m['Destination']+',readonly'
                if m.get('Propagation'):spec+=',bind-propagation='+m['Propagation']
            else:spec='type=volume,src='+TARGET+'-'+role+',dst='+m['Destination']
            cmd+=['--mount',spec]
        if role=='frontend':cmd+=['-p','127.0.0.1:'+str(PORT)+':80']
        if cfg.get('User'):cmd+=['--user',cfg['User']]
        if cfg.get('WorkingDir'):cmd+=['--workdir',cfg['WorkingDir']]
        health=cfg.get('Healthcheck')
        if health and health['Test'][0]!='NONE':
            assert health['Test'][0]=='CMD-SHELL','HEALTHCHECK_COMMAND_TYPE_UNSUPPORTED'
            cmd+=['--health-cmd',health['Test'][1]]
            for key,flag in [('Interval','--health-interval'),('Timeout','--health-timeout'),('StartPeriod','--health-start-period')]:
                if health.get(key):cmd+=[flag,str(health[key])+'ns']
            if health.get('Retries'):cmd+=['--health-retries',str(health['Retries'])]
        entry=cfg.get('Entrypoint') or []
        if entry:cmd+=['--entrypoint',entry[0]]
        cmd+=[source_images[role],*entry[1:],*(cfg.get('Cmd') or [])]
        cid=run(cmd).decode().strip()
        actual=json.loads(docker('inspect',cid))[0]
        assert actual['Id']==cid and actual['Image']==source_images[role],'NEW_CONTAINER_IDENTITY_INVALID'
        services.append(dict(role=role,id=cid,imageId=actual['Image'],ip=old_ips[service['ip']]))
    firewall=target['iptablesPin']['path']
    assert pin(firewall)==target['iptablesPin'],'IPTABLES_BINARY_CHANGED'
    for chain,rule in [('INPUT',['-s',SUBNET,'-m','conntrack','--ctstate','NEW','-j','REJECT']),('DOCKER-USER',['-s',SUBNET,'!','-d',SUBNET,'-m','conntrack','--ctstate','NEW','-j','REJECT'])]:
        run([firewall,'-I',chain,'1',*rule]);run([firewall,'-C',chain,*rule])
    for s in services:
        if s['role'] in ('mysql','redis'):docker('start',s['id'])
    mysql=next(s['id'] for s in services if s['role']=='mysql')
    deadline=time.monotonic()+180
    while True:
        p=subprocess.run(['docker','exec',mysql,'mysql','--defaults-extra-file=/run/recovery/mysql-client.cnf','-Nse',"SELECT @@server_uuid; SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='ruoyi-vue-pro'; SELECT @@lower_case_table_names"],capture_output=True)
        if p.returncode==0:break
        assert time.monotonic()<deadline,'MYSQL_INITIALIZATION_TIMEOUT'
        time.sleep(2)
    values=p.stdout.decode().strip().splitlines()
    assert len(values)==3 and values[1:] == ['0',source_case],'NEW_DATABASE_NOT_EMPTY_OR_CASE_MISMATCH'
    assert values[0] != source_receipt['databaseUuid'],'DATABASE_UUID_REUSED'
    redis=next(s['id'] for s in services if s['role']=='redis')
    password_pin=target['secrets']['redis']['REDIS_PASSWORD'];password=Path(password_pin['path']).read_bytes()
    response=run(['docker','exec','-i',redis,'redis-cli','--no-auth-warning','--askpass','DBSIZE'],input=password+b'\n').decode()
    assert response.strip().endswith('0'),'NEW_REDIS_NOT_EMPTY'
    assert not list(Path(volumes['minio']['Mountpoint']).iterdir()),'NEW_MINIO_VOLUME_NOT_EMPTY'
    assert not (NEW/'.recovery-operation.json').exists(),'NEW_TARGET_OCCUPIED'
    receipt=dict(plan,networkId=network_id,services=services,volumes=volumes,databaseUuid=values[0],databaseEmpty=True,redisEmpty=True,minioVolumeEmpty=True,targetUnreserved=True)
    write(NEW/'prepared-target-ready.json',receipt)
    print(json.dumps(receipt))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--create',action='store_true')
    main(parser.parse_args().create)
