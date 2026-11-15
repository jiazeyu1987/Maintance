# 新目标控制入口 Pin 修复

## Current Status

ready_for_closeout。定向修复和本地回归完成；接续准备空恢复目标功能，由父任务统一提交、集成和部署。

## 目标与里程碑

1. 核对正式恢复、仓库入口文件名及 wrapper 的实际模块定位方式。
2. BDD / RED：旧模板指向旧引擎时，新控制配置必须选择 engineDirectory 内的正式入口和真实新 Pin。
3. 最小实现并运行定向 GREEN 与 native 模块回归。

## 经验门禁

- 先核脚本和 manifest 契约；不得用猜测目录或新增 fallback 解决入口漂移。
- 仅本地源码和测试；禁止服务器操作、部署、恢复、清理和提交。
- UTF-8 读写；私密输入只取路径和结构，不输出或提交凭据。
- BDD + RED → GREEN → REGRESSION；明确本地验证不等于真实远端验收。
- 固定工作树为 C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/integration-worktree，文件归属仅 ops/spug/prepare_target_native.py、其测试和本记录。

## 设计约束检查

- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，控制入口与选定安装目录绑定，重新计算实际文件 Pin。
- 是否存在临时补丁或绕过：否。

## BDD 场景

Given 控制模板 programPins 指向旧安装、setting.engineDirectory 中有正式 recovery_entry.py 和 repository_entry.py，When 构造新目标控制配置，Then 两个 programPins 精确引用新目录内文件及其真实字节摘要，旧模板保持原样。

Given 选定安装目录缺少其中一个正式入口，When 构造控制配置，Then 明确失败，不沿用旧引擎。

Given 旧 PYTHONPATH 包含旧引擎 control/common/formal 与独立 site-packages，When 重建控制配置，Then 仅按旧入口根目录的精确路径段替换引擎模块路径，保留第三方依赖和仅前缀相似的其它目录。

## 实际契约核对

- `ops/backup_engine/build_package.py` 将同一正式 wrapper 以 repository_entry.py、recovery_entry.py、control_entry.py 三个名称放在包根目录。
- `ops/backup_engine/entry.py` 使用 `Path(__file__).resolve().parent` 作为引擎根，随后从该根下 control/common 加载模块。因此旧 entry Pin 即使搭配新 workingDirectory，也仍加载旧模块。
- 父任务私密观测 live-engine-needed-mappings.private.json 显示恢复/仓库两项 Pin 与 PYTHONPATH 前三项仍指旧引擎；Python、工作目录和 owner formalModuleDirectory 已指新目录。这里只修复仍漂移的两处，不修改已有正确字段或第三方 site-packages。

## TDD 与执行记录

使用 `C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe -X utf8`，工作目录为本文固定 integration-worktree。

- RED: `-m unittest ops.spug.test_prepare_target_native.NativePreparationTests.test_control_uses_selected_engine_entries_and_module_paths ops.spug.test_prepare_target_native.NativePreparationTests.test_control_does_not_reuse_old_entry_when_selected_program_is_missing` -> 2 个用例、3 个失败：仍返回旧入口，缺任一新入口均未失败。
- GREEN: 同一命令 -> 2 tests PASS。实际创建新入口文件并计算 Pin；验证新绝对路径、字节摘要、三项模块路径和独立依赖保留。
- REGRESSION: `-m unittest ops.spug.test_prepare_target_native` -> 25 tests PASS，无 skip。涵盖现有控制配置消费者、服务环境、准备失败断路及资源清理边界。
- 实现仅在 control_document 重新绑定两个正式 programPins，并将继承的 Linux PYTHONPATH 按旧入口根目录边界映射到选定引擎目录；新入口缺失报 PREPARE_CONTROL_PROGRAM_MISSING。
- 更新两个既有控制测试的安装文件夹夹具，提供产品现已要求的实际 recovery/repository entry 文件。
- 未运行服务器动作、打包、部署或真实恢复；未提交。父任务负责源码提交及随后部署验收。
