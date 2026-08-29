# r260829k timed test-only release timing summary

- releaseTag: release-20260829-timed-head-test-r260829k-r2
- failedReleaseTag: release-20260829-timed-head-test-r260829k-r1
- maintenanceHead: eb1193f1e3dec75ed87cb01a10464a05e2e91d60
- appHead: 3892f88f00d30aa06a4be6c5bd48f9e55ed6203c
- buildOperationId: op-2026-08-29T094711769603400Z-ded24bdd-b6fc-40f1-a43a-79f8a9232111
- publishOperationId: op-2026-08-29T100507230543400Z-9db39d71-d6b4-42f9-a030-61da96fc4c5f

| Segment | Seconds | Minutes | Result |
| --- | ---: | ---: | --- |
| release_worktree_create | 92.541 | 1.54 | completed |
| runtime_control_config | 0.044 | 0.00 | completed |
| maintenance_release_contract_tests | 1.041 | 0.02 | completed |
| runtime_control_build | 274.128 | 4.57 | completed |
| runtime_control_start | 40.902 | 0.68 | completed |
| build_release_preview | 0.180 | 0.00 | completed |
| build_release_operation | 30.172 | 0.50 | failed |
| app_frontend_dependency_prepare_after_r1_failure | 461.456 | 7.69 | completed |
| build_release_preview_r2 | 0.099 | 0.00 | completed |
| build_release_operation_r2 | 840.638 | 14.01 | completed |
| manifest_package_validation_r2 | 0.155 | 0.00 | completed |
| publish_test_preview | 5.438 | 0.09 | completed |
| test_server_pre_publish_status | 1.875 | 0.03 | completed |
| publish_test_operation | 290.605 | 4.84 | completed |
| remote_runtime_verification_r2 | 0.777 | 0.01 | completed |
| runtime_control_release_status_verification | 6.076 | 0.10 | completed |
| playwright_runtime_console_page_verification | 10.074 | 0.17 | completed |
| task_closeout_cleanup_apply | 1.634 | 0.03 | completed |
| release_worktree_git_remove | 25.748 | 0.43 | completed |
| release_worktree_physical_cleanup | 2.238 | 0.04 | completed |
| final_closeout_verification | 0.935 | 0.02 | completed |

- successful core build-release + publish-test: 1,131.243s (18.85 min)
- successful core + verification around publish: 1,155.638s (19.26 min)
- setup before release operations: 408.656s (6.81 min)
- r1 failure + dependency recovery overhead: 491.808s (8.20 min)
- closeout cleanup + verification: 30.555s (0.51 min)
- total measured segments including closeout: 2,086.756s (34.78 min)
- wall clock from worktree create to page verification pass: 3,219.000s (53.65 min)
