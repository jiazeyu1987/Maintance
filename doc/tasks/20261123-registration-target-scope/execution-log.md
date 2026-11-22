# Execution log

BDD: Given historical failed effects on test/backup, When submitting prod-only registration, Then leave those records untouched and permit prod observation. Same-target, unknown-target, all-target and active-worker protections remain.
RED: python -X utf8 -B -m unittest test_target_registration -> FAIL, 8 tests, 2 expected errors: Failed remote effects require reconciliation before registration for test/backup history. Initial fixture missing packages was corrected before recording this behavior RED.
Worktree: C:/SpugHandoff/release/registration-scope-20261123; baseline int_main 7ad37a8; branch codex/registration-target-scope-20261123. No application package rebuild required; maintenance executor only.

GREEN: unittest test_target_registration -> PASS (8 tests). REGRESSION: unittest test_target_registration test_origin_audit_closure test_release_recovery -> PASS (37 tests, includes cross-target remote operation refusal). Existing Python tar extraction deprecation warning retained; no runtime failure.

Runtime first installation retained idle history; registration rejected by old rehearsal maintenance record (no job dispatched). BDD: nonselected maintenance must not prevent selected registration; selected maintenance/unknown must reject. RED: 10 tests, 1 expected Pending maintenance error. GREEN/REGRESSION: 38 tests PASS after selected-target maintenance scope correction.
