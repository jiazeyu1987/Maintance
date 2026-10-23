"""Transactional local release state. Legacy JSON is imported explicitly offline."""
import argparse
import json
import os
from pathlib import Path
import sqlite3


def process_lock(root):
    handle = open(Path(root) / 'executor.lock', 'a+b')
    try:
        handle.seek(0)
        handle.write(b'0')
        handle.flush()
        handle.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return handle
    except BaseException:
        handle.close()
        raise


def validate(value):
    if not (isinstance(value, dict) and isinstance(value.get('jobs'), list)
            and isinstance(value.get('packages'), list) and isinstance(value.get('environments'), dict)):
        raise ValueError('Invalid release state; refusing to initialize empty history')
    return value


class StateStore:
    def __init__(self, root):
        self.path = Path(root) / 'state.sqlite3'
        if not self.path.exists():
            if (Path(root) / 'state.json').exists():
                raise ValueError('Legacy state.json requires offline state_store.py --migrate --root before starting')
            self.create(dict(packages=[], jobs=[], environments={}))

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=5)
        try:
            connection.execute('PRAGMA synchronous=FULL')
        except BaseException:
            connection.close()
            raise
        return connection

    def create(self, value):
        payload = json.dumps(validate(value), ensure_ascii=False)
        # Exclusive file creation prevents accidentally replacing existing history.
        with self.path.open('xb'):
            pass
        connection = self.connect()
        try:
            if connection.execute('PRAGMA journal_mode=WAL').fetchone()[0] != 'wal':
                raise RuntimeError('SQLite WAL is required for concurrent read-only observations')
            with connection:
                connection.execute('CREATE TABLE release_state (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)')
                connection.execute('INSERT INTO release_state VALUES (1, ?)', (payload,))
        finally:
            connection.close()

    def load(self):
        connection = self.connect()
        try:
            rows = connection.execute('SELECT payload FROM release_state').fetchall()
            if len(rows) != 1:
                raise ValueError('Release state row is missing or ambiguous')
            return validate(json.loads(rows[0][0]))
        finally:
            connection.close()

    def save(self, value):
        payload = json.dumps(validate(value), ensure_ascii=False)
        connection = self.connect()
        try:
            with connection:
                result = connection.execute('UPDATE release_state SET payload=? WHERE id=1', (payload,))
                if result.rowcount != 1:
                    raise ValueError('Release state row is missing')
        finally:
            connection.close()


def migrate(root):
    root = Path(root)
    with process_lock(root):
        value = validate(json.loads((root / 'state.json').read_text('utf-8')))
        store = StateStore.__new__(StateStore)
        store.path = root / 'state.sqlite3'
        store.create(value)
        if store.load() != value:
            raise RuntimeError('Imported state differs from original JSON')
        return {'migrated': True, 'jobs': len(value['jobs']), 'packages': len(value['packages'])}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--migrate', action='store_true', required=True)
    args = parser.parse_args()
    print(json.dumps(migrate(args.root)))
