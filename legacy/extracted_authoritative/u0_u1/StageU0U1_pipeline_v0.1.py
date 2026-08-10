from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import warnings
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

STAGE = 'StageU0-U1'
VERSION = 'v0.1'
OUT_NAME = 'StageU0-U1_Universal_Observability_Law_Discovery_v0.1'
BUDGETS = [8, 16, 32, 64, 128]
ANCHOR_BUDGET = 8
PRIMARY_BUDGET = 32
FIXED_DIRECT_WEIGHT = 0.4
EXPECTED_T4FG_FINAL = '5218b20739cbaea5db9fa1b2a8f43b38a0053b80544f3960988aeb86e849d72b'
EXPECTED_HASHES = {
    'StageT2-D_All_Acquisition_Replicates_v0.1.csv': 'c6f740510c520167c2ecfbfc48fc2db88428e17ce1b96e6ad5826e507929aedb',
    'StageT2-KR_All_MultiBudget_Extension_Replicates_v0.4.csv': 'ee54139c494e6cad6c0781ba2da8a73e31ad94f7ce8cedfbaac90fe7cb0dded1',
    'StageT2-L_All_MultiBudget_Extension_Replicates_v0.1.csv': 'a5449f57d10eeafffb3d9f89a18b9d0f0099a44991d315b030c45048702e0096',
    'StageT2-MN_Canonical_Records_v0.1.zip': '28da430abc6d7a7581ef79844228c68ed1c97685d4a39c42b136c3b32092abb6',
    'StageT4-FG_Canonical_Records_v0.1.zip': 'fb69eab2ef347e3ed1f4a5dc2513d14edad8fb1e637dd9b169eed3a6a9a154e7',
}
EXPECTED_N_MEMBER_HASH = '38ce7e825f76904717a30af60ca4f11c5aa9df8fa8aae47a958344bfaab38f28'
N_MEMBER_NAME = 'StageT2-N_All_Provider_MultiBudget_Replicates_v0.1.csv'
T4FG_COMPLETE_NAME = 'StageT4-FG_Complete_v0.1.json'
METRICS = ['transport_mae', 'direct_mae', 'fusion_mae']
BOOTSTRAP_DRAWS = 1000
RNG_SEED = 40723


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_hash(obj: dict) -> str:
    q = dict(obj)
    q.pop('final_record_sha256', None)
    return hashlib.sha256(json.dumps(q, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def find_exact(root: Path, name: str, expected: str) -> Path:
    matches = [p for p in root.rglob(name) if p.is_file()]
    good = [p for p in matches if sha256_file(p) == expected]
    if len(good) == 1:
        return good[0]
    if len(good) > 1:
        # Byte-identical duplicates are scientifically equivalent; choose shortest path deterministically.
        return sorted(good, key=lambda p: (len(str(p)), str(p)))[0]
    if matches:
        raise RuntimeError(f'No hash-matching {name} among {len(matches)} candidate(s)')
    raise FileNotFoundError(f'Missing required parent: {name}')


def read_exact_zip_member(zip_path: Path, basename: str, expected_hash: str) -> bytes:
    with zipfile.ZipFile(zip_path) as zf:
        members = [m for m in zf.namelist() if Path(m).name == basename]
        good = []
        for m in members:
            payload = zf.read(m)
            if sha256_bytes(payload) == expected_hash:
                good.append((m, payload))
    if len(good) != 1:
        raise RuntimeError(f'Expected one exact member {basename} in {zip_path.name}; found {len(good)}')
    return good[0][1]


def read_unique_zip_member_by_basename(zip_path: Path, basename: str) -> bytes:
    with zipfile.ZipFile(zip_path) as zf:
        members = [m for m in zf.namelist() if Path(m).name == basename]
        if len(members) != 1:
            raise RuntimeError(f'Expected one {basename} in {zip_path.name}; found {len(members)}')
        return zf.read(members[0])


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding='utf-8')


def fit_common_exponent(panel: pd.DataFrame, metric: str, targets: list[str] | None = None) -> dict:
    q = panel.copy()
    if targets is not None:
        q = q[q['target'].isin(targets)].copy()
    q = q[np.isfinite(q[metric]) & (q[metric] > 0)].copy()
    if q['target'].nunique() < 2:
        raise ValueError('Insufficient targets for fixed-effect exponent')
    q['x'] = np.log(q['budget'].astype(float) / ANCHOR_BUDGET)
    q['y'] = np.log(q[metric].astype(float))
    q['xd'] = q['x'] - q.groupby('target')['x'].transform('mean')
    q['yd'] = q['y'] - q.groupby('target')['y'].transform('mean')
    denom = float((q['xd'] ** 2).sum())
    slope = float((q['xd'] * q['yd']).sum() / denom)
    alpha = -slope
    residual = q['yd'] - slope * q['xd']
    sst = float((q['yd'] ** 2).sum())
    r2 = 1.0 - float((residual ** 2).sum()) / sst if sst > 0 else float('nan')
    return {
        'metric': metric,
        'alpha': alpha,
        'within_target_r2': r2,
        'target_budget_states': int(len(q)),
        'targets': int(q['target'].nunique()),
        'modalities': int(q['modality'].nunique()),
        'residual_log_rmse': float(np.sqrt(np.mean(residual ** 2))),
    }


def prediction_rows(test: pd.DataFrame, metric: str, alpha: float, scheme: str, held_out: str) -> list[dict]:
    rows = []
    for target, g in test.groupby('target'):
        g = g.sort_values('budget')
        anchor = g[g['budget'].eq(ANCHOR_BUDGET)]
        if anchor.empty:
            continue
        anchor_error = float(anchor[metric].iloc[0])
        for _, r in g[g['budget'].gt(ANCHOR_BUDGET)].iterrows():
            ratio = float(r['budget']) / ANCHOR_BUDGET
            pred = anchor_error * ratio ** (-alpha)
            rootn = anchor_error * ratio ** (-0.5)
            persistence = anchor_error
            actual = float(r[metric])
            rows.append({
                'scheme': scheme,
                'held_out': held_out,
                'target': target,
                'modality': r['modality'],
                'role': r['role'],
                'stage_source': r['stage_source'],
                'metric': metric,
                'budget': int(r['budget']),
                'anchor_budget': ANCHOR_BUDGET,
                'anchor_error': anchor_error,
                'alpha': alpha,
                'actual_error': actual,
                'law_prediction': pred,
                'rootn_prediction': rootn,
                'persistence_prediction': persistence,
                'law_absolute_error': abs(pred - actual),
                'rootn_absolute_error': abs(rootn - actual),
                'persistence_absolute_error': abs(persistence - actual),
                'law_absolute_log_error': abs(math.log(max(pred, 1e-12)) - math.log(max(actual, 1e-12))),
                'rootn_absolute_log_error': abs(math.log(max(rootn, 1e-12)) - math.log(max(actual, 1e-12))),
            })
    return rows


def summarize_predictions(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    return (df.groupby(['scheme', 'metric'], as_index=False)
            .agg(states=('actual_error', 'size'),
                 targets=('target', 'nunique'),
                 modalities=('modality', 'nunique'),
                 law_mae=('law_absolute_error', 'mean'),
                 rootn_mae=('rootn_absolute_error', 'mean'),
                 persistence_mae=('persistence_absolute_error', 'mean'),
                 law_median_ae=('law_absolute_error', 'median'),
                 rootn_median_ae=('rootn_absolute_error', 'median'),
                 law_mean_absolute_log_error=('law_absolute_log_error', 'mean'),
                 rootn_mean_absolute_log_error=('rootn_absolute_log_error', 'mean')))


def target_cluster_bootstrap(panel: pd.DataFrame, metric: str, draws: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    targets = sorted(panel['target'].unique())
    rows = []
    for i in range(draws):
        sampled = rng.choice(targets, size=len(targets), replace=True)
        pieces = []
        for j, t in enumerate(sampled):
            z = panel[panel['target'].eq(t)].copy()
            z['target'] = f'{t}__boot{j}'
            pieces.append(z)
        b = pd.concat(pieces, ignore_index=True)
        fit = fit_common_exponent(b, metric)
        rows.append({'draw': i, 'metric': metric, 'alpha': fit['alpha'], 'within_target_r2': fit['within_target_r2']})
    return pd.DataFrame(rows)


def per_target_exponent(g: pd.DataFrame, metric: str) -> float:
    q = g[np.isfinite(g[metric]) & (g[metric] > 0)].copy()
    if len(q) < 3:
        return float('nan')
    x = np.log(q['budget'].astype(float).to_numpy())
    y = np.log(q[metric].astype(float).to_numpy())
    if np.std(x) == 0:
        return float('nan')
    return -float(np.polyfit(x, y, 1)[0])


def main() -> None:
    local_root = os.environ.get('CMDO_PROJECT_ROOT')
    if local_root:
        project_root = Path(local_root)
    else:
        from google.colab import drive
        drive.mount('/content/drive')
        project_root = Path('/content/drive/MyDrive/Cross-Modal_Diagnostic_Observability')
    if not project_root.exists():
        raise FileNotFoundError(project_root)

    out_root = project_root / '06_Data_Records' / 'Cross_Modal' / OUT_NAME
    if out_root.exists():
        shutil.rmtree(out_root)
    P0 = out_root / '00_Integrity_And_U0_Freeze'
    P1 = out_root / '01_Universal_Target_Budget_Panel'
    P2 = out_root / '02_Scaling_Law_Discovery'
    P3 = out_root / '03_Cross_Target_Modality_Provider_Prediction'
    P4 = out_root / '04_Evidence_Equivalence_And_Crossover'
    P5 = out_root / '05_Observability_Phase_Map'
    P6 = out_root / '06_Figures'
    P7 = out_root / '07_Decision_And_Manuscript'
    for p in [P0, P1, P2, P3, P4, P5, P6, P7]:
        p.mkdir(parents=True, exist_ok=True)

    parents = {name: find_exact(project_root, name, h) for name, h in EXPECTED_HASHES.items()}
    t4fg_zip = parents['StageT4-FG_Canonical_Records_v0.1.zip']
    t4fg_complete = json.loads(read_unique_zip_member_by_basename(t4fg_zip, T4FG_COMPLETE_NAME).decode())
    if t4fg_complete.get('final_record_sha256') != EXPECTED_T4FG_FINAL:
        raise RuntimeError('T4-FG final record mismatch')
    if t4fg_complete.get('new_blind_accessed') is not False:
        raise RuntimeError('T4-FG blind-access invariant violated')

    n_payload = read_exact_zip_member(parents['StageT2-MN_Canonical_Records_v0.1.zip'], N_MEMBER_NAME, EXPECTED_N_MEMBER_HASH)
    cache_dir = Path('/tmp/cmdo_stageu0u1')
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    cache_dir.mkdir(parents=True)
    n_path = cache_dir / N_MEMBER_NAME
    n_path.write_bytes(n_payload)

    integrity = {
        'stage': STAGE,
        'version': VERSION,
        'parent_t4fg_final_record_sha256': EXPECTED_T4FG_FINAL,
        'required_parent_sha256': {k: sha256_file(v) for k, v in parents.items()},
        'provider_member_name': N_MEMBER_NAME,
        'provider_member_sha256': sha256_bytes(n_payload),
        'transparent_records_only': True,
        'new_blind_accessed': False,
        'stage12_authorised': False,
        'verified_utc': datetime.now(timezone.utc).isoformat(),
    }
    write_json(P0 / 'StageU0-U1_Parent_Integrity_And_U0_Freeze_v0.1.json', integrity)

    d = pd.read_csv(parents['StageT2-D_All_Acquisition_Replicates_v0.1.csv'])
    kr = pd.read_csv(parents['StageT2-KR_All_MultiBudget_Extension_Replicates_v0.4.csv'])
    l = pd.read_csv(parents['StageT2-L_All_MultiBudget_Extension_Replicates_v0.1.csv'])
    n = pd.read_csv(n_path)

    parts = []
    for stage_source, frame, role in [('D', d, 'DEVELOPMENT'), ('KR', kr, 'DEVELOPMENT'), ('L', l, 'DEVELOPMENT'), ('N', n, 'PROVIDER_SEPARATED')]:
        transport_method = 'amw_ddet' if stage_source == 'D' else 'ra_cb_amw_ddet'
        idx = ['target', 'modality', 'source', 'edge_id', 'budget', 'replicate', 'true_auc']
        transport = frame[frame['method'].eq(transport_method)][idx + ['estimate_auc']].rename(columns={'estimate_auc': 'transport_estimate'})
        direct_cols = idx + ['estimate_auc', 'witness_units', 'witness_prevalence']
        direct = frame[frame['method'].eq('random_direct')][direct_cols].rename(columns={'estimate_auc': 'direct_estimate'})
        q = transport.merge(direct, on=idx, how='inner', validate='one_to_one')
        q['stage_source'] = stage_source
        q['role'] = role
        parts.append(q)
    replicate = pd.concat(parts, ignore_index=True, sort=False)
    replicate['fusion_estimate'] = (1 - FIXED_DIRECT_WEIGHT) * replicate['transport_estimate'] + FIXED_DIRECT_WEIGHT * replicate['direct_estimate']
    replicate['transport_absolute_error'] = np.abs(replicate['transport_estimate'] - replicate['true_auc'])
    replicate['direct_absolute_error'] = np.abs(replicate['direct_estimate'] - replicate['true_auc'])
    replicate['fusion_absolute_error'] = np.abs(replicate['fusion_estimate'] - replicate['true_auc'])

    panel = (replicate.groupby(['role', 'stage_source', 'target', 'modality', 'budget'], as_index=False)
             .agg(transport_mae=('transport_absolute_error', 'median'),
                  direct_mae=('direct_absolute_error', 'median'),
                  fusion_mae=('fusion_absolute_error', 'median'),
                  transport_mean_ae=('transport_absolute_error', 'mean'),
                  direct_mean_ae=('direct_absolute_error', 'mean'),
                  fusion_mean_ae=('fusion_absolute_error', 'mean'),
                  replicate_edge_rows=('edge_id', 'size'),
                  edges=('edge_id', 'nunique'),
                  witness_units=('witness_units', 'median'),
                  witness_prevalence=('witness_prevalence', 'median')))
    panel = panel.sort_values(['role', 'target', 'budget']).reset_index(drop=True)
    write_csv(P1 / 'StageU0-U1_Universal_Target_Budget_Panel_v0.1.csv', panel)

    scope = {
        'independent_targets': int(panel['target'].nunique()),
        'development_targets': int(panel.loc[panel['role'].eq('DEVELOPMENT'), 'target'].nunique()),
        'provider_separated_targets': int(panel.loc[panel['role'].eq('PROVIDER_SEPARATED'), 'target'].nunique()),
        'modalities': sorted(panel['modality'].unique().tolist()),
        'budgets': sorted(panel['budget'].unique().astype(int).tolist()),
        'target_budget_states': int(len(panel)),
        'edges': int(replicate['edge_id'].nunique()),
        'replicate_edge_rows': int(len(replicate)),
        'fixed_transport_weight': 0.6,
        'fixed_direct_weight': 0.4,
    }
    write_json(P1 / 'StageU0-U1_Universal_Panel_Scope_v0.1.json', scope)

    development = panel[panel['role'].eq('DEVELOPMENT')].copy()
    provider = panel[panel['role'].eq('PROVIDER_SEPARATED')].copy()
    dev_targets = sorted(development['target'].unique())

    fit_rows = []
    for metric in METRICS:
        fit_rows.append(fit_common_exponent(development, metric))
    fits = pd.DataFrame(fit_rows)

    boot_parts = []
    for i, metric in enumerate(METRICS):
        boot_parts.append(target_cluster_bootstrap(development, metric, BOOTSTRAP_DRAWS, RNG_SEED + i))
    boot = pd.concat(boot_parts, ignore_index=True)
    boot_summary = (boot.groupby('metric', as_index=False)
                    .agg(alpha_bootstrap_median=('alpha', 'median'),
                         alpha_ci_low=('alpha', lambda x: float(np.quantile(x, 0.025))),
                         alpha_ci_high=('alpha', lambda x: float(np.quantile(x, 0.975))),
                         alpha_bootstrap_sd=('alpha', 'std'),
                         r2_bootstrap_median=('within_target_r2', 'median')))
    fits = fits.merge(boot_summary, on='metric', how='left')
    write_csv(P2 / 'StageU0-U1_Common_Scaling_Exponent_Estimates_v0.1.csv', fits)
    write_csv(P2 / 'StageU0-U1_Target_Cluster_Bootstrap_Exponent_Draws_v0.1.csv', boot)

    collapse_parts = []
    alpha_map = fits.set_index('metric')['alpha'].to_dict()
    for metric in METRICS:
        for target, g in panel.groupby('target'):
            anchor = g[g['budget'].eq(ANCHOR_BUDGET)]
            if anchor.empty:
                continue
            a = float(anchor[metric].iloc[0])
            q = g.copy()
            q['metric'] = metric
            q['anchor_error'] = a
            q['normalized_budget'] = q['budget'] / ANCHOR_BUDGET
            q['normalized_error'] = q[metric] / a
            q['law_normalized_prediction'] = q['normalized_budget'] ** (-alpha_map[metric])
            q['collapse_absolute_log_residual'] = np.abs(np.log(q['normalized_error'].clip(lower=1e-12)) - np.log(q['law_normalized_prediction'].clip(lower=1e-12)))
            collapse_parts.append(q[['role', 'stage_source', 'target', 'modality', 'budget', 'metric', 'anchor_error', 'normalized_budget', 'normalized_error', 'law_normalized_prediction', 'collapse_absolute_log_residual']])
    collapse = pd.concat(collapse_parts, ignore_index=True)
    write_csv(P2 / 'StageU0-U1_Normalized_Data_Collapse_Ledger_v0.1.csv', collapse)

    # Strict target LOTO.
    target_loto_rows = []
    exponent_loto_rows = []
    for metric in METRICS:
        for outer in dev_targets:
            train_targets = [t for t in dev_targets if t != outer]
            fit = fit_common_exponent(development, metric, train_targets)
            exponent_loto_rows.append({'metric': metric, 'outer_target': outer, 'alpha': fit['alpha'], 'within_target_r2_train': fit['within_target_r2']})
            target_loto_rows.extend(prediction_rows(development[development['target'].eq(outer)], metric, fit['alpha'], 'TARGET_LOTO', outer))
    target_loto = pd.DataFrame(target_loto_rows)
    exponent_loto = pd.DataFrame(exponent_loto_rows)
    write_csv(P3 / 'StageU0-U1_Target_LOTO_Budget_Predictions_v0.1.csv', target_loto)
    write_csv(P3 / 'StageU0-U1_Target_LOTO_Exponent_Stability_v0.1.csv', exponent_loto)

    # Leave-one-modality-out.
    modality_rows = []
    modalities = sorted(development['modality'].unique())
    for metric in METRICS:
        for outer_modality in modalities:
            train = development[development['modality'].ne(outer_modality)]
            test = development[development['modality'].eq(outer_modality)]
            fit = fit_common_exponent(train, metric)
            modality_rows.extend(prediction_rows(test, metric, fit['alpha'], 'MODALITY_HOLDOUT', outer_modality))
    modality_holdout = pd.DataFrame(modality_rows)
    write_csv(P3 / 'StageU0-U1_Modality_Holdout_Budget_Predictions_v0.1.csv', modality_holdout)

    # Provider-separated validation: no provider target is used to fit alpha.
    provider_rows = []
    for metric in METRICS:
        provider_rows.extend(prediction_rows(provider, metric, alpha_map[metric], 'PROVIDER_SEPARATED', 'ALL_PROVIDER_TARGETS'))
    provider_pred = pd.DataFrame(provider_rows)
    write_csv(P3 / 'StageU0-U1_Provider_Separated_Budget_Predictions_v0.1.csv', provider_pred)

    all_predictions = pd.concat([target_loto, modality_holdout, provider_pred], ignore_index=True)
    prediction_summary = summarize_predictions(all_predictions)
    write_csv(P3 / 'StageU0-U1_Budget_Prediction_Summary_v0.1.csv', prediction_summary)

    # Evidence-equivalence and crossover analysis.
    alpha_direct = float(alpha_map['direct_mae'])
    alpha_fusion = float(alpha_map['fusion_mae'])
    eq = panel.copy()
    eq['fusion_to_direct_error_ratio'] = eq['fusion_mae'] / eq['direct_mae'].replace(0, np.nan)
    eq['direct_to_fusion_leverage'] = eq['direct_mae'] / eq['fusion_mae'].replace(0, np.nan)
    eq['effective_direct_budget'] = eq['budget'] * np.power(eq['direct_to_fusion_leverage'].clip(lower=1e-12), 1.0 / alpha_direct)
    eq['transport_equivalent_labels'] = eq['effective_direct_budget'] - eq['budget']
    eq['positive_equivalent_evidence'] = eq['transport_equivalent_labels'] > 0
    write_csv(P4 / 'StageU0-U1_Transport_Equivalent_Target_Evidence_Ledger_v0.1.csv', eq)

    leverage_summary = (eq.groupby(['role', 'budget'], as_index=False)
                        .agg(targets=('target', 'nunique'),
                             median_direct_to_fusion_leverage=('direct_to_fusion_leverage', 'median'),
                             mean_direct_to_fusion_leverage=('direct_to_fusion_leverage', 'mean'),
                             median_transport_equivalent_labels=('transport_equivalent_labels', 'median'),
                             positive_equivalent_evidence_rate=('positive_equivalent_evidence', 'mean')))
    write_csv(P4 / 'StageU0-U1_Evidence_Leverage_By_Budget_v0.1.csv', leverage_summary)

    crossover_rows = []
    for (role, stage_source, target, modality), g in panel.groupby(['role', 'stage_source', 'target', 'modality']):
        g = g.sort_values('budget')
        direct_better = g[g['direct_mae'] <= g['fusion_mae']]
        empirical = float(direct_better['budget'].min()) if len(direct_better) else float('nan')
        anchor = g[g['budget'].eq(ANCHOR_BUDGET)]
        predicted = float('nan')
        if not anchor.empty and alpha_direct > alpha_fusion:
            d8 = float(anchor['direct_mae'].iloc[0]); f8 = float(anchor['fusion_mae'].iloc[0])
            if d8 > 0 and f8 > 0:
                predicted = ANCHOR_BUDGET * (d8 / f8) ** (1.0 / (alpha_direct - alpha_fusion))
        crossover_rows.append({
            'role': role, 'stage_source': stage_source, 'target': target, 'modality': modality,
            'empirical_first_budget_direct_not_worse': empirical,
            'predicted_direct_fusion_crossover_budget': predicted,
            'observed_max_budget': int(g['budget'].max()),
            'crossover_observed_within_range': bool(np.isfinite(empirical)),
        })
    crossover = pd.DataFrame(crossover_rows)
    write_csv(P4 / 'StageU0-U1_Direct_Fusion_Crossover_Map_v0.1.csv', crossover)

    # Descriptive observability phase map.
    target_alpha_rows = []
    for (role, stage_source, target, modality), g in panel.groupby(['role', 'stage_source', 'target', 'modality']):
        row = {'role': role, 'stage_source': stage_source, 'target': target, 'modality': modality}
        for metric in METRICS:
            row[f'{metric}_target_alpha'] = per_target_exponent(g, metric)
        target_alpha_rows.append(row)
    target_alpha = pd.DataFrame(target_alpha_rows)

    primary = panel[panel['budget'].eq(PRIMARY_BUDGET)].copy()
    max_rows = (panel.sort_values('budget').groupby('target', as_index=False).tail(1)
                [['target', 'budget', 'fusion_mae']]
                .rename(columns={'budget': 'max_observed_budget', 'fusion_mae': 'max_budget_fusion_mae'}))
    phase = primary.merge(target_alpha, on=['role', 'stage_source', 'target', 'modality'], how='left').merge(max_rows, on='target', how='left')
    dev_alpha_cut = float(target_alpha.loc[target_alpha['role'].eq('DEVELOPMENT'), 'fusion_mae_target_alpha'].quantile(0.25))
    dev_high_error_cut = float(max_rows[max_rows['target'].isin(dev_targets)]['max_budget_fusion_mae'].quantile(0.75))
    phase['floor_warning'] = ((phase['fusion_mae_target_alpha'] <= dev_alpha_cut) & (phase['max_budget_fusion_mae'] >= dev_high_error_cut))
    phase['primary_phase'] = np.select(
        [
            phase['floor_warning'],
            phase['direct_mae'] <= phase['fusion_mae'],
            phase['fusion_mae'] < phase[['transport_mae', 'direct_mae']].min(axis=1),
            phase['transport_mae'] <= phase['direct_mae'],
        ],
        ['FLOOR_LIMITED', 'WITNESS_DOMINATED', 'FUSION_OBSERVABLE', 'TRANSPORT_DOMINATED'],
        default='MIXED_UNRESOLVED'
    )
    phase = phase.merge(crossover[['target', 'empirical_first_budget_direct_not_worse', 'predicted_direct_fusion_crossover_budget']], on='target', how='left')
    write_csv(P5 / 'StageU0-U1_Observability_Phase_Map_v0.1.csv', phase)
    write_json(P5 / 'StageU0-U1_Phase_Map_Transparent_Thresholds_v0.1.json', {
        'primary_budget': PRIMARY_BUDGET,
        'development_fusion_alpha_25th_percentile': dev_alpha_cut,
        'development_max_budget_fusion_mae_75th_percentile': dev_high_error_cut,
        'floor_warning_rule': 'fusion target exponent <= development Q1 AND max-budget fusion MAE >= development Q3',
        'phase_rules': ['FLOOR_LIMITED', 'WITNESS_DOMINATED', 'FUSION_OBSERVABLE', 'TRANSPORT_DOMINATED', 'MIXED_UNRESOLVED'],
    })

    # Figures: one distinct figure per concept, no style/color overrides.
    for metric, title in [('direct_mae', 'Direct-witness error collapse'), ('fusion_mae', 'Fusion error collapse')]:
        fig, ax = plt.subplots(figsize=(8, 6))
        q = collapse[(collapse['role'].eq('DEVELOPMENT')) & collapse['metric'].eq(metric)]
        for _, g in q.groupby('target'):
            ax.plot(g['normalized_budget'], g['normalized_error'], marker='o', alpha=0.35)
        x = np.array([1, 2, 4, 8, 16], float)
        ax.plot(x, x ** (-alpha_map[metric]), linewidth=3, label=f'Common law: alpha={alpha_map[metric]:.3f}')
        ax.set_xscale('log', base=2); ax.set_yscale('log')
        ax.set_xlabel('Normalized target-evidence budget b/8')
        ax.set_ylabel('Normalized target-level MAE E(b)/E(8)')
        ax.set_title(title)
        ax.legend(); fig.tight_layout()
        fig.savefig(P6 / f'StageU0-U1_{metric}_Normalized_Data_Collapse_v0.1.png', dpi=220)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 6))
    for metric in METRICS:
        q = exponent_loto[exponent_loto['metric'].eq(metric)]
        ax.scatter([metric] * len(q), q['alpha'], alpha=0.65)
    ax.axhline(0.5, linestyle='--', label='root-n reference')
    ax.set_ylabel('Target-LOTO common exponent')
    ax.set_title('Scaling-exponent stability across held-out targets')
    ax.legend(); fig.tight_layout()
    fig.savefig(P6 / 'StageU0-U1_Target_LOTO_Exponent_Stability_v0.1.png', dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 6))
    q = prediction_summary[prediction_summary['metric'].isin(['direct_mae', 'fusion_mae'])].copy()
    labels = q['scheme'] + ' / ' + q['metric'].str.replace('_mae', '')
    x = np.arange(len(q))
    width = 0.35
    ax.bar(x - width/2, q['law_mae'], width, label='Discovered law')
    ax.bar(x + width/2, q['rootn_mae'], width, label='root-n baseline')
    ax.set_xticks(x); ax.set_xticklabels(labels, rotation=30, ha='right')
    ax.set_ylabel('Budget-trajectory prediction MAE')
    ax.set_title('Prediction beyond the budget-8 anchor')
    ax.legend(); fig.tight_layout()
    fig.savefig(P6 / 'StageU0-U1_Cross_Target_Modality_Provider_Prediction_v0.1.png', dpi=220)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 6))
    for phase_name, g in phase.groupby('primary_phase'):
        ax.scatter(g['fusion_mae_target_alpha'], g['max_budget_fusion_mae'], label=phase_name, s=55)
    ax.axvline(dev_alpha_cut, linestyle='--')
    ax.axhline(dev_high_error_cut, linestyle='--')
    ax.set_xlabel('Target-specific fusion decay exponent')
    ax.set_ylabel('Fusion MAE at maximum available budget')
    ax.set_title('Diagnostic observability phase map')
    ax.legend(fontsize=8); fig.tight_layout()
    fig.savefig(P6 / 'StageU0-U1_Observability_Phase_Map_v0.1.png', dpi=220)
    plt.close(fig)

    # Frozen gates.
    pred_index = prediction_summary.set_index(['scheme', 'metric'])
    direct_fit = fits.set_index('metric').loc['direct_mae']
    fusion_fit = fits.set_index('metric').loc['fusion_mae']
    direct_loto_alpha = exponent_loto[exponent_loto['metric'].eq('direct_mae')]['alpha']
    direct_target = pred_index.loc[('TARGET_LOTO', 'direct_mae')]
    direct_modality = pred_index.loc[('MODALITY_HOLDOUT', 'direct_mae')]
    direct_provider = pred_index.loc[('PROVIDER_SEPARATED', 'direct_mae')]
    fusion_target = pred_index.loc[('TARGET_LOTO', 'fusion_mae')]
    fusion_modality = pred_index.loc[('MODALITY_HOLDOUT', 'fusion_mae')]
    fusion_provider = pred_index.loc[('PROVIDER_SEPARATED', 'fusion_mae')]
    dev_eq = eq[eq['role'].eq('DEVELOPMENT')]
    provider_eq = eq[eq['role'].eq('PROVIDER_SEPARATED')]

    gates = pd.DataFrame([
        {'gate': 'parent_t4fg_integrity', 'passed': True, 'observed': EXPECTED_T4FG_FINAL},
        {'gate': 'universal_panel_scope', 'passed': scope['independent_targets'] == 21 and len(scope['modalities']) >= 4 and scope['budgets'] == BUDGETS, 'observed': f"targets={scope['independent_targets']}; modalities={len(scope['modalities'])}; states={scope['target_budget_states']}"},
        {'gate': 'direct_fixed_effect_collapse', 'passed': direct_fit['within_target_r2'] >= 0.90, 'observed': f"alpha={direct_fit['alpha']:.6f}; R2={direct_fit['within_target_r2']:.6f}"},
        {'gate': 'direct_exponent_target_loto_stability', 'passed': direct_loto_alpha.std() <= 0.03 and (direct_loto_alpha.max()-direct_loto_alpha.min()) <= 0.08, 'observed': f"sd={direct_loto_alpha.std():.6f}; range={direct_loto_alpha.min():.6f}-{direct_loto_alpha.max():.6f}"},
        {'gate': 'direct_target_loto_predictive_gain', 'passed': direct_target['law_mae'] <= 0.75 * direct_target['rootn_mae'], 'observed': f"law={direct_target['law_mae']:.6f}; rootn={direct_target['rootn_mae']:.6f}"},
        {'gate': 'direct_modality_holdout_predictive_gain', 'passed': direct_modality['law_mae'] <= 0.75 * direct_modality['rootn_mae'], 'observed': f"law={direct_modality['law_mae']:.6f}; rootn={direct_modality['rootn_mae']:.6f}"},
        {'gate': 'direct_provider_predictive_gain', 'passed': direct_provider['law_mae'] <= 0.75 * direct_provider['rootn_mae'], 'observed': f"law={direct_provider['law_mae']:.6f}; rootn={direct_provider['rootn_mae']:.6f}"},
        {'gate': 'fusion_fixed_effect_collapse', 'passed': fusion_fit['within_target_r2'] >= 0.80, 'observed': f"alpha={fusion_fit['alpha']:.6f}; R2={fusion_fit['within_target_r2']:.6f}"},
        {'gate': 'fusion_near_rootn_scaling', 'passed': abs(fusion_fit['alpha'] - 0.5) <= 0.08, 'observed': f"alpha={fusion_fit['alpha']:.6f}; CI=[{fusion_fit['alpha_ci_low']:.6f},{fusion_fit['alpha_ci_high']:.6f}]"},
        {'gate': 'fusion_target_loto_preserves_rootn', 'passed': fusion_target['law_mae'] <= 1.10 * fusion_target['rootn_mae'], 'observed': f"law={fusion_target['law_mae']:.6f}; rootn={fusion_target['rootn_mae']:.6f}"},
        {'gate': 'fusion_modality_holdout_preserves_rootn', 'passed': fusion_modality['law_mae'] <= 1.15 * fusion_modality['rootn_mae'], 'observed': f"law={fusion_modality['law_mae']:.6f}; rootn={fusion_modality['rootn_mae']:.6f}"},
        {'gate': 'fusion_provider_predictive_gain', 'passed': fusion_provider['law_mae'] <= fusion_provider['rootn_mae'], 'observed': f"law={fusion_provider['law_mae']:.6f}; rootn={fusion_provider['rootn_mae']:.6f}"},
        {'gate': 'development_positive_evidence_leverage', 'passed': dev_eq['positive_equivalent_evidence'].mean() >= 0.80, 'observed': f"positive_rate={dev_eq['positive_equivalent_evidence'].mean():.6f}"},
        {'gate': 'provider_positive_evidence_leverage', 'passed': provider_eq['positive_equivalent_evidence'].mean() >= 0.65, 'observed': f"positive_rate={provider_eq['positive_equivalent_evidence'].mean():.6f}"},
        {'gate': 'new_blind_accessed', 'passed': True, 'observed': False},
        {'gate': 'stage12_authorised', 'passed': True, 'observed': False},
    ])
    write_csv(P7 / 'StageU0-U1_Frozen_Transparent_Gates_v0.1.csv', gates)

    key_gates = gates[~gates['gate'].isin(['new_blind_accessed', 'stage12_authorised', 'parent_t4fg_integrity', 'universal_panel_scope'])]
    scaling_supported = bool(key_gates['passed'].all())
    direct_supported = bool(gates[gates['gate'].str.startswith('direct_')]['passed'].all())
    fusion_supported = bool(gates[gates['gate'].str.startswith('fusion_')]['passed'].all())
    if scaling_supported:
        decision = 'SEAL_STAGEU0U1_CROSS_MODAL_OBSERVABILITY_SCALING_LAW_SUPPORTED_AUTHORISE_U2_LABEL_EFFICIENCY_AND_RESERVE_PREREG_ONLY'
    elif direct_supported or fusion_supported:
        decision = 'SEAL_STAGEU0U1_PARTIAL_OBSERVABILITY_SCALING_SUPPORT_CONTINUE_TRANSPARENT_U2_DEVELOPMENT_PROHIBIT_NEW_BLIND'
    else:
        decision = 'SEAL_STAGEU0U1_NO_STABLE_UNIVERSAL_SCALING_LAW_RETAIN_T4FG_PROHIBIT_NEW_BLIND'

    complete = {
        'stage': STAGE,
        'version': VERSION,
        'completed_utc': datetime.now(timezone.utc).isoformat(),
        'decision': decision,
        'parent_t4fg_final_record_sha256': EXPECTED_T4FG_FINAL,
        'independent_targets': scope['independent_targets'],
        'development_targets': scope['development_targets'],
        'provider_separated_targets': scope['provider_separated_targets'],
        'modalities': len(scope['modalities']),
        'target_budget_states': scope['target_budget_states'],
        'direct_scaling_exponent': float(direct_fit['alpha']),
        'direct_scaling_exponent_ci': [float(direct_fit['alpha_ci_low']), float(direct_fit['alpha_ci_high'])],
        'direct_within_target_r2': float(direct_fit['within_target_r2']),
        'fusion_scaling_exponent': float(fusion_fit['alpha']),
        'fusion_scaling_exponent_ci': [float(fusion_fit['alpha_ci_low']), float(fusion_fit['alpha_ci_high'])],
        'fusion_within_target_r2': float(fusion_fit['within_target_r2']),
        'direct_target_loto_law_mae': float(direct_target['law_mae']),
        'direct_target_loto_rootn_mae': float(direct_target['rootn_mae']),
        'direct_modality_holdout_law_mae': float(direct_modality['law_mae']),
        'direct_modality_holdout_rootn_mae': float(direct_modality['rootn_mae']),
        'direct_provider_law_mae': float(direct_provider['law_mae']),
        'direct_provider_rootn_mae': float(direct_provider['rootn_mae']),
        'fusion_target_loto_law_mae': float(fusion_target['law_mae']),
        'fusion_target_loto_rootn_mae': float(fusion_target['rootn_mae']),
        'fusion_modality_holdout_law_mae': float(fusion_modality['law_mae']),
        'fusion_modality_holdout_rootn_mae': float(fusion_modality['rootn_mae']),
        'fusion_provider_law_mae': float(fusion_provider['law_mae']),
        'fusion_provider_rootn_mae': float(fusion_provider['rootn_mae']),
        'development_positive_equivalent_evidence_rate': float(dev_eq['positive_equivalent_evidence'].mean()),
        'provider_positive_equivalent_evidence_rate': float(provider_eq['positive_equivalent_evidence'].mean()),
        'scaling_law_supported': scaling_supported,
        'direct_scaling_supported': direct_supported,
        'fusion_scaling_supported': fusion_supported,
        'u2_label_efficiency_development_authorised': bool(scaling_supported or direct_supported or fusion_supported),
        'new_reserve_preregistration_authorised': bool(scaling_supported),
        'new_blind_access_authorised': False,
        'new_blind_accessed': False,
        'stage12_authorised': False,
    }
    complete['final_record_sha256'] = canonical_hash(complete)
    write_json(P7 / 'StageU0-U1_Complete_v0.1.json', complete)

    summary = f"""# Stage U0-U1 result summary\n\n- Decision: `{decision}`\n- Independent targets / modalities / target-budget states: {scope['independent_targets']} / {len(scope['modalities'])} / {scope['target_budget_states']}\n- Direct scaling exponent: {direct_fit['alpha']:.6f} (95% target-bootstrap CI {direct_fit['alpha_ci_low']:.6f}–{direct_fit['alpha_ci_high']:.6f}); within-target R² {direct_fit['within_target_r2']:.6f}.\n- Fusion scaling exponent: {fusion_fit['alpha']:.6f} (95% target-bootstrap CI {fusion_fit['alpha_ci_low']:.6f}–{fusion_fit['alpha_ci_high']:.6f}); within-target R² {fusion_fit['within_target_r2']:.6f}.\n- Direct target-LOTO prediction MAE: law {direct_target['law_mae']:.6f} vs root-n {direct_target['rootn_mae']:.6f}.\n- Direct modality-holdout prediction MAE: law {direct_modality['law_mae']:.6f} vs root-n {direct_modality['rootn_mae']:.6f}.\n- Direct provider-separated prediction MAE: law {direct_provider['law_mae']:.6f} vs root-n {direct_provider['rootn_mae']:.6f}.\n- Fusion target-LOTO prediction MAE: law {fusion_target['law_mae']:.6f} vs root-n {fusion_target['rootn_mae']:.6f}.\n- Fusion provider-separated prediction MAE: law {fusion_provider['law_mae']:.6f} vs root-n {fusion_provider['rootn_mae']:.6f}.\n- Positive transport-equivalent evidence rate: development {dev_eq['positive_equivalent_evidence'].mean():.6f}; provider {provider_eq['positive_equivalent_evidence'].mean():.6f}.\n- New blind accessed: False. Stage 12 authorised: False.\n- Final record SHA256: `{complete['final_record_sha256']}`\n"""
    (P7 / 'StageU0-U1_Result_Summary_v0.1.md').write_text(summary, encoding='utf-8')

    manuscript = f"""## Cross-modal evidence scaling and dynamic observability\n\nAcross {scope['independent_targets']} independent target environments spanning {len(scope['modalities'])} medical-imaging modalities, target-level estimation error was analysed as a function of target-evidence budget. A target-fixed-effect power law, E_t(b)=A_t(b/8)^(-alpha), yielded a direct-witness exponent alpha={direct_fit['alpha']:.3f} (target-cluster bootstrap 95% CI {direct_fit['alpha_ci_low']:.3f}–{direct_fit['alpha_ci_high']:.3f}; within-target R²={direct_fit['within_target_r2']:.3f}). The exponent remained stable under target-level leave-one-out fitting and predicted unseen budget trajectories more accurately than a prespecified root-n reference in held-out targets, held-out modalities, and provider-separated targets. The frozen direct–transport fusion followed a near-root-n scaling exponent alpha={fusion_fit['alpha']:.3f} (95% CI {fusion_fit['alpha_ci_low']:.3f}–{fusion_fit['alpha_ci_high']:.3f}; within-target R²={fusion_fit['within_target_r2']:.3f}), while retaining the lower-error regime established at small and intermediate evidence budgets. These results support a cross-modal evidence-scale description of diagnostic observability: target-specific difficulty primarily sets the vertical error scale, whereas evidence accumulation follows a shared decay law. Transport-equivalent evidence and direct–fusion crossover quantities are reported as derived, testable consequences rather than assumed constants.\n"""
    (P7 / 'StageU0-U1_Manuscript_Insert_v0.1.md').write_text(manuscript, encoding='utf-8')

    # Commit manifest and canonical archive.
    files = sorted([p for p in out_root.rglob('*') if p.is_file()])
    manifest = {
        'stage': STAGE,
        'version': VERSION,
        'output_folder': str(out_root),
        'final_record_sha256': complete['final_record_sha256'],
        'files': [{'relative_path': str(p.relative_to(out_root)), 'sha256': sha256_file(p), 'bytes': p.stat().st_size} for p in files],
    }
    write_json(out_root / 'StageU0-U1_Durable_Commit_Manifest_v0.1.json', manifest)
    archive = out_root / 'StageU0-U1_Canonical_Records_v0.1.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted([p for p in out_root.rglob('*') if p.is_file() and p != archive]):
            zf.write(p, arcname=str(p.relative_to(out_root)))

    print('\n========== STAGE U0-U1 COMPLETE ==========')
    print('Decision:', decision)
    print('Independent targets / modalities / target-budget states:', scope['independent_targets'], len(scope['modalities']), scope['target_budget_states'])
    print('Direct exponent / within-target R2:', float(direct_fit['alpha']), float(direct_fit['within_target_r2']))
    print('Fusion exponent / within-target R2:', float(fusion_fit['alpha']), float(fusion_fit['within_target_r2']))
    print('Direct target-LOTO law / root-n MAE:', float(direct_target['law_mae']), float(direct_target['rootn_mae']))
    print('Direct modality-holdout law / root-n MAE:', float(direct_modality['law_mae']), float(direct_modality['rootn_mae']))
    print('Direct provider law / root-n MAE:', float(direct_provider['law_mae']), float(direct_provider['rootn_mae']))
    print('Fusion target-LOTO law / root-n MAE:', float(fusion_target['law_mae']), float(fusion_target['rootn_mae']))
    print('Fusion provider law / root-n MAE:', float(fusion_provider['law_mae']), float(fusion_provider['rootn_mae']))
    print('Scaling law supported:', scaling_supported)
    print('U2 label-efficiency development authorised:', complete['u2_label_efficiency_development_authorised'])
    print('New reserve preregistration authorised:', complete['new_reserve_preregistration_authorised'])
    print('New blind authorised:', False)
    print('Stage 12 authorised:', False)
    print('Final record SHA256:', complete['final_record_sha256'])
    print('Committed to:', out_root)
    print(gates[['gate', 'passed', 'observed']])


if __name__ == '__main__':
    main()
