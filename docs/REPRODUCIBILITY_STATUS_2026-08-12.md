# CMDO reproducibility status — 12 August 2026

This note is the current reviewer-facing replay status. It supplements, but does not
erase, the earlier fresh-replay scientific boundary.

## Fresh raw-to-science profile

The fresh accepted chain retains the declared Stage T2-D scientific divergence
boundary. The historical 11/11 authorisation is not forced by changing thresholds,
gates, seeds, budgets, labels, or selectors. Exit code 4 remains a scientific
non-reproduction boundary rather than an engineering crash.

## Retrospective archival downstream profile

Using byte-verified historical accepted parents and immutable historical source code,
the downstream chain has now been audited through T2-MN:

- T2-KR: Linux scientific path reproduced with only machine-precision continuous
  numerical tails.
- T2-L: the true historical-parent Linux scientific path reproduced; the meta table
  was byte-exact and residual continuous differences were machine precision.
- T2-M: all three historical deterministic performance checkpoints reproduced to
  floating-point roundoff and all 15 frozen gates passed without threshold changes.
- T2-MN: the historical T2-M checkpoint, provider target identities, provider
  regimes, gates and decisions reproduced; archive differences are dynamic
  provenance/rendering plus machine-precision continuous tails, with no discrete
  scientific divergence.

This archival profile is implementation/reproducibility evidence and is not
represented as a fresh raw-to-science accepted chain.

## T2-L raw-image representation boundary

The frozen ResNet50 IMAGENET1K_V2 representation was reconstructed under the pinned
Linux CPU stack. Raw-image SHA identities and historical image-ID arrays were exact.
Cross-machine reconstruction showed only sparse float32 terminal-bit differences:

- ISIC2017_TEST: max absolute embedding difference 1.1920928955078125e-7
- ISIC2018_TEST: max absolute embedding difference 1.1920928955078125e-7
- ISIC2019_TEST: max absolute embedding difference 5.960464477539063e-8

Historical frozen embedding arrays therefore remain the byte-identical archival
checkpoint; fresh raw-image representation replay is classified as
machine-precision numerical reproduction. No scientific gate, selector, regime or
conclusion is changed by this classification.

## Reviewer interpretation

The reviewer package deliberately distinguishes:

1. engineering/integrity verification;
2. fresh scientific replay and its declared T2-D boundary;
3. retrospective historical-parent continuation;
4. byte-identical frozen archival checkpoints; and
5. machine-precision cross-platform numerical reproduction.

No frozen scientific threshold is relaxed to convert a non-reproduction into a pass.

## U9

U9/eICU remains excluded from all default reviewer profiles and no eICU patient data
is included in the reviewer package. U9 is a separate prospective extension.
