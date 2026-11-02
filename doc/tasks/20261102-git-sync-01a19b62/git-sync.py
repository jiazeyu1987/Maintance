"""Audit this authorized Git sync without printing credential values."""
import collections
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit
import winreg

ROOT = Path(__file__).resolve().parents[3]
TASK = Path(__file__).resolve().parent
ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="Never",
           PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
ENV["PATH"] = str(Path(sys.executable).parent) + os.pathsep + ENV["PATH"]


def git(*args, data=None, timeout=60):
    result = subprocess.run(["git", "-C", str(ROOT), "-c", "core.safecrlf=false", *args],
                            input=data, capture_output=True, env=ENV, timeout=timeout)
    if result.returncode:
        message = result.stderr.decode("utf-8", errors="replace")
        message = re.sub(r"(https?://)[^/@\s]+:[^/@\s]+@", r"\1<REDACTED>@", message)
        raise RuntimeError(f"git {args[0]} failed ({result.returncode}): {message[:1800]}")
    return result.stdout


def text(*args):
    return git(*args).decode("utf-8").strip()


def network_options():
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                        r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as key:
        enabled = winreg.QueryValueEx(key, "ProxyEnable")[0]
        address = winreg.QueryValueEx(key, "ProxyServer")[0] if enabled else ""
    if enabled:
        assert address in ("127.0.0.1:7890", "http://127.0.0.1:7890"), "Unexpected enabled proxy"
        return ["-c", "http.proxy=http://127.0.0.1:7890"]
    return []


def save(name, report):
    (TASK / name).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


assert text("rev-parse", "--show-toplevel").replace("\\", "/").lower() == ROOT.as_posix().lower()
assert text("branch", "--show-current") == "int_main"
assert text("remote", "get-url", "origin") == "https://github.com/jiazeyu1987/Maintance.git"
assert not text("diff", "--name-only", "--diff-filter=U"), "Unresolved conflicts"
mode = sys.argv[1]
if mode == "inspect":
    status = git("status", "--porcelain=v1", "-z", "--untracked-files=all").decode("utf-8").split("\0")
    actual = git("diff", "--name-only", "-z").decode("utf-8").strip("\0").split("\0")
    tracked = [line[3:] for line in status if line and not line.startswith("?? ")]
    untracked = [line[3:] for line in status if line.startswith("?? ")]
    report = dict(head=text("rev-parse", "HEAD"), upstream=text("rev-parse", "@{upstream}"),
                  staged=text("diff", "--cached", "--name-only").splitlines(),
                  actualChanged=[p for p in actual if p], trackedStatusCount=len(tracked),
                  trackedHashes={p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
                                 for p in tracked if (ROOT / p).is_file()},
                  untrackedCount=len(untracked), untrackedGroups=dict(collections.Counter(
                      "/".join(p.split("/")[:3]) for p in untracked)))
    save("initial-state.json", report)
elif mode == "fetch":
    options = network_options()
    result = git(*options, "fetch", "origin", timeout=55)
    save("fetch-result.json", dict(status="PASS", network="existing-system-proxy" if options else "default",
         remoteCommit=text("rev-parse", "origin/int_main"), head=text("rev-parse", "HEAD"),
         aheadBehind=text("rev-list", "--left-right", "--count", "HEAD...origin/int_main"),
         incomingFiles=text("diff", "--name-only", "HEAD...origin/int_main").splitlines()))
elif mode in ("audit", "audit-final"):
    audited_head = text("rev-parse", "HEAD")
    secrets = set()

    def collect(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if (re.search("password|token|secret", key, re.I)
                        and not re.search("(file|path|name)$", key, re.I)
                        and isinstance(item, str) and len(item) >= 6):
                    secrets.add(item.encode("utf-8"))
                collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    private_root = Path("C:/SpugHandoff/release")
    private = json.loads((private_root / "executor.private.json").read_text("utf-8-sig"))
    for private_data in (private,
                         json.loads(Path(private["loginVerification"]["credentialsFile"]).read_text("utf-8-sig")),
                         json.loads((private_root / "private/spug-login.private.json").read_text("utf-8-sig"))):
        collect(private_data)
    objects = {}
    listing = git("rev-list", "--objects", "--missing=print", "HEAD", "^origin/int_main").decode("utf-8").splitlines()
    assert not any(line.startswith("?") for line in listing), "Missing outgoing objects"
    for line in listing:
        oid, _, path = line.partition(" ")
        objects[oid] = path
    sizes = git("cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize)",
                data=("\n".join(objects) + "\n").encode()).decode().splitlines() if objects else []
    blobs = []
    violations = []
    candidates = []
    reviewed_fixtures = []
    patterns = {
        "private-key": rb"-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----[\r\n]+[A-Za-z0-9+/=]{24,}",
        "github-token": rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})",
        "credential-url": rb"https?://[^/\s:@]{2,}:[^/\s@]{6,}@",
    }

    def scan(path, content):
        if any(secret in content for secret in secrets):
            violations.append(dict(path=path, reason="exact private credential found"))
        for rule, pattern in patterns.items():
            for match in re.finditer(pattern, content):
                allowed_contexts = {
                    "ops/spug/release-center/test_intruoyi_rehearsal.py":
                        "test_origin_requires_explicit_safe_host_port_without_extra_url_parts",
                    "ops/spug/release-center/test_release_precheck.py":
                        "test_credentials_do_not_enter_error_text",
                }
                functions = re.findall(rb"^\s*def ([A-Za-z0-9_]+)\(", content[:match.start()], re.M)
                function = functions[-1].decode() if functions else ""
                if rule == "credential-url" and allowed_contexts.get(path) == function:
                    reviewed_fixtures.append(dict(path=path, function=function,
                        valueSha256=hashlib.sha256(match.group()).hexdigest(),
                        reason="synthetic negative URL-validation/redaction fixture"))
                else:
                    violations.append(dict(path=path, reason=rule))
        if re.search(rb"(?i)(?:password|passwd|secret|access_token|api_key)\s*[=:]\s*[\"']?[^\s\"'${}<>,;]{8,}", content):
            candidates.append(path)

    for line in sizes:
        oid, kind, size = line.split()
        if kind != "blob":
            continue
        size = int(size)
        path = objects[oid]
        blobs.append(dict(path=path, bytes=size))
        if size > 100_000_000:
            violations.append(dict(path=path, reason="blob exceeds 100 MB"))
        else:
            scan(path, git("cat-file", "blob", oid))
    changed = text("diff", "--name-only").splitlines()
    for path in changed:
        if (ROOT / path).is_file():
            content = (ROOT / path).read_bytes()
            if len(content) > 100_000_000:
                violations.append(dict(path=path, reason="working file exceeds 100 MB"))
            scan(path, content)
    assert text("rev-parse", "HEAD") == audited_head, "HEAD changed during audit"
    output_name = "tmp/final-audit.json" if mode == "audit-final" else "content-audit.json"
    (TASK / "tmp").mkdir(exist_ok=True)
    save(output_name, dict(status="PASS" if not violations else "BLOCKER", auditedHead=audited_head,
         outgoingCommits=int(text("rev-list", "--count", "HEAD", "^origin/int_main")),
         blobCount=len(blobs), totalBytes=sum(b["bytes"] for b in blobs),
         largestBlobs=sorted(blobs, key=lambda b: b["bytes"], reverse=True)[:5],
         violations=violations, credentialCandidatePaths=sorted(set(candidates)),
         exactPrivateCredentialScanPassed=not any(v["reason"] == "exact private credential found" for v in violations),
         reviewedSyntheticFixtures=reviewed_fixtures, changedTrackedFiles=changed))
    assert not violations, "Push content audit blocked"
elif mode == "review-credentials":
    report = json.loads((TASK / "content-audit.json").read_text("utf-8"))
    for path in sorted(set(report["credentialCandidatePaths"] + [v["path"] for v in report["violations"]])):
        content = (ROOT / path).read_text("utf-8")
        function = ""
        for number, line in enumerate(content.splitlines(), 1):
            if re.match(r"\s*(?:async )?def ", line):
                function = line.strip().split("(")[0]
            urls = list(re.finditer(r"https?://[^/\s:@]{2,}:[^/\s@]{6,}@[^\s\"')]*", line))
            assignment = re.search(r"(?i)(?:password|passwd|secret|access_token|api_key)\s*[=:]\s*[\"']?[^\s\"'${}<>,;]{8,}", line)
            if not urls and not assignment:
                continue
            safe = line
            for match in reversed(urls):
                parsed = urlsplit(match.group())
                safe = safe[:match.start()] + "<credential-url-host=" + str(parsed.hostname) + ">" + safe[match.end():]
            safe = re.sub(r"(?i)((?:password|passwd|secret|access_token|api_key)\s*[=:]\s*)[^,;)]+", r"\1<REDACTED>", safe)
            print(json.dumps(dict(path=path, line=number, function=function, context=safe[:220]), ensure_ascii=False))
elif mode == "verify":
    java = Path("C:/Users/D01021/AppData/Local/Programs/JavaMaven/jdk-17.0.20.1+1/bin/java.exe")
    yaml_jar = Path.home() / ".m2/repository/org/yaml/snakeyaml/2.4/snakeyaml-2.4.jar"
    assert java.is_file() and yaml_jar.is_file(), "Required Java YAML parser unavailable"
    temporary = TASK / "tmp"
    temporary.mkdir(exist_ok=True)
    source_file = temporary / "CheckYaml.java"
    source_file.write_text('''import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import org.yaml.snakeyaml.Yaml;
class CheckYaml {
  public static void main(String[] args) throws Exception {
    try (var reader = Files.newBufferedReader(Path.of(args[0]), StandardCharsets.UTF_8)) {
      Map<?,?> root = new Yaml().load(reader);
      Map<?,?> maintenance = (Map<?,?>)root.get("maintenance");
      Map<?,?> runtime = (Map<?,?>)maintenance.get("runtime-control");
      for (String key : new String[]{"repo-root", "frontend-root", "website-root", "ops-root"}) {
        System.out.println(key + "\\t" + runtime.get(key));
      }
    }
  }
}
''', encoding="utf-8")
    checked = {}
    for name in ("backend/src/main/resources/application.yaml", "config/runtime-control.example.yaml"):
        source = (ROOT / name).read_bytes()
        assert not source.startswith(b"\xef\xbb\xbf"), "Unexpected UTF-8 BOM"
        source.decode("utf-8")
        parsed = subprocess.run([str(java), "-Dfile.encoding=UTF-8", "--class-path", str(yaml_jar),
                                 str(source_file), str(ROOT / name)], capture_output=True, timeout=30)
        assert parsed.returncode == 0, "SnakeYAML parsing failed: " + parsed.stderr.decode("utf-8", errors="replace")
        config = dict(line.split("\t", 1) for line in parsed.stdout.decode("utf-8").splitlines())
        resolved = {}
        for key in ("repo-root", "frontend-root", "website-root", "ops-root"):
            value = config[key].replace(chr(36) + "{user.dir}", str(ROOT))
            path = (ROOT / value).resolve()
            assert path.is_dir(), "Missing configured directory: " + key
            resolved[key] = str(path)
        checked[name] = resolved
    launcher = (ROOT / "scripts/dev-backend.ps1").read_text("utf-8")
    assert '"-Dspring-boot.run.workingDirectory=$Root"' in launcher
    assert "$Root = Split-Path -Parent $PSScriptRoot" in launcher
    for name in json.loads((TASK / "initial-state.json").read_text("utf-8"))["actualChanged"]:
        (ROOT / name).read_text("utf-8")
    git("diff", "--check")
    save("verification.json", dict(status="PASS", yamlSyntax="PASS", utf8="PASS",
         gitDiffCheck="PASS", launcherWorkingDirectory="PASS", configuredDirectories=checked,
         functionalRegression="Not rerun: Git synchronization and existing configuration/documentation changes only"))
elif mode == "push":
    head = text("rev-parse", "HEAD")
    final = "--final" in sys.argv[2:]
    audit_name = "tmp/final-audit.json" if final else "content-audit.json"
    audit = json.loads((TASK / audit_name).read_text("utf-8"))
    assert audit["status"] == "PASS" and audit["auditedHead"] == head
    git(*network_options(), "push", "origin", head + ":refs/heads/int_main", timeout=55)
    remote = git(*network_options(), "ls-remote", "--heads", "origin", "refs/heads/int_main").decode().split()[0]
    assert remote == head, "Remote head mismatch"
    save("tmp/final-push.json" if final else "push-result.json", dict(status="PASS", branch="int_main", head=head,
         remoteCommit=remote, forceUsed=False,
         aheadBehind=text("rev-list", "--left-right", "--count", "HEAD...origin/int_main")))
else:
    raise ValueError(mode)
