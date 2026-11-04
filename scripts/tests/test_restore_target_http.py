"""Local synthetic HTTP contract tests, without Spug or server operations."""
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'backend/src/main/resources'))
import recovery_control_smallapp_http as module


class TargetSelectionHttp(unittest.TestCase):
    def test_authenticated_target_query_and_invalid_duplicate_parameters(self):
        observed=[]
        native=SimpleNamespace(selections=lambda **kw:observed.append(kw) or {'observedAt':'unit','applications':[]})
        ledger=SimpleNamespace(native=native)
        with patch.object(module,'credential',return_value='Bearer unit-private-token'):
            handler=module.handler(ledger,dict(authCredentialRef={},allowedClientAddresses=['127.0.0.1']))
        server=ThreadingHTTPServer(('127.0.0.1',0),handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            base='http://127.0.0.1:'+str(server.server_port)
            def get(path,auth=True):
                headers={'Authorization':'Bearer unit-private-token'} if auth else {}
                return urllib.request.urlopen(urllib.request.Request(base+path,headers=headers),timeout=3)
            with get('/selections'):pass
            with get('/selections?targetConfigRef=main-58'):pass
            self.assertEqual(observed,[{'selected_target':None},{'selected_target':'main-58'}])
            for query in ['?targetConfigRef=main-58&targetConfigRef=main-59','?targetConfigRef=','?other=main-58']:
                with self.assertRaises(urllib.error.HTTPError):get('/selections'+query)
            with self.assertRaises(urllib.error.HTTPError):get('/selections?targetConfigRef=main-58',auth=False)
            self.assertEqual(len(observed),2)
        finally:
            server.shutdown();server.server_close();thread.join(timeout=3)


if __name__=='__main__':unittest.main()
