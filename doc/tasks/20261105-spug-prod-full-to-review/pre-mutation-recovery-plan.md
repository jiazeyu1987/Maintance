# 写入前失败的受审计续恢复

## 已证实事实与方案
History356 原 worker exit1，mutationDispatched=false，未创建 replacement-intent/importer，恢复器已留下 PROVEN_NO_MUTATION 宿主预约释放回执。原五服务及其它全部业务的 PID、启动时间、配置摘要均保持，数据库 UUID 不变且885张表。控制服务实际软/硬句柄限制1024/4096，不能容纳当前 FULL 的全部归档路径租约。

先为本任务独占且空闲的 .59 控制服务持久配置 LimitNOFILE=65536，实测服务进程和子进程继承预算，不改变归档保护。此配置保留在 systemd drop-in，只重载该控制服务，不重启 Docker/主机或业务。历史失败证据逐字节保持。

现有准许机制仅支持已经写入并保持停写的失败，不能用于当前仍运行且未写入的情况。新增明确的写入前失败准许模式：核原失败/退出/请求/配置/替换失败/原预约及 PROVEN_NO_MUTATION 释放 pins、无原进程/intent/importer、原 native 记录均无 mutation、原目标严格身份/存储与所有原服务运行、预期885表；持原物理目标锁与宿主元数据锁，无当前宿主预约时只追加新的 v2 准许/观察/ready 回执。不得删除任何旧记录或停止业务来套用旧模式。下一次仅允许同一来源、备份点和目标的真实 Spug 新编号消费一次准许。

## BDD 与验证
- Given 明确写入前失败且原预约已有合格释放回执；When 运维显式准许同一FULL→同一原目标；Then 仅追加审计，原失败不变、业务不停，下一次真实UI操作可消费且不自动恢复。
- Given 缺少释放回执、发生过mutation/intent/importer、未知或活动进程、原pin漂移、存在其它预约、目标UUID/状态/表数变化；When 请求写入前准许；Then fail fast，无准许或删除。
- RED→GREEN 覆盖成功及各拒绝合同；原写入后失败准许、归档FD/路径保护、替换与宿主预约回归。Linux真实flock/文件系统测试在任务自有临时目录运行。
- 从已提交且验证通过的目标创建本次专属临时发布worktree构建SAFE组件，按pins安装新代次，只更新本任务控制绑定；保留旧引擎与原失败配置。验证新控制认证准入、包摘要及无关业务后正常Spug再提交。

## 第二次真实失败：MAIN 执行依赖合同
History357 仍在写入前exit1，缺失pin为旧演练 `/var/lib/docker/intruoyi-data/backup-restore-lab/test58-20261016/execution/native-entry/iptables`；当前原目标/885表/UUID/所有业务保持。MAIN 的 bound 路径使用严格登记资源归属，不执行演练隔离防火墙命令；SAFE初始化却无条件将演练iptablesPin加入执行依赖租约。修复实际封包初始化：MAIN只租约实际Docker执行文件，演练仍强制Docker+iptables。两种路径的全部归档/版本/输入文件租约与哈希保持；不在旧测试目录制造替身或禁用归档校验，不改目标合同摘要以破坏既有已消费准许。实际封包回归先RED验证MAIN缺演练文件也能建立完整归档租约、演练缺文件必须失败；保持真实MAIN身份/停写/存储等全部门禁。再次安装新精确提交代次，保留History356/357两个失败，针对357正式追加同点同目标写入前准许，然后真实Spug新编号一次确认。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否；两种明确且互斥的失败恢复合同，不能从写入后模式降为写入前模式。
- 是否从根因和长期维护角度解决：是；补齐持久资源预算和可复用的严格审计入口。
- 是否存在临时补丁或绕过：否；不删claim、不改失败、不新建stateRoot绕锁、不禁用归档保护。

## 经验门禁
- Trigger：主实例恢复在实际写入前失败但留有替换claim。
- Preflight check：原失败与退出pins、PROVEN_NO_MUTATION释放、无intent/importer/native mutation、空闲控制、无当前预约、原全部业务基线和严格目标身份；高风险写入前记录experience-preflight PASS。
- Blocker：上述任何事实缺失或漂移；不按猜测清锁或调用停写后的旧准许流程。
- Verification：RED/GREEN/REGRESSION、65536实测、失败原pins不变、追加准许与一次消费、实际Spug新编号完整终态及业务验收。
- Forbidden action：改失败状态、删claim/预约、重派同一编号、停止其它服务、修改NAS数据或降低归档核验。
- Evidence：archive-budget-diagnosis.json、执行记录、Linux测试及后续安装/准许/恢复回执。
