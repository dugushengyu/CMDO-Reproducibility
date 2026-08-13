# CMDO U9 Pre-outcome Engineering Amendment A1

**Status:** PRE-OUTCOME, DATA-INDEPENDENT ENGINEERING CORRECTION
**Base U9 version:** v1.0
**Base reviewer commit:** a130c7fa7a40b04f5ae05fe6a00c328784fa49df
**Validated A1 distributable MATLAB SHA-256:** 1a8d609144d692725ff2ee2618ea8b25129a051d04ec20a97f52943adbe35cfc
**Git checkout MATLAB SHA-256 after text-line-ending normalization by Git:** 5f72a5aba7650bc7ac51ac48c72db8e5d7ede19d856a75d29b8367387da43352
**Normalized MATLAB source content identical across the two representations:** Yes
**Full eICU reserve outcomes accessed before amendment:** No
**Formal U9 ADAPT on full eICU before amendment:** No
**PREPARE before amendment:** No
**UNSEAL before amendment:** No

## Trigger

Public eICU-CRD Demo v2.0 was used only as an engineering/schema dry run before credentialed full eICU access. The dry run exposed two implementation portability defects before the frozen hospital-count gate:

1. The official APACHE result identifier is `apachePatientResultsID`, while the frozen v1.0 adapter requested `apachePatientsResultsID`.
2. On Windows, case-insensitive filesystem matching allowed the table locator's camel-case and lower-case glob patterns to return the same physical file under differently cased path strings, which was then falsely classified as an ambiguous table.

## Authorized corrections

A1 makes exactly these implementation changes:

1. `apachePatientsResultsID` -> `apachePatientResultsID`.
2. Canonical downstream `apachepatientsresultsid` -> `apachepatientresultsid`.
3. Table-locator path de-duplication is made case-insensitive on Windows-compatible paths by applying `unique(lower(paths), 'stable')` and retaining the corresponding original paths.

No other scientific source-code change is authorized by A1.

## Frozen scientific specification unchanged

A1 does **not** change:

- APACHE version: 4.
- Minimum age: 18.
- Minimum outcome-free hospital roster: 512.
- Hospital-role counts: 6 SOURCE, 6 HISTORY, 6 CALIBRATION, 20 RESERVE.
- Required hospitals: 38.
- Budgets: 64, 128, 256.
- Replicates: 200.
- Four-fold guarded observer geometry.
- Maximum transport weight: 0.35.
- Decision guard band: 0.01.
- Role seed: 2026081001.
- Master seed: 2026081002.
- Calibration seed: 2026081003.
- Ten outcome-free matched hospital pairs.
- Any integrity, certification, safety, decision-efficiency, mechanism, or conceptual-witness gate.
- One-shot authorization and reserve-outcome access policy.
- Claim boundary.

## Regression requirement

The amended package must pass:

1. Native MATLAB `SELFTEST`.
2. Public-demo schema regression using the exact official demo files and frozen adapter.
3. The demo adapter must proceed through table discovery, selected-column import, APACHE-IVa cohort construction, and stop only at `CMDO:U9:HospitalCount`.
4. No PREPARE seal, one-shot marker, or canonical U9 result may be produced in the demo regression.
5. Static checks must confirm all frozen constants above remain present and unchanged.
6. The source exact-diff audit must confirm that reversing A1.1-A1.3 reconstructs the base v1.0 source text.

The public demo is **not** scientific evidence for U9 and creates no manuscript claim. Its sole purpose is pre-outcome engineering validation.

## Distribution and Git line-ending boundary

The validated A1 distributable package and the GitHub text checkout contain identical normalized MATLAB source text. Git normalized the committed MATLAB text from CRLF to LF, so their raw file SHA-256 values differ even though their source content is identical.

The A1 package manifest records the exact bytes of the distributable package and is therefore a **distribution-package manifest**, not a promise that text-file byte hashes will equal a Git checkout after platform-specific line-ending conversion.

Formal U9 execution should use one frozen representation consistently. The current reviewer execution artifact is the validated A1 distributable package; its code SHA-256 is the value recorded above. If a Git checkout is instead used for a future formal pre-outcome execution, its actual checkout code SHA-256 must be recorded in that execution's seal and authorization chain. The two byte representations must not be silently mixed.

## Governance

The original v1.0 package remains preserved as the historical frozen parent. Formal U9 execution on credentialed eICU-CRD v2.0 must use the validated A1 implementation after regression validation is complete. Any future engineering correction before PREPARE requires a new explicit amendment; no scientific threshold may be relaxed in response to observed outcomes.
