# Execution Log

## BDD

- BDD: 主系统与发票助手测试服联合发布 -> Given 已提交的主系统目标提交和发票助手发布目录，When 执行测试服发布并完成运行态校验，Then 测试服主系统健康、前端可访问、发票助手 `18733` 可访问且发布证据完整。

## Log

- 2026-09-03: 用户要求“再次将主系统和发票打印助手一起发布到测试服务器”。
- 2026-09-03: 创建本次任务目录与基础任务文档。
- 2026-09-03: GREEN: experience-preflight -> PASS。已读取 CI/CD 发布契约、项目经验索引、测试服发布门禁、构建发布门禁、PowerShell/SSH 门禁、服务器访问、登录访问、发布备份恢复和 worktree 规则；本次仅允许测试服 `172.30.30.58`，禁止 mark/prod/backup 和手工改库/ledger/lock。
- 2026-09-03: Previous task guard -> 上一项 `20260902-release-preflight-speedup` 已验证但因混合脏文档不能安全独立提交；本次发布不纳入该未提交优化，只从已提交 HEAD 创建 clean release worktree。
- 2026-09-03: Frozen input plan -> maintenance HEAD `024c643f48d251f3d8991ea9c12bfd0a2b6013bd`，app HEAD `65980ea01751c09146e2f0996a65689fc834ee44`，assistant HEAD `f077f4965b184a1b5c282bd1a3d8074f8e7e1510`；主工作区 dirty/untracked 内容均不得进入发布包。
- 2026-09-03T08:13:00+08:00: interrupted release audit -> `release-20260903-main-invoice-assistant-test-r260903a-r1` build-release operation failed at Smart Release report-only missing baseline manifest; `release-20260903-main-invoice-assistant-test-r260903a-r2` was interrupted while running `pnpm build:test` and has no manifest/tar/docker-compose output. Both tags are invalid and will not be published.
- 2026-09-03T08:28:24+08:00: Created fresh release worktrees for the retry: maintenance `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260903b\m` at `024c643f48d251f3d8991ea9c12bfd0a2b6013bd`; app `D:\IntRuoyiWorktree\r260903b\a` at `65980ea01751c09146e2f0996a65689fc834ee44`; assistant `D:\ProjectPackage\Int\IntRuoyiWorktrees\invoice-assistant-r260903b` at `f077f4965b184a1b5c282bd1a3d8074f8e7e1510`.
- 2026-09-03T08:30:00+08:00: GREEN: frontend-dependency-preflight -> PASS. `prepare-frontend-dependencies.ps1` prepared `cross-env.cmd`, `vite.cmd`, and `vue-tsc.cmd` for `D:\IntRuoyiWorktree\r260903b\a\IntRuoyiFronted`.
- 2026-09-03T08:30:00+08:00: GREEN: migration-policy-gate -> PASS. `run-release-migration-policy-gate.py` passed for 561 migrations, output `doc/tasks/20260903-main-invoice-assistant-test-release/artifacts/r260903b-migration-policy-gate.json`.
- 2026-09-03T08:30:00+08:00: GREEN: assistant-static-contracts -> PASS. `node --check server.js`, fixed-port, container-deploy, auth, WebAPI access and WebAPI query regression static checks passed in the assistant release worktree.
- 2026-09-03T08:30:00+08:00: RED: invoice-voucher-print-bridge-static -> FAIL, expected reason: command was first invoked from the assistant cwd so the static test inspected the wrong project root.
- 2026-09-03T08:30:00+08:00: GREEN: invoice-voucher-print-bridge-static -> PASS. Reran `node script/tests/invoice-voucher-print-kingdee-config-bridge-static.test.mjs` from `D:\IntRuoyiWorktree\r260903b\a\IntRuoyiBackend`.
- 2026-09-03T08:30:48+08:00: GREEN: runtime-control-build -> PASS. `scripts/build.ps1` built the maintenance frontend, ran 26 backend tests, and produced `backend\target\runtime-control-maintenance-2026.06-SNAPSHOT.jar`.
- 2026-09-03T08:31:00+08:00: GREEN: maintenance-preflight-tests -> PASS. `python -X utf8 -m pytest scripts\tests\test_release_sql_preflight_gate.py scripts\tests\test_publish_dcc_codex_runtime_contract.py -q` passed with 59 tests.
- 2026-09-03T08:32:00+08:00: Started runtime-control from the `r260903b` maintenance worktree on local port `48181`, PID `7848`; `/actuator/health` returned `UP`.
- 2026-09-03T08:34:16+08:00: Submitted build-release for `release-20260903-main-invoice-assistant-test-r260903b-r1`; operation `op-2026-09-03T003416026425200Z-a77fef3a-6a7c-4e45-8b6e-9df3f3ca67c3`.
- 2026-09-03T08:48:00+08:00: GREEN: build-release -> PASS. Operation `op-2026-09-03T003416026425200Z-a77fef3a-6a7c-4e45-8b6e-9df3f3ca67c3` completed successfully; package `release-20260903-main-invoice-assistant-test-r260903b-r1` was built and uploaded to NAS path `Backup/ReleasePackage/release-20260903-main-invoice-assistant-test-r260903b-r1`.
- 2026-09-03T08:49:40+08:00: Submitted publish-test for `release-20260903-main-invoice-assistant-test-r260903b-r1`; operation `op-2026-09-03T004932354398500Z-004c967b-9fcd-47a5-b126-69aac9485585`.
- 2026-09-03T08:57:00+08:00: GREEN: publish-test -> PASS. Operation `op-2026-09-03T004932354398500Z-004c967b-9fcd-47a5-b126-69aac9485585` completed successfully; test server reported backend health HTTP 200, frontend HTTP 200, PDF worker HTTP 200, release lock released as `APPLIED`, and no mark/prod/backup action was executed.
- 2026-09-03T09:00:00+08:00: GREEN: assistant-artifact -> PASS. Created source artifact `invoice-assistant-f077f49-r260903b-source.tar`, bytes `358400`, SHA256 `E67850143F9944BF2895A8D445002DDC5BF87745407D3DAD57C067DF530B7AA6`; remote SHA256 matched before extraction and build.
- 2026-09-03T09:01:00+08:00: INFO: assistant-remote-prestate -> systemd unit still referenced old image tag while a manually running same-name container used `erp-invoice-voucher-print-assistant:webapi-r260902i`; systemd was in auto-restart conflict. Deployment stopped only `erp-invoice-voucher-print-assistant.service`, removed only its same-name old container, installed the new unit tag, and restarted the service.
- 2026-09-03T09:01:57+08:00: GREEN: assistant-deploy -> PASS. Test server built and ran `erp-invoice-voucher-print-assistant:f077f49-r260903b`; systemd active, container running, `0.0.0.0:18733` listening, direct root HTTP returned `403`, and container environment contains `KINGDEE_RUNTIME_DIR` without `KINGDEE_ENV_PATH`.
- 2026-09-03T09:04:00+08:00: GREEN: remote-runtime-verification -> PASS. Test server `.env IMAGE_TAG=release-20260903-main-invoice-assistant-test-r260903b-r1`; backend/frontend image tags match the releaseTag; backend health `UP`; frontend HTTP `200`; `release-info.json` contains the releaseTag; assistant image tag matches `f077f49-r260903b`; release lock `APPLIED`; migration ledger has `APPLIED:1`, `SKIPPED_ALREADY_APPLIED:501`, and `FAILED/RUNNING=0`.
- 2026-09-03T09:06:21+08:00: BLOCKER: invoice-assistant-entry-e2e -> missing `INVOICE_ASSISTANT_E2E_PASSWORD` in the current process. `verify-invoice-assistant-entry.e2e.cjs` wrote `artifacts/invoice-assistant-entry-e2e/result.json` with status `BLOCKED`; no login, business write, password, cookie, token, or API-only substitute was used.
- 2026-09-03T09:08:00+08:00: GREEN: project-experience-consolidation -> PASS. Added assistant systemd/container tag drift gate to `docs/test-release-preflight.md` and routed related keywords in `docs/experience-index.md`.
- 2026-09-03T09:10:00+08:00: GREEN: runtime-control-process-stop -> PASS. Stopped task-owned local runtime-control PID `7848`; follow-up check confirmed port `48181` is not listening.
- 2026-09-03T09:11:00+08:00: GREEN: task-doc-diff-check -> PASS. `git diff --check` passed for task-owned docs and evidence; Git only emitted LF/CRLF warnings for existing Markdown files.
- 2026-09-03: 用户明确调整本次验收范围为“测试发布成功即可，不用进行 E2E 测试”。此前因缺少 `INVOICE_ASSISTANT_E2E_PASSWORD` 阻塞的登录后菜单 iframe 验收不再是本任务完成条件；未执行登录、业务写入或 API-only 替代。
- 2026-09-03: GREEN: release-acceptance-scope -> PASS. 主系统 `build-release -> publish-test`、manifest、测试服镜像 tag、health、frontend HTTP、release-info、release lock/migration 与助手 `18733` 运行态均已通过，任务转入 closeout。
- 2026-09-03: GREEN: task-closeout-preview/apply -> PASS. 保留 `task.md`、`execution-log.md`、`verification-report.md`；已删除任务目录中的临时构建日志、artifact、pytest 副本和未执行 E2E 脚本，无 blocked/warnings。
- 2026-09-03: GREEN: release-worktree-cleanup -> PASS. 已删除本任务 `r260903a/r260903b` 的维护仓 worktree、主系统 worktree、助手 worktree、残留前端 `node_modules` 以及两轮 runtime-control state；其他任务 worktree 未触碰。
