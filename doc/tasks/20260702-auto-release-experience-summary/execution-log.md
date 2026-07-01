GREEN: experience-preflight -> PASS，已读取 docs/experience-index.md、docs/release-build-preflight-lessons.md、docs/release-agent-checklist.md 与 ci-cd-environment-delivery 技能说明；本任务只修改本机维护仓代码和文档，不执行真实服务器发布。
BDD: 发布 operation 完成后自动生成经验候选 -> Given build-release/publish-test operation 结束 When operation 状态更新为 SUCCESS 或 FAILED Then 运行控制台写入 release-experience-candidates.md，包含 action、environment、releaseTag、status、summary 和前置经验建议。
BDD: 非发布 operation 不生成候选 -> Given restart 等非发布动作结束 When operation 状态更新 Then 不写入发布经验候选。
RED: `mvn -f backend\pom.xml "-Dtest=RuntimeControlOriginalParityTest#completedReleaseOperationsWriteExperienceCandidateNotes,RuntimeControlOriginalParityTest#nonReleaseOperationsDoNotWriteExperienceCandidateNotes" test` -> FAIL，预期原因：发布 operation 完成后尚未生成 `release-experience-candidates.md`。
GREEN: `mvn -f backend\pom.xml "-Dtest=RuntimeControlOriginalParityTest#completedReleaseOperationsWriteExperienceCandidateNotes,RuntimeControlOriginalParityTest#nonReleaseOperationsDoNotWriteExperienceCandidateNotes" test` -> PASS，发布 operation 自动写入经验候选，非发布 operation 不写入。
GREEN: release-experience-candidate-fail-fast -> PASS，候选文件写入失败时，operation 状态会被明确标记为 FAILED 并抛出错误，不静默跳过经验沉淀。
