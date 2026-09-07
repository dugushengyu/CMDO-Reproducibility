# Manuscript integration design — v2 certifiability boundary

Status: design only. Do not edit the frozen manuscript until local MATLAB verification and one final priority audit are complete.

## Core decision

Do **not** add a fourth stage.

Keep the existing evidential order:

`IDENTIFY -> REUSE -> PRESERVE`.

Redefine the scientific content of PRESERVE from

> fixed-use value can be lost when reuse becomes adaptive

to

> adaptive reuse has a finite-sample certifiability boundary: same-audit magnitude control is insufficient, while honest protection against coupling consumes current-outcome information and can make fair full-budget safety statistically uncertifiable.

This is a deepening of PRESERVE, not an appended topic.

## Revised novelty hierarchy

### Novelty 1 — IDENTIFY

Outcome-free monitoring need not identify current performance; observationally equivalent deployment worlds can have different performance.

### Novelty 2 — REUSE

Once representative current outcomes restore estimability, completed historical performance becomes an efficiency resource whose value is governed by historical mismatch relative to current estimation uncertainty.

### Novelty 3 — PRESERVE / CERTIFIABILITY

A favorable fixed-use result does not imply adaptive safety. More strongly:

1. no positive borrowing-magnitude cap alone can guarantee no-harm under unrestricted same-audit adaptation, even when every fixed convex weight is beneficial;
2. independent current evidence can restore a finite-sample reuse certificate;
3. under fair same-total-budget comparison, the current information spent creating that independence imposes an exact feasibility boundary;
4. in the iid mean problem, historical mismatch must lie within one decision-audit standard error, and high-confidence certification of that region is intrinsically low-power in a Gaussian benchmark.

This turns the final stage from an empirical failure diagnosis into an impossibility/possibility theorem.

## Main-text compression rule

The main paper should contain only the minimum mathematics needed to make the conceptual jump.

Recommended main-text theorem content:

### Main result A — same-audit impossibility

State in prose plus one compact displayed line:

> For any positive cap on a same-audit adaptive borrowing weight, there exists a bounded problem in which all fixed weights under that cap improve MSE but the adaptive rule worsens it.

The explicit two-point construction and proof go to SI.

### Main result B — full-budget certifiability boundary

For the iid mean case, show only

`|H-theta| <= SD(D_decision)`

as the maximal historical mismatch compatible with role-separated MSE non-inferiority to the full-budget direct estimator.

Immediately explain the interpretation:

> the outcomes used to decide whether history is safe are themselves part of the current evidence that direct evaluation could have used.

The general quadratic, safe interval, Gaussian optimal certification test and 8.23% power ceiling go to SI / Extended Data.

## Results architecture

Existing U10 remains the empirical bridge:

1. matched fixed reuse is beneficial in all eight states;
2. shared adaptive reuse is worse than its matched fixed comparator in all eight and flips benefit to harm in five;
3. the new theorem explains why small weights do not rescue same-audit adaptation;
4. the role-separation theory explains why the earlier strict-split repair can reduce coupling yet lose efficiency.

The new theory therefore **explains both sides of the U10 result**:

- why shared adaptation can fail despite conservative borrowing;
- why simply splitting the audit is not a free repair.

No new dataset is required.

## Figure strategy

Do not add a sixth main figure.

Preferred option: revise the conceptual content of the existing PRESERVE figure/panel so it contains three visual states:

`fixed-use benefit -> same-audit adaptive loss -> certifiability boundary`.

The figure should emphasize one visual message:

> safety requires controlling dependence, but protection spends information.

A detailed phase diagram belongs in Extended Data/SI if needed.

## Abstract change if integration is approved

The current third-stage sentence should be replaced by a sentence with this logic:

> Even when fixed historical reuse reduces estimation risk, adaptive reuse can reverse that gain. We prove that no positive weight cap alone guarantees finite-sample safety under unrestricted same-audit adaptation, and that restoring a certificate by separating the borrowing decision from current evaluation imposes an information cost that can eliminate any full-budget-safe borrowing region.

The final sentence remains the evidential-order principle, now with a stronger endpoint:

> current performance must first be identifiable; historical evidence must then prove useful; and adaptive reuse must finally be certifiable under the finite current evidence available to support it.

Do not use `safe`, `fail-safe`, or `guaranteed` without the theorem assumptions immediately attached.

## Discussion change if integration is approved

The conceptual synthesis becomes three irreducible problems:

1. **missing relation** — outcome-free evidence may not identify performance;
2. **transport mismatch** — completed history may be biased for current deployment;
3. **certification cost** — using scarce current outcomes to decide how much history to reuse creates dependence, while removing that dependence spends information that direct evaluation could otherwise use.

The final message is no longer merely `adaptation can hurt`.

It becomes:

> Evidence reuse is constrained twice: by whether history is close enough to current truth and by whether the current evidence needed to establish that closeness can be separated from the estimator without erasing the gain.

## What should be deleted/reduced if this theory enters the paper

To avoid content stacking:

- reduce the current post-hoc coupling narrative to one mechanism example rather than a standalone novelty claim;
- move detailed permutation localization and some adaptation-frontier algebra deeper into SI;
- do not add another dataset or metric family;
- do not present the role-separated certificate as a new deployed algorithm unless a non-vacuous operational construction is later obtained.

The new theorem should **replace** some existing PRESERVE explanatory content, not sit after it.

## Integration threshold

Proceed to manuscript rewrite only after:

1. `VERIFY_THEORY_V2` passes locally in MATLAB;
2. the existing v1/v2 numerical probes reproduce locally;
3. one final specialist literature check finds no direct prior theorem matching the combined same-audit/full-budget certifiability result;
4. all wording keeps U10/new theory explicitly post-completion where appropriate.

If these pass, the scientific identity changes enough to justify one controlled manuscript rewrite.