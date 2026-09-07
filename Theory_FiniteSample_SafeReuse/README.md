# Finite-sample safe reuse — exploratory theory module

Status: **exploratory / post-completion theory only**.

This module is intentionally isolated from the frozen CMDO submission record. It was started from `main` commit `12e6c0aca22fe3e1661bfed523182ae6439429b6` on branch `theory/finite-sample-safe-reuse-v0`. It does **not** modify U6–U11 frozen artifacts, verdicts, figure sources, or the submission tag.

## Research question

Can adaptive historical borrowing be given a genuine finite-sample no-harm / certifiability theory relative to current-only performance evaluation, rather than only a post-completion explanation of when adaptation failed?

## Current v1 result

The first pass has moved beyond the original safe-cap idea.

1. **Magnitude-only impossibility.** A general bounded theorem proves that for every nontrivial borrowing cap below one, every fixed weight under that cap can be MSE-safe while a same-audit adaptive rule under the same cap is harmful.
2. **Role-separated finite-sample certificate.** An independent current decision audit can produce a confidence-set-based worst-case mismatch coordinate `Lambda_U`, yielding a high-probability conditional MSE certificate without target-truth leakage.
3. **Same-total-budget certifiability boundary.** If independence is purchased by withholding current outcomes from evaluation, a certified interval exists only when the historical-information gain can pay the resulting split tax.
4. **Falsification of the naive construction.** Exact binomial enumeration at U10-like parameter settings indicates that a simple 95% Clopper-Pearson decision/evaluation split is operationally vacuous against full-budget direct evaluation across the tested split fractions. The theorem remains valid, but the naive certificate is not a useful final method.

The emerging question is therefore a **safety–information boundary**: dependence must be controlled, but controlling it can itself consume the finite audit information needed to make historical reuse worthwhile.

## Key files

- `THEORY_RESULT_V1.md` — formal v1 theorem package: same-audit magnitude-only impossibility, observable role-separated certificate, and full-budget certifiability boundary.
- `THEOREM_DRAFT.md` — earlier derivation, coupling correction, counterexample, and proof obligations.
- `VERIFY_THEORY_V1.m` — deterministic MATLAB checks of the v1 constructions and quadratic boundary.
- `safe_reuse_cap.m` — oracle role-separated cap helper.
- `RUN_SAFE_REUSE_PROBE.m` — self-contained simulation/counterexample check.
- `ANALYZE_U10_SAFE_REUSE.m` — read-only oracle diagnostic against frozen U10 summaries.
- `ANALYZE_U10_SPLIT_TAX.m` — oracle half-split full-budget feasibility diagnostic.
- `PROBE_U10_NONORACLE_TRIGGER.m` — exact iid-binomial Clopper-Pearson trigger-probability probe at U10-like parameter settings.
- `RESULTS_V1_2026-09-07.md` — current mathematical/empirical research verdict and next-step decision.
- `NOVELTY_AUDIT_2026-09-07.md` — adjacent literature and protected novelty boundary.
- `MANUSCRIPT_TRIGGER.md` — explicit threshold for whether this branch is allowed to reopen the manuscript narrative.

## What is not claimed

- The ordinary fixed-weight bias–variance geometry is not new.
- Adaptive shrinkage itself is not new.
- Finite-sample failures of estimated reuse weights are not new in general.
- The simple honest-split certificate is not yet an operational method.
- No frozen CMDO stage is retrospectively upgraded by this branch.

## Next research target

Do **not** add more datasets. Continue only along one of two routes:

### Route A: dependence-controlled reuse without a fixed split tax

Seek a cross-fitted, orthogonalized, predictable, or otherwise dependence-controlled construction that uses most/all current outcomes while admitting a finite-sample risk bound.

### Route B: sharpen the impossibility boundary

If Route A fails, prove that no method in a broad same-audit class can simultaneously provide nontrivial adaptive borrowing, uniform finite-sample MSE no-harm, and full-budget current-data efficiency without additional structural assumptions.

## Stop / manuscript rule

Do **not** merge this module into the submission branch merely because the algebra is correct. The current manuscript remains the baseline.

Reopen the manuscript narrative only if the branch produces either:

- a non-oracle, non-vacuous full-budget certificate (or a dependence-controlled construction that materially reduces the split cost); or
- a sufficiently general impossibility/possibility theorem that changes PRESERVE from a failure diagnosis into a fundamental certifiability boundary.

Otherwise keep the work as a theory note / Supplementary possibility boundary and leave the current manuscript unchanged.