# 20260821 仅测试服 HEAD 发布

## Task Goal

基于本次发布开始时记录的当前分支 HEAD 已提交代码构建维护控制台与测试发布包，并仅发布到测试服务器；未提交改动、未跟踪文件和脏工作区内容不得进入构建产物。

## Milestones

1. 启动门禁与任务文档：读取适用规则、发布/服务器/登录/worktree/PowerShell/经验门禁并记录授权。
2. Git 与 worktree 输入锁定：确认当前分支、HEAD、脏工作区状态、目标提交、构建目录和本轮专用临时 worktree。
3. 构建维护控制台与发布包：仅从干净临时 worktree 的冻结提交构建，并校验 package、manifest、版本号、变更说明和 sourceRepos。
4. 仅测试服发布：执行 publish-test；禁止 mark-tested、promote-prod、promote-backup。
5. 测试服真实运行态验证：核 operation=SUCCESS、manifest、远端 `.env IMAGE_TAG`、backend/frontend 镜像 tag、容器状态、health、HTTP 200、前端页面、运行控制台版本号和变更说明。
6. 问题记录与长过程复盘：记录 Git/worktree/构建/manifest/发布/镜像/容器/健康/页面/控制台/文档流程差异/重复操作/耗时点。
7. 经验沉淀与收尾：发布成功后沉淀前置经验，记录 verification-report；清理本任务临时 worktree 后标记 completed。

## Expected Verification

- 构建产物只包含本次启动时当前分支 HEAD 已提交代码。
- build-release 产物、manifest、版本号和变更说明可追溯到目标提交。
- publish-test 成功且不触发正式服、备份服或 mark-tested。
- 测试服务器真实运行态全部通过：镜像 tag、容器、健康检查、HTTP、页面、运行控制台版本和变更说明。
- 所有问题按要求字段记录，并在成功后转成前置经验。

## 经验门禁

- 测试服发布范围：只允许单一 releaseTag 的 `build-release -> publish-test`；禁止 `mark-tested`、`promote-prod`、`promote-backup`；不得把未走完整三环境闭环误判为测试服失败。
- Git / worktree：发布必须新建本轮专用干净临时 worktree；目标提交为发布开始时记录的 HEAD，构建开始后不追逐后续提交；主工作区 dirty 不得进入产物。
- 构建产物：构建后必须直接读取 `manifest.json`、legacy manifest、artifact hash、`sourceRepos[*].commit/dirty/path`、版本号和变更说明；缺失、dirty、提交不符或变更说明不能绑定目标提交即 fail fast。
- 发布参数：publish-test 前必须按现有文档确认测试服 host、runtime 目录和环境参数；payload 不得包含正式/备份发布动作或 build-only 字段。
- 远端运行态：发布后必须核 operation=SUCCESS、远端 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 running、backend health=UP、frontend HTTP 200、页面和运行控制台 release-info。
- PowerShell / SSH：全程显式 UTF-8；PowerShell 不用 `&&`；多行 SSH/MySQL 使用 LF/UTF-8 载体；每个关键命令以退出码和后置断言共同判定；秘密输出必须脱敏。
- 高风险动作：服务器写入/发布前，`execution-log.md` 必须先记录 `GREEN: experience-preflight -> PASS`。
- 经验沉淀：发布成功后，新增可复用问题优先更新 `docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`docs/powershell-preflight-lessons.md`、`docs/experience-index.md`。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否；缺任何构建来源、manifest、版本号、变更说明或运行态验证项均 fail fast。
- 是否从根因和长期维护角度解决：是；按正式发布脚本与现有发布文档执行，仅限制目标环境为测试服。
- 是否存在临时补丁或绕过：否；如过程中发现必须修复脚本或配置，需先正式记录、验证并提交，再用新 worktree/new releaseTag 重建。

## Current Status

blocked

## 2026-08-22 授权后的测试服历史快照修复

- 用户已明确授权仅对测试服执行受控历史 route snapshot 数据修复；本轮仅允许修复 `172.30.30.58` 上的测试库，不触碰正式服、备份服或任意其它环境。
- 当前修复边界：仅更新 `mes_pro_route_version` 中已识别 blocker 的历史快照 JSON，并将 `route_snapshot_sha256` 与 `route_snapshot_format_version` 置空，随后再用现有 BACKFILL 门禁回填身份列。
- 预期结果：修复后重新运行 publish-test 的 route snapshot BACKFILL/READINESS，必须回到 `READY/0` 后才能继续容器切换、页面和运行控制台验收。
- 仍然保留的失败事实：此前 r260822a-r2 已判废，不能复用旧 operation、旧 releaseTag 或旧运行态证明。
- 实际结果：修复 SQL 已在测试服执行并通过数据库后置核对，但正式 BACKFILL 仍为 `BLOCKED/8`，未达到继续构建或发布的门禁。

## 2026-08-22 继续执行记录

- 用户继续授权本任务，沿用现有任务目录与此前已冻结的发布输入，不重新从 Git 获取后续提交。
- 当前优先动作：定位测试服 route snapshot BACKFILL 的 `BLOCKED/882` 真实 blocker 分类；本阶段只允许只读数据库、代码与已生成报告核查。
- 禁止动作：不重试 `r260822a-r2`，不修改测试服业务数据、migration ledger、release lock 或远端 `.env`，不执行 `mark-tested`、`promote-prod`、`promote-backup`。
- 当前判断：r260822a-r2 构建产物可追溯且通过 manifest 校验，但发布未达到 `operation=SUCCESS`，仍不得判定测试服发布成功。

## 2026-08-22 授权后正式 BACKFILL 阻塞

- `route-snapshot-repair-r260822a-r2.sql` 已按授权仅写入测试服 `mes_pro_route_version`，`repairedCount=27`；数据库后置核对 `47/47` 快照非空。
- 正式 runner 报告：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260821-test-only-head-release\evidence\route-snapshot-identity-backfill-authorized-r260822a.json`，`mode=BACKFILL`、`status=BLOCKED`、`scannedCount=47`、`updatedCount=0`、`blockerCount=8`。
- 8 个 blocker 均为 `routeVersionId=3`、`routeId=900025` 的 `configSnapshots.scheduleConfigs[*].routeProcessId` 未解析；实际重复为 4 个 ID（`900124`、`900125`、`900126`、`900127`）各被两轮校验报告一次。
- 只读源表核查：`mes_pro_route_schedule_config` 使用 `route_version_id + route_process_id` 保存配置；对应 `route_version_id=3` 的物理配置仍引用上述旧 ID，但 `mes_pro_route_process` 当前行及含逻辑删除行均不存在这些 ID。当前 `route_id=900025` 的路线工序 ID 已是另一组新 ID，且没有正式映射表或代码/文档修复方案可证明旧 ID 对应关系。
- 冻结代码契约要求所有快照引用必须解析到正式 `routeProcessId`；禁止按排序盲映射、删除配置、置空配置或从当前路线静默推断历史身份。因此本任务在正式数据来源缺失处 fail fast。
- 影响：不得进入新 build-release、不得切换容器、不得做页面/运行控制台成功验收；r260822a-r2 继续判废，不重试。
- 需要的解除条件：提供正式的 `900124–900127` 到当前路线工序的可审计映射/恢复来源，或明确授权并提供针对 `mes_pro_route_schedule_config` 与快照引用的正式修复方案、备份和回滚证据。仅“继续授权测试服发布”不足以替代该数据契约。

### Milestone Update 2026-08-22 授权后复核

- Milestone 2 Git 与 worktree 输入锁定：completed，维护 HEAD=`66c4ea05dda04459433bc22471ea2b6f4f3dfc32`，app HEAD=`c4d2c637bf1f2cea723876ee363f311b1128aaf4`，两个发布 worktree 仍 detached clean。
- Milestone 3 构建发布包：completed，沿用 r260822a-r2 的已验证构建证据；因旧 tag 已判废，未复用产物进行新发布。
- Milestone 4 仅测试服发布：blocked，授权后的正式 BACKFILL 为 `BLOCKED/8`，未进入容器切换。
- Milestone 5 测试服真实运行态验证：blocked，目标镜像未切换，页面与运行控制台不能用旧容器结果替代。
- Milestone 6 问题记录与长过程复盘：completed，新增 P051-P061，包含修复结果、孤儿引用、runner 清理、路径/引号/表结构探针、凭据暴露风险和证据时钟差异。
- Milestone 7 经验沉淀与收尾：blocked，正式数据映射缺失，暂不删除发布 worktree，不标记 `completed`。

## 2026-08-22 route snapshot blocker 只读根因诊断

- 只读取得测试服报告：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260821-test-only-head-release\evidence\route-snapshot-identity-backfill-r260822a-r2.json`；状态=`BLOCKED`，扫描=`47`，更新=`0`，blockerCount=`882`。
- blocker 分类：`FLOW_NODES_MISSING=8`、`ROUTE_ID_MISSING=2`、`PROCESS_ID_INVALID=436`、`PRODUCT_BOM_IDENTITY_INVALID=436`。
- 测试库只读核对：`mes_pro_route_version` 共 `47` 条；租户 `1`（芋道源码）`46` 条，租户 `122`（测试租户）`1` 条；身份列 `route_snapshot_sha256` 与 `route_snapshot_format_version` 当前均为空。
- 典型数据：路线版本 `id=110` 的历史快照有 `26` 个 BOM，快照中的 `productBoms[*].processId=0`，而当前 `mes_pro_route_product_bom` 对应路线的物理行 `process_id` 为正数；这证明不能用当前投影静默重写不可变历史快照。
- 根因结论：本轮构造注入修复已解除 Spring runner 启动问题，但测试服已有历史 route snapshot 不满足当前严格身份/结构门禁；发布脚本正确 fail fast，不能以跳过 BACKFILL、仅写 hash、排除租户 1 或改写快照的方式降级。
- 处理边界：只读取远端报告、表结构、租户 ID、路线快照聚合字段和 BOM 聚合字段；未修改业务数据、未修改 migration ledger/release lock、未重试 r260822a-r2、未执行 mark-tested/promote-prod/promote-backup。
- 当前阻塞：需要业务所有者提供正式的历史快照修复/数据治理方案，并明确是否允许对对应租户执行受保护数据修复；在此之前不能继续构建发布或宣称测试发布成功。现有全局规则禁止修改芋道源码租户数据，因此当前任务保持 blocked。

### 继续诊断中遇到的问题

- P044：现象=测试服没有 `jq`；阶段=只读报告汇总；影响=首个聚合命令无法执行，但未影响远端业务；原因判断=运行镜像未安装 jq；处理动作=改用远端已有 `python3` 解析同一 JSON；结果=报告摘要与 blocker 分类成功复核；可前置检查=是；可自动化=是；下次避免=发布前置诊断工具清单固定使用 Python 标准库或随包工具，并记录命令版本。
- P045：现象=第一次 MySQL 聚合探针因 PowerShell/SSH 引号导致空字符串表达式语法错误；阶段=只读数据库核查；影响=该次探针失败，无写入；原因判断=内联 SQL 的引号层级不稳定；处理动作=改用 UTF-8 SQL 文件经 stdin 传输，重跑简化聚合；结果=表结构、租户分布、身份列状态成功取得；可前置检查=是；可自动化=是；下次避免=中文/多层引号 SQL 一律使用 UTF-8 文件载体并单独验证退出码。
- P046：现象=第一次 JSON 路径探针使用 `CHAR(36)` 生成路径，MySQL 报 `ERROR 3144 ... CHARACTER SET 'binary'`；阶段=只读快照字段核查；影响=该次探针失败，无写入；原因判断=路径表达式返回 binary，JSON_EXTRACT 不接受该类型；处理动作=改用 SQL 文件中的字面 `$.` 路径，避免 shell 展开；结果=样本结构成功复核；可前置检查=是；可自动化=是；下次避免=JSON SQL 探针用 stdin 文件并对路径函数结果做类型检查。
- P047：现象=测试服 route snapshot BACKFILL 真实报告 `BLOCKED/882`；阶段=publish-test 前置运行报告；影响=无法进入容器切换、健康检查、页面和运行控制台版本验收；原因判断=47 条历史快照本身存在结构/身份 blocker，且其中 46 条属于芋道源码租户；处理动作=只读分类与样本核验，禁止改数据、跳过门禁或重试同一 releaseTag；结果=根因确认，任务继续 blocked；可前置检查=是；可自动化=是；下次避免=任何远端写入前单独执行 route snapshot BACKFILL/READINESS，并把租户分布和 blocker 分类纳入 fail-fast 证据。
- P048：现象=终端直接输出 `system_tenant.name` 出现乱码；阶段=租户身份核对；影响=不能把乱码原文作为证据；原因判断=SSH/终端输出编码链路不稳定；处理动作=改查 `HEX(name)`，按 UTF-8 解码确认租户名称；结果=确认 `1=芋道源码`、`122=测试租户`；可前置检查=是；可自动化=是；下次避免=中文数据库证据写 UTF-8 文件或查 HEX，不直接复制终端乱码。

## Milestone Update 2026-08-22 continued

- Milestone 2 Git 与 worktree 输入锁定：completed，继续沿用 r260822a 冻结输入，未追逐后续提交。
- Milestone 3 构建发布包：completed，r260822a-r2 provenance、manifest、版本号和变更说明均通过。
- Milestone 4 仅测试服发布：blocked，publish-test 在 route snapshot BACKFILL `BLOCKED/882` 阻断，operation 未收束为 SUCCESS。
- Milestone 5 测试服真实运行态验证：blocked，目标镜像未切换，不能使用旧容器的健康/HTTP 结果代替本轮验收。
- Milestone 6 问题记录与长过程复盘：completed，新增 P044-P048 和只读数据库/报告证据。
- Milestone 7 经验沉淀与收尾：blocked，当前没有可合法执行的修复授权，发布 worktree 继续保留，不执行 closeout 删除。

## Notes

- 用户已明确授权执行仅测试服发布；不得操作正式服、备份服或 mark-tested。
- 2026-08-21 已读取启动规则、经验索引、PowerShell/发布技能与上一轮任务状态；本轮从当前日期建立新任务记录，后续冻结本轮 HEAD，不追逐后续提交。
- P001：任务目录创建首次使用 `New-Item -LiteralPath` 在本机 PowerShell 中不兼容。阶段=任务文档；影响=任务文档创建延迟但未执行构建/发布；原因判断=当前 PowerShell/New-Item 参数集不支持 LiteralPath；处理动作=改用 `New-Item -Path`；结果=任务文档创建成功；可前置检查=是；可自动化=是；下次避免=目录创建统一用兼容 `-Path` 或 .NET API。
- P002：PowerShell here-string 写任务文档命令悬挂。阶段=任务文档；影响=任务文档创建延迟但未执行构建/发布；原因判断=多行命令承载不稳定；处理动作=终止悬挂会话并改用 apply_patch；结果=任务文档写入成功；可前置检查=是；可自动化=是；下次避免=长中文文档优先 apply_patch 或脚本文件，不用长内联 here-string。
- P012：`release-20260821-intmain-head-test-r260821c-r3` 构建 operation 为 SUCCESS，但 `validate-release-manifest.ps1 -PackagePath` 返回 `FORBIDDEN_HARDCODED_TARGET_IP`；`runtime-env/test.env`、`prod.env`、`backup.env` 均含 `EDHR_S3_ENDPOINT=http://172.30.30.57:9000`。阶段=构建后 manifest/发布包校验；影响=发布包未通过正式校验，不允许进入 `publish-test`；原因判断=发布包运行环境生成仍写入具体目标 IP，违反目标配置契约；处理动作=停止发布，不修改包、不发布测试服、不触发正式/备份动作；结果=任务阻塞；可前置检查=是；可自动化=是；下次避免=build-release 成功判定前必须执行并通过 manifest validator，且 runtime-env 不得含 forbidden target IP。
- P013：manifest 与前端 `release-info.json` 的 `changeSet.summary/items` 出现乱码 `浠诲姟: 淇鍙戝竷Hook闀滃儚鍙傛暟`，而冻结主程序提交主题为 `任务: 修复发布Hook镜像参数`。阶段=版本号/变更说明校验；影响=无法确认运行控制台会显示正确变更说明，按验收标准必须失败；原因判断=构建脚本采集 Git 提交说明时存在编码路径问题；处理动作=停止发布，不手工改 manifest/release-info；结果=任务阻塞；可前置检查=是；可自动化=是；下次避免=build-release 后用 UTF-8 校验 changeSet 与 `git log -1 --pretty=%s` 完全一致，乱码即 fail fast。
- P014：构建脚本已将 r3 包上传 NAS 并返回 operation SUCCESS，但独立 manifest validator 失败。阶段=构建脚本/流程一致性；影响=若只信 operation 状态可能误发布无效包；原因判断=build-release 成功状态未把发布包 validator 失败作为阻断条件；处理动作=以后置独立校验为准判定失败，未执行 publish-test；结果=任务阻塞；可前置检查=是；可自动化=是；下次避免=将 manifest validator 接入 build-release 成功门禁，失败时不得标记 SUCCESS 或上传后可发布。
- P015：`release-20260821-intmain-head-test-r260821d-r1` 在后端/前端构建和镜像导出后失败，包目录缺 `manifest.json`，validator 返回 `MANIFEST_MISSING`。阶段=build-release；影响=该 releaseTag 判废，不得 publish-test；原因判断=runtime-env/test.env 生成阶段阻断导致 manifest 未写入；处理动作=停止发布并使用新 releaseTag 重建；结果=待重建；可前置检查=是；可自动化=是；下次避免=runtime-env 目标 host 边界必须在镜像构建前通过。
- P016：test runtime env 仍将通用 `EDHR_S3_ENDPOINT` 解析到非测试服 host。阶段=runtime-env 生成；影响=发布包无法完成 manifest 生成；原因判断=脚本只优先目标专属变量，但目标专属变量缺失时没有把通用 endpoint 按目标 host 重绑；处理动作=新增 `Resolve-TargetEdhrS3Endpoint`，在 `Set-PublishRuntimeDefaultsForTarget` 和 `New-ReleaseRuntimeEnvContent` 中传入 `TargetServerHost`；结果=合同测试、发布说明合同、运行控制台合同和 PowerShell 解析均通过；可前置检查=是；可自动化=是；下次避免=build-release 前静态合同必须覆盖 generic endpoint -> target host 重绑路径。
- P017：`release-20260821-intmain-head-test-r260821e-r1` 在 eDHR protected storage verifier 阶段失败，返回 `InvalidAccessKeyId`。阶段=build-release 前置对象锁校验；影响=未生成发布包，不得 publish-test；原因判断=隔离控制台缺 `EDHR_S3_TEST_*`，把 generic/prod 凭据用于 test endpoint；处理动作=只读测试服 `.env` 并在内存中验证目标配置 PASS，随后正式修复 secret 渠道；结果=r1 判废，待新提交/new releaseTag 重建；可前置检查=是；可自动化=是；下次避免=隔离控制台启动前必须校验目标环境 EDHR 变量。
- P018：排障中宽泛搜索命中过往临时目录中的 secret-bearing runtime env。阶段=证据采集；影响=原始输出不得保存或提交；原因判断=搜索范围包含历史 backup/restore tmp；处理动作=不写入原始输出，改用脱敏/窄范围探针；结果=任务文档仅记录 presence/host 摘要；可前置检查=是；可自动化=是；下次避免=发布排障 `rg` 默认排除 secret-bearing 历史临时目录。
- P019：48181 仍运行旧 `r260821c` 控制台，`r260821e` 隔离控制台在 48183。阶段=运行控制台归属；影响=误用 48181 会读到旧 operation；原因判断=为不覆盖稳定主控制台使用隔离端口；处理动作=后续 r260821e 操作固定使用 48183 并记录 PID/JAR/state-dir；结果=未触碰旧控制台；可前置检查=是；可自动化=是；下次避免=每次 action 前记录控制台端口与 JAR 路径。
- P020：release-20260821-intmain-head-test-r260821f-r1 在 build-release 的 eDHR protected storage verifier 阶段返回 InvalidAccessKeyId。阶段=build-release 前置对象锁校验；影响=未生成 manifest 或发布包，禁止 publish-test；原因判断=a87b0ef 仅在 deploy-release 前导入测试服 .env，而 build-release 仍使用本机继承的非测试密钥；处理动作=判废 r260821f-r1，在独立修复 worktree 先补 RED 回归，再让 build-release 以只读方式导入当前测试服 runtime .env 后执行目标化默认值和 verifier；结果=修复中；可前置检查=是；可自动化=是；下次避免=所有会执行目标对象锁 verifier 的 build/deploy 路径均必须先确认其密钥来源为当前 target 环境。- P021：release-20260821-intmain-head-test-r260821h-r1 在前端 pnpm build:test 阶段失败，提示 Local package.json exists, but node_modules missing 与 cross-env 不可识别。阶段=build-release 前端构建；影响=本轮 releaseTag 判废，不得继续发布测试服；原因判断=新的 app release worktree 只检出到了 HEAD，但未先恢复前端依赖；处理动作=停止本轮 r1，先对 D:\IntRuoyiWorktree\r260821h\a\IntRuoyiFronted 执行 pnpm install --frozen-lockfile --package-import-method=copy，再用新 releaseTag 重建；结果=修复中；可前置检查=是；可自动化=是；下次避免=每次新 app release worktree 必须先核对 node_modules\.bin\cross-env.cmd、vite.cmd、vue-tsc.cmd，不存在则不得进入 build-release。- P022：首次 app 前端依赖恢复被中断，返回码 `1073807364`；重新安装 1103 packages PASS，并通过关键 bin、`.modules.yaml pendingBuilds=[]` 和实际 `pnpm build:test` 验证。
- P023：r260821h-r2 build-release 因隔离运行控制台继承无效 PATH，日志为 `Missing command: mvn`；r2 判废，已找到并验证本机 Maven 3.9.16，在新控制台进程启动前显式补入 PATH，使用新 releaseTag 重试。该项已转为 build-release 前的 Maven 可执行性门禁。
- P024：r260821h-r3 前端镜像构建因 Docker Hub 网络瞬时失败判废；后端/前端构建已通过，已按标准动作 pull 
ginx:1.27-alpine 成功并使用新 releaseTag 重试。

## Milestone Update

- Milestone 3 构建发布包：completed。r260821h-r4 build-release SUCCESS，manifest validator PASS，package/sourceRepos/dirty/changeSet/release-info/tar hash 全部与冻结 app HEAD 一致；版本标识按现有契约为 releaseTag/packageId。
- Milestone 4 仅测试服发布：blocked。publish-test operation `op-2026-08-21T210307402431400Z-d11e3d45-06fb-4026-a039-a1ee4f70086b` FAILED，失败于测试服 route snapshot BACKFILL 运行报告。
- Milestone 5 测试服真实运行态验证：blocked。失败态只完成影响复核，不能进入成功验收。
- Milestone 6 问题记录与长过程复盘：completed。P001-P031 已记录，包含构建、脚本、镜像、容器、远端漂移、凭据日志、控制台和耗时点。
- Milestone 7 经验沉淀与收尾：blocked。发布未成功，任务专用 worktree 和隔离控制台按阻塞保全规则暂不删除。

## 2026-08-21 r260821h-r4 发布阻塞

- 目标提交：维护 `66c4ea05dda04459433bc22471ea2b6f4f3dfc32`；app `12a773ef285ff34bf2bd25036fd3dff2930912bc`。
- worktree：维护 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260821h\m`；app `D:\IntRuoyiWorktree\r260821h\a`；publish 前均为 detached clean，未产生新提交。
- 构建包：`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260821-intmain-head-test-r260821h-r4`。
- 构建：operation `op-2026-08-21T204711713137200Z-9de34c7d-990f-4236-8d47-70be7309ce14` SUCCESS；manifest validator、sourceRepos、release-info、artifact hash 均通过。
- 发布：operation `op-2026-08-21T210307402431400Z-d11e3d45-06fb-4026-a039-a1ee4f70086b` FAILED，退出码 1；错误为 `MesProRouteVersionSnapshotMigrationRunner` 多构造函数无显式 `@Autowired`，Spring 报 `No default constructor found`。
- 远端影响：`.env IMAGE_TAG` 已变为 r4，但 backend 实际镜像仍为 `hotfix-20260814-route-submit-order-r1`，frontend 实际镜像仍为 `release-20260813-intmain-head-test-r260812b-r2`；旧容器 running、backend health=UP、frontend HTTP=200，frontend `release-info.json` 仍为旧版本。旧 `.env` 基线无法安全证明，未猜测回滚、未修改 release lock/migration、未重试。
- 范围：未执行 `mark-tested`、`promote-prod`、`promote-backup`；正式服和备份服未访问、未写入；r4 判废，不得复用。
- P026：r4 Docker backend 构建出现 `InvalidDefaultArgInFrom` warning。阶段=镜像构建；影响=本次构建成功但基础镜像 ARG 契约不明确；原因判断=Dockerfile 的 ARG 默认值与 FROM 组合未满足 BuildKit 静态检查；处理动作=记录 warning，未用 warning 代替产物验证；结果=镜像 digest 已验证，需进入 build 前置门禁；可前置检查=是；可自动化=是；下次避免=扫描 Docker build warning，命中该 warning 即修复或阻塞重建。
- P027：publish operation 原始日志写入了带密码参数的 MySQL 命令。阶段=迁移登记；影响=raw log 不可作为长期证据，存在凭据暴露风险；原因判断=发布脚本记录完整外部命令，未在日志层脱敏；处理动作=证据只保留脱敏摘要，不提交 raw log；结果=本轮不提交敏感日志，脚本缺陷待修复；可前置检查=是；可自动化=是；下次避免=统一日志脱敏并用 secret-pattern scan fail fast，禁止打印完整 MySQL 命令。
- P028：publish-test 先写远端 `.env`，后执行 BACKFILL，失败后出现 `.env`/实际镜像/release-info 漂移。阶段=失败收束；影响=测试服配置与真实运行态不一致；原因判断=写入、迁移和重启缺少失败事务边界及可证明的旧配置恢复；处理动作=冻结 operation、容器、health、HTTP、release-info 和 `.env`；因旧基线不可安全还原，停止猜测性回滚和重试；结果=阻塞；可前置检查=是；可自动化=是；下次避免=写入前保存旧 `.env` 哈希，失败自动恢复并验证 env/compose/实际镜像一致，否则 fail fast。
- P029：r4 route snapshot BACKFILL 暴露 Spring Bean 多构造函数缺少显式注入标注。阶段=publish-test 前置运行报告；影响=新 backend 镜像无法启动该报告，发布无法完成；原因判断=生产构造函数与测试构造函数并存，Spring 无法选择注入构造函数；处理动作=判废 r4，不在本轮修改冻结 app 代码；结果=需独立修复任务提交后以新 HEAD/new releaseTag 重建；可前置检查=是；可自动化=是；下次避免=build-release 前运行 Spring context smoke 或多构造函数 Bean 静态检查。
- P030：维护 release worktree 在 `scripts\build.ps1` 和控制台运行期间生成未跟踪 `runtime/` 目录。阶段=构建/控制台运行；影响=worktree 不再 clean，不能直接删除或作为后续发布输入；原因判断=构建/运行输出目录未完全隔离到 state-dir；处理动作=停止隔离控制台后保留目录和 worktree 供阻塞审计，不扩大清理；结果=任务阻塞期间不删除；可前置检查=是；可自动化=是；下次避免=构建后立即检测并按绝对路径清理本任务生成 runtime，或让所有运行输出固定写入 state-dir。
- P031：本轮隔离控制台停止后，48185 已无监听；稳定端口 48181 也未监听。阶段=阻塞收尾；影响=本轮不能宣称稳定运行控制台已恢复；原因判断=任务在 publish-test 失败后按阻塞规则停止临时控制台，未启动主工作区控制台；处理动作=不在失败发布任务中扩大到主工作区启动或远端状态修复；结果=作为阻塞收尾条件记录；可前置检查=是；可自动化=是；下次避免=只有发布成功并进入 closeout 时才执行稳定控制台恢复，恢复后验证 PID/JAR/config/state/health。
## 2026-08-22 构造注入修复提交

- 独立实现 worktree：`D:\IntRuoyiWorktree\route-snapshot-autowired-fix`；分支：`codex/20260821-route-snapshot-autowired-fix`。
- BDD：Given route snapshot migration runner 存在生产构造函数和测试构造函数，When Spring 启动发布前运行报告，Then runner 必须被正确实例化而不报 `No default constructor found`。
- RED：移除生产构造函数 `@Autowired` 后，Spring context 回归测试 FAIL，错误为 `BeanCreationException ... No default constructor found`。
- GREEN：恢复 `@Autowired` 后同一测试 PASS（1/1），目标 Maven reactor PASS，`git diff --check` PASS。
- 实现提交：`c4d2c637bf1f2cea723876ee363f311b1128aaf4`，主题 `任务: 修复路由快照运行器构造注入`；实现 worktree clean。
- P032：不复用失败的 r4；从已提交根因修复创建新冻结 app 发布输入，使用新 releaseTag 重建。
- P033：提交钩子曾因 detached HEAD、缺少 worktree port registry 及共享 registry 无关 active slot 31 阻止；切换任务分支并登记 task-owned slot 23（8157/48157）后提交成功。
- 下一步：从该提交创建新的专用发布 app worktree，与维护仓冻结 HEAD 配对，重新执行仅测试服发布。

## 2026-08-22 r260822a-r2 发布阻塞

- 本轮冻结输入：维护 `66c4ea05dda04459433bc22471ea2b6f4f3dfc32`，app 修复提交 `c4d2c637bf1f2cea723876ee363f311b1128aaf4`；发布 worktree 分别为 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260822a\m` 与 `D:\IntRuoyiWorktree\r260822a\a`，均从冻结提交创建，构建前 clean。
- 构建包：`E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260822-intmain-head-test-r260822a-r2`；build operation `op-2026-08-22T033833931534300Z-c3389b33-a5b1-44e0-9b17-e63dc07cce7e` SUCCESS；manifest validator PASS；sourceRepos commit=`c4d2c637bf1f2cea723876ee363f311b1128aaf4`、dirty=false；releaseTag/packageId 与变更说明 `任务: 修复路由快照运行器构造注入` 一致。
- publish operation `op-2026-08-22T035621436028400Z-55335b7f-e740-4d0f-a9d1-a85f875648fa` 只提交到 `test`，未执行 mark-tested/promote-prod/promote-backup；实际进入 route snapshot BACKFILL 前置运行器。
- P038：现象=route snapshot BACKFILL 报告为 `status=BLOCKED`、`blockerCount=882`；阶段=publish-test 运行报告；影响=测试发布未完成，不能切换目标镜像或判定成功；原因判断=测试服真实路由快照身份数据仍存在 882 个迁移门禁阻塞，构造注入修复只解决启动实例化问题，未消除业务数据 blocker；处理动作=读取报告状态后停止本次发布，删除任务创建的临时 backend runner，不修改业务数据、不修改 migration ledger、不重试同一 releaseTag；结果=发布阻塞，现有 backend/frontend 容器保持旧 tag。
- P039：现象=临时 route snapshot runner 在报告生成后未自行退出，发布脚本的 `docker compose run --rm` 长时间等待；按 task-owned 容器边界远程移除该临时 runner 后，未观察到目标 live backend/frontend 被停止；阶段=publish-test 失败收束；影响=操作无法自然进入最终状态，增加远端临时容器和等待耗时；原因判断=运行器失败/阻塞路径的容器退出与发布脚本等待边界不完整；处理动作=仅清理 `intruoyi-runtime-backend-run-5b246e6c431d`，保留失败报告摘要；结果=临时 runner 已清理，live 容器未切换。
- P040：现象=维护控制台 operation API 在临时 runner 清理后仍显示该 publish operation=`RUNNING`，状态文件未从初始状态更新，未满足 operation=SUCCESS；阶段=发布操作状态收束；影响=无法形成成功证据，且可能阻塞后续同环境操作；原因判断=异步命令执行器先阻塞读取子进程 stdout，命令超时只在流关闭后才检查，异常/强制清理路径没有可靠的 FAILED/STOPPED 状态收束；处理动作=不手工伪造 SUCCESS，不重复提交；记录为维护脚本/控制台缺陷，保留 operation 状态和脱敏日志；结果=任务阻塞，需修复状态机与命令执行器后用新 releaseTag 重跑。
- P041：现象=publish operation raw log 曾包含完整 MySQL 命令参数；阶段=迁移登记/失败收束；影响=原始日志不能作为证据，存在凭据泄露风险；原因判断=发布脚本 logger 记录了完整外部命令，未统一脱敏；处理动作=停止保留原始日志，原地重写为 UTF-8 脱敏日志并执行 secret-pattern 检查，任务文档不写入凭据；结果=日志已脱敏；下次必须在 publish 前置门禁中以样例测试 logger，并将命中 secret 直接 fail fast。
- P042：现象=逐文件 scp 与逐迁移 SSH/MySQL 登记耗时较长，publish operation 长时间停留初始摘要；阶段=发布过程；影响=人工等待与判断成本高，且容易误判为卡死；原因判断=脚本按文件/迁移串行执行，控制台只保存初始 summary；处理动作=按固定间隔读取 operation、脱敏日志、远端临时 runner 和 live 容器，不重复提交；结果=确认前期仍在推进，最终阻塞于 BACKFILL 报告；下次应记录阶段进度计数并设置真实无进展超时。
- P043：现象=测试服 `.env IMAGE_TAG`/Compose 目标已为 r2，但 live backend/frontend 实际镜像仍为旧 tag；阶段=publish-test 失败收束；影响=配置目标与真实运行态漂移，不能判定发布成功，也不能安全复用或重试 r2；原因判断=脚本在 BACKFILL 前先写 `.env`，失败/runner 清理路径缺少可证明的旧 env 自动恢复；处理动作=只读记录 `.env`、Compose、实际镜像和容器状态，不猜测旧值、不改 migration ledger/release lock、不重启 live 容器；结果=任务阻塞；下次必须在远端写入前保存旧 env 哈希/来源并实现失败自动恢复后复核。
- 失败态远端只读复核：测试服 `172.30.30.58` 的 live backend=`intruoyi-backend:hotfix-20260814-route-submit-order-r1`、live frontend=`intruoyi-frontend:release-20260813-intmain-head-test-r260812b-r2`，两容器仍 running；未执行前端版本验收，不能将旧容器 HTTP/health 200 作为本轮成功。
- 范围结论：未执行正式服/备份服写入，未执行 `mark-tested`、`promote-prod`、`promote-backup`；r260822a-r2 判废，不得复用或重试。

## Milestone Update 2026-08-22

- Milestone 3 构建发布包：completed。r260822a-r2 的 build-release、manifest、artifact hash、sourceRepos、版本号和 changeSet 均通过。
- Milestone 4 仅测试服发布：blocked。唯一 publish-test operation 未达到 SUCCESS，阻塞于 route snapshot BACKFILL 报告 `BLOCKED/882`，并出现 operation 状态未收束问题。
- Milestone 5 测试服真实运行态验证：blocked。目标镜像未切换，未进入页面/运行控制台版本验收。
- Milestone 6 问题记录与长过程复盘：completed。新增 P034-P043，记录依赖、构建 warning、manifest 字段、迁移耗时、route snapshot blocker、临时 runner、operation 状态、日志脱敏和 env/image 漂移问题。
- Milestone 7 经验沉淀与收尾：blocked。发布未成功；本轮发布 worktree 保留用于阻塞审计，未执行 closeout 删除或 completed 标记。

## 2026-08-22 继续执行复核

- 冻结输入未变化：维护 HEAD=`66c4ea05dda04459433bc22471ea2b6f4f3dfc32`，app HEAD=`c4d2c637bf1f2cea723876ee363f311b1128aaf4`；两个发布 worktree 仍 detached clean。
- 失败报告未变化：`status=BLOCKED`、`blockerCount=882`、`scannedCount=47`、`updatedCount=0`。
- 测试服只读复核：`.env IMAGE_TAG` 仍为 r2；实际 backend/frontend 仍为旧 tag 且运行中；临时 route runner 不存在。env 与实际镜像漂移仍未恢复，不能作为本轮发布成功证据。
- 本次新增问题 P049：首次远程复核探针因 PowerShell 多层引号解析失败，随后改用简单 SSH 只读命令成功复核；无远端副作用。完整字段见 `execution-log.md`。
- 当前状态继续为 `blocked`。不得复用 r2、不得修改 migration ledger/release lock/租户数据、不得跳过 BACKFILL/READINESS，不得删除本任务发布 worktree。

## 2026-08-22 blocker 租户精确关联补充

- 报告 882 条 blocker 已与真实 `mes_pro_route_version.id -> tenant_id` 只读关联，47/47 映射成功、0 条未映射。
- 精确分布：租户 1“芋道源码” 881 条；租户 122“测试租户” 1 条。租户 1 仍受保护，不能在本任务中修改；只修测试租户也不能满足全租户门禁。
- 冻结 app 代码和 enforcement SQL 均确认全量扫描/全表 blocker count 必须为 0；不能通过租户过滤、跳过 BACKFILL/READINESS 或只写身份 hash 发布。
- 新增 P050，完整现象、影响、处理动作和自动化建议见 `execution-log.md`。

## 2026-08-22 历史备份表证据补充

- 三份测试库历史 `m3syncbk_*_schedproc` 备份表交叉读取结果一致，证明旧 `routeProcessId=900124/900125/900126/900127` 的历史 process/config 身份，但未提供旧 ID 到当前路线工序 ID 的正式映射。
- 当前 `routeId=900025` 共 23 个工序，前四个新 `routeProcessId=926785/926786/926787/926788` 的 process ID、编码均已变化；名称重合或顺序相似不构成可审计映射，禁止猜测性修复。
- 证据文件：`doc/tasks/20260821-test-only-head-release/evidence/route-snapshot-orphan-route-process-history-r260822a.json`；`readOnly=true`、`writesPerformed=false`、`mappingSourceFound=false`、结论=`BLOCKED`。
- P062-P064 已补入 `execution-log.md`：历史来源不足、身份相似导致盲映射风险、一次未注入受控 MySQL 凭据的只读探针失败；探针已用受控环境变量重跑成功，未发生额外写入。
- 冻结 app 的 `docs/backend-development.md` 已作为正式规则证据复核：快照身份必须证明唯一映射，禁止按 `processId`、名称、`sort` 或运行态 fallback 推断旧 `routeProcessId`；本轮历史备份证据与该规则一致，新增 P065-P066 记录搜索范围和路径问题。
- 最终 worktree 复核再次复现 PowerShell 空管道语法问题，已修正并通过；P067 已记录，两个冻结 worktree 的 HEAD/clean 状态仍与任务记录一致。
- 当前状态保持 `blocked`：剩余 8 条 `ROUTE_PROCESS_UNRESOLVED` 未满足正式 BACKFILL/READINESS 门禁；不重建、不发布、不重试 r2，不删除发布 worktree。

## 2026-08-23 正式映射补全与修复迭代

- 已补齐正式旧新映射来源：测试库历史备份表 `m3syncbk_20260731025926_schedproc` 与当前 `mes_pro_route_version.id=3` 的 `flowGraph.nodes[*]` 形成唯一 1:1 对照；旧 `routeProcessId` `900124/900125/900126/900127` 分别对应当前 `926785/926786/926787/926788`。
- 这次补全只用于 test-server repair，不涉及正式服、备份服或任何 releaseTag 拼接；修复边界仍然只限 `mes_pro_route_version.id=3` 的 `scheduleConfigs[0..3].routeProcessId` 和 identity 列清空。
- 已生成 task-owned 修复 SQL：`D:\ProjectPackage\Int\IntRuoyiMaintance\doc\tasks\20260821-test-only-head-release\evidence\route-snapshot-repair-r260822a-r3.sql`；下一步是按现有 test-only DB 入口执行，然后立即重跑 BACKFILL / READINESS。
- 当前 `Current Status` 仍保持 `blocked`，直到新的 BACKFILL / READINESS 报告确认 `READY/0`。

## 2026-08-23 发布重试失败与状态收束

- P068：现象=首次重试误调用主工作区脚本，因主工作区与冻结发布 worktree 的迁移 SQL 集合不同而报 `Release migration metadata missing`；阶段=发布脚本入口；影响=该次未进入远端容器切换，未形成发布成功证据；原因判断=未在执行前校验脚本路径、脚本 HEAD 与冻结发布输入一致；处理动作=停止并改用冻结 app worktree 的发布脚本；结果=误调用已废止，不作为发布结果；可前置检查=是；可自动化=是；下次避免=发布前强制校验脚本绝对路径、脚本 blob SHA、worktree HEAD 与 package manifest。
- P069：现象=冻结脚本使用旧 MinIO 容器名 `intruoyi-minio`，测试服务器实际容器为 `ragflow_compose-minio-1`；阶段=远端对象锁与 Docker 前置检查；影响=首次正确入口在远端前置阶段失败；原因判断=服务器文档/历史 NAS 配置与当前运行态名称不一致；处理动作=按测试服务器真实运行态改用 `ragflow_compose-minio-1`；结果=前置检查继续通过；可前置检查=是；可自动化=是；下次避免=发布前只读探测并固定目标容器 ID/名称，名称不匹配即 fail fast。
- P070：现象=冻结发布脚本调用严格 smoke wrapper 时未导出 `MES_SMOKE_NODE_IMAGE`，返回 `MES_SMOKE_NODE_IMAGE is required`；阶段=发布前 smoke；影响=发布在容器切换前失败；原因判断=冻结脚本与当前 wrapper 环境契约不一致；处理动作=未在冻结 worktree 中临时修补，记录为需要新提交、新冻结 worktree、新 releaseTag 和重建的正式缺陷；结果=当前 r2 产物不可判定成功；可前置检查=是；可自动化=是；下次避免=构建后执行 smoke wrapper 参数/环境契约静态检查。
- P071：现象=临时尝试 source 远端完整 `.env` 后出现 `-Xmx2g: not found`；阶段=失败排障；影响=排障重试失败，未改变业务数据或容器；原因判断=`.env` 含非 shell-safe 的 JVM 参数行，不能整体 source；处理动作=停止并恢复冻结脚本原内容；结果=未保留临时补丁；可前置检查=是；可自动化=是；下次避免=只允许名单化读取 `MES_SMOKE_*` 变量，禁止 source 完整 `.env`。
- P072：现象=复杂远端 shell 的 PowerShell 字符串插值产生不安全临时补丁；阶段=失败排障；影响=未形成可审计修复，增加重复操作时间；原因判断=将多行远端脚本直接嵌入 PowerShell；处理动作=不继续使用临时内联修补；结果=冻结脚本恢复同源内容；可前置检查=是；可自动化=是；下次避免=复杂远端脚本必须以 UTF-8/LF 文件传输并校验 SHA 后执行。
- P073：现象=一次宽范围 `pgrep -af` 可能回显带凭据的命令行；阶段=远端进程排查；影响=产生敏感输出暴露风险；原因判断=进程查询范围过宽；处理动作=停止并丢弃原始输出，改用限定进程名/返回码探针；结果=未写入任务证据或提交日志；可前置检查=是；可自动化=是；下次避免=禁止记录完整命令行，只记录窄化进程存在性与退出码。
- P074：现象=route snapshot enforcement 在容器切换前失败，精确 release operation lock 与 migration ledger 留在 `RUNNING`；阶段=发布失败收束；影响=阻塞后续同目标重试并可能误判发布状态；原因判断=发布脚本在失败路径未完成状态收束；处理动作=先执行任务拥有的精确 test-only recovery SQL，再只读核验 `RUNNING=0`；结果=恢复完成前保持 `blocked`，不继续发布；可前置检查=是；可自动化=是；下次避免=发布脚本必须提供失败路径 finally/recovery，并将 stale RUNNING 作为下一步发布的 fail-fast 条件。
- P075：现象=冻结 app worktree 曾出现同内容 CRLF/index 状态差异；阶段=冻结输入完整性复核；影响=短暂显示工作区变化，存在误判构建输入被修改的风险；原因判断=恢复文件时行尾/索引元数据变化；处理动作=核对 blob SHA、工作树 diff 与 cached diff，确认内容回到冻结提交；结果=冻结 worktree 内容一致；可前置检查=是；可自动化=是；下次避免=冻结 worktree 创建后禁止编辑，脚本修复必须走新提交和新冻结 worktree。
- 当前结论：构建产物与 manifest 证据仍有效，但正确冻结入口的发布 operation 未成功，远端 backend/frontend 实际镜像仍为旧 tag；本轮不得判定测试发布成功、不得执行 `mark-tested`、`promote-prod` 或 `promote-backup`，冻结 worktree 与失败发布目录保留待收束。
- P076：现象=第一份 stale recovery SQL 将 migration 的 `operation_id` 假定为 `test-<releaseTag>`，官方入口返回 `MIGRATION_RECOVERY_NOT_UPDATED`，而 operation lock 已更新；阶段=失败发布状态恢复；影响=首次恢复未清除 migration 的 `RUNNING` 状态；原因判断=lock 表与 migration 表的 operation_id 契约不同，未先读取精确元数据；处理动作=只读查询该 releaseTag 的 migration 行，确认 migration 使用 releaseTag 本身后停止猜测并生成精确 recovery SQL；结果=待官方 test-only 入口应用并复核；可前置检查=是；可自动化=是；下次避免=恢复前必须分别读取两表的 exact key，不得复用 operation lock 的 operation_id 规则。
- P077：现象=按 releaseTag 读取全部 migration 行输出过大并被截断；阶段=失败状态元数据核查；影响=不能把截断输出作为完整证据，增加审计成本；原因判断=查询未限定到目标 migration_id；处理动作=丢弃截断输出，保留仅精确目标行和 RUNNING 计数的窄化查询；结果=取得 operation_id 差异证据；可前置检查=是；可自动化=是；下次避免=所有远端状态查询必须按 releaseTag + operation/migration id 限定，并限制输出列。
- 2026-08-23 只读复核结果：`infra_release_operation_lock` 与 `infra_release_migration` 均已转为 `FAILED`，test 环境 `RUNNING` lock/migration 均为 `0`；这只代表失败状态已收束，不代表测试发布成功。

## 2026-08-23 scheduler smoke env repair iteration

- P078：现象=重新执行冻结发布命令时遗漏 `-TestServerHost 172.30.30.58`，脚本在参数绑定阶段 fail fast；阶段=发布命令预检；影响=未进入远端发布动作，无容器或数据库副作用；原因判断=手工重跑命令时未把测试服主机参数显式带上；处理动作=补齐测试服主机参数后继续重试；结果=已清除该命令错误；可前置检查=是；可自动化=是；下次避免=发布重试前固定从 task log 复制完整参数，不要手打补参。
- P079：现象=继续重试时又遗漏 `-BackupServerHost 172.30.30.59`，脚本再次 fail fast；阶段=发布命令预检；影响=未进入远端发布动作；原因判断=只补了测试服主机，未同步补齐脚本要求的备份服地址；处理动作=补齐备份服参数后再次重试；结果=进入真实 deploy-release 链路；可前置检查=是；可自动化=是；下次避免=测试/备份/正式目标主机参数都必须按脚本约束一次性提供。
- P080：现象=远端 scheduler smoke wrapper 在 `install/exec/run` 阶段读取不到 `MES_SMOKE_NODE_IMAGE`，返回 `MES_SMOKE_NODE_IMAGE is required`；阶段=deploy-release 远端 smoke 复制后；影响=发布卡在 smoke 阶段，未进入后续运行态验收；原因判断=发布脚本虽然写入远端 `.env`，但调用 smoke wrapper 时没有把 `MES_SMOKE_NODE_IMAGE` 显式带入命令环境；处理动作=在新干净 worktree `D:\IntRuoyiWorktree\r260823a\a`（branch `codex/release-smoke-node-image-export`）补契约测试并修复脚本；结果=本地契约测试已通过，待提交、重建和重新发布；可前置检查=是；可自动化=是；下次避免=远端 smoke wrapper 的关键环境变量必须在命令行显式导出，不能只写入远端 `.env`。
- 当前结论：r2 仍未成功发布；新的修复 worktree 已建立，但还未完成提交、重建和再次测试服发布。正式成功前，仍不得判定完成。
