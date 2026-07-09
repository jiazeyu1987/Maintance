from pathlib import Path
from datetime import datetime
maint = Path(r"D:\ProjectPackage\Int\IntRuoyiMaintance")
task = maint / "doc" / "tasks" / "20260709-codeonly-three-env-head-release"
lesson = maint / "docs" / "release-build-preflight-lessons.md"
index = maint / "docs" / "experience-index.md"
exec_log = task / "execution-log.md"
request_log = maint / "docs" / "request-command-log.md"
lesson_text = """

## 2026-07-09 build-release 迁移元数据必须先过全量策略门禁

- 适用场景：执行 IntRuoyi code-only / no-data `build-release` 前，尤其是 HEAD 中包含 `sql/mysql/*.sql` 迁移文件时。
- 强制门禁：先运行 `script/release/run-release-migration-policy-gate.py --sql-root <backend>/sql/mysql --json`，并保存完整 JSON 证据；不得只抽查单文件。
- 元数据约束：`type` 只能使用脚本允许枚举 `schema`、`data`、`menu`、`config`、`permission`、`seed`；不得写 `schema-data` 等组合值。
- 依赖约束：`dependsOn` 必须填写真实存在的 migrationId，且依赖迁移的 `allowedEnvironments` 必须覆盖子迁移环境。
- 失败处理：若 build-release 报 `Invalid type in release migration metadata` 或 `missing release-migration metadata`，先冻结 operation 日志与策略门禁 JSON，再修复 SQL 首行元数据并补 `script/tests` 覆盖后重新生成新的 releaseTag。
"""
index_line = "- 2026-07-09：build-release 前必须执行全量迁移元数据策略门禁，`type` 只允许 schema/data/menu/config/permission/seed，修复 SQL 元数据需同步补 `script/tests` 覆盖；详见 `docs/release-build-preflight-lessons.md#2026-07-09-build-release-迁移元数据必须先过全量策略门禁`。\n"
for path in [lesson, index, exec_log, request_log]:
    path.parent.mkdir(parents=True, exist_ok=True)
if "## 2026-07-09 build-release 迁移元数据必须先过全量策略门禁" not in lesson.read_text(encoding="utf-8"):
    lesson.write_text(lesson.read_text(encoding="utf-8") + lesson_text, encoding="utf-8")
idx = index.read_text(encoding="utf-8")
if index_line.strip() not in idx:
    index.write_text(idx.rstrip() + "\n" + index_line, encoding="utf-8")
entry = """

### 2026-07-09 迁移元数据门禁修复

- RED: build-release-v4 -> FAIL，`20260708_mes_balloon_process_device_capacity.sql` 使用非法 `type=schema-data`。
- RED: migration-policy-full -> FAIL，`20260708_mes_batch_record_version_phase_one.sql` 缺少 `release-migration` 元数据。
- GREEN: migration-policy-full-after-metadata-fixes-final -> PASS，证据 `evidence/migration-policy-full-after-metadata-fixes-final.json`。
- GREEN: python -X utf8 -m pytest script/tests/test_release_migration_metadata_sql_20260708.py -> PASS，证据 `evidence/backend-release-migration-20260708-pytest.out.log`。
- 经验沉淀：已更新 `docs/release-build-preflight-lessons.md` 与 `docs/experience-index.md`，后续 build-release 前必须先过全量迁移元数据策略门禁。
"""
log_text = exec_log.read_text(encoding="utf-8")
if "### 2026-07-09 迁移元数据门禁修复" not in log_text:
    exec_log.write_text(log_text.rstrip() + entry, encoding="utf-8")
req_entry = """

### 2026-07-09 IntRuoyi 三环境 code-only 发布 - 迁移元数据修复

- command: `python -X utf8 -m pytest script/tests/test_release_migration_metadata_sql_20260708.py`
- result: PASS，补充 20260708 两条 SQL 的 release-migration 元数据测试覆盖。
- command: `script/release/run-release-migration-policy-gate.py --sql-root <backend>/sql/mysql --json`
- result: PASS，见任务 evidence 中 full policy gate JSON。
"""
req_text = request_log.read_text(encoding="utf-8") if request_log.exists() else ""
if "### 2026-07-09 IntRuoyi 三环境 code-only 发布 - 迁移元数据修复" not in req_text:
    request_log.write_text(req_text.rstrip() + req_entry, encoding="utf-8")