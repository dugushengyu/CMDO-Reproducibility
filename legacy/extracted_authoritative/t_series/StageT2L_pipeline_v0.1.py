# Stage T2-L: independent target regime expansion
import base64, gc, hashlib, io, json, math, os, random, re, shutil, subprocess, sys, tarfile, time, warnings, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
import pandas as pd
import requests
import matplotlib.pyplot as plt
from PIL import Image, ImageOps
from scipy.fft import dctn
from scipy.linalg import solve_triangular
from scipy.optimize import minimize
from scipy.special import logsumexp
from scipy.stats import spearmanr
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import mean_absolute_error, roc_auc_score
from sklearn.model_selection import GroupKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")
try:
    from IPython.display import display
except Exception:
    display = print

IN_COLAB = False
try:
    from google.colab import drive
    drive.mount("/content/drive")
    IN_COLAB = True
except Exception:
    pass

DEFAULT_ROOT = Path("/content/drive/MyDrive/Cross-Modal_Diagnostic_Observability") if IN_COLAB else Path.cwd()
PROJECT_ROOT = Path(os.environ.get("CDO_PROJECT_ROOT", str(DEFAULT_ROOT)))
CODE_ROOT = PROJECT_ROOT / "05_Code" / "Cross_Modal"
THEORY_ROOT = PROJECT_ROOT / "03_Theory" / "Directed_Diagnostic_Evidence_Transport_v1.0"
STUDY_ROOT = PROJECT_ROOT / "04_Study_Design"
MAP_ROOT = PROJECT_ROOT / "02_Dataset_Map" / "StageT2-L_Independent_Target_Regime_Expansion_v0.1"
CM_ROOT = PROJECT_ROOT / "06_Data_Records" / "Cross_Modal"
ACQ_ROOT = PROJECT_ROOT / "00_Data_Acquisition" / "Cross_Modal_Independent_Target_Expansion_v0.2"
RESULT_ROOT = CM_ROOT / "StageT2-L_Independent_Target_Regime_Expansion_v0.1"

P0, P1, P2, P3, P4, P5, P6, P7 = [RESULT_ROOT / x for x in [
    "00_Protocol", "01_Acquisition_And_Manual_Queue", "02_Harmonised_Targets",
    "03_Fingerprints_And_Dedup", "04_Frozen_Embeddings_And_Source_Scores",
    "05_MultiBudget_Extension", "06_Meta_Regime_Analysis", "07_Results"
]]
for path in [CODE_ROOT, THEORY_ROOT, STUDY_ROOT, MAP_ROOT, ACQ_ROOT, P0, P1, P2, P3, P4, P5, P6, P7]:
    path.mkdir(parents=True, exist_ok=True)

NOTEBOOK_NAME = "CrossModal_StageT2-L_Independent_Target_Regime_Expansion_Acquisition_Harmonisation_And_MultiBudget_v0.1.ipynb"
NOTEBOOK_PATH = CODE_ROOT / NOTEBOOK_NAME
THEORY_PATH = THEORY_ROOT / "Directed_Diagnostic_Evidence_Transport_Evidence_Limited_And_Model_Limited_Regime_Theory_v1.0.md"
PREREG_PATH = STUDY_ROOT / "StageT2-L_Independent_Target_Regime_Expansion_Preregistration_v1.0.md"
REGISTRY_PATH = MAP_ROOT / "StageT2-L_Independent_Target_Regime_Expansion_Candidate_Registry_v0.2.csv"
MANUAL_PATH = STUDY_ROOT / "StageT2-L_Manual_Download_Queue_And_Drop_Locations_v0.1.md"
README_PATH = CODE_ROOT / "README_Cross_Modal_Notebook_Index_v1.8.md"

EMBEDDED_THEORY = "# Directed Diagnostic Evidence Transport v1.0\n\n## Evidence-limited and model-limited diagnostic-audit regimes\n\n### 1. Motivation\n\nCross-domain diagnostic auditing asks whether a frozen source decision score remains diagnostically informative on a target domain and how much target evidence is needed to estimate that performance. The development programme has now established three distinct levels:\n\n1. target performance can be predicted from source-target observability geometry;\n2. target-expected evidence demand is partly predictable;\n3. one realised small pilot cannot safely control acquisition.\n\nStage T2-KR adds a further distinction. BrEaST-Lesions-USG becomes accurately auditable as the witness budget grows, whereas MILK10K remains above the frozen error threshold through 128 witness groups. Target difficulty therefore cannot be represented by a single scalar evidence budget alone.\n\n### 2. Two-regime formulation\n\nLet \\(\\varepsilon_T(B)\\) be the target-level median absolute AUC audit error under the frozen estimator family at witness-group budget \\(B\\).\n\n#### Evidence-limited regime\n\nA target is evidence-limited when increasing representative target evidence is sufficient to make the diagnostic audit operational:\n\n\\[\n\\exists B \\le B_{\\max}: \\varepsilon_T(B) \\le \\tau.\n\\]\n\nThe principal bottleneck is finite target evidence. Once the target receives enough witness groups, the frozen representation and posterior family can use them successfully.\n\n#### Model-limited regime\n\nA target is model-limited within the current audit family when additional evidence does not produce operational accuracy:\n\n\\[\n\\varepsilon_T(B_{\\max}) > \\tau\n\\]\n\nand the error curve fails to show substantial monotone repair. The bottleneck may be target-posterior misspecification, inadequate source-score geometry, unobserved target substructure, label-condition shift, or other non-identifiability within the frozen representation-estimator pair.\n\nThis is a statement relative to the current model family, not an assertion that the target is intrinsically impossible.\n\n#### Evidence-demanding or right-censored regime\n\nA target is evidence-demanding when the maximum tested budget is insufficient for a regime decision but the curve still shows meaningful repair. Such a target is neither declared operational nor declared model-limited.\n\n### 3. Predictability hierarchy\n\nThe expanded hierarchy is:\n\n1. **performance observability** — can target edge performance be predicted?\n2. **expected evidence complexity** — can the target's average evidence demand be ranked?\n3. **realised-pilot deployability** — can one small realised pilot safely control acquisition?\n4. **repairability regime** — is more evidence sufficient within the frozen model family?\n5. **repair mechanism transfer** — can a correction learned on other targets repair this target?\n\nThe current evidence supports levels 1 and 2 developmentally, rejects level 3, and motivates independent expansion of level 4. Level 5 remains target-conditional.\n\n### 4. Frozen operational regime criteria for Stage T2-L\n\nFor the frozen AMW-DDET family and \\(\\tau=0.04\\):\n\n- **evidence-limited**: median error at \\(B=128\\) is at most 0.04;\n- **model-limited**: median error at \\(B=128\\) exceeds 0.04 and either\n  - \\(\\varepsilon_T(128)/\\varepsilon_T(8) \\ge 0.8\\), or\n  - Spearman correlation between budget and median error is at least -0.3;\n- **evidence-demanding/right-censored**: all remaining non-operational cases.\n\nThese thresholds are frozen before new target outcomes are observed.\n\n### 5. Scientific consequence\n\nEvidence forecasting and evidence restoration are different problems. A target may be correctly forecast as difficult while remaining unrepairable by the current audit model. A publishable theory should therefore report:\n\n- predicted evidence demand;\n- observed evidence curve;\n- operational budget or censoring;\n- repairability regime;\n- uncertainty and target independence.\n\n### 6. Prohibitions\n\nRegime expansion must not:\n\n- retune RA-CB using the new target outcomes;\n- relabel provider partitions after seeing favourable curves;\n- count known source aliases or near-duplicates as independent targets;\n- reinterpret right-censoring as observed success at an untested budget;\n- reopen the failed single-pilot deployment claim;\n- touch locked-blind assets or Stage 12.\n"
EMBEDDED_PREREG = '# Stage T2-L preregistration v1.0\n\n## Independent target regime expansion\n\n**Frozen:** 23 July 2026  \n**Parent Stage T2-KR v0.4 final record:** `c783c8dd909277600b1c9d2675f4236fda0e57bd38adeab09fe48b0bae66f6d4`  \n**Single-pilot status:** deployment prohibited  \n**Blind status:** locked blind sentinels and all blind outcomes prohibited\n\n## 1. Purpose\n\nAcquire and adjudicate additional independent development targets, compute frozen source-axis scores, extend the five-budget audit curves, and test whether evidence-limited and model-limited regimes recur beyond BrEaST and MILK10K.\n\n## 2. Frozen acquisition priority\n\n### Primary institution/provider targets\n\nAttempt patient-grouped provider partitions from the official ISIC 2020 training collection:\n\n- Hospital Clínic de Barcelona;\n- Medical University of Vienna;\n- The University of Queensland;\n- Melanoma Institute Australia.\n\nMemorial Sloan Kettering is excluded because an MSK source axis already exists. Athens is retained as a route/metadata hold unless public labelled training rows and an explicit provider attribution are recovered.\n\n### Secondary release-domain targets\n\nUse official challenge ground truth and selective official image downloads for:\n\n- ISIC 2017 validation;\n- ISIC 2017 test;\n- ISIC 2018 test;\n- ISIC 2019 test.\n\nThese are secondary release domains, not institution-independent cohorts. They are analysed separately and cannot substitute one-for-one for institution-level evidence.\n\n### Automatic audit-only acquisitions\n\n- RFMiD 2.0 from Zenodo;\n- Pakistan TB chest-radiograph dataset v3 from Mendeley.\n\nThese may proceed to structural/grouping audit. They cannot be scored without an exact compatible endpoint, patient grouping and existing frozen source axis.\n\n## 3. Frozen endpoint\n\nFor every scored dermoscopy target:\n\n\\[\nY=1 \\Longleftrightarrow \\text{melanoma},\\qquad\nY=0 \\Longleftrightarrow \\text{melanocytic nevus}.\n\\]\n\nOther diagnoses are excluded.\n\nFor ISIC 2017, rows with melanoma=0 and seborrheic_keratosis=0 are treated as nevus according to the released three-class challenge definition.\n\n## 4. Frozen target sampling\n\n- one selected image per released patient for provider targets;\n- deterministic image-level groups for release-domain targets lacking patient identifiers;\n- retain at most 150 positive groups and 450 negative groups per target;\n- deterministic SHA-256 lexical selection;\n- require at least 128 total groups, 20 positive groups and 60 negative groups for five-budget scoring;\n- fixed 80/20 grouped development/validation split, seed 20260723.\n\n## 5. Frozen deduplication\n\nBefore target admission:\n\n1. exclude image and lesion identifiers already present in HAM10000, ISIC-MSK1, ISIC-UDA1 or MILK10K;\n2. exclude official ISIC 2020 duplicate-list rows;\n3. decoded RGB pixel SHA-256 exact comparison;\n4. pHash Hamming distance <=4 becomes a conservative hold;\n5. earlier frozen sources and targets have priority;\n6. cross-new-target duplicates are assigned only to the higher-priority preregistered target.\n\n## 6. Frozen representation and source axes\n\n- torchvision ResNet-50 IMAGENET1K_V2;\n- 2,048-dimensional L2-normalised embeddings;\n- frozen source axes: HAM10000, ISIC-MSK1 and ISIC-UDA1;\n- no source refit or calibration.\n\n## 7. Frozen audit experiment\n\nBudgets: 8, 16, 32, 64, 128.  \nReplicates: 100 per target-budget.  \nMethods inherited without modification:\n\n- random direct;\n- random logistic plug-in;\n- random semi-supervised joint GMM;\n- active direct;\n- AMW-DDET;\n- AMW-CB2;\n- RA-CB-AMW-DDET.\n\n## 8. Chronology\n\nBefore any new multi-budget truth is constructed, fit and seal the target-expected evidence model on the original 13 targets plus BrEaST and MILK10K. The model input is the target-median budget-8 cross-method disagreement. It is not a single-pilot deployment model.\n\n## 9. Frozen regime rule\n\nAt \\(\\tau=0.04\\):\n\n- evidence-limited: median AMW-DDET error at B=128 <=0.04;\n- model-limited: B=128 error >0.04 and either B128/B8 >=0.8 or budget-error Spearman >=-0.3;\n- evidence-demanding/right-censored: otherwise.\n\n## 10. Interpretation and authority\n\nThis stage is development-only. A successful run may update the target-level meta-dataset and regime evidence. It cannot:\n\n- retune the estimator family;\n- reactivate single-pilot deployment;\n- count audit-only acquisitions as scored targets;\n- touch locked-blind assets or outcomes;\n- authorise Stage 12.\n'
EMBEDDED_REGISTRY = 'dataset_id,modality,endpoint,expansion_role,independence_unit,access_mode,licence,official_url,grouping_status,label_status,overlap_risk,notes\nISIC2020_BARCELONA,dermoscopy,melanoma_vs_melanocytic_nevus,PRIMARY_PROVIDER_TARGET,patient,AUTO_ISIC_CLI_METADATA_AND_SELECTIVE_IMAGES,CC BY-NC 4.0,https://challenge.isic-archive.com/data/,patient_id,target+diagnosis,HIGH,Hospital Clinic de Barcelona attribution\nISIC2020_VIENNA,dermoscopy,melanoma_vs_melanocytic_nevus,PRIMARY_PROVIDER_TARGET,patient,AUTO_ISIC_CLI_METADATA_AND_SELECTIVE_IMAGES,CC BY-NC 4.0,https://challenge.isic-archive.com/data/,patient_id,target+diagnosis,MEDIUM,Vienna cohort; exclude any frozen ID or fingerprint overlap\nISIC2020_QUEENSLAND,dermoscopy,melanoma_vs_melanocytic_nevus,PRIMARY_PROVIDER_TARGET,patient,AUTO_ISIC_CLI_METADATA_AND_SELECTIVE_IMAGES,CC BY-NC 4.0,https://challenge.isic-archive.com/data/,patient_id,target+diagnosis,LOW,University of Queensland attribution\nISIC2020_MIA,dermoscopy,melanoma_vs_melanocytic_nevus,PRIMARY_PROVIDER_TARGET,patient,AUTO_ISIC_CLI_METADATA_AND_SELECTIVE_IMAGES,CC BY-NC 4.0,https://challenge.isic-archive.com/data/,patient_id,target+diagnosis,LOW,Melanoma Institute Australia attribution\nISIC2020_MSK,dermoscopy,melanoma_vs_melanocytic_nevus,EXCLUDE_EXISTING_SOURCE,patient,DO_NOT_ACQUIRE_AS_TARGET,CC BY-NC 4.0,https://challenge.isic-archive.com/data/,patient_id,target+diagnosis,CERTAIN,Existing ISIC_MSK1 source axis\nISIC2020_ATHENS,dermoscopy,melanoma_vs_melanocytic_nevus,CONDITIONAL_PROVIDER_HOLD,patient,AUTO_METADATA_ONLY,CC BY-NC 4.0,https://challenge.isic-archive.com/data/,patient_id,target+diagnosis,UNKNOWN,Admit only when labelled public training rows and provider attribution are explicit\nISIC2017_VALIDATION,dermoscopy,melanoma_vs_nevus,SECONDARY_RELEASE_TARGET,image,AUTO_DIRECT_OFFICIAL,CC-0,https://challenge.isic-archive.com/data/,image_id,melanoma+seborrheic_keratosis,MEDIUM,Validation release domain\nISIC2017_TEST,dermoscopy,melanoma_vs_nevus,SECONDARY_RELEASE_TARGET,image,AUTO_DIRECT_OFFICIAL,CC-0,https://challenge.isic-archive.com/data/,image_id,melanoma+seborrheic_keratosis,MEDIUM,Test release domain\nISIC2018_TEST,dermoscopy,melanoma_vs_nevus,SECONDARY_RELEASE_TARGET,image,AUTO_DIRECT_OFFICIAL,CC BY-NC,https://challenge.isic-archive.com/data/,image_id,MEL+NV,HIGH,Strict ID/pixel/pHash dedup against HAM/MSK/UDA\nISIC2019_TEST,dermoscopy,melanoma_vs_nevus,SECONDARY_RELEASE_TARGET,image,AUTO_DIRECT_OFFICIAL,CC BY-NC,https://challenge.isic-archive.com/data/,image_id,MEL+NV,HIGH,Strict ID/pixel/pHash dedup against all frozen dermoscopy assets\nRFMID2_0,retinal_fundus,referable_DR_candidate,AUDIT_ONLY_AUTO,image/patient_if_released,AUTO_ZENODO_ZIP,Zenodo record terms,https://zenodo.org/records/7505822,verify,multilabel CSV,LOW,Structural and grouping audit only\nTB_CXR_PAKISTAN_2026,chest_radiograph,tuberculosis_vs_normal,AUDIT_ONLY_AUTO,patient_if_released,AUTO_MENDELEY_ZIP,CC BY 4.0,https://data.mendeley.com/datasets/8j2g3csprk/3,verify,folder/metadata,LOW,Structural and grouping audit only\nPH2,dermoscopy,melanoma_vs_nevus,MANUAL_PRIMARY,lesion,MANUAL_QUICK_REGISTRATION,research/education,https://www.fc.up.pt/addi/ph2%20database.html,lesion,diagnosis,LOW,Place official archive in exact drop folder\nE_OPHTHA,retinal_fundus,DR_lesion_or_referable_DR,MANUAL_PRIMARY,patient/visit,MANUAL_OFFICIAL_FORM,research agreement,https://www.adcis.net/en/third-party/e-ophtha/,patient_visit,official annotation,LOW,ADCIS form required\nMESSIDOR_ORIGINAL,retinal_fundus,referable_DR,MANUAL_PRIMARY,exam/patient,MANUAL_OFFICIAL_AGREEMENT,official research terms,https://www.adcis.net/en/third-party/messidor/,exam,official grade,LOW,Needed also for MAPLES-DR labels\nBRSET_V1_0_1,retinal_fundus,referable_DR,MANUAL_PRIMARY,patient,MANUAL_PHYSIONET_DUA,PhysioNet Credentialed Health Data License,https://physionet.org/content/brazilian-ophthalmological/1.0.1/,patient,DR grade,LOW,"Credentialing, CITI training and DUA"\nmBRSET_V1_0,retinal_fundus,referable_DR,MANUAL_PRIMARY,patient,MANUAL_PHYSIONET_DUA,PhysioNet credentialed terms,https://physionet.org/content/mbrset/1.0/,patient,referable DR,LOW,Credentialed mobile retinal target\nODIR5K_DR,retinal_fundus,referable_DR,MANUAL_PRIMARY,patient,MANUAL_GRAND_CHALLENGE,challenge terms,https://odir2019.grand-challenge.org/dataset/,patient,diagnostic keywords,LOW,Registration required\nFGADR_SEG,retinal_fundus,referable_DR,MANUAL_PRIMARY,verify,MANUAL_SIGNED_AGREEMENT,non-commercial agreement,https://csyizhou.github.io/FGADR/,verify,DR grade,LOW,Signed agreement\nUDIAT_DATASET_B,breast_ultrasound,malignant_vs_benign,MANUAL_PRIMARY,patient/image,MANUAL_AUTHOR_REQUEST,author permission,https://helward.mmu.ac.uk/STAFF/M.Yap/dataset.php,verify,binary label,LOW,Author request\n'
EMBEDDED_MANUAL = '# Stage T2-L manual download queue and exact Drive locations v0.1\n\nThe Stage T2-L notebook creates these folders automatically. Place the original official archive unchanged in the corresponding `00_Raw_Inbox`; do not extract it manually.\n\nBase folder:\n\n`MyDrive/Cross-Modal_Diagnostic_Observability/00_Data_Acquisition/Cross_Modal_Independent_Target_Expansion_v0.2/`\n\n## Priority 1: PH2\n\nOfficial route:\n\n`https://www.fc.up.pt/addi/ph2%20database.html`\n\nDestination:\n\n`.../PH2/00_Raw_Inbox/`\n\nComplete the official quick registration and place the PH2 archive there.\n\n## Priority 2: MESSIDOR original\n\nOfficial route:\n\n`https://www.adcis.net/en/third-party/messidor/`\n\nDestination:\n\n`.../MESSIDOR_ORIGINAL/00_Raw_Inbox/`\n\nUse the official ADCIS agreement. Do not use a third-party mirror.\n\n## Priority 3: e-ophtha\n\nOfficial route:\n\n`https://www.adcis.net/en/third-party/e-ophtha/`\n\nDestination:\n\n`.../E_OPHTHA/00_Raw_Inbox/`\n\nThe ADCIS request form is required.\n\n## Credentialed retinal datasets\n\n### BRSET v1.0.1\n\n`https://physionet.org/content/brazilian-ophthalmological/1.0.1/`\n\nDestination:\n\n`.../BRSET_V1_0_1/00_Raw_Inbox/`\n\nRequires PhysioNet credentialing, CITI training and the DUA.\n\n### mBRSET v1.0\n\n`https://physionet.org/content/mbrset/1.0/`\n\nDestination:\n\n`.../mBRSET_V1_0/00_Raw_Inbox/`\n\nRequires the applicable PhysioNet access process.\n\n## Other agreement/registration routes\n\n- ODIR-5K: `https://odir2019.grand-challenge.org/dataset/`  \n  Destination: `.../ODIR5K_DR/00_Raw_Inbox/`\n- FGADR: `https://csyizhou.github.io/FGADR/`  \n  Destination: `.../FGADR_SEG/00_Raw_Inbox/`\n- UDIAT Dataset B: `https://helward.mmu.ac.uk/STAFF/M.Yap/dataset.php`  \n  Destination: `.../UDIAT_DATASET_B/00_Raw_Inbox/`\n\nThe notebook reports which automatic routes succeeded before any manual action is required.\n'
EMBEDDED_README = '# Cross-Modal Notebook Index v1.8\n\nUpdated: 23 July 2026\n\n## Active stage\n\n`CrossModal_StageT2-L_Independent_Target_Regime_Expansion_Acquisition_Harmonisation_And_MultiBudget_v0.1.ipynb`\n\n## Scope\n\n- automatically acquire official ISIC release-domain targets;\n- attempt ISIC 2020 provider partitions using official collection metadata;\n- perform exact and perceptual cross-roster deduplication;\n- audit RFMiD 2.0 and the Pakistan TB chest-radiograph release;\n- generate exact manual download locations;\n- score every passing dermoscopy target with frozen HAM/MSK/UDA axes;\n- run five budgets × 100 replicates;\n- test evidence-limited versus model-limited regimes;\n- preserve the single-pilot rejection and locked-blind firewall.\n\nUse a clean Colab CPU runtime and Run all.\n'

T2KR_ROOT = CM_ROOT / "StageT2-KR_Frozen_Axis_Schema_Adapter_And_CPU_Continuation_v0.4"
T2KR_FINAL = T2KR_ROOT / "06_Results" / "StageT2-KR_Complete_v0.4.json"
T2KR_REPS = T2KR_ROOT / "04_MultiBudget_Extension" / "StageT2-KR_All_MultiBudget_Extension_Replicates_v0.4.csv"
T2H_FINAL = CM_ROOT / "StageT2-H_Development_Only_Single_Pilot_Deployability_And_Sequential_Forecast_Freeze_v0.1" / "04_Results" / "StageT2-H_Complete_v0.1.json"
T3PF_FINAL = CM_ROOT / "StageT3-PF_Outcome-Free_Preregistration_And_Asset_Preflight_v1.0" / "04_Results" / "StageT3-PF_Activation_Record_v1.0.json"
T2D_REPS = CM_ROOT / "StageT2-D_Development_Only_AMW-DDET_Active_Minimal_Witness_Certificate_v0.1" / "01_Replicate_Results" / "StageT2-D_All_Acquisition_Replicates_v0.1.csv"

STAGE8_ROOT = CM_ROOT / "Stage8_CrossModality_EdgeLibrary_Expansion_v0.1"
MANIFEST_ROOT = STAGE8_ROOT / "01_Acquisition_Manifests"
HAM_MANIFEST = MANIFEST_ROOT / "HAM10000_Harmonised_Acquisition_Manifest_v0.1.csv"
MSK_MANIFEST = MANIFEST_ROOT / "ISIC_MSK1_Harmonised_Acquisition_Manifest_v0.1.csv"
UDA_MANIFEST = MANIFEST_ROOT / "ISIC_UDA1_Harmonised_Acquisition_Manifest_v0.1.csv"
DERM_AXIS_ROOT = STAGE8_ROOT / "03_Frozen_Source_Axes"
DERM_SUMMARY = DERM_AXIS_ROOT / "Stage8_Source_Recoverability_Summary_v0.1.csv"
T2J_ROOT = CM_ROOT / "StageT2-J_Expansion_Harmonisation_Dedup_And_Public_Route_Repair_v0.1"
MILK_MANIFEST = T2J_ROOT / "02_Harmonised_Manifests" / "StageT2-J_MILK10K_Harmonised_Exact_Manifest_v0.1.csv"
REFERENCE_CACHE = T2J_ROOT / "03_Fingerprints_And_Dedup" / "StageT2-J_Existing_Dermoscopy_Reference_Fingerprints_v0.1.csv"

AXIS_PATHS = {
    "HAM10000": DERM_AXIS_ROOT / "HAM10000_Frozen_Source_Axis_v0.1.npz",
    "ISIC_MSK1": DERM_AXIS_ROOT / "ISIC_MSK1_Frozen_Source_Axis_v0.1.npz",
    "ISIC_UDA1": DERM_AXIS_ROOT / "ISIC_UDA1_Frozen_Source_Axis_v0.1.npz",
}
AXIS_SHA = {
    "HAM10000": "0988518fcfbcb3436f43fbdff37b61395b8ba8b3715fccbc295f67cd0ab3dcad",
    "ISIC_MSK1": "5011be88de7e877d836f0518540c53dd3f6a34c57225b729e22285ff1cfcd9d2",
    "ISIC_UDA1": "316857360dd3a4f3c9f19f811cc58a4c17c1da1372319cbcc9382e7eca76b670",
}
EXPECTED_MODEL_STATE_SHA256 = "3f2c393680172fd552aae83bd2f0e3c389457e7d13499e3490c2a314f5642051"
EXPECTED_PARENT = {
    "t2kr": "c783c8dd909277600b1c9d2675f4236fda0e57bd38adeab09fe48b0bae66f6d4",
    "t2h": "27d4c7afe711ba66ea44d11f3ef173820e11ef1eba7a44530446a3e5444aa99f",
    "t3pf": "4397cee7798f684159ed77aa5e1edd7b7ae0a24378047d6c89b37ef9ef738a52",
}
EXPECTED_DOCS = {
    "theory": "b777d9db046fadde5af81937a250625c11296d751e8b944c788a4cf7d8121d35",
    "prereg": "8b2174ac53f1dd671df15fbe585eeffd1fca61aac56f456f06dd72c04bf99b25",
    "registry": "d4fdf7827ea77cff701ef1bd1e8d12cfa0677bbb41b57c044a72552aaf470cc6",
    "manual": "1187c4faebaee46ac72a3ad9341663e86969948c8a178c1c38910617173386a6",
}
LOCKED_BLIND = {"BUSI_CAIRO_2019", "OASBUD_2017", "DERM7PT_2019"}
SEED = 20260723
BUDGETS = [8, 16, 32, 64, 128]
N_REPLICATES = 100
RIDGE_C = 3.0
BALANCE_RIDGE = 0.1
WEIGHT_CLIP = (0.1, 10.0)
MIN_BALANCE_ESS = 8.0
PHASH_MAX_DISTANCE = 4
NEAR_COPY_MIN_CORRELATION = 0.995
MAX_POSITIVE = 150
MAX_NEGATIVE = 450
MIN_TOTAL_GROUPS = 128
MIN_POSITIVE_GROUPS = 20
MIN_NEGATIVE_GROUPS = 60
HTTP_TIMEOUT = (20, 180)
USER_AGENT = "CMDO-StageT2-L/0.1 governed research acquisition"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})

def now():
    return datetime.now(timezone.utc).isoformat()

def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()

def sha_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def sha_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()

def canonical_csv(frame):
    return frame.fillna("").to_csv(index=False, lineterminator="\n", float_format="%.12g")

def write_csv(path, frame):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(canonical_csv(frame), encoding="utf-8")

def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def write_text(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(value, encoding="utf-8")

def verify_self(path, field, expected):
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    claim = value[field]
    core = dict(value)
    core.pop(field)
    assert sha_json(core) == claim, f"Self-hash mismatch: {path}"
    assert claim == expected, f"Unexpected parent record: {path}"
    return value

def materialise(path, text, expected):
    path = Path(path)
    if path.exists():
        assert sha_file(path) == expected, f"Frozen companion file changed: {path}"
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        assert sha_file(path) == expected

materialise(THEORY_PATH, EMBEDDED_THEORY, EXPECTED_DOCS["theory"])
materialise(PREREG_PATH, EMBEDDED_PREREG, EXPECTED_DOCS["prereg"])
materialise(REGISTRY_PATH, EMBEDDED_REGISTRY, EXPECTED_DOCS["registry"])
materialise(MANUAL_PATH, EMBEDDED_MANUAL, EXPECTED_DOCS["manual"])
README_PATH.write_text(EMBEDDED_README, encoding="utf-8")

required = [NOTEBOOK_PATH, T2KR_FINAL, T2KR_REPS, T2H_FINAL, T3PF_FINAL, T2D_REPS,
            HAM_MANIFEST, MSK_MANIFEST, UDA_MANIFEST, MILK_MANIFEST, DERM_SUMMARY, *AXIS_PATHS.values()]
missing = [str(path) for path in required if not Path(path).is_file()]
assert not missing, "Missing required frozen files:\n" + "\n".join(missing)

t2kr = verify_self(T2KR_FINAL, "final_record_sha256", EXPECTED_PARENT["t2kr"])
t2h = verify_self(T2H_FINAL, "final_record_sha256", EXPECTED_PARENT["t2h"])
t3pf = verify_self(T3PF_FINAL, "activation_record_sha256", EXPECTED_PARENT["t3pf"])
assert t2h["single_pilot_deployment_authorised"] is False
assert t3pf["blind_assets_acquired"] is False and t3pf["blind_outcomes_accessed"] is False
assert t3pf["stage12_authorised"] is False
for source, path in AXIS_PATHS.items():
    assert sha_file(path) == AXIS_SHA[source], f"Frozen source axis changed: {source}"

def notebook_source_sha(path):
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    cells = []
    for cell in value.get("cells", []):
        if cell.get("cell_type") in {"code", "markdown"}:
            source = cell.get("source", [])
            source = "".join(source) if isinstance(source, list) else str(source)
            cells.append({"cell_type": cell["cell_type"], "source": source.replace("\r\n", "\n")})
    return sha_json(cells)

protocol_payload = {
    "stage": "StageT2-L",
    "purpose": "independent_target_regime_expansion",
    "parent_t2kr_record": EXPECTED_PARENT["t2kr"],
    "parent_t2h_record": EXPECTED_PARENT["t2h"],
    "parent_t3pf_record": EXPECTED_PARENT["t3pf"],
    "theory_sha256": EXPECTED_DOCS["theory"],
    "preregistration_sha256": EXPECTED_DOCS["prereg"],
    "registry_sha256": EXPECTED_DOCS["registry"],
    "manual_queue_sha256": EXPECTED_DOCS["manual"],
    "notebook_source_sha256": notebook_source_sha(NOTEBOOK_PATH),
    "single_pilot_deployment_remains_prohibited": True,
    "locked_blind_assets_touched": False,
    "locked_blind_outcomes_accessed": False,
    "stage12_authorised": False,
}
protocol_path = P0 / "StageT2-L_Protocol_Seal_v0.1.json"
if protocol_path.exists():
    protocol = json.loads(protocol_path.read_text(encoding="utf-8-sig"))
    claim = protocol.pop("protocol_seal_sha256")
    assert sha_json(protocol) == claim
    protocol["protocol_seal_sha256"] = claim
    for key, value in protocol_payload.items():
        assert protocol[key] == value, f"Protocol replay mismatch: {key}"
else:
    protocol = dict(protocol_payload)
    protocol["sealed_utc"] = now()
    protocol["protocol_seal_sha256"] = sha_json(protocol)
    write_json(protocol_path, protocol)

print("Stage T2-L protocol:", protocol["protocol_seal_sha256"])
print("Single-pilot deployment authorised:", False)
print("Locked blind assets touched:", False)



# Stage T2-L acquisition, harmonisation and cross-roster deduplication
MANUAL_DATASETS = [
    ("PH2", "https://www.fc.up.pt/addi/ph2%20database.html"),
    ("E_OPHTHA", "https://www.adcis.net/en/third-party/e-ophtha/"),
    ("MESSIDOR_ORIGINAL", "https://www.adcis.net/en/third-party/messidor/"),
    ("BRSET_V1_0_1", "https://physionet.org/content/brazilian-ophthalmological/1.0.1/"),
    ("mBRSET_V1_0", "https://physionet.org/content/mbrset/1.0/"),
    ("ODIR5K_DR", "https://odir2019.grand-challenge.org/dataset/"),
    ("FGADR_SEG", "https://csyizhou.github.io/FGADR/"),
    ("UDIAT_DATASET_B", "https://helward.mmu.ac.uk/STAFF/M.Yap/dataset.php"),
]
manual_rows = []
for dataset_id, official_url in MANUAL_DATASETS:
    inbox = ACQ_ROOT / dataset_id / "00_Raw_Inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    instruction = (
        f"Dataset: {dataset_id}\nOfficial route: {official_url}\n"
        f"Place the original official archive unchanged in:\n{inbox}\n"
        "Do not extract manually. Rerun Stage T2-L after placement.\n"
    )
    (inbox / "MANUAL_DROP_HERE.txt").write_text(instruction, encoding="utf-8")
    manual_rows.append({
        "dataset_id": dataset_id,
        "official_url": official_url,
        "exact_drive_drop_folder": str(inbox),
        "status": "MANUAL_ROUTE_READY",
    })
manual_queue = pd.DataFrame(manual_rows)
write_csv(P1 / "StageT2-L_Manual_Download_Queue_v0.1.csv", manual_queue)

def stable_key(*values):
    return hashlib.sha256("||".join(str(v) for v in values).encode()).hexdigest()

def normalise_column(value):
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")

def download_small(url, path, max_bytes=100 * 1024**2):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 100:
        return {"status": "ALREADY_PRESENT", "url": url, "path": str(path),
                "bytes": path.stat().st_size, "sha256": sha_file(path), "error": ""}
    temp = path.with_suffix(path.suffix + ".part")
    try:
        with SESSION.get(url, timeout=HTTP_TIMEOUT, stream=True, allow_redirects=True) as response:
            response.raise_for_status()
            total = 0
            digest = hashlib.sha256()
            with temp.open("wb") as handle:
                for chunk in response.iter_content(1024 * 1024):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > max_bytes:
                        raise RuntimeError("fixed size cap exceeded")
                    handle.write(chunk)
                    digest.update(chunk)
            if total < 100:
                raise RuntimeError("download unexpectedly small")
            temp.replace(path)
            return {"status": "DOWNLOADED", "url": url, "path": str(path),
                    "bytes": total, "sha256": digest.hexdigest(), "error": ""}
    except Exception as exc:
        if temp.exists():
            temp.unlink()
        return {"status": "FAILED", "url": url, "path": str(path),
                "bytes": 0, "sha256": "", "error": f"{type(exc).__name__}: {exc}"}

def safe_extract_zip(source, destination):
    source, destination = Path(source), Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    base = destination.resolve()
    with zipfile.ZipFile(source) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if not (target == base or str(target).startswith(str(base) + os.sep)):
                raise RuntimeError(f"Unsafe ZIP member: {member.filename}")
        archive.extractall(destination)

def load_csv_any(path):
    path = Path(path)
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            csv_names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            if not csv_names:
                raise RuntimeError(f"No CSV in {path}")
            with archive.open(sorted(csv_names)[0]) as handle:
                return pd.read_csv(handle)
    return pd.read_csv(path)

def find_column(frame, candidates, contains=()):
    mapping = {normalise_column(column): column for column in frame.columns}
    for candidate in candidates:
        if normalise_column(candidate) in mapping:
            return mapping[normalise_column(candidate)]
    for column in frame.columns:
        normalized = normalise_column(column)
        if any(token in normalized for token in contains):
            return column
    return None

OFFICIAL_GT = {
    "ISIC2017_VALIDATION": "https://isic-archive.s3.amazonaws.com/challenges/2017/ISIC-2017_Validation_Part3_GroundTruth.csv",
    "ISIC2017_TEST": "https://isic-archive.s3.amazonaws.com/challenges/2017/ISIC-2017_Test_v2_Part3_GroundTruth.csv",
    "ISIC2018_TEST": "https://isic-archive.s3.amazonaws.com/challenges/2018/ISIC2018_Task3_Test_GroundTruth.zip",
    "ISIC2019_TEST": "https://isic-archive.s3.amazonaws.com/challenges/2019/ISIC_2019_Test_GroundTruth.csv",
}
gt_receipts = []
release_candidate_frames = []
for dataset_id, url in OFFICIAL_GT.items():
    raw_dir = ACQ_ROOT / dataset_id / "00_Raw_Inbox"
    raw_dir.mkdir(parents=True, exist_ok=True)
    suffix = ".zip" if url.lower().endswith(".zip") else ".csv"
    path = raw_dir / f"{dataset_id}_Official_GroundTruth{suffix}"
    receipt = download_small(url, path, max_bytes=20 * 1024**2)
    receipt["dataset_id"] = dataset_id
    gt_receipts.append(receipt)
    if receipt["status"] not in {"DOWNLOADED", "ALREADY_PRESENT"}:
        continue
    try:
        gt = load_csv_any(path)
        image_col = find_column(gt, ["image", "image_id", "image_name"], contains=("image",))
        if image_col is None:
            image_col = gt.columns[0]
        melanoma_col = find_column(gt, ["MEL", "melanoma"], contains=("melanoma",))
        nv_col = find_column(gt, ["NV", "nevus"], contains=("nevus",))
        sk_col = find_column(gt, ["seborrheic_keratosis", "SK"], contains=("seborrheic",))
        if melanoma_col is None:
            raise RuntimeError("melanoma column missing")
        image_id = gt[image_col].astype(str).str.replace(r"\.(jpg|jpeg|png)$", "", regex=True, case=False)
        melanoma = pd.to_numeric(gt[melanoma_col], errors="coerce")
        if nv_col is not None:
            nevus = pd.to_numeric(gt[nv_col], errors="coerce")
            keep = melanoma.eq(1) | nevus.eq(1)
            label = np.where(melanoma.eq(1), 1, np.where(nevus.eq(1), 0, np.nan))
        elif sk_col is not None:
            sk = pd.to_numeric(gt[sk_col], errors="coerce")
            keep = melanoma.eq(1) | (melanoma.eq(0) & sk.eq(0))
            label = np.where(melanoma.eq(1), 1, np.where(melanoma.eq(0) & sk.eq(0), 0, np.nan))
        else:
            raise RuntimeError("nevus or seborrheic-keratosis column missing")
        frame = pd.DataFrame({
            "dataset": dataset_id,
            "modality": "dermoscopy",
            "task": "melanoma_vs_melanocytic_nevus",
            "image_id": image_id,
            "group_id": dataset_id + "::IMAGE::" + image_id,
            "label": label,
            "target_role": "SECONDARY_RELEASE_TARGET",
            "provider": dataset_id,
            "source_url": "https://isic-archive.s3.amazonaws.com/images/" + image_id + ".jpg",
        })
        frame = frame[keep & pd.notna(frame["label"])].copy()
        frame["label"] = frame["label"].astype(int)
        release_candidate_frames.append(frame)
    except Exception as exc:
        gt_receipts[-1]["parse_error"] = f"{type(exc).__name__}: {exc}"

write_csv(P1 / "StageT2-L_Official_GroundTruth_Receipts_v0.1.csv", pd.DataFrame(gt_receipts))

# Official ISIC 2020 metadata and provider partitions.
provider_candidate_frames = []
isic2020_audit = {"status": "NOT_ATTEMPTED", "error": "", "metadata_rows": 0, "provider_field": ""}
cli_root = ACQ_ROOT / "ISIC2020_OFFICIAL_COLLECTION70" / "00_Raw_Inbox"
cli_root.mkdir(parents=True, exist_ok=True)
cli_metadata_path = cli_root / "ISIC_Collection70_CLI_Metadata.csv"
gt2020_path = cli_root / "ISIC_2020_Training_GroundTruth_v2.csv"
duplicate2020_path = cli_root / "ISIC_2020_Training_Duplicates.csv"

try:
    if not cli_metadata_path.exists():
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "isic-cli==12.5.2"],
            check=True, timeout=600
        )
        before = set(cli_root.glob("*.csv"))
        subprocess.run(
            ["isic", "metadata", "download", "--collections", "70"],
            cwd=cli_root, check=True, timeout=1200
        )
        after = [path for path in cli_root.glob("*.csv") if path not in before]
        candidates = after or list(cli_root.glob("*.csv"))
        candidates = [path for path in candidates if "groundtruth" not in path.name.lower() and "duplicate" not in path.name.lower()]
        if candidates:
            chosen = max(candidates, key=lambda path: path.stat().st_size)
            if chosen != cli_metadata_path:
                shutil.move(str(chosen), cli_metadata_path)
    gt2020_receipt = download_small(
        "https://isic-archive.s3.amazonaws.com/challenges/2020/ISIC_2020_Training_GroundTruth_v2.csv",
        gt2020_path, max_bytes=10 * 1024**2
    )
    duplicate_receipt = download_small(
        "https://isic-archive.s3.amazonaws.com/challenges/2020/ISIC_2020_Training_Duplicates.csv",
        duplicate2020_path, max_bytes=10 * 1024**2
    )
    if cli_metadata_path.exists() and gt2020_path.exists():
        metadata = pd.read_csv(cli_metadata_path)
        labels2020 = pd.read_csv(gt2020_path)
        metadata.columns = [normalise_column(column) for column in metadata.columns]
        labels2020.columns = [normalise_column(column) for column in labels2020.columns]
        meta_id = find_column(metadata, ["isic_id", "image_name", "image_id"], contains=("isic_id", "image"))
        label_id = find_column(labels2020, ["image_name", "isic_id", "image_id"], contains=("image",))
        patient_col = find_column(labels2020, ["patient_id"], contains=("patient",))
        lesion_col = find_column(labels2020, ["lesion_id"], contains=("lesion",))
        diagnosis_col = find_column(labels2020, ["diagnosis"], contains=("diagnosis",))
        target_col = find_column(labels2020, ["target"], contains=("target",))
        benign_col = find_column(labels2020, ["benign_malignant"], contains=("benign",))
        assert meta_id and label_id and patient_col and diagnosis_col and target_col
        metadata[meta_id] = metadata[meta_id].astype(str)
        labels2020[label_id] = labels2020[label_id].astype(str)
        merged = labels2020.merge(metadata, left_on=label_id, right_on=meta_id, how="left", suffixes=("", "_meta"))
        provider_columns = [
            column for column in merged.columns
            if any(token in normalise_column(column) for token in [
                "attribution", "institution", "contributor", "copyright", "source"
            ])
        ]
        if provider_columns:
            provider_text = merged[provider_columns].fillna("").astype(str).agg(" || ".join, axis=1)
        else:
            provider_text = pd.Series([""] * len(merged), index=merged.index)

        def canonical_provider(text):
            text = str(text).lower()
            if "barcelona" in text or "hospital clínic" in text or "hospital clinic" in text:
                return "ISIC2020_BARCELONA"
            if "vienna" in text or "vidir" in text:
                return "ISIC2020_VIENNA"
            if "queensland" in text:
                return "ISIC2020_QUEENSLAND"
            if "melanoma institute australia" in text or "sydney melanoma" in text:
                return "ISIC2020_MIA"
            if "memorial sloan" in text or "msk" in text:
                return "ISIC2020_MSK"
            if "athens" in text or "syngros" in text:
                return "ISIC2020_ATHENS"
            return ""
        merged["provider_target"] = provider_text.map(canonical_provider)
        diagnosis = merged[diagnosis_col].astype(str).str.lower()
        target = pd.to_numeric(merged[target_col], errors="coerce")
        is_mel = target.eq(1) | diagnosis.str.contains("melanoma", na=False)
        is_nevus = diagnosis.str.contains("nevus|naevi|melanocytic nev", regex=True, na=False)
        merged["binary_label"] = np.where(is_mel, 1, np.where(is_nevus, 0, np.nan))
        for provider in ["ISIC2020_BARCELONA","ISIC2020_VIENNA","ISIC2020_QUEENSLAND","ISIC2020_MIA"]:
            part = merged[merged["provider_target"].eq(provider) & pd.notna(merged["binary_label"])].copy()
            if len(part) == 0:
                continue
            part["patient_key"] = part[patient_col].astype(str)
            part = part[part["patient_key"].ne("") & part["patient_key"].ne("nan")]
            group_class = part.groupby("patient_key")["binary_label"].nunique()
            valid_patients = group_class[group_class == 1].index
            part = part[part["patient_key"].isin(valid_patients)].copy()
            part["stable"] = [stable_key(provider, p, i) for p, i in zip(part["patient_key"], part[label_id])]
            part = part.sort_values("stable").drop_duplicates("patient_key", keep="first")
            frame = pd.DataFrame({
                "dataset": provider,
                "modality": "dermoscopy",
                "task": "melanoma_vs_melanocytic_nevus",
                "image_id": part[label_id].astype(str),
                "group_id": provider + "::PATIENT::" + part["patient_key"].astype(str),
                "label": part["binary_label"].astype(int),
                "target_role": "PRIMARY_PROVIDER_TARGET",
                "provider": provider,
                "source_url": "https://isic-archive.s3.amazonaws.com/images/" + part[label_id].astype(str) + ".jpg",
            })
            provider_candidate_frames.append(frame)
        isic2020_audit.update({
            "status": "METADATA_PARSED",
            "metadata_rows": int(len(metadata)),
            "ground_truth_rows": int(len(labels2020)),
            "provider_field": " || ".join(provider_columns),
            "provider_counts": merged["provider_target"].value_counts().to_dict(),
        })
    else:
        isic2020_audit["status"] = "HOLD_OFFICIAL_METADATA_ROUTE_FAILED"
except Exception as exc:
    isic2020_audit["status"] = "HOLD_OFFICIAL_METADATA_ROUTE_FAILED"
    isic2020_audit["error"] = f"{type(exc).__name__}: {exc}"

write_json(P1 / "StageT2-L_ISIC2020_Provider_Metadata_Audit_v0.1.json", isic2020_audit)

all_candidate_frames = release_candidate_frames + provider_candidate_frames
candidate_raw = pd.concat(all_candidate_frames, ignore_index=True) if all_candidate_frames else pd.DataFrame(
    columns=["dataset","modality","task","image_id","group_id","label","target_role","provider","source_url"]
)

# Deterministic case-control cap within each target.
def cap_target(frame):
    rows = []
    for label, maximum in [(1, MAX_POSITIVE), (0, MAX_NEGATIVE)]:
        part = frame[frame["label"].eq(label)].copy()
        part["stable"] = [stable_key(row.dataset, row.group_id, row.image_id) for row in part.itertuples()]
        rows.append(part.sort_values("stable").head(maximum))
    return pd.concat(rows, ignore_index=True) if rows else frame.iloc[0:0].copy()

candidate_capped = pd.concat(
    [cap_target(frame) for _, frame in candidate_raw.groupby("dataset")],
    ignore_index=True
) if len(candidate_raw) else candidate_raw.copy()

# Existing identifier and fingerprint firewall.
existing_manifests = pd.concat(
    [pd.read_csv(HAM_MANIFEST), pd.read_csv(MSK_MANIFEST), pd.read_csv(UDA_MANIFEST)],
    ignore_index=True
)
existing_ids = set(existing_manifests["image_id"].astype(str))
existing_lesions = set()
if "unit_id" in existing_manifests:
    existing_lesions = set(existing_manifests["unit_id"].astype(str).str.extract(r"::LESION::(.+)$")[0].dropna())
milk = pd.read_csv(MILK_MANIFEST)
existing_ids.update(milk["image_id"].astype(str))
if "group_id" in milk:
    existing_lesions.update(milk["group_id"].astype(str).str.replace(r"^.*::LESION::", "", regex=True))

official_duplicate_ids = set()
if duplicate2020_path.exists():
    try:
        dup = pd.read_csv(duplicate2020_path)
        for column in dup.columns:
            official_duplicate_ids.update(dup[column].dropna().astype(str))
    except Exception:
        pass

candidate_capped["adjudication_status"] = "PENDING_DOWNLOAD"
candidate_capped.loc[candidate_capped["image_id"].astype(str).isin(existing_ids), "adjudication_status"] = "EXCLUDE_EXISTING_IMAGE_ID"
candidate_capped.loc[candidate_capped["image_id"].astype(str).isin(official_duplicate_ids), "adjudication_status"] = "EXCLUDE_OFFICIAL_DUPLICATE_LIST"

def download_image_record(record):
    dataset = record["dataset"]
    image_id = record["image_id"]
    destination = ACQ_ROOT / dataset / "01_Selected_Images" / f"{image_id}.jpg"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 1024:
        return {"row_index": record["row_index"], "download_status": "ALREADY_PRESENT",
                "image_path": str(destination), "bytes": destination.stat().st_size, "error": ""}
    for attempt in range(3):
        try:
            response = SESSION.get(record["source_url"], timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            data = response.content
            if len(data) < 1024 or "text/html" in response.headers.get("content-type", "").lower():
                raise RuntimeError("not a valid image response")
            destination.write_bytes(data)
            return {"row_index": record["row_index"], "download_status": "DOWNLOADED",
                    "image_path": str(destination), "bytes": len(data), "error": ""}
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            time.sleep(1.5 * (attempt + 1))
    return {"row_index": record["row_index"], "download_status": "FAILED",
            "image_path": "", "bytes": 0, "error": error}

to_download = candidate_capped[candidate_capped["adjudication_status"].eq("PENDING_DOWNLOAD")].reset_index().rename(columns={"index":"row_index"})
download_rows = []
if len(to_download):
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = [executor.submit(download_image_record, row._asdict()) for row in to_download.itertuples(index=False)]
        for count, future in enumerate(as_completed(futures), 1):
            download_rows.append(future.result())
            if count % 100 == 0:
                print("Downloaded selected images:", count, "/", len(to_download))
downloads = pd.DataFrame(download_rows)
for column in ["download_status","image_path","bytes","error"]:
    if column not in candidate_capped.columns:
        candidate_capped[column] = ""
if len(downloads):
    indexed_downloads = downloads.set_index("row_index")
    for column in ["download_status","image_path","bytes","error"]:
        candidate_capped.loc[indexed_downloads.index.astype(int), column] = indexed_downloads[column]
candidate_capped["download_status"] = candidate_capped["download_status"].fillna("")
candidate_capped.loc[
    candidate_capped["adjudication_status"].eq("PENDING_DOWNLOAD") &
    ~candidate_capped["download_status"].isin(["DOWNLOADED","ALREADY_PRESENT"]),
    "adjudication_status"
] = "HOLD_DOWNLOAD_FAILED"

def image_fingerprint(path):
    data = Path(path).read_bytes()
    with Image.open(io.BytesIO(data)) as image0:
        image = ImageOps.exif_transpose(image0).convert("RGB")
        width, height = image.size
        rgb = np.asarray(image, dtype=np.uint8)
        header = json.dumps({"width":width,"height":height,"mode":"RGB"}, sort_keys=True, separators=(",",":")).encode() + b"\0"
        pixel_sha = sha_bytes(header + rgb.tobytes(order="C"))
        gray = np.asarray(image.convert("L").resize((32,32), Image.Resampling.LANCZOS), dtype=np.float32)
        low = dctn(gray, type=2, norm="ortho")[:8,:8]
        threshold = float(np.median(low.flatten()[1:]))
        bits = (low.flatten() > threshold).astype(np.uint8)
        phash = 0
        for bit in bits:
            phash = (phash << 1) | int(bit)
        thumb = np.asarray(image.convert("L").resize((32,32), Image.Resampling.BILINEAR), dtype=np.uint8)
    return {
        "raw_image_sha256": sha_bytes(data),
        "pixel_sha256": pixel_sha,
        "pixel_width": width,
        "pixel_height": height,
        "phash64": f"{phash:016x}",
        "thumb32_b64": base64.b64encode(thumb.tobytes()).decode("ascii"),
    }

fp_rows = []
for index, row in candidate_capped[
    candidate_capped["adjudication_status"].eq("PENDING_DOWNLOAD") &
    candidate_capped["download_status"].isin(["DOWNLOADED","ALREADY_PRESENT"])
].iterrows():
    try:
        fp_rows.append({"row_index": index, **image_fingerprint(row["image_path"]), "fingerprint_error": ""})
    except Exception as exc:
        fp_rows.append({"row_index": index, "fingerprint_error": f"{type(exc).__name__}: {exc}"})
fp = pd.DataFrame(fp_rows)
for column in ["raw_image_sha256","pixel_sha256","pixel_width","pixel_height","phash64","thumb32_b64","fingerprint_error"]:
    if column not in candidate_capped.columns:
        candidate_capped[column] = np.nan
if len(fp):
    fp = fp.set_index("row_index")
    for column in ["raw_image_sha256","pixel_sha256","pixel_width","pixel_height","phash64","thumb32_b64","fingerprint_error"]:
        if column in fp.columns:
            candidate_capped.loc[fp.index, column] = fp[column]
candidate_capped.loc[
    candidate_capped["adjudication_status"].eq("PENDING_DOWNLOAD") &
    candidate_capped["pixel_sha256"].isna(),
    "adjudication_status"
] = "HOLD_FINGERPRINT_FAILED"

reference_frames = []
if REFERENCE_CACHE.exists():
    reference_frames.append(pd.read_csv(REFERENCE_CACHE))
milk_reference = milk[milk["dedup_status"].eq("KEEP_UNIQUE")].copy()
milk_reference = milk_reference.rename(columns={"dataset":"reference_dataset","image_id":"reference_image_id"})
reference_frames.append(milk_reference)
reference = pd.concat(reference_frames, ignore_index=True, sort=False) if reference_frames else pd.DataFrame()
if "dataset" in reference.columns and "reference_dataset" not in reference.columns:
    reference["reference_dataset"] = reference["dataset"]
if "image_id" in reference.columns and "reference_image_id" not in reference.columns:
    reference["reference_image_id"] = reference["image_id"]
if "status" in reference.columns:
    reference = reference[reference["status"].astype(str).isin(["FINGERPRINTED","KEEP_UNIQUE",""]) | reference["status"].isna()]
reference_pixel = set(reference["pixel_sha256"].dropna().astype(str)) if "pixel_sha256" in reference else set()

def normalise_phash(value):
    text = str(value).strip().lower()
    if re.fullmatch(r"[0-9a-f]{1,16}", text):
        return text.zfill(16)
    return None

reference_phash = [
    value for value in (normalise_phash(v) for v in reference.get("phash64", pd.Series(dtype=str)).dropna())
    if value is not None
]

def phash_distance(left, right):
    left = normalise_phash(left)
    right = normalise_phash(right)
    if left is None or right is None:
        return 65
    return (int(left,16) ^ int(right,16)).bit_count()

candidate_capped.loc[
    candidate_capped["adjudication_status"].eq("PENDING_DOWNLOAD") &
    candidate_capped["pixel_sha256"].astype(str).isin(reference_pixel),
    "adjudication_status"
] = "EXCLUDE_CROSS_ROSTER_EXACT_PIXEL_DUPLICATE"

# Preregistered target priority: provider targets, then release targets by year.
priority = [
    "ISIC2020_BARCELONA","ISIC2020_VIENNA","ISIC2020_QUEENSLAND","ISIC2020_MIA",
    "ISIC2017_VALIDATION","ISIC2017_TEST","ISIC2018_TEST","ISIC2019_TEST"
]
accepted_pixel = set(reference_pixel)
accepted_phash = list(reference_phash)
dedup_rows = []
for dataset_id in priority:
    indices = candidate_capped.index[
        candidate_capped["dataset"].eq(dataset_id) &
        candidate_capped["adjudication_status"].eq("PENDING_DOWNLOAD")
    ].tolist()
    for index in indices:
        row = candidate_capped.loc[index]
        pixel_sha = str(row["pixel_sha256"])
        phash = str(row["phash64"])
        if pixel_sha in accepted_pixel:
            status = "EXCLUDE_CROSS_TARGET_EXACT_PIXEL_DUPLICATE"
        else:
            near_distance = min((phash_distance(phash, value) for value in accepted_phash), default=65)
            status = "HOLD_CROSS_ROSTER_PHASH_NEAR_COPY" if near_distance <= PHASH_MAX_DISTANCE else "KEEP_UNIQUE"
        candidate_capped.loc[index, "adjudication_status"] = status
        dedup_rows.append({"dataset":dataset_id,"image_id":row["image_id"],"status":status})
        if status == "KEEP_UNIQUE":
            accepted_pixel.add(pixel_sha)
            accepted_phash.append(phash)

write_csv(P3 / "StageT2-L_Selected_Image_Download_And_Dedup_Manifest_v0.1.csv", candidate_capped)
write_csv(P3 / "StageT2-L_Cross_Roster_Dedup_Audit_v0.1.csv", pd.DataFrame(dedup_rows))

# Freeze eligible target roster and grouped split.
target_frames = []
target_status_rows = []
for dataset_id, frame in candidate_capped.groupby("dataset"):
    retained = frame[frame["adjudication_status"].eq("KEEP_UNIQUE")].copy()
    counts = retained.groupby("label")["group_id"].nunique().to_dict()
    eligible = (
        retained["group_id"].nunique() >= MIN_TOTAL_GROUPS
        and counts.get(1,0) >= MIN_POSITIVE_GROUPS
        and counts.get(0,0) >= MIN_NEGATIVE_GROUPS
    )
    target_status_rows.append({
        "dataset": dataset_id,
        "target_role": frame["target_role"].iloc[0],
        "candidate_rows": len(frame),
        "retained_images": len(retained),
        "retained_groups": retained["group_id"].nunique(),
        "negative_groups": counts.get(0,0),
        "positive_groups": counts.get(1,0),
        "five_budget_score_ready": bool(eligible),
    })
    if not eligible:
        continue
    groups = retained[["group_id","label"]].drop_duplicates()
    train_groups, validation_groups = train_test_split(
        groups, test_size=0.2, random_state=SEED, stratify=groups["label"]
    )
    partition = {
        **{group:"development" for group in train_groups["group_id"]},
        **{group:"validation" for group in validation_groups["group_id"]},
    }
    retained["partition"] = retained["group_id"].map(partition)
    retained["unit_id"] = retained["dataset"] + "::IMAGE::" + retained["image_id"].astype(str)
    retained["source_locator"] = retained["image_path"]
    retained["extension_status"] = "T2L_FROZEN_SCORE_READY"
    target_frames.append(retained[[
        "dataset","modality","task","image_id","unit_id","group_id","label",
        "source_locator","partition","raw_image_sha256","target_role","extension_status"
    ]])

target_status = pd.DataFrame(target_status_rows)
target_roster = pd.concat(target_frames, ignore_index=True) if target_frames else pd.DataFrame(
    columns=["dataset","modality","task","image_id","unit_id","group_id","label",
             "source_locator","partition","raw_image_sha256","target_role","extension_status"]
)
write_csv(P2 / "StageT2-L_Target_Readiness_Map_v0.1.csv", target_status)
write_csv(P2 / "StageT2-L_Frozen_Score_Ready_Target_Roster_v0.1.csv", target_roster)

# Automatic audit-only acquisitions.
audit_specs = [
    ("RFMID2_0", "https://zenodo.org/records/7505822/files/RFMiD2_0.zip?download=1", 500 * 1024**2),
    ("TB_CXR_PAKISTAN_2026", "https://api.data.mendeley.com/datasets/8j2g3csprk/zip/file_downloaded?version=3", 6 * 1024**3),
]
audit_rows = []
for dataset_id, url, cap in audit_specs:
    inbox = ACQ_ROOT / dataset_id / "00_Raw_Inbox"
    extracted = ACQ_ROOT / dataset_id / "01_Extracted"
    inbox.mkdir(parents=True, exist_ok=True)
    archive = inbox / f"{dataset_id}_official.zip"
    receipt = download_small(url, archive, max_bytes=cap)
    status = receipt["status"]
    error = receipt["error"]
    image_count = 0
    metadata_files = 0
    grouping_candidates = []
    if status in {"DOWNLOADED","ALREADY_PRESENT"}:
        try:
            if not extracted.exists() or not any(extracted.rglob("*")):
                safe_extract_zip(archive, extracted)
            image_count = sum(1 for path in extracted.rglob("*") if path.is_file() and path.suffix.lower() in {".jpg",".jpeg",".png",".bmp",".tif",".tiff"})
            tables = [path for path in extracted.rglob("*") if path.is_file() and path.suffix.lower() in {".csv",".xlsx",".xls"}]
            metadata_files = len(tables)
            for table in tables[:20]:
                try:
                    frame = pd.read_csv(table, nrows=5) if table.suffix.lower()==".csv" else pd.read_excel(table, nrows=5)
                    grouping_candidates.extend([column for column in frame.columns if any(token in normalise_column(column) for token in ["patient","subject","case","visit","exam"])])
                except Exception:
                    pass
            status = "ACQUIRED_STRUCTURAL_AUDIT_ONLY"
        except Exception as exc:
            status = "HOLD_EXTRACTION_OR_SCHEMA"
            error = f"{type(exc).__name__}: {exc}"
    audit_rows.append({
        "dataset_id":dataset_id,"status":status,"image_count":image_count,
        "metadata_files":metadata_files,
        "grouping_candidate_columns":" || ".join(sorted(set(map(str,grouping_candidates)))),
        "archive_sha256":sha_file(archive) if archive.exists() else "",
        "error":error,
    })
audit_only = pd.DataFrame(audit_rows)
write_csv(P1 / "StageT2-L_Automatic_Audit_Only_Acquisitions_v0.1.csv", audit_only)

display(target_status)
display(audit_only)
print("Score-ready targets:", sorted(target_roster["dataset"].unique()) if len(target_roster) else [])



# Frozen CPU embeddings and dermoscopy source-axis scoring
assert len(target_roster) > 0, "No score-ready targets were acquired; inspect readiness and manual queue."

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torchvision.models import resnet50, ResNet50_Weights
from tqdm.auto import tqdm

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
torch.set_num_threads(max(1, min(8, os.cpu_count() or 2)))
DEVICE = torch.device("cpu")
WEIGHTS = ResNet50_Weights.IMAGENET1K_V2
TRANSFORM = WEIGHTS.transforms(antialias=True)
MODEL = resnet50(weights=WEIGHTS)
MODEL.fc = nn.Identity()
MODEL.eval().to(DEVICE)

def model_state_sha256(model):
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        digest.update(name.encode() + b"\0")
        array = tensor.detach().cpu().contiguous().numpy()
        digest.update(str(array.dtype).encode() + b"\0")
        digest.update(np.asarray(array.shape, dtype=np.int64).tobytes())
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()

MODEL_STATE_SHA256 = model_state_sha256(MODEL)
assert MODEL_STATE_SHA256 == EXPECTED_MODEL_STATE_SHA256

class TargetImageDataset(Dataset):
    def __init__(self, frame):
        self.frame = frame.reset_index(drop=True)
    def __len__(self):
        return len(self.frame)
    def __getitem__(self, index):
        row = self.frame.iloc[index]
        path = Path(row["source_locator"])
        data = path.read_bytes()
        if str(row.get("raw_image_sha256","")).strip():
            assert sha_bytes(data) == str(row["raw_image_sha256"])
        with Image.open(io.BytesIO(data)) as image0:
            image = ImageOps.exif_transpose(image0).convert("RGB")
            tensor = TRANSFORM(image)
        return tensor, index

DERM_SOURCES = ["HAM10000","ISIC_MSK1","ISIC_UDA1"]
SOURCE_BY_MODALITY = {"dermoscopy": DERM_SOURCES}
derm_summary = pd.read_csv(DERM_SUMMARY).set_index("source")
SOURCE_VALIDATION_AUC = {source: float(derm_summary.loc[source,"validation_auc"]) for source in DERM_SOURCES}

embedding_rows, score_rows, axis_schema_rows = [], [], []
for dataset_id, frame in target_roster.groupby("dataset", sort=True):
    frame = frame.sort_values("image_id").reset_index(drop=True)
    embedding_path = P4 / f"{dataset_id}_Frozen_ResNet50_V2_Embeddings_v0.1.npy"
    ids_path = P4 / f"{dataset_id}_Embedding_Image_IDs_v0.1.npy"
    expected_ids = np.asarray(frame["image_id"].astype(str).tolist(), dtype=np.str_)
    if embedding_path.exists() and ids_path.exists():
        assert np.array_equal(np.load(ids_path, allow_pickle=False).astype(str), expected_ids)
        embeddings = np.load(embedding_path, mmap_mode="r", allow_pickle=False)
    else:
        loader = DataLoader(TargetImageDataset(frame), batch_size=24, shuffle=False, num_workers=2, pin_memory=False)
        chunks = []
        for images, indices in tqdm(loader, desc=f"Embedding {dataset_id}"):
            with torch.inference_mode():
                features = F.normalize(MODEL(images.to(DEVICE)), p=2, dim=1)
            chunks.append(features.cpu().numpy().astype(np.float32))
        array = np.concatenate(chunks, axis=0)
        assert array.shape == (len(frame),2048)
        np.save(embedding_path, array, allow_pickle=False)
        np.save(ids_path, expected_ids, allow_pickle=False)
        embeddings = np.load(embedding_path, mmap_mode="r", allow_pickle=False)
    norms = np.linalg.norm(np.asarray(embeddings), axis=1)
    assert np.max(np.abs(norms-1.0)) < 2e-5

    for source in DERM_SOURCES:
        axis_path = AXIS_PATHS[source]
        with np.load(axis_path, allow_pickle=False) as axis:
            keys = set(axis.files)
            identity_key = "dataset_id" if "dataset_id" in keys else "source"
            assert str(axis[identity_key]) == source
            if {"coefficient_raw","intercept_raw"}.issubset(keys):
                coefficient_key, intercept_key = "coefficient_raw","intercept_raw"
                schema = "STAGE11_STYLE"
            elif {"raw_coefficient","raw_intercept"}.issubset(keys):
                coefficient_key, intercept_key = "raw_coefficient","raw_intercept"
                schema = "STAGE8_STYLE"
            else:
                raise KeyError(f"No documented parameter pair in {axis_path.name}: {sorted(keys)}")
            coefficient = np.asarray(axis[coefficient_key], dtype=np.float64)
            intercept = float(axis[intercept_key])
            assert coefficient.shape == (2048,) and np.isfinite(coefficient).all() and np.isfinite(intercept)
            if "model_state_sha256" in keys:
                assert str(axis["model_state_sha256"]) == MODEL_STATE_SHA256
        axis_schema_rows.append({
            "source":source,"axis_filename":axis_path.name,"axis_sha256":sha_file(axis_path),
            "identity_key":identity_key,"coefficient_key":coefficient_key,
            "intercept_key":intercept_key,"schema":schema,
        })
        logits = np.asarray(embeddings,dtype=np.float64) @ coefficient + intercept
        for row, logit in zip(frame.itertuples(), logits):
            score_rows.append({
                "target":dataset_id,"target_role":row.target_role,"modality":"dermoscopy",
                "source":source,"edge_id":f"{source}__TO__{dataset_id}",
                "image_id":row.image_id,"unit_id":row.unit_id,"group_id":row.group_id,
                "label":int(row.label),"partition":row.partition,
                "logit":float(logit),"probability":float(1/(1+np.exp(-np.clip(logit,-60,60)))),
                "source_validation_auc":SOURCE_VALIDATION_AUC[source],
            })
    embedding_rows.append({
        "target":dataset_id,"images":len(frame),"dimension":2048,
        "model_state_sha256":MODEL_STATE_SHA256,
        "embedding_sha256":sha_file(embedding_path),"image_ids_sha256":sha_file(ids_path),
        "maximum_l2_norm_error":float(np.max(np.abs(norms-1.0))),"device":"cpu",
    })
    gc.collect()

source_scores = pd.DataFrame(score_rows)
embedding_manifest = pd.DataFrame(embedding_rows)
axis_schema_audit = pd.DataFrame(axis_schema_rows).drop_duplicates()
truth_rows = []
for (target,target_role,source,edge_id), frame in source_scores.groupby(["target","target_role","source","edge_id"]):
    truth_rows.append({
        "target":target,"target_role":target_role,"modality":"dermoscopy",
        "source":source,"edge_id":edge_id,
        "true_auc":float(roc_auc_score(frame["label"],frame["logit"])),
        "source_validation_auc":float(frame["source_validation_auc"].iloc[0]),
        "units":frame["unit_id"].nunique(),"groups":frame["group_id"].nunique(),
    })
truth_table = pd.DataFrame(truth_rows)
write_csv(P4 / "StageT2-L_Frozen_Embedding_Manifest_v0.1.csv", embedding_manifest)
write_csv(P4 / "StageT2-L_Frozen_Axis_Schema_Audit_v0.1.csv", axis_schema_audit)
write_csv(P4 / "StageT2-L_Frozen_Source_Score_Predictions_v0.1.csv", source_scores)
write_csv(P4 / "StageT2-L_Expansion_Edge_Truth_Table_v0.1.csv", truth_table)
display(embedding_manifest)
display(truth_table)



# Freeze the 15-target expected-budget model before constructing any new target budget truth.
old_reps = pd.concat([pd.read_csv(T2D_REPS), pd.read_csv(T2KR_REPS)], ignore_index=True, sort=False)
assert old_reps["target"].nunique() == 15
assert set(BUDGETS).issubset(set(old_reps["budget"].unique()))

def target_budget_meta_from_replicates(reps):
    curve = (
        reps[reps["method"].eq("amw_ddet")]
        .groupby(["target","modality","budget"],as_index=False)
        .agg(median_error=("absolute_error","median"))
    )
    budget_rows = []
    for (target,modality), frame in curve.groupby(["target","modality"]):
        found = None
        for budget in BUDGETS:
            row = frame[frame["budget"].eq(budget)]
            if len(row) and float(row["median_error"].iloc[0]) <= 0.04:
                found = budget
                break
        operational = found if found is not None else 256
        budget_rows.append({
            "target":target,"modality":modality,
            "minimum_budget_operational":operational,
            "log2_minimum_budget":math.log2(operational),
            "right_censored_above_128":found is None,
        })
    budget_table = pd.DataFrame(budget_rows)
    legal = ["random_direct","random_logistic_plugin","random_joint_gmm","active_direct","amw_ddet"]
    b8 = reps[reps["budget"].eq(8)]
    pivot = b8.pivot_table(
        index=["target","modality","replicate","edge_id"],
        columns="method",values="estimate_auc"
    ).reset_index()
    pivot["cross_method_sd"] = pivot.reindex(columns=legal).std(axis=1)
    pilot_rep = (
        pivot.groupby(["target","modality","replicate"],as_index=False)
        .agg(pilot_disagreement=("cross_method_sd","mean"))
    )
    pilot_target = (
        pilot_rep.groupby(["target","modality"],as_index=False)
        .agg(pilot_disagreement_index=("pilot_disagreement","median"))
    )
    return budget_table.merge(pilot_target,on=["target","modality"])

old15_data = target_budget_meta_from_replicates(old_reps)
assert old15_data["target"].nunique() == 15

ALPHAS = [0.1,1.0,10.0,100.0]
alpha_rows = []
for alpha in ALPHAS:
    errors = []
    for held in old15_data["target"]:
        train = old15_data[old15_data["target"].ne(held)]
        test = old15_data[old15_data["target"].eq(held)]
        model = Pipeline([
            ("impute",SimpleImputer(strategy="median")),
            ("scale",StandardScaler()),
            ("ridge",Ridge(alpha=alpha)),
        ])
        model.fit(train[["pilot_disagreement_index"]],train["log2_minimum_budget"])
        errors.append(abs(float(model.predict(test[["pilot_disagreement_index"]])[0]) - float(test["log2_minimum_budget"].iloc[0])))
    alpha_rows.append({"alpha":alpha,"loto_mae":float(np.mean(errors))})
alpha_audit = pd.DataFrame(alpha_rows).sort_values(["loto_mae","alpha"])
selected_alpha = float(alpha_audit.iloc[0]["alpha"])
old15_model = Pipeline([
    ("impute",SimpleImputer(strategy="median")),
    ("scale",StandardScaler()),
    ("ridge",Ridge(alpha=selected_alpha)),
])
old15_model.fit(old15_data[["pilot_disagreement_index"]],old15_data["log2_minimum_budget"])

old15_record = {
    "stage":"StageT2-L",
    "event":"OLD15_EXPECTED_BUDGET_MODEL_FREEZE_BEFORE_NEW_TARGET_TRUTH",
    "training_targets":sorted(old15_data["target"].tolist()),
    "feature":"target_median_budget8_cross_method_disagreement",
    "selected_alpha":selected_alpha,
    "imputer_statistics":[float(v) for v in old15_model.named_steps["impute"].statistics_],
    "scaler_mean":[float(v) for v in old15_model.named_steps["scale"].mean_],
    "scaler_scale":[float(v) for v in old15_model.named_steps["scale"].scale_],
    "ridge_coefficient":[float(v) for v in np.ravel(old15_model.named_steps["ridge"].coef_)],
    "ridge_intercept":float(np.ravel(np.asarray(old15_model.named_steps["ridge"].intercept_))[0]),
    "new_target_multibudget_truth_observed":False,
    "single_pilot_deployment_authorised":False,
    "frozen_utc":now(),
}
old15_record["freeze_sha256"] = sha_json(old15_record)
write_json(P6 / "StageT2-L_Old15_Expected_Budget_Model_Freeze_v0.1.json", old15_record)
write_csv(P6 / "StageT2-L_Old15_Budget_Model_Alpha_Audit_v0.1.csv", alpha_audit)
write_csv(P6 / "StageT2-L_Old15_Budget_Training_Data_v0.1.csv", old15_data)
print("Old 15-target expected-budget model frozen before new truth:", old15_record["freeze_sha256"])



# Complete five-budget inherited AMW/RA-CB extension experiment Run complete five-budget parent and RA-CB extension experiments
def prep_target_table(frame):
    unit = "unit_id"
    meta = frame.groupby([unit], as_index=False).agg(
        label=("label", "first"),
        group_id=("group_id", "first"),
        modality=("modality", "first"),
    )
    wide = frame.pivot_table(index=unit, columns="source", values="logit", aggfunc="mean").reset_index()
    return wide.merge(meta, on=unit, validate="one_to_one")

def weighted_auc(scores, probabilities):
    scores = np.asarray(scores, float)
    p = np.asarray(probabilities, float)
    n = 1 - p
    denominator = p.sum() * n.sum()
    if denominator <= 0:
        return np.nan
    order = np.argsort(scores, kind="mergesort")
    scores, p, n = scores[order], p[order], n[order]
    numerator = 0.0
    negatives_before = 0.0
    starts = np.r_[0, np.flatnonzero(np.diff(scores)) + 1]
    ends = np.r_[starts[1:], len(scores)]
    for start, end in zip(starts, ends):
        p_here = p[start:end].sum()
        n_here = n[start:end].sum()
        numerator += p_here * (negatives_before + 0.5 * n_here)
        negatives_before += n_here
    return float(numerator / denominator)

def choose_groups(n, budget, rng, design, active):
    if not active:
        return rng.choice(n, budget, replace=False)
    anchors = max(2, int(np.ceil(budget * 0.25)))
    selected = list(rng.choice(n, anchors, replace=False))
    used = np.zeros(n, bool)
    used[selected] = True
    inverse = np.linalg.inv(np.eye(design.shape[1]) + design[selected].T @ design[selected])
    while len(selected) < budget:
        gains = np.einsum("ij,jk,ik->i", design, inverse, design)
        gains[used] = -np.inf
        index = int(np.argmax(gains + rng.normal(0, 1e-12, n)))
        vector = design[index]
        product = inverse @ vector
        inverse -= np.outer(product, product) / (1 + vector @ product)
        selected.append(index)
        used[index] = True
    return np.asarray(selected)

def crossfitted_logistic_probabilities(x, y, groups, witness):
    if len(np.unique(y[witness])) < 2:
        return None
    model = LogisticRegression(C=RIDGE_C, solver="lbfgs", max_iter=2000).fit(x[witness], y[witness])
    probabilities = model.predict_proba(x)[:, 1]
    local = np.flatnonzero(witness)
    local_groups = groups[witness]
    folds = min(5, len(pd.unique(local_groups)))
    if folds >= 2:
        splitter = GroupKFold(folds)
        for fit_idx, score_idx in splitter.split(x[witness], y[witness], local_groups):
            if len(np.unique(y[witness][fit_idx])) < 2:
                continue
            fold_model = LogisticRegression(C=RIDGE_C, solver="lbfgs", max_iter=2000).fit(
                x[witness][fit_idx], y[witness][fit_idx]
            )
            probabilities[local[score_idx]] = fold_model.predict_proba(x[witness][score_idx])[:, 1]
    return probabilities

def gaussian_logpdf(x, mean, covariance):
    chol = np.linalg.cholesky(covariance)
    z = solve_triangular(chol, (x - mean).T, lower=True).T
    return -0.5 * (
        x.shape[1] * np.log(2 * np.pi)
        + 2 * np.log(np.diag(chol)).sum()
        + (z * z).sum(1)
    )

def semisupervised_gmm(x, y, witness, max_iter=200, tol=1e-7):
    dimension = x.shape[1]
    means = np.vstack([x[witness & (y == klass)].mean(0) for klass in (0, 1)])
    covariance = np.cov(x.T) if dimension > 1 else np.array([[np.var(x[:, 0])]])
    covariance = np.atleast_2d(covariance) + np.eye(dimension) * 1e-3
    prior = np.clip(np.mean(y[witness]), 0.05, 0.95)
    responsibilities = np.zeros((len(x), 2))
    for _ in range(max_iter):
        old = np.r_[means.ravel(), covariance.ravel(), prior]
        log_joint = np.c_[
            np.log(1 - prior) + gaussian_logpdf(x, means[0], covariance),
            np.log(prior) + gaussian_logpdf(x, means[1], covariance),
        ]
        responsibilities[:] = np.exp(log_joint - logsumexp(log_joint, axis=1, keepdims=True))
        responsibilities[witness] = np.c_[1 - y[witness], y[witness]]
        weights = responsibilities.sum(0)
        means = responsibilities.T @ x / weights[:, None]
        covariance = np.zeros((dimension, dimension))
        for klass in (0, 1):
            centered = x - means[klass]
            covariance += (centered * responsibilities[:, [klass]]).T @ centered
        covariance /= len(x)
        covariance = 0.8 * covariance + 0.2 * np.diag(np.diag(covariance)) + np.eye(dimension) * 1e-3
        prior = np.clip(weights[1] / len(x), 0.01, 0.99)
        new = np.r_[means.ravel(), covariance.ravel(), prior]
        if np.max(np.abs(new - old)) < tol:
            break
    log_joint = np.c_[
        np.log(1 - prior) + gaussian_logpdf(x, means[0], covariance),
        np.log(prior) + gaussian_logpdf(x, means[1], covariance),
    ]
    return np.exp(log_joint - logsumexp(log_joint, axis=1, keepdims=True))[:, 1]

def balance_features(group_x):
    return np.column_stack([group_x, group_x ** 2])

def entropy_balance_weights(sample_phi, target_phi, ridge=BALANCE_RIDGE, clip=WEIGHT_CLIP):
    sample_phi = np.asarray(sample_phi, float)
    target_phi = np.asarray(target_phi, float)
    target_mean = target_phi.mean(0)
    center = sample_phi.mean(0)
    scale = sample_phi.std(0) + 1e-6
    a = (sample_phi - center) / scale
    mu = (target_mean - center) / scale

    def objective(lam):
        raw = np.clip(a @ lam, -30, 30)
        shifted = raw - raw.max()
        weight = np.exp(shifted)
        weight /= weight.sum()
        value = np.log(np.exp(raw).mean()) - mu @ lam + 0.5 * ridge * np.sum(lam ** 2)
        gradient = weight @ a - mu + ridge * lam
        return value, gradient

    fit = minimize(lambda value: objective(value), np.zeros(a.shape[1]), jac=True, method="L-BFGS-B")
    valid = bool(fit.success and np.all(np.isfinite(fit.x)))
    lam = fit.x if valid else np.zeros(a.shape[1])
    raw = np.clip(a @ lam, -30, 30)
    raw -= raw.max()
    weight = np.exp(raw)
    weight /= weight.mean()
    weight = np.clip(weight, clip[0], clip[1])
    weighted_mean = np.average(sample_phi, axis=0, weights=weight)
    raw_scale = target_phi.std(0) + 1e-6
    standardized_residual = float(np.max(np.abs((weighted_mean - target_mean) / raw_scale)))
    ess = float(weight.sum() ** 2 / np.sum(weight ** 2))
    return weight, {
        "optimizer_success": valid,
        "weight_min": float(weight.min()),
        "weight_max": float(weight.max()),
        "weight_ess": ess,
        "balance_residual_max_standardized": standardized_residual,
    }

def candidate_posterior(x, y, groups, unique_groups, selected_indices, balanced):
    selected_groups = unique_groups[selected_indices]
    witness = np.isin(groups, selected_groups)
    if len(np.unique(y[witness])) < 2:
        return None, None
    group_x = np.asarray([x[groups == group].mean(0) for group in unique_groups])
    phi = balance_features(group_x)
    group_lookup = {group: index for index, group in enumerate(unique_groups)}
    if balanced:
        full_weight, diagnostics = entropy_balance_weights(phi[selected_indices], phi)
        lookup = dict(zip(selected_groups, full_weight))
        unit_weight = np.asarray([lookup[group] for group in groups[witness]], float)
    else:
        diagnostics = {
            "optimizer_success": True, "weight_min": 1.0, "weight_max": 1.0,
            "weight_ess": float(len(selected_groups)),
            "balance_residual_max_standardized": np.nan,
        }
        unit_weight = np.ones(witness.sum())

    model = LogisticRegression(C=RIDGE_C, solver="lbfgs", max_iter=3000).fit(
        x[witness], y[witness], sample_weight=unit_weight
    )
    eta = model.predict_proba(x)[:, 1]
    local = np.flatnonzero(witness)
    local_groups = groups[witness]
    folds = min(5, len(pd.unique(local_groups)))
    if folds >= 2:
        splitter = GroupKFold(folds)
        for train, test in splitter.split(x[witness], y[witness], local_groups):
            if len(np.unique(y[witness][train])) < 2:
                continue
            train_groups = np.asarray(pd.unique(local_groups[train]))
            if balanced:
                indices = np.asarray([group_lookup[group] for group in train_groups])
                fold_weight, _ = entropy_balance_weights(phi[indices], phi)
                lookup = dict(zip(train_groups, fold_weight))
                train_weight = np.asarray([lookup[group] for group in local_groups[train]], float)
            else:
                train_weight = np.ones(len(train))
            fold = LogisticRegression(C=RIDGE_C, solver="lbfgs", max_iter=3000).fit(
                x[witness][train], y[witness][train], sample_weight=train_weight
            )
            eta[local[test]] = fold.predict_proba(x[witness][test])[:, 1]
    return eta, diagnostics

def group_brier(y, eta, groups, selected_groups):
    return np.asarray([
        np.mean((y[groups == group] - eta[groups == group]) ** 2)
        for group in selected_groups
    ], float)

target_tables = {}
for target, score_frame in source_scores.groupby("target"):
    wide = prep_target_table(score_frame)
    sources = SOURCE_BY_MODALITY[wide["modality"].iloc[0]]
    assert all(source in wide.columns for source in sources)
    target_tables[target] = (wide, sources)

rows, diagnostic_rows, skip_rows = [], [], []
for target, (data, sources) in target_tables.items():
    raw = data[sources].to_numpy(float)
    x = (raw - raw.mean(0)) / (raw.std(0) + 1e-9)
    y = data["label"].to_numpy(int)
    groups = data["group_id"].astype(str).to_numpy()
    unique_groups = np.asarray(pd.unique(groups))
    group_x = np.asarray([x[groups == group].mean(0) for group in unique_groups])
    design = np.c_[np.ones(len(unique_groups)), group_x]
    truths = {source: roc_auc_score(y, x[:, index]) for index, source in enumerate(sources)}

    for budget in BUDGETS:
        if len(unique_groups) < budget:
            for replicate in range(N_REPLICATES):
                skip_rows.append({
                    "target": target, "budget": budget, "replicate": replicate,
                    "stage": "all", "reason": "insufficient_independent_groups",
                })
            continue

        for replicate in range(N_REPLICATES):
            base_seed = SEED + replicate * 1009 + budget * 17 + sum(map(ord, target))
            rng_random = np.random.default_rng(base_seed)
            rng_active = np.random.default_rng(base_seed + 1)
            selected_random = choose_groups(len(unique_groups), budget, rng_random, design, False)
            selected_active = choose_groups(len(unique_groups), budget, rng_active, design, True)
            witness_random = np.isin(groups, unique_groups[selected_random])
            witness_active = np.isin(groups, unique_groups[selected_active])

            if len(np.unique(y[witness_random])) < 2 or len(np.unique(y[witness_active])) < 2:
                skip_rows.append({
                    "target": target, "budget": budget, "replicate": replicate,
                    "stage": "acquisition", "reason": "single_witness_class",
                })
                continue

            eta_random = crossfitted_logistic_probabilities(x, y, groups, witness_random)
            eta_active = crossfitted_logistic_probabilities(x, y, groups, witness_active)
            try:
                eta_gmm = semisupervised_gmm(x, y, witness_random)
            except np.linalg.LinAlgError:
                eta_gmm = None

            eta_u, diag_u = candidate_posterior(
                x, y, groups, unique_groups, selected_active, False
            )
            eta_cb, diag_cb = candidate_posterior(
                x, y, groups, unique_groups, selected_active, True
            )
            selected_groups = unique_groups[selected_active]
            cb_admissible = bool(
                eta_cb is not None and diag_cb["optimizer_success"]
                and diag_cb["weight_ess"] >= MIN_BALANCE_ESS
            )
            loss_u = group_brier(y, eta_u, groups, selected_groups)
            loss_cb = (
                group_brier(y, eta_cb, groups, selected_groups)
                if eta_cb is not None else np.full(len(selected_groups), np.inf)
            )
            select_cb = bool(cb_admissible and loss_cb.mean() < loss_u.mean())
            eta_ra = eta_cb if select_cb else eta_u

            diagnostic_rows.append({
                "target": target, "modality": data["modality"].iloc[0],
                "budget": budget, "replicate": replicate,
                "selected_candidate": "AMW-CB2" if select_cb else "AMW-U",
                "balance_selected": select_cb,
                "cb_admissible": cb_admissible,
                "cv_brier_amw_u": float(loss_u.mean()),
                "cv_brier_amw_cb2": float(loss_cb.mean()),
                **diag_cb,
            })

            method_eta = {
                "random_logistic_plugin": eta_random,
                "random_joint_gmm": eta_gmm,
                "amw_ddet": eta_active,
                "amw_u_recomputed": eta_u,
                "amw_cb2": eta_cb,
                "ra_cb_amw_ddet": eta_ra,
            }

            for index, source in enumerate(sources):
                common = {
                    "target": target,
                    "modality": data["modality"].iloc[0],
                    "source": source,
                    "edge_id": f"{source}__TO__{target}",
                    "budget": budget,
                    "replicate": replicate,
                    "true_auc": float(truths[source]),
                    "source_validation_auc": SOURCE_VALIDATION_AUC[source],
                    "retention_threshold": SOURCE_VALIDATION_AUC[source] - 0.15,
                    "independent_groups": len(unique_groups),
                }
                direct_random = roc_auc_score(y[witness_random], x[witness_random, index])
                direct_active = roc_auc_score(y[witness_active], x[witness_active, index])
                rows.append({
                    **common, "method": "random_direct", "estimate_auc": direct_random,
                    "witness_units": int(witness_random.sum()),
                    "witness_prevalence": float(y[witness_random].mean()),
                    "balance_selected": False,
                })
                rows.append({
                    **common, "method": "active_direct", "estimate_auc": direct_active,
                    "witness_units": int(witness_active.sum()),
                    "witness_prevalence": float(y[witness_active].mean()),
                    "balance_selected": False,
                })
                for method, eta in method_eta.items():
                    if eta is None:
                        continue
                    witness = witness_random if method.startswith("random_") else witness_active
                    rows.append({
                        **common, "method": method,
                        "estimate_auc": weighted_auc(x[:, index], eta),
                        "witness_units": int(witness.sum()),
                        "witness_prevalence": float(y[witness].mean()),
                        "balance_selected": select_cb if method == "ra_cb_amw_ddet" else False,
                    })
        print("Completed:", target, "budget", budget)

extension_results = pd.DataFrame(rows)
extension_results["absolute_error"] = (
    extension_results["estimate_auc"] - extension_results["true_auc"]
).abs()
extension_diagnostics = pd.DataFrame(diagnostic_rows)
extension_skips = pd.DataFrame(skip_rows)

write_csv(P5 / "StageT2-L_All_MultiBudget_Extension_Replicates_v0.1.csv", extension_results)
write_csv(P5 / "StageT2-L_RA_CB_Selector_And_Balance_Diagnostics_v0.1.csv", extension_diagnostics)
write_csv(P5 / "StageT2-L_Skipped_Extension_Replicates_v0.1.csv", extension_skips)

print("Extension result rows:", len(extension_results))
print("Skipped rows:", len(extension_skips))



target_role_map = target_roster[["dataset","target_role"]].drop_duplicates().set_index("dataset")["target_role"].to_dict()
extension_results["target_role"] = extension_results["target"].map(target_role_map)
write_csv(P5 / "StageT2-L_All_MultiBudget_Extension_Replicates_v0.1.csv", extension_results)



# Stage T2-L target-regime evaluation and completion.
legal_methods = ["random_direct","random_logistic_plugin","random_joint_gmm","active_direct","amw_ddet"]

budget_rows = []
for method in ["amw_ddet","ra_cb_amw_ddet"]:
    curve = (
        extension_results[extension_results["method"].eq(method)]
        .groupby(["target","target_role","modality","budget"],as_index=False)
        .agg(median_error=("absolute_error","median"))
    )
    for (target,target_role,modality), frame in curve.groupby(["target","target_role","modality"]):
        found = None
        for budget in BUDGETS:
            row = frame[frame["budget"].eq(budget)]
            if len(row) and float(row["median_error"].iloc[0]) <= 0.04:
                found = budget
                break
        operational = found if found is not None else 256
        budget_rows.append({
            "target":target,"target_role":target_role,"modality":modality,"method":method,
            "minimum_budget_operational":operational,
            "log2_minimum_budget":math.log2(operational),
            "right_censored_above_128":found is None,
        })
extension_budget = pd.DataFrame(budget_rows)

amw_curve = (
    extension_results[extension_results["method"].eq("amw_ddet")]
    .groupby(["target","target_role","budget"],as_index=False)
    .agg(median_error=("absolute_error","median"))
)
regime_rows = []
for (target,target_role), frame in amw_curve.groupby(["target","target_role"]):
    frame = frame.sort_values("budget")
    errors = dict(zip(frame["budget"],frame["median_error"]))
    e8 = float(errors.get(8,np.nan))
    e128 = float(errors.get(128,np.nan))
    rho = float(spearmanr(frame["budget"],frame["median_error"]).statistic) if frame["median_error"].nunique() > 1 else 0.0
    ratio = e128/e8 if np.isfinite(e8) and e8 > 0 else np.nan
    if np.isfinite(e128) and e128 <= 0.04:
        regime = "EVIDENCE_LIMITED_OPERATIONAL"
    elif np.isfinite(e128) and e128 > 0.04 and ((np.isfinite(ratio) and ratio >= 0.8) or rho >= -0.3):
        regime = "MODEL_LIMITED_WITHIN_FROZEN_AUDIT_FAMILY"
    else:
        regime = "EVIDENCE_DEMANDING_RIGHT_CENSORED"
    regime_rows.append({
        "target":target,"target_role":target_role,
        "median_error_b8":e8,"median_error_b128":e128,
        "b128_to_b8_ratio":ratio,"budget_error_spearman":rho,
        "frozen_regime":regime,
    })
regime_table = pd.DataFrame(regime_rows)

# New target budget-8 signature and old-15 frozen-model prediction.
new_b8 = extension_results[extension_results["budget"].eq(8)]
new_pivot = new_b8.pivot_table(
    index=["target","target_role","modality","replicate","edge_id"],
    columns="method",values="estimate_auc"
).reset_index()
new_pivot["cross_method_sd"] = new_pivot.reindex(columns=legal_methods).std(axis=1)
new_pilot = (
    new_pivot.groupby(["target","target_role","modality","replicate"],as_index=False)
    .agg(pilot_disagreement=("cross_method_sd","mean"))
    .groupby(["target","target_role","modality"],as_index=False)
    .agg(
        pilot_disagreement_index=("pilot_disagreement","median"),
        pilot_disagreement_iqr=("pilot_disagreement",lambda x:float(np.quantile(x,.75)-np.quantile(x,.25))),
    )
)
amw_budget = extension_budget[extension_budget["method"].eq("amw_ddet")].copy()
new_meta = amw_budget.merge(new_pilot,on=["target","target_role","modality"])
new_meta["old15_prediction_log2_budget"] = old15_model.predict(new_meta[["pilot_disagreement_index"]])
new_meta["old15_absolute_log2_error"] = (new_meta["old15_prediction_log2_budget"]-new_meta["log2_minimum_budget"]).abs()
new_meta["old15_baseline_log2_budget"] = float(old15_data["log2_minimum_budget"].median())
new_meta["old15_baseline_absolute_error"] = (new_meta["old15_baseline_log2_budget"]-new_meta["log2_minimum_budget"]).abs()
old15_extension_gain = (
    1 - new_meta["old15_absolute_log2_error"].mean()/new_meta["old15_baseline_absolute_error"].mean()
    if new_meta["old15_baseline_absolute_error"].mean() > 0 else np.nan
)

expanded_data = pd.concat([
    old15_data[["target","modality","minimum_budget_operational","log2_minimum_budget","pilot_disagreement_index"]].assign(cohort="previous15"),
    new_meta[["target","modality","minimum_budget_operational","log2_minimum_budget","pilot_disagreement_index"]].assign(cohort="stageT2L"),
],ignore_index=True)

expanded_predictions = []
for held in expanded_data["target"]:
    train = expanded_data[expanded_data["target"].ne(held)]
    test = expanded_data[expanded_data["target"].eq(held)]
    alpha_scores = []
    for alpha in ALPHAS:
        inner_errors = []
        for inner_held in train["target"]:
            inner_train = train[train["target"].ne(inner_held)]
            inner_test = train[train["target"].eq(inner_held)]
            model = Pipeline([
                ("impute",SimpleImputer(strategy="median")),
                ("scale",StandardScaler()),
                ("ridge",Ridge(alpha=alpha)),
            ])
            model.fit(inner_train[["pilot_disagreement_index"]],inner_train["log2_minimum_budget"])
            prediction = float(model.predict(inner_test[["pilot_disagreement_index"]])[0])
            inner_errors.append(abs(prediction-float(inner_test["log2_minimum_budget"].iloc[0])))
        alpha_scores.append((float(np.mean(inner_errors)),alpha))
    chosen = min(alpha_scores)[1]
    model = Pipeline([
        ("impute",SimpleImputer(strategy="median")),
        ("scale",StandardScaler()),
        ("ridge",Ridge(alpha=chosen)),
    ])
    model.fit(train[["pilot_disagreement_index"]],train["log2_minimum_budget"])
    expanded_predictions.append({
        "target":held,"cohort":test["cohort"].iloc[0],
        "actual":float(test["log2_minimum_budget"].iloc[0]),
        "prediction":float(model.predict(test[["pilot_disagreement_index"]])[0]),
        "baseline":float(train["log2_minimum_budget"].median()),
        "selected_alpha":chosen,
    })
expanded_predictions = pd.DataFrame(expanded_predictions)
expanded_rho = float(spearmanr(expanded_predictions["actual"],expanded_predictions["prediction"]).statistic)
expanded_mae = float(mean_absolute_error(expanded_predictions["actual"],expanded_predictions["prediction"]))
expanded_baseline_mae = float(mean_absolute_error(expanded_predictions["actual"],expanded_predictions["baseline"]))
expanded_gain = 1-expanded_mae/expanded_baseline_mae if expanded_baseline_mae>0 else np.nan

ra32 = (
    extension_results[
        extension_results["method"].eq("ra_cb_amw_ddet") &
        extension_results["budget"].eq(32)
    ]
    .groupby(["target","target_role","source","edge_id"],as_index=False)
    .agg(
        true_auc=("true_auc","first"),
        predicted_auc_b32=("estimate_auc","median"),
        median_absolute_error_b32=("absolute_error","median"),
    )
)
target_mae = (
    ra32.groupby(["target","target_role"],as_index=False)
    .agg(target_median_mae_b32=("median_absolute_error_b32","median"))
)

write_csv(P6 / "StageT2-L_Operational_Budgets_v0.1.csv",extension_budget)
write_csv(P6 / "StageT2-L_Frozen_Regime_Assignments_v0.1.csv",regime_table)
write_csv(P6 / "StageT2-L_New_Target_Old15_Budget_Model_Evaluation_v0.1.csv",new_meta)
write_csv(P6 / "StageT2-L_Expanded_Target_Budget_Meta_Data_v0.1.csv",expanded_data)
write_csv(P6 / "StageT2-L_Expanded_LOTO_Budget_Predictions_v0.1.csv",expanded_predictions)
write_csv(P6 / "StageT2-L_RA_CB_B32_Edge_Summary_v0.1.csv",ra32)
write_csv(P6 / "StageT2-L_RA_CB_B32_Target_Summary_v0.1.csv",target_mae)

score_ready_count = int(target_roster["dataset"].nunique())
primary_count = int(target_status.loc[
    target_status["five_budget_score_ready"] &
    target_status["target_role"].eq("PRIMARY_PROVIDER_TARGET"),"dataset"
].nunique())
secondary_count = int(target_status.loc[
    target_status["five_budget_score_ready"] &
    target_status["target_role"].eq("SECONDARY_RELEASE_TARGET"),"dataset"
].nunique())
gt_success = int(pd.DataFrame(gt_receipts)["status"].isin(["DOWNLOADED","ALREADY_PRESENT"]).sum())
regimes_complete = bool(len(regime_table)==score_ready_count and regime_table["frozen_regime"].notna().all())

gates = pd.DataFrame([
    {"gate":"G1_parent_and_document_integrity","passed":True,"observed":"T2-KR/T2-H/T3-PF and companion hashes exact"},
    {"gate":"G2_manual_drop_locations","passed":len(manual_queue)==len(MANUAL_DATASETS),"observed":len(manual_queue)},
    {"gate":"G3_official_release_ground_truth","passed":gt_success>=2,"observed":f"{gt_success}/{len(OFFICIAL_GT)} routes"},
    {"gate":"G4_isic2020_provider_metadata","passed":isic2020_audit["status"]=="METADATA_PARSED","observed":isic2020_audit},
    {"gate":"G5_cross_roster_dedup_applied","passed":len(candidate_capped)>0,"observed":candidate_capped["adjudication_status"].value_counts().to_dict()},
    {"gate":"G6_at_least_two_new_targets_scored","passed":score_ready_count>=2,"observed":sorted(target_roster["dataset"].unique())},
    {"gate":"G7_four_or_more_new_targets_scored","passed":score_ready_count>=4,"observed":score_ready_count},
    {"gate":"G8_frozen_source_axes_exact","passed":True,"observed":sorted(AXIS_PATHS)},
    {"gate":"G9_multibudget_completeness","passed":set(BUDGETS).issubset(set(extension_results["budget"].unique())),"observed":len(extension_results)},
    {"gate":"G10_old15_frozen_before_new_truth","passed":old15_record["new_target_multibudget_truth_observed"] is False,"observed":old15_record["freeze_sha256"]},
    {"gate":"G11_regime_assignment_complete","passed":regimes_complete,"observed":regime_table["frozen_regime"].value_counts().to_dict()},
    {"gate":"G12_audit_only_routes_documented","passed":len(audit_only)==2,"observed":audit_only.to_dict("records")},
    {"gate":"G13_single_pilot_failure_preserved","passed":t2h["single_pilot_deployment_authorised"] is False,"observed":False},
    {"gate":"G14_locked_blind_firewall","passed":True,"observed":"no locked-blind path or outcome accessed"},
    {"gate":"G15_stage12_false","passed":t3pf["stage12_authorised"] is False,"observed":False},
])
core = gates[gates["gate"].isin([
    "G1_parent_and_document_integrity","G2_manual_drop_locations",
    "G3_official_release_ground_truth","G5_cross_roster_dedup_applied",
    "G6_at_least_two_new_targets_scored","G8_frozen_source_axes_exact",
    "G9_multibudget_completeness","G10_old15_frozen_before_new_truth",
    "G11_regime_assignment_complete","G12_audit_only_routes_documented",
    "G13_single_pilot_failure_preserved","G14_locked_blind_firewall","G15_stage12_false"
])]
core_pass = bool(core["passed"].all())
if not core_pass:
    decision = "TERMINATE_T2L_CORE_INTEGRITY_ACQUISITION_SCORING_OR_FIREWALL_FAILURE"
elif score_ready_count >= 4 and primary_count >= 2:
    decision = "SEAL_INDEPENDENT_REGIME_EXPANSION_AUTHORISE_EXPANDED_META_REGIME_ANALYSIS_ONLY"
elif score_ready_count >= 4:
    decision = "SEAL_RELEASE_DOMAIN_REGIME_EXPANSION_RETAIN_PROVIDER_INDEPENDENCE_LIMITATION"
elif score_ready_count >= 2:
    decision = "SEAL_PARTIAL_TARGET_REGIME_EXPANSION_CONTINUE_MANUAL_AND_PROVIDER_ACQUISITION"
else:
    decision = "HOLD_TARGET_REGIME_EXPANSION_CONTINUE_OFFICIAL_ACQUISITION"

write_csv(P6 / "StageT2-L_Frozen_Gates_v0.1.csv",gates)

plt.figure(figsize=(8,6))
for cohort,frame in expanded_predictions.groupby("cohort"):
    plt.scatter(frame["actual"],frame["prediction"],label=cohort)
lo=min(expanded_predictions["actual"].min(),expanded_predictions["prediction"].min())
hi=max(expanded_predictions["actual"].max(),expanded_predictions["prediction"].max())
plt.plot([lo,hi],[lo,hi],linestyle="--")
plt.xlabel("Actual log2 operational budget")
plt.ylabel("LOTO predicted log2 budget")
plt.title(f"Expanded expected-budget relation: rho={expanded_rho:.3f}")
plt.legend()
plt.tight_layout()
plt.savefig(P7/"StageT2-L_Expanded_Budget_Meta_Analysis_v0.1.png",dpi=220)
plt.show()

plt.figure(figsize=(10,6))
for target,frame in amw_curve.groupby("target"):
    plt.plot(frame["budget"],frame["median_error"],marker="o",label=target)
plt.axhline(0.04,linestyle="--")
plt.xscale("log",base=2)
plt.xlabel("Witness-group budget")
plt.ylabel("Median absolute AUC error")
plt.title("Stage T2-L frozen AMW-DDET evidence curves")
plt.legend(fontsize=7)
plt.tight_layout()
plt.savefig(P7/"StageT2-L_Evidence_Curves_v0.1.png",dpi=220)
plt.show()

completion = {
    "stage":"StageT2-L",
    "decision":decision,
    "parent_t2kr_final_record_sha256":EXPECTED_PARENT["t2kr"],
    "protocol_seal_sha256":protocol["protocol_seal_sha256"],
    "score_ready_targets":sorted(target_roster["dataset"].unique().tolist()),
    "score_ready_target_count":score_ready_count,
    "primary_provider_targets":primary_count,
    "secondary_release_targets":secondary_count,
    "expansion_edges":int(truth_table["edge_id"].nunique()),
    "multibudget_result_rows":int(len(extension_results)),
    "regime_counts":regime_table["frozen_regime"].value_counts().to_dict(),
    "old15_extension_relative_mae_improvement":float(old15_extension_gain),
    "expanded_loto_spearman":expanded_rho,
    "expanded_loto_relative_mae_improvement":float(expanded_gain),
    "manual_queue_count":len(manual_queue),
    "single_pilot_deployment_authorised":False,
    "locked_blind_assets_touched":False,
    "locked_blind_outcomes_accessed":False,
    "stage12_authorised":False,
    "gates_passed":int(gates["passed"].sum()),
    "gates_total":int(len(gates)),
    "completed_utc":now(),
}
completion["final_record_sha256"] = sha_json(completion)
write_json(P7/"StageT2-L_Complete_v0.1.json",completion)

summary = f"""# Stage T2-L result summary v0.1

- Decision: `{decision}`
- Score-ready targets: `{completion['score_ready_targets']}`
- Primary provider targets: `{primary_count}`
- Secondary release targets: `{secondary_count}`
- Expansion edges: `{completion['expansion_edges']}`
- Multi-budget rows: `{completion['multibudget_result_rows']}`
- Regime counts: `{completion['regime_counts']}`
- Old-15 extension relative MAE improvement: `{old15_extension_gain:.2%}`
- Expanded LOTO Spearman: `{expanded_rho:.6f}`
- Expanded LOTO relative MAE improvement: `{expanded_gain:.2%}`
- Gates: `{completion['gates_passed']}/{completion['gates_total']}`
- Single-pilot deployment authorised: `False`
- Locked blind assets touched: `False`
- Stage 12 authorised: `False`
- Final record SHA256: `{completion['final_record_sha256']}`
"""
write_text(P7/"StageT2-L_Result_Summary_v0.1.md",summary)

display(regime_table)
display(new_meta)
display(target_mae)
display(gates)
print("\n========== STAGE T2-L COMPLETE ==========")
print("Decision:",decision)
print("Score-ready targets:",completion["score_ready_targets"])
print("Regime counts:",completion["regime_counts"])
print("Expanded LOTO Spearman:",expanded_rho)
print("Manual queue:",P1/"StageT2-L_Manual_Download_Queue_v0.1.csv")
print("Single-pilot deployment authorised:",False)
print("Locked blind assets touched:",False)
print("Stage 12 authorised:",False)
print("Final record SHA256:",completion["final_record_sha256"])
