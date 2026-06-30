# 20260630 build-release 本地运行态保护门禁

## Task Goal

收口维护控制台真实 `build-release` 期间本机 `48081` 运行态会被旁路本地重启入口切回 `E:\Int\CacheData\IntRuoyi\runtime\backend-*.jar` 的风险，在维护仓发布脚本层补齐正式门禁，确保构建窗口内主线本地运行态不会被自动或误触发的本地重启动作抢占。

## Scope

- 维护仓：`D:\ProjectPackage\Int\IntRuoyiMaintance`
- 改动对象：`ops\deploy\publish-int-ruoyi.ps1` 及其契约测试
- 验证范围：本机 `build-release` 过程对 `E:\Int\CacheData\IntRuoyi\runtime\local-runtime-restart.guard` 的持有/释放行为

## Non-Scope

- 不修改业务后端或前端功能
- 不新增 fallback、兼容分支或静默降级
- 不执行正式服、备份服写入

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
  - 发布链路问题优先补成脚本门禁，不依赖人工记忆避免重复踩坑。
- `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
  - 发布类改动需 fail fast，不能用临时绕过掩盖运行态冲突。
- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
  - 本文件仅保留事后记忆；本次正式约束应直接落到前置脚本/测试中。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是；把本地运行态保护下沉到 `build-release` 脚本窗口，而不是依赖手工先写 guard。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

BDD: build-release 自动保护本地运行态 -> Given 本机主线 `48081` 正在为真实本地验证服务 When 维护控制台执行 `build-release` Then 发布脚本必须自动持有 `local-runtime-restart.guard`，阻止旁路本地重启脚本抢占运行态。

BDD: build-release 结束后释放自持有 guard -> Given 发布脚本为本次 `build-release` 新建了 guard When 构建成功或失败结束 Then 脚本必须只释放自己创建的 guard，不得误删外部已有 guard。

## Milestones

1. 建立任务台账并记录门禁。`COMPLETED`
2. 补充脚本契约测试，先锁定 guard 持有/释放约束。`IN_PROGRESS`
3. 最小修改 `publish-int-ruoyi.ps1` 实现 guard 门禁。`PENDING`
4. 跑定向测试并记录 RED/GREEN。`PENDING`
5. 回写结论并继续当前排产冒烟。`PENDING`

## Expected Verification

- `python -X utf8 -m pytest scripts/tests/test_publish_release_lock_cleanup.py -q`
- `python -X utf8 scripts/verify_contracts.py`
- 定向只读核对 `publish-int-ruoyi.ps1` 在 `build-release` 下持有/释放 `local-runtime-restart.guard`

## Current Status

BLOCKED：用户已切换到更高优先级的测试服 DCC 受控浏览报错修复重发版；本任务当前已完成问题定界，但脚本 guard 门禁尚未继续实现，先显式阻塞，待用户恢复优先级后续做。
