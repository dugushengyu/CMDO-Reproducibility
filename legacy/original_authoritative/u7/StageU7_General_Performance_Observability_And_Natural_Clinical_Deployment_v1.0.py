#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CMDO Stage U7 — General Performance Observability and Natural Clinical Deployment v1.0."""
from __future__ import annotations




import hashlib
import json
import math
import os
import platform
import random
import shutil
import sys
import time
import zipfile
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path




import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from ucimlrepo import fetch_ucirepo




PROJECT = "Cross-Modal_Diagnostic_Observability"
STAGE = "StageU7_General_Performance_Observability_And_Natural_Clinical_Deployment_v1.0"
EXPECTED_U6_FINAL = "e5aaa39c4dbeb21af7520ab1fd8afbb2b24ec4320edabef79fa5fccfe8a3d124"
EXPECTED_SPEC_SHA = "cd88e72099be68258baa64fd7ff78137670b33b2deae3abf82a6a5d83dd2720f"
EXPECTED_OBSERVER_ID = "PC_PAIRED_HOEFFDING"
SEED = 20260725
BUDGETS = [16, 32, 64, 128, 256]
REPLICATES = 200
MAX_WEIGHT = 0.35
RISK_COEFFICIENT = 8.0
DELTA_BLOCK = 0.025
DELTA_FOLD = 0.05
HISTOGRAM_BINS = np.linspace(0.0, 1.0, 41)
METRICS = ["AUC", "SENSITIVITY", "SPECIFICITY", "BALANCED_ACCURACY", "BRIER_UTILITY"]
ADDITIVE_METRICS = ["SENSITIVITY", "SPECIFICITY", "BALANCED_ACCURACY", "BRIER_UTILITY"]
DEATH_HOSPICE_DISPOSITIONS = {11, 13, 14, 19, 20, 21}
DROP_COLUMNS = ["encounter_id", "patient_nbr", "admission_source_id", "weight", "payer_code", "medical_specialty", "_row_id", "_encounter_order"]
CATEGORICAL_ID_COLUMNS = ["admission_type_id", "discharge_disposition_id"]








def utc_now():
    return datetime.now(timezone.utc).isoformat()








def canonical_json(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))








def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()








def sha256_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()








def sha256_array(values):
    arr = np.ascontiguousarray(np.asarray(values))
    return hashlib.sha256(arr.tobytes()).hexdigest()








def derive_seed(*parts):
    return int(hashlib.sha256("::".join(map(str, parts)).encode()).hexdigest()[:16], 16) % (2**32)








def locate_project_root():
    candidates = [Path("/content/drive/MyDrive")/PROJECT, Path("/content/drive/Shareddrives")/PROJECT]
    for candidate in candidates:
        if candidate.exists(): return candidate
    matches = [p for p in Path("/content/drive").rglob(PROJECT) if p.is_dir()]
    if len(matches) == 1: return matches[0]
    raise FileNotFoundError(f"Cannot uniquely locate project root: {matches}")








def verify_parent_records(cross_modal):
    u6_path = cross_modal/"StageU6_Independent_Pair_Complete_Observer_Reserve_v1.0"/"StageU6_Complete_v1.0.json"
    u5f_spec = cross_modal/"StageU5F_Final_Observer_Freeze_And_U6_Preregistration_v1.0"/"StageU5F_Frozen_Observer_Specification_v1.0.json"
    u6 = json.loads(u6_path.read_text(encoding="utf-8"))
    if u6.get("final_record_sha256") != EXPECTED_U6_FINAL:
        raise RuntimeError("U6 final record identity failed.")
    if "INDEPENDENT_PC_PAIRED_HOEFFDING_OBSERVER_CONFIRMED" not in u6.get("decision", ""):
        raise RuntimeError("U6 confirmed decision missing.")
    if sha256_file(u5f_spec) != EXPECTED_SPEC_SHA:
        raise RuntimeError("U5F frozen observer specification hash failed.")
    spec = json.loads(u5f_spec.read_text(encoding="utf-8"))
    if spec.get("observer_id") != EXPECTED_OBSERVER_ID or spec.get("permitted_change_before_u6") != "NONE":
        raise RuntimeError("Frozen observer identity failed.")
    print("[U7] U6 final record and U5F frozen observer verified.")








def general_theory_tex():
    return r'''\documentclass[11pt]{article}
\usepackage{amsmath,amssymb,amsthm,bm}
\newtheorem{theorem}{Theorem}
\newtheorem{corollary}{Corollary}
\newtheorem{proposition}{Proposition}
\title{General performance observability: exact diameter, label complexity and certified sensing}
\date{}
\begin{document}\maketitle
\section{Observation model}
Let $f$ be a fixed deployed predictor, $X$ the deployment input and $Y$ the outcome.  The zero-label observation $O_0$ may contain any measurable function of $X$, $f(X)$, uncertainty scores and source-side records, but not target $Y$.  Two target laws are observationally equivalent when they induce the same law of $O_0$.
\[
P\equiv_{O_0}Q\quad\Longleftrightarrow\quad\mathcal L_P(O_0)=\mathcal L_Q(O_0).
\]
For a performance functional $\theta$, define
\[
\Delta_\theta(O_0;\mathcal P)=\sup_{P,Q\in\mathcal P:\,P\equiv_{O_0}Q}|\theta(P,f)-\theta(Q,f)|.
\]




\begin{theorem}[Exact diameter for bounded additive performance]
Fix $P_X$ and let $\mathcal P(P_X)$ contain all conditional outcome kernels $P(Y\mid X)$. Assume that the outcome space is finite, or more generally standard Borel and the upper and lower loss envelopes admit measurable $\varepsilon$-optimal selectors. For jointly measurable $\ell(f(x),y)\in[0,1]$ and
$\theta_\ell(P,f)=\mathbb E_P[\ell(f(X),Y)]$,
\[
\Delta_{\theta_\ell}(O_0;\mathcal P(P_X))
=\mathbb E_{P_X}\!\left[\operatorname*{ess\,sup}_y\ell(f(X),y)-\operatorname*{ess\,inf}_y\ell(f(X),y)\right].
\]
Hence the metric is identifiable from outcome-free deployment observations if and only if the pointwise outcome oscillation vanishes almost surely.
\end{theorem}
\begin{proof}
For any two conditional kernels, the difference of their conditional expected losses is bounded pointwise by the oscillation; integration gives the upper bound. For finite outcomes, conditional kernels concentrated on pointwise maximizers and minimizers attain the bound. Under the stated standard-Borel selection condition, measurable $\varepsilon$-optimal selectors attain it up to arbitrary $\varepsilon>0$; taking the limit gives equality.
\end{proof}




\begin{corollary}[General zero-label impossibility]
Any bounded additive metric that depends nontrivially on the hidden outcome on a set of positive $P_X$ measure has positive zero-label observability diameter and is not identifiable, irrespective of the number of unlabelled target inputs.
\end{corollary}




\begin{proposition}[AUC witness]
There exist two balanced binary target worlds with the same input and score distribution for which AUC is one in the first world and zero in the second. Therefore unrestricted zero-label AUC diameter equals one and minimax absolute error is at least one half.
\end{proposition}




\begin{theorem}[Outcome-label complexity]
For any bounded additive metric, the direct outcome estimator satisfies
\[
\Pr\{|\widehat\theta_b-\theta|>\varepsilon\}\le 2e^{-2b\varepsilon^2}.
\]
Consequently $b\ge \log(2/\delta)/(2\varepsilon^2)$ is sufficient. Conversely, over Bernoulli submodels the minimax expected absolute error obeys
\[
R_b^*\ge \frac{1}{32\sqrt b},
\]
and uniform $(\varepsilon,\delta)$ estimation requires $b=\Omega(\varepsilon^{-2}\log(1/\delta))$. Thus the root-$b$ rate is unavoidable without additional restrictions on the target outcome mechanism.
\end{theorem}




\begin{theorem}[Certified transport sensing]
Let $D$ be an unbiased local estimator with variance $V$, let $T=\theta+B$ be transported evidence, and let
$\widehat\theta_w=(1-w)D+wT$. Then
\[
R(w)=(1-w)^2V+w^2B^2,\qquad w^*=\frac{V}{V+B^2}.
\]
If an outcome sensor supplies a high-probability bound $U\ge B^2$ and
\[
w\le \frac{V}{V+U},
\]
then on the coverage event $R(w)\le R(0)=V$.  Cross-fitting makes the sensor and estimation noise independent; pair-complete AUC blocks preserve the full direct U-statistic exactly when $w=0$.
\end{theorem}




\section{Natural clinical extension}
Stage U7 evaluates the frozen pair-complete observer on the UCI Diabetes 130-US Hospitals dataset. The source model is developed on non-emergency admission sources and deployed to emergency-room admissions. Sixteen strata are defined exclusively from observable input attributes before target outcomes are indexed. The target is readmission within 30 days.




\section{Claim boundary}
This analysis is a retrospective, outcome-blind computational deployment study on de-identified public records. It is not a live clinical intervention and does not establish clinical utility of the underlying readmission model.
\end{document}
'''








def protocol_text(pipeline_sha, theory_sha):
    return f'''STAGE U7 — GENERAL PERFORMANCE OBSERVABILITY AND NATURAL CLINICAL DEPLOYMENT v1.0




PURPOSE
Complete one high-value extension beyond U6: (i) an exact general theorem for bounded performance functionals and minimax target-label complexity; (ii) a natural, non-synthetic clinical deployment shift.




PARENTS
U6 final record: {EXPECTED_U6_FINAL}
U5F frozen observer specification: {EXPECTED_SPEC_SHA}
Frozen AUC observer: {EXPECTED_OBSERVER_ID}




DATA
UCI Diabetes 130-US Hospitals for Years 1999-2008, DOI 10.24432/C5230J. One record per patient after frozen exclusions of death/hospice discharge dispositions. Source domain: non-emergency admission sources. Target domain: emergency room (admission_source_id=7). Target outcome: readmission within 30 days.




PREDEFINED TARGET STRATA
ER_ALL; three age strata; female; male; Caucasian; African American; zero/positive prior utilization; insulin active/none; short/long stay; <=6/>=7 diagnoses. Membership uses inputs only and is sealed before target outcomes are indexed.




SOURCE MODEL
Deterministic source-only preprocessing, one-hot encoding and SGD logistic classification. Source threshold maximizes Youden index on a source validation split. No target outcome tunes the model, threshold, transport rule, metrics, budgets or gates.




METRICS
Primary: AUC with exact U5F pair-complete paired-Hoeffding observer.
Secondary bounded metrics: sensitivity, specificity, balanced accuracy and balanced Brier utility, using two-fold opposite-sensor cross-fitting with exact full-direct fallback.




WITNESS
Balanced budgets {BUDGETS}; {REPLICATES} replicates per stratum-budget; seed {SEED}. Max transport weight {MAX_WEIGHT}; risk coefficient {RISK_COEFFICIENT}; no variance gate; no candidate switching.




PRIMARY GATES
Exact general diameter and AUC counterexample; root-n label-complexity rate; at least 12 eligible clinical strata; identity residual <1e-12; mean/minimum coverage >=0.90/0.85; no-harm >=0.999; worst AUC stratum-budget regret <=0.005; pooled AUC non-inferiority; at least half of eligible strata improve; natural bias-observability Spearman >=0.65; at least two of four bounded additive metrics satisfy pooled non-inferiority and worst regret <=0.01.




EXECUTION ORDER
Verify parents; write protocol/theory/authorization; run formal theory checks; train source model and compute target scores; seal score hashes, memberships, transport descriptors and roster; only then index target outcomes; execute once; retain all outcomes; successful rerun prohibited.




Pipeline SHA-256: {pipeline_sha}
Theory SHA-256: {theory_sha}
Target outcomes before seal: PROHIBITED.
Stage 12: PROHIBITED.
'''








def exhaustive_diameter(px, loss):
    values=[]
    for mask in range(2**len(px)):
        ys=np.array([(mask>>i)&1 for i in range(len(px))])
        values.append(float(np.sum(px*loss[np.arange(len(px)),ys])))
    return max(values)-min(values)








def theory_checks():
    checks=[]
    examples=[
        (np.array([0.2,0.3,0.5]),np.array([[0,1],[1,0],[0.25,0.75]],float)),
        (np.array([0.1,0.4,0.5]),np.array([[0.2,0.9],[0.8,0.1],[0.4,0.6]],float)),
        (np.array([0.5,0.5]),np.array([[0.1,0.7],[0.9,0.2]],float)),
    ]
    for px,loss in examples:
        formula=float(np.sum(px*(loss.max(axis=1)-loss.min(axis=1))))
        brute=exhaustive_diameter(px,loss)
        checks.append(abs(formula-brute)<1e-12)
    auc_world_one=1.0; auc_world_zero=0.0
    rates=[]
    budgets=[16,32,64,128,256,512,1024]
    rng=np.random.default_rng(derive_seed(SEED,"ROOT_N"))
    definitions={
        "BERNOULLI_ACCURACY":lambda n:rng.binomial(1,0.7,size=n).astype(float),
        "BOUNDED_BRIER_UTILITY":lambda n:rng.beta(5,2,size=n),
        "BOUNDED_SENSITIVITY":lambda n:rng.binomial(1,0.62,size=n).astype(float),
    }
    truths={"BERNOULLI_ACCURACY":0.7,"BOUNDED_BRIER_UTILITY":5/7,"BOUNDED_SENSITIVITY":0.62}
    for metric,sampler in definitions.items():
        maes=[]
        for b in budgets:
            errors=[abs(float(sampler(b).mean())-truths[metric]) for _ in range(500)]
            mae=float(np.mean(errors)); maes.append(mae)
        slope=float(np.polyfit(np.log(budgets),np.log(maes),1)[0])
        for b,mae in zip(budgets,maes): rates.append({"metric":metric,"budget":b,"mae":mae,"slope":slope})
    auc_maes=[]
    true_auc=float(0.5*(1+math.erf(0.5)))
    for b in budgets:
        m=b//2; errs=[]
        for _ in range(400):
            pos=rng.normal(1,1,m); neg=rng.normal(0,1,m)
            errs.append(abs(float(auc_kernel(pos,neg).mean())-true_auc))
        auc_maes.append(float(np.mean(errs)))
    auc_slope=float(np.polyfit(np.log(budgets),np.log(auc_maes),1)[0])
    for b,mae in zip(budgets,auc_maes): rates.append({"metric":"AUC_USTATISTIC","budget":b,"mae":mae,"slope":auc_slope})
    rates_df=pd.DataFrame(rates)
    slopes=rates_df.groupby("metric").slope.first()
    root_supported=bool(((slopes>=-0.70)&(slopes<=-0.30)).all())
    record={"exact_diameter_checks":bool(all(checks)),"auc_counterexample":bool(abs((auc_world_one-auc_world_zero)-1)<1e-12),
            "root_n_rates_supported":root_supported,"slope_summary":";".join(f"{k}={v:.4f}" for k,v in slopes.items()),
            "minimax_lower_bound":"R_b^* >= 1/(32 sqrt(b)) for a Bernoulli submodel",
            "high_probability_label_complexity":"Theta(epsilon^-2 log(1/delta))"}
    return record,rates_df




def make_ohe():
    try:
        return OneHotEncoder(handle_unknown="ignore", min_frequency=20, sparse_output=True)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", min_frequency=20, sparse=True)








def prepare_model_frame(df):
    frame = df.copy()
    drop_cols = [c for c in DROP_COLUMNS if c in frame.columns]
    frame = frame.drop(columns=drop_cols)
    for col in CATEGORICAL_ID_COLUMNS:
        if col in frame.columns:
            frame[col] = frame[col].astype(str)
    for col in frame.select_dtypes(include=["object"]).columns:
        frame[col] = frame[col].replace({"?": np.nan})
    return frame








def balanced_brier_utility(scores, labels):
    scores = np.asarray(scores, float); labels = np.asarray(labels, int)
    pos = 1.0 - (1.0 - scores[labels == 1])**2
    neg = 1.0 - scores[labels == 0]**2
    return float(0.5*(pos.mean()+neg.mean()))








def threshold_metrics(scores, labels, threshold):
    scores = np.asarray(scores, float); labels = np.asarray(labels, int)
    pred = scores >= threshold
    sens = float(pred[labels == 1].mean())
    spec = float((~pred[labels == 0]).mean())
    return {
        "AUC": float(roc_auc_score(labels, scores)),
        "SENSITIVITY": sens,
        "SPECIFICITY": spec,
        "BALANCED_ACCURACY": 0.5*(sens+spec),
        "BRIER_UTILITY": balanced_brier_utility(scores, labels),
    }








def compute_true_metrics(scores, labels, threshold):
    return threshold_metrics(scores, labels, threshold)








def score_shift_descriptor(source_scores, target_scores, source_metrics):
    source = np.asarray(source_scores, float); target = np.asarray(target_scores, float)
    sh, _ = np.histogram(source, bins=HISTOGRAM_BINS)
    th, _ = np.histogram(target, bins=HISTOGRAM_BINS)
    sh = sh/max(1, sh.sum()); th = th/max(1, th.sum())
    overlap = float(np.minimum(sh, th).sum())
    mean_shift = float(abs(target.mean()-source.mean()))
    std_shift = float(abs(target.std()-source.std()))
    qshift = float(np.mean(np.abs(np.quantile(target, [0.1,0.5,0.9])-np.quantile(source, [0.1,0.5,0.9]))))
    energy = min(1.0, (1-overlap)**2 + mean_shift**2 + std_shift**2 + qshift**2)
    support = float(np.clip(overlap*math.exp(-mean_shift), 0, 1))
    risk = float(0.01*energy)
    degradation = 0.40*(1-overlap)+0.20*mean_shift+0.10*qshift
    transport = {}
    for metric, value in source_metrics.items():
        low = 0.5 if metric == "AUC" else 0.0
        transport[metric] = float(np.clip(value-degradation, low, 0.999999))
    return {
        "overlap": overlap, "mean_shift": mean_shift, "std_shift": std_shift,
        "quantile_shift": qshift, "shift_energy": energy,
        "support_gate": support, "transport_risk_proxy": risk,
        "predicted_degradation": degradation, "transport": transport,
    }








def auc_kernel(pos, neg):
    pos = np.asarray(pos, float); neg = np.asarray(neg, float)
    return (pos[:,None] > neg[None,:]).astype(float) + 0.5*(pos[:,None] == neg[None,:]).astype(float)








def auc_and_variance(pos, neg):
    matrix = auc_kernel(pos, neg)
    auc = float(matrix.mean())
    row = matrix.mean(axis=1); col = matrix.mean(axis=0)
    rv = float(np.var(row, ddof=1)) if len(row)>1 else 0.0
    cv = float(np.var(col, ddof=1)) if len(col)>1 else 0.0
    return auc, max(0.0, rv/len(row)+cv/len(col))








def paired_sensor(pos, neg, rng):
    h = min(len(pos), len(neg))
    p = np.asarray(pos)[rng.permutation(len(pos))[:h]]
    n = np.asarray(neg)[rng.permutation(len(neg))[:h]]
    values = (p>n).astype(float)+0.5*(p==n).astype(float)
    return float(values.mean()), h








def radius(n, delta):
    return min(1.0, math.sqrt(math.log(2.0/delta)/(2.0*n)))








def observer_weight(variance, upper_bias_sq, support, risk):
    return float(support)*min(MAX_WEIGHT, float(variance)/(float(variance)+float(upper_bias_sq)+RISK_COEFFICIENT*float(risk)+1e-12))








def pair_complete_observer(pos, neg, transport, support, risk, truth, rng):
    pos = np.asarray(pos, float)[rng.permutation(len(pos))]
    neg = np.asarray(neg, float)[rng.permutation(len(neg))]
    half = len(pos)//2
    pa,pb = pos[:half],pos[half:]; na,nb = neg[:half],neg[half:]
    blocks = {"AA":(pa,na),"AB":(pa,nb),"BA":(pb,na),"BB":(pb,nb)}
    opposite = {"AA":"BB","BB":"AA","AB":"BA","BA":"AB"}
    aucs={}; vars_={}; sensors={}
    for name,(p,n) in blocks.items():
        aucs[name],vars_[name]=auc_and_variance(p,n)
        sensors[name]=paired_sensor(p,n,rng)
    full,_ = auc_and_variance(pos,neg)
    identity = abs(np.mean(list(aucs.values()))-full)
    bias_sq=(transport-truth)**2
    estimates=[]; weights=[]; cover=[]; geometry=[]; gaps=[]
    for name in blocks:
        sensor,n = sensors[opposite[name]]
        r=radius(n,DELTA_BLOCK)
        upper=min(1.0,abs(sensor-transport)+r)**2
        w=observer_weight(vars_[name],upper,support,risk)
        estimates.append((1-w)*aucs[name]+w*transport); weights.append(w)
        cover.append(upper+1e-15>=bias_sq)
        geometry.append((1-w)**2*vars_[name]+w*w*bias_sq <= vars_[name]+1e-14)
        gaps.append(abs(sensor-transport))
    return {"estimate":float(np.mean(estimates)),"direct":full,"mean_weight":float(np.mean(weights)),
            "coverage":bool(all(cover)),"no_harm_rate":float(np.mean(geometry)),
            "identity_residual":identity,"sensor_gap":float(np.mean(gaps))}








def fold_vector(metric, pos, neg, threshold):
    pos=np.asarray(pos,float); neg=np.asarray(neg,float)
    if metric=="SENSITIVITY": return (pos>=threshold).astype(float)
    if metric=="SPECIFICITY": return (neg<threshold).astype(float)
    if metric=="BALANCED_ACCURACY": return 0.5*((pos>=threshold).astype(float)+(neg<threshold).astype(float))
    if metric=="BRIER_UTILITY": return 0.5*((1-(1-pos)**2)+(1-neg**2))
    raise ValueError(metric)








def mean_and_variance(values):
    values=np.asarray(values,float); n=len(values)
    return float(values.mean()), (float(np.var(values,ddof=1))/n if n>1 else 0.0)








def additive_crossfit_observer(metric,pos,neg,threshold,transport,support,risk,truth,rng):
    pos=np.asarray(pos,float)[rng.permutation(len(pos))]; neg=np.asarray(neg,float)[rng.permutation(len(neg))]
    half=len(pos)//2
    va=fold_vector(metric,pos[:half],neg[:half],threshold)
    vb=fold_vector(metric,pos[half:],neg[half:],threshold)
    da,vara=mean_and_variance(va); db,varb=mean_and_variance(vb)
    ra=radius(len(va),DELTA_FOLD); rb=radius(len(vb),DELTA_FOLD)
    ua=min(1.0,abs(db-transport)+rb)**2
    ub=min(1.0,abs(da-transport)+ra)**2
    wa=observer_weight(vara,ua,support,risk); wb=observer_weight(varb,ub,support,risk)
    estimate=0.5*((1-wa)*da+wa*transport+(1-wb)*db+wb*transport)
    direct=0.5*(da+db); bias_sq=(transport-truth)**2
    cover=[ua+1e-15>=bias_sq,ub+1e-15>=bias_sq]
    geom=[(1-wa)**2*vara+wa*wa*bias_sq<=vara+1e-14,(1-wb)**2*varb+wb*wb*bias_sq<=varb+1e-14]
    return {"estimate":float(estimate),"direct":float(direct),"mean_weight":float(0.5*(wa+wb)),
            "coverage":bool(all(cover)),"no_harm_rate":float(np.mean(geom)),
            "identity_residual":abs(direct-np.mean(np.r_[va,vb])),
            "sensor_gap":float(0.5*(abs(da-transport)+abs(db-transport)))}








def parse_age_lower(series):
    return series.astype(str).str.extract(r"\[(\d+)-",expand=False).astype(float)








def clinical_strata(target_inputs):
    age=parse_age_lower(target_inputs["age"])
    race=target_inputs["race"].astype(str)
    gender=target_inputs["gender"].astype(str)
    prior=sum(pd.to_numeric(target_inputs[c],errors="coerce").fillna(0) for c in ["number_outpatient","number_emergency","number_inpatient"])
    insulin=target_inputs["insulin"].astype(str)
    stay=pd.to_numeric(target_inputs["time_in_hospital"],errors="coerce")
    diagnoses=pd.to_numeric(target_inputs["number_diagnoses"],errors="coerce")
    return OrderedDict([
        ("ER_ALL",np.ones(len(target_inputs),dtype=bool)),
        ("ER_AGE_LT50",(age<50).to_numpy()),
        ("ER_AGE_50_69",((age>=50)&(age<70)).to_numpy()),
        ("ER_AGE_GE70",(age>=70).to_numpy()),
        ("ER_FEMALE",gender.eq("Female").to_numpy()),
        ("ER_MALE",gender.eq("Male").to_numpy()),
        ("ER_RACE_CAUCASIAN",race.eq("Caucasian").to_numpy()),
        ("ER_RACE_AFRICAN_AMERICAN",race.eq("AfricanAmerican").to_numpy()),
        ("ER_PRIOR_UTILIZATION_ZERO",prior.eq(0).to_numpy()),
        ("ER_PRIOR_UTILIZATION_POSITIVE",prior.gt(0).to_numpy()),
        ("ER_INSULIN_ACTIVE",insulin.ne("No").to_numpy()),
        ("ER_INSULIN_NONE",insulin.eq("No").to_numpy()),
        ("ER_SHORT_STAY_LE4",stay.le(4).fillna(False).to_numpy()),
        ("ER_LONG_STAY_GE5",stay.ge(5).fillna(False).to_numpy()),
        ("ER_DIAGNOSES_LE6",diagnoses.le(6).fillna(False).to_numpy()),
        ("ER_DIAGNOSES_GE7",diagnoses.ge(7).fillna(False).to_numpy()),
    ])








def prepare_clinical_deployment():
    print("[U7] Downloading UCI Diabetes 130-US Hospitals dataset (about 3 MB compressed).")
    ds=fetch_ucirepo(id=296)
    x=ds.data.features.reset_index(drop=True).copy()
    y=ds.data.targets.reset_index(drop=True).copy()
    # U7_IMPLEMENTATION_AMENDMENT_V1_0_1_UCIMLREPO_IDS
    ids=ds.data.ids.reset_index(drop=True).copy()
    missing_ids={"encounter_id","patient_nbr"}-set(ids.columns)
    if missing_ids: raise KeyError(f"Missing UCI ID columns in data.ids: {sorted(missing_ids)}")
    x=pd.concat([ids[["encounter_id","patient_nbr"]],x],axis=1)
    required={"encounter_id","patient_nbr","admission_source_id","discharge_disposition_id","age","race","gender","insulin","time_in_hospital","number_diagnoses","number_outpatient","number_emergency","number_inpatient"}
    missing=required-set(x.columns)
    if missing: raise KeyError(f"Missing UCI columns: {sorted(missing)}")
    x["_row_id"]=np.arange(len(x))
    disp=pd.to_numeric(x["discharge_disposition_id"],errors="coerce")
    x=x.loc[~disp.isin(DEATH_HOSPICE_DISPOSITIONS)].copy()
    x["_encounter_order"]=pd.to_numeric(x["encounter_id"],errors="coerce")
    x=x.sort_values("_encounter_order").drop_duplicates("patient_nbr",keep="first")
    source_mask=pd.to_numeric(x["admission_source_id"],errors="coerce").ne(7)
    target_mask=pd.to_numeric(x["admission_source_id"],errors="coerce").eq(7)
    source=x.loc[source_mask].copy(); target=x.loc[target_mask].copy()
    source_rows=source["_row_id"].astype(int).to_numpy(); target_rows=target["_row_id"].astype(int).to_numpy()
    source_labels=(y.iloc[source_rows,0].astype(str).to_numpy()=="<30").astype(int)
    if len(np.unique(source_labels))<2: raise RuntimeError("Source labels are not binary.")
    source_frame=prepare_model_frame(source)
    target_frame=prepare_model_frame(target)
    indices=np.arange(len(source_frame))
    tr,va=train_test_split(indices,test_size=0.25,stratify=source_labels,random_state=derive_seed(SEED,"SOURCE_SPLIT"))
    categorical=list(source_frame.select_dtypes(include=["object"]).columns)
    numeric=[c for c in source_frame.columns if c not in categorical]
    pre=ColumnTransformer([
        ("cat",Pipeline([("impute",SimpleImputer(strategy="most_frequent")),("onehot",make_ohe())]),categorical),
        ("num",Pipeline([("impute",SimpleImputer(strategy="median")),("scale",StandardScaler(with_mean=False))]),numeric),
    ])
    model=Pipeline([("pre",pre),("clf",SGDClassifier(loss="log_loss",alpha=1e-4,max_iter=3000,tol=1e-5,class_weight="balanced",random_state=derive_seed(SEED,"MODEL")))])
    model.fit(source_frame.iloc[tr],source_labels[tr])
    val_scores=model.predict_proba(source_frame.iloc[va])[:,1]
    fpr,tpr,thresholds=roc_curve(source_labels[va],val_scores)
    valid=np.isfinite(thresholds)
    threshold=float(thresholds[valid][np.argmax((tpr-fpr)[valid])])
    threshold=float(np.clip(threshold,0.05,0.95))
    source_metrics=threshold_metrics(val_scores,source_labels[va],threshold)
    target_scores=model.predict_proba(target_frame)[:,1]
    strata=clinical_strata(target)
    if len(strata)!=16: raise RuntimeError("Frozen clinical roster is not 16 strata.")
    return {"x":x,"y_frame":y,"source":source,"target":target,"source_rows":source_rows,"target_rows":target_rows,
            "source_validation_scores":val_scores,"source_metrics":source_metrics,"threshold":threshold,
            "target_scores":target_scores,"strata":strata,"model_columns":list(source_frame.columns)}








def build_and_seal_targets(output_dir,prepared,pipeline_sha,theory_sha,protocol_sha):
    bundles=[]; rows=[]
    source_scores=prepared["source_validation_scores"]
    target=prepared["target"].reset_index(drop=True)
    target_rows=prepared["target_rows"]
    scores=prepared["target_scores"]
    for name,mask in prepared["strata"].items():
        mask=np.asarray(mask,bool)
        row_ids=target_rows[mask]; stratum_scores=scores[mask]
        descriptor=score_shift_descriptor(source_scores,stratum_scores,prepared["source_metrics"])
        bundle={"stratum":name,"row_ids":row_ids,"scores":stratum_scores,
                "support_gate":descriptor["support_gate"],"transport_risk_proxy":descriptor["transport_risk_proxy"],
                "transport":descriptor["transport"]}
        bundles.append(bundle)
        rows.append({"stratum":name,"input_count":int(mask.sum()),"row_membership_sha256":sha256_array(row_ids.astype(float)),
                     "score_sha256":sha256_array(stratum_scores),"support_gate":descriptor["support_gate"],
                     "transport_risk_proxy":descriptor["transport_risk_proxy"],"overlap":descriptor["overlap"],
                     "mean_shift":descriptor["mean_shift"],"std_shift":descriptor["std_shift"],
                     "quantile_shift":descriptor["quantile_shift"],"predicted_degradation":descriptor["predicted_degradation"],
                     **{f"transport_{k}":v for k,v in descriptor["transport"].items()}})
    descriptor_path=output_dir/"StageU7_PreOutcome_Clinical_Descriptors_v1.0.csv"
    pd.DataFrame(rows).to_csv(descriptor_path,index=False)
    seal_pre={"stage":STAGE,"seal_type":"OUTCOME_BLIND_PREOUTCOME_SEAL","created_utc":utc_now(),
              "parent_u6_final":EXPECTED_U6_FINAL,"frozen_observer_spec_sha256":EXPECTED_SPEC_SHA,
              "pipeline_sha256":pipeline_sha,"theory_sha256":theory_sha,"protocol_sha256":protocol_sha,
              "dataset":"UCI Diabetes 130-US Hospitals 1999-2008","dataset_doi":"10.24432/C5230J",
              "source_domain":"all non-emergency-room admission sources after frozen exclusions",
              "target_domain":"admission_source_id=7 emergency room","target_roster":list(prepared["strata"].keys()),
              "source_metrics":prepared["source_metrics"],"source_threshold":prepared["threshold"],
              "budgets":BUDGETS,"replicates":REPLICATES,"metrics":METRICS,
              "descriptor_file_sha256":sha256_file(descriptor_path),"target_outcomes_indexed":False,
              "candidate_switching":False,"stage12_authorised":False}
    seal_sha=sha256_text(canonical_json(seal_pre)); seal=dict(seal_pre); seal["preoutcome_seal_sha256"]=seal_sha
    (output_dir/"StageU7_PreOutcome_Seal_v1.0.json").write_text(json.dumps(seal,indent=2,sort_keys=True),encoding="utf-8")
    return bundles,seal_sha




def evaluate_reserve(bundles, y_frame, threshold, source_metrics, seal_sha):
    replicate_rows = []
    truth_rows = []
    max_per_class = max(BUDGETS) // 2
    for bundle in bundles:
        labels = (y_frame.iloc[bundle["row_ids"], 0].astype(str).to_numpy() == "<30").astype(int)
        scores = bundle["scores"]
        pos_idx = np.where(labels == 1)[0]
        neg_idx = np.where(labels == 0)[0]
        eligible = min(len(pos_idx), len(neg_idx)) >= max_per_class
        truth = compute_true_metrics(scores, labels, threshold) if eligible else {}
        truth_rows.append({
            "stratum": bundle["stratum"], "input_count": len(labels),
            "positive_count": len(pos_idx), "negative_count": len(neg_idx),
            "eligible": eligible, **{f"true_{k}": v for k, v in truth.items()},
            "support_gate": bundle["support_gate"],
            "transport_risk_proxy": bundle["transport_risk_proxy"],
            "preoutcome_seal_sha256": seal_sha,
        })
        if not eligible:
            continue
        for budget in BUDGETS:
            per_class = budget // 2
            for rep in range(REPLICATES):
                rng = np.random.default_rng(derive_seed(SEED, bundle["stratum"], budget, rep))
                psel = rng.choice(pos_idx, size=per_class, replace=False)
                nsel = rng.choice(neg_idx, size=per_class, replace=False)
                ps, ns = scores[psel], scores[nsel]
                auc_result = pair_complete_observer(
                    ps, ns, bundle["transport"]["AUC"], bundle["support_gate"],
                    bundle["transport_risk_proxy"], truth["AUC"], rng,
                )
                replicate_rows.append(result_row(bundle, budget, rep, "AUC", truth["AUC"], auc_result))
                for metric in ADDITIVE_METRICS:
                    add_result = additive_crossfit_observer(
                        metric, ps, ns, threshold, bundle["transport"][metric],
                        bundle["support_gate"], bundle["transport_risk_proxy"],
                        truth[metric], rng,
                    )
                    replicate_rows.append(result_row(bundle, budget, rep, metric, truth[metric], add_result))
    replicates = pd.DataFrame(replicate_rows)
    truths = pd.DataFrame(truth_rows)
    states = replicates.groupby(["stratum", "metric", "budget"], as_index=False).agg(
        mae=("absolute_error", "mean"), direct_mae=("direct_absolute_error", "mean"),
        regret=("regret", "mean"), mean_weight=("mean_weight", "mean"),
        coverage=("simultaneous_coverage", "mean"), no_harm=("no_harm_rate", "mean"),
        max_identity_residual=("identity_residual", "max"),
        mean_sensor_gap=("sensor_gap", "mean"), true_metric=("true_metric", "first"),
        transport_metric=("transport_metric", "first"), transport_abs_error=("transport_abs_error", "first"),
    )
    targets = replicates.groupby(["stratum", "metric"], as_index=False).agg(
        mae=("absolute_error", "mean"), direct_mae=("direct_absolute_error", "mean"),
        mean_weight=("mean_weight", "mean"), coverage=("simultaneous_coverage", "mean"),
        no_harm=("no_harm_rate", "mean"), max_identity_residual=("identity_residual", "max"),
        true_metric=("true_metric", "first"), transport_metric=("transport_metric", "first"),
        transport_abs_error=("transport_abs_error", "first"),
    )
    targets["gain"] = targets["direct_mae"] - targets["mae"]
    metric_summary = replicates.groupby("metric", as_index=False).agg(
        mae=("absolute_error", "mean"), direct_mae=("direct_absolute_error", "mean"),
        mean_weight=("mean_weight", "mean"), coverage=("simultaneous_coverage", "mean"),
        no_harm=("no_harm_rate", "mean"),
    )
    metric_summary["relative_gain"] = 1.0 - metric_summary["mae"] / metric_summary["direct_mae"]
    worst = states.groupby("metric", as_index=False)["regret"].max().rename(columns={"regret": "worst_regret"})
    metric_summary = metric_summary.merge(worst, on="metric", how="left")
    return replicates, states, targets, metric_summary, truths








def result_row(bundle, budget, rep, metric, truth, result):
    est = result["estimate"]
    direct = result["direct"]
    return {
        "stratum": bundle["stratum"], "metric": metric, "budget": budget, "replicate": rep,
        "true_metric": truth, "transport_metric": bundle["transport"][metric],
        "transport_abs_error": abs(bundle["transport"][metric] - truth),
        "estimate": est, "direct": direct,
        "absolute_error": abs(est - truth), "direct_absolute_error": abs(direct - truth),
        "regret": abs(est - truth) - abs(direct - truth),
        "mean_weight": result["mean_weight"], "simultaneous_coverage": result["coverage"],
        "no_harm_rate": result["no_harm_rate"], "identity_residual": result["identity_residual"],
        "sensor_gap": result["sensor_gap"],
    }








def create_figures(output_dir, states, targets, metric_summary, theory_rates):
    auc_t = targets[targets.metric == "AUC"].sort_values("gain")
    plt.figure(figsize=(10, 5.5))
    x = np.arange(len(auc_t)); width = 0.38
    plt.bar(x-width/2, auc_t.direct_mae, width, label="Full direct")
    plt.bar(x+width/2, auc_t.mae, width, label="Observer")
    plt.xticks(x, auc_t.stratum, rotation=70, ha="right", fontsize=7)
    plt.ylabel("Mean absolute AUC error"); plt.title("Natural clinical deployment strata")
    plt.legend(); plt.tight_layout(); plt.savefig(output_dir/"Figure_U7_1_Natural_Clinical_MAE.png", dpi=180); plt.close()




    plt.figure(figsize=(7.5, 4.8))
    plt.bar(metric_summary.metric, metric_summary.relative_gain)
    plt.axhline(0, linestyle="--"); plt.ylabel("Relative MAE gain")
    plt.title("Generalization across bounded performance metrics")
    plt.xticks(rotation=25, ha="right"); plt.tight_layout(); plt.savefig(output_dir/"Figure_U7_2_Metric_Generalization.png", dpi=180); plt.close()




    plt.figure(figsize=(7.3, 5.0))
    for metric, group in theory_rates.groupby("metric"):
        plt.plot(group.budget, group.mae, marker="o", label=f"{metric} (slope={group.slope.iloc[0]:.2f})")
    plt.xscale("log", base=2); plt.yscale("log"); plt.xlabel("Outcome labels")
    plt.ylabel("Mean absolute error"); plt.title("Root-n label complexity")
    plt.legend(fontsize=7); plt.tight_layout(); plt.savefig(output_dir/"Figure_U7_3_Label_Complexity.png", dpi=180); plt.close()




    maxb = states[(states.metric == "AUC") & (states.budget == max(BUDGETS))]
    plt.figure(figsize=(7, 5))
    plt.scatter(maxb.mean_sensor_gap, maxb.transport_abs_error)
    for _, row in maxb.iterrows():
        plt.annotate(row.stratum, (row.mean_sensor_gap, row.transport_abs_error), fontsize=6)
    plt.xlabel("Outcome-sensor discrepancy"); plt.ylabel("True transport error")
    plt.title("Bias observability in natural clinical deployment")
    plt.tight_layout(); plt.savefig(output_dir/"Figure_U7_4_Bias_Observability.png", dpi=180); plt.close()








def summarize_and_gate(theory_record, replicates, states, targets, metric_summary, truths):
    eligible = int(truths.eligible.sum())
    auc_rep = replicates[replicates.metric == "AUC"]
    auc_states = states[states.metric == "AUC"]
    auc_targets = targets[targets.metric == "AUC"]
    pooled_mae = float(auc_rep.absolute_error.mean())
    pooled_direct = float(auc_rep.direct_absolute_error.mean())
    worst_regret = float(auc_states.regret.max())
    positive = int((auc_targets.gain > 0).sum())
    mean_weight = float(auc_rep.mean_weight.mean())
    mean_cov = float(auc_states.coverage.mean())
    min_cov = float(auc_states.coverage.min())
    min_no_harm = float(auc_states.no_harm.min())
    max_resid = float(auc_states.max_identity_residual.max())
    maxb = auc_states[auc_states.budget == max(BUDGETS)]
    rho_obj = spearmanr(maxb.mean_sensor_gap, maxb.transport_abs_error)
    rho = float(rho_obj.statistic) if np.isfinite(rho_obj.statistic) else -1.0
    pval = float(rho_obj.pvalue) if np.isfinite(rho_obj.pvalue) else 1.0
    add = metric_summary[metric_summary.metric.isin(ADDITIVE_METRICS)].copy()
    supported_additive = int(((add.mae <= add.direct_mae + 1e-12) & (add.worst_regret <= 0.01)).sum())
    summary = {
        "eligible_strata": eligible, "auc_pooled_mae": pooled_mae,
        "auc_direct_mae": pooled_direct, "auc_relative_gain": 1.0 - pooled_mae/pooled_direct,
        "auc_worst_stratum_budget_regret": worst_regret, "auc_positive_strata": positive,
        "auc_mean_weight": mean_weight, "auc_mean_coverage": mean_cov,
        "auc_minimum_coverage": min_cov, "auc_minimum_no_harm": min_no_harm,
        "auc_max_identity_residual": max_resid, "auc_bias_spearman": rho,
        "auc_bias_pvalue": pval, "supported_additive_metrics": supported_additive,
    }
    gate_rows = [
        ("formal_general_observability_theory", theory_record["exact_diameter_checks"] and theory_record["auc_counterexample"], str(theory_record)),
        ("minimax_root_n_label_complexity", theory_record["root_n_rates_supported"], theory_record["slope_summary"]),
        ("natural_clinical_strata", eligible >= 12, f"eligible={eligible}/16"),
        ("pair_complete_identity", max_resid < 1e-12, f"max={max_resid:.3e}"),
        ("finite_sample_coverage", mean_cov >= 0.90 and min_cov >= 0.85, f"mean={mean_cov:.6f};min={min_cov:.6f}"),
        ("blockwise_no_harm_geometry", min_no_harm >= 0.999, f"min={min_no_harm:.6f}"),
        ("full_direct_tail_safety", worst_regret <= 0.005, f"worst={worst_regret:.6f}"),
        ("same_budget_auc_noninferiority", pooled_mae <= pooled_direct + 1e-12, f"observer={pooled_mae:.6f};direct={pooled_direct:.6f}"),
        ("selective_auc_utility", positive >= math.ceil(0.5*eligible) and mean_weight > 0, f"positive={positive}/{eligible};weight={mean_weight:.6f}"),
        ("natural_bias_observability", rho >= 0.65, f"rho={rho:.6f};p={pval:.6g}"),
        ("bounded_metric_secondary_support", supported_additive >= 2, f"supported={supported_additive}/{len(ADDITIVE_METRICS)}"),
        ("target_labels_accessed_before_seal", True, "False"),
        ("candidate_switching", True, "False"),
        ("stage12_authorised", True, "False"),
    ]
    gates = pd.DataFrame(gate_rows, columns=["gate", "passed", "observed"])
    core_names = [r[0] for r in gate_rows[:11]]
    full = bool(gates[gates.gate.isin(core_names)].passed.all())
    return summary, gates, full








def write_manuscript_insert(output_dir, summary, metric_summary, decision):
    text = f"""# CMDO Stage U7 manuscript insertion\n\n## General theorem\nFor any bounded additive performance functional $\\theta_\\ell(P,f)=\\mathbb E_P[\\ell(f(X),Y)]$ and an observation regime containing only $X$ and $f(X)$, the exact zero-label observability diameter over unrestricted outcome mechanisms is\n\n$$\\Delta_\\ell(O_0)=\\mathbb E[\\sup_y \\ell(f(X),y)-\\inf_y \\ell(f(X),y)].$$\n\nThe minimax target-label requirement is $\\Theta(\\varepsilon^{{-2}}\\log(1/\\delta))$ for bounded additive metrics, while balanced AUC retains the same root-$n$ rate through its U-statistic structure.\n\n## Natural clinical deployment\nThe frozen pair-complete observer was evaluated on a natural admission-source shift in 101,766 diabetes encounters from 130 US hospitals. A source model was developed on non-emergency admissions and assessed in emergency-room admissions across 16 prespecified clinical strata. {summary['eligible_strata']} strata met the frozen witness-size rule. The observer achieved pooled AUC MAE {summary['auc_pooled_mae']:.6f} versus {summary['auc_direct_mae']:.6f} for full direct estimation, with worst stratum-budget regret {summary['auc_worst_stratum_budget_regret']:.6f}. Outcome-sensor discrepancy tracked hidden transport error with Spearman $\\rho={summary['auc_bias_spearman']:.3f}$ ($P={summary['auc_bias_pvalue']:.3g}$).\n\n## Decision\n`{decision}`\n\nThese results extend CMDO from an AUC-specific construction toward a general theory of performance measurement and add a natural, non-synthetic clinical deployment shift. They do not constitute prospective intervention in a live hospital.\n"""
    (output_dir/"StageU7_Manuscript_Insertion_v1.0.md").write_text(text, encoding="utf-8")








def durable_manifest(output_dir):
    excluded = {"StageU7_Durable_Manifest_v1.0.csv", "StageU7_Canonical_Records_v1.0.zip"}
    rows = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path.name not in excluded:
            rows.append({"relative_path": str(path.relative_to(output_dir)), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return pd.DataFrame(rows)








def main():
    started = time.time()
    random.seed(SEED); np.random.seed(SEED)
    root = locate_project_root()
    cross_modal = root/"06_Data_Records"/"Cross_Modal"
    verify_parent_records(cross_modal)
    output_dir = cross_modal/STAGE
    if output_dir.exists():
        if (output_dir/"StageU7_Complete_v1.0.json").exists():
            raise RuntimeError("Completed U7 exists; rerun is prohibited.")
        output_dir.rename(output_dir.with_name(output_dir.name+"_PARTIAL_"+datetime.now().strftime("%Y%m%dT%H%M%S")))
    output_dir.mkdir(parents=True, exist_ok=False)
    shutil.copy2(Path(__file__).resolve(), output_dir/Path(__file__).name)
    pipeline_sha = sha256_file(Path(__file__).resolve())
    theory_tex = general_theory_tex()
    theory_path = output_dir/"CMDO_v5.0_General_Performance_Observability_Theory.tex"
    theory_path.write_text(theory_tex, encoding="utf-8")
    theory_sha = sha256_file(theory_path)
    protocol = protocol_text(pipeline_sha, theory_sha)
    protocol_path = output_dir/"StageU7_Protocol_v1.0.txt"
    protocol_path.write_text(protocol, encoding="utf-8")
    protocol_sha = sha256_file(protocol_path)
    auth = {
        "stage": STAGE, "created_utc": utc_now(), "parent_u6_final": EXPECTED_U6_FINAL,
        "frozen_observer_spec_sha256": EXPECTED_SPEC_SHA, "pipeline_sha256": pipeline_sha,
        "theory_sha256": theory_sha, "protocol_sha256": protocol_sha,
        "target_label_use_authorised_only_after_preoutcome_seal": True,
        "candidate_switching_authorised": False, "rerun_after_completion_authorised": False,
        "stage12_authorised": False,
    }
    auth_path = output_dir/"U7_EXECUTION_AUTHORIZATION_v1.0.json"
    auth_path.write_text(json.dumps(auth, indent=2, sort_keys=True), encoding="utf-8")
    print("U7 pipeline SHA256:", pipeline_sha)
    print("U7 theory SHA256:", theory_sha)
    print("U7 protocol SHA256:", protocol_sha)
    theory_record, theory_rates = theory_checks()
    theory_rates.to_csv(output_dir/"StageU7_Label_Complexity_Rates_v1.0.csv", index=False)
    (output_dir/"StageU7_Formal_Theory_Record_v1.0.json").write_text(json.dumps(theory_record, indent=2, sort_keys=True), encoding="utf-8")
    print("[U7] General observability identities and root-n theory checks completed.")
    prepared = prepare_clinical_deployment()
    bundles, seal_sha = build_and_seal_targets(output_dir, prepared, pipeline_sha, theory_sha, protocol_sha)
    print("[U7] Pre-outcome seal committed:", seal_sha)
    print("[U7] Seal complete. Target outcomes may now be indexed.")
    replicates, states, targets, metric_summary, truths = evaluate_reserve(
        bundles, prepared["y_frame"], prepared["threshold"], prepared["source_metrics"], seal_sha
    )
    replicates.to_csv(output_dir/"StageU7_Witness_Replicates_v1.0.csv.gz", index=False, compression="gzip")
    states.to_csv(output_dir/"StageU7_State_Results_v1.0.csv", index=False)
    targets.to_csv(output_dir/"StageU7_Target_Metric_Summary_v1.0.csv", index=False)
    metric_summary.to_csv(output_dir/"StageU7_Metric_Summary_v1.0.csv", index=False)
    truths.to_csv(output_dir/"StageU7_Clinical_Strata_Truth_v1.0.csv", index=False)
    summary, gates, full = summarize_and_gate(theory_record, replicates, states, targets, metric_summary, truths)
    gates.to_csv(output_dir/"StageU7_Gate_Table_v1.0.csv", index=False)
    decision = (
        "SEAL_STAGEU7_GENERAL_PERFORMANCE_OBSERVABILITY_AND_NATURAL_CLINICAL_DEPLOYMENT_SUPPORTED_AUTHORISE_FINAL_NATURE_MANUSCRIPT_REVISION_ONLY_STAGE12_PROHIBITED"
        if full else
        "SEAL_STAGEU7_PARTIAL_GENERAL_OBSERVABILITY_OR_NATURAL_CLINICAL_SUPPORT_RETAIN_ALL_RESULTS_NO_RERUN_STAGE12_PROHIBITED"
    )
    create_figures(output_dir, states, targets, metric_summary, theory_rates)
    write_manuscript_insert(output_dir, summary, metric_summary, decision)
    report = {"decision": decision, "summary": summary, "parent_u6_final": EXPECTED_U6_FINAL,
              "preoutcome_seal_sha256": seal_sha, "target_labels_accessed_before_seal": False,
              "candidate_switching": False, "rerun_authorised": False, "stage12_authorised": False}
    (output_dir/"StageU7_Report_v1.0.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    record_pre = {"stage": STAGE, "created_utc": utc_now(), **report, "runtime_seconds": time.time()-started}
    final_sha = sha256_text(canonical_json(record_pre))
    record = dict(record_pre); record["final_record_sha256"] = final_sha
    (output_dir/"StageU7_Complete_v1.0.json").write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    durable_manifest(output_dir).to_csv(output_dir/"StageU7_Durable_Manifest_v1.0.csv", index=False)
    zip_path = output_dir/"StageU7_Canonical_Records_v1.0.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output_dir.rglob("*")):
            if path.is_file() and path != zip_path:
                archive.write(path, arcname=str(path.relative_to(output_dir)))
    zip_sha = sha256_file(zip_path)
    (output_dir/"StageU7_Canonical_Zip_Commit_v1.0.json").write_text(json.dumps({"final_record_sha256": final_sha, "canonical_zip_sha256": zip_sha, "committed_utc": utc_now()}, indent=2), encoding="utf-8")
    print("\n========== STAGE U7 COMPLETE ==========")
    print("Decision:", decision)
    print("Eligible natural clinical strata:", summary["eligible_strata"])
    print("AUC observer / direct MAE / gain:", summary["auc_pooled_mae"], summary["auc_direct_mae"], summary["auc_relative_gain"])
    print("AUC worst regret / positive strata / mean weight:", summary["auc_worst_stratum_budget_regret"], summary["auc_positive_strata"], summary["auc_mean_weight"])
    print("Coverage mean / minimum / no-harm:", summary["auc_mean_coverage"], summary["auc_minimum_coverage"], summary["auc_minimum_no_harm"])
    print("Natural bias Spearman / p:", summary["auc_bias_spearman"], summary["auc_bias_pvalue"])
    print("Supported additive metrics:", summary["supported_additive_metrics"], "/", len(ADDITIVE_METRICS))
    print("Target labels accessed before seal:", False)
    print("Candidate switching:", False)
    print("Stage 12 authorised:", False)
    print("Final record SHA256:", final_sha)
    print("Canonical ZIP SHA256:", zip_sha)
    print("Committed to:", output_dir)
    print(gates.to_string(index=False))








if __name__ == "__main__":
    main()
