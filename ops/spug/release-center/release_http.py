"""Bounded fixed-origin HTTP; one deadline covers identity and forwarded route."""
import http.client
import socket
import threading
import time
import urllib.parse


class ReleaseHTTPError(ValueError):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def remaining(deadline):
    value = deadline - time.monotonic()
    if value <= 0:
        raise ReleaseHTTPError(504, 'RELEASE_EXECUTOR_DEADLINE_EXCEEDED')
    return value


def read_response(origin, route, method, data, headers, deadline, max_bytes):
    """Do not follow redirects, use proxy env, or buffer an unbounded body."""
    parsed = urllib.parse.urlsplit(origin)
    path = urllib.parse.urlsplit(route)
    if (parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password
            or parsed.path or parsed.query or parsed.fragment or not route.startswith('/')
            or path.scheme or path.netloc or path.fragment):
        raise ReleaseHTTPError(502, 'RELEASE_EXECUTOR_ORIGIN_INVALID')
    connection_type = http.client.HTTPSConnection if parsed.scheme == 'https' else http.client.HTTPConnection
    connection = connection_type(parsed.hostname, parsed.port, timeout=remaining(deadline))
    watchdog = None
    expired = threading.Event()
    try:
        connection.connect()
        transport = connection.sock

        def expire():
            # socket timeouts alone reset on each received byte, including header
            # lines parsed by http.client. Interrupt this exact socket at deadline.
            expired.set()
            try:
                transport.shutdown(socket.SHUT_RDWR)
            except OSError:
                # A concurrently completed response may already own the close.
                pass

        watchdog = threading.Timer(remaining(deadline), expire)
        watchdog.daemon = True
        watchdog.start()
        transport.settimeout(remaining(deadline))
        connection.request(method, route, body=data, headers=headers)
        transport.settimeout(remaining(deadline))
        with connection.getresponse() as response:
            if 300 <= response.status < 400:
                raise ReleaseHTTPError(502, 'RELEASE_EXECUTOR_REDIRECT_REFUSED')
            if response.length is not None and response.length > max_bytes:
                raise ReleaseHTTPError(502, 'RELEASE_EXECUTOR_RESPONSE_TOO_LARGE')
            chunks = []
            size = 0
            expected = response.length
            while not response.isclosed():
                transport.settimeout(remaining(deadline))
                chunk = response.read1(min(65536, max_bytes + 1 - size))
                remaining(deadline)
                if not chunk:
                    break
                size += len(chunk)
                if size > max_bytes:
                    raise ReleaseHTTPError(502, 'RELEASE_EXECUTOR_RESPONSE_TOO_LARGE')
                chunks.append(chunk)
            if expected is not None and size != expected:
                remaining(deadline)
                raise ReleaseHTTPError(502, 'RELEASE_EXECUTOR_RESPONSE_TRUNCATED')
            remaining(deadline)
            return response.status, b''.join(chunks)
    except (socket.timeout, TimeoutError) as exc:
        raise ReleaseHTTPError(504, 'RELEASE_EXECUTOR_DEADLINE_EXCEEDED') from exc
    except (OSError, http.client.HTTPException) as exc:
        if expired.is_set() or time.monotonic() >= deadline:
            raise ReleaseHTTPError(504, 'RELEASE_EXECUTOR_DEADLINE_EXCEEDED') from exc
        raise ReleaseHTTPError(502, 'RELEASE_EXECUTOR_TRANSPORT_FAILED') from exc
    finally:
        if watchdog is not None:
            watchdog.cancel()
            watchdog.join()
        connection.close()
