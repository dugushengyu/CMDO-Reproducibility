#!/usr/bin/env python3
"""Standard-library portability audit for the exact CMDO submission route."""
from __future__ import annotations
import csv, hashlib, json, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ACTIVE=[
 'matlab/submission_figures/Figure1_IDA_RealData_Final.m',
 'matlab/submission_figures/Figure2_IDENTIFY_Validation.m',
 'matlab/submission_figures/Figure3_REUSE_Validation.m',
 'matlab/submission_figures/Figure4_PRESERVE_Refined.m',
 'matlab/submission_figures/Figure5_PhaseBoundary.m',
 'matlab/submission_figures/ED1_OutcomeFreeBoundary_v9.m',
 'matlab/submission_figures/ED2_IntegrityControls_v2.m',
 'matlab/submission_figures/cmdo_submission_load.m']
REQUIRED=['RUN_SUBMISSION_FIGURES.m',*ACTIVE,
 'source_data/figure1_assets/Figure1_assets_selected_v1.mat',
 'source_data/figure5_submission/CMDO_SystemStress_AUC_StateSummary_v1_1.csv',
 'source_data/figure6_admissibility/CMDO_Admissibility_State_MSE_Audit.csv',
 'source_data/figure4/CMDO_PRESERVE_StateRisk_v1.csv',
 'source_data/figure4/CMDO_AdaptationFrontier_v1.csv',
 'source_data/ed2/ED2_CouplingSummary_v1.csv',
 'source_data/ed2/ED2_LockedControlSummary_v1.csv',
 'source_data/submission_frozen/StageU4C_Audit_State_Results_v1.1.csv',
 'source_data/submission_frozen/StageU4C_Component_Fits_v1.1.csv',
 'source_data/submission_frozen/StageU4C_Component_Trajectory_Predictions_v1.1.csv',
 'source_data/submission_frozen/StageU4C_Evidence_Expiry_Map_v1.1.csv',
 'source_data/submission_frozen/StageU5B_Audit_State_Results_v1.0.csv',
 'source_data/submission_frozen/StageU6_Audit_State_Results_v1.0.csv',
 'source_data/submission_frozen/StageU6_Target_Summary_v1.0.csv',
 'source_data/submission_frozen/StageU7_State_Results_v1.0.csv',
 'source_data/submission_frozen/StageU7_Target_Metric_Summary_v1.0.csv',
 'source_data/submission_frozen/StageU7_Metric_Summary_v1.0.csv',
 'U10_Prospective_ECG/01_Prospective_Result/U10_PRIMARY_RESULT.json',
 'U10_Prospective_ECG/02_Posthoc_Diagnostics/U10_DEPENDENCE_DECOMPOSITION.csv',
 'U11_Information_Closure/01_Result/U11_WORLD_PLUS_georgia_v0.1.csv',
 'U11_Information_Closure/01_Result/U11_WORLD_MINUS_georgia_v0.1.csv',
 'U11_Information_Closure/01_Result/U11_WORLD_PLUS_cpsc_2018_v0.1.csv',
 'U11_Information_Closure/01_Result/U11_WORLD_MINUS_cpsc_2018_v0.1.csv',
 'provenance/submission_github_native_v4_manifest.csv']
FORBIDDEN=['C:\\Users\\zyx\\','F:\\manuscript manual\\','CMDO-U6-WSL-REPLAY','uigetfile(']
FIG1_SHA='30490a2586a9394fad868159ccd1f0248b0d9afc17d9bc970456c425c63925e7'
METHODS=['PC_PAIRED_HOEFFDING','PC_USTAT_MCDIARMID','PC_DELONG','PC_PLUGIN']
CRIT={8:[1,1,.25,.75],16:[2,4,.75,2],32:[4,4,1.5,2],64:[4,4,2,2],128:[4,4,2,2]}

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()

def git(*args):
 return subprocess.run(['git','-C',str(ROOT),*args],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True).returncode

def main():
 missing=[x for x in REQUIRED if not (ROOT/x).is_file()]
 if missing: raise RuntimeError('Missing reviewer files:\n'+'\n'.join(missing))
 if (ROOT/'.git').is_dir():
  untracked=[x for x in REQUIRED if git('ls-files','--error-unmatch','--',x)!=0]
  if untracked: raise RuntimeError('Required files are not Git-tracked:\n'+'\n'.join(untracked))
 for rel in ACTIVE:
  txt=(ROOT/rel).read_text(encoding='utf-8',errors='replace')
  for token in FORBIDDEN:
   if token in txt: raise RuntimeError(f'Author-machine dependency: {rel}: {token}')
 manifest=ROOT/'provenance/submission_github_native_v4_manifest.csv'; n=0
 with manifest.open(newline='',encoding='utf-8-sig') as f:
  for r in csv.DictReader(f):
   p=ROOT/r['path'].replace('\\','/')
   if not p.is_file() or p.stat().st_size!=int(r['bytes']) or sha(p)!=r['sha256'].lower():
    raise RuntimeError(f'Frozen-manifest mismatch: {p}')
   n+=1
 if n<12: raise RuntimeError(f'Unexpectedly short frozen manifest: {n}')
 if sha(ROOT/'source_data/figure1_assets/Figure1_assets_selected_v1.mat')!=FIG1_SHA:
  raise RuntimeError('Figure-1 frozen asset SHA mismatch')
 path=ROOT/'source_data/figure5_submission/CMDO_SystemStress_AUC_StateSummary_v1_1.csv'
 with path.open(newline='',encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
 lambdas=sorted({float(r['lambda_nominal']) for r in rows})
 observed={}
 for budget,expected in CRIT.items():
  vals=[]
  for method in METHODS:
   c=0.0
   for lam in lambdas:
    cell=[r for r in rows if r['method']==method and int(float(r['budget']))==budget and abs(float(r['lambda_nominal'])-lam)<1e-12]
    if not cell: raise RuntimeError(f'Incomplete Figure-5 grid: {method}, m={budget}, lambda={lam}')
    if max(float(r['mean_excess_mae']) for r in cell)<=0: c=lam
    else: break
   vals.append(c)
  if any(abs(a-b)>1e-12 for a,b in zip(vals,expected)): raise RuntimeError(f'Figure-5 critical Lambda mismatch: m={budget}: {vals}')
  observed[str(budget)]=vals
 cmdo={}; us={}
 for r in rows:
  lam=float(r['lambda_nominal'])
  if lam>1+1e-12: continue
  key=(float(r['true_auc']),int(float(r['budget'])),lam,int(float(r['bias_sign'])))
  if r['method']=='PC_PAIRED_HOEFFDING': cmdo[key]=float(r['gain_percent'])
  if r['method']=='PC_USTAT_MCDIARMID': us[key]=float(r['gain_percent'])
 keys=sorted(set(cmdo)&set(us)); adv=[cmdo[k]-us[k] for k in keys]
 mean=sum(adv)/len(adv); win=sum(x>0 for x in adv)/len(adv)
 if abs(mean-1.0817)>=5e-4 or abs(win-.8)>=1e-12: raise RuntimeError(f'Figure-5 paired fingerprint mismatch: {mean}, {win}')
 report={'status':'PASS','platform':sys.platform,'required_files':len(REQUIRED),'manifest_entries':n,'figure5_rows':len(rows),'critical_lambda':observed,'cmdo_minus_ustat_pp':mean,'cmdo_win_fraction':win}
 print('=== CMDO SUBMISSION PORTABILITY STATIC AUDIT: PASS ==='); print(json.dumps(report,indent=2))
 return 0
if __name__=='__main__': raise SystemExit(main())
