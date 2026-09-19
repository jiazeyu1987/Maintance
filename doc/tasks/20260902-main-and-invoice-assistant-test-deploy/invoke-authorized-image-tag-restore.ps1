param(
    [Parameter(Mandatory = $true)]
    [string]$ExpectedCurrentTag,

    [Parameter(Mandatory = $true)]
    [string]$RestoreTag,

    [string]$ServerHost = '172.30.30.58',

    [string]$ServerUser = 'root'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

foreach ($tag in @($ExpectedCurrentTag, $RestoreTag)) {
    if ($tag -notmatch '^[A-Za-z0-9_.-]{1,128}$') {
        throw "Invalid IMAGE_TAG value: $tag"
    }
}

$remoteScript = @'
set -eu

expected_current="$1"
restore_tag="$2"
env_path=/opt/intruoyi/runtime/.env

case "$expected_current" in ""|*[!A-Za-z0-9_.-]*) echo "invalid_expected_tag=$expected_current" >&2; exit 10;; esac
case "$restore_tag" in ""|*[!A-Za-z0-9_.-]*) echo "invalid_restore_tag=$restore_tag" >&2; exit 11;; esac

[ -f "$env_path" ]
[ ! -L "$env_path" ]
before_count=$(grep -c '^IMAGE_TAG=' "$env_path" || true)
[ "$before_count" -eq 1 ]
before_tag=$(sed -n 's/^IMAGE_TAG=//p' "$env_path")
[ "$before_tag" = "$expected_current" ]
before_meta=$(stat -c '%a:%u:%g' "$env_path")

tmp_path=$(mktemp "${env_path}.codex-image-tag-restore.XXXXXX")
cleanup() {
  rm -f "$tmp_path"
}
trap cleanup EXIT HUP INT TERM

awk -v restored="$restore_tag" '/^IMAGE_TAG=/{print "IMAGE_TAG=" restored; next} {print}' "$env_path" > "$tmp_path"
chown --reference="$env_path" "$tmp_path"
chmod --reference="$env_path" "$tmp_path"
mv -f "$tmp_path" "$env_path"
trap - EXIT HUP INT TERM

after_count=$(grep -c '^IMAGE_TAG=' "$env_path" || true)
after_tag=$(sed -n 's/^IMAGE_TAG=//p' "$env_path")
after_meta=$(stat -c '%a:%u:%g' "$env_path")
[ "$after_count" -eq 1 ]
[ "$after_tag" = "$restore_tag" ]
[ "$after_meta" = "$before_meta" ]

printf 'REMOTE_IMAGE_TAG_RESTORE_DONE\n'
printf 'before_tag=%s\n' "$before_tag"
printf 'after_tag=%s\n' "$after_tag"
printf 'image_tag_count=%s\n' "$after_count"
printf 'metadata=%s\n' "$after_meta"
'@

$normalizedRemoteScript = $remoteScript -replace "`r`n", "`n"
$payloadBytes = [System.Text.Encoding]::UTF8.GetBytes($normalizedRemoteScript)
$sha256 = [System.Security.Cryptography.SHA256]::Create()
try {
    $payloadSha = [System.BitConverter]::ToString(
        $sha256.ComputeHash($payloadBytes)
    ).Replace('-', '').ToLowerInvariant()
}
finally {
    $sha256.Dispose()
}

$psi = [System.Diagnostics.ProcessStartInfo]::new()
$psi.FileName = 'ssh.exe'
$psi.ArgumentList.Add("${ServerUser}@${ServerHost}")
$psi.ArgumentList.Add('bash')
$psi.ArgumentList.Add('-s')
$psi.ArgumentList.Add('--')
$psi.ArgumentList.Add($ExpectedCurrentTag)
$psi.ArgumentList.Add($RestoreTag)
$psi.RedirectStandardInput = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.UseShellExecute = $false

$process = [System.Diagnostics.Process]::Start($psi)
$process.StandardInput.BaseStream.Write($payloadBytes, 0, $payloadBytes.Length)
$process.StandardInput.Close()
$stdout = $process.StandardOutput.ReadToEnd()
$stderr = $process.StandardError.ReadToEnd()
$process.WaitForExit()

Write-Output "payload_bytes=$($payloadBytes.Length)"
Write-Output "payload_sha256=$payloadSha"
Write-Output $stdout
if (-not [string]::IsNullOrWhiteSpace($stderr)) {
    Write-Output "ssh_stderr_present=true"
}

if ($process.ExitCode -ne 0) {
    throw "remote image tag restore failed with exit code $($process.ExitCode); stderr=$stderr; stdout=$stdout"
}

if ($stdout -notmatch 'REMOTE_IMAGE_TAG_RESTORE_DONE') {
    throw "remote image tag restore marker missing; stdout=$stdout"
}
