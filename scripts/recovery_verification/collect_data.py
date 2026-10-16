"""Read-only real MySQL/S3 inventory. Credentials are environment references only."""
import base64
import datetime as dt
from decimal import Decimal
import hashlib
import os
import re
from urllib.parse import urlsplit

from core import fields, need, text, integer, canonical, digest, VerificationError


def secret_environment(name):
    text(name)
    need(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name), "SECRET_ENV_REFERENCE_REQUIRED")
    need(name in os.environ and bool(os.environ[name]), "SECRET_REFERENCE_UNAVAILABLE")
    return os.environ[name]


def identifier(value):
    need(type(value) is str and re.fullmatch(r"[A-Za-z0-9_]+", value), "SQL_IDENTIFIER_REQUIRED")
    return "`" + value + "`"


def encode_cell(value):
    if value is None or type(value) in (str, int, bool):
        return value
    if type(value) is bytes:
        return {"type": "bytes", "base64": base64.b64encode(value).decode("ascii")}
    if type(value) in (dt.date, dt.datetime, dt.time):
        return {"type": type(value).__name__, "value": value.isoformat()}
    if type(value) is dt.timedelta:
        return {"type": "timedelta", "microseconds": value // dt.timedelta(microseconds=1)}
    if type(value) is Decimal:
        return {"type": "decimal", "value": str(value)}
    if type(value) is float:
        return {"type": "float", "hex": value.hex()}
    raise VerificationError("UNSUPPORTED_DATABASE_VALUE_TYPE")


def row_digest(row):
    return digest(canonical([encode_cell(value) for value in row]))


def multiset_digest(row_hashes):
    return digest(canonical(sorted(row_hashes)))


def validate_data_settings(settings):
    fields(settings, "mysql s3 derivedInventoryPin derivedObservers")
    mysql, s3 = settings["mysql"], settings["s3"]
    fields(mysql, "host port database username passwordEnv referenceSpecs connectTimeoutSeconds")
    text(mysql["host"])
    integer(mysql["port"], 1)
    need(mysql["port"] <= 65535, "MYSQL_PORT_RANGE")
    identifier(mysql["database"])
    text(mysql["username"])
    integer(mysql["connectTimeoutSeconds"], 1)
    need(type(mysql["referenceSpecs"]) is list and bool(mysql["referenceSpecs"]), "REFERENCE_SPECS_REQUIRED")
    for spec in mysql["referenceSpecs"]:
        fields(spec, "table bucket keyColumn deletedColumn domainColumn allowedDomains")
        for key in ("table", "keyColumn", "deletedColumn", "domainColumn"):
            identifier(spec[key])
        text(spec["bucket"])
        need(type(spec["allowedDomains"]) is list and bool(spec["allowedDomains"])
             and all(type(value) is str and value for value in spec["allowedDomains"]), "REFERENCE_DOMAIN_SCOPE")
    fields(s3, "endpointUrl region accessKeyEnv secretKeyEnv scopes timeoutSeconds")
    endpoint = urlsplit(text(s3["endpointUrl"]))
    need(endpoint.scheme in ("http", "https") and bool(endpoint.hostname) and not endpoint.username
         and not endpoint.password and not endpoint.query and not endpoint.fragment, "S3_ENDPOINT_REQUIRED")
    text(s3["region"])
    integer(s3["timeoutSeconds"], 1)
    need(type(s3["scopes"]) is list and bool(s3["scopes"]), "OBJECT_SCOPE_REQUIRED")
    seen = []
    for scope in s3["scopes"]:
        fields(scope, "bucket prefix")
        text(scope["bucket"])
        need(type(scope["prefix"]) is str, "OBJECT_PREFIX_REQUIRED")
        need(not any(scope["bucket"] == bucket and (scope["prefix"].startswith(prefix) or
                     prefix.startswith(scope["prefix"])) for bucket, prefix in seen), "OVERLAPPING_OBJECT_SCOPES")
        seen.append((scope["bucket"], scope["prefix"]))
    # Resolve every credential reference before the first network connection, without logging it.
    for name in (mysql["passwordEnv"], s3["accessKeyEnv"], s3["secretKeyEnv"]):
        secret_environment(name)


def collect_mysql(settings, expected_database_id, deadline):
    fields(settings, "host port database username passwordEnv referenceSpecs connectTimeoutSeconds")
    import pymysql
    timeout = min(integer(settings["connectTimeoutSeconds"], 1), max(1, int(deadline.remaining())))
    identifier(settings["database"])
    connection = pymysql.connect(host=text(settings["host"]), port=integer(settings["port"], 1),
                                 database=settings["database"], user=text(settings["username"]),
                                 password=secret_environment(settings["passwordEnv"]),
                                 connect_timeout=timeout, read_timeout=timeout, write_timeout=timeout,
                                 charset="utf8mb4", autocommit=False)
    tables, references = [], []
    try:
        with connection.cursor() as cursor:
            cursor.execute("SHOW FULL TABLES")
            table_rows = cursor.fetchall()
            need(table_rows and all(row[1] == "BASE TABLE" for row in table_rows),
                 "UNSUPPORTED_VIEW_SCOPE")
            cursor.execute("SELECT @@server_uuid, DATABASE()")
            uuid, database = cursor.fetchone()
            database_id = str(uuid) + "/" + str(database)
            need(database_id == expected_database_id, "MYSQL_TARGET_IDENTITY_MISMATCH")
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            cursor.execute("START TRANSACTION WITH CONSISTENT SNAPSHOT, READ ONLY")
            names = sorted(row[0] for row in table_rows)
            specs = {}
            need(type(settings["referenceSpecs"]) is list and bool(settings["referenceSpecs"]),
                 "REFERENCE_SPECS_REQUIRED")
            for spec in settings["referenceSpecs"]:
                fields(spec, "table bucket keyColumn deletedColumn domainColumn allowedDomains")
                need(spec["table"] in names and spec["table"] not in specs, "REFERENCE_TABLE_SCOPE")
                specs[spec["table"]] = spec
            for name in names:
                deadline.remaining()
                quoted = identifier(name)
                cursor.execute("DESCRIBE " + quoted)
                described = cursor.fetchall()
                columns = [column[0] for column in described]
                cursor.execute("SHOW CREATE TABLE " + quoted)
                ddl = cursor.fetchone()[1]
                cursor.execute("SHOW TABLE STATUS WHERE Name = %s", (name,))
                status = cursor.fetchone()
                need(status and status[1] == "InnoDB", "NONTRANSACTIONAL_TABLE_UNSUPPORTED")
                # SHOW CREATE's live AUTO_INCREMENT counter is part of exact structure evidence.
                cursor.execute("SELECT * FROM " + quoted)
                hashes = []
                spec = specs.get(name)
                if spec is not None:
                    need(all(spec[key] in columns for key in ("keyColumn", "deletedColumn", "domainColumn")),
                         "REFERENCE_COLUMN_UNAVAILABLE")
                    indexes = {key: columns.index(spec[key]) for key in ("keyColumn", "deletedColumn", "domainColumn")}
                while True:
                    deadline.remaining()
                    rows = cursor.fetchmany(1000)
                    if not rows:
                        break
                    for row in rows:
                        hashed = row_digest(row)
                        hashes.append(hashed)
                        if spec is not None:
                            deleted = row[indexes["deletedColumn"]]
                            need(type(deleted) in (int, bool) and deleted in (0, 1), "REFERENCE_DELETE_STATE_UNKNOWN")
                            references.append({"table": name, "rowSha256": hashed, "bucket": spec["bucket"],
                                               "key": text(row[indexes["keyColumn"]]), "deleted": bool(deleted),
                                               "domain": text(row[indexes["domainColumn"]])})
                tables.append({"name": name, "schemaSha256": digest(ddl.encode("utf-8")),
                               "rowCount": len(hashes), "dataSha256": multiset_digest(hashes)})
            # Check schema and server identity again; the read transaction does not lock DDL.
            cursor.execute("SHOW FULL TABLES")
            need(sorted(cursor.fetchall()) == sorted(table_rows), "DATABASE_SCOPE_CHANGED_DURING_READ", "STALE")
            for table in tables:
                cursor.execute("SHOW CREATE TABLE " + identifier(table["name"]))
                need(digest(cursor.fetchone()[1].encode("utf-8")) == table["schemaSha256"],
                     "DATABASE_SCHEMA_CHANGED_DURING_READ", "STALE")
            cursor.execute("SELECT @@server_uuid, DATABASE()")
            uuid_after, database_after = cursor.fetchone()
            need((uuid_after, database_after) == (uuid, database), "MYSQL_IDENTITY_CHANGED", "STALE")
        connection.rollback()
    finally:
        connection.close()
    return database_id, tables, references


def collect_objects(settings, deadline):
    fields(settings, "endpointUrl region accessKeyEnv secretKeyEnv scopes timeoutSeconds")
    import boto3
    from botocore.config import Config
    timeout = min(integer(settings["timeoutSeconds"], 1), deadline.remaining())
    client = boto3.client("s3", endpoint_url=text(settings["endpointUrl"]), region_name=text(settings["region"]),
                          aws_access_key_id=secret_environment(settings["accessKeyEnv"]),
                          aws_secret_access_key=secret_environment(settings["secretKeyEnv"]),
                          config=Config(connect_timeout=timeout, read_timeout=timeout,
                                        retries={"total_max_attempts": 1}))
    objects = []
    try:
        for scope in settings["scopes"]:
            fields(scope, "bucket prefix")
            initial = {}
            deadline.remaining()
            paginator = client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=scope["bucket"], Prefix=scope["prefix"]):
                deadline.remaining()
                for item in page.get("Contents", []):
                    key = item["Key"]
                    need(key not in initial, "S3_DUPLICATE_LIST_KEY")
                    initial[key] = (item["Size"], item["ETag"], item["LastModified"].isoformat())
            for key, listed in sorted(initial.items()):
                deadline.remaining()
                result = client.get_object(Bucket=scope["bucket"], Key=key, IfMatch=listed[1])
                hashed, size = hashlib.sha256(), 0
                body = result["Body"]
                try:
                    while True:
                        deadline.remaining()
                        raw = body.read(1024 * 1024)
                        if not raw:
                            break
                        hashed.update(raw)
                        size += len(raw)
                finally:
                    body.close()
                need(size == listed[0] == result["ContentLength"] and result["ETag"] == listed[1],
                     "S3_CONTENT_CHANGED", "STALE")
                objects.append({"bucket": scope["bucket"], "key": key, "bytes": size, "sha256": hashed.hexdigest()})
            final = {}
            for page in paginator.paginate(Bucket=scope["bucket"], Prefix=scope["prefix"]):
                deadline.remaining()
                for item in page.get("Contents", []):
                    need(item["Key"] not in final, "S3_DUPLICATE_LIST_KEY")
                    final[item["Key"]] = (item["Size"], item["ETag"], item["LastModified"].isoformat())
            need(initial == final, "S3_INVENTORY_CHANGED_DURING_READ", "STALE")
    finally:
        client.close()
    return objects


def collect_data(settings, identity, deadline):
    validate_data_settings(settings)
    from native_observe import collect_service
    from core import json_pin, same
    binding = json_pin(identity["objectBindingPin"], deadline)
    same(binding["targetIdentityPin"], identity["targetIdentityPin"], "OBJECT_BINDING_TARGET_MISMATCH")
    need(binding["role"] == "minio" and binding["endpointUrl"] == settings["s3"]["endpointUrl"],
         "S3_ENDPOINT_TARGET_MISMATCH")
    database_before = (collect_mysql(settings["mysql"], identity["databaseId"], deadline)
                       if binding['schemaVersion']=='RecoveryServiceBinding/v1' else None)
    def collect_primary(before):
        database = database_before if database_before is not None else collect_mysql(settings["mysql"], identity["databaseId"], deadline)
        return database, collect_objects(settings["s3"], deadline)
    ((database_id, tables, references), objects), object_after = collect_service(
        identity["objectBindingPin"], deadline, collect_primary)
    from derived_state import collect_derived
    derived = collect_derived(settings["derivedInventoryPin"], settings["derivedObservers"], identity, deadline)
    result = {"databaseId": database_id, "tables": tables, "objectScopes": settings["s3"]["scopes"],
              "objects": objects, "references": references, "referenceSpecs": settings["mysql"]["referenceSpecs"],
              "objectTarget": object_after, "derivedInventoryPin": settings["derivedInventoryPin"], "derived": derived}
    from integrity import data_snapshot
    data_snapshot(result)
    return result
