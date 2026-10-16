"""Local gate-test records. These are never runtime acceptance evidence."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]
MODULE = REPO / "ops" / "recovery"
sys.path.insert(0, str(MODULE))

from recovery_environment_contract import Trust, atomic_json, pin_file, utc_now
from recovery_environment import ENTRANCE_TYPES


class LocalRecords:
    def __init__(self, root):
        self.root = root
        self.material = root / "material"
        self.material.mkdir()
        for name in ("evidence", "journal", "private"):
            (root / name).mkdir()
        self.sequence = 0
        self.schema_pin = pin_file(REPO / "doc/tasks/20261010-backup-restore-modular-development/record-schemas.json")
        sample = self.write("local-gate.json", {"purpose": "schema and gate unit input; not business evidence"})
        tool = self.raw("not-an-executable.bin", b"Local unit material; never invoked\n")
        self.source = {"schemaVersion": "RecoverySourceScope/v1", "machineId": "source-machine",
            "sourceIdentityPin": sample, "containerIds": [], "containerNames": ["source-backend"],
            "writerContainerIds": [], "volumeNames": ["source-mysql"], "networkNames": ["source-network"],
            "materialPaths": [str(root / "source-only")], "endpointHosts": ["10.40.0.2"]}
        source_pin = self.write("source.json", self.source)
        target_pin = self.write("identity.json", {"schemaVersion": "RecoveryTargetIdentity/v1", "targetId": "unit-target",
            "machineId": "unit-machine", "dockerEngineId": "unit-engine", "sourceIdentityPin": sample})
        roles = ["mysql", "minio", "redis", "backend", "frontend"]
        self.services = []
        for index, role in enumerate(roles):
            mount = {"mysql": "/var/lib/mysql", "minio": "/data", "redis": "/data"}.get(role)
            health = {"minio": (9000, "/minio/health/live", "HTTP_200"),
                      "backend": (8080, "/health", "BACKEND_UP"), "frontend": (80, "/", "HTML")}.get(role)
            self.services.append({"role": role, "name": "unit-" + role, "ip": f"172.29.240.{index+2}",
                "memoryBytes": 1024 * 1024, "cpuMillis": 100, "capabilities": [], "command": [], "env": {},
                "mounts": [{"volume": "unit-" + role + "-data", "target": mount, "readOnly": False}] if mount else [],
                "configurationMounts": [], "ports": [{"hostPort": 18081, "containerPort": 80}] if role == "frontend" else [],
                "health": dict(zip(("port", "path", "expected"), health)) if health else None})
        self.images = {}
        image_pins = []
        for index, role in enumerate(roles):
            image = {"schemaVersion": "RecoveryImage/v1", "role": role, "imageId": "sha256:" + str(index+1)*64,
                     "architecture": "amd64", "os": "linux", "version": "unit-fixture", "archivePin": tool}
            self.images[role] = image
            image_pins.append(self.write("image-" + role + ".json", image))
        endpoints = {key: {"host": role, "port": port, "domain": "unit-"+role}
            for key, role, port in (("database", "mysql", 3306), ("objectStore", "minio", 9000),
                                   ("redis", "redis", 6379), ("backend", "backend", 8080), ("frontend", "frontend", 80))}
        bindings = []
        for role, key, endpoint, template in (("backend", "DB_URL", "database", "jdbc:mysql://{host}:{port}/{database}"),
            ("backend", "OBJECT_URL", "objectStore", "http://{host}:{port}"),
            ("backend", "REDIS_ADDRESS", "redis", "{host}:{port}"),
            ("frontend", "BACKEND_URL", "backend", "http://{host}:{port}")):
            next(service for service in self.services if service["role"] == role)["env"][key] = template.format(**endpoints[endpoint], database="unit_db")
            bindings.append({"service": role, "environment": key, "endpoint": endpoint, "template": template,
                             "consumerEvidencePins": [sample]})
        self.configuration = {"schemaVersion": "RecoveryApplicationConfiguration/v1", "targetId": "unit-target", "database": "unit_db",
            "buckets": ["unit-bucket"], "serviceEnvironment": {service["role"]: deepcopy(service["env"]) for service in self.services},
            "endpointMap": endpoints, "endpointBindings": bindings}
        configuration_pin = self.write("application-configuration.json", self.configuration)
        inventories = []
        for role in ("backend", "frontend"):
            inventories.append(self.write("startup-" + role + ".json", {"schemaVersion": "RecoveryStartupInventory/v1", "role": role,
                "imageId": self.images[role]["imageId"], "complete": True,
                "entrances": [{"id": role+"-"+kind, "type": kind, "state": "ABSENT_IN_PINNED_IMAGE", "requiredEnvironment": {},
                               "evidencePins": [sample]} for kind in sorted(ENTRANCE_TYPES)]}))
        secrets = []
        for role, key in (("mysql", "MYSQL_ROOT_PASSWORD"), ("mysql", "RECOVERY_MYSQL_CLIENT_CNF"),
                          ("minio", "MINIO_ROOT_USER"), ("minio", "MINIO_ROOT_PASSWORD")):
            secret = self.raw("unit-private-" + key, b"unit-test-value")
            os.chmod(secret["path"], 0o600)
            secrets.append(self.write("reference-" + key + ".json", {"schemaVersion": "RecoverySecretReference/v1", "service": role,
                "environment": key, "provider": "FILE", "filePin": secret, "custody": "INDEPENDENT"}))
        self.config = {"schemaVersion": "RecoveryEnvironmentConfig/v1", "targetId": "unit-target", "targetIdentityPin": target_pin,
            "sourceScopePin": source_pin, "evidenceRoot": str(root/"evidence"), "journalRoot": str(root/"journal"),
            "privateRoot": str(root/"private"), "materialRoots": [str(self.material)], "dockerPin": tool, "pythonPin": tool,
            "iptablesPin": tool, "imagePins": image_pins, "configurationPin": configuration_pin, "secretRefs": secrets,
            "network": {"name": "unit-network", "subnet": "172.29.240.0/24", "gateway": "172.29.240.1", "bridge": "br-unit"},
            "services": self.services, "database": "unit_db", "buckets": ["unit-bucket"], "controlledPreconditions": None}
        self.policy = {"schemaVersion": "RecoveryEnvironmentPolicy/v2", "recordSchemasPin": self.schema_pin,
            "dockerServerVersion": "unit-unexecuted", "architecture": "amd64", "requiredDataBytes": 1024,
            "requiredTemporaryBytes": 1024, "requiredMemoryBytes": 5*1024*1024, "probeTimeoutSeconds": 1,
            "startupTimeoutSeconds": 2, "s3Region": "us-east-1", "mysqlClientPath": "/usr/bin/mysql", "requiredRoles": roles,
            "imageSha256s": [pin["sha256"] for pin in image_pins], "requiredSafeEnvironment": {role: {} for role in roles},
            "startupInventoryPins": inventories, "blockedEndpoints": [{"host": "10.40.0.2", "port": 80, "class": "SOURCE"},
                {"host": "172.29.240.1", "port": 22, "class": "HOST"}, {"host": "192.0.2.1", "port": 443, "class": "EXTERNAL"}],
            "blockedDnsName": "unit.example.com", "sourceScopeSha256": source_pin["sha256"], "maximumProofAgeSeconds": 300,
            "moduleSourcePins": [pin_file(MODULE/name) for name in ("environment_cli.py", "recovery_environment.py",
                "recovery_environment_contract.py", "recovery_environment_runtime.py", "recovery_environment_supervisor.py", "recovery_environment_probe.py", "recovery_application.py",
                "recovery_application_restore.py", "recovery_application_protection.py", "recovery_environment_fence.py", "w05_controlled_eligibility.py")],
            "restoreWorkerPin": pin_file(MODULE/"recovery_data.py"), "physicalRestartPolicyPin": None, "controlledFenceVerificationPin": None,
            "controlledEligibilityPin": None, "controlledVerificationPolicyPin": None, "controlledIndependentOriginalPins": []}
        self.policy["applicationWriteProtectionPin"] = self.write("write-protection-policy.json", {
            "schemaVersion": "RecoveryApplicationWriteProtectionPolicy/v1", "targetIdentityPin": target_pin,
            "configurationPin": configuration_pin, "imagePins": image_pins, "mechanismId": "unit-contract-only",
            "sourceEvidencePins": [sample], "enforceScriptPin": self.raw("unit-enforce.py", b"raise SystemExit(1)\n"),
            "observeScriptPin": self.raw("unit-observe.py", b"raise SystemExit(1)\n"),
            "requiredScopes": ["BUSINESS_DATABASE", "BUSINESS_OBJECTS", "BUSINESS_DERIVED", "APPLICATION_MUTATIONS", "SCHEDULERS", "EXTERNAL_DISPATCH"]})
        now = datetime.now(timezone.utc)
        self.authorization = {"schemaVersion": "RecoveryEnvironmentAuthorization/v1", "operationId": "unit-op", "targetId": "unit-target",
            "executorId": "unit-executor", "mode": "REHEARSAL", "actions": ["PREPARE_TARGET", "START_APPLICATION"],
            "notBefore": (now-timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
            "expiresAt": (now+timedelta(minutes=30)).isoformat().replace("+00:00", "Z"), "approved": True}
        self.lease = {"schemaVersion": "RecoveryEnvironmentLease/v1", "operationId": "unit-op", "targetId": "unit-target",
            "executorId": "unit-executor", "leaseId": "unit-lease", "fenceToken": 1, "notBefore": self.authorization["notBefore"],
            "expiresAt": self.authorization["expiresAt"], "state": "HELD"}
        self.point = {"schemaVersion": "RepositoryPoint/v1", "backupId": "unit-backup", "generationId": "unit-generation", "pointType": "FULL",
            "parentPointPins": [], "commonRecoveryPoint": "unit-consistency-marker", "manifestPin": sample, "payloadRefs": [sample],
            "readbackEvidencePin": sample, "ownerCloseEvidencePin": sample, "originalExitEvidencePin": sample,
            "integrityState": "COMPLETE", "blockedReason": None, "rehearsalEligible": True, "controlledRestoreEligible": True}
        self.point_pin = self.write("point.json", self.point)
        self.sample = sample
        self.approve()

    def raw(self, name, raw):
        path = self.material / name
        path.write_bytes(raw)
        return pin_file(path)

    def write(self, name, value):
        path = self.material / name
        atomic_json(path, value)
        return pin_file(path)

    def approve(self):
        """Explicitly repin unit authority after a test intentionally edits inputs."""
        config_pin = self.write("target-config.json", self.config)
        policy_pin = self.write("policy.json", self.policy)
        auth_pin = self.write("authorization.json", self.authorization)
        lease_pin = self.write("lease.json", self.lease)
        self.trust_pin = self.write("trust.json", {"schemaVersion": "RecoveryEnvironmentTrust/v1", "executorId": "unit-executor",
            "policySha256": policy_pin["sha256"], "targetConfigSha256": config_pin["sha256"], "recordSchemasPin": self.schema_pin,
            "authorizationSha256s": [auth_pin["sha256"]], "leaseSha256s": [lease_pin["sha256"]]})
        self.trust = Trust(self.trust_pin["path"], self.trust_pin["sha256"])
        self.request = {"schemaVersion": "backup-restore-operation/v1", "operationId": "unit-op", "requestId": "unit-request",
            "action": "PREPARE_TARGET", "mode": "REHEARSAL", "selectedPointPin": self.point_pin, "sourceOrTargetRef": config_pin,
            "policyPin": policy_pin, "authorizationRefs": [auth_pin], "leaseRef": lease_pin, "inputPins": {}, "deadlineMilliseconds": 5000}
        self.plan = {"schemaVersion": "RestorePlan/v1", "operationId": "unit-op", "restoreId": "unit-restore", "mode": "REHEARSAL",
            "candidatePin": self.point_pin, "orderedChainPins": [self.point_pin], "recoveryPoint": self.point["commonRecoveryPoint"],
            "targetRef": config_pin, "supportedVersionPins": [*self.config["imagePins"], self.sample], "toolPins": [self.config["pythonPin"]],
            "plannedWrites": [{"resource": "unit-database", "action": "IMPORT", "targetIdentityPin": self.config["targetIdentityPin"]}],
            "sideEffectPolicyPin": policy_pin, "authorizationRefs": [auth_pin], "leaseRef": lease_pin, "immutableInputsSha256": "a"*64}
        self.plan_pin = self.write("plan.json", self.plan)
        self.request["inputPins"] = {"restorePlan": self.plan_pin}

    def original_child(self, exit_code=0, timed_out=False):
        directory = self.material / "original-child"
        directory.mkdir(exist_ok=True)
        script = directory/"child.py"
        script.write_text(f"raise SystemExit({exit_code})\n", encoding="utf-8")
        request_pin = self.write("original-request.json", {"purpose": "harmless local subprocess"})
        intent = {"schemaVersion": "recovery-invocation/v1", "scriptPin": pin_file(script), "pythonPin": pin_file(sys.executable),
                  "requestPin": request_pin}
        atomic_json(directory/"intent.json", intent)
        intent_pin = pin_file(directory/"intent.json")
        child = subprocess.run([sys.executable, "-I", str(script)], capture_output=True, timeout=10)
        (directory/"stdout.bin").write_bytes(child.stdout)
        (directory/"stderr.bin").write_bytes(child.stderr)
        atomic_json(directory/"exit.json", {"schemaVersion": "recovery-original-exit/v1", "intentPin": intent_pin,
            "actualExitCode": child.returncode, "timedOut": timed_out, "remoteTerminalConfirmed": True})
        return [intent_pin, request_pin, pin_file(directory/"stdout.bin"), pin_file(directory/"stderr.bin"), pin_file(directory/"exit.json")]

    def start_inputs(self):
        """Gate-only assembly; no fabricated runtime output is passed to Docker."""
        self.config["pythonPin"] = pin_file(sys.executable)
        self.plan["toolPins"] = [self.config["pythonPin"]]
        self.plan_pin = self.write("plan.json", self.plan)
        proof = {"schemaVersion": "RecoveryEnvironmentProof/v1", "planPin": self.plan_pin, "operationId": "unit-op",
            "configurationRef": self.request["sourceOrTargetRef"], "targetIdentityPin": self.config["targetIdentityPin"],
            "leaseRef": self.request["leaseRef"], "recoveryPoint": self.plan["recoveryPoint"], "observedAt": utc_now()}
        side_effect = {"operationId": "unit-op", "state": "ENFORCED", "targetIdentityPin": self.config["targetIdentityPin"],
                       "policyPin": self.request["policyPin"], "startupInventoryPins": self.policy["startupInventoryPins"]}
        self.target = {"schemaVersion": "RecoveryTarget/v1", "targetId": "unit-target", "targetIdentityPin": self.config["targetIdentityPin"],
            "resourcesProofPin": self.write("resources-gate.json", proof), "isolationProofPin": self.write("isolation-gate.json", {"operationId": "unit-op"}),
            "versionPins": self.plan["supportedVersionPins"], "configurationPin": self.config["configurationPin"], "secretRefs": self.config["secretRefs"],
            "sideEffectIsolationPin": self.write("side-effects-gate.json", side_effect), "leaseRef": self.request["leaseRef"],
            "modePreconditionsPin": self.write("mode-gate.json", {"operationId": "unit-op"})}
        self.restore = {"schemaVersion": "RestoreExecutionResult/v1", "operationId": "unit-op", "restoreId": "unit-restore",
            "planPin": self.plan_pin, "targetIdentityPin": self.config["targetIdentityPin"], "recoveryPoint": self.plan["recoveryPoint"],
            "dbStepEvidencePins": [], "objectStepEvidencePins": [], "consistencyEvidencePin": self.sample,
            "originalInvocationPins": [], "state": "SUCCEEDED", "writeProtectionState": "ENFORCED"}
        self.request["action"] = "START_APPLICATION"
        self.repin_start()
        # Harmless local protocol worker: real subprocess exits and file output,
        # engineered payloads. These tests never claim data restoration.
        program = self.material/"unit-step-worker.py"
        program.write_text("import json,sys\nr=json.load(open(sys.argv[1]))\njson.dump(r,open(sys.argv[2],'w'))\n", encoding="utf-8")
        self.policy["restoreWorkerPin"] = pin_file(program)
        original = {**self.request, "action": "REHEARSAL", "inputPins": {"repositoryPoint": self.point_pin}}
        original_pin = self.write("w04-original-request.json", original)
        material_pin = self.write("step-material.json", {"schemaVersion": "RecoveryMaterial/v1",
            "sourceScopePin": self.config["sourceScopePin"], "recoveryPoint": self.plan["recoveryPoint"]})
        db_data = {"recoveryPoint": self.plan["recoveryPoint"], "databaseUuid": "unit-db"}
        object_data = {"recoveryPoint": self.plan["recoveryPoint"], "objects": "unit-shape"}
        db_pin = self.step_original("DATABASE_FULL", db_data, original_pin, material_pin)
        object_pin = self.step_original("OBJECT_FULL", object_data, original_pin, material_pin,
                                        previousObjectResultPin=None, parentRecoveryPoint=None)
        db_result = self.write("db-final-data.json", db_data)
        object_result = self.write("object-final-data.json", object_data)
        derived_data = {"schemaVersion": "RecoveryDerivedEvidence/v1", "recoveryPoint": self.plan["recoveryPoint"],
                        "targetIdentityPin": self.config["targetIdentityPin"], "classes": []}
        derived_pin = self.step_original("DERIVED_DATA", derived_data, original_pin, material_pin,
                                         databaseResultPin=db_result, objectResultPin=object_result)
        consistency = {"schemaVersion": "RecoveryConsistencyEvidence/v1", "recoveryPoint": self.plan["recoveryPoint"],
                       "targetIdentityPin": self.config["targetIdentityPin"], "allReferencesVerified": True,
                       "invariantsVerified": True, "applicationVerified": False}
        consistent_pin = self.step_original("CONSISTENCY", consistency, original_pin, material_pin,
                                            databaseResultPin=db_result, objectResultPin=object_result)
        self.restore.update(dbStepEvidencePins=[db_pin], objectStepEvidencePins=[object_pin],
            consistencyEvidencePin=self.write("consistency-gate.json", {**consistency, "derivedEvidencePin": derived_pin,
                "originalConsistencyResultPin": consistent_pin}))
        self.repin_start()
        return proof

    def step_original(self, action, data, original_pin, material_pin, **extra):
        directory = self.material/("step-"+action.lower())
        directory.mkdir()
        child = {"schemaVersion": "RecoveryDataRequest/v1", "operationId": "unit-op", "requestId": "step-"+action,
                 "action": action, "originalRequestPin": original_pin, "planPin": self.plan_pin,
                 "recoveryTargetPin": self.request["inputPins"]["recoveryTarget"], "materialPin": material_pin,
                 "deadlineMilliseconds": 5000, **extra}
        atomic_json(directory/"request.json", child)
        child_pin = pin_file(directory/"request.json")
        intent_pin = self.write_at(directory/"intent.json", {"schemaVersion": "recovery-invocation/v1",
            "scriptPin": self.policy["restoreWorkerPin"], "pythonPin": pin_file(sys.executable), "requestPin": child_pin,
            "startedAt": utc_now(), "style": "operation"})
        native_pin = self.write_at(directory/"native-000.json", {"schemaVersion": "RecoveryDataInvocation/v1",
            "operationId": "unit-op", "action": action, "state": "SUCCEEDED", "actualExitCode": 0, "mutation": False})
        envelope = {"schemaVersion": "RecoveryDataStepResult/v1", "operationId": "unit-op", "requestId": child["requestId"],
            "action": action, "state": "SUCCEEDED", "failureCode": None, "data": data,
            "originalResultPins": [native_pin], "actualExitCode": 0}
        envelope_pin = self.write_at(directory/"unit-envelope.json", envelope)
        output = directory/"result.json"
        process = subprocess.run([sys.executable, "-I", self.policy["restoreWorkerPin"]["path"], envelope_pin["path"], str(output)],
                                 capture_output=True, timeout=5)
        assert process.returncode == 0
        result_pin = pin_file(output)
        terminal_pin = self.write_at(directory/"exit.json", {"schemaVersion": "recovery-original-exit/v1",
            "intentPin": intent_pin, "actualExitCode": process.returncode, "timedOut": False,
            "remoteTerminalConfirmed": None, "finishedAt": utc_now()})
        self.restore["originalInvocationPins"].extend([intent_pin, child_pin, result_pin, terminal_pin])
        return result_pin

    def write_at(self, path, value):
        atomic_json(path, value)
        return pin_file(path)

    def repin_start(self):
        self.request["inputPins"] = {"restoreExecutionResult": self.write("restore-gate.json", self.restore),
                                     "recoveryTarget": self.write("target-gate.json", self.target)}
