Set-StrictMode -Version Latest

function Get-DeploymentEvidenceDigest {
    param([byte[]]$Bytes)
    $sha=[Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant() }
    finally { $sha.Dispose() }
}

function ConvertFrom-DeploymentEvidenceJson {
    param([string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { throw 'RELEASE_DEPLOYMENT_EVIDENCE_EMPTY' }
    if(-not $Text.TrimStart().StartsWith('{') -or -not $Text.TrimEnd().EndsWith('}')){throw 'RELEASE_DEPLOYMENT_EVIDENCE_OBJECT_REQUIRED'}
    # ConvertFrom-Json on Windows PowerShell accepts duplicate properties. Scan
    # property tokens before conversion, including escaped equivalent names.
    $tokens=[regex]::Matches($Text,'"(?:[^"\\]|\\.)*"|[{}\[\]:,]|true|false|null|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?')
    $stack=[Collections.Generic.Stack[object]]::new()
    $offset=0
    for($i=0;$i -lt $tokens.Count;$i++) {
        $token=$tokens[$i]
        if (-not [string]::IsNullOrWhiteSpace($Text.Substring($offset,$token.Index-$offset))) { throw 'RELEASE_DEPLOYMENT_EVIDENCE_JSON_INVALID' }
        $offset=$token.Index+$token.Length
        if($token.Value -ceq '{') { $stack.Push([Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)) }
        elseif($token.Value -ceq '}') { if($stack.Count -eq 0){throw 'RELEASE_DEPLOYMENT_EVIDENCE_JSON_INVALID'};$null=$stack.Pop() }
        elseif($token.Value.StartsWith('"') -and $i+1 -lt $tokens.Count -and $tokens[$i+1].Value -ceq ':') {
            if($stack.Count -eq 0){throw 'RELEASE_DEPLOYMENT_EVIDENCE_JSON_INVALID'}
            $key=ConvertFrom-Json -InputObject $token.Value
            if(-not $stack.Peek().Add([string]$key)){throw 'RELEASE_DEPLOYMENT_EVIDENCE_DUPLICATE_KEY'}
        }
    }
    if($stack.Count -ne 0 -or -not [string]::IsNullOrWhiteSpace($Text.Substring($offset))){throw 'RELEASE_DEPLOYMENT_EVIDENCE_JSON_INVALID'}
    try { return ConvertFrom-Json -InputObject $Text -ErrorAction Stop }
    catch { throw 'RELEASE_DEPLOYMENT_EVIDENCE_JSON_INVALID' }
}

function Assert-DeploymentEvidenceRoot {
    param([string]$Root)
    if($Root -cnotmatch '^/[A-Za-z0-9_./-]+$' -or $Root -match '(^|/)\.\.?(?:/|$)' -or $Root.EndsWith('/')) {
        throw 'RELEASE_DEPLOYMENT_EVIDENCE_PATH_INVALID'
    }
}

function Assert-DeploymentEvidenceScope {
    param($Scope,$Expected)
    foreach($key in @('environment','host','machineId','database','serverUuid')) {
        if($null -eq $Scope.PSObject.Properties[$key] -or [string]::IsNullOrWhiteSpace([string]$Scope.$key)) {throw 'RELEASE_DEPLOYMENT_EVIDENCE_SCOPE_INVALID'}
        if($null -ne $Expected -and [string]$Scope.$key -cne [string]$Expected.$key){throw "RELEASE_DEPLOYMENT_EVIDENCE_SCOPE_MISMATCH: $key"}
    }
    if($Scope.environment -cnotin @('test','prod','backup') -or $Scope.database -cnotmatch '^[A-Za-z][A-Za-z0-9_-]{0,63}$' -or
       $Scope.machineId -cnotmatch '^[0-9a-f]{32}$' -or $Scope.serverUuid -cnotmatch '^[0-9a-fA-F-]{36}$') {throw 'RELEASE_DEPLOYMENT_EVIDENCE_SCOPE_INVALID'}
}

function Read-DeploymentEvidenceFile {
    param([string]$Path,[scriptblock]$Capture,[string]$ExpectedDigest='')
    $r=& $Capture "set -eu`ntest -f '$Path'`ntest ! -L '$Path'`nbase64 -w 0 '$Path'"
    if(-not $r.Ok){throw 'RELEASE_DEPLOYMENT_EVIDENCE_READ_FAILED'}
    try {$bytes=[Convert]::FromBase64String(([string]$r.Output).Trim());$text=[Text.UTF8Encoding]::new($false,$true).GetString($bytes)}
    catch {throw 'RELEASE_DEPLOYMENT_EVIDENCE_ENCODING_INVALID'}
    $digest=Get-DeploymentEvidenceDigest $bytes
    if($ExpectedDigest -and $digest -cne $ExpectedDigest){throw 'RELEASE_DEPLOYMENT_EVIDENCE_DIGEST_MISMATCH'}
    return @{value=(ConvertFrom-DeploymentEvidenceJson $text);digest=$digest}
}

function Assert-DeploymentOperationBinding {
    param($Operation,$Scope)
    if($Operation.schemaVersion -cne 'release-deployment-operation/v1' -or $Operation.attemptId -cnotmatch '^[0-9a-f]{64}$') {throw 'RELEASE_DEPLOYMENT_EVIDENCE_OPERATION_INVALID'}
    Assert-DeploymentEvidenceScope $Operation.binding.scope $Scope
    $binding=$Operation.binding
    if($binding.releaseTag -cnotmatch '^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$' -or $binding.lockOperationId -cne "$($Scope.environment)-$($binding.releaseTag)") {throw 'RELEASE_DEPLOYMENT_EVIDENCE_OPERATION_BINDING_INVALID'}
    foreach($key in @('leaseTokenDigest','packageDigest','manifestDigest','planDigest')) {
        if($binding.$key -cnotmatch '^[0-9a-f]{64}$'){throw "RELEASE_DEPLOYMENT_EVIDENCE_OPERATION_BINDING_INVALID: $key"}
    }
    if($Operation.writeAttempted -isnot [bool] -or ($Operation.revision -isnot [int] -and $Operation.revision -isnot [long]) -or $Operation.revision -lt 1 -or
       $Operation.state -cnotin @('PREPARED','STARTED','FINALIZING','RECOVERY_REQUIRED','ZERO_WRITE_FAILED','COMMITTED')) {throw 'RELEASE_DEPLOYMENT_EVIDENCE_OPERATION_STATE_INVALID'}
    if($Operation.state -cin @('PREPARED','ZERO_WRITE_FAILED') -and $Operation.writeAttempted){throw 'RELEASE_DEPLOYMENT_EVIDENCE_ZERO_WRITE_INVALID'}
}

function Read-ReleaseDeploymentState {
    param([Parameter(Mandatory=$true)][string]$Root,[Parameter(Mandatory=$true)]$Scope,[Parameter(Mandatory=$true)][scriptblock]$Capture)
    Assert-DeploymentEvidenceRoot $Root
    Assert-DeploymentEvidenceScope $Scope $null
    $preflight=@"
set -eu
test -d '$Root'
test ! -L '$Root'
test -w '$Root'
test -d '$Root/operations'
test ! -L '$Root/operations'
test -w '$Root/operations'
test -f '$Root/gate.lock'
test ! -L '$Root/gate.lock'
test -w '$Root/gate.lock'
for tool in flock base64 sha256sum mv find; do command -v "`$tool" >/dev/null; done
base64 -w 0 </dev/null >/dev/null
printf EVIDENCE_PLATFORM_READY
"@
    $r=& $Capture $preflight
    if(-not $r.Ok -or ([string]$r.Output).Trim() -cne 'EVIDENCE_PLATFORM_READY'){throw 'RELEASE_DEPLOYMENT_EVIDENCE_PLATFORM_NOT_READY: complete explicit persistent-state preparation'}
    $file=Read-DeploymentEvidenceFile "$Root/gate.json" $Capture
    $gate=$file.value
    if($gate.schemaVersion -cne 'release-deployment-gate/v1' -or ($gate.revision -isnot [int] -and $gate.revision -isnot [long]) -or $gate.revision -lt 0){throw 'RELEASE_DEPLOYMENT_EVIDENCE_GATE_INVALID'}
    Assert-DeploymentEvidenceScope $gate.scope $Scope
    $state=@{gate=$gate;gateDigest=$file.digest;operation=$null;receipt=$null}
    if($gate.state -ceq 'READY') {
        if($gate.revision -ne 0 -or $null -ne $gate.attemptId -or $null -ne $gate.operationDigest -or $null -ne $gate.receiptDigest){throw 'RELEASE_DEPLOYMENT_EVIDENCE_READY_INVALID'}
        $empty=& $Capture "find '$Root/operations' -mindepth 1 -maxdepth 1 -print -quit"
        if(-not $empty.Ok -or -not [string]::IsNullOrWhiteSpace([string]$empty.Output)){throw 'RELEASE_DEPLOYMENT_EVIDENCE_ORPHAN_OPERATION'}
        return $state
    }
    if($gate.attemptId -cnotmatch '^[0-9a-f]{64}$' -or $gate.operationDigest -cnotmatch '^[0-9a-f]{64}$'){throw 'RELEASE_DEPLOYMENT_EVIDENCE_GATE_INVALID'}
    $op=Read-DeploymentEvidenceFile "$Root/operations/$($gate.attemptId).json" $Capture $gate.operationDigest
    Assert-DeploymentOperationBinding $op.value $Scope
    if($op.value.attemptId -cne $gate.attemptId -or $op.value.revision -ne $gate.revision -or $op.value.state -cne $gate.state){throw 'RELEASE_DEPLOYMENT_EVIDENCE_OPERATION_MISMATCH'}
    Assert-DeploymentEvidenceScope $gate.binding.scope $Scope
    foreach($key in @('lockOperationId','releaseTag','leaseTokenDigest','packageDigest','manifestDigest','planDigest')) {
        if($gate.binding.$key -cne $op.value.binding.$key){throw 'RELEASE_DEPLOYMENT_EVIDENCE_GATE_BINDING_MISMATCH'}
    }
    $state.operation=$op.value
    if($op.value.receiptDigest -cne $gate.receiptDigest){throw 'RELEASE_DEPLOYMENT_EVIDENCE_RECEIPT_DIGEST_MISMATCH'}
    if($null -ne $gate.receiptDigest) {
        if($gate.receiptDigest -cnotmatch '^[0-9a-f]{64}$'){throw 'RELEASE_DEPLOYMENT_EVIDENCE_RECEIPT_INVALID'}
        $receipt=Read-DeploymentEvidenceFile "$Root/operations/$($gate.attemptId).receipt.json" $Capture $gate.receiptDigest
        if($receipt.value.schemaVersion -cne 'release-deployment-receipt/v1' -or $receipt.value.attemptId -cne $gate.attemptId){throw 'RELEASE_DEPLOYMENT_EVIDENCE_RECEIPT_INVALID'}
        foreach($key in @('lockOperationId','releaseTag','leaseTokenDigest','packageDigest','manifestDigest','planDigest')) {
            if($receipt.value.binding.$key -cne $op.value.binding.$key){throw 'RELEASE_DEPLOYMENT_EVIDENCE_RECEIPT_BINDING_MISMATCH'}
        }
        Assert-DeploymentEvidenceScope $receipt.value.binding.scope $Scope
        $state.receipt=$receipt.value
    }
    if($gate.state -ceq 'COMMITTED') {
        if($null -eq $state.receipt -or -not $op.value.writeAttempted){throw 'RELEASE_DEPLOYMENT_EVIDENCE_COMPLETION_INVALID'}
        foreach($key in @('lockApplied','historyVerified','cleanupVerified')) {
            if($op.value.completion.$key -isnot [bool] -or $op.value.completion.$key -ne $true){throw 'RELEASE_DEPLOYMENT_EVIDENCE_COMPLETION_INVALID'}
        }
    }
    return $state
}

function New-ReleaseDeploymentOperation {
    param($Scope,[string]$LockOperationId,[string]$ReleaseTag,[string]$LeaseToken,[string]$PackageDigest,[string]$ManifestDigest,[string]$PlanDigest,$Before,$Target)
    $scopeObject=ConvertFrom-Json ($Scope|ConvertTo-Json -Depth 10 -Compress)
    Assert-DeploymentEvidenceScope $scopeObject $null
    if([string]::IsNullOrWhiteSpace($LeaseToken)){throw 'RELEASE_DEPLOYMENT_EVIDENCE_LEASE_REQUIRED'}
    $attempt=Get-DeploymentEvidenceDigest ([Text.Encoding]::UTF8.GetBytes($LockOperationId+"`n"+$LeaseToken))
    $operation=[pscustomobject][ordered]@{
        schemaVersion='release-deployment-operation/v1';attemptId=$attempt;revision=1;state='PREPARED';phase='prepared';writeAttempted=$false
        binding=[pscustomobject]@{scope=$scopeObject;lockOperationId=$LockOperationId;releaseTag=$ReleaseTag;leaseTokenDigest=(Get-DeploymentEvidenceDigest ([Text.Encoding]::UTF8.GetBytes($LeaseToken)));packageDigest=$PackageDigest;manifestDigest=$ManifestDigest;planDigest=$PlanDigest}
        before=$Before;target=$Target;phases=@();verification=$null;observation=$null;originalError=$null;observationErrors=@();finalizationErrors=@();receiptDigest=$null;history=$null;completion=$null
    }
    Assert-DeploymentOperationBinding $operation $scopeObject
    return $operation
}

function Get-DeploymentEvidencePreviousFileGuard {
    param([string]$Root,$State)
    if($State.gate.state -ceq 'READY') {
        return "test -z `"`$(find '$Root/operations' -mindepth 1 -maxdepth 1 -print -quit)`""
    }
    $id=$State.gate.attemptId
    if($id -cnotmatch '^[0-9a-f]{64}$' -or $State.gate.operationDigest -cnotmatch '^[0-9a-f]{64}$'){throw 'RELEASE_DEPLOYMENT_EVIDENCE_GATE_INVALID'}
    $guard="test -f '$Root/operations/$id.json'`ntest ! -L '$Root/operations/$id.json'`nprevious=`$(sha256sum <'$Root/operations/$id.json')`ntest `"`${previous%% *}`" = '$($State.gate.operationDigest)'"
    if($null -ne $State.gate.receiptDigest) {
        if($State.gate.receiptDigest -cnotmatch '^[0-9a-f]{64}$'){throw 'RELEASE_DEPLOYMENT_EVIDENCE_RECEIPT_INVALID'}
        $guard+="`ntest -f '$Root/operations/$id.receipt.json'`ntest ! -L '$Root/operations/$id.receipt.json'`nprevious_receipt=`$(sha256sum <'$Root/operations/$id.receipt.json')`ntest `"`${previous_receipt%% *}`" = '$($State.gate.receiptDigest)'"
    }
    return $guard
}

function Save-ReleaseDeploymentState {
    param([string]$Root,$State,$Operation,[scriptblock]$Capture,[Parameter(Mandatory=$true)][string]$FenceCommand,[switch]$Create)
    Assert-DeploymentEvidenceRoot $Root
    $Operation.revision=[int64]$State.gate.revision+1
    Assert-DeploymentOperationBinding $Operation $State.gate.scope
    if(-not $Create -and ($State.gate.attemptId -cne $Operation.attemptId -or $State.operation.binding.leaseTokenDigest -cne $Operation.binding.leaseTokenDigest)){throw 'RELEASE_DEPLOYMENT_EVIDENCE_ATTEMPT_MISMATCH'}
    if(-not $Create) {
        # Read the persisted previous value, not a mutable caller-owned object.
        # The final gate-digest CAS fences changes between this read and write.
        $old=(Read-DeploymentEvidenceFile "$Root/operations/$($State.gate.attemptId).json" $Capture $State.gate.operationDigest).value
        if($old.writeAttempted -eq $true -and $Operation.writeAttempted -ne $true){throw 'RELEASE_DEPLOYMENT_EVIDENCE_WRITE_FLAG_REGRESSION'}
        if(($old.state -ceq 'COMMITTED') -or
           ($old.state -ceq 'RECOVERY_REQUIRED' -and $Operation.state -cne 'RECOVERY_REQUIRED') -or
           ($old.state -ceq 'ZERO_WRITE_FAILED' -and $Operation.state -cne 'ZERO_WRITE_FAILED') -or
           ($old.state -ceq 'FINALIZING' -and $Operation.state -cin @('PREPARED','STARTED','ZERO_WRITE_FAILED'))){throw 'RELEASE_DEPLOYMENT_EVIDENCE_STATE_REGRESSION'}
        foreach($key in @('lockOperationId','releaseTag','leaseTokenDigest','packageDigest','manifestDigest','planDigest')) {
            if($old.binding.$key -cne $Operation.binding.$key){throw 'RELEASE_DEPLOYMENT_EVIDENCE_IMMUTABLE_BINDING_MISMATCH'}
        }
    }
    if($Create -and $State.gate.state -cnotin @('READY','COMMITTED','ZERO_WRITE_FAILED')){throw 'RELEASE_DEPLOYMENT_EVIDENCE_RECOVERY_REQUIRED'}
    $opJson=$Operation|ConvertTo-Json -Depth 60 -Compress
    $opBytes=[Text.Encoding]::UTF8.GetBytes($opJson)
    $gate=[ordered]@{schemaVersion='release-deployment-gate/v1';scope=$State.gate.scope;binding=$Operation.binding;revision=$Operation.revision;state=$Operation.state;attemptId=$Operation.attemptId;operationDigest=(Get-DeploymentEvidenceDigest $opBytes);receiptDigest=$Operation.receiptDigest}
    $gateJson=$gate|ConvertTo-Json -Depth 15 -Compress
    $opData=[Convert]::ToBase64String($opBytes);$gateData=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($gateJson))
    $attempt=$Operation.attemptId
    $createGuard=if($Create){"test ! -e '$Root/operations/$attempt.json'"}else{"test -f '$Root/operations/$attempt.json'`ntest ! -L '$Root/operations/$attempt.json'"}
    $previousGuard=Get-DeploymentEvidencePreviousFileGuard -Root $Root -State $State
    # A new attempt must block the previous committed gate before its operation
    # becomes visible. Missing-operation and digest-mismatch windows fail closed.
    $replace=if($Create){"mv -f -- `"`$gate_tmp`" '$Root/gate.json'`nmv -f -- `"`$op_tmp`" '$Root/operations/$attempt.json'"}else{"mv -f -- `"`$op_tmp`" '$Root/operations/$attempt.json'`nmv -f -- `"`$gate_tmp`" '$Root/gate.json'"}
    $command=@"
set -eu
test -d '$Root'
test ! -L '$Root'
test -d '$Root/operations'
test ! -L '$Root/operations'
test -f '$Root/gate.lock'
test ! -L '$Root/gate.lock'
test -f '$Root/gate.json'
test ! -L '$Root/gate.json'
exec 9<'$Root/gate.lock'
flock -x 9
current=`$(sha256sum <'$Root/gate.json')
test "`${current%% *}" = '$($State.gateDigest)'
$previousGuard
fence=`$(
$FenceCommand
)
test "`$fence" = 'EVIDENCE_FENCE_OK'
$createGuard
umask 077
op_tmp='$Root/operations/.$attempt.'`$`$'.tmp'
gate_tmp='$Root/.gate.$attempt.'`$`$'.tmp'
trap 'rm -f "`$op_tmp" "`$gate_tmp"' EXIT
set -C
printf '%s' '$opData' | base64 -d >"`$op_tmp"
printf '%s' '$gateData' | base64 -d >"`$gate_tmp"
$replace
printf EVIDENCE_SAVED
"@
    $r=& $Capture $command
    if(-not $r.Ok -or ([string]$r.Output).Trim() -cne 'EVIDENCE_SAVED'){throw 'RELEASE_DEPLOYMENT_EVIDENCE_WRITE_FAILED: state remains blocking or unknown'}
    return Read-ReleaseDeploymentState -Root $Root -Scope $State.gate.scope -Capture $Capture
}

function Write-ReleaseDeploymentReceipt {
    param([string]$Root,$State,$Receipt,[scriptblock]$Capture,[Parameter(Mandatory=$true)][string]$FenceCommand)
    Assert-DeploymentEvidenceRoot $Root
    if($State.gate.state -cne 'FINALIZING' -or $Receipt.attemptId -cne $State.gate.attemptId){throw 'RELEASE_DEPLOYMENT_EVIDENCE_RECEIPT_STATE_INVALID'}
    $json=$Receipt|ConvertTo-Json -Depth 60 -Compress
    $bytes=[Text.Encoding]::UTF8.GetBytes($json);$encoded=[Convert]::ToBase64String($bytes)
    $path="$Root/operations/$($State.gate.attemptId).receipt.json"
    $previousGuard=Get-DeploymentEvidencePreviousFileGuard -Root $Root -State $State
    $command=@"
set -eu
test -d '$Root'
test ! -L '$Root'
test -d '$Root/operations'
test ! -L '$Root/operations'
test -f '$Root/gate.lock'
test ! -L '$Root/gate.lock'
test -f '$Root/gate.json'
test ! -L '$Root/gate.json'
exec 9<'$Root/gate.lock'
flock -x 9
current=`$(sha256sum <'$Root/gate.json')
test "`${current%% *}" = '$($State.gateDigest)'
$previousGuard
fence=`$(
$FenceCommand
)
test "`$fence" = EVIDENCE_FENCE_OK
test ! -e '$path'
umask 077
tmp='$path.'`$`$'.tmp'
trap 'rm -f "`$tmp"' EXIT
set -C
printf '%s' '$encoded' | base64 -d >"`$tmp"
mv -f -- "`$tmp" '$path'
printf RECEIPT_SAVED
"@
    $r=& $Capture $command
    if(-not $r.Ok -or ([string]$r.Output).Trim() -cne 'RECEIPT_SAVED'){throw 'RELEASE_DEPLOYMENT_EVIDENCE_RECEIPT_WRITE_FAILED'}
    $digest=Get-DeploymentEvidenceDigest $bytes
    $null=Read-DeploymentEvidenceFile $path $Capture $digest
    return $digest
}

function Assert-ReleaseDeploymentGate {
    param($State,[switch]$CompletionVerified,[switch]$Recovery,[string]$ExpectedOperationId='',[string]$ExpectedReleaseTag='',[string]$ExpectedLeaseToken='')
    if($State.gate.state -ceq 'READY'){return}
    if($State.gate.state -ceq 'COMMITTED' -and $CompletionVerified -and -not $Recovery){return}
    if($State.gate.state -ceq 'ZERO_WRITE_FAILED' -and -not $State.operation.writeAttempted -and $CompletionVerified -and -not $Recovery){return}
    if($Recovery -and $State.gate.state -cin @('PREPARED','ZERO_WRITE_FAILED') -and -not $State.operation.writeAttempted) {
        $leaseDigest=Get-DeploymentEvidenceDigest ([Text.Encoding]::UTF8.GetBytes($ExpectedLeaseToken))
        if($State.operation.binding.lockOperationId -ceq $ExpectedOperationId -and $State.operation.binding.releaseTag -ceq $ExpectedReleaseTag -and $State.operation.binding.leaseTokenDigest -ceq $leaseDigest){return}
    }
    throw "RELEASE_DEPLOYMENT_EVIDENCE_RECOVERY_REQUIRED: $($State.gate.state)"
}

function Write-ReleaseLocalAtomicEvidence {
    param([string]$Path,[string]$Text,[switch]$CreateOnly)
    $full=[IO.Path]::GetFullPath($Path)
    if(-not [IO.Directory]::Exists([IO.Path]::GetDirectoryName($full))){throw 'RELEASE_DEPLOYMENT_EVIDENCE_LOCAL_PARENT_MISSING'}
    $temp=$full+'.'+[Guid]::NewGuid().ToString('N')+'.tmp'
    try {
        $stream=[IO.File]::Open($temp,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
        try {$bytes=[Text.Encoding]::UTF8.GetBytes($Text);$stream.Write($bytes,0,$bytes.Length);$stream.Flush($true)}finally{$stream.Dispose()}
        if($CreateOnly -or -not [IO.File]::Exists($full)){[IO.File]::Move($temp,$full)}else{[IO.File]::Replace($temp,$full,$null)}
        if([IO.File]::ReadAllText($full,[Text.UTF8Encoding]::new($false,$true)) -cne $Text){throw 'RELEASE_DEPLOYMENT_EVIDENCE_LOCAL_READBACK_FAILED'}
    } finally {if([IO.File]::Exists($temp)){[IO.File]::Delete($temp)}}
}

Export-ModuleMember -Function Read-ReleaseDeploymentState,New-ReleaseDeploymentOperation,Save-ReleaseDeploymentState,Write-ReleaseDeploymentReceipt,Assert-ReleaseDeploymentGate,Write-ReleaseLocalAtomicEvidence,Get-DeploymentEvidenceDigest
