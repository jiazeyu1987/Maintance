$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$configPath = 'C:\SpugHandoff\release\executor.private.json'
$utf8 = [System.Text.UTF8Encoding]::new($false)
$original = [System.IO.File]::ReadAllText($configPath, $utf8)
$document = $original | ConvertFrom-Json
$beforeAcl = (Microsoft.PowerShell.Security\Get-Acl -LiteralPath $configPath).Sddl
$expected = @{ test = '172.30.30.58'; prod = '172.30.30.57' }
foreach ($name in @('test', 'prod')) {
    if ($document.targets.$name.host -ne $expected[$name] -or
        $document.targets.$name.fenbeitongAssistantHost -ne 'fenbeitong-assistant') {
        throw 'Registered target identity differs; profile preserved.'
    }
    if ($document.targets.$name.PSObject.Properties.Name -contains 'fenbeitongAssistantUrl') {
        throw 'Public URL already exists; inspect concurrent change before editing.'
    }
}
# Replace only two exact host-local anchors; preserve every other original byte.
$updated = $original
foreach ($name in @('test', 'prod')) {
    $hostText = $expected[$name]
    $pattern = '(?s)("' + $name + '"\s*:\s*\{.*?"fenbeitongAssistantHost"\s*:\s*"fenbeitong-assistant")'
    $regex = [System.Text.RegularExpressions.Regex]::new($pattern)
    if ($regex.Matches($updated).Count -ne 1) { throw 'Profile anchor is ambiguous.' }
    $insertion = ',"fenbeitongAssistantUrl":"http://' + $hostText + ':18734/"'
    $updated = $regex.Replace($updated, ('$1' + $insertion), 1)
}
$parsed = $updated | ConvertFrom-Json
foreach ($name in @('test', 'prod')) {
    if ($parsed.targets.$name.fenbeitongAssistantUrl -ne ('http://' + $expected[$name] + ':18734/')) {
        throw 'Prepared public URL differs.'
    }
}
$privateDir = Split-Path -Parent $configPath
$nonce = [Guid]::NewGuid().ToString('N')
$probe = Join-Path $privateDir ('fenbeitong-url-probe-' + $nonce)
$probeNew = $probe + '.new'
$probeBackup = $probe + '.before'
[System.IO.File]::WriteAllText($probe, 'old', $utf8)
[System.IO.File]::WriteAllText($probeNew, 'new', $utf8)
$probeAcl = (Microsoft.PowerShell.Security\Get-Acl -LiteralPath $probe).Sddl
[System.IO.File]::Replace($probeNew, $probe, $probeBackup)
if ([System.IO.File]::ReadAllText($probe, $utf8) -ne 'new' -or
    [System.IO.File]::ReadAllText($probeBackup, $utf8) -ne 'old' -or
    (Microsoft.PowerShell.Security\Get-Acl -LiteralPath $probe).Sddl -ne $probeAcl) {
    throw 'Atomic replacement/ACL probe failed; original configuration untouched.'
}
Remove-Item -LiteralPath $probe, $probeBackup
$prepared = Join-Path $privateDir ('fenbeitong-url-prepared-' + $nonce)
$backup = Join-Path $privateDir ('executor.before-fenbeitong-url-' + $nonce + '.private.json')
[System.IO.File]::WriteAllText($prepared, $updated, $utf8)
# Detect an intervening edit before replacing the original.
if ([System.IO.File]::ReadAllText($configPath, $utf8) -cne $original -or
    (Microsoft.PowerShell.Security\Get-Acl -LiteralPath $configPath).Sddl -ne $beforeAcl) {
    throw 'Concurrent profile or ACL change; original configuration preserved.'
}
[System.IO.File]::Replace($prepared, $configPath, $backup)
if ([System.IO.File]::ReadAllText($configPath, $utf8) -cne $updated -or
    [System.IO.File]::ReadAllText($backup, $utf8) -cne $original -or
    (Microsoft.PowerShell.Security\Get-Acl -LiteralPath $configPath).Sddl -ne $beforeAcl -or
    (Microsoft.PowerShell.Security\Get-Acl -LiteralPath $backup).Sddl -ne $beforeAcl) {
    throw 'Configuration readback or ACL differs; inspect actual replacement result and private backup.'
}
Write-Output 'PASS: local test/prod public URLs registered; original bytes and ACL retained in private backup.'
Write-Output ('Private recovery file: ' + $backup)
