"""Load the verified standalone epoch writer in the actual flock owner's PID."""
import ast
import hashlib
import importlib
import os
from pathlib import Path
import stat
import sys
import sysconfig
import types


def initialize_epoch_in_lock_owner(module_pin, policy, lock_fd):
    path = Path(module_pin['path'])
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError('EPOCH_INITIALIZER_MODULE_CHANGED')
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
        raise ValueError('EPOCH_INITIALIZER_MODULE_CHANGED')
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise ValueError('EPOCH_INITIALIZER_MODULE_CHANGED')
        raw = stream.read()
    after = path.lstat()
    fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
    actual = dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    if actual != module_pin or any(getattr(before, key) != getattr(after, key) for key in fields):
        raise ValueError('EPOCH_INITIALIZER_MODULE_CHANGED')
    tree = ast.parse(raw, filename=str(path))
    allowed = {'datetime', 'hashlib', 'json', 'os', 'pathlib', 're', 'stat', 'sys', 'fcntl'}
    dependencies = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            dependencies.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level or node.module is None:
                raise ValueError('EPOCH_INITIALIZER_DEPENDENCY_CHANGED')
            dependencies.add(node.module)
    if not dependencies <= allowed:
        raise ValueError('EPOCH_INITIALIZER_DEPENDENCY_CHANGED')
    stdlib = Path(sysconfig.get_path('stdlib')).resolve()
    origins = {}
    for name in sorted(dependencies):
        dependency = importlib.import_module(name)
        origin = getattr(getattr(dependency, '__spec__', None), 'origin', None)
        if origin not in ('built-in', 'frozen'):
            if not origin:
                raise ValueError('EPOCH_INITIALIZER_DEPENDENCY_CHANGED')
            resolved = Path(origin).resolve()
            if stdlib not in resolved.parents or any(part in ('site-packages', 'dist-packages') for part in resolved.parts):
                raise ValueError('EPOCH_INITIALIZER_DEPENDENCY_CHANGED')
        origins[name] = origin
    # This unique module never consults an old recovery_backup_epoch cache or pyc.
    module = types.ModuleType('_task_pinned_backup_epoch_' + actual['sha256'])
    module.__file__ = str(path)
    exec(compile(tree, str(path), 'exec'), module.__dict__)
    epoch = module.initialize(policy, lock_fd)
    return dict(epoch=epoch, modulePin=actual, initializerPid=os.getpid(),
                dependencyOrigins=origins, loadedFromVerifiedSource=True)
