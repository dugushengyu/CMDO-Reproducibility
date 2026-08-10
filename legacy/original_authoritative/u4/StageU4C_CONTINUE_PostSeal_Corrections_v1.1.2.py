#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMDO Stage U4C — AUTHORISED prospective multi-family reserve — ENGINEERING/RUNNER AMENDMENT v1.0.4.

Scientific status
-----------------
This is a new outcome-blind reserve execution under the final Stage U4B
preregistration. It does not alter Stage U3C or U4A.

Reserve families
----------------
1. DIGITS: source MNIST; targets USPS, SVHN, QMNIST-test50k, EMNIST-digits.
2. CIVIL_COMMENTS: source publications selected by the frozen complement rule;
   six target publication IDs selected deterministically by target count only.
3. ACS_INCOME: source California; targets New York, Texas, Florida, Illinois.

Primary objects
---------------
- Frozen two-component-decay plus floor observability law.
- Budget-8 prediction of later direct-witness trajectories.
- Static-transport evidence validity horizon.
- Family-calibrated, reliability-gated, budget-adaptive, empirical no-harm audit.
- Deployable single-witness AUC uncertainty using a DeLong/U-statistic variance.

No target outcome is used before the pre-outcome target roster, source models,
label-free descriptors, transport predictions, risk estimates and their hashes
are sealed to disk.
"""

from __future__ import annotations

import bz2
import hashlib
import json
import math
import os
import platform
import random
import runpy
import shutil
import sys
import time
import warnings
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import ndimage
from scipy.optimize import nnls
from scipy.stats import wasserstein_distance
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import LeaveOneOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.random_projection import GaussianRandomProjection, SparseRandomProjection
from sklearn.utils import check_random_state
from skimage.feature import hog


PROJECT = "Cross-Modal_Diagnostic_Observability"
STAGE = "StageU4C_Authorised_Prospective_Component_Expiry_Safe_Audit_v1.1"
U4B_TITLE = "Stage U4B Final Prospective Component-Expiry Safe-Audit Preregistration v1.0"

EXPECTED_U4A_FINAL_RECORD_SHA256 = (
    "30e87b3d22d7423758a5cf1834eb8e7ff2d73eeed941661200b178cb0b8ae2fa"
)
EXPECTED_U4A_CANONICAL_ZIP_SHA256 = (
    "54f02263f5f944a11ca639f248a584e6cb860860e6160d297401797d2f7a404f"
)
EXPECTED_U4A_EXECUTED_PIPELINE_SHA256 = (
    "fede52ad47ebd5ac2296e81256a096b2a197bdec72a28a861da3977b2d697c8a"
)
SUPERSEDED_U4A_PREPARATION_SHA256 = (
    "d9affc39ff17d36912a13c2026e3bad1723d732c80d57211fe06447164e8d0f6"
)

BUDGETS = np.asarray([8, 16, 32, 64, 128], dtype=int)
N_REPLICATES = 200
SEED = 20260724
HARD_CLASS_ALPHA = 0.3998539033589277

# Frozen from the mean U4A direct-AUC component fractions.
P0_U4A = 0.08087937
P_HALF_U4A = 0.49109779
P_ONE_U4A = 0.42802284
Q_DECAY = P_HALF_U4A / (P_HALF_U4A + P_ONE_U4A)

# Frozen U4A adaptive-rule simplification.
BIAS_FRACTION = 1.0
RESIDUAL_QUANTILE = 0.8
MAX_TRANSPORT_WEIGHT = 0.5
DISAGREEMENT_SCALE = 2.0
SUPPORT_SCALE = 4.0
NO_HARM_SLACK = 0.0

TARGET_LIMITS = {
    "DIGITS": 5000,
    "MULTINLI_GENRES": 3000,
    "ACS_INCOME": 20000,
}
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
        Path.home() / "MyDrive" / PROJECT,
        Path("/mnt/data") / PROJECT,
        Path.cwd() / PROJECT,
    ]
    for candidate in candidates:
        if candidate.exists() and (candidate / "06_Data_Records").exists():
            return candidate.resolve()
    raise FileNotFoundError(
        "CMDO project root not found. Mount Google Drive and ensure "
        "MyDrive/Cross-Modal_Diagnostic_Observability exists."
    )


def unique_recursive(root: Path, filename: str) -> Path:
    matches = list(root.rglob(filename))
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one {filename} under {root}; found {len(matches)}."
        )
    return matches[0]


def verify_parent(project_root: Path) -> Dict[str, Any]:
    u4a_complete = unique_recursive(project_root, "StageU4A_Complete_v1.0.json")
    u4a_zip = unique_recursive(project_root, "StageU4A_Canonical_Records_v1.0.zip")
    complete = json.loads(u4a_complete.read_text(encoding="utf-8"))
    checks = {
        "u4a_complete_path": str(u4a_complete),
        "u4a_zip_path": str(u4a_zip),
        "u4a_final_record_observed": complete.get("final_record_sha256"),
        "u4a_final_record_expected": EXPECTED_U4A_FINAL_RECORD_SHA256,
        "u4a_final_record_matches": complete.get("final_record_sha256")
        == EXPECTED_U4A_FINAL_RECORD_SHA256,
        "u4a_zip_observed": sha256_file(u4a_zip),
        "u4a_zip_expected": EXPECTED_U4A_CANONICAL_ZIP_SHA256,
        "u4a_zip_matches": sha256_file(u4a_zip)
        == EXPECTED_U4A_CANONICAL_ZIP_SHA256,
        "u4a_decision": complete.get("decision"),
        "u4a_authorises_u4b_final_preregistration": bool(
            complete.get("u4b_final_preregistration_authorised")
        ),
        "u4a_new_blind_accessed": bool(complete.get("new_blind_accessed")),
        "u4a_stage12_authorised": bool(complete.get("stage12_authorised")),
        "executed_pipeline_sha256": EXPECTED_U4A_EXECUTED_PIPELINE_SHA256,
        "superseded_preparation_sha256": SUPERSEDED_U4A_PREPARATION_SHA256,
        "governance_amendment": (
            "The preparation manifest SHA is superseded by the notebook-verified "
            "executed pipeline SHA. U4A output authority is the final record and "
            "canonical ZIP above; no scientific input or result was changed."
        ),
    }
    checks["parent_integrity_pass"] = bool(
        checks["u4a_final_record_matches"]
        and checks["u4a_zip_matches"]
        and checks["u4a_authorises_u4b_final_preregistration"]
        and not checks["u4a_new_blind_accessed"]
        and not checks["u4a_stage12_authorised"]
    )
    return checks


def verify_authorisation(
    prereg_path: Path,
    auth_path: Path,
    pipeline_path: Path,
    replacement_path: Path,
    qmnist_correction_path: Path,
    multinli_correction_path: Path,
) -> Dict[str, Any]:
    auth = json.loads(auth_path.read_text(encoding="utf-8"))
    observed_prereg = sha256_file(prereg_path)
    observed_pipeline = sha256_file(pipeline_path)
    observed_replacement = sha256_file(replacement_path)
    observed_qmnist_correction = sha256_file(qmnist_correction_path)
    observed_multinli_correction = sha256_file(multinli_correction_path)
    checks = {
        "prereg_sha_observed": observed_prereg,
        "prereg_sha_authorised": auth.get("u4b_v1_1_preregistration_sha256"),
        "pipeline_sha_observed": observed_pipeline,
        "pipeline_sha_authorised": auth.get("u4c_v1_1_1_pipeline_sha256"),
        "replacement_sha_observed": observed_replacement,
        "replacement_sha_authorised": auth.get("reserve_replacement_record_sha256"),
        "qmnist_correction_sha_observed": observed_qmnist_correction,
        "qmnist_correction_sha_authorised": auth.get(
            "qmnist_correction_record_sha256"
        ),
        "multinli_correction_sha_observed": observed_multinli_correction,
        "multinli_correction_sha_authorised": auth.get(
            "multinli_alignment_correction_record_sha256"
        ),
        "authoritative_preoutcome_seal_sha256": auth.get(
            "authoritative_preoutcome_seal_sha256"
        ),
        "parent_u4a_sha": auth.get("parent_u4a_final_record_sha256"),
        "continuation_authorised": bool(auth.get("u4c_continuation_authorised")),
        "stage12_authorised": bool(auth.get("stage12_authorised")),
    }
    checks["authorisation_integrity_pass"] = bool(
        observed_prereg == auth.get("u4b_v1_1_preregistration_sha256")
        and observed_pipeline == auth.get("u4c_v1_1_1_pipeline_sha256")
        and observed_replacement == auth.get("reserve_replacement_record_sha256")
        and observed_qmnist_correction
        == auth.get("qmnist_correction_record_sha256")
        and observed_multinli_correction
        == auth.get("multinli_alignment_correction_record_sha256")
        and auth.get("authoritative_preoutcome_seal_sha256")
        == "796117600086bad5185c1e4e35cbfedddca54036cad84aac1f77e51698790144"
        and auth.get("parent_u4a_final_record_sha256")
        == EXPECTED_U4A_FINAL_RECORD_SHA256
        and auth.get("parent_u4a_canonical_zip_sha256")
        == EXPECTED_U4A_CANONICAL_ZIP_SHA256
        and auth.get("u4c_continuation_authorised") is True
        and auth.get("stage12_authorised") is False
    )
    return checks


def deterministic_indices(n: int, limit: int, seed: int) -> np.ndarray:
    if n <= limit:
        return np.arange(n, dtype=int)
    rng = np.random.default_rng(seed)
    return np.sort(rng.choice(n, size=limit, replace=False))


def entropy_binary(scores: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(scores, dtype=float), 1e-7, 1 - 1e-7)
    return -(p * np.log(p) + (1 - p) * np.log(1 - p))


def to_dense_array(x: Any) -> np.ndarray:
    if hasattr(x, "toarray"):
        return np.asarray(x.toarray(), dtype=float)
    return np.asarray(x, dtype=float)


def make_projection(x_source: Any, seed: int, n_components: int = 24):
    n_features = x_source.shape[1]
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
            abs(entropy_binary(source_scores).mean() - entropy_binary(target_scores).mean())
        ),
        "confidence_shift": float(
            abs(np.abs(source_scores - 0.5).mean() - np.abs(target_scores - 0.5).mean())
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
        pseudo_rows.append({"family": family, "environment": env["name"], **d, "auc": auc})
    pseudo = pd.DataFrame(pseudo_rows)

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

    pseudo_z = Xs
    target_rows: List[dict] = []
    for name, item in targets.items():
        d = descriptor(source_z, source_scores, item["z"], item["scores"])
        vector = np.asarray([[d[c] for c in DESCRIPTOR_COLUMNS]], dtype=float)
        vector_s = scaler.transform(vector)[0]
        min_distance = float(
            np.min(np.sqrt(np.sum((pseudo_z - vector_s.reshape(1, -1)) ** 2, axis=1)))
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


def adaptive_estimate(
    direct_auc: float,
    direct_var: float,
    transport_auc: float,
    transport_risk: float,
    support_gate: float,
) -> Tuple[float, float, bool]:
    base_weight = direct_var / (direct_var + transport_risk + 1e-12)
    disagreement_denom = DISAGREEMENT_SCALE * math.sqrt(
        direct_var + transport_risk + 1e-12
    )
    disagreement_gate = math.exp(
        -0.5 * ((direct_auc - transport_auc) / max(disagreement_denom, 1e-12)) ** 2
    )
    weight = min(
        MAX_TRANSPORT_WEIGHT,
        base_weight * support_gate * disagreement_gate,
    )
    estimated_fusion_risk = (
        (1 - weight) ** 2 * direct_var + weight**2 * transport_risk
    )
    allowed = estimated_fusion_risk <= (1 + NO_HARM_SLACK) * direct_var + 1e-12
    if not allowed:
        weight = 0.0
    estimate = (1 - weight) * direct_auc + weight * transport_auc
    return float(estimate), float(weight), bool(allowed)


def image_to_28_gray(data: np.ndarray) -> np.ndarray:
    arr = np.asarray(data)
    if arr.ndim == 4 and arr.shape[1] in (1, 3):
        arr = np.moveaxis(arr, 1, -1)
    if arr.ndim == 4 and arr.shape[-1] == 3:
        arr = np.dot(arr[..., :3], np.asarray([0.299, 0.587, 0.114]))
    if arr.ndim == 4 and arr.shape[-1] == 1:
        arr = arr[..., 0]
    if arr.ndim != 3:
        raise ValueError(f"Unsupported image array shape: {arr.shape}")
    out = np.empty((len(arr), 28, 28), dtype=np.float32)
    for i, image in enumerate(arr):
        image = image.astype(np.float32)
        if image.max() > 1.5:
            image = image / 255.0
        zoom = (28 / image.shape[0], 28 / image.shape[1])
        out[i] = ndimage.zoom(image, zoom, order=1)
    return np.clip(out, 0, 1)


def hog_features(images: np.ndarray) -> np.ndarray:
    return np.asarray(
        [
            hog(
                image,
                orientations=9,
                pixels_per_cell=(7, 7),
                cells_per_block=(2, 2),
                block_norm="L2-Hys",
            )
            for image in images
        ],
        dtype=np.float32,
    )


def prepare_digits(raw_root: Path) -> Dict[str, Any]:
    import torchvision.datasets as tvd

    root = raw_root / "digits"
    root.mkdir(parents=True, exist_ok=True)
    mnist_train = tvd.MNIST(root, train=True, download=True)
    mnist_test = tvd.MNIST(root, train=False, download=True)
    target_ds = {
        "USPS": tvd.USPS(root, train=False, download=True),
        "SVHN": tvd.SVHN(root, split="test", download=True),
        "QMNIST_TEST50K": tvd.QMNIST(root, what="test50k", compat=True, download=True),
        "EMNIST_DIGITS": tvd.EMNIST(root, split="digits", train=False, download=True),
    }

    source_idx = deterministic_indices(len(mnist_train.data), 30000, SEED + 1)
    source_images = image_to_28_gray(np.asarray(mnist_train.data)[source_idx])
    source_y = np.asarray(mnist_train.targets)[source_idx] % 2
    source_x = hog_features(source_images)

    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(
            C=1.0,
            max_iter=1000,
            class_weight="balanced",
            random_state=SEED,
        ),
    )
    model.fit(source_x, source_y)

    ref_idx = deterministic_indices(len(mnist_test.data), 3000, SEED + 2)
    ref_images = image_to_28_gray(np.asarray(mnist_test.data)[ref_idx])
    ref_y = np.asarray(mnist_test.targets)[ref_idx] % 2
    ref_x = hog_features(ref_images)
    ref_scores = model.predict_proba(ref_x)[:, 1]

    projector = make_projection(ref_x, SEED + 3)
    source_z = projector.transform(ref_x)

    pseudo_specs = [
        ("clean", lambda x: x),
        ("rot_m20", lambda x: ndimage.rotate(x, -20, reshape=False, axes=(1, 2), order=1)),
        ("rot_m10", lambda x: ndimage.rotate(x, -10, reshape=False, axes=(1, 2), order=1)),
        ("rot_p10", lambda x: ndimage.rotate(x, 10, reshape=False, axes=(1, 2), order=1)),
        ("rot_p20", lambda x: ndimage.rotate(x, 20, reshape=False, axes=(1, 2), order=1)),
        ("blur_08", lambda x: ndimage.gaussian_filter(x, sigma=(0, 0.8, 0.8))),
        ("blur_15", lambda x: ndimage.gaussian_filter(x, sigma=(0, 1.5, 1.5))),
        ("contrast_06", lambda x: np.clip((x - 0.5) * 0.6 + 0.5, 0, 1)),
        ("contrast_14", lambda x: np.clip((x - 0.5) * 1.4 + 0.5, 0, 1)),
        ("noise_10", lambda x: np.clip(x + np.random.default_rng(SEED + 4).normal(0, 0.10, x.shape), 0, 1)),
        ("noise_20", lambda x: np.clip(x + np.random.default_rng(SEED + 5).normal(0, 0.20, x.shape), 0, 1)),
        ("invert", lambda x: 1 - x),
    ]
    pseudo_envs = []
    for name, fn in pseudo_specs:
        imgs = fn(ref_images.copy())
        x = hog_features(imgs)
        scores = model.predict_proba(x)[:, 1]
        pseudo_envs.append(
            {
                "name": name,
                "z": projector.transform(x),
                "scores": scores,
                "y": ref_y,
            }
        )

    targets: Dict[str, Dict[str, Any]] = {}
    protected_labels: Dict[str, Any] = {}
    for j, (name, ds) in enumerate(target_ds.items()):
        data = np.asarray(ds.data)
        idx = deterministic_indices(len(data), TARGET_LIMITS["DIGITS"], SEED + 100 + j)
        images = image_to_28_gray(data[idx])
        x = hog_features(images)
        scores = model.predict_proba(x)[:, 1]
        targets[name] = {
            "z": projector.transform(x),
            "scores": scores,
            "indices": idx,
        }
        protected_labels[name] = {"dataset": ds, "indices": idx}

    def reveal() -> Dict[str, np.ndarray]:
        out = {}
        for name, item in protected_labels.items():
            ds, idx = item["dataset"], item["indices"]
            if hasattr(ds, "targets"):
                labels = np.asarray(ds.targets)[idx]
            elif hasattr(ds, "labels"):
                labels = np.asarray(ds.labels)[idx]
            else:
                raise AttributeError(f"Cannot locate labels for {name}")

            # Post-seal mechanical correction v1.1.1.
            # TorchVision QMNIST stores full metadata in ds.targets even when
            # compat=True; its __getitem__ returns target[0] as the digit class.
            if name == "QMNIST_TEST50K":
                if labels.ndim != 2 or labels.shape[1] < 1:
                    raise RuntimeError(
                        f"Unexpected QMNIST target shape: {labels.shape}"
                    )
                labels = labels[:, 0]
            elif labels.ndim != 1:
                raise RuntimeError(
                    f"Unexpected non-QMNIST target shape for {name}: {labels.shape}"
                )

            parity = (labels.astype(int) % 2).astype(int)
            if parity.ndim != 1 or not set(np.unique(parity)).issubset({0, 1}):
                raise RuntimeError(
                    f"Invalid binary parity labels for {name}: shape={parity.shape}"
                )
            out[name] = parity
        return out

    return {
        "family": "DIGITS",
        "source_z": source_z,
        "source_scores": ref_scores,
        "pseudo_envs": pseudo_envs,
        "targets": targets,
        "reveal": reveal,
        "acquisition": {
            "source": "torchvision MNIST train",
            "targets": list(target_ds),
            "task": "digit parity (odd=1, even=0)",
            "source_train_n": int(len(source_idx)),
            "source_reference_n": int(len(ref_idx)),
        },
    }


def bytes_to_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if hasattr(value, "decode"):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _download_https_file(url: str, path: Path, minimum_size: int) -> str:
    import requests

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size >= minimum_size:
        return sha256_file(path)

    tmp = path.with_suffix(path.suffix + ".part")
    if tmp.exists():
        tmp.unlink()
    with requests.get(url, stream=True, timeout=(30, 300), allow_redirects=True) as response:
        response.raise_for_status()
        with tmp.open("wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
    if tmp.stat().st_size < minimum_size:
        raise RuntimeError(
            f"Downloaded file is unexpectedly small: {tmp} ({tmp.stat().st_size} bytes)"
        )
    tmp.replace(path)
    return sha256_file(path)


def prepare_multinli_genres(raw_root: Path) -> Dict[str, Any]:
    root = raw_root / "multinli_genres"
    root.mkdir(parents=True, exist_ok=True)

    revision = "da70db2"
    base = (
        "https://huggingface.co/datasets/nyu-mll/multi_nli/"
        f"resolve/{revision}/data"
    )
    files = {
        "train": root / "train-00000-of-00001.parquet",
        "validation_matched": root / "validation_matched-00000-of-00001.parquet",
        "validation_mismatched": root / "validation_mismatched-00000-of-00001.parquet",
    }
    urls = {
        split: f"{base}/{path.name}?download=true"
        for split, path in files.items()
    }
    minimum_sizes = {
        "train": 150_000_000,
        "validation_matched": 3_000_000,
        "validation_mismatched": 3_000_000,
    }
    file_hashes = {
        split: _download_https_file(urls[split], files[split], minimum_sizes[split])
        for split in files
    }

    # Source-labelled data.
    train_df = pd.read_parquet(
        files["train"],
        columns=["pairID", "premise", "hypothesis", "genre", "label"],
    )
    train_df = train_df[train_df["label"].isin([0, 1, 2])].reset_index(drop=True)
    source_idx = deterministic_indices(
        len(train_df), min(120000, len(train_df)), SEED + 210
    )
    train_sample = train_df.iloc[source_idx].reset_index(drop=True)
    source_texts = (
        train_sample["premise"].astype(str)
        + " [SEP] "
        + train_sample["hypothesis"].astype(str)
    ).tolist()
    source_y = (train_sample["label"].to_numpy(dtype=int) == 0).astype(int)

    matched_df = pd.read_parquet(
        files["validation_matched"],
        columns=["pairID", "premise", "hypothesis", "genre", "label"],
    )
    matched_df = matched_df[matched_df["label"].isin([0, 1, 2])].reset_index(drop=True)
    ref_texts = (
        matched_df["premise"].astype(str)
        + " [SEP] "
        + matched_df["hypothesis"].astype(str)
    ).tolist()
    ref_y = (matched_df["label"].to_numpy(dtype=int) == 0).astype(int)
    ref_genres = matched_df["genre"].astype(str).tolist()

    vectorizer = TfidfVectorizer(
        lowercase=True,
        analyzer="char_wb",
        ngram_range=(3, 5),
        min_df=3,
        max_features=80000,
        sublinear_tf=True,
    )
    x_source = vectorizer.fit_transform(source_texts)
    model = LogisticRegression(
        C=1.0,
        max_iter=1000,
        class_weight="balanced",
        random_state=SEED,
    )
    model.fit(x_source, source_y)

    x_ref = vectorizer.transform(ref_texts)
    ref_scores = model.predict_proba(x_ref)[:, 1]
    projector = make_projection(x_ref, SEED + 211)
    source_z = projector.transform(x_ref)

    pseudo_envs: List[Dict[str, Any]] = []
    ref_y_arr = np.asarray(ref_y, dtype=int)
    for genre in sorted(set(ref_genres)):
        idx = np.asarray([i for i, value in enumerate(ref_genres) if value == genre])
        if len(idx) >= 300 and len(np.unique(ref_y_arr[idx])) == 2:
            pseudo_envs.append(
                {
                    "name": f"matched_genre_{genre}",
                    "z": source_z[idx],
                    "scores": ref_scores[idx],
                    "y": ref_y_arr[idx],
                }
            )
    lengths = np.asarray([len(text) for text in ref_texts])
    quantiles = np.quantile(lengths, [0, 0.2, 0.4, 0.6, 0.8, 1.0])
    for i in range(5):
        mask = (lengths >= quantiles[i]) & (
            lengths <= quantiles[i + 1] if i == 4 else lengths < quantiles[i + 1]
        )
        idx = np.where(mask)[0]
        if len(idx) >= 300 and len(np.unique(ref_y_arr[idx])) == 2:
            pseudo_envs.append(
                {
                    "name": f"matched_length_q{i+1}",
                    "z": source_z[idx],
                    "scores": ref_scores[idx],
                    "y": ref_y_arr[idx],
                }
            )

    # Target file is deliberately read without the label column before sealing.
    target_unlabelled = pd.read_parquet(
        files["validation_mismatched"],
        columns=["pairID", "premise", "hypothesis", "genre"],
    ).reset_index(drop=True)
    target_unlabelled["genre"] = target_unlabelled["genre"].astype(str)
    counts = target_unlabelled["genre"].value_counts()
    selected_genres = sorted(
        genre for genre, count in counts.items() if int(count) >= 512
    )
    if len(selected_genres) < 4:
        raise RuntimeError(
            f"Expected at least four MultiNLI mismatched genres; found {selected_genres}"
        )

    targets: Dict[str, Dict[str, Any]] = {}
    for genre in selected_genres:
        frame = target_unlabelled[target_unlabelled["genre"] == genre].copy()
        if len(frame) > TARGET_LIMITS["MULTINLI_GENRES"]:
            idx = deterministic_indices(
                len(frame),
                TARGET_LIMITS["MULTINLI_GENRES"],
                SEED + 220 + selected_genres.index(genre),
            )
            frame = frame.iloc[idx].copy()
        texts = (
            frame["premise"].astype(str)
            + " [SEP] "
            + frame["hypothesis"].astype(str)
        ).tolist()
        x = vectorizer.transform(texts)
        scores = model.predict_proba(x)[:, 1]
        targets[f"GENRE_{genre}"] = {
            "z": projector.transform(x),
            "scores": scores,
            "pair_ids": frame["pairID"].astype(str).to_numpy(),
            # Post-seal mechanical correction v1.1.2:
            # retain original validation_mismatched row positions because
            # MultiNLI pairID is not guaranteed to be unique.
            "row_positions": frame.index.to_numpy(dtype=int),
        }

    def reveal() -> Dict[str, np.ndarray]:
        # The label column is first read only after the authoritative
        # pre-outcome seal. Alignment is by original Parquet row position,
        # not pairID, because pairID is not a unique key.
        labelled = pd.read_parquet(
            files["validation_mismatched"],
            columns=["label"],
        ).reset_index(drop=True)
        out: Dict[str, np.ndarray] = {}
        for target, item in targets.items():
            row_positions = np.asarray(item["row_positions"], dtype=int)
            labels = labelled.iloc[row_positions]["label"].to_numpy(dtype=int)
            if len(labels) != len(item["scores"]):
                raise RuntimeError(
                    f"MultiNLI row alignment mismatch for {target}: "
                    f"labels={len(labels)}, scores={len(item['scores'])}"
                )
            if not set(np.unique(labels)).issubset({0, 1, 2}):
                raise RuntimeError(
                    f"Unexpected MultiNLI labels for {target}: "
                    f"{np.unique(labels)}"
                )
            binary = (labels == 0).astype(int)
            if set(np.unique(binary)) != {0, 1}:
                raise RuntimeError(
                    f"MultiNLI target lacks both binary classes: {target}"
                )
            out[target] = binary
        return out

    return {
        "family": "MULTINLI_GENRES",
        "source_z": source_z,
        "source_scores": ref_scores,
        "pseudo_envs": pseudo_envs,
        "targets": targets,
        "reveal": reveal,
        "acquisition": {
            "dataset": "NYU MultiNLI official Hugging Face Parquet conversion",
            "repository_revision": revision,
            "file_sha256": file_hashes,
            "source_split": "train",
            "source_reference_split": "validation_matched",
            "target_split": "validation_mismatched",
            "target_selection_rule": (
                "all lexicographically sorted mismatched genres with at least "
                "512 valid rows; no label column read before the pre-outcome seal"
            ),
            "selected_genres": selected_genres,
            "source_train_n": int(len(train_sample)),
            "source_reference_n": int(len(matched_df)),
            "task": "binary NLI: entailment=1; neutral/contradiction=0",
            "source_model": (
                "source-only char_wb TF-IDF 3-5 grams, 80k features, "
                "balanced logistic regression"
            ),
        },
    }


def prepare_acs_income(raw_root: Path) -> Dict[str, Any]:
    from folktables import ACSDataSource, ACSIncome

    root = raw_root / "acs"
    root.mkdir(parents=True, exist_ok=True)
    data_source = ACSDataSource(
        survey_year="2018",
        horizon="1-Year",
        survey="person",
        root_dir=str(root),
    )
    source_df = data_source.get_data(states=["CA"], download=True)
    x_all, y_all, _ = ACSIncome.df_to_numpy(source_df)
    idx = deterministic_indices(len(x_all), min(100000, len(x_all)), SEED + 300)
    x_all, y_all = x_all[idx], y_all[idx].astype(int)
    split = min(80000, int(0.8 * len(x_all)))
    x_train, y_train = x_all[:split], y_all[:split]
    x_ref, y_ref = x_all[split:], y_all[split:]

    model = make_pipeline(
        StandardScaler(),
        LogisticRegression(
            C=1.0,
            max_iter=1000,
            class_weight="balanced",
            random_state=SEED,
        ),
    )
    model.fit(x_train, y_train)
    ref_scores = model.predict_proba(x_ref)[:, 1]
    projector = make_projection(x_ref, SEED + 301)
    source_z = projector.transform(x_ref)

    age = x_ref[:, 0]
    hours = x_ref[:, 7]
    pseudo_envs: List[Dict[str, Any]] = []
    for name, vector in [("age", age), ("hours", hours)]:
        qs = np.quantile(vector, [0, 0.25, 0.5, 0.75, 1])
        for i in range(4):
            mask = (vector >= qs[i]) & (
                vector <= qs[i + 1] if i == 3 else vector < qs[i + 1]
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

    target_states = ["NY", "TX", "FL", "IL"]
    targets: Dict[str, Dict[str, Any]] = {}
    protected: Dict[str, np.ndarray] = {}
    for j, state in enumerate(target_states):
        df = data_source.get_data(states=[state], download=True)
        x, y, _ = ACSIncome.df_to_numpy(df)
        ix = deterministic_indices(len(x), TARGET_LIMITS["ACS_INCOME"], SEED + 320 + j)
        x, y = x[ix], y[ix].astype(int)
        scores = model.predict_proba(x)[:, 1]
        targets[state] = {"z": projector.transform(x), "scores": scores}
        protected[state] = y

    def reveal() -> Dict[str, np.ndarray]:
        return {name: value.copy() for name, value in protected.items()}

    return {
        "family": "ACS_INCOME",
        "source_z": source_z,
        "source_scores": ref_scores,
        "pseudo_envs": pseudo_envs,
        "targets": targets,
        "reveal": reveal,
        "acquisition": {
            "dataset": "folktables ACS 2018 1-Year person survey",
            "source_state": "CA",
            "target_states": target_states,
            "task": "ACSIncome",
            "source_train_n": int(len(x_train)),
            "source_reference_n": int(len(x_ref)),
        },
    }


def acquire_all(raw_root: Path) -> List[Dict[str, Any]]:
    families = []
    print("[U4C] Preparing DIGITS source model and unlabelled target scores.")
    families.append(prepare_digits(raw_root))
    print("[U4C] Preparing MULTINLI_GENRES source model and unlabelled target scores.")
    families.append(prepare_multinli_genres(raw_root))
    print("[U4C] Preparing ACS_INCOME source model and unlabelled target scores.")
    families.append(prepare_acs_income(raw_root))
    return families


def pre_outcome_transport_seal(
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
    pseudo_all.to_csv(output_dir / "StageU4C_Source_Pseudo_Environments_v1.1.csv", index=False)
    targets_all.to_csv(
        output_dir / "StageU4C_PreOutcome_Target_Descriptors_And_Transport_v1.1.csv",
        index=False,
    )
    acquisition = {
        family["family"]: family["acquisition"] for family in families
    }
    seal = {
        "created_utc": utc_now(),
        "status": "SEALED_BEFORE_TARGET_OUTCOME_USE",
        "target_count": int(len(targets_all)),
        "family_count": int(targets_all["family"].nunique()),
        "target_roster": (
            targets_all[["family", "target", "n_target_unlabelled"]]
            .sort_values(["family", "target"])
            .to_dict("records")
        ),
        "transport_models": models,
        "acquisition": acquisition,
        "target_descriptor_csv_sha256": sha256_file(
            output_dir / "StageU4C_PreOutcome_Target_Descriptors_And_Transport_v1.1.csv"
        ),
        "pseudo_environment_csv_sha256": sha256_file(
            output_dir / "StageU4C_Source_Pseudo_Environments_v1.1.csv"
        ),
    }
    seal_text = json.dumps(seal, ensure_ascii=False, indent=2, sort_keys=True)
    seal["seal_sha256"] = sha256_text(canonical_json(seal))
    (output_dir / "StageU4C_PreOutcome_Transport_Seal_v1.1.json").write_text(
        json.dumps(seal, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print("[U4C] Pre-outcome transport seal committed:", seal["seal_sha256"])
    return pseudo_all, targets_all, seal


def reveal_all_labels(families: List[Dict[str, Any]]) -> Dict[Tuple[str, str], np.ndarray]:
    labels: Dict[Tuple[str, str], np.ndarray] = {}
    for family in families:
        revealed = family["reveal"]()
        for target, y in revealed.items():
            arr = np.asarray(y, dtype=int)
            if arr.ndim != 1:
                raise RuntimeError(
                    f"Revealed labels must be 1D for {family['family']}/{target}; "
                    f"observed {arr.shape}"
                )
            if set(np.unique(arr)) != {0, 1}:
                raise RuntimeError(
                    f"Revealed labels must contain both binary classes for "
                    f"{family['family']}/{target}; observed {np.unique(arr)}"
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
                raise ValueError(f"Label-score length mismatch for {family_name}/{target}")
            if len(np.unique(y)) != 2:
                raise ValueError(f"Target {family_name}/{target} has one class only.")
            true_auc = float(roc_auc_score(y, scores))
            pos_idx = np.where(y == 1)[0]
            neg_idx = np.where(y == 0)[0]
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
                half = budget // 2
                if len(pos_idx) < half or len(neg_idx) < half:
                    raise ValueError(
                        f"Insufficient classes for {family_name}/{target} at budget {budget}."
                    )
                for replicate in range(N_REPLICATES):
                    rng = np.random.default_rng(
                        SEED + target_counter * 100000 + int(budget) * 1000 + replicate
                    )
                    sampled = np.concatenate(
                        [
                            rng.choice(pos_idx, size=half, replace=False),
                            rng.choice(neg_idx, size=half, replace=False),
                        ]
                    )
                    yy, ss = y[sampled], scores[sampled]
                    direct_auc, direct_var = delong_auc_variance(yy, ss)
                    static = 0.6 * transport_auc + 0.4 * direct_auc
                    adaptive, weight, allowed = adaptive_estimate(
                        direct_auc,
                        direct_var,
                        transport_auc,
                        transport_risk,
                        support_gate,
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
                            "transport_risk_proxy": transport_risk,
                            "support_gate": support_gate,
                            "static_fusion_auc": static,
                            "adaptive_auc": adaptive,
                            "transport_weight": weight,
                            "no_harm_gate_allowed": allowed,
                            "direct_abs_error": abs(direct_auc - true_auc),
                            "static_abs_error": abs(static - true_auc),
                            "adaptive_abs_error": abs(adaptive - true_auc),
                        }
                    )
            target_counter += 1
    replicates = pd.DataFrame(rows)
    true_metrics = pd.DataFrame(true_rows)
    return replicates, true_metrics


def state_summary(replicates: pd.DataFrame) -> pd.DataFrame:
    agg = (
        replicates.groupby(["family", "target", "budget"], as_index=False)
        .agg(
            direct_mae=("direct_abs_error", "mean"),
            static_fusion_mae=("static_abs_error", "mean"),
            adaptive_mae=("adaptive_abs_error", "mean"),
            median_direct_sd=("direct_sd", "median"),
            mean_transport_weight=("transport_weight", "mean"),
            support_gate=("support_gate", "first"),
            transport_auc=("transport_auc", "first"),
            transport_risk_proxy=("transport_risk_proxy", "first"),
            true_auc=("true_auc", "first"),
        )
    )
    agg["adaptive_regret_vs_direct"] = agg["adaptive_mae"] - agg["direct_mae"]
    agg["adaptive_gain_vs_direct"] = agg["direct_mae"] - agg["adaptive_mae"]
    agg["adaptive_gain_vs_static"] = agg["static_fusion_mae"] - agg["adaptive_mae"]
    return agg


def fit_amplitude(budgets: np.ndarray, errors: np.ndarray, shape: np.ndarray) -> float:
    return float(np.dot(errors, shape) / max(np.dot(shape, shape), 1e-12))


def frozen_component_shape(budgets: np.ndarray) -> np.ndarray:
    x = budgets / 8.0
    return P0_U4A + P_HALF_U4A * x ** -0.5 + P_ONE_U4A * x ** -1.0


def constrained_component_shape(budgets: np.ndarray, floor_fraction: float) -> np.ndarray:
    x = budgets / 8.0
    decaying = Q_DECAY * x ** -0.5 + (1 - Q_DECAY) * x ** -1.0
    return floor_fraction + (1 - floor_fraction) * decaying


def component_predictions(states: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    fit_rows, prediction_rows = [], []
    for keys, group in states.groupby(["family", "target"], sort=True):
        group = group.sort_values("budget")
        budgets = group["budget"].to_numpy(dtype=float)
        errors = group["direct_mae"].to_numpy(dtype=float)
        early = budgets <= 32
        late = budgets >= 64
        b_early, e_early = budgets[early], errors[early]

        # Fully frozen U4A component shape: only amplitude fitted.
        fshape = frozen_component_shape(b_early)
        famp = fit_amplitude(b_early, e_early, fshape)
        frozen_pred = famp * frozen_component_shape(budgets)

        # Primary parsimonious target-updated component law:
        # U4A fixes the ratio of the two decaying components; only amplitude and
        # floor fraction are selected on a fixed 0..0.8 grid using early budgets.
        best = None
        for floor_fraction in np.linspace(0, 0.8, 81):
            shape = constrained_component_shape(b_early, floor_fraction)
            amp = fit_amplitude(b_early, e_early, shape)
            pred = amp * shape
            mae = float(np.mean(np.abs(pred - e_early)))
            candidate = (mae, float(floor_fraction), amp)
            if best is None or candidate < best:
                best = candidate
        assert best is not None
        _, floor_fraction, amp = best
        component_pred = amp * constrained_component_shape(budgets, floor_fraction)

        hard_shape = (budgets / 8.0) ** -HARD_CLASS_ALPHA
        hard_amp = fit_amplitude(
            b_early,
            e_early,
            (b_early / 8.0) ** -HARD_CLASS_ALPHA,
        )
        hard_pred = hard_amp * hard_shape

        root_shape = (budgets / 8.0) ** -0.5
        root_amp = fit_amplitude(b_early, e_early, (b_early / 8.0) ** -0.5)
        root_pred = root_amp * root_shape

        family, target = keys
        fit_rows.append(
            {
                "family": family,
                "target": target,
                "frozen_component_amplitude": famp,
                "updated_component_amplitude": amp,
                "updated_floor_fraction": floor_fraction,
                "frozen_q_decay": Q_DECAY,
                "component_late_mae": float(np.mean(np.abs(component_pred[late] - errors[late]))),
                "frozen_component_late_mae": float(np.mean(np.abs(frozen_pred[late] - errors[late]))),
                "hard_class_late_mae": float(np.mean(np.abs(hard_pred[late] - errors[late]))),
                "rootn_late_mae": float(np.mean(np.abs(root_pred[late] - errors[late]))),
            }
        )
        for i, budget in enumerate(budgets):
            prediction_rows.append(
                {
                    "family": family,
                    "target": target,
                    "budget": int(budget),
                    "truth_direct_mae": errors[i],
                    "component_pred": component_pred[i],
                    "frozen_component_pred": frozen_pred[i],
                    "hard_class_pred": hard_pred[i],
                    "rootn_pred": root_pred[i],
                    "is_late": bool(late[i]),
                }
            )
    return pd.DataFrame(fit_rows), pd.DataFrame(prediction_rows)


def empirical_expiry(states: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, group in states.groupby(["family", "target"], sort=True):
        group = group.sort_values("budget")
        benefit = group["direct_mae"].to_numpy() - group["static_fusion_mae"].to_numpy()
        budgets = group["budget"].to_numpy(dtype=int)
        positive = benefit > 0
        if not positive[0]:
            empirical = 8
        else:
            empirical = 256
            for i in range(1, len(budgets)):
                if not positive[i]:
                    empirical = int(budgets[i])
                    break

        first = group.iloc[0]
        direct_mae_proxy = math.sqrt(2 / math.pi) * float(first["median_direct_sd"])
        transport_rmse_proxy = math.sqrt(float(first["transport_risk_proxy"]))
        if transport_rmse_proxy <= 1e-12:
            predicted = 256.0
        else:
            predicted = 8.0 * (direct_mae_proxy / transport_rmse_proxy) ** 2
        predicted = float(np.clip(predicted, 8, 256))
        distance_levels = abs(math.log2(predicted / empirical))
        rows.append(
            {
                "family": keys[0],
                "target": keys[1],
                "empirical_expiry_budget": empirical,
                "predicted_expiry_budget_from_budget8": predicted,
                "log2_budget_distance": distance_levels,
                "within_one_budget_level": bool(distance_levels <= 1.0),
                "positive_budget_count": int(positive.sum()),
                **{
                    f"benefit_budget_{int(b)}": float(v)
                    for b, v in zip(budgets, benefit)
                },
            }
        )
    return pd.DataFrame(rows)


def equivalent_budget(direct_curve: pd.DataFrame, target_error: float) -> float:
    curve = direct_curve.sort_values("budget")
    budgets = curve["budget"].to_numpy(dtype=float)
    errors = curve["direct_mae"].to_numpy(dtype=float)
    order = np.argsort(errors)
    e, b = errors[order], budgets[order]
    if target_error <= e[0]:
        if len(e) >= 2 and e[1] > 0 and e[0] > 0:
            alpha = max(
                0.05,
                -math.log(e[0] / e[1]) / math.log(b[0] / b[1]),
            )
            return float(np.clip(b[0] * (e[0] / max(target_error, 1e-12)) ** (1 / alpha), 8, 2048))
        return float(b[0])
    if target_error >= e[-1]:
        return float(max(2.0, b[-1] * e[-1] / target_error))
    return float(np.exp(np.interp(np.log(target_error), np.log(e), np.log(b))))


def add_leverage(states: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, group in states.groupby(["family", "target"], sort=True):
        for record in group.to_dict("records"):
            eq = equivalent_budget(group, float(record["adaptive_mae"]))
            record["adaptive_equivalent_direct_budget"] = eq
            record["adaptive_label_leverage"] = eq / float(record["budget"])
            rows.append(record)
    return pd.DataFrame(rows)


def evaluate_gates(
    states: pd.DataFrame,
    fits: pd.DataFrame,
    expiry: pd.DataFrame,
    integrity: Mapping[str, Any],
    authorisation: Mapping[str, Any],
) -> Tuple[pd.DataFrame, Dict[str, Any], str]:
    component_mae = float(fits["component_late_mae"].mean())
    hard_mae = float(fits["hard_class_late_mae"].mean())
    root_mae = float(fits["rootn_late_mae"].mean())
    gain_hard = 1 - component_mae / hard_mae
    gain_root = 1 - component_mae / root_mae
    target_beats_hard = int(np.sum(fits["component_late_mae"] < fits["hard_class_late_mae"]))
    target_beats_root = int(np.sum(fits["component_late_mae"] < fits["rootn_late_mae"]))

    direct = float(states["direct_mae"].mean())
    static = float(states["static_fusion_mae"].mean())
    adaptive = float(states["adaptive_mae"].mean())
    budget8 = states[states["budget"] == 8]
    family_regret = (
        states.groupby("family")[["adaptive_mae", "direct_mae"]].mean()
    )
    family_regret["regret"] = family_regret["adaptive_mae"] - family_regret["direct_mae"]
    median_weights = states.groupby("budget")["mean_transport_weight"].median()
    nonincreasing = bool(np.all(np.diff(median_weights.to_numpy()) <= 1e-10))
    target_count = int(states[["family", "target"]].drop_duplicates().shape[0])

    summary = {
        "target_count": target_count,
        "family_count": int(states["family"].nunique()),
        "component_late_mae": component_mae,
        "hard_class_late_mae": hard_mae,
        "rootn_late_mae": root_mae,
        "component_gain_vs_hard": gain_hard,
        "component_gain_vs_rootn": gain_root,
        "targets_component_beats_hard": target_beats_hard,
        "targets_component_beats_rootn": target_beats_root,
        "direct_overall_mae": direct,
        "static_overall_mae": static,
        "adaptive_overall_mae": adaptive,
        "adaptive_gain_vs_direct": 1 - adaptive / direct,
        "adaptive_gain_vs_static": 1 - adaptive / static,
        "budget8_positive_targets": int(np.sum(budget8["adaptive_mae"] < budget8["direct_mae"])),
        "median_budget8_label_leverage": float(budget8["adaptive_label_leverage"].median()),
        "worst_target_budget_regret": float(states["adaptive_regret_vs_direct"].max()),
        "worst_family_regret": float(family_regret["regret"].max()),
        "expiry_within_one_level": int(expiry["within_one_budget_level"].sum()),
        "median_transport_weight_by_budget": {
            str(int(k)): float(v) for k, v in median_weights.items()
        },
        "weight_nonincreasing": nonincreasing,
    }

    gates = [
        {
            "gate": "integrity_and_execution_authorisation",
            "passed": bool(
                integrity["parent_integrity_pass"]
                and authorisation["authorisation_integrity_pass"]
            ),
            "observed": (
                f"parent={integrity['parent_integrity_pass']};"
                f"authorisation={authorisation['authorisation_integrity_pass']}"
            ),
        },
        {
            "gate": "reserve_roster_at_least_12_targets_3_families",
            "passed": target_count >= 12 and summary["family_count"] >= 3,
            "observed": f"{target_count} targets; {summary['family_count']} families",
        },
        {
            "gate": "component_pooled_gain_at_least_15_percent",
            "passed": gain_hard >= 0.15 and gain_root >= 0.15,
            "observed": f"vs_hard={gain_hard:.6f};vs_rootn={gain_root:.6f}",
        },
        {
            "gate": "component_target_majority",
            "passed": (
                target_beats_hard >= math.ceil(2 * target_count / 3)
                and target_beats_root >= math.ceil(2 * target_count / 3)
            ),
            "observed": (
                f"hard={target_beats_hard}/{target_count};"
                f"rootn={target_beats_root}/{target_count}"
            ),
        },
        {
            "gate": "expiry_prediction_within_adjacent_budget",
            "passed": summary["expiry_within_one_level"] >= math.ceil(0.6 * target_count),
            "observed": f"{summary['expiry_within_one_level']}/{target_count}",
        },
        {
            "gate": "adaptive_pooled_noninferior_and_beats_static",
            "passed": adaptive <= 1.02 * direct and adaptive < static,
            "observed": (
                f"adaptive={adaptive:.6f};direct={direct:.6f};static={static:.6f}"
            ),
        },
        {
            "gate": "adaptive_low_budget_utility",
            "passed": (
                summary["budget8_positive_targets"] >= math.ceil(0.6 * target_count)
                and summary["median_budget8_label_leverage"] >= 1.15
            ),
            "observed": (
                f"positive={summary['budget8_positive_targets']}/{target_count};"
                f"median_leverage={summary['median_budget8_label_leverage']:.6f}"
            ),
        },
        {
            "gate": "adaptive_regret_control",
            "passed": (
                summary["worst_family_regret"] <= 0.005
                and summary["worst_target_budget_regret"] <= 0.01
            ),
            "observed": (
                f"family={summary['worst_family_regret']:.6f};"
                f"target_budget={summary['worst_target_budget_regret']:.6f}"
            ),
        },
        {
            "gate": "transport_weight_exits_with_budget",
            "passed": nonincreasing and median_weights.loc[128] <= 0.05,
            "observed": json.dumps(summary["median_transport_weight_by_budget"]),
        },
        {"gate": "new_blind_accessed", "passed": True, "observed": True},
        {"gate": "stage12_authorised", "passed": True, "observed": False},
    ]
    gate_df = pd.DataFrame(gates)

    primary_names = [
        "component_pooled_gain_at_least_15_percent",
        "component_target_majority",
        "expiry_prediction_within_adjacent_budget",
        "adaptive_pooled_noninferior_and_beats_static",
        "adaptive_low_budget_utility",
        "adaptive_regret_control",
        "transport_weight_exits_with_budget",
    ]
    integrity_pass = bool(gate_df.iloc[:2]["passed"].all())
    primary_pass = bool(
        gate_df[gate_df["gate"].isin(primary_names)]["passed"].all()
    )
    component_method_pass = bool(
        gate_df[
            gate_df["gate"].isin(
                [
                    "component_pooled_gain_at_least_15_percent",
                    "component_target_majority",
                    "adaptive_pooled_noninferior_and_beats_static",
                    "adaptive_regret_control",
                ]
            )
        ]["passed"].all()
    )
    if integrity_pass and primary_pass:
        decision = (
            "SEAL_STAGEU4C_STRONG_PROSPECTIVE_SUPPORT_COMPONENT_UNIVERSALITY_"
            "EVIDENCE_EXPIRY_AND_SAFE_SEQUENTIAL_AUDIT_NATURE_ROUTE_ELIGIBLE_"
            "STAGE12_STILL_PROHIBITED"
        )
    elif integrity_pass and component_method_pass:
        decision = (
            "SEAL_STAGEU4C_PARTIAL_PROSPECTIVE_SUPPORT_COMPONENT_AND_SAFE_AUDIT_"
            "SUPPORTED_EXPIRY_OR_LOW_BUDGET_GATE_PARTIAL_REROUTE_NMI_TPAMI_"
            "STAGE12_PROHIBITED"
        )
    else:
        decision = (
            "SEAL_STAGEU4C_PROSPECTIVE_RESERVE_PARTIAL_OR_FAILED_RETAIN_ALL_"
            "RESULTS_REROUTE_STAGE12_PROHIBITED"
        )
    return gate_df, summary, decision


def make_figures(
    output_dir: Path,
    states: pd.DataFrame,
    predictions: pd.DataFrame,
    expiry: pd.DataFrame,
    target_transport: pd.DataFrame,
) -> None:
    fig = plt.figure(figsize=(9, 6))
    late = predictions[predictions["is_late"]]
    methods = ["component_pred", "hard_class_pred", "rootn_pred"]
    values = [
        np.mean(np.abs(late[m] - late["truth_direct_mae"]))
        for m in methods
    ]
    plt.bar(methods, values)
    plt.ylabel("Late-budget prediction MAE")
    plt.title("Prospective observability-law prediction")
    plt.tight_layout()
    fig.savefig(output_dir / "Figure_U4C_1_Component_Prediction.png", dpi=220)
    plt.close(fig)

    fig = plt.figure(figsize=(9, 6))
    for keys, group in states.groupby(["family", "target"]):
        plt.plot(group["budget"], group["direct_mae"], marker="o", alpha=0.7)
    plt.xscale("log", base=2)
    plt.yscale("log")
    plt.xlabel("Target-label budget")
    plt.ylabel("Direct AUC witness MAE")
    plt.title("Untouched multi-family direct observability trajectories")
    plt.tight_layout()
    fig.savefig(output_dir / "Figure_U4C_2_Direct_Trajectories.png", dpi=220)
    plt.close(fig)

    fig = plt.figure(figsize=(9, 6))
    for _, row in expiry.iterrows():
        vals = [row[f"benefit_budget_{b}"] for b in BUDGETS]
        plt.plot(BUDGETS, vals, marker="o", alpha=0.7)
    plt.axhline(0)
    plt.xscale("log", base=2)
    plt.xlabel("Target-label budget")
    plt.ylabel("Direct MAE − static-fusion MAE")
    plt.title("Prospective evidence-validity horizons")
    plt.tight_layout()
    fig.savefig(output_dir / "Figure_U4C_3_Evidence_Expiry.png", dpi=220)
    plt.close(fig)

    fig = plt.figure(figsize=(9, 6))
    method = states.groupby("budget")[
        ["direct_mae", "static_fusion_mae", "adaptive_mae"]
    ].median()
    for col in method.columns:
        plt.plot(method.index, method[col], marker="o", label=col)
    plt.xscale("log", base=2)
    plt.yscale("log")
    plt.xlabel("Target-label budget")
    plt.ylabel("Median AUC estimation MAE")
    plt.title("Reliability-gated sequential audit")
    plt.legend()
    plt.tight_layout()
    fig.savefig(output_dir / "Figure_U4C_4_Method_Comparison.png", dpi=220)
    plt.close(fig)

    fig = plt.figure(figsize=(9, 6))
    weights = states.groupby("budget")["mean_transport_weight"].agg(["median", "min", "max"])
    plt.plot(weights.index, weights["median"], marker="o")
    plt.fill_between(weights.index, weights["min"], weights["max"], alpha=0.2)
    plt.xscale("log", base=2)
    plt.xlabel("Target-label budget")
    plt.ylabel("Transport weight")
    plt.title("Indirect evidence exits as direct evidence accumulates")
    plt.tight_layout()
    fig.savefig(output_dir / "Figure_U4C_5_Transport_Exit.png", dpi=220)
    plt.close(fig)

    fig = plt.figure(figsize=(9, 6))
    merged = target_transport.copy()
    plt.scatter(
        merged["support_gate"],
        merged["transport_risk_proxy"],
    )
    for _, row in merged.iterrows():
        plt.annotate(row["target"], (row["support_gate"], row["transport_risk_proxy"]), fontsize=6)
    plt.yscale("log")
    plt.xlabel("Label-free support gate")
    plt.ylabel("Calibrated transport risk proxy")
    plt.title("Transport reliability across untouched targets")
    plt.tight_layout()
    fig.savefig(output_dir / "Figure_U4C_6_Transport_Reliability.png", dpi=220)
    plt.close(fig)


def write_manuscript_insert(
    output_dir: Path,
    summary: Mapping[str, Any],
    gate_df: pd.DataFrame,
    decision: str,
) -> Path:
    text = f"""# Stage U4C prospective reserve result

Decision: `{decision}`

The final Stage U4B protocol evaluated {summary['target_count']} untouched target
environments across {summary['family_count']} families: cross-domain digit
images, publication-domain toxicity classification and cross-state income
classification. Target outcomes were used only after the target roster,
label-free descriptors, source-only transport models and transport predictions
were sealed.

## Component universality

The parsimonious component law achieved late-budget MAE
{summary['component_late_mae']:.6f}, compared with
{summary['hard_class_late_mae']:.6f} for the rejected hard ranking exponent and
{summary['rootn_late_mae']:.6f} for root-n. Relative gains were
{summary['component_gain_vs_hard']:.6f} and
{summary['component_gain_vs_rootn']:.6f}, respectively.

## Evidence expiry

Predicted expiry was within one adjacent budget level in
{summary['expiry_within_one_level']}/{summary['target_count']} targets.

## Safe sequential audit

Direct-only overall MAE: {summary['direct_overall_mae']:.6f}.
Static fusion overall MAE: {summary['static_overall_mae']:.6f}.
Adaptive audit overall MAE: {summary['adaptive_overall_mae']:.6f}.
Adaptive relative gain versus direct: {summary['adaptive_gain_vs_direct']:.6f}.
Adaptive relative gain versus static fusion: {summary['adaptive_gain_vs_static']:.6f}.
Budget-8 positive targets: {summary['budget8_positive_targets']}/{summary['target_count']}.
Median budget-8 label leverage: {summary['median_budget8_label_leverage']:.6f}.
Worst family regret: {summary['worst_family_regret']:.6f}.
Worst target-budget regret: {summary['worst_target_budget_regret']:.6f}.

## Claim boundary

This is the first new prospective test of the post-U3C component/expiry/safe-audit
theory. Stage U3C remains partial/failed and Stage U4A remains transparent
development. Stage 12 is not authorised by this result.

## Gate table

{gate_df.to_markdown(index=False)}
"""
    path = output_dir / "StageU4C_Manuscript_Insert_v1.1.md"
    path.write_text(text, encoding="utf-8")
    return path


def manifest(output_dir: Path) -> pd.DataFrame:
    rows = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name not in {
            "StageU4C_Durable_Manifest_v1.1.csv",
            "StageU4C_Canonical_Records_v1.1.zip",
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
    np.random.seed(SEED)
    random.seed(SEED)
    warnings.filterwarnings("ignore", category=FutureWarning)

    pipeline_path = Path(__file__).resolve()
    prereg_path = Path(os.environ["CMDO_U4B_PREREG_PATH"]).resolve()
    auth_path = Path(os.environ["CMDO_U4C_AUTH_PATH"]).resolve()
    replacement_path = Path(os.environ["CMDO_U4B_REPLACEMENT_PATH"]).resolve()
    qmnist_correction_path = Path(
        os.environ["CMDO_U4C_QMNIST_CORRECTION_PATH"]
    ).resolve()
    multinli_correction_path = Path(
        os.environ["CMDO_U4C_MULTINLI_CORRECTION_PATH"]
    ).resolve()

    project_root = locate_project_root()
    parent_integrity = verify_parent(project_root)
    authorisation = verify_authorisation(
        prereg_path,
        auth_path,
        pipeline_path,
        replacement_path,
        qmnist_correction_path,
        multinli_correction_path,
    )
    if not parent_integrity["parent_integrity_pass"]:
        raise RuntimeError(f"U4A parent integrity failed: {parent_integrity}")
    if not authorisation["authorisation_integrity_pass"]:
        raise RuntimeError(f"Continuation authorisation failed: {authorisation}")

    output_dir = (
        project_root / "06_Data_Records" / "Cross_Modal" / STAGE
    )
    if not output_dir.exists():
        raise RuntimeError(
            "Authoritative sealed U4C v1.1 output folder is missing; "
            "continuation is prohibited."
        )

    seal_path = output_dir / "StageU4C_PreOutcome_Transport_Seal_v1.1.json"
    descriptor_path = (
        output_dir
        / "StageU4C_PreOutcome_Target_Descriptors_And_Transport_v1.1.csv"
    )
    pseudo_path = output_dir / "StageU4C_Source_Pseudo_Environments_v1.1.csv"
    if not all(path.exists() for path in [seal_path, descriptor_path, pseudo_path]):
        raise RuntimeError("The authoritative pre-outcome seal bundle is incomplete.")

    authoritative_seal = json.loads(seal_path.read_text(encoding="utf-8"))
    if authoritative_seal.get("seal_sha256") != "796117600086bad5185c1e4e35cbfedddca54036cad84aac1f77e51698790144":
        raise RuntimeError(
            "Unexpected authoritative seal SHA: "
            f"{authoritative_seal.get('seal_sha256')}"
        )
    if sha256_file(descriptor_path) != authoritative_seal.get(
        "target_descriptor_csv_sha256"
    ):
        raise RuntimeError("Authoritative target descriptor CSV integrity failed.")
    if sha256_file(pseudo_path) != authoritative_seal.get(
        "pseudo_environment_csv_sha256"
    ):
        raise RuntimeError("Authoritative pseudo-environment CSV integrity failed.")

    print(
        "[U4C v1.1.2] Authoritative pre-outcome seal verified:",
        authoritative_seal["seal_sha256"],
    )
    print(
        "[U4C v1.1.2] Blind was accessed after this seal; only the exact "
        "QMNIST target[0] adapter and MultiNLI original-row alignment "
        "corrections are authorised."
    )

    shutil.copy2(
        auth_path,
        output_dir / "U4C_CONTINUATION_AUTHORIZATION_v1.1.1.json",
    )
    shutil.copy2(
        qmnist_correction_path,
        output_dir / "StageU4C_PostSeal_QMNIST_Label_Adapter_Correction_v1.1.1.txt",
    )
    shutil.copy2(
        multinli_correction_path,
        output_dir / "StageU4C_PostSeal_MultiNLI_Row_Alignment_Correction_v1.1.2.txt",
    )
    shutil.copy2(pipeline_path, output_dir / pipeline_path.name)

    # Remove only downstream products from an incomplete attempt, preserving
    # the authoritative pre-outcome seal bundle and parent governance files.
    downstream_names = [
        "StageU4C_AUC_Witness_Replicates_v1.1.csv.gz",
        "StageU4C_Target_True_Metrics_v1.1.csv",
        "StageU4C_Audit_State_Results_v1.1.csv",
        "StageU4C_Component_Fits_v1.1.csv",
        "StageU4C_Component_Trajectory_Predictions_v1.1.csv",
        "StageU4C_Evidence_Expiry_Map_v1.1.csv",
        "StageU4C_Gate_Table_v1.1.csv",
        "StageU4C_Manuscript_Insert_v1.1.md",
        "StageU4C_Complete_v1.1.json",
        "StageU4C_Durable_Manifest_v1.1.csv",
        "StageU4C_Canonical_Records_v1.1.zip",
        "StageU4C_Canonical_Zip_Commit_v1.1.json",
    ]
    for name in downstream_names:
        path = output_dir / name
        if path.exists():
            path.unlink()

    raw_root = Path("/content/cmdo_u4c_ephemeral_raw")
    raw_root.mkdir(parents=True, exist_ok=True)

    print("[U4C v1.1.2] Reconstructing source-only state for seal equivalence.")
    families = acquire_all(raw_root)

    reconstruction_dir = Path("/content/cmdo_u4c_v111_seal_reconstruction")
    if reconstruction_dir.exists():
        shutil.rmtree(reconstruction_dir)
    reconstruction_dir.mkdir(parents=True, exist_ok=False)
    _, target_transport, reconstructed_seal = pre_outcome_transport_seal(
        families, reconstruction_dir
    )
    reconstructed_descriptor = (
        reconstruction_dir
        / "StageU4C_PreOutcome_Target_Descriptors_And_Transport_v1.1.csv"
    )
    reconstructed_pseudo = (
        reconstruction_dir / "StageU4C_Source_Pseudo_Environments_v1.1.csv"
    )

    descriptor_match = (
        sha256_file(reconstructed_descriptor)
        == authoritative_seal["target_descriptor_csv_sha256"]
    )
    pseudo_match = (
        sha256_file(reconstructed_pseudo)
        == authoritative_seal["pseudo_environment_csv_sha256"]
    )
    roster_match = (
        reconstructed_seal["target_roster"]
        == authoritative_seal["target_roster"]
    )
    if not (descriptor_match and pseudo_match and roster_match):
        raise RuntimeError(
            "Reconstructed source-only state does not match the authoritative "
            f"seal: descriptor={descriptor_match}, pseudo={pseudo_match}, "
            f"roster={roster_match}. Continuation prohibited."
        )

    print("[U4C v1.1.2] Source-only reconstruction exactly matches sealed hashes.")
    print("[U4C v1.1.2] Applying QMNIST target[0] adapter and continuing witnesses.")

    labels = reveal_all_labels(families)
    replicates, true_metrics = run_witnesses(
        families, target_transport, labels
    )
    states = add_leverage(state_summary(replicates))
    fits, predictions = component_predictions(states)
    expiry = empirical_expiry(states)

    replicates.to_csv(
        output_dir / "StageU4C_AUC_Witness_Replicates_v1.1.csv.gz",
        index=False,
        compression="gzip",
    )
    true_metrics.to_csv(
        output_dir / "StageU4C_Target_True_Metrics_v1.1.csv", index=False
    )
    states.to_csv(
        output_dir / "StageU4C_Audit_State_Results_v1.1.csv", index=False
    )
    fits.to_csv(output_dir / "StageU4C_Component_Fits_v1.1.csv", index=False)
    predictions.to_csv(
        output_dir / "StageU4C_Component_Trajectory_Predictions_v1.1.csv",
        index=False,
    )
    expiry.to_csv(
        output_dir / "StageU4C_Evidence_Expiry_Map_v1.1.csv", index=False
    )

    gate_df, summary, decision = evaluate_gates(
        states, fits, expiry, parent_integrity, authorisation
    )
    gate_df.to_csv(
        output_dir / "StageU4C_Gate_Table_v1.1.csv", index=False
    )
    make_figures(output_dir, states, predictions, expiry, target_transport)
    write_manuscript_insert(output_dir, summary, gate_df, decision)

    qmnist_correction_sha = sha256_file(qmnist_correction_path)
    multinli_correction_sha = sha256_file(multinli_correction_path)
    pre_record = {
        "stage": STAGE,
        "status": "AUTHORISED_PROSPECTIVE_RESERVE_WITH_POSTSEAL_MECHANICAL_CORRECTION",
        "created_utc": utc_now(),
        "decision": decision,
        "parent_u4a_final_record_sha256": EXPECTED_U4A_FINAL_RECORD_SHA256,
        "parent_u4a_canonical_zip_sha256": EXPECTED_U4A_CANONICAL_ZIP_SHA256,
        "parent_integrity": parent_integrity,
        "authorisation_integrity": authorisation,
        "authoritative_pre_outcome_transport_seal_sha256": "796117600086bad5185c1e4e35cbfedddca54036cad84aac1f77e51698790144",
        "source_only_reconstruction_descriptor_match": descriptor_match,
        "source_only_reconstruction_pseudo_match": pseudo_match,
        "source_only_reconstruction_roster_match": roster_match,
        "qmnist_correction_record_sha256": qmnist_correction_sha,
        "multinli_alignment_correction_record_sha256": multinli_correction_sha,
        "postseal_corrections": [
            (
                "QMNIST ds.targets is a 2D metadata tensor; use column 0 "
                "as the digit class."
            ),
            (
                "MultiNLI pairID is not a unique alignment key; read target "
                "labels by the original validation_mismatched Parquet row "
                "positions used to generate the sealed scores."
            ),
        ],
        "blind_accessed_before_correction": True,
        "scientific_parameter_or_gate_changed": False,
        "summary": summary,
        "new_blind_accessed": True,
        "stage12_authorised": False,
        "runtime_seconds": time.time() - started,
        "python": sys.version,
        "platform": platform.platform(),
    }
    final_sha = sha256_text(canonical_json(pre_record))
    record = dict(pre_record)
    record["final_record_sha256"] = final_sha
    (output_dir / "StageU4C_Complete_v1.1.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    man = manifest(output_dir)
    man.to_csv(
        output_dir / "StageU4C_Durable_Manifest_v1.1.csv", index=False
    )
    zip_path = output_dir / "StageU4C_Canonical_Records_v1.1.zip"
    with zipfile.ZipFile(
        zip_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for path in sorted(output_dir.rglob("*")):
            if path.is_file() and path != zip_path:
                archive.write(
                    path, arcname=str(path.relative_to(output_dir))
                )
    zip_sha = sha256_file(zip_path)
    (output_dir / "StageU4C_Canonical_Zip_Commit_v1.1.json").write_text(
        json.dumps(
            {
                "stage": STAGE,
                "final_record_sha256": final_sha,
                "canonical_zip_sha256": zip_sha,
                "authoritative_preoutcome_seal_sha256": "796117600086bad5185c1e4e35cbfedddca54036cad84aac1f77e51698790144",
                "qmnist_correction_record_sha256": qmnist_correction_sha,
                "multinli_alignment_correction_record_sha256": (
                    multinli_correction_sha
                ),
                "committed_utc": utc_now(),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print("\n========== STAGE U4C COMPLETE ==========")
    print("Decision:", decision)
    print("Authoritative pre-outcome seal:", "796117600086bad5185c1e4e35cbfedddca54036cad84aac1f77e51698790144")
    print("Post-seal QMNIST correction applied:", True)
    print("Post-seal MultiNLI row-alignment correction applied:", True)
    print("Targets / families:", summary["target_count"], summary["family_count"])
    print("Component late-budget MAE:", summary["component_late_mae"])
    print("Hard-class late-budget MAE:", summary["hard_class_late_mae"])
    print("Root-n late-budget MAE:", summary["rootn_late_mae"])
    print(
        "Component gain vs hard/root-n:",
        summary["component_gain_vs_hard"],
        summary["component_gain_vs_rootn"],
    )
    print(
        "Expiry within one level:",
        summary["expiry_within_one_level"],
        "/",
        summary["target_count"],
    )
    print(
        "Adaptive / direct / static MAE:",
        summary["adaptive_overall_mae"],
        summary["direct_overall_mae"],
        summary["static_overall_mae"],
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
    print("Blind accessed:", True)
    print("Scientific parameter or gate changed:", False)
    print("Stage 12 authorised:", False)
    print("Final record SHA256:", final_sha)
    print("Canonical ZIP SHA256:", zip_sha)
    print("Committed to:", output_dir)
    print(gate_df.to_string(index=False))


if __name__ == "__main__":
    main()

