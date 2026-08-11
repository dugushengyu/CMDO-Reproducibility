# Data access and redistribution gates

The machine-readable dataset registry is `provenance/datasets.json`. A downloadable
URL is not itself redistribution permission. Raw provider data remain outside Git.

## Public automatic routes

With `--allow-network`, original stage code may acquire declared official/public
routes including ISIC releases, NLM chest radiographs, TBX11K, public Zenodo/Mendeley
or TCIA development assets, CIFAR variants, PACS, JHU Amazon sentiment, torchvision
digits, MultiNLI, ACS PUMS/Folktables, MedMNIST, UCI-296, and CDC NHANES.

## Historical Stage11C official receipts

The accepted Stage11C-R path depends on six exact historical official receipt files.
They are **not redistributed by GitHub or the portable package**. Before a fresh
full-claim replay, place them under:

`<project-root>/00_Data_Acquisition/Stage11C_Manual_Official_Receipts/`

The exact filenames, sizes, and SHA-256 values are in
`provenance/historical_receipts.json`. Preflight verifies all six and returns
`BLOCKED_HISTORICAL_RECEIPTS` on any absence or mismatch. The runner does not pretend
that these historical receipts can be recreated as a new automatic provider action.

## Manual/account-gated routes

| Dataset/route | Gate | Redistribution | Reviewer treatment |
|---|---|---|---|
| HiSBreast v2 | public Mendeley v2 archive; historical scripted acquisition returned HTTP 403, so official browser/manual download is an allowed prerequisite | do not bundle the ~1 GB raw archive | required by T2-KR; mount at the declared v0.1 acquisition path |
| PH2 | official registration/manual archive | do not bundle | optional provider extension |
| IDRiD | challenge access | no raw GitHub copy | historical/extension path only |
| DeepDRiD | challenge/repository terms | do not bundle pending rights | historical path only |
| EyePACS | Kaggle account/competition terms | never public-package raw bytes | historical path only |
| sealed BUSI/OASBUD/Derm7pt assets | historical role/provider terms | no automatic redistribution | excluded unless explicitly authorized |
| eICU-CRD | PhysioNet credentialing/DUA | strictly restricted | U9 excluded from default reviewer profiles |

Configured manual paths may be supplied through an untracked TOML file or
`CMDO_DATA_*` environment variables. They are mounted into the isolated runtime tree,
not copied into the repository.

## Portable-only bootstrap bytes

Large historical bootstrap archives under `bootstrap_inputs/portable/` are included
in the reviewer portable distribution but Git-ignored. They contain only the exact
historical records required to reconstruct chronology or to run the explicitly
archival profile. Their presence does not convert restricted raw provider data into
redistributable data.
