# Data access and redistribution gates

The machine-readable source of truth is `provenance/datasets.json`. Reviewers should
use official routes and retain the provider receipt/version/hash in their run
directory. A script being able to download a file does not itself grant a right to
redistribute it.

## Automatic public routes

These are fetched by the original stage code when `--allow-network` is present:

- ISIC collections/releases and provider metadata;
- NLM Montgomery and Shenzhen chest radiographs;
- TBX11K's author route;
- public Zenodo, Mendeley and TCIA development assets;
- CIFAR-10, CIFAR-10.1 and CIFAR-10-C;
- PACS and the official JHU Amazon sentiment dataset;
- torchvision digit datasets and MultiNLI;
- ACS PUMS/Folktables, MedMNIST and UCI-296;
- CDC NHANES public-use files.

The portable package contains code, manifests and small result records, not those raw
downloads.

## Manual/account-gated routes

| Dataset | Gate | Redistribution rule | Default profile |
|---|---|---|---|
| PH2 | official registration/manual archive | do not bundle | optional provider extension |
| IDRiD | challenge access workflow | no raw GitHub copy | historical replay only |
| DeepDRiD | official challenge/repository terms need confirmation | do not bundle pending audit | historical replay only |
| EyePACS | Kaggle competition rules/account | never include in public package | historical replay only |
| BUSI/OASBUD/Derm7pt locked assets | sealed historical role and provider terms | no automatic access | excluded from accepted replay download |
| eICU-CRD | PhysioNet credentialing, training and DUA | strictly excluded | U9 optional; never default |

The runner accepts manual paths through an untracked TOML file or `CMDO_DATA_*`
environment variables. It symlinks them into a new runtime tree; it does not copy
them into the repository or package.

## Reviewer-safe publication boundary

GitHub may contain source, environment files, hashes, data dictionaries, small
canonical result records where redistribution is allowed, and the SourceData
workbook. Raw images, credentialed health data, account-gated archives, model caches
and local path files must remain outside Git.
