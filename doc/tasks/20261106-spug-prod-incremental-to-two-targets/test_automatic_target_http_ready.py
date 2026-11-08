import http.server
import json
import os
import socket
import threading
import time
import unittest
import urllib.request

from automatic_target_http_ready import wait_http_json


class Readiness(unittest.TestCase):
    def listener(self, *, delay=0, status=200, body=b'{"ready":true}'):
        with socket.socket() as temporary:
            temporary.bind(('127.0.0.1',0));port=temporary.getsockname()[1]
        stopped=threading.Event();started=threading.Event();state={'requests':0,'server':None}
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                state['requests']+=1;self.send_response(status);self.end_headers();self.wfile.write(body)
            def log_message(self,*args):pass
        def run():
            if stopped.wait(delay):return
            server=http.server.HTTPServer(('127.0.0.1',port),Handler);server.timeout=.05;state['server']=server;started.set()
            while not stopped.is_set():server.handle_request()
            server.server_close()
        thread=threading.Thread(target=run);thread.start()
        self.addCleanup(lambda:(stopped.set(),thread.join(3)))
        if delay==0:self.assertTrue(started.wait(3))
        return urllib.request.Request('http://127.0.0.1:'+str(port)+'/selections'),state

    def test_delayed_real_listener_is_ready_within_budget(self):
        request,state=self.listener(delay=.2);observations=[];pid=os.getpid()
        def verify():
            self.assertEqual(os.getpid(),pid);observations.append(time.monotonic())
        result=wait_http_json(urllib.request.build_opener(urllib.request.ProxyHandler({})),request,verify,lambda x:self.assertTrue(x['ready']),timeout=2)
        self.assertEqual(result,{'ready':True});self.assertGreaterEqual(len(observations),2);self.assertEqual(state['requests'],1)

    def test_non200_is_never_retried(self):
        request,state=self.listener(status=503)
        with self.assertRaises(urllib.error.HTTPError):wait_http_json(urllib.request.build_opener(),request,lambda:None,lambda x:None,timeout=2)
        self.assertEqual(state['requests'],1)

    def test_invalid_json_is_never_retried(self):
        request,state=self.listener(body=b'not-json')
        with self.assertRaises(json.JSONDecodeError):wait_http_json(urllib.request.build_opener(),request,lambda:None,lambda x:None,timeout=2)
        self.assertEqual(state['requests'],1)

    def test_invalid_structure_is_never_retried(self):
        request,state=self.listener(body=b'{}')
        with self.assertRaises(KeyError):wait_http_json(urllib.request.build_opener(),request,lambda:None,lambda x:x['ready'],timeout=2)
        self.assertEqual(state['requests'],1)

    def test_process_identity_failure_stops_before_http(self):
        request,state=self.listener()
        def reject():raise ValueError('CONTROL_PID_CHANGED')
        with self.assertRaisesRegex(ValueError,'CONTROL_PID_CHANGED'):wait_http_json(urllib.request.build_opener(),request,reject,lambda x:None,timeout=2)
        self.assertEqual(state['requests'],0)

    def test_no_listener_fails_within_budget(self):
        request,state=self.listener(delay=3);started=time.monotonic()
        with self.assertRaises((ValueError,urllib.error.URLError)):
            wait_http_json(urllib.request.build_opener(),request,lambda:None,lambda x:None,timeout=.25)
        self.assertLess(time.monotonic()-started,1);self.assertEqual(state['requests'],0)


if __name__=='__main__':unittest.main()
