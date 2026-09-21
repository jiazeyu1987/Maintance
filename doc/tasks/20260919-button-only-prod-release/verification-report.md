# Verification Report

## Verdict

BLOCKED / NOT READY FOR INDEPENDENT RECHECK — 第十轮 R10-1 预览真实证据核验在隔离组件和本机 PowerShell 合同中转绿；R10-2 新版主程序通过真实 admin 页面可达，但测试租户凭据缺失、本机 promote-prod 菜单尚未迁移、总览自动远端只读探测失败，权限及页面验收未闭合。审阅任务仍为 BLOCKED；未明确“同意发布”前禁止构建、部署、mark-tested 或晋级。r105 已判废，r106 从未构建。

## 第十轮增量（当前）

| 项目 | 证据 | 状态 |
|---|---|---|
| R10-1 正式预览 | `c8edc935c`：预览只读重读 NAS manifest/tested、成功测试 operation/标准文件及维护发布器实际 SHA；eligible 快照在 grant/派发前重检。缺失、字段漂移、损坏原始 operation、执行器指纹错误均 BLOCKED，TESTED 不变、无 grant/生产 operation；执行阶段原双摘要/脚本检验保留 | 本地组件 PASS，实际 NAS/正式环境 NOT RUN |
| 跨仓证明合同 | 应用 operation 成功后原子写标准 `SUCCESS`/UTC 证明；`ReleaseWorkflowTestEvidenceStoreTest` 真实调用维护 `ReleasePackageGovernance.psm1` 的 `Assert-PublishTestOperationEvidence` PASS；NAS tested.json 按原始字节解析并计 SHA，损坏 JSON 拒绝 | 本机真实模块 PASS |
| 回归 | 扩大 `RuntimeControl*Test,ReleaseWorkflow*Test` Maven、前端 `ts:check`、静态按钮合同、`git diff --check` 均 exit 0；代码提交 `c8edc935c` 尚在同任务分支，未合主干/推送 | PASS（本地） |
| 新版本运行身份 | clean `c8edc935c` 构建本机 JAR SHA-256 `8F85E6B2...`，PID 9884 曾运行于 48086，前端 8086；进程 JAR 路径/哈希与构建文件一致，生产写开关 false、Quartz 和本地 job-control false；GET `/admin-api/infra/runtime-control/release-workflows` 200；任务进程现已退出 | 部分 PASS |
| Playwright 页面 | 固定 1.60.0 + 显式 Chromium 1223，从 8086 登录页经真实菜单进入 `/infra/monitors/runtime-control`。工作流面板可见；发布原因为空时构建按钮禁用，填写后仅观察启用、不点击；无合格 TESTED 包，晋级按钮 0，旧通用正式按钮 0。浏览器只记录脱敏 GET 路径/状态；截图在任务输出目录 | admin 只读 PASS；测试租户 NOT RUN |
| 权限和总览 | 只读库核测试租户 122 的 `aoteman` 现有 super_admin 与 query/operate/restart 角色绑定；本地尚无新增 promote-prod 菜单。既有总览自动调用远端只读状态脚本并出现 SSH/shell 错误；不能以禁写配置误当禁读，也不在未明确边界下继续远端探测 | BLOCKED |

未覆盖：缺真实合格 TESTED 包，不能在页面点 production preview 正向路径或做实际 NAS/目标运行态复验；缺测试租户登录凭据与明确远端只读边界，无法完成该身份的菜单/独立生产权限和错误反馈 E2E。没有执行任何新发布写入或创建生产 operation；本轮页面证据不证明可正式发布。

## Requirement Evidence

| # | 要求 | 当前证据 | 结论 |
|---|---|---|---|
| 1 | 多步骤迁移事务保护 | 两个迁移包含显式事务/异常回滚；真实 MySQL 后续触发器故障验证原数据不变 | PASS |
| 2 | 取得锁后异常统一释放 | 只读确认锁表契约后先取锁，再执行数据盘挂载、目录清理/创建、上传、迁移、切换与验收；整段位于统一 try/catch，仅持锁者释放 | PASS |
| 3 | 锁持有到完整验收与历史记录 | `APPLIED` 释放位于 HTTP/PDF 与部署历史记录之后 | PASS（静态/合同） |
| 4 | 同 worktree 原子构建互斥 | state-dir OS 文件锁；两个独立 store 竞争仅一个成功，按 operationId 释放，进程退出后遗留标记不阻断重启 | PASS |
| 5 | 命令超时/中断可靠 | 异步日志泵、独立 waitFor；真实 PowerShell 中断测试证明进程被终止 | PASS |
| 6 | 预览源码绑定执行 | 预览 token 绑定维护/应用 HEAD、路径和 releaseTag；执行缺失/不匹配返回 400 | PASS |
| 7 | 终态与日志/经验归档解耦 | operation 终态先持久化；真实不可写日志测试后状态仍为 FAILED | PASS |
| 8 | 租约 token 全路径脱敏 | 命令日志和启动 IOException 共用脱敏；真实启动失败测试不含 token | PASS |
| 9 | 预检与迁移条件一致 | 空 `menu_ids` 真实 MySQL RED/GREEN；目标预检矩阵 170 passed | PASS（已知审阅范围） |
| 10 | 真实生产执行链行为测试 | 生产迁移写入函数经实际 PowerShell→SSH→测试服 MySQL 临时库验证：持锁写入成功，租约替换后写入失败且无新台账；实际恢复脚本的活跃心跳、并发单赢家和精确终态同步通过，临时库已清零 | PASS（隔离真实链） |
| 11 | 正确诊断顺序 | 本轮先真实谓词/实库复现，再修复和全量静态回归，未以按钮构建逐项试错 | PASS |
| 12 | 维护仓主干融合与收尾 | 前序修复已融合；本轮追加发布器摘要绑定融合到维护 `int_main=1ce47ef`，应用工作流融合到 `int_main=f797a49fa`。并行脏文件同路径交集均为 0；维护融合结果 124 项发布回归 PASS，维护仓无 remote。临时 worktree 尚保留以待审阅/发布后收尾 | PARTIAL（融合通过，任务未收尾） |
| 13 | 一键正式发布最终验收 | 本地主干已有专用 workflow/preview/grant、页面按钮、同包摘要校验和受控维护发布器指纹绑定；实际控制台未加载新版本，更无真实按钮部署与正式服验收。独立复检未放行 | BLOCKED（待复检/真实验收） |

## 本轮增量验证

- 本机维护包治理 78/78、发布预检/锁/应用治理 46/46；PowerShell AST PASS。
- 主程序运行控制定向 104/104 与扩大 `RuntimeControl*Test,ReleaseWorkflow*Test` 最后一轮 PASS；前端 `ts:check`、专用按钮静态合同、入口静态测试 2/2 PASS。
- 新权限 SQL 的隔离 MySQL 测试 4/4，含本机真实菜单 ID 冲突、缺失/重复父菜单、错误父节点、插入异常回滚及幂等；全部临时库已删除。全量迁移策略 634 PASS。
- 以上均不是生产环境页面验收或实际发布成功证明。控制台未加载本轮新提交，`productionWriteEnabled` 与批准提交/脚本 SHA 配置尚待冻结后的明确设置。
- 本轮提交与融合：应用 `f797a49fa`、维护实现 `b55c9d2` / 本地主干 `1ce47ef`；维护融合后的 124 项发布相关测试 PASS。r106 从未构建且原源码冻结失效，后续必须新 worktree/new tag。

## 前序验证命令（历史，非第十轮发布许可）

- `mvn -q test package` -> PASS。
- `corepack pnpm typecheck`、`corepack pnpm build` -> PASS。
- 维护发布、锁、预检与包治理回归 -> `212 passed`。
- 目标预检/迁移矩阵/SQL/包治理回归 -> `170 passed`。
- 应用迁移真实 MySQL 与合同 -> `15 passed`。
- DCC 注册证完整定向类 -> `6/6 passed`；配套迁移合同/真实 MySQL/策略定向回归 -> `18 passed`。
- 应用迁移策略门禁 -> PASS，`migrationCount=632`。
- `publish-int-ruoyi.ps1`、`recover-release-operation-lock.ps1` AST -> PASS。
- 维护后端全量 `mvn -q test package` -> 40 tests，0 failures/errors，package PASS；维护前端 typecheck/build -> PASS。

## Remaining Gates

1. 应用 `int_main/origin=int_main=f797a49fa` 为前轮基线；本轮预览整改 `c8edc935c` 仅在任务分支，未融合/推送。维护本地主干含上轮修复且无 remote，不得将基线提交当作本轮代码运行身份。
2. 测试租户 `aoteman` 真实登录凭据缺失；本机新 permission 菜单尚未执行迁移，不能扩大主租户或其它角色权限制造按钮可见。需确认本地控制台总览自动只读探测远端的授权边界，并修复/记录既有 SSH 脚本失败后，才能继续该页面 E2E；不能通过 mock 或禁读伪装。没有 TESTED 包时正向 production preview 合理 NOT RUN。
3. 补齐 R10-2 后更新机器状态与脱敏页面证据，通知用户安排 `codex://threads/01a0bd1f-ea37-7112-bdc5-4673055ff2c0` 复检。只有其明确“同意发布”后，才能新建专用冻结 worktree、绑定实际脚本 SHA 和批准提交并使用新 releaseTag；在此之前不做发布写入。
