"""Explicit operator quarantine preserves archive originals and execution history."""
from datetime import datetime
from pathlib import Path
import re

from recovery_control_smallapp import exact, local_read, need, opaque


def quarantined(native, config, reference, source_ref, binding_pin):
    path = Path(config['registryRoot']) / 'quarantined-points' / (opaque(reference) + '.json')
    if not path.exists() and not path.is_symlink():
        return False
    value = local_read(path)
    exact(value, 'schemaVersion reference sourceConfigRef pointBindingPin reasonCode evidencePin quarantinedAt',
          'POINT_QUARANTINE_FIELDS_INVALID')
    need(value['schemaVersion'] == 'SmallAppPointQuarantine/v1' and value['reference'] == reference and
         value['sourceConfigRef'] == source_ref and value['pointBindingPin'] == binding_pin,
         'POINT_QUARANTINE_BINDING_CHANGED')
    need(value['reasonCode'] in {'RECOVERY_METADATA_DIGEST_INVALID', 'BUSINESS_RESTORE_MISMATCH'},
         'POINT_QUARANTINE_REASON_INVALID')
    stamp = value['quarantinedAt']
    need(type(stamp) is str and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z', stamp),
         'POINT_QUARANTINE_TIME_INVALID')
    datetime.fromisoformat(stamp.replace('Z', '+00:00'))
    evidence = native.document(value['evidencePin'])
    if value['reasonCode'] == 'BUSINESS_RESTORE_MISMATCH':
        exact(evidence, 'schemaVersion reference sourceConfigRef pointBindingPin sourceSnapshotPin restoredSnapshotPin',
              'POINT_QUARANTINE_EVIDENCE_INVALID')
        need(evidence['schemaVersion'] == 'SmallAppBusinessRestoreMismatch/v1' and
             evidence['reference'] == reference and evidence['sourceConfigRef'] == source_ref and
             evidence['pointBindingPin'] == binding_pin, 'POINT_QUARANTINE_EVIDENCE_INVALID')
        source = native.document(evidence['sourceSnapshotPin'])
        restored = native.document(evidence['restoredSnapshotPin'])
        def contents(snapshot):
            return sorted([(r['title'], r['content'], sorted((f['name'], f['bytes'], f['sha256'])
                           for f in r['files'])) for r in snapshot['records']])
        need(source['tenant'] == restored['tenant'] and contents(source) != contents(restored),
             'POINT_QUARANTINE_BUSINESS_MISMATCH_NOT_PROVEN')
        return True
    exact(evidence, 'schemaVersion reference sourceConfigRef pointBindingPin invalidPin actualSha256',
          'POINT_QUARANTINE_EVIDENCE_INVALID')
    need(evidence['schemaVersion'] == 'SmallAppPointDigestMismatch/v1' and
         evidence['reference'] == reference and evidence['sourceConfigRef'] == source_ref and
         evidence['pointBindingPin'] == binding_pin, 'POINT_QUARANTINE_EVIDENCE_INVALID')
    import recovery_control_executor as executor
    executor.pin_reference(evidence['invalidPin'])
    need(type(evidence['actualSha256']) is str and re.fullmatch('[0-9a-f]{64}', evidence['actualSha256']) and
         evidence['invalidPin']['sha256'] != evidence['actualSha256'], 'POINT_QUARANTINE_EVIDENCE_INVALID')
    return True
