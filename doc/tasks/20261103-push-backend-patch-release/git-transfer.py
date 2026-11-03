"""Run scoped Git transfer checks without printing credential-bearing URLs."""
import json
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

REPOS = {
    "maintenance": Path(__file__).resolve().parents[3],
    "intruoyi": Path("C:/SpugHandoff/backend-log-src-20261102"),
}


def sanitize(value):
    value = re.sub(r"(https?://)[^\s/@]+(?::[^\s/@]*)?@", r"\1[REDACTED]@", value)
    value = re.sub(r"\b(?:gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+)\b", "[REDACTED]", value)
    return value


def git(repo, *args, check=True):
    env = os.environ.copy()
    env.update(PYTHONUTF8="1", GIT_TERMINAL_PROMPT="0")
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    options = []
    if args and args[0] in {"ls-remote", "fetch", "push"}:
        with socket.socket() as probe:
            probe.settimeout(1)
            if probe.connect_ex(("127.0.0.1", 7890)) == 0:
                options = ["-c", "http.proxy=http://127.0.0.1:7890"]
    result = subprocess.run(["git", *options, *args], cwd=repo, env=env, capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=180)
    if check and result.returncode:
        raise RuntimeError(sanitize((result.stdout + result.stderr).strip()))
    return result


def main():
    name, mode = sys.argv[1:3]
    repo = REPOS[name]
    branch = git(repo, "branch", "--show-current").stdout.strip()
    if mode == "inventory":
        result = {
            "repository": name, "path": str(repo), "branch": branch,
            "head": git(repo, "rev-parse", "HEAD").stdout.strip(),
            "origin": sanitize(git(repo, "remote", "get-url", "origin").stdout.strip()),
            "pushOrigin": sanitize(git(repo, "remote", "get-url", "--push", "origin").stdout.strip()),
            "proxy": sanitize(git(repo, "config", "--get", "http.proxy", check=False).stdout.strip()),
            "trackingRefs": git(repo, "for-each-ref", "--format=%(refname:short) %(objectname)", "refs/remotes/origin/" + branch, "refs/remotes/origin/int_main").stdout.strip(),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif mode == "remote":
        result = git(repo, "ls-remote", "--heads", "origin", "refs/heads/" + branch, "refs/heads/int_main")
        print(sanitize(result.stdout))
    elif mode == "fetch":
        result = git(repo, "fetch", "--no-tags", "origin")
        print(sanitize(result.stdout + result.stderr))
    elif mode == "push":
        result = git(repo, "push", "--set-upstream", "origin", "HEAD:refs/heads/" + branch)
        print(sanitize(result.stdout + result.stderr))
    elif mode == "verify":
        head = git(repo, "rev-parse", "HEAD").stdout.strip()
        refs = git(repo, "ls-remote", "--heads", "origin", "refs/heads/" + branch, "refs/heads/int_main").stdout
        identities = dict((line.split()[1], line.split()[0]) for line in refs.splitlines())
        assert identities.get("refs/heads/" + branch) == head, "Remote task branch differs from local HEAD"
        main = git(repo, "rev-parse", "refs/remotes/origin/int_main").stdout.strip()
        assert identities.get("refs/heads/int_main") == main, "Remote int_main changed; inspect ownership"
        result = dict(repository=name, branch=branch, head=head, remoteHeadMatches=True,
                      intMainHead=main, intMainUnchanged=True, status="PASS")
        if "--check" not in sys.argv:
            (Path(__file__).resolve().parent / ("push-" + name + ".json")).write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        raise ValueError("Unknown mode")


if __name__ == "__main__":
    main()
