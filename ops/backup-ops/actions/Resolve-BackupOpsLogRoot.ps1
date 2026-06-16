param(
    [Parameter(Mandatory = $true)]
    [string]$ConfigPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

try {
    $resolvedConfigPath = [System.IO.Path]::GetFullPath($ConfigPath)
    if (-not (Test-Path -LiteralPath $resolvedConfigPath)) {
        throw "缺少日志配置文件: $resolvedConfigPath"
    }

    $configText = [System.IO.File]::ReadAllText(
        $resolvedConfigPath,
        [System.Text.UTF8Encoding]::new($false)
    )
    $config = $configText | ConvertFrom-Json

    if ($null -eq $config.console) {
        throw "配置缺少 console 节点: $resolvedConfigPath"
    }

    $logRoot = [string]$config.console.logRoot
    if ([string]::IsNullOrWhiteSpace($logRoot)) {
        throw "配置缺少 console.logRoot: $resolvedConfigPath"
    }

    $resolvedLogRoot = if ([System.IO.Path]::IsPathRooted($logRoot)) {
        [System.IO.Path]::GetFullPath($logRoot)
    } else {
        [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $logRoot))
    }

    [Console]::Write($resolvedLogRoot)
    exit 0
}
catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 2
}
