# 发布不成功的直接原因

## 当前结论

**当前第四次按钮构建被电脑重启中断，控制台恢复后未能结束旧 running operation，工作流一直 BUILDING，因此无法继续发布测试服。** 这是当前真实阻断，不以展示或审计问题作为失败根因。

证据截至 2026-09-17 18:32 +08:00，来自本机 operation、workflow、构建日志、操作系统启动时间、进程只读查询和对应代码。本轮没有触发新构建、发布、登录、服务器请求或数据库操作。

## 四次真实按钮尝试

| 尝试 | workflow / operation | 实际结果 | 当前判断 |
| --- | --- | --- | --- |
| 12:39 | rw-91de413adbb3 / 32276942-b868-4c5c-bb97-f6235fb0570a | 构建日志含非法 UTF-8，列表/阶段解析抛 MalformedInputException；任务后来停止构建，operation=failed、workflow=FAILED/LOG_DECODING | 输出编码问题已修，后三份日志严格 UTF-8 解码通过；不再是当前阻断。 |
| 13:01 | rw-19adea2faa85 / 7e4d9356-1ee3-4900-be7d-b8087af89f95 | 后端、前端、镜像、manifest 均完成，NAS 上传错误指向业务共享，创建 Backup 目录 UnauthorizedAccessException | 应用 1b15673b0 已统一读写 releaseNasConfig；第三次真实上传成功，故不再是当前阻断。 |
| 13:47 | rw-aadedeeb968b / 84d22aa9-f463-49c9-a68b-b086b7aeb917 | 14:21:20 build operation=succeeded，NAS 上传/验包成功；控制台因要求不存在的 manifest.includeShowroomBuildPackage 报 RELEASE_PACKAGE_EVIDENCE_MISSING | 1c44505ee 已改读 canonical components 并精确读包。实际 workflow 于15:48:55变成READY，证明这处阻断已解除。 |
| 15:49 | rw-d12f1b2d7a7e / fee8558c-bfe5-4f44-adec-e46147a7ed64 | 16:02:42 Maven BUILD SUCCESS，日志随后停在 pnpm build:test；16:09:35系统重启；operation至今running、workflow至今BUILDING | 当前直接阻断。没有完整manifest或镜像包，未进入NAS上传及publish-test。 |

## 当前阻断的完整证据链

1. 最新 releaseTag 为 `release-20260917-074905-d12f1b2d7a7e-app`；operation 源文件为 `E:/Int/CacheData/IntRuoyi/runtime-control/fee8558c-bfe5-4f44-adec-e46147a7ed64.json`，当前 status=running。
2. [构建日志:14063](/E:/Int/CacheData/IntRuoyi/runtime-control/logs/fee8558c-bfe5-4f44-adec-e46147a7ed64.log:14063) 为 Maven BUILD SUCCESS；14066 为完成时间16:02:42；14069-14070为 Building frontend static assets / Run: pnpm build:test，此后没有成功或失败终态。
3. Win32_OperatingSystem.LastBootUpTime=`2026-09-17 16:09:35`。workflow 最后更新16:09:05，最后心跳16:02:43。旧构建启动于15:49，早于此次系统启动；当前进程查询排除诊断自身后未发现该发布路径、operation或tag对应命令。
4. 本地包目录 `E:/Int/CacheData/IntRuoyi/publish-int-ruoyi/release-20260917-074905-d12f1b2d7a7e-app` 只有 `evidence`、`required-sql`，根 manifest.json 不存在。不能把这一目录当作READY包或继续部署。
5. 控制台后端于17:38:04启动、17:38:56完成；[恢复日志:1255](/D:/IntRuoyiWorktree/r260911-release-button/a/doc/tasks/20260916-release-button-remediation/backend-after-reboot.stdout.log:1255) 开始出现 `RELEASE_WORKFLOW_OPERATION_TERMINATION_UNCONFIRMED`，18:31仍在周期重复。
6. 原因是 executor 的 activeProcesses/activeContainers 仅在内存中；重启后旧 operation 的进程句柄不存在。[RuntimeControlCommandExecutorImpl.java:92](/D:/IntRuoyiWorktree/r260911-release-button/a/IntRuoyiBackend/yudao-module-infra/src/main/java/cn/iocoder/yudao/module/infra/service/runtimecontrol/RuntimeControlCommandExecutorImpl.java:92) 找不到句柄返回false，当前运行后端的恢复路径抛终止未确认，不能收束旧 operation。磁盘上另有未提交修改将false直接写failed，但实际后端日志证明该修改尚不是当前运行行为。
7. [index.vue:1047](/D:/IntRuoyiWorktree/r260911-release-button/a/IntRuoyiFronted/src/views/infra/runtime-control/index.vue:1047) 只在选中workflow.state=READY时允许点击发布测试服，BUILDING无法继续。

结论边界：能确认第四次构建被系统重启打断；不能从未出现错误的前端尾日志推断“前端源码编译失败”。当前卡住的是中断 operation 的恢复与终态收束。

## 今天是否已经进入测试服部署

当前控制台 state-dir 中，与 `release-20260917-*` 对应的 operation 共4条，全部是build-release；没有publish-test operation。不能把当前状态描述成“测试服部署脚本又失败了”。

第三次完整包的本地 manifest 确认：publishScope=app-release，components含backend/admin-frontend/database-contract/required-sql/runtime-env/packaging-manifest，不含旧includeShowroomBuildPackage字段；packageDigest=`8811a5cfb0c62556bd6b287870c9d5fde6eb12e3916ba3955d2ff2d7ffdb8f0a`，artifactCount=661。它能证明构建/NAS链路曾成功，但其来源是应用1b15673b0，不代表后来所有未提交修复已出包。

## 需要优先解决的实际事项

1. 基于旧operation启动时间、当前系统启动时间、任务命令归属及缺失制品证据，正式收束这次已中断的构建；恢复机制应能识别“旧本机进程已不可能继续运行”，保留真实中断原因，不能长期保持running。
2. 确定本次要发布的已提交来源。若要求当前修复版本，先完成来源提交与干净隔离，再用新workflow/tag构建；不能重用第四次半成品或给它补写manifest。
3. 对最终READY且来源正确的同一包，通过发布测试服按钮创建真正的publish-test operation，才开始验证部署脚本、迁移、镜像切换和运行态。当前尚无这一阶段的实际失败证据。

本轮只定位和验证失败原因，没有修改状态文件、终止进程、修复代码或执行发布。

## 验证方法与结果

- 历史任务文档仅用于定位，结论由真实 operation/workflow/log/manifest 交叉确认。
- 对4份构建日志执行严格UTF-8解码：第一份在byte393931失败，其余3份通过。此为文件证据校验，不是产品测试。
- 只读进程枚举先排除当前诊断PowerShell自身，避免命令文本含发布路径造成误报。
- 分析任务PASS：直接根因已定位。发布目标未完成，不给出发布成功结论。
