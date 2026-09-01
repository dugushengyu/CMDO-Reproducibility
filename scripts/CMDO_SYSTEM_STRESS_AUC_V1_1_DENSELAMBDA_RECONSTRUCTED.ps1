param([string]$OutDir='')
$ErrorActionPreference='Stop'
Set-StrictMode -Version 2.0
$repo=Split-Path -Parent $PSScriptRoot
$py=Join-Path $PSScriptRoot 'CMDO_SYSTEM_STRESS_AUC_V1_1_DENSELAMBDA_RECONSTRUCTED.py'
if(-not(Test-Path -LiteralPath $py)){throw "Missing generator: $py"}
if(-not $OutDir){$OutDir=Join-Path $repo 'source_data\figure5_stress_reconstructed'}
$python=Get-Command py -ErrorAction SilentlyContinue
if($python){& $python.Source -3 $py --outdir $OutDir}
else{$python=Get-Command python -ErrorAction SilentlyContinue;if(-not $python){throw 'Python 3 not found on PATH.'};& $python.Source $py --outdir $OutDir}
if($LASTEXITCODE -ne 0){throw "Stress generator failed with exit code $LASTEXITCODE"}
$csv=Join-Path $OutDir 'CMDO_SystemStress_AUC_StateSummary_v1_1.csv'
if(-not(Test-Path -LiteralPath $csv)){throw "Expected CSV not created: $csv"}
Write-Host "Generated Figure-5 stress source: $csv"
