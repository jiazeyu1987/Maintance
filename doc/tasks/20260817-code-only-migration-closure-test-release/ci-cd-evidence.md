# CI/CD Environment Evidence

## Target And Strategy

- Target: 仅测试服务器。
- Strategy: 新任务提交 -> 合回 `int_main` -> 新的干净临时发布 worktree -> 新 releaseTag -> `build-release` -> `publish-test` -> 真实运行态与页面验收。
- Forbidden: `mark-tested`、`promote-prod`、`promote-backup`。

## Commands, Files, Secrets, Artifacts, Approval, Rollback

待读取正式发布文档与完成预检后补充；秘密只记录引用和 owner，不记录值。

## RED / GREEN / Blockers

待执行。
