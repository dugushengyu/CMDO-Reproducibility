param(
    [string]$Root = "$HOME\CMDO-U10-ECG",
    [switch]$DeepDataHash
)

$ErrorActionPreference = "Stop"

function Get-Sha256Lower([string]$Path) {
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Assert-Hash([string]$Label, [string]$Path, [string]$Expected) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Missing $Label : $Path"
    }
    $actual = Get-Sha256Lower $Path
    if ($actual -ne $Expected.ToLowerInvariant()) {
        throw "$Label hash mismatch.`nExpected: $Expected`nActual:   $actual`nPath: $Path"
    }
    Write-Host "[PASS] $Label"
    return $actual
}


function Get-RelativePathCompat([string]$BasePath, [string]$TargetPath) {
    # Windows PowerShell 5.1 / .NET Framework does not provide
    # [System.IO.Path]::GetRelativePath(), so use System.Uri instead.
    $baseFull = [System.IO.Path]::GetFullPath($BasePath)
    if (-not $baseFull.EndsWith([string][System.IO.Path]::DirectorySeparatorChar)) {
        $baseFull = $baseFull + [System.IO.Path]::DirectorySeparatorChar
    }
    $targetFull = [System.IO.Path]::GetFullPath($TargetPath)

    $baseUri = New-Object System.Uri($baseFull)
    $targetUri = New-Object System.Uri($targetFull)
    $rel = $baseUri.MakeRelativeUri($targetUri).ToString()
    $rel = [System.Uri]::UnescapeDataString($rel)
    return $rel.Replace("/", [string][System.IO.Path]::DirectorySeparatorChar)
}

$rootPath = (Resolve-Path -LiteralPath $Root).Path
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$freezeRoot = Join-Path $rootPath ("FINAL_FREEZE_U10_" + $timestamp)
$capDir = Join-Path $freezeRoot "EVIDENCE_CAPSULE"
New-Item -ItemType Directory -Force -Path $capDir | Out-Null

Write-Host "===================================================================="
Write-Host " CMDO U10 FINAL SCIENTIFIC FREEZE v0.1.1 PS5.1"
Write-Host " Root: $rootPath"
Write-Host "===================================================================="

# ------------------------------------------------------------------
# 1. Verify immutable chain already established in the experiment.
# ------------------------------------------------------------------
$seal = Join-Path $rootPath "SEALS\U10_PREOUTCOME_SEAL.json"
$spec = Join-Path $rootPath "UNSEAL\U10_LOCKED_EVALUATION_SPEC_v0.1.json"
$prosCsv = Join-Path $rootPath "UNSEAL\RESULTS_v0.1\U10_TARGET_BUDGET_SUMMARY.csv"
$prosJson = Join-Path $rootPath "UNSEAL\RESULTS_v0.1\U10_PRIMARY_RESULT.json"
$post1Csv = Join-Path $rootPath "UNSEAL\POSTHOC_FAILURE_DIAGNOSTICS_v0.1\U10_POSTHOC_PHASE_DIAGNOSTICS.csv"
$post1Json = Join-Path $rootPath "UNSEAL\POSTHOC_FAILURE_DIAGNOSTICS_v0.1\U10_POSTHOC_FAILURE_DIAGNOSTICS.json"
$post2Csv = Join-Path $rootPath "UNSEAL\POSTHOC_DEPENDENCE_DECOMPOSITION_v0.1\U10_DEPENDENCE_DECOMPOSITION.csv"
$post2Json = Join-Path $rootPath "UNSEAL\POSTHOC_DEPENDENCE_DECOMPOSITION_v0.1\U10_DEPENDENCE_DECOMPOSITION.json"

$known = [ordered]@{
    preoutcome_seal = @{
        path = $seal
        expected = "efccafc32dc7778986296f6f7314488f6d08c45bdff2efdcb7f0918d36aec949"
        status = "PROSPECTIVE_PREOUTCOME"
    }
    locked_evaluation_spec = @{
        path = $spec
        expected = "25b8810080a595494552789aca632c67db4b6af16b7f404920e38d9aee45a449"
        status = "LOCKED_BEFORE_TARGET_UNSEAL"
    }
    prospective_summary_csv = @{
        path = $prosCsv
        expected = "685be9c1a86b4ace5c41d1ff4564fc2fedd65a8f15e9555fe6b3886a6d3c4df9"
        status = "PROSPECTIVE_RESULT"
    }
    prospective_primary_json = @{
        path = $prosJson
        expected = "dd2624ba443c69ef2dd276f40eefdff8dadb97612e9838c77b019a4e15c9b090"
        status = "PROSPECTIVE_RESULT"
    }
    posthoc_failure_csv = @{
        path = $post1Csv
        expected = "cae428a478cca74ca28e73cd986edba10ebdfff4c8bb89de82d2c696e1802afb"
        status = "POSTHOC_EXPLORATORY"
    }
    posthoc_failure_json = @{
        path = $post1Json
        expected = "3597fea4f9a0546705488a70003f91ca168d38cef92ef53928f0b94b27040f12"
        status = "POSTHOC_EXPLORATORY"
    }
    posthoc_dependence_csv = @{
        path = $post2Csv
        expected = "580a0480391ea40cad021fc0264350f6eba357d24a219a670687163159470bcc"
        status = "POSTHOC_EXPLORATORY"
    }
    posthoc_dependence_json = @{
        path = $post2Json
        expected = "95d9f1cf9cd20c493af94fce9d94bb7fff8e27ce601ee58e8af0fec767f54947"
        status = "POSTHOC_EXPLORATORY"
    }
}

$verified = [ordered]@{}
foreach ($name in $known.Keys) {
    $k = $known[$name]
    $actual = Assert-Hash $name $k.path $k.expected
    $verified[$name] = [ordered]@{
        relative_path = Get-RelativePathCompat $rootPath $k.path
        sha256 = $actual
        scientific_status = $k.status
    }
}

# ------------------------------------------------------------------
# 2. Verify artifacts referenced INSIDE the preoutcome seal.
# ------------------------------------------------------------------
$sealObj = Get-Content -LiteralPath $seal -Raw | ConvertFrom-Json

$modelPath = Join-Path $rootPath "PRESEAL\SOURCE_MODEL_ptb-xl_AF.joblib"
$splitPath = Join-Path $rootPath "PRESEAL\SOURCE_SPLIT_ptb-xl.csv"
Assert-Hash "source_model_from_seal" $modelPath $sealObj.source_development.model_sha256 | Out-Null
Assert-Hash "source_split_from_seal" $splitPath $sealObj.source_development.source_split_sha256 | Out-Null

foreach ($ta in $sealObj.target_artifacts) {
    $ds = [string]$ta.dataset
    $score = Join-Path $rootPath ("PRESEAL\TARGET_SCORES_" + $ds + ".csv")
    $roster = Join-Path $rootPath ("PRESEAL\ROSTER_" + $ds + ".csv")
    $feat = Join-Path $rootPath ("PRESEAL\FEATURES_" + $ds + ".npz")
    Assert-Hash "$ds target_scores_from_seal" $score $ta.score_sha256 | Out-Null
    Assert-Hash "$ds roster_from_seal" $roster $ta.roster_sha256 | Out-Null
    Assert-Hash "$ds features_from_seal" $feat $ta.feature_sha256 | Out-Null
}

# ------------------------------------------------------------------
# 3. Record target/data state.
# ------------------------------------------------------------------
$dataState = [ordered]@{}
foreach ($ds in @("ptb-xl","georgia","cpsc_2018")) {
    $d = Join-Path $rootPath ("data\" + $ds)
    $dataState[$ds] = [ordered]@{
        mat_count = (Get-ChildItem -LiteralPath $d -Recurse -File -Filter *.mat | Measure-Object).Count
        hea_count = (Get-ChildItem -LiteralPath $d -Recurse -File -Filter *.hea | Measure-Object).Count
        part_count = (Get-ChildItem -LiteralPath $d -Recurse -File -Filter *.part -ErrorAction SilentlyContinue | Measure-Object).Count
    }
}

if ($dataState["ptb-xl"].mat_count -ne 21837 -or $dataState["ptb-xl"].hea_count -ne 21837) {
    throw "PTB-XL data counts changed."
}
if ($dataState["georgia"].mat_count -ne 10344 -or $dataState["georgia"].hea_count -ne 10344) {
    throw "Georgia data counts changed after unseal."
}
if ($dataState["cpsc_2018"].mat_count -ne 6877 -or $dataState["cpsc_2018"].hea_count -ne 6877) {
    throw "CPSC data counts changed after unseal."
}
Write-Host "[PASS] Raw-data counts match final U10 state."

# ------------------------------------------------------------------
# 4. Copy scientific evidence. Raw public data are NOT duplicated.
# ------------------------------------------------------------------
$copyMap = @(
    @{src=(Join-Path $rootPath "SEALS"); dst=(Join-Path $capDir "SEALS")},
    @{src=(Join-Path $rootPath "PRESEAL"); dst=(Join-Path $capDir "PRESEAL")},
    @{src=(Join-Path $rootPath "UNSEAL"); dst=(Join-Path $capDir "UNSEAL")}
)
foreach ($m in $copyMap) {
    if (Test-Path -LiteralPath $m.src) {
        Copy-Item -LiteralPath $m.src -Destination $m.dst -Recurse -Force
    }
}

# Copy locally used code packages if they still exist.
$codeDir = Join-Path $capDir "CODE_PACKAGES"
New-Item -ItemType Directory -Force -Path $codeDir | Out-Null
$codeCandidates = @(
    "$HOME\CMDO-U10-FAST-v0.2.1\CMDO_U10_ECG_FAST_v0.2.1",
    "$HOME\CMDO-U10-PRESEAL-v0.3.2\CMDO_U10_PRESEAL_PIPELINE_v0.3.2_LABELFIX_QC",
    "$HOME\CMDO-U10-UNSEAL-EVAL-v0.1.1\CMDO_U10_UNSEAL_EVAL_v0.1.1_RESUMABLE",
    "$HOME\CMDO-U10-POSTHOC-v0.1\CMDO_U10_POSTHOC_FAILURE_DIAGNOSTICS_v0.1",
    "$HOME\CMDO-U10-DEPENDENCE-v0.1\CMDO_U10_DEPENDENCE_DECOMPOSITION_v0.1"
)
$copiedCode = @()
foreach ($c in $codeCandidates) {
    if (Test-Path -LiteralPath $c) {
        $leaf = Split-Path -Leaf $c
        $dest = Join-Path $codeDir $leaf
        Copy-Item -LiteralPath $c -Destination $dest -Recurse -Force
        $copiedCode += $leaf
    }
}

# ------------------------------------------------------------------
# 5. Optional deep SHA256 manifest for all public raw-data files.
# ------------------------------------------------------------------
$rawManifestRel = $null
if ($DeepDataHash) {
    Write-Host "[deep] Hashing every raw-data file. This can take a while..."
    $rawRows = New-Object System.Collections.Generic.List[object]
    $files = Get-ChildItem -LiteralPath (Join-Path $rootPath "data") -Recurse -File | Sort-Object FullName
    $i = 0
    foreach ($f in $files) {
        $i++
        if (($i % 1000) -eq 0) {
            Write-Host ("[deep] {0}/{1}" -f $i, $files.Count)
        }
        $rawRows.Add([pscustomobject]@{
            relative_path = Get-RelativePathCompat $rootPath $f.FullName
            size_bytes = $f.Length
            sha256 = (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        })
    }
    $rawManifest = Join-Path $capDir "U10_RAW_DATA_SHA256_MANIFEST.csv"
    $rawRows | Export-Csv -LiteralPath $rawManifest -NoTypeInformation -Encoding UTF8
    $rawManifestRel = "U10_RAW_DATA_SHA256_MANIFEST.csv"
    Write-Host "[PASS] Deep raw-data SHA256 manifest complete."
}

# ------------------------------------------------------------------
# 6. Create chronology / evidence ledger.
# ------------------------------------------------------------------
$chronology = @"
CMDO U10 FINAL SCIENTIFIC FREEZE
================================

Scientific chronology:
1. PREOUTCOME stage:
   - PTB-XL source headers/labels available.
   - Georgia and CPSC target headers absent.
   - Source model, threshold, historical H, target waveform rosters and target scores frozen.
   - PREOUTCOME seal SHA256:
     efccafc32dc7778986296f6f7314488f6d08c45bdff2efdcb7f0918d36aec949

2. BEFORE TARGET UNSEAL:
   - Locked evaluation specification SHA256:
     25b8810080a595494552789aca632c67db4b6af16b7f404920e38d9aee45a449
   - One-shot unseal marker written before target headers were downloaded.

3. PROSPECTIVE RESULT:
   - Primary verdict: MECHANISM_NOT_CONFIRMED.
   - This result is immutable and must not be replaced by post-hoc analyses.
   - Prospective CSV SHA256:
     685be9c1a86b4ace5c41d1ff4564fc2fedd65a8f15e9555fe6b3886a6d3c4df9
   - Prospective JSON SHA256:
     dd2624ba443c69ef2dd276f40eefdff8dadb97612e9838c77b019a4e15c9b090

4. POST-HOC EXPLORATORY ANALYSES:
   - Variance/phase diagnostics.
   - Dependence/adaptation decomposition.
   - These analyses may motivate theory but do not retroactively redefine the prospective gate.

Final raw-data state:
- PTB-XL: 21837 .mat, 21837 .hea
- Georgia: 10344 .mat, 10344 .hea
- CPSC 2018: 6877 .mat, 6877 .hea

Public data resource:
PhysioNet/Computing in Cardiology Challenge 2020, version 1.0.2.

Freeze rule:
No U10 artifact inside this evidence capsule should be edited in place.
Any future analysis must be written to a new versioned POSTHOC or THEORY directory
and must cite this freeze capsule / ledger.
"@
$chronPath = Join-Path $capDir "U10_SCIENTIFIC_CHRONOLOGY.txt"
Set-Content -LiteralPath $chronPath -Value $chronology -Encoding UTF8

$ledger = [ordered]@{
    schema = "CMDO_U10_FINAL_SCIENTIFIC_FREEZE_v0.1.1_PS51"
    created_utc = (Get-Date).ToUniversalTime().ToString("o")
    source_root = $rootPath
    public_data_resource = "PhysioNet/Computing in Cardiology Challenge 2020 v1.0.2"
    scientific_status = [ordered]@{
        prospective_primary_verdict = "MECHANISM_NOT_CONFIRMED"
        prospective_result_is_immutable = $true
        posthoc_results_are_exploratory = $true
    }
    verified_artifacts = $verified
    raw_data_counts = $dataState
    copied_code_packages = $copiedCode
    raw_data_sha256_manifest = $rawManifestRel
    freeze_policy = "Do not edit frozen artifacts in place; create new versioned post-hoc/theory outputs only."
}
$ledgerPath = Join-Path $capDir "U10_FINAL_EVIDENCE_LEDGER.json"
$ledger | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $ledgerPath -Encoding UTF8

# ------------------------------------------------------------------
# 7. Hash everything in the evidence capsule.
# ------------------------------------------------------------------
Write-Host "[manifest] Hashing evidence capsule..."
$rows = New-Object System.Collections.Generic.List[object]
$files = Get-ChildItem -LiteralPath $capDir -Recurse -File |
    Where-Object { $_.Name -ne "U10_EVIDENCE_CAPSULE_SHA256_MANIFEST.csv" } |
    Sort-Object FullName

foreach ($f in $files) {
    $rows.Add([pscustomobject]@{
        relative_path = Get-RelativePathCompat $capDir $f.FullName
        size_bytes = $f.Length
        sha256 = (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
    })
}
$manifest = Join-Path $capDir "U10_EVIDENCE_CAPSULE_SHA256_MANIFEST.csv"
$rows | Export-Csv -LiteralPath $manifest -NoTypeInformation -Encoding UTF8
$manifestHash = Get-Sha256Lower $manifest

# ------------------------------------------------------------------
# 8. Zip evidence capsule and hash archive.
# ------------------------------------------------------------------
$zipPath = Join-Path $freezeRoot "CMDO_U10_FINAL_EVIDENCE_CAPSULE_v0.1.1.zip"
Compress-Archive -LiteralPath $capDir -DestinationPath $zipPath -CompressionLevel Optimal -Force
$zipHash = Get-Sha256Lower $zipPath

$freezeSummary = [ordered]@{
    schema = "CMDO_U10_FINAL_FREEZE_SUMMARY_v0.1.1_PS51"
    created_utc = (Get-Date).ToUniversalTime().ToString("o")
    evidence_capsule_manifest_sha256 = $manifestHash
    evidence_capsule_zip = [IO.Path]::GetFileName($zipPath)
    evidence_capsule_zip_sha256 = $zipHash
    deep_raw_data_hashing = [bool]$DeepDataHash
    prospective_primary_verdict = "MECHANISM_NOT_CONFIRMED"
}
$summaryPath = Join-Path $freezeRoot "U10_FINAL_FREEZE_SUMMARY.json"
$freezeSummary | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $summaryPath -Encoding UTF8

# Mark copied capsule files read-only; original scientific root is untouched.
Get-ChildItem -LiteralPath $capDir -Recurse -File | ForEach-Object {
    $_.IsReadOnly = $true
}

Write-Host "===================================================================="
Write-Host " U10 FINAL FREEZE COMPLETE"
Write-Host " Freeze directory : $freezeRoot"
Write-Host " Capsule ZIP      : $zipPath"
Write-Host " Capsule ZIP SHA  : $zipHash"
Write-Host " Manifest SHA     : $manifestHash"
Write-Host " Prospective verdict remains: MECHANISM_NOT_CONFIRMED"
Write-Host "===================================================================="
