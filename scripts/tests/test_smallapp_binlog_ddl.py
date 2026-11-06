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
 'CREATE TABLE child (id BIGINT, FOREIGN KEY (id) REFERENCES parent(id) /* ignored */)',
 'CREATE TABLE child (id BIGINT, FOREIGN KEY (id) REFERENCES parent(id)) DATA DIRECTORY = \'/tmp\'',
 'GRANT ALL ON *.* TO stranger',
 'INSERT INTO child VALUES (1)',
])
def test_unknown_or_out_of_scope_statements_still_rejected(sql):
    with pytest.raises(Exception):
        scoped_table_ddl(sql,'rehearsal','rehearsal')


@pytest.mark.parametrize('actions',[
 'ON DELETE CASCADE', 'ON UPDATE CASCADE',
 'ON DELETE CASCADE ON UPDATE CASCADE',
 'ON UPDATE RESTRICT ON DELETE SET NULL',
 'ON DELETE NO ACTION ON UPDATE SET NULL',
])
def test_same_database_foreign_key_actions(actions):
    scope=RowEventScope('rehearsal','FILE_POSITION')
    scope.observe('Anonymous_Gtid','SET @@SESSION.GTID_NEXT= ANONYMOUS')
    scope.observe('Query','use `rehearsal`; CREATE TABLE child (id BIGINT, '
                  'CONSTRAINT fk FOREIGN KEY (id) REFERENCES rehearsal.parent(id) '+actions+') /* xid=42 */')
    scope.complete()
    assert scope.ddl_count==1 and scope.affected_tables=={'child'}


@pytest.mark.parametrize('reference,actions',[
 ('other.parent','ON DELETE CASCADE'),
 ('parent','ON DELETE CASCADE ON DELETE RESTRICT'),
 ('parent','ON UPDATE CASCADE ON UPDATE NO ACTION'),
 ('parent','ON DELETE CASCADE; DROP DATABASE rehearsal'),
 ('parent','ON DELETE CASCADE /* arbitrary */'),
 ('parent','ON DELETE SET DEFAULT'),
 ('parent','ON DELETE CASCADE ON UPDATE (SELECT 1)'),
])
def test_foreign_key_actions_do_not_expand_scope(reference,actions):
    with pytest.raises(Exception):
        scoped_table_ddl('CREATE TABLE child (id BIGINT, FOREIGN KEY (id) REFERENCES '+
                         reference+'(id) '+actions+')','rehearsal','rehearsal')


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


@pytest.mark.parametrize('definition,options',[
 ("`deleted` bit(1) NOT NULL DEFAULT b'0', `updated` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP", "COMMENT='business #1; row'"),
 ("`id` bigint, KEY `idx` (`id`) USING BTREE", 'ROW_FORMAT=DYNAMIC'),
 ("`id` bigint, `active` bigint GENERATED ALWAYS AS ((case when (`id` > 0) then `id` else NULL end)) STORED", ''),
 ("`value` varchar(64), CONSTRAINT `chk` CHECK ((json_valid(`value`) and char_length(trim(`value`)) > 0))", ''),
 ("`value` varchar(64), `key` varbinary(64) GENERATED ALWAYS AS (convert(concat(`value`,_utf8mb4'#INITIAL') using binary)) STORED", ''),
 ("`value` varchar(64), CONSTRAINT `chk` CHECK (regexp_like(`value`,_utf8mb4'^[0-9a-f]{64}$'))", ''),
 ("`value` json DEFAULT (json_object()), `id` bigint, KEY idx (`id`) USING BTREE COMMENT 'index'", ''),
 ("`id` bigint, `g` varchar(64) GENERATED ALWAYS AS (cast(`id` as char charset utf8mb4)) STORED, CHECK (`g` in (_ascii'GLOBAL',_ascii'TENANT'))", ''),
])
def test_original_main_table_definitions(definition,options):
    assert scoped_table_ddl('CREATE TABLE child ('+definition+') ENGINE=InnoDB '+options,'rehearsal','rehearsal')=='child'


@pytest.mark.parametrize('definition',[
 '`id` bigint, CONSTRAINT chk CHECK (other.func(`id`))',
 '`id` bigint, CONSTRAINT chk CHECK (evil(`id`))',
 '`id` bigint, CONSTRAINT chk CHECK (sleep(10))',
 '`id` bigint, CONSTRAINT chk CHECK (utf8mb4(`id`))',
 '`id` bigint, CONSTRAINT chk CHECK (unsigned(`id`))',
 '`id` bigint, CONSTRAINT chk CHECK (signed(`id`))',
 '`id` bigint, CONSTRAINT chk CHECK ((SELECT 1))',
 '`id` bigint, CONSTRAINT chk CHECK (@global_read_only := 0)',
 '`id` bigint, CONSTRAINT chk CHECK (`other`.`id` > 0)',
 "`id` bigint, CONSTRAINT chk CHECK (`id` > 0 /* allowed? */)",
 "`id` bigint, `g` bigint GENERATED ALWAYS AS (load_file('/etc/passwd')) STORED",
 "`id` bigint, `g` bigint GENERATED ALWAYS AS (other.func(`id`)) STORED",
])
def test_table_expressions_cannot_execute_unbounded_sql(definition):
    with pytest.raises(Exception):scoped_table_ddl('CREATE TABLE child ('+definition+')','rehearsal','rehearsal')


@pytest.mark.parametrize('body',[
 "BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Immutable'; END",
 "BEGIN IF NOT (OLD.id <=> NEW.id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Immutable'; END IF; END",
 'BEGIN SET NEW.generation=UUID(); SET NEW.version=1; END',
 "BEGIN IF OLD.version IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Missing'; ELSE SET NEW.version=OLD.version+1; END IF; END",
 "BEGIN DECLARE linked varchar(32); SELECT status INTO linked FROM parent WHERE `id`=OLD.id; IF linked <> 'DRAFT' THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Immutable'; END IF; END",
 "BEGIN DECLARE linked varchar(32); SELECT v.status INTO linked FROM child AS c JOIN rehearsal.parent AS v ON v.id=c.parent_id WHERE c.id=OLD.id; IF linked IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Missing'; END IF; END",
])
def test_local_integrity_trigger_ddl(body):
    scope=RowEventScope('rehearsal','FILE_POSITION')
    scope.observe('Anonymous_Gtid','SET @@SESSION.GTID_NEXT= ANONYMOUS')
    scope.observe('Query','use `rehearsal`; CREATE DEFINER=`root`@`localhost` TRIGGER guard BEFORE UPDATE ON child FOR EACH ROW '+body)
    scope.complete();assert scope.ddl_count==1 and scope.affected_tables=={'child'}


@pytest.mark.parametrize('target,body',[
 ('other.child',"BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='x'; END"),
 ('child','BEGIN SET @global=0; END'),
 ('child','BEGIN SET NEW.id=other.func(); END'),
 ('child','BEGIN CALL external_proc(); END'),
 ('child','BEGIN DELETE FROM other.parent; END'),
 ('child','BEGIN SET NEW.id=sleep(1); END'),
 ('child','BEGIN SET NEW.id=`evil`(1); END'),
 ('child','BEGIN DECLARE linked bigint; SELECT id INTO linked FROM other.parent WHERE id=OLD.id; END'),
 ('child','BEGIN DECLARE linked bigint; SELECT other.func(id) INTO linked FROM parent WHERE id=OLD.id; END'),
 ('child','BEGIN DECLARE linked bigint; SELECT p.id INTO linked FROM parent p JOIN other.secret s ON s.id=p.id WHERE p.id=OLD.id; END'),
 ('child',"BEGIN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='x'; END; DROP TABLE child"),
])
def test_trigger_scope_rejects_external_or_unknown_effects(target,body):
    scope=RowEventScope('rehearsal','FILE_POSITION');scope.observe('Anonymous_Gtid','SET @@SESSION.GTID_NEXT= ANONYMOUS')
    with pytest.raises(Exception):scope.observe('Query','use `rehearsal`; CREATE DEFINER=`root`@`localhost` TRIGGER guard BEFORE UPDATE ON '+target+' FOR EACH ROW '+body)
