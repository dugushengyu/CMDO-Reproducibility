# Reviewer quickstart

CMDO separates **engineering reproducibility**, **fresh raw-to-science replay**, and
**archival historical-parent continuation**. These modes answer different questions
and must not be conflated.

## 1. Install

Use Python 3.11. MATLAB must be callable as `matlab` for U8 and publication figures;
the Statistics and Machine Learning Toolbox is required.

```bash
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
python -m pip install -c environment/replay-constraints.txt -r environment/requirements-replay.txt
```

For CUDA, install the matching official PyTorch wheel first. The runner also exports
`PIP_CONSTRAINT=environment/replay-constraints.txt` so legacy notebook `pip install`
commands cannot silently upgrade the numerical stack during replay. Immutable
Drive-era source bytes remain unchanged. Runtime copies adapt `isic-cli==12.5.2` to
`12.4.0`, the last Python-3.11-compatible release.


## 2. One-command engineering acceptance

For an ordinary Git clone (large Portable-only assets absent):

```bash
python scripts/final_reviewer_acceptance.py --skip-runtime
```

For the reviewer Portable bundle, require the seven canonical archives as well:

```bash
python scripts/final_reviewer_acceptance.py --skip-runtime --require-canonical
```

On the intended Python 3.11/MATLAB workstation, omit `--skip-runtime`; a supplied
`--project-root` additionally verifies the six historical receipt identities and
reports any sealed T2-D scientific boundary without turning it into an engineering
failure.

## 3. Static integrity audit

```bash
python RUN_REPRODUCTION.py audit
```

This performs code/provenance/DAG/adapter checks without downloading scientific data.

## 4. Fast frozen-result reproduction

```bash
python RUN_REPRODUCTION.py frozen
```

This byte-verifies the seven canonical archives and regenerates current figures. It
does not retrain models.

## 5. Fresh raw-to-science replay

Use the **reviewer portable bundle**, not a bare Git clone, because large
byte-verified historical bootstrap inputs are intentionally Git-ignored. On Windows,
use short roots such as `C:\Users\<you>\P` and `C:\Users\<you>\R`.

Before the run, place the six exact historical Stage11C official receipt files under
`<project-root>/00_Data_Acquisition/Stage11C_Manual_Official_Receipts/`. Their names,
sizes, and SHA-256 values are declared in `provenance/historical_receipts.json`.
These are **historical prerequisites**, not fresh provider downloads.

Inspect the plan:

```bash
python RUN_REPRODUCTION.py full-claim --plan
```

Run:

```bash
python RUN_REPRODUCTION.py full-claim \
  --run-id CMDO-FRESH-FULL \
  --output-root /short/path/R \
  --project-root /short/path/P \
  --allow-network \
  --acknowledge-retrospective-replay
```

Windows PowerShell example:

```powershell
python .\RUN_REPRODUCTION.py full-claim `
  --run-id CMDO-FRESH-FULL `
  --output-root "$HOME\R" `
  --project-root "$HOME\P" `
  --allow-network `
  --acknowledge-retrospective-replay
```

The declared plan has 55 nodes, but a scientifically valid fresh replay may stop
earlier. The reference current-runtime replay executes T2-D successfully but does
not reproduce its historical 11/11 authorisation gate. The runner therefore seals
`SCIENTIFIC_DIVERGENCE_BOUNDARY` at T2-D and returns exit status **4**. This is a
scientific non-reproduction boundary, not an engineering crash; downstream stages
are not represented as part of a fresh accepted chain.

Resume only interrupted engineering work with the same run ID and `--resume`.
A sealed scientific boundary cannot be bypassed by resume.

## 6. Archival historical-parent continuation

This profile is deliberately separate. It starts from byte-verified **accepted
historical T2-D/T2-E parents** and audits downstream historical implementation. It is
**not** a fresh raw-to-science reproduction and must use a project root separate from
the fresh replay tree.

```powershell
python .\RUN_REPRODUCTION.py archival-continuation `
  --run-id CMDO-ARCHIVAL `
  --output-root "$HOME\R" `
  --project-root "$HOME\A" `
  --allow-network `
  --acknowledge-retrospective-replay
```

The archival classification is written to
`ARCHIVAL_CONTINUATION_CLASSIFICATION.json` and the run ledger. U9/eICU is excluded.

## Exit codes

- `0` — selected profile completed.
- `1` — engineering/integrity/stage execution failure.
- `3` — explicit prerequisite block (runtime, network, license/receipt, path budget,
  or governance acknowledgement).
- `4` — `SCIENTIFIC_DIVERGENCE_BOUNDARY`; a scientific stage executed, but the frozen
  authorisation boundary was not reproduced. This is not converted into a pass.

## Governance boundary

`full-claim` is a retrospective replay of already disclosed outcomes and cannot
create a new prospective claim. U9/eICU is excluded from all default reviewer
profiles. No gate threshold is relaxed to force reproduction. The detailed T2-D
boundary is machine-readable in `provenance/scientific_boundaries.json`.
