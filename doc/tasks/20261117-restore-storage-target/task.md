# 空目标文件存储连接适配

## Goal
完成既定六步的附件验收。恢复后、应用启动前，把明确指定的文件配置连接到目标MinIO；保持原备份、业务附件、文件配置ID/bucket/domain及其它字段不变。

## Milestones
- [x] 真实预览失败定位：host.docker.internal无法解析，源凭据与目标MinIO不一致。
- [x] BDD/RED：指定配置的endpoint/accessKey/accessSecret适配，非指定行不变，缺配置拒绝。
- [x] GREEN/REGRESSION：最小适配实现及实际SAFE封包接入。
- [x] 固定提交构建安装、通过原恢复流程执行、真实附件验收。
- [x] 合并验证、记录及自有工作区清理。

## Expected Verification
单测覆盖字段保持及错误暴露；真实目标只读核对适配结果；Spug恢复成功后真实登录、8表基线和3附件字节/SHA验证。历史失败保留。

## 经验门禁
Trigger：空目标恢复后的附件API code500。Preflight check：当前目标a316/ce917、原生成功、真实DESCRIBE infra_file_config已核；只操作授权.59，目标MinIO连接来自当前配置的服务及secret pins。Blocker：不能明确配置ID、bucket或目标身份时不写。Verification：实际封包调用和原生结果、真实预览内容。Forbidden action：不改源库、原始备份、正式NAS或本机受保护展厅；不伪造旧操作成功；秘密不进入日志/命令参数。Evidence：主execution-log附件验收及inspect_file_endpoint59.py只读结果。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，恢复生命周期执行目标连接适配，不手工改库充当功能完成。
- 是否存在临时补丁或绕过：否。

## BDD
Given空目标已恢复数据和对象且应用未启动，When执行显式文件配置适配，Then仅指定配置的目标endpoint和凭据更新，原ID/bucket/domain及附件不变，并记录脱敏回执。
Given配置不在显式范围或缺失，When适配，Then不修改无关配置，缺失配置报错。

## Current Status
completed：089a267已安装并融合维护仓，合并后67测试/20子测试通过。本轮9ddf恢复成功，endpoint指向目标MinIO，实际Docker secret核对accessMatches/secretMatches均true。8表、登录、版本通过；两图片真实页面及SHA通过、PDF对象206586字节/SHA通过。PDF页面不可见与正式源数据缺少受控/生效时间及项目归属一致，用户已确认保持最小范围并记录历史问题，不扩大历史迁移。两个纯构建worktree已删除，开发worktree已删除，历史PDF按用户明确范围记录。
