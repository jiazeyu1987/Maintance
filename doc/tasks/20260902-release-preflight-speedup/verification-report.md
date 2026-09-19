# 20260902 发布加速与真实门禁前置验证报告

## Summary

`PASS_WITH_CLOSEOUT_LIMITATIONS`。本任务已把两类会拖慢发布的真实门禁前移：required SQL 的 MySQL 64 字符标识符限制，以及运行控制台 operation state 根目录非 operation JSON 污染。未访问、重启或修改测试服、正式服、备份服。

## Environment

- 本地维护仓：`D:\ProjectPackage\Int\IntRuoyiMaintance`
- 任务目录：`doc/tasks/20260902-release-preflight-speedup`
- 外部环境：未访问测试服、正式服或备份服；本任务只改本地代码、测试和文档。

## Commands

- RED SQL：`python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py -q -k "identifier_length" --basetemp <task-state>\pytest-red`
- RED Java：`mvn -f backend\pom.xml -Dtest=RuntimeControlOperationStoreTest test`
- GREEN pytest：`python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py scripts\tests\test_publish_dcc_codex_runtime_contract.py -q --basetemp <task-state>\pytest-regression`
- GREEN backend：`mvn -f backend\pom.xml test`
- Syntax：`python -X utf8 -m py_compile ops\release\release_sql_contract_gate.py`；`ops\deploy\publish-int-ruoyi.ps1` PowerShell AST parse。

## Secrets

未使用、读取或记录密码、token、私钥、连接串、完整 `.env` 或 raw secret-bearing operation log。

## Pipeline

- `release_sql_contract_gate.py` 在 migration policy gate 内执行；发布前本地门禁先于依赖恢复、前端构建、Maven 打包和远端 publish-test。
- `RuntimeControlOperationStore.listLatest` 仅读取 `op-*.json`，避免 state 根目录中的任务证据 JSON 破坏 operations API。
- 既有发布真实验收不降级：releaseTag、manifest、sourceRepos dirty=false、远端 `.env IMAGE_TAG`、实际镜像、health、HTTP、版本说明和页面验收仍必须保留。

## Verification

- SQL 标识符 RED：失败原因为 `expected migration policy gate to propagate identifier length failure`。
- operation state RED：失败原因为读取 `migration-policy.json` 非 operation JSON。
- pytest GREEN：`62 passed`。
- Maven GREEN：`27 passed`。
- Python 编译与 PowerShell AST：通过。

## Rollback

- 回滚代码：还原 `ops/release/release_sql_contract_gate.py`、`backend/src/main/java/com/intruoyi/maintenance/runtime/RuntimeControlOperationStore.java`、新增测试和对应文档。
- 回滚影响：只影响本地发布前置门禁和运行控制台 operation 列表读取；未产生远端变更。

## Blockers

实现、测试和经验沉淀无阻塞。收尾限制如下：

- 当前维护仓在任务开始前已有多份长期文档和发布任务记录脏改动；本任务也更新了其中部分文档，因此未擅自整文件提交，避免混入非本任务改动。
- 本任务外部 pytest state 目录 `D:\ProjectPackage\Int\IntRuoyiWorktrees\release-preflight-speedup-state` 的递归清理被工具安全策略拦截；该目录只含可再生测试临时文件，保留待后续安全清理。
