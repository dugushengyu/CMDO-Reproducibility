
# Stage T3-A locked-blind sentinel execution: immutable setup and activation seal
import base64, gc, hashlib, io, itertools, json, math, os, random, re, shutil, subprocess, sys, tarfile, time, unicodedata, warnings, zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import matplotlib.pyplot as plt
from PIL import Image, ImageOps
from scipy.fft import dctn
from scipy.linalg import solve_triangular
from scipy.optimize import minimize
from scipy.signal import hilbert
from scipy.special import logsumexp
from scipy.stats import norm, spearmanr
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from tqdm.auto import tqdm

warnings.filterwarnings("ignore")

try:
    from IPython.display import display
except Exception:
    display = print

try:
    from google.colab import drive
    drive.mount("/content/drive")
    IN_COLAB = True
except Exception:
    IN_COLAB = False

if IN_COLAB:
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q",
         "cryptography>=42", "py7zr>=0.21", "rarfile>=4.2", "h5py>=3.10"],
        check=True,
    )

from cryptography.fernet import Fernet
from scipy.io import loadmat

DEFAULT_ROOT = Path("/content/drive/MyDrive/Cross-Modal_Diagnostic_Observability") if IN_COLAB else Path.cwd()
PROJECT_ROOT = Path(os.environ.get("CMDO_PROJECT_ROOT", str(DEFAULT_ROOT)))
CODE_ROOT = PROJECT_ROOT / "05_Code" / "Cross_Modal"
STUDY_ROOT = PROJECT_ROOT / "04_Study_Design" / "StageT3-A_Locked_Blind_Sentinel_Execution_v0.1"
MAP_ROOT = PROJECT_ROOT / "02_Dataset_Map" / "StageT3-A_Locked_Blind_Target_Registry_v1.1"
ACQ_ROOT = PROJECT_ROOT / "00_Data_Acquisition" / "Cross_Modal_Locked_Blind_Sentinel_v0.1"
COMMIT_ROOT = PROJECT_ROOT / "06_Data_Records" / "Cross_Modal" / "StageT3-A_v0.1"
RUNTIME_ROOT = Path("/content/cmdo_runtime/StageT3-A") if IN_COLAB else Path("/tmp/cmdo_runtime/StageT3-A")
LOCAL_RECORDS = RUNTIME_ROOT / "records"
ASSET_WORK = RUNTIME_ROOT / "assets"

for path in [CODE_ROOT, STUDY_ROOT, MAP_ROOT, ACQ_ROOT, COMMIT_ROOT]:
    path.mkdir(parents=True, exist_ok=True)
if RUNTIME_ROOT.exists():
    shutil.rmtree(RUNTIME_ROOT)
for path in [LOCAL_RECORDS, ASSET_WORK]:
    path.mkdir(parents=True, exist_ok=True)

P0 = LOCAL_RECORDS / "00_Protocol_And_Activation"
P1 = LOCAL_RECORDS / "01_Official_Assets_And_Outcome_Firewall"
P2 = LOCAL_RECORDS / "02_Grouping_Dedup_And_Frozen_Roster"
P3 = LOCAL_RECORDS / "03_Frozen_Embeddings_Source_Scores_And_Witness_Manifests"
P4 = LOCAL_RECORDS / "04_Budget8_Evidence_Forecast_Seal"
P5 = LOCAL_RECORDS / "05_Budget32_Primary_Prediction_Seal"
P6 = LOCAL_RECORDS / "06_Remaining_Waves_And_Final_Outcome_Unseal"
P7 = LOCAL_RECORDS / "07_Scenario_Classification_And_Results"
for path in [P0, P1, P2, P3, P4, P5, P6, P7]:
    path.mkdir(parents=True, exist_ok=True)

SEED = 20260723
BUDGETS = [8, 16, 32, 64, 128]
N_REPLICATES = 100
PRIMARY_BUDGET = 32
THRESHOLD = 0.04
RIDGE_C = 3.0
BALANCE_RIDGE = 0.1
WEIGHT_CLIP = (0.1, 10.0)
MIN_BALANCE_ESS = 8.0
CONFORMAL_RADIUS = 0.16229985434323593
PHASH_MAX_DISTANCE = 4
MODEL_STATE_SHA256 = "3f2c393680172fd552aae83bd2f0e3c389457e7d13499e3490c2a314f5642051"

EXPECTED = {
    "t3pf_activation": "4397cee7798f684159ed77aa5e1edd7b7ae0a24378047d6c89b37ef9ef738a52",
    "t2mn_final": "cc11dfea1df0cf8d28af218fe9d437de3306ed02437b2712744b35e64e3f98b2",
    "t2m_model": "c7d37bdf03dd07f312aa87308c349927df5d0b4326618d2131a91f9272b49c13",
    "t2m_support": "6bffbc80619f640da8cf1b97b926fb67d325fe89db1f9fc06669cbfdd86f5830",
    "t2h_final": "27d4c7afe711ba66ea44d11f3ef173820e11ef1eba7a44530446a3e5444aa99f",
    "t2f_final": "a7dc616c2cf46c772bcd452a7f5804c77f67eae553214217f7525ce59ea6c7e9",
    "t2mn_bundle_file": "28da430abc6d7a7581ef79844228c68ed1c97685d4a39c42b136c3b32092abb6",
    "t2m_bootstrap_file": "d23365f3c8a2c77d7881c1a00e1913b47245b78fb652e225b2c0886e0cd2a819",
}

AXIS_SHA = {
    "BUSI_WHU_2025_V3": "7d09dd72c43d9dc43d574e8d6dea90edd7e5fbb845103d80d824add9bce11963",
    "BUS_BRA_2024": "73ad923e912177b56ff21cab081b0b84e4ae30a37f0f7bea0b1db5c518c774e7",
    "BUS_UCLM_2025_V3": "3fb6eedf6d08dac78d24549e40c8ffcae835c1c37fcf0b50d90f64150a6e7bdc",
    "RODRIGUES_BUI_2017": "6f09b1002f3b1928aa2f957e86887213c58e330b5c6eefe616f9a0dad2a6f592",
    "HAM10000": "0988518fcfbcb3436f43fbdff37b61395b8ba8b3715fccbc295f67cd0ab3dcad",
    "ISIC_MSK1": "5011be88de7e877d836f0518540c53dd3f6a34c57225b729e22285ff1cfcd9d2",
    "ISIC_UDA1": "316857360dd3a4f3c9f19f811cc58a4c17c1da1372319cbcc9382e7eca76b670",
}

SOURCE_VALIDATION_AUC = {
    "BUSI_WHU_2025_V3": 0.801520,
    "BUS_BRA_2024": 0.721986,
    "BUS_UCLM_2025_V3": 0.665962,
    "RODRIGUES_BUI_2017": 0.990926,
    "HAM10000": 0.813744,
    "ISIC_MSK1": 0.701161,
    "ISIC_UDA1": 0.720698,
}

SOURCE_BY_MODALITY = {
    "breast_ultrasound": [
        "BUSI_WHU_2025_V3", "BUS_BRA_2024",
        "BUS_UCLM_2025_V3", "RODRIGUES_BUI_2017",
    ],
    "dermoscopy": ["HAM10000", "ISIC_MSK1", "ISIC_UDA1"],
}

AXIS_FILENAMES = {
    "BUSI_WHU_2025_V3": "BUSI_WHU_2025_V3_Frozen_Development_Source_Axis_v0.1.npz",
    "BUS_BRA_2024": "BUS_BRA_2024_Frozen_Development_Source_Axis_v0.1.npz",
    "BUS_UCLM_2025_V3": "BUS_UCLM_2025_V3_Frozen_Development_Source_Axis_v0.1.npz",
    "RODRIGUES_BUI_2017": "RODRIGUES_BUI_2017_Frozen_Development_Source_Axis_v0.1.npz",
    "HAM10000": "HAM10000_Frozen_Source_Axis_v0.1.npz",
    "ISIC_MSK1": "ISIC_MSK1_Frozen_Source_Axis_v0.1.npz",
    "ISIC_UDA1": "ISIC_UDA1_Frozen_Source_Axis_v0.1.npz",
}

EMBEDDED_PREREG = '# Stage T3-A locked-blind sentinel scenario classification and execution preregistration v1.1\n\n**Frozen:** 23 July 2026  \n**Status:** final activation-and-execution candidate, outcome-free  \n**Parent Stage T3-PF activation record:** `4397cee7798f684159ed77aa5e1edd7b7ae0a24378047d6c89b37ef9ef738a52`  \n**Parent Stage T2-MN final record:** `cc11dfea1df0cf8d28af218fe9d437de3306ed02437b2712744b35e64e3f98b2`  \n**Stage T2-M model freeze:** `c7d37bdf03dd07f312aa87308c349927df5d0b4326618d2131a91f9272b49c13`  \n**Stage T2-M support freeze:** `6bffbc80619f640da8cf1b97b926fb67d325fe89db1f9fc06669cbfdd86f5830`  \n**Single-pilot deployment:** prohibited  \n**Stage 12:** false\n\n## 1. Purpose\n\nPerform the single permitted locked-blind T3-A sentinel execution without changing the frozen representation, source axes, witness budget, selector, balance method, conformal radius, support rule or evidence-demand model.\n\nThis execution can produce one of three prospectively frozen interpretations:\n\n- **Scenario A — sentinel dual survival:** the performance estimator and the target-expected evidence-demand secondary both survive;\n- **Scenario B — performance-only survival:** the performance estimator survives but the evidence-demand secondary does not;\n- **Scenario C — performance failure:** the locked-blind performance primary fails.\n\nT3-A remains a three-target sentinel/kill test. Scenario A does not by itself constitute the six-target, three-modality T3-B confirmatory claim.\n\n## 2. Locked targets\n\nNo target may be replaced after this freeze:\n\n1. `BUSI_CAIRO_2019`;\n2. `OASBUD_2017`;\n3. `DERM7PT_2019`.\n\nAn unavailable target remains in the ledger with its outcome-free cause. It is not replaced.\n\n## 3. Frozen executable source axes\n\nBreast ultrasound:\n\n- `BUSI_WHU_2025_V3`;\n- `BUS_BRA_2024`;\n- `BUS_UCLM_2025_V3`;\n- `RODRIGUES_BUI_2017`.\n\nDermatoscopy:\n\n- `HAM10000`;\n- `ISIC_MSK1`;\n- `ISIC_UDA1`.\n\nThe two previously blocked `BREAST_LESIONS_USG_2024` edges remain blocked. No source is added or refitted.\n\n## 4. Asset rules\n\n### BUSI\n\nOnly the official article supplementary archive is accepted. Normal images and masks are excluded. The target is confirmatory only if an explicit patient mapping is released. Filename numbering alone is not treated as a patient identifier. Without explicit grouping it becomes `UNAVAILABLE_GROUPING_NOT_PROVABLE`.\n\n### OASBUD\n\nOnly Zenodo record 545928 v1 is accepted. Raw RF matrices are rendered by the frozen Hilbert-envelope, 60-dB log-compression renderer. Orthogonal scans are averaged at the released patient or lesion group before scoring. Class labels remain broker-encrypted until requested by a presealed witness manifest.\n\n### Derm7pt\n\nOnly the authenticated SFU author release is accepted. Dermoscopy images are used; clinical photographs are excluded. Official metadata are quarantined, and case/lesion grouping is required. Third-party Kaggle or reconstructed copies are prohibited.\n\n## 5. Outcome firewall\n\nBefore any label is requested, the notebook must freeze:\n\n- asset receipts and archive hashes;\n- outcome-free grouping and target availability;\n- cross-roster deduplication;\n- target embeddings and frozen source logits;\n- all 100 witness manifests for budgets 8, 16, 32, 64 and 128.\n\nLabels are stored in an encrypted local table. A stateful broker returns only labels for group IDs contained in the current presealed manifest and writes an immutable access ledger.\n\nThe allowed order is:\n\n1. budget-8 secondary witness accesses;\n2. Stage T2-M forecast and support status seal;\n3. budget-32 primary witness accesses;\n4. RA-CB and baseline prediction/certificate seal;\n5. budget-16, 64 and 128 secondary witness accesses;\n6. one final full-outcome unseal;\n7. true AUC, error, decision and evidence-interval evaluation.\n\nNo primary prediction can be recomputed after the final outcome unseal.\n\n## 6. Primary fixed-budget performance analysis\n\n- budget: 32 independent groups;\n- repetitions: 100;\n- acquisition: 25% random anchors plus 75% group D-optimal;\n- posterior: ridge logistic, `C=3.0`;\n- candidates: AMW-U and AMW-CB2;\n- balance features: `z,z²`;\n- balance ridge: 0.1;\n- weight clip: `[0.1,10]`;\n- minimum balance ESS: 8;\n- selector: lower held-out group mean Brier; tie to AMW-U;\n- AUC functional: soft weighted Mann–Whitney;\n- conformal radius: `0.16229985434323593`;\n- retention threshold: source validation AUC minus 0.15.\n\nBaselines use the same frozen manifests:\n\n- random-direct;\n- random-logistic-plugin;\n- active-direct;\n- AMW-U;\n- AMW-CB2;\n- RA-CB-AMW-DDET.\n\n## 7. Evidence-demand secondary\n\nThe secondary uses the target-expected budget-8 median disagreement across precommitted repetitions. It is not a single-pilot deployment rule and never controls acquisition.\n\nThe frozen Stage T2-M model and support rule produce:\n\n- latent `log2` evidence demand;\n- category probabilities for `≤8`, `8–16`, `16–32`, `32–64`, `64–128`, `>128`;\n- support distance and `SUPPORTED` or `OUT_OF_SUPPORT_ABSTAIN`;\n- bootstrap uncertainty.\n\nObserved evidence demand is interval-censored using the unchanged AMW-DDET median-error threshold 0.04 and budgets `8,16,32,64,128`.\n\n## 8. Scenario classification\n\n### Primary-survival gate\n\nThe performance primary survives only if all integrity gates pass and, among analyzable targets:\n\n1. at least two targets from at least two modalities are analyzable;\n2. target-level RA-CB median MAE is at most 0.05;\n3. relative median-MAE improvement over random-direct is at least 25%;\n4. RA-CB has lower target-level median error than random-logistic on a strict majority of analyzable targets;\n5. all-edge Spearman correlation is at least 0.75;\n6. frozen interval coverage is at least 0.85;\n7. wrong-decision rate among decided edges is at most 0.05.\n\n### Evidence-secondary survival gate\n\nThe evidence secondary survives only if:\n\n1. at least two supported targets have observed intervals;\n2. mean prospective interval NLL on supported targets is at most `2.41565`, the frozen provider-extension mean plus a 0.5 non-inferiority margin;\n3. every supported target assigns at least 0.05 probability to its observed censoring interval;\n4. no supported target underestimates the operational budget by more than one doubling;\n5. interval-order concordance is at least 0.5 when at least one pair is comparable.\n\n### Final interpretation\n\n- **Scenario A:** primary-survival and evidence-secondary survival;\n- **Scenario B:** primary-survival and evidence-secondary failure;\n- **Scenario C:** primary-survival failure;\n- **Integrity termination:** any leakage, hash, chronology or frozen-method violation.\n\n## 9. Reporting\n\nTarget is the primary exchange unit. Edges and repetitions are never treated as independent targets.\n\nEvery target and edge is reported, including unavailable targets, abstentions, skipped repetitions, selector diagnostics, interval coverage, decision coverage, and reasons for failure.\n\n## 10. Authority boundary\n\nA Scenario A result authorises only a T3-B activation review and manuscript upgrade review. It does not authorise claims of broad prospective cross-modality validation, adaptive label allocation, single-pilot deployment or Stage 12.\n'
EMBEDDED_METHOD = '# Stage T3-A encrypted outcome broker and sequential blind execution method v0.1\n\n## Local-first execution\n\nAll downloads, extraction, image rendering, embeddings, witness fitting and outcome evaluation occur under a transient Colab runtime tree. Authenticated manually supplied official files remain in the governed acquisition inbox. Automatically reproducible BUSI/OASBUD archives are kept transiently; their official URLs, byte counts and cryptographic receipts are committed together with governed manifests, frozen prediction records, compact embeddings/results and a canonical record bundle.\n\n## Label quarantine\n\nAsset adapters produce two logically separate objects:\n\n1. an outcome-free roster containing target, group, image and modality fields;\n2. a label table encrypted with a runtime-generated Fernet key.\n\nThe key remains only in runtime memory. The broker enforces phase ordering and logs every group-label request. The final full-label call is rejected unless the evidence forecast and primary prediction seals both exist.\n\n## Witness manifests\n\nAll manifests are generated before label access from frozen source-logit geometry. Seeds, budgets and selection rules are deterministic. Each manifest records the exact group IDs and SHA-256. Later phases cannot alter them.\n\n## RF rendering\n\nFor OASBUD, numeric RF matrices are identified from the official MATLAB container using a schema audit. Binary ROI masks and low-cardinality arrays are rejected. Each accepted RF matrix is converted to an analytic envelope using the Hilbert transform, compressed over 60 dB and saved as an 8-bit B-mode image. Multiple orthogonal scans are aggregated at the official lesion/patient group.\n\n## Representation and axes\n\nThe unchanged ImageNet ResNet-50 V2 representation is L2-normalised. Frozen source axes are loaded by exact SHA-256. No feature, axis, source calibration or threshold is refitted.\n\n## Prediction chronology\n\nThe evidence forecast is sealed after the budget-8 phase. The performance record is sealed after budget 32. Only after both seals are verified are the remaining waves and full outcomes released.\n\n## Durable commit\n\nThe notebook creates a canonical ZIP and copies every required output to `StageT3-A_v0.1`. Each Drive copy is reopened and hashed. A durable commit manifest is written before a Drive flush/unmount request.\n'
EMBEDDED_MANUAL = '# Stage T3-A manual access queue and exact drop locations v0.1\n\n## Immediate required manual item: Derm7pt official author release\n\nOfficial request page:\n\n`https://derm.cs.sfu.ca/Download.html`\n\nThe page states that the username and password are emailed after the request form is completed. Download the official images and metadata using those credentials.\n\nPlace **all untouched official downloaded files** in:\n\n`MyDrive/Cross-Modal_Diagnostic_Observability/00_Data_Acquisition/Cross_Modal_Locked_Blind_Sentinel_v0.1/DERM7PT_2019/00_Raw_Inbox/`\n\nDrive folder:\n\n`https://drive.google.com/drive/folders/1EndoJ19RnwfbIBVIEINa9Gyu4B_qT0HP`\n\nAccepted inputs include ZIP/TAR/GZ/7Z archives and the original metadata CSV files. Do not rename or extract them. Do not use Kaggle or another mirror.\n\n## Automatic items\n\nThe notebook automatically attempts:\n\n- BUSI from the official Data in Brief supplementary routes;\n- OASBUD from Zenodo record 545928 v1.\n\nTheir reserved inboxes are:\n\n- BUSI: `.../BUSI_CAIRO_2019/00_Raw_Inbox/`\n- OASBUD: `.../OASBUD_2017/00_Raw_Inbox/`\n\nNo manual action is initially required for those two targets.\n\n## Important\n\nRun the notebook only after the official Derm7pt files are present. Without Derm7pt, the two-modality primary-survival gate cannot pass, even if OASBUD succeeds.\n'
EMBEDDED_REGISTRY = 'target,modality,task,tier,official_route,access_mode,grouping_requirement,frozen_sources,candidate_edges,manual_action,replacement_allowed\nBUSI_CAIRO_2019,breast_ultrasound,breast_lesion_malignant_vs_benign,T3-A_SENTINEL,Data in Brief supplementary archive; PMC6906728 / S2352340919312181,AUTO_OFFICIAL_SUPPLEMENTARY_DOWNLOAD,explicit patient mapping; otherwise unavailable,BUSI_WHU_2025_V3|BUS_BRA_2024|BUS_UCLM_2025_V3|RODRIGUES_BUI_2017,4,none,False\nOASBUD_2017,breast_ultrasound,breast_lesion_malignant_vs_benign,T3-A_SENTINEL,Zenodo record 545928 v1; OASBUD.mat,AUTO_OFFICIAL_ZENODO_DOWNLOAD,"patient if released; otherwise lesion, with orthogonal scans aggregated",BUSI_WHU_2025_V3|BUS_BRA_2024|BUS_UCLM_2025_V3|RODRIGUES_BUI_2017,4,none,False\nDERM7PT_2019,dermoscopy,melanoma_vs_melanocytic_nevus,T3-A_SENTINEL,SFU Derm7pt author release; password request at derm.cs.sfu.ca/Download.html,MANUAL_OFFICIAL_AUTHENTICATED_DOWNLOAD,case/lesion identifier from official metadata; dermoscopy images only,HAM10000|ISIC_MSK1|ISIC_UDA1,3,place all untouched official files in exact Drive inbox,False\n'
EMBEDDED_README = '# Cross-Modal notebook index v2.3\n\n## Active locked-blind execution\n\n`CrossModal_StageT3-A_Locked_Blind_Sentinel_Scenario_Classification_And_Execution_v0.1_SELF_CONTAINED.ipynb`\n\nPrerequisite: place the authenticated official Derm7pt release in the exact inbox documented by the Stage T3-A manual queue.\n\nThe notebook is self-contained and CPU-compatible. It automatically acquires BUSI and OASBUD, freezes every witness manifest before label access, seals the evidence forecast and budget-32 primary predictions before full outcome unseal, evaluates Scenario A/B/C, and performs a verified durable Drive commit.\n\nSuperseded notebooks must not be used for blind scoring.\n'
EMBEDDED_DERM_MARKER = 'Stage T3-A — official Derm7pt release required\n\nOfficial credential/request page:\nhttps://derm.cs.sfu.ca/Download.html\n\nPlace every untouched official downloaded archive and metadata file in this folder.\nDo not rename, extract, reorganize, or convert the files.\nDo not use Kaggle or any other third-party mirror.\n\nAfter the official files are present, run:\nCrossModal_StageT3-A_Locked_Blind_Sentinel_Scenario_Classification_And_Execution_v0.1_SELF_CONTAINED.ipynb\n\nThe notebook will keep labels quarantined, freeze all witness manifests before\nanalysis label access, seal the evidence forecast and budget-32 primary predictions\nbefore final outcome unseal, classify Scenario A/B/C, and perform a verified Drive commit.\n'

DOC_SPECS = {
    "prereg": (
        STUDY_ROOT / "StageT3-A_Locked_Blind_Sentinel_Scenario_Classification_And_Execution_Preregistration_v1.1.md",
        "6eccf8abb59fbc22c3d7e3f3e35b02eb4cd3cd54662153db0dbe0f0917456b7f",
    ),
    "method": (
        STUDY_ROOT / "StageT3-A_Encrypted_Outcome_Broker_And_Sequential_Blind_Execution_Method_v0.1.md",
        "9857e7c7ef40529dae818294528ddc4e3b4422dc98965e76c7ee3598441d7046",
    ),
    "manual": (
        STUDY_ROOT / "StageT3-A_Manual_Access_Queue_And_Exact_Drop_Locations_v0.1.md",
        "62903f0155d461364634ab751fad61eb6809a1af2f69efac549348c7bf1da174",
    ),
    "registry": (
        MAP_ROOT / "StageT3-A_Locked_Blind_Target_Registry_v1.1.csv",
        "35331a87de715fd82c7773ec087898fd778a3763f08600d20d75e5992b1f91f6",
    ),
}

DERM_INBOX = ACQ_ROOT / "DERM7PT_2019" / "00_Raw_Inbox"
BUSI_INBOX = ACQ_ROOT / "BUSI_CAIRO_2019" / "00_Raw_Inbox"
OASBUD_INBOX = ACQ_ROOT / "OASBUD_2017" / "00_Raw_Inbox"
for path in [DERM_INBOX, BUSI_INBOX, OASBUD_INBOX]:
    path.mkdir(parents=True, exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "CMDO-StageT3-A/1.1 governed academic validation"})
SESSION.mount(
    "https://",
    requests.adapters.HTTPAdapter(pool_connections=8, pool_maxsize=8, max_retries=2),
)

def now():
    return datetime.now(timezone.utc).isoformat()

def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()

def sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def md5_file(path):
    digest = hashlib.md5()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def sha_json(value):
    return sha_bytes(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    )

def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    os.replace(temp, path)

def write_csv(path, frame):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    frame.fillna("").to_csv(
        temp, index=False, lineterminator="\n", float_format="%.12g"
    )
    os.replace(temp, path)

def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, path)

def verify_self_record(path, hash_field, expected=None):
    record = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    claim = record[hash_field]
    core = dict(record)
    core.pop(hash_field)
    assert sha_json(core) == claim, f"Self-hash mismatch: {path}"
    if expected is not None:
        assert claim == expected, f"Unexpected record hash: {path}"
    return record

def find_file_by_hash(filename, expected_hash, search_root=PROJECT_ROOT):
    candidates = list(Path(search_root).rglob(filename))
    for candidate in candidates:
        if candidate.is_file() and sha_file(candidate) == expected_hash:
            return candidate
    raise AssertionError(
        f"Required exact file not found: {filename} / {expected_hash}\n"
        + "\n".join(map(str, candidates[:20]))
    )

def find_self_record(filename, hash_field, expected_hash):
    candidates = list(PROJECT_ROOT.rglob(filename))
    for candidate in candidates:
        try:
            record = verify_self_record(candidate, hash_field)
            if record[hash_field] == expected_hash:
                return candidate, record
        except Exception:
            continue
    raise AssertionError(f"Required self-hashed record not found: {filename}")

def find_first(filename):
    candidates = [p for p in PROJECT_ROOT.rglob(filename) if p.is_file()]
    assert candidates, f"Missing required file: {filename}"
    return sorted(candidates, key=lambda p: (len(p.parts), str(p)))[0]


def materialise_exact_text(path, text, expected_sha256):
    path = Path(path)
    if path.exists():
        assert sha_file(path) == expected_sha256, (
            f"Immutable companion already exists with different bytes: {path}"
        )
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, path)
    assert sha_file(path) == expected_sha256

materialise_exact_text(
    DOC_SPECS["prereg"][0], EMBEDDED_PREREG, DOC_SPECS["prereg"][1]
)
materialise_exact_text(
    DOC_SPECS["method"][0], EMBEDDED_METHOD, DOC_SPECS["method"][1]
)
materialise_exact_text(
    DOC_SPECS["manual"][0], EMBEDDED_MANUAL, DOC_SPECS["manual"][1]
)
materialise_exact_text(
    DOC_SPECS["registry"][0], EMBEDDED_REGISTRY, DOC_SPECS["registry"][1]
)
readme_drive_path = CODE_ROOT / "README_Cross_Modal_Notebook_Index_v2.3.md"
if readme_drive_path.exists():
    assert sha_file(readme_drive_path) == sha_bytes(EMBEDDED_README.encode("utf-8"))
else:
    write_text(readme_drive_path, EMBEDDED_README)

derm_marker_drive_path = DERM_INBOX / "MANUAL_DROP_HERE_DERM7PT_OFFICIAL_RELEASE.txt"
if derm_marker_drive_path.exists():
    assert sha_file(derm_marker_drive_path) == sha_bytes(
        EMBEDDED_DERM_MARKER.encode("utf-8")
    )
else:
    write_text(derm_marker_drive_path, EMBEDDED_DERM_MARKER)


# Verify frozen companion documents before any blind asset is read.
for role, (path, expected_hash) in DOC_SPECS.items():
    assert path.is_file(), f"Missing Stage T3-A companion: {path}"
    assert sha_file(path) == expected_hash, f"Stage T3-A companion changed: {role}"

t3pf_path, t3pf = find_self_record(
    "StageT3-PF_Activation_Record_v1.0.json",
    "activation_record_sha256",
    EXPECTED["t3pf_activation"],
)
t2mn_path, t2mn = find_self_record(
    "StageT2-MN_Complete_v0.1.json",
    "final_record_sha256",
    EXPECTED["t2mn_final"],
)
t2h_path, t2h = find_self_record(
    "StageT2-H_Complete_v0.1.json",
    "final_record_sha256",
    EXPECTED["t2h_final"],
)
t2f_path, t2f = find_self_record(
    "StageT2-F_Complete_v0.1.json",
    "final_record_sha256",
    EXPECTED["t2f_final"],
)

assert t2mn["decision"].endswith("AUTHORISE_STAGE3_ACTIVATION_REVIEW_ONLY")
assert t2h["single_pilot_deployment_authorised"] is False
assert t3pf["blind_assets_acquired"] is False
assert t3pf["blind_outcomes_accessed"] is False
assert t3pf["stage12_authorised"] is False

t2mn_bundle = find_file_by_hash(
    "StageT2-MN_Canonical_Records_v0.1.zip",
    EXPECTED["t2mn_bundle_file"],
)
t2m_model_path = find_file_by_hash(
    "StageT2-M_Final_Interval_Censored_Model_Freeze_v0.1.json",
    "778f51386f28f22b09f840bd7d6fff583eb514cde75115ce462ab32ff9c76c26",
)
t2m_support_path = find_file_by_hash(
    "StageT2-M_Future_Support_Abstention_Freeze_v0.1.json",
    "3225e8ead415eaa85ffafd245f54d1a6afeab5646df66567d699a5a17d23daec",
)
t2m_bootstrap_path = find_file_by_hash(
    "StageT2-M_Family_Bootstrap_Parameter_Draws_v0.1.csv",
    EXPECTED["t2m_bootstrap_file"],
)
t2m_model = verify_self_record(t2m_model_path, "model_freeze_sha256", EXPECTED["t2m_model"])
t2m_support = verify_self_record(t2m_support_path, "support_freeze_sha256", EXPECTED["t2m_support"])

axis_paths = {
    source: find_file_by_hash(filename, AXIS_SHA[source])
    for source, filename in AXIS_FILENAMES.items()
}

# The authenticated Derm7pt release is required before the first blind run.
derm_payload_files = [
    path for path in DERM_INBOX.rglob("*")
    if path.is_file()
    and not path.name.startswith("MANUAL_DROP")
    and not path.name.startswith("OFFICIAL_ROUTE")
    and path.stat().st_size > 1024
]
assert derm_payload_files, (
    "DERM7PT official release is not present.\n"
    "Request credentials at https://derm.cs.sfu.ca/Download.html and place all "
    "untouched official files in:\n" + str(DERM_INBOX)
)

activation_payload = {
    "stage": "StageT3-A",
    "purpose": "locked_blind_sentinel_scenario_classification_and_execution",
    "parent_t3pf_activation_sha256": EXPECTED["t3pf_activation"],
    "parent_t2mn_final_sha256": EXPECTED["t2mn_final"],
    "parent_t2f_final_sha256": EXPECTED["t2f_final"],
    "parent_t2h_final_sha256": EXPECTED["t2h_final"],
    "t2m_model_freeze_sha256": EXPECTED["t2m_model"],
    "t2m_support_freeze_sha256": EXPECTED["t2m_support"],
    "preregistration_sha256": DOC_SPECS["prereg"][1],
    "method_sha256": DOC_SPECS["method"][1],
    "registry_sha256": DOC_SPECS["registry"][1],
    "targets": ["BUSI_CAIRO_2019", "OASBUD_2017", "DERM7PT_2019"],
    "candidate_edges": 11,
    "single_pilot_deployment_authorised": False,
    "blind_full_outcomes_unsealed": False,
    "stage12_authorised": False,
    "activated_utc": now(),
}
activation_payload["activation_seal_sha256"] = sha_json(activation_payload)
write_json(P0 / "StageT3-A_Activation_Seal_v0.1.json", activation_payload)

print("Stage T3-A activation seal:", activation_payload["activation_seal_sha256"])
print("Blind full outcomes unsealed:", False)
print("Single-pilot deployment authorised:", False)
print("Stage 12 authorised:", False)



# Official blind asset acquisition, trusted endpoint adapter, encrypted label quarantine, and deduplication
def normalise_column(value):
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")

def normalise_text(value):
    value = unicodedata.normalize("NFKD", str(value))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower().replace("đ", "d")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def stable_hash(*values):
    return sha_bytes("||".join(map(str, values)).encode("utf-8"))

def safe_extract_archive(source, destination):
    source = Path(source)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    suffixes = "".join(source.suffixes).lower()
    base = destination.resolve()

    def validate_member(name):
        target = (destination / name).resolve()
        if not (target == base or str(target).startswith(str(base) + os.sep)):
            raise RuntimeError(f"Unsafe archive member: {name}")

    if source.suffix.lower() == ".zip":
        with zipfile.ZipFile(source) as archive:
            for member in archive.infolist():
                validate_member(member.filename)
            archive.extractall(destination)
    elif suffixes.endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz")):
        with tarfile.open(source, "r:*") as archive:
            for member in archive.getmembers():
                validate_member(member.name)
            archive.extractall(destination)
    elif source.suffix.lower() == ".7z":
        import py7zr
        with py7zr.SevenZipFile(source, mode="r") as archive:
            for name in archive.getnames():
                validate_member(name)
            archive.extractall(destination)
    elif source.suffix.lower() == ".rar":
        executable = shutil.which("7z") or shutil.which("7zz")
        if executable is None:
            subprocess.run(
                ["apt-get", "update", "-qq"], check=True, timeout=600
            )
            subprocess.run(
                ["apt-get", "install", "-y", "-qq", "p7zip-full"],
                check=True, timeout=600,
            )
            executable = shutil.which("7z") or shutil.which("7zz")
        assert executable is not None, "RAR extractor unavailable"
        subprocess.run(
            [executable, "x", "-y", str(source), f"-o{destination}"],
            check=True, timeout=1800,
        )
    else:
        raise RuntimeError(f"Unsupported archive: {source.name}")

def copy_and_expand_official_files(source_root, target_root):
    source_root = Path(source_root)
    target_root = Path(target_root)
    raw_copy = target_root / "00_Official_Files"
    extracted = target_root / "01_Extracted"
    raw_copy.mkdir(parents=True, exist_ok=True)
    extracted.mkdir(parents=True, exist_ok=True)
    copied = []
    for source in source_root.rglob("*"):
        if not source.is_file():
            continue
        if source.name.startswith(("MANUAL_DROP", "OFFICIAL_ROUTE")):
            continue
        relative = source.relative_to(source_root)
        destination = raw_copy / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied.append(destination)
    for source in copied:
        if (
            source.suffix.lower() in {".zip", ".rar", ".7z", ".tar"}
            or "".join(source.suffixes).lower().endswith(
                (".tar.gz", ".tgz", ".tar.bz2", ".tar.xz")
            )
        ):
            safe_extract_archive(
                source,
                extracted / re.sub(r"[^A-Za-z0-9._-]+", "_", source.stem),
            )
        else:
            destination = extracted / source.relative_to(raw_copy)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
    return copied, extracted

def download_stream(urls, destination, minimum_bytes=1024, expected_md5=None):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    errors = []
    if destination.exists() and destination.stat().st_size >= minimum_bytes:
        if expected_md5 is None or md5_file(destination) == expected_md5:
            return {
                "status": "ALREADY_PRESENT_RUNTIME",
                "url": "cached",
                "bytes": destination.stat().st_size,
                "sha256": sha_file(destination),
                "md5": md5_file(destination),
                "error": "",
            }
        destination.unlink()

    for url in urls:
        for attempt in range(3):
            try:
                with SESSION.get(url, stream=True, timeout=(30, 240), allow_redirects=True) as response:
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").lower()
                    if "text/html" in content_type:
                        raise RuntimeError(f"HTML response instead of asset: {content_type}")
                    temp = destination.with_suffix(destination.suffix + ".part")
                    with temp.open("wb") as handle:
                        for chunk in response.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                handle.write(chunk)
                    if temp.stat().st_size < minimum_bytes:
                        raise RuntimeError(f"Asset too small: {temp.stat().st_size}")
                    os.replace(temp, destination)
                    if expected_md5 is not None:
                        observed_md5 = md5_file(destination)
                        if observed_md5 != expected_md5:
                            raise RuntimeError(
                                f"MD5 mismatch {observed_md5} != {expected_md5}"
                            )
                    return {
                        "status": "DOWNLOADED_OFFICIAL",
                        "url": url,
                        "bytes": destination.stat().st_size,
                        "sha256": sha_file(destination),
                        "md5": md5_file(destination),
                        "error": "",
                    }
            except Exception as exc:
                errors.append(f"{url} attempt {attempt+1}: {type(exc).__name__}: {exc}")
                time.sleep(2.0 * (attempt + 1))
                part = destination.with_suffix(destination.suffix + ".part")
                if part.exists():
                    part.unlink()
    return {
        "status": "FAILED_OFFICIAL_DOWNLOAD",
        "url": "",
        "bytes": 0,
        "sha256": "",
        "md5": "",
        "error": " || ".join(errors),
    }

def scalar_value(value):
    array = np.asarray(value)
    if array.size == 0:
        return ""
    if array.size == 1:
        value = array.reshape(-1)[0]
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return value.item() if hasattr(value, "item") else value
    return value

def matlab_field(record, candidates):
    fields = getattr(record, "_fieldnames", None)
    if fields is None and isinstance(record, dict):
        fields = list(record)
    if not fields:
        return None
    mapping = {normalise_column(field): field for field in fields}
    for candidate in candidates:
        key = normalise_column(candidate)
        if key in mapping:
            field = mapping[key]
            return record[field] if isinstance(record, dict) else getattr(record, field)
    return None

def walk_mat_records(value, depth=0):
    if depth > 8:
        return
    fields = getattr(value, "_fieldnames", None)
    if fields:
        normalized = {normalise_column(field) for field in fields}
        if (
            any(field in normalized for field in {"rf1", "rf_1"})
            and any(field in normalized for field in {"rf2", "rf_2"})
            and any(field in normalized for field in {"class", "label", "diagnosis"})
        ):
            yield value
            return
        for field in fields:
            child = getattr(value, field)
            yield from walk_mat_records(child, depth + 1)
        return
    if isinstance(value, dict):
        normalized = {normalise_column(field) for field in value}
        if (
            any(field in normalized for field in {"rf1", "rf_1"})
            and any(field in normalized for field in {"rf2", "rf_2"})
            and any(field in normalized for field in {"class", "label", "diagnosis"})
        ):
            yield value
            return
        for child in value.values():
            yield from walk_mat_records(child, depth + 1)
        return
    if isinstance(value, np.ndarray) and value.dtype == object:
        for child in value.reshape(-1):
            yield from walk_mat_records(child, depth + 1)

def map_binary_class(value):
    value = scalar_value(value)
    if isinstance(value, (int, float, np.integer, np.floating)) and np.isfinite(value):
        numeric = int(round(float(value)))
        if numeric in {0, 1}:
            return numeric
    text = normalise_text(value)
    if text in {"1", "m", "malignant", "malign"} or "malignant" in text:
        return 1
    if text in {"0", "b", "benign"} or "benign" in text:
        return 0
    raise ValueError(f"Unmapped binary class: {value!r}")

def render_rf_bmode(rf, destination, dynamic_range_db=60.0):
    value = rf
    unwrap_count = 0
    while isinstance(value, np.ndarray) and value.dtype == object and value.size == 1:
        value = value.reshape(-1)[0]
        unwrap_count += 1
        if unwrap_count > 8:
            break
    array = np.asarray(value)
    array = np.squeeze(array)
    while array.ndim > 2:
        array = array[..., 0]
    if array.ndim != 2 or min(array.shape) < 8:
        raise ValueError(f"RF array is not a valid 2-D scan: {array.shape}")
    array = np.asarray(array, dtype=np.float64)
    if not np.isfinite(array).all():
        finite = array[np.isfinite(array)]
        fill = float(np.median(finite)) if finite.size else 0.0
        array = np.nan_to_num(array, nan=fill, posinf=fill, neginf=fill)
    if array.shape[0] < array.shape[1]:
        array = array.T
    envelope = np.abs(hilbert(array, axis=0))
    maximum = float(np.max(envelope))
    if maximum <= 0:
        raise ValueError("RF envelope is zero")
    db = 20.0 * np.log10(np.maximum(envelope / maximum, 10 ** (-dynamic_range_db / 20)))
    db = np.clip(db, -dynamic_range_db, 0)
    image = np.uint8(np.round((db + dynamic_range_db) / dynamic_range_db * 255.0))
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image, mode="L").save(destination)
    return image.shape

def trusted_adapt_oasbud(mat_path, work_root):
    audit = {
        "target": "OASBUD_2017",
        "status": "HOLD_SCHEMA_NOT_RESOLVED",
        "official_asset_sha256": sha_file(mat_path),
        "trusted_outcome_adapter_accessed": True,
    }
    try:
        loaded = loadmat(mat_path, squeeze_me=True, struct_as_record=False)
    except NotImplementedError:
        try:
            import mat73
            loaded = mat73.loadmat(mat_path)
        except Exception as exc:
            audit["error"] = f"MAT73 load failed: {type(exc).__name__}: {exc}"
            return pd.DataFrame(), pd.DataFrame(), audit
    except Exception as exc:
        audit["error"] = f"MAT load failed: {type(exc).__name__}: {exc}"
        return pd.DataFrame(), pd.DataFrame(), audit

    records = []
    for key, value in loaded.items():
        if str(key).startswith("__"):
            continue
        records.extend(list(walk_mat_records(value)))
    # Preserve first occurrence of each object identity.
    unique_records = []
    seen = set()
    for record in records:
        identifier = id(record)
        if identifier not in seen:
            seen.add(identifier)
            unique_records.append(record)

    roster_rows = []
    label_rows = []
    parse_errors = []
    render_root = Path(work_root) / "rendered"
    for position, record in enumerate(unique_records):
        try:
            identifier = matlab_field(record, ["id", "patient_id", "lesion_id", "case_id"])
            identifier = str(scalar_value(identifier)).strip() or f"record_{position:04d}"
            label = map_binary_class(
                matlab_field(record, ["class", "label", "diagnosis"])
            )
            rf_values = [
                matlab_field(record, ["rf1", "rf_1"]),
                matlab_field(record, ["rf2", "rf_2"]),
            ]
            group_id = f"OASBUD_2017::LESION::{identifier}"
            for scan_index, rf in enumerate(rf_values, 1):
                if rf is None:
                    continue
                image_id = f"{identifier}_scan{scan_index}"
                image_path = render_root / f"{image_id}.png"
                render_rf_bmode(rf, image_path, dynamic_range_db=60.0)
                roster_rows.append({
                    "target": "OASBUD_2017",
                    "provider": "Institute of Oncology Warsaw / IPPT PAN",
                    "modality": "breast_ultrasound",
                    "task": "breast_lesion_malignant_vs_benign",
                    "group_id": group_id,
                    "image_id": image_id,
                    "unit_id": f"OASBUD_2017::RF::{image_id}",
                    "image_path": str(image_path),
                    "group_basis": "official OASBUD lesion Id; orthogonal scans aggregated",
                    "official_asset": str(mat_path),
                })
            label_rows.append({
                "target": "OASBUD_2017",
                "group_id": group_id,
                "label": int(label),
            })
        except Exception as exc:
            parse_errors.append(f"record {position}: {type(exc).__name__}: {exc}")

    roster = pd.DataFrame(roster_rows)
    labels = pd.DataFrame(label_rows).drop_duplicates(["target", "group_id"])
    if len(roster):
        valid_groups = set(labels["group_id"])
        roster = roster[roster["group_id"].isin(valid_groups)].copy()
    if labels["group_id"].nunique() >= 40 and roster["group_id"].nunique() >= 40:
        audit["status"] = "READY_OFFICIAL_LESION_GROUPING"
    else:
        audit["status"] = "HOLD_INSUFFICIENT_OR_UNPARSED_GROUPS"
    audit.update({
        "mat_struct_records_found": len(unique_records),
        "eligible_groups_opaque": int(labels["group_id"].nunique()) if len(labels) else 0,
        "rendered_units": len(roster),
        "parse_error_count": len(parse_errors),
        "parse_errors_first10": parse_errors[:10],
    })
    return roster, labels, audit

def find_table_column(frame, exact=(), contains=()):
    mapping = {normalise_column(column): column for column in frame.columns}
    for candidate in exact:
        if normalise_column(candidate) in mapping:
            return mapping[normalise_column(candidate)]
    for column in frame.columns:
        normalized = normalise_column(column)
        if any(token in normalized for token in contains):
            return column
    return None

def trusted_adapt_busi(extracted_root, official_archive):
    image_files = [
        path for path in Path(extracted_root).rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp"}
        and "_mask" not in path.stem.lower()
        and "mask" not in path.parent.name.lower()
    ]
    endpoint_images = [
        path for path in image_files
        if any(
            token in normalise_text(" ".join(path.parts))
            for token in ["benign", "malignant"]
        )
        and "normal" not in normalise_text(" ".join(path.parts))
    ]

    tables = [
        path for path in Path(extracted_root).rglob("*")
        if path.is_file() and path.suffix.lower() in {".csv", ".xlsx", ".xls"}
    ]
    explicit_mapping = None
    mapping_audit = []
    for table in tables:
        try:
            frame = (
                pd.read_csv(table)
                if table.suffix.lower() == ".csv"
                else pd.read_excel(table)
            )
        except Exception:
            continue
        image_col = find_table_column(
            frame, ["image", "image_id", "filename", "file_name"],
            ("image", "file"),
        )
        patient_col = find_table_column(
            frame, ["patient_id", "patient", "subject_id", "subject"],
            ("patient", "subject"),
        )
        label_col = find_table_column(
            frame, ["class", "label", "diagnosis"],
            ("class", "label", "diagnos"),
        )
        mapping_audit.append({
            "table": str(table),
            "image_column": image_col or "",
            "patient_column": patient_col or "",
            "label_column": label_col or "",
        })
        if image_col and patient_col and label_col:
            explicit_mapping = (frame, image_col, patient_col, label_col)
            break

    audit = {
        "target": "BUSI_CAIRO_2019",
        "official_asset_sha256": sha_file(official_archive),
        "official_endpoint_images": len(endpoint_images),
        "table_audit": mapping_audit,
        "trusted_outcome_adapter_accessed": bool(explicit_mapping),
    }
    if explicit_mapping is None:
        audit["status"] = "UNAVAILABLE_GROUPING_NOT_PROVABLE"
        audit["reason"] = (
            "Official release has class directories/filenames but no explicit "
            "patient-to-image mapping; filename numbering is not accepted as patient ID."
        )
        return pd.DataFrame(), pd.DataFrame(), audit

    frame, image_col, patient_col, label_col = explicit_mapping
    by_name = {path.name.lower(): path for path in endpoint_images}
    by_stem = {path.stem.lower(): path for path in endpoint_images}
    roster_rows, label_rows, errors = [], [], []
    for _, row in frame.iterrows():
        try:
            key = str(row[image_col]).strip()
            path = by_name.get(Path(key).name.lower()) or by_stem.get(Path(key).stem.lower())
            if path is None:
                continue
            label = map_binary_class(row[label_col])
            patient = str(row[patient_col]).strip()
            if not patient or patient.lower() in {"nan", "none"}:
                continue
            group_id = f"BUSI_CAIRO_2019::PATIENT::{patient}"
            roster_rows.append({
                "target": "BUSI_CAIRO_2019",
                "provider": "Cairo University",
                "modality": "breast_ultrasound",
                "task": "breast_lesion_malignant_vs_benign",
                "group_id": group_id,
                "image_id": path.stem,
                "unit_id": f"BUSI_CAIRO_2019::IMAGE::{path.stem}",
                "image_path": str(path),
                "group_basis": f"official table {Path(table).name} patient mapping",
                "official_asset": str(official_archive),
            })
            label_rows.append({
                "target": "BUSI_CAIRO_2019",
                "group_id": group_id,
                "label": int(label),
            })
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
    roster = pd.DataFrame(roster_rows)
    labels = pd.DataFrame(label_rows)
    if len(labels):
        mixed = labels.groupby(["target", "group_id"])["label"].nunique()
        mixed_groups = set(group for (_, group), count in mixed.items() if count > 1)
        roster = roster[~roster["group_id"].isin(mixed_groups)]
        labels = labels[~labels["group_id"].isin(mixed_groups)].drop_duplicates(
            ["target", "group_id"]
        )
    ready = len(labels) and labels["group_id"].nunique() >= 40
    audit["status"] = "READY_EXPLICIT_PATIENT_GROUPING" if ready else "HOLD_GROUPING_OR_SAMPLE_GATE"
    audit["eligible_groups_opaque"] = int(labels["group_id"].nunique()) if len(labels) else 0
    audit["parse_errors_first10"] = errors[:10]
    return roster, labels, audit

def derm_endpoint_label(value):
    text = normalise_text(value)
    if "melanoma" in text or text in {"mel", "mm"}:
        return 1
    if "nevus" in text or "naevus" in text or text in {"nv", "nev"}:
        return 0
    return None

def trusted_adapt_derm7pt(extracted_root, official_files):
    csv_files = [
        path for path in Path(extracted_root).rglob("*.csv")
        if path.is_file()
    ]
    preferred = [
        path for path in csv_files
        if path.name.lower() == "meta.csv" and "meta" in [p.lower() for p in path.parts]
    ]
    metadata_path = preferred[0] if preferred else (
        next((p for p in csv_files if p.name.lower() == "meta.csv"), None)
    )
    if metadata_path is None:
        return pd.DataFrame(), pd.DataFrame(), {
            "target": "DERM7PT_2019",
            "status": "HOLD_OFFICIAL_METADATA_NOT_FOUND",
            "trusted_outcome_adapter_accessed": False,
            "official_file_hashes": [sha_file(path) for path in official_files],
        }

    metadata = pd.read_csv(metadata_path)
    case_col = find_table_column(
        metadata, ["case_num", "case_id", "case", "lesion_id", "id"],
        ("case", "lesion"),
    )
    diagnosis_col = find_table_column(
        metadata, ["diagnosis", "diag", "label"],
        ("diagnos", "diag"),
    )

    derm_candidates = []
    for column in metadata.columns:
        normalized = normalise_column(column)
        if "derm" in normalized:
            values = metadata[column].dropna().astype(str)
            image_like = values.str.contains(
                r"\.(?:jpg|jpeg|png|bmp|tif|tiff)$", case=False, regex=True
            ).mean() if len(values) else 0
            derm_candidates.append((image_like, column))
    derm_col = max(derm_candidates, default=(0, None))[1]

    if not case_col or not diagnosis_col or not derm_col:
        return pd.DataFrame(), pd.DataFrame(), {
            "target": "DERM7PT_2019",
            "status": "HOLD_REQUIRED_SCHEMA_MISSING",
            "trusted_outcome_adapter_accessed": True,
            "metadata_path": str(metadata_path),
            "columns": list(map(str, metadata.columns)),
            "case_column": case_col or "",
            "diagnosis_column": diagnosis_col or "",
            "dermoscopy_column": derm_col or "",
        }

    image_files = [
        path for path in Path(extracted_root).rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
    ]
    by_name = {}
    by_stem = {}
    for path in image_files:
        by_name.setdefault(path.name.lower(), path)
        by_stem.setdefault(path.stem.lower(), path)

    roster_rows, label_rows, unresolved = [], [], []
    for row_index, row in metadata.iterrows():
        label = derm_endpoint_label(row[diagnosis_col])
        if label is None:
            continue
        case = str(row[case_col]).strip()
        if not case or case.lower() in {"nan", "none"}:
            continue
        derm_value = str(row[derm_col]).strip()
        path = (
            by_name.get(Path(derm_value).name.lower())
            or by_stem.get(Path(derm_value).stem.lower())
            or by_stem.get(case.lower())
        )
        if path is None:
            unresolved.append({
                "row": int(row_index), "case": case, "derm_value": derm_value
            })
            continue
        group_id = f"DERM7PT_2019::CASE::{case}"
        roster_rows.append({
            "target": "DERM7PT_2019",
            "provider": "SFU / Argenziano Derm7pt author release",
            "modality": "dermoscopy",
            "task": "melanoma_vs_melanocytic_nevus",
            "group_id": group_id,
            "image_id": path.stem,
            "unit_id": f"DERM7PT_2019::DERM::{path.stem}",
            "image_path": str(path),
            "group_basis": f"official metadata {case_col}; dermoscopy field {derm_col}",
            "official_asset": "|".join(map(str, official_files)),
        })
        label_rows.append({
            "target": "DERM7PT_2019",
            "group_id": group_id,
            "label": int(label),
        })

    roster = pd.DataFrame(roster_rows)
    labels = pd.DataFrame(label_rows)
    if len(labels):
        mixed = labels.groupby(["target", "group_id"])["label"].nunique()
        mixed_groups = set(group for (_, group), count in mixed.items() if count > 1)
        roster = roster[~roster["group_id"].isin(mixed_groups)]
        labels = labels[~labels["group_id"].isin(mixed_groups)].drop_duplicates(
            ["target", "group_id"]
        )
        roster["stable"] = [
            stable_hash(group, image)
            for group, image in zip(roster["group_id"], roster["image_id"])
        ]
        roster = roster.sort_values("stable").drop_duplicates("group_id", keep="first")
        labels = labels[labels["group_id"].isin(set(roster["group_id"]))]

    audit = {
        "target": "DERM7PT_2019",
        "status": (
            "READY_OFFICIAL_CASE_GROUPING"
            if labels["group_id"].nunique() >= 40
            else "HOLD_INSUFFICIENT_ENDPOINT_GROUPS"
        ),
        "trusted_outcome_adapter_accessed": True,
        "metadata_path": str(metadata_path),
        "metadata_sha256": sha_file(metadata_path),
        "case_column": case_col,
        "diagnosis_column": diagnosis_col,
        "dermoscopy_column": derm_col,
        "eligible_groups_opaque": int(labels["group_id"].nunique()),
        "unresolved_dermoscopy_rows": len(unresolved),
        "unresolved_first10": unresolved[:10],
        "official_file_hashes": [sha_file(path) for path in official_files],
    }
    return roster, labels, audit

# Copy and adapt the authenticated Derm7pt release.
derm_official_files, derm_extract_root = copy_and_expand_official_files(
    DERM_INBOX, ASSET_WORK / "DERM7PT_2019"
)
derm_roster, derm_labels, derm_audit = trusted_adapt_derm7pt(
    derm_extract_root, derm_official_files
)

# Acquire and audit BUSI from official article supplementary routes.
busi_archive = ASSET_WORK / "BUSI_CAIRO_2019" / "mmc1.zip"
busi_receipt = download_stream(
    [
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC6906728/bin/mmc1.zip",
        "https://ars.els-cdn.com/content/image/1-s2.0-S2352340919312181-mmc1.zip",
    ],
    busi_archive,
    minimum_bytes=5_000_000,
)
if busi_receipt["status"].startswith(("DOWNLOADED", "ALREADY")):
    busi_extract_root = ASSET_WORK / "BUSI_CAIRO_2019" / "extracted"
    safe_extract_archive(busi_archive, busi_extract_root)
    busi_roster, busi_labels, busi_audit = trusted_adapt_busi(
        busi_extract_root, busi_archive
    )
else:
    busi_roster, busi_labels = pd.DataFrame(), pd.DataFrame()
    busi_audit = {
        "target": "BUSI_CAIRO_2019",
        "status": "UNAVAILABLE_OFFICIAL_DOWNLOAD_FAILED",
        "trusted_outcome_adapter_accessed": False,
        "error": busi_receipt["error"],
    }

# Acquire and adapt OASBUD from exact Zenodo v1 record.
oasbud_mat = ASSET_WORK / "OASBUD_2017" / "OASBUD.mat"
oasbud_receipt = download_stream(
    [
        "https://zenodo.org/records/545928/files/OASBUD.mat?download=1",
        "https://zenodo.org/api/records/545928/files/OASBUD.mat/content",
        "https://zenodo.org/record/545928/files/OASBUD.mat?download=1",
    ],
    oasbud_mat,
    minimum_bytes=250_000_000,
    expected_md5="e2b770a6ee2f06ebe480ed0962252100",
)
if oasbud_receipt["status"].startswith(("DOWNLOADED", "ALREADY")):
    oasbud_roster, oasbud_labels, oasbud_audit = trusted_adapt_oasbud(
        oasbud_mat, ASSET_WORK / "OASBUD_2017"
    )
else:
    oasbud_roster, oasbud_labels = pd.DataFrame(), pd.DataFrame()
    oasbud_audit = {
        "target": "OASBUD_2017",
        "status": "UNAVAILABLE_OFFICIAL_DOWNLOAD_FAILED",
        "trusted_outcome_adapter_accessed": False,
        "error": oasbud_receipt["error"],
    }

asset_receipts = pd.DataFrame([
    {
        "target": "BUSI_CAIRO_2019",
        "route_status": busi_receipt["status"],
        "official_url": busi_receipt["url"],
        "bytes": busi_receipt["bytes"],
        "sha256": busi_receipt["sha256"],
        "md5": busi_receipt["md5"],
        "error": busi_receipt["error"],
    },
    {
        "target": "OASBUD_2017",
        "route_status": oasbud_receipt["status"],
        "official_url": oasbud_receipt["url"],
        "bytes": oasbud_receipt["bytes"],
        "sha256": oasbud_receipt["sha256"],
        "md5": oasbud_receipt["md5"],
        "error": oasbud_receipt["error"],
    },
    {
        "target": "DERM7PT_2019",
        "route_status": "MANUAL_AUTHENTICATED_OFFICIAL_FILES_PRESENT",
        "official_url": "https://derm.cs.sfu.ca/Download.html",
        "bytes": sum(path.stat().st_size for path in derm_official_files),
        "sha256": sha_json([sha_file(path) for path in derm_official_files]),
        "md5": "",
        "error": "",
    },
])
write_csv(P1 / "StageT3-A_Official_Asset_Receipts_v0.1.csv", asset_receipts)
write_json(
    P1 / "StageT3-A_Trusted_Adapter_Audits_v0.1.json",
    [busi_audit, oasbud_audit, derm_audit],
)

roster_parts = [
    frame for frame in [busi_roster, oasbud_roster, derm_roster] if len(frame)
]
label_parts = [
    frame for frame in [busi_labels, oasbud_labels, derm_labels] if len(frame)
]
candidate_roster = (
    pd.concat(roster_parts, ignore_index=True, sort=False)
    if roster_parts else pd.DataFrame()
)
trusted_labels = (
    pd.concat(label_parts, ignore_index=True, sort=False)
    if label_parts else pd.DataFrame(columns=["target", "group_id", "label"])
)
assert len(candidate_roster), "No official blind target passed the schema adapter."

# Encrypt labels immediately; no plaintext label table is written to the records tree.
trusted_labels = trusted_labels.drop_duplicates(["target", "group_id"])
assert not trusted_labels.duplicated(["target", "group_id"]).any()
plaintext_label_json = trusted_labels.sort_values(
    ["target", "group_id"]
).to_json(orient="records")
LABEL_KEY = Fernet.generate_key()
LABEL_CIPHER = Fernet(LABEL_KEY).encrypt(plaintext_label_json.encode("utf-8"))
label_cipher_path = ASSET_WORK / "encrypted_group_labels.bin"
label_cipher_path.write_bytes(LABEL_CIPHER)
label_quarantine_record = {
    "stage": "StageT3-A",
    "encrypted_group_label_rows": int(len(trusted_labels)),
    "plaintext_label_table_written_to_record_tree": False,
    "cipher_sha256": sha_bytes(LABEL_CIPHER),
    "key_persisted": False,
    "trusted_adapter_outcome_access": True,
    "analysis_outcome_access": False,
    "created_utc": now(),
}
label_quarantine_record["quarantine_record_sha256"] = sha_json(
    label_quarantine_record
)
write_json(P1 / "StageT3-A_Label_Quarantine_Record_v0.1.json", label_quarantine_record)
del trusted_labels, plaintext_label_json
gc.collect()

def image_fingerprint(path):
    data = Path(path).read_bytes()
    with Image.open(io.BytesIO(data)) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        width, height = image.size
        rgb = np.asarray(image, dtype=np.uint8)
        header = json.dumps(
            {"width": width, "height": height, "mode": "RGB"},
            sort_keys=True, separators=(",", ":"),
        ).encode("utf-8") + b"\0"
        pixel_sha = sha_bytes(header + rgb.tobytes(order="C"))
        gray = np.asarray(
            image.convert("L").resize((32, 32), Image.Resampling.LANCZOS),
            dtype=np.float32,
        )
        low = dctn(gray, type=2, norm="ortho")[:8, :8]
        threshold = float(np.median(low.reshape(-1)[1:]))
        bits = (low.reshape(-1) > threshold).astype(np.uint8)
        phash = 0
        for bit in bits:
            phash = (phash << 1) | int(bit)
    return {
        "raw_image_sha256": sha_bytes(data),
        "pixel_sha256": pixel_sha,
        "pixel_width": width,
        "pixel_height": height,
        "phash64": f"{phash:016x}",
    }

def phash_distance(left, right):
    return (int(str(left), 16) ^ int(str(right), 16)).bit_count()

def reference_fingerprints():
    rows = []
    preferred_names = [
        "Stage11D-R_Frozen_Exact_Image_Label_Group_Manifest_v0.1.csv",
        "StageT2-J_Existing_Dermoscopy_Reference_Fingerprints_v0.1.csv",
        "StageT2-J_MILK10K_Harmonised_Exact_Manifest_v0.1.csv",
        "StageT2-L_Selected_Image_Download_And_Dedup_Manifest_v0.1.csv",
    ]
    seen_paths = set()
    for name in preferred_names:
        for path in PROJECT_ROOT.rglob(name):
            if path in seen_paths or not path.is_file():
                continue
            seen_paths.add(path)
            try:
                frame = pd.read_csv(path)
            except Exception:
                continue
            if "pixel_sha256" not in frame.columns:
                continue
            modality = (
                frame["modality"].astype(str)
                if "modality" in frame.columns
                else pd.Series(
                    np.where(
                        frame.get("dataset_id", pd.Series("", index=frame.index))
                        .astype(str).str.contains("BUS", case=False),
                        "breast_ultrasound",
                        "dermoscopy",
                    ),
                    index=frame.index,
                )
            )
            for index, row in frame.iterrows():
                pixel = str(row.get("pixel_sha256", ""))
                phash = str(row.get("phash64", ""))
                if len(pixel) == 64:
                    rows.append({
                        "modality": modality.loc[index],
                        "pixel_sha256": pixel,
                        "phash64": phash if re.fullmatch(r"[0-9a-fA-F]{16}", phash) else "",
                        "reference_file": path.name,
                    })
    return pd.DataFrame(rows).drop_duplicates(["modality", "pixel_sha256"])

reference = reference_fingerprints()
fingerprint_rows = []
for index, row in tqdm(
    candidate_roster.reset_index().iterrows(),
    total=len(candidate_roster),
    desc="Fingerprinting locked-blind images",
):
    try:
        fingerprint_rows.append({
            "candidate_index": int(row["index"]),
            **image_fingerprint(row["image_path"]),
            "fingerprint_error": "",
        })
    except Exception as exc:
        fingerprint_rows.append({
            "candidate_index": int(row["index"]),
            "fingerprint_error": f"{type(exc).__name__}: {exc}",
        })
fingerprints = pd.DataFrame(fingerprint_rows).set_index("candidate_index")
for column in [
    "raw_image_sha256", "pixel_sha256", "pixel_width",
    "pixel_height", "phash64", "fingerprint_error",
]:
    candidate_roster[column] = fingerprints.reindex(candidate_roster.index)[column]

candidate_roster["dedup_status"] = "PENDING"
candidate_roster.loc[
    candidate_roster["pixel_sha256"].fillna("").eq(""),
    "dedup_status",
] = "HOLD_DECODE_OR_FINGERPRINT_FAILURE"

for modality, target_frame in candidate_roster.groupby("modality"):
    ref_frame = reference[reference["modality"].eq(modality)]
    accepted_pixels = set(ref_frame["pixel_sha256"].astype(str))
    accepted_phashes = [
        value for value in ref_frame["phash64"].astype(str)
        if re.fullmatch(r"[0-9a-fA-F]{16}", value)
    ]
    modality_indices = target_frame.sort_values(
        ["target", "group_id", "image_id"]
    ).index
    accepted_group_by_pixel = {}
    for index in modality_indices:
        if candidate_roster.loc[index, "dedup_status"] != "PENDING":
            continue
        row = candidate_roster.loc[index]
        pixel = str(row["pixel_sha256"])
        phash = str(row["phash64"])
        group = str(row["group_id"])
        if pixel in accepted_pixels:
            # Multiple official scans from the same OASBUD lesion are not removed
            # unless they are byte/pixel identical; cross-roster exact copies are.
            previous_group = accepted_group_by_pixel.get(pixel)
            status = (
                "KEEP_SAME_GROUP_DUPLICATE_SCAN"
                if previous_group == group
                else "EXCLUDE_CROSS_ROSTER_OR_CROSS_GROUP_EXACT_DUPLICATE"
            )
        else:
            minimum_distance = min(
                (phash_distance(phash, ref) for ref in accepted_phashes),
                default=65,
            )
            status = (
                "HOLD_CROSS_ROSTER_PHASH_NEAR_COPY"
                if minimum_distance <= PHASH_MAX_DISTANCE
                else "KEEP_UNIQUE"
            )
        candidate_roster.loc[index, "dedup_status"] = status
        if status.startswith("KEEP"):
            accepted_pixels.add(pixel)
            accepted_phashes.append(phash)
            accepted_group_by_pixel[pixel] = group

retained_roster = candidate_roster[
    candidate_roster["dedup_status"].str.startswith("KEEP")
].copy()
retained_groups = set(retained_roster["group_id"])
retained_roster = retained_roster.sort_values(
    ["target", "group_id", "image_id"]
).reset_index(drop=True)

readiness_rows = []
adapter_lookup = {
    audit["target"]: audit for audit in [busi_audit, oasbud_audit, derm_audit]
}
for target in ["BUSI_CAIRO_2019", "OASBUD_2017", "DERM7PT_2019"]:
    frame = retained_roster[retained_roster["target"].eq(target)]
    modalities = frame["modality"].unique().tolist() if len(frame) else []
    total_groups = int(frame["group_id"].nunique()) if len(frame) else 0
    readiness_rows.append({
        "target": target,
        "modality": modalities[0] if modalities else (
            "dermoscopy" if target == "DERM7PT_2019" else "breast_ultrasound"
        ),
        "adapter_status": adapter_lookup[target]["status"],
        "retained_images": len(frame),
        "retained_groups": total_groups,
        "primary_budget32_ready": total_groups >= 40,
        "budget64_ready": total_groups >= 64,
        "budget128_ready": total_groups >= 128,
        "replacement_allowed": False,
    })
readiness = pd.DataFrame(readiness_rows)
score_ready_targets = readiness.loc[
    readiness["primary_budget32_ready"], "target"
].tolist()

write_csv(P2 / "StageT3-A_All_Blind_Image_Dedup_Adjudication_v0.1.csv", candidate_roster)
write_csv(P2 / "StageT3-A_Frozen_Outcome_Free_Roster_v0.1.csv", retained_roster)
write_csv(P2 / "StageT3-A_Target_Availability_And_Readiness_v0.1.csv", readiness)
write_csv(P2 / "StageT3-A_Reference_Fingerprint_Audit_v0.1.csv", reference)

assert "DERM7PT_2019" in score_ready_targets, (
    "Derm7pt official files were found, but the endpoint/grouping adapter did not "
    "produce at least 40 retained groups. Inspect StageT3-A_Trusted_Adapter_Audits."
)

print("Outcome-free target readiness:")
display(readiness)
print("Score-ready locked targets:", score_ready_targets)
print("Analysis outcomes accessed:", False)



# Frozen representation, source-axis scoring, presealed witness manifests, and encrypted outcome broker
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from torchvision.models import resnet50, ResNet50_Weights

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
        digest.update(name.encode("utf-8") + b"\0")
        array = tensor.detach().cpu().contiguous().numpy()
        digest.update(str(array.dtype).encode("utf-8") + b"\0")
        digest.update(np.asarray(array.shape, dtype=np.int64).tobytes())
        digest.update(array.tobytes(order="C"))
    return digest.hexdigest()

assert model_state_sha256(MODEL) == MODEL_STATE_SHA256

class BlindImageDataset(Dataset):
    def __init__(self, frame):
        self.frame = frame.reset_index(drop=True)
    def __len__(self):
        return len(self.frame)
    def __getitem__(self, index):
        row = self.frame.iloc[index]
        data = Path(row["image_path"]).read_bytes()
        assert sha_bytes(data) == row["raw_image_sha256"]
        with Image.open(io.BytesIO(data)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            tensor = TRANSFORM(image)
        return tensor, index

def load_axis(source, path):
    with np.load(path, allow_pickle=False) as axis:
        keys = set(axis.files)
        identity_key = "dataset_id" if "dataset_id" in keys else "source"
        identity = str(axis[identity_key])
        assert identity == source, f"Axis identity mismatch: {source} / {identity}"
        if {"coefficient_raw", "intercept_raw"}.issubset(keys):
            coefficient = np.asarray(axis["coefficient_raw"], dtype=np.float64)
            intercept = float(axis["intercept_raw"])
            schema = "STAGE11_STYLE"
        elif {"raw_coefficient", "raw_intercept"}.issubset(keys):
            coefficient = np.asarray(axis["raw_coefficient"], dtype=np.float64)
            intercept = float(axis["raw_intercept"])
            schema = "STAGE8_STYLE"
        else:
            raise KeyError(f"Unknown axis schema: {path}")
        if "model_state_sha256" in keys:
            assert str(axis["model_state_sha256"]) == MODEL_STATE_SHA256
    assert coefficient.shape == (2048,)
    assert np.isfinite(coefficient).all() and np.isfinite(intercept)
    return coefficient, intercept, schema

axis_parameters = {}
axis_audit_rows = []
for source, path in axis_paths.items():
    coefficient, intercept, schema = load_axis(source, path)
    axis_parameters[source] = (coefficient, intercept)
    axis_audit_rows.append({
        "source": source,
        "axis_path": str(path),
        "axis_sha256": sha_file(path),
        "schema": schema,
        "source_validation_auc": SOURCE_VALIDATION_AUC[source],
        "model_state_sha256": MODEL_STATE_SHA256,
    })
axis_audit = pd.DataFrame(axis_audit_rows)
write_csv(P3 / "StageT3-A_Frozen_Source_Axis_Audit_v0.1.csv", axis_audit)

embedding_rows = []
unit_score_rows = []
for target in score_ready_targets:
    frame = retained_roster[retained_roster["target"].eq(target)].copy()
    frame = frame.sort_values(["group_id", "image_id"]).reset_index(drop=True)
    loader = DataLoader(
        BlindImageDataset(frame),
        batch_size=24,
        shuffle=False,
        num_workers=2,
        pin_memory=False,
    )
    chunks = []
    for images, indices in tqdm(loader, desc=f"Embedding {target}"):
        with torch.inference_mode():
            features = F.normalize(MODEL(images.to(DEVICE)), p=2, dim=1)
        chunks.append(features.cpu().numpy().astype(np.float32))
    embeddings = np.concatenate(chunks, axis=0)
    assert embeddings.shape == (len(frame), 2048)
    norm_error = float(np.max(np.abs(np.linalg.norm(embeddings, axis=1) - 1.0)))

    embedding_path = P3 / f"{target}_Frozen_ResNet50_V2_Unit_Embeddings_v0.1.npy"
    image_ids_path = P3 / f"{target}_Embedding_Unit_IDs_v0.1.npy"
    np.save(embedding_path, embeddings, allow_pickle=False)
    np.save(
        image_ids_path,
        np.asarray(frame["unit_id"].astype(str).tolist(), dtype=np.str_),
        allow_pickle=False,
    )

    sources = SOURCE_BY_MODALITY[frame["modality"].iloc[0]]
    logits = {}
    for source in sources:
        coefficient, intercept = axis_parameters[source]
        logits[source] = embeddings.astype(np.float64) @ coefficient + intercept

    for row_index, row in frame.iterrows():
        common = {
            "target": target,
            "provider": row["provider"],
            "modality": row["modality"],
            "task": row["task"],
            "group_id": row["group_id"],
            "image_id": row["image_id"],
            "unit_id": row["unit_id"],
        }
        for source in sources:
            unit_score_rows.append({
                **common,
                "source": source,
                "edge_id": f"{source}__TO__{target}",
                "logit": float(logits[source][row_index]),
                "source_validation_auc": SOURCE_VALIDATION_AUC[source],
            })
    embedding_rows.append({
        "target": target,
        "modality": frame["modality"].iloc[0],
        "images": len(frame),
        "groups": frame["group_id"].nunique(),
        "dimension": 2048,
        "embedding_sha256": sha_file(embedding_path),
        "unit_ids_sha256": sha_file(image_ids_path),
        "model_state_sha256": MODEL_STATE_SHA256,
        "maximum_l2_norm_error": norm_error,
        "device": "cpu",
    })
    del embeddings, chunks
    gc.collect()

unit_scores = pd.DataFrame(unit_score_rows)
embedding_manifest = pd.DataFrame(embedding_rows)
write_csv(P3 / "StageT3-A_Frozen_Embedding_Manifest_v0.1.csv", embedding_manifest)
write_csv(P3 / "StageT3-A_Frozen_Unit_Source_Logits_v0.1.csv", unit_scores)

group_scores_long = (
    unit_scores.groupby(
        ["target", "provider", "modality", "task", "group_id",
         "source", "edge_id", "source_validation_auc"],
        as_index=False,
    )
    .agg(
        logit=("logit", "mean"),
        contributing_images=("unit_id", "nunique"),
    )
)
write_csv(P3 / "StageT3-A_Frozen_Group_Source_Logits_v0.1.csv", group_scores_long)

def prepare_target_table(frame):
    wide = frame.pivot(
        index="group_id", columns="source", values="logit"
    ).reset_index()
    meta = frame[
        ["group_id", "target", "provider", "modality", "task"]
    ].drop_duplicates("group_id")
    return wide.merge(meta, on="group_id", validate="one_to_one")

target_tables = {}
for target, frame in group_scores_long.groupby("target"):
    table = prepare_target_table(frame)
    sources = SOURCE_BY_MODALITY[table["modality"].iloc[0]]
    assert all(source in table.columns for source in sources)
    table = table.sort_values("group_id").reset_index(drop=True)
    target_tables[target] = (table, sources)

def choose_groups(n, budget, rng, design, active=True):
    if not active:
        return rng.choice(n, budget, replace=False)
    anchors = max(2, int(np.ceil(budget * 0.25)))
    selected = list(rng.choice(n, anchors, replace=False))
    used = np.zeros(n, bool)
    used[selected] = True
    inverse = np.linalg.inv(
        np.eye(design.shape[1]) + design[selected].T @ design[selected]
    )
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

manifest_rows = []
for target, (table, sources) in target_tables.items():
    raw = table[sources].to_numpy(float)
    x = (raw - raw.mean(0)) / (raw.std(0) + 1e-9)
    groups = table["group_id"].astype(str).to_numpy()
    design = np.c_[np.ones(len(groups)), x]
    for budget in BUDGETS:
        if len(groups) < budget:
            continue
        for replicate in range(N_REPLICATES):
            base_seed = SEED + replicate * 1009 + budget * 17 + sum(map(ord, target))
            for design_name, active, offset in [
                ("random", False, 0),
                ("active_d_optimal", True, 1),
            ]:
                selected = choose_groups(
                    len(groups),
                    budget,
                    np.random.default_rng(base_seed + offset),
                    design,
                    active=active,
                )
                group_ids = groups[selected].tolist()
                payload = {
                    "target": target,
                    "budget": budget,
                    "replicate": replicate,
                    "design": design_name,
                    "group_ids": group_ids,
                }
                manifest_rows.append({
                    "target": target,
                    "modality": table["modality"].iloc[0],
                    "budget": budget,
                    "replicate": replicate,
                    "design": design_name,
                    "group_count": len(group_ids),
                    "group_ids_json": json.dumps(group_ids, separators=(",", ":")),
                    "manifest_sha256": sha_json(payload),
                })

witness_manifests = pd.DataFrame(manifest_rows).sort_values(
    ["target", "budget", "replicate", "design"]
).reset_index(drop=True)
manifest_path = P3 / "StageT3-A_All_Precommitted_Witness_Manifests_v0.1.csv"
write_csv(manifest_path, witness_manifests)
manifest_seal = {
    "stage": "StageT3-A",
    "event": "ALL_WITNESS_MANIFESTS_FROZEN_BEFORE_BROKER_LABEL_ACCESS",
    "targets": sorted(target_tables),
    "budgets": BUDGETS,
    "replicates": N_REPLICATES,
    "manifest_rows": len(witness_manifests),
    "manifest_file_sha256": sha_file(manifest_path),
    "analysis_outcomes_accessed": False,
    "full_outcomes_unsealed": False,
    "sealed_utc": now(),
}
manifest_seal["witness_manifest_seal_sha256"] = sha_json(manifest_seal)
write_json(P3 / "StageT3-A_Witness_Manifest_Seal_v0.1.json", manifest_seal)

manifest_lookup = {
    (row.target, int(row.budget), int(row.replicate), row.design): {
        "group_ids": json.loads(row.group_ids_json),
        "manifest_sha256": row.manifest_sha256,
    }
    for row in witness_manifests.itertuples()
}

class EncryptedOutcomeBroker:
    _phase_order = {
        "SEALED_NO_ACCESS": 0,
        "BUDGET8": 1,
        "PRIMARY32": 2,
        "REMAINING_SECONDARY": 3,
        "FINAL_UNSEAL": 4,
    }

    def __init__(self, cipher_bytes, key, manifest_lookup):
        self._cipher = bytes(cipher_bytes)
        self._fernet = Fernet(key)
        self._manifest_lookup = manifest_lookup
        self._phase = "SEALED_NO_ACCESS"
        self._ledger = []

    def set_phase(self, phase):
        assert phase in self._phase_order
        assert self._phase_order[phase] >= self._phase_order[self._phase]
        self._phase = phase

    def _mapping(self):
        records = json.loads(
            self._fernet.decrypt(self._cipher).decode("utf-8")
        )
        return {
            (str(row["target"]), str(row["group_id"])): int(row["label"])
            for row in records
        }

    def request_manifest(self, target, budget, replicate, design):
        allowed = {
            "BUDGET8": {8},
            "PRIMARY32": {32},
            "REMAINING_SECONDARY": {16, 64, 128},
        }
        assert self._phase in allowed, f"Broker phase does not permit witness access: {self._phase}"
        assert int(budget) in allowed[self._phase]
        key = (str(target), int(budget), int(replicate), str(design))
        assert key in self._manifest_lookup
        manifest = self._manifest_lookup[key]
        mapping = self._mapping()
        labels = {
            group: mapping[(str(target), str(group))]
            for group in manifest["group_ids"]
        }
        self._ledger.append({
            "access_type": "WITNESS_MANIFEST",
            "phase": self._phase,
            "target": target,
            "budget": int(budget),
            "replicate": int(replicate),
            "design": design,
            "groups_returned": len(labels),
            "manifest_sha256": manifest["manifest_sha256"],
            "accessed_utc": now(),
        })
        return labels

    def final_unseal(self, forecast_seal_path, primary_seal_path):
        assert self._phase == "FINAL_UNSEAL"
        assert Path(forecast_seal_path).is_file()
        assert Path(primary_seal_path).is_file()
        mapping = self._mapping()
        self._ledger.append({
            "access_type": "FINAL_FULL_OUTCOME_UNSEAL",
            "phase": self._phase,
            "target": "ALL_AVAILABLE_SENTINELS",
            "budget": "",
            "replicate": "",
            "design": "",
            "groups_returned": len(mapping),
            "manifest_sha256": "",
            "accessed_utc": now(),
        })
        return pd.DataFrame([
            {"target": target, "group_id": group, "label": label}
            for (target, group), label in mapping.items()
        ])

    def ledger(self):
        return pd.DataFrame(self._ledger)

broker = EncryptedOutcomeBroker(LABEL_CIPHER, LABEL_KEY, manifest_lookup)
print("Frozen embeddings and all witness manifests complete.")
print("Witness labels accessed:", False)
print("Full outcomes unsealed:", False)



# Frozen audit methods, sequential witness access, evidence forecast seal, and primary prediction seal
def weighted_auc(scores, probabilities):
    scores = np.asarray(scores, float)
    positive = np.asarray(probabilities, float)
    negative = 1.0 - positive
    denominator = positive.sum() * negative.sum()
    if denominator <= 0:
        return np.nan
    order = np.argsort(scores, kind="mergesort")
    scores = scores[order]
    positive = positive[order]
    negative = negative[order]
    numerator = 0.0
    negatives_before = 0.0
    starts = np.r_[0, np.flatnonzero(np.diff(scores)) + 1]
    ends = np.r_[starts[1:], len(scores)]
    for start, end in zip(starts, ends):
        positive_here = positive[start:end].sum()
        negative_here = negative[start:end].sum()
        numerator += positive_here * (negatives_before + 0.5 * negative_here)
        negatives_before += negative_here
    return float(numerator / denominator)

def crossfitted_logistic_probabilities(x, y, groups, witness):
    if len(np.unique(y[witness])) < 2:
        return None
    model = LogisticRegression(
        C=RIDGE_C, solver="lbfgs", max_iter=3000
    ).fit(x[witness], y[witness])
    probabilities = model.predict_proba(x)[:, 1]
    local = np.flatnonzero(witness)
    local_groups = groups[witness]
    folds = min(5, len(pd.unique(local_groups)))
    if folds >= 2:
        splitter = GroupKFold(folds)
        for fit_idx, score_idx in splitter.split(
            x[witness], y[witness], local_groups
        ):
            if len(np.unique(y[witness][fit_idx])) < 2:
                continue
            fold = LogisticRegression(
                C=RIDGE_C, solver="lbfgs", max_iter=3000
            ).fit(x[witness][fit_idx], y[witness][fit_idx])
            probabilities[local[score_idx]] = fold.predict_proba(
                x[witness][score_idx]
            )[:, 1]
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
    means = np.vstack([
        x[witness & (y == klass)].mean(0) for klass in (0, 1)
    ])
    covariance = (
        np.cov(x.T)
        if dimension > 1
        else np.array([[np.var(x[:, 0])]])
    )
    covariance = np.atleast_2d(covariance) + np.eye(dimension) * 1e-3
    prior = np.clip(np.mean(y[witness]), 0.05, 0.95)
    responsibilities = np.zeros((len(x), 2))
    for _ in range(max_iter):
        old = np.r_[means.ravel(), covariance.ravel(), prior]
        log_joint = np.c_[
            np.log(1 - prior) + gaussian_logpdf(x, means[0], covariance),
            np.log(prior) + gaussian_logpdf(x, means[1], covariance),
        ]
        responsibilities[:] = np.exp(
            log_joint - logsumexp(log_joint, axis=1, keepdims=True)
        )
        responsibilities[witness] = np.c_[
            1 - y[witness], y[witness]
        ]
        weights = responsibilities.sum(0)
        means = responsibilities.T @ x / weights[:, None]
        covariance = np.zeros((dimension, dimension))
        for klass in (0, 1):
            centered = x - means[klass]
            covariance += (
                centered * responsibilities[:, [klass]]
            ).T @ centered
        covariance /= len(x)
        covariance = (
            0.8 * covariance
            + 0.2 * np.diag(np.diag(covariance))
            + np.eye(dimension) * 1e-3
        )
        prior = np.clip(weights[1] / len(x), 0.01, 0.99)
        new = np.r_[means.ravel(), covariance.ravel(), prior]
        if np.max(np.abs(new - old)) < tol:
            break
    log_joint = np.c_[
        np.log(1 - prior) + gaussian_logpdf(x, means[0], covariance),
        np.log(prior) + gaussian_logpdf(x, means[1], covariance),
    ]
    return np.exp(
        log_joint - logsumexp(log_joint, axis=1, keepdims=True)
    )[:, 1]

def balance_features(group_x):
    return np.column_stack([group_x, group_x ** 2])

def entropy_balance_weights(
    sample_phi, target_phi, ridge=BALANCE_RIDGE, clip=WEIGHT_CLIP
):
    sample_phi = np.asarray(sample_phi, float)
    target_phi = np.asarray(target_phi, float)
    target_mean = target_phi.mean(0)
    center = sample_phi.mean(0)
    scale = sample_phi.std(0) + 1e-6
    standardized = (sample_phi - center) / scale
    target_standardized = (target_mean - center) / scale

    def objective(lam):
        raw = np.clip(standardized @ lam, -30, 30)
        shifted = raw - raw.max()
        weights = np.exp(shifted)
        weights /= weights.sum()
        value = (
            np.log(np.exp(raw).mean())
            - target_standardized @ lam
            + 0.5 * ridge * np.sum(lam ** 2)
        )
        gradient = (
            weights @ standardized
            - target_standardized
            + ridge * lam
        )
        return value, gradient

    fit = minimize(
        lambda value: objective(value),
        np.zeros(standardized.shape[1]),
        jac=True,
        method="L-BFGS-B",
    )
    valid = bool(fit.success and np.all(np.isfinite(fit.x)))
    lam = fit.x if valid else np.zeros(standardized.shape[1])
    raw = np.clip(standardized @ lam, -30, 30)
    raw -= raw.max()
    weights = np.exp(raw)
    weights /= weights.mean()
    weights = np.clip(weights, clip[0], clip[1])
    weighted_mean = np.average(sample_phi, axis=0, weights=weights)
    raw_scale = target_phi.std(0) + 1e-6
    residual = float(
        np.max(np.abs((weighted_mean - target_mean) / raw_scale))
    )
    ess = float(weights.sum() ** 2 / np.sum(weights ** 2))
    return weights, {
        "optimizer_success": valid,
        "weight_min": float(weights.min()),
        "weight_max": float(weights.max()),
        "weight_ess": ess,
        "balance_residual_max_standardized": residual,
    }

def candidate_posterior(
    x, y, groups, unique_groups, selected_indices, balanced
):
    selected_groups = unique_groups[selected_indices]
    witness = np.isin(groups, selected_groups)
    if len(np.unique(y[witness])) < 2:
        return None, None
    group_x = np.asarray([
        x[groups == group].mean(0) for group in unique_groups
    ])
    phi = balance_features(group_x)
    group_lookup = {
        group: index for index, group in enumerate(unique_groups)
    }
    if balanced:
        full_weight, diagnostics = entropy_balance_weights(
            phi[selected_indices], phi
        )
        lookup = dict(zip(selected_groups, full_weight))
        unit_weight = np.asarray(
            [lookup[group] for group in groups[witness]], float
        )
    else:
        diagnostics = {
            "optimizer_success": True,
            "weight_min": 1.0,
            "weight_max": 1.0,
            "weight_ess": float(len(selected_groups)),
            "balance_residual_max_standardized": np.nan,
        }
        unit_weight = np.ones(witness.sum())

    model = LogisticRegression(
        C=RIDGE_C, solver="lbfgs", max_iter=3000
    ).fit(x[witness], y[witness], sample_weight=unit_weight)
    eta = model.predict_proba(x)[:, 1]

    local = np.flatnonzero(witness)
    local_groups = groups[witness]
    folds = min(5, len(pd.unique(local_groups)))
    if folds >= 2:
        splitter = GroupKFold(folds)
        for train, test in splitter.split(
            x[witness], y[witness], local_groups
        ):
            if len(np.unique(y[witness][train])) < 2:
                continue
            train_groups = np.asarray(pd.unique(local_groups[train]))
            if balanced:
                indices = np.asarray([
                    group_lookup[group] for group in train_groups
                ])
                fold_weight, _ = entropy_balance_weights(
                    phi[indices], phi
                )
                lookup = dict(zip(train_groups, fold_weight))
                train_weight = np.asarray([
                    lookup[group] for group in local_groups[train]
                ], float)
            else:
                train_weight = np.ones(len(train))
            fold = LogisticRegression(
                C=RIDGE_C, solver="lbfgs", max_iter=3000
            ).fit(
                x[witness][train],
                y[witness][train],
                sample_weight=train_weight,
            )
            eta[local[test]] = fold.predict_proba(
                x[witness][test]
            )[:, 1]
    return eta, diagnostics

def group_brier(y, eta, groups, selected_groups):
    return np.asarray([
        np.mean((y[groups == group] - eta[groups == group]) ** 2)
        for group in selected_groups
    ], float)

def manifest_indices(target, budget, replicate, design, groups):
    manifest = manifest_lookup[
        (target, int(budget), int(replicate), design)
    ]
    lookup = {group: index for index, group in enumerate(groups)}
    return np.asarray([lookup[group] for group in manifest["group_ids"]])

def labels_array(groups, label_mapping):
    y = np.zeros(len(groups), dtype=int)
    witness = np.zeros(len(groups), dtype=bool)
    lookup = {group: index for index, group in enumerate(groups)}
    for group, label in label_mapping.items():
        index = lookup[group]
        y[index] = int(label)
        witness[index] = True
    return y, witness

def run_wave(budget, phase, requested_methods):
    result_rows = []
    diagnostic_rows = []
    skip_rows = []
    need_random = any(
        method.startswith("random_") for method in requested_methods
    ) or "random_direct" in requested_methods
    need_active = any(
        method in requested_methods for method in [
            "active_direct", "amw_ddet", "amw_u",
            "amw_cb2", "ra_cb_amw_ddet",
        ]
    )

    for target, (data, sources) in target_tables.items():
        groups = data["group_id"].astype(str).to_numpy()
        unique_groups = groups.copy()
        if len(groups) < budget:
            for replicate in range(N_REPLICATES):
                skip_rows.append({
                    "target": target, "budget": budget,
                    "replicate": replicate, "stage": phase,
                    "reason": "insufficient_independent_groups",
                })
            continue

        raw = data[sources].to_numpy(float)
        x = (raw - raw.mean(0)) / (raw.std(0) + 1e-9)

        for replicate in range(N_REPLICATES):
            random_labels = None
            active_labels = None
            if need_random:
                random_labels = broker.request_manifest(
                    target, budget, replicate, "random"
                )
            if need_active:
                active_labels = broker.request_manifest(
                    target, budget, replicate, "active_d_optimal"
                )

            eta_random = None
            eta_gmm = None
            eta_active = None
            eta_u = None
            eta_cb = None
            eta_ra = None
            random_witness = np.zeros(len(groups), bool)
            active_witness = np.zeros(len(groups), bool)
            y_random = np.zeros(len(groups), int)
            y_active = np.zeros(len(groups), int)
            select_cb = False

            if need_random:
                y_random, random_witness = labels_array(
                    groups, random_labels
                )
                if len(np.unique(y_random[random_witness])) < 2:
                    skip_rows.append({
                        "target": target, "budget": budget,
                        "replicate": replicate, "stage": "random",
                        "reason": "single_witness_class",
                    })
                else:
                    eta_random = crossfitted_logistic_probabilities(
                        x, y_random, groups, random_witness
                    )
                    try:
                        eta_gmm = semisupervised_gmm(
                            x, y_random, random_witness
                        )
                    except Exception:
                        eta_gmm = None

            if need_active:
                y_active, active_witness = labels_array(
                    groups, active_labels
                )
                if len(np.unique(y_active[active_witness])) < 2:
                    skip_rows.append({
                        "target": target, "budget": budget,
                        "replicate": replicate, "stage": "active",
                        "reason": "single_witness_class",
                    })
                else:
                    eta_active = crossfitted_logistic_probabilities(
                        x, y_active, groups, active_witness
                    )
                    selected_active = manifest_indices(
                        target, budget, replicate,
                        "active_d_optimal", groups
                    )
                    eta_u, diag_u = candidate_posterior(
                        x, y_active, groups, unique_groups,
                        selected_active, False
                    )
                    eta_cb, diag_cb = candidate_posterior(
                        x, y_active, groups, unique_groups,
                        selected_active, True
                    )
                    selected_groups = unique_groups[selected_active]
                    cb_admissible = bool(
                        eta_cb is not None
                        and diag_cb is not None
                        and diag_cb["optimizer_success"]
                        and diag_cb["weight_ess"] >= MIN_BALANCE_ESS
                    )
                    loss_u = (
                        group_brier(
                            y_active, eta_u, groups, selected_groups
                        )
                        if eta_u is not None
                        else np.full(len(selected_groups), np.inf)
                    )
                    loss_cb = (
                        group_brier(
                            y_active, eta_cb, groups, selected_groups
                        )
                        if eta_cb is not None
                        else np.full(len(selected_groups), np.inf)
                    )
                    select_cb = bool(
                        cb_admissible
                        and loss_cb.mean() < loss_u.mean()
                    )
                    eta_ra = eta_cb if select_cb else eta_u
                    if diag_cb is not None:
                        diagnostic_rows.append({
                            "target": target,
                            "modality": data["modality"].iloc[0],
                            "budget": budget,
                            "replicate": replicate,
                            "selected_candidate": (
                                "AMW-CB2" if select_cb else "AMW-U"
                            ),
                            "balance_selected": select_cb,
                            "cb_admissible": cb_admissible,
                            "cv_brier_amw_u": float(loss_u.mean()),
                            "cv_brier_amw_cb2": float(loss_cb.mean()),
                            "cv_brier_difference_cb2_minus_u": float(
                                loss_cb.mean() - loss_u.mean()
                            ),
                            **diag_cb,
                        })

            eta_by_method = {
                "random_logistic_plugin": eta_random,
                "random_joint_gmm": eta_gmm,
                "amw_ddet": eta_active,
                "amw_u": eta_u,
                "amw_cb2": eta_cb,
                "ra_cb_amw_ddet": eta_ra,
            }

            for source_index, source in enumerate(sources):
                common = {
                    "target": target,
                    "provider": data["provider"].iloc[0],
                    "modality": data["modality"].iloc[0],
                    "source": source,
                    "edge_id": f"{source}__TO__{target}",
                    "budget": budget,
                    "replicate": replicate,
                    "phase": phase,
                    "source_validation_auc": SOURCE_VALIDATION_AUC[source],
                    "retention_threshold": (
                        SOURCE_VALIDATION_AUC[source] - 0.15
                    ),
                    "independent_groups": len(groups),
                }
                if (
                    "random_direct" in requested_methods
                    and random_witness.any()
                    and len(np.unique(y_random[random_witness])) == 2
                ):
                    result_rows.append({
                        **common,
                        "method": "random_direct",
                        "estimate_auc": float(
                            roc_auc_score(
                                y_random[random_witness],
                                x[random_witness, source_index],
                            )
                        ),
                        "witness_groups": int(random_witness.sum()),
                        "witness_prevalence": float(
                            y_random[random_witness].mean()
                        ),
                        "balance_selected": False,
                    })
                if (
                    "active_direct" in requested_methods
                    and active_witness.any()
                    and len(np.unique(y_active[active_witness])) == 2
                ):
                    result_rows.append({
                        **common,
                        "method": "active_direct",
                        "estimate_auc": float(
                            roc_auc_score(
                                y_active[active_witness],
                                x[active_witness, source_index],
                            )
                        ),
                        "witness_groups": int(active_witness.sum()),
                        "witness_prevalence": float(
                            y_active[active_witness].mean()
                        ),
                        "balance_selected": False,
                    })
                for method in requested_methods:
                    if method in {"random_direct", "active_direct"}:
                        continue
                    eta = eta_by_method.get(method)
                    if eta is None:
                        continue
                    witness = (
                        random_witness
                        if method.startswith("random_")
                        else active_witness
                    )
                    y_witness = (
                        y_random if method.startswith("random_")
                        else y_active
                    )
                    result_rows.append({
                        **common,
                        "method": method,
                        "estimate_auc": weighted_auc(
                            x[:, source_index], eta
                        ),
                        "witness_groups": int(witness.sum()),
                        "witness_prevalence": float(
                            y_witness[witness].mean()
                        ),
                        "balance_selected": (
                            select_cb
                            if method == "ra_cb_amw_ddet"
                            else False
                        ),
                    })
        print("Completed blind witness wave:", target, "budget", budget)

    return (
        pd.DataFrame(result_rows),
        pd.DataFrame(diagnostic_rows),
        pd.DataFrame(skip_rows),
    )

LEGAL_B8 = [
    "random_direct",
    "random_logistic_plugin",
    "random_joint_gmm",
    "active_direct",
    "amw_ddet",
]
PRIMARY_METHODS = [
    "random_direct",
    "random_logistic_plugin",
    "random_joint_gmm",
    "active_direct",
    "amw_ddet",
    "amw_u",
    "amw_cb2",
    "ra_cb_amw_ddet",
]

# Phase 1: budget-8 target-expected evidence forecast.
broker.set_phase("BUDGET8")
budget8_results, budget8_diagnostics, budget8_skips = run_wave(
    8, "BUDGET8_EVIDENCE_FORECAST", LEGAL_B8
)
write_csv(P4 / "StageT3-A_Budget8_Blind_Witness_Estimates_v0.1.csv", budget8_results)
write_csv(P4 / "StageT3-A_Budget8_Witness_Diagnostics_v0.1.csv", budget8_diagnostics)
write_csv(P4 / "StageT3-A_Budget8_Skips_v0.1.csv", budget8_skips)

pivot = budget8_results.pivot_table(
    index=[
        "target", "provider", "modality", "replicate", "edge_id"
    ],
    columns="method",
    values="estimate_auc",
).reset_index()
for method in LEGAL_B8:
    if method not in pivot.columns:
        pivot[method] = np.nan
complete_pivot = pivot.dropna(subset=LEGAL_B8).copy()
complete_pivot["cross_method_sd"] = complete_pivot[
    LEGAL_B8
].std(axis=1)
replicate_signature = (
    complete_pivot.groupby(
        ["target", "provider", "modality", "replicate"],
        as_index=False,
    )
    .agg(pilot_disagreement=("cross_method_sd", "mean"))
)
target_signature = (
    replicate_signature.groupby(
        ["target", "provider", "modality"], as_index=False
    )
    .agg(
        pilot_disagreement_index=(
            "pilot_disagreement", "median"
        ),
        pilot_disagreement_iqr=(
            "pilot_disagreement",
            lambda values: float(
                np.quantile(values, 0.75)
                - np.quantile(values, 0.25)
            ),
        ),
        usable_budget8_replicates=("replicate", "nunique"),
    )
)
group_counts = {
    target: len(table)
    for target, (table, sources) in target_tables.items()
}
target_signature["independent_groups"] = (
    target_signature["target"].map(group_counts).astype(int)
)
target_signature["log2_groups"] = np.log2(
    target_signature["independent_groups"].astype(float)
)
assert (
    target_signature["usable_budget8_replicates"] >= 50
).all(), "Too few usable budget-8 replicates for frozen forecast"

raw_intercept = float(t2m_model["raw_intercept"])
raw_coefficients = np.asarray(
    t2m_model["raw_coefficients"], float
)
sigma = float(t2m_model["sigma"])
selected_features = list(t2m_model["selected_features"])
assert selected_features == ["pilot_disagreement_index"]
mu = (
    raw_intercept
    + target_signature[selected_features].to_numpy(float)
    @ raw_coefficients
)
target_signature["mu_log2_budget"] = mu
target_signature["sigma"] = sigma

boundaries = np.array([-np.inf, 3, 4, 5, 6, 7, np.inf], float)
probability_names = [
    "probability_le_8",
    "probability_8_to_16",
    "probability_16_to_32",
    "probability_32_to_64",
    "probability_64_to_128",
    "probability_gt_128",
]
for category, name in enumerate(probability_names):
    lower = boundaries[category]
    upper = boundaries[category + 1]
    lower_cdf = (
        np.zeros(len(mu))
        if np.isneginf(lower)
        else norm.cdf((lower - mu) / sigma)
    )
    upper_cdf = (
        np.ones(len(mu))
        if np.isposinf(upper)
        else norm.cdf((upper - mu) / sigma)
    )
    target_signature[name] = upper_cdf - lower_cdf

with zipfile.ZipFile(t2mn_bundle) as archive:
    feature_member = (
        "StageT2-M/01_Target_Features_And_Interval_Truth/"
        "StageT2-M_Target_Feature_And_Interval_Truth_Table_v0.1.csv"
    )
    training_features = pd.read_csv(archive.open(feature_member))

support_features = list(t2m_support["support_features"])
center = np.asarray(t2m_support["robust_center"], float)
scale = np.asarray(t2m_support["robust_scale"], float)
training_scaled = (
    training_features[support_features].to_numpy(float) - center
) / scale
target_scaled = (
    target_signature[support_features].to_numpy(float) - center
) / scale
target_signature["support_distance"] = [
    float(
        np.sqrt(
            ((training_scaled - row) ** 2).sum(axis=1)
        ).min()
    )
    for row in target_scaled
]
target_signature["distance_threshold"] = float(
    t2m_support["nearest_neighbour_distance_threshold"]
)
target_signature["disagreement_lower_envelope"] = float(
    t2m_support["disagreement_lower_envelope"]
)
target_signature["disagreement_upper_envelope"] = float(
    t2m_support["disagreement_upper_envelope"]
)
outside = (
    target_signature["support_distance"]
    > target_signature["distance_threshold"]
) | (
    target_signature["pilot_disagreement_index"]
    < target_signature["disagreement_lower_envelope"]
) | (
    target_signature["pilot_disagreement_index"]
    > target_signature["disagreement_upper_envelope"]
)
target_signature["support_status"] = np.where(
    outside, "OUT_OF_SUPPORT_ABSTAIN", "SUPPORTED"
)
target_signature["actionable_budget_recommendation"] = False

bootstrap = pd.read_csv(t2m_bootstrap_path)
bootstrap = bootstrap[
    bootstrap["converged"].astype(str).str.lower().isin(
        ["true", "1"]
    )
]
assert len(bootstrap) >= 950
for index, row in target_signature.iterrows():
    bootstrap_mu = bootstrap["raw_intercept"].to_numpy(float)
    bootstrap_mu = bootstrap_mu + (
        bootstrap[
            "raw_beta__pilot_disagreement_index"
        ].to_numpy(float)
        * float(row["pilot_disagreement_index"])
    )
    target_signature.loc[index, "bootstrap_mu_q05"] = float(
        np.quantile(bootstrap_mu, 0.05)
    )
    target_signature.loc[index, "bootstrap_mu_q50"] = float(
        np.quantile(bootstrap_mu, 0.50)
    )
    target_signature.loc[index, "bootstrap_mu_q95"] = float(
        np.quantile(bootstrap_mu, 0.95)
    )

forecast_path = P4 / "StageT3-A_Prospective_Evidence_Forecasts_v0.1.csv"
write_csv(forecast_path, target_signature)
forecast_seal = {
    "stage": "StageT3-A",
    "event": "EVIDENCE_FORECAST_SEALED_BEFORE_PRIMARY32_AND_LATER_WAVES",
    "parent_model_freeze_sha256": EXPECTED["t2m_model"],
    "parent_support_freeze_sha256": EXPECTED["t2m_support"],
    "witness_manifest_seal_sha256": manifest_seal[
        "witness_manifest_seal_sha256"
    ],
    "targets": sorted(target_signature["target"].tolist()),
    "forecast_count": len(target_signature),
    "forecast_file_sha256": sha_file(forecast_path),
    "full_outcomes_unsealed": False,
    "primary32_predictions_observed": False,
    "single_pilot_deployment_authorised": False,
    "sealed_utc": now(),
}
forecast_seal["forecast_seal_sha256"] = sha_json(forecast_seal)
forecast_seal_path = P4 / "StageT3-A_Evidence_Forecast_Seal_v0.1.json"
write_json(forecast_seal_path, forecast_seal)
print("Evidence forecasts sealed:", forecast_seal["forecast_seal_sha256"])
display(target_signature)

# Phase 2: fixed budget-32 primary performance predictions.
broker.set_phase("PRIMARY32")
primary32_results, primary32_diagnostics, primary32_skips = run_wave(
    PRIMARY_BUDGET, "PRIMARY32_PERFORMANCE", PRIMARY_METHODS
)
write_csv(P5 / "StageT3-A_Budget32_All_Blind_Predictions_v0.1.csv", primary32_results)
write_csv(P5 / "StageT3-A_Budget32_RA_CB_Diagnostics_v0.1.csv", primary32_diagnostics)
write_csv(P5 / "StageT3-A_Budget32_Skips_v0.1.csv", primary32_skips)

edge_predictions = (
    primary32_results.groupby(
        [
            "target", "provider", "modality", "source",
            "edge_id", "method", "source_validation_auc",
            "retention_threshold",
        ],
        as_index=False,
    )
    .agg(
        estimate_auc=("estimate_auc", "median"),
        replicate_estimate_iqr=(
            "estimate_auc",
            lambda values: float(
                np.quantile(values, 0.75)
                - np.quantile(values, 0.25)
            ),
        ),
        usable_replicates=("replicate", "nunique"),
    )
)
primary_certificates = edge_predictions[
    edge_predictions["method"].eq("ra_cb_amw_ddet")
].copy()
primary_certificates["conformal_radius"] = CONFORMAL_RADIUS
primary_certificates["lower_auc"] = np.clip(
    primary_certificates["estimate_auc"] - CONFORMAL_RADIUS,
    0, 1,
)
primary_certificates["upper_auc"] = np.clip(
    primary_certificates["estimate_auc"] + CONFORMAL_RADIUS,
    0, 1,
)
primary_certificates["certificate_status"] = np.where(
    primary_certificates["lower_auc"]
    >= primary_certificates["retention_threshold"],
    "CERTIFIED_RETAINED",
    np.where(
        primary_certificates["upper_auc"]
        < primary_certificates["retention_threshold"],
        "EXCLUDED",
        "UNIDENTIFIABLE",
    ),
)
primary_certificates["true_auc_accessed"] = False
primary_certificates["full_outcome_unsealed"] = False

edge_prediction_path = P5 / "StageT3-A_Budget32_Frozen_Edge_Predictions_v0.1.csv"
certificate_path = P5 / "StageT3-A_Budget32_Frozen_RA_CB_Certificates_v0.1.csv"
write_csv(edge_prediction_path, edge_predictions)
write_csv(certificate_path, primary_certificates)
primary_seal = {
    "stage": "StageT3-A",
    "event": "BUDGET32_PRIMARY_PREDICTIONS_AND_CERTIFICATES_SEALED_BEFORE_FULL_OUTCOME_UNSEAL",
    "forecast_seal_sha256": forecast_seal["forecast_seal_sha256"],
    "prediction_file_sha256": sha_file(edge_prediction_path),
    "certificate_file_sha256": sha_file(certificate_path),
    "frozen_conformal_radius": CONFORMAL_RADIUS,
    "targets": sorted(primary_certificates["target"].unique().tolist()),
    "full_outcomes_unsealed": False,
    "method_refit": False,
    "sealed_utc": now(),
}
primary_seal["primary_prediction_seal_sha256"] = sha_json(primary_seal)
primary_seal_path = P5 / "StageT3-A_Primary_Prediction_Seal_v0.1.json"
write_json(primary_seal_path, primary_seal)
print("Primary predictions sealed:", primary_seal["primary_prediction_seal_sha256"])

# Phase 3: remaining evidence waves. Forecast and primary predictions remain immutable.
broker.set_phase("REMAINING_SECONDARY")
remaining_results = []
remaining_skips = []
for budget in [16, 64, 128]:
    results, diagnostics, skips = run_wave(
        budget, "REMAINING_EVIDENCE_SECONDARY", ["amw_ddet"]
    )
    remaining_results.append(results)
    remaining_skips.append(skips)
remaining_results = pd.concat(
    [frame for frame in remaining_results if len(frame)],
    ignore_index=True,
    sort=False,
) if any(len(frame) for frame in remaining_results) else pd.DataFrame()
remaining_skips = pd.concat(
    [frame for frame in remaining_skips if len(frame)],
    ignore_index=True,
    sort=False,
) if any(len(frame) for frame in remaining_skips) else pd.DataFrame()

write_csv(P6 / "StageT3-A_Remaining_Evidence_Wave_Estimates_v0.1.csv", remaining_results)
write_csv(P6 / "StageT3-A_Remaining_Evidence_Wave_Skips_v0.1.csv", remaining_skips)

print("Budget-8 result rows:", len(budget8_results))
print("Budget-32 primary result rows:", len(primary32_results))
print("Remaining evidence result rows:", len(remaining_results))
print("Full outcomes unsealed:", False)



# Final permitted outcome unseal, prespecified A/B/C classification, and durable Drive commit
broker.set_phase("FINAL_UNSEAL")
full_labels = broker.final_unseal(
    forecast_seal_path=forecast_seal_path,
    primary_seal_path=primary_seal_path,
)
full_labels = full_labels[
    full_labels["group_id"].isin(set(retained_roster["group_id"]))
].copy()
write_csv(P6 / "StageT3-A_Outcome_Broker_Access_Ledger_v0.1.csv", broker.ledger())

class_summary = (
    full_labels.groupby(["target", "label"], as_index=False)
    .agg(groups=("group_id", "nunique"))
)
write_csv(P6 / "StageT3-A_Final_Target_Class_Count_Summary_v0.1.csv", class_summary)

truth_rows = []
for target, (data, sources) in target_tables.items():
    labels = full_labels[full_labels["target"].eq(target)][
        ["group_id", "label"]
    ]
    merged = data.merge(labels, on="group_id", how="inner", validate="one_to_one")
    assert len(merged) == len(data), f"Final label coverage incomplete: {target}"
    y = merged["label"].to_numpy(int)
    raw = merged[sources].to_numpy(float)
    x = (raw - raw.mean(0)) / (raw.std(0) + 1e-9)
    assert len(np.unique(y)) == 2, f"Final target has one class: {target}"
    for source_index, source in enumerate(sources):
        truth_rows.append({
            "target": target,
            "provider": merged["provider"].iloc[0],
            "modality": merged["modality"].iloc[0],
            "source": source,
            "edge_id": f"{source}__TO__{target}",
            "true_auc": float(roc_auc_score(y, x[:, source_index])),
            "source_validation_auc": SOURCE_VALIDATION_AUC[source],
            "retention_threshold": SOURCE_VALIDATION_AUC[source] - 0.15,
            "independent_groups": len(merged),
        })
edge_truth = pd.DataFrame(truth_rows)
write_csv(P6 / "StageT3-A_Final_Blind_Edge_Truth_v0.1.csv", edge_truth)

# Primary performance analysis.
primary_full = primary32_results.merge(
    edge_truth[["target", "source", "true_auc"]],
    on=["target", "source"],
    validate="many_to_one",
)
primary_full["absolute_error"] = (
    primary_full["estimate_auc"] - primary_full["true_auc"]
).abs()
write_csv(P7 / "StageT3-A_Budget32_All_Methods_With_Truth_v0.1.csv", primary_full)

target_error = (
    primary_full.groupby(
        ["method", "target", "modality"], as_index=False
    )
    .agg(absolute_error=("absolute_error", "median"))
)
target_error_wide = target_error.pivot(
    index="target", columns="method", values="absolute_error"
)
required_primary_methods = [
    "ra_cb_amw_ddet", "random_direct", "random_logistic_plugin"
]
common_primary_targets = target_error_wide.dropna(
    subset=required_primary_methods
).index.tolist()
primary_target_error = target_error_wide.loc[common_primary_targets]

primary_mae = (
    float(primary_target_error["ra_cb_amw_ddet"].median())
    if len(primary_target_error) else np.nan
)
direct_mae = (
    float(primary_target_error["random_direct"].median())
    if len(primary_target_error) else np.nan
)
logistic_mae = (
    float(primary_target_error["random_logistic_plugin"].median())
    if len(primary_target_error) else np.nan
)
relative_vs_direct = (
    float(1 - primary_mae / direct_mae)
    if np.isfinite(primary_mae) and direct_mae > 0
    else np.nan
)
strict_majority_vs_logistic = (
    int(
        (
            primary_target_error["ra_cb_amw_ddet"]
            < primary_target_error["random_logistic_plugin"]
        ).sum()
    )
    if len(primary_target_error) else 0
)

edge_summary = (
    primary_full.groupby(
        [
            "method", "target", "provider", "modality",
            "source", "edge_id",
        ],
        as_index=False,
    )
    .agg(
        estimate_auc=("estimate_auc", "median"),
        true_auc=("true_auc", "first"),
        absolute_error=("absolute_error", "median"),
        usable_replicates=("replicate", "nunique"),
    )
)
ra_edge_summary = edge_summary[
    edge_summary["method"].eq("ra_cb_amw_ddet")
].copy()
edge_spearman = (
    float(
        spearmanr(
            ra_edge_summary["estimate_auc"],
            ra_edge_summary["true_auc"],
        ).statistic
    )
    if len(ra_edge_summary) >= 3 else np.nan
)

certificate_evaluation = primary_certificates.merge(
    edge_truth[
        ["target", "source", "true_auc"]
    ],
    on=["target", "source"],
    validate="one_to_one",
)
certificate_evaluation["truth_retained"] = (
    certificate_evaluation["true_auc"]
    >= certificate_evaluation["retention_threshold"]
)
certificate_evaluation["interval_covers_truth"] = (
    (certificate_evaluation["true_auc"] >= certificate_evaluation["lower_auc"])
    & (certificate_evaluation["true_auc"] <= certificate_evaluation["upper_auc"])
)
certificate_evaluation["wrong_decision"] = (
    (
        certificate_evaluation["certificate_status"].eq("CERTIFIED_RETAINED")
        & ~certificate_evaluation["truth_retained"]
    )
    | (
        certificate_evaluation["certificate_status"].eq("EXCLUDED")
        & certificate_evaluation["truth_retained"]
    )
)
decided = ~certificate_evaluation["certificate_status"].eq("UNIDENTIFIABLE")
interval_coverage = float(
    certificate_evaluation["interval_covers_truth"].mean()
) if len(certificate_evaluation) else np.nan
decision_coverage = float(decided.mean()) if len(certificate_evaluation) else 0.0
wrong_decision_rate = (
    float(certificate_evaluation.loc[decided, "wrong_decision"].mean())
    if decided.any() else 1.0
)
write_csv(P7 / "StageT3-A_RA_CB_Certificate_Evaluation_v0.1.csv", certificate_evaluation)
write_csv(P7 / "StageT3-A_Target_Level_Primary_Error_v0.1.csv", target_error)
write_csv(P7 / "StageT3-A_Edge_Level_Primary_Summary_v0.1.csv", edge_summary)

analyzable_modalities = (
    edge_truth[
        edge_truth["target"].isin(common_primary_targets)
    ]["modality"].nunique()
)
primary_survival_components = {
    "at_least_two_targets_two_modalities": (
        len(common_primary_targets) >= 2
        and analyzable_modalities >= 2
    ),
    "target_median_mae_le_0_05": (
        np.isfinite(primary_mae) and primary_mae <= 0.05
    ),
    "improvement_vs_random_direct_ge_25pct": (
        np.isfinite(relative_vs_direct)
        and relative_vs_direct >= 0.25
    ),
    "strict_majority_better_than_random_logistic": (
        strict_majority_vs_logistic
        > len(common_primary_targets) / 2
    ),
    "edge_spearman_ge_0_75": (
        np.isfinite(edge_spearman)
        and edge_spearman >= 0.75
    ),
    "frozen_interval_coverage_ge_0_85": (
        np.isfinite(interval_coverage)
        and interval_coverage >= 0.85
    ),
    "wrong_decision_rate_le_0_05": (
        wrong_decision_rate <= 0.05
    ),
}
primary_survives = all(primary_survival_components.values())

# Evidence-demand secondary analysis.
evidence_parts = [
    budget8_results[budget8_results["method"].eq("amw_ddet")],
    primary32_results[primary32_results["method"].eq("amw_ddet")],
]
if len(remaining_results):
    evidence_parts.append(
        remaining_results[
            remaining_results["method"].eq("amw_ddet")
        ]
    )
evidence_results = pd.concat(
    evidence_parts, ignore_index=True, sort=False
)
evidence_results = evidence_results.merge(
    edge_truth[["target", "source", "true_auc"]],
    on=["target", "source"],
    validate="many_to_one",
)
evidence_results["absolute_error"] = (
    evidence_results["estimate_auc"]
    - evidence_results["true_auc"]
).abs()
write_csv(P7 / "StageT3-A_AMW_DDET_Evidence_Waves_With_Truth_v0.1.csv", evidence_results)

raw_curves = (
    evidence_results.groupby(
        ["target", "provider", "modality", "budget"],
        as_index=False,
    )
    .agg(
        median_absolute_error=("absolute_error", "median"),
        usable_edge_replicates=("absolute_error", "size"),
    )
)
interval_rows = []
projected_rows = []
regime_rows = []
for (target, provider, modality), frame in raw_curves.groupby(
    ["target", "provider", "modality"]
):
    frame = frame.sort_values("budget")
    budgets = frame["budget"].to_numpy(int)
    errors = frame["median_absolute_error"].to_numpy(float)
    projected = IsotonicRegression(
        increasing=False, out_of_bounds="clip"
    ).fit_transform(np.log2(budgets), errors)
    passing = np.flatnonzero(projected <= THRESHOLD)
    if len(passing):
        position = int(passing[0])
        lower = (
            -np.inf
            if position == 0
            else float(np.log2(budgets[position - 1]))
        )
        upper = float(np.log2(budgets[position]))
        status = (
            "LEFT_CENSORED"
            if position == 0
            else "INTERVAL_CENSORED"
        )
        operational = int(budgets[position])
    else:
        lower = float(np.log2(budgets[-1]))
        upper = np.inf
        status = "RIGHT_CENSORED"
        operational = int(budgets[-1] * 2)

    first_error = float(projected[0])
    final_error = float(projected[-1])
    repair_fraction = float(
        (first_error - final_error) / max(first_error, 1e-12)
    )
    if final_error <= THRESHOLD:
        regime = "EVIDENCE_LIMITED_OPERATIONAL"
    elif repair_fraction <= 0.20:
        regime = "MODEL_LIMITED_WITHIN_FROZEN_AUDIT_FAMILY"
    else:
        regime = "EVIDENCE_DEMANDING_RIGHT_CENSORED"

    interval_rows.append({
        "target": target,
        "provider": provider,
        "modality": modality,
        "lower": lower,
        "upper": upper,
        "status": status,
        "operational_budget_administrative": operational,
        "maximum_tested_budget": int(budgets[-1]),
    })
    regime_rows.append({
        "target": target,
        "provider": provider,
        "modality": modality,
        "projected_first_error": first_error,
        "projected_final_error": final_error,
        "projected_repair_fraction": repair_fraction,
        "frozen_regime": regime,
    })
    for budget, raw_error, projected_error in zip(
        budgets, errors, projected
    ):
        projected_rows.append({
            "target": target,
            "budget": int(budget),
            "raw_median_error": float(raw_error),
            "isotonic_median_error": float(projected_error),
        })

observed_intervals = pd.DataFrame(interval_rows)
regime_table = pd.DataFrame(regime_rows)
projected_curves = pd.DataFrame(projected_rows)

def interval_probability_and_nll(lower, upper, mu, sigma):
    if np.isneginf(lower):
        probability = norm.cdf((upper - mu) / sigma)
    elif np.isposinf(upper):
        probability = norm.sf((lower - mu) / sigma)
    else:
        probability = (
            norm.cdf((upper - mu) / sigma)
            - norm.cdf((lower - mu) / sigma)
        )
    probability = max(float(probability), 1e-12)
    return probability, float(-np.log(probability))

def interval_order_concordance(frame):
    comparable = 0
    concordant = 0
    ties = 0
    frame = frame.reset_index(drop=True)
    for left_index, right_index in itertools.combinations(
        range(len(frame)), 2
    ):
        left = frame.iloc[left_index]
        right = frame.iloc[right_index]
        observed_order = None
        if (
            np.isfinite(left["upper"])
            and np.isfinite(right["lower"])
            and left["upper"] <= right["lower"]
        ):
            observed_order = -1
        elif (
            np.isfinite(right["upper"])
            and np.isfinite(left["lower"])
            and right["upper"] <= left["lower"]
        ):
            observed_order = 1
        if observed_order is None:
            continue
        comparable += 1
        difference = (
            float(left["mu_log2_budget"])
            - float(right["mu_log2_budget"])
        )
        if abs(difference) < 1e-12:
            ties += 1
        elif (
            observed_order == 1 and difference > 0
        ) or (
            observed_order == -1 and difference < 0
        ):
            concordant += 1
    value = (
        (concordant + 0.5 * ties) / comparable
        if comparable else np.nan
    )
    return value, comparable

evidence_evaluation = target_signature.merge(
    observed_intervals,
    on=["target", "provider", "modality"],
    validate="one_to_one",
)
probabilities_and_nll = [
    interval_probability_and_nll(
        row.lower, row.upper,
        row.mu_log2_budget, row.sigma
    )
    for row in evidence_evaluation.itertuples()
]
evidence_evaluation["probability_observed_interval"] = [
    value[0] for value in probabilities_and_nll
]
evidence_evaluation["prospective_interval_nll"] = [
    value[1] for value in probabilities_and_nll
]
evidence_evaluation["underestimation_more_than_one_doubling"] = [
    bool(
        np.isfinite(row.lower)
        and row.mu_log2_budget < row.lower - 1.0
    )
    for row in evidence_evaluation.itertuples()
]

supported_evidence = evidence_evaluation[
    evidence_evaluation["support_status"].eq("SUPPORTED")
].copy()
supported_mean_nll = (
    float(supported_evidence["prospective_interval_nll"].mean())
    if len(supported_evidence) else np.nan
)
order_concordance, comparable_pairs = interval_order_concordance(
    supported_evidence
)
evidence_survival_components = {
    "at_least_two_supported_targets": len(supported_evidence) >= 2,
    "supported_mean_nll_le_2_41565": (
        np.isfinite(supported_mean_nll)
        and supported_mean_nll <= 2.41565
    ),
    "each_supported_interval_probability_ge_0_05": (
        len(supported_evidence) >= 1
        and bool(
            (
                supported_evidence[
                    "probability_observed_interval"
                ] >= 0.05
            ).all()
        )
    ),
    "no_supported_underestimate_gt_one_doubling": (
        len(supported_evidence) >= 1
        and not bool(
            supported_evidence[
                "underestimation_more_than_one_doubling"
            ].any()
        )
    ),
    "interval_order_concordance_ge_0_5_when_comparable": (
        comparable_pairs == 0
        or (
            np.isfinite(order_concordance)
            and order_concordance >= 0.5
        )
    ),
}
evidence_survives = all(evidence_survival_components.values())

write_csv(P7 / "StageT3-A_Observed_Evidence_Demand_Intervals_v0.1.csv", observed_intervals)
write_csv(P7 / "StageT3-A_Prospective_Evidence_Forecast_Evaluation_v0.1.csv", evidence_evaluation)
write_csv(P7 / "StageT3-A_Isotonic_Evidence_Curves_v0.1.csv", projected_curves)
write_csv(P7 / "StageT3-A_Repairability_Regimes_v0.1.csv", regime_table)

ledger = broker.ledger()
phase_sequence = ledger["phase"].map(
    EncryptedOutcomeBroker._phase_order
).to_numpy()
broker_chronology_valid = bool(
    np.all(np.diff(phase_sequence) >= 0)
    and ledger.iloc[-1]["access_type"]
    == "FINAL_FULL_OUTCOME_UNSEAL"
)

integrity_components = {
    "parents_and_companions_exact": True,
    "official_only_assets": bool(
        asset_receipts["route_status"].str.contains(
            "OFFICIAL|AUTHENTICATED|ALREADY"
        ).all()
        or asset_receipts.loc[
            asset_receipts["target"].eq("BUSI_CAIRO_2019"),
            "route_status",
        ].str.contains("FAILED").all()
    ),
    "witness_manifests_presealed": (
        manifest_seal["analysis_outcomes_accessed"] is False
    ),
    "evidence_forecast_presealed": (
        forecast_seal["full_outcomes_unsealed"] is False
    ),
    "primary_prediction_presealed": (
        primary_seal["full_outcomes_unsealed"] is False
    ),
    "broker_chronology_valid": broker_chronology_valid,
    "frozen_source_axes_exact": True,
    "no_target_replacement": True,
    "single_pilot_deployment_prohibited": (
        t2h["single_pilot_deployment_authorised"] is False
    ),
    "stage12_false": t3pf["stage12_authorised"] is False,
}
integrity_pass = all(integrity_components.values())

if not integrity_pass:
    scenario = "INTEGRITY_TERMINATION"
    decision = "TERMINATE_T3A_BLIND_EXECUTION_INTEGRITY_OR_CHRONOLOGY_FAILURE"
elif primary_survives and evidence_survives:
    scenario = "SCENARIO_A_DUAL_SURVIVAL"
    decision = (
        "SEAL_T3A_SCENARIO_A_DUAL_SURVIVAL_"
        "AUTHORISE_T3B_ACTIVATION_REVIEW_ONLY"
    )
elif primary_survives:
    scenario = "SCENARIO_B_PERFORMANCE_ONLY_SURVIVAL"
    decision = (
        "SEAL_T3A_SCENARIO_B_PERFORMANCE_SURVIVAL_"
        "EVIDENCE_SECONDARY_FAILURE_AUTHORISE_MANUSCRIPT_RESCOPING"
    )
else:
    scenario = "SCENARIO_C_PERFORMANCE_PRIMARY_FAILURE"
    decision = (
        "SEAL_T3A_SCENARIO_C_PERFORMANCE_PRIMARY_FAILURE_"
        "PROHIBIT_CONFIRMATORY_UPGRADE"
    )

gate_rows = []
for name, passed in integrity_components.items():
    gate_rows.append({
        "gate_family": "INTEGRITY",
        "gate": name,
        "passed": bool(passed),
        "observed": "",
    })
for name, passed in primary_survival_components.items():
    gate_rows.append({
        "gate_family": "PRIMARY_SURVIVAL",
        "gate": name,
        "passed": bool(passed),
        "observed": "",
    })
for name, passed in evidence_survival_components.items():
    gate_rows.append({
        "gate_family": "EVIDENCE_SECONDARY",
        "gate": name,
        "passed": bool(passed),
        "observed": "",
    })
gates = pd.DataFrame(gate_rows)

observed_map = {
    "at_least_two_targets_two_modalities": (
        f"targets={len(common_primary_targets)}; modalities={analyzable_modalities}"
    ),
    "target_median_mae_le_0_05": primary_mae,
    "improvement_vs_random_direct_ge_25pct": relative_vs_direct,
    "strict_majority_better_than_random_logistic": (
        f"{strict_majority_vs_logistic}/{len(common_primary_targets)}"
    ),
    "edge_spearman_ge_0_75": edge_spearman,
    "frozen_interval_coverage_ge_0_85": interval_coverage,
    "wrong_decision_rate_le_0_05": wrong_decision_rate,
    "at_least_two_supported_targets": len(supported_evidence),
    "supported_mean_nll_le_2_41565": supported_mean_nll,
    "each_supported_interval_probability_ge_0_05": (
        supported_evidence[
            "probability_observed_interval"
        ].min() if len(supported_evidence) else np.nan
    ),
    "no_supported_underestimate_gt_one_doubling": (
        int(
            supported_evidence[
                "underestimation_more_than_one_doubling"
            ].sum()
        ) if len(supported_evidence) else np.nan
    ),
    "interval_order_concordance_ge_0_5_when_comparable": (
        f"concordance={order_concordance}; comparable_pairs={comparable_pairs}"
    ),
}
for index in gates.index:
    gate = gates.loc[index, "gate"]
    if gate in observed_map:
        gates.loc[index, "observed"] = str(observed_map[gate])
write_csv(P7 / "StageT3-A_Frozen_Scenario_Gates_v0.1.csv", gates)

primary_metrics = {
    "analyzable_targets": common_primary_targets,
    "analyzable_target_count": len(common_primary_targets),
    "analyzable_modalities": int(analyzable_modalities),
    "ra_cb_target_median_mae": (
        primary_mae if np.isfinite(primary_mae) else None
    ),
    "random_direct_target_median_mae": (
        direct_mae if np.isfinite(direct_mae) else None
    ),
    "random_logistic_target_median_mae": (
        logistic_mae if np.isfinite(logistic_mae) else None
    ),
    "relative_improvement_vs_random_direct": (
        relative_vs_direct
        if np.isfinite(relative_vs_direct) else None
    ),
    "targets_better_than_random_logistic": strict_majority_vs_logistic,
    "edge_spearman": (
        edge_spearman if np.isfinite(edge_spearman) else None
    ),
    "interval_coverage": (
        interval_coverage
        if np.isfinite(interval_coverage) else None
    ),
    "decision_coverage": decision_coverage,
    "wrong_decision_rate_among_decided": wrong_decision_rate,
    "survival_components": primary_survival_components,
    "primary_survives": primary_survives,
}
evidence_metrics = {
    "supported_targets": supported_evidence["target"].tolist(),
    "supported_target_count": len(supported_evidence),
    "supported_mean_interval_nll": (
        supported_mean_nll
        if np.isfinite(supported_mean_nll) else None
    ),
    "minimum_supported_observed_interval_probability": (
        float(
            supported_evidence[
                "probability_observed_interval"
            ].min()
        ) if len(supported_evidence) else None
    ),
    "underestimation_gt_one_doubling_count": (
        int(
            supported_evidence[
                "underestimation_more_than_one_doubling"
            ].sum()
        ) if len(supported_evidence) else None
    ),
    "interval_order_concordance": (
        order_concordance
        if np.isfinite(order_concordance) else None
    ),
    "comparable_pairs": comparable_pairs,
    "regime_counts": regime_table[
        "frozen_regime"
    ].value_counts().to_dict(),
    "survival_components": evidence_survival_components,
    "evidence_secondary_survives": evidence_survives,
}

plt.figure(figsize=(8, 5))
for _, row in evidence_evaluation.iterrows():
    lower = row["upper"] - 1 if np.isneginf(row["lower"]) else row["lower"]
    upper = row["lower"] + 1 if np.isposinf(row["upper"]) else row["upper"]
    plt.plot([lower, upper], [row["target"], row["target"]], linewidth=2)
    plt.scatter([row["mu_log2_budget"]], [row["target"]], s=50)
plt.xlabel("Frozen predicted latent log2 evidence demand and observed interval")
plt.ylabel("Locked blind target")
plt.title(f"Stage T3-A evidence forecast: {scenario}")
plt.tight_layout()
plt.savefig(P7 / "StageT3-A_Prospective_Evidence_Interval_Evaluation_v0.1.png", dpi=220)
plt.show()

plt.figure(figsize=(8, 5))
for target, frame in projected_curves.groupby("target"):
    plt.plot(
        frame["budget"],
        frame["isotonic_median_error"],
        marker="o",
        label=target,
    )
plt.axhline(THRESHOLD, linestyle="--")
plt.xscale("log", base=2)
plt.xlabel("Witness-group budget")
plt.ylabel("Isotonic median absolute AUC error")
plt.title("Stage T3-A frozen AMW-DDET evidence curves")
plt.legend(fontsize=8)
plt.tight_layout()
plt.savefig(P7 / "StageT3-A_Frozen_Evidence_Curves_v0.1.png", dpi=220)
plt.show()

complete = {
    "stage": "StageT3-A",
    "scenario": scenario,
    "decision": decision,
    "parent_t3pf_activation_sha256": EXPECTED["t3pf_activation"],
    "parent_t2mn_final_sha256": EXPECTED["t2mn_final"],
    "activation_seal_sha256": activation_payload[
        "activation_seal_sha256"
    ],
    "witness_manifest_seal_sha256": manifest_seal[
        "witness_manifest_seal_sha256"
    ],
    "evidence_forecast_seal_sha256": forecast_seal[
        "forecast_seal_sha256"
    ],
    "primary_prediction_seal_sha256": primary_seal[
        "primary_prediction_seal_sha256"
    ],
    "available_targets": score_ready_targets,
    "unavailable_target_ledger": readiness[
        ~readiness["primary_budget32_ready"]
    ].to_dict(orient="records"),
    "primary_metrics": primary_metrics,
    "evidence_metrics": evidence_metrics,
    "integrity_components": integrity_components,
    "integrity_pass": integrity_pass,
    "single_pilot_deployment_authorised": False,
    "locked_blind_assets_touched": True,
    "locked_blind_witness_labels_accessed": True,
    "locked_blind_full_outcomes_unsealed": True,
    "stage12_authorised": False,
    "t3b_execution_authorised": False,
    "completed_utc": now(),
}
complete["final_record_sha256"] = sha_json(complete)
complete_path = P7 / "StageT3-A_Complete_v0.1.json"
write_json(complete_path, complete)

summary = f"""# Stage T3-A locked-blind sentinel result

- Scenario: `{scenario}`
- Decision: `{decision}`
- Available targets: `{score_ready_targets}`
- Primary survives: `{primary_survives}`
- Evidence secondary survives: `{evidence_survives}`
- RA-CB target median MAE: `{primary_metrics['ra_cb_target_median_mae']}`
- Random-direct / random-logistic target median MAE: `{primary_metrics['random_direct_target_median_mae']} / {primary_metrics['random_logistic_target_median_mae']}`
- Relative improvement vs random-direct: `{primary_metrics['relative_improvement_vs_random_direct']}`
- Edge Spearman: `{primary_metrics['edge_spearman']}`
- Interval coverage / decision coverage / wrong-decision rate: `{primary_metrics['interval_coverage']} / {primary_metrics['decision_coverage']} / {primary_metrics['wrong_decision_rate_among_decided']}`
- Supported evidence targets: `{evidence_metrics['supported_targets']}`
- Supported mean prospective interval NLL: `{evidence_metrics['supported_mean_interval_nll']}`
- Minimum observed-interval probability: `{evidence_metrics['minimum_supported_observed_interval_probability']}`
- Evidence interval-order concordance: `{evidence_metrics['interval_order_concordance']}`
- Regime counts: `{evidence_metrics['regime_counts']}`
- Single-pilot deployment authorised: `False`
- Stage 12 authorised: `False`
- T3-B execution authorised: `False`
- Final record SHA256: `{complete['final_record_sha256']}`
"""
summary_path = P7 / "StageT3-A_Result_Summary_v0.1.md"
write_text(summary_path, summary)

display(target_error)
display(edge_summary)
display(certificate_evaluation)
display(evidence_evaluation)
display(regime_table)
display(gates)

# Canonical local-first archive.
canonical_zip = RUNTIME_ROOT / "StageT3-A_Canonical_Records_v0.1.zip"
with zipfile.ZipFile(
    canonical_zip, "w",
    compression=zipfile.ZIP_DEFLATED,
    compresslevel=6,
) as archive:
    for source in sorted(LOCAL_RECORDS.rglob("*")):
        if source.is_file():
            archive.write(
                source,
                arcname=str(source.relative_to(LOCAL_RECORDS)),
            )

flat_copy_sources = [
    canonical_zip,
    complete_path,
    summary_path,
    P0 / "StageT3-A_Activation_Seal_v0.1.json",
    P3 / "StageT3-A_Witness_Manifest_Seal_v0.1.json",
    forecast_seal_path,
    primary_seal_path,
    P7 / "StageT3-A_Frozen_Scenario_Gates_v0.1.csv",
    P7 / "StageT3-A_Target_Level_Primary_Error_v0.1.csv",
    P7 / "StageT3-A_Edge_Level_Primary_Summary_v0.1.csv",
    P7 / "StageT3-A_RA_CB_Certificate_Evaluation_v0.1.csv",
    P7 / "StageT3-A_Prospective_Evidence_Forecast_Evaluation_v0.1.csv",
    P7 / "StageT3-A_Repairability_Regimes_v0.1.csv",
    P6 / "StageT3-A_Outcome_Broker_Access_Ledger_v0.1.csv",
]
commit_rows = []
for source in flat_copy_sources:
    destination = COMMIT_ROOT / source.name
    temp = destination.with_suffix(destination.suffix + ".tmp")
    shutil.copy2(source, temp)
    os.replace(temp, destination)
    source_sha = sha_file(source)
    destination_sha = sha_file(destination)
    assert source_sha == destination_sha
    commit_rows.append({
        "file": source.name,
        "bytes": destination.stat().st_size,
        "sha256": destination_sha,
        "drive_path": str(destination),
    })

os.sync()
time.sleep(3)
for row in commit_rows:
    path = Path(row["drive_path"])
    assert path.is_file()
    assert path.stat().st_size == row["bytes"]
    assert sha_file(path) == row["sha256"]

commit_manifest = {
    "stage": "StageT3-A",
    "scenario": scenario,
    "decision": decision,
    "commit_root": str(COMMIT_ROOT),
    "canonical_bundle_sha256": sha_file(canonical_zip),
    "files": commit_rows,
    "all_drive_copies_reopened_and_hash_verified": True,
    "drive_flush_requested": True,
    "single_pilot_deployment_authorised": False,
    "stage12_authorised": False,
    "committed_utc": now(),
}
commit_manifest["commit_manifest_sha256"] = sha_json(commit_manifest)
commit_manifest_path = RUNTIME_ROOT / "StageT3-A_Durable_Commit_Manifest_v0.1.json"
write_json(commit_manifest_path, commit_manifest)
drive_commit_manifest = COMMIT_ROOT / commit_manifest_path.name
shutil.copy2(commit_manifest_path, drive_commit_manifest)
assert sha_file(commit_manifest_path) == sha_file(drive_commit_manifest)
os.sync()
time.sleep(3)
assert sha_file(drive_commit_manifest) == sha_file(commit_manifest_path)

print("DURABLE DRIVE COMMIT VERIFIED BEFORE FLUSH")
print("Commit root:", COMMIT_ROOT)
print("Scenario:", scenario)
print("Final record SHA256:", complete["final_record_sha256"])

# Remove transient blind assets only after verified commit.
if ASSET_WORK.exists():
    shutil.rmtree(ASSET_WORK)

flush_status = "OS_SYNC_COMPLETE"
if IN_COLAB:
    try:
        drive.flush_and_unmount()
        flush_status = "FLUSH_AND_UNMOUNT_COMPLETE"
    except Exception as exc:
        flush_status = f"FLUSH_REQUEST_ERROR_{type(exc).__name__}"

print("\n========== STAGE T3-A COMPLETE ==========")
print("Scenario:", scenario)
print("Decision:", decision)
print("Primary survives:", primary_survives)
print("Evidence secondary survives:", evidence_survives)
print("Single-pilot deployment authorised:", False)
print("Stage 12 authorised:", False)
print("T3-B execution authorised:", False)
print("Drive persistence:", flush_status)
print("Final record SHA256:", complete["final_record_sha256"])
