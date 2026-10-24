"""Real Linux socket regression for the probe -> preflight handoff."""
import errno
import socket
import sys
import unittest

from intruoyi_runtime import RuntimeBlocked
from intruoyi_runtime_agent import check_acceptance_port


@unittest.skipUnless(sys.platform.startswith('linux'), 'Target socket semantics require Linux')
class AcceptancePortTests(unittest.TestCase):
    def test_closed_probe_time_wait_allows_next_listener(self):
        with socket.socket() as listener, socket.socket() as client:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(('127.0.0.1', 0))
            address = listener.getsockname()
            listener.listen(1)
            client.connect(address)
            accepted, _ = listener.accept()
            accepted.close()  # Server sends FIN first, retaining TIME_WAIT.
            self.assertEqual(client.recv(1), b'')
        with socket.socket() as original:
            with self.assertRaises(OSError) as caught:
                original.bind(address)
            self.assertEqual(caught.exception.errno, errno.EADDRINUSE)
        check_acceptance_port(*address)

    def test_live_listener_remains_blocked(self):
        with socket.socket() as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(('0.0.0.0', 0))
            listener.listen(1)
            port = listener.getsockname()[1]
            with self.assertRaisesRegex(RuntimeBlocked, 'Acceptance port cannot be bound'):
                check_acceptance_port('127.0.0.1', port)
            with socket.socket() as client:
                client.connect(('127.0.0.1', port))
                accepted, _ = listener.accept()
                accepted.close()


if __name__ == '__main__':
    unittest.main()
