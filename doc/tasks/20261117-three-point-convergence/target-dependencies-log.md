BDD: Given an incremental point has an archived parent with fileStorage policy, When the dependencies stage prepares it, Then resolve the pinned parentPointPins before cleanup and inherit only the matching application/source policy; reject cycles, changed pins and mismatched identities.

BDD: Given formal capture retained images metadata in semantic-capture/provided-<original-path-sha256>.bin, When the original source file no longer exists, Then the packaged restore guard and source program resolver use that archive copy while preserving the original version pin identity; changed bytes, missing or duplicate copies fail. A version pin already listed directly in payloadPins uses that declared archived file without fallback.

RED: initial test_prepare_point_policy -> missing resolve_point_policy. Initial recovery source suite after strict archive wiring -> 9 failures because old unit fixtures stored metadata outside declared payloads. Fixtures now declare directly archived metadata; a disk-backed case explicitly deletes the original metadata and validates archived resolution, then changes archive bytes and confirms rejection.

GREEN: explicit bundled Python -m pytest ops/recovery/test_recovery_version_copies.py scripts/tests/test_recovery_program_source.py scripts/tests/test_recovery_archive_versions.py -q -> 61 passed.

REGRESSION: explicit bundled Python -m unittest discover -s ops/spug -p test_prepare*.py -> 55 passed. PYTHONPATH uses existing offline test dependencies; no global install or remote writes.

Implemented formal entries: NativePreparation.dependencies resolves authoritative pinned ancestry from installed owner.recoveryPoints; generated standard restore runtime guard selects archive copies; resolve_source_program reads the same archive copies. The package allowlist and native lease fixture include the new reviewed module/metadata payload contract. Parent owns final Linux packaged regression and integration.

Scope: this resolves metadata at restore construction and fileStorage during preparation, without adding a second full restore validation engine to the empty-target preparation stage. Existing static point registration remains the selection source; no new registration UI or server deployment is claimed.
