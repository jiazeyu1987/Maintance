"""Reuse the reviewed real UI path with this task's actual acceptance gates."""
from pathlib import Path
task=Path(__file__).resolve().parent
assert not (task/'execute_spug_restore.cjs').exists(),'EXISTING_REVIEWED_HELPER_MUST_NOT_BE_OVERWRITTEN'
source=(task.parent/'20261105-spug-full-to-prod/execute_spug_restore.cjs').read_text(encoding='utf-8')
old="const source='intruoyi-57-safe-20261024-v1',point='smallapp-73cd541a95d84d6a86f9d693e4053c75',target='intruoyi-main-57-safe-restore-20261105-v2';"
new="""const suffix=process.argv[2];if(!['58','59'].includes(suffix))throw Error('TARGET_REQUIRED');
const kind='restore-'+suffix,load=name=>JSON.parse(fs.readFileSync(path.join(task,name),'utf8'));
const acceptedPoint=load('new-incremental-point-verified.json');
const source='intruoyi-57-safe-20261024-v1',point=acceptedPoint.operationId,target='intruoyi-main-'+suffix+'-safe-restore-20261104-v1';"""
assert source.count(old)==1
source=source.replace(old,new).replace('full-to-prod-20261105','prod-incremental-to-two-targets-20261106')
start=source.index(' const clearance=')
end=source.index(' const browser=',start)
gate=""" const readback=load('new-incremental-payload-readback.json'),admission=load('target-new-point-admission-'+suffix+'.json');
 const preserved=load('source-after-backup-preservation.json'),rollback=load('target-rollback-point-admission-'+suffix+'.json');
 const sourceState=load('source-global-state-restored.json');
 const samePin=(a,b)=>a&&b&&['path','bytes','sha256'].every(k=>a[k]===b[k]);
 if(acceptedPoint.status!=='PASS'||acceptedPoint.state!=='SUCCEEDED'||acceptedPoint.actualExitCode!==0||acceptedPoint.pointType!=='INCREMENTAL'||acceptedPoint.parentBackupId!=='smallapp-7fec29a3e132463096aec915c08acab3')throw Error('NEW_INCREMENTAL_ACCEPTANCE_REQUIRED');
 if(readback.status!=='PASS'||readback.operationId!==point||!readback.payloadContentVerified||!readback.exactTreeVerifiedBeforeAndAfter||!readback.metadataPinsVerifiedBeforeAndAfter||!samePin(readback.pointPin,acceptedPoint.pointPin)||!samePin(readback.manifestPin,acceptedPoint.manifestPin))throw Error('COMPLETE_SAFE_READBACK_REQUIRED');
 if(admission.status!=='PASS'||admission.recoveryPointRef!==point||admission.targetConfigRef!==target||!samePin(admission.pointPin,acceptedPoint.pointPin)||admission.orderedChainPins.length!==2||Date.now()-Date.parse(admission.observedAt)>900000)throw Error('FRESH_TARGET_ADMISSION_REQUIRED');
 if(preserved.status!=='PASS'||preserved.backupOperationId!==point||rollback.status!=='PASS'||rollback.host!=='172.30.30.'+suffix)throw Error('SOURCE_PRESERVATION_AND_ROLLBACK_BASIS_REQUIRED');
 if(sourceState.status!=='PASS'||sourceState.backupOperationId!==point||!sourceState.originalGlobalStateRestored||!sourceState.strictBinlogToolStillVerified)throw Error('SOURCE_GLOBAL_STATE_RESTORATION_REQUIRED');
 if(suffix==='59'&&(load('restore-58-native-evidence.json').status!=='PASS'||load('target-58-after-business.json').status!=='PASS'||load('restored-runtime-58.json').status!=='PASS'))throw Error('TEST_TARGET_ACCEPTANCE_REQUIRED_FIRST');
"""
source=source[:start]+gate+source[end:]
source=source.replace("path.join(task,'restore-ui-","path.join(task,kind+'-ui-")
source=source.replace("priv+'/restore-entry-response.private.json'","priv+'/'+kind+'-entry-response.private.json'")
source=source.replace("selectOption('172.30.30.57');\n  await frame.waitForFunction(()=>!document.querySelector('#simple-submit').disabled);","selectOption('172.30.30.'+suffix);\n  await frame.waitForFunction(()=>!document.querySelector('#simple-submit').disabled);")
source=source.replace("[source,point,target,'172.30.30.57','安全模式']","[source,point,target,'172.30.30.'+suffix,'安全模式']")
assert "const receipt=path.join(task,kind+'-ui-submission.json');" in source
assert 'health-recovery-clearance' not in source and "selectOption('172.30.30.'+suffix)" in source
destination=task/'execute_spug_restore.cjs';destination.write_text(source,encoding='utf-8');assert destination.read_text(encoding='utf-8')==source
print('RESTORE_UI_HELPER_PREPARED_WITH_CURRENT_ACCEPTANCE_GATES')
