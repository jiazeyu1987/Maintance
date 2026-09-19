import pathlib
import re
import sys


SECRET_PATTERNS = [
    (re.compile(r"(?i)(MYSQL_PWD=)([^\s]+)"), r"\1<redacted>"),
    (re.compile(r"(?i)(mysql\s+-p)([^\s]+)"), r"\1<redacted>"),
    (re.compile(r"(?i)(password\s*[=:]\s*)([^\s'\";]+)"), r"\1<redacted>"),
    (re.compile(r"(?i)(secret[_-]?key\s*[=:]\s*)([^\s'\";]+)"), r"\1<redacted>"),
    (re.compile(r"(?i)(access[_-]?key\s*[=:]\s*)([^\s'\";]+)"), r"\1<redacted>"),
    (re.compile(r"(?i)(secret\s*[=:]\s*)([^\s'\";]+)"), r"\1<redacted>"),
    (re.compile(r"(?i)(token\s*[=:]\s*)([^\s'\";]+)"), r"\1<redacted>"),
    (re.compile(r"(?i)(hmac[_-]?secret\s*[=:]\s*)([^\s'\";]+)"), r"\1<redacted>"),
    (re.compile(r"(?i)(jwt[_-]?secret\s*[=:]\s*)([^\s'\";]+)"), r"\1<redacted>"),
    (re.compile(r"(?i)(base64[_-]?key\s*[=:]\s*)([^\s'\";]+)"), r"\1<redacted>"),
    (re.compile(r"(?i)(-p)([^\s'\"]+)"), r"\1<redacted>"),
]


def sanitize(text: str) -> str:
    for pattern, replacement in SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def main() -> int:
    if len(sys.argv) not in (3, 4):
        print("usage: sanitize_log_tail.py <input-log> <output-file> [tail-bytes]", file=sys.stderr)
        return 2
    source = pathlib.Path(sys.argv[1])
    target = pathlib.Path(sys.argv[2])
    tail_bytes = int(sys.argv[3]) if len(sys.argv) == 4 else 65536
    data = source.read_bytes()
    tail = data[-tail_bytes:].decode("utf-8", errors="replace")
    target.write_text(sanitize(tail), encoding="utf-8")
    print(str(target))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
