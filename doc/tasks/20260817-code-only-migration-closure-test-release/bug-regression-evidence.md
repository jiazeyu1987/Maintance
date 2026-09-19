# Bug Regression Evidence

## Bug Summary And Expected Behavior

`code-only` 发布预检先生成 passed 计划，PowerShell 调用方随后过滤待执行的 `type=data` migration，导致剩余 APPLY migration 的传递依赖闭包被破坏并在测试服写入阶段失败。预期行为是在任何远端写入前由 scope-aware 计划明确阻塞不闭包的发布。

## Reproduction

待 RED 阶段补充精确命令与失败断言。

## Root Cause

待代码与调用链复核后补充。

## Regression Test

待 RED 阶段补充。

## RED / GREEN / Risk / Blockers

待执行。
