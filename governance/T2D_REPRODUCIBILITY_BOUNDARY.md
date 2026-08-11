# T2-D reproducibility boundary

The original accepted historical T2-D v0.1 certificate passed all 11 frozen gates,
including target-cluster exact sign-flip G4 = `0.0364990234375`. A fresh raw-to-science
replay on the disclosed reference environment executed the same T2-D stage to
completion but passed `10/11`; G4 was `0.0587158203125`, and the resulting decision
was `DO_NOT_AUTHORISE_BLIND_VALIDATION_REVISE_OR_TERMINATE`.

The engineering audit then separated three issues:

1. a localized Stage11E near-zero-variance conditioning instability was confirmed and
   a pre-fit hardening candidate preserved source recoverability, but did not restore
   the original T2-D v0.1 authorisation;
2. a full rank-invariant T2-D development probe stabilized G4 but reproducibly failed
   the predeclared label-permutation G10 control and was rejected;
3. a rank-selection/original-estimation development probe passed the historical and
   conditioned worlds but failed the predeclared three-world freeze rule because the
   unconditioned fresh world passed only 8/11; it was rejected.

No frozen threshold was relaxed, the locked blind assets remained untouched, and
Stage 12 remained prohibited. Further T2-D method tuning against the already observed
development gates was closed.

The reviewer runner therefore treats a non-authorising fresh T2-D result as
`SCIENTIFIC_DIVERGENCE_BOUNDARY` (exit code `4`), preserves the successfully produced
scientific artifacts, and does not execute downstream stages as a fresh accepted
chain. Downstream historical implementation may instead be audited with the separate
`archival-continuation` profile, which is explicitly not fresh raw-to-science
reproduction.

Machine-readable definitions are in:

- `provenance/scientific_boundaries.json`
- `provenance/reference_fresh_replay_environment.json`
