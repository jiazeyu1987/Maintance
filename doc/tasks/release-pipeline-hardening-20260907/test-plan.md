# 发布流水线 P0 加固独立测试计划

- Task ID: `release-pipeline-hardening-20260907`
- Created: `2026-09-07T21:07:40+08:00`
- Workspace: `D:\ProjectPackage\Int\IntRuoyiWorktrees\release-pipeline-hardening-20260907\m`
- User Request: `同一个安装包先发布测试服，验证后原样晋级正式服和备份服。`

## Test Scope

验证 PRD P1-P3：direct 入口关闭、with-data 阻断 prod/backup、逐文件完整性与稳定摘要、tested 绑定真实成功 publish-test operation、prod/backup 一致门禁，以及所有拒绝发生在远端写入前。只用本地临时包、虚构 operation JSON 和本机真实运行时；不连接 NAS/服务器，不运行真实发布、Docker、数据库、MinIO 或浏览器流程。

## Environment

- Windows PowerShell 5.1、Python 3.12、pytest、Git、JDK 17、Maven 3.9。
- 工作目录为任务 worktree；UTF-8；临时根为 `$env:TEMP\release-pipeline-hardening-20260907`。
- NAS、ssh/scp、Docker、数据库和 MinIO 使用“调用即失败”的本地探针；任何调用次数非 0 均判失败。

## Accounts and Fixtures

- 不需要任何账号、密码、token、私钥、连接串或真实配置。
- `PKG-CODE-VALID`：最小 code-only 包；`PKG-DATA-VALID`：最小 with-data 包。
- `PKG-MUT-*`：内容篡改、缺失、额外文件、bytes/hash 错误、绝对路径、`..`、重复和大小写冲突。
- `OP-SUCCESS`：environment=test、action=publish-test、status=SUCCESS、releaseTag 匹配；负例逐项改变字段或使用畸形 JSON。
- `TESTED-VALID` 只能由真实本地 mark-tested 流程生成；负例逐字段变异。
- fixture 每例独立创建并清理，不读取真实运行配置或 operation 日志；缺工具/fixture 时 fail fast，不得 skip。

## Commands

```powershell
python -X utf8 -m pytest scripts/tests/test_release_package_governance.py -q --basetemp "$env:TEMP\release-pipeline-hardening-20260907\governance"
python -X utf8 -m pytest scripts/tests/test_release_package_slimming.py scripts/tests/test_deploy_precheck_report_contract.py scripts/tests/test_release_sql_preflight_gate.py scripts/tests/test_publish_release_lock_cleanup.py scripts/tests/test_runtime_control_frontend_deploy_contract.py -q --basetemp "$env:TEMP\release-pipeline-hardening-20260907\focused"
mvn.cmd -f backend/pom.xml -Dtest=RuntimeControlContractTest,RuntimeControlOriginalGovernanceParityTest,RuntimeControlOriginalParityTest test
python -X utf8 -m pytest scripts/tests tests -q --basetemp "$env:TEMP\release-pipeline-hardening-20260907\full"
python -X utf8 scripts/verify_contracts.py
git diff --check
```

PowerShell AST 另执行：

```powershell
$paths = @('ops/deploy/publish-int-ruoyi.ps1', 'ops/release/lib/ReleasePackageGovernance.psm1') | Where-Object { Test-Path $_ }
foreach ($path in $paths) { $tokens=$null; $errors=$null; [void][System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path $path),[ref]$tokens,[ref]$errors); if ($errors.Count) { $errors | ForEach-Object { Write-Error $_.Message }; exit 1 } }
```

成功信号：命令退出码全部为 0，Maven `BUILD SUCCESS`，Tests run 非 0，Failures/Errors/Skipped 均为 0，AST 无错误，diff check 无错误。

## Test Cases

### T1: Mode 强制并删除 direct

- Covers: P1-AC1
- Level: integration/contract
- Command: 治理 pytest 的 direct/missing-mode 用例与 AST 命令
- Expected: direct 和缺失 Mode 无副作用地非零失败；合法显式 Mode 通过参数绑定。

### T2: with-data 生产级拒绝

- Covers: P1-AC2
- Level: unit/integration
- Command: 治理 pytest 的 scope 参数化用例
- Expected: test 通过，prod/backup 明确拒绝 with-data。

### T3: scope 门禁早于外部动作

- Covers: P1-AC3
- Level: integration/contract
- Command: 治理 pytest 的 scope-order 用例
- Expected: prod/backup 拒绝后 NAS 之外全部外部写入探针为 0。

### T4: 显式命令兼容

- Covers: P1-AC4
- Level: backend integration
- Command: Maven 定向合同命令
- Expected: build/deploy/mark 仅生成显式合法 Mode；code-only test/prod/backup 参数保持兼容。

### T5: artifact 精确覆盖 payload

- Covers: P2-AC1
- Level: module integration
- Command: 治理 pytest 的 exact-payload 用例
- Expected: manifest.json 被声明，全部 path/bytes/实际 hash 一致且无遗漏。

### T6: 摘要稳定且变化敏感

- Covers: P2-AC2
- Level: unit
- Command: 治理 pytest 的固定摘要向量和跨根目录用例
- Expected: 同内容跨根/分隔符摘要相同；payload 或 manifest 变化导致摘要变化或失败。

### T7: 完整性负例矩阵

- Covers: P2-AC3
- Level: parameterized integration
- Command: 治理 pytest 的 tamper/missing/extra/path 用例
- Expected: 每个负例非零，错误包含相对路径及 mismatch/missing/undeclared/invalid/duplicate 原因。

### T8: 四个生命周期位置强制校验

- Covers: P2-AC4
- Level: runtime/structural contract
- Command: 治理 pytest 的 lifecycle-order 用例
- Expected: build 本地与 NAS 后复制、deploy 下载后、mark 写入前均使用同一校验器；失败后后续探针为 0。

### T9: attestation 精确排除

- Covers: P2-AC5
- Level: unit/integration
- Command: 治理 pytest 的 attestation-exclusion 用例
- Expected: 仅受控可变 metadata 白名单 `tested.json`、`rollback-compatibility.json`、`prod-latest.json`、`backup-latest.json`、`prod-deployments/**`、`backup-deployments/**` 可排除不可变 payload；其他额外文件失败。排除不代表 metadata 有效，tested 由 P3 验证，deployment history 保持现有候选与回滚合同。

### T10: operation 严格选择

- Covers: P3-AC1
- Level: backend unit/integration
- Command: Maven operation selection 测试
- Expected: 仅 environment/action/status/releaseTag 全匹配的 operation 可用，其余明确失败。

### T11: 服务端证据所有权和脚本交叉验证

- Covers: P3-AC2
- Level: backend/module integration
- Command: Maven preview/execute 测试与治理 pytest operation-evidence 用例
- Expected: 客户端证据值不进入命令；服务端选择证据，PowerShell 再核 ID、环境、动作、状态和 tag。

### T12: tested 字段和原子写入

- Covers: P3-AC3
- Level: module integration
- Command: 治理 pytest 的 atomic-attestation 用例
- Expected: 成功文件字段/格式/digest 齐全；前置失败保留旧字节且不留临时半文件。

### T13: prod 与 backup 强绑定矩阵

- Covers: P3-AC4
- Level: parameterized integration
- Command: 治理 pytest 的 prod-backup-attestation 用例
- Expected: 两环境重算 payload/digest 并核全部字段；所有陈旧/伪造值在外部动作前失败且探针为 0。

### T14: 删除 backup 和 RequireTested 绕过

- Covers: P3-AC5
- Level: contract/integration
- Command: 治理 pytest 的 mandatory-attestation 合同与 AST 命令
- Expected: prod/backup 无条件要求 tested；源码不存在临时 backup bypass，RequireTested 不再决定是否验证。

### T15: 合法本地闭环与回归

- Covers: P3-AC6
- Level: local integration/regression
- Command: 本计划 Commands 全部命令
- Expected: 合法 fixture 完成 mark、prod gate、backup gate并绑定同一 tag/package/manifest/operation；全回归通过，外部探针为 0。

## Coverage Matrix

| Case ID | Area | Scenario | Level | Acceptance IDs | Evidence |
| --- | --- | --- | --- | --- | --- |
| T1 | Mode | direct/隐式 Mode 拒绝 | integration | P1-AC1 | `test-report.md#T1` |
| T2 | Scope | with-data 仅 test | integration | P1-AC2 | `test-report.md#T2` |
| T3 | 顺序 | scope 早于外部动作 | contract | P1-AC3 | `test-report.md#T3` |
| T4 | Java 命令 | 显式 Mode 兼容 | backend | P1-AC4 | `test-report.md#T4` |
| T5 | 清单 | payload 精确覆盖 | integration | P2-AC1 | `test-report.md#T5` |
| T6 | 摘要 | 稳定与敏感性 | unit | P2-AC2 | `test-report.md#T6` |
| T7 | 完整性 | 全负例 fail fast | integration | P2-AC3 | `test-report.md#T7` |
| T8 | 生命周期 | 四处强制校验 | contract | P2-AC4 | `test-report.md#T8` |
| T9 | 排除项 | 证明文件精确排除 | integration | P2-AC5 | `test-report.md#T9` |
| T10 | Operation | 成功操作选择 | backend | P3-AC1 | `test-report.md#T10` |
| T11 | 证据所有权 | 服务端选择与二次验证 | integration | P3-AC2 | `test-report.md#T11` |
| T12 | Tested | 字段与原子写入 | integration | P3-AC3 | `test-report.md#T12` |
| T13 | 晋级 | prod/backup 强绑定 | integration | P3-AC4 | `test-report.md#T13` |
| T14 | 强制门禁 | 删除绕过 | contract | P3-AC5 | `test-report.md#T14` |
| T15 | 回归 | 合法本地闭环 | regression | P3-AC6 | `test-report.md#T15` |

## Evaluator Independence

- Mode: blind-first-pass
- Validation surface: real-runtime
- Required tools: Windows PowerShell 5.1, Python 3.12, pytest, JDK 17, Maven 3.9, Git
- First-pass readable artifacts: prd.md, test-plan.md
- Withheld artifacts: execution-log.md, task-state.json
- Real environment expectation: 在真实 worktree 和真实 PowerShell/Python/JVM 中执行本地文件哈希、JSON 解析和 MVC 测试；包和 operation 使用隔离 fixture，禁止连接真实 NAS/服务器或以 mock 成功替代治理文件操作。
- Escalation rule: tester 先写初始 verdict；仅主 Agent 要求差异分析后才能读取 withheld artifacts。

## Pass / Fail Criteria

- Pass when: T1-T15 全部 PASS，P1-AC1 至 P3-AC6 全覆盖，全部命令成功，无相关 skip/xfail、外部连接、秘密、fallback 或降级。
- Fail when: direct 可执行、with-data 可晋级、内容漂移漏检、tested 可伪造、backup 可跳过、门禁晚于外部动作、任一 AC 未覆盖或必需命令失败。
- Blocked when: 必需工具/依赖缺失、worktree 不可读、无法无远端验证或并发改动无法归属；BLOCKED 不得记 PASS。

## Regression Scope

- legacy/v1 manifest、包瘦身、Docker build context 清理、hash 格式、required SQL、migration 状态、发布锁清理。
- 控制台 build/publish/mark/promote 参数隔离、目标环境、生产确认、dry-run 路径和 `scripts/verify_contracts.py`。
- 无前端变更，因此不要求浏览器测试。

## Reporting Notes

- tester 只写 `test-report.md`，不得改产品代码、PRD、test plan 或 task-state。
- 每 case 记录 UTC 时间、命令、退出码、结果、覆盖 AC、运行时证明与非敏感证据；失败记录最小复现和外部探针数。
- 摘要证据仅记录 fixture 相对路径和 digest；测试后清理 fixture，清理失败判 FAIL。
