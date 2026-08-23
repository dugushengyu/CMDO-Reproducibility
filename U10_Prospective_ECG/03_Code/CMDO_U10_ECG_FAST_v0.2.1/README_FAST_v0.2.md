# CMDO U10 FAST downloader v0.2

Use this package instead of v0.1 when downloading the PhysioNet Challenge 2020 U10 reserve.

## Why v0.2 is faster

v0.1 performed a `HEAD` request and a SHA256 calculation for every file before/after transfer.
With ~60,895 small files, request latency dominated bandwidth.

v0.2:
- uses persistent HTTP sessions;
- does not issue a separate HEAD request;
- resumes via `Range`;
- caches verified/downloaded file sizes in SQLite;
- skips cached files without network requests on future reruns;
- defers SHA256 hashing to a separate local-only `verify-local` phase.

## Scientific boundary is unchanged

PRESEAL:
- PTB-XL source: `.mat + .hea`
- Georgia target: `.mat only`
- CPSC 2018 target: `.mat only`

Target `.hea` files remain forbidden until `SEALS/U10_PREOUTCOME_SEAL.json` exists.

## Existing v0.1 files

Keep them. v0.2 will validate them once using a Range GET, add them to its SQLite cache, and then never probe them again on future reruns.

## Start

```powershell
$fast = "$HOME\CMDO-U10-FAST-v0.2"
$root = "$HOME\CMDO-U10-ECG"
Set-Location $fast

powershell -ExecutionPolicy Bypass -File ".\CMDO_U10_FAST.ps1" `
    -Phase preseal `
    -Root $root `
    -Workers 48
```

Try 48 workers first. If PhysioNet returns many 429/503 errors, reduce to 32. If the line is still underused and errors remain zero, 64 can be tested.

## Status

```powershell
powershell -ExecutionPolicy Bypass -File ".\CMDO_U10_FAST.ps1" `
    -Phase status `
    -Root $root
```

## After PRESEAL is fully complete

Do not unseal yet.

A later, local-only hash inventory can be created with:

```powershell
powershell -ExecutionPolicy Bypass -File ".\CMDO_U10_FAST.ps1" `
    -Phase verify-local `
    -Root $root
```

This uses no network and writes `manifests/U10_LOCAL_SHA256.jsonl`.
