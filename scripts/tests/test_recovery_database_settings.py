"""Strict parsing of archived MySQL database attributes; real SQL is tested separately."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'ops' / 'recovery'))
from recovery_data import database_settings
from recovery_engine import RecoveryError


@pytest.mark.parametrize('database,charset,collation,encryption', [
    ('ledger_archive', 'utf8mb4', 'utf8mb4_bin', 'N'),
    ('reporting_archive', 'latin1', 'latin1_swedish_ci', 'N'),
    ('encrypted_archive', 'utf8mb4', 'utf8mb4_0900_ai_ci', 'Y'),
])
def test_reads_archived_attributes(database, charset, collation, encryption):
    definition = [database, f"CREATE DATABASE `{database}` /*!40100 DEFAULT CHARACTER SET {charset} "
        f"COLLATE {collation} */ /*!80016 DEFAULT ENCRYPTION='{encryption}' */"]
    assert database_settings(definition, database) == dict(
        characterSet=charset, collation=collation, encryption=encryption)


@pytest.mark.parametrize('change', [
    lambda value: value.replace('`archive`', '`another_database`'),
    lambda value: value + '; DROP DATABASE other',
    lambda value: value + ' READ ONLY=1',
    lambda value: value.replace('utf8mb4_bin', "utf8mb4_bin; SELECT 1"),
    lambda value: value.replace(" /*!80016 DEFAULT ENCRYPTION='N' */", ''),
])
def test_rejects_unbound_or_unrepresented_settings(change):
    ddl = "CREATE DATABASE `archive` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_bin */ " \
        "/*!80016 DEFAULT ENCRYPTION='N' */"
    with pytest.raises(RecoveryError):
        database_settings(['archive', change(ddl)], 'archive')


def test_rejects_wrong_database_identity():
    with pytest.raises(RecoveryError, match='ARCHIVED_DATABASE_DEFINITION_INVALID'):
        database_settings(['wrong_database', 'CREATE DATABASE `wrong_database`'], 'archive')


def test_preserves_mysql_implicit_charset_default_collation():
    ddl = "CREATE DATABASE `latin_archive` /*!40100 DEFAULT CHARACTER SET latin1 */ " \
        "/*!80016 DEFAULT ENCRYPTION='N' */"
    assert database_settings(['latin_archive', ddl], 'latin_archive') == dict(
        characterSet='latin1', collation=None, encryption='N')
