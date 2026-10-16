"""Affected checks of the actual W05 runtime binding; no remote or native calls."""
from copy import deepcopy
from datetime import datetime, timezone
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import registration as r


def check():
    value = r.validate(r.load(ROOT / "smallapp.registration.json"))
    observation = r.local_document(value["evidencePins"]["actualRuntimeBindingObservation"])
    owner = {name: r.local_document(pin) for name, pin in observation["transportPins"].items()}
    for name, phase in owner.items():
        raw = r.verified_raw(observation["exactNativeOriginalTransportCopies"][name])
        original = phase["nativeResultOriginalPin"]
        assert len(raw) == original["bytes"] and hashlib.sha256(raw).hexdigest() == original["sha256"]
    assert value["runtime"]["sourceConfigurationFields"] == owner["configure"]["publicConfiguration"]["backend"]
    assert value["runtime"]["configurationPin"] == owner["configure"]["backendConfigurationPin"]
    assert value["source"]["assetInventory"]["applicationFilePins"] == owner["stage"]["sourceInstalledPins"]
    assert len(value["source"]["assetInventory"]["applicationFilePins"]) == 26
    assert value["runtime"]["pythonPin"] == owner["engine"]["actualRuntimePythonPin"]
    assert value["runtime"]["dependencyClosurePin"] == owner["stage"]["nativeResultOriginalPin"]
    assert [item["requirement"] for item in observation["source"]["declaredDependencyBindings"]] == value["runtime"]["dependencyNames"]
    assert len(observation["source"]["declaredDependencyBindings"]) == 11
    assert observation["engine"]["stageRuntimeMembers"] == 62 and observation["engine"]["currentRuntimeMembers"] == 63
    assert value["engineSelectionRef"] == observation["engine"]["currentObservedSelection"]["engineSelectionRef"]
    for key in ("engineArtifactPin", "engineEntryPin", "engineVersionPin"):
        assert observation["engine"]["currentObservedSelection"][key] == owner["common-refresh"][key]
    assert observation["engine"]["currentEngineApproved"] is False
    assert observation["source"]["healthIsBusinessUseProof"] is False
    assert value["source"]["redis"]["applicationUseProofPin"] is None
    assert value["allowedRestoreTargets"][0]["redis"]["applicationUseProofPin"] is None
    assert owner["verify"]["businessDataWritten"] is False
    assert owner["verify"]["writerBarrier"]["state"] == "PROTECTED"
    assert owner["verify"]["frontend"]["actualHttpStatus"] == 200
    assert owner["verify"]["actualRedisConsumerProof"]["redisDbSize"] == 0
    source, target = value["source"]["redis"], value["allowedRestoreTargets"][0]["redis"]
    target_ref = target["configRef"]
    assert source["state"] == target["state"] == "OBSERVED_ALLOCATED"
    assert source["serverVersion"] == target["serverVersion"] == "7.4.8"
    assert target["runtimeConfigurationPin"] == owner["target_configure"]["backendConfigurationPin"]
    assert source["secretReference"] != target["secretReference"]
    assert value["allowedRestoreTargets"][0]["freshnessProofPin"] is None
    assert value["source"]["resourceBindingPin"] is None and value["source"]["nativeConfigPin"] is None
    assert all(item is None for item in observation["nativeUnconfigured"].values())
    bad = deepcopy(value)
    bad["runtime"]["sourceConfigurationFields"] = owner["target_configure"]["publicConfiguration"]["backend"]
    try:
        r.validate(bad)
    except r.Invalid as error:
        assert str(error) == "RUNTIME_REGISTRATION_MISMATCH"
    else:
        raise AssertionError("target config accepted as source")
    sys.path.insert(0, str(ROOT.parents[2] / "backend/src/main/resources"))
    from recovery_control_registration import metadata, action_missing, source_metadata_gate
    from recovery_control_smallapp import Failure
    metadata(value)
    actions = {}
    for action, selected in (("FULL", None), ("INCREMENTAL", None), ("START_APPLICATION", None), ("RESTORE", target_ref)):
        actions[action] = dict(targetConfigRef=selected, w08Missing=r.missing(value, action, selected),
                               w01Missing=action_missing(value, action, selected))
    full = {item["field"] for item in actions["FULL"]["w01Missing"]}
    assert not any(key.startswith("runtime.") or key.startswith("source.assetInventory.") for key in full)
    assert "source.redis.applicationUseProofPin" in full
    assert not any(key.startswith("allowedRestoreTargets") or key in ("archive.fullParentChainRef", "archive.recoveryPointRef") for key in full)
    assert "archive.fullParentChainRef" in {i["field"] for i in actions["INCREMENTAL"]["w08Missing"]}
    assert "archive.recoveryPointRef" in {i["field"] for i in actions["RESTORE"]["w08Missing"]}
    for action in ("START_APPLICATION", "RESTORE"):
        assert not any(i["field"].endswith("applicationUseProofPin") for i in actions[action]["w01Missing"])
    try:
        source_metadata_gate(value, "FULL")
    except Failure as error:
        assert str(error) == "REGISTERED_ACTION_INPUTS_UNCONFIGURED"
    else:
        raise AssertionError("runtime acceptance inferred without actual native/private inputs")
    semantic = r.redis_inputs(value, "FULL", scope="SEMANTIC")
    assert semantic["instance"]["serverVersion"] == "7.4.8" and semantic["executionReadiness"] == "NOT_EVALUATED"
    try:
        r.redis_inputs(value, "FULL")
    except r.Invalid as error:
        assert str(error) == "REDIS_INPUTS_UNCONFIGURED"
    else:
        raise AssertionError("runtime projection accepted before private/business proof")
    result = subprocess.run([sys.executable, "-B", str(ROOT / "registration.py"), "validate",
                             str(ROOT / "smallapp.registration.json"), "--verify-local-evidence"],
                            capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0
    cli = json.loads(result.stdout)
    assert cli["nativeApplicationFilePinsNotVerified"] == 26
    assert cli["executionReadiness"] == "NOT_EVALUATED"
    for name in ("registration.py", "check_runtime_binding.py"):
        ast.parse((ROOT / name).read_text(encoding="utf-8"), filename=name)
    return dict(schemaVersion="W08RuntimeBindingChecks/v1", at=datetime.now(timezone.utc).isoformat(), passed=True,
                scope="Affected actual-field bindings, SOURCE/TARGET config refusal, original W01 metadata/actions, local-only CLI and runtime refusal",
                reusedEightGroupEvidence="history/pre-runtime-binding/checks-redis.json (8/8 previous immutable semantic scope)",
                actualOwnerPinsAndInstalledFieldsMatched=True, currentW01PureMetadataAccepted=True,
                sourceFullHasNoFutureTargetParentPoint=True, healthAcceptedAsBusinessUse=False,
                currentNativeAuthorityAccepted=False, runtimeAcceptance=False, actionInputs=actions,
                localEvidenceVerified=cli["verifiedLocalEvidenceCount"], nativeApplicationFilePinsNotVerified=26,
                remoteCalls=0, serviceMocks=0, businessWrites=0)


if __name__ == "__main__":
    report = check()
    (ROOT / "checks-runtime-binding.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("passed", "currentW01PureMetadataAccepted", "sourceFullHasNoFutureTargetParentPoint", "runtimeAcceptance", "nativeApplicationFilePinsNotVerified")}, ensure_ascii=False))
