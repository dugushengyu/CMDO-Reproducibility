from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path


EXPECTED_PROTOCOL_SHA256 = (
    "c2025dd81539776b5b93f8b6c9850b33922a01edfb73275d91c7a63202ad59da"
)

EXPECTED_PREWITNESS_COMMIT = (
    "58d8ecb9952ec580d1f60345ac8127063a57532a"
)

SOURCE_SPECS = {
    "georgia": {
        "score_rel": (
            "U10_Prospective_ECG/00_Protocol/PRESEAL_SMALL/"
            "TARGET_SCORES_georgia.csv"
        ),
        "roster_rel": (
            "U10_Prospective_ECG/00_Protocol/PRESEAL_SMALL/"
            "ROSTER_georgia.csv"
        ),
        "score_sha256": (
            "53e1c9da2c4eb05ddbaca18ef1a8ace69f96ba93fcf79fb707e6fbb8f81610df"
        ),
        "roster_sha256": (
            "9706a054cd9b14fb7b038a0ce2ea8796188641dfcfb345bb643d9d3aa45db103"
        ),
        "n": 10292,
    },
    "cpsc_2018": {
        "score_rel": (
            "U10_Prospective_ECG/00_Protocol/PRESEAL_SMALL/"
            "TARGET_SCORES_cpsc_2018.csv"
        ),
        "roster_rel": (
            "U10_Prospective_ECG/00_Protocol/PRESEAL_SMALL/"
            "ROSTER_cpsc_2018.csv"
        ),
        "score_sha256": (
            "37f84929a3800a5616c75b36657681157c8d0998a0843ff633fbbb53ba64bd62"
        ),
        "roster_sha256": (
            "648785c18805c168a0469a58329552de42d7437801615253ca22674010f2eadf"
        ),
        "n": 6877,
    },
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(1024 * 1024)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def canonical_telemetry_hash(
    rows: list[dict[str, object]],
) -> str:
    """
    Hash the observation channel only:
        record_id, score_af, predicted_af

    Synthetic outcomes are deliberately excluded.
    """
    h = hashlib.sha256()
    for row in rows:
        line = (
            f"{row['record_id']}\t"
            f"{format(float(row['score_af']), '.17g')}\t"
            f"{int(row['predicted_af'])}\n"
        )
        h.update(line.encode("utf-8"))
    return h.hexdigest()


def auc_rank(
    y: list[int],
    score: list[float],
) -> float:
    """
    ROC AUC via Mann-Whitney rank statistic.

    Equal raw scores receive average ranks, therefore each
    positive-negative tied pair contributes the standard 0.5.
    """
    if len(y) != len(score):
        raise ValueError("AUC vectors have different lengths.")

    n = len(y)
    if n == 0:
        raise ValueError("Empty AUC input.")

    indexed = sorted(
        enumerate(score),
        key=lambda z: z[1],
    )

    ranks = [0.0] * n

    i = 0
    while i < n:
        j = i + 1
        value = indexed[i][1]

        while j < n and indexed[j][1] == value:
            j += 1

        # Ranks are 1-based. Positions i..j-1 therefore span
        # ranks i+1 through j.
        avg_rank = ((i + 1) + j) / 2.0

        for k in range(i, j):
            original_index = indexed[k][0]
            ranks[original_index] = avg_rank

        i = j

    n_pos = sum(y)
    n_neg = n - n_pos

    if n_pos == 0 or n_neg == 0:
        raise ValueError("AUC requires both outcome classes.")

    rank_sum_pos = sum(
        ranks[i] for i, label in enumerate(y) if label == 1
    )

    u = (
        rank_sum_pos
        - n_pos * (n_pos + 1) / 2.0
    )

    return u / (n_pos * n_neg)


def confusion_metrics(
    y: list[int],
    pred: list[int],
) -> dict[str, float | int]:
    if len(y) != len(pred):
        raise ValueError("Outcome and prediction lengths differ.")

    tp = sum(1 for a, b in zip(y, pred) if a == 1 and b == 1)
    tn = sum(1 for a, b in zip(y, pred) if a == 0 and b == 0)
    fp = sum(1 for a, b in zip(y, pred) if a == 0 and b == 1)
    fn = sum(1 for a, b in zip(y, pred) if a == 1 and b == 0)

    n = len(y)
    pos = tp + fn
    neg = tn + fp

    sensitivity = tp / pos if pos else float("nan")
    specificity = tn / neg if neg else float("nan")
    accuracy = (tp + tn) / n if n else float("nan")

    balanced_accuracy = (
        (sensitivity + specificity) / 2.0
        if math.isfinite(sensitivity) and math.isfinite(specificity)
        else float("nan")
    )

    return {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "accuracy": accuracy,
        "balanced_accuracy": balanced_accuracy,
        "sensitivity": sensitivity,
        "specificity": specificity,
    }


def brier_score(
    y: list[int],
    score: list[float],
) -> float:
    if len(y) != len(score):
        raise ValueError("Brier vectors have different lengths.")

    return sum(
        (float(p) - int(t)) ** 2
        for t, p in zip(y, score)
    ) / len(y)


def write_world_csv(
    path: Path,
    rows: list[dict[str, object]],
    synthetic_outcome: list[int],
) -> None:
    if len(rows) != len(synthetic_outcome):
        raise ValueError("World CSV vectors have different lengths.")

    fieldnames = [
        "record_id",
        "score_af",
        "predicted_af",
        "synthetic_outcome",
    ]

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()

        for row, y in zip(rows, synthetic_outcome):
            writer.writerow(
                {
                    "record_id": row["record_id"],
                    "score_af": format(
                        float(row["score_af"]),
                        ".17g",
                    ),
                    "predicted_af": int(row["predicted_af"]),
                    "synthetic_outcome": int(y),
                }
            )


def world_metrics(
    y: list[int],
    score: list[float],
    pred: list[int],
) -> dict[str, object]:
    cm = confusion_metrics(y, pred)

    return {
        "n": len(y),
        "positives": int(sum(y)),
        "prevalence": float(sum(y) / len(y)),
        "auc": float(auc_rank(y, score)),
        "accuracy": float(cm["accuracy"]),
        "balanced_accuracy": float(cm["balanced_accuracy"]),
        "sensitivity": float(cm["sensitivity"]),
        "specificity": float(cm["specificity"]),
        "brier": float(brier_score(y, score)),
        "confusion": {
            "tp": int(cm["tp"]),
            "tn": int(cm["tn"]),
            "fp": int(cm["fp"]),
            "fn": int(cm["fn"]),
        },
    }


def main() -> None:
    script_path = Path(__file__).resolve()

    # U11_Information_Closure/02_Code/script.py -> repo root
    repo = script_path.parents[2]

    protocol = (
        repo
        / "U11_Information_Closure"
        / "00_Protocol"
        / "U11_INFORMATION_CLOSURE_PROTOCOL_v0.1.json"
    )

    protocol_seal = (
        repo
        / "U11_Information_Closure"
        / "00_Protocol"
        / "U11_INFORMATION_CLOSURE_PROTOCOL_v0.1.sha256"
    )

    result_dir = (
        repo
        / "U11_Information_Closure"
        / "01_Result"
    )
    result_dir.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------
    # 1. Protocol integrity
    # --------------------------------------------------------
    protocol_sha = sha256_file(protocol)

    if protocol_sha != EXPECTED_PROTOCOL_SHA256:
        raise RuntimeError(
            "Protocol SHA256 mismatch: "
            f"{protocol_sha}"
        )

    seal_text = protocol_seal.read_text(
        encoding="utf-8-sig"
    ).strip()

    if not seal_text.startswith(EXPECTED_PROTOCOL_SHA256):
        raise RuntimeError(
            "Protocol SHA seal file mismatch."
        )

    protocol_obj = json.loads(
        protocol.read_text(encoding="utf-8")
    )

    if protocol_obj.get("status") != "PRE-WITNESS_LOCKED":
        raise RuntimeError(
            "Protocol is not PRE-WITNESS_LOCKED."
        )

    # --------------------------------------------------------
    # 2. Process BOTH locked cohorts
    # --------------------------------------------------------
    all_results: dict[str, object] = {}

    for cohort in ("georgia", "cpsc_2018"):
        spec = SOURCE_SPECS[cohort]

        score_path = repo / spec["score_rel"]
        roster_path = repo / spec["roster_rel"]

        if sha256_file(score_path) != spec["score_sha256"]:
            raise RuntimeError(
                f"{cohort}: target-score SHA256 mismatch."
            )

        if sha256_file(roster_path) != spec["roster_sha256"]:
            raise RuntimeError(
                f"{cohort}: roster SHA256 mismatch."
            )

        score_rows = read_csv(score_path)
        roster_rows = read_csv(roster_path)

        if len(score_rows) != spec["n"]:
            raise RuntimeError(
                f"{cohort}: unexpected target-score row count."
            )

        if len(roster_rows) != spec["n"]:
            raise RuntimeError(
                f"{cohort}: unexpected roster row count."
            )

        score_by_id: dict[str, dict[str, object]] = {}

        for r in score_rows:
            rid = str(r["record_id"])

            if rid in score_by_id:
                raise RuntimeError(
                    f"{cohort}: duplicate score record_id {rid}"
                )

            score = float(r["score_af"])
            pred_float = float(r["predicted_af"])

            if not math.isfinite(score):
                raise RuntimeError(
                    f"{cohort}: non-finite score."
                )

            if pred_float not in (0.0, 1.0):
                raise RuntimeError(
                    f"{cohort}: predicted_af is not binary."
                )

            score_by_id[rid] = {
                "record_id": rid,
                "score_af": score,
                "predicted_af": int(pred_float),
            }

        roster_ids = [
            str(r["record_id"])
            for r in roster_rows
        ]

        if len(set(roster_ids)) != len(roster_ids):
            raise RuntimeError(
                f"{cohort}: duplicate roster record_id."
            )

        if set(roster_ids) != set(score_by_id):
            raise RuntimeError(
                f"{cohort}: score/roster ID sets differ."
            )

        # Canonical observation order follows the frozen roster.
        rows = [
            score_by_id[rid]
            for rid in roster_ids
        ]

        n = len(rows)
        m = n // 2

        # Deterministic ranking used ONLY for synthetic
        # label selection. Raw score values remain unchanged.
        ranked_indices = sorted(
            range(n),
            key=lambda i: (
                float(rows[i]["score_af"]),
                str(rows[i]["record_id"]),
            ),
        )

        low_positive = set(ranked_indices[:m])
        high_positive = set(ranked_indices[n - m:])

        y_minus = [
            1 if i in low_positive else 0
            for i in range(n)
        ]

        y_plus = [
            1 if i in high_positive else 0
            for i in range(n)
        ]

        if sum(y_plus) != m or sum(y_minus) != m:
            raise RuntimeError(
                f"{cohort}: matched prevalence construction failed."
            )

        score_vector = [
            float(r["score_af"])
            for r in rows
        ]

        pred_vector = [
            int(r["predicted_af"])
            for r in rows
        ]

        telemetry_sha = canonical_telemetry_hash(rows)

        # WORLD_PLUS and WORLD_MINUS intentionally reuse
        # exactly the same telemetry object.
        telemetry_sha_plus = canonical_telemetry_hash(rows)
        telemetry_sha_minus = canonical_telemetry_hash(rows)

        if not (
            telemetry_sha
            == telemetry_sha_plus
            == telemetry_sha_minus
        ):
            raise RuntimeError(
                f"{cohort}: telemetry identity check failed."
            )

        plus_metrics = world_metrics(
            y_plus,
            score_vector,
            pred_vector,
        )

        minus_metrics = world_metrics(
            y_minus,
            score_vector,
            pred_vector,
        )

        if (
            plus_metrics["positives"]
            != minus_metrics["positives"]
        ):
            raise RuntimeError(
                f"{cohort}: prevalence is not matched."
            )

        prevalence_difference = abs(
            float(plus_metrics["prevalence"])
            - float(minus_metrics["prevalence"])
        )

        if prevalence_difference != 0.0:
            raise RuntimeError(
                f"{cohort}: prevalence mismatch."
            )

        auc_gap = abs(
            float(plus_metrics["auc"])
            - float(minus_metrics["auc"])
        )

        if auc_gap <= 0.0:
            raise RuntimeError(
                f"{cohort}: primary witness failed: "
                "AUC values are identical."
            )

        plus_path = (
            result_dir
            / f"U11_WORLD_PLUS_{cohort}_v0.1.csv"
        )
        minus_path = (
            result_dir
            / f"U11_WORLD_MINUS_{cohort}_v0.1.csv"
        )

        write_world_csv(
            plus_path,
            rows,
            y_plus,
        )

        write_world_csv(
            minus_path,
            rows,
            y_minus,
        )

        all_results[cohort] = {
            "source": {
                "score_rel": spec["score_rel"],
                "roster_rel": spec["roster_rel"],
                "score_sha256": spec["score_sha256"],
                "roster_sha256": spec["roster_sha256"],
            },
            "construction": {
                "n": n,
                "m": m,
                "matched_prevalence": True,
                "telemetry_sha256_world_plus": (
                    telemetry_sha_plus
                ),
                "telemetry_sha256_world_minus": (
                    telemetry_sha_minus
                ),
                "telemetry_byte_identity_claim": True,
                "score_values_modified": False,
                "outcome_source": "synthetic_protocol_locked",
            },
            "world_plus": plus_metrics,
            "world_minus": minus_metrics,
            "primary_auc_gap": auc_gap,
            "prevalence_difference": prevalence_difference,
            "primary_success": True,
        }

    # --------------------------------------------------------
    # 3. Cross-cohort verdict
    # --------------------------------------------------------
    all_success = all(
        bool(all_results[c]["primary_success"])
        for c in ("georgia", "cpsc_2018")
    )

    result = {
        "result_name": (
            "CMDO U11 Information-Closure "
            "Constructive Demonstration"
        ),
        "version": "0.1",
        "protocol_sha256": EXPECTED_PROTOCOL_SHA256,
        "prewitness_protocol_commit": (
            EXPECTED_PREWITNESS_COMMIT
        ),
        "source_outcomes_read": False,
        "true_u10_labels_used": False,
        "retraining_performed": False,
        "reinference_performed": False,
        "cohort_selection_performed": False,
        "cohorts": all_results,
        "primary_verdict": (
            "INFORMATION_CLOSURE_WITNESS_CONFIRMED"
            if all_success
            else "INFORMATION_CLOSURE_WITNESS_NOT_CONFIRMED"
        ),
        "interpretation_boundary": (
            "Constructive identification witness only; "
            "not a claim about the real clinical outcomes "
            "of either cohort."
        ),
    }

    result_path = (
        result_dir
        / "U11_INFORMATION_CLOSURE_RESULT_v0.1.json"
    )

    result_text = json.dumps(
        result,
        indent=2,
        sort_keys=False,
        ensure_ascii=True,
    ) + "\n"

    result_path.write_text(
        result_text,
        encoding="utf-8",
        newline="\n",
    )

    # --------------------------------------------------------
    # 4. Result SHA256 manifest
    # --------------------------------------------------------
    result_files = sorted(
        p for p in result_dir.iterdir()
        if p.is_file()
        and p.name != "U11_RESULT_SHA256_MANIFEST_v0.1.csv"
    )

    manifest_path = (
        result_dir
        / "U11_RESULT_SHA256_MANIFEST_v0.1.csv"
    )

    with manifest_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as f:
        writer = csv.writer(
            f,
            lineterminator="\n",
        )
        writer.writerow(
            ["file", "sha256", "bytes"]
        )

        for p in result_files:
            writer.writerow(
                [
                    p.name,
                    sha256_file(p),
                    p.stat().st_size,
                ]
            )

    # --------------------------------------------------------
    # 5. Console summary
    # --------------------------------------------------------
    print("=" * 78)
    print("CMDO U11 INFORMATION-CLOSURE WITNESS")
    print("=" * 78)
    print(f"Protocol SHA256: {EXPECTED_PROTOCOL_SHA256}")
    print("True U10 labels read: NO")
    print("Retraining: NO")
    print("Re-inference: NO")
    print()

    for cohort in ("georgia", "cpsc_2018"):
        r = all_results[cohort]

        print(f"[{cohort}]")
        print(
            "n / positives each world: "
            f"{r['construction']['n']} / "
            f"{r['world_plus']['positives']}"
        )
        print(
            "prevalence +/-: "
            f"{r['world_plus']['prevalence']:.12f} / "
            f"{r['world_minus']['prevalence']:.12f}"
        )
        print(
            "telemetry SHA +: "
            f"{r['construction']['telemetry_sha256_world_plus']}"
        )
        print(
            "telemetry SHA -: "
            f"{r['construction']['telemetry_sha256_world_minus']}"
        )
        print(
            "AUC + / -: "
            f"{r['world_plus']['auc']:.12f} / "
            f"{r['world_minus']['auc']:.12f}"
        )
        print(
            "absolute AUC gap: "
            f"{r['primary_auc_gap']:.12f}"
        )
        print(
            "Accuracy + / -: "
            f"{r['world_plus']['accuracy']:.12f} / "
            f"{r['world_minus']['accuracy']:.12f}"
        )
        print(
            "Balanced accuracy + / -: "
            f"{r['world_plus']['balanced_accuracy']:.12f} / "
            f"{r['world_minus']['balanced_accuracy']:.12f}"
        )
        print(
            "Brier + / -: "
            f"{r['world_plus']['brier']:.12f} / "
            f"{r['world_minus']['brier']:.12f}"
        )
        print(
            "PRIMARY SUCCESS: "
            f"{r['primary_success']}"
        )
        print()

    print(f"VERDICT: {result['primary_verdict']}")
    print()
    print(f"Result:   {result_path}")
    print(f"Manifest: {manifest_path}")
    print("=" * 78)


if __name__ == "__main__":
    main()
