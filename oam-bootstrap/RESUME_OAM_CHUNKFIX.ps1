$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoFull = 'dugushengyu/MelaninAnchored-DeltaMap-Reproducibility'
$root = Join-Path $HOME 'MelaninAnchored-DeltaMap-Reproducibility'
$sourceClone = Join-Path $env:TEMP 'OAM_BOOTSTRAP_SOURCE'
$tmpZip = Join-Path $env:TEMP 'oam_pipeline_active_slim.zip'
$tmpExtract = Join-Path $env:TEMP 'oam_pipeline_active_extract'
$expectedZipSha = '1bad2fc6d784a696aa5e2bf3b61caa3d78596aa8ed0ac4749bf8ecf44c1db23a'
$workRoot = 'D:\Xiu ting data clear results\MelaninAnchoredDeltaMap_Repro'

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
Write-Host ' OAM CLEANROOM - CHUNK RECOVERY BOOTSTRAP'
Write-Host '============================================================'

foreach ($cmd in @('gh','git','matlab')) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        throw "Required command not found on PATH: $cmd"
    }
}

$old = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& gh auth status *> $null
$authCode = $LASTEXITCODE
$ErrorActionPreference = $old
if ($authCode -ne 0) { throw 'GitHub CLI is not authenticated. Run gh auth login first.' }
Write-Host '[PASS] GitHub authentication available.'

# Pull the private bootstrap source into a disposable location.
if (Test-Path $sourceClone) { Remove-Item -Recurse -Force $sourceClone }
Write-Host '[FETCH] Cloning private bootstrap/chunk source...'
Invoke-Native -Label 'Private bootstrap clone' -Command { gh repo clone $repoFull $sourceClone -- --depth 1 }

$chunkDir = Join-Path $sourceClone 'bootstrap\chunks'
if (-not (Test-Path $chunkDir)) { throw "Chunk directory not found: $chunkDir" }

# Exact manifest: part09.txt is intentionally NOT used; it was replaced by 09a + 09b.
$parts = @()
foreach ($i in 1..8) { $parts += Join-Path $chunkDir ('part{0:D2}.txt' -f $i) }
$parts += Join-Path $chunkDir 'part09a.txt'
$parts += Join-Path $chunkDir 'part09b.txt'
foreach ($i in 10..12) { $parts += Join-Path $chunkDir ('part{0:D2}.txt' -f $i) }

foreach ($p in $parts) {
    if (-not (Test-Path $p)) { throw "Missing bootstrap chunk: $p" }
}
Write-Host "[PASS] Chunk manifest complete: $($parts.Count) parts."

Write-Host '[ASSEMBLE] Reconstructing complete ZIP from text chunks...'
$b64 = New-Object System.Text.StringBuilder
foreach ($p in $parts) {
    $txt = [IO.File]::ReadAllText($p).Trim()
    [void]$b64.Append($txt)
}
try {
    $bytes = [Convert]::FromBase64String($b64.ToString())
}
catch {
    throw "Base64 reconstruction failed: $($_.Exception.Message)"
}
[IO.File]::WriteAllBytes($tmpZip, $bytes)

$actualSha = (Get-FileHash $tmpZip -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "[HASH] $actualSha"
if ($actualSha -ne $expectedZipSha) {
    throw "Reconstructed ZIP SHA mismatch. Expected $expectedZipSha, got $actualSha"
}
Write-Host '[PASS] Complete ZIP SHA256 verified.'

# Validate the central directory before extraction. This catches the exact failure
# seen with the earlier 7.5 KB truncated staging ZIP.
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zipHandle = $null
try {
    $zipHandle = [System.IO.Compression.ZipFile]::OpenRead($tmpZip)
    $entryCount = $zipHandle.Entries.Count
    if ($entryCount -lt 1) { throw 'ZIP opened but contains no entries.' }
}
finally {
    if ($null -ne $zipHandle) { $zipHandle.Dispose() }
}
Write-Host "[PASS] ZIP central directory verified: $entryCount entries."

if (Test-Path $tmpExtract) { Remove-Item -Recurse -Force $tmpExtract }
New-Item -ItemType Directory -Force -Path $tmpExtract | Out-Null
Expand-Archive -LiteralPath $tmpZip -DestinationPath $tmpExtract -Force
$pkg = Join-Path $tmpExtract 'oam_bootstrap_pkg'
if (-not (Test-Path (Join-Path $pkg 'run.ps1'))) { throw 'Extracted package is missing run.ps1.' }
if (-not (Test-Path (Join-Path $pkg 'matlab'))) { throw 'Extracted package is missing matlab directory.' }
$fileCount = @(Get-ChildItem -LiteralPath $pkg -Recurse -File).Count
Write-Host "[PASS] Package extraction verified: $fileCount files."

# Rebuild the final local clean-room from the private GitHub repo.
if (Test-Path $root) {
    $dirty = $false
    if (Test-Path (Join-Path $root '.git')) {
        Push-Location $root
        try { $dirty = (@(git status --porcelain).Count -gt 0) }
        finally { Pop-Location }
    }
    if ($dirty) { throw "Existing workspace has uncommitted changes: $root" }
    Write-Host "[CLEAN] Removing previous clean-room: $root"
    Remove-Item -Recurse -Force $root
}

Write-Host "[CLONE] $repoFull -> $root"
Invoke-Native -Label 'Final clean-room clone' -Command { gh repo clone $repoFull $root -- --depth 1 }

# Overlay the verified active package while preserving the repo bootstrap folder.
$old = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
robocopy $pkg $root /E /NFL /NDL /NJH /NJS /NP | Out-Null
$robocopyCode = $LASTEXITCODE
$ErrorActionPreference = $old
if ($robocopyCode -ge 8) { throw "robocopy failed with exit code $robocopyCode" }
Write-Host '[PASS] Verified active package installed into clean-room.'

# Machine-local paths. This file should remain gitignored by the active package.
$configDir = Join-Path $root 'config'
if (-not (Test-Path $configDir)) { New-Item -ItemType Directory -Force -Path $configDir | Out-Null }
$config = @'
function cfg = oam_local_config()
cfg.rawDataRoot   = 'D:\Xiuting Data\002021EczemaMSOM_rLabProcessed';
cfg.severityExcel = 'D:\astar work\AStar DL\severity record.xlsx';
cfg.workRoot      = 'D:\Xiu ting data clear results\MelaninAnchoredDeltaMap_Repro';
cfg.datasetRoot   = fullfile(cfg.workRoot, 'dataset');
cfg.resultsRoot   = fullfile(cfg.workRoot, 'results');
cfg.logsRoot      = fullfile(cfg.workRoot, 'logs');
cfg.sourceVarName='UR_flat'; cfg.projMode='mean'; cfg.useGPU=true;
cfg.dz_mm=0.01; cfg.dx_mm=0.01; cfg.roughnessThreshold=25.0;
cfg.lowPct=1; cfg.highPct=99; cfg.binEdges_mm=[0 0.268 0.468 2.500];
cfg.oxygenationMode='auto'; cfg.auditMaxFiles=20;
cfg.auditCorrThreshold=0.99; cfg.auditRelativeErrorThreshold=0.08;
cfg.tbvMode='per_scan_robust_normalized_Hbt';
cfg.randomSeed=1; cfg.dpi=300; cfg.fontName='Arial'; cfg.fontSize=13;
cfg.imgH=128; cfg.imgW=128; cfg.latentDim=64; cfg.maxEpochs=1500;
cfg.miniBatchSize=16; cfg.initialLearnRate=1e-4; cfg.l2Reg=1e-3;
cfg.nCVrep=200; cfg.testFrac=0.30; cfg.nPermModel=2000; cfg.nPermFinal=5000; cfg.nBootDensity=1000;
cfg.syntheticShiftPx=[0 2 5 10 15 20];
cfg.maxLatentPCsForCCA=10; cfg.displayCanonicalModes=3; cfg.displayTopAIPCs=5;
end
'@
[IO.File]::WriteAllText((Join-Path $configDir 'oam_local_config.m'), $config, (New-Object System.Text.UTF8Encoding($false)))
Write-Host '[PASS] Machine-local configuration written.'

Push-Location $root
try {
    git config core.longpaths true
    git add .
    $pending = @(git status --porcelain)
    if ($pending.Count -gt 0) {
        Invoke-Native -Label 'Active-code commit' -Command { git commit -m 'Install verified active MATLAB and PowerShell reproducibility pipeline' }
        Invoke-Native -Label 'Active-code push' -Command { git push origin main }
    }
    else {
        Write-Host '[PASS] Active code already committed.'
    }

    Write-Host '============================================================'
    Write-Host ' STARTING FULL MATLAB RUN'
    Write-Host ' Stage 00 audits Hb/HbO2/Hbt scale before downstream stages.'
    Write-Host '============================================================'
    & powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1
    if ($LASTEXITCODE -ne 0) { throw "Pipeline failed with exit code $LASTEXITCODE" }

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
    foreach ($x in $safe) {
        $src = Join-Path $workRoot $x[0]
        if (Test-Path $src) { Copy-Item -LiteralPath $src -Destination (Join-Path $reportDir $x[1]) -Force }
    }

    $meta = "# Latest clean-room run`r`n`r`nGenerated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')`r`n`r`nOnly aggregate/non-identifying summaries are mirrored here. Raw OAM data, severity Excel, pair-level tables, local paths, logs and image outputs remain local.`r`n"
    [IO.File]::WriteAllText((Join-Path $reportDir 'README.md'), $meta, (New-Object System.Text.UTF8Encoding($false)))

    git add -f run_reports/latest
    $reportPending = @(git status --porcelain)
    if ($reportPending.Count -gt 0) {
        Invoke-Native -Label 'Run-summary commit' -Command { git commit -m 'Record latest non-identifying clean-room summaries' }
        Invoke-Native -Label 'Run-summary push' -Command { git push origin main }
    }

    $head = (git rev-parse HEAD).Trim()
    $dirtyFinal = @(git status --porcelain)
    if ($dirtyFinal.Count -gt 0) { throw 'Final Git worktree is not clean.' }

    Write-Host '============================================================'
    Write-Host ' FINAL PASS'
    Write-Host " Repo:   $repoFull"
    Write-Host " HEAD:   $head"
    Write-Host " Local:  $root"
    Write-Host " Output: $workRoot"
    Write-Host ' Git worktree: CLEAN'
    Write-Host ' Aggregate summaries: PUSHED (when present)'
    Write-Host '============================================================'
}
finally {
    Pop-Location
}
