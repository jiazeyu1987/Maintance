"""Finite five-entry host control; no production CLI or host-drain attestation.

systemctl effects and journal completion are separate. Uncertain intents are
retained and never replayed. Only this task's exact runtime mask is removed.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import time

import formal_boot_state as boot
import formal_original_launch as launch
import formal_snapshot_linux as snapshot
from formal_filesystem_watchdog import require_native_runtime
from formal_s3_export import _strict_json
from formal_snapshot_linux import FormalSnapshotError,require

CLOSE_ORDER=('crond.service','dnf-makecache.timer','systemd-tmpfiles-clean.timer',
             'unbound-anchor.timer','cockpit.socket')
RESTORE_ORDER=(CLOSE_ORDER[1],CLOSE_ORDER[2],CLOSE_ORDER[3],CLOSE_ORDER[0],CLOSE_ORDER[4])
ASSOCIATED=('dnf-makecache.service','systemd-tmpfiles-clean.service','unbound-anchor.service','cockpit.service')
UNIT_FIELDS={'loadState','active','sub','mainPid','controlPid','unitFileState','configurationSha256',
             'configurationFiles','loadedConfigurationPaths','linksSha256','stopContractSha256','timerSemanticsSha256',
             'originalMasked','mask','persistentMask'}
PROPERTIES=('Id','Names','LoadState','ActiveState','SubState','UnitFileState','FragmentPath','DropInPaths',
    'MainPID','ControlPID','Job','KillMode','KillSignal','SendSIGKILL','TimeoutStopUSec',
    'Triggers','TriggeredBy','PartOf','BindsTo','Conflicts','Before','After','PropagatesStopTo',
    'Persistent','AccuracyUSec','RandomizedDelayUSec')
UNIT_FILE_STATES=('enabled','enabled-runtime','static','disabled','masked','masked-runtime')


def _manager_file_state(properties,method_state,original,mask,persistent):
    """Validate every show value; permit only the retained pre-reload object."""
    property_state=properties['UnitFileState']
    _need(property_state in UNIT_FILE_STATES and method_state in UNIT_FILE_STATES,'PROPERTY_UNSUPPORTED')
    if property_state==method_state:return
    loaded=[p for p in (properties['FragmentPath'],*properties['DropInPaths'].split()) if p]
    _need(original is not None and not original['originalMasked'] and mask is not None and
        persistent is None and method_state=='masked-runtime' and
        property_state==original['unitFileState'] and property_state not in ('masked','masked-runtime') and
        properties['LoadState']==original['loadState']=='loaded' and
        loaded==original['loadedConfigurationPaths'],'ORIGINAL_MANAGER_FILE_STATE_CHANGED')


def _closed_manager(current):
    _need((current['mask'] is not None or current['persistentMask'] is not None) and
        current['loadState']=='masked' and current['unitFileState']==
        ('masked' if current['persistentMask'] is not None else 'masked-runtime'),'CLOSED_ENTRY_CHANGED')


def _sha(value):return hashlib.sha256(value).hexdigest()
def _digest(value):return _sha(snapshot._canonical_bytes(value))
def _need(ok,code):require(ok,'FORMAL_HOST_'+code)
def _step(unit,suffix):return 'host-'+unit.rsplit('.',1)[0]+suffix
def _event(claim,name):return next((e['details'] for e in claim.events if e['step']==name),None)


def _typed_schedule(raw,calendar):
    try:fields=shlex.split(raw.decode('utf-8',errors='strict'))
    except (ValueError,UnicodeError):raise FormalSnapshotError('FORMAL_HOST_TIMER_PROPERTY_INVALID') from None
    signature='a(sst)' if calendar else 'a(stt)'
    _need(len(fields)>=2 and fields[0]==signature and fields[1].isdigit(),'TIMER_PROPERTY_INVALID')
    count=int(fields[1]);_need(0<=count<=32 and len(fields)==2+3*count,'TIMER_PROPERTY_INVALID')
    allowed={'OnCalendar'} if calendar else {'OnActiveUSec','OnBootUSec','OnStartupUSec','OnUnitActiveUSec','OnUnitInactiveUSec'}
    result=[]
    for index in range(count):
        base,value,next_elapse=fields[2+3*index:5+3*index]
        _need(base in allowed and next_elapse.isdigit() and int(next_elapse)<2**64,'TIMER_PROPERTY_UNSUPPORTED')
        _need(bool(value) and (calendar or value.isdigit() and int(value)<2**64),'TIMER_PROPERTY_INVALID')
        result.append([base,value])
    return result


class NativeHostAdmission:
    """Native manager transport and exact mask ownership; no alternate backend.

    runtime_directory only permits a root-trusted Linux test fixture. There is
    no user-supplied command, unit, environment, shell, PID kill or job cancel.
    """
    def __init__(self,*,runtime_directory=Path('/run/systemd/system'),persistent_directory=Path('/etc/systemd/system')):
        self.runtime=boot._absolute(str(runtime_directory))
        self.persistent=boot._absolute(str(persistent_directory))

    def _run(self,args,deadline,limit=1048576):
        try:return launch._bounded_command(['/usr/bin/systemctl',*args],deadline=deadline,limit=limit)
        except launch.LaunchObservationError:
            raise FormalSnapshotError('FORMAL_HOST_SYSTEMCTL_EFFECT_UNCERTAIN') from None

    def capabilities(self,deadline):
        version=self._run(['--version'],deadline,16384);help_text=self._run(['--help'],deadline,65536)
        _need(re.match(rb'systemd [0-9]+\b',version) is not None and
            all(v in help_text for v in (b'--runtime',b'--no-block',b'--job-mode',b'--quiet',
                                        b'mask',b'stop',b'start',b'daemon-reload')),'SYSTEMCTL_CAPABILITY_UNSUPPORTED')
        bus_version=self._bus_run(['--version'],deadline,16384);bus_help=self._bus_run(['--help'],deadline,65536)
        _need(bus_version==version and b'get-property' in bus_help and b'call' in bus_help and b'--system' in bus_help,
              'BUSCTL_CAPABILITY_UNSUPPORTED')
        raw=Path('/etc/machine-id').read_bytes()
        _need(re.fullmatch(rb'[0-9a-f]{32}\n?',raw) is not None,'MACHINE_ID_INVALID')
        return {'bootId':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                'machineIdSha256':_sha(raw),'systemctlSha256':_digest([version.hex(),help_text.hex(),bus_version.hex(),bus_help.hex()])}

    def _bus_run(self,args,deadline,limit=65536):
        try:return launch._bounded_command(['/usr/bin/busctl',*args],deadline=deadline,limit=limit)
        except launch.LaunchObservationError:
            raise FormalSnapshotError('FORMAL_HOST_BUS_PROPERTY_UNAVAILABLE') from None

    def _bus_property(self,unit,interface,name,deadline):
        _need(unit in CLOSE_ORDER and (interface,name) in (
            ('Service','ExecStop'),('Service','ExecStopPost'),('Timer','TimersCalendar'),('Timer','TimersMonotonic')),
            'BUS_PROPERTY_INVALID')
        encoded=''.join(c if c.isascii() and c.isalnum() else '_%02x'%ord(c) for c in unit)
        return self._bus_run(['--system','--no-pager','get-property','org.freedesktop.systemd1',
            '/org/freedesktop/systemd1/unit/'+encoded,'org.freedesktop.systemd1.'+interface,name],deadline)

    def observe_related_work(self,binding,expected_sha256,*,guard,deadline,
                             proc_directory=Path('/proc'),require_idle=False,allow_bound_process_absence=False):
        """Finite fixed-unit source observation; never a complete writer fence.

        The explicit binding must come from this operation's prior observation.
        proc_directory permits only a root-trusted native test fixture; there
        is no CLI override, version probing, action or process termination.
        """
        from formal_host_derived_work import observe_related_work
        return observe_related_work(self,binding,expected_sha256,guard=guard,
            deadline=deadline,proc_directory=proc_directory,require_idle=require_idle,
            allow_bound_process_absence=allow_bound_process_absence)

    def observe_related_work_native(self,binding,expected_sha256,*,deadline,
                                    proc_directory=Path('/proc'),require_idle=True,allow_bound_process_absence=False):
        from formal_host_derived_work import observe_related_work_native
        return observe_related_work_native(self,binding,expected_sha256,deadline=deadline,
            proc_directory=proc_directory,require_idle=require_idle,allow_bound_process_absence=allow_bound_process_absence)

    def _unit_file_state(self,unit,deadline):
        _need(unit in CLOSE_ORDER,'UNIT_INVALID')
        raw=self._bus_run(['--system','--no-pager','call','org.freedesktop.systemd1',
            '/org/freedesktop/systemd1','org.freedesktop.systemd1.Manager','GetUnitFileState','s',unit],deadline)
        value=re.fullmatch(rb's "(enabled|enabled-runtime|static|disabled|masked|masked-runtime)"\n',raw)
        _need(value is not None,'UNIT_FILE_STATE_UNSUPPORTED')
        return value.group(1).decode('ascii')

    @staticmethod
    def _link_at(directory,name):
        try:info=os.stat(name,dir_fd=directory,follow_symlinks=False)
        except FileNotFoundError:return None
        _need(stat.S_ISLNK(info.st_mode) and info.st_uid==0 and info.st_nlink==1,'RUNTIME_UNIT_CONFLICT')
        target=os.readlink(name,dir_fd=directory)
        _need(target=='/dev/null','RUNTIME_UNIT_CONFLICT')
        return {'target':target,'signature':list(boot._signature(info))}

    def mask_identity(self,unit):
        _need(unit in CLOSE_ORDER,'UNIT_INVALID')
        with boot._directory(self.runtime) as (directory,identity):
            result=self._link_at(directory,unit)
            boot._directory_unchanged(self.runtime,identity)
            _need(result==self._link_at(directory,unit),'MASK_OWNERSHIP_UNPROVEN')
            return result

    def persistent_mask_identity(self,unit):
        _need(unit in CLOSE_ORDER,'UNIT_INVALID')
        with boot._directory(self.persistent) as (directory,identity):
            result=self._link_at(directory,unit)
            boot._directory_unchanged(self.persistent,identity)
            _need(result==self._link_at(directory,unit),'MASK_OWNERSHIP_UNPROVEN')
            return result

    def remove_owned_mask(self,unit,expected):
        _need(unit in CLOSE_ORDER and type(expected) is dict,'MASK_OWNERSHIP_UNPROVEN')
        with boot._directory(self.runtime) as (directory,identity):
            _need(self._link_at(directory,unit)==expected,'MASK_OWNERSHIP_UNPROVEN')
            boot._directory_unchanged(self.runtime,identity)
            # Only the exact task-created runtime link; no manager-wide unmask.
            os.unlink(unit,dir_fd=directory);os.fsync(directory)
            _need(self._link_at(directory,unit) is None,'MASK_REMOVAL_UNCERTAIN')
            boot._directory_unchanged(self.runtime,identity)

    def create_owned_mask(self,unit):
        _need(unit in CLOSE_ORDER,'UNIT_INVALID')
        with boot._directory(self.runtime) as (directory,identity):
            _need(self._link_at(directory,unit) is None,'RUNTIME_UNIT_CONFLICT')
            boot._directory_unchanged(self.runtime,identity)
            try:os.symlink('/dev/null',unit,dir_fd=directory)
            except FileExistsError:raise FormalSnapshotError('FORMAL_HOST_RUNTIME_UNIT_CONFLICT') from None
            os.fsync(directory);result=self._link_at(directory,unit)
            _need(result is not None,'MASK_OWNERSHIP_UNPROVEN')
            boot._directory_unchanged(self.runtime,identity)
            return result

    def command(self,action,unit,deadline):
        _need(action in ('stop','start','reload') and
            (unit in CLOSE_ORDER if action!='reload' else unit is None),'COMMAND_INVALID')
        args=['--quiet','daemon-reload'] if action=='reload' else ['--quiet','--no-block','--job-mode=fail',action,'--',unit]
        _need(self._run(args,deadline,16384)==b'','SYSTEMCTL_EFFECT_UNCERTAIN')

    def _links(self,unit):
        values=[]
        for directory_path in (self.runtime,self.persistent):
            with boot._directory(directory_path) as (directory,identity):
                entries=os.listdir(directory);_need(len(entries)<=512,'LINK_INVENTORY_LIMIT')
                for name in sorted(entries):
                    if name==unit:continue  # masks are separately pinned.
                    info=os.stat(name,dir_fd=directory,follow_symlinks=False)
                    if not stat.S_ISDIR(info.st_mode) or not name.endswith(('.wants','.requires')):continue
                    child=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=directory)
                    try:
                        links=os.listdir(child);_need(len(links)<=512,'LINK_INVENTORY_LIMIT')
                        if unit not in links:continue
                        link=os.stat(unit,dir_fd=child,follow_symlinks=False)
                        _need(stat.S_ISLNK(link.st_mode) and link.st_uid==0,'ENABLEMENT_CHANGED')
                        values.append([str(directory_path/name/unit),os.readlink(unit,dir_fd=child),list(boot._signature(link))])
                    finally:os.close(child)
                boot._directory_unchanged(directory_path,identity)
        return _digest(values)

    @staticmethod
    def _configuration(paths):
        result=[]
        for path in paths:
            selected=boot._absolute(path)
            _need(str(selected).startswith(('/usr/lib/systemd/system/','/etc/systemd/system/','/run/systemd/system/')),
                  'CONFIGURATION_PATH_INVALID')
            with boot._directory(selected.parent,no_atime=True) as (directory,identity):
                info=os.stat(selected.name,dir_fd=directory,follow_symlinks=False)
                _need(stat.S_ISREG(info.st_mode) and info.st_uid==0 and not info.st_mode&0o022,'CONFIGURATION_UNTRUSTED')
                raw,signature=boot._read_at(directory,selected.name,stat.S_IMODE(info.st_mode),1048576,no_atime=True)
                result.append({'path':path,'sha256':_sha(raw),'signature':list(signature)})
                boot._directory_unchanged(selected.parent,identity)
        return result

    @staticmethod
    def _configuration_signatures(files):
        for value in files:
            selected=boot._absolute(value['path'])
            with boot._directory(selected.parent,no_atime=True) as (directory,identity):
                info=os.stat(selected.name,dir_fd=directory,follow_symlinks=False)
                _need(stat.S_ISREG(info.st_mode) and list(boot._signature(info))==value['signature'],
                      'CONFIGURATION_CHANGED')
                boot._directory_unchanged(selected.parent,identity)
        return files

    def observe(self,unit,deadline,original=None,*,signatures_only=False):
        _need(unit in CLOSE_ORDER,'UNIT_INVALID')
        raw=self._run(['show','--no-pager','--property='+','.join(PROPERTIES),'--',unit],deadline,65536)
        properties={}
        try:
            for line in raw.decode('utf-8',errors='strict').splitlines():
                k,v=line.split('=',1);_need(k in PROPERTIES and k not in properties,'PROPERTY_INVALID');properties[k]=v
        except (UnicodeError,ValueError):raise FormalSnapshotError('FORMAL_HOST_PROPERTY_INVALID') from None
        mask=self.mask_identity(unit)
        with boot._directory(self.persistent) as (directory,_):persistent=self._link_at(directory,unit)
        needed={'Id','Names','LoadState','ActiveState','SubState','UnitFileState','FragmentPath','DropInPaths','Job'}
        if unit=='crond.service':needed|={'MainPID','ControlPID'}
        if unit=='crond.service' and not (mask or persistent):
            needed|={'MainPID','ControlPID','KillMode','KillSignal','SendSIGKILL','TimeoutStopUSec'}
        if unit.endswith('.timer') and not (mask or persistent):
            needed|={'Persistent','AccuracyUSec','RandomizedDelayUSec','Triggers'}
        _need(needed<=properties.keys() and properties['Id']==unit and properties['Names'].split()==[unit],
              'PROPERTY_UNSUPPORTED')
        unit_file_state=self._unit_file_state(unit,deadline)
        _manager_file_state(properties,unit_file_state,original,mask,persistent)
        _need(properties['Job'] in ('','0'),'SYSTEMD_EFFECT_PENDING')
        jobs=self._run(['list-jobs','--no-legend','--no-pager'],deadline,65536).decode('utf-8',errors='strict')
        for line in jobs.splitlines():
            fields=line.split()
            _need(len(fields)==4 and fields[0].isdigit() and int(fields[0])>0 and
                re.fullmatch('[A-Za-z0-9_.@:-]+',fields[1]) is not None and
                re.fullmatch('[a-z-]+',fields[2]) is not None and fields[3] in ('waiting','running'),'JOB_INVALID')
            _need(fields[1] not in CLOSE_ORDER+ASSOCIATED,'SYSTEMD_EFFECT_PENDING')
        loaded_paths=[p for p in (properties['FragmentPath'],*properties['DropInPaths'].split()) if p]
        paths=[p for p in loaded_paths if p!='/dev/null']
        if original is not None:paths=[f['path'] for f in original['configurationFiles']]
        _need(not signatures_only or original is not None,'CONFIGURATION_REQUIRED')
        files=self._configuration_signatures(original['configurationFiles']) if signatures_only else self._configuration(paths)
        stop={k:properties.get(k) for k in ('KillMode','KillSignal','SendSIGKILL','TimeoutStopUSec','ExecStop','ExecStopPost',
                                          'PartOf','BindsTo','Conflicts','PropagatesStopTo')}
        closed_masked=bool(mask or persistent) and properties['ActiveState']=='inactive' and \
            properties['SubState']=='dead' and properties.get('MainPID')=='0' and properties.get('ControlPID')=='0'
        if unit=='crond.service' and not closed_masked:
            for name in ('ExecStop','ExecStopPost'):
                # Typed primary source always; omitted show keys are never defaults.
                value=self._bus_property(unit,'Service',name,deadline)
                _need(value==b'a(sasbttttuii) 0\n','CRON_STOP_CONTRACT_UNSUPPORTED')
                stop[name]=[]
        if original is None and unit=='crond.service' and not (mask or persistent):
            _need(stop['KillMode']=='process' and not stop['ExecStop'] and not stop['ExecStopPost'],
                  'CRON_STOP_CONTRACT_UNSUPPORTED')
        if unit=='crond.service' and not closed_masked and (properties['ActiveState']!='inactive' or
                original is not None and original['active']=='active'):
            # Hashing an unsafe original strategy does not make it nonforced.
            # No host policy mutation or alternate kill route is permitted.
            _need(stop['KillSignal']=='15' and stop['SendSIGKILL']=='no' and
                stop['TimeoutStopUSec']=='infinity', 'CRON_CONTROLLED_STOP_UNSAFE')
        timer={k:properties.get(k) for k in ('Persistent','AccuracyUSec','RandomizedDelayUSec','Triggers')}
        if unit.endswith('.timer'):
            if not (mask or persistent) or original is not None and not original['originalMasked']:
                timer['calendar']=_typed_schedule(self._bus_property(unit,'Timer','TimersCalendar',deadline),True)
                timer['monotonic']=_typed_schedule(self._bus_property(unit,'Timer','TimersMonotonic',deadline),False)
            else:timer.update(calendar=None,monotonic=None)
        try:main=int(properties.get('MainPID','0'));control=int(properties.get('ControlPID','0'))
        except ValueError:raise FormalSnapshotError('FORMAL_HOST_PROPERTY_INVALID') from None
        result=dict(loadState=properties['LoadState'],active=properties['ActiveState'],sub=properties['SubState'],mainPid=main,controlPid=control,
            unitFileState=unit_file_state,configurationSha256=_digest(files),configurationFiles=files,
            loadedConfigurationPaths=loaded_paths,
            linksSha256=self._links(unit),stopContractSha256=_digest(stop),
            timerSemanticsSha256=_digest(timer) if unit.endswith('.timer') else None,
            originalMasked=mask is not None or persistent is not None,mask=mask,persistentMask=persistent)
        _need(time.monotonic()<deadline,'DEADLINE')
        return result


def _validate(plan):
    _need(type(plan) is dict and set(plan)=={'schemaVersion','host','units'} and
        plan['schemaVersion']=='formal-host-admission-plan/v1' and type(plan['host']) is dict and
        set(plan['host'])=={'bootId','machineIdSha256','systemctlSha256'} and type(plan['units']) is dict and
        set(plan['units'])==set(CLOSE_ORDER),'PLAN_INVALID')
    _need(re.fullmatch(r'[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}',plan['host']['bootId']) is not None and
        all(type(plan['host'][k]) is str and re.fullmatch('[0-9a-f]{64}',plan['host'][k])
            for k in ('machineIdSha256','systemctlSha256')),'PLAN_INVALID')
    for unit,v in plan['units'].items():
        _need(type(v) is dict and set(v)==UNIT_FIELDS|{'stopApproved','timerResumeApproved'} and
            type(v['stopApproved']) is bool and v['stopApproved'] and type(v['timerResumeApproved']) is bool and
            type(v['originalMasked']) is bool and type(v['mainPid']) is int and v['mainPid']>=0 and
            type(v['controlPid']) is int and v['controlPid']==0 and type(v['configurationFiles']) is list and
            len(v['configurationFiles'])<=32 and type(v['loadedConfigurationPaths']) is list and
            len(v['loadedConfigurationPaths'])<=33 and all(type(p) is str for p in v['loadedConfigurationPaths']) and
            v['active'] in ('active','inactive') and
            v['unitFileState'] in ('enabled','enabled-runtime','static','disabled','masked','masked-runtime'), 'PLAN_INVALID')
        _need(not (v['active']=='active' and v['originalMasked']),'ORIGINAL_ACTIVE_MASKED_NOT_RESTORABLE')
        _need(v['originalMasked']==(v['mask'] is not None or v['persistentMask'] is not None),'PLAN_INVALID')
        if v['originalMasked']:
            _need(v['loadState']=='masked' and v['loadedConfigurationPaths'][:1]==['/dev/null'] and
                v['unitFileState']==('masked' if v['persistentMask'] is not None else 'masked-runtime'),
                'ORIGINAL_MANAGER_MASK_NOT_LOADED')
        else:
            _need(v['loadState']=='loaded' and v['unitFileState'] not in ('masked','masked-runtime'),
                  'ORIGINAL_MANAGER_STATE_UNSUPPORTED')
        _need(v['sub']==('dead' if v['active']=='inactive' else 'running' if unit=='crond.service' else
                        'listening' if unit=='cockpit.socket' else 'waiting'),'ORIGINAL_STATE_UNSUPPORTED')
        _need(v['active']!='inactive' or v['mainPid']==0,'ORIGINAL_STATE_UNSUPPORTED')
        _need(all(type(v[k]) is str and re.fullmatch('[0-9a-f]{64}',v[k]) for k in
            ('configurationSha256','linksSha256','stopContractSha256')) and
            (type(v['timerSemanticsSha256']) is str and re.fullmatch('[0-9a-f]{64}',v['timerSemanticsSha256'])
             if unit.endswith('.timer') else v['timerSemanticsSha256'] is None),'PLAN_INVALID')


def _checked(claim,native,host,guard,deadline):
    _need(callable(guard),'MUTATION_GUARD_REQUIRED');snapshot.observation_timeout(1)
    claim.assert_owned();guard();claim.assert_owned()
    _need(native.capabilities(deadline)==host,'ORIGINAL_BINDING_CHANGED')
    _need(time.monotonic()<deadline,'DEADLINE')


def _bound(claim):
    claim.assert_owned();bound=_event(claim,'host-originals-bound');_need(bound is not None,'ORIGINALS_REQUIRED')
    raw,signature=boot._read_secure(claim.root/'host-originals.json',0o600,65536,no_atime=True)
    _need(_sha(raw)==bound['sha256'] and list(signature)==bound['signature'],'ORIGINAL_BINDING_CHANGED')
    plan=_strict_json(raw);_validate(plan)
    return plan


def _source(observed,original):
    _need(all(observed[k]==original[k] for k in ('configurationSha256','configurationFiles','linksSha256','persistentMask')),
          'ORIGINAL_BINDING_CHANGED')
    loaded=observed['loadedConfigurationPaths']
    _need((loaded==original['loadedConfigurationPaths'] and observed['loadState']==original['loadState']) or
          (loaded==['/dev/null',*original['loadedConfigurationPaths'][1:]] and observed['loadState']=='masked' and
           (observed['mask'] is not None or observed['persistentMask'] is not None)),
          'LOADED_CONFIGURATION_CHANGED')


def _deadline(timeout):
    _need(type(timeout) is int and 1<=timeout<=300,'DEADLINE_INVALID')
    return time.monotonic()+snapshot.observation_timeout(timeout)


def _private_tail(claim,plan,deadline):
    # No external callback after the last native observation.
    _need(_bound(claim)==plan,'ORIGINAL_BINDING_CHANGED');claim.assert_owned()
    _need(time.monotonic()<deadline,'DEADLINE')


def _prefix(claim,plan,native,units,deadline,restored=False):
    for unit in units:
        original=plan['units'][unit];current=native.observe(unit,deadline,original);_source(current,original)
        if restored:
            _need(all(current[k]==original[k] for k in ('loadState','mask','persistentMask','active','sub','unitFileState',
                'stopContractSha256','timerSemanticsSha256')) and current['controlPid']==0 and
                (original['active']=='active' or current['mainPid']==0),'PREVIOUS_ENTRY_CHANGED')
        else:
            _closed_manager(current)
            completed=_event(claim,_step(unit,'-closed'))
            _need(completed is not None and current['mask']==(completed['ownedMask'] or original['mask']) and
                current['active']=='inactive' and current['sub']=='dead' and current['mainPid']==0 and
                current['controlPid']==0,'PREVIOUS_ENTRY_CHANGED')


def _wait(claim,plan,native,unit,original,deadline,check,active):
    while True:
        check()
        try:
            current=native.observe(unit,deadline,original);_source(current,original)
            if current['active']==active and current['controlPid']==0 and (active=='active' or current['mainPid']==0):
                return current
        except FormalSnapshotError as exc:
            if exc.code!='FORMAL_HOST_SYSTEMD_EFFECT_PENDING':raise
        _need(time.monotonic()<deadline,'SYSTEMD_EFFECT_PENDING')
        time.sleep(min(0.05,max(0,deadline-time.monotonic())))


def bind_host_originals(claim,plan,expected_sha256,*,guard,native=None,timeout=60):
    require_native_runtime();_need(os.geteuid()==0,'ROOT_REQUIRED')
    raw=snapshot._canonical_bytes(plan);plan=_strict_json(raw);_validate(plan)
    _need(len(raw)<=65536 and _sha(raw)==expected_sha256,'PLAN_CHANGED')
    _need(_event(claim,'host-originals-bound') is None and not (claim.root/'host-originals.json').exists(),'ACTION_ALREADY_STARTED')
    deadline=_deadline(timeout);native=NativeHostAdmission() if native is None else native
    _checked(claim,native,plan['host'],guard,deadline)
    for unit in CLOSE_ORDER:
        current=native.observe(unit,deadline)
        _need(current=={k:plan['units'][unit][k] for k in UNIT_FIELDS},'ORIGINAL_BINDING_CHANGED')
    _checked(claim,native,plan['host'],guard,deadline)
    # Re-observe after callbacks; approval is a detached immutable byte snapshot.
    for unit in CLOSE_ORDER:
        _need(native.observe(unit,deadline)=={k:plan['units'][unit][k] for k in UNIT_FIELDS},'ORIGINAL_BINDING_CHANGED')
    claim._write(claim.root/'host-originals.json',raw)
    saved,signature=boot._read_secure(claim.root/'host-originals.json',0o600,65536,no_atime=True)
    _need(saved==raw and time.monotonic()<deadline,'PLAN_CHANGED')
    claim.record('host-originals-bound',{'sha256':_sha(raw),'signature':list(signature)})
    _private_tail(claim,plan,deadline)
    return _result('HOST_ORIGINALS_BOUND')


def _result(state):return dict(state=state,fullHostFence=False,fullDrain=False,productionEvidence=False,releaseReady=False)


def _derived_bound(claim):
    """Consume only this claim's pre-close observation; never learn new sources."""
    from formal_host_derived_work import _validate as validate_derived
    claim.assert_owned();event=_event(claim,'host-derived-originals-bound')
    _need(type(event) is dict and set(event)=={'sha256','signature'},'DERIVED_ORIGINALS_REQUIRED')
    positions={e['step']:e['sequence'] for e in claim.events}
    derived_position=positions['host-derived-originals-bound']
    _need(positions.get('host-originals-bound',derived_position)>=0 and
        positions.get('host-originals-bound',derived_position)<derived_position and
        all(e['sequence']>derived_position for e in claim.events if e['step'].startswith('host-') and
            e['step'] not in ('host-originals-bound','host-derived-originals-bound')),'DERIVED_BINDING_TOO_LATE')
    raw,signature=boot._read_secure(claim.root/'host-derived-originals.json',0o600,65536,no_atime=True)
    _need(_sha(raw)==event['sha256'] and list(signature)==event['signature'],'DERIVED_ORIGINAL_BINDING_CHANGED')
    original=_strict_json(raw)
    _need(type(original) is dict and set(original)=={'schemaVersion','hostOriginalsSha256',
        'binding','bindingSha256','observationSha256'} and original['schemaVersion']=='formal-host-derived-originals/v1',
        'DERIVED_ORIGINAL_BINDING_CHANGED')
    host_bound=_event(claim,'host-originals-bound');plan=_bound(claim)
    _need(original['hostOriginalsSha256']==host_bound['sha256'] and
        original['binding']['bootId']==plan['host']['bootId'] and type(original['observationSha256']) is str and
        re.fullmatch('[0-9a-f]{64}',original['observationSha256']),'DERIVED_ORIGINAL_BINDING_CHANGED')
    validate_derived(original['binding'],original['bindingSha256'])
    return original,(raw,signature)


def bind_host_derived_sources(claim,binding,expected_sha256,*,guard,native=None,timeout=60,approved_request=None):
    """Seal actual fixed-unit identities before any mask/stop in this claim."""
    from formal_host_derived_work import _validate as validate_derived
    require_native_runtime();_need(os.geteuid()==0,'ROOT_REQUIRED')
    deadline=_deadline(timeout);plan=_bound(claim)
    _need(_event(claim,'host-derived-originals-bound') is None and
        not (claim.root/'host-derived-originals.json').exists(),'DERIVED_ACTION_ALREADY_STARTED')
    _need(not any(e['step'].startswith('host-') and e['step']!='host-originals-bound' for e in claim.events),
        'DERIVED_BINDING_TOO_LATE')
    raw=snapshot._canonical_bytes(binding);binding=_strict_json(raw)
    validate_derived(binding,expected_sha256)
    _need(binding['bootId']==plan['host']['bootId'],'DERIVED_BOOT_CHANGED')
    native=NativeHostAdmission() if native is None else native
    _checked(claim,native,plan['host'],guard,deadline)
    observed=native.observe_related_work(binding,expected_sha256,guard=guard,deadline=deadline,require_idle=False)
    known=sorted(binding['knownProcesses'],key=lambda row:row['pid'])
    actual=[{'pid':row['pid'],'startTicks':row['startTicks']} for row in observed['processes']]
    _need(known==actual,'DERIVED_KNOWN_SET_CHANGED')
    _need(observed['units']['crond.service']['MainPID']==plan['units']['crond.service']['mainPid'] and
        observed['units']['crond.service']['ControlPID']==plan['units']['crond.service']['controlPid'],
        'DERIVED_ORIGINAL_PROCESS_CHANGED')
    # Finish approval/content callbacks before the no-callback native tail.
    guard();claim.assert_owned()
    _need(snapshot._canonical_bytes(binding)==raw and _bound(claim)==plan,'DERIVED_BINDING_CHANGED')
    claim.assert_owned();_need(time.monotonic()<deadline,'DEADLINE')
    # Every owner callback has completed. Do not accept a source learned after
    # a callback began closing any host entry.
    _need(not any(e['step'].startswith('host-') and e['step']!='host-originals-bound' for e in claim.events),
        'DERIVED_BINDING_TOO_LATE')
    last=native.observe_related_work_native(binding,expected_sha256,deadline=deadline,require_idle=False)
    _need(last==observed,'DERIVED_SOURCE_CHANGED')
    def request_signature():
        if approved_request is None:return
        path,signature=approved_request
        _need(boot._signature(os.stat(path,follow_symlinks=False))==signature and
            signature[0]==claim.root.stat().st_dev,'DERIVED_REQUEST_CHANGED')
    request_signature();claim.assert_owned();_need(time.monotonic()<deadline,'DEADLINE')
    original=dict(schemaVersion='formal-host-derived-originals/v1',hostOriginalsSha256=
        _event(claim,'host-originals-bound')['sha256'],binding=binding,bindingSha256=expected_sha256,
        observationSha256=_digest(observed))
    saved=snapshot._canonical_bytes(original);_need(len(saved)<=65536,'DERIVED_SOURCE_LIMIT')
    path=claim.root/'host-derived-originals.json';claim._write(path,saved)
    pair=boot._read_secure(path,0o600,65536,no_atime=True)
    _need(pair[0]==saved and time.monotonic()<deadline,'DERIVED_BINDING_CHANGED')
    request_signature()
    claim.record('host-derived-originals-bound',{'sha256':_sha(saved),'signature':list(pair[1])})
    _derived_bound(claim);_need(time.monotonic()<deadline,'DEADLINE')
    return _result('HOST_DERIVED_ORIGINALS_BOUND_ONLY')


class ClosedHostAdmissionChecks:
    """Repeated actual five-entry checks; no whole-host or derived drain proof.

    Native injection is only a protocol test boundary. Production selects the
    same fixed systemd transport. No action, journal growth or reconciliation.
    """
    def __init__(self,claim,*,native=None,controlled_stop=False):
        require_native_runtime();_need(os.geteuid()==0 and type(claim) is snapshot.FormalMaintenanceClaim,'INPUT_INVALID')
        _need(type(controlled_stop) is bool,'INPUT_INVALID');self._controlled_stop=controlled_stop
        self.claim=claim;self.plan=_bound(claim)
        self.native=NativeHostAdmission() if native is None else native
        self.derived,self.derived_pair=_derived_bound(claim)
        self.initial=_strict_json(snapshot._canonical_bytes(claim.events));self.pins={}
        _need(all(_event(claim,_step(u,'-closed')) is not None for u in CLOSE_ORDER),'ALL_ENTRIES_CLOSED_REQUIRED')
        for unit in CLOSE_ORDER:
            original=self.plan['units'][unit];completed=_event(claim,_step(unit,'-closed'))
            _need(type(completed) is dict and set(completed)=={'originalSha256','ownedMask'} and
                completed['originalSha256']==_digest(original) and
                (completed['ownedMask'] is None if original['originalMasked'] else type(completed['ownedMask']) is dict),
                'CLOSED_BINDING_CHANGED')
        for event in claim.events:
            if not event['step'].startswith('host-'):continue
            path=claim.root/('event-%06d.json'%event['sequence'])
            pair=boot._read_secure(path,0o600,16384,no_atime=True)
            _need(pair[0]==snapshot._canonical_bytes(event),'CLOSED_BINDING_CHANGED');self.pins[path]=pair
        path=claim.root/'host-originals.json'
        self.pins[path]=boot._read_secure(path,0o600,65536,no_atime=True)
        self.pins[claim.root/'host-derived-originals.json']=self.derived_pair
        with boot._directory(claim.root,no_atime=True) as (_,self.root_identity):pass
        self.lock=boot._signature(os.fstat(claim._fd));self._private()

    def _private(self):
        claim=self.claim;claim.assert_owned()
        _need(snapshot._canonical_bytes(claim.events[:len(self.initial)])==
            snapshot._canonical_bytes(self.initial),'CLOSED_BINDING_CHANGED')
        _need(not any('-restore-' in e['step'] and e['step'].startswith('host-') or
            e['step'] in ('released','failed-retained') for e in claim.events),'CLOSED_STAGE_INVALID')
        _need(not any(e['step'].startswith('host-') for e in claim.events[len(self.initial):]),'CLOSED_STAGE_INVALID')
        for path,pair in self.pins.items():
            derived=path.name=='host-derived-originals.json'
            _need(boot._read_secure(path,0o600,65536 if path.name in ('host-originals.json','host-derived-originals.json') else 16384,no_atime=True)==pair,
                  'DERIVED_ORIGINAL_BINDING_CHANGED' if derived else 'CLOSED_BINDING_CHANGED')
        self.event_names={'event-%06d.json'%event['sequence'] for event in claim.events}
        self._signatures()

    def _signatures(self):
        for unit in CLOSE_ORDER:
            original=self.plan['units'][unit];completed=_event(self.claim,_step(unit,'-closed'))
            self.native._configuration_signatures(original['configurationFiles'])
            _need(self.native.mask_identity(unit)==(completed['ownedMask'] or original['mask']) and
                self.native.persistent_mask_identity(unit)==original['persistentMask'],'CLOSED_MASK_CHANGED')
        for path,pair in self.pins.items():
            _need(boot._signature(os.stat(path,follow_symlinks=False))==pair[1],
                'DERIVED_ORIGINAL_BINDING_CHANGED' if path.name=='host-derived-originals.json' else 'CLOSED_BINDING_CHANGED')
        with boot._directory(self.claim.root,no_atime=True) as (directory,identity):
            _need(identity==self.root_identity and {n for n in os.listdir(directory) if n.startswith('event-')}==
                self.event_names,'CLOSED_BINDING_CHANGED')
        _need(boot._signature(os.fstat(self.claim._fd))==self.lock and
            boot._signature(os.stat(self.claim.root/'ownership.lock',follow_symlinks=False))==self.lock,
            'CLOSED_BINDING_CHANGED')

    def _observe_entries(self,deadline,*,signatures_only):
        for unit in CLOSE_ORDER:
            original=self.plan['units'][unit];completed=_event(self.claim,_step(unit,'-closed'))
            current=self.native.observe(unit,deadline,original,signatures_only=signatures_only);_source(current,original)
            _closed_manager(current)
            _need(current['mask']==(completed['ownedMask'] or original['mask']) and
                current['active']=='inactive' and current['sub']=='dead' and current['mainPid']==0 and
                current['controlPid']==0,'CLOSED_ENTRY_CHANGED')

    def prepare(self,*,guard,deadline):
        _checked(self.claim,self.native,self.plan['host'],guard,deadline);self._private()
        self._observe_entries(deadline,signatures_only=False)
        extra={'allow_bound_process_absence':True} if self._controlled_stop else {}
        self.native.observe_related_work(self.derived['binding'],self.derived['bindingSha256'],
            guard=guard,deadline=deadline,require_idle=True,**extra)
        self._private()

    def assert_native(self,*,deadline):
        # The content stage must be completed before other sources' final
        # native reads. No owner callback or private/config content read here.
        self._observe_entries(deadline,signatures_only=True)
        extra={'allow_bound_process_absence':True} if self._controlled_stop else {}
        self.native.observe_related_work_native(self.derived['binding'],self.derived['bindingSha256'],
            deadline=deadline,require_idle=True,**extra)
        self._signatures();_need(time.monotonic()<deadline,'DEADLINE')

    def __call__(self,*,guard,timeout=60):
        deadline=_deadline(timeout);self.prepare(guard=guard,deadline=deadline)
        self.assert_native(deadline=deadline)
        return _result('FIXED_HOST_ENTRIES_CLOSED_OBSERVED_ONLY')


def close_host_admission(claim,unit,*,guard,native=None,timeout=60):
    require_native_runtime();_need(os.geteuid()==0 and unit in CLOSE_ORDER,'UNIT_INVALID')
    plan=_bound(claim);original=plan['units'][unit]
    _derived_bound(claim)
    _need(all(_event(claim,_step(u,'-closed')) is not None for u in CLOSE_ORDER[:CLOSE_ORDER.index(unit)]) and
        all(_event(claim,_step(unit,s)) is None for s in ('-mask-intent','-stop-intent','-closed')) and
        not any('-restore-' in e['step'] or e['step']=='released' for e in claim.events),'ACTION_PENDING_OR_OUT_OF_ORDER')
    native=NativeHostAdmission() if native is None else native;deadline=_deadline(timeout)
    def check():
        _checked(claim,native,plan['host'],guard,deadline);_need(_bound(claim)==plan,'ORIGINAL_BINDING_CHANGED')
    check();_prefix(claim,plan,native,CLOSE_ORDER[:CLOSE_ORDER.index(unit)],deadline)
    current=native.observe(unit,deadline);_need(current=={k:original[k] for k in UNIT_FIELDS},'ORIGINAL_BINDING_CHANGED')
    owned=None
    if not original['originalMasked']:
        claim.record(_step(unit,'-mask-intent'),{'originalSha256':_digest(original)})
        check();_need(native.observe(unit,deadline)==current,'ORIGINAL_BINDING_CHANGED')
        owned=native.create_owned_mask(unit);check()
        _need(owned is not None,'MASK_OWNERSHIP_UNPROVEN')
        current=native.observe(unit,deadline,original);_source(current,original)
        _need(current['mask']==owned and current['active']==original['active'],'MASK_EFFECT_UNCERTAIN')
        claim.record(_step(unit,'-masked'),{'mask':owned})
    if original['active']=='active':
        claim.record(_step(unit,'-stop-intent'),{'originalSha256':_digest(original)})
        check();current=native.observe(unit,deadline,original);_source(current,original)
        _need(current['mask']==(owned or original['mask']) and current['active']=='active' and
              all(current[k]==original[k] for k in ('loadState','loadedConfigurationPaths','mainPid','controlPid')) and
              current['stopContractSha256']==original['stopContractSha256'],'STOP_CONTRACT_CHANGED')
        native.command('stop',unit,deadline)
    current=_wait(claim,plan,native,unit,original,deadline,check,'inactive')
    if owned is not None:
        # Reloading a masked running service may reset its safe KillMode.
        # JOB_STOP consumes the retained original manager object first; only
        # after natural inactive may this task reload its new runtime mask.
        native.command('reload',None,deadline)
        current=_wait(claim,plan,native,unit,original,deadline,check,'inactive')
    _need(current['mask']==(owned or original['mask']) and current['active']=='inactive' and current['sub']=='dead'
        and current['mainPid']==0 and current['controlPid']==0,'SYSTEMD_EFFECT_PENDING')
    _closed_manager(current)
    check();last=native.observe(unit,deadline,original);_source(last,original)
    _need(last==current,'ORIGINAL_BINDING_CHANGED');_private_tail(claim,plan,deadline)
    claim.record(_step(unit,'-closed'),{'originalSha256':_digest(original),'ownedMask':owned})
    _private_tail(claim,plan,deadline)
    return _result('HOST_ENTRY_CLOSED_DERIVED_WORK_PENDING')


def restore_host_admission(claim,unit,*,guard,recovery_guard,native=None,timeout=60):
    require_native_runtime();_need(os.geteuid()==0 and unit in RESTORE_ORDER,'UNIT_INVALID')
    _need(callable(recovery_guard),'RECOVERY_GUARD_REQUIRED');plan=_bound(claim);original=plan['units'][unit]
    _need(all(_event(claim,_step(u,'-closed')) is not None for u in CLOSE_ORDER) and
        all(_event(claim,_step(u,'-restored')) is not None for u in RESTORE_ORDER[:RESTORE_ORDER.index(unit)]) and
        _event(claim,_step(unit,'-restore-intent')) is None and _event(claim,_step(unit,'-restored')) is None,
        'ACTION_PENDING_OR_OUT_OF_ORDER')
    _need(not (unit.endswith('.timer') and original['active']=='active') or original['timerResumeApproved'],
          'TIMER_RESUME_SEMANTICS_UNAPPROVED')
    native=NativeHostAdmission() if native is None else native;deadline=_deadline(timeout)
    owned=_event(claim,_step(unit,'-closed'))['ownedMask']
    def check():
        recovery_guard();_checked(claim,native,plan['host'],guard,deadline);_need(_bound(claim)==plan,'ORIGINAL_BINDING_CHANGED')
    check();_prefix(claim,plan,native,RESTORE_ORDER[:RESTORE_ORDER.index(unit)],deadline,restored=True)
    pending=[u for u in CLOSE_ORDER if u not in RESTORE_ORDER[:RESTORE_ORDER.index(unit)]]
    _prefix(claim,plan,native,pending,deadline)
    current=native.observe(unit,deadline,original);_source(current,original)
    _need(current['mask']==(owned or original['mask']) and current['active']=='inactive' and
        current['mainPid']==0 and current['controlPid']==0,'MASK_OWNERSHIP_UNPROVEN')
    claim.record(_step(unit,'-restore-intent'),{'originalSha256':_digest(original),'ownedMask':owned})
    check();current=native.observe(unit,deadline,original);_source(current,original)
    _need(current['mask']==(owned or original['mask']) and current['active']=='inactive','MASK_OWNERSHIP_UNPROVEN')
    if owned is not None:
        native.remove_owned_mask(unit,owned);native.command('reload',None,deadline)
    check();current=native.observe(unit,deadline,original);_source(current,original)
    _need(current['mask']==original['mask'] and current['active']=='inactive','RESTORE_EFFECT_UNCERTAIN')
    if original['active']=='active':
        _need(current['stopContractSha256']==original['stopContractSha256'] and
              current['timerSemanticsSha256']==original['timerSemanticsSha256'],'ORIGINAL_BINDING_CHANGED')
        native.command('start',unit,deadline)
    current=_wait(claim,plan,native,unit,original,deadline,check,original['active'])
    _need(all(current[k]==original[k] for k in ('loadState','mask','persistentMask','active','sub','unitFileState',
        'stopContractSha256','timerSemanticsSha256')) and current['controlPid']==0,'RESTORE_EFFECT_PENDING')
    check();last=native.observe(unit,deadline,original);_source(last,original)
    _need(last==current,'ORIGINAL_BINDING_CHANGED');_private_tail(claim,plan,deadline)
    claim.record(_step(unit,'-restored'),{'originalSha256':_digest(original)})
    _private_tail(claim,plan,deadline)
    return _result('HOST_ENTRY_RESTORED_DERIVED_WORK_PENDING')
