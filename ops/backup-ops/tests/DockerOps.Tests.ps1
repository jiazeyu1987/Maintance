$ErrorActionPreference = 'Stop'

$modulePath = Join-Path $PSScriptRoot '..\scripts\modules\Infra\DockerOps.psm1'
Import-Module $modulePath -Force -DisableNameChecking

Describe 'Wait-BackupOpsRemoteHttpOk' {
    It 'bounds each remote health probe with curl and SSH process timeouts' {
        InModuleScope DockerOps {
            function Invoke-BackupSshCommand {
                param(
                    [Parameter(Mandatory)]
                    [hashtable]$Request
                )

                $script:CapturedRemoteHealthRequest = $Request
                return [pscustomobject]@{
                    output = 'OK'
                }
            }

            try {
                Wait-BackupOpsRemoteHttpOk `
                    -SshRequest @{ Host = '172.30.30.58'; User = 'root' } `
                    -Url 'http://127.0.0.1:48081/actuator/health' `
                    -Code 'INTBK-5003' `
                    -TimeoutSeconds 180

                $script:CapturedRemoteHealthRequest.ContainsKey('TimeoutSeconds') | Should Be $true
                $script:CapturedRemoteHealthRequest.TimeoutSeconds | Should Be 15
                $script:CapturedRemoteHealthRequest.Command | Should Match 'curl --connect-timeout 5 --max-time 10 -fsS'
            } finally {
                Remove-Item -Path function:\Invoke-BackupSshCommand -ErrorAction SilentlyContinue
                Remove-Variable -Name CapturedRemoteHealthRequest -Scope Script -ErrorAction SilentlyContinue
            }
        }
    }
}
