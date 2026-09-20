# Verification Report

## Verdict

FAIL — 代码与本机静态门禁已显著收敛，但真实生产执行链、维护仓主干融合和最终按钮发布仍未完成，因此当前不得发布正式服。

## Requirement Evidence

| # | 要求 | 当前证据 | 结论 |
|---|---|---|---|
| 1 | 多步骤迁移事务保护 | 两个迁移包含显式事务/异常回滚；真实 MySQL 后续触发器故障验证原数据不变 | PASS |
| 2 | 取得锁后异常统一释放 | 发布脚本取得锁后的上传、迁移、切换与验收位于统一 try/catch；仅持锁者执行失败释放 | PASS（静态/合同） |
| 3 | 锁持有到完整验收与历史记录 | `APPLIED` 释放位于 HTTP/PDF 与部署历史记录之后 | PASS（静态/合同） |
| 4 | 同 worktree 原子构建互斥 | state-dir OS 文件锁；两个独立 store 竞争仅一个成功，按 operationId 释放，进程退出后遗留标记不阻断重启 | PASS |
| 5 | 命令超时/中断可靠 | 异步日志泵、独立 waitFor；真实 PowerShell 中断测试证明进程被终止 | PASS |
| 6 | 预览源码绑定执行 | 预览 token 绑定维护/应用 HEAD、路径和 releaseTag；执行缺失/不匹配返回 400 | PASS |
| 7 | 终态与日志/经验归档解耦 | operation 终态先持久化；真实不可写日志测试后状态仍为 FAILED | PASS |
| 8 | 租约 token 全路径脱敏 | 命令日志和启动 IOException 共用脱敏；真实启动失败测试不含 token | PASS |
| 9 | 预检与迁移条件一致 | 空 `menu_ids` 真实 MySQL RED/GREEN；目标预检矩阵 170 passed | PASS（已知审阅范围） |
| 10 | 真实生产执行链行为测试 | 融合 worktree 实际恢复脚本经 PowerShell→SSH→bash→测试服 intruoyi-mysql 临时库通过行尾归一化、活跃心跳、并发恢复与精确终态；完整 deploy-release 失权后的业务写入仍需随测试服按钮链验证 | PARTIAL |
| 11 | 正确诊断顺序 | 本轮先真实谓词/实库复现，再修复和全量静态回归，未以按钮构建逐项试错 | PASS |
| 12 | 维护仓主干融合与收尾 | 修复仍在保护 worktree；维护主工作区脏且维护仓无 remote | FAIL |
| 13 | 一键正式发布最终验收 | 尚未执行同一 releaseTag 的真实按钮完整链路和正式运行态验收 | FAIL |

## Verification Commands

- `mvn -q test package` -> PASS。
- `corepack pnpm typecheck`、`corepack pnpm build` -> PASS。
- 维护发布锁/SQL/包治理回归 -> `146 passed`。
- 目标预检/迁移矩阵/SQL/包治理回归 -> `170 passed`。
- 应用迁移真实 MySQL 与合同 -> `10 passed`。
- 应用迁移策略门禁 -> PASS，`migrationCount=632`。
- `publish-int-ruoyi.ps1`、`recover-release-operation-lock.ps1` AST -> PASS。

## Remaining Gates

1. 在测试服真实按钮 deploy-release 中补齐失权后的业务写入阻断与发布失败清理证据；恢复脚本的 PowerShell/SSH/MySQL 整链已通过隔离临时库验证。
2. 将当前融合提交安全合回维护 `int_main`；主工作区已有并行脏改动，当前只保留独立融合 worktree。
3. 创建全新临时发布 worktree，以同一 releaseTag 通过真实页面按钮完成 build-release、publish-test、真实测试验收、mark-tested、promote-prod 和正式运行态验收。
