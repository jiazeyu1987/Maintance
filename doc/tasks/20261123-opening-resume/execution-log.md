# Execution log

BDD: Normal backend with stopped public frontend and matching opening marker uses registered acceptance entry for observation, health and login; public entry required once public frontend starts. Missing/stale/wrong marker cannot grant acceptance entry.
RED: python -X utf8 -B -m unittest test_pending_opening_entry -> FAIL, missing state-aware verification_entry. Production behavior already reproduced by JOB-477c786a34 (public HTTP200 required before opening).
Worktree C:/SpugHandoff/release/opening-resume-20261123, baseline f179c8b, branch codex/opening-resume-20261123.

GREEN/REGRESSION: unittest test_pending_opening_entry test_technical_verification test_intruoyi_runtime test_resume_test_tail ->88PASS. Corrected fixture RuntimeBlocked exception type and supplied required stagingRoot to startup timing fixture. Covers opening-marker identity refusal, public entry after frontend runs, existing startup deadlines and executor login entry selection.

BDD: Released application source generation -> Given verified new application image on the same registered network with changed IP, When staging source generation, Then update application service address and exactly its published writer allowlist entry; data services and unknown/ambiguous network identity remain rejected. Live evidence: baseline backend .11, current verified .8, one old writer reference; imports pass and empty attempt exists. No fallback; update new generation only, preserve old pins.

RED: unittest test_source_address ->5 errors, missing refresh_application_address. GREEN/REGRESSION: test_source_address test_source_runtime test_source_binding_entry test_release_runtime_metadata test_runtime_metadata_entry ->27PASS. New application generation updates the unique IPv4 address only on the same registered network IDs, carries exact writer allowlist replacement; data services remain unchanged. Old generation pins not edited.
