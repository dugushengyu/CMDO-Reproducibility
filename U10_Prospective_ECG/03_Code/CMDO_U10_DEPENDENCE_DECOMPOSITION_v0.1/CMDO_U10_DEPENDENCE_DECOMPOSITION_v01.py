#!/usr/bin/env python3
"""
CMDO U10 POST-HOC DEPENDENCE DECOMPOSITION v0.1
================================================

Exploratory only. The prospective verdict remains MECHANISM_NOT_CONFIRMED.

Purpose:
Separate four possibilities behind U10's large-budget failures:
1) historical evidence is intrinsically not worth borrowing;
2) mean borrowing level is wrong;
3) random-weight heterogeneity is costly;
4) dependence between adaptive weights and audit error is costly.

It also tests a mechanistic control:
- original cross-fit uses disjoint halves drawn without replacement;
- independent-fold control draws A and B independently from the target frame
  (overlap allowed) and is therefore a NON-DEPLOYMENT mechanistic control.

No prospective claim is changed.
"""

from __future__ import annotations
import argparse, hashlib, json, re, time
from pathlib import Path
import numpy as np
import pandas as pd

EXPECTED_SEAL = "efccafc32dc7778986296f6f7314488f6d08c45bdff2efdcb7f0918d36aec949"
EXPECTED_SPEC = "25b8810080a595494552789aca632c67db4b6af16b7f404920e38d9aee45a449"
EXPECTED_CSV = "685be9c1a86b4ace5c41d1ff4564fc2fedd65a8f15e9555fe6b3886a6d3c4df9"
EXPECTED_JSON = "dd2624ba443c69ef2dd276f40eefdff8dadb97612e9838c77b019a4e15c9b090"

AF_CODE="164889003"
MASTER=20260823
BUDGETS=[128,256,512,1024]
REPS=200
PERMS=500
CAP=.35

def sha256_file(p: Path, block=4*1024*1024):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(block), b""):
            h.update(b)
    return h.hexdigest()

def require(c,msg):
    if not c: raise RuntimeError(msg)

def parse_dx(p: Path):
    txt=p.read_text(encoding="utf-8-sig",errors="replace")
    m=re.search(r"(?im)^\s*#?\s*Dx\s*:\s*(.*?)\s*$",txt)
    return set() if not m else set(re.findall(r"\d+",m.group(1)))

def seed_for(*parts):
    s="|".join(map(str,parts)).encode()
    return int.from_bytes(hashlib.sha256(s).digest()[:8],"little")

def w_rule(D,H,m):
    V=max(D*(1-D)/m,1e-8)
    return min(CAP,V/(V+(D-H)**2))

def mse(a,theta):
    a=np.asarray(a,float)
    return float(np.mean((a-theta)**2))

def gain(base,risk):
    return float(100*(base-risk)/base)

def load_z(root,ds,seal):
    score=root/"PRESEAL"/f"TARGET_SCORES_{ds}.csv"
    roster=root/"PRESEAL"/f"ROSTER_{ds}.csv"
    rec=[x for x in seal["target_artifacts"] if x["dataset"]==ds][0]
    require(sha256_file(score)==rec["score_sha256"],f"{ds}: score hash mismatch")
    require(sha256_file(roster)==rec["roster_sha256"],f"{ds}: roster hash mismatch")
    df=pd.read_csv(score,dtype={"record_id":str})
    hm={p.stem:p for p in (root/"data"/ds).rglob("*.hea")}
    y=np.asarray([int(AF_CODE in parse_dx(hm[r])) for r in df.record_id],dtype=np.int8)
    pred=df.predicted_af.to_numpy(dtype=np.int8)
    return (pred==y).astype(float)

def original_replicates(z,H,ds,m):
    N=len(z); h=m//2
    D=[]; DA=[]; DB=[]; wF=[]; wA=[]; wB=[]; shared=[]; cf=[]
    for r in range(REPS):
        rng=np.random.default_rng(seed_for(MASTER,ds,m,r))
        idx=rng.choice(N,size=m,replace=False)
        rng.shuffle(idx)
        ia=idx[:h]; ib=idx[h:]
        d=float(z[idx].mean()); da=float(z[ia].mean()); db=float(z[ib].mean())
        wf=w_rule(d,H,m); wa=w_rule(da,H,h); wb=w_rule(db,H,m-h)
        D.append(d); DA.append(da); DB.append(db); wF.append(wf); wA.append(wa); wB.append(wb)
        shared.append((1-wf)*d+wf*H)
        cf.append(.5*((1-wb)*da+wb*H + (1-wa)*db+wa*H))
    return [np.asarray(x,float) for x in (D,DA,DB,wF,wA,wB,shared,cf)]

def independent_fold_control(z,H,ds,m):
    """
    Mechanistic control only:
    A and B are independently sampled SRSWOR half-samples from the same finite frame.
    They may overlap, so this is not an audit-budget-preserving deployment design.
    """
    N=len(z); h=m//2
    out=[]
    cfs=[]; DA=[]; DB=[]; wA=[]; wB=[]
    for r in range(REPS):
        rngA=np.random.default_rng(seed_for("indA",MASTER,ds,m,r))
        rngB=np.random.default_rng(seed_for("indB",MASTER,ds,m,r))
        ia=rngA.choice(N,size=h,replace=False)
        ib=rngB.choice(N,size=m-h,replace=False)
        da=float(z[ia].mean()); db=float(z[ib].mean())
        wa=w_rule(da,H,h); wb=w_rule(db,H,m-h)
        est=.5*((1-wb)*da+wb*H + (1-wa)*db+wa*H)
        DA.append(da); DB.append(db); wA.append(wa); wB.append(wb); cfs.append(est)
    return [np.asarray(x,float) for x in (DA,DB,wA,wB,cfs)]

def shared_exact_decomp(D,W,H,theta):
    e=D-theta; B=H-theta
    wb=float(W.mean())
    V2=float(np.mean(e*e))
    varW=float(np.var(W))
    covmag=float(np.mean(((1-W)**2 - np.mean((1-W)**2)) * (e*e - np.mean(e*e))))
    directional=float(2*B*(np.mean(W*(1-W)*e)-wb*(1-wb)*np.mean(e)))
    hetero=float((V2+B*B)*varW)
    fixed=(1-wb)*D+wb*H
    adaptive=(1-W)*D+W*H
    tax=mse(adaptive,theta)-mse(fixed,theta)
    require(abs(tax-(hetero+covmag+directional))<1e-12,"Shared exact adaptation-tax decomposition failed")
    return tax,hetero,covmag,directional,mse(fixed,theta)

def permuted_shared(D,W,H,theta,ds,m):
    risks=[]
    for k in range(PERMS):
        rng=np.random.default_rng(seed_for("perm_shared",MASTER,ds,m,k))
        wp=W[rng.permutation(len(W))]
        risks.append(mse((1-wp)*D+wp*H,theta))
    return float(np.mean(risks)),float(np.std(risks))

def permuted_crossfit(DA,DB,wA,wB,H,theta,ds,m):
    risks=[]
    for k in range(PERMS):
        rngA=np.random.default_rng(seed_for("perm_cf_A",MASTER,ds,m,k))
        rngB=np.random.default_rng(seed_for("perm_cf_B",MASTER,ds,m,k))
        wa=wA[rngA.permutation(len(wA))]
        wb=wB[rngB.permutation(len(wB))]
        est=.5*((1-wb)*DA+wb*H + (1-wa)*DB+wa*H)
        risks.append(mse(est,theta))
    return float(np.mean(risks)),float(np.std(risks))

def one_cell(z,H,ds,m,prospective):
    N=len(z); h=m//2; theta=float(z.mean()); B=H-theta
    D,DA,DB,wF,wA,wB,shared,cf=original_replicates(z,H,ds,m)
    base=mse(D,theta)

    # Reproduce locked result.
    ref=float(prospective.loc[(prospective.dataset==ds)&(prospective.budget==m),"crossfit_mse"].iloc[0])
    require(abs(mse(cf,theta)-ref)<1e-12,f"{ds} m={m}: prospective reproduction mismatch")

    # Fixed mean-weight controls.
    wfbar=float(wF.mean())
    shared_const=(1-wfbar)*D+wfbar*H
    wabar=float(wA.mean()); wbbar=float(wB.mean())
    cf_const=.5*((1-wbbar)*DA+wbbar*H + (1-wabar)*DB+wabar*H)

    # Permutation controls preserve adaptive-weight marginals while breaking pairing.
    psh,psh_sd=permuted_shared(D,wF,H,theta,ds,m)
    pcf,pcf_sd=permuted_crossfit(DA,DB,wA,wB,H,theta,ds,m)

    # Independent-fold mechanistic control.
    iDA,iDB,iwA,iwB,icf=independent_fold_control(z,H,ds,m)

    # Exact shared adaptation tax.
    tax,hetero,covmag,directional,shared_const_exact=shared_exact_decomp(D,wF,H,theta)
    require(abs(shared_const_exact-mse(shared_const,theta))<1e-12,"constant shared mismatch")

    # Cross-half dependence.
    corrAB=float(np.corrcoef(DA,DB)[0,1])
    covAB=float(np.mean((DA-DA.mean())*(DB-DB.mean())))
    theoretical_corr=float(-h/(N-h))
    corr_ind=float(np.corrcoef(iDA,iDB)[0,1])

    # Weight-error cross dependence.
    eA=DA-theta; eB=DB-theta
    cov_wA_eB=float(np.mean((wA-wA.mean())*(eB-eB.mean())))
    cov_wB_eA=float(np.mean((wB-wB.mean())*(eA-eA.mean())))
    ieA=iDA-theta; ieB=iDB-theta
    cov_iwA_ieB=float(np.mean((iwA-iwA.mean())*(ieB-ieB.mean())))
    cov_iwB_ieA=float(np.mean((iwB-iwB.mean())*(ieA-ieA.mean())))

    return {
        "dataset":ds,"budget":m,"N":N,"theta":theta,"H":H,"B":B,
        "direct_mse":base,
        "shared_adaptive_mse":mse(shared,theta),
        "shared_adaptive_gain_pct":gain(base,mse(shared,theta)),
        "shared_constant_mean_weight":wfbar,
        "shared_constant_mean_mse":mse(shared_const,theta),
        "shared_constant_mean_gain_pct":gain(base,mse(shared_const,theta)),
        "shared_permuted_weight_mse":psh,
        "shared_permuted_weight_gain_pct":gain(base,psh),
        "shared_permuted_weight_mse_sd":psh_sd,
        "shared_adaptation_tax":tax,
        "shared_tax_weight_heterogeneity":hetero,
        "shared_tax_error_magnitude_covariance":covmag,
        "shared_tax_directional_dependence":directional,
        "crossfit_adaptive_mse":mse(cf,theta),
        "crossfit_adaptive_gain_pct":gain(base,mse(cf,theta)),
        "crossfit_constant_mean_weight_A":wabar,
        "crossfit_constant_mean_weight_B":wbbar,
        "crossfit_constant_mean_mse":mse(cf_const,theta),
        "crossfit_constant_mean_gain_pct":gain(base,mse(cf_const,theta)),
        "crossfit_permuted_weight_mse":pcf,
        "crossfit_permuted_weight_gain_pct":gain(base,pcf),
        "crossfit_permuted_weight_mse_sd":pcf_sd,
        "independent_fold_crossfit_mse":mse(icf,theta),
        "independent_fold_crossfit_gain_vs_original_full_direct_pct":gain(base,mse(icf,theta)),
        "corr_DA_DB_disjoint_observed":corrAB,
        "corr_DA_DB_disjoint_theory":theoretical_corr,
        "cov_DA_DB_disjoint":covAB,
        "corr_DA_DB_independent_control":corr_ind,
        "cov_wA_errorB_disjoint":cov_wA_eB,
        "cov_wB_errorA_disjoint":cov_wB_eA,
        "cov_wA_errorB_independent_control":cov_iwA_ieB,
        "cov_wB_errorA_independent_control":cov_iwB_ieA,
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

    for name,p,exp in [
        ("seal",sealp,EXPECTED_SEAL),("spec",specp,EXPECTED_SPEC),
        ("prospective_csv",csvp,EXPECTED_CSV),("prospective_json",jsonp,EXPECTED_JSON)
    ]:
        actual=sha256_file(p)
        require(actual==exp,f"{name} hash mismatch: {actual}")
        print(f"[verify] {name}: PASS {actual}")

    seal=json.loads(sealp.read_text(encoding="utf-8"))
    H=float(seal["source_development"]["historical_accuracy_H"])
    prospective=pd.read_csv(csvp)

    rows=[]
    for ds in ("georgia","cpsc_2018"):
        z=load_z(root,ds,seal)
        for m in BUDGETS:
            rec=one_cell(z,H,ds,m,prospective)
            rows.append(rec)
            print(
                f"[cell] {ds} m={m} "
                f"shared={rec['shared_adaptive_gain_pct']:+.2f}% "
                f"shared_const={rec['shared_constant_mean_gain_pct']:+.2f}% "
                f"shared_perm={rec['shared_permuted_weight_gain_pct']:+.2f}% "
                f"cf={rec['crossfit_adaptive_gain_pct']:+.2f}% "
                f"cf_const={rec['crossfit_constant_mean_gain_pct']:+.2f}% "
                f"cf_perm={rec['crossfit_permuted_weight_gain_pct']:+.2f}% "
                f"cf_ind={rec['independent_fold_crossfit_gain_vs_original_full_direct_pct']:+.2f}%"
            )

    df=pd.DataFrame(rows)
    od=root/"UNSEAL"/"POSTHOC_DEPENDENCE_DECOMPOSITION_v0.1"
    od.mkdir(parents=True,exist_ok=True)
    csvout=od/"U10_DEPENDENCE_DECOMPOSITION.csv"
    df.to_csv(csvout,index=False,float_format="%.12g")

    # Classification of the failure pattern, intentionally descriptive.
    summary={}
    for ds in ("georgia","cpsc_2018"):
        d=df[df.dataset==ds]
        summary[ds]={
            "adaptive_crossfit_positive_budgets":int((d.crossfit_adaptive_gain_pct>0).sum()),
            "constant_mean_crossfit_positive_budgets":int((d.crossfit_constant_mean_gain_pct>0).sum()),
            "permuted_weight_crossfit_positive_budgets":int((d.crossfit_permuted_weight_gain_pct>0).sum()),
            "independent_fold_crossfit_positive_budgets_vs_original_full_direct":int((d.independent_fold_crossfit_gain_vs_original_full_direct_pct>0).sum()),
            "median_disjoint_corr_observed":float(d.corr_DA_DB_disjoint_observed.median()),
            "median_disjoint_corr_theory":float(d.corr_DA_DB_disjoint_theory.median()),
            "median_independent_control_corr":float(d.corr_DA_DB_independent_control.median()),
            "median_shared_adaptation_tax":float(d.shared_adaptation_tax.median()),
        }

    jout=od/"U10_DEPENDENCE_DECOMPOSITION.json"
    result={
        "schema":"CMDO_U10_POSTHOC_DEPENDENCE_DECOMPOSITION_v0.1",
        "status":"EXPLORATORY_POSTHOC_DO_NOT_REPLACE_PROSPECTIVE_VERDICT",
        "prospective_verdict":"MECHANISM_NOT_CONFIRMED",
        "summary":summary,
        "csv_sha256":sha256_file(csvout),
        "created_unix":time.time()
    }
    jout.write_text(json.dumps(result,indent=2,sort_keys=True),encoding="utf-8")

    print("="*110)
    print(" U10 POST-HOC DEPENDENCE DECOMPOSITION COMPLETE")
    print(" Prospective verdict remains MECHANISM_NOT_CONFIRMED")
    print("="*110)
    cols=[
        "dataset","budget",
        "shared_adaptive_gain_pct","shared_constant_mean_gain_pct","shared_permuted_weight_gain_pct",
        "shared_adaptation_tax","shared_tax_weight_heterogeneity",
        "shared_tax_error_magnitude_covariance","shared_tax_directional_dependence",
        "crossfit_adaptive_gain_pct","crossfit_constant_mean_gain_pct",
        "crossfit_permuted_weight_gain_pct","independent_fold_crossfit_gain_vs_original_full_direct_pct",
        "corr_DA_DB_disjoint_observed","corr_DA_DB_disjoint_theory",
        "corr_DA_DB_independent_control",
        "cov_wA_errorB_disjoint","cov_wA_errorB_independent_control"
    ]
    print(df[cols].to_string(index=False))
    print()
    print(json.dumps(summary,indent=2))
    print(f"CSV : {csvout}")
    print(f"JSON: {jout}")
    print(f"CSV SHA256 : {sha256_file(csvout)}")
    print(f"JSON SHA256: {sha256_file(jout)}")
    print("="*110)

if __name__=="__main__":
    main()
