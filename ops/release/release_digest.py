"""Language-independent package and manifest digest contract for app-release."""

from dataclasses import dataclass
import hashlib


class PackagePathError(ValueError):
    pass


@dataclass(frozen=True)
class ArtifactBytes:
    path: str
    content: bytes


@dataclass(frozen=True)
class ArtifactDigest:
    path: str
    bytes: int
    sha256: str


@dataclass(frozen=True)
class PackageDigestResult:
    artifacts: tuple[ArtifactDigest, ...]
    canonical_input: bytes
    package_digest: str


def _normalise_path(path: str) -> str:
    if (
        not isinstance(path, str)
        or not path
        or path != path.strip()
        or "\\" in path
        or path.startswith("/")
        or (len(path) >= 2 and path[1] == ":")
        or any(ord(char) < 32 or ord(char) == 127 for char in path)
    ):
        raise PackagePathError(f"PACKAGE_PATH_INVALID: {path!r}")
    if any(segment in ("", ".", "..") for segment in path.split("/")):
        raise PackagePathError(f"PACKAGE_PATH_INVALID: {path!r}")
    return path


def _ascii_case_fold(path: str) -> str:
    return "".join(chr(ord(char) + 32) if "A" <= char <= "Z" else char for char in path)


def calculate_package_digest(artifacts: list[ArtifactBytes]) -> PackageDigestResult:
    seen: set[str] = set()
    entries: list[ArtifactDigest] = []
    for artifact in artifacts:
        if not isinstance(artifact.content, bytes):
            raise PackagePathError("PACKAGE_PATH_INVALID: artifact content must be bytes")
        path = _normalise_path(artifact.path)
        folded = _ascii_case_fold(path)
        if folded in seen:
            raise PackagePathError(f"PACKAGE_PATH_INVALID: case-folded path collision: {path}")
        seen.add(folded)
        entries.append(ArtifactDigest(path, len(artifact.content), hashlib.sha256(artifact.content).hexdigest()))
    entries.sort(key=lambda entry: entry.path.encode("utf-8"))
    canonical = b"".join(
        f"{entry.path}\t{entry.bytes}\t{entry.sha256}\n".encode("utf-8") for entry in entries
    )
    return PackageDigestResult(tuple(entries), canonical, hashlib.sha256(canonical).hexdigest())


def calculate_manifest_digest(manifest_bytes: bytes) -> str:
    if not isinstance(manifest_bytes, bytes):
        raise ValueError("MANIFEST_BYTES_MISSING")
    return hashlib.sha256(manifest_bytes).hexdigest()
