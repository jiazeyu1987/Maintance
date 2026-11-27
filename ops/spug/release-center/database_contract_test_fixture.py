"""Local database contract fixture for isolated runtime continuation tests."""
import json
import sqlite3
from ops.release import release_database_contract as contract


def install(test, root, manifest):
    folder = root / contract.DIRECTORY
    folder.mkdir(parents=True)
    (folder / 'catalog.json').write_text(json.dumps({
        'schemaVersion': contract.VERSION,
        'contracts': [{'id': 'resume-rule', 'file': 'resume-rule.sql'}]}), encoding='utf-8')
    query = ("SELECT CASE WHEN COUNT(*)=1 THEN 'DATABASE_CONTRACT_PASS:resume-rule' "
             "ELSE 'BLOCKED:resume-rule' END FROM rules WHERE value='PATROL';")
    (folder / 'resume-rule.sql').write_text(query, encoding='utf-8')
    descriptor, _ = contract.collect(root)
    manifest['databaseContract'] = descriptor
    manifest['files'].extend(dict(name=item['file'], sha256=item['sha256'])
                             for item in [descriptor['catalog']] + descriptor['checks'])
    db = sqlite3.connect(':memory:')
    test.addCleanup(db.close)
    db.execute('CREATE TABLE rules(value TEXT)')
    db.execute("INSERT INTO rules VALUES('PATROL')")
    test.contract_db = db

    def wrap(other):
        def execute(profile, sql):
            if 'DATABASE_CONTRACT_PASS:resume-rule' in sql:
                expected = 'SET SESSION TRANSACTION READ ONLY;\nSTART TRANSACTION READ ONLY;\n' + query + '\nROLLBACK;'
                test.assertEqual(sql, expected)
                return '\n'.join(str(row[0]) for row in db.execute(query))
            return other(profile, sql)
        return execute
    return wrap
