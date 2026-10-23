"""Retained rehearsal tail contracts. All external boundaries are mocked; no remote writes."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import intruoyi_rehearsal_agent as a
from intruoyi_runtime import require, RuntimeBlocked


def sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class RetainedTailTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder=Path(self.temp.name)/'seed'
        self.folder.mkdir()
        self.progress=Path(self.temp.name)/'jobs'
        self.root='JOB-9310b279dd'
        self.retry='JOB-1111111111'
        self.profile=dict(environment='rehearsal',sourceEnvironment='prod',network='internal',host='192.0.2.58',acceptanceFrontend='acceptance',
                          entryUrl='http://192.0.2.58:38092',acceptanceUrl='http://192.0.2.58:38093',
                          isolatedMinioPublicUrl='http://192.0.2.58:39092',
                          **{role:a.PREFIX+'-'+role for role in ('backend','frontend','database','redis','minio')})
        self.source=dict(entryUrl='http://192.0.2.57:48080',mediaUrlColumns=[{'table':'infra_file'}])
        self.raw='server { listen 48080; location /admin-api/ { proxy_pass http://backend:48081/; } }\n'
        self.images={role:'image-'+role for role in ('backend','frontend','database','redis','minio')}
        self.origin=dict(images={k:self.images[k] for k in ('backend','frontend')},schemaSha256='schema',ledgerSha256='ledger',releaseTag='baseline')
        self.capture=dict(originFingerprint='origin',origin=self.origin,images=self.images,
                          backendUpstreams=['original-backend'],minioUpstreams=['original-minio'],
                          mediaIdentity={'objects':4},historicalMetadata={'releaseTag':'baseline'},artifacts=[])
        for name in ('recovery.sql','minio.tar','redis.jsonl','backend-startup.private.json','historical-release-info.json'):
            (self.folder/name).write_bytes(('retained-'+name).encode())
            self.capture['artifacts'].append(dict(name=name,bytes=(self.folder/name).stat().st_size,sha256=file_sha(self.folder/name)))
        self.capture['artifacts'].append(dict(name='nginx.conf',bytes=len(self.raw.encode()),sha256=hashlib.sha256(self.raw.encode()).hexdigest()))
        self.write('rehearsal-owned.json',{'owner':a.PREFIX})
        self.write('verified-media-origin.json',self.capture['mediaIdentity'])
        self.write('isolated-media-url-transformations.json',dict(columns=[],remainingRegisteredOrigins=0,sourceInventorySha256=sha(self.source['mediaUrlColumns'])))
        self.write('isolated-config-transformations.json',[{'id':1}])
        self.write('isolated-startup-differences.json',{'copiedSourceMountCount':0})
        old=a.isolated_nginx_config(self.raw,48080,self.capture['backendUpstreams'],self.profile['backend'],self.capture['minioUpstreams'],self.profile['minio'])
        (self.folder/'nginx.conf').write_text(old)
        self.corrected=a.isolated_nginx_config(self.raw,48080,['original-backend','backend'],self.profile['backend'],['original-minio'],self.profile['minio'])
        ingress=a.rehearsal_gateway_ingress(self.profile)
        (self.folder/'gateway-nginx.conf').write_text(ingress['nginx'])
        self.items={}
        for role in (*self.images,'gateway'):
            name=self.profile[role] if role!='gateway' else a.PREFIX+'-gateway'
            self.items[name]=dict(Id='id-'+role,Image=self.images['frontend' if role=='gateway' else role],
                                 Config={'Labels':{a.LABEL:a.PREFIX}},State={'Running':role!='frontend'},
                                 NetworkSettings={'Networks':{'internal':{}}},
                                 HostConfig={'PortBindings':ingress['portBindings'] if role=='gateway' else {}},Mounts=[])
        for role,name in [('frontend','nginx.conf'),('gateway','gateway-nginx.conf')]:
            key=self.profile[role] if role!='gateway' else a.PREFIX+'-gateway'
            self.items[key]['Mounts']=[dict(Type='bind',Destination='/etc/nginx/conf.d/default.conf',Source=str(self.folder/name),RW=False)]
        self.remote=Mock()
        self.remote.inspect.side_effect=lambda name:copy.deepcopy(self.items[name])
        self.remote.run.return_value=json.dumps([dict(Internal=True,Labels={a.LABEL:a.PREFIX})]).encode()
        self.observed=dict(self.origin,fingerprint='isolated',backendHealth={'status':'UP'},frontendHttpStatus=200,readOnly=dict(read_only=False,super_read_only=False))
        self.api=dict(require=require,remote=self.remote,sha=sha,file_sha=file_sha,private_json=self.write_path,
                      observe=Mock(side_effect=lambda p:copy.deepcopy(self.observed)),RuntimeBlocked=RuntimeBlocked,docker=Mock(side_effect=self.docker))
        self.p=dict(profile=self.profile,sourceProfile=self.source,originalJobId=self.root,retryJobId=self.retry,
                    releaseTag='2026-10-23-16-51-17',packageSha256='a'*64,manifestSha256='b'*64,
                    sourceProof=dict(source='prod',originalJobId=self.root,releaseTag='2026-10-23-16-51-17',capture=self.capture,
                                     captureIdentity=sha(self.capture),captureSha256='c'*64,nginx=self.raw,
                                     backendUpstreams=['original-backend','backend'],minioUpstreams=['original-minio']))
        self.original=dict(jobId=self.root,phase='failed',pid=123,processStart='stopped')
        self.journals={self.root:dict(self.original)}
        (self.progress/self.root).mkdir(parents=True)
        self.write_path(self.progress/self.root/'rehearsal-progress.private.json',self.original)
        self.dispatch_original=a.dispatch
        self.addCleanup(patch.stopall)
        patch.object(a,'REHEARSAL_PROGRESS_ROOT',self.progress).start()
        self.worker_generation=0
        patch.object(a,'process_start_identity',side_effect=lambda pid:'current-'+str(self.worker_generation) if pid==os.getpid() else None).start()
        patch.object(a,'dispatch',side_effect=self.dispatch).start()
        response=Mock(status=200)
        response.__enter__=Mock(return_value=response)
        response.__exit__=Mock(return_value=False)
        patch.object(a,'urlopen',return_value=response).start()

    def write_path(self,path,value):
        Path(path).write_text(json.dumps(value))

    def write(self,name,value):
        self.write_path(self.folder/name,value)

    def docker(self,method,path,*args):
        self.assertEqual(method,'POST')
        self.assertTrue(path.endswith('/start'))
        identity=path.split('/')[2]
        next(x for x in self.items.values() if x['Id']==identity)['State']['Running']=True

    def dispatch(self,p,api):
        if p['action']=='rehearsal-verify-stopped':
            return {'stopped':True}
        if p['action']=='rehearsal-job-progress':
            self.journals[p['jobId']]=dict(jobId=p['jobId'],phase=p['phase'])
            return self.journals[p['jobId']]
        if p['action']=='rehearsal-job-status':
            return dict(self.journals[p['jobId']],status='succeeded')
        self.fail('Unexpected action: '+p['action'])

    def run_tail(self):
        self.worker_generation+=1
        return a.resume_rehearsal_tail(self.p,self.api,self.folder)

    def test_success_only_repairs_mounted_inode_and_starts_frontend(self):
        inode=(self.folder/'nginx.conf').stat().st_ino
        result=self.run_tail()
        self.assertEqual((self.folder/'nginx.conf').stat().st_ino,inode)
        self.assertEqual((self.folder/'nginx.conf').read_text(),self.corrected)
        self.api['docker'].assert_called_once_with('POST','/containers/id-frontend/start')
        self.assertEqual(self.journals[self.root],self.original)
        self.assertEqual(result['resumeReceipt']['status'],'completed')
        self.assertEqual(result['remotePreparationProgress']['jobId'],self.retry)
        self.remote.sql.assert_not_called()

    def test_source_crlf_bytes_survive_actual_proof_json_transport_and_tail(self):
        source_root=Path(self.temp.name)/'source'
        source_folder=source_root/'rehearsal-seed'/self.p['releaseTag']
        source_folder.mkdir(parents=True)
        raw=self.raw.replace('\n','\r\n').encode('utf-8')
        (source_folder/'nginx.conf').write_bytes(raw)
        self.write_path(source_folder/'rehearsal-owned.json',{'owner':a.PREFIX})
        artifact=next(x for x in self.capture['artifacts'] if x['name']=='nginx.conf')
        artifact.update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        self.capture['origin']['components']={role:{'containerId':'id-'+role} for role in ('backend','frontend')}
        self.write_path(source_folder/'capture-complete.private.json',self.capture)
        self.items[self.profile['backend']]['NetworkSettings']['Networks']['internal']['Aliases']=['backend']
        source_profile=dict(self.profile,environment='prod')
        source_api=dict(self.api,directory=lambda profile,tag:source_root/tag)
        source_observation=dict(self.observed,fingerprint='origin',maintenance=False)
        source_api['observe']=Mock(return_value=source_observation)
        self.journals[self.root]['phase']='capture-complete'
        proof=self.dispatch_original(dict(profile=source_profile,action='rehearsal-tail-source-proof',
                                          originalJobId=self.root,releaseTag=self.p['releaseTag'],expectedOriginFingerprint='origin'),source_api)
        transported=json.loads(json.dumps(proof))
        self.assertEqual(transported['nginx'].encode('utf-8'),raw)
        self.assertEqual(hashlib.sha256(transported['nginx'].encode('utf-8')).hexdigest(),artifact['sha256'])
        self.journals[self.root]=dict(self.original)
        self.p['sourceProof']=copy.deepcopy(transported)
        self.p['sourceProof']['nginx']=transported['nginx'].replace('\r\n','\n')
        with self.assertRaisesRegex(RuntimeBlocked,'Original source Nginx content differs'):
            self.run_tail()
        self.api['docker'].assert_not_called()
        self.p['sourceProof']=transported
        result=self.run_tail()
        self.assertEqual(result['resumeReceipt']['status'],'completed')
        self.assertEqual((self.folder/'nginx.conf').read_text(),self.corrected)
        self.assertEqual((source_folder/'nginx.conf').read_bytes(),raw)

    def test_completed_recollection_uses_original_success_job_and_fresh_health(self):
        self.run_tail()
        self.api['docker'].reset_mock()
        self.api['observe'].reset_mock()
        self.p['retryJobId']='JOB-2222222222'
        result=self.run_tail()
        self.assertEqual(result['resumeReceipt']['retryJobId'],self.retry)
        self.assertEqual(result['remotePreparationProgress']['jobId'],self.retry)
        self.api['docker'].assert_not_called()
        self.assertGreaterEqual(self.api['observe'].call_count,2)

    def test_health_failure_is_retained_and_running_frontend_can_be_verified_again(self):
        self.observed['frontendHttpStatus']=503
        with patch.object(a.time,'monotonic',side_effect=[0,241]),self.assertRaises(RuntimeBlocked):
            self.run_tail()
        old=json.loads((self.folder/'tail-resume'/self.retry/'receipt.private.json').read_text())
        self.assertEqual((old['status'],old['phase']),('failed','health'))
        self.observed['frontendHttpStatus']=200
        self.p['retryJobId']='JOB-2222222222'
        self.api['docker'].reset_mock()
        result=self.run_tail()
        self.assertEqual(result['resumeReceipt']['retryJobId'],'JOB-2222222222')
        self.api['docker'].assert_not_called()
        self.assertEqual(json.loads((self.folder/'tail-resume'/self.retry/'receipt.private.json').read_text()),old)

    def test_changed_nginx_schema_or_owned_image_rejected_before_start(self):
        for kind in ('nginx','schema','image','media'):
            with self.subTest(kind=kind):
                if kind=='nginx':
                    path=self.folder/'nginx.conf'; original=path.read_text(); path.write_text('unrelated')
                elif kind=='schema':self.observed['schemaSha256']='changed'
                elif kind=='image':self.items[self.profile['backend']]['Image']='wrong'
                else:self.write('verified-media-origin.json',{})
                with self.assertRaises(RuntimeBlocked):self.run_tail()
                self.api['docker'].assert_not_called()
                if kind=='nginx':path.write_text(original)
                elif kind=='schema':self.observed['schemaSha256']='schema'
                elif kind=='image':self.items[self.profile['backend']]['Image']=self.images['backend']
                else:self.write('verified-media-origin.json',self.capture['mediaIdentity'])

    def test_running_original_worker_rejected(self):
        with patch.object(a,'process_start_identity',return_value='stopped'),self.assertRaises(RuntimeBlocked):
            self.run_tail()
        self.api['docker'].assert_not_called()

    def test_running_frontend_without_prior_tail_proof_is_rejected(self):
        self.items[self.profile['frontend']]['State']['Running']=True
        (self.folder/'nginx.conf').write_text(self.corrected)
        with self.assertRaises(RuntimeBlocked):self.run_tail()
        self.api['docker'].assert_not_called()


if __name__=='__main__':
    unittest.main()
