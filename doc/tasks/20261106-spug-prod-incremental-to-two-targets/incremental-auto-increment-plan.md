# 增量恢复冻结自增状态修复

## 当前事实与阻塞
History368实际FAILED_RETAINED/exit1，原生SQL importer实际exit0，最终FORMAL_SCHEMA_MISMATCH。03:04Z在仍停写的真实目标上只读批量核完整元数据，全部catalog相等，规范化后的全部定义只有mes_kingdee_production_order_sync_record一处不同：冻结AUTO_INCREMENT=30384，目标=30376；仅替换这个计数后该DDL逐字相同。不能将其忽略或归一化为一致：这会丢失下一次分配主键的状态。

## 正式方案
增量BINLOG_SQL回放结束后、数据独立回读之前，依据同一不可变expectedDataPin中冻结的完整schema还原自增状态。只从实际自增整数列及SHOW CREATE TABLE顶层表选项提取计数，字面量、注释、列内部文本不得成为表选项；校验完整schema证明、表/列绑定和有界正整数。通过真实MySQL元数据读取当前计数，仅对不同且结构合同匹配的表执行明确ALTER TABLE AUTO_INCREMENT。操作在既有目标身份/锁/停写/原生SQL退出确认保护内，写意图、实际退出与前后值证据；原完整结构/数据、对象、引用、Redis及应用验收保持。未知格式、身份漂移、字段/表差异、SQL错误或最终计数不一致继续硬失败，不忽略校验。

实际实现直接复用observe_schema完整观察原生SHOW CREATE和catalog，提前证明全部其它结构，接受额外观察耗时；不新增缓存或猜测信息表计数。只对差异表在原生mutation前再次读取完整原DDL，写后从真实SHOW CREATE核列/计数/其它定义；最终独立数据回读仍保持原严格schema检查。

本次不修改来源归档、冻结证明、历史结果或现有业务行。只升级确实需要的目标控制组件；正式来源控制及主程序保持。构建必须来自本次修复已提交目标的全新干净专属worktree，不复用两份既有构建目录。

实际最小恢复入口使用独立modules_from登记，须同时加入formal_schema_evidence并对SAFE冻结封包应用唯一上下文变更；只给通用NativeData加载器加模块不足以覆盖MAIN路径。补充真实封包在独立进程调用实际modules_from的两变体测试，缺失先RED。9a65b5a控制安装记录保留且不派发恢复，最终只能使用含入口修正的已验证新提交封包。

## BDD与TDD
- Given 已冻结schema/真实只读差异及未使用的自增号；When 增量回放完成；Then 按冻结值恢复计数，最终完整schema/data严格一致。
- Given DDL注释/默认字面量中含AUTO_INCREMENT样式文本、重复表选项、非整数自增列、身份/证明或表列漂移；When 生成或执行还原计划；Then 拒绝，不执行错误ALTER或吞掉失败。
- RED先以真实30384/30376证明和孤立MySQL真实INSERT IGNORE或回滚分配场景复现；GREEN只补齐正式计数恢复；REGRESSION核原完整schema/data、SQL导入、增量协议及封包接口。真实MySQL测试不得在三服业务库创建测试数据。

## 失败保护与后续执行
先完整SHA固定History368所有恢复/ledger原件，保留旧请求/结果/导入器与885表tokens及原配置。严格按已有recovery_retained_retry合同核原worker和原生导入器退出、原五容器身份、885表、停止writer、原锁/预约、归档/端口/scheduler保护；只追加同点同目标clearance与保护交接，不删除锁、改失败历史或启动未验收应用。修复验证/提交/新构建/限定安装通过后，Spug真实用户路径仅提交一个新操作号重新恢复同一新增量整链；新旧尝试独立保存，不能覆盖368回执。测试服新尝试完整验收后才派发备份服。

安装执行合同：inspect_allocator_target_upgrade.py只读固定两目标当前target-installation、owner/control、全部引擎SHA与服务状态；.58核原保留预约和885表，.59核无预约且原五服务运行。install_allocator_target_control.py只使用本次独立提交的全新干净worktree封包；持原物理锁和宿主预约锁，安装engine-allocator-<commit>及全新owner/control、zz-allocator服务drop-in，归档原指针与unit。owner.targets与sources必须逐字段保持，仅formalModuleDirectory和对应控制程序路径/pins切换；仅重启本任务目标控制服务，实测新PID/命令/65536句柄继承。前后完整容器集合/定义/镜像/PID/启动时间、fstab和保护挂载保持。对.58全部2842原件再次实读SHA后核前后稳定身份及小元数据SHA，原保留预约/旧安装保持。安装本身不执行恢复、不启停业务服务或解除旧保护。

尝试选择使用显式restore-selected-attempts.json；.58新尝试kind=restore-58-r2，原restore-58/History368文件保留，.59仍restore-59。没有选择清单或路径不匹配立即拒绝，不自动使用最新或旧失败操作；新的准入允许且必须凭正式同点同目标clearance验证已停写原实例，不能先启动失败应用来满足普通健康准入。

## 经验门禁
- Trigger：增量SQL importer exit0而FORMAL_SCHEMA_MISMATCH，冻结自增状态与回放结果不同。
- Preflight check：核真实不可变源schema和完整目标catalog/定义差异；保留失败全文件pins、worker/importer终态、停止writer、锁/预约及原实例/共享盘；先完成真实隔离MySQL RED/GREEN和严格负例。
- Blocker：任何非计数结构差异未解释、格式/证据漂移、真实测试缺失、活动worker或未能按既有合同交接保护，阻塞安装/新恢复。
- Verification：固定源计数/实际目标计数/退出/回读证据，真实UI新操作完整数据库数据和结构、对象/引用/Redis/应用/其它业务/共享盘验收。
- Forbidden action：不移除AUTO_INCREMENT比对、不用MAX(id)+1代替冻结状态、不伪造或改写368、不直接重提同操作号、不删失败原件/锁、不修改公司/mnt/nas或fstab。
- Evidence：restore-368-failure.json、restore-368-schema-difference-summary.json及对应私密完整比较，后续TDD和实际安装/新操作回执。

## 设计约束检查
- 是否引入fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，恢复增量日志未必携带的已冻结分配器状态。
- 是否存在临时补丁或绕过：否。
