# Verification Report

## Result

PASS：已只读确认 `zhaojie` 看不到排产工单删除按钮的直接原因是账号权限投影不包含 `mes:pro-schedule-order:delete`。

## Evidence

- 前端按钮：`v-hasPermi="['mes:pro-schedule-order:delete']"`；仅对 `removedFromSchedule=false` 的行渲染。
- 后端接口：删除和删除影响预览均以同一 permission 做 `@PreAuthorize`。
- 真实页面：`芋道源码/zhaojie` 登录成功，排产工单页加载 20 行，删除按钮 0 个，页面无权限错误。
- 权限响应：排产相关权限包含 query/create/update/admission-diff/preflight/manual-finish，不包含 delete。
- 测试服数据库：删除菜单存在且启用；目标账号全部有效角色均无该菜单绑定。
- 正式角色配置：`mes_scheduler` 白名单不包含菜单 5586，当前运行态符合角色边界。

## Conclusion

当前不是发布失败或前端显示错误。`zhaojie` 的“排产员”角色没有被授予高风险的排产工单删除能力，因此前端隐藏按钮，后端也会拒绝无此权限的删除请求。若业务要求排产员可以删除，应另行批准正式权限变更，将精确 permission 纳入 `mes_scheduler` 的正式角色白名单并完成回归和 fresh 登录验证；不应直接去掉前端权限控制。

## Safety

本次未点击删除、未修改权限、角色、菜单、工单或服务器配置；证据中不包含密码、token 或 Cookie。
