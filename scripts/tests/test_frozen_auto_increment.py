"""Frozen allocator plans preserve strict schema validation and column binding."""
import copy
import hashlib
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'ops/backup_engine/formal'))
from formal_snapshot_linux import FormalSnapshotError, _canonical_bytes
from formal_schema_evidence import frozen_auto_increment_plan, compare_schema


def seal(value):
    value = copy.deepcopy(value)
    for key in ('schemaSha256', 'observationSha256', 'observationIdentity'):
        value.pop(key, None)
    value['schemaSha256'] = hashlib.sha256(_canonical_bytes(value)).hexdigest()
    value['observationIdentity'] = dict(containerId='a' * 64,
        databaseUuid='11111111-1111-1111-1111-111111111111')
    value['observationSha256'] = hashlib.sha256(_canonical_bytes(value)).hexdigest()
    return value


def schema(counter=11, *, suffix='', extra='auto_increment', data_type='bigint'):
    option = '' if counter is None else ' AUTO_INCREMENT=' + str(counter)
    value = dict(database='allocator_proof',
        catalog=dict(TABLES=[['allocated', 'BASE TABLE']], ROUTINES=[], TRIGGERS=[], EVENTS=[],
            COLUMNS=[['allocated', 'id', '1', data_type, data_type, None, None, 'NO', None, extra, '']]),
        definitions=dict(DATABASE={'allocator_proof': ['allocator_proof',
            'CREATE DATABASE `allocator_proof`']}, TABLE={'allocated': ['allocated',
            'CREATE TABLE `allocated` (\n  `id` bigint NOT NULL AUTO_INCREMENT,\n'
            '  PRIMARY KEY (`id`)\n) ENGINE=InnoDB' + option + suffix]},
            VIEW={}, FUNCTION={}, PROCEDURE={}, TRIGGER={}, EVENT={}),
        objectCounts=dict(DATABASE=1, TABLE=1, VIEW=0, FUNCTION=0, PROCEDURE=0, TRIGGER=0, EVENT=0),
        excludedHistoricalFields=['SHOW CREATE TRIGGER.Created'],
        fullDataEquivalenceVerified=False, productionEvidence=False)
    return seal(value)


def test_only_changed_frozen_allocator_is_planned_and_strict_comparison_stays_strict():
    source, target = schema(11), schema(3)
    with pytest.raises(FormalSnapshotError, match='FORMAL_SCHEMA_MISMATCH'):
        compare_schema(source, target)
    assert frozen_auto_increment_plan(source, target) == [dict(table='allocated', column='id',
        before=3, after=11, sql='ALTER TABLE `allocated` AUTO_INCREMENT = 11;')]
    assert frozen_auto_increment_plan(source, source) == []
    assert source == schema(11) and target == schema(3)


def test_empty_allocator_is_one_and_can_be_restored_downwards():
    assert frozen_auto_increment_plan(schema(None), schema(3))[0]['after'] == 1
    assert frozen_auto_increment_plan(schema(3), schema(11))[0]['after'] == 3


@pytest.mark.parametrize('text', [" COMMENT='AUTO_INCREMENT=999'", ' /* AUTO_INCREMENT=999 */'])
def test_literal_and_comment_are_not_options(text):
    assert frozen_auto_increment_plan(schema(11, suffix=text), schema(3, suffix=text))[0]['after'] == 11


@pytest.mark.parametrize('counter', ['0', '-1', '1.5', '1x', '18446744073709551616',
                                     '3 AUTO_INCREMENT=4', '3+4'])
def test_invalid_or_duplicate_counter_is_rejected(counter):
    with pytest.raises(FormalSnapshotError):
        frozen_auto_increment_plan(schema(counter), schema(3))


@pytest.mark.parametrize('kwargs', [dict(extra=''), dict(data_type='varchar'), dict(extra='auto_incrementX')])
def test_counter_requires_real_integer_auto_increment_column(kwargs):
    with pytest.raises(FormalSnapshotError):
        frozen_auto_increment_plan(schema(11, **kwargs), schema(3, **kwargs))


def test_non_allocator_schema_difference_rejects_before_any_mutation():
    with pytest.raises(FormalSnapshotError, match='FORMAL_SCHEMA_MISMATCH'):
        frozen_auto_increment_plan(schema(11, suffix=" COMMENT='original'"),
                                   schema(3, suffix=" COMMENT='changed'"))
    target = schema(3)
    target['definitions']['DATABASE']['allocator_proof'][1] += ' COLLATE utf8mb4_bin'
    with pytest.raises(FormalSnapshotError, match='FORMAL_SCHEMA_PROOF_CHANGED'):
        frozen_auto_increment_plan(schema(11), target)


def test_quoted_identifier_is_escaped_and_catalog_bound():
    source, target = schema(11), schema(3)
    for value in (source, target):
        value['catalog']['TABLES'][0][0] = 'a`b'
        value['catalog']['COLUMNS'][0][0] = 'a`b'
        row = value['definitions']['TABLE'].pop('allocated')
        row[0] = 'a`b';row[1] = row[1].replace('`allocated`', '`a``b`')
        value['definitions']['TABLE']['a`b'] = row
    assert frozen_auto_increment_plan(seal(source), seal(target))[0]['sql'] == \
        'ALTER TABLE `a``b` AUTO_INCREMENT = 11;'


def test_ddl_table_name_must_match_catalog_even_when_both_proofs_are_hashed():
    values = [schema(11), schema(3)]
    for value in values:
        value['definitions']['TABLE']['allocated'][1] = value['definitions']['TABLE']['allocated'][1].replace(
            '`allocated`', '`other`')
    with pytest.raises(FormalSnapshotError, match='FORMAL_ALLOCATOR_TABLE_CHANGED'):
        frozen_auto_increment_plan(*[seal(v) for v in values])


def test_plain_table_cannot_gain_an_allocator_and_schema_difference_is_never_hidden():
    values = [schema(None, extra=''), schema(None, extra='')]
    for value in values:
        value['definitions']['TABLE']['allocated'][1] = value['definitions']['TABLE']['allocated'][1].replace(
            ' NOT NULL AUTO_INCREMENT', ' NOT NULL')
    assert frozen_auto_increment_plan(*[seal(v) for v in values]) == []
    values[1]['definitions']['TABLE']['allocated'][1] += ' AUTO_INCREMENT=7'
    with pytest.raises(FormalSnapshotError):
        frozen_auto_increment_plan(*[seal(v) for v in values])
