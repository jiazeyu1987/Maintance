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
