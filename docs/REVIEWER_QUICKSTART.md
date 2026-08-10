# Reviewer quickstart

The fastest scientifically useful check is the `frozen` profile. The deepest check
is `full-claim`. They answer different questions and should not be described as the
same run.

## 1. Install

Use Python 3.11. MATLAB must be callable as `matlab` for U8 and publication figures;
the Statistics and Machine Learning Toolbox is required.

```bash
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
python -m pip install -r environment/requirements-replay.txt
```

For a CUDA machine, install the matching official PyTorch CUDA wheel before the
requirements file. Do not change the scientific seeds, budgets or replicate counts.

Python 3.11 compatibility note: the immutable Drive-era T-series sources retain their
original `isic-cli==12.5.2` bytes and hashes. Runtime-adapted copies substitute
`isic-cli==12.4.0`, the last release compatible with Python 3.11; this changes only
the acquisition client version, not scientific seeds, budgets or source commitments.

## 2. Integrity audit (no data download)

```bash
python RUN_REPRODUCTION.py audit
```

This verifies source imports, embedded-payload extraction, sealed U8/U9 packages,
the stage DAG, dataset registry, frozen-asset manifests and non-destructive path
adapters.

## 3. Minutes-scale engineering smoke test

```bash
python RUN_REPRODUCTION.py smoke --allow-network
```

This downloads the official UCI-296 clinical dataset, preprocesses an 8,000-row
deterministic sample, trains a logistic model, evaluates AUC and writes a ROC figure.
It is labelled `ENGINEERING_SMOKE_TEST_NOT_MANUSCRIPT_RESULT` and must not be cited
as a CMDO manuscript estimate.

## 4. Fast frozen-result reproduction

```bash
python RUN_REPRODUCTION.py frozen
```

This byte-verifies the seven U4C-U7 canonical archives and renders all current main
and extended figures. It does not retrain any model. In the portable ZIP, the
canonical archives are already present; in a normal Git clone, place them under
`data/canonical_records/` or set `CMDO_CANONICAL_RECORD_DIR`.

## 5. Full raw-data and training replay

First inspect the complete 55-node plan:

```bash
python RUN_REPRODUCTION.py full-claim --plan
```

Then run it:

```bash
python RUN_REPRODUCTION.py full-claim \
  --allow-network \
  --acknowledge-retrospective-replay
```

If a manual or account-gated asset is needed, copy
`config/reproduction.example.toml` to an untracked local file, fill only the paths
you are permitted to use, and add `--config /path/to/reproduction.toml`.

The full profile:

- creates a new isolated project-shaped work tree;
- preserves all imported source bytes and executes adapted copies only;
- downloads public datasets from declared official routes;
- reruns preprocessing, frozen representations, model fitting and target analysis;
- trains U2 CIFAR from a fresh work directory for 12 epochs;
- replays U3C/U4C/U5B/U6/U7 and U8 as disclosed retrospective reconstructions;
- compares structures and governance fields exactly, and retrained metrics under
  declared tolerances;
- renders figures from replay U4C-U7 canonical records;
- writes a resumable `run_state.json` and one log per stage.

Resume the same run after an interruption:

```bash
python RUN_REPRODUCTION.py full-claim \
  --run-id YOUR_EXISTING_RUN_ID \
  --allow-network \
  --acknowledge-retrospective-replay \
  --resume
```

Exit status `3` is an intentional prerequisite gate, such as
`BLOCKED_LICENSE_GATE`, `BLOCKED_RUNTIME` or `BLOCKED_GOVERNANCE_ACK`. It is not a
silent skip. Exit status `1` is a failed stage or integrity comparison.

## Governance boundary

`full-claim` is a retrospective replay of already disclosed outcomes. It cannot
create a new prospective validation claim. U9/eICU is excluded from every default
profile and is never automatically prepared or unsealed.
