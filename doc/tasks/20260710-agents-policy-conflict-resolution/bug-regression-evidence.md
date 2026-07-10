# Bug Regression Evidence

## Bug Summary

规则体系存在两个可复现的收尾缺陷：

1. 发布任务要求 worktree 删除后才能 `completed`，但 task-closeout apply 只接受 `completed`，形成循环依赖。
2. 独立验证默认生成 `verification-report.md`，task-closeout 默认把它归入删除集。

## Expected Behavior

- `ready_for_closeout` 表示实现和验证完成、等待清理；该状态允许 task-closeout apply。
- `in_progress`、`blocked`、`unknown` 必须阻塞 apply。
- `verification-report.md` 必须默认进入 keep。
- cleanup、合并和 worktree 删除验证通过后，任务才更新为 `completed`。

## Reproduction

```powershell
Set-Location C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts
python -X utf8 -m unittest test_task_closeout.py -v
```

## Root Cause

- `extract_status()` 只识别 `completed`、`blocked` 和带空格的 `in progress`，不识别项目实际使用的 `in_progress` 或新状态 `ready_for_closeout`。
- apply 门禁硬编码为 `task_status != "completed"`。
- 默认核心保留文件仅包含 `task.md` 和 `execution-log.md`。

## Regression Test

新增 `scripts/test_task_closeout.py`，覆盖：

- `ready_for_closeout` 允许 apply 且保留验证报告。
- `in_progress` 仍阻塞 apply。
- `completed` 继续兼容。

## RED

RED: `python -X utf8 -m unittest test_task_closeout.py -v` -> FAIL，预期原因是脚本不识别 `ready_for_closeout` / `in_progress` 且未默认保留验证报告。

`python -X utf8 -m unittest test_task_closeout.py -v` -> FAIL：

- `ready_for_closeout` 实际被识别为 `unknown`。
- `in_progress` 实际被识别为 `unknown`。

首次从 D 盘向 unittest 传入 C 盘绝对测试路径时发生跨盘 `relpath` 失败；改在测试目录运行后，又发现动态导入模块未注册到 `sys.modules`。修正测试承载方式后取得上述预期 RED。

## GREEN

GREEN: `python -X utf8 -m unittest test_task_closeout.py -v` -> PASS，3/3；skill quick validation 与真实 CLI 前向测试同时通过。

`python -X utf8 -m unittest test_task_closeout.py -v` -> PASS，3/3。

`python -X utf8 ...\quick_validate.py ...\task-closeout-cleanup` -> PASS。

真实 CLI 临时目录前向测试：

- `ready_for_closeout` apply 返回 0，临时文件删除，`verification-report.md` 保留。
- `in_progress` apply 返回 2，临时文件未删除。

## Risk And Regression Scope

- 保留对旧 `completed` 任务的兼容。
- 新状态只放宽到 `ready_for_closeout`，不会允许 `in_progress`、`blocked` 或 `unknown` 清理。
- 默认额外保留一个固定文件名 `verification-report.md`，不会扩大到任意 evidence 文件。

Verification: 单元测试、skill quick validation、真实 CLI 临时目录前向测试、旧冲突文本扫描、UTF-8 严格解码和两个 Git 仓库的 `git diff --check` 均通过。

## Blockers

无。
