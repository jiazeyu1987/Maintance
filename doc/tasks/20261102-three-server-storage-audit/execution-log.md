# 执行记录

- 用户：分析正式服、测试服、备份服有哪些内容可以删除释放空间。
- 授权：三服只读状态与存储诊断；此次不执行删除、配置修改或发布。
- 前序完整包/前端补丁发布未因本次审计自动恢复，原发布历史与空间阻塞保留。
- Bootstrap：明确UTF-8读取适用AGENTS、前任务、经验索引；E:/IntRuoyi/docs/powershell-memory.md在当前电脑不存在，将核已确认实际源码映射，不猜测远端访问资料。
- 前序复核：任务文件已出现2026-11-02多机器接管规则修订，故不继续沿用“必须重新导出”的旧结论；本次保留原任务资料，专注当前用户的只读空间分析，发布空间和真实恢复证据仍未解除。原任务未完成，不宣称完成，也不改写其后续规则修订。
- GREEN: experience-preflight -> PASS（仅只读三服存储诊断）；已按实际源码C:/Users/D01021/Documents/ChatGPT/IntRuoyi读取server-access、release-backup-restore、powershell-memory及命中release-agent-checklist。TEST58/PROD57/backup59均由本次用户明确授权分析，无服务重启/写入/备份/恢复/删除授权需求。使用既有profile+StrictHostKeyChecking密钥通道，远端Python从UTF-8 stdin执行只读元数据命令，不输出Env、日志正文或凭据。

## 采集与验证
- 2026-11-02 01:01–01:15 UTC：三服执行df -B1 -T、findmnt目标/源/类型、Docker info及allowlist inspect、du -x -B1、指定文件stat、/proc fd/cwd引用检查。du使用nice/ionice及超时，排除公司共享NAS；不读取数据库或对象正文，不执行远端写操作。
- 第一轮Docker df -v含命令列，已从可交付证据删除完整Containers段；原件只留Git外。挂载options同样不进入摘要，防止连接选项泄漏。当前容器事实来自明确字段白名单，不保存Env/完整Command。
- 采集载体曾遇到远端Python3.6不支持capture_output；修正为stdout/stderr PIPE后重跑成功；本地一条复杂inline汇总命令引号错误，在执行前SyntaxError，改用UTF-8 .py载体成功。未将失败或超时当成零占用。
- GREEN: 实际df -> 正式数据盘1106.31GiB、测试72.04GiB、备份24.38GiB可用；对应根分区36.05/6.89/2.34GiB。
- GREEN: Docker引用 -> 无完全无容器引用的卷，build cache均0；停止容器可写层不足0.1GiB/台，不作为大空间来源。
- GREEN: 备份旧Docker目录专项 -> 当前daemon data-root位于数据盘，全部当前GraphDriver无旧路径，fd/cwd及service无直接旧路径引用；旧根下确有业务数据/NAS子挂载。旧发布目录两个入口设备与inode一致，避免重复计数。旧overlay/image/buildkit约10.87GiB仍须核销唯一可写层；不整根删除。
- GREEN: 旧检查点 -> 各服10/28、10/29目标正式/测试/备份包有succeeded和business-opened回执，无直接容器挂载/fd/cwd引用；只是清理候选，独立恢复有效性及保留政策尚未验收，不执行删除。统计已同时纳入recovery.sql与recovery.sql.gz，未漏算未压缩数据库。
- GREEN: 保护边界 -> 测试当前恢复绑定、仍运行的rehearsal-prod配置与卷、备份运行MinIO数据127.35GiB、失败恢复证据、共享NAS均保留。
- BLOCKER: 前序发布任务 -> 发布空间与真实恢复证据尚未重新验收；本任务不推进完整包/前端补丁发布，也不将本次只读分析视为解除其阻塞。
- 原始/详细脱敏JSON和只读采集载体已在核对绝对源/目标范围、确认目标不存在后移至C:/SpugHandoff/release/private/acceptance/storage-audit-20261102/evidence；未覆盖旧证据。storage-facts.json登记详细证据SHA256。
- ready_for_closeout：报告及最小事实已形成；本任务没有worktree、运行控制台或远端状态变更需要清理，保留前序发布隔离目录。

- GREEN: closeout verification -> PASS：详细证据哈希与JSON可解析、候选回执/引用事实交叉检查、旧目录挂载别名核对、UTF-8无BOM/替换字符、凭据字段检查通过；本任务没有新增worktree或控制台需清理。
- completed：只读分析完成；按明确文件列表提交任务记录与独立请求日志条目，保留其他未提交改动，不推送、不操作前序发布。
