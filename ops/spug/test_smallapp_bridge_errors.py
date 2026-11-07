"""Transport fault contracts; no simulated backup/restore success or browser E2E."""
import errno
import http.client
import io
import socket
import ssl
import unittest
import urllib.error
from unittest.mock import Mock

import smallapp_adapter as adapter


class BridgeErrors(unittest.TestCase):
    def test_automatic_plan_budget_encloses_native_deadline_without_changing_normal_calls(self):
        for path, request, expected in (
            ('/incremental-plan?sourceConfigRef=source-A', None, 40),
            ('/operations', {'action': 'INCREMENTAL'}, 40),
            ('/selections', None, 10),
            ('/operations/id', None, 10),
            ('/operations', {'action': 'FULL'}, 10),
        ):
            with self.subTest(path=path, request=request):
                bridge = self.bridge()
                bridge.opener.open.return_value = io.BytesIO(b'{}')
                self.assertEqual(bridge.call('http://127.0.0.1:18083' + path, request), {})
                self.assertEqual(bridge.opener.open.call_args.kwargs['timeout'], expected)

    def bridge(self):
        bridge = adapter.HttpBridge.__new__(adapter.HttpBridge)
        bridge.headers = {'Authorization': 'unit-only-secret-must-not-escape'}
        bridge.requests = []
        bridge.opener = Mock()
        return bridge

    def assert_code(self, bridge, code):
        with self.assertRaises(adapter.Refused) as caught:
            bridge.call('http://127.0.0.1:18083/selections')
        self.assertEqual(str(caught.exception), code)
        self.assertNotIn('secret', str(caught.exception))
        self.assertEqual(bridge.requests, ['GET'])

    def test_native_transport_failures_have_distinct_safe_codes(self):
        sensitive = 'unit-only-secret https://user:secret@example.invalid/'
        failures = [
            (TimeoutError(sensitive), 'BRIDGE_TIMEOUT'),
            (ConnectionRefusedError(errno.ECONNREFUSED, sensitive), 'BRIDGE_CONNECTION_REFUSED'),
            (socket.gaierror(socket.EAI_NONAME, sensitive), 'BRIDGE_DNS_FAILED'),
            (ConnectionResetError(errno.ECONNRESET, sensitive), 'BRIDGE_CONNECTION_RESET'),
            (OSError(errno.ENETUNREACH, sensitive), 'BRIDGE_NETWORK_UNREACHABLE'),
            (OSError(errno.EHOSTUNREACH, sensitive), 'BRIDGE_NETWORK_UNREACHABLE'),
            (OSError(10061, sensitive), 'BRIDGE_CONNECTION_REFUSED'),
            (OSError(10060, sensitive), 'BRIDGE_TIMEOUT'),
            (ssl.SSLCertVerificationError(1, sensitive), 'BRIDGE_TLS_CERTIFICATE_INVALID'),
            (ssl.SSLError(1, sensitive), 'BRIDGE_TLS_FAILED'),
            (http.client.RemoteDisconnected(sensitive), 'BRIDGE_RESPONSE_INCOMPLETE'),
            (http.client.IncompleteRead(b'secret', 100), 'BRIDGE_RESPONSE_INCOMPLETE'),
            (http.client.BadStatusLine(sensitive), 'BRIDGE_RESPONSE_HTTP_INVALID'),
            (OSError(errno.EIO, sensitive), 'BRIDGE_IO_FAILED'),
            (ValueError(sensitive), 'BRIDGE_REQUEST_INVALID'),
        ]
        for error, code in failures:
            for wrapped in (False, True):
                with self.subTest(kind=type(error).__name__, wrapped=wrapped):
                    bridge = self.bridge()
                    bridge.opener.open.side_effect = urllib.error.URLError(error) if wrapped else error
                    self.assert_code(bridge, code)

    def test_unknown_url_error_does_not_guess_from_raw_text(self):
        bridge = self.bridge()
        bridge.opener.open.side_effect = urllib.error.URLError('secret: connection refused or timed out')
        self.assert_code(bridge, 'BRIDGE_CONNECTION_FAILED')

    def test_response_encoding_json_and_size_are_distinguished(self):
        for body, code in [
            (b'\xffsecret', 'BRIDGE_RESPONSE_ENCODING_INVALID'),
            (b'<html>secret login page</html>', 'BRIDGE_RESPONSE_JSON_INVALID'),
            (b'{"secret":', 'BRIDGE_RESPONSE_JSON_INVALID'),
            (b'x' * 65537, 'BRIDGE_RESPONSE_TOO_LARGE'),
        ]:
            with self.subTest(code=code):
                bridge = self.bridge()
                bridge.opener.open.return_value = io.BytesIO(body)
                self.assert_code(bridge, code)

    def test_http_status_and_valid_symbolic_errors_survive_without_body_leaks(self):
        for status in (401, 403, 404, 500, 502, 503, 504):
            for body in (b'<html>secret</html>', b'{"detail":"secret"}', b'\xffsecret'):
                with self.subTest(status=status, body=body[:8]):
                    bridge = self.bridge()
                    bridge.opener.open.side_effect = urllib.error.HTTPError(
                        'http://user:secret@127.0.0.1/', status, 'secret', {}, io.BytesIO(body))
                    self.assert_code(bridge, 'BRIDGE_HTTP_' + str(status))
        bridge = self.bridge()
        bridge.opener.open.side_effect = urllib.error.HTTPError(
            'http://127.0.0.1/', 409, 'conflict', {}, io.BytesIO(b'{"errorCode":"TARGET_NOT_CURRENTLY_FRESH"}'))
        self.assert_code(bridge, 'TARGET_NOT_CURRENTLY_FRESH')

    def test_http_body_read_failure_retains_proven_status(self):
        bridge = self.bridge()
        body = Mock()
        body.read.side_effect = TimeoutError('secret')
        bridge.opener.open.side_effect = urllib.error.HTTPError(
            'http://127.0.0.1/', 503, 'secret', {}, body)
        self.assert_code(bridge, 'BRIDGE_HTTP_503')


if __name__ == '__main__':
    unittest.main(verbosity=2)
