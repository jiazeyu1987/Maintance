# 阶段部署选择的使用合同

三个阶段使用不可变的独立文件：`automatic-full-deployment-selection.json`、`automatic-i1-deployment-selection.json`、`automatic-i2-deployment-selection.json`。本次仅准备helper，没有生成真实选择或运行UI/远端。由父任务在实际安装PASS后按对应报告的原字节生成wx选择文件。

```text
schemaVersion: AutomaticStageDeployment/v1
kind: FULL | I1 | I2
sourceConfigRef: intruoyi-57-safe-20261024-v1
sourceCommit: 该阶段实际source控制包40位提交
spugCommit: 0d445782dc06995b3c84b1b45146ea4b75483f92
sourceInstallationPin: {file,bytes,sha256} 相对TASK
sourcePrivateInstallationPin: {file,bytes,sha256} 相对PRIVATE，仅文件名/摘要无私密内容
sourceBuildPin: {file,bytes,sha256} 相对TASK，release-build-<source7>.json
spugInstallationPin: {file:automatic-spug-installation-0d44578.json,bytes,sha256}
```

FULL选择仅允许旧`automatic-control-installation-57.json`及PRIVATE同stem.private.json，完整commit为0d；文件均不改写。I1/I2必须明确新`AutomaticSourceControlUpgrade/v1`实际PASS，不能以旧报告缺schema推断新代次。

新source报告固定controllers[0]SOURCE/[1]MAIN_TARGET，public/private只差每项control。controllerGenerations逐项有role/sourceCommit/fileManifestSha256/fileCount/packageSha256/buildPin，MAIN_TARGET另installationPin旧57。loader核新source包和build、previousPid与前代source PID、policy/epoch与前代及保留目标一致、旧target控制行精确保留；Spug安装名单必须正好原11文件。

`automatic_stage_deployment.load_stage_deployment(task,private,kind)`是纯本机文件函数，返回selection/selectionPin/sourceCommit/spugCommit/sourceInstallation/privateSourceInstallation/sourceBuild/spugInstallation/controllerGenerations。privateSourceInstallation为内存规范化副本（附各控制代次），不回写原报告；调用方不能把它当成新私密安装回执。

原preflight调用仍为`prepare_automatic_ui_preflight.py --kind I1 --phase preview|submit|verify --observation <新名>`，会自动要求固定同kind选择存在。source输入按新sourceCommit闭合验证backup_engine/recovery/files.json精确映射；Spug只按原spugCommit闭合11个文件。两者HEAD/index/worktree任一改变均失败，允许其它不在此组件范围的独立已提交历史。

实际预检逐controller代次核PID/配置/engine/manifest/成员SHA，旧target0d不能误用新source manifest。Spug运行11文件逐SHA核验。来源真实健康、epoch、锁、容量和计划仍执行；控制GET可能写query audit，报告明确`businessMutationDispatched=false/controlApiQueriesPerformed=true/queryAuditWritesMayOccur=true`，不是笼统零服务器写入。

新gate为`AutomaticIncrementalUiPreflight/v2`：implementationCommit/installationCommit/buildCommit均表示source实际commit，另有spugCommit/deploymentSelectionPin，gitDeploymentInputs分source/spug。新I1/I2 UI提交回执为`AutomaticIncrementalUiSubmission/v2`并绑定同selectionPin/spugCommit。新观察附相同字段；真实UI最多一次POST、wx原回执、未知结果只GET原id的规则保持。

旧FULL submission/terminal/audit/sourceproof保持v1/0d原字节。历史FULL verify只在显式FULL选择指向0d时接受该v1；新预检实际PID仍必须匹配0d，因此应先完成FULL历史源恢复和verify，再升级source。不能为通过历史verify把FULL选择换成新代次。未知旧v1 kind/commit不兼容。

父任务后续acceptance选择v2由archive负责，逐kind引用对应deploymentSelectionPin。audit/source-restoration由epoch负责人按明确阶段消费，不由UI helper替代真实原件审计。source-only新build尚未实际安装时，I1/I2选定文件和新preflight均不得标PASS。
