# 20260806-head-test-only-release Verification Report

## Status

completed

## Required Gates

- 构建产物只包含冻结 HEAD 已提交代码。
- 测试服务器发布成功。
- 测试服真实运行态检查通过。
- 运行控制台显示当前版本号和变更说明。
- 所有问题已记录。
- 发布成功后已沉淀为前置经验。

## Final Result

- PASS: 最终有效 releaseTag 为 `release-20260806-intmain-head-test-r260806c-r1`；失败 releaseTag `r260806a-r1`、`r260806b-r1`、`r260806b-r2` 均已判废且未复用。
- PASS: 构建来源固定为 r260806c clean release worktree；维护 HEAD=`c1b10cc3a20fd5f4f5d228219ae4c046ad320256`，主程序 HEAD=`19173d2b41442e6b2df3c16c424c11713b3dbbcc`，主工作区 dirty 内容未进入构建输入。
- PASS: r260806c migration policy gate 通过，`migrationCount=444`；Spring constructor gate 通过，`MesTeamLeaderProcessConfigServiceImpl` public 生产构造函数存在 `@Autowired`。
- PASS: 维护控制台构建成功，Maven tests `26` passed，jar SHA256=`05f39a3e8d090833cbb4127fa5724a9baac63715750273211fe2c7f0a3ab5116`。
- PASS: build-release operation `op-2026-08-06T131808382264900Z-1a134a91-d2eb-434d-b0a6-b0da5018a2f7` 为 `SUCCESS`；发布包目录为 `E:\Int\CacheData\IntRuoyi\publish-int-ruoyi\release-20260806-intmain-head-test-r260806c-r1`。
- PASS: Manifest validation 通过；`manifest.json` / `release-manifest.json` / image tar 存在，artifact count=`458`，missing=`0`，mismatch=`0`，sourceRepos 均为 `19173d2b41442e6b2df3c16c424c11713b3dbbcc` 且 `dirty=false`。
- PASS: 版本号与变更说明可追溯到目标 releaseTag；Manifest v1 与 frontend release-info 均包含 `changeSet.summary`、`changeSet.component=intruoyi`、发布包和组件范围。
- PASS: publish-test preview 指向 `Environment=test`、`ServerHost=172.30.30.58`、`RemoteAppDir=/opt/intruoyi/runtime`，未触发 `mark-tested`、`promote-prod`、`promote-backup`。
- PASS: publish-test operation `op-2026-08-06T134301524868800Z-58d50c52-dab5-43b8-8ce9-81849d0c96ef` 为 `SUCCESS`。
- PASS: 测试服真实运行态通过；`.env IMAGE_TAG`、backend/frontend 实际镜像 tag 均为 `release-20260806-intmain-head-test-r260806c-r1`，两个容器 running，backend health=`UP`，frontend HTTP=`200`，页面 title=`瑛泰管理系统`。
- PASS: release-info、release lock 和 migration 状态通过；lock=`APPLIED`，当前 releaseTag migration failed/running=`0`，sourceRepos dirty=false。
- PASS: Playwright 页面验收通过；测试服前端登录页可见，运行控制台 HTTP 200，点击“查看变更”后显示当前 releaseTag、发布包、组件范围和变更说明，console errors/failed requests 均为 0。
- PASS: 已记录 I001-I013 问题；可前置化问题已写入 `docs/release-build-preflight-lessons.md`、`docs/test-release-preflight.md`、`docs/powershell-preflight-lessons.md` 和 `docs/experience-index.md`。
- PASS: closeout 完成；48181 已恢复主维护路径 PID=`35236` 且 health=`UP`，r260806c maintenance/app release worktree 与 state dir 的 Git 注册和物理路径均已清理，最终远端 postcheck 仍为 PASS。

## Evidence

- 维护 release worktree：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260806c\m`。
- 主程序 release worktree：`D:\IntRuoyiWorktree\r260806c-release-app`。
- runtime-control state dir：`D:\ProjectPackage\Int\IntRuoyiWorktrees\r260806c-state\runtime-control`。
- Migration policy evidence：`doc/tasks/20260806-head-test-only-release/migration-policy-gate-r260806c.json`。
- Spring constructor evidence：`doc/tasks/20260806-head-test-only-release/spring-constructor-gate-r260806c.json`。
- Build evidence：`build-release-operation-final-r260806c-r1.json`、`build-release-log-tail-r260806c-r1.redacted.txt`。
- Manifest evidence：`manifest-validation-r260806c-r1.json`、`manifest-summary-r260806c-r1.json`。
- Publish evidence：`publish-test-preview-gate-r260806c-r1.json`、`publish-test-operation-final-r260806c-r1.json`、`publish-test-log-tail-r260806c-r1.redacted.txt`。
- Remote runtime evidence：`remote-release-precheck-r260806c-r1.txt`、`remote-release-postcheck-r260806c-r1.json`、`remote-release-postcheck-r260806c-r1.txt`。
- Browser evidence：`playwright-runtime-console-r260806c-r1.json`，截图位于 `output\playwright\r260806c-release\`。

## No-Go Items Avoided

- 未从 dirty 主工作区构建。
- 未复用失败 releaseTag。
- 未执行 `mark-tested`。
- 未执行 `promote-prod`。
- 未执行 `promote-backup`。
- 未发布正式服或备份服。

