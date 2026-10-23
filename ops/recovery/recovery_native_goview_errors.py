"""Private GoView diagnostics: exception text, SQL and options never leave memory."""
from __future__ import annotations

import re

from recovery_environment_contract import EnvironmentFailure


def safe_failure(error, *, depth=0, seen=None):
    seen = set() if seen is None else seen
    name = type(error).__module__ + '.' + type(error).__qualname__
    value = dict(failureType=name if re.fullmatch(r'[A-Za-z0-9_.]{1,160}', name) else 'REDACTED_TYPE')
    # Numeric driver/OS codes only. args[1], str(error), repr and traceback can
    # contain passwords, connection strings, SQL or raw server messages.
    if type(getattr(error, 'errno', None)) is int:
        value['errno'] = error.errno
    if error.args and type(error.args[0]) is int:
        value['driverCode'] = error.args[0]
    if isinstance(error, EnvironmentFailure):
        code = error.code
        value['safeCode'] = code if type(code) is str and re.fullmatch(
            r'(?:GOVIEW|NATIVE|LOCAL|UTC|JSON|NONFINITE|DUPLICATE)_[A-Z0-9_]{1,120}', code) else 'GOVIEW_DEPENDENCY_FAILURE'
        value['unknown'] = error.unknown
    if id(error) in seen or depth >= 12:
        value['chainTruncated'] = True
        return value
    seen.add(id(error))
    if isinstance(error, BaseExceptionGroup):
        value['members'] = [safe_failure(e, depth=depth+1, seen=seen) for e in error.exceptions[:32]]
        value['omittedMembers'] = max(0, len(error.exceptions)-32)
    # Preserve primary errors even when an unchanged dependency's finally
    # raised while another exception was active. Never serialize its message.
    linked = error.__cause__ if error.__cause__ is not None else error.__context__
    if linked is not None:
        value['preceding'] = safe_failure(linked, depth=depth+1, seen=seen)
    if isinstance(error, GoViewFailure):
        value['diagnostic'] = error.diagnostic
    return value


class GoViewFailure(EnvironmentFailure):
    def __init__(self, code, diagnostic, *, result=None):
        super().__init__(code, unknown=True, result=result)
        self.diagnostic = diagnostic


def remember(scope, error, phase):
    if not hasattr(scope, 'failures'):
        scope.failures = []
    scope.failures.append(dict(phase=phase, error=safe_failure(error)))


def uncertain(scope, primary, cleanup):
    """No storage/cleanup exception can erase UNKNOWN or the original type."""
    s = scope.selection
    return GoViewFailure('GOVIEW_EXECUTION_UNKNOWN_NO_RETRY', dict(
        state='UNKNOWN', retryAllowed=False, primary=safe_failure(primary) if primary else None,
        cleanup=[safe_failure(e) for e in cleanup], retainedFailures=list(scope.failures),
        operationId=s['operationId'], batchId=s['batchId'], connectionId=s['connectionId'],
        intent=getattr(scope, 'intent', None), createDispatched=getattr(scope, 'create_dispatched', False)))
