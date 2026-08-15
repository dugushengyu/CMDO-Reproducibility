from __future__ import annotations
from pathlib import Path
import argparse, json, hashlib, shutil, zipfile, sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve

from cmdo_observer import evaluate_target, synthetic_selftest
from downloaders import ensure_uci_heart, ensure_physionet_2019

HERE = Path(__file__).resolve().parent
CONFIG = json.loads((HERE/"frozen_config_v1_0.json").read_text(encoding="utf-8"))
WORK = HERE/"CMDO_U9_OpenClinical_Workdir_v1_0"
RAW = WORK/"00_Raw_Official"
DERIVED = WORK/"01_Derived"
RESULTS = WORK/"03_Results"
FIGS = WORK/"04_Figures"
CANON = WORK/"05_Canonical"
MANUAL = HERE/"manual_downloads"

def mkdirs():
    for p in (WORK, RAW, DERIVED, RESULTS, FIGS, CANON, MANUAL):
        p.mkdir(parents=True, exist_ok=True)

def sha256(p: Path) -> str:
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1024*1024), b""): h.update(b)
    return h.hexdigest()

def youden_threshold(y, score):
    fpr,tpr,thr = roc_curve(y, score)
    j=tpr-fpr
    ix=int(np.nanargmax(j))
    return float(thr[ix])

def make_model(seed):
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
        ("scaler", StandardScaler()),
        ("logit", LogisticRegression(
            penalty="l2", C=1.0, solver="lbfgs", max_iter=3000,
            random_state=seed
        ))
    ])

def split_three(X,y,seed):
    Xtr, Xrest, ytr, yrest = train_test_split(
        X,y,test_size=0.40,stratify=y,random_state=seed)
    Xval, Xhist, yval, yhist = train_test_split(
        Xrest,yrest,test_size=0.50,stratify=yrest,random_state=seed+1)
    return Xtr,Xval,Xhist,ytr,yval,yhist

def save_json(obj,p):
    def conv(x):
        if isinstance(x,(np.integer,)): return int(x)
        if isinstance(x,(np.floating,)): return float(x)
        if isinstance(x,(np.bool_,)): return bool(x)
        raise TypeError(type(x).__name__)
    p.write_text(json.dumps(obj,indent=2,default=conv,allow_nan=False),encoding="utf-8")

# ---------------- U9A ----------------
HEART_COLS=["age","sex","cp","trestbps","chol","fbs","restecg","thalach","exang","oldpeak","slope","ca","thal","num"]

def find_heart_files(root):
    files={p.name.lower():p for p in root.rglob("processed.*.data")}
    def pick(*tokens):
        for name,p in files.items():
            if all(t in name for t in tokens): return p
        return None
    out={
        "cleveland":pick("cleveland"),
        "hungary":pick("hungarian"),
        "switzerland":pick("switzerland"),
        "va_long_beach":pick("va"),
    }
    if any(v is None for v in out.values()):
        raise RuntimeError(f"Could not identify processed UCI centre files. Available: {list(files)}")
    return out

def load_heart(p):
    df=pd.read_csv(p,header=None,names=HEART_COLS,na_values="?")
    for c in HEART_COLS: df[c]=pd.to_numeric(df[c],errors="coerce")
    df=df.dropna(subset=["num"]).copy()
    y=(df.pop("num").values>0).astype(int)
    return df.values.astype(float),y

def run_u9a():
    cfg=CONFIG["u9a"]
    root=ensure_uci_heart(RAW,MANUAL)
    fs=find_heart_files(root)
    Xs,ys=load_heart(fs["cleveland"])
    Xtr,Xval,Xhist,ytr,yval,yhist=split_three(Xs,ys,cfg["seed_split"])
    mdl=make_model(cfg["seed_split"])
    mdl.fit(Xtr,ytr)
    sval=mdl.predict_proba(Xval)[:,1]
    threshold=youden_threshold(yval,sval)
    shist=mdl.predict_proba(Xhist)[:,1]
    hist_acc=float(((shist>=threshold).astype(int)==yhist).mean())
    source={
        "source_n":int(len(ys)),"train_n":int(len(ytr)),"validation_n":int(len(yval)),
        "historical_n":int(len(yhist)),"threshold":threshold,
        "historical_accuracy":hist_acc,"historical_auc":float(roc_auc_score(yhist,shist))
    }
    all_reps=[]; all_states=[]; target_summaries=[]
    for ti,t in enumerate(cfg["targets"]):
        X,y=load_heart(fs[t])
        s=mdl.predict_proba(X)[:,1]
        reps,states,summ=evaluate_target(
            target_name=t,y=y,score=s,threshold=threshold,
            historical_accuracy=hist_acc,budgets=cfg["budgets"],
            replicates=cfg["replicates"],master_seed=cfg["seed_audit"]+ti,
            folds=CONFIG["observer"]["folds"],
            opposite=tuple(CONFIG["observer"]["opposite_fold_zero_based"]),
            delta_family=CONFIG["observer"]["delta_family"],
            max_weight=CONFIG["observer"]["max_transport_weight"])
        all_reps.append(reps); all_states.append(states); target_summaries.append(summ)
    reps=pd.concat(all_reps,ignore_index=True); states=pd.concat(all_states,ignore_index=True)
    reps.to_csv(RESULTS/"U9A_replicates.csv",index=False)
    states.to_csv(RESULTS/"U9A_states.csv",index=False)
    targets=(reps.groupby("target",as_index=False)
             .agg(direct_mae=("direct_abs_error","mean"),
                  observer_mae=("observer_abs_error","mean"),
                  mean_weight=("mean_weight","mean"),
                  true_accuracy=("true_accuracy","first"),
                  target_n=("target_n","first")))
    targets["regret"]=targets.observer_mae-targets.direct_mae
    targets["relative_gain"]=(targets.direct_mae-targets.observer_mae)/targets.direct_mae
    targets.to_csv(RESULTS/"U9A_targets.csv",index=False)
    summary={
        "stage":"U9A","role":"MULTICENTRE_BRIDGE_FALSIFICATION",
        "source":source,
        "pooled_direct_mae":float(reps.direct_abs_error.mean()),
        "pooled_observer_mae":float(reps.observer_abs_error.mean()),
        "pooled_relative_gain":float((reps.direct_abs_error.mean()-reps.observer_abs_error.mean())/reps.direct_abs_error.mean()),
        "worst_state_regret":float(states.regret.max()),
        "improved_targets":int((targets.regret<=0).sum()),
        "mean_weight":float(reps.mean_weight.mean()),
        "certificate_violations":int(reps.covered_event_certificate_violations.sum()),
        "maximum_fallback_residual":float(reps.fallback_residual.max())
    }
    gates={
        "exact_fallback":summary["maximum_fallback_residual"]<1e-12,
        "zero_certificate_violations":summary["certificate_violations"]==0,
        "pooled_noninferiority":summary["pooled_observer_mae"]<=summary["pooled_direct_mae"],
        "worst_state_regret":summary["worst_state_regret"]<=0.015,
        "two_of_three_targets_improve":summary["improved_targets"]>=2,
        "nontrivial_borrowing":summary["mean_weight"]>0,
    }
    summary["gates"]=gates
    summary["decision"]="SUPPORT_MULTICENTRE_BRIDGE" if all(gates.values()) else "BRIDGE_FALSIFICATION_SIGNAL"
    save_json(summary,RESULTS/"U9A_summary.json")
    # Figure
    fig,ax=plt.subplots(figsize=(7.2,4.5))
    for i,row in targets.reset_index(drop=True).iterrows():
        ax.plot([row.direct_mae,row.observer_mae],[i,i],lw=1)
        ax.scatter(row.direct_mae,i,facecolors="none",edgecolors="black",label="Direct" if i==0 else None)
        ax.scatter(row.observer_mae,i,marker="s",label="Observer" if i==0 else None)
    ax.set_yticks(range(len(targets)),targets.target.tolist())
    ax.set_xlabel("Pooled accuracy MAE")
    ax.set_title("U9A multicentre bridge")
    ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(FIGS/"U9A_multicentre_bridge.png",dpi=300); plt.close(fig)
    return summary

# --------------- U9B -----------------
PHYS_VARS=["HR","O2Sat","Temp","SBP","MAP","DBP","Resp","EtCO2","BaseExcess","HCO3","FiO2","pH","PaCO2","SaO2","AST","BUN","Alkalinephos","Calcium","Chloride","Creatinine","Bilirubin_direct","Glucose","Lactate","Magnesium","Phosphate","Potassium","Bilirubin_total","TroponinI","Hct","Hgb","PTT","WBC","Fibrinogen","Platelets"]
STATIC=["Age","Gender","Unit1","Unit2","HospAdmTime"]

def phys_subject_features_only(p:Path, first_hours:int):
    # Deliberately do not read or convert SepsisLabel here. This routine is
    # permitted before the U9B one-shot target-outcome marker.
    df=pd.read_csv(p,sep="|")
    required=set(PHYS_VARS+STATIC)
    missing=required.difference(df.columns)
    if missing:
        raise RuntimeError(f"Missing predictor columns in {p}: {sorted(missing)}")
    w=df.iloc[:first_hours].copy()
    feat=[]
    for c in PHYS_VARS:
        x=pd.to_numeric(w[c],errors="coerce").to_numpy(float)
        finite=x[np.isfinite(x)]
        feat.extend([
            float(np.mean(finite)) if len(finite) else np.nan,
            float(finite[-1]) if len(finite) else np.nan,
            float(1.0-len(finite)/max(len(x),1))
        ])
    for c in STATIC:
        x=pd.to_numeric(df[c],errors="coerce").to_numpy(float)
        finite=x[np.isfinite(x)]
        feat.append(float(finite[0]) if len(finite) else np.nan)
    return feat

def phys_subject_label_only(p:Path):
    df=pd.read_csv(p,sep="|",usecols=["SepsisLabel"])
    return int(pd.to_numeric(df["SepsisLabel"],errors="coerce").fillna(0).max()>0)

def build_phys_features(root:Path, name:str, hours:int):
    cache=DERIVED/f"{name}_features_first{hours}h.npz"
    if cache.exists():
        z=np.load(cache)
        return z["X"]
    files=sorted(root.rglob("*.psv"))
    X=[]; total=len(files)
    for i,p in enumerate(files,1):
        X.append(phys_subject_features_only(p,hours))
        if i%2000==0: print(f"  {name}: extracted outcome-free features {i}/{total}")
    X=np.asarray(X,float)
    np.savez_compressed(cache,X=X)
    return X

def build_phys_labels(root:Path, name:str):
    cache=DERIVED/f"{name}_OUTCOMES_AFTER_MARKER.npz"
    if cache.exists():
        z=np.load(cache)
        return z["y"]
    files=sorted(root.rglob("*.psv"))
    y=[]; total=len(files)
    for i,p in enumerate(files,1):
        y.append(phys_subject_label_only(p))
        if i%4000==0: print(f"  {name}: read outcomes {i}/{total}")
    y=np.asarray(y,int)
    np.savez_compressed(cache,y=y)
    return y

def run_u9b():
    cfg=CONFIG["u9b"]
    Aroot,Broot=ensure_physionet_2019(RAW,MANUAL)

    # Source outcomes are permitted. Target System-B predictors are extracted
    # outcome-free before the marker; target labels are read only afterwards.
    XA=build_phys_features(Aroot,"training_setA",cfg["first_hours"])
    yA=build_phys_labels(Aroot,"training_setA_SOURCE_ALLOWED")
    XB=build_phys_features(Broot,"training_setB",cfg["first_hours"])

    marker=RESULTS/"U9B_ONE_SHOT_ANALYSIS_STARTED_v1_0.json"
    if marker.exists():
        raise RuntimeError("U9B one-shot marker already exists. Preserve Workdir; do not silently rerun. "
                           "Use a fresh copy only for a disclosed reconstruction.")
    save_json({
        "stage":"U9B","status":"ONE_SHOT_TARGET_OUTCOME_ANALYSIS_STARTED",
        "source_feature_cache_sha256":sha256(DERIVED/f"training_setA_features_first{cfg['first_hours']}h.npz"),
        "target_outcome_free_feature_cache_sha256":sha256(DERIVED/f"training_setB_features_first{cfg['first_hours']}h.npz"),
        "note":"Marker written before System-B SepsisLabel values are read into analysis."
    },marker)

    yB=build_phys_labels(Broot,"training_setB_TARGET")
    Xtr,Xval,Xhist,ytr,yval,yhist=split_three(XA,yA,cfg["seed_split"])
    mdl=make_model(cfg["seed_split"])
    mdl.fit(Xtr,ytr)
    sval=mdl.predict_proba(Xval)[:,1]
    threshold=youden_threshold(yval,sval)
    shist=mdl.predict_proba(Xhist)[:,1]
    hist_acc=float(((shist>=threshold).astype(int)==yhist).mean())
    sb=mdl.predict_proba(XB)[:,1]


    reps,states,summ=evaluate_target(
        target_name="hospital_system_B",y=yB,score=sb,threshold=threshold,
        historical_accuracy=hist_acc,budgets=cfg["budgets"],replicates=cfg["replicates"],
        master_seed=cfg["seed_audit"],folds=CONFIG["observer"]["folds"],
        opposite=tuple(CONFIG["observer"]["opposite_fold_zero_based"]),
        delta_family=CONFIG["observer"]["delta_family"],
        max_weight=CONFIG["observer"]["max_transport_weight"])
    reps.to_csv(RESULTS/"U9B_replicates.csv",index=False)
    states.to_csv(RESULTS/"U9B_states.csv",index=False)
    source={
        "system_A_n":int(len(yA)),"system_B_n":int(len(yB)),
        "system_A_prevalence":float(yA.mean()),"system_B_prevalence":float(yB.mean()),
        "train_n":int(len(ytr)),"validation_n":int(len(yval)),"historical_n":int(len(yhist)),
        "threshold":threshold,"historical_accuracy":hist_acc,
        "historical_auc":float(roc_auc_score(yhist,shist)),
        "target_auc":float(roc_auc_score(yB,sb))
    }
    summary={"stage":"U9B","role":"PRIMARY_OPEN_EXTERNAL_CLINICAL_SYSTEM_RESERVE","source":source,**summ}
    gates={
        "system_counts":len(yA)>=20000 and len(yB)>=19500,
        "exact_fallback":summ["maximum_fallback_residual"]<1e-12,
        "zero_certificate_violations":summ["certificate_violations"]==0,
        "mean_simultaneous_coverage":summ["mean_simultaneous_coverage"]>=0.90,
        "minimum_budget_coverage":summ["minimum_simultaneous_coverage"]>=0.85,
        "root_budget_slope":(-0.70<=summ["direct_root_budget_slope"]<=-0.30),
        "pooled_noninferiority":summ["observer_mae"]<=summ["direct_mae"],
        "worst_budget_regret":summ["worst_state_regret"]<=0.005,
        "nontrivial_borrowing":summ["mean_weight"]>0,
    }
    summary["gates"]=gates
    integrity=["system_counts","exact_fallback","zero_certificate_violations",
               "mean_simultaneous_coverage","minimum_budget_coverage","root_budget_slope"]
    empirical=["pooled_noninferiority","worst_budget_regret","nontrivial_borrowing"]
    if all(gates[k] for k in integrity) and all(gates[k] for k in empirical):
        summary["decision"]="SUPPORT_OPEN_EXTERNAL_CLINICAL_SYSTEM_OBSERVER"
    elif all(gates[k] for k in integrity):
        summary["decision"]="PARTIAL_EXTERNAL_CERTIFICATION_EFFICIENCY_NOT_CONFIRMED"
    else:
        summary["decision"]="FAIL_U9B_INTEGRITY_OR_CERTIFICATION_GATE"
    save_json(summary,RESULTS/"U9B_summary.json")

    fig,ax=plt.subplots(figsize=(7.2,4.5))
    st=states.sort_values("budget")
    ax.plot(st.budget,st.direct_mae,"--o",label="Same-budget direct")
    ax.plot(st.budget,st.observer_mae,"-o",label="Guarded observer")
    ax.set_xscale("log",base=2)
    ax.set_xlabel("Screened-case budget")
    ax.set_ylabel("Accuracy MAE")
    ax.set_title("U9B external hospital-system reserve")
    ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(FIGS/"U9B_external_system_MAE.png",dpi=300); plt.close(fig)

    fig,ax=plt.subplots(figsize=(7.2,4.5))
    ax.plot(st.budget,st.mean_weight,"-o")
    ax.set_xscale("log",base=2)
    ax.set_xlabel("Screened-case budget")
    ax.set_ylabel("Mean transport weight")
    ax.set_title("U9B guarded borrowing")
    fig.tight_layout(); fig.savefig(FIGS/"U9B_transport_weight.png",dpi=300); plt.close(fig)
    return summary

def canonicalize(u9a,u9b):
    complete={
        "stage":"U9_OPEN_CLINICAL","version":"v1.0",
        "u9a":u9a,"u9b":u9b,
        "primary_claim_decision":u9b["decision"],
        "eicu_status":"DEFERRED_CONFIRMATORY_MULTICENTRE_REPLICATION_NOT_REQUIRED_FOR_PRIMARY_U9_DECISION"
    }
    complete_path=CANON/"StageU9_OpenClinical_Complete_v1_0.json"
    save_json(complete,complete_path)
    members=[
        RESULTS/"U9A_summary.json",RESULTS/"U9A_targets.csv",RESULTS/"U9A_states.csv",
        RESULTS/"U9B_summary.json",RESULTS/"U9B_states.csv",
        FIGS/"U9A_multicentre_bridge.png",FIGS/"U9B_external_system_MAE.png",FIGS/"U9B_transport_weight.png",
        complete_path
    ]
    zpath=CANON/"CMDO_U9_OpenClinical_Canonical_Record_v1_0.zip"
    with zipfile.ZipFile(zpath,"w",compression=zipfile.ZIP_DEFLATED) as z:
        for p in members: z.write(p,p.relative_to(WORK))
    (CANON/"CMDO_U9_OpenClinical_Canonical_Record_v1_0.sha256").write_text(
        sha256(zpath)+"  "+zpath.name+"\n",encoding="utf-8")
    return complete

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("mode",choices=["selftest","u9a","u9b","all"])
    args=ap.parse_args()
    mkdirs()
    if args.mode=="selftest":
        print(json.dumps(synthetic_selftest(),indent=2)); return
    if args.mode=="u9a":
        s=run_u9a(); print(json.dumps(s,indent=2)); return
    if args.mode=="u9b":
        s=run_u9b(); print(json.dumps(s,indent=2)); return
    # all
    a=run_u9a()
    b=run_u9b()
    c=canonicalize(a,b)
    print("\n================ CMDO U9 OPEN CLINICAL COMPLETE ================")
    print("U9A decision:",a["decision"])
    print("U9B decision:",b["decision"])
    print("U9B direct MAE:",f'{b["direct_mae"]:.8f}')
    print("U9B observer MAE:",f'{b["observer_mae"]:.8f}')
    print("U9B relative gain:",f'{100*b["relative_gain"]:.3f}%')
    print("U9B worst budget regret:",f'{b["worst_state_regret"]:.8f}')
    print("U9B mean weight:",f'{b["mean_weight"]:.6f}')
    print("Canonical ZIP:",CANON/"CMDO_U9_OpenClinical_Canonical_Record_v1_0.zip")

if __name__=="__main__":
    main()
