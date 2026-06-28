BDD: 发布说明变更项中文正常显示 -> Given 发布脚本在 PowerShell 5.1 环境执行 / When 生成 release changeSet / Then "发布包" 与 "组件范围" 中文项写入 manifest 时不出现乱码。
BDD: 前端静态发布说明与 manifest 保持一致 -> Given 发布脚本生成 release-info.json 与 release-manifest.json / When 写入相同 changeSet / Then 两处变更项使用同一安全文本来源且不会因源码编码解释而变成乱码。

GREEN: experience-preflight -> PASS，已读取 `D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-agent-checklist.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`，本次仅做本机源码与静态测试修改，不执行真实发布或服务器写入。
RED: release-change-items-encoding-analysis -> FAIL，定位到 `ops/deploy/publish-int-ruoyi.ps1` 为 UTF-8 无 BOM，`New-ReleaseChangeSetManifest` 直接使用中文字面量 `"发布包"`、`"组件范围"`；在 Windows PowerShell 5.1 下脚本源码默认按 ANSI 解释，生成的 changeSet 中文项会写入乱码。
GREEN: release-change-items-unicode-safe-script-fix -> PASS，已在 `ops/deploy/publish-int-ruoyi.ps1` 新增 `ConvertTo-ReleaseUnicodeText`，将发布说明中的中文标签改为码点安全构造，避免 PowerShell 5.1 误按 ANSI 解释无 BOM 脚本中的中文字面量。
GREEN: python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_package_slimming.py -q -> PASS
GREEN: node D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\publish_release_info_contract.test.mjs -> PASS
GREEN: python -X utf8 -m pytest D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_package_slimming.py D:\ProjectPackage\Int\IntRuoyiMaintance\scripts\tests\test_release_sql_preflight_gate.py -q -> PASS
GREEN: task-closeout-preview-requested -> PASS，按收尾规范准备执行 `task-closeout-cleanup` preview，再进行本地提交与推送前置检查。
GREEN: python -X utf8 C:\Users\BJB110\.codex\skills\task-closeout-cleanup\scripts\task_closeout.py --task-id 20260628-release-change-items-garbled-fix --mode preview -> PASS, status=ready, keep={task.md, execution-log.md}, delete/block/warning 均为空
