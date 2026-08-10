# Stage T4-DE: Baseline-Anchored Multi-Functional Audit Method v2
import os, json, math, hashlib, zipfile, shutil, warnings
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from scipy.stats import spearmanr
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.linear_model import Ridge, LogisticRegression

warnings.filterwarnings('ignore')
try:
    from IPython.display import display
except Exception:
    display = print

try:
    from google.colab import drive
    drive.mount('/content/drive', force_remount=False)
    IN_COLAB = True
except Exception:
    IN_COLAB = False

SEED = 20260723
rng = np.random.default_rng(SEED)
np.random.seed(SEED)
EXPECTED_T4ABC_FINAL = 'f35d2f06a05f732d2b46922cdd200117cd02339ae349c9b54b9f1fddd5d5a58c'
RETENTION_TOL = 0.05
CONFORMAL_ALPHA = 0.10

DEFAULT_ROOT = Path('/content/drive/MyDrive/Cross-Modal_Diagnostic_Observability') if IN_COLAB else Path.cwd()
PROJECT_ROOT = Path(os.environ.get('CMDO_PROJECT_ROOT', str(DEFAULT_ROOT)))
CM_ROOT = PROJECT_ROOT / '06_Data_Records' / 'Cross_Modal'
RUNTIME_ROOT = Path('/content/cmdo_runtime/StageT4-DE') if IN_COLAB else PROJECT_ROOT / '_runtime_StageT4DE'
COMMIT_ROOT = CM_ROOT / 'StageT4-DE_Baseline_Anchored_MultiFunctional_Audit_v0.1'
for p in [RUNTIME_ROOT, RUNTIME_ROOT/'00_Integrity', RUNTIME_ROOT/'01_Target_Edge_Ledger',
          RUNTIME_ROOT/'02_Scalar_Head', RUNTIME_ROOT/'03_Rank_Head',
          RUNTIME_ROOT/'04_Cluster_Conformal_Certification', RUNTIME_ROOT/'05_Theory_And_Diagnostics',
          RUNTIME_ROOT/'06_Figures', RUNTIME_ROOT/'07_Decision_And_Manuscript']:
    p.mkdir(parents=True, exist_ok=True)
P0=RUNTIME_ROOT/'00_Integrity'; P1=RUNTIME_ROOT/'01_Target_Edge_Ledger'; P2=RUNTIME_ROOT/'02_Scalar_Head'
P3=RUNTIME_ROOT/'03_Rank_Head'; P4=RUNTIME_ROOT/'04_Cluster_Conformal_Certification'
P5=RUNTIME_ROOT/'05_Theory_And_Diagnostics'; P6=RUNTIME_ROOT/'06_Figures'; P7=RUNTIME_ROOT/'07_Decision_And_Manuscript'


def now(): return datetime.now(timezone.utc).isoformat()
def sha_bytes(v): return hashlib.sha256(v).hexdigest()
def sha_json(v): return sha_bytes(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())
def sha_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()
def atomic_text(path,text):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(text,encoding='utf-8'); os.replace(tmp,path)
def write_json(path,v): atomic_text(path,json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def write_csv(path,df): atomic_text(path,df.to_csv(index=False,lineterminator='\n',float_format='%.12g'))
def verify_self_record(path,field='final_record_sha256'):
    v=json.loads(Path(path).read_text(encoding='utf-8')); claim=v[field]; core=dict(v); core.pop(field)
    assert sha_json(core)==claim, f'self-hash mismatch: {path}'; return v
def safe_rho(a,b):
    a=np.asarray(a,float); b=np.asarray(b,float)
    if len(a)<2 or np.nanstd(a)==0 or np.nanstd(b)==0: return np.nan
    return float(spearmanr(a,b).statistic)
def safe_extract(path,dest):
    dest=Path(dest); dest.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(path) as z:
        root=dest.resolve()
        for info in z.infolist():
            out=(dest/info.filename).resolve(); assert str(out).startswith(str(root))
        z.extractall(dest)
def finite_quantile(values,q):
    x=np.sort(np.asarray(values,float)); n=len(x)
    if n==0: return np.nan
    k=int(np.ceil((n+1)*q))-1; k=max(0,min(k,n-1)); return float(x[k])

# ---------- immutable parents ----------
T2F_ROOT=CM_ROOT/'StageT2-F_Development_Only_RA-CB-AMW-DDET_Risk_Adaptive_Covariate_Balance_And_Blind_Refreeze_v0.1'
T2F_REPS=T2F_ROOT/'01_RA_CB_Replicates'/'StageT2-F_RA-CB_All_Replicates_v0.1.csv'
T2F_DIAG=T2F_ROOT/'02_Mechanism_And_Applicability'/'StageT2-F_Selector_And_Balance_Diagnostics_v0.1.csv'
T4ABC_ROOT=CM_ROOT/'StageT4-ABC_Decomposed_Observability_And_MethodV1_Transparent_Validation_v0.1'
T4ABC_ZIP=T4ABC_ROOT/'StageT4-ABC_Canonical_Records_v0.1.zip'
T4ABC_COMPLETE=T4ABC_ROOT/'StageT4-ABC_Complete_v0.1.json'
required=[T2F_REPS,T2F_DIAG,T4ABC_ZIP,T4ABC_COMPLETE]
missing=[str(p) for p in required if not p.is_file()]
assert not missing, 'Missing immutable inputs:\n'+'\n'.join(missing)
t4=verify_self_record(T4ABC_COMPLETE)
assert t4['final_record_sha256']==EXPECTED_T4ABC_FINAL
assert t4['theory_decomposition_supported'] is True
assert t4['method_v1_upgrade_supported'] is False
assert t4['new_blind_accessed'] is False and t4['new_blind_access_authorised'] is False
integrity={'stage':'StageT4-DE','created_utc':now(),'parent_t4abc_final_record_sha256':EXPECTED_T4ABC_FINAL,
           't4abc_bundle_sha256':sha_file(T4ABC_ZIP),'transparent_development_only':True,
           'new_blind_accessed':False,'stage12_authorised':False}
integrity['integrity_record_sha256']=sha_json(integrity)
write_json(P0/'StageT4-DE_Parent_Integrity_Record_v0.1.json',integrity)
T4EX=P0/'t4abc_extract'; safe_extract(T4ABC_ZIP,T4EX)

# ---------- target-edge rather than replicate classification unit ----------
reps=pd.read_csv(T2F_REPS); diag=pd.read_csv(T2F_DIAG)
CANDS=['amw_u_recomputed','amw_cb2','ra_cb_amw_ddet','soft_ra_cb_audit']
assert reps['target'].nunique()==13 and reps['replicate'].nunique()==100
assert set(CANDS).issubset(set(reps['method'].unique()))
agg=(reps.groupby(['target','modality','source','edge_id','method'],as_index=False)
     .agg(estimate_median=('estimate_auc','median'),estimate_mean=('estimate_auc','mean'),estimate_std=('estimate_auc','std'),
          true_auc=('true_auc','first'),source_validation_auc=('source_validation_auc','first'),
          retention_threshold=('retention_threshold','first'),independent_groups=('independent_groups','first')))
wide=agg.pivot(index=['target','modality','source','edge_id'],columns='method',values=['estimate_median','estimate_mean','estimate_std']).reset_index()
wide.columns=['__'.join([str(x) for x in c if str(x)!='']) if isinstance(c,tuple) else c for c in wide.columns]
meta=(reps.groupby(['target','modality','source','edge_id'],as_index=False)
      .agg(true_auc=('true_auc','first'),source_validation_auc=('source_validation_auc','first'),
           retention_threshold=('retention_threshold','first'),independent_groups=('independent_groups','first')))
tdiag=(diag.groupby(['target','modality'],as_index=False)
       .agg(cb_admissible_rate=('cb_admissible','mean'),balance_selected_rate=('balance_selected','mean'),
            cv_brier_u=('cv_brier_amw_u','median'),cv_brier_cb2=('cv_brier_amw_cb2','median'),
            brier_diff=('cv_brier_difference_cb2_minus_u','median'),soft_selector_weight=('soft_selector_weight','median'),
            weight_ess=('weight_ess','median'),weight_min=('weight_min','median'),weight_max=('weight_max','median'),
            balance_residual=('balance_residual_max_standardized','median')))
edge=wide.merge(meta,on=['target','modality','source','edge_id']).merge(tdiag,on=['target','modality'])
edge['ra_estimate']=edge['estimate_median__ra_cb_amw_ddet']
edge['residual_to_ra']=edge['true_auc']-edge['ra_estimate']
for c,short in [('amw_u_recomputed','u'),('amw_cb2','cb2'),('soft_ra_cb_audit','soft')]:
    edge[f'delta_{short}_to_ra']=edge[f'estimate_median__{c}']-edge['ra_estimate']
edge['cross_method_range']=edge[[f'estimate_median__{c}' for c in CANDS]].max(axis=1)-edge[[f'estimate_median__{c}' for c in CANDS]].min(axis=1)
edge['cross_method_sd']=edge[[f'estimate_median__{c}' for c in CANDS]].std(axis=1)
write_csv(P1/'StageT4-DE_Target_Edge_Aggregated_Candidate_Ledger_v0.1.csv',edge)
unit_record={'independent_environment_units':int(edge['target'].nunique()),'edge_units':int(edge['edge_id'].nunique()),
             'raw_replicate_rows':int(len(reps)),'replicate_groups_per_target':int(reps['replicate'].nunique()),
             'training_unit':'target-edge with target-cluster cross-validation','replicate_level_oracle_classification_prohibited':True,
             'modality_categories':sorted(edge['modality'].unique().tolist())}
write_json(P5/'StageT4-DE_Environment_Unit_And_Modality_Record_v0.1.json',unit_record)

# ---------- scalar head: baseline-anchored continuous correction ----------
NUM=[
 'ra_estimate','delta_u_to_ra','delta_cb2_to_ra','delta_soft_to_ra','cross_method_range','cross_method_sd',
 'estimate_std__amw_u_recomputed','estimate_std__amw_cb2','estimate_std__ra_cb_amw_ddet','estimate_std__soft_ra_cb_audit',
 'source_validation_auc','retention_threshold','independent_groups','cb_admissible_rate','balance_selected_rate',
 'cv_brier_u','cv_brier_cb2','brier_diff','soft_selector_weight','weight_ess','weight_min','weight_max','balance_residual']
CAT=['modality']
METHOD_COLUMNS=[f'estimate_median__{c}' for c in CANDS]
RA_BASIS=np.array([0.,0.,1.,0.])

def target_weights(df):
    return df.groupby('target')['target'].transform(lambda x:1.0/len(x)).to_numpy(float)

def contextual_model(alpha):
    pre=ColumnTransformer([('num',StandardScaler(),NUM),('cat',OneHotEncoder(handle_unknown='ignore'),CAT)])
    return Pipeline([('pre',pre),('model',Ridge(alpha=float(alpha)))])

def fit_convex(df,lam):
    X=df[METHOD_COLUMNS].to_numpy(float); y=df['true_auc'].to_numpy(float); sw=target_weights(df)
    def obj(w):
        pred=X@w; smooth=np.sqrt((pred-y)**2+1e-6)
        return float(np.sum(sw*smooth)/np.sum(sw)+float(lam)*np.sum((w-RA_BASIS)**2))
    cons={'type':'eq','fun':lambda w:np.sum(w)-1.0}
    res=minimize(obj,RA_BASIS.copy(),method='SLSQP',bounds=[(0,1)]*4,constraints=cons,options={'maxiter':1000,'ftol':1e-10})
    assert res.success, res.message
    return res.x

def fit_predict_spec(train,test,spec):
    family,param=spec
    if family=='identity': return test['ra_estimate'].to_numpy(float),{'correction_cap':0.0}
    if family=='ridge':
        model=contextual_model(param); model.fit(train[NUM+CAT],train['residual_to_ra'],model__sample_weight=target_weights(train))
        correction=np.clip(model.predict(test[NUM+CAT]),-.10,.10)
        return np.clip(test['ra_estimate'].to_numpy(float)+correction,0,1),{'correction_cap':.10}
    if family=='convex':
        w=fit_convex(train,param); return np.clip(test[METHOD_COLUMNS].to_numpy(float)@w,0,1),{'weights':w.tolist()}
    raise ValueError(spec)

def equal_target_mae(df,pred):
    z=df[['target','true_auc']].copy(); z['pred']=np.asarray(pred,float)
    return float(z.groupby('target').apply(lambda q:np.mean(np.abs(q['pred']-q['true_auc'])),include_groups=False).mean())

def frozen_replicate_target_median_mae(validation_edges,pred):
    # Match the declared primary endpoint exactly: apply a held-target edge correction
    # to the frozen RA-CB replicate distribution, then take that target's median error.
    corr=validation_edges[['edge_id','ra_estimate']].copy()
    corr['edge_correction']=np.asarray(pred,float)-corr['ra_estimate'].to_numpy(float)
    vr=ra_rep_base[ra_rep_base['target'].isin(validation_edges['target'].unique())].merge(
        corr[['edge_id','edge_correction']],on='edge_id',validate='many_to_one')
    est=np.clip(vr['estimate_auc'].to_numpy(float)+vr['edge_correction'].to_numpy(float),0,1)
    return float(np.median(np.abs(est-vr['true_auc'].to_numpy(float))))

SPECS=[('identity',0.)]+[('ridge',a) for a in [.1,1.,10.,100.,1000.]]+[('convex',l) for l in [0.,.001,.01,.1,1.,10.]]
ra_rep_base=reps[reps['method'].eq('ra_cb_amw_ddet')].copy()
scalar_parts=[]; model_rows=[]
for outer in sorted(edge['target'].unique()):
    train=edge[edge['target'].ne(outer)].copy(); test=edge[edge['target'].eq(outer)].copy()
    inner_scores={}
    for spec in SPECS:
        vals=[]
        for inner in sorted(train['target'].unique()):
            tri=train[train['target'].ne(inner)]; vai=train[train['target'].eq(inner)]
            p,_=fit_predict_spec(tri,vai,spec); vals.append(frozen_replicate_target_median_mae(vai,p))
        inner_scores[spec]=float(np.mean(vals))
    identity_score=inner_scores[('identity',0.)]
    chosen=min(inner_scores,key=inner_scores.get)
    # A correction must show at least 2% target-cluster CV benefit; otherwise retain the frozen baseline.
    if chosen!=('identity',0.) and inner_scores[chosen] > identity_score*.98: chosen=('identity',0.)
    pred,details=fit_predict_spec(train,test,chosen)
    q=test[['target','modality','source','edge_id','true_auc','retention_threshold','ra_estimate']].copy()
    q['scalar_v2_estimate']=pred; q['edge_correction']=q['scalar_v2_estimate']-q['ra_estimate']
    q['selected_family']=chosen[0]; q['selected_parameter']=chosen[1]
    scalar_parts.append(q)
    model_rows.append({'outer_target':outer,'selected_family':chosen[0],'selected_parameter':chosen[1],
                       'inner_selected_equal_target_mae':inner_scores[chosen],'inner_identity_equal_target_mae':identity_score,
                       'inner_relative_improvement':(identity_score-inner_scores[chosen])/identity_score if identity_score else 0,
                       'details_json':json.dumps(details,sort_keys=True)})
scalar_edge=pd.concat(scalar_parts,ignore_index=True)
write_csv(P2/'StageT4-DE_Nested_LOTO_Scalar_Edge_Predictions_v0.1.csv',scalar_edge)
write_csv(P2/'StageT4-DE_Nested_LOTO_Scalar_Model_Ledger_v0.1.csv',pd.DataFrame(model_rows))

# Apply one held-target edge correction to the same frozen RA-CB replicate distribution.
ra_rep=ra_rep_base.copy()
rep_v2=ra_rep.merge(scalar_edge[['edge_id','edge_correction','selected_family','selected_parameter']],on='edge_id',validate='many_to_one')
rep_v2['scalar_v2_estimate']=np.clip(rep_v2['estimate_auc']+rep_v2['edge_correction'],0,1)
rep_v2['scalar_v2_absolute_error']=np.abs(rep_v2['scalar_v2_estimate']-rep_v2['true_auc'])
write_csv(P2/'StageT4-DE_Scalar_V2_Frozen_Replicate_Application_v0.1.csv',rep_v2)
scalar_target=(rep_v2.groupby(['target','modality'],as_index=False)
               .agg(ra_cb_target_median_mae=('absolute_error','median'),ra_cb_target_mean_mae=('absolute_error','mean'),
                    scalar_v2_target_median_mae=('scalar_v2_absolute_error','median'),scalar_v2_target_mean_mae=('scalar_v2_absolute_error','mean')))
write_csv(P2/'StageT4-DE_Scalar_Target_Performance_v0.1.csv',scalar_target)
ra_global=float(scalar_target['ra_cb_target_median_mae'].median()); v2_global=float(scalar_target['scalar_v2_target_median_mae'].median())
ra_edges=scalar_edge['ra_estimate']; v2_edges=scalar_edge['scalar_v2_estimate']; truth=scalar_edge['true_auc']
scalar_summary=pd.DataFrame([
 {'method':'ra_cb_amw_ddet','median_target_mae':ra_global,'mean_target_mae':float(scalar_target['ra_cb_target_median_mae'].mean()),'edge_spearman':safe_rho(ra_edges,truth)},
 {'method':'baseline_anchored_scalar_v2','median_target_mae':v2_global,'mean_target_mae':float(scalar_target['scalar_v2_target_median_mae'].mean()),'edge_spearman':safe_rho(v2_edges,truth)}])
write_csv(P2/'StageT4-DE_Scalar_Global_Comparison_v0.1.csv',scalar_summary)

# Oracle headroom is descriptive only and never enters v2 predictions.
method_target=(reps.groupby(['method','target'],as_index=False).agg(target_median_mae=('absolute_error','median')))
oracle=method_target.loc[method_target.groupby('target')['target_median_mae'].idxmin()].rename(columns={'method':'oracle_method','target_median_mae':'oracle_target_median_mae'})
ra_t=method_target[method_target['method'].eq('ra_cb_amw_ddet')][['target','target_median_mae']].rename(columns={'target_median_mae':'ra_target_median_mae'})
oracle=oracle.merge(ra_t,on='target'); oracle['oracle_improvement']=oracle['ra_target_median_mae']-oracle['oracle_target_median_mae']
write_csv(P5/'StageT4-DE_Descriptive_Oracle_Headroom_v0.1.csv',oracle)

# ---------- rank head: pairwise target-cluster model, separate from scalar head ----------
pair_rows=[]
for target,g in edge.groupby('target'):
    g=g.sort_values('edge_id').reset_index(drop=True)
    for i in range(len(g)):
        for j in range(i+1,len(g)):
            a,b=g.iloc[i],g.iloc[j]
            row={'target':target,'modality':a['modality'],'edge_i':a['edge_id'],'edge_j':b['edge_id'],
                 'label_i_better':int(a['true_auc']>b['true_auc'])}
            for c in CANDS:
                row[f'diff_{c}']=float(a[f'estimate_median__{c}']-b[f'estimate_median__{c}'])
            row['diff_validation']=float(a['source_validation_auc']-b['source_validation_auc'])
            row['diff_threshold']=float(a['retention_threshold']-b['retention_threshold'])
            row['abs_ra_gap']=abs(row['diff_ra_cb_amw_ddet'])
            pair_rows.append(row)
pairs=pd.DataFrame(pair_rows)
PAIR_NUM=[f'diff_{c}' for c in CANDS]+['diff_validation','diff_threshold','abs_ra_gap']

def rank_model(C):
    return Pipeline([('scale',StandardScaler()),('model',LogisticRegression(C=float(C),max_iter=2000,class_weight='balanced',random_state=SEED))])

def rank_scores_from_pairs(target_edges,pair_pred):
    scores={e:0.0 for e in target_edges}
    for r,p in zip(pair_pred.itertuples(index=False),pair_pred['p_i_better']):
        scores[r.edge_i]+=float(p); scores[r.edge_j]+=float(1-p)
    return scores

rank_parts=[]; rank_models=[]
for outer in sorted(edge['target'].unique()):
    tr=pairs[pairs['target'].ne(outer)].copy(); te=pairs[pairs['target'].eq(outer)].copy()
    specs=[('ra_fixed',0.),('cb2_fixed',0.)]+[('pair_logistic',C) for C in [.01,.1,1.,10.,100.]]
    scores={}
    for family,param in specs:
        vals=[]
        for inner in sorted(tr['target'].unique()):
            tri=tr[tr['target'].ne(inner)]; vai=tr[tr['target'].eq(inner)]
            if family=='ra_fixed': pred=(vai['diff_ra_cb_amw_ddet']>=0).astype(int).to_numpy()
            elif family=='cb2_fixed': pred=(vai['diff_amw_cb2']>=0).astype(int).to_numpy()
            else:
                if tri['label_i_better'].nunique()<2: pred=(vai['diff_ra_cb_amw_ddet']>=0).astype(int).to_numpy()
                else:
                    m=rank_model(param); m.fit(tri[PAIR_NUM],tri['label_i_better']); pred=(m.predict_proba(vai[PAIR_NUM])[:,1]>=.5).astype(int)
            vals.append(float(np.mean(pred==vai['label_i_better'].to_numpy())))
        scores[(family,param)]=float(np.mean(vals))
    ra_score=scores[('ra_fixed',0.)]
    chosen=max(scores,key=lambda x:(scores[x], x[0]=='ra_fixed', -x[1]))
    # Require material cluster-CV evidence before overriding the frozen ranking.
    if chosen[0]!='ra_fixed' and scores[chosen] < ra_score+.10: chosen=('ra_fixed',0.)
    te=te.copy()
    if chosen[0]=='ra_fixed': te['p_i_better']=(te['diff_ra_cb_amw_ddet']>=0).astype(float)
    elif chosen[0]=='cb2_fixed': te['p_i_better']=(te['diff_amw_cb2']>=0).astype(float)
    else:
        m=rank_model(chosen[1]); m.fit(tr[PAIR_NUM],tr['label_i_better']); te['p_i_better']=m.predict_proba(te[PAIR_NUM])[:,1]
    te['predicted_pair_label']=(te['p_i_better']>=.5).astype(int)
    te['selected_rank_family']=chosen[0]; te['selected_rank_parameter']=chosen[1]
    rank_parts.append(te)
    rank_models.append({'outer_target':outer,'selected_family':chosen[0],'selected_parameter':chosen[1],
                        'inner_selected_pairwise_accuracy':scores[chosen],'inner_ra_pairwise_accuracy':ra_score})
rank_pair=pd.concat(rank_parts,ignore_index=True)
write_csv(P3/'StageT4-DE_Nested_LOTO_Rank_Pair_Predictions_v0.1.csv',rank_pair)
write_csv(P3/'StageT4-DE_Nested_LOTO_Rank_Model_Ledger_v0.1.csv',pd.DataFrame(rank_models))
rank_target_rows=[]; rank_edge_rows=[]
for target,g in edge.groupby('target'):
    pp=rank_pair[rank_pair['target'].eq(target)]
    scores=rank_scores_from_pairs(g['edge_id'].tolist(),pp)
    q=g[['target','modality','edge_id','true_auc','ra_estimate','estimate_median__amw_cb2']].copy()
    q['rank_v2_score']=q['edge_id'].map(scores)
    rank_edge_rows.append(q)
    rank_target_rows.append({'target':target,'modality':g['modality'].iloc[0],
        'ra_rank_spearman':safe_rho(q['ra_estimate'],q['true_auc']),
        'cb2_rank_spearman':safe_rho(q['estimate_median__amw_cb2'],q['true_auc']),
        'rank_v2_spearman':safe_rho(q['rank_v2_score'],q['true_auc']),
        'rank_v2_pairwise_accuracy':float(np.mean(pp['predicted_pair_label']==pp['label_i_better'])),
        'pair_count':len(pp)})
rank_edges=pd.concat(rank_edge_rows,ignore_index=True); rank_target=pd.DataFrame(rank_target_rows)
write_csv(P3/'StageT4-DE_Rank_Edge_Scores_v0.1.csv',rank_edges)
write_csv(P3/'StageT4-DE_Rank_Target_Performance_v0.1.csv',rank_target)

# ---------- target-cluster conformal certificate ----------
# Cross-fitted target maxima are the calibration units, avoiding pseudo-replication across edges.
cert_rows=[]
for method,pcol in [('ra_cb','ra_estimate'),('scalar_v2','scalar_v2_estimate')]:
    z=scalar_edge[['target','edge_id','true_auc','retention_threshold',pcol]].copy()
    z['abs_residual']=np.abs(z[pcol]-z['true_auc'])
    target_max=z.groupby('target')['abs_residual'].max().to_dict()
    for target,g in z.groupby('target'):
        cal=[v for t,v in target_max.items() if t!=target]
        radius=finite_quantile(cal,1-CONFORMAL_ALPHA)
        for _,r in g.iterrows():
            lo=max(0,float(r[pcol]-radius)); hi=min(1,float(r[pcol]+radius)); truth=float(r['true_auc']); thr=float(r['retention_threshold'])
            decision='RETAIN' if lo>=thr else ('EXCLUDE' if hi<thr else 'ABSTAIN')
            true_decision='RETAIN' if truth>=thr else 'EXCLUDE'
            cert_rows.append({'method':method,'target':target,'edge_id':r['edge_id'],'alpha':CONFORMAL_ALPHA,'radius':radius,
                              'estimate':float(r[pcol]),'lower':lo,'upper':hi,'true_auc':truth,'retention_threshold':thr,
                              'covered':bool(lo<=truth<=hi),'decision':decision,'true_decision':true_decision,
                              'decided':decision!='ABSTAIN','wrong_decision':bool(decision!='ABSTAIN' and decision!=true_decision)})
cert=pd.DataFrame(cert_rows)
write_csv(P4/'StageT4-DE_Target_Cluster_Conformal_Edge_Certificates_v0.1.csv',cert)
cert_summary=[]
for method,g in cert.groupby('method'):
    decided=g[g['decided']]
    target_cov=g.groupby('target')['covered'].all()
    cert_summary.append({'method':method,'edge_coverage':float(g['covered'].mean()),'target_simultaneous_coverage':float(target_cov.mean()),
                         'decision_coverage':float(g['decided'].mean()),'wrong_decision_rate_among_decided':float(decided['wrong_decision'].mean()) if len(decided) else 0.0,
                         'mean_radius':float(g['radius'].mean())})
cert_summary=pd.DataFrame(cert_summary)
write_csv(P4/'StageT4-DE_Target_Cluster_Conformal_Summary_v0.1.csv',cert_summary)

# ---------- carry forward 23-target decomposition without refitting ----------
obs_path=list(T4EX.rglob('StageT4-ABC_Decomposed_Observability_Target_Vector_v0.1.csv'))
assert len(obs_path)==1
obs23=pd.read_csv(obs_path[0]); write_csv(P5/'StageT4-DE_Carried_Forward_23_Target_Decomposed_Observability_v0.1.csv',obs23)

# ---------- figures ----------
fig,ax=plt.subplots(figsize=(8,6)); ax.scatter(scalar_edge['ra_estimate'],scalar_edge['true_auc'],label='RA-CB',alpha=.8); ax.scatter(scalar_edge['scalar_v2_estimate'],scalar_edge['true_auc'],label='Scalar v2',alpha=.8)
ax.plot([.4,1],[.4,1],linestyle='--',linewidth=1); ax.set_xlabel('Estimated target AUC'); ax.set_ylabel('True target AUC'); ax.set_title('Baseline-anchored scalar head: strict target LOTO'); ax.legend(); fig.tight_layout(); fig.savefig(P6/'StageT4-DE_Scalar_LOTO_Calibration_v0.1.png',dpi=180); plt.close(fig)
fig,ax=plt.subplots(figsize=(9,5)); q=scalar_target.sort_values('ra_cb_target_median_mae'); x=np.arange(len(q)); ax.plot(x,q['ra_cb_target_median_mae'],marker='o',label='RA-CB'); ax.plot(x,q['scalar_v2_target_median_mae'],marker='o',label='Scalar v2'); ax.set_xticks(x); ax.set_xticklabels(q['target'],rotation=90,fontsize=8); ax.set_ylabel('Median replicate AUC error'); ax.set_title('Target-level scalar error'); ax.legend(); fig.tight_layout(); fig.savefig(P6/'StageT4-DE_Target_Scalar_Error_v0.1.png',dpi=180); plt.close(fig)
fig,ax=plt.subplots(figsize=(8,5)); qr=rank_target.sort_values('ra_rank_spearman'); x=np.arange(len(qr)); ax.plot(x,qr['ra_rank_spearman'],marker='o',label='RA-CB rank'); ax.plot(x,qr['rank_v2_spearman'],marker='o',label='Pairwise rank v2'); ax.set_xticks(x); ax.set_xticklabels(qr['target'],rotation=90,fontsize=8); ax.set_ylim(-1.1,1.1); ax.set_ylabel('Within-target Spearman'); ax.set_title('Independent rank head'); ax.legend(); fig.tight_layout(); fig.savefig(P6/'StageT4-DE_Rank_Head_Performance_v0.1.png',dpi=180); plt.close(fig)
fig,ax=plt.subplots(figsize=(7,5)); ax.scatter(cert_summary['decision_coverage'],cert_summary['wrong_decision_rate_among_decided']);
for _,r in cert_summary.iterrows(): ax.annotate(r['method'],(r['decision_coverage'],r['wrong_decision_rate_among_decided']))
ax.axhline(.05,linestyle='--',linewidth=1); ax.set_xlabel('Decision coverage'); ax.set_ylabel('Wrong-decision rate'); ax.set_title('Target-cluster conformal certification'); fig.tight_layout(); fig.savefig(P6/'StageT4-DE_Certificate_Safety_v0.1.png',dpi=180); plt.close(fig)

# ---------- gates and decision ----------
ra_rank_med=float(rank_target['ra_rank_spearman'].median()); v2_rank_med=float(rank_target['rank_v2_spearman'].median())
ra_pair=[]
for _,r in rank_pair.iterrows(): ra_pair.append(int((r['diff_ra_cb_amw_ddet']>0)==bool(r['label_i_better'])))
ra_pair_acc=float(np.mean(ra_pair)); v2_pair_acc=float(np.mean(rank_pair['predicted_pair_label']==rank_pair['label_i_better']))
c_ra=cert_summary[cert_summary['method'].eq('ra_cb')].iloc[0]; c_v2=cert_summary[cert_summary['method'].eq('scalar_v2')].iloc[0]
scalar_upgrade=bool(v2_global<=ra_global*.98)
scalar_noninferior=bool(v2_global<=ra_global*1.02)
rank_upgrade=bool((v2_rank_med>=ra_rank_med) and (v2_pair_acc>=ra_pair_acc))
cert_safe=bool(c_v2['target_simultaneous_coverage']>=.90 and c_v2['wrong_decision_rate_among_decided']<=.05)
cert_useful=bool(c_v2['decision_coverage']>=c_ra['decision_coverage'])
gates=pd.DataFrame([
 {'gate':'parent_t4abc_integrity','passed':True,'observed':EXPECTED_T4ABC_FINAL},
 {'gate':'environment_is_target_not_replicate','passed':unit_record['independent_environment_units']==13,'observed':f"targets=13; raw rows={len(reps)}"},
 {'gate':'modality_retained_as_categorical_feature','passed':len(unit_record['modality_categories'])==4,'observed':'|'.join(unit_record['modality_categories'])},
 {'gate':'scalar_v2_improves_ra_cb','passed':scalar_upgrade,'observed':f'{v2_global:.6f} vs {ra_global:.6f}'},
 {'gate':'scalar_v2_noninferior_ra_cb','passed':scalar_noninferior,'observed':f'{v2_global:.6f} vs {ra_global:.6f}'},
 {'gate':'independent_rank_head_improves_or_preserves','passed':rank_upgrade,'observed':f'median rho {v2_rank_med:.6f} vs {ra_rank_med:.6f}; pair {v2_pair_acc:.6f} vs {ra_pair_acc:.6f}'},
 {'gate':'target_cluster_conformal_safety','passed':cert_safe,'observed':f"target coverage={c_v2['target_simultaneous_coverage']:.6f}; wrong={c_v2['wrong_decision_rate_among_decided']:.6f}"},
 {'gate':'certificate_decision_coverage_not_reduced','passed':cert_useful,'observed':f"v2={c_v2['decision_coverage']:.6f}; RA={c_ra['decision_coverage']:.6f}"},
 {'gate':'new_blind_accessed','passed':True,'observed':False},
 {'gate':'stage12_authorised','passed':True,'observed':False},
])
write_csv(P7/'StageT4-DE_Frozen_Transparent_Gates_v0.1.csv',gates)
if scalar_upgrade and rank_upgrade and cert_safe and cert_useful:
    decision='SEAL_T4DE_METHOD_V2_MULTIFUNCTIONAL_AUDIT_AUTHORISE_NEW_RESERVE_DESIGN_ONLY'
elif scalar_noninferior and cert_safe:
    decision='SEAL_T4DE_METHOD_V2_PARTIAL_SUPPORT_CONTINUE_TRANSPARENT_DEVELOPMENT_PROHIBIT_NEW_BLIND'
else:
    decision='SEAL_T4DE_METHOD_V2_NOT_SUPPORTED_CONTINUE_THEORY_AND_METHOD_DEVELOPMENT_PROHIBIT_NEW_BLIND'
complete={'stage':'StageT4-DE','decision':decision,'transparent_development_only':True,
          'parent_t4abc_final_record_sha256':EXPECTED_T4ABC_FINAL,'independent_targets':13,'edges':27,
          'ra_cb_median_target_mae':ra_global,'scalar_v2_median_target_mae':v2_global,
          'ra_edge_spearman':float(scalar_summary.loc[scalar_summary.method.eq('ra_cb_amw_ddet'),'edge_spearman'].iloc[0]),
          'scalar_v2_edge_spearman':float(scalar_summary.loc[scalar_summary.method.eq('baseline_anchored_scalar_v2'),'edge_spearman'].iloc[0]),
          'ra_median_within_target_rank':ra_rank_med,'rank_v2_median_within_target_rank':v2_rank_med,
          'ra_pairwise_accuracy':ra_pair_acc,'rank_v2_pairwise_accuracy':v2_pair_acc,
          'scalar_upgrade_supported':scalar_upgrade,'scalar_noninferiority_supported':scalar_noninferior,
          'rank_head_supported':rank_upgrade,'target_cluster_conformal_safe':cert_safe,'certificate_useful':cert_useful,
          'new_blind_accessed':False,'new_blind_access_authorised':False,'stage12_authorised':False,'completed_utc':now()}
complete['final_record_sha256']=sha_json(complete)
write_json(P7/'StageT4-DE_Complete_v0.1.json',complete)
summary=f'''# Stage T4-DE baseline-anchored multi-functional audit result\n\n- Decision: `{decision}`\n- Independent target environments / edges: `13` / `27`\n- Frozen RA-CB / scalar-v2 median target MAE: `{ra_global:.6f}` / `{v2_global:.6f}`\n- Frozen RA-CB / scalar-v2 edge Spearman: `{complete['ra_edge_spearman']:.6f}` / `{complete['scalar_v2_edge_spearman']:.6f}`\n- RA-CB / independent rank-v2 median within-target Spearman: `{ra_rank_med:.6f}` / `{v2_rank_med:.6f}`\n- RA-CB / rank-v2 pairwise accuracy: `{ra_pair_acc:.6f}` / `{v2_pair_acc:.6f}`\n- Scalar upgrade supported: `{scalar_upgrade}`\n- Scalar noninferiority supported: `{scalar_noninferior}`\n- Independent rank head supported: `{rank_upgrade}`\n- Target-cluster conformal safety supported: `{cert_safe}`\n- Certificate decision coverage not reduced: `{cert_useful}`\n- New blind authorised: `False`\n- Stage 12 authorised: `False`\n- Final record SHA256: `{complete['final_record_sha256']}`\n'''
atomic_text(P7/'StageT4-DE_Result_Summary_v0.1.md',summary)
manuscript=f'''# Manuscript-ready Stage T4-DE insert\n\nStage T4-DE replaced replicate-level method classification with a target-cluster design. Candidate estimates were aggregated at the directed target-edge level, modality was retained as an explicit categorical variable, and all hyperparameter and method choices were nested within leave-one-target-out validation. The scalar head estimated a continuous correction to the frozen RA-CB baseline or a constrained convex mixture only when inner target-cluster validation showed a prespecified benefit; otherwise it reverted to the frozen baseline. Applied to the original frozen RA-CB replicate distribution, the scalar head achieved a median target-level absolute AUC error of {v2_global:.4f}, compared with {ra_global:.4f} for RA-CB. A separate pairwise rank head achieved median within-target Spearman {v2_rank_med:.3f} and pairwise accuracy {v2_pair_acc:.3f}, compared with {ra_rank_med:.3f} and {ra_pair_acc:.3f} for RA-CB ranking. Target-cluster conformal calibration treated each target, rather than each edge or replicate, as one calibration unit and achieved simultaneous target coverage {c_v2['target_simultaneous_coverage']:.3f}, wrong-decision rate {c_v2['wrong_decision_rate_among_decided']:.3f}, and decision coverage {c_v2['decision_coverage']:.3f}. This transparent stage does not reinterpret the Stage T3-A failure and does not access or authorize a new blind reserve.\n'''
atomic_text(P7/'StageT4-DE_Manuscript_Insert_v0.1.md',manuscript)

# ---------- canonical durable commit ----------
bundle=RUNTIME_ROOT/'StageT4-DE_Canonical_Records_v0.1.zip'
with zipfile.ZipFile(bundle,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(RUNTIME_ROOT.rglob('*')):
        if p.is_file() and p!=bundle and '.tmp' not in p.name: z.write(p,p.relative_to(RUNTIME_ROOT))
commit_files=[bundle,P7/'StageT4-DE_Complete_v0.1.json',P7/'StageT4-DE_Result_Summary_v0.1.md',P7/'StageT4-DE_Frozen_Transparent_Gates_v0.1.csv',P2/'StageT4-DE_Scalar_Global_Comparison_v0.1.csv',P3/'StageT4-DE_Rank_Target_Performance_v0.1.csv',P4/'StageT4-DE_Target_Cluster_Conformal_Summary_v0.1.csv']
COMMIT_ROOT.mkdir(parents=True,exist_ok=True); manifest_rows=[]
for src in commit_files:
    dst=COMMIT_ROOT/src.name; shutil.copy2(src,dst); assert sha_file(dst)==sha_file(src)
    manifest_rows.append({'file':src.name,'bytes':src.stat().st_size,'sha256':sha_file(src),'drive_path':str(dst)})
manifest={'stage':'StageT4-DE','commit_root':str(COMMIT_ROOT),'canonical_bundle_sha256':sha_file(bundle),'files':manifest_rows,
          'all_drive_copies_reopened_and_hash_verified':True,'new_blind_access_authorised':False,'stage12_authorised':False,'committed_utc':now()}
manifest['commit_manifest_sha256']=sha_json(manifest)
write_json(COMMIT_ROOT/'StageT4-DE_Durable_Commit_Manifest_v0.1.json',manifest)
assert verify_self_record(COMMIT_ROOT/'StageT4-DE_Complete_v0.1.json')['final_record_sha256']==complete['final_record_sha256']

print('\n========== STAGE T4-DE COMPLETE ==========')
print('Decision:',decision)
print('Independent targets / edges:',13,27)
print('RA-CB / scalar-v2 median target MAE:',ra_global,v2_global)
print('RA-CB / rank-v2 median within-target Spearman:',ra_rank_med,v2_rank_med)
print('Scalar upgrade supported:',scalar_upgrade)
print('Rank head supported:',rank_upgrade)
print('Target-cluster conformal safe:',cert_safe)
print('New blind authorised:',False)
print('Stage 12 authorised:',False)
print('Final record SHA256:',complete['final_record_sha256'])
print('Committed to:',COMMIT_ROOT)
display(gates)
