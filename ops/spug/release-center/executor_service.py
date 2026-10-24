"""Dedicated Windows SCM service. No scheduled task, desktop window, or PID edits."""
import hashlib
import json
import os
from pathlib import Path
import threading
import sys

import win32api
import win32job
import win32service
import win32serviceutil

SERVICE_NAME = 'IntRuoyiReleaseExecutor'


def load_descriptor(path):
    path = Path(path).resolve(strict=True)
    descriptor = json.loads(path.read_text('utf-8'))
    root = path.parent
    hashes = json.loads((root / 'source-sha256.json').read_text('utf-8'))
    for relative, expected in hashes.items():
        source = (root / 'source' / relative).resolve(strict=True)
        if root / 'source' not in source.parents or hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise RuntimeError('Frozen service source identity differs: ' + relative)
    expected_file = root / 'source/ops/spug/release-center/executor_service.py'
    if Path(__file__).resolve() != expected_file.resolve():
        raise RuntimeError('Service module is not the selected frozen source')
    for key, value in descriptor['environment'].items():
        if key not in {'PATH', 'JAVA_HOME', 'MAVEN_HOME', 'M2_HOME', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA',
                       'TEMP', 'TMP', 'DOCKER_CONFIG', 'DOCKER_HOST', 'DOCKER_CONTEXT', 'PNPM_HOME'}:
            raise RuntimeError('Unexpected service environment variable: ' + key)
        os.environ[key] = value
    config = json.loads(Path(descriptor['config']).read_text('utf-8-sig'))
    config['executionMode'] = 'windows-service'
    return root, config


def own_process_tree():
    handle = win32job.CreateJobObject(None, '')
    info = win32job.QueryInformationJobObject(handle, win32job.JobObjectExtendedLimitInformation)
    info['BasicLimitInformation']['LimitFlags'] = win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    win32job.SetInformationJobObject(handle, win32job.JobObjectExtendedLimitInformation, info)
    win32job.AssignProcessToJobObject(handle, win32api.GetCurrentProcess())
    return handle


class ReleaseExecutorService(win32serviceutil.ServiceFramework):
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = 'IntRuoyi Release Executor'
    _svc_description_ = 'Persistent Spug release executor; interrupted operations require reconciliation.'

    def __init__(self, args):
        super().__init__(args)
        self.stopping = threading.Event()
        self.executor = None

    def SvcStop(self):
        if self.executor is not None:
            with self.executor.lock:
                self.executor.draining = True
        self.stopping.set()
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING, waitHint=30000)

    def SvcDoRun(self):
        root, config = load_descriptor(win32serviceutil.GetServiceCustomOption(self._svc_name_, 'Descriptor'))
        sys.stdout = (root / 'service.stdout.log').open('a', encoding='utf-8', buffering=1)
        sys.stderr = (root / 'service.stderr.log').open('a', encoding='utf-8', buffering=1)
        # Keep this handle for the process lifetime. An abnormal host exit closes
        # it and kills only this executor's inherited local child processes.
        self.process_tree = own_process_tree()
        os.chdir(root / 'source')
        from executor import create_server
        from intruoyi_executor import IntRuoyiExecutor
        self.executor = IntRuoyiExecutor(config)
        server = create_server(self.executor, config)
        server.timeout = 1
        try:
            while True:
                if self.stopping.is_set():
                    with self.executor.lock:
                        self.executor.draining = True
                        running = any(j['status'] == 'running' for j in self.executor.state['jobs'])
                    if not running and not (self.executor.worker and self.executor.worker.is_alive()):
                        break
                    self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING, waitHint=30000)
                server.handle_request()
        finally:
            server.server_close()
            self.executor.process_lock.close()


if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(ReleaseExecutorService)
