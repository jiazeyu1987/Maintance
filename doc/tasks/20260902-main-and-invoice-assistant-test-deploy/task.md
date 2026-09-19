# 20260902 主程序与发票助手测试服发布任务

## Task Goal

将 IntRuoyi 主程序当前已提交发布输入与已独立部署的发票凭证打印助手发布/对齐至测试服务器 `172.30.30.58`，并验证主程序前后端、版本发布证据及助手 `18733` 服务均处于可用且相互兼容的真实运行态。

## Milestones

1. 启动门禁：读取发布、服务器、worktree、PowerShell 经验与当前运行态，明确本次发布边界。
2. 发布输入冻结：确认主程序前后端与助手目标提交均已提交，创建本次专用临时发布 worktree。
3. 主程序测试服发布：按单一 releaseTag 执行 `build-release -> publish-test`，不执行正式服、备份服或 `mark-tested`。
4. 助手对齐验证：确认助手 `erp-invoice-voucher-print-assistant:8f63829` 和主程序新版本共同运行，未授权拦截与入口授权链保持正确。
5. 真实验收与收尾：完成主程序真实前端路径、API 最终校验、镜像/manifest/releaseTag 证据与任务清理。

## Expected Verification

- Given 主程序和发票助手均有冻结的已提交发布输入，When 发布主程序至测试服并保留助手独立服务，Then 测试服主程序前端 HTTP 200、后端 health=UP、运行镜像 tag/远端 `.env IMAGE_TAG`/manifest/releaseTag 一致，助手 `18733` 容器运行且未授权直连被拒绝。
- Given 主程序入口使用助手 ticket 授权，When 测试租户真实用户通过前端进入发票打印助手，Then 浏览器实际载入助手业务页面而非被授权拦截。
- 只发布测试服；不操作正式服、备份服、测试库业务数据或主程序未提交内容；不记录明文凭据。

## 经验门禁

- Trigger: 测试服主程序发布、独立发票助手联调、PowerShell/SSH、真实 Playwright E2E、临时发布 worktree。
- Preflight check: 创建后按经验索引读取测试服发布、构建、PowerShell、服务器、备份恢复、登录和 worktree 规则；确认前后端发布输入都来自已提交内容，发布前记录 `GREEN: experience-preflight -> PASS`，并在发布 worktree 执行构建。
- Blocker: 主程序任一发布输入未提交或无法冻结、发布脚本契约/目标主机不明确、worktree 不能创建、测试服运行态与本次发布争用、缺少测试租户入口或发布成功证据任一项缺失。
- Verification: `build-release` 与 `publish-test` 记录同一 releaseTag 成功；检查 operation、manifest、远端 `.env IMAGE_TAG`、backend/frontend 镜像 tag、backend health=UP、frontend HTTP 200；Playwright 从主程序真实入口完成 ticket 授权链；助手服务/容器和 `18733` 响应符合授权预期。
- Forbidden action: 禁止在主工作区构建/发布，禁止混入未提交或未跟踪内容，禁止执行 `mark-tested`/正式服/备份服发布，禁止用 API 或 SQL 绕过主程序前端入口，禁止杀死未知服务或记录凭据。
- Evidence: 本任务 `execution-log.md`、`verification-report.md`、发布操作记录、manifest、远端运行态和 Playwright 证据。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否
- 是否从根因和长期维护角度解决：是。本次按既有正式发布闭环与独立助手部署契约执行，不使用临时覆盖或端口绕过。
- 是否存在临时补丁或绕过：否

## Current Status

in_progress

## Milestone Status

1. 启动门禁：completed。已读取 CI/CD 发布契约、测试服访问、发布/备份恢复、PowerShell 编码与 SSH、登录/助手 ticket、worktree、测试服发布及构建发布经验；后续远端操作限定为 `172.30.30.58`，主程序仅走单一 `build-release -> publish-test`，助手固定 `18733`。
2. 发布输入冻结：completed。当前有效发布输入为 r260902c：维护、主程序、助手 release worktree 分别为 `D:\ProjectPackage\Int\IntRuoyiWorktrees\r260902c\m`、`D:\IntRuoyiWorktree\r260902c\a`、`D:\ProjectPackage\Int\IntRuoyiWorktrees\invoice-assistant-r260902c`，均 detached、clean，目标提交依次为 `024c643f48d251f3d8991ea9c12bfd0a2b6013bd`、`90deb1e72c224dc1fc010178db53f0ba3dc41ea3`、`8f6382941de87237eda49bb3a270c2064a821b95`。主程序主工作区未提交/未跟踪文件不在本次发布输入内。
3. 主程序测试服发布：completed。`release-20260902-main-invoice-assistant-test-r260902c-r1` 的 build operation 与 publish-test operation 均为 SUCCESS；测试服 `.env IMAGE_TAG`、backend/frontend 实际镜像、backend health、frontend HTTP、release-info、release-status、release lock 和目标 migration ledger 均通过。
4. 助手对齐验证：in_progress。续跑只读复核发现助手容器已被后续工作更新为 `erp-invoice-voucher-print-assistant:webapi-r260902i` 且 running，但 systemd 单元仍在用旧 tag 重启并处于 `activating`；正在用助手当前已提交 HEAD `f077f4965b184a1b5c282bd1a3d8074f8e7e1510` 的 clean release worktree 重新部署并恢复 systemd active。
5. 真实验收与收尾：blocked。真实入口 E2E 脚本已准备并执行前置检查，但当前进程缺少 `INVOICE_ASSISTANT_E2E_PASSWORD`；按登录门禁不能猜密码、不能改账号、不能 API-only 冒充页面验收。

### Recovery State

- 已在用户授权范围内原子恢复测试服 `/opt/intruoyi/runtime/.env` 的唯一 `IMAGE_TAG`：`release-20260902-main-invoice-assistant-test-r260902a-r1` -> `release-20260901-main-invoice-assistant-test-r260901a-r1`。
- 重启后独立只读复核：`.env`、backend/frontend 实际镜像均为 `release-20260901-main-invoice-assistant-test-r260901a-r1`；两容器 running、backend health=UP、frontend HTTP=200、release lock RUNNING=0。
- 本机重启已停止本任务 runtime-control；三份 r260902b 发布 worktree 仍完整、detached、clean。本机恢复控制台后需重新执行 publish-test preview 与当前目标 tag ledger 检查，再提交发布。

### Previous Release Blocker (Resolved)

- 通知模板 SQL 已修复并在新 build releaseTag 验证；当前无 SQL/manifest/plan/ledger blocker。
- 远端 `.env IMAGE_TAG=release-20260902-main-invoice-assistant-test-r260902b-r1` 与 backend/frontend 实际镜像漂移的问题，已在用户授权后原子恢复并完成 r260902c 发布。
- 当前剩余阻塞仅为真实入口 E2E 缺少当前进程环境变量 `INVOICE_ASSISTANT_E2E_PASSWORD`。

### Post-Resume Read-Only Evidence

- 本机 `127.0.0.1:48181` 未监听，r260902c runtime-control 未运行。
- r260902c 发布 worktree 仍 clean：维护 `024c643f48d251f3d8991ea9c12bfd0a2b6013bd`、主程序 `90deb1e72c224dc1fc010178db53f0ba3dc41ea3`、助手 `8f6382941de87237eda49bb3a270c2064a821b95`。
- r260902c 发布包仍存在，manifest releaseTag=`release-20260902-main-invoice-assistant-test-r260902c-r1`，backend/frontend sourceRepos 均为 `90deb1e72c224dc1fc010178db53f0ba3dc41ea3` 且 dirty=false。
- 远端只读复核仍确认 `.env` 与实际运行镜像漂移；目标 r260902c 的 migration FAILED/RUNNING=0 且 target release lock RUNNING=0。
- 本地 r260902c `publish-test` preview 已复核通过，结构化目标为测试服 `172.30.30.58` 和 `/opt/intruoyi/runtime`，无 mark/prod/backup 动作；preview 后 runtime-control 已停止。
- 助手 `8f6382941de87237eda49bb3a270c2064a821b95` 已完成本地静态验证并生成 task-owned artifact `artifacts/invoice-voucher-print-assistant-8f63829-r260902c.tar`，SHA256=`EF2DDF7344F4FB64385462BE3613E883853597CA11F84F7023B1D860DA5390AF`，等待主程序 publish-test 成功后独立部署。
- 已准备并 AST 验证 `invoke-remote-assistant-deploy.ps1`；该 helper 尚未执行，后续仅在主程序发布成功、经验门禁再次转绿后，用于独立更新测试服助手服务。
- 已准备并 AST 验证 `invoke-authorized-image-tag-restore.ps1`；该 helper 尚未执行，必须等用户明确授权本次 r260902b 失败漂移的单行恢复后才可调用。
- 已准备并语法验证 `verify-invoice-assistant-entry.e2e.cjs`；`node --check` 通过，`npx` 与 r260902c 前端 worktree 的 Playwright package 均可用，硬编码密码/token 扫描无命中。该脚本尚未执行，必须等主程序 r260902c publish-test、助手独立部署和登录密码进程级注入后，才能用于真实菜单入口验收。
- 电脑重启后再次只读探针确认：远端 `.env IMAGE_TAG` 仍为失败 `release-20260902-main-invoice-assistant-test-r260902b-r1`，backend/frontend 实际镜像仍为稳定 `release-20260901-main-invoice-assistant-test-r260901a-r1`；backend/frontend/assistant running，backend health=UP、frontend HTTP=200、assistant HTTP=403，global lock RUNNING=0，目标 r260902c migration FAILED/RUNNING=0、target lock RUNNING=0。
- 自动续跑再次只读探针确认：prepublish probe SHA256 与 target ledger SHA256 均未变化，远端仍为同一 `.env` 漂移阻塞；没有外部恢复或新的 publish-test 操作发生。
- 阻塞审计复核：第三轮只读探针仍为相同 SHA256 和相同运行态，本机 `127.0.0.1:48181` 未监听；当前已无无需授权即可推进的发布动作。任务保持 `blocked`，等待用户明确授权恢复测试服 `.env` 单行 IMAGE_TAG。
- 授权恢复已完成：测试服 `/opt/intruoyi/runtime/.env` 的唯一 `IMAGE_TAG` 已从 `release-20260902-main-invoice-assistant-test-r260902b-r1` 原子恢复到 `release-20260901-main-invoice-assistant-test-r260901a-r1`；独立只读探针确认 backend/frontend 实际镜像同为该 tag 且 running，backend health=UP、frontend HTTP=200、assistant HTTP=403，目标 r260902c ledger/lock 仍为 0。
- 主程序 r260902c 测试服发布完成：publish operation=`op-2026-09-02T030941863891200Z-fd71a596-4dcc-4fd4-904a-20074c27d315` SUCCESS；远端 `.env IMAGE_TAG`、backend/frontend 实际镜像均为 `release-20260902-main-invoice-assistant-test-r260902c-r1`，backend/frontend running，backend health=UP，frontend HTTP=200；`/release-info.json` 与 runtime-control release-status 均显示 r260902c、sourceRepos `90deb1e72c224dc1fc010178db53f0ba3dc41ea3` 且 dirty=false；release lock=APPLIED，target migration FAILED/RUNNING=0。
- 发票助手独立部署完成：远端构建并运行 `erp-invoice-voucher-print-assistant:8f63829`，systemd active、container running、`18733` 直连 HTTP 403；部署后主程序 `.env`、backend/frontend image tag、backend health 与 frontend HTTP 仍保持 r260902c 通过。
- E2E 阻塞：当前进程没有 `INVOICE_ASSISTANT_E2E_PASSWORD`；脚本已产出 `artifacts/invoice-assistant-entry-e2e/result.json`，status=`BLOCKED`，impact=`无法执行测试服真实登录和发票助手 iframe 验收`。

### Prior Authorization Received

- 2026-09-02 用户曾明确回复“授权”。该授权已用于上一次受限恢复：将测试服 `/opt/intruoyi/runtime/.env` 的唯一 `IMAGE_TAG` 从首轮失败 tag 原子恢复为当时 backend/frontend 实际运行 tag。该授权不覆盖当前 r260902b 失败后产生的新 `.env` 漂移；本次仍需新的明确授权后才能恢复单行 IMAGE_TAG 并继续 publish-test。

### Resolved Authorization

- 用户已明确回复：`授权恢复测试服 IMAGE_TAG 单行并继续发布`。
- 授权范围已执行完成：仅将测试服 `/opt/intruoyi/runtime/.env` 的唯一 `IMAGE_TAG` 从 `release-20260902-main-invoice-assistant-test-r260902b-r1` 原子恢复到当前实际运行 tag `release-20260901-main-invoice-assistant-test-r260901a-r1`；未重启服务，未修改 migration ledger/release lock/schema/业务数据，未操作正式服或备份服。

### Current Authorization

- 2026-09-02 用户明确回复：`授权恢复测试服 IMAGE_TAG 单行并继续发布`。
- 本次授权范围固定为：仅将测试服 `/opt/intruoyi/runtime/.env` 的唯一 `IMAGE_TAG` 从 `release-20260902-main-invoice-assistant-test-r260902b-r1` 原子恢复到当前实际运行 tag `release-20260901-main-invoice-assistant-test-r260901a-r1`；恢复后继续 r260902c 测试服 `publish-test`、助手独立部署和真实入口验收。恢复步骤仍禁止重启服务、修改 migration ledger/release lock/schema/业务数据、操作正式服或备份服。

### Required E2E Input

- 等待以当前进程环境变量注入 `INVOICE_ASSISTANT_E2E_PASSWORD` 后，继续执行 `verify-invoice-assistant-entry.e2e.cjs`。不得把密码写入脚本、任务文档、截图或命令日志。

### 2026-09-02 23:53 Re-Release Request

- 用户再次要求将主系统和发票打印助手一起发布到测试服务器。
- 本轮计划使用新的 release attempt `r260902d`：维护仓已提交 HEAD `024c643f48d251f3d8991ea9c12bfd0a2b6013bd`、主程序已提交 HEAD `65980ea01751c09146e2f0996a65689fc834ee44`、助手已提交 HEAD `f077f4965b184a1b5c282bd1a3d8074f8e7e1510`。
- 主程序与助手主工作区存在未提交改动；按发布门禁，本轮发布只使用 clean release worktree 中的已提交 HEAD，不纳入未提交或未跟踪文件。
- 目标仍限定为测试服务器 `172.30.30.58`：主程序执行新 releaseTag 的 `build-release -> publish-test`；助手独立部署到 `18733`；禁止 `mark-tested`、正式服、备份服、手工 ledger/schema/业务数据修改或记录凭据。
