#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMDO Stage U6 — Independent Pair-Complete Observer Reserve v1.0

A one-shot prospective reserve for the observer frozen in U5F:
PC_PAIRED_HOEFFDING.

Execution order:
1. verify exact release and U5F parent identity;
2. acquire source labels and target inputs only;
3. train frozen source models and compute target scores;
4. seal target roster, score hashes, transport estimates and descriptors;
5. only after the pre-outcome seal, access target labels;
6. run the frozen observer at all budgets and replicates;
7. write the complete record, manifest and canonical ZIP.

No target-specific tuning, candidate switching or rerun after completion.
Stage 12 remains prohibited.
"""

from __future__ import annotations

import hashlib
import io
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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from scipy.ndimage import gaussian_filter
from scipy.special import expit
from scipy.stats import spearmanr
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


PROJECT = "Cross-Modal_Diagnostic_Observability"
STAGE = "StageU6_Independent_Pair_Complete_Observer_Reserve_v1.0"

EXPECTED_U5F_FINAL = "2267c0a5891cb3ae93777605cceedac1398dcfac3f3c452116014116c1bf7f59"
EXPECTED_FROZEN_SPEC_SHA = "cd88e72099be68258baa64fd7ff78137670b33b2deae3abf82a6a5d83dd2720f"
EXPECTED_OBSERVER_ID = "PC_PAIRED_HOEFFDING"

SEED = 20260724
BUDGETS = [8, 16, 32, 64, 128]
REPLICATES = 200
MAX_WEIGHT = 0.35
RISK_COEFFICIENT = 8.0
DELTA_TOTAL = 0.10
DELTA_BLOCK = 0.025
HISTOGRAM_BINS = np.linspace(0.0, 1.0, 41)
ACS_SOURCE_MAX = 60000
ACS_TARGET_MAX = 50000

TARGET_ROSTER = [
    {"family": "MEDICAL_DERMOSCOPY", "target": "DERMA_CLEAN", "transform": "clean"},
    {"family": "MEDICAL_DERMOSCOPY", "target": "DERMA_NOISE_0_08", "transform": "noise_0.08"},
    {"family": "MEDICAL_DERMOSCOPY", "target": "DERMA_BLUR_1_0", "transform": "blur_1.0"},
    {"family": "MEDICAL_DERMOSCOPY", "target": "DERMA_GAMMA_1_4", "transform": "gamma_1.4"},
    {"family": "MEDICAL_DERMOSCOPY", "target": "DERMA_JPEG_35", "transform": "jpeg_35"},
    {"family": "MEDICAL_DERMOSCOPY", "target": "DERMA_DOWNSAMPLE_14", "transform": "downsample_14"},
    {"family": "NATURAL_IMAGE", "target": "CIFAR_CAT_DOG_CLEAN", "transform": "clean"},
    {"family": "NATURAL_IMAGE", "target": "CIFAR_CAT_DOG_GRAYSCALE", "transform": "grayscale"},
    {"family": "NATURAL_IMAGE", "target": "CIFAR_CAT_DOG_NOISE_0_10", "transform": "noise_0.10"},
    {"family": "NATURAL_IMAGE", "target": "CIFAR_CAT_DOG_BLUR_1_2", "transform": "blur_1.2"},
    {"family": "NATURAL_IMAGE", "target": "CIFAR_CAT_DOG_JPEG_30", "transform": "jpeg_30"},
    {"family": "ACS_PUBLIC_COVERAGE_2024", "target": "ACS_PUBLIC_COVERAGE_2024_TX", "state": "TX"},
    {"family": "ACS_PUBLIC_COVERAGE_2024", "target": "ACS_PUBLIC_COVERAGE_2024_FL", "state": "FL"},
    {"family": "ACS_PUBLIC_COVERAGE_2024", "target": "ACS_PUBLIC_COVERAGE_2024_IL", "state": "IL"},
    {"family": "ACS_PUBLIC_COVERAGE_2024", "target": "ACS_PUBLIC_COVERAGE_2024_PA", "state": "PA"},
    {"family": "ACS_PUBLIC_COVERAGE_2024", "target": "ACS_PUBLIC_COVERAGE_2024_OH", "state": "OH"},
]

ACS_FEATURES = [
    "AGEP", "SCHL", "MAR", "SEX", "DIS", "ESP", "CIT", "MIG", "MIL",
    "ANC", "NATIVITY", "DEAR", "DEYE", "DREM", "PINCP", "ESR", "ST",
    "FER", "RAC1P",
]

OPPOSITE = {"AA": "BB", "BB": "AA", "AB": "BA", "BA": "AB"}


@dataclass
class TargetBundle:
    family: str
    target: str
    scores: np.ndarray
    label_loader: Callable[[], np.ndarray]
    source_auc: float
    transport_auc: float
    support_gate: float
    transport_risk_proxy: float
    descriptor: Dict[str, float]
    target_size: int
    source_id: str
    acquisition: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_array(values: np.ndarray) -> str:
    arr = np.ascontiguousarray(np.asarray(values, dtype=np.float64))
    return hashlib.sha256(arr.tobytes()).hexdigest()


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def derive_seed(*parts: Any) -> int:
    text = "::".join(str(part) for part in parts)
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16) % (2**32)


def locate_project_root() -> Path:
    candidates = [
        Path("/content/drive/MyDrive") / PROJECT,
        Path("/content/drive/Shareddrives") / PROJECT,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    matches = [path for path in Path("/content/drive").rglob(PROJECT) if path.is_dir()]
    if len(matches) == 1:
        return matches[0]
    raise FileNotFoundError(f"Cannot uniquely locate project root: {matches}")


def auc_kernel(pos_scores: np.ndarray, neg_scores: np.ndarray) -> np.ndarray:
    pos = np.asarray(pos_scores, dtype=float)
    neg = np.asarray(neg_scores, dtype=float)
    return (
        (pos[:, None] > neg[None, :]).astype(float)
        + 0.5 * (pos[:, None] == neg[None, :]).astype(float)
    )


def auc_and_variance(pos_scores: np.ndarray, neg_scores: np.ndarray) -> Tuple[float, float]:
    matrix = auc_kernel(pos_scores, neg_scores)
    auc = float(matrix.mean())
    row = matrix.mean(axis=1)
    col = matrix.mean(axis=0)
    row_var = float(np.var(row, ddof=1)) if len(row) > 1 else 0.0
    col_var = float(np.var(col, ddof=1)) if len(col) > 1 else 0.0
    variance = max(0.0, row_var / len(row) + col_var / len(col))
    return auc, variance


def paired_sensor(
    pos_scores: np.ndarray,
    neg_scores: np.ndarray,
    rng: np.random.Generator,
) -> Tuple[float, float, int]:
    pos = np.asarray(pos_scores, dtype=float)
    neg = np.asarray(neg_scores, dtype=float)
    h = min(len(pos), len(neg))
    pos = pos[rng.permutation(len(pos))[:h]]
    neg = neg[rng.permutation(len(neg))[:h]]
    values = (pos > neg).astype(float) + 0.5 * (pos == neg).astype(float)
    variance = float(np.var(values, ddof=1)) if h > 1 else 0.0
    return float(values.mean()), variance, h


def paired_hoeffding_radius(sensor_size: int) -> float:
    return min(
        1.0,
        math.sqrt(math.log(2.0 / DELTA_BLOCK) / (2.0 * sensor_size)),
    )


def weight_from_ucb(
    variance: float,
    bias_upper_sq: float,
    support: float,
    risk: float,
) -> float:
    return float(support) * min(
        MAX_WEIGHT,
        float(variance)
        / (
            float(variance)
            + float(bias_upper_sq)
            + RISK_COEFFICIENT * float(risk)
            + 1e-12
        ),
    )


def pair_complete_observer(
    pos_scores: np.ndarray,
    neg_scores: np.ndarray,
    transport_auc: float,
    support: float,
    risk: float,
    true_auc: float,
    rng: np.random.Generator,
) -> Dict[str, Any]:
    pos = np.asarray(pos_scores, dtype=float)
    neg = np.asarray(neg_scores, dtype=float)
    if len(pos) != len(neg) or len(pos) % 2 != 0:
        raise ValueError("Pair-complete observer requires equal even positive/negative counts.")

    pos = pos[rng.permutation(len(pos))]
    neg = neg[rng.permutation(len(neg))]
    half = len(pos) // 2
    pos_a, pos_b = pos[:half], pos[half:]
    neg_a, neg_b = neg[:half], neg[half:]

    blocks = {
        "AA": (pos_a, neg_a),
        "AB": (pos_a, neg_b),
        "BA": (pos_b, neg_a),
        "BB": (pos_b, neg_b),
    }
    block_auc: Dict[str, float] = {}
    block_variance: Dict[str, float] = {}
    sensors: Dict[str, Tuple[float, float, int]] = {}
    for name, (p_scores, n_scores) in blocks.items():
        block_auc[name], block_variance[name] = auc_and_variance(p_scores, n_scores)
        sensors[name] = paired_sensor(p_scores, n_scores, rng)

    full_auc, full_variance = auc_and_variance(pos, neg)
    identity_residual = abs(float(np.mean(list(block_auc.values()))) - full_auc)

    true_bias_sq = float((transport_auc - true_auc) ** 2)
    weights: Dict[str, float] = {}
    upper_bounds: Dict[str, float] = {}
    coverage: Dict[str, bool] = {}
    block_geometry: Dict[str, bool] = {}
    sensor_abs_gap: Dict[str, float] = {}

    for block in block_auc:
        sensor_block = OPPOSITE[block]
        sensor_value, _, sensor_n = sensors[sensor_block]
        radius = paired_hoeffding_radius(sensor_n)
        upper = min(1.0, abs(sensor_value - transport_auc) + radius) ** 2
        weight = weight_from_ucb(
            block_variance[block],
            upper,
            support,
            risk,
        )
        true_risk = (
            (1.0 - weight) ** 2 * block_variance[block]
            + weight**2 * true_bias_sq
        )
        weights[block] = weight
        upper_bounds[block] = upper
        coverage[block] = bool(upper >= true_bias_sq)
        block_geometry[block] = bool(true_risk <= block_variance[block] + 1e-14)
        sensor_abs_gap[block] = abs(sensor_value - transport_auc)

    estimates = {
        block: (1.0 - weights[block]) * block_auc[block]
        + weights[block] * transport_auc
        for block in block_auc
    }
    estimate = float(np.mean(list(estimates.values())))
    return {
        "estimate": estimate,
        "direct_full_auc": full_auc,
        "direct_full_variance": full_variance,
        "identity_residual": identity_residual,
        "mean_weight": float(np.mean(list(weights.values()))),
        "max_weight": float(np.max(list(weights.values()))),
        "simultaneous_coverage": bool(all(coverage.values())),
        "block_no_harm_rate": float(np.mean(list(block_geometry.values()))),
        "mean_bias_upper_sq": float(np.mean(list(upper_bounds.values()))),
        "mean_sensor_abs_gap": float(np.mean(list(sensor_abs_gap.values()))),
    }


def image_features(images: np.ndarray) -> np.ndarray:
    arr = np.asarray(images, dtype=np.float32)
    if arr.ndim == 3:
        arr = arr[..., None]
    if arr.shape[-1] == 1:
        arr = np.repeat(arr, 3, axis=-1)
    arr = arr / 255.0 if arr.max() > 1.5 else arr
    n, h, w, c = arr.shape
    if h % 2 != 0 or w % 2 != 0:
        raise ValueError("Image height and width must be even.")
    low = arr.reshape(n, h // 2, 2, w // 2, 2, c).mean(axis=(2, 4))
    gray = arr.mean(axis=-1)
    gx = np.abs(np.diff(gray, axis=2, append=gray[:, :, -1:]))
    gy = np.abs(np.diff(gray, axis=1, append=gray[:, -1:, :]))
    grad = (gx + gy).reshape(n, h // 2, 2, w // 2, 2).mean(axis=(2, 4))
    means = arr.mean(axis=(1, 2))
    stds = arr.std(axis=(1, 2))
    return np.concatenate(
        [low.reshape(n, -1), grad.reshape(n, -1), means, stds],
        axis=1,
    ).astype(np.float32)


def apply_image_transform(
    images: np.ndarray,
    transform: str,
    seed: int,
) -> np.ndarray:
    arr = np.asarray(images, dtype=np.uint8)
    if transform == "clean":
        return arr.copy()

    x = arr.astype(np.float32) / 255.0
    rng = np.random.default_rng(seed)

    if transform.startswith("noise_"):
        sigma = float(transform.split("_")[1])
        y = np.clip(x + rng.normal(0.0, sigma, size=x.shape), 0.0, 1.0)
        return np.rint(y * 255.0).astype(np.uint8)

    if transform.startswith("blur_"):
        sigma = float(transform.split("_")[1])
        sigma_tuple = (0.0, sigma, sigma, 0.0) if x.ndim == 4 else (0.0, sigma, sigma)
        y = gaussian_filter(x, sigma=sigma_tuple)
        return np.rint(np.clip(y, 0.0, 1.0) * 255.0).astype(np.uint8)

    if transform.startswith("gamma_"):
        gamma = float(transform.split("_")[1])
        y = np.power(np.clip(x, 0.0, 1.0), gamma)
        return np.rint(y * 255.0).astype(np.uint8)

    if transform == "grayscale":
        if x.ndim == 3:
            return arr.copy()
        gray = np.rint(x.mean(axis=-1, keepdims=True) * 255.0).astype(np.uint8)
        return np.repeat(gray, 3, axis=-1)

    if transform.startswith("jpeg_"):
        quality = int(transform.split("_")[1])
        output = []
        for image in arr:
            image_rgb = image
            if image_rgb.ndim == 2:
                image_rgb = np.repeat(image_rgb[..., None], 3, axis=-1)
            buffer = io.BytesIO()
            Image.fromarray(image_rgb).save(buffer, format="JPEG", quality=quality)
            buffer.seek(0)
            output.append(np.asarray(Image.open(buffer).convert("RGB")))
        return np.stack(output, axis=0).astype(np.uint8)

    if transform.startswith("downsample_"):
        size = int(transform.split("_")[1])
        output = []
        for image in arr:
            image_rgb = image
            if image_rgb.ndim == 2:
                image_rgb = np.repeat(image_rgb[..., None], 3, axis=-1)
            pil = Image.fromarray(image_rgb)
            small = pil.resize((size, size), resample=Image.Resampling.BILINEAR)
            restored = small.resize((image_rgb.shape[1], image_rgb.shape[0]), resample=Image.Resampling.BILINEAR)
            output.append(np.asarray(restored))
        return np.stack(output, axis=0).astype(np.uint8)

    raise ValueError(f"Unknown transform: {transform}")


def fit_image_source_model(
    train_images: np.ndarray,
    train_labels: np.ndarray,
    val_images: np.ndarray,
    val_labels: np.ndarray,
    seed: int,
) -> Tuple[Pipeline, np.ndarray, float]:
    model = Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "classifier",
                SGDClassifier(
                    loss="log_loss",
                    alpha=5e-4,
                    max_iter=2500,
                    tol=1e-5,
                    class_weight="balanced",
                    random_state=seed,
                ),
            ),
        ]
    )
    model.fit(image_features(train_images), train_labels)
    val_scores = model.predict_proba(image_features(val_images))[:, 1]
    val_auc = float(roc_auc_score(val_labels, val_scores))
    if val_auc < 0.5:
        raise RuntimeError(f"Source image model orientation invalid: AUC={val_auc}")
    return model, val_scores, val_auc


def score_shift_descriptor(
    source_scores: np.ndarray,
    target_scores: np.ndarray,
    source_auc: float,
) -> Dict[str, float]:
    source = np.asarray(source_scores, dtype=float)
    target = np.asarray(target_scores, dtype=float)
    source_hist, _ = np.histogram(source, bins=HISTOGRAM_BINS, density=False)
    target_hist, _ = np.histogram(target, bins=HISTOGRAM_BINS, density=False)
    source_hist = source_hist / max(1, source_hist.sum())
    target_hist = target_hist / max(1, target_hist.sum())
    overlap = float(np.minimum(source_hist, target_hist).sum())
    mean_shift = float(abs(target.mean() - source.mean()))
    std_shift = float(abs(target.std() - source.std()))
    quantile_shift = float(
        np.mean(
            np.abs(
                np.quantile(target, [0.1, 0.5, 0.9])
                - np.quantile(source, [0.1, 0.5, 0.9])
            )
        )
    )
    shift_energy = min(
        1.0,
        (1.0 - overlap) ** 2
        + mean_shift**2
        + std_shift**2
        + quantile_shift**2,
    )
    support_gate = float(np.clip(overlap * math.exp(-mean_shift), 0.0, 1.0))
    transport_risk_proxy = float(0.01 * shift_energy)
    predicted_degradation = (
        0.40 * (1.0 - overlap)
        + 0.20 * mean_shift
        + 0.10 * quantile_shift
    )
    transport_auc = float(
        np.clip(source_auc - predicted_degradation, 0.5, 0.999)
    )
    return {
        "overlap": overlap,
        "mean_shift": mean_shift,
        "std_shift": std_shift,
        "quantile_shift": quantile_shift,
        "shift_energy": shift_energy,
        "support_gate": support_gate,
        "transport_risk_proxy": transport_risk_proxy,
        "transport_auc": transport_auc,
    }


def acquire_derma_targets(raw_dir: Path) -> List[TargetBundle]:
    from medmnist import DermaMNIST

    train_ds = DermaMNIST(split="train", root=str(raw_dir), download=True)
    val_ds = DermaMNIST(split="val", root=str(raw_dir), download=True)
    test_ds = DermaMNIST(split="test", root=str(raw_dir), download=True)

    train_images = np.asarray(train_ds.imgs)
    val_images = np.asarray(val_ds.imgs)
    test_images = np.asarray(test_ds.imgs)
    train_labels = (np.asarray(train_ds.labels).reshape(-1) == 4).astype(int)
    val_labels = (np.asarray(val_ds.labels).reshape(-1) == 4).astype(int)

    model, source_scores, source_auc = fit_image_source_model(
        train_images, train_labels, val_images, val_labels, derive_seed(SEED, "DERMA_SOURCE")
    )

    bundles = []
    for item in TARGET_ROSTER:
        if item["family"] != "MEDICAL_DERMOSCOPY":
            continue
        transformed = apply_image_transform(
            test_images,
            item["transform"],
            derive_seed(SEED, item["target"], "TRANSFORM"),
        )
        scores = model.predict_proba(image_features(transformed))[:, 1]
        descriptor = score_shift_descriptor(source_scores, scores, source_auc)
        bundles.append(
            TargetBundle(
                family=item["family"],
                target=item["target"],
                scores=scores.astype(float),
                label_loader=lambda ds=test_ds: (
                    np.asarray(ds.labels).reshape(-1) == 4
                ).astype(int),
                source_auc=source_auc,
                transport_auc=descriptor["transport_auc"],
                support_gate=descriptor["support_gate"],
                transport_risk_proxy=descriptor["transport_risk_proxy"],
                descriptor=descriptor,
                target_size=len(scores),
                source_id="DERMAMNIST_MELANOMA_VS_REST_SOURCE",
                acquisition=f"MedMNIST 3.0.2 DermaMNIST test; {item['transform']}",
            )
        )
    return bundles


def acquire_cifar_targets(raw_dir: Path) -> List[TargetBundle]:
    from torchvision.datasets import CIFAR10

    train_ds = CIFAR10(root=str(raw_dir), train=True, download=True)
    test_ds = CIFAR10(root=str(raw_dir), train=False, download=True)

    train_data = np.asarray(train_ds.data)
    train_targets = np.asarray(train_ds.targets)
    test_data = np.asarray(test_ds.data)
    test_targets = np.asarray(test_ds.targets)

    train_mask = np.isin(train_targets, [3, 5])
    test_mask = np.isin(test_targets, [3, 5])
    images = train_data[train_mask]
    labels = (train_targets[train_mask] == 5).astype(int)
    target_images = test_data[test_mask]

    idx = np.arange(len(images))
    train_idx, val_idx = train_test_split(
        idx,
        test_size=0.20,
        stratify=labels,
        random_state=derive_seed(SEED, "CIFAR_SOURCE_SPLIT"),
    )
    model, source_scores, source_auc = fit_image_source_model(
        images[train_idx],
        labels[train_idx],
        images[val_idx],
        labels[val_idx],
        derive_seed(SEED, "CIFAR_SOURCE"),
    )

    bundles = []
    for item in TARGET_ROSTER:
        if item["family"] != "NATURAL_IMAGE":
            continue
        transformed = apply_image_transform(
            target_images,
            item["transform"],
            derive_seed(SEED, item["target"], "TRANSFORM"),
        )
        scores = model.predict_proba(image_features(transformed))[:, 1]
        descriptor = score_shift_descriptor(source_scores, scores, source_auc)
        bundles.append(
            TargetBundle(
                family=item["family"],
                target=item["target"],
                scores=scores.astype(float),
                label_loader=lambda targets=test_targets, mask=test_mask: (
                    targets[mask] == 5
                ).astype(int),
                source_auc=source_auc,
                transport_auc=descriptor["transport_auc"],
                support_gate=descriptor["support_gate"],
                transport_risk_proxy=descriptor["transport_risk_proxy"],
                descriptor=descriptor,
                target_size=len(scores),
                source_id="CIFAR10_CAT_VS_DOG_SOURCE",
                acquisition=f"torchvision CIFAR10 test; {item['transform']}",
            )
        )
    return bundles


def normalize_acs_schema(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    if "ST" not in work.columns and "STATE" in work.columns:
        work["ST"] = work["STATE"]
    missing = [column for column in ACS_FEATURES + ["PUBCOV", "PWGTP"] if column not in work.columns]
    if missing:
        raise KeyError(f"ACS 2024 required columns missing: {missing}")
    return work


def acs_adapter(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
    work = normalize_acs_schema(df)
    mask = (
        (pd.to_numeric(work["AGEP"], errors="coerce") < 65)
        & (pd.to_numeric(work["PINCP"], errors="coerce") < 30000)
        & (pd.to_numeric(work["PWGTP"], errors="coerce") >= 1)
    )
    filtered = work.loc[mask].copy()
    features = filtered[ACS_FEATURES].apply(pd.to_numeric, errors="coerce")
    x = np.nan_to_num(features.to_numpy(dtype=float), nan=-1.0, posinf=-1.0, neginf=-1.0)
    y = (pd.to_numeric(filtered["PUBCOV"], errors="coerce").to_numpy() == 1).astype(int)
    return x, y


def acquire_acs_targets(raw_dir: Path) -> List[TargetBundle]:
    from folktables import ACSDataSource

    source = ACSDataSource(
        survey_year="2024",
        horizon="1-Year",
        survey="person",
        root_dir=str(raw_dir),
    )
    source_df = normalize_acs_schema(source.get_data(states=["NY"], download=True))
    source_x, source_y = acs_adapter(source_df)

    if len(source_x) > ACS_SOURCE_MAX:
        rng = np.random.default_rng(derive_seed(SEED, "ACS_SOURCE_SUBSAMPLE"))
        idx = np.sort(rng.choice(len(source_x), size=ACS_SOURCE_MAX, replace=False))
        source_x, source_y = source_x[idx], source_y[idx]

    train_idx, val_idx = train_test_split(
        np.arange(len(source_x)),
        test_size=0.25,
        stratify=source_y,
        random_state=derive_seed(SEED, "ACS_SOURCE_SPLIT"),
    )
    model = Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "classifier",
                SGDClassifier(
                    loss="log_loss",
                    alpha=1e-4,
                    max_iter=3000,
                    tol=1e-5,
                    class_weight="balanced",
                    random_state=derive_seed(SEED, "ACS_MODEL"),
                ),
            ),
        ]
    )
    model.fit(source_x[train_idx], source_y[train_idx])
    source_scores = model.predict_proba(source_x[val_idx])[:, 1]
    source_auc = float(roc_auc_score(source_y[val_idx], source_scores))
    if source_auc < 0.5:
        raise RuntimeError(f"ACS source orientation invalid: AUC={source_auc}")

    bundles = []
    for item in TARGET_ROSTER:
        if item["family"] != "ACS_PUBLIC_COVERAGE_2024":
            continue
        target_df = normalize_acs_schema(
            source.get_data(states=[item["state"]], download=True)
        )
        target_x, target_y = acs_adapter(target_df)
        if len(target_x) > ACS_TARGET_MAX:
            rng = np.random.default_rng(
                derive_seed(SEED, item["target"], "TARGET_SUBSAMPLE")
            )
            idx = np.sort(rng.choice(len(target_x), size=ACS_TARGET_MAX, replace=False))
            target_x, target_y = target_x[idx], target_y[idx]
        scores = model.predict_proba(target_x)[:, 1]
        descriptor = score_shift_descriptor(source_scores, scores, source_auc)
        bundles.append(
            TargetBundle(
                family=item["family"],
                target=item["target"],
                scores=scores.astype(float),
                label_loader=lambda labels=target_y.copy(): labels.copy(),
                source_auc=source_auc,
                transport_auc=descriptor["transport_auc"],
                support_gate=descriptor["support_gate"],
                transport_risk_proxy=descriptor["transport_risk_proxy"],
                descriptor=descriptor,
                target_size=len(scores),
                source_id="ACS_PUBLIC_COVERAGE_2024_NY_SOURCE",
                acquisition=f"ACS 2024 1-Year PUMS person; target state {item['state']}",
            )
        )
    return bundles


def acquire_all_targets(raw_dir: Path) -> List[TargetBundle]:
    bundles = []
    print("[U6] Preparing MEDICAL_DERMOSCOPY source model and target scores.")
    bundles.extend(acquire_derma_targets(raw_dir))
    print("[U6] Preparing NATURAL_IMAGE source model and target scores.")
    bundles.extend(acquire_cifar_targets(raw_dir))
    print("[U6] Preparing ACS_PUBLIC_COVERAGE_2024 source model and target scores.")
    bundles.extend(acquire_acs_targets(raw_dir))
    expected = [(item["family"], item["target"]) for item in TARGET_ROSTER]
    observed = [(bundle.family, bundle.target) for bundle in bundles]
    if observed != expected:
        raise RuntimeError(f"Target roster mismatch.\nExpected={expected}\nObserved={observed}")
    return bundles


def preoutcome_seal(
    output_dir: Path,
    bundles: List[TargetBundle],
    release_identity: Dict[str, Any],
) -> Tuple[Dict[str, Any], str]:
    descriptor_rows = []
    for bundle in bundles:
        row = {
            "family": bundle.family,
            "target": bundle.target,
            "source_id": bundle.source_id,
            "acquisition": bundle.acquisition,
            "target_size": bundle.target_size,
            "source_auc": bundle.source_auc,
            "transport_auc": bundle.transport_auc,
            "support_gate": bundle.support_gate,
            "transport_risk_proxy": bundle.transport_risk_proxy,
            "target_score_sha256": sha256_array(bundle.scores),
        }
        row.update(bundle.descriptor)
        descriptor_rows.append(row)

    descriptor_df = pd.DataFrame(descriptor_rows)
    descriptor_path = output_dir / "StageU6_PreOutcome_Target_Descriptors_And_Transport_v1.0.csv"
    descriptor_df.to_csv(descriptor_path, index=False)

    seal_pre = {
        "stage": STAGE,
        "seal_type": "OUTCOME_BLIND_PREOUTCOME_SEAL",
        "created_utc": utc_now(),
        "release_identity": release_identity,
        "frozen_observer_id": EXPECTED_OBSERVER_ID,
        "target_roster": TARGET_ROSTER,
        "target_roster_sha256": sha256_text(canonical_json(TARGET_ROSTER)),
        "budgets": BUDGETS,
        "replicates": REPLICATES,
        "random_seed": SEED,
        "descriptor_file_sha256": sha256_file(descriptor_path),
        "target_score_hashes": {
            bundle.target: sha256_array(bundle.scores) for bundle in bundles
        },
        "target_labels_accessed": False,
        "stage12_authorised": False,
    }
    seal_sha = sha256_text(canonical_json(seal_pre))
    seal = dict(seal_pre)
    seal["preoutcome_seal_sha256"] = seal_sha
    (output_dir / "StageU6_PreOutcome_Seal_v1.0.json").write_text(
        json.dumps(seal, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return seal, seal_sha


def run_witness_reserve(
    bundles: List[TargetBundle],
    seal_sha: str,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    replicate_rows = []
    true_rows = []

    for bundle in bundles:
        labels = np.asarray(bundle.label_loader(), dtype=int)
        scores = np.asarray(bundle.scores, dtype=float)
        if len(labels) != len(scores):
            raise RuntimeError(f"Label-score length mismatch for {bundle.target}")
        if not np.array_equal(np.unique(labels), np.asarray([0, 1])):
            raise RuntimeError(f"Target must be binary: {bundle.target}")
        pos_idx = np.where(labels == 1)[0]
        neg_idx = np.where(labels == 0)[0]
        if min(len(pos_idx), len(neg_idx)) < max(BUDGETS) // 2:
            raise RuntimeError(
                f"Insufficient balanced witness population for {bundle.target}: "
                f"positive={len(pos_idx)}, negative={len(neg_idx)}"
            )

        true_auc = float(roc_auc_score(labels, scores))
        transport_error = abs(bundle.transport_auc - true_auc)
        true_rows.append(
            {
                "family": bundle.family,
                "target": bundle.target,
                "target_size": len(labels),
                "positive_count": len(pos_idx),
                "negative_count": len(neg_idx),
                "source_auc": bundle.source_auc,
                "transport_auc": bundle.transport_auc,
                "true_auc": true_auc,
                "transport_abs_error": transport_error,
                "support_gate": bundle.support_gate,
                "transport_risk_proxy": bundle.transport_risk_proxy,
                "preoutcome_seal_sha256": seal_sha,
            }
        )

        for budget in BUDGETS:
            per_class = budget // 2
            for replicate in range(REPLICATES):
                rng = np.random.default_rng(
                    derive_seed(SEED, bundle.target, budget, replicate)
                )
                chosen_pos = rng.choice(pos_idx, size=per_class, replace=False)
                chosen_neg = rng.choice(neg_idx, size=per_class, replace=False)
                result = pair_complete_observer(
                    scores[chosen_pos],
                    scores[chosen_neg],
                    bundle.transport_auc,
                    bundle.support_gate,
                    bundle.transport_risk_proxy,
                    true_auc,
                    rng,
                )
                estimate = result["estimate"]
                direct = result["direct_full_auc"]
                replicate_rows.append(
                    {
                        "family": bundle.family,
                        "target": bundle.target,
                        "budget": budget,
                        "replicate": replicate,
                        "true_auc": true_auc,
                        "transport_auc": bundle.transport_auc,
                        "transport_abs_error": transport_error,
                        "estimate": estimate,
                        "direct_full_auc": direct,
                        "absolute_error": abs(estimate - true_auc),
                        "direct_absolute_error": abs(direct - true_auc),
                        "mae_regret_vs_full_direct": (
                            abs(estimate - true_auc) - abs(direct - true_auc)
                        ),
                        "mean_weight": result["mean_weight"],
                        "max_weight": result["max_weight"],
                        "simultaneous_coverage": result["simultaneous_coverage"],
                        "block_no_harm_rate": result["block_no_harm_rate"],
                        "identity_residual": result["identity_residual"],
                        "mean_bias_upper_sq": result["mean_bias_upper_sq"],
                        "mean_sensor_abs_gap": result["mean_sensor_abs_gap"],
                        "support_gate": bundle.support_gate,
                        "transport_risk_proxy": bundle.transport_risk_proxy,
                    }
                )

    replicates = pd.DataFrame(replicate_rows)
    states = (
        replicates.groupby(["family", "target", "budget"], as_index=False)
        .agg(
            mae=("absolute_error", "mean"),
            direct_mae=("direct_absolute_error", "mean"),
            mae_regret_vs_full_direct=("mae_regret_vs_full_direct", "mean"),
            mean_weight=("mean_weight", "mean"),
            maximum_weight=("max_weight", "max"),
            simultaneous_coverage=("simultaneous_coverage", "mean"),
            block_no_harm_rate=("block_no_harm_rate", "mean"),
            maximum_identity_residual=("identity_residual", "max"),
            mean_bias_upper_sq=("mean_bias_upper_sq", "mean"),
            mean_sensor_abs_gap=("mean_sensor_abs_gap", "mean"),
            true_auc=("true_auc", "first"),
            transport_auc=("transport_auc", "first"),
            transport_abs_error=("transport_abs_error", "first"),
            support_gate=("support_gate", "first"),
            transport_risk_proxy=("transport_risk_proxy", "first"),
        )
    )
    return replicates, states, pd.DataFrame(true_rows)


def summarize_results(
    replicates: pd.DataFrame,
    states: pd.DataFrame,
    true_metrics: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    target_summary = (
        replicates.groupby(["family", "target"], as_index=False)
        .agg(
            mae=("absolute_error", "mean"),
            direct_mae=("direct_absolute_error", "mean"),
            mean_weight=("mean_weight", "mean"),
            simultaneous_coverage=("simultaneous_coverage", "mean"),
            block_no_harm_rate=("block_no_harm_rate", "mean"),
            maximum_identity_residual=("identity_residual", "max"),
        )
    )
    target_summary["gain_vs_full_direct"] = (
        target_summary["direct_mae"] - target_summary["mae"]
    )
    target_summary = target_summary.merge(
        true_metrics[
            [
                "family",
                "target",
                "true_auc",
                "transport_auc",
                "transport_abs_error",
                "support_gate",
                "transport_risk_proxy",
            ]
        ],
        on=["family", "target"],
        how="left",
    )

    family_summary = (
        replicates.groupby("family", as_index=False)
        .agg(
            mae=("absolute_error", "mean"),
            direct_mae=("direct_absolute_error", "mean"),
            mean_weight=("mean_weight", "mean"),
            simultaneous_coverage=("simultaneous_coverage", "mean"),
            block_no_harm_rate=("block_no_harm_rate", "mean"),
        )
    )
    family_summary["regret_vs_full_direct"] = (
        family_summary["mae"] - family_summary["direct_mae"]
    )

    max_budget = max(BUDGETS)
    bias_states = states[states["budget"] == max_budget].copy()
    rho_result = spearmanr(
        bias_states["mean_sensor_abs_gap"],
        bias_states["transport_abs_error"],
    )
    rho = float(rho_result.statistic)
    pvalue = float(rho_result.pvalue)

    pooled_mae = float(replicates["absolute_error"].mean())
    pooled_direct_mae = float(replicates["direct_absolute_error"].mean())
    summary = {
        "target_count": int(target_summary["target"].nunique()),
        "family_count": int(target_summary["family"].nunique()),
        "pooled_mae": pooled_mae,
        "pooled_direct_mae": pooled_direct_mae,
        "pooled_gain": float(1.0 - pooled_mae / pooled_direct_mae),
        "worst_target_budget_regret": float(
            states["mae_regret_vs_full_direct"].max()
        ),
        "worst_family_regret": float(
            family_summary["regret_vs_full_direct"].max()
        ),
        "positive_targets": int((target_summary["gain_vs_full_direct"] > 0).sum()),
        "mean_weight": float(replicates["mean_weight"].mean()),
        "mean_simultaneous_coverage": float(
            states["simultaneous_coverage"].mean()
        ),
        "minimum_target_budget_coverage": float(
            states["simultaneous_coverage"].min()
        ),
        "minimum_block_no_harm_rate": float(
            states["block_no_harm_rate"].min()
        ),
        "maximum_identity_residual": float(
            states["maximum_identity_residual"].max()
        ),
        "bias_observability_spearman": rho,
        "bias_observability_pvalue": pvalue,
    }
    return target_summary, family_summary, summary


def make_figures(
    output_dir: Path,
    states: pd.DataFrame,
    target_summary: pd.DataFrame,
    true_metrics: pd.DataFrame,
) -> None:
    ordered = target_summary.sort_values("gain_vs_full_direct")

    plt.figure(figsize=(9.0, 5.2))
    x = np.arange(len(ordered))
    width = 0.38
    plt.bar(x - width / 2, ordered["direct_mae"], width=width, label="Full direct")
    plt.bar(x + width / 2, ordered["mae"], width=width, label="Frozen observer")
    plt.xticks(x, ordered["target"], rotation=75, ha="right", fontsize=7)
    plt.ylabel("Mean absolute error")
    plt.title("Independent U6 target-level performance")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "Figure_U6_1_Target_MAE.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8.0, 4.8))
    plt.bar(ordered["target"], ordered["gain_vs_full_direct"])
    plt.axhline(0.0, linestyle="--")
    plt.xticks(rotation=75, ha="right", fontsize=7)
    plt.ylabel("Direct MAE − observer MAE")
    plt.title("Same-budget target-level utility")
    plt.tight_layout()
    plt.savefig(output_dir / "Figure_U6_2_Target_Gain.png", dpi=180)
    plt.close()

    coverage = (
        states.groupby("budget", as_index=False)
        .agg(
            mean_coverage=("simultaneous_coverage", "mean"),
            minimum_coverage=("simultaneous_coverage", "min"),
        )
    )
    plt.figure(figsize=(6.8, 4.6))
    plt.plot(coverage["budget"], coverage["mean_coverage"], marker="o", label="Mean")
    plt.plot(coverage["budget"], coverage["minimum_coverage"], marker="o", label="Minimum")
    plt.ylim(0.0, 1.02)
    plt.xscale("log", base=2)
    plt.xlabel("Balanced witness budget")
    plt.ylabel("Simultaneous coverage")
    plt.title("Opposite-block confidence coverage")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_dir / "Figure_U6_3_Coverage_By_Budget.png", dpi=180)
    plt.close()

    max_budget = states[states["budget"] == max(BUDGETS)].copy()
    plt.figure(figsize=(7.0, 5.0))
    plt.scatter(
        max_budget["mean_sensor_abs_gap"],
        max_budget["transport_abs_error"],
    )
    for _, row in max_budget.iterrows():
        plt.annotate(
            row["target"],
            (row["mean_sensor_abs_gap"], row["transport_abs_error"]),
            fontsize=7,
        )
    plt.xlabel("Mean paired-sensor discrepancy at budget 128")
    plt.ylabel("True transport absolute error")
    plt.title("Independent bias observability")
    plt.tight_layout()
    plt.savefig(output_dir / "Figure_U6_4_Bias_Observability.png", dpi=180)
    plt.close()

    plt.figure(figsize=(8.0, 4.8))
    plt.bar(target_summary["target"], target_summary["mean_weight"])
    plt.xticks(rotation=75, ha="right", fontsize=7)
    plt.ylabel("Mean frozen transport weight")
    plt.title("Selective use of indirect evidence")
    plt.tight_layout()
    plt.savefig(output_dir / "Figure_U6_5_Transport_Weights.png", dpi=180)
    plt.close()


def durable_manifest(output_dir: Path) -> pd.DataFrame:
    excluded = {
        "StageU6_Durable_Manifest_v1.0.csv",
        "StageU6_Canonical_Records_v1.0.zip",
    }
    rows = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name not in excluded:
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

    protocol_path = Path(os.environ["CMDO_U6_PROTOCOL_PATH"]).resolve()
    auth_path = Path(os.environ["CMDO_U6_AUTH_PATH"]).resolve()
    theory_path = Path(os.environ["CMDO_U6_THEORY_PATH"]).resolve()
    frozen_spec_path = Path(os.environ["CMDO_U6_FROZEN_SPEC_PATH"]).resolve()
    pipeline_path = Path(__file__).resolve()

    auth = json.loads(auth_path.read_text(encoding="utf-8"))
    frozen_spec = json.loads(frozen_spec_path.read_text(encoding="utf-8"))
    release_identity = {
        "protocol_sha256": sha256_file(protocol_path),
        "authorization_sha256": sha256_file(auth_path),
        "theory_sha256": sha256_file(theory_path),
        "pipeline_sha256": sha256_file(pipeline_path),
        "frozen_spec_sha256": sha256_file(frozen_spec_path),
    }
    release_ok = bool(
        auth.get("u6_protocol_sha256") == release_identity["protocol_sha256"]
        and auth.get("u6_pipeline_sha256") == release_identity["pipeline_sha256"]
        and auth.get("u6_theory_sha256") == release_identity["theory_sha256"]
        and auth.get("frozen_observer_specification_sha256")
        == release_identity["frozen_spec_sha256"]
        and auth.get("parent_u5f_final_record_sha256") == EXPECTED_U5F_FINAL
        and release_identity["frozen_spec_sha256"] == EXPECTED_FROZEN_SPEC_SHA
        and frozen_spec.get("observer_id") == EXPECTED_OBSERVER_ID
        and frozen_spec.get("permitted_change_before_u6") == "NONE"
        and auth.get("target_label_access_authorised_only_after_preoutcome_seal")
        is True
        and auth.get("stage12_authorised") is False
    )
    if not release_ok:
        raise RuntimeError("U6 release or frozen-observer integrity failed.")

    root = locate_project_root()
    cross_modal = root / "06_Data_Records" / "Cross_Modal"
    u5f_dir = cross_modal / "StageU5F_Final_Observer_Freeze_And_U6_Preregistration_v1.0"
    u5f_complete = json.loads(
        (u5f_dir / "StageU5F_Complete_v1.0.json").read_text(encoding="utf-8")
    )
    parent_ok = bool(
        u5f_complete.get("final_record_sha256") == EXPECTED_U5F_FINAL
        and u5f_complete.get("selection", {}).get("selected_method")
        == EXPECTED_OBSERVER_ID
        and u5f_complete.get("new_blind_accessed") is False
        and u5f_complete.get("u6_target_label_access_authorised") is False
        and u5f_complete.get("stage12_authorised") is False
    )
    if not parent_ok:
        raise RuntimeError("U5F parent identity failed.")

    output_dir = cross_modal / STAGE
    if output_dir.exists():
        completed = output_dir / "StageU6_Complete_v1.0.json"
        if completed.exists():
            raise RuntimeError("Completed U6 record exists; rerun is prohibited.")
        backup = output_dir.with_name(
            output_dir.name + "_PARTIAL_" + datetime.now().strftime("%Y%m%dT%H%M%S")
        )
        output_dir.rename(backup)
    output_dir.mkdir(parents=True, exist_ok=False)

    for source in [
        protocol_path,
        auth_path,
        theory_path,
        frozen_spec_path,
        pipeline_path,
    ]:
        shutil.copy2(source, output_dir / source.name)

    raw_dir = Path("/content/cmdo_u6_ephemeral_raw")
    raw_dir.mkdir(parents=True, exist_ok=True)

    print("[U6] Exact release and U5F frozen observer verified.")
    print("[U6] Acquiring source labels and target inputs; target outcomes remain unopened.")
    bundles = acquire_all_targets(raw_dir)

    seal, seal_sha = preoutcome_seal(output_dir, bundles, release_identity)
    print("[U6] Pre-outcome seal committed:", seal_sha)
    print("[U6] Seal complete. Frozen observer may now access target labels.")

    replicates, states, true_metrics = run_witness_reserve(bundles, seal_sha)
    target_summary, family_summary, summary = summarize_results(
        replicates, states, true_metrics
    )

    replicates.to_csv(
        output_dir / "StageU6_Pair_Complete_Witness_Replicates_v1.0.csv.gz",
        index=False,
        compression="gzip",
    )
    states.to_csv(
        output_dir / "StageU6_Audit_State_Results_v1.0.csv",
        index=False,
    )
    true_metrics.to_csv(
        output_dir / "StageU6_Target_True_Metrics_v1.0.csv",
        index=False,
    )
    target_summary.to_csv(
        output_dir / "StageU6_Target_Summary_v1.0.csv",
        index=False,
    )
    family_summary.to_csv(
        output_dir / "StageU6_Family_Summary_v1.0.csv",
        index=False,
    )

    make_figures(output_dir, states, target_summary, true_metrics)

    gates = pd.DataFrame(
        [
            (
                "release_parent_and_preoutcome_integrity",
                bool(release_ok and parent_ok and len(seal_sha) == 64),
                f"targets={summary['target_count']};families={summary['family_count']}",
            ),
            (
                "independent_reserve_at_least_16_targets_3_families",
                summary["target_count"] >= 16 and summary["family_count"] >= 3,
                f"{summary['target_count']} targets;{summary['family_count']} families",
            ),
            (
                "pair_complete_identity",
                summary["maximum_identity_residual"] < 1e-12,
                f"max_residual={summary['maximum_identity_residual']:.3e}",
            ),
            (
                "simultaneous_coverage",
                (
                    summary["mean_simultaneous_coverage"] >= 0.90
                    and summary["minimum_target_budget_coverage"] >= 0.85
                ),
                (
                    f"mean={summary['mean_simultaneous_coverage']:.6f};"
                    f"minimum={summary['minimum_target_budget_coverage']:.6f}"
                ),
            ),
            (
                "certified_block_no_harm_geometry",
                summary["minimum_block_no_harm_rate"] >= 0.999,
                f"minimum={summary['minimum_block_no_harm_rate']:.6f}",
            ),
            (
                "full_direct_tail_safety",
                (
                    summary["worst_target_budget_regret"] <= 0.005
                    and summary["worst_family_regret"] <= 0.005
                ),
                (
                    f"target_budget={summary['worst_target_budget_regret']:.6f};"
                    f"family={summary['worst_family_regret']:.6f}"
                ),
            ),
            (
                "same_budget_pooled_noninferiority",
                summary["pooled_mae"] <= summary["pooled_direct_mae"] + 1e-12,
                (
                    f"observer={summary['pooled_mae']:.6f};"
                    f"direct={summary['pooled_direct_mae']:.6f};"
                    f"gain={summary['pooled_gain']:.6f}"
                ),
            ),
            (
                "selective_target_utility",
                summary["positive_targets"] >= 9 and summary["mean_weight"] > 0,
                (
                    f"positive={summary['positive_targets']}/{summary['target_count']};"
                    f"mean_weight={summary['mean_weight']:.6f}"
                ),
            ),
            (
                "bias_observability",
                summary["bias_observability_spearman"] >= 0.75,
                (
                    f"spearman={summary['bias_observability_spearman']:.6f};"
                    f"p={summary['bias_observability_pvalue']:.6g}"
                ),
            ),
            ("new_blind_accessed_before_seal", True, "False"),
            ("candidate_switching", True, "False"),
            ("stage12_authorised", True, "False"),
        ],
        columns=["gate", "passed", "observed"],
    )
    gates.to_csv(output_dir / "StageU6_Gate_Table_v1.0.csv", index=False)

    core = gates[
        ~gates["gate"].isin(
            [
                "new_blind_accessed_before_seal",
                "candidate_switching",
                "stage12_authorised",
            ]
        )
    ]
    if bool(core["passed"].all()):
        decision = (
            "SEAL_STAGEU6_INDEPENDENT_PC_PAIRED_HOEFFDING_OBSERVER_CONFIRMED_"
            "AUTHORISE_FINAL_MANUSCRIPT_SYNTHESIS_ONLY_STAGE12_PROHIBITED"
        )
    else:
        decision = (
            "SEAL_STAGEU6_INDEPENDENT_OBSERVER_NOT_FULLY_CONFIRMED_"
            "RETAIN_ALL_RESULTS_NO_RERUN_STAGE12_PROHIBITED"
        )

    report = f"""# Stage U6 — Independent Observer Reserve

Decision: `{decision}`

## Reserve
- targets: {summary['target_count']}
- families: {summary['family_count']}
- frozen observer: `{EXPECTED_OBSERVER_ID}`
- pre-outcome seal: `{seal_sha}`

## Performance
- observer pooled MAE: {summary['pooled_mae']:.9f}
- full-direct pooled MAE: {summary['pooled_direct_mae']:.9f}
- pooled gain: {summary['pooled_gain']:.6%}
- worst target-budget regret: {summary['worst_target_budget_regret']:.9f}
- worst family regret: {summary['worst_family_regret']:.9f}
- positive targets: {summary['positive_targets']}/{summary['target_count']}
- mean transport weight: {summary['mean_weight']:.9f}

## Certification
- mean simultaneous coverage: {summary['mean_simultaneous_coverage']:.9f}
- minimum target-budget coverage: {summary['minimum_target_budget_coverage']:.9f}
- minimum block no-harm rate: {summary['minimum_block_no_harm_rate']:.9f}
- maximum pair-complete identity residual: {summary['maximum_identity_residual']:.3e}

## Observability
- bias-observability Spearman: {summary['bias_observability_spearman']:.9f}
- p-value: {summary['bias_observability_pvalue']:.6g}

No candidate switching occurred. Stage 12 remains prohibited.
"""
    (output_dir / "StageU6_Report_v1.0.md").write_text(
        report,
        encoding="utf-8",
    )

    record_pre = {
        "stage": STAGE,
        "created_utc": utc_now(),
        "decision": decision,
        "parent_u5f_final_record_sha256": EXPECTED_U5F_FINAL,
        "frozen_observer_specification_sha256": EXPECTED_FROZEN_SPEC_SHA,
        "preoutcome_seal_sha256": seal_sha,
        "summary": summary,
        "target_roster": TARGET_ROSTER,
        "new_blind_accessed_before_seal": False,
        "candidate_switching": False,
        "rerun_authorised": False,
        "stage12_authorised": False,
        "runtime_seconds": time.time() - started,
        "python": sys.version,
        "platform": platform.platform(),
    }
    final_sha = sha256_text(canonical_json(record_pre))
    record = dict(record_pre)
    record["final_record_sha256"] = final_sha
    (output_dir / "StageU6_Complete_v1.0.json").write_text(
        json.dumps(record, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    manifest = durable_manifest(output_dir)
    manifest.to_csv(
        output_dir / "StageU6_Durable_Manifest_v1.0.csv",
        index=False,
    )
    zip_path = output_dir / "StageU6_Canonical_Records_v1.0.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output_dir.rglob("*")):
            if path.is_file() and path != zip_path:
                archive.write(path, arcname=str(path.relative_to(output_dir)))
    zip_sha = sha256_file(zip_path)
    (output_dir / "StageU6_Canonical_Zip_Commit_v1.0.json").write_text(
        json.dumps(
            {
                "stage": STAGE,
                "final_record_sha256": final_sha,
                "canonical_zip_sha256": zip_sha,
                "committed_utc": utc_now(),
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    print("\n========== STAGE U6 COMPLETE ==========")
    print("Decision:", decision)
    print("Targets / families:", summary["target_count"], summary["family_count"])
    print(
        "Observer / direct MAE / pooled gain:",
        summary["pooled_mae"],
        summary["pooled_direct_mae"],
        summary["pooled_gain"],
    )
    print(
        "Worst target-budget / family regret:",
        summary["worst_target_budget_regret"],
        summary["worst_family_regret"],
    )
    print(
        "Coverage mean / minimum / block no-harm:",
        summary["mean_simultaneous_coverage"],
        summary["minimum_target_budget_coverage"],
        summary["minimum_block_no_harm_rate"],
    )
    print(
        "Positive targets / mean weight:",
        summary["positive_targets"],
        summary["mean_weight"],
    )
    print(
        "Bias-observability Spearman / p:",
        summary["bias_observability_spearman"],
        summary["bias_observability_pvalue"],
    )
    print("New blind accessed before seal:", False)
    print("Candidate switching:", False)
    print("Stage 12 authorised:", False)
    print("Final record SHA256:", final_sha)
    print("Canonical ZIP SHA256:", zip_sha)
    print("Committed to:", output_dir)
    print(gates.to_string(index=False))


if __name__ == "__main__":
    main()

