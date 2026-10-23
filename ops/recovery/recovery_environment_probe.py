"""Finite, read-only probes inside one actual container network namespace.

Secrets arrive over stdin and never enter argv or output. HTTP requests have
literal local destinations, no proxy or redirects. This is a native execution
worker, not a mock health endpoint and not an independent business acceptance.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import errno
import hashlib
import hmac
import http.client
import ipaddress
import json
import os
import socket
import struct
import sys
import time
from xml.etree import ElementTree


def sign_s3(access, secret, region, host, now):
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    date = now.strftime("%Y%m%d")
    body_sha = hashlib.sha256(b"").hexdigest()
    headers = f"host:{host}\nx-amz-content-sha256:{body_sha}\nx-amz-date:{stamp}\n"
    signed = "host;x-amz-content-sha256;x-amz-date"
    canonical = "GET\n/\n\n" + headers + "\n" + signed + "\n" + body_sha
    scope = f"{date}/{region}/s3/aws4_request"
    string = "AWS4-HMAC-SHA256\n" + stamp + "\n" + scope + "\n" + hashlib.sha256(canonical.encode()).hexdigest()
    def mac(key, value):
        return hmac.new(key, value.encode(), hashlib.sha256).digest()
    key = mac(mac(mac(mac(("AWS4" + secret).encode(), date), region), "s3"), "aws4_request")
    signature = hmac.new(key, string.encode(), hashlib.sha256).hexdigest()
    return {"x-amz-content-sha256": body_sha, "x-amz-date": stamp,
            "Authorization": f"AWS4-HMAC-SHA256 Credential={access}/{scope}, SignedHeaders={signed}, Signature={signature}"}


def http_observe(port, path, remaining, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=remaining())
    try:
        connection.request("GET", path, headers={"Connection": "close", "Accept-Encoding": "identity", **(headers or {})})
        response = connection.getresponse()
        lengths = response.headers.get_all("Content-Length", [])
        if len(lengths) > 1 or lengths and (not lengths[0].isdigit() or int(lengths[0]) > 1024 * 1024):
            raise ValueError("HTTP_LENGTH_INVALID")
        body = response.read(1024 * 1024 + 1)
        if len(body) > 1024 * 1024 or lengths and len(body) != int(lengths[0]):
            raise ValueError("HTTP_BODY_INVALID")
        remaining()
        return response.status, body
    finally:
        connection.close()


def probe(spec):
    deadline = time.monotonic() + spec["seconds"]
    def remaining():
        value = deadline - time.monotonic()
        if value <= 0:
            raise TimeoutError()
        return value
    protocol = spec["protocol"]
    if protocol == "dnsBlocked":
        name = spec["name"]
        question = b"".join(bytes([len(label)]) + label.encode("ascii") for label in name.split(".")) + b"\x00\x00\x01\x00\x01"
        transaction = b"\x52\x43"
        request = transaction + b"\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00" + question
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connection:
            connection.settimeout(remaining())
            connection.connect(("127.0.0.11", 53))
            connection.send(request)
            try:
                raw = connection.recv(4096)
            except (TimeoutError, ConnectionRefusedError):
                return {"state": "OBSERVED", "result": {"externalDnsBlocked": True, "name": name, "reason": "NO_UPSTREAM_RESPONSE"}}
            if len(raw) < 12 or raw[:2] != transaction:
                raise ValueError("DNS_RESPONSE_INVALID")
            flags, _, answers, _, _ = struct.unpack("!5H", raw[2:12])
            if not flags & 0x8000 or answers != 0 or flags & 0x000F not in (2, 5):
                raise ValueError("EXTERNAL_DNS_BLOCK_NOT_PROVEN")
            return {"state": "OBSERVED", "result": {"externalDnsBlocked": True, "name": name, "rcode": flags & 0x000F,
                    "responseSha256": hashlib.sha256(raw).hexdigest()}}
    if protocol == "blocked":
        # Literal destinations avoid ambient DNS and source-host discovery.
        ipaddress.IPv4Address(spec["host"])
        try:
            connection = socket.create_connection((spec["host"], spec["port"]), timeout=remaining())
        except OSError as failure:
            if isinstance(failure, TimeoutError) or failure.errno in (errno.ENETUNREACH, errno.EHOSTUNREACH, errno.EACCES, errno.EPERM):
                return {"state": "OBSERVED", "result": {"blocked": True, "host": spec["host"], "port": spec["port"],
                         "reason": "TIMEOUT" if isinstance(failure, TimeoutError) else errno.errorcode[failure.errno]}}
            # A refused connection proves reachability; it does not prove isolation.
            raise ValueError("BLOCK_NOT_PROVEN") from None
        else:
            connection.close()
            raise ValueError("BLOCKED_ENDPOINT_REACHABLE")
    if protocol == "redis":
        with socket.create_connection(("127.0.0.1", spec["port"]), timeout=remaining()) as connection:
            connection.sendall(b"*1\r\n$4\r\nPING\r\n*1\r\n$6\r\nDBSIZE\r\n")
            raw = bytearray()
            while raw.count(b"\r\n") < 2:
                connection.settimeout(remaining())
                chunk = connection.recv(1024)
                if not chunk or len(raw) + len(chunk) > 1024:
                    raise ValueError("REDIS_RESPONSE_INVALID")
                raw.extend(chunk)
            rows = raw.split(b"\r\n")
            if rows[0] != b"+PONG" or not rows[1].startswith(b":") or not rows[1][1:].isdigit():
                raise ValueError("REDIS_RESPONSE_INVALID")
            return {"state": "OBSERVED", "result": {"ready": True, "keyCount": int(rows[1][1:]),
                    "responseSha256": hashlib.sha256(raw).hexdigest()}}
    if protocol == "tcp":
        with socket.create_connection(("127.0.0.1", spec["port"]), timeout=remaining()):
            return {"state": "OBSERVED", "result": {"ready": True, "port": spec["port"]}}
    if protocol == "s3":
        host = "127.0.0.1:" + str(spec["port"])
        headers = sign_s3(spec["access"], spec["secret"], spec["region"], host, datetime.now(timezone.utc))
        status, body = http_observe(spec["port"], "/", remaining, headers)
        if status != 200:
            raise ValueError("S3_LIST_BUCKETS_FAILED")
        if b"<!DOCTYPE" in body or b"<!ENTITY" in body:
            raise ValueError("S3_XML_UNSAFE")
        root = ElementTree.fromstring(body)
        if root.tag != "{http://s3.amazonaws.com/doc/2006-03-01/}ListAllMyBucketsResult":
            raise ValueError("S3_BUCKET_RESPONSE_ROOT_INVALID")
        buckets = [node.text for node in root.findall(".//{*}Buckets/{*}Bucket/{*}Name")]
        if len(buckets) != len(set(buckets)) or any(not name for name in buckets):
            raise ValueError("S3_BUCKET_RESPONSE_INVALID")
        return {"state": "OBSERVED", "result": {"ready": True, "bucketCount": len(buckets), "buckets": buckets,
                "responseSha256": hashlib.sha256(body).hexdigest()}}
    if protocol != "http":
        raise ValueError("PROTOCOL_UNSUPPORTED")
    status, body = http_observe(spec["port"], spec["path"], remaining)
    ready = status == 200
    expected = spec["expected"]
    if expected == "BACKEND_UP":
        def pairs(entries):
            result = {}
            for key, value in entries:
                if key in result:
                    raise ValueError("HEALTH_DUPLICATE_FIELD")
                result[key] = value
            return result
        value = json.loads(body, object_pairs_hook=pairs)
        ready &= type(value) is dict and value.get("status") == "UP"
    elif expected == "HTML":
        ready &= b"<html" in body.lower() and b"</html>" in body.lower()
    elif expected == "TRUE":
        ready &= body.strip() == b"true"
    elif expected != "HTTP_200":
        raise ValueError("HEALTH_EXPECTATION_UNSUPPORTED")
    return {"state": "OBSERVED", "result": {"ready": bool(ready), "httpStatus": status,
            "bodyBytes": len(body), "bodySha256": hashlib.sha256(body).hexdigest()}}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--namespace-fd", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        if os.name != "posix" or not hasattr(os, "setns"):
            raise ValueError("NATIVE_SETNS_REQUIRED")
        raw = sys.stdin.buffer.read(65537)
        if len(raw) > 65536:
            raise ValueError("PROBE_REQUEST_LIMIT")
        spec = json.loads(raw)
        if not 0 < spec["seconds"] <= 300:
            raise ValueError("PROBE_BUDGET_INVALID")
        os.setns(args.namespace_fd, os.CLONE_NEWNET)
        result = probe(spec)
        print(json.dumps(result, separators=(",", ":")))
        return 0
    except (ConnectionRefusedError, TimeoutError):
        print('{"state":"NOT_READY","result":null}')
        return 0
    except Exception as failure:
        # Never serialize exception text (HTTP auth headers may be involved).
        print(json.dumps({"state": "FAILED", "failureType": type(failure).__name__}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
