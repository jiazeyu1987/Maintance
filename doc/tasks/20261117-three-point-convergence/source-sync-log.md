# 发布后来源同步分析
实际入口：intruoyi_runtime_agent.deploy负责维护态发布，reopen会再次替换backend容器，因此来源必须在finish_reopen正常backend健康、public frontend启动后绑定，不能在deploy阶段冻结容器ID。

发现：profile当前无来源控制器/配置/运行.env字段；sourceBinding必须显式配置，禁止猜测57路径。Runtime.call会将agent和依赖Python源码注入远端，新增模块必须同步注入。

上一轮source_binding_stage.py生成capture、objects/versionPins、writer evidence、baselineTarget、sourceConfigurations/sourceProgramPolicies新不可变代次；source_binding_activate.py持source锁，核systemd原PID/config pin且无子进程，再切换指定service。必须完整参数化这些行为，不能只改.env。

重试：当前reopen强制maintenance=true；如果正常backend启动后的来源同步失败，不能盲目重跑reopen，需按同candidate和实际imageID/容器身份进入明确补同步路径。完成回执必须同时证明.env版本、实际writer IDs、capture preflight、新controller pin实际激活；只调用外部命令或写待办JSON不算同步成功。

初始状态：分析完成时尚未生产改动或服务器写入；以下记录后续实现进度。

BDD source binding: Given explicit controller/source/service/runtime paths and new healthy containers, When opening release, Then persist new source generation, synchronize IMAGE_TAG, activate controller and verify receipt; repeated call must reuse exact generation, source drift must fail. Implementation delegated to binding_impl, no remote writes.

## 正式入口实现与验证

- BDD: Given 正常后端已经启动而来源同步失败，When 同一候选重试 reopen，Then 仅允许持久标记的 releaseTag、镜像、实际 backend ID 一致时重试；漂移拒绝，不重复替换 backend。
- BDD: Given 同步函数抛错，When finish_reopen 调用，Then 错误传播、不得返回成功、保留验收容器和绑定重试证据。
- RED: `python -X utf8 -m unittest test_source_binding_entry` 初始 2 个用例失败，实际入口缺少 synchronize 调用、远端传输缺少新模块。
- GREEN: 实现 finish_reopen 调用、Runtime.call 模块注入，2 个入口用例通过。
- REGRESSION: 加入实际 reopen / finish_reopen 函数的临时文件与边界单元测试；`python -X utf8 -m unittest test_direct_release test_source_binding_entry` 共 23 PASS。
- 测试运行路径：`C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`，PYTHONPATH 使用已有 `C:/SpugHandoff/convergence-test-deps`、`C:/Spug/runtime/private/prod-incremental-to-two-targets-20261106/test-dependencies` 和本工作区 release-center。首次回归因 psutil 不在路径而导入失败，复用既有隔离依赖后通过；未安装全局依赖。
- 新增私密 profile 示例和配置说明，普通无来源绑定配置发布不猜服务器，不把 NOT_CONFIGURED 当来源同步完成。
- 当前仅本机实现，无服务器写入，无发布，无 Git 提交。

## 来源生成与激活模块验证

- BDD: Given 明确来源、控制器及发布容器绑定，When 发布后同步，Then 更新唯一 IMAGE_TAG 并保留原权限/属主，生成实际服务和配置的完整新代次，持来源锁切换控制器并核对真实进程配置 pin；失败不生成成功回执。
- BDD: Given 部分准备失败或激活失败，When 同一版本重试，Then 保留失败 attempt，未完成准备另建 attempt；完成准备复用 staging receipt，已激活时不重复重启；版本回退仍替换同一个正式 dropin。
- RED: `python -B -m unittest test_release_backup_source -v` 初始模块缺失失败；无配置测试暴露 Windows 提前导入 fcntl；阶段重试测试因 create_attempt 未实现失败。
- RED: Linux 容器运行权限保持测试得到 mode 0600 != 0640；跨应用来源测试未抛出 APPLICATION_MISMATCH。均已修复。
- GREEN / REGRESSION: `docker run --rm --network none -v C:/SpugHandoff/converge-20261117/ops/spug/release-center:/work:ro -w /work python:3.12-bookworm python -B -O -m unittest test_release_backup_source linux_release_backup_source_check -v`：13 PASS。-O 模式下保留显式身份检查，无依赖 assert。
- 验证使用真实临时文件、Linux flock、真实子进程及 /proc 配置参数；systemd、Docker 运行态边界是受控测试替身，不属于线上 E2E。完整 stage 的真实生产数据生成及真实 systemd 服务切换仍须后续部署后验证，不宣称服务器已同步。
- stage 正式生成 capture/objects/version/writer evidence/baselineTarget/owner/control 全链；保留非应用服务身份及挂载。固定 zz-release-source-binding.conf 原子替换，仅接受当前模块生成且指向当前 pin 的旧内容，并保留 previous-dropin.json。若既存更晚 systemd dropin 覆盖，本次实际 pin 核对会明确失败，需部署配置时整理该服务的旧发布覆盖项。
- 修改文件：release_backup_source.py、test_release_backup_source.py、linux_release_backup_source_check.py；无服务器操作、无 Git 提交。
- 最终审查 BDD: Given 前次中断遗留固定名临时文件，When 再次同步 IMAGE_TAG，Then 本次使用同目录独立随机临时文件完成原子替换，仅清理本次文件，保留旧证据。RED: 单测 test_abandoned_temporary_file_does_not_block_retry 得到 FileExistsError。GREEN / REGRESSION: 同上 Docker Python -O 命令，14 PASS；已改为 mkstemp 和 finally 定向清理。
- BDD: Given 来源同步和验收容器清理已成功，When 再次 reopen，Then 不复用已消费的绑定重试标记、不重复切换来源。RED: `test_completed_acceptance_consumes_binding_retry_marker` 1 FAIL（缺标记移除）；GREEN/REGRESSION: `python -X utf8 -m unittest test_direct_release test_source_binding_entry test_release_backup_source` 27 PASS。
- 父审查后补全生命周期：验收容器删除成功即移除 pending 标记；失败保留。完成后的 reopen 拒绝盲目重开，需核对运行态；同步模块自己的相同代次重试保持幂等。
- 锁审查：`ops/backup_engine/formal/minimal_capture_worker.py:155` 的 Runtime.preflight 只选择工具并记录事件，sourceLockPath/flock 在独立 capture()（212/218）；旧 `ops/recovery/minimal_capture_worker.py` 的 preflight 同样不取锁。来源同步持锁后调用 preflight 不会重复获取来源锁。
- 最终模块合入后的 REGRESSION: `python -X utf8 -m unittest test_direct_release test_source_binding_entry test_release_backup_source` 29 PASS；`git diff --check` PASS。本机实现可集成；线上部署与私密 profile 配置未执行。
- 临时文件重试修复后的最终回归：同一 Windows 命令 30 PASS，`git diff --check` PASS；Linux `-O` 14 PASS（见下方子模块记录）。本机实现 ready_for_closeout，由父任务统一提交/融合。
