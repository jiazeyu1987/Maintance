# 备份服恢复 MVP 最终收尾

## Current Status
completed

## 融合与验证

- 主线int_main由25fe7edc47ee1cba9a4b85bcdc892d7819ea107e以ff-only融合至fd0b45d32f15bf0ddbc0287422d3b75a8d34b32f；只迁入任务最终增量，没有整合旧integration部署基线。
- request-command-log单文件原字节及binary patch持久保存，先对最终结果副本git apply --check，后精确恢复该文件、ff-only、应用原补丁。1699项原状态集合与原暂存内容未变；该脏日志未进入本次最终记录提交。
- GREEN: 融合后50个任务文件与已测试提交一致；标准生成154模块，runtime/data编译通过，三个验收runner的node --check通过。既有定向测试及真实FULL/增量验收均PASS，没有重复大矩阵。
- FULL与FULL+I1+I2均Spug SUCCEEDED；各11表计数、真实登录/用户页及3附件字节/SHA通过。I1/I2附件变化为零，仅证明附件保留，不声称非空附件变化已验收；全库逐行等价未执行。

## 清理执行记录

执行：从int_main工作目录运行私密closeout_worktrees.py，对下列每项核路径归属、Git登记、精确HEAD与clean，再逐项git worktree remove（无force），核目录及登记不存在。13个发布工作区没有产生新提交；final-integration产生的任务提交已经融合并验证。构建及各阶段验证命令见local-install-preparation.md、final-integration.md与execution-log.md。

| 工作区绝对路径 | 固定目标提交 | 新提交 | 已融合 | 删除结果 |
| --- | --- | --- | --- | --- |
| C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-worktree | 5aeaaf10fd4793081a6871743361ae043dce319e | 无 | 无新提交；最终实现已融合 | exit0，目录/登记不存在 |
| C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v2 | 44cc4bbcdcd0a02e502e8a9e13ccd5a1a4841348 | 无 | 无新提交；最终实现已融合 | exit0，目录/登记不存在 |
| C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v3 | 1bea1496770abf6813fab2afb8fe9dfd6bc38608 | 无 | 无新提交；最终实现已融合 | exit0，目录/登记不存在 |
| C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v4 | f2cff77bf13492de9ede64f60001a02e054190c2 | 无 | 无新提交；最终实现已融合 | exit0，目录/登记不存在 |
| C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v5 | 8beac1a8529daf426bfbfa3663a7898a40eff091 | 无 | 无新提交；最终实现已融合 | exit0，目录/登记不存在 |
| C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v6 | 780a6ee2362aad254452c07197ee082a17ac2d2f | 无 | 无新提交；最终实现已融合 | exit0，目录/登记不存在 |
| C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v7 | 73dfd22ecac09f3ffda9da7070102fdf0676febd | 无 | 无新提交；最终实现已融合 | exit0，目录/登记不存在 |
| C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v8 | f3eb4b5271b56a4d119e22066070f7f5ca8d5cf5 | 无 | 无新提交；最终实现已融合 | exit0，目录/登记不存在 |
| C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v9 | f6ffee15b9f7a2a27b127c72bb7e1700dad1008c | 无 | 无新提交；最终实现已融合 | exit0，目录/登记不存在 |
| C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v10 | 393be43f8e6c7ae5b7413b0fbe3754917110aae2 | 无 | 无新提交；最终实现已融合 | exit0，目录/登记不存在 |
| C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v11 | 3dca5a9ced5ec26e1d973b84661a2c8d5d66d5d6 | 无 | 无新提交；最终实现已融合 | exit0，目录/登记不存在 |
| C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v12 | 31a670f883054a0cf09c4241a781327f117af46e | 无 | 无新提交；最终实现已融合 | exit0，目录/登记不存在 |
| C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/release-v13 | c4fa257d207c83c0179eaae83fa889b1861663b9 | 无 | 无新提交；最终实现已融合 | exit0，目录/登记不存在 |
| C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/final-integration | fd0b45d32f15bf0ddbc0287422d3b75a8d34b32f | 有 | 是 | exit0，目录/登记不存在 |

## 保留与运行态

- 原integration-worktree及其分支保留：部署基线携带其它历史，未作为整支融合输入；本任务最终能力已通过精确路径迁移及测试合入主线，不因保留历史工作区而宣称有未融合任务实现。
- 父managed工作区保留，受Codex应用保护，非本次临时发布执行环境；没有绕过保护删除。其他并发工作区、进程、无关文件及原暂存内容不动。
- 父已精确停止自有SSH PID32632，18089无监听；验收浏览器关闭，无release/final-integration进程消费者。Spug及.59已恢复服务保留。无新远端写入、无推送。
- 私密安装载体、原证据与dirty保护备份保留在本任务私密目录；不提交凭据。
