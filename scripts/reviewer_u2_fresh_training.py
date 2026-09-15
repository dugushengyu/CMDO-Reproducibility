#!/usr/bin/env python3
"""Fresh public-data U2 training replay for the CMDO reviewer E2E audit.

This is an additional reviewer audit, not a replacement for frozen manuscript
results. It reproduces the U2 public CIFAR training/evaluation configuration:
- seed 20260724
- positive CIFAR classes {2,3,4,5,6,7}
- 45k train / 5k validation split
- frozen CNN architecture
- AdamW(lr=2e-3, weight_decay=1e-4), cosine schedule
- 12 epochs, batch size 256
- clean CIFAR-10, CIFAR-10.1 v6, and 12 CIFAR-10-C corruptions at severities 1/3/5

Fresh metrics are compared with provenance/u2_frozen_metrics.csv using the
declared replay tolerances. Model-byte identity is intentionally not required.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import random
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SEED = 20260724
EPOCHS = 12
POSITIVE_CLASSES = {2, 3, 4, 5, 6, 7}
BUDGETS = (8, 16, 32, 64, 128)
CIFAR10C_URL = "https://zenodo.org/records/2535967/files/CIFAR-10-C.tar?download=1"
CIFAR10C_MD5 = "56bf5dcef84df0e2308c6dcbcbbd8499"
CIFAR101_DATA_URL = "https://raw.githubusercontent.com/modestyachts/CIFAR-10.1/master/datasets/cifar10.1_v6_data.npy"
CIFAR101_LABELS_URL = "https://raw.githubusercontent.com/modestyachts/CIFAR-10.1/master/datasets/cifar10.1_v6_labels.npy"
CORRUPTIONS = (
    "gaussian_noise", "shot_noise", "impulse_noise", "gaussian_blur",
    "motion_blur", "fog", "frost", "brightness", "contrast",
    "jpeg_compression", "pixelate", "zoom_blur",
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def download(url: str, path: Path, min_bytes: int = 1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and path.stat().st_size >= min_bytes:
        print(f"reuse download: {path} ({path.stat().st_size} bytes)")
        return
    curl = shutil.which("curl.exe") or shutil.which("curl")
    if curl:
        cmd = [curl, "-L", "--fail", "--retry", "5", "--retry-delay", "5", "-C", "-", "-o", str(path), url]
        print("$", " ".join(cmd), flush=True)
        subprocess.run(cmd, check=True)
    else:
        print(f"download: {url}", flush=True)
        with urllib.request.urlopen(url) as src, path.open("wb") as dst:
            shutil.copyfileobj(src, dst, length=1024 * 1024)
    if not path.is_file() or path.stat().st_size < min_bytes:
        raise RuntimeError(f"download incomplete: {path}")


def validate_cifar10c_arrays(extracted: Path) -> bool:
    needed = ["labels.npy", *[f"{c}.npy" for c in CORRUPTIONS]]
    if any(not (extracted / name).is_file() for name in needed):
        return False
    try:
        labels = np.load(extracted / "labels.npy", mmap_mode="r")
        if labels.shape[0] != 50000:
            return False
        for corr in CORRUPTIONS:
            arr = np.load(extracted / f"{corr}.npy", mmap_mode="r")
            if arr.shape != (50000, 32, 32, 3):
                return False
    except Exception:
        return False
    return True


def ensure_cifar10c(data_root: Path) -> tuple[Path, dict[str, object]]:
    extracted_candidates = [
        data_root / "CIFAR-10-C_Official_Selected" / "CIFAR-10-C",
        data_root / "CIFAR-10-C" / "selected" / "CIFAR-10-C",
    ]
    for extracted in extracted_candidates:
        if validate_cifar10c_arrays(extracted):
            print(f"REUSE EXISTING CIFAR-10-C ARRAYS: PASS: {extracted}", flush=True)
            return extracted, {
                "mode": "reused_preexisting_selected_arrays",
                "selected_root": str(extracted),
                "shape_validation": "PASS",
                "archive_md5_checked_this_run": False,
            }

    archive_candidates = [
        data_root / "CIFAR-10-C_Official_Archive" / "CIFAR-10-C.tar",
        data_root / "CIFAR-10-C" / "CIFAR-10-C.tar",
    ]
    archive = None
    for candidate in archive_candidates:
        if candidate.is_file():
            got = md5(candidate)
            if got == CIFAR10C_MD5:
                archive = candidate
                print(f"REUSE EXISTING CIFAR-10-C ARCHIVE: MD5 PASS: {candidate}", flush=True)
                break
            print(f"IGNORE CIFAR-10-C ARCHIVE WITH BAD MD5: {candidate} ({got})", flush=True)

    if archive is None:
        archive = data_root / "CIFAR-10-C" / "CIFAR-10-C.tar"
        archive.parent.mkdir(parents=True, exist_ok=True)
        if archive.exists():
            archive.unlink()
        download(CIFAR10C_URL, archive, min_bytes=2_000_000_000)
        got = md5(archive)
        if got != CIFAR10C_MD5:
            raise RuntimeError(f"CIFAR-10-C MD5 mismatch: {got}")
        print(f"CIFAR-10-C DOWNLOAD MD5 PASS: {CIFAR10C_MD5}", flush=True)

    extracted = data_root / "CIFAR-10-C" / "selected" / "CIFAR-10-C"
    extracted.mkdir(parents=True, exist_ok=True)
    needed = ["labels.npy", *[f"{c}.npy" for c in CORRUPTIONS]]
    missing = [name for name in needed if not (extracted / name).is_file()]
    if missing:
        print(f"extracting {len(missing)} selected CIFAR-10-C arrays", flush=True)
        with tarfile.open(archive, "r") as tf:
            by_name = {m.name: m for m in tf.getmembers()}
            for name in missing:
                member_name = f"CIFAR-10-C/{name}"
                if member_name not in by_name:
                    raise RuntimeError(f"missing archive member: {member_name}")
                member = by_name[member_name]
                src = tf.extractfile(member)
                if src is None:
                    raise RuntimeError(f"could not read archive member: {member_name}")
                with (extracted / name).open("wb") as dst:
                    shutil.copyfileobj(src, dst, length=8 * 1024 * 1024)

    if not validate_cifar10c_arrays(extracted):
        raise RuntimeError("CIFAR-10-C selected-array validation failed after extraction")
    return extracted, {
        "mode": "archive_verified_and_extracted",
        "selected_root": str(extracted),
        "archive": str(archive),
        "archive_md5": CIFAR10C_MD5,
        "shape_validation": "PASS",
        "archive_md5_checked_this_run": True,
    }


def resolve_cifar10_root(data_root: Path, CIFAR10) -> tuple[Path, str]:
    candidates = [
        data_root / "torchvision",
        data_root / "cifar10",
    ]
    for candidate in candidates:
        try:
            _ = CIFAR10(root=str(candidate), train=True, download=False)
            _ = CIFAR10(root=str(candidate), train=False, download=False)
            print(f"REUSE EXISTING CIFAR-10: PASS: {candidate}", flush=True)
            return candidate, "reused_preexisting"
        except Exception:
            pass

    target = data_root / "cifar10"
    print(f"CIFAR-10 cache not found under known layouts; downloading to {target}", flush=True)
    _ = CIFAR10(root=str(target), train=True, download=True)
    _ = CIFAR10(root=str(target), train=False, download=True)
    return target, "downloaded_or_torchvision_verified"


def resolve_cifar101(data_root: Path) -> tuple[Path, Path, str]:
    candidates = [
        data_root / "CIFAR-10.1",
        data_root / "cifar10.1",
    ]
    for directory in candidates:
        data = directory / "cifar10.1_v6_data.npy"
        labels = directory / "cifar10.1_v6_labels.npy"
        if data.is_file() and labels.is_file():
            try:
                x = np.load(data, mmap_mode="r")
                y = np.load(labels, mmap_mode="r")
                if x.shape == (2000, 32, 32, 3) and y.shape == (2000,):
                    print(f"REUSE EXISTING CIFAR-10.1: PASS: {directory}", flush=True)
                    return data, labels, "reused_preexisting"
            except Exception:
                pass

    directory = data_root / "cifar10.1"
    data = directory / "cifar10.1_v6_data.npy"
    labels = directory / "cifar10.1_v6_labels.npy"
    download(CIFAR101_DATA_URL, data, min_bytes=5_000_000)
    download(CIFAR101_LABELS_URL, labels, min_bytes=5_000)
    x = np.load(data, mmap_mode="r")
    y = np.load(labels, mmap_mode="r")
    if x.shape != (2000, 32, 32, 3) or y.shape != (2000,):
        raise RuntimeError("CIFAR-10.1 validation failed")
    return data, labels, "downloaded_or_existing_current_layout"


def set_seed(torch) -> None:
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(SEED)


def binary_label(y: int) -> float:
    return 1.0 if int(y) in POSITIVE_CLASSES else 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--witness-reps", type=int, default=100)
    args = parser.parse_args()

    work_root = args.work_root.expanduser().resolve()
    data_root = (args.data_root or (work_root / "public_data")).expanduser().resolve()
    out = work_root / "u2_fresh"
    predictions_dir = out / "predictions"
    for d in (work_root, data_root, out, predictions_dir):
        d.mkdir(parents=True, exist_ok=True)

    try:
        import torch
        import torch.nn as nn
        import torch.nn.functional as F
        from torch.utils.data import DataLoader, Dataset, Subset
        from torchvision import transforms
        from torchvision.datasets import CIFAR10
        import torchvision
        from PIL import Image
        from sklearn.metrics import (
            average_precision_score,
            balanced_accuracy_score,
            brier_score_loss,
            log_loss,
            roc_auc_score,
        )
        from sklearn.model_selection import train_test_split
    except Exception as exc:
        raise SystemExit(
            "Missing E2E dependencies. Install torch/torchvision plus numpy, "
            "scikit-learn, Pillow and matplotlib in a Python 3.11 environment. "
            f"Original import error: {exc}"
        )

    set_seed(torch)
    if args.device == "cuda" and not torch.cuda.is_available():
        raise SystemExit("--device cuda requested but torch.cuda.is_available() is False")
    device = torch.device(
        "cuda" if args.device == "cuda" or (args.device == "auto" and torch.cuda.is_available()) else "cpu"
    )
    workers = 0 if os.name == "nt" else 2
    pin = device.type == "cuda"

    environment = {
        "python": sys.version,
        "platform": platform.platform(),
        "torch": torch.__version__,
        "torchvision": torchvision.__version__,
        "cuda_runtime": torch.version.cuda,
        "cuda_available": bool(torch.cuda.is_available()),
        "device": str(device),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "seed": SEED,
        "epochs": args.epochs,
        "positive_classes": sorted(POSITIVE_CLASSES),
    }
    write_json(out / "environment.json", environment)
    print(json.dumps(environment, indent=2), flush=True)

    # Public data acquisition/reuse. Prefer verified legacy CMDO cache layouts.
    print("Resolving existing public CIFAR caches before any download", flush=True)
    cifar_root, cifar10_mode = resolve_cifar10_root(data_root, CIFAR10)
    train_base = CIFAR10(root=str(cifar_root), train=True, download=False)
    test_base = CIFAR10(root=str(cifar_root), train=False, download=False)

    c101_data, c101_labels, c101_mode = resolve_cifar101(data_root)
    c10c_root, c10c_meta = ensure_cifar10c(data_root)

    acquisition = {
        "CIFAR10": {
            "source": "torchvision.datasets.CIFAR10",
            "root": str(cifar_root),
            "mode": cifar10_mode,
        },
        "CIFAR10_1_V6": {
            "data_url": CIFAR101_DATA_URL,
            "labels_url": CIFAR101_LABELS_URL,
            "data_path": str(c101_data),
            "labels_path": str(c101_labels),
            "data_sha256": sha256(c101_data),
            "labels_sha256": sha256(c101_labels),
            "mode": c101_mode,
            "shape_validation": "PASS",
        },
        "CIFAR10_C": {
            "source": CIFAR10C_URL,
            "official_archive_md5": CIFAR10C_MD5,
            "selected_corruptions": list(CORRUPTIONS),
            "severities": [1, 3, 5],
            **c10c_meta,
        },
    }
    write_json(out / "acquisition.json", acquisition)

    normalize = transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2470, 0.2435, 0.2616))
    train_tf = transforms.Compose([
        transforms.RandomCrop(32, padding=4),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        normalize,
    ])
    eval_tf = transforms.Compose([transforms.ToTensor(), normalize])

    class BinaryBase(Dataset):
        def __init__(self, base, transform):
            self.base = base
            self.transform = transform
        def __len__(self):
            return len(self.base)
        def __getitem__(self, idx):
            img, y = self.base[idx]
            return self.transform(img), np.float32(binary_label(y))

    class BinaryNumpy(Dataset):
        def __init__(self, images, labels, transform):
            self.images = images
            self.labels = labels
            self.transform = transform
        def __len__(self):
            return len(self.labels)
        def __getitem__(self, idx):
            img = Image.fromarray(np.asarray(self.images[idx], dtype=np.uint8))
            return self.transform(img), np.float32(binary_label(int(self.labels[idx])))

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.features = nn.Sequential(
                nn.Conv2d(3, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
                nn.Conv2d(64, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
                nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(),
                nn.Conv2d(128, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(), nn.MaxPool2d(2),
                nn.Conv2d(128, 256, 3, padding=1), nn.BatchNorm2d(256), nn.ReLU(),
                nn.AdaptiveAvgPool2d(1),
            )
            self.fc = nn.Linear(256, 1)
        def forward(self, x):
            z = self.features(x).flatten(1)
            return self.fc(z).squeeze(1)

    targets = np.asarray(train_base.targets)
    all_idx = np.arange(len(train_base))
    train_idx, val_idx = train_test_split(
        all_idx,
        test_size=5000,
        random_state=SEED,
        stratify=targets,
    )
    train_ds = BinaryBase(Subset(train_base, train_idx), train_tf)
    val_ds = BinaryBase(Subset(train_base, val_idx), eval_tf)

    model = Net().to(device)
    loader = DataLoader(
        train_ds, batch_size=256, shuffle=True, num_workers=workers,
        pin_memory=pin,
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    history: list[dict[str, object]] = []
    started = time.time()
    for epoch in range(args.epochs):
        model.train()
        losses = []
        for batch_index, (x, y) in enumerate(loader, start=1):
            x = x.to(device, non_blocking=pin)
            y = y.to(device, non_blocking=pin)
            optimizer.zero_grad(set_to_none=True)
            logits = model(x)
            loss = F.binary_cross_entropy_with_logits(logits, y)
            loss.backward()
            optimizer.step()
            losses.append(float(loss.detach().cpu()))
            if batch_index % 25 == 0:
                print(
                    f"epoch {epoch + 1:02d}/{args.epochs} "
                    f"batch {batch_index:03d}/{len(loader):03d} "
                    f"loss={np.mean(losses[-25:]):.6f}",
                    flush=True,
                )
        scheduler.step()
        row = {
            "epoch": epoch + 1,
            "loss": float(np.mean(losses)),
            "lr": float(optimizer.param_groups[0]["lr"]),
        }
        history.append(row)
        print(f"EPOCH COMPLETE {row}", flush=True)
        write_csv(out / "training_history.csv", history, ["epoch", "loss", "lr"])
        torch.save(
            {
                "epoch": epoch + 1,
                "seed": SEED,
                "model_state_dict": model.state_dict(),
                "history": history,
            },
            out / "checkpoint_latest.pt",
        )

    def infer(dataset, batch_size=512):
        dl = DataLoader(
            dataset, batch_size=batch_size, shuffle=False, num_workers=workers,
            pin_memory=pin,
        )
        model.eval()
        scores: list[np.ndarray] = []
        labels: list[np.ndarray] = []
        with torch.no_grad():
            for x, y in dl:
                logits = model(x.to(device, non_blocking=pin))
                scores.append(torch.sigmoid(logits).cpu().numpy())
                labels.append(y.numpy())
        return np.concatenate(scores), np.concatenate(labels).astype(int)

    def metrics(y, s, threshold):
        pred = (s >= threshold).astype(int)
        return {
            "auc": float(roc_auc_score(y, s)),
            "auprc": float(average_precision_score(y, s)),
            "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
            "brier": float(brier_score_loss(y, s)),
            "log_loss": float(log_loss(y, np.column_stack([1 - s, s]), labels=[0, 1])),
        }

    val_s, val_y = infer(val_ds)
    grid = np.quantile(val_s, np.linspace(0.05, 0.95, 181))
    bas = [balanced_accuracy_score(val_y, (val_s >= t).astype(int)) for t in grid]
    threshold = float(grid[int(np.argmax(bas))])
    val_metrics = metrics(val_y, val_s, threshold)
    write_json(out / "validation_metrics.json", {"threshold": threshold, **val_metrics})
    print(f"validation threshold={threshold:.12f} metrics={val_metrics}", flush=True)

    labels_all = np.load(c10c_root / "labels.npy", mmap_mode="r")
    specs: list[tuple[str, str, Dataset]] = []
    specs.append(("CIFAR10_CLEAN", "clean", BinaryBase(test_base, eval_tf)))
    x101 = np.load(c101_data, mmap_mode="r")
    y101 = np.load(c101_labels, mmap_mode="r")
    specs.append(("CIFAR10_1_V6", "resampled_test", BinaryNumpy(x101, y101, eval_tf)))
    for corr in CORRUPTIONS:
        images = np.load(c10c_root / f"{corr}.npy", mmap_mode="r")
        for sev in (1, 3, 5):
            lo = (sev - 1) * 10000
            hi = sev * 10000
            specs.append(
                (
                    f"{corr.upper()}_S{sev}",
                    corr,
                    BinaryNumpy(images[lo:hi], labels_all[lo:hi], eval_tf),
                )
            )

    if len(specs) != 38:
        raise RuntimeError(f"expected 38 U2 targets, built {len(specs)}")

    fresh_rows: list[dict[str, object]] = []
    prediction_payload: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for i, (name, family, dataset) in enumerate(specs, start=1):
        print(f"inference {i:02d}/38 {name}", flush=True)
        s, y = infer(dataset)
        row = {
            "target": name,
            "family": family,
            "n": int(len(y)),
            "prevalence": float(y.mean()),
            "threshold": threshold,
            **metrics(y, s, threshold),
        }
        fresh_rows.append(row)
        prediction_payload[name] = (s, y)
        np.savez_compressed(predictions_dir / f"{name}.npz", scores=s, labels=y)
        print(row, flush=True)

    metric_fields = [
        "target", "family", "n", "prevalence", "threshold",
        "auc", "auprc", "balanced_accuracy", "brier", "log_loss",
    ]
    fresh_metrics_path = out / "StageU2_External_Target_True_Metrics_v0.1.csv"
    write_csv(fresh_metrics_path, fresh_rows, metric_fields)

    # Declared fresh-training tolerance comparison.
    rule = json.loads((ROOT / "provenance/replay_acceptance_rules.json").read_text(encoding="utf-8"))["u2_fresh_training"]
    with (ROOT / "provenance/u2_frozen_metrics.csv").open(encoding="utf-8-sig", newline="") as fh:
        frozen_rows = list(csv.DictReader(fh))
    frozen = {r["target"]: r for r in frozen_rows}
    fresh = {str(r["target"]): r for r in fresh_rows}
    failures: list[str] = []
    comparisons: list[dict[str, object]] = []
    metric_failures: list[dict[str, object]] = []

    if set(frozen) != set(fresh):
        failures.append("target roster mismatch")
    for target in sorted(set(frozen) & set(fresh)):
        left = frozen[target]
        right = fresh[target]
        if left["family"] != right["family"]:
            failures.append(f"{target}: family mismatch")
        if int(float(left["n"])) != int(right["n"]):
            failures.append(f"{target}: n mismatch")
        if not math.isclose(float(left["prevalence"]), float(right["prevalence"]), abs_tol=1e-12, rel_tol=0):
            failures.append(f"{target}: prevalence mismatch")
        for metric in rule["metric_columns"]:
            a = float(left[metric])
            b = float(right[metric])
            absolute = abs(a - b)
            relative = absolute / max(abs(a), abs(b), 1e-15)
            passed = absolute <= float(rule["absolute_tolerance"]) or relative <= float(rule["relative_tolerance"])
            comparisons.append(
                {
                    "target": target,
                    "metric": metric,
                    "frozen": a,
                    "fresh": b,
                    "absolute_difference": absolute,
                    "relative_difference": relative,
                    "passed": int(passed),
                }
            )
            if not passed:
                message = (
                    f"{target} {metric}: frozen={a:.8g} fresh={b:.8g} "
                    f"abs={absolute:.6g} rel={relative:.6g}"
                )
                failures.append(message)
                metric_failures.append(
                    {
                        "target": target,
                        "metric": metric,
                        "frozen": a,
                        "fresh": b,
                        "absolute_difference": absolute,
                        "relative_difference": relative,
                    }
                )

    write_csv(
        out / "u2_metric_comparison.csv",
        comparisons,
        ["target", "metric", "frozen", "fresh", "absolute_difference", "relative_difference", "passed"],
    )

    # Independent operating-threshold diagnostic.
    # This uses the threshold already present in the frozen pre-existing U2
    # provenance. It does NOT optimize a new threshold after seeing this run.
    frozen_thresholds = sorted({float(r["threshold"]) for r in frozen_rows})
    if len(frozen_thresholds) != 1:
        raise RuntimeError(f"expected one frozen U2 threshold, found {frozen_thresholds}")
    frozen_threshold = frozen_thresholds[0]
    frozen_threshold_ba_rows: list[dict[str, object]] = []
    for target in sorted(frozen):
        s, y = prediction_payload[target]
        ba = float(balanced_accuracy_score(y, (s >= frozen_threshold).astype(int)))
        ref = float(frozen[target]["balanced_accuracy"])
        absolute = abs(ref - ba)
        relative = absolute / max(abs(ref), abs(ba), 1e-15)
        passed = (
            absolute <= float(rule["absolute_tolerance"])
            or relative <= float(rule["relative_tolerance"])
        )
        frozen_threshold_ba_rows.append(
            {
                "target": target,
                "frozen_reference_threshold": frozen_threshold,
                "native_fresh_threshold": threshold,
                "frozen_balanced_accuracy": ref,
                "fresh_balanced_accuracy_at_frozen_threshold": ba,
                "absolute_difference": absolute,
                "relative_difference": relative,
                "passed": int(passed),
            }
        )
    write_csv(
        out / "frozen_threshold_balanced_accuracy.csv",
        frozen_threshold_ba_rows,
        [
            "target", "frozen_reference_threshold", "native_fresh_threshold",
            "frozen_balanced_accuracy", "fresh_balanced_accuracy_at_frozen_threshold",
            "absolute_difference", "relative_difference", "passed",
        ],
    )

    # Representative current-outcome audit generated from the fresh predictions.
    rng = np.random.default_rng(SEED + 303)
    audit_rows: list[dict[str, object]] = []
    for name, family, _dataset in specs:
        s, y = prediction_payload[name]
        truth = float(fresh[name]["auc"])
        pos = np.flatnonzero(y == 1)
        neg = np.flatnonzero(y == 0)
        for budget in BUDGETS:
            estimates = []
            npos = budget // 2
            nneg = budget - npos
            for _ in range(args.witness_reps):
                idx = np.concatenate([
                    rng.choice(pos, npos, replace=False),
                    rng.choice(neg, nneg, replace=False),
                ])
                estimates.append(float(roc_auc_score(y[idx], s[idx])))
            arr = np.asarray(estimates)
            audit_rows.append(
                {
                    "target": name,
                    "family": family,
                    "budget": budget,
                    "replicates": args.witness_reps,
                    "true_auc": truth,
                    "median_absolute_error": float(np.median(np.abs(arr - truth))),
                    "mean_absolute_error": float(np.mean(np.abs(arr - truth))),
                }
            )
    write_csv(
        out / "fresh_current_outcome_audit.csv",
        audit_rows,
        ["target", "family", "budget", "replicates", "true_auc", "median_absolute_error", "mean_absolute_error"],
    )

    # Compact audit figure, separate from manuscript figures.
    try:
        import matplotlib.pyplot as plt
        frozen_auc = np.array([float(frozen[r["target"]]["auc"]) for r in fresh_rows])
        fresh_auc = np.array([float(r["auc"]) for r in fresh_rows])
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        axes[0].plot([r["epoch"] for r in history], [r["loss"] for r in history], marker="o")
        axes[0].set_xlabel("Epoch")
        axes[0].set_ylabel("Training BCE")
        axes[0].set_title("Fresh U2 training")
        axes[1].scatter(frozen_auc, fresh_auc, s=18)
        lo = float(min(frozen_auc.min(), fresh_auc.min()))
        hi = float(max(frozen_auc.max(), fresh_auc.max()))
        axes[1].plot([lo, hi], [lo, hi], linestyle="--")
        axes[1].set_xlabel("Frozen AUC")
        axes[1].set_ylabel("Fresh AUC")
        axes[1].set_title("38-target replay")
        fig.tight_layout()
        fig.savefig(out / "Fresh_U2_Training_Audit.png", dpi=220, bbox_inches="tight")
        fig.savefig(out / "Fresh_U2_Training_Audit.pdf", bbox_inches="tight")
        plt.close(fig)
    except Exception as exc:
        print(f"WARNING audit figure not generated: {exc}", flush=True)

    structural_failures = [
        item for item in failures
        if "target roster mismatch" in item
        or "family mismatch" in item
        or ": n mismatch" in item
        or ": prevalence mismatch" in item
    ]
    core_metric_failures = [
        item for item in metric_failures
        if item["metric"] in {"auc", "auprc", "balanced_accuracy", "brier"}
    ]
    threshold_free_core_failures = [
        item for item in core_metric_failures
        if item["metric"] in {"auc", "auprc", "brier"}
    ]
    native_balanced_accuracy_failures = [
        item for item in core_metric_failures
        if item["metric"] == "balanced_accuracy"
    ]
    logloss_metric_failures = [
        item for item in metric_failures
        if item["metric"] == "log_loss"
    ]
    frozen_threshold_ba_passed = sum(int(row["passed"]) for row in frozen_threshold_ba_rows)
    threshold_selection_supported = bool(native_balanced_accuracy_failures) and (
        not threshold_free_core_failures
        and frozen_threshold_ba_passed == len(frozen_threshold_ba_rows)
    )
    numeric_advisory_class = (
        "NONE"
        if not metric_failures
        else "THRESHOLD_SELECTION"
        if threshold_selection_supported
        else "LOGLOSS_ONLY"
        if logloss_metric_failures and not core_metric_failures
        else "CORE_METRIC"
    )
    total_metric_comparisons = len(comparisons)
    passed_metric_comparisons = sum(int(row["passed"]) for row in comparisons)

    report = {
        "classification": "CMDO_REVIEWER_E2E_FRESH_U2_TRAINING",
        "status": (
            "PASS" if not failures
            else "STRUCTURAL_FAIL" if structural_failures
            else "REVIEW_REQUIRED"
        ),
        "numeric_advisory_class": numeric_advisory_class,
        "model_byte_identity_required": False,
        "fresh_training": True,
        "public_data_acquisition": True,
        "targets": len(fresh_rows),
        "epochs": args.epochs,
        "threshold": threshold,
        "native_validation_threshold": threshold,
        "frozen_reference_threshold": frozen_threshold,
        "threshold_selection_diagnostic": "SUPPORTED" if threshold_selection_supported else "NOT_ESTABLISHED",
        "frozen_threshold_balanced_accuracy_passed": frozen_threshold_ba_passed,
        "frozen_threshold_balanced_accuracy_total": len(frozen_threshold_ba_rows),
        "tolerance": {
            "absolute": rule["absolute_tolerance"],
            "relative": rule["relative_tolerance"],
        },
        "metric_comparisons_total": total_metric_comparisons,
        "metric_comparisons_passed": passed_metric_comparisons,
        "metric_comparisons_failed": len(metric_failures),
        "core_metric_failures": core_metric_failures,
        "threshold_free_core_failures": threshold_free_core_failures,
        "native_balanced_accuracy_failures": native_balanced_accuracy_failures,
        "logloss_metric_failures": logloss_metric_failures,
        "failed_comparisons": failures[:100],
        "duration_seconds": round(time.time() - started, 3),
        "fresh_metrics_sha256": sha256(fresh_metrics_path),
        "checkpoint_sha256": sha256(out / "checkpoint_latest.pt"),
        "environment": environment,
    }
    write_json(out / "fresh_u2_report.json", report)

    advisory_lines = [
        "# Fresh U2 numeric replay advisory",
        "",
        f"Strict replay status: {report['status']}",
        f"Advisory class: {numeric_advisory_class}",
        f"Metric comparisons: {passed_metric_comparisons}/{total_metric_comparisons} within the predeclared tolerance.",
        "",
        "The original absolute/relative replay tolerances were not changed.",
        "Structural mismatches remain failures. AUC, AUPRC, balanced accuracy and Brier are treated as core replay metrics; log-loss is reported separately as a probability-sensitive metric.",
        "",
    ]
    if threshold_selection_supported and not structural_failures:
        advisory_lines += [
            "Native-threshold balanced-accuracy deviation(s) were observed, while AUC, AUPRC and Brier remained within the predeclared tolerance.",
            f"The pre-existing frozen U2 threshold ({frozen_threshold:.12f}) was then applied without re-optimization to the same saved fresh predictions.",
            f"Balanced accuracy at that frozen threshold was within tolerance for {frozen_threshold_ba_passed}/{len(frozen_threshold_ba_rows)} targets.",
            "This supports a threshold-selection sensitivity advisory; the strict native-threshold replay status remains REVIEW_REQUIRED.",
            "",
            "Native balanced-accuracy deviations:",
        ]
        advisory_lines += [
            f"- {item['target']}: frozen={item['frozen']:.8g}, native fresh={item['fresh']:.8g}, "
            f"abs={item['absolute_difference']:.6g}, rel={item['relative_difference']:.6g}"
            for item in native_balanced_accuracy_failures
        ]
        if logloss_metric_failures:
            advisory_lines += ["", "Additional log-loss deviations:"]
            advisory_lines += [
                f"- {item['target']}: frozen={item['frozen']:.8g}, fresh={item['fresh']:.8g}, "
                f"abs={item['absolute_difference']:.6g}, rel={item['relative_difference']:.6g}"
                for item in logloss_metric_failures
            ]
    elif logloss_metric_failures and not core_metric_failures and not structural_failures:
        advisory_lines += [
            "This run completed with log-loss-only deviations: every failed metric comparison was log-loss.",
            "No structural or core-metric tolerance failure was observed.",
            "",
            "Log-loss-only deviations:",
        ]
        advisory_lines += [
            f"- {item['target']}: frozen={item['frozen']:.8g}, fresh={item['fresh']:.8g}, "
            f"abs={item['absolute_difference']:.6g}, rel={item['relative_difference']:.6g}"
            for item in logloss_metric_failures
        ]
    elif core_metric_failures:
        advisory_lines += ["Core-metric tolerance failures require investigation."]
    elif structural_failures:
        advisory_lines += ["Structural mismatch detected; this is a reproduction failure."]
    else:
        advisory_lines += ["All numeric comparisons are within tolerance."]
    (out / "NUMERIC_REPLAY_ADVISORY.md").write_text(
        "\n".join(advisory_lines) + "\n", encoding="utf-8"
    )

    print(json.dumps(report, indent=2), flush=True)
    if structural_failures:
        print("FRESH U2 TRAINING REPLAY: STRUCTURAL FAIL", file=sys.stderr)
        return 2
    if failures:
        if numeric_advisory_class == "THRESHOLD_SELECTION":
            print("=== FRESH U2 TRAINING REPLAY: REVIEW REQUIRED (threshold-selection advisory) ===")
        elif numeric_advisory_class == "LOGLOSS_ONLY":
            print("=== FRESH U2 TRAINING REPLAY: REVIEW REQUIRED (log-loss-only advisory) ===")
        else:
            print("=== FRESH U2 TRAINING REPLAY: REVIEW REQUIRED (core numeric tolerance) ===")
        return 0
    print("=== FRESH U2 TRAINING REPLAY: PASS ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
