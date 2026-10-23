"""Regression coverage for real smallapp startup DDL in incremental backups."""
import pathlib
import re
import sys
import pytest

ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'ops/backup_engine/formal'))
from formal_binlog_scope import scoped_table_ddl,RowEventScope,scoped_database_ddl,event_rows


def test_actual_smallapp_startup_ddl():
    source=(ROOT/'ops/rehearsal-app/backend/src/main/java/cn/intruoyi/rehearsal/LabService.java').read_text(encoding='utf8')
    statements=re.findall(r'db.execute\("(CREATE TABLE IF NOT EXISTS [^"]+)"\)',source)
    assert len(statements)==3
    scope=RowEventScope('rehearsal','FILE_POSITION')
    for sql in statements:
        scope.observe('Anonymous_Gtid','SET @@SESSION.GTID_NEXT= ANONYMOUS')
        scope.observe('Query','use `rehearsal`; '+sql+' /* xid=19 */')
    scope.complete()
    assert scope.ddl_count==3
    assert scope.affected_tables=={'lab_user','lab_record','lab_attachment'}


@pytest.mark.parametrize('sql,default',[
 ('CREATE TABLE child (id BIGINT, INDEX(id))','rehearsal'),
 ('CREATE TABLE child (id BIGINT, UNIQUE KEY (id))','rehearsal'),
 ('CREATE TABLE child (id BIGINT, CONSTRAINT fk FOREIGN KEY (id) REFERENCES rehearsal.parent(id))','rehearsal'),
 ('CREATE TABLE rehearsal.child (id BIGINT, FOREIGN KEY (id) REFERENCES parent(id))',None),
 ('CREATE TABLE child (id BIGINT AUTO_INCREMENT, PRIMARY KEY(id)) ENGINE=InnoDB AUTO_INCREMENT=5','rehearsal'),
])
def test_bounded_same_database_definitions(sql,default):
    assert scoped_table_ddl(sql,'rehearsal',default)=='child'


@pytest.mark.parametrize('sql',[
 'CREATE TABLE child (id BIGINT, FOREIGN KEY (id) REFERENCES other.parent(id))',
 'CREATE TABLE other.child (id BIGINT, FOREIGN KEY (id) REFERENCES rehearsal.parent(id))',
 'CREATE TABLE child (id BIGINT) AS SELECT * FROM other.parent',
 'CREATE TABLE child LIKE other.parent',
 'CREATE TABLE child (id BIGINT); DROP TABLE parent',
 'CREATE TABLE child (id BIGINT, INDEX ((id + 1)))',
 'CREATE TABLE child (id BIGINT, FOREIGN KEY (id) REFERENCES parent(id) ON DELETE CASCADE)',
 'CREATE TABLE child (id BIGINT, FOREIGN KEY (id) REFERENCES parent(id) /* ignored */)',
 'CREATE TABLE child (id BIGINT, FOREIGN KEY (id) REFERENCES parent(id)) DATA DIRECTORY = \'/tmp\'',
 'GRANT ALL ON *.* TO stranger',
 'INSERT INTO child VALUES (1)',
])
def test_unknown_or_out_of_scope_statements_still_rejected(sql):
    with pytest.raises(Exception):
        scoped_table_ddl(sql,'rehearsal','rehearsal')


@pytest.mark.parametrize('sql',[
 'DROP DATABASE `rehearsal`',
 'CREATE DATABASE `rehearsal`',
 "ALTER DATABASE `rehearsal` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT ENCRYPTION='N'",
])
def test_same_database_replacement_marks_every_table_for_observation(sql):
    scope=RowEventScope('rehearsal','FILE_POSITION')
    scope.observe('Anonymous_Gtid','SET @@SESSION.GTID_NEXT= ANONYMOUS')
    scope.observe('Query',sql+' /* xid=4 */');scope.complete()
    assert scope.affected_tables=={'*'} and scope.ddl_count==1


@pytest.mark.parametrize('sql',[
 'DROP DATABASE `other`','CREATE DATABASE mysql',
 'DROP DATABASE rehearsal; DROP DATABASE mysql',
 'CREATE DATABASE rehearsal /*!99999 unsafe */',
 'ALTER DATABASE rehearsal READ ONLY=1',
])
def test_database_ddl_rejects_other_schemas_or_unknown_options(sql):
    with pytest.raises(Exception):scoped_database_ddl(sql,'rehearsal')


def test_raw_mysql_multiline_ddl_is_one_event_with_its_original_bytes():
    ddl='CREATE TABLE `t` (\n  `id` bigint NOT NULL,\n PRIMARY KEY (`id`)\n) ENGINE=InnoDB'
    raw='binlog.000001\t4\tQuery\t1\t123\tuse `rehearsal`; '+ddl+'\n'
    rows=event_rows(raw,'binlog.000001')
    assert len(rows)==1 and rows[0].split('\t',5)[5]=='use `rehearsal`; '+ddl
    assert scoped_table_ddl(ddl,'rehearsal','rehearsal')=='t'


def test_database_reset_observation_includes_all_remaining_tables():
    from formal_data_evidence import affected_table_scope
    schema=dict(catalog={'TABLES':[['a','BASE TABLE'],['b','BASE TABLE'],['v','VIEW']]})
    assert affected_table_scope(schema,['*'])==['a','b']


@pytest.mark.parametrize('action',['DISABLE','ENABLE'])
def test_exact_mysqldump_index_wrapper(action):
    assert scoped_table_ddl('/*!40000 ALTER TABLE `lab_record` '+action+' KEYS */','rehearsal','rehearsal')=='lab_record'
