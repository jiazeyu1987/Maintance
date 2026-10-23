"""Resolve explicit SQL source references without treating them as migrations.

A reference is never marked applied. Its immutable source bytes are retained,
and a named, executable successor must supply the reviewed release SQL.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re


class SourceCatalogError(ValueError):
    pass


def migration_contracts(sql_root: Path, catalog: dict | None = None) -> list[dict]:
    """Bind reviewed runtime handlers to immutable SQL without editing old headers."""
    if catalog is None:
        path = sql_root / 'release-sources.json'
        if not path.is_file():
            return []
        catalog = json.loads(path.read_text('utf-8-sig'))
    entries = catalog.get('migrationContracts', [])
    if not isinstance(entries, list):
        raise SourceCatalogError('migrationContracts must be a list')
    sources = {name: name for name in catalog.get('migrations', [])}
    sources.update({entry['file']: entry['original'] for entry in catalog.get('historicalMigrations', [])})
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise SourceCatalogError('Migration contract must declare file, checksum, handler and reason')
        name = entry.get('file')
        if name not in sources or name in seen:
            raise SourceCatalogError('Unknown/duplicate migration contract: '+str(name))
        if set(entry) != {'file', 'sha256', 'approvedHook', 'reason'} or entry['approvedHook'] != 'route-snapshot-identity-v1' or name != '20260812_mes_route_version_snapshot_identity_enforce.sql':
            raise SourceCatalogError('Unreviewed migration handler contract: '+str(name))
        if not isinstance(entry['reason'], str) or len(entry['reason'].strip()) < 10:
            raise SourceCatalogError('Migration contract reason required: '+name)
        if hashlib.sha256((sql_root/sources[name]).read_bytes()).hexdigest() != entry['sha256']:
            raise SourceCatalogError('Contract immutable SQL changed: '+name)
        seen.add(name)
    return entries


def apply_migration_contracts(sql_root: Path, migrations: list[dict]) -> None:
    by_id = {entry['migrationId']: entry for entry in migrations}
    for contract in migration_contracts(sql_root):
        identity = Path(contract['file']).stem
        if identity not in by_id or by_id[identity]['sha256'] != contract['sha256']:
            raise SourceCatalogError('Contract migration differs from release inputs: '+identity)
        existing = by_id[identity].get('approvedHook')
        if existing and existing != contract['approvedHook']:
            raise SourceCatalogError('Catalog cannot replace a declared hook: '+identity)
        by_id[identity]['approvedHook'] = contract['approvedHook']


def migration_scopes(sql_root: Path, catalog: dict | None = None) -> list[dict]:
    """Narrow immutable migrations to a reviewed, separate business-data scope."""
    if catalog is None:
        catalog_path = sql_root / 'release-sources.json'
        if not catalog_path.is_file():
            return []
        catalog = json.loads(catalog_path.read_text('utf-8-sig'))
    entries = catalog.get('migrationScopes', [])
    if not isinstance(entries, list):
        raise SourceCatalogError('migrationScopes must be a list')
    sources = {name: name for name in catalog.get('migrations', [])}
    sources.update({entry['file']: entry['original'] for entry in catalog.get('historicalMigrations', [])})
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise SourceCatalogError('Migration scope must declare file, checksum, scope and reason')
        name = entry.get('file')
        if not isinstance(name, str) or name not in sources or name in seen:
            raise SourceCatalogError('Unknown/duplicate migration scope: '+str(name))
        # This registry can only remove automatic application-release eligibility.
        # It does not authorize a new executor or widen a script's declared scope.
        if entry.get('allowedPublishScopes') != ['with-data']:
            raise SourceCatalogError('Catalog migration scope must be explicitly with-data: '+name)
        if not isinstance(entry.get('reason'), str) or len(entry['reason'].strip()) < 10:
            raise SourceCatalogError('Migration scope reason required: '+name)
        source = sql_root / sources[name]
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != entry.get('sha256'):
            raise SourceCatalogError('Scoped immutable migration missing or changed: '+name)
        seen.add(name)
    return entries


def apply_migration_scopes(sql_root: Path, migrations: list[dict]) -> None:
    by_id = {entry['migrationId']: entry for entry in migrations}
    for scope in migration_scopes(sql_root):
        identity = Path(scope['file']).stem
        if identity not in by_id:
            raise SourceCatalogError('Scoped migration is not in release inputs: '+identity)
        migration = by_id[identity]
        original_scopes = migration.get('allowedPublishScopes', [])
        if original_scopes and 'with-data' not in original_scopes:
            raise SourceCatalogError('Catalog cannot widen declared migration scope: '+identity)
        if migration['sha256'] != scope['sha256']:
            raise SourceCatalogError('Scoped migration checksum differs from manifest: '+identity)
        migration['allowedPublishScopes'] = list(scope['allowedPublishScopes'])
        migration['scopeReason'] = scope['reason']


def migration_dependencies(sql_root: Path, catalog: dict | None = None) -> list[dict]:
    """Add reviewed prerequisite edges without rewriting immutable SQL headers."""
    if catalog is None:
        path = sql_root / 'release-sources.json'
        if not path.is_file():
            return []
        catalog = json.loads(path.read_text('utf-8-sig'))
    entries = catalog.get('migrationDependencies', [])
    if not isinstance(entries, list):
        raise SourceCatalogError('migrationDependencies must be a list')
    sources = {name: name for name in catalog.get('migrations', [])}
    sources.update({entry['file']: entry['original'] for entry in catalog.get('historicalMigrations', [])})
    known_ids = {Path(name).stem for name in sources}
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise SourceCatalogError('Migration dependency must declare file, checksum, prerequisites and reason')
        name = entry.get('file')
        if not isinstance(name, str) or name not in sources or name in seen:
            raise SourceCatalogError('Unknown/duplicate dependency migration: '+str(name))
        dependencies = entry.get('dependsOn')
        if not isinstance(dependencies, list) or not dependencies or any(
                not isinstance(mid, str) or mid not in known_ids or mid == Path(name).stem for mid in dependencies):
            raise SourceCatalogError('Known non-self dependency IDs required: '+name)
        if len(dependencies) != len(set(dependencies)):
            raise SourceCatalogError('Duplicate prerequisite: '+name)
        if not isinstance(entry.get('reason'), str) or len(entry['reason'].strip()) < 10:
            raise SourceCatalogError('Migration dependency reason required: '+name)
        source = sql_root / sources[name]
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != entry.get('sha256'):
            raise SourceCatalogError('Dependency migration missing or changed: '+name)
        seen.add(name)
    return entries


def apply_migration_dependencies(sql_root: Path, migrations: list[dict]) -> None:
    by_id = {entry['migrationId']: entry for entry in migrations}
    for dependency in migration_dependencies(sql_root):
        identity = Path(dependency['file']).stem
        if identity not in by_id or any(mid not in by_id for mid in dependency['dependsOn']):
            raise SourceCatalogError('Catalog dependency is not in release inputs: '+identity)
        migration = by_id[identity]
        if migration['sha256'] != dependency['sha256']:
            raise SourceCatalogError('Dependency migration checksum differs from manifest: '+identity)
        migration['dependsOn'] = list(dict.fromkeys(migration['dependsOn'] + dependency['dependsOn']))


def sql_tokens(text: str) -> list[str]:
    """Compare SQL without discarding literals or executable MySQL comments."""
    text = text.replace('\r\n', '\n').replace('\r', '\n').lstrip('\ufeff')
    output, index = [], 0
    while index < len(text):
        char = text[index]
        if char.isspace():
            index += 1
        elif char == '#' or (text.startswith('--', index) and
                              (index+2 == len(text) or text[index+2].isspace())):
            end = text.find('\n', index)
            index = len(text) if end < 0 else end+1
        elif text.startswith('/*', index):
            end = text.find('*/', index+2)
            if end < 0:
                raise SourceCatalogError('Unterminated SQL comment')
            if text.startswith(('/*!', '/*+'), index):
                output.append(text[index:end+2])
            index = end+2
        elif char in "'\"`":
            start, quote = index, char
            index += 1
            while index < len(text):
                if text[index] == '\\':
                    index += 2
                elif text[index] == quote:
                    if index+1 < len(text) and text[index+1] == quote:
                        index += 2
                    else:
                        index += 1
                        break
                else:
                    index += 1
            else:
                raise SourceCatalogError('Unterminated SQL literal')
            output.append(text[start:index])
        else:
            token = re.match(r'[A-Za-z0-9_$]+|<=>|>=|<=|<>|!=|:=|&&|\|\||.', text[index:])[0]
            output.append(token)
            index += len(token)
    return output


def historical_sources(sql_root: Path, catalog: dict) -> list[dict]:
    entries = catalog.get('historicalMigrations', [])
    if not isinstance(entries, list):
        raise SourceCatalogError('historicalMigrations list required')
    names = set()
    originals = set()
    for entry in entries:
        name = entry.get('file', '')
        original = entry.get('original', '')
        if not re.fullmatch(r'20\d{6}_[a-zA-Z0-9_]+\.sql', name) or name in names:
            raise SourceCatalogError('Invalid/duplicate historical source: '+name)
        if original != 'historical/'+name:
            raise SourceCatalogError('Historical original must have the same migration ID: '+name)
        for relative, checksum in ((name, entry.get('sha256')), (original, entry.get('originalSha256'))):
            path = sql_root/relative
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != checksum:
                raise SourceCatalogError('Historical/reviewed source missing or changed: '+relative)
        if not isinstance(entry.get('reason'), str) or len(entry['reason'].strip()) < 10:
            raise SourceCatalogError('Historical disposition reason required: '+name)
        disposition = entry.get('disposition')
        if disposition == 'equivalent':
            if sql_tokens((sql_root/name).read_text('utf-8-sig')) != sql_tokens((sql_root/original).read_text('utf-8-sig')):
                raise SourceCatalogError('Executable SQL changes require forward migrations: '+name)
            if entry.get('successors'):
                raise SourceCatalogError('Equivalent SQL must not declare unnecessary successors: '+name)
        elif disposition == 'forward-migrations':
            successors = entry.get('successors')
            if not isinstance(successors, list) or not successors or len(successors) != len(set(successors)):
                raise SourceCatalogError('Explicit forward migrations required: '+name)
            for successor in successors:
                if not isinstance(successor, str) or not re.fullmatch(r'20\d{6}_[a-zA-Z0-9_]+\.sql', successor) or successor == name:
                    raise SourceCatalogError('Invalid historical successor: '+name)
                path = sql_root/successor
                if not path.is_file():
                    raise SourceCatalogError('Historical successor missing: '+successor)
                metadata = re.search(r'^\s*--\s*release-migration\s*:\s*(.+)$', path.read_text('utf-8-sig'), re.M | re.I)
                if not metadata or not re.search(r'(?:^|;)\s*type=(schema|data|menu|config|permission|seed)(?:;|$)', metadata[1]):
                    raise SourceCatalogError('Historical successor must be executable: '+successor)
        else:
            raise SourceCatalogError('Historical changes are not resolved: '+name)
        names.add(name)
        originals.add(original)
    if {p.relative_to(sql_root).as_posix() for p in (sql_root/'historical').glob('*.sql')} != originals:
        raise SourceCatalogError('Unregistered/missing historical original files')
    return entries


def release_paths(sql_root: Path) -> tuple[list[Path], list[dict]]:
    sql_root = sql_root.resolve()
    path = sql_root / 'release-sources.json'
    if not path.is_file():
        raise SourceCatalogError('Explicit release-sources.json required')
    catalog = json.loads(path.read_text('utf-8-sig'))
    if catalog.get('schemaVersion') != 'release-sql-sources/v2':
        raise SourceCatalogError('Unsupported SQL source catalog')
    migrations = catalog.get('migrations')
    exclusions = catalog.get('excludedSources', [])
    if not isinstance(migrations, list) or not isinstance(exclusions, list):
        raise SourceCatalogError('Explicit migrations and excludedSources lists required')
    registered = set()
    for name in migrations:
        if not isinstance(name, str) or not re.fullmatch(r'20\d{6}_[a-zA-Z0-9_]+\.sql', name) or name in registered:
            raise SourceCatalogError('Invalid/duplicate registered migration: ' + str(name))
        registered.add(name)
    excluded = set()
    for entry in exclusions:
        if not isinstance(entry, dict):
            raise SourceCatalogError('Excluded source must declare file and reason')
        name = entry.get('file', '')
        if not isinstance(name, str) or not re.fullmatch(r'20\d{6}_[a-zA-Z0-9_]+\.sql', name) or name in excluded:
            raise SourceCatalogError('Invalid/duplicate excluded source: ' + str(name))
        if not isinstance(entry.get('reason'), str) or not entry['reason'].strip():
            raise SourceCatalogError('Excluded source reason required: ' + name)
        excluded.add(name)
    references = catalog.get('sourceReferences')
    if not isinstance(references, list):
        raise SourceCatalogError('sourceReferences list required')
    history = historical_sources(sql_root, catalog)
    history_names = {entry['file'] for entry in history}
    names = set()
    for entry in references:
        name = entry.get('file', '')
        replacement = entry.get('replacement', '')
        if not re.fullmatch(r'20\d{6}_[a-zA-Z0-9_]+\.sql', name) or name in names or name in history_names:
            raise SourceCatalogError('Invalid or repeated source reference: ' + name)
        names.add(name)
        source = sql_root / name
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != entry.get('sha256'):
            raise SourceCatalogError('Source reference missing or changed: ' + name)
        if not isinstance(entry.get('reason'), str) or len(entry['reason'].strip()) < 10:
            raise SourceCatalogError('Explicit source disposition reason required: ' + name)
        if entry.get('kind') == 'review-only':
            if sql_tokens(source.read_text('utf-8-sig')) or entry.get('replacement'):
                raise SourceCatalogError('Review-only references must contain no executable SQL or replacement: '+name)
            continue
        if entry.get('kind') == 'rollback-only':
            if not name.endswith('_rollback.sql') or entry.get('replacement'):
                raise SourceCatalogError('Rollback reference must name an explicit rollback without replacement: '+name)
            continue
        if entry.get('kind') not in (None, 'replacement'):
            raise SourceCatalogError('Unknown source reference kind: '+name)
        if not re.fullmatch(r'20\d{6}_[a-zA-Z0-9_]+\.sql', replacement) or replacement == name:
            raise SourceCatalogError('Executable replacement required: ' + name)
        successor = sql_root / replacement
        if not successor.is_file():
            raise SourceCatalogError('Replacement SQL missing: ' + replacement)
        metadata = re.search(r'^\s*--\s*release-migration\s*:\s*(.+)$', successor.read_text('utf-8-sig'), re.M | re.I)
        if not metadata or not re.search(r'(?:^|;)\s*type=(schema|data|menu|config|permission|seed)(?:;|$)', metadata[1]):
            raise SourceCatalogError('Replacement must be an executable migration: ' + replacement)
    if any(x.get('replacement') in names for x in references):
        raise SourceCatalogError('Replacement cannot itself be an excluded source reference')
    categories = [registered, excluded, names, history_names]
    classified = set().union(*categories)
    if sum(len(category) for category in categories) != len(classified):
        raise SourceCatalogError('SQL source has conflicting catalog classifications')
    # Discovery only detects omissions. It never grants a new file release eligibility.
    actual = {candidate.name for candidate in sql_root.glob('20*.sql')}
    unregistered, missing = actual - classified, classified - actual
    if unregistered or missing:
        raise SourceCatalogError('SQL catalog mismatch; unregistered: ' + ', '.join(sorted(unregistered))
                                 + '; missing: ' + ', '.join(sorted(missing)))
    paths = [sql_root/name for name in sorted(registered)]
    paths.extend(sql_root/entry['original'] for entry in history)
    historical_successors = {successor for entry in history for successor in entry.get('successors', [])}
    if historical_successors - registered:
        raise SourceCatalogError('Historical successors must be independently executable migrations')
    for entry in references:
        if entry.get('kind') not in ('review-only', 'rollback-only') and sql_root / entry['replacement'] not in paths:
            raise SourceCatalogError('Replacement is not in release inputs: ' + entry['replacement'])
    migration_scopes(sql_root, catalog)
    migration_dependencies(sql_root, catalog)
    migration_contracts(sql_root, catalog)
    return paths, references


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sql-root', type=Path, required=True)
    args = parser.parse_args()
    paths, refs = release_paths(args.sql_root)
    print(json.dumps(dict(files=[p.relative_to(args.sql_root.resolve()).as_posix() for p in paths], sourceReferences=refs,
                         migrationScopes=migration_scopes(args.sql_root),
                         migrationDependencies=migration_dependencies(args.sql_root),
                         migrationContracts=migration_contracts(args.sql_root)), ensure_ascii=False))


if __name__ == '__main__':
    main()
