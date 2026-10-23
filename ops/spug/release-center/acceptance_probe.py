"""Prove executor-to-acceptance ingress before stopping registered writers."""
import json
import secrets
import shlex
import subprocess
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit


PROBE_SERVER = r'''
import json,sys,time
from http.server import BaseHTTPRequestHandler, HTTPServer
host,port,token=json.loads(sys.argv[1])
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def do_GET(self):
  if self.path != '/'+token:
   self.send_error(404); return
  self.send_response(200); self.end_headers(); self.wfile.write(token.encode())
  self.server.verified=True
class Server(HTTPServer):
 def get_request(self):
  connection,address=super().get_request()
  connection.settimeout(2)
  return connection,address
server=Server((host,port),Handler)
server.timeout=0.5
server.verified=False
deadline=time.monotonic()+15
try:
 while not server.verified and time.monotonic()<deadline: server.handle_request()
finally: server.server_close()
sys.exit(0 if server.verified else 2)
'''


def check(runtime, env):
    profile = runtime.profile(env)
    url = urlsplit(profile.get('acceptanceUrl', ''))
    if (url.scheme != 'http' or url.hostname != profile['host'] or not url.port
            or url.username or url.password or url.path not in ('', '/') or url.query or url.fragment
            or profile['acceptanceUrl'].rstrip('/') == profile['entryUrl'].rstrip('/')):
        raise ValueError('Explicit separate HTTP acceptance host/port required')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    if env == 'rehearsal':
        # Its already provisioned gateway owns the port before the candidate
        # acceptance upstream exists. 502 proves ingress only, never app health.
        try:
            with opener.open(profile['acceptanceUrl'], timeout=5) as response:
                status = response.status
        except urllib.error.HTTPError as error:
            status = error.code
        if status not in (200, 502):
            raise ValueError('Registered rehearsal acceptance gateway did not respond as expected')
        return {'reachable': True, 'mode': 'registered-rehearsal-gateway', 'httpStatus': status}
    token = secrets.token_hex(24)
    args = json.dumps([url.hostname, url.port, token])
    command = shlex.quote(profile['python'])+' -u -c '+shlex.quote(PROBE_SERVER)+' '+shlex.quote(args)
    process = subprocess.Popen(['ssh', *runtime.ssh_options(), 'root@'+profile['host'], command],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    verified = False
    try:
        deadline = time.monotonic()+12
        while time.monotonic() < deadline and process.poll() is None:
            try:
                with opener.open(profile['acceptanceUrl'].rstrip('/')+'/'+token, timeout=1) as response:
                    if response.status != 200 or response.read(128).decode('ascii') != token:
                        raise ValueError('Acceptance probe identity mismatch; port is occupied')
                verified = True
                break
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.25)  # Wait only for this bounded probe's startup/network response.
        process.communicate(timeout=25)
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=5)
    if not verified or process.returncode != 0:
        raise ValueError('Acceptance ingress unreachable or occupied: '+profile['acceptanceUrl']+
                         '; verify the fixed executor source/firewall rule before deployment')
    return {'reachable': True, 'mode': 'temporary-nonce-listener', 'url': profile['acceptanceUrl']}
