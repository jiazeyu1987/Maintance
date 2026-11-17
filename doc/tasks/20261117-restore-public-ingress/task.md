# 恢复目标公开网页入口

## Goal
用户能够通过 http://172.30.30.59:8081/index 访问已恢复应用，后续同配置重新准备空目标仍可沿用入口。

## Milestones
- [x] 确认内部200、外部超时、internal网络及防火墙缺口。
- [ ] 生成持久systemd socket/proxyd配置，定向测试。
- [ ] 固定提交，安装到.59，真实公开地址登录验证。
- [ ] 融合验证，提交证据并清理自有worktree。

## Expected Verification
配置推导前端地址，绑定单一主机8081；不公开数据库等端口。实际入口/index及静态资源200，真实浏览器登录/业务页面成功。原5容器身份和数据不变。

## 经验门禁
Trigger：恢复后公开入口不可达。Preflight check：真实8081、内部HTTP、Docker端口、firewalld、现有proxyd和原容器ID。Blocker：前端内部失败或目标配置不匹配。Verification：单位测试和实际公开地址浏览器。Forbidden action：不以SSH隧道代替公开入口验收，不重做恢复、不改业务库、不关闭防火墙。Evidence：父任务execution-log及本任务执行日志。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，提供独立持久网页入口，从已登记准备配置推导稳定地址，不依赖临时隧道或容器ID。
- 是否存在临时补丁或绕过：否，使用已有systemd-socket-proxyd，不安装新组件。

## Current Status
in_progress：原恢复已成功，公开入口验收重新打开。仅改变网页接入，不改变恢复数据和容器身份。
