"""Inspect outgoing Git objects; report identities and findings, never values."""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from importlib.util import module_from_spec, spec_from_file_location

task = Path(__file__).resolve().parent
spec = spec_from_file_location("git_transfer", task / "git-transfer.py")
transfer = module_from_spec(spec)
spec.loader.exec_module(transfer)
name = sys.argv[1]
repo = transfer.REPOS[name]
root = Path("C:/SpugHandoff/release")
config = json.loads((root / "executor.private.json").read_text(encoding="utf-8"))
values = set()


def collect(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if re.search(r"password|passwd|secret|token", key, re.I) and isinstance(item, str) and len(item) >= 8:
                values.add(item.encode("utf-8"))
            collect(item)
    elif isinstance(value, list):
        for item in value:
            collect(item)


collect(config)
credentials = [root / "private/spug-login.private.json"]
business = config.get("loginVerification", {}).get("credentialsFile")
if business:
    credentials.append(Path(business))
for path in credentials:
    collect(json.loads(path.read_text(encoding="utf-8")))

git = lambda *args: transfer.git(repo, *args).stdout
objects = git("rev-list", "--objects", "HEAD", "--not", "--remotes=origin").splitlines()
paths = {line.partition(" ")[0]: line.partition(" ")[2] for line in objects}
oids = list(paths)
sizes = subprocess.run(["git", "cat-file", "--batch-check"], input=("\n".join(oids) + "\n").encode(),
                       cwd=repo, capture_output=True, check=True, timeout=90).stdout.decode("ascii").splitlines()
blobs = [(row.split()[0], int(row.split()[2])) for row in sizes if row.split()[1] == "blob"]
large = [{"path": paths[oid], "size": size} for oid, size in blobs if size > 100_000_000]
assert not large, "Outgoing Git blob exceeds 100 MB; stop before push"
payload = subprocess.run(["git", "cat-file", "--batch"], input=("\n".join(oid for oid, _ in blobs) + "\n").encode(),
                         cwd=repo, capture_output=True, check=True, timeout=90).stdout
offset = 0
findings = []
patterns = {
    "private-key": rb"-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----",
    "github-token": rb"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{40,})\b",
    "credential-url": rb"https?://[^\s/@:]+:[^\s/@]+@",
}
for expected, size in blobs:
    end = payload.index(b"\n", offset)
    header = payload[offset:end].decode("ascii").split()
    assert header == [expected, "blob", str(size)]
    data = payload[end + 1:end + 1 + size]
    offset = end + 2 + size
    reasons = [key for key, pattern in patterns.items() if re.search(pattern, data)]
    if any(value in data for value in values):
        reasons.append("configured-private-value")
    if reasons:
        findings.append({"path": paths[expected], "object": expected, "reasons": reasons})

commits = git("log", "--format=%H %s", "HEAD", "--not", "--remotes=origin").splitlines()
report = {
    "repository": name, "branch": git("branch", "--show-current").strip(),
    "head": git("rev-parse", "HEAD").strip(), "unpublishedCommitCount": len(commits),
    "unpublishedCommits": commits, "outgoingObjectCount": len(oids), "outgoingBlobCount": len(blobs),
    "maximumBlobBytes": max((size for _, size in blobs), default=0),
    "totalBlobBytes": sum(size for _, size in blobs), "largeObjectFindings": large,
    "credentialFindings": findings, "status": "FAIL" if findings else "PASS",
}
if "--check" not in sys.argv:
    (task / ("audit-" + name + ".json")).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: value for key, value in report.items() if key != "unpublishedCommits"}, ensure_ascii=False, indent=2))
assert not findings, "Outgoing credential scan failed; contents intentionally not printed"
