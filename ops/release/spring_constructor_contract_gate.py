from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


BEAN_ANNOTATION_PATTERN = re.compile(
    r"@(?:Service|Component|Controller|RestController|Configuration)\b"
    r"(?:\s*\([^)]*\))?"
    r"(?:\s*@\w+(?:\([^)]*\))?)*"
    r"\s*(?:public\s+|protected\s+|private\s+|abstract\s+|final\s+)*class\s+([A-Za-z_$][\w$]*)",
    re.DOTALL,
)
CONSTRUCTOR_PATTERN = re.compile(
    r"(?m)^[ \t]*(?:(?:public|protected|private|final|synchronized)\s+)*"
    r"(?:<[^>\n]+>\s+)?(?P<class_name>[A-Za-z_$][\w$]*)\s*\((?P<parameters>[^)]*)\)"
)
AUTOWIRED_PATTERN = re.compile(r"@Autowired\b")


def _mask_java_comments_and_strings(text: str) -> str:
    masked = list(text)
    index = 0
    state = "code"
    quote = ""
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if state == "code":
            if char == "/" and next_char == "/":
                masked[index] = " "
                masked[index + 1] = " "
                state = "line_comment"
                index += 2
                continue
            if char == "/" and next_char == "*":
                masked[index] = " "
                masked[index + 1] = " "
                state = "block_comment"
                index += 2
                continue
            if char in ('"', "'"):
                quote = char
                masked[index] = " "
                state = "string"
            index += 1
            continue
        if state == "line_comment":
            if char == "\n":
                state = "code"
            elif char != "\r":
                masked[index] = " "
            index += 1
            continue
        if state == "block_comment":
            if char == "*" and next_char == "/":
                masked[index] = " "
                masked[index + 1] = " "
                state = "code"
                index += 2
                continue
            if char != "\n" and char != "\r":
                masked[index] = " "
            index += 1
            continue
        if char == "\\" and index + 1 < len(text):
            if text[index + 1] not in "\r\n":
                masked[index] = " "
                masked[index + 1] = " "
            index += 2
            continue
        if char == quote:
            masked[index] = " "
            state = "code"
            index += 1
            continue
        if char != "\n" and char != "\r":
            masked[index] = " "
        index += 1
    return "".join(masked)


def _find_matching_brace(text: str, opening: int) -> int | None:
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def _constructor_contract_failures_for_file(path: Path) -> list[dict[str, object]]:
    source = path.read_text(encoding="utf-8")
    masked = _mask_java_comments_and_strings(source)
    failures: list[dict[str, object]] = []
    for class_match in BEAN_ANNOTATION_PATTERN.finditer(masked):
        class_name = class_match.group(1)
        opening = masked.find("{", class_match.end())
        if opening < 0:
            continue
        closing = _find_matching_brace(masked, opening)
        if closing is None:
            continue
        body_start = opening + 1
        body = masked[body_start:closing]
        constructors = [
            match
            for match in CONSTRUCTOR_PATTERN.finditer(body)
            if match.group("class_name") == class_name
        ]
        if len(constructors) <= 1:
            continue
        autowired_count = 0
        no_arg_count = 0
        for constructor in constructors:
            parameters = constructor.group("parameters").strip()
            if not parameters:
                no_arg_count += 1
            prefix_start = max(body.rfind("}", 0, constructor.start()), body.rfind(";", 0, constructor.start())) + 1
            prefix = body[prefix_start : constructor.start()]
            if AUTOWIRED_PATTERN.search(prefix):
                autowired_count += 1
        if autowired_count == 1 or no_arg_count == 1:
            continue
        line = source.count("\n", 0, body_start + constructors[0].start()) + 1
        failures.append(
            {
                "file": path.as_posix(),
                "line": line,
                "class": class_name,
                "constructorCount": len(constructors),
                "autowiredCount": autowired_count,
                "noArgCount": no_arg_count,
            }
        )
    return failures


def find_constructor_contract_failures(source_root: Path | str) -> list[dict[str, object]]:
    root = Path(source_root).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Spring constructor gate source root is missing: {root}")
    failures: list[dict[str, object]] = []
    for path in sorted(root.rglob("*.java")):
        if any(part in {".git", "target", "node_modules"} for part in path.parts):
            continue
        failures.extend(_constructor_contract_failures_for_file(path))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    args = parser.parse_args()
    failures = find_constructor_contract_failures(Path(args.source_root))
    if failures:
        sys.stderr.write(
            json.dumps(
                {"status": "failed", "failureCount": len(failures), "failures": failures},
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
        return 1
    sys.stdout.write(json.dumps({"status": "passed"}, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
