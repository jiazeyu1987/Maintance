# 20260828 仅测试服 HEAD 发布

## Task Goal

基于本次发布开始时冻结的当前分支最新已提交代码，构建维护控制台和测试发布包，并仅发布到测试服务器 `172.30.30.58`；未提交改动、未跟踪文件和脏工作区内容不得进入构建产物。

## Frozen Baseline

- 最终有效发布轮次：`r260829j`
- releaseTag：`release-20260829-frozen-head-test-r260829j-r1`
- 维护仓目标提交：`int_main@24106b18eec879e87d5cdf8d79fa0a739e9120a6`
- E:\IntRuoyi 目标提交：`int_main@3892f88f00d30aa06a4be6c5bd48f9e55ed6203c`
- 当前主工作区均存在既有脏改动，最终构建和发布未使用主工作区工作树。
- 构建开始后未追逐后续提交；最终产物只绑定 `r260829j` worktree 中记录的两个 HEAD。

## Release Worktrees

- 维护仓发布 worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260829j\m`
- IntRuoyi 发布 worktree：`D:\IntRuoyiWorktree\r260829j\a`
- 构建状态目录：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260829j-state`
- 发布包目录：`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260829-frozen-head-test-r260829j-r1`
- Git 状态：两个发布 worktree 均为 detached HEAD，`git status --short --branch` 仅输出 `## HEAD (no branch)`。
- 构建输入约束：最终构建和发布只使用上述 worktree 中冻结的提交，不追踪后续主工作区提交。

## Milestones

1. 启动门禁与任务文档：读取适用规则、经验索引、发布/服务器/登录/worktree/PowerShell 前置经验并记录授权。
2. Git 与 worktree 输入锁定：确认当前分支、HEAD、dirty 状态、目标提交、构建目录和本轮专用临时 worktree。
3. 构建维护控制台与发布包：仅从冻结提交的干净临时 worktree 构建，并校验 package、manifest、版本号和变更说明。
4. 仅测试服发布：执行 `publish-test`；禁止 `mark-tested`、`promote-prod`、`promote-backup`。
5. 测试服真实运行态验证：核 operation、manifest、远端 `.env IMAGE_TAG`、实际镜像 tag、容器状态、health、HTTP、页面和运行控制台版本说明。
6. 问题记录与长过程复盘：记录 Git/worktree/构建/manifest/发布/镜像/容器/健康/页面/控制台/流程不一致/重复操作/耗时点。
7. 经验沉淀与收尾：成功后沉淀前置经验，完成 closeout 并删除本任务临时 worktree。

## Expected Verification

- 构建产物只包含本次冻结 HEAD 已提交代码。
- build-release 产物、manifest、版本号和变更说明可追溯到目标提交。
- publish-test 成功且不触发正式服、备份服或 `mark-tested`。
- 测试服务器真实运行态全部通过：镜像 tag、容器、健康检查、HTTP、页面、运行控制台版本和变更说明。
- 所有问题按要求字段记录，并在成功后转成前置经验。

## 经验门禁

- 测试服发布范围：只允许单一 releaseTag 的 `build-release -> publish-test`；禁止正式服、备份服和 `mark-tested`。
- Git / worktree：发布必须使用本轮专用干净临时 worktree；目标提交为发布开始时记录的 HEAD，构建开始后不追逐后续提交。
- 构建产物：构建后必须直接读取 `manifest.json`、artifact 清单、`sourceRepos[*].commit/dirty/path`、版本号和变更说明；缺失、dirty、提交不符或变更说明无法绑定目标提交即 fail fast。
- 发布参数：`publish-test` 前必须按现有文档确认测试服 host、runtime 目录和环境参数；payload 不得包含正式/备份发布动作。
- 远端运行态：发布后必须核 operation=SUCCESS、远端 `.env IMAGE_TAG`、实际镜像 tag、容器 running、backend health=UP、frontend HTTP 200、页面和运行控制台 release-info。
- PowerShell / SSH：全程显式 UTF-8；PowerShell 不用 `&&`；多行 SSH/MySQL 使用 LF/UTF-8 载体；每个关键命令以退出码和后置断言共同判定。
- 高风险动作：服务器写入/发布前，`execution-log.md` 必须先记录 `GREEN: experience-preflight -> PASS`。
- 经验沉淀：发布成功后，新增可复用问题优先更新 `docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`docs/powershell-preflight-lessons.md`、`docs/experience-index.md`。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否
- 是否从根因和长期维护角度解决：是
- 是否存在临时补丁或绕过：否

## Current Status

completed

## Blocker Summary

- 发布阻塞已在后续正式提交中逐轮修复，并以新的 clean release worktree 和新的 releaseTag 重新冻结后重跑。
- 最终有效轮次 `r260829j-r1` 已完成 `build-release -> publish-test`，发布范围仅测试服；未执行 `mark-tested`、`promote-prod` 或 `promote-backup`。
- 最终验收门禁 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260829j-state\test-release-final-gate-r260829j-r1.json` 为 `status=passed`，所有运行态和页面检查通过。
- 本轮问题已沉淀为前置经验；本任务专用 Playwright 浏览器、临时运行控制台和 release worktree 均已清理。
- 收尾验收：44 个 task-owned release worktree 的 Git 注册、物理路径和进程引用均为 0。

## 2026-08-28 继续执行

- 用户继续授权后，当前 app 主线已前进到 `8b5799a89b7ae673e4bdc79c02f5599f56d55b59`，但已提交 HEAD 仍包含空 Vue SFC 与 rollback SQL 发布扫描阻塞。
- 为达到“只发布已提交代码”的验收标准，本轮只允许提交两个发布阻塞的正式修复：维护仓 rollback-only SQL 排除契约、app 仓 `TrainingRulesReadonlyTab.vue` 恢复只读映射工作面。
- 已验证最小修复面：维护仓 `test_release_sql_preflight_gate.py` 通过；app 仓培训规则静态契约由失败转为通过。
- 下一步：分别提交维护仓和 app 仓的任务相关修复，随后创建新的本轮发布 worktree/releaseTag；旧 `r260828a` 阻塞 worktree 不复用。

## 2026-08-28 二次继续执行

- 维护仓当前 HEAD 已前进到 `5727beb1bdea618ff8020a697fae2e89acf96e8e`，提交历史包含 `34181a6 任务: 排除回滚专用SQL发布扫描` 与 `5727beb 任务: 修复维护前端依赖门禁`。
- IntRuoyi 当前 HEAD 已前进到 `8763b1562d3396c8ac5fde0c62a11ecc616a2cdf`，提交历史包含 `4758107f9 任务: 恢复培训规则只读页`。
- 主工作区仍存在大量未提交/未跟踪改动，继续禁止直接构建；本轮重新冻结为 `r260828b`，只使用新 HEAD 的干净发布 worktree。
- 旧 `r260828a` 阻塞 worktree 不复用；成功后与 `r260828b` 一起按 task-owned release worktree 清理门禁收尾。

## 2026-08-28 三次继续执行

- 恢复执行时发现 `r260828b` 实际 worktree HEAD 为维护仓 `34181a6be9ccf2087e8f0bf0408b28a8d28b61f5`、IntRuoyi `4758107f998af83eee95eee2152b4bc69ad8d51f`，与上段记录的冻结 HEAD 不一致，不能作为本轮发布输入。
- 已确认 `r260828h` 是唯一同时匹配上段冻结 HEAD 的专用发布 worktree：维护仓 `5727beb1bdea618ff8020a697fae2e89acf96e8e`，IntRuoyi `8763b1562d3396c8ac5fde0c62a11ecc616a2cdf`；两个 worktree 均为 detached HEAD 且 clean。
- 当前 IntRuoyi 主工作区后续又前进到 `17b48e9bb044c5d74bc5c86daef33b0b5f9cc830`，但本次发布不追逐后续提交；继续只基于 `r260828h` 中已记录的冻结提交构建和发布。
- 本轮构建目录：维护仓 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260828h\m`，IntRuoyi `D:\IntRuoyiWorktree\r260828h\a`，状态目录 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260828h-state`。

## 2026-08-28 六次继续执行

- `r260828j-r1/r2` 均已判废，原因分别为前端依赖二进制缺失和 app 后端 Maven 编译失败。
- 已提交 app 最小正式修复 `69c0f601afa3207eef99c9eb7db19e6237bc6cdb`（仅 `DccRegistrationCertificateDraftData` 增加 `remark` 字段，匹配既有构造调用）。
- 本轮重新冻结为 `r260828k`：维护仓 `8f98739469611947e48291d4d246d910fcc60ebb`，IntRuoyi `69c0f601afa3207eef99c9eb7db19e6237bc6cdb`。
- 本轮构建目录：维护仓 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260828k\m`，IntRuoyi `D:\IntRuoyiWorktree\r260828k\a`，状态目录 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260828k-state`。
- 两个 release worktree 均为 detached HEAD 且 clean；构建开始后不追逐主工作区后续提交。
- 已通过构建前门禁：Vue SFC 完整性、迁移策略、Spring 构造扫描、维护仓发布脚本合同。
- 当前正在执行前端依赖恢复；releaseTag 固定为 `release-20260828-frozen-head-test-r260828k-r1`。

## 2026-08-29 七次继续执行

- `r260828k-r1` 判废：冻结 app 提交只补齐 `DccRegistrationCertificateDraftData` record 字段，仍有两个已提交构造调用未传 `remark`，后端 Maven 编译失败，未执行 `publish-test`。
- app 主线已有后续已提交正式修复 `f34dd3177f4b4c43ae5cb33acbb1978937bda878`（`任务: 修复注册证草稿备注构造调用`），本轮不使用主工作区未提交改动。
- 已识别本轮专用 `r260829a` release worktree：维护仓 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260829a\m` at `8f98739469611947e48291d4d246d910fcc60ebb`，IntRuoyi `D:\IntRuoyiWorktree\r260829a\a` at `f34dd3177f4b4c43ae5cb33acbb1978937bda878`。
- 两个 `r260829a` release worktree 均为 detached HEAD 且 clean；主工作区仍较脏，继续禁止直接构建。
- 已通过 `r260829a` 构建前门禁：Vue SFC 完整性 `vueCount=1489, badCount=0`、迁移策略 `status=passed, migrationCount=527`、Spring 构造扫描 `status=passed`、维护仓发布脚本合同 `48 passed`。
- 下一步：恢复 app 前端依赖、构建维护控制台、启动指向 `r260829a` 的运行控制台，并提交新的 `build-release`，releaseTag 固定为 `release-20260829-frozen-head-test-r260829a-r1`。

## 2026-08-29 八次继续执行

- `r260829a-r1` 判废：build-release 后端 Maven 编译失败，冻结 app 提交缺少 `DccRegistrationCertificateVersionDO.remark` 字段，未执行 `publish-test`。
- app 主线已有后续已提交正式修复 `4bd2830af0b717f9ce21fedc1af503af296b192b`（`任务: 修复注册证版本备注字段`）；本轮不使用主工作区未提交改动。
- 本轮重新固定为 `r260829b`：维护仓 `8f98739469611947e48291d4d246d910fcc60ebb`，IntRuoyi `4bd2830af0b717f9ce21fedc1af503af296b192b`。
- 本轮构建目录：维护仓 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260829b\m`，IntRuoyi `D:\IntRuoyiWorktree\r260829b\a`，状态目录 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260829b-state`。
- 两个 `r260829b` release worktree 均为 detached HEAD 且 clean；主工作区仍较脏，继续禁止直接构建。
- 构建开始后不追逐 app 主工作区后续提交 `bf94b2a18272b029f5d5c92d3a85fcf01f623fee`；继续只基于 `r260829b` 记录的冻结提交构建和发布。
- 已通过 `r260829b` 迁移策略门禁：`status=passed, migrationCount=527`。
- 下一步：补齐 `r260829b` 维护控制台本机配置、恢复前端依赖、构建维护控制台、启动指向 `r260829b` 的运行控制台，并提交新的 `build-release`，releaseTag 固定为 `release-20260829-frozen-head-test-r260829b-r1`。

## 2026-08-29 九次继续执行

- `r260829b-r1` 判废：build-release 后端 Maven `testCompile` 失败，冻结 app 提交的注册证测试与查询对象字段不一致，未执行 `publish-test`。
- r260829b 本地前置结果：Vue SFC 完整性 PASS、迁移策略 PASS、Spring 构造扫描 PASS、维护仓脚本合同 `48 passed`、DCC 主源码 compile PASS、app 前端依赖恢复且 ignored-builds 为 `None`、维护控制台构建 PASS。
- app 主线当前最新已提交 HEAD 为 `bf94b2a18272b029f5d5c92d3a85fcf01f623fee`，包含 DCC 注册证测试、查询对象与相邻前后端更新；主工作区仍 dirty，不能直接构建。
- 后续动作：创建新的本轮专用 clean release worktree `r260829c`，维护仓继续使用 `8f98739469611947e48291d4d246d910fcc60ebb`，IntRuoyi 使用 `bf94b2a18272b029f5d5c92d3a85fcf01f623fee`；从构建前门禁重新跑，releaseTag 递增为 `release-20260829-frozen-head-test-r260829c-r1`。

## 2026-08-29 十次继续执行

- `r260829c-r1` 判废：后端 Maven package 与前端 build:test 已通过，但 build-release 在 Docker build context 准备阶段以退出码 `-1` 失败，未生成可发布 manifest，未执行 `publish-test`。
- 已确认维护仓主线存在已提交正式修复 `34b9e0b058d4d8468dc8b3fa7e179369bbea7960`（`任务: 优化发布前端构建上下文复制`），用于修复 r260829c 的构建上下文复制失败；未使用维护仓未提交改动。
- 本轮重新固定为 `r260829d`：维护仓 `34b9e0b058d4d8468dc8b3fa7e179369bbea7960`，IntRuoyi 继续使用 `bf94b2a18272b029f5d5c92d3a85fcf01f623fee`，不追逐 app 主工作区后续提交 `8e28366e97d865a4cd768866ab731fb5831b075f`。
- 本轮构建目录：维护仓 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260829d\m`，IntRuoyi `D:\IntRuoyiWorktree\r260829d\a`，状态目录 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260829d-state`。
- 两个 `r260829d` release worktree 均为 detached HEAD 且 clean；构建开始后继续只认该 worktree 的冻结提交。
- 已通过 `r260829d` 构建前门禁：Vue SFC 完整性 `vueCount=1490, badCount=0`、迁移策略 `status=passed, migrationCount=530`、Spring 构造扫描 `status=passed`、维护仓脚本合同 `53 passed`、前端依赖恢复完成且 `ignored-builds=None`、`cross-env/vite/vue-tsc` 二进制均存在。
- 下一步：从 `r260829d` 构建维护控制台，启动指向 r260829d 的运行控制台，提交新的 `build-release`，releaseTag 固定为 `release-20260829-frozen-head-test-r260829d-r1`。

## 2026-08-29 十二次继续执行

- `r260829d-r2` build-release 成功且 manifest 校验通过，但 `publish-test` 在 required SQL `20260515_dcc_runtime_schema_repair.sql` 执行阶段失败；测试服未判定发布成功。
- 失败根因：旧 SQL 直接用长 `title` 回填 `dcc_controlled_file.file_number`，测试服真实数据触发 `ERROR 1406 Data too long for column 'file_number'`。
- 已提交 app 正式修复 `b9e6eea98bdbd995ad540e67af72094d747b8f38`（`任务: 修复DCC运行修复SQL编号长度`），并通过目标 Python/JUnit/迁移策略门禁。
- 本轮重新冻结为 `r260829e`：维护仓 `34b9e0b058d4d8468dc8b3fa7e179369bbea7960`，IntRuoyi `b9e6eea98bdbd995ad540e67af72094d747b8f38`；主工作区仍 dirty，禁止直接构建。
- 下一步：创建 `r260829e` clean release worktree，重新构建维护控制台和发布包，releaseTag 固定为 `release-20260829-frozen-head-test-r260829e-r1`，成功后仅执行 `publish-test`。

## 2026-08-29 十四次继续执行

- `r260829e-r1` build-release 成功、manifest/release-info 校验通过，但 `publish-test` 执行 required SQL `20260814_mes_production_release_roles.sql` 时失败；测试服未判定发布成功。
- 失败根因：生产放行角色 SQL 的 Memory 临时表字符串列继承测试库默认 collation，与真实 `system_menu.permission` / `system_role.code` 等字段比较时触发 `ERROR 1267 Illegal mix of collations`；同一目标静态测试还暴露了该 SQL 使用 `TRUNCATE TABLE` 违反既有非破坏性契约。
- 已提交 app 正式修复 `caf5c323061b68506da77fbd54c62c82893c3cbb`（`任务: 修复生产放行角色SQL排序规则`），提交范围仅 `20260814_mes_production_release_roles.sql` 与对应静态契约测试。
- 已验证最小修复面：`test_mes_production_release_roles_sql.py` 由 RED 转为 `7 passed`；发布迁移策略门禁 `migration-policy-gate-after-role-collation.json` 为 `status=passed, migrationCount=532`。
- `r260829e-r1` 判废；下一轮重新冻结为 `r260829f`，维护仓继续使用 `34b9e0b058d4d8468dc8b3fa7e179369bbea7960`，IntRuoyi 使用 `caf5c323061b68506da77fbd54c62c82893c3cbb`，releaseTag 固定为 `release-20260829-frozen-head-test-r260829f-r1`。

## 2026-08-29 十五次继续执行

- r260829f 发布输入已冻结：维护仓 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260829f\m` at `34b9e0b058d4d8468dc8b3fa7e179369bbea7960`，IntRuoyi worktree `D:\IntRuoyiWorktree\r260829f\a` at `caf5c323061b68506da77fbd54c62c82893c3cbb`；两者均为 detached HEAD 且 clean，主工作区脏改动不参与构建。
- GREEN: r260829f 构建前门禁通过：Vue SFC 完整性 `vueCount=1490, badCount=0`；迁移策略 `status=passed, migrationCount=531`；Spring 构造契约 `{"status":"passed"}`；维护仓发布脚本合同 `53 passed`。
- GREEN: app 前端依赖恢复通过：`pnpm install --frozen-lockfile --reporter append-only` 完成，临时 `pnpm.onlyBuiltDependencies` rebuild 后 `pnpm ignored-builds=None`，并恢复 `package.json`，tracked diff 为空。
- GREEN: 维护控制台构建通过：`scripts\build.ps1` 完成前端 typecheck/build 与 Maven `26` tests，jar `runtime-control-maintenance-2026.06-SNAPSHOT.jar` SHA256=`4968F42134E4941A1464D3CDDEB073694A7BDE58B7B595672813D6E15103D12C`。
- GREEN: runtime-control-r260829f-health -> PASS，端口 `48191` 返回 `UP`，配置指向 r260829f app/maintenance worktree 与 r260829f-state。
- RECHECK: build-release-preview-r260829f-r1 -> PASS，脚本路径、后端/前端 repo root、releaseTag 与 code-only 参数均指向 r260829f 冻结输入。
- IN_PROGRESS: build-release-r260829f-r1 -> operation `op-2026-08-29T031946177716200Z-cf66e3ac-cf7f-4869-b15c-258e5a6cd360` 已提交并正在执行；未执行 `publish-test`、`mark-tested`、`promote-prod` 或 `promote-backup`。

## 2026-08-29 十六次继续执行

- `r260829f-r1` build-release 成功且 manifest/release-info 校验通过；发布包目录为 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260829-frozen-head-test-r260829f-r1`，source commit 均为 `caf5c323061b68506da77fbd54c62c82893c3cbb`，dirty 均为 `false`，变更说明为 `任务: 修复生产放行角色SQL排序规则`。
- `r260829f-r1` publish-test 判废：operation `op-2026-08-29T033804078209300Z-ea8ead8d-db0e-413e-8c69-be21c3517832` 执行 required SQL `20260817_dcc_registration_certificate_core.sql` 时失败，错误为 `ERROR 1644 (45000) at line 421: DCC registration certificate core column contract mismatch`；发布锁已释放，未执行测试服成功验收。
- 根因确认：测试服 `dcc_registration_certificate_snapshot.registrant_name` 为 `varchar(255) NOT NULL`，而当前 SQL/H2 合同均要求 `varchar(255) DEFAULT NULL`；该旧表 nullability 漂移属于可自动修正的兼容旧状态，不应阻断后续严格合同断言。
- 已提交 app 正式修复 `d3f5d6f13603ae723357cd909022eb1652ab64c0`（`任务: 修复注册证核心SQL旧表列合同`），不修改测试服数据、不在 release worktree 临时补丁。
- 本轮重新固定为 `r260829g`：维护仓 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260829g\m` at `34b9e0b058d4d8468dc8b3fa7e179369bbea7960`，IntRuoyi worktree `D:\IntRuoyiWorktree\r260829g\a` at `d3f5d6f13603ae723357cd909022eb1652ab64c0`，状态目录 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260829g-state`。
- RECHECK: r260829g-release-worktree-clean -> 两个 worktree 均为 detached HEAD 且 `git status --short` 为空；主工作区仍存在未提交改动，不参与本轮构建。
