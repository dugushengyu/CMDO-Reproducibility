#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMDO Stage U5B — Sentinel-Observability Prospective Reserve v1.0

This is a new prospective reserve following transparent Stage U4D development.
No U4 confirmatory target is reused. Target outcomes are used only after the
target roster, source-only models, label-free descriptors, transport estimates,
risk estimates, score hashes, and target sample counts have been sealed.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
import platform
import random
import shutil
import sys
import time
import warnings
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from scipy import ndimage
from scipy.stats import spearmanr, wasserstein_distance
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import LeaveOneOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.random_projection import GaussianRandomProjection, SparseRandomProjection
from skimage.feature import hog


PROJECT = "Cross-Modal_Diagnostic_Observability"
STAGE = "StageU5B_Sentinel_Observability_Prospective_Reserve_v1.0"

EXPECTED_U4D_FINAL_SHA256 = (
    "153c79ff42861d375f107df3d9b64aa5b65400610213cb3fe17b85b9fa22972e"
)
EXPECTED_U4C_FINAL_SHA256 = (
    "2828095fa9ec611738d986541a4b29ff390f8874493d40b5a6a6a65cf38b704b"
)
EXPECTED_U4C_CANONICAL_ZIP_SHA256 = (
    "6faadd171fd0e1a3d10897494a878a6b716f195bed500220952a09d087bea244"
)

BUDGETS = np.asarray([8, 16, 32, 64, 128], dtype=int)
N_REPLICATES = 200
SEED = 20260724

# U4D-transparent frozen sentinel parameters.
SENTINEL_BIAS_COEFFICIENT = 0.5
SENTINEL_RISK_COEFFICIENT = 8.0
SENTINEL_MAX_WEIGHT = 0.35

# Frozen label-free transport model inherited as a baseline only.
BIAS_FRACTION = 1.0
RESIDUAL_QUANTILE = 0.8
SUPPORT_SCALE = 4.0
LABEL_FREE_MAX_WEIGHT = 0.5
LABEL_FREE_DISAGREEMENT_SCALE = 2.0

DESCRIPTOR_COLUMNS = [
    "feature_mean_shift",
    "variance_log_ratio",
    "score_shift",
    "entropy_shift",
    "confidence_shift",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def locate_project_root() -> Path:
    candidates = [
        Path("/content/drive/MyDrive") / PROJECT,
        Path("/content/drive/Shareddrives") / PROJECT,
    ]
    for path in candidates:
        if path.exists():
            return path
    matches = list(Path("/content/drive").rglob(PROJECT))
    matches = [path for path in matches if path.is_dir()]
    if len(matches) == 1:
        return matches[0]
    raise FileNotFoundError(f"Cannot uniquely locate {PROJECT}: {matches}")


def deterministic_indices(n: int, limit: int, seed: int) -> np.ndarray:
    if n <= limit:
        return np.arange(n, dtype=int)
    rng = np.random.default_rng(seed)
    return np.sort(rng.choice(n, size=limit, replace=False))


def entropy_binary(scores: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(scores, dtype=float), 1e-7, 1 - 1e-7)
    return -(p * np.log(p) + (1 - p) * np.log(1 - p))


def make_projection(x_source: Any, seed: int, n_components: int = 24):
    n_features = int(x_source.shape[1])
    n_components = max(2, min(n_components, n_features))
    if hasattr(x_source, "tocsr"):
        projector = SparseRandomProjection(
            n_components=n_components,
            dense_output=True,
            random_state=seed,
        )
    else:
        projector = GaussianRandomProjection(
            n_components=n_components,
            random_state=seed,
        )
    projector.fit(x_source)
    return projector


def descriptor(
    source_z: np.ndarray,
    source_scores: np.ndarray,
    target_z: np.ndarray,
    target_scores: np.ndarray,
) -> Dict[str, float]:
    source_z = np.asarray(source_z, dtype=float)
    target_z = np.asarray(target_z, dtype=float)
    source_scores = np.asarray(source_scores, dtype=float)
    target_scores = np.asarray(target_scores, dtype=float)
    ms, mt = source_z.mean(axis=0), target_z.mean(axis=0)
    vs, vt = source_z.var(axis=0), target_z.var(axis=0)
    return {
        "feature_mean_shift": float(np.linalg.norm(mt - ms) / math.sqrt(len(ms))),
        "variance_log_ratio": float(
            np.mean(np.abs(np.log((vt + 1e-6) / (vs + 1e-6))))
        ),
        "score_shift": float(wasserstein_distance(source_scores, target_scores)),
        "entropy_shift": float(
            abs(
                entropy_binary(source_scores).mean()
                - entropy_binary(target_scores).mean()
            )
        ),
        "confidence_shift": float(
            abs(
                np.abs(source_scores - 0.5).mean()
                - np.abs(target_scores - 0.5).mean()
            )
        ),
    }


def fit_transport(
    family: str,
    source_z: np.ndarray,
    source_scores: np.ndarray,
    pseudo_envs: List[Dict[str, Any]],
    targets: Dict[str, Dict[str, Any]],
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    pseudo_rows: List[dict] = []
    for env in pseudo_envs:
        d = descriptor(source_z, source_scores, env["z"], env["scores"])
        auc = float(roc_auc_score(env["y"], env["scores"]))
        pseudo_rows.append(
            {"family": family, "environment": env["name"], **d, "auc": auc}
        )
    pseudo = pd.DataFrame(pseudo_rows)
    if len(pseudo) < 6:
        raise RuntimeError(f"Too few pseudo-environments for {family}: {len(pseudo)}")

    X = pseudo[DESCRIPTOR_COLUMNS].to_numpy(dtype=float)
    y = pseudo["auc"].to_numpy(dtype=float)
    scaler = StandardScaler().fit(X)
    Xs = scaler.transform(X)
    alphas = [0.01, 0.1, 1.0, 10.0, 100.0]
    loo = LeaveOneOut()
    best_alpha, best_mae, best_pred = None, math.inf, None
    for alpha in alphas:
        pred = np.zeros(len(y), dtype=float)
        for train_idx, val_idx in loo.split(Xs):
            model = Ridge(alpha=alpha).fit(Xs[train_idx], y[train_idx])
            pred[val_idx] = model.predict(Xs[val_idx])
        mae = float(np.mean(np.abs(pred - y)))
        if mae < best_mae:
            best_alpha, best_mae, best_pred = alpha, mae, pred
    assert best_alpha is not None and best_pred is not None
    model = Ridge(alpha=best_alpha).fit(Xs, y)

    residual = best_pred - y
    bias = float(np.median(residual))
    centred = residual - bias
    residual_scale = float(
        max(np.quantile(np.abs(centred), RESIDUAL_QUANTILE), 0.015)
    )

    target_rows: List[dict] = []
    for name, item in targets.items():
        d = descriptor(source_z, source_scores, item["z"], item["scores"])
        vector = np.asarray([[d[c] for c in DESCRIPTOR_COLUMNS]], dtype=float)
        vector_s = scaler.transform(vector)[0]
        min_distance = float(
            np.min(np.sqrt(np.sum((Xs - vector_s.reshape(1, -1)) ** 2, axis=1)))
        )
        support_gate = float(
            math.exp(-0.5 * (min_distance / SUPPORT_SCALE) ** 2)
        )
        raw_pred = float(model.predict(vector_s.reshape(1, -1))[0])
        corrected = float(np.clip(raw_pred - BIAS_FRACTION * bias, 0.0, 1.0))
        transport_risk = float(
            (residual_scale / max(support_gate, 0.05)) ** 2
        )
        target_rows.append(
            {
                "family": family,
                "target": name,
                **d,
                "transport_auc_raw": raw_pred,
                "transport_auc": corrected,
                "transport_cv_bias": bias,
                "transport_cv_residual_scale": residual_scale,
                "support_distance": min_distance,
                "support_gate": support_gate,
                "transport_risk_proxy": transport_risk,
                "target_score_sha256": sha256_bytes(
                    np.asarray(item["scores"], dtype=np.float64).tobytes()
                ),
                "n_target_unlabelled": int(len(item["scores"])),
            }
        )
    model_record = {
        "family": family,
        "alpha": best_alpha,
        "loo_mae": best_mae,
        "bias": bias,
        "residual_scale": residual_scale,
        "scaler_mean": scaler.mean_.tolist(),
        "scaler_scale": scaler.scale_.tolist(),
        "ridge_coef": model.coef_.tolist(),
        "ridge_intercept": float(model.intercept_),
        "pseudo_environment_count": int(len(pseudo)),
    }
    return pseudo, pd.DataFrame(target_rows), model_record


def delong_auc_variance(y: np.ndarray, scores: np.ndarray) -> Tuple[float, float]:
    y = np.asarray(y, dtype=int)
    scores = np.asarray(scores, dtype=float)
    pos = scores[y == 1]
    neg = scores[y == 0]
    if len(pos) < 2 or len(neg) < 2:
        raise ValueError("DeLong variance requires at least two positives and negatives.")
    phi = (pos[:, None] > neg[None, :]).astype(float)
    phi += 0.5 * (pos[:, None] == neg[None, :])
    auc = float(phi.mean())
    v10 = phi.mean(axis=1)
    v01 = phi.mean(axis=0)
    variance = float(
        np.var(v10, ddof=1) / len(pos) + np.var(v01, ddof=1) / len(neg)
    )
    return auc, max(variance, 1e-10)


def label_free_estimate(
    direct_auc: float,
    direct_var: float,
    transport_auc: float,
    transport_risk: float,
    support_gate: float,
) -> Tuple[float, float]:
    base_weight = direct_var / (direct_var + transport_risk + 1e-12)
    denom = LABEL_FREE_DISAGREEMENT_SCALE * math.sqrt(
        direct_var + transport_risk + 1e-12
    )
    gate = math.exp(
        -0.5 * ((direct_auc - transport_auc) / max(denom, 1e-12)) ** 2
    )
    weight = min(
        LABEL_FREE_MAX_WEIGHT,
        base_weight * support_gate * gate,
    )
    return (
        float((1 - weight) * direct_auc + weight * transport_auc),
        float(weight),
    )


def sentinel_estimate(
    direct_auc: float,
    direct_var: float,
    transport_auc: float,
    transport_risk: float,
    support_gate: float,
) -> Tuple[float, float, float]:
    sentinel_bias_sq = max(
        0.0,
        (direct_auc - transport_auc) ** 2 - direct_var,
    )
    denominator = (
        direct_var
        + SENTINEL_BIAS_COEFFICIENT * sentinel_bias_sq
        + SENTINEL_RISK_COEFFICIENT * transport_risk
        + 1e-12
    )
    weight = support_gate * min(
        SENTINEL_MAX_WEIGHT,
        direct_var / denominator,
    )
    estimate = (1 - weight) * direct_auc + weight * transport_auc
    return float(estimate), float(weight), float(sentinel_bias_sq)


def download_https(
    url: str,
    path: Path,
    minimum_size: int = 1024,
    expected_md5: str | None = None,
) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size >= minimum_size:
        if expected_md5 is None:
            return sha256_file(path)
        md5 = hashlib.md5(path.read_bytes()).hexdigest()
        if md5 == expected_md5:
            return sha256_file(path)
        path.unlink()

    tmp = path.with_suffix(path.suffix + ".part")
    if tmp.exists():
        tmp.unlink()
    with requests.get(url, stream=True, timeout=(30, 600), allow_redirects=True) as response:
        response.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    if tmp.stat().st_size < minimum_size:
        raise RuntimeError(f"Unexpectedly small download: {url}")
    if expected_md5 is not None:
        md5 = hashlib.md5(tmp.read_bytes()).hexdigest()
        if md5 != expected_md5:
            raise RuntimeError(
                f"MD5 mismatch for {path.name}: {md5} != {expected_md5}"
            )
    tmp.replace(path)
    return sha256_file(path)


def hog_features(images: np.ndarray) -> np.ndarray:
    images = np.asarray(images, dtype=np.float32)
    if images.max() > 1.5:
        images = images / 255.0
    rows = []
    for image in images:
        rows.append(
            hog(
                image,
                orientations=9,
                pixels_per_cell=(4, 4),
                cells_per_block=(2, 2),
                block_norm="L2-Hys",
                feature_vector=True,
            )
        )
    return np.asarray(rows, dtype=np.float32)


def xray_shift(images: np.ndarray, kind: str, seed: int) -> np.ndarray:
    x = np.asarray(images, dtype=np.float32)
    if x.max() > 1.5:
        x = x / 255.0
    if kind == "clean":
        return x.copy()
    if kind.startswith("blur_"):
        sigma = float(kind.split("_")[1])
        return ndimage.gaussian_filter(x, sigma=(0, sigma, sigma)).astype(np.float32)
    if kind.startswith("noise_"):
        sigma = float(kind.split("_")[1])
        rng = np.random.default_rng(seed)
        return np.clip(x + rng.normal(0, sigma, size=x.shape), 0, 1).astype(np.float32)
    if kind.startswith("contrast_"):
        scale = float(kind.split("_")[1])
        return np.clip(0.5 + scale * (x - 0.5), 0, 1).astype(np.float32)
    if kind == "downsample_14":
        pooled = x.reshape(len(x), 14, 2, 14, 2).mean(axis=(2, 4))
        return np.repeat(np.repeat(pooled, 2, axis=1), 2, axis=2).astype(np.float32)
    raise ValueError(kind)


def prepare_medical_xray(raw_root: Path) -> Dict[str, Any]:
    root = raw_root / "medical_xray"
    root.mkdir(parents=True, exist_ok=True)
    pneumonia_path = root / "pneumoniamnist.npz"
    chest_path = root / "chestmnist.npz"
    pneumonia_sha = download_https(
        "https://zenodo.org/records/10519652/files/pneumoniamnist.npz?download=1",
        pneumonia_path,
        minimum_size=1_000_000,
        expected_md5="28209eda62fecd6e6a2d98b1501bb15f",
    )
    chest_sha = download_https(
        "https://zenodo.org/records/10519652/files/chestmnist.npz?download=1",
        chest_path,
        minimum_size=20_000_000,
        expected_md5="02c8a6516a18b556561a56cbdd36c4a8",
    )

    with np.load(pneumonia_path) as data:
        train_images = np.asarray(data["train_images"])
        train_labels = np.asarray(data["train_labels"]).reshape(-1).astype(int)
        val_images = np.asarray(data["val_images"])
        val_labels = np.asarray(data["val_labels"]).reshape(-1).astype(int)
        target_test_images = np.asarray(data["test_images"])
    with np.load(chest_path) as data:
        chest_test_images = np.asarray(data["test_images"])

    x_train = hog_features(train_images)
    x_ref = hog_features(val_images)
    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(
            C=1.0,
            max_iter=1200,
            class_weight="balanced",
            random_state=SEED,
        ),
    )
    model.fit(x_train, train_labels)
    ref_scores = model.predict_proba(x_ref)[:, 1]
    projector = make_projection(x_ref, SEED + 10)
    source_z = projector.transform(x_ref)

    pseudo_specs = [
        "clean",
        "blur_0.5",
        "blur_1.0",
        "blur_1.5",
        "noise_0.04",
        "noise_0.08",
        "noise_0.12",
        "contrast_0.7",
        "contrast_0.5",
        "downsample_14",
    ]
    pseudo_envs: List[Dict[str, Any]] = []
    for j, spec in enumerate(pseudo_specs):
        shifted = xray_shift(val_images, spec, SEED + 20 + j)
        features = hog_features(shifted)
        scores = model.predict_proba(features)[:, 1]
        pseudo_envs.append(
            {
                "name": spec,
                "z": projector.transform(features),
                "scores": scores,
                "y": val_labels,
            }
        )

    targets: Dict[str, Dict[str, Any]] = {}
    target_specs = {
        "PNEUMONIA_CLEAN": "clean",
        "PNEUMONIA_BLUR_1_2": "blur_1.2",
        "PNEUMONIA_NOISE_0_10": "noise_0.10",
        "PNEUMONIA_CONTRAST_0_45": "contrast_0.45",
        "PNEUMONIA_DOWNSAMPLE_14": "downsample_14",
    }
    for j, (target, spec) in enumerate(target_specs.items()):
        shifted = xray_shift(target_test_images, spec, SEED + 50 + j)
        features = hog_features(shifted)
        scores = model.predict_proba(features)[:, 1]
        targets[target] = {
            "z": projector.transform(features),
            "scores": scores,
        }

    chest_features = hog_features(chest_test_images)
    chest_scores = model.predict_proba(chest_features)[:, 1]
    targets["CHESTMNIST_PNEUMONIA"] = {
        "z": projector.transform(chest_features),
        "scores": chest_scores,
    }

    def reveal() -> Dict[str, np.ndarray]:
        with np.load(pneumonia_path) as data:
            pneumonia_labels = (
                np.asarray(data["test_labels"]).reshape(-1).astype(int)
            )
        with np.load(chest_path) as data:
            chest_labels = np.asarray(data["test_labels"])[:, 6].astype(int)
        out = {
            target: pneumonia_labels.copy()
            for target in target_specs
        }
        out["CHESTMNIST_PNEUMONIA"] = chest_labels
        return out

    return {
        "family": "MEDICAL_XRAY",
        "source_z": source_z,
        "source_scores": ref_scores,
        "pseudo_envs": pseudo_envs,
        "targets": targets,
        "reveal": reveal,
        "acquisition": {
            "source_dataset": "MedMNIST PneumoniaMNIST train",
            "source_reference": "PneumoniaMNIST validation",
            "target_datasets": [
                "PneumoniaMNIST test acquisition shifts",
                "ChestMNIST test pneumonia label index 6",
            ],
            "pneumoniamnist_sha256": pneumonia_sha,
            "chestmnist_sha256": chest_sha,
            "task": "pneumonia versus normal/other",
            "source_model": "HOG + standardised balanced logistic regression",
            "target_roster_rule": "five fixed test transforms plus full ChestMNIST test",
        },
    }


AMAZON_REPOSITORY = "shijli/amazon-reviews-multi"
AMAZON_REVISION = "e5bebced3300c8edefe2006390dff9aaeb5d3b8d"


def amazon_repo_path(language: str, split: str) -> str:
    """Resolve exactly one Parquet object inside the frozen repository revision."""
    api_url = (
        "https://huggingface.co/api/datasets/"
        f"{AMAZON_REPOSITORY}/tree/{AMAZON_REVISION}/{language}"
        "?recursive=false&expand=false"
    )
    response = requests.get(api_url, timeout=(30, 120))
    response.raise_for_status()
    entries = response.json()
    candidates = sorted(
        entry["path"]
        for entry in entries
        if entry.get("type") == "file"
        and Path(entry.get("path", "")).name.startswith(split + "-")
        and str(entry.get("path", "")).endswith(".parquet")
    )
    if len(candidates) != 1:
        raise RuntimeError(
            f"Expected exactly one frozen Amazon Parquet for "
            f"{language}/{split}; found {candidates}"
        )
    return candidates[0]


def amazon_url(repository_path: str) -> str:
    return (
        f"https://huggingface.co/datasets/{AMAZON_REPOSITORY}/resolve/"
        f"{AMAZON_REVISION}/{repository_path}?download=true"
    )


def read_amazon_parquet(
    path: Path,
    selected_indices: np.ndarray | None,
    include_labels: bool,
) -> Dict[str, Any]:
    columns = ["review_title", "review_body", "product_category"]
    if include_labels:
        columns.append("stars")
    frame = pd.read_parquet(path, columns=columns).reset_index(drop=True)
    total = int(len(frame))

    if selected_indices is not None:
        selected_indices = np.asarray(selected_indices, dtype=int)
        if len(selected_indices) and (
            selected_indices.min() < 0 or selected_indices.max() >= total
        ):
            raise RuntimeError(
                f"Selected Amazon row is outside [0,{total}): {path}"
            )
        selected_frame = frame.iloc[selected_indices].copy()
        positions = selected_indices
    else:
        selected_frame = frame
        positions = np.arange(total, dtype=int)

    titles = selected_frame["review_title"].fillna("").astype(str)
    bodies = selected_frame["review_body"].fillna("").astype(str)
    texts = (titles + " [SEP] " + bodies).tolist()
    categories = (
        selected_frame["product_category"]
        .fillna("unknown")
        .astype(str)
        .tolist()
    )
    labels = None
    if include_labels:
        stars = selected_frame["stars"].to_numpy(dtype=int)
        if not set(np.unique(stars)).issubset({1, 2, 3, 4, 5}):
            raise RuntimeError(
                f"Unexpected Amazon stars in {path}: {np.unique(stars)}"
            )
        labels = (stars >= 4).astype(int)

    return {
        "texts": texts,
        "categories": categories,
        "positions": np.asarray(positions, dtype=int),
        "labels": labels,
        "total_rows": total,
    }


def prepare_amazon_languages(raw_root: Path) -> Dict[str, Any]:
    root = raw_root / "amazon_languages"
    root.mkdir(parents=True, exist_ok=True)

    required = [("en", "train"), ("en", "validation")]
    target_languages = ["de", "es", "fr", "ja", "zh"]
    required.extend((language, "test") for language in target_languages)

    paths: Dict[Tuple[str, str], Path] = {}
    repository_paths: Dict[str, str] = {}
    hashes: Dict[str, str] = {}
    for language, split in required:
        repository_path = amazon_repo_path(language, split)
        repository_paths[f"{language}/{split}"] = repository_path
        path = root / f"{language}_{split}.parquet"
        minimum = (
            20_000_000
            if (language, split) == ("en", "train")
            else 300_000
        )
        hashes[f"{language}/{split}"] = download_https(
            amazon_url(repository_path),
            path,
            minimum_size=minimum,
        )
        paths[(language, split)] = path

    source_indices = deterministic_indices(200000, 60000, SEED + 100)
    train = read_amazon_parquet(
        paths[("en", "train")],
        selected_indices=source_indices,
        include_labels=True,
    )
    if train["total_rows"] != 200000:
        raise RuntimeError(
            f"Unexpected English train row count: {train['total_rows']}"
        )
    validation = read_amazon_parquet(
        paths[("en", "validation")],
        selected_indices=None,
        include_labels=True,
    )
    if validation["total_rows"] != 5000:
        raise RuntimeError(
            f"Unexpected English validation row count: "
            f"{validation['total_rows']}"
        )

    vectorizer = TfidfVectorizer(
        lowercase=True,
        analyzer="char_wb",
        ngram_range=(3, 5),
        min_df=3,
        max_features=60000,
        sublinear_tf=True,
    )
    x_train = vectorizer.fit_transform(train["texts"])
    model = LogisticRegression(
        C=1.0,
        max_iter=1200,
        class_weight="balanced",
        random_state=SEED,
    )
    model.fit(x_train, train["labels"])

    x_ref = vectorizer.transform(validation["texts"])
    ref_scores = model.predict_proba(x_ref)[:, 1]
    ref_y = validation["labels"]
    projector = make_projection(x_ref, SEED + 101)
    source_z = projector.transform(x_ref)

    pseudo_envs: List[Dict[str, Any]] = []
    category_series = pd.Series(validation["categories"])
    for category, count in category_series.value_counts().items():
        if int(count) < 120:
            continue
        idx = np.where(category_series.to_numpy() == category)[0]
        if len(np.unique(ref_y[idx])) == 2:
            pseudo_envs.append(
                {
                    "name": f"category_{category}",
                    "z": source_z[idx],
                    "scores": ref_scores[idx],
                    "y": ref_y[idx],
                }
            )
    lengths = np.asarray([len(text) for text in validation["texts"]])
    quantiles = np.quantile(lengths, [0, 0.2, 0.4, 0.6, 0.8, 1.0])
    for i in range(5):
        mask = (lengths >= quantiles[i]) & (
            lengths <= quantiles[i + 1]
            if i == 4
            else lengths < quantiles[i + 1]
        )
        idx = np.where(mask)[0]
        if len(idx) >= 300 and len(np.unique(ref_y[idx])) == 2:
            pseudo_envs.append(
                {
                    "name": f"length_q{i+1}",
                    "z": source_z[idx],
                    "scores": ref_scores[idx],
                    "y": ref_y[idx],
                }
            )

    targets: Dict[str, Dict[str, Any]] = {}
    protected_positions: Dict[str, np.ndarray] = {}
    for language in target_languages:
        unlabelled = read_amazon_parquet(
            paths[(language, "test")],
            selected_indices=None,
            include_labels=False,
        )
        if unlabelled["total_rows"] != 5000:
            raise RuntimeError(
                f"Unexpected {language} test row count: "
                f"{unlabelled['total_rows']}"
            )
        x = vectorizer.transform(unlabelled["texts"])
        scores = model.predict_proba(x)[:, 1]
        target = f"LANG_{language}"
        targets[target] = {
            "z": projector.transform(x),
            "scores": scores,
        }
        protected_positions[target] = unlabelled["positions"]

    def reveal() -> Dict[str, np.ndarray]:
        out: Dict[str, np.ndarray] = {}
        for language in target_languages:
            labelled = read_amazon_parquet(
                paths[(language, "test")],
                selected_indices=None,
                include_labels=True,
            )
            target = f"LANG_{language}"
            positions = protected_positions[target]
            labels = labelled["labels"][positions]
            if len(labels) != len(targets[target]["scores"]):
                raise RuntimeError(f"Amazon label-score mismatch: {target}")
            if set(np.unique(labels)) != {0, 1}:
                raise RuntimeError(
                    f"Amazon target lacks both classes: {target}"
                )
            out[target] = labels.astype(int)
        return out

    return {
        "family": "AMAZON_LANGUAGES",
        "source_z": source_z,
        "source_scores": ref_scores,
        "pseudo_envs": pseudo_envs,
        "targets": targets,
        "reveal": reveal,
        "acquisition": {
            "dataset": (
                "Parquet mirror of the Multilingual Amazon Reviews Corpus"
            ),
            "repository": AMAZON_REPOSITORY,
            "repository_revision": AMAZON_REVISION,
            "repository_paths": repository_paths,
            "file_sha256": hashes,
            "source_language": "en",
            "target_languages": target_languages,
            "task": "stars >=4 versus stars <=3",
            "source_train_n": int(len(train["texts"])),
            "source_reference_n": int(len(validation["texts"])),
            "source_model": "char_wb TF-IDF + balanced logistic regression",
            "acquisition_amendment": "StageU5_Outcome_Blind_Acquisition_Amendment_v1.0.1",
        },
    }


ACS_INCOME_2022_FEATURES = [
    "AGEP",
    "COW",
    "SCHL",
    "MAR",
    "OCCP",
    "POBP",
    "RELSHIPP",
    "WKHP",
    "SEX",
    "RAC1P",
]


def acs_income_2022_to_numpy(frame: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    """Apply the frozen ACSIncome task with the official 2022 relationship field."""
    required = set(
        ACS_INCOME_2022_FEATURES + ["PINCP", "PWGTP"]
    )
    missing = sorted(required - set(frame.columns))
    if missing:
        raise RuntimeError(
            f"ACS 2022 person schema is missing required columns: {missing}. "
            f"Available relationship columns: "
            f"{sorted(c for c in frame.columns if c.startswith('REL'))}"
        )

    filtered = frame[
        (frame["AGEP"] > 16)
        & (frame["PINCP"] > 100)
        & (frame["WKHP"] > 0)
        & (frame["PWGTP"] >= 1)
    ].reset_index(drop=True)

    features = filtered[ACS_INCOME_2022_FEATURES].to_numpy(dtype=float)
    features = np.nan_to_num(features, nan=-1.0, posinf=-1.0, neginf=-1.0)
    labels = (filtered["PINCP"].to_numpy(dtype=float) > 50000).astype(int)

    if len(features) != len(labels) or len(features) == 0:
        raise RuntimeError(
            f"Invalid ACSIncome 2022 conversion: X={features.shape}, "
            f"y={labels.shape}"
        )
    if set(np.unique(labels)) != {0, 1}:
        raise RuntimeError(
            f"ACSIncome 2022 conversion lacks both classes: {np.unique(labels)}"
        )
    return features, labels


def prepare_acs_income_2022(raw_root: Path) -> Dict[str, Any]:
    from folktables import ACSDataSource

    root = raw_root / "acs_2022"
    root.mkdir(parents=True, exist_ok=True)
    source = ACSDataSource(
        survey_year="2022",
        horizon="1-Year",
        survey="person",
        root_dir=str(root),
    )

    source_df = source.get_data(states=["CA"], download=True)
    if "RELP" in source_df.columns:
        raise RuntimeError(
            "Unexpected legacy RELP field in the frozen 2022 ACS source."
        )
    if "RELSHIPP" not in source_df.columns:
        raise RuntimeError(
            "Official 2022 relationship field RELSHIPP is absent."
        )

    x_all, y_all = acs_income_2022_to_numpy(source_df)
    idx = deterministic_indices(len(x_all), min(100000, len(x_all)), SEED + 200)
    x_all, y_all = x_all[idx], y_all[idx]
    split = min(80000, int(0.8 * len(x_all)))
    x_train, y_train = x_all[:split], y_all[:split]
    x_ref, y_ref = x_all[split:], y_all[split:]

    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(
            C=1.0,
            max_iter=1200,
            class_weight="balanced",
            random_state=SEED,
        ),
    )
    model.fit(x_train, y_train)
    ref_scores = model.predict_proba(x_ref)[:, 1]
    projector = make_projection(x_ref, SEED + 201)
    source_z = projector.transform(x_ref)

    pseudo_envs: List[Dict[str, Any]] = []
    for feature_index, name in [(0, "age"), (7, "hours")]:
        vector = x_ref[:, feature_index]
        quantiles = np.quantile(vector, [0, 0.25, 0.5, 0.75, 1.0])
        for i in range(4):
            mask = (vector >= quantiles[i]) & (
                vector <= quantiles[i + 1]
                if i == 3
                else vector < quantiles[i + 1]
            )
            ix = np.where(mask)[0]
            if len(ix) >= 300 and len(np.unique(y_ref[ix])) == 2:
                pseudo_envs.append(
                    {
                        "name": f"{name}_q{i+1}",
                        "z": source_z[ix],
                        "scores": ref_scores[ix],
                        "y": y_ref[ix],
                    }
                )
    for feature_index, name in [(8, "sex"), (9, "race")]:
        values, counts = np.unique(x_ref[:, feature_index], return_counts=True)
        for value in values[np.argsort(-counts)[:4]]:
            ix = np.where(x_ref[:, feature_index] == value)[0]
            if len(ix) >= 300 and len(np.unique(y_ref[ix])) == 2:
                pseudo_envs.append(
                    {
                        "name": f"{name}_{int(value)}",
                        "z": source_z[ix],
                        "scores": ref_scores[ix],
                        "y": y_ref[ix],
                    }
                )

    target_states = ["WA", "MA", "GA", "NC", "AZ"]
    targets: Dict[str, Dict[str, Any]] = {}
    protected_labels: Dict[str, np.ndarray] = {}
    for j, state in enumerate(target_states):
        frame = source.get_data(states=[state], download=True)
        x, y = acs_income_2022_to_numpy(frame)
        ix = deterministic_indices(len(x), min(20000, len(x)), SEED + 220 + j)
        x_selected = x[ix]
        y_selected = y[ix]
        scores = model.predict_proba(x_selected)[:, 1]
        targets[state] = {
            "z": projector.transform(x_selected),
            "scores": scores,
        }
        protected_labels[state] = y_selected

    def reveal() -> Dict[str, np.ndarray]:
        return {
            state: labels.copy()
            for state, labels in protected_labels.items()
        }

    return {
        "family": "ACS_INCOME_2022",
        "source_z": source_z,
        "source_scores": ref_scores,
        "pseudo_envs": pseudo_envs,
        "targets": targets,
        "reveal": reveal,
        "acquisition": {
            "dataset": "Census ACS 2022 1-Year person survey via folktables downloader",
            "source_state": "CA",
            "target_states": target_states,
            "task": "ACSIncome: PINCP > 50000 after the standard adult filter",
            "features": ACS_INCOME_2022_FEATURES,
            "schema_adapter": "RELP -> official 2022 successor RELSHIPP",
            "source_train_n": int(len(x_train)),
            "source_reference_n": int(len(x_ref)),
            "schema_amendment": "StageU5_Outcome_Blind_ACS2022_Schema_Amendment_v1.0.2",
        },
    }


def acquire_all(raw_root: Path) -> List[Dict[str, Any]]:
    print("[U5] Preparing MEDICAL_XRAY source model and target scores.")
    medical = prepare_medical_xray(raw_root)
    print("[U5] Preparing AMAZON_LANGUAGES source model and target scores.")
    text = prepare_amazon_languages(raw_root)
    print("[U5] Preparing ACS_INCOME_2022 source model and target scores.")
    tabular = prepare_acs_income_2022(raw_root)
    return [medical, text, tabular]


def pre_outcome_seal(
    families: List[Dict[str, Any]],
    output_dir: Path,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    pseudo_frames, target_frames = [], []
    models = {}
    for family in families:
        pseudo, targets, model_record = fit_transport(
            family["family"],
            family["source_z"],
            family["source_scores"],
            family["pseudo_envs"],
            family["targets"],
        )
        pseudo_frames.append(pseudo)
        target_frames.append(targets)
        models[family["family"]] = model_record

    pseudo_all = pd.concat(pseudo_frames, ignore_index=True)
    targets_all = pd.concat(target_frames, ignore_index=True)
    pseudo_path = output_dir / "StageU5B_Source_Pseudo_Environments_v1.0.csv"
    target_path = (
        output_dir
        / "StageU5B_PreOutcome_Target_Descriptors_And_Transport_v1.0.csv"
    )
    pseudo_all.to_csv(pseudo_path, index=False)
    targets_all.to_csv(target_path, index=False)

    seal = {
        "created_utc": utc_now(),
        "status": "SEALED_BEFORE_U5_TARGET_OUTCOME_USE",
        "target_count": int(len(targets_all)),
        "family_count": int(targets_all["family"].nunique()),
        "target_roster": (
            targets_all[["family", "target", "n_target_unlabelled"]]
            .sort_values(["family", "target"])
            .to_dict("records")
        ),
        "transport_models": models,
        "acquisition": {
            family["family"]: family["acquisition"] for family in families
        },
        "target_descriptor_csv_sha256": sha256_file(target_path),
        "pseudo_environment_csv_sha256": sha256_file(pseudo_path),
    }
    seal["seal_sha256"] = sha256_text(canonical_json(seal))
    (output_dir / "StageU5B_PreOutcome_Transport_Seal_v1.0.json").write_text(
        json.dumps(seal, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print("[U5] Pre-outcome seal committed:", seal["seal_sha256"])
    return pseudo_all, targets_all, seal


def reveal_labels(
    families: List[Dict[str, Any]],
) -> Dict[Tuple[str, str], np.ndarray]:
    labels: Dict[Tuple[str, str], np.ndarray] = {}
    for family in families:
        revealed = family["reveal"]()
        for target, values in revealed.items():
            arr = np.asarray(values, dtype=int)
            if arr.ndim != 1 or set(np.unique(arr)) != {0, 1}:
                raise RuntimeError(
                    f"Invalid target labels for {family['family']}/{target}: "
                    f"shape={arr.shape}, classes={np.unique(arr)}"
                )
            labels[(family["family"], target)] = arr
    return labels


def run_witnesses(
    families: List[Dict[str, Any]],
    target_transport: pd.DataFrame,
    labels: Dict[Tuple[str, str], np.ndarray],
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    transport_index = target_transport.set_index(["family", "target"])
    rows: List[dict] = []
    true_rows: List[dict] = []
    target_counter = 0
    for family in families:
        family_name = family["family"]
        for target, item in family["targets"].items():
            y = labels[(family_name, target)]
            scores = np.asarray(item["scores"], dtype=float)
            if len(y) != len(scores):
                raise RuntimeError(f"Label-score mismatch: {family_name}/{target}")
            true_auc = float(roc_auc_score(y, scores))
            pos_idx = np.where(y == 1)[0]
            neg_idx = np.where(y == 0)[0]
            if min(len(pos_idx), len(neg_idx)) < 64:
                raise RuntimeError(
                    f"Insufficient minority class for budget 128: "
                    f"{family_name}/{target}, pos={len(pos_idx)}, neg={len(neg_idx)}"
                )
            true_rows.append(
                {
                    "family": family_name,
                    "target": target,
                    "n": len(y),
                    "positive_n": len(pos_idx),
                    "negative_n": len(neg_idx),
                    "prevalence": float(y.mean()),
                    "true_auc": true_auc,
                }
            )
            trow = transport_index.loc[(family_name, target)]
            transport_auc = float(trow["transport_auc"])
            transport_risk = float(trow["transport_risk_proxy"])
            support_gate = float(trow["support_gate"])
            for budget in BUDGETS:
                half = int(budget // 2)
                for replicate in range(N_REPLICATES):
                    rng = np.random.default_rng(
                        SEED
                        + target_counter * 100000
                        + int(budget) * 1000
                        + replicate
                    )
                    sampled = np.concatenate(
                        [
                            rng.choice(pos_idx, size=half, replace=False),
                            rng.choice(neg_idx, size=half, replace=False),
                        ]
                    )
                    direct_auc, direct_var = delong_auc_variance(
                        y[sampled], scores[sampled]
                    )
                    static_auc = 0.6 * transport_auc + 0.4 * direct_auc
                    label_free_auc, label_free_weight = label_free_estimate(
                        direct_auc,
                        direct_var,
                        transport_auc,
                        transport_risk,
                        support_gate,
                    )
                    sentinel_auc, sentinel_weight, sentinel_bias_sq = (
                        sentinel_estimate(
                            direct_auc,
                            direct_var,
                            transport_auc,
                            transport_risk,
                            support_gate,
                        )
                    )
                    true_bias_sq = (transport_auc - true_auc) ** 2
                    oracle_weight = support_gate * min(
                        SENTINEL_MAX_WEIGHT,
                        direct_var
                        / (
                            direct_var
                            + true_bias_sq
                            + SENTINEL_RISK_COEFFICIENT * transport_risk
                            + 1e-12
                        ),
                    )
                    oracle_auc = (
                        (1 - oracle_weight) * direct_auc
                        + oracle_weight * transport_auc
                    )
                    rows.append(
                        {
                            "family": family_name,
                            "target": target,
                            "budget": int(budget),
                            "replicate": replicate,
                            "true_auc": true_auc,
                            "direct_auc": direct_auc,
                            "direct_variance": direct_var,
                            "direct_sd": math.sqrt(direct_var),
                            "transport_auc": transport_auc,
                            "transport_abs_error": abs(transport_auc - true_auc),
                            "transport_risk_proxy": transport_risk,
                            "support_gate": support_gate,
                            "static_auc": static_auc,
                            "label_free_auc": label_free_auc,
                            "label_free_weight": label_free_weight,
                            "sentinel_auc": sentinel_auc,
                            "sentinel_weight": sentinel_weight,
                            "sentinel_bias_sq": sentinel_bias_sq,
                            "oracle_auc": oracle_auc,
                            "oracle_weight": oracle_weight,
                            "direct_abs_error": abs(direct_auc - true_auc),
                            "static_abs_error": abs(static_auc - true_auc),
                            "label_free_abs_error": abs(label_free_auc - true_auc),
                            "sentinel_abs_error": abs(sentinel_auc - true_auc),
                            "oracle_abs_error": abs(oracle_auc - true_auc),
                        }
                    )
            target_counter += 1
    return pd.DataFrame(rows), pd.DataFrame(true_rows)


def summarize_states(replicates: pd.DataFrame) -> pd.DataFrame:
    states = (
        replicates.groupby(["family", "target", "budget"], as_index=False)
        .agg(
            direct_mae=("direct_abs_error", "mean"),
            static_mae=("static_abs_error", "mean"),
            label_free_mae=("label_free_abs_error", "mean"),
            sentinel_mae=("sentinel_abs_error", "mean"),
            oracle_mae=("oracle_abs_error", "mean"),
            median_direct_sd=("direct_sd", "median"),
            mean_label_free_weight=("label_free_weight", "mean"),
            mean_sentinel_weight=("sentinel_weight", "mean"),
            mean_oracle_weight=("oracle_weight", "mean"),
            mean_sentinel_bias_sq=("sentinel_bias_sq", "mean"),
            support_gate=("support_gate", "first"),
            transport_auc=("transport_auc", "first"),
            transport_abs_error=("transport_abs_error", "first"),
            transport_risk_proxy=("transport_risk_proxy", "first"),
            true_auc=("true_auc", "first"),
        )
    )
    states["sentinel_regret_vs_direct"] = (
        states["sentinel_mae"] - states["direct_mae"]
    )
    states["sentinel_gain_vs_direct"] = (
        states["direct_mae"] - states["sentinel_mae"]
    )
    states["sentinel_gain_vs_static"] = (
        states["static_mae"] - states["sentinel_mae"]
    )
    states["sentinel_gain_vs_label_free"] = (
        states["label_free_mae"] - states["sentinel_mae"]
    )
    states["sentinel_label_leverage"] = (
        states["direct_mae"] / np.maximum(states["sentinel_mae"], 1e-12)
    ) ** 2
    return states


def fit_rootn(states: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (family, target), group in states.groupby(["family", "target"]):
        group = group.sort_values("budget")
        x = 1.0 / np.sqrt(group["budget"].to_numpy(float))
        y = group["direct_mae"].to_numpy(float)
        amplitude = float(np.dot(x, y) / max(np.dot(x, x), 1e-12))
        pred = amplitude * x
        rows.append(
            {
                "family": family,
                "target": target,
                "rootn_amplitude": amplitude,
                "rootn_mae": float(np.mean(np.abs(pred - y))),
                "direct_mae_budget8": float(y[0]),
                "direct_mae_budget128": float(y[-1]),
            }
        )
    return pd.DataFrame(rows)


def evaluate_gates(
    states: pd.DataFrame,
    true_metrics: pd.DataFrame,
    integrity_pass: bool,
) -> Tuple[pd.DataFrame, Dict[str, Any], str]:
    target_count = int(states[["family", "target"]].drop_duplicates().shape[0])
    family_count = int(states["family"].nunique())
    overall = states[
        [
            "direct_mae",
            "static_mae",
            "label_free_mae",
            "sentinel_mae",
            "oracle_mae",
        ]
    ].mean()

    budget8 = states[states["budget"] == 8]
    positive_budget8 = int(
        (budget8["sentinel_mae"] < budget8["direct_mae"]).sum()
    )
    median_leverage = float(budget8["sentinel_label_leverage"].median())
    worst_target_budget_regret = float(
        states["sentinel_regret_vs_direct"].max()
    )
    family_regret = (
        states.groupby("family")[["sentinel_mae", "direct_mae"]].mean()
    )
    worst_family_regret = float(
        (family_regret["sentinel_mae"] - family_regret["direct_mae"]).max()
    )

    target_level = (
        states.groupby(["family", "target"], as_index=False)
        .agg(
            sentinel_bias_sq=("mean_sentinel_bias_sq", "mean"),
            transport_abs_error=("transport_abs_error", "first"),
            sentinel_weight=("mean_sentinel_weight", "mean"),
        )
    )
    rho, rho_p = spearmanr(
        target_level["sentinel_bias_sq"],
        target_level["transport_abs_error"],
    )
    target_level = target_level.sort_values("transport_abs_error")
    quartile = max(1, len(target_level) // 4)
    low_weight = float(target_level.head(quartile)["sentinel_weight"].median())
    high_weight = float(target_level.tail(quartile)["sentinel_weight"].median())
    selective_ratio = high_weight / max(low_weight, 1e-12)

    severe = states[states["transport_abs_error"] >= 0.15]
    if len(severe):
        severe_regret = float(severe["sentinel_regret_vs_direct"].max())
        static_harm = np.maximum(0.0, severe["static_mae"] - severe["direct_mae"])
        sentinel_harm = np.maximum(
            0.0, severe["sentinel_mae"] - severe["direct_mae"]
        )
        severe_harm_reduction = float(
            1.0 - sentinel_harm.sum() / max(static_harm.sum(), 1e-12)
        )
    else:
        severe_regret = 0.0
        severe_harm_reduction = 1.0

    gates = [
        (
            "integrity_and_exact_authorisation",
            bool(integrity_pass),
            str(integrity_pass),
        ),
        (
            "new_reserve_at_least_16_targets_3_families",
            target_count >= 16 and family_count >= 3,
            f"{target_count} targets; {family_count} families",
        ),
        (
            "sentinel_pooled_gain_vs_direct",
            overall["sentinel_mae"] <= 0.90 * overall["direct_mae"],
            (
                f"sentinel={overall['sentinel_mae']:.6f};"
                f"direct={overall['direct_mae']:.6f};"
                f"static={overall['static_mae']:.6f}"
            ),
        ),
        (
            "sentinel_low_budget_utility",
            positive_budget8 >= math.ceil(0.60 * target_count)
            and median_leverage >= 1.25,
            f"positive={positive_budget8}/{target_count};leverage={median_leverage:.6f}",
        ),
        (
            "sentinel_regret_control",
            worst_target_budget_regret <= 0.01 and worst_family_regret <= 0.005,
            (
                f"target_budget={worst_target_budget_regret:.6f};"
                f"family={worst_family_regret:.6f}"
            ),
        ),
        (
            "sentinel_tail_safety_tradeoff_vs_label_free",
            (
                overall["sentinel_mae"] <= 1.20 * overall["label_free_mae"]
                and worst_target_budget_regret
                <= (
                    0.50
                    * float(
                        (
                            states["label_free_mae"] - states["direct_mae"]
                        ).max()
                    )
                    if float(
                        (
                            states["label_free_mae"] - states["direct_mae"]
                        ).max()
                    )
                    > 0.02
                    else 0.01
                )
            ),
            (
                f"sentinel_mae={overall['sentinel_mae']:.6f};"
                f"label_free_mae={overall['label_free_mae']:.6f};"
                f"sentinel_worst_regret={worst_target_budget_regret:.6f};"
                f"label_free_worst_regret="
                f"{float((states['label_free_mae']-states['direct_mae']).max()):.6f}"
            ),
        ),
        (
            "bias_observability",
            bool(np.isfinite(rho) and rho >= 0.50),
            f"spearman={rho:.6f};p={rho_p:.6g}",
        ),
        (
            "selective_persistence_or_exit",
            selective_ratio <= 0.60,
            (
                f"high_error_weight={high_weight:.6f};"
                f"low_error_weight={low_weight:.6f};"
                f"ratio={selective_ratio:.6f}"
            ),
        ),
        (
            "severe_transport_failure_control",
            severe_regret <= 0.015 and severe_harm_reduction >= 0.50,
            (
                f"severe_regret={severe_regret:.6f};"
                f"harm_reduction={severe_harm_reduction:.6f};"
                f"states={len(severe)}"
            ),
        ),
        (
            "stage12_prohibited",
            True,
            "False",
        ),
    ]
    gate_df = pd.DataFrame(gates, columns=["gate", "passed", "observed"])
    primary = gate_df[
        ~gate_df["gate"].isin(["stage12_prohibited"])
    ]
    if bool(primary["passed"].all()):
        decision = (
            "SEAL_STAGEU5B_SENTINEL_OBSERVABILITY_STRONG_PROSPECTIVE_SUPPORT_"
            "AUTHORISE_MANUSCRIPT_SYNTHESIS_STAGE12_PROHIBITED"
        )
    elif bool(
        gate_df.set_index("gate").loc[
            [
                "sentinel_pooled_gain_vs_direct",
                "sentinel_low_budget_utility",
                "bias_observability",
            ],
            "passed",
        ].all()
    ):
        decision = (
            "SEAL_STAGEU5B_SENTINEL_OBSERVABILITY_PARTIAL_SUPPORT_"
            "REROUTE_OR_REFINE_STAGE12_PROHIBITED"
        )
    else:
        decision = (
            "SEAL_STAGEU5B_SENTINEL_OBSERVABILITY_FAILED_RETAIN_ALL_RESULTS_"
            "STAGE12_PROHIBITED"
        )

    summary = {
        "target_count": target_count,
        "family_count": family_count,
        "direct_overall_mae": float(overall["direct_mae"]),
        "static_overall_mae": float(overall["static_mae"]),
        "label_free_overall_mae": float(overall["label_free_mae"]),
        "sentinel_overall_mae": float(overall["sentinel_mae"]),
        "oracle_overall_mae": float(overall["oracle_mae"]),
        "sentinel_gain_vs_direct": float(
            1 - overall["sentinel_mae"] / overall["direct_mae"]
        ),
        "sentinel_gain_vs_static": float(
            1 - overall["sentinel_mae"] / overall["static_mae"]
        ),
        "sentinel_gain_vs_label_free": float(
            1 - overall["sentinel_mae"] / overall["label_free_mae"]
        ),
        "budget8_positive_targets": positive_budget8,
        "median_budget8_label_leverage": median_leverage,
        "worst_target_budget_regret": worst_target_budget_regret,
        "worst_family_regret": worst_family_regret,
        "bias_observability_spearman": float(rho),
        "bias_observability_pvalue": float(rho_p),
        "high_to_low_transport_error_weight_ratio": selective_ratio,
        "severe_transport_state_count": int(len(severe)),
        "severe_transport_worst_regret": severe_regret,
        "severe_transport_harm_reduction": severe_harm_reduction,
    }
    return gate_df, summary, decision


def make_figures(
    output_dir: Path,
    states: pd.DataFrame,
    true_metrics: pd.DataFrame,
) -> None:
    methods = pd.Series(
        {
            "Direct": states["direct_mae"].mean(),
            "Static": states["static_mae"].mean(),
            "Label-free": states["label_free_mae"].mean(),
            "Sentinel": states["sentinel_mae"].mean(),
            "Oracle": states["oracle_mae"].mean(),
        }
    )
    plt.figure(figsize=(7.2, 4.8))
    methods.plot(kind="bar")
    plt.ylabel("Mean absolute AUC error")
    plt.title("U5 prospective audit comparison")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(output_dir / "Figure_U5B_1_Method_Comparison.png", dpi=180)
    plt.close()

    target = (
        states.groupby(["family", "target"], as_index=False)
        .agg(
            transport_error=("transport_abs_error", "first"),
            sentinel_bias_sq=("mean_sentinel_bias_sq", "mean"),
        )
    )
    plt.figure(figsize=(7.0, 5.0))
    plt.scatter(target["sentinel_bias_sq"], target["transport_error"])
    for _, row in target.iterrows():
        plt.annotate(
            row["target"],
            (row["sentinel_bias_sq"], row["transport_error"]),
            fontsize=7,
        )
    plt.xlabel("Sentinel-estimated squared transport bias")
    plt.ylabel("True transport absolute error")
    plt.title("Minimal labels restore bias observability")
    plt.tight_layout()
    plt.savefig(output_dir / "Figure_U5B_2_Bias_Observability.png", dpi=180)
    plt.close()

    weight = (
        states.groupby(["family", "target"], as_index=False)
        .agg(
            transport_error=("transport_abs_error", "first"),
            sentinel_weight=("mean_sentinel_weight", "mean"),
        )
        .sort_values("transport_error")
    )
    plt.figure(figsize=(8.0, 5.0))
    plt.barh(
        weight["family"] + "/" + weight["target"],
        weight["sentinel_weight"],
    )
    plt.xlabel("Mean sentinel transport weight")
    plt.title("Selective persistence and exit across targets")
    plt.tight_layout()
    plt.savefig(output_dir / "Figure_U5B_3_Selective_Weight.png", dpi=180)
    plt.close()

    budget = states.groupby("budget")[
        ["direct_mae", "label_free_mae", "sentinel_mae"]
    ].mean()
    plt.figure(figsize=(7.0, 5.0))
    for column in budget.columns:
        plt.plot(budget.index, budget[column], marker="o", label=column)
    plt.xscale("log", base=2)
    plt.xlabel("Target label budget")
    plt.ylabel("Mean absolute AUC error")
    plt.title("Evidence-budget trajectories")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "Figure_U5B_4_Budget_Trajectories.png", dpi=180)
    plt.close()


def verify_inputs(
    u4d_path: Path,
    prereg_path: Path,
    auth_path: Path,
    pipeline_path: Path,
    theory_path: Path,
    acquisition_amendment_path: Path,
    schema_amendment_path: Path,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    u4d = json.loads(u4d_path.read_text(encoding="utf-8"))
    auth = json.loads(auth_path.read_text(encoding="utf-8"))
    checks = {
        "u4d_record_hash": sha256_file(u4d_path),
        "prereg_hash": sha256_file(prereg_path),
        "pipeline_hash": sha256_file(pipeline_path),
        "theory_hash": sha256_file(theory_path),
        "acquisition_amendment_hash": sha256_file(
            acquisition_amendment_path
        ),
        "schema_amendment_hash": sha256_file(schema_amendment_path),
        "u4d_final_record_internal": u4d.get("final_record_sha256"),
        "u4d_expected": EXPECTED_U4D_FINAL_SHA256,
    }
    passed = bool(
        u4d.get("final_record_sha256") == EXPECTED_U4D_FINAL_SHA256
        and u4d.get("u5_preregistration_authorised") is True
        and auth.get("stage_u4d_final_record_sha256") == EXPECTED_U4D_FINAL_SHA256
        and auth.get("stage_u4d_record_file_sha256") == checks["u4d_record_hash"]
        and auth.get("stage_u4c_final_record_sha256") == EXPECTED_U4C_FINAL_SHA256
        and auth.get("stage_u4c_canonical_zip_sha256")
        == EXPECTED_U4C_CANONICAL_ZIP_SHA256
        and auth.get("u5_preregistration_sha256") == checks["prereg_hash"]
        and auth.get("u5_pipeline_sha256") == checks["pipeline_hash"]
        and auth.get("u5_theory_memo_sha256") == checks["theory_hash"]
        and auth.get("u5_acquisition_amendment_sha256")
        == checks["acquisition_amendment_hash"]
        and auth.get("u5_schema_amendment_sha256")
        == checks["schema_amendment_hash"]
        and auth.get("u5_execution_authorised") is True
        and auth.get("stage12_authorised") is False
    )
    checks["integrity_pass"] = passed
    return checks, auth


def manifest(output_dir: Path) -> pd.DataFrame:
    rows = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name not in {
            "StageU5B_Durable_Manifest_v1.0.csv",
            "StageU5B_Canonical_Records_v1.0.zip",
        }:
            rows.append(
                {
                    "relative_path": str(path.relative_to(output_dir)),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    return pd.DataFrame(rows)


def main() -> None:
    started = time.time()
    random.seed(SEED)
    np.random.seed(SEED)
    warnings.filterwarnings("ignore", category=FutureWarning)

    pipeline_path = Path(__file__).resolve()
    u4d_path = Path(os.environ["CMDO_U4D_RECORD_PATH"]).resolve()
    prereg_path = Path(os.environ["CMDO_U5_PREREG_PATH"]).resolve()
    auth_path = Path(os.environ["CMDO_U5_AUTH_PATH"]).resolve()
    theory_path = Path(os.environ["CMDO_U5_THEORY_PATH"]).resolve()
    acquisition_amendment_path = Path(
        os.environ["CMDO_U5_ACQUISITION_AMENDMENT_PATH"]
    ).resolve()
    schema_amendment_path = Path(
        os.environ["CMDO_U5_SCHEMA_AMENDMENT_PATH"]
    ).resolve()

    integrity, auth = verify_inputs(
        u4d_path,
        prereg_path,
        auth_path,
        pipeline_path,
        theory_path,
        acquisition_amendment_path,
        schema_amendment_path,
    )
    if not integrity["integrity_pass"]:
        raise RuntimeError(f"U5 exact-hash integrity failed: {integrity}")

    project_root = locate_project_root()
    output_dir = (
        project_root / "06_Data_Records" / "Cross_Modal" / STAGE
    )
    if output_dir.exists():
        final_path = output_dir / "StageU5B_Complete_v1.0.json"
        if final_path.exists():
            raise RuntimeError(
                "A completed U5B result already exists. Rerun is prohibited."
            )
        backup = output_dir.with_name(
            output_dir.name + "_PARTIAL_" + datetime.now().strftime("%Y%m%dT%H%M%S")
        )
        output_dir.rename(backup)
    output_dir.mkdir(parents=True, exist_ok=False)

    shutil.copy2(u4d_path, output_dir / "StageU4D_Complete_v1.0.json")
    shutil.copy2(prereg_path, output_dir / "StageU5A_Final_Preregistration_v1.0.txt")
    shutil.copy2(auth_path, output_dir / "U5B_EXECUTION_AUTHORIZATION_v1.0.json")
    shutil.copy2(theory_path, output_dir / "CMDO_v2_Theory_Reconstruction_v1.0.md")
    shutil.copy2(
        acquisition_amendment_path,
        output_dir / "StageU5_Outcome_Blind_Acquisition_Amendment_v1.0.1.txt",
    )
    shutil.copy2(
        schema_amendment_path,
        output_dir / "StageU5_Outcome_Blind_ACS2022_Schema_Amendment_v1.0.2.txt",
    )
    shutil.copy2(pipeline_path, output_dir / pipeline_path.name)

    raw_root = Path("/content/cmdo_u5_ephemeral_raw")
    raw_root.mkdir(parents=True, exist_ok=True)

    print("[U5] Exact-hash authorisation verified. Preparing source-only models.")
    families = acquire_all(raw_root)
    _, target_transport, seal = pre_outcome_seal(families, output_dir)
    if seal["target_count"] < 16 or seal["family_count"] < 3:
        raise RuntimeError(
            f"Frozen reserve incomplete: {seal['target_count']} targets, "
            f"{seal['family_count']} families"
        )

    print("[U5] Seal complete. Frozen witness protocol may now access labels.")
    labels = reveal_labels(families)
    replicates, true_metrics = run_witnesses(
        families, target_transport, labels
    )
    states = summarize_states(replicates)
    rootn = fit_rootn(states)

    replicates.to_csv(
        output_dir / "StageU5B_AUC_Witness_Replicates_v1.0.csv.gz",
        index=False,
        compression="gzip",
    )
    true_metrics.to_csv(
        output_dir / "StageU5B_Target_True_Metrics_v1.0.csv",
        index=False,
    )
    states.to_csv(
        output_dir / "StageU5B_Audit_State_Results_v1.0.csv",
        index=False,
    )
    rootn.to_csv(
        output_dir / "StageU5B_RootN_Direct_Trajectories_v1.0.csv",
        index=False,
    )

    gate_df, summary, decision = evaluate_gates(
        states, true_metrics, integrity["integrity_pass"]
    )
    gate_df.to_csv(
        output_dir / "StageU5B_Gate_Table_v1.0.csv",
        index=False,
    )
    make_figures(output_dir, states, true_metrics)

    manuscript = f"""# Stage U5B prospective sentinel-observability result

Decision: `{decision}`

The new reserve contains {summary['target_count']} targets across
{summary['family_count']} families: medical X-ray acquisition and cross-dataset
shift, multilingual review-language shift, and ACS 2022 cross-state shift.

Direct-only MAE: {summary['direct_overall_mae']:.6f}.
Label-free adaptive MAE: {summary['label_free_overall_mae']:.6f}.
Sentinel-shrinkage MAE: {summary['sentinel_overall_mae']:.6f}.
Oracle-shrinkage MAE: {summary['oracle_overall_mae']:.6f}.

The sentinel gain versus direct was {summary['sentinel_gain_vs_direct']:.6f}.
At budget 8, {summary['budget8_positive_targets']}/{summary['target_count']}
targets improved and median label leverage was
{summary['median_budget8_label_leverage']:.6f}.

The observed target-level correlation between sentinel-estimated bias and true
transport error was {summary['bias_observability_spearman']:.6f}.
Worst target-budget regret was {summary['worst_target_budget_regret']:.6f}.
Stage 12 remains prohibited.
"""
    (output_dir / "StageU5B_Manuscript_Insert_v1.0.md").write_text(
        manuscript, encoding="utf-8"
    )

    pre_record = {
        "stage": STAGE,
        "status": "PROSPECTIVE_U5_SENTINEL_OBSERVABILITY_COMPLETE",
        "created_utc": utc_now(),
        "decision": decision,
        "stage_u4d_final_record_sha256": EXPECTED_U4D_FINAL_SHA256,
        "stage_u4c_final_record_sha256": EXPECTED_U4C_FINAL_SHA256,
        "stage_u4c_canonical_zip_sha256": EXPECTED_U4C_CANONICAL_ZIP_SHA256,
        "pre_outcome_seal_sha256": seal["seal_sha256"],
        "integrity": integrity,
        "frozen_sentinel_parameters": {
            "bias_coefficient": SENTINEL_BIAS_COEFFICIENT,
            "risk_coefficient": SENTINEL_RISK_COEFFICIENT,
            "max_weight": SENTINEL_MAX_WEIGHT,
        },
        "summary": summary,
        "new_blind_accessed": True,
        "post_outcome_parameter_change": False,
        "stage12_authorised": False,
        "runtime_seconds": time.time() - started,
        "python": sys.version,
        "platform": platform.platform(),
    }
    final_sha = sha256_text(canonical_json(pre_record))
    record = dict(pre_record)
    record["final_record_sha256"] = final_sha
    (output_dir / "StageU5B_Complete_v1.0.json").write_text(
        json.dumps(record, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    durable = manifest(output_dir)
    durable.to_csv(
        output_dir / "StageU5B_Durable_Manifest_v1.0.csv",
        index=False,
    )
    zip_path = output_dir / "StageU5B_Canonical_Records_v1.0.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output_dir.rglob("*")):
            if path.is_file() and path != zip_path:
                archive.write(path, arcname=str(path.relative_to(output_dir)))
    zip_sha = sha256_file(zip_path)
    (output_dir / "StageU5B_Canonical_Zip_Commit_v1.0.json").write_text(
        json.dumps(
            {
                "stage": STAGE,
                "final_record_sha256": final_sha,
                "canonical_zip_sha256": zip_sha,
                "pre_outcome_seal_sha256": seal["seal_sha256"],
                "committed_utc": utc_now(),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print("\n========== STAGE U5B COMPLETE ==========")
    print("Decision:", decision)
    print("Targets / families:", summary["target_count"], summary["family_count"])
    print(
        "Direct / label-free / sentinel / oracle MAE:",
        summary["direct_overall_mae"],
        summary["label_free_overall_mae"],
        summary["sentinel_overall_mae"],
        summary["oracle_overall_mae"],
    )
    print("Budget-8 positive targets:", summary["budget8_positive_targets"])
    print(
        "Median budget-8 label leverage:",
        summary["median_budget8_label_leverage"],
    )
    print(
        "Worst family / target-budget regret:",
        summary["worst_family_regret"],
        summary["worst_target_budget_regret"],
    )
    print(
        "Bias-observability Spearman:",
        summary["bias_observability_spearman"],
    )
    print("Stage 12 authorised:", False)
    print("Final record SHA256:", final_sha)
    print("Canonical ZIP SHA256:", zip_sha)
    print("Committed to:", output_dir)
    print(gate_df.to_string(index=False))


if __name__ == "__main__":
    main()

