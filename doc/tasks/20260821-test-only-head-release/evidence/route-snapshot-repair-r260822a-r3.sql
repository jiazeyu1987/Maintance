-- route snapshot repair for test server only
-- packageReleaseTag: release-20260822-intmain-head-test-r260822a-r2
-- repairIteration: r3
-- targetHost: 172.30.30.58
-- targetDatabase: ruoyi-vue-pro
-- scope: mes_pro_route_version.id=3, scheduleConfigs[0..3] only
-- formal mapping:
-- 900124 -> 926785 (historical processId 900331 -> current processId 922894, B010 -> Z2630, sort 1)
-- 900125 -> 926786 (historical processId 900333 -> current processId 922895, B030 -> Z3710, sort 2)
-- 900126 -> 926787 (historical processId 900370 -> current processId 922896, PROC-XLSX-00001 -> Z2775, sort 3)
-- 900127 -> 926788 (historical processId 900371 -> current processId 922897, PROC-XLSX-00002 -> Z2772, sort 4)
SET SESSION sql_mode = IF(FIND_IN_SET('NO_BACKSLASH_ESCAPES', @@SESSION.sql_mode), @@SESSION.sql_mode, CONCAT_WS(',', @@SESSION.sql_mode, 'NO_BACKSLASH_ESCAPES'));
START TRANSACTION;
UPDATE mes_pro_route_version
SET route_snapshot_json = JSON_SET(
        route_snapshot_json,
        '$.configSnapshots.scheduleConfigs[0].routeProcessId', 926785,
        '$.configSnapshots.scheduleConfigs[1].routeProcessId', 926786,
        '$.configSnapshots.scheduleConfigs[2].routeProcessId', 926787,
        '$.configSnapshots.scheduleConfigs[3].routeProcessId', 926788
    ),
    route_snapshot_sha256 = NULL,
    route_snapshot_format_version = NULL,
    update_time = NOW()
WHERE id = 3;
COMMIT;
