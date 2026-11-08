# 57 MAIN 完整控制组件升级合同只读复核

## Current Status
completed — 本机只读合同审查完成；没有修改源码、测试或服务器。安装与实时验证由根任务继续执行，本记录不代表服务器已升级或已通过实时健康检查。

## 目标与里程碑
- [x] 确认现有 source/control/owner 配置形状及旧 MAIN 目标保持条件。
- [x] 对照新 STANDARD 130 文件合同，核 sourceEpochPolicies / targetBackupEpochPolicies 与 frontend readiness 差异。
- [x] 给根任务必要配置更改和不执行恢复的候选验证命令；私密内容仅输出最小必要字段或摘要。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。合同不匹配明确阻塞，不能绕过就绪和历史比较。
- 是否从根因和长期维护角度解决：是。按完整提交的实际入口合同审查正式配置迁移。
- 是否存在临时补丁或绕过：否。既有 target 对象及历史原件保持完全一致，策略通过 owner 顶层映射登记。

## 经验门禁
- STANDARD 冻结包实际入口、配置和已安装旧版本分别核对，不能用本地轻量源码代替新包合同。
- 主程序已闭合旧失败记录仍需原 target 完全相等，不移除字段或放宽物理目标比较。
- 源与恢复侧 epoch 策略必须同 root/sourceIdentity/databaseUuid/sourceLockPath，初始化持同一真实源锁。
- MAIN 前端/存储就绪使用正式语义 profile；健康协议与端点必须来自新代码合同，不以 running 或随意 HTTP 200 冒充。
- 本阶段仅本机只读审查，不连接远端、不执行恢复；完整私密配置与凭据不得输出或提交。

## 预期验证
比较提交中的配置入口与本机已采集实际配置；只输出结构、存在性、非敏感合同字段及必要修改。最终实机就绪由根任务在既有授权范围验证。

## 只读结果与验证边界

1. STANDARD 包已按实际 tar 内容核对：130 个文件，standard 变体，fileVerification / payloadContentVerification 均开启；清单内所有文件 SHA 匹配。实际包包含 epoch 模块、owner 顶层策略解析和 frontend_readiness 配置传递。此处没有构建或重新打包。
2. 原 MAIN owner 没有 targetBackupEpochPolicies，也没有 frontendReadiness。源与目标的数据库 UUID、物理 source lock 一致。应在两个新 control 顶层加入相同 sourceEpochPolicies，并仅在 MAIN owner 顶层加入 targetBackupEpochPolicies；原 targets 完整保持。新 epoch 根独立于应用数据及恢复 stateRoot，初始化须持原物理锁。
3. 原 MAIN 前端登记为桥接地址 172.21.0.3:80，后端为 172.21.0.11:48081；前端并非 HOST_NGINX/loopback 分支，因此不需要增加 frontendReadiness。用已采集真实容器 inspect 数据实际调用新 endpoint()，服务配置摘要全部匹配，得到 minio /minio/health/ready、backend /actuator/health、frontend /。这只是采集快照的合同验证，没有发出实时 HTTP 请求；实时结果仍须由安装门禁确认。
4. Native.selections(TARGET) 可核旧失败闭合依据、服务与存储身份、数据库 UUID、Redis 认证，但 observe_main_target 不调用 recovery_main_health.preflight/probe，也不调用 replacement_value(owner,TARGET)。已向根任务报告该覆盖缺口，并确认最新 installer 已在激活前增加下列实际新包调用：replacement_value 与 control 策略完全相等；health.preflight；三个服务 endpoint + probe，均须 ready=True、HTTP 200，后端内部另要求 status=UP。
5. 新 MAIN control 的 sourceConfigurations 必须绑定新当前来源 owner，不能沿用 MAIN 旧副本的 capture 配置。已确认 installer 使用 new[0].ownerConfigurationPin。来源 owner 内两处 captureCommand/toolPaths 的引擎路径会正式更新；采集配置本身没有引擎路径。MAIN owner 的 sources 和 targets 不包含旧引擎前缀，递归重绑定不应改变它们；installer 已显式断言 targets 与旧值完全相等。

## 激活前正式候选门禁

使用新包和新 control 的 environment / Python 运行，不需要创建恢复请求：

```python
n = Native(new_control_pin)
c = n.configuration()
owner = n.document(c['restoreConfigurations'][SOURCE][TARGET])
effective = replacement_value(owner, TARGET)
assert effective['backupEpoch'] == c['sourceEpochPolicies'][SOURCE]
assert owner['targets'] == original_owner['targets']
assert owner['sources'] == original_owner['sources']
preflight(native_with_actual_inspect)
for role in ('minio', 'backend', 'frontend'):
    result = probe(endpoint(native_with_actual_inspect, role), role, 10)
    assert result['ready'] and result['httpStatus'] == 200
```

其中 native_with_actual_inspect 仅绑定原 target、注册服务和真实 Docker inspect；frontend_readiness 从 owner 可选映射读取。最新 installer 已纳入策略和语义健康验证主体；建议同时保留 MAIN owner.sources 精确相等断言。来源侧新周期首次计划必须明确 BASELINE_REQUIRED，不能重新认可未绑定 epoch 的历史备份作为增量基线。

本审查不涉及 BDD/TDD 行为修改；既有实现的 Linux 回归证据由主任务记录。唯一新增交付是本审查文档，未提交私密配置或容器环境值。
