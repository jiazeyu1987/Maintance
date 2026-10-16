"""Explicit Linux owned-child supervision; no PID lookup is a signal handle.

One private supervisor owns exactly one newly created worker session. It is a
subreaper and never reaps a child until all signals to that child are finished.
Linux retains a direct child's PID (including its zombie) until this sole parent
waits for it. Consequently kill(pid) cannot hit a reused PID in this interval.
Descendants are reached by killing owned parents then adopting their orphans,
including descendants that changed session; no process-group/UID/name kill is
used. A lost supervisor/proof/boundary is UNKNOWN, never a cleanup assertion.
"""
from __future__ import annotations

import ctypes
import json
import math
import os
from pathlib import Path
import select
import signal
import socket
import subprocess
import sys
import time

MODEL = "linux-owned-child-subreaper-v1"
SUPERVISOR_SCRIPT = Path(__file__).resolve()
MAX_FRAME = 1024 * 1024


class SupervisionFailure(Exception):
    def __init__(self, code, *, unknown=True):
        self.code, self.unknown = code, unknown
        super().__init__(code)


def check(condition, code):
    if not condition:
        raise SupervisionFailure(code)


def prepare_local_supervision():
    if os.name != "posix":
        return
    check(sys.platform == "linux" and all(hasattr(os, name) for name in
          ("waitid", "WNOWAIT", "WEXITED", "WNOHANG", "P_PID", "fork")),
          "LOCAL_TASK_SUPERVISION_UNAVAILABLE")
    check(signal.getsignal(signal.SIGCHLD) != signal.SIG_IGN,
          "LOCAL_TASK_CHILD_AUTO_REAP_REJECTED")
    # prctl is performed inside the dedicated supervisor, never on a shared
    # calling process. This parent only proves the selected /proc interface.
    Path(f"/proc/self/task/{os.getpid()}/children").read_text(encoding="ascii")


def identity(pid):
    path = Path("/proc") / str(pid)
    raw = (path / "stat").read_bytes()
    fields = raw[raw.rindex(b")") + 2:].split()
    status = dict(line.split(':', 1) for line in (path / 'status').read_text(encoding='ascii').splitlines())
    return {"pid": pid, "state": fields[0].decode("ascii"), "parent": int(fields[1]),
            "group": int(fields[2]), "session": int(fields[3]), "startTicks": int(fields[19]),
            "uid": int(status['Uid'].split()[1]), "gid": int(status['Gid'].split()[1])}


def _send(channel, message):
    data = json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n"
    check(len(data) <= MAX_FRAME, "LOCAL_SUPERVISOR_FRAME_LIMIT")
    channel.sendall(data)


def worker_identity_arguments(uid, gid, *, inherit_identity):
    """Select exec credentials without mutating an already exact identity."""
    check(type(inherit_identity) is bool, 'LOCAL_SUPERVISOR_IDENTITY_MODE_INVALID')
    check((uid is None and gid is None) or
          (type(uid) is int and uid >= 0 and type(gid) is int and gid >= 0),
          'LOCAL_SUPERVISOR_WORKER_IDENTITY_INVALID')
    if inherit_identity:
        check(uid is not None and gid is not None, 'LOCAL_SUPERVISOR_SELECTED_IDENTITY_REQUIRED')
        check(os.getresuid() == (uid, uid, uid) and os.getresgid() == (gid, gid, gid) and
              os.getgroups() == [], 'LOCAL_SUPERVISOR_INHERITED_IDENTITY_MISMATCH')
        # Even setgroups(0, NULL) requires CAP_SETGID. This mode proves that
        # no set*id/setgroups operation is needed before exec, never retries it.
        return {}
    return {'user': uid, 'group': gid, 'extra_groups': ()} if uid is not None else {}


class OwnedChildSupervisor:
    """CommandRunner adapter. returncode is the actual worker's wait status."""
    def __init__(self, argv, *, env, stdin, pass_fds=(), cwd=None, user=None, group=None,
                 no_new_privileges=False, inherit_identity=False):
        self.argv, self.env, self.stdin, self.pass_fds = argv, env, stdin, tuple(pass_fds)
        self.cwd, self.user, self.group = cwd, user, group
        self.no_new_privileges = no_new_privileges
        check(type(inherit_identity) is bool, 'LOCAL_SUPERVISOR_IDENTITY_MODE_INVALID')
        self.inherit_identity = inherit_identity
        self.process = None
        self.channel = None
        self.pid = None
        self.supervisor_pid = None
        self.returncode = None
        self.worker_dispatched = None
        self.terminal = None
        self.observed = []
        self.buffer = b""
        self.output = self.error = b""
        self.channel_closed = False
        self.ready = False
        self.supervisor_identity = None
        self.dispatch = None

    def spawn(self):
        # Check caller-owned descriptors before allocating the private channel:
        # an invalid requested number must not become valid by socket FD reuse.
        for fd in self.pass_fds:
            check(type(fd) is int and fd >= 0, "LOCAL_TASK_PASS_FD_INVALID")
            os.fstat(fd)
        parent, child = socket.socketpair()
        try:
            self.process = subprocess.Popen(
                [sys.executable, "-I", "-S", str(SUPERVISOR_SCRIPT), "--supervise", str(child.fileno()),
                 *(['--inherit-selected-identity'] if self.inherit_identity else [])],
                stdin=subprocess.PIPE if self.stdin is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True,
                pass_fds=(*self.pass_fds, child.fileno()), env=self.env,
                cwd=self.cwd)
            self.supervisor_pid = self.process.pid
            self.channel = parent
        except BaseException:
            parent.close()
            raise
        finally:
            child.close()

    def start(self, timeout, *, guard=lambda: None, deadline=None):
        self.channel.settimeout(timeout)
        _send(self.channel, {"kind": "START", "model": MODEL, "argv": self.argv,
                            "env": self.env, "passFds": list(self.pass_fds),
                            "noNewPrivileges": self.no_new_privileges,
                            "workerUid": self.user, "workerGid": self.group})
        until = time.monotonic() + timeout
        dispatched = False
        while self.pid is None and self.terminal is None:
            guard()
            self._receive(min(0.05, max(0.001, until - time.monotonic())))
            if self.ready and not dispatched and self.terminal is None:
                # Capabilities are established before this renewed live gate.
                # The helper cannot create its worker until this explicit message.
                guard()
                _send(self.channel, {"kind": "DISPATCH", "deadlineMonotonic": until if deadline is None else deadline})
                dispatched = True
            if time.monotonic() >= until and self.pid is None and self.terminal is None:
                guard()  # Preserve the operation's expired deadline/revocation reason.
            check(time.monotonic() < until or self.pid is not None or self.terminal is not None,
                  "LOCAL_SUPERVISOR_START_DEADLINE")
        if self.terminal is not None:
            check(self.terminal.get("treeTerminated") is True, "LOCAL_TASK_TREE_TERMINATION_UNPROVEN")
            raise SupervisionFailure(self.terminal["failureCode"], unknown=self.terminal["unknown"])

    def _receive(self, timeout=0):
        if self.channel_closed:
            return
        readable, _, _ = select.select([self.channel], [], [], timeout)
        if not readable:
            return
        data = self.channel.recv(65536)
        if not data:
            self.channel_closed = True
            return
        self.buffer += data
        check(len(self.buffer) <= MAX_FRAME, "LOCAL_SUPERVISOR_FRAME_LIMIT")
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            message = json.loads(line)
            check(message["model"] == MODEL and message["supervisorPid"] == self.supervisor_pid,
                  "LOCAL_SUPERVISOR_IDENTITY_UNPROVEN")
            if message["kind"] == "READY":
                check(not self.ready and self.pid is None, "LOCAL_SUPERVISOR_READY_INVALID")
                self.supervisor_identity = message["supervisorIdentity"]
                check(self.supervisor_identity["pid"] == self.supervisor_pid,
                      "LOCAL_SUPERVISOR_IDENTITY_UNPROVEN")
                self.ready = True
            elif message["kind"] == "STARTED":
                check(self.pid is None and message["worker"]["parent"] == self.supervisor_pid and
                      message["worker"]["pid"] == message["worker"]["group"] == message["worker"]["session"],
                      "LOCAL_TASK_GROUP_IDENTITY_UNPROVEN")
                self.pid = message["worker"]["pid"]
                self.worker_dispatched = True
                self.observed = [message["worker"]]
                self.dispatch = message["dispatch"]
                check(self.dispatch["argv"] == self.argv and
                      (self.cwd is None or self.dispatch["cwd"] == self.cwd),
                      "LOCAL_SUPERVISOR_COMMAND_CHANGED")
            elif message["kind"] == "TERMINAL":
                check(self.terminal is None and message["workerPid"] == self.pid,
                      "LOCAL_SUPERVISOR_TERMINAL_IDENTITY_UNPROVEN")
                self.terminal = message
                self.worker_dispatched = message["workerDispatched"]
                self.returncode = message["actualExitCode"]
                self.observed = message["children"]
            else:
                raise SupervisionFailure("LOCAL_SUPERVISOR_MESSAGE_INVALID")

    def communicate(self, pending_input=None, timeout=None):
        # Only the supervisor is waited for here. It must have reaped its whole
        # owned tree and emitted a terminal proof before its own exit is usable.
        try:
            self.output, self.error = self.process.communicate(pending_input, timeout=timeout)
        except subprocess.TimeoutExpired:
            self._receive(0)
            raise
        while not self.channel_closed:
            self._receive(0.1)
        check(self.terminal is not None and not self.buffer and self.process.returncode == 0,
              "LOCAL_SUPERVISOR_TERMINAL_UNPROVEN")
        check(self.terminal["treeTerminated"] is True, "LOCAL_TASK_TREE_TERMINATION_UNPROVEN")
        return self.output, self.error

    def members(self):
        check(self.terminal is not None, "LOCAL_SUPERVISOR_TERMINAL_UNPROVEN")
        if self.terminal["unknown"]:
            raise SupervisionFailure(self.terminal["failureCode"])
        check(self.terminal["reason"] != "CHILDREN_AFTER_WORKER_EXIT", "LOCAL_TASK_CHILDREN_STILL_RUNNING")
        check(self.terminal["failureCode"] is None, self.terminal["failureCode"])
        return []

    def terminate(self, process=None, seconds=5):
        if self.terminal is None:
            # Closing this private endpoint wakes the sole supervisor even when
            # sending CANCEL fails. No guessed PID or process group is signalled.
            try:
                self.channel.shutdown(socket.SHUT_WR)
            except OSError:
                self.channel.close()
                self.channel_closed = True
        until = time.monotonic() + seconds + 1
        while True:
            check(time.monotonic() < until, "LOCAL_TASK_TREE_TERMINATION_UNPROVEN")
            try:
                output, error = self.communicate(timeout=min(0.1, until - time.monotonic()))
                break
            except subprocess.TimeoutExpired:
                continue
        check(self.terminal["treeTerminated"], "LOCAL_TASK_TREE_TERMINATION_UNPROVEN")
        return output, error

    def proof(self, terminated):
        return [{"pid": item["pid"], "startTicks": item["startTicks"],
                 "state": "TERMINATED" if terminated and item.get("reaped") else "TERMINATION_UNPROVEN",
                 "parentAtSignal": item.get("parentAtSignal"),
                 "signalOwnership": item.get("signalOwnership"), "reaped": item.get("reaped", False)}
                for item in self.observed]

    def close(self):
        if self.channel is not None:
            self.channel.close()


class Supervisor:
    """Single threaded sole parent: ownership, not /proc double-checks, pins PID."""
    def __init__(self, channel, *, inherit_identity=False):
        self.channel = channel
        self.pid = os.getpid()
        self.worker = None
        self.worker_pid = None
        self.actual_exit = None
        self.held = {}
        self.history = []
        self.escaped = False
        self.reason = "NORMAL_EXIT"
        self.buffer = b""
        self.spawn_attempted = False
        self.native_identity = None
        self.dispatch = None
        check(type(inherit_identity) is bool, 'LOCAL_SUPERVISOR_IDENTITY_MODE_INVALID')
        self.inherit_identity = inherit_identity

    def spawn_worker(self, start):
        # Verify the supervisor's actual inherited IDs immediately before fork;
        # this dedicated supervisor is single-threaded and does not change them.
        credentials = worker_identity_arguments(start['workerUid'], start['workerGid'],
                                                inherit_identity=self.inherit_identity)
        self.spawn_attempted = True
        self.worker = subprocess.Popen(start['argv'], stdin=0, stdout=1, stderr=2,
            env=start['env'], pass_fds=tuple(start['passFds']), start_new_session=True, **credentials)

    def children(self):
        # A direct child cannot disappear/reuse PID here: SIGCHLD is default,
        # no other thread waits, and this method never calls wait/reaps.
        ids = [int(value) for value in Path(f"/proc/self/task/{self.pid}/children").read_text(encoding="ascii").split()]
        for pid in ids:
            item = identity(pid)
            check(item["parent"] == self.pid, "LOCAL_TASK_CHILD_OWNERSHIP_UNPROVEN")
            if pid not in self.held:
                item["heldMonotonic"] = time.monotonic()
                self.held[pid] = item
            check(self.held[pid]["startTicks"] == item["startTicks"], "LOCAL_TASK_CHILD_IDENTITY_CHANGED")
            if self.worker_pid is not None and (item["group"] != self.worker_pid or item["session"] != self.worker_pid):
                self.escaped = True
        check(set(self.held).issubset(ids), "LOCAL_TASK_CHILD_OWNERSHIP_LOST")
        return ids

    def exited(self, pid):
        return os.waitid(os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)

    def reap(self, pid):
        item = self.held[pid]
        got, status = os.waitpid(pid, os.WNOHANG)
        check(got == pid, "LOCAL_TASK_CHILD_REAP_UNPROVEN")
        if pid == self.worker_pid:
            self.actual_exit = os.waitstatus_to_exitcode(status)
            self.worker.returncode = self.actual_exit
        item.update(reaped=True, actualWaitStatus=status, reapedMonotonic=time.monotonic())
        self.history.append(item)
        del self.held[pid]

    def terminate_tree(self, seconds=5):
        until = time.monotonic() + seconds
        while time.monotonic() < until:
            ids = self.children()
            # No reaping until signals for this snapshot have completed. A
            # direct-child PID remains reserved even if it exits during kill.
            for pid in ids:
                if self.exited(pid) is None:
                    self.held[pid].update(parentAtSignal=self.pid,
                        signalOwnership="SOLE_PARENT_UNREAPED_CHILD")
                    os.kill(pid, signal.SIGKILL)
                    self.held[pid].update(signalSent=True, signalledMonotonic=time.monotonic())
            for pid in ids:
                # Hold the worker/session leader's zombie until every adopted
                # child has finished. It is an additional session identity anchor.
                if pid != self.worker_pid and self.exited(pid) is not None:
                    self.reap(pid)
            ids = self.children()
            if ids == [self.worker_pid] and self.exited(self.worker_pid) is not None:
                self.reap(self.worker_pid)
                check(not self.children(), "LOCAL_TASK_ADOPTION_UNPROVEN")
                return
            if not ids:
                return
            time.sleep(0.01)
        raise SupervisionFailure("LOCAL_TASK_TREE_TERMINATION_UNPROVEN")

    def receive(self, timeout):
        readable, _, _ = select.select([self.channel], [], [], timeout)
        if not readable:
            return None
        data = self.channel.recv(65536)
        if not data:
            return {"kind": "CANCEL"}
        self.buffer += data
        check(len(self.buffer) <= MAX_FRAME, "LOCAL_SUPERVISOR_FRAME_LIMIT")
        if b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            return json.loads(line)
        return None

    def terminal(self, failure=None):
        no_spawn_proven = self.worker_pid is None and (not self.spawn_attempted or
                           isinstance(failure, (FileNotFoundError, PermissionError, ValueError, TypeError)))
        unknown = (failure is not None and not no_spawn_proven) or self.escaped
        code = failure.code if isinstance(failure, SupervisionFailure) else (
            "LOCAL_SUPERVISOR_EXECUTION_OR_IO_FAILED" if failure else
            "LOCAL_TASK_SESSION_BOUNDARY_LOST" if self.escaped else None)
        _send(self.channel, {"kind": "TERMINAL", "model": MODEL, "supervisorPid": self.pid,
            "supervisorIdentity": self.native_identity, "dispatch": self.dispatch,
            "workerPid": self.worker_pid, "workerDispatched": (False if no_spawn_proven else
                                    True if self.worker_pid is not None else None),
            "actualExitCode": self.actual_exit, "treeTerminated": not self.held and not self.children(),
            "children": self.history + list(self.held.values()), "reason": self.reason,
            "unknown": unknown, "failureCode": code})

    def run(self):
        failure = None
        try:
            until = time.monotonic() + 5
            start = None
            while start is None and time.monotonic() < until:
                start = self.receive(0.05)
            check(start is not None and start.get("kind") == "START" and start.get("model") == MODEL,
                  "LOCAL_SUPERVISOR_START_PROTOCOL_FAILED")
            prepare_local_supervision()
            check(os.getpgrp() == self.pid and os.getsid(0) == self.pid,
                  "LOCAL_SUPERVISOR_SESSION_UNPROVEN")
            signal.signal(signal.SIGCHLD, signal.SIG_DFL)
            libc = ctypes.CDLL(None, use_errno=True)
            check(libc.prctl(36, 1, 0, 0, 0) == 0, "LOCAL_TASK_SUBREAPER_UNAVAILABLE")
            actual = ctypes.c_int()
            check(libc.prctl(37, ctypes.byref(actual), 0, 0, 0) == 0 and actual.value == 1,
                  "LOCAL_TASK_SUBREAPER_UNPROVEN")
            check(type(start["noNewPrivileges"]) is bool, "LOCAL_SUPERVISOR_START_PROTOCOL_FAILED")
            check((start['workerUid'] is None and start['workerGid'] is None) or
                  (type(start['workerUid']) is int and start['workerUid'] >= 0 and
                   type(start['workerGid']) is int and start['workerGid'] >= 0),
                  'LOCAL_SUPERVISOR_WORKER_IDENTITY_INVALID')
            if start["noNewPrivileges"]:
                check(libc.prctl(38, 1, 0, 0, 0) == 0,
                      "LOCAL_TASK_NO_NEW_PRIVILEGES_UNPROVEN")
            check(type(start["argv"]) is list and type(start["passFds"]) is list,
                  "LOCAL_SUPERVISOR_START_PROTOCOL_FAILED")
            self.native_identity = dict(identity(self.pid), uid=os.getuid(), gid=os.getgid(),
                bootId=Path('/proc/sys/kernel/random/boot_id').read_text(encoding='ascii').strip(),
                namespaces={name: os.readlink('/proc/self/ns/' + name)
                            for name in ('pid', 'mnt', 'net', 'user')})
            _send(self.channel, {"kind": "READY", "model": MODEL, "supervisorPid": self.pid,
                                 "supervisorIdentity": self.native_identity})
            dispatch = None
            while dispatch is None and time.monotonic() < until:
                dispatch = self.receive(0.05)
            check(dispatch is not None and dispatch.get("kind") == "DISPATCH",
                  "LOCAL_SUPERVISOR_DISPATCH_NOT_AUTHORIZED")
            budget = dispatch["deadlineMonotonic"]
            check(type(budget) in (int, float) and math.isfinite(budget) and time.monotonic() < budget,
                  "LOCAL_SUPERVISOR_DISPATCH_DEADLINE_EXCEEDED")
            self.spawn_worker(start)
            self.worker_pid = self.worker.pid
            self.children()
            # Successful Popen has consumed the exec-error pipe. These are the
            # sole parent's actual exec inputs, not a worker-written receipt.
            self.dispatch = {"argv": start["argv"], "cwd": os.getcwd(),
                             "uid": self.held[self.worker_pid]['uid'],
                             "gid": self.held[self.worker_pid]['gid']}
            _send(self.channel, {"kind": "STARTED", "model": MODEL, "supervisorPid": self.pid,
                                 "worker": self.held[self.worker_pid], "dispatch": self.dispatch})
            while True:
                ids = self.children()
                if self.exited(self.worker_pid) is not None:
                    if ids != [self.worker_pid]:
                        self.reason = "CHILDREN_AFTER_WORKER_EXIT"
                        self.terminate_tree()
                    else:
                        self.reap(self.worker_pid)
                    break
                message = self.receive(0.02)
                if message is not None:
                    check(message.get("kind") == "CANCEL", "LOCAL_SUPERVISOR_CONTROL_INVALID")
                    self.reason = "CANCELLED"
                    self.terminate_tree()
                    break
        except BaseException as exc:
            failure = exc
            try:
                self.terminate_tree()
            except BaseException:
                failure = SupervisionFailure("LOCAL_TASK_TREE_TERMINATION_UNPROVEN")
        # I/O failure here is a nonzero supervisor exit. The caller cannot infer
        # worker/tree success from either that exit or mere worker stdout.
        self.terminal(failure)


def main():
    check(len(sys.argv) in (3, 4) and sys.argv[1] == "--supervise" and
          (len(sys.argv) == 3 or sys.argv[3] == '--inherit-selected-identity'),
          "LOCAL_SUPERVISOR_ARGUMENT_INVALID")
    with socket.socket(fileno=int(sys.argv[2])) as channel:
        Supervisor(channel, inherit_identity=len(sys.argv) == 4).run()


if __name__ == "__main__":
    main()
