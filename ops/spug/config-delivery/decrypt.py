"""Decrypt a Spug configuration snapshot without printing secret contents.

Requires cryptography. Output must be a new directory. This never installs files
into a running Spug service or starts an execution bridge.
"""
import argparse
import base64
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b'SPUG-CONFIG-AES256GCM-v1\n'


def decrypt_payload(package, key_document):
    key = base64.b64decode(key_document['keyBase64'], validate=True)
    if key_document['schemaVersion'] != 'SpugConfigurationKey/v1' or len(key) != 32:
        raise ValueError('CONFIGURATION_KEY_INVALID')
    if not package.startswith(MAGIC) or len(package) < len(MAGIC) + 28:
        raise ValueError('ENCRYPTED_CONFIGURATION_FORMAT_INVALID')
    offset = len(MAGIC)
    return AESGCM(key).decrypt(package[offset:offset + 12], package[offset + 12:], MAGIC)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', required=True, type=Path)
    parser.add_argument('--key-file', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    raw = decrypt_payload(args.package.read_bytes(), json.loads(args.key_file.read_bytes()))
    # Validate every entry before creating the output directory.
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        members = archive.getmembers()
        names = set()
        for item in members:
            path = PurePosixPath(item.name)
            if (not item.isfile() or path.is_absolute() or '..' in path.parts
                    or '\\' in item.name or ':' in item.name or item.name in names
                    or not path.parts or path.parts[0] not in {'state', 'private'}):
                raise ValueError('CONFIGURATION_ARCHIVE_ENTRY_INVALID')
            names.add(item.name)
        args.output.mkdir(parents=False, exist_ok=False, mode=0o700)
        if os.name == 'nt':
            user = subprocess.check_output(['whoami'], text=True).strip()
            subprocess.run(['icacls', str(args.output), '/inheritance:r', '/grant:r',
                            user + ':(OI)(CI)F', '*S-1-5-18:(OI)(CI)F'],
                           check=True, capture_output=True)
        for item in members:
            destination = args.output.joinpath(*PurePosixPath(item.name).parts)
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with destination.open('xb') as target:
                target.write(archive.extractfile(item).read())
            if os.name != 'nt':
                destination.chmod(0o600)
    print(json.dumps({'decrypted': True, 'files': len(members),
                      'installed': False, 'runtimeReadinessVerified': False}))


if __name__ == '__main__':
    main()
