"""Bound semantic readiness for registered original MAIN services.

These roles always use their service protocol. Any declared Docker health check
is an additional condition; the isolated-target Docker contract is unchanged.
"""
import errno
import hashlib
import ipaddress
import socket
import time
import urllib.error
import urllib.request

from recovery_engine import RecoveryError, parse, persist_evidence, require, utc

ROLES = {'minio': (9000, '/minio/health/ready'),
         'backend': (48081, '/actuator/health'), 'frontend': (80, '/')}
STARTUP_SECONDS = 600
RESPONSE_LIMIT = 65536


def endpoint(native, role, row=None):
    from recovery_main_target import service_configuration_digest
    require(role in ROLES, 'MAIN_HEALTH_ROLE_UNSUPPORTED')
    service = native.config_services[role]
    row = native.inspect(service['id']) if row is None else row
    require(row['Id'] == service['id'] and row['Image'] == service['imageId'] and
            service_configuration_digest(row) == native.config['mainApplication']['serviceConfigurationDigests'][role],
            'MAIN_HEALTH_SERVICE_CHANGED')
    port, path = ROLES[role]
    require(str(port) + '/tcp' in (row['Config'].get('ExposedPorts') or {}), 'MAIN_HEALTH_PORT_NOT_DECLARED')
    try:
        address = ipaddress.IPv4Address(service['ip'])
    except (ValueError, ipaddress.AddressValueError):
        raise RecoveryError('MAIN_HEALTH_ENDPOINT_INVALID') from None
    require(str(address) == service['ip'] and address.is_private and not address.is_unspecified and
            not address.is_link_local and not address.is_multicast and
            (not address.is_loopback or role == 'minio' and str(address) == '127.0.0.1'),
            'MAIN_HEALTH_ENDPOINT_INVALID')
    return 'http://' + str(address) + ':' + str(port) + path


def preflight(native):
    for role in ROLES:
        endpoint(native, role)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def probe(url, role, timeout):
    require(role in ROLES, 'MAIN_HEALTH_ROLE_UNSUPPORTED')
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    response = None
    try:
        response = opener.open(urllib.request.Request(url, headers={'Accept': 'application/json' if role == 'backend' else '*/*'}),
                               timeout=timeout)
    except urllib.error.HTTPError as error:
        response = error
    except (urllib.error.URLError, TimeoutError) as error:
        reason = getattr(error, 'reason', error)
        require(isinstance(reason, (TimeoutError, socket.timeout)) or
                isinstance(reason, OSError) and reason.errno in
                (errno.ECONNREFUSED, errno.ETIMEDOUT, errno.EHOSTUNREACH, errno.ENETUNREACH, errno.ECONNRESET),
                'MAIN_HEALTH_TRANSPORT_INVALID')
        return dict(ready=False, httpStatus=None, transport='NOT_READY', bodySha256=None)
    with response:
        raw = response.read(RESPONSE_LIMIT + 1)
        status = response.code
        require(len(raw) <= RESPONSE_LIMIT, 'MAIN_HEALTH_RESPONSE_LIMIT')
        require(status == 200 or status in (429, 500, 502, 503, 504), 'MAIN_HEALTH_HTTP_STATUS_INVALID')
        ready = status == 200
        if ready and role == 'backend':
            try:
                value = parse(raw)
                require(type(value) is dict and type(value.get('status')) is str,
                        'MAIN_HEALTH_BACKEND_RESPONSE_INVALID')
            except (ValueError, UnicodeError, RecoveryError):
                raise RecoveryError('MAIN_HEALTH_BACKEND_RESPONSE_INVALID') from None
            ready = value['status'] == 'UP'
        return dict(ready=ready, httpStatus=status, bodySha256=hashlib.sha256(raw).hexdigest())


def wait_healthy(native, role):
    native.bound()
    deadline = time.monotonic() + min(STARTUP_SECONDS, native.budget.remaining())
    attempts = 0
    while True:
        native.guard()
        require(time.monotonic() < deadline, 'MAIN_SEMANTIC_HEALTH_TIMEOUT')
        row = native.inspect(native.config_services[role]['id'])
        url = endpoint(native, role, row)
        state = row['State']
        require(state['Running'] and not state['Paused'] and not state['Restarting'], 'MAIN_HEALTH_SERVICE_NOT_RUNNING')
        declared = bool(row['Config'].get('Healthcheck'))
        docker_health = state.get('Health')
        if declared:
            require(type(docker_health) is dict and docker_health.get('Status') in ('starting', 'healthy'),
                    'MAIN_DOCKER_HEALTH_INVALID')
        attempts += 1
        observed = probe(url, role, max(0.001, min(5, deadline - time.monotonic(), native.budget.remaining())))
        if observed['ready'] and (not declared or docker_health['Status'] == 'healthy'):
            require(time.monotonic() < deadline, 'MAIN_SEMANTIC_HEALTH_TIMEOUT')
            native.bound()
            ref = persist_evidence(native.root / ('main-health-' + role + '.json'),
                dict(schemaVersion='RegisteredMainSemanticReadiness/v1', role=role, containerId=row['Id'], imageId=row['Image'],
                     serviceConfigurationDigest=native.config['mainApplication']['serviceConfigurationDigests'][role],
                     endpoint=url, status='healthy', semanticStatus='UP' if role == 'backend' else 'READY',
                     dockerHealthcheckConfigured=declared, dockerHealthStatus=None if not declared else docker_health['Status'],
                     observedAt=utc(), attempts=attempts, **observed), native.original_pins)
            return dict(containerId=row['Id'], imageId=row['Image'], status='healthy', observedAt=utc(), readinessPin=ref)
        require(time.monotonic() < deadline, 'MAIN_SEMANTIC_HEALTH_TIMEOUT')
        time.sleep(min(1, max(0.001, deadline - time.monotonic()), native.budget.remaining()))
