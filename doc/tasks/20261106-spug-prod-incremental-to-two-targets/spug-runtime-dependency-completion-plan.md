# Spug 运行依赖与发布验收补齐

## Goal and Current Status

in_progress。已提交192ba38的唯一c1实际运行109.875秒、exit1：七配置均APPLIED，三服原HOST verify均PASS；最终Spug verify实际原生exit0但结果FAILED/SIMPLE_CONFIGURATION_INVALID，未生成成功核心。原v2和c1失败、claim、全部原件保持，禁止重派配置写入。

已证实根因线索：同一已提交c7728ad的smallapp_simple.py支持catalogueRestoreBindings，当前宿主运行文件仍是只接受nas/servers/bindings的旧版本。原PRODUCT_FILES只有11项，未包含被smallapp_entry/verify实际导入的smallapp_simple.py；因此原构建/安装的11项通过不能证明全部运行依赖已更新。先查完整实际依赖闭包和精确差异，不能仅手动覆盖一个文件后宣称修复完成。

## Milestones and expected verification

1. 保存c1实际原生终态与逐阶段/七APPLIED证据，只读核当前配置、运行Python依赖与候选同提交字节、实际导入位置及entry身份。
2. 按重构规范由原子代理先提出最小正式长期方案：构建清单覆盖实际运行依赖并校验遗漏；已有11项构建/安装作为历史原件，不修改旧pin。精确补充缺失依赖并保全原件，不重跑三服或七配置写入。
3. BDD/RED→GREEN→REGRESSION与父独立必要验证后限定提交，再按已有授权完成精确运行资源安装。已加载进程如需重载，只允许此前已授权的本任务entry，不重启容器/Docker/其它业务。
4. 原c1为全写入已完成、最后验证失败，后续仅明确版本化重新验收，保留原失败，不删除claim、不换ID复写。三服/Spug验证及真实UI、备份恢复仍逐项验收。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。完整依赖清单及显式最终验收，未知或遗漏拒绝。
- 是否从根因和长期维护角度解决：是。构建和安装覆盖产品真正依赖，避免部分文件通过被误判整体可运行。
- 是否存在临时补丁或绕过：否。不手工改配置/运行文件，不伪造旧构建或失败，不通过放宽产品配置校验隐藏不匹配。

## 经验门禁

- Trigger：部署清单未覆盖实际导入依赖，已完成配置写入而最终产品验证失败。
- Preflight check：固定旧两次失败、真实七APPLIED/三HOST PASS、当前配置pins、候选提交与依赖原文、运行源及真实导入路径、实例/entry身份。
- Blocker：依赖闭包未知、未能限定归属或精确安装对象、需要覆盖原失败/重复业务写入、缺真实最终验证。
- Verification：缺依赖真实RED、完整构建/部署依赖合同GREEN/回归、实际原容器读回和产品解析、真实页面。
- Forbidden action：不删除claim或改原pin，不重写已成功七配置，不全量复制ops目录，不重启整机/Docker/容器，不改NAS/fstab/18081，不用本机成功代替现场。
- Evidence：c1原attempt/七阶段/native stdout及outer completion；后续依赖检查、设计/TDD、安装与只验收记录。

## 父审查与第一阶段批准

完整审查spug-runtime-dependency-completion-design.md（18887B/SHAedd637287fc126901883631bf9edfea6e510e53fdf33fa3e10c699a095729dd0）后，批准第一阶段BDD/RED→GREEN→必要回归。仅新增spug_runtime_dependency_completion.py及专属测试/日志；不改旧11资源/PRODUCT_FILES、publication/v2/c1/selection/collector及任何旧350输入。共享纯闭包须实际检查14文件依赖关系，不能只写固定列表宣称完整。新补充报告绑定原c772已提交干净输入，原11及另2保持，真实安装只允许simple唯一目标；必须先保全原字节，精确entry重载及原容器配置/14文件读回。默认纯prepare、明确activate才写；子代理只本地实现测试，不操作Docker/服务器或提交。

第二阶段只验收/v4设计方向已认可，尚不修改其旧reader；先完成第一阶段并冻结交付，由父必要验证/提交/正式安装恢复页面解析。第二阶段不作为第一阶段安装前置。父负责提供实际c1配置测试输入、外层终态与PID不存在原件；实现不得使用占位pins或成功fixture替代它们。
