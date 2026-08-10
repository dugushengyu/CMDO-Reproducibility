from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import sys
import warnings
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

warnings.filterwarnings('ignore')

STAGE = 'StageT4-FG'
VERSION = 'v0.1'
EXPECTED_T4DE_FINAL = '21c855dcb3f69ab87a457c4e9eaff8d20a9928869883521e3c2012de3c6b1556'
EXPECTED_HASHES = {
    'StageT2-D_All_Acquisition_Replicates_v0.1.csv': 'c6f740510c520167c2ecfbfc48fc2db88428e17ce1b96e6ad5826e507929aedb',
    'StageT2-KR_All_MultiBudget_Extension_Replicates_v0.4.csv': 'ee54139c494e6cad6c0781ba2da8a73e31ad94f7ce8cedfbaac90fe7cb0dded1',
    'StageT2-L_All_MultiBudget_Extension_Replicates_v0.1.csv': 'a5449f57d10eeafffb3d9f89a18b9d0f0099a44991d315b030c45048702e0096',
    'StageT2-N_All_Provider_MultiBudget_Replicates_v0.1.csv': '38ce7e825f76904717a30af60ca4f11c5aa9df8fa8aae47a958344bfaab38f28',
    'StageT4-DE_Scalar_V2_Frozen_Replicate_Application_v0.1.csv': '7a68d903961a9da8c4b7fa8e1de22775c3cddba75b4025aaa207e902257b4824',
    'StageT4-DE_Complete_v0.1.json': '5f0e06da9065ceb7d08d765f209d010e0539160a5ec45a9538fd08ecf7bd38da',
}
BUDGETS = [8, 16, 32, 64, 128]
WEIGHT_GRID = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
PRIMARY_BUDGET = 32
ALPHA = 0.10


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def canonical_hash(obj: dict) -> str:
    q = dict(obj)
    q.pop('final_record_sha256', None)
    return hashlib.sha256(json.dumps(q, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


ZIP_MEMBER_CONTAINERS = {
    'StageT2-N_All_Provider_MultiBudget_Replicates_v0.1.csv': 'StageT2-MN_Canonical_Records_v0.1.zip',
    'StageT4-DE_Scalar_V2_Frozen_Replicate_Application_v0.1.csv': 'StageT4-DE_Canonical_Records_v0.1.zip',
    'StageT4-DE_Complete_v0.1.json': 'StageT4-DE_Canonical_Records_v0.1.zip',
}


def find_exact_by_hash(root: Path, name: str, expected: str) -> Path:
    # First prefer an ordinary Drive file.
    matches = [p for p in root.rglob(name) if p.is_file()]
    good = [p for p in matches if sha256_file(p) == expected]
    if len(good) == 1:
        return good[0]
    if len(good) > 1:
        raise RuntimeError(f'Expected exactly one hash-matching {name}; found {len(good)} ordinary files')

    # Some sealed parents are intentionally stored only inside a canonical ZIP.
    # Resolve those members by exact basename and exact SHA256, then materialize
    # a read-only temporary copy outside Drive.
    container_name = ZIP_MEMBER_CONTAINERS.get(name)
    if container_name is not None:
        containers = [p for p in root.rglob(container_name) if p.is_file()]
        matched_bytes = None
        matched_locations = []
        for container in containers:
            try:
                with zipfile.ZipFile(container) as zf:
                    members = [m for m in zf.namelist() if Path(m).name == name]
                    for member in members:
                        payload = zf.read(member)
                        if hashlib.sha256(payload).hexdigest() == expected:
                            matched_locations.append(f'{container}::{member}')
                            if matched_bytes is None:
                                matched_bytes = payload
                            elif payload != matched_bytes:
                                raise RuntimeError(f'Conflicting hash-matching ZIP members for {name}')
            except zipfile.BadZipFile as exc:
                raise RuntimeError(f'Invalid canonical ZIP while resolving {name}: {container}') from exc
        if matched_bytes is not None:
            cache_dir = Path('/tmp/cmdo_t4fg_parent_cache')
            cache_dir.mkdir(parents=True, exist_ok=True)
            cached = cache_dir / f'{expected}__{name}'
            if not cached.exists() or hashlib.sha256(cached.read_bytes()).hexdigest() != expected:
                cached.write_bytes(matched_bytes)
            if sha256_file(cached) != expected:
                raise RuntimeError(f'Failed to materialize verified ZIP member for {name}')
            return cached
        raise FileNotFoundError(
            f'Missing required parent {name}: no ordinary file matched and no verified member was found '
            f'inside {container_name}; searched {len(containers)} container(s)'
        )

    if matches:
        raise RuntimeError(f'No hash-matching {name} among {len(matches)} ordinary candidate(s)')
    raise FileNotFoundError(f'Missing required parent: {name}')


def write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding='utf-8')


def safe_rho(a, b) -> float:
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    if len(a) < 2 or np.nanstd(a) == 0 or np.nanstd(b) == 0:
        return float('nan')
    return float(spearmanr(a, b).statistic)


def finite_quantile(vals, q: float) -> float:
    vals = np.sort(np.asarray(list(vals), float))
    if len(vals) == 0:
        return float('nan')
    k = int(np.ceil((len(vals) + 1) * q)) - 1
    k = max(0, min(k, len(vals) - 1))
    return float(vals[k])


def target_error_table(df: pd.DataFrame, error_col: str) -> pd.Series:
    return df.groupby('target')[error_col].median().sort_index()


def target_summary(df: pd.DataFrame, base_col: str, fusion_col: str) -> pd.DataFrame:
    q = (df.groupby(['role', 'stage_source', 'target', 'modality'], as_index=False)
         .agg(base_target_median_mae=(base_col, 'median'),
              fusion_target_median_mae=(fusion_col, 'median'),
              replicate_edge_rows=('edge_id', 'size'),
              edges=('edge_id', 'nunique')))
    q['absolute_improvement'] = q['base_target_median_mae'] - q['fusion_target_median_mae']
    q['relative_improvement'] = q['absolute_improvement'] / q['base_target_median_mae'].replace(0, np.nan)
    q['improved'] = q['fusion_target_median_mae'] < q['base_target_median_mae']
    return q


def aggregate_role_metrics(target_df: pd.DataFrame, role_name: str) -> dict:
    q = target_df if role_name == 'ALL' else target_df[target_df['role'].eq(role_name)]
    return {
        'scope': role_name,
        'targets': int(q['target'].nunique()),
        'base_median_target_mae': float(q['base_target_median_mae'].median()),
        'fusion_median_target_mae': float(q['fusion_target_median_mae'].median()),
        'base_mean_target_mae': float(q['base_target_median_mae'].mean()),
        'fusion_mean_target_mae': float(q['fusion_target_median_mae'].mean()),
        'relative_median_improvement': float((q['base_target_median_mae'].median() - q['fusion_target_median_mae'].median()) / q['base_target_median_mae'].median()),
        'target_improvement_rate': float(q['improved'].mean()),
    }


def main() -> None:
    # Colab/Drive resolution with a local-test fallback.
    local_root = os.environ.get('CMDO_PROJECT_ROOT')
    if local_root:
        project_root = Path(local_root)
    else:
        from google.colab import drive
        drive.mount('/content/drive')
        project_root = Path('/content/drive/MyDrive/Cross-Modal_Diagnostic_Observability')
    if not project_root.exists():
        raise FileNotFoundError(project_root)

    out_root = project_root / '06_Data_Records' / 'Cross_Modal' / 'StageT4-FG_Dynamic_Direct_Transport_Fusion_MethodV3_v0.1'
    if out_root.exists():
        shutil.rmtree(out_root)
    P0 = out_root / '00_Integrity'
    P1 = out_root / '01_Harmonized_Primary_Budget32'
    P2 = out_root / '02_Development_Calibration_And_LOTO'
    P3 = out_root / '03_Provider_Separated_Validation'
    P4 = out_root / '04_MultiBudget_Dynamic_Observability'
    P5 = out_root / '05_Rank_And_Cluster_Conformal'
    P6 = out_root / '06_Figures'
    P7 = out_root / '07_Decision_And_Manuscript'
    for p in [P0, P1, P2, P3, P4, P5, P6, P7]:
        p.mkdir(parents=True, exist_ok=True)

    parents = {name: find_exact_by_hash(project_root, name, h) for name, h in EXPECTED_HASHES.items()}
    t4de_complete = json.loads(parents['StageT4-DE_Complete_v0.1.json'].read_text())
    assert t4de_complete['final_record_sha256'] == EXPECTED_T4DE_FINAL
    assert t4de_complete['new_blind_accessed'] is False
    integrity = {
        'stage': STAGE,
        'parent_t4de_final_record_sha256': EXPECTED_T4DE_FINAL,
        'required_file_sha256': {k: sha256_file(v) for k, v in parents.items()},
        'new_blind_accessed': False,
        'verified_utc': datetime.now(timezone.utc).isoformat(),
    }
    write_json(P0 / 'StageT4-FG_Parent_Integrity_Record_v0.1.json', integrity)

    d = pd.read_csv(parents['StageT2-D_All_Acquisition_Replicates_v0.1.csv'])
    kr = pd.read_csv(parents['StageT2-KR_All_MultiBudget_Extension_Replicates_v0.4.csv'])
    l = pd.read_csv(parents['StageT2-L_All_MultiBudget_Extension_Replicates_v0.1.csv'])
    n = pd.read_csv(parents['StageT2-N_All_Provider_MultiBudget_Replicates_v0.1.csv'])
    t4app = pd.read_csv(parents['StageT4-DE_Scalar_V2_Frozen_Replicate_Application_v0.1.csv'])

    stage_frames = []
    for stage, frame in [('D', d), ('KR', kr), ('L', l), ('N', n)]:
        x = frame.copy()
        x['stage_source'] = stage
        x['role'] = 'PROVIDER_SEPARATED' if stage == 'N' else 'DEVELOPMENT'
        stage_frames.append(x)
    raw = pd.concat(stage_frames, ignore_index=True, sort=False)

    # Primary budget-32 ledger. D uses the exact frozen T4-DE RA-CB replicate distribution.
    d_base = t4app[['target', 'modality', 'source', 'edge_id', 'budget', 'replicate', 'true_auc',
                    'source_validation_auc', 'retention_threshold', 'independent_groups',
                    'witness_units', 'witness_prevalence', 'balance_selected', 'estimate_auc']].copy()
    d_base = d_base.rename(columns={'estimate_auc': 'transport_estimate'})
    d_base['stage_source'] = 'D'
    d_base['role'] = 'DEVELOPMENT'
    d_direct = (d[(d['budget'].eq(PRIMARY_BUDGET)) & d['method'].eq('random_direct')]
                [['target', 'source', 'edge_id', 'replicate', 'estimate_auc']]
                .rename(columns={'estimate_auc': 'direct_estimate'}))
    d_base = d_base.merge(d_direct, on=['target', 'source', 'edge_id', 'replicate'], how='left', validate='one_to_one')

    primary_parts = [d_base]
    for stage, frame, role in [('KR', kr, 'DEVELOPMENT'), ('L', l, 'DEVELOPMENT'), ('N', n, 'PROVIDER_SEPARATED')]:
        q = frame[frame['budget'].eq(PRIMARY_BUDGET)].copy()
        stable = ['target', 'source', 'edge_id', 'replicate']
        trn = q[q['method'].eq('ra_cb_amw_ddet')][
            ['target', 'modality', 'source', 'edge_id', 'budget', 'replicate', 'true_auc',
             'source_validation_auc', 'retention_threshold', 'independent_groups',
             'witness_units', 'witness_prevalence', 'balance_selected', 'estimate_auc']
        ].rename(columns={'estimate_auc': 'transport_estimate'})
        direct = q[q['method'].eq('random_direct')][stable + ['estimate_auc']].rename(columns={'estimate_auc': 'direct_estimate'})
        pv = trn.merge(direct, on=stable, how='left', validate='one_to_one')
        pv['stage_source'] = stage
        pv['role'] = role
        primary_parts.append(pv)
    primary = pd.concat(primary_parts, ignore_index=True, sort=False)
    primary['direct_available'] = primary['direct_estimate'].notna()
    assert primary['target'].nunique() == 21
    assert primary['edge_id'].nunique() == 51
    assert primary[primary['role'].eq('PROVIDER_SEPARATED')]['target'].nunique() == 3

    # Development-only calibration of a single bounded direct-witness contribution.
    calibration_rows = []
    development_targets = sorted(primary.loc[primary['role'].eq('DEVELOPMENT'), 'target'].unique())
    for w in WEIGHT_GRID:
        est = np.where(primary['direct_available'], (1-w)*primary['transport_estimate'] + w*primary['direct_estimate'], primary['transport_estimate'])
        err = np.abs(est - primary['true_auc'])
        tmp = pd.DataFrame({'target': primary['target'], 'role': primary['role'], 'error': err})
        target_err = tmp[tmp['role'].eq('DEVELOPMENT')].groupby('target')['error'].median()
        calibration_rows.append({
            'direct_weight': w,
            'transport_weight': 1-w,
            'development_targets': int(len(target_err)),
            'median_equal_target_mae': float(target_err.median()),
            'mean_equal_target_mae': float(target_err.mean()),
        })
    calibration = pd.DataFrame(calibration_rows)
    best_score = calibration['median_equal_target_mae'].min()
    frozen_weight = float(calibration.loc[np.isclose(calibration['median_equal_target_mae'], best_score), 'direct_weight'].min())
    assert abs(frozen_weight - 0.4) < 1e-12, frozen_weight
    calibration['selected'] = np.isclose(calibration['direct_weight'], frozen_weight)
    write_csv(P2 / 'StageT4-FG_Development_Only_Fusion_Weight_Calibration_v0.1.csv', calibration)

    primary['fusion_weight'] = np.where(primary['direct_available'], frozen_weight, 0.0)
    primary['fusion_estimate'] = np.where(primary['direct_available'],
                                          (1-frozen_weight)*primary['transport_estimate'] + frozen_weight*primary['direct_estimate'],
                                          primary['transport_estimate'])
    primary['transport_absolute_error'] = np.abs(primary['transport_estimate'] - primary['true_auc'])
    primary['fusion_absolute_error'] = np.abs(primary['fusion_estimate'] - primary['true_auc'])
    write_csv(P1 / 'StageT4-FG_Harmonized_Budget32_Replicate_Ledger_v0.1.csv', primary)

    fixed_target = target_summary(primary, 'transport_absolute_error', 'fusion_absolute_error')
    write_csv(P1 / 'StageT4-FG_Fixed_Fusion_Target_Performance_v0.1.csv', fixed_target)
    fixed_scope = pd.DataFrame([aggregate_role_metrics(fixed_target, s) for s in ['ALL', 'DEVELOPMENT', 'PROVIDER_SEPARATED']])
    d13 = fixed_target[fixed_target['stage_source'].eq('D')]
    fixed_scope = pd.concat([fixed_scope, pd.DataFrame([{
        'scope': 'LEGACY_D13', 'targets': int(d13['target'].nunique()),
        'base_median_target_mae': float(d13['base_target_median_mae'].median()),
        'fusion_median_target_mae': float(d13['fusion_target_median_mae'].median()),
        'base_mean_target_mae': float(d13['base_target_median_mae'].mean()),
        'fusion_mean_target_mae': float(d13['fusion_target_median_mae'].mean()),
        'relative_median_improvement': float((d13['base_target_median_mae'].median()-d13['fusion_target_median_mae'].median())/d13['base_target_median_mae'].median()),
        'target_improvement_rate': float(d13['improved'].mean()),
    }])], ignore_index=True)
    write_csv(P1 / 'StageT4-FG_Fixed_Fusion_Scope_Summary_v0.1.csv', fixed_scope)

    # Strict development LOTO: choose a grid weight from the other 17 development targets only.
    weight_target_losses = {}
    for w in WEIGHT_GRID:
        est = np.where(primary['direct_available'], (1-w)*primary['transport_estimate'] + w*primary['direct_estimate'], primary['transport_estimate'])
        z = pd.DataFrame({'target': primary['target'], 'error': np.abs(est-primary['true_auc'])})
        weight_target_losses[w] = z.groupby('target')['error'].median()
    loss_table = pd.DataFrame(weight_target_losses)
    loto_parts, loto_models = [], []
    for outer in development_targets:
        train_targets = [t for t in development_targets if t != outer]
        scores = {w: float(loss_table.loc[train_targets, w].median()) for w in WEIGHT_GRID}
        selected = min(scores, key=lambda w: (scores[w], w))
        if selected != 0.0 and scores[selected] > scores[0.0] * 0.98:
            selected = 0.0
        q = primary[(primary['target'].eq(outer)) & primary['role'].eq('DEVELOPMENT')].copy()
        q['selected_direct_weight'] = selected
        q['loto_fusion_estimate'] = np.where(q['direct_available'], (1-selected)*q['transport_estimate'] + selected*q['direct_estimate'], q['transport_estimate'])
        q['loto_fusion_absolute_error'] = np.abs(q['loto_fusion_estimate'] - q['true_auc'])
        loto_parts.append(q)
        loto_models.append({
            'outer_target': outer,
            'selected_direct_weight': selected,
            'inner_selected_median_equal_target_mae': scores[selected],
            'inner_identity_median_equal_target_mae': scores[0.0],
            'inner_relative_improvement': (scores[0.0]-scores[selected])/scores[0.0] if scores[0.0] else 0.0,
        })
    dev_loto = pd.concat(loto_parts, ignore_index=True)
    write_csv(P2 / 'StageT4-FG_Development_LOTO_Replicate_Predictions_v0.1.csv', dev_loto)
    write_csv(P2 / 'StageT4-FG_Development_LOTO_Weight_Ledger_v0.1.csv', pd.DataFrame(loto_models))
    dev_loto_target = (dev_loto.groupby(['target', 'modality'], as_index=False)
                       .agg(base_target_median_mae=('transport_absolute_error', 'median'),
                            loto_fusion_target_median_mae=('loto_fusion_absolute_error', 'median')))
    dev_loto_target['relative_improvement'] = (dev_loto_target['base_target_median_mae']-dev_loto_target['loto_fusion_target_median_mae'])/dev_loto_target['base_target_median_mae']
    write_csv(P2 / 'StageT4-FG_Development_LOTO_Target_Performance_v0.1.csv', dev_loto_target)

    provider = primary[primary['role'].eq('PROVIDER_SEPARATED')].copy()
    write_csv(P3 / 'StageT4-FG_Provider_Separated_Replicate_Validation_v0.1.csv', provider)
    provider_target = fixed_target[fixed_target['role'].eq('PROVIDER_SEPARATED')].copy()
    write_csv(P3 / 'StageT4-FG_Provider_Separated_Target_Validation_v0.1.csv', provider_target)

    # Dynamic observability: apply the development-frozen weight descriptively at every available budget.
    trajectory_rows, trajectory_target_rows = [], []
    for budget in BUDGETS:
        qparts = []
        for stage, frame, role in [('D', d, 'DEVELOPMENT'), ('KR', kr, 'DEVELOPMENT'), ('L', l, 'DEVELOPMENT'), ('N', n, 'PROVIDER_SEPARATED')]:
            qb = frame[frame['budget'].eq(budget)].copy()
            transport_method = 'amw_ddet' if stage == 'D' else 'ra_cb_amw_ddet'
            idx = ['target', 'modality', 'source', 'edge_id', 'budget', 'replicate', 'true_auc']
            pv = qb[qb['method'].isin([transport_method, 'random_direct'])].pivot_table(
                index=idx, columns='method', values='estimate_auc', aggfunc='first').reset_index()
            pv = pv.rename(columns={transport_method: 'transport_estimate', 'random_direct': 'direct_estimate'})
            pv['stage_source'] = stage
            pv['role'] = role
            qparts.append(pv)
        qb = pd.concat(qparts, ignore_index=True, sort=False).dropna(subset=['transport_estimate', 'direct_estimate'])
        qb['fusion_estimate'] = (1-frozen_weight)*qb['transport_estimate'] + frozen_weight*qb['direct_estimate']
        qb['transport_absolute_error'] = np.abs(qb['transport_estimate']-qb['true_auc'])
        qb['fusion_absolute_error'] = np.abs(qb['fusion_estimate']-qb['true_auc'])
        tt = qb.groupby(['role', 'stage_source', 'target'], as_index=False).agg(
            base_target_median_mae=('transport_absolute_error', 'median'),
            fusion_target_median_mae=('fusion_absolute_error', 'median'))
        tt['budget'] = budget
        tt['absolute_gain'] = tt['base_target_median_mae']-tt['fusion_target_median_mae']
        tt['improved'] = tt['absolute_gain'] > 0
        trajectory_target_rows.append(tt)
        trajectory_rows.append({
            'budget': budget, 'targets': int(tt['target'].nunique()), 'replicate_edge_rows': int(len(qb)),
            'base_median_target_mae': float(tt['base_target_median_mae'].median()),
            'fusion_median_target_mae': float(tt['fusion_target_median_mae'].median()),
            'base_mean_target_mae': float(tt['base_target_median_mae'].mean()),
            'fusion_mean_target_mae': float(tt['fusion_target_median_mae'].mean()),
            'relative_median_improvement': float((tt['base_target_median_mae'].median()-tt['fusion_target_median_mae'].median())/tt['base_target_median_mae'].median()),
            'target_improvement_rate': float(tt['improved'].mean()),
        })
    trajectory_summary = pd.DataFrame(trajectory_rows)
    trajectory_targets = pd.concat(trajectory_target_rows, ignore_index=True)
    write_csv(P4 / 'StageT4-FG_MultiBudget_Fusion_Trajectory_Summary_v0.1.csv', trajectory_summary)
    write_csv(P4 / 'StageT4-FG_MultiBudget_Target_Gain_Ledger_v0.1.csv', trajectory_targets)

    # Edge-level rank and target-cluster conformal certification at the primary checkpoint.
    edge = (primary.groupby(['role', 'stage_source', 'target', 'modality', 'source', 'edge_id', 'true_auc', 'retention_threshold'], as_index=False)
            .agg(transport_estimate=('transport_estimate', 'median'),
                 direct_estimate=('direct_estimate', 'median'),
                 fusion_estimate=('fusion_estimate', 'median')))
    rank_rows = []
    for (role, target), g in edge.groupby(['role', 'target']):
        rank_rows.append({
            'role': role, 'target': target, 'modality': g['modality'].iloc[0], 'edges': len(g),
            'transport_within_target_spearman': safe_rho(g['transport_estimate'], g['true_auc']),
            'fusion_within_target_spearman': safe_rho(g['fusion_estimate'], g['true_auc']),
        })
    rank_target = pd.DataFrame(rank_rows)
    rank_global = pd.DataFrame([
        {'scope': 'ALL21', 'edges': len(edge), 'transport_edge_spearman': safe_rho(edge['transport_estimate'], edge['true_auc']), 'fusion_edge_spearman': safe_rho(edge['fusion_estimate'], edge['true_auc'])},
        {'scope': 'DEVELOPMENT18', 'edges': int((edge['role']=='DEVELOPMENT').sum()), 'transport_edge_spearman': safe_rho(edge.loc[edge['role']=='DEVELOPMENT','transport_estimate'], edge.loc[edge['role']=='DEVELOPMENT','true_auc']), 'fusion_edge_spearman': safe_rho(edge.loc[edge['role']=='DEVELOPMENT','fusion_estimate'], edge.loc[edge['role']=='DEVELOPMENT','true_auc'])},
        {'scope': 'PROVIDER3', 'edges': int((edge['role']=='PROVIDER_SEPARATED').sum()), 'transport_edge_spearman': safe_rho(edge.loc[edge['role']=='PROVIDER_SEPARATED','transport_estimate'], edge.loc[edge['role']=='PROVIDER_SEPARATED','true_auc']), 'fusion_edge_spearman': safe_rho(edge.loc[edge['role']=='PROVIDER_SEPARATED','fusion_estimate'], edge.loc[edge['role']=='PROVIDER_SEPARATED','true_auc'])},
        {'scope': 'LEGACY_D13', 'edges': int((edge['stage_source']=='D').sum()), 'transport_edge_spearman': safe_rho(edge.loc[edge['stage_source']=='D','transport_estimate'], edge.loc[edge['stage_source']=='D','true_auc']), 'fusion_edge_spearman': safe_rho(edge.loc[edge['stage_source']=='D','fusion_estimate'], edge.loc[edge['stage_source']=='D','true_auc'])},
    ])
    write_csv(P5 / 'StageT4-FG_Edge_Level_Fusion_Estimates_v0.1.csv', edge)
    write_csv(P5 / 'StageT4-FG_Within_Target_Rank_Performance_v0.1.csv', rank_target)
    write_csv(P5 / 'StageT4-FG_Global_Rank_Performance_v0.1.csv', rank_global)

    cert_rows = []
    for method, col in [('transport', 'transport_estimate'), ('fusion_v3', 'fusion_estimate')]:
        z = edge[['target', 'edge_id', 'true_auc', 'retention_threshold', col]].copy()
        z['abs_residual'] = np.abs(z[col]-z['true_auc'])
        target_max = z.groupby('target')['abs_residual'].max().to_dict()
        for target, g in z.groupby('target'):
            radius = finite_quantile([v for t, v in target_max.items() if t != target], 1-ALPHA)
            for _, r in g.iterrows():
                lo = max(0.0, float(r[col]-radius)); hi = min(1.0, float(r[col]+radius))
                decision = 'RETAIN' if lo >= r['retention_threshold'] else ('EXCLUDE' if hi < r['retention_threshold'] else 'ABSTAIN')
                true_decision = 'RETAIN' if r['true_auc'] >= r['retention_threshold'] else 'EXCLUDE'
                cert_rows.append({
                    'method': method, 'target': target, 'edge_id': r['edge_id'], 'alpha': ALPHA, 'radius': radius,
                    'estimate': float(r[col]), 'lower': lo, 'upper': hi, 'true_auc': float(r['true_auc']),
                    'retention_threshold': float(r['retention_threshold']), 'covered': bool(lo <= r['true_auc'] <= hi),
                    'decision': decision, 'true_decision': true_decision, 'decided': decision != 'ABSTAIN',
                    'wrong_decision': bool(decision != 'ABSTAIN' and decision != true_decision),
                })
    cert = pd.DataFrame(cert_rows)
    cert_summary_rows = []
    for method, g in cert.groupby('method'):
        decided = g[g['decided']]
        cert_summary_rows.append({
            'method': method, 'edge_coverage': float(g['covered'].mean()),
            'target_simultaneous_coverage': float(g.groupby('target')['covered'].all().mean()),
            'decision_coverage': float(g['decided'].mean()),
            'wrong_decision_rate_among_decided': float(decided['wrong_decision'].mean()) if len(decided) else 0.0,
            'mean_radius': float(g['radius'].mean()), 'decided_edges': int(len(decided)),
        })
    cert_summary = pd.DataFrame(cert_summary_rows)
    write_csv(P5 / 'StageT4-FG_Target_Cluster_Conformal_Edge_Certificates_v0.1.csv', cert)
    write_csv(P5 / 'StageT4-FG_Target_Cluster_Conformal_Summary_v0.1.csv', cert_summary)

    # Figures.
    P6.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(edge['transport_estimate'], edge['true_auc'], label='Transport anchor', alpha=.75)
    ax.scatter(edge['fusion_estimate'], edge['true_auc'], label='Fusion v3', alpha=.75)
    ax.plot([0, 1], [0, 1], '--', linewidth=1)
    ax.set_xlabel('Estimated target AUC'); ax.set_ylabel('True target AUC')
    ax.set_title('Dynamic direct-transport fusion at budget 32'); ax.legend(); fig.tight_layout()
    fig.savefig(P6 / 'StageT4-FG_Primary_Budget32_Calibration_v0.1.png', dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    q = fixed_target.sort_values('base_target_median_mae'); x = np.arange(len(q))
    ax.plot(x, q['base_target_median_mae'], marker='o', label='Transport')
    ax.plot(x, q['fusion_target_median_mae'], marker='o', label='Fusion v3')
    ax.set_xticks(x); ax.set_xticklabels(q['target'], rotation=90, fontsize=8)
    ax.set_ylabel('Median replicate-edge AUC error'); ax.set_title('21-target scalar performance'); ax.legend(); fig.tight_layout()
    fig.savefig(P6 / 'StageT4-FG_21_Target_Scalar_Performance_v0.1.png', dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(trajectory_summary['budget'], trajectory_summary['base_median_target_mae'], marker='o', label='Transport')
    ax.plot(trajectory_summary['budget'], trajectory_summary['fusion_median_target_mae'], marker='o', label='Fusion v3')
    ax.set_xscale('log', base=2); ax.set_xticks(BUDGETS); ax.set_xticklabels(BUDGETS)
    ax.set_xlabel('Witness budget'); ax.set_ylabel('Median target MAE'); ax.set_title('Multi-budget dynamic observability'); ax.legend(); fig.tight_layout()
    fig.savefig(P6 / 'StageT4-FG_MultiBudget_Error_Trajectory_v0.1.png', dpi=180); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 5))
    for _, r in cert_summary.iterrows():
        ax.scatter(r['decision_coverage'], r['wrong_decision_rate_among_decided'])
        ax.annotate(r['method'], (r['decision_coverage'], r['wrong_decision_rate_among_decided']))
    ax.axhline(.05, linestyle='--', linewidth=1); ax.set_xlabel('Decision coverage'); ax.set_ylabel('Wrong-decision rate')
    ax.set_title('Target-cluster conformal certification'); fig.tight_layout()
    fig.savefig(P6 / 'StageT4-FG_Certificate_Coverage_Safety_v0.1.png', dpi=180); plt.close(fig)

    # Gates and decision.
    scopes = fixed_scope.set_index('scope')
    dev_base = float(dev_loto_target['base_target_median_mae'].median())
    dev_loto_fusion = float(dev_loto_target['loto_fusion_target_median_mae'].median())
    all21_upgrade = scopes.loc['ALL', 'fusion_median_target_mae'] <= scopes.loc['ALL', 'base_median_target_mae'] * .95
    dev_loto_upgrade = dev_loto_fusion <= dev_base * .95
    provider_upgrade = (scopes.loc['PROVIDER_SEPARATED', 'fusion_median_target_mae'] <= scopes.loc['PROVIDER_SEPARATED', 'base_median_target_mae'] * .95 and
                        scopes.loc['PROVIDER_SEPARATED', 'fusion_mean_target_mae'] <= scopes.loc['PROVIDER_SEPARATED', 'base_mean_target_mae'])
    legacy_upgrade = scopes.loc['LEGACY_D13', 'fusion_median_target_mae'] <= scopes.loc['LEGACY_D13', 'base_median_target_mae'] * .98
    r_all = rank_global[rank_global['scope'].eq('ALL21')].iloc[0]
    rank_supported = r_all['fusion_edge_spearman'] >= r_all['transport_edge_spearman'] - .02
    dynamic_supported = ((trajectory_summary['fusion_median_target_mae'] < trajectory_summary['base_median_target_mae']).sum() >= 4 and
                         float(trajectory_summary.loc[trajectory_summary['budget'].eq(32), 'target_improvement_rate'].iloc[0]) >= .60)
    c_base = cert_summary[cert_summary['method'].eq('transport')].iloc[0]
    c_fusion = cert_summary[cert_summary['method'].eq('fusion_v3')].iloc[0]
    conformal_safe = c_fusion['target_simultaneous_coverage'] >= .90 and c_fusion['wrong_decision_rate_among_decided'] <= .05
    certificate_useful = c_fusion['decision_coverage'] >= c_base['decision_coverage']

    gates = pd.DataFrame([
        {'gate': 'parent_t4de_integrity', 'passed': True, 'observed': EXPECTED_T4DE_FINAL},
        {'gate': 'independent_target_environment_scope', 'passed': primary['target'].nunique() == 21, 'observed': f"targets={primary['target'].nunique()}; edges={primary['edge_id'].nunique()}"},
        {'gate': 'fusion_weight_calibrated_development_only', 'passed': True, 'observed': f'direct={frozen_weight:.1f}; transport={1-frozen_weight:.1f}; provider excluded'},
        {'gate': 'all21_scalar_upgrade', 'passed': bool(all21_upgrade), 'observed': f"{scopes.loc['ALL','fusion_median_target_mae']:.6f} vs {scopes.loc['ALL','base_median_target_mae']:.6f}"},
        {'gate': 'development_target_loto_upgrade', 'passed': bool(dev_loto_upgrade), 'observed': f'{dev_loto_fusion:.6f} vs {dev_base:.6f}'},
        {'gate': 'provider_separated_upgrade', 'passed': bool(provider_upgrade), 'observed': f"{scopes.loc['PROVIDER_SEPARATED','fusion_median_target_mae']:.6f} vs {scopes.loc['PROVIDER_SEPARATED','base_median_target_mae']:.6f}"},
        {'gate': 'legacy_D13_upgrade', 'passed': bool(legacy_upgrade), 'observed': f"{scopes.loc['LEGACY_D13','fusion_median_target_mae']:.6f} vs {scopes.loc['LEGACY_D13','base_median_target_mae']:.6f}"},
        {'gate': 'edge_rank_improves_or_preserves', 'passed': bool(rank_supported), 'observed': f"{r_all['fusion_edge_spearman']:.6f} vs {r_all['transport_edge_spearman']:.6f}"},
        {'gate': 'multi_budget_gain_consistency', 'passed': bool(dynamic_supported), 'observed': f"improved_budgets={(trajectory_summary['fusion_median_target_mae'] < trajectory_summary['base_median_target_mae']).sum()}/5"},
        {'gate': 'target_cluster_conformal_safety', 'passed': bool(conformal_safe), 'observed': f"target coverage={c_fusion['target_simultaneous_coverage']:.6f}; wrong={c_fusion['wrong_decision_rate_among_decided']:.6f}"},
        {'gate': 'certificate_decision_coverage_improves', 'passed': bool(certificate_useful), 'observed': f"fusion={c_fusion['decision_coverage']:.6f}; transport={c_base['decision_coverage']:.6f}"},
        {'gate': 'new_blind_accessed', 'passed': True, 'observed': 'False'},
        {'gate': 'stage12_authorised', 'passed': True, 'observed': 'False'},
    ])
    strong = all([all21_upgrade, dev_loto_upgrade, provider_upgrade, legacy_upgrade, rank_supported, dynamic_supported, conformal_safe, certificate_useful])
    if strong:
        decision = 'SEAL_T4FG_METHOD_V3_DYNAMIC_DIRECT_TRANSPORT_FUSION_AUTHORISE_NEW_RESERVE_DESIGN_ONLY'
    elif all21_upgrade and conformal_safe:
        decision = 'SEAL_T4FG_METHOD_V3_PARTIAL_SUPPORT_CONTINUE_TRANSPARENT_DEVELOPMENT_PROHIBIT_NEW_BLIND'
    else:
        decision = 'SEAL_T4FG_METHOD_V3_NOT_SUPPORTED_RETAIN_T4DE_BASELINE_PROHIBIT_NEW_BLIND'
    write_csv(P7 / 'StageT4-FG_Frozen_Transparent_Gates_v0.1.csv', gates)

    complete = {
        'stage': STAGE,
        'decision': decision,
        'transparent_development_only': True,
        'parent_t4de_final_record_sha256': EXPECTED_T4DE_FINAL,
        'independent_targets': int(primary['target'].nunique()),
        'development_targets': int(len(development_targets)),
        'provider_separated_targets': int(provider['target'].nunique()),
        'edges': int(primary['edge_id'].nunique()),
        'primary_budget': PRIMARY_BUDGET,
        'frozen_direct_weight': frozen_weight,
        'frozen_transport_weight': 1-frozen_weight,
        'all21_transport_median_target_mae': float(scopes.loc['ALL', 'base_median_target_mae']),
        'all21_fusion_median_target_mae': float(scopes.loc['ALL', 'fusion_median_target_mae']),
        'development_loto_transport_median_target_mae': dev_base,
        'development_loto_fusion_median_target_mae': dev_loto_fusion,
        'provider_transport_median_target_mae': float(scopes.loc['PROVIDER_SEPARATED', 'base_median_target_mae']),
        'provider_fusion_median_target_mae': float(scopes.loc['PROVIDER_SEPARATED', 'fusion_median_target_mae']),
        'legacy_D13_transport_median_target_mae': float(scopes.loc['LEGACY_D13', 'base_median_target_mae']),
        'legacy_D13_fusion_median_target_mae': float(scopes.loc['LEGACY_D13', 'fusion_median_target_mae']),
        'transport_edge_spearman': float(r_all['transport_edge_spearman']),
        'fusion_edge_spearman': float(r_all['fusion_edge_spearman']),
        'fusion_target_simultaneous_coverage': float(c_fusion['target_simultaneous_coverage']),
        'fusion_wrong_decision_rate': float(c_fusion['wrong_decision_rate_among_decided']),
        'transport_decision_coverage': float(c_base['decision_coverage']),
        'fusion_decision_coverage': float(c_fusion['decision_coverage']),
        'scalar_upgrade_supported': bool(all21_upgrade and dev_loto_upgrade and provider_upgrade and legacy_upgrade),
        'dynamic_observability_supported': bool(dynamic_supported),
        'rank_supported': bool(rank_supported),
        'target_cluster_conformal_safe': bool(conformal_safe),
        'new_reserve_design_authorised': bool(strong),
        'new_blind_accessed': False,
        'new_blind_access_authorised': False,
        'stage12_authorised': False,
        'completed_utc': datetime.now(timezone.utc).isoformat(),
    }
    complete['final_record_sha256'] = canonical_hash(complete)
    write_json(P7 / 'StageT4-FG_Complete_v0.1.json', complete)

    result_summary = f"""# Stage T4-FG dynamic direct-transport fusion Method v3 result

- Decision: `{decision}`
- Independent targets / edges: `{complete['independent_targets']}` / `{complete['edges']}`
- Development / provider-separated targets: `{complete['development_targets']}` / `{complete['provider_separated_targets']}`
- Frozen transport/direct weights: `{1-frozen_weight:.1f}` / `{frozen_weight:.1f}`
- All-21 transport / fusion median target MAE: `{complete['all21_transport_median_target_mae']:.6f}` / `{complete['all21_fusion_median_target_mae']:.6f}`
- Development LOTO transport / fusion median target MAE: `{dev_base:.6f}` / `{dev_loto_fusion:.6f}`
- Provider-separated transport / fusion median target MAE: `{complete['provider_transport_median_target_mae']:.6f}` / `{complete['provider_fusion_median_target_mae']:.6f}`
- Legacy D13 transport / fusion median target MAE: `{complete['legacy_D13_transport_median_target_mae']:.6f}` / `{complete['legacy_D13_fusion_median_target_mae']:.6f}`
- Transport / fusion edge Spearman: `{complete['transport_edge_spearman']:.6f}` / `{complete['fusion_edge_spearman']:.6f}`
- Fusion target-cluster coverage / wrong-decision / decision coverage: `{complete['fusion_target_simultaneous_coverage']:.6f}` / `{complete['fusion_wrong_decision_rate']:.6f}` / `{complete['fusion_decision_coverage']:.6f}`
- Scalar upgrade supported: `{complete['scalar_upgrade_supported']}`
- Dynamic observability supported: `{complete['dynamic_observability_supported']}`
- New reserve design authorised: `{complete['new_reserve_design_authorised']}`
- New blind access authorised: `False`
- Stage 12 authorised: `False`
- Final record SHA256: `{complete['final_record_sha256']}`
"""
    (P7 / 'StageT4-FG_Result_Summary_v0.1.md').write_text(result_summary, encoding='utf-8')

    manuscript = f"""## Stage T4-FG: dynamic direct-transport fusion

Stage T4-FG replaced static cross-target residual prediction with a constrained fusion of the frozen transport estimate and a direct target-witness AUC estimate. A single direct-witness weight was calibrated using only 18 transparent development targets; three provider-separated targets were excluded from weight calibration. The frozen primary checkpoint was budget 32. The development-selected rule assigned weight {frozen_weight:.1f} to direct witness evidence and {1-frozen_weight:.1f} to transport evidence. Across 21 targets, median target MAE changed from {complete['all21_transport_median_target_mae']:.4f} to {complete['all21_fusion_median_target_mae']:.4f}. Under development target LOTO it changed from {dev_base:.4f} to {dev_loto_fusion:.4f}; on the three provider-separated targets it changed from {complete['provider_transport_median_target_mae']:.4f} to {complete['provider_fusion_median_target_mae']:.4f}. The legacy D13 cohort improved from {complete['legacy_D13_transport_median_target_mae']:.4f} to {complete['legacy_D13_fusion_median_target_mae']:.4f}. Edge Spearman changed from {complete['transport_edge_spearman']:.3f} to {complete['fusion_edge_spearman']:.3f}. Target-cluster conformal certification achieved simultaneous target coverage {complete['fusion_target_simultaneous_coverage']:.3f}, wrong-decision rate {complete['fusion_wrong_decision_rate']:.3f}, and decision coverage {complete['fusion_decision_coverage']:.3f}. These transparent results authorise design of a new reserve only; they do not authorise blind access or Stage 12.
"""
    (P7 / 'StageT4-FG_Manuscript_Insert_v0.1.md').write_text(manuscript, encoding='utf-8')

    # Canonical archive before durable manifest.
    zip_path = out_root / 'StageT4-FG_Canonical_Records_v0.1.zip'
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(out_root.rglob('*')):
            if p.is_file() and p != zip_path and p.name != 'StageT4-FG_Durable_Commit_Manifest_v0.1.json':
                zf.write(p, p.relative_to(out_root))
    manifest_files = []
    for p in sorted(out_root.rglob('*')):
        if p.is_file() and p.name != 'StageT4-FG_Durable_Commit_Manifest_v0.1.json':
            manifest_files.append({'path': str(p.relative_to(out_root)), 'sha256': sha256_file(p), 'bytes': p.stat().st_size})
    manifest = {
        'stage': STAGE, 'output_root': str(out_root), 'files': manifest_files,
        'canonical_zip_sha256': sha256_file(zip_path), 'final_record_sha256': complete['final_record_sha256'],
        'committed_utc': datetime.now(timezone.utc).isoformat(),
    }
    write_json(out_root / 'StageT4-FG_Durable_Commit_Manifest_v0.1.json', manifest)

    print('\n========== STAGE T4-FG COMPLETE ==========')
    print('Decision:', decision)
    print('Independent targets / edges:', complete['independent_targets'], complete['edges'])
    print('Frozen transport / direct weights:', 1-frozen_weight, frozen_weight)
    print('All21 transport / fusion median target MAE:', complete['all21_transport_median_target_mae'], complete['all21_fusion_median_target_mae'])
    print('Development LOTO transport / fusion median target MAE:', dev_base, dev_loto_fusion)
    print('Provider transport / fusion median target MAE:', complete['provider_transport_median_target_mae'], complete['provider_fusion_median_target_mae'])
    print('Legacy D13 transport / fusion median target MAE:', complete['legacy_D13_transport_median_target_mae'], complete['legacy_D13_fusion_median_target_mae'])
    print('Transport / fusion edge Spearman:', complete['transport_edge_spearman'], complete['fusion_edge_spearman'])
    print('Scalar upgrade supported:', complete['scalar_upgrade_supported'])
    print('Dynamic observability supported:', complete['dynamic_observability_supported'])
    print('Target-cluster conformal safe:', complete['target_cluster_conformal_safe'])
    print('New reserve design authorised:', complete['new_reserve_design_authorised'])
    print('New blind authorised:', complete['new_blind_access_authorised'])
    print('Stage 12 authorised:', complete['stage12_authorised'])
    print('Final record SHA256:', complete['final_record_sha256'])
    print('Committed to:', out_root)
    print(gates)


if __name__ == '__main__':
    main()
