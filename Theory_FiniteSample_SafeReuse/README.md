# Finite-sample safe reuse — exploratory theory module

Status: **v2 theory result / post-completion branch only**.

This module is intentionally isolated from the frozen CMDO submission record. It was started from `main` commit `12e6c0aca22fe3e1661bfed523182ae6439429b6` on branch `theory/finite-sample-safe-reuse-v0`. It does **not** modify U6–U11 frozen artifacts, verdicts, figure sources, or the submission tag.

## Research question

Can adaptive reuse of completed historical performance evidence be certified in finite samples against current-only post-deployment evaluation, rather than merely diagnosed after adaptation fails?

## Current v2 result

The branch now supports a finite-sample **certifiability trilemma**.

1. **Same-audit magnitude-only impossibility.** For every positive borrowing cap `0<omega<=1`, there is a bounded problem in which every fixed convex weight toward history is MSE-beneficial, yet a same-audit adaptive rule using only `0` and `omega` is MSE-harmful.
2. **Role-separated finite-sample certificate.** An independent current decision audit can generate an observable worst-case mismatch bound and a `1-alpha` conditional MSE no-harm certificate relative to an evaluation-only direct estimator.
3. **Same-total-budget boundary.** If outcomes are withheld to create independence, a full-budget-safe convex reuse weight exists only when historical mismatch is small enough to pay that information cost.
4. **One-decision-standard-error limit.** In the iid sample-mean problem, no role-separated convex weight can beat full-budget direct evaluation unless `|H-theta| <= SD(D_decision)`. The maximally tolerant weight is `m_s/M`.
5. **Gaussian certification-power ceiling.** In the exact Gaussian benchmark, any level-5% certification rule for the full-budget-safe region can certify even perfect historical agreement with probability at most about **8.23%**.

The simple 95% Clopper–Pearson split construction was also falsified as an operational method in the U10-like parameter probe: it had zero trigger probability across the tested states/splits. The theorem remains valid; the naive method is too information-expensive.

## Key files

- `THEORY_RESULT_V2.md` — current formal theorem package and proofs.
- `VERIFY_THEORY_V2.m` — deterministic Base-MATLAB checks of the v2 constructions and numerical constants.
- `RESULTS_V2_2026-09-07.md` — current scientific verdict.
- `NOVELTY_AUDIT_V2_2026-09-07.md` — targeted adjacent-literature audit and protected novelty boundary.
- `THEORY_RESULT_V1.md` / `THEOREM_DRAFT.md` — earlier derivation record.
- `PROBE_U10_NONORACLE_TRIGGER.m` — exact iid-binomial probe of the naive 95% split certificate.
- `ANALYZE_U10_SAFE_REUSE.m` — read-only oracle diagnostic against frozen U10 summaries.
- `ANALYZE_U10_SPLIT_TAX.m` — earlier oracle split-tax diagnostic.
- `RUN_SAFE_REUSE_PROBE.m` / `safe_reuse_cap.m` — baseline checks/helpers.
- `MANUSCRIPT_TRIGGER.md` — rule governing whether this branch is allowed to reopen the manuscript narrative.

## What is not claimed

- fixed-weight bias–variance trade-offs are not new;
- adaptive historical borrowing is not new;
- finite-sample adaptive-weight failures are not new in general;
- sample splitting is not new;
- bias caps and exact Type-I control for external borrowing are not new;
- the branch does not establish a universal impossibility for every conceivable data-fusion estimator;
- no frozen CMDO stage is retrospectively upgraded.

## Current research interpretation

The original constructive goal — a simple high-confidence, same-total-budget safe borrowing rule — did **not** survive the first realistic probe. That negative result exposed a stronger theoretical object:

> same-audit adaptation needs dependence control, but current outcomes spent creating that control are removed from the fair direct comparator; in the iid mean problem this restricts full-budget-safe historical mismatch to one decision-audit standard error, making conventional high-confidence certification intrinsically difficult.

This is potentially identity-changing for the existing PRESERVE stage because it turns `adaptive reuse can lose value` into an impossibility/possibility boundary for **certifiable reuse**.

## Local verification

Run in MATLAB from this directory:

```matlab
VERIFY_THEORY_V2
RUN_SAFE_REUSE_PROBE
ANALYZE_U10_SAFE_REUSE
ANALYZE_U10_SPLIT_TAX
PROBE_U10_NONORACLE_TRIGGER
```

`VERIFY_THEORY_V2` is deterministic and Base-MATLAB only. The repository records the scripts, but this environment does not contain a MATLAB runtime, so manuscript numerical claims should wait for the user's local MATLAB pass.

## Stop / manuscript rule

Do not merge this branch merely because the mathematics is correct.

The branch is now strong enough to justify a manuscript **integration design**, but not an automatic rewrite. Integration is warranted only if the v2 trilemma can replace/strengthen PRESERVE without creating a fourth conceptual stage or bloating notation.

If integrated, the protected novelty should be framed narrowly as a finite-sample **certifiability boundary for adaptive reuse of completed historical performance evidence**, not as the first theory of adaptive borrowing.