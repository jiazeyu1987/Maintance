"""Temporary migration routine lifecycle must retain row scope checks."""
import pathlib
import sys
import unittest
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ops/backup_engine/formal'))
from formal_binlog_scope import RowEventScope, inspect_binlog_scope


def query(scope, sql):
    scope.observe('Anonymous_Gtid', 'SET @@SESSION.GTID_NEXT= ANONYMOUS')
    scope.observe('Query', 'use `app`; ' + sql)


class TemporaryRoutineTests(unittest.TestCase):
  def test_lifecycle_across_log_rotation(self):
    class Events:
      database_log_mode = 'FILE_POSITION'
      def query(self, sql):
        filename = 'binlog.000001' if '000001' in sql else 'binlog.000002'
        statement = ('CREATE DEFINER=`root`@`localhost` PROCEDURE `migrate`() BEGIN SELECT 1; END'
                     if filename.endswith('1') else 'DROP PROCEDURE migrate')
        return (f'{filename}\t4\tAnonymous_Gtid\t1\t20\tSET @@SESSION.GTID_NEXT= ANONYMOUS\n'
                f'{filename}\t20\tQuery\t1\t40\tuse `app`; {statement}\n')
    segments = [dict(file=f'binlog.{n:06}',startPosition=4,stopPosition=40) for n in (1,2)]
    proof = inspect_binlog_scope(Events(), segments, 'app', guard=lambda: None, deadline=time.monotonic()+10)
    self.assertEqual([1,1], [p['ddlEventCount'] for p in proof['segments']])
    self.assertEqual([[],[]], [p['affectedTables'] for p in proof['segments']])

  def test_closed_temporary_migration_procedure(self):
    scope = RowEventScope('app', 'FILE_POSITION')
    query(scope, 'DROP PROCEDURE IF EXISTS migrate_roles')
    query(scope, 'CREATE DEFINER=`root`@`localhost` PROCEDURE `migrate_roles`()\nBEGIN\n UPDATE roles SET enabled=1;\nEND /* xid=19 */')
    scope.observe('Anonymous_Gtid', 'SET @@SESSION.GTID_NEXT= ANONYMOUS')
    scope.observe('Query', 'BEGIN')
    scope.observe('Table_map', 'table_id: 7 (app.roles)')
    scope.observe('Update_rows', 'table_id: 7 flags: STMT_END_F')
    scope.observe('Xid', 'COMMIT /* xid=20 */')
    query(scope, 'DROP PROCEDURE migrate_roles /* xid=21 */')
    scope.complete()
    self.assertEqual(scope.row_count, 1)
    self.assertEqual({'roles'}, scope.affected_tables)

  def test_nested_handler_and_condition_definition(self):
    scope = RowEventScope('app', 'FILE_POSITION')
    query(scope, "CREATE DEFINER=`root`@`localhost` PROCEDURE `migrate`() BEGIN DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END; IF (SELECT COUNT(*) FROM roles)=0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='missing'; END IF; UPDATE roles SET enabled=1; END")
    query(scope, 'DROP PROCEDURE migrate')
    scope.complete()
    self.assertEqual(set(), scope.affected_tables)

  def test_unclosed_definition_rejected_at_range_end(self):
    scope = RowEventScope('app', 'FILE_POSITION')
    query(scope, 'CREATE DEFINER=`root`@`localhost` PROCEDURE `migrate`() BEGIN SELECT 1; END')
    with self.assertRaises(Exception):
      scope.complete()

  def test_cursor_loop_migration_definition(self):
    scope = RowEventScope('app', 'FILE_POSITION')
    query(scope, "CREATE DEFINER=`root`@`localhost` PROCEDURE `migrate`() BEGIN DECLARE done INT DEFAULT 0; DECLARE required_id BIGINT; DECLARE items CURSOR FOR SELECT id FROM roles; DECLARE CONTINUE HANDLER FOR NOT FOUND SET done=1; OPEN items; item_loop: LOOP FETCH items INTO required_id; IF done=1 THEN LEAVE item_loop; END IF; UPDATE roles SET enabled=1 WHERE id=required_id; END LOOP; CLOSE items; END")
    query(scope, 'DROP PROCEDURE migrate')
    scope.complete()
    self.assertEqual(set(), scope.affected_tables)


  def test_unproven_routine_statement_rejected(self):
    for sql in ('DROP PROCEDURE other.migrate_roles','CALL migrate_roles()',
                "PREPARE stmt FROM 'DELETE FROM roles'",
                'CREATE DEFINER=`root`@`localhost` PROCEDURE `other`.`migrate_roles`() BEGIN SELECT 1; END',
                'CREATE DEFINER=`root`@`localhost` PROCEDURE `migrate`() BEGIN SELECT 1; END; DROP TABLE roles; BEGIN SELECT 1; END',
                'CREATE DEFINER=`root`@`localhost` PROCEDURE `migrate`() BEGIN CALL evil(); END',
                'CREATE DEFINER=`root`@`localhost` PROCEDURE `migrate`() BEGIN SELECT * FROM other.roles; END'):
      with self.assertRaises(Exception):
        query(RowEventScope('app', 'FILE_POSITION'), sql)


if __name__ == '__main__':
    unittest.main(verbosity=2)
