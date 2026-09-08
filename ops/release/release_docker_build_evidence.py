from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import sys
from pathlib import Path, PurePosixPath
from typing import Any


SPEC_SCHEMA = "release-docker-build-spec/v1"
INPUT_SCHEMA = "release-docker-build-input/v1"
FINAL_SCHEMA = "release-docker-build-evidence/v1"
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
ARG_PATTERN = re.compile(r"^ARG\s+([A-Za-z_][A-Za-z0-9_]*)(?:=.*)?$", re.IGNORECASE)
FROM_PATTERN = re.compile(r"^FROM\s+(?:--platform=\S+\s+)?(\S+)(?:\s+AS\s+\S+)?$", re.IGNORECASE)
VARIABLE_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}|\$([A-Za-z_][A-Za-z0-9_]*)")


class DockerBuildEvidenceError(ValueError):
    pass


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _file_digest(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _read_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise DockerBuildEvidenceError(f"{label} is missing: {path}")
    raw = path.read_bytes()
    if not raw.strip():
        raise DockerBuildEvidenceError(f"{label} is blank: {path}")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DockerBuildEvidenceError(f"{label} is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise DockerBuildEvidenceError(f"{label} must be a JSON object")
    return value


def _write_object(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def _logical_dockerfile_lines(text: str) -> list[str]:
    lines: list[str] = []
    pending = ""
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        pending += stripped
        if pending.endswith("\\"):
            pending = pending[:-1] + " "
            continue
        lines.append(pending)
        pending = ""
    if pending:
        raise DockerBuildEvidenceError("Dockerfile ends with an incomplete continuation")
    return lines


def _resolve_variables(value: str, build_args: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1) or match.group(2)
        if name not in build_args:
            raise DockerBuildEvidenceError(f"Dockerfile variable has no build arg value: {name}")
        return build_args[name]

    return VARIABLE_PATTERN.sub(replace, value)


def _parse_copy_sources(line: str) -> list[str]:
    remainder = line[4:].strip()
    if remainder.startswith("--"):
        raise DockerBuildEvidenceError("COPY flags and external stages are not supported by build evidence")
    if remainder.startswith("["):
        try:
            values = json.loads(remainder)
        except json.JSONDecodeError as exc:
            raise DockerBuildEvidenceError(f"invalid JSON COPY instruction: {exc}") from exc
        if not isinstance(values, list) or len(values) < 2 or not all(isinstance(value, str) for value in values):
            raise DockerBuildEvidenceError("JSON COPY requires string sources and destination")
        return values[:-1]
    try:
        values = shlex.split(remainder, posix=True)
    except ValueError as exc:
        raise DockerBuildEvidenceError(f"invalid COPY instruction: {exc}") from exc
    if len(values) < 2:
        raise DockerBuildEvidenceError("COPY requires at least one source and one destination")
    return values[:-1]


def _normalize_context_source(source: str) -> PurePosixPath:
    normalized = source.replace("\\", "/")
    pure = PurePosixPath(normalized)
    if (
        not normalized
        or pure.is_absolute()
        or ".." in pure.parts
        or any(character in normalized for character in "*?[")
    ):
        raise DockerBuildEvidenceError(f"unsafe or non-deterministic COPY source: {source or '<blank>'}")
    return pure


def _collect_context_records(context_root: Path, sources: list[str]) -> list[dict[str, object]]:
    root = context_root.resolve()
    if not root.is_dir():
        raise DockerBuildEvidenceError(f"Docker context root is missing: {context_root}")
    records: list[dict[str, object]] = []
    seen: set[str] = set()
    for source in sources:
        pure = _normalize_context_source(source)
        candidate = (root / Path(*pure.parts)).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise DockerBuildEvidenceError(f"COPY source escapes Docker context: {source}") from exc
        if not candidate.exists():
            raise DockerBuildEvidenceError(f"COPY source is missing from Docker context: {source}")
        if candidate.is_symlink():
            raise DockerBuildEvidenceError(f"COPY source symlink is not allowed: {source}")
        files = [candidate] if candidate.is_file() else sorted(
            (path for path in candidate.rglob("*") if path.is_file()),
            key=lambda path: path.relative_to(root).as_posix().casefold(),
        )
        if not files:
            raise DockerBuildEvidenceError(f"COPY source directory contains no files: {source}")
        for path in files:
            if path.is_symlink():
                raise DockerBuildEvidenceError(f"COPY input symlink is not allowed: {path}")
            resolved = path.resolve()
            try:
                relative = resolved.relative_to(root).as_posix()
            except ValueError as exc:
                raise DockerBuildEvidenceError(f"COPY input escapes Docker context: {path}") from exc
            folded = relative.casefold()
            if folded in seen:
                raise DockerBuildEvidenceError(f"duplicate or case-colliding COPY input: {relative}")
            seen.add(folded)
            content = resolved.read_bytes()
            records.append({"path": relative, "sha256": _file_digest(content), "size": len(content)})
    records.sort(key=lambda item: str(item["path"]).casefold())
    return records


def _normalize_build_args(raw: object, component_name: str) -> dict[str, str]:
    if not isinstance(raw, dict):
        raise DockerBuildEvidenceError(f"{component_name} buildArgs must be an object")
    values: dict[str, str] = {}
    for key, value in raw.items():
        name = str(key)
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) or not isinstance(value, str) or not value:
            raise DockerBuildEvidenceError(f"{component_name} build arg is invalid: {name}")
        values[name] = value
    return dict(sorted(values.items()))


def _build_component(raw: object) -> dict[str, object]:
    if not isinstance(raw, dict):
        raise DockerBuildEvidenceError("Docker build spec component must be an object")
    name = str(raw.get("name") or "").strip()
    image_reference = str(raw.get("imageReference") or "").strip()
    if not name or not image_reference:
        raise DockerBuildEvidenceError("Docker build component requires name and imageReference")
    dockerfile_path = Path(str(raw.get("dockerfile") or ""))
    context_root = Path(str(raw.get("contextRoot") or ""))
    if not dockerfile_path.is_file():
        raise DockerBuildEvidenceError(f"{name} Dockerfile is missing: {dockerfile_path}")
    dockerfile_bytes = dockerfile_path.read_bytes()
    try:
        dockerfile_text = dockerfile_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DockerBuildEvidenceError(f"{name} Dockerfile must be UTF-8") from exc
    build_args = _normalize_build_args(raw.get("buildArgs"), name)
    lines = _logical_dockerfile_lines(dockerfile_text)
    declared_args = {match.group(1) for line in lines if (match := ARG_PATTERN.fullmatch(line))}
    missing_args = sorted(declared_args - set(build_args))
    if missing_args:
        raise DockerBuildEvidenceError(f"{name} Dockerfile build args are missing values: {', '.join(missing_args)}")
    from_values = [match.group(1) for line in lines if (match := FROM_PATTERN.fullmatch(line))]
    if len(from_values) != 1:
        raise DockerBuildEvidenceError(f"{name} Dockerfile must contain exactly one FROM instruction")
    resolved_from = _resolve_variables(from_values[0], build_args)
    base = raw.get("baseImage")
    if not isinstance(base, dict):
        raise DockerBuildEvidenceError(f"{name} baseImage must be an object")
    base_reference = str(base.get("reference") or "").strip()
    base_digest = str(base.get("digest") or "").strip().lower()
    if base_reference != resolved_from:
        raise DockerBuildEvidenceError(f"{name} base image reference differs from resolved FROM")
    if not SHA256_PATTERN.fullmatch(base_digest):
        raise DockerBuildEvidenceError(f"{name} base image digest must be sha256:<64 hex>")
    copy_sources: list[str] = []
    for line in lines:
        if line.upper().startswith("COPY "):
            copy_sources.extend(_parse_copy_sources(line))
    if not copy_sources:
        raise DockerBuildEvidenceError(f"{name} Dockerfile declares no COPY inputs")
    context_records = _collect_context_records(context_root, copy_sources)
    dockerfile = {"digest": _file_digest(dockerfile_bytes), "size": len(dockerfile_bytes)}
    context = {"digest": _digest(context_records), "files": context_records}
    base_image = {"reference": base_reference, "digest": base_digest}
    build_args_section = {"digest": _digest(build_args), "values": build_args}
    input_fingerprint = _digest(
        {
            "dockerfileDigest": dockerfile["digest"],
            "contextDigest": context["digest"],
            "baseImage": base_image,
            "buildArgsDigest": build_args_section["digest"],
            "imageReference": image_reference,
        }
    )
    return {
        "name": name,
        "imageReference": image_reference,
        "inputFingerprint": input_fingerprint,
        "dockerfile": dockerfile,
        "context": context,
        "baseImage": base_image,
        "buildArgs": build_args_section,
    }


def build_input_evidence(spec_path: Path) -> dict[str, object]:
    spec = _read_object(spec_path, "Docker build spec")
    if spec.get("schemaVersion") != SPEC_SCHEMA:
        raise DockerBuildEvidenceError(f"Docker build spec schemaVersion must be {SPEC_SCHEMA}")
    raw_components = spec.get("components")
    if not isinstance(raw_components, list) or not raw_components:
        raise DockerBuildEvidenceError("Docker build spec components must be a non-empty array")
    components = [_build_component(raw) for raw in raw_components]
    names = [str(component["name"]) for component in components]
    if len({name.casefold() for name in names}) != len(names):
        raise DockerBuildEvidenceError("Docker build spec component names must be unique")
    return {"schemaVersion": INPUT_SCHEMA, "components": components}


def _assert_same_input(actual: dict[str, Any], expected: dict[str, object]) -> None:
    if _canonical_bytes(actual) != _canonical_bytes(expected):
        raise DockerBuildEvidenceError("Docker build inputs changed after pre-build capture")


def _normalize_actual_images(raw: dict[str, Any], expected: dict[str, object]) -> dict[str, dict[str, object]]:
    expected_components = {str(item["name"]): item for item in expected["components"]}  # type: ignore[index]
    if set(raw) != set(expected_components):
        raise DockerBuildEvidenceError("actual image identities do not match build components")
    result: dict[str, dict[str, object]] = {}
    for name, component in expected_components.items():
        identity = raw.get(name)
        if not isinstance(identity, dict):
            raise DockerBuildEvidenceError(f"actual image identity must be an object: {name}")
        reference = str(identity.get("reference") or "")
        image_id = str(identity.get("id") or "").lower()
        repo_digests = identity.get("repoDigests")
        if reference != component["imageReference"]:
            raise DockerBuildEvidenceError(f"actual image reference mismatch: {name}")
        if not SHA256_PATTERN.fullmatch(image_id):
            raise DockerBuildEvidenceError(f"actual image id is invalid: {name}")
        if not isinstance(repo_digests, list) or not all(isinstance(value, str) for value in repo_digests):
            raise DockerBuildEvidenceError(f"actual image repoDigests must be an array: {name}")
        result[name] = {
            "reference": reference,
            "id": image_id,
            "repoDigests": sorted(repo_digests),
        }
    return result


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    capture = subparsers.add_parser("capture")
    capture.add_argument("--spec", required=True)
    capture.add_argument("--output", required=True)
    verify = subparsers.add_parser("verify-input")
    verify.add_argument("--spec", required=True)
    verify.add_argument("--evidence", required=True)
    finalize = subparsers.add_parser("finalize")
    finalize.add_argument("--spec", required=True)
    finalize.add_argument("--evidence", required=True)
    finalize.add_argument("--actual-images", required=True)
    finalize.add_argument("--output", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        expected = build_input_evidence(Path(args.spec))
        if args.command == "capture":
            _write_object(Path(args.output), expected)
        else:
            actual_input = _read_object(Path(args.evidence), "Docker build input evidence")
            _assert_same_input(actual_input, expected)
            if args.command == "finalize":
                actual_images = _normalize_actual_images(
                    _read_object(Path(args.actual_images), "actual image identities"), expected
                )
                components = []
                for component in expected["components"]:  # type: ignore[index]
                    finalized = dict(component)
                    finalized["actualImage"] = actual_images[str(component["name"])]
                    components.append(finalized)
                final: dict[str, object] = {"schemaVersion": FINAL_SCHEMA, "components": components}
                final["evidenceDigest"] = _digest(final)
                _write_object(Path(args.output), final)
        return 0
    except (DockerBuildEvidenceError, OSError, ValueError) as exc:
        print(f"DOCKER_BUILD_EVIDENCE_BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
