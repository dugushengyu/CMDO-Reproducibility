# Drive cleanup and GitHub publication

Cleanup is intentionally a second transaction after reproduction, not part of the
runner.

## Current Drive proposal

The exact-ID proposal is `cleanup/drive_cleanup_manifest.csv`. Its current targeted
scope contains 134 files:

- 89 `KEEP`;
- 34 `ARCHIVE_CANDIDATE`;
- 10 `REVIEW`;
- 1 `DELETE_CANDIDATE` (generated Python bytecode only).

No row is authorized for deletion. The inventory covers five migration/code/figure/
governance roots and explicitly does not cover the full raw-data Drive. The archive
candidates total about 139 MB, mostly older figure renders and explicitly labelled
legacy/superseded files. Archiving them is reversible and remains preferable to
deletion until a second backup is verified.

## Required order

1. Run repository audit and unit tests.
2. Run `frozen` successfully on the delivery machine.
3. Complete `full-claim`, or record every typed external gate that prevents it.
4. Produce a public GitHub snapshot containing no restricted raw assets.
5. Create a second independent backup and verify its hashes.
6. Review the exact Drive IDs in the cleanup CSV.
7. Confirm rows explicitly; archive first, delete only irreproducible-free generated
   artifacts.

## GitHub status boundary

The local repository is ready to publish, but publication is only complete after an
accessible remote repository exists and its commit SHA is verified through the
GitHub connection. Raw data, ignored canonical/frozen assets and run outputs are not
part of the Git commit. The portable delivery ZIP carries the small ignored assets
needed for the frozen route separately.

GitHub cleanup should be derived from the committed tree after publication. It must
not be inferred from an inaccessible or nonexistent remote, and it must not remove
the provenance manifests, governance evidence or source hashes.
