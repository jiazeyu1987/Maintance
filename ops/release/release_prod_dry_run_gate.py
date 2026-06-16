from __future__ import annotations

from typing import Any


class ProdDryRunGateError(RuntimeError):
    """Raised when production deploy-release lacks valid dry-run evidence."""


def validate_prod_dry_run_evidence(evidence: dict[str, Any] | None, *, release_tag: str) -> dict[str, Any]:
    if not evidence:
        raise ProdDryRunGateError("missing prod dry-run evidence")
    if evidence.get("status") != "passed":
        raise ProdDryRunGateError(f"prod dry-run evidence status must be passed: {evidence.get('status')}")
    if evidence.get("targetEnvironment") != "prod":
        raise ProdDryRunGateError(
            f"prod dry-run evidence targetEnvironment must be prod: {evidence.get('targetEnvironment')}"
        )
    if evidence.get("releaseTag") != release_tag:
        raise ProdDryRunGateError(
            f"prod dry-run evidence releaseTag does not match deploy-release: {evidence.get('releaseTag')}"
        )
    if evidence.get("mode") != "preflight-release":
        raise ProdDryRunGateError(f"prod dry-run evidence mode must be preflight-release: {evidence.get('mode')}")
    write_actions = evidence.get("writeActions")
    if not isinstance(write_actions, list):
        raise ProdDryRunGateError("prod dry-run evidence writeActions must be an explicit list")
    if write_actions:
        raise ProdDryRunGateError("prod dry-run evidence must be read-only")
    return evidence
