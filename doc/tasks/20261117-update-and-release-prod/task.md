# 更新代码并通过 Spug 发布正式服

## Current Status
completed

## 任务目标与授权
用户明确要求“先更新代码，然后发布到正式服”。沿本会话 Spug 发布中心上下文执行代码更新、固定提交构建、测试服验证、同包正式晋级及业务验收开放。目标测试服 172.30.30.58、正式服 172.30.30.57；此次不扩展至审查服发布、数据清空或独立备份恢复。

## 前序任务
本会话前序 `20261117-spug-release-guide` 已 completed，提交 ca1801f；无本会话未完前序任务。

## 本轮续接
用户再次明确要求发布正式服务器，继续原更新代码及发布目标。上一轮已 fetch 远端，未合并、构建、创建 worktree 或操作服务器；浏览器 URL 验证无法完成导致工具终止。此次先重新核实际状态，使用产品支持的浏览器入口恢复操作，不跳过地址校验。

## 里程碑
- [x] UTF-8 bootstrap 与前序任务状态确认。
- [x] 确认当前 Spug 实例、仓库、活动任务、恢复策略及登记版本；实时运行态随阶段预检。
- [x] 更新参与仓库代码并固定本次提交：5ad3fd94179395b3ca96849b893ef66c571b0de7。
- [x] 新专用干净 worktree 构建不可变包：2026-11-17-23-51-44，JOB-5961273dd4 succeeded。
- [x] 测试服部署、真实页面与运行态验证、mark-tested（外部图标/头像观察单独保留）。
- [x] 同包正式部署、业务验收并开放；正常入口已完成真实页面及运行态核对。
- [x] 记录结论，完成任务自有资源与 worktree 收尾。

## 预期验证
单一 releaseTag；构建源为已提交固定内容；各操作最终成功，manifest/包双摘要相符，目标 IMAGE_TAG、实际镜像、health UP、HTTP 200、页面版本、真实登录及迁移状态一致。正式技术检查与业务验收分别留证。保留既有并发任务与凭据。

## 本任务 worktree
- 集成 worktree：C:/SpugHandoff/release/integration-20261117-prod-update；分支 codex/20261117-update-release-prod。
- 起点：16719d77cbaa496438a1e0622d5db9ec5d27508e；合入 origin/int_main=831ad4532321246e9e1763ec2ef47fb249c645b1。
- 主工作区27项未提交开发改动不进入构建；其中5项交集已三方保留融合，其他22项SHA256完全保持，索引未暂存。
- 构建命令：Spug真实页面 build-release（固定合并后提交）；实际构建worktree由执行器本轮新建，路径与清理结果如下。
- 验证命令：check-menu-migrations.py --staged、git diff --cached --check、发布迁移策略与构建/目标预检。
- 新提交：5ad3fd94179395b3ca96849b893ef66c571b0de7，合并远端业务及本机发布契约，并修复新迁移登记与有效租户/旧菜单识别；已合回int_main，干净状态Git删除exit0、路径和登记均无残留。
- 使用官方 reserve-worktree-slot 登记int_main profile slot7；未启动服务。清理时8088/48088无监听，持同一mutex将自身登记设inactive，其他项保持；主分支runtime port guard通过。
- 已合回 int_main：5ad3fd941，27项未提交开发改动保留；验证私密目录 main-integration-result.json 为PASS。
- 构建 worktree：C:/SpugHandoff/release/build/2026-11-17-23-51-44；提交5ad3fd941；命令为Spug build-release，产物封存成功，无新提交；执行器清理passed、git移除exit0、路径无残留。
- 维护工具worktree：C:/SpugHandoff/release/maintenance-20261117-env-metadata；起点7d54e301532c05bcb2a885e59a2753e4cf039f7f，目标67ffd43c241cd39595d462729e2b2697d6b14cdd。验证：test_runtime_env_metadata.py 5项PASS；已合回维护仓int_main同提交，仅3个新增文件；干净状态Git删除exit0，路径和登记均无残留。

## 最终结论
同包2026-11-17-23-51-44已完成build-release→publish-test→mark-tested→promote-prod→accept-prod；正式172.30.30.57:8081业务开放，测试同版本。7个本包任务均succeeded，manifest/包摘要、远端IMAGE_TAG、双镜像tag/digest、health UP、HTTP200、6项新迁移及正常入口真实登录/用户页面/版本均已独立核对。详见release-evidence.json。外部Iconify连接失败、历史外域头像及只读验收保护请求的观察完整保留；未宣称所有外部资源或全部业务功能通过。当前控制台稳定PID11716保持，所有本任务worktree已删除，无未合并提交或收尾阻塞。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，使用现行 Spug 正式发布工作流及远端已登记基线。
- 是否存在临时补丁或绕过：否。

## 经验门禁
- 先读 release-backup-restore/server-access/login-access、Spug 发布中心入口和命中经验；高风险执行前写入 experience-preflight PASS，否则阻断。
- 使用当次实际配置确认主程序根目录与执行器身份，禁止按旧电脑盘符猜测；检查活动操作、发布锁及恢复依据。
- 多机器历史缺失仅阻断具体无法验证的动作，不补造成功历史、不用模板覆盖私密配置。
- 仅从 Git 已提交目标构建，新建本次专用 worktree；固定同一包和 releaseTag 逐级测试、正式晋级。
- 隔离演练与正式恢复按实例显式策略执行；external 不等于已验证外部备份，不擅自改变策略。
- 正式技术检查后仍保持维护；真实业务验收通过后 accept-prod 开放。保护正式 /mnt/nas 挂载与全部既有共享资料。
- 发布后使用runtime_env_metadata.py核同包技术证明、双镜像、原IMAGE_TAG及远端锁后对齐单行；读回前不判版本一致，不能用标签更新代替部署/页面验收。
- Git 更新前核分支/远端/脏状态/交集，不丢弃、覆盖或提交无关改动；仅更新本任务实际参与仓库。
- worktree 创建、融合、清理先读 worktree-memory；删除前核绝对路径、归属、提交融合及验证。
- 中文文本显式 UTF-8；不打印、提交密码、token、私钥和连接串。
