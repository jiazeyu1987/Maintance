# Verification Report

## Verdict

REMEDIATION IN PROGRESS / REVIEW REQUIRED — 主程序工作流、专用按钮和维护发布器的路径/摘要绑定已提交并融合两个本地主干；实际控制台尚未加载新代码，配置/权限和真实按钮验收均未完成。用户新增独立复检门禁；审阅任务明确“同意发布”之前不得执行测试服部署、mark-tested 或正式晋级。r105 构建已 FAILED，未完成发布。

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

## Verification Commands

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

1. 已确认应用本地 `int_main=4b556f2de` 与 `origin/int_main` 一致；维护本地 `int_main=5bde76f` 已包含发布整改。无需再等待远端同步授权。
2. 本地主干已融合；需独立复检，且实际控制台加载新提交前不得开始发布。发布配置必须绑定新的冻结 worktree、批准提交和该工作树上维护脚本的实际文件 SHA，不能使用默认主工作区路径、空摘要或别的工作树 SHA。权限 SQL 不自动给任何角色授权，正式晋级操作人必须有经批准的菜单角色绑定或原有超管权限。
3. 整改完成后通知用户安排 `codex://threads/01a0bd1f-ea37-7112-bdc5-4673055ff2c0` 复检。只有其明确“同意发布”后，才能新建本次专用发布 worktree、重新冻结新 releaseTag，通过真实主程序按钮执行测试服和正式服闭环；在此之前不做发布写入。
