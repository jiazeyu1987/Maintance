"""Read-only identity proof on the explicitly selected native Docker host."""
import ipaddress
import datetime as dt
import os
from pathlib import Path
import subprocess
from urllib.parse import urlsplit

from core import canonical, fields, json_pin, need, parse, read_pin, same, now, integer, pins, pin_key, timestamp

BINDING_FIELDS = ("schemaVersion targetIdentityPin sourceScopePin environmentConfigPin resourcesProofPin "
                  "dockerPin machineIdPath role endpointUrl applicationStartPin")
IDENTITY_PROFILE = "w05-native-readonly-docker-inspect-v1"
IDENTITY_FIELDS = ("schemaVersion rehearsalId operationId restoreId targetIdentityPin sourceScopePin "
    "environmentConfigPin resourcesProofPin applicationStartPin role endpointUrl dockerPin probeSourcePin "
    "probeRuntimeProofPin infoResultPin inspectResultPin networkResultPin invocationPins machineId dockerEngineId "
    "containerId imageId networkId endpointId ipAddress issuedAt expiresAt")
INFO_FORMAT = '{"ID":{{json .ID}}}'
INSPECT_FORMAT = ('[{"Id":{{json .Id}},"Image":{{json .Image}},"Name":{{json .Name}},'
    '"State":{"Running":{{json .State.Running}}},"Config":{"Labels":{'
    '"intruoyi.recovery.target":{{json (index .Config.Labels "intruoyi.recovery.target")}},'
    '"intruoyi.recovery.operation":{{json (index .Config.Labels "intruoyi.recovery.operation")}}}},'
    '"NetworkSettings":{"Networks":{{json .NetworkSettings.Networks}}}}]')
NETWORK_FORMAT = '[{"Id":{{json .Id}},"Containers":{{json .Containers}}}]'


def native_identity_argv(docker_path, verb, container_id, network_id):
    """Exact safe Docker-native JSON projection; stdout is retained without rewriting."""
    arguments = {"info": ["info", "--format", INFO_FORMAT],
                 "inspect": ["inspect", "--format", INSPECT_FORMAT, container_id],
                 "network": ["network", "inspect", "--format", NETWORK_FORMAT, network_id]}
    need(verb in arguments, "SERVICE_NATIVE_READONLY_OPERATION")
    return [docker_path, "--host", "unix:///var/run/docker.sock", *arguments[verb]]


def service_binding(pin, reader=json_pin):
    binding = reader(pin)
    selected_v2 = binding.get("schemaVersion") == "RecoveryServiceBinding/v2"
    fields(binding, BINDING_FIELDS + (" identityProfile nativeIdentityProofPin" if selected_v2 else ""),
           "RecoveryServiceBinding/v2" if selected_v2 else "RecoveryServiceBinding/v1")
    if selected_v2:
        need(binding["identityProfile"] == IDENTITY_PROFILE, "SERVICE_NATIVE_PROFILE_UNSUPPORTED")
    target = reader(binding["targetIdentityPin"])
    config = reader(binding["environmentConfigPin"])
    proof = reader(binding["resourcesProofPin"])
    source = reader(binding["sourceScopePin"])
    same(config["targetIdentityPin"], binding["targetIdentityPin"], "SERVICE_TARGET_CONFIG_MISMATCH")
    same(config["sourceScopePin"], binding["sourceScopePin"], "SERVICE_SOURCE_SCOPE_MISMATCH")
    same(proof["targetIdentityPin"], binding["targetIdentityPin"], "SERVICE_PROOF_TARGET_MISMATCH")
    same(proof["configurationRef"], binding["environmentConfigPin"], "SERVICE_PROOF_CONFIG_MISMATCH")
    same(config["dockerPin"], binding["dockerPin"], "SERVICE_DOCKER_EXECUTABLE_MISMATCH")
    need(target["schemaVersion"] == "RecoveryTargetIdentity/v1" and
         proof["schemaVersion"] == "RecoveryEnvironmentProof/v1" and
         config["schemaVersion"] == "RecoveryEnvironmentConfig/v1" and
         source["schemaVersion"] == "RecoverySourceScope/v1" and
         proof["resources"]["machineId"] == target["machineId"] and
         proof["resources"]["dockerEngineId"] == target["dockerEngineId"], "SERVICE_NATIVE_HOST_UNBOUND")
    service_configs = [item for item in config["services"] if item["role"] == binding["role"]]
    need(len(service_configs) == 1, "SERVICE_ROLE_UNBOUND")
    service_config = service_configs[0]
    services = [item for item in proof["services"] if item["name"] == "/" + service_config["name"]]
    need(len(services) == 1, "SERVICE_RESOURCE_UNBOUND")
    service = services[0]
    need(service["id"] not in source["containerIds"] and service["name"].lstrip("/") not in source["containerNames"],
         "SOURCE_OBJECT_SERVICE_REJECTED")
    network_id = proof["network"]["networkId"]
    networks = [value for value in service["networks"].values() if value["NetworkID"] == network_id]
    need(len(networks) == 1, "SERVICE_NETWORK_UNBOUND")
    application = reader(binding["applicationStartPin"])
    need(application["schemaVersion"] == "ApplicationStartResult/v1" and application["state"] == "SUCCEEDED" and
         application["operationId"] == proof["operationId"] and application["targetIdentityPin"] == binding["targetIdentityPin"],
         "SERVICE_APPLICATION_UNBOUND")
    launches = [record for ref in application["originalStartResultPins"]
                if (record := reader(ref)).get("schemaVersion") == "RecoveryApplicationLaunch/v1"]
    need(len(launches) == 1 and launches[0]["network"]["networkId"] == network_id, "SERVICE_CURRENT_NETWORK_UNBOUND")
    endpoint_record = launches[0]["network"]["containers"][service["id"]]
    need(endpoint_record["Name"] == service["name"].lstrip("/"), "SERVICE_CURRENT_CONTAINER_UNBOUND")
    network = {"NetworkID": network_id, "EndpointID": endpoint_record["EndpointID"],
               "IPAddress": endpoint_record["IPv4Address"].split("/")[0]}
    endpoint = urlsplit(binding["endpointUrl"])
    need(endpoint.scheme in ("http", "https", "redis", "amqp", "amqps") and endpoint.hostname and
         not endpoint.username and not endpoint.password and not endpoint.query and not endpoint.fragment and
         endpoint.path in ("", "/"), "SERVICE_ENDPOINT_INVALID")
    try:
        address = str(ipaddress.ip_address(endpoint.hostname))
    except ValueError:
        need(False, "SERVICE_LITERAL_IP_REQUIRED")
    configured_port = 6379 if binding["role"] == "redis" else service_config["health"]["port"]
    need(address == network["IPAddress"] and address not in source["endpointHosts"] and
         endpoint.port == configured_port, "SERVICE_ENDPOINT_TARGET_MISMATCH")
    return binding, target, proof, service, network


def native_service_identity(binding_pin, boundary, expected, source_pins, maximum_age_ms, *, identity_proof_pin=None):
    """Read signed exact W05 originals; this path has no Docker/socket/process execution."""
    from evidence import native_process_result, native_runtime_metadata, NATIVE_PROCESS_PROFILE
    from lab_boundary import REHEARSAL
    need(boundary is not None, "NATIVE_PROFILE_LAB_ONLY")
    boundary.recheck()
    binding, target, resources, service, network = service_binding(binding_pin, boundary.original)
    need(binding["schemaVersion"] == "RecoveryServiceBinding/v2" and binding["identityProfile"] == IDENTITY_PROFILE,
         "SERVICE_NATIVE_PROFILE_REQUIRED")
    proof_pin = binding["nativeIdentityProofPin"] if identity_proof_pin is None else identity_proof_pin
    proof = boundary.signed(proof_pin, boundary.admission["authorityKeyPin"])
    fields(proof, IDENTITY_FIELDS, "RecoveryNativeServiceIdentity/v1")
    need(proof["rehearsalId"] == REHEARSAL and proof["operationId"] == expected["operationId"] == boundary.operation_id
         and proof["restoreId"] == expected["restoreId"] and proof["role"] == binding["role"]
         and proof["endpointUrl"] == binding["endpointUrl"], "SERVICE_NATIVE_CURRENT_OPERATION")
    for name in ("targetIdentityPin", "sourceScopePin", "environmentConfigPin", "resourcesProofPin", "applicationStartPin", "dockerPin"):
        same(proof[name], binding[name], "SERVICE_NATIVE_BINDING_MISMATCH")
    same(binding["targetIdentityPin"], expected["targetIdentityPin"], "SERVICE_NATIVE_CURRENT_TARGET")
    same(binding["targetIdentityPin"], boundary.admission["targetIdentityPin"], "SERVICE_NATIVE_ADMITTED_TARGET")
    same(binding["sourceScopePin"], expected["sourceScopePin"], "SERVICE_NATIVE_CURRENT_SOURCE")
    same(binding["environmentConfigPin"], expected["environmentConfigPin"], "SERVICE_NATIVE_CURRENT_CONFIG")
    same(binding["applicationStartPin"], expected["applicationStartPin"], "SERVICE_NATIVE_CURRENT_START")
    need(resources["operationId"] == proof["operationId"], "SERVICE_NATIVE_RESOURCE_OPERATION")
    current = dt.datetime.now(dt.timezone.utc)
    issued, expires = timestamp(proof["issuedAt"]), timestamp(proof["expiresAt"])
    need(0 <= (current-issued).total_seconds()*1000 <= integer(maximum_age_ms, 1) and issued <= current < expires,
         "SERVICE_NATIVE_IDENTITY_STALE", "STALE")
    boundary.window(proof["expiresAt"])
    runtime, _ = native_runtime_metadata(boundary, proof["probeRuntimeProofPin"], "EXECUTOR", maximum_age_ms)
    need(timestamp(runtime["issuedAt"]) <= issued < expires <= timestamp(runtime["expiresAt"]), "SERVICE_NATIVE_RUNTIME_WINDOW")
    need({pin_key(proof["probeSourcePin"]), pin_key(proof["dockerPin"])} <= set(pins(source_pins)),
         "SERVICE_NATIVE_PROBE_SOURCE_UNBOUND")
    references = [proof[name] for name in ("infoResultPin", "inspectResultPin", "networkResultPin")]
    pins(references)
    need(len(pins(proof["invocationPins"])) == 3, "SERVICE_NATIVE_INVOCATION_COVERAGE")
    results = {pin_key(value): name for name, value in zip(("info", "inspect", "network"), references)}
    seen, intervals = set(), []
    for reference in proof["invocationPins"]:
        call = boundary.original(reference)
        fields(call, "schemaVersion operationId restoreId targetIdentityPin recoveryPoint stage state actualExitCode "
               "startedAt finishedAt sourcePins resultPin commandId command argv cwd processProfile processResultPin",
               "RecoveryInvocation/v1")
        need(call["processProfile"] == NATIVE_PROCESS_PROFILE and call["operationId"] == expected["operationId"] and
             call["restoreId"] == expected["restoreId"] and call["recoveryPoint"] == expected["recoveryPoint"],
             "SERVICE_NATIVE_INVOCATION_BINDING")
        same(call["targetIdentityPin"], expected["targetIdentityPin"], "SERVICE_NATIVE_INVOCATION_TARGET")
        selected = pin_key(call["resultPin"])
        need(selected in results and selected not in seen, "SERVICE_NATIVE_INVOCATION_RESULT_COVERAGE")
        seen.add(selected)
        process = native_process_result(boundary, call["processResultPin"], call, source_pins, maximum_age_ms,
            role="EXECUTOR", selected_installation=False, runtime_proof_pin=proof["probeRuntimeProofPin"])
        need(pin_key(proof["probeSourcePin"]) in set(pins(call["sourcePins"])), "SERVICE_NATIVE_PROBE_NOT_INVOKED")
        # The independent native supervisor captures the literal Docker child argv.
        # No Python wrapper, shell, socket or command is executed by this consumer.
        verb = results[selected]
        need(process["argv"] == native_identity_argv(proof["dockerPin"]["path"], verb, service["id"], network["NetworkID"]),
             "SERVICE_NATIVE_READONLY_ARGV")
        need(process["stdoutPin"]["sha256"] == call["resultPin"]["sha256"] and
             process["stdoutPin"]["bytes"] == call["resultPin"]["bytes"] and process["stderrPin"]["bytes"] == 0,
             "SERVICE_NATIVE_RAW_STDOUT_MISMATCH")
        need(timestamp(runtime["issuedAt"]) <= timestamp(call["startedAt"]) < timestamp(call["finishedAt"]) <= issued,
             "SERVICE_NATIVE_INVOCATION_TIME")
        intervals.append((timestamp(call["startedAt"]), timestamp(call["finishedAt"]), call["finishedAt"]))
    info, inspected, networks = [boundary.original(reference) for reference in references]
    fields(info, "ID")
    need(info["ID"] == target["dockerEngineId"], "SERVICE_DOCKER_ENGINE_MISMATCH")
    need(type(inspected) is list and len(inspected) == 1 and type(networks) is list and len(networks) == 1,
         "SERVICE_NATIVE_RAW_RESULT_SHAPE")
    actual, actual_network_record = inspected[0], networks[0]
    fields(actual, "Id Image Name State Config NetworkSettings")
    fields(actual["State"], "Running")
    fields(actual["Config"], "Labels")
    fields(actual["Config"]["Labels"], "intruoyi.recovery.target intruoyi.recovery.operation")
    fields(actual["NetworkSettings"], "Networks")
    fields(actual_network_record, "Id Containers")
    need(actual["Id"] == service["id"] and actual["Image"] == service["imageId"] and
         actual["Name"] == service["name"] and actual["State"]["Running"] is True and
         actual["Config"]["Labels"]["intruoyi.recovery.target"] == target["targetId"] and
         actual["Config"]["Labels"]["intruoyi.recovery.operation"] == expected["operationId"],
         "SERVICE_INSTANCE_IDENTITY_MISMATCH", "STALE")
    selected_networks = [value for value in actual["NetworkSettings"]["Networks"].values()
                         if value["NetworkID"] == network["NetworkID"]]
    need(len(selected_networks) == 1 and all(selected_networks[0][key] == network[key]
         for key in ("NetworkID", "EndpointID", "IPAddress")), "SERVICE_NETWORK_IDENTITY_MISMATCH", "STALE")
    need(actual_network_record["Id"] == network["NetworkID"], "SERVICE_NATIVE_NETWORK_ID")
    endpoint = actual_network_record["Containers"][service["id"]]
    need(endpoint["Name"] == service["name"].lstrip("/") and endpoint["EndpointID"] == network["EndpointID"]
         and endpoint["IPv4Address"].split("/")[0] == network["IPAddress"], "SERVICE_NATIVE_NETWORK_ENDPOINT", "STALE")
    expected_identity = dict(machineId=target["machineId"], dockerEngineId=target["dockerEngineId"],
        containerId=service["id"], imageId=service["imageId"], networkId=network["NetworkID"],
        endpointId=network["EndpointID"], ipAddress=network["IPAddress"])
    need(all(proof[name] == value for name, value in expected_identity.items()), "SERVICE_NATIVE_IDENTITY_MISMATCH", "STALE")
    boundary.recheck()
    return {"schemaVersion": "RecoveryServiceObservation/v1", "bindingPin": binding_pin,
            "targetIdentityPin": binding["targetIdentityPin"], "operationId": proof["operationId"],
            "role": binding["role"], "endpointUrl": binding["endpointUrl"], **expected_identity,
            "observedAt": max(intervals, key=lambda value: value[1])[2]}


def probe_service(pin, deadline, *, collection_id=None, sequence=None, phase=None):
    selection = json_pin(pin, deadline)
    if selection.get("schemaVersion") == "RecoveryServiceBinding/v2":
        selected = getattr(deadline, "native_service_context", None)
        need(type(selected) is dict, "SERVICE_NATIVE_CALLER_SELECTION_REQUIRED")
        client = selected.get("client")
        need(client is not None and collection_id is not None and sequence is not None and phase is not None,
             "SERVICE_NATIVE_FRESH_CLIENT_REQUIRED")
        return client.observe(pin, collection_id=collection_id, sequence=sequence, phase=phase)
    binding, target, proof, expected, network = service_binding(pin, lambda ref: json_pin(ref, deadline))
    need(os.name == "posix", "SERVICE_NATIVE_LINUX_REQUIRED")
    machine = Path(binding["machineIdPath"])
    need(machine.is_absolute(), "SERVICE_MACHINE_ID_PATH_REQUIRED")
    deadline.remaining()
    observed_machine = machine.read_text(encoding="ascii").strip()
    need(observed_machine == target["machineId"], "SERVICE_MACHINE_ID_MISMATCH")
    read_pin(binding["dockerPin"], deadline, content=False)

    def docker(arguments):
        deadline.remaining()
        process = subprocess.run([binding["dockerPin"]["path"], "--host", "unix:///var/run/docker.sock", *arguments],
                                 capture_output=True, timeout=deadline.remaining(), check=False,
                                 env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C", "LANG": "C"})
        need(process.returncode == 0 and not process.stderr, "SERVICE_IDENTITY_PROBE_FAILED")
        need(len(process.stdout) <= 16 * 1024 * 1024, "SERVICE_IDENTITY_PROBE_LIMIT")
        deadline.remaining()
        return parse(process.stdout)
    info = docker(["info", "--format", "{{json .}}"])
    need(info["ID"] == target["dockerEngineId"], "SERVICE_DOCKER_ENGINE_MISMATCH")
    inspected = docker(["inspect", expected["id"]])
    need(type(inspected) is list and len(inspected) == 1, "SERVICE_INSPECT_AMBIGUOUS")
    actual = inspected[0]
    need(actual["Id"] == expected["id"] and actual["Image"] == expected["imageId"] and
         actual["Name"] == expected["name"] and actual["State"]["Running"] is True and
         actual["Config"]["Labels"]["intruoyi.recovery.target"] == target["targetId"] and
         actual["Config"]["Labels"]["intruoyi.recovery.operation"] == proof["operationId"],
         "SERVICE_INSTANCE_IDENTITY_MISMATCH")
    actual_networks = [item for item in actual["NetworkSettings"]["Networks"].values()
                       if item["NetworkID"] == proof["network"]["networkId"]]
    need(len(actual_networks) == 1, "SERVICE_NETWORK_CHANGED")
    actual_network = actual_networks[0]
    need(all(actual_network[key] == network[key] for key in ("NetworkID", "EndpointID", "IPAddress")),
         "SERVICE_NETWORK_IDENTITY_MISMATCH")
    read_pin(binding["dockerPin"], deadline, content=False)
    return {"schemaVersion": "RecoveryServiceObservation/v1", "bindingPin": pin,
            "targetIdentityPin": binding["targetIdentityPin"], "operationId": proof["operationId"],
            "role": binding["role"], "endpointUrl": binding["endpointUrl"], "machineId": observed_machine,
            "dockerEngineId": info["ID"], "containerId": actual["Id"], "imageId": actual["Image"],
            "networkId": actual_network["NetworkID"], "endpointId": actual_network["EndpointID"],
            "ipAddress": actual_network["IPAddress"], "observedAt": now()}


def verify_service_observation(context, observation, binding_pin, role):
    binding, target, proof, service, network = service_binding(binding_pin, context.record)
    if binding["schemaVersion"] == "RecoveryServiceBinding/v2":
        from native_observe import verify_collection_evidence
        observation = verify_collection_evidence(context, observation, binding_pin)
    fields(observation, "schemaVersion bindingPin targetIdentityPin operationId role endpointUrl machineId "
           "dockerEngineId containerId imageId networkId endpointId ipAddress observedAt", "RecoveryServiceObservation/v1")
    same(observation["bindingPin"], binding_pin, "OBSERVED_SERVICE_BINDING_MISMATCH")
    same(observation["targetIdentityPin"], context.target_pin, "SERVICE_TARGET_MISMATCH")
    same(binding["sourceScopePin"], context.source_pin, "BUSINESS_SOURCE_SCOPE_MISMATCH")
    same(binding["environmentConfigPin"], context.request["sourceOrTargetRef"], "SERVICE_TARGET_CONFIG_MISMATCH")
    same(binding["applicationStartPin"], context.request["inputPins"]["applicationStartResult"], "SERVICE_APPLICATION_MISMATCH")
    need(observation["role"] == binding["role"] == role and
         observation["operationId"] == proof["operationId"] == context.request["operationId"] and
         observation["endpointUrl"] == binding["endpointUrl"] and
         observation["machineId"] == target["machineId"] and observation["dockerEngineId"] == target["dockerEngineId"] and
         observation["containerId"] == service["id"] and observation["imageId"] == service["imageId"] and
         observation["networkId"] == network["NetworkID"] and observation["endpointId"] == network["EndpointID"] and
         observation["ipAddress"] == network["IPAddress"], "ACTUAL_SERVICE_TARGET_MISMATCH", "STALE")
