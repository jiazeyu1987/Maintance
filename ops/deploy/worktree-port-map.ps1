$script:IntRuoyiFrontendBasePort = 8081
$script:IntRuoyiBackendBasePort = 48081
$script:IntRuoyiRegistryRelativePath = 'worktrees\.ports\worktree-ports.json'

function ConvertTo-IntRuoyiWorktreeName {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [string]$Branch,
        [Parameter(Mandatory = $true)]
        [ValidateSet('ruoyi-vue-pro', 'yudao-ui-admin-vue3')]
        [string]$RepoFolder
    )

    $normalizedBranch = if ($Branch) { $Branch.Trim() } else { '' }
    if ($normalizedBranch.StartsWith('refs/heads/')) {
        $normalizedBranch = $normalizedBranch.Substring('refs/heads/'.Length)
    }
    if ($normalizedBranch -eq 'int_main') {
        return 'int_main'
    }
    if ($normalizedBranch.StartsWith('task/')) {
        return $normalizedBranch.Substring('task/'.Length)
    }
    if ($normalizedBranch.StartsWith('codex/')) {
        return $normalizedBranch.Substring('codex/'.Length)
    }

    $normalizedPath = ([System.IO.Path]::GetFullPath($Path.Replace('/', '\'))).TrimEnd('\')
    $pattern = '\\worktrees\\([^\\]+)\\' + [regex]::Escape($RepoFolder) + '$'
    if ($normalizedPath -match $pattern) {
        return $Matches[1]
    }
    $flatPattern = '\\worktrees\\' + [regex]::Escape($RepoFolder) + '-([^\\]+)$'
    if ($normalizedPath -match $flatPattern) {
        return $Matches[1]
    }

    throw "Cannot derive IntRuoyi worktree name from path [$Path] and branch [$Branch]."
}

function Get-IntRuoyiGitWorktrees {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RepoPath,
        [Parameter(Mandatory = $true)]
        [ValidateSet('frontend', 'backend')]
        [string]$Kind
    )

    if (-not (Test-Path -LiteralPath $RepoPath)) {
        throw "Missing $Kind repository path: $RepoPath"
    }

    $repoFolder = if ($Kind -eq 'frontend') { 'yudao-ui-admin-vue3' } else { 'ruoyi-vue-pro' }
    $lines = & git -C $RepoPath worktree list --porcelain
    if ($LASTEXITCODE -ne 0) {
        throw "git worktree list failed for $Kind repository: $RepoPath"
    }

    $rawEntries = New-Object System.Collections.Generic.List[object]
    $current = $null
    foreach ($line in $lines) {
        if ($line.StartsWith('worktree ')) {
            if ($null -ne $current) {
                $rawEntries.Add([PSCustomObject]$current)
            }
            $current = [ordered]@{
                Path = $line.Substring('worktree '.Length)
                Branch = ''
                Head = ''
            }
            continue
        }
        if ($null -eq $current) {
            continue
        }
        if ($line.StartsWith('branch ')) {
            $current.Branch = $line.Substring('branch '.Length)
        } elseif ($line.StartsWith('HEAD ')) {
            $current.Head = $line.Substring('HEAD '.Length)
        }
    }
    if ($null -ne $current) {
        $rawEntries.Add([PSCustomObject]$current)
    }

    $entries = @()
    foreach ($entry in $rawEntries) {
        $fullPath = [System.IO.Path]::GetFullPath($entry.Path.Replace('/', '\'))
        if (-not (Test-Path -LiteralPath $fullPath)) {
            throw "Stale $Kind worktree path listed by git. Prune or repair it first: $fullPath"
        }
        $entries += [PSCustomObject]@{
            Name = ConvertTo-IntRuoyiWorktreeName -Path $fullPath -Branch $entry.Branch -RepoFolder $repoFolder
            Path = $fullPath.TrimEnd('\')
            Branch = $entry.Branch
            Head = $entry.Head
            Kind = $Kind
        }
    }

    return @($entries)
}

function Assert-IntRuoyiUnique {
    param(
        [object[]]$Items,
        [string]$PropertyName,
        [string]$Label
    )

    $duplicates = @($Items |
        Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_.($PropertyName)) } |
        Group-Object -Property $PropertyName |
        Where-Object { $_.Count -gt 1 } |
        Select-Object -ExpandProperty Name)
    if ($duplicates.Count -gt 0) {
        throw "$Label has duplicate $PropertyName values: $($duplicates -join ', ')"
    }
}

function Assert-IntRuoyiPairedWorktrees {
    param(
        [object[]]$FrontendWorktrees,
        [object[]]$BackendWorktrees
    )

    Assert-IntRuoyiUnique -Items $FrontendWorktrees -PropertyName 'Name' -Label 'frontend worktrees'
    Assert-IntRuoyiUnique -Items $BackendWorktrees -PropertyName 'Name' -Label 'backend worktrees'

    $frontendNames = @($FrontendWorktrees | Select-Object -ExpandProperty Name | Sort-Object)
    $backendNames = @($BackendWorktrees | Select-Object -ExpandProperty Name | Sort-Object)

    if (($frontendNames | Where-Object { $_ -eq 'int_main' } | Measure-Object).Count -ne 1) {
        throw 'frontend worktrees must include exactly one int_main worktree.'
    }
    if (($backendNames | Where-Object { $_ -eq 'int_main' } | Measure-Object).Count -ne 1) {
        throw 'backend worktrees must include exactly one int_main worktree.'
    }

    $missingBackend = @($frontendNames | Where-Object { $_ -notin $backendNames })
    $missingFrontend = @($backendNames | Where-Object { $_ -notin $frontendNames })
    if ($missingBackend.Count -gt 0 -or $missingFrontend.Count -gt 0) {
        throw "frontend/backend worktree name mismatch. Missing backend: [$($missingBackend -join ', ')]; missing frontend: [$($missingFrontend -join ', ')]."
    }
}

function Get-IntRuoyiSortedActiveNames {
    param([object[]]$Worktrees)

    $names = @($Worktrees | Select-Object -ExpandProperty Name | Sort-Object)
    return @('int_main') + @($names | Where-Object { $_ -ne 'int_main' })
}

function Read-IntRuoyiWorktreePortRegistry {
    param([Parameter(Mandatory = $true)][string]$RegistryPath)

    if (-not (Test-Path -LiteralPath $RegistryPath)) {
        return $null
    }

    $json = [System.IO.File]::ReadAllText($RegistryPath, [System.Text.UTF8Encoding]::new($false))
    if ([string]::IsNullOrWhiteSpace($json)) {
        throw "Worktree port registry is empty: $RegistryPath"
    }
    return $json | ConvertFrom-Json
}

function New-IntRuoyiAssignment {
    param(
        [string]$Name,
        [int]$FrontendPort,
        [int]$BackendPort,
        [bool]$Active,
        [object]$FrontendWorktree,
        [object]$BackendWorktree,
        [object]$ExistingAssignment
    )

    [PSCustomObject][ordered]@{
        Name = $Name
        FrontendPort = $FrontendPort
        BackendPort = $BackendPort
        Active = $Active
        FrontendPath = if ($FrontendWorktree) { $FrontendWorktree.Path } elseif ($ExistingAssignment) { $ExistingAssignment.FrontendPath } else { $null }
        BackendPath = if ($BackendWorktree) { $BackendWorktree.Path } elseif ($ExistingAssignment) { $ExistingAssignment.BackendPath } else { $null }
        FrontendBranch = if ($FrontendWorktree) { $FrontendWorktree.Branch } elseif ($ExistingAssignment) { $ExistingAssignment.FrontendBranch } else { $null }
        BackendBranch = if ($BackendWorktree) { $BackendWorktree.Branch } elseif ($ExistingAssignment) { $ExistingAssignment.BackendBranch } else { $null }
    }
}

function New-IntRuoyiWorktreePortPlan {
    param(
        [Parameter(Mandatory = $true)]
        [object[]]$FrontendWorktrees,
        [Parameter(Mandatory = $true)]
        [object[]]$BackendWorktrees,
        [object]$ExistingRegistry,
        [int]$BaseFrontendPort = $script:IntRuoyiFrontendBasePort,
        [int]$BaseBackendPort = $script:IntRuoyiBackendBasePort
    )

    $FrontendWorktrees = @($FrontendWorktrees)
    $BackendWorktrees = @($BackendWorktrees)
    Assert-IntRuoyiPairedWorktrees -FrontendWorktrees $FrontendWorktrees -BackendWorktrees $BackendWorktrees

    if ($null -ne $ExistingRegistry) {
        if ($null -eq $ExistingRegistry.BaseFrontendPort -or $null -eq $ExistingRegistry.BaseBackendPort) {
            throw 'Existing worktree port registry is missing base port fields.'
        }
        if ([int]$ExistingRegistry.BaseFrontendPort -ne $BaseFrontendPort -or [int]$ExistingRegistry.BaseBackendPort -ne $BaseBackendPort) {
            throw "Existing worktree port registry base ports do not match expected $BaseFrontendPort/$BaseBackendPort."
        }
    }

    $existingAssignments = @()
    if ($null -ne $ExistingRegistry -and $null -ne $ExistingRegistry.Assignments) {
        $existingAssignments = @($ExistingRegistry.Assignments)
    }

    Assert-IntRuoyiUnique -Items $existingAssignments -PropertyName 'Name' -Label 'existing port registry'
    Assert-IntRuoyiUnique -Items $existingAssignments -PropertyName 'FrontendPort' -Label 'existing port registry'
    Assert-IntRuoyiUnique -Items $existingAssignments -PropertyName 'BackendPort' -Label 'existing port registry'

    $existingByName = @{}
    $maxFrontendPort = $BaseFrontendPort - 1
    $maxBackendPort = $BaseBackendPort - 1
    foreach ($assignment in $existingAssignments) {
        if ([string]::IsNullOrWhiteSpace($assignment.Name)) {
            throw 'Existing worktree port registry contains an assignment without Name.'
        }
        if ($null -eq $assignment.FrontendPort -or $null -eq $assignment.BackendPort) {
            throw "Existing worktree port registry assignment [$($assignment.Name)] is missing ports."
        }
        if ($assignment.Name -eq 'int_main' -and ([int]$assignment.FrontendPort -ne $BaseFrontendPort -or [int]$assignment.BackendPort -ne $BaseBackendPort)) {
            throw "Existing worktree port registry must keep int_main at $BaseFrontendPort/$BaseBackendPort."
        }
        $existingByName[$assignment.Name] = $assignment
        $maxFrontendPort = [Math]::Max($maxFrontendPort, [int]$assignment.FrontendPort)
        $maxBackendPort = [Math]::Max($maxBackendPort, [int]$assignment.BackendPort)
    }

    $frontendByName = @{}
    foreach ($worktree in $FrontendWorktrees) {
        $frontendByName[$worktree.Name] = $worktree
    }
    $backendByName = @{}
    foreach ($worktree in $BackendWorktrees) {
        $backendByName[$worktree.Name] = $worktree
    }

    $activeNames = Get-IntRuoyiSortedActiveNames -Worktrees $FrontendWorktrees
    $activeNameSet = @{}
    $assignments = @()
    foreach ($name in $activeNames) {
        $activeNameSet[$name] = $true
        $frontendWorktree = $frontendByName[$name]
        $backendWorktree = $backendByName[$name]
        if ($existingByName.ContainsKey($name)) {
            $existing = $existingByName[$name]
            $frontendPort = [int]$existing.FrontendPort
            $backendPort = [int]$existing.BackendPort
        } elseif ($name -eq 'int_main') {
            $existing = $null
            $frontendPort = $BaseFrontendPort
            $backendPort = $BaseBackendPort
            $maxFrontendPort = [Math]::Max($maxFrontendPort, $frontendPort)
            $maxBackendPort = [Math]::Max($maxBackendPort, $backendPort)
        } else {
            $existing = $null
            $maxFrontendPort += 1
            $maxBackendPort += 1
            $frontendPort = $maxFrontendPort
            $backendPort = $maxBackendPort
        }
        $assignments += New-IntRuoyiAssignment -Name $name -FrontendPort $frontendPort -BackendPort $backendPort -Active $true -FrontendWorktree $frontendWorktree -BackendWorktree $backendWorktree -ExistingAssignment $existing
    }

    foreach ($assignment in ($existingAssignments | Sort-Object Name)) {
        if ($activeNameSet.ContainsKey($assignment.Name)) {
            continue
        }
        $assignments += New-IntRuoyiAssignment -Name $assignment.Name -FrontendPort ([int]$assignment.FrontendPort) -BackendPort ([int]$assignment.BackendPort) -Active $false -FrontendWorktree $null -BackendWorktree $null -ExistingAssignment $assignment
    }

    Assert-IntRuoyiUnique -Items $assignments -PropertyName 'Name' -Label 'planned port registry'
    Assert-IntRuoyiUnique -Items $assignments -PropertyName 'FrontendPort' -Label 'planned port registry'
    Assert-IntRuoyiUnique -Items $assignments -PropertyName 'BackendPort' -Label 'planned port registry'

    return [PSCustomObject][ordered]@{
        SchemaVersion = 1
        BaseFrontendPort = $BaseFrontendPort
        BaseBackendPort = $BaseBackendPort
        UpdatedAt = (Get-Date).ToUniversalTime().ToString('o')
        Assignments = @($assignments)
    }
}

function Get-IntRuoyiBackendRepoRootFromScript {
    return (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path.TrimEnd('\')
}

function Get-IntRuoyiWorktreeInventory {
    param([string]$CurrentBackendRepoRoot = (Get-IntRuoyiBackendRepoRootFromScript))

    $backendWorktrees = Get-IntRuoyiGitWorktrees -RepoPath $CurrentBackendRepoRoot -Kind 'backend'
    $mainBackend = @($backendWorktrees | Where-Object { $_.Name -eq 'int_main' })
    if ($mainBackend.Count -ne 1) {
        throw 'backend worktrees must include exactly one int_main entry to locate the IntRuoyi workspace root.'
    }

    $workspaceRoot = (Split-Path -Parent $mainBackend[0].Path).TrimEnd('\')
    $frontendMain = Join-Path $workspaceRoot 'yudao-ui-admin-vue3'
    $frontendWorktrees = Get-IntRuoyiGitWorktrees -RepoPath $frontendMain -Kind 'frontend'

    return [PSCustomObject]@{
        WorkspaceRoot = $workspaceRoot
        RegistryPath = Join-Path $workspaceRoot $script:IntRuoyiRegistryRelativePath
        FrontendWorktrees = @($frontendWorktrees)
        BackendWorktrees = @($backendWorktrees)
    }
}

function Write-IntRuoyiWorktreePortRegistry {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RegistryPath,
        [Parameter(Mandatory = $true)]
        [object]$Plan
    )

    $registryDir = Split-Path -Parent $RegistryPath
    if (-not (Test-Path -LiteralPath $registryDir)) {
        New-Item -ItemType Directory -Path $registryDir -Force | Out-Null
    }
    $payload = $Plan | ConvertTo-Json -Depth 10
    [System.IO.File]::WriteAllText($RegistryPath, $payload, [System.Text.UTF8Encoding]::new($false))
}

function Sync-IntRuoyiWorktreePorts {
    param(
        [string]$CurrentBackendRepoRoot = (Get-IntRuoyiBackendRepoRootFromScript),
        [switch]$NoWrite
    )

    $inventory = Get-IntRuoyiWorktreeInventory -CurrentBackendRepoRoot $CurrentBackendRepoRoot
    $existingRegistry = Read-IntRuoyiWorktreePortRegistry -RegistryPath $inventory.RegistryPath
    $plan = New-IntRuoyiWorktreePortPlan -FrontendWorktrees $inventory.FrontendWorktrees -BackendWorktrees $inventory.BackendWorktrees -ExistingRegistry $existingRegistry
    $plan | Add-Member -NotePropertyName WorkspaceRoot -NotePropertyValue $inventory.WorkspaceRoot
    $plan | Add-Member -NotePropertyName RegistryPath -NotePropertyValue $inventory.RegistryPath
    if (-not $NoWrite) {
        Write-IntRuoyiWorktreePortRegistry -RegistryPath $inventory.RegistryPath -Plan $plan
    }
    return $plan
}

function Resolve-IntRuoyiWorktreeNameFromBackendRoot {
    param(
        [Parameter(Mandatory = $true)]
        [string]$BackendRepoRoot,
        [Parameter(Mandatory = $true)]
        [object[]]$BackendWorktrees
    )

    $normalizedRoot = ([System.IO.Path]::GetFullPath($BackendRepoRoot)).TrimEnd('\')
    $match = @($BackendWorktrees | Where-Object { ([System.IO.Path]::GetFullPath($_.Path)).TrimEnd('\') -ieq $normalizedRoot })
    if ($match.Count -eq 1) {
        return $match[0].Name
    }
    throw "Cannot resolve current backend worktree name from path: $BackendRepoRoot"
}

function New-IntRuoyiMainPortContext {
    param([string]$CurrentBackendRepoRoot = (Get-IntRuoyiBackendRepoRootFromScript))

    $backendRepoRoot = (Resolve-Path $CurrentBackendRepoRoot).Path.TrimEnd('\')
    $workspaceRoot = (Split-Path -Parent $backendRepoRoot).TrimEnd('\')
    $frontendPath = Join-Path $workspaceRoot 'yudao-ui-admin-vue3'
    if (-not (Test-Path -LiteralPath $frontendPath)) {
        throw "Missing int_main frontend path: $frontendPath"
    }

    return [PSCustomObject]@{
        Name = 'int_main'
        WorkspaceRoot = $workspaceRoot
        RegistryPath = Join-Path $workspaceRoot $script:IntRuoyiRegistryRelativePath
        FrontendPath = $frontendPath
        BackendPath = $backendRepoRoot
        FrontendPort = [int]$script:IntRuoyiFrontendBasePort
        BackendPort = [int]$script:IntRuoyiBackendBasePort
    }
}

function Get-IntRuoyiWorktreePortContext {
    param(
        [string]$WorktreeName,
        [string]$CurrentBackendRepoRoot = (Get-IntRuoyiBackendRepoRootFromScript)
    )

    if ($WorktreeName -eq 'int_main') {
        return New-IntRuoyiMainPortContext -CurrentBackendRepoRoot $CurrentBackendRepoRoot
    }

    $plan = Sync-IntRuoyiWorktreePorts -CurrentBackendRepoRoot $CurrentBackendRepoRoot
    if ([string]::IsNullOrWhiteSpace($WorktreeName)) {
        $inventory = Get-IntRuoyiWorktreeInventory -CurrentBackendRepoRoot $CurrentBackendRepoRoot
        $WorktreeName = Resolve-IntRuoyiWorktreeNameFromBackendRoot -BackendRepoRoot $CurrentBackendRepoRoot -BackendWorktrees $inventory.BackendWorktrees
    }

    $assignment = @($plan.Assignments | Where-Object { $_.Name -eq $WorktreeName -and $_.Active }) | Select-Object -First 1
    if ($null -eq $assignment) {
        throw "No active IntRuoyi worktree port assignment found for [$WorktreeName]."
    }

    return [PSCustomObject]@{
        Name = $assignment.Name
        WorkspaceRoot = $plan.WorkspaceRoot
        RegistryPath = $plan.RegistryPath
        FrontendPath = $assignment.FrontendPath
        BackendPath = $assignment.BackendPath
        FrontendPort = [int]$assignment.FrontendPort
        BackendPort = [int]$assignment.BackendPort
    }
}
