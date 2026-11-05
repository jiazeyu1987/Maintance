# 正式新全量包经 Spug 恢复测试服验收

2026-11-05：本轮正式服 172.30.30.57 新全量备份，经真实 Spug 页面恢复到原测试服 172.30.30.58 MAIN，备份和恢复均真实成功。该结论只覆盖此来源、此新备份点和此目标。

## 操作与身份

- FULL：History350，`smallapp-73cd541a95d84d6a86f9d693e4053c75`，14:17:28 成功、原退出0。归档 14378 个载荷文件、26090562595 字节，COMPLETE 及独立读回通过。
- RESTORE：History355，`smallapp-6cb9423086fe4b62ad21505e189bc36b`，19:04:19 原生成功、实际退出0。页面每次只提交一次，前四次失败另行保全，未改写成成功。
- 恢复点：`sha256:e94ad09d511f2b9ebb576e8b8f460a04087ddfbf3d2ed92b6391bb658b59d3c4`；精确绑定本轮新 FULL，未使用旧备份代替。
- 目标：`intruoyi-main-58-safe-restore-20261104-v1`；原五个容器和镜像保持，数据库 UUID `20ca4c6c-cc31-11f1-9b95-0242ac1deb16` 保持。

## 验收证据

| 项目 | 实际结果 | 记录 |
| --- | --- | --- |
| 数据库 | 885 表、512156 行；完整结构与行摘要一致 | restored-native-evidence.json、fifth-database-comparison.json |
| 附件 | 5916 个版本、4920 个唯一内容、9653189892 字节；原版本 ID 与内容回读一致 | restored-native-evidence.json、fifth-object-comparison.json |
| 引用与约束 | allReferencesVerified / presentReferencesVerified / invariantsVerified 均 true；源缺失引用0 | restored-native-evidence.json |
| Redis | 受控 DB1 本次源快照0键，恢复0键；值/绝对到期校验通过 | restored-native-evidence.json |
| 运行状态 | 原五服务运行，backend UP、frontend HTTP200、数据库 UUID 保持 | restored-runtime.json |
| 真实页面 | Chrome真实登录、按菜单进入用户管理，2117条/当前20行，版本2026-11-03-12-15-42，业务写入0 | target-after-restore-business.json |
| 原包与清理 | 最终archive-verification及restore-cleanup完成，暂存清理文件数/字节和路径缺失逐项校验 | restore-live-progress.json、restored-native-evidence.json |
| 资源与历史 | 宿主预约按VALIDATED_CHILD_SUCCESS释放，active不存在；原第三次失败6份pins保持 | restored-native-evidence.json |
| 正式源保护 | 原五服务健康；12个受保护容器配置/挂载保持，11个PID/启动时间保持，MinIO停启属于已授权采集 | exact-source.json、source-after-full-preservation.json |

原生应用启动回执的 businessAcceptance 为 NOT_PERFORMED，独立真实页面验证补充了登录、权限、版本和用户列表可用性；未将其改成完整业务回归。本轮空 Redis 快照不能证明非空键及TTL的真实恢复案例。DCC项目代码页原基线无记录的限制保留，不宣称全部业务流程验收。serverDurabilityVerified=false 的备份原字段保留，不声称已验证 NAS 服务端耐久性。

## 修复与收尾

SAFE实际包接口/破坏性SQL审计及保留失败续恢复修复提交9176b3c；独立数据预算提前校验提交04f5f9c。后者 Windows118、Linux195必要回归通过，正式16GiB校验预算与64GiB SQL展开上限保持独立。

两个本次专用临时发布worktree均无新提交、构建前后干净，Git登记与物理目录已删除；不需要合回发布副本的新提交。实现保存在本任务开发分支，按现有清单不自动融合int_main；开发worktree仍由原三服目标登记任务使用。控制组件和守护通道使用服务器引擎目录及C:/Spug稳定路径，不依赖已删除的发布checkout。旧失败目录及其暂存材料保留，本次清理不涉及NAS备份或其它任务资源。

本轮证明正式来源→测试目的地路径可用。正式服作为恢复目的地尚未启用；.59已有登记但本轮未执行数据恢复。原三服登记任务的剩余准入与配置核对须继续单独处理，不能用此验收宣称三个目的地全部就绪。
