"""Exclusive target-only file staging, without runtime or installation authority.

The caller must hold its own physical lock and enforce current process, mount,
capacity, source and business preservation gates. This module does file work
only and keeps partial results on failure for explicit inspection.
"""
from copy import deepcopy
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tarfile

import main_program_control_staging as legacy
import main_program_target_control_candidate as binding


def need(condition,code):
    if not condition:raise ValueError('MAIN_TARGET_STAGING_'+code)


def _target_package(raw,build):
    """Read exactly the official 153 payload members and original manifest."""
    need(type(raw) is bytes and 0<len(raw)<=legacy.MAX_PACKAGE_BYTES and type(build) is dict,
        'PACKAGE_BUILD_CHANGED')
    package_sha=legacy.digest(raw)
    rows=build.get('packages')
    need(type(rows) is list and len(rows)==2 and all(type(r) is dict for r in rows) and
        {r.get('variant') for r in rows}=={'standard','lightweight'},'PACKAGE_VARIANTS_CHANGED')
    standard=next(r for r in rows if r['variant']=='standard')
    need(standard.get('fileCount')==153 and standard.get('bytes')==len(raw) and
        standard.get('sha256')==legacy.digest(raw),'PACKAGE_BUILD_CHANGED')
    files={};total=0
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
        for member in archive:
            name=member.name;path=PurePosixPath(name)
            need(len(files)<154 and name not in files,'PACKAGE_MEMBER_CLOSURE')
            need(member.isfile() and name and not path.is_absolute() and str(path)==name and
                '..' not in path.parts and not any(c in name for c in ('\\',':','\0')) and
                not any(ord(c)<32 for c in name) and 0<member.size<=legacy.MAX_MEMBER_BYTES,
                'PACKAGE_MEMBER_UNSAFE')
            total+=member.size;need(total<=legacy.MAX_PACKAGE_BYTES,'PACKAGE_EXPANDED_LIMIT')
            content=archive.extractfile(member).read(member.size+1)
            need(len(content)==member.size,'PACKAGE_MEMBER_TRUNCATED');files[name]=content
    need(len(files)==154 and 'package.json' in files,'PACKAGE_MEMBER_CLOSURE')
    metadata=json.loads(files['package.json'].decode('utf-8'),object_pairs_hook=legacy.document)
    payload={name:raw for name,raw in files.items() if name!='package.json'}
    hashes={name:legacy.digest(raw) for name,raw in payload.items()}
    need(type(metadata) is dict and metadata.get('variant')=='standard' and
        metadata.get('fileVerification') is True and metadata.get('payloadContentVerification') is True and
        metadata.get('files')==hashes and
        legacy.digest(legacy.canonical(hashes))==metadata.get('packageSha256')==standard.get('fileManifestSha256'),
        'PACKAGE_MANIFEST_CHANGED')
    for name,raw in payload.items():
        if name.endswith('.py'):compile(raw,name,'exec',dont_inherit=True)
    return dict(files=files,payloadFiles=payload,packageSha256=package_sha,
        fileManifestSha256=standard['fileManifestSha256'])


def _file_pin(location,raw):
    return dict(path=str(location),bytes=len(raw),sha256=legacy.digest(raw))


def _identity(location):
    item=location.lstat()
    return (item.st_dev,item.st_ino,item.st_mode,item.st_nlink,item.st_uid,item.st_gid,
        item.st_size,item.st_mtime_ns,item.st_ctime_ns)


def preflight_target_filesystem(*,candidate,host,current_controller,owner,control,old_build,new_build,
        preservation,configuration_root,new_engine,package_raw,previous_package_raw):
    """Rebuild, read all originals and check every destination; creates nothing."""
    package=_target_package(package_raw,new_build)
    previous=legacy.verify_package(previous_package_raw,old_build)
    rebuilt=binding.build_target_control_candidate(host=host,current_controller=current_controller,owner=owner,control=control,
        old_build=old_build,new_build=new_build,preservation=preservation,configuration_root=configuration_root,
        new_engine=new_engine,package_files=package['payloadFiles'],previous_package_files=previous['payloadFiles'])
    need(type(candidate) is dict and candidate==rebuilt,'CANDIDATE_REBUILD_CHANGED')
    engine=Path(str(binding.path(new_engine)));configuration=Path(str(binding.path(configuration_root)))
    old_engine=Path(str(binding.path(current_controller['engine'])))
    # Existing roots are rejected even if they are empty or dangling symlinks.
    for root,code in ((engine,'ENGINE_EXISTS'),(configuration,'CONFIGURATION_EXISTS')):
        legacy._parent_without_alias(root.parent)
        need(root.parent.is_dir(),'ROOT_PARENT_MISSING');need(not os.path.lexists(root),code)
    legacy._parent_without_alias(old_engine)
    need(old_engine.is_dir(),'PREVIOUS_ENGINE_REQUIRED')
    destinations={};documents=deepcopy(rebuilt['newDocuments'])
    for name,raw in package['files'].items():
        destination=engine/name
        need(destination!=engine and destination.is_relative_to(engine),'PACKAGE_DESTINATION_CHANGED')
        destinations[str(destination)]=raw
    for row in documents:
        destination,raw=legacy._document(row)
        need(destination!=configuration and destination.is_relative_to(configuration) and
            str(destination) not in destinations,'DOCUMENT_DESTINATION_CHANGED')
        destinations[str(destination)]=raw
    need(len(destinations)==170,'DESTINATION_CLOSURE_CHANGED')
    for location in destinations:
        destination=Path(location);legacy._parent_without_alias(destination.parent)
        need(not os.path.lexists(destination),'DESTINATION_EXISTS')
    retained={}
    for name,raw in previous['files'].items():retained[str(old_engine/name)]=_file_pin(old_engine/name,raw)
    for value,key in ((owner,'ownerConfigurationPin'),(control,'controlConfigurationPin')):
        reference=current_controller[key]
        need(reference==_file_pin(reference['path'],legacy.canonical(value)),'ORIGINAL_DOCUMENT_PIN_CHANGED')
        old=retained.setdefault(reference['path'],deepcopy(reference));need(old==reference,'RETAINED_PIN_CONFLICT')
    need(len(retained)==150 and not set(retained)&set(destinations),'RETAINED_DESTINATION_CONFLICT')
    identities={}
    for reference in retained.values():
        legacy._read_pin(reference);identities[reference['path']]=_identity(Path(reference['path']))
    return dict(schemaVersion='MainProgramTargetControlFilesystemPreflight/v1',status='PREFLIGHT_ONLY_NOT_STAGED',
        candidate=deepcopy(rebuilt),engine=str(engine),configurationRoot=str(configuration),
        payloadFileCount=153,packageFileCount=154,documentCount=16,
        package=package,newDocuments=documents,destinations=destinations,
        retainedPins=list(retained.values()),retainedIdentities=identities,
        sourceCommit=rebuilt['sourceCommit'],host=rebuilt['host'])


class TargetStagingFailure(legacy.StagingFailure):
    def __init__(self,created_paths,failed_path):
        RuntimeError.__init__(self,'MAIN_TARGET_STAGING_PARTIAL_FILES_RETAINED')
        self.created_paths=tuple(created_paths)
        self.failed_path=str(failed_path)


def stage_target_filesystem(*,candidate,host,current_controller,owner,control,old_build,new_build,
        preservation,configuration_root,new_engine,package_raw,previous_package_raw):
    """Stage files with native exclusive writes; never issues runtime admission."""
    need(os.name=='posix','NATIVE_POSIX_REQUIRED')
    ready=preflight_target_filesystem(candidate=candidate,host=host,current_controller=current_controller,owner=owner,control=control,
        old_build=old_build,new_build=new_build,preservation=preservation,configuration_root=configuration_root,
        new_engine=new_engine,package_raw=package_raw,previous_package_raw=previous_package_raw)
    created=[];failed=ready['engine'];engine=Path(ready['engine']);configuration=Path(ready['configurationRoot'])
    try:
        legacy._mkdir(engine,created)
        for name,raw in ready['package']['files'].items():
            failed=str(engine/name);legacy._directories(Path(failed).parent,created)
            legacy._write_exclusive(Path(failed),raw,created)
        failed=str(configuration);legacy._mkdir(configuration,created)
        for row in ready['newDocuments']:
            failed=row['pin']['path'];legacy._directories(Path(failed).parent,created)
            legacy._write_exclusive(Path(failed),legacy.canonical(row['value']),created)
        for root,expected in ((engine,{str(engine/name) for name in ready['package']['files']}),
                (configuration,{row['pin']['path'] for row in ready['newDocuments']})):
            failed=str(root)
            observed={str(p) for p in root.rglob('*') if p.is_file() or p.is_symlink()}
            need(observed==expected,'STAGED_CLOSURE_CHANGED')
        for location,raw in ready['destinations'].items():
            failed=location;need(legacy._read_pin(_file_pin(location,raw))==raw,'STAGED_BYTES_CHANGED')
            item=Path(location).lstat()
            need(stat.S_IMODE(item.st_mode)==0o400 and item.st_nlink==1 and item.st_uid==os.geteuid(),
                'STAGED_IDENTITY_CHANGED')
        for reference in ready['retainedPins']:
            failed=reference['path'];legacy._read_pin(reference)
            need(_identity(Path(failed))==ready['retainedIdentities'][failed],'ORIGINAL_IDENTITY_CHANGED')
    except Exception as error:
        raise TargetStagingFailure(created,failed) from error
    return dict(schemaVersion='MainProgramTargetControlFilesystemStaging/v1',status='FILES_STAGED_RUNTIME_UNVERIFIED',
        activationReportEligible=False,sourceCommit=ready['sourceCommit'],host=ready['host'],engine=str(engine),
        configurationRoot=str(configuration),payloadFileCount=153,packageFileCount=154,documentCount=16,
        packageSha256=legacy.digest(package_raw),fileManifestSha256=ready['package']['fileManifestSha256'],
        createdPaths=created,newDocuments=[deepcopy(row['pin']) for row in ready['newDocuments']],
        retainedPins=deepcopy(ready['retainedPins']),originalFilesUnchanged=True,
        installationPerformed=False,controlServicesReloaded=False,restoreDispatched=False)
