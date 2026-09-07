# Results v2 — cross-fitting does not remove the safety–information tension

Date: 2026-09-07

## New theorem

The natural two-fold reciprocal cross-fit construction has now been analyzed exactly.

Each fold chooses a borrowing weight from its own current outcomes and applies that weight to the opposite fold; the two role-swapped estimates are then averaged so that all audited outcomes re-enter the final estimator.

Although each weight is independent of the direct estimate to which it is locally applied, the aggregate risk contains a residual dependence term through `c=E[W e]`.

A bounded counterexample proves that for every `0<omega<2/3` there exists a problem in which:

- every fixed historical-reuse weight `w<=omega` is MSE non-inferior to the full two-fold direct estimator;
- the reciprocal cross-fitted adaptive estimator is nevertheless strictly worse than full direct.

The implemented CMDO maximum borrowing cap 0.35 lies inside this theorem's range; this is a theoretical relevance statement only, not a retrospective claim about the frozen observer.

## Consequence

The branch now has a three-part boundary:

1. **same audit:** uses all information, but magnitude control cannot prevent harmful coupling;
2. **one-way honest split:** restores a finite-sample certificate, but pays an information/split tax;
3. **reciprocal cross-fit:** recovers both folds, but ordinary role swapping reintroduces aggregate dependence and therefore does not restore a universal magnitude-only guarantee.

This makes the research target more precise. A useful constructive theorem now requires more than ordinary cross-fitting: it needs an orthogonal/dependence-controlled construction or a selective certificate whose validity explicitly accounts for reuse of the decision data.

## Scientific interpretation

The important emerging object is no longer a 'safe cap'. It is a **safety–information tension**:

> removing adaptive dependence consumes current information, while naively reusing that information can recreate the dependence that safety required removing.

If this tension can be turned into a general impossibility/possibility boundary with an observable non-vacuous certificate, it would change the PRESERVE layer of the manuscript. If not, it remains an exploratory theory note.

## Files

- `THEORY_RESULT_V2_CROSSFIT.md`
- `VERIFY_CROSSFIT_V2.m`

No manuscript files or frozen U10 records were modified.