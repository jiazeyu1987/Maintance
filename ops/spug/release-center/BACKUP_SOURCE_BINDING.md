# 发布后同步备份来源

将 `backup-source-binding.example.json` 中的 `backupSourceBinding` 合入对应服务器的私密 runtime 配置 `targets.<环境名>`，替换全部占位值。不能写到演示 inventory 配置，也不能从其他服务器复制路径或容器名。profile 后端、前端容器必须对应 containers 的 backend、frontend。运行账号需要读取已有来源配置并管理指定 systemd 服务；本次代码交付不自动部署配置。

字段来源：sourceRef 必须已登记在运行控制器的 sourceConfigurations、sourceProgramPolicies、sourceEpochPolicies 中；engineRoot 指已安装的恢复引擎，controlEntryPath 为其 control_entry.py；serviceName 为实际运行控制器服务；dropInDirectory 为该服务的 systemd drop-in 目录；pythonPath 为现有控制器使用的 Python。environmentFile、composeFile 是实际运行配置。generationRoot 是保留不可变来源配置和失败证据的私密目录；containers 是已登记 baselineTarget 的五种服务容器。

正式入口为 reopen/finish_reopen。发布先退出维护模式，正常 backend 和公共 frontend 健康后，再生成新来源配置：同步 IMAGE_TAG、实际镜像和容器 ID、配置材料、writer 证据及 baselineTarget，执行 capture preflight，随后持来源锁切换控制器。成功回执必须证明运行控制器使用新 config pin。不能在维护态 deploy 时绑定即将被替换的 backend。

无 backupSourceBinding 的普通发布返回 NOT_CONFIGURED，不推断来源；需要备份来源同步的服务器必须显式填写完整配置，缺项或同步失败会使发布失败，不报告来源同步完成。失败时业务可能已开放，入口保留绑定重试标记；同一 releaseTag、镜像和实际 backend ID 不变时可重试 reopen，发生漂移必须先调查。阶段失败保留 attempt 证据，已完成阶段按回执复用，不重复重启已激活的新控制器。

systemd drop-in 使用模块管理的固定文件，原子替换并保留前代证据，避免不同 releaseTag 排序改变生效配置。应使用专属且没有更晚排序 ExecStart 覆盖项的目录；运行 PID 的实际 config pin 不符会失败，不以 systemctl 返回成功替代实际激活验证。原 pin 与代次证据保留，不清理备份数据、不修改共享盘。

成功删除验收容器后移除绑定重试标记；已经完成的 reopen 不再次切换来源，会拒绝盲目重复开放并要求核对运行态。来源模块本身对相同已激活代次返回同一结果；这不代表可以重复执行已消费的完整发布尾部。

本机测试只证明代码及本机临时环境行为；线上验收需部署包含此模块的 release-center，按已核实路径配置 profile，再通过真实发布检查回执。普通发布的 NOT_CONFIGURED 不能作为备份来源已同步的证据。
