"""Materialize a caller-selected binding for an already fixed VERIFY request.

Only an independent invoking service may select RECOVERY_VERIFICATION_SELECTION_PIN.
This tool never creates grants, evidence, trace, source baselines or approvals.
"""
import argparse
import datetime as dt
import os
import sys

from core import (Deadline, VerificationError, file_pin, fields, json_pin, need, parse,
                  pin_key, pins, read_pin, same, timestamp, write_atomic)
from evidence import EvidenceContext
from verify_recovery import authorize, policy_record


def bind(request_path, output_path, selection_pin):
    need(selection_pin is not None, "INDEPENDENT_CALLER_SELECTION_REQUIRED")
    selection = json_pin(selection_pin)
    lab_selected = selection.get("schemaVersion") == "RecoveryLabCallerSelection/v1"
    fields(selection, "schemaVersion callerThreadId producerThreadIds requestPin schemaPin sourceScopePin "
           "executableScopePin runTracePin independentOriginalPins validUntil" +
           (" labAdmissionPin" if lab_selected else ""),
           "RecoveryLabCallerSelection/v1" if lab_selected else "RecoveryCallerSelection/v1")
    deadline = Deadline(30000)
    request_pin = file_pin(request_path, deadline)
    same(request_pin, selection["requestPin"], "CALLER_REQUEST_MISMATCH")
    request = json_pin(request_pin, deadline)
    need(request["action"] == "VERIFY_RECOVERY", "UNSUPPORTED_ACTION")
    binding = dict(selection, schemaVersion="RecoveryLabCallerBinding/v1" if lab_selected else "RecoveryCallerBinding/v1")
    # Validation reads only selected originals and code scope; it does not mint authorization.
    temporary_context = EvidenceContext(request, request_pin, selection_pin, deadline, selected_binding=binding)
    policy = policy_record(temporary_context)
    target = temporary_context.record(policy["recoveryTargetPin"], "RecoveryTarget")
    temporary_context.target_pin = target["targetIdentityPin"]
    authorize(temporary_context, request["authorizationRefs"])
    need(timestamp(selection["validUntil"]) > dt.datetime.now(dt.timezone.utc), "CALLER_BINDING_EXPIRED", "STALE")
    temporary_context.recheck()
    return write_atomic(output_path, binding)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        raw = os.environ.get("RECOVERY_VERIFICATION_SELECTION_PIN")
        selected = parse(raw.encode("utf-8")) if raw is not None else None
        bind(args.request, args.output, selected)
        return 0
    except VerificationError as error:
        print(error.code, file=sys.stderr)
        return 2 if error.verdict == "UNKNOWN" else 1
    except (OSError, ValueError, TypeError, KeyError, ImportError, MemoryError) as error:
        print("CALLER_BINDING_" + type(error).__name__.upper(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
