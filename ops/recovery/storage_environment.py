"""Shared data-disk layout for backup configuration and new restore targets."""
import argparse
import json
from pathlib import PurePosixPath


def storage_layout(environment, target_id):
    root = PurePosixPath(environment['dataRoot'])
    repository = PurePosixPath(environment['repositoryRoot'])
    if not root.is_absolute() or root == PurePosixPath('/') or '..' in root.parts:
        raise ValueError('Explicit absolute dataRoot required')
    if not repository.is_absolute() or '..' in repository.parts:
        raise ValueError('Explicit absolute repositoryRoot required')
    if not target_id or target_id in ('.', '..') or '/' in target_id or '\\' in target_id:
        raise ValueError('Single target directory name required')
    target = root / target_id
    mounts = {role: dict(type='bind', source=str(target/'data'/role), destination=destination)
              for role, destination in [('mysql', '/var/lib/mysql'), ('minio', '/data'), ('redis', '/data')]}
    return dict(dataRoot=str(root), captureStagingRoot=str(root/'capture-staging'),
                repositoryOperationsRoot=str(root/'repository-operations'),
                recoveryOperationsRoot=str(root/'recovery-operations'),
                repositoryRoot=str(repository), targetRoot=str(target), mounts=mounts)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environment', required=True)
    parser.add_argument('--target', required=True)
    args = parser.parse_args()
    with open(args.environment, encoding='utf-8') as stream:
        print(json.dumps(storage_layout(json.load(stream), args.target), indent=2))
