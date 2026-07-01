# 任务：维护仓发布链路支持 DCC 批量识别 5 worker

## 任务目标
- 维护仓发布链路写入 `DCC_PROJECT_CODE_RECOGNITION_WORKER_COUNT`。
- 测试服 compose 将 worker-count 传给后端 JVM 参数。
- 默认测试服并发数为 5，并允许环境变量覆盖。

## 里程碑
- [completed] 建立维护仓任务文档和门禁记录。
- [completed] 补维护仓发布脚本、compose 和合同测试。
- [completed] 运行维护仓定向测试并记录结果。

## 经验门禁
- PowerShell/UTF-8：已读取 IntRuoyi `docs/powershell-memory.md`，所有中文文档写入显式 UTF-8。
- 发布链路：已读取 IntRuoyi `docs/release-backup-restore.md` 与 `docs/server-access.md`；发布代码在维护仓修改，当前仅修改本机维护仓文件，不执行测试服发布/重启。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，通过发布链路正式配置项传递 worker-count。
- 是否存在临时补丁或绕过：否。

## 预期验证
- `python -m pytest scripts\tests\test_publish_dcc_codex_runtime_contract.py -q`

## 当前状态
- completed
