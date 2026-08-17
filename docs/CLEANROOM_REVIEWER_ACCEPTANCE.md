# Clean-room reviewer acceptance

This is the maintainer-side final acceptance before a submission/release candidate is distributed. It deliberately tests the reviewer workflow from a fresh delivery rather than from the author's long-lived working tree.

## Standard maintainer command on Windows

From the canonical repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\RUN_CLEANROOM_REVIEWER.ps1
```

The wrapper first builds the final reviewer artifacts and then creates a new clean-room workspace under a deliberately short Windows path such as `C:\CMDO-CR-<timestamp>`. The fresh-clone runner invokes Git with `core.longpaths=true` on Windows and also records that setting in the clone. This avoids false checkout failures caused only by the repository's long immutable historical governance paths. A custom writable short path can be supplied with `-Workspace` when required.

The default acceptance is intentionally strict:

1. the source repository must be at the same commit as `origin/main` with no tracked changes;
2. `RUN_REVIEWER.py check` must pass before packaging;
3. all seven canonical archives must match the frozen size, SHA-256 and ZIP CRC records;
4. a deterministic `CMDO-Reviewer-Assets-v1.0.zip` is built;
5. a deterministic `CMDO-Reproducibility-Reviewer-Portable-v1.0.zip` is built and byte-verified;
6. a completely fresh Git clone is checked out at the exact source commit, using Windows long-path-safe Git handling when applicable;
7. a new Python 3.11 virtual environment is created and the pinned replay requirements are installed;
8. the fresh clone runs `RUN_REVIEWER.py check`;
9. the reviewer asset ZIP is installed and byte-verified in that fresh clone;
10. both deep replay plans are parsed without execution;
11. final Figure 5/6 are regenerated with MATLAB;
12. the public-data smoke path is executed with explicit network permission;
13. the frozen manuscript-figure route is executed;
14. the fresh clone must remain Git-clean after reviewer execution.

A successful run ends with:

```text
=== CMDO CLEANROOM REVIEWER ACCEPTANCE PASS ===
CMDO FINAL CLEAN-ROOM REVIEWER CANDIDATE: PASS
```

and writes `CMDO_CLEANROOM_REVIEWER_REPORT.json` plus step logs in the clean-room workspace.

## Submission artifacts

The build step writes the following under `dist/`:

- `CMDO-Reviewer-Assets-v1.0.zip` — the seven byte-frozen canonical manuscript archives used by the standard GitHub-clone reviewer route;
- `CMDO-Reproducibility-Reviewer-Portable-v1.0.zip` — an offline-friendly deterministic code/assets snapshot that excludes restricted raw data and deferred eICU data;
- `CMDO-Submission-Candidate-v1.0_MANIFEST.json` — the Git commit, artifact hashes and interpretation boundary;
- `CMDO-Submission-Candidate-v1.0_SHA256.txt` — SHA-256 identities for the final artifacts and sidecars.

The two ZIP delivery modes are complementary. A normal reviewer can clone the repository and install `CMDO-Reviewer-Assets-v1.0.zip`. The portable ZIP is a fallback for environments where a GitHub clone is inconvenient.

## Scope boundary

A clean-room PASS certifies the documented reviewer engineering path, public smoke test, exact canonical manuscript assets and frozen figure regeneration. It does not reinterpret the disclosed fresh T2-D scientific divergence, does not relax a frozen gate and does not claim a fresh U9/eICU raw-to-science replay. The deferred eICU branch remains excluded from the default reviewer profiles and from distributed reviewer artifacts.

## Reduced diagnostic runs

The clean-room runner supports reduced modes for debugging only:

```bash
python scripts/run_cleanroom_reviewer_test.py --selftest
python scripts/build_submission_candidate.py --plan
```

The PowerShell wrapper also accepts `-Workspace`, `-SkipNetwork`, `-SkipEnvironmentInstall`, `-SkipFrozen` and `-SkipMatlab`. A run using skips is diagnostic and should not be used as the final submission acceptance record.
