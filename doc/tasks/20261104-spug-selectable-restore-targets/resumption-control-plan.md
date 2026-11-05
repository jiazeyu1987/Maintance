# 三服登记接续的控制组件修正计划

正式新全量到原测试实例已经完成。本计划仅落实既有“允许安装控制组件和登记配置，不执行恢复”授权，更新.59控制组件；正式服继续先只读核验，不修改业务容器或开放恢复按钮。

## 已证实的当前状态
- .57负载0.60，精确容器inspect恢复正常，原后端/前端及数据服务运行；旧超时原因不再作为当前阻塞。当前后端存在可写bind及Docker socket，MinIO发布9000/9001，超出当前主目标合同的只读配置挂载/数据端口不暴露要求。需要正式支持这些现有运行形态及明确writer控制，不能删除检查或直接登记通过。
- .59自有控制服务active/enabled、旧121文件包摘要通过、无恢复操作/claim/宿主预约；实际dataLimits.max_bytes=64GiB非法，SQL展开64GiB是独立合法上限。另原登记的backend/mysql/minio/redis现在停止，仅frontend运行；本计划不会擅自启动它们，也不会把已登记等同当前可执行。

## 执行步骤
1. 在本任务全新专用发布worktree检出已提交且已验证的04f5f9ce，构建实际SAFE包，运行真实封包合同的容量门禁测试；保持既有Linux195 PASS证据，不重复构造模拟E2E。
2. .59远端只读预检：现有owner/control/service及所有业务ID/PID/StartedAt/pins未漂移，无operation/claim/active reservation；旧配置实际formal.validate_limits必须拒绝64GiB。保存原unit/receipt。
3. .59新不可变engine-readback-04f5f9ce代次、新owner/control文件。owner仅更新formalModuleDirectory与dataLimits.max_bytes=16GiB；target、source、operationsRoot、资源锁/状态目录及SQL64GiB不变。控制器程序pin、PYTHONPATH、systemd ExecStart定向切换至新代次，最后原子更新receipt；仅重启spug-main-restore-59-20261104-v3.service。
4. 逐文件SHA、实际Native配置验证、正式容量验证、认证selections真实预检；原业务全部ID/PID/StartedAt保持、零恢复operation/claim。若原业务仍停止，明确记录对应准入失败，不改业务状态或使用其它实例顶替。
5. 真实Spug登录从全部包清单恢复入口核.58可选；.59按当前真实预检显示结果，.57继续禁用；只确认/返回、零恢复POST。清理本次专属干净发布worktree，核稳定控制路径不依赖发布目录；保存当前具体剩余阻塞。

回退仅可在无已受理操作时将原unit/receipt精确恢复并重载自有控制服务；旧包/配置完整保留。禁止回退到非法配置后声称可恢复，禁止删除操作/claim或共享数据。

## 设计约束检查
- 是否引入fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是；同步已经过真实恢复验证的控制修复，容量语义独立且在访问目标前验证。
- 是否存在临时补丁或绕过：否；不改业务运行形态以满足安装器、不移除正式目标的缺失合同门禁。
