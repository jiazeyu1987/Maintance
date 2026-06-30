# 20260630 基于主分支完成测试服务器真实发布闭环执行日志

GREEN: experience-preflight -> PASS，已读取并命中 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\server-access.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\login-access.md`。已确认本轮目标是测试服真实 `build-release -> publish-test` 闭环，并要求完整留痕与经验沉淀。

BDD: 主分支真实发布测试服闭环 -> Given 三仓主分支输入已明确且运行控制台可用 When 真实执行 `build-release -> publish-test` Then 测试服 `.env IMAGE_TAG`、backend/frontend 镜像 tag、backend health、frontend HTTP 必须全部与同一 releaseTag 一致。

BDD: 发布失败必须形成可复用排障材料 -> Given 任一步真实发布失败 When 记录问题并排查 Then 必须保留失败现象、定位过程、根因、修复动作和复验结果，且不得用默认成功、静默跳过或手工改环境掩盖失败。

BDD: 通用问题前移沉淀为事前经验 -> Given 本轮发布暴露出可复用的构建或部署问题 When 发布闭环完成 Then 必须把可前移的问题补到发布前置经验文档，把失败后排障方案保留为事后学习材料。

BLOCKER: main-branch-dirty-precheck-20260630 -> 维护仓 `D:\ProjectPackage\Int\IntRuoyiMaintance` 当前 `git status --short --branch` 显示主分支 `int_main` 存在未跟踪文件 `output/doc/*.xlsx`、`output/doc/*.md`、`output/doc/*.docx`。按当前长期基线，主分支工作区 dirty 时不得默认继续发布，也不得默认切 worktree 规避；需先明确这些文件是否属于本次发布无关临时产物，以及采用何种处理方式后才能继续。

BLOCKER: runtime-control-health-20260630 -> 本机运行控制台 `http://127.0.0.1:48181/actuator/health` 当前请求失败，错误为“无法连接到远程服务器”。影响：在运行控制台恢复前，无法执行真实 `build-release` / `publish-test` 页面动作，本轮发布闭环暂时不能继续。
