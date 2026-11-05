"""Explicit, append-only recovery of a terminated replacement failure.

This operator path never executes a restore or changes its historical result.
The next restore still requires a new request through the ordinary user flow.
"""
from datetime import datetime,timezone,timedelta
from pathlib import Path
import argparse
import json
import os
import re
import subprocess

from recovery_engine import absolute,canonical,digest,load,pin,pinned_json,require,utc


def append(path,value):
    with path.open('xb') as stream:
        os.chmod(path,0o600)
        stream.write(canonical(value));stream.flush();os.fsync(stream.fileno())
    if os.name=='posix':
        fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    return pin(path)


def validate_clearance(target,claim):
    path=claim/'recovery-clearance.json'
    if not path.exists():return None
    value=load(path)
    require(value.get('schemaVersion') in ('RetainedReplacementRecovery/v1','RetainedReplacementRecovery/v2') and
            value.get('operationId')==claim.name and bool(value.get('authorization')),
            'RECOVERY_CLEARANCE_INVALID')
    require(value.get('targetConfigurationSha256')==digest(target),'RECOVERY_CLEARANCE_TARGET_CHANGED')
    require(absolute(str(claim))==claim and claim.parent==absolute(target['replacement']['stateRoot']),
            'RECOVERY_CLEARANCE_PATH_CHANGED')
    ready=load(claim/'recovery-ready.json')
    require(ready['clearancePin']==pin(path),'RECOVERY_CLEARANCE_CHANGED')
    release=pinned_json(ready['releasePin'])
    require(release['clearancePin']==pin(path) and
            release['reason']=='EXPLICIT_RETAINED_REPLACEMENT_RECOVERY',
            'RECOVERY_CLEARANCE_RELEASE_NOT_PROVEN')
    if 'observationPin' in value:pinned_json(value['observationPin'])
    if 'reservationPin' in value:pinned_json(value['reservationPin'])
    request,result,exited,replacement=[pinned_json(value[k]) for k in
        ('requestPin','resultPin','exitPin','replacementResultPin')]
    original_root=Path(value['requestPin']['path']).parent
    require(original_root.name==claim.name and value['requestPin']['path']==str(original_root/'request.json') and
            value['resultPin']['path']==str(original_root/'worker-result.json') and
            value['exitPin']['path']==str(original_root/'child-exit.json'),
            'RECOVERY_CLEARANCE_ORIGINAL_CHANGED')
    if value['schemaVersion']=='RetainedReplacementRecovery/v2':
        require(value.get('failurePhase')=='BEFORE_MUTATION' and
                value['configurationPin']['path']==str(original_root/'configuration.json'),
                'RECOVERY_CLEARANCE_INVALID')
        configuration=pinned_json(value['configurationPin'])
        require(configuration['targets'][value['targetConfigRef']]==target,'RECOVERY_CLEARANCE_TARGET_CHANGED')
        verify_no_mutation(configuration,request,original_root,value,value['noMutationReleasePin'])
    require(value['replacementResultPin']['path']==str(claim/'replacement-result.json') and
            request['operationId']==result['operationId']==replacement['operationId']==claim.name and
            result['state']==replacement['state']=='FAILED_RETAINED' and result['actualExitCode']==1 and
            exited['actualExitCode']==1 and exited['timedOut'] is False and
            replacement['targetConfigRef']==value['targetConfigRef'] and
            all(request[k]==value[k] for k in ('sourceConfigRef','recoveryPointRef','targetConfigRef')),
            'RECOVERY_CLEARANCE_ORIGINAL_CHANGED')
    used=claim/'recovery-consumption.json'
    if used.exists():
        consumed=load(used)
        require(consumed['clearancePin']==pin(path),'RECOVERY_CLEARANCE_CHANGED')
        next_id=consumed['replacementOperationId']
        require(type(next_id) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,120}',next_id) and
                next_id!=claim.name and (claim.parent/next_id).is_dir(),
                'RECOVERY_CLEARANCE_CONSUMER_MISSING')
    else:
        require(datetime.now(timezone.utc)<datetime.fromisoformat(value['expiresAt'].replace('Z','+00:00')),
                'RECOVERY_CLEARANCE_EXPIRED')
    return value


def bind_clearances(target,request,*,consume):
    state=absolute(target['replacement']['stateRoot']);references=[]
    for claim in sorted(state.iterdir()):
        if not claim.is_dir():continue
        if (claim/'recovery-consumption.json').exists():
            validate_clearance(target,claim)
            continue
        value=validate_clearance(target,claim)
        if value is None:continue
        require(all(request[k]==value[k] for k in ('sourceConfigRef','recoveryPointRef','targetConfigRef')),
                'RECOVERY_CLEARANCE_REQUEST_CHANGED')
        if consume:
            require((state/request['operationId']).is_dir(),'RECOVERY_CLEARANCE_CONSUMER_MISSING')
            references.append(append(claim/'recovery-consumption.json',dict(
                schemaVersion='RetainedReplacementConsumption/v1',clearancePin=pin(claim/'recovery-clearance.json'),
                replacementOperationId=request['operationId'],consumedAt=utc())))
    return references


class ReadOnlyTarget:
    def __init__(self,configuration,request,root):
        self.config=configuration['targets'][request['targetConfigRef']]
        self.config_services={r['role']:r for r in self.config['services']}
        self.root=root;self.source=configuration['sources'][request['sourceConfigRef']]
        self.policy=self.config['dataPolicy'];self.snapshots={}
        self.db_container=self.config_services['mysql']['id']
        self.mysql_client_path=configuration['environmentMysqlClientPath']

    def docker(self,args):
        require(args and args[0] in ('info','inspect','ps','volume','network','exec'),
                'RECOVERY_OBSERVATION_WRITE_REJECTED')
        if args[0] in ('volume','network'):require(args[1]=='inspect','RECOVERY_OBSERVATION_WRITE_REJECTED')
        if args[0]=='exec':
            require(args[-2]=='-e' and args[-1] in ('SELECT @@server_uuid;',
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='"+self.config['database']+"';"),
                    'RECOVERY_OBSERVATION_WRITE_REJECTED')
        command=[self.config['dockerPin']['path'],'--host','unix:///var/run/docker.sock',*args]
        process=subprocess.run(command,input=getattr(self,'query_input',None),capture_output=True,timeout=30)
        require(process.returncode==0 and not process.stderr and len(process.stdout)<=64*1024*1024,
                'RECOVERY_OBSERVATION_FAILED')
        return process.stdout

    def inspect(self,identity):return json.loads(self.docker(['inspect',identity]))[0]

    def query(self,statement):
        from recovery_engine import check_pin
        secret=check_pin(self.config['secrets']['mysql']['MYSQL_ROOT_PASSWORD'])
        require(secret and not any(c in secret for c in (b'\r',b'\n',b'\0')),'SECRET_FORMAT_INVALID')
        script=('test -z "${MYSQL_TEST_LOGIN_FILE:-}"; test -n "${HOME:-}"; '
                'test ! -e "$HOME/.mylogin.cnf"; test ! -L "$HOME/.mylogin.cnf"; '
                'IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec "$@"')
        self.query_input=secret+b'\n'
        try:
            return self.docker(['exec','-i',self.db_container,'sh','-ec',script,'recovery-observation',
                self.mysql_client_path,'--no-defaults','--protocol=SOCKET','--host=localhost','--batch',
                '--skip-column-names','-e',statement]).decode().strip()
        finally:self.query_input=None

    def database_uuid(self):return self.query('SELECT @@server_uuid;')


def observe(configuration,request,root,expected_tables,running=False):
    from recovery_replace import verify_services
    from recovery_main_target import verify_runtime
    from recovery_engine import check_pin
    target=configuration['targets'][request['targetConfigRef']]
    check_pin(target['dockerPin'])
    native=ReadOnlyTarget(configuration,request,root)
    verify_services(native,target['replacement']);verify_runtime(native,states=False)
    rows={role:native.inspect(s['id']) for role,s in native.config_services.items()}
    require(all(row['State']['Running'] is (running or role in ('mysql','redis')) for role,row in rows.items()),
            'RECOVERY_TARGET_MUST_REMAIN_RUNNING' if running else 'RECOVERY_TARGET_MUST_REMAIN_QUIESCED')
    count=int(native.query("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='"+target['database']+"';"))
    require(count==expected_tables,'RECOVERY_TARGET_TABLE_COUNT_CHANGED')
    return dict(schemaVersion='RetainedReplacementObservation/v1',targetConfigRef=request['targetConfigRef'],
        databaseUuid=native.database_uuid(),tableCount=count,observedAt=utc(),
        services={role:dict(id=row['Id'],image=row['Image'],running=row['State']['Running'],
            startedAt=row['State']['StartedAt']) for role,row in rows.items()})


def verify_no_mutation(configuration,request,root,refs,release_ref):
    """Read the exact original no-mutation release; never release a pointer here."""
    from recovery_resource_admission import _binding
    from recovery_engine import check_pin
    require(release_ref['path']==str(root/'resource-no-mutation-release.json'),
            'RECOVERY_NO_MUTATION_NOT_PROVEN')
    release=pinned_json(release_ref)
    result,exited=pinned_json(refs['resultPin']),pinned_json(refs['exitPin'])
    reservation=pin(root/'resource-reservation.json');original=pinned_json(reservation)
    require(release.get('reason')=='PROVEN_NO_MUTATION' and
            release.get('reservationPin')==reservation and release.get('resultPin')==refs['resultPin'] and
            release.get('exitPin')==refs['exitPin'] and
            all(original.get(k)==v for k,v in _binding(configuration,request,root).items()) and
            result.get('operationId')==request['operationId'] and result.get('state')=='FAILED_RETAINED' and
            type(result.get('actualExitCode')) is int and result['actualExitCode']==1 and
            result.get('data',{}).get('mutationDispatched') is False and
            type(exited.get('actualExitCode')) is int and exited['actualExitCode']==1 and
            exited.get('timedOut') is False and
            not any(root.rglob('importer-*.json')) and
            not (root/'replacement-preparation/replacement-intent.json').exists(),
            'RECOVERY_NO_MUTATION_NOT_PROVEN')
    require(type(result.get('originalResultPins')) is list,'RECOVERY_NO_MUTATION_NOT_PROVEN')
    for reference in result['originalResultPins']:check_pin(reference)
    for path in root.rglob('native-*.json'):
        reference=pin(path);value=pinned_json(reference)
        require(reference in result['originalResultPins'] and value.get('mutation') is False and
                type(value.get('actualExitCode')) is int and value.get('finishedAt'),
                'RECOVERY_NO_MUTATION_NOT_PROVEN')
    return reservation


def authorize(configuration,request,root,authorization,expected_tables,*,no_mutation=False):
    """Append a narrowly bound clearance and release only its exact host pointer."""
    require(os.name=='posix' and type(authorization) is str and 10<=len(authorization)<=2000 and
            type(expected_tables) is int and expected_tables>=0 and type(no_mutation) is bool,
            'RECOVERY_AUTHORIZATION_REQUIRED')
    from recovery_resource_admission import _host_lock,_verify_reservation,_sync_host,HOST_ROOT
    from recovery_replace import validate
    import fcntl
    value=validate(configuration['targets'][request['targetConfigRef']])
    require(root==absolute(configuration['operationsRoot'])/request['operationId'],'RECOVERY_OPERATION_ROOT_CHANGED')
    request_ref=pin(root/'request.json');require(pinned_json(request_ref)==request,'RECOVERY_REQUEST_CHANGED')
    require(load(root/'configuration.json')==configuration,'RECOVERY_CONFIGURATION_CHANGED')
    claim=absolute(value['stateRoot'])/request['operationId']
    require(claim.is_dir() and not (claim/'recovery-clearance.json').exists(),'RECOVERY_CLEARANCE_ALREADY_EXISTS')
    refs=dict(requestPin=request_ref,resultPin=pin(root/'worker-result.json'),exitPin=pin(root/'child-exit.json'),
        replacementResultPin=pin(claim/'replacement-result.json'))
    result,exited,replacement=[pinned_json(refs[k]) for k in ('resultPin','exitPin','replacementResultPin')]
    require(result['operationId']==replacement['operationId']==request['operationId'] and
            result['state']==replacement['state']=='FAILED_RETAINED' and result['actualExitCode']==1 and
            exited['actualExitCode']==1 and exited['timedOut'] is False and
            result.get('data',{}).get('mutationDispatched') is (not no_mutation) and
            (no_mutation or (root/'replacement-preparation/replacement-intent.json').is_file()),
            'RECOVERY_ORIGINAL_NOT_TERMINATED_FAILURE')
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():continue
        try:command=(process/'cmdline').read_bytes()
        except OSError:continue
        require(not (request['operationId'].encode() in command and
            any(name in command for name in (b'recovery_minimal_worker.py',b'recovery_entry.py',
                                             b'recovery_control_smallapp.py\x00worker'))),
            'RECOVERY_ORIGINAL_PROCESS_RUNNING')
    fd=os.open(value['lockPath'],os.O_RDWR|os.O_NOFOLLOW)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with _host_lock():
            extra={}
            if no_mutation:
                require(not os.path.lexists(HOST_ROOT/'active.json'),'RECOVERY_HOST_RESERVATION_ACTIVE')
                release_ref=pin(root/'resource-no-mutation-release.json')
                reservation=verify_no_mutation(configuration,request,root,refs,release_ref);active=None
                extra=dict(failurePhase='BEFORE_MUTATION',noMutationReleasePin=release_ref,
                           configurationPin=pin(root/'configuration.json'))
                observation_value=observe(configuration,request,root,expected_tables,True)
            else:
                reservation,active=_verify_reservation(configuration,request,root)
                observation_value=observe(configuration,request,root,expected_tables)
            observation=append(claim/'recovery-observation.json',observation_value)
            clearance=append(claim/'recovery-clearance.json',dict(schemaVersion='RetainedReplacementRecovery/v2' if no_mutation else 'RetainedReplacementRecovery/v1',
                operationId=request['operationId'],sourceConfigRef=request['sourceConfigRef'],
                recoveryPointRef=request['recoveryPointRef'],targetConfigRef=request['targetConfigRef'],
                targetConfigurationSha256=digest(configuration['targets'][request['targetConfigRef']]),
                authorization=authorization,issuedAt=utc(),
                expiresAt=(datetime.now(timezone.utc)+timedelta(hours=24)).isoformat(),
                observationPin=observation,reservationPin=reservation,**refs,**extra))
            release=append(root/'resource-recovery-release.json',dict(
                schemaVersion='RetainedReplacementResourceRelease/v1',clearancePin=clearance,
                originalActive=active,releasedAt=utc(),reason='EXPLICIT_RETAINED_REPLACEMENT_RECOVERY'))
            if not no_mutation:
                require(load(HOST_ROOT/'active.json')==active,'RECOVERY_RESERVATION_CHANGED')
                (HOST_ROOT/'active.json').unlink()
                try:_sync_host()
                except Exception:
                    append(HOST_ROOT/'active.json',active)
                    raise
            append(claim/'recovery-ready.json',dict(clearancePin=clearance,releasePin=release,readyAt=utc()))
            return dict(clearancePin=clearance,releasePin=release,originalState='FAILED_RETAINED',
                        restoreDispatched=False,nextRequestMustUseSamePoint=True)
    finally:os.close(fd)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operation-root',required=True)
    parser.add_argument('--authorization',required=True)
    parser.add_argument('--expected-table-count',required=True,type=int)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--authorize-retained-replacement',action='store_true')
    mode.add_argument('--authorize-no-mutation-replacement',action='store_true')
    args=parser.parse_args();root=absolute(args.operation_root)
    print(json.dumps(authorize(load(root/'configuration.json'),load(root/'request.json'),root,
                               args.authorization,args.expected_table_count,
                               no_mutation=args.authorize_no_mutation_replacement)))


if __name__=='__main__':main()
