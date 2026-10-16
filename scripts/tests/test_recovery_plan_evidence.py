"""Trust and malformed chain gates; generated keys are only local protocol data."""
import base64
from pathlib import Path
import sys

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'ops'/'recovery'))
from recovery_engine import RecoveryError, canonical, pin, write
from recovery_plan import signed_evidence
from recovery_data import ordered_segments


def test_repository_signed_evidence_is_verified_from_provisioned_key(tmp_path):
    key = Ed25519PrivateKey.generate(); path=tmp_path/'public.pem'
    path.write_bytes(key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo))
    public = pin(path); policy={'repositoryEvidenceKeyPins':[public]}; payload={'actualExitCode':0}
    envelope=dict(schemaVersion='RepositorySignedRecord/v1',keySha256=public['sha256'],payload=payload,
                  signature=base64.b64encode(key.sign(canonical(payload))).decode())
    ref=write(tmp_path/'evidence.json',envelope); assert signed_evidence(ref,policy) == payload
    envelope['payload']={'actualExitCode':1}; ref=write(tmp_path/'evidence.json',envelope)
    with pytest.raises(InvalidSignature): signed_evidence(ref,policy)


def test_repository_unsigned_claim_cannot_create_trust(tmp_path):
    ref=write(tmp_path/'claim.json',{'schemaVersion':'RepositoryOriginalExit/v1','actualExitCode':0})
    with pytest.raises(RecoveryError,match='SIGNED_REPOSITORY_EVIDENCE_REQUIRED'):
        signed_evidence(ref,{'repositoryEvidenceKeyPins':[]})


def test_binlog_gaps_are_rejected_before_import(tmp_path):
    path=tmp_path/'binlog';path.write_bytes(b'local continuity input');ref=pin(path)
    material={'payloadPins':[ref], 'database': {'startPosition':{'file':'mysql-bin.000001','position':4},
        'endPosition':{'file':'mysql-bin.000001','position':100}, 'segments':[{'payloadPin':ref,
        'startPosition':{'file':'mysql-bin.000001','position':20},'endPosition':{'file':'mysql-bin.000001','position':100}}]}}
    with pytest.raises(RecoveryError,match='BINLOG_SEGMENT_GAP_OR_REVERSED'): ordered_segments(material)
