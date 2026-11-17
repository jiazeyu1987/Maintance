用户：收敛三项。当前只开展本机代码修复；部署范围另按实际授权核对。

GREEN: experience-preflight -> PASS。独立任务worktree，正式入口接入，保护主线无关改动，不操作服务器。重构按AGENTS由分项子agent实现，父agent审查及集成。

BDD/RED/GREEN详细证据见本目录各分项日志。本机PATH Python为占位启动器，改用已有bundled Python。在线隔离依赖安装因TLS失败即停止，随后复用既有离线wheel；未绕过TLS或安装服务器组件。

REGRESSION: Linux离线python:3.12-bookworm，实际源码只读挂载，pytest scripts/tests/test_backup_variants.py -q -> 37 PASS（15.53秒）。Windows同组有NATIVE_LINUX_REQUIRED失败，未跳过冒充通过，以真实Linux完整运行替代。
REGRESSION: pytest test_integration_worktree_cleanup.py test_build_worktree_cleanup.py test_recovery_version_copies.py test_recovery_program_source.py test_recovery_archive_versions.py -> 90 PASS（64.65秒）。
REGRESSION: unittest discover -s ops/spug -p test_prepare*.py -> 55 PASS；discover -s ops/backup_engine -p test_chain_single_load.py -> 3 PASS。
REGRESSION: unittest test_direct_release -> 19 PASS；test_source_binding_entry -> 5 PASS。

审查：版本副本不改冻结身份，父策略清理前解析；去重仅单次chain去除规划用完整load，保留后续独立完整校验；来源切换不在维护态deploy冻结容器身份，持锁preflight本身不二次取锁。生产assert已改显式错误；固定systemd覆盖文件支持多代及回退版本；.env保留属主和权限。

当前主线从基线新增ca1801f（其它任务的流程核对文档），本任务生产路径无重叠脏改动。docs/request-command-log.md有并发未提交记录，收尾仅追加并精确暂存本任务段落，不提交他人内容。

GREEN: .env随机同目录临时文件与finally只清本次文件；原固定临时文件残留不再阻止重试。来源模块Windows 6 PASS，连同入口/普通发布30 PASS；Linux -O真实临时文件/flock/proc边界14 PASS，见source-sync-log.md。git diff --check PASS。
GREEN: experience-preflight -> PASS（融合/清理）。仅合并本任务已验证提交；主线并发修改保留；清理使用明确本任务路径、已融合提交与外置归属回执；删除后记录最终状态。
