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

function Test-PowerShellSyntax {
    param([Parameter(Mandatory=$true)][string]$Path)
    $tokens = $null
    $errors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile($Path,[ref]$tokens,[ref]$errors)
    if ($errors.Count -gt 0) {
        Write-Host "[FAIL] Parser errors in $Path"
        foreach ($e in $errors) {
            Write-Host ("  line {0}, col {1}: {2}" -f $e.Extent.StartLineNumber,$e.Extent.StartColumnNumber,$e.Message)
        }
        throw "PowerShell syntax preflight failed: $Path"
    }
    Write-Host "[PASS] Syntax: $Path"
}

Write-Host '============================================================'
Write-Host ' OAM CLEANROOM - RESUME AFTER POWERSHELL PARSER FIX'
Write-Host '============================================================'

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

if (-not (Test-Path (Join-Path $root '.git'))) { throw "Clean-room repository missing: $root" }

$old = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& gh auth status *> $null
$authCode = $LASTEXITCODE
$ErrorActionPreference = $old
if ($authCode -ne 0) { throw 'GitHub CLI is not authenticated.' }

Push-Location $root
try {
    git config user.name $gitName
    git config user.email $gitEmail
    git config core.longpaths true

    $dirtyBefore = @(git status --porcelain)
    if ($dirtyBefore.Count -gt 0) {
        Write-Host '[DIAGNOSTIC] Local changes before update:'
        git status --short
        throw 'Local clean-room is not clean; refusing to overwrite it.'
    }

    $before = (git rev-parse HEAD).Trim()
    Write-Host "[HEAD before] $before"
    Write-Host '[UPDATE] Pulling parser/exit-code fixes from private repo...'
    Invoke-Native -Label 'git pull' -Command { git pull --ff-only origin main }
    $after = (git rev-parse HEAD).Trim()
    Write-Host "[HEAD after]  $after"

    $runner = Join-Path $root 'powershell\RUN_ALL.ps1'
    $entry = Join-Path $root 'run.ps1'
    Test-PowerShellSyntax -Path $runner
    Test-PowerShellSyntax -Path $entry

    # Also parse every PowerShell helper before starting MATLAB.
    $psFiles = @(Get-ChildItem -LiteralPath (Join-Path $root 'powershell') -Filter '*.ps1' -File)
    foreach ($ps in $psFiles) {
        if ($ps.FullName -ne $runner) { Test-PowerShellSyntax -Path $ps.FullName }
    }
    Write-Host '[PASS] PowerShell syntax preflight completed with zero parser errors.'

    Write-Host '============================================================'
    Write-Host ' STARTING FULL MATLAB RUN'
    Write-Host ' A real failure will now terminate with a non-zero exit code.'
    Write-Host '============================================================'

    $global:LASTEXITCODE = 0
    & powershell -NoProfile -ExecutionPolicy Bypass -File .\run.ps1
    $pipelineExit = $LASTEXITCODE
    if ($pipelineExit -ne 0) {
        throw "Full pipeline stopped correctly with exit code $pipelineExit"
    }
    Write-Host '[PASS] Full MATLAB/PowerShell pipeline completed with exit code 0.'

    # Only a genuinely successful run is allowed to refresh the mirrored summaries.
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
    if ($copied -eq 0) {
        throw 'Pipeline returned success but no expected aggregate summary files were found; refusing FINAL PASS.'
    }

    $meta = "# Latest verified clean-room run`r`n`r`nGenerated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')`r`n`r`nPipeline exit code: 0.`r`nAggregate/non-identifying summaries copied: $copied.`r`n`r`nRaw OAM data, severity Excel, pair-level tables, local paths, logs and image outputs remain local.`r`n"
    [IO.File]::WriteAllText((Join-Path $reportDir 'README.md'),$meta,[Text.UTF8Encoding]::new($false))

    git add -f run_reports/latest
    $pending = @(git status --porcelain)
    if ($pending.Count -gt 0) {
        Invoke-Native -Label 'Run-summary commit' -Command { git commit -m 'Record latest verified non-identifying clean-room summaries' }
        Invoke-Native -Label 'Run-summary push' -Command { git push origin main }
    }

    $head = (git rev-parse HEAD).Trim()
    $dirtyFinal = @(git status --porcelain)
    if ($dirtyFinal.Count -gt 0) {
        git status --short
        throw 'Final Git worktree is not clean.'
    }

    Write-Host '============================================================'
    Write-Host ' VERIFIED FINAL PASS'
    Write-Host " Repo:   $repoFull"
    Write-Host " HEAD:   $head"
    Write-Host " Local:  $root"
    Write-Host " Output: $workRoot"
    Write-Host " Aggregate summaries copied: $copied"
    Write-Host ' Git worktree: CLEAN'
    Write-Host '============================================================'
}
finally {
    Pop-Location
}
