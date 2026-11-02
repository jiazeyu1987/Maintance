# 当前发布载荷保留结论

- 完整发布：三服都上传并校验release.tar，解包后保留程序镜像、迁移脚本、manifest和执行回执；这不是把三服业务数据随程序包互相覆盖。
- 测试58、备份59：每轮完整升级采用checkpoint，保存升级前数据库快照、登记的Redis/MinIO数据卷归档、容器配置和恢复绑定，数据量随本服数据规模增长。
- 正式57：当前只读取releaseWorkflow中的非敏感策略字段，确认version=direct-three-server-v1、productionRecovery=external、externalRecoveryConfirmed=true。该模式不调用Spug全量capture，只记独立恢复责任与原始配置/发布证据；这不代表本任务实时验证了外部备份。
- 前端补丁：三服保留补丁release.tar、镜像和原前端容器/配置、部署回执；该路径不执行数据库命令，不生成整库或MinIO全量检查点。
- 清理：现有artifact_retention提供scan-artifacts/clean-artifacts独立流程，需成功扫描、选择可清理组及明确确认；保护当前版本、上一稳定版及未结束任务等。没有在正常发布成功后调用该清理流程。因此以后发布仍会重新增加占用，本次空间清理没有修改这项机制。

## 核对来源
- intruoyi_executor.py:594-601：目标恢复模式；640：上传包。
- intruoyi_runtime.py:548-595：精确staging与release.tar上传/校验。
- intruoyi_runtime_agent.py:832-842：external与capture分支。
- intruoyi_recovery_agent.py:221-255：升级前数据库/数据卷/容器检查点。
- frontend_patch.py:144-154及frontend_patch_agent.py:140-150：补丁包与原前端恢复资料。
- artifact_retention.py:submit/scan/execute：独立扫描、选择、确认后清理，没有发布后自动调用。

本任务仅核对本机实际执行器代码和允许的策略字段；不运行发布/备份/清理，不读取凭据，不访问服务器，不改策略。历史清理不能当作以后永久零积累的保证。
