"""Native Spug session/permission boundary for the additive release entry."""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from application_registry import ApplicationRegistry, RegistryError

sys.path.insert(0, '/data/spug/spug_api')
os.environ['DJANGO_SETTINGS_MODULE'] = 'spug.settings'
import django
django.setup()
from django.test import RequestFactory
from django.db import close_old_connections
from libs.middleware import AuthenticationMiddleware

CONFIG = json.loads(Path(os.environ['RELEASE_BRIDGE_CONFIG']).read_text('utf-8'))
REGISTRY = ApplicationRegistry(CONFIG)
AUTH = AuthenticationMiddleware(lambda request: None)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def proxy(self):
        close_old_connections()
        try:
            if self.client_address[0] != '127.0.0.1':
                raise ValueError('Loopback proxy required')
            token = self.headers.get('X-Token', '')
            if not re.fullmatch('[0-9a-f]{32}', token):
                raise ValueError('Spug login required')
            request = RequestFactory().get('/release-center/', HTTP_X_TOKEN=token,
                HTTP_X_FORWARDED_FOR=self.headers.get('X-Forwarded-For', ''))
            if AUTH.process_request(request) is not None or request.user.is_deleted:
                raise ValueError('Spug login required')
            perm = 'schedule.schedule.edit' if self.command == 'POST' else 'schedule.schedule.view'
            if not request.user.has_perms([perm]):
                raise ValueError('Spug permission required: ' + perm)
            if self.command == 'POST' and self.headers.get('Origin') != CONFIG['origin']:
                raise ValueError('Request origin refused')
            size = int(self.headers.get('Content-Length', '0'))
            if size < 0 or size > 16384:
                raise ValueError('Invalid request size')
            data = self.rfile.read(size) if self.command == 'POST' else None
            if self.command == 'GET' and self.path == '/applications':
                return self.send(200, json.dumps(REGISTRY.catalog(), ensure_ascii=False).encode('utf-8'))
            payload = json.loads(data) if data is not None else None
            app, route = REGISTRY.resolve(self.path, self.command, payload)
            try:
                status, raw = REGISTRY.request(app, route, self.command, payload, str(request.user.id))
            except urllib.error.HTTPError as exc:
                with exc:
                    status, raw = exc.code, exc.read()
            self.send(status, raw)
        except RegistryError as exc:
            self.send(exc.status, json.dumps({'error': str(exc)}, ensure_ascii=False).encode('utf-8'))
        except ValueError as exc:
            self.send(403, json.dumps({'error': str(exc)}).encode())
        except Exception:
            self.send(502, b'{"error":"Release executor unavailable; inspect own service logs"}')
        finally:
            close_old_connections()

    def send(self, status, data):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    do_GET = proxy
    do_POST = proxy


ThreadingHTTPServer(('127.0.0.1', 18111), Handler).serve_forever()
