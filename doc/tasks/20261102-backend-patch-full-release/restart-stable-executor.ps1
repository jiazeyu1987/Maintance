param([ValidateSet('runtime-history','runtime-restore','runtime-ascii','runtime-interruption','runtime-catalog','runtime-release-info','runtime-untouched-restore','runtime-boundary','runtime-stopped-patch','runtime-cleanup','runtime-cleanup-legacy')][string]$Evidence)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$env:JAVA_HOME = 'C:/Users/D01021/AppData/Local/Programs/JavaMaven/jdk-17.0.20.1+1'
$env:PATH = 'C:/Users/D01021/Documents/spug-handoff-work-20261030/runtime/Python312-3.12.14;C:/Users/D01021/AppData/Local/Programs/JavaMaven/apache-maven-3.9.12/bin;C:/Users/D01021/AppData/Local/Programs/JavaMaven/jdk-17.0.20.1+1/bin;C:/Users/D01021/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin;' + $env:PATH
if (Get-NetTCPConnection -LocalPort 18112 -State Listen -ErrorAction SilentlyContinue) { throw 'Executor listener already exists' }
$prefix = 'C:/SpugHandoff/release/private/backend-patch-full-release-20261102/' + $Evidence
$executorProcess = Start-Process -FilePath 'C:/Users/D01021/Documents/spug-handoff-work-20261030/runtime/Python312-3.12.14/python.exe' -ArgumentList @('C:/SpugHandoff/release/source/ops/spug/release-center/intruoyi_executor.py','--config','C:/SpugHandoff/release/executor.private.json') -WorkingDirectory 'C:/SpugHandoff/release/source/ops/spug/release-center' -WindowStyle Hidden -RedirectStandardOutput ($prefix+'/executor.stdout.private.log') -RedirectStandardError ($prefix+'/executor.stderr.private.log') -PassThru
$executorProcess.Id
