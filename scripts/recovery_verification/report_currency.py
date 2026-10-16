"""Caller-pinned current bindings invalidate an old report without re-running recovery."""
import argparse
import datetime as dt
import os
import sys

from core import (Deadline, VerificationError, absolute, fields, need, parse, json_pin, same,
                  timestamp, validate, read_pin, write_atomic, now, integer, frozen_schema)
from evidence import assess_report


def assess(report_path, current_path, output_path, trust_pin):
    need(trust_pin is not None, "CURRENCY_CALLER_TRUST_REQUIRED")
    trust = json_pin(trust_pin)
    fields(trust, "schemaVersion callerThreadId producerThreadIds reportPin currentBindingPin schemaPin "
           "maxAgeMilliseconds validUntil", "RecoveryCurrencyCallerBinding/v1")
    need(type(trust["callerThreadId"]) is str and trust["callerThreadId"] and
         type(trust["producerThreadIds"]) is list and trust["producerThreadIds"] and
         trust["callerThreadId"] not in trust["producerThreadIds"], "CURRENCY_CALLER_NOT_INDEPENDENT")
    observed = now()
    need(timestamp(trust["validUntil"]) > timestamp(observed), "CURRENCY_BINDING_EXPIRED", "STALE")
    need(str(absolute(report_path)) == str(absolute(trust["reportPin"]["path"])) and
         str(absolute(current_path)) == str(absolute(trust["currentBindingPin"]["path"])), "CURRENCY_PATH_UNBOUND")
    schema = frozen_schema(trust["schemaPin"])
    report = json_pin(trust["reportPin"])
    validate(schema, "RecoveryVerificationReport", report)
    current = json_pin(trust["currentBindingPin"])
    window_ms = int((timestamp(trust["validUntil"]) - timestamp(observed)).total_seconds()*1000)
    deadline = Deadline(window_ms)
    result = assess_report(report, current, integer(trust["maxAgeMilliseconds"], 1), observed, deadline)
    validate(schema, "RecoveryVerificationReport", result)
    for pin in (trust_pin, trust["reportPin"], trust["currentBindingPin"], trust["schemaPin"]):
        read_pin(pin, deadline, content=False)
    need(timestamp(trust["validUntil"]) > timestamp(now()), "CURRENCY_BINDING_EXPIRED", "STALE")
    output = absolute(output_path)
    need(not output.exists(), "CURRENCY_OUTPUT_ALREADY_EXISTS")
    write_atomic(output, result)
    return 0 if result["verdict"] == "PASSED" else 2 if result["verdict"] == "UNKNOWN" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True)
    parser.add_argument("--current", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        configured = os.environ.get("RECOVERY_VERIFICATION_CURRENCY_TRUST_PIN")
        trust = parse(configured.encode("utf-8")) if configured is not None else None
        return assess(args.report, args.current, args.output, trust)
    except VerificationError as error:
        print(error.code, file=sys.stderr)
        return 2 if error.verdict == "UNKNOWN" else 1
    except Exception as error:
        print("CURRENCY_" + type(error).__name__.upper(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
