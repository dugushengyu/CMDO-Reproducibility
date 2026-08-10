"""A minutes-scale public-data download -> train -> evaluate -> figure smoke test.

This is an engineering smoke test, not a reproduction of a manuscript estimate.
It uses the U7 source dataset family and deliberately caps the sample size.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path


UCI_DIABETES_ZIP = (
    "https://archive.ics.uci.edu/static/public/296/"
    "diabetes+130-us+hospitals+for+years+1999-2008.zip"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(output_dir: Path, *, allow_network: bool, sample_size: int) -> Path:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import pandas as pd
        from sklearn.compose import ColumnTransformer
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import RocCurveDisplay, roc_auc_score
        from sklearn.model_selection import train_test_split
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import OneHotEncoder
    except ImportError as exc:
        raise RuntimeError(
            "smoke profile requires pandas, matplotlib and scikit-learn"
        ) from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    archive_path = output_dir / "uci_diabetes_296.zip"
    if not archive_path.exists():
        if not allow_network:
            raise RuntimeError(
                "public smoke asset is absent; rerun with --allow-network"
            )
        request = urllib.request.Request(
            UCI_DIABETES_ZIP, headers={"User-Agent": "CMDO-reproducibility/0.2"}
        )
        with urllib.request.urlopen(request, timeout=180) as response:
            archive_path.write_bytes(response.read())

    with zipfile.ZipFile(archive_path) as archive:
        members = [name for name in archive.namelist() if name.endswith("dataset_diabetes/diabetic_data.csv")]
        if not members:
            members = [name for name in archive.namelist() if name.endswith("diabetic_data.csv")]
        if len(members) != 1:
            raise RuntimeError(f"unexpected UCI archive layout: {members}")
        with archive.open(members[0]) as stream:
            frame = pd.read_csv(stream, na_values=["?"])

    frame = frame.drop_duplicates(subset=["encounter_id"]).copy()
    if len(frame) > sample_size:
        frame = frame.sample(sample_size, random_state=20260725)
    target = (frame["readmitted"] == "<30").astype(int)
    features = frame[
        [
            "race",
            "gender",
            "age",
            "admission_type_id",
            "discharge_disposition_id",
            "time_in_hospital",
            "num_lab_procedures",
            "num_procedures",
            "num_medications",
            "number_diagnoses",
        ]
    ]
    categorical = ["race", "gender", "age", "admission_type_id", "discharge_disposition_id"]
    numeric = [column for column in features.columns if column not in categorical]
    preprocessor = ColumnTransformer(
        [
            (
                "categorical",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        ("encode", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical,
            ),
            (
                "numeric",
                Pipeline([("impute", SimpleImputer(strategy="median"))]),
                numeric,
            ),
        ]
    )
    model = Pipeline(
        [
            ("preprocess", preprocessor),
            (
                "classifier",
                LogisticRegression(max_iter=300, class_weight="balanced", random_state=20260725),
            ),
        ]
    )
    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=0.25,
        random_state=20260725,
        stratify=target,
    )
    model.fit(x_train, y_train)
    score = model.predict_proba(x_test)[:, 1]
    auc = float(roc_auc_score(y_test, score))
    if not 0.5 <= auc <= 1.0:
        raise RuntimeError(f"invalid smoke-test AUC: {auc}")

    figure_path = output_dir / "smoke_roc.png"
    RocCurveDisplay.from_predictions(y_test, score, name="UCI-296 smoke")
    plt.tight_layout()
    plt.savefig(figure_path, dpi=160)
    plt.close()
    result = {
        "classification": "ENGINEERING_SMOKE_TEST_NOT_MANUSCRIPT_RESULT",
        "source_url": UCI_DIABETES_ZIP,
        "download_sha256": sha256(archive_path),
        "rows_total": int(len(frame)),
        "rows_train": int(len(x_train)),
        "rows_test": int(len(x_test)),
        "positive_test": int(y_test.sum()),
        "auc": auc,
        "seed": 20260725,
        "figure": figure_path.name,
    }
    result_path = output_dir / "smoke_result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--sample-size", type=int, default=8000)
    args = parser.parse_args()
    result = run(
        args.output_dir, allow_network=args.allow_network, sample_size=args.sample_size
    )
    print(f"CMDO smoke PASS: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
