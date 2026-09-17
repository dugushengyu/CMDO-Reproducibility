$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = Join-Path $HOME 'MelaninAnchored-DeltaMap-Reproducibility'
$workRoot = 'D:\Xiu ting data clear results\MelaninAnchoredDeltaMap_Repro'
$reportDir = Join-Path $root 'run_reports\latest'

Write-Host '============================================================'
Write-Host ' OAM CLEANROOM - FINALIZE VERIFIED RUN'
Write-Host '============================================================'

if (-not (Test-Path (Join-Path $root '.git'))) { throw "Repository not found: $root" }
if (-not (Test-Path $workRoot)) { throw "Work/output root not found: $workRoot" }

Push-Location $root
try {
    $dirtyBefore = @(git status --porcelain)
    if ($dirtyBefore.Count -gt 0) {
        Write-Host '[DIAGNOSTIC] Git status before finalization:'
        git status --short
        throw 'Repository worktree is not clean before finalization.'
    }

    $head = (git rev-parse HEAD).Trim()
    Write-Host "[HEAD] $head"

    if (Test-Path $reportDir) { Remove-Item -Recurse -Force $reportDir }
    New-Item -ItemType Directory -Force -Path $reportDir | Out-Null

    # Strict whitelist: aggregate/non-identifying outputs only.
    $safe = @(
        @('results\audit\UR_scale_summary.txt',                         'UR_scale_summary.txt'),
        @('results\FINAL\RUN_SUMMARY.txt',                            'RUN_SUMMARY.txt'),
        @('results\FINAL\MANUSCRIPT_UPDATE_NOTES.md',                 'MANUSCRIPT_UPDATE_NOTES.md'),
        @('results\Figure3\DiseaseModels_ranked.csv',                 'Figure3_DiseaseModels_ranked.csv'),
        @('results\Figure3\SeverityBinaryModels_eczema_ranked.csv',   'Figure3_EczemaModels_ranked.csv'),
        @('results\Figure3\SeverityBinaryModels_psoriasis_ranked.csv','Figure3_PsoriasisModels_ranked.csv'),
        @('results\Figure5\Fig5B_canonical_spectrum.csv',             'Figure5_canonical_spectrum.csv'),
        @('results\Figure5\Fig5D_physics_loadings.csv',               'Figure5_physics_loadings.csv'),
        @('results\Figure5\Fig5E_ai_loadings.csv',                    'Figure5_ai_loadings.csv'),
        @('results\Supplementary\FigureS1_QC_Retention.csv',          'FigureS1_QC_Retention.csv'),
        @('results\Supplementary\FigureS2_SyntheticShiftRobustness.csv','FigureS2_SyntheticShiftRobustness.csv'),
        @('results\Supplementary\FigureS3_metrics.txt',               'FigureS3_metrics.txt')
    )

    $copied = New-Object System.Collections.Generic.List[string]
    foreach ($x in $safe) {
        $src = Join-Path $workRoot $x[0]
        if (Test-Path $src) {
            Copy-Item -LiteralPath $src -Destination (Join-Path $reportDir $x[1]) -Force
            [void]$copied.Add($x[1])
            Write-Host "[COPY] $($x[1])"
        }
        else {
            Write-Host "[SKIP] Missing optional safe summary: $($x[0])"
        }
    }

    if ($copied.Count -lt 3) {
        throw "Too few verified aggregate summaries found ($($copied.Count)); refusing to finalize."
    }

    $meta = @"
# Latest verified clean-room run

Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')
Code HEAD at finalization: `$head`
Aggregate summaries copied: $($copied.Count)

This directory intentionally contains only aggregate/non-identifying summaries.
Raw OAM data, severity spreadsheets, pair-level records, local filesystem paths,
logs, MAT files, and image outputs remain local and are not mirrored here.
"@
    [IO.File]::WriteAllText((Join-Path $reportDir 'README.md'), $meta, [Text.UTF8Encoding]::new($false))

    # Privacy guard 1: machine-local configuration must remain untracked/unstaged.
    $localConfig = 'config/oam_local_config.m'
    $oldEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    git check-ignore -q -- $localConfig
    $ignoreCode = $LASTEXITCODE
    $ErrorActionPreference = $oldEap
    if ($ignoreCode -ne 0) { throw 'Privacy guard failed: config/oam_local_config.m is not ignored.' }

    # Stage ONLY the safe report directory.
    git add -f -- run_reports/latest

    # Privacy guard 2: reject any staged path outside the whitelist directory.
    $staged = @(git diff --cached --name-only)
    $badPaths = @($staged | Where-Object { $_ -notlike 'run_reports/latest/*' })
    if ($badPaths.Count -gt 0) {
        Write-Host '[BLOCK] Unexpected staged paths:'
        $badPaths | ForEach-Object { Write-Host "  $_" }
        git reset
        throw 'Privacy guard blocked commit: unexpected staged files.'
    }

    # Privacy guard 3: scan staged report text for obvious Windows local paths.
    $pathPatterns = @('C:\\Users\\','D:\\','E:\\')
    foreach ($p in $staged) {
        $full = Join-Path $root ($p -replace '/', '\')
        if (-not (Test-Path $full)) { continue }
        $text = [IO.File]::ReadAllText($full)
        foreach ($pat in $pathPatterns) {
            if ($text -match $pat) {
                git reset
                throw "Privacy guard blocked commit: local filesystem path found in $p"
            }
        }
    }

    $pending = @(git diff --cached --name-only)
    if ($pending.Count -eq 0) {
        Write-Host '[PASS] Safe aggregate reports already match GitHub; nothing to commit.'
    }
    else {
        git commit -m 'Record verified non-identifying OAM clean-room summaries'
        if ($LASTEXITCODE -ne 0) { throw 'Final summary commit failed.' }
        git push origin main
        if ($LASTEXITCODE -ne 0) { throw 'Final summary push failed.' }
        Write-Host '[PASS] Verified aggregate summaries committed and pushed.'
    }

    $dirtyAfter = @(git status --porcelain)
    if ($dirtyAfter.Count -gt 0) {
        Write-Host '[DIAGNOSTIC] Remaining Git status:'
        git status --short
        throw 'Final worktree is not clean.'
    }

    $finalHead = (git rev-parse HEAD).Trim()
    Write-Host '============================================================'
    Write-Host ' VERIFIED CLEANROOM FINAL PASS'
    Write-Host " HEAD: $finalHead"
    Write-Host " Aggregate summaries mirrored: $($copied.Count)"
    Write-Host ' Git worktree: CLEAN'
    Write-Host ' Raw/private/local-path material: NOT STAGED'
    Write-Host '============================================================'
}
finally {
    Pop-Location
}
