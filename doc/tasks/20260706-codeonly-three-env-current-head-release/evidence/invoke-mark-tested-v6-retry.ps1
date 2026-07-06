$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
& 'D:\ProjectPackage\Int\IntRuoyiWorktrees\r260706ce\m\ops\deploy\publish-int-ruoyi.ps1' `
  -Mode 'mark-tested' `
  -ReleaseTag 'release-20260706-2245-codeonly-three-env-v6' `
  -NasConfigPath 'D:\ProjectPackage\Int\IntRuoyiWorktrees\r260706ce\m\runtime\runtime-control\nas-release-config\manual-release-20260706-v5.json' `
  -BackendRepoRoot 'D:\ProjectPackage\Int\IntRuoyiWorktrees\r260706ce\b' `
  -FrontendRepoRoot 'D:\ProjectPackage\Int\IntRuoyiWorktrees\r260706ce\f' `
  -TestConclusion '回归通过_允许上线正式服_codeonly三环境v6' `
  -SelectedRecoverySetCandidateId 'restore:20260621-063218' `
  -RecoverySetId '20260621-063218' `
  -RecoverySetManifestHash '6806edb9075622a5dbe646e2a1dca1ea499472cc610e070161b68f7249aecf66' `
  -RecoverySetProgramVersion 'release-20260620-current-head-prod-target-v7' `
  -RecoverySetRedisPolicy 'CLEAR_AND_REBUILD' `
  -SkipDatabaseSync `
  -SkipMinioSync