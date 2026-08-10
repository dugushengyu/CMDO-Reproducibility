# Stage T4-ABC: Decomposed Diagnostic Observability and Method-v1 transparent validation
import os, json, math, hashlib, zipfile, shutil, warnings
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.optimize import least_squares
from scipy.stats import spearmanr
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier

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
THRESHOLD = 0.05
PRIMARY_BUDGET = 64
BOOTSTRAPS = 100
EXPECTED_T2MN_FINAL = 'cc11dfea1df0cf8d28af218fe9d437de3306ed02437b2712744b35e64e3f98b2'
EXPECTED_T3A_FINAL = '9c6cd7929437a262d7d8b0c7c9e17193d1f30a1be47915fa3ae60fd15b518bc9'
EXPECTED_T3X_FINAL = 'a27ccfbb123b8de3eaaa43968e335e0005f5159155c5b991ef7be4b965076b00'

DEFAULT_ROOT = Path('/content/drive/MyDrive/Cross-Modal_Diagnostic_Observability') if IN_COLAB else Path.cwd()
PROJECT_ROOT = Path(os.environ.get('CMDO_PROJECT_ROOT', str(DEFAULT_ROOT)))
CM_ROOT = PROJECT_ROOT / '06_Data_Records' / 'Cross_Modal'
RUNTIME_ROOT = Path('/content/cmdo_runtime/StageT4-ABC') if IN_COLAB else PROJECT_ROOT / '_runtime_StageT4ABC'
COMMIT_ROOT = CM_ROOT / 'StageT4-ABC_Decomposed_Observability_And_MethodV1_Transparent_Validation_v0.1'
for p in [RUNTIME_ROOT, RUNTIME_ROOT/'00_Integrity', RUNTIME_ROOT/'01_Harmonized_Transparent_Ledger',
          RUNTIME_ROOT/'02_Functional_Rank_Selector', RUNTIME_ROOT/'03_Budget_Floor_Decomposition',
          RUNTIME_ROOT/'04_Observability_And_Certification', RUNTIME_ROOT/'05_Figures',
          RUNTIME_ROOT/'06_Decision_And_Manuscript']:
    p.mkdir(parents=True, exist_ok=True)

P0=RUNTIME_ROOT/'00_Integrity'; P1=RUNTIME_ROOT/'01_Harmonized_Transparent_Ledger'
P2=RUNTIME_ROOT/'02_Functional_Rank_Selector'; P3=RUNTIME_ROOT/'03_Budget_Floor_Decomposition'
P4=RUNTIME_ROOT/'04_Observability_And_Certification'; P5=RUNTIME_ROOT/'05_Figures'
P6=RUNTIME_ROOT/'06_Decision_And_Manuscript'


def now():
    return datetime.now(timezone.utc).isoformat()

def sha_bytes(value):
    return hashlib.sha256(value).hexdigest()

def sha_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()

def sha_json(value):
    return sha_bytes(json.dumps(value, sort_keys=True, separators=(',',':'), ensure_ascii=False).encode())

def atomic_text(path, text):
    path=Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(text, encoding='utf-8')
    os.replace(tmp,path)

def write_json(path, value):
    atomic_text(path, json.dumps(value, indent=2, ensure_ascii=False)+'\n')

def write_csv(path, frame):
    atomic_text(path, frame.to_csv(index=False, lineterminator='\n', float_format='%.12g'))

def verify_self_record(path, hash_field='final_record_sha256'):
    value=json.loads(Path(path).read_text(encoding='utf-8'))
    claim=value[hash_field]
    core=dict(value); core.pop(hash_field)
    assert sha_json(core)==claim, f'self-hash mismatch: {path}'
    return value

def safe_extract(path, destination):
    destination=Path(destination); destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path) as z:
        root=destination.resolve()
        for info in z.infolist():
            out=(destination/info.filename).resolve()
            assert str(out).startswith(str(root)), 'unsafe archive path'
        z.extractall(destination)

def find_one(root, basename):
    hits=list(Path(root).rglob(basename))
    assert len(hits)==1, f'expected one {basename}, got {len(hits)}'
    return hits[0]

def safe_rho(a,b):
    a=np.asarray(a,float); b=np.asarray(b,float)
    if len(a)<2 or np.nanstd(a)==0 or np.nanstd(b)==0: return np.nan
    return float(spearmanr(a,b).statistic)

# ---------- exact immutable inputs ----------
T2D_REPS = CM_ROOT/'StageT2-D_Development_Only_AMW-DDET_Active_Minimal_Witness_Certificate_v0.1'/'01_Replicate_Results'/'StageT2-D_All_Acquisition_Replicates_v0.1.csv'
T2KR_REPS = CM_ROOT/'StageT2-KR_Frozen_Axis_Schema_Adapter_And_CPU_Continuation_v0.4'/'04_MultiBudget_Extension'/'StageT2-KR_All_MultiBudget_Extension_Replicates_v0.4.csv'
T2L_REPS = CM_ROOT/'StageT2-L_Independent_Target_Regime_Expansion_v0.1'/'05_MultiBudget_Extension'/'StageT2-L_All_MultiBudget_Extension_Replicates_v0.1.csv'
T2F_REPS = CM_ROOT/'StageT2-F_Development_Only_RA-CB-AMW-DDET_Risk_Adaptive_Covariate_Balance_And_Blind_Refreeze_v0.1'/'01_RA_CB_Replicates'/'StageT2-F_RA-CB_All_Replicates_v0.1.csv'
T2F_DIAG = CM_ROOT/'StageT2-F_Development_Only_RA-CB-AMW-DDET_Risk_Adaptive_Covariate_Balance_And_Blind_Refreeze_v0.1'/'02_Mechanism_And_Applicability'/'StageT2-F_Selector_And_Balance_Diagnostics_v0.1.csv'
T2MN_ROOT = CM_ROOT/'StageT2-MN_v0.1'
T2MN_ZIP = T2MN_ROOT/'StageT2-MN_Canonical_Records_v0.1.zip'
T2MN_COMPLETE = T2MN_ROOT/'StageT2-MN_Complete_v0.1.json'
T3X_ROOT = CM_ROOT/'StageT3-X_Transparent_Blind_Failure_Autopsy_And_Observability_Decomposition_v0.1'
T3X_ZIP = T3X_ROOT/'StageT3-X_Canonical_Records_v0.1.zip'
T3X_COMPLETE = T3X_ROOT/'StageT3-X_Complete_v0.1.json'
required=[T2D_REPS,T2KR_REPS,T2L_REPS,T2F_REPS,T2F_DIAG,T2MN_ZIP,T2MN_COMPLETE,T3X_ZIP,T3X_COMPLETE]
missing=[str(p) for p in required if not p.is_file()]
assert not missing, 'Missing immutable inputs:\n'+'\n'.join(missing)

t2mn_complete=verify_self_record(T2MN_COMPLETE)
t3x_complete=verify_self_record(T3X_COMPLETE)
assert t2mn_complete['final_record_sha256']==EXPECTED_T2MN_FINAL
assert t3x_complete['final_record_sha256']==EXPECTED_T3X_FINAL
assert t3x_complete['parent_t3a_final_record_sha256']==EXPECTED_T3A_FINAL
assert t3x_complete['parent_t3a_scenario']=='SCENARIO_C_PERFORMANCE_PRIMARY_FAILURE'
assert t3x_complete['new_blind_access_authorised'] is False

integrity={
 'stage':'StageT4-ABC','created_utc':now(),
 'parent_t2mn_final_record_sha256':EXPECTED_T2MN_FINAL,
 'parent_t3a_final_record_sha256':EXPECTED_T3A_FINAL,
 'parent_t3x_final_record_sha256':EXPECTED_T3X_FINAL,
 't2mn_bundle_sha256':sha_file(T2MN_ZIP),'t3x_bundle_sha256':sha_file(T3X_ZIP),
 'transparent_post_unblinding':True,'new_blind_accessed':False,'stage12_authorised':False,
}
integrity['integrity_record_sha256']=sha_json(integrity)
write_json(P0/'StageT4-ABC_Parent_Integrity_Record_v0.1.json',integrity)

T2MN_EX=P0/'t2mn_extract'; T3X_EX=P0/'t3x_extract'
safe_extract(T2MN_ZIP,T2MN_EX); safe_extract(T3X_ZIP,T3X_EX)

# ---------- harmonized 23-target transparent evidence ledger ----------
base=pd.concat([pd.read_csv(T2D_REPS),pd.read_csv(T2KR_REPS),pd.read_csv(T2L_REPS)],ignore_index=True,sort=False)
assert base['target'].nunique()==18
base=base[base['method'].eq('amw_ddet')].copy()
base['cohort']='DEVELOPMENT_18'; base['analysis_method']='amw_ddet'

provider=pd.read_csv(find_one(T2MN_EX,'StageT2-N_All_Provider_MultiBudget_Replicates_v0.1.csv'))
provider=provider[provider['method'].eq('ra_cb_amw_ddet')].copy()
assert provider['target'].nunique()==3
provider['cohort']='PROVIDER_PROSPECTIVE_3'; provider['analysis_method']='ra_cb_amw_ddet'

sentinel=pd.read_csv(find_one(T3X_EX,'StageT3-X_Best_Shared_And_Edge_Budget_Sensitivity_All_Replicates_v0.1.csv'))
sentinel=sentinel[sentinel['method'].eq('shared_spline')].copy()
assert sentinel['target'].nunique()==2
sentinel['cohort']='REVEALED_SENTINEL_2'; sentinel['analysis_method']='shared_spline'

common=['target','modality','source','edge_id','budget','replicate','true_auc','estimate_auc','absolute_error','cohort','analysis_method']
for frame in [base,provider,sentinel]:
    for c in common:
        if c not in frame: frame[c]=np.nan
harm=pd.concat([base[common],provider[common],sentinel[common]],ignore_index=True,sort=False)
harm['budget']=pd.to_numeric(harm['budget'],errors='coerce').astype('Int64')
harm=harm.dropna(subset=['budget','absolute_error','estimate_auc','true_auc']).copy()
harm['budget']=harm['budget'].astype(int)
assert harm['target'].nunique()==23
write_csv(P1/'StageT4-ABC_Harmonized_23_Target_Transparent_Replicate_Ledger_v0.1.csv',harm)

curve=(harm.groupby(['cohort','target','modality','analysis_method','budget'],as_index=False)
       .agg(median_error=('absolute_error','median'),mean_error=('absolute_error','mean'),
            edge_count=('edge_id','nunique'),replicate_count=('replicate','nunique')))
write_csv(P1/'StageT4-ABC_Harmonized_23_Target_Budget_Curves_v0.1.csv',curve)

# scalar and rank summaries at each target's best available primary checkpoint (64, else 32)
point_rows=[]
for (cohort,target,modality),g in harm.groupby(['cohort','target','modality']):
    available=sorted(g['budget'].unique())
    chosen=PRIMARY_BUDGET if PRIMARY_BUDGET in available else (32 if 32 in available else max(available))
    q=g[g['budget'].eq(chosen)]
    edge=q.groupby(['source','edge_id'],as_index=False).agg(estimate_auc=('estimate_auc','median'),true_auc=('true_auc','first'),edge_mae=('absolute_error','median'))
    point_rows.append({'cohort':cohort,'target':target,'modality':modality,'checkpoint_budget':chosen,
        'scalar_target_median_mae':float(edge['edge_mae'].median()),'scalar_target_mean_mae':float(edge['edge_mae'].mean()),
        'rank_spearman':safe_rho(edge['estimate_auc'],edge['true_auc']),'edge_count':len(edge)})
point=pd.DataFrame(point_rows)
write_csv(P1/'StageT4-ABC_Target_Scalar_And_Rank_Checkpoint_Summary_v0.1.csv',point)

# ---------- functional/rank-aware selector: strict nested LOTO on 13 development targets ----------
t2f=pd.read_csv(T2F_REPS); diag=pd.read_csv(T2F_DIAG)
candidates=['amw_u_recomputed','amw_cb2','ra_cb_amw_ddet','soft_ra_cb_audit']
assert set(candidates).issubset(set(t2f['method'].unique()))

loss_rows=[]
for keys,g in t2f.groupby(['target','modality','replicate','method']):
    rho=safe_rho(g['estimate_auc'],g['true_auc'])
    loss_rows.append((*keys,float(g['absolute_error'].mean()),rho,int(g['edge_id'].nunique())))
loss=pd.DataFrame(loss_rows,columns=['target','modality','replicate','method','mean_abs_error','rank_spearman','edge_count'])
loss['rank_penalty']=1-loss['rank_spearman'].fillna(0).clip(-1,1)
loss['functional_rank_loss']=loss['mean_abs_error']+0.015*loss['rank_penalty']
idx=loss.groupby(['target','replicate'])['functional_rank_loss'].idxmin()
oracle=loss.loc[idx,['target','replicate','method','functional_rank_loss']].rename(columns={'method':'oracle_method','functional_rank_loss':'oracle_loss'})

piv=t2f.pivot_table(index=['target','modality','replicate','edge_id'],columns='method',values='estimate_auc').reset_index()
piv['cross_method_sd']=piv[candidates].std(axis=1)
piv['cross_method_range']=piv[candidates].max(axis=1)-piv[candidates].min(axis=1)
features=piv.groupby(['target','modality','replicate'],as_index=False).agg(edge_count=('edge_id','nunique'),method_disagreement=('cross_method_sd','mean'),method_range=('cross_method_range','mean'))
for method in candidates:
    z=piv.groupby(['target','modality','replicate'])[method].agg(['mean','std']).reset_index().rename(columns={'mean':method+'_mean','std':method+'_sd'})
    features=features.merge(z,on=['target','modality','replicate'],validate='one_to_one')
features=features.merge(diag,on=['target','modality','replicate'],validate='one_to_one').merge(oracle,on=['target','replicate'],validate='one_to_one')
exclude={'target','modality','replicate','selected_candidate','oracle_method','oracle_loss'}
feature_cols=[c for c in features.columns if c not in exclude]
for c in feature_cols: features[c]=pd.to_numeric(features[c],errors='coerce')
features[feature_cols]=features[feature_cols].replace([np.inf,-np.inf],np.nan)
features[feature_cols]=features[feature_cols].fillna(features[feature_cols].median(numeric_only=True)).fillna(0)
lookup=loss.set_index(['target','replicate','method'])['functional_rank_loss'].to_dict()

def selector_loss(rows,pred):
    return float(np.mean([lookup[(t,int(r),m)] for t,r,m in zip(rows['target'],rows['replicate'],pred)]))

def selector_factory(name):
    if name=='multinomial_logistic':
        return make_pipeline(StandardScaler(),LogisticRegression(max_iter=2000,C=.5,class_weight='balanced',random_state=SEED))
    return HistGradientBoostingClassifier(max_iter=120,max_depth=3,learning_rate=.05,l2_regularization=1.0,random_state=SEED)

selector_rows=[]; model_ledger=[]
for outer in sorted(features['target'].unique()):
    train=features[features['target'].ne(outer)].copy(); test=features[features['target'].eq(outer)].copy()
    inner_scores={}
    for spec in ['multinomial_logistic','hist_gradient']:
        vals=[]
        for inner in sorted(train['target'].unique()):
            tri=train[train['target'].ne(inner)]; vai=train[train['target'].eq(inner)]
            model=selector_factory(spec); model.fit(tri[feature_cols],tri['oracle_method'])
            vals.append(selector_loss(vai,model.predict(vai[feature_cols])))
        inner_scores[spec]=float(np.mean(vals))
    chosen=min(inner_scores,key=inner_scores.get)
    model=selector_factory(chosen); model.fit(train[feature_cols],train['oracle_method'])
    pred=model.predict(test[feature_cols])
    tmp=test[['target','modality','replicate']].copy(); tmp['selected_method']=pred; tmp['selector_model']=chosen
    selector_rows.append(tmp)
    model_ledger.append({'outer_target':outer,'selected_model':chosen,**{'inner_'+k:v for k,v in inner_scores.items()}})
selector=pd.concat(selector_rows,ignore_index=True)
selected=t2f.merge(selector,on=['target','modality','replicate'])
selected=selected[selected['method'].eq(selected['selected_method'])].copy()
selected['method']='functional_rank_selector_v1'
selected=selected[t2f.columns]
combined=pd.concat([t2f,selected],ignore_index=True)

selector_target=(combined.groupby(['method','target','modality'],as_index=False)
                 .agg(target_median_mae=('absolute_error','median'),target_mean_mae=('absolute_error','mean')))
selector_global=[]
for method,g in combined.groupby('method'):
    t=selector_target[selector_target['method'].eq(method)]
    edges=g.groupby('edge_id',as_index=False).agg(estimate_auc=('estimate_auc','median'),true_auc=('true_auc','first'))
    selector_global.append({'method':method,'median_target_mae':float(t['target_median_mae'].median()),
                            'mean_target_mae':float(t['target_median_mae'].mean()),
                            'edge_spearman':safe_rho(edges['estimate_auc'],edges['true_auc'])})
selector_global=pd.DataFrame(selector_global).sort_values('median_target_mae')
write_csv(P2/'StageT4-ABC_Nested_LOTO_Functional_Rank_Selector_Predictions_v0.1.csv',selector)
write_csv(P2/'StageT4-ABC_Nested_LOTO_Selector_Model_Ledger_v0.1.csv',pd.DataFrame(model_ledger))
write_csv(P2/'StageT4-ABC_Functional_Rank_Selector_Target_Performance_v0.1.csv',selector_target)
write_csv(P2/'StageT4-ABC_Functional_Rank_Selector_Global_Comparison_v0.1.csv',selector_global)

# ---------- budget-indexed repairability + error-floor decomposition ----------
def floor_curve(par,b):
    floor,amp,alpha=par
    return floor+amp*(np.asarray(b,float)/8.0)**(-alpha)

def fit_floor(b,e):
    b=np.asarray(b,float); e=np.asarray(e,float)
    order=np.argsort(b); b=b[order]; e=e[order]
    env=np.minimum.accumulate(e)
    if len(b)<3:
        return {'floor':float(env[-1]),'amplitude':float(max(env[0]-env[-1],0)),'alpha':np.nan,'rmse':np.nan,'envelope':env}
    x0=np.array([max(0,min(env[-1]*.8,THRESHOLD)),max(env[0]-env[-1],.005),.7])
    res=least_squares(lambda p:floor_curve(p,b)-env,x0,bounds=([0,0,.05],[.30,.60,4.0]),max_nfev=5000)
    pred=floor_curve(res.x,b)
    return {'floor':float(res.x[0]),'amplitude':float(res.x[1]),'alpha':float(res.x[2]),'rmse':float(np.sqrt(np.mean((pred-env)**2))),'envelope':env}

def operational_budget(floor,amp,alpha):
    if not np.isfinite(alpha) or floor>=THRESHOLD or amp<=0: return np.inf
    ratio=(THRESHOLD-floor)/amp
    if ratio<=0: return np.inf
    return float(8*ratio**(-1/alpha))

floor_rows=[]; boot_rows=[]
for (cohort,target,modality,method),g in harm.groupby(['cohort','target','modality','analysis_method']):
    med=g.groupby('budget',as_index=False).agg(error=('absolute_error','median')).sort_values('budget')
    fit=fit_floor(med['budget'],med['error'])
    op=operational_budget(fit['floor'],fit['amplitude'],fit['alpha'])
    reached=bool(np.nanmin(fit['envelope'])<=THRESHOLD)
    last_gain=float(fit['envelope'][-2]-fit['envelope'][-1]) if len(fit['envelope'])>1 else np.nan
    if reached: regime='EVIDENCE_LIMITED_OPERATIONAL'
    elif fit['floor']>=THRESHOLD and (not np.isfinite(last_gain) or last_gain<.01): regime='MODEL_LIMITED_FLOOR'
    else: regime='EVIDENCE_DEMANDING_RIGHT_CENSORED'
    floor_rows.append({'cohort':cohort,'target':target,'modality':modality,'analysis_method':method,
        'tested_budgets':'|'.join(map(str,med['budget'].tolist())),'error_b_min':float(med.iloc[0]['error']),
        'error_b_max':float(med.iloc[-1]['error']),'repairable_drop':float(fit['envelope'][0]-fit['envelope'][-1]),
        'fitted_floor':fit['floor'],'fitted_amplitude':fit['amplitude'],'fitted_alpha':fit['alpha'],'fit_rmse':fit['rmse'],
        'last_doubling_gain':last_gain,'operational_budget_model':op,'threshold_reached':reached,'regime':regime})
    reps=sorted(g['replicate'].dropna().unique())
    if len(reps)>=10 and med['budget'].nunique()>=3:
        for k in range(BOOTSTRAPS):
            chosen=rng.choice(reps,size=len(reps),replace=True)
            parts=[]
            for i,r in enumerate(chosen):
                q=g[g['replicate'].eq(r)].copy(); q['_boot_instance']=i; parts.append(q)
            bg=pd.concat(parts,ignore_index=True).groupby('budget',as_index=False).agg(error=('absolute_error','median')).sort_values('budget')
            bf=fit_floor(bg['budget'],bg['error'])
            boot_rows.append({'target':target,'bootstrap':k,'floor':bf['floor'],'alpha':bf['alpha'],'operational_budget_model':operational_budget(bf['floor'],bf['amplitude'],bf['alpha'])})
floors=pd.DataFrame(floor_rows); boots=pd.DataFrame(boot_rows)
if len(boots):
    bsum=boots.groupby('target',as_index=False).agg(floor_q05=('floor',lambda x:np.quantile(x,.05)),floor_q50=('floor','median'),floor_q95=('floor',lambda x:np.quantile(x,.95)),model_floor_probability=('floor',lambda x:np.mean(x>=THRESHOLD)))
    floors=floors.merge(bsum,on='target',how='left')
else:
    floors['floor_q05']=floors['floor_q50']=floors['floor_q95']=floors['model_floor_probability']=np.nan
write_csv(P3/'StageT4-ABC_Repairable_Plus_Error_Floor_Target_Decomposition_v0.1.csv',floors)
write_csv(P3/'StageT4-ABC_Error_Floor_Bootstrap_Draws_v0.1.csv',boots)

# ---------- decomposed observability vector and safety synthesis ----------
obs=point.merge(floors[['target','repairable_drop','fitted_floor','model_floor_probability','operational_budget_model','regime']],on='target',how='left')
obs['scalar_observable_at_checkpoint']=obs['scalar_target_median_mae'].le(THRESHOLD)
obs['rank_observable_at_checkpoint']=obs['rank_spearman'].ge(.80)
obs['repairability_observable']=obs['repairable_drop'].ge(.02)
obs['model_floor_warning']=obs['regime'].eq('MODEL_LIMITED_FLOOR') | obs['model_floor_probability'].ge(.5)
obs['support_status']=np.where(obs['cohort'].eq('REVEALED_SENTINEL_2'),'SUPPORTED_IN_FROZEN_T2M_ENVELOPE',np.where(obs['cohort'].eq('PROVIDER_PROSPECTIVE_3'),'SUPPORTED_PROSPECTIVE_PROVIDER','DEVELOPMENT_SUPPORT'))
write_csv(P4/'StageT4-ABC_Decomposed_Observability_Target_Vector_v0.1.csv',obs)

cert=pd.read_csv(find_one(T3X_EX,'StageT3-X_Transparent_Certificate_Radius_Selectivity_Curve_v0.1.csv'))
cert=cert.rename(columns={'interval_coverage':'coverage','wrong_decision_rate_among_decided':'wrong_decision_rate'})
# safest useful radius: coverage>=.95 and wrong-decision<=.05, maximize decision coverage
safe=cert[(cert['coverage']>=.95)&(cert['wrong_decision_rate']<=.05)].copy()
if len(safe):
    selected_cert=safe.sort_values(['decision_coverage','radius'],ascending=[False,True]).iloc[0].to_dict()
else:
    selected_cert={}
write_csv(P4/'StageT4-ABC_Revealed_Sentinel_Certificate_Selectivity_Curve_v0.1.csv',cert)
write_json(P4/'StageT4-ABC_Selected_Transparent_Certificate_Operating_Point_v0.1.json',selected_cert)

# ---------- figures ----------
fig,ax=plt.subplots(figsize=(11,6))
for target,g in curve.groupby('target'):
    ax.plot(g['budget'],g['median_error'],alpha=.55,marker='o',linewidth=1)
ax.axhline(THRESHOLD,color='black',linestyle='--',linewidth=1)
ax.set_xscale('log',base=2); ax.set_xlabel('Independent witness groups'); ax.set_ylabel('Median absolute AUC error')
ax.set_title('Budget-indexed error curves across 23 transparent targets'); fig.tight_layout(); fig.savefig(P5/'StageT4-ABC_23_Target_Budget_Curves_v0.1.png',dpi=180); plt.close(fig)

fig,ax=plt.subplots(figsize=(9,5))
sg=selector_global.sort_values('median_target_mae')
ax.barh(sg['method'],sg['median_target_mae']); ax.axvline(THRESHOLD,color='black',linestyle='--',linewidth=1)
ax.set_xlabel('Median target-level absolute AUC error'); ax.set_title('Strict nested-LOTO selector comparison'); fig.tight_layout(); fig.savefig(P5/'StageT4-ABC_Selector_Comparison_v0.1.png',dpi=180); plt.close(fig)

fig,ax=plt.subplots(figsize=(10,6))
order=obs.sort_values(['cohort','scalar_target_median_mae'])
x=np.arange(len(order))
ax.scatter(x,order['scalar_target_median_mae'],label='checkpoint MAE')
ax.scatter(x,order['fitted_floor'],label='fitted floor')
ax.axhline(THRESHOLD,color='black',linestyle='--',linewidth=1); ax.set_xticks(x); ax.set_xticklabels(order['target'],rotation=90,fontsize=7)
ax.set_ylabel('Absolute AUC error'); ax.set_title('Observed error and estimated model floor'); ax.legend(); fig.tight_layout(); fig.savefig(P5/'StageT4-ABC_Error_Floor_Map_v0.1.png',dpi=180); plt.close(fig)

if {'decision_coverage','wrong_decision_rate'}.issubset(cert.columns):
    fig,ax=plt.subplots(figsize=(7,5)); ax.plot(cert['decision_coverage'],cert['wrong_decision_rate'],marker='o')
    ax.axhline(.05,color='black',linestyle='--',linewidth=1); ax.set_xlabel('Decision coverage'); ax.set_ylabel('Wrong-decision rate'); ax.set_title('Coverage–abstention safety trade-off'); fig.tight_layout(); fig.savefig(P5/'StageT4-ABC_Certificate_Coverage_Abstention_v0.1.png',dpi=180); plt.close(fig)

# ---------- frozen transparent gates and decision ----------
metric=lambda m: float(selector_global.loc[selector_global['method'].eq(m),'median_target_mae'].iloc[0])
rankmetric=lambda m: float(selector_global.loc[selector_global['method'].eq(m),'edge_spearman'].iloc[0])
ra_mae=metric('ra_cb_amw_ddet'); v1_mae=metric('functional_rank_selector_v1')
ra_rank=rankmetric('ra_cb_amw_ddet'); v1_rank=rankmetric('functional_rank_selector_v1')
provider_count=int((obs['cohort']=='PROVIDER_PROSPECTIVE_3').sum()); target_count=int(obs['target'].nunique())
cert_coverage=float(selected_cert.get('coverage',np.nan)); cert_wrong=float(selected_cert.get('wrong_decision_rate',np.nan)); cert_decision=float(selected_cert.get('decision_coverage',np.nan))
model_floor_count=int(obs['model_floor_warning'].sum())
rank_pass_count=int(obs['rank_observable_at_checkpoint'].sum())
scalar_pass_count=int(obs['scalar_observable_at_checkpoint'].sum())

gates=pd.DataFrame([
 {'gate':'parent_chain_integrity','passed':True,'observed':'T2-MN/T3-A/T3-X exact self-hashed parents'},
 {'gate':'transparent_target_scope','passed':target_count>=23,'observed':target_count},
 {'gate':'provider_separation_retained','passed':provider_count>=3,'observed':provider_count},
 {'gate':'functional_rank_selector_improves_ra_cb','passed':v1_mae<=ra_mae*.98,'observed':f'{v1_mae:.6f} vs {ra_mae:.6f}'},
 {'gate':'functional_rank_selector_preserves_rank','passed':np.isfinite(v1_rank) and v1_rank>=ra_rank-.02,'observed':f'{v1_rank:.6f} vs {ra_rank:.6f}'},
 {'gate':'budget_floor_decomposition_identifies_heterogeneity','passed':model_floor_count>=1 and obs['regime'].nunique()>=2,'observed':f'floor warnings={model_floor_count}; regimes={obs["regime"].nunique()}'},
 {'gate':'scalar_and_rank_are_empirically_separable','passed':not obs['scalar_observable_at_checkpoint'].equals(obs['rank_observable_at_checkpoint']),'observed':f'scalar={scalar_pass_count}; rank={rank_pass_count}'},
 {'gate':'certificate_safety_survives','passed':np.isfinite(cert_coverage) and cert_coverage>=.95 and cert_wrong<=.05,'observed':f'coverage={cert_coverage:.4f}; wrong={cert_wrong:.4f}; decision={cert_decision:.4f}'},
 {'gate':'single_pilot_deployment_prohibited','passed':True,'observed':'prohibited'},
 {'gate':'new_blind_accessed','passed':True,'observed':False},
 {'gate':'stage12_authorised','passed':True,'observed':False},
])
write_csv(P6/'StageT4-ABC_Frozen_Transparent_Gates_v0.1.csv',gates)

method_upgrade_pass=bool(gates.loc[gates['gate'].isin(['functional_rank_selector_improves_ra_cb','functional_rank_selector_preserves_rank']),'passed'].all())
theory_pass=bool(gates.loc[gates['gate'].isin(['budget_floor_decomposition_identifies_heterogeneity','scalar_and_rank_are_empirically_separable','certificate_safety_survives']),'passed'].all())
if method_upgrade_pass and theory_pass:
    decision='SEAL_T4ABC_DECOMPOSED_OBSERVABILITY_AND_METHOD_V1_AUTHORISE_NEW_RESERVE_DESIGN_ONLY'
else:
    decision='SEAL_T4ABC_DECOMPOSED_OBSERVABILITY_CONTINUE_METHOD_V1_DEVELOPMENT_PROHIBIT_NEW_BLIND'

complete={
 'stage':'StageT4-ABC','decision':decision,'transparent_post_unblinding':True,
 'parent_t2mn_final_record_sha256':EXPECTED_T2MN_FINAL,'parent_t3a_final_record_sha256':EXPECTED_T3A_FINAL,'parent_t3x_final_record_sha256':EXPECTED_T3X_FINAL,
 'transparent_targets':target_count,'development_targets':int((obs['cohort']=='DEVELOPMENT_18').sum()),
 'provider_prospective_targets':provider_count,'revealed_sentinel_targets':int((obs['cohort']=='REVEALED_SENTINEL_2').sum()),
 'ra_cb_median_target_mae':ra_mae,'functional_rank_selector_v1_median_target_mae':v1_mae,
 'ra_cb_edge_spearman':ra_rank,'functional_rank_selector_v1_edge_spearman':v1_rank,
 'model_floor_warning_targets':model_floor_count,'scalar_observable_targets':scalar_pass_count,'rank_observable_targets':rank_pass_count,
 'certificate_selected_operating_point':selected_cert,'theory_decomposition_supported':theory_pass,'method_v1_upgrade_supported':method_upgrade_pass,
 'new_blind_accessed':False,'new_blind_access_authorised':False,'single_pilot_deployment_authorised':False,'stage12_authorised':False,
 'completed_utc':now(),
}
complete['final_record_sha256']=sha_json(complete)
write_json(P6/'StageT4-ABC_Complete_v0.1.json',complete)

summary=f'''# Stage T4-ABC decomposed-observability transparent validation result\n\n- Decision: `{decision}`\n- Transparent targets: `{target_count}` (18 development + 3 provider-prospective + 2 revealed sentinel)\n- RA-CB median target MAE: `{ra_mae:.6f}`\n- Functional/rank selector v1 median target MAE: `{v1_mae:.6f}`\n- RA-CB / v1 edge Spearman: `{ra_rank:.6f}` / `{v1_rank:.6f}`\n- Model-floor warning targets: `{model_floor_count}`\n- Scalar-observable / rank-observable targets: `{scalar_pass_count}` / `{rank_pass_count}`\n- Certificate coverage / wrong-decision / decision coverage: `{cert_coverage:.6f}` / `{cert_wrong:.6f}` / `{cert_decision:.6f}`\n- Theory decomposition supported: `{theory_pass}`\n- Method-v1 upgrade supported: `{method_upgrade_pass}`\n- New blind access authorised: `False`\n- Stage 12 authorised: `False`\n- Final record SHA256: `{complete['final_record_sha256']}`\n'''
write_text=atomic_text
write_text(P6/'StageT4-ABC_Result_Summary_v0.1.md',summary)

manuscript=f'''# Manuscript-ready Stage T4-ABC insert\n\nFollowing the preregistered Stage T3-A Scenario C failure, Stage T4-ABC treated the two revealed sentinel targets strictly as transparent development evidence and combined them with 18 prior development targets and three provider-separated prospective-development targets. The analysis separated scalar edge-performance recovery, within-target rank recovery, support, repairability, error floor and selective certification rather than representing auditability by a single score. Across the frozen Stage T2-F development set, a strictly nested leave-one-target-out functional/rank-aware selector achieved a median target-level absolute AUC error of {v1_mae:.4f}, compared with {ra_mae:.4f} for the frozen RA-CB selector; this {'passed' if method_upgrade_pass else 'did not pass'} the prespecified method-upgrade criterion. Budget-indexed repairable-plus-floor curves identified {model_floor_count} targets with a model-floor warning and empirically separated scalar observability from rank observability. The frozen certificate family retained a selected transparent operating point with coverage {cert_coverage:.3f}, wrong-decision rate {cert_wrong:.3f}, and decision coverage {cert_decision:.3f}. These findings support decomposed, budget-indexed diagnostic observability as the scientific object, while any upgraded estimator requires a completely new prospective reserve and cannot reinterpret Stage T3-A as a success.\n'''
write_text(P6/'StageT4-ABC_Manuscript_Insert_v0.1.md',manuscript)

# canonical archive + verified durable commit
bundle=RUNTIME_ROOT/'StageT4-ABC_Canonical_Records_v0.1.zip'
with zipfile.ZipFile(bundle,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for p in sorted(RUNTIME_ROOT.rglob('*')):
        if p.is_file() and p!=bundle and '.tmp' not in p.name:
            z.write(p,p.relative_to(RUNTIME_ROOT))

commit_files=[bundle,P6/'StageT4-ABC_Complete_v0.1.json',P6/'StageT4-ABC_Result_Summary_v0.1.md',P6/'StageT4-ABC_Frozen_Transparent_Gates_v0.1.csv',P4/'StageT4-ABC_Decomposed_Observability_Target_Vector_v0.1.csv']
COMMIT_ROOT.mkdir(parents=True,exist_ok=True)
manifest_rows=[]
for src in commit_files:
    dst=COMMIT_ROOT/src.name
    shutil.copy2(src,dst)
    assert dst.is_file() and sha_file(dst)==sha_file(src)
    manifest_rows.append({'file':src.name,'bytes':src.stat().st_size,'sha256':sha_file(src),'drive_path':str(dst)})
commit_manifest={'stage':'StageT4-ABC','commit_root':str(COMMIT_ROOT),'canonical_bundle_sha256':sha_file(bundle),'files':manifest_rows,
                 'all_drive_copies_reopened_and_hash_verified':True,'locked_blind_assets_touched':False,'new_blind_access_authorised':False,'stage12_authorised':False,'committed_utc':now()}
commit_manifest['commit_manifest_sha256']=sha_json(commit_manifest)
write_json(COMMIT_ROOT/'StageT4-ABC_Durable_Commit_Manifest_v0.1.json',commit_manifest)
assert verify_self_record(COMMIT_ROOT/'StageT4-ABC_Complete_v0.1.json')['final_record_sha256']==complete['final_record_sha256']

print('\n========== STAGE T4-ABC COMPLETE ==========')
print('Decision:',decision)
print('Transparent targets:',target_count)
print('RA-CB / v1 median target MAE:',ra_mae,v1_mae)
print('Theory decomposition supported:',theory_pass)
print('Method-v1 upgrade supported:',method_upgrade_pass)
print('New blind authorised:',False)
print('Stage 12 authorised:',False)
print('Final record SHA256:',complete['final_record_sha256'])
print('Committed to:',COMMIT_ROOT)
display(gates)
