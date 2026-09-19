# 20260723 DCC 受控浏览权限弹窗测试服发布

## Task Goal

将已修复的 DCC 受控浏览 viewer 模式前端提交发布到测试服务器，并用真实账号验证 `DCC项目代码 -> 数显球囊扩张压力泵 -> 详情 -> 文件 -> 受控浏览` 对应的受控文件 viewer 不再触发“没有该操作权限”。

## Current Status

completed

## Scope

- 环境：测试服 `172.30.30.58`
- 发布包：`release-20260723-dcc-viewer-permission-r260723vp-r1`
- 范围：`Component=intruoyi`，`publishScope=code-only`
- 后端提交：`2d7fabf8263f3a5410f334bd177ea492e06b098b`
- 前端提交：`4c6c01e824c0af5dca9df082141449ef1402ca03`
- 禁止范围：不执行 `mark-tested`、不发布备份服、不发布正式服、不做备份/恢复。

## Milestones

- [x] 核对发布门禁和测试服访问边界。
- [x] 构建 code-only 发布包并上传 NAS。
- [x] 校验发布包 manifest、sourceRepos 提交和 dirty 状态。
- [x] 发布到测试服并验证远端运行态。
- [x] 使用真实浏览器和 `wangsiyu` 账号验证受控浏览 viewer。
- [x] 清理本任务 worktree 与临时凭据配置。
- [x] 标记任务完成。

## 经验门禁

- PowerShell 门禁：已读取 `docs/powershell-memory.md`；命令使用显式 UTF-8，不使用 `&&`，长任务不以单一退出码替代运行态证据。
- 发布门禁：已读取 `docs/release-backup-restore.md`；发布后以远端 `.env`、Docker 镜像、健康检查、前端 HTTP 和业务 E2E 共同验收。
- 服务器门禁：已读取 `docs/server-access.md`；本轮只触达测试服 `172.30.30.58`，未触达备份服和正式服。
- 登录门禁：已读取 `docs/login-access.md`；真实 E2E 前先执行官方 `login-preflight.mjs`。
- 高风险动作门禁：已记录并满足 `GREEN: experience-preflight -> PASS` 后执行测试服发布和真实浏览器验证。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；viewer 模式跳过管理态接口，且保留受控预览权限与 viewer token 机制。
- 是否存在临时补丁或绕过：否。

## Expected Verification

- 发布包 manifest 证明 `releaseTag`、`publishScope`、`component` 与前后端提交一致。
- 测试服 `.env IMAGE_TAG`、前后端镜像 tag 与发布包一致。
- 后端 `/actuator/health` 返回 `UP`，前端首页返回 `200`，PDF worker 返回 `200 application/javascript`。
- `wangsiyu` 登录 `芋道源码` 后访问目标受控文件 viewer：
  - `/preview-metadata` 返回 `code=0`
  - `/preview` 返回 `200 application/pdf`
  - 不调用 `/form-center/actions/active-instance`
  - 不调用 `/dcc/electronic-signatures/page`
  - 不出现“没有该操作权限”
  - 不出现 `2054545668044081200` 精度截断 ID

## Evidence

- 构建日志：`build-release.out.log`
- Manifest 校验：本地发布包 `manifest.json` / `release-manifest.json`
- 运行态验证：远端 `.env`、Docker inspect、health、HTTP、PDF worker
- 浏览器证据：`artifacts/post-release-controlled-viewer/probe-preview-headers-result.json`
- 断言证据：`artifacts/post-release-controlled-viewer/assert-controlled-viewer-result.json`
