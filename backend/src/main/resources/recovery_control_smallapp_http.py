"""Direct Spug HTTP entry; task-private Bearer reference and explicit client IPs."""
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import os
from pathlib import Path
import re
import stat

from recovery_control_smallapp import (Failure, MAX_FRAME, canonical, decode, exact,
    local_read, native_required, need, opaque, public_error, request)


def credential(reference):
    exact(reference, 'path uid gid mode', 'TRANSPORT_CREDENTIAL_REFERENCE_INVALID')
    need(reference['uid'] == reference['gid'] == 0 and reference['mode'] == 0o600,
         'TRANSPORT_CREDENTIAL_CUSTODY_REQUIRED')
    value = local_read(reference['path'], limit=2048)
    exact(value, 'headers', 'TRANSPORT_PRIVATE_HEADERS_INVALID')
    exact(value['headers'], 'Authorization', 'TRANSPORT_PRIVATE_AUTHORIZATION_REQUIRED')
    authorization = value['headers']['Authorization']
    need(type(authorization) is str and re.fullmatch('Bearer [A-Za-z0-9_-]{43,128}', authorization),
         'TRANSPORT_PRIVATE_AUTHORIZATION_INVALID')
    return authorization


def handler(ledger, config):
    # Secret bytes remain in memory; request logs and command arguments never contain them.
    authorized = credential(config['authCredentialRef'])
    allowed = set(config['allowedClientAddresses'])
    need(allowed and all(type(address) is str and str(ipaddress.ip_address(address)) == address
                        for address in allowed), 'TRANSPORT_CLIENT_ADDRESSES_REQUIRED')

    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.0'
        server_version = 'SmallAppExecutionBridge'
        sys_version = ''

        def setup(self):
            super().setup(); self.connection.settimeout(5)

        def log_message(self, fmt, *args):
            # HTTP headers/body and native streams are private originals, never console logs.
            return

        def reply(self, code, payload):
            raw = canonical(payload)
            self.send_response(code)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers(); self.wfile.write(raw)

        def admit(self):
            need(self.client_address[0] in allowed, 'TRANSPORT_CLIENT_FORBIDDEN')
            supplied = self.headers.get_all('Authorization', [])
            need(len(supplied) == 1 and hmac.compare_digest(supplied[0].encode(), authorized.encode()),
                 'TRANSPORT_AUTHENTICATION_REQUIRED')
            need(not self.headers.get_all('Transfer-Encoding', []), 'TRANSPORT_CHUNKED_REFUSED')

        def do_POST(self):
            try:
                self.admit(); need(self.path == '/operations', 'TRANSPORT_ROUTE_UNKNOWN')
                lengths = self.headers.get_all('Content-Length', [])
                need(len(lengths) == 1 and re.fullmatch('[0-9]+', lengths[0]), 'TRANSPORT_LENGTH_REQUIRED')
                length = int(lengths[0])
                need(0 < length <= MAX_FRAME and self.headers.get_content_type() == 'application/json',
                     'TRANSPORT_BODY_INVALID')
                raw = self.rfile.read(length)
                need(len(raw) == length, 'TRANSPORT_BODY_TRUNCATED')
                payload = request(decode(raw))
                self.reply(202, ledger.submit(payload))
            except Exception as error:
                self.reply(409 if isinstance(error, Failure) else 500, {'errorCode': public_error(error)})

        def do_GET(self):
            try:
                self.admit()
                if self.path == '/selections':
                    self.reply(200, ledger.native.selections())
                    return
                need(self.path.startswith('/operations/') and self.path.count('/') == 2,
                     'TRANSPORT_ROUTE_UNKNOWN')
                operation = opaque(self.path[len('/operations/'):])
                self.reply(200, ledger.status(operation))
            except Exception as error:
                self.reply(404 if isinstance(error, Failure) else 500, {'errorCode': public_error(error)})

    return Handler


def run_server(config, ledger):
    native_required()
    import ipaddress
    try:
        address = ipaddress.ip_address(config['listenAddress'])
    except ValueError:
        raise Failure('TRANSPORT_TASK_BIND_REQUIRED') from None
    need(address.version == 4 and address.is_private and not address.is_unspecified
         and not address.is_multicast and type(config['listenPort']) is int and
         1024 <= config['listenPort'] <= 65535 and config['listenPort'] not in (8081, 9000, 2375, 2376),
         'TRANSPORT_TASK_BIND_REQUIRED')
    import fcntl
    lock_fd = os.open(Path(config['ledgerRoot']) / 'service.lock', os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(lock_fd)
        need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_uid == info.st_gid == 0 and
             stat.S_IMODE(info.st_mode) == 0o600, 'SERVICE_LOCK_CUSTODY_REQUIRED')
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with ThreadingHTTPServer((config['listenAddress'], config['listenPort']), handler(ledger, config)) as server:
            server.daemon_threads = False
            server.serve_forever(poll_interval=0.5)
    finally:
        os.close(lock_fd)
