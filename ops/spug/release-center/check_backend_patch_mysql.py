"""Explicit local MySQL integration. Creates/removes only its own isolated fixture.

Run manually; no server credentials, exposed ports, business DB or persistent volume.
"""
import json
from pathlib import Path
import subprocess
import tempfile
import time
import uuid

from backend_patch_agent import acquire_fence,release_fence


def run(args,*,data=None,check=True):
    value=subprocess.run(args,input=data,capture_output=True,timeout=90)
    if check and value.returncode:raise RuntimeError('Local integration command failed: '+args[0])
    return value


class Mysql:
    def __init__(self,name):self.name=name
    def inspect(self,name):return json.loads(run(['docker','inspect',name]).stdout)[0]
    def sql(self,profile,query):
        return run(['docker','exec','-i',self.name,'mysql','-h127.0.0.1','-uroot','--batch','--skip-column-names'],data=query.encode()).stdout.decode().strip()


def main():
    name='spug-backend-patch-check-'+uuid.uuid4().hex[:12]
    created=run(['docker','create','--network','none','--label','spug.task=backend-patch-local-check',
                 '--tmpfs','/var/lib/mysql:rw,size=1g','-e','MYSQL_ALLOW_EMPTY_PASSWORD=yes','--name',name,'mysql:8.0.39']).stdout.decode().strip()
    try:
        run(['docker','start',created]);remote=Mysql(name);profile={'database':name}
        deadline=time.monotonic()+90
        while True:
            ready=run(['docker','exec',name,'mysql','-h127.0.0.1','-uroot','-NBe','SELECT 1;'],check=False)
            if ready.returncode==0:break
            if time.monotonic()>deadline:raise RuntimeError('Local MySQL did not start')
            time.sleep(1)
        remote.sql(profile,'CREATE DATABASE patch_contract; CREATE TABLE patch_contract.example(id INT PRIMARY KEY,value VARCHAR(40)); INSERT INTO patch_contract.example VALUES(1,"original");')
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);acquire_fence(profile,root,remote)
            for query in ['UPDATE patch_contract.example SET value="unexpected";',
                          'CREATE TABLE patch_contract.forbidden(id INT);']:
                result=run(['docker','exec','-i',name,'mysql','-h127.0.0.1','-uroot'],data=query.encode(),check=False)
                assert result.returncode!=0 and b'1290' in result.stderr,'MySQL must refuse root DML and DDL during startup'
            assert remote.sql(profile,'SELECT value FROM patch_contract.example;')=='original'
            assert remote.sql(profile,'SHOW TABLES FROM patch_contract;')=='example'
            try:acquire_fence(profile,Path(temporary)/'another',remote)
            except ValueError:pass
            else:raise AssertionError('External fence must not be adopted')
            release_fence(profile,root,remote)
            assert remote.sql(profile,'SELECT @@global.read_only,@@global.super_read_only;')=='0\t0'
            remote.sql(profile,'UPDATE patch_contract.example SET value="normal-business-write";')
        print(json.dumps(dict(status='passed',mysql='8.0.39',rootDmlRejected=True,rootDdlRejected=True,
                              originalRowsUnchanged=True,externalFencePreserved=True,ownedFenceReleased=True,
                              remoteServersAccessed=0)))
    finally:
        actual=json.loads(run(['docker','inspect',created]).stdout)[0]
        assert actual['Config']['Labels']['spug.task']=='backend-patch-local-check'
        run(['docker','rm','-f',created])


if __name__=='__main__':main()
