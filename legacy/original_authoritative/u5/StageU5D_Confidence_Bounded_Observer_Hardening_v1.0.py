#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMDO Stage U5D — Confidence-Bounded Observer Hardening v1.0

Transparent post-U5/U5C development. Reconstructs the exact 16-target U5
reserve from public raw data, verifies target score hashes against the sealed
pre-outcome record, and performs genuine raw-sample two-fold cross-fitting at
the same total target-label budget.

No new blind is accessed. No U4/U5/U5C record or decision is changed.
"""
from __future__ import annotations

import hashlib, importlib.util, json, math, os, platform, random, shutil, sys, time, warnings, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.metrics import roc_auc_score

PROJECT='Cross-Modal_Diagnostic_Observability'
STAGE='StageU5D_Confidence_Bounded_Observer_Hardening_v1.0'
EXPECTED_U5_FINAL='0850505e3a603b5c3cca68a44c94c10970218d525cb8364be5a6f148b5059721'
EXPECTED_U5C_FINAL='cd796c8d3e54cb26fb1fe269bac3b3c528d61bc59770d533361dcf4956f1b4f7'
EXPECTED_BASE_PIPELINE_SHA='5ff064f1bb1581f6ed99eb6958fb14e53e54acac0db3e214f3d7528d3835bcde'
EXPECTED_DESCRIPTOR_SHA='84465a697f27e5d1f2d58604f8c0c1f04d1c646dd2af4b6be384b5431246bc54'
EXPECTED_TRUE_SHA='a96db6f8886a91fd9a3a31dc5dd0f010689384b769d1b5d018318af85b350702'
BUDGETS=np.asarray([8,16,32,64,128],dtype=int)
N_REPLICATES=200
SEQUENTIAL_REPLICATES=200
MAX_TOTAL_BUDGET=128
DELTA=0.10
SEED=20260724
MAX_WEIGHT=0.35
RISK_COEFFICIENT=8.0


def utc_now(): return datetime.now(timezone.utc).isoformat()
def sha256_file(path:Path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
    return h.hexdigest()
def sha256_bytes(data:bytes): return hashlib.sha256(data).hexdigest()
def canonical_json(obj): return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def sha256_text(text): return hashlib.sha256(text.encode()).hexdigest()

def locate_project_root():
    for p in [Path('/content/drive/MyDrive')/PROJECT, Path('/content/drive/Shareddrives')/PROJECT]:
        if p.exists(): return p
    matches=[p for p in Path('/content/drive').rglob(PROJECT) if p.is_dir()]
    if len(matches)==1:return matches[0]
    raise FileNotFoundError(matches)

def import_base(path:Path):
    spec=importlib.util.spec_from_file_location('cmdo_u5_base',path)
    mod=importlib.util.module_from_spec(spec); assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod

def paired_sensor(pos_scores,neg_scores,rng):
    pos=np.asarray(pos_scores,float)[rng.permutation(len(pos_scores))]
    neg=np.asarray(neg_scores,float)[rng.permutation(len(neg_scores))]
    m=min(len(pos),len(neg)); pos=pos[:m]; neg=neg[:m]
    z=(pos>neg).astype(float)+0.5*(pos==neg)
    mean=float(z.mean())
    var=float(np.var(z,ddof=1)) if m>1 else 0.0
    return mean,var,m,z

def radii(sensor_var,m,delong_var,delta):
    hoeff=math.sqrt(math.log(2/delta)/(2*m))
    if m>1:
        eb=math.sqrt(2*sensor_var*math.log(2/delta)/m)+7*math.log(2/delta)/(3*(m-1))
    else: eb=1.0
    eb=min(1.0,eb)
    mcd=min(1.0,math.sqrt(math.log(2/delta)/m))
    dl=min(1.0,float(norm.ppf(1-delta/2))*math.sqrt(max(delong_var,1e-12)))
    return {'PAIRED_HOEFFDING':min(1.0,hoeff),'PAIRED_EMPBERN':eb,'USTAT_MCDIARMID':mcd,'DELONG_NORMAL':dl}

def weight_from_ucb(V,U,support,risk):
    return float(support)*min(MAX_WEIGHT,float(V)/(float(V)+float(U)+RISK_COEFFICIENT*float(risk)+1e-12))

def verify_reconstruction(base,families,u5_dir):
    frames=[]
    for fam in families:
        _,targets,_=base.fit_transport(fam['family'],fam['source_z'],fam['source_scores'],fam['pseudo_envs'],fam['targets'])
        frames.append(targets)
    reconstructed=pd.concat(frames,ignore_index=True).sort_values(['family','target']).reset_index(drop=True)
    authoritative=pd.read_csv(u5_dir/'StageU5B_PreOutcome_Target_Descriptors_And_Transport_v1.0.csv').sort_values(['family','target']).reset_index(drop=True)
    if len(reconstructed)!=len(authoritative): raise RuntimeError('target count mismatch')
    keys=['family','target','n_target_unlabelled','target_score_sha256']
    exact=bool(reconstructed[keys].astype(str).equals(authoritative[keys].astype(str)))
    numeric=['feature_mean_shift','variance_log_ratio','score_shift','entropy_shift','confidence_shift','transport_auc_raw','transport_auc','transport_cv_bias','transport_cv_residual_scale','support_distance','support_gate','transport_risk_proxy']
    maxdiff=float(np.max(np.abs(reconstructed[numeric].to_numpy(float)-authoritative[numeric].to_numpy(float))))
    passed=exact and maxdiff<1e-10
    if not passed: raise RuntimeError({'exact':exact,'maxdiff':maxdiff})
    return reconstructed,authoritative,{'target_roster_and_score_hashes_exact':exact,'maximum_numeric_difference':maxdiff,'reconstruction_pass':passed}

def make_raw_table(families,labels):
    frames=[]; manifest=[]
    for fam in families:
        family=fam['family']
        for target,item in fam['targets'].items():
            s=np.asarray(item['scores'],float); y=np.asarray(labels[(family,target)],int)
            if len(s)!=len(y): raise RuntimeError(f'{family}/{target} mismatch')
            frames.append(pd.DataFrame({'family':family,'target':target,'row_index':np.arange(len(y)),'score':s,'label':y}))
            manifest.append({'family':family,'target':target,'n':len(y),'positive_n':int(y.sum()),'negative_n':int((1-y).sum()),'score_sha256':sha256_bytes(s.astype(np.float64).tobytes()),'label_sha256':sha256_bytes(y.astype(np.int8).tobytes()),'true_auc':float(roc_auc_score(y,s))})
    return pd.concat(frames,ignore_index=True),pd.DataFrame(manifest)

def fold_estimate(base,y,scores,indices):
    yy=y[indices]; ss=scores[indices]
    return base.delong_auc_variance(yy,ss)

def crossfit_analysis(base,families,labels,transport):
    tindex=transport.set_index(['family','target'])
    rows=[]; target_counter=0
    for fam in families:
        family=fam['family']
        for target,item in fam['targets'].items():
            y=np.asarray(labels[(family,target)],int); scores=np.asarray(item['scores'],float)
            true=float(roc_auc_score(y,scores)); pos=np.where(y==1)[0]; neg=np.where(y==0)[0]
            tr=tindex.loc[(family,target)]; T=float(tr['transport_auc']); support=float(tr['support_gate']); risk=float(tr['transport_risk_proxy']); true_bias_sq=(T-true)**2
            for budget in BUDGETS:
                per_class=int(budget//2); fold_class=per_class//2
                for rep in range(N_REPLICATES):
                    rng=np.random.default_rng(SEED+target_counter*100000+int(budget)*1000+rep)
                    sp=rng.choice(pos,size=per_class,replace=False); sn=rng.choice(neg,size=per_class,replace=False)
                    sp=sp[rng.permutation(per_class)]; sn=sn[rng.permutation(per_class)]
                    a=np.concatenate([sp[:fold_class],sn[:fold_class]]); b=np.concatenate([sp[fold_class:],sn[fold_class:]])
                    full=np.concatenate([sp,sn])
                    Dfull,Vfull=fold_estimate(base,y,scores,full)
                    Da,Va=fold_estimate(base,y,scores,a); Db,Vb=fold_estimate(base,y,scores,b)
                    pa,pva,ma,_=paired_sensor(scores[sp[:fold_class]],scores[sn[:fold_class]],rng)
                    pb,pvb,mb,_=paired_sensor(scores[sp[fold_class:]],scores[sn[fold_class:]],rng)
                    rad_a=radii(pva,ma,Va,DELTA); rad_b=radii(pvb,mb,Vb,DELTA)
                    sensors_a={'PAIRED_HOEFFDING':pa,'PAIRED_EMPBERN':pa,'USTAT_MCDIARMID':Da,'DELONG_NORMAL':Da}
                    sensors_b={'PAIRED_HOEFFDING':pb,'PAIRED_EMPBERN':pb,'USTAT_MCDIARMID':Db,'DELONG_NORMAL':Db}
                    for method in rad_a:
                        Ua=min(1.0,abs(sensors_a[method]-T)+rad_a[method])**2
                        Ub=min(1.0,abs(sensors_b[method]-T)+rad_b[method])**2
                        # A senses bias, B estimates; B senses bias, A estimates.
                        w_b=weight_from_ucb(Vb,Ua,support,risk); est_b=(1-w_b)*Db+w_b*T
                        w_a=weight_from_ucb(Va,Ub,support,risk); est_a=(1-w_a)*Da+w_a*T
                        est=0.5*(est_a+est_b); split_direct=0.5*(Da+Db)
                        risk_a=(1-w_a)**2*Va+w_a**2*true_bias_sq; risk_b=(1-w_b)**2*Vb+w_b**2*true_bias_sq
                        split_direct_risk_upper=0.5*(Va+Vb); crossfit_risk_upper=0.5*(risk_a+risk_b)
                        rows.append({'family':family,'target':target,'budget':int(budget),'replicate':rep,'method':method,'true_auc':true,'transport_auc':T,'true_bias_sq':true_bias_sq,'support_gate':support,'transport_risk_proxy':risk,'direct_full_auc':Dfull,'direct_full_variance':Vfull,'split_direct_auc':split_direct,'estimate':est,'absolute_error':abs(est-true),'direct_full_abs_error':abs(Dfull-true),'split_direct_abs_error':abs(split_direct-true),'squared_error':(est-true)**2,'direct_full_squared_error':(Dfull-true)**2,'split_direct_squared_error':(split_direct-true)**2,'mean_weight':0.5*(w_a+w_b),'fold_a_coverage':bool(Ub>=true_bias_sq),'fold_b_coverage':bool(Ua>=true_bias_sq),'joint_coverage':bool(Ua>=true_bias_sq and Ub>=true_bias_sq),'crossfit_theoretical_risk_upper':crossfit_risk_upper,'split_direct_theoretical_risk_upper':split_direct_risk_upper,'certified_no_harm_upper':bool(crossfit_risk_upper<=split_direct_risk_upper+1e-14)})
                    # Same-budget original plugin and oracle comparators.
                    bh=max(0.0,(Dfull-T)**2-Vfull)
                    wp=support*min(MAX_WEIGHT,Vfull/(Vfull+0.5*bh+RISK_COEFFICIENT*risk+1e-12)); ep=(1-wp)*Dfull+wp*T
                    wo=support*min(MAX_WEIGHT,Vfull/(Vfull+true_bias_sq+RISK_COEFFICIENT*risk+1e-12)); eo=(1-wo)*Dfull+wo*T
                    for method,est,w in [('PLUGIN_FULL',ep,wp),('ORACLE_FULL',eo,wo),('DIRECT_FULL',Dfull,0.0),('SPLIT_DIRECT',split_direct,0.0)]:
                        rows.append({'family':family,'target':target,'budget':int(budget),'replicate':rep,'method':method,'true_auc':true,'transport_auc':T,'true_bias_sq':true_bias_sq,'support_gate':support,'transport_risk_proxy':risk,'direct_full_auc':Dfull,'direct_full_variance':Vfull,'split_direct_auc':split_direct,'estimate':est,'absolute_error':abs(est-true),'direct_full_abs_error':abs(Dfull-true),'split_direct_abs_error':abs(split_direct-true),'squared_error':(est-true)**2,'direct_full_squared_error':(Dfull-true)**2,'split_direct_squared_error':(split_direct-true)**2,'mean_weight':w,'fold_a_coverage':np.nan,'fold_b_coverage':np.nan,'joint_coverage':np.nan,'crossfit_theoretical_risk_upper':np.nan,'split_direct_theoretical_risk_upper':np.nan,'certified_no_harm_upper':np.nan})
            target_counter+=1
    return pd.DataFrame(rows)

def sequential_cs(families,labels,transport):
    tindex=transport.set_index(['family','target']); rows=[]; target_counter=0
    max_pairs=MAX_TOTAL_BUDGET//2
    for fam in families:
        family=fam['family']
        for target,item in fam['targets'].items():
            y=np.asarray(labels[(family,target)],int); s=np.asarray(item['scores'],float); true=float(roc_auc_score(y,s)); T=float(tindex.loc[(family,target),'transport_auc']); true_abs=abs(T-true)
            pos=np.where(y==1)[0]; neg=np.where(y==0)[0]
            for rep in range(SEQUENTIAL_REPLICATES):
                rng=np.random.default_rng(SEED+9000000+target_counter*100000+rep)
                pp=rng.choice(pos,size=max_pairs,replace=False); nn=rng.choice(neg,size=max_pairs,replace=False)
                pp=pp[rng.permutation(max_pairs)]; nn=nn[rng.permutation(max_pairs)]
                z=(s[pp]>s[nn]).astype(float)+0.5*(s[pp]==s[nn]); csum=np.cumsum(z)
                path_cover=True
                for t in range(1,max_pairs+1):
                    delta_t=6*DELTA/(math.pi**2*t**2)
                    r=math.sqrt(math.log(2/delta_t)/(2*t)); mean=float(csum[t-1]/t)
                    lo=max(0.0,mean-r); hi=min(1.0,mean+r)
                    blo=max(0.0,abs(T-mean)-r); bhi=min(1.0,abs(T-mean)+r)
                    cover=lo<=true<=hi; path_cover=path_cover and cover
                    rows.append({'family':family,'target':target,'replicate':rep,'pair_count':t,'total_labels':2*t,'paired_auc':mean,'auc_lower':lo,'auc_upper':hi,'true_auc':true,'transport_auc':T,'true_transport_abs_error':true_abs,'bias_abs_lower':blo,'bias_abs_upper':bhi,'auc_covered':cover,'path_covered_so_far':path_cover})
            target_counter+=1
    return pd.DataFrame(rows)

def summarise_methods(rep):
    states=(rep.groupby(['family','target','budget','method'],as_index=False).agg(mae=('absolute_error','mean'),mse=('squared_error','mean'),direct_full_mae=('direct_full_abs_error','mean'),direct_full_mse=('direct_full_squared_error','mean'),split_direct_mae=('split_direct_abs_error','mean'),mean_weight=('mean_weight','mean'),fold_coverage=('fold_a_coverage','mean'),joint_coverage=('joint_coverage','mean'),certified_no_harm_rate=('certified_no_harm_upper','mean')))
    states['mae_regret_vs_full_direct']=states['mae']-states['direct_full_mae']; states['mae_regret_vs_split_direct']=states['mae']-states['split_direct_mae']
    summary=(states.groupby('method',as_index=False).agg(pooled_mae=('mae','mean'),pooled_mse=('mse','mean'),pooled_direct_full_mae=('direct_full_mae','mean'),worst_target_budget_regret_vs_full=('mae_regret_vs_full_direct','max'),worst_target_budget_regret_vs_split=('mae_regret_vs_split_direct','max'),mean_weight=('mean_weight','mean'),mean_fold_coverage=('fold_coverage','mean'),mean_joint_coverage=('joint_coverage','mean'),minimum_certified_no_harm_rate=('certified_no_harm_rate','min')))
    summary['gain_vs_full_direct']=1-summary['pooled_mae']/summary['pooled_direct_full_mae']
    return states,summary

def sequential_summary(seq):
    path=(seq.groupby(['family','target','replicate'],as_index=False).agg(simultaneous_coverage=('auc_covered','all')))
    target=(path.groupby(['family','target'],as_index=False).agg(simultaneous_coverage=('simultaneous_coverage','mean')))
    stops=[]
    for (family,target,rep),g in seq.groupby(['family','target','replicate']):
        g=g.sort_values('pair_count')
        def first(mask):
            vals=g.loc[mask,'total_labels']; return int(vals.iloc[0]) if len(vals) else np.nan
        stops.append({'family':family,'target':target,'replicate':rep,'labels_certify_bias_below_0_05':first(g['bias_abs_upper']<=0.05),'labels_certify_bias_below_0_10':first(g['bias_abs_upper']<=0.10),'labels_certify_bias_above_0_15':first(g['bias_abs_lower']>=0.15)})
    stops=pd.DataFrame(stops)
    return target,stops

def make_figures(out,summary,states,seq_target,stops):
    plt.figure(figsize=(8,5)); x=np.arange(len(summary)); plt.bar(x,summary['pooled_mae']); plt.xticks(x,summary['method'],rotation=70,ha='right',fontsize=7); plt.ylabel('Pooled MAE'); plt.title('Raw-sample same-budget crossfit observers'); plt.tight_layout(); plt.savefig(out/'Figure_U5D_1_Method_MAE.png',dpi=180); plt.close()
    cf=summary[summary['method'].isin(['PAIRED_HOEFFDING','PAIRED_EMPBERN','USTAT_MCDIARMID','DELONG_NORMAL'])]
    plt.figure(figsize=(7,5)); plt.scatter(cf['worst_target_budget_regret_vs_full'],cf['pooled_mae']);
    for _,r in cf.iterrows(): plt.annotate(r['method'],(r['worst_target_budget_regret_vs_full'],r['pooled_mae']),fontsize=8)
    plt.xlabel('Worst target-budget MAE regret vs full direct'); plt.ylabel('Pooled MAE'); plt.title('Guarantee–efficiency frontier'); plt.tight_layout(); plt.savefig(out/'Figure_U5D_2_Guarantee_Efficiency_Frontier.png',dpi=180); plt.close()
    cov=states[states['method'].isin(['PAIRED_HOEFFDING','PAIRED_EMPBERN','USTAT_MCDIARMID','DELONG_NORMAL'])].groupby(['method','budget'],as_index=False)['fold_coverage'].mean()
    plt.figure(figsize=(7,5));
    for m,g in cov.groupby('method'): plt.plot(g['budget'],g['fold_coverage'],marker='o',label=m)
    plt.xscale('log',base=2); plt.axhline(1-DELTA,linestyle='--'); plt.xlabel('Total labels'); plt.ylabel('Per-fold bias-UCB coverage'); plt.title('Finite-sample and asymptotic coverage'); plt.legend(fontsize=7); plt.tight_layout(); plt.savefig(out/'Figure_U5D_3_Coverage_By_Budget.png',dpi=180); plt.close()
    plt.figure(figsize=(8,5)); plt.bar(seq_target['family']+'/'+seq_target['target'],seq_target['simultaneous_coverage']); plt.axhline(1-DELTA,linestyle='--'); plt.xticks(rotation=75,ha='right',fontsize=7); plt.ylabel('Anytime simultaneous coverage'); plt.title('Paired Hoeffding confidence sequence'); plt.tight_layout(); plt.savefig(out/'Figure_U5D_4_Sequential_Coverage.png',dpi=180); plt.close()
    med=stops.groupby(['family','target'],as_index=False)[['labels_certify_bias_below_0_10','labels_certify_bias_above_0_15']].median(numeric_only=True)
    plt.figure(figsize=(8,5)); idx=np.arange(len(med)); plt.bar(idx-0.2,med['labels_certify_bias_below_0_10'],width=0.4,label='Bias < 0.10'); plt.bar(idx+0.2,med['labels_certify_bias_above_0_15'],width=0.4,label='Bias > 0.15'); plt.xticks(idx,med['target'],rotation=75,ha='right',fontsize=7); plt.ylabel('Median labels to certify'); plt.title('Target-specific evidence demand'); plt.legend(); plt.tight_layout(); plt.savefig(out/'Figure_U5D_5_Sequential_Label_Demand.png',dpi=180); plt.close()

def manifest(out):
    rows=[]
    for p in sorted(out.rglob('*')):
        if p.is_file() and p.name not in {'StageU5D_Durable_Manifest_v1.0.csv','StageU5D_Canonical_Records_v1.0.zip'}: rows.append({'relative_path':str(p.relative_to(out)),'size_bytes':p.stat().st_size,'sha256':sha256_file(p)})
    return pd.DataFrame(rows)

def main():
    started=time.time(); random.seed(SEED); np.random.seed(SEED); warnings.filterwarnings('ignore',category=FutureWarning)
    protocol=Path(os.environ['CMDO_U5D_PROTOCOL_PATH']).resolve(); authp=Path(os.environ['CMDO_U5D_AUTH_PATH']).resolve(); theory=Path(os.environ['CMDO_U5D_THEORY_PATH']).resolve(); basep=Path(os.environ['CMDO_U5D_BASE_PIPELINE_PATH']).resolve(); pipelinep=Path(__file__).resolve()
    auth=json.loads(authp.read_text())
    release_ok=auth.get('u5d_protocol_sha256')==sha256_file(protocol) and auth.get('u5d_pipeline_sha256')==sha256_file(pipelinep) and auth.get('u5d_theory_sha256')==sha256_file(theory) and auth.get('base_u5_pipeline_sha256')==sha256_file(basep)==EXPECTED_BASE_PIPELINE_SHA and auth.get('new_blind_access_authorised') is False and auth.get('stage12_authorised') is False
    if not release_ok: raise RuntimeError('release integrity failed')
    root=locate_project_root(); cross=root/'06_Data_Records'/'Cross_Modal'; u5=cross/'StageU5B_Sentinel_Observability_Prospective_Reserve_v1.0'; u5c=cross/'StageU5C_Theory_Proof_And_Empirical_Certification_v1.0'
    u5rec=json.loads((u5/'StageU5B_Complete_v1.0.json').read_text()); u5crec=json.loads((u5c/'StageU5C_Complete_v1.0.json').read_text())
    parent_ok=u5rec.get('final_record_sha256')==EXPECTED_U5_FINAL and u5crec.get('final_record_sha256')==EXPECTED_U5C_FINAL and sha256_file(u5/'StageU5B_PreOutcome_Target_Descriptors_And_Transport_v1.0.csv')==EXPECTED_DESCRIPTOR_SHA and sha256_file(u5/'StageU5B_Target_True_Metrics_v1.0.csv')==EXPECTED_TRUE_SHA
    if not parent_ok: raise RuntimeError('parent integrity failed')
    out=cross/STAGE
    if out.exists():
        if (out/'StageU5D_Complete_v1.0.json').exists(): raise RuntimeError('completed U5D exists; rerun prohibited')
        out.rename(out.with_name(out.name+'_PARTIAL_'+datetime.now().strftime('%Y%m%dT%H%M%S')))
    out.mkdir(parents=True)
    for p in [protocol,authp,theory,basep,pipelinep]: shutil.copy2(p,out/p.name)
    base=import_base(basep); raw=Path('/content/cmdo_u5d_ephemeral_raw'); raw.mkdir(parents=True,exist_ok=True)
    print('[U5D] Reconstructing the exact U5 source models and raw targets.')
    families=base.acquire_all(raw)
    transport,authoritative,recon=verify_reconstruction(base,families,u5)
    print('[U5D] Exact target score hashes and transport descriptors verified.')
    labels=base.reveal_labels(families)
    raw_table,raw_manifest=make_raw_table(families,labels)
    auth_true=pd.read_csv(u5/'StageU5B_Target_True_Metrics_v1.0.csv').sort_values(['family','target']).reset_index(drop=True)
    chk=raw_manifest.sort_values(['family','target']).reset_index(drop=True)
    true_diff=float(np.max(np.abs(chk['true_auc'].to_numpy()-auth_true['true_auc'].to_numpy())))
    if true_diff>1e-12: raise RuntimeError(f'true AUC mismatch {true_diff}')
    raw_table.to_csv(out/'StageU5D_Reconstructed_Target_Scores_And_Labels_v1.0.csv.gz',index=False,compression='gzip'); raw_manifest.to_csv(out/'StageU5D_Reconstructed_Target_Manifest_v1.0.csv',index=False)
    print('[U5D] Running genuine raw-sample same-budget two-fold cross-fitting.')
    rep=crossfit_analysis(base,families,labels,transport); rep.to_csv(out/'StageU5D_Raw_Sample_Crossfit_Replicates_v1.0.csv.gz',index=False,compression='gzip')
    states,summary=summarise_methods(rep); states.to_csv(out/'StageU5D_Raw_Sample_Crossfit_State_Results_v1.0.csv',index=False); summary.to_csv(out/'StageU5D_Method_Summary_v1.0.csv',index=False)
    print('[U5D] Running paired anytime-valid confidence-sequence analysis.')
    seq=sequential_cs(families,labels,transport); seq.to_csv(out/'StageU5D_Sequential_Confidence_Sequence_v1.0.csv.gz',index=False,compression='gzip')
    seq_target,stops=sequential_summary(seq); seq_target.to_csv(out/'StageU5D_Sequential_Coverage_By_Target_v1.0.csv',index=False); stops.to_csv(out/'StageU5D_Sequential_Stopping_Replicates_v1.0.csv.gz',index=False,compression='gzip')
    # Analytic label complexity for paired Hoeffding fixed-time sensing.
    rows=[]
    for delta in [0.10,0.05,0.01]:
        for eps in [0.05,0.075,0.10,0.15]:
            pairs=math.ceil(math.log(2/delta)/(2*eps**2)); rows.append({'delta':delta,'auc_radius':eps,'required_independent_pairs':pairs,'required_balanced_labels':2*pairs})
    pd.DataFrame(rows).to_csv(out/'StageU5D_Analytic_Label_Complexity_v1.0.csv',index=False)
    make_figures(out,summary,states,seq_target,stops)
    sidx=summary.set_index('method')
    paired_h=sidx.loc['PAIRED_HOEFFDING']; paired_e=sidx.loc['PAIRED_EMPBERN']; dl=sidx.loc['DELONG_NORMAL']
    seq_cov=float(seq_target['simultaneous_coverage'].mean())
    gates=[('release_and_parent_integrity',release_ok and parent_ok,str(release_ok and parent_ok)),('exact_raw_target_reconstruction',recon['reconstruction_pass'] and true_diff<1e-12,f"score_hashes={recon['target_roster_and_score_hashes_exact']};max_descriptor_diff={recon['maximum_numeric_difference']:.3e};true_auc_diff={true_diff:.3e}"),('paired_hoeffding_fold_coverage',paired_h['mean_fold_coverage']>=0.90,f"coverage={paired_h['mean_fold_coverage']:.6f};joint={paired_h['mean_joint_coverage']:.6f}"),('paired_empbern_fold_coverage',paired_e['mean_fold_coverage']>=0.90,f"coverage={paired_e['mean_fold_coverage']:.6f};joint={paired_e['mean_joint_coverage']:.6f}"),('empbern_improves_hoeffding_efficiency',paired_e['pooled_mae']<=paired_h['pooled_mae'] and paired_e['mean_weight']>=paired_h['mean_weight'],f"EB_mae={paired_e['pooled_mae']:.6f};H_mae={paired_h['pooled_mae']:.6f};EB_w={paired_e['mean_weight']:.6f};H_w={paired_h['mean_weight']:.6f}"),('certified_geometry_on_covered_folds',paired_h['minimum_certified_no_harm_rate']>=0.999 and paired_e['minimum_certified_no_harm_rate']>=0.999,f"H={paired_h['minimum_certified_no_harm_rate']:.6f};EB={paired_e['minimum_certified_no_harm_rate']:.6f}"),('delong_practical_same_budget_utility',dl['pooled_mae']<=dl['pooled_direct_full_mae'] and dl['worst_target_budget_regret_vs_full']<=0.005,f"mae={dl['pooled_mae']:.6f};direct={dl['pooled_direct_full_mae']:.6f};worst={dl['worst_target_budget_regret_vs_full']:.6f}"),('anytime_confidence_sequence_coverage',seq_cov>=0.90,f"coverage={seq_cov:.6f}"),('new_blind_accessed',True,'False'),('stage12_authorised',True,'False')]
    gate=pd.DataFrame(gates,columns=['gate','passed','observed']); gate.to_csv(out/'StageU5D_Gate_Table_v1.0.csv',index=False)
    core=gate[~gate['gate'].isin(['new_blind_accessed','stage12_authorised'])]
    if bool(core['passed'].all()): decision='SEAL_STAGEU5D_CONFIDENCE_BOUNDED_OBSERVER_HARDENING_SUPPORTED_AUTHORISE_FINAL_OBSERVER_FREEZE_AND_U6_PREREGISTRATION_ONLY_NO_NEW_BLIND_STAGE12_PROHIBITED'
    else: decision='SEAL_STAGEU5D_PARTIAL_CONFIDENCE_BOUNDED_OBSERVER_SUPPORT_RETAIN_ALL_RESULTS_REFINE_BEFORE_U6_NO_NEW_BLIND_STAGE12_PROHIBITED'
    report=f"""# Stage U5D — Confidence-Bounded Observer Hardening\n\nDecision: `{decision}`\n\n- Exact U5 raw target reconstruction: {recon['reconstruction_pass']}\n- Maximum target-descriptor difference: {recon['maximum_numeric_difference']:.3e}\n- Maximum true-AUC difference: {true_diff:.3e}\n- Paired Hoeffding coverage / MAE / worst full-direct regret: {paired_h['mean_fold_coverage']:.6f} / {paired_h['pooled_mae']:.6f} / {paired_h['worst_target_budget_regret_vs_full']:.6f}\n- Paired empirical-Bernstein coverage / MAE / worst full-direct regret: {paired_e['mean_fold_coverage']:.6f} / {paired_e['pooled_mae']:.6f} / {paired_e['worst_target_budget_regret_vs_full']:.6f}\n- DeLong practical coverage / MAE / worst full-direct regret: {dl['mean_fold_coverage']:.6f} / {dl['pooled_mae']:.6f} / {dl['worst_target_budget_regret_vs_full']:.6f}\n- Anytime simultaneous coverage: {seq_cov:.6f}\n\nThe finite-sample guarantees apply to independent paired sentinel comparisons and to split-direct baselines. Comparisons with the full U-statistic direct estimator at the same total label budget are empirical efficiency comparisons, not no-harm theorems.\n"""
    (out/'StageU5D_Report_v1.0.md').write_text(report)
    pre={'stage':STAGE,'status':'TRANSPARENT_CONFIDENCE_BOUNDED_OBSERVER_HARDENING','created_utc':utc_now(),'decision':decision,'parent_u5_final_record_sha256':EXPECTED_U5_FINAL,'parent_u5c_final_record_sha256':EXPECTED_U5C_FINAL,'release_integrity_pass':release_ok,'parent_integrity_pass':parent_ok,'reconstruction':recon,'true_auc_max_difference':true_diff,'method_summary':summary.to_dict('records'),'sequential_mean_simultaneous_coverage':seq_cov,'new_blind_accessed':False,'parent_result_changed':False,'stage12_authorised':False,'runtime_seconds':time.time()-started,'python':sys.version,'platform':platform.platform()}
    final=sha256_text(canonical_json(pre)); rec=dict(pre); rec['final_record_sha256']=final; (out/'StageU5D_Complete_v1.0.json').write_text(json.dumps(rec,indent=2,sort_keys=True))
    man=manifest(out); man.to_csv(out/'StageU5D_Durable_Manifest_v1.0.csv',index=False)
    zp=out/'StageU5D_Canonical_Records_v1.0.zip'
    with zipfile.ZipFile(zp,'w',compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(out.rglob('*')):
            if p.is_file() and p!=zp: zf.write(p,arcname=str(p.relative_to(out)))
    zsha=sha256_file(zp); (out/'StageU5D_Canonical_Zip_Commit_v1.0.json').write_text(json.dumps({'stage':STAGE,'final_record_sha256':final,'canonical_zip_sha256':zsha,'committed_utc':utc_now()},indent=2,sort_keys=True))
    print('\n========== STAGE U5D COMPLETE =========='); print('Decision:',decision); print('Exact reconstruction:',recon['reconstruction_pass']); print('Paired Hoeffding coverage / MAE / worst regret:',paired_h['mean_fold_coverage'],paired_h['pooled_mae'],paired_h['worst_target_budget_regret_vs_full']); print('Paired EmpBern coverage / MAE / worst regret:',paired_e['mean_fold_coverage'],paired_e['pooled_mae'],paired_e['worst_target_budget_regret_vs_full']); print('DeLong coverage / MAE / worst regret:',dl['mean_fold_coverage'],dl['pooled_mae'],dl['worst_target_budget_regret_vs_full']); print('Anytime simultaneous coverage:',seq_cov); print('New blind accessed:',False); print('Stage 12 authorised:',False); print('Final record SHA256:',final); print('Canonical ZIP SHA256:',zsha); print('Committed to:',out); print(gate.to_string(index=False))

if __name__=='__main__': main()

