# Execution Log

- 用户需求：说明发票助手、分贝通助手、OnlyOffice本地卷实际数据；检查菜单和权限是否备份恢复。
- 前序20261117-backup-restore-completeness-audit已completed，提交bfbf44d；新建本任务只读追问审计。
- BDD: 本地数据分类 -> Given 正式部署挂载和实际文件，When 只读schema/代码/聚合清单交叉核对，Then 区分原始业务文件、状态/规则/登录资料、生成结果、缓存和服务内部数据。
- BDD: 菜单权限覆盖 -> Given 固定备份恢复点及真实权限表，When 核对各表完整内容指纹，Then 明确已恢复范围及时间点限制。
- 无产品代码或行为变更，不适用实现TDD；远程操作仅只读，不执行高风险写入。

## Preflight
- 显式UTF-8 bootstrap读取适用AGENTS、当前自有前序任务状态、experience-index和powershell-memory后立即建立本任务文档。
- 已按索引读取server-access、release-backup-restore及匹配的备份恢复经验入口；摘取门禁见task.md。
- 上一自有遗漏审计completed，commit bfbf44d9356545c610a03860fde13884c27faa80；本次沿用相同冻结链，不干预并发“检测进程”发布任务。
- 所有SSH均使用既有私密身份和known-hosts引用。只读Python通过stdin执行，未在服务器写probe；查询只输出schema、数量和允许字段名，未打印秘密或业务正文。

## Milestones and Evidence
1. `probe_local_data.py`：docker inspect核对实际挂载；文件stat和类型聚合；SQLite mode=ro/query_only读取真实表结构和数量。结果`local-data-inventory.json`，exit0。
2. `probe_service_semantics.py`：读取本地状态但只输出结构/字段名/数量，金蝶配置只输出变量名。结果`service-data-semantics.json`，exit0。动态记录ID和账户文件名不保留，结果文件名仅保留脱敏通用模式。
3. `probe_code_and_onlyoffice.py`：代码仅输出引用名和行号，PostgreSQL只读事务核实doc_changes=0/task_result=0，RabbitMQ五队列ready/unack均0。结果`code-onlyoffice-evidence.json`。Redis INFO exit1未吞掉或伪装为空。
4. `probe_onlyoffice_configuration.py`：只输出数据库/缓存目标和非秘密配置名；明确Redis错误分类为Connection refused。结果`onlyoffice-configuration.json`，exit0。
5. `probe_persistence_references.py`：部署tenant-store.js实际引用SQLite及app_key/access_token/bill_sign_key，支持独立接入配置归属。结果`persistence-evidence.json`，exit0。
6. `probe_permission_schema.py`：先读真实DESCRIBE，确认权限标识、数据范围、路由组件和租户字段；结果`permission-schema.json`。从前序全内容证据提取12表匹配关系，写入`permission-backup-evidence.json`，未重写原备份/恢复历史。
7. `data-classification-report.md`：说明实际数据类别、数量和固定点边界；仅审计的主链未覆盖辅助服务本地数据，未推断所有可能独立备份均不存在。

## Validation
- GREEN: BDD 本地数据分类 -> PASS，实际目录、schema/字段及代码引用相互印证；未把助手业务状态和认证资料归为可丢弃缓存。
- GREEN: BDD 菜单权限覆盖 -> PASS，system_menu/role/role_menu/user_role/tenant/tenant_package/dept/post/user_post/role_category/temporary_role_grant/temporary_role_grant_audit共12表完整行多重集指纹均匹配固定恢复点。
- 已知限制：system_users上次全表内容不同，不能声称所有用户字段完全一致；OnlyOffice本地Redis未连接，不能声称其内存为空或服务健康；本次不做登录E2E。
- 工具层一次JavaScript语法错误未派发远程probe，修正后执行成功。初版结构输出包含动态业务键，已改为聚合数量和字段结构并覆盖本地证据；未保留单号、个人信息或秘密值。
- 本任务未创建worktree，未启动/改动运行控制台，无远程probe进程遗留；仅本地任务文档与脱敏证据变更。

## Closeout
- GREEN: UTF-8无BOM/无替代字符、全部JSON解析、probe Python语法检查 -> PASS；16个任务文件逐一检查。
- GREEN: 聚合证据复算 -> PASS，发票27,050文件/3,006,098,356字节，分贝通四类记录数量及12张权限表匹配状态正确。
- GREEN: task-closeout -> PASS，无本任务worktree/运行控制台/远程probe遗留；仅暂存本任务目录和请求日志本次增量，保留无关修改。
- Current Status: completed；只读审计完成，不代表已实施辅助服务备份补齐或修复OnlyOffice Redis。
