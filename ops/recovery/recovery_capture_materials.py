"""Shared strict material algorithms; this module grants no restore permission.

The caller owns the write barrier's lifecycle. Ordinary source capture still
restores its source unconditionally in its worker; MAIN retains its original
custody. Neither lifecycle is represented by an optional boolean/callback.
"""
from copy import deepcopy
import os
from pathlib import Path
import stat
import subprocess
import sys
from importlib.util import find_spec

from formal_capture_budget import drain_owned_process
from formal_capture_incremental import canonical, write_record
from formal_capture_recovery_inputs import capture_recovery_inputs
from formal_capture_semantics import observe_position
from formal_data_evidence import DataMySql, compare_data, observe_data, observe_affected_data
from formal_snapshot_linux import PrivateDockerMySql, require
from minimal_capture_support import MinimalSeries, MinimalSemantic, actual_pin, path_checked


def save_application_images(path,images,budget,*,process_observer=None):
    """Use the existing bounded image stream with an optional real-client owner."""
    from formal_snapshot_linux import _drain_observed_process
    require(process_observer is None or all(callable(getattr(process_observer,name,None))
        for name in ('before','started','finished')),'FORMAL_MYSQL_PROCESS_OBSERVER_INVALID')
    command=['docker','image','save',*images]
    with budget.open(path,'images') as sink:
        if process_observer is not None:process_observer.before(command)
        process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        _drain_observed_process(process,b'',sink,guard=budget.check,deadline=budget.deadline,
            observer=process_observer,argv=command)
        sink.flush();os.fsync(sink.fileno())


class SourceCaptureLifecycle:
    """Closed adapter for the existing source worker, not a restore switch."""
    def __init__(self,runtime):
        module=sys.modules.get(type(runtime).__module__)
        selected=find_spec('minimal_capture_worker')
        require(type(runtime).__module__ in ('minimal_capture_worker','__main__') and module is not None and
                type(runtime) is getattr(module,'Runtime',None) and selected is not None and
                Path(module.__file__).resolve()==Path(selected.origin).resolve(),'MINIMAL_CAPTURE_LIFECYCLE_INVALID')
        self.runtime=runtime
        self.worker=module
        self.semantic=None

    def _mysql(self,source,limits):
        password=self.originals.read(source['passwordPin'],16384).decode('utf-8').removesuffix('\n')
        return (PrivateDockerMySql(source['mysqlContainerId'],password,timeout=limits['querySeconds']),
                DataMySql(source['mysqlContainerId'],password,timeout=limits['querySeconds']))

    def _save_images(self,path,images,budget):
        save_application_images(path,images,budget)
        self.worker.validate_image_export(path,images,budget.check)
        return actual_pin(path,budget.check)

    def _semantic(self,series,originals,descriptor,source):
        self.semantic=MinimalSemantic(series,originals,descriptor,source)
        return self.semantic

    def _admit_semantic(self,prepared):
        source=prepared.config['source']
        prepared.semantic.verify_endpoint(prepared.budget.check)
        if 'redisSnapshot' in source:
            from minimal_redis_snapshot import preflight as redis_preflight
            redis_preflight(source['redisSnapshot'],prepared.budget.check)
        programs=['mysql','sh','timeout']
        if prepared.identity['action']=='FULL':programs.append('mysqldump')
        self.runtime.command(['exec',source['mysqlContainerId'],'sh','-ec',
            'for program in '+' '.join(programs)+'; do command -v "$program" >/dev/null || exit 1; done'])
        self.runtime.event('CAPTURE_DEPENDENCIES_VERIFIED')

    def _capture_database(self,prepared):
        _capture_database(prepared,self.runtime)

    def _verify_parent(self,semantic):
        semantic.check()

    def _verify_objects(self,semantic):
        self.worker.verify_objects_after_offline(semantic,self.runtime)


class PreparedCaptureMaterials:
    def __init__(self,config,identity,root,budget,originals,lifecycle):
        self.config,self.identity=deepcopy(config),deepcopy(identity)
        self.root,self.budget,self.originals,self.lifecycle=Path(root),budget,originals,lifecycle
        self._configuration_bytes=canonical(config);self._identity_bytes=canonical(identity)
        self._used=False

    def check(self):
        self.budget.check();self.originals.current()
        require(canonical(self.config)==self._configuration_bytes and
                canonical(self.identity)==self._identity_bytes,'MINIMAL_CAPTURE_MATERIALS_CHANGED')


class CapturedMaterials:
    """Material references only: sourceRestored/READY are never implied."""
    def __init__(self,prepared,result):
        require(type(prepared) is PreparedCaptureMaterials and prepared._used,
                'MINIMAL_CAPTURE_MATERIALS_INVALID')
        self._prepared,self._result=prepared,deepcopy(result)

    @property
    def result(self):return deepcopy(self._result)


def _lifecycle(value):
    if type(value) is SourceCaptureLifecycle:return value.runtime
    from recovery_target_capture import MainTargetCapture
    require(type(value) is MainTargetCapture,'MINIMAL_CAPTURE_LIFECYCLE_INVALID')
    return value.runtime


def prepare_materials(config,identity,root,*,output_budget,originals,transport):
    """Retain original configs, semantic inputs and images before stopping.

    All SQL/object/Redis algorithms and formats stay in their existing formal
    modules. The concrete lifecycle supplies only its proved transport/custody.
    """
    runtime=_lifecycle(transport);source=config['source'];limits=config['limits'];budget=output_budget
    require(runtime.config==config and runtime.root==Path(root) and runtime.budget is budget,
            'MINIMAL_CAPTURE_MATERIALS_BINDING_CHANGED')
    prepared=PreparedCaptureMaterials(config,identity,root,budget,originals,transport)
    transport.originals=originals
    descriptor=originals.document(source['objectSourcePin'])
    expected_parent=None if config['parent'] is None else config['parent']['objectContentIndexPin']
    require(descriptor['parentExportIndexPin']==expected_parent,'MINIMAL_OBJECT_PARENT_CHANGED')
    secret_refs=[source['passwordPin'],descriptor['credentialReference']]
    redis=source.get('redisSnapshot',{})
    if 'passwordPin' in redis:secret_refs.append(redis['passwordPin'])
    secrets={reference['path'] for reference in secret_refs}
    for reference in secret_refs:
        # Provisioned immutable S3 credentials are owner-read-only. Other
        # secret transports retain their existing exact owner-read/write mode.
        modes=(0o400,0o600) if reference==descriptor['credentialReference'] else (0o600,)
        require(stat.S_IMODE(path_checked(reference['path']).stat().st_mode) in modes,
                'MINIMAL_SECRET_MODE_REQUIRED')
    mysql,data_mysql=transport._mysql(source,limits)
    mysql.database_log_mode=source.get('databaseLogMode','GTID')
    mode=mysql.query('SELECT @@global.gtid_mode;').strip()
    require(mode==('ON' if mysql.database_log_mode=='GTID' else 'OFF'),'MINIMAL_DATABASE_LOG_MODE_CHANGED')
    runtime.mysql=mysql
    require(mysql.query('SELECT @@server_uuid;').strip()==source['databaseUuid'],'MINIMAL_DATABASE_UUID_CHANGED')
    runtime.flags=mysql.query('SELECT @@global.read_only,@@global.super_read_only;').strip().split('\t')
    require(len(runtime.flags)==2 and all(x in ('0','1') for x in runtime.flags),'MINIMAL_DATABASE_FLAGS_INVALID')
    budget.mkdir(Path(root)/'payload');budget.mkdir(Path(root)/'recovery-materials');budget.mkdir(Path(root)/'original-configs')
    write_record(Path(root)/'payload'/'database-log-mode.json',dict(mode=mysql.database_log_mode,observedGtidMode=mode))
    catalog_pin=write_record(Path(root)/'recovery-materials'/'catalog.json',dict(
        schemaVersion='minimal-capture-catalog/v1',sourceIdentity=source['sourceIdentity'],
        configurationPins=source['configurationPins'],materialPins=source['materialPins']))
    series=MinimalSeries(config,identity,catalog_pin,originals,budget.check)
    semantic=transport._semantic(series,originals,descriptor,source)
    prepared.mysql,prepared.data_mysql,prepared.series,prepared.semantic=mysql,data_mysql,series,semantic
    if type(transport) is SourceCaptureLifecycle:transport._admit_semantic(prepared)
    material_rows=[];config_rows={}
    for key,label,prefix in (('configurationPins','role','original-configs'),('materialPins','purpose','recovery-materials')):
        for item in source[key]:
            reference=item['reference']
            require(reference['path'] not in secrets,'MINIMAL_SECRET_AS_MATERIAL_REFUSED')
            raw=originals.read(reference);relative=prefix+'/'+item[label]+'.bin'
            with budget.open(Path(root)/relative,'config') as out:
                out.write(raw);out.flush();os.fsync(out.fileno())
            material_rows.append(dict(archivePath=relative,sourcePin=reference,purpose=item[label]))
            if key=='configurationPins':
                config_rows[item[label]]=dict(source=reference,copyPath=item[label]+'.bin',
                    copySha256=reference['sha256'],copyBytes=reference['bytes'])
    write_record(Path(root)/'original-configs'/'config-capture-stage.json',dict(
        schemaVersion='minimal-capture-configuration-stage/v1',originals=config_rows))
    material_rows.append(dict(archivePath='recovery-materials/catalog.json',sourcePin=catalog_pin,purpose='capture-catalog'))
    write_record(Path(root)/'recovery-materials'/'index.json',dict(schemaVersion='backup-capture-material-index/v1',files=material_rows))
    runtime.phase='CONFIGURATION_AND_IMAGE_CAPTURE'
    image_path=Path(root)/'payload'/'original-application-images.tar'
    if type(transport) is SourceCaptureLifecycle:
        image_pin=transport._save_images(image_path,source['applicationImageIds'],budget)
    else:
        transport._save_images(image_path,source['applicationImageIds'],budget)
        transport.worker.validate_image_export(image_path,source['applicationImageIds'],budget.check)
        image_pin=actual_pin(image_path,budget.check)
    write_record(Path(root)/'payload'/'050-original-images.json',dict(imageIds=source['applicationImageIds'],
        archivePin=image_pin))
    runtime.event('CONFIGURATION_AND_IMAGES_CAPTURED')
    prepared.check()
    return prepared


def _capture_database(prepared,runtime):
    """The original full strict algorithm, also used by MAIN without a flag."""
    source=prepared.config['source'];limits=prepared.config['limits'];root=prepared.root;budget=prepared.budget
    mysql,data_mysql,series=prepared.mysql,prepared.data_mysql,prepared.series
    def data(name):
        return observe_data(data_mysql,source['database'],source['databaseUuid'],guard=runtime.protected,
            scratch=root/name,max_rows=limits['dataMaxRows'],max_nodes=limits['dataMaxNodes'],
            max_bytes=limits['dataMaxBytes'],seconds=limits['dataSeconds'])
    if prepared.identity['action']=='FULL':
        runtime.phase='SOURCE_DATA_BEFORE';before=data('scratch-before')
        write_record(root/'payload'/'011-source-data.json',before)
    runtime.phase='DATABASE_CAPTURE'
    series.database(mysql,source['database'],root/'payload'/'database.sql.gz',guard=runtime.protected)
    if prepared.identity['action']=='FULL':
        runtime.phase='SOURCE_DATA_AFTER';after=data('scratch-after');compare_data(before,after)
        write_record(root/'payload'/'012-source-data-after.json',after)
    else:
        runtime.phase='SOURCE_AFFECTED_DATA'
        changed=sorted({table for segment in series.database_scope['segments'] for table in segment['affectedTables']})
        case=mysql.query('SELECT @@lower_case_table_names;').strip()
        require(case in ('0','1','2'),'MINIMAL_DATABASE_CASE_INVALID')
        observed=observe_affected_data(data_mysql,source['database'],source['databaseUuid'],affected_tables=changed,
            lower_case_table_names=int(case),guard=runtime.protected,scratch=root/'scratch-affected',
            max_rows=limits['dataMaxRows'],max_nodes=limits['dataMaxNodes'],max_bytes=limits['dataMaxBytes'],seconds=limits['dataSeconds'])
        write_record(root/'payload'/'source-affected-data.json',observed)
        series.database_delta.update(dataObservation='AFFECTED_TABLES_V1',lowerCaseTableNames=int(case))


def capture_protected_materials(prepared,lifecycle):
    require(type(prepared) is PreparedCaptureMaterials and prepared.lifecycle is lifecycle and not prepared._used,
            'MINIMAL_CAPTURE_MATERIALS_INVALID')
    runtime=_lifecycle(lifecycle);prepared.check();prepared._used=True
    worker=lifecycle.worker
    source=prepared.config['source'];root=prepared.root;budget=prepared.budget
    mysql,series,semantic=prepared.mysql,prepared.series,prepared.semantic
    runtime.phase='SEMANTIC_CAPTURE'
    semantic.capture(mysql,source['database'],root/'semantic-capture',runtime.protected)
    if type(lifecycle) is SourceCaptureLifecycle:lifecycle._capture_database(prepared)
    else:_capture_database(prepared,runtime)
    runtime.phase='MINIO_OFFLINE_PRECHECK';runtime.protected(force=True)
    runtime.phase='MINIO_STOP';runtime.stop(source['minioContainerId']);runtime.minio_stopped=True
    runtime.phase='MINIO_PHYSICAL_CAPTURE'
    series.files(source['minioDataPath'],root/'payload'/'minio-physical',guard=runtime.protected,scopes=source.get('minioPhysicalScopes'))
    runtime.protected(force=True)
    runtime.phase='MINIO_START';runtime.command(['start','--',source['minioContainerId']]);runtime.minio_stopped=False
    runtime.phase='MINIO_READINESS';worker.wait_ready(semantic,runtime)
    runtime.phase='OBJECT_RECHECK';lifecycle._verify_objects(semantic)
    runtime.phase='DATABASE_POINT_RECHECK'
    require(observe_position(mysql,runtime.protected)==series.end,'MINIMAL_DATABASE_POINT_CHANGED')
    point=series.point(source_restored=False)
    write_record(root/'payload'/'capture-content-point.json',point)
    write_record(root/'payload'/'capture-file-inventory.json',series.file_inventory)
    runtime.phase='SEMANTIC_FINALIZE';supplement,_=semantic.finalize(point,runtime.protected)
    runtime.phase='CAPTURE_FINAL_CHECK'
    if type(lifecycle) is SourceCaptureLifecycle:lifecycle._verify_parent(semantic)
    prepared.originals.check(full=True);runtime.protected(force=True)
    entries=worker.archive_entries(root,budget.check)
    inputs=capture_recovery_inputs(point,source_root=str(root),entries=entries,supplemental=supplement)
    inputs_pin=write_record(root/'capture-recovery-inputs.json',inputs);entries['capture-recovery-inputs.json']=worker.marker(inputs_pin)
    entries_pin=write_record(root/'capture-archive-entries.json',entries)
    return CapturedMaterials(prepared,dict(captureRoot=str(root),captureInputsPin=inputs_pin,archiveEntriesPin=entries_pin,
        capturePointPin=actual_pin(root/'payload'/'capture-content-point.json'),
        objectContentIndexPin=actual_pin(root/'semantic-capture'/'object-content-index.json'),
        recoveryPoint=point['commonRecoveryPoint'],sourceIdentity=source['sourceIdentity']))
