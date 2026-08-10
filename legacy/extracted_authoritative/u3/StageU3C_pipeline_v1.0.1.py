from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
import warnings
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

SEED = 20260724
BUDGETS = [8, 16, 32, 64, 128]
N_REP = 200
FUSION_TRANSPORT_WEIGHT = 0.6
FUSION_DIRECT_WEIGHT = 0.4

U01_FINAL_SHA256 = "e18602ed16b242cfe5a220539ef46c525ca3c2f2046c16476afbaeb2cf8f5556"
U2_FINAL_SHA256 = "158627b2bc9ab1c977e474ebefea4b254bf42a4a3ea90baead7ef263f2211c5a"
U3A_FINAL_SHA256 = "38939c39aff66bba716affd92a19b7ae96f233a7872d4926094d6195b3c8250d"
U3B_PREREGISTRATION_SHA256 = "565a5c577c995cc65040778780b03382259e801cf2dac6bd43543d96cf49ea2c"
U3B_SEAL_SHA256 = "c1601253c3336b9ddeff5f1e7ff9b842db55be2aa9401bc9a045b4cf8e75f2b5"
PREDICTION_ENVELOPE_SHA256 = "5b9149e1e2be49cd0bc70710bd8c740cefff01360eb7eef7713fb6512dd97ef2"

PACS_REVISION = "394113073258ead631f617d2e13bb377c0715c4b"
PACS_PARQUET_SHA256 = "4fc041ee92eec6043fe6e2859e8bdd138e5f958bc621afd153879812cbe65ff5"
AMAZON_URL = "https://www.cs.jhu.edu/~mdredze/datasets/sentiment/domain_sentiment_data.tar.gz"

ROOT = Path("/content/drive/MyDrive/Cross-Modal_Diagnostic_Observability")
DESIGN_ROOT = ROOT / "04_Study_Design/StageU3_Prospective_Reserve_Design_And_Preregistration"
AUTH_PATH = DESIGN_ROOT / "U3C_EXECUTION_AUTHORIZATION.json"
U3B_FINAL_ROOT = DESIGN_ROOT / "StageU3B_Final_Preregistration_v1.0"
U3B_PREREG_PATH = U3B_FINAL_ROOT / "StageU3B_Final_Prospective_Reserve_Preregistration_v1.0.txt"
U3B_SEAL_PATH = U3B_FINAL_ROOT / "StageU3B_Final_Preregistration_Seal_v1.0.json"
ENVELOPE_PATH = U3B_FINAL_ROOT / "StageU3A_Prospective_Reserve_Prediction_Envelope_v0.1.csv"
U3A_ROOT = ROOT / "06_Data_Records/Cross_Modal/StageU3A_Observability_Universality_Classes_v0.1"
U2_DATA = ROOT / "11_External_Data/NonBiomedical/CIFAR_External_v0.1"
DATA_ROOT = ROOT / "11_External_Data/Prospective_Reserve_U3C_v1.0"
OUT_ROOT = ROOT / "06_Data_Records/Cross_Modal/StageU3C_Prospective_Reserve_v1.0"

SUB = {
    "integrity": "00_Integrity_And_Authorisation",
    "acquisition": "01_Reserve_Acquisition_And_Hashes",
    "source": "02_Source_Models_And_Thresholds",
    "predictions": "03_Target_Predictions_And_Descriptors",
    "witness": "04_Target_Budget_Witnesses",
    "classes": "05_Prospective_Class_And_Trajectory_Tests",
    "fusion": "06_Transport_Fusion_And_Label_Leverage",
    "figures": "07_Figures",
    "decision": "08_Decision_And_Manuscript",
}

RUN_LOG = OUT_ROOT / SUB["integrity"] / "StageU3C_Run_Log_v1.0.txt"
PROGRESS_PATH = OUT_ROOT / SUB["integrity"] / "StageU3C_Progress_v1.0.json"

EXPECTED_ROSTER = {
    "PACS": {"source": "photo", "targets": ["art_painting", "cartoon", "sketch"]},
    "AMAZON_MDS": {"source": "books", "targets": ["dvd", "electronics", "kitchen"]},
}
EXPECTED_METRICS = ["auc", "auprc", "balanced_accuracy", "brier", "log_loss"]


def utc_now() -> str:
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def log(message: str) -> None:
    stamp = utc_now()
    line = f"[Stage U3C {stamp}] {message}"
    print(line, flush=True)
    try:
        RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
        with RUN_LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_seed(*parts: Any) -> int:
    raw = "|".join(map(str, parts)).encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "little") % (2**32 - 1)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_json(path: Path, obj: Any) -> None:
    atomic_write_text(path, json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False))


def save_df(path: Path, df: "pd.DataFrame") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)


def update_progress(stage: str, **extra: Any) -> None:
    current: Dict[str, Any] = {}
    if PROGRESS_PATH.exists():
        try:
            current = json.loads(PROGRESS_PATH.read_text(encoding="utf-8"))
        except Exception:
            current = {}
    current.update({"stage": stage, "updated_at_utc": utc_now(), **extra})
    write_json(PROGRESS_PATH, current)


def ensure_dirs() -> None:
    for name in SUB.values():
        (OUT_ROOT / name).mkdir(parents=True, exist_ok=True)
    DATA_ROOT.mkdir(parents=True, exist_ok=True)


def ensure_dependencies() -> None:
    required = {
        "numpy": "numpy",
        "pandas": "pandas",
        "sklearn": "scikit-learn",
        "torch": "torch",
        "torchvision": "torchvision",
        "PIL": "Pillow",
        "datasets": "datasets>=2.19,<5",
        "joblib": "joblib",
        "matplotlib": "matplotlib",
    }
    missing: List[str] = []
    for module, package in required.items():
        try:
            __import__(module)
        except Exception:
            missing.append(package)
    if missing:
        log("Installing missing packages: " + ", ".join(missing))
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", *missing])


def import_runtime_packages() -> None:
    global np, pd
    import numpy as _np
    import pandas as _pd
    np = _np
    pd = _pd


def exact_sha(path: Path, expected: str, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing {label}: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise RuntimeError(f"{label} SHA mismatch: actual={actual}, expected={expected}")


def require_authorisation() -> Dict[str, Any]:
    if not AUTH_PATH.exists():
        raise RuntimeError("U3C execution is not authorised: missing " + str(AUTH_PATH))
    auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    required = [
        "authorised",
        "authorised_at_utc",
        "u3a_final_record_sha256",
        "u3b_preregistration_sha256",
        "u3b_seal_sha256",
        "prediction_envelope_sha256",
        "execution_pipeline_sha256",
        "reserve_roster",
        "budgets",
        "metrics",
        "replicates",
    ]
    missing = [k for k in required if k not in auth]
    if missing or auth.get("authorised") is not True:
        raise RuntimeError(f"Invalid U3C authorisation: missing={missing}; authorised={auth.get('authorised')}")
    if "authorisation_record_sha256" not in auth:
        raise RuntimeError("Authorisation record has no self-seal.")
    unsigned_auth = {key: value for key, value in auth.items() if key != "authorisation_record_sha256"}
    actual_auth_sha = hashlib.sha256(json.dumps(unsigned_auth, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    if actual_auth_sha != auth["authorisation_record_sha256"]:
        raise RuntimeError(f"Authorisation self-seal mismatch: {actual_auth_sha} != {auth['authorisation_record_sha256']}")

    expected_pipeline_sha = os.environ.get("CMDO_U3C_PIPELINE_SHA256", "")
    checks = {
        "u3a_final_record_sha256": U3A_FINAL_SHA256,
        "u3b_preregistration_sha256": U3B_PREREGISTRATION_SHA256,
        "u3b_seal_sha256": U3B_SEAL_SHA256,
        "prediction_envelope_sha256": PREDICTION_ENVELOPE_SHA256,
        "execution_pipeline_sha256": expected_pipeline_sha,
    }
    for key, expected in checks.items():
        if not expected or auth.get(key) != expected:
            raise RuntimeError(f"Authorisation field {key} mismatch: {auth.get(key)} != {expected}")
    if auth.get("reserve_roster") != EXPECTED_ROSTER:
        raise RuntimeError("Authorised reserve roster differs from the frozen roster.")
    if list(auth.get("budgets")) != BUDGETS:
        raise RuntimeError("Authorised budgets differ from frozen budgets.")
    if list(auth.get("metrics")) != EXPECTED_METRICS:
        raise RuntimeError("Authorised metrics differ from frozen metrics.")
    if int(auth.get("replicates")) != N_REP:
        raise RuntimeError("Authorised replicate count differs from frozen count.")

    u3a_complete = U3A_ROOT / SUB["decision"].replace("08_", "07_") / "StageU3A_Complete_v0.1.json"
    # U3A uses 07_Decision_And_Manuscript.
    u3a_complete = U3A_ROOT / "07_Decision_And_Manuscript/StageU3A_Complete_v0.1.json"
    if not u3a_complete.exists():
        raise FileNotFoundError("Formal U3A complete record is missing.")
    actual_u3a = json.loads(u3a_complete.read_text(encoding="utf-8"))["final_record_sha256"]
    if actual_u3a != U3A_FINAL_SHA256:
        raise RuntimeError("Formal U3A record SHA does not match the authorisation.")

    exact_sha(U3B_PREREG_PATH, U3B_PREREGISTRATION_SHA256, "U3B preregistration text")
    exact_sha(U3B_SEAL_PATH, U3B_SEAL_SHA256, "U3B preregistration seal")
    exact_sha(ENVELOPE_PATH, PREDICTION_ENVELOPE_SHA256, "prospective prediction envelope")
    return auth


def safe_extract_tar(archive: Path, destination: Path) -> None:
    destination = destination.resolve()
    with tarfile.open(archive, "r:gz") as tf:
        for member in tf.getmembers():
            target = (destination / member.name).resolve()
            if not str(target).startswith(str(destination)):
                raise RuntimeError(f"Unsafe archive member: {member.name}")
        tf.extractall(destination)


def download_with_progress(url: str, destination: Path, retries: int = 3) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 0:
        log(f"Reusing downloaded file: {destination.name} ({destination.stat().st_size / 1e6:.1f} MB)")
        return
    tmp = destination.with_suffix(destination.suffix + ".part")
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 CMDO-U3C/1.0"})
            with urllib.request.urlopen(req, timeout=120) as response, tmp.open("wb") as out:
                total = int(response.headers.get("Content-Length") or 0)
                done = 0
                last = time.time()
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    out.write(block)
                    done += len(block)
                    if time.time() - last > 5:
                        if total:
                            log(f"Downloading {destination.name}: {done / 1e6:.1f}/{total / 1e6:.1f} MB")
                        else:
                            log(f"Downloading {destination.name}: {done / 1e6:.1f} MB")
                        last = time.time()
            os.replace(tmp, destination)
            return
        except Exception as exc:
            log(f"Download attempt {attempt}/{retries} failed: {exc}")
            if tmp.exists():
                tmp.unlink()
            if attempt == retries:
                raise
            time.sleep(3 * attempt)


def entropy(prob: "np.ndarray") -> "np.ndarray":
    p = np.clip(np.asarray(prob, float), 1e-8, 1 - 1e-8)
    return -(p * np.log(p) + (1 - p) * np.log(1 - p))


def descriptors(source_features: "np.ndarray", source_scores: "np.ndarray", target_features: "np.ndarray", target_scores: "np.ndarray") -> "np.ndarray":
    sm, tm = source_features.mean(0), target_features.mean(0)
    sv, tv = source_features.var(0) + 1e-8, target_features.var(0) + 1e-8
    return np.array(
        [
            np.linalg.norm(tm - sm) / math.sqrt(len(sm)),
            np.mean(np.abs(np.log(tv / sv))),
            abs(float(target_scores.mean() - source_scores.mean())),
            abs(float(entropy(target_scores).mean() - entropy(source_scores).mean())),
            abs(float(np.maximum(target_scores, 1 - target_scores).mean() - np.maximum(source_scores, 1 - source_scores).mean())),
        ],
        float,
    )


def fit_transport_mapping():
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler

    src_cache = U2_DATA / "model_checkpoints/StageU2_CIFAR_source_validation_cache_AUTHORITATIVE_v0.1.7.npz"
    pred_root = U2_DATA / "environment_prediction_cache_v0.1.7_AUTHORITATIVE_EPOCH12"
    if not src_cache.exists() or not pred_root.exists():
        raise FileNotFoundError("Corrected U2 authoritative prediction caches are required for frozen transport training.")
    source = np.load(src_cache)
    source_features, source_scores = np.asarray(source["features"]), np.asarray(source["scores"])
    sm, sv = source_features.mean(0), source_features.var(0) + 1e-8
    rows, outcomes, names = [], [], []
    for path in sorted(pred_root.glob("*.npz")):
        arr = np.load(path, allow_pickle=False)
        target_mean, target_var = np.asarray(arr["feature_mean"]), np.asarray(arr["feature_var"])
        target_scores = np.asarray(arr["scores"])
        row = np.array(
            [
                np.linalg.norm(target_mean - sm) / math.sqrt(len(sm)),
                np.mean(np.abs(np.log(target_var / sv))),
                abs(float(target_scores.mean() - source_scores.mean())),
                abs(float(entropy(target_scores).mean() - entropy(source_scores).mean())),
                abs(float(np.maximum(target_scores, 1 - target_scores).mean() - np.maximum(source_scores, 1 - source_scores).mean())),
            ],
            float,
        )
        rows.append(row)
        outcomes.append(float(arr["auc"]))
        names.append(path.stem)
    X, y = np.asarray(rows), np.asarray(outcomes)
    if len(X) != 38:
        raise RuntimeError(f"Frozen U2 transport training roster must contain 38 environments, found {len(X)}")
    scaler = StandardScaler().fit(X)
    model = Ridge(alpha=1.0).fit(scaler.transform(X), y)
    frame = pd.DataFrame(
        X,
        columns=["feature_mean_shift", "variance_log_ratio", "score_shift", "entropy_shift", "confidence_shift"],
    ).assign(target=names, true_auc=y)
    return scaler, model, frame


def choose_threshold(y: "np.ndarray", p: "np.ndarray") -> float:
    from sklearn.metrics import balanced_accuracy_score

    grid = np.linspace(0.02, 0.98, 97)
    values = [balanced_accuracy_score(y, p >= threshold) for threshold in grid]
    return float(grid[int(np.argmax(values))])


def full_metrics(y: "np.ndarray", p: "np.ndarray", threshold: float) -> Dict[str, float]:
    from sklearn.metrics import average_precision_score, balanced_accuracy_score, brier_score_loss, log_loss, roc_auc_score

    y = np.asarray(y, int)
    p = np.clip(np.asarray(p, float), 1e-8, 1 - 1e-8)
    if len(np.unique(y)) < 2:
        raise ValueError("Full target metric requires both classes.")
    return {
        "auc": float(roc_auc_score(y, p)),
        "auprc": float(average_precision_score(y, p)),
        "balanced_accuracy": float(balanced_accuracy_score(y, p >= threshold)),
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
    }


def hash_torch_state_dict(state: Mapping[str, Any]) -> str:
    h = hashlib.sha256()
    for key in sorted(state):
        tensor = state[key].detach().cpu().contiguous()
        h.update(key.encode("utf-8"))
        h.update(str(tensor.dtype).encode("utf-8"))
        h.update(np.asarray(tensor).tobytes())
    return h.hexdigest()


def load_or_build_pacs_system() -> Tuple["np.ndarray", "np.ndarray", "np.ndarray", float, Dict[str, Tuple["np.ndarray", "np.ndarray", "np.ndarray"]], Dict[str, Any]]:
    cache_dir = DATA_ROOT / "pacs"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "StageU3C_PACS_Frozen_System_Cache_v1.0.npz"
    meta_path = cache_dir / "StageU3C_PACS_Frozen_System_Metadata_v1.0.json"
    if cache_path.exists() and meta_path.exists():
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        if metadata.get("cache_sha256") != sha256_file(cache_path):
            raise RuntimeError("PACS frozen-system cache hash mismatch.")
        log("Reusing frozen PACS source-system cache.")
        arr = np.load(cache_path, allow_pickle=False)
        targets = {
            target: (arr[f"{target}_features"], arr[f"{target}_labels"], arr[f"{target}_scores"])
            for target in EXPECTED_ROSTER["PACS"]["targets"]
        }
        return arr["source_features"], arr["source_labels"], arr["source_scores"], float(arr["threshold"]), targets, metadata

    import torch
    from datasets import load_dataset
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split
    from torch.utils.data import DataLoader, Dataset
    from torchvision.models import ResNet18_Weights, resnet18

    os.environ.setdefault("HF_HOME", str(cache_dir / "hf_home"))
    os.environ.setdefault("HF_DATASETS_CACHE", str(cache_dir / "hf_datasets_cache"))
    os.environ.setdefault("TORCH_HOME", str(cache_dir / "torch_home"))

    log("Acquiring PACS at frozen Hugging Face revision " + PACS_REVISION)
    dataset = load_dataset("flwrlabs/pacs", split="train", revision=PACS_REVISION)
    if len(dataset) != 9991:
        raise RuntimeError(f"Frozen PACS row count mismatch: {len(dataset)} != 9991")
    label_names = list(dataset.features["label"].names)
    expected_labels = ["dog", "elephant", "giraffe", "guitar", "horse", "house", "person"]
    if label_names != expected_labels:
        raise RuntimeError(f"PACS label roster changed: {label_names}")

    weights = ResNet18_Weights.DEFAULT
    transform = weights.transforms()
    model = resnet18(weights=weights)
    model.fc = torch.nn.Identity()
    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model_hash = hash_torch_state_dict(model.state_dict())
    log(f"PACS frozen feature extractor: ResNet18 on {device}; state SHA256={model_hash}")

    living = {"dog", "elephant", "giraffe", "horse", "person"}

    class PACSDataset(Dataset):
        def __len__(self):
            return len(dataset)

        def __getitem__(self, index: int):
            row = dataset[int(index)]
            label_name = label_names[int(row["label"])]
            return transform(row["image"].convert("RGB")), int(label_name in living), str(row["domain"])

    batch_size = 128 if device.type == "cuda" else 32
    workers = 2 if device.type == "cuda" else 0
    loader = DataLoader(PACSDataset(), batch_size=batch_size, shuffle=False, num_workers=workers, pin_memory=device.type == "cuda")
    features, labels, domains = [], [], []
    with torch.inference_mode():
        for batch_index, (images, y, domain) in enumerate(loader, 1):
            output = model(images.to(device, non_blocking=device.type == "cuda")).cpu().numpy().astype("float32")
            features.append(output)
            labels.append(y.numpy().astype("int8"))
            domains.extend(list(domain))
            if batch_index == 1 or batch_index % 10 == 0 or batch_index == len(loader):
                log(f"PACS feature extraction: batch {batch_index}/{len(loader)}")
    F = np.concatenate(features)
    y = np.concatenate(labels)
    domain = np.asarray(domains)
    observed_domains = sorted(set(domain.tolist()))
    if observed_domains != ["art_painting", "cartoon", "photo", "sketch"]:
        raise RuntimeError(f"PACS domain roster changed: {observed_domains}")

    source_idx = np.flatnonzero(domain == "photo")
    train_idx, validation_idx = train_test_split(source_idx, test_size=0.25, random_state=SEED, stratify=y[source_idx])
    classifier = LogisticRegression(max_iter=3000, class_weight="balanced", random_state=SEED).fit(F[train_idx], y[train_idx])
    source_scores = classifier.predict_proba(F[validation_idx])[:, 1]
    threshold = choose_threshold(y[validation_idx], source_scores)

    target_data: Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    payload: Dict[str, Any] = {
        "source_features": F[validation_idx],
        "source_labels": y[validation_idx],
        "source_scores": source_scores,
        "threshold": np.asarray(threshold),
    }
    for target in EXPECTED_ROSTER["PACS"]["targets"]:
        idx = np.flatnonzero(domain == target)
        target_scores = classifier.predict_proba(F[idx])[:, 1]
        target_data[target] = (F[idx], y[idx], target_scores)
        payload[f"{target}_features"] = F[idx]
        payload[f"{target}_labels"] = y[idx]
        payload[f"{target}_scores"] = target_scores
    np.savez_compressed(cache_path, **payload)

    coefficient_payload = np.ascontiguousarray(classifier.coef_).tobytes() + np.ascontiguousarray(classifier.intercept_).tobytes()
    metadata = {
        "dataset": "flwrlabs/pacs",
        "dataset_revision": PACS_REVISION,
        "parquet_sha256_from_frozen_dataset_card": PACS_PARQUET_SHA256,
        "dataset_fingerprint": str(getattr(dataset, "_fingerprint", "unknown")),
        "rows": int(len(dataset)),
        "domains": observed_domains,
        "labels": label_names,
        "binary_task": "living_vs_artifact",
        "living_labels": sorted(living),
        "source_domain": "photo",
        "target_domains": EXPECTED_ROSTER["PACS"]["targets"],
        "feature_extractor": "torchvision ResNet18_Weights.DEFAULT; frozen penultimate representation",
        "feature_extractor_state_sha256": model_hash,
        "source_classifier_coefficient_sha256": sha256_bytes(coefficient_payload),
        "source_train_n": int(len(train_idx)),
        "source_validation_n": int(len(validation_idx)),
        "threshold": threshold,
        "cache_sha256": sha256_file(cache_path),
    }
    write_json(meta_path, metadata)
    return F[validation_idx], y[validation_idx], source_scores, threshold, target_data, metadata


def parse_review_file(path: Path, label: int) -> List[Tuple[str, int]]:
    text = path.read_text(encoding="latin1", errors="ignore")
    reviews = re.findall(r"<review_text>(.*?)</review_text>", text, flags=re.S | re.I)
    return [(re.sub(r"\s+", " ", review).strip(), label) for review in reviews if review.strip()]


def load_amazon_records() -> Tuple[Dict[str, List[Tuple[str, int]]], Dict[str, Any]]:
    cache_dir = DATA_ROOT / "amazon_mds"
    cache_dir.mkdir(parents=True, exist_ok=True)
    archive = cache_dir / "domain_sentiment_data.tar.gz"
    download_with_progress(AMAZON_URL, archive)
    extracted_marker = cache_dir / ".extracted_complete"
    if not extracted_marker.exists():
        log("Extracting official Amazon Multi-Domain Sentiment archive.")
        safe_extract_tar(archive, cache_dir)
        atomic_write_text(extracted_marker, utc_now())

    domains: Dict[str, List[Tuple[str, int]]] = {}
    for positive in cache_dir.rglob("positive.review"):
        domain = positive.parent.name.lower()
        negative = positive.parent / "negative.review"
        if negative.exists():
            domains[domain] = parse_review_file(positive, 1) + parse_review_file(negative, 0)
    mapping: Dict[str, List[Tuple[str, int]]] = {}
    for key, values in domains.items():
        if key == "books":
            mapping["books"] = values
        elif "dvd" in key:
            mapping["dvd"] = values
        elif "electronic" in key:
            mapping["electronics"] = values
        elif "kitchen" in key:
            mapping["kitchen"] = values
    expected = {"books", "dvd", "electronics", "kitchen"}
    if set(mapping) != expected:
        raise RuntimeError(f"Amazon domain mapping incomplete: {sorted(mapping)}")
    metadata = {
        "dataset": "Amazon Multi-Domain Sentiment Dataset v1",
        "official_url": AMAZON_URL,
        "archive_sha256": sha256_file(archive),
        "domains": {key: len(value) for key, value in mapping.items()},
        "source_domain": "books",
        "target_domains": EXPECTED_ROSTER["AMAZON_MDS"]["targets"],
    }
    return mapping, metadata


def load_or_build_amazon_system() -> Tuple["np.ndarray", "np.ndarray", "np.ndarray", float, Dict[str, Tuple["np.ndarray", "np.ndarray", "np.ndarray"]], Dict[str, Any]]:
    cache_dir = DATA_ROOT / "amazon_mds"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "StageU3C_Amazon_Frozen_System_Cache_v1.0.npz"
    meta_path = cache_dir / "StageU3C_Amazon_Frozen_System_Metadata_v1.0.json"
    if cache_path.exists() and meta_path.exists():
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        if metadata.get("cache_sha256") != sha256_file(cache_path):
            raise RuntimeError("Amazon frozen-system cache hash mismatch.")
        log("Reusing frozen Amazon source-system cache.")
        arr = np.load(cache_path, allow_pickle=False)
        targets = {
            target: (arr[f"{target}_features"], arr[f"{target}_labels"], arr[f"{target}_scores"])
            for target in EXPECTED_ROSTER["AMAZON_MDS"]["targets"]
        }
        return arr["source_features"], arr["source_labels"], arr["source_scores"], float(arr["threshold"]), targets, metadata

    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split

    records, acquisition_metadata = load_amazon_records()
    source = records["books"]
    texts = np.asarray([text for text, _ in source], dtype=object)
    labels = np.asarray([label for _, label in source], dtype=int)
    train_idx, validation_idx = train_test_split(np.arange(len(labels)), test_size=0.25, random_state=SEED, stratify=labels)
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=50000, sublinear_tf=True)
    X_train = vectorizer.fit_transform(texts[train_idx])
    X_validation = vectorizer.transform(texts[validation_idx])
    classifier = LogisticRegression(max_iter=3000, class_weight="balanced", random_state=SEED).fit(X_train, labels[train_idx])
    source_scores = classifier.predict_proba(X_validation)[:, 1]
    threshold = choose_threshold(labels[validation_idx], source_scores)
    n_components = min(256, X_train.shape[0] - 1, X_train.shape[1] - 1)
    svd = TruncatedSVD(n_components=n_components, random_state=SEED).fit(X_train)
    source_features = svd.transform(X_validation).astype("float32")

    target_data: Dict[str, Tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    payload: Dict[str, Any] = {
        "source_features": source_features,
        "source_labels": labels[validation_idx].astype("int8"),
        "source_scores": source_scores,
        "threshold": np.asarray(threshold),
    }
    for target in EXPECTED_ROSTER["AMAZON_MDS"]["targets"]:
        target_records = records[target]
        target_texts = np.asarray([text for text, _ in target_records], dtype=object)
        target_labels = np.asarray([label for _, label in target_records], dtype=int)
        X_target = vectorizer.transform(target_texts)
        target_features = svd.transform(X_target).astype("float32")
        target_scores = classifier.predict_proba(X_target)[:, 1]
        target_data[target] = (target_features, target_labels, target_scores)
        payload[f"{target}_features"] = target_features
        payload[f"{target}_labels"] = target_labels.astype("int8")
        payload[f"{target}_scores"] = target_scores
        log(f"Amazon frozen prediction cache built: {target} n={len(target_labels)}")
    np.savez_compressed(cache_path, **payload)

    vocab_payload = "\n".join(f"{token}\t{index}" for token, index in sorted(vectorizer.vocabulary_.items())).encode("utf-8")
    coefficient_payload = np.ascontiguousarray(classifier.coef_).tobytes() + np.ascontiguousarray(classifier.intercept_).tobytes()
    metadata = {
        **acquisition_metadata,
        "binary_task": "positive_vs_negative_sentiment",
        "representation": "source-only TF-IDF unigram/bigram; min_df=2; max_features=50000; sublinear_tf=True",
        "vocabulary_sha256": sha256_bytes(vocab_payload),
        "svd_components": int(n_components),
        "source_classifier_coefficient_sha256": sha256_bytes(coefficient_payload),
        "source_train_n": int(len(train_idx)),
        "source_validation_n": int(len(validation_idx)),
        "threshold": threshold,
        "cache_sha256": sha256_file(cache_path),
    }
    write_json(meta_path, metadata)
    return source_features, labels[validation_idx], source_scores, threshold, target_data, metadata


def balanced_auc_draws(y: "np.ndarray", p: "np.ndarray", budget: int, seed: int) -> "np.ndarray":
    from sklearn.metrics import roc_auc_score

    rng = np.random.default_rng(seed)
    positive = np.flatnonzero(y == 1)
    negative = np.flatnonzero(y == 0)
    n_positive = budget // 2
    n_negative = budget - n_positive
    if len(positive) < n_positive or len(negative) < n_negative:
        raise RuntimeError("Target does not contain enough examples for balanced AUC witness sampling.")
    values = np.empty(N_REP, dtype=float)
    for replicate in range(N_REP):
        indices = np.r_[rng.choice(positive, n_positive, replace=False), rng.choice(negative, n_negative, replace=False)]
        values[replicate] = roc_auc_score(y[indices], p[indices])
    return values


def natural_metric_draws(y: "np.ndarray", p: "np.ndarray", budget: int, threshold: float, seed: int) -> Dict[str, "np.ndarray"]:
    from sklearn.metrics import average_precision_score, balanced_accuracy_score, brier_score_loss, log_loss

    rng = np.random.default_rng(seed)
    outputs = {key: np.full(N_REP, np.nan, dtype=float) for key in ["auprc", "balanced_accuracy", "brier", "log_loss"]}
    for replicate in range(N_REP):
        indices = rng.choice(len(y), budget, replace=False)
        sample_y = y[indices]
        sample_p = np.clip(p[indices], 1e-8, 1 - 1e-8)
        outputs["brier"][replicate] = brier_score_loss(sample_y, sample_p)
        outputs["log_loss"][replicate] = log_loss(sample_y, sample_p, labels=[0, 1])
        if len(np.unique(sample_y)) == 2:
            outputs["auprc"][replicate] = average_precision_score(sample_y, sample_p)
            outputs["balanced_accuracy"][replicate] = balanced_accuracy_score(sample_y, sample_p >= threshold)
    return outputs


def target_witness_results(dataset: str, target: str, target_features: "np.ndarray", y: "np.ndarray", p: "np.ndarray", threshold: float, source_features: "np.ndarray", source_scores: "np.ndarray", transport_auc: float) -> Tuple[Dict[str, Any], Dict[str, Any], "pd.DataFrame", "pd.DataFrame"]:
    truth = full_metrics(y, p, threshold)
    descriptor = descriptors(source_features, source_scores, target_features, p)
    panel_rows: List[Dict[str, Any]] = []
    replicate_rows: List[Dict[str, Any]] = []
    for budget in BUDGETS:
        auc = balanced_auc_draws(y, p, budget, stable_seed(SEED, dataset, target, budget, "auc"))
        natural = natural_metric_draws(y, p, budget, threshold, stable_seed(SEED, dataset, target, budget, "natural"))
        fusion = FUSION_TRANSPORT_WEIGHT * transport_auc + FUSION_DIRECT_WEIGHT * auc
        arrays = {"auc": auc, "auc_fusion": fusion, **natural}
        for metric_name, values in arrays.items():
            metric = "auc" if metric_name == "auc_fusion" else metric_name
            evidence = "fusion" if metric_name == "auc_fusion" else "direct"
            truth_value = truth[metric]
            valid = values[np.isfinite(values)]
            panel_rows.append(
                {
                    "dataset": dataset,
                    "target": target,
                    "metric": metric,
                    "evidence": evidence,
                    "budget": budget,
                    "mae": float(np.median(np.abs(valid - truth_value))),
                    "mean_ae": float(np.mean(np.abs(valid - truth_value))),
                    "replicates": int(len(valid)),
                    "invalid_replicates": int(len(values) - len(valid)),
                    "truth": truth_value,
                }
            )
        for replicate in range(N_REP):
            replicate_rows.append(
                {
                    "dataset": dataset,
                    "target": target,
                    "budget": budget,
                    "replicate": replicate,
                    "auc_direct": float(auc[replicate]),
                    "auc_fusion": float(fusion[replicate]),
                }
            )
    true_row = {"dataset": dataset, "target": target, "n": int(len(y)), "prevalence": float(y.mean()), "threshold": threshold, **truth}
    descriptor_row = {
        "dataset": dataset,
        "target": target,
        "transport_auc": transport_auc,
        **dict(zip(["feature_mean_shift", "variance_log_ratio", "score_shift", "entropy_shift", "confidence_shift"], descriptor)),
    }
    return true_row, descriptor_row, pd.DataFrame(panel_rows), pd.DataFrame(replicate_rows)


def fit_target_alphas(panel: "pd.DataFrame") -> "pd.DataFrame":
    rows: List[Dict[str, Any]] = []
    for (dataset, target, metric, evidence), group in panel.groupby(["dataset", "target", "metric", "evidence"]):
        group = group.sort_values("budget")
        if len(group) < 4 or (group["mae"] <= 0).any():
            continue
        x = np.log(group["budget"].to_numpy(float) / 8.0)
        y = np.log(group["mae"].to_numpy(float))
        alpha = -float(np.polyfit(x, y, 1)[0])
        rows.append({"dataset": dataset, "target": target, "metric": metric, "evidence": evidence, "alpha": alpha})
    return pd.DataFrame(rows)


def monotone_label_leverage(panel: "pd.DataFrame") -> "pd.DataFrame":
    rows: List[Dict[str, Any]] = []
    auc = panel[panel["metric"].eq("auc")].pivot_table(index=["dataset", "target", "budget"], columns="evidence", values="mae").reset_index()
    for (dataset, target), group in auc.groupby(["dataset", "target"]):
        group = group.sort_values("budget")
        budgets = group["budget"].to_numpy(float)
        direct = group["direct"].to_numpy(float)
        fusion = group["fusion"].to_numpy(float)
        direct_monotone = np.minimum.accumulate(direct)
        xp = np.log(direct_monotone[::-1].clip(min=1e-12))
        fp = np.log(budgets[::-1])
        order = np.argsort(xp)
        xp, fp = xp[order], fp[order]
        unique_xp, unique_indices = np.unique(xp, return_index=True)
        unique_fp = fp[unique_indices]
        for budget, fusion_error in zip(budgets, fusion):
            equivalent = float(np.exp(np.interp(np.log(max(fusion_error, 1e-12)), unique_xp, unique_fp, left=np.log(budgets.max()), right=np.log(budgets.min()))))
            equivalent = float(np.clip(equivalent, budgets.min(), budgets.max()))
            rows.append(
                {
                    "dataset": dataset,
                    "target": target,
                    "budget": int(budget),
                    "direct_mae": float(direct[group["budget"].to_numpy() == budget][0]),
                    "fusion_mae": float(fusion[group["budget"].to_numpy() == budget][0]),
                    "equivalent_direct_budget": equivalent,
                    "leverage": equivalent / budget,
                }
            )
    return pd.DataFrame(rows)


def class_trajectory_predictions(panel: "pd.DataFrame", envelopes: "pd.DataFrame") -> "pd.DataFrame":
    rows: List[Dict[str, Any]] = []
    for (dataset, target, metric, evidence), group in panel.groupby(["dataset", "target", "metric", "evidence"]):
        group = group.sort_values("budget")
        envelope_evidence = "fusion_0.6_transport_0.4_direct" if evidence == "fusion" else "direct"
        match = envelopes[
            envelopes["dataset"].eq(dataset)
            & envelopes["target_domain"].eq(target)
            & envelopes["metric"].eq(metric)
            & envelopes["evidence"].eq(envelope_evidence)
        ]
        if len(match) != 1:
            raise RuntimeError(f"Prediction-envelope match failure for {(dataset, target, metric, evidence)}: {len(match)}")
        alpha = float(match.iloc[0]["predicted_alpha_center"])
        anchor = float(group.loc[group["budget"].eq(8), "mae"].iloc[0])
        for _, row in group[group["budget"].gt(8)].iterrows():
            class_prediction = anchor * (float(row["budget"]) / 8.0) ** (-alpha)
            rootn_prediction = anchor * (float(row["budget"]) / 8.0) ** (-0.5)
            rows.append(
                {
                    "dataset": dataset,
                    "target": target,
                    "metric": metric,
                    "evidence": evidence,
                    "budget": int(row["budget"]),
                    "truth_mae": float(row["mae"]),
                    "predicted_alpha": alpha,
                    "class_pred": class_prediction,
                    "rootn_pred": rootn_prediction,
                    "class_abs_error": abs(float(row["mae"]) - class_prediction),
                    "rootn_abs_error": abs(float(row["mae"]) - rootn_prediction),
                }
            )
    return pd.DataFrame(rows)


def evaluate_gates(alpha_df: "pd.DataFrame", envelopes: "pd.DataFrame", predictions: "pd.DataFrame", leverage: "pd.DataFrame", auth: Mapping[str, Any], acquired_targets: Sequence[Tuple[str, str]]) -> "pd.DataFrame":
    rows: List[Dict[str, Any]] = []

    auc_observed = alpha_df[(alpha_df["metric"].eq("auc")) & (alpha_df["evidence"].eq("direct"))].copy()
    auc_envelopes = envelopes[(envelopes["metric"].eq("auc")) & (envelopes["evidence"].eq("direct"))][
        ["dataset", "target_domain", "predicted_alpha_lower", "predicted_alpha_upper"]
    ]
    auc_observed = auc_observed.merge(auc_envelopes, left_on=["dataset", "target"], right_on=["dataset", "target_domain"], how="left", validate="one_to_one")
    auc_observed["inside"] = (auc_observed["alpha"] >= auc_observed["predicted_alpha_lower"]) & (auc_observed["alpha"] <= auc_observed["predicted_alpha_upper"])
    auc_inside = int(auc_observed["inside"].sum())

    regular_metrics = ["balanced_accuracy", "brier", "log_loss"]
    regular_observed = alpha_df[(alpha_df["metric"].isin(regular_metrics)) & (alpha_df["evidence"].eq("direct"))].copy()
    regular_envelopes = envelopes[(envelopes["metric"].isin(regular_metrics)) & (envelopes["evidence"].eq("direct"))][
        ["dataset", "target_domain", "metric", "predicted_alpha_lower", "predicted_alpha_upper"]
    ]
    regular_observed = regular_observed.merge(regular_envelopes, left_on=["dataset", "target", "metric"], right_on=["dataset", "target_domain", "metric"], how="left", validate="one_to_one")
    regular_observed["inside"] = (regular_observed["alpha"] >= regular_observed["predicted_alpha_lower"]) & (regular_observed["alpha"] <= regular_observed["predicted_alpha_upper"])
    regular_inside = int(regular_observed["inside"].sum())

    class_error = float(predictions["class_abs_error"].mean())
    rootn_error = float(predictions["rootn_abs_error"].mean())
    gain = float(1 - class_error / rootn_error) if rootn_error > 0 else float("nan")
    primary = leverage[leverage["budget"].eq(32)].copy()
    median_leverage = float(primary["leverage"].median())
    positive_targets = int((primary["leverage"] > 1).sum())
    expected_pairs = sorted((dataset, target) for dataset, item in EXPECTED_ROSTER.items() for target in item["targets"])
    observed_pairs = sorted(acquired_targets)

    rows.extend(
        [
            {"gate": "execution_authorisation_integrity", "passed": True, "observed": auth["authorisation_record_sha256"]},
            {"gate": "parent_u3a_integrity", "passed": auth["u3a_final_record_sha256"] == U3A_FINAL_SHA256, "observed": auth["u3a_final_record_sha256"]},
            {"gate": "u3b_preregistration_integrity", "passed": auth["u3b_preregistration_sha256"] == U3B_PREREGISTRATION_SHA256, "observed": auth["u3b_preregistration_sha256"]},
            {"gate": "prediction_envelope_integrity", "passed": auth["prediction_envelope_sha256"] == PREDICTION_ENVELOPE_SHA256, "observed": auth["prediction_envelope_sha256"]},
            {"gate": "reserve_roster_complete_and_unchanged", "passed": observed_pairs == expected_pairs, "observed": f"observed={observed_pairs}; expected={expected_pairs}"},
            {"gate": "direct_auc_class_containment", "passed": auc_inside >= 4, "observed": f"{auc_inside}/6"},
            {"gate": "regular_metric_class_containment", "passed": regular_inside >= 12, "observed": f"{regular_inside}/{len(regular_observed)}"},
            {"gate": "class_law_prediction_gain", "passed": gain >= 0.10, "observed": f"gain={gain:.6f}; class={class_error:.6f}; rootn={rootn_error:.6f}"},
            {"gate": "fusion_median_label_leverage", "passed": median_leverage >= 1.25, "observed": f"median={median_leverage:.6f}"},
            {"gate": "fusion_positive_targets", "passed": positive_targets >= 4, "observed": f"{positive_targets}/6"},
            {"gate": "new_blind_accessed", "passed": True, "observed": True},
            {"gate": "stage12_authorised", "passed": True, "observed": False},
        ]
    )
    return pd.DataFrame(rows)


def make_figures(alpha_df: "pd.DataFrame", envelopes: "pd.DataFrame", predictions: "pd.DataFrame", leverage: "pd.DataFrame") -> None:
    import matplotlib.pyplot as plt

    figure_root = OUT_ROOT / SUB["figures"]
    figure_root.mkdir(parents=True, exist_ok=True)

    observed = alpha_df[alpha_df["evidence"].eq("direct")].copy()
    observed["key"] = observed["dataset"] + ":" + observed["target"] + ":" + observed["metric"]
    observed = observed.sort_values(["metric", "dataset", "target"]).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(10, max(5, len(observed) * 0.18)))
    ax.scatter(observed["alpha"], np.arange(len(observed)), s=18)
    ax.axvline(0.5, linestyle="--", linewidth=1)
    ax.set_yticks(np.arange(len(observed)))
    ax.set_yticklabels(observed["key"], fontsize=6)
    ax.set_xlabel("Observed evidence-scaling exponent")
    ax.set_title("Prospective reserve exponents")
    fig.tight_layout()
    fig.savefig(figure_root / "StageU3C_Observed_Exponent_Map_v1.0.pdf")
    fig.savefig(figure_root / "StageU3C_Observed_Exponent_Map_v1.0.png", dpi=300)
    plt.close(fig)

    summary = predictions.groupby(["metric", "evidence"])[["class_abs_error", "rootn_abs_error"]].mean().reset_index()
    x = np.arange(len(summary))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    width = 0.38
    ax.bar(x - width / 2, summary["class_abs_error"], width, label="class law")
    ax.bar(x + width / 2, summary["rootn_abs_error"], width, label="root-n")
    ax.set_xticks(x)
    ax.set_xticklabels(summary["metric"] + "/" + summary["evidence"], rotation=45, ha="right")
    ax.set_ylabel("Mean absolute trajectory-prediction error")
    ax.legend()
    fig.tight_layout()
    fig.savefig(figure_root / "StageU3C_Class_Law_Versus_RootN_v1.0.pdf")
    fig.savefig(figure_root / "StageU3C_Class_Law_Versus_RootN_v1.0.png", dpi=300)
    plt.close(fig)

    primary = leverage[leverage["budget"].eq(32)].sort_values(["dataset", "target"])
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.bar(primary["dataset"] + ":" + primary["target"], primary["leverage"])
    ax.axhline(1.0, linestyle="--", linewidth=1)
    ax.axhline(1.25, linestyle=":", linewidth=1)
    ax.set_ylabel("Direct-equivalent label leverage at budget 32")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(figure_root / "StageU3C_Fusion_Label_Leverage_v1.0.pdf")
    fig.savefig(figure_root / "StageU3C_Fusion_Label_Leverage_v1.0.png", dpi=300)
    plt.close(fig)


def build_release_manifest_and_zip() -> Tuple[Path, str, Path]:
    manifest_path = OUT_ROOT / "StageU3C_Durable_Commit_Manifest_v1.0.csv"
    zip_path = OUT_ROOT / "StageU3C_Canonical_Records_v1.0.zip"
    zip_commit_path = OUT_ROOT / "StageU3C_Canonical_Zip_Commit_v1.0.json"

    excluded = {manifest_path.resolve(), zip_path.resolve(), zip_commit_path.resolve()}
    files = sorted(path for path in OUT_ROOT.rglob("*") if path.is_file() and path.resolve() not in excluded and not path.name.endswith(".tmp"))
    rows = [{"relative_path": str(path.relative_to(OUT_ROOT)), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in files]
    save_df(manifest_path, pd.DataFrame(rows))

    files_for_zip = files + [manifest_path]
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files_for_zip:
            archive.write(path, arcname=str(path.relative_to(OUT_ROOT)))
    zip_sha = sha256_file(zip_path)
    write_json(zip_commit_path, {"canonical_zip": zip_path.name, "canonical_zip_sha256": zip_sha, "files": len(files_for_zip), "created_at_utc": utc_now()})
    return zip_path, zip_sha, manifest_path


def main() -> None:
    started = time.time()
    ensure_dirs()
    update_progress("STARTING")
    ensure_dependencies()
    import_runtime_packages()

    auth = require_authorisation()
    write_json(OUT_ROOT / SUB["integrity"] / "StageU3C_Execution_Authorisation_Record_v1.0.json", auth)
    execution_identity = {
        "pipeline_sha256": os.environ.get("CMDO_U3C_PIPELINE_SHA256"),
        "authorisation_record_sha256": auth["authorisation_record_sha256"],
        "u3a_final_record_sha256": U3A_FINAL_SHA256,
        "u3b_preregistration_sha256": U3B_PREREGISTRATION_SHA256,
        "prediction_envelope_sha256": PREDICTION_ENVELOPE_SHA256,
    }
    identity_path = OUT_ROOT / SUB["integrity"] / "StageU3C_Execution_Identity_v1.0.json"
    if identity_path.exists():
        existing_identity = json.loads(identity_path.read_text(encoding="utf-8"))
        if existing_identity != execution_identity:
            raise RuntimeError("Existing U3C target cache belongs to a different execution identity; outcome-blind reuse is prohibited.")
    else:
        write_json(identity_path, execution_identity)
    environment = {
        "utc_started": utc_now(),
        "python": sys.version,
        "platform": platform.platform(),
        "pipeline_sha256": os.environ.get("CMDO_U3C_PIPELINE_SHA256"),
    }
    try:
        import torch
        environment.update({"torch": torch.__version__, "cuda_available": bool(torch.cuda.is_available()), "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None})
    except Exception as exc:
        environment["torch_error"] = str(exc)
    write_json(OUT_ROOT / SUB["integrity"] / "StageU3C_Runtime_Environment_v1.0.json", environment)
    log(f"Authorisation verified. Compute backend: {'cuda' if environment.get('cuda_available') else 'cpu'}")

    update_progress("FITTING_FROZEN_TRANSPORT_MAPPING")
    scaler, transport_model, u2_descriptors = fit_transport_mapping()
    save_df(OUT_ROOT / SUB["source"] / "StageU3C_U2_Transport_Training_Descriptors_v1.0.csv", u2_descriptors)

    update_progress("PREPARING_PACS_SOURCE_SYSTEM")
    pacs = load_or_build_pacs_system()
    update_progress("PREPARING_AMAZON_SOURCE_SYSTEM")
    amazon = load_or_build_amazon_system()
    systems = [("PACS", *pacs[:5], pacs[5]), ("AMAZON_MDS", *amazon[:5], amazon[5])]

    acquisition_records = {"PACS": pacs[5], "AMAZON_MDS": amazon[5]}
    write_json(OUT_ROOT / SUB["acquisition"] / "StageU3C_Reserve_Acquisition_Record_v1.0.json", acquisition_records)

    true_frames, descriptor_frames, panel_frames, replicate_frames = [], [], [], []
    acquired_targets: List[Tuple[str, str]] = []
    target_cache_root = OUT_ROOT / SUB["witness"] / "target_level_cache_v1.0"
    target_cache_root.mkdir(parents=True, exist_ok=True)

    for dataset, source_features, source_labels, source_scores, threshold, targets, _metadata in systems:
        for target in EXPECTED_ROSTER[dataset]["targets"]:
            acquired_targets.append((dataset, target))
            true_path = target_cache_root / f"{dataset}_{target}_true.json"
            descriptor_path = target_cache_root / f"{dataset}_{target}_descriptor.json"
            panel_path = target_cache_root / f"{dataset}_{target}_panel.csv"
            replicate_path = target_cache_root / f"{dataset}_{target}_auc_replicates.csv"
            if all(path.exists() for path in [true_path, descriptor_path, panel_path, replicate_path]):
                log(f"Reusing completed target witness cache: {dataset}/{target}")
                true_frames.append(pd.DataFrame([json.loads(true_path.read_text(encoding="utf-8"))]))
                descriptor_frames.append(pd.DataFrame([json.loads(descriptor_path.read_text(encoding="utf-8"))]))
                panel_frames.append(pd.read_csv(panel_path))
                replicate_frames.append(pd.read_csv(replicate_path))
                continue

            target_features, target_labels, target_scores = targets[target]
            descriptor = descriptors(source_features, source_scores, target_features, target_scores)
            transport_auc = float(np.clip(transport_model.predict(scaler.transform(descriptor.reshape(1, -1)))[0], 0.5, 1.0))
            log(f"Computing prospective witnesses: {dataset}/{target}; n={len(target_labels)}; transport_auc={transport_auc:.6f}")
            true_row, descriptor_row, panel_df, replicate_df = target_witness_results(
                dataset,
                target,
                target_features,
                target_labels,
                target_scores,
                threshold,
                source_features,
                source_scores,
                transport_auc,
            )
            write_json(true_path, true_row)
            write_json(descriptor_path, descriptor_row)
            save_df(panel_path, panel_df)
            save_df(replicate_path, replicate_df)
            true_frames.append(pd.DataFrame([true_row]))
            descriptor_frames.append(pd.DataFrame([descriptor_row]))
            panel_frames.append(panel_df)
            replicate_frames.append(replicate_df)
            update_progress("TARGET_COMPLETED", dataset=dataset, target=target, completed_targets=len(true_frames), total_targets=6)

    true_df = pd.concat(true_frames, ignore_index=True)
    descriptor_df = pd.concat(descriptor_frames, ignore_index=True)
    panel = pd.concat(panel_frames, ignore_index=True)
    replicates = pd.concat(replicate_frames, ignore_index=True)
    save_df(OUT_ROOT / SUB["predictions"] / "StageU3C_Target_True_Metrics_v1.0.csv", true_df)
    save_df(OUT_ROOT / SUB["predictions"] / "StageU3C_Target_Shift_Descriptors_And_Transport_v1.0.csv", descriptor_df)
    save_df(OUT_ROOT / SUB["witness"] / "StageU3C_Target_Budget_MAE_v1.0.csv", panel)
    save_df(OUT_ROOT / SUB["fusion"] / "StageU3C_AUC_Direct_Fusion_Replicates_v1.0.csv", replicates)

    update_progress("EVALUATING_PROSPECTIVE_GATES")
    envelopes = pd.read_csv(ENVELOPE_PATH)
    alpha_df = fit_target_alphas(panel)
    leverage_df = monotone_label_leverage(panel)
    prediction_df = class_trajectory_predictions(panel, envelopes)
    save_df(OUT_ROOT / SUB["classes"] / "StageU3C_Target_Exponents_v1.0.csv", alpha_df)
    save_df(OUT_ROOT / SUB["classes"] / "StageU3C_Prospective_Trajectory_Predictions_v1.0.csv", prediction_df)
    save_df(OUT_ROOT / SUB["fusion"] / "StageU3C_Label_Leverage_v1.0.csv", leverage_df)

    gates = evaluate_gates(alpha_df, envelopes, prediction_df, leverage_df, auth, acquired_targets)
    save_df(OUT_ROOT / SUB["decision"] / "StageU3C_Frozen_Prospective_Gates_v1.0.csv", gates)
    make_figures(alpha_df, envelopes, prediction_df, leverage_df)

    integrity_gate_names = {
        "execution_authorisation_integrity",
        "parent_u3a_integrity",
        "u3b_preregistration_integrity",
        "prediction_envelope_integrity",
        "reserve_roster_complete_and_unchanged",
    }
    science_gate_names = {
        "direct_auc_class_containment",
        "regular_metric_class_containment",
        "class_law_prediction_gain",
        "fusion_median_label_leverage",
        "fusion_positive_targets",
    }
    integrity_supported = bool(gates[gates["gate"].isin(integrity_gate_names)]["passed"].all())
    science_supported = bool(gates[gates["gate"].isin(science_gate_names)]["passed"].all())
    supported = integrity_supported and science_supported
    decision = (
        "SEAL_STAGEU3C_PROSPECTIVE_RESERVE_SUPPORTED_NATURE_ROUTE_EVIDENCE_COMPLETE_STAGE12_STILL_PROHIBITED"
        if supported
        else "SEAL_STAGEU3C_PROSPECTIVE_RESERVE_PARTIAL_OR_FAILED_RETAIN_ALL_RESULTS_REROUTE_STAGE12_PROHIBITED"
    )

    primary = leverage_df[leverage_df["budget"].eq(32)]
    complete: Dict[str, Any] = {
        "stage": "StageU3C",
        "version": "v1.0",
        "decision": decision,
        "prospective_reserve_supported": supported,
        "integrity_supported": integrity_supported,
        "science_supported": science_supported,
        "targets": 6,
        "families": 2,
        "metrics": EXPECTED_METRICS,
        "budgets": BUDGETS,
        "replicates": N_REP,
        "direct_auc_targets_inside_envelope": str(gates.loc[gates.gate.eq("direct_auc_class_containment"), "observed"].iloc[0]),
        "regular_pairs_inside_envelope": str(gates.loc[gates.gate.eq("regular_metric_class_containment"), "observed"].iloc[0]),
        "class_law_prediction_gain": str(gates.loc[gates.gate.eq("class_law_prediction_gain"), "observed"].iloc[0]),
        "fusion_median_label_leverage_budget32": float(primary["leverage"].median()),
        "fusion_positive_targets_budget32": int((primary["leverage"] > 1).sum()),
        "new_blind_accessed": True,
        "new_blind_authorised": True,
        "stage12_authorised": False,
        "parent_u3a_final_sha256": U3A_FINAL_SHA256,
        "u3b_preregistration_sha256": U3B_PREREGISTRATION_SHA256,
        "prediction_envelope_sha256": PREDICTION_ENVELOPE_SHA256,
        "pipeline_sha256": os.environ.get("CMDO_U3C_PIPELINE_SHA256"),
        "runtime_seconds": float(time.time() - started),
    }
    stable_record = {key: value for key, value in complete.items() if key != "runtime_seconds"}
    payload = json.dumps(stable_record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    complete["final_record_sha256"] = hashlib.sha256(payload).hexdigest()
    write_json(OUT_ROOT / SUB["decision"] / "StageU3C_Complete_v1.0.json", complete)

    manuscript = f"""# Stage U3C prospective reserve result\n\nDecision: `{decision}`\n\nProspective reserve supported: **{supported}**.\n\nSix untouched target environments spanning PACS visual style shift and Amazon text-domain shift were evaluated under the frozen U3B protocol. No target was removed, replaced, or retuned after outcome access.\n\nFinal record SHA-256: `{complete['final_record_sha256']}`\n"""
    atomic_write_text(OUT_ROOT / SUB["decision"] / "StageU3C_Manuscript_Insert_v1.0.md", manuscript)

    zip_path, zip_sha, manifest_path = build_release_manifest_and_zip()
    update_progress("COMPLETE", decision=decision, final_record_sha256=complete["final_record_sha256"], canonical_zip_sha256=zip_sha)

    print("\n========== STAGE U3C COMPLETE ==========")
    print("Decision:", decision)
    print("Prospective reserve supported:", supported)
    print("Targets / families / metrics:", 6, 2, 5)
    print("Reserve execution authorised:", True)
    print("New blind accessed:", True)
    print("Stage 12 authorised:", False)
    print("Final record SHA256:", complete["final_record_sha256"])
    print("Canonical ZIP SHA256:", zip_sha)
    print("Committed to:", OUT_ROOT)
    print(gates.to_string(index=False))


if __name__ == "__main__":
    main()
