"""Real Maven BDD/TDD run; raw UTF-8 logs stay private."""
from pathlib import Path
import os,subprocess,sys,re,json
phase=sys.argv[1];assert phase in ('red','green')
folder=Path('C:/SpugHandoff/backend-log-src-20261102/IntRuoyiBackend')
env=dict(os.environ,JAVA_HOME='C:/Users/D01021/AppData/Local/Programs/JavaMaven/jdk-17.0.20.1+1',JAVA_TOOL_OPTIONS='-Dfile.encoding=UTF-8')
tests='ShowroomProductCoverStartupRecoveryTest' if phase=='red' else 'ShowroomProductCoverStartupRecoveryTest,ShowroomProductCoverBatchTaskServiceTest'
command=['C:/Users/D01021/AppData/Local/Programs/JavaMaven/apache-maven-3.9.12/bin/mvn.cmd','-B','-ntp',
         '-pl','yudao-module-showroom','-am','-Dtest='+tests,'-Dsurefire.failIfNoSpecifiedTests=false','test']
log=Path('C:/SpugHandoff/release/private/backend-patch-full-release-20261102/showroom-startup-'+phase+'.private.log')
assert not log.exists(),'Preserve earlier test evidence'
with log.open('wb') as stream:r=subprocess.run(command,cwd=folder,env=env,stdout=stream,stderr=subprocess.STDOUT)
text=log.read_text('utf-8',errors='strict')
print(json.dumps(dict(phase=phase,exitCode=r.returncode,summaries=re.findall(r'Tests run: \d+, Failures: \d+, Errors: \d+, Skipped: \d+[^\r\n]*',text),
                     result='BUILD SUCCESS' if 'BUILD SUCCESS' in text else 'BUILD FAILURE')))
sys.exit(r.returncode)
