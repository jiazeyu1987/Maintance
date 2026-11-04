# 执行记录

- 用户需求：解释截图中恢复服务器地址选项的“未登记目标”。
- 已执行唯一只读 UTF-8 bootstrap，读取适用 AGENTS、经验索引、PowerShell 经验与近期任务状态；未调用外部服务或执行恢复。
- 建立本会话独立只读核查任务；其他任务的 ready_for_closeout 状态不属于本会话前序任务。
- 本任务仅读取本机代码与说明，不连接服务器，不变更程序、配置或数据。
- 文档缺口：E:/IntRuoyi/docs/powershell-memory.md 与 release-backup-restore.md 不存在，历史 D: 路径同样不存在；初次 Get-Content 对缺失路径报参数错误，随后 Test-Path 确认不存在。不得声称已阅读；不执行需要上述文档的恢复等操作。解释仍可由本机源码直接确认。
- 代码证据：ops/spug/smallapp-ui/simple.js:11 按 product/server/mode 找当前绑定；:34 覆盖模式选择 overwriteTargetServers；:90-93 地址无映射时标“未登记目标”并禁用；:108-110 缺登记或当前不可用时禁止提交。
- 后端证据：ops/spug/smallapp_simple.py:12-31 读取独立 servers/bindings 并公开两类恢复目标映射；:50-54 按引用区分空目标和覆盖目标，禁止语义不明。ops/spug/README.md:154 登记不等于可恢复，目标选中后必须校验身份、连通及准入。
- 静态核对通过：提示表示当前组合没有绑定该服务器的恢复目标引用，不能据此判断离线或备份损坏。截图三台均缺映射，当前组合不能从列表选择目标；其他模式是否已登记及运行配置原因未核实。
- 本轮没有产品行为变更，无 BDD/TDD 或 E2E；没有新增进程、worktree、远程访问或业务写入。最终仅提交本任务记录。
- 续问：用户询问如何把一个数据包恢复到指定服务器。上一轮任务已 completed；本轮重新打开同一说明任务，只读确认页面实际操作和管理员目标绑定要求，无恢复授权或服务器动作。
- 续问证据：simple.js:210-249 注册页面事件，选择备份包/目标、刷新配置、展示冻结确认参数，覆盖方式显式勾选后方可派发；index.html:11、47 为两种方式及覆盖确认；无目标登记表单。smallapp_simple.py:9、31 明确目标映射由后台配置提供，服务器列表和恢复目标登记分离。
- 续问验证：rg 定位配置文件消费及页面事件，并交叉核对 README:150-156 的目标准入；只提供“管理员登记并绑定目标 -> 刷新配置 -> 选来源恢复点/模式/方式/地址 -> 核验确认 -> 观察执行并业务验收”的说明。未读取私密配置，未连接服务器或执行恢复，无产品改动、进程、worktree 或清理事项。
- 新截图续问：用户从 /backup-center 的“全部包清单”点击 .57 的 IntRuoyi 全量包恢复，弹框安全/覆盖模式没有目标。本轮只读核对该具体入口和包绑定，先记录任务，不将报错反馈视为恢复到正式服授权。
- 本机副本归属：先读维护仓与 C:/SpugHandoff 副本，发现缺少新清单 UI。全目录检索过宽，已停止本任务自身检索会话，无他人进程变动。随后 docker ps --format 的端口证明 18080 属 transfer、18081 属 handoff；早先读取 handoff 的非敏感映射不作为用户实例的配置证据。
- 当前入口证据：C:/SpugHandoff/sidebar-entry-20261104/upstream/src/pages/backup-restore/index.js 嵌入 /backup-restore/?embedded=1；18080 transfer 的 nginx.conf include /opt/intruoyi-spug/smallapp-entry.locations.conf；其 alias 指向 /opt/intruoyi-spug/smallapp-ui/，宿主 bind 来源为 C:/Spug/runtime/ops/spug。
- 当前 UI 证据：C:/Spug/runtime/ops/spug/smallapp-ui/simple.js:20-39 openCatalogRestore 冻结 packageId，匹配所选应用、包来源服务器及 safe，默认 replace；:134-136 固定恢复点；:163 在目标检查前拒绝未登记恢复点；:165 没有已登记且可用目标时显示截图提示。package-catalog.js:82-86 仅按备份类型及 indexed 启用清单恢复，不表示目标准入已通过；详情明确未全载荷校验或恢复验证。
- 当前配置证据：本机 docker exec 仅读取 /var/lib/intruoyi-spug/smallapp-simple-settings.json 并投影公开 product/server/mode/applicationId 与映射地址键，不输出其他字段。transfer 中 intruoyi-57-safe-20261024-v1 的 freshHosts=[.57,.58,.59]，overwriteHosts=[]；其他当前 IntRuoyi 来源的覆盖地址同样为空。精确原因已证实为覆盖映射缺失，不声称已查远端连通性或备份载荷完整性。
- 已询问用户目的服务器与方式；后续登记/恢复仍等待目标范围，未执行。无前端 E2E、网络调用、远端 SSH、配置改动或备份恢复任务；本机只读配置检查不是服务器运行态验收。诊断完成，UTF-8 与差异检查后仅提交本任务记录。
