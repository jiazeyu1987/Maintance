# 20260829 发票打印助手测试服部署任务

## Task Goal

将 `E:\ProjectPackage\erp-invoice-voucher-print-assistant` 下的发票打印助手发布到测试服务器，并让主程序可通过测试服 `18733` 端口打开查看。

## Milestones

1. 启动门禁与任务文档：创建任务记录、记录 BDD/TDD 边界、摘取发布/服务器/PowerShell 经验门禁。
2. 项目与部署方式复核：读取目标项目说明、构建脚本、Docker/静态资源部署方式、端口配置和测试服接入方式。
3. 本地验证与打包：在不引入 fallback 的前提下运行目标项目必要测试/构建，产出可部署 artifact。
4. 测试服部署：按测试服访问文档发布 artifact，配置服务暴露 `18733` 端口。
5. 真实运行态验证：从测试服本机和本机访问链路验证 `18733` HTTP 可达，必要时验证主程序可打开该地址。
6. 收尾：记录验证报告、清理任务临时产物，更新任务状态和命令日志。

## Expected Verification

- BDD: Given 发票打印助手已有可构建项目，When 发布到测试服务器并暴露 `18733`，Then 测试服 `18733` 返回可打开的前端页面，且主程序可通过该端口查看。
- RED/GREEN: 若需要新增或修复部署配置，先写配置/脚本合同 RED，再实现并验证 GREEN。
- 构建命令、部署命令、远端服务状态、端口监听、HTTP 状态码、页面可见性都必须记录证据。
- 不操作正式服/备份服；不修改 IntRuoyi 主程序业务数据；不记录明文凭据。

## 经验门禁

- Trigger: 测试服部署、服务器写入、端口暴露、PowerShell/SSH 编排、前端构建与真实页面验收。
- Preflight check: 先读取 `E:\IntRuoyi\docs\server-access.md`、`E:\IntRuoyi\docs\release-backup-restore.md`、`E:\IntRuoyi\docs\powershell-memory.md` 和目标项目自带规则；确认测试服目标、端口 `18733` 占用情况、构建命令、artifact 来源和回滚路径；高风险动作前记录 `GREEN: experience-preflight -> PASS`。
- Blocker: 缺测试服访问方式、端口被未知服务占用、目标项目不可构建、部署目标目录无法确认、需要凭据但无安全来源、或远端验证无法证明实际服务为本次 artifact。
- Verification: 构建/部署命令退出码、artifact 摘要、远端进程/容器状态、`18733` 监听、测试服 HTTP 200、页面内容/标题和必要主程序访问证据。
- Forbidden action: 禁止部署到正式服/备份服，禁止强杀未知进程释放端口，禁止用 mock 服务或旧 artifact 冒充成功，禁止修改主程序业务数据或跳过真实 HTTP 页面验证。
- Evidence: `docs/experience-index.md`、`E:\IntRuoyi\docs\server-access.md`、`E:\IntRuoyi\docs\release-backup-restore.md`、`E:\IntRuoyi\docs\powershell-memory.md`、`ci-cd-environment-delivery` evidence contract。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否
- 是否从根因和长期维护角度解决：是
- 是否存在临时补丁或绕过：否

## Current Status

completed

## Milestone Status

1. 启动门禁与任务文档：completed。已创建任务文档，完成经验门禁摘取，并在高风险动作前记录 `GREEN: experience-preflight -> PASS`。
2. 项目与部署方式复核：completed。已确认助手项目默认端口、授权 callback、主程序 iframe/ticket 契约和测试服边界。
3. 本地验证与打包：completed。助手发布源已更新为提交 `92d47d54ca7ff831264a1b97742e0c4a174f15fa`；维护仓发布脚本已修复并行复制和进程退出码捕获；主程序最终发布输入为提交 `60fb439d75659a4a9276e39a241f28f005292218`，发布包 manifest 记录 backend/frontend 均为该提交且 dirty=false。
4. 测试服部署：completed。已将助手容器/服务部署到 `172.30.30.58:18733`，远端服务已按端口监听。
5. 真实运行态验证：completed。主程序测试服 releaseTag `release-20260830-invoice-assistant-test-r260830k-r1` 已发布；`aoteman` 从 ERP 菜单通过 ticket/callback 打开助手 iframe，`dccmatrixregsvc` 无权限看不到菜单，直连助手返回 403。
6. 收尾：completed。已完成经验沉淀、`task-closeout-cleanup` 清理任务临时产物，并删除本任务拥有的临时发布 worktree。

### Latest Blocker

无未解决发布阻塞。`r260830k` 发布与真实 Playwright 验收均已通过，收尾清理已完成。
