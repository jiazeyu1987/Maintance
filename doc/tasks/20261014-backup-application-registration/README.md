# W08 应用登记与实际 r2 运行输入

当前入口为 `delivery.json`。本次已消费 W05 发布的实际 `smallapp-20261014-r2-redis` 安装输入，填入原 v3 交付和 `ApplicationRegistration/v1` / `three-component-20261014-r1` 登记；没有等待目标最终验收或 W05 全部验收。两应用沿用同一结构、原 Registry、原引擎选择和逻辑 source/target 别名。IntRuoyi 实际部署与本次共同引擎的等价关系仍未核实。

`runtime-binding-observation.json` 保存本次 exact owner 输入、Windows 传输 Pin 与 Linux 原件 Pin 的区别。`consumer-interface.json` 说明实际接线，`remaining-inputs.json` 分别列 W08 配置缺值和 W01 原动作解析缺值。原生执行、真实登录、备份恢复和 E2E 验收均为 false。

## 已消费的实际输入

W02 定版 source delivery SHA 为 `850bbfff94e371af0194eb12526feb033478f910e02a87892057eab8d9abc13c`，26 文件封存包 SHA 为 `aaa21b180ac2d21d250943c27fe87f091300b22df3002a5efbbf3e9f2d79dfe3`。十份 `r2-contracts/` 保持封存成员原字节，只用于本地消费，不是完整安装源码。W05 的 26 个已安装 Linux source Pin 与生产者成员 bytes/hash/路径后缀一致；Linux Python 实测 3.12.7，11 项声明依赖均匹配安装闭包。源实际五份配置、目标实际五份配置和镜像身份已记录。

W05 `stage/configure/verify/target_configure` 四份指定原件及后续已发布 `engine/build/materialize/target_materialize` 原件均被消费，其 Windows raw 传输副本 bytes/SHA 与所声明 Linux phase 原件一致。这个一致性不构成 W08 直接读取 Linux 原件、签名 installation、runtime trust 或原生授权验收。

源继续使用已存在的 MySQL schema `brlab_20261012_smallapp_source_20261014_r1`、MinIO bucket `brlab-20261012-smallapp-source-20261014-r1` 和原 source 目录，没有重新创建。源实际 r2 配置已代入 `runtime.sourceConfigurationFields`；误将 TARGET 配置代入 SOURCE 会被拒绝。源 PROTECTED，前端 HTTP 200，Redis 客户端 UP；DB0 为空、会话/记录/对象/附件均为零，`businessDataWritten=false`。这些事实不证明真实登录或 Redis 业务读取；源/目标 `applicationUseProofPin` 均为 null。

源 Redis 实际端点 `172.21.0.7:6379`，目标为 `172.23.0.4:6379`，各自独立容器，DB0，INFO 7.4.8，角色 instanceId 和 source/target 前缀保持原值。两份公开配置同用 `smallapp.redis`；私密逻辑引用分别为 `smallapp-20261014/source-private/redis-password` 与 `smallapp-20261014/target-private/redis-password`。引用已知，实际 native Registry/bridge resolver 尚未绑定，不能标 OWNER_BOUND。材料不包含凭据值或凭据哈希。

共同引擎 stage 记录有 62 个运行成员，后续 engine 原件有 63 个成员，包含同一 62 成员及一个新增运行契约；本地 W03 测试文件不在安装闭包内。stage 与首次 engine 的 artifact/version/entry 历史分别保存；当前 common-refresh 绑定另列如下。当前观察的选择为 `common-engine-smallapp-r2-20261014`，实际 signed installation、trust、service、engine approval、桥接端点及认证、当前 grant 和 HELD lease 均未交付，保持 null。W04 W07-R2-01 过期证据修复仅影响目标最终验收；本次 common-refresh 已刷新实际 artifact/version/共同闭包引用，独立 trust/签名仍 pending；以后实际安装新包时须再次更新受影响绑定，当前观察不是永久验收，也不冻结源 FULL。

`w05-installation-observation.json` 的 03:09 r1 是历史事实；上一轮交付保存在 `history/pre-runtime-binding/`，不再用它表示当前 r2 未安装。

## 语义与动作

Redis 会话缓存是业务必需的 `REBUILD` 类，MySQL 为权威来源，`rebuildFrom=DATABASE`，executor 为 `smallapp.redis-session-cache.mysql.v1`。有限键范围为实际 source prefix 加 `*`；不捕获 Redis payload。`recipePin` 指向原 W02 existing-derived adapter 契约，`derivedClass.configurationReferences` 指向 exact Redis policy，二者不能代替 W04 approved executor、trust、plan/request 或 `RecoveryDerivedExecution` 原件。

目标须在 DERIVED_DATA 前证明专属 Redis 为空、保持 PROTECTED，在真实 DATABASE 恢复后、应用启动前重建。有效 SQL 会话按原绝对 expiry 保留，规则仍为 `SET PXAT to floor(original SQL expires_at UTC in milliseconds); no sliding expiration`。`reloginRequired=true` 指授权 OPEN 后通过独立目标浏览器重新登录，不表示清空有效恢复会话。目标配置和早期 Redis 空库观察不能代替整目标当前 freshness 原件。

首个 FULL 不要求未来 parent、point、目标、capturedInventory 输出、schedule 或 retention。源当前剩余输入主要是实际 source resource/config 原生绑定、archive repository/service/policy、四个运行私密角色原生解析及授权登录后的 Redis/SQL 使用证明。START 不要求业务使用证明。INCREMENTAL 的真实 FULL parent 和 RESTORE 的真实选定 point 只能按原链路逐步产生。

实际 W01 `action_missing` 对 RESTORE 仍检查原 source resourceBindingPin/nativeConfigPin 与安装元数据；它不要求当前源业务使用证明或 live 源进程/Redis 私密域在线。RESTORE 另需所选目标的原 resource/config/freshness、真实链点和归档。完整缺值按实际解析单列，不能用 W08 纯配置完整性替代 W01 原生准入。

`source.redis-semantic-inputs.json`、`target.redis-semantic-inputs.json` 是显式 SEMANTIC 投影，已含实际观察的实例字段和剩余 `runtimeMissing`，`executionReadiness=NOT_EVALUATED`。Python 默认 RUNTIME；CLI 必须指定 scope。RUNTIME 在私密/使用/目标前置缺失时拒绝，未自动降级。工具不生成原生身份、签名、grant/lease 或派发操作。

## 本地使用与验证

```powershell
python -B doc/tasks/20261014-backup-application-registration/registration.py validate doc/tasks/20261014-backup-application-registration/smallapp.registration.json --verify-local-evidence
python -B doc/tasks/20261014-backup-application-registration/registration.py redis-inputs doc/tasks/20261014-backup-application-registration/smallapp.registration.json --action FULL --projection-scope SEMANTIC
python -B doc/tasks/20261014-backup-application-registration/registration.py redis-inputs doc/tasks/20261014-backup-application-registration/smallapp.registration.json --action RESTORE --target-config-ref smallapp-20261014-target-r1 --projection-scope SEMANTIC
```

结构和显式 SEMANTIC 投影成功；实际缺值导致 RUNTIME 拒绝。`--verify-local-evidence` 只核本地公开传输证据，输出明确列出 26 个 Linux application Pin 未验证；它不远端读取或提供原生验证替代。W01/W05 仍须在 Linux 传输并认证 exact source-delivery/adapter receipt 原件，核已安装配置/语义/policy/cache 原字节。接口给出封存成员到实际 Linux source 成员映射，未知 native receipt Pin 保留 null。

本次 `check_runtime_binding.py` / `checks-runtime-binding.json` 对受影响实际字段绑定、源目标配置拒绝、W01 纯 metadata/action、本地 CLI 和 RUNTIME 拒绝检查通过。W01 metadata 接受当前实际登记；`source_metadata_gate(FULL)` 准确返回 `REGISTERED_ACTION_INPUTS_UNCONFIGURED`，不能据此声称原生接纳。此前 8/8 语义检查复用 `history/pre-runtime-binding/checks-redis.json`，没有重跑完整 8/19/37 项或环境演练。历史 13/13、9/9 和此前活动代码观察各保留原范围。

`spug-display-projections.json` 是当前登记 SHA 的六字段片段；原 owner 需接到实际已导入 W01、认证 selections、任务 7/8/9 和实际桥接认证。它不是完整 settings 或授权。根 finite grouped review 已完成，不再列作新门禁；在本次消费的 root 状态中，真实业务/FULL/I1/RESTORE 释放仍为 false。

本地范围完成，`waiting_dependency / ready_for_closeout`。仅等待上述实际缺失原件及分阶段授权。本轮只写 W08 目录；无消息、Agent、SSH/SQL/API/UI、远端或业务写入、提交推送，PAUSED 监控保持暂停。

## 当前 common-refresh 有限更新

已消费 `common-refresh.json` 与其 raw 传输副本，后者为 23646 bytes / `2ea4c2d86410a791b0ed8ef1465f3779b3b98bdbbdd71a274643d24e768a796a`。同一 `common-engine-smallapp-r2-20261014` 当前 artifact 是 `common-refresh-source-phase-20261014/common-engine.tar.gz`，332335 bytes / `6f0b261fb191aa3f5fc00bd5d73b08493fbdf3e2e969cfa3c04dfd1a68edb0e2`；version 为同目录 `common-engine-version.json`，56922 bytes / `34392ca1ce897ac625f5755fe273823c4ec5303b9b99a60ac2c4c0a81730dbe0`。当前共同闭包为同目录 `common-installed-closure.original.json`，971225 bytes / `abb4ead7418ebcc9ece8eb5b153fbcfa9ef688110298b045af54d3e8c0461f83`。完整 Linux 原件路径见运行观察/交付。

原件记录三个模块实际更新，60 个成员保留、共 63 个；实际 Linux import exit=0。这只证明已安装修复模块，不能替代独立签名 installation/trust、原生源 resource/config 或归档 service。应用 r2 版本、Python/依赖、MySQL/MinIO/Redis 身份和应用闭包未变；应用闭包与此次共同引擎闭包分别保留，不混用。

旧 current engine 绑定及交付保存在 `history/pre-common-refresh-20261014/`。登记证据绑定和 Spug 当前 SHA 已更新；两份 Redis SEMANTIC 投影没有引擎字段，输入未变，已验证与当前转换结果一致。当前有限检查为 `checks-common-refresh.json`，未重复 20-Pin 整套、既有 runtime suite 或环境探查。匹配此次安装模块的 W01 纯 metadata 接受更新登记；实际原生运行验收仍为 false。
