"""Independent original admission, same-point bindings and current report validity."""
from pathlib import Path
import datetime as dt
import os
import sys

from core import (fields, need, integer, text, timestamp, pins, pin_key, json_pin,
                  read_pin, same, validate, VerificationError, parse, frozen_schema)


NATIVE_PROCESS_PROFILE = "linux-owned-child-subreaper-v1"
NATIVE_PROCESS_FIELDS = ("schemaVersion rehearsalId operationId restoreId targetIdentityPin recoveryPoint stage "
    "commandId command argv cwd sourcePins supervisorPin pythonPin nativeRuntimeProofPin hostId bootId "
    "pidNamespace mountNamespace networkNamespace userNamespace supervisorPid supervisorStartTicks childPid "
    "childStartTicks uid gid startedAt finishedAt terminationKind waitStatus actualExitCode descendantState "
    "stdoutPin stderrPin resultPin")
RUNTIME_PROOF_FIELDS = ("schemaVersion rehearsalId runtimeId nativeRuntimeTrustPin issuedAt expiresAt hostId bootId "
    "managerPid managerStartTicks pidNamespace mountNamespace networkNamespace userNamespace rootDevice rootInode "
    "immutableRuntimeArtifactDigest readOnlyMountEvidencePin managerIdentityEvidencePin nativeLinkageEvidencePin")
RUNTIME_TRUST_FIELDS = ("schemaVersion rehearsalId labRoot runtimeId runtimeRole backingRootPath literalRoots "
    "immutableRuntimeArtifactDigest vendorArtifactPins nativeFilePins")
_NATIVE_HELPERS = {}


def native_stream_verifier(boundary, installation_pin):
    """Self-admit only this VERIFIER using its own selected helper instance."""
    import importlib.util
    from pathlib import PurePosixPath
    same(installation_pin,boundary.context['installedClosurePin'],'NATIVE_SELF_INSTALLATION_REQUIRED')
    installation=boundary.signed(installation_pin,boundary.admission['authorityKeyPin'])
    trust=boundary.signed(installation['nativeRuntimeTrustPin'],boundary.admission['authorityKeyPin'])
    need(trust['runtimeRole']=='VERIFIER','NATIVE_SELF_VERIFIER_REQUIRED')
    selected=[]
    for name in ('repository_records','repository_native_runtime'):
        candidates=[pin for pin in installation['filePins'] if PurePosixPath(pin['path']).name==name+'.py']
        need(len(candidates)==1,'NATIVE_STREAM_HELPER_SELECTION_REQUIRED')
        source=candidates[0];native_private_path(source['path'])
        need(pin_key(source) in boundary.selected,'LAB_ORIGINAL_NOT_INDEPENDENTLY_SELECTED')
        raw=boundary.read(source,content=True);key=pin_key(source)
        module=sys.modules.get(name)
        if module is None:
            spec=importlib.util.spec_from_file_location(name,source['path'])
            need(spec is not None and spec.loader is not None,'NATIVE_STREAM_HELPER_LOAD')
            module=importlib.util.module_from_spec(spec)
            sys.modules[name]=module
            # Execute the exact verified source; import loaders may otherwise use
            # an unselected pre-existing bytecode cache with matching metadata.
            try:exec(compile(raw,source['path'],'exec'),module.__dict__)
            except BaseException:
                del sys.modules[name]
                raise
        else:need(_NATIVE_HELPERS.get(key) is module,'NATIVE_STREAM_HELPER_INSTANCE_CHANGED')
        need(getattr(module,'__file__',None)==source['path'],'NATIVE_STREAM_HELPER_INSTANCE_CHANGED')
        _NATIVE_HELPERS[key]=module
        boundary.read(source,content=False);selected.append((source,module))
    module=selected[-1][1]
    need(callable(getattr(module,'verify_native_file',None)) and callable(getattr(module,'verify_native_installation',None)),
         'NATIVE_STREAM_API_REQUIRED')
    module.verify_native_installation(installation_pin,[boundary.admission['authorityKeyPin']],deadline=boundary.deadline.end)
    for source,_ in selected:boundary.read(source,content=False)
    return module


def native_private_path(value):
    from pathlib import PurePosixPath
    from lab_boundary import ROOT
    path = PurePosixPath(text(value))
    need(path.is_absolute() and str(path) == value and ".." not in path.parts and
         PurePosixPath(ROOT) in path.parents, "NATIVE_RUNTIME_PRIVATE_ROOT")


def native_runtime_metadata(boundary, proof_pin, role, maximum_age_ms):
    """Authenticate selected metadata; this does not perform runtime self-admission."""
    from lab_boundary import REHEARSAL, ROOT
    from core import sha
    from pathlib import PurePosixPath
    need(boundary is not None, "NATIVE_PROFILE_LAB_ONLY")
    boundary.recheck()
    key = boundary.admission["authorityKeyPin"]
    proof = boundary.signed(proof_pin, key)
    fields(proof, RUNTIME_PROOF_FIELDS, "RepositoryLabNativeRuntimeProof/v1")
    trust = boundary.signed(proof["nativeRuntimeTrustPin"], key)
    fields(trust, RUNTIME_TRUST_FIELDS, "RepositoryLabNativeRuntimeTrust/v1")
    need(proof["rehearsalId"] == trust["rehearsalId"] == REHEARSAL and
         proof["runtimeId"] == trust["runtimeId"] and trust["runtimeRole"] == role and
         role in {"EXECUTOR", "VERIFIER"} and trust["labRoot"] == ROOT, "NATIVE_RUNTIME_ROLE_OR_SCOPE")
    text(proof["runtimeId"])
    for value in (proof["nativeRuntimeTrustPin"]["path"], trust["backingRootPath"]):
        native_private_path(value)
    need(type(trust["literalRoots"]) is list and bool(trust["literalRoots"]) and
         all(type(value) is str and PurePosixPath(value).is_absolute() and str(PurePosixPath(value)) == value
             and ".." not in PurePosixPath(value).parts for value in trust["literalRoots"]) and
         len(trust["literalRoots"]) == len(set(trust["literalRoots"])), "NATIVE_LITERAL_ROOTS")
    need(proof["immutableRuntimeArtifactDigest"] == trust["immutableRuntimeArtifactDigest"], "NATIVE_RUNTIME_DIGEST")
    digest = text(trust["immutableRuntimeArtifactDigest"])
    need(digest.startswith("sha256:"), "NATIVE_RUNTIME_DIGEST")
    sha(digest[7:])
    pins(trust["vendorArtifactPins"])
    need(type(trust["nativeFilePins"]) is list and bool(trust["nativeFilePins"]), "NATIVE_RUNTIME_MEMBERS")
    members = []
    for item in trust["nativeFilePins"]:
        fields(item, "pin roles vendorArtifactPins")
        members.append(item["pin"])
        need(type(item["roles"]) is list and bool(item["roles"]) and
             all(type(value) is str for value in item["roles"]) and len(item["roles"]) == len(set(item["roles"])) and
             set(item["roles"]) <= {"native-tool", "native-manager", "native-interpreter", "native-library", "native-locale"},
             "NATIVE_RUNTIME_MEMBER_ROLE")
        need(set(pins(item["vendorArtifactPins"])) <= set(pins(trust["vendorArtifactPins"])), "NATIVE_VENDOR_UNBOUND")
    pins(members)
    need(len({pin_key(pin)[0] for pin in members}) == len(members), "NATIVE_RUNTIME_MEMBER_DUPLICATE_PATH")
    for pin in [*trust["vendorArtifactPins"], *members]:
        need(pin_key(pin) in boundary.selected, "LAB_ORIGINAL_NOT_INDEPENDENTLY_SELECTED")
    for name in ("readOnlyMountEvidencePin", "managerIdentityEvidencePin", "nativeLinkageEvidencePin"):
        boundary.original(proof[name])
    for name in ("managerPid", "managerStartTicks", "rootInode"):
        integer(proof[name], 1)
    integer(proof["rootDevice"])
    for name in ("hostId", "bootId", "pidNamespace", "mountNamespace", "networkNamespace", "userNamespace"):
        text(proof[name])
    host = boundary.original(boundary.admission["executionHostPin"])
    need(proof["hostId"] == host["hostId"] and proof["bootId"] == host["bootId"], "NATIVE_RUNTIME_HOST_MISMATCH", "STALE")
    current = dt.datetime.now(dt.timezone.utc)
    start, end = timestamp(proof["issuedAt"]), timestamp(proof["expiresAt"])
    need(0 <= (current-start).total_seconds()*1000 <= integer(maximum_age_ms, 1) and start <= current < end,
         "NATIVE_RUNTIME_PROOF_STALE", "STALE")
    boundary.window(proof["expiresAt"])
    return proof, trust


def native_runtime_proof(boundary, proof_pin, role, maximum_age_ms, *, selected_installation=True):
    need(role=='VERIFIER' and selected_installation is True,'NATIVE_SELF_VERIFIER_REQUIRED')
    proof,trust=native_runtime_metadata(boundary,proof_pin,role,maximum_age_ms)
    installed=boundary.signed(boundary.context['installedClosurePin'],boundary.admission['authorityKeyPin'])
    fields(installed,'schemaVersion root sourceToolkitPin filePins pythonPin dependencyPins nativeRuntimeTrustPin nativeRuntimeProofPin',
           'RepositoryNativeInstallation/v2')
    same(installed['nativeRuntimeProofPin'],proof_pin,'NATIVE_SELECTED_RUNTIME_PROOF')
    same(installed['nativeRuntimeTrustPin'],proof['nativeRuntimeTrustPin'],'NATIVE_SELECTED_RUNTIME_TRUST')
    host=boundary.original(boundary.admission['executionHostPin'])
    need(proof['pidNamespace']==host['pidNamespace'] and proof['mountNamespace']==host['mountNamespace'],
         'NATIVE_SELECTED_NAMESPACE_MISMATCH','STALE')
    native_stream_verifier(boundary,boundary.context['installedClosurePin'])
    return proof,trust


def _native_process_result(boundary, process_pin, invocation, source_pins, maximum_age_ms, *,
                           role="VERIFIER", selected_installation=True, runtime_proof_pin=None):
    from lab_boundary import REHEARSAL
    from core import absolute
    need(boundary is not None, "NATIVE_PROFILE_LAB_ONLY")
    boundary.recheck()
    result = boundary.signed(process_pin, boundary.admission["authorityKeyPin"])
    fields(result, NATIVE_PROCESS_FIELDS, "RecoveryNativeProcessResult/v1")
    need(result["rehearsalId"] == REHEARSAL, "NATIVE_PROCESS_REHEARSAL")
    for name in ("operationId", "restoreId", "recoveryPoint", "stage", "commandId", "command", "argv", "cwd", "startedAt", "finishedAt"):
        need(result[name] == invocation[name], "NATIVE_PROCESS_INVOCATION_MISMATCH", "STALE")
    need(result["operationId"] == boundary.operation_id, "NATIVE_PROCESS_CURRENT_OPERATION")
    for name in ("operationId", "restoreId", "recoveryPoint", "stage", "commandId", "command", "cwd"):
        text(result[name])
    same(result["targetIdentityPin"], invocation["targetIdentityPin"], "NATIVE_PROCESS_TARGET_MISMATCH")
    same(result["targetIdentityPin"], boundary.admission["targetIdentityPin"], "NATIVE_PROCESS_CURRENT_TARGET")
    same(result["resultPin"], invocation["resultPin"], "NATIVE_PROCESS_RESULT_MISMATCH")
    need(set(pins(result["sourcePins"])) == set(pins(invocation["sourcePins"])) <= set(pins(source_pins)),
         "NATIVE_PROCESS_SOURCE_MISMATCH")
    need({pin_key(result["pythonPin"]), pin_key(result["supervisorPin"])} <= set(pins(result["sourcePins"])),
         "NATIVE_PROCESS_EXECUTOR_UNBOUND")
    for pin in result["sourcePins"]:
        need(pin_key(pin) in boundary.selected, "LAB_ORIGINAL_NOT_INDEPENDENTLY_SELECTED")
        if role=='VERIFIER':boundary.read(pin, content=False)
    need(type(result["argv"]) is list and bool(result["argv"]) and
         all(type(value) is str and value and "\x00" not in value for value in result["argv"]), "NATIVE_PROCESS_ARGV")
    executable = os.path.normcase(str(absolute(result["argv"][0])))
    need(executable in {pin_key(pin)[0] for pin in result["sourcePins"]}, "NATIVE_PROCESS_EXECUTABLE_UNBOUND")
    if role == "VERIFIER":
        need(executable == pin_key(result["pythonPin"])[0], "NATIVE_PROCESS_PYTHON_MISMATCH")
    absolute(result["cwd"])
    for name in ("supervisorPid", "supervisorStartTicks", "childPid", "childStartTicks"):
        integer(result[name], 1)
    need(result["supervisorPid"] != result["childPid"], "NATIVE_PROCESS_CHILD_IDENTITY")
    need(result["childStartTicks"] >= result["supervisorStartTicks"], "NATIVE_PROCESS_CHILD_START")
    for name in ("uid", "gid"):
        integer(result[name])
    if runtime_proof_pin is not None:
        same(result["nativeRuntimeProofPin"], runtime_proof_pin, "NATIVE_PROCESS_RUNTIME_UNBOUND")
    if role=='EXECUTOR':
        need(selected_installation is False,'NATIVE_PEER_METADATA_ONLY')
        proof,_=native_runtime_metadata(boundary,result['nativeRuntimeProofPin'],role,maximum_age_ms)
    else:
        proof,_=native_runtime_proof(boundary,result['nativeRuntimeProofPin'],role,maximum_age_ms,
                                   selected_installation=selected_installation)
    for name in ("hostId", "bootId", "pidNamespace", "mountNamespace", "networkNamespace", "userNamespace"):
        need(result[name] == proof[name], "NATIVE_PROCESS_NAMESPACE_OR_HOST_MISMATCH", "STALE")
    if selected_installation:
        host = boundary.original(boundary.admission["executionHostPin"])
        same(result["pythonPin"], host["pythonPin"], "NATIVE_PROCESS_CURRENT_PYTHON")
        need(result["uid"] == host["uid"] and result["gid"] == host["gid"], "NATIVE_PROCESS_CURRENT_UID_GID")
    started, finished = timestamp(result["startedAt"]), timestamp(result["finishedAt"])
    current = dt.datetime.now(dt.timezone.utc)
    need(timestamp(proof["issuedAt"]) <= started < finished <= current < timestamp(proof["expiresAt"]) and
         0 <= (current-finished).total_seconds()*1000 <= maximum_age_ms, "NATIVE_PROCESS_TIME", "STALE")
    for name in ("stdoutPin", "stderrPin", "resultPin"):
        boundary.original(result[name], False)
    need(result["terminationKind"] in {"EXITED", "SIGNALED", "UNKNOWN"} and
         result["descendantState"] in {"REAPED", "UNKNOWN"}, "NATIVE_PROCESS_TERMINAL_FIELDS")
    if (result["terminationKind"] == "UNKNOWN" or result["descendantState"] == "UNKNOWN" or
            result["waitStatus"] is None or result["actualExitCode"] is None):
        need(False, "NATIVE_PROCESS_EXIT_UNKNOWN", "UNKNOWN")
    if invocation["state"] == "TERMINAL_UNKNOWN" or invocation["actualExitCode"] is None:
        need(False, "NATIVE_PROCESS_EXIT_UNKNOWN", "UNKNOWN")
    need(type(invocation["actualExitCode"]) is int, "NATIVE_PROCESS_INVOCATION_EXIT_INTEGER")
    status = integer(result["waitStatus"])
    need(status <= 65535, "NATIVE_PROCESS_WAIT_STATUS")
    if result["terminationKind"] == "SIGNALED":
        # POSIX wait status is validated as bytes even in offline Windows contract checks.
        need((status & 127) not in (0, 127) and status >> 8 == 0, "NATIVE_PROCESS_WAIT_MISMATCH")
        signal_number = status & 127
        need(type(result["actualExitCode"]) is int and result["actualExitCode"] == -signal_number,
             "NATIVE_PROCESS_SIGNAL_EXIT_MISMATCH")
        need(False, "NATIVE_PROCESS_SIGNALED", "FAILED")
    need((status & 255) == 0 and (status >> 8) <= 255, "NATIVE_PROCESS_WAIT_MISMATCH")
    actual = status >> 8
    need(type(result["actualExitCode"]) is int and result["actualExitCode"] == actual == invocation["actualExitCode"],
         "NATIVE_PROCESS_EXIT_MISMATCH", "FAILED")
    need(actual == 0 and invocation["state"] == "SUCCEEDED", "NATIVE_PROCESS_FAILED", "FAILED")
    for pin in result["sourcePins"]:
        if role=='VERIFIER':boundary.read(pin, content=False)
    boundary.recheck()
    return result


def native_process_result(boundary, process_pin, invocation, source_pins, maximum_age_ms, *,
                          role="VERIFIER", selected_installation=True, runtime_proof_pin=None):
    try:
        return _native_process_result(boundary, process_pin, invocation, source_pins, maximum_age_ms,
            role=role, selected_installation=selected_installation, runtime_proof_pin=runtime_proof_pin)
    except VerificationError as error:
        if error.code == "ORIGINAL_UNAVAILABLE":
            raise VerificationError("NATIVE_PROCESS_ORIGINAL_UNAVAILABLE", "UNKNOWN") from error
        raise


class EvidenceContext:
    def __init__(self, request, request_pin, trust_pin, deadline, selected_binding=None):
        self.request, self.deadline = request, deadline
        original_trust = json_pin(trust_pin, deadline)
        if selected_binding is None:
            trust = original_trust
        else:
            lab_selection = original_trust.get("schemaVersion") == "RecoveryLabCallerSelection/v1"
            fields(original_trust, "schemaVersion callerThreadId producerThreadIds requestPin schemaPin sourceScopePin "
                   "executableScopePin runTracePin independentOriginalPins validUntil" +
                   (" labAdmissionPin" if lab_selection else ""),
                   "RecoveryLabCallerSelection/v1" if lab_selection else "RecoveryCallerSelection/v1")
            need(selected_binding == dict(original_trust, schemaVersion=
                 "RecoveryLabCallerBinding/v1" if lab_selection else "RecoveryCallerBinding/v1"),
                 "CALLER_SELECTION_MISMATCH")
            trust = selected_binding
        lab_selected = trust.get("schemaVersion") == "RecoveryLabCallerBinding/v1"
        fields(trust, "schemaVersion callerThreadId producerThreadIds requestPin schemaPin "
               "sourceScopePin executableScopePin runTracePin independentOriginalPins validUntil" +
               (" labAdmissionPin" if lab_selected else ""),
               "RecoveryLabCallerBinding/v1" if lab_selected else "RecoveryCallerBinding/v1")
        text(trust["callerThreadId"])
        need(type(trust["producerThreadIds"]) is list and bool(trust["producerThreadIds"])
             and all(type(value) is str and value for value in trust["producerThreadIds"])
             and trust["callerThreadId"] not in trust["producerThreadIds"], "CALLER_NOT_INDEPENDENT")
        need(timestamp(trust["validUntil"]) > dt.datetime.now(dt.timezone.utc), "CALLER_BINDING_EXPIRED", "STALE")
        same(request_pin, trust["requestPin"], "CALLER_REQUEST_MISMATCH")
        self.trust = trust
        self.schema = frozen_schema(trust["schemaPin"])
        validate(self.schema, "OperationRequest", request)
        need(request["action"] == "VERIFY_RECOVERY", "UNSUPPORTED_ACTION")
        need(set(request["inputPins"]) == {"restorePlan", "restoreExecutionResult", "applicationStartResult"},
             "VERIFY_INPUT_KEYS")
        need(request["selectedPointPin"] is not None, "SELECTED_POINT_REQUIRED")
        self.admitted = set(pins(trust["independentOriginalPins"]))
        self.admitted.add(pin_key(request_pin))
        self.request_pin = request_pin
        self.consumed = [request_pin, trust_pin, trust["schemaPin"], trust["sourceScopePin"],
                         trust["executableScopePin"], trust["runTracePin"]]
        self.admitted.update(pin_key(pin) for pin in self.consumed)
        self.source_pin = trust["sourceScopePin"]
        business = self.record(self.source_pin)
        fields(business, "schemaVersion machineId sourceIdentityPin containerIds containerNames writerContainerIds "
               "volumeNames networkNames materialPaths endpointHosts", "RecoverySourceScope/v1")
        self.record(business["sourceIdentityPin"])
        self.business_scope = business
        self.lab = None
        if lab_selected:
            from lab_boundary import LabBoundary
            self.lab = LabBoundary(trust["labAdmissionPin"], trust["independentOriginalPins"],
                                   self.read, self.record, deadline, request["operationId"], request["mode"],
                                   request_pin=request_pin)
            self.admitted.add(pin_key(self.lab.context_pin))
            self.consumed.append(self.lab.context_pin)
            same(self.lab.admission["sourceIdentityPin"], business["sourceIdentityPin"], "LAB_BUSINESS_SOURCE_MISMATCH")
        scope = json_pin(trust["executableScopePin"], deadline)
        fields(scope, "schemaVersion callerThreadId producerThreadIds complete sourcePins", "RecoveryExecutableScope/v1")
        need(scope["callerThreadId"] == trust["callerThreadId"] and
             scope["producerThreadIds"] == trust["producerThreadIds"] and scope["complete"] is True,
             "SOURCE_SCOPE_NOT_INDEPENDENT_OR_COMPLETE")
        source_keys = pins(scope["sourcePins"])
        need(len({key[0] for key in source_keys}) == len(source_keys), "SOURCE_PATH_DUPLICATE")
        self.source_pins = scope["sourcePins"]
        self.source_keys = set(source_keys)
        self.admitted.update(source_keys)
        # Caller must account for every executable Python source in this module.
        own_files = {os.path.normcase(str(path.resolve()))
                     for path in Path(__file__).resolve().parent.glob("*.py")}
        own_files.add(os.path.normcase(str(Path(sys.executable).resolve())))
        need(own_files <= {key[0] for key in source_keys}, "VERIFIER_SOURCE_SCOPE_INCOMPLETE")
        trace = json_pin(trust["runTracePin"], deadline)
        fields(trace, "schemaVersion callerThreadId operationId sourcePinsBefore sourcePinsAfter "
               "startedAt finishedAt collectionInvocationPins", "RecoverySourceTrace/v1")
        need(trace["callerThreadId"] == trust["callerThreadId"] and
             trace["operationId"] == request["operationId"], "SOURCE_TRACE_IDENTITY")
        need(pins(trace["sourcePinsBefore"]) == source_keys == pins(trace["sourcePinsAfter"]),
             "SOURCE_CHANGED_DURING_RUN", "STALE")
        need(timestamp(trace["startedAt"]) < timestamp(trace["finishedAt"]) <=
             dt.datetime.now(dt.timezone.utc), "SOURCE_TRACE_TIME")
        self.trace = trace
        for pin in scope["sourcePins"]:
            self.read(pin)

    def read(self, pin, content=False):
        self.deadline.remaining()
        need(pin_key(pin) in self.admitted, "ORIGINAL_NOT_CALLER_PINNED")
        raw = read_pin(pin, self.deadline, content=content)
        if pin_key(pin) not in {pin_key(item) for item in self.consumed}:
            self.consumed.append(pin)
        return raw

    def record(self, pin, definition=None):
        from core import parse
        record = parse(self.read(pin, content=True))
        if definition:
            validate(self.schema, definition, record)
        return record

    def bind(self, record):
        request = self.request
        need(record["operationId"] == request["operationId"] and
             record["restoreId"] == self.plan["restoreId"], "OPERATION_RESTORE_MISMATCH", "STALE")
        same(record["targetIdentityPin"], self.target_pin, "TARGET_MISMATCH")
        if "recoveryPoint" in record:
            need(record["recoveryPoint"] == self.plan["recoveryPoint"], "RECOVERY_POINT_MISMATCH", "STALE")

    def observation(self, pin, kind):
        record = self.record(pin)
        fields(record, "schemaVersion kind operationId restoreId targetIdentityPin recoveryPoint "
               "startedAt finishedAt complete data", "RecoveryObservation/v1")
        self.bind(record)
        need(record["kind"] == kind and record["complete"] is True, "OBSERVATION_INCOMPLETE")
        start, finish = timestamp(record["startedAt"]), timestamp(record["finishedAt"])
        need(timestamp(self.trace["startedAt"]) <= start <= finish <= timestamp(self.trace["finishedAt"]),
             "OBSERVATION_OUTSIDE_TRACED_RUN")
        return record

    def invocation(self, pin, stage, evidence_pins):
        record = self.record(pin)
        fields(record, "schemaVersion operationId restoreId targetIdentityPin recoveryPoint stage "
               "state actualExitCode startedAt finishedAt sourcePins resultPin commandId command argv cwd "
               "processProfile processResultPin", "RecoveryInvocation/v1")
        self.bind(record)
        need(record["stage"] == stage, "INVOCATION_STAGE")
        need(record["state"] in ("SUCCEEDED", "FAILED_RETAINED", "TERMINAL_UNKNOWN"), "INVOCATION_STATE")
        if record["processProfile"] != NATIVE_PROCESS_PROFILE:
            if record["state"] == "TERMINAL_UNKNOWN" or record["actualExitCode"] is None:
                need(False, "ORIGINAL_PROCESS_EXIT_UNKNOWN", "UNKNOWN")
            need(type(record["actualExitCode"]) is int, "ORIGINAL_EXIT_INTEGER_REQUIRED")
            need(record["state"] == "SUCCEEDED" and record["actualExitCode"] == 0,
                 "ORIGINAL_PROCESS_FAILED", "FAILED")
        need(pin_key(record["resultPin"]) in set(pins(evidence_pins)), "INVOCATION_RESULT_UNBOUND")
        need(set(pins(record["sourcePins"])) <= self.source_keys, "INVOCATION_SOURCE_UNBOUND")
        from core import absolute
        need(type(record["argv"]) is list and bool(record["argv"]) and
             all(type(value) is str and "\x00" not in value for value in record["argv"]), "INVOCATION_ARGV_REQUIRED")
        executable = os.path.normcase(str(absolute(record["argv"][0])))
        need(executable in {pin_key(value)[0] for value in record["sourcePins"]}, "INVOKED_EXECUTABLE_NOT_PINNED")
        absolute(record["cwd"])
        text(record["commandId"])
        text(record["command"])
        raw_result = (None if record["processProfile"] == NATIVE_PROCESS_PROFILE else
                      self.record(record["processResultPin"]))
        command_id_key = "id"
        if record["processProfile"] == NATIVE_PROCESS_PROFILE:
            maximum_age = integer(self.record(self.request["policyPin"])["maxAgeMilliseconds"], 1)
            saved = native_process_result(self.lab, record["processResultPin"], record, self.source_pins, maximum_age)
            actual_exit = saved["actualExitCode"]
            command_id_key = "commandId"
        elif record["processProfile"] == "exec-command-result":
            saved = raw_result
            need(type(saved.get("result")) is dict and type(saved["result"].get("exit_code")) is int,
                 "PROCESS_ORIGINAL_INCOMPLETE", "UNKNOWN")
            actual_exit = saved["result"]["exit_code"]
            need(saved["result"].get("session_id") is None, "PROCESS_ORIGINAL_STILL_RUNNING", "UNKNOWN")
        elif record["processProfile"] == "codex-command-event":
            need(type(raw_result.get("payload")) is dict and type(raw_result["payload"].get("item")) is dict,
                 "PROCESS_ORIGINAL_EVENT_REQUIRED")
            saved = raw_result["payload"]["item"]
            need(saved.get("type") == "CommandExecution" and saved.get("status") == "completed",
                 "PROCESS_ORIGINAL_INCOMPLETE", "UNKNOWN")
            need(type(saved.get("exitCode")) is int, "PROCESS_ORIGINAL_EXIT_UNKNOWN", "UNKNOWN")
            actual_exit = saved["exitCode"]
        else:
            need(False, "EXPLICIT_PROCESS_PROFILE_REQUIRED")
        need(saved.get(command_id_key) == record["commandId"] and saved.get("command") == record["command"] and
             saved.get("argv") == record["argv"] and saved.get("cwd") == record["cwd"], "PROCESS_ORIGINAL_CALL_MISMATCH")
        need(actual_exit == record["actualExitCode"], "PROCESS_ORIGINAL_EXIT_MISMATCH", "FAILED")
        need(timestamp(self.trace["startedAt"]) <= timestamp(record["startedAt"]) <
             timestamp(record["finishedAt"]) <= timestamp(self.trace["finishedAt"]), "INVOCATION_TIME")
        self.read(record["resultPin"])
        return record

    def recheck(self):
        need(timestamp(self.trust["validUntil"]) > dt.datetime.now(dt.timezone.utc), "CALLER_BINDING_EXPIRED", "STALE")
        if self.lab is not None:
            self.lab.recheck()
        for pin in self.consumed:
            self.deadline.remaining()
            read_pin(pin, self.deadline, content=False)


def admit_restore(context, target_record_pin, policy):
    request = context.request
    plan = context.record(request["inputPins"]["restorePlan"], "RestorePlan")
    context.plan = plan
    need(plan["operationId"] == request["operationId"] and plan["mode"] == request["mode"],
         "PLAN_REQUEST_MISMATCH", "STALE")
    same(plan["targetRef"], request["sourceOrTargetRef"], "TARGET_REF_MISMATCH")
    same(plan["candidatePin"], request["selectedPointPin"], "CANDIDATE_MISMATCH")
    context.read(request["sourceOrTargetRef"])
    configuration = context.record(request["sourceOrTargetRef"])
    need(configuration.get("schemaVersion") == "RecoveryEnvironmentConfig/v1", "TARGET_CONFIG_VERSION")
    same(configuration["sourceScopePin"], context.source_pin, "BUSINESS_SOURCE_SCOPE_MISMATCH")
    target = context.record(target_record_pin, "RecoveryTarget")
    context.target_pin = target["targetIdentityPin"]
    context.read(context.target_pin)
    if context.lab is not None:
        same(context.lab.admission["targetIdentityPin"], context.target_pin, "LAB_RESTORE_TARGET_MISMATCH")
    chain = plan["orderedChainPins"]
    pins(chain)
    same(chain[-1], plan["candidatePin"], "CHAIN_TIP_MISMATCH")
    points = []
    for index, pin in enumerate(chain):
        point = context.record(pin, "RepositoryPoint")
        need(point["integrityState"] == "COMPLETE" and point["blockedReason"] in
             (None, "REPOSITORY_CURRENT_RECOVERY_PASSED_REQUIRED"),
             "REPOSITORY_POINT_INCOMPLETE")
        if request["mode"] == "REHEARSAL":
            need(point["rehearsalEligible"] is True, "REPOSITORY_POINT_NOT_ELIGIBLE")
        need(point["pointType"] == ("FULL" if index == 0 else "INCREMENTAL"), "CHAIN_ORDER")
        parents = pins(point["parentPointPins"], False)
        need(parents == pins(chain[:index], False), "CHAIN_PARENT_MISMATCH")
        need(not points or point["generationId"] == points[0]["generationId"], "CHAIN_GENERATION_MISMATCH")
        for key in ("manifestPin", "readbackEvidencePin", "ownerCloseEvidencePin", "originalExitEvidencePin"):
            context.read(point[key])
        if context.lab is not None:
            manifest = context.lab.signed(point["manifestPin"], context.lab.admission["repositoryEvidenceKeyPin"])
            context.lab.copy_protection(manifest["copyProtectionPin"], policy["maxAgeMilliseconds"])
        for payload in point["payloadRefs"]:
            context.read(payload)
        points.append(point)
    need(points[-1]["commonRecoveryPoint"] == plan["recoveryPoint"], "PLAN_POINT_MISMATCH", "STALE")
    tool_versions = plan["toolPins"] + plan["supportedVersionPins"]
    pins(tool_versions)
    need(pins(target["versionPins"]) == pins(plan["supportedVersionPins"]), "TARGET_VERSION_MISMATCH", "STALE")
    for pin in tool_versions:
        context.read(pin)
    if request["mode"] == "CONTROLLED_RESTORE":
        from controlled_eligibility import verify_controlled_eligibility
        verify_controlled_eligibility(context, policy)
    for key in ("configurationPin", "sideEffectIsolationPin", "resourcesProofPin", "isolationProofPin",
                "modePreconditionsPin", "leaseRef"):
        context.read(target[key])
    same(plan["leaseRef"], target["leaseRef"], "PLAN_TARGET_LEASE_MISMATCH")
    context.read(plan["sideEffectPolicyPin"])
    for authorization in plan["authorizationRefs"]:
        context.read(authorization)
    restore = context.record(request["inputPins"]["restoreExecutionResult"], "RestoreExecutionResult")
    context.bind(restore)
    same(restore["planPin"], request["inputPins"]["restorePlan"], "RESTORE_PLAN_MISMATCH")
    need(restore["state"] == "SUCCEEDED", "RESTORE_NOT_SUCCEEDED",
         "UNKNOWN" if restore["state"] == "TERMINAL_UNKNOWN" else "FAILED")
    need(restore["writeProtectionState"] == "ENFORCED", "WRITE_PROTECTION_NOT_ENFORCED")
    from native_originals import restore_originals, application_originals, isolation_lifecycle
    originals = restore_originals(context, restore, target_record_pin, points)
    context.restore_invocations = originals
    app = context.record(request["inputPins"]["applicationStartResult"], "ApplicationStartResult")
    context.bind(app)
    same(app["restoreResultPin"], request["inputPins"]["restoreExecutionResult"], "APP_RESTORE_MISMATCH")
    need(app["state"] == "SUCCEEDED", "APPLICATION_NOT_SUCCEEDED",
         "UNKNOWN" if app["state"] == "TERMINAL_UNKNOWN" else "FAILED")
    same(app["configurationPin"], target["configurationPin"], "APPLICATION_CONFIGURATIONPIN_MISMATCH")
    need(set(pins(app["imagePins"])) <= set(pins(target["versionPins"])), "IMAGE_VERSION_MISMATCH", "STALE")
    for pin in app["imagePins"]:
        context.read(pin)
    starts = application_originals(context, app)
    context.application_invocations = starts
    context.read(app["healthEvidencePin"])
    isolation_lifecycle(context, target, app)
    return plan, restore, app, target


def report_invalidations(report, current, max_age_ms, observed_at, deadline=None):
    """Caller supplies the current binding and original envelope's finishedAt.

    Every referenced original is reread, including the complete executable scope,
    timing, browser artifacts, and nested version/configuration/chain evidence.
    """
    required = ("backupAndChainPins", "planPin", "targetIdentityPin", "sourceScopePin",
                "toolAndVersionPins", "restoreResultPin", "applicationStartPin", "targetApprovalRefs")
    identity = ("operationId", "restoreId", "mode")
    need(type(current) is dict and set(current) == set(required) | set(identity) | {"reportGeneratedAt"},
         "CURRENT_BINDING_REQUIRED")
    integer(max_age_ms, 1)
    reasons = []
    for key in identity:
        if report[key] != current[key]:
            reasons.append(key + "_CHANGED")
    for key in required:
        left, right = report[key], current[key]
        match = pins(left, False) == pins(right, False) if type(left) is list else pin_key(left) == pin_key(right)
        if not match:
            reasons.append(key + "_CHANGED")
    age = (timestamp(observed_at) - timestamp(current["reportGeneratedAt"])).total_seconds() * 1000
    if age < 0:
        reasons.append("REPORT_FROM_FUTURE")
    elif age > max_age_ms:
        reasons.append("REPORT_EXPIRED")
    visited = set()
    def reread(pin, key):
        identity_key = pin_key(pin)
        if identity_key in visited:
            return
        need(len(visited) < 10000, "EVIDENCE_GRAPH_LIMIT")
        visited.add(identity_key)
        try:
            read_pin(pin, deadline, content=False)
            from core import MAX_JSON_BYTES
            if pin["bytes"] > MAX_JSON_BYTES:
                return
            raw = read_pin(pin, deadline, content=True)
        except VerificationError as error:
            reasons.append(key + "_ORIGINAL_" + error.code)
            return
        if raw.lstrip().startswith((b"{", b"[")):
            try:
                record = parse(raw)
                if type(record) is dict and record.get("schemaVersion") == "RecoveryObservation/v1":
                    elapsed = (timestamp(observed_at) - timestamp(record["finishedAt"])).total_seconds() * 1000
                    if elapsed < 0 or elapsed > max_age_ms:
                        reasons.append(key + "_OBSERVATION_EXPIRED")
                if type(record) is dict and record.get("schemaVersion") == "RecoveryVerificationAuthorization/v1":
                    if not timestamp(record["validFrom"]) <= timestamp(observed_at) < timestamp(record["validUntil"]):
                        reasons.append(key + "_AUTHORIZATION_EXPIRED")
                if type(record) is dict and record.get("schemaVersion") in ("RecoveryCallerBinding/v1", "RecoveryLabCallerBinding/v1"):
                    if timestamp(observed_at) >= timestamp(record["validUntil"]):
                        reasons.append(key + "_CALLER_BINDING_EXPIRED")
                version = record.get("schemaVersion") if type(record) is dict else None
                if type(version) is str and (version == "RecoveryLabAdmission" or version.startswith("RecoveryLabAdmission/")):
                    if version != "RecoveryLabAdmission/v2":
                        reasons.append(key + "_LAB_ADMISSION_VERSION_UNSUPPORTED")
                    elif timestamp(observed_at) >= timestamp(record.get("validUntil")):
                        reasons.append(key + "_LAB_AUTHORITY_EXPIRED")
                if version == "RepositoryLabCopyProtection/v1":
                    if timestamp(observed_at) >= timestamp(record["validUntil"]):
                        reasons.append(key + "_LAB_AUTHORITY_EXPIRED")
                if type(record) is dict and record.get("schemaVersion") in (
                        "BackupRehearsalAuthorityContext/v1", "RepositoryLabScope/v1"):
                    if timestamp(observed_at) >= timestamp(record["expiresAt"]):
                        reasons.append(key + "_LAB_AUTHORITY_EXPIRED")
                walk(record, key)
            except VerificationError as error:
                reasons.append(key + "_ORIGINAL_" + error.code)
    def walk(value, key):
        if type(value) is dict:
            if set(value) == {"path", "bytes", "sha256"} and type(value["path"]) is str and \
                    type(value["bytes"]) is int and type(value["sha256"]) is str:
                reread(value, key)
            else:
                for child in value.values():
                    walk(child, key)
        elif type(value) is list:
            for child in value:
                walk(child, key)
    for key in (*required, "dataEvidencePins", "playwrightEvidencePins", "rtoObservation", "rpoObservation"):
        walk(report[key], key)
    return list(dict.fromkeys(reasons))


def assess_report(report, current, max_age_ms, observed_at, deadline=None):
    reasons = report_invalidations(report, current, max_age_ms, observed_at, deadline)
    result = dict(report)
    if reasons:
        result["verdict"] = "STALE"
        result["invalidatedBy"] = list(dict.fromkeys(report["invalidatedBy"] + reasons))
    return result
