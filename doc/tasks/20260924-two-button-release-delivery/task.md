# 两入口发布开发交付

## Current Status
blocked

P1已完成并提交；P2未通过审查。指定GPT-5.6 Luna后端子任务连续三次HTTP 503，维护子任务也503，开发服务不可用。未擅自切换模型；草稿及工作区保留，详见verification-report.md。

## 用户授权与目标
用户已确认复用现有构建、部署、验收、晋级阶段并收敛为两个顶层入口，明确要求用 GPT-5.6 Luna 子代理开发，主代理 review 和把控方向。按照已提交计划 `doc/tasks/20260924-two-button-release-next-steps/implementation-plan.md` 执行，不能只改按钮名称或用前端请求串联后台阶段。

## 里程碑
1. PRD/测试合同与当前基线审查（完成，首轮修订后validator PASS，主代理approved）。
2. 独立 worktree 基线对齐、锁与状态修复（完成，P1主审通过；维护772fc46、应用d30f7ee02）。
3. 后端持久目标/自动推进和前端两入口（P2进行中后因Luna服务503阻塞，P3未开始）。
4. 独立验证、修复闭环及新版本复检（待执行）。
5. 满足授权和门禁后的真实按钮验收、集成与收尾（待执行）。

## 预期验证
严格 BDD/RED/GREEN/REGRESSION；生产生成SQL在隔离MySQL验证；Java状态、授权和恢复合同验证；Playwright真实页面路径。主代理复核提交与证据，独立tester不修改产品代码。缺少实际前提明确阻断，不以mock成功替代验收。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，复用现有状态机与执行器。
- 是否存在临时补丁或绕过：否；不改被冻结发布输入，不手工清远端锁/台账或写成功状态。

## 经验门禁
- 前序规划任务已completed；本次单独交付目录，避免规划完成等同于实现完成。
- 用户明确指定开发子代理模型gpt-5.6-luna，主代理负责审查与task-state；仅本任务相关仓库建立独立工作区，不改并发任务资源。
- Windows/中文全部显式UTF-8，PowerShell不使用&&；命令与证据脱敏。
- 当前int_main与R22批准分支存在发布相关差异，必须先核对并选择性对齐；R22旧GO不能自动覆盖新代码。
- 发布锁必须实际验证生产SQL；未知写入保持隔离；所有发布写动作只能通过真实产品按钮，接口仅最终核验。
- 高风险动作前记录experience-preflight；不在尚未明确边界时操作远程服务器。
- spec-driven-delivery的五份核心文件均保留；另按项目规则保留本task.md及最终verification-report，不因技能默认文件数删除项目必需记录。

## 当前阻塞
- 指定Luna开发服务连续HTTP 503；后端已重试三次，维护子任务也受影响。
- P2代码仍有未放行项，不能提交该草稿或执行发布；主审完整缺口与续接点已记录verification-report.md。

## 隔离工作区
- 应用：D:/IntRuoyiWorktree/two-button-release-delivery-app，基线f46b0bdc20d80ee7fa6e5d6b86898bcae0d0b357，已无冲突合入b15b52e0c4c14ed46ebe0772ba4aea2caa8df090，待验证后提交。注册slot33，前端8208/后端48208，port guard PASS。
- 维护：D:/IntRuoyiWorktree/two-button-release-delivery-maintenance，基线7230ddc81aff1a3b53d2ce02df226c57a4dc3c61，已无冲突合入0e5d785added60ed742455c37efe3612fcf60ba3，待验证后提交。
- 两仓分支：codex/two-button-release-delivery；未动冻结R22工作区、main脏改动、其他进程或端口。
- 主代理审查边界：先P1真实SQL/状态，再逐阶段放行；新代码不能沿用旧R22 GO。
- P1同阶段分工：luna_executor只改维护锁与测试，luna_state_executor只改应用状态与Java测试；后者使用app WT同名任务目录记录BDD/TDD，中央task-state仍由主代理独占。禁止跨仓写入和提前执行P2。
- 合并基线主审验证：应用WT后端 `mvn.cmd -B -pl yudao-module-infra -am '-Dtest=ReleaseWorkflow*,RuntimeControlServiceImplTest' '-Dsurefire.failIfNoSpecifiedTests=false' test` 退出0，136 tests、0失败/错误/跳过；这是基线回归，不替代新增行为RED/GREEN。
- 维护基线回归：preflight_r20 / migration_supersession / package_governance 共110通过、3失败；失败均为supersession测试硬编码旧相邻a目录，未找到当前应用源码。已要求P1改为显式应用路径配置并重跑，未以软链接或复制文件掩盖。
- 主审重跑上述完整回归：显式设置INTRUOYI_TEST_APP_BACKEND为本轮应用WT后，113 passed，52.57秒、退出0。原路径阻塞已解决；此结果不替代锁/状态新增行为验收。

## 后续阶段审查约束
- P2源准备作为受控、有证据的步骤；现有ReleaseSourceFreezeContract保持纯验证，复用scripts/prepare-frontend-dependencies.ps1准备依赖。每轮路径、源SHA和依赖证据须持久化，不能要求操作者先手工建WT再点按钮。
- 新请求使用显式幂等键，绑定操作者、批准源和规范化载荷；同键同载荷回读、异载荷拒绝。不能仅用原因/源生成永久键，阻止用户后续有意的同源新发布。
- operation持久创建与派发状态要分开；已有running文件不等于执行已开始。跨进程CAS不能仅依赖Java synchronized，需真实并发验证；仅依赖内存map不满足重启合同。
- 前端依赖准备完成：当前应用WT `corepack pnpm install --frozen-lockfile` 退出0，pnpm10.25.0，依赖1103项；无主工作区node_modules复制，无服务启动。随后 `corepack pnpm ts:check` 退出0，合并基线类型检查通过。
- P1维护局部主审：实际生成SQL旧顺序RED证据由executor记录；主代理独立重跑lock文件4 PASS。首次/APPLIED/同tag/并发/失权/异常退出覆盖仍不齐，已退回补齐，不放行P1。
- 源字节审查：新app WT受全局autocrlf=true影响，两份20260904历史迁移被检出为CRLF，规范化LF后与批准Git blob完全一致。主代理仅将本任务WT这两个未编辑文件恢复为merged index原始UTF-8/LF字节（不改Git内容或测试期望）；批准hash分别b67eda6fab5266f66aca48dea03a9bc2e2e39f6eeeb9e6733c32909de10d8783、6c3bdd8a1b8dad7b71f09b22d1b6dab1d5598ae300ba805cc883afcd26457b90。P2源准备必须固定源字节策略，不能依赖全局Git换行配置。
