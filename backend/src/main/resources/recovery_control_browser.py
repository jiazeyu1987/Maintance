"""W01 explicit browser-v2 entry, called only in the owner's already selected inherited role.

No identity conversion, default deadline, default grant, root-proof promotion,
or browser execution from the control JVM. The real owned broker channel is
supplied by the existing privileged bootstrap, never constructed here.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import socket
import sys
import time


def require(condition, code):
    if not condition:
        raise RuntimeError(code)


def pin(value):
    require(type(value) is dict and set(value) == {'path', 'bytes', 'sha256'} and
            type(value['bytes']) is int and value['bytes'] >= 0 and
            type(value['path']) is str and value['path'].startswith('/') and
            '\\' not in value['path'] and '\x00' not in value['path'] and
            all(part not in ('', '.', '..') for part in value['path'].split('/')[1:]) and
            type(value['sha256']) is str and len(value['sha256']) == 64 and
            all(c in '0123456789abcdef' for c in value['sha256']), 'BROWSER_ENTRY_PIN_INVALID')
    return value


def decode(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'BROWSER_ENTRY_DUPLICATE_FIELD'); result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)


def deadline():
    require(sys.platform == 'linux', 'BROWSER_ENTRY_NATIVE_LINUX_REQUIRED')
    value = os.environ.get('INTRUOYI_NATIVE_DEADLINE_MONOTONIC')
    require(value is not None, 'BROWSER_ENTRY_EXPLICIT_DEADLINE_REQUIRED')
    selected = float(value)
    require(math.isfinite(selected) and 0 < selected - time.monotonic() <= 300,
            'BROWSER_ENTRY_CURRENT_DEADLINE_REQUIRED')
    return selected


def selected_context(launch_pin, provision_pin, authority_pin, *, read_deadline):
    """The actual W05 context invokes W03's current browser-native reader; there is no supplied admission callback."""
    for reference in (launch_pin, provision_pin, authority_pin): pin(reference)
    from recovery_native_browser import BrowserQualificationContext
    context = BrowserQualificationContext(launch_pin, provision_pin, authority_pin, deadline=read_deadline)
    selected = context.selection
    require(selected['producerEntryPin'] == selected['signerEntryPin'], 'BROWSER_ENTRY_SINGLE_SOURCE_REQUIRED')
    entry = selected['producerEntryPin']; pin(entry)
    require(Path(entry['path']).resolve(strict=True) == Path(__file__).resolve(strict=True), 'BROWSER_ENTRY_CURRENT_SOURCE_REQUIRED')
    raw = Path(entry['path']).read_bytes()
    require(len(raw) == entry['bytes'] and hashlib.sha256(raw).hexdigest() == entry['sha256'], 'BROWSER_ENTRY_SOURCE_CHANGED')
    # Exact selected private schema bytes are part of the complete sourceAccess, never classpath defaults.
    own = [a['pin'] for a in selected['sourceAccess'] if PurePosixPath(a['pin']['path']).name == 'recovery-control-browser-private-contract.json']
    require(len(own) == 1, 'BROWSER_ENTRY_PRIVATE_CONTRACT_REQUIRED')
    exported = decode(context.raw(own[0]))
    from recovery_native_browser import CONTRACT
    require(exported == CONTRACT, 'BROWSER_ENTRY_CONSUMER_CONTRACT_CHANGED')
    context.source_guard()
    return context


def authority_entry(context, broker_channel, on_ready):
    require(sys.platform == 'linux' and isinstance(broker_channel, socket.socket) and callable(on_ready),
            'BROWSER_ENTRY_INHERITED_BROKER_REQUIRED')
    from recovery_native_browser import BrowserAuthorityService
    return BrowserAuthorityService(context, broker_channel).serve(on_ready)


def producer_entry(context, authority_identity_pin, *, sandbox_channel):
    pin(authority_identity_pin)
    require(context.phase in ('NATIVE_BROWSER_CAPABILITY', 'NATIVE_BROWSER_QUALIFICATION'),
            'BROWSER_ENTRY_EXPLICIT_PHASE_REQUIRED')
    require(context.phase == 'NATIVE_BROWSER_CAPABILITY' and sandbox_channel is None or
            context.phase == 'NATIVE_BROWSER_QUALIFICATION' and isinstance(sandbox_channel, socket.socket),
            'BROWSER_ENTRY_SELECTED_SANDBOX_CHANNEL_REQUIRED')
    from recovery_native_browser import assert_current_b, qualification_entry, BrowserSandboxObserver
    assert_current_b(context)
    if context.phase == 'NATIVE_BROWSER_QUALIFICATION':
        observer = BrowserSandboxObserver(context, sandbox_channel)
        return qualification_entry(context, authority_identity_pin, sandbox_observer=observer)
    return qualification_entry(context, authority_identity_pin)


def parser():
    result = argparse.ArgumentParser(allow_abbrev=False)
    result.add_argument('role', choices=['browser-authority', 'browser-producer'])
    for name in ('launch', 'provision', 'authority'):
        result.add_argument('--' + name + '-pin', required=True)
    result.add_argument('--authority-identity-pin')
    result.add_argument('--broker-fd', type=int)
    result.add_argument('--sandbox-observer-fd', type=int)
    return result


def main():
    args = parser().parse_args()
    require((args.role == 'browser-authority' and args.broker_fd is not None and args.broker_fd >= 3 and args.authority_identity_pin is None and args.sandbox_observer_fd is None)
            or (args.role == 'browser-producer' and args.broker_fd is None and args.authority_identity_pin is not None
                and (args.sandbox_observer_fd is None or args.sandbox_observer_fd >= 3)),
            'BROWSER_ENTRY_EXACT_ROLE_ARGUMENTS_REQUIRED')
    selected_deadline = deadline()
    context = selected_context(*[decode(getattr(args, name + '_pin')) for name in ('launch', 'provision', 'authority')], read_deadline=selected_deadline)
    if args.role == 'browser-authority':
        with socket.socket(fileno=args.broker_fd) as broker:
            authority_entry(context, broker, lambda value: print(json.dumps(value, sort_keys=True, separators=(',', ':')), flush=True))
    else:
        if args.sandbox_observer_fd is None:
            value = producer_entry(context, decode(args.authority_identity_pin), sandbox_channel=None)
        else:
            with socket.socket(fileno=args.sandbox_observer_fd) as observer_channel:
                value = producer_entry(context, decode(args.authority_identity_pin), sandbox_channel=observer_channel)
        print(json.dumps(value, sort_keys=True, separators=(',', ':')), flush=True)


if __name__ == '__main__':
    main()
