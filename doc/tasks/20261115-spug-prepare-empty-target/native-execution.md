# Native preparation

Goal: implement the local Linux executor for the fixed .59 preparation action, without executing it remotely during development.

Milestones: define explicit private installation configuration; RED tests for unsafe cleanup and ordering; implement preparation, cleanup and native initialization; run focused regression and report limitations.

Experience gates: UTF-8; no secrets in output; dependencies and task state outside cleanup; preserve all mounts and NAS; exact native identities; no shell commands from browser; no fake READY; existing recovery registration must consume new identities. No fallback, swallowed errors or temporary bypass.

BDD: Given an installed .59 plan and its matching preview digest, When dependencies are missing, Then fail before cleanup. Given cleanup contains a mount or protected path, When planning, Then refuse. Given matching native service templates and images, When initializing, Then create fresh resources, prove empty data and return actual identities for registration.

Status: ready_for_parent_review. Local implementation and focused tests complete; no remote preparation, deployment or acceptance has been performed.

## BDD / TDD evidence

- RED: the initial test import failed because prepare_target_native did not exist. GREEN: initial filesystem safeguards and identity mapping passed.
- RED: new owner nested identities and failure-stage tests failed (missing run_stages, stale image binding). GREEN: identity substitution and persisted FAILED stage events; 8 tests passed.
- RED: fresh-owner projection, repeated resource selection and real control CLI tests failed (missing functions). GREEN: 11 tests passed.
- RED: retained dependencies could not be reused after deleting their originals. GREEN: permanent dependency manifest plus explicit retained pins; 12 tests passed.
- RED: current control configuration contract and removal of a container with a protected read-only bind failed. GREEN: real control reader accepts the new document; container removal uses `docker rm` without `-v`, leaving preserved host files untouched.
- Final GREEN / REGRESSION: bundled Python `-X utf8 -m unittest ops.spug.test_prepare_target_native` -> 14 tests PASS, no skipped tests.
- Tests cover real local file operations, error ordering and actual existing control JSON/argparse contracts. Docker-boundary unit tests use controlled command responses to check command selection; they do not claim a Docker/server acceptance run. Linux root/custody enforcement is only substituted in the Windows contract unit test, never in product code.

## Interface and result

`handle(payload, emit)` accepts `{configurationPin, action, request}`. Preview returns its public plan. Execute emits stage events and a result; query accepts `operationId` and returns the persisted status/result. Browser inputs contain only operation ID, application ID, recovery point reference, preview digest and confirmation.

Preview fields: `host`, `applicationId`, `recoveryPointRef`, `cleanupSummary`, `preserveSummary`, `stages`, `planDigest`.

Successful native result is **INITIALIZED**, not READY. It includes `targetConfigRef`, `sourceConfigRef`, `ownerPin`, `controlPin`, `registrationPin`, `registrationSha256`, `engineSelectionRef`, `progressRoot`, `pythonPath`, `listenAddress`, `listenPort`, `observed`, and the three stage results. Spug must publish its local target bindings and check authenticated selections before returning READY. The preparation code never starts a restore.

The control runs `python -B control_entry.py serve --config-pin <JSON>` in the dedicated `spug-prepare59-restore.service`. `taskRoot` is the preparation operation directory; `registry/applications`, `registry/points`, and `ledger` are its children, matching `recovery_control_smallapp_native.Native.configuration`. The registration retains the installed application's metadata and uses only the new target in `allowedRestoreTargets`.

## Native private installation configuration

This file is private administrator configuration, never browser input. The installation process must obtain values from the existing measured .59 installation, Docker inspect and selected NAS backup; placeholder values below are not deployable values.

| Field | Source / meaning |
| --- | --- |
| `host` | Exactly `172.30.30.59`. |
| `machineId`, `dockerEngineId`, `dockerPath`, `dockerRoot` | Actual `/etc/machine-id`, Docker daemon ID, executable and DockerRootDir. Existing observation places DockerRootDir at `/mnt/intruoyi-data/docker-engine`. |
| `dataRoot` | Actual local data mount; all cleanup directories and new target directories must be descendants. |
| `toolRoot`, `stateRoot` | Permanent private directories excluded from cleanup; no symlinks. Installed Python and native module must already run inside toolRoot. |
| `hostReservationRoot` | Exactly `/var/lib/spug-restore-resources`, shared with current restore admission. |
| `sourceLockPaths` | Explicit actual source locks if this installation shares source activity; no invented parallel lock. |
| `archiveRoots` | Actual accessible NAS archive roots, always preserved. |
| `cleanup` | Exact `directories`, `containerIds` (full IDs), `volumeNames`, `networkIds` (full IDs), `serviceNames` selected for initial cleanup. No shell or wildcard. |
| `dependencies` | Explicit file copies: `{source, destination, mode?, uid?, gid?, rewriteJson?}`. Destination is toolRoot-relative. File permissions/owners are preserved unless explicitly configured. JSON references needing relocation are listed leaf-first with rewriteJson=true. NAS files must not be relocated or rewritten. |
| `ownerTemplatePath`, `ownerTemplateTargetRef` | Actual current RecoveryMinimalConfiguration/v1 and its target. Existing main owner is accepted: the generator removes mainApplication/replacement and target-history policies for the newly created target; no old target identity is reused. |
| `formalModuleDirectory` | Retained actual formal engine module directory under permanent tools. |
| `targetPrefix`, `subnet`, `templateSubnet`, `frontendPort` | New resource prefix, dedicated IPv4 subnet, prior template subnet for address rewriting, host loopback frontend port. |
| `database`, `mysqlCaseRule`, `mysqlClientFile`, `redisSecret` | Existing database name/case rule, container MySQL credentials path, toolRoot-relative Redis secret file. Secrets are kept in private files. |
| `templateDataPaths` | Old actual mysql/minio/redis host data paths, used solely to replace references in the new owner. |
| `resourceBudget` | Current engine's RestoreResourceBudget/v1 with actual memory limits and disk paths covering dataRoot, stateRoot and retained tools. Reuse observed installation requirements; do not point to removed operation directories. |
| `points` | Admitted recoveryPointRef -> `{applicationId, sourceConfigRef, imageArchivePin, roleImages}`. Image archive path must be the accessible archive copy on this target, not a former source capture-staging pathname. roleImages maps exactly the five roles to image IDs from that backup. |
| `services` | Exactly five explicit service specifications derived from Docker inspect and backup configurations; see below. |
| `control` | `{templatePath, registrationPath, serviceName, engineDirectory, pythonPath, listenAddress, listenPort}`. serviceName is fixed to spug-prepare59-restore.service. Template is actual SmallAppExecutionServiceConfig/v2, registration is actual ApplicationRegistration/v1. |

Service shape (repeat for mysql, minio, redis, backend, frontend):

```json
{
  "role": "mysql",
  "memoryBytes": 4294967296,
  "templateIp": "172.28.140.32",
  "dataDestination": "/var/lib/mysql",
  "dataOwnership": [999, 999],
  "environment": ["MYSQL_DATABASE=ruoyi-vue-pro"],
  "binds": [{"source": "private/mysql-client.cnf", "destination": "/run/recovery/mysql-client.cnf"}],
  "command": ["--lower_case_table_names=1"]
}
```

Use each actual image's UID/GID and original startup specification; the numbers above are illustrative. Environment and container arguments are installer-private values from the approved template, never an arbitrary host command. Additional optional keys are `user`, `workingDirectory`, `entrypoint`, `healthCommand`. Application configuration binds use `rewriteAddresses: true`; the copied target configuration receives the new IPs and its owner Pin is recalculated. Application startup remains stopped. MySQL/Redis alone start and are checked empty; MinIO's new direct bind directory stays physically empty.

## Required retained files and first installation

The feature installer must retain the complete working Python runtime (not only its executable), the selected existing engine package and its Python dependencies, this native module, and its private configuration in toolRoot before invoking preview. The engine package must contain the existing control_entry.py entry, recovery/repository programs and their adjacent imported modules. No package manager is invoked by preparation.

Dependencies then collect the current application's private credentials and actual MySQL/Redis/backend/frontend configuration files, plus any referenced source/control/catalogue configuration files that otherwise live inside cleanup. Existing control `programPins`, authentication reference, source configurations and archive catalogues must point to retained files; dependency JSON relocation recalculates their Pins. `formalModuleDirectory` must retain the current SQL/S3/readback modules used by the actual recovery engine. Do not substitute only a generic owner shell: preserve current `sources`, application/dataPolicy, credentials, runtime settings and archive configuration.

The native module snapshots current owner/control/registration templates into `toolRoot/prepared-inputs` before cleanup. Its manifest makes those retained files the normal source for subsequent preparation; removed originals are not rediscovered and tampered retained copies fail explicitly. The next operation uses only initial explicit cleanup plus the last preparation's recorded container IDs, network ID and data directory. Successfully enumerated absent old IDs are skipped; Docker errors are not interpreted as absence.

Current implementation includes the real Linux commands and control publication path. This task has not populated or installed the machine-private configuration, nor run cleanup on .59. That remaining deployment prerequisite must be stated to users; local tests alone do not prove server READY.
