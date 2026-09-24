# 两入口发布开发阶段审查

## 当前结论

BLOCKED：P1基线、锁与状态修复已通过主审并提交；P2尚未通过，P3两入口页面尚未开发。指定GPT-5.6 Luna后端子任务连续三次HTTP 503，维护子任务也返回HTTP 503。未切换开发模型，未执行测试服/正式服发布。

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

- 维护：D:/IntRuoyiWorktree/two-button-release-delivery-maintenance；P1提交后P2草稿为publish-int-ruoyi.ps1、release_input_preparation.py及测试，未提交。
- 应用：D:/IntRuoyiWorktree/two-button-release-delivery-app；P1提交后P2草稿为Record/Store/Service、IntentTest及应用侧执行记录，未提交。
- 分支均为codex/two-button-release-delivery。应用slot33，端口8208/48208；本次检查未发现这两端口监听，也未发现匹配本任务标识的运行中开发/测试进程。
- 中央task-state唯一由主代理维护；应用侧任务日志保存Java TDD证据，中央日志保存维护及主审证据。
- 服务恢复后从P2窄切片继续，先完成持久intent/CAS与安全prepare，再审cleanup和后台自动推进。不得重做P1、接管历史READY、改冻结R22工作区或沿用旧GO发布新代码。
- 当前不是ready_for_closeout：保留两个工作区及草稿，不合回int_main、不清理或删除工作区、不宣布整项完成。
