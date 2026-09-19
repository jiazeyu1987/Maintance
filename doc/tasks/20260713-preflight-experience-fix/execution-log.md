# 20260713 前置经验问题修复执行日志

## Initial Request

- REQUEST: 用户要求修复前置经验审查发现的问题。
- SCOPE: 修改长期前置经验和规则入口；不执行发布、不操作服务器、不触碰无关脏改。

## Milestone 1 - Task Bootstrap

- GREEN: task-directory -> PASS，创建 `doc/tasks/20260713-preflight-experience-fix/`。
- GREEN: task-doc-bootstrap -> PASS，写入任务目标、里程碑、预期验证、设计约束、BDD 和经验门禁。

## Milestone 2 - Documentation Fixes

- GREEN: fix-migration-gate-command -> PASS，`docs/test-release-preflight.md` 推荐命令改为先 `--help`，再用 `--output <task-dir>\migration-policy-gate.json`；`docs/release-build-preflight-lessons.md` 不再把历史 `--json` 作为冻结 worktree 主推荐命令。
- GREEN: fix-bootstrap-order-conflict -> PASS，维护仓 `AGENTS.md`、`docs/experience-index.md`、`docs/powershell-preflight-lessons.md`，以及主项目 `AGENTS.md`、`docs/experience-index.md`、`docs/powershell-memory.md` 均明确 PowerShell 只读 UTF-8 bootstrap 是 task-doc-first 的唯一前置例外，且 bootstrap 后必须立即创建或更新任务文档并摘取经验门禁。
- GREEN: fix-test-release-evidence -> PASS，`docs/test-release-preflight.md` 的可索引门禁摘要已补齐 `Evidence` 字段。
- GREEN: fix-index-route-drift -> PASS，`docs/experience-index.md` 将漂移或脆弱锚点改为文件 + 标题路由；保留仍可稳定解析的锚点。
- GREEN: fix-test-only-scope-wording -> PASS，`docs/release-build-preflight-lessons.md` 明确完整三环境发布与仅测试服发布的范围边界，避免仅测试服任务误执行 `mark-tested`、`promote-prod` 或 `promote-backup`。
- GREEN: fix-format-artifacts -> PASS，移除发布经验中的孤立 `'`，并将 `\build-release` 规范为 `build-release`。

## Milestone 3 - Verification

- GREEN: migration-gate-help -> PASS，当前后端脚本 `run-release-migration-policy-gate.py --help` 只列出 `--output`，未列出 `--json`。
- GREEN: stale-json-primary-command-scan -> PASS，维护仓测试服/构建发布前置文档中仅保留“历史 `--json` 不得直接用于冻结 worktree”的禁止语义，不再把 `--json` 作为主推荐执行命令。
- GREEN: index-anchor-check -> PASS，`docs/experience-index.md` 中 29 个带 `#` 的剩余锚点 missing=0、broken=0。
- GREEN: bootstrap-exception-route -> PASS，`rg` 可在维护仓和主项目规则入口定位 `task-doc-first 的唯一前置例外`。
- GREEN: diff-check-maintenance -> PASS，维护仓本次修改文件 `git diff --check` 无空白错误；仅有 Git 行尾提示。
- GREEN: diff-check-main-project -> PASS，主项目本次修改文件 `git diff --check` 无空白错误；仅有 Git 行尾提示。
- GREEN: utf8-control-scan -> PASS，本次涉及的维护仓与主项目文件均 UTF-8 可读、NUL=0、非法控制字符=0。
- GREEN: secret-scan -> PASS，敏感词扫描命中均为 `<redacted>`、`<secret>` 示例或历史脱敏记录，未发现本次新增明文密码、token、私钥或连接串。
