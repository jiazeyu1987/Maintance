"""Archive-derived immutable point catalog and complete dependency chains."""
from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import re
import hashlib

from repository_records import (RepositoryError, absolute, document, exact, pin_file,
                                read_pin, require, safe_path, timestamp, utc, write_new, canonical,
                                signed_pin)
from repository_binding import repository_binding


class Catalog:
    def __init__(self, config, deadline):
        self.config, self.deadline = config, deadline
        self.archives = safe_path(config.root / 'archives')
        require(self.archives.is_dir(), 'REPOSITORY_ARCHIVES_REQUIRED')

    def contained(self, pin, root):
        path = safe_path(pin['path'])
        require(root in path.parents, 'REPOSITORY_ARCHIVE_PATH_ESCAPED')
        return path

    def manifest(self, point):
        path = self.contained(point['manifestPin'], self.archives)
        require(path.name == 'manifest.json' and path.parent.name == '.repository', 'REPOSITORY_MANIFEST_LOCATION_INVALID')
        value = document(read_pin(point['manifestPin'], deadline=self.deadline))
        exact(value, 'schemaVersion backupId generationId pointType parentPointPins commonRecoveryPoint sourceIdentityPin createdAt versionPins toolPins payloadRefs payloadTreePin copyProtectionPin', 'RepositoryManifest/v1')
        for key in ('backupId', 'generationId', 'pointType', 'parentPointPins', 'commonRecoveryPoint', 'payloadRefs'):
            require(value[key] == point[key], 'REPOSITORY_MANIFEST_POINT_MISMATCH')
        require(value['sourceIdentityPin'] == self.config.policy['sourceIdentityPin'], 'REPOSITORY_POINT_SOURCE_MISMATCH')
        read_pin(value['sourceIdentityPin'])
        require(value['versionPins'] and value['toolPins'], 'REPOSITORY_VERSION_METADATA_REQUIRED')
        for key, supported in (('versionPins', 'supportedVersionPins'), ('toolPins', 'supportedToolPins')):
            require(type(value[key]) is list and all(pin in self.config.policy[supported] for pin in value[key]), 'REPOSITORY_VERSION_UNSUPPORTED')
            for pin in value[key]:
                read_pin(pin)
        require(timestamp(value['createdAt']) <= datetime.now(timezone.utc), 'REPOSITORY_FUTURE_POINT_REFUSED')
        require(value['copyProtectionPin'] == self.config.copy_protection(), 'REPOSITORY_COPY_POLICY_CHANGED')
        return value, path.parent.parent

    def payload(self, point, manifest, archive, *, verify_content=True):
        tree = document(read_pin(manifest['payloadTreePin'], deadline=self.deadline))
        require(type(tree) is dict and tree, 'REPOSITORY_PAYLOAD_TREE_INVALID')
        self.contained(manifest['payloadTreePin'], archive / '.repository')
        if not verify_content:
            for ref in point['payloadRefs']:
                self.contained(ref, archive)
            return {str(Path(ref['path']).relative_to(archive)): ref for ref in point['payloadRefs']}
        expected = set()
        files = {}
        for relative, spec in tree.items():
            self.deadline.check()
            require(type(relative) is str and relative and not re.search(r'[\\:*?"<>|\x00-\x1f]', relative) and not relative.startswith('/') and all(part not in ('', '.', '..', '.repository') for part in relative.split('/')), 'REPOSITORY_PAYLOAD_PATH_INVALID')
            require(not any(part.rstrip(' .') != part or re.fullmatch(r'(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', part) for part in relative.split('/')), 'REPOSITORY_PAYLOAD_PATH_INVALID')
            require(relative.casefold() not in {name.casefold() for name in expected}, 'REPOSITORY_CASE_COLLISION')
            path = safe_path(archive / relative)
            require(archive in path.parents, 'REPOSITORY_PAYLOAD_PATH_ESCAPED')
            expected.add(relative)
            if spec == 'directory':
                require(path.is_dir(), 'REPOSITORY_PAYLOAD_CORRUPT')
            else:
                require(type(spec) is str and re.fullmatch(r'file\|(0|[1-9][0-9]*)\|[0-9a-f]{64}', spec), 'REPOSITORY_PAYLOAD_TREE_INVALID')
                _, size, sha = spec.split('|')
                require(path.is_file(), 'REPOSITORY_PAYLOAD_CORRUPT')
                from repository_host_view import original_path
                actual = (pin_file(path, self.deadline) if verify_content else
                          dict(path=original_path(path), bytes=path.stat().st_size, sha256=sha))
                require(actual['bytes'] == int(size) and actual['sha256'] == sha, 'REPOSITORY_PAYLOAD_CORRUPT')
                files[relative] = actual
        actual_paths = set()
        for root, dirs, names in os.walk(archive, followlinks=False):
            self.deadline.check()
            if Path(root) == archive:
                dirs[:] = [name for name in dirs if name != '.repository']
            for name in dirs + names:
                path = safe_path(Path(root) / name)
                actual_paths.add(path.relative_to(archive).as_posix())
        require(expected == actual_paths and files and [files[name] for name in sorted(files)] == point['payloadRefs'], 'REPOSITORY_PAYLOAD_SET_MISMATCH')
        return files

    def evidence(self, point):
        for key, schema in (('readbackEvidencePin', 'RepositoryReadback/v1'), ('ownerCloseEvidencePin', 'RepositoryOwnerClose/v1'), ('originalExitEvidencePin', 'RepositoryOriginalExit/v1')):
            proof = self.config.evidence_record(point[key], schema)
            require(proof['backupId'] == point['backupId'] and proof['manifestPin'] == point['manifestPin'], 'REPOSITORY_EVIDENCE_POINT_MISMATCH')
            if key == 'readbackEvidencePin':
                require(proof['independentConnection'] is True and proof['payloadRefs'] == point['payloadRefs'] and proof['serverDurabilityVerified'] is False, 'REPOSITORY_READBACK_UNPROVEN')
            elif key == 'ownerCloseEvidencePin':
                require(proof['exactReaderCloseVerified'] is True and proof['sourceFinalGuardVerified'] is True, 'REPOSITORY_OWNER_CLOSE_UNPROVEN')
            else:
                require(type(proof['actualExitCode']) is int and proof['actualExitCode'] == 0 and proof['rawTerminalVerified'] is True and proof['processTerminated'] is True, 'REPOSITORY_ORIGINAL_EXIT_UNKNOWN')
            require(proof['operationId'] and proof['originalProcessPin'], 'REPOSITORY_PROCESS_EVIDENCE_REQUIRED')
            read_pin(proof['originalProcessPin'])
        readback = self.config.evidence_record(point['readbackEvidencePin'], 'RepositoryReadback/v1')
        closed = self.config.evidence_record(point['ownerCloseEvidencePin'], 'RepositoryOwnerClose/v1')
        exited = self.config.evidence_record(point['originalExitEvidencePin'], 'RepositoryOriginalExit/v1')
        require(readback['originalProcessPin'] == closed['originalProcessPin'] == exited['originalProcessPin'] and readback['operationId'] == closed['operationId'] == exited['operationId'], 'REPOSITORY_ORIGINAL_PROCESS_MISMATCH')

    def load(self, pin):
        self.contained(pin, self.archives)
        point = document(read_pin(pin, deadline=self.deadline))
        self.config.validate(point, 'RepositoryPoint')
        require(point['integrityState'] == 'COMPLETE', 'REPOSITORY_POINT_INCOMPLETE')
        manifest, archive = self.manifest(point)
        require(absolute(pin['path']) == archive / '.repository' / 'point.json', 'REPOSITORY_POINT_LOCATION_INVALID')
        self.payload(point, manifest, archive)
        self.evidence(point)
        self.binding(pin, point)
        return point, manifest

    def binding(self, point_pin, point=None):
        if point is None:
            point = document(read_pin(point_pin, deadline=self.deadline))
        sidecar = Path(point['manifestPin']['path']).parent
        binding_pin = pin_file(sidecar / 'recovery-repository-binding.json', self.deadline)
        self.contained(binding_pin, self.archives)
        value = document(read_pin(binding_pin, deadline=self.deadline))
        exact(value, 'schemaVersion backupId generationId repositoryPointPin manifestPin sourceScopePin recoveryMaterialPin objectContentIndexPin', 'RecoveryRepositoryBinding/v1')
        require(value['repositoryPointPin'] == point_pin and value['manifestPin'] == point['manifestPin'] and
                value['backupId'] == point['backupId'] and value['generationId'] == point['generationId'],
                'REPOSITORY_CAPTURE_BINDING_POINT_MISMATCH')
        for field in ('recoveryMaterialPin', 'objectContentIndexPin'):
            self.contained(value[field], sidecar)
        expected = repository_binding(self.config, point_pin, point,
                                      value['recoveryMaterialPin'], value['objectContentIndexPin'])
        require(value == expected, 'REPOSITORY_CAPTURE_BINDING_INVALID')
        proof = self.config.evidence_record(point['readbackEvidencePin'], 'RepositoryReadback/v1')
        require(all(proof[field] == value[field] for field in
                    ('recoveryMaterialPin', 'objectContentIndexPin', 'sourceScopePin')),
                'REPOSITORY_CAPTURE_BINDING_NOT_AUTHENTICATED')
        index = document(read_pin(value['objectContentIndexPin'], 64 * 1024 * 1024, self.deadline))
        allowed_archives = {Path(p['path']).parent.parent for p in point['parentPointPins'] + [point_pin]}
        owned_payloads = list(point['payloadRefs'])
        for parent_pin in point['parentPointPins']:
            parent = document(read_pin(parent_pin, deadline=self.deadline))
            self.config.validate(parent, 'RepositoryPoint')
            require(parent['generationId'] == point['generationId'], 'REPOSITORY_CONTENT_OWNER_MISMATCH')
            manifest, _ = self.manifest(parent)
            owned_payloads.extend(manifest['payloadRefs'])
        for sha, reference in index['contentPins'].items():
            self.contained(reference, self.archives)
            require(reference['sha256'] == sha and reference in owned_payloads and
                    any(root in Path(reference['path']).parents for root in allowed_archives),
                    'REPOSITORY_CONTENT_OWNER_MISMATCH')
            require(pin_file(reference['path'], self.deadline) == reference, 'REPOSITORY_OBJECT_CONTENT_CHANGED')
        return value

    def chain(self, pin):
        point, manifest = self.load(pin)
        parents = point['parentPointPins']
        require(type(parents) is list and len(parents) + 1 <= self.config.policy['maxChainPoints'], 'REPOSITORY_NEW_FULL_REQUIRED')
        require(len({item['path'] for item in parents + [pin]}) == len(parents) + 1, 'REPOSITORY_CHAIN_CYCLE')
        chain = []
        generation = point['generationId']
        prior_time = None
        for index, reference in enumerate(parents + [pin]):
            candidate, metadata = self.load(reference)
            require(candidate['generationId'] == generation and candidate['parentPointPins'] == parents[:index], 'REPOSITORY_CHAIN_INVALID')
            require(candidate['pointType'] == ('FULL' if index == 0 else 'INCREMENTAL'), 'REPOSITORY_CHAIN_BASELINE_REQUIRED')
            created = timestamp(metadata['createdAt'])
            require(prior_time is None or created > prior_time, 'REPOSITORY_CHAIN_ORDER_INVALID')
            prior_time = created
            chain.append((reference, candidate, metadata))
        require((timestamp(manifest['createdAt']) - timestamp(chain[0][2]['createdAt'])).total_seconds() <= self.config.policy['maxChainAgeSeconds'], 'REPOSITORY_NEW_FULL_REQUIRED')
        return chain

    def grade(self, pin, report_pin=None):
        # A damaged pin cannot be converted to a successful placeholder record.
        point = document(read_pin(pin))
        self.config.validate(point, 'RepositoryPoint')
        point = dict(point, rehearsalEligible=False, controlledRestoreEligible=False, blockedReason=None)
        try:
            chain = self.chain(pin)
        except (RepositoryError, FileNotFoundError) as error:
            point['integrityState'] = 'CORRUPT' if isinstance(error, RepositoryError) and error.code in ('REPOSITORY_PAYLOAD_CORRUPT', 'REPOSITORY_PIN_CHANGED', 'REPOSITORY_PAYLOAD_SET_MISMATCH') else 'INCOMPLETE'
            point['blockedReason'] = error.code if isinstance(error, RepositoryError) else 'REPOSITORY_CHAIN_OR_EVIDENCE_MISSING'
            return point
        point['rehearsalEligible'] = True
        point['blockedReason'] = 'REPOSITORY_CURRENT_RECOVERY_PASSED_REQUIRED'
        if report_pin is not None:
            report = document(read_pin(report_pin))
            self.config.validate(report, 'RecoveryVerificationReport')
            source_scope = self.binding(pin)['sourceScopePin']
            scope = document(read_pin(source_scope))
            if report['verdict'] != 'PASSED' or report['invalidatedBy'] != [] or report['backupAndChainPins'] != [item[0] for item in chain] or report['sourceScopePin'] != source_scope or scope['sourceIdentityPin'] != self.config.policy['sourceIdentityPin']:
                point['blockedReason'] = 'REPOSITORY_RECOVERY_REPORT_MISMATCH'
                point['rehearsalEligible'] = False
                return point
            for field in ('planPin', 'targetIdentityPin', 'sourceScopePin', 'restoreResultPin', 'applicationStartPin'):
                read_pin(report[field])
            for field in ('toolAndVersionPins', 'dataEvidencePins', 'playwrightEvidencePins'):
                require(report[field], 'REPOSITORY_RECOVERY_REPORT_EVIDENCE_REQUIRED')
                for evidence_pin in report[field]:
                    read_pin(evidence_pin)
            require(all(pin in self.config.policy['supportedToolPins'] + self.config.policy['supportedVersionPins'] for pin in report['toolAndVersionPins']), 'REPOSITORY_RECOVERY_TOOL_VERSION_MISMATCH')
            for field in ('rtoObservation', 'rpoObservation'):
                observation = report[field]
                require(observation['state'] == 'MEASURED' and type(observation['observedMilliseconds']) is int and type(observation['objectiveMilliseconds']) is int and observation['observedMilliseconds'] <= observation['objectiveMilliseconds'] and observation['evidencePins'], 'REPOSITORY_RECOVERY_OBJECTIVE_UNPROVEN')
                for evidence_pin in observation['evidencePins']:
                    read_pin(evidence_pin)
            # An explicit authority approval authenticates this report and current window.
            approved = False
            for approval_pin in self.config.value['recoveryApprovalPins']:
                approval = signed_pin(approval_pin, self.config.value['authorityKeyPins'])
                exact(approval, 'schemaVersion repositoryId reportPin targetIdentityPin sourceIdentityPin validUntil', 'RepositoryRecoveryApproval/v1')
                approved |= (approval['repositoryId'] == self.config.value['repositoryId'] and approval['reportPin'] == report_pin and approval['targetIdentityPin'] == report['targetIdentityPin'] and approval['sourceIdentityPin'] == self.config.policy['sourceIdentityPin'] and timestamp(approval['validUntil']) > datetime.now(timezone.utc))
            if not approved:
                point['blockedReason'] = 'REPOSITORY_POST_VERIFICATION_APPROVAL_REQUIRED'
                return point
            point.update(controlledRestoreEligible=True, blockedReason=None)
        return point

    def list(self, report_pin=None):
        rows = []
        # The immutable archive sidecars are the catalog; no index/database dependency.
        for archive in sorted(self.archives.iterdir()):
            safe_path(archive)
            require(archive.is_dir(), 'REPOSITORY_UNRECOGNIZED_ARCHIVE_ENTRY')
            point_path = archive / '.repository' / 'point.json'
            if point_path.exists():
                try:
                    pin = pin_file(point_path, self.deadline)
                    rows.append((pin, self.grade(pin, report_pin)))
                except (RepositoryError, FileNotFoundError) as error:
                    rows.append((None, {'archivePath': archive.as_posix(), 'integrityState': 'CORRUPT', 'blockedReason': error.code if isinstance(error, RepositoryError) else 'REPOSITORY_POINT_ORIGINAL_MISSING', 'rehearsalEligible': False, 'controlledRestoreEligible': False}))
            else:
                # Failed/unfinished copies remain explicit inventory entries, never candidates.
                rows.append((None, {'archivePath': archive.as_posix(), 'integrityState': 'INCOMPLETE', 'blockedReason': 'REPOSITORY_UNSEALED_ARCHIVE', 'rehearsalEligible': False, 'controlledRestoreEligible': False}))
        return rows

    def register(self, publication, request):
        exact(publication, 'schemaVersion manifestPin readbackEvidencePin ownerCloseEvidencePin originalExitEvidencePin actualExitCode recoveryMaterialPin objectContentIndexPin sourceScopePin', 'RepositoryPublication/v1')
        manifest_pin = publication['manifestPin']
        manifest = document(read_pin(manifest_pin))
        require(publication['actualExitCode'] == 0 and type(publication['actualExitCode']) is int, 'REPOSITORY_PUBLISHER_EXIT_FAILED')
        require(manifest['pointType'] == ('FULL' if request['action'] == 'BACKUP_FULL' else 'INCREMENTAL'), 'REPOSITORY_CAPTURE_KIND_MISMATCH')
        expected_parents = []
        if request['action'] == 'BACKUP_INCREMENTAL':
            require(request['selectedPointPin'] is not None, 'REPOSITORY_INCREMENTAL_PARENT_REQUIRED')
            expected_parents = [item[0] for item in self.chain(request['selectedPointPin'])]
        require(manifest['parentPointPins'] == expected_parents, 'REPOSITORY_CAPTURE_PARENT_MISMATCH')
        point = {key: manifest[key] for key in ('backupId', 'generationId', 'pointType', 'parentPointPins', 'commonRecoveryPoint', 'payloadRefs')}
        point.update(schemaVersion='RepositoryPoint/v1', manifestPin=manifest_pin,
                     readbackEvidencePin=publication['readbackEvidencePin'], ownerCloseEvidencePin=publication['ownerCloseEvidencePin'], originalExitEvidencePin=publication['originalExitEvidencePin'], integrityState='COMPLETE', blockedReason='REPOSITORY_CURRENT_RECOVERY_PASSED_REQUIRED', rehearsalEligible=True, controlledRestoreEligible=False)
        self.config.validate(point, 'RepositoryPoint')
        metadata, archive = self.manifest(point)
        self.payload(point, metadata, archive)
        self.evidence(point)
        path = archive / '.repository' / 'point.json'
        # Validate the whole proposed chain before the final COMPLETE sidecar is written.
        if expected_parents:
            baseline = self.load(expected_parents[0])[1]
            require(manifest['generationId'] == self.load(expected_parents[-1])[0]['generationId'] and len(expected_parents) + 1 <= self.config.policy['maxChainPoints'] and 0 < (timestamp(manifest['createdAt']) - timestamp(self.load(expected_parents[-1])[1]['createdAt'])).total_seconds() and (timestamp(manifest['createdAt']) - timestamp(baseline['createdAt'])).total_seconds() <= self.config.policy['maxChainAgeSeconds'], 'REPOSITORY_NEW_FULL_REQUIRED')
        self.config.current()
        raw = canonical(point)
        proposed_pin = dict(path=path.as_posix(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        binding = repository_binding(self.config, proposed_pin, point,
                                     publication['recoveryMaterialPin'], publication['objectContentIndexPin'])
        require(binding['sourceScopePin'] == publication['sourceScopePin'], 'REPOSITORY_CAPTURE_BINDING_INVALID')
        write_new(archive / '.repository' / 'recovery-repository-binding.json', binding)
        self.binding(proposed_pin, point)
        self.config.authorization(request, request['sourceOrTargetRef'])
        result_pin = write_new(path, point)
        require(result_pin == proposed_pin, 'REPOSITORY_POINT_PUBLICATION_CHANGED')
        return result_pin, point
