"""Install/update the frozen SCM service from an elevated Windows console."""
import argparse
import ctypes
import json
from pathlib import Path
import socket
import sys
import time
import urllib.request

import win32api
import win32service
import win32serviceutil
import win32security
import ntsecuritycon

from executor_service import SERVICE_NAME, load_descriptor


def health(config):
    request = urllib.request.Request('http://127.0.0.1:' + str(config['port']) + '/state',
                                     headers={'X-Release-Key':config['bridgeKey']})
    return json.load(urllib.request.urlopen(request, timeout=15))


def control_service(action):
    """Use the operator's service-specific permissions, not SCM admin rights."""
    access = {'start': win32service.SERVICE_START, 'stop': win32service.SERVICE_STOP}[action]
    manager = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_CONNECT)
    try:
        handle = win32service.OpenService(manager, SERVICE_NAME, access)
        try:
            if action == 'start':
                win32service.StartService(handle, None)
            else:
                win32service.ControlService(handle, win32service.SERVICE_CONTROL_STOP)
        finally:
            win32service.CloseServiceHandle(handle)
    finally:
        win32service.CloseServiceHandle(manager)


def require_idle_console(process, state):
    if any(job['status'] == 'running' for job in state['jobs']):
        raise RuntimeError('Original executor still has running release jobs')
    console_host = (Path(win32api.GetSystemDirectory()) / 'conhost.exe').resolve(strict=True)
    for child in process.children(recursive=True):
        # A Windows console host belongs to the console, not a release job.
        # Verify its real executable and direct parent; a name alone is insufficient.
        if (child.name().lower() == 'conhost.exe' and child.ppid() == process.pid
                and Path(child.exe()).resolve(strict=True) == console_host):
            continue
        raise RuntimeError(f'Original executor still has a child process (PID {child.pid}); '
                           'wait for it to finish before installing the service')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('install', 'update', 'start', 'stop', 'restart', 'status'))
    parser.add_argument('--descriptor', required=True)
    parser.add_argument('--replace-console-pid', type=int)
    parser.add_argument('--expected-console-script')
    args = parser.parse_args()
    root, config = load_descriptor(args.descriptor)
    if args.action == 'status':
        status = win32serviceutil.QueryServiceStatus(SERVICE_NAME)
        print(json.dumps(dict(serviceName=SERVICE_NAME, serviceStatus=status[1],
                              runtime=health(config)['executorRuntime'] if status[1] == win32service.SERVICE_RUNNING else None)))
        return
    if args.action in ('install', 'update') and not ctypes.windll.shell32.IsUserAnAdmin():
        raise RuntimeError('Windows service installation/control requires an Administrator console')
    if args.replace_console_pid:
        import psutil
        if args.action != 'install' or not args.expected_console_script:
            raise RuntimeError('Explicit original console script identity required for first install')
        process = psutil.Process(args.replace_console_pid)
        expected = Path(args.expected_console_script).resolve(strict=True)
        commands = process.cmdline()
        if process.name().lower() != 'python.exe' or not any(
                Path(part).resolve() == expected for part in commands if part.endswith('.py')):
            raise RuntimeError('Original console process identity differs')
        state = health(config)
        require_idle_console(process, state)
        # Bound process handle protects against PID reuse between check and stop.
        process.terminate()
        process.wait(timeout=20)
    if args.action == 'install':
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1', config['port'])) == 0:
                raise RuntimeError('Executor listener still active; refusing a second executor')
        manager = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
        try:
            existing = {item[0] for item in win32service.EnumServicesStatus(manager)}
        finally:
            win32service.CloseServiceHandle(manager)
        module = str(root / 'source/ops/spug/release-center/executor_service') + '.ReleaseExecutorService'
        if SERVICE_NAME in existing:
            raise RuntimeError('Service already exists; stop it explicitly before updating its fixed descriptor')
        win32serviceutil.InstallService(module, SERVICE_NAME, 'IntRuoyi Release Executor',
                startType=win32service.SERVICE_AUTO_START, delayedstart=True,
                description='Persistent Spug release executor with explicit interruption reconciliation')
        win32serviceutil.SetServiceCustomOption(SERVICE_NAME, 'Descriptor', str(Path(args.descriptor).resolve()))
        manager = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
        handle = win32service.OpenService(manager, SERVICE_NAME, win32service.SERVICE_ALL_ACCESS)
        try:
            win32service.ChangeServiceConfig2(handle, win32service.SERVICE_CONFIG_FAILURE_ACTIONS,
                dict(ResetPeriod=86400, RebootMsg='', Command='', Actions=[(win32service.SC_ACTION_RESTART, 10000)] * 3))
            win32service.ChangeServiceConfig2(handle, win32service.SERVICE_CONFIG_FAILURE_ACTIONS_FLAG, True)
            descriptor = json.loads(Path(args.descriptor).read_text('utf-8'))
            sid = win32security.ConvertStringSidToSid(descriptor['operatorSid'])
            security = win32security.GetSecurityInfo(handle, win32security.SE_SERVICE, win32security.DACL_SECURITY_INFORMATION)
            acl = security.GetSecurityDescriptorDacl()
            if acl is None:
                raise RuntimeError('Service access control list is absent')
            acl.AddAccessAllowedAce(win32security.ACL_REVISION,
                win32service.SERVICE_QUERY_STATUS | win32service.SERVICE_QUERY_CONFIG | win32service.SERVICE_START
                | win32service.SERVICE_STOP | win32service.SERVICE_INTERROGATE | ntsecuritycon.READ_CONTROL, sid)
            win32security.SetSecurityInfo(handle, win32security.SE_SERVICE, win32security.DACL_SECURITY_INFORMATION,
                                         None, None, acl, None)
        finally:
            win32service.CloseServiceHandle(handle)
            win32service.CloseServiceHandle(manager)
        control_service('start')
    elif args.action in ('stop', 'restart', 'update'):
        control_service('stop')
        win32serviceutil.WaitForServiceStatus(SERVICE_NAME, win32service.SERVICE_STOPPED, 60)
        if args.action == 'update':
            module = str(root / 'source/ops/spug/release-center/executor_service') + '.ReleaseExecutorService'
            win32serviceutil.ChangeServiceConfig(module, SERVICE_NAME, startType=win32service.SERVICE_AUTO_START,
                                                 delayedstart=True)
            win32serviceutil.SetServiceCustomOption(SERVICE_NAME, 'Descriptor', str(Path(args.descriptor).resolve()))
        if args.action in ('restart', 'update'):
            control_service('start')
    else:
        control_service('start')
    if args.action != 'stop':
        win32serviceutil.WaitForServiceStatus(SERVICE_NAME, win32service.SERVICE_RUNNING, 30)
        deadline = time.monotonic() + 30
        while True:
            try:
                state = health(config)
                break
            except urllib.error.URLError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(.5)
        if state['executorRuntime']['mode'] != 'windows-service':
            raise RuntimeError('Listener is not the selected SCM executor')
        print(json.dumps(dict(service=SERVICE_NAME, runtime=state['executorRuntime'],
                              activeJobs=sum(j['status']=='running' for j in state['jobs']))))


if __name__ == '__main__':
    main()
