# 分阶段提交任务记录

本helper仅管理已经审阅、已验证记录的精确提交，不执行验收、服务器操作、融合、stash或清理。当前任务仍在运行，不能用它把状态提前改成ready_for_closeout或completed。默认prepare不产生Git写入；下面命令示例均未实际执行。

## acceptance阶段

须先完成真实自动FULL→I1→I2审计、独立源恢复证明、当前三服安装及稳定控制验证，任务首个`## Current Status`为`ready_for_closeout`。helper复用`closeout_contracts.automatic_chain/current_installations`及`stable-controls-closeout.json`检查真实验收；这一步不要求构建清理或主线融合。

运行副本必须位于`codex/spug-selectable-restore-targets-20261104`。HEAD由调用者显式给出完整40位SHA，可为当前b5或之后独立提交，不能沿用旧packaged-frontend安装提交。

先人工审查具体文件，然后创建本TASK内新selection JSON：

```json
{
  "schemaVersion": "TaskRecordSelection/v1",
  "mode": "acceptance",
  "expectedHead": "调用时实际完整40位提交",
  "files": [
    {
      "path": "doc/tasks/20261106-spug-prod-incremental-to-two-targets/task.md",
      "bytes": 123,
      "sha256": "实际文件64位小写SHA256"
    }
  ]
}
```

示例bytes/SHA只表示字段，不能作为真实清单。每个文件需按实际字节计算pin。必须包含任务状态文件；共享文档只允许显式列出`docs/request-command-log.md`、`docs/experience-index.md`、`docs/release-agent-checklist.md`和本轮命中的`docs/powershell-preflight-lessons.md`，不会自动全部纳入。42项旧Nov4资产、PRIVATE原文、目录跳转、符号链接、重复路径直接拒绝。PNG还须逐张审查无凭据并在该项写`binaryCredentialsReviewed: true`，helper只核格式，不声称能代替图片内容审查。

selection本身不能纳入自身清单；新回执也不能纳入本轮清单，避免自引用pin。清单、回执可由后续明确记录提交收录，无需改写既有证明。

```powershell
$recordsTask = 'C:/Users/D01021/.codex/worktrees/spug-restore-targets/Maintance/doc/tasks/20261106-spug-prod-incremental-to-two-targets'
& 'C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -X utf8 -B "$recordsTask/commit_records.py" --mode acceptance --expected-head <实际40位HEAD> --selection "$recordsTask/records-selection-acceptance-1.json" --receipt "$recordsTask/records-prepare-acceptance-1.json"
```

实际准备成功后，父任务审阅`PREPARED`回执及pins；决定提交时用同一清单、同一HEAD、**另一个新的receipt名称**加`--execute`。它会重新执行全部检查，再精确暂存选定的已改变文件，分批每次最多30路径以适配Windows长度限制。不会把其它TASK新记录或并行修改顺手加入。

成功execute另外独占创建`<receipt去掉.json>-commit.json`，记录真实commit、所提交路径与准备回执pin。准备回执保持原`PREPARED/gitWritesPerformed=false`，表示写入前观察，不能当最终提交证明。真正提交结果只认新commit回执与实际Git历史。

## final阶段

只能在已融合后的`int_main`副本运行。TASK/ROOT从该脚本实际位置计算。原helper曾要求删除长期开发checkout，这是helper过严，AGENTS明确要求清理的是本任务临时发布worktree；现保留开发checkout和42项旧资产，不因其存在阻止final。

任务文档须为`completed`，且在写该状态前已经取得真实融合、回归、稳定控制和清理依据。`--finalization`为本TASK独立证明：

```text
schemaVersion: TaskRecordsFinalization/v2
status: PASS
mainHead: 最终记录提交前、当前int_main完整HEAD
taskHead: 已合入int_main的实际任务记录提交
taskWorktree: integration-readonly-scope.json记录的原任务工作区
taskWorktreeDisposition: retained_with_preexisting_assets
taskWorktreeHead: 保留checkout的实际完整HEAD，须已是当前main祖先
retainedAssetsPin: {file: integration-pending-scope.json, bytes, sha256}
mergeVerificationPin: {file, bytes, sha256}
closeoutPin: {file: closeout-verification.json, bytes, sha256}
cleanupPin: {file: owned-build-cleanup.json, bytes, sha256}
stableControlsPin: {file: stable-controls-closeout.json, bytes, sha256}
```

`mergeVerificationPin`指向本TASK独立真实融合验证JSON，必须含`status=PASS`、相同`mainHead/taskHead`及`mergeVerified/targetedRegressionPassed/parallelChangesPreserved=true`。这些事实须由真正融合后验证产生，不能手写布尔值代替验证。helper另用真实Git确认taskHead是当前HEAD祖先。

closeout/cleanup/stable报告须是现有完整收尾链的真实PASS并与pins一致；所有明确登记临时发布构建代次与targetCommit/package/report pins都须吻合，当前清单中11个build worktree物理目录和Git登记均消失。

开发checkout须按上述disposition保留在原路径及Git登记中，实际HEAD已在main历史内。42项既有资产逐项核原路径/bytes/SHA，不改写其归属、不删除。其本TASK及明确shared docs的dirty路径，须已与main HEAD的Git内容相同，或实际字节与本次final显式清单相同；后者将由本次final提交承接。其它待融合任务改动仍失败，不要求清空无关dirty，不新增自引用pin。

final使用`--mode final --expected-head <当前int_main HEAD> --selection <mode=final的新清单> --finalization <真实最终证明> --receipt <新名称>`，先不带execute准备，审阅后另名execute。final证明记录的是提交前HEAD，不引用未来最终记录commit，避免不可能满足的自引用条件。

## 失败与保留

HEAD、分支、空index、pins或非选定文件漂移均失败。已有回执拒绝覆盖。Git写入前失败不暂存；若明确execute后在暂存或commit阶段失败，保留实际index供父任务审阅，**不自动reset、不重试commit、不写成功回执**。无论模式都不改变task.md内容或status，不处理主线dirty交集审批，不能代替integration-closeout-plan中的私密日志处置。

选定文件完整核SHA；非选定路径只核Git改动路径集合及lstat身份、大小和时间，不读取无关私密内容或大文件。回执明确标为identity保护，不声称完成其它任务文件的字节审计。最终融合阶段的两边字节保全由独立融合验证承担。
