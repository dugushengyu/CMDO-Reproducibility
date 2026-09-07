# Finite-sample certifiability of adaptive historical reuse — v2

Status: exploratory post-completion theory. This branch does not revise any frozen CMDO stage, result, figure source, or submission tag.

## 1. Setup

Let `theta` be the current target performance. Let a current direct estimator satisfy

`D = theta + e`,

with `E[e]=0` and `E[e^2]=V>0`. Let the completed historical performance value be fixed at

`H = theta + B`.

For a borrowing weight `W in [0,1]`, define

`A = (1-W)D + W H`.

Risk is squared-error risk unless stated otherwise.

The v2 objective is not to invent another borrowing rule. It is to characterize when adaptive historical reuse is **certifiable** against current-only evaluation and when such certification is impossible or information-limited.

---

## 2. Baseline fixed/role-separated identity

If `W` is independent of `D`, with `mu=E[W]`, `q=E[W^2]`, and `Lambda=B^2/V`, then exactly

`R(A)/V - 1 = -2 mu + (1+Lambda) q`.

For a fixed weight `w`,

`R(A_w)/V - 1 = -2w + (1+Lambda)w^2`.

Thus fixed reuse is MSE non-inferior to direct evaluation iff

`0 <= w <= 2/(1+Lambda)`.

This ordinary bias–variance geometry is background and is not claimed as the new result.

---

## 3. Theorem 1 — no positive magnitude-only safeguard under unrestricted same-audit adaptation

**Theorem 1 (magnitude-only safety is impossible).** For every `omega` with `0 < omega <= 1`, there exists a bounded scalar estimation problem with `theta,D,H in [0,1]` such that

1. `D` is unbiased for `theta`;
2. every fixed weight `w in [0,1]` is strictly MSE-better than direct evaluation for `w>0`;
3. a same-audit rule `W=W(D)` taking values only in `{0,omega}` is strictly MSE-worse than direct evaluation.

### Explicit construction

Take

- `theta = 0.5`;
- `D=0.6` with probability `0.8` and `D=0.1` with probability `0.2`;
- `H=0.65`.

Then `E[D]=0.5`,

`V = 0.8(0.1)^2 + 0.2(-0.4)^2 = 0.04`,

`B=0.15`, and `Lambda=B^2/V=0.5625`.

For any fixed `w in [0,1]`,

`R(A_w)-V = w(25w-32)/400`,

which is strictly negative for every `0<w<=1`.

Now define

`W=omega` if `D=0.6`, and `W=0` if `D=0.1`.

Then

`R(A)-V = omega(omega+4)/500 > 0`

for every `omega>0`.

Therefore **no positive pointwise cap on borrowing magnitude can be a universal no-harm device for unrestricted same-audit adaptation**, even in a bounded problem where every fixed convex combination with the same historical value is beneficial.

### Consequence

Any valid same-audit safety theory must control more than `0<=W<=omega`; it must restrict or bound the dependence between the borrowing decision and the current estimation error.

---

## 4. Exact dependence correction

Without independence,

`R(A)-V = -2V mu + (V+B^2)q + C_dep`,

where

`C_dep = -2 Cov(W,e^2) + Cov(W^2,e^2) + 2B Cov(W,e) - 2B Cov(W^2,e)`.

Define the role-separated safety margin

`M_safe = 2V mu - (V+B^2)q`.

Then exactly

`R(A)<=V  <=>  C_dep <= M_safe`.

This identity separates two objects that should not be conflated:

- **magnitude/heterogeneity geometry**, represented by `mu,q,B,V`;
- **same-audit coupling**, represented by `C_dep`.

Theorem 1 shows that the second can overturn the first even when the first is favorable for every fixed weight.

---

## 5. Theorem 2 — observable finite-sample certificate under honest role separation

Let `S` be a decision audit independent of the evaluation estimator `D_eval`. Suppose `C_alpha(S)` is a finite-sample confidence set with

`P_theta(theta in C_alpha(S)) >= 1-alpha`.

Let the evaluation estimator be unbiased with variance `V_eval(theta)>0`. Define

`Lambda_U(S) = sup_{t in C_alpha(S)} (H-t)^2 / V_eval(t)`.

Let `w(S)` be any measurable weight satisfying

`0 <= w(S) <= min{1, 2/(1+Lambda_U(S))}`.

Define

`A_S = (1-w(S)) D_eval + w(S) H`.

**Theorem 2.** Under the stated assumptions,

`P_S( E_theta[(A_S-theta)^2 | S] <= V_eval(theta) ) >= 1-alpha`.

### Proof

On the event `theta in C_alpha(S)`,

`(H-theta)^2/V_eval(theta) <= Lambda_U(S)`.

Conditional on `S`, the weight is fixed and independent of `D_eval`; hence

`E[(A_S-theta)^2|S]/V_eval(theta)-1`

`= -2w(S) + [1+Lambda(theta)] w(S)^2`

`<= -2w(S) + [1+Lambda_U(S)] w(S)^2 <= 0`.

The confidence event has probability at least `1-alpha`. QED.

This is a genuine finite-sample, non-oracle, high-probability conditional MSE certificate. It is relative to the evaluation-only direct estimator; fair comparison with a direct estimator using the full current-outcome budget is harder.

---

## 6. Theorem 3 — general same-total-budget certifiability boundary

Let `D_full` denote current-only direct evaluation using the full current-outcome budget and let

`V_full(theta) = rho V_eval(theta)`, `0<rho<=1`,

where `rho` is known and does not depend on `theta`. Define the information cost of role separation

`delta = 1-rho`.

On the confidence event, sufficient full-budget safety requires

`(1+Lambda_U)w^2 - 2w + delta <= 0`.

**Theorem 3.** A non-empty certified weight interval exists iff

`delta <= 1/(1+Lambda_U)`.

When feasible,

`w_minus <= w <= w_plus`,

with

`w_+/- = [1 +/- sqrt(1-(1+Lambda_U)delta)]/(1+Lambda_U)`.

Thus `Psi = 1/(1+Lambda_U)-delta` is a certifiability margin:

- `Psi>0`: a non-degenerate safe interval exists;
- `Psi=0`: one safe weight exists;
- `Psi<0`: no role-separated convex reuse weight can be certified against full-budget direct evaluation under the stated mismatch bound.

This is a feasibility boundary, not merely a tuning formula.

---

## 7. Theorem 4 — the one-decision-standard-error boundary

The preceding quadratic becomes especially transparent for an iid sample-mean problem.

Let the total current-outcome budget be

`M = m_s + m_e`,

where `m_s` observations form an independent decision audit and `m_e` observations form an independent evaluation audit. Suppose each current observation has mean `theta` and variance `sigma^2`.

Then

`V_s = sigma^2/m_s`,

`V_eval = sigma^2/m_e`,

`V_full = sigma^2/M`.

Consider the role-separated convex estimator

`A_w = (1-w)D_eval + wH`.

**Theorem 4 (one-standard-error feasibility boundary).** There exists at least one `w in [0,1]` such that

`R(A_w) <= V_full`

if and only if

`B^2 <= V_s = sigma^2/m_s`.

Equivalently,

`|H-theta| <= SD(D_s)`.

Moreover, the weight that maximizes the admissible historical-mismatch radius is

`w = delta = m_s/M`.

At this weight,

`R(A_delta)-V_full = [m_s/(M^2)] * [m_s B^2 - sigma^2]`.

### Proof

For general `w`, full-budget non-inferiority is equivalent to

`B^2 <= V_eval [2w-w^2-delta]/w^2`,

where `delta=m_s/M`.

The right-hand side is maximized at `w=delta`. Substitution gives

`max_w B_max^2(w) = sigma^2/m_s = V_s`.

At `w=delta`, direct expansion gives the displayed risk difference. QED.

### Interpretation

This result exposes the information price of honest role separation. To beat the current-only estimator that uses all `M` outcomes, the historical performance value must be known to lie within **one decision-audit standard error** of current truth. No choice of convex borrowing weight can enlarge that role-separated full-budget-safe mismatch region.

The special weight `w=m_s/M` has an intuitive interpretation: the historical value replaces exactly the fraction of the full direct estimator that would otherwise have been supplied by the decision audit.

---

## 8. Corollary — Bernoulli accuracy safe set

For binary correctness, `sigma^2=theta(1-theta)`. Theorem 4 becomes

`m_s(H-theta)^2 <= theta(1-theta)`.

The set of current accuracies satisfying this inequality is the interval

`theta_- <= theta <= theta_+`,

where

`theta_+/- = [2m_s H + 1 +/- sqrt(1+4m_s H(1-H))] / [2(m_s+1)]`.

This interval is the exact iid-Bernoulli oracle safe region for full-budget role-separated replacement at the maximally tolerant weight `w=m_s/M`.

For the frozen U10 parameter values used only as a post-completion iid benchmark:

- Georgia: `theta=0.955110765643`, `H=0.973208152049`, so `sigma^2/B^2 = 130.9074`;
- CPSC 2018: `theta=0.942125927003`, `H=0.973208152049`, so `sigma^2/B^2 = 56.4376`.

Thus, even with oracle knowledge of current truth, an honest decision audit larger than about 131 observations for Georgia or 56 observations for CPSC would make full-budget role-separated convex reuse infeasible in this iid benchmark. This is diagnostic only; it is not a prospective claim about the finite-cohort U10 sampling design.

---

## 9. Theorem 5 — high-confidence pilot certification has a low-power ceiling in the Gaussian benchmark

Theorem 4 says that an independent pilot must establish

`|H-theta| <= sigma/sqrt(m_s)`.

How difficult is that certification problem even when historical and current performance are exactly equal?

Assume the decision-audit mean is exactly Gaussian with known variance:

`D_s ~ Normal(theta, sigma^2/m_s)`.

Define

`Z = (D_s-H)/(sigma/sqrt(m_s))`,

so `Z ~ Normal(mu,1)` with

`mu=(theta-H)/(sigma/sqrt(m_s))`.

Full-budget role-separated reuse is feasible only for `|mu|<=1`.

Consider any certification rule `phi(Z) in [0,1]` satisfying the finite-sample false-certification constraint

`sup_{|mu|>=1} E_mu[phi(Z)] <= alpha`.

**Theorem 5 (Gaussian certification-power ceiling).** The maximum possible certification probability at perfect historical agreement (`mu=0`) is

`pi_star(alpha) = 2 Phi(c_alpha)-1`,

where `c_alpha>0` is the unique solution of

`Phi(c_alpha-1) - Phi(-c_alpha-1) = alpha`.

The optimal rule certifies for `|Z|<=c_alpha` (with boundary randomization if exact equality is required).

At `alpha=0.05`,

`c_0.05 = 0.10331848...`,

`pi_star(0.05) = 0.08228979...`.

Therefore, even under **perfect historical agreement**, no level-5% certification rule in this Gaussian benchmark can certify the one-standard-error safe region more than about **8.23%** of the time.

### Proof

Any valid rule has size at most `alpha` at both boundary distributions `N(-1,1)` and `N(1,1)`, hence size at most `alpha` under their equal mixture.

Against this least-favorable boundary mixture, the likelihood ratio for `N(0,1)` is proportional to

`1/cosh(z)`,

which is strictly decreasing in `|z|`. By the Neyman–Pearson lemma, the most powerful level-`alpha` rule is therefore a central rule `|Z|<=c_alpha`. Its probability is equal at the two boundary nulls, and for a centered interval decreases as `|mu|` moves beyond 1, so it controls the entire unsafe set. Its power at `mu=0` is `2Phi(c_alpha)-1`. QED.

### Interpretation

The failure of the naive 95% confidence-set split is not merely a poor implementation detail. In the canonical Gaussian benchmark, the oracle full-budget-safe mismatch region is only one pilot standard error wide; a high-confidence attempt to certify such a narrow region is intrinsically low-power.

---

## 10. Certifiability trilemma within the convex-reuse class

Theorems 1–5 imply a finite-sample tension:

1. **Reuse all current outcomes adaptively with the same audit:** no positive magnitude cap alone can guarantee no-harm; dependence must be controlled.
2. **Create honest role separation:** finite-sample certification becomes possible relative to the evaluation-only direct estimator.
3. **Demand fairness against full-budget current-only evaluation:** the cost of creating independence shrinks the safe mismatch region to at most one decision-audit standard error; in a Gaussian benchmark, certifying even perfect agreement at 95% confidence has at most 8.23% power.

Hence, within this scalar convex historical-reuse class, one cannot obtain useful finite-sample guarantees by simply combining a conservative borrowing cap with a naive current-audit split. A practical escape requires **additional structure**: a dependence bound, a model that narrows historical mismatch, external/current evidence independent of the direct audit, or a more efficient dependence-controlled construction.

This is the strongest current result of the branch.

---

## 11. Relation to frozen U10

The frozen U10 summaries already exhibit the phenomenon motivating Theorem 1:

- 8/8 observed mean shared weights lie below the oracle role-separated cap;
- 8/8 matched constant-mean-weight comparators are beneficial;
- 5/8 shared-adaptive states are harmful relative to full direct evaluation.

The simple 95% Clopper–Pearson decision/evaluation certificate probed in v1 had zero trigger probability in all eight U10-like states over the tested split grid. Theorem 5 explains why that negative result is not surprising: the full-budget-safe region created by honest splitting is statistically difficult to certify at high confidence even in a favorable Gaussian benchmark.

No U10 result is reclassified by this analysis. These are post-completion theory diagnostics only.

---

## 12. Novelty boundary

The branch must **not** claim any of the following as new:

- fixed-weight bias–variance trade-offs;
- adaptive historical borrowing;
- Stein/shrinkage dominance under structured models;
- finite-sample failures of estimated adaptive weights in general;
- bias caps or exact type-I control for external-control borrowing;
- sample splitting as a generic device for avoiding data reuse.

The candidate distinct contribution, if the literature audit continues to hold, is the combined **certifiability boundary for post-deployment performance reuse**:

- a bounded same-audit impossibility result showing that even universal fixed-weight benefit does not imply safety of any positive data-dependent cap;
- a non-oracle finite-sample role-separated MSE certificate;
- an exact same-total-budget feasibility boundary;
- the one-decision-standard-error limit on the historical mismatch that role separation can tolerate;
- and a high-confidence certification-power ceiling showing why a naive split can be formally valid yet operationally nearly useless.

This should be framed as an impossibility/possibility theory of **certifiable reuse**, not as the first finite-sample theory of adaptive borrowing.

---

## 13. Manuscript trigger after v2

The branch has crossed the earlier Route-B threshold in a mathematically meaningful way: the negative result is no longer just `the split was expensive in U10`; it is an analytic certifiability boundary plus a Gaussian power ceiling.

However, the frozen manuscript should still not be rewritten automatically. Before narrative integration:

1. finish a targeted prior-art audit around finite-sample dominance of biased/unbiased estimator averaging, adaptive misspecification, dynamic historical borrowing, and equivalence/certification testing;
2. locally run the deterministic MATLAB verification scripts;
3. decide whether the paper can present the certifiability trilemma without creating a fourth conceptual stage or excessive notation;
4. keep all U10 uses explicitly post-completion.

If those checks pass, the final PRESERVE novelty can be upgraded from `adaptive reuse can destroy fixed-use value` to `adaptive evidence reuse has a finite-sample certifiability boundary`.