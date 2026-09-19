# Verification Report

## Result

PASS

## Package Verification

- `releaseTag`：`release-20260723-dcc-viewer-permission-r260723vp-r1`
- `component`：`intruoyi`
- `publishScope`：`code-only`
- 后端提交：`2d7fabf8263f3a5410f334bd177ea492e06b098b`
- 前端提交：`4c6c01e824c0af5dca9df082141449ef1402ca03`
- Git 状态：两个 source repo 均为 `dirty=false`

## Test Server Runtime

- `.env IMAGE_TAG`：`release-20260723-dcc-viewer-permission-r260723vp-r1`
- 后端镜像：`intruoyi-backend:release-20260723-dcc-viewer-permission-r260723vp-r1`
- 前端镜像：`intruoyi-frontend:release-20260723-dcc-viewer-permission-r260723vp-r1`
- 后端健康：`{"status":"UP"}`
- 前端首页：HTTP `200`
- PDF worker：`/pdfjs/pdf.worker.mjs` -> `200 application/javascript`

## DCC Viewer Verification

- 账号：测试服 `芋道源码/wangsiyu`，凭据在执行记录中脱敏。
- 目标路径：`/dcc/controlled-file/detail/2054545668044081212?viewer=1&from=project-code`
- 权限基线：拥有 `dcc:controlled-file:query`、`dcc:project-code:query`；不拥有 `form:instance:create`、`dcc:controlled-file:signature:manage`。
- 预览元数据：HTTP `200` / `code=0`
- PDF 预览：HTTP `200` / `application/pdf`
- 原始误触接口：`/form-center/actions/active-instance` 未调用；`/dcc/electronic-signatures/page` 未调用。
- 页面结果：未出现“没有该操作权限”；无失败 admin API；预览布局可见；未出现 `2054545668044081200` 精度截断 ID。

## Remaining Work

无。
