# Numerical closure for the CMDO submission

This directory provides a small additive reproduction layer for numerical analyses that were added after the original frozen empirical stages. It closes the traceability path from the manuscript/Supplementary Information back to executable calculations without changing any frozen U6-U11 verdict, prespecified gate, figure source record, or reviewer-acceptance criterion.

The existing reviewer pathway remains unchanged:

```powershell
python RUN_REVIEWER.py all
```

The numerical-closure pathway is separate and optional:

```powershell
python numerical_closure/RUN_NUMERICAL_CLOSURE.py
```

A faster diagnostic run is:

```powershell
python numerical_closure/RUN_NUMERICAL_CLOSURE.py --quick
```

The scripts use NumPy, pandas and SciPy, which are already pinned in the repository's maintainer environment under `environment/requirements-reviewer.txt`.

## 1. PCC finite-grid certification

`reproduce_pcc.py` regenerates the finite-grid certification analysis underlying the tracked PCC source tables:

```text
source_data/pcc/PCC_frontier_classified.csv
source_data/pcc/PCC_scaling_summary_v12.csv
```

The executable specification is:

- desired fixed borrowing weight: `w0 = 0.05`;
- false-certification level: `delta = 0.05`;
- target certification power: `0.80`;
- target AUC grid: 0.55 to 0.95 in steps of 0.05;
- historical mismatch grid: -0.10 to +0.10 in steps of 0.025, with historical AUC clipped to the open unit interval and duplicate clipped states removed;
- protected future per-class AUC audit sizes: 16, 32, 64, 128, 256 and 512;
- certification-pair grid: 16, 32, 64, 128, 256, 512, 1,024 and 2,048 pairs;
- exact two-sided Clopper-Pearson intervals;
- the Birnbaum-Klose least-favourable continuous-score AUC variance envelope used by the submission renderer;
- the first tested certification budget reaching target power while retaining the declared false-certification guarantee.

The script reconstructs all 474 grid states, compares them numerically with the frozen table, reconstructs the scaling summary and verifies the reported zero-mismatch log-log slope of 1.00 over application audit sizes 32-512.

Optional regenerated CSVs can be written outside the repository:

```powershell
python numerical_closure/reproduce_pcc.py --write-dir C:\CMDO-NUMERICAL-CLOSURE
```

## 2. Exact U10 finite-cohort risk

`reproduce_u10_exact.py` evaluates the locked U10 shared-audit rule exactly for the frozen Georgia and CPSC 2018 binary correctness rosters.

For each cohort and audit budget, the number of correct predictions in a simple-random audit follows the exact hypergeometric distribution. The script applies the locked scalar rule

```text
V = max(D(1-D)/m, 1e-8)
w = min(0.35, V / (V + (D-H)^2))
```

and computes the exact direct, matched-fixed and adaptive risks without Monte Carlo approximation.

The required closure fingerprints are:

```text
adaptive risk > matched-fixed risk: 8/8 states
fixed-use benefit -> adaptive harm: 5/8 states
```

This is a post-completion exact check of the frozen U10 binary rosters and does not revise the prospective U10 verdict `MECHANISM_NOT_CONFIRMED`.

## 3. Tie-robust PCC audit

The original PCC-v1.4 tie-robust validation was executed in MATLAB before this numerical-closure directory was added. The exact FULL-run text summary is retained here as:

```text
PCC_V14_TIE_FULL_SUMMARY_20260907.txt
```

Its archived execution fingerprints include:

```text
random discrete states: 120000
continuous-score BK violations: 26205/120000 = 21.837500%
minimum trueV - tau-only tie-aware lower bound: 4.9183853433e-06
minimum trueV - sharper tie-aware lower bound: 2.33067211364e-11
tie-robust lower-bound audit: PASS
```

The preserved run metadata record a random discrete-distribution family with 2-8 ordered support points, independently generated class probability vectors from Dirichlet(1), audit sizes sampled from {16,32,64,128,256}, and seed 140401.

`reproduce_tie_audit.py` performs two checks:

1. it verifies the exact archived FULL-run fingerprints above; and
2. it independently implements the same mathematical discrete-distribution stress family in Python and verifies that the tie-aware lower envelopes remain valid while the unmodified continuous-score lower bound is violated in a substantial fraction of tied states.

The independent Python check is intentionally **not** described as a byte-identical replay of the historical MATLAB random stream. The original MATLAB generator was not part of the frozen `cmdo-submission-v2.1.3` repository, so asserting identical random draws would be stronger than the archived evidence supports. The exact historical result is retained as an execution fingerprint, while the Python implementation supplies an executable independent mathematical cross-check.

## Evidential authority

These scripts are reproduction/closure utilities. They do not:

- overwrite any frozen U6-U11 protocol or result;
- change the 185-state synthesis;
- add the deferred eICU reserve to that synthesis;
- change the locked U10 prospective verdict;
- convert retrospective PCC projections into prospective validation;
- change any manuscript figure source table; or
- alter `RUN_REVIEWER.py all`.

They only make the generation and verification path for already-reported post-completion numerical analyses explicit.
