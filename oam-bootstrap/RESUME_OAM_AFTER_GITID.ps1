$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoFull = 'dugushengyu/MelaninAnchored-DeltaMap-Reproducibility'
$root = Join-Path $HOME 'MelaninAnchored-DeltaMap-Reproducibility'
$workRoot = 'D:\Xiu ting data clear results\MelaninAnchoredDeltaMap_Repro'
$gitName = 'Z.Y.XU'
$gitEmail = '63897600+dugushengyu@users.noreply.github.com'

function Invoke-Native {
    param(
        [Parameter(Mandatory=$true)][scriptblock]$Command,
        [Parameter(Mandatory=$true)][string]$Label
    )
    $old = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $Command
        $code = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $old
    }
    if ($code -ne 0) { throw "$Label failed with exit code $code" }
}

Write-Host '============================================================'
Write-Host ' OAM CLEANROOM - RESUME AFTER GIT IDENTITY CHECKPOINT'
Write-Host '============================================================'

# Refresh PATH so gh installed by winget is visible to child PowerShell sessions.
$machinePath = [Environment]::GetEnvironmentVariable('Path','Machine')
$userPath = [Environment]::GetEnvironmentVariable('Path','User')
$env:Path = "$machinePath;$userPath"
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    $ghCandidate = Join-Path $env:ProgramFiles 'GitHub CLI\gh.exe'
    if (Test-Path $ghCandidate) { $env:Path = "$(Split-Path $ghCandidate);$env:Path" }
}

foreach ($cmd in @('gh','git','matlab')) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        throw "Required command not found on PATH: $cmd"
    }
}

if (-not (Test-Path (Join-Path $root '.git'))) {
    throw "Expected clean-room Git repository is missing: $root"
}
if (-not (Test-Path (Join-Path $root 'run.ps1'))) {
    throw "Verified active package is missing run.ps1: $root"
}

$old = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& gh auth status *> $null
$authCode = $LASTEXITCODE
$ErrorActionPreference = $old
if ($authCode -ne 0) { throw 'GitHub CLI is not authenticated.' }
Write-Host '[PASS] Existing clean-room and GitHub authentication found.'

Push-Location $root
try {
    git config core.longpaths true
    git config user.name $gitName
    git config user.email $gitEmail
    Write-Host "[PASS] Repository-local Git identity set: $gitName <$gitEmail>"

    # Never commit the machine-local config, even if the package .gitignore is changed later.
    $localConfig = 'config/oam_local_config.m'
    $infoExclude = Join-Path $root '.git\info\exclude'
    $excludeText = if (Test-Path $infoExclude) { [IO.File]::ReadAllText($infoExclude) } else { '' }
    if ($excludeText -notmatch '(?m)^config/oam_local_config\.m\s*$') {
        [IO.File]::AppendAllText($infoExclude, "`r`nconfig/oam_local_config.m`r`n", [Text.UTF8Encoding]::new($false))
    }
    $old = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    git reset -- $localConfig *> $null
    $ErrorActionPreference = $old
    if (-not (Test-Path (Join-Path $root $localConfig))) { throw 'Machine-local config unexpectedly missing.' }
    Write-Host '[PASS] Machine-local config protected from Git commits.'

    git add .
    $pending = @(git status --porcelain)
    if ($pending.Count -gt 0) {
        Write-Host '[COMMIT] Committing verified active pipeline...'
        Invoke-Native -Label 'Active-code commit' -Command { git commit -m 'Install verified active MATLAB and PowerShell reproducibility pipeline' }
        Invoke-Native -Label 'Active-code push' -Command { git push origin main }
        Write-Host '[PASS] Active pipeline committed and pushed.'
    }
    else {
        Write-Host '[PASS] No active-code changes need committing.'
    }

    Write-Host '============================================================'
    Write-Host ' STARTING FULL MATLAB RUN'
    Write-Host ' Stage 00 audits Hb/HbO2/Hbt scale before downstream stages.'
    Write-Host '============================================================'

    & powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1
    if ($LASTEXITCODE -ne 0) { throw "Pipeline failed with exit code $LASTEXITCODE" }
    Write-Host '[PASS] Full MATLAB/PowerShell pipeline completed.'

    # Mirror only aggregate/non-identifying summaries to GitHub.
    $reportDir = Join-Path $root 'run_reports\latest'
    if (Test-Path $reportDir) { Remove-Item -Recurse -Force $reportDir }
    New-Item -ItemType Directory -Force -Path $reportDir | Out-Null

    $safe = @(
        @('results\audit\UR_scale_summary.txt','UR_scale_summary.txt'),
        @('results\FINAL\RUN_SUMMARY.txt','RUN_SUMMARY.txt'),
        @('results\FINAL\MANUSCRIPT_UPDATE_NOTES.md','MANUSCRIPT_UPDATE_NOTES.md'),
        @('results\Figure3\DiseaseModels_ranked.csv','Figure3_DiseaseModels_ranked.csv'),
        @('results\Figure3\SeverityBinaryModels_eczema_ranked.csv','Figure3_EczemaModels_ranked.csv'),
        @('results\Figure3\SeverityBinaryModels_psoriasis_ranked.csv','Figure3_PsoriasisModels_ranked.csv'),
        @('results\Figure5\Fig5B_canonical_spectrum.csv','Figure5_canonical_spectrum.csv'),
        @('results\Figure5\Fig5D_physics_loadings.csv','Figure5_physics_loadings.csv'),
        @('results\Figure5\Fig5E_ai_loadings.csv','Figure5_ai_loadings.csv')
    )
    $copied = 0
    foreach ($x in $safe) {
        $src = Join-Path $workRoot $x[0]
        if (Test-Path $src) {
            Copy-Item -LiteralPath $src -Destination (Join-Path $reportDir $x[1]) -Force
            $copied++
        }
    }

    $meta = "# Latest clean-room run`r`n`r`nGenerated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')`r`n`r`nOnly aggregate/non-identifying summaries are mirrored here. Raw OAM data, severity Excel, pair-level tables, local paths, logs and image outputs remain local.`r`n"
    [IO.File]::WriteAllText((Join-Path $reportDir 'README.md'), $meta, [Text.UTF8Encoding]::new($false))
    Write-Host "[REPORT] Aggregate/non-identifying summaries copied: $copied"

    git add -f run_reports/latest
    $reportPending = @(git status --porcelain)
    if ($reportPending.Count -gt 0) {
        Invoke-Native -Label 'Run-summary commit' -Command { git commit -m 'Record latest non-identifying clean-room summaries' }
        Invoke-Native -Label 'Run-summary push' -Command { git push origin main }
        Write-Host '[PASS] Safe run summaries committed and pushed.'
    }

    $head = (git rev-parse HEAD).Trim()
    $dirtyFinal = @(git status --porcelain)
    if ($dirtyFinal.Count -gt 0) {
        Write-Host '[DIAGNOSTIC] Remaining Git status:'
        git status --short
        throw 'Final Git worktree is not clean.'
    }

    Write-Host '============================================================'
    Write-Host ' FINAL PASS'
    Write-Host " Repo:   $repoFull"
    Write-Host " HEAD:   $head"
    Write-Host " Local:  $root"
    Write-Host " Output: $workRoot"
    Write-Host ' Git worktree: CLEAN'
    Write-Host ' Aggregate summaries: PUSHED'
    Write-Host '============================================================'
}
finally {
    Pop-Location
}
