from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "ops" / "release" / "release_build_preflight.py"
DOCKER_EVIDENCE_RUNNER = ROOT / "ops" / "release" / "release_docker_build_evidence.py"
PUBLISH_SCRIPT = ROOT / "ops" / "deploy" / "publish-int-ruoyi.ps1"


def _sha256(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _write_inputs(tmp_path: Path) -> tuple[Path, Path]:
    sql_dir = tmp_path / "required-sql"
    sql_dir.mkdir()
    sql = sql_dir / "20260908_contract.sql"
    sql.write_bytes(b"SELECT 1;\n")
    source_repos = [
        {
            "name": "backend",
            "pathRole": "backend",
            "commit": "1" * 40,
            "dirty": False,
        },
        {
            "name": "frontend",
            "pathRole": "admin-frontend",
            "commit": "2" * 40,
            "dirty": False,
        },
    ]
    migration = {
        "migrationId": "20260908_contract",
        "file": "required-sql/20260908_contract.sql",
        "sha256": _sha256(sql.read_bytes()),
        "type": "schema",
        "allowedEnvironments": ["test", "prod", "backup"],
        "dependsOn": [],
        "riskLevel": "medium",
    }
    manifest = {
        "schemaVersion": "release-build-prospective/v1",
        "releaseTag": "release-20260908",
        "sourceRepos": source_repos,
        "publishScope": "app-release",
        "database": {"schemaMigrations": [migration]},
        "requiredSql": [migration],
    }
    manifest_path = tmp_path / "prospective-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    target_state_path = tmp_path / "target-state.json"
    target_state_path.write_text(
        json.dumps(
            {
                "schemaVersion": "release-target-state/v1",
                "collectionId": "11111111-1111-4111-8111-111111111111",
                "collectedAt": "2026-09-08T03:00:00Z",
                "targetEnvironment": "test",
                "migrationLedger": {},
            }
        ),
        encoding="utf-8",
    )
    return manifest_path, target_state_path


def _run(tmp_path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    manifest, target_state = _write_inputs(tmp_path)
    output = tmp_path / "build-preflight-evidence.json"
    return subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8",
            str(RUNNER),
            "run",
            "--prospective-manifest",
            str(manifest),
            "--target-state",
            str(target_state),
            "--target-environment",
            "test",
            "--publish-scope",
            "app-release",
            "--output",
            str(output),
            *extra,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
    )


def test_runner_writes_complete_deterministic_binding_evidence(tmp_path: Path) -> None:
    result = _run(tmp_path)
    assert result.returncode == 0, result.stderr
    evidence = json.loads((tmp_path / "build-preflight-evidence.json").read_text(encoding="utf-8"))
    assert evidence["schemaVersion"] == "release-build-preflight/v1"
    assert evidence["status"] == "passed"
    assert evidence["targetEnvironment"] == "test"
    assert evidence["publishScope"] == "app-release"
    assert evidence["collectionId"] == "11111111-1111-4111-8111-111111111111"
    assert evidence["collectedAt"] == "2026-09-08T03:00:00Z"
    assert evidence["sourceCommits"] == {"backend": "1" * 40, "frontend": "2" * 40}
    assert set(evidence["bindings"]) == {
        "sourceFingerprint",
        "requiredSqlDigest",
        "prospectiveManifestDigest",
        "targetStateDigest",
        "plannerItemsDigest",
        "plannerStatusItemsDigest",
        "preflightFingerprint",
    }
    assert all(value.startswith("sha256:") for value in evidence["bindings"].values())
    assert evidence["bindings"]["preflightFingerprint"] == (
        "sha256:77a1be24cb22b07c6fdef14c2554a59101b696f40cafb5ad85c31457ad97a30f"
    )
    assert evidence["planner"]["status"] == "passed"
    assert evidence["planner"]["items"][0]["action"] == "APPLY"


def test_runner_is_deterministic_except_fresh_collection_identity(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    assert _run(first_dir).returncode == 0
    assert _run(second_dir).returncode == 0
    first = json.loads((first_dir / "build-preflight-evidence.json").read_text(encoding="utf-8"))
    second = json.loads((second_dir / "build-preflight-evidence.json").read_text(encoding="utf-8"))
    assert first["bindings"] == second["bindings"]


@pytest.mark.parametrize("field", ["source", "sql", "target", "environment", "scope"])
def test_material_input_drift_changes_binding_or_fails(tmp_path: Path, field: str) -> None:
    baseline = tmp_path / "baseline"
    changed = tmp_path / "changed"
    baseline.mkdir()
    changed.mkdir()
    assert _run(baseline).returncode == 0
    manifest_path, target_path = _write_inputs(changed)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    target = json.loads(target_path.read_text(encoding="utf-8"))
    command_extra: list[str] = []
    if field == "source":
        manifest["sourceRepos"][0]["commit"] = "3" * 40
    elif field == "sql":
        sql_path = changed / "required-sql" / "20260908_contract.sql"
        sql_path.write_bytes(b"SELECT 2;\n")
        digest = _sha256(sql_path.read_bytes())
        manifest["requiredSql"][0]["sha256"] = digest
        manifest["database"]["schemaMigrations"][0]["sha256"] = digest
    elif field == "target":
        target["migrationLedger"] = {
            "20260908_contract": {"status": "APPLIED", "sha256": "0" * 64}
        }
    elif field == "environment":
        target["targetEnvironment"] = "prod"
        command_extra = ["--target-environment", "prod"]
    else:
        manifest["publishScope"] = "code-only"
        command_extra = ["--publish-scope", "code-only"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    target_path.write_text(json.dumps(target), encoding="utf-8")
    output = changed / "evidence.json"
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(RUNNER), "run", "--prospective-manifest", str(manifest_path),
         "--target-state", str(target_path), "--target-environment", "test", "--publish-scope", "app-release",
         "--output", str(output), *command_extra],
        cwd=ROOT, text=True, capture_output=True, encoding="utf-8",
    )
    if field in {"environment", "scope"}:
        assert result.returncode != 0
    else:
        assert result.returncode == 0, result.stderr
        baseline_evidence = json.loads((baseline / "build-preflight-evidence.json").read_text(encoding="utf-8"))
        changed_evidence = json.loads(output.read_text(encoding="utf-8"))
        assert changed_evidence["bindings"]["preflightFingerprint"] != baseline_evidence["bindings"]["preflightFingerprint"]


@pytest.mark.parametrize(
    "mutation", ["blank", "malformed", "missing-ledger", "invalid-ledger", "wrong-environment"]
)
def test_invalid_target_state_fails_closed(tmp_path: Path, mutation: str) -> None:
    manifest, target = _write_inputs(tmp_path)
    if mutation == "blank":
        target.write_text("", encoding="utf-8")
    elif mutation == "malformed":
        target.write_text("{", encoding="utf-8")
    else:
        payload = json.loads(target.read_text(encoding="utf-8"))
        if mutation == "missing-ledger":
            payload.pop("migrationLedger")
        elif mutation == "invalid-ledger":
            payload["migrationLedger"] = {"migration-a": {"status": "", "sha256": "not-a-digest"}}
        else:
            payload["targetEnvironment"] = "prod"
        target.write_text(json.dumps(payload), encoding="utf-8")
    output = tmp_path / "evidence.json"
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(RUNNER), "run", "--prospective-manifest", str(manifest),
         "--target-state", str(target), "--target-environment", "test", "--publish-scope", "app-release",
         "--output", str(output)],
        cwd=ROOT, text=True, capture_output=True, encoding="utf-8",
    )
    assert result.returncode != 0
    assert not output.exists()


def test_blocked_plan_is_written_but_cannot_qualify_build(tmp_path: Path) -> None:
    manifest, target = _write_inputs(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["database"]["schemaMigrations"][0]["dependsOn"] = ["missing-prerequisite"]
    payload["requiredSql"][0]["dependsOn"] = ["missing-prerequisite"]
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    result = _run_existing_inputs(manifest, target, tmp_path / "evidence.json")
    assert result.returncode != 0
    evidence = json.loads((tmp_path / "evidence.json").read_text(encoding="utf-8"))
    assert evidence["status"] == "blocked"
    assert evidence["planner"]["items"][0]["action"] == "BLOCKED_DEPENDENCY_MISSING"


def _run_existing_inputs(manifest: Path, target: Path, output: Path, command: str = "run") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(RUNNER), command, "--prospective-manifest", str(manifest),
         "--target-state", str(target), "--target-environment", "test", "--publish-scope", "app-release",
         "--output", str(output)],
        cwd=ROOT, text=True, capture_output=True, encoding="utf-8",
    )


@pytest.mark.parametrize("mutation", ["status", "action", "missing-binding", "digest"])
def test_verify_rejects_invalid_or_tampered_evidence(tmp_path: Path, mutation: str) -> None:
    assert _run(tmp_path).returncode == 0
    manifest = tmp_path / "prospective-manifest.json"
    target = tmp_path / "target-state.json"
    evidence_path = tmp_path / "build-preflight-evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if mutation == "status":
        evidence["status"] = "blocked"
    elif mutation == "action":
        evidence["planner"]["items"][0]["action"] = "UNKNOWN"
    elif mutation == "missing-binding":
        evidence["bindings"].pop("requiredSqlDigest")
    else:
        evidence["bindings"]["targetStateDigest"] = "sha256:" + "0" * 64
    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
    result = _run_existing_inputs(manifest, target, evidence_path, command="verify")
    assert result.returncode != 0


def test_evidence_excludes_sensitive_manifest_material(tmp_path: Path) -> None:
    manifest, target = _write_inputs(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["password"] = "do-not-copy"
    payload["rawEnv"] = "TOKEN=do-not-copy"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    result = _run_existing_inputs(manifest, target, tmp_path / "evidence.json")
    assert result.returncode == 0, result.stderr
    serialized = (tmp_path / "evidence.json").read_text(encoding="utf-8")
    assert "do-not-copy" not in serialized
    assert "password" not in serialized.lower()
    assert "rawenv" not in serialized.lower()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("migrationId", "different-id"),
        ("file", "required-sql/different.sql"),
        ("sha256", "sha256:" + "0" * 64),
        ("type", "data"),
        ("allowedEnvironments", ["test"]),
        ("dependsOn", ["different-dependency"]),
        ("riskLevel", "high"),
    ],
)
def test_planner_migrations_must_exactly_match_required_sql(
    tmp_path: Path, field: str, value: object
) -> None:
    manifest, target = _write_inputs(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["database"]["schemaMigrations"][0][field] = value
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    result = _run_existing_inputs(manifest, target, tmp_path / "evidence.json")
    assert result.returncode != 0
    assert "schemaMigrations must exactly match requiredSql" in result.stderr


@pytest.mark.parametrize("dirty", [True, None, "false"])
def test_source_repo_must_explicitly_be_clean(tmp_path: Path, dirty: object) -> None:
    manifest, target = _write_inputs(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    if dirty is None:
        payload["sourceRepos"][0].pop("dirty")
    else:
        payload["sourceRepos"][0]["dirty"] = dirty
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    result = _run_existing_inputs(manifest, target, tmp_path / "evidence.json")
    assert result.returncode != 0
    assert "dirty=false" in result.stderr


def test_publish_script_orders_fresh_test_preflight_before_expensive_builds() -> None:
    script = PUBLISH_SCRIPT.read_text(encoding="utf-8")
    main_flow = script.index("if ($Mode -ne 'deploy-release')")
    stage = script.index("Copy-RequiredDatabaseSqlScripts", main_flow)
    preflight = script.index("Invoke-BuildReleaseTargetPreflight", stage)
    backend = script.index("Info 'Building backend jar'", preflight)
    frontend = script.index('Info "Building frontend static assets', preflight)
    docker = script.index("Info 'Building backend image'", preflight)
    assert stage < preflight < backend < docker
    assert preflight < frontend
    function_start = script.index("function Invoke-BuildReleaseTargetPreflight")
    function_end = script.index("\nfunction ", function_start + 1)
    function_body = script[function_start:function_end]
    assert "$TestServerHost" in function_body
    assert "[System.Guid]::NewGuid()" in function_body
    assert "Remove-Item -LiteralPath $evidenceRoot -Recurse -Force" in function_body
    assert "if ($capture.ExitCode -ne 0)" in function_body
    assert "target-state collection returned blank output" in function_body
    assert "target-state collection returned invalid JSON" in function_body
    assert "$stateSqlBase64 = [Convert]::ToBase64String" in function_body
    assert "printf '%s' '$stateSqlBase64' | base64 -d" in function_body
    assert "BUILD_PREFLIGHT_SQL" not in function_body
    assert "release_build_preflight.py" in function_body
    assert "build-preflight-evidence.json" in function_body
    assert "$stateSqlBase64 = [Convert]::ToBase64String" in function_body
    assert "printf '%s' '$stateSqlBase64' | base64 -d | docker exec" in function_body
    assert "BUILD_PREFLIGHT_SQL" not in function_body
    assert "table_count=" not in function_body


def _write_docker_spec(tmp_path: Path) -> tuple[Path, Path, Path]:
    context = tmp_path / "context"
    (context / "backend").mkdir(parents=True)
    (context / "frontend" / "dist").mkdir(parents=True)
    (context / "backend" / "app.jar").write_bytes(b"jar-v1")
    (context / "frontend" / "nginx.conf").write_bytes(b"server {}\n")
    (context / "frontend" / "dist" / "index.html").write_bytes(b"<main>v1</main>\n")
    backend_dockerfile = tmp_path / "Dockerfile.backend"
    backend_dockerfile.write_text(
        "ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\nCOPY backend/app.jar app.jar\n",
        encoding="utf-8",
    )
    frontend_dockerfile = tmp_path / "Dockerfile.frontend"
    frontend_dockerfile.write_text(
        "FROM nginx:1.27-alpine\n"
        "COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf\n"
        "COPY frontend/dist/ /usr/share/nginx/html/\n",
        encoding="utf-8",
    )
    spec = {
        "schemaVersion": "release-docker-build-spec/v1",
        "components": [
            {
                "name": "backend",
                "dockerfile": str(backend_dockerfile),
                "contextRoot": str(context),
                "buildArgs": {"BASE_IMAGE": "registry.local/runtime:17"},
                "baseImage": {
                    "reference": "registry.local/runtime:17",
                    "digest": "sha256:" + "1" * 64,
                },
                "imageReference": "app-backend:release-1",
            },
            {
                "name": "frontend",
                "dockerfile": str(frontend_dockerfile),
                "contextRoot": str(context),
                "buildArgs": {},
                "baseImage": {
                    "reference": "nginx:1.27-alpine",
                    "digest": "sha256:" + "2" * 64,
                },
                "imageReference": "app-frontend:release-1",
            },
        ],
    }
    spec_path = tmp_path / "docker-build-spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    evidence_path = tmp_path / "docker-build-input-evidence.json"
    actual_path = tmp_path / "actual-images.json"
    actual_path.write_text(
        json.dumps(
            {
                "backend": {
                    "reference": "app-backend:release-1",
                    "id": "sha256:" + "a" * 64,
                    "repoDigests": ["registry.local/app-backend@sha256:" + "b" * 64],
                },
                "frontend": {
                    "reference": "app-frontend:release-1",
                    "id": "sha256:" + "c" * 64,
                    "repoDigests": [],
                },
            }
        ),
        encoding="utf-8",
    )
    return spec_path, evidence_path, actual_path


def _run_docker_evidence(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(DOCKER_EVIDENCE_RUNNER), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
    )


def test_docker_evidence_covers_only_dockerfile_copy_inputs_args_and_base(tmp_path: Path) -> None:
    spec, evidence, _ = _write_docker_spec(tmp_path)
    result = _run_docker_evidence("capture", "--spec", str(spec), "--output", str(evidence))
    assert result.returncode == 0, result.stderr
    payload = json.loads(evidence.read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == "release-docker-build-input/v1"
    backend, frontend = payload["components"]
    assert backend["name"] == "backend"
    assert set(backend) == {
        "name", "imageReference", "inputFingerprint", "dockerfile", "context", "baseImage", "buildArgs"
    }
    assert [item["path"] for item in backend["context"]["files"]] == ["backend/app.jar"]
    assert [item["path"] for item in frontend["context"]["files"]] == [
        "frontend/dist/index.html",
        "frontend/nginx.conf",
    ]
    assert backend["baseImage"]["digest"] == "sha256:" + "1" * 64
    assert backend["buildArgs"]["values"] == {"BASE_IMAGE": "registry.local/runtime:17"}
    assert backend["inputFingerprint"] == (
        "sha256:0a6001e489cdfe2d4fa54c8f6e61cc1734701beb7252a2bb5f68a57767194b2c"
    )
    assert all(section["digest"].startswith("sha256:") for section in (
        backend["dockerfile"], backend["context"], backend["baseImage"], backend["buildArgs"]
    ))


@pytest.mark.parametrize("field", ["dockerfile", "context", "buildArg", "baseDigest"])
def test_docker_input_fingerprint_changes_for_every_material_input(tmp_path: Path, field: str) -> None:
    spec, evidence, _ = _write_docker_spec(tmp_path)
    assert _run_docker_evidence("capture", "--spec", str(spec), "--output", str(evidence)).returncode == 0
    baseline = json.loads(evidence.read_text(encoding="utf-8"))["components"][0]["inputFingerprint"]
    payload = json.loads(spec.read_text(encoding="utf-8"))
    if field == "dockerfile":
        Path(payload["components"][0]["dockerfile"]).write_text(
            "ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\nCOPY backend/app.jar /opt/app.jar\n", encoding="utf-8"
        )
    elif field == "context":
        (tmp_path / "context" / "backend" / "app.jar").write_bytes(b"jar-v2")
    elif field == "buildArg":
        payload["components"][0]["buildArgs"]["BASE_IMAGE"] = "registry.local/runtime:21"
        payload["components"][0]["baseImage"]["reference"] = "registry.local/runtime:21"
        spec.write_text(json.dumps(payload), encoding="utf-8")
    else:
        payload["components"][0]["baseImage"]["digest"] = "sha256:" + "9" * 64
        spec.write_text(json.dumps(payload), encoding="utf-8")
    changed = tmp_path / "changed.json"
    result = _run_docker_evidence("capture", "--spec", str(spec), "--output", str(changed))
    assert result.returncode == 0, result.stderr
    assert json.loads(changed.read_text(encoding="utf-8"))["components"][0]["inputFingerprint"] != baseline


@pytest.mark.parametrize("mutation", ["missing", "traversal", "duplicate", "invalid-digest", "missing-arg"])
def test_docker_input_contract_fails_closed(tmp_path: Path, mutation: str) -> None:
    spec, evidence, _ = _write_docker_spec(tmp_path)
    payload = json.loads(spec.read_text(encoding="utf-8"))
    dockerfile = Path(payload["components"][0]["dockerfile"])
    if mutation == "missing":
        dockerfile.write_text("ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\nCOPY backend/missing.jar app.jar\n", encoding="utf-8")
    elif mutation == "traversal":
        dockerfile.write_text("ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\nCOPY ../secret.txt app.jar\n", encoding="utf-8")
    elif mutation == "duplicate":
        dockerfile.write_text(
            "ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\nCOPY backend/app.jar app.jar\nCOPY backend/app.jar copy.jar\n",
            encoding="utf-8",
        )
    elif mutation == "invalid-digest":
        payload["components"][0]["baseImage"]["digest"] = "latest"
        spec.write_text(json.dumps(payload), encoding="utf-8")
    else:
        payload["components"][0]["buildArgs"] = {}
        spec.write_text(json.dumps(payload), encoding="utf-8")
    result = _run_docker_evidence("capture", "--spec", str(spec), "--output", str(evidence))
    assert result.returncode != 0
    assert not evidence.exists()


def test_docker_input_drift_after_build_is_rejected(tmp_path: Path) -> None:
    spec, evidence, _ = _write_docker_spec(tmp_path)
    assert _run_docker_evidence("capture", "--spec", str(spec), "--output", str(evidence)).returncode == 0
    (tmp_path / "context" / "backend" / "app.jar").write_bytes(b"changed-during-build")
    result = _run_docker_evidence("verify-input", "--spec", str(spec), "--evidence", str(evidence))
    assert result.returncode != 0


def test_final_docker_evidence_records_actual_images_and_recomputes(tmp_path: Path) -> None:
    spec, evidence, actual = _write_docker_spec(tmp_path)
    assert _run_docker_evidence("capture", "--spec", str(spec), "--output", str(evidence)).returncode == 0
    final = tmp_path / "package" / "manifest" / "docker-build-evidence.json"
    result = _run_docker_evidence(
        "finalize", "--spec", str(spec), "--evidence", str(evidence),
        "--actual-images", str(actual), "--output", str(final)
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(final.read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == "release-docker-build-evidence/v1"
    assert payload["components"][0]["actualImage"]["id"] == "sha256:" + "a" * 64
    assert payload["components"][1]["actualImage"]["id"] == "sha256:" + "c" * 64
    assert payload["evidenceDigest"].startswith("sha256:")


def test_publish_script_uses_native_cache_and_keeps_governance_order() -> None:
    script = PUBLISH_SCRIPT.read_text(encoding="utf-8")
    backend_build = script.index("Info 'Building backend image'")
    frontend_build = script.index("Info 'Building frontend image'")
    save = script.index("Info 'Exporting release images'", frontend_build)
    manifest = script.index("Write-ReleaseManifest -PackageTag $ReleaseTag", save)
    integrity = script.index("Test-ReleasePackageIntegrity", manifest)
    nas_copy = script.index("Copy-ReleasePackageToNas", integrity)
    assert "--no-cache" not in script[backend_build:frontend_build]
    assert "--no-cache" not in script[frontend_build:save]
    capture = script.index("\nWrite-DockerBuildInputEvidence\n", 0, backend_build)
    verify = script.index("\nAssert-DockerBuildInputsUnchanged\n", backend_build, save)
    finalize = script.index("\nWrite-FinalDockerBuildEvidence\n", verify, save)
    assert capture < backend_build < verify < finalize < save < manifest < integrity < nas_copy
    finalize_function = script.index("function Write-FinalDockerBuildEvidence")
    finalize_function_end = script.index("\nfunction ", finalize_function + 1)
    finalize_body = script[finalize_function:finalize_function_end]
    assert "Get-DockerImageIdentity" in finalize_body
    assert "manifest\\docker-build-evidence.json" in finalize_body
