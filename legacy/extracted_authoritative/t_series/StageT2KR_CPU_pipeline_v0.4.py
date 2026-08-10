# @title T2-K-0. Mount Drive, verify immutable parents/documents/axes, and seal the protocol
import base64, gc, hashlib, io, itertools, json, math, os, platform, random, re, shutil, sys, tarfile, time, unicodedata, warnings, zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
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
THEORY_ROOT = PROJECT_ROOT / "03_Theory" / "Directed_Diagnostic_Evidence_Transport_v0.9"
STUDY_ROOT = PROJECT_ROOT / "04_Study_Design"
CM_ROOT = PROJECT_ROOT / "06_Data_Records" / "Cross_Modal"
ACQ_ROOT = PROJECT_ROOT / "00_Data_Acquisition" / "Cross_Modal_Independent_Target_Expansion_v0.1"

RESULT_ROOT = CM_ROOT / "StageT2-KR_Frozen_Axis_Schema_Adapter_And_CPU_Continuation_v0.4"
LEGACY_CACHE_ROOTS = [
    (
        CM_ROOT
        / "StageT2-KR_HiSBreast_Regex_Checkpoint_Repair_And_CPU_MultiBudget_Extension_v0.3"
        / "03_Frozen_Embeddings_And_Source_Scores"
    ),
    (
        CM_ROOT
        / "StageT2-KR_HiSBreast_Container_JSON_Repair_And_CPU_MultiBudget_Extension_v0.2"
        / "03_Frozen_Embeddings_And_Source_Scores"
    ),
]
P0, P1, P2, P3, P4, P5, P6 = [RESULT_ROOT / x for x in [
    "00_Protocol", "01_HiSBreast_Adjudication", "02_Expansion_Target_Roster",
    "03_Frozen_Embeddings_And_Source_Scores", "04_MultiBudget_Extension",
    "05_Meta_Analysis_And_Gates", "06_Results"
]]
for p in [CODE_ROOT, THEORY_ROOT, STUDY_ROOT, P0, P1, P2, P3, P4, P5, P6]:
    p.mkdir(parents=True, exist_ok=True)

NOTEBOOK_NAME = "CrossModal_StageT2-KR_Frozen_Axis_Schema_Adapter_And_CPU_Continuation_v0.4.ipynb"
NOTEBOOK_PATH = CODE_ROOT / NOTEBOOK_NAME
PREREG_PATH = STUDY_ROOT / "StageT2-KR_Axis_Schema_Adapter_And_CPU_Continuation_Preregistration_v1.3.md"
METHOD_PATH = THEORY_ROOT / "Frozen_Source_Axis_Schema_Adapter_And_CPU_Continuation_Method_v0.4.md"
LEXICON_PATH = STUDY_ROOT / "StageT2-KR_Frozen_HiSBreast_ICD_Diagnosis_Lexicon_v0.4.csv"

README_PATH = CODE_ROOT / "README_Cross_Modal_Notebook_Index_v1.7.md"
EMBEDDED_PREREG_TEXT = '# Stage T2-KR preregistration v1.3\n\n## Frozen source-axis schema adapter and CPU continuation\n\n**Frozen:** 22 July 2026, after Stage T2-KR v0.3 completed both target embeddings and terminated on the first frozen source-axis load, before any source-score table, target AUC, multi-budget result, or expanded meta-analysis was produced.\n\n## Observed non-outcome implementation fact\n\nThe frozen dermoscopy and breast-ultrasound axes use two historical NPZ schemas:\n\n- Stage 8 dermoscopy: `source`, `raw_coefficient`, `raw_intercept`;\n- Stage 11E-R ultrasound: `dataset_id`, `coefficient_raw`, `intercept_raw`, plus `model_state_sha256`.\n\nThe v0.3 loader assumed only the Stage 11E-R schema and therefore raised `KeyError: dataset_id` on the first dermoscopy axis.\n\n## Frozen repair\n\nThe adapter:\n\n1. verifies every axis by its already frozen SHA-256;\n2. accepts identity from exactly one of `dataset_id` or `source`;\n3. accepts raw coefficient/intercept from exactly one of the two documented historical key pairs;\n4. requires a 2,048-dimensional finite coefficient and finite scalar intercept;\n5. verifies `model_state_sha256` when that field is present;\n6. records the detected schema for every source;\n7. reuses v0.3 embeddings only after exact target-order, dimensionality, finite-value and L2-normalisation checks.\n\nNo coefficient, intercept, source identity, source axis, representation, estimator, budget, selector, threshold or scientific gate is changed.\n\n## Scientific boundary\n\nHiSBreast remains excluded because no explicit released patient identifier was recovered. Only MILK10K and BrEaST-Lesions-USG proceed. Stage T2-H single-pilot deployment remains rejected. Locked-blind assets/outcomes remain untouched. Stage 12 remains false.\n'
EMBEDDED_METHOD_TEXT = '# Frozen source-axis schema adapter and CPU continuation method v0.4\n\nThe project contains two immutable historical NPZ layouts.\n\nFor each source-axis file, the loader first verifies the preregistered file SHA-256. It then reads:\n\n- identity from `dataset_id` or `source`;\n- coefficient from `coefficient_raw` or `raw_coefficient`;\n- intercept from `intercept_raw` or `raw_intercept`.\n\nAmbiguous, absent or dimensionally invalid fields terminate execution. A stored representation-model hash is checked when present. Stage 8 dermoscopy axes without that field remain admissible because the exact files, source identities, 2,048-dimensional parameters and Stage 8 axis-equivalence records are already frozen and hash-verified.\n\nThe continuation imports completed v0.3 target embeddings only when image IDs, target order, dimensions, finite values and unit L2 norms all match. It then resumes at frozen source scoring and runs the unchanged five-budget development extension.\n'
EMBEDDED_LEXICON_TEXT = 'category,normalised_regex,interpretation,strength\nnegative,\\bkhong co te bao ac tinh\\b,no malignant cells,strong\nnegative,\\bkhong ghi nhan te bao ac tinh\\b,no malignant cells recorded,strong\nnegative,\\bkhong ung thu\\b,no cancer,strong\nnegative,\\bkhong ac tinh\\b,not malignant,strong\npositive,\\bc50(?:\\s+\\d+)?\\b,ICD-10 malignant neoplasm of breast,strong\npositive,\\bbreast cancer\\b,English breast cancer,strong\npositive,\\bung thu\\b,Vietnamese cancer,strong\npositive,\\bac tinh\\b,Vietnamese malignant,strong\npositive,\\bu ac\\b,malignant tumour,strong\npositive,\\bmalignan,English malignant,strong\npositive,\\bcarcinom,carcinoma,strong\nnegative,\\bd24(?:\\s+\\d+)?\\b,ICD-10 benign neoplasm of breast,strong\nnegative,\\bn60(?:\\s+\\d+)?\\b,ICD-10 benign mammary dysplasia,strong\nnegative,\\bn61(?:\\s+\\d+)?\\b,ICD-10 inflammatory breast disorder,strong\nnegative,\\bn62(?:\\s+\\d+)?\\b,ICD-10 hypertrophy of breast,strong\nnegative,\\blanh tinh\\b,explicit benign,strong\nnegative,\\bbenign\\b,English benign,strong\nnegative,\\bu xo tuyen\\b,fibroadenoma,moderate\nnegative,\\bfibroadenom,fibroadenoma,moderate\nnegative,\\bnang\\b,cyst,moderate\nnegative,\\bcyst\\b,cyst,moderate\nambiguous_hold,\\bn63(?:\\s+\\d+)?\\b,unspecified breast lump,weak\nambiguous_hold,\\bn64(?:\\s+\\d+)?\\b,other breast disorder,weak\nambiguous_hold,\\br92(?:\\s+\\d+)?\\b,abnormal breast imaging finding,weak\nambiguous_hold,\\bd48\\s+6\\b,uncertain behaviour of breast,weak\nambiguous_hold,\\batypical changes\\b,atypical without definitive diagnosis,weak\nnormal_exclude,\\bbinh thuong\\b,normal breast,strong\nnormal_exclude,\\bno abnormalities\\b,no abnormality,strong\nnormal_exclude,\\bnormal\\b,normal,strong\nambiguous_hold,\\bnghi ngo\\b,suspicious only,weak\nambiguous_hold,\\btheo doi\\b,follow-up only,weak\nambiguous_hold,\\bbirads\\s*4\\b,BI-RADS 4 without final diagnosis,weak\n'
EMBEDDED_README_TEXT = '# Cross-Modal Notebook Index v1.7\n\nUpdated: 22 July 2026\n\nActive notebook:\n\n`CrossModal_StageT2-KR_Frozen_Axis_Schema_Adapter_And_CPU_Continuation_v0.4.ipynb`\n\nUse a clean CPU runtime and Run all. The notebook reuses verified v0.3 embeddings, adapts the two frozen historical NPZ schemas, and resumes source scoring plus the complete multi-budget extension.\n'

T2J_FINAL = CM_ROOT / "StageT2-J_Expansion_Harmonisation_Dedup_And_Public_Route_Repair_v0.1" / "05_Results" / "StageT2-J_Complete_v0.1.json"
T2J_SPLIT = CM_ROOT / "StageT2-J_Expansion_Harmonisation_Dedup_And_Public_Route_Repair_v0.1" / "04_Grouped_Splits" / "StageT2-J_Frozen_Grouped_Split_Manifest_v0.1.csv"
T2J_BREAST_MANIFEST = CM_ROOT / "StageT2-J_Expansion_Harmonisation_Dedup_And_Public_Route_Repair_v0.1" / "02_Harmonised_Manifests" / "StageT2-J_BrEaST_Harmonised_Exact_Manifest_v0.1.csv"

T2H_FINAL = CM_ROOT / "StageT2-H_Development_Only_Single_Pilot_Deployability_And_Sequential_Forecast_Freeze_v0.1" / "04_Results" / "StageT2-H_Complete_v0.1.json"
T3PF_FINAL = CM_ROOT / "StageT3-PF_Outcome-Free_Preregistration_And_Asset_Preflight_v1.0" / "04_Results" / "StageT3-PF_Activation_Record_v1.0.json"
T2D_REPS = CM_ROOT / "StageT2-D_Development_Only_AMW-DDET_Active_Minimal_Witness_Certificate_v0.1" / "01_Replicate_Results" / "StageT2-D_All_Acquisition_Replicates_v0.1.csv"

DERM_AXIS_ROOT = CM_ROOT / "Stage8_CrossModality_EdgeLibrary_Expansion_v0.1" / "03_Frozen_Source_Axes"
DERM_SUMMARY = DERM_AXIS_ROOT / "Stage8_Source_Recoverability_Summary_v0.1.csv"
US_AXIS_ROOT = CM_ROOT / "Stage11E-R_Development_Only_Source_Recoverability_And_Axis_Freeze_v0.1" / "03_Frozen_Source_Axes"
US_AXIS_MANIFEST = US_AXIS_ROOT / "Stage11E-R_Frozen_Source_Axis_Manifest_v0.1.csv"
US_DECISIONS = CM_ROOT / "Stage11E-R_Development_Only_Source_Recoverability_And_Axis_Freeze_v0.1" / "04_Heldout_Validation" / "Stage11E-R_Source_Recoverability_Decisions_v0.1.csv"
US_EXACT_MANIFEST = CM_ROOT / "Stage11D-R_Cross_Roster_Dedup_Exact_Manifest_And_Grouped_Split_Freeze_v0.1" / "01_Exact_Manifest" / "Stage11D-R_Frozen_Exact_Image_Label_Group_Manifest_v0.1.csv"

HIS_ROOT = ACQ_ROOT / "HISBREAST_V2"
HIS_ARCHIVE = HIS_ROOT / "00_Raw_Inbox" / "HiSBreast_Version 2.zip"
HIS_EXTRACTED = HIS_ROOT / "01_Extracted"

EXPECTED = {
    "t2j_file_sha256": "f6d3207d3d7f46ceebdc18b627bab34f936b64176cf17d7c609068125c339c5b",
    "t2j_record_sha256": "dc23137bf52c791bf40132f08bd22396e5d5b6d5d06c886271560161e610f4d8",
    "t2j_split_sha256": "e0d9a7d4813601c508c37221f14b707e1eac139e4c52c54da7e77fdf4fa688ec",
    "t2h_file_sha256": "4dc14383a299a97a3937a4fe2a38919952b6c931c5ee14308220141442504da4",
    "t2h_record_sha256": "27d4c7afe711ba66ea44d11f3ef173820e11ef1eba7a44530446a3e5444aa99f",
    "t3pf_file_sha256": "10646d771a3cd9e86c8c96eb4a134d4878c7542bb4b0b07ab9e01fa8b0c09c25",
    "t3pf_record_sha256": "4397cee7798f684159ed77aa5e1edd7b7ae0a24378047d6c89b37ef9ef738a52",
    "t2d_reps_sha256": "c6f740510c520167c2ecfbfc48fc2db88428e17ce1b96e6ad5826e507929aedb",
    "derm_summary_sha256": "0a382978f3f3cddd05dbe911fa9cceb7f6243484d649176503770027992458d2",
    "us_axis_manifest_sha256": "e91094bba0810c987cf44a94e4edc467bf8e7a359b48f9915b677b550ca31ec5",
    "us_decisions_sha256": "a7ad22dcc25e5bef7763246d79fad64536fcbb87eef4493037712da8f07199be",
    "prereg_sha256": "b459fab24aad9e890a06e4e960c181fecfe029032aceea24dbe47614f6f101ce",
    "method_sha256": "5acbd5c75274a3cb31202ee9f1c2ac2dc94146abd74439ecd882f8cc58512c40",
    "lexicon_sha256": "564b14ccd71a971bcc6fa8819ccedaae064e2b689c0a0022d81a9c8c2ba54653",
}
EXPECTED_MODEL_STATE_SHA256 = "3f2c393680172fd552aae83bd2f0e3c389457e7d13499e3490c2a314f5642051"

AXIS_SHA = {
    "HAM10000": "0988518fcfbcb3436f43fbdff37b61395b8ba8b3715fccbc295f67cd0ab3dcad",
    "ISIC_MSK1": "5011be88de7e877d836f0518540c53dd3f6a34c57225b729e22285ff1cfcd9d2",
    "ISIC_UDA1": "316857360dd3a4f3c9f19f811cc58a4c17c1da1372319cbcc9382e7eca76b670",
    "BUSI_WHU_2025_V3": "7d09dd72c43d9dc43d574e8d6dea90edd7e5fbb845103d80d824add9bce11963",
    "BUS_BRA_2024": "73ad923e912177b56ff21cab081b0b84e4ae30a37f0f7bea0b1db5c518c774e7",
    "RODRIGUES_BUI_2017": "6f09b1002f3b1928aa2f957e86887213c58e330b5c6eefe616f9a0dad2a6f592",
}
AXIS_PATHS = {
    "HAM10000": DERM_AXIS_ROOT / "HAM10000_Frozen_Source_Axis_v0.1.npz",
    "ISIC_MSK1": DERM_AXIS_ROOT / "ISIC_MSK1_Frozen_Source_Axis_v0.1.npz",
    "ISIC_UDA1": DERM_AXIS_ROOT / "ISIC_UDA1_Frozen_Source_Axis_v0.1.npz",
    "BUSI_WHU_2025_V3": US_AXIS_ROOT / "BUSI_WHU_2025_V3_Frozen_Development_Source_Axis_v0.1.npz",
    "BUS_BRA_2024": US_AXIS_ROOT / "BUS_BRA_2024_Frozen_Development_Source_Axis_v0.1.npz",
    "RODRIGUES_BUI_2017": US_AXIS_ROOT / "RODRIGUES_BUI_2017_Frozen_Development_Source_Axis_v0.1.npz",
}

LOCKED_BLIND = {"BUSI_CAIRO_2019", "OASBUD_2017", "DERM7PT_2019"}
SEED = 20260722
BUDGETS = [8, 16, 32, 64, 128]
N_REPLICATES = 100
RIDGE_C = 3.0
BALANCE_RIDGE = 0.1
WEIGHT_CLIP = (0.1, 10.0)
MIN_BALANCE_ESS = 8.0
PHASH_MAX_DISTANCE = 4
NEAR_COPY_MIN_CORRELATION = 0.995

def now():
    return datetime.now(timezone.utc).isoformat()

def sha_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()

def sha_json(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()

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
    assert claim == expected, f"Unexpected record hash: {path}"
    return value

def notebook_source_sha(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    cells = []
    for cell in value.get("cells", []):
        if cell.get("cell_type") not in {"code", "markdown"}:
            continue
        source = cell.get("source", [])
        source = "".join(source) if isinstance(source, list) else str(source)
        cells.append({"cell_type": cell["cell_type"], "source": source.replace("\r\n", "\n")})
    return sha_json(cells)

def materialise_embedded_text(path, text, expected_sha):
    path = Path(path)
    if path.exists():
        observed = sha_file(path)
        assert observed == expected_sha, f"Embedded protocol file changed: {path} :: {observed}"
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        assert sha_file(path) == expected_sha

materialise_embedded_text(PREREG_PATH, EMBEDDED_PREREG_TEXT, EXPECTED["prereg_sha256"])
materialise_embedded_text(METHOD_PATH, EMBEDDED_METHOD_TEXT, EXPECTED["method_sha256"])
materialise_embedded_text(LEXICON_PATH, EMBEDDED_LEXICON_TEXT, EXPECTED["lexicon_sha256"])
README_PATH.write_text(EMBEDDED_README_TEXT, encoding="utf-8")

required = [
    NOTEBOOK_PATH, PREREG_PATH, METHOD_PATH, LEXICON_PATH,
    T2J_FINAL, T2J_SPLIT, T2J_BREAST_MANIFEST, T2H_FINAL, T3PF_FINAL,
    T2D_REPS, DERM_SUMMARY, US_AXIS_MANIFEST, US_DECISIONS, US_EXACT_MANIFEST,
    HIS_ARCHIVE, *AXIS_PATHS.values(),
]
missing = [str(p) for p in required if not Path(p).is_file()]
assert not missing, "Missing required files:\n" + "\n".join(missing)
assert HIS_ARCHIVE.stat().st_size >= 900 * 1024**2, f"HiSBreast archive too small: {HIS_ARCHIVE.stat().st_size}"

for role, path in {
    "t2j_file_sha256": T2J_FINAL,
    "t2j_split_sha256": T2J_SPLIT,
    "t2h_file_sha256": T2H_FINAL,
    "t3pf_file_sha256": T3PF_FINAL,
    "t2d_reps_sha256": T2D_REPS,
    "derm_summary_sha256": DERM_SUMMARY,
    "us_axis_manifest_sha256": US_AXIS_MANIFEST,
    "us_decisions_sha256": US_DECISIONS,
    "prereg_sha256": PREREG_PATH,
    "method_sha256": METHOD_PATH,
    "lexicon_sha256": LEXICON_PATH,
}.items():
    observed = sha_file(path)
    assert observed == EXPECTED[role], f"Hash mismatch {role}: {observed}"

for source, path in AXIS_PATHS.items():
    observed = sha_file(path)
    assert observed == AXIS_SHA[source], f"Frozen source axis changed: {source}"

t2j = verify_self(T2J_FINAL, "final_record_sha256", EXPECTED["t2j_record_sha256"])
t2h = verify_self(T2H_FINAL, "final_record_sha256", EXPECTED["t2h_record_sha256"])
t3pf = verify_self(T3PF_FINAL, "activation_record_sha256", EXPECTED["t3pf_record_sha256"])
assert t2h["single_pilot_deployment_authorised"] is False
assert t3pf["blind_assets_acquired"] is False
assert t3pf["blind_outcomes_accessed"] is False
assert t3pf["stage12_authorised"] is False

protocol_payload = {
    "stage": "StageT2-KR-v0.4",
    "purpose": "hisbreast_container_json_repair_cpu_source_scoring_and_multibudget_extension",
    "parent_t2j_record": EXPECTED["t2j_record_sha256"],
    "parent_t2h_record": EXPECTED["t2h_record_sha256"],
    "parent_t3pf_record": EXPECTED["t3pf_record_sha256"],
    "preregistration_sha256": EXPECTED["prereg_sha256"],
    "method_sha256": EXPECTED["method_sha256"],
    "lexicon_sha256": EXPECTED["lexicon_sha256"],
    "notebook_source_sha256": notebook_source_sha(NOTEBOOK_PATH),
    "hisbreast_archive_filename": HIS_ARCHIVE.name,
    "hisbreast_archive_size_bytes": HIS_ARCHIVE.stat().st_size,
    "single_pilot_deployment_remains_prohibited": True,
    "locked_blind_assets_touched": False,
    "locked_blind_outcomes_accessed": False,
    "stage12_authorised": False,
}
protocol_path = P0 / "StageT2-KR_Protocol_Seal_v0.4.json"
if protocol_path.exists():
    protocol = verify_self(protocol_path, "protocol_seal_sha256", json.loads(protocol_path.read_text())["protocol_seal_sha256"])
    for key, value in protocol_payload.items():
        assert protocol[key] == value, f"Protocol replay mismatch: {key}"
else:
    protocol = dict(protocol_payload)
    protocol["sealed_utc"] = now()
    protocol["protocol_seal_sha256"] = sha_json(protocol)
    write_json(protocol_path, protocol)

print("HiSBreast archive confirmed:", HIS_ARCHIVE.name, HIS_ARCHIVE.stat().st_size, "bytes")
print("Stage T2-KR protocol:", protocol["protocol_seal_sha256"])
print("Locked blind assets touched:", False)


# @title T2-KR-1. Safely extract HiSBreast, recognise 32 JSON containers and explode released records
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
TEXT_EXTENSIONS = {".txt", ".csv"}

def safe_extract_zip(source, destination):
    source = Path(source)
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    base = destination.resolve()
    with zipfile.ZipFile(source) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if not (target == base or str(target).startswith(str(base) + os.sep)):
                raise RuntimeError(f"Unsafe ZIP member: {member.filename}")
        archive.extractall(destination)

def normalise_text(value):
    value = unicodedata.normalize("NFKD", str(value))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower().replace("đ", "d")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()

existing_images = [p for p in HIS_EXTRACTED.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]
if len(existing_images) < 900:
    print("Extracting official HiSBreast archive...")
    safe_extract_zip(HIS_ARCHIVE, HIS_EXTRACTED)

all_files = sorted(p for p in HIS_EXTRACTED.rglob("*") if p.is_file())
image_paths = [p for p in all_files if p.suffix.lower() in IMAGE_EXTENSIONS and "__MACOSX" not in p.parts]
json_paths = [p for p in all_files if p.suffix.lower() == ".json" and "__MACOSX" not in p.parts]
diagnosis_paths = [p for p in all_files if p.suffix.lower() == ".txt" and "diagnos" in normalise_text(p.parent) and "__MACOSX" not in p.parts]
description_paths = [p for p in all_files if p.suffix.lower() == ".txt" and "description" in normalise_text(p.parent) and "__MACOSX" not in p.parts]
annotation_candidates = [p for p in all_files if p.name.lower() == "hisbreast_anotation.csv"]

assert len(image_paths) >= 900, f"Too few HiSBreast images after extraction: {len(image_paths)}"
assert len(diagnosis_paths) >= 900, f"Too few per-image diagnosis files: {len(diagnosis_paths)}"
assert len(json_paths) >= 1, "No HiSBreast JSON containers found"
assert annotation_candidates, "Official hisbreast_anotation.csv missing"
ANNOTATION_PATH = annotation_candidates[0]

# The official CSV has a generic first header row followed by the semantic header row.
annotation_raw = pd.read_csv(ANNOTATION_PATH, encoding_errors="replace")
if list(annotation_raw.columns)[:2] == ["Column1", "Column2"] and len(annotation_raw):
    semantic_header = annotation_raw.iloc[0].astype(str).tolist()
    annotation = annotation_raw.iloc[1:].copy()
    annotation.columns = semantic_header
else:
    annotation = annotation_raw.copy()
assert len(annotation) >= 900

inventory = pd.DataFrame([{
    "relative_path": str(path.relative_to(HIS_ROOT)),
    "size_bytes": path.stat().st_size,
    "suffix": path.suffix.lower(),
    "top_release_folder": path.relative_to(HIS_EXTRACTED).parts[0] if path.relative_to(HIS_EXTRACTED).parts else "",
} for path in all_files])
write_csv(P1 / "StageT2-KR_HiSBreast_Release_Inventory_v0.4.csv", inventory)
folder_summary = inventory.groupby(["top_release_folder", "suffix"], as_index=False).agg(files=("relative_path", "count"), bytes=("size_bytes", "sum"))
write_csv(P1 / "StageT2-KR_HiSBreast_Folder_Summary_v0.4.csv", folder_summary)
write_csv(P1 / "StageT2-KR_HiSBreast_Official_Annotation_Audit_v0.4.csv", annotation)

def flatten_json(value, prefix="", output=None):
    if output is None:
        output = {}
    if isinstance(value, dict):
        for key, child in value.items():
            key_path = f"{prefix}.{key}" if prefix else str(key)
            key_norm = normalise_text(key)
            if any(token in key_norm for token in ["base64", "image data", "image base", "anh base"]):
                continue
            flatten_json(child, key_path, output)
    elif isinstance(value, list):
        if len(value) <= 30 and all(not isinstance(x, (dict, list)) for x in value):
            output[prefix] = " | ".join(str(x) for x in value)
    elif isinstance(value, (str, int, float, bool)) or value is None:
        text = "" if value is None else str(value)
        if len(text) <= 10000:
            output[prefix] = text
    return output

def extract_record_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        priority = ["data", "records", "items", "tasks", "images", "annotations", "results"]
        for key in priority:
            child = value.get(key)
            if isinstance(child, list) and len(child):
                return child
        candidates = [child for child in value.values() if isinstance(child, list) and len(child)]
        record_like = [child for child in candidates if sum(isinstance(x, dict) for x in child) >= max(1, len(child)//2)]
        if record_like:
            return max(record_like, key=len)
        return [value]
    return [value]

json_rows, json_container_rows, json_errors = [], [], []
for path in json_paths:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
        records = extract_record_list(value)
        json_container_rows.append({"json_path": str(path), "container_filename": path.name, "expanded_records": len(records), "parse_status": "PASS"})
        for index, record in enumerate(records):
            flat = flatten_json(record)
            json_rows.append({
                "record_stem": f"{path.name}_{index}",
                "container_filename": path.name,
                "container_index": index,
                "json_path": str(path),
                **flat,
            })
    except Exception as exc:
        json_errors.append({"json_path": str(path), "error": f"{type(exc).__name__}: {exc}"})

json_frame = pd.DataFrame(json_rows)
JSON_CONTAINER_EXPANSION_PASS = len(json_frame) >= 900
write_csv(P1 / "StageT2-KR_HiSBreast_JSON_Container_Audit_v0.4.csv", pd.DataFrame(json_container_rows))
write_csv(P1 / "StageT2-KR_HiSBreast_JSON_Parse_Errors_v0.4.csv", pd.DataFrame(json_errors))

field_rows = []
if len(json_frame):
    for column in [c for c in json_frame.columns if c not in {"record_stem", "container_filename", "container_index", "json_path"}]:
        values = json_frame[column].astype(str).replace({"": np.nan, "nan": np.nan})
        nonempty = values.dropna()
        field_rows.append({
            "field": column,
            "normalised_field": normalise_text(column),
            "coverage": float(len(nonempty) / len(json_frame)),
            "unique_nonempty": int(nonempty.nunique()),
            "uniqueness_ratio": float(nonempty.nunique() / max(1, len(nonempty))),
            "example_values": " || ".join(nonempty.drop_duplicates().head(5).astype(str)),
        })
field_audit = pd.DataFrame(field_rows)
if len(field_audit):
    field_audit = field_audit.sort_values(["coverage", "field"], ascending=[False, True])
else:
    field_audit = pd.DataFrame(columns=["field", "normalised_field", "coverage", "unique_nonempty", "uniqueness_ratio", "example_values"])
write_csv(P1 / "StageT2-KR_HiSBreast_JSON_Field_Audit_v0.4.csv", field_audit)

print("HiSBreast images / diagnosis files / JSON containers / expanded JSON records / annotation rows:", len(image_paths), len(diagnosis_paths), len(json_paths), len(json_frame), len(annotation))
display(folder_summary)
display(pd.DataFrame(json_container_rows).sort_values("expanded_records", ascending=False).head(20))

# @title T2-KR-2. Recover patient grouping and map exact per-image diagnosis files conservatively
def patient_semantic_score(field):
    text = normalise_text(field)
    score = 0
    strong = ["ma benh nhan", "ma bn", "mabn", "patient code", "patient id", "patientcode", "patientid", "id benh nhan"]
    medium = ["benh nhan", "patient", "subject id", "subject code", "medical record", "hospital id"]
    if any(token in text for token in strong): score += 10
    elif any(token in text for token in medium): score += 5
    if any(token in text for token in ["image", "anh", "file", "filename", "diagn", "chan doan", "description"]): score -= 8
    return score

patient_candidates = field_audit.copy()
if len(patient_candidates):
    patient_candidates["semantic_score"] = patient_candidates["field"].map(patient_semantic_score)
    patient_candidates = patient_candidates[(patient_candidates["semantic_score"] > 0) & (patient_candidates["coverage"] >= 0.80)].sort_values(
        ["semantic_score", "coverage", "uniqueness_ratio", "field"], ascending=[False, False, True, True]
    )
else:
    patient_candidates["semantic_score"] = pd.Series(dtype=float)
PATIENT_FIELD = patient_candidates.iloc[0]["field"] if len(patient_candidates) else None
PATIENT_FIELD_STATUS = "PASS_EXPLICIT_RELEASED_PATIENT_CODE" if PATIENT_FIELD is not None else "HOLD_NO_EXPLICIT_RELEASED_PATIENT_CODE"

def read_text_flexible(path):
    data = Path(path).read_bytes()
    for encoding in ["utf-8-sig", "utf-8", "utf-16", "cp1258", "latin-1"]:
        try: return data.decode(encoding)
        except Exception: pass
    return data.decode("utf-8", errors="replace")

diagnosis_file_map = {normalise_text(path.stem): read_text_flexible(path).strip() for path in diagnosis_paths}
description_file_map = {normalise_text(path.stem): read_text_flexible(path).strip() for path in description_paths}
image_map = {normalise_text(path.stem): path for path in image_paths}
json_lookup = {normalise_text(row["record_stem"]): row for row in json_frame.to_dict("records")} if len(json_frame) else {}

lexicon = pd.read_csv(LEXICON_PATH)
assert {"category", "normalised_regex", "strength"}.issubset(lexicon.columns)
negated_positive_patterns = lexicon[(lexicon["category"] == "negative") & lexicon["normalised_regex"].astype(str).str.contains("khong")]["normalised_regex"].tolist()

def map_diagnosis(text):
    original = str(text or "").strip()
    normalized = normalise_text(original)
    positive_scan = normalized
    for pattern in negated_positive_patterns:
        positive_scan = re.sub(pattern, " ", positive_scan)
    hits = []
    for row in lexicon.itertuples():
        scan = positive_scan if row.category == "positive" else normalized
        if re.search(str(row.normalised_regex), scan):
            hits.append({"category": row.category, "strength": row.strength, "pattern": row.normalised_regex, "interpretation": row.interpretation})
    strong_pos = [h for h in hits if h["category"] == "positive" and h["strength"] == "strong"]
    strong_neg = [h for h in hits if h["category"] == "negative" and h["strength"] == "strong"]
    any_pos = [h for h in hits if h["category"] == "positive"]
    any_neg = [h for h in hits if h["category"] == "negative"]
    normal = [h for h in hits if h["category"] == "normal_exclude"]
    ambiguous = [h for h in hits if h["category"] == "ambiguous_hold"]
    if strong_pos and strong_neg: status, label = "CONFLICT_STRONG_POSITIVE_AND_NEGATIVE", np.nan
    elif strong_pos: status, label = "INCLUDE_MALIGNANT", 1
    elif strong_neg: status, label = "INCLUDE_BENIGN", 0
    elif any_pos and any_neg: status, label = "CONFLICT_WEAK_OR_MODERATE_ANCHORS", np.nan
    elif any_pos: status, label = "INCLUDE_MALIGNANT", 1
    elif any_neg: status, label = "INCLUDE_BENIGN", 0
    elif normal: status, label = "EXCLUDE_NORMAL", np.nan
    elif ambiguous: status, label = "HOLD_AMBIGUOUS", np.nan
    else: status, label = "HOLD_UNMAPPED", np.nan
    return {"diagnosis_original": original, "diagnosis_normalised": normalized, "label_status": status, "binary_label": label, "lexicon_hits_json": json.dumps(hits, ensure_ascii=False)}

# Frozen implementation assertions: serialization and normalized ICD grammar only.
assert map_diagnosis("C50-U ác của vú")["label_status"] == "INCLUDE_MALIGNANT"
assert map_diagnosis("D24-U lành vú")["label_status"] == "INCLUDE_BENIGN"
assert map_diagnosis("N64-Biến đổi khác ở vú")["label_status"] == "HOLD_AMBIGUOUS"
assert map_diagnosis("D48.6-U tân sinh không xác định")["label_status"] == "HOLD_AMBIGUOUS"

record_rows = []
for stem_key, image_path in sorted(image_map.items()):
    record = json_lookup.get(stem_key, {})
    diagnosis_text = diagnosis_file_map.get(stem_key, "")
    description_text = description_file_map.get(stem_key, "")
    patient_raw = str(record.get(PATIENT_FIELD, "") if PATIENT_FIELD else "").strip()
    mapped = map_diagnosis(diagnosis_text)
    record_rows.append({
        "sample_id": image_path.stem,
        "json_record_key": str(record.get("record_stem", "")),
        "json_path": str(record.get("json_path", "")),
        "json_record_matched": bool(record),
        "container_batch": re.sub(r"_\\d+$", "", image_path.stem),
        "image_path": str(image_path),
        "image_present": True,
        "diagnosis_file_present": stem_key in diagnosis_file_map,
        "description_original": description_text,
        "patient_field": PATIENT_FIELD or "",
        "patient_code_raw": patient_raw,
        "patient_code_present": bool(patient_raw),
        **mapped,
    })

his_records = pd.DataFrame(record_rows)
his_records["group_id"] = np.where(his_records["patient_code_present"], "HISBREAST_V2::PATIENT::" + his_records["patient_code_raw"].astype(str), "")
patient_coverage = float(his_records["patient_code_present"].mean()) if len(his_records) else 0.0
json_match_rate = float(his_records["json_record_matched"].mean()) if len(his_records) else 0.0
diagnosis_coverage = float(his_records["diagnosis_file_present"].mean()) if len(his_records) else 0.0

diagnosis_dictionary = his_records.groupby(["diagnosis_original", "diagnosis_normalised", "label_status", "binary_label"], dropna=False, as_index=False).agg(samples=("sample_id", "count")).sort_values(["label_status", "samples"], ascending=[True, False])
patient_selection = pd.DataFrame([{
    "selected_patient_field": PATIENT_FIELD or "",
    "status": PATIENT_FIELD_STATUS,
    "record_coverage": patient_coverage,
    "unique_patient_codes": int(his_records.loc[his_records["patient_code_present"], "patient_code_raw"].nunique()),
    "samples": int(len(his_records)),
    "json_container_count": int(len(json_paths)),
    "json_expanded_records": int(len(json_frame)),
    "json_record_match_rate": json_match_rate,
    "diagnosis_file_coverage": diagnosis_coverage,
}])

write_csv(P1 / "StageT2-KR_HiSBreast_Patient_Field_Candidate_Audit_v0.4.csv", patient_candidates)
write_csv(P1 / "StageT2-KR_HiSBreast_Patient_Field_Selection_v0.4.csv", patient_selection)
write_csv(P1 / "StageT2-KR_HiSBreast_Diagnosis_Dictionary_v0.4.csv", diagnosis_dictionary)
write_csv(P1 / "StageT2-KR_HiSBreast_PreDedup_Record_Manifest_v0.4.csv", his_records)
display(patient_selection)
display(his_records["label_status"].value_counts().rename_axis("label_status").reset_index(name="samples"))
display(diagnosis_dictionary.head(50))

# @title T2-K-3. Fingerprint, deduplicate and conditionally freeze a patient-grouped HiSBreast split
def image_fingerprint(path):
    path = Path(path)
    data = path.read_bytes()
    with Image.open(io.BytesIO(data)) as image0:
        image = ImageOps.exif_transpose(image0).convert("RGB")
        width, height = image.size
        rgb = np.asarray(image, dtype=np.uint8)
        header = json.dumps(
            {"width": width, "height": height, "mode": "RGB"},
            sort_keys=True, separators=(",", ":")
        ).encode() + b"\0"
        pixel_sha = sha_bytes(header + rgb.tobytes(order="C"))
        gray = np.asarray(
            image.convert("L").resize((32, 32), Image.Resampling.LANCZOS),
            dtype=np.float32,
        )
        low = dctn(gray, type=2, norm="ortho")[:8, :8]
        median = float(np.median(low.flatten()[1:]))
        bits = (low.flatten() > median).astype(np.uint8)
        phash = 0
        for bit in bits:
            phash = (phash << 1) | int(bit)
        thumb = np.asarray(
            image.convert("L").resize((32, 32), Image.Resampling.BILINEAR),
            dtype=np.uint8,
        )
    return {
        "raw_image_sha256": sha_bytes(data),
        "pixel_sha256": pixel_sha,
        "pixel_width": int(width),
        "pixel_height": int(height),
        "pixel_mode": "RGB",
        "phash64": f"{phash:016x}",
        "thumb32_b64": base64.b64encode(thumb.tobytes(order="C")).decode("ascii"),
        "decode_ok": True,
    }

def decode_thumb(value):
    array = np.frombuffer(base64.b64decode(value), dtype=np.uint8).astype(np.float32)
    array = array.reshape(32, 32).ravel()
    return (array - array.mean()) / (array.std() + 1e-8)

def phash_distance(a, b):
    return (int(str(a), 16) ^ int(str(b), 16)).bit_count()

def thumb_corr(a, b):
    x, y = decode_thumb(a), decode_thumb(b)
    return float(np.dot(x, y) / len(x))

eligible_mask = (
    his_records["label_status"].isin(["INCLUDE_MALIGNANT", "INCLUDE_BENIGN"]) &
    his_records["image_present"] &
    his_records["patient_code_present"]
)
his_records["dedup_status"] = np.where(
    eligible_mask, "KEEP_PENDING_FINGERPRINT",
    np.where(~his_records["image_present"], "HOLD_IMAGE_MISSING",
    np.where(~his_records["patient_code_present"], "HOLD_PATIENT_CODE_MISSING",
             his_records["label_status"]))
)

fingerprint_rows = []
for count, (index, row) in enumerate(his_records[eligible_mask].iterrows(), 1):
    try:
        fingerprint_rows.append({"row_index": index, **image_fingerprint(row["image_path"]), "fingerprint_error": ""})
    except Exception as exc:
        fingerprint_rows.append({
            "row_index": index, "decode_ok": False,
            "fingerprint_error": f"{type(exc).__name__}: {exc}",
        })
    if count % 200 == 0:
        print("HiSBreast fingerprints:", count, "/", int(eligible_mask.sum()))

fp = pd.DataFrame(fingerprint_rows).set_index("row_index") if fingerprint_rows else pd.DataFrame()
for column in [
    "raw_image_sha256", "pixel_sha256", "pixel_width", "pixel_height",
    "pixel_mode", "phash64", "thumb32_b64", "decode_ok", "fingerprint_error",
]:
    his_records[column] = fp[column] if column in fp.columns else np.nan

his_records.loc[
    eligible_mask & ~his_records["decode_ok"].fillna(False),
    "dedup_status"
] = "HOLD_IMAGE_DECODE_FAILURE"

dedup_audit = []

# Internal exact duplicates.
pending = his_records[his_records["dedup_status"].eq("KEEP_PENDING_FINGERPRINT")]
for pixel_sha, group in pending.groupby("pixel_sha256", dropna=True):
    if len(group) < 2:
        continue
    labels = sorted(group["binary_label"].astype(int).unique())
    ordered = group.sort_values(["patient_code_raw", "sample_id"])
    if len(labels) > 1:
        action = "QUARANTINE_INTERNAL_EXACT_LABEL_CONFLICT"
        his_records.loc[ordered.index, "dedup_status"] = action
    else:
        action = "EXCLUDE_INTERNAL_EXACT_PIXEL_DUPLICATE"
        his_records.loc[ordered.index[1:], "dedup_status"] = action
    dedup_audit.append({
        "scope": "internal_exact", "candidate_sample": ordered.iloc[-1]["sample_id"],
        "reference_sample": ordered.iloc[0]["sample_id"], "action": action,
        "phash_distance": 0, "thumbnail_correlation": 1.0,
    })

# Internal high-confidence near copies.
pending_records = list(
    his_records[his_records["dedup_status"].eq("KEEP_PENDING_FINGERPRINT")].itertuples()
)
for i, left in enumerate(pending_records):
    if his_records.loc[left.Index, "dedup_status"] != "KEEP_PENDING_FINGERPRINT":
        continue
    for right in pending_records[i + 1:]:
        if his_records.loc[right.Index, "dedup_status"] != "KEEP_PENDING_FINGERPRINT":
            continue
        distance = phash_distance(left.phash64, right.phash64)
        if distance > PHASH_MAX_DISTANCE:
            continue
        correlation = thumb_corr(left.thumb32_b64, right.thumb32_b64)
        if correlation < NEAR_COPY_MIN_CORRELATION:
            continue
        if int(left.binary_label) != int(right.binary_label):
            action = "QUARANTINE_INTERNAL_NEAR_COPY_LABEL_CONFLICT"
            his_records.loc[[left.Index, right.Index], "dedup_status"] = action
        else:
            action = "EXCLUDE_INTERNAL_HIGH_CONFIDENCE_NEAR_COPY"
            loser = max(left.Index, right.Index)
            his_records.loc[loser, "dedup_status"] = action
        dedup_audit.append({
            "scope": "internal_near", "candidate_sample": right.sample_id,
            "reference_sample": left.sample_id, "action": action,
            "phash_distance": distance, "thumbnail_correlation": correlation,
        })

# Cross-roster exact and conservative pHash review against existing ultrasound and BrEaST.
existing_us = pd.read_csv(US_EXACT_MANIFEST)
existing_breast = pd.read_csv(T2J_BREAST_MANIFEST)
reference = pd.concat([
    existing_us.rename(columns={
        "dataset_id": "reference_dataset",
        "sample_id": "reference_sample",
        "binary_label": "reference_label",
    })[["reference_dataset", "reference_sample", "reference_label", "pixel_sha256", "phash64"]],
    existing_breast.rename(columns={
        "dataset": "reference_dataset",
        "image_id": "reference_sample",
        "label": "reference_label",
    })[["reference_dataset", "reference_sample", "reference_label", "pixel_sha256", "phash64"]],
], ignore_index=True)
reference = reference.dropna(subset=["pixel_sha256", "phash64"])

pixel_lookup = {
    pixel_sha: group.to_dict("records")
    for pixel_sha, group in reference.groupby("pixel_sha256")
}

for index in his_records.index[his_records["dedup_status"].eq("KEEP_PENDING_FINGERPRINT")]:
    row = his_records.loc[index]
    exact = pixel_lookup.get(row["pixel_sha256"], [])
    if exact:
        labels = sorted(set(int(item["reference_label"]) for item in exact if pd.notna(item["reference_label"])))
        action = (
            "QUARANTINE_CROSS_ROSTER_EXACT_LABEL_CONFLICT"
            if labels and int(row["binary_label"]) not in labels
            else "EXCLUDE_CROSS_ROSTER_EXACT_PIXEL_DUPLICATE"
        )
        his_records.loc[index, "dedup_status"] = action
        dedup_audit.append({
            "scope": "cross_exact", "candidate_sample": row["sample_id"],
            "reference_sample": exact[0]["reference_sample"], "action": action,
            "phash_distance": 0, "thumbnail_correlation": np.nan,
        })
        continue
    candidate_hash = int(str(row["phash64"]), 16)
    best = None
    for ref in reference.itertuples():
        distance = (candidate_hash ^ int(str(ref.phash64), 16)).bit_count()
        if distance <= PHASH_MAX_DISTANCE:
            score = (distance, str(ref.reference_dataset), str(ref.reference_sample))
            if best is None or score < best[0]:
                best = (score, ref)
    if best is not None:
        ref = best[1]
        action = "HOLD_CROSS_ROSTER_PHASH_NEAR_COPY_REVIEW"
        his_records.loc[index, "dedup_status"] = action
        dedup_audit.append({
            "scope": "cross_phash", "candidate_sample": row["sample_id"],
            "reference_sample": ref.reference_sample, "action": action,
            "phash_distance": best[0][0], "thumbnail_correlation": np.nan,
        })

his_records.loc[
    his_records["dedup_status"].eq("KEEP_PENDING_FINGERPRINT"),
    "dedup_status"
] = "KEEP_UNIQUE"

retained = his_records[his_records["dedup_status"].eq("KEEP_UNIQUE")].copy()
group_label_counts = retained.groupby("group_id")["binary_label"].nunique()
mixed_groups = group_label_counts[group_label_counts > 1].index.tolist()

patient_coverage = float(his_records["patient_code_present"].mean())
mapped_binary_rate = float(his_records["label_status"].isin(["INCLUDE_MALIGNANT", "INCLUDE_BENIGN"]).mean())
class_groups = retained.groupby("binary_label")["group_id"].nunique().to_dict()

HIS_ADAPTER_PASS = bool(
    PATIENT_FIELD is not None
    and patient_coverage >= 0.80
    and json_match_rate >= 0.80
    and diagnosis_coverage >= 0.95
    and mapped_binary_rate >= 0.50
    and class_groups.get(0.0, 0) >= 30
    and class_groups.get(1.0, 0) >= 30
    and retained["group_id"].nunique() >= 80
)

his_split = pd.DataFrame()
if HIS_ADAPTER_PASS:
    group_table = retained.groupby("group_id", as_index=False).agg(
        negative=("binary_label", lambda x: int((x == 0).sum())),
        positive=("binary_label", lambda x: int((x == 1).sum())),
        images=("sample_id", "count"),
    )
    group_table["stratum"] = np.where(
        (group_table["negative"] > 0) & (group_table["positive"] > 0),
        "mixed",
        np.where(group_table["positive"] > 0, "positive", "negative"),
    )
    stratify = group_table["stratum"] if group_table["stratum"].value_counts().min() >= 2 else None
    train_groups, validation_groups = train_test_split(
        group_table, test_size=0.20, random_state=SEED, stratify=stratify
    )
    partition = {
        **{g: "development" for g in train_groups["group_id"]},
        **{g: "validation" for g in validation_groups["group_id"]},
    }
    his_split = retained.copy()
    his_split["dataset"] = "HISBREAST_V2"
    his_split["modality"] = "breast_ultrasound"
    his_split["task"] = "breast_lesion_malignant_vs_benign"
    his_split["image_id"] = his_split["sample_id"]
    his_split["unit_id"] = "HISBREAST_V2::IMAGE::" + his_split["sample_id"].astype(str)
    his_split["label"] = his_split["binary_label"].astype(int)
    his_split["source_locator"] = his_split["image_path"]
    his_split["partition"] = his_split["group_id"].map(partition)
    assert his_split.groupby("group_id")["partition"].nunique().max() == 1
    assert his_split.groupby("partition")["label"].nunique().min() == 2

write_csv(P1 / "StageT2-KR_HiSBreast_PostDedup_Manifest_v0.4.csv", his_records)
write_csv(P1 / "StageT2-KR_HiSBreast_Dedup_Audit_v0.4.csv", pd.DataFrame(dedup_audit))
write_csv(P1 / "StageT2-KR_HiSBreast_Grouped_Split_Manifest_v0.4.csv", his_split)

his_summary = pd.DataFrame([{
    "official_images_found": len(image_paths),
    "json_records": len(json_frame),
    "patient_field": PATIENT_FIELD or "",
    "patient_field_status": PATIENT_FIELD_STATUS,
    "patient_code_coverage": patient_coverage,
    "json_record_match_rate": json_match_rate,
    "diagnosis_file_coverage": diagnosis_coverage,
    "mapped_binary_rate": mapped_binary_rate,
    "mapped_negative_samples": int(his_records["binary_label"].eq(0).sum()),
    "mapped_positive_samples": int(his_records["binary_label"].eq(1).sum()),
    "retained_unique_images": int(len(retained)),
    "retained_groups": int(retained["group_id"].nunique()),
    "mixed_label_groups": int(len(mixed_groups)),
    "adapter_pass": HIS_ADAPTER_PASS,
}])
write_csv(P1 / "StageT2-KR_HiSBreast_Adjudication_Summary_v0.4.csv", his_summary)
display(his_summary)
display(his_records["dedup_status"].value_counts().rename_axis("status").reset_index(name="samples"))


# @title T2-KR-4. Assemble the frozen expansion target roster
base_split = pd.read_csv(T2J_SPLIT)
assert set(base_split["dataset"]) == {"ISIC_MILK10K", "BREAST_LESIONS_USG"}
assert base_split.groupby(["dataset", "group_id"])["partition"].nunique().max() == 1

base_targets = base_split[[
    "dataset", "modality", "task", "image_id", "unit_id", "group_id",
    "label", "source_locator", "partition", "raw_image_sha256"
]].copy()
base_targets["extension_status"] = "T2J_SPLIT_READY"

target_frames = [base_targets]
if HIS_ADAPTER_PASS:
    his_target = his_split[[
        "dataset", "modality", "task", "image_id", "unit_id", "group_id",
        "label", "source_locator", "partition", "raw_image_sha256"
    ]].copy()
    his_target["extension_status"] = "T2KR_CONDITIONAL_ADAPTER_PASS"
    target_frames.append(his_target)

target_roster = pd.concat(target_frames, ignore_index=True)
assert target_roster.groupby(["dataset", "group_id"])["partition"].nunique().max() == 1
assert target_roster.groupby("dataset")["label"].nunique().min() == 2
assert not any(token.lower() in " ".join(target_roster["source_locator"].astype(str)).lower() for token in LOCKED_BLIND)

target_summary = (
    target_roster.groupby(["dataset", "modality", "task"], as_index=False)
    .agg(
        images=("image_id", "count"),
        groups=("group_id", "nunique"),
        negative=("label", lambda x: int((x == 0).sum())),
        positive=("label", lambda x: int((x == 1).sum())),
    )
)
# Replace partition summaries explicitly.
part_counts = (
    target_roster.groupby(["dataset", "partition"])["group_id"]
    .nunique().unstack(fill_value=0)
)
target_summary["development_groups"] = target_summary["dataset"].map(part_counts.get("development", pd.Series(dtype=int))).fillna(0).astype(int)
target_summary["validation_groups"] = target_summary["dataset"].map(part_counts.get("validation", pd.Series(dtype=int))).fillna(0).astype(int)

write_csv(P2 / "StageT2-KR_Frozen_Expansion_Target_Roster_v0.4.csv", target_roster)
write_csv(P2 / "StageT2-KR_Expansion_Target_Summary_v0.4.csv", target_summary)
display(target_summary)


# @title T2-KR-5. Compute frozen ResNet-50 embeddings and source-axis scores
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision
from torch.utils.data import Dataset, DataLoader
from torchvision.models import resnet50, ResNet50_Weights
from tqdm.auto import tqdm

random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
if torch.cuda.is_available():
    torch.cuda.manual_seed_all(SEED)
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True

torch.set_num_threads(max(1, min(8, os.cpu_count() or 2)))
DEVICE = torch.device("cpu")
WEIGHTS = ResNet50_Weights.IMAGENET1K_V2
TRANSFORM = WEIGHTS.transforms(antialias=True)
MODEL = resnet50(weights=WEIGHTS)
MODEL.fc = nn.Identity()
MODEL.eval().to(DEVICE)

def model_state_sha256(model):
    h = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        h.update(name.encode() + b"\0")
        array = tensor.detach().cpu().contiguous().numpy()
        h.update(str(array.dtype).encode() + b"\0")
        h.update(np.asarray(array.shape, dtype=np.int64).tobytes())
        h.update(array.tobytes(order="C"))
    return h.hexdigest()

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
        if str(row.get("raw_image_sha256", "")).strip():
            assert sha_bytes(data) == str(row["raw_image_sha256"])
        with Image.open(io.BytesIO(data)) as image0:
            image = ImageOps.exif_transpose(image0).convert("RGB")
            tensor = TRANSFORM(image)
        return tensor, index

DERM_SOURCES = ["HAM10000", "ISIC_MSK1", "ISIC_UDA1"]
US_SOURCES = ["BUSI_WHU_2025_V3", "BUS_BRA_2024", "RODRIGUES_BUI_2017"]
SOURCE_BY_MODALITY = {
    "dermoscopy": DERM_SOURCES,
    "breast_ultrasound": US_SOURCES,
}

derm_summary = pd.read_csv(DERM_SUMMARY).set_index("source")
us_decisions = pd.read_csv(US_DECISIONS).set_index("dataset_id")
SOURCE_VALIDATION_AUC = {
    **{s: float(derm_summary.loc[s, "validation_auc"]) for s in DERM_SOURCES},
    **{s: float(us_decisions.loc[s, "heldout_auc"]) for s in US_SOURCES},
}

embedding_manifest_rows = []
score_rows = []
axis_schema_rows = []

for dataset_id, frame in target_roster.groupby("dataset", sort=True):
    frame = frame.sort_values("image_id").reset_index(drop=True)
    embedding_path = P3 / f"{dataset_id}_Frozen_ResNet50_V2_Embeddings_v0.1.npy"
    ids_path = P3 / f"{dataset_id}_Embedding_Image_IDs_v0.1.npy"
    expected_ids = np.asarray(frame["image_id"].astype(str).tolist(), dtype=np.str_)

    # Import the previous partial CPU embedding only after strict numerical checks.
    if not embedding_path.exists():
        for legacy_root in LEGACY_CACHE_ROOTS:
            legacy_embedding_path = legacy_root / embedding_path.name
            legacy_ids_path = legacy_root / ids_path.name
            if not legacy_embedding_path.exists():
                continue
            legacy = np.load(legacy_embedding_path, mmap_mode="r", allow_pickle=False)
            ids_valid = True
            if legacy_ids_path.exists():
                try:
                    legacy_ids = np.load(legacy_ids_path, allow_pickle=False).astype(str)
                    ids_valid = bool(np.array_equal(legacy_ids, expected_ids))
                except Exception:
                    ids_valid = False
            legacy_valid = bool(
                ids_valid
                and legacy.ndim == 2
                and legacy.shape == (len(frame), 2048)
                and np.isfinite(np.asarray(legacy)).all()
                and np.max(np.abs(np.linalg.norm(np.asarray(legacy), axis=1) - 1.0)) < 2e-5
            )
            if legacy_valid:
                shutil.copy2(legacy_embedding_path, embedding_path)
                np.save(ids_path, expected_ids, allow_pickle=False)
                print("Imported verified legacy embedding:", dataset_id, "from", legacy_root.name)
                break

    if embedding_path.exists() and ids_path.exists():
        saved_ids = np.load(ids_path, allow_pickle=False).astype(str)
        assert np.array_equal(saved_ids, expected_ids)
        embeddings = np.load(embedding_path, mmap_mode="r", allow_pickle=False)
    else:
        dataset = TargetImageDataset(frame)
        loader = DataLoader(
            dataset, batch_size=24,
            shuffle=False, num_workers=2, pin_memory=False
        )
        chunks = []
        for images, indices in tqdm(loader, desc=f"Embedding {dataset_id}"):
            images = images.to(DEVICE, non_blocking=True)
            with torch.inference_mode():
                features = F.normalize(MODEL(images), p=2, dim=1)
            chunks.append(features.cpu().numpy().astype(np.float32))
        embeddings_array = np.concatenate(chunks, axis=0)
        assert embeddings_array.shape == (len(frame), 2048)
        np.save(embedding_path, embeddings_array, allow_pickle=False)
        np.save(ids_path, expected_ids, allow_pickle=False)
        assert np.array_equal(np.load(ids_path, allow_pickle=False).astype(str), expected_ids)
        embeddings = np.load(embedding_path, mmap_mode="r", allow_pickle=False)

    norms = np.linalg.norm(np.asarray(embeddings), axis=1)
    assert np.max(np.abs(norms - 1.0)) < 2e-5
    modality = frame["modality"].iloc[0]
    sources = SOURCE_BY_MODALITY[modality]

    for source in sources:
        axis_path = AXIS_PATHS[source]
        with np.load(axis_path, allow_pickle=False) as axis:
            keys = set(axis.files)
            if "dataset_id" in keys:
                identity_key = "dataset_id"
            elif "source" in keys:
                identity_key = "source"
            else:
                raise KeyError(f"No frozen source identity field in {axis_path.name}: {sorted(keys)}")
            assert str(axis[identity_key]) == source

            if {"coefficient_raw", "intercept_raw"}.issubset(keys):
                coefficient_key, intercept_key = "coefficient_raw", "intercept_raw"
                axis_schema = "STAGE11ER_DATASET_ID_COEFFICIENT_RAW"
            elif {"raw_coefficient", "raw_intercept"}.issubset(keys):
                coefficient_key, intercept_key = "raw_coefficient", "raw_intercept"
                axis_schema = "STAGE8_SOURCE_RAW_COEFFICIENT"
            else:
                raise KeyError(f"No documented raw-parameter pair in {axis_path.name}: {sorted(keys)}")

            coefficient = np.asarray(axis[coefficient_key], dtype=np.float64)
            intercept = float(axis[intercept_key])
            assert coefficient.shape == (2048,)
            assert np.isfinite(coefficient).all() and np.isfinite(intercept)
            if "model_state_sha256" in keys:
                assert str(axis["model_state_sha256"]) == MODEL_STATE_SHA256

        axis_schema_rows.append({
            "source": source,
            "axis_filename": axis_path.name,
            "axis_sha256": sha_file(axis_path),
            "identity_key": identity_key,
            "coefficient_key": coefficient_key,
            "intercept_key": intercept_key,
            "schema": axis_schema,
            "model_state_sha256_present": "model_state_sha256" in keys,
            "dimension": int(coefficient.shape[0]),
        })
        scores = np.asarray(embeddings, dtype=np.float64) @ coefficient + intercept
        for row, score in zip(frame.itertuples(), scores):
            score_rows.append({
                "target": dataset_id,
                "modality": modality,
                "source": source,
                "edge_id": f"{source}__TO__{dataset_id}",
                "image_id": row.image_id,
                "unit_id": row.unit_id,
                "group_id": row.group_id,
                "label": int(row.label),
                "partition": row.partition,
                "logit": float(score),
                "probability": float(1 / (1 + np.exp(-np.clip(score, -60, 60)))),
                "source_validation_auc": SOURCE_VALIDATION_AUC[source],
            })

    embedding_manifest_rows.append({
        "target": dataset_id,
        "images": len(frame),
        "dimension": int(embeddings.shape[1]),
        "model_state_sha256": MODEL_STATE_SHA256,
        "embedding_sha256": sha_file(embedding_path),
        "image_ids_sha256": sha_file(ids_path),
        "maximum_l2_norm_error": float(np.max(np.abs(norms - 1.0))),
        "device": str(DEVICE),
    })
    gc.collect()

source_scores = pd.DataFrame(score_rows)
embedding_manifest = pd.DataFrame(embedding_manifest_rows)
assert source_scores.groupby(["target", "source", "unit_id"]).size().max() == 1
assert source_scores.groupby(["target", "unit_id"])["label"].nunique().max() == 1

truth_rows = []
for (target, modality, source, edge_id), frame in source_scores.groupby(
    ["target", "modality", "source", "edge_id"]
):
    truth_rows.append({
        "target": target,
        "modality": modality,
        "source": source,
        "edge_id": edge_id,
        "true_auc": float(roc_auc_score(frame["label"], frame["logit"])),
        "source_validation_auc": float(frame["source_validation_auc"].iloc[0]),
        "units": int(frame["unit_id"].nunique()),
        "groups": int(frame["group_id"].nunique()),
    })
truth_table = pd.DataFrame(truth_rows)

write_csv(P3 / "StageT2-KR_Frozen_Embedding_Manifest_v0.4.csv", embedding_manifest)
write_csv(P3 / "StageT2-KR_Frozen_Axis_Schema_Audit_v0.4.csv", pd.DataFrame(axis_schema_rows))
write_csv(P3 / "StageT2-KR_Frozen_Source_Score_Predictions_v0.4.csv", source_scores)
write_csv(P3 / "StageT2-KR_Expansion_Edge_Truth_Table_v0.4.csv", truth_table)
display(embedding_manifest)
display(truth_table)
print("Execution device:", DEVICE)


# @title T2-KR-6. Seal the old 13-target expected-budget model before new multi-budget truth is constructed
old_t2d = pd.read_csv(T2D_REPS)
assert old_t2d["target"].nunique() == 13
assert set(old_t2d["budget"].unique()) == set(BUDGETS)

old_curve = (
    old_t2d[old_t2d["method"].eq("amw_ddet")]
    .groupby(["target", "modality", "budget"], as_index=False)
    .agg(median_error=("absolute_error", "median"))
)
old_budget_rows = []
for (target, modality), frame in old_curve.groupby(["target", "modality"]):
    found = None
    for budget in BUDGETS:
        row = frame[frame["budget"].eq(budget)]
        if len(row) and float(row["median_error"].iloc[0]) <= 0.04:
            found = budget
            break
    operational = found if found is not None else 256
    old_budget_rows.append({
        "target": target,
        "modality": modality,
        "minimum_budget_operational": operational,
        "log2_minimum_budget": math.log2(operational),
    })
old_budget_target = pd.DataFrame(old_budget_rows)

old_b8 = old_t2d[old_t2d["budget"].eq(8)]
old_pivot = old_b8.pivot_table(
    index=["target", "modality", "replicate", "edge_id"],
    columns="method", values="estimate_auc"
).reset_index()
legal_methods = [
    "random_direct", "random_logistic_plugin", "random_joint_gmm",
    "active_direct", "amw_ddet",
]
old_pivot["cross_method_sd"] = old_pivot[legal_methods].std(axis=1)
old_pilot_rep = (
    old_pivot.groupby(["target", "modality", "replicate"], as_index=False)
    .agg(pilot_disagreement=("cross_method_sd", "mean"))
)
old_pilot_target = (
    old_pilot_rep.groupby(["target", "modality"], as_index=False)
    .agg(pilot_disagreement_index=("pilot_disagreement", "median"))
)
old_budget_data = old_budget_target.merge(old_pilot_target, on=["target", "modality"])

ALPHAS = [0.1, 1.0, 10.0, 100.0]
alpha_rows = []
for alpha in ALPHAS:
    errors = []
    for held in old_budget_data["target"]:
        train = old_budget_data[old_budget_data["target"] != held]
        test = old_budget_data[old_budget_data["target"] == held]
        model = Pipeline([
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("ridge", Ridge(alpha=alpha)),
        ])
        model.fit(train[["pilot_disagreement_index"]], train["log2_minimum_budget"])
        errors.append(abs(float(model.predict(test[["pilot_disagreement_index"]])[0]) - float(test["log2_minimum_budget"].iloc[0])))
    alpha_rows.append({"alpha": alpha, "loto_mae": float(np.mean(errors))})
alpha_audit = pd.DataFrame(alpha_rows).sort_values(["loto_mae", "alpha"])
selected_alpha = float(alpha_audit.iloc[0]["alpha"])

old_model = Pipeline([
    ("impute", SimpleImputer(strategy="median")),
    ("scale", StandardScaler()),
    ("ridge", Ridge(alpha=selected_alpha)),
])
old_model.fit(old_budget_data[["pilot_disagreement_index"]], old_budget_data["log2_minimum_budget"])

old_model_record = {
    "stage": "StageT2-KR-v0.4",
    "event": "OLD_13_TARGET_EXPECTED_BUDGET_MODEL_FREEZE_BEFORE_REPAIR_EXTENSION_TRUTH",
    "feature": "median_budget8_cross_method_disagreement",
    "training_targets": sorted(old_budget_data["target"].tolist()),
    "selected_alpha": selected_alpha,
    "imputer_statistics": [float(x) for x in old_model.named_steps["impute"].statistics_],
    "scaler_mean": [float(x) for x in old_model.named_steps["scale"].mean_],
    "scaler_scale": [float(x) for x in old_model.named_steps["scale"].scale_],
    "ridge_coefficient": [float(x) for x in np.ravel(old_model.named_steps["ridge"].coef_)],
    "ridge_intercept": float(np.ravel(np.asarray(old_model.named_steps["ridge"].intercept_))[0]),
    "new_target_multibudget_truth_observed": False,
    "single_pilot_deployment_authorised": False,
    "frozen_utc": now(),
}
old_model_record["freeze_sha256"] = sha_json(old_model_record)
write_json(P5 / "StageT2-KR_Old13_Expected_Budget_Model_Freeze_v0.4.json", old_model_record)
write_csv(P5 / "StageT2-KR_Old13_Budget_Model_Alpha_Audit_v0.4.csv", alpha_audit)
write_csv(P5 / "StageT2-KR_Old13_Budget_Training_Data_v0.4.csv", old_budget_data)

print("Old 13-target expected-budget model frozen before new truth.")
print("Selected alpha:", selected_alpha)
print("Freeze SHA256:", old_model_record["freeze_sha256"])


# @title T2-KR-7. Run complete five-budget parent and RA-CB extension experiments
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

write_csv(P4 / "StageT2-KR_All_MultiBudget_Extension_Replicates_v0.4.csv", extension_results)
write_csv(P4 / "StageT2-KR_RA_CB_Selector_And_Balance_Diagnostics_v0.4.csv", extension_diagnostics)
write_csv(P4 / "StageT2-KR_Skipped_Extension_Replicates_v0.4.csv", extension_skips)

print("Extension result rows:", len(extension_results))
print("Skipped rows:", len(extension_skips))


# @title T2-KR-8. Evaluate new targets, old-model extension, expanded meta-analysis, gates and completion
# Operational budgets for AMW and RA-CB.
budget_rows = []
for method in ["amw_ddet", "ra_cb_amw_ddet"]:
    curve = (
        extension_results[extension_results["method"].eq(method)]
        .groupby(["target", "modality", "budget"], as_index=False)
        .agg(median_error=("absolute_error", "median"))
    )
    for (target, modality), frame in curve.groupby(["target", "modality"]):
        found = None
        for budget in BUDGETS:
            row = frame[frame["budget"].eq(budget)]
            if len(row) and float(row["median_error"].iloc[0]) <= 0.04:
                found = budget
                break
        operational = found if found is not None else 256
        budget_rows.append({
            "target": target, "modality": modality, "method": method,
            "minimum_budget_operational": operational,
            "log2_minimum_budget": math.log2(operational),
            "right_censored_above_128": found is None,
        })
extension_budget = pd.DataFrame(budget_rows)

# New target expected-pilot disagreement and frozen old-model prediction.
new_b8 = extension_results[extension_results["budget"].eq(8)]
new_pivot = new_b8.pivot_table(
    index=["target", "modality", "replicate", "edge_id"],
    columns="method", values="estimate_auc"
).reset_index()
new_pivot["cross_method_sd"] = new_pivot.reindex(columns=legal_methods).std(axis=1)
new_pilot_rep = (
    new_pivot.groupby(["target", "modality", "replicate"], as_index=False)
    .agg(pilot_disagreement=("cross_method_sd", "mean"))
)
new_pilot_target = (
    new_pilot_rep.groupby(["target", "modality"], as_index=False)
    .agg(
        pilot_disagreement_index=("pilot_disagreement", "median"),
        pilot_disagreement_iqr=("pilot_disagreement", lambda x: float(np.quantile(x, .75) - np.quantile(x, .25))),
    )
)
amw_budget = extension_budget[extension_budget["method"].eq("amw_ddet")].copy()
new_meta = amw_budget.merge(new_pilot_target, on=["target", "modality"])
new_meta["old13_prediction_log2_budget"] = old_model.predict(
    new_meta[["pilot_disagreement_index"]]
)
new_meta["old13_absolute_log2_error"] = (
    new_meta["old13_prediction_log2_budget"] - new_meta["log2_minimum_budget"]
).abs()
new_meta["old13_baseline_log2_budget"] = float(old_budget_data["log2_minimum_budget"].median())
new_meta["old13_baseline_absolute_error"] = (
    new_meta["old13_baseline_log2_budget"] - new_meta["log2_minimum_budget"]
).abs()

# Expanded leave-one-target-out result, transparently development-only.
expanded_data = pd.concat([
    old_budget_data[[
        "target", "modality", "minimum_budget_operational",
        "log2_minimum_budget", "pilot_disagreement_index"
    ]].assign(cohort="original13"),
    new_meta[[
        "target", "modality", "minimum_budget_operational",
        "log2_minimum_budget", "pilot_disagreement_index"
    ]].assign(cohort="expansion"),
], ignore_index=True)

expanded_pred_rows = []
for held in expanded_data["target"]:
    train = expanded_data[expanded_data["target"] != held]
    test = expanded_data[expanded_data["target"] == held]
    alpha_scores = []
    for alpha in ALPHAS:
        fold_errors = []
        for inner_held in train["target"]:
            inner_train = train[train["target"] != inner_held]
            inner_test = train[train["target"] == inner_held]
            model = Pipeline([
                ("impute", SimpleImputer(strategy="median")),
                ("scale", StandardScaler()),
                ("ridge", Ridge(alpha=alpha)),
            ])
            model.fit(inner_train[["pilot_disagreement_index"]], inner_train["log2_minimum_budget"])
            prediction = float(model.predict(inner_test[["pilot_disagreement_index"]])[0])
            fold_errors.append(abs(prediction - float(inner_test["log2_minimum_budget"].iloc[0])))
        alpha_scores.append((float(np.mean(fold_errors)), alpha))
    selected = min(alpha_scores)[1]
    model = Pipeline([
        ("impute", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("ridge", Ridge(alpha=selected)),
    ])
    model.fit(train[["pilot_disagreement_index"]], train["log2_minimum_budget"])
    prediction = float(model.predict(test[["pilot_disagreement_index"]])[0])
    expanded_pred_rows.append({
        "target": held,
        "cohort": test["cohort"].iloc[0],
        "actual": float(test["log2_minimum_budget"].iloc[0]),
        "prediction": prediction,
        "baseline": float(train["log2_minimum_budget"].median()),
        "selected_alpha": selected,
    })
expanded_predictions = pd.DataFrame(expanded_pred_rows)
expanded_rho = float(spearmanr(expanded_predictions["actual"], expanded_predictions["prediction"]).statistic)
expanded_mae = float(mean_absolute_error(expanded_predictions["actual"], expanded_predictions["prediction"]))
expanded_baseline_mae = float(mean_absolute_error(expanded_predictions["actual"], expanded_predictions["baseline"]))
expanded_gain = 1 - expanded_mae / expanded_baseline_mae if expanded_baseline_mae > 0 else np.nan

# RA-CB performance summary on expansion targets.
ra_summary = (
    extension_results[extension_results["method"].eq("ra_cb_amw_ddet")]
    .groupby(["target", "modality", "source", "edge_id"], as_index=False)
    .agg(
        true_auc=("true_auc", "first"),
        predicted_auc_b32=("estimate_auc", lambda x: float(np.median(x))),
        median_absolute_error=("absolute_error", "median"),
    )
)
# Correctly isolate budget 32 for the predicted value.
ra32 = (
    extension_results[
        extension_results["method"].eq("ra_cb_amw_ddet") &
        extension_results["budget"].eq(32)
    ]
    .groupby(["target", "modality", "source", "edge_id"], as_index=False)
    .agg(
        true_auc=("true_auc", "first"),
        predicted_auc_b32=("estimate_auc", "median"),
        median_absolute_error_b32=("absolute_error", "median"),
    )
)
extension_target_mae = (
    ra32.groupby(["target", "modality"], as_index=False)
    .agg(target_median_mae_b32=("median_absolute_error_b32", "median"))
)

write_csv(P5 / "StageT2-KR_Expansion_Operational_Budgets_v0.4.csv", extension_budget)
write_csv(P5 / "StageT2-KR_New_Target_Old13_Budget_Model_Evaluation_v0.4.csv", new_meta)
write_csv(P5 / "StageT2-KR_Expanded_Target_Budget_Meta_Data_v0.4.csv", expanded_data)
write_csv(P5 / "StageT2-KR_Expanded_LOTO_Budget_Predictions_v0.4.csv", expanded_predictions)
write_csv(P5 / "StageT2-KR_RA_CB_Expansion_Edge_Summary_v0.4.csv", ra32)
write_csv(P5 / "StageT2-KR_RA_CB_Expansion_Target_Summary_v0.4.csv", extension_target_mae)

old_extension_improvement = float(
    1 - new_meta["old13_absolute_log2_error"].mean() /
    new_meta["old13_baseline_absolute_error"].mean()
) if new_meta["old13_baseline_absolute_error"].mean() > 0 else np.nan

gates = pd.DataFrame([
    {"gate": "G1_parent_and_document_integrity", "passed": True, "observed": "all frozen hashes exact"},
    {"gate": "G2_hisbreast_official_archive", "passed": HIS_ARCHIVE.stat().st_size >= 900 * 1024**2, "observed": HIS_ARCHIVE.stat().st_size},
    {"gate": "G3_hisbreast_structure", "passed": len(image_paths) >= 900 and len(diagnosis_paths) >= 900 and len(json_paths) >= 1, "observed": f"images={len(image_paths)}; diagnosis={len(diagnosis_paths)}; containers={len(json_paths)}; expanded={len(json_frame)}"},
    {"gate": "G4_hisbreast_explicit_patient_grouping", "passed": bool(PATIENT_FIELD is not None and patient_coverage >= 0.80), "observed": f"field={PATIENT_FIELD}; coverage={patient_coverage:.3f}"},
    {"gate": "G5_hisbreast_conservative_endpoint", "passed": bool(mapped_binary_rate >= 0.50 and class_groups.get(0.0, 0) >= 30 and class_groups.get(1.0, 0) >= 30), "observed": f"mapped={mapped_binary_rate:.3f}; groups={class_groups}"},
    {"gate": "G6_hisbreast_adapter", "passed": HIS_ADAPTER_PASS, "observed": his_summary.to_dict("records")},
    {"gate": "G7_minimum_two_expansion_targets_scored", "passed": source_scores["target"].nunique() >= 2, "observed": sorted(source_scores["target"].unique())},
    {"gate": "G8_frozen_source_axes_exact", "passed": True, "observed": sorted(AXIS_PATHS)},
    {"gate": "G9_multibudget_completeness", "passed": set(BUDGETS).issubset(set(extension_results["budget"].unique())) and extension_results["target"].nunique() >= 2, "observed": f"rows={len(extension_results)}"},
    {"gate": "G10_old_model_frozen_before_new_truth", "passed": old_model_record["new_target_multibudget_truth_observed"] is False, "observed": old_model_record["freeze_sha256"]},
    {"gate": "G11_single_pilot_failure_preserved", "passed": t2h["single_pilot_deployment_authorised"] is False, "observed": False},
    {"gate": "G12_locked_blind_firewall", "passed": True, "observed": "no locked-blind path or outcome accessed"},
    {"gate": "G13_stage12_false", "passed": t3pf["stage12_authorised"] is False, "observed": False},
])

core_integrity = bool(gates.loc[gates["gate"].isin([
    "G1_parent_and_document_integrity", "G2_hisbreast_official_archive",
    "G3_hisbreast_structure", "G7_minimum_two_expansion_targets_scored",
    "G8_frozen_source_axes_exact", "G9_multibudget_completeness",
    "G10_old_model_frozen_before_new_truth", "G11_single_pilot_failure_preserved",
    "G12_locked_blind_firewall", "G13_stage12_false",
]), "passed"].all())

if not core_integrity:
    decision = "TERMINATE_T2K_CORE_INTEGRITY_SCORING_OR_FIREWALL_FAILURE"
elif HIS_ADAPTER_PASS:
    decision = "SEAL_THREE_EXPANSION_TARGETS_AND_MULTIBUDGET_EXTENSION_AUTHORISE_EXPANDED_META_ANALYSIS_ONLY"
else:
    decision = "SEAL_TWO_EXPANSION_TARGETS_AND_MULTIBUDGET_EXTENSION_RETAIN_HISBREAST_ADAPTER_HOLD"

write_csv(P5 / "StageT2-KR_Frozen_Gates_v0.4.csv", gates)

# Figures.
plt.figure(figsize=(8, 6))
for cohort, frame in expanded_predictions.groupby("cohort"):
    plt.scatter(frame["actual"], frame["prediction"], label=cohort)
lo = min(expanded_predictions["actual"].min(), expanded_predictions["prediction"].min())
hi = max(expanded_predictions["actual"].max(), expanded_predictions["prediction"].max())
plt.plot([lo, hi], [lo, hi], linestyle="--")
plt.xlabel("Actual log2 operational budget")
plt.ylabel("LOTO predicted log2 budget")
plt.title(f"Expanded target-expected budget relation: rho={expanded_rho:.3f}")
plt.legend()
plt.tight_layout()
plt.savefig(P6 / "StageT2-KR_Expanded_Budget_Meta_Analysis_v0.4.png", dpi=220)
plt.show()

plt.figure(figsize=(9, 5))
plot_frame = (
    extension_results[extension_results["method"].isin(["amw_ddet", "ra_cb_amw_ddet"])]
    .groupby(["target", "budget", "method"], as_index=False)
    .agg(median_error=("absolute_error", "median"))
)
for (target, method), frame in plot_frame.groupby(["target", "method"]):
    plt.plot(frame["budget"], frame["median_error"], marker="o", label=f"{target}:{method}")
plt.axhline(0.04, linestyle="--")
plt.xscale("log", base=2)
plt.xlabel("Witness-group budget")
plt.ylabel("Median absolute AUC error")
plt.title("Expansion target evidence curves")
plt.legend(fontsize=7)
plt.tight_layout()
plt.savefig(P6 / "StageT2-KR_Expansion_Evidence_Curves_v0.4.png", dpi=220)
plt.show()

completion = {
    "stage": "StageT2-KR-v0.4",
    "decision": decision,
    "parent_t2j_final_record_sha256": EXPECTED["t2j_record_sha256"],
    "parent_t2h_final_record_sha256": EXPECTED["t2h_record_sha256"],
    "parent_t3pf_activation_record_sha256": EXPECTED["t3pf_record_sha256"],
    "protocol_seal_sha256": protocol["protocol_seal_sha256"],
    "hisbreast_adapter_pass": bool(HIS_ADAPTER_PASS),
    "hisbreast_selected_patient_field": PATIENT_FIELD or "",
    "hisbreast_retained_images": int(len(retained)),
    "hisbreast_retained_groups": int(retained["group_id"].nunique()),
    "scored_expansion_targets": sorted(source_scores["target"].unique().tolist()),
    "scored_expansion_target_count": int(source_scores["target"].nunique()),
    "expansion_edges": int(truth_table["edge_id"].nunique()),
    "multibudget_result_rows": int(len(extension_results)),
    "old13_extension_relative_mae_improvement": old_extension_improvement,
    "expanded_loto_spearman": expanded_rho,
    "expanded_loto_relative_mae_improvement": expanded_gain,
    "single_pilot_deployment_authorised": False,
    "locked_blind_assets_touched": False,
    "locked_blind_outcomes_accessed": False,
    "stage12_authorised": False,
    "gates_passed": int(gates["passed"].sum()),
    "gates_total": int(len(gates)),
    "completed_utc": now(),
}
completion["final_record_sha256"] = sha_json(completion)
write_json(P6 / "StageT2-KR_Complete_v0.4.json", completion)

summary = f"""# Stage T2-KR result summary v0.1

- Decision: `{decision}`
- HiSBreast adapter pass: `{HIS_ADAPTER_PASS}`
- HiSBreast patient field: `{PATIENT_FIELD}`
- Scored expansion targets: `{completion['scored_expansion_targets']}`
- Expansion edges: `{completion['expansion_edges']}`
- Multi-budget result rows: `{completion['multibudget_result_rows']}`
- Old-13 model extension relative MAE improvement: `{old_extension_improvement:.2%}`
- Expanded LOTO Spearman: `{expanded_rho:.6f}`
- Expanded LOTO relative MAE improvement: `{expanded_gain:.2%}`
- Gates: `{int(gates['passed'].sum())}/{len(gates)}`
- Single-pilot deployment authorised: `False`
- Locked blind assets touched: `False`
- Stage 12 authorised: `False`
- Final record SHA256: `{completion['final_record_sha256']}`
"""
write_text(P6 / "StageT2-KR_Result_Summary_v0.4.md", summary)

display(new_meta)
display(extension_target_mae)
display(gates)
print("\n========== STAGE T2-K COMPLETE ==========")
print("Decision:", decision)
print("HiSBreast adapter pass:", HIS_ADAPTER_PASS)
print("Scored expansion targets:", completion["scored_expansion_targets"])
print("Expansion edges:", completion["expansion_edges"])
print("Expanded LOTO Spearman:", expanded_rho)
print("Single-pilot deployment authorised:", False)
print("Locked blind assets touched:", False)
print("Stage 12 authorised:", False)
print("Final record SHA256:", completion["final_record_sha256"])
