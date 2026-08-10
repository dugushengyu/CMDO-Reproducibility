# MATLAB migration status

The repository now has a portable MATLAB setup/configuration layer, canonical-record loaders, figure helpers, environment/GPU checks, non-data unit tests, all current MATLAB figure sources, native U8/U9 packages, and a single top-level dispatcher.

U0–U7 are imported and provenance-locked but are not yet declared MATLAB-equivalent. Their original implementations mix deep-learning/dataset ecosystems and sealed prospective workflows. Each future port must satisfy:

1. fixed input fixture and source hash;
2. exact seed/config capture;
3. column/schema equivalence;
4. numerical comparison against canonical CSV/JSON outputs;
5. explicit tolerance and discrepancy report;
6. seal/governance review before changing the default runner.

Current execution rule: figures read frozen U4C–U7 canonical records; U8/U9 use their native MATLAB packages; no sealed U0–U7 stage is automatically re-executed.
