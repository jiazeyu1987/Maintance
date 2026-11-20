# 测试发布元数据尾部续办

## Current Status
ready_for_closeout

## 目标与里程碑
在既有原失败作业、发布包、迁移台账、备份及原容器校验之后，仅对绑定当前正常运行容器的 runtime-opening-pending 尾部续办。先 RED、再实现、再定向回归。主线程负责统一记录、提交和收尾。

## 设计约束检查
- 是否引入 fallback/降级/吞异常：否。
- 是否从根因和长期维护角度解决：是，沿用既有续办入口和完成回执。
- 是否存在临时补丁或绕过：否。

## 经验门禁
- 发布脚本契约先于环境排查；仅明确标记、包和实际运行身份匹配才续办，未知必须阻断。
- 保留原包、原备份和原容器；续办不得重跑迁移或重新备份。
- 原工作进程活跃、镜像或容器身份漂移、schema/ledger变化必须阻断。
- 本项仅本地代码与单元回归，不执行服务器、E2E、发布、安装或提交；显式 UTF-8 读写。

## BDD 与预期验证
- Given 原测试发布在正常入口开放后元数据对齐失败且完整证据匹配，When 从原失败作业续办，Then 只完成 finish_reopen 并产生 completed receipt，零迁移 SQL、零重新备份。
- Given 正常健康但缺少 pending 证据或 marker/容器身份/原快照不一致，When 续办，Then 阻断并不调用 finish_reopen。
- Given 原 worker 或历史续办 worker 活跃，When 续办，Then 阻断。
- Given 尾部再次失败，When 新 retry job 重试，Then 继续同一原失败作业且原件保持不变。

## 执行证据
- RED：新增原失败作业尾部续办和再次失败重试两个测试，`python -X utf8 -m unittest test_resume_test_tail.ResumeTailTest.test_runtime_metadata_tail_resumes_original_failure_without_replacing_or_sql_writes test_resume_test_tail.ResumeTailTest.test_runtime_metadata_tail_failure_retries_with_unchanged_previous_receipt` -> 1 error + 1 failure，均被旧 `Public frontend must remain stopped` 规则挡住，符合预期。
- GREEN：新分支复用原失败作业、原包、备份、迁移台账、原容器、维护后端快照核验，绑定 runtime-opening-pending / deployment-pending / business-opened 与正常前后端、原验收资源。只调用 finish_reopen 并形成既有 completed receipt；原作业及原包/备份/快照字节不变，迁移与备份函数零调用，SQL 仅既有 SELECT 台账读取。
- 新 marker 本轮尚未安装，因此强制包含 frontendId，不兼容缺 frontendId 的新 marker；legacy backup-source-binding marker 保持原 3 字段合同。BDD：Given 同镜像前端被另一个容器替换，When 元数据 intent 尚未形成就重试，Then marker 身份不符阻断。
- 第二轮 RED：`python -X utf8 -m unittest test_runtime_metadata_entry` -> 2 errors，旧 marker 未记录 frontendId、旧检查不接受新合同。GREEN：新增前端 ID 写入与校验后通过。
- REGRESSION：`python -X utf8 -m unittest test_resume_test_tail test_test_tail_adapter test_sealed_origin_resume test_release_runtime_metadata test_runtime_metadata_entry test_source_binding_entry test_release_backup_source test_rehearsal_tail` -> 82 tests PASS，exit 0。覆盖缺标记、pending 漂移、正常后端/前端配置漂移、同镜像容器替换、schema/ledger 漂移、metadata intent 身份漂移、验收资源归属、健康失败、活跃 worker、再次失败及原回执保持。
- 一次扩大回归命令误用了不存在的 test_runtime_metadata / test_source_binding 模块，明确记录 ImportError；查实际模块名后以上标准命令重新运行通过，不以包装退出码掩盖测试失败。
- 仅修改 intruoyi_runtime_agent.py、test_resume_test_tail.py、test_runtime_metadata_entry.py 及本记录；无服务器、安装、提交动作。父线程负责最终完整回归、实现提交与 worktree 收尾。
