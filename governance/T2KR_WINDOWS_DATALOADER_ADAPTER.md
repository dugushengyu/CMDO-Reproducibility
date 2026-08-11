# T2-KR Windows DataLoader compatibility adapter

The immutable Stage T2-KR v0.4 source creates a PyTorch DataLoader with
`num_workers=2` while the scientific pipeline executes at module top level.

The historical Linux/Colab execution environment uses a process model under
which this was executable. Windows multiprocessing uses `spawn`; each
DataLoader worker therefore re-imports and re-executes the complete top-level
T2-KR pipeline and fails Python's safe-import requirement before embedding.

The reproduction runtime adapter therefore applies:

- Windows: `num_workers=0`
- non-Windows: `num_workers=2`

The authoritative source bytes remain unchanged.

The adapter does not change dataset membership, image ordering
(`shuffle=False`), batch size, preprocessing, ResNet-50 weights, model state,
embedding dimension, embedding normalization, source axes, labels, random
seeds, estimators, budgets, thresholds, gates, outcomes, or locked-blind
access. It changes only the platform-specific image-loading execution mode.

The Windows-adapted replay successfully completed Stage T2-KR with both
expansion targets, all five budgets, 23,904 extension-result rows, six
expansion edges, locked-blind access remaining false, single-pilot deployment
remaining prohibited, and Stage 12 remaining false.
