"""Closed, manifest-bound imports for isolated frozen-candidate tests only."""
import hashlib
import importlib.abc
from importlib.machinery import PathFinder
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys


_SHA = re.compile(r'[0-9a-f]{64}\Z')
_PRODUCT_PREFIXES = ('recovery_', 'repository_', 'formal_', 'minimal_')
_MEMBER_LIMIT = 64 * 1024 * 1024
_TOTAL_LIMIT = 256 * 1024 * 1024


def _need(condition, code):
    if not condition:
        raise RuntimeError(code)


def _regular(path, code):
    try:
        info = path.lstat()
    except FileNotFoundError:
        raise RuntimeError('CANDIDATE_MEMBER_MISSING') from None
    _need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, code)
    _need(info.st_size <= _MEMBER_LIMIT, 'CANDIDATE_SIZE_LIMIT')
    return info


class _CandidateImports(importlib.abc.MetaPathFinder):
    def __init__(self, engine, package_pin):
        self.engine = Path(engine).absolute()
        _need(self.engine.is_dir() and not self.engine.is_symlink(),
              'CANDIDATE_ROOT_INVALID')
        _need(self.engine.resolve() == self.engine, 'CANDIDATE_ROOT_INVALID')
        self.package_path = self.engine / 'package.json'
        _need(isinstance(package_pin, dict) and
              set(package_pin) == {'path', 'bytes', 'sha256'},
              'CANDIDATE_MANIFEST_PIN_INVALID')
        _need(package_pin['path'] == str(self.package_path) and
              type(package_pin['bytes']) is int and package_pin['bytes'] > 0 and
              isinstance(package_pin['sha256'], str) and
              _SHA.fullmatch(package_pin['sha256']),
              'CANDIDATE_MANIFEST_PIN_INVALID')
        self.package_pin = dict(package_pin)
        _regular(self.package_path, 'CANDIDATE_MEMBER_INVALID')
        self.package_raw = self.package_path.read_bytes()
        self._verify_package_pin()
        try:
            self.manifest = json.loads(self.package_raw)
        except (ValueError, UnicodeDecodeError):
            raise RuntimeError('CANDIDATE_MANIFEST_INVALID') from None
        _need(isinstance(self.manifest, dict), 'CANDIDATE_MANIFEST_INVALID')
        files = self.manifest.get('files')
        _need(isinstance(files, dict) and bool(files), 'CANDIDATE_MANIFEST_INVALID')
        _need(self.manifest.get('candidateOnly') is True and
              self.manifest.get('source') == 'isolated-frozen-candidate-test' and
              isinstance(self.manifest.get('candidateSourceSnapshotSha256'), str) and
              _SHA.fullmatch(self.manifest['candidateSourceSnapshotSha256']),
              'CANDIDATE_IDENTITY_INVALID')
        encoded = json.dumps(files, sort_keys=True, separators=(',', ':')).encode()
        _need(hashlib.sha256(encoded).hexdigest() == self.manifest.get('packageSha256'),
              'CANDIDATE_MANIFEST_DIGEST_CHANGED')
        self.files = dict(files)
        self.modules = {}
        self.directories = set()
        for name, digest in self.files.items():
            _need(isinstance(name, str) and name and '\\' not in name and
                  ':' not in name, 'CANDIDATE_MEMBER_PATH_INVALID')
            relative = PurePosixPath(name)
            _need(not relative.is_absolute() and str(relative) == name and
                  all(p not in ('.', '..', '') for p in relative.parts) and
                  name != 'package.json', 'CANDIDATE_MEMBER_PATH_INVALID')
            _need(isinstance(digest, str) and _SHA.fullmatch(digest),
                  'CANDIDATE_MANIFEST_INVALID')
            self.directories.update(str(p) for p in relative.parents if str(p) != '.')
            if (len(relative.parts) == 2 and relative.parts[0] in
                    ('common', 'formal', 'control') and relative.suffix == '.py'):
                module = relative.stem
                _need(module.isidentifier() and module not in self.modules,
                      'CANDIDATE_MODULE_COLLISION')
                self.modules[module] = self.engine / name
        self.entered = False
        self.verify()

    def _verify_package_pin(self):
        raw = self.package_path.read_bytes()
        _need(len(raw) == self.package_pin['bytes'] and
              hashlib.sha256(raw).hexdigest() == self.package_pin['sha256'],
              'CANDIDATE_MANIFEST_CHANGED')

    def _verify_member(self, name):
        path = self.engine / name
        info = _regular(path, 'CANDIDATE_MEMBER_INVALID')
        _need(hashlib.sha256(path.read_bytes()).hexdigest() == self.files[name],
              'CANDIDATE_MEMBER_CHANGED')
        return info.st_size

    def verify(self):
        self._verify_package_pin()
        total = len(self.package_raw)
        for name in self.files:
            total += self._verify_member(name)
            _need(total <= _TOTAL_LIMIT, 'CANDIDATE_SIZE_LIMIT')
        actual_files, actual_directories = set(), set()
        for path in self.engine.rglob('*'):
            relative = path.relative_to(self.engine).as_posix()
            info = path.lstat()
            if stat.S_ISDIR(info.st_mode):
                actual_directories.add(relative)
            else:
                _need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                      'CANDIDATE_MEMBER_INVALID')
                actual_files.add(relative)
        _need(actual_files == set(self.files) | {'package.json'} and
              actual_directories == self.directories,
              'CANDIDATE_FILE_SET_CHANGED')
        for name, path in self.modules.items():
            module = sys.modules.get(name)
            if module is not None:
                origin = getattr(module, '__file__', None)
                _need(isinstance(origin, str) and Path(origin).resolve() == path,
                      'CANDIDATE_MODULE_PRELOADED')

    def __enter__(self):
        _need(not self.entered, 'CANDIDATE_ROUTER_ALREADY_ENTERED')
        self.verify()
        self.entered = True
        sys.meta_path.insert(0, self)
        return self

    def find_spec(self, fullname, path=None, target=None):
        candidate = self.modules.get(fullname)
        if candidate is None:
            _need(not fullname.startswith(_PRODUCT_PREFIXES),
                  'CANDIDATE_MODULE_UNDECLARED')
            return None
        self._verify_member(candidate.relative_to(self.engine).as_posix())
        spec = PathFinder.find_spec(fullname, [str(candidate.parent)])
        _need(spec is not None and spec.origin is not None and
              Path(spec.origin).resolve() == candidate,
              'CANDIDATE_MODULE_ORIGIN_CHANGED')
        return spec

    def __exit__(self, error_type, error, traceback):
        try:
            self.verify()
        except RuntimeError as drift:
            if error is None:
                raise
            error.add_note(str(drift))
        finally:
            sys.meta_path[:] = [finder for finder in sys.meta_path if finder is not self]
            self.entered = False
        return False


def candidate_imports(engine, package_pin):
    return _CandidateImports(engine, package_pin)
