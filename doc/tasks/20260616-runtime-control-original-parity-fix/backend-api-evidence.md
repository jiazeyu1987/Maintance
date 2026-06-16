# Backend API Evidence

## Scope

- `backend/src/main/java/com/intruoyi/maintenance/runtime/RuntimeControlService.java`
- `backend/src/main/java/com/intruoyi/maintenance/runtime/RuntimeControlOperationAction.java`
- `backend/src/test/java/com/intruoyi/maintenance/runtime/RuntimeControlOriginalParityTest.java`

## Contract

- `GET /admin-api/infra/runtime-control/release-status` must expose original `testCurrentReleaseTag` and `latestTestedReleaseTag`.
- High-risk operation requests must reject unsupported fields for the selected action.
- `mark-release-tested` must bind to current test environment releaseTag.
- Restore candidates require DCC `chainStatus=COMPLETE`.

## Evidence

- `RuntimeControlOriginalParityTest#releaseStatusAndMarkTestedUseCurrentTestReleaseTagLikeOriginal` 覆盖 `testCurrentReleaseTag/latestTestedReleaseTag` 与 `mark-release-tested` 服务端绑定当前测试服版本。
- `RuntimeControlOriginalParityTest#unsupportedActionFieldsAreRejectedLikeOriginal` 覆盖不支持字段 fail fast。
- `RuntimeControlOriginalParityTest#restoreCandidateRequiresCompleteDccChainLikeOriginal` 覆盖 DCC `chainStatus` 非 `COMPLETE` 阻断。
- `mvn -f backend/pom.xml -Dtest=RuntimeControlOriginalParityTest test` -> PASS，7 tests / 0 failures。
- `mvn -f backend/pom.xml test` -> PASS，12 tests / 0 failures。
