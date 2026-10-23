"""Reuse a Docker export by image IDs, without lightweight file verification.

Each backup still contains its own tar: deleting an older backup or this cache
cannot break a newer restore. Actual read/export failures remain errors.
"""
import hashlib
import os
from pathlib import Path
import stat
import subprocess
import uuid

from formal_capture_budget import drain_owned_process
from minimal_capture_support import canonical, document, exclusive_json, path_checked
from formal_snapshot_linux import require


def capture_images(config, destination, budget, validate_export, *, result=None):
    import fcntl
    images = sorted(config['source']['applicationImageIds'])
    cache = path_checked(config['archiveRoot'], directory=True)/'.image-exports'
    cache.mkdir(mode=0o700, exist_ok=True)
    path_checked(str(cache), directory=True)
    key = hashlib.sha256(canonical(images)).hexdigest()
    entry = cache/key
    archive = entry/'images.tar'
    metadata = entry/'metadata.json'
    lock = os.open(cache/(key+'.lock'), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        require(stat.S_ISREG(os.fstat(lock).st_mode) and os.fstat(lock).st_nlink == 1,
            'MINIMAL_IMAGE_CACHE_LOCK_INVALID')
        # Do not wait indefinitely behind another export while holding source ownership.
        try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            require(False, 'MINIMAL_IMAGE_EXPORT_BUSY')
        budget.check()
        reused = entry.exists()
        if reused:
            value, _ = document(metadata)
            require(value.get('imageIds') == images and set(value) == {'imageIds', 'archivePin'} and
                value['archivePin']['path'] == str(archive), 'MINIMAL_IMAGE_CACHE_INVALID')
            expected = value['archivePin']
        else:
            pending = cache/(key+'.'+uuid.uuid4().hex+'.pending')
            pending.mkdir(mode=0o700)
            temporary = pending/'images.tar'
            pending_metadata = pending/'metadata.json'
            try:
                export_sha = hashlib.sha256(); export_bytes = 0
                with temporary.open('xb') as output:
                    os.chmod(temporary, 0o600)
                    class Sink:
                        def write(self, block):
                            nonlocal export_bytes
                            budget.check()
                            require(budget.written+len(block) <= budget.maximum, 'MINIMAL_WRITE_LIMIT')
                            size = output.write(block)
                            budget.written += size
                            require(size == len(block), 'MINIMAL_SHORT_WRITE')
                            export_sha.update(block); export_bytes += size
                    child = subprocess.Popen(['docker', 'image', 'save', *images],
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    drain_owned_process(child, b'', Sink(), guard=budget.check, deadline=budget.deadline)
                    output.flush(); os.fsync(output.fileno())
                measured = dict(path=str(temporary), bytes=export_bytes, sha256=export_sha.hexdigest())
                expected = dict(measured, path=str(archive))
                exclusive_json(pending_metadata, dict(imageIds=images, archivePin=expected))
                # Publish both files together; an interrupted export is never a cache entry.
                os.rename(pending, entry)
            finally:
                if pending.exists():
                    if temporary.exists(): temporary.unlink()
                    if pending_metadata.exists(): pending_metadata.unlink()
                    pending.rmdir()
        # Hash the bytes being copied, not a separate cached file pass. No hard
        # links: each backup remains independently owned and single-linked.
        path_checked(str(archive))
        checksum = hashlib.sha256(); total = 0
        with archive.open('rb') as incoming, budget.open(destination, 'images') as output:
            while block := incoming.read(1024*1024):
                total += len(block)
                checksum.update(block); output.write(block)
            output.flush(); os.fsync(output.fileno())
        if result is not None:
            result.update(path=str(destination), bytes=total, sha256=checksum.hexdigest())
        return reused
    finally:
        os.close(lock)
