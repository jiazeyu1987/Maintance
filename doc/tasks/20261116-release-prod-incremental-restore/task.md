# 同步发布与正式增量恢复闭环

## Goal
用户授权按六步执行：同步本地 IntRuoyi Git，固定提交构建；测试服发布验收；同包正式服发布；正式服增量备份；.59 准备空目标后恢复新点完整依赖链；验证版本、业务数据、附件和登录。NAS保留，未提交内容不进入发布包。

## Milestones
- [x] 确认配置和仓库，Git同步固定提交（最终发布源提交 ea50d70d；主工作区脏改动保留，最终融合待收尾）。
- [x] 独立发布worktree构建并测试服验收（18-57-58，同包技术验收及真实用户管理页面PASS）。
- [x] 同一releaseTag正式发布验收（18-57-58，正式开放及常规页面验证PASS）。
- [x] 发布后正式服增量备份；新FULL及INCREMENTAL均成功，原始父子点摘要绑定通过。
- [x] Spug准备.59并恢复新恢复点依赖链（9ddf本轮SUCCEEDED，数据、登录、版本及图片通过；历史PDF对象完整，页面既有缺口按用户确认记录）。
- [ ] 真实验收、提交记录和自有工作区清理。

## Expected Verification
发布核SUCCESS、manifest、env与实际镜像tag、backend UP、frontend200及真实登录；恢复核原生终态、数据、附件、登录和应用版本。只验收本次实际操作，不沿用旧轮次成功。

## 发布范围与结果
旧包2026-11-16-11-56-23的失败及回滚证据保留。最终源提交ea50d70d排除本地租户专用修复、未完成文件隔离改造及新增关闭审计环境限制，服务器保持DEVELOPMENT_DISABLED。最终包2026-11-16-18-57-58已完成测试及正式发布、真实登录和版本验收；新备份链、.59恢复及融合清理仍在推进。

## 经验门禁
- UTF-8读写，原任务已completed；保留无关dirty，fetch后确认远端及本地提交，不盲pull/reset。
- 读取release-backup-restore/server-access/login-access和命中的release-agent-checklist；高风险动作前记录GREEN。
- 只从已提交目标的新临时发布worktree构建，同包先测试后正式；.59按用户本轮恢复流程，不执行发布覆盖。
- 生产NAS禁止删除；备份链须核数据库UUID/日志连续及新版本关联，失败不默认成功或重提。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，使用现有发布备份恢复入口。
- 是否存在临时补丁或绕过：否。

## Current Status
ready_for_closeout：测试/正式同包18-57-58发布、新FULL+INCREMENTAL链、.59恢复9ddf及8表/附件验收已完成。用户报告8081入口不可达后，已补齐持久systemd网页入口和精确防火墙规则；真实公开URL登录、用户管理2117条、版本通过。此前隧道验收仅证明内部应用，公开入口缺口已纠正。应用ea50d70d融合并通过前端22/Java96；入口f33673f融合并通过主线3测试，其工作区已删除。唯一残留仍为原integration-20261116-sixstep物理目录，用户正在手动删除；本轮只读检查仍存在，暂不标completed。

## 审计启动限制修正（用户已确认）
结果：源提交ea50d70d已排除新增关闭审计环境限制；同包2026-11-16-18-57-58在测试服和正式服以DEVELOPMENT_DISABLED启动及真实登录验证通过。
目标：服务器明确配置 DEVELOPMENT_DISABLED 时按既有关闭模式启动；LOCAL_POLICY 限定独立local及回环库；FORMAL不变，缺失/无效配置仍失败。同步页面及当前说明，不修改迁移历史与数据库模式。
验证：模式单测、Spring上下文启动与关闭审计不加载策略、前端既有行为测试，后续新发布包真实服务器启动。无fallback、无临时绕过；删除关闭模式多余环境限制作为正式行为。

## 当前收尾阻塞
- 唯一剩余项：C:/SpugHandoff/release/integration-20261116-sixstep 的长路径残留目录。Git worktree remove已移除注册但报告Filename too long；精确Remove-Item删除被自动审批拒绝（blocked by policy），未给更具体原因。没有改用其他工具规避。
- 原未提交26文件、合并候选27文件、原任务说明及验证报告已保存于C:/SpugHandoff/release/sixstep-20261116/integration-preservation；主线实际文件与候选一致，3未跟踪文件SHA未变。残留目录不承载唯一源码或证据。
- 历史PDF按用户确认范围交付，不作为清理阻塞；不扩大DCC历史迁移，不重复发布/恢复/测试。
