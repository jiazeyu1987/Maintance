# 自动增量任务收尾 helper 调用合同

本说明的命令均由父任务按授权及现场预检执行；本子任务仅完成本机合同测试和语法检查。没有运行服务器核验、浏览器、清理或主线融合。所有命令 cwd 为本 TASK，Python 为 `C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -X utf8`。

## 明确构建归属

`task-owned-builds.json` 固定每代完整提交、精确 worktree、原构建报告 SHA、原封包 SHA 和文件清单 SHA；原构建报告不回写 `deleted`。现已明确登记11代：6319024、d487abf、9a65b5a、701b442、7c5f057、9c93449、0c5828a、3019c2e、0d44578、b5c8817、0dc7429。以该明确清单为准，不得用目录扫描生成待删列表。

仅后续另有明确本任务构建时运行 `python cleanup_owned_build.py register --report release-build-<7位SHA>.json`。它只修改任务清单，不执行删除。

## 实际证据顺序

1. 每点 FULL/I1/I2 实际终态后，由既有 UI helper `--phase verify --expect-terminal` 产生独立页面观察和固定 `automatic-<kind>-ui-terminal.json`；由 `verify_automatic_backup_chain.py` 产生相应 audit；再 `python verify_automatic_source_restoration.py --kind FULL|I1|I2` 产生固定独立源恢复报告。不得在 FULL 执行中运行来源当前健康核验。
2. I2 后用 `prepare_automatic_ui_preflight.py --kind I2 --phase verify --observation <显式新观察名>` 取得最终来源空闲、健康和 READY 计划。最终 parent 必须 I2、base 必须新 FULL。
3. 必须取得真实 `automatic-target-installation-58.json`、`automatic-target-installation-59.json` 两份 PASS。失败诊断、PLAN_ONLY/STAGED 均不能代替。旧 `allocator-selected-installations.json`、367证明及58/59恢复时安装证明保持不变；新控制历史在 stable 检查中另核。
4. `node verify_catalogue_identity_readonly.cjs --observation r4 --login`：全新context真实登录，精确复用自动FULL的账户/密码、`登 录`、嵌套登录响应及必要`知道了`流程，只允许单次本机精确登录POST（authPosts=1）；全部业务写入拒绝。核 Spug 管理员与侧栏后先等待精确iframe文档导航domcontentloaded，再核document200并进入全部包清单刷新；真实目录200、完整非空、非刷新态、可见行/总数一致才 PASS。首轮至r3失败原件保留，r4结果为 `catalogue-identity-readonly-verification-r4.json`；attempt/result/HTTP原文均独占创建。成功后另建 `catalogue-identity-readonly-selection.json`，绑定全部连续失败原件及唯一成功观察。r2截图已证实仍为登录页；r3实际登录身份已通过，随后在iframe初始URL解析时失败。具体会话被替换的原因未证实，不重用旧session或延长超时。
5. 按下述结构创建 `automatic-acceptance-selection.json`，每个 pin 为对应实际文件 `{file,bytes,sha256}`。使用 `closeout_contracts.file_pin(TASK,实际文件名)` 计算，不能手填成功状态。三个 kind 均要求各自 submit/verify 观察及固定 source-restoration 报告；最终来源 pin 绑定实际 `...-preflight-evidence.json`，不是 gate 文件。

```json
{
  "schemaVersion": "TaskAutomaticAcceptanceSelection/v2",
  "kinds": {
    "FULL": {"deploymentSelectionPin": {}, "submissionObservationPin": {}, "terminalObservationPin": {}, "sourceRestorationReportPin": {}},
    "I1": {"deploymentSelectionPin": {}, "submissionObservationPin": {}, "terminalObservationPin": {}, "sourceRestorationReportPin": {}},
    "I2": {"deploymentSelectionPin": {}, "submissionObservationPin": {}, "terminalObservationPin": {}, "sourceRestorationReportPin": {}}
  },
  "finalSourcePreflightPin": {}
}
```

6. 全部安装和目录实际 PASS 后才记录当前安装选择：

```powershell
python verify_stable_controls.py --record-selection --source-installation automatic-source-control-installation-<实际新提交7位>.json --catalogue-report catalogue-identity-installation.json --catalogue-observation catalogue-identity-readonly-verification-r4.json
python verify_stable_controls.py
```

以上 r4 只能在实际 PASS 后选用；如成功在另一个明确观察，参数必须对应 selection 中的真实成功文件。第一条只登记实际证据 pins，输出 `SELECTION_RECORDED_NOT_VERIFIED`，不等于验收；第二条才只读核实际源/目标服务 PID、活动配置、封包全部文件、逐代回执、旧原件 SHA、epoch/目标可选、来源最终计划、Windows原传输、Spug实际11文件/入口以及目录执行器/桥接器与原309任务不变。它要求三点证据齐全，故不能提前运行。

FULL 373 的阶段选择明确绑定原 `automatic-control-installation-57.json`、原 Spug 0d 回执和构建。I1/I2 明确绑定实际后继来源安装；每个 deploymentSelectionPin 指向对应 `automatic-<kind>-deployment-selection.json`。三点原备份证据不回写版本。当前安装使用 `TaskCurrentInstallations/v2`：source57 选择新来源回执；MAIN57、58/59 恢复控制及 Spug 11 文件各自保留并核对 0d 的完整清单，不能拿新来源 manifest 要求旧目标升级。来源安装器及阶段选择使用见 `automatic-source-successor-plan.md`、`automatic-stage-deployment-usage.md`。

7. 父任务最后重新取得 `source-closeout-preservation.json`、`target-58-closeout-preservation.json`、`target-59-closeout-preservation.json`；它们必须晚于 I2 原生终态。不得重跑旧代次 `protected-history-*-after.json` 来覆盖历史证明；当前新代次 protected history 已由第二条 stable 命令独立检查。
8. 主线融合仍有脏重叠/未确认归属时，任务保持阻塞，不能删任务工作区。这里只处理无新提交的明确构建 worktree，须父任务完成清理经验预检，task.md 为 `ready_for_closeout`，每代先 check 再 cleanup：

```powershell
python cleanup_owned_build.py check --generation <清单中明确7位SHA>
python cleanup_owned_build.py cleanup --generation <同一7位SHA>
```

每代检查精确 HEAD、全部未跟踪及ignored均干净、无新提交、保留封包 SHA、无引用进程/本任务容器卷、实际验收与当前控制证明。删除仅 `git worktree remove` 指定精确路径；物理与注册均消失后才记成功，明确清单中全部11代完成才生成 aggregate。不删除本 TASK 工作区或其他任务资源。

9. `python verify_closeout.py`：保留旧367及58/59完整验收，新增自动三点/独立源恢复/最终计划/当前代次/目录/显式清理清单核验。缺任一实际文件或不匹配均失败。父任务仍须单独处理实现提交、融合、任务文档最终提交和总任务 completed 门禁。

## 本地验证范围

`python -m unittest test_automatic_closeout_contracts -v`：真实已落盘本地原件及定向变异，12项通过。测试不是 E2E，未运行任何备份或恢复，也不证明尚未完成的自动三点。

`node --check verify_catalogue_identity_readonly.cjs`；五个 Python helper 及嵌入 Linux CURRENT_SCRIPT 仅 compile/AST 语法通过，未执行其服务读取。

`node --test catalogue_login_contract.test.cjs`：三项认证/导航时序单元测试，拒绝异源/不同端口/业务POST/重复登录，区分嵌套token、MFA和安全提示，并验证iframe地址只在精确文档导航完成后检查。不是实际登录或浏览器验证。r3版本14项及受测SHA留 `automatic-closeout-helper-regression-r2.json`；r4仅涉及JS helper，最新3项及SHA见 `catalogue-login-helper-r4-regression.json`，先前报告保留。
