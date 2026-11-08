"""Adapt established restricted record verification and commit to this task."""
from common import TASK

prior=TASK.parent/'20261105-spug-full-to-prod'
verification=(prior/'verify_task_records.py').read_text(encoding='utf-8')
assert verification.count('from install_prod_control import TASK, PRIVATE')==1
verification=verification.replace('from install_prod_control import TASK, PRIVATE','from common import TASK, PRIVATE')
verification=verification.replace('len(item)>=8','len(item)>=6').replace('len(match[1])>=8','len(match[1])>=6')
verification=verification.replace("r'password|token|secret|authorization'","r'password|token|secret|authorization|access[_-]?key|api[_-]?key'")
commit=(prior/'commit_records.py').read_text(encoding='utf-8')
assert commit.count('from install_prod_control import TASK,PRIVATE')==1
commit=commit.replace('from install_prod_control import TASK,PRIVATE','from common import TASK,PRIVATE')
commit=commit.replace('9dce31858c7bc9196b7a0d7ee34d93fec18c9473','6319024c003ead602d59e7697673fa3c39807863')
commit=commit.replace('任务: 完成Spug正式服恢复验收归档','任务: 完成正式增量备份及两服恢复验收')
for name,value in [('verify_task_records.py',verification),('commit_records.py',commit)]:
 path=TASK/name;assert not path.exists(),'RECORD_HELPER_ALREADY_EXISTS';path.write_text(value,encoding='utf-8');assert path.read_text(encoding='utf-8')==value
print('RESTRICTED_RECORD_HELPERS_PREPARED_NOT_EXECUTED')
