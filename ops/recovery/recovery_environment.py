"""PREPARE_TARGET orchestration and strict runtime configuration.

Business imports belong to W04. A successful preparation proves a dedicated
empty target and usable pinned dependencies, never a successful data recovery.
"""
from __future__ import annotations

import hashlib
import ipaddress
import os
from pathlib import Path
import re
from string import Formatter
import time
from datetime import datetime, timezone

from recovery_environment_contract import (EnvironmentFailure, Trust, atomic_json, authorize, canonical,
    decode, digest, exact, original_w04_exits, pin_file, read_bytes, read_pin, require, safe_path, text, utc, utc_now, verify_large_pin)
from recovery_environment_runtime import (CommandRunner, NativeDocker, ensure_material_path, exclusive_lock)


CONFIG_FIELDS = ("schemaVersion", "targetId", "targetIdentityPin", "sourceScopePin", "evidenceRoot", "journalRoot",
                 "privateRoot", "materialRoots", "dockerPin", "pythonPin", "iptablesPin", "imagePins", "configurationPin",
                 "secretRefs", "network", "services", "database", "buckets", "controlledPreconditions")
POLICY_FIELDS = ("schemaVersion", "recordSchemasPin", "dockerServerVersion", "architecture", "requiredDataBytes",
                 "requiredTemporaryBytes", "requiredMemoryBytes", "probeTimeoutSeconds", "startupTimeoutSeconds",
                 "s3Region", "mysqlClientPath", "requiredRoles", "imageSha256s", "requiredSafeEnvironment",
                 "startupInventoryPins", "blockedEndpoints", "blockedDnsName", "sourceScopeSha256", "maximumProofAgeSeconds", "moduleSourcePins",
                 "restoreWorkerPin", "physicalRestartPolicyPin", "applicationWriteProtectionPin", "controlledFenceVerificationPin",
                 "controlledEligibilityPin", "controlledVerificationPolicyPin", "controlledIndependentOriginalPins")
ENTRANCE_TYPES = {"QUARTZ", "MQ", "HTTP_OUTBOUND", "NOTIFICATION", "WEBHOOK", "AUTO_DDL", "STARTUP_HOOK"}
NAME_PATTERN = r"[a-z][a-z0-9_-]{2,62}"


def validate_configuration(config, policy, trust, guard):
    exact(config, CONFIG_FIELDS, "TARGET_CONFIG_INVALID")
    exact(policy, POLICY_FIELDS, "ENVIRONMENT_POLICY_INVALID")
    require(config["schemaVersion"] == "RecoveryEnvironmentConfig/v1" and
            policy["schemaVersion"] == "RecoveryEnvironmentPolicy/v2", "CONFIGURATION_VERSION_INVALID")
    from w05_controlled_eligibility import validate_admission_policy
    validate_admission_policy(policy, guard)
    require(policy["recordSchemasPin"] == trust.value["recordSchemasPin"], "RECORD_SCHEMA_TRUST_MISMATCH")
    require(re.fullmatch(NAME_PATTERN, config["targetId"]), "TARGET_ID_INVALID")
    require(type(config["materialRoots"]) is list and config["materialRoots"], "INDEPENDENT_CUSTODY_ROOTS_REQUIRED")
    for name in ("evidenceRoot", "journalRoot", "privateRoot"):
        safe_path(config[name], directory=True)
    roots = [safe_path(config[name], directory=True) for name in ("evidenceRoot", "journalRoot", "privateRoot")]
    require(all(not a.is_relative_to(b) and not b.is_relative_to(a) for i, a in enumerate(roots) for b in roots[i + 1:]),
            "PRIVATE_PUBLIC_STATE_ROOT_OVERLAP")
    for name in ("requiredDataBytes", "requiredTemporaryBytes", "requiredMemoryBytes", "maximumProofAgeSeconds"):
        require(type(policy[name]) is int and policy[name] > 0, "RESOURCE_POLICY_REQUIRED")
    for name in ("probeTimeoutSeconds", "startupTimeoutSeconds"):
        require(type(policy[name]) is int and 0 < policy[name] <= 300, "HEALTH_BUDGET_INVALID")
    require(re.fullmatch(r"/[A-Za-z0-9_./-]+", policy["mysqlClientPath"]) and
            re.fullmatch(r"[A-Za-z0-9_-]+", config["database"]), "MYSQL_CONFIGURATION_INVALID")
    require(type(config["buckets"]) is list and config["buckets"] and len(set(config["buckets"])) == len(config["buckets"])
            and all(re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", bucket) for bucket in config["buckets"]),
            "OBJECT_BUCKET_CONFIGURATION_INVALID")
    identity = read_pin(config["targetIdentityPin"])
    exact(identity, ("schemaVersion", "targetId", "machineId", "dockerEngineId", "sourceIdentityPin"), "TARGET_IDENTITY_INVALID")
    require(identity["schemaVersion"] == "RecoveryTargetIdentity/v1" and identity["targetId"] == config["targetId"],
            "TARGET_IDENTITY_MISMATCH")
    source = read_pin(config["sourceScopePin"])
    exact(source, ("schemaVersion", "machineId", "sourceIdentityPin", "containerIds", "containerNames", "writerContainerIds",
                   "volumeNames", "networkNames", "materialPaths", "endpointHosts"), "SOURCE_SCOPE_INVALID")
    require(source["schemaVersion"] == "RecoverySourceScope/v1" and
            config["sourceScopePin"]["sha256"] == policy["sourceScopeSha256"] and
            identity["sourceIdentityPin"] == source["sourceIdentityPin"], "SOURCE_SCOPE_NOT_APPROVED")
    read_pin(source["sourceIdentityPin"])
    require(all(type(source[key]) is list for key in ("containerIds", "containerNames", "writerContainerIds", "volumeNames",
                                                   "networkNames", "materialPaths", "endpointHosts")), "SOURCE_SCOPE_LIST_INVALID")
    for resource in source["containerIds"] + source["writerContainerIds"]:
        require(re.fullmatch("[0-9a-f]{64}", resource), "SOURCE_CONTAINER_ID_INVALID")
    require(set(source["writerContainerIds"]).issubset(source["containerIds"]), "SOURCE_WRITERS_NOT_IN_SCOPE")
    require(all(Path(path).is_absolute() for path in source["materialPaths"]), "SOURCE_PATH_INVALID")
    require(all(not root.is_relative_to(Path(source_path)) for root in roots for source_path in source["materialPaths"]),
            "STATE_ROOT_IN_SOURCE_SCOPE_REJECTED")
    for name in ("dockerPin", "pythonPin", "iptablesPin", "configurationPin"):
        ensure_material_path(config[name]["path"], config)
        verify_large_pin(config[name], guard)
    for pin in policy["moduleSourcePins"]:
        verify_large_pin(pin, guard)
    required_modules = {Path(__file__).name, "recovery_environment_contract.py", "recovery_environment_runtime.py",
                        "recovery_environment_probe.py", "recovery_application.py", "environment_cli.py",
                        "recovery_application_restore.py", "recovery_application_protection.py"}
    required_modules.add("recovery_environment_fence.py")
    required_modules.add("recovery_environment_supervisor.py")
    required_modules.add("w05_controlled_eligibility.py")
    require({Path(pin["path"]).name for pin in policy["moduleSourcePins"]} == required_modules and
            all(Path(pin["path"]).parent == Path(__file__).parent for pin in policy["moduleSourcePins"]),
            "EXECUTOR_SOURCE_PINS_INCOMPLETE")
    require(Path(policy["restoreWorkerPin"]["path"]) == Path(__file__).with_name("recovery_data.py"),
            "RESTORE_WORKER_PATH_MISMATCH")
    verify_large_pin(policy["restoreWorkerPin"], guard)
    if policy["physicalRestartPolicyPin"] is not None:
        from recovery_application_restore import restart_policy
        restart_policy(config, policy, guard)
    network = config["network"]
    exact(network, ("name", "subnet", "gateway", "bridge"), "NETWORK_CONFIG_INVALID")
    require(re.fullmatch(NAME_PATTERN, network["name"]) and re.fullmatch(r"br-[a-z0-9]{3,10}", network["bridge"]),
            "NETWORK_NAME_INVALID")
    try:
        subnet = ipaddress.IPv4Network(network["subnet"], strict=True)
        gateway = ipaddress.IPv4Address(network["gateway"])
        require(subnet.is_private and subnet.prefixlen >= 24 and gateway in subnet.hosts(), "NETWORK_ADDRESS_INVALID")
    except ValueError:
        raise EnvironmentFailure("NETWORK_ADDRESS_INVALID") from None
    blocked = policy["blockedEndpoints"]
    require(re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,63}", policy["blockedDnsName"]), "DNS_NEGATIVE_PROBE_NAME_REQUIRED")
    require(type(blocked) is list and blocked, "NETWORK_NEGATIVE_PROBES_REQUIRED")
    hosts = set()
    classes = set()
    for endpoint in blocked:
        exact(endpoint, ("host", "port", "class"), "BLOCKED_ENDPOINT_INVALID")
        try:
            address = ipaddress.IPv4Address(endpoint["host"])
        except ValueError:
            raise EnvironmentFailure("BLOCKED_ENDPOINT_INVALID") from None
        require(address not in subnet or str(address) == network["gateway"], "BLOCKED_ENDPOINT_IN_TARGET_NETWORK")
        require(type(endpoint["port"]) is int and 0 < endpoint["port"] <= 65535, "BLOCKED_ENDPOINT_PORT_INVALID")
        hosts.add(endpoint["host"])
        classes.add(endpoint["class"])
    require({"SOURCE", "HOST", "EXTERNAL"}.issubset(classes) and network["gateway"] in hosts and
            set(source["endpointHosts"]).issubset(hosts), "SOURCE_HOST_EXTERNAL_PROBES_INCOMPLETE")
    roles = policy["requiredRoles"]
    require(type(roles) is list and {"mysql", "minio", "redis", "backend", "frontend"}.issubset(roles) and
            len(set(roles)) == len(roles), "DEPENDENCY_ROLES_REQUIRED")
    services = config["services"]
    require(type(services) is list and {service["role"] for service in services} == set(roles)
            and len(services) == len(roles), "SERVICE_ROLES_MISMATCH")
    images = {}
    for pin in config["imagePins"]:
        require(pin["sha256"] in policy["imageSha256s"], "IMAGE_METADATA_NOT_APPROVED")
        record = read_pin(pin)
        exact(record, ("schemaVersion", "role", "imageId", "architecture", "os", "version", "archivePin"), "IMAGE_RECORD_INVALID")
        require(record["schemaVersion"] == "RecoveryImage/v1" and record["role"] not in images and
                re.fullmatch("sha256:[0-9a-f]{64}", record["imageId"]) and record["os"] == "linux" and
                record["architecture"] == policy["architecture"], "IMAGE_VERSION_OR_ARCHITECTURE_MISMATCH")
        text(record["version"])
        ensure_material_path(record["archivePin"]["path"], config)
        images[record["role"]] = record
    require(set(images) == set(roles), "PINNED_IMAGE_ROLES_INCOMPLETE")
    configuration = read_pin(config["configurationPin"])
    exact(configuration, ("schemaVersion", "targetId", "database", "buckets", "serviceEnvironment", "endpointMap", "endpointBindings"),
          "APPLICATION_CONFIGURATION_INVALID")
    require(configuration["schemaVersion"] == "RecoveryApplicationConfiguration/v1" and
            configuration["targetId"] == config["targetId"] and configuration["database"] == config["database"] and
            configuration["buckets"] == config["buckets"], "APPLICATION_CONFIGURATION_TARGET_MISMATCH")
    endpoints = configuration["endpointMap"]
    require(type(endpoints) is dict and {"database", "objectStore", "redis", "backend", "frontend"}.issubset(endpoints),
            "TARGET_ENDPOINT_MAPPING_REQUIRED")
    service_by_role = {service["role"]: service for service in services}
    endpoint_roles = {"database": "mysql", "objectStore": "minio", "redis": "redis", "backend": "backend", "frontend": "frontend"}
    for key, role in endpoint_roles.items():
        exact(endpoints[key], ("host", "port", "domain"), "TARGET_ENDPOINT_INVALID")
        require(endpoints[key]["host"] in (role, service_by_role[role]["ip"]) and
                endpoints[key]["domain"] == service_by_role[role]["name"], "SOURCE_ENDPOINT_MAPPING_REJECTED")
        require(type(endpoints[key]["port"]) is int and 0 < endpoints[key]["port"] <= 65535,
                "TARGET_ENDPOINT_PORT_INVALID")
    validate_endpoint_bindings(configuration, config, guard)
    names, ips, ports, volume_owners = set(), set(), set(), {}
    for service in services:
        exact(service, ("role", "name", "ip", "memoryBytes", "cpuMillis", "capabilities", "command", "env", "mounts",
                        "configurationMounts", "ports", "health"), "SERVICE_CONFIG_INVALID")
        role = service["role"]
        require(re.fullmatch(NAME_PATTERN, service["name"]) and service["name"] not in names, "SERVICE_NAME_INVALID")
        names.add(service["name"])
        try:
            ip = ipaddress.IPv4Address(service["ip"])
            require(ip in subnet.hosts() and ip != gateway and ip not in ips, "SERVICE_IP_INVALID")
        except ValueError:
            raise EnvironmentFailure("SERVICE_IP_INVALID") from None
        ips.add(ip)
        require(type(service["memoryBytes"]) is int and service["memoryBytes"] > 0 and
                type(service["cpuMillis"]) is int and service["cpuMillis"] > 0, "SERVICE_RESOURCE_LIMIT_REQUIRED")
        require(type(service["capabilities"]) is list and len(set(service["capabilities"])) == len(service["capabilities"])
                and set(service["capabilities"]).issubset({"CHOWN", "DAC_OVERRIDE", "SETGID", "SETUID"})
                and (role in ("mysql", "minio", "redis") or not service["capabilities"]), "SERVICE_CAPABILITY_REJECTED")
        require(type(service["command"]) is list and all(type(arg) is str and "\x00" not in arg for arg in service["command"]),
                "SERVICE_COMMAND_INVALID")
        require(type(service["env"]) is dict and service["env"] == configuration["serviceEnvironment"][role],
                "SERVICE_ENV_CONFIGURATION_MISMATCH")
        for key, value in service["env"].items():
            require(re.fullmatch("[A-Za-z_][A-Za-z0-9_]*", key) and type(value) is str and
                    not any(char in value for char in "\x00\r\n") and not re.search("password|secret|token|credential|private.?key", key, re.I),
                    "PUBLIC_ENV_SECRET_OR_FORMAT_REJECTED")
            require(not any(host in value for host in source["endpointHosts"]), "SOURCE_ENV_ADDRESS_REJECTED")
        safe_env = policy["requiredSafeEnvironment"].get(role)
        require(type(safe_env) is dict and all(service["env"].get(key) == value for key, value in safe_env.items()),
                "SIDE_EFFECT_CONFIGURATION_NOT_ENFORCED")
        for mount in service["mounts"]:
            exact(mount, ("volume", "target", "readOnly"), "VOLUME_MOUNT_INVALID")
            require(re.fullmatch(NAME_PATTERN, mount["volume"]) and re.fullmatch(r"/[A-Za-z0-9_./-]+", mount["target"])
                    and ".." not in Path(mount["target"]).parts and type(mount["readOnly"]) is bool,
                    "VOLUME_MOUNT_INVALID")
            require(mount["volume"] not in volume_owners, "CROSS_SERVICE_VOLUME_SHARING_REJECTED")
            volume_owners[mount["volume"]] = role
        for mount in service["configurationMounts"]:
            exact(mount, ("pin", "target"), "CONFIGURATION_MOUNT_INVALID")
            ensure_material_path(mount["pin"]["path"], config)
            verify_large_pin(mount["pin"], guard)
            require(re.fullmatch(r"/[A-Za-z0-9_./-]+", mount["target"]) and ".." not in Path(mount["target"]).parts,
                    "CONFIGURATION_MOUNT_TARGET_INVALID")
        for port in service["ports"]:
            exact(port, ("hostPort", "containerPort"), "PORT_MAPPING_INVALID")
            require(role in ("backend", "frontend", "showroom") and
                    type(port["hostPort"]) is int and 1024 <= port["hostPort"] <= 65535
                    and type(port["containerPort"]) is int and 1 <= port["containerPort"] <= 65535
                    and port["hostPort"] not in ports, "PORT_MAPPING_UNSAFE")
            ports.add(port["hostPort"])
        if role not in ("mysql", "redis"):
            exact(service["health"], ("port", "path", "expected"), "HEALTH_CONFIGURATION_INVALID")
            require(type(service["health"]["port"]) is int and 0 < service["health"]["port"] <= 65535 and
                    re.fullmatch(r"/[A-Za-z0-9_./%-]*", service["health"]["path"]), "HEALTH_ENDPOINT_INVALID")
            expected = {"backend": "BACKEND_UP", "frontend": "HTML", "showroom": "HTML", "onlyoffice": "TRUE", "minio": "HTTP_200"}
            require(role in expected and service["health"]["expected"] == expected[role], "HEALTH_EXPECTATION_REQUIRED")
        else:
            require(service["health"] is None, "DEPENDENCY_NATIVE_HEALTH_REQUIRED")
    for role, target in (("mysql", "/var/lib/mysql"), ("minio", "/data"), ("redis", "/data")):
        require(any(mount["target"] == target and not mount["readOnly"] for mount in service_by_role[role]["mounts"]),
                "DEPENDENCY_PERSISTENT_VOLUME_REQUIRED")
    require(sum(service["memoryBytes"] for service in services) <= policy["requiredMemoryBytes"], "MEMORY_POLICY_TOO_SMALL")
    secret_keys = set()
    for pin in config["secretRefs"]:
        reference = read_pin(pin)
        exact(reference, ("schemaVersion", "service", "environment", "provider", "filePin", "custody"), "SECRET_REFERENCE_INVALID")
        require(reference["schemaVersion"] == "RecoverySecretReference/v1" and reference["provider"] == "FILE" and
                reference["custody"] == "INDEPENDENT" and reference["service"] in roles and
                re.fullmatch("[A-Za-z_][A-Za-z0-9_]*", reference["environment"]), "SECRET_REFERENCE_NOT_INDEPENDENT")
        key = reference["service"], reference["environment"]
        require(key not in secret_keys, "DUPLICATE_SECRET_BINDING")
        secret_keys.add(key)
        path = ensure_material_path(reference["filePin"]["path"], config)
        verify_large_pin(reference["filePin"], guard)
        if os.name == "posix":
            require(path.stat().st_mode & 0o077 == 0, "SECRET_FILE_PERMISSIONS_UNSAFE")
    require({("mysql", "MYSQL_ROOT_PASSWORD"), ("mysql", "RECOVERY_MYSQL_CLIENT_CNF"),
             ("minio", "MINIO_ROOT_USER"), ("minio", "MINIO_ROOT_PASSWORD")}.issubset(secret_keys), "DEPENDENCY_SECRETS_REQUIRED")
    validate_startup_inventory(config, policy, images, guard)
    from recovery_application_protection import validate_write_protection
    validate_write_protection(config, policy, guard)
    return config


def validate_endpoint_bindings(configuration, config, guard):
    """Bind approved consumer settings to target endpoints, not just metadata."""
    bindings = configuration["endpointBindings"]
    require(type(bindings) is list and bindings, "ENDPOINT_CONSUMER_BINDINGS_REQUIRED")
    services = {service["role"]: service for service in config["services"]}
    consumed, keys = set(), set()
    for binding in bindings:
        exact(binding, ("service", "environment", "endpoint", "template", "consumerEvidencePins"), "ENDPOINT_BINDING_INVALID")
        role, key, endpoint = binding["service"], binding["environment"], binding["endpoint"]
        require(role in services and endpoint in configuration["endpointMap"] and
                type(key) is str and re.fullmatch("[A-Za-z_][A-Za-z0-9_]*", key) and (role, key) not in keys,
                "ENDPOINT_BINDING_DUPLICATE_OR_UNKNOWN")
        keys.add((role, key))
        text(binding["template"], "ENDPOINT_TEMPLATE_REQUIRED")
        fields = set()
        try:
            for _, field, spec, conversion in Formatter().parse(binding["template"]):
                if field is not None:
                    require(field in {"host", "port", "domain", "database"} and not spec and not conversion,
                            "ENDPOINT_TEMPLATE_UNSAFE")
                    fields.add(field)
            require({"host", "port"}.issubset(fields), "ENDPOINT_TEMPLATE_ADDRESS_REQUIRED")
            value = binding["template"].format(**configuration["endpointMap"][endpoint], database=config["database"])
        except (ValueError, KeyError):
            raise EnvironmentFailure("ENDPOINT_TEMPLATE_INVALID") from None
        require(services[role]["env"].get(key) == value, "ENDPOINT_CONSUMER_CONFIGURATION_MISMATCH")
        require(type(binding["consumerEvidencePins"]) is list and binding["consumerEvidencePins"],
                "ENDPOINT_CONSUMER_SOURCE_EVIDENCE_REQUIRED")
        for pin in binding["consumerEvidencePins"]:
            verify_large_pin(pin, guard)
        consumed.add((role, endpoint))
    require({("backend", "database"), ("backend", "objectStore"), ("backend", "redis"), ("frontend", "backend")}.issubset(consumed),
            "ENDPOINT_CONSUMER_COVERAGE_INCOMPLETE")


def validate_startup_inventory(config, policy, images, guard=lambda: None):
    """Pin the actual image's complete startup/callout coverage, not one switch."""
    inventories = [read_pin(pin) for pin in policy["startupInventoryPins"]]
    needed = {role for role in images if role not in ("mysql", "minio", "redis")}
    require({item["role"] for item in inventories} == needed and len(inventories) == len(needed), "STARTUP_INVENTORY_INCOMPLETE")
    service_by_role = {service["role"]: service for service in config["services"]}
    for inventory in inventories:
        exact(inventory, ("schemaVersion", "role", "imageId", "complete", "entrances"), "STARTUP_INVENTORY_INVALID")
        require(inventory["schemaVersion"] == "RecoveryStartupInventory/v1" and inventory["complete"] is True and
                inventory["imageId"] == images[inventory["role"]]["imageId"], "STARTUP_INVENTORY_IMAGE_MISMATCH")
        classes = set()
        ids = set()
        for entrance in inventory["entrances"]:
            exact(entrance, ("id", "type", "state", "requiredEnvironment", "evidencePins"), "STARTUP_ENTRANCE_INVALID")
            text(entrance["id"])
            require(entrance["id"] not in ids and entrance["type"] in ENTRANCE_TYPES and entrance["evidencePins"],
                    "STARTUP_ENTRANCE_EVIDENCE_REQUIRED")
            ids.add(entrance["id"])
            classes.add(entrance["type"])
            for pin in entrance["evidencePins"]:
                # Source/classpath analysis original is independently pinned by
                # the approved policy. Its raw bytes need not be a JSON record.
                verify_large_pin(pin, guard)
            require(type(entrance["requiredEnvironment"]) is dict, "STARTUP_ENVIRONMENT_INVALID")
            if entrance["state"] == "DISABLED_BY_CONFIGURATION":
                require(entrance["requiredEnvironment"] and all(service_by_role[inventory["role"]]["env"].get(key) == value
                    and policy["requiredSafeEnvironment"][inventory["role"]].get(key) == value
                    for key, value in entrance["requiredEnvironment"].items()), "STARTUP_ENTRANCE_NOT_DISABLED")
            else:
                require(entrance["state"] == "ABSENT_IN_PINNED_IMAGE" and not entrance["requiredEnvironment"],
                        "STARTUP_ENTRANCE_UNSAFE")
        require(classes == ENTRANCE_TYPES, "STARTUP_CALL_PATH_COVERAGE_INCOMPLETE")


def validate_plan(plan, plan_pin, request, config, trust, guard=lambda: None):
    trust.schemas.validate(plan, "RestorePlan")
    require(plan["operationId"] == request["operationId"] and plan["mode"] == request["mode"] and
            plan["targetRef"] == request["sourceOrTargetRef"] and plan["candidatePin"] == request["selectedPointPin"] and
            plan["leaseRef"] == request["leaseRef"] and plan["sideEffectPolicyPin"] == request["policyPin"] and
            plan["authorizationRefs"] == request["authorizationRefs"], "RESTORE_PLAN_REQUEST_MISMATCH")
    require(plan["orderedChainPins"] and all(pin in plan["supportedVersionPins"] for pin in config["imagePins"]),
            "RESTORE_PLAN_VERSION_OR_CHAIN_MISSING")
    point = read_pin(plan["candidatePin"])
    trust.schemas.validate(point, "RepositoryPoint")
    allowed_reasons = (None, "REPOSITORY_CURRENT_RECOVERY_PASSED_REQUIRED")
    require(point["integrityState"] == "COMPLETE" and point["blockedReason"] in allowed_reasons and point["rehearsalEligible"] is True
            and point["commonRecoveryPoint"] == plan["recoveryPoint"], "RESTORE_POINT_NOT_ELIGIBLE")
    # Controlled authority is derived from independently selected current proof;
    # the immutable producer boolean is not an authorization decision.
    for pin in plan["orderedChainPins"] + plan["supportedVersionPins"] + plan["toolPins"]:
        verify_large_pin(pin, guard)
    require(plan["plannedWrites"] and all(write["targetIdentityPin"] == config["targetIdentityPin"]
            for write in plan["plannedWrites"]), "PLANNED_WRITE_TARGET_MISMATCH")
    read_pin(config["targetIdentityPin"])
    return plan


def check_controlled_preconditions(request, config, trust, runtime):
    if request["mode"] == "REHEARSAL":
        require(config["controlledPreconditions"] is None, "REHEARSAL_CONTROLLED_CONFIGURATION_REJECTED")
        return {"mode": "REHEARSAL", "sourceWritesAuthorized": False, "isolatedTarget": True}
    from w05_controlled_eligibility import admit_controlled
    admit_controlled(request, config, runtime.policy, trust, runtime.runner)
    preconditions = config["controlledPreconditions"]
    exact(preconditions, ("restoreKind", "protectionPointPin", "verificationReportPin", "sourceFencePin", "validUntil"),
          "CONTROLLED_PRECONDITIONS_REQUIRED")
    require(datetime.now(timezone.utc) < utc(preconditions["validUntil"]), "CONTROLLED_PRECONDITIONS_STALE")
    source = read_pin(config["sourceScopePin"])
    if preconditions["restoreKind"] == "REBUILD_EMPTY":
        require(preconditions["protectionPointPin"] is None and preconditions["verificationReportPin"] is None,
                "EMPTY_REBUILD_PROTECTION_MISMATCH")
    else:
        require(preconditions["restoreKind"] == "REPLACE_EXISTING" and preconditions["protectionPointPin"] is not None
                and preconditions["verificationReportPin"] is not None, "PROTECTION_POINT_REQUIRED")
        point = read_pin(preconditions["protectionPointPin"])
        trust.schemas.validate(point, "RepositoryPoint")
        require(point["integrityState"] == "COMPLETE" and point["blockedReason"] in
                (None, "REPOSITORY_CURRENT_RECOVERY_PASSED_REQUIRED") and point["rehearsalEligible"] is True,
                "PROTECTION_POINT_INCOMPLETE")
        report = read_pin(preconditions["verificationReportPin"])
        trust.schemas.validate(report, "RecoveryVerificationReport")
        require(report["verdict"] == "PASSED" and not report["invalidatedBy"] and
                preconditions["protectionPointPin"] in report["backupAndChainPins"] and
                report["sourceScopePin"] == config["sourceScopePin"], "PROTECTION_POINT_NOT_VERIFIED")
        # Fully consume the original verification bindings; existence is not enough.
        for key in ("backupAndChainPins", "toolAndVersionPins", "dataEvidencePins", "playwrightEvidencePins", "targetApprovalRefs"):
            require(report[key], "PROTECTION_REPORT_ORIGINALS_MISSING")
            for pin in report[key]:
                verify_large_pin(pin, runtime.runner.guard)
        for key in ("planPin", "targetIdentityPin", "restoreResultPin", "applicationStartPin"):
            read_pin(report[key])
        protection_plan = read_pin(report["planPin"])
        protection_restore = read_pin(report["restoreResultPin"])
        protection_start = read_pin(report["applicationStartPin"])
        trust.schemas.validate(protection_plan, "RestorePlan")
        trust.schemas.validate(protection_restore, "RestoreExecutionResult")
        trust.schemas.validate(protection_start, "ApplicationStartResult")
        require(protection_plan["candidatePin"] == preconditions["protectionPointPin"] and
                protection_plan["recoveryPoint"] == protection_restore["recoveryPoint"] == point["commonRecoveryPoint"] and
                protection_restore["planPin"] == report["planPin"] and protection_start["restoreResultPin"] == report["restoreResultPin"] and
                protection_restore["targetIdentityPin"] == protection_start["targetIdentityPin"] == report["targetIdentityPin"] and
                protection_restore["operationId"] == protection_start["operationId"] == protection_plan["operationId"] == report["operationId"] and
                protection_restore["restoreId"] == protection_start["restoreId"] == protection_plan["restoreId"] == report["restoreId"] and
                protection_restore["state"] == protection_start["state"] == "SUCCEEDED" and
                protection_restore["writeProtectionState"] == "ENFORCED", "PROTECTION_REPORT_BINDING_MISMATCH")
        original_w04_exits(protection_restore["originalInvocationPins"], runtime.runner.guard)
    from recovery_environment_fence import controlled_handoff
    handoff_ref, handoff, fence, terminals = controlled_handoff(request, config, runtime.policy, runtime.runner.guard, trust.schemas)
    require(preconditions["sourceFencePin"] is None or preconditions["sourceFencePin"] == handoff["sourceFencePin"],
            "CONFIGURED_SOURCE_FENCE_HANDOFF_MISMATCH")
    # W04 owns source stop/fence execution. W05 never restarts it and checks
    # live writer identities where the approved source is on this target host.
    target_identity = read_pin(config["targetIdentityPin"])
    observations = []
    if target_identity["machineId"] == source["machineId"]:
        for container_id in source["writerContainerIds"]:
            item = runtime.inspect(container_id)
            require(item["State"]["Running"] is False and item["State"]["Restarting"] is False and
                    item["HostConfig"]["RestartPolicy"]["Name"] == "no", "SOURCE_WRITER_NOT_STOPPED")
            observations.append({"containerId": container_id, "running": False, "restartPolicy": "no"})
    else:
        require(all(record.get("remoteTerminalConfirmed") is True for record in terminals), "REMOTE_SOURCE_FENCE_TERMINAL_UNKNOWN")
    return {"mode": "CONTROLLED_RESTORE", "restoreKind": preconditions["restoreKind"],
            "protectionPointPin": preconditions["protectionPointPin"], "verificationReportPin": preconditions["verificationReportPin"],
            "sourceFencePin": handoff["sourceFencePin"], "controlledFenceHandoffPin": handoff_ref,
            "sourceFencePointEvidencePin": handoff["sourceFencePointEvidencePin"], "sourceWriterObservations": observations,
            "retainedSourceResources": True}


def wait_health(runtime, service):
    deadline = min(runtime.runner.deadline, time.monotonic() + runtime.policy["startupTimeoutSeconds"])
    while True:
        runtime.runner.guard()
        require(time.monotonic() < deadline, "SERVICE_HEALTH_DEADLINE_EXCEEDED")
        if service["role"] == "mysql":
            observation = runtime.namespace_probe("mysql", {"protocol": "tcp", "port": 3306}, allow_not_ready=True)
            if observation["result"] and observation["result"].get("ready"):
                return runtime.mysql_tables()
        else:
            observation = runtime.health(service, allow_not_ready=True)
            if observation["result"] and observation["result"].get("ready"):
                return observation
        # Only explicit readiness observations retry; invocation errors do not.
        time.sleep(min(0.25, max(0, deadline - time.monotonic())))


def prepare_target(request, config, policy, plan, plan_pin, trust, runtime, private_dir):
    resources = runtime.native_preflight()
    mode = check_controlled_preconditions(request, config, trust, runtime)
    runtime.inventory_absent()
    images = runtime.prepare_images()
    network_id = runtime.create_network()
    side_effects = runtime.enforce_firewall()
    volumes = runtime.create_volumes()
    services, healthy = [], {}
    dependencies = {"mysql", "minio", "redis"}
    for service in config["services"]:
        if service["role"] in dependencies:
            created = runtime.create_service(service, private_dir)
            services.append(runtime.start_service(service, created["id"]))
            healthy[service["role"]] = wait_health(runtime, service)
    require(healthy["mysql"]["tableCount"] == 0, "TARGET_DATABASE_NOT_EMPTY")
    buckets = runtime.minio_buckets()
    require(buckets["result"]["bucketCount"] == 0, "TARGET_OBJECT_STORE_NOT_EMPTY")
    require(healthy["redis"]["result"]["keyCount"] == 0, "TARGET_REDIS_NOT_EMPTY")
    network = runtime.check_network(network_id, list(runtime.identities.values()))
    blocked = runtime.isolation_probes()
    # Applications are created only after W04 finishes the data restore.
    proof = {"schemaVersion": "RecoveryEnvironmentProof/v1", "operationId": request["operationId"],
             "targetId": config["targetId"], "targetIdentityPin": config["targetIdentityPin"], "planPin": plan_pin,
             "configurationRef": request["sourceOrTargetRef"], "recoveryPoint": plan["recoveryPoint"],
             "leaseRef": request["leaseRef"], "observedAt": utc_now(), "resources": resources, "images": images,
             "network": network, "volumes": volumes, "services": services, "health": healthy,
             "objectSpace": buckets, "blockedEndpointProbes": blocked, "sourceWritesPerformed": False}
    root = runtime.runner.root
    runtime.runner.guard()
    atomic_json(root / "resources-proof.json", proof)
    runtime.runner.guard()
    atomic_json(root / "isolation-proof.json", {"schemaVersion": "RecoveryIsolationProof/v1", "operationId": request["operationId"],
        "targetId": config["targetId"], "network": network, "volumes": volumes, "blockedEndpointProbes": blocked,
        "observedAt": utc_now(), "state": "ENFORCED"})
    runtime.runner.guard()
    atomic_json(root / "side-effect-isolation.json", {"schemaVersion": "RecoverySideEffectIsolation/v1",
        "operationId": request["operationId"], "targetIdentityPin": config["targetIdentityPin"], "state": "ENFORCED",
        "policyPin": request["policyPin"], "startupInventoryPins": policy["startupInventoryPins"],
        "firewall": side_effects, "observedAt": utc_now()})
    runtime.runner.guard()
    atomic_json(root / "mode-preconditions.json", {"schemaVersion": "RecoveryModePreconditions/v1", "operationId": request["operationId"],
        "targetIdentityPin": config["targetIdentityPin"], "planPin": plan_pin, "mode": mode, "observedAt": utc_now(),
        "emptyDatabase": True, "emptyObjectStore": True, "emptyRedis": True, "resourcesProofPin": pin_file(root / "resources-proof.json")})
    runtime.runner.guard()
    target = {"schemaVersion": "RecoveryTarget/v1", "targetId": config["targetId"], "targetIdentityPin": config["targetIdentityPin"],
              "resourcesProofPin": pin_file(root / "resources-proof.json"), "isolationProofPin": pin_file(root / "isolation-proof.json"),
              "versionPins": plan["supportedVersionPins"], "configurationPin": config["configurationPin"], "secretRefs": config["secretRefs"],
              "sideEffectIsolationPin": pin_file(root / "side-effect-isolation.json"), "leaseRef": request["leaseRef"],
              "modePreconditionsPin": pin_file(root / "mode-preconditions.json")}
    trust.schemas.validate(target, "RecoveryTarget")
    runtime.runner.guard()
    atomic_json(root / "recovery-target.json", target)
    artifact = pin_file(root / "recovery-target.json")
    runtime.runner.guard()
    return target, artifact


def retained_commit_failure(operation_dir, request, trust, guard):
    """Recover actual retained originals on an uncertain duplicate, never replay."""
    path = operation_dir / "terminal-commit-failure.json"
    if not path.exists():
        return None
    fault_pin = pin_file(path)
    fault = read_pin(fault_pin)
    require(fault.get("schemaVersion") == "RecoveryEnvironmentCommitFailure/v1", "COMMIT_FAILURE_RECORD_INVALID")
    result = fault["result"]
    trust.schemas.validate(result, "OperationResult")
    require(result["state"] == "TERMINAL_UNKNOWN" and all(result[key] == request[key] for key in
            ("operationId", "requestId", "action")), "COMMIT_FAILURE_REQUEST_MISMATCH")
    retained = {**result, "originalResultPins": [*result["originalResultPins"], fault_pin]}
    try:
        for pin in result["originalResultPins"]:
            verify_large_pin(pin, guard)
        guard()
    except (EnvironmentFailure, OSError, ValueError, KeyError, TypeError) as failure:
        cause = failure.code if isinstance(failure, EnvironmentFailure) else type(failure).__name__.upper()
        code = "COMMIT_ORIGINAL_VALIDATION_FAILED_" + cause
        retained = {**retained, "state": "TERMINAL_UNKNOWN", "data": None, "failureCode": code,
            "message": code + "; saved exit and selected references retained; original references are not verified."}
        raise EnvironmentFailure(code, unknown=True, result=retained) from None
    return retained


def confirmed_terminal(journal, evidence_root, target_key, trust, guard):
    """A terminal journal is prepared data until its final decision is published."""
    request_key = hashlib.sha256(journal["requestId"].encode("utf-8")).hexdigest()
    operation_dir = safe_path(evidence_root, directory=True) / ("request-" + request_key)
    intent_path = operation_dir / "commit-intent.json"
    confirmation_path = operation_dir / "commit-confirmed.json"
    result = None
    try:
        result = read_pin(journal["resultPin"])
        trust.schemas.validate(result, "OperationResult")
        require(intent_path.exists() and confirmation_path.exists(), "TERMINAL_COMMIT_CONFIRMATION_MISSING")
        intent_pin = pin_file(intent_path)
        intent = read_pin(intent_pin)
        confirmation = decode(read_bytes(str(confirmation_path)))
        require(intent["schemaVersion"] == "RecoveryEnvironmentCommitIntent/v1" and
                confirmation["schemaVersion"] == "RecoveryEnvironmentCommitConfirmation/v1" and
                confirmation["intentPin"] == intent_pin and confirmation["resultPin"] == journal["resultPin"] and
                all(intent[key] == confirmation[key] == journal[key] for key in
                    ("targetKey", "requestId", "requestSha256", "operationId", "action")) and
                intent["targetKey"] == target_key and digest(intent["request"]) == journal["requestSha256"] and
                all(result[key] == journal[key] for key in ("requestId", "operationId", "action")) and
                confirmation["state"] == journal["state"] == result["state"], "TERMINAL_COMMIT_CONFIRMATION_MISMATCH")
        original_request = intent["request"]
        trust.schemas.validate(original_request, "OperationRequest")
        for pin in result["originalResultPins"]:
            verify_large_pin(pin, guard)
        # Bind the historical decision to actual pinned authority and validity,
        # rather than letting a new request supply replacement qualification.
        if result["state"] == "SUCCEEDED":
            checked = utc(confirmation["checkedAt"])
            history_pin = next((pin for pin in result["originalResultPins"] if
                                Path(pin["path"]).name == "effect-history.json"), None)
            require(history_pin is not None, "TERMINAL_COMMIT_EFFECT_HISTORY_MISSING")
            history = read_pin(history_pin)
            require(history["schemaVersion"] == "RecoveryEnvironmentEffectHistory/v1" and
                    history["operationId"] == original_request["operationId"] and
                    history["operationProofConfirmed"] is True and history["state"] == "SUCCEEDED" and
                    history["admissionValidUntil"] == confirmation["admissionValidUntil"] and
                    history["deadlineMonotonic"] == confirmation["deadlineMonotonic"] and
                    not any(effect == "UNCONFIRMED" for effect in history["effects"].values()),
                    "TERMINAL_COMMIT_EFFECT_HISTORY_MISMATCH")
            require(confirmation["checkedMonotonic"] < confirmation["deadlineMonotonic"],
                    "TERMINAL_COMMIT_DEADLINE_INVALID")
            if original_request["mode"] == "CONTROLLED_RESTORE":
                require(confirmation["admissionValidUntil"] is not None and
                        checked < utc(confirmation["admissionValidUntil"]), "TERMINAL_COMMIT_QUALIFICATION_INVALID")
            require(original_request["authorizationRefs"], "WRITE_AUTHORIZATION_REQUIRED")
            permitted = False
            for pin in [*original_request["authorizationRefs"], original_request["leaseRef"]]:
                authority = (read_pin(pin) if pin == original_request["leaseRef"] else
                             trust.trusted(pin, "authorizationSha256s"))
                require(utc(authority["notBefore"]) <= checked < utc(authority["expiresAt"]) and
                        authority["operationId"] == original_request["operationId"] and
                        authority["targetId"] == intent["targetId"], "TERMINAL_COMMIT_AUTHORITY_INVALID")
                if pin == original_request["leaseRef"]:
                    require(authority["state"] == "HELD" and type(authority["fenceToken"]) is int and
                            authority["fenceToken"] > 0, "TERMINAL_COMMIT_LEASE_INVALID")
                else:
                    exact(authority, ("schemaVersion", "operationId", "targetId", "executorId", "mode", "actions",
                                      "notBefore", "expiresAt", "approved"), "AUTHORIZATION_INVALID")
                    require(authority["approved"] is True and authority["mode"] == original_request["mode"] and
                            authority["schemaVersion"] == "RecoveryEnvironmentAuthorization/v1" and
                            authority["executorId"] == trust.value["executorId"], "TERMINAL_COMMIT_AUTHORITY_INVALID")
                    require(type(authority["actions"]) is list, "AUTHORIZATION_ACTIONS_INVALID")
                    # Every exact grant must remain valid; permission is the
                    # union, matching admission's authorize(), without skipping
                    # later grants once this action has been covered.
                    permitted |= original_request["action"] in authority["actions"]
            require(permitted, "ACTION_NOT_AUTHORIZED")
        guard()
    except (EnvironmentFailure, OSError, ValueError, KeyError, TypeError) as failure:
        code = failure.code if isinstance(failure, EnvironmentFailure) else "TERMINAL_COMMIT_CONFIRMATION_UNREADABLE"
        retained = None if result is None else {**result, "state": "TERMINAL_UNKNOWN", "data": None,
            "failureCode": code, "message": code + "; saved exit and selected original references retained; terminal commit not confirmed."}
        raise EnvironmentFailure(code, unknown=True, result=retained) from None
    return result


def run_operation(request, trust, deadline, *, runtime_factory=NativeDocker):
    trust.schemas.validate(request, "OperationRequest")
    require(request["action"] in ("PREPARE_TARGET", "START_APPLICATION"), "W05_ACTION_UNSUPPORTED")
    required_keys = {"restorePlan"} if request["action"] == "PREPARE_TARGET" else {"restoreExecutionResult", "recoveryTarget"}
    require(set(request["inputPins"]) == required_keys and request["selectedPointPin"] is not None, "W05_INPUT_PINS_INVALID")
    config = trust.trusted(request["sourceOrTargetRef"], "targetConfigSha256")
    policy = trust.trusted(request["policyPin"], "policySha256")
    runner = None
    def guard():
        require(time.monotonic() < (deadline if runner is None else runner.deadline), "DEADLINE_EXCEEDED")
        trust.trusted(request["sourceOrTargetRef"], "targetConfigSha256")
        trust.trusted(request["policyPin"], "policySha256")
        authorize(request, trust, config["targetId"])
        require(time.monotonic() < (deadline if runner is None else runner.deadline), "DEADLINE_EXCEEDED")
    guard()
    validate_configuration(config, policy, trust, guard)
    if request["mode"] == "REHEARSAL":
        require(policy["controlledEligibilityPin"] is None and policy["controlledVerificationPolicyPin"] is None
                and policy["controlledIndependentOriginalPins"] == [], "REHEARSAL_CONTROLLED_POLICY_PROHIBITED")
    else:
        require(policy["controlledEligibilityPin"] is not None and policy["controlledVerificationPolicyPin"] is not None,
                "CONTROLLED_ADMISSION_PINS_REQUIRED")
    identity = read_pin(config["targetIdentityPin"])
    target_key = digest({"targetId": config["targetId"], "machineId": identity["machineId"], "dockerEngineId": identity["dockerEngineId"]})
    journal_root = safe_path(config["journalRoot"], directory=True)
    request_key = hashlib.sha256(request["requestId"].encode("utf-8")).hexdigest()
    journal_path = journal_root / ("request-" + request_key + ".json")
    target_journal_path = journal_root / ("target-" + target_key + ".json")
    pending_path = journal_root / ("target-" + target_key + ".commit-pending.json")
    fingerprint = digest(request)
    operation_base = safe_path(config["evidenceRoot"], directory=True) / ("request-" + request_key)
    intent_path = operation_base / "commit-intent.json"
    confirmation_path = operation_base / "commit-confirmed.json"
    fault_path = operation_base / "terminal-commit-failure.json"
    with exclusive_lock(journal_root / ("target-" + target_key + ".lock")):
        # Recheck after acquiring the local unique-executor lock.
        guard()
        if journal_path.exists():
            previous = decode(read_bytes(str(journal_path)))
            require(previous["requestSha256"] == fingerprint, "IDEMPOTENCY_CONTENT_MISMATCH")
            if previous["state"] == "RUNNING":
                try:
                    retained = retained_commit_failure(safe_path(config["evidenceRoot"], directory=True) /
                        ("request-" + request_key), request, trust, guard)
                except EnvironmentFailure as failure:
                    if failure.result is not None:
                        raise
                    raise EnvironmentFailure("PREVIOUS_INVOCATION_EVIDENCE_UNREADABLE_" + failure.code, unknown=True) from None
                except (OSError, ValueError, KeyError, TypeError):
                    raise EnvironmentFailure("PREVIOUS_INVOCATION_EVIDENCE_UNREADABLE", unknown=True) from None
                raise EnvironmentFailure("PREVIOUS_INVOCATION_TERMINAL_UNKNOWN", unknown=True, result=retained)
            result = None
            try:
                result = read_pin(previous["resultPin"])
                trust.schemas.validate(result, "OperationResult")
                for pin in result["originalResultPins"]:
                    verify_large_pin(pin, guard)
                if result["state"] == "SUCCEEDED" and request["mode"] == "CONTROLLED_RESTORE":
                    history_pin = next((pin for pin in result["originalResultPins"] if
                                        Path(pin["path"]).name == "effect-history.json"), None)
                    require(history_pin is not None, "CONTROLLED_TERMINAL_VALIDITY_MISSING")
                    history = read_pin(history_pin)
                    require(history["schemaVersion"] == "RecoveryEnvironmentEffectHistory/v1" and
                            history["operationId"] == request["operationId"] and
                            history["admissionValidUntil"] is not None, "CONTROLLED_TERMINAL_VALIDITY_MISSING")
                    remaining_validity = (utc(history["admissionValidUntil"]) - datetime.now(timezone.utc)).total_seconds()
                    require(remaining_validity > 0, "CONTROLLED_TERMINAL_VALIDITY_EXPIRED")
                    deadline = min(deadline, time.monotonic() + remaining_validity)
                    guard()
                require(not pending_path.exists() and not fault_path.exists(), "TERMINAL_COMMIT_NOT_CONFIRMED")
                previous_target = decode(read_bytes(str(target_journal_path)))
                require(all(previous.get(key) == previous_target.get(key) == value for key, value in
                            {"targetKey": target_key, "requestId": request["requestId"], "requestSha256": fingerprint,
                             "operationId": request["operationId"], "action": request["action"],
                             "state": result["state"], "resultPin": previous["resultPin"]}.items()) and
                        all(result[key] == request[key] for key in ("requestId", "operationId", "action")) and
                        result["state"] in ("SUCCEEDED", "FAILED_RETAINED", "TERMINAL_UNKNOWN"),
                        "TARGET_TERMINAL_COMMIT_MISMATCH")
                guard()
                confirmed_terminal(previous, config["evidenceRoot"], target_key, trust, guard)
                guard()
            except (EnvironmentFailure, OSError, ValueError, KeyError, TypeError) as failure:
                code = failure.code if isinstance(failure, EnvironmentFailure) else "TERMINAL_COMMIT_UNREADABLE"
                retained = None if result is None else {**result, "state": "TERMINAL_UNKNOWN", "data": None,
                    "failureCode": code, "message": code}
                if pending_path.exists() or fault_path.exists():
                    try:
                        actual = retained_commit_failure(safe_path(config["evidenceRoot"], directory=True) /
                            ("request-" + request_key), request, trust, guard)
                        if actual is not None:
                            retained = actual
                    except EnvironmentFailure as failure:
                        if failure.result is not None:
                            retained, code = failure.result, failure.code
                        else:
                            code = "TERMINAL_COMMIT_EVIDENCE_UNREADABLE_" + failure.code
                            if retained is not None:
                                retained = {**retained, "failureCode": code, "message": code +
                                    "; selected original references are not verified."}
                    except (OSError, ValueError, KeyError, TypeError):
                        code = "TERMINAL_COMMIT_EVIDENCE_UNREADABLE"
                        if retained is not None:
                            retained = {**retained, "failureCode": code, "message": code}
                raise EnvironmentFailure(code, unknown=True, result=retained) from None
            return result
        if pending_path.exists():
            raise EnvironmentFailure("TARGET_TERMINAL_COMMIT_NOT_CONFIRMED", unknown=True)
        if target_journal_path.exists():
            previous_target = decode(read_bytes(str(target_journal_path)))
            require(previous_target["targetKey"] == target_key, "TARGET_JOURNAL_IDENTITY_MISMATCH")
            if previous_target["state"] in ("RUNNING", "TERMINAL_UNKNOWN"):
                raise EnvironmentFailure("TARGET_PREVIOUS_EFFECT_TERMINAL_UNKNOWN", unknown=True)
            confirmed_terminal(previous_target, config["evidenceRoot"], target_key, trust, guard)
        # Include journals predating the target-level gate. An old uncertain
        # request may not be bypassed by changing its requestId.
        for previous_path in journal_root.glob("request-*.json"):
            previous_request = decode(read_bytes(str(previous_path)))
            if "targetKey" not in previous_request:
                raise EnvironmentFailure("LEGACY_UNCERTAIN_TARGET_IDENTITY_REQUIRED", unknown=True)
            prior_target = previous_request["targetKey"]
            if type(prior_target) is not str or re.fullmatch(r"[0-9a-f]{64}", prior_target) is None:
                raise EnvironmentFailure("LEGACY_JOURNAL_TARGET_IDENTITY_INVALID", unknown=True)
            if previous_request["state"] in ("RUNNING", "TERMINAL_UNKNOWN"):
                # Target uncertainty rejects before requestId-dependent proof
                # lookup; a missing requestId cannot bypass this durable gate.
                if prior_target == target_key:
                    raise EnvironmentFailure("TARGET_PREVIOUS_EFFECT_TERMINAL_UNKNOWN", unknown=True)
                continue
            if prior_target == target_key:
                prior_key = hashlib.sha256(previous_request["requestId"].encode("utf-8")).hexdigest()
                prior_fault = safe_path(config["evidenceRoot"], directory=True) / ("request-" + prior_key) / "terminal-commit-failure.json"
                if prior_fault.exists():
                    raise EnvironmentFailure("TARGET_TERMINAL_COMMIT_NOT_CONFIRMED", unknown=True)
                confirmed_terminal(previous_request, config["evidenceRoot"], target_key, trust, guard)
        operation_dir = safe_path(config["evidenceRoot"], directory=True) / ("request-" + request_key)
        private_dir = safe_path(config["privateRoot"], directory=True) / ("request-" + request_key)
        require(not operation_dir.exists() and not private_dir.exists(), "UNJOURNALED_REQUEST_ARTIFACTS_EXIST")
        operation_dir.mkdir(mode=0o700)
        private_dir.mkdir(mode=0o700)
        started = utc_now()
        target_journal = {"schemaVersion": "RecoveryEnvironmentTargetJournal/v1", "targetKey": target_key,
            "targetIdentityPin": config["targetIdentityPin"], "requestId": request["requestId"],
            "requestSha256": fingerprint, "operationId": request["operationId"], "action": request["action"],
            "state": "RUNNING", "startedAt": started, "resultPin": None}
        # Durable before dispatch; retained on every incomplete terminal write,
        # Pin or directory-fsync. Its deletion is deliberately not a durability
        # dependency: reappearance after a crash can only block, never admit.
        atomic_json(pending_path, target_journal)
        atomic_json(intent_path, {"schemaVersion": "RecoveryEnvironmentCommitIntent/v1",
            **{key: target_journal[key] for key in ("targetKey", "requestId", "requestSha256", "operationId", "action")},
            "targetId": config["targetId"], "request": request, "startedAt": started})
        atomic_json(target_journal_path, target_journal)
        atomic_json(journal_path, {"schemaVersion": "RecoveryEnvironmentJournal/v1", "requestId": request["requestId"],
            "targetKey": target_key, "requestSha256": fingerprint, "operationId": request["operationId"], "action": request["action"], "state": "RUNNING",
            "startedAt": started, "resultPin": None})
        runner = CommandRunner(operation_dir, deadline, guard)
        runtime = runtime_factory(config, policy, runner, request["operationId"])
        data = None
        original_pins = []
        failure_code = None
        state = "SUCCEEDED"
        try:
            if request["action"] == "PREPARE_TARGET":
                plan_pin = request["inputPins"]["restorePlan"]
                plan = validate_plan(read_pin(plan_pin), plan_pin, request, config, trust, guard)
                data, artifact = prepare_target(request, config, policy, plan, plan_pin, trust, runtime, private_dir)
            else:
                from recovery_application import start_application
                data, artifact = start_application(request, config, policy, trust, runtime, private_dir)
            original_pins.append(artifact)
            require(not any(value == "UNCONFIRMED" for value in runner.effects.values()), "NATIVE_EFFECT_READBACK_UNCONFIRMED")
            guard()
            runner.operation_proof_confirmed = True
            guard()
        except EnvironmentFailure as failure:
            state = "TERMINAL_UNKNOWN" if failure.unknown or runner.unconfirmed_effects() else "FAILED_RETAINED"
            failure_code = failure.code
        except (OSError, ValueError, KeyError, TypeError, KeyboardInterrupt) as failure:
            state = "TERMINAL_UNKNOWN" if isinstance(failure, KeyboardInterrupt) or runner.unconfirmed_effects() else "FAILED_RETAINED"
            failure_code = "ENVIRONMENT_" + type(failure).__name__.upper()
        result = {"schemaVersion": "backup-restore-operation-result/v1", "operationId": request["operationId"],
                  "requestId": request["requestId"], "action": request["action"], "state": state, "failureCode": failure_code,
                  "message": "Target prepared; data recovery and business acceptance are separate." if state == "SUCCEEDED" and
                  request["action"] == "PREPARE_TARGET" else "Application started; independent business acceptance required." if state == "SUCCEEDED"
                  else failure_code, "data": data if state == "SUCCEEDED" else None,
                  "originalResultPins": [*runner.pins, *original_pins], "startedAt": started, "finishedAt": utc_now(),
                  "actualExitCode": runner.last_exit}
        result_path = operation_dir / "operation-result.json"
        stage = "EFFECT_HISTORY"
        def terminal_guard():
            # Once a failure is established, bounded failure retention remains
            # necessary after expiry. No success proof/commit can cross it.
            if state == "SUCCEEDED":
                runner.guard()
        try:
            terminal_guard()
            history_path = operation_dir / "effect-history.json"
            atomic_json(history_path, {"schemaVersion": "RecoveryEnvironmentEffectHistory/v1", "operationId": request["operationId"],
                "effects": runner.effects, "operationProofConfirmed": runner.operation_proof_confirmed,
                "originalInvocationPins": runner.pins, "state": state, "observedAt": utc_now(),
                "deadlineMonotonic": runner.deadline, "admissionValidUntil": runner.admission_valid_until})
            result["originalResultPins"].append(pin_file(history_path))
            terminal_guard()
            stage = "RESULT"
            trust.schemas.validate(result, "OperationResult")
            atomic_json(result_path, result)
            terminal_guard()
            stage = "RESULT_PIN"
            result_pin = pin_file(result_path)
            terminal_guard()
            terminal = {**target_journal, "state": state, "resultPin": result_pin}
            stage = "REQUEST_JOURNAL"
            atomic_json(journal_path, {**terminal, "schemaVersion": "RecoveryEnvironmentJournal/v1"})
            terminal_guard()
            stage = "TARGET_JOURNAL"
            atomic_json(target_journal_path, terminal)
            terminal_guard()
            stage = "COMMIT_READBACK"
            require(read_pin(result_pin) == result and decode(read_bytes(str(journal_path))) ==
                    {**terminal, "schemaVersion": "RecoveryEnvironmentJournal/v1"} and
                    decode(read_bytes(str(target_journal_path))) == terminal, "TERMINAL_COMMIT_READBACK_MISMATCH")
            terminal_guard()
            stage = "COMMIT_RELEASE"
            pending_path.unlink()
            terminal_guard()
            stage = "COMMIT_PREPARE"
            ready_path = operation_dir / "commit-ready.json"
            confirmation = {"schemaVersion": "RecoveryEnvironmentCommitConfirmation/v1",
                **{key: terminal[key] for key in ("targetKey", "requestId", "requestSha256", "operationId", "action", "state", "resultPin")},
                "intentPin": pin_file(intent_path), "checkedAt": utc_now(), "checkedMonotonic": time.monotonic(),
                "deadlineMonotonic": runner.deadline, "admissionValidUntil": runner.admission_valid_until}
            atomic_json(ready_path, confirmation)
            terminal_guard()
            require(decode(read_bytes(str(ready_path))) == confirmation, "TERMINAL_COMMIT_PREPARATION_MISMATCH")
            terminal_guard()
            stage = "COMMIT_PUBLISH"
            # Linearization point: only this atomic rename publishes a decision.
            # All fallible evidence writes/readbacks and the final shared guard
            # precede it. No post-publication expiry check can revoke a commit.
            # Prepared bytes are fsynced already. A lost rename after a crash
            # leaves the permanent intent without confirmation, which blocks.
            os.rename(ready_path, confirmation_path)
        except (EnvironmentFailure, OSError, ValueError, KeyError, TypeError, KeyboardInterrupt) as failure:
            # Preserve prior UNKNOWN code and every available real original.
            code = failure_code if state == "TERMINAL_UNKNOWN" and failure_code else "TERMINAL_COMMIT_" + stage + "_FAILED"
            cause = failure.code if isinstance(failure, EnvironmentFailure) else type(failure).__name__.upper()
            result = {**result, "state": "TERMINAL_UNKNOWN", "failureCode": code, "message": code,
                      "data": None, "finishedAt": utc_now()}
            result["message"] = code + "; cause=" + cause + "; terminal commit not confirmed."
            if not pending_path.exists():
                try:
                    atomic_json(pending_path, {**target_journal, "state": "TERMINAL_UNKNOWN"})
                except (EnvironmentFailure, OSError, ValueError, KeyError, TypeError):
                    result["message"] += " Pending intent could not be restored."
            # The pending intent remains authoritative even when no further
            # storage is available. Failure recording is bounded and explicit.
            fault = {"schemaVersion": "RecoveryEnvironmentCommitFailure/v1", "stage": stage,
                     "failureType": type(failure).__name__, "result": result,
                     "effectHistory": runner.effects, "targetKey": target_key,
                     "causeCode": cause, "deadlineMonotonic": runner.deadline,
                     "admissionValidUntil": runner.admission_valid_until}
            fault_path = operation_dir / "terminal-commit-failure.json"
            try:
                atomic_json(fault_path, fault)
                result["originalResultPins"].append(pin_file(fault_path))
            except (EnvironmentFailure, OSError, ValueError, KeyError, TypeError):
                result["message"] += " Commit failure evidence could not be persisted; pending intent " + (
                    "retained." if pending_path.exists() else "not persisted.")
        return result
