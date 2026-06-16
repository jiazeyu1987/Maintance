Set-StrictMode -Version Latest

function Read-BackupOpsMenuChoice {
    [CmdletBinding()]
    param()

    $choice = Read-Host -Prompt '请输入编号'
    return $choice.Trim()
}

function Read-BackupNowConfirmation {
    [CmdletBinding()]
    param()

    Write-Host '即将执行“立即备份”。' -ForegroundColor Cyan
    Write-Host ''
    Write-Host '影响范围:'
    Write-Host '- 导出正式库 MySQL'
    Write-Host '- 备份 MinIO yudao 桶对象'
    Write-Host '- 同步到测试服务器备份仓库'
    Write-Host ''
    Write-Host '本操作不会停止前端或后端服务。'
    Write-Host ''
    $answer = Read-Host -Prompt '确认执行请输入 Y，取消请输入 N'
    $answer = $answer.Trim().ToUpperInvariant()
    return $answer -eq 'Y'
}

function Read-RollbackAppConfirmation {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$ImageTag
    )

    Write-Host '即将执行“回滚应用版本”。' -ForegroundColor Yellow
    Write-Host ''
    Write-Host '影响范围:'
    Write-Host '- 修改正式环境 IMAGE_TAG'
    Write-Host '- 重启 backend / frontend'
    Write-Host '- 不恢复数据库'
    Write-Host '- 不恢复对象文件'
    Write-Host ''
    Write-Host ("目标版本: {0}" -f $ImageTag)
    Write-Host '请确认当前问题属于“版本/发布异常”，不是“数据异常”。'
    Write-Host ''
    $answer = Read-Host -Prompt '确认执行请输入 Y，取消请输入 N'
    $answer = $answer.Trim().ToUpperInvariant()
    return $answer -eq 'Y'
}

function Read-RestoreDataConfirmation {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$BackupId
    )

    Write-Host '警告：即将执行“恢复数据”。' -ForegroundColor Red
    Write-Host ''
    Write-Host '影响范围:'
    Write-Host '- 停止 backend / frontend'
    Write-Host '- 覆盖数据库到指定恢复点'
    Write-Host '- 覆盖对象文件到指定恢复点'
    Write-Host '- 执行前会自动生成 pre-restore 保护快照'
    Write-Host ''
    Write-Host ("目标恢复点: {0}" -f $BackupId)
    Write-Host '该操作不可作为日常试探性操作使用。'
    Write-Host ''
    $answer = Read-Host -Prompt '确认执行请输入 RESTORE，取消请输入 N'
    $answer = $answer.Trim().ToUpperInvariant()
    return $answer -eq 'RESTORE'
}

function Select-BackupOpsImageTag {
    [CmdletBinding()]
    param(
        [object[]]$Candidates = @(),

        [string]$SelectedImageTag
    )

    if ($SelectedImageTag) {
        return $SelectedImageTag
    }

    if ($null -eq $Candidates) {
        $Candidates = @()
    }

    if ($Candidates.Count -eq 0) {
        return $null
    }

    Write-Host '可回滚 IMAGE_TAG 列表:'
    for ($index = 0; $index -lt $Candidates.Count; $index++) {
        Write-Host ("[{0}] {1}" -f ($index + 1), $Candidates[$index])
    }

    $choice = Read-Host -Prompt '请选择回滚版本编号'
    $choice = $choice.Trim()
    $parsedIndex = 0
    if (-not [int]::TryParse($choice, [ref]$parsedIndex)) {
        return $null
    }

    $position = $parsedIndex - 1
    if ($position -lt 0 -or $position -ge $Candidates.Count) {
        return $null
    }

    return [string]$Candidates[$position]
}

function Select-BackupOpsRestorePoint {
    [CmdletBinding()]
    param(
        [object[]]$Candidates = @(),

        [string]$SelectedBackupId
    )

    if ($SelectedBackupId) {
        return $SelectedBackupId
    }

    if ($null -eq $Candidates) {
        $Candidates = @()
    }

    if ($Candidates.Count -eq 0) {
        return $null
    }

    Write-Host '可恢复备份点列表:'
    for ($index = 0; $index -lt $Candidates.Count; $index++) {
        $candidate = $Candidates[$index]
        if ($candidate -is [string]) {
            Write-Host ("[{0}] {1}" -f ($index + 1), $candidate)
            continue
        }

        $backupId = $candidate.backupId
        $status = $candidate.status
        $imageTag = $candidate.imageTag
        $completedAt = $candidate.completedAt

        Write-Host ("[{0}] {1}" -f ($index + 1), $backupId)
        Write-Host ("    类型: {0}" -f $candidate.backupType)
        Write-Host ("    状态: {0}" -f $status)
        Write-Host ("    镜像版本: {0}" -f $imageTag)
        Write-Host ("    完成时间: {0}" -f $completedAt)
    }

    $choice = Read-Host -Prompt '请选择恢复点编号'
    $choice = $choice.Trim()
    $parsedIndex = 0
    if (-not [int]::TryParse($choice, [ref]$parsedIndex)) {
        return $null
    }

    $position = $parsedIndex - 1
    if ($position -lt 0 -or $position -ge $Candidates.Count) {
        return $null
    }

    $selected = $Candidates[$position]
    if ($selected -is [string]) {
        return $selected
    }

    return [string]$selected.backupId
}

Export-ModuleMember -Function @(
    'Read-BackupOpsMenuChoice',
    'Read-BackupNowConfirmation',
    'Read-RollbackAppConfirmation',
    'Read-RestoreDataConfirmation',
    'Select-BackupOpsImageTag',
    'Select-BackupOpsRestorePoint'
)
