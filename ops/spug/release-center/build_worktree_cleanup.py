"""Remove only an unchanged, detached, registered build checkout owned by a job."""
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess

import psutil

from executor import require


def _git(repo, *args):
    result = subprocess.run(['git', '-c', 'core.longpaths=true', '-C', str(repo), *args],
                            capture_output=True, timeout=120)
    require(result.returncode == 0, 'Build worktree Git verification failed; checkout preserved')
    return result.stdout


def _long(path):
    text = str(Path(path).absolute())
    if os.name != 'nt' or text.startswith('\\\\?\\'):
        return text
    return '\\\\?\\UNC\\'+text[2:] if text.startswith('\\\\') else '\\\\?\\'+text


def _linked(path):
    attributes = os.lstat(path)
    return stat.S_ISLNK(attributes.st_mode) or bool(getattr(attributes, 'st_file_attributes', 0) & 0x400)


def _registration(repo, target):
    rows = _git(repo, 'worktree', 'list', '--porcelain', '-z').decode('utf-8').split('\0')
    records = []; current = {}
    for row in rows:
        if row.startswith('worktree '):
            if current: records.append(current)
            current = {'path':Path(row[9:]).resolve()}
        elif row.startswith('HEAD '): current['commit'] = row[5:]
        elif row == 'detached': current['detached'] = True
        elif row.startswith('locked'): current['locked'] = True
    if current: records.append(current)
    return next((r for r in records if r['path'] == target), None)


def _consumers(target):
    needle = str(target).replace('\\', '/').casefold()
    for process in psutil.process_iter(['pid']):
        try:
            cwd = process.cwd().replace('\\', '/').casefold().rstrip('/')
            args = process.cmdline()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
        # The caller's cwd is checked too; deleting its own source is forbidden.
        if cwd == needle or cwd.startswith(needle+'/') or (process.pid != os.getpid() and any(
                needle in arg.replace('\\', '/').casefold() for arg in args)):
            raise ValueError('Build worktree still has a process consumer; checkout preserved')


def _generated_links(directory):
    """Git's Windows removal can traverse junctions even with longpaths enabled."""
    pending = [str(directory)]; links = []
    while pending:
        with os.scandir(pending.pop()) as entries:
            for entry in entries:
                attributes = entry.stat(follow_symlinks=False)
                linked = stat.S_ISLNK(attributes.st_mode) or bool(getattr(attributes,'st_file_attributes',0) & 0x400)
                if linked:
                    links.append((entry.path, bool(getattr(attributes,'st_file_attributes',0) & 0x10)))
                elif entry.is_dir(follow_symlinks=False):
                    pending.append(entry.path)
    return links


def _inspect(target, tree, allow_metadata):
    count = 0; links = []
    for directory, dirs, files in os.walk(_long(target), followlinks=False):
        relative_dir = Path(os.path.relpath(directory, _long(target)))
        for name in list(dirs):
            path = Path(directory)/name
            rel = (relative_dir/name).as_posix()
            if rel.startswith('./'): rel = rel[2:]
            require(name != '.git', 'Embedded Git repository must be preserved')
            generated = (rel in ('IntRuoyiFronted/node_modules', 'IntRuoyiFronted/dist',
                                'IntRuoyiFronted/dist-prod', 'IntRuoyiFronted/dist-intruoyi-test', 'IntRuoyiFronted/.vite')
                         or rel.startswith('IntRuoyiBackend/') and name == 'target')
            require(not _linked(path), 'Directory link must be preserved: '+rel)
            if generated:
                require(not any(p == rel or p.startswith(rel+'/') for p in tree), 'Tracked content in generated directory')
                links.extend(_generated_links(path))
                dirs.remove(name)
        for name in files:
            path = Path(directory)/name
            rel = (relative_dir/name).as_posix()
            if rel.startswith('./'): rel = rel[2:]
            if rel == '.git' and allow_metadata:
                continue
            require(name != '.git' and not _linked(path), 'Linked file or embedded Git metadata must be preserved')
            if rel in tree:
                data = path.read_bytes()
                def blob(value):
                    return hashlib.sha1(b'blob '+str(len(value)).encode()+b'\0'+value).hexdigest()
                require(blob(data) == tree[rel] or blob(data.replace(b'\r\n', b'\n')) == tree[rel],
                        'Build worktree modified tracked source must be preserved: '+rel)
                count += 1
            elif rel.startswith('IntRuoyiBackend/') and name == '.flattened-pom.xml':
                continue
            else:
                bytecode = re.fullmatch(r'(scripts/.+)/__pycache__/([^/]+)\.cpython-\d+\.pyc', rel)
                allowed = False
                if bytecode and bytecode[1]+'/'+bytecode[2]+'.py' in tree:
                    data = path.read_bytes()
                    allowed = len(data) >= 16 and data[:4] == importlib.util.MAGIC_NUMBER and int.from_bytes(data[4:8], 'little') in (0, 1, 3)
                require(allowed, 'Unknown non-generated build file must be preserved: '+rel)
    return count, links


def cleanup_build_worktree(repo, worktree, build_root, commit, *, prior_proof=None, before_remove=None):
    original = Path(worktree).absolute()
    root = Path(build_root).resolve(strict=True)
    exists = os.path.lexists(_long(original))
    require(original.parent.resolve() == root and original != root and (not exists or not _linked(original)),
            'Unsafe build worktree removal path')
    target = original.resolve()
    require(target != Path(repo).resolve() and not Path(repo).resolve().is_relative_to(target),
            'Source repository cannot be removed')
    registered = _registration(repo, target)
    if registered:
        require(registered.get('detached') and not registered.get('locked')
                and registered.get('commit') == commit, 'Build worktree registration or commit differs; preserved')
        require(exists, 'Registered build worktree is missing; inspect it before removal')
        require(_git(target, 'rev-parse', 'HEAD').decode().strip() == commit, 'Build worktree commit changed')
        require(not _git(target, 'status', '--porcelain', '-z', '--untracked-files=all').strip(),
                'Build worktree is dirty; modified/untracked files preserved')
    else:
        require(isinstance(prior_proof, dict) and prior_proof.get('ownershipVerified') is True
                and prior_proof.get('commit') == commit and Path(prior_proof.get('path','')).resolve() == target,
                'Missing build worktree registration and no prior ownership proof; preserved')
    tree = {}
    for row in _git(repo, 'ls-tree', '-r', '-z', commit).split(b'\0'):
        if row:
            identity, name = row.split(b'\t', 1)
            mode, kind, oid = identity.split()
            require(kind == b'blob' and mode in (b'100644', b'100755'), 'Special tracked entries must be preserved')
            tree[name.decode('utf-8')] = oid.decode()
    _consumers(target)
    verified, links = _inspect(target, tree, registered is not None) if exists else (0, [])
    if before_remove:
        before_remove(dict(status='verified', path=str(target), commit=commit, ownershipVerified=True))
    # All source/unknown-file/consumer checks have passed. Remove only link
    # entries, never their targets, before allowing Git to remove dependencies.
    for link, directory_link in links:
        if directory_link:
            os.rmdir(link)
        else:
            os.unlink(link)
    exit_code = None
    if registered:
        removed = subprocess.run(['git', '-c', 'core.longpaths=true', '-C', str(repo),
                                  'worktree', 'remove', '--force', str(target)], capture_output=True, timeout=180)
        exit_code = removed.returncode
    require(_registration(repo, target) is None, 'Build worktree removal did not unregister the checkout; preserved')
    residual = os.path.lexists(_long(target))
    if residual:
        require(not os.path.lexists(_long(target/'.git')), 'Residual Git metadata must be preserved')
        _consumers(target)
        _, residual_links = _inspect(target, tree, False)
        for link, directory_link in residual_links:
            (os.rmdir if directory_link else os.unlink)(link)
        def onerror(function, name, error):
            attributes = os.stat(name, follow_symlinks=False)
            if isinstance(error, PermissionError) and getattr(attributes, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_READONLY:
                os.chmod(name, stat.S_IWRITE)
                function(name)
            else:
                raise error
        shutil.rmtree(_long(target), onexc=onerror)
    require(not os.path.lexists(_long(target)), 'Build worktree physical removal incomplete')
    return dict(status='passed', path=str(target), commit=commit, verifiedTrackedFiles=verified,
                gitRemovalExitCode=exit_code, residualRemoved=residual, ownershipVerified=True,
                generatedLinksDetached=len(links),
                registeredAfter=False, physicalPathExists=False, producedNewCommits=False)
