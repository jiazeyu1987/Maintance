# 辅助服务本地数据与菜单权限备份核查

核查日期：2026-11-17。正式服为已核实的172.30.30.57，恢复目标为172.30.30.59。本次只读检查部署挂载、实际文件、数据库结构/数量及代码引用；未触发助手运行、备份、恢复、重启或业务写入。

## 结论

主系统的菜单、角色、权限标识、数据范围权限、角色菜单授权、用户角色绑定及租户菜单限制，均在所审计的主MySQL备份恢复范围内；相关12张表的整表内容指纹与冻结备份点匹配。三个辅助服务的以下本地目录/独立卷未纳入该条主系统备份恢复链，不能以主系统菜单恢复成功推定其业务状态和连接资料已恢复。

## 发票助手

实际容器：`erp-invoice-voucher-print-assistant`。三个挂载合计27,050个文件、3,006,098,356字节，约3.01GB（十进制）。

| 正式服主机目录后缀 | 实际内容 | 数量/大小 |
| --- | --- | --- |
| `.../erp-invoice-voucher-print-assistant/uploads` | 上传的发票PDF原文件 | 8,600个PDF，1,038,241,906字节 |
| `.../erp-invoice-voucher-print-assistant/results` | 生成的ERP凭证PDF、凭证与发票合并打印包，以及发票号提取、待查询清单、ERP查询/映射结果、处理汇总和上次结果状态JSON | 9,208个PDF、9,240个JSON，1,967,855,832字节 |
| `.../erp-invoice-voucher-print-assistant/runtime` | 两份`.env.kingdee`，包含金蝶地址、账套、用户名/密码及应用认证/签名相关配置项 | 2个文件，618字节 |

上述目录完整前缀为`/opt/intruoyi/runtime/erp-invoice-voucher-print-assistant/`。文件类型、通用结果文件名模式与部署的生成凭证、合并PDF、提取发票号和查询映射脚本相互印证。只检查连接变量名，未输出配置值、发票正文或业务单号。

这些内容同时包含原始业务文件、生成结果和认证资料，不能整体归为缓存。此处未证明另有独立备份，也未把“该链未覆盖”扩大为“所有备份均不存在”。

## 分贝通助手

主机目录`/var/lib/docker/fenbeitong-release/data`挂载至容器`/data`，共4个文件、75,788,418字节，约75.8MB。

| 文件 | 实际内容 |
| --- | --- |
| `state.json` | 3,349条同步单据、222条凭证/ERP推送处理记录、4个同步批次、200条操作日志；另有当前租户/金蝶账户选择及申请人员目录状态 |
| `fenbeitong-tenants.sqlite` | `fenbeitong_tenants`表2条租户接入配置：接口地址与路径、认证模式、应用标识/密钥、访问token及过期时间、账单签名密钥、拉取范围和请求配置等 |
| `.sqlite-wal`、`.sqlite-shm` | 对应SQLite的WAL与共享内存辅助文件；属于正在使用的SQLite持久化体系 |

同步单据的已观察字段包括单号/类型、金额/税额、报销或付款信息、申请人、员工编号、银行账户、部门/组织及处理状态。凭证记录包含ERP结果/编号、历史推送、重试错误、幂等键和内容哈希。这些是集成业务状态和防重复处理依据，不宜仅按可再生成缓存理解。

数量是当前本地记录数，未逐条判定真实/模拟来源；未输出个人银行信息、单据正文或接口秘密值。该独立SQLite中的接入租户配置，不能由主系统`system_tenant`和菜单表恢复替代。

## OnlyOffice独立数据卷

实际容器：`intruoyi-onlyoffice`，共有7个独立挂载卷。下列为容器内路径；主机实际卷标识见`local-data-inventory.json`。

| 容器目录 | 保存内容与当前观察 |
| --- | --- |
| `/var/lib/postgresql` | 本地PostgreSQL数据库文件约64.8MB。`onlyoffice`库的`doc_changes`保存文档协作修改，`task_result`保存文档打开/转换任务状态、回调等；检查时两张表均为0行 |
| `/var/lib/rabbitmq` | 消息队列内部数据库与持久化状态，约205KB；检查到5个队列，待处理和未确认消息均为0 |
| `/var/lib/redis` | 当前卷内0个文件。对配置指向的本地Redis探测返回Connection refused，未取得内存键数量，不能据此宣称Redis健康或内存数据为空 |
| `/var/log/onlyoffice` | 服务日志及压缩历史日志，73个文件 |
| `/var/www/onlyoffice/Data` | `wopi_private.key`、`wopi_public.key`密钥对及`.private/ds_release_date`版本标记，共3个文件 |
| `/usr/share/fonts/truetype/custom` | 自定义字体目录，当前为空 |
| `/var/lib/onlyoffice` | 当前卷内无文件 |

因此当前已观察到的是服务内部数据库、队列、日志、WOPI密钥等；文档修改和任务表目前为空。空表/空目录只代表检查时状态，不能推断历史上从未使用，也不能把密钥等全部视为可丢弃缓存。本次未对业务文档原件在其他存储中的归属作全量追踪。

## 菜单、角色和权限是否备份恢复

**是，针对下述已成功恢复的固定备份点，已核实。** 本次读取正式库真实`DESCRIBE`，将配置字段映射到上次审计的整表指纹，证据不限于行数。

| 配置/关系 | 表 | 冻结点及恢复目标行数 |
| --- | --- | ---: |
| 菜单树、路径/组件、显示状态、权限标识 | `system_menu` | 1,930 |
| 角色、数据范围和部门范围配置 | `system_role` | 81 |
| 角色拥有的菜单及其租户绑定 | `system_role_menu` | 7,171 |
| 用户角色及其租户绑定 | `system_user_role` | 2,201 |
| 主系统租户 | `system_tenant` | 4 |
| 租户套餐及可用菜单集合 | `system_tenant_package` | 1 |
| 部门、岗位、用户岗位 | `system_dept` / `system_post` / `system_user_post` | 347 / 5 / 13 |
| 角色分类 | `system_role_category` | 30 |
| 临时角色授权及审计 | `system_temporary_role_grant` / `system_temporary_role_grant_audit` | 0 / 0 |

以上12张表，备份点与恢复目标的完整行多重集SHA-256均匹配。`system_menu.permission`、路由/组件字段，`system_role.data_scope/data_scope_dept_ids`，关系表的`tenant_id`及套餐的`menu_ids`均属于相应整行校验范围。

用户表2,155行也在恢复范围内，但上次审计已发现其运行后内容指纹不同；本报告不将其宣称为逐字节相同，不影响上述12张已确认匹配的配置/关系表结论。本次未进行登录后的权限功能E2E。

## 时间与证据边界

- FULL：`smallapp-8d9db80d8f1e4531ba9a0234335d0dcb`，manifest时间2026-11-16 15:30:57 UTC。
- INCREMENTAL：`smallapp-bf67a867d3ec4e369ca31657c45e62c6`，manifest时间2026-11-16 18:19:56 UTC。
- 恢复：`smallapp-9ddf6a1391f14bddb7af731a53f69a5e`，完成于2026-11-16 22:25:52 UTC。
- 冻结点：`sha256:9d106914764c9e72cee2dd992c5a8c991a4ea2a36759f9d63aec438bdaa37c4e`。

主系统菜单权限结论对应上述冻结点；之后正式服新增/变更的配置不因此自动视为已经恢复。辅助服务文件数量来自本次对运行中系统的只读观察，并非跨服务一致性快照。

直接证据：`local-data-inventory.json`、`service-data-semantics.json`、`code-onlyoffice-evidence.json`、`onlyoffice-configuration.json`、`persistence-evidence.json`、`permission-schema.json`、`permission-backup-evidence.json`。备份覆盖/目标指纹来源为前序任务`../20261117-backup-restore-completeness-audit/`的审计记录。
