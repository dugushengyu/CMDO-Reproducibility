# CMDO U10 one-shot unseal + prospective evaluation v0.1.1 RESUMABLE

Prepared after the PREOUTCOME seal and before Georgia/CPSC target labels were unsealed.

PREOUTCOME seal SHA256:
`efccafc32dc7778986296f6f7314488f6d08c45bdff2efdcb7f0918d36aec949`

Locked evaluation-spec SHA256:
`25b8810080a595494552789aca632c67db4b6af16b7f404920e38d9aee45a449`

The runner verifies the seal, locks the evaluation spec, writes a one-shot marker before
target-label download, downloads Georgia/CPSC `.hea`, checks exact counts, then evaluates.

Run:

```powershell
$zip = "$HOME\Downloads\CMDO_U10_UNSEAL_EVAL_v0.1.zip"
$work = "$HOME\CMDO-U10-UNSEAL-EVAL-v0.1"
Set-Location $HOME
if (Test-Path -LiteralPath $work) { Remove-Item $work -Recurse -Force }
Expand-Archive -LiteralPath $zip -DestinationPath $work -Force
$pkg = Join-Path $work "CMDO_U10_UNSEAL_EVAL_v0.1"
Set-Location $pkg

powershell -ExecutionPolicy Bypass -File ".\CMDO_U10_UNSEAL_AND_EVALUATE.ps1" `
  -Root "$HOME\CMDO-U10-ECG" `
  -Workers 64
```


## Resume behavior

The one-shot marker is permanent evidence that unsealing began under the locked seal/spec.
If PhysioNet times out while target `.hea` files are downloading, the runner automatically
retries up to 30 times. A later rerun of the same v0.1.1 package is also allowed only when
the existing marker matches the exact frozen seal and evaluation-spec hashes.

This makes transport resumable without creating a second scientific unseal.
