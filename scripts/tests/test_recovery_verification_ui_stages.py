"""Offline boundary checks only; no fake login, browser, data or restore result."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "recovery_verification"))
from core import VerificationError
from ruoyi_ui import request_violation, validate_flows
from run_ui_recovery import validate_endpoints, prepare, check_started_protection


def endpoints(phase="baseline"):
    selected = "http://127.0.0.1:18082" if phase == "target" else "http://127.0.0.1:18081"
    return {"phase": phase, "sourceOrigin": "http://127.0.0.1:18081", "targetOrigin": "http://127.0.0.1:18082",
            "apiOrigin": selected, "baseUrl": selected + "/login", "allowedOrigins": [selected, "http://127.0.0.1:19001"],
            "objectOrigins": ["http://127.0.0.1:19001"],
            "writeApiPaths": [] if phase == "target" else ["/admin-api/mes/md/product-sop/create"]}


@pytest.mark.parametrize("url", ["http://localhost:8081", "http://127.0.0.1:9000", "http://[::1]:8081"])
def test_legacy_shared_endpoints_are_rejected(url):
    config = endpoints()
    config["allowedOrigins"].append(url)
    with pytest.raises(VerificationError, match="UI_SHARED_LEGACY_ENDPOINT_PROHIBITED"):
        validate_endpoints(config)


def test_target_cannot_allow_source_origin():
    config = endpoints("target")
    config["allowedOrigins"].append(config["sourceOrigin"])
    with pytest.raises(VerificationError, match="UI_STAGE_ENDPOINT_SCOPE"):
        validate_endpoints(config)


@pytest.mark.parametrize("method,path,headers,expected", [
    ("PUT", "/admin-api/mes/md/product-sop/update", {"tenant-id": "122"}, "UNAPPROVED_BUSINESS_WRITE"),
    ("GET", "/admin-api/mes/md/item/page", {"tenant-id": "1"}, "WRONG_TENANT"),
    ("GET", "/admin-api/mes/md/item/page", {"tenant-id": "122", "visit-tenant-id": "1"}, "WRONG_TENANT"),
    ("GET", "/admin-api/showroom/company/get", {"tenant-id": "122"}, "PROTECTED_PATH"),
    ("POST", "/admin-api/system/auth/login", {"tenant-id": "122"}, "WRONG_LOGIN"),
])
def test_target_side_effects_and_wrong_identity_rejected(method, path, headers, expected):
    config = endpoints("target")
    assert request_violation(config, method, config["apiOrigin"] + path, headers, None, None) == expected


def test_source_write_scope_is_exact_path_not_prefix():
    config = endpoints()
    url = config["apiOrigin"] + "/admin-api/mes/md/product-sop/create-other"
    assert request_violation(config, "POST", url, {"tenant-id": "122"}, None, 122) == "UNAPPROVED_BUSINESS_WRITE"


def test_cross_origin_presigned_object_write_is_rejected():
    config = endpoints()
    assert request_violation(config, "PUT", "http://127.0.0.1:19001/private/object", {}, None, 122) == "UNAPPROVED_OBJECT_WRITE"


def test_target_upload_is_rejected_before_browser():
    with pytest.raises(VerificationError, match="TARGET_BUSINESS_UPLOAD_PROHIBITED"):
        validate_flows([{"pathId": "query", "entrySteps": [{"kind": "click", "selector": "a"}],
                         "steps": [{"kind": "upload", "selector": "input[type=file]", "contentPin": {}}]}], "target")


def test_missing_download_entry_is_not_converted_to_success():
    flow = {"pathId": "download", "entrySteps": [{"kind": "click", "selector": "a"}],
            "steps": [{"kind": "text", "selector": ".title", "expected": "actual selected title"}]}
    with pytest.raises(VerificationError, match="UI_DOWNLOAD_COUNT"):
        validate_flows([flow], "target")


def test_missing_independent_authorization_stops_before_reading_config():
    with pytest.raises(VerificationError, match="UI_CALLER_TRUST_REQUIRED"):
        prepare(str(Path(__file__).resolve().parent / "unprovided-runtime-config.json"), None)


def test_success_label_cannot_release_target_without_real_start_policy():
    pin = {"path": str(Path(__file__).resolve()), "bytes": 1, "sha256": "0" * 64}
    side = {"targetIdentityPin": pin, "applicationWriteProtectionPolicyPin": pin}
    records = iter([side, {"schemaVersion": "success-label-only", "state": "ENFORCED"}])
    with pytest.raises(VerificationError, match="UI_START_PROTECTION_POLICY_REQUIRED"):
        check_started_protection({"sideEffectIsolationPin": pin, "targetIdentityPin": pin}, {}, lambda _: next(records))
