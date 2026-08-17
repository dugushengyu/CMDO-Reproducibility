#!/usr/bin/env python3
"""Audit the final sealed Figure 5/6 renderers against repository source records."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] if Path(__file__).resolve().parent.name == 'scripts' else Path(__file__).resolve().parent
FIG5 = ROOT / 'matlab/figures/main/Figure5.m'
FIG6 = ROOT / 'matlab/figures/main/Figure6.m'
F6SRC = ROOT / 'source_data/figure6_admissibility/CMDO_Admissibility_State_MSE_Audit.csv'
U8STATE = ROOT / 'source_data/figure6_u8_u9/U8_state.csv'
U8CYCLES = ROOT / 'source_data/figure6_u8_u9/U8_cycles.csv'
U8GATES = ROOT / 'source_data/figure6_u8_u9/U8_gates.csv'
U9ATARGETS = ROOT / 'source_data/figure6_u8_u9/U9A_targets.csv'
U9ASUMMARY = ROOT / 'source_data/figure6_u8_u9/U9A_summary.json'
U9BSTATES = ROOT / 'source_data/figure6_u8_u9/U9B_states.csv'
U9BSUMMARY = ROOT / 'source_data/figure6_u8_u9/U9B_summary.json'
DECOMP = ROOT / 'source_data/figure6_admissibility/U9B_external_composability_decomposition.csv'
SHARED = ROOT / 'source_data/figure6_admissibility/U9B_shared_audit_coupling.csv'
STRICT = ROOT / 'source_data/figure6_admissibility/U9B_strict_split_mechanistic_control.csv'
SEAL = ROOT / 'provenance/final_figure56_seal.json'
EXPECTED_STATE_SHA = '4ef09304a0dbb4110130b9543b05bd8a7d0f34f22dd0ecef1cb6ef758c6174c4'


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def matlab_block(text: str, name: str) -> str:
    # Numeric/string vector or matrix assignment terminated by ];
    m = re.search(rf'(?ms)^\s*{re.escape(name)}\s*=\s*\[\s*\.\.\.(.*?)\]\s*\'?(?:\s*;)', text)
    if not m:
        # also accept compact [ ... ]; forms without the leading continuation token
        m = re.search(rf'(?ms)^\s*{re.escape(name)}\s*=\s*\[(.*?)\]\s*\'?(?:\s*;)', text)
    if not m:
        raise AssertionError(f'cannot parse MATLAB assignment: {name}')
    return m.group(1)


def matlab_numbers(text: str, name: str) -> list[float]:
    block = matlab_block(text, name)
    return [float(x) for x in re.findall(r'(?<![A-Za-z_])[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?', block)]


def matlab_strings(text: str, name: str) -> list[str]:
    block = matlab_block(text, name)
    return re.findall(r'"([^"]+)"', block)


def matlab_scalar(text: str, name: str) -> float:
    m = re.search(
        rf'(?ms)^\s*{re.escape(name)}\s*=\s*(?:\.\.\.\s*)?([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)\s*;',
        text,
    )
    if not m:
        raise AssertionError(f'cannot parse MATLAB scalar: {name}')
    return float(m.group(1))


def assert_close(a: float, b: float, tol: float, label: str) -> None:
    if not math.isfinite(a) or not math.isfinite(b) or abs(a - b) > tol:
        raise AssertionError(f'{label}: {a!r} != {b!r} within {tol}')


def assert_vector_close(a: list[float], b: list[float], tol: float, label: str) -> None:
    if len(a) != len(b):
        raise AssertionError(f'{label}: length {len(a)} != {len(b)}')
    worst = max((abs(x-y) for x,y in zip(a,b)), default=0.0)
    if worst > tol:
        raise AssertionError(f'{label}: max absolute delta {worst} > {tol}')


def rank_average(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        r = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[order[k]] = r
        i = j
    return ranks


def pearson(x: list[float], y: list[float]) -> float:
    mx = sum(x)/len(x); my = sum(y)/len(y)
    num = sum((a-mx)*(b-my) for a,b in zip(x,y))
    denx = sum((a-mx)**2 for a in x); deny = sum((b-my)**2 for b in y)
    return num / math.sqrt(denx*deny)


def spearman(x: list[float], y: list[float]) -> float:
    return pearson(rank_average(x), rank_average(y))


def audit_figure6() -> dict:
    text = FIG6.read_text(encoding='utf-8')
    if 'readtable(' in text or 'readmatrix(' in text:
        raise AssertionError('Figure6 must be a sealed renderer with no runtime table read')
    if "CMDO_OUTPUT_ROOT" not in text or "'figures','main'" not in text:
        raise AssertionError('Figure6 does not honor reviewer output routing')
    if sha256(F6SRC) != EXPECTED_STATE_SHA:
        raise AssertionError('Figure6 state audit source SHA-256 mismatch')

    rr = rows(F6SRC)
    if len(rr) != 185:
        raise AssertionError(f'Figure6 source must contain 185 states, found {len(rr)}')
    counts = {s: sum(r['stage'] == s for r in rr) for s in ('U6','U7','U8','U9A','U9B')}
    if counts != {'U6':80,'U7':80,'U8':12,'U9A':9,'U9B':4}:
        raise AssertionError(f'Figure6 stage counts mismatch: {counts}')

    stage = [r['stage'] for r in rr]
    lam = [float(r['lambda_ean']) for r in rr]
    weight = [float(r['mean_weight']) for r in rr]
    observed = [float(r['mse_gain_pct']) for r in rr]
    psi = [float(r['psi_meanweight']) for r in rr]
    ratio = [float(r['scalar_risk_ratio_at_meanweight']) for r in rr]

    if matlab_strings(text, 'stage_embedded') != stage:
        raise AssertionError('Figure6 embedded stage vector differs from audit source')
    assert_vector_close(matlab_numbers(text,'lambda_embedded'), lam, 1e-12, 'Figure6 Lambda embedding')
    assert_vector_close(matlab_numbers(text,'weight_embedded'), weight, 1e-14, 'Figure6 weight embedding')
    assert_vector_close(matlab_numbers(text,'gain_embedded'), observed, 1e-13, 'Figure6 observed-gain embedding')
    assert_vector_close(matlab_numbers(text,'psi_embedded'), psi, 1e-14, 'Figure6 Psi embedding')
    assert_vector_close(matlab_numbers(text,'ratio_embedded'), ratio, 1e-14, 'Figure6 scalar-ratio embedding')

    psi_re = [w*(1+l)/2 for w,l in zip(weight,lam)]
    ratio_re = [(1-w)**2 + l*w*w for w,l in zip(weight,lam)]
    max_psi = max(abs(a-b) for a,b in zip(psi,psi_re))
    max_ratio = max(abs(a-b) for a,b in zip(ratio,ratio_re))
    if max_psi >= 1e-12 or max_ratio >= 1e-12:
        raise AssertionError(f'Figure6 scalar identity failure: psi={max_psi}, ratio={max_ratio}')

    theory = [100*(1-r) for r in ratio_re]
    rho_lambda = spearman([math.log10(x) for x in lam], observed)
    rho_theory = spearman(theory, observed)
    assert_close(rho_lambda, -0.5610382472233805, 5e-12, 'rho(log10 Lambda, observed)')
    assert_close(rho_theory, 0.5875990296046397, 5e-12, 'rho(theory, observed)')

    dec = rows(DECOMP)
    if len(dec) != 4:
        raise AssertionError('U9B decomposition must contain four budgets')
    for r in dec:
        closure = float(r['scalar_gain_pct']) - float(r['observed_gain_pct']) - float(r['xi_downward_pp'])
        assert_close(closure, 0.0, 1e-12, f"U9B Xi closure budget {r['budget']}")

    sh = rows(SHARED); ss = rows(STRICT)
    if len(sh) != 4 or len(ss) != 8:
        raise AssertionError('strict-split audit source dimensions are wrong')
    mean_shared_corr = sum(abs(float(r['corr_w_A'])) for r in sh)/4
    mean_shared_xi = sum(abs(float(r['xi_cross_pp'])) for r in sh)/4
    mean_split_corr = sum(abs(float(r['corr_w_A'])) for r in ss)/8
    mean_split_xi = sum(abs(float(r['xi_cross_pp'])) for r in ss)/8
    assert_close(mean_shared_corr,0.9405,1e-12,'mean shared |corr|')
    assert_close(mean_split_corr,0.05575,1e-12,'mean split |corr|')
    assert_close(mean_shared_xi,9.44525,1e-12,'mean shared |Xi_cross|')
    assert_close(mean_split_xi,2.18575,1e-12,'mean split |Xi_cross|')

    return {
        'state_sha256': sha256(F6SRC),
        'state_count': len(rr),
        'stage_counts': counts,
        'max_psi_reconstruction_delta': max_psi,
        'max_scalar_ratio_reconstruction_delta': max_ratio,
        'rho_log10_lambda_observed': rho_lambda,
        'rho_scalar_prediction_observed': rho_theory,
        'mean_shared_abs_corr': mean_shared_corr,
        'mean_split_abs_corr': mean_split_corr,
        'mean_shared_abs_xi_cross_pp': mean_shared_xi,
        'mean_split_abs_xi_cross_pp': mean_split_xi,
    }


def audit_figure5() -> dict:
    text = FIG5.read_text(encoding='utf-8')
    if 'readtable(' in text or 'readmatrix(' in text:
        raise AssertionError('Figure5 must be a sealed renderer with no runtime table read')
    if "CMDO_OUTPUT_ROOT" not in text or "'figures','main'" not in text:
        raise AssertionError('Figure5 does not honor reviewer output routing')

    u8 = rows(U8STATE)
    cycle_order = ['NHANES_2015_2016','NHANES_2017_2018','NHANES_2021_2023']
    budgets = [128,256,512,1024]
    def u8_matrix(field: str) -> list[float]:
        out=[]
        for cyc in cycle_order:
            for b in budgets:
                rec = next(r for r in u8 if r['cycle']==cyc and int(r['budget'])==b)
                out.append(float(rec[field]))
        return out
    assert_vector_close(matlab_numbers(text,'u8_direct'),u8_matrix('direct_mae'),1e-15,'Figure5 U8 direct')
    assert_vector_close(matlab_numbers(text,'u8_observer'),u8_matrix('observer_mae'),1e-15,'Figure5 U8 observer')
    assert_vector_close(matlab_numbers(text,'u8_mean_weight'),u8_matrix('mean_weight'),1e-15,'Figure5 U8 weights')

    cyc = {r['cycle']:r for r in rows(U8CYCLES)}
    assert_vector_close(matlab_numbers(text,'u8_cycle_bias'),[float(cyc[c]['historical_accuracy_bias']) for c in cycle_order],1e-15,'Figure5 U8 cycle bias')
    assert_vector_close(matlab_numbers(text,'u8_cycle_weight'),[float(cyc[c]['mean_weight']) for c in cycle_order],1e-15,'Figure5 U8 cycle weight')

    gates = {r['gate']:r for r in rows(U8GATES)}
    assert_close(matlab_scalar(text,'u8_mean_coverage'),float(gates['mean_simultaneous_coverage']['observed']),5e-13,'U8 mean coverage')
    assert_close(matlab_scalar(text,'u8_min_coverage'),float(gates['minimum_state_simultaneous_coverage']['observed']),1e-15,'U8 min coverage')
    assert_close(matlab_scalar(text,'u8_worst_state_regret'),float(gates['worst_state_regret']['observed']),5e-16,'U8 worst regret')
    assert_close(matlab_scalar(text,'u8_slope'),float(gates['direct_root_budget_slope']['observed']),5e-13,'U8 slope')

    targets = {r['target']:r for r in rows(U9ATARGETS)}
    target_order = ['hungary','switzerland','va_long_beach']
    assert_vector_close(matlab_numbers(text,'u9a_gain_pct'),[100*float(targets[x]['relative_gain']) for x in target_order],1e-13,'Figure5 U9A target gains')
    u9as = json.loads(U9ASUMMARY.read_text(encoding='utf-8'))
    assert_close(matlab_scalar(text,'u9a_pooled_gain_pct'),100*float(u9as['pooled_relative_gain']),1e-13,'U9A pooled gain')
    assert_close(matlab_scalar(text,'u9a_mean_weight'),float(u9as['mean_weight']),1e-15,'U9A mean weight')
    assert_close(matlab_scalar(text,'u9a_worst_state_regret'),float(u9as['worst_state_regret']),1e-15,'U9A worst regret')

    u9b = sorted(rows(U9BSTATES), key=lambda r:int(r['budget']))
    assert_vector_close(matlab_numbers(text,'u9b_direct'),[float(r['direct_mae']) for r in u9b],1e-15,'Figure5 U9B direct')
    assert_vector_close(matlab_numbers(text,'u9b_observer'),[float(r['observer_mae']) for r in u9b],1e-15,'Figure5 U9B observer')
    assert_vector_close(matlab_numbers(text,'u9b_weight'),[float(r['mean_weight']) for r in u9b],1e-15,'Figure5 U9B weights')
    assert_vector_close(matlab_numbers(text,'u9b_gain_pct_by_budget'),[100*float(r['relative_gain']) for r in u9b],1e-13,'Figure5 U9B gains')
    u9bs = json.loads(U9BSUMMARY.read_text(encoding='utf-8'))
    assert_close(matlab_scalar(text,'u9b_source_prevalence'),float(u9bs['source']['system_A_prevalence']),1e-15,'U9B source prevalence')
    assert_close(matlab_scalar(text,'u9b_target_prevalence'),float(u9bs['target_prevalence']),1e-15,'U9B target prevalence')
    assert_close(matlab_scalar(text,'u9b_historical_auc'),float(u9bs['source']['historical_auc']),1e-15,'U9B historical AUC')
    assert_close(matlab_scalar(text,'u9b_target_auc'),float(u9bs['source']['target_auc']),1e-15,'U9B target AUC')
    assert_close(matlab_scalar(text,'u9b_historical_accuracy'),float(u9bs['historical_accuracy']),1e-15,'U9B historical accuracy')
    assert_close(matlab_scalar(text,'u9b_target_accuracy'),float(u9bs['true_accuracy']),1e-15,'U9B target accuracy')
    assert_close(matlab_scalar(text,'u9b_pooled_gain_pct'),100*float(u9bs['relative_gain']),1e-13,'U9B pooled gain')
    assert_close(matlab_scalar(text,'u9b_worst_budget_mean_regret'),float(u9bs['worst_state_regret']),1e-15,'U9B worst regret')
    assert_close(matlab_scalar(text,'u9b_mean_coverage'),float(u9bs['mean_simultaneous_coverage']),1e-15,'U9B mean coverage')
    assert_close(matlab_scalar(text,'u9b_min_coverage'),float(u9bs['minimum_simultaneous_coverage']),1e-15,'U9B min coverage')
    assert_close(matlab_scalar(text,'u9b_slope'),float(u9bs['direct_root_budget_slope']),1e-15,'U9B slope')

    return {
        'u8_states': len(u8),
        'u9a_targets': len(targets),
        'u9b_states': len(u9b),
        'u8_pooled_gain_pct': matlab_scalar(text,'u8_pooled_gain_pct'),
        'u9a_pooled_gain_pct': matlab_scalar(text,'u9a_pooled_gain_pct'),
        'u9b_pooled_gain_pct': matlab_scalar(text,'u9b_pooled_gain_pct'),
    }


def audit_seal() -> dict:
    seal = json.loads(SEAL.read_text(encoding='utf-8'))
    for key,path in [('figure5',FIG5),('figure6',FIG6),('admissibility_state_table',F6SRC)]:
        rec = seal['files'][key]
        actual = sha256(path)
        if actual != rec['sha256']:
            raise AssertionError(f"seal mismatch for {key}: {actual} != {rec['sha256']}")
        if path.stat().st_size != int(rec['size_bytes']):
            raise AssertionError(f'seal size mismatch for {key}')
    return {'seal_version': seal['seal_version'], 'classification': seal['classification']}


def main() -> int:
    required=[FIG5,FIG6,F6SRC,U8STATE,U8CYCLES,U8GATES,U9ATARGETS,U9ASUMMARY,U9BSTATES,U9BSUMMARY,DECOMP,SHARED,STRICT,SEAL]
    missing=[str(p.relative_to(ROOT)) for p in required if not p.is_file()]
    if missing:
        print('FINAL FIGURE 5/6 AUDIT FAIL: missing files')
        for p in missing: print(' -',p)
        return 1
    try:
        report={'figure5':audit_figure5(),'figure6':audit_figure6(),'seal':audit_seal()}
    except Exception as exc:
        print(f'FINAL FIGURE 5/6 AUDIT FAIL: {type(exc).__name__}: {exc}')
        return 1
    print(json.dumps(report,indent=2,sort_keys=True))
    print('=== CMDO FINAL FIGURE 5/6 AUDIT PASS ===')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
