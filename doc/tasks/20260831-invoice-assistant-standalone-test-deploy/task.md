# 20260831 发票打印助手独立测试服发布任务

## Task Goal

将 `E:\ProjectPackage\erp-invoice-voucher-print-assistant` 当前已提交内容独立发布到测试服务器 `172.30.30.58` 的 `18733` 端口；主程序端口已正常运行，本次不发布 IntRuoyi 主程序、不修改主程序菜单/权限/业务数据。

## Milestones

1. 启动门禁与任务文档：建立任务目录、记录 BDD/TDD 边界、摘取发布/服务器/PowerShell/助手部署经验门禁。
2. 发布源冻结：确认助手项目 Git 状态、目标提交、现有 Docker/启动契约和测试服运行方式。
3. 本地验证与打包：在发布源 worktree 或当前已提交源上运行静态/构建验证，生成可追踪 artifact。
4. 测试服独立部署：只更新发票打印助手服务和 `18733` 暴露，不重启或发布 IntRuoyi 主程序。
5. 真实运行态验证：验证远端容器/服务状态、`18733` HTTP 响应、未授权访问拦截、主程序既有端口仍可达。
6. 收尾：记录验证报告、更新 request-command log、按任务清理策略处理临时产物并标记完成。

## Expected Verification

- BDD: Given 主程序已运行且助手项目有可构建内容，When 单独发布助手到测试服 `18733`，Then `http://172.30.30.58:18733/` 可访问且主程序端口保持可达。
- BDD: Given 助手需要主程序 ticket 授权，When 直接访问未带有效 ticket 的助手页面，Then 助手返回明确拒绝结果而不是开放业务页面。
- 不执行 IntRuoyi `build-release` / `publish-test`；不操作正式服/备份服；不修改测试库或主程序业务数据；不记录明文凭据。

## 经验门禁

- Trigger: 测试服独立服务发布、服务器写入、端口 `18733`、PowerShell/SSH 编排、Docker 容器部署、真实 HTTP 验证。
- Preflight check: 先读取测试服访问、备份/恢复、PowerShell 编码/SSH、worktree 与上次助手部署记录；确认发布源 commit、artifact hash、远端现有服务归属、`18733` 监听对象、主程序端口现状和回滚路径；服务器写入前记录 `GREEN: experience-preflight -> PASS`。
- Blocker: 目标项目有未确认脏改动、缺 Dockerfile/启动脚本、无法确认测试服访问方式、`18733` 被未知服务占用、远端已有助手服务无法归属、主程序端口不可达且与本次发布边界冲突、或 artifact 无法证明来自目标提交。
- Verification: 本地 `node --check` 与静态测试 PASS、artifact SHA256、远端部署命令退出码、容器/服务状态、`18733` HTTP 状态、未授权访问拒绝、主程序 `8081`/`48081` 可达性。
- Forbidden action: 禁止发布或重启 IntRuoyi 主程序，禁止强杀未知进程释放端口，禁止用旧 artifact 冒充当前内容，禁止手工改测试库或绕过授权，禁止保存明文 secret 输出。
- Evidence: 本任务 `execution-log.md`、`verification-report.md`、服务器只读探测与脱敏部署日志。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否
- 是否从根因和长期维护角度解决：是
- 是否存在临时补丁或绕过：否

## Current Status

completed

## Milestone Status

1. 启动门禁与任务文档：completed。已读取 CI/CD skill、经验索引、测试服访问、发布备份恢复、PowerShell、worktree 与上次发票打印助手部署记录，并摘取本任务门禁。
2. 发布源冻结：completed。用户要求先整理并提交当前改动后再发布；助手仓库当前已无未提交文件，最新发布输入冻结为 `ba55fb8ddb5aa507d70e7d64f4a5d8c44a12179b`（`任务: 更新销售组织名称`），分支 `main` 领先 `origin/main` 5 个本地提交。
3. 本地验证与打包：completed。发布 worktree 内 `node --check` 与 4 个静态合同通过；源 artifact `invoice-voucher-print-assistant-ba55fb8.tar` 大小 `317440` bytes，SHA256=`3E6B6502AE2CD88AB8F17512EFA3DE42F106C5FF740C435F903EC6E3E0FCD5AB`。
4. 测试服独立部署：completed。已上传 artifact 到测试服，远端 SHA256 校验一致，构建 Docker 镜像 `erp-invoice-voucher-print-assistant:ba55fb8`，仅重启 `erp-invoice-voucher-print-assistant.service`。
5. 真实运行态验证：completed。测试服 systemd active，容器 `erp-invoice-voucher-print-assistant:ba55fb8` running，`0.0.0.0:18733` LISTEN；直连助手 HTTP 403 且显示无权访问，主程序前端 HTTP 200，后端 health `UP`。
6. 收尾：completed。`task-closeout-cleanup` preview/apply 均通过，已删除本任务临时 artifacts；助手发布 worktree `D:\ProjectPackage\Int\IntRuoyiWorktrees\invoice-assistant-standalone-r260831d` 已从 Git 注册和物理目录移除。

### Latest Blocker

无未解决阻塞。助手独立测试服发布、验证、任务自有临时产物清理和 release worktree 删除均已完成。
