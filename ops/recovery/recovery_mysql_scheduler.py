"""Append-only custody of the global scheduler for an exclusive MAIN database."""
from pathlib import Path
import time

from recovery_engine import absolute, digest, load, pin, pinned_json, require, utc
from recovery_retained_retry import append

SYSTEM_DATABASES = {'mysql', 'sys', 'information_schema', 'performance_schema'}
STATE_SQL = 'SELECT @@server_uuid, @@GLOBAL.read_only, @@GLOBAL.super_read_only, @@GLOBAL.event_scheduler;'
WORKERS_SQL = "SELECT COUNT(*) FROM information_schema.PROCESSLIST WHERE USER='event_scheduler';"
TRANSACTIONS_SQL = 'SELECT COUNT(*) FROM information_schema.innodb_trx;'
DRAIN_TIMEOUT_SECONDS = 15


class MainMysqlScheduler:
    def __init__(self, target, operation_id, journal, query, *, inherited=None):
        require(target.get('mainApplication', {}).get('schemaVersion') in
                ('RegisteredMainApplication/v1', 'RegisteredMainApplication/v2'), 'MAIN_SCHEDULER_MAIN_REQUIRED')
        self.target, self.operation_id, self.query = target, operation_id, query
        self.journal, self.inherited = absolute(str(journal)), inherited
        self.binding = digest(dict(database=target['database'], databaseUuid=target['replacement']['databaseUuid'],
            mysql=[s for s in target['services'] if s['role'] == 'mysql'], mainApplication=target['mainApplication']))

    def _state(self):
        raw = self.query(STATE_SQL).decode('ascii')
        values = raw.rstrip('\n').split('\t')
        require(len(values) == 4 and raw == '\t'.join(values)+'\n' and
                values[:3] == [self.target['replacement']['databaseUuid'], '0', '0'] and
                values[3] in ('ON', 'OFF', 'DISABLED'), 'MAIN_SCHEDULER_DATABASE_CHANGED')
        names = self.query('SHOW DATABASES;').decode('utf-8').splitlines()
        require(len(names) == len(set(names)) and set(names) == SYSTEM_DATABASES | {self.target['database']},
                'MAIN_SCHEDULER_DATABASE_SCOPE_CHANGED')
        return values[3]

    def _inherited(self):
        if self.inherited is None: return None
        value = pinned_json(self.inherited)
        intent, active = [pinned_json(value[key]) for key in ('intentPin', 'activePin')]
        require(value.get('schemaVersion') == 'MainMysqlSchedulerRecoveryCustody/v1' and
                value['configurationDigest'] == self.binding and value['operationId'] != self.operation_id and
                value['originalState'] in ('ON', 'OFF', 'DISABLED') and
                value['pausedState'] == ('DISABLED' if value['originalState'] == 'DISABLED' else 'OFF') and
                intent['operationId'] == active['operationId'] == value['operationId'] and
                intent['configurationDigest'] == active['configurationDigest'] == self.binding and
                intent['originalState'] == value['originalState'] and active['intentPin'] == value['intentPin'] and
                self.inherited['path'] == str(Path(value['intentPin']['path']).parent/'recovery-custody.json') and
                not (Path(value['intentPin']['path']).parent/'released.json').exists(),
                'MAIN_SCHEDULER_RECOVERY_CUSTODY_CHANGED')
        return value

    def preflight(self):
        require(not self.journal.exists(), 'MAIN_SCHEDULER_ALREADY_CLAIMED')
        current = self._state(); inherited = self._inherited()
        require(inherited is None or current == inherited['pausedState'], 'MAIN_SCHEDULER_STATE_CHANGED')
        return current

    def install(self):
        current = self.preflight(); inherited = self._inherited()
        original = inherited['originalState'] if inherited else current
        paused = 'DISABLED' if original == 'DISABLED' else 'OFF'
        self.journal.mkdir(mode=0o700)
        intent = append(self.journal/'intent.json', dict(schemaVersion='MainMysqlSchedulerIntent/v1',
            operationId=self.operation_id, configurationDigest=self.binding, originalState=original,
            observedInitialState=current, pausedState=paused, inheritedCustodyPin=self.inherited, startedAt=utc()))
        if current == 'ON': self.query('SET GLOBAL event_scheduler=OFF;', mutation=True)
        require(self._state() == paused, 'MAIN_SCHEDULER_STATE_CHANGED')
        deadline = time.monotonic()+DRAIN_TIMEOUT_SECONDS
        while True:
            require(self._state() == paused, 'MAIN_SCHEDULER_STATE_CHANGED')
            if self.query(WORKERS_SQL).strip() == b'0' and self.query(TRANSACTIONS_SQL).strip() == b'0': break
            require(time.monotonic() < deadline, 'MAIN_SCHEDULER_NOT_QUIESCED')
            time.sleep(0.2)
        append(self.journal/'active.json', dict(schemaVersion='MainMysqlSchedulerActive/v1',
            operationId=self.operation_id, configurationDigest=self.binding, intentPin=intent, pausedState=paused))
        self.verify()

    def verify(self):
        active = load(self.journal/'active.json'); intent = pinned_json(active['intentPin'])
        require(active.get('schemaVersion') == 'MainMysqlSchedulerActive/v1' and
                intent.get('schemaVersion') == 'MainMysqlSchedulerIntent/v1' and
                active['operationId'] == intent['operationId'] == self.operation_id and
                active['configurationDigest'] == intent['configurationDigest'] == self.binding and
                active['intentPin']['path'] == str(self.journal/'intent.json') and
                intent['originalState'] in ('ON', 'OFF', 'DISABLED') and
                active['pausedState'] == intent['pausedState'] ==
                    ('DISABLED' if intent['originalState'] == 'DISABLED' else 'OFF') and
                not (self.journal/'released.json').exists(), 'MAIN_SCHEDULER_IDENTITY_CHANGED')
        require(self._state() == active['pausedState'], 'MAIN_SCHEDULER_STATE_CHANGED')
        require(self.query(WORKERS_SQL).strip() == b'0', 'MAIN_SCHEDULER_NOT_QUIESCED')
        return intent

    def recovery_custody(self):
        intent = self.verify()
        return append(self.journal/'recovery-custody.json', dict(schemaVersion='MainMysqlSchedulerRecoveryCustody/v1',
            operationId=self.operation_id, configurationDigest=self.binding, originalState=intent['originalState'],
            pausedState=intent['pausedState'], intentPin=pin(self.journal/'intent.json'),
            activePin=pin(self.journal/'active.json'), issuedAt=utc()))

    def release(self):
        intent = self.verify(); original = intent['originalState']
        append(self.journal/'release-intent.json', dict(operationId=self.operation_id,
            originalState=original, activePin=pin(self.journal/'active.json'), startedAt=utc()))
        try:
            if original == 'ON': self.query('SET GLOBAL event_scheduler=ON;', mutation=True)
            require(self._state() == original, 'MAIN_SCHEDULER_STATE_CHANGED')
            return append(self.journal/'released.json', dict(schemaVersion='MainMysqlSchedulerRelease/v1',
                operationId=self.operation_id, configurationDigest=self.binding, originalState=original,
                originalStateRestored=True, intentPin=pin(self.journal/'intent.json'),
                activePin=pin(self.journal/'active.json'), finishedAt=utc()))
        except BaseException:
            # A failed release is still a failed restore: do not leave imported
            # enabled events running after a transport/readback/journal error.
            if original == 'ON':
                self.query('SET GLOBAL event_scheduler=OFF;', mutation=True)
                require(self._state() == 'OFF', 'MAIN_SCHEDULER_FAILURE_PAUSE_NOT_PROVEN')
            raise
