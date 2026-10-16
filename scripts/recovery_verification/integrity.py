"""Full inventories are compared separately from database reference coverage."""
from core import fields, need, text, sha, integer, canonical, digest, timestamp, same


def data_snapshot(value):
    fields(value, "databaseId tables objectScopes objects references referenceSpecs objectTarget derivedInventoryPin derived")
    text(value["databaseId"])
    need(type(value["tables"]) is list and bool(value["tables"]), "DATABASE_TABLE_SCOPE_REQUIRED")
    tables = {}
    for table in value["tables"]:
        fields(table, "name schemaSha256 rowCount dataSha256")
        name = text(table["name"])
        need(name not in tables, "DUPLICATE_TABLE")
        integer(table["rowCount"])
        sha(table["schemaSha256"])
        sha(table["dataSha256"])
        tables[name] = table
    need(type(value["objectScopes"]) is list and bool(value["objectScopes"]), "OBJECT_SCOPE_REQUIRED")
    scopes = []
    for scope in value["objectScopes"]:
        fields(scope, "bucket prefix")
        text(scope["bucket"])
        need(type(scope["prefix"]) is str, "OBJECT_PREFIX_REQUIRED")
        pair = scope["bucket"], scope["prefix"]
        need(pair not in scopes, "DUPLICATE_OBJECT_SCOPE")
        need(not any(bucket == pair[0] and (pair[1].startswith(prefix) or prefix.startswith(pair[1]))
                     for bucket, prefix in scopes), "OVERLAPPING_OBJECT_SCOPES")
        scopes.append(pair)
    need(type(value["objects"]) is list, "OBJECT_INVENTORY_REQUIRED")
    objects = {}
    for item in value["objects"]:
        fields(item, "bucket key bytes sha256")
        pair = text(item["bucket"]), text(item["key"])
        need(pair not in objects, "DUPLICATE_OBJECT")
        need(any(pair[0] == bucket and pair[1].startswith(prefix) for bucket, prefix in scopes),
             "OBJECT_OUTSIDE_SCOPE")
        integer(item["bytes"])
        sha(item["sha256"])
        objects[pair] = item
    need(type(value["referenceSpecs"]) is list and bool(value["referenceSpecs"]), "REFERENCE_SCOPE_REQUIRED")
    for spec in value["referenceSpecs"]:
        fields(spec, "table bucket keyColumn deletedColumn domainColumn allowedDomains")
        need(spec["table"] in tables, "REFERENCE_TABLE_NOT_IN_SCOPE")
        for key in ("bucket", "keyColumn", "deletedColumn", "domainColumn"):
            text(spec[key])
        need(type(spec["allowedDomains"]) is list and bool(spec["allowedDomains"])
             and all(type(domain) is str and domain for domain in spec["allowedDomains"]), "REFERENCE_DOMAIN_SCOPE")
    need(type(value["references"]) is list, "REFERENCE_INVENTORY_REQUIRED")
    specs = {spec["table"]: spec for spec in value["referenceSpecs"]}
    need(len(specs) == len(value["referenceSpecs"]), "DUPLICATE_REFERENCE_TABLE")
    counts = {name: 0 for name in specs}
    for item in value["references"]:
        fields(item, "table rowSha256 bucket key deleted domain")
        sha(item["rowSha256"])
        need(item["table"] in specs and type(item["deleted"]) is bool, "REFERENCE_SCOPE_OR_DELETE_STATE")
        spec = specs[item["table"]]
        need(item["bucket"] == spec["bucket"] and item["domain"] in spec["allowedDomains"],
             "REFERENCE_EXTERNAL_BUCKET_OR_DOMAIN")
        text(item["key"])
        counts[item["table"]] += 1
    need(all(count == tables[name]["rowCount"] for name, count in counts.items()),
         "REFERENCE_ROWS_NOT_COMPLETE")
    return tables, objects


def verify_data(expected, observed, require_deleted_objects):
    need(type(require_deleted_objects) is bool, "DELETED_OBJECT_POLICY_REQUIRED")
    expected_tables, expected_objects = data_snapshot(expected)
    actual_tables, actual_objects = data_snapshot(observed)
    need(expected["tables"] and expected["objectScopes"] == observed["objectScopes"]
         and expected["referenceSpecs"] == observed["referenceSpecs"], "DATA_SCOPE_MISMATCH", "STALE")
    # databaseId may change when restored to an isolated database; it is checked against the
    # caller-approved target identity in the verifier rather than against the source server.
    need(expected_tables == actual_tables, "DATABASE_STRUCTURE_OR_CONTENT_MISMATCH", "FAILED")
    need(expected_objects == actual_objects, "OBJECT_CONTENT_OR_INVENTORY_MISMATCH", "FAILED")
    refs = lambda rows: sorted(canonical(row) for row in rows)
    need(refs(expected["references"]) == refs(observed["references"]), "REFERENCE_ROWS_MISMATCH", "FAILED")
    required = [row for row in observed["references"] if require_deleted_objects or not row["deleted"]]
    missing = sorted({(row["bucket"], row["key"]) for row in required} - set(actual_objects))
    need(not missing, "DATABASE_REFERENCES_MISSING_OBJECTS", "FAILED")
    return {"tables": len(actual_tables), "objects": len(actual_objects),
            "referenceRows": len(observed["references"]),
            "activeReferenceRows": sum(not row["deleted"] for row in observed["references"]),
            "uniqueReferencedObjects": len({(row["bucket"], row["key"]) for row in required}),
            "referenceRowsSha256": digest(canonical(sorted(observed["references"], key=canonical)))}


PROTECTED = {"source-environment", "tenant-admin", "dcc-matrix", "showroom-28",
             "bucket-yudao-showroom", "external-systems"}


def verify_protection(before, after, required_scopes, before_isolation_pin, after_isolation_pin):
    need(type(required_scopes) is list and set(required_scopes) >= PROTECTED
         and len(required_scopes) == len(set(required_scopes)), "PROTECTION_SCOPE_INCOMPLETE")
    for data, isolation_pin in ((before, before_isolation_pin), (after, after_isolation_pin)):
        fields(data, "scopeSnapshots sideEffectIsolationPin")
        same(data["sideEffectIsolationPin"], isolation_pin, "SIDE_EFFECT_ISOLATION_CHANGED")
        need(type(data["scopeSnapshots"]) is dict and set(data["scopeSnapshots"]) == set(required_scopes),
             "PROTECTION_OBSERVATION_SCOPE")
        for value in data["scopeSnapshots"].values():
            fields(value, "resourceIdentity sha256")
            text(value["resourceIdentity"])
            sha(value["sha256"])
    need(before["scopeSnapshots"] == after["scopeSnapshots"], "PROTECTED_RESOURCE_CHANGED", "FAILED")


def verify_user_paths(data, required_paths, target_identity):
    fields(data, "engine targetOrigin tenantId tenantName username paths blockedExternalRequests "
           "pageErrorCount businessFailureCount")
    need(data["engine"] == "playwright" and data["tenantId"] == 122 and type(data["tenantId"]) is int
         and data["tenantName"] == "测试租户" and data["username"] == "aoteman", "PROTECTED_TENANT_OR_USER")
    need(data["targetOrigin"] == target_identity["frontendOrigin"], "BROWSER_TARGET_MISMATCH", "STALE")
    need(type(required_paths) is list and set(required_paths) >= {"login", "query", "view", "download"},
         "REQUIRED_USER_PATHS_INCOMPLETE")
    need(type(data["paths"]) is list, "USER_PATH_EVIDENCE_REQUIRED")
    paths = {}
    for path in data["paths"]:
        fields(path, "pathId entrySelector assertions screenshotPin download")
        name = text(path["pathId"])
        need(name not in paths, "DUPLICATE_USER_PATH")
        text(path["entrySelector"])
        need(type(path["assertions"]) is list and bool(path["assertions"]), "USER_ASSERTIONS_REQUIRED")
        for assertion in path["assertions"]:
            fields(assertion, "selector kind expected observed")
            text(assertion["selector"])
            need(assertion["kind"] in ("text", "visible", "image") and
                 type(assertion["observed"]) is type(assertion["expected"]) and
                 assertion["observed"] == assertion["expected"], "USER_ASSERTION_FAILED", "FAILED")
        if name == "download":
            fields(path["download"], "expectedBytes expectedSha256 actualBytes actualSha256 contentPin")
            download = path["download"]
            integer(download["expectedBytes"], 1)
            sha(download["expectedSha256"])
            need(download["expectedBytes"] == download["actualBytes"] and
                 download["expectedSha256"] == download["actualSha256"], "DOWNLOAD_CONTENT_MISMATCH", "FAILED")
        else:
            need(path["download"] is None, "UNEXPECTED_DOWNLOAD")
        paths[name] = path
    need(set(paths) == set(required_paths), "USER_PATH_MISSING_OR_UNEXPECTED")
    integer(data["blockedExternalRequests"])
    need(type(data["pageErrorCount"]) is int and data["pageErrorCount"] == 0 and
         type(data["businessFailureCount"]) is int and data["businessFailureCount"] == 0,
         "BROWSER_BUSINESS_ERROR", "FAILED")


def measure_timing(data, rto_objective, rpo_objective, evidence_pin):
    fields(data, "clockDomainId restoreStartMonotonicNs userReadyMonotonicNs recoveryPointUtc "
           "disruptionUtc clockUncertaintyMilliseconds restoreStartInvocationPin userReadyObservationPin "
           "recoveryPointEvidencePin clockEvidencePin disruptionEvidencePin")
    text(data["clockDomainId"])
    start, end = integer(data["restoreStartMonotonicNs"]), integer(data["userReadyMonotonicNs"])
    need(end >= start, "RTO_MONOTONIC_ORDER")
    uncertainty = integer(data["clockUncertaintyMilliseconds"])
    point, disruption = timestamp(data["recoveryPointUtc"]), timestamp(data["disruptionUtc"])
    need(point <= disruption, "RPO_POINT_AFTER_DISRUPTION")
    # Round up; sub-millisecond time and clock uncertainty never improve the verdict.
    rto_ms = (end - start + 999999) // 1000000
    difference = disruption - point
    microseconds = difference // __import__("datetime").timedelta(microseconds=1)
    rpo_ms = (microseconds + 999) // 1000 + uncertainty
    observations = []
    for measured, objective in ((rto_ms, rto_objective), (rpo_ms, rpo_objective)):
        if objective is not None:
            integer(objective)
        observations.append({"state": "MEASURED", "observedMilliseconds": measured,
                             "objectiveMilliseconds": objective, "evidencePins": [evidence_pin]})
    verdict = "BLOCKED" if rto_objective is None or rpo_objective is None else (
        "FAILED" if rto_ms > rto_objective or rpo_ms > rpo_objective else "PASSED")
    return observations[0], observations[1], verdict
