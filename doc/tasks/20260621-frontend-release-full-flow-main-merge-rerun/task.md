# 任务：主程序合并后重新走页面发布全链路

## 任务目标

在主程序合并新代码后，重新通过运行控制台前端页面，严格执行一次“构建发布包 -> 部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服”的完整链路，确认当前主程序基线仍然满足真实页面发布流程。全过程禁止用接口直调替代页面提交；遇到任一步失败，必须先记录到任务文档，再修复并从页面重走，直到单次链路一次性通过。

## 上一任务检查

- 上一维护仓任务：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260621-frontend-release-full-flow-rerun\task.md`
- 状态：`COMPLETED`
- 处理：上一任务完成的是“基于现有 v6 证据和远端运行态的完成审计”，证明旧链路曾完整走通；本任务是因主程序合并后担心当前基线已发生变化而重新发起的真实页面全链路重跑，属于新的高风险验证任务，需单独建档。

## 用户要求与执行边界

- 用户要求：
  - 主程序合并修改了部分代码后，重新再走一遍真实页面发布流程
  - 仍然必须按页面前端点击操作走完整链路
  - 禁止直接调接口替代页面动作
  - 每遇到问题先记录到任务文档，修复后继续从页面走
- 当前任务边界：
  - 当前验证目标基线已更新为 clean release backend worktree `D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\ruoyi-vue-pro` 提交 `a72602e2f0`（在 `3ace5094ec` 基础上继续纳入打印策略菜单冲突修复提交 `ca023336e9` 与回归证据提交 `a72602e2f0`）
  - 当前验证目标基线是业务前端 `D:\ProjectPackage\Int\IntRuoyi\yudao-ui-admin-vue3` 最新 `int_main` 提交 `37359a074`
  - 维护仓 `D:\ProjectPackage\Int\IntRuoyiMaintance` 当前分支为 `int_main`，存在 `backup-ops` 相关未提交改动，但 `ops/deploy` 与运行控制台页面发布链路本次未发现未提交更改
  - 高风险动作前必须在 `execution-log.md` 中记录 `GREEN: experience-preflight -> PASS`

## 经验门禁

- `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`
  - 命中文档：
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
    - `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
    - `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
    - `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
- 本任务强制门禁摘录：
  - 构建发布包必须通过运行控制台页面按钮真实提交，命令行只允许做只读核验、失败排查和脚本/测试辅助。
  - 发布前必须确认当前运行控制台实例可用、当前业务前后端基线明确、目标环境明确、目标 `releaseTag` 唯一。
  - 每次主程序发布输入发生变化后，必须使用新的 `releaseTag` 重建并从测试服开始整链重走。
  - 发布验证不能只看健康检查，必须同时核 operation、发布包 manifest、远端 `.env`、运行镜像、页面入口和受保护边界。
  - 正式服和备份服都属于高门禁环境，必须使用已测试通过发布包，并保持 `PROD` 确认语义。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。
- `是否从根因和长期维护角度解决`：是。若当前主程序合并引入任何发布链路问题，必须修正式代码/脚本/契约后再从页面重跑。
- `是否存在临时补丁或绕过`：否。

## BDD 场景

- `BDD: 合并后页面真实发布全链路仍可通过 -> Given 主程序前后端已合并新代码且运行控制台可访问 / When 在页面上依次执行构建发布包、部署测试服、标记测试通过、上线正式服、上线备份服 / Then 每一步都必须由真实页面动作触发并最终成功。`
- `BDD: 合并后若链路失败必须先记录再修复重走 -> Given 任一步页面动作或后台执行因当前主程序基线失败 / When 记录失败证据并修复 / Then 必须先把失败与根因写入执行日志，再从页面重新走完整链路直到一次性通过。`

## 里程碑

1. 建立本任务文档，确认上一任务已完成并锁定当前业务前后端与维护仓基线。`DONE`
2. 完成 `experience-preflight`、本机控制台可用性检查与页面提交前预检。`DONE`
3. 通过页面真实执行构建发布包并完成候选包核验。`IN_PROGRESS`
4. 通过页面真实部署测试服并完成只读运行态验证。`TODO`
5. 通过页面真实标记测试通过并确认恢复候选/测试结论。`TODO`
6. 通过页面真实上线正式服并完成运行态与受保护边界验证。`TODO`
7. 通过页面真实上线备份服并完成运行态与受保护边界验证。`TODO`
8. 汇总本轮问题、修复、最终通过证据并执行收尾预览。`TODO`

## 预期验证

- `execution-log.md` 在任何真实写入前存在 `GREEN: experience-preflight -> PASS`
- 明确记录本轮使用的新 `releaseTag` 以及前后端/维护仓基线
- build/test/mark-tested/prod/backup 每一步都存在真实页面触发的 operation ID、状态和日志路径
- 测试服/正式服/备份服远端 `.env` 与运行镜像都切到本轮新 `releaseTag`
- 正式服与备份服 `config_id=28 AND path LIKE 'showroom/%'` 的受保护 URL 边界未漂移
- 若发现问题，存在对应 BDD、失败记录、修复记录和整链重跑证据

## 当前状态

IN_PROGRESS：`2026-06-22` 真实页面 `deploy-test(v4)` 暴露的 `20260618_mes_edhr_label_print_queue.sql` 菜单主键冲突，已在业务后端任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-label-print-menu-id-collision-fix\` 按严格 TDD 修复并通过回归，且修复提交已落盘为 `6d96efef31`。只读证据确认 `900272-900279` 被独立表单占用、`900280-900283` 被其他 eDHR 菜单占用，因此 label print 菜单已切换到独立的 `900320-900331` 号段；`pytest`、迁移策略门禁与真实页面 `build-release(v5)` 均已通过，NAS 产物目录为 `Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v5`。

`2026-06-22` 继续在真实页面预览 `deploy-test(v5)` 时，测试服预览显示 `-RemoteReleaseRoot /var/lib/docker/intruoyi-releases -RemoteDataRoot /var/lib/docker/intruoyi-data/runtime-data -RemoteDataDiskMount /var/lib/docker -RemoteDataDiskDevice /dev/vdb -RemoteMinioContainer ragflow_compose-minio-1`。这组参数一度被怀疑为漂移，但随后已通过只读核对 `backend/src/main/resources/application.yaml`、`ops/deploy/publish-int-ruoyi.ps1` 环境映射、历史真实通过证据以及测试服 `show-int-ruoyi-remote-status.ps1` 运行态验证为当前测试服真实基线，实机状态返回 `running` 且当前运行标记为 `release-20260621-page-full-flow-mainmerge-v4`。因此本轮未出现新的配置阻塞，真实页面已继续提交 `deploy-test(v5)`。

`2026-06-22` 新的真实阻塞点出现在 `deploy-test(v5)` 远端执行中：operation `op-2026-06-21T224939775740400Z-71e88cac-530c-41f0-a189-d2ca59292b50` 在测试服 required SQL `20260618_mes_edhr_oq_pq_execution_deviation.sql` line 357 因 `Invalid eDHR OQ/PQ button menu definition; cannot merge tenant package menu_ids` 失败。日志同时确认此前的 `20260618_mes_edhr_label_print_queue.sql` 已成功跨过，说明当前主阻塞已切换到新的 OQ/PQ 菜单定义冲突。按任务门禁，下一步必须先在业务后端按严格 TDD 修复该根因；由于发布包输入将再次变化，旧标签 `release-20260621-page-full-flow-mainmerge-v5` 不可继续使用，修复后必须以新的 `releaseTag` 从真实页面重新执行 `build-release -> deploy-test`，再继续后续链路。

`2026-06-22` 上述 OQ/PQ 根因已在业务后端任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-oq-pq-menu-definition-fix\` 按严格 TDD 修复完成并正式提交。当前只读源码与测试服真实 `system_menu` 共同证明：旧号段 `900290-900295` 中，`900290-900292` 与其他 eDHR SQL 存在直接复用，`900293-900295` 已被 `eDHR统一变更` 占用，因此 OQ/PQ 菜单整体切换到独立未占用的 `900332-900337`，并加入 `tmp_mes_edhr_oq_pq_legacy_menu_map` 吸收测试库已经落下的旧 OQ/PQ 页面/按钮残留。当前业务修复已通过 `python -X utf8 -m pytest ...test_edhr_oq_pq_schema_sql.py -q`、`python -X utf8 ...run-release-migration-policy-gate.py --sql-root ...` 与 bug regression validator，提交已落盘为 `0d82319b98`（功能修复）和 `3ace5094ec`（补充回归证据）。由于发布包输入已再次变化，旧标签 `release-20260621-page-full-flow-mainmerge-v5` 已失效；下一步必须通过真实页面以新的 `releaseTag`（建议 `release-20260621-page-full-flow-mainmerge-v6`）重新执行 `build-release -> deploy-test`，再继续后续链路。

`2026-06-22` 真实页面已按新输入基线重新执行 `build-release(v6)`，operation `op-2026-06-21T232456287004700Z-51059473-149c-41e4-8fe3-14e2d4a9d7cb` 最终 `SUCCESS`；本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v6\` 已生成 `manifest.json`、`release-manifest.json` 与 `intruoyi-images_release-20260621-page-full-flow-mainmerge-v6.tar`，NAS 发布目录为 `Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v6`。`manifest.json` 确认 `releaseTag=release-20260621-page-full-flow-mainmerge-v6`、`publishScope=code-only`，并记录 backend 源提交 `3ace5094ec7768237e7249b876a4eca67dad5e2a`、admin frontend 源提交 `37359a074cedcc0a341f17cb0abdd1a71f838731`。

`2026-06-22` 继续准备 `deploy-test(v6)` 前，只读核对 `manifest.json sourceRepos` 与当前源码仓状态时发现新的高风险前置差异：backend 与 admin frontend 在候选包中都被标记为 `dirty=true`。当前 `git status --short` 证明业务后端存在 DCC 文件名识别相关未提交改动（`DccControlledFileProjectCodeRecognitionService*` 等），业务前端存在 DCC 受控预览相关未提交改动（`src/views/dcc/controlled-file/detail/index.vue` 等）。影响：`release-20260621-page-full-flow-mainmerge-v6` 并非“纯已提交 merged main 基线”候选包，而是混入未提交 DCC 工作树改动的 dirty baseline；按 fail-fast 门禁，在未明确这些 dirty 改动是否应纳入本轮真实发布链路前，不应继续 `deploy-test -> mark-tested -> prod -> backup`。

`2026-06-22` 为消除 dirty baseline 影响，已新建成对 clean release worktree：后端 `D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\ruoyi-vue-pro`（branch `codex/20260622-page-full-flow-mainmerge-release-clean`，HEAD `3ace5094ec`，`git status --short` 为空）、前端 `D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\yudao-ui-admin-vue3`（branch `codex/20260622-page-full-flow-mainmerge-release-clean`，HEAD `37359a074`，`git status --short` 为空）。同时已将本机运维台局部配置 `config/runtime-control.local.yaml` 的 `repo-root` / `frontend-root` 切换到这两个 clean worktree，准备重启运维控制台后继续保持“页面按钮触发”的真实链路。

`2026-06-22` 已重新打开运行控制台并核验页面预览弹窗，确认 `build-release` 预览参数已经指向上述 clean worktree；当前需要在真实页面重新提交新的 `releaseTag` 后，从头再走一遍构建发布包 -> 部署测试服 -> 标记测试通过 -> 上线正式服 -> 上线备份服，不能沿用旧的 dirty baseline 结果。

`2026-06-22` 真实页面 `build-release(v7)` 已成功提交到 clean worktree 基线，但 operation `op-2026-06-21T234844686010400Z-12704e02-b10c-472d-af05-cb4b5ff828c3` 在前端打包阶段失败：`D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\yudao-ui-admin-vue3\node_modules\vite\bin\vite.js` 缺失，说明 clean frontend worktree 的依赖现场尚未完成 bootstrap。当前发布包未生成，不能继续测试服/正式服/备份服；必须先补齐 clean worktree 依赖，再用新的 `releaseTag` 从真实页面重新执行 build-release。

`2026-06-22` 上述 clean frontend worktree 依赖阻塞已完成现场修复：确认 `node_modules` 原先不存在后，已在 `D:\ProjectPackage\Int\IntRuoyi\worktrees\20260622-page-full-flow-mainmerge-release-clean\yudao-ui-admin-vue3` 执行 `pnpm install --frozen-lockfile`，随后 `pnpm build:test` 成功输出 `Build successful. Please see dist-test directory`。当前 clean worktree 前端依赖前置条件已恢复，下一步可回真实页面用新的 `releaseTag`（建议 `release-20260621-page-full-flow-mainmerge-v8`）重新提交 `build-release`。

`2026-06-22` 真实页面 `build-release(v8)` 已成功通过，operation `op-2026-06-22T000330671317300Z-c009a2ba-8bcf-4210-b73a-2a09a4a1e424` 收口为 `SUCCESS`；本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v8\` 已生成 `manifest.json`、`release-manifest.json` 与 `intruoyi-images_release-20260621-page-full-flow-mainmerge-v8.tar`，NAS 目录为 `Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v8`。`manifest.json` 已核对 backend/front commit 分别为 `3ace5094ec` / `37359a074`，且 `sourceRepos.dirty` 均为 `false`，说明当前候选包已回到 clean release baseline。下一步继续从真实页面执行 `deploy-test(v8)`。

`2026-06-22` 真实页面 `deploy-test(v8)` 已提交，operation `op-2026-06-22T001514869158500Z-1d251735-38f1-43d5-afe3-c40e4b603a8e` 最终在测试服 required SQL `20260618_mes_edhr_oq_pq_execution_deviation.sql` line 399 失败，错误为 `Missing eDHR OQ/PQ system_menu rows; cannot merge tenant package menu_ids`。日志确认此前的 `20260613_dcc_file_view_matrix_seed`、`20260615_showroom_hall_canvas_background`、`20260618_mes_edhr_label_print_queue` 与 `20260618_post_release_role_e2e_gate` 都已成功跨过，说明当前主阻塞已切换为 OQ/PQ 菜单行缺失，而不是旧的按钮定义冲突。

`2026-06-22` 随后对测试服 `172.30.30.58` 做只读 `system_menu` 核对，确认当前真实库里 `900332-900337` 仅存在 `900335-900337` 三条，`900332-900334` 缺失，且旧 OQ/PQ `900290-900292` 也已不存在；这说明当前 SQL 仍存在 cleanup 顺序缺陷：先按旧 `path/permission` 存在而跳过新 `900332-900334` 插入，再删除 legacy `900290-900292`，最终把页面/查询/创建三条一起删空，只剩执行/复测/关闭三条。按门禁，下一步必须在业务后端按严格 TDD 修复该正式 SQL 顺序问题；由于发布包输入将再次变化，旧标签 `release-20260621-page-full-flow-mainmerge-v8` 不可继续使用，修复后必须通过真实页面以新的 `releaseTag`（建议 `release-20260621-page-full-flow-mainmerge-v9`）重新执行 `build-release -> deploy-test`，之后才能继续 `mark-tested -> prod -> backup`。

`2026-06-22` 上述 cleanup 顺序根因已在业务仓任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-oq-pq-legacy-cleanup-order-fix\` 按严格 TDD 修复完成，并通过 `pytest`、迁移策略门禁与 bug regression validator。当前维护仓必须改用新的 `releaseTag` `release-20260621-page-full-flow-mainmerge-v9` 重新构建发布包，然后继续真实页面 `build-release -> deploy-test -> mark-tested -> prod -> backup`。

`2026-06-22` 真实页面已按新输入基线完成 `build-release(v9)`，operation `op-2026-06-22T010042891831400Z-d59751ca-ab81-4136-b128-0f98537c2cd5` 最终 `SUCCESS`；本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v9\` 已生成 `manifest.json`、`release-manifest.json` 与 `intruoyi-images_release-20260621-page-full-flow-mainmerge-v9.tar`，NAS 发布目录为 `Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v9`。`manifest.json` 已核对 backend/frontend 源提交分别为 `3ace5094ec7768237e7249b876a4eca67dad5e2a` / `37359a074cedcc0a341f17cb0abdd1a71f838731`，且 `sourceRepos.dirty=false`，说明本轮 v9 候选包仍保持 clean release baseline。

`2026-06-22` 随后真实页面提交 `deploy-test(v9)`，operation `op-2026-06-22T011513436036700Z-42784c13-1bca-48e9-b0a9-fa51f2309f0a` 最终 `FAILED`；远端日志确认前一轮 OQ/PQ 阻塞已跨过，新的失败切换为 `20260618_mes_edhr_print_policy_reissue_void.sql` line 103 的 `Duplicate entry '900285' for key 'system_menu.PRIMARY'`。影响：`release-20260621-page-full-flow-mainmerge-v9` 无法继续用于 `mark-tested -> prod -> backup`；下一步必须先在业务后端记录并修复该 `system_menu` 主键冲突，再改用新的 `releaseTag` 从真实页面重新 `build-release -> deploy-test`。

`2026-06-22` 上述 print policy 根因已在业务后端任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-print-policy-menu-id-collision-fix\` 按严格 TDD 修复完成，并通过 `python -X utf8 -m pytest ...test_edhr_print_policy_reissue_schema_sql.py -q`、`python -X utf8 ...run-release-migration-policy-gate.py --sql-root ...` 与 bug regression validator。当前 clean release backend worktree 已补齐 cherry-pick：功能修复提交为 `ca023336e9`、回归证据提交为 `a72602e2f0`，前端 clean worktree 仍为 `37359a074`。由于发布包输入再次变化，旧标签 `release-20260621-page-full-flow-mainmerge-v9` 已失效；下一步必须通过真实页面以新的 `releaseTag`（建议 `release-20260621-page-full-flow-mainmerge-v10`）重新执行 `build-release -> deploy-test`，测试服通过后再继续 `mark-tested -> prod -> backup`。

`2026-06-22` 真实页面 `build-release(v10)` 已成功收口，operation `op-2026-06-22T030125335519200Z-62e5f1af-95d5-4011-9983-9f1c03771bf7` 最终 `SUCCESS`；本地候选目录 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260621-page-full-flow-mainmerge-v10\` 已生成 `manifest.json`、`release-manifest.json` 与 `intruoyi-images_release-20260621-page-full-flow-mainmerge-v10.tar`，NAS 发布目录为 `Backup/ReleasePackage/release-20260621-page-full-flow-mainmerge-v10`。`manifest.json` 已核对 backend/frontend 源提交分别为 `a72602e2f0` / `37359a074`，且 `sourceRepos.dirty=false`，说明当前候选包继续保持 clean release baseline。

`2026-06-22` 随后真实页面提交 `deploy-test(v10)`，operation `op-2026-06-22T031709289783300Z-b87c3859-b5bf-4f2c-b03f-008cf8d5e7b3` 最终 `FAILED`。远端日志确认此前阻塞的 `20260618_mes_edhr_print_policy_reissue_void.sql` 已在真实测试库成功 `APPLIED`，新的失败切换为 `20260618_mes_edhr_dhr_template_lifecycle.sql`：MySQL 在 line `120` 抛出 `ERROR 1062 (23000): Duplicate entry '900293' for key 'system_menu.PRIMARY'`。只读核对测试服 `system_menu` 现场已确认 `900290-900292` 是当前 DHR 模板菜单本身，而 `900293-900299` 已被 `20260618_mes_edhr_unified_change_impact.sql` 的“eDHR统一变更”整段占用，因此当前 DHR 模板按钮仍复用冲突号段。

`2026-06-22` 按“先记录再修复”门禁，本轮 `deploy-test(v10)` 失败已先在维护仓任务文档落盘。影响：`release-20260621-page-full-flow-mainmerge-v10` 无法继续用于 `mark-tested -> prod -> backup`；下一步必须在业务后端新建严格 TDD 修复任务，给 `20260618_mes_edhr_dhr_template_lifecycle.sql` 切换独立未冲突菜单号段并通过回归验证，随后改用新的 `releaseTag` 从真实页面重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。

`2026-06-22` 上述 DHR 模板根因已在业务后端任务 `D:\ProjectPackage\Int\IntRuoyi\ruoyi-vue-pro\doc\tasks\20260622-edhr-dhr-template-menu-id-collision-fix\` 按严格 TDD 修复完成，并通过 `python -X utf8 -m pytest ...test_edhr_dhr_template_schema_sql.py -q`、`python -X utf8 ...run-release-migration-policy-gate.py --sql-root ...` 与 bug regression validator。当前 clean release backend worktree 已补齐 cherry-pick：修复提交为 `d9606a65df`，前端 clean worktree 仍为 `37359a074`。由于发布包输入再次变化，旧标签 `release-20260621-page-full-flow-mainmerge-v10` 已失效；下一步必须通过真实页面以新的 `releaseTag`（建议 `release-20260621-page-full-flow-mainmerge-v11`）重新执行 `build-release -> deploy-test`，测试服通过后再继续 `mark-tested -> prod -> backup`。

`2026-06-22` 真实页面随后已实际提交 `build-release(v11)`，operation `op-2026-06-22T034606591995400Z-87264c6d-8e7b-4b5f-801f-e8b6e91e555f` 最终 `FAILED`。本机构建在进入 Maven/Vite 打包前就被维护仓新增的 SQL 预检门禁拦下，报错为 `system_menu.id must be an integer literal for release preflight: .../20260520_system_nas_management_menu.sql:11 -> \`name\``；失败文件是合法 SQL，包含 `ON DUPLICATE KEY UPDATE ... VALUES(\`name\`)`，说明当前维护仓 `release_sql_contract_gate.py` 对 `VALUES(...)` 更新子句存在误判。影响：基于 DHR 模板修复后的最新 clean baseline 目前连新的候选发布包都无法生成，因此测试服/正式服/备份服链路全部暂停；按“先记录再修复”门禁，必须先在维护仓按严格 TDD 修复该 SQL 预检解析根因，再改用新的 `releaseTag`（建议 `release-20260621-page-full-flow-mainmerge-v12`）从真实页面重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。

`2026-06-22` 上述维护仓 SQL 预检误判根因已在维护仓任务 `D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260622-sql-preflight-gate\` 按严格 TDD 修复完成：新增回归用例覆盖合法 `ON DUPLICATE KEY UPDATE ... VALUES(...)` 菜单 SQL，`release_sql_contract_gate.py` 现只解析真正 `VALUES (...)` 顶层插入元组，已经不再把更新子句里的 `VALUES(\`name\`)` 误当成新的 `system_menu` 记录。当前回归已通过维护仓 `pytest`、showroom 发布合同测试和真实 clean release backend SQL 根目录门禁，因此下一步可以回真实页面以新的 `releaseTag` `release-20260621-page-full-flow-mainmerge-v12` 重新执行 `build-release -> deploy-test -> mark-tested -> prod -> backup`。
