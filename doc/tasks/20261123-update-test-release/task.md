# 更新 IntRuoyi 并发布测试服

## Current Status
completed

## 目标及授权
更新 IntRuoyi 已提交代码到远端最新版本，然后仅发布测试服务器。前序 20261121-promote-tested-prod 已 completed；本任务不晋级正式服或审查服。

## 里程碑
1. 已完成：核对配置、Git 最新提交、当前运行态及发布锁。
2. 已完成：在新专用干净发布worktree构建275c87011。
3. 已完成：2026-11-23-22-02-22测试服运行态、菜单、版本、打印认证入口验证。
4. 已完成：发布结论已记录；所有本任务worktree清理通过，稳定执行器路径复核通过。

## 已完成与阻断
- 用户确认没有其他发布，继续仅测试服范围。
- 应用第一轮迁移登记修复4f528e1cd已构建18:31包；远端随后出现18:42前端配置更新，旧包被STALE_RELEASE拒绝，未部署。
- 已核实际远端基线；测试专属登记JOB-5253b19346成功。未知更新历史不追认为成功发布。
- 维护915ffca/075c841已提交融合并安装：打印助手运行期公开地址注入、历史登录失败覆盖证明门禁。相关回归94/101项通过；原内部assistant-host保留，实际内网探测符合健康合同。稳定执行器状态和其它配置保持。
- 应用运行期地址修复d14032e99已推送；35项直接相关测试通过。真实助手三个部署文件已只读交应用方补外部契约验证。
- 迁移预检已由f0806c282/d9022d50a修复；2026-11-23-20-22-13固定d9022d50a构建，同原封包续办JOB-29a5c45b86成功，原清理超时失败保留。
- 测试发布JOB-fd39bacc82 succeeded，独立运行态operation SUCCESS、manifest/.env/实际双镜像同tag，backend UP/frontend 200，无维护；登录、排产工单、版本说明通过。
- 原打印403已由275c87011修复；新包2026-11-23-22-02-22构建JOB-f8f6510f3c和测试发布JOB-2b57a4ae44均succeeded。新包独立运行态核对PASS，真实菜单、版本、认证票据及助手iframe全部通过，页面按6项非阻断观察记PASS_WITH_OBSERVATIONS。
- 所有本任务临时worktree均已按归属证明清理；维护两个提交已合回int_main并验证。稳定执行器PID14268路径C:/SpugHandoff/release/source，未使用临时worktree。未改其它任务工作区。
## 预期验证
同一 releaseTag 的 build-release 与 publish-test 成功；manifest、远端 IMAGE_TAG、实际双镜像一致，backend UP、frontend HTTP 200；Playwright 真实登录页面验收；自有 worktree 已清理且控制台保持稳定路径。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，使用正式发布链和固定提交输入。
- 是否存在临时补丁或绕过：否。

## 配置持久化修复设计
应用由IntRuoyi提供受权限保护的运行期公开地址；维护复用现有按目标profile注入JVM属性的发布模式，新增显式打印助手URL配置及校验，每次容器替换保留配置。不改恢复原件，不在通用包内硬编码测试地址；失败在停服前暴露。维护实现使用独立worktree，验证后提交融合并安装已提交源码。

## 经验门禁
- 先按已验证私密配置确定主程序路径与环境，阅读发布、访问、登录、worktree 和测试发布前置文档。
- 更新 Git 不覆盖未提交开发改动；构建仅使用本次目标提交的新专用 worktree，禁止复用或主工作区构建。
- 高风险动作前在 execution-log 记录 experience-preflight PASS；检查任务锁、原操作身份、迁移合同和恢复依据。
- 发布长阶段按原 job 与绑定 runtimeStagingRoots 核查，响应超时不重复派发。
- 测试服范围不执行 mark-tested、promote-prod 或 promote-backup。
- 页面异常按 release-page-acceptance 逐项归因，不把基础冒烟宣称业务全量 E2E。
- 收口先 ready_for_closeout，确认自有 worktree 清理与稳定控制台路径后 completed。凭据和原始私密输出不提交。
