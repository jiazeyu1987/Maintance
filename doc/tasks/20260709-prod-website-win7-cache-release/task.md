# 正式服展厅 Win7 按需缓存网页包发布

## 任务目标

将 `D:\ProjectPackage\Website\dist` 中已本机验证的展厅前端包发布到正式服 `http://172.30.30.57:8083/`，修复 Win7 Hall 客户端打开正式服后 `Failed to fetch` 的问题。

## 里程碑

1. 完成正式服发布前置门禁与任务记录。
2. 确认正式服 8083 当前部署方式、容器/目录和回滚点。
3. 备份当前正式服 8083 静态网页包。
4. 发布本机最新 Website dist 到正式服 8083。
5. 验证正式服 URL、脚本 marker、Hall 客户端首屏加载结果。

## 预期验证

- `http://172.30.30.57:8083/` 返回最新 dist 中的 `assets/index-B4q8uOAb.js` 或等价新 hash。
- 正式服 JS 包包含 `medical-kiosk-win7-attachment-local-paths` 与 `productAttachmentDownloadProgress`。
- Hall 客户端日志不再出现启动后后台拉 `stages/TEST/assets/award-*audio*` 导致 `Failed to fetch`。
- 桌面 Hall 快捷方式可打开正式服展厅首页。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，发布已验证的按需缓存前端包，而不是修改快捷方式或手工屏蔽错误。
- 是否存在临时补丁或绕过：否。

## 当前状态

Completed。

## 最终验证结果

- 正式服 `http://172.30.30.57:8083/` 已发布新版 Website dist，入口引用 `assets/index-B4q8uOAb.js`。
- `intruoyi-website` 容器已重启，使 bind mount 指向新版 dist。
- Win7 客户端已重新打包并通过桌面快捷方式访问正式服；用户确认最终链路可用。