# 正式服发布起点接管

候选保持 2026-11-22-21-56-28，提交 02d5f081fa9bd93dfe1be9e7d98561155bde6175；测试服发布和基础页面冒烟已通过。

正式服预检 JOB-73a751fbaf：除 target-plan 外全部通过；唯一失败原因为实际 images 与本机登记基线不同。未执行正式部署。

2026-11-22T15:31:55.213491Z 只读观察：
- 实际版本 2026-11-22-12-43-39。
- backend UP、frontend HTTP 200、maintenance=false、read_only=false、super_read_only=false。
- backend image sha256:1ae2a01198ff98a536f613827b748519ed2bf745e19905f16b96e27d205bf8f0。
- frontend image sha256:597a86c384aa4266a8daad8515fe5e4a449a433aaf15e93fc3082c0bcbc5fbb2。
- 完整 schema/ledger/runtime 配置指纹在私有 prod-current-observation.private.json，不把当前观察冒充此前发布验收。

现有 target_registration.registration_targets 支持 payload.target=prod；执行器通过 Runtime.observe 与 validate_origin 后登记所选目标，不执行部署。UI page=8 只提供三服一起登记，没有目标选择。三服整体登记要求所有目标通过，不能为正式服接管强行改变已使用独立恢复的 .59 配置。

已向用户请求本次使用现有接口的明确例外：action=register-targets，applicationId=intruoyi，target=prod，唯一 requestId。不得直接修改 SQLite，不改历史失败记录，不改封包、SQL或镜像，不补造历史成功；确认到达前不提交该请求。

确认后：保存现有登记和观察摘要，通过现有认证入口提交一次所选目标登记；按原编号读取终态。登记成功后重新执行 check-prod，再 promote-prod。正式服健康、版本、迁移、真实页面及开放验收完成后再增量备份和 .59 恢复。
