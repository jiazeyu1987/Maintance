# 全量恢复八表行数只读验收载体

## Current Status
ready_for_closeout

## 目标、里程碑与预期验证
独立脚本读取全量或 I2 私密基线的 11 表 count，与固定 .59 上显式指定 READY 新目标的 MySQL 比较。凭据仅从容器内部已有文件读取，不打印；SQL 仅 SELECT。脚本在恢复成功后由父任务执行，本子任务不提前验收、不改产品。

## 经验门禁
- v9 恢复准入修复已部署，真实全量任务已受理且 worker 活跃；本子任务只准备本地验收载体，不操作该 worker/容器/数据库。
- 真实目标固定 .59 与本次 newRef；基线来自父任务已采私密文件，不用模拟数据替代远端验收。
- 不打印凭据、原始环境或私密配置，命令只有读取；UTF-8 显式处理。
- BDD/RED/GREEN 仅证明载体比较及命令边界，不能称为真实恢复验收通过。父任务统一记录共享命令日志。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否；缺基线或查询失败立即失败。
- 是否从根因和长期维护角度解决：是；独立核对固定恢复点数据的可观察行数，不增加产品检查。
- 是否存在临时补丁或绕过：否；仅授权验收载体，无产品修改或写库操作。

## BDD
- Given 已冻结的 8 表行数与恢复后同一目标，When 执行只读核对，Then 逐表输出期望/实际行数并仅在全部相等时成功；查询错误、表缺失或数量不符返回失败。
- 父任务追加：Given 下一轮 READY 会产生新的 target，When 调用验收 helper，Then 必须显式传 --target 且匹配 spug-empty59-[a-f0-9]{12}；不推断、不默认旧目标，主机固定 .59，远端容器名称仍精确匹配。

## 验证与命令
- 父任务补充范围：8 业务表加 erp_kingdee_sync_run、infra_job_log、dcc_registration_certificate_daily_run 共 11 表，不能扫其余表。live_install 已按实际保存元数据补齐全量与 I2 私密基线 databaseTableCounts，本脚本不改基线。
- RED: `python -X utf8 -m unittest test_verify_restored_counts -q` -> FAIL，helper 尚不存在。
- GREEN: 同命令 -> PASS 1/1；覆盖11表 SELECT 查询、全部相等、行数不符、缺表及额外表拒绝。未执行远端查询，不算恢复验收 PASS。
- 固定 host=172.30.30.59、显式 target、容器 `<target>-mysql` 精确匹配；使用已有 `/run/recovery/mysql-client.cnf`，凭据不进入命令值/输出。
- 父任务确认全量 SUCCESS 后，在本目录执行以下命令（PowerShell）：

```powershell
& 'C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' -X utf8 ./verify_restored_counts.py --target '<从本轮READY读取的spug-empty59目标>' --baseline C:/Spug/runtime/private/spug-backup59-mvp-20261116/full3c2395-acceptance-baseline.private.json --output C:/Spug/runtime/private/spug-backup59-mvp-20261116/full3c2395-restored-counts.private.json
```

- 脚本不默认 target；下一轮清空后传新的 READY target，不修改源码、不自动探测。
- 追加 RED: 同一 unittest 命令 2 errors，原 compare 不接受 target 且没有 target_ref。GREEN: 2 tests PASS，合法新目标精确回显、错误前缀/越界/命令字符拒绝，未远端执行。
- 当前工作区基线 f6ffee15b9f7a2a27b127c72bb7e1700dad1008c；本子任务仅载体、定向测试与记录，未改产品。最终融合及目录收口由父任务负责。
