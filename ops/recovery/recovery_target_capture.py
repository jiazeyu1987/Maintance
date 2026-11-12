"""Same-process MAIN current-target capture under retained original custody.

This is an internal material entry, not an overwrite permission or a repository
publisher. A completed material session continues holding all writer barriers.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

from recovery_engine import RecoveryError, canonical, digest, pin, pinned_json, require, utc, write
from recovery_program_native import _NativeView
from recovery_program_protection import ProtectionCustody, _preservation_root
from recovery_program_execution import _directory
from minimal_capture_support import (Budget, Originals, actual_pin, exclusive_json,
    path_checked, source_config_redis, validate_config, validate_main_target_config, MinimalSemantic)


def _redis_authentication(target,redis):
    """Bind an already validated snapshot to the registered MAIN auth contract."""
    application=target.get('mainApplication')
    require(type(application) is dict and application.get('schemaVersion') in
        ('RegisteredMainApplication/v1','RegisteredMainApplication/v2'),
        'PROGRAM_CAPTURE_REDIS_AUTHENTICATION_INVALID')
    if application['schemaVersion']=='RegisteredMainApplication/v1':
        require('redisAuthentication' not in application,'PROGRAM_CAPTURE_REDIS_AUTHENTICATION_INVALID')
        mode='PASSWORD'
    else:
        authentication=application.get('redisAuthentication')
        require(type(authentication) is dict and (authentication==dict(mode='PASSWORD') or
            set(authentication)=={'mode','aclSha256'} and authentication['mode']=='NONE' and
            type(authentication['aclSha256']) is str and
            re.fullmatch('[0-9a-f]{64}',authentication['aclSha256']) is not None),
            'PROGRAM_CAPTURE_REDIS_AUTHENTICATION_INVALID')
        mode=authentication['mode']
    secrets=target.get('secrets',{})
    require(type(secrets) is dict and type(secrets.get('redis',{})) is dict and type(redis) is dict,
        'PROGRAM_CAPTURE_REDIS_CREDENTIAL_CHANGED')
    registered=secrets.get('redis',{})
    if mode=='PASSWORD':
        reference=registered.get('REDIS_PASSWORD')
        require(type(reference) is dict and 'passwordPin' in redis and redis['passwordPin']==reference,
            'PROGRAM_CAPTURE_REDIS_CREDENTIAL_CHANGED')
    else:
        require(not registered and 'passwordPin' not in redis,'PROGRAM_CAPTURE_REDIS_CREDENTIAL_CHANGED')


class _CaptureJournalLease:
    """Keep completed pins authoritative through overlapping kernel leases.

    Active intents retain their separate full-read check. No event is waived
    for a terminal rewrite: that path enters this set only after completion.
    A fault permanently removes admission, while later failure/exit records
    may still be retained as evidence without acquiring execution authority.
    """
    def __init__(self):
        self._guard=None;self._pins={};self._fault=None;self._closed=False

    def retain(self,reference):
        require(not self._closed,'PROGRAM_CAPTURE_JOURNAL_CLOSED')
        if self._fault is not None:return  # Evidence only after permanent failure.
        candidate=None
        try:
            require(reference['path'] not in self._pins,'PROGRAM_CAPTURE_JOURNAL_CHANGED')
            self.check(self._pins)
            pins={**self._pins,reference['path']:deepcopy(reference)}
            from recovery_archive_guard import ArchivePathGuard
            candidate=ArchivePathGuard.capture(pins)
            require(actual_pin(reference['path'])==reference,'PROGRAM_CAPTURE_JOURNAL_CHANGED')
            # The previous lease stays alive throughout setup and hashing.
            # Its queued changes cannot be discarded by the replacement set.
            self.check(self._pins);candidate.check()
            previous=self._guard;self._guard=candidate;candidate=None;self._pins=pins
            if previous is not None:previous.close()
        except BaseException as error:
            self._fault=error
            raise
        finally:
            if candidate is not None:candidate.close()

    def check(self,pins):
        require(not self._closed,'PROGRAM_CAPTURE_JOURNAL_CLOSED')
        if self._fault is not None:raise self._fault
        try:
            require(pins==self._pins,'PROGRAM_CAPTURE_JOURNAL_CHANGED')
            if self._guard is not None:self._guard.check()
        except BaseException as error:
            self._fault=error
            raise

    def close(self):
        self._closed=True
        if self._guard is not None:
            guard=self._guard;self._guard=None;guard.close()


class _CaptureProcessObserver:
    """Own actual stream children and the original context's exact intent token."""
    def __init__(self,session):
        self.session=session;self.active=None;self.sequence=0

    def before(self,argv):
        s=self.session
        require(self.active is None,'PROGRAM_CAPTURE_STREAM_ALREADY_ACTIVE')
        dumping=self._dump_command(argv)
        s.guard(force=dumping)
        self.sequence+=1
        path=s._journal/('stream-%05d.json'%self.sequence)
        value=dict(schemaVersion='RecoveryDataInvocation/v1',operationId=s._context._request['operationId'],
            action='RESTORE',argvSha256=digest(argv),mutation=False,startedAt=utc(),finishedAt=None,
            actualExitCode=None,state='TERMINAL_UNKNOWN')
        from recovery_program_activation import _exclusive
        reference=_exclusive(path,value,s._context._check)
        self.active=dict(path=path,value=value,intent_pin=reference,token=None,process=None,pid=os.getpid(),
            dump=dumping)
        self.active['token']=s._view.begin_invocation(s._native,reference)

    def _dump_command(self,argv):
        """Recognize only the formal original-container dump transport."""
        import re
        s=self.session
        return (type(argv) is list and len(argv)==19 and
            argv[:6]==['docker','exec','-i',s.source['mysqlContainerId'],'sh','-ec'] and
            type(argv[6]) is str and re.fullmatch(
                r'test -z "\$\{MYSQL_TEST_LOGIN_FILE:-\}"; test -n "\$\{HOME:-\}"; '
                r'test ! -e "\$HOME/\.mylogin\.cnf"; test ! -L "\$HOME/\.mylogin\.cnf"; '
                r'IFS= read -r MYSQL_PWD; export MYSQL_PWD; exec timeout --signal=TERM --kill-after=5 '
                r'[1-9][0-9]*s mysqldump "\$@"',argv[6]) is not None and
            argv[7:]==['formal-mysql','--no-defaults','--protocol=SOCKET','-uroot','--single-transaction',
                '--routines','--triggers','--events','--hex-blob','--set-gtid-purged=OFF',
                '--default-character-set=utf8mb4',s.source['database']])

    def started(self,process,argv):
        s=self.session;row=self.active
        require(row is not None and row['process'] is None and type(process) is subprocess.Popen and
            row['pid']==os.getpid() and digest(argv)==row['value']['argvSha256'],
            'PROGRAM_CAPTURE_EXPORT_OWNER_CHANGED')
        row['process']=process
        if row['dump']:
            require(s._lease is not None,'PROGRAM_CAPTURE_NOT_ACTIVE')
            s._lease._register_export(process)

    def finished(self,process):
        s=self.session;row=self.active
        require(row is not None and row['process'] is process and row['pid']==os.getpid() and
            process.poll() is not None,'PROGRAM_CAPTURE_EXPORT_TERMINAL_REQUIRED')
        row['value'].update(finishedAt=utc(),actualExitCode=process.returncode,
            state='SUCCEEDED' if process.returncode==0 else 'FAILED_RETAINED')
        reference=write(row['path'],row['value'])
        s._view.finish_invocation(row['token'],reference)
        self.active=None
        s._retain(reference)
        if row['dump']:s._lease._finish_export(process)
        s.guard(force=row['dump'])


class _MainCaptureBudget(Budget):
    def __init__(self,root,limits,context):
        super().__init__(root,limits)
        self._context=context;self.deadline=min(self.deadline,context.budget.deadline)

    def check(self):
        self._context.budget.remaining()
        super().check()


class MainTargetCapture:
    @classmethod
    def prepare(cls,native,*,capture_ref,reservation_pin):
        view=getattr(native,'native_context',None)
        require(type(view) is _NativeView,'PROGRAM_CAPTURE_VIEW_INVALID')
        view.guard_native(native)
        require(view.phase=='PREPARATION','PROGRAM_CAPTURE_PREPARATION_REQUIRED')
        custody=getattr(native,'protection_custody',None)
        require(type(custody) is ProtectionCustody and custody._context is view._context,
                'PROGRAM_CAPTURE_CUSTODY_REQUIRED')
        custody._validate(native)
        context=view._context
        policy=context._owner['targetProgramPolicies'][context._request['targetConfigRef']]
        captures=policy['captureConfigurationPins']
        require(type(capture_ref) is str and capture_ref in captures,'PROGRAM_CAPTURE_CONFIGURATION_UNREGISTERED')
        require(capture_ref in view.evidence['capturePins'],'PROGRAM_CAPTURE_CONFIGURATION_UNREGISTERED')
        from recovery_resource_admission import verify_reservation
        verified=verify_reservation(context._owner,context._request,context._root)
        require(reservation_pin==verified==view.evidence['reservationPin'],'PROGRAM_CAPTURE_RESERVATION_CHANGED')
        return cls._prepare(native,capture_ref,view.evidence['capturePins'][capture_ref],reservation_pin)

    @classmethod
    def _prepare(cls,native,capture_ref,capture_pin,reservation_pin):
        context=native.native_context._context
        require(getattr(context,'_target_capture_session',None) is None,'PROGRAM_CAPTURE_ALREADY_CLAIMED')
        config=pinned_json(capture_pin)
        if config.get('schemaVersion')=='MainTargetCaptureConfiguration/v1':validate_main_target_config(config)
        else:validate_config(config)
        cls._configuration(native,capture_ref,config)
        from recovery_replace import verify_services
        from recovery_main_target import application_runtime_inputs, verify_runtime
        verify_services(native,native.config['replacement']);verify_runtime(native,states=False)
        application_runtime_inputs(native)
        result=cls.__new__(cls)
        result._native,result._view,result._context=native,native.native_context,context
        result._custody=native.protection_custody
        result._capture_ref,result._capture_pin,result._reservation=capture_ref,deepcopy(capture_pin),deepcopy(reservation_pin)
        result.config,result.source=deepcopy(config),deepcopy(config['source'])
        result._raw=canonical(config);result._closed=False;result._state='PREPARING';result._pins={}
        result._lease=None;result._capturing=False;result._guard_depth=0;result._guard_export_process=None
        result._last_check=0;result._read_hashes=set()
        result._material=None;result._unknown=False;result._failure_code=None
        result._parent=_preservation_root(context)
        result._journal=result._parent/'session';result._journal.mkdir(mode=0o700)
        result.root=result._parent/'capture';result.root.mkdir(mode=0o700)
        result._identities={path:_directory(path,'PROGRAM_CAPTURE_DIRECTORY_CHANGED')
            for path in (result._parent,result._journal,result.root)}
        result._journal_lease=_CaptureJournalLease()
        result.budget=_MainCaptureBudget(result.root,config['limits'],context)
        result.limits=result.config['limits'];result.runtime=result
        result.worker=__import__('minimal_capture_worker')
        result.phase='CONFIGURATION_ADMISSION';result.events=0;result.minio_stopped=False
        result._observer=_CaptureProcessObserver(result)
        context._target_capture_session=result
        try:
            result.originals=Originals(result.budget.check)
            result.originals.document(capture_pin)
            for tool in config['tools'].values():result.originals.read(actual_pin(tool))
            result._admit_resources()
            result._record('intent.json',dict(schemaVersion='MainTargetCaptureIntent/v1',operationId=context._request['operationId'],
                targetConfigRef=context._request['targetConfigRef'],captureRef=capture_ref,configurationPin=capture_pin,
                originalTargetPin=context._evidence['targetPin'],executionBindingPin=context._binding,
                resourceAdmissionPin=reservation_pin,captureRoot=str(result.root),startedAt=utc()))
            from recovery_capture_materials import prepare_materials
            identity=dict(schemaVersion='MainTargetCaptureIdentity/v1',operationId=context._request['operationId'],
                action='FULL',parent=None,targetConfigRef=context._request['targetConfigRef'])
            from formal_snapshot_linux import observation_deadline
            token=observation_deadline.set(result.budget.deadline)
            try:
                with result.budget.activate():
                    result._prepared=prepare_materials(config,identity,result.root,output_budget=result.budget,
                        originals=result.originals,transport=result)
            finally:observation_deadline.reset(token)
            result._state='PREPARED';result.check()
            return result
        except BaseException as error:
            try:result._fail(error)
            finally:result.close()
            raise

    @staticmethod
    def _configuration(native,capture_ref,config):
        target=native.config;source=config['source'];context=native.native_context._context
        services=native.config_services;epoch=context._policy['backupEpochPolicy']
        require(config['sourceConfigRef']==capture_ref and config['parent'] is None and
            config['sourceLockPath']==epoch['sourceLockPath'],
            'PROGRAM_CAPTURE_CONFIGURATION_SCOPE_CHANGED')
        if config.get('schemaVersion')=='MainTargetCaptureConfiguration/v1':
            require(config.get('outputRootPolicy')=='CURRENT_OPERATION_TARGET_PRESERVATION_CAPTURE' and
                'archiveRoot' not in config,'PROGRAM_CAPTURE_CONFIGURATION_SCOPE_CHANGED')
        else:
            require(config.get('schemaVersion')=='minimal-source-capture-config/v1' and
                config['archiveRoot'] in native.source['archiveRoots'],'PROGRAM_CAPTURE_CONFIGURATION_SCOPE_CHANGED')
        require(source['sourceIdentity']==source['sourceFingerprint']==epoch['sourceIdentity'] and
            source['databaseUuid']==epoch['databaseUuid']==target['replacement']['databaseUuid'] and
            source['database']==target['database'] and source['mysqlContainerId']==services['mysql']['id'] and
            source['minioContainerId']==services['minio']['id'] and
            set(source['writerContainerIds'])=={services[r]['id'] for r in ('backend','frontend')} and
            set(source['applicationImageIds'])=={s['imageId'] for s in services.values()} and
            source['passwordPin']==target['secrets']['mysql']['MYSQL_ROOT_PASSWORD'],
            'PROGRAM_CAPTURE_CONFIGURATION_SCOPE_CHANGED')
        mounts=[m for m in target['replacement']['services']['minio']['mounts'] if
            m['Destination']==source['minioMountDestination'] and m['RW'] is True and m['Source']==source['minioDataPath']]
        require(len(mounts)==1,'PROGRAM_CAPTURE_CONFIGURATION_SCOPE_CHANGED')
        from recovery_replacement_storage import overlaps
        output=context._root/'target-preservation'
        forbidden=[*target['dataPaths'],target['dataRoot'],target['replacement']['stateRoot'],epoch['root'],
            *native.source['archiveRoots'],*(m['Source'] for row in target['replacement']['services'].values() for m in row['mounts'])]
        require(all(not overlaps(str(output),path) for path in forbidden),'PROGRAM_CAPTURE_OUTPUT_OVERLAP')
        require(not os.environ.get('DOCKER_CONTEXT') and not os.environ.get('DOCKER_TLS_VERIFY') and
            os.environ.get('DOCKER_HOST','unix:///var/run/docker.sock') in ('','unix:///var/run/docker.sock'),
            'MINIMAL_LOCAL_DOCKER_REQUIRED')
        for name,value in config['tools'].items():
            tool=path_checked(value)
            require(tool.name==name and tool.is_file() and os.access(tool,os.X_OK) and
                shutil.which(name) is not None and Path(shutil.which(name)).resolve()==tool,'MINIMAL_TOOL_SELECTION_CHANGED')
        require(pin(config['tools']['docker'])==target['dockerPin'],'PROGRAM_CAPTURE_TOOL_CHANGED')
        require({canonical(row['reference']) for row in source['configurationPins']}==
            {canonical(p) for p in target['mainApplication']['configurationPins']},'PROGRAM_CAPTURE_CONFIGURATION_SCOPE_CHANGED')
        descriptor=pinned_json(source['objectSourcePin'])
        require(descriptor['sourceIdentity']==source['sourceIdentity'] and descriptor['minioContainerId']==services['minio']['id'] and
            descriptor['endpoint']=='http://'+services['minio']['ip']+':9000' and
            set(descriptor['buckets'])==set(target['buckets']) and descriptor['parentExportIndexPin'] is None,
            'PROGRAM_CAPTURE_OBJECT_SCOPE_CHANGED')
        credentials=pinned_json(descriptor['credentialReference'])
        for key,environment in (('accessKey','MINIO_ROOT_USER'),('secretKey','MINIO_ROOT_PASSWORD')):
            reference=target.get('secrets',{}).get('minio',{}).get(environment)
            require(reference is not None,'PROGRAM_CAPTURE_OBJECT_CREDENTIAL_REQUIRED')
            from formal_capture_recovery_inputs import original_bytes
            require(original_bytes(reference,limit=16384).decode('utf-8')==credentials[key],
                'PROGRAM_CAPTURE_OBJECT_CREDENTIAL_CHANGED')
        versions=descriptor['versionPins']
        material=[row['reference'] for row in source['materialPins']]
        require(versions and all(reference in material for reference in versions),'PROGRAM_CAPTURE_VERSION_CHANGED')
        image_set={s['role']:s['imageId'] for s in services.values()}
        require(any(pinned_json(reference).get('images')==image_set for reference in versions),'PROGRAM_CAPTURE_VERSION_CHANGED')
        redis=source_config_redis(source)
        require(redis['containerId']==services['redis']['id'] and redis['host']==services['redis']['ip'] and
            redis['database']==target['redisRebuild']['database'],'PROGRAM_CAPTURE_REDIS_SCOPE_CHANGED')
        _redis_authentication(target,redis)

    @property
    def handed_off(self):return self._state=='HANDED_OFF'

    def _admit_resources(self):
        from recovery_resource_admission import (observe_resources,check_budget,verify_reservation,
            configured_budget,enforce_disk_capacity,ResourceAdmissionError)
        c=self._context
        require(verify_reservation(c._owner,c._request,c._root)==self._reservation,'PROGRAM_CAPTURE_RESERVATION_CHANGED')
        policy=configured_budget(c._owner,c._request);observed=observe_resources(c._owner,c._request,policy)
        check_budget(policy,observed)
        device=self.root.stat().st_dev
        same=[r for r in observed['disks'] if r['device']==device]
        required=sum(policy['diskBytesByPath'][r['path']] for r in same)+self.budget.maximum+self.budget.reserve
        free=min([shutil.disk_usage(self.root).free,*[r['freeBytes'] for r in same]])
        try:
            decision=enforce_disk_capacity(policy,required,free,'PROGRAM_CAPTURE_DISK_SPACE_INSUFFICIENT',
                minimum_free_bytes=self.budget.reserve)
        except ResourceAdmissionError as error:
            if error.code=='PROGRAM_CAPTURE_DISK_SPACE_INSUFFICIENT':
                raise RecoveryError(error.code) from error
            raise
        record=dict(schemaVersion='MainTargetCaptureResourceAdmission/v1',
            operationId=c._request['operationId'],reservationPin=self._reservation,device=device,requiredBytes=required,
            freeBytes=free,admitted=True,businessAcceptance='NOT_PERFORMED')
        if policy['schemaVersion']=='RestoreResourceBudget/v2':
            record.update(schemaVersion='MainTargetCaptureResourceAdmission/v2',
                diskAdmissionMode=decision['diskAdmissionMode'],
                forecastReservationsEnforced=decision['forecastReservationsEnforced'],minimumFreeBytes=self.budget.reserve)
        self._record('resource-admission.json',record)

    def _record(self,name,value):
        reference=exclusive_json(self._journal/name,value)
        self._retain(reference)
        return reference

    def _retain(self,reference):
        # Record the actual published bytes/exit before validating admission.
        # A lost lease must never discard a dispatched child's terminal proof.
        self._pins[reference['path']]=reference
        self._native.original_pins.append(deepcopy(reference))
        self._journal_lease.retain(reference)

    def check(self):
        require(not self._closed,'PROGRAM_CAPTURE_CLOSED')
        require(self._state!='FAILED_RETAINED','PROGRAM_CAPTURE_FAILED_RETAINED')
        require(self._context._target_capture_session is self and self._view._context is self._context and
            self._native.protection_custody is self._custody,'PROGRAM_CAPTURE_OWNER_CHANGED')
        require(canonical(self.config)==self._raw and self.source==self.config['source'],'PROGRAM_CAPTURE_CONFIGURATION_CHANGED')
        for path,identity in self._identities.items():
            require(_directory(path,'PROGRAM_CAPTURE_DIRECTORY_CHANGED')==identity,'PROGRAM_CAPTURE_DIRECTORY_CHANGED')
        expected={Path(path).name for path in self._pins}
        if self._observer.active is not None:
            row=self._observer.active;expected.add(row['path'].name)
            require(actual_pin(row['path'])==row['intent_pin'],'PROGRAM_CAPTURE_JOURNAL_CHANGED')
        require({p.name for p in self._journal.iterdir()}==expected,'PROGRAM_CAPTURE_JOURNAL_CHANGED')
        self._journal_lease.check(self._pins)

    def guard(self,*,force=False):
        self.check();self.budget.check();self._view.guard_native(self._native);self._custody._validate(self._native)
        row=self._observer.active;export=None
        if row is not None and row['process'] is not None:
            if row['dump']:
                require(self._lease is not None and self._lease._process is row['process'],
                    'PROGRAM_CAPTURE_EXPORT_OWNER_CHANGED')
                if self._lease._export_state()!='RUNNING':return
                export=row['process']
            elif row['process'].poll() is not None:return
            # An already exited child gets local checks only until the original
            # drain's finished callback fixes its token and checks strict trx==0.
        if not force and time.monotonic()-self._last_check<.5:return
        from recovery_main_target import application_runtime_inputs,verify_runtime,verify_writer_quiescence
        from recovery_replace import verify_services
        before=len(self._context._invocations);self._guard_depth+=1
        self._guard_export_process=export
        try:
            verify_services(self._native,self._native.config['replacement'])
            verify_runtime(self._native,states=self._capturing)
            application_runtime_inputs(self._native)
            if self._capturing:
                verify_writer_quiescence(self._native)
                if self._lease is not None:self._lease.verify()
                else:
                    view=self._custody.view_for(self._native)
                    for item in (view.archive,view.fence,view.scheduler):item.verify()
            self.originals.current()
        finally:
            self._guard_export_process=None;self._guard_depth-=1
        # These exact successful, same-owner guard observations form a finite
        # read-only whitelist. It is frozen before a child is admitted, never
        # enlarged while an exporter has an outstanding intent.
        if self._observer.active is None:
            rows=self._context._invocations[before:]
            require(all(not row['intentObservation']['mutation'] and row['terminalPin'] is not None and
                row['terminalObservation']['state']=='SUCCEEDED' for row in rows),'PROGRAM_CAPTURE_GUARD_INVOCATION_INVALID')
            self._read_hashes={row['intentObservation']['argvSha256'] for row in rows}
        self._last_check=time.monotonic()

    protected=guard

    def _allows_guard_invocation(self,view,value,pending):
        row=self._observer.active
        return (view is self._view and view._context is self._context and self._state=='CAPTURING' and
            self._guard_depth==1 and row is not None and row['dump'] and row['pid']==os.getpid() and
            row['process'] is not None and type(row['process']) is subprocess.Popen and
            self._guard_export_process is row['process'] and self._lease is not None and
            self._lease._process is row['process'] and self._lease._export_state() in ('RUNNING','EXITED_UNREAPED') and
            pending==[row['token']] and
            value.get('schemaVersion')=='RecoveryDataInvocation/v1' and value.get('mutation') is False and
            value.get('action')=='RESTORE' and value.get('argvSha256') in self._read_hashes)

    def event(self,stage,**data):
        self.events+=1
        return self._record('event-%04d.json'%self.events,dict(at=utc(),stage=stage,**data))

    def _mysql(self,source,limits):
        from formal_snapshot_linux import PrivateDockerMySql
        from formal_data_evidence import DataMySql
        password=self.originals.read(source['passwordPin'],16384).decode('utf-8').removesuffix('\n')
        return (PrivateDockerMySql(source['mysqlContainerId'],password,timeout=limits['querySeconds'],process_observer=self._observer),
            DataMySql(source['mysqlContainerId'],password,timeout=limits['querySeconds'],process_observer=self._observer))

    def _semantic(self,series,originals,descriptor,source):
        return MinimalSemantic(series,originals,descriptor,source,process_observer=self._observer)

    def _save_images(self,path,images,budget):
        from recovery_capture_materials import save_application_images
        save_application_images(path,images,budget,process_observer=self._observer)

    def _verify_objects(self,semantic):
        self.worker.verify_objects_after_offline(semantic,self,process_observer=self._observer)

    def _minio(self,running):
        self.guard(force=True)
        identity=self.source['minioContainerId']
        require(self._native.storage_running is not running,'PROGRAM_CAPTURE_STORAGE_STATE_CHANGED')
        self._native.docker(['start' if running else 'stop',identity],mutation=True)
        observed=self._native.inspect(identity)
        require(observed['State']['Running'] is running and not observed['State']['Paused'] and
            not observed['State']['Restarting'],'PROGRAM_CAPTURE_STORAGE_TERMINAL_REQUIRED')
        self._native.storage_running=running;self.minio_stopped=not running
        self.guard(force=True)

    def command(self,arguments):
        require(arguments==['start','--',self.source['minioContainerId']],'PROGRAM_CAPTURE_COMMAND_REFUSED')
        self._minio(True);return b''

    def stop(self,container):
        require(container==self.source['minioContainerId'],'PROGRAM_CAPTURE_COMMAND_REFUSED')
        self._minio(False)

    def capture(self):
        require(self._state=='PREPARED','PROGRAM_CAPTURE_ALREADY_USED')
        self._capturing=True
        try:
            self.guard(force=True)
            require(not self._native.storage_running and not self._native.running_applications,
                'PROGRAM_CAPTURE_WRITERS_NOT_STOPPED')
            self._lease=self._custody.capture_view_for(self._native);self._lease.begin()
            self._state='CAPTURING';self.minio_stopped=True
            self._minio(True);self.worker.wait_ready(self._prepared.semantic,self)
            from recovery_capture_materials import capture_protected_materials
            from formal_snapshot_linux import observation_deadline
            token=observation_deadline.set(self.budget.deadline)
            try:
                with self.budget.activate():self._material=capture_protected_materials(self._prepared,self)
            finally:observation_deadline.reset(token)
            self._minio(False);self.guard(force=True)
            self._record('materials.json',dict(schemaVersion='MainTargetCaptureMaterials/v1',
                operationId=self._context._request['operationId'],intentPin=self._pins[str(self._journal/'intent.json')],
                materials=self._material.result,writersRemainQuiesced=True,sourceRestored=False,finishedAt=utc()))
            self._state='MATERIAL_COMPLETE'
            return self._material
        except BaseException as error:
            self._fail(error);raise

    def _fail(self,error):
        self._state='FAILED_RETAINED';self._failure_code=getattr(error,'code',type(error).__name__)
        proof=self._context.snapshot()
        self._unknown=bool(getattr(error,'unknown',False) or getattr(error,'clientCleanupUncertain',False) or proof['terminalUnknown'])
        self._record('failure.json',dict(schemaVersion='MainTargetCaptureFailure/v1',
            operationId=self._context._request['operationId'],phase=self.phase,failureCode=self._failure_code,
            mutationDispatched=proof['mutationDispatched'],terminalUnknown=self._unknown,
            originalResultPins=deepcopy(list(self._pins.values())),sourceRestored=False,finishedAt=utc()))

    def snapshot(self):
        native=self._context.snapshot()
        return dict(schemaVersion='MainTargetCapture/v1',operationId=self._context._request['operationId'],
            state=self._state,configurationPin=deepcopy(self._capture_pin),reservationPin=deepcopy(self._reservation),
            sourceRestored=False,writersRemainQuiesced=self._state=='MATERIAL_COMPLETE',
            mutationDispatched=native['mutationDispatched'],terminalUnknown=self._unknown or native['terminalUnknown'],
            originalResultPins=deepcopy(list(self._pins.values())),failureCode=self._failure_code,
            materials=None if self._material is None else self._material.result)

    def handoff(self,verified_preservation):
        from recovery_target_preservation import _HandoffArchive
        require(type(verified_preservation) is _HandoffArchive and
            verified_preservation._publication is getattr(self._context,'_target_preservation',None) and
            verified_preservation._publication.session is self and
            verified_preservation._publication._handoff_archive is verified_preservation,
            'PROGRAM_CAPTURE_PRESERVATION_REQUIRED')
        require(self._state=='MATERIAL_COMPLETE' and self._observer.active is None,
            'PROGRAM_CAPTURE_HANDOFF_STATE_INVALID')
        self.guard(force=True)
        evidence=self._context.snapshot()
        require(not evidence['terminalUnknown'] and all(row['terminalPin'] is not None and
            row['terminalObservation']['state']=='SUCCEEDED' for row in evidence['invocations']),
            'PROGRAM_CAPTURE_HANDOFF_UNSETTLED')
        require(not self._native.storage_running and not self._native.running_applications,
            'PROGRAM_CAPTURE_WRITERS_NOT_STOPPED')
        intent=self._record('handoff-intent.json',dict(schemaVersion='MainTargetPreservationHandoffIntent/v1',
            operationId=self._context._request['operationId'],targetConfigRef=self._context._request['targetConfigRef'],
            bindingPin=self._context._binding,archiveProofPin=verified_preservation.archive_pin,
            captureSessionPin=self._pins[str(self._journal/'intent.json')],
            originalFlags=[1,1],restoreFlags=[0,0],createdAt=utc()))
        self._state='HANDOFF_IN_PROGRESS'
        try:
            self._lease.handoff(verified_preservation)
            from recovery_main_target import verify_writer_quiescence,verify_runtime
            from recovery_replace import verify_services
            verify_services(self._native,self._native.config['replacement'])
            verify_runtime(self._native,states=True);verify_writer_quiescence(self._native)
            self._lease._external_protections()
            reference=self._record('handoff.json',dict(schemaVersion='MainTargetPreservationHandoff/v1',
                state='SUCCEEDED',operationId=self._context._request['operationId'],
                targetConfigRef=self._context._request['targetConfigRef'],intentPin=intent,
                archiveProofPin=verified_preservation.archive_pin,
                originalResultPins=deepcopy(self._context.snapshot()['originalResultPins']),finishedAt=utc()))
            self._state='HANDED_OFF'
            return reference
        except BaseException as error:
            self._fail(error);raise

    def close(self):
        self._closed=True
        self._journal_lease.close()
