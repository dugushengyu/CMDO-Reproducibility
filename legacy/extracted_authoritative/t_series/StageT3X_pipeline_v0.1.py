# Stage T3-X transparent Stage T3-A failure autopsy and decomposed observability diagnosis
import os, sys, io, json, math, time, hashlib, zipfile, shutil, re, unicodedata, warnings, itertools
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.io import loadmat
from scipy.stats import spearmanr, kendalltau
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import PolynomialFeatures, SplineTransformer, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier

warnings.filterwarnings('ignore')
try:
    from IPython.display import display
except Exception:
    display = print

try:
    from google.colab import drive
    drive.mount('/content/drive')
    IN_COLAB = True
except Exception:
    IN_COLAB = False

SEED = 20260723
np.random.seed(SEED)
EXPECTED_BUNDLE_SHA = '8f1a4165136afc09d92ea9c2a1e4d8dee275dd3e7d732d426b664f97ae59ff00'
EXPECTED_FINAL_SHA = '9c6cd7929437a262d7d8b0c7c9e17193d1f30a1be47915fa3ae60fd15b518bc9'
EXPECTED_SCENARIO = 'SCENARIO_C_PERFORMANCE_PRIMARY_FAILURE'
EXPECTED_DECISION = 'SEAL_T3A_SCENARIO_C_PERFORMANCE_PRIMARY_FAILURE_PROHIBIT_CONFIRMATORY_UPGRADE'
PRIMARY_BUDGET = 32
BUDGETS = [8, 16, 32, 64, 128]
THRESHOLD = 0.04
N_REPS = 100

DEFAULT_ROOT = Path('/content/drive/MyDrive/Cross-Modal_Diagnostic_Observability') if IN_COLAB else Path.cwd()
PROJECT_ROOT = Path(os.environ.get('CMDO_PROJECT_ROOT', str(DEFAULT_ROOT)))
CODE_ROOT = PROJECT_ROOT / '05_Code' / 'Cross_Modal'
THEORY_ROOT = PROJECT_ROOT / '03_Theory' / 'Directed_Diagnostic_Observability_Decomposition_v1.2'
STUDY_ROOT = PROJECT_ROOT / '04_Study_Design' / 'StageT3-X_Transparent_Blind_Failure_Autopsy_v0.1'
ACQ_ROOT = PROJECT_ROOT / '00_Data_Acquisition' / 'Cross_Modal_Locked_Blind_Sentinel_v0.1'
COMMIT_ROOT = PROJECT_ROOT / '06_Data_Records' / 'Cross_Modal' / 'StageT3-X_Transparent_Blind_Failure_Autopsy_And_Observability_Decomposition_v0.1'
RUNTIME_ROOT = Path('/content/cmdo_runtime/StageT3-X') if IN_COLAB else Path('/tmp/cmdo_runtime/StageT3-X')
PARENT_ROOT = RUNTIME_ROOT / 'parent_t3a'
RAW_ROOT = RUNTIME_ROOT / 'raw'
RESULT_ROOT = RUNTIME_ROOT / 'records'
for p in [CODE_ROOT, THEORY_ROOT, STUDY_ROOT, COMMIT_ROOT]:
    p.mkdir(parents=True, exist_ok=True)
if RUNTIME_ROOT.exists():
    shutil.rmtree(RUNTIME_ROOT)
for p in [PARENT_ROOT, RAW_ROOT, RESULT_ROOT]:
    p.mkdir(parents=True, exist_ok=True)

P0 = RESULT_ROOT / '00_Integrity_And_Outcome_Reconstruction'
P1 = RESULT_ROOT / '01_Frozen_Output_Reproduction_And_Selector_Autopsy'
P2 = RESULT_ROOT / '02_Rank_Compression_And_Consensus_Trap'
P3 = RESULT_ROOT / '03_Transparent_Posterior_And_Functional_Grid'
P4 = RESULT_ROOT / '04_Budget_Sensitivity_And_Error_Floor'
P5 = RESULT_ROOT / '05_Certificate_Selectivity_And_Safety'
P6 = RESULT_ROOT / '06_Mechanism_Adjudication_And_Upgrade_Decision'
for p in [P0,P1,P2,P3,P4,P5,P6]: p.mkdir(parents=True, exist_ok=True)

def now(): return datetime.now(timezone.utc).isoformat()
def sha_bytes(data): return hashlib.sha256(data).hexdigest()
def sha_file(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()
def sha_json(obj): return sha_bytes(json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())
def write_json(path,obj):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); os.replace(tmp,path)
def write_csv(path,df):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp'); df.fillna('').to_csv(tmp,index=False,lineterminator='\n',float_format='%.12g'); os.replace(tmp,path)
def write_text(path,text):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(text,encoding='utf-8'); os.replace(tmp,path)
def normalise_column(v): return re.sub(r'[^a-z0-9]+','_',str(v).strip().lower()).strip('_')
def normalise_text(v):
    v=unicodedata.normalize('NFKD',str(v)); v=''.join(c for c in v if not unicodedata.combining(c)); v=v.lower().replace('đ','d'); v=re.sub(r'[^a-z0-9]+',' ',v); return re.sub(r'\s+',' ',v).strip()
def verify_self_record(path,field,expected=None):
    rec=json.loads(Path(path).read_text(encoding='utf-8-sig')); claim=rec[field]; core=dict(rec); core.pop(field); assert sha_json(core)==claim
    if expected: assert claim==expected
    return rec

def find_exact_file(name, expected_sha=None):
    candidates=list(PROJECT_ROOT.rglob(name))
    if expected_sha:
        candidates=[p for p in candidates if p.is_file() and sha_file(p)==expected_sha]
    assert candidates, f'Missing exact file: {name}'
    return sorted(candidates,key=lambda p:(len(p.parts),str(p)))[0]

# Embedded companion documents make the notebook independent of upload ordering.
EMBEDDED_THEORY = '# Directed Diagnostic Evidence Transport: Decomposed Observability and the Consensus Trap\n\n**Version:** 1.2 working theory  \n**Status:** post–Stage T3-A transparent theory revision candidate  \n**Parent locked-blind record:** `9c6cd7929437a262d7d8b0c7c9e17193d1f30a1be47915fa3ae60fd15b518bc9`\n\n## 1. Motivation\n\nStage T3-A showed that low target-level median performance error, correct interval coverage, correct selective decisions, correct edge ordering, and correct evidence-demand ordering are not equivalent properties. A diagnostic target may therefore be partially observable in one functional and unobservable in another.\n\n## 2. Decomposed observability\n\nFor a directed source axis `s` evaluated on target `t`, define separate observability questions:\n\n1. **Posterior observability:** can sparse target evidence recover the outcome posterior relevant to the audit?\n2. **Marginal edge-performance observability:** can the scalar performance of `s -> t` be estimated?\n3. **Rank observability:** can the ordering of multiple source axes on the same target be recovered?\n4. **Decision-certifiable observability:** can retain, exclude, or abstain decisions be made with controlled error?\n5. **Evidence-demand observability:** can the target evidence needed to reach an audit error tolerance be forecast?\n6. **Repairability observability:** can additional evidence be distinguished from a frozen-model error floor?\n\nNo implication between adjacent layers is assumed without an explicit proposition or empirical test.\n\n## 3. Consensus trap\n\nA low disagreement among audit estimators has two possible meanings:\n\n- estimators are jointly close to truth;\n- estimators share a structural bias and are jointly wrong.\n\nThe second state is the **consensus trap**. It makes method disagreement an incomplete proxy for evidence demand and motivates diagnostics that compare model classes, functionals, local rank structure, and support rather than only resampling variants of one posterior family.\n\n## 4. Shared-posterior rank compression\n\nA shared estimated posterior may give acceptable average scalar error while compressing edge-specific differences. This can preserve broad calibration yet invert source-axis ranking. Rank observability therefore requires a dedicated functional diagnostic and cannot be inferred from posterior Brier risk alone.\n\n## 5. Error-demand decomposition\n\nOperational evidence demand is decomposed conceptually into:\n\n- sampling uncertainty;\n- calibration demand;\n- rank-recovery demand;\n- model-class misspecification or frozen representation floor.\n\nIncreasing target labels can reduce the first three terms. It need not remove the final term. A plateau above the tolerance threshold is evidence for model-family limitation rather than an instruction to extrapolate indefinitely to a larger label budget.\n\n## 6. Safety claim\n\nPoint-prediction failure does not imply certification failure. A conservative interval and abstention rule may retain coverage and zero wrong decisions while sacrificing decision coverage. Safety must therefore be evaluated by coverage, selective error, and abstention rate, not only point MAE.\n\n## 7. Required empirical adjudication\n\nThe Stage T3-X autopsy must distinguish among:\n\n- selector failure;\n- shared-posterior model-class failure;\n- AUC-functional or rank-objective misalignment;\n- insufficient budget;\n- frozen representation/axis limitation;\n- consensus-trap behaviour.\n\nStage T3-A is fully revealed and may be used only for transparent diagnosis and method development. Any upgraded method requires a completely new prospective reserve.\n'
EMBEDDED_PREREG = '# Stage T3-X transparent blind-failure autopsy and observability-decomposition preregistration v1.0\n\n**Frozen:** 23 July 2026  \n**Parent Stage T3-A final record:** `9c6cd7929437a262d7d8b0c7c9e17193d1f30a1be47915fa3ae60fd15b518bc9`  \n**Parent canonical bundle SHA-256:** `8f1a4165136afc09d92ea9c2a1e4d8dee275dd3e7d732d426b664f97ae59ff00`  \n**Status:** transparent post-unblinding diagnosis; not confirmatory; no Stage 3 or Stage 12 authority\n\n## 1. Purpose\n\nDetermine whether the Stage T3-A failure is primarily attributable to the frozen selector, shared-posterior model class, AUC-functional/rank misalignment, insufficient target evidence, a frozen-model error floor, or a consensus trap. The analysis is explicitly transparent and cannot rehabilitate Stage T3-A as a blind success.\n\n## 2. Immutable inputs\n\nThe exact Stage T3-A canonical bundle is the primary immutable input. Official Derm7pt metadata and exact OASBUD v1 outcomes are re-read only to reconstruct group labels for transparent alternative-model experiments. The frozen target roster, source logits, source axes, witness manifests and true edge AUCs may not be changed.\n\n## 3. Frozen-output autopsy\n\nThe notebook will reproduce Stage T3-A metrics, quantify target/edge method dominance, selector regret, oracle-candidate ceilings, rank compression, pairwise inversions, disagreement–error association, evidence-curve slope/floor structure, and the fixed-certificate coverage/abstention trade-off.\n\n## 4. Transparent alternative-model grid\n\nUsing the exact active D-optimal witness manifests, the notebook will compare:\n\n- shared linear logistic posterior;\n- shared quadratic logistic posterior;\n- shared spline logistic posterior;\n- shared histogram-gradient-boosted posterior;\n- edge-specific univariate linear posterior;\n- edge-specific univariate spline posterior;\n- existing active-direct, AMW-U, AMW-CB2, AMW-DDET and RA-CB outputs.\n\nWitness predictions are cross-fitted. Budget 32 is the primary autopsy budget. The best shared and edge-specific alternatives are then inspected at budgets 16, 64 and 128 to distinguish model-class limitation from evidence limitation. Full-label cross-fitted ceilings are diagnostic only.\n\n## 5. Mechanism adjudication\n\nA mechanism is supported only by predefined comparisons:\n\n- **selector-dominated:** frozen-candidate oracle materially improves RA-CB and meets the rank target;\n- **shared-posterior misspecification:** a flexible shared posterior improves target median MAE by at least 20% and improves edge rank;\n- **functional/rank misalignment:** an edge-specific method outperforms the best shared method and restores rank;\n- **budget limitation:** a method fails at 32 but reaches the frozen performance criteria at 64 or 128;\n- **model floor:** late-budget improvement is below 0.01 while error remains above 0.04;\n- **consensus trap:** estimator disagreement has weak association with error and low-disagreement/high-error cases occur;\n- **certificate survival:** frozen coverage is at least 0.85 and wrong decided-edge rate is at most 0.05.\n\n## 6. Upgrade decision\n\nThe final decision is one of:\n\n1. `AUTHORISE_DECOMPOSED_OBSERVABILITY_THEORY_AND_V1_METHOD_DEVELOPMENT`;\n2. `AUTHORISE_DECOMPOSED_OBSERVABILITY_THEORY_ONLY`;\n3. `AUTHORISE_TARGETED_V1_METHOD_DEVELOPMENT_ONLY`;\n4. `STOP_ESCALATION_RETAIN_T3A_BOUNDARY_REPORT`.\n\nNo decision authorises reinterpretation of T3-A, access to another blind reserve, adaptive acquisition, single-pilot deployment, or Stage 12.\n\n## 7. Reporting\n\nAll results, including failed alternative models, skipped manifests, outcome reconstruction audits and sensitivity analyses, are retained. Target is the primary exchange unit. Replicates and edges are not treated as independent targets for confirmatory claims.\n'
EMBEDDED_METHOD = '# Stage T3-X failure autopsy and transparent model-comparison method v0.1\n\n## Inputs and chronology\n\nThe analysis begins only after verifying the exact Stage T3-A canonical ZIP and its internal self-hashed completion record. Stage T3-A remains a failed locked-blind experiment. T3-X is transparent diagnosis.\n\n## Data reconstruction\n\nFrozen group source logits and witness manifests are read from the canonical bundle. Derm7pt endpoint labels are reconstructed from the authenticated official `meta.csv`; OASBUD lesion labels are reconstructed from Zenodo record 545928 v1. Reconstructed group IDs must exactly cover the frozen analyzable roster.\n\n## Model comparison\n\nAll alternative models use the same frozen witness group IDs. Cross-fitting replaces in-witness posterior predictions to reduce optimistic functional estimation. Shared models estimate one posterior from all source logits; edge-specific models estimate one posterior per source score. The AUC functional remains the soft weighted Mann–Whitney statistic.\n\n## Autopsy outputs\n\nThe pipeline produces selector-regret, rank-compression, consensus-trap, budget-sensitivity, error-floor, certificate-selectivity and mechanism-adjudication tables, together with a compact canonical record archive and deterministic final record.\n\n## Storage\n\nOfficial OASBUD raw data are downloaded to transient runtime storage and deleted after the verified commit. The existing authenticated Derm7pt archive remains in its governed acquisition inbox. Only compact results are committed to Drive.\n'
EMBEDDED_README = '# Cross-Modal notebook index v2.4\n\n## Active transparent autopsy\n\n`CrossModal_StageT3-X_Transparent_Blind_Failure_Autopsy_And_Observability_Decomposition_v0.1_SELF_CONTAINED.ipynb`\n\nThis notebook does not rerun or rescue the Stage T3-A blind test. It treats Stage T3-A as revealed development evidence, verifies the exact canonical record, reconstructs official target labels, performs frozen-output failure decomposition, compares transparent shared and edge-specific posterior families on the exact witness manifests, diagnoses selector/model/functional/budget/consensus mechanisms, and writes a verified compact Drive record.\n\nUse a clean CPU runtime and `Runtime -> Run all`. No additional manual download is required while the authenticated Derm7pt `release_v0.zip` remains in its existing governed inbox.\n'
COMPANIONS = [
    (THEORY_ROOT/'Directed_Diagnostic_Evidence_Transport_Decomposed_Observability_And_Consensus_Trap_Theory_v1.2.md', EMBEDDED_THEORY, '1d0057c310cd632fd87b538246b7512f57a018cdb933e48489ab4b4d35f4cb8e'),
    (STUDY_ROOT/'StageT3-X_Transparent_Blind_Failure_Autopsy_And_Observability_Decomposition_Preregistration_v1.0.md', EMBEDDED_PREREG, 'b79d3857d4409004f31ac63d0f9c4bb961026e1edb0726bcc01038d8aab937db'),
    (STUDY_ROOT/'StageT3-X_Failure_Autopsy_And_Transparent_Model_Comparison_Method_v0.1.md', EMBEDDED_METHOD, '80af9ce3d272538f372681d36ae8bdaf976a7d9b16738cfd1cb045bf59336c50'),
    (CODE_ROOT/'README_Cross_Modal_Notebook_Index_v2.4.md', EMBEDDED_README, 'fa2638435098e80badc3592d285dbc2cdd862b8d43c477b5c964e9545d6f8ef4'),
]
for path,text,expected in COMPANIONS:
    if path.exists():
        assert sha_file(path)==expected, f'Companion differs: {path}'
    else:
        write_text(path,text); assert sha_file(path)==expected

bundle_path=find_exact_file('StageT3-A_Canonical_Records_v0.1.zip',EXPECTED_BUNDLE_SHA)
assert sha_file(bundle_path)==EXPECTED_BUNDLE_SHA
with zipfile.ZipFile(bundle_path) as z:
    z.extractall(PARENT_ROOT)
complete_path=PARENT_ROOT/'07_Scenario_Classification_And_Results'/'StageT3-A_Complete_v0.1.json'
parent_complete=verify_self_record(complete_path,'final_record_sha256',EXPECTED_FINAL_SHA)
assert parent_complete['scenario']==EXPECTED_SCENARIO
assert parent_complete['decision']==EXPECTED_DECISION
assert parent_complete['integrity_pass'] is True
assert parent_complete['t3b_execution_authorised'] is False

integrity_record={
    'stage':'StageT3-X','purpose':'transparent_failure_autopsy_and_observability_decomposition',
    'parent_bundle_path':str(bundle_path),'parent_bundle_sha256':EXPECTED_BUNDLE_SHA,
    'parent_final_record_sha256':EXPECTED_FINAL_SHA,'parent_scenario':EXPECTED_SCENARIO,
    'parent_integrity_pass':True,'confirmatory_claim':False,'blind_status':'FULLY_REVEALED_DEVELOPMENT_EVIDENCE',
    'stage3_execution_authorised':False,'stage12_authorised':False,'started_utc':now()
}
integrity_record['integrity_record_sha256']=sha_json(integrity_record)
write_json(P0/'StageT3-X_Parent_Integrity_Record_v0.1.json',integrity_record)
print('Stage T3-X parent integrity:',integrity_record['integrity_record_sha256'])

# Outcome reconstruction from official sources, now transparently permitted after Stage T3-A unblinding.
import requests

def md5_file(path):
    h=hashlib.md5()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()

def safe_extract_zip(source,dest):
    dest=Path(dest); dest.mkdir(parents=True,exist_ok=True); base=dest.resolve()
    with zipfile.ZipFile(source) as z:
        for m in z.infolist():
            target=(dest/m.filename).resolve(); assert target==base or str(target).startswith(str(base)+os.sep)
        z.extractall(dest)

def find_table_column(frame,exact=(),contains=()):
    mapping={normalise_column(c):c for c in frame.columns}
    for c in exact:
        if normalise_column(c) in mapping: return mapping[normalise_column(c)]
    for c in frame.columns:
        n=normalise_column(c)
        if any(t in n for t in contains): return c
    return None

def derm_endpoint_label(v):
    t=normalise_text(v)
    if 'melanoma' in t or t in {'mel','mm'}: return 1
    if 'nevus' in t or 'naevus' in t or t in {'nv','nev'}: return 0
    return None

def reconstruct_derm_labels():
    expected='89a4749e7e43d1c2e73876aaeb867af5b2624e929ee3d1ae7202268588566b54'
    candidates=[p for p in (ACQ_ROOT/'DERM7PT_2019'/'00_Raw_Inbox').rglob('*') if p.is_file() and p.stat().st_size>1024]
    archives=[p for p in candidates if p.suffix.lower()=='.zip' and sha_file(p)==expected]
    assert archives, 'Exact authenticated Derm7pt release_v0.zip not found'
    archive=archives[0]; extract=RAW_ROOT/'DERM7PT_2019'; safe_extract_zip(archive,extract)
    metas=list(extract.rglob('meta.csv')); assert metas
    meta=next((p for p in metas if 'meta' in [x.lower() for x in p.parts]),metas[0])
    assert sha_file(meta)=='471199fb86bcc97cd1521bcc4255bb3f9c563e2ed0ad3ff836392d81a3ed9d3b'
    df=pd.read_csv(meta)
    case_col=find_table_column(df,['case_num','case_id','case','lesion_id','id'],('case','lesion'))
    diag_col=find_table_column(df,['diagnosis','diag','label'],('diagnos','diag'))
    assert case_col and diag_col
    rows=[]
    for _,r in df.iterrows():
        y=derm_endpoint_label(r[diag_col])
        if y is None: continue
        case=str(r[case_col]).strip()
        if not case or case.lower() in {'nan','none'}: continue
        rows.append({'target':'DERM7PT_2019','group_id':f'DERM7PT_2019::CASE::{case}','label':int(y)})
    out=pd.DataFrame(rows).drop_duplicates(['target','group_id'])
    return out, {'target':'DERM7PT_2019','official_archive_sha256':sha_file(archive),'metadata_sha256':sha_file(meta),'reconstructed_groups':out.group_id.nunique()}

def scalar_value(value):
    a=np.asarray(value)
    if a.size==0:return ''
    if a.size==1:
        v=a.reshape(-1)[0]
        if isinstance(v,bytes): return v.decode('utf-8',errors='replace')
        return v.item() if hasattr(v,'item') else v
    return value

def matlab_field(record,candidates):
    fields=getattr(record,'_fieldnames',None)
    if fields is None and isinstance(record,dict): fields=list(record)
    if not fields:return None
    mapping={normalise_column(f):f for f in fields}
    for c in candidates:
        k=normalise_column(c)
        if k in mapping:
            f=mapping[k]; return record[f] if isinstance(record,dict) else getattr(record,f)
    return None

def walk_mat_records(value,depth=0):
    if depth>8:return
    fields=getattr(value,'_fieldnames',None)
    if fields:
        n={normalise_column(f) for f in fields}
        if any(f in n for f in {'rf1','rf_1'}) and any(f in n for f in {'rf2','rf_2'}) and any(f in n for f in {'class','label','diagnosis'}):
            yield value; return
        for f in fields: yield from walk_mat_records(getattr(value,f),depth+1)
        return
    if isinstance(value,dict):
        n={normalise_column(f) for f in value}
        if any(f in n for f in {'rf1','rf_1'}) and any(f in n for f in {'rf2','rf_2'}) and any(f in n for f in {'class','label','diagnosis'}):
            yield value; return
        for child in value.values(): yield from walk_mat_records(child,depth+1)
        return
    if isinstance(value,np.ndarray) and value.dtype==object:
        for child in value.reshape(-1): yield from walk_mat_records(child,depth+1)

def map_binary_class(v):
    v=scalar_value(v)
    if isinstance(v,(int,float,np.integer,np.floating)) and np.isfinite(v):
        i=int(round(float(v)))
        if i in {0,1}:return i
    t=normalise_text(v)
    if t in {'1','m','malignant','malign'} or 'malignant' in t:return 1
    if t in {'0','b','benign'} or 'benign' in t:return 0
    raise ValueError(v)

def download_oasbud():
    dest=RAW_ROOT/'OASBUD.mat'; urls=[
        'https://zenodo.org/records/545928/files/OASBUD.mat?download=1',
        'https://zenodo.org/api/records/545928/files/OASBUD.mat/content',
        'https://zenodo.org/record/545928/files/OASBUD.mat?download=1']
    errors=[]
    for url in urls:
        try:
            with requests.get(url,stream=True,timeout=(30,300),allow_redirects=True,headers={'User-Agent':'CMDO-StageT3-X/1.0'}) as r:
                r.raise_for_status(); tmp=dest.with_suffix('.part')
                with tmp.open('wb') as f:
                    for chunk in r.iter_content(1024*1024):
                        if chunk:f.write(chunk)
                assert tmp.stat().st_size>250_000_000
                os.replace(tmp,dest)
            if md5_file(dest)!='e2b770a6ee2f06ebe480ed0962252100': raise RuntimeError('MD5 mismatch')
            if sha_file(dest)!='698eadeabe451d8af3b6c8e205d2a8cbc590ab1275d188614916bceb501bcd48': raise RuntimeError('SHA mismatch')
            return dest,url
        except Exception as e:
            errors.append(f'{url}: {type(e).__name__}: {e}')
            if dest.exists():dest.unlink()
            p=dest.with_suffix('.part')
            if p.exists():p.unlink()
    raise RuntimeError('OASBUD download failed: '+' || '.join(errors))

def reconstruct_oasbud_labels():
    mat,url=download_oasbud(); loaded=loadmat(mat,squeeze_me=True,struct_as_record=False)
    records=[]
    for k,v in loaded.items():
        if not str(k).startswith('__'):records.extend(list(walk_mat_records(v)))
    uniq=[]; seen=set()
    for r in records:
        if id(r) not in seen: seen.add(id(r)); uniq.append(r)
    rows=[]
    for pos,r in enumerate(uniq):
        ident=matlab_field(r,['id','patient_id','lesion_id','case_id']); ident=str(scalar_value(ident)).strip() or f'record_{pos:04d}'
        y=map_binary_class(matlab_field(r,['class','label','diagnosis']))
        rows.append({'target':'OASBUD_2017','group_id':f'OASBUD_2017::LESION::{ident}','label':int(y)})
    out=pd.DataFrame(rows).drop_duplicates(['target','group_id'])
    return out, {'target':'OASBUD_2017','official_url':url,'official_mat_sha256':sha_file(mat),'reconstructed_groups':out.group_id.nunique(),'mat_records':len(uniq)}

derm_labels,derm_audit=reconstruct_derm_labels()
oas_labels,oas_audit=reconstruct_oasbud_labels()
labels=pd.concat([derm_labels,oas_labels],ignore_index=True)
write_json(P0/'StageT3-X_Official_Outcome_Reconstruction_Audit_v0.1.json',[derm_audit,oas_audit])

# Frozen parent tables.
def parent_csv(rel): return pd.read_csv(PARENT_ROOT/rel)
roster=parent_csv('02_Grouping_Dedup_And_Frozen_Roster/StageT3-A_Frozen_Outcome_Free_Roster_v0.1.csv')
group_logits=parent_csv('03_Frozen_Embeddings_Source_Scores_And_Witness_Manifests/StageT3-A_Frozen_Group_Source_Logits_v0.1.csv')
manifests=parent_csv('03_Frozen_Embeddings_Source_Scores_And_Witness_Manifests/StageT3-A_All_Precommitted_Witness_Manifests_v0.1.csv')
primary_all=parent_csv('07_Scenario_Classification_And_Results/StageT3-A_Budget32_All_Methods_With_Truth_v0.1.csv')
edge_summary_parent=parent_csv('07_Scenario_Classification_And_Results/StageT3-A_Edge_Level_Primary_Summary_v0.1.csv')
diagnostics=parent_csv('05_Budget32_Primary_Prediction_Seal/StageT3-A_Budget32_RA_CB_Diagnostics_v0.1.csv')
edge_truth=parent_csv('06_Remaining_Waves_And_Final_Outcome_Unseal/StageT3-A_Final_Blind_Edge_Truth_v0.1.csv')
evidence_eval_parent=parent_csv('07_Scenario_Classification_And_Results/StageT3-A_Prospective_Evidence_Forecast_Evaluation_v0.1.csv')
evidence_curves_parent=parent_csv('07_Scenario_Classification_And_Results/StageT3-A_Isotonic_Evidence_Curves_v0.1.csv')
cert_parent=parent_csv('07_Scenario_Classification_And_Results/StageT3-A_RA_CB_Certificate_Evaluation_v0.1.csv')

frozen_groups=set(group_logits.group_id.astype(str))
matched=labels[labels.group_id.astype(str).isin(frozen_groups)].copy()
coverage=(matched.groupby('target').group_id.nunique()/group_logits.groupby('target').group_id.nunique()).rename('coverage').reset_index()
assert set(coverage.target)=={'DERM7PT_2019','OASBUD_2017'} and np.allclose(coverage.coverage,1.0)
write_csv(P0/'StageT3-X_Outcome_Group_Coverage_v0.1.csv',coverage)
label_summary=matched.groupby(['target','label'],as_index=False).agg(groups=('group_id','nunique'))
label_hash=sha_json(matched.sort_values(['target','group_id'])[['target','group_id','label']].to_dict(orient='records'))
write_csv(P0/'StageT3-X_Transparent_Outcome_Class_Summary_v0.1.csv',label_summary)
write_json(P0/'StageT3-X_Transparent_Outcome_Label_Hash_v0.1.json',{'label_rows':len(matched),'label_table_sha256':label_hash,'full_label_table_persisted':False})
print('Official outcome reconstruction coverage:'); display(coverage)

# 1. Exact Stage T3-A reproduction and frozen-output autopsy.
def rank_metrics(frame):
    frame=frame.dropna(subset=['estimate_auc','true_auc']).copy()
    if len(frame)<2:return {'edge_count':len(frame),'spearman':np.nan,'kendall':np.nan,'inversions':np.nan,'true_range':np.nan,'predicted_range':np.nan,'range_ratio':np.nan,'slope':np.nan}
    true=frame.true_auc.to_numpy(float); pred=frame.estimate_auc.to_numpy(float)
    inv=0; comparable=0
    for i,j in itertools.combinations(range(len(frame)),2):
        dt=true[i]-true[j]; dp=pred[i]-pred[j]
        if abs(dt)<1e-12:continue
        comparable+=1
        if dp*dt<0:inv+=1
    true_range=float(np.ptp(true)); pred_range=float(np.ptp(pred))
    slope=float(np.polyfit(true,pred,1)[0]) if np.std(true)>0 else np.nan
    return {'edge_count':len(frame),'spearman':float(spearmanr(pred,true).statistic),'kendall':float(kendalltau(pred,true).statistic),'inversions':inv,'comparable_pairs':comparable,'true_range':true_range,'predicted_range':pred_range,'range_ratio':pred_range/true_range if true_range>0 else np.nan,'slope':slope}

target_method=(primary_all.groupby(['method','target','modality'],as_index=False).agg(target_median_absolute_error=('absolute_error','median'),target_mean_absolute_error=('absolute_error','mean'),usable_rows=('absolute_error','size')))
write_csv(P1/'StageT3-X_Frozen_Target_Method_Performance_v0.1.csv',target_method)

edge_medians=(primary_all.groupby(['method','target','provider','modality','source','edge_id'],as_index=False).agg(estimate_auc=('estimate_auc','median'),true_auc=('true_auc','first'),absolute_error=('absolute_error','median'),usable_replicates=('replicate','nunique')))
rank_rows=[]
for (method,target),frame in edge_medians.groupby(['method','target']):
    rank_rows.append({'method':method,'target':target,'modality':frame.modality.iloc[0],**rank_metrics(frame)})
rank_table=pd.DataFrame(rank_rows)
write_csv(P1/'StageT3-X_Frozen_Method_Rank_And_Compression_Autopsy_v0.1.csv',rank_table)

wide=target_method.pivot(index='target',columns='method',values='target_median_absolute_error')
reproduced={
    'ra_cb_target_median_mae':float(wide['ra_cb_amw_ddet'].median()),
    'random_direct_target_median_mae':float(wide['random_direct'].median()),
    'random_logistic_target_median_mae':float(wide['random_logistic_plugin'].median()),
}
reproduced['relative_improvement_vs_random_direct']=1-reproduced['ra_cb_target_median_mae']/reproduced['random_direct_target_median_mae']
ra_edges=edge_medians[edge_medians.method.eq('ra_cb_amw_ddet')]
reproduced['edge_spearman']=float(spearmanr(ra_edges.estimate_auc,ra_edges.true_auc).statistic)
reproduced['targets_better_than_random_logistic']=int((wide.ra_cb_amw_ddet<wide.random_logistic_plugin).sum())
expected=parent_complete['primary_metrics']
for k in ['ra_cb_target_median_mae','random_direct_target_median_mae','random_logistic_target_median_mae','relative_improvement_vs_random_direct','edge_spearman']:
    assert abs(reproduced[k]-expected[k])<1e-10,(k,reproduced[k],expected[k])
assert reproduced['targets_better_than_random_logistic']==expected['targets_better_than_random_logistic']
repro_record={'stage':'StageT3-X','parent_metrics_reproduced_exactly':True,'reproduced':reproduced,'parent':expected,'created_utc':now()}
repro_record['reproduction_record_sha256']=sha_json(repro_record)
write_json(P1/'StageT3-X_Exact_Parent_Result_Reproduction_v0.1.json',repro_record)

# Selector regret among the three frozen active posterior candidates.
candidate_methods=['amw_u','amw_cb2','amw_ddet']
rep_candidate=(primary_all[primary_all.method.isin(candidate_methods)].groupby(['target','replicate','method'],as_index=False).agg(replicate_edge_mae=('absolute_error','median'),replicate_edge_mean_error=('absolute_error','mean')))
rep_pivot=rep_candidate.pivot(index=['target','replicate'],columns='method',values='replicate_edge_mae').reset_index()
diag=diagnostics[['target','replicate','selected_candidate','balance_selected','cv_brier_amw_u','cv_brier_amw_cb2','cv_brier_difference_cb2_minus_u']].copy()
diag['selected_method']=np.where(diag.selected_candidate.astype(str).str.upper().eq('AMW-CB2'),'amw_cb2','amw_u')
selector=rep_pivot.merge(diag,on=['target','replicate'],validate='one_to_one')
selector['selected_true_mae']=[r[r.selected_method] for _,r in selector.iterrows()]
selector['oracle_method']=selector[candidate_methods].idxmin(axis=1)
selector['oracle_true_mae']=selector[candidate_methods].min(axis=1)
selector['selector_regret']=selector.selected_true_mae-selector.oracle_true_mae
selector['selected_oracle']=selector.selected_method.eq(selector.oracle_method)
selector['brier_choice_true_loss_advantage']=np.where(selector.selected_method.eq('amw_cb2'),selector.amw_u-selector.amw_cb2,selector.amw_cb2-selector.amw_u)
write_csv(P1/'StageT3-X_Frozen_Selector_Regret_By_Replicate_v0.1.csv',selector)
selector_summary=(selector.groupby('target',as_index=False).agg(selected_oracle_rate=('selected_oracle','mean'),median_selector_regret=('selector_regret','median'),mean_selector_regret=('selector_regret','mean'),q90_selector_regret=('selector_regret',lambda x:float(np.quantile(x,.9))),brier_choice_harm_rate=('brier_choice_true_loss_advantage',lambda x:float((x<0).mean()))))
write_csv(P1/'StageT3-X_Frozen_Selector_Regret_Target_Summary_v0.1.csv',selector_summary)

# Edge-wise and target-wise frozen candidate oracle ceilings.
edge_candidate=edge_medians[edge_medians.method.isin(candidate_methods)].copy()
edge_oracle=edge_candidate.sort_values('absolute_error').groupby(['target','source','edge_id'],as_index=False).first()
edge_oracle['method']='frozen_edge_oracle'
target_oracle_rows=[]
for target,frame in target_method[target_method.method.isin(candidate_methods)].groupby('target'):
    best=frame.sort_values('target_median_absolute_error').iloc[0]
    target_oracle_rows.append({'target':target,'oracle_method':best.method,'oracle_target_median_mae':best.target_median_absolute_error})
target_oracle=pd.DataFrame(target_oracle_rows)
write_csv(P1/'StageT3-X_Frozen_Edge_Oracle_Ceiling_v0.1.csv',edge_oracle)
write_csv(P1/'StageT3-X_Frozen_Target_Oracle_Ceiling_v0.1.csv',target_oracle)

# Pairwise inversion ledger for the RA-CB method.
inversion_rows=[]
for target,frame in ra_edges.groupby('target'):
    frame=frame.reset_index(drop=True)
    for i,j in itertools.combinations(range(len(frame)),2):
        a,b=frame.iloc[i],frame.iloc[j]
        true_order=np.sign(a.true_auc-b.true_auc); pred_order=np.sign(a.estimate_auc-b.estimate_auc)
        inversion_rows.append({'target':target,'source_a':a.source,'source_b':b.source,'true_auc_a':a.true_auc,'true_auc_b':b.true_auc,'predicted_auc_a':a.estimate_auc,'predicted_auc_b':b.estimate_auc,'true_order':true_order,'predicted_order':pred_order,'inversion':bool(true_order*pred_order<0),'predicted_tie':bool(pred_order==0)})
inversion_ledger=pd.DataFrame(inversion_rows)
write_csv(P1/'StageT3-X_RA_CB_Pairwise_Rank_Inversion_Ledger_v0.1.csv',inversion_ledger)

print('Exact parent reproduction: PASS')
display(target_method)
display(rank_table)
display(selector_summary)

# 2. Rank compression, consensus-trap and evidence-demand decomposition.
cons_methods=['random_direct','random_logistic_plugin','random_joint_gmm','active_direct','amw_ddet','amw_u','amw_cb2','ra_cb_amw_ddet']
cons_pivot=primary_all[primary_all.method.isin(cons_methods)].pivot_table(index=['target','modality','edge_id','source','replicate','true_auc'],columns='method',values='estimate_auc').reset_index()
method_cols=[m for m in cons_methods if m in cons_pivot.columns]
cons_pivot['method_disagreement_sd']=cons_pivot[method_cols].std(axis=1)
cons_pivot['method_disagreement_range']=cons_pivot[method_cols].max(axis=1)-cons_pivot[method_cols].min(axis=1)
cons_pivot['consensus_estimate']=cons_pivot[method_cols].median(axis=1)
cons_pivot['consensus_absolute_error']=(cons_pivot.consensus_estimate-cons_pivot.true_auc).abs()
cons_pivot['ra_cb_absolute_error']=(cons_pivot.ra_cb_amw_ddet-cons_pivot.true_auc).abs()
cons_pivot['high_error']=cons_pivot.consensus_absolute_error>0.05
for target,idx in cons_pivot.groupby('target').groups.items():
    q=float(cons_pivot.loc[idx,'method_disagreement_sd'].quantile(.25)); cons_pivot.loc[idx,'low_disagreement']=cons_pivot.loc[idx,'method_disagreement_sd']<=q
cons_pivot['consensus_trap_case']=cons_pivot.low_disagreement.astype(bool)&cons_pivot.high_error
write_csv(P2/'StageT3-X_Consensus_Disagreement_And_Error_By_Replicate_Edge_v0.1.csv',cons_pivot)
consensus_rows=[]
for target,frame in cons_pivot.groupby('target'):
    rho=float(spearmanr(frame.method_disagreement_sd,frame.consensus_absolute_error).statistic)
    auc=np.nan
    if frame.high_error.nunique()==2:
        auc=float(roc_auc_score(frame.high_error.astype(int),frame.method_disagreement_sd))
    consensus_rows.append({'target':target,'rows':len(frame),'disagreement_error_spearman':rho,'disagreement_high_error_auc':auc,'low_disagreement_high_error_rate':float(frame.consensus_trap_case.mean()),'high_error_rate':float(frame.high_error.mean()),'median_disagreement':float(frame.method_disagreement_sd.median()),'median_consensus_error':float(frame.consensus_absolute_error.median())})
consensus_summary=pd.DataFrame(consensus_rows)
write_csv(P2/'StageT3-X_Consensus_Trap_Target_Summary_v0.1.csv',consensus_summary)

# Target source-score geometry: redundancy can hide axis-specific ordering failure.
geometry_rows=[]
for target,frame in group_logits.groupby('target'):
    wide_scores=frame.pivot(index='group_id',columns='source',values='logit')
    corr=wide_scores.corr(method='spearman')
    for a,b in itertools.combinations(corr.columns,2):
        geometry_rows.append({'target':target,'source_a':a,'source_b':b,'source_score_spearman':float(corr.loc[a,b]),'absolute_source_score_spearman':abs(float(corr.loc[a,b]))})
geometry=pd.DataFrame(geometry_rows)
write_csv(P2/'StageT3-X_Target_Source_Score_Geometry_v0.1.csv',geometry)

# Evidence curve slopes, threshold crossing and model-floor signals.
evidence_rows=[]
for target,frame in evidence_curves_parent.groupby('target'):
    frame=frame.sort_values('budget'); lookup=dict(zip(frame.budget.astype(int),frame.isotonic_median_error.astype(float)))
    def val(b): return lookup.get(b,np.nan)
    early=(val(8)-val(32))/2 if np.isfinite(val(8)) and np.isfinite(val(32)) else np.nan
    late=(val(32)-val(128))/2 if np.isfinite(val(32)) and np.isfinite(val(128)) else np.nan
    last_improvement=(val(64)-val(128)) if np.isfinite(val(64)) and np.isfinite(val(128)) else np.nan
    floor=val(128)
    evidence_rows.append({'target':target,'error_b8':val(8),'error_b16':val(16),'error_b32':val(32),'error_b64':val(64),'error_b128':val(128),'early_improvement_per_doubling_8_to_32':early,'late_improvement_per_doubling_32_to_128':late,'last_doubling_improvement_64_to_128':last_improvement,'model_floor_signal':bool(np.isfinite(floor) and floor>THRESHOLD and np.isfinite(last_improvement) and last_improvement<0.01),'threshold_reached_by_128':bool(np.isfinite(floor) and floor<=THRESHOLD)})
evidence_decomposition=pd.DataFrame(evidence_rows).merge(evidence_eval_parent[['target','pilot_disagreement_index','mu_log2_budget','support_status','probability_observed_interval','prospective_interval_nll','status','operational_budget_administrative']],on='target',how='left')
write_csv(P4/'StageT3-X_Evidence_Demand_Slope_And_Error_Floor_Decomposition_v0.1.csv',evidence_decomposition)

# Fixed-certificate selective risk curve under transparent radius sensitivity.
radius_rows=[]
base=cert_parent.copy()
for radius in np.linspace(0.02,0.30,57):
    lower=np.clip(base.estimate_auc-radius,0,1); upper=np.clip(base.estimate_auc+radius,0,1)
    status=np.where(lower>=base.retention_threshold,'CERTIFIED_RETAINED',np.where(upper<base.retention_threshold,'EXCLUDED','UNIDENTIFIABLE'))
    truth_retained=base.true_auc>=base.retention_threshold
    decided=status!='UNIDENTIFIABLE'
    wrong=((status=='CERTIFIED_RETAINED')&(~truth_retained))|((status=='EXCLUDED')&truth_retained)
    radius_rows.append({'radius':float(radius),'interval_coverage':float(((base.true_auc>=lower)&(base.true_auc<=upper)).mean()),'decision_coverage':float(decided.mean()),'wrong_decision_rate_among_decided':float(wrong[decided].mean()) if decided.any() else np.nan,'decided_edges':int(decided.sum())})
certificate_curve=pd.DataFrame(radius_rows)
write_csv(P5/'StageT3-X_Transparent_Certificate_Radius_Selectivity_Curve_v0.1.csv',certificate_curve)

# Figures.
plt.figure(figsize=(8,6))
for target,frame in ra_edges.groupby('target'):
    plt.scatter(frame.true_auc,frame.estimate_auc,s=70,label=target)
    for _,r in frame.iterrows(): plt.annotate(r.source,(r.true_auc,r.estimate_auc),fontsize=8)
lims=[min(ra_edges.true_auc.min(),ra_edges.estimate_auc.min())-.03,max(ra_edges.true_auc.max(),ra_edges.estimate_auc.max())+.03]
plt.plot(lims,lims,'--'); plt.xlim(lims); plt.ylim(lims); plt.xlabel('True edge AUC'); plt.ylabel('Frozen RA-CB median estimate'); plt.title('Stage T3-X: RA-CB rank compression and inversions'); plt.legend(); plt.tight_layout(); plt.savefig(P2/'StageT3-X_RA_CB_Rank_Compression_v0.1.png',dpi=220); plt.show()

plt.figure(figsize=(8,5))
for target,frame in cons_pivot.groupby('target'):
    plt.scatter(frame.method_disagreement_sd,frame.consensus_absolute_error,alpha=.35,label=target)
plt.axhline(.05,linestyle='--'); plt.xlabel('Across-method disagreement SD'); plt.ylabel('Consensus absolute edge error'); plt.title('Consensus trap: disagreement need not reveal shared error'); plt.legend(); plt.tight_layout(); plt.savefig(P2/'StageT3-X_Consensus_Trap_Scatter_v0.1.png',dpi=220); plt.show()

plt.figure(figsize=(8,5))
for target,frame in evidence_curves_parent.groupby('target'):
    plt.plot(frame.budget,frame.isotonic_median_error,marker='o',label=target)
plt.axhline(THRESHOLD,linestyle='--'); plt.xscale('log',base=2); plt.xlabel('Witness-group budget'); plt.ylabel('Isotonic median absolute AUC error'); plt.title('Evidence limitation versus model-floor plateau'); plt.legend(); plt.tight_layout(); plt.savefig(P4/'StageT3-X_Evidence_Demand_Error_Floor_v0.1.png',dpi=220); plt.show()

print('Consensus-trap summary:'); display(consensus_summary)
print('Evidence-demand decomposition:'); display(evidence_decomposition)

# 3. Transparent posterior-family and edge-functional grid on the exact frozen manifests.
def weighted_auc(scores,probabilities):
    scores=np.asarray(scores,float); pos=np.asarray(probabilities,float); neg=1-pos
    denom=pos.sum()*neg.sum()
    if denom<=0:return np.nan
    order=np.argsort(scores,kind='mergesort'); scores=scores[order]; pos=pos[order]; neg=neg[order]
    numerator=0.; neg_before=0.; starts=np.r_[0,np.flatnonzero(np.diff(scores))+1]; ends=np.r_[starts[1:],len(scores)]
    for a,b in zip(starts,ends):
        ph=pos[a:b].sum(); nh=neg[a:b].sum(); numerator+=ph*(neg_before+.5*nh); neg_before+=nh
    return float(numerator/denom)

def model_factory(kind,seed=SEED):
    if kind in {'shared_linear','edge_linear'}:
        return make_pipeline(StandardScaler(),LogisticRegression(C=3.0,solver='lbfgs',max_iter=3000,random_state=seed))
    if kind=='shared_quadratic':
        return make_pipeline(PolynomialFeatures(degree=2,include_bias=False),StandardScaler(),LogisticRegression(C=1.0,solver='lbfgs',max_iter=3000,random_state=seed))
    if kind in {'shared_spline','edge_spline'}:
        return make_pipeline(SplineTransformer(n_knots=4,degree=3,include_bias=False),StandardScaler(),LogisticRegression(C=1.0,solver='lbfgs',max_iter=3000,random_state=seed))
    if kind=='shared_histgb':
        return HistGradientBoostingClassifier(max_depth=2,max_iter=100,learning_rate=.05,l2_regularization=1.0,min_samples_leaf=5,random_state=seed)
    raise KeyError(kind)

def crossfit_posterior(X,y,witness_idx,kind,seed):
    X=np.asarray(X,float); y=np.asarray(y,int); witness_idx=np.asarray(witness_idx,int)
    yw=y[witness_idx]
    if len(np.unique(yw))<2:return None,'single_class'
    try:
        model=model_factory(kind,seed); model.fit(X[witness_idx],yw); eta=model.predict_proba(X)[:,1]
        counts=np.bincount(yw,minlength=2); folds=int(min(4,counts.min()))
        if folds>=2:
            skf=StratifiedKFold(n_splits=folds,shuffle=True,random_state=seed)
            for train_local,test_local in skf.split(X[witness_idx],yw):
                fold=model_factory(kind,seed+17+int(test_local[0])); fold.fit(X[witness_idx][train_local],yw[train_local]); eta[witness_idx[test_local]]=fold.predict_proba(X[witness_idx][test_local])[:,1]
        return np.clip(eta,1e-5,1-1e-5),'PASS'
    except Exception as e:
        return None,f'{type(e).__name__}: {e}'

def target_data(target):
    f=group_logits[group_logits.target.eq(target)].copy()
    wide=f.pivot(index='group_id',columns='source',values='logit').reset_index()
    meta=f[['group_id','modality','provider']].drop_duplicates('group_id')
    wide=wide.merge(meta,on='group_id',validate='one_to_one').merge(matched[['target','group_id','label']],on='group_id',validate='one_to_one')
    sources=sorted(f.source.unique().tolist())
    wide=wide.sort_values('group_id').reset_index(drop=True)
    X=wide[sources].to_numpy(float); X=(X-X.mean(0))/(X.std(0)+1e-9)
    y=wide.label.to_numpy(int); groups=wide.group_id.astype(str).to_numpy()
    return wide,sources,X,y,groups

target_cache={t:target_data(t) for t in sorted(group_logits.target.unique())}
manifest_map={}
for r in manifests[manifests.design.eq('active_d_optimal')].itertuples(): manifest_map[(r.target,int(r.budget),int(r.replicate))]=json.loads(r.group_ids_json)
truth_map={(r.target,r.source):float(r.true_auc) for r in edge_truth.itertuples()}

PRIMARY_GRID=['shared_linear','shared_quadratic','shared_spline','shared_histgb','edge_linear','edge_spline']
transparent_rows=[]; transparent_skips=[]
for target,(table,sources,X,y,groups) in target_cache.items():
    lookup={g:i for i,g in enumerate(groups)}
    for rep in range(N_REPS):
        key=(target,PRIMARY_BUDGET,rep)
        if key not in manifest_map: continue
        idx=np.asarray([lookup[g] for g in manifest_map[key] if g in lookup],int)
        if len(idx)!=PRIMARY_BUDGET:
            transparent_skips.append({'target':target,'budget':PRIMARY_BUDGET,'replicate':rep,'method':'ALL','reason':'manifest_group_mismatch'}); continue
        for kind in PRIMARY_GRID:
            if kind.startswith('edge_'):
                for j,source in enumerate(sources):
                    eta,status=crossfit_posterior(X[:,[j]],y,idx,kind,SEED+rep*101+j)
                    if eta is None:
                        transparent_skips.append({'target':target,'budget':PRIMARY_BUDGET,'replicate':rep,'method':kind,'source':source,'reason':status}); continue
                    est=weighted_auc(X[:,j],eta)
                    transparent_rows.append({'target':target,'modality':table.modality.iloc[0],'provider':table.provider.iloc[0],'budget':PRIMARY_BUDGET,'replicate':rep,'method':kind,'source':source,'edge_id':f'{source}__TO__{target}','estimate_auc':est,'true_auc':truth_map[(target,source)],'absolute_error':abs(est-truth_map[(target,source)]),'fit_status':status})
            else:
                eta,status=crossfit_posterior(X,y,idx,kind,SEED+rep*101)
                if eta is None:
                    transparent_skips.append({'target':target,'budget':PRIMARY_BUDGET,'replicate':rep,'method':kind,'source':'ALL','reason':status}); continue
                for j,source in enumerate(sources):
                    est=weighted_auc(X[:,j],eta)
                    transparent_rows.append({'target':target,'modality':table.modality.iloc[0],'provider':table.provider.iloc[0],'budget':PRIMARY_BUDGET,'replicate':rep,'method':kind,'source':source,'edge_id':f'{source}__TO__{target}','estimate_auc':est,'true_auc':truth_map[(target,source)],'absolute_error':abs(est-truth_map[(target,source)]),'fit_status':status})
    print('Transparent budget-32 grid complete:',target)
transparent=pd.DataFrame(transparent_rows); transparent_skips=pd.DataFrame(transparent_skips)
write_csv(P3/'StageT3-X_Transparent_Budget32_Posterior_And_Functional_Grid_v0.1.csv',transparent)
write_csv(P3/'StageT3-X_Transparent_Budget32_Model_Skips_v0.1.csv',transparent_skips)

# Full-label cross-fitted ceilings diagnose model-class approximation independent of witness budget.
ceiling_rows=[]
for target,(table,sources,X,y,groups) in target_cache.items():
    idx=np.arange(len(y))
    for kind in PRIMARY_GRID:
        if kind.startswith('edge_'):
            for j,source in enumerate(sources):
                eta,status=crossfit_posterior(X[:,[j]],y,idx,kind,SEED+9000+j)
                if eta is None:continue
                est=weighted_auc(X[:,j],eta); ceiling_rows.append({'target':target,'modality':table.modality.iloc[0],'method':kind+'_full_label_ceiling','source':source,'estimate_auc':est,'true_auc':truth_map[(target,source)],'absolute_error':abs(est-truth_map[(target,source)]),'fit_status':status})
        else:
            eta,status=crossfit_posterior(X,y,idx,kind,SEED+9000)
            if eta is None:continue
            for j,source in enumerate(sources):
                est=weighted_auc(X[:,j],eta); ceiling_rows.append({'target':target,'modality':table.modality.iloc[0],'method':kind+'_full_label_ceiling','source':source,'estimate_auc':est,'true_auc':truth_map[(target,source)],'absolute_error':abs(est-truth_map[(target,source)]),'fit_status':status})
ceiling=pd.DataFrame(ceiling_rows)
write_csv(P3/'StageT3-X_Full_Label_Crossfit_Model_Class_Ceilings_v0.1.csv',ceiling)

# Summaries and rank metrics for transparent methods.
transparent_target=(transparent.groupby(['method','target','modality'],as_index=False).agg(target_median_absolute_error=('absolute_error','median'),target_mean_absolute_error=('absolute_error','mean'),usable_rows=('absolute_error','size')))
transparent_edge=(transparent.groupby(['method','target','modality','source','edge_id'],as_index=False).agg(estimate_auc=('estimate_auc','median'),true_auc=('true_auc','first'),absolute_error=('absolute_error','median'),usable_replicates=('replicate','nunique')))
transparent_rank=[]
for (method,target),f in transparent_edge.groupby(['method','target']): transparent_rank.append({'method':method,'target':target,'modality':f.modality.iloc[0],**rank_metrics(f)})
transparent_rank=pd.DataFrame(transparent_rank)
ceiling_target=(ceiling.groupby(['method','target','modality'],as_index=False).agg(target_median_absolute_error=('absolute_error','median'),target_mean_absolute_error=('absolute_error','mean')))
ceiling_rank=[]
for (method,target),f in ceiling.groupby(['method','target']): ceiling_rank.append({'method':method,'target':target,'modality':f.modality.iloc[0],**rank_metrics(f)})
ceiling_rank=pd.DataFrame(ceiling_rank)
write_csv(P3/'StageT3-X_Transparent_Budget32_Target_Method_Summary_v0.1.csv',transparent_target)
write_csv(P3/'StageT3-X_Transparent_Budget32_Edge_And_Rank_Summary_v0.1.csv',transparent_edge.merge(transparent_rank[['method','target','spearman','range_ratio','inversions']],on=['method','target'],how='left'))
write_csv(P3/'StageT3-X_Full_Label_Model_Class_Ceiling_Summary_v0.1.csv',ceiling_target.merge(ceiling_rank[['method','target','spearman','range_ratio','inversions']],on=['method','target'],how='left'))

# Global method metrics use target as the primary exchange unit.
def global_method_metrics(target_summary,edge_summary):
    rows=[]
    for method,tf in target_summary.groupby('method'):
        ef=edge_summary[edge_summary.method.eq(method)]
        w=tf.set_index('target').target_median_absolute_error
        if len(w)<2:continue
        rd=wide.loc[w.index,'random_direct']; rl=wide.loc[w.index,'random_logistic_plugin']
        mae=float(w.median()); direct=float(rd.median()); logistic=float(rl.median())
        rows.append({'method':method,'target_count':len(w),'target_median_mae':mae,'relative_improvement_vs_random_direct':1-mae/direct if direct>0 else np.nan,'targets_better_than_random_logistic':int((w<rl).sum()),'strict_majority_better_than_random_logistic':bool((w<rl).sum()>len(w)/2),'edge_spearman':float(spearmanr(ef.estimate_auc,ef.true_auc).statistic) if len(ef)>=3 else np.nan,'passes_transparent_rescue_shape':bool(mae<=.05 and (1-mae/direct)>=.25 and (w<rl).sum()>len(w)/2 and len(ef)>=3 and spearmanr(ef.estimate_auc,ef.true_auc).statistic>=.75)})
    return pd.DataFrame(rows).sort_values(['passes_transparent_rescue_shape','target_median_mae'],ascending=[False,True])
transparent_global=global_method_metrics(transparent_target,transparent_edge)
write_csv(P3/'StageT3-X_Transparent_Budget32_Global_Method_Adjudication_v0.1.csv',transparent_global)

print('Transparent budget-32 global model adjudication:'); display(transparent_global)

# 4. Budget sensitivity for the best transparent shared and edge-specific families.
shared_candidates=transparent_global[transparent_global.method.str.startswith('shared_')]
edge_candidates=transparent_global[transparent_global.method.str.startswith('edge_')]
assert len(shared_candidates) and len(edge_candidates)
best_shared=shared_candidates.sort_values(['target_median_mae','edge_spearman'],ascending=[True,False]).iloc[0].method
best_edge=edge_candidates.sort_values(['target_median_mae','edge_spearman'],ascending=[True,False]).iloc[0].method
budget_methods=[best_shared,best_edge]
budget_rows=[]; budget_skips=[]
for target,(table,sources,X,y,groups) in target_cache.items():
    lookup={g:i for i,g in enumerate(groups)}
    for budget in [16,64,128]:
        if len(groups)<budget:continue
        for rep in range(N_REPS):
            key=(target,budget,rep)
            if key not in manifest_map:continue
            idx=np.asarray([lookup[g] for g in manifest_map[key] if g in lookup],int)
            if len(idx)!=budget:
                budget_skips.append({'target':target,'budget':budget,'replicate':rep,'method':'ALL','reason':'manifest_group_mismatch'});continue
            for kind in budget_methods:
                if kind.startswith('edge_'):
                    for j,source in enumerate(sources):
                        eta,status=crossfit_posterior(X[:,[j]],y,idx,kind,SEED+budget*10000+rep*101+j)
                        if eta is None:
                            budget_skips.append({'target':target,'budget':budget,'replicate':rep,'method':kind,'source':source,'reason':status});continue
                        est=weighted_auc(X[:,j],eta);budget_rows.append({'target':target,'modality':table.modality.iloc[0],'budget':budget,'replicate':rep,'method':kind,'source':source,'estimate_auc':est,'true_auc':truth_map[(target,source)],'absolute_error':abs(est-truth_map[(target,source)])})
                else:
                    eta,status=crossfit_posterior(X,y,idx,kind,SEED+budget*10000+rep*101)
                    if eta is None:
                        budget_skips.append({'target':target,'budget':budget,'replicate':rep,'method':kind,'source':'ALL','reason':status});continue
                    for j,source in enumerate(sources):
                        est=weighted_auc(X[:,j],eta);budget_rows.append({'target':target,'modality':table.modality.iloc[0],'budget':budget,'replicate':rep,'method':kind,'source':source,'estimate_auc':est,'true_auc':truth_map[(target,source)],'absolute_error':abs(est-truth_map[(target,source)])})
        print('Transparent budget sensitivity complete:',target,budget)
budget_results=pd.DataFrame(budget_rows)
# Add primary-budget rows for the selected methods.
budget_results=pd.concat([transparent[transparent.method.isin(budget_methods)],budget_results],ignore_index=True,sort=False)
write_csv(P4/'StageT3-X_Best_Shared_And_Edge_Budget_Sensitivity_All_Replicates_v0.1.csv',budget_results)
write_csv(P4/'StageT3-X_Budget_Sensitivity_Skips_v0.1.csv',pd.DataFrame(budget_skips))

budget_target=(budget_results.groupby(['method','budget','target','modality'],as_index=False).agg(target_median_absolute_error=('absolute_error','median'),target_mean_absolute_error=('absolute_error','mean')))
budget_edge=(budget_results.groupby(['method','budget','target','modality','source'],as_index=False).agg(estimate_auc=('estimate_auc','median'),true_auc=('true_auc','first'),absolute_error=('absolute_error','median')))
budget_global=[]
for (method,budget),tf in budget_target.groupby(['method','budget']):
    ef=budget_edge[(budget_edge.method.eq(method))&(budget_edge.budget.eq(budget))]
    budget_global.append({'method':method,'budget':int(budget),'target_median_mae':float(tf.target_median_absolute_error.median()),'edge_spearman':float(spearmanr(ef.estimate_auc,ef.true_auc).statistic),'all_targets_mae_le_0_05':bool((tf.target_median_absolute_error<=.05).all()),'target_count':len(tf)})
budget_global=pd.DataFrame(budget_global)
write_csv(P4/'StageT3-X_Budget_Sensitivity_Target_And_Global_Summary_v0.1.csv',budget_target.merge(budget_global,on=['method','budget'],how='left',suffixes=('','_global')))

plt.figure(figsize=(8,5))
for (method,target),f in budget_target.groupby(['method','target']):
    plt.plot(f.budget,f.target_median_absolute_error,marker='o',label=f'{method}:{target}')
plt.axhline(.05,linestyle='--');plt.xscale('log',base=2);plt.xlabel('Witness-group budget');plt.ylabel('Target median absolute edge error');plt.title('Transparent model-family budget sensitivity');plt.legend(fontsize=7);plt.tight_layout();plt.savefig(P4/'StageT3-X_Transparent_Model_Budget_Sensitivity_v0.1.png',dpi=220);plt.show()

print('Best shared model:',best_shared)
print('Best edge-specific model:',best_edge)
display(budget_global)

# 5. Mechanism adjudication and upgrade decision.
# Frozen oracle global metrics.
edge_oracle_metric=rank_metrics(edge_oracle)
frozen_target_oracle_global_mae=float(target_oracle.oracle_target_median_mae.median())
selector_dominated=bool(
    frozen_target_oracle_global_mae <= .05
    and np.isfinite(edge_oracle_metric['spearman'])
    and edge_oracle_metric['spearman'] >= .75
    and float(selector.selector_regret.mean()) >= .002
)

ra_cb_mae=reproduced['ra_cb_target_median_mae']
ra_cb_rank=reproduced['edge_spearman']
best_shared_row=transparent_global[transparent_global.method.eq(best_shared)].iloc[0]
best_edge_row=transparent_global[transparent_global.method.eq(best_edge)].iloc[0]
shared_improvement=1-float(best_shared_row.target_median_mae)/ra_cb_mae
edge_improvement=1-float(best_edge_row.target_median_mae)/ra_cb_mae
shared_posterior_misspecification=bool(
    shared_improvement >= .20
    and float(best_shared_row.edge_spearman) >= ra_cb_rank + .05
)
functional_rank_misalignment=bool(
    float(best_edge_row.target_median_mae) <= float(best_shared_row.target_median_mae)*.90
    and float(best_edge_row.edge_spearman) >= max(.75,float(best_shared_row.edge_spearman)+.05)
)

b32=budget_global[budget_global.budget.eq(32)].set_index('method')
later=budget_global[budget_global.budget.isin([64,128])]
budget_limited=False
for method in budget_methods:
    base=b32.loc[method] if method in b32.index else None
    good=later[(later.method.eq(method))&(later.all_targets_mae_le_0_05)&(later.edge_spearman>=.75)]
    if base is not None and not (bool(base.all_targets_mae_le_0_05) and float(base.edge_spearman)>=.75) and len(good): budget_limited=True

model_floor_supported=bool(evidence_decomposition.model_floor_signal.any())
consensus_trap_supported=bool(((consensus_summary.disagreement_error_spearman.abs()<.30)&(consensus_summary.low_disagreement_high_error_rate>=.05)).any())
certificate_survived=bool(parent_complete['primary_metrics']['interval_coverage']>=.85 and parent_complete['primary_metrics']['wrong_decision_rate_among_decided']<=.05)
rank_observability_separates_from_scalar_error=bool(parent_complete['primary_metrics']['ra_cb_target_median_mae']<=.05 and parent_complete['primary_metrics']['edge_spearman']<.75)
evidence_order_separates_from_interval_calibration=bool(parent_complete['evidence_metrics']['supported_mean_interval_nll']<=2.41565 and parent_complete['evidence_metrics']['interval_order_concordance']<.5)

theory_decomposition_supported=bool(rank_observability_separates_from_scalar_error and certificate_survived and (consensus_trap_supported or evidence_order_separates_from_interval_calibration))
method_v1_direction_supported=bool(selector_dominated or shared_posterior_misspecification or functional_rank_misalignment or budget_limited)
if theory_decomposition_supported and method_v1_direction_supported:
    decision='AUTHORISE_DECOMPOSED_OBSERVABILITY_THEORY_AND_V1_METHOD_DEVELOPMENT'
elif theory_decomposition_supported:
    decision='AUTHORISE_DECOMPOSED_OBSERVABILITY_THEORY_ONLY'
elif method_v1_direction_supported:
    decision='AUTHORISE_TARGETED_V1_METHOD_DEVELOPMENT_ONLY'
else:
    decision='STOP_ESCALATION_RETAIN_T3A_BOUNDARY_REPORT'

mechanisms=pd.DataFrame([
    {'mechanism':'selector_dominated','supported':selector_dominated,'observed':f'oracle_global_mae={frozen_target_oracle_global_mae:.6f}; oracle_spearman={edge_oracle_metric["spearman"]}; mean_selector_regret={selector.selector_regret.mean():.6f}','implication':'Replace Brier-only selector with functional/rank-aware selection.'},
    {'mechanism':'shared_posterior_misspecification','supported':shared_posterior_misspecification,'observed':f'best_shared={best_shared}; improvement_vs_ra_cb={shared_improvement:.4f}; spearman={best_shared_row.edge_spearman}','implication':'Develop a flexible shared posterior with explicit misspecification detection.'},
    {'mechanism':'functional_rank_misalignment','supported':functional_rank_misalignment,'observed':f'best_edge={best_edge}; edge_improvement_vs_ra_cb={edge_improvement:.4f}; spearman={best_edge_row.edge_spearman}','implication':'Develop edge-specific or rank-aware AUC functionals rather than one shared posterior output.'},
    {'mechanism':'budget_limited','supported':budget_limited,'observed':later.to_dict(orient='records'),'implication':'Increase evidence only under a nonadaptive future protocol; do not reinterpret Stage T3-A.'},
    {'mechanism':'model_floor','supported':model_floor_supported,'observed':evidence_decomposition[['target','error_b64','error_b128','model_floor_signal']].to_dict(orient='records'),'implication':'Separate repairable evidence demand from frozen-model error floor.'},
    {'mechanism':'consensus_trap','supported':consensus_trap_supported,'observed':consensus_summary.to_dict(orient='records'),'implication':'Add model-class and structural-bias probes; estimator agreement alone is insufficient.'},
    {'mechanism':'certificate_survival','supported':certificate_survived,'observed':f'coverage={parent_complete["primary_metrics"]["interval_coverage"]}; wrong_decision={parent_complete["primary_metrics"]["wrong_decision_rate_among_decided"]}; decision_coverage={parent_complete["primary_metrics"]["decision_coverage"]}','implication':'Promote selective certification and abstention to a co-primary theoretical object.'},
    {'mechanism':'rank_scalar_separation','supported':rank_observability_separates_from_scalar_error,'observed':f'median_mae={ra_cb_mae}; edge_spearman={ra_cb_rank}','implication':'Formalize scalar edge-performance observability separately from rank observability.'},
    {'mechanism':'evidence_order_calibration_separation','supported':evidence_order_separates_from_interval_calibration,'observed':f'mean_nll={parent_complete["evidence_metrics"]["supported_mean_interval_nll"]}; order_concordance={parent_complete["evidence_metrics"]["interval_order_concordance"]}','implication':'Evidence-demand interval calibration does not imply cross-target ordering.'},
])
write_csv(P6/'StageT3-X_Mechanism_Adjudication_v0.1.csv',mechanisms)

recommendations=[]
if selector_dominated: recommendations.append('Build a preregistered functional/rank-aware selector and compare it with Brier selection on transparent development targets.')
if shared_posterior_misspecification: recommendations.append(f'Promote {best_shared} as a development candidate and add an explicit consensus-bias detector.')
if functional_rank_misalignment: recommendations.append(f'Develop {best_edge}-style edge-specific estimation or a hierarchical shared-plus-edge residual model.')
if budget_limited: recommendations.append('Model evidence demand as budget-dependent identifiability rather than a single budget-8 disagreement scalar.')
if model_floor_supported: recommendations.append('Fit a repairable-plus-error-floor censored curve and prohibit unbounded budget extrapolation.')
if consensus_trap_supported: recommendations.append('Create a model-class disagreement and local rank-cycle diagnostic to distinguish reliable consensus from shared bias.')
if certificate_survived: recommendations.append('Retain frozen conformal certification and report coverage–abstention trade-offs as a principal result.')
if theory_decomposition_supported: recommendations.append('Proceed to the complete decomposed-observability theory, transparent multi-target validation and a new prospective reserve design.')
if not recommendations: recommendations.append('Do not escalate the method; retain the Stage T3-A boundary report and write the negative result transparently.')
recommendation_table=pd.DataFrame({'priority':range(1,len(recommendations)+1),'recommendation':recommendations})
write_csv(P6/'StageT3-X_Recommended_Next_Actions_v0.1.csv',recommendation_table)

# Integrity and completion gates.
gates=pd.DataFrame([
    {'gate':'G1_exact_parent_bundle_and_self_hash','passed':True,'observed':EXPECTED_BUNDLE_SHA},
    {'gate':'G2_official_outcome_reconstruction_exact','passed':bool(np.allclose(coverage.coverage,1.0)),'observed':coverage.to_dict(orient='records')},
    {'gate':'G3_parent_metrics_reproduced_exactly','passed':True,'observed':reproduced},
    {'gate':'G4_frozen_selector_rank_and_consensus_autopsy_complete','passed':bool(len(selector)==200 and len(rank_table)>0 and len(cons_pivot)>0),'observed':f'selector_rows={len(selector)}; rank_rows={len(rank_table)}; consensus_rows={len(cons_pivot)}'},
    {'gate':'G5_transparent_model_grid_complete','passed':bool(len(transparent)>0 and transparent.method.nunique()==len(PRIMARY_GRID)),'observed':f'rows={len(transparent)}; methods={transparent.method.nunique()}'},
    {'gate':'G6_full_label_ceilings_complete','passed':bool(len(ceiling)>0),'observed':len(ceiling)},
    {'gate':'G7_budget_sensitivity_complete','passed':bool(set(budget_global.budget)>=set([16,32,64,128])),'observed':budget_global.to_dict(orient='records')},
    {'gate':'G8_mechanism_adjudication_complete','passed':bool(len(mechanisms)==9),'observed':decision},
    {'gate':'G9_t3a_not_reinterpreted','passed':True,'observed':'SCENARIO_C retained as immutable parent truth'},
    {'gate':'G10_no_new_blind_or_confirmatory_claim','passed':True,'observed':'transparent post-unblinding development only'},
    {'gate':'G11_single_pilot_deployment_false','passed':True,'observed':False},
    {'gate':'G12_stage3_and_stage12_false','passed':True,'observed':False},
])
write_csv(P6/'StageT3-X_Gates_v0.1.csv',gates)

# Summary figure comparing all frozen and transparent methods.
combined_target=pd.concat([
    target_method[['method','target','target_median_absolute_error']].assign(family='frozen'),
    transparent_target[['method','target','target_median_absolute_error']].assign(family='transparent')
],ignore_index=True)
plot_order=(combined_target.groupby('method').target_median_absolute_error.median().sort_values().index.tolist())
plt.figure(figsize=(11,6))
for target,frame in combined_target.groupby('target'):
    x=[plot_order.index(m) for m in frame.method]
    plt.scatter(x,frame.target_median_absolute_error,s=55,label=target)
plt.axhline(.05,linestyle='--');plt.xticks(range(len(plot_order)),plot_order,rotation=60,ha='right');plt.ylabel('Target median absolute edge error');plt.title('Frozen and transparent method-family autopsy');plt.legend();plt.tight_layout();plt.savefig(P6/'StageT3-X_Frozen_And_Transparent_Method_Comparison_v0.1.png',dpi=220);plt.show()

# Human-readable theory update recommendation.
theory_update=f'''# Stage T3-X theory and method upgrade decision\n\n- Parent Stage T3-A scenario: `{EXPECTED_SCENARIO}`\n- Stage T3-X decision: `{decision}`\n- Theory decomposition supported: `{theory_decomposition_supported}`\n- Method-v1 direction supported: `{method_v1_direction_supported}`\n- Selector dominated: `{selector_dominated}`\n- Shared-posterior misspecification supported: `{shared_posterior_misspecification}`\n- Functional/rank misalignment supported: `{functional_rank_misalignment}`\n- Budget limitation supported: `{budget_limited}`\n- Model-floor signal supported: `{model_floor_supported}`\n- Consensus trap supported: `{consensus_trap_supported}`\n- Certificate survival supported: `{certificate_survived}`\n\n## Required interpretation\n\nStage T3-A remains a locked-blind Scenario C result. Stage T3-X is a transparent mechanism study. Any method selected here is development-only and requires a completely new prospective reserve.\n\n## Recommended next actions\n\n'''+''.join(f'{i+1}. {x}\n' for i,x in enumerate(recommendations))
write_text(P6/'StageT3-X_Theory_And_Method_Upgrade_Decision_v0.1.md',theory_update)

complete={
    'stage':'StageT3-X','decision':decision,'parent_t3a_final_record_sha256':EXPECTED_FINAL_SHA,'parent_t3a_scenario':EXPECTED_SCENARIO,
    'transparent_post_unblinding':True,'parent_reproduced_exactly':True,'targets':sorted(target_cache),'best_shared_method':best_shared,'best_edge_specific_method':best_edge,
    'mechanism_support':{r.mechanism:bool(r.supported) for r in mechanisms.itertuples()},'theory_decomposition_supported':theory_decomposition_supported,'method_v1_direction_supported':method_v1_direction_supported,
    'recommendations':recommendations,'all_gates_passed':bool(gates.passed.all()),'t3a_reinterpreted_as_success':False,'new_blind_access_authorised':False,'single_pilot_deployment_authorised':False,'stage3_execution_authorised':False,'stage12_authorised':False,'completed_utc':now()
}
complete['final_record_sha256']=sha_json(complete)
write_json(P6/'StageT3-X_Complete_v0.1.json',complete)
summary=f'''# Stage T3-X transparent failure-autopsy result\n\n- Decision: `{decision}`\n- Parent Stage T3-A remains: `{EXPECTED_SCENARIO}`\n- Best shared transparent method: `{best_shared}`\n- Best edge-specific transparent method: `{best_edge}`\n- Theory decomposition supported: `{theory_decomposition_supported}`\n- Method-v1 direction supported: `{method_v1_direction_supported}`\n- Consensus trap supported: `{consensus_trap_supported}`\n- Model-floor signal supported: `{model_floor_supported}`\n- Certificate survival supported: `{certificate_survived}`\n- New blind access authorised: `False`\n- Stage 12 authorised: `False`\n- Final record SHA256: `{complete['final_record_sha256']}`\n'''
write_text(P6/'StageT3-X_Result_Summary_v0.1.md',summary)

display(mechanisms)
display(recommendation_table)
display(gates)

# Compact canonical archive and verified durable Drive commit.
canonical=RUNTIME_ROOT/'StageT3-X_Canonical_Records_v0.1.zip'
with zipfile.ZipFile(canonical,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for f in sorted(RESULT_ROOT.rglob('*')):
        if f.is_file():z.write(f,arcname=str(f.relative_to(RESULT_ROOT)))
commit_sources=[canonical,P6/'StageT3-X_Complete_v0.1.json',P6/'StageT3-X_Result_Summary_v0.1.md',P6/'StageT3-X_Gates_v0.1.csv',P6/'StageT3-X_Mechanism_Adjudication_v0.1.csv',P6/'StageT3-X_Recommended_Next_Actions_v0.1.csv',P6/'StageT3-X_Theory_And_Method_Upgrade_Decision_v0.1.md',P3/'StageT3-X_Transparent_Budget32_Global_Method_Adjudication_v0.1.csv',P4/'StageT3-X_Budget_Sensitivity_Target_And_Global_Summary_v0.1.csv',P2/'StageT3-X_Consensus_Trap_Target_Summary_v0.1.csv']
commit_rows=[]
for src in commit_sources:
    dst=COMMIT_ROOT/src.name;tmp=dst.with_suffix(dst.suffix+'.tmp');shutil.copy2(src,tmp);os.replace(tmp,dst);assert sha_file(src)==sha_file(dst)
    commit_rows.append({'file':src.name,'bytes':dst.stat().st_size,'sha256':sha_file(dst),'drive_path':str(dst)})
os.sync();time.sleep(3)
for r in commit_rows:
    p=Path(r['drive_path']);assert p.is_file() and p.stat().st_size==r['bytes'] and sha_file(p)==r['sha256']
commit_manifest={'stage':'StageT3-X','decision':decision,'commit_root':str(COMMIT_ROOT),'canonical_bundle_sha256':sha_file(canonical),'files':commit_rows,'all_drive_copies_reopened_and_hash_verified':True,'drive_flush_requested':True,'new_blind_access_authorised':False,'stage12_authorised':False,'committed_utc':now()}
commit_manifest['commit_manifest_sha256']=sha_json(commit_manifest)
write_json(COMMIT_ROOT/'StageT3-X_Durable_Commit_Manifest_v0.1.json',commit_manifest)
os.sync();time.sleep(3);assert verify_self_record(COMMIT_ROOT/'StageT3-X_Durable_Commit_Manifest_v0.1.json','commit_manifest_sha256')['commit_manifest_sha256']==commit_manifest['commit_manifest_sha256']

# Remove transient official OASBUD raw material after verified compact commit.
if RAW_ROOT.exists():shutil.rmtree(RAW_ROOT)
flush='OS_SYNC_COMPLETE'
if IN_COLAB:
    try: drive.flush_and_unmount();flush='FLUSH_AND_UNMOUNT_COMPLETE'
    except Exception as e:flush=f'FLUSH_REQUEST_ERROR_{type(e).__name__}'
print('\n========== STAGE T3-X COMPLETE ==========')
print('Decision:',decision)
print('Theory decomposition supported:',theory_decomposition_supported)
print('Method-v1 direction supported:',method_v1_direction_supported)
print('Best shared method:',best_shared)
print('Best edge-specific method:',best_edge)
print('Parent T3-A remains Scenario C:',True)
print('New blind access authorised:',False)
print('Stage 12 authorised:',False)
print('Drive persistence:',flush)
print('Final record SHA256:',complete['final_record_sha256'])
