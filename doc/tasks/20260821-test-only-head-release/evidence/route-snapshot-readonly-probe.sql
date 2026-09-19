DESCRIBE mes_pro_route_version;
SELECT id,
       tenant_id,
       route_id,
       JSON_UNQUOTE(JSON_EXTRACT(route_snapshot_json, '$.routeId')) AS snapshot_route_id,
       JSON_LENGTH(JSON_EXTRACT(route_snapshot_json, '$.configSnapshots.flowGraph.nodes')) AS node_count,
       JSON_LENGTH(JSON_EXTRACT(route_snapshot_json, '$.configSnapshots.productBoms')) AS bom_count,
       JSON_UNQUOTE(JSON_EXTRACT(route_snapshot_json, '$.configSnapshots.productBoms[0].processId'))
           AS bom0_process_id,
       JSON_UNQUOTE(JSON_EXTRACT(route_snapshot_json, '$.configSnapshots.productBoms[0].routeProcessId'))
           AS bom0_route_process_id,
       JSON_KEYS(JSON_EXTRACT(route_snapshot_json, '$.configSnapshots.productBoms[0]')) AS bom0_keys
FROM mes_pro_route_version
WHERE id IN (3, 5, 110, 448)
ORDER BY id;

SELECT id, name, status, deleted
FROM system_tenant
WHERE id IN (1, 122)
ORDER BY id;

SELECT route_id, COUNT(*) AS bom_rows,
       SUM(process_id IS NULL) AS null_process_id,
       SUM(process_id = 0) AS zero_process_id,
       MIN(process_id) AS min_process_id,
       MAX(process_id) AS max_process_id
FROM mes_pro_route_product_bom
WHERE route_id IN (900025, 900026, 922119)
GROUP BY route_id
ORDER BY route_id;

DESCRIBE mes_pro_route_product_bom;
