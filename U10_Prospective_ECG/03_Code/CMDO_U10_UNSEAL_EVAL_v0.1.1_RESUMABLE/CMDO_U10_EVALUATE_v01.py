#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, time
from pathlib import Path

import numpy as np
import pandas as pd

EXPECTED_SEAL_SHA = "efccafc32dc7778986296f6f7314488f6d08c45bdff2efdcb7f0918d36aec949"
EXPECTED_SPEC_SHA = "25b8810080a595494552789aca632c67db4b6af16b7f404920e38d9aee45a449"
AF_CODE = "164889003"

def sha256_file(path: Path, block=4*1024*1024):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(block), b""):
            h.update(b)
    return h.hexdigest()

def require(c,msg):
    if not c:
        raise RuntimeError(msg)

def parse_dx(header: Path):
    import re
    txt=header.read_text(encoding="utf-8-sig",errors="replace")
    m=re.search(r"(?im)^\s*#?\s*Dx\s*:\s*(.*?)\s*$",txt)
    if not m:
        return set()
    return set(re.findall(r"\d+",m.group(1)))

def derived_seed(master,dataset,budget,rep):
    s=f"{master}|{dataset}|{budget}|{rep}".encode()
    return int.from_bytes(hashlib.sha256(s).digest()[:8],"little",signed=False)

def weight_rule(D,H,m):
    V=max(D*(1-D)/m,1e-8)
    return min(0.35, V/(V+(D-H)**2))

def load_target(root: Path, ds: str, seal: dict):
    score_path=root/"PRESEAL"/f"TARGET_SCORES_{ds}.csv"
    roster_path=root/"PRESEAL"/f"ROSTER_{ds}.csv"
    require(score_path.exists(),f"Missing {score_path}")
    require(roster_path.exists(),f"Missing {roster_path}")

    rec=[x for x in seal["target_artifacts"] if x["dataset"]==ds][0]
    require(sha256_file(score_path)==rec["score_sha256"],f"Frozen score hash mismatch: {ds}")
    require(sha256_file(roster_path)==rec["roster_sha256"],f"Frozen roster hash mismatch: {ds}")

    df=pd.read_csv(score_path,dtype={"record_id":str})
    require(list(df.columns)==["record_id","score_af","predicted_af"],f"Unexpected score columns: {ds}")
    header_map={p.stem:p for p in (root/"data"/ds).rglob("*.hea")}
    expected_total={"georgia":10344,"cpsc_2018":6877}[ds]
    require(len(header_map)==expected_total,f"{ds}: expected {expected_total} headers after unseal, found {len(header_map)}")
    require(df["record_id"].is_unique,f"Duplicate frozen record IDs: {ds}")
    missing=[rid for rid in df["record_id"] if rid not in header_map]
    require(not missing,f"{ds}: {len(missing)} eligible records lack headers")

    y=np.array([int(AF_CODE in parse_dx(header_map[rid])) for rid in df["record_id"]],dtype=np.int8)
    pred=df["predicted_af"].to_numpy(dtype=np.int8)
    z=(pred==y).astype(np.float64)
    return df["record_id"].to_numpy(str),y,pred,z

def summarize_arm(est,theta):
    err=est-theta
    return {
        "mse":float(np.mean(err**2)),
        "mae":float(np.mean(np.abs(err))),
        "bias":float(np.mean(err)),
    }

def rel_gain(base,other):
    return float(100*(base-other)/base) if base>0 else float("nan")

def eval_budget(z,theta,H,ds,m,reps,master):
    n=len(z)
    require(m<=n,f"budget {m} > n={n}")
    Df=[]; DA=[]; DB=[]; wF=[]; wA=[]; wB=[]
    shared=[]; ab=[]; ba=[]; cf=[]

    for r in range(reps):
        rng=np.random.default_rng(derived_seed(master,ds,m,r))
        idx=rng.choice(n,size=m,replace=False)
        rng.shuffle(idx)
        h=m//2
        ia=idx[:h]; ib=idx[h:]
        d=float(np.mean(z[idx]))
        da=float(np.mean(z[ia]))
        db=float(np.mean(z[ib]))
        wf=weight_rule(d,H,m)
        wa=weight_rule(da,H,h)
        wb=weight_rule(db,H,m-h)
        a_shared=(1-wf)*d+wf*H
        a_ab=(1-wa)*db+wa*H
        a_ba=(1-wb)*da+wb*H
        a_cf=0.5*(a_ab+a_ba)

        Df.append(d); DA.append(da); DB.append(db)
        wF.append(wf); wA.append(wa); wB.append(wb)
        shared.append(a_shared); ab.append(a_ab); ba.append(a_ba); cf.append(a_cf)

    Df=np.asarray(Df); DA=np.asarray(DA); DB=np.asarray(DB)
    wF=np.asarray(wF); wA=np.asarray(wA); wB=np.asarray(wB)
    shared=np.asarray(shared); ab=np.asarray(ab); ba=np.asarray(ba); cf=np.asarray(cf)

    eF=Df-theta; eA=DA-theta; eB=DB-theta
    B=H-theta

    direct=summarize_arm(Df,theta)
    halfA=summarize_arm(DA,theta); halfB=summarize_arm(DB,theta)
    sh=summarize_arm(shared,theta)
    sab=summarize_arm(ab,theta); sba=summarize_arm(ba,theta)
    scf=summarize_arm(cf,theta)

    C_shared=float(2*B*np.mean(wF*(1-wF)*eF))
    C_ab=float(2*B*np.mean(wA*(1-wA)*eB))
    C_ba=float(2*B*np.mean(wB*(1-wB)*eA))
    C_strict=float(0.5*(C_ab+C_ba))

    q=0.5*((1-wB)*eA+(1-wA)*eB)
    rr=0.5*(wA+wB)*B
    C_cf=float(2*np.mean(q*rr))

    sh_noise=float(np.mean(((1-wF)*eF)**2))
    sh_bias=float(np.mean((wF*B)**2))
    sh_sum=sh_noise+sh_bias+C_shared

    cf_noise=float(np.mean(q**2))
    cf_bias=float(np.mean(rr**2))
    cf_sum=cf_noise+cf_bias+C_cf

    require(abs(sh_sum-sh["mse"])<1e-12,f"Shared exact decomposition failed {ds} m={m}")
    require(abs(cf_sum-scf["mse"])<1e-12,f"Crossfit exact decomposition failed {ds} m={m}")

    def reduction(C):
        if abs(C_shared)<1e-18:
            return float("nan")
        return float(100*(abs(C_shared)-abs(C))/abs(C_shared))

    return {
        "dataset":ds,"budget":m,"n_target":n,"theta_target_accuracy":theta,
        "H_historical_accuracy":H,"B_H_minus_theta":B,
        "direct_full_mse":direct["mse"],"direct_full_mae":direct["mae"],"direct_full_bias":direct["bias"],
        "half_direct_mean_mse":0.5*(halfA["mse"]+halfB["mse"]),
        "shared_mse":sh["mse"],"shared_mae":sh["mae"],"shared_bias":sh["bias"],
        "strict_A_to_B_mse":sab["mse"],"strict_B_to_A_mse":sba["mse"],
        "strict_mean_mse":0.5*(sab["mse"]+sba["mse"]),
        "crossfit_mse":scf["mse"],"crossfit_mae":scf["mae"],"crossfit_bias":scf["bias"],
        "shared_gain_vs_full_direct_pct":rel_gain(direct["mse"],sh["mse"]),
        "strict_mean_gain_vs_full_direct_pct":rel_gain(direct["mse"],0.5*(sab["mse"]+sba["mse"])),
        "crossfit_gain_vs_full_direct_pct":rel_gain(direct["mse"],scf["mse"]),
        "shared_coupling":C_shared,
        "strict_A_to_B_coupling":C_ab,"strict_B_to_A_coupling":C_ba,
        "strict_mean_coupling":C_strict,"crossfit_coupling":C_cf,
        "strict_abs_coupling_reduction_pct":reduction(C_strict),
        "crossfit_abs_coupling_reduction_pct":reduction(C_cf),
        "mean_w_shared":float(np.mean(wF)),"mean_w_A":float(np.mean(wA)),"mean_w_B":float(np.mean(wB)),
        "shared_exact_noise_term":sh_noise,"shared_exact_bias_term":sh_bias,
        "crossfit_exact_noise_term":cf_noise,"crossfit_exact_bias_term":cf_bias,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",required=True)
    ap.add_argument("--spec",required=True)
    args=ap.parse_args()

    root=Path(args.root).expanduser().resolve()
    spec_path=Path(args.spec).expanduser().resolve()
    seal_path=root/"SEALS"/"U10_PREOUTCOME_SEAL.json"
    marker=root/"UNSEAL"/"U10_UNSEAL_STARTED.json"

    require(seal_path.exists(),"Missing pre-outcome seal")
    actual_seal=sha256_file(seal_path)
    require(actual_seal==EXPECTED_SEAL_SHA,
            f"Seal hash mismatch. Expected {EXPECTED_SEAL_SHA}, got {actual_seal}")
    require(spec_path.exists(),"Missing locked evaluation spec")
    actual_spec=sha256_file(spec_path)
    require(actual_spec==EXPECTED_SPEC_SHA,
            f"Evaluation spec hash mismatch. Expected {EXPECTED_SPEC_SHA}, got {actual_spec}")
    require(marker.exists(),"Missing one-shot UNSEAL_STARTED marker")

    seal=json.loads(seal_path.read_text(encoding="utf-8"))
    spec=json.loads(spec_path.read_text(encoding="utf-8"))
    H=float(seal["source_development"]["historical_accuracy_H"])

    outdir=root/"UNSEAL"/"RESULTS_v0.1"
    outdir.mkdir(parents=True,exist_ok=True)

    rows=[]
    target_summary={}
    for ds in spec["targets"]:
        ids,y,pred,z=load_target(root,ds,seal)
        theta=float(np.mean(z))
        prevalence=float(np.mean(y))
        target_summary[ds]={
            "eligible_n":int(len(y)),
            "af_positive_n":int(y.sum()),
            "af_prevalence":prevalence,
            "target_accuracy_theta":theta,
            "historical_H":H,
            "B_H_minus_theta":float(H-theta),
        }
        print(f"[target] {ds} n={len(y)} AF={int(y.sum())} prev={prevalence:.6f} theta={theta:.6f} H={H:.6f} B={H-theta:+.6f}")
        for m in spec["audit_design"]["budgets"]:
            rec=eval_budget(z,theta,H,ds,int(m),
                            int(spec["audit_design"]["replicates_per_budget"]),
                            int(spec["audit_design"]["master_seed"]))
            rows.append(rec)
            print("[budget]",ds,m,
                  f"gain_shared={rec['shared_gain_vs_full_direct_pct']:+.2f}%",
                  f"gain_strict={rec['strict_mean_gain_vs_full_direct_pct']:+.2f}%",
                  f"gain_crossfit={rec['crossfit_gain_vs_full_direct_pct']:+.2f}%",
                  f"Cshared={rec['shared_coupling']:+.3e}",
                  f"Cstrict={rec['strict_mean_coupling']:+.3e}",
                  f"Ccf={rec['crossfit_coupling']:+.3e}")

    df=pd.DataFrame(rows)
    csv_path=outdir/"U10_TARGET_BUDGET_SUMMARY.csv"
    df.to_csv(csv_path,index=False,float_format="%.12g")

    verdicts={}
    for ds in spec["targets"]:
        d=df[df.dataset==ds].copy()
        strict_ok=int((d["strict_abs_coupling_reduction_pct"]>0).sum())
        cf_ok=int((d["crossfit_abs_coupling_reduction_pct"]>0).sum())
        verdicts[ds]={
            "strict_budgets_reduced_abs_coupling":strict_ok,
            "crossfit_budgets_reduced_abs_coupling":cf_ok,
            "per_target_gate_pass":bool(strict_ok>=3 and cf_ok>=3),
        }

    pooled_strict_median=float(np.nanmedian(df["strict_abs_coupling_reduction_pct"]))
    pooled_cf_median=float(np.nanmedian(df["crossfit_abs_coupling_reduction_pct"]))
    pooled_ok=(pooled_strict_median>0) and (pooled_cf_median>0)
    per_target_ok=all(v["per_target_gate_pass"] for v in verdicts.values())
    verdict="MECHANISM_CONFIRMED" if (per_target_ok and pooled_ok) else "MECHANISM_NOT_CONFIRMED"

    result={
        "schema":"CMDO_U10_RESULT_v0.1",
        "preoutcome_seal_sha256":EXPECTED_SEAL_SHA,
        "locked_evaluation_spec_sha256":EXPECTED_SPEC_SHA,
        "target_summary":target_summary,
        "per_target_gate":verdicts,
        "pooled_strict_median_abs_coupling_reduction_pct":pooled_strict_median,
        "pooled_crossfit_median_abs_coupling_reduction_pct":pooled_cf_median,
        "primary_verdict":verdict,
        "summary_csv_sha256":sha256_file(csv_path),
        "created_unix":time.time()
    }
    json_path=outdir/"U10_PRIMARY_RESULT.json"
    json_path.write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")

    print("="*78)
    print(" U10 PROSPECTIVE EVALUATION COMPLETE")
    print(f" Primary verdict: {verdict}")
    for ds,v in verdicts.items():
        print(f" {ds}: strict {v['strict_budgets_reduced_abs_coupling']}/4; crossfit {v['crossfit_budgets_reduced_abs_coupling']}/4; pass={v['per_target_gate_pass']}")
    print(f" pooled median |coupling| reduction: strict={pooled_strict_median:+.2f}% crossfit={pooled_cf_median:+.2f}%")
    print(f" Results: {outdir}")
    print(f" CSV SHA256: {sha256_file(csv_path)}")
    print(f" JSON SHA256: {sha256_file(json_path)}")
    print("="*78)

if __name__=="__main__":
    main()
