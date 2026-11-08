"""Verify source recovery after failed operations without claiming a new point."""
import argparse,json

from common import PRIVATE,TASK,active_source_installation, now, remote, write
from verify_source_restoration import SCRIPT


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--history',choices=['365','366'],default='365');args=parser.parse_args()
    destination=TASK/('source-after-failed-'+args.history+'-global-state.json')
    assert not destination.exists(),'SOURCE_RECOVERY_EVIDENCE_ALREADY_EXISTS'
    first = json.loads((TASK / 'registered-binlog-tool-restored.json').read_text(encoding='utf-8'))
    second = json.loads((TASK / ('incremental-'+args.history+'-failure.json')).read_text(encoding='utf-8'))
    pins = first['failedOriginalPins']
    for history in ('365','366'):
        if int(history)<=int(args.history):pins+=json.loads((PRIVATE/('failed-'+history+'-all-pins.private.json')).read_text(encoding='utf-8'))['pins']
    installed=active_source_installation()
    exporter=json.loads((TASK/'binlog-tmpfs-tool-provisioned.json').read_text(encoding='utf-8'))
    script = SCRIPT.replace('FAILED_364_ORIGINAL_CHANGED', 'FAILED_ORIGINAL_CHANGED')
    variables=dict(ENGINE=installed['engine'],FAILED_PINS=pins,CAPTURE_PIN=installed['captureConfigurationPin'],EXPORTER=exporter)
    report = remote('172.30.30.57','\n'.join(k+'='+repr(v) for k,v in variables.items())+'\n'+script,120)
    report.update(observedAt=now(), failedOperationId=second['operationId'],
                  newRecoveryPointPublished=False, destinationRestoreDispatched=False)
    write(destination, report)
    print(json.dumps(report))
