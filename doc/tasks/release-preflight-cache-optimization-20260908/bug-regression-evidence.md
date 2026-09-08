# Release Notes Fixture Timestamp Regression Evidence

## Bug Summary

`RuntimeControlOriginalParityTest.releaseStatusExposesCurrentReleaseNotesForCurrentEnvironmentsOnly` 间歇失败。测试连续用 `Instant.now()` 保存 old/current 发布记录，在 Windows 时钟分辨率下两条 test 记录可能得到完全相同的 `requestedAt`。

## Expected

fixture 应显式表达 `release-old-history` 早于 `release-test-notes`。生产代码在时间相同时继续使用既定 `operationId` tie-break，不因测试数据的隐含插入顺序而改变。

## Reproduction

```powershell
$env:JAVA_HOME = 'C:\Users\BJB110\.jdks\jdk-17.0.20+8'
$env:Path = "$env:JAVA_HOME\bin;$env:Path"
mvn.cmd -f backend\pom.xml test
```

## Root Cause

测试 helper `saveSuccessfulOperation` 把 `Instant.now()` 写入 `requestedAt`。目标用例假定后插入的 current 记录时间更晚，但 Windows 上两次调用可能返回相同时间；此时生产排序按已定义的 `operationId` 规则选择 `op-old-history-release`，fixture 的隐含插入先后无法被推断。

## Regression Test

只修改 tracked 测试 `RuntimeControlOriginalParityTest.releaseStatusExposesCurrentReleaseNotesForCurrentEnvironmentsOnly`，改用既有 `saveSuccessfulOperationAt` 并为 old、test current、prod current、backup current 指定清晰且互异的 UTC 时间。不修改生产 comparator。

## RED:

- `2026-09-08 12:48`：JDK 17 `mvn.cmd -f backend\pom.xml test` -> FAIL，`26 tests, 1 failure`。
- 失败断言：`$.data.testCurrentReleaseNotes.releaseTag` expected `release-test-notes`，actual `release-old-history`。
- 修复前定向复跑偶发 PASS（`1 test`），进一步证明该问题依赖系统时钟碰撞而非稳定业务错误；不能据此把原 Maven RED 判为已解决。

## GREEN:

- 定向稳定性命令连续运行 3 次：

```powershell
1..3 | ForEach-Object {
    mvn.cmd -f backend\pom.xml "-Dtest=RuntimeControlOriginalParityTest#releaseStatusExposesCurrentReleaseNotesForCurrentEnvironmentsOnly" test
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
```

- 结果：3/3 PASS；每轮 `Tests run: 1, Failures: 0, Errors: 0, Skipped: 0`。
- 全量 `mvn.cmd -f backend\pom.xml test` -> PASS；`Tests run: 26, Failures: 0, Errors: 0, Skipped: 0`，`BUILD SUCCESS`。

## Verification

JDK 17 定向测试连续 3 次通过，全量 Maven 26 个测试通过；`git diff --check` 无 whitespace error。验证没有修改生产 comparator。

## Risk

变更仅固定测试时间，不改变生产排序、API、发布逻辑或运行时数据。主要风险是时间设置仍不清晰或遗漏同一 fixture 中的环境记录，因此四条记录均使用显式且互异的 UTC 时间。

## Blockers

None.
