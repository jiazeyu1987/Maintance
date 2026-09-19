param(
    [Parameter(Mandatory = $true)]
    [string]$ArtifactPath,

    [Parameter(Mandatory = $true)]
    [string]$ImageTag,

    [string]$ServerHost = '172.30.30.58',

    [string]$ServerUser = 'root'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not (Test-Path -LiteralPath $ArtifactPath -PathType Leaf)) {
    throw "Artifact not found: $ArtifactPath"
}

if ($ImageTag -notmatch '^[A-Za-z0-9_.-]{1,64}$') {
    throw "Invalid image tag: $ImageTag"
}

$artifactItem = Get-Item -LiteralPath $ArtifactPath
$expectedSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $ArtifactPath).Hash.ToLowerInvariant()
$remoteArtifact = "/tmp/$($artifactItem.Name)"
$remoteTarget = "${ServerUser}@${ServerHost}:$remoteArtifact"

& scp.exe $ArtifactPath $remoteTarget
if ($LASTEXITCODE -ne 0) {
    throw "scp failed with exit code $LASTEXITCODE"
}

$remoteScript = @'
set -eu

artifact_path="$1"
expected_sha="$2"
image_tag="$3"

case "$image_tag" in
  ""|*[!A-Za-z0-9_.-]*)
    echo "invalid_image_tag=$image_tag" >&2
    exit 10
    ;;
esac

app_dir=/opt/intruoyi/runtime/erp-invoice-voucher-print-assistant
unit_path=/etc/systemd/system/erp-invoice-voucher-print-assistant.service
tmp_extract=$(mktemp -d "$app_dir/source-build.XXXXXX")

cleanup() {
  rm -rf "$tmp_extract"
}
trap cleanup EXIT HUP INT TERM

[ -f "$artifact_path" ]
actual_sha=$(sha256sum "$artifact_path" | awk '{print $1}')
[ "$actual_sha" = "$expected_sha" ]

fragment_path=$(systemctl show -p FragmentPath --value erp-invoice-voucher-print-assistant.service 2>/dev/null || true)
if [ -n "$fragment_path" ] && [ "$fragment_path" != "$unit_path" ]; then
  echo "unexpected_unit_path=$fragment_path" >&2
  exit 11
fi

mkdir -p "$app_dir/runtime" "$app_dir/results" "$app_dir/uploads"
tar -xf "$artifact_path" -C "$tmp_extract"
[ -f "$tmp_extract/Dockerfile" ]
[ -f "$tmp_extract/server.js" ]
[ -f "$tmp_extract/package.json" ]

image="erp-invoice-voucher-print-assistant:$image_tag"
docker build --pull=false -t "$image" "$tmp_extract"

cat > "$unit_path.tmp" <<UNIT
[Unit]
Description=ERP Invoice Voucher Print Assistant
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=simple
Restart=always
RestartSec=5
ExecStart=/usr/bin/docker run --name erp-invoice-voucher-print-assistant --rm --network host --pull never -e INVOICE_RENAMER_HOST=0.0.0.0 -e INVOICE_RENAMER_PORT=18733 -e INVOICE_VOUCHER_PRINT_TICKET_VALIDATE_URL=http://127.0.0.1:48081/admin-api/system/auth/invoice-voucher-print-ticket/validate -e INVOICE_VOUCHER_PRINT_SESSION_TTL_SECONDS=14400 -v /opt/intruoyi/runtime/erp-invoice-voucher-print-assistant/runtime:/opt/invoice-voucher-print-assistant/runtime -v /opt/intruoyi/runtime/erp-invoice-voucher-print-assistant/results:/opt/invoice-voucher-print-assistant/浏览器运行结果 -v /opt/intruoyi/runtime/erp-invoice-voucher-print-assistant/uploads:/opt/invoice-voucher-print-assistant/服务器上传发票 $image
ExecStop=/usr/bin/docker stop erp-invoice-voucher-print-assistant

[Install]
WantedBy=multi-user.target
UNIT

mv -f "$unit_path.tmp" "$unit_path"
systemctl daemon-reload
systemctl restart erp-invoice-voucher-print-assistant.service
sleep 3

systemctl is-active --quiet erp-invoice-voucher-print-assistant.service
running_image=$(docker inspect -f '{{.Config.Image}}' erp-invoice-voucher-print-assistant)
running_state=$(docker inspect -f '{{.State.Status}}' erp-invoice-voucher-print-assistant)
[ "$running_image" = "$image" ]
[ "$running_state" = "running" ]
ss -ltn | grep -q ':18733 '
assistant_http=$(curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:18733/)
[ "$assistant_http" = "403" ]

printf 'REMOTE_ASSISTANT_DEPLOY_SUCCESS\n'
printf 'artifact_sha256=%s\n' "$actual_sha"
printf 'image=%s\n' "$running_image"
printf 'state=%s\n' "$running_state"
printf 'assistant_http=%s\n' "$assistant_http"
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
$psi.ArgumentList.Add($remoteArtifact)
$psi.ArgumentList.Add($expectedSha)
$psi.ArgumentList.Add($ImageTag)
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

if ($process.ExitCode -ne 0) {
    throw "remote deploy failed with exit code $($process.ExitCode); stderr=$stderr; stdout=$stdout"
}

if ($stdout -notmatch 'REMOTE_ASSISTANT_DEPLOY_SUCCESS') {
    throw "remote deploy success marker missing; stdout=$stdout"
}

Write-Output "payload_bytes=$($payloadBytes.Length)"
Write-Output "payload_sha256=$payloadSha"
Write-Output $stdout
