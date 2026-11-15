# 空目标控制器显式客户端白名单

## Current Status
ready_for_closeout

## 目标、里程碑与预期验证
父任务真实 v5 准备三阶段已 INITIALIZED，新目标 spug-empty59-733c9c2fe019 在登记选择时返回 TRANSPORT_CLIENT_FORBIDDEN。等待安装 agent 确认实际 peer 与原白名单后，正式传递 control.allowedClientAddresses，保留原认证；不修改已失败任务，不自动放行网段。里程碑为真实合同确认、BDD/RED、最小实现及定向回归、精确提交交审。

## 经验门禁
- 前一 prepare-cleanup 子任务已提交并部署，真实清理及初始化成功；最终闭环和收口继续由父任务负责。
- 本子任务只改本地源码与测试；真实客户端地址由已采证据明确，不从网络猜测、不自动放行全网。
- 遵循来源 IP 与运行依赖合同门禁，认证文件和其他配置字段保持；仅当前提交产物可供后续发布。
- 所有中文显式 UTF-8，BDD/RED 在生产改动前；不提交私密配置、凭据或远端原始日志。共享命令日志由父任务统一收口。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否；显式客户端配置非法时拒绝，不改变认证或屏蔽登记失败。
- 是否从根因和长期维护角度解决：是；新控制器监听地址变化后，应使用对应显式客户端白名单，不能沿用旧 tunnel-only 模板名单。
- 是否存在临时补丁或绕过：否；已有失败记录保持，后续重新从页面创建准备任务。

## BDD 与执行证据
- BDD: 显式控制器客户端 -> Given 安装配置包含实际 Spug 客户端 IP，When 生成新控制器配置，Then 使用该明确 IP 名单、保留认证和其余模板配置。
- BDD: 非法客户端范围 -> Given 配置为 CIDR、通配符或非 IP 值，When 构造配置，Then 明确拒绝，不启动全网可访问控制器。
- 真实根因确认：安装 agent 使用实际 Spug 容器短 TCP 连接与远端 ss 确认 peer=192.168.109.82；新控制器继承名单仅 127.0.0.1。仅私密安装配置显式增加实际客户端，不自动发现来源、不放宽认证。
- RED: 两个定向测试 -> FAIL，实际 control 文档读取仍返回 127.0.0.1，非法客户端配置未拒绝。
- GREEN / REGRESSION: `python -X utf8 -m unittest test_prepare_target_native test_prepare_target test_prepare_target_http test_prepare_target_registration -q` -> PASS 42/42；`git diff --check` -> PASS。
- 实现只增加规范 IP 列表字段，预览前检查配置并在新 control 文档中明确覆盖；认证等模板字段保留。生产执行/页面重建由父任务负责，本子任务没有远端写入，也不声称旧任务 READY。

## 工作区与交付
- 工作区：`C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/integration-worktree`；基线 `8beac1a8529daf426bfbfa3663a7898a40eff091`。
- 实现提交：`1750f2993eca706d41bd943263732ff784eaafc8`，仅 native 实现、对应测试和安装说明 3 文件。
- 发布仅需更新 native 及私密配置/pin；无前端或 entry 变更。父任务负责新 release-v6 与最终融合/工作树收口。
