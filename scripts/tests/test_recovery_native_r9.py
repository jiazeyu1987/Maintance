"""R9 credential-selection and readiness unit checks, not Linux attestations."""
import ast
import errno
from pathlib import Path
import socket
import stat
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ops/recovery'))
import recovery_environment_supervisor as supervision
import recovery_native_launcher as launcher
import recovery_native_signer as signer
from recovery_environment_contract import EnvironmentFailure
from recovery_native_observation import receive_frame


def selected_start(uid=0, gid=0):
    return dict(workerUid=uid, workerGid=gid, argv=['selected-python', 'admit-installation'],
                env={'INTRUOYI_NATIVE_DEADLINE_MONOTONIC': '120'}, passFds=[])


def inherited_ids(monkeypatch, uids=(0, 0, 0), gids=(0, 0, 0), groups=()):
    # These are explicit syscall-return fixtures. Never change host credentials.
    monkeypatch.setattr(supervision, 'os', SimpleNamespace(getresuid=lambda: uids,
        getresgid=lambda: gids, getgroups=lambda: list(groups)))


@pytest.mark.parametrize('uid,gid', [(0, 0), (24001, 24002)])
def test_exact_inherited_identity_omits_all_privileged_popen_arguments(monkeypatch, uid, gid):
    inherited_ids(monkeypatch, (uid,)*3, (gid,)*3)
    calls = []
    child = SimpleNamespace(pid=51)
    monkeypatch.setattr(supervision.subprocess, 'Popen', lambda argv, **kw: calls.append((argv, kw)) or child)
    parent = supervision.Supervisor.__new__(supervision.Supervisor)
    parent.inherit_identity = True; parent.spawn_attempted = False; parent.worker = None
    parent.spawn_worker(selected_start(uid, gid))
    assert parent.worker is child and parent.spawn_attempted
    assert calls == [(['selected-python', 'admit-installation'], dict(stdin=0, stdout=1, stderr=2,
        env={'INTRUOYI_NATIVE_DEADLINE_MONOTONIC':'120'}, pass_fds=(), start_new_session=True))]


@pytest.mark.parametrize('damage', ['real-uid', 'effective-uid', 'saved-uid', 'real-gid',
    'effective-gid', 'saved-gid', 'group-zero', 'foreign-group', 'missing-selection', 'bool-uid', 'bool-mode'])
def test_wrong_inherited_identity_fails_before_spawn_attempt(monkeypatch, damage):
    uids = [0]*3; gids = [0]*3; groups = []
    for index, prefix in enumerate(('real', 'effective', 'saved')):
        if damage == prefix+'-uid': uids[index] = 1
        if damage == prefix+'-gid': gids[index] = 1
    if damage == 'group-zero': groups = [0]
    if damage == 'foreign-group': groups = [24000]
    inherited_ids(monkeypatch, tuple(uids), tuple(gids), groups)
    calls = []
    monkeypatch.setattr(supervision.subprocess, 'Popen', lambda *a, **kw: calls.append(True))
    start = selected_start()
    if damage == 'missing-selection': start.update(workerUid=None, workerGid=None)
    if damage == 'bool-uid': start['workerUid'] = False
    parent = supervision.Supervisor.__new__(supervision.Supervisor)
    parent.inherit_identity = 1 if damage == 'bool-mode' else True
    parent.spawn_attempted = False; parent.worker = None
    with pytest.raises(supervision.SupervisionFailure): parent.spawn_worker(start)
    assert not calls and not parent.spawn_attempted and parent.worker is None


@pytest.mark.parametrize('uid,gid', [(0, 0), (24001, 24002), (None, None)])
def test_explicit_identity_change_retains_original_arguments_and_failure(monkeypatch, uid, gid):
    inherited_ids(monkeypatch, (17, 18, 19), (27, 28, 29), (37,))
    calls = []; original = PermissionError(errno.EPERM, 'unit dispatch denied')
    def denied(argv, **kwargs):
        calls.append(kwargs)
        raise original
    monkeypatch.setattr(supervision.subprocess, 'Popen', denied)
    parent = supervision.Supervisor.__new__(supervision.Supervisor)
    parent.inherit_identity = False; parent.spawn_attempted = False; parent.worker = None
    with pytest.raises(PermissionError) as caught: parent.spawn_worker(selected_start(uid, gid))
    assert caught.value is original and parent.spawn_attempted and parent.worker is None
    expected = dict(stdin=0, stdout=1, stderr=2, env={'INTRUOYI_NATIVE_DEADLINE_MONOTONIC':'120'},
                    pass_fds=(), start_new_session=True)
    if uid is not None: expected.update(user=uid, group=gid, extra_groups=())
    assert calls == [expected]


@pytest.mark.parametrize('inherit', [True, False])
def test_selected_mode_reaches_dedicated_supervisor_cli(monkeypatch, inherit):
    # Use real local socketpair FD ownership, but capture process creation only.
    calls = []
    monkeypatch.setattr(supervision.subprocess, 'Popen',
        lambda argv, **kwargs: calls.append((argv, kwargs)) or SimpleNamespace(pid=52))
    parent = supervision.OwnedChildSupervisor(['selected-python'], env={}, stdin=None,
        user=0, group=0, no_new_privileges=True, inherit_identity=inherit)
    try:
        parent.spawn()
        assert calls[0][0][1:5] == ['-I', '-S', str(supervision.SUPERVISOR_SCRIPT), '--supervise']
        assert calls[0][0][6:] == (['--inherit-selected-identity'] if inherit else [])
        assert not {'user', 'group', 'extra_groups'} & calls[0][1].keys()
    finally: parent.close()


def test_native_producer_explicitly_selects_inheritance_without_relaxing_nnp():
    tree = ast.parse((ROOT/'ops/recovery/recovery_native_process.py').read_text(encoding='utf-8'))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and
             isinstance(n.func, ast.Name) and n.func.id == 'OwnedChildSupervisor']
    assert len(calls) == 1
    options = {k.arg:k.value for k in calls[0].keywords}
    assert ast.literal_eval(options['inherit_identity']) is True
    assert ast.literal_eval(options['no_new_privileges']) is True
    assert ast.unparse(options['user']) == 'self.uid' and ast.unparse(options['group']) == 'self.gid'


@pytest.mark.parametrize('failure_stage', [None, 'bind', 'chmod', 'chown', 'custody', 'listen',
    'measurement', 'stable-custody', 'expired-before-ready'])
def test_authority_ready_requires_listen_custody_and_measurement(monkeypatch, failure_stage):
    # Run actual serve + launcher handoff code with explicit socket/OS fixtures.
    # Only the ready-frame transport is real local socketpair I/O on Windows.
    events = []; clock = SimpleNamespace(now=1.0)
    def event(stage):
        events.append(stage)
        if stage == failure_stage: raise OSError(errno.EPERM, stage)
    class Channel:
        def __enter__(self): return self
        def __exit__(self, *args): event('channel-closed')
        def settimeout(self, timeout): assert timeout > 0
        def recv(self, size): return b'{"finishLaunchPin":{"selected":1}}\n'
        def sendall(self, data):
            assert data == b'{"finishedLaunchPin":{"selected":1}}\n'
            event('first-request-replied')
    class Server:
        def __enter__(self): return self
        def __exit__(self, *args): event('listener-closed')
        def bind(self, path): event('bind')
        def listen(self, backlog): assert backlog == 1; event('listen')
        def accept(self): event('accept'); return Channel(), None
    path = SimpleNamespace(parent=SimpleNamespace(stat=lambda: SimpleNamespace(
        st_uid=0, st_gid=0, st_mode=stat.S_IFDIR|0o700)))
    def chmod(actual, mode): assert actual is path and mode == 0o600; event('chmod')
    def chown(actual, uid, gid, **kwargs):
        assert actual is path and uid == gid == 0 and kwargs == {'follow_symlinks':False}
        event('chown')
    token = object()
    def custody(actual, previous=None):
        assert actual is path
        if previous is None: event('custody')
        else: assert previous is token; event('stable-custody')
        return token
    def guard():
        event('measurement')
        if failure_stage == 'expired-before-ready': clock.now = 101.0
    monkeypatch.setattr(signer, 'socket', SimpleNamespace(AF_UNIX=1, SOCK_STREAM=1, socket=lambda *a: Server()))
    monkeypatch.setattr(signer, 'os', SimpleNamespace(chmod=chmod, chown=chown))
    monkeypatch.setattr(signer, 'time', SimpleNamespace(monotonic=lambda: clock.now))
    monkeypatch.setattr(signer, 'signer_socket_custody', custody)
    monkeypatch.setattr(signer, 'select', SimpleNamespace(select=lambda readers, *a: (readers, [], [])))
    service = signer.AuthoritySigningService.__new__(signer.AuthoritySigningService)
    service.path = path; service.deadline = 100.0; service.launch_pin = {'selected':1}
    service.guard = guard; service._live_peer = lambda channel: event('peer-checked')
    service.publish_current_identity = lambda proof, expires: {'identity':1}
    context = SimpleNamespace(proof_pin={'proof':1}, expires_at='selected-expiry', deadline=100.0)
    receiver, sender = socket.socketpair()
    original_send = launcher.send_frame
    def send_ready(channel, payload, deadline):
        event('ready')
        assert events[:7] == ['bind','chmod','chown','custody','listen','measurement','stable-custody']
        # Fixture deadline is independent of this real local transport deadline.
        import time
        assert deadline == context.deadline
        original_send(channel, payload, time.monotonic()+2)
    monkeypatch.setattr(launcher, 'send_frame', send_ready)
    try:
        if failure_stage:
            with pytest.raises((OSError, EnvironmentFailure)): launcher.serve_authority(context, service, sender)
            assert 'ready' not in events and 'accept' not in events
            receiver.setblocking(False)
            with pytest.raises(BlockingIOError): receiver.recv(1)
        else:
            launcher.serve_authority(context, service, sender)
            import time
            assert receive_frame(receiver, time.monotonic()+2) == {
                'schemaVersion':'RepositoryLabNativeAuthorityReady/v1', 'authorityIdentityPin':{'identity':1}}
            assert events.count('ready') == 1 and events.index('ready') < events.index('accept')
            assert 'first-request-replied' in events
        assert events[-1] == 'listener-closed'
    finally: receiver.close(); sender.close()
