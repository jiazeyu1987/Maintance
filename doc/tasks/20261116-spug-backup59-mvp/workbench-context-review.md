# 工作台上下文接口只读审查

## Current Status
completed

## 目标与验证
真实 FULL 恢复和登录已经成功，但验收 runner 将 POST /admin-api/workbench/context 视为业务写入拦截。只读定位已确认主程序源码或现有归档代码，追踪控制器及服务调用，给出是否查询的精确证据；不改服务、业务数据或 runner。

## 经验门禁
- 前序健康/重置修复已提交交父任务，当前是同一验收链只读调查。
- 主程序目录以实际路径证据确认，不沿用旧盘符；只读源码，不凭 HTTP 方法推定写入。
- 密钥、会话和业务数据不输出。当前不需要远端扫描或新安装组件。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，依据接口实际副作用区分查询与业务写入。
- 是否存在临时补丁或绕过：否。

## 结论与源码证据
不能将该接口标为纯只读白名单：它创建查询上下文，包含数据库初始化和 Redis 令牌写入。建议保留拦截，runner 对同一请求的 route/request 事件去重，并区分 blocked request attempt 与实际写入；被拦截不能称为已发生业务 mutation。

- 路径依据：维护仓 `backend/src/main/resources/application.yaml:26` 的 `repo-root: ../IntRuoyi/IntRuoyiBackend`，相对实际主维护仓解析为 `C:/Users/D01021/Documents/ChatGPT/IntRuoyi/IntRuoyiBackend`。该本地仓 HEAD 为 `ebad95af22684d4390ba64a930fd9c96824c68c1`。
- `yudao-server/src/main/java/cn/iocoder/yudao/server/controller/admin/profileworkbench/ProfileWorkbenchTodoController.java:17` 声明 POST /context；27 行转调 service.context。
- 默认 s3 的 `yudao-server/src/main/java/cn/iocoder/yudao/server/profileworkbench/ProfileWorkbenchTodoQueryService.java:49` 调 initializer.initialize；`yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/service/profileworkbench/WorkbenchVisibilityContextInitializer.java:13` 调版本 mapper。
- `yudao-module-system/src/main/java/cn/iocoder/yudao/module/system/dal/mysql/profileworkbench/WorkbenchVisibilityVersionMapper.java:6` 是 INSERT INTO system_workbench_visibility_context ... ON DUPLICATE KEY UPDATE，不能视为 SELECT。
- `yudao-server/src/main/java/cn/iocoder/yudao/server/profileworkbench/WorkbenchQueryTokens.java:42` 创建查询 token；同目录 `RedisWorkbenchTokenStore.java:11` 使用 Redis setIfAbsent 并带过期时间。
- s4 的同目录 `IndexQueryTransaction.java:44-46` 同样初始化上下文，`IndexQueryTokens.java:34` 同样创建 token。因此两种配置都不能无条件宣称无写副作用。
- 以上是实际配置指向的本地源码审查，不声称恢复镜像与该 HEAD 同源；无需扩大为镜像拆包或远端数据库检查。本轮未改产品、runner、服务或业务数据，未运行该接口。父任务可继续已通过的真实登录与附件只读验收。
