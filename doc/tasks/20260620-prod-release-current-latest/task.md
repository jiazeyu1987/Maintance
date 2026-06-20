# 任务：发布当前最新程序到测试服并推进正式发布

## 任务目标

在用户已明确授权访问和修改正式服务器的前提下，先将当前最新程序构建并发布到测试服务器，完成发布后必要验证；确认不会影响正式服 `website` 数据边界后，再将同一发布包发布到正式服务器，并完成发布后验证。

本任务必须严格保护正式服 `website` 数据，不得误触发 Website/展厅数据同步、MinIO/NAS 覆盖或其他超出“当前最新程序发布”范围的数据写入。

## 上一任务检查

- 上一维护仓任务：`doc/tasks/20260620-fupan-post-release-role-e2e-gate/task.md`
- 状态：`COMPLETED`
- 处理：上一任务已完成复盘，不存在未收尾阻塞；本任务作为新的发布任务单独建档推进。

## 用户授权与发布边界

- 用户已明确授权：访问测试服务器与正式服务器，并执行当前最新程序发布。
- 强制边界：不得影响正式服 `website` 数据。
- 约束落地：
  - 发布前必须确认本次发布为代码包发布边界，避免触发 Website/展厅构筑包、MinIO 同步、整库数据覆盖或其他 `with-data` 行为。
  - 发布前必须核对正式服当前运行目录、挂载、compose、镜像 tag、数据根与 Website 相关目录边界。
  - 若正式服当前架构与维护仓发布脚本不兼容，必须先阻塞并说明具体风险，不得带风险直接发布。

## 经验门禁

- `docs/experience-index.md`
  - 命中文档：
    - `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`
    - `D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`
    - `D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`
    - `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`
- 本任务强制门禁摘录：
  - 发布前先确认运行控制台为当前版本，不能把“代码已改”当成“发布入口已生效”。
  - 发布前先预检 Docker 基础镜像、迁移策略门禁、Maven target/jar 锁。
  - 发布验证不能只看健康检查，必须同时核 operation、manifest、远端 `IMAGE_TAG`、运行镜像和真实入口。
  - 发布相关配置、required SQL、smoke 环境变量必须进入发布链与产物校验，不能依赖服务器残留默认值。
  - 真实发布、备份、恢复、回滚前必须明确目标环境、目标主机、目标目录、目标数据盘和数据边界；缺一项即阻塞。
  - 正式服 `website` 数据受保护；未证明本次发布不会触碰相关数据前，不得进入正式服写操作。

## 设计约束检查

- `是否引入 fallback/降级/吞异常`：否。本任务按正式发布链路执行，前置不满足即阻塞。
- `是否从根因和长期维护角度解决`：是。发布前先核对脚本与环境边界，避免靠服务器手工补丁或一次性绕过完成上线。
- `是否存在临时补丁或绕过`：否。若需临时绕过，必须先回到用户确认并补充风险说明。

## BDD 场景

- `BDD: 测试服先发布再正式发布 -> Given 当前最新程序待发布 / When 执行本次发布任务 / Then 必须先构建同一发布包并部署测试服验证通过，再允许推进正式服发布。`
- `BDD: 正式服 Website 数据必须受保护 -> Given 正式服存在受保护的 website 数据 / When 审计并执行正式服发布 / Then 发布动作只能落在本次批准的代码包边界，若存在 Website/MinIO/NAS 数据覆盖风险则必须阻塞。`
- `BDD: 发布完成必须以多重证据判定 -> Given 构建和部署动作已提交 / When 判断测试服或正式服发布是否完成 / Then 必须同时具备 operation 成功、manifest 一致、远端 IMAGE_TAG 一致、镜像运行态正常和真实入口验证证据。`

## 里程碑

1. M1：建立任务文档、完成经验门禁预检并记录高风险动作前置证据。`DONE`
2. M2：核对维护仓发布脚本、运行控制台与测试服/正式服环境边界，确认正式服 `website` 数据不会被影响。`DONE`
3. M3：构建当前最新发布包并发布测试服，完成发布后验证。`DONE`
4. M4：在测试服完成三角色真实验收后，发布同一版本到正式服并完成发布后验证。`DONE`
5. M5：整理证据、更新任务状态并执行收尾。`DONE`

## 预期验证

- 高风险动作前置：
  - `execution-log.md` 中存在 `GREEN: experience-preflight -> PASS`
- 构建与发布：
  - 构建 operation 成功，发布 manifest 存在且与目标范围一致
  - 测试服发布 operation 成功，测试服远端 `IMAGE_TAG` 与 manifest 一致
  - 正式服发布 operation 成功，正式服远端 `IMAGE_TAG` 与 manifest 一致
- 运行态：
  - 测试服与正式服后端健康检查通过
  - 管理前端真实入口可访问；如本次范围要求，补充登录或核心路径验证
- 数据边界：
  - 正式服发布预览与实际执行均不包含超出授权范围的 Website/展厅数据同步与对象数据覆盖

## 当前状态

COMPLETED：当前最新 code-only 发布包 `release-20260620-current-head-prod-target-v7` 已在测试服和正式服完成发布。测试服三角色真实验收保持通过；正式服已完成构建、precheck、`preflight-release` 只读证据、真实 `deploy-release`、远端 `IMAGE_TAG` 与入口验证，且未影响 `website` 运行态。

关键结果：

- 测试服三角色真实验收最终通过，证据 `evidence/post-release-role-e2e-1781939411338.json`
- 后端发布阻塞根因已完成 3 轮修复并提交到后端仓 `9667a05ff2`
- 最新正式候选包 `release-20260620-current-head-prod-target-v7` 已成功上传 NAS 并通过正式服 precheck
- 正式服 `deploy-release` 已成功完成，远端 `.env` 为 `IMAGE_TAG=release-20260620-current-head-prod-target-v7`
- 正式服 `http://172.30.30.57:48081/actuator/health`、`http://172.30.30.57:8081/`、`http://172.30.30.57:8081/pdfjs/pdf.worker.mjs` 均返回 `200`
- 正式服 `intruoyi-website` 仍为 `nginx:1.27-alpine` 且保持 `Up 2 weeks`，本次 code-only 发布未触碰 Website/MinIO 数据边界

## 最终验证

- `GREEN: build-release-prod-v7 -> PASS`
- `GREEN: prod-deploy-precheck-v7 -> PASS`
- `GREEN: prod-preflight-release-dry-run-v7 -> PASS`
- `GREEN: deploy-release-prod-v7 -> PASS`
- `GREEN: prod-runtime-http-and-image-tag-v7 -> PASS`
- `GREEN: prod-website-boundary-v7 -> PASS`
