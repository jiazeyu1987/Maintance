# 空目标控制进程启动环境

## Current Status
ready_for_closeout

## 目标、里程碑与预期验证
v6 已完成原生三阶段，但新控制器 selections 缺 jsonschema；实际依赖已在保留的 site-packages 内，配置环境中也已有 PYTHONPATH，生成的 systemd unit 却没有传入环境。按实际配置键修复控制进程启动环境传递，不安装组件，不修改原失败任务。里程碑：实际环境键核对、BDD/RED、最小实现及定向回归、精确提交。

## 经验门禁
- 前一客户端白名单修复已提交并由父任务部署；当前真实闭环未完成，最终验收和收口仍由父任务负责。
- 核真实入口及已有配置所需依赖，不用新增安装掩盖环境丢失；认证不变，不输出原始环境值或凭据。
- 只改当前 integration-worktree 的本任务文件，中文显式 UTF-8；行为变更先 BDD/RED，定向验证通过后提交。
- 本子任务无远端写入或部署；既有失败历史保持。父任务统一记录共享命令日志。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否；正式启动使用已配置环境，不缺省改装依赖。
- 是否从根因和长期维护角度解决：是；构造的控制配置和控制进程实际启动环境必须一致。
- 是否存在临时补丁或绕过：否；不手改运行中进程或旧失败状态，不新增全局环境。

## BDD 与执行证据
- BDD: 控制服务环境传递 -> Given 私密 control 配置含已有依赖的 PYTHONPATH，When 生成并启动控制服务，Then 实际进程使用该配置环境且 selections 可导入现有模块，unit/log 不泄漏秘密。
- 真实根因确认：安装 agent 记录新控制器 PID 没有 PYTHONPATH，缺失模块为 jsonschema；既有 site-packages 已包含该模块。仅诊断进程按配置补入路径后 Native.selections PASS，未修改远端资源。
- 实际配置 environment 键为 LANG、PATH、PYTHONDONTWRITEBYTECODE、PYTHONPATH；所需库位于已保留的本地路径。原认证保持。
- RED: `python -X utf8 -m unittest test_prepare_target_native.NativePreparationTests.test_installed_control_service_receives_private_configuration_environment -q` -> FAIL，真实 install_control 生成 unit 没有 EnvironmentFile。
- GREEN / REGRESSION: `python -X utf8 -m unittest test_prepare_target_native test_prepare_target test_prepare_target_http test_prepare_target_registration -q` -> PASS 43/43；`git diff --check` -> PASS。
- 实现将完整已配置环境写入本次操作目录 control.env，写值前权限置 0600，unit 只保存文件引用。非法变量名/换行明确拒绝，不输出环境值或凭据。没有安装依赖、没有改旧失败记录。

## 工作区与交付
- 工作区：`C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/integration-worktree`；基线 `780a6ee2362aad254452c07197ee082a17ac2d2f`。
- 实现提交：`d52c205cd68bb10c43d899dbcbee93ab3fc85d99`；仅 native 实现、定向测试及安装说明 3 文件。
- 新 release-v7 只需更新 native/pin，不改本机 entry/JS；真实安装、下一次页面准备、最终融合及工作树收口由父任务负责。

## v8：实际 systemd 219 环境文件路径合同
- v7 真实失败：prepare-a1b08336-e0eb-4c5e-8003-5109d19d7516 三阶段成功，登记仍缺 jsonschema。安装 agent 在 journal 发现 systemd 219 将 EnvironmentFile 值的双引号作为路径字符，报路径非绝对并忽略；文件存在且格式正确，但 PID 仍未收到 PYTHONPATH。
- 本次只修 EnvironmentFile 路径输出，实际路径无空格；不引入多版本框架，不安装依赖，不改环境配置或失败历史。
- BDD: 已存在环境文件 -> Given 当前 systemd 219 与无空格的绝对环境文件路径，When 生成 unit，Then EnvironmentFile 右值本身就是该可读取绝对路径，不含被当作路径字符的双引号。
- 预期验证：定向测试读取实际 install_control 生成的 EnvironmentFile 右值，必须精确等于并可打开生成文件；原配置环境/认证保持。
- RED: 单个 install_control 合同用例 -> FAIL，EnvironmentFile 右值含引号及转义，无法直接指向所生成文件。
- GREEN / REGRESSION: 修正单行路径输出后，`python -X utf8 -m unittest test_prepare_target_native test_prepare_target test_prepare_target_http test_prepare_target_registration -q` -> PASS 43/43；`git diff --check` -> PASS。测试读取 unit 指令的精确值并打开文件，不再只断言存在 EnvironmentFile 字样。
- 实现提交 `e5d55946ae20797f42ae0915f5b61c69088f80e5`，基线 `73dfd22ecac09f3ffda9da7070102fdf0676febd`，仅 native 和对应测试；本机未启动 systemd，真实系统加载与下一轮页面准备由父任务安装 v8 验证。
