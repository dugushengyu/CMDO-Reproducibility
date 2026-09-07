# Finite-sample safe reuse — exploratory theory module

Status: **exploratory / post-completion theory only**.

This module is intentionally isolated from the frozen CMDO submission record. It was started from `main` commit `12e6c0aca22fe3e1661bfed523182ae6439429b6` on branch `theory/finite-sample-safe-reuse-v0`. It does **not** modify U6–U11 frozen artifacts, verdicts, figure sources, or the submission tag.

## Research question

Can adaptive historical borrowing be given a genuine finite-sample no-harm condition relative to same-budget direct evaluation, rather than only a post-completion explanation of when adaptation failed?

The first target is deliberately narrow:

1. derive an exact finite-sample risk identity for a role-separated adaptive weight;
2. obtain a non-asymptotic sufficient no-harm cap;
3. show explicitly why the same cap does not protect a same-audit/coupled rule;
4. test the resulting geometry against the frozen U10 summaries without retuning U10;
5. decide whether an implementable, non-oracle certificate can be built. If not, stop rather than forcing the result into the paper.

## Candidate baseline result

Let `D` be an unbiased current estimator of target performance `theta`, with finite-sample variance `V`. Let `H` be a completed historical estimate with mismatch `B = H - theta`. Let `W` be an adaptive borrowing weight determined from a decision sample that is independent of `D`, with `0 <= W <= omega`.

For

`A = (1-W) D + W H`,

the exact finite-sample MSE is

`R(A) = V - 2 V E[W] + (V + B^2) E[W^2]`.

Hence, if `Lambda = B^2 / V`, a sufficient condition for `R(A) <= V` is

`omega <= 2 / (1 + Lambda)`.

More generally, no harm is equivalent to

`E[W^2] / E[W] <= 2 / (1 + Lambda)`

when `E[W] > 0` and the role-separation independence condition holds.

This is exact in finite samples and does not assume normality. It is **not yet claimed as the final novel theorem**: the current research task is to determine whether this can be strengthened into an implementable finite-sample certificate with a data-derived upper bound on `Lambda`, and whether the coupling correction yields a nontrivial general condition.

## Why U10 is useful here

The frozen U10 summaries already contain the ingredients needed for a strong falsification check:

- exact target accuracy and historical accuracy;
- direct finite-cohort risk scale;
- shared-adaptive risk;
- matched constant-mean-weight risk;
- permuted-weight and independent-fold diagnostics;
- measured coupling terms.

A key diagnostic question is whether the observed shared-adaptive failures occur even when the *mean* borrowing level lies below the oracle role-separated safe cap. If yes, that is evidence that controlling weight magnitude alone is insufficient and that dependence must appear explicitly in any useful finite-sample safety theorem.

## Files

- `THEOREM_DRAFT.md` — derivation, exact coupling correction, counterexample, and proof obligations.
- `safe_reuse_cap.m` — oracle finite-sample cap under role separation.
- `RUN_SAFE_REUSE_PROBE.m` — self-contained simulation/counterexample check.
- `ANALYZE_U10_SAFE_REUSE.m` — read-only diagnostic against frozen U10 summary files.
- `LITERATURE_SCOPE.md` — nearby results and novelty boundary.

## Stop rule

Do **not** merge this module into the submission branch merely because the algebra is correct. Continue only if at least one of the following survives review:

- a genuinely nontrivial finite-sample guarantee for adaptive reuse;
- an implementable high-probability certificate using an independently estimated mismatch bound;
- a sharp impossibility result showing that nontrivial no-harm is impossible under unrestricted same-audit coupling, together with a constructive route that restores safety.

If the result reduces only to the existing fixed-weight bias–variance geometry with an independence assumption, keep it as a research note and leave the current manuscript unchanged.
