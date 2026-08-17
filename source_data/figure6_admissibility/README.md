# Final Figure 6 audit companions

`matlab/figures/main/Figure6.m` is a sealed single-file renderer and does not read these files at runtime. These text records retain the audit trail behind its embedded frozen values.

- `CMDO_Admissibility_State_MSE_Audit.csv`: the six exact columns used by Figure 6 for all 185 synthesis states (U6=80, U7=80, U8=12, U9A=9, U9B=4). The originating full 26-column table had SHA-256 `a0ad0c9f9feded26b9b32f732ae62d7639d5ff91be983cb54a04525b0efc6d03`; the Git-tracked six-column audit extract has SHA-256 `4ef09304a0dbb4110130b9543b05bd8a7d0f34f22dd0ecef1cb6ef758c6174c4`.
- `U9B_external_composability_decomposition.csv`: panel-c scalar/observed/Xi values.
- `U9B_shared_audit_coupling.csv`: panel-d shared-audit mechanism values.
- `U9B_strict_split_mechanistic_control.csv`: both strict-split orientations and the finite-sample trade-off.

The strict-split analysis is post-hoc mechanistic evidence and does not change the frozen U9B verdict.
