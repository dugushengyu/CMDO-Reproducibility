$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$owner       = 'dugushengyu'
$stagingRepo = 'CMDO-Reproducibility'
$branch      = 'oam-bootstrap-20260917'
$projectRepo = 'MelaninAnchored-DeltaMap-Reproducibility'
$root        = Join-Path $HOME $projectRepo
$tmpZip      = Join-Path $env:TEMP 'oam_pipeline_active.zip'
$tmpExtract  = Join-Path $env:TEMP 'oam_pipeline_extract'
$rawUrl      = "https://raw.githubusercontent.com/$owner/$stagingRepo/$branch/oam-bootstrap/oam_pipeline_active.zip"
$expectedSha = '2a1839e758595f7d4a0c8ecab2972e3cb939187cb91e843ff163c9e944c23eae'

Write-Host '============================================================'
Write-Host ' Melanin-Anchored Delta-Map — clean-room bootstrap'
Write-Host ' MATLAB active pipeline + PowerShell orchestration'
Write-Host '============================================================'

foreach ($cmd in @('git','matlab')) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        throw "Required command not found on PATH: $cmd"
    }
}

# GitHub CLI is used only to create/push the private reproducibility repo.
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host '[SETUP] Installing GitHub CLI...'
        winget install --id GitHub.cli -e --source winget --accept-package-agreements --accept-source-agreements
    }
}
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw 'GitHub CLI (gh) is required. Install it, then rerun this block.'
}

try { gh auth status *> $null } catch {
    Write-Host '[SETUP] GitHub login required; browser login will open.'
    gh auth login --web --git-protocol https
}

# Fresh local clean-room. Never touch the old delta-map/DL folders.
if (Test-Path $root) {
    $dirty = $false
    if (Test-Path (Join-Path $root '.git')) {
        Push-Location $root
        try { $dirty = -not [string]::IsNullOrWhiteSpace((git status --porcelain)) } finally { Pop-Location }
    }
    if ($dirty) { throw "Existing workspace has uncommitted changes: $root" }
    Write-Host "[CLEAN] Removing previous clean-room: $root"
    Remove-Item -Recurse -Force $root
}
if (Test-Path $tmpExtract) { Remove-Item -Recurse -Force $tmpExtract }
New-Item -ItemType Directory -Force -Path $tmpExtract | Out-Null

Write-Host '[FETCH] Downloading the active pipeline from the sealed staging branch...'
Invoke-WebRequest -Uri $rawUrl -OutFile $tmpZip -UseBasicParsing
$actualSha = (Get-FileHash $tmpZip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualSha -ne $expectedSha) {
    throw "Bootstrap SHA256 mismatch. Expected $expectedSha, got $actualSha"
}
Write-Host "[PASS] Pipeline SHA256: $actualSha"

Expand-Archive -LiteralPath $tmpZip -DestinationPath $tmpExtract -Force
$src = Join-Path $tmpExtract 'oam_bootstrap_pkg'
if (-not (Test-Path $src)) { throw "Package root missing: $src" }
Move-Item -Path $src -Destination $root

# Machine-local paths. This file is gitignored and is never pushed.
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
$config | Set-Content -LiteralPath (Join-Path $root 'config\oam_local_config.m') -Encoding UTF8

Push-Location $root
try {
    git init | Out-Null
    git config core.longpaths true
    git checkout -B main | Out-Null
    git add .
    git commit -m 'Initialize MATLAB/PowerShell OAM reproducibility pipeline' | Out-Null

    $repoFull = "$owner/$projectRepo"
    gh repo view $repoFull *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[GITHUB] Creating private repo $repoFull ..."
        gh repo create $repoFull --private --description 'Melanin-anchored Delta-map OAM reproducibility pipeline' --confirm
    }
    $remote = "https://github.com/$repoFull.git"
    if ((git remote) -contains 'origin') { git remote set-url origin $remote } else { git remote add origin $remote }
    git push -u origin main --force
    Write-Host "[PASS] Code pushed to private GitHub repo: $repoFull"

    Write-Host ''
    Write-Host '============================================================'
    Write-Host ' STARTING FULL MATLAB RUN'
    Write-Host ' Stage 00 will audit Hb/HbO2/Hbt scale, then the pipeline'
    Write-Host ' automatically uses the supported oxygenation definition.'
    Write-Host '============================================================'

    & powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1
    if ($LASTEXITCODE -ne 0) { throw "Full pipeline failed with exit code $LASTEXITCODE" }

    $workRoot = 'D:\Xiu ting data clear results\MelaninAnchoredDeltaMap_Repro'
    $reportDir = Join-Path $root 'run_reports\latest'
    if (Test-Path $reportDir) { Remove-Item -Recurse -Force $reportDir }
    New-Item -ItemType Directory -Force -Path $reportDir | Out-Null

    # Only non-identifying aggregate summaries are mirrored to GitHub.
    # Raw scans, patient Excel, pair-level tables, paths, logs and images stay local.
    $safeFiles = @(
        @{Src=(Join-Path $workRoot 'results\audit\UR_scale_summary.txt'); Dst='UR_scale_summary.txt'},
        @{Src=(Join-Path $workRoot 'results\FINAL\RUN_SUMMARY.txt'); Dst='RUN_SUMMARY.txt'},
        @{Src=(Join-Path $workRoot 'results\FINAL\MANUSCRIPT_UPDATE_NOTES.md'); Dst='MANUSCRIPT_UPDATE_NOTES.md'},
        @{Src=(Join-Path $workRoot 'results\Figure3\DiseaseModels_ranked.csv'); Dst='Figure3_DiseaseModels_ranked.csv'},
        @{Src=(Join-Path $workRoot 'results\Figure3\SeverityBinaryModels_eczema_ranked.csv'); Dst='Figure3_EczemaModels_ranked.csv'},
        @{Src=(Join-Path $workRoot 'results\Figure3\SeverityBinaryModels_psoriasis_ranked.csv'); Dst='Figure3_PsoriasisModels_ranked.csv'},
        @{Src=(Join-Path $workRoot 'results\Figure5\Fig5B_canonical_spectrum.csv'); Dst='Figure5_canonical_spectrum.csv'},
        @{Src=(Join-Path $workRoot 'results\Figure5\Fig5D_physics_loadings.csv'); Dst='Figure5_physics_loadings.csv'},
        @{Src=(Join-Path $workRoot 'results\Figure5\Fig5E_ai_loadings.csv'); Dst='Figure5_ai_loadings.csv'}
    )
    foreach ($f in $safeFiles) {
        if (Test-Path $f.Src) { Copy-Item $f.Src (Join-Path $reportDir $f.Dst) -Force }
    }

    $meta = @"
# Latest clean-room run

Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')

Only aggregate/non-identifying summaries are mirrored here. Raw OAM data, severity Excel, pair-level tables, local paths, logs and image outputs remain local.
"@
    $meta | Set-Content -LiteralPath (Join-Path $reportDir 'README.md') -Encoding UTF8

    git add -f run_reports/latest
    git commit -m 'Record latest non-identifying clean-room summaries' | Out-Null
    git push origin main

    $head = git rev-parse HEAD
    $status = git status --porcelain
    if (-not [string]::IsNullOrWhiteSpace($status)) { throw 'Final Git worktree is not clean.' }

    Write-Host ''
    Write-Host '============================================================'
    Write-Host ' FINAL PASS'
    Write-Host " Repo:   $repoFull"
    Write-Host " HEAD:   $head"
    Write-Host " Local:  $root"
    Write-Host " Output: $workRoot"
    Write-Host ' Git worktree: CLEAN'
    Write-Host ' Safe aggregate run summaries: PUSHED'
    Write-Host '============================================================'
}
finally {
    Pop-Location
}
