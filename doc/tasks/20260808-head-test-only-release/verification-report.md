# Verification Report

## Scope

仅测试服发布验证；禁止正式服、备份服和 mark-tested/promote 操作。

## Results

- PASS: 构建来源固定为维护仓 HEAD `c1b10cc3a20fd5f4f5d228219ae4c046ad320256` 与主程序 HEAD `a6bc1f0cff77fe18e45212ce539c4f76fec65b64`，两个 release worktree 均 clean。
- PASS: build-release operation `op-2026-08-07T162053494032800Z-9ac3afad-085b-4399-8e67-885e4675b954` SUCCESS，manifest/sourceRepos/artifact hash/release-info 校验通过。
- PASS: publish-test operation `op-2026-08-07T163451475350300Z-1bf52485-98a1-4558-8899-fc19c58cda83` SUCCESS；未执行 `mark-tested`、`promote-prod`、`promote-backup`。
- PASS: 测试服 `.env IMAGE_TAG`、backend/frontend 实际镜像 tag、容器 running、backend health `UP`、frontend HTTP `200`、release-info、release lock `APPLIED`、migration failed/running `0` 均匹配 `release-20260808-intmain-head-test-r260808a-r1`。
- PASS: Playwright Chrome 真实页面验收通过；测试服前端 HTTP 200，运行控制台页面显示当前 releaseTag、发布包、组件范围和变更说明。
- PASS: 本次新增问题已沉淀到 `docs/test-release-preflight.md`、`docs/release-build-preflight-lessons.md`、`docs/powershell-preflight-lessons.md` 和 `docs/experience-index.md`。
- PASS: closeout cleanup 已完成；48182 不再监听，r260808a 维护/主程序 release worktree 与 state dir 已删除且两仓 worktree registry 不含本轮路径。
- PASS: 最终测试服远端复核仍通过；`.env IMAGE_TAG`、backend/frontend 镜像、容器 running、backend health `UP`、frontend HTTP `200`、release-info dirty=false、release lock `APPLIED`、migration failed/running `0` 均匹配 `release-20260808-intmain-head-test-r260808a-r1`。

## Blockers

- 暂无。
