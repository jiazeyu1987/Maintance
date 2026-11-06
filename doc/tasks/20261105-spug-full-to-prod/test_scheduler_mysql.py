"""Exercise the lifecycle against an owned, disconnected real MySQL server."""
import datetime
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

from install_prod_control import PRIVATE,TASK
from test_storage_linux import DOCKER,ROOT

sys.path.insert(0,str(ROOT/'ops/recovery'))
sys.path.insert(0,str(PRIVATE/'local-win-test-deps'))
from recovery_mysql_scheduler import MainMysqlScheduler

NAME='spug-prod-main-scheduler-mysql-20261106'
LABEL='spug-full-to-prod-20261105'


def run(args,timeout=30):
    return subprocess.run([DOCKER,*args],capture_output=True,timeout=timeout)


if __name__=='__main__':
    identity=None;proof={};journal=PRIVATE/('scheduler-mysql-test-'+uuid.uuid4().hex)
    journal.mkdir(mode=0o700)
    try:
        image=run(['image','inspect','mysql:8.0.39']);assert image.returncode==0,'REAL_MYSQL_IMAGE_REQUIRED'
        image_id=json.loads(image.stdout)[0]['Id']
        assert run(['inspect',NAME]).returncode!=0,'OWNED_TEST_NAME_ALREADY_EXISTS'
        created=run(['run','-d','--rm','--name',NAME,'--label','codex.task='+LABEL,
            '--network','none','--memory','1g','--tmpfs','/var/lib/mysql:rw,size=512m',
            '-e','MYSQL_ALLOW_EMPTY_PASSWORD=yes',image_id,'--event-scheduler=ON'],timeout=45)
        assert created.returncode==0,'REAL_MYSQL_CREATE_FAILED'
        identity=created.stdout.decode().strip();print('Created isolated real MySQL test',flush=True)
        def query(statement,*,mutation=False):
            response=run(['exec',identity,'mysql','--no-defaults','--protocol=SOCKET','-uroot',
                '--batch','--skip-column-names','-e',statement])
            if response.returncode or response.stderr:
                (journal/'mysql-query-failure.private.log').write_bytes(response.stdout+response.stderr)
            assert response.returncode==0 and not response.stderr,'REAL_MYSQL_QUERY_FAILED'
            return response.stdout
        for attempt in range(90):
            response=run(['exec',identity,'mysqladmin','--no-defaults','--protocol=SOCKET','-uroot','ping'])
            executable=run(['exec',identity,'cat','/proc/1/comm'])
            (journal/'readiness.private.json').write_text(json.dumps(dict(pingExit=response.returncode,
                processExit=executable.returncode,process=executable.stdout.decode(errors='replace'),
                error=executable.stderr.decode(errors='replace'))),encoding='utf-8')
            if response.returncode==0 and executable.returncode==0 and executable.stdout.strip()==b'mysqld':break
            time.sleep(1)
        else:raise RuntimeError('REAL_MYSQL_START_TIMEOUT')
        query('CREATE DATABASE scheduler_case; CREATE TABLE scheduler_case.ticks (id INT AUTO_INCREMENT PRIMARY KEY);',mutation=True)
        database_uuid=query('SELECT @@server_uuid;').decode().strip()
        target=dict(database='scheduler_case',mainApplication={'schemaVersion':'RegisteredMainApplication/v2'},
            services=[dict(role='mysql',id=identity,imageId=image_id)],replacement=dict(databaseUuid=database_uuid))
        query('CREATE EVENT scheduler_case.original_event ON SCHEDULE EVERY 1 SECOND DO INSERT INTO scheduler_case.ticks VALUES ();',mutation=True)
        def count():return int(query('SELECT COUNT(*) FROM scheduler_case.ticks;'))
        for attempt in range(10):
            if count()>0:break
            time.sleep(1)
        else:raise RuntimeError('REAL_MYSQL_ENABLED_EVENT_NOT_RUNNING')
        first=MainMysqlScheduler(target,'real-operation',journal/'first',query)
        first.install();before=count();time.sleep(2);assert count()==before,'EVENT_RAN_WHILE_PAUSED'
        query('CREATE EVENT scheduler_case.imported_event ON SCHEDULE EVERY 1 SECOND DO INSERT INTO scheduler_case.ticks VALUES ();',mutation=True)
        first.verify();before=count();time.sleep(2);assert count()==before,'IMPORTED_EVENT_RAN_WHILE_PAUSED'
        custody=first.recovery_custody()
        second=MainMysqlScheduler(target,'real-retry',journal/'second',query,inherited=custody)
        second.install();second.verify();second.release()
        assert query('SELECT @@GLOBAL.event_scheduler;').strip()==b'ON'
        for attempt in range(10):
            if count()>before:break
            time.sleep(1)
        else:raise RuntimeError('REAL_MYSQL_ORIGINAL_STATE_NOT_RESTORED')
        query('SET GLOBAL event_scheduler=OFF;',mutation=True)
        third=MainMysqlScheduler(target,'real-original-off',journal/'third',query)
        third.install();third.release();assert query('SELECT @@GLOBAL.event_scheduler;').strip()==b'OFF'
        proof=dict(status='PASS',observedAt=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            containerId=identity,imageId=image_id,realMysql=True,network='none',publishedPorts=0,
            enabledOriginalEventPaused=True,enabledImportedEventPaused=True,
            failedOperationRemainedPaused=True,retryRestoredFirstOriginalOn=True,originalOffPreserved=True)
        print('Real scheduler pause, retained custody and exact release passed',flush=True)
    finally:
        if identity:
            inspected=run(['inspect',identity]);assert inspected.returncode==0,'OWNED_MYSQL_DISAPPEARED'
            row=json.loads(inspected.stdout)[0]
            assert row['Id']==identity and row['Name']=='/'+NAME and row['Config']['Labels']['codex.task']==LABEL
            assert row['HostConfig']['NetworkMode']=='none' and not row['HostConfig']['PortBindings'] and row['HostConfig']['AutoRemove']
            stopped=run(['stop','--time','10',identity],timeout=30);assert stopped.returncode==0,'OWNED_MYSQL_CLEANUP_FAILED'
            for attempt in range(15):
                if run(['inspect',identity]).returncode!=0:break
                time.sleep(1)
            else:raise RuntimeError('OWNED_MYSQL_NOT_REMOVED')
            if proof:proof['ownedContainerRemoved']=True
        if proof:
            (TASK/'real-mysql-scheduler-verification.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
            print(json.dumps(proof),flush=True)
