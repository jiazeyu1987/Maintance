"""Prepare reviewed code-only overlay; never read/output private configuration."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

repo=Path(__file__).resolve().parents[3]
source=repo/'ops/spug/release-center'
live=Path('C:/SpugHandoff/release/source')
private=Path('C:/SpugHandoff/release/private/post-release-cleanup-20261102')
overlay=private/'candidate-source-v3'
if overlay.exists():
    raise SystemExit('Candidate already exists; inspect rather than overwrite')
shutil.copytree(live,overlay,ignore=shutil.ignore_patterns('__pycache__'))
target=overlay/'ops/spug/release-center'
changes={
 'intruoyi_executor.py':[(
  '            return self.execute_bound(job)',
  '            result = self.execute_bound(job)\n            from post_release_cleanup import run as cleanup_after_acceptance\n            cleanup_after_acceptance(self, job)\n            return result'),(
  '# A repeated request returns its original task even if a newer release now runs.',
  "# A repeated request returns its original task even if a newer release now runs.\n        require(not getattr(self, 'cleanup_active', False), '发布收尾清理仍在执行，请等待其完成')"),(
  '    def execute(self, job):\n        tracker = None',
  "    def execute(self, job):\n        tracker = None\n        self.cleanup_active = job['action'] == 'accept-backup'"),(
  '        finally:\n            if context is not None:',
  '        finally:\n            self.cleanup_active = False\n            if context is not None:')],
 'frontend_patch.py':[(
  "            self.log(job,'前端补丁操作完成；后端及数据库保持原容器。')",
  "            self.log(job,'前端补丁操作完成；后端及数据库保持原容器。')\n            from post_release_cleanup import run as cleanup_after_acceptance\n            cleanup_after_acceptance(self,job)"),(
  "            require(not getattr(self,'draining',False),'执行器正在停止')",
  "            require(not getattr(self,'draining',False),'执行器正在停止')\n            require(not getattr(self,'cleanup_active',False),'发布收尾清理仍在执行，请等待其完成')"),(
  '    def frontend_job(self,job):',
  "    def frontend_job(self,job):\n        self.cleanup_active = job['action'] == PREFIX+'accept' and job.get('target') == 'backup'"),(
  '        finally:\n            self.runtime.operation_context.binding=None',
  '        finally:\n            self.cleanup_active = False\n            self.runtime.operation_context.binding=None')],
 'intruoyi_runtime_agent.py':[(
  "if action in ('artifact-inventory','artifact-remove'):",
  "if action in ('artifact-inventory','artifact-remove','artifact-auto-clean'):")],
 'intruoyi_runtime.py':[(
  "uncertain_on_disconnect = action in ('frontend-patch-deploy'",
  "uncertain_on_disconnect = action in ('artifact-auto-clean','frontend-patch-deploy'"),(
  "        profile = self.profile(env)\n        payload = json.dumps({'action': action, 'profile': profile, **arguments}, ensure_ascii=True)",
  "        profile = self.profile(env)\n        if action == 'artifact-auto-clean':\n            profile['stagingRoot'] = self.targets[env]['stagingRoot']\n        if context:\n            profile['operationLockRoot'] = self.targets[env]['stagingRoot']\n        payload = json.dumps({'action': action, 'profile': profile, **arguments}, ensure_ascii=True)")]
}
names=['post_release_cleanup.py','artifact_files.py','operation_journal.py',*changes]
report=[]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
for name in names:
    path=target/name
    before=sha(live/'ops/spug/release-center'/name)
    if name in changes:
        text=path.read_text('utf-8')
        for old,new in changes[name]:
            if text.count(old)!=1: raise SystemExit('Unexpected source contract: '+name)
            text=text.replace(old,new)
        path.write_text(text,'utf-8')
    else:
        shutil.copyfile(source/name,path)
    compile(path.read_text('utf-8'),str(path),'exec')
    report.append(dict(name=name,beforeSha256=before,afterSha256=sha(path)))
for name in ('test_post_release_cleanup.py','test_post_release_cleanup_lock.py'):
    shutil.copyfile(source/name,target/name)
(private/'code-update-plan.json').write_text(json.dumps(report,indent=2),'utf-8')
print(json.dumps(dict(candidate=str(target),files=len(names),privatePlan=str(private/'code-update-plan.json'))))
