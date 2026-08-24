# Execution Log

## BDD

BDD: 同一 r11 发布包晋级正式服 -> Given r11 已在测试服成功运行且 package/manifest 可核验 / When 先 mark-release-tested 再执行带 `PROD` 和 `RequireTested` 的 promote-prod / Then 正式服只切换到同一 r11，operation、运行态、release-info 和版本说明全部通过，否则流程停止。

## Preflight

GREEN: experience-preflight -> PASS；已读取正式发布、服务器访问、登录、worktree 限制、CI/CD、launch gate、独立验证和项目经验文档；正式环境操作授权来自用户当前请求，目标仅正式服务器 `172.30.30.57`，备用服务器不在本任务范围。

## Status

- 当前阶段：正式晋级前只读核验。
- 发布范围：同一 `release-20260823-intmain-training-r260823f-r11`；不重建、不换 tag、不执行 `promote-backup`。
- 后续所有命令、operation、问题和验证结果按阶段追加；凭据、token、私钥和完整环境密钥不写入日志。

## 失败与修复闭环

- 现象：第一次“标记测试通过”操作 `op-2026-08-24T155529974423600Z-c8c5aff4-838b-42f3-94dc-acc1e0868536` 失败，日志报 `Release migration metadata missing: E:\IntRuoyi\IntRuoyiBackend\sql\mysql\20260822_mes_active_order_pick_list_binding.sql`。
- 阶段：`mark-tested` 本地门禁。
- 影响：未写入测试通过标记，正式服晋级未执行，符合 fail-fast。
- 原因判断：发布脚本在所有模式无条件执行 `Get-ReleaseDatabaseSqlScripts`，导致仅消费 NAS 已构建包的 `mark-tested` 仍读取当前开发仓库 SQL；当前仓库该文件缺少 metadata，但 r11 包自身已有构建时 manifest/required-sql。
- 处理动作：先补回归测试，随后将 SQL 源仓库扫描限制在需要构建/部署 SQL 的模式，`mark-tested` 改为直接使用包内 manifest，不重建、不修改 r11 包。
- 结果：待 RED/GREEN 与同一 r11 重试验证。
- 可前置检查：是；执行 `mark-tested` 前应验证脚本不会读取未锁定的开发仓库 SQL。
- 可自动化：是；增加脚本契约测试并在 preview 阶段检查 SQL 源路径。
- 下次避免：发布包晋级动作只消费包内 manifest/required-sql，禁止依赖发布开始后变化的开发工作区。

BDD: 包消费模式不读取开发仓库 SQL -> Given r11 包已完成构建且 mark-tested 只需 NAS 包内证据 / When 执行维护脚本的 `mark-tested` / Then 不调用当前开发仓库的 `Get-ReleaseDatabaseSqlScripts`，直接校验包内 manifest。
RED: `python -X utf8 -m pytest scripts/tests/test_release_sql_preflight_gate.py -k package_only_modes -q` -> FAIL, 原脚本无包消费模式 guard。
GREEN: `python -X utf8 -m pytest scripts/tests/test_release_sql_preflight_gate.py -k 'package_only_modes or publish_script_runs_sql_preflight_before_backend_build' -q` -> PASS（2 passed）。
GREEN: `python -X utf8 -m pytest scripts/tests/test_release_sql_preflight_gate.py --basetemp=runtime/pytest-r11-preflight -q` -> PASS（32 passed）。
问题记录：完整测试首次使用系统临时目录时因 `C:\Users\BJB110\AppData\Local\Temp\pytest-of-BJB110` 权限不足产生 11 个 setup error；改用任务目录 basetemp 后 32/32 通过。该问题可前置检查并可自动化固定 basetemp。

## 正式晋级结果

- `GREEN: mark-tested -> PASS`：`op-2026-08-24T161343310401700Z-81371129-617a-45cf-a42c-c720d8c5b0bd`，同一 r11 标记成功；`latestTestedReleaseTag` 与 `tested=true` 均为 r11。
- `GREEN: prod-preview -> PASS`：生成 `release-20260823-intmain-training-r260823f-r11-preflight-release-dry-run.json`，目标 `prod/172.30.30.57`，manifest、包声明、哈希、禁用目标扫描、目标配置、迁移计划报告均通过，未执行远程写入。
- `BLOCKER: promote-prod -> FAILED`：`op-2026-08-24T162302044432900Z-4eca53c5-366b-4699-b2a7-5a9876992d65`。正式服已完成 r11 `.env` 写入、镜像加载、MySQL/Redis 健康检查和迁移包上传，但 `release_preflight_plan.py` 在正式库上生成 `status=blocked`：`code-only` 包包含未满足依赖链 `20260803_dcc_product_onboarding_flow -> 20260607_product_master_data`、`20260816_mdm_enterprise_company_scope` 及其下游注册证书迁移，脚本按门禁停止，未启动 r11 backend/frontend，也未把 prod 标为成功。
- 恢复动作：将正式服 `/opt/intruoyi/runtime/.env` 恢复为发布前 `.env.before-showroom-codex-20260716075857`（旧 tag），确认 backend/frontend 实际镜像仍为旧运行版本、backend health=UP、frontend HTTP=200；prod 锁已由脚本置为 FAILED/释放。未执行备份服动作。
- 影响：本次不能判定正式服发布成功；必须先解决正式库迁移依赖/发布 scope 契约，再以同一 r11 重新走 preview 与 promote-prod。禁止手工修改迁移状态或绕过 `BLOCKED_SCOPE_DEPENDENCY`。
- 问题记录：直接对测试发布后的本地缓存目录运行 manifest validator 时发现部署阶段生成的 `.env`、`preflight-plan.json`、`preflight-target-state-test.json`、`ops-runtime` 等未声明文件，报告 `PACKAGE_UNDECLARED_FILE`。阶段：构建包复核；影响：直接复核会失败，但不代表 NAS 原始 manifest 无效；原因判断：发布脚本在同一缓存目录写入部署运行时证据，包缓存被部署污染。处理：未删除或篡改 r11，改用正式 prod dry-run 的 sanitized package workspace；结果：prod preview PASS。可前置检查：是；构建/发布后应区分 immutable package 与 deployment workspace。可自动化：是；发布脚本应输出独立 sanitized 校验目录。下次避免：禁止把部署生成文件写回 immutable package，或在 validator 前先生成受控清单。
