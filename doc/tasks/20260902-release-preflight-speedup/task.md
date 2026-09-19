# 20260902 发布加速与真实门禁前置任务

## Task Goal

把本次测试服发布中暴露的“真实门禁问题”尽量前移到本地构建前检查，减少重复构建、重复上传和重复 publish-test 失败；重点先覆盖 MySQL 标识符长度、发布状态目录污染和构建复制性能三类已出现问题。

## Milestones

1. 启动门禁：读取发布、构建、PowerShell 与前置经验规则，明确不操作测试/正式/备份服务器。
2. RED 复现：用静态合同证明现有发布前检查不能提前拦截 MySQL 64 字符标识符问题。
3. 最小实现：补齐构建前 required SQL 静态门禁，并复用/加强已有构建复制性能合同。
4. GREEN 验证：运行目标测试、PowerShell 解析和 diff 检查。
5. 经验沉淀：更新发布前置经验、索引和任务证据，形成下次发布前必查项。

## Expected Verification

- 本地检查能在 build-release / publish-test 前发现 SQL 中超过 MySQL 64 字符的约束、索引、触发器、过程、函数、事件或临时检查名。
- 运行维护仓相关 pytest 合同通过。
- 发布脚本 PowerShell 解析通过。
- 不访问、不重启、不修改测试服、正式服或备份服。

## 经验门禁

- Trigger: 测试服发布、required SQL、migration policy gate、MySQL ERROR 1059、发布加速、构建前 fail fast。
- Preflight check: 发布前必须在 clean release worktree 运行 required SQL 静态门禁；可在本地确定的问题必须在 build-release 前失败，不得等到 publish-test 对真实库执行才暴露。
- Blocker: SQL 标识符超过 MySQL 64 字符、release state 根目录混入非 operation state 文件、构建上下文复制未启用并行/完整性校验、或门禁结果无法追溯到本次 release worktree。
- Verification: 记录 RED/GREEN 测试命令、命中的 SQL 文件/行号、发布脚本解析结果和经验索引关键词检索结果。
- Forbidden action: 禁止手工改测试库绕过 required SQL；禁止复用失败 releaseTag；禁止为了提速跳过 manifest/sourceRepos/dirty/health/HTTP/版本说明等真实验收；禁止把真实门禁降级为 warning。
- Evidence: 本任务 `execution-log.md` 与 `verification-report.md`。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，目标是把确定性失败转为发布前 fail fast。
- 是否存在临时补丁或绕过：否。

## Current Status

ready_for_closeout

## Milestone Status

1. 启动门禁：completed。已读取 CI/CD 与前置经验技能、构建/发布/PowerShell/worktree 引用、项目经验索引；本任务边界限定为本地脚本、运行控制台读取逻辑、测试和经验文档，不访问服务器。
2. RED 复现：completed。SQL 标识符长度测试先失败；运行控制台 operation store 测试先因 `migration-policy.json` 非 operation JSON 报错失败。
3. 最小实现：completed。`release_sql_contract_gate.py` 新增 MySQL 64 字符标识符门禁；`RuntimeControlOperationStore` 列表仅读取 `op-*.json`。
4. GREEN 验证：completed。目标 pytest、维护后端 Maven 测试、Python 编译和 PowerShell AST 均通过。
5. 经验沉淀：completed。已更新发布 checklist、发布构建前置经验、经验索引和 request-command-log。
