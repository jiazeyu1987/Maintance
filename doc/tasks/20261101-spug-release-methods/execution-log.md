# 执行记录

- 用户：当前Spug的发布有几种方式。
- 范围：仅本地代码、非敏感配置字段与进程身份只读核查；没有登录Spug、请求远端状态、构建或发布。
- GREEN: local-runtime-identity -> PASS；PID14328入口C:/SpugHandoff/release/source/ops/spug/release-center/intruoyi_executor.py。私密配置只输出applicationId=intruoyi、workflowVersion=direct-three-server-v1、productionRecovery=external，没有输出凭据或配置全文。
- GREEN: release-entry-review -> PASS；README.md直接三服策略、ui/app.js完整包流程、frontend_patch.py的ACTIONS和FrontendPatchMixin、intruoyi_executor.py最终继承、ui/frontend-patch.js页面均支持两种主要交付方式。
- 完整包：build-release/publish-test/mark-tested/promote-prod/accept-prod/promote-backup/accept-backup；一个固定包逐服升级，迁移仅按包内合约执行。
- 前端补丁：frontend-patch-build/deploy/accept；绑定baseReleaseTag，仅替换前端，保留原前端用于恢复，后端数据库保持。
- 说明：仅测试发布是完整流程的范围选择；重传NAS、既有包补发及恢复不是额外构建方式；演练为可选管理。已拉取Git代码与运行目录区分，不声称新Git版本已替换执行器。
- 核查中两次rg包含不存在文件名，明确文件未找到后改读真实intruoyi_executor.py及frontend_patch.py，不影响上述实际入口证据；未修改生产代码或执行器。
- 验证完成，无worktree、应用进程或运行配置变更。最终记录仅提交本任务文件。
