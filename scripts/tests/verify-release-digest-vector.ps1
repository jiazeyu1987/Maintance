$ErrorActionPreference = 'Stop'

$repositoryRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$modulePath = Join-Path $repositoryRoot 'ops\release\lib\ReleasePackageGovernance.psm1'
Import-Module -Force $modulePath

$artifacts = @(
    [pscustomobject]@{
        path = 'required-sql/001.sql'
        bytes = [int64]10
        sha256 = 'b4e0497804e46e0a0b0b8c31975b062152d551bac49c3c2e80932567b4085dcd'
    },
    [pscustomobject]@{
        path = 'docker-compose.yml'
        bytes = [int64]10
        sha256 = 'fa73fccdc99ea835967c7dee7efbed1f3ca87260d92931850fdd66da8cb12f1d'
    }
)

$package = Get-ReleasePackageDigest -Artifacts $artifacts
if ($package.PackageDigest -cne 'b3920c523e8739501931bd5b68811bf7350b2a742960023b2fe1b7925adb0273') {
    throw "package digest mismatch: $($package.PackageDigest)"
}

$manifestBytes = [System.Text.UTF8Encoding]::new($false).GetBytes(
    '{"schemaVersion":2,"packageDigest":"b3920c523e8739501931bd5b68811bf7350b2a742960023b2fe1b7925adb0273"}' + "`n"
)
$manifestDigest = Get-ReleaseBytesSha256Hex -Bytes $manifestBytes
if ($manifestDigest -cne 'bb44ed6ea9550e067c1a2af3a105a0989503b046646f26bd1bac19455bee2800') {
    throw "manifest digest mismatch: $manifestDigest"
}

foreach ($invalidArtifacts in @(
    @([pscustomobject]@{ path = 'required-sql\001.sql'; bytes = [int64]1; sha256 = ('0' * 64) }),
    @(
        [pscustomobject]@{ path = 'A/file.txt'; bytes = [int64]1; sha256 = ('0' * 64) },
        [pscustomobject]@{ path = 'a/file.txt'; bytes = [int64]1; sha256 = ('1' * 64) }
    )
)) {
    try {
        $null = Get-ReleasePackageDigest -Artifacts $invalidArtifacts
        throw 'invalid artifact path was accepted'
    } catch {
        if ($_.Exception.Message -notmatch 'PACKAGE_PATH_INVALID') {
            throw
        }
    }
}

Write-Host 'PowerShell release digest vector passed'
