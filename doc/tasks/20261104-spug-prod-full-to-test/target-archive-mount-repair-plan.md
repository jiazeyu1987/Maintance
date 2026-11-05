# 测试服原归档只读挂载恢复

2026-11-05 14:31 北京时间。沿用用户对 `post-boot-repair-plan.md` 的原 NAS 挂载恢复授权。

## 已证实的根因
首次恢复 `smallapp-ba0bca490ac243768c8b759fa14a8bbd` 在 admission 报 `ARCHIVE_ROOT_UNAVAILABLE`；ledger 仅有 request/intent/selection/admission-error，没有 worker、completion 或 replacement claim。五个原容器 PID、StartedAt 均与恢复前一致。

历史 .58 mountinfo 证明 `/var/lib/docker/intruoyi-data/prod57-spug-rehearsal-20261021/nas` 原为共享 `//172.30.30.4/IT共享` 的只读挂载，目前是空目录。现有 fstab 管理的 `/mnt/intruoyi-backup-nas` 已自动挂载同一共享，其新 FULL point 原始字节 SHA256 与正式服验证值一致。`/mnt/nas` 下有本地目录，本次不覆盖、不删除、不改动。

## 正式处理与验证
1. 重验原目标为空、无 symlink、无现有挂载，现有共享来源正确且新 FULL point 摘要相符。
2. 新增专属 systemd mount 单元，把现有 NAS 共享根目录只读 bind 到原归档路径；依赖现有 NAS mount 单元。设置 enable。控制服务增加 RequiresMountsFor 依赖；仅 daemon-reload，不重启业务或当前控制服务。
3. 核 CIFS 来源、mountRoot=/、目标 ro、unit active/enabled；通过已安装的只读 archive resolver 核完整元数据 pins 和同一新 FULL 选择绑定。
4. 保留首次失败恢复所有原始记录。通过 Spug 正常界面创建下一次恢复操作，不复用失败 operationId，不直接调用恢复 API，不伪造成功。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。任何来源、路径、摘要不符立即失败。
- 是否从根因和长期维护角度解决：是。恢复原 canonical 路径并补齐持久 mount 及控制服务依赖。
- 是否存在临时补丁或绕过：否。原 archive/point/source pins 不变；不修改历史或业务数据。

## 经验门禁
- Trigger：重启后恢复 admission 缺原归档目录。
- Preflight check：核历史 mountinfo、现有 fstab 共享来源、目标空目录、真实新 point 摘要、失败操作无执行、业务 PID 未变化。
- Blocker：未知本地文件、路径链接、共享或 point 不匹配、已有恢复进程。
- Verification：ro mount 与持久单元、installed resolver 精确 pins、实际 Spug 新操作及最终恢复验证。
- Forbidden action：覆盖本地未知文件、改写 NAS/凭据/历史、替换旧包、直接 API 启动恢复。
- Evidence：target-nas-diagnosis.json、restore-terminal-record.json、私密历史 mountinfo、target-original-nas-confirmed.private.json。
