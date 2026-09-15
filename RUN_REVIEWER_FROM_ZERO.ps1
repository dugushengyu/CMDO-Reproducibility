param(
    [string]$DataRoot = "",
    [string]$WorkRoot = "",
    [string]$EnvRoot = "",
    [string]$Matlab = "",
    [ValidateSet("auto","cuda","cpu")]
    [string]$Device = "auto",
    [int]$Epochs = 12,
    [int]$WitnessReps = 100,
    [switch]$FreshEnvironment
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = $PSScriptRoot
Set-Location $RepoRoot

if (-not $WorkRoot) {
    $WorkRoot = Join-Path $env:USERPROFILE "CMDO_REVIEWER_RUN"
}
if (-not $DataRoot) {
    if ($env:CMDO_DATA_ROOT) {
        $DataRoot = $env:CMDO_DATA_ROOT
    } else {
        $DataRoot = Join-Path $env:USERPROFILE ".cmdo\public_data"
    }
}
if (-not $EnvRoot) {
    $local = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { $env:USERPROFILE }
    $EnvRoot = Join-Path $local "CMDO\reviewer_py311"
}

$WorkRoot = [System.IO.Path]::GetFullPath($WorkRoot)
$DataRoot = [System.IO.Path]::GetFullPath($DataRoot)
$EnvRoot = [System.IO.Path]::GetFullPath($EnvRoot)

if ($WorkRoot -eq $DataRoot) {
    throw "WorkRoot and DataRoot must be different. WorkRoot is deleted at the start of each clean reviewer run; DataRoot is the persistent public-data cache."
}

Write-Host "============================================================"
Write-Host " CMDO REVIEWER FROM-ZERO RUN"
Write-Host "============================================================"
Write-Host "Repository : $RepoRoot"
Write-Host "Work root  : $WorkRoot"
Write-Host "Data cache : $DataRoot"
Write-Host "Env root   : $EnvRoot"
Write-Host "Device     : $Device"
Write-Host "Epochs     : $Epochs"
Write-Host ""

if (Test-Path (Join-Path $RepoRoot ".git")) {
    $status = git status --porcelain --untracked-files=all
    if ($LASTEXITCODE -ne 0) { throw "git status failed" }
    if ($status) { throw ("Repository must be clean before reviewer run." + [Environment]::NewLine + $status) }
    $head = git rev-parse HEAD
    Write-Host "Git HEAD   : $head"
}

function Find-Python311 {
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        $candidate = & $launcher.Source -3.11 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $candidate) {
            return ($candidate | Select-Object -First 1).Trim()
        }
    }

    foreach ($name in @("python.exe","python3.exe","python")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) {
            $ver = & $cmd.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if ($LASTEXITCODE -eq 0 -and ($ver | Select-Object -First 1).Trim() -eq "3.11") {
                return $cmd.Source
            }
        }
    }
    throw "Python 3.11 was not found. Install Python 3.11, then rerun this script."
}

$BasePython = Find-Python311
Write-Host "Python 3.11: $BasePython"

if ($FreshEnvironment -and (Test-Path $EnvRoot)) {
    Write-Host "Removing prior reviewer Python environment: $EnvRoot"
    Remove-Item $EnvRoot -Recurse -Force
}

$VenvPython = Join-Path $EnvRoot "Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "Creating fresh reviewer Python environment..."
    & $BasePython -m venv $EnvRoot
    if ($LASTEXITCODE -ne 0) { throw "Python venv creation failed" }
}

& $VenvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }

$TorchIndex = "https://download.pytorch.org/whl/cpu"
$TorchLabel = "cpu"

if ($Device -ne "cpu") {
    $smi = Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue
    if ($smi) {
        $smiText = (& $smi.Source 2>&1 | Out-String)
        $cudaMatch = [regex]::Match($smiText, "CUDA Version:\s*([0-9]+\.[0-9]+)")
        if ($cudaMatch.Success) {
            $driverCuda = [version]$cudaMatch.Groups[1].Value
            if ($driverCuda -ge [version]"12.8") {
                $TorchLabel = "cu128"
                $TorchIndex = "https://download.pytorch.org/whl/cu128"
            } elseif ($driverCuda -ge [version]"12.6") {
                $TorchLabel = "cu126"
                $TorchIndex = "https://download.pytorch.org/whl/cu126"
            }
            Write-Host "NVIDIA driver CUDA capability: $driverCuda"
        }
    }

    if ($Device -eq "cuda" -and $TorchLabel -eq "cpu") {
        throw "CUDA was explicitly requested, but no compatible NVIDIA driver (CUDA >= 12.6) was detected."
    }
}

Write-Host "PyTorch build selected: $TorchLabel"
& $VenvPython -m pip install torch==2.12.1 torchvision==0.27.1 --index-url $TorchIndex
if ($LASTEXITCODE -ne 0) { throw "PyTorch installation failed" }

& $VenvPython -m pip install -r (Join-Path $RepoRoot "environment\requirements-reviewer-e2e-core.txt")
if ($LASTEXITCODE -ne 0) { throw "Core dependency installation failed" }

$CudaUsable = (& $VenvPython -c "import torch; print('1' if torch.cuda.is_available() else '0')" | Select-Object -Last 1).Trim()
$RuntimeDevice = $Device
if ($Device -eq "auto") {
    $RuntimeDevice = if ($CudaUsable -eq "1") { "cuda" } else { "cpu" }
}
if ($Device -eq "cuda" -and $CudaUsable -ne "1") {
    throw "CUDA environment was installed but torch.cuda.is_available() is False."
}

& $VenvPython -c "import torch, torchvision; print('torch       =', torch.__version__); print('torchvision =', torchvision.__version__); print('CUDA runtime=', torch.version.cuda); print('CUDA usable =', torch.cuda.is_available()); print('GPU         =', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE')"
if ($LASTEXITCODE -ne 0) { throw "PyTorch environment verification failed" }

Write-Host ""
Write-Host "Reviewer runtime device: $RuntimeDevice"
Write-Host "Public datasets are persistent at DataRoot. Existing verified files are reused; only missing data are downloaded."
Write-Host "All generated reviewer outputs are rebuilt under WorkRoot."
Write-Host ""

$RunArgs = @(
    (Join-Path $RepoRoot "RUN_REVIEWER_E2E.py"),
    "--work-root", $WorkRoot,
    "--data-root", $DataRoot,
    "--device", $RuntimeDevice,
    "--epochs", "$Epochs",
    "--witness-reps", "$WitnessReps"
)
if ($Matlab) {
    $RunArgs += @("--matlab", $Matlab)
}

& $VenvPython @RunArgs
if ($LASTEXITCODE -ne 0) {
    throw "CMDO E2E reviewer run failed with exit code $LASTEXITCODE"
}

$ReportPath = Join-Path $WorkRoot "CMDO_E2E_REVIEWER_REPORT.json"
if (-not (Test-Path $ReportPath)) {
    throw "Final reviewer report not found: $ReportPath"
}
$Report = Get-Content $ReportPath -Raw | ConvertFrom-Json

if ($Report.fresh_model_training -ne $true) { throw "Final report does not confirm fresh model training" }
if ([int]$Report.fresh_external_prediction_targets -ne 38) { throw "Final report does not contain 38 fresh prediction targets" }
if ([int]$Report.manuscript_figures_regenerated -ne 8) { throw "Final report does not confirm 8 regenerated manuscript figures" }
if ([int]$Report.final_png_count -ne 8 -or [int]$Report.final_pdf_count -ne 8) {
    throw "Final graphical inventory is not 8 PNG + 8 PDF"
}
if ($Report.git_worktree_clean_after_run -ne $true) { throw "Repository was not clean after the reviewer run" }

Write-Host ""
Write-Host "============================================================"
Write-Host " CMDO REVIEWER FROM-ZERO RUN COMPLETE"
Write-Host "============================================================"
Write-Host "Status      : $($Report.status)"
Write-Host "Fresh train : PASS"
Write-Host "Targets     : 38/38"
Write-Host "Figures     : 8 PNG + 8 PDF"
Write-Host "Git clean   : PASS"
Write-Host "Report      : $ReportPath"
Write-Host "Results ZIP : $($Report.results_package)"
Write-Host "SHA256 file : $($Report.results_package_sha256_sidecar)"
Write-Host "============================================================"
