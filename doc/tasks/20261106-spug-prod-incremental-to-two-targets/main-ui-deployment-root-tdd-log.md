# MAIN UI 显式部署根目录：TDD 记录

## Current Status

ready_for_closeout。本机实现与必要验证完成，四文件冻结交父；实现提交及实际只读预检/真实UI由父推进。本阶段采用父批准的双 root 修订 `main-ui-deployment-roots-design-r2.md`（11898B/SHA `857eba56d18cdcf21e8fcc814c50b70b3e4e65a3ef5af5bc4388d4e057409244`）。原单 root 设计保留，未实施。只改preflight、MAIN UI消费者及两份独立测试；旧v1/dispatcher/chain/只读audit/历史reader保持。本子任务不访问服务器、浏览器，不构建、不提交或写本仓 index。

## 目标、里程碑与预期验证

1. RED：真实临时Git仓库/worktree及明确的UI证明读取协议先失败。
2. GREEN：显式root仅取已验build.worktree，原完整source/Spug函数前后执行；新v2严格消费，默认仍原合同。
3. REGRESSION：受影响旧预检及MAIN/普通UI合同、上一消费者测试通过，原输入与范围保持，记录原始日志与SHA。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。没有参数则原默认目录；显式参数不匹配时失败，不搜索替代目录。
- 是否从根因和长期维护角度解决：是。区分开发工作区与已登记部署源码；scope算法不复制、不缩减。
- 是否存在临时补丁或绕过：否。目录、build原件、commit、clean及runtime证据完整绑定。

## 经验门禁

- Trigger：真实MAIN预检使用开发目录导致已安装source漂移误判。
- Preflight check：正式build原worktree/target与原source/Spug完整scopes；新改文件不得命中五历史attempt。
- Blocker：路径/对象/commit不符，源码dirty，scope差异，stage前后变动，v2原件或字段不闭合。
- Verification：真实Git RED→GREEN，CJS浏览器前验证协议，有限回归及输入SHA。
- Forbidden action：不monkeypatch原Git验证函数、不改原scope、不把临时协议测试记为现场验收、不改历史原件。
- Evidence：已批准设计及本日志的真实执行结果。

## BDD

- Given开发目录有dirty源码、原build worktree干净且精确target，When显式root，Then完整source/Spug校验通过且开发字节不变；不传参数仍原失败。
- Given同commit其它目录、相对/缺失/别名路径、错build对象/target/pin，When显式root，Then外部观察前拒绝。
- Given登记root自身staged/unstaged/untracked/Spug或HEAD漂移，When检查，Then失败；末次复核期间漂移也失败。
- Givenv2 gate，WhenMAIN UI读取，Thensource/Spug/root/build/runtime完整同值；缺失或变化在浏览器前拒绝，旧v1保持。

## 实际执行

尚未运行测试或实现。父随后在已登记 clean source worktree 真实执行原两 component 门禁，Spug 因 565→b5 的 `ops/spug/smallapp-ui/app.js` 差异而拒绝；该 FAIL 必须保留。单 root 方案已停止，未改生产或测试文件。

修订设计为 `main-ui-deployment-roots-design-r2.md`（11898B/SHA `857eba56d18cdcf21e8fcc814c50b70b3e4e65a3ef5af5bc4388d4e057409244`），等待父审阅。父独立真实 `main-ui-registered-component-roots-observation-20261110-r1.json` 已证明 source b5 与 Spug 565 各自登记 root 的原完整 component 门禁分别 PASS；这不是 UI gate 或现场操作成功。本子任务只读 loader 核明 Spug 字段为 `worktree/sourceCommit`，正式 `resourceBuildPin` 与原对象完全一致。

父已批准上述修订；仅四文件实施。已只读逐查五份历史 attempt，本次四文件匹配数均为零。

RED：session 74483 已终态，Python 新23项全部失败（22缺正式函数、1缺CLI双参数）；JS新24项中23失败、原v1兼容1通过。真实临时Git/worktree前置均完成，零skip；JS失败为v2被原schema拒绝。原日志 `main-ui-deployment-roots-red-r1-python.log`（52842B/c0ce65b73f83c67b3c9ad646f26e36577c093c4e5cef534fa6df8d8e5c9a276e）、`main-ui-deployment-roots-red-r1-javascript.log`（44740B/40048912bbb1e4303cff10b30fe29854b96998b7448135a35f6e47cd9e598eee），报告 `main-ui-deployment-roots-red-r1.json`。四输入SHA前后保持；非现场/UI验收。接下来仅最小实现，测试保持。

GREEN + REGRESSION：唯一 session 4405 已完整终态。Python 命令为固定 runtime `python -B -X utf8 -m pytest test_main_ui_deployment_root.py test_main_program_ui_preflight.py test_automatic_ui_preflight_git.py -q -p no:cacheprovider`（均 TASK 下绝对路径），58 PASS（新23、原预检8、原Git27），exit0，1705.61秒。真实临时Git操作较慢，期间只读确认进程推进，未重复启动、未中止改跑。JS 命令 `node --test main_ui_deployment_root.test.cjs automatic_main_cycle_ui_contract.test.cjs automatic_stage_ui_contract.test.cjs`，37 PASS（新24、原MAIN9、原stage4），exit0，3.76秒。两套零skip，四输入SHA前后保持；每条实际完整参数与原日志pin记录于 `main-ui-deployment-roots-green-r1.json`。

- Python 原日志 `main-ui-deployment-roots-green-r1-python.log`：114B/SHA `d7da12b5b60b47b0f79f4fa5b3781e0afcad5add2ca20ee5bc80a2adde5262db`。
- JS 原日志 `main-ui-deployment-roots-green-r1-javascript.log`：2737B/SHA `824cb9b7c6218499a8a16a56923d52c7706490ce65f20de842bded8f1d886e20`。
- `main-ui-deployment-roots-preservation-r1.json`：原共享Git函数、dispatcher、selector、chain/readonly和历史reader共10文件与观察时HEAD完全一致。原五attempt未绑定本次四文件。

## 最终实现与边界

`verify_main_deployment_inputs` 仅允许成对显式 `--source-deployment-root` 与 `--spug-deployment-root`；通过原完整build对象/pin和每个真实根的精确HEAD/全clean验证，分别执行原完整source/spug scope。默认仍原shared-head gate及其真实差异拒绝；外部观察前与结束后再次完整检查，显式才生成MAIN v2。

CJS仅MAIN v2在浏览器前运行固定正式dispatcher CLI，完整重验全部inputPins，再读两build、generation及runtime同值证明。后续门禁只复用同唯一selection的不可变推导，仍逐全部原件/身份核验；未知/失败不建立成功缓存，不能换selection或外部注入证明。实际完整CLI/现场UI不由本机协议fixture冒充。

父已只读审阅四文件、未提出修改，并独立启动真实只读MAIN预检；该现场结果不在本子任务的95项本机PASS之内。本阶段没有真实备份/恢复/UI/远端/构建或本仓提交。冻结交付文件与SHA另列 `main-ui-deployment-roots-delivery-r1.json`。
