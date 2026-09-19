# 验证报告

## 当前结论

`IN_PROGRESS`。用户已再次要求联合发布，本轮将使用新的 `r260902d` clean release worktree 冻结维护仓 `024c643f48d251f3d8991ea9c12bfd0a2b6013bd`、主程序 `65980ea01751c09146e2f0996a65689fc834ee44`、助手 `f077f4965b184a1b5c282bd1a3d8074f8e7e1510`，仅发布测试服务器 `172.30.30.58`。主程序和助手主工作区存在未提交改动，均不进入本轮发布输入。真实菜单入口 E2E 仍依赖当前进程注入 `INVOICE_ASSISTANT_E2E_PASSWORD`，不能猜密码、改账号或用 API-only 冒充页面验收。

## 已通过证据

- 发布源：维护、主程序、助手 clean r260902c release worktree 固定为 `024c643f48d251f3d8991ea9c12bfd0a2b6013bd`、`90deb1e72c224dc1fc010178db53f0ba3dc41ea3`、`8f6382941de87237eda49bb3a270c2064a821b95`。
- 本地门禁：维护仓 `84 passed`；通知模板静态 `3 passed`、隔离 MySQL 回归通过、migration policy、Spring constructor、助手回归、冻结前端依赖与关键二进制均通过；runtime-control Maven package `26 tests`、BUILD SUCCESS。
- 构建：build operation `op-2026-09-02T015148976367700Z-caecf947-ac1e-4255-9077-b3dd9b5c05c6` 为 `SUCCESS`；manifest releaseTag=`release-20260902-main-invoice-assistant-test-r260902c-r1`，两份 sourceRepo commit 均为 `90deb1e72c224dc1fc010178db53f0ba3dc41ea3`，`dirty=false`；官方 validator 通过；本地 backend/frontend images 已生成。
- target plan：`passed`，561 项，3 项本次可应用 migration，0 项 scope/dependency blocker；目标 r260902c migration FAILED/RUNNING=0、target release lock RUNNING=0。
- 发布预览：r260902c 本地 runtime-control health=UP，`publish-test` preview 的结构化目标为 `test`/`172.30.30.58`/`/opt/intruoyi/runtime`/同一 releaseTag，未包含 mark/prod/backup 动作；preview 后控制台已停止。
- 助手 artifact：助手 clean worktree HEAD=`8f6382941de87237eda49bb3a270c2064a821b95`，静态/脚本解析验证通过，artifact `invoice-voucher-print-assistant-8f63829-r260902c.tar` size=`348160` bytes、SHA256=`EF2DDF7344F4FB64385462BE3613E883853597CA11F84F7023B1D860DA5390AF`。
- 助手部署准备：当前测试服助手承载只读确认完成；任务内部署 helper `invoke-remote-assistant-deploy.ps1` 已通过 AST 解析但尚未执行。
- 恢复准备：任务内 `.env IMAGE_TAG` 单行恢复 helper `invoke-authorized-image-tag-restore.ps1` 已通过 AST 解析但尚未执行。
- E2E 准备：真实入口验收脚本 `verify-invoice-assistant-entry.e2e.cjs` 已通过 `node --check`；`npx`、Node/npm 和 r260902c 前端 Playwright package 可用；脚本硬编码密码/token 扫描无命中。脚本尚未运行，等待主程序 publish-test、助手独立部署和登录密码进程级注入。
- 发布前运行态：电脑重启后再次只读探针确认，远端 `.env IMAGE_TAG=release-20260902-main-invoice-assistant-test-r260902b-r1`，实际 backend/frontend 仍运行上轮主程序 tag `release-20260901-main-invoice-assistant-test-r260901a-r1`，助手 tag `ba55fb8`；backend/frontend/assistant running，backend health=UP、frontend=200、assistant direct=403、release lock RUNNING=0；目标 r260902c migration FAILED/RUNNING=0、target lock RUNNING=0。
- 自动续跑复核：prepublish probe SHA256=`3346a3e24d59d4b509ea4b626e1e267da64e814560358066b1ea4341deed4297`、target ledger SHA256=`7de98c285003fe121385982b2138a10e96adb2c6d180d9d1cd0538aa6999e3c1`，与上一次一致；外部状态未恢复，阻塞仍成立。
- 阻塞审计：第三轮复核仍为相同状态，本机 `127.0.0.1:48181` 未监听；在没有用户明确授权前，继续恢复 `.env`、提交 publish-test 或部署助手都属于未授权远端写入，故当前任务只能保持 `BLOCKED`。
- 授权恢复：用户明确授权后，测试服 `/opt/intruoyi/runtime/.env` 的唯一 `IMAGE_TAG` 已原子恢复为 `release-20260901-main-invoice-assistant-test-r260901a-r1`；恢复后独立只读 probe SHA256=`5d3bd64babae01d506aa1f4be83c9d64ff53fb1862953bb19c3c984bff6746de`，目标 ledger SHA256=`7de98c285003fe121385982b2138a10e96adb2c6d180d9d1cd0538aa6999e3c1`；backend/frontend/assistant running，backend health=UP，frontend HTTP=200，assistant HTTP=403，target r260902c migration/lock 仍为 0。
- 主程序发布：publish operation `op-2026-09-02T030941863891200Z-fd71a596-4dcc-4fd4-904a-20074c27d315` SUCCESS；远端 `.env IMAGE_TAG`、backend/frontend 实际镜像均为 `release-20260902-main-invoice-assistant-test-r260902c-r1`；backend/frontend running、backend health=UP、frontend HTTP=200；release-info 和 runtime-control release-status 均显示 r260902c，sourceRepos 均为 `90deb1e72c224dc1fc010178db53f0ba3dc41ea3` 且 dirty=false；release lock=APPLIED，target migration FAILED/RUNNING=0。
- 助手发布：artifact SHA256=`EF2DDF7344F4FB64385462BE3613E883853597CA11F84F7023B1D860DA5390AF` 远端校验一致；测试服助手 image=`erp-invoice-voucher-print-assistant:8f63829`、systemd active、container running、`18733` 直连 HTTP 403；部署后主程序 backend/frontend 仍为 r260902c 且健康。
- E2E 前置检查：`verify-invoice-assistant-entry.e2e.cjs` 产出 `status=BLOCKED`，原因是缺少 `INVOICE_ASSISTANT_E2E_PASSWORD`；未执行真实登录、未写业务数据、未记录凭据。

## 历史账本

- `20260625_dcc_fvm_matrix_retain_other_completion`：`FAILED`，releaseTag=`release-20260628-1438-head-full-v8`。
- `20260717_mes_balloon_excel_device_workstation_binding`：`FAILED`，releaseTag=`release-20260727-onlyoffice-test-r260727-1823`。
- `20260709_mes_rt000006_batch_record_mapping`：`FAILED`，releaseTag=`release-20260727-onlyoffice-test-r260727-1948`。

上述及本任务失败 releaseTag 的记录已只读保留，不对远端 ledger 做手工改写。主程序与助手测试服发布均已完成；剩余验收项为注入真实测试租户密码后运行主程序菜单入口 ticket 链 E2E，并在通过后执行任务收尾。
