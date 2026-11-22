# Execution log

BDD: Normal backend with stopped public frontend and matching opening marker uses registered acceptance entry for observation, health and login; public entry required once public frontend starts. Missing/stale/wrong marker cannot grant acceptance entry.
RED: python -X utf8 -B -m unittest test_pending_opening_entry -> FAIL, missing state-aware verification_entry. Production behavior already reproduced by JOB-477c786a34 (public HTTP200 required before opening).
Worktree C:/SpugHandoff/release/opening-resume-20261123, baseline f179c8b, branch codex/opening-resume-20261123.

GREEN/REGRESSION: unittest test_pending_opening_entry test_technical_verification test_intruoyi_runtime test_resume_test_tail ->88PASS. Corrected fixture RuntimeBlocked exception type and supplied required stagingRoot to startup timing fixture. Covers opening-marker identity refusal, public entry after frontend runs, existing startup deadlines and executor login entry selection.
