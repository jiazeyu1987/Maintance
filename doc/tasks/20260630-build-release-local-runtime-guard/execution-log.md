# 20260630 build-release 本地运行态保护门禁执行日志

GREEN: experience-preflight-20260630-build-release-local-runtime-guard -> PASS，已读取并命中 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\experience-index.md`、`D:\ProjectPackage\Int\IntRuoyiMaintance\docs\release-build-preflight-lessons.md`、`D:\ProjectPackage\Int\IntRuoyi\docs\release-backup-restore.md` 与 `D:\ProjectPackage\Int\IntRuoyiMaintance\docs\agent-memory\project-error-prevention.md`；确认本轮目标是把本地运行态保护收口为脚本门禁，而不是继续依赖手工写 guard。

GREEN: runtime-control-operation-audit-20260630 -> PASS，只读核对 `D:\ProjectPackage\Int\IntRuoyiMaintance\runtime\runtime-control\op-2026-06-30T010216635859800Z-d1bcfb21-29af-4f88-946d-cfa903f15cf9.json` 与对应日志后确认，当次真实页面记录中只有 `build-release` operation，没有第二条显式 `/restart` operation；因此当前收口重点应放在“阻断旁路本地重启入口抢占 48081”，而不是继续假设 `build-release` 自己追加了 restart。

BDD: build-release 自动保护本地运行态 -> Given 本机主线 `48081` 正在为真实本地验证服务 When 维护控制台执行 `build-release` Then 发布脚本必须自动持有 `local-runtime-restart.guard`，阻止旁路本地重启脚本抢占运行态。

BDD: build-release 结束后释放自持有 guard -> Given 发布脚本为本次 `build-release` 新建了 guard When 构建成功或失败结束 Then 脚本必须只释放自己创建的 guard，不得误删外部已有 guard。
