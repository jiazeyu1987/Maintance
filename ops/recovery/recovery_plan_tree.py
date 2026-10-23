"""Whole archived tree verification using W03's exact file|bytes|sha encoding."""
import os
from pathlib import Path
import re

from recovery_engine import absolute, check_pin, pin, pinned_json, require


def archived_tree(point, manifest, *, verify_content=True):
    path = absolute(point['manifestPin']['path'])
    require(path.name == 'manifest.json' and path.parent.name == '.repository', 'MANIFEST_ARCHIVE_LOCATION_INVALID')
    archive = path.parent.parent
    tree = pinned_json(manifest['payloadTreePin'])
    require(absolute(manifest['payloadTreePin']['path']).parent == path.parent and type(tree) is dict and tree,
            'COMPLETE_ARCHIVED_TREE_REQUIRED')
    expected = set(); files = {}; folded = set()
    if not verify_content:
        for ref in point['payloadRefs']:
            require(absolute(ref['path']).is_relative_to(archive), 'ARCHIVED_TREE_ESCAPED')
        return archive
    for relative, spec in tree.items():
        require(type(relative) is str and relative and not re.search(r'[\\:*?"<>|\x00-\x1f]', relative) and
                all(part not in ('', '.', '..', '.repository') for part in relative.split('/')) and
                not relative.startswith('/'), 'ARCHIVED_TREE_RELATIVE_PATH_INVALID')
        require(relative.casefold() not in folded, 'ARCHIVED_TREE_CASE_COLLISION')
        folded.add(relative.casefold())
        item = absolute(str(archive/relative)); require(item.is_relative_to(archive), 'ARCHIVED_TREE_ESCAPED')
        expected.add(relative)
        if spec == 'directory':
            require(item.is_dir(), 'ARCHIVED_DIRECTORY_CHANGED')
        else:
            require(type(spec) is str and re.fullmatch(r'file\|(0|[1-9][0-9]*)\|[0-9a-f]{64}', spec), 'ARCHIVED_FILE_ENTRY_INVALID')
            _, size, sha = spec.split('|'); ref = dict(path=str(item), bytes=int(size), sha256=sha)
            if verify_content:
                check_pin(ref, content=False)
            else:
                require(item.is_file() and item.stat().st_size == int(size), 'PIN_CHANGED')
            files[relative] = ref
    observed = set()
    for root, dirs, names in os.walk(archive, followlinks=False):
        if Path(root) == archive: dirs[:] = [name for name in dirs if name != '.repository']
        for name in dirs+names:
            item = absolute(str(Path(root)/name)); observed.add(item.relative_to(archive).as_posix())
    require(expected == observed and files and [files[name] for name in sorted(files)] == point['payloadRefs'],
            'COMPLETE_ARCHIVED_PAYLOAD_SET_MISMATCH')
    return archive
