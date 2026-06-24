# Execution Log

## BDD

BDD: 发布包注入发布信息 -> Given 构建 code-only 发布包 When 前端 dist 构建完成 Then dist/release-info.json 包含 releaseTag、changeSet、sourceRepos。

BDD: 三环境页面版本一致 -> Given 测试服、正式服、备份服使用同一发布包 When 用户打开业务前端 Then 页面显示的 releaseTag 与远端 IMAGE_TAG 一致。

## RED

RED: node scripts/tests/publish_release_info_contract.test.mjs -> FAIL，发布脚本未生成业务前端 `release-info.json`，manifest changeSet 没有可复用生成函数。

## GREEN

GREEN: node scripts/tests/publish_release_info_contract.test.mjs -> PASS，2 tests passed。

GREEN: powershell scriptblock syntax check -> PASS，`PowerShell syntax OK`。

## BLOCKER

- 暂无。
