"""Full readback over a new authenticated SMB connection and private cache."""
import hashlib
import os
from pathlib import Path, PureWindowsPath
import re
import stat

from repository_records import (absolute, document, exact, pin_file, read_pin,
                                require, safe_path, write_new)
from repository_host_view import logical


def relative_name(value):
    require(type(value) is str and value and not value.startswith('/') and
            not re.search(r'[\\:*?"<>|\x00-\x1f]', value) and
            all(p not in ('', '.', '..') and p.rstrip(' .') == p for p in value.split('/')),
            'REPOSITORY_READBACK_PATH_INVALID')
    return value


class SmbReadback:
    def __init__(self, configuration, deadline, *, verify_environment=True):
        self.verify_environment = verify_environment
        exact(configuration, 'schemaVersion uncRoot repositoryRelativePath repositoryRoot credentialPin port authProtocol recordRoot maximumRecordBytes maximumTotalRecordBytes libraryPins',
              'RepositorySmbReadbackConfig/v1')
        require(configuration['uncRoot'].startswith('\\\\') and
                configuration['authProtocol'] in ('ntlm', 'kerberos') and
                type(configuration['port']) is int and 1 <= configuration['port'] <= 65535,
                'REPOSITORY_SMB_CONFIGURATION_INVALID')
        self.configuration, self.deadline = configuration, deadline
        relative_name(configuration['repositoryRelativePath'])
        self.cache = {}
        if verify_environment:
            require(configuration['libraryPins'], 'REPOSITORY_SMB_LIBRARY_PINS_REQUIRED')
            for reference in configuration['libraryPins']:
                read_pin(reference, 32 * 1024 * 1024, deadline)
        import smbclient
        import smbprotocol
        if verify_environment:
          require(all(any(absolute(p['path']) == Path(module.__file__) for p in configuration['libraryPins'])
                    for module in (smbclient, smbprotocol)), 'REPOSITORY_SMB_LIBRARY_CHANGED')
        self.client = smbclient
        credential = document(read_pin(configuration['credentialPin'], 65536, deadline))
        exact(credential, 'schemaVersion server share username password', 'RepositorySmbCredential/v1')
        if verify_environment:
          require(configuration['uncRoot'] == '\\\\' + credential['server'] + '\\' + credential['share'] and
                all(type(credential[k]) is str and credential[k] for k in ('server', 'share', 'username', 'password')),
                'REPOSITORY_SMB_CREDENTIAL_TARGET_MISMATCH')
        self.session = smbclient.register_session(credential['server'], username=credential['username'],
            password=credential['password'], port=configuration['port'], encrypt=True,
            auth_protocol=configuration['authProtocol'], require_signing=True,
            connection_timeout=deadline.remaining(), connection_cache=self.cache)
        if verify_environment:
          require(self.session.connection.transport.connected and self.session.encrypt_data and
                self.session.connection.require_signing and len(self.cache) == 1,
                'REPOSITORY_SMB_AUTHENTICATION_UNPROVEN')
        self.connection_id = str(self.session.connection.client_guid) + ':' + str(self.session.session_id)
        self.kwargs = dict(connection_cache=self.cache, port=configuration['port'])
        self.record_bytes = 0
        require(type(configuration['maximumRecordBytes']) is int and
                0 < configuration['maximumRecordBytes'] <= 64 * 1024 * 1024 and
                type(configuration['maximumTotalRecordBytes']) is int and
                configuration['maximumTotalRecordBytes'] >= configuration['maximumRecordBytes'],
                'REPOSITORY_READBACK_RECORD_BUDGET_REQUIRED')
        root = safe_path(configuration['recordRoot'])
        self.records = root / hashlib.sha256(self.connection_id.encode()).hexdigest()
        self.records.mkdir(mode=0o700)

    def remote(self, repository_path):
        path = logical(repository_path)
        root = logical(self.configuration['repositoryRoot'])
        require(root in path.parents or path == root, 'REPOSITORY_SMB_PATH_ESCAPED')
        return str(PureWindowsPath(self.configuration['uncRoot']) /
                   self.configuration['repositoryRelativePath'] / path.relative_to(root).as_posix())

    def check(self):
        self.deadline.check()
        if self.verify_environment:
            require(self.session.connection.transport.connected and self.session.encrypt_data,
                    'REPOSITORY_SMB_CONNECTION_LOST')

    def read(self, repository_path, expected=None, retain=False):
        self.check()
        remote = self.remote(repository_path)
        before = self.client.stat(remote, follow_symlinks=False, **self.kwargs)
        require(stat.S_ISREG(before.st_mode) and not (getattr(before, 'st_file_attributes', 0) & 1024),
                'REPOSITORY_SMB_FILE_REQUIRED')
        if retain:
            require(before.st_size <= self.configuration['maximumRecordBytes'] and
                    self.record_bytes + before.st_size <= self.configuration['maximumTotalRecordBytes'],
                    'REPOSITORY_READBACK_RECORD_BUDGET_EXCEEDED')
        digest, length, raw = hashlib.sha256(), 0, bytearray()
        with self.client.open_file(remote, mode='rb', share_access='r', **self.kwargs) as stream:
            while True:
                self.check()
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                length += len(chunk)
                digest.update(chunk)
                if retain:
                    raw.extend(chunk)
        reference = dict(path=logical(repository_path).as_posix(), bytes=length, sha256=digest.hexdigest())
        retained = None
        if retain:
            path = self.records / (hashlib.sha256(repository_path.encode()).hexdigest() + '.raw')
            with path.open('xb') as output:
                output.write(raw)
                output.flush()
                os.fsync(output.fileno())
            retained = pin_file(path, self.deadline)
            self.record_bytes += length
        return reference, retained

    def tree(self, archive):
        entries = {}
        def walk(relative):
            self.check()
            root = logical(archive) / relative
            for item in self.client.scandir(self.remote(str(root)), **self.kwargs):
                name = relative_name((relative + '/' if relative else '') + item.name)
                if not relative and item.name == '.repository':
                    require(item.is_dir(follow_symlinks=False), 'REPOSITORY_SMB_SIDECAR_INVALID')
                    continue
                info = item.stat(follow_symlinks=False)
                require(not stat.S_ISLNK(info.st_mode) and not (getattr(info, 'st_file_attributes', 0) & 1024),
                        'REPOSITORY_SMB_REPARSE_REFUSED')
                if stat.S_ISDIR(info.st_mode):
                    entries[name] = 'directory'
                    walk(name)
                else:
                    require(stat.S_ISREG(info.st_mode), 'REPOSITORY_SMB_FILE_REQUIRED')
                    entries[name] = info.st_size
        walk('')
        return entries

    def verify(self, archive, expected, material=None, *, payload_content=True):
        archive = logical(archive)
        before = self.tree(str(archive)) if payload_content else None
        if payload_content:
            require(set(before) == set(expected), 'REPOSITORY_INDEPENDENT_PAYLOAD_SET_MISMATCH')
        retained, generated = {}, {}
        inputs = None
        needed = set()
        if material is not None:
            _, inputs_copy = self.read(str(archive / 'capture-recovery-inputs.json'), retain=True)
            inputs = document(read_pin(inputs_copy, 64 * 1024 * 1024))
            retained[(archive / 'capture-recovery-inputs.json').as_posix()] = inputs_copy
            needed = {'semantic-capture/source-inputs.json', 'semantic-capture/object-content-index.json'}
            references = [inputs['objectContentIndexPin']] + [inputs['semanticSupplement'][key] for key in
                          ('referenceInventoryPin', 'derivedInventoryPin', 'objectInventoryPin', 'objectExportReceiptPin')]
            if inputs['database']['expectedDataPin']['path'].endswith('/payload/source-affected-data.json'):
                references.extend([inputs['capturePointPin'], inputs['database']['expectedDataPin'],
                    inputs['archiveFilePins']['payload/database.sql.incremental-scope.json']])
            for reference in references:
                names = [name for name, p in inputs['archiveFilePins'].items() if p == reference]
                require(len(names) == 1, 'REPOSITORY_CAPTURE_ORIGINAL_MAP_INVALID')
                needed.add(names[0])
        for name, marker in sorted(expected.items()):
            self.check()
            if marker == 'directory':
                if payload_content:
                    require(before[name] == marker, 'REPOSITORY_SMB_TYPE_CHANGED')
                continue
            require(type(marker) is str and re.fullmatch(r'file\|(0|[1-9][0-9]*)\|[0-9a-f]{64}', marker),
                    'REPOSITORY_PAYLOAD_TREE_INVALID')
            _, size, digest = marker.split('|')
            target = archive / relative_name(name)
            expected_pin = dict(path=target.as_posix(), bytes=int(size), sha256=digest)
            keep = name in needed or name.startswith('semantic-capture/provided-')
            # ponytail: the single-operator path reads binding records only;
            # payload digests remain declarations, not readback evidence.
            if payload_content or keep:
                reference, copy = self.read(str(target), expected_pin, retain=keep)
            else:
                reference, copy = expected_pin, None
            generated[name] = reference
            if copy is not None:
                retained[name] = copy
        if payload_content:
            require(self.tree(str(archive)) == before, 'REPOSITORY_SMB_TREE_CHANGED')
        original_records_pin = None
        if material is not None:
            self.read(material['manifestPin']['path'], material['manifestPin'])
            self.read(material['payloadTreePin']['path'], material['payloadTreePin'])
            require(sorted(generated.values(), key=lambda p: p['path']) ==
                    sorted(material['payloadRefs'], key=lambda p: p['path']),
                    'REPOSITORY_READBACK_PAYLOAD_SET_MISMATCH')
            records = {source['path']: retained[name] for name, source in inputs['archiveFilePins'].items()
                       if name in retained}
            from pathlib import PurePosixPath
            source_inputs_path = str(PurePosixPath(inputs['capturePointPin']['path']).parents[1] / 'capture-recovery-inputs.json')
            records[source_inputs_path] = retained[(archive / 'capture-recovery-inputs.json').as_posix()]
            provisioned = document(read_pin(retained['semantic-capture/source-inputs.json'], 64 * 1024 * 1024))
            for item in provisioned['provisionedInputCopies']:
                copy_pin = retained[item['archivePath']]
                records[item['sourcePin']['path']] = copy_pin
            original_records_pin = write_new(self.records / 'readback-originals.json',
                dict(schemaVersion='RepositoryReadbackOriginals/v1', manifestPin=material['manifestPin'],
                     archivedFilePins=generated, readbackOriginalPins=records))
        return self.connection_id, original_records_pin

    def close(self):
        # This cache was created for this read only. No writer mapping or other
        # application's SMB session is disconnected.
        self.client.reset_connection_cache(fail_on_error=True, connection_cache=self.cache)

    def __enter__(self):
        return self

    def __exit__(self, kind, value, trace):
        self.close()
