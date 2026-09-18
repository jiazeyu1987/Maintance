# 已测试发布包一键发布正式服 PRD

## Purpose and Scope

本产品能力面向 IntRuoyi 运行控制台，新增一个独立、明确的“发布到正式服务器”按钮。按钮只负责把**已经在测试服务器成功部署并完成测试验收**的同一不可变程序包晋级到正式服务器，不重新构建、不生成新 `releaseTag`、不携带或替换业务数据。

首版范围止于正式服务器发布和验收。审查服务器仍使用独立动作，不由本按钮自动触发。

## Evidence Reviewed

- R92、R93 已连续完成 `build-release -> publish-test`、测试服运行态核验和真实登录验证。
- 当前候选实现已有 `TESTED -> PROD_PREVIEW -> PROMOTING_PROD -> COMPLETED` 状态、一次性生产授权、`PROD` 确认和 `promote-prod` 脚本能力。
- 当前候选前端已有“晋级正式服”入口，但位于尚未合入 `int_main` 的 R93 分支，不能视为已交付。
- `docs/release-agent-checklist.md` 规定正式服发布必须复用同一 `releaseTag`，并核对 operation、manifest、远端 `.env`、实际镜像、后端健康和前端 HTTP。
- `E:\IntRuoyi\docs\server-access.md` 固定正式服务器为 `172.30.30.57`，正式写入必须显式确认 `PROD`，目标参数必须来自受控配置。
- `ops/deploy/publish-int-ruoyi.ps1` 已要求生产级部署提供测试 operation 证据、tested 证明和生产 dry-run 证据。

## Product Summary

操作者从“标准程序发布”区域选择一个发布工作流。只有工作流处于 `TESTED`、包摘要和测试证据有效、正式服只读预检通过、没有活动生产发布或恢复隔离、操作者具备专用权限时，“发布到正式服务器”按钮才可确认执行。

点击按钮后，系统先展示服务端生成的正式发布预检结果。操作者核对目标、版本、摘要、测试证据、变更和恢复准备情况，填写发布原因并精确输入 `PROD`。服务端签发短时、一次性、与工作流及摘要绑定的授权，再创建唯一生产发布 operation。页面持续显示结构化阶段、耗时、最后进展和阻断原因，最终按真实运行态证据判定成功或进入恢复态。

## Target Users

- 发布操作者：具有 `infra:runtime-control:promote-prod` 权限，负责预检、确认和监控正式发布。
- 发布观察者：具有 `infra:runtime-control:query` 权限，只能查看状态、证据和结果。
- 恢复负责人：在发布进入 `RECOVERY_REQUIRED` 后按独立恢复流程检查和处置；首版不在本按钮中自动回滚业务数据。

## First Version Scope

1. 在标准程序发布区域提供独立按钮，名称固定为“发布到正式服务器”。
2. 候选来源固定为服务端发布工作流；客户端不得提交任意包路径、主机、脚本或环境参数。
3. 只有 `TESTED` 工作流可申请正式发布预检。
4. 展示同一 `releaseTag`、package digest、manifest digest、源码提交、测试 operation、验收人、验收时间、验收结论和正式服当前版本。
5. 执行服务端只读正式服预检，输出逐项检查和结构化 blockers。
6. 采用精确 `PROD` 文本确认、短时一次性授权、状态版本校验和幂等键。
7. 复用 NAS 上已测试的不可变包，不运行 `build-release`。
8. 在首次正式服写入前取得统一生产环境锁，并保持到最终验收完成。
9. 成功、确认零写入失败、部分/未知写入失败使用不同状态和处理规则。
10. 记录可审计证据并对成功、失败或恢复阻塞各通知一次。

## Non-Goals

- 不把“构建发布包”“发布测试服”“标记测试通过”和“发布正式服”合并成一个无确认的按钮。
- 不自动发布审查服务器，不自动执行 `promote-backup`。
- 不允许选择未测试包、直接输入 `releaseTag` 绕过工作流或修改发布包。
- 不自动回滚业务数据，不通过覆盖迁移台账制造一致。
- 不在首版引入双人审批；若未来需要四眼原则，应作为独立产品变更。
- 不在本设计任务中访问、预检或写入任何远端服务器。

## Functional Requirements

### FR-PROD-001 候选资格

系统必须只允许状态为 `TESTED` 的工作流进入正式发布预检。工作流必须绑定非空且合法的 `releaseTag`、package digest、manifest digest、测试 operation ID 和测试 operation 证据路径。

### FR-PROD-002 不可变包绑定

正式发布必须复用测试服验证过的同一包。服务端必须重新计算或从可信清单验证 package/manifest digest，并与工作流、tested 证明和一次性授权逐项一致。任一不一致必须在生产写入前阻断。

### FR-PROD-003 独立按钮与资格说明

按钮应始终位于标准程序发布区域。不可用时保持可见并显示具体原因；不得仅通过隐藏按钮表达权限或状态不足。

### FR-PROD-004 只读预检

点击按钮首先创建只读 eligibility preview。预检至少覆盖：权限、工作流状态、摘要、测试证据、授权配置、正式服固定目标、SSH/密钥引用存在性、NAS 包可读性、活动 operation/环境锁、远端运行目录、数据盘与挂载、容量、当前 releaseTag、迁移依赖和 checksum、数据质量前置、恢复准备与生产写开关。

### FR-PROD-005 确认对话框

只有 eligibility preview 全部通过时才允许最终确认。对话框必须显示正式服务器、目标 releaseTag、当前正式版本、package/manifest digest、测试验收摘要、预计动作、恢复准备和不可自动回滚提示，并要求填写原因和精确输入 `PROD`。

### FR-PROD-006 一次性授权

服务端必须签发有效期不超过 15 分钟、只能消费一次的授权。授权绑定 workflow ID、releaseTag、package digest、manifest digest、preview ID、目标环境、preset、权限范围和服务端认证用户。过期、撤销、已消费或绑定不一致时拒绝执行。

### FR-PROD-007 幂等与并发

同一工作流/正式环境只能有一个活动发布。重复点击、网络重试或并发用户不得创建第二个生产写 operation；系统应返回现有 operation 或明确冲突。

### FR-PROD-008 受控执行

服务端根据受控配置解析正式服务器及路径，调用现有 `promote-prod`/`deploy-release -Environment prod` 能力。客户端字段白名单之外的 `releaseTag`、targetEnvironment、host、path、script、test evidence 等字段必须被拒绝。

### FR-PROD-009 结构化进度

页面必须显示当前步骤、步骤持续时间、最后结构化进展时间和阻断原因。日志仅用于诊断，不得以日志文件修改时间代替 workflow/operation 状态。

### FR-PROD-010 成功判定

只有下列证据全部一致时状态才可变为 `COMPLETED`：production operation=`SUCCESS`、manifest/digest 匹配、正式服 `.env IMAGE_TAG=<releaseTag>`、backend/frontend 实际镜像 tag 一致、容器处于预期状态、backend health=`UP`、frontend HTTP=`200`、页面 `/release-info.json` 或等价页面证据显示同一版本、生产环境锁终态正确。

### FR-PROD-011 失败分类

- 在未取得生产锁、未消费授权且能证明零写入时：工作流保持 `TESTED`，允许修复前置条件后重新预检。
- 已消费授权、已派发 operation、已取得生产锁或无法证明零写入时：工作流进入 `RECOVERY_REQUIRED`，保持生产隔离，禁止再次发布。
- 恢复完成前不得显示“发布失败，可直接重试”或自动释放锁。

### FR-PROD-012 审计与通知

记录 requestedBy、authorizedBy、releaseTag、摘要、preview、operation、目标环境、阶段事件、最终证据和时间戳；不记录密码、token、私钥、连接串或完整秘密环境变量。成功、失败和恢复阻塞分别只通知一次。

## Business Rules

1. 正式发布链严格为同一 `releaseTag` 的 `build-release -> publish-test -> mark-tested -> promote-prod`。
2. 测试服仅部署成功不等于 `TESTED`；必须有显式 PASS 验收和可信服务端操作者身份。
3. `releaseTag`、摘要、测试证据和 preset 组成正式晋级身份，任何字段改变都需要新工作流和新发布包。
4. `productionWriteEnabled=false` 时预检可以展示阻断，但不得创建生产写 operation。
5. 正式目标固定由服务端配置确定；首版显示为正式服务器 `172.30.30.57`，客户端不可覆盖。
6. 操作者必须具备专用 `infra:runtime-control:promote-prod` 权限；通用 `operate` 权限不足以单独授权正式发布。
7. 正式发布不自动触发审查服发布、备份、数据恢复或业务数据回滚。
8. required SQL、schema/migration 仍是程序包发布的一部分；“不含数据”不表示跳过数据库结构和 required SQL。
9. 失败 `releaseTag` 不得通过改包、改 tested 状态或改台账继续晋级。
10. 所有页面错误必须展示服务端真实错误码和安全可公开的下一步建议，不得静默吞错。

## States and Transitions

| 当前状态 | 事件 | 条件 | 下一状态 |
|---|---|---|---|
| `TEST_DEPLOYED` | 提交 PASS 验收 | 测试 operation 和真实验收证据有效 | `TESTED` |
| `TESTED` | 只读正式预检失败 | 零写入 | 保持 `TESTED`，返回 blockers |
| `TESTED` | 只读正式预检通过 | 生成短时 preview | 保持 `TESTED` |
| `TESTED` | 授权与最终再校验通过 | 取得生产租约、消费一次性授权 | `PROD_PREVIEW` |
| `PROD_PREVIEW` | 派发正式发布 | operation 绑定成功 | `PROMOTING_PROD` |
| `PROMOTING_PROD` | 全部最终证据通过 | 同一 releaseTag 全项一致 | `COMPLETED` |
| `PROD_PREVIEW`/`PROMOTING_PROD` | 已写入或写入不明失败 | 不能证明零写入 | `RECOVERY_REQUIRED` |
| `TESTED` | 授权/确认/租约获取前失败 | 明确零写入 | 保持 `TESTED` |
| `RECOVERY_REQUIRED` | 恢复验收通过 | 独立恢复流程确认 | 由恢复设计决定，首版按钮不可直接推进 |

## Edge Cases

- 页面展示 `TESTED` 后包被替换或 manifest 摘要变化：最终再校验阻断。
- preview 通过后正式服状态被其它操作改变：preview 过期或状态指纹不匹配，重新预检。
- 操作者双击或浏览器重发：幂等返回同一 operation。
- 一次性授权签发后未执行：到期自动失效，不产生写入。
- 服务端重启发生在授权消费后或 operation 派发后：从持久化 workflow/operation/远端锁恢复，进入监控或 `RECOVERY_REQUIRED`，不得创建新 operation。
- 发布脚本退出成功但镜像/health/HTTP 不一致：判定失败并进入恢复态。
- 正式服已运行同一 releaseTag：只有全部证据一致才可返回“已是目标版本”的幂等成功；任一不一致必须阻断，不能跳过验证。
- 审查服不可用：不影响正式服按钮，因为首版不自动发布审查服。
- 页面断线：后台 operation 继续由服务端管理；重新打开页面按 operation ID 恢复进度。

## Acceptance Criteria

- AC-PROD-001：非 `TESTED` 工作流按钮不可执行且显示精确原因。
- AC-PROD-002：正式发布请求不允许客户端传 host、path、targetEnvironment 或另一个 releaseTag。
- AC-PROD-003：preview 任一 blocker 导致零生产写入且工作流保持 `TESTED`。
- AC-PROD-004：错误/过期/已消费授权或错误 `PROD` 文本均不能创建 operation。
- AC-PROD-005：相同请求重复提交只有一个 production operation。
- AC-PROD-006：执行日志证明没有发生 `build-release`，包摘要与测试时完全一致。
- AC-PROD-007：部分写入或派发结果未知时为 `RECOVERY_REQUIRED` 且生产环境锁仍保持。
- AC-PROD-008：只有九项正式服最终证据一致才显示成功。
- AC-PROD-009：正式发布成功后审查服 releaseTag 和 operation 历史无变化。
- AC-PROD-010：真实浏览器路径从运行控制台点击按钮完成，接口只用于最终证据核验。

## Open Questions

- 首版是否要求“测试验收人”和“正式发布人”必须为不同账号？当前需求未要求双人审批，本文默认允许同一有权用户完成，但保留完整审计。
- 正式发布通知渠道除站内信外是否还需企业微信或邮件？首版只要求现有通知机制且每种终态一次。

## Product Blockers

- 前序 R93 候选实现尚未安全融合到应用和维护仓 `int_main`，实现任务开始前必须先确定基线/合并策略。
- 当前所有工作流写端点共用 `infra:runtime-control:operate`；正式发布专用权限尚未实现和迁移。
- 当前 UI 在一个前端函数中先签发授权再直接执行，缺少用户可审查的结构化 production preview 和 preview 快照绑定。
- 未经后续任务明确授权，不得通过真实正式服操作完成 AC-PROD-010；设计完成不等于生产按钮已验收。
