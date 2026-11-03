"""Maven evidence for the actual Quartz startup contract; private raw logs."""
from pathlib import Path
import os, subprocess, sys, re, json
phase=sys.argv[1];assert phase in ('red','green','green2','regression')
tests='SchedulerManagerDefinitionTest,JobStartupDefinitionSyncTest'
if phase in ('green','green2','regression'):tests+=',SchedulerManagerUniqueJobTest,JobHandlerInvokerRetryTest,ReleaseMaintenanceJobTest,JobStartupSyncRunnerTest,JobServiceImplTest'
env=dict(os.environ,JAVA_HOME='C:/Users/D01021/AppData/Local/Programs/JavaMaven/jdk-17.0.20.1+1',JAVA_TOOL_OPTIONS='-Dfile.encoding=UTF-8')
command=['C:/Users/D01021/AppData/Local/Programs/JavaMaven/apache-maven-3.9.12/bin/mvn.cmd','-B','-ntp','-pl','yudao-module-infra','-am','-Dtest='+tests,'-Dsurefire.failIfNoSpecifiedTests=false','test']
log=Path('C:/SpugHandoff/release/private/backend-patch-full-release-20261102/quartz-startup-'+phase+'.private.log');assert not log.exists()
with log.open('wb') as output:r=subprocess.run(command,cwd='C:/SpugHandoff/backend-log-src-20261102/IntRuoyiBackend',env=env,stdout=output,stderr=subprocess.STDOUT)
content=log.read_text('utf-8')
print(json.dumps(dict(phase=phase,exitCode=r.returncode,summaries=re.findall(r'Tests run: \d+, Failures: \d+, Errors: \d+, Skipped: \d+[^\r\n]*',content),compilationErrors=len(re.findall(r'cannot find symbol',content)),result='BUILD SUCCESS' if 'BUILD SUCCESS' in content else 'BUILD FAILURE')))
sys.exit(r.returncode)
