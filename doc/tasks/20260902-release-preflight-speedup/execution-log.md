# 执行日志

## 2026-09-02

- 用户意图：希望加速部署过程，并防止以后再出现类似“到测试服 publish-test 才暴露”的真实门禁问题。
- 边界：本任务只修改本地发布前置检查、测试和经验文档；不访问、不重启、不修改测试服、正式服或备份服。
- BDD: required SQL 标识符长度前置门禁 -> Given 发布包包含 required SQL When build-release 前运行本地 migration/preflight gate Then 超过 MySQL 64 字符的约束/索引/例程/事件标识符必须 fail fast，不得等 publish-test 执行真实库时报 ERROR 1059。
- BDD: 发布加速不降级验收 -> Given 本地门禁提前失败 When 修复后重新发布 Then 仍必须保留 manifest、sourceRepos dirty=false、operation、`.env IMAGE_TAG`、实际镜像、health、HTTP、版本说明和页面验收。
- GREEN: experience-preflight -> PASS。已读取 `ci-cd-environment-delivery`、`preflight-experience-consolidation`、构建/发布/PowerShell reference；任务范围限定为本地前置门禁与经验沉淀。
- RED: `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q -k "identifier_length" --basetemp D:\ProjectPackage\Int\IntRuoyiWorktrees\release-preflight-speedup-state\pytest-red` -> FAIL，`expected migration policy gate to propagate identifier length failure`，证明 MySQL 64 字符标识符未被构建前门禁拦截。
- RED: `mvn -f backend\pom.xml -Dtest=RuntimeControlOperationStoreTest test` -> FAIL，`RuntimeControlOperationStore.listLatest` 尝试读取 state 根目录 `migration-policy.json` 并报错，证明 operation 列表会被非 operation JSON 污染。
- GREEN: identifier-sql-gate -> PASS。`release_sql_contract_gate.py` 新增 `CONSTRAINT`、`INDEX/KEY`、`TRIGGER`、`PROCEDURE`、`FUNCTION`、`EVENT` 标识符长度检查，超过 MySQL 64 字符直接报告文件/行号；`pytest ... -k "identifier"` 通过 `2 passed`。
- GREEN: operation-state-root-gate -> PASS。`RuntimeControlOperationStore` 的 `listLatest` 只读取根目录 `op-*.json`，任务证据 JSON 不再拖死 operations API；`RuntimeControlOperationStoreTest` 通过。
- GREEN: regression -> PASS。`python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py scripts\tests\test_publish_dcc_codex_runtime_contract.py -q --basetemp D:\ProjectPackage\Int\IntRuoyiWorktrees\release-preflight-speedup-state\pytest-regression` -> `62 passed`。
- GREEN: syntax -> PASS。`python -X utf8 -m py_compile ops\release\release_sql_contract_gate.py` 和 `ops\deploy\publish-int-ruoyi.ps1` PowerShell AST parse 通过。
- GREEN: backend-regression -> PASS。`mvn -f backend\pom.xml test` -> `27 passed`。
- GREEN: experience-consolidation -> PASS。已更新 `docs/release-agent-checklist.md`、`docs/release-build-preflight-lessons.md`、`docs/experience-index.md` 和 `docs/request-command-log.md`，将本次问题写为发布前可执行门禁。
- GREEN: closeout-preview -> PASS。`task-closeout-cleanup` preview 保留 `task.md`、`execution-log.md`、`verification-report.md`，工作区内无可删项、无 blocked。
- GREEN: closeout-apply -> PASS。`task-closeout-cleanup` apply 成功，工作区内无删除项。
- BLOCKER: final-closeout -> 本仓在任务开始前已有多份长期文档和发布任务记录脏改动；本次新增经验也写入其中，不能安全地整文件提交而不混入非本任务改动。另，本任务外部 pytest state 目录 `D:\ProjectPackage\Int\IntRuoyiWorktrees\release-preflight-speedup-state` 清理命令被工具安全策略拦截，保留为待清理残留。当前实现与验证完成，但未执行 commit，任务保持 `ready_for_closeout`。

## Issues

- ISSUE-001: 现象=首次 pytest 使用全局 `%TEMP%\pytest-of-BJB110` 报 `PermissionError: [WinError 5] 拒绝访问`；阶段=RED 复现；影响=业务 RED 未执行；原因判断=全局 pytest 临时目录 ACL/残留问题；处理动作=改用本任务专属 `--basetemp D:\ProjectPackage\Int\IntRuoyiWorktrees\release-preflight-speedup-state\...`；结果=RED/GREEN 均可复现；是否可前置检查=是；是否可自动化=是；下次如何避免=发布/门禁 pytest 统一指定任务自有 basetemp。
- ISSUE-002: 现象=MySQL `ERROR 1059` 类问题只能到真实 publish-test 执行 SQL 时暴露；阶段=构建前门禁缺口；影响=重复 build-release、上传和失败恢复，耗时明显增加；原因判断=required SQL 静态合同未扫描 MySQL 64 字符标识符限制；处理动作=新增 SQL 标识符长度门禁和 policy gate 传播测试；结果=本地 build-release 前即可 fail fast；是否可前置检查=是；是否可自动化=是；下次如何避免=先跑 migration policy gate，再进入耗时构建。
- ISSUE-003: 现象=运行控制台 operations API 会读取 state 根目录非 operation JSON（如 `migration-policy.json`）并失败；阶段=operation 观察；影响=发布状态观察中断，容易误以为 operation 本身异常；原因判断=operation store 按 `*.json` 全量读取；处理动作=只读取 `op-*.json` operation state 文件；结果=非 operation 证据 JSON 不影响 operation 列表；是否可前置检查=是；是否可自动化=是；下次如何避免=任务证据写入 `evidence/`，operation 根目录只保留 `op-*.json`。
- ISSUE-004: 现象=Maven RED 输出中的中文异常在控制台显示为乱码；阶段=Java RED 证据读取；影响=不影响失败定位，但降低日志可读性；原因判断=Maven/JVM 控制台编码与 PowerShell UTF-8 设置未完全对齐；处理动作=本次记录英文类名和路径作为证据；结果=GREEN 后无残留失败；是否可前置检查=是；是否可自动化=是；下次如何避免=需要中文异常可读时显式增加 JVM/Maven UTF-8 参数并记录。
- ISSUE-005: 现象=新增 Java 回归测试路径 `backend/src/test/java/com/intruoyi/maintenance/runtime/...` 被本地 `.git/info/exclude` 的 `runtime/` 规则忽略；阶段=提交前 Git 可见性检查；影响=如果不强制纳入，测试文件可能只在本机存在而提交遗漏；原因判断=本地 exclude 规则过宽；处理动作=执行 `git add -N -f -- backend/src/test/java/com/intruoyi/maintenance/runtime/RuntimeControlOperationStoreTest.java` 使其进入 Git 可见 diff；结果=`git status` 显示 `A`；是否可前置检查=是；是否可自动化=是；下次如何避免=新增 `runtime` 包路径文件后运行 `git check-ignore -v` 和 `git status --short --untracked-files=all`。
- ISSUE-006: 现象=外部 pytest state 目录清理命令被工具安全策略拒绝；阶段=任务收尾；影响=留下可再生临时目录，不影响代码和测试结论；原因判断=工具拒绝递归删除命令；处理动作=已只读确认路径在 `D:\ProjectPackage\Int\IntRuoyiWorktrees` 下且只含本任务 pytest 目录，未尝试绕过策略；结果=目录保留待人工或后续授权清理；是否可前置检查=是；是否可自动化=部分；下次如何避免=优先将 pytest basetemp 放在 workspace 内 task cleanup 可处理的位置，或在任务开始记录可清理路径并使用受支持清理脚本。
