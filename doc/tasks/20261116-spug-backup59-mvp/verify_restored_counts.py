"""Run only after the parent has observed successful full restore; no database writes."""
import argparse
import json
from pathlib import Path
import re
import subprocess

HOST='172.30.30.59'
TABLES=('infra_file','system_users','system_tenant','mes_pro_work_order','mes_pro_batch_record_execution',
        'mes_pro_batch_record_template','dcc_product_catalog','erp_product','erp_kingdee_sync_run',
        'infra_job_log','dcc_registration_certificate_daily_run')


def count_query(expected):
    if set(expected)!=set(TABLES) or any(type(value) is not int or value<0 for value in expected.values()):
        raise ValueError('EXPECTED_ELEVEN_TABLE_COUNTS_REQUIRED')
    return ' UNION ALL '.join("SELECT '"+name+"', COUNT(*) FROM `ruoyi-vue-pro`.`"+name+'`' for name in TABLES)+';'


def target_ref(value):
    if not isinstance(value,str) or not re.fullmatch('spug-empty59-[a-f0-9]{12}',value):
        raise ValueError('EXPLICIT_PREPARED_TARGET_REQUIRED')
    return value


def compare(expected,actual,target):
    target_ref(target)
    count_query(expected)
    if set(actual)!=set(expected) or any(type(value) is not int for value in actual.values()):
        raise ValueError('OBSERVED_TABLE_COUNTS_INCOMPLETE')
    rows=[dict(table=name,expected=expected[name],actual=actual[name],matched=expected[name]==actual[name]) for name in TABLES]
    return dict(host=HOST,targetConfigRef=target,tables=rows,matched=all(row['matched'] for row in rows),serverWrites=False)


def observe(query,target):
    target_ref(target)
    # Fixed .59 and explicit READY target. Neither password nor Env is read back.
    code="""import json,subprocess,sys
target=__TARGET__
try:
 observed=subprocess.run(['docker','inspect','--format','{{.Name}}',target+'-mysql'],capture_output=True,text=True,timeout=15)
 if observed.returncode or observed.stdout.strip()!='/'+target+'-mysql':raise ValueError('TARGET_MYSQL_NOT_FOUND')
 result=subprocess.run(['docker','exec','-i',target+'-mysql','mysql','--defaults-extra-file=/run/recovery/mysql-client.cnf','--batch','--skip-column-names'],input=__QUERY__,capture_output=True,text=True,timeout=90)
 if result.returncode:raise ValueError('COUNT_QUERY_FAILED')
 rows=[line.split('\\t') for line in result.stdout.splitlines()]
 if any(len(row)!=2 for row in rows) or len(rows)!=11:raise ValueError('COUNT_QUERY_RESULT_INVALID')
 print(json.dumps({name:int(value) for name,value in rows}))
except Exception as error:
 print(json.dumps({'errorCode':str(error) if isinstance(error,ValueError) and str(error) in ('TARGET_MYSQL_NOT_FOUND','COUNT_QUERY_FAILED','COUNT_QUERY_RESULT_INVALID') else 'COUNT_OBSERVATION_FAILED'}));sys.exit(1)
""".replace('__TARGET__',repr(target)).replace('__QUERY__',repr(query))
    args=['C:/Windows/System32/OpenSSH/ssh.exe','-F','NUL','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
          '-o','IdentitiesOnly=yes','-i','C:/SpugHandoff/release/private/sshIdentityFile',
          '-o','UserKnownHostsFile=C:/SpugHandoff/release/private/sshKnownHostsFile','-o','ConnectTimeout=8',
          'root@'+HOST,'/mnt/intruoyi-data/recovery-tools/python/bin/python3.12 -B -']
    result=subprocess.run(args,input=code.encode('utf-8'),capture_output=True,timeout=120)
    if result.returncode:raise ValueError('RESTORED_COUNT_OBSERVATION_FAILED')
    return json.loads(result.stdout)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--target',required=True,type=target_ref)
    options=parser.parse_args()
    baseline=json.loads(options.baseline.read_text(encoding='utf-8'))
    expected=baseline['databaseTableCounts']
    report=compare(expected,observe(count_query(expected),options.target),options.target)
    report['backupId']=baseline['backupId']
    options.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(dict(matched=report['matched'],tables=len(report['tables']),host=HOST,targetConfigRef=options.target)))
    return 0 if report['matched'] else 1


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        print(json.dumps({'errorCode':'RESTORED_COUNT_VERIFICATION_FAILED'}));raise SystemExit(1)
