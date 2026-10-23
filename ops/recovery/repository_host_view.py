"""Explicit filesystem views; a view never changes an original Pin's identity."""
import os
from pathlib import Path, PurePosixPath, PureWindowsPath


def logical(value):
    from repository_records import require
    require(type(value) is str and value and '\x00' not in value,
            'REPOSITORY_ABSOLUTE_PATH_REQUIRED')
    value = value.replace('\\', '/')
    path = PureWindowsPath(value) if PureWindowsPath(value).is_absolute() else PurePosixPath(value)
    require(path.is_absolute() and '..' not in path.parts and '.' not in value.split('/'),
            'REPOSITORY_PATH_INVALID')
    return path


class HostView:
    def __init__(self, reference):
        from repository_records import document, exact, read_pin, require
        self.pin = reference
        reference_path = logical(reference['path'])
        require((os.name == 'nt' and isinstance(reference_path, PureWindowsPath)) or
                (os.name != 'nt' and isinstance(reference_path, PurePosixPath)),
                'REPOSITORY_HOST_VIEW_PIN_MUST_BE_LOCAL')
        value = document(read_pin(reference))
        exact(value, 'schemaVersion mappings', 'RepositoryHostView/v1')
        require(type(value['mappings']) is list and value['mappings'], 'REPOSITORY_HOST_MAPPINGS_REQUIRED')
        self.mappings = []
        for entry in value['mappings']:
            require(type(entry) is dict and set(entry) == {'originalPrefix', 'localPrefix'},
                    'REPOSITORY_HOST_MAPPING_INVALID')
            source, target = logical(entry['originalPrefix']), Path(entry['localPrefix'])
            require(target.is_absolute() and '..' not in target.parts and
                    target.is_dir() and not target.is_symlink(), 'REPOSITORY_HOST_VIEW_ROOT_REQUIRED')
            for old_source, old_target in self.mappings:
                require(not (source == old_source or source in old_source.parents or old_source in source.parents or
                             target == old_target or target in old_target.parents or old_target in target.parents),
                        'REPOSITORY_HOST_MAPPING_OVERLAP')
            self.mappings.append((source, target))

    def resolve(self, value):
        from repository_records import read_pin, require
        read_pin(self.pin)
        source = logical(value)
        matches = [(prefix, target) for prefix, target in self.mappings
                   if source == prefix or prefix in source.parents]
        require(len(matches) == 1, 'REPOSITORY_HOST_PATH_UNMAPPED')
        prefix, target = matches[0]
        return target.joinpath(*source.relative_to(prefix).parts)


_selected = None


def select(reference):
    global _selected
    _selected = None if reference is None else HostView(reference)


def resolve(value):
    original = logical(value)
    # The current host's native namespace needs no cross-host translation.
    if (os.name == 'nt' and isinstance(original, PureWindowsPath)) or (
            os.name != 'nt' and isinstance(original, PurePosixPath)):
        return Path(str(original))
    from repository_records import require
    require(_selected is not None, 'REPOSITORY_HOST_VIEW_REQUIRED')
    return _selected.resolve(value)


def current(reference):
    from repository_records import read_pin, require
    require((_selected is None and reference is None) or
            (_selected is not None and _selected.pin == reference), 'REPOSITORY_HOST_VIEW_CHANGED')
    if reference is not None:
        read_pin(reference)


def original_path(value):
    """Recover identity when filesystem enumeration returns a mapped local view."""
    path = Path(value)
    if _selected is not None and path.is_absolute():
        for original, local in _selected.mappings:
            if path == local or local in path.parents:
                from repository_records import read_pin
                read_pin(_selected.pin)
                return original.joinpath(*path.relative_to(local).parts).as_posix()
    return logical(str(value)).as_posix()


def bootstrap():
    """Private process configuration only; no request or path discovery."""
    from repository_records import pin_file, require
    path = os.environ.get('INTRUOYI_REPOSITORY_HOST_VIEW_PATH')
    digest = os.environ.get('INTRUOYI_REPOSITORY_HOST_VIEW_SHA256')
    require((path is None) == (digest is None), 'REPOSITORY_HOST_VIEW_CONFIG_INCOMPLETE')
    if path is not None:
        reference = pin_file(path)
        require(reference['sha256'] == digest, 'REPOSITORY_HOST_VIEW_CONFIG_CHANGED')
        select(reference)
