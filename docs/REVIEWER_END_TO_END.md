# Reviewer end-to-end reproducibility pathway

## What a fresh clone can do

From a fresh clone of the frozen submission branch, a reviewer can run one MATLAB command:

```matlab
RUN_REVIEWER_END_TO_END('Strict',true,'RunStressReplay',true)
```

The command performs six checks/actions:

1. Cross-platform MATLAB/toolbox preflight and author-specific-path scan.
2. SHA-256 verification of all tracked frozen submission inputs listed in `provenance/submission_github_native_v4_manifest.csv`.
3. Verification of the explicit re-execution scope in `provenance/reviewer_reexecution_contract_v1.json`.
4. Deterministic reconstruction of the fully synthetic dense-Lambda AUC stress test into a temporary directory.
5. Regeneration of Figure 1-5 and Extended Data Figure 1-2 from the authoritative tracked frozen records.
6. Final output and Git-clean audit.

Outputs are written under the operating system temporary directory by default, so a successful run does not modify tracked repository files.

## Required environment

The final figure pathway is MATLAB-based. The strongest end-to-end audit additionally uses Python for the synthetic stress replay.

Recommended reviewer environment:

- Windows, macOS, or Linux.
- MATLAB R2024a or later.
- Statistics and Machine Learning Toolbox (functions used by the final analysis/figures include `tiedrank` and `perfcurve`).
- Python 3.10 or later for the optional stress replay.
- Python packages listed in `scripts/stress_replay/requirements_stress.txt` (`numpy`, `pandas`, `scipy`).
- Git is recommended for the final clean-worktree check but is not required to execute the figures from a downloaded archive.

To install the Python replay dependencies when network access is available:

```bash
python -m pip install -r scripts/stress_replay/requirements_stress.txt
```

The figure-rendering phase itself performs no network access.

## Important scientific boundary

`RUN_REVIEWER_END_TO_END` is deliberately not described as a raw-patient-data rerun of every historical stage.

Several CMDO stages are prospective/sealed, and some underlying clinical data are access-restricted. In particular, eICU patient-level data cannot be redistributed through a public GitHub repository. Re-running such stages on an arbitrary computer would either violate the sealed analysis role or require credentials that a generic reviewer machine cannot possess.

For those stages the reproducible evidentiary object is the tracked, hash-verified frozen derived record used by the manuscript. This is stronger and more honest than silently replacing a sealed prospective analysis with a new post-completion rerun.

The precise policy for each stage is machine-readable in:

```text
provenance/reviewer_reexecution_contract_v1.json
```

## Figure 5: authoritative source versus diagnostic replay

The manuscript Figure 5 is rendered only from the authoritative tracked frozen CSV:

```text
source_data/figure5_submission/CMDO_SystemStress_AUC_StateSummary_v1_1.csv
```

Its locked manuscript fingerprint is checked before rendering, including the critical tested Lambda values and the shared-Lambda<=1 CMDO-versus-U-stat summary.

The executable script:

```text
scripts/stress_replay/CMDO_SYSTEM_STRESS_AUC_V1_1_DENSELAMBDA_RECONSTRUCTED.py
```

is a deterministic reconstruction of the lost stress-test program. It generates synthetic data from scratch and provides an independent diagnostic replay, but it is **not** claimed to be byte-identical to the lost 2026-08-31 program and it never overwrites the manuscript Figure-5 source.

## Minimal figure-only route

If a reviewer only wants to regenerate the final figures from the frozen evidence package:

```matlab
RUN_SUBMISSION_FIGURES('Batch',true,'Strict',true)
```

## Expected successful end-to-end summary

A successful strongest-portability run ends with a report similar to:

```text
Frozen tracked inputs verified : 12/12
Diagnostic stress replay       : PASS
Authoritative final figures    : true
External repository dependencies: 0
External data paths             : 0
Network during figure rendering : 0
Git clean                        : true
PORTABLE REVIEWER AUDIT          : true
```

The exact platform-dependent local clone path is irrelevant: a GitHub repository must exist somewhere on the reviewer's filesystem after cloning. The portability criterion is that no file outside the clone is required.

## Stronger testing recommendation before submission

The author should execute the command from a second fresh clone and, if possible, on a second operating-system installation or a clean virtual machine. This tests environment portability in addition to path independence. Passing on one Windows installation proves fresh-clone isolation; it does not logically prove compatibility with every possible MATLAB/Python version or every operating system.
