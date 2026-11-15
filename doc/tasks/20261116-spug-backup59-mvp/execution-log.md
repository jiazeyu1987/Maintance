# 最终融合工作区执行记录

此文件只记录独立融合子任务；父开发工作区已有真实部署/恢复执行日志，最终收口必须合并保留双方记录，不覆盖父日志。

- GREEN: experience-preflight -> PASS；固定int_main25fe7ed及任务bcaf0e3，仅迁入0bbf939之后任务差异，工作区final-integration，禁止部署/合主线/清理。
- BDD: 主线已有首版入口和独立修复 -> Given主线基线，When迁入后续空目标/恢复去重实现，Then只含本任务增量且主线既有语义保留。
- `git worktree add -b codex/spug-backup59-mvp-final-integration C:/Spug/runtime/private/spug-backup59-mvp-20261116/local-install/final-integration 25fe7edc47ee1cba9a4b85bcdc892d7819ea107e` -> PASS。
- `standard_sources()+safe_fixes()` -> PASS；两冲突精确解决，未导入部署base额外改动。
- GREEN: Python `-B -X utf8 -m unittest ops.spug.test_prepare_target ops.spug.test_prepare_target_http ops.spug.test_prepare_target_native ops.spug.test_prepare_target_registration`，PYTHONPATH=ops/spug -> 46 tests PASS。
- GREEN: Node `--test ops/spug/smallapp-ui/prepare-target.test.cjs ops/spug/smallapp_ui_safety.test.cjs` -> 82 PASS。
- GREEN: Python `-B -X utf8 -m unittest discover -s doc/tasks/20261116-spug-backup59-mvp -p test_verify_restored_counts.py` -> 2 PASS。
- Linux已有python:3.12-bookworm，--network none --rm，源码/Git/既有local-test-deps只读挂载，无组件安装。首次载体未设GIT_DIR导致Git路径错误，修正容器映射后进入实际测试。
- REGRESSION: pytest test_backup_target_mounts.py及test_backup_variants.py筛选target_mounts、safe_registered_main_archive_inputs、standard_selected_chain_avoids、standard_final_archive_step、standard_keeps_original_code_except_reviewed_fixes_and_archive_names、standard_physical_result -> 11 PASS/1 FAIL；唯一失败为主线原HEAD可复现的10项构建allowlist遗漏。
- GREEN: 父批准精确补齐已生成模块allowlist，复跑test_standard_keeps_original_code_except_reviewed_fixes_and_archive_names -> 1 PASS；之前11项无新增受影响变化，无重复运行。
- `git diff --cached --check` -> PASS。工作区产生本任务融合提交后保留待审，不合回int_main、不删除；父后续v12增量另行合入本工作区。
- GREEN: v12差异bcaf0e3..31a670f精确三文件通过bytes传递git apply --3way --index -> PASS无冲突。现有Linux隔离载体test_prepared_database_readback.py -> 4 passed in 3.26s，其他已PASS组未重跑。实际恢复健康检查失败待后续修复，最终融合/发布仍未完成。
- GREEN: v13差异31a670f..c4fa257通过bytes传递git apply --3way --index -> PASS无冲突。Linux test_prepared_service_health.py -> 5 passed in 4.22s；Python unittest ops.spug.test_prepare_target_native -> 28 tests PASS。未重复数据库或其它已PASS组；只提交独立融合工作区，不部署/合主线/清理。
