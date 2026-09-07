# Finite-sample certifiable reuse — exploratory theory module

Status: **theory package complete enough for local verification and manuscript-integration review**.

This module is intentionally isolated from the frozen CMDO submission record. It was started from `main` commit `12e6c0aca22fe3e1661bfed523182ae6439429b6` on branch `theory/finite-sample-safe-reuse-v0`. It does **not** modify U6–U11 frozen artifacts, verdicts, figure sources, or the submission tag.

## Research question

Can adaptive reuse of completed historical performance evidence be certified in finite samples against current-only post-deployment evaluation, rather than merely diagnosed after adaptation fails?

## Current result: a certifiability trilemma

The branch now supports a finite-sample impossibility/possibility package.

1. **Same-audit magnitude-only limitation.** For every positive borrowing cap `0<omega<=1`, there is a bounded problem in which every fixed convex weight toward history is MSE-beneficial, yet a same-audit adaptive rule using only `0` and `omega` is MSE-harmful.
2. **Role-separated finite-sample certificate.** An independent current decision audit can generate an observable worst-case mismatch bound and a `1-alpha` conditional MSE no-harm certificate relative to an evaluation-only direct estimator.
3. **Same-total-budget boundary.** If outcomes are withheld to create independence, a full-budget-safe convex reuse weight exists only when historical mismatch is small enough to pay that information cost.
4. **One-decision-standard-error limit.** In the iid sample-mean problem, no role-separated convex weight can beat full-budget direct evaluation unless `|H-theta| <= SD(D_decision)`. The maximally tolerant weight is `m_s/M`.
5. **Cross-fit closure.** Ordinary symmetric two-fold cross-fitting does not automatically remove full-budget dependence. Its exact risk retains `a=E[We]`; a bounded construction has individually role-separated fold estimators but a 29% aggregate MSE increase over full-data direct evaluation.
6. **Calibration consequence.** Classical equivalence-testing logic applied to the one-standard-error region shows why high-confidence certification can be intrinsically weak. In the exact Gaussian benchmark, a level-5% optimal central certification rule has at most about 8.23% certification probability at perfect historical agreement. This value is an explanatory consequence, not a standalone novelty claim.

The simple 95% Clopper–Pearson split construction was also falsified as an operational method in the U10-like parameter probe: it had zero trigger probability across the tested states/splits. The theorem remains valid; the naive method is too information-expensive.

## Key files

- `THEORY_RESULT_V2.md` — formal theorem package and proofs through the one-standard-error boundary and Gaussian calibration consequence.
- `CROSSFIT_CLOSURE.md` — exact symmetric two-fold cross-fit risk identity and bounded counterexample.
- `VERIFY_THEORY_V2.m` — deterministic Base-MATLAB checks of the v2 constructions and numerical constants.
- `VERIFY_CROSSFIT_CLOSURE.m` — deterministic Base-MATLAB verification of the cross-fit identity/counterexample.
- `RESULTS_V2_2026-09-07.md` — scientific verdict after the main theorem pass.
- `FINAL_PRIORITY_AUDIT_2026-09-07.md` — final targeted novelty boundary after older shrinkage/model-averaging and equivalence-testing checks.
- `NOVELTY_AUDIT_V2_2026-09-07.md` — detailed adjacent-literature audit.
- `MANUSCRIPT_INTEGRATION_V2.md` — design for strengthening PRESERVE without adding a fourth stage.
- `MANUSCRIPT_TRIGGER.md` — frozen rule governing whether this branch is allowed to reopen the manuscript narrative.
- `PROBE_U10_NONORACLE_TRIGGER.m` — exact iid-binomial probe of the naive 95% split certificate.
- `ANALYZE_U10_SAFE_REUSE.m` — read-only oracle diagnostic against frozen U10 summaries.
- `ANALYZE_U10_SPLIT_TAX.m` — oracle split-tax diagnostic.
- `THEORY_RESULT_V1.md`, `THEOREM_DRAFT.md`, `INITIAL_FINDINGS.md` — derivation history.

## What is not claimed

- fixed-weight bias–variance trade-offs are not new;
- adaptive historical borrowing is not new;
- finite-sample adaptive-weight failures are not new in general;
- sample splitting and cross-fitting are not new;
- equivalence testing / most-powerful central equivalence tests are not new;
- bias caps and exact Type-I control for external borrowing are not new;
- the branch does not establish a universal impossibility for every conceivable data-fusion estimator;
- no frozen CMDO stage is retrospectively upgraded.

## Protected novelty after targeted prior-art audit

The defensible candidate novelty is the **combined finite-sample certifiability boundary for completed historical performance evidence in post-deployment evaluation**:

> borrowing magnitude alone does not protect unrestricted same-audit adaptation; independent current evidence can restore a conditional risk certificate, but creating that independence consumes current-outcome information that direct evaluation could otherwise use. Under an iid mean model this limits full-budget-safe historical mismatch to one decision-audit standard error, while ordinary symmetric fold-swapping does not automatically remove the aggregate dependence.

The priority claim belongs to this combined evidential/certifiability architecture, not to the individual shrinkage algebra, sample-splitting device, or equivalence-test consequence.

## Local verification

Run in MATLAB from this directory:

```matlab
VERIFY_THEORY_V2
VERIFY_CROSSFIT_CLOSURE
RUN_SAFE_REUSE_PROBE
ANALYZE_U10_SAFE_REUSE
ANALYZE_U10_SPLIT_TAX
PROBE_U10_NONORACLE_TRIGGER
```

The first two scripts are deterministic and Base-MATLAB only. The repository records the scripts, but this environment does not contain a MATLAB runtime, so manuscript numerical claims should wait for the user's local MATLAB pass.

## Manuscript rule

Do not merge this branch merely because the mathematics is correct.

The theory has crossed the scientific threshold for a controlled **PRESERVE** rewrite, provided the local MATLAB checks pass. It should deepen the existing third stage, not create a fourth stage and not add another dataset.

If integrated, existing mechanism/permutation detail should be reduced or moved deeper into SI so the new theory **replaces** explanatory material rather than stacking on top of it.