# 任务：修复发布说明变更项乱码

## 任务目标

- 修复运行控制台“版本变更说明”弹窗中 `变更项` 的乱码问题。
- 根因定位到维护仓发布脚本，确保后续生成的 `release-manifest.json` 与 `release-info.json` 中中文变更项在 PowerShell 5.1 下稳定为 UTF-8 正常文本。
- 补充静态回归测试，防止再次因脚本源码编码解释导致发布说明乱码。

## 当前状态

COMPLETED

## 经验门禁

- 来源：`D:\ProjectPackage\Int\IntRuoyi\docs\experience-index.md`
- 命中文档：
  - `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`
  - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
- 适用强制门禁：
  - 发布、构建、部署代码统一在 `D:\ProjectPackage\Int\IntRuoyiMaintance` 修改；业务仓只作为发布输入，不在业务仓补脚本逻辑。
  - 影响发布链路的改动必须同步验证 manifest/产物契约，不能只做页面观感修复。
  - 本次仅做本机源码与静态测试修改，不执行真实发布、服务器写入或高风险动作。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是。通过消除 PowerShell 5.1 对无 BOM 脚本中文字面量的依赖，从源头修复发布说明乱码。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 发布说明变更项中文正常显示 -> Given 发布脚本在 PowerShell 5.1 环境执行 / When 生成 release changeSet / Then "发布包" 与 "组件范围" 中文项写入 manifest 时不出现乱码。`
- `BDD: 前端静态发布说明与 manifest 保持一致 -> Given 发布脚本生成 release-info.json 与 release-manifest.json / When 写入相同 changeSet / Then 两处变更项使用同一安全文本来源且不会因源码编码解释而变成乱码。`

## 里程碑

1. M1：创建任务文档、执行日志并记录请求。`COMPLETED`
2. M2：定位乱码根因并设计正式修复。`COMPLETED`
3. M3：修改发布脚本，移除对中文字面量的风险依赖。`COMPLETED`
4. M4：补充静态回归测试并完成验证。`COMPLETED`
5. M5：回写任务证据并完成收尾。`COMPLETED`

## 预期验证

- `ops/deploy/publish-int-ruoyi.ps1` 的 `New-ReleaseChangeSetManifest` 不再直接依赖中文字面量。
- 新增或更新的脚本测试能覆盖变更项中文编码安全契约。
- 现有 `publish_release_info_contract.test.mjs` 与新增 Python 测试通过。

## 风险与关注点

- 当前维护仓脚本文件为 UTF-8 无 BOM；在 Windows PowerShell 5.1 下直接使用中文字面量存在被按 ANSI 误读的风险，不能用“改一两行文案”掩盖。
- 变更项既用于 `release-info.json`，也用于 `manifest.json`，修复必须保证两处共用同一来源，避免一处正常一处乱码。

## Final Verification

- `python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_package_slimming.py D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_sql_preflight_gate.py -q` -> `PASS`
- `node D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\publish_release_info_contract.test.mjs` -> `PASS`
- `python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260628-release-change-items-garbled-fix --mode preview` -> `status: ready`，仅保留 `task.md` 与 `execution-log.md`

## 当前阻塞

- 无。
