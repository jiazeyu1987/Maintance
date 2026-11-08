"""Task-owned Docker integration; no business containers, ports or volumes."""
from pathlib import Path
import hashlib
import gzip
import http.client
import io
import json
import os
import socket
import sys
import tarfile
import tempfile
import time
from urllib.parse import quote

sys.path[:0] = ['/src/ops/recovery', '/src/scripts/tests']
from recovery_engine import pin, pinned_json
from recovery_program_containers import UnixDocker
from recovery_program_import import prepare_image_import, load_image_import
from test_recovery_program_generation import case
from test_recovery_program_activation import locked, claim, start


def main():
    deadline = time.monotonic()+240
    def guard():
        if time.monotonic() >= deadline: raise TimeoutError('native image import deadline')
    api_version = os.environ['PROGRAM_TEST_API']
    engine = UnixDocker(guard=guard,deadline=deadline,api_version=api_version)
    base = os.environ['PROGRAM_TEST_BASE_IMAGE']
    prefix = 'codex-program-import-native-20261108-r1'
    label = {'codex.task':'20261106-spug-prod-incremental-to-two-targets','spug.program.import':prefix}
    repository = prefix
    protected = repository+':protected'
    created = []; archived = None; tag_created = False
    output = Path(os.environ['PROGRAM_TEST_EVIDENCE_DIR'])
    result = dict(schemaVersion='NativeProgramImageImportCheck/v1',status='RUNNING',
                  databaseRestoreExecuted=False,productionServerTouched=False)

    def transfer(method, path, *, source=None, destination=None):
        guard()
        connection = http.client.HTTPConnection('localhost',timeout=30)
        transport = socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        try:
            transport.settimeout(30); transport.connect('/var/run/docker.sock'); connection.sock=transport
            connection.putrequest(method,'/v'+api_version+path)
            if source is not None:
                connection.putheader('Content-Type','application/x-tar')
                connection.putheader('Content-Length',str(source.stat().st_size))
            connection.endheaders()
            if source is not None:
                with source.open('rb') as stream:
                    while True:
                        guard(); data=stream.read(1024*1024)
                        if not data: break
                        connection.send(data)
            response=connection.getresponse()
            if not 200 <= response.status < 300: raise RuntimeError('native Docker HTTP '+str(response.status))
            body=bytearray(); count=0
            while True:
                guard(); data=response.read1(1024*1024)
                if not data: break
                count+=len(data)
                if count > 1024**3: raise RuntimeError('native transfer budget')
                if destination is None:
                    if count > 1024**2: raise RuntimeError('native response budget')
                    body.extend(data)
                else: destination.write(data)
            return bytes(body)
        finally:
            connection.close(); transport.close()

    failure = None; cleanup_errors = []
    try:
        assert engine.image(base)['Id'] == base
        assert not engine.request('GET','/containers/json?all=true&filters='+quote(json.dumps({'name':[prefix]}),safe=''))
        assert not engine.request('GET','/images/json?filters='+quote(json.dumps({'reference':[repository+':*']}),safe=''))
        original = engine.request('POST','/containers/create?name='+prefix+'-source',dict(
            Image=base,Cmd=['/bin/true'],Labels=label,HostConfig=dict(NetworkMode='none')))
        created.append(original['Id'])
        commit = engine.request('POST','/commit?container='+original['Id'],dict(
            Entrypoint=['/bin/sh','-c'],Cmd=['printf archived-program-import-ok'],Labels=label))
        archived = commit['Id']
        assert archived != base
        engine.request('POST','/images/'+archived+'/tag?repo='+repository+'&tag=protected')
        tag_created=True
        with tempfile.TemporaryDirectory(prefix='program-import-native-') as temporary:
            root=Path(temporary); fixture=case.__wrapped__(root)
            saved_archive=root/'engine-saved.tar'
            with saved_archive.open('xb') as stream:
                transfer('GET','/images/get?names='+quote(protected,safe=''),destination=stream)
            with tarfile.open(saved_archive) as saved:
                manifest=json.load(saved.extractfile('manifest.json'))
                saved_ids=['sha256:'+hashlib.sha256(saved.extractfile(row['Config']).read()).hexdigest() for row in manifest]
            result.update(commitReturnedId=archived,engineImageId=engine.image(archived)['Id'],
                savedConfigIds=saved_ids,savedManifestEntries=len(manifest))
            assert len(saved_ids)==1
            program_id=saved_ids[0]
            # The production contract is the legacy, uncompressed Docker-save
            # format already verified in the real server archives. Desktop's
            # containerd store exports compressed OCI blobs. Construct that
            # explicit legacy fixture from the real config and real layers;
            # the production reader retains its strict format and digest rules.
            archive=root/'original.tar'
            with tarfile.open(saved_archive) as saved, tarfile.open(archive,'w') as legacy:
                entry=manifest[0]; config=saved.extractfile(entry['Config']).read()
                configuration=json.loads(config)
                config_name=program_id[7:]+'.json'
                item=tarfile.TarInfo(config_name);item.size=len(config);legacy.addfile(item,io.BytesIO(config))
                layers=[]
                for index,(name,expected) in enumerate(zip(entry['Layers'],configuration['rootfs']['diff_ids'])):
                    layer_path=root/('layer-%d.tar'%index)
                    with saved.extractfile(name) as blob, layer_path.open('xb') as layer:
                        magic=blob.read(2);blob.seek(0)
                        if magic==b'\x1f\x8b': reader=gzip.GzipFile(fileobj=blob)
                        else: reader=blob
                        try:
                            while True:
                                guard();data=reader.read(1024*1024)
                                if not data:break
                                layer.write(data)
                        finally:
                            if reader is not blob:reader.close()
                    assert 'sha256:'+pin(layer_path)['sha256']==expected
                    layer_name='layer-%d/layer.tar'%index;layers.append(layer_name)
                    item=tarfile.TarInfo(layer_name);item.size=layer_path.stat().st_size
                    with layer_path.open('rb') as layer:legacy.addfile(item,layer)
                    layer_path.unlink()
                raw=json.dumps([dict(Config=config_name,RepoTags=[protected],Layers=layers)]).encode()
                item=tarfile.TarInfo('manifest.json');item.size=len(raw);legacy.addfile(item,io.BytesIO(raw))
            original_pin=pin(archive)
            result.update(fixtureFormat='LEGACY_UNCOMPRESSED_DOCKER_SAVE',
                fixtureConfigAndDiffIdsVerified=True,engineSavedArchiveSha256=pin(saved_archive)['sha256'])
            engine.request('POST','/images/'+base+'/tag?repo='+repository+'&tag=protected')
            protected_before=engine.request('GET','/images/'+quote(protected,safe='')+'/json')['Id']
            assert protected_before==base
            engine.request('DELETE','/images/'+archived)
            assert all(row['Id'] != archived for row in engine.request('GET','/images/json?all=true'))
            restore=claim(fixture); directory=restore/'program-import'; directory.mkdir(mode=0o700)
            preparation=prepare_image_import(original_pin,dict(backend=program_id,frontend=program_id),directory,
                guard=guard,architecture='amd64',max_archive_bytes=1024**3,max_import_bytes=1024**3)
            plan=pinned_json(preparation)
            def load(path):
                raw=transfer('POST','/images/load?quiet=true',source=path)
                messages=[json.loads(line) for line in raw.splitlines() if line]
                assert messages and all('error' not in row and 'errorDetail' not in row for row in messages),messages
                return raw
            with locked(fixture) as descriptor:
                epoch=start(fixture,restore,descriptor)
                receipt=load_image_import(preparation,operation_id='restore-1',epoch_policy=fixture['epoch'],
                    lock_fd=descriptor,load=load,inspect_image=engine.image,guard=guard)
            imported=pinned_json(receipt)
            assert imported['state']=='LOADED' and imported['epoch']==epoch
            assert engine.image(program_id)['Id']==program_id
            protected_after=engine.request('GET','/images/'+quote(protected,safe='')+'/json')['Id']
            assert protected_after==protected_before==base
            running=engine.request('POST','/containers/create?name='+prefix+'-run',dict(
                Image=program_id,Labels=label,HostConfig=dict(NetworkMode='none')))
            created.append(running['Id'])
            engine.request('POST','/containers/'+running['Id']+'/start')
            while engine.inspect(running['Id'])['State']['Running']:
                guard(); time.sleep(0.05)
            assert engine.inspect(running['Id'])['State']['ExitCode']==0
            raw=transfer('GET','/containers/'+running['Id']+'/logs?stdout=true&stderr=true')
            assert b'archived-program-import-ok' in raw,raw
            assert pin(archive)==original_pin
            result.update(status='PASS',originalArchiveUnchanged=True,originalArchiveBytes=original_pin['bytes'],
                originalArchiveSha256=original_pin['sha256'],importBytes=plan['importPin']['bytes'],
                importSha256=plan['importPin']['sha256'],archivedImageId=program_id,
                archivedImageRecreatedAfterRemoval=True,existingTagPreserved=True,archivedProgramRan=True,
                imageRoles=['backend','frontend'],sharedImageConfigForRoles=True,realLinuxFlock=True,
                loadResultSha256=receipt['sha256'],nativeStdoutSha256=hashlib.sha256(raw).hexdigest())
    except BaseException as error:
        failure=error
        result.update(status='FAIL',failureCode=getattr(error,'code',type(error).__name__),failure=str(error))
    finally:
        # All names/IDs were created above and are recorded before each cleanup.
        # No broad label or image/container pruning is permitted.
        for identity in reversed(created):
            try: engine.request('DELETE','/containers/'+identity+'?force=true')
            except Exception as error: cleanup_errors.append(dict(kind='container',id=identity,error=str(error)))
        if tag_created:
            try: engine.request('DELETE','/images/'+quote(protected,safe=''))
            except Exception as error: cleanup_errors.append(dict(kind='tag',id=protected,error=str(error)))
        if archived is not None:
            try:
                rows=engine.request('GET','/images/json?all=true')
                owned={row['Id'] for row in rows if (row.get('Labels') or {}).get('spug.program.import')==prefix}
                if any(row['Id']==archived for row in rows):owned.add(archived)
                for identity in sorted(owned):engine.request('DELETE','/images/'+identity)
            except Exception as error: cleanup_errors.append(dict(kind='image',id=archived,error=str(error)))
        result.update(cleanupErrors=cleanup_errors,createdContainerIds=created,
            ownedContainersRemoved=not engine.request('GET','/containers/json?all=true&filters='+quote(json.dumps({'name':[prefix]}),safe='')),
            ownedTagsRemoved=not engine.request('GET','/images/json?filters='+quote(json.dumps({'reference':[repository+':*']}),safe='')),
            ownedImagesRemoved=not any((row.get('Labels') or {}).get('spug.program.import')==prefix
                for row in engine.request('GET','/images/json?all=true')))
        if cleanup_errors or not all(result[k] for k in ('ownedContainersRemoved','ownedTagsRemoved','ownedImagesRemoved')):result['status']='FAIL'
        (output/'native-report.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)
    if failure is not None:raise failure
    assert result['status']=='PASS',result


if __name__=='__main__':main()
