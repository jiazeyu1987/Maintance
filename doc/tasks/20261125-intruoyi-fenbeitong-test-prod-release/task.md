# IntRuoyi 测试服与正式服发布

## 目标与范围

用户明确授权将当前 IntRuoyi 修复发布到测试服务器和正式服务器。前序分贝通运行时地址修复任务已 completed。本任务固定已提交的目标源码，使用本次专用临时发布 worktree 构建单一 releaseTag，先发布测试服并验收，再晋级正式服；不发布分贝通助手或审查服务器。

## Current Status

completed

## 里程碑

- [x] 建立任务并确认前序已完成、测试及正式发布已获授权。
- [x] 读取发布门禁，核对源码、执行器、远端真实版本、锁和恢复依据。
- [x] 在新建专用 worktree 构建并固定同一发布包。
- [x] 发布测试服，核运行态、版本与真实登录页面。
- [x] 晋级正式服，核同包运行态、版本与真实登录页面。
- [x] 收口证据、删除任务自有 worktree、核验稳定控制台路径；最终记录按独立提交归档。

## 预期验证

两服发布操作均为 SUCCESS；manifest、远端 .env IMAGE_TAG、前后端实际镜像 tag 与同一 releaseTag 一致；后端 health=UP、前端 HTTP 200；真实浏览器登录后验证发布版本、变更说明与分贝通页面的运行时地址。缺少必需依赖、恢复依据或验收失败时准确阻断，不冒报成功。

## 固定输入与进度

最终releaseTag：2026-11-26-01-52-12；源码：eb866bbaf4ea1b1c6db93daa63e77576766c3684；维护执行源码：ea06ce8983d2330f9fab478551209582c11582fe。构建、测试发布、mark-tested、正式晋级和正式开放均succeeded。两服实际双镜像相同、IMAGE_TAG匹配、UP/HTTP200、非维护、来源绑定pending已消费，三个阶段数据库合同均PASS；测试、正式维护入口和正式普通入口真实页面均PASS_WITH_OBSERVATIONS。详见verification.md和release-result.json。

发布中补齐SQL登记/只读预检（6a099294a0b045f59b4f3896e06c20f1486a35e3），修复分贝通票据未绑定签发租户导致匿名回调缺上下文（最终源码提交）。两项实现均已验证、提交、合入int_main；主线无关脏文件保持。初次未登记SQL构建失败、第二包分贝通503和探针定位/网络事件失败均完整保留于execution-log.md及独立证据，不混入最终包成功历史。

已验证真实登录、排产入口和实际空列表、分贝通本服票据与认证iframe、可见版本和变更说明。两服助手字段映射未保存、部分租户注册证提醒配置缺失仍保留；财务同步/生成/记账及工作台初始化不在已通过范围。各窗口末尾新发起的工作台来源目录GET明确记为未验证，不伪造响应成功。

本轮6个自有worktree均已删除，物理路径和Git登记均无残留；SQL和租户实现已融合int_main并验证，slot9/10已释放。稳定执行器PID 29472、argv和cwd核验通过，私密配置字节保持；其它任务资源保持。最终证明见local-closeout-proof.json。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；使用已验证并提交的运行时地址合同及正式发布流程。
- 是否存在临时补丁或绕过：否。

## 经验门禁

- Trigger：同一 IntRuoyi 发布包部署测试服并晋级正式服，涉及构建、服务器写入与 worktree 收尾。
- Preflight check：先读 server-access、login-access、release-backup-restore、release-agent-checklist、worktree-memory 及命中的发布配置经验；确认目标已提交、执行器同源、环境显式 URL、迁移合同、锁和恢复依据。高风险动作前在 execution-log.md 写入 GREEN 或 BLOCKER。
- Blocker：源包/迁移合同、实际运行身份、恢复依据、环境配置、真实登录验收中任何具体必需项无法证明时，仅阻断对应动作；跨机器本地历史缺失不直接要求重导包。
- Verification：单一 releaseTag 的 build-release、publish-test、mark-tested、promote-prod；同时核操作、manifest、IMAGE_TAG、实际双镜像、后端健康、前端 HTTP 与真实页面；清理后核 Git 注册、物理目录与控制台路径。
- Forbidden action：禁止将脏工作区或未跟踪文件放入包、拼接不同 releaseTag、改写历史成功、泄露凭据、操作其它任务资源、删除或卸载正式 /mnt/nas；不扩大为审查服务器或分贝通助手发布。
- 维护生成缓存门禁：清理前同时核ordinary status和ignored清单；未知缓存必须证明与受控源码完整编译结果一致，保留原始拦截和派生证明后精确删除，再使用原正式清理器，不扩大白名单。
- Evidence：本目录 execution-log.md、脱敏发布回执、页面与运行态证据、worktree 目标提交及清理记录；命令意图和结果同步 request-command-log。
