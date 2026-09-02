# CMDO reproducibility

This repository contains the frozen reproducibility record for the final CMDO manuscript.

## Final scientific architecture

The final manuscript is organized as:

**IDENTIFY -> REUSE -> PRESERVE**

with:

- Figure 1 — conceptual evidential order and system information flow
- Figure 2 — IDENTIFY: performance non-identifiability and outcome restoration
- Figure 3 — REUSE: evidence admissibility across frozen deployment states
- Figure 4 — PRESERVE: adaptive composability and the adaptation frontier
- Figure 5 — system advantage: budget-dependent robustness–efficiency operating region
- Extended Data Figure 1 — developmental falsification of a universal outcome-free route
- Extended Data Figure 2 — role-separation and coupling-pathway diagnostics

## Reviewer entry points

### Strongest portable reviewer audit

From a fresh clone, run:

```matlab
RUN_REVIEWER_END_TO_END('Strict',true,'RunStressReplay',true)
```

This verifies all tracked frozen reviewer inputs by SHA-256, runs the deterministic reconstructed synthetic stress replay, regenerates Figure 1-5 plus Extended Data Figure 1-2, and performs path/output/Git-clean checks.

Detailed scope and environment requirements are documented in:

```text
docs/REVIEWER_END_TO_END.md
provenance/reviewer_reexecution_contract_v1.json
```

### Final figures only

```matlab
RUN_SUBMISSION_FIGURES('Batch',true,'Strict',true)
```

By default, reviewer outputs are written under the operating-system temporary directory rather than into tracked repository paths.

## Final P0 reproducibility freeze

The final submission freeze adds explicit checks for the manuscript-state changes made after the previous submission tags: the data-driven Figure 4 adaptation frontier, the 185-state admissibility synthesis, and the five-block post-completion Figure 5 Monte Carlo stability diagnostic.

Before creating a new submission tag:

1. Generate the final-scope SHA-256 manifest once:

```powershell
python scripts/build_submission_final_manifest.py
```

2. Commit `provenance/submission_final_manifest_v1.csv`.
3. From a clean checkout of that exact commit, run:

```matlab
RUN_P0_FINAL_FREEZE('Strict',true,'RunStressReplay',true)
```

4. Create the submission tag only if the final gate reports `FINAL P0 FREEZE : true` and the worktree remains clean.

`VERIFY_P0_SUBMISSION_INPUTS.m` checks the final scientific-source fingerprints. The final gate also verifies the final SHA-256 manifest and invokes the full reviewer evidence-to-figure audit. The exact commit that passes this gate—not an earlier tag—is the commit that should be cited by the manuscript and Supplementary Information.

The five-block Figure 5 replay is explicitly a post-completion Monte Carlo stability diagnostic. Its tracked summary is under:

```text
source_data/figure5_submission/diagnostics/
```

It does not replace the frozen authoritative Figure 5 state summary.

## Recorded clean-room validation

A fresh GitHub clone was validated on Windows (PCWIN64) with MATLAB R2024b Update 5 and Python 3.11. The run verified all 12 tracked reviewer inputs by SHA-256, regenerated the deterministic synthetic stress replay, rendered all seven final figure targets, used zero external repository/data paths during rendering, and finished Git-clean.

Machine-readable record:

```text
provenance/reviewer_end_to_end_validation_windows_r2024b_20260901.json
```

This record predates the final P0 freeze and therefore remains evidence for the earlier reviewer pathway rather than a substitute for the new `RUN_P0_FINAL_FREEZE` acceptance run.

The repository also includes Windows and macOS/Linux fresh-clone launchers under `reviewer_portability/`. Cross-platform launchers are provided by design; the recorded empirical acceptance environment above is Windows R2024b.

## What 'end-to-end' means here

A generic reviewer computer can reproduce the complete **reviewer evidence-to-figure pathway** from a fresh GitHub clone: byte-verify the frozen derived evidence package, regenerate the fully synthetic diagnostic stress replay, and render the complete final figure set without any author-machine path.

It is **not** claimed that every historical prospective stage can be re-run from raw patient-level data on an arbitrary computer. Several stages are sealed and some underlying clinical datasets require controlled access. For those stages, the scientifically correct reviewer action is to verify and consume the tracked frozen derived records rather than silently replace a sealed prospective analysis with a new post-completion rerun.

The machine-readable stage-by-stage policy is:

```text
provenance/reviewer_reexecution_contract_v1.json
```

## Final source manifests

The earlier reviewer-facing frozen-input manifest is:

```text
provenance/submission_github_native_v4_manifest.csv
```

The final P0 freeze uses the broader manifest:

```text
provenance/submission_final_manifest_v1.csv
```

The latter is generated only after all final-scope source and renderer edits are complete, then committed before the clean-checkout acceptance run.

The central stage inventory through U11 is:

```text
provenance/stage_registry.json
```

## Figure 1 frozen asset

Figure 1 is rendered from the tracked frozen asset:

```text
source_data/figure1_assets/Figure1_assets_selected_v1.mat
```

SHA-256:

```text
30490a2586a9394fad868159ccd1f0248b0d9afc17d9bc970456c425c63925e7
```

## Figure 4 source

The reviewer-facing Figure 4 renderer reads the tracked source:

```text
source_data/figure4_submission/CMDO_Figure4_PRESERVE_Source_v1.csv
```

The corresponding provenance file records the definitions and aggregate fingerprints used by the adaptation-frontier panel. The renderer no longer embeds the earlier 7-of-8 winner-classification logic.

## Figure 5 source and replay separation

The authoritative manuscript Figure 5 reads only:

```text
source_data/figure5_submission/CMDO_SystemStress_AUC_StateSummary_v1_1.csv
```

The reconstructed executable stress test is kept separately under:

```text
scripts/stress_replay/
```

It is a deterministic diagnostic reconstruction of the lost stress-test program and must never overwrite the frozen manuscript Figure-5 source.

The five-block Monte Carlo stability diagnostic is regenerated separately by:

```powershell
python scripts/stress_replay/run_figure5_mc_stability.py --outdir <OUTPUT_DIRECTORY>
```

## Restricted and sealed data

No raw restricted PhysioNet/eICU patient-level records are redistributed. The repository instead tracks the frozen derived records required for the final reviewer-facing figure pathway. Authorized stage-specific reruns remain separate from the default reviewer command.

## Scientific interpretation boundaries

- U11 is a protocol-locked constructive information-closure witness, not an estimate of the real clinical performance of Georgia or CPSC 2018.
- U10 did not confirm shared-audit coupling as a general mechanism across both external ECG cohorts.
- Post-completion permutation and role-separation analyses are diagnostics and do not overwrite the locked U10 prospective verdict.
- The five-block Figure 5 Monte Carlo replay characterizes finite-replicate stability and does not replace or retune the authoritative frozen stress-test summary.
- U0-U5 are retained as developmental lineage and are not promoted into the final confirmatory chain.

## Repository policy

- Frozen protocols and locked prospective verdicts must not be overwritten.
- New post-completion analyses must remain explicitly labelled as such.
- Generated outputs, local caches and raw patient data remain outside Git unless explicitly tracked by policy.
- Final submission tagging should occur only after a fresh-clone P0 acceptance run passes on the exact commit to be tagged.
