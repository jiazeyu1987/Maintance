# 无人查询成功增量自动登记

## Current Status

local_verified；远端安装与真实连续增量验收尚未完成，完整任务保持 in_progress。

## 目标、场景与设计约束

Given 独立备份 worker 已成功且退出、launcher 原回执仍为 exit2/RUNNING、I1 三个控制登记尚不存在，When 用户再次点击增量备份或查询自动计划，Then 控制组件核原终态与不可变材料、自动登记 I1，并选择 I1 为父点。不得依赖浏览器先详细查询、手工补登记或重写原 completion。

无 fallback、降级、吞异常或临时绕过；从自动异步闭合解决根因。只在持原来源准入时发布，缺件、冲突、worker 存活或 epoch 漂移明确阻断。完整旧登记仅核小证据；详细查询及当前候选链保持完整验证。

## 里程碑与必要验证

- RED：真实 Linux launcher/worker/文件，预期 I1，实际返回旧 FULL；1 FAIL、0 ERROR、0 SKIP，native1。原 fixture 前置错误另行保留，不计产品 RED。
- GREEN：15 PASS，覆盖无人查询后控制重启、新控制保留原 owner、部分发布续办、epoch 漂移、缺登记依赖、原件冲突、失败不发布、并发不能选旧父。没有预写 I1 登记。
- REGRESSION：既有异步闭合与计划 68 PASS，原180秒子进程和300秒父预算保持。
- 提交切面独立验证：从 Git index 冻结真实16个源码 blob，排除工作区既有 MAIN 恢复保全改动；四套83 PASS，0 FAIL/ERROR/SKIP，native0，输入保持、容器移除。该精确 index 才是本实现提交依据。
- 后续：以干净专属发布 worktree 构建并安装 source 控制，再从真实 Spug 验证原 I1 无手工登记收口及 I2 自动接续；不以本地协议测试替代。

原生结果、JUnit、输入 SHA 与精确提交源码清单见 `unpolled-incremental-native-verified-r1.json`。所有本轮测试网络隔离，只使用有限协议文件和真实进程，远端动作及业务数据写入均为0。

## 经验门禁

- Trigger：异步 exit2/RUNNING completion 与 owner 成功并存，下一次计划仍选旧父。
- Preflight check：先只读保留原登记缺失现场、原 owner 终态/worker 退出及完整绑定，再做无预登记 BDD/RED；不通过详细 query 掩盖现场。
- Blocker：原请求/配置/路径不符，活动 worker，材料校验失败，登记冲突，epoch 漂移或任何测试前置失败。
- Verification：真实进程 RED→GREEN、有限相关回归、精确 index 测试；安装后另核真实 Spug 父链。
- Forbidden action：手工登记、改原 completion、退回旧 FULL、放宽期限或把本地成功当上线完成。
- Evidence：`unpolled-i1-registration-20261111-r1.json` 与上述验证摘要、主 execution-log。
