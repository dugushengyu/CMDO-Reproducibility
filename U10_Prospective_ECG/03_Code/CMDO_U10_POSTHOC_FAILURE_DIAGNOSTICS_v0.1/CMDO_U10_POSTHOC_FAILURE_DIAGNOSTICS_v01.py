#!/usr/bin/env python3
"""
CMDO U10 POST-HOC FAILURE DIAGNOSTICS v0.1
===========================================

IMPORTANT:
- This is explicitly POST-HOC / exploratory.
- It does NOT alter the locked prospective verdict.
- It verifies the exact prospective result hashes before doing anything.
- It asks why the prospective mechanism gate failed.

Diagnostics:
1) Reconstruct target correctness on the exact frozen PRESEAL roster.
2) Reproduce the same audit replicates.
3) Compute budget-dependent evidence ratio Lambda = B^2 / V using:
   a) Monte-Carlo direct-estimator MSE from the locked prospective run,
   b) finite-population Bernoulli variance.
4) Compare observed adaptive weights to the fixed-weight safe boundary.
5) Test two EXPLORATORY cross-fit calibration variants:
   - FULLM: sensor fold estimates bias but V is scaled to the final full-budget estimator.
   - FULLM+FPC: same, additionally using finite-population correction.
6) Compute a non-deployable oracle fixed-weight benchmark.

No prospective gate is redefined.
"""

from __future__ import annotations
import argparse, hashlib, json, math, re, time
from pathlib import Path
import numpy as np
import pandas as pd

EXPECTED_SEAL = "efccafc32dc7778986296f6f7314488f6d08c45bdff2efdcb7f0918d36aec949"
EXPECTED_SPEC = "25b8810080a595494552789aca632c67db4b6af16b7f404920e38d9aee45a449"
EXPECTED_PROSPECTIVE_CSV = "685be9c1a86b4ace5c41d1ff4564fc2fedd65a8f15e9555fe6b3886a6d3c4df9"
EXPECTED_PROSPECTIVE_JSON = "dd2624ba443c69ef2dd276f40eefdff8dadb97612e9838c77b019a4e15c9b090"
AF_CODE = "164889003"
MASTER_SEED = 20260823
BUDGETS = [128,256,512,1024]
REPS = 200
CAP = 0.35

def sha256_file(p: Path, block=4*1024*1024):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(block), b""):
            h.update(b)
    return h.hexdigest()

def require(c,msg):
    if not c:
        raise RuntimeError(msg)

def parse_dx(p: Path):
    txt=p.read_text(encoding="utf-8-sig",errors="replace")
    m=re.search(r"(?im)^\s*#?\s*Dx\s*:\s*(.*?)\s*$",txt)
    if not m:
        return set()
    return set(re.findall(r"\d+",m.group(1)))

def seed_for(ds,m,r):
    s=f"{MASTER_SEED}|{ds}|{m}|{r}".encode()
    return int.from_bytes(hashlib.sha256(s).digest()[:8],"little")

def w_original(D,H,m):
    V=max(D*(1-D)/m,1e-8)
    return min(CAP, V/(V+(D-H)**2))

def w_fullm(Dsensor,H,m_full):
    # Exploratory: sensor fold estimates mismatch, but variance scale is the FINAL full-budget estimator.
    V=max(Dsensor*(1-Dsensor)/m_full,1e-8)
    return min(CAP, V/(V+(Dsensor-H)**2))

def w_fullm_fpc(Dsensor,H,m_full,N):
    fpc=max((N-m_full)/(N-1), 0.0)
    V=max(Dsensor*(1-Dsensor)/m_full*fpc,1e-8)
    return min(CAP, V/(V+(Dsensor-H)**2))

def load_z(root,ds,seal):
    score=root/"PRESEAL"/f"TARGET_SCORES_{ds}.csv"
    roster=root/"PRESEAL"/f"ROSTER_{ds}.csv"
    rec=[x for x in seal["target_artifacts"] if x["dataset"]==ds][0]
    require(sha256_file(score)==rec["score_sha256"],f"{ds} target score hash changed")
    require(sha256_file(roster)==rec["roster_sha256"],f"{ds} roster hash changed")
    df=pd.read_csv(score,dtype={"record_id":str})
    hm={p.stem:p for p in (root/"data"/ds).rglob("*.hea")}
    y=np.asarray([int(AF_CODE in parse_dx(hm[rid])) for rid in df.record_id],dtype=np.int8)
    pred=df.predicted_af.to_numpy(dtype=np.int8)
    return (pred==y).astype(float), y

def mse(a,theta):
    a=np.asarray(a,float)
    return float(np.mean((a-theta)**2))

def coupling_crossfit(DA,DB,wA,wB,theta,B):
    eA=DA-theta; eB=DB-theta
    q=.5*((1-wB)*eA + (1-wA)*eB)
    rr=.5*(wA+wB)*B
    return float(2*np.mean(q*rr))

def evaluate_exploratory(z,H,ds,m):
    N=len(z); theta=float(np.mean(z)); B=H-theta
    DA=[]; DB=[]; Dfull=[]
    wF=[]; wA_orig=[]; wB_orig=[]
    wA_full=[]; wB_full=[]; wA_fpc=[]; wB_fpc=[]
    cf_orig=[]; cf_full=[]; cf_fpc=[]
    for r in range(REPS):
        rng=np.random.default_rng(seed_for(ds,m,r))
        idx=rng.choice(N,size=m,replace=False)
        rng.shuffle(idx)
        h=m//2
        ia=idx[:h]; ib=idx[h:]
        d=float(np.mean(z[idx])); da=float(np.mean(z[ia])); db=float(np.mean(z[ib]))
        wf=w_original(d,H,m)
        wao=w_original(da,H,h); wbo=w_original(db,H,m-h)
        waf=w_fullm(da,H,m); wbf=w_fullm(db,H,m)
        wafpc=w_fullm_fpc(da,H,m,N); wbfpc=w_fullm_fpc(db,H,m,N)

        Dfull.append(d); DA.append(da); DB.append(db); wF.append(wf)
        wA_orig.append(wao); wB_orig.append(wbo)
        wA_full.append(waf); wB_full.append(wbf)
        wA_fpc.append(wafpc); wB_fpc.append(wbfpc)

        cf_orig.append(.5*((1-wbo)*da+wbo*H + (1-wao)*db+wao*H))
        cf_full.append(.5*((1-wbf)*da+wbf*H + (1-waf)*db+waf*H))
        cf_fpc.append(.5*((1-wbfpc)*da+wbfpc*H + (1-wafpc)*db+wafpc*H))

    Dfull=np.asarray(Dfull); DA=np.asarray(DA); DB=np.asarray(DB)
    wF=np.asarray(wF); wA_orig=np.asarray(wA_orig); wB_orig=np.asarray(wB_orig)
    wA_full=np.asarray(wA_full); wB_full=np.asarray(wB_full)
    wA_fpc=np.asarray(wA_fpc); wB_fpc=np.asarray(wB_fpc)
    cf_orig=np.asarray(cf_orig); cf_full=np.asarray(cf_full); cf_fpc=np.asarray(cf_fpc)

    V_mc=mse(Dfull,theta)
    fpc=(N-m)/(N-1)
    V_fpc=theta*(1-theta)/m*fpc
    lam_mc=(B*B/V_mc) if V_mc>0 else float("inf")
    lam_fpc=(B*B/V_fpc) if V_fpc>0 else float("inf")
    safe_mc=2/(1+lam_mc)
    opt_mc=1/(1+lam_mc)
    safe_fpc=2/(1+lam_fpc)
    opt_fpc=1/(1+lam_fpc)

    # Non-deployable oracle benchmark: fixed weight optimized for finite-population variance.
    w_oracle=min(CAP,opt_fpc)
    oracle=(1-w_oracle)*Dfull+w_oracle*H

    base=V_mc
    def gain(x):
        rx=mse(x,theta)
        return 100*(base-rx)/base,rx

    g_orig,r_orig=gain(cf_orig)
    g_full,r_full=gain(cf_full)
    g_fpc,r_fpc=gain(cf_fpc)
    g_oracle,r_oracle=gain(oracle)

    C_orig=coupling_crossfit(DA,DB,wA_orig,wB_orig,theta,B)
    C_full=coupling_crossfit(DA,DB,wA_full,wB_full,theta,B)
    C_fpc=coupling_crossfit(DA,DB,wA_fpc,wB_fpc,theta,B)

    return {
        "dataset":ds,"budget":m,"N":N,"theta":theta,"H":H,"B":B,
        "direct_mc_mse":V_mc,"finite_population_variance":V_fpc,
        "Lambda_mc":lam_mc,"Lambda_fpc":lam_fpc,
        "fixed_opt_weight_mc":opt_mc,"fixed_safe_max_mc":safe_mc,
        "fixed_opt_weight_fpc":opt_fpc,"fixed_safe_max_fpc":safe_fpc,
        "mean_w_shared_original":float(np.mean(wF)),
        "p_shared_weight_above_safe_fpc":float(np.mean(wF>safe_fpc)),
        "mean_sensor_weight_original":float(.5*(np.mean(wA_orig)+np.mean(wB_orig))),
        "mean_sensor_weight_fullm":float(.5*(np.mean(wA_full)+np.mean(wB_full))),
        "mean_sensor_weight_fullm_fpc":float(.5*(np.mean(wA_fpc)+np.mean(wB_fpc))),
        "prospective_crossfit_mse_recomputed":r_orig,
        "prospective_crossfit_gain_pct_recomputed":g_orig,
        "exploratory_fullm_crossfit_mse":r_full,
        "exploratory_fullm_crossfit_gain_pct":g_full,
        "exploratory_fullm_fpc_crossfit_mse":r_fpc,
        "exploratory_fullm_fpc_crossfit_gain_pct":g_fpc,
        "oracle_fixed_weight":w_oracle,
        "oracle_fixed_mse":r_oracle,
        "oracle_fixed_gain_pct":g_oracle,
        "coupling_crossfit_original":C_orig,
        "coupling_crossfit_fullm":C_full,
        "coupling_crossfit_fullm_fpc":C_fpc,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",required=True)
    args=ap.parse_args()
    root=Path(args.root).expanduser().resolve()

    sealp=root/"SEALS"/"U10_PREOUTCOME_SEAL.json"
    specp=root/"UNSEAL"/"U10_LOCKED_EVALUATION_SPEC_v0.1.json"
    csvp=root/"UNSEAL"/"RESULTS_v0.1"/"U10_TARGET_BUDGET_SUMMARY.csv"
    jsonp=root/"UNSEAL"/"RESULTS_v0.1"/"U10_PRIMARY_RESULT.json"

    checks={
        "preoutcome_seal":(sha256_file(sealp),EXPECTED_SEAL),
        "locked_spec":(sha256_file(specp),EXPECTED_SPEC),
        "prospective_csv":(sha256_file(csvp),EXPECTED_PROSPECTIVE_CSV),
        "prospective_json":(sha256_file(jsonp),EXPECTED_PROSPECTIVE_JSON),
    }
    for name,(actual,expected) in checks.items():
        require(actual==expected,f"{name} hash mismatch: expected {expected}, got {actual}")
        print(f"[verify] {name}: PASS {actual}")

    seal=json.loads(sealp.read_text(encoding="utf-8"))
    H=float(seal["source_development"]["historical_accuracy_H"])
    prospective=pd.read_csv(csvp)

    out=[]
    target_diag={}
    for ds in ("georgia","cpsc_2018"):
        z,y=load_z(root,ds,seal)
        target_diag[ds]={
            "N":int(len(z)),"AF_positive_n":int(y.sum()),
            "AF_prevalence":float(np.mean(y)),
            "theta_accuracy":float(np.mean(z)),
            "H":H,"B":float(H-np.mean(z))
        }
        for m in BUDGETS:
            rec=evaluate_exploratory(z,H,ds,m)
            # Exact prospective crossfit reproduction check against frozen CSV.
            ref=float(prospective.loc[(prospective.dataset==ds)&(prospective.budget==m),
                                      "crossfit_mse"].iloc[0])
            require(abs(rec["prospective_crossfit_mse_recomputed"]-ref)<1e-12,
                    f"Prospective crossfit reproduction mismatch {ds} m={m}")
            out.append(rec)

    df=pd.DataFrame(out)
    od=root/"UNSEAL"/"POSTHOC_FAILURE_DIAGNOSTICS_v0.1"
    od.mkdir(parents=True,exist_ok=True)
    table=od/"U10_POSTHOC_PHASE_DIAGNOSTICS.csv"
    df.to_csv(table,index=False,float_format="%.12g")

    # Compact verdict about the exploratory calibration hypothesis.
    summary={}
    for ds in ("georgia","cpsc_2018"):
        d=df[df.dataset==ds]
        orig=(d["prospective_crossfit_gain_pct_recomputed"]>0).sum()
        full=(d["exploratory_fullm_crossfit_gain_pct"]>0).sum()
        fpc=(d["exploratory_fullm_fpc_crossfit_gain_pct"]>0).sum()
        summary[ds]={
            "prospective_crossfit_positive_gain_budgets":int(orig),
            "fullm_calibrated_positive_gain_budgets":int(full),
            "fullm_fpc_calibrated_positive_gain_budgets":int(fpc),
            "median_gain_prospective_pct":float(d["prospective_crossfit_gain_pct_recomputed"].median()),
            "median_gain_fullm_pct":float(d["exploratory_fullm_crossfit_gain_pct"].median()),
            "median_gain_fullm_fpc_pct":float(d["exploratory_fullm_fpc_crossfit_gain_pct"].median()),
        }

    result={
        "schema":"CMDO_U10_POSTHOC_FAILURE_DIAGNOSTICS_v0.1",
        "status":"EXPLORATORY_POSTHOC_DO_NOT_REPLACE_PROSPECTIVE_VERDICT",
        "prospective_primary_verdict":"MECHANISM_NOT_CONFIRMED",
        "verified_hashes":{k:v[0] for k,v in checks.items()},
        "target_diagnostics":target_diag,
        "calibration_hypothesis_summary":summary,
        "table_sha256":sha256_file(table),
        "created_unix":time.time()
    }
    outj=od/"U10_POSTHOC_FAILURE_DIAGNOSTICS.json"
    outj.write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")

    print("="*96)
    print(" U10 POST-HOC FAILURE DIAGNOSTICS COMPLETE")
    print(" Prospective verdict remains: MECHANISM_NOT_CONFIRMED")
    print("="*96)
    cols=[
        "dataset","budget","Lambda_fpc","fixed_opt_weight_fpc","fixed_safe_max_fpc",
        "mean_w_shared_original","p_shared_weight_above_safe_fpc",
        "prospective_crossfit_gain_pct_recomputed",
        "exploratory_fullm_crossfit_gain_pct",
        "exploratory_fullm_fpc_crossfit_gain_pct",
        "oracle_fixed_gain_pct"
    ]
    print(df[cols].to_string(index=False))
    print()
    print("[exploratory calibration summary]")
    print(json.dumps(summary,indent=2))
    print(f"CSV : {table}")
    print(f"JSON: {outj}")
    print(f"CSV SHA256 : {sha256_file(table)}")
    print(f"JSON SHA256: {sha256_file(outj)}")
    print("="*96)

if __name__=="__main__":
    main()
