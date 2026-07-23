START TRANSACTION;
CREATE TEMPORARY TABLE target_ids (id BIGINT PRIMARY KEY);
INSERT INTO target_ids (id) VALUES (2054545668044045935),(2054545668044045936),(2054545668044045937),(2054545668044045938),(2054545668044045939),(2054545668044045940),(2054545668044045941),(2054545668044045942),(2054545668044045943),(2054545668044045944),(2054545668044045945),(2054545668044045946),(2054545668044045958),(2054545668044045959),(2054545668044045960),(2054545668044045961),(2054545668044045967),(2054545668044045968),(2054545668044045969),(2054545668044045970),(2054545668044045971),(2054545668044045972),(2054545668044045973),(2054545668044045974),(2054545668044045975),(2054545668044045976),(2054545668044045977),(2054545668044045978),(2054545668044045979),(2054545668044045980),(2054545668044045981),(2054545668044045982),(2054545668044045983),(2054545668044045984),(2054545668044045985),(2054545668044045986),(2054545668044045987),(2054545668044045988),(2054545668044045989),(2054545668044045990),(2054545668044045991),(2054545668044046003),(2054545668044046004),(2054545668044046005),(2054545668044046006),(2054545668044046018),(2054545668044046019),(2054545668044046020),(2054545668044046021),(2054545668044046022),(2054545668044046023),(2054545668044046024),(2054545668044046036),(2054545668044046037),(2054545668044046038),(2054545668044046039),(2054545668044046040),(2054545668044046053),(2054545668044046054),(2054545668044046055),(2054545668044046056),(2054545668044046057),(2054545668044046058),(2054545668044046059),(2054545668044046066),(2054545668044046083),(2054545668044046084),(2054545668044046107),(2054545668044046108),(2054545668044046110),(2054545668044046170),(2054545668044046171),(2054545668044046172),(2054545668044046173),(2054545668044046174),(2054545668044046186),(2054545668044046189),(2054545668044046190),(2054545668044046191),(2054545668044046192),(2054545668044046193),(2054545668044046194),(2054545668044046195),(2054545668044046196),(2054545668044046203),(2054545668044046204),(2054545668044046205),(2054545668044046206),(2054545668044046212),(2054545668044046226),(2054545668044046227),(2054545668044046236),(2054545668044046237),(2054545668044046238),(2054545668044046239),(2054545668044046245);
CREATE TEMPORARY TABLE target_file_ids AS
  SELECT DISTINCT source_file_id AS file_id FROM dcc_controlled_file f JOIN target_ids t ON t.id = f.id WHERE source_file_id IS NOT NULL
  UNION SELECT DISTINCT original_file_id FROM dcc_controlled_file f JOIN target_ids t ON t.id = f.id WHERE original_file_id IS NOT NULL
  UNION SELECT DISTINCT published_file_id FROM dcc_controlled_file f JOIN target_ids t ON t.id = f.id WHERE published_file_id IS NOT NULL
  UNION SELECT DISTINCT stamped_file_id FROM dcc_controlled_file f JOIN target_ids t ON t.id = f.id WHERE stamped_file_id IS NOT NULL
  UNION SELECT DISTINCT drawing_pdf_file_id FROM dcc_controlled_file f JOIN target_ids t ON t.id = f.id WHERE drawing_pdf_file_id IS NOT NULL
  UNION SELECT DISTINCT training_record_file_id FROM dcc_controlled_file f JOIN target_ids t ON t.id = f.id WHERE training_record_file_id IS NOT NULL;
CREATE TEMPORARY TABLE other_refs AS
  SELECT f.id AS controlled_id, f.source_file_id AS file_id FROM dcc_controlled_file f WHERE f.id NOT IN (SELECT id FROM target_ids) AND f.deleted = b'0' AND f.source_file_id IS NOT NULL
  UNION ALL SELECT f.id, f.original_file_id FROM dcc_controlled_file f WHERE f.id NOT IN (SELECT id FROM target_ids) AND f.deleted = b'0' AND f.original_file_id IS NOT NULL
  UNION ALL SELECT f.id, f.published_file_id FROM dcc_controlled_file f WHERE f.id NOT IN (SELECT id FROM target_ids) AND f.deleted = b'0' AND f.published_file_id IS NOT NULL
  UNION ALL SELECT f.id, f.stamped_file_id FROM dcc_controlled_file f WHERE f.id NOT IN (SELECT id FROM target_ids) AND f.deleted = b'0' AND f.stamped_file_id IS NOT NULL
  UNION ALL SELECT f.id, f.drawing_pdf_file_id FROM dcc_controlled_file f WHERE f.id NOT IN (SELECT id FROM target_ids) AND f.deleted = b'0' AND f.drawing_pdf_file_id IS NOT NULL
  UNION ALL SELECT f.id, f.training_record_file_id FROM dcc_controlled_file f WHERE f.id NOT IN (SELECT id FROM target_ids) AND f.deleted = b'0' AND f.training_record_file_id IS NOT NULL;
SET @target_rows = (SELECT COUNT(*) FROM dcc_controlled_file f JOIN target_ids t ON t.id = f.id);
SET @target_safe_rows = (SELECT COUNT(*) FROM dcc_controlled_file f JOIN target_ids t ON t.id = f.id WHERE f.tenant_id = 122 AND f.deleted = b'0' AND f.status = 'ACTIVE' AND f.file_number LIKE 'CODEX-E2E%');
SET @target_bad_rows = (SELECT COUNT(*) FROM dcc_controlled_file f JOIN target_ids t ON t.id = f.id WHERE NOT (f.tenant_id = 122 AND f.deleted = b'0' AND f.status = 'ACTIVE' AND f.file_number LIKE 'CODEX-E2E%'));
SET @shared_records = (SELECT COUNT(DISTINCT o.controlled_id) FROM other_refs o JOIN target_file_ids t ON t.file_id = o.file_id);
SET @ok_pre = (@target_rows = 96 AND @target_safe_rows = 96 AND @target_bad_rows = 0 AND @shared_records = 0);
UPDATE dcc_controlled_file f JOIN target_ids t ON t.id = f.id
   SET f.deleted = b'1',
       f.updater = 'codex-prod-backup-rehearsal-20260724',
       f.update_time = NOW()
 WHERE @ok_pre = 1
   AND f.tenant_id = 122
   AND f.deleted = b'0'
   AND f.status = 'ACTIVE'
   AND f.file_number LIKE 'CODEX-E2E%';
SET @updated_rows = ROW_COUNT();
SET @post_deleted_rows = (SELECT COUNT(*) FROM dcc_controlled_file f JOIN target_ids t ON t.id = f.id WHERE f.deleted <> b'0');
SET @post_active_rows = (SELECT COUNT(*) FROM dcc_controlled_file f JOIN target_ids t ON t.id = f.id WHERE f.deleted = b'0');
SET @should_commit = (@ok_pre = 1 AND @updated_rows = 96 AND @post_deleted_rows = 96 AND @post_active_rows = 0);
SELECT 'target_rows', @target_rows;
SELECT 'target_safe_rows_before', @target_safe_rows;
SELECT 'target_bad_rows_before', @target_bad_rows;
SELECT 'shared_records_before', @shared_records;
SELECT 'updated_rows', @updated_rows;
SELECT 'post_deleted_rows_in_tx', @post_deleted_rows;
SELECT 'post_active_rows_in_tx', @post_active_rows;
SELECT 'commit_decision', IF(@should_commit, 'COMMIT', 'ROLLBACK');
SET @commit_sql = IF(@should_commit, 'COMMIT', 'ROLLBACK');
PREPARE stmt FROM @commit_sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;