# 两入口发布开发阶段审查

## 当前结论

P1基线、锁与状态修复已通过主审并提交；P2尚未通过，P3两入口页面尚未开发。用户现已确认Luna恢复并要求续接；同一P2 worktree草稿继续审查与修复。未切换开发模型，未执行测试服/正式服发布。

## 已通过的P1

- 维护提交：772fc46d1b989cc6718b4a3dc1680028690e4338。
- 应用提交：d30f7ee028456df874a7389dc5f5c7e837211279。
- 维护主审回归：31项锁测试、113项迁移/包测试、138项其余受影响维护测试通过。
- 应用最终Maven：146 tests，0 failures/errors/skips；主代理核对Surefire XML。正面零写入阻断允许安全失败重试，错误身份/未知派发/日志损坏保持隔离；重复stale扫描不覆盖RECOVERY_REQUIRED原始证据。
- 应用Python基线86 PASS/1 FAIL；唯一期望缺少allowedPublishScopes字段的问题精确修正后，该完整测试文件8 PASS。前端类型检查、现有页面静态合同和端口guard通过。
- 实际锁SQL来自产品PowerShell函数；同tag/同operation/同executor更换lease后，真实Ownership函数拒绝旧lease，新的heartbeat推进fence。实际carrier故障注入证明成功文本不能掩盖非零退出。

## P2未放行项

1. 应用候选仅开始request key持久化，尚无完整显式发布目标、API及scheduler准备→构建→清理→部署链；不能称为两个按钮已经可用。
2. createIntent当前会把不同请求直接替换为已有活动workflow；须改成明确冲突或完整持久幂等语义，并绑定actor、preset、目标与批准载荷。
3. 当前OS锁只包围创建；跨实例CAS更新、同JVM重叠文件锁和真实并发/重启用例尚未完成。P2日志中的缺API编译失败仅是接口RED，不是并发验证。
4. 维护prepare尚无完整CLI加正式依赖helper的真实成功链。最初提交伪造stamp的fixture已被主审拒绝；后续阻断fixture通过也不能冒充真实安装成功。
5. 所有权写入时序、已有prepared证据重验、部分创建续接、安装执行器及模块完整性仍需完善；源仓可以dirty/HEAD前进，但只能读取批准Git对象，不能要求源仓等同冻结输入。
6. 长步骤仍需可靠流式进度、合理deadline和本任务子进程树终止证据；不能只延长timeout或缓冲到结束，导致heartbeat误判。
7. cleanup草稿尚缺双路径、批准HEAD、reparse/junction、进程/所有权及ExpectedPreparationDigest完整校验，禁止对真实开发仓调用。不得先删除再计算一个新的摘要来认可漂移证据。

## 工作区与续接

- 维护：D:/IntRuoyiWorktree/two-button-release-delivery-maintenance；P2准备提交为d316da9（任务: 加固发布输入准备与清理证据）；3项隔离测试通过。该提交只覆盖本地输入准备/清理合同，不证明真实依赖安装成功。
- 真实本机准备演练：workflow `rw-p2-proof-20260924` 使用 maintenance=`d316da978e5bcf169d08ec33b110132a124a103e`、application/frontend=`d0824cc97245bc68783d511f923bc95ed1d08f28`，调用正式 `prepare-frontend-dependencies.ps1` 后生成 PREPARED；脚本摘要、lockfile摘要、dependency stamp摘要均持久化。未启动服务、未占端口、未写远端。
- 该演练的 cleanup 已成功校验 prepared digest 和两路径摘要，Git 注册已解除并删除 maintenance worktree；Windows 删除含 node_modules 的 application 目录返回 `Result too large`，该目录仍是本任务唯一临时 proof 目录，不能记为 cleanup 完成，也不能清理其他路径。
- 应用：D:/IntRuoyiWorktree/two-button-release-delivery-app；P2意图/CAS提交为d0824cc97，后续Store加锁和竞争测试仍在同一工作区待提交；已验证151项Maven通过。
- 分支均为codex/two-button-release-delivery。应用slot33，端口8208/48208；本次检查未发现这两端口监听，也未发现匹配本任务标识的运行中开发/测试进程。
- 中央task-state唯一由主代理维护；应用侧任务日志保存Java TDD证据，中央日志保存维护及主审证据。
- 当前P2续接：P2 intent候选需补目标身份、active-request冲突、跨进程状态CAS覆盖/并发测试；source prepare已有改进但cleanup仍未放行。通过后才继续scheduler/API自动推进。不得重做P1、接管历史READY、改冻结R22工作区或沿用旧GO发布新代码。
- 应用 scheduler 草稿已撤回：它曾尝试 READY 直接派发 publish-test，绕过持久 prepare/cleanup 证据；未保留其 GREEN 测试结果。当前后台链必须先接入 prepare operation、build、cleanup，再允许 publish-test。
- 当前不是ready_for_closeout：保留两个工作区及草稿，不合回int_main、不清理或删除工作区、不宣布整项完成。
