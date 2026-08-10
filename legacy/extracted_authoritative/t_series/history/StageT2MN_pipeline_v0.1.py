
# Stage T2-MN: merged interval-censored development freeze and provider prospective extension
import base64, gc, hashlib, io, itertools, json, math, os, random, re, shutil, subprocess, sys, time, unicodedata, warnings, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
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
from scipy.special import log_ndtr, logsumexp
from scipy.stats import norm, spearmanr
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold, train_test_split
from sklearn.preprocessing import RobustScaler, StandardScaler
from tqdm.auto import tqdm

warnings.filterwarnings("ignore")
try:
    from IPython.display import display
except Exception:
    display = print

IN_COLAB = False
try:
    from google.colab import drive
    drive.mount("/content/drive", force_remount=True)
    IN_COLAB = True
except Exception:
    pass

DEFAULT_ROOT = Path("/content/drive/MyDrive/Cross-Modal_Diagnostic_Observability") if IN_COLAB else Path.cwd()
PROJECT_ROOT = Path(os.environ.get("CDO_PROJECT_ROOT", str(DEFAULT_ROOT)))
CODE_ROOT = PROJECT_ROOT / "05_Code" / "Cross_Modal"
THEORY_ROOT = PROJECT_ROOT / "03_Theory" / "Directed_Diagnostic_Evidence_Transport_v1.1"
M_STUDY_ROOT = PROJECT_ROOT / "04_Study_Design" / "StageT2-M_Censored_Evidence_Demand_And_Support_Abstention_v0.1"
MN_STUDY_ROOT = PROJECT_ROOT / "04_Study_Design" / "StageT2-MN_Merged_Censored_Model_And_Provider_Extension_v0.1"
MN_MAP_ROOT = PROJECT_ROOT / "02_Dataset_Map" / "StageT2-MN_Provider_Target_Registry_v0.1"
CM_ROOT = PROJECT_ROOT / "06_Data_Records" / "Cross_Modal"
DRIVE_RESULT_ROOT = CM_ROOT / "StageT2-MN_v0.1"
RUNTIME_ROOT = Path("/content/cmdo_runtime/StageT2-MN") if IN_COLAB else Path("/tmp/cmdo_runtime/StageT2-MN")
if RUNTIME_ROOT.exists():
    shutil.rmtree(RUNTIME_ROOT)
RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
LOCAL_RECORD_ROOT = RUNTIME_ROOT / "governed_records"
LOCAL_M_ROOT = LOCAL_RECORD_ROOT / "StageT2-M"
LOCAL_N_ROOT = LOCAL_RECORD_ROOT / "StageT2-N"
LOCAL_ACQ_ROOT = RUNTIME_ROOT / "provider_acquisition_work"
for path in [LOCAL_RECORD_ROOT, LOCAL_M_ROOT, LOCAL_N_ROOT, LOCAL_ACQ_ROOT]:
    path.mkdir(parents=True, exist_ok=True)

NOTEBOOK_NAME = "CrossModal_StageT2-MN_Censored_Model_Freeze_And_Provider_Prospective_Extension_v0.1.ipynb"
NOTEBOOK_PATH = CODE_ROOT / NOTEBOOK_NAME
MERGED_PREREG_PATH = MN_STUDY_ROOT / "StageT2-MN_Merged_Censored_Model_And_Provider_Prospective_Extension_Preregistration_v1.0.md"
MERGED_METHOD_PATH = MN_STUDY_ROOT / "StageT2-MN_Local_First_Durable_Commit_And_Prospective_Extension_Method_v0.1.md"
PERSISTENCE_REVIEW_PATH = MN_STUDY_ROOT / "StageT2-M_Durable_Persistence_Failure_Review_And_Remediation_v0.1.md"
REGISTRY_PATH = MN_MAP_ROOT / "StageT2-MN_Provider_Separated_Target_Registry_v0.1.csv"
README_PATH = CODE_ROOT / "README_Cross_Modal_Notebook_Index_v2.2.md"

THEORY_PATH = THEORY_ROOT / "Directed_Diagnostic_Evidence_Transport_Interval_Censored_Evidence_Demand_And_Support_Conditioned_Observability_Theory_v1.1.md"
M_METHOD_PATH = THEORY_ROOT / "Interval_Censored_Evidence_Demand_And_Support_Abstention_Method_v0.1.md"
M_PREREG_PATH = M_STUDY_ROOT / "StageT2-M_Development_Only_Interval_Censored_Evidence_Demand_And_Support_Abstention_Preregistration_v1.0.md"
M_ADDENDUM_PATH = M_STUDY_ROOT / "StageT2-N_Provider_Separated_Prospective_Evidence_Demand_Extension_Addendum_v0.1.md"
FAMILY_PATH = M_STUDY_ROOT / "StageT2-M_Frozen_Evidence_Family_Map_v0.1.csv"

T2D_REPS = CM_ROOT / "StageT2-D_Development_Only_AMW-DDET_Active_Minimal_Witness_Certificate_v0.1" / "01_Replicate_Results" / "StageT2-D_All_Acquisition_Replicates_v0.1.csv"
T2KR_REPS = CM_ROOT / "StageT2-KR_Frozen_Axis_Schema_Adapter_And_CPU_Continuation_v0.4" / "04_MultiBudget_Extension" / "StageT2-KR_All_MultiBudget_Extension_Replicates_v0.4.csv"
T2L_REPS = CM_ROOT / "StageT2-L_Independent_Target_Regime_Expansion_v0.1" / "05_MultiBudget_Extension" / "StageT2-L_All_MultiBudget_Extension_Replicates_v0.1.csv"
T2L_META = CM_ROOT / "StageT2-L_Independent_Target_Regime_Expansion_v0.1" / "06_Meta_Regime_Analysis" / "StageT2-L_Expanded_Target_Budget_Meta_Data_v0.1.csv"
T2L_FINAL = CM_ROOT / "StageT2-L_Independent_Target_Regime_Expansion_v0.1" / "07_Results" / "StageT2-L_Complete_v0.1.json"
T2H_FINAL = CM_ROOT / "StageT2-H_Development_Only_Single_Pilot_Deployability_And_Sequential_Forecast_Freeze_v0.1" / "04_Results" / "StageT2-H_Complete_v0.1.json"
T3PF_FINAL = CM_ROOT / "StageT3-PF_Outcome-Free_Preregistration_And_Asset_Preflight_v1.0" / "04_Results" / "StageT3-PF_Activation_Record_v1.0.json"

STAGE8_ROOT = CM_ROOT / "Stage8_CrossModality_EdgeLibrary_Expansion_v0.1"
MANIFEST_ROOT = STAGE8_ROOT / "01_Acquisition_Manifests"
HAM_MANIFEST = MANIFEST_ROOT / "HAM10000_Harmonised_Acquisition_Manifest_v0.1.csv"
MSK_MANIFEST = MANIFEST_ROOT / "ISIC_MSK1_Harmonised_Acquisition_Manifest_v0.1.csv"
UDA_MANIFEST = MANIFEST_ROOT / "ISIC_UDA1_Harmonised_Acquisition_Manifest_v0.1.csv"
DERM_AXIS_ROOT = STAGE8_ROOT / "03_Frozen_Source_Axes"
DERM_SUMMARY = DERM_AXIS_ROOT / "Stage8_Source_Recoverability_Summary_v0.1.csv"
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
T2J_ROOT = CM_ROOT / "StageT2-J_Expansion_Harmonisation_Dedup_And_Public_Route_Repair_v0.1"
MILK_MANIFEST = T2J_ROOT / "02_Harmonised_Manifests" / "StageT2-J_MILK10K_Harmonised_Exact_Manifest_v0.1.csv"
REFERENCE_CACHE = T2J_ROOT / "03_Fingerprints_And_Dedup" / "StageT2-J_Existing_Dermoscopy_Reference_Fingerprints_v0.1.csv"
T2L_MANIFEST = CM_ROOT / "StageT2-L_Independent_Target_Regime_Expansion_v0.1" / "03_Fingerprints_And_Dedup" / "StageT2-L_Selected_Image_Download_And_Dedup_Manifest_v0.1.csv"

EXPECTED = {
    "t2d_reps": "c6f740510c520167c2ecfbfc48fc2db88428e17ce1b96e6ad5826e507929aedb",
    "t2kr_reps": "ee54139c494e6cad6c0781ba2da8a73e31ad94f7ce8cedfbaac90fe7cb0dded1",
    "t2l_reps": "a5449f57d10eeafffb3d9f89a18b9d0f0099a44991d315b030c45048702e0096",
    "t2l_meta": "ab3b0fb583b6edeb63af596b371d34a16f2b8a00db75f1835e5816d4d3e6bb67",
    "t2l_file": "7bce95d2fa7220cdaca81d367d690f7fcb9081bfa34accc16c12bf65f89976ae",
    "t2l_record": "6383464d23e27c7ac9226b696a639894555df294d8d22b5906a55f68620abb96",
    "t2h_file": "4dc14383a299a97a3937a4fe2a38919952b6c931c5ee14308220141442504da4",
    "t2h_record": "27d4c7afe711ba66ea44d11f3ef173820e11ef1eba7a44530446a3e5444aa99f",
    "t3pf_file": "10646d771a3cd9e86c8c96eb4a134d4878c7542bb4b0b07ab9e01fa8b0c09c25",
    "t3pf_record": "4397cee7798f684159ed77aa5e1edd7b7ae0a24378047d6c89b37ef9ef738a52",
    "theory": "ef8b0c777a9353058b8c2399996c7b85523e786f8c0a61cb05be15ee53531db8",
    "m_method": "395c923f8c640cb3cc9759d52e97de6d712195f6416bbce2adf8f49098644ed1",
    "m_prereg": "ea84797702a5613abbe3c669510fbc17918892386be1aa8923de05c52c254806",
    "m_addendum": "5cc37194774c482dcc3392bd12e12c55aad4cde7c6d93496db883d3a426df4e1",
    "family": "fed4400bdfa7447052a69274f2ea00bba23475a729ecce131e7699ca18275d2d",
    "merged_prereg": "abf0af09b32a54d787c6e064bc59eb74fb7aa1d46e7531af4557b24dca6ed026",
    "merged_method": "3d7def5ea7f664a887d98691bd9a5f93ef54775276ed9fc60b56b7ffd886f614",
    "persistence_review": "1f65e1dccafdc6f7b972e006cfc23575e9e8978afb1df6b9a6ec95b5811d2f33",
    "registry": "9b34769d0f217a78215bea2bf06368f65cc3a67366ee715a3ec372949ad7bf1b",
    "readme": "19cb3a3aca316e4096c9ff1dd50fcd5cd38a95a9cdc8956acd9c7d449635d4a5",
}

SEED = 20260723
THRESHOLD = 0.04
BOOTSTRAPS = 1000
LEGAL_METHODS = ["random_direct", "random_logistic_plugin", "random_joint_gmm", "active_direct", "amw_ddet"]
FEATURE_SETS = {
    "CORE": ["pilot_disagreement_index"],
    "PILOT": ["pilot_disagreement_index", "pilot_disagreement_iqr", "pilot_amw_logit_gap"],
    "COMPACT": ["pilot_disagreement_index", "pilot_disagreement_iqr", "source_auc_mean", "source_auc_sd", "log2_groups"],
}
PENALTIES = [0.1, 1.0, 10.0, 100.0]
SUPPORT_FEATURES = ["pilot_disagreement_index", "log2_groups"]

COLLECTIONS = [
    {"dataset": "HIBA_ISIC_176", "collection_id": 176, "provider": "Hospital Italiano de Buenos Aires", "role": "PRIMARY_PROVIDER_TARGET", "group_priority": ["patient_id", "lesion_id"], "priority": 1},
    {"dataset": "SYDNEY_ACQUIRED_215", "collection_id": 215, "provider": "Sydney Melanoma Diagnostic Center at Royal Prince Alfred Hospital", "role": "PRIMARY_PROVIDER_TARGET", "group_priority": ["patient_id", "lesion_id"], "priority": 2},
    {"dataset": "BCN20000_ISIC_249", "collection_id": 249, "provider": "Hospital Clínic de Barcelona", "role": "PRIMARY_PROVIDER_LESION_TARGET", "group_priority": ["lesion_id"], "priority": 3},
    {"dataset": "MELSELF_ISIC_485", "collection_id": 485, "provider": "MEL-SELF provider network", "role": "CONDITIONAL_PROVIDER_NETWORK_TARGET", "group_priority": ["patient_id", "lesion_id"], "priority": 4},
]
LOCKED_BLIND = {"BUSI_CAIRO_2019", "OASBUD_2017", "DERM7PT_2019"}
BUDGETS = [8, 16, 32, 64, 128]
N_REPLICATES = 100
MAX_POSITIVE = 150
MAX_NEGATIVE = 450
MIN_TOTAL_GROUPS = 128
MIN_POSITIVE_GROUPS = 20
MIN_NEGATIVE_GROUPS = 60
PHASH_MAX_DISTANCE = 4
RIDGE_C = 3.0
BALANCE_RIDGE = 0.1
WEIGHT_CLIP = (0.1, 10.0)
MIN_BALANCE_ESS = 8.0

SESSION = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=16, pool_maxsize=16, max_retries=1)
SESSION.mount("https://", adapter)
SESSION.headers.update({"User-Agent": "CMDO-StageT2-MN/0.1 governed academic acquisition"})
HTTP_TIMEOUT = (20, 180)
OFFLINE_TEST = os.environ.get("CMDO_OFFLINE_TEST", "0") == "1"

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

def sha_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()

def _atomic_local_bytes(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    with path.open("rb") as handle:
        os.fsync(handle.fileno())
    return path

def write_csv(path, frame):
    data = frame.fillna("").to_csv(index=False, lineterminator="\n", float_format="%.12g").encode("utf-8")
    _atomic_local_bytes(path, data)

def write_json(path, value):
    _atomic_local_bytes(path, (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))

def write_text(path, value):
    _atomic_local_bytes(path, str(value).encode("utf-8"))

def verify_self(path, field, expected=None):
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    claim = value[field]
    core = dict(value)
    core.pop(field)
    assert sha_json(core) == claim, f"Self-hash mismatch: {path}"
    if expected is not None:
        assert claim == expected, f"Unexpected record hash: {path}"
    return value

def notebook_source_sha(path):
    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    cells = []
    for cell in value.get("cells", []):
        if cell.get("cell_type") not in {"code", "markdown"}:
            continue
        source = cell.get("source", [])
        source = "".join(source) if isinstance(source, list) else str(source)
        cells.append({"cell_type": cell["cell_type"], "source": source.replace("\r\n", "\n")})
    return sha_json(cells)

required = [
    NOTEBOOK_PATH, MERGED_PREREG_PATH, MERGED_METHOD_PATH, PERSISTENCE_REVIEW_PATH, REGISTRY_PATH, README_PATH,
    THEORY_PATH, M_METHOD_PATH, M_PREREG_PATH, M_ADDENDUM_PATH, FAMILY_PATH,
    T2D_REPS, T2KR_REPS, T2L_REPS, T2L_META, T2L_FINAL, T2H_FINAL, T3PF_FINAL,
    HAM_MANIFEST, MSK_MANIFEST, UDA_MANIFEST, MILK_MANIFEST, REFERENCE_CACHE,
    T2L_MANIFEST, DERM_SUMMARY, *AXIS_PATHS.values(),
]
missing = [str(path) for path in required if not Path(path).is_file()]
assert not missing, "Missing required immutable or merged files:\n" + "\n".join(missing)

for role, path in {
    "t2d_reps": T2D_REPS, "t2kr_reps": T2KR_REPS, "t2l_reps": T2L_REPS,
    "t2l_meta": T2L_META, "t2l_file": T2L_FINAL, "t2h_file": T2H_FINAL,
    "t3pf_file": T3PF_FINAL, "theory": THEORY_PATH, "m_method": M_METHOD_PATH,
    "m_prereg": M_PREREG_PATH, "m_addendum": M_ADDENDUM_PATH, "family": FAMILY_PATH,
    "merged_prereg": MERGED_PREREG_PATH, "merged_method": MERGED_METHOD_PATH,
    "persistence_review": PERSISTENCE_REVIEW_PATH, "registry": REGISTRY_PATH, "readme": README_PATH,
}.items():
    observed = sha_file(path)
    assert observed == EXPECTED[role], f"Hash mismatch {role}: {observed}"

t2l_final = verify_self(T2L_FINAL, "final_record_sha256", EXPECTED["t2l_record"])
t2h_final = verify_self(T2H_FINAL, "final_record_sha256", EXPECTED["t2h_record"])
t3pf_final = verify_self(T3PF_FINAL, "activation_record_sha256", EXPECTED["t3pf_record"])
assert t2h_final["single_pilot_deployment_authorised"] is False
assert t3pf_final["blind_assets_acquired"] is False
assert t3pf_final["blind_outcomes_accessed"] is False
assert t3pf_final["stage12_authorised"] is False
for source, path in AXIS_PATHS.items():
    assert sha_file(path) == AXIS_SHA[source]

M_P0, M_P1, M_P2, M_P3, M_P4, M_P5 = [LOCAL_M_ROOT / name for name in [
    "00_Protocol", "01_Target_Features_And_Interval_Truth",
    "02_Censored_Model_Selection", "03_LOTO_Family_Holdout_And_Support",
    "04_Regime_Consolidation", "05_Results"
]]
for path in [M_P0, M_P1, M_P2, M_P3, M_P4, M_P5]:
    path.mkdir(parents=True, exist_ok=True)
P0, P1, P2, P3, P4, P5 = M_P0, M_P1, M_P2, M_P3, M_P4, M_P5

entry_payload = {
    "stage": "StageT2-MN",
    "event": "MERGED_STAGE_ENTRY_SEAL_BEFORE_DEVELOPMENT_RECOMPUTATION_AND_PROVIDER_ACCESS",
    "parent_t2l_record": EXPECTED["t2l_record"],
    "parent_t2h_record": EXPECTED["t2h_record"],
    "parent_t3pf_record": EXPECTED["t3pf_record"],
    "merged_preregistration_sha256": EXPECTED["merged_prereg"],
    "merged_method_sha256": EXPECTED["merged_method"],
    "persistence_review_sha256": EXPECTED["persistence_review"],
    "provider_registry_sha256": EXPECTED["registry"],
    "notebook_source_sha256": notebook_source_sha(NOTEBOOK_PATH),
    "provider_metadata_or_outcomes_loaded": False,
    "single_pilot_deployment_authorised": False,
    "locked_blind_assets_touched": False,
    "locked_blind_outcomes_accessed": False,
    "stage12_authorised": False,
    "sealed_utc": now(),
}
entry_payload["entry_seal_sha256"] = sha_json(entry_payload)
write_json(M_P0 / "StageT2-MN_Entry_Seal_v0.1.json", entry_payload)

protocol = {
    "stage": "StageT2-M",
    "purpose": "development_only_interval_censored_evidence_demand_and_support_abstention_freeze_within_merged_stage",
    "parent_t2l_record": EXPECTED["t2l_record"],
    "parent_t2h_record": EXPECTED["t2h_record"],
    "parent_t3pf_record": EXPECTED["t3pf_record"],
    "theory_sha256": EXPECTED["theory"],
    "method_sha256": EXPECTED["m_method"],
    "preregistration_sha256": EXPECTED["m_prereg"],
    "conditional_addendum_sha256": EXPECTED["m_addendum"],
    "family_map_sha256": EXPECTED["family"],
    "merged_entry_seal_sha256": entry_payload["entry_seal_sha256"],
    "new_target_outcomes_loaded": False,
    "single_pilot_deployment_authorised": False,
    "locked_blind_assets_touched": False,
    "locked_blind_outcomes_accessed": False,
    "stage12_authorised": False,
    "sealed_utc": now(),
}
protocol["protocol_seal_sha256"] = sha_json(protocol)
write_json(M_P0 / "StageT2-M_Protocol_Seal_Within_T2-MN_v0.1.json", protocol)

print("Stage T2-MN entry seal:", entry_payload["entry_seal_sha256"])
print("Stage T2-M local-first recomputation begins.")
print("Provider metadata or outcomes loaded:", False)


# @title T2-M-1. Reconstruct the 18-target feature table and interval-censored truth
t2d = pd.read_csv(T2D_REPS)
t2kr = pd.read_csv(T2KR_REPS)
t2l = pd.read_csv(T2L_REPS)
parent_meta = pd.read_csv(T2L_META)
family_map = pd.read_csv(FAMILY_PATH)

replicates = pd.concat([t2d, t2kr, t2l], ignore_index=True, sort=False)
assert replicates["target"].nunique() == 18
assert set(LEGAL_METHODS).issubset(set(replicates["method"].unique()))

b8 = replicates[replicates["budget"].eq(8)].copy()
pivot = b8.pivot_table(
    index=["target", "modality", "replicate", "edge_id"],
    columns="method", values="estimate_auc"
).reset_index()
for method in LEGAL_METHODS:
    if method not in pivot.columns:
        pivot[method] = np.nan

pivot["cross_method_sd"] = pivot[LEGAL_METHODS].std(axis=1)
pivot["amw_logit_gap"] = (pivot["amw_ddet"] - pivot["random_logistic_plugin"]).abs()

replicate_features = (
    pivot.groupby(["target", "modality", "replicate"], as_index=False)
    .agg(
        disagreement=("cross_method_sd", "mean"),
        amw_logit_gap=("amw_logit_gap", "mean"),
    )
)
target_features = (
    replicate_features.groupby(["target", "modality"], as_index=False)
    .agg(
        pilot_disagreement_index=("disagreement", "median"),
        pilot_disagreement_iqr=("disagreement", lambda x: float(np.quantile(x, .75) - np.quantile(x, .25))),
        pilot_amw_logit_gap=("amw_logit_gap", "median"),
    )
)
static_features = (
    b8.groupby(["target", "modality"], as_index=False)
    .agg(
        independent_groups=("independent_groups", "first"),
        source_auc_mean=("source_validation_auc", "mean"),
        source_auc_sd=("source_validation_auc", "std"),
        edge_count=("edge_id", "nunique"),
    )
)
static_features["source_auc_sd"] = static_features["source_auc_sd"].fillna(0.0)

features = target_features.merge(static_features, on=["target", "modality"], validate="one_to_one")
features["log2_groups"] = np.log2(features["independent_groups"].astype(float))
features = features.merge(family_map, on="target", validate="one_to_one")
assert len(features) == 18
assert features["evidence_family"].notna().all()

parent_check = parent_meta[["target", "pilot_disagreement_index"]].merge(
    features[["target", "pilot_disagreement_index"]],
    on="target", suffixes=("_parent", "_reconstructed"), validate="one_to_one"
)
parent_check["absolute_difference"] = (
    parent_check["pilot_disagreement_index_parent"]
    - parent_check["pilot_disagreement_index_reconstructed"]
).abs()
assert parent_check["absolute_difference"].max() < 1e-9

curve = (
    replicates[replicates["method"].eq("amw_ddet")]
    .groupby(["target", "modality", "budget"], as_index=False)
    .agg(median_error=("absolute_error", "median"))
)

truth_rows = []
for (target, modality), frame in curve.groupby(["target", "modality"]):
    frame = frame.sort_values("budget")
    budgets = frame["budget"].to_numpy(int)
    errors = frame["median_error"].to_numpy(float)
    passing = np.flatnonzero(errors <= THRESHOLD)
    if len(passing):
        index = int(passing[0])
        upper = float(np.log2(budgets[index]))
        lower = -np.inf if index == 0 else float(np.log2(budgets[index - 1]))
        status = "LEFT_CENSORED" if index == 0 else "INTERVAL_CENSORED"
        operational_budget = int(budgets[index])
    else:
        lower = float(np.log2(budgets[-1]))
        upper = np.inf
        status = "RIGHT_CENSORED"
        operational_budget = 256
    truth_rows.append({
        "target": target,
        "modality": modality,
        "lower_log2_budget": lower,
        "upper_log2_budget": upper,
        "censoring_status": status,
        "operational_budget_administrative": operational_budget,
        "maximum_tested_budget": int(budgets[-1]),
        "tested_budget_count": int(len(budgets)),
    })

interval_truth = pd.DataFrame(truth_rows)
features = features.merge(interval_truth, on=["target", "modality"], validate="one_to_one")
features = features.rename(columns={
    "lower_log2_budget": "lower",
    "upper_log2_budget": "upper",
    "censoring_status": "status",
})

parent_budget = parent_meta[["target", "minimum_budget_operational"]]
budget_check = parent_budget.merge(
    features[["target", "operational_budget_administrative"]],
    on="target", validate="one_to_one"
)
assert (
    budget_check["minimum_budget_operational"].astype(int)
    == budget_check["operational_budget_administrative"].astype(int)
).all()

family_counts = features["evidence_family"].value_counts()
features["family_total_weight"] = features["evidence_family"].map(lambda value: 1.0 / family_counts[value])
features["family_total_weight"] /= features["family_total_weight"].mean()

write_csv(P1 / "StageT2-M_Target_Feature_And_Interval_Truth_Table_v0.1.csv", features)
write_csv(P1 / "StageT2-M_Parent_Feature_Reconstruction_Check_v0.1.csv", parent_check)
write_csv(P1 / "StageT2-M_Operational_Budget_Reconstruction_Check_v0.1.csv", budget_check)
write_csv(P1 / "StageT2-M_AMW_DDET_Raw_Budget_Curves_v0.1.csv", curve)

display(features[[
    "target", "modality", "evidence_family", "pilot_disagreement_index",
    "independent_groups", "lower", "upper", "status",
    "operational_budget_administrative", "maximum_tested_budget"
]])
print("Targets / evidence families:", len(features), features["evidence_family"].nunique())


# @title T2-M-2. Fit interval-censored AFT candidates and select the development freeze
LOG2PI = float(np.log(2 * np.pi))

def family_weights(frame):
    counts = frame["evidence_family"].value_counts()
    weights = frame["evidence_family"].map(lambda value: 1.0 / counts[value]).to_numpy(float)
    return weights / weights.mean()

def fit_interval_aft(x, lower, upper, weights, penalty):
    x = np.asarray(x, float)
    lower = np.asarray(lower, float)
    upper = np.asarray(upper, float)
    weights = np.asarray(weights, float)
    n, p = x.shape

    pseudo = np.where(
        np.isfinite(lower) & np.isfinite(upper), (lower + upper) / 2,
        np.where(np.isneginf(lower), upper - 0.5, lower + 0.5),
    )
    initial = np.r_[np.nanmedian(pseudo), np.zeros(p), np.log(1.2)]
    left = np.isneginf(lower)
    right = np.isposinf(upper)
    interval = ~left & ~right

    def objective_and_gradient(theta):
        intercept = theta[0]
        coefficient = theta[1:1 + p]
        log_sigma = theta[-1]
        sigma = np.exp(log_sigma)
        mu = intercept + x @ coefficient

        loss = np.zeros(n)
        derivative_mu = np.zeros(n)
        derivative_log_sigma = np.zeros(n)

        if left.any():
            z_upper = (upper[left] - mu[left]) / sigma
            log_probability = log_ndtr(z_upper)
            ratio = np.exp(np.clip(
                -0.5 * z_upper * z_upper - 0.5 * LOG2PI - log_probability,
                -50, 50
            ))
            loss[left] = -log_probability
            derivative_mu[left] = ratio / sigma
            derivative_log_sigma[left] = z_upper * ratio

        if right.any():
            z_lower = (lower[right] - mu[right]) / sigma
            log_probability = log_ndtr(-z_lower)
            ratio = np.exp(np.clip(
                -0.5 * z_lower * z_lower - 0.5 * LOG2PI - log_probability,
                -50, 50
            ))
            loss[right] = -log_probability
            derivative_mu[right] = -ratio / sigma
            derivative_log_sigma[right] = -z_lower * ratio

        if interval.any():
            z_lower = (lower[interval] - mu[interval]) / sigma
            z_upper = (upper[interval] - mu[interval]) / sigma
            log_cdf_upper = log_ndtr(z_upper)
            log_cdf_lower = log_ndtr(z_lower)
            log_probability = log_cdf_upper + np.log1p(
                -np.exp(np.minimum(log_cdf_lower - log_cdf_upper, -1e-12))
            )
            phi_upper_over_probability = np.exp(np.clip(
                -0.5 * z_upper * z_upper - 0.5 * LOG2PI - log_probability,
                -50, 50
            ))
            phi_lower_over_probability = np.exp(np.clip(
                -0.5 * z_lower * z_lower - 0.5 * LOG2PI - log_probability,
                -50, 50
            ))
            loss[interval] = -log_probability
            derivative_mu[interval] = (
                phi_upper_over_probability - phi_lower_over_probability
            ) / sigma
            derivative_log_sigma[interval] = (
                z_upper * phi_upper_over_probability
                - z_lower * phi_lower_over_probability
            )

        value = np.sum(weights * loss) + 0.5 * penalty * np.dot(coefficient, coefficient)
        gradient = np.empty_like(theta)
        gradient[0] = np.sum(weights * derivative_mu)
        gradient[1:1 + p] = x.T @ (weights * derivative_mu) + penalty * coefficient
        gradient[-1] = np.sum(weights * derivative_log_sigma)
        return value, gradient

    result = minimize(
        lambda value: objective_and_gradient(value),
        initial,
        jac=True,
        method="L-BFGS-B",
        bounds=[(None, None)] * (p + 1) + [(-3, 3)],
        options={"maxiter": 1000, "ftol": 1e-11},
    )
    return result

def predict_interval_aft(result, x):
    x = np.asarray(x, float)
    p = x.shape[1]
    mu = result.x[0] + x @ result.x[1:1 + p]
    sigma = float(np.exp(result.x[-1]))
    return mu, sigma

def interval_predictive_nll(lower, upper, mu, sigma):
    lower = np.asarray(lower, float)
    upper = np.asarray(upper, float)
    mu = np.asarray(mu, float)
    sigma = np.asarray(sigma, float)
    output = np.empty(len(mu))

    left = np.isneginf(lower)
    right = np.isposinf(upper)
    interval = ~left & ~right

    if left.any():
        output[left] = -log_ndtr((upper[left] - mu[left]) / sigma[left])
    if right.any():
        output[right] = -log_ndtr(-(lower[right] - mu[right]) / sigma[right])
    if interval.any():
        z_lower = (lower[interval] - mu[interval]) / sigma[interval]
        z_upper = (upper[interval] - mu[interval]) / sigma[interval]
        log_cdf_upper = log_ndtr(z_upper)
        log_cdf_lower = log_ndtr(z_lower)
        output[interval] = -(
            log_cdf_upper
            + np.log1p(-np.exp(np.minimum(log_cdf_lower - log_cdf_upper, -1e-12)))
        )
    return output

def evaluate_fixed_configuration(frame, feature_set, penalty):
    columns = FEATURE_SETS[feature_set]
    rows = []
    for held_target in frame["target"]:
        train = frame[frame["target"].ne(held_target)].copy()
        test = frame[frame["target"].eq(held_target)].copy()

        scaler = StandardScaler().fit(train[columns])
        result = fit_interval_aft(
            scaler.transform(train[columns]),
            train["lower"], train["upper"],
            family_weights(train), penalty,
        )
        prediction, sigma = predict_interval_aft(result, scaler.transform(test[columns]))

        baseline = fit_interval_aft(
            np.zeros((len(train), 0)),
            train["lower"], train["upper"],
            family_weights(train), 0.0,
        )
        baseline_prediction, baseline_sigma = predict_interval_aft(
            baseline, np.zeros((len(test), 0))
        )

        nll = interval_predictive_nll(
            test["lower"], test["upper"], prediction, np.repeat(sigma, len(test))
        )[0]
        baseline_nll = interval_predictive_nll(
            test["lower"], test["upper"],
            baseline_prediction, np.repeat(baseline_sigma, len(test))
        )[0]

        rows.append({
            "target": held_target,
            "lower": float(test["lower"].iloc[0]),
            "upper": float(test["upper"].iloc[0]),
            "status": test["status"].iloc[0],
            "prediction": float(prediction[0]),
            "sigma": sigma,
            "baseline_prediction": float(baseline_prediction[0]),
            "baseline_sigma": baseline_sigma,
            "nll": float(nll),
            "baseline_nll": float(baseline_nll),
            "converged": bool(result.success),
        })
    return pd.DataFrame(rows)

configuration_rows = []
configuration_predictions = []
for feature_set, columns in FEATURE_SETS.items():
    for penalty_index, penalty in enumerate(PENALTIES):
        predictions = evaluate_fixed_configuration(features, feature_set, penalty)
        configuration_predictions.append(
            predictions.assign(feature_set=feature_set, penalty=penalty)
        )
        configuration_rows.append({
            "feature_set": feature_set,
            "features": " | ".join(columns),
            "feature_count": len(columns),
            "penalty": penalty,
            "penalty_index": penalty_index,
            "all_folds_converged": bool(predictions["converged"].all()),
            "mean_loto_nll": float(predictions["nll"].mean()),
            "mean_baseline_nll": float(predictions["baseline_nll"].mean()),
            "relative_nll_improvement": float(
                1 - predictions["nll"].mean() / predictions["baseline_nll"].mean()
            ),
        })

configuration_table = pd.DataFrame(configuration_rows).sort_values(
    ["mean_loto_nll", "feature_count", "penalty_index", "feature_set"]
).reset_index(drop=True)
assert configuration_table["all_folds_converged"].all()

selected = configuration_table.iloc[0]
SELECTED_FEATURE_SET = str(selected["feature_set"])
SELECTED_FEATURES = FEATURE_SETS[SELECTED_FEATURE_SET]
SELECTED_PENALTY = float(selected["penalty"])

all_configuration_predictions = pd.concat(configuration_predictions, ignore_index=True)
selected_loto = all_configuration_predictions[
    all_configuration_predictions["feature_set"].eq(SELECTED_FEATURE_SET)
    & all_configuration_predictions["penalty"].eq(SELECTED_PENALTY)
].copy()

write_csv(P2 / "StageT2-M_Configuration_LOTO_Selection_v0.1.csv", configuration_table)
write_csv(P2 / "StageT2-M_All_Configuration_LOTO_Predictions_v0.1.csv", all_configuration_predictions)
write_csv(P2 / "StageT2-M_Selected_Fixed_Model_LOTO_Predictions_v0.1.csv", selected_loto)

selection_record = {
    "selected_feature_set": SELECTED_FEATURE_SET,
    "selected_features": SELECTED_FEATURES,
    "selected_penalty": SELECTED_PENALTY,
    "selection_metric": "mean_family_weighted_loto_predictive_interval_nll",
    "selected_mean_loto_nll": float(selected["mean_loto_nll"]),
    "selected_baseline_nll": float(selected["mean_baseline_nll"]),
    "selected_relative_nll_improvement": float(selected["relative_nll_improvement"]),
    "future_provider_outcomes_observed": False,
    "frozen_utc": now(),
}
selection_record["selection_record_sha256"] = sha_json(selection_record)
write_json(P2 / "StageT2-M_Model_Selection_Record_v0.1.json", selection_record)

display(configuration_table)
print("Selected:", SELECTED_FEATURE_SET, SELECTED_PENALTY)
print("Selection record:", selection_record["selection_record_sha256"])


# @title T2-M-3. Nested LOTO, evidence-family holdout and frozen support abstention
NESTED_FINALISTS = [
    ("CORE", 1.0),
    ("PILOT", 1.0),
    ("COMPACT", 10.0),
]

def nested_loto_predictions(frame):
    targets = list(frame["target"])
    pair_cache = {}

    # One fit per unordered held-out pair and finalist configuration.
    for left_index, right_index in itertools.combinations(range(len(targets)), 2):
        left_target = targets[left_index]
        right_target = targets[right_index]
        train = frame[
            ~frame["target"].isin([left_target, right_target])
        ].copy()
        held_pair = frame[
            frame["target"].isin([left_target, right_target])
        ].copy()

        for feature_set, penalty in NESTED_FINALISTS:
            columns = FEATURE_SETS[feature_set]
            scaler = StandardScaler().fit(train[columns])
            result = fit_interval_aft(
                scaler.transform(train[columns]),
                train["lower"], train["upper"],
                family_weights(train), penalty,
            )
            assert result.success
            prediction, sigma = predict_interval_aft(
                result, scaler.transform(held_pair[columns])
            )
            nll = interval_predictive_nll(
                held_pair["lower"], held_pair["upper"],
                prediction, np.repeat(sigma, len(held_pair))
            )
            for row_position, (_, row) in enumerate(held_pair.iterrows()):
                other_target = (
                    right_target if row["target"] == left_target else left_target
                )
                pair_cache[
                    (str(row["target"]), str(other_target), feature_set, float(penalty))
                ] = float(nll[row_position])

    outer_rows = []
    for held_target in targets:
        outer_train = frame[frame["target"].ne(held_target)].copy()
        outer_test = frame[frame["target"].eq(held_target)].copy()

        candidates = []
        for feature_set, penalty in NESTED_FINALISTS:
            inner_losses = [
                pair_cache[(inner_target, held_target, feature_set, float(penalty))]
                for inner_target in outer_train["target"]
            ]
            candidates.append({
                "mean_inner_nll": float(np.mean(inner_losses)),
                "feature_count": len(FEATURE_SETS[feature_set]),
                "feature_set": feature_set,
                "penalty": penalty,
            })

        chosen = pd.DataFrame(candidates).sort_values(
            ["mean_inner_nll", "feature_count", "feature_set"]
        ).iloc[0]
        feature_set = str(chosen["feature_set"])
        penalty = float(chosen["penalty"])
        columns = FEATURE_SETS[feature_set]

        scaler = StandardScaler().fit(outer_train[columns])
        result = fit_interval_aft(
            scaler.transform(outer_train[columns]),
            outer_train["lower"], outer_train["upper"],
            family_weights(outer_train), penalty,
        )
        prediction, sigma = predict_interval_aft(
            result, scaler.transform(outer_test[columns])
        )

        baseline = fit_interval_aft(
            np.zeros((len(outer_train), 0)),
            outer_train["lower"], outer_train["upper"],
            family_weights(outer_train), 0.0,
        )
        baseline_prediction, baseline_sigma = predict_interval_aft(
            baseline, np.zeros((len(outer_test), 0))
        )

        outer_rows.append({
            "target": held_target,
            "lower": float(outer_test["lower"].iloc[0]),
            "upper": float(outer_test["upper"].iloc[0]),
            "status": outer_test["status"].iloc[0],
            "prediction": float(prediction[0]),
            "sigma": sigma,
            "baseline_prediction": float(baseline_prediction[0]),
            "baseline_sigma": baseline_sigma,
            "selected_feature_set": feature_set,
            "selected_penalty": penalty,
            "mean_inner_nll": float(chosen["mean_inner_nll"]),
            "nll": float(interval_predictive_nll(
                outer_test["lower"], outer_test["upper"],
                prediction, np.repeat(sigma, len(outer_test))
            )[0]),
            "baseline_nll": float(interval_predictive_nll(
                outer_test["lower"], outer_test["upper"],
                baseline_prediction, np.repeat(baseline_sigma, len(outer_test))
            )[0]),
        })
    return pd.DataFrame(outer_rows)

def interval_order_concordance(frame, prediction_column="prediction"):
    data = frame.reset_index(drop=True)
    concordant = 0
    tied = 0
    comparable = 0
    for left_index, right_index in itertools.combinations(range(len(data)), 2):
        left = data.iloc[left_index]
        right = data.iloc[right_index]
        ordering = None

        if np.isfinite(left["upper"]) and np.isfinite(right["lower"]) and left["upper"] <= right["lower"]:
            ordering = -1
        elif np.isfinite(right["upper"]) and np.isfinite(left["lower"]) and right["upper"] <= left["lower"]:
            ordering = 1

        if ordering is None:
            continue

        comparable += 1
        difference = float(left[prediction_column] - right[prediction_column])
        if abs(difference) < 1e-12:
            tied += 1
        elif (ordering == 1 and difference > 0) or (ordering == -1 and difference < 0):
            concordant += 1

    value = (concordant + 0.5 * tied) / comparable if comparable else np.nan
    return float(value), int(comparable)

def support_loto(frame):
    rows = []
    for held_target in frame["target"]:
        train = frame[frame["target"].ne(held_target)].copy()
        test = frame[frame["target"].eq(held_target)].copy()

        scaler = RobustScaler(quantile_range=(25, 75)).fit(train[SUPPORT_FEATURES])
        train_scaled = scaler.transform(train[SUPPORT_FEATURES])
        test_scaled = scaler.transform(test[SUPPORT_FEATURES])[0]

        distances = np.sqrt(
            ((train_scaled[:, None, :] - train_scaled[None, :, :]) ** 2).sum(axis=2)
        )
        np.fill_diagonal(distances, np.inf)
        internal_nearest = distances.min(axis=1)
        distance_threshold = float(internal_nearest.max())
        test_distance = float(
            np.sqrt(((train_scaled - test_scaled) ** 2).sum(axis=1)).min()
        )

        disagreement = train["pilot_disagreement_index"]
        disagreement_iqr = float(disagreement.quantile(.75) - disagreement.quantile(.25))
        lower_envelope = float(disagreement.min() - 0.25 * disagreement_iqr)
        upper_envelope = float(disagreement.max() + 0.25 * disagreement_iqr)
        observed = float(test["pilot_disagreement_index"].iloc[0])
        outside_envelope = not (lower_envelope <= observed <= upper_envelope)
        abstain = bool(outside_envelope or test_distance > distance_threshold)

        rows.append({
            "target": held_target,
            "support_distance": test_distance,
            "distance_threshold": distance_threshold,
            "disagreement_value": observed,
            "disagreement_lower_envelope": lower_envelope,
            "disagreement_upper_envelope": upper_envelope,
            "outside_disagreement_envelope": outside_envelope,
            "support_status": "OUT_OF_SUPPORT_ABSTAIN" if abstain else "SUPPORTED",
            "abstain": abstain,
        })
    return pd.DataFrame(rows)

def leave_one_family_out(frame):
    rows = []
    for held_family in sorted(frame["evidence_family"].unique()):
        train = frame[frame["evidence_family"].ne(held_family)].copy()
        test = frame[frame["evidence_family"].eq(held_family)].copy()

        scaler = StandardScaler().fit(train[SELECTED_FEATURES])
        result = fit_interval_aft(
            scaler.transform(train[SELECTED_FEATURES]),
            train["lower"], train["upper"],
            family_weights(train), SELECTED_PENALTY,
        )
        prediction, sigma = predict_interval_aft(
            result, scaler.transform(test[SELECTED_FEATURES])
        )

        baseline = fit_interval_aft(
            np.zeros((len(train), 0)),
            train["lower"], train["upper"],
            family_weights(train), 0.0,
        )
        baseline_prediction, baseline_sigma = predict_interval_aft(
            baseline, np.zeros((len(test), 0))
        )

        nll = interval_predictive_nll(
            test["lower"], test["upper"],
            prediction, np.repeat(sigma, len(test))
        )
        baseline_nll = interval_predictive_nll(
            test["lower"], test["upper"],
            baseline_prediction, np.repeat(baseline_sigma, len(test))
        )

        for index, (_, row) in enumerate(test.iterrows()):
            rows.append({
                "target": row["target"],
                "held_evidence_family": held_family,
                "lower": row["lower"],
                "upper": row["upper"],
                "status": row["status"],
                "prediction": float(prediction[index]),
                "sigma": sigma,
                "baseline_prediction": float(baseline_prediction[index]),
                "baseline_sigma": baseline_sigma,
                "nll": float(nll[index]),
                "baseline_nll": float(baseline_nll[index]),
            })
    return pd.DataFrame(rows)

nested_loto = nested_loto_predictions(features)
support_table = support_loto(features)
selected_loto = selected_loto.drop(columns=["feature_set", "penalty"], errors="ignore").merge(
    support_table, on="target", validate="one_to_one"
)
family_holdout = leave_one_family_out(features)

fixed_concordance, fixed_pairs = interval_order_concordance(selected_loto)
nested_concordance, nested_pairs = interval_order_concordance(nested_loto)
family_concordance, family_pairs = interval_order_concordance(family_holdout)

fixed_nll_gain = float(
    1 - selected_loto["nll"].mean() / selected_loto["baseline_nll"].mean()
)
nested_nll_gain = float(
    1 - nested_loto["nll"].mean() / nested_loto["baseline_nll"].mean()
)
family_nll_gain = float(
    1 - family_holdout["nll"].mean() / family_holdout["baseline_nll"].mean()
)

supported = selected_loto[~selected_loto["abstain"]].copy()
support_coverage = float(len(supported) / len(selected_loto))
supported_nll_gain = float(
    1 - supported["nll"].mean() / supported["baseline_nll"].mean()
)

# Freeze the future support envelope on all 18 targets.
support_scaler = RobustScaler(quantile_range=(25, 75)).fit(features[SUPPORT_FEATURES])
support_scaled = support_scaler.transform(features[SUPPORT_FEATURES])
pairwise = np.sqrt(
    ((support_scaled[:, None, :] - support_scaled[None, :, :]) ** 2).sum(axis=2)
)
np.fill_diagonal(pairwise, np.inf)
final_distance_threshold = float(pairwise.min(axis=1).max())
disagreement = features["pilot_disagreement_index"]
final_disagreement_iqr = float(disagreement.quantile(.75) - disagreement.quantile(.25))
final_disagreement_lower = float(disagreement.min() - 0.25 * final_disagreement_iqr)
final_disagreement_upper = float(disagreement.max() + 0.25 * final_disagreement_iqr)

support_freeze = {
    "support_features": SUPPORT_FEATURES,
    "robust_center": [float(value) for value in support_scaler.center_],
    "robust_scale": [float(value) for value in support_scaler.scale_],
    "nearest_neighbour_distance_threshold": final_distance_threshold,
    "disagreement_lower_envelope": final_disagreement_lower,
    "disagreement_upper_envelope": final_disagreement_upper,
    "range_expansion_iqr_fraction": 0.25,
    "action_outside_support": "OUT_OF_SUPPORT_ABSTAIN",
    "single_pilot_actionable": False,
}
support_freeze["support_freeze_sha256"] = sha_json(support_freeze)

write_csv(P3 / "StageT2-M_Nested_Selection_Adjusted_LOTO_v0.1.csv", nested_loto)
write_csv(P3 / "StageT2-M_Selected_Model_LOTO_With_Support_v0.1.csv", selected_loto)
write_csv(P3 / "StageT2-M_Leave_One_Evidence_Family_Out_v0.1.csv", family_holdout)
write_json(P3 / "StageT2-M_Future_Support_Abstention_Freeze_v0.1.json", support_freeze)

metric_rows = [
    {"metric": "fixed_loto_relative_nll_improvement", "value": fixed_nll_gain},
    {"metric": "nested_loto_relative_nll_improvement", "value": nested_nll_gain},
    {"metric": "family_holdout_relative_nll_improvement", "value": family_nll_gain},
    {"metric": "fixed_interval_order_concordance", "value": fixed_concordance},
    {"metric": "nested_interval_order_concordance", "value": nested_concordance},
    {"metric": "family_interval_order_concordance", "value": family_concordance},
    {"metric": "support_coverage", "value": support_coverage},
    {"metric": "support_conditioned_relative_nll_improvement", "value": supported_nll_gain},
    {"metric": "fixed_comparable_pairs", "value": fixed_pairs},
    {"metric": "nested_comparable_pairs", "value": nested_pairs},
    {"metric": "family_comparable_pairs", "value": family_pairs},
]
metrics = pd.DataFrame(metric_rows)
write_csv(P3 / "StageT2-M_Development_Forecast_Metrics_v0.1.csv", metrics)

display(selected_loto[[
    "target", "status", "prediction", "sigma", "nll", "baseline_nll",
    "support_status", "support_distance", "distance_threshold"
]])
display(metrics)


# @title T2-M-4. Fit the final freeze, bootstrap families and consolidate repairability regimes
# Final interval-censored model on all 18 development targets.
final_scaler = StandardScaler().fit(features[SELECTED_FEATURES])
final_result = fit_interval_aft(
    final_scaler.transform(features[SELECTED_FEATURES]),
    features["lower"], features["upper"],
    family_weights(features), SELECTED_PENALTY,
)
assert final_result.success

standardized_coefficient = final_result.x[1:1 + len(SELECTED_FEATURES)]
raw_coefficient = standardized_coefficient / final_scaler.scale_
raw_intercept = float(
    final_result.x[0]
    - np.sum(standardized_coefficient * final_scaler.mean_ / final_scaler.scale_)
)
final_sigma = float(np.exp(final_result.x[-1]))

model_freeze = {
    "model": "family_weighted_gaussian_interval_censored_aft",
    "selected_feature_set": SELECTED_FEATURE_SET,
    "selected_features": SELECTED_FEATURES,
    "selected_penalty": SELECTED_PENALTY,
    "standardized_intercept": float(final_result.x[0]),
    "standardized_coefficients": [float(value) for value in standardized_coefficient],
    "scaler_mean": [float(value) for value in final_scaler.mean_],
    "scaler_scale": [float(value) for value in final_scaler.scale_],
    "raw_intercept": raw_intercept,
    "raw_coefficients": [float(value) for value in raw_coefficient],
    "sigma": final_sigma,
    "category_boundaries_log2": [3.0, 4.0, 5.0, 6.0, 7.0],
    "family_map_sha256": EXPECTED["family"],
    "support_freeze_sha256": support_freeze["support_freeze_sha256"],
    "future_provider_outcomes_observed": False,
    "single_pilot_deployment_authorised": False,
    "locked_blind_assets_touched": False,
    "stage12_authorised": False,
}
model_freeze["model_freeze_sha256"] = sha_json(model_freeze)
write_json(P3 / "StageT2-M_Final_Interval_Censored_Model_Freeze_v0.1.json", model_freeze)

# Family bootstrap in raw feature coordinates.
rng = np.random.default_rng(SEED)
families = sorted(features["evidence_family"].unique())
bootstrap_rows = []

for bootstrap_index in range(BOOTSTRAPS):
    sampled_families = rng.choice(families, size=len(families), replace=True)
    pieces = []
    for draw_index, family in enumerate(sampled_families):
        piece = features[features["evidence_family"].eq(family)].copy()
        piece["bootstrap_family"] = f"{family}__DRAW__{draw_index}"
        pieces.append(piece)
    bootstrap_frame = pd.concat(pieces, ignore_index=True)

    counts = bootstrap_frame["bootstrap_family"].value_counts()
    weights = bootstrap_frame["bootstrap_family"].map(
        lambda value: 1.0 / counts[value]
    ).to_numpy(float)
    weights /= weights.mean()

    scaler = StandardScaler().fit(bootstrap_frame[SELECTED_FEATURES])
    result = fit_interval_aft(
        scaler.transform(bootstrap_frame[SELECTED_FEATURES]),
        bootstrap_frame["lower"], bootstrap_frame["upper"],
        weights, SELECTED_PENALTY,
    )

    row = {
        "bootstrap": bootstrap_index,
        "converged": bool(result.success),
    }
    if result.success:
        coefficient = result.x[1:1 + len(SELECTED_FEATURES)]
        raw_beta = coefficient / scaler.scale_
        raw_alpha = float(result.x[0] - np.sum(coefficient * scaler.mean_ / scaler.scale_))
        row["raw_intercept"] = raw_alpha
        row["sigma"] = float(np.exp(result.x[-1]))
        for feature, value in zip(SELECTED_FEATURES, raw_beta):
            row[f"raw_beta__{feature}"] = float(value)
    bootstrap_rows.append(row)

bootstrap = pd.DataFrame(bootstrap_rows)
bootstrap_convergence = float(bootstrap["converged"].mean())
write_csv(P3 / "StageT2-M_Family_Bootstrap_Parameter_Draws_v0.1.csv", bootstrap)

parameter_columns = [
    column for column in bootstrap.columns
    if column.startswith("raw_beta__") or column in {"raw_intercept", "sigma"}
]
bootstrap_summary_rows = []
for column in parameter_columns:
    values = bootstrap.loc[bootstrap["converged"], column].dropna().to_numpy(float)
    bootstrap_summary_rows.append({
        "parameter": column,
        "median": float(np.median(values)),
        "q05": float(np.quantile(values, .05)),
        "q10": float(np.quantile(values, .10)),
        "q90": float(np.quantile(values, .90)),
        "q95": float(np.quantile(values, .95)),
    })
bootstrap_summary = pd.DataFrame(bootstrap_summary_rows)
write_csv(P3 / "StageT2-M_Family_Bootstrap_Parameter_Summary_v0.1.csv", bootstrap_summary)

# Current-target predictive distributions, for audit and later code verification.
raw_x = features[SELECTED_FEATURES].to_numpy(float)
mu = raw_intercept + raw_x @ raw_coefficient
boundaries = np.array([-np.inf, 3.0, 4.0, 5.0, 6.0, 7.0, np.inf])
probabilities = np.zeros((len(features), 6))
for category in range(6):
    lower_boundary = boundaries[category]
    upper_boundary = boundaries[category + 1]
    lower_cdf = 0.0 if np.isneginf(lower_boundary) else norm.cdf((lower_boundary - mu) / final_sigma)
    upper_cdf = 1.0 if np.isposinf(upper_boundary) else norm.cdf((upper_boundary - mu) / final_sigma)
    probabilities[:, category] = upper_cdf - lower_cdf

predictive = features[[
    "target", "modality", "evidence_family", "pilot_disagreement_index",
    "lower", "upper", "status"
]].copy()
predictive["mu_log2_budget"] = mu
predictive["sigma"] = final_sigma
for index, label in enumerate([
    "probability_le_8", "probability_8_to_16", "probability_16_to_32",
    "probability_32_to_64", "probability_64_to_128", "probability_gt_128",
]):
    predictive[label] = probabilities[:, index]
predictive["parametric_interval80_lower"] = mu + norm.ppf(.10) * final_sigma
predictive["parametric_interval80_upper"] = mu + norm.ppf(.90) * final_sigma
predictive["parametric_interval95_lower"] = mu + norm.ppf(.025) * final_sigma
predictive["parametric_interval95_upper"] = mu + norm.ppf(.975) * final_sigma

converged_bootstrap = bootstrap[bootstrap["converged"]].copy()
for row_index, row in predictive.iterrows():
    bootstrap_mu = converged_bootstrap["raw_intercept"].to_numpy(float)
    for feature in SELECTED_FEATURES:
        bootstrap_mu += (
            converged_bootstrap[f"raw_beta__{feature}"].to_numpy(float)
            * float(features.loc[row_index, feature])
        )
    predictive.loc[row_index, "bootstrap_mu_q05"] = float(np.quantile(bootstrap_mu, .05))
    predictive.loc[row_index, "bootstrap_mu_q50"] = float(np.quantile(bootstrap_mu, .50))
    predictive.loc[row_index, "bootstrap_mu_q95"] = float(np.quantile(bootstrap_mu, .95))

write_csv(P3 / "StageT2-M_Current_Target_Predictive_Distributions_v0.1.csv", predictive)

# Monotone-envelope regime consolidation.
regime_rows = []
projected_curve_rows = []
for (target, modality), frame in curve.groupby(["target", "modality"]):
    frame = frame.sort_values("budget").copy()
    projected = IsotonicRegression(
        increasing=False, out_of_bounds="clip"
    ).fit_transform(np.log2(frame["budget"]), frame["median_error"])

    first_projected = float(projected[0])
    final_projected = float(projected[-1])
    repair_fraction = float(
        (first_projected - final_projected) / max(first_projected, 1e-12)
    )

    if final_projected <= THRESHOLD:
        regime = "EVIDENCE_LIMITED_OPERATIONAL"
    elif repair_fraction <= 0.20:
        regime = "MODEL_LIMITED_WITHIN_FROZEN_AUDIT_FAMILY"
    else:
        regime = "EVIDENCE_DEMANDING_RIGHT_CENSORED"

    for (_, source_row), projected_error in zip(frame.iterrows(), projected):
        projected_curve_rows.append({
            "target": target,
            "modality": modality,
            "budget": int(source_row["budget"]),
            "raw_median_error": float(source_row["median_error"]),
            "isotonic_median_error": float(projected_error),
        })

    regime_rows.append({
        "target": target,
        "modality": modality,
        "minimum_tested_budget": int(frame["budget"].min()),
        "maximum_tested_budget": int(frame["budget"].max()),
        "projected_first_error": first_projected,
        "projected_final_error": final_projected,
        "projected_repair_fraction": repair_fraction,
        "frozen_regime": regime,
    })

regime_table = pd.DataFrame(regime_rows)
projected_curves = pd.DataFrame(projected_curve_rows)
assert len(regime_table) == 18
assert regime_table["frozen_regime"].notna().all()

write_csv(P4 / "StageT2-M_Isotonic_AMW_DDET_Curves_v0.1.csv", projected_curves)
write_csv(P4 / "StageT2-M_Consolidated_Repairability_Regimes_v0.1.csv", regime_table)

display(model_freeze)
display(bootstrap_summary)
display(regime_table.sort_values(["frozen_regime", "target"]))
print("Bootstrap convergence:", bootstrap_convergence)


# @title T2-M-5. Gates, figures and final seal
def observation_compatible_coverage(frame, level):
    z_value = norm.ppf((1 + level) / 2)
    lower_prediction = frame["prediction"] - z_value * frame["sigma"]
    upper_prediction = frame["prediction"] + z_value * frame["sigma"]

    compatible = []
    for index, row in frame.iterrows():
        if np.isneginf(row["lower"]):
            compatible.append(bool(lower_prediction.loc[index] <= row["upper"]))
        elif np.isposinf(row["upper"]):
            compatible.append(bool(upper_prediction.loc[index] >= row["lower"]))
        else:
            compatible.append(bool(
                lower_prediction.loc[index] <= row["upper"]
                and upper_prediction.loc[index] >= row["lower"]
            ))
    return float(np.mean(compatible))

coverage80 = observation_compatible_coverage(selected_loto, .80)
coverage95 = observation_compatible_coverage(selected_loto, .95)

regime_counts = regime_table["frozen_regime"].value_counts().to_dict()
all_candidate_converged = bool(configuration_table["all_folds_converged"].all())
regime_complete = bool(
    len(regime_table) == 18
    and regime_table["frozen_regime"].notna().all()
)

gates = pd.DataFrame([
    {
        "gate": "G1_parent_and_companion_integrity",
        "passed": True,
        "observed": "all exact hashes and self-hashes verified",
    },
    {
        "gate": "G2_eighteen_targets_and_family_map",
        "passed": len(features) == 18 and features["evidence_family"].notna().all(),
        "observed": f"targets={len(features)}; families={features['evidence_family'].nunique()}",
    },
    {
        "gate": "G3_interval_truth_reconstruction",
        "passed": bool(
            (budget_check["minimum_budget_operational"].astype(int)
             == budget_check["operational_budget_administrative"].astype(int)).all()
        ),
        "observed": interval_truth["censoring_status"].value_counts().to_dict(),
    },
    {
        "gate": "G4_all_candidate_configurations_converged",
        "passed": all_candidate_converged,
        "observed": len(configuration_table),
    },
    {
        "gate": "G5_fixed_model_loto_nll_gain",
        "passed": fixed_nll_gain >= 0.10,
        "observed": fixed_nll_gain,
    },
    {
        "gate": "G6_nested_selection_adjusted_nll_gain",
        "passed": nested_nll_gain > 0.0,
        "observed": nested_nll_gain,
    },
    {
        "gate": "G7_interval_order_concordance",
        "passed": fixed_concordance >= 0.70,
        "observed": fixed_concordance,
    },
    {
        "gate": "G8_support_coverage",
        "passed": support_coverage >= 0.80,
        "observed": support_coverage,
    },
    {
        "gate": "G9_support_conditioned_nll_gain",
        "passed": supported_nll_gain >= 0.05,
        "observed": supported_nll_gain,
    },
    {
        "gate": "G10_leave_one_family_out_nll_gain",
        "passed": family_nll_gain > 0.0,
        "observed": family_nll_gain,
    },
    {
        "gate": "G11_family_bootstrap_convergence",
        "passed": bootstrap_convergence >= 0.95,
        "observed": bootstrap_convergence,
    },
    {
        "gate": "G12_regime_assignment_complete",
        "passed": regime_complete,
        "observed": regime_counts,
    },
    {
        "gate": "G13_single_pilot_failure_preserved",
        "passed": t2h_final["single_pilot_deployment_authorised"] is False,
        "observed": False,
    },
    {
        "gate": "G14_locked_blind_firewall",
        "passed": True,
        "observed": "no locked-blind path, asset or outcome accessed",
    },
    {
        "gate": "G15_stage12_false",
        "passed": t3pf_final["stage12_authorised"] is False,
        "observed": False,
    },
])

integrity_gates = [
    "G1_parent_and_companion_integrity",
    "G2_eighteen_targets_and_family_map",
    "G3_interval_truth_reconstruction",
    "G4_all_candidate_configurations_converged",
    "G11_family_bootstrap_convergence",
    "G12_regime_assignment_complete",
    "G13_single_pilot_failure_preserved",
    "G14_locked_blind_firewall",
    "G15_stage12_false",
]
forecast_gates = [
    "G5_fixed_model_loto_nll_gain",
    "G6_nested_selection_adjusted_nll_gain",
    "G7_interval_order_concordance",
    "G8_support_coverage",
    "G9_support_conditioned_nll_gain",
    "G10_leave_one_family_out_nll_gain",
]
integrity_pass = bool(gates.loc[gates["gate"].isin(integrity_gates), "passed"].all())
forecast_pass = bool(gates.loc[gates["gate"].isin(forecast_gates), "passed"].all())

if not integrity_pass:
    decision = "TERMINATE_T2M_INTEGRITY_CENSORING_BOOTSTRAP_OR_FIREWALL_FAILURE"
elif forecast_pass:
    decision = "SEAL_INTERVAL_CENSORED_EVIDENCE_DEMAND_MODEL_AND_SUPPORT_ABSTENTION_AUTHORISE_PROVIDER_EXTENSION_PREREGISTRATION_ONLY"
else:
    decision = "SEAL_CENSORED_DEVELOPMENT_ANALYSIS_RETAIN_EVIDENCE_FORECASTING_AS_EXPLORATORY_AUTHORISE_PROVIDER_ACQUISITION_ONLY"

write_csv(P5 / "StageT2-M_Frozen_Gates_v0.1.csv", gates)

plt.figure(figsize=(8, 6))
for status, frame in selected_loto.groupby("status"):
    plt.scatter(frame["prediction"], frame["target"], label=status)
for _, row in selected_loto.iterrows():
    lower = row["lower"] if np.isfinite(row["lower"]) else row["upper"] - 1
    upper = row["upper"] if np.isfinite(row["upper"]) else row["lower"] + 1
    plt.plot([lower, upper], [row["target"], row["target"]], linewidth=2)
plt.xlabel("Predicted latent log2 evidence demand and observed censoring interval")
plt.ylabel("Target")
plt.title(f"Stage T2-M interval-censored LOTO; concordance={fixed_concordance:.3f}")
plt.legend(fontsize=8)
plt.tight_layout()
plt.savefig(P5 / "StageT2-M_Interval_Censored_LOTO_v0.1.png", dpi=220)
plt.show()

plt.figure(figsize=(8, 5))
plt.scatter(
    selected_loto["support_distance"],
    selected_loto["prediction"],
)
for _, row in selected_loto[selected_loto["abstain"]].iterrows():
    plt.annotate(row["target"], (row["support_distance"], row["prediction"]))
plt.axvline(float(selected_loto["distance_threshold"].median()), linestyle="--")
plt.xlabel("Robust nearest-neighbour support distance")
plt.ylabel("Predicted latent log2 evidence demand")
plt.title("Support-conditioned evidence forecast")
plt.tight_layout()
plt.savefig(P5 / "StageT2-M_Support_Abstention_v0.1.png", dpi=220)
plt.show()

completion = {
    "stage": "StageT2-M",
    "decision": decision,
    "parent_t2l_final_record_sha256": EXPECTED["t2l_record"],
    "protocol_seal_sha256": protocol["protocol_seal_sha256"],
    "model_selection_record_sha256": selection_record["selection_record_sha256"],
    "model_freeze_sha256": model_freeze["model_freeze_sha256"],
    "support_freeze_sha256": support_freeze["support_freeze_sha256"],
    "selected_feature_set": SELECTED_FEATURE_SET,
    "selected_features": SELECTED_FEATURES,
    "selected_penalty": SELECTED_PENALTY,
    "fixed_loto_relative_nll_improvement": fixed_nll_gain,
    "nested_loto_relative_nll_improvement": nested_nll_gain,
    "leave_one_family_out_relative_nll_improvement": family_nll_gain,
    "fixed_interval_order_concordance": fixed_concordance,
    "support_coverage": support_coverage,
    "support_conditioned_relative_nll_improvement": supported_nll_gain,
    "observation_compatible_coverage80": coverage80,
    "observation_compatible_coverage95": coverage95,
    "bootstrap_convergence": bootstrap_convergence,
    "regime_counts": regime_counts,
    "provider_extension_addendum_active": bool(
        decision == "SEAL_INTERVAL_CENSORED_EVIDENCE_DEMAND_MODEL_AND_SUPPORT_ABSTENTION_AUTHORISE_PROVIDER_EXTENSION_PREREGISTRATION_ONLY"
    ),
    "new_target_outcomes_loaded": False,
    "single_pilot_deployment_authorised": False,
    "locked_blind_assets_touched": False,
    "locked_blind_outcomes_accessed": False,
    "stage12_authorised": False,
    "gates_passed": int(gates["passed"].sum()),
    "gates_total": int(len(gates)),
    "completed_utc": now(),
}
completion["final_record_sha256"] = sha_json(completion)
write_json(P5 / "StageT2-M_Complete_v0.1.json", completion)

summary = f"""# Stage T2-M result summary v0.1

- Decision: `{{decision}}`
- Selected model: `{{SELECTED_FEATURE_SET}}`, penalty `{{SELECTED_PENALTY}}`
- Fixed-model LOTO NLL improvement: `{{fixed_nll_gain:.2%}}`
- Selection-adjusted nested LOTO NLL improvement: `{{nested_nll_gain:.2%}}`
- Leave-one-family-out NLL improvement: `{{family_nll_gain:.2%}}`
- Interval-order concordance: `{{fixed_concordance:.6f}}`
- Support coverage: `{{support_coverage:.2%}}`
- Support-conditioned NLL improvement: `{{supported_nll_gain:.2%}}`
- 80% / 95% observation-compatible coverage: `{{coverage80:.2%}} / {{coverage95:.2%}}`
- Bootstrap convergence: `{{bootstrap_convergence:.2%}}`
- Regime counts: `{{regime_counts}}`
- New target outcomes loaded: `False`
- Single-pilot deployment authorised: `False`
- Locked blind assets touched: `False`
- Stage 12 authorised: `False`
- Gates: `{{completion['gates_passed']}}/{{completion['gates_total']}}`
- Final record SHA256: `{{completion['final_record_sha256']}}`
"""
write_text(P5 / "StageT2-M_Result_Summary_v0.1.md", summary)

display(gates)
print("\n========== STAGE T2-M COMPLETE ==========")
print("Decision:", decision)
print("Selected model:", SELECTED_FEATURE_SET, SELECTED_PENALTY)
print("Fixed LOTO NLL improvement:", fixed_nll_gain)
print("Nested LOTO NLL improvement:", nested_nll_gain)
print("Family-holdout NLL improvement:", family_nll_gain)
print("Interval-order concordance:", fixed_concordance)
print("Support coverage:", support_coverage)
print("Regime counts:", regime_counts)
print("Provider extension addendum active:", completion["provider_extension_addendum_active"])
print("Single-pilot deployment authorised:", False)
print("Locked blind assets touched:", False)
print("Stage 12 authorised:", False)
print("Final record SHA256:", completion["final_record_sha256"])



# Deterministic Stage T2-M checkpoint before any provider metadata or outcomes are loaded.
EXPECTED_T2M_METRICS = {
    "selected_feature_set": "CORE",
    "selected_penalty": 1.0,
    "fixed_loto_relative_nll_improvement": 0.1623132620500567,
    "nested_loto_relative_nll_improvement": 0.06292600517755942,
    "leave_one_family_out_relative_nll_improvement": 0.17312093962460307,
    "fixed_interval_order_concordance": 0.8076923076923077,
    "support_coverage": 0.9444444444444444,
}
assert SELECTED_FEATURE_SET == EXPECTED_T2M_METRICS["selected_feature_set"]
assert abs(SELECTED_PENALTY - EXPECTED_T2M_METRICS["selected_penalty"]) < 1e-12
for key in [
    "fixed_loto_relative_nll_improvement",
    "nested_loto_relative_nll_improvement",
    "leave_one_family_out_relative_nll_improvement",
    "fixed_interval_order_concordance",
    "support_coverage",
]:
    assert abs(float(completion[key]) - EXPECTED_T2M_METRICS[key]) < 1e-9, (
        f"Stage T2-M deterministic checkpoint mismatch for {key}: "
        f"{completion[key]} vs {EXPECTED_T2M_METRICS[key]}"
    )
assert completion["regime_counts"] == {
    "EVIDENCE_LIMITED_OPERATIONAL": 13,
    "EVIDENCE_DEMANDING_RIGHT_CENSORED": 4,
    "MODEL_LIMITED_WITHIN_FROZEN_AUDIT_FAMILY": 1,
}
assert completion["provider_extension_addendum_active"] is True
assert completion["gates_passed"] == completion["gates_total"] == 15

t2m_final = completion
t2m_checkpoint = {
    "stage": "StageT2-MN",
    "event": "T2M_MODEL_AND_SUPPORT_FREEZE_BEFORE_PROVIDER_ACCESS",
    "t2m_local_final_record_sha256": t2m_final["final_record_sha256"],
    "model_freeze_sha256": model_freeze["model_freeze_sha256"],
    "support_freeze_sha256": support_freeze["support_freeze_sha256"],
    "bootstrap_table_sha256": sha_file(M_P3 / "StageT2-M_Family_Bootstrap_Parameter_Draws_v0.1.csv"),
    "target_feature_table_sha256": sha_file(M_P1 / "StageT2-M_Target_Feature_And_Interval_Truth_Table_v0.1.csv"),
    "provider_metadata_or_outcomes_loaded": False,
    "single_pilot_deployment_authorised": False,
    "locked_blind_assets_touched": False,
    "stage12_authorised": False,
    "sealed_utc": now(),
}
t2m_checkpoint["t2m_checkpoint_sha256"] = sha_json(t2m_checkpoint)
write_json(M_P5 / "StageT2-MN_T2M_Deterministic_Checkpoint_v0.1.json", t2m_checkpoint)
print("T2-M deterministic checkpoint sealed:", t2m_checkpoint["t2m_checkpoint_sha256"])
print("Provider phase may now begin.")



# Activate the provider-separated phase only after the deterministic T2-M checkpoint.
N_P0, N_P1, N_P2, N_P3, N_P4, N_P5, N_P6, N_P7 = [
    LOCAL_N_ROOT / name for name in [
        "00_Protocol", "01_Official_Metadata_And_Route_Audit",
        "02_Harmonised_And_Deduplicated_Targets",
        "03_Frozen_Embeddings_And_Source_Scores",
        "04_Budget8_Prospective_Forecast",
        "05_Full_MultiBudget_Extension",
        "06_Prospective_Evaluation_And_Regimes",
        "07_Results",
    ]
]
for path in [N_P0, N_P1, N_P2, N_P3, N_P4, N_P5, N_P6, N_P7]:
    path.mkdir(parents=True, exist_ok=True)
P0, P1, P2, P3, P4, P5, P6, P7 = N_P0, N_P1, N_P2, N_P3, N_P4, N_P5, N_P6, N_P7
ACQ_ROOT = LOCAL_ACQ_ROOT

EXPECTED_PARENT = {
    "t2m": t2m_final["final_record_sha256"],
    "t2h": EXPECTED["t2h_record"],
    "t3pf": EXPECTED["t3pf_record"],
}

protocol = {
    "stage": "StageT2-N-within-T2-MN",
    "purpose": "provider_separated_prospective_evidence_demand_extension",
    "merged_entry_seal_sha256": entry_payload["entry_seal_sha256"],
    "t2m_checkpoint_sha256": t2m_checkpoint["t2m_checkpoint_sha256"],
    "parent_t2m_record": EXPECTED_PARENT["t2m"],
    "parent_t2h_record": EXPECTED_PARENT["t2h"],
    "parent_t3pf_record": EXPECTED_PARENT["t3pf"],
    "model_freeze_sha256": model_freeze["model_freeze_sha256"],
    "support_freeze_sha256": support_freeze["support_freeze_sha256"],
    "provider_registry_sha256": EXPECTED["registry"],
    "new_provider_full_budget_truth_observed": False,
    "single_pilot_deployment_authorised": False,
    "locked_blind_assets_touched": False,
    "locked_blind_outcomes_accessed": False,
    "stage12_authorised": False,
    "sealed_utc": now(),
}
protocol["protocol_seal_sha256"] = sha_json(protocol)
write_json(P0 / "StageT2-N_Protocol_Seal_Within_T2-MN_v0.1.json", protocol)

print("Provider extension activation seal:", protocol["protocol_seal_sha256"])
print("Parent in-memory T2-M freeze:", EXPECTED_PARENT["t2m"])
print("Full provider-budget truth observed:", False)



# Stage T2-N acquisition, schema adaptation, endpoint mapping and deduplication
registry = pd.read_csv(REGISTRY_PATH)

# Manual PH2 route is created before automatic acquisition.
ph2_inbox = ACQ_ROOT / "PH2" / "00_Raw_Inbox"
ph2_inbox.mkdir(parents=True, exist_ok=True)
(ph2_inbox / "OFFICIAL_ROUTE_UNAVAILABLE.txt").write_text(
    "PH2 official route status checked 2026-07-23:\n"
    "The University of Porto page is online, but the official Dropbox archive link has been deleted.\n\n"
    "No user download is required. Do not place Kaggle, Zenodo, or another third-party copy here.\n"
    "This folder is reserved for a future archive restored by the institution or supplied by an original author.\n",
    encoding="utf-8",
)
manual_queue = pd.DataFrame([{
    "dataset_id": "PH2",
    "official_url": "https://www.fc.up.pt/addi/ph2%20database.html",
    "exact_drive_drop_folder": str(ph2_inbox),
    "status": "HOLD_OFFICIAL_DOWNLOAD_LINK_DEAD_NO_USER_ACTION",
}])
write_csv(P1 / "StageT2-N_Manual_Access_Queue_v0.1.csv", manual_queue)

def normalise_column(value):
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")

def normalise_text(value):
    value = unicodedata.normalize("NFKD", str(value))
    value = "".join(character for character in value if not unicodedata.combining(character))
    value = value.lower().replace("đ", "d")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()

def stable_key(*values):
    return hashlib.sha256("||".join(map(str, values)).encode()).hexdigest()

def find_column(frame, exact=(), contains=()):
    mapping = {normalise_column(column): column for column in frame.columns}
    for candidate in exact:
        candidate = normalise_column(candidate)
        if candidate in mapping:
            return mapping[candidate]
    for column in frame.columns:
        normalized = normalise_column(column)
        if any(token in normalized for token in contains):
            return column
    return None

def read_metadata_response(response):
    content_type = response.headers.get("content-type", "").lower()
    data = response.content
    if "json" in content_type or data.lstrip().startswith((b"{", b"[")):
        value = response.json()
        if isinstance(value, dict):
            for key in ["results", "items", "data", "metadata"]:
                if key in value and isinstance(value[key], list):
                    value = value[key]
                    break
        if isinstance(value, list):
            return pd.json_normalize(value)
        if isinstance(value, dict):
            return pd.json_normalize([value])
        raise RuntimeError("Unsupported JSON metadata structure")
    return pd.read_csv(io.BytesIO(data))

def download_collection_metadata(collection):
    dataset = collection["dataset"]
    if OFFLINE_TEST:
        return pd.DataFrame(), {
            "dataset": dataset, "collection_id": collection["collection_id"],
            "status": "OFFLINE_TEST_ROUTE_SKIPPED", "metadata_rows": 0,
            "metadata_path": "", "metadata_sha256": "", "route": "", "error": "",
        }
    collection_id = collection["collection_id"]
    raw_dir = ACQ_ROOT / dataset / "00_Official_Metadata"
    raw_dir.mkdir(parents=True, exist_ok=True)
    canonical = raw_dir / f"{dataset}_Official_Collection_Metadata.csv"
    if canonical.exists() and canonical.stat().st_size > 200:
        frame = pd.read_csv(canonical)
        return frame, {
            "dataset": dataset, "collection_id": collection_id,
            "status": "ALREADY_PRESENT", "metadata_rows": len(frame),
            "metadata_path": str(canonical), "metadata_sha256": sha_file(canonical),
            "route": "canonical_drive_copy", "error": "",
        }

    routes = []
    # Direct official HIBA DOI metadata is stable and small.
    if collection_id == 176:
        routes.append("https://isic-archive.s3.amazonaws.com/dois/10.34970-559884/hiba-skin-lesions.csv")
    routes.extend([
        f"https://api.isic-archive.com/collections/{collection_id}/metadata/",
        f"https://api.isic-archive.com/collections/{collection_id}/metadata",
    ])
    errors = []
    for url in routes:
        try:
            response = SESSION.get(url, timeout=HTTP_TIMEOUT, allow_redirects=True)
            response.raise_for_status()
            frame = read_metadata_response(response)
            if len(frame) < 1 or len(frame.columns) < 2:
                raise RuntimeError(f"metadata table unexpectedly small: {frame.shape}")
            frame.to_csv(canonical, index=False)
            return frame, {
                "dataset": dataset, "collection_id": collection_id,
                "status": "DOWNLOADED", "metadata_rows": len(frame),
                "metadata_path": str(canonical), "metadata_sha256": sha_file(canonical),
                "route": url, "error": "",
            }
        except Exception as exc:
            errors.append(f"{url} :: {type(exc).__name__}: {exc}")

    # Official CLI fallback.
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "isic-cli==12.5.2"],
            check=True, timeout=600,
        )
        cli_dir = RUNTIME_ROOT / "isic_cli_metadata" / dataset
        cli_dir.mkdir(parents=True, exist_ok=True)
        before = set(cli_dir.glob("*.csv"))
        subprocess.run(
            ["isic", "metadata", "download", "--collections", str(collection_id)],
            cwd=cli_dir, check=True, timeout=1200,
        )
        candidates = [path for path in cli_dir.glob("*.csv") if path not in before] or list(cli_dir.glob("*.csv"))
        if not candidates:
            raise RuntimeError("isic-cli produced no CSV")
        chosen = max(candidates, key=lambda path: path.stat().st_size)
        frame = pd.read_csv(chosen)
        if len(frame) < 1:
            raise RuntimeError("isic-cli metadata is empty")
        frame.to_csv(canonical, index=False)
        return frame, {
            "dataset": dataset, "collection_id": collection_id,
            "status": "DOWNLOADED_BY_ISIC_CLI", "metadata_rows": len(frame),
            "metadata_path": str(canonical), "metadata_sha256": sha_file(canonical),
            "route": "isic-cli metadata download", "error": "",
        }
    except Exception as exc:
        errors.append(f"isic-cli :: {type(exc).__name__}: {exc}")

    return pd.DataFrame(), {
        "dataset": dataset, "collection_id": collection_id,
        "status": "HOLD_OFFICIAL_METADATA_ROUTE_FAILED", "metadata_rows": 0,
        "metadata_path": str(canonical), "metadata_sha256": "",
        "route": "", "error": " || ".join(errors),
    }

def endpoint_label(text):
    normalized = normalise_text(text)
    # Explicit negative phrases are evaluated before positive tokens.
    no_melanoma = bool(re.search(r"\b(no|not|without|negative for)\s+melanoma\b", normalized))
    positive = bool(
        re.search(r"\bmelanoma\b", normalized)
        or re.search(r"\bmalignant melanoma\b", normalized)
        or re.search(r"\bmel\b", normalized)
    ) and not no_melanoma
    negative = bool(
        re.search(r"\bmelanocytic nevus\b", normalized)
        or re.search(r"\bmelanocytic naevus\b", normalized)
        or re.search(r"\bnevus\b", normalized)
        or re.search(r"\bnaevi?\b", normalized)
        or re.search(r"\bnv\b", normalized)
    )
    # Exclude non-melanocytic entities even when benign/malignant appears.
    disallowed = bool(re.search(
        r"\bbasal cell\b|\bsquamous cell\b|\bbcc\b|\bscc\b|"
        r"\bseborrheic\b|\bdermatofibroma\b|\bvascular\b|"
        r"\bactinic keratosis\b|\bunknown\b|\bindeterminate\b",
        normalized
    ))
    if positive and negative:
        return "HOLD_ENDPOINT_CONFLICT", np.nan
    if positive and not disallowed:
        return "INCLUDE_MELANOMA", 1
    if negative and not disallowed:
        return "INCLUDE_NEVUS", 0
    return "HOLD_NON_ENDPOINT_OR_UNSPECIFIC", np.nan

def adapt_isic_metadata(frame, collection):
    if len(frame) == 0:
        return pd.DataFrame(), {"dataset": collection["dataset"], "status": "HOLD_EMPTY_METADATA"}

    original_columns = list(map(str, frame.columns))
    frame = frame.copy()
    frame.columns = [normalise_column(column) for column in frame.columns]

    image_col = find_column(frame, ["isic_id", "image_id", "name", "image_name"], ("isic_id", "image_id"))
    patient_col = find_column(frame, ["patient_id", "patient"], ("patient",))
    lesion_col = find_column(frame, ["lesion_id", "lesion"], ("lesion",))
    image_type_col = find_column(frame, ["image_type"], ("image_type",))
    diagnosis_cols = [
        column for column in frame.columns
        if any(token in normalise_column(column) for token in [
            "diagnosis", "classification", "pathology", "benign_malignant",
            "melanoma", "nevus", "naevus", "histopath",
        ])
    ]
    if image_col is None or not diagnosis_cols:
        return pd.DataFrame(), {
            "dataset": collection["dataset"],
            "status": "HOLD_REQUIRED_SCHEMA_MISSING",
            "columns": original_columns,
            "image_column": image_col or "",
            "diagnosis_columns": diagnosis_cols,
        }

    image_id = frame[image_col].astype(str).str.replace(r"\.(jpg|jpeg|png)$", "", regex=True, case=False)
    text = frame[diagnosis_cols].fillna("").astype(str).agg(" || ".join, axis=1)
    mapped = text.map(endpoint_label)
    output = pd.DataFrame({
        "dataset": collection["dataset"],
        "provider": collection["provider"],
        "target_role": collection["role"],
        "collection_id": collection["collection_id"],
        "image_id": image_id,
        "diagnosis_evidence": text,
        "endpoint_status": [value[0] for value in mapped],
        "label": [value[1] for value in mapped],
    })
    if patient_col is not None:
        output["patient_id"] = frame[patient_col].fillna("").astype(str)
    else:
        output["patient_id"] = ""
    if lesion_col is not None:
        output["lesion_id"] = frame[lesion_col].fillna("").astype(str)
    else:
        output["lesion_id"] = ""
    if image_type_col is not None:
        output["image_type"] = frame[image_type_col].fillna("").astype(str)
        dermoscopic = output["image_type"].map(normalise_text).str.contains("dermoscop", na=False)
        if dermoscopic.any():
            output.loc[~dermoscopic, "endpoint_status"] = "HOLD_NON_DERMOSCOPIC"
            output.loc[~dermoscopic, "label"] = np.nan
    else:
        output["image_type"] = ""

    grouping_column = ""
    for candidate in collection["group_priority"]:
        if candidate in output.columns:
            values = output[candidate].astype(str)
            coverage = values.ne("").mean() - values.eq("nan").mean()
            valid_count = values[values.ne("") & values.ne("nan")].nunique()
            if coverage >= 0.90 and valid_count >= MIN_TOTAL_GROUPS:
                grouping_column = candidate
                break
    if not grouping_column:
        return output, {
            "dataset": collection["dataset"],
            "status": "HOLD_NO_EXPLICIT_GROUPING_WITH_SUFFICIENT_COVERAGE",
            "image_column": image_col,
            "patient_column": patient_col or "",
            "lesion_column": lesion_col or "",
            "diagnosis_columns": diagnosis_cols,
            "rows": len(output),
        }

    output["grouping_column"] = grouping_column
    output["group_id_raw"] = output[grouping_column].astype(str)
    output.loc[
        output["group_id_raw"].isin(["", "nan", "None", "none"]),
        "endpoint_status"
    ] = "HOLD_GROUP_ID_MISSING"
    output.loc[
        output["group_id_raw"].isin(["", "nan", "None", "none"]),
        "label"
    ] = np.nan

    eligible = output[pd.notna(output["label"])].copy()
    mixed = eligible.groupby("group_id_raw")["label"].nunique()
    mixed_groups = set(mixed[mixed > 1].index)
    output.loc[output["group_id_raw"].isin(mixed_groups), "endpoint_status"] = "HOLD_MIXED_LABEL_GROUP"
    output.loc[output["group_id_raw"].isin(mixed_groups), "label"] = np.nan

    eligible = output[pd.notna(output["label"])].copy()
    eligible["stable"] = [
        stable_key(collection["dataset"], group, image)
        for group, image in zip(eligible["group_id_raw"], eligible["image_id"])
    ]
    eligible = eligible.sort_values("stable").drop_duplicates("group_id_raw", keep="first")

    capped = []
    for label, maximum in [(1, MAX_POSITIVE), (0, MAX_NEGATIVE)]:
        part = eligible[eligible["label"].eq(label)].copy()
        part["selection_stable"] = [
            stable_key(collection["dataset"], label, group, image)
            for group, image in zip(part["group_id_raw"], part["image_id"])
        ]
        capped.append(part.sort_values("selection_stable").head(maximum))
    selected = pd.concat(capped, ignore_index=True) if capped else eligible.iloc[0:0].copy()
    selected["label"] = selected["label"].astype(int)
    selected["group_id"] = (
        collection["dataset"] + "::" + grouping_column.upper() + "::" + selected["group_id_raw"].astype(str)
    )
    selected["source_url"] = "https://isic-archive.s3.amazonaws.com/images/" + selected["image_id"].astype(str) + ".jpg"

    counts = selected.groupby("label")["group_id"].nunique().to_dict()
    score_ready_pre_dedup = bool(
        selected["group_id"].nunique() >= MIN_TOTAL_GROUPS
        and counts.get(1, 0) >= MIN_POSITIVE_GROUPS
        and counts.get(0, 0) >= MIN_NEGATIVE_GROUPS
    )
    audit = {
        "dataset": collection["dataset"],
        "status": "CANDIDATE_ENDPOINT_AND_GROUPING_READY" if score_ready_pre_dedup else "HOLD_INSUFFICIENT_ENDPOINT_GROUPS_PRE_DEDUP",
        "metadata_rows": len(output),
        "endpoint_mapped_rows": int(pd.notna(output["label"]).sum()),
        "selected_groups_pre_dedup": int(selected["group_id"].nunique()),
        "negative_groups_pre_dedup": int(counts.get(0, 0)),
        "positive_groups_pre_dedup": int(counts.get(1, 0)),
        "grouping_column": grouping_column,
        "mixed_label_groups": len(mixed_groups),
        "image_column": image_col,
        "diagnosis_columns": diagnosis_cols,
    }
    return selected, audit

metadata_receipts = []
adapter_audits = []
automatic_candidates = []
for collection in COLLECTIONS:
    metadata, receipt = download_collection_metadata(collection)
    metadata_receipts.append(receipt)
    selected, audit = adapt_isic_metadata(metadata, collection)
    adapter_audits.append(audit)
    if len(selected):
        automatic_candidates.append(selected)

write_csv(P1 / "StageT2-N_Official_Metadata_Receipts_v0.1.csv", pd.DataFrame(metadata_receipts))
write_json(P1 / "StageT2-N_ISIC_Metadata_Adapter_Audits_v0.1.json", adapter_audits)

# Optional PH2 official archive adapter.
def extract_archive(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    suffix = source.suffix.lower()
    if suffix == ".zip":
        base = destination.resolve()
        with zipfile.ZipFile(source) as archive:
            for member in archive.infolist():
                target = (destination / member.filename).resolve()
                if not (target == base or str(target).startswith(str(base) + os.sep)):
                    raise RuntimeError(f"Unsafe archive member: {member.filename}")
            archive.extractall(destination)
    elif suffix in {".rar", ".7z"}:
        subprocess.run(["7z", "x", "-y", str(source), f"-o{destination}"], check=True, timeout=1800)
    else:
        raise RuntimeError(f"Unsupported PH2 archive: {source.name}")

def adapt_ph2():
    archives = [
        path for path in ph2_inbox.iterdir()
        if path.is_file() and path.suffix.lower() in {".zip", ".rar", ".7z"}
    ]
    if not archives:
        return pd.DataFrame(), {
            "dataset": "PH2", "status": "HOLD_OFFICIAL_DOWNLOAD_LINK_DEAD",
            "drop_folder": str(ph2_inbox),
        }
    if len(archives) > 1:
        return pd.DataFrame(), {
            "dataset": "PH2", "status": "HOLD_MULTIPLE_ARCHIVES_AMBIGUOUS",
            "archives": [path.name for path in archives],
        }
    archive = archives[0]
    extracted = RUNTIME_ROOT / "PH2_extracted"
    extract_archive(archive, extracted)

    images = [
        path for path in extracted.rglob("*")
        if path.is_file() and path.suffix.lower() in {".bmp", ".jpg", ".jpeg", ".png"}
    ]
    image_rows = []
    for path in images:
        match = re.search(r"\b(IMD\d+)\b", path.name, re.I)
        if match:
            image_rows.append({"image_id": match.group(1).upper(), "image_path": str(path)})
    image_frame = pd.DataFrame(image_rows).drop_duplicates("image_id") if image_rows else pd.DataFrame()

    tables = [
        path for path in extracted.rglob("*")
        if path.is_file() and path.suffix.lower() in {".xlsx", ".xls", ".csv"}
    ]
    label_rows = []
    for table in tables:
        try:
            if table.suffix.lower() == ".csv":
                raw = pd.read_csv(table, header=None)
            else:
                raw = pd.read_excel(table, header=None)
        except Exception:
            continue

        # Official PH2 spreadsheets commonly use a multi-row header followed by
        # X marks under Common Nevus, Atypical Nevus and Melanoma.
        header_index = None
        header_values = None
        for row_index in range(min(30, len(raw))):
            values = [normalise_text(value) for value in raw.iloc[row_index].tolist()]
            joined = " || ".join(values)
            if ("image" in joined or "name" in joined) and "melanoma" in joined:
                header_index = row_index
                header_values = values
                break
        if header_index is not None:
            image_columns = [
                index for index, value in enumerate(header_values)
                if "image" in value or "name" in value
            ]
            melanoma_columns = [
                index for index, value in enumerate(header_values)
                if "melanoma" in value
            ]
            nevus_columns = [
                index for index, value in enumerate(header_values)
                if "nev" in value or "naev" in value
            ]
            for row_index in range(header_index + 1, len(raw)):
                values = raw.iloc[row_index].tolist()
                text = " || ".join("" if pd.isna(value) else str(value) for value in values)
                match = re.search(r"\b(IMD\d+)\b", text, re.I)
                if not match:
                    continue
                positive_mark = any(
                    index < len(values)
                    and normalise_text(values[index]) not in {"", "0", "nan", "no"}
                    for index in melanoma_columns
                )
                negative_mark = any(
                    index < len(values)
                    and normalise_text(values[index]) not in {"", "0", "nan", "no"}
                    for index in nevus_columns
                )
                if positive_mark and not negative_mark:
                    status, label = "INCLUDE_MELANOMA", 1
                elif negative_mark and not positive_mark:
                    status, label = "INCLUDE_NEVUS", 0
                else:
                    continue
                label_rows.append({
                    "image_id": match.group(1).upper(),
                    "endpoint_status": status,
                    "label": label,
                    "diagnosis_evidence": text,
                })
            continue

        # Fallback for row-wise textual diagnosis files.
        for row in raw.itertuples(index=False, name=None):
            text = " || ".join("" if pd.isna(value) else str(value) for value in row)
            match = re.search(r"\b(IMD\d+)\b", text, re.I)
            if not match:
                continue
            normalized = normalise_text(text)
            if "melanoma" in normalized:
                status, label = "INCLUDE_MELANOMA", 1
            elif (
                "common nev" in normalized or "atypical nev" in normalized
                or "nevus" in normalized or "naevus" in normalized
            ):
                status, label = "INCLUDE_NEVUS", 0
            else:
                continue
            label_rows.append({
                "image_id": match.group(1).upper(),
                "endpoint_status": status,
                "label": label,
                "diagnosis_evidence": text,
            })
    labels = pd.DataFrame(label_rows).drop_duplicates("image_id") if label_rows else pd.DataFrame()
    if len(image_frame) == 0 or len(labels) == 0:
        return pd.DataFrame(), {
            "dataset": "PH2", "status": "HOLD_OFFICIAL_SCHEMA_NOT_ADAPTED",
            "images_found": len(image_frame), "labels_found": len(labels),
            "archive_sha256": sha_file(archive),
        }
    selected = image_frame.merge(labels, on="image_id", validate="one_to_one")
    selected["dataset"] = "PH2"
    selected["provider"] = "Hospital Pedro Hispano"
    selected["target_role"] = "MANUAL_PRIMARY_PROVIDER_TARGET"
    selected["collection_id"] = ""
    selected["grouping_column"] = "lesion_id"
    selected["group_id_raw"] = selected["image_id"]
    selected["group_id"] = "PH2::LESION_ID::" + selected["image_id"]
    selected["source_url"] = ""
    selected["patient_id"] = ""
    selected["lesion_id"] = selected["image_id"]
    selected["image_type"] = "dermoscopic"
    counts = selected.groupby("label")["group_id"].nunique().to_dict()
    ready = bool(
        selected["group_id"].nunique() >= MIN_TOTAL_GROUPS
        and counts.get(1, 0) >= MIN_POSITIVE_GROUPS
        and counts.get(0, 0) >= MIN_NEGATIVE_GROUPS
    )
    return selected, {
        "dataset": "PH2",
        "status": "CANDIDATE_ENDPOINT_AND_GROUPING_READY" if ready else "HOLD_INSUFFICIENT_ENDPOINT_GROUPS_PRE_DEDUP",
        "selected_groups_pre_dedup": selected["group_id"].nunique(),
        "negative_groups_pre_dedup": counts.get(0, 0),
        "positive_groups_pre_dedup": counts.get(1, 0),
        "archive_sha256": sha_file(archive),
    }

ph2_candidates, ph2_audit = adapt_ph2()
adapter_audits.append(ph2_audit)
if len(ph2_candidates):
    automatic_candidates.append(ph2_candidates)
write_json(P1 / "StageT2-N_All_Target_Adapter_Audits_v0.1.json", adapter_audits)
official_copy_root = P1 / "Official_Metadata_Copies"
official_copy_root.mkdir(parents=True, exist_ok=True)
for receipt in metadata_receipts:
    source = Path(str(receipt.get("metadata_path", "")))
    if source.is_file():
        shutil.copy2(source, official_copy_root / source.name)

candidate = pd.concat(automatic_candidates, ignore_index=True, sort=False) if automatic_candidates else pd.DataFrame(
    columns=[
        "dataset", "provider", "target_role", "collection_id", "image_id",
        "diagnosis_evidence", "endpoint_status", "label", "patient_id",
        "lesion_id", "image_type", "grouping_column", "group_id_raw",
        "group_id", "source_url", "image_path",
    ]
)

# Existing source/target image identifiers and fingerprints.
existing_ids = set()
existing_group_ids = set()
for path in [HAM_MANIFEST, MSK_MANIFEST, UDA_MANIFEST, MILK_MANIFEST, T2L_MANIFEST]:
    frame = pd.read_csv(path)
    for column in frame.columns:
        normalized = normalise_column(column)
        if normalized in {"image_id", "isic_id", "reference_image_id"} or normalized.endswith("_image_id"):
            existing_ids.update(frame[column].dropna().astype(str).str.replace(r"\.(jpg|jpeg|png)$", "", regex=True, case=False))
        if normalized in {"group_id", "lesion_id", "patient_id"}:
            existing_group_ids.update(frame[column].dropna().astype(str))

reference_frames = []
if REFERENCE_CACHE.exists():
    reference_frames.append(pd.read_csv(REFERENCE_CACHE))
for path in [MILK_MANIFEST, T2L_MANIFEST]:
    frame = pd.read_csv(path)
    if "pixel_sha256" in frame.columns or "phash64" in frame.columns:
        reference_frames.append(frame)
reference = pd.concat(reference_frames, ignore_index=True, sort=False) if reference_frames else pd.DataFrame()
reference_pixels = set(reference.get("pixel_sha256", pd.Series(dtype=str)).dropna().astype(str))
reference_phashes = [str(value) for value in reference.get("phash64", pd.Series(dtype=str)).dropna()]

candidate["adjudication_status"] = "PENDING_DOWNLOAD"
candidate.loc[candidate["image_id"].astype(str).isin(existing_ids), "adjudication_status"] = "EXCLUDE_EXISTING_IMAGE_ID"
candidate.loc[candidate["group_id"].astype(str).isin(existing_group_ids), "adjudication_status"] = "EXCLUDE_EXISTING_GROUP_ID"

def download_candidate(record):
    dataset = record["dataset"]
    image_id = record["image_id"]
    destination = RUNTIME_ROOT / "selected_images" / dataset / f"{image_id}.jpg"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if record.get("image_path") and Path(str(record["image_path"])).exists():
        shutil.copy2(str(record["image_path"]), destination)
        return record["row_index"], "COPIED_FROM_OFFICIAL_ARCHIVE", str(destination), destination.stat().st_size, ""
    for attempt in range(3):
        try:
            response = SESSION.get(record["source_url"], timeout=HTTP_TIMEOUT)
            response.raise_for_status()
            data = response.content
            content_type = response.headers.get("content-type", "").lower()
            if len(data) < 1024 or "text/html" in content_type:
                raise RuntimeError("invalid image response")
            destination.write_bytes(data)
            return record["row_index"], "DOWNLOADED", str(destination), len(data), ""
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            time.sleep(1.2 * (attempt + 1))
    return record["row_index"], "FAILED", "", 0, error

pending = candidate[candidate["adjudication_status"].eq("PENDING_DOWNLOAD")].reset_index().rename(columns={"index": "row_index"})
download_rows = []
with ThreadPoolExecutor(max_workers=8) as executor:
    futures = [executor.submit(download_candidate, row._asdict()) for row in pending.itertuples(index=False)]
    for count, future in enumerate(as_completed(futures), 1):
        row_index, status, image_path, byte_count, error = future.result()
        download_rows.append({
            "row_index": row_index, "download_status": status,
            "image_path": image_path, "download_bytes": byte_count, "download_error": error,
        })
        if count % 100 == 0:
            print("Provider selected images processed:", count, "/", len(pending))
downloads = pd.DataFrame(download_rows).set_index("row_index") if download_rows else pd.DataFrame()
for column in ["download_status", "image_path", "download_bytes", "download_error"]:
    if column not in candidate.columns:
        candidate[column] = ""
    if len(downloads):
        candidate.loc[downloads.index, column] = downloads[column]
candidate["download_status"] = candidate["download_status"].fillna("")
candidate.loc[
    candidate["adjudication_status"].eq("PENDING_DOWNLOAD")
    & ~candidate["download_status"].isin(["DOWNLOADED", "COPIED_FROM_OFFICIAL_ARCHIVE"]),
    "adjudication_status"
] = "HOLD_DOWNLOAD_FAILED"

def fingerprint_image(path):
    data = Path(path).read_bytes()
    with Image.open(io.BytesIO(data)) as image0:
        image = ImageOps.exif_transpose(image0).convert("RGB")
        width, height = image.size
        rgb = np.asarray(image, dtype=np.uint8)
        header = json.dumps(
            {"width": width, "height": height, "mode": "RGB"},
            sort_keys=True, separators=(",", ":")
        ).encode() + b"\0"
        pixel_sha = sha_bytes(header + rgb.tobytes(order="C"))
        gray = np.asarray(image.convert("L").resize((32, 32), Image.Resampling.LANCZOS), dtype=np.float32)
        low = dctn(gray, type=2, norm="ortho")[:8, :8]
        threshold = float(np.median(low.flatten()[1:]))
        bits = (low.flatten() > threshold).astype(np.uint8)
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

fingerprint_rows = []
for index, row in candidate[
    candidate["adjudication_status"].eq("PENDING_DOWNLOAD")
    & candidate["download_status"].isin(["DOWNLOADED", "COPIED_FROM_OFFICIAL_ARCHIVE"])
].iterrows():
    try:
        fingerprint_rows.append({"row_index": index, **fingerprint_image(row["image_path"]), "fingerprint_error": ""})
    except Exception as exc:
        fingerprint_rows.append({"row_index": index, "fingerprint_error": f"{type(exc).__name__}: {exc}"})
fingerprints = pd.DataFrame(fingerprint_rows).set_index("row_index") if fingerprint_rows else pd.DataFrame()
for column in ["raw_image_sha256", "pixel_sha256", "pixel_width", "pixel_height", "phash64", "fingerprint_error"]:
    if column not in candidate.columns:
        candidate[column] = np.nan if column in {"pixel_width", "pixel_height"} else ""
    if len(fingerprints) and column in fingerprints.columns:
        candidate.loc[fingerprints.index, column] = fingerprints[column]
candidate.loc[
    candidate["adjudication_status"].eq("PENDING_DOWNLOAD")
    & candidate["pixel_sha256"].fillna("").astype(str).eq(""),
    "adjudication_status"
] = "HOLD_FINGERPRINT_FAILED"
candidate.loc[
    candidate["adjudication_status"].eq("PENDING_DOWNLOAD")
    & candidate["pixel_sha256"].astype(str).isin(reference_pixels),
    "adjudication_status"
] = "EXCLUDE_CROSS_ROSTER_EXACT_PIXEL_DUPLICATE"

def phash_distance(left, right):
    return (int(str(left), 16) ^ int(str(right), 16)).bit_count()

priority = ["HIBA_ISIC_176", "SYDNEY_ACQUIRED_215", "BCN20000_ISIC_249", "MELSELF_ISIC_485", "PH2"]
accepted_pixels = set(reference_pixels)
accepted_phashes = list(reference_phashes)
for dataset in priority:
    indices = candidate.index[
        candidate["dataset"].eq(dataset)
        & candidate["adjudication_status"].eq("PENDING_DOWNLOAD")
    ].tolist()
    for index in indices:
        row = candidate.loc[index]
        pixel = str(row["pixel_sha256"])
        phash = str(row["phash64"])
        if pixel in accepted_pixels:
            status = "EXCLUDE_CROSS_TARGET_EXACT_PIXEL_DUPLICATE"
        else:
            distance = min((phash_distance(phash, value) for value in accepted_phashes), default=65)
            status = "HOLD_CROSS_ROSTER_PHASH_NEAR_COPY" if distance <= PHASH_MAX_DISTANCE else "KEEP_UNIQUE"
        candidate.loc[index, "adjudication_status"] = status
        if status == "KEEP_UNIQUE":
            accepted_pixels.add(pixel)
            accepted_phashes.append(phash)

write_csv(P2 / "StageT2-N_All_Candidate_Image_Adjudication_v0.1.csv", candidate)

# Freeze target roster, split and canonical selected-image bundle.
roster_frames = []
readiness_rows = []
for dataset, frame in candidate.groupby("dataset"):
    retained = frame[frame["adjudication_status"].eq("KEEP_UNIQUE")].copy()
    counts = retained.groupby("label")["group_id"].nunique().to_dict()
    ready = bool(
        retained["group_id"].nunique() >= MIN_TOTAL_GROUPS
        and counts.get(1, 0) >= MIN_POSITIVE_GROUPS
        and counts.get(0, 0) >= MIN_NEGATIVE_GROUPS
    )
    readiness_rows.append({
        "dataset": dataset,
        "provider": frame["provider"].iloc[0],
        "target_role": frame["target_role"].iloc[0],
        "candidate_rows": len(frame),
        "retained_images": len(retained),
        "retained_groups": retained["group_id"].nunique(),
        "negative_groups": counts.get(0, 0),
        "positive_groups": counts.get(1, 0),
        "score_ready": ready,
        "reason": "" if ready else "minimum_group_or_class_gate_not_met_after_dedup",
    })
    if not ready:
        continue

    groups = retained[["group_id", "label"]].drop_duplicates()
    development, validation = train_test_split(
        groups, test_size=0.2, random_state=SEED, stratify=groups["label"]
    )
    partition = {
        **{group: "development" for group in development["group_id"]},
        **{group: "validation" for group in validation["group_id"]},
    }
    retained["partition"] = retained["group_id"].map(partition)
    retained["unit_id"] = retained["dataset"] + "::IMAGE::" + retained["image_id"].astype(str)
    retained["source_locator"] = retained["image_path"]
    retained["modality"] = "dermoscopy"
    retained["task"] = "melanoma_vs_melanocytic_nevus"

    # Storage-economical canonical record: retain the governed manifest, hashes,
    # embeddings and source scores, but not duplicate public image bytes in Drive.
    manifest_path = P2 / f"{dataset}_Selected_Manifest_v0.1.csv"
    bundle_manifest = retained[[
        "dataset", "provider", "target_role", "image_id", "unit_id", "group_id",
        "label", "partition", "source_url", "raw_image_sha256", "pixel_sha256", "phash64"
    ]].copy()
    write_csv(manifest_path, bundle_manifest)
    retained["canonical_bundle"] = ""
    retained["bundle_member"] = ""
    roster_frames.append(retained[[
        "dataset", "provider", "target_role", "modality", "task", "image_id",
        "unit_id", "group_id", "label", "partition", "source_locator",
        "raw_image_sha256", "pixel_sha256", "phash64", "canonical_bundle", "bundle_member"
    ]])

readiness = pd.DataFrame(readiness_rows, columns=[
    "dataset", "provider", "target_role", "candidate_rows", "retained_images",
    "retained_groups", "negative_groups", "positive_groups", "score_ready", "reason"
])
target_roster = pd.concat(roster_frames, ignore_index=True) if roster_frames else pd.DataFrame(
    columns=[
        "dataset", "provider", "target_role", "modality", "task", "image_id",
        "unit_id", "group_id", "label", "partition", "source_locator",
        "raw_image_sha256", "pixel_sha256", "phash64", "canonical_bundle", "bundle_member"
    ]
)
write_csv(P2 / "StageT2-N_Target_Readiness_Map_v0.1.csv", readiness)
write_csv(P2 / "StageT2-N_Frozen_Score_Ready_Target_Roster_v0.1.csv", target_roster)

display(readiness)
print("Score-ready provider targets:", sorted(target_roster["dataset"].unique()) if len(target_roster) else [])



# Frozen CPU representation and source-axis scoring for admitted provider targets
SCORING_ENABLED = bool(len(target_roster) > 0)
source_scores = pd.DataFrame(columns=[
    "target", "provider", "target_role", "modality", "source", "edge_id",
    "image_id", "unit_id", "group_id", "label", "partition", "logit",
    "probability", "source_validation_auc"
])
truth_table = pd.DataFrame(columns=[
    "target", "provider", "target_role", "modality", "source", "edge_id",
    "true_auc", "source_validation_auc", "units", "groups"
])
embedding_manifest = pd.DataFrame(columns=[
    "target", "images", "dimension", "model_state_sha256", "embedding_sha256",
    "image_ids_sha256", "maximum_l2_norm_error", "device"
])
axis_schema_audit = pd.DataFrame(columns=[
    "source", "axis_filename", "axis_sha256", "identity_key",
    "coefficient_key", "intercept_key", "schema"
])

if SCORING_ENABLED:
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
            assert sha_bytes(data) == str(row["raw_image_sha256"])
            with Image.open(io.BytesIO(data)) as image0:
                image = ImageOps.exif_transpose(image0).convert("RGB")
                tensor = TRANSFORM(image)
            return tensor, index

    DERM_SOURCES = ["HAM10000", "ISIC_MSK1", "ISIC_UDA1"]
    SOURCE_BY_MODALITY = {"dermoscopy": DERM_SOURCES}
    derm_summary = pd.read_csv(DERM_SUMMARY).set_index("source")
    SOURCE_VALIDATION_AUC = {
        source: float(derm_summary.loc[source, "validation_auc"])
        for source in DERM_SOURCES
    }

    embedding_rows, score_rows, axis_rows = [], [], []
    for dataset, frame in target_roster.groupby("dataset", sort=True):
        frame = frame.sort_values("image_id").reset_index(drop=True)
        embedding_path = P3 / f"{dataset}_Frozen_ResNet50_V2_Embeddings_v0.1.npy"
        ids_path = P3 / f"{dataset}_Embedding_Image_IDs_v0.1.npy"
        expected_ids = np.asarray(frame["image_id"].astype(str).tolist(), dtype=np.str_)

        if embedding_path.exists() and ids_path.exists():
            assert np.array_equal(np.load(ids_path, allow_pickle=False).astype(str), expected_ids)
            embeddings = np.load(embedding_path, mmap_mode="r", allow_pickle=False)
        else:
            loader = DataLoader(
                TargetImageDataset(frame), batch_size=24, shuffle=False,
                num_workers=2, pin_memory=False
            )
            chunks = []
            for images, indices in tqdm(loader, desc=f"Embedding {dataset}"):
                with torch.inference_mode():
                    features_tensor = F.normalize(MODEL(images.to(DEVICE)), p=2, dim=1)
                chunks.append(features_tensor.cpu().numpy().astype(np.float32))
            array = np.concatenate(chunks, axis=0)
            assert array.shape == (len(frame), 2048)
            np.save(embedding_path, array, allow_pickle=False)
            np.save(ids_path, expected_ids, allow_pickle=False)
            embeddings = np.load(embedding_path, mmap_mode="r", allow_pickle=False)

        norms = np.linalg.norm(np.asarray(embeddings), axis=1)
        assert np.max(np.abs(norms - 1.0)) < 2e-5

        for source in DERM_SOURCES:
            axis_path = AXIS_PATHS[source]
            with np.load(axis_path, allow_pickle=False) as axis:
                keys = set(axis.files)
                identity_key = "dataset_id" if "dataset_id" in keys else "source"
                assert str(axis[identity_key]) == source
                if {"coefficient_raw", "intercept_raw"}.issubset(keys):
                    coefficient_key, intercept_key = "coefficient_raw", "intercept_raw"
                    schema = "STAGE11_STYLE"
                elif {"raw_coefficient", "raw_intercept"}.issubset(keys):
                    coefficient_key, intercept_key = "raw_coefficient", "raw_intercept"
                    schema = "STAGE8_STYLE"
                else:
                    raise KeyError(f"No documented parameter pair in {axis_path.name}: {sorted(keys)}")
                coefficient = np.asarray(axis[coefficient_key], dtype=np.float64)
                intercept = float(axis[intercept_key])
                assert coefficient.shape == (2048,)
                assert np.isfinite(coefficient).all() and np.isfinite(intercept)
                if "model_state_sha256" in keys:
                    assert str(axis["model_state_sha256"]) == MODEL_STATE_SHA256

            axis_rows.append({
                "source": source, "axis_filename": axis_path.name,
                "axis_sha256": sha_file(axis_path), "identity_key": identity_key,
                "coefficient_key": coefficient_key, "intercept_key": intercept_key,
                "schema": schema,
            })
            logits = np.asarray(embeddings, dtype=np.float64) @ coefficient + intercept
            for row, logit in zip(frame.itertuples(), logits):
                score_rows.append({
                    "target": dataset, "provider": row.provider,
                    "target_role": row.target_role, "modality": "dermoscopy",
                    "source": source, "edge_id": f"{source}__TO__{dataset}",
                    "image_id": row.image_id, "unit_id": row.unit_id,
                    "group_id": row.group_id, "label": int(row.label),
                    "partition": row.partition, "logit": float(logit),
                    "probability": float(1 / (1 + np.exp(-np.clip(logit, -60, 60)))),
                    "source_validation_auc": SOURCE_VALIDATION_AUC[source],
                })

        embedding_rows.append({
            "target": dataset, "images": len(frame), "dimension": 2048,
            "model_state_sha256": MODEL_STATE_SHA256,
            "embedding_sha256": sha_file(embedding_path),
            "image_ids_sha256": sha_file(ids_path),
            "maximum_l2_norm_error": float(np.max(np.abs(norms - 1.0))),
            "device": "cpu",
        })
        gc.collect()

    source_scores = pd.DataFrame(score_rows)
    embedding_manifest = pd.DataFrame(embedding_rows)
    axis_schema_audit = pd.DataFrame(axis_rows).drop_duplicates()

    truth_rows = []
    for (target, provider, role, source, edge_id), frame in source_scores.groupby(
        ["target", "provider", "target_role", "source", "edge_id"]
    ):
        truth_rows.append({
            "target": target, "provider": provider, "target_role": role,
            "modality": "dermoscopy", "source": source, "edge_id": edge_id,
            "true_auc": float(roc_auc_score(frame["label"], frame["logit"])),
            "source_validation_auc": float(frame["source_validation_auc"].iloc[0]),
            "units": frame["unit_id"].nunique(),
            "groups": frame["group_id"].nunique(),
        })
    truth_table = pd.DataFrame(truth_rows)

write_csv(P3 / "StageT2-N_Frozen_Embedding_Manifest_v0.1.csv", embedding_manifest)
write_csv(P3 / "StageT2-N_Frozen_Axis_Schema_Audit_v0.1.csv", axis_schema_audit)
write_csv(P3 / "StageT2-N_Frozen_Source_Score_Predictions_v0.1.csv", source_scores)
write_csv(P3 / "StageT2-N_Provider_Edge_Truth_Table_v0.1.csv", truth_table)

if SCORING_ENABLED:
    display(embedding_manifest)
    display(truth_table)
else:
    print("No target passed acquisition/grouping/dedup gates; scoring branch skipped.")


# Inherited frozen AMW/RA-CB method family, split into prospective budget-8 and later-budget phases

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


def run_extension_budgets(budgets, phase_label):
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
    
        for budget in budgets:
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
    
    results = pd.DataFrame(rows)
    if len(results):
        results["absolute_error"] = (results["estimate_auc"] - results["true_auc"]).abs()
        role_map = target_roster[["dataset", "target_role"]].drop_duplicates().set_index("dataset")["target_role"].to_dict()
        provider_map = target_roster[["dataset", "provider"]].drop_duplicates().set_index("dataset")["provider"].to_dict()
        results["target_role"] = results["target"].map(role_map)
        results["provider"] = results["target"].map(provider_map)
        results["phase"] = phase_label
    diagnostics = pd.DataFrame(diagnostic_rows)
    skips = pd.DataFrame(skip_rows)
    return results, diagnostics, skips

budget8_results = pd.DataFrame()
budget8_diagnostics = pd.DataFrame()
budget8_skips = pd.DataFrame()
if SCORING_ENABLED:
    budget8_results, budget8_diagnostics, budget8_skips = run_extension_budgets([8], "PROSPECTIVE_BUDGET8")

write_csv(P4 / "StageT2-N_Budget8_Prospective_Replicates_v0.1.csv", budget8_results)
write_csv(P4 / "StageT2-N_Budget8_RA_CB_Diagnostics_v0.1.csv", budget8_diagnostics)
write_csv(P4 / "StageT2-N_Budget8_Skips_v0.1.csv", budget8_skips)
print("Budget-8 result rows:", len(budget8_results))



# Freeze Stage T2-M prospective distributions and support status before higher-budget truth.
prospective_forecasts = pd.DataFrame()
forecast_record = {
    "stage": "StageT2-N",
    "event": "PROVIDER_TARGET_FORECASTS_SEALED_BEFORE_HIGHER_BUDGET_TRUTH",
    "parent_t2m_record": EXPECTED_PARENT["t2m"],
    "model_freeze_sha256": model_freeze["model_freeze_sha256"],
    "support_freeze_sha256": support_freeze["support_freeze_sha256"],
    "full_provider_budget_truth_observed": False,
    "single_pilot_deployment_authorised": False,
    "locked_blind_assets_touched": False,
    "stage12_authorised": False,
}

if SCORING_ENABLED:
    pivot = budget8_results[
        budget8_results["method"].isin(LEGAL_METHODS)
    ].pivot_table(
        index=["target", "provider", "target_role", "modality", "replicate", "edge_id"],
        columns="method", values="estimate_auc"
    ).reset_index()
    for method in LEGAL_METHODS:
        if method not in pivot.columns:
            pivot[method] = np.nan
    pivot["cross_method_sd"] = pivot[LEGAL_METHODS].std(axis=1)
    replicate_signature = (
        pivot.groupby(["target", "provider", "target_role", "modality", "replicate"], as_index=False)
        .agg(pilot_disagreement=("cross_method_sd", "mean"))
    )
    target_signature = (
        replicate_signature.groupby(["target", "provider", "target_role", "modality"], as_index=False)
        .agg(
            pilot_disagreement_index=("pilot_disagreement", "median"),
            pilot_disagreement_iqr=("pilot_disagreement", lambda x: float(np.quantile(x, .75) - np.quantile(x, .25))),
            usable_budget8_replicates=("replicate", "nunique"),
        )
    )
    group_counts = target_roster.groupby("dataset")["group_id"].nunique().to_dict()
    target_signature["independent_groups"] = target_signature["target"].map(group_counts).astype(int)
    target_signature["log2_groups"] = np.log2(target_signature["independent_groups"].astype(float))
    assert (target_signature["usable_budget8_replicates"] >= 50).all()

    selected_features = list(model_freeze["selected_features"])
    raw_intercept = float(model_freeze["raw_intercept"])
    raw_coefficients = np.asarray(model_freeze["raw_coefficients"], float)
    sigma = float(model_freeze["sigma"])
    assert selected_features == ["pilot_disagreement_index"]
    mu = (
        raw_intercept
        + target_signature[selected_features].to_numpy(float) @ raw_coefficients
    )
    target_signature["mu_log2_budget"] = mu
    target_signature["sigma"] = sigma

    boundaries = np.array([-np.inf, 3.0, 4.0, 5.0, 6.0, 7.0, np.inf])
    probability_names = [
        "probability_le_8", "probability_8_to_16", "probability_16_to_32",
        "probability_32_to_64", "probability_64_to_128", "probability_gt_128",
    ]
    for category, name in enumerate(probability_names):
        lower = boundaries[category]
        upper = boundaries[category + 1]
        lower_cdf = np.zeros(len(mu)) if np.isneginf(lower) else norm.cdf((lower - mu) / sigma)
        upper_cdf = np.ones(len(mu)) if np.isposinf(upper) else norm.cdf((upper - mu) / sigma)
        target_signature[name] = upper_cdf - lower_cdf

    target_signature["parametric_interval80_lower"] = mu + norm.ppf(.10) * sigma
    target_signature["parametric_interval80_upper"] = mu + norm.ppf(.90) * sigma
    target_signature["parametric_interval95_lower"] = mu + norm.ppf(.025) * sigma
    target_signature["parametric_interval95_upper"] = mu + norm.ppf(.975) * sigma

    # Frozen support rule.
    support_features = list(support_freeze["support_features"])
    center = np.asarray(support_freeze["robust_center"], float)
    scale = np.asarray(support_freeze["robust_scale"], float)
    training_features = features.copy()
    training_scaled = (
        training_features[support_features].to_numpy(float) - center
    ) / scale
    target_scaled = (
        target_signature[support_features].to_numpy(float) - center
    ) / scale
    support_distance = np.asarray([
        np.sqrt(((training_scaled - row) ** 2).sum(axis=1)).min()
        for row in target_scaled
    ])
    target_signature["support_distance"] = support_distance
    target_signature["distance_threshold"] = float(
        support_freeze["nearest_neighbour_distance_threshold"]
    )
    target_signature["disagreement_lower_envelope"] = float(
        support_freeze["disagreement_lower_envelope"]
    )
    target_signature["disagreement_upper_envelope"] = float(
        support_freeze["disagreement_upper_envelope"]
    )
    outside_envelope = (
        target_signature["pilot_disagreement_index"]
        < target_signature["disagreement_lower_envelope"]
    ) | (
        target_signature["pilot_disagreement_index"]
        > target_signature["disagreement_upper_envelope"]
    )
    outside_distance = (
        target_signature["support_distance"]
        > target_signature["distance_threshold"]
    )
    target_signature["outside_disagreement_envelope"] = outside_envelope
    target_signature["outside_distance_support"] = outside_distance
    target_signature["support_status"] = np.where(
        outside_envelope | outside_distance,
        "OUT_OF_SUPPORT_ABSTAIN",
        "SUPPORTED",
    )
    target_signature["actionable_budget_recommendation"] = False

    # Frozen family-bootstrap model uncertainty.
    bootstrap = globals()["bootstrap"].copy()
    bootstrap = bootstrap[bootstrap["converged"].astype(str).str.lower().isin(["true", "1"])].copy()
    assert len(bootstrap) >= 950
    for index, row in target_signature.iterrows():
        bootstrap_mu = bootstrap["raw_intercept"].to_numpy(float).copy()
        for feature in selected_features:
            bootstrap_mu += (
                bootstrap[f"raw_beta__{feature}"].to_numpy(float)
                * float(row[feature])
            )
        target_signature.loc[index, "bootstrap_mu_q05"] = float(np.quantile(bootstrap_mu, .05))
        target_signature.loc[index, "bootstrap_mu_q50"] = float(np.quantile(bootstrap_mu, .50))
        target_signature.loc[index, "bootstrap_mu_q95"] = float(np.quantile(bootstrap_mu, .95))

    prospective_forecasts = target_signature
    write_csv(P4 / "StageT2-N_Prospective_Provider_Forecasts_v0.1.csv", prospective_forecasts)

forecast_record["score_ready_targets"] = (
    sorted(prospective_forecasts["target"].tolist()) if len(prospective_forecasts) else []
)
forecast_record["forecast_count"] = int(len(prospective_forecasts))
forecast_record["forecast_table_sha256"] = (
    sha_file(P4 / "StageT2-N_Prospective_Provider_Forecasts_v0.1.csv")
    if len(prospective_forecasts) else ""
)
forecast_record["sealed_utc"] = now()
forecast_record["prospective_forecast_record_sha256"] = sha_json(forecast_record)

forecast_record_path = P4 / "StageT2-N_Prospective_Forecast_Seal_v0.1.json"
if forecast_record_path.exists():
    existing = verify_self(
        forecast_record_path, "prospective_forecast_record_sha256"
    )
    for key, value in forecast_record.items():
        if key != "sealed_utc":
            assert existing[key] == value, f"Forecast replay mismatch: {key}"
    forecast_record = existing
else:
    write_json(forecast_record_path, forecast_record)

display(prospective_forecasts)
print("Prospective forecasts sealed before budgets 16-128:", forecast_record["prospective_forecast_record_sha256"])
print("Full provider-budget truth observed at seal:", False)



# Execute the unchanged higher-budget ladder only after prospective forecast seal.
higher_results = pd.DataFrame()
higher_diagnostics = pd.DataFrame()
higher_skips = pd.DataFrame()
if SCORING_ENABLED:
    assert forecast_record["full_provider_budget_truth_observed"] is False
    assert forecast_record_path.exists()
    higher_results, higher_diagnostics, higher_skips = run_extension_budgets(
        [16, 32, 64, 128], "POST_FORECAST_HIGHER_BUDGETS"
    )

all_results = pd.concat([budget8_results, higher_results], ignore_index=True, sort=False)
all_diagnostics = pd.concat([budget8_diagnostics, higher_diagnostics], ignore_index=True, sort=False)
all_skips = pd.concat([budget8_skips, higher_skips], ignore_index=True, sort=False)

write_csv(P5 / "StageT2-N_All_Provider_MultiBudget_Replicates_v0.1.csv", all_results)
write_csv(P5 / "StageT2-N_All_RA_CB_Selector_And_Balance_Diagnostics_v0.1.csv", all_diagnostics)
write_csv(P5 / "StageT2-N_All_Skipped_Replicates_v0.1.csv", all_skips)

print("Full multi-budget result rows:", len(all_results))
print("Skipped rows:", len(all_skips))



# Prospective interval evaluation, regime assignment, gates and final seal.
observed_intervals = pd.DataFrame()
regime_table = pd.DataFrame()
prospective_evaluation = pd.DataFrame()
ra32_summary = pd.DataFrame()

def predictive_interval_nll(lower, upper, mu, sigma):
    if np.isneginf(lower):
        probability = norm.cdf((upper - mu) / sigma)
    elif np.isposinf(upper):
        probability = norm.sf((lower - mu) / sigma)
    else:
        probability = norm.cdf((upper - mu) / sigma) - norm.cdf((lower - mu) / sigma)
    return float(-np.log(max(float(probability), 1e-12))), float(probability)

def interval_order_concordance(frame):
    comparable = 0
    concordant = 0
    tied = 0
    data = frame.reset_index(drop=True)
    for left_index, right_index in itertools.combinations(range(len(data)), 2):
        left = data.iloc[left_index]
        right = data.iloc[right_index]
        ordering = None
        if np.isfinite(left["upper"]) and np.isfinite(right["lower"]) and left["upper"] <= right["lower"]:
            ordering = -1
        elif np.isfinite(right["upper"]) and np.isfinite(left["lower"]) and right["upper"] <= left["lower"]:
            ordering = 1
        if ordering is None:
            continue
        comparable += 1
        difference = float(left["mu_log2_budget"] - right["mu_log2_budget"])
        if abs(difference) < 1e-12:
            tied += 1
        elif (ordering == 1 and difference > 0) or (ordering == -1 and difference < 0):
            concordant += 1
    value = (concordant + 0.5 * tied) / comparable if comparable else np.nan
    return float(value) if np.isfinite(value) else np.nan, comparable

if SCORING_ENABLED and len(all_results):
    curve = (
        all_results[all_results["method"].eq("amw_ddet")]
        .groupby(["target", "provider", "target_role", "budget"], as_index=False)
        .agg(median_error=("absolute_error", "median"))
    )

    interval_rows = []
    regime_rows = []
    projected_rows = []
    for (target, provider, role), frame in curve.groupby(["target", "provider", "target_role"]):
        frame = frame.sort_values("budget")
        budgets = frame["budget"].to_numpy(int)
        errors = frame["median_error"].to_numpy(float)
        passing = np.flatnonzero(errors <= THRESHOLD)
        if len(passing):
            index = int(passing[0])
            lower = -np.inf if index == 0 else float(np.log2(budgets[index - 1]))
            upper = float(np.log2(budgets[index]))
            status = "LEFT_CENSORED" if index == 0 else "INTERVAL_CENSORED"
            operational = int(budgets[index])
        else:
            lower = float(np.log2(budgets[-1]))
            upper = np.inf
            status = "RIGHT_CENSORED"
            operational = 256

        projected = IsotonicRegression(
            increasing=False, out_of_bounds="clip"
        ).fit_transform(np.log2(budgets), errors)
        first_projected = float(projected[0])
        final_projected = float(projected[-1])
        repair_fraction = float(
            (first_projected - final_projected) / max(first_projected, 1e-12)
        )
        if final_projected <= THRESHOLD:
            regime = "EVIDENCE_LIMITED_OPERATIONAL"
        elif repair_fraction <= 0.20:
            regime = "MODEL_LIMITED_WITHIN_FROZEN_AUDIT_FAMILY"
        else:
            regime = "EVIDENCE_DEMANDING_RIGHT_CENSORED"

        interval_rows.append({
            "target": target, "provider": provider, "target_role": role,
            "lower": lower, "upper": upper, "status": status,
            "operational_budget_administrative": operational,
            "maximum_tested_budget": int(budgets[-1]),
        })
        regime_rows.append({
            "target": target, "provider": provider, "target_role": role,
            "projected_first_error": first_projected,
            "projected_final_error": final_projected,
            "projected_repair_fraction": repair_fraction,
            "frozen_regime": regime,
        })
        for budget, raw_error, projected_error in zip(budgets, errors, projected):
            projected_rows.append({
                "target": target, "budget": int(budget),
                "raw_median_error": float(raw_error),
                "isotonic_median_error": float(projected_error),
            })

    observed_intervals = pd.DataFrame(interval_rows)
    regime_table = pd.DataFrame(regime_rows)
    projected_curves = pd.DataFrame(projected_rows)
    prospective_evaluation = prospective_forecasts.merge(
        observed_intervals, on=["target", "provider", "target_role"], validate="one_to_one"
    )
    nll_rows = [
        predictive_interval_nll(row.lower, row.upper, row.mu_log2_budget, row.sigma)
        for row in prospective_evaluation.itertuples()
    ]
    prospective_evaluation["predictive_interval_nll"] = [value[0] for value in nll_rows]
    prospective_evaluation["probability_observed_interval"] = [value[1] for value in nll_rows]

    concordance, comparable_pairs = interval_order_concordance(prospective_evaluation)
    supported = prospective_evaluation[
        prospective_evaluation["support_status"].eq("SUPPORTED")
    ]
    supported_mean_nll = (
        float(supported["predictive_interval_nll"].mean()) if len(supported) else np.nan
    )
    abstention_rate = float(
        prospective_evaluation["support_status"].eq("OUT_OF_SUPPORT_ABSTAIN").mean()
    )

    ra32_summary = (
        all_results[
            all_results["method"].eq("ra_cb_amw_ddet")
            & all_results["budget"].eq(32)
        ]
        .groupby(["target", "provider", "target_role"], as_index=False)
        .agg(target_median_mae_b32=("absolute_error", "median"))
    )

    write_csv(P6 / "StageT2-N_Observed_Interval_Truth_v0.1.csv", observed_intervals)
    write_csv(P6 / "StageT2-N_Prospective_Forecast_Evaluation_v0.1.csv", prospective_evaluation)
    write_csv(P6 / "StageT2-N_Isotonic_Evidence_Curves_v0.1.csv", projected_curves)
    write_csv(P6 / "StageT2-N_Provider_Regime_Assignments_v0.1.csv", regime_table)
    write_csv(P6 / "StageT2-N_RA_CB_B32_Target_Summary_v0.1.csv", ra32_summary)
else:
    concordance, comparable_pairs = np.nan, 0
    supported_mean_nll = np.nan
    abstention_rate = np.nan

score_ready_count = int(readiness["score_ready"].sum()) if len(readiness) else 0
provider_count = int(
    readiness.loc[readiness["score_ready"], "provider"].nunique()
) if len(readiness) else 0
metadata_success = int(
    pd.DataFrame(metadata_receipts)["status"].isin(
        ["DOWNLOADED", "DOWNLOADED_BY_ISIC_CLI", "ALREADY_PRESENT"]
    ).sum()
)
budget_complete = bool(
    not SCORING_ENABLED
    or (
        set(BUDGETS).issubset(set(all_results["budget"].unique()))
        and all(
            set(BUDGETS).issubset(
                set(all_results.loc[all_results["target"].eq(target), "budget"].unique())
            )
            for target in target_roster["dataset"].unique()
        )
    )
)
forecast_chronology = bool(
    forecast_record["full_provider_budget_truth_observed"] is False
    and forecast_record_path.exists()
)
regime_complete = bool(
    not SCORING_ENABLED
    or (
        len(regime_table) == score_ready_count
        and regime_table["frozen_regime"].notna().all()
    )
)

gates = pd.DataFrame([
    {"gate": "G1_parent_model_support_and_documents_exact", "passed": True,
     "observed": "T2-M/T2-H/T3-PF, source axes and companion hashes exact"},
    {"gate": "G2_official_metadata_routes_audited", "passed": len(metadata_receipts) == len(COLLECTIONS),
     "observed": f"success={metadata_success}/{len(COLLECTIONS)}; all routes audited"},
    {"gate": "G3_at_least_one_provider_target_score_ready", "passed": score_ready_count >= 1,
     "observed": sorted(target_roster["dataset"].unique()) if len(target_roster) else []},
    {"gate": "G4_at_least_two_provider_targets_score_ready", "passed": score_ready_count >= 2,
     "observed": score_ready_count},
    {"gate": "G5_distinct_provider_count_at_least_two", "passed": provider_count >= 2,
     "observed": provider_count},
    {"gate": "G6_cross_roster_dedup_governance_complete", "passed": True,
     "observed": candidate["adjudication_status"].value_counts().to_dict() if len(candidate) else {"NO_ENDPOINT_READY_CANDIDATE": 0}},
    {"gate": "G7_frozen_source_axes_exact", "passed": True,
     "observed": sorted(AXIS_PATHS)},
    {"gate": "G8_budget8_forecast_sealed_before_higher_truth", "passed": forecast_chronology,
     "observed": forecast_record["prospective_forecast_record_sha256"]},
    {"gate": "G9_full_multibudget_completeness", "passed": budget_complete,
     "observed": int(len(all_results))},
    {"gate": "G10_prospective_interval_evaluation_finite",
     "passed": bool(
         not SCORING_ENABLED
         or (
             len(prospective_evaluation) == score_ready_count
             and np.isfinite(prospective_evaluation["predictive_interval_nll"]).all()
         )
     ),
     "observed": (
         float(prospective_evaluation["predictive_interval_nll"].mean())
         if len(prospective_evaluation) else "not_scored"
     )},
    {"gate": "G11_regime_assignment_complete", "passed": regime_complete,
     "observed": regime_table["frozen_regime"].value_counts().to_dict() if len(regime_table) else {}},
    {"gate": "G12_manual_ph2_route_ready", "passed": ph2_inbox.exists(),
     "observed": str(ph2_inbox)},
    {"gate": "G13_runtime_storage_policy", "passed": str(RUNTIME_ROOT).startswith("/content/") or not IN_COLAB,
     "observed": str(RUNTIME_ROOT)},
    {"gate": "G14_single_pilot_failure_preserved",
     "passed": t2h_final["single_pilot_deployment_authorised"] is False,
     "observed": False},
    {"gate": "G15_locked_blind_firewall", "passed": True,
     "observed": "no locked-blind path, asset or outcome accessed"},
    {"gate": "G16_stage12_false", "passed": t3pf_final["stage12_authorised"] is False,
     "observed": False},
])

integrity_names = [
    "G1_parent_model_support_and_documents_exact",
    "G2_official_metadata_routes_audited",
    "G6_cross_roster_dedup_governance_complete",
    "G7_frozen_source_axes_exact",
    "G8_budget8_forecast_sealed_before_higher_truth",
    "G9_full_multibudget_completeness",
    "G10_prospective_interval_evaluation_finite",
    "G11_regime_assignment_complete",
    "G12_manual_ph2_route_ready",
    "G13_runtime_storage_policy",
    "G14_single_pilot_failure_preserved",
    "G15_locked_blind_firewall",
    "G16_stage12_false",
]
integrity_pass = bool(gates.loc[gates["gate"].isin(integrity_names), "passed"].all())

if not integrity_pass:
    decision = "TERMINATE_T2N_INTEGRITY_ACQUISITION_CHRONOLOGY_SCORING_OR_FIREWALL_FAILURE"
elif score_ready_count >= 2 and provider_count >= 2:
    decision = "SEAL_PROVIDER_SEPARATED_PROSPECTIVE_EXTENSION_RETAIN_FROZEN_MODEL_AUTHORISE_STAGE3_ACTIVATION_REVIEW_ONLY"
elif score_ready_count == 1:
    decision = "SEAL_PARTIAL_PROVIDER_EXTENSION_CONTINUE_OFFICIAL_AND_PH2_ACQUISITION"
else:
    decision = "HOLD_PROVIDER_EXTENSION_CONTINUE_OFFICIAL_METADATA_REPAIR_AND_PH2_MANUAL_ACQUISITION"

write_csv(P7 / "StageT2-N_Frozen_Gates_v0.1.csv", gates)

if len(prospective_evaluation):
    plt.figure(figsize=(8, 5))
    colors = prospective_evaluation["support_status"].map(
        {"SUPPORTED": 0, "OUT_OF_SUPPORT_ABSTAIN": 1}
    )
    plt.scatter(
        prospective_evaluation["mu_log2_budget"],
        prospective_evaluation["target"],
        c=colors,
    )
    for _, row in prospective_evaluation.iterrows():
        lower = row["upper"] - 1 if np.isneginf(row["lower"]) else row["lower"]
        upper = row["lower"] + 1 if np.isposinf(row["upper"]) else row["upper"]
        plt.plot([lower, upper], [row["target"], row["target"]], linewidth=2)
    plt.xlabel("Frozen predicted latent log2 budget and observed interval")
    plt.ylabel("Provider target")
    plt.title("Stage T2-N prospective evidence-demand evaluation")
    plt.tight_layout()
    plt.savefig(P7 / "StageT2-N_Prospective_Interval_Evaluation_v0.1.png", dpi=220)
    plt.show()

    plt.figure(figsize=(8, 5))
    for target, frame in projected_curves.groupby("target"):
        plt.plot(frame["budget"], frame["isotonic_median_error"], marker="o", label=target)
    plt.axhline(THRESHOLD, linestyle="--")
    plt.xscale("log", base=2)
    plt.xlabel("Witness-group budget")
    plt.ylabel("Isotonic median absolute AUC error")
    plt.title("Provider-separated frozen evidence curves")
    plt.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(P7 / "StageT2-N_Provider_Evidence_Curves_v0.1.png", dpi=220)
    plt.show()

completion = {
    "stage": "StageT2-N",
    "decision": decision,
    "parent_t2m_final_record_sha256": EXPECTED_PARENT["t2m"],
    "protocol_seal_sha256": protocol["protocol_seal_sha256"],
    "prospective_forecast_record_sha256": forecast_record["prospective_forecast_record_sha256"],
    "score_ready_targets": sorted(target_roster["dataset"].unique()) if len(target_roster) else [],
    "score_ready_target_count": score_ready_count,
    "distinct_provider_count": provider_count,
    "expansion_edge_count": int(truth_table["edge_id"].nunique()) if len(truth_table) else 0,
    "multibudget_result_rows": int(len(all_results)),
    "mean_prospective_interval_nll": (
        float(prospective_evaluation["predictive_interval_nll"].mean())
        if len(prospective_evaluation) else None
    ),
    "supported_mean_prospective_interval_nll": (
        supported_mean_nll if np.isfinite(supported_mean_nll) else None
    ),
    "interval_order_concordance": (
        concordance if np.isfinite(concordance) else None
    ),
    "comparable_target_pairs": comparable_pairs,
    "abstention_rate": abstention_rate if np.isfinite(abstention_rate) else None,
    "regime_counts": (
        regime_table["frozen_regime"].value_counts().to_dict()
        if len(regime_table) else {}
    ),
    "ph2_manual_archive_present": bool(
        any(path.suffix.lower() in {".zip", ".rar", ".7z"} for path in ph2_inbox.iterdir())
    ),
    "single_pilot_deployment_authorised": False,
    "locked_blind_assets_touched": False,
    "locked_blind_outcomes_accessed": False,
    "stage12_authorised": False,
    "gates_passed": int(gates["passed"].sum()),
    "gates_total": int(len(gates)),
    "completed_utc": now(),
}
completion["final_record_sha256"] = sha_json(completion)
write_json(P7 / "StageT2-N_Complete_v0.1.json", completion)

summary = f"""# Stage T2-N result summary v0.1

- Decision: `{decision}`
- Score-ready provider targets: `{completion['score_ready_targets']}`
- Distinct providers: `{provider_count}`
- Directed expansion edges: `{completion['expansion_edge_count']}`
- Multi-budget rows: `{completion['multibudget_result_rows']}`
- Mean prospective interval NLL: `{completion['mean_prospective_interval_nll']}`
- Interval-order concordance: `{completion['interval_order_concordance']}`
- Abstention rate: `{completion['abstention_rate']}`
- Regime counts: `{completion['regime_counts']}`
- PH2 official archive present: `{completion['ph2_manual_archive_present']}`
- Single-pilot deployment authorised: `False`
- Locked blind assets touched: `False`
- Stage 12 authorised: `False`
- Gates: `{completion['gates_passed']}/{completion['gates_total']}`
- Final record SHA256: `{completion['final_record_sha256']}`
"""
write_text(P7 / "StageT2-N_Result_Summary_v0.1.md", summary)

display(prospective_evaluation)
display(regime_table)
display(ra32_summary)
display(gates)

print("\n========== STAGE T2-N COMPLETE ==========")
print("Decision:", decision)
print("Score-ready provider targets:", completion["score_ready_targets"])
print("Distinct providers:", provider_count)
print("Regime counts:", completion["regime_counts"])
print("PH2 official archive present:", completion["ph2_manual_archive_present"])
print("PH2 exact drop folder:", ph2_inbox)
print("Single-pilot deployment authorised:", False)
print("Locked blind assets touched:", False)
print("Stage 12 authorised:", False)
print("Final record SHA256:", completion["final_record_sha256"])



# Merge substage records and perform a verified, local-first durable Drive commit.
n_completion = completion
FINAL_LOCAL_ROOT = LOCAL_RECORD_ROOT / "StageT2-MN-Final"
FINAL_LOCAL_ROOT.mkdir(parents=True, exist_ok=True)

if n_completion["score_ready_target_count"] >= 2 and n_completion["distinct_provider_count"] >= 2:
    merged_decision = "SEAL_T2MN_CENSORED_MODEL_AND_PROVIDER_PROSPECTIVE_EXTENSION_AUTHORISE_STAGE3_ACTIVATION_REVIEW_ONLY"
elif n_completion["score_ready_target_count"] == 1:
    merged_decision = "SEAL_T2MN_CENSORED_MODEL_AND_PARTIAL_PROVIDER_EXTENSION_CONTINUE_PROVIDER_ACQUISITION"
else:
    merged_decision = "SEAL_T2MN_CENSORED_MODEL_HOLD_PROVIDER_EXTENSION_CONTINUE_OFFICIAL_ROUTE_REPAIR"

mn_completion = {
    "stage": "StageT2-MN",
    "decision": merged_decision,
    "entry_seal_sha256": entry_payload["entry_seal_sha256"],
    "t2m_checkpoint_sha256": t2m_checkpoint["t2m_checkpoint_sha256"],
    "t2m_final_record_sha256": t2m_final["final_record_sha256"],
    "t2m_model_freeze_sha256": model_freeze["model_freeze_sha256"],
    "t2m_support_freeze_sha256": support_freeze["support_freeze_sha256"],
    "provider_activation_seal_sha256": protocol["protocol_seal_sha256"],
    "provider_forecast_seal_sha256": forecast_record["prospective_forecast_record_sha256"],
    "t2m_selected_feature_set": t2m_final["selected_feature_set"],
    "t2m_selected_penalty": t2m_final["selected_penalty"],
    "t2m_fixed_loto_relative_nll_improvement": t2m_final["fixed_loto_relative_nll_improvement"],
    "t2m_nested_loto_relative_nll_improvement": t2m_final["nested_loto_relative_nll_improvement"],
    "t2m_family_holdout_relative_nll_improvement": t2m_final["leave_one_family_out_relative_nll_improvement"],
    "t2m_interval_order_concordance": t2m_final["fixed_interval_order_concordance"],
    "t2m_support_coverage": t2m_final["support_coverage"],
    "t2m_regime_counts": t2m_final["regime_counts"],
    "score_ready_provider_targets": n_completion["score_ready_targets"],
    "score_ready_provider_target_count": n_completion["score_ready_target_count"],
    "distinct_provider_count": n_completion["distinct_provider_count"],
    "provider_regime_counts": n_completion["regime_counts"],
    "mean_provider_prospective_interval_nll": n_completion["mean_prospective_interval_nll"],
    "provider_abstention_rate": n_completion["abstention_rate"],
    "ph2_status": "HOLD_OFFICIAL_DOWNLOAD_LINK_DEAD",
    "single_pilot_deployment_authorised": False,
    "locked_blind_assets_touched": False,
    "locked_blind_outcomes_accessed": False,
    "stage12_authorised": False,
    "durable_commit_required": True,
    "completed_utc": now(),
}
mn_completion["final_record_sha256"] = sha_json(mn_completion)
mn_complete_path = FINAL_LOCAL_ROOT / "StageT2-MN_Complete_v0.1.json"
write_json(mn_complete_path, mn_completion)

mn_summary = f"""# Stage T2-MN result summary v0.1

- Decision: `{mn_completion['decision']}`
- T2-M selected model: `{mn_completion['t2m_selected_feature_set']}`, penalty `{mn_completion['t2m_selected_penalty']}`
- T2-M fixed / nested / family-holdout NLL improvements:
  `{mn_completion['t2m_fixed_loto_relative_nll_improvement']:.2%}` /
  `{mn_completion['t2m_nested_loto_relative_nll_improvement']:.2%}` /
  `{mn_completion['t2m_family_holdout_relative_nll_improvement']:.2%}`
- T2-M interval-order concordance: `{mn_completion['t2m_interval_order_concordance']:.6f}`
- T2-M support coverage: `{mn_completion['t2m_support_coverage']:.2%}`
- T2-M regimes: `{mn_completion['t2m_regime_counts']}`
- Score-ready provider targets: `{mn_completion['score_ready_provider_targets']}`
- Distinct providers: `{mn_completion['distinct_provider_count']}`
- Provider regimes: `{mn_completion['provider_regime_counts']}`
- PH2: `HOLD_OFFICIAL_DOWNLOAD_LINK_DEAD`
- Single-pilot deployment authorised: `False`
- Locked blind assets touched: `False`
- Stage 12 authorised: `False`
- Final record SHA256: `{mn_completion['final_record_sha256']}`
"""
mn_summary_path = FINAL_LOCAL_ROOT / "StageT2-MN_Result_Summary_v0.1.md"
write_text(mn_summary_path, mn_summary)

# Canonical ZIP contains governed records only; ephemeral selected images live outside LOCAL_RECORD_ROOT.
bundle_path = RUNTIME_ROOT / "StageT2-MN_Canonical_Records_v0.1.zip"
with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for source in sorted(LOCAL_RECORD_ROOT.rglob("*")):
        if source.is_file():
            archive.write(source, arcname=str(source.relative_to(LOCAL_RECORD_ROOT)))
bundle_sha = sha_file(bundle_path)

def durable_drive_copy(source, destination):
    source = Path(source)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".uploading")
    if temporary.exists():
        temporary.unlink()
    with source.open("rb") as reader, temporary.open("wb") as writer:
        while True:
            block = reader.read(1024 * 1024)
            if not block:
                break
            writer.write(block)
        writer.flush()
        os.fsync(writer.fileno())
    os.replace(temporary, destination)
    os.sync()
    observed_size = destination.stat().st_size
    observed_sha = sha_file(destination)
    assert observed_size == source.stat().st_size, f"Drive size mismatch: {destination}"
    assert observed_sha == sha_file(source), f"Drive SHA mismatch: {destination}"
    return {
        "file": destination.name,
        "bytes": observed_size,
        "sha256": observed_sha,
        "drive_path": str(destination),
    }

DRIVE_RESULT_ROOT.mkdir(parents=True, exist_ok=True)
commit_rows = []
commit_rows.append(durable_drive_copy(
    bundle_path, DRIVE_RESULT_ROOT / "StageT2-MN_Canonical_Records_v0.1.zip"
))

critical_sources = [
    mn_complete_path,
    mn_summary_path,
    M_P3 / "StageT2-M_Final_Interval_Censored_Model_Freeze_v0.1.json",
    M_P3 / "StageT2-M_Future_Support_Abstention_Freeze_v0.1.json",
    M_P3 / "StageT2-M_Family_Bootstrap_Parameter_Draws_v0.1.csv",
    M_P5 / "StageT2-M_Frozen_Gates_v0.1.csv",
    N_P2 / "StageT2-N_Target_Readiness_Map_v0.1.csv",
    N_P4 / "StageT2-N_Prospective_Forecast_Seal_v0.1.json",
    N_P7 / "StageT2-N_Frozen_Gates_v0.1.csv",
    N_P7 / "StageT2-N_Complete_v0.1.json",
]
for optional in [
    N_P4 / "StageT2-N_Prospective_Provider_Forecasts_v0.1.csv",
    N_P6 / "StageT2-N_Prospective_Forecast_Evaluation_v0.1.csv",
    N_P6 / "StageT2-N_Provider_Regime_Assignments_v0.1.csv",
]:
    if optional.is_file():
        critical_sources.append(optional)

for source in critical_sources:
    assert Path(source).is_file(), f"Critical local record missing before commit: {source}"
    commit_rows.append(durable_drive_copy(
        source, DRIVE_RESULT_ROOT / Path(source).name
    ))

commit_manifest = {
    "stage": "StageT2-MN",
    "commit_root": str(DRIVE_RESULT_ROOT),
    "canonical_bundle_sha256": bundle_sha,
    "files": commit_rows,
    "all_drive_copies_reopened_and_hash_verified": True,
    "drive_flush_requested": bool(IN_COLAB),
    "locked_blind_assets_touched": False,
    "stage12_authorised": False,
    "committed_utc": now(),
}
commit_manifest["commit_manifest_sha256"] = sha_json(commit_manifest)
local_manifest_path = FINAL_LOCAL_ROOT / "StageT2-MN_Durable_Commit_Manifest_v0.1.json"
write_json(local_manifest_path, commit_manifest)
manifest_row = durable_drive_copy(
    local_manifest_path,
    DRIVE_RESULT_ROOT / "StageT2-MN_Durable_Commit_Manifest_v0.1.json",
)
assert manifest_row["sha256"] == sha_file(local_manifest_path)

# Final mounted-path verification before flushing Drive.
for row in commit_rows + [manifest_row]:
    path = Path(row["drive_path"])
    assert path.is_file()
    assert path.stat().st_size == row["bytes"]
    assert sha_file(path) == row["sha256"]

print("\nDURABLE DRIVE COMMIT VERIFIED BEFORE FLUSH")
print("Drive result folder:", DRIVE_RESULT_ROOT)
print("Canonical bundle SHA256:", bundle_sha)
print("Commit manifest SHA256:", commit_manifest["commit_manifest_sha256"])

flush_status = "NOT_IN_COLAB"
if IN_COLAB:
    try:
        drive.flush_and_unmount()
        flush_status = "FLUSH_AND_UNMOUNT_COMPLETE"
    except Exception as exc:
        raise RuntimeError(f"Drive flush-and-unmount failed after byte verification: {exc}")

# Ephemeral image/download caches can now be removed.
if RUNTIME_ROOT.exists():
    shutil.rmtree(RUNTIME_ROOT)

print("\n========== STAGE T2-MN COMPLETE ==========")
print("Decision:", mn_completion["decision"])
print("T2-M model:", mn_completion["t2m_selected_feature_set"], mn_completion["t2m_selected_penalty"])
print("Provider targets:", mn_completion["score_ready_provider_targets"])
print("Drive persistence:", flush_status)
print("Durable commit manifest SHA256:", commit_manifest["commit_manifest_sha256"])
print("Single-pilot deployment authorised:", False)
print("Locked blind assets touched:", False)
print("Stage 12 authorised:", False)
print("Final record SHA256:", mn_completion["final_record_sha256"])
