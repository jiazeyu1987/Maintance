# 20260724 推送维护仓到 GitHub - Verification Report

## Result

completed

## Evidence

- 原始本地 HEAD：`fe182434475d27200054c9991232d1418c15fd50`
- 清理后隔离克隆 HEAD：`9978c0837a5176e4e951c35a8c87625e39930ca6`
- 首次推送失败：`doc/tasks/20260709-codeonly-three-env-head-release/evidence/build-release-v5-result.json` 为 `372.63 MB`，超过 GitHub `100.00 MB` 单文件限制。
- 本地确认：`git ls-tree -l HEAD doc/tasks/20260709-codeonly-three-env-head-release/evidence/build-release-v5-result.json` 报告 blob `52f78ba7ed90c9da81d65caf39e53e29d6055207`，大小 `390728434`。
- 历史清理：隔离克隆使用 `git filter-branch --index-filter` 从所有可达提交移除该路径，并清理 `refs/original`、reflog 和不可达对象。
- 大文件扫描：清理后 `int_main` 可达 blob 无超过 `100 MB` 的对象。
- 推送验证：`git push https://github.com/jiazeyu1987/IntRuoyiMaintance.git int_main:int_main` 成功。
- 远端验证：`git ls-remote --heads https://github.com/jiazeyu1987/IntRuoyiMaintance.git int_main` 返回 `refs/heads/int_main`，最终远端引用以实时验证结果为准。

## Notes

- 当前主工作区仍保留原始未重写历史和既有未确认改动；本次为避免触碰脏工作区，推送在隔离克隆中完成。
