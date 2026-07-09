# 执行日志

BDD: 正式服 Hall 首屏加载 -> Given 桌面 Hall 快捷方式指向 `http://172.30.30.57:8083/` 且正式服发布最新 Website dist / When 用户双击 Hall 快捷方式 / Then 客户端加载正式服展厅首页，不再出现 `展厅数据加载失败 Failed to fetch`。
GREEN: experience-preflight -> PASS，已读取 `docs/powershell-memory.md`、`docs/server-access.md`、`docs/login-access.md`、`docs/release-backup-restore.md`、`docs/experience-index.md`；用户已明确授权正式服发布操作。
GREEN: local-website-build -> PASS，
pm run build 成功，dist index 引用 $jsName，JS 包包含 medical-kiosk-win7-attachment-local-paths、productAttachmentDownloadProgress、openReleaseAsset。
GREEN: prod-website-readonly-probe -> PASS，正式服存在 intruoyi-website nginx 容器，8083 暴露，宿主目录 /opt/intruoyi/runtime/website 可读。
GREEN: prod-website-container-remount -> PASS，重启 intruoyi-website 后容器内 /usr/share/nginx/html/index.html 已从旧 ssets/index-DkOAEWrq.js 切换为 ssets/index-B4q8uOAb.js。
GREEN: prod-http-marker-verify-after-restart -> PASS，http://172.30.30.57:8083/ 当前引用 ssets/index-B4q8uOAb.js，远端 JS 包包含 Win7 本地路径缓存与下载进度 marker。
GREEN: hall-formal-shortcut-smoke -> PASS，桌面 Hall 快捷方式启动后日志出现 load_end: status=200 url=http://172.30.30.57:8083/，未出现 Failed to fetch、screen=\"kiosk-error\" 或 esource_load_failed。
GREEN: formal-website-publish -> PASS，正式服 `http://172.30.30.57:8083/` 已服务新版 `assets/index-B4q8uOAb.js`，并验证新版 marker 存在。
GREEN: win7-client-final-confirmation -> PASS，Win7 Hall 客户端重新打包后通过桌面快捷方式访问正式服，用户确认“已经可以了”。