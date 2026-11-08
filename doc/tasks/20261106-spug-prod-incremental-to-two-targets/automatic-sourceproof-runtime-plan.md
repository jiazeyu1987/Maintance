# 自动源恢复证明的运行环境合同

## Current Status
ready_for_closeout — 本机60项回归PASS/零skip，实际同PID精确运行环境只读导入PASS（3产品模块+40依赖模块完整实际SHA，含native extension）；FULL源证明未重跑，等待root审阅。原失败620B和FULL audit保持；I1/I2显式阶段代次另项待接入。

## 目标与里程碑
- [x] 核原失败、helper传输环境及安装控制服务的真实Python/dependency合同。
- [x] BDD/RED固定缺失runtime上下文，最小修复并验证准确依赖路径/pins。
- [x] GREEN/回归/只读实际导入证明，冻结交根任务复核。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。缺失/错误依赖、Python或pin仍明确失败。
- 是否从根因和长期维护角度解决：是。检查helper使用其实际依赖模块所属的已安装运行环境，而非假设传输Python环境可直接导入。
- 是否存在临时补丁或绕过：否。不安装依赖、不改控制服务、不跳过语义健康或主程序状态门禁。

## 经验门禁
- Trigger：FULL373真实成功后的独立源恢复证明导入失败。
- Preflight check：保留620B失败日志SHA39fb0bc4f05487414c88b710e6cd44c2f4ea680feda9d191d0d36e2eb55e4acf；读取精确安装/实际owner/capture/环境，并按pins核依赖归属。
- Blocker：任何runtime来源/解释器/路径/原始pin不能验证；真实源证明未经root审阅不可重跑。
- Verification：明确本机合同RED/GREEN与只读真实安装导入验证，不用mock成功冒充运行态证明。
- Forbidden action：不得pip安装、远端写入/服务变更、覆盖FULL成功audit或原失败、执行备份/恢复/SQL写入。
- Evidence：新runtime诊断/测试日志；原失败和FULL audit原件保持。

## BDD
- Given实际来源控制与目标语义健康模块使用已登记Python依赖，When验收helper导入这些模块，Then必须按准确运行上下文并验证其来源，不能依赖SSH传输Python偶然可导入。
- Given任一解释器或模块归属pin/依赖路径变化，When预检，Then在业务检查前明确拒绝。
- Given已存在FULL audit和原失败，When修复helper，Then原件字节保持，实际源证明待root独立执行。

## 已证实根因与修复
SSH传输使用正确的已登记Python，但helper仅注入engine三目录，漏掉精确已pin control.environment.PYTHONPATH的第四项已安装runtime site-packages。已按完整固定路径注入，核transport实际解释器与pythonPin相等、bytecode关闭、路径绝对/规范/无别名、产品模块实际来源与130清单SHA相同，记录所有实际加载依赖文件SHA。无pip安装、无服务环境改动。相邻health子进程原本已正确使用target控制配置environment，保持不变。

## RED / GREEN / REGRESSION
- sourceproof-runtime-red.txt：11项FAIL；正式原现场620B ModuleNotFoundError日志保持。
- sourceproof-runtime-green.txt：25 PASS/2 FAIL。2项是UI agent同时收紧v1只认历史FULL，旧测试将FULL v1重标成I1/I2因正式协议被拒；已保留中间失败并改为明确拒绝测试，不mock绕过。真正新代I1/I2支持另项实施。
- sourceproof-runtime-regression.txt：12运行环境+16源证明+32派发合同=60 PASS/零skip，0.47秒；完整载体UTF-8编译与FULL本机prepare通过。
- 两次只读实际imports报告均独占新建；automatic-sourceproof-runtime-imports-complete.json含当前PID25086、实际PYTHONPATH、3产品和40依赖原文件pins（含rpds native extension）。无SQL/API/业务命令、无远端写入，未运行完整源证明。
- automatic-sourceproof-runtime-fix.json固定helper/测试/原失败/FULL audit与imports报告pins。root审阅后沿用 `verify_automatic_source_restoration.py --kind FULL`。本轮不允许据此宣称I1/I2可运行。

基线路径确认：E盘原文档缺失，按root已确认迁移入口读取C:/SpugHandoff/release/repository/docs/server-access.md与release-backup-restore.md；仅已有授权精确主机只读诊断，不变更访问范围。
