#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math, platform, re, sys, time, warnings
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy import signal, stats
from scipy.io import loadmat
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import balanced_accuracy_score, roc_auc_score

AF_CODE = "164889003"
FS = 500
WINDOW_SECONDS = 10
MIN_SECONDS = 6
RAW_N = FS * WINDOW_SECONDS
MIN_N = FS * MIN_SECONDS
DS_FS = 100
DOWNSAMPLE = 5
SEED = 20260823
BUDGETS = [128,256,512,1024]
REPLICATES = 200
MAX_BORROW_WEIGHT = 0.35

EXPECTED = {
    "ptb-xl": {"mat":21837, "hea":21837},
    "georgia": {"mat":10344, "hea":0},
    "cpsc_2018": {"mat":6877, "hea":0},
}

def sha256_file(path: Path, block=4*1024*1024):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(block), b""):
            h.update(b)
    return h.hexdigest()

def sha256_text(s: str):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def require(c,msg):
    if not c:
        raise RuntimeError(msg)

def count_files(d: Path, pattern: str):
    return sum(1 for _ in d.rglob(pattern)) if d.exists() else 0

def forbidden_target_headers(root: Path):
    hits=[]
    for ds in ("georgia","cpsc_2018"):
        d=root/"data"/ds
        if d.exists():
            hits.extend(d.rglob("*.hea"))
    return hits

def roster_size_digest(root: Path, ds: str, pattern: str):
    d=root/"data"/ds
    rows=[]
    for p in sorted(d.rglob(pattern)):
        rows.append(f"{p.relative_to(d).as_posix()}\t{p.stat().st_size}")
    return sha256_text("\n".join(rows))

def audit_download(root: Path):
    hits=forbidden_target_headers(root)
    require(not hits, "PREOUTCOME BOUNDARY VIOLATION: target .hea files exist.")
    rep={}
    for ds,exp in EXPECTED.items():
        d=root/"data"/ds
        nm=count_files(d,"*.mat"); nh=count_files(d,"*.hea")
        require(nm==exp["mat"], f"{ds}: expected {exp['mat']} .mat, found {nm}")
        require(nh==exp["hea"], f"{ds}: expected {exp['hea']} .hea, found {nh}")
        rep[ds]={
            "mat":nm,"hea":nh,
            "mat_roster_size_sha256":roster_size_digest(root,ds,"*.mat"),
            "hea_roster_size_sha256":roster_size_digest(root,ds,"*.hea") if nh else None,
        }
    return rep

def parse_source_dx_codes(header: Path):
    """Robust SOURCE-ONLY diagnosis parser for PhysioNet Challenge headers."""
    txt = header.read_text(encoding="utf-8-sig", errors="replace")

    # Accept common variants such as "#Dx:", "# Dx :", "Dx:" and leading whitespace.
    m = re.search(r"(?im)^\s*#?\s*Dx\s*:\s*(.*?)\s*$", txt)
    if not m:
        return set()

    # SNOMED codes are integer tokens. Parsing digits also tolerates whitespace
    # and trailing punctuation without changing the diagnosis semantics.
    return set(re.findall(r"\d+", m.group(1)))

def parse_source_label(header: Path):
    return int(AF_CODE in parse_source_dx_codes(header))

def load_ecg(path: Path):
    obj=loadmat(path)
    if "val" in obj:
        x=np.asarray(obj["val"])
    else:
        c=[np.asarray(v) for k,v in obj.items() if not k.startswith("__") and isinstance(v,np.ndarray) and v.ndim==2]
        if not c: raise ValueError("No 2D ECG array")
        x=max(c,key=lambda a:a.size)
    if x.shape[0]!=12 and x.shape[1]==12:
        x=x.T
    if x.shape[0]!=12:
        raise ValueError(f"Expected 12 leads, got {x.shape}")
    return x.astype(np.float64,copy=False)

def fixed_window(x):
    n=x.shape[1]; dur=n/FS
    if n<MIN_N:
        raise ValueError(f"record too short: {dur:.3f}s")
    if n>=RAW_N:
        return x[:,:RAW_N],dur,0
    need=RAW_N-n
    mode="reflect" if n>1 else "edge"
    return np.pad(x,((0,0),(0,need)),mode=mode),dur,1

def robust_z(x):
    med=np.nanmedian(x,axis=1,keepdims=True)
    mad=np.nanmedian(np.abs(x-med),axis=1,keepdims=True)
    scale=1.4826*mad
    std=np.nanstd(x,axis=1,keepdims=True)
    scale=np.where(scale>1e-8,scale,np.where(std>1e-8,std,1.0))
    z=(x-med)/scale
    z=np.clip(z,-12,12)
    z[~np.isfinite(z)]=0
    return z

def rr_features(v):
    try:
        sos=signal.butter(2,[5,20],btype="bandpass",fs=FS,output="sos")
        y=signal.sosfiltfilt(sos,v)
    except Exception:
        y=v
    env=np.abs(y)
    prom=max(float(np.quantile(env,0.90)*0.35),0.15)
    peaks,_=signal.find_peaks(env,distance=int(0.25*FS),prominence=prom)
    if len(peaks)<4:
        return [float(len(peaks))]+[np.nan]*6
    rr=np.diff(peaks)/FS
    rr=rr[(rr>=0.25)&(rr<=2.5)]
    if len(rr)<3:
        return [float(len(peaks))]+[np.nan]*6
    drr=np.diff(rr)
    hist,_=np.histogram(rr,bins=np.linspace(0.25,2.5,17))
    p=hist/max(hist.sum(),1)
    ent=-(p[p>0]*np.log(p[p>0])).sum()/math.log(16)
    return [
        float(len(peaks)),float(np.mean(rr)),float(np.std(rr)),
        float(np.std(rr)/(np.mean(rr)+1e-12)),
        float(np.sqrt(np.mean(drr*drr))/(np.mean(rr)+1e-12)) if len(drr) else 0.0,
        float(np.mean(np.abs(drr)>0.05)) if len(drr) else 0.0,
        float(ent)
    ]

def feature_names():
    names=["duration_seconds","was_padded"]
    for l in range(12):
        for n in ("absmean","rms","q95_q05","d_absmean","d_std","zero_cross","skew","kurtosis"):
            names.append(f"L{l+1}_{n}")
    for l in range(12):
        for n in ("bp_0p5_3","bp_3_8","bp_8_15","bp_15_30","bp_30_45","spec_entropy"):
            names.append(f"L{l+1}_{n}")
    for lead in ("II","V1"):
        for n in ("peak_count","rr_mean","rr_std","rr_cv","rmssd_norm","pnn50","rr_entropy"):
            names.append(f"{lead}_{n}")
    names += ["crosslead_corr_mean","crosslead_corr_sd"]
    return names

FEATURE_NAMES=feature_names()

def extract_one(path: Path):
    rid=path.stem
    try:
        x=load_ecg(path)
        x,dur,padded=fixed_window(x)
        z=robust_z(x)
        z100=signal.resample_poly(z,1,DOWNSAMPLE,axis=1)
        feats=[float(dur),float(padded)]
        for lead in range(12):
            v=z100[lead]; dv=np.diff(v)
            feats += [
                float(np.mean(np.abs(v))), float(np.sqrt(np.mean(v*v))),
                float(np.quantile(v,0.95)-np.quantile(v,0.05)),
                float(np.mean(np.abs(dv))), float(np.std(dv)),
                float(np.mean(np.signbit(v[:-1])!=np.signbit(v[1:]))),
                float(stats.skew(v,bias=False,nan_policy="omit")),
                float(stats.kurtosis(v,fisher=True,bias=False,nan_policy="omit"))
            ]
        freqs=np.fft.rfftfreq(z100.shape[1],d=1/DS_FS)
        psd=np.abs(np.fft.rfft(z100,axis=1))**2
        psd=np.maximum(psd,1e-12)
        bands=[(0.5,3),(3,8),(8,15),(15,30),(30,45)]
        total=psd[:,(freqs>=0.5)&(freqs<=45)].sum(axis=1)+1e-12
        for lead in range(12):
            p=psd[lead]
            for lo,hi in bands:
                m=(freqs>=lo)&(freqs<hi)
                feats.append(float(p[m].sum()/total[lead]))
            q=p[(freqs>=0.5)&(freqs<=45)]
            q=q/(q.sum()+1e-12)
            feats.append(float(-(q*np.log(q+1e-12)).sum()/math.log(max(len(q),2))))
        feats += rr_features(z[1])
        feats += rr_features(z[6])
        C=np.corrcoef(z100)
        u=C[np.triu_indices_from(C,k=1)]
        u=u[np.isfinite(u)]
        feats += [float(np.mean(u)) if len(u) else np.nan,
                  float(np.std(u)) if len(u) else np.nan]
        require(len(feats)==len(FEATURE_NAMES),"feature length mismatch")
        return rid,True,feats,""
    except Exception as e:
        return rid,False,None,repr(e)

def extract_dataset(root,ds,outdir,workers):
    mats=sorted((root/"data"/ds).rglob("*.mat"))
    print(f"[features] {ds}: {len(mats)} waveforms; workers={workers}")
    rows=Parallel(n_jobs=workers,prefer="processes",batch_size=16,verbose=10)(delayed(extract_one)(p) for p in mats)
    good=[r for r in rows if r[1]]; bad=[r for r in rows if not r[1]]
    require(good,f"No eligible records in {ds}")
    ids=np.asarray([r[0] for r in good],dtype=object)
    X=np.asarray([r[2] for r in good],dtype=np.float32)
    fp=outdir/f"FEATURES_{ds}.npz"
    np.savez_compressed(fp,record_id=ids,X=X,feature_names=np.asarray(FEATURE_NAMES,dtype=object))
    pd.DataFrame({"record_id":ids}).to_csv(outdir/f"ROSTER_{ds}.csv",index=False)
    pd.DataFrame([{"record_id":r[0],"error":r[3]} for r in bad], columns=["record_id","error"]).to_csv(outdir/f"FEATURE_ERRORS_{ds}.csv",index=False)
    print(f"[features] {ds}: eligible={len(good)} excluded={len(bad)} sha256={sha256_file(fp)}")

def load_features(path):
    a=np.load(path,allow_pickle=True)
    return a["record_id"].astype(str),a["X"].astype(np.float32)

def stable_hash(s):
    return hashlib.sha256((str(SEED)+"|"+s).encode()).hexdigest()

def split_source(ids,y):
    split=np.empty(len(ids),dtype=object)
    for cls in (0,1):
        idx=np.flatnonzero(y==cls)
        order=sorted(idx.tolist(),key=lambda i:stable_hash(ids[i]))
        n=len(order); a=int(round(.60*n)); b=int(round(.20*n))
        for j,i in enumerate(order):
            split[i]="train" if j<a else ("validation" if j<a+b else "historical")
    return split.astype(str)

def audit_source_diagnoses(root: Path, ids):
    hm = {p.stem: p for p in (root/"data"/"ptb-xl").rglob("*.hea")}
    require(all(i in hm for i in ids), "Missing source headers")

    counts = {}
    no_dx = 0
    examples = []
    for rid in ids:
        codes = parse_source_dx_codes(hm[rid])
        if not codes:
            no_dx += 1
        for code in codes:
            counts[code] = counts.get(code, 0) + 1
        if len(examples) < 5:
            examples.append({"record_id": rid, "codes": sorted(codes)})

    af_n = int(counts.get(AF_CODE, 0))
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:20]

    print("[labels] PTB-XL source diagnosis audit")
    print(f"[labels] headers={len(ids)} no_Dx={no_dx} unique_codes={len(counts)}")
    print(f"[labels] AF code {AF_CODE}: positives={af_n}")
    print("[labels] top codes:", top)
    print("[labels] first examples:", examples)

    # Save the SOURCE-ONLY label audit before any model training.
    out = root/"PRESEAL"/"SOURCE_DIAGNOSIS_AUDIT_ptb-xl.json"
    out.write_text(json.dumps({
        "source": "ptb-xl",
        "n_headers": int(len(ids)),
        "n_without_parsed_Dx": int(no_dx),
        "unique_codes": int(len(counts)),
        "af_code": AF_CODE,
        "af_positive_count": af_n,
        "top_codes": top,
        "examples": examples
    }, indent=2), encoding="utf-8")

    require(af_n > 0,
            "AF code is still absent after robust source-header parsing; "
            "stop and inspect SOURCE_DIAGNOSIS_AUDIT_ptb-xl.json before changing the task.")
    return af_n

def source_labels(root,ids):
    hm={p.stem:p for p in (root/"data"/"ptb-xl").rglob("*.hea")}
    require(all(i in hm for i in ids),"Missing source headers")
    return np.asarray([parse_source_label(hm[i]) for i in ids],dtype=np.int8)

def choose_threshold(y,p):
    ts=np.arange(.10,.9001,.0025)
    acc=np.asarray([np.mean((p>=t)==y) for t in ts])
    best=np.flatnonzero(acc==acc.max())
    i=sorted(best.tolist(),key=lambda j:(abs(ts[j]-.5),ts[j]))[0]
    return float(ts[i]),float(acc[i])

def train_source(root,outdir):
    ids,X=load_features(outdir/"FEATURES_ptb-xl.npz")
    audit_source_diagnoses(root, ids)
    y=source_labels(root,ids)
    print(f"[labels] binary AF labels: positives={int(y.sum())} negatives={int(len(y)-y.sum())}")
    sp=split_source(ids,y)
    pd.DataFrame({"record_id":ids,"label_af":y,"split":sp}).to_csv(outdir/"SOURCE_SPLIT_ptb-xl.csv",index=False)
    tr=sp=="train"; va=sp=="validation"; hi=sp=="historical"
    require(y[tr].sum()>0 and y[va].sum()>0 and y[hi].sum()>0,"AF positives missing from a source split")
    n0=np.sum(y[tr]==0); n1=np.sum(y[tr]==1)
    sw=np.where(y[tr]==1,0.5/max(n1,1),0.5/max(n0,1))*tr.sum()
    model=HistGradientBoostingClassifier(
        loss="log_loss",learning_rate=.05,max_iter=300,max_leaf_nodes=31,
        min_samples_leaf=20,l2_regularization=1.0,early_stopping=False,random_state=SEED
    )
    print(f"[model] training n={tr.sum()} AF={int(y[tr].sum())}")
    model.fit(X[tr],y[tr],sample_weight=sw)
    pv=model.predict_proba(X[va])[:,1]
    th,val_acc=choose_threshold(y[va],pv)
    ph=model.predict_proba(X[hi])[:,1]
    hp=ph>=th
    model_path=outdir/"SOURCE_MODEL_ptb-xl_AF.joblib"
    joblib.dump(model,model_path,compress=3)
    summary={
        "af_code":AF_CODE,"split_seed":SEED,
        "n_total_eligible":int(len(ids)),"n_af":int(y.sum()),
        "n_train":int(tr.sum()),"n_validation":int(va.sum()),"n_historical":int(hi.sum()),
        "threshold":th,
        "validation_accuracy":val_acc,
        "validation_balanced_accuracy":float(balanced_accuracy_score(y[va],pv>=th)),
        "validation_auc":float(roc_auc_score(y[va],pv)),
        "historical_accuracy_H":float(np.mean(hp==y[hi])),
        "historical_balanced_accuracy":float(balanced_accuracy_score(y[hi],hp)),
        "historical_auc":float(roc_auc_score(y[hi],ph)),
        "model_sha256":sha256_file(model_path),
        "source_split_sha256":sha256_file(outdir/"SOURCE_SPLIT_ptb-xl.csv"),
    }
    (outdir/"SOURCE_SUMMARY.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps(summary,indent=2))
    return summary

def score_target(ds,outdir,model,threshold):
    ids,X=load_features(outdir/f"FEATURES_{ds}.npz")
    p=model.predict_proba(X)[:,1]
    pred=(p>=threshold).astype(np.int8)
    sp=outdir/f"TARGET_SCORES_{ds}.csv"
    pd.DataFrame({"record_id":ids,"score_af":p,"predicted_af":pred}).to_csv(sp,index=False,float_format="%.10g")
    return {
        "dataset":ds,"n":int(len(ids)),
        "score_sha256":sha256_file(sp),
        "roster_sha256":sha256_file(outdir/f"ROSTER_{ds}.csv"),
        "feature_sha256":sha256_file(outdir/f"FEATURES_{ds}.npz"),
    }

def audit_feature_exclusions(outdir: Path):
    """
    Outcome-blind QC of feature-extraction exclusions.
    Only exclusions already implied by the frozen eligibility rule are admissible:
      - not 12 leads
      - waveform shorter than 6 s
    Any other extraction error stops the seal.
    """
    report = {}
    allowed_prefixes = ("ValueError('Expected 12 leads", 'ValueError("Expected 12 leads',
                        "ValueError('record too short", 'ValueError("record too short')
    for ds in ("ptb-xl","georgia","cpsc_2018"):
        p = outdir / f"FEATURE_ERRORS_{ds}.csv"
        if not p.exists():
            report[ds] = {"excluded": 0, "allowed_eligibility_exclusions": 0, "unexpected": 0, "top_errors": []}
            continue
        # v0.2 wrote a zero-byte CSV when a dataset had zero exclusions.
        # Treat that as exactly zero exclusions; do not fail QC.
        if p.stat().st_size == 0:
            report[ds] = {"excluded": 0, "allowed_eligibility_exclusions": 0, "unexpected": 0, "top_errors": []}
            print(f"[feature-QC] {ds}: excluded=0 allowed=0 unexpected=0")
            continue
        try:
            df = pd.read_csv(p)
        except pd.errors.EmptyDataError:
            report[ds] = {"excluded": 0, "allowed_eligibility_exclusions": 0, "unexpected": 0, "top_errors": []}
            print(f"[feature-QC] {ds}: excluded=0 allowed=0 unexpected=0")
            continue
        if df.empty:
            report[ds] = {"excluded": 0, "allowed_eligibility_exclusions": 0, "unexpected": 0, "top_errors": []}
            print(f"[feature-QC] {ds}: excluded=0 allowed=0 unexpected=0")
            continue

        errors = df["error"].fillna("").astype(str)
        allowed = errors.map(lambda s: s.startswith(allowed_prefixes))
        unexpected_df = df.loc[~allowed].copy()
        vc = errors.value_counts().head(10)

        report[ds] = {
            "excluded": int(len(df)),
            "allowed_eligibility_exclusions": int(allowed.sum()),
            "unexpected": int((~allowed).sum()),
            "top_errors": [{"count": int(c), "error": str(e)} for e,c in vc.items()]
        }
        print(f"[feature-QC] {ds}: excluded={len(df)} allowed={int(allowed.sum())} unexpected={int((~allowed).sum())}")
        for e,c in vc.items():
            print(f"[feature-QC]   {c} x {e}")

        require(unexpected_df.empty,
                f"{ds}: {len(unexpected_df)} unexpected feature-extraction errors. "
                f"Inspect {p} before sealing.")

    (outdir/"FEATURE_EXCLUSION_AUDIT.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",required=True)
    ap.add_argument("--workers",type=int,default=8)
    args=ap.parse_args()
    root=Path(args.root).expanduser().resolve()
    outdir=root/"PRESEAL"; sealdir=root/"SEALS"
    outdir.mkdir(parents=True,exist_ok=True); sealdir.mkdir(parents=True,exist_ok=True)
    seal=sealdir/"U10_PREOUTCOME_SEAL.json"
    if seal.exists():
        raise SystemExit(f"Refusing to overwrite existing seal: {seal}")

    print("="*78)
    print(" CMDO U10 ECG PRESEAL PIPELINE v0.3.2 LABELFIX+QC")
    print("="*78)

    audit=audit_download(root)
    print("[audit] exact counts + target .hea absence: PASS")
    print(json.dumps(audit,indent=2))

    for ds in ("ptb-xl","georgia","cpsc_2018"):
        fp=outdir/f"FEATURES_{ds}.npz"
        rp=outdir/f"ROSTER_{ds}.csv"
        if fp.exists() and rp.exists():
            print(f"[features] reusing {fp.name}")
        else:
            extract_dataset(root,ds,outdir,max(1,args.workers))

    feature_exclusion_audit = audit_feature_exclusions(outdir)
    require(not forbidden_target_headers(root),"Target headers appeared during preprocessing.")

    mp=outdir/"SOURCE_MODEL_ptb-xl_AF.joblib"
    sm=outdir/"SOURCE_SUMMARY.json"
    if mp.exists() and sm.exists():
        print("[model] reusing frozen source model")
        summary=json.loads(sm.read_text(encoding="utf-8"))
    else:
        summary=train_source(root,outdir)

    model_hash=sha256_file(mp)
    model=joblib.load(mp)
    target_artifacts=[]
    for ds in ("georgia","cpsc_2018"):
        sp=outdir/f"TARGET_SCORES_{ds}.csv"
        if sp.exists():
            target_artifacts.append({
                "dataset":ds,
                "n":int(pd.read_csv(sp,usecols=["record_id"]).shape[0]),
                "score_sha256":sha256_file(sp),
                "roster_sha256":sha256_file(outdir/f"ROSTER_{ds}.csv"),
                "feature_sha256":sha256_file(outdir/f"FEATURES_{ds}.npz"),
            })
            print(f"[scores] reusing {sp.name}")
        else:
            target_artifacts.append(score_target(ds,outdir,model,float(summary["threshold"])))
            print(f"[scores] frozen waveform-only scores for {ds}")

    require(sha256_file(mp)==model_hash,"Source model changed during target scoring.")
    require(not forbidden_target_headers(root),"Target headers appeared before seal.")

    protocol={
        "schema":"CMDO_U10_PREOUTCOME_SEAL_v0.3.2_LABELFIX_QC",
        "status":"SEALED_PREOUTCOME",
        "created_unix":time.time(),
        "resource":"PhysioNet Challenge 2020 v1.0.2",
        "source":"ptb-xl",
        "targets":["georgia","cpsc_2018"],
        "task":{"label":"AF present vs absent","snomed_ct":AF_CODE,"primary_estimand":"fixed-threshold accuracy"},
        "preprocessing":{
            "sampling_hz":FS,"minimum_duration_s":MIN_SECONDS,"analysis_window_s":WINDOW_SECONDS,
            "long_record_rule":"first 10 s","short_record_rule":"reflect-pad to 10 s for records >=6 s",
            "normalization":"per-record per-lead median/MAD robust standardization","feature_downsample_hz":DS_FS,
            "target_headers_used":False
        },
        "source_development":summary,
        "prospective_evaluation":{
            "budgets":BUDGETS,"replicates_per_budget":REPLICATES,"replicate_seed":SEED,
            "max_borrow_weight":MAX_BORROW_WEIGHT,
            "arms":["same-audit adaptive borrowing","strict 50/50 role separation both orientations","two-fold cross-fitted role allocation"],
            "shared_weight_rule":"w=min(0.35,Vhat/(Vhat+(D-H)^2)); Vhat=max(D(1-D)/m,1e-8)",
            "strict_split_rule":"sensor half computes w; disjoint estimation half computes D; both orientations reported",
            "crossfit_rule":"A computes w_A applied to B; B computes w_B applied to A; average both estimates",
            "primary_mechanistic_prediction":"role separation reduces exact weight-error directional coupling relative to same-audit arm",
            "reporting_rule":"Georgia and CPSC both reported; neither target may be dropped based on outcome"
        },
        "target_artifacts":target_artifacts,
        "download_audit":audit,
        "feature_exclusion_audit":feature_exclusion_audit,
        "code":{"preseal_script_sha256":sha256_file(Path(__file__).resolve()),"python":sys.version,"platform":platform.platform()}
    }
    seal.write_text(json.dumps(protocol,indent=2,sort_keys=True),encoding="utf-8")
    sh=sha256_file(seal)
    (sealdir/"U10_PREOUTCOME_SEAL.sha256").write_text(f"{sh}  U10_PREOUTCOME_SEAL.json\n",encoding="utf-8")
    print("="*78)
    print(" U10 PREOUTCOME SEAL COMPLETE")
    print(f" Seal: {seal}")
    print(f" SHA256: {sh}")
    print(" Georgia/CPSC .hea files remain absent.")
    print("="*78)

if __name__=="__main__":
    warnings.filterwarnings("ignore",category=RuntimeWarning)
    main()
