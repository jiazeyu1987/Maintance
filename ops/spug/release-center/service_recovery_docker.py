"""Bounded local Docker API; no shell, remote transport or container creation."""
import base64
import http.client
import json
import re
import socket
import struct
from urllib.parse import quote

from service_recovery import RecoveryBlocked, require, digest


class Connection(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect('/var/run/docker.sock')


class Docker:
    def __init__(self, *, timeout):
        self.timeout = timeout

    def request(self, method, path, value=None, *, raw=False):
        connection = Connection('localhost', timeout=self.timeout)
        try:
            connection.request(method, path, body=None if value is None else json.dumps(value).encode(),
                               headers={'Content-Type': 'application/json'})
            response = connection.getresponse()
            data = response.read(2 * 1024 * 1024 + 1)
            require(response.status < 300 and len(data) <= 2 * 1024 * 1024,
                    'DOCKER_REQUEST_FAILED_' + str(response.status))
            return data if raw else json.loads(data) if data else None
        except (OSError, ValueError, http.client.HTTPException):
            raise RecoveryBlocked('DOCKER_UNAVAILABLE') from None
        finally:
            connection.close()

    def inspect(self, identity):
        require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', identity), 'INVALID_CONTAINER')
        return self.request('GET', '/containers/' + quote(identity, safe='') + '/json')

    @staticmethod
    def running(info):
        value = info['State']
        require(value['Running'] is True and value['Paused'] is False and value['Restarting'] is False
                and value.get('Dead') is not True, 'CONTAINER_NOT_RUNNING')

    @staticmethod
    def identity(info):
        require(re.fullmatch('[0-9a-f]{64}', info['Id']) and re.fullmatch('sha256:[0-9a-f]{64}', info['Image']),
                'DOCKER_IDENTITY_INVALID')
        # Env and mounts may contain secrets; store only their hash.
        return {'containerId': info['Id'], 'imageId': info['Image'],
                'configSha256': digest({k: info[k] for k in ('Config', 'HostConfig', 'Mounts')})}

    def sql(self, identity, query):
        require(query == 'SELECT @@server_uuid,@@global.read_only,@@global.super_read_only;', 'QUERY_NOT_ALLOWED')
        # Credentials stay inside the registered MySQL container environment.
        command = ['sh', '-c',
            'if [ -n "$MYSQL_ROOT_PASSWORD_FILE" ]; then export MYSQL_PWD="$(cat "$MYSQL_ROOT_PASSWORD_FILE")"; '
            'elif [ -n "$MYSQL_ROOT_PASSWORD" ]; then export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; else exit 7; fi; '
            'exec mysql --connect-timeout=3 -uroot --batch --skip-column-names -e "$1"', 'recovery-readonly', query]
        created = self.request('POST', '/containers/' + identity + '/exec',
                               {'AttachStdout': True, 'AttachStderr': True, 'Cmd': command})
        result = self.request('POST', '/exec/' + created['Id'] + '/start', {'Detach': False, 'Tty': False}, raw=True)
        outcome = self.request('GET', '/exec/' + created['Id'] + '/json')
        require(outcome['Running'] is False and outcome['ExitCode'] == 0, 'DATABASE_PROBE_FAILED')
        stdout = bytearray()
        offset = 0
        while offset < len(result):
            require(len(result) - offset >= 8, 'DATABASE_FRAME_INVALID')
            stream, length = result[offset], struct.unpack('>I', result[offset + 4:offset + 8])[0]
            offset += 8
            require(stream in (1, 2) and offset + length <= len(result), 'DATABASE_FRAME_INVALID')
            require(stream == 1, 'DATABASE_PROBE_STDERR')
            stdout.extend(result[offset:offset + length])
            offset += length
        return stdout.decode('utf-8').strip()

    def database_state(self, identity):
        values = self.sql(identity, 'SELECT @@server_uuid,@@global.read_only,@@global.super_read_only;').split('\t')
        require(len(values) == 3 and re.fullmatch('[0-9a-f-]{36}', values[0])
                and all(v in ('0', '1') for v in values[1:]), 'DATABASE_STATE_UNKNOWN')
        return values[0], values[1:] != ['0', '0']

    def restart(self, before, stop_timeout):
        current = self.inspect(before['Id'])
        self.running(current)
        require(self.identity(before) == self.identity(current)
                and current['State']['StartedAt'] == before['State']['StartedAt'], 'RESTART_IDENTITY_CHANGED')
        self.request('POST', '/containers/' + before['Id'] + '/restart?t=' + str(stop_timeout))
        after = self.inspect(before['Id'])
        self.running(after)
        require(self.identity(after) == self.identity(before)
                and after['State']['StartedAt'] != before['State']['StartedAt'], 'RESTART_NOT_CONFIRMED')

    def evidence(self, info):
        logs = self.request('GET', '/containers/' + info['Id']
                            + '/logs?stdout=1&stderr=1&timestamps=1&tail=80', raw=True)
        # Logs can contain credentials. Only the mode-600 local evidence file receives these bytes.
        return {'state': info['State'], 'dockerLogStreamBase64': base64.b64encode(logs).decode('ascii')}
