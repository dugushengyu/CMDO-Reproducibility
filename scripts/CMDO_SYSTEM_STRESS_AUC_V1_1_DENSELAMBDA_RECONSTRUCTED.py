#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CMDO controlled AUC stress test v1.1 dense-Lambda — faithful reconstruction.

Reconstructed from the final manuscript-locked stress design and frozen U5E
pair-complete observer formulas. This is intentionally labelled a reconstruction;
it is not claimed to be byte-identical to the lost 2026-08-31 script.
"""
from __future__ import annotations

import argparse, hashlib, json, math
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
from scipy.stats import norm

BUDGETS=np.asarray([8,16,32,64,128],dtype=int)
TRUE_AUCS=np.asarray([0.55,0.65,0.75],dtype=float)
LAMBDAS=np.asarray([0,.25,.50,.75,1,1.5,2,4],dtype=float)
N_CALIBRATION=500
N_REPLICATES=200
BASE_SEED=20260724
DELTA_TOTAL=.10
DELTA_BLOCK=DELTA_TOTAL/4
MAX_WEIGHT=.35
RISK_COEFFICIENT=8.0
SUPPORT_GATE=1.0
TRANSPORT_RISK_PROXY=0.0
Z_DELONG=float(norm.ppf(1-DELTA_BLOCK/2))
METHODS=["DIRECT","PC_PAIRED_HOEFFDING","PC_USTAT_MCDIARMID","PC_DELONG","PC_DELONG_VARGATE","PC_PLUGIN","PC_PLUGIN_VARGATE","PC_ORACLE"]
LABEL={"DIRECT":"Direct","PC_PAIRED_HOEFFDING":"CMDO","PC_USTAT_MCDIARMID":"U-stat","PC_DELONG":"DeLong","PC_DELONG_VARGATE":"DeLong + gate","PC_PLUGIN":"Plug-in","PC_PLUGIN_VARGATE":"Plug-in + gate","PC_ORACLE":"Oracle"}
OPPOSITE={"AA":"BB","BB":"AA","AB":"BA","BA":"AB"}
BLOCKS=("AA","AB","BA","BB")


def sha256_file(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def auc_and_variance(pos:np.ndarray,neg:np.ndarray)->Tuple[float,float]:
    K=(pos[:,None]>neg[None,:]).astype(float)+.5*(pos[:,None]==neg[None,:]).astype(float)
    auc=float(K.mean()); r=K.mean(1); c=K.mean(0)
    rv=float(np.var(r,ddof=1)) if len(r)>1 else 0.; cv=float(np.var(c,ddof=1)) if len(c)>1 else 0.
    return auc,max(0.,rv/len(r)+cv/len(c))


def paired_sensor(pos,neg,rng):
    h=min(len(pos),len(neg)); pos=pos[rng.permutation(len(pos))[:h]]; neg=neg[rng.permutation(len(neg))[:h]]
    v=(pos>neg).astype(float)+.5*(pos==neg)
    return float(v.mean()),float(np.var(v,ddof=1)) if h>1 else 0.,int(h)


def radius(method,n,delong_var):
    if method=='PC_PAIRED_HOEFFDING': return min(1.,math.sqrt(math.log(2/DELTA_BLOCK)/(2*n)))
    if method=='PC_USTAT_MCDIARMID': return min(1.,math.sqrt(math.log(2/DELTA_BLOCK)/n))
    if method=='PC_DELONG': return min(1.,Z_DELONG*math.sqrt(max(delong_var,1e-12)))
    raise ValueError(method)


def weight_ucb(v,u): return SUPPORT_GATE*min(MAX_WEIGHT,v/(v+u+RISK_COEFFICIENT*TRANSPORT_RISK_PROXY+1e-12))
def weight_plugin(v,b): return SUPPORT_GATE*min(MAX_WEIGHT,v/(v+.5*b+RISK_COEFFICIENT*TRANSPORT_RISK_PROXY+1e-12))
def separation(auc): return math.sqrt(2.)*float(norm.ppf(auc))


def sample_current(auc,budget,rng):
    n=budget//2; d=separation(auc)
    pos=rng.normal(d,1.,n); neg=rng.normal(0.,1.,n)
    pos=pos[rng.permutation(n)]; neg=neg[rng.permutation(n)]; h=n//2
    return pos[:h],pos[h:],neg[:h],neg[h:]


def compute_blocks(pa,pb,na,nb,rng):
    blocks={'AA':(pa,na),'AB':(pa,nb),'BA':(pb,na),'BB':(pb,nb)}; A={}; V={}; P={}
    for k in BLOCKS:
        A[k],V[k]=auc_and_variance(*blocks[k]); P[k]=paired_sensor(*blocks[k],rng)
    return A,V,P


def build(method,A,V,P,hist,true_bias_sq,full_var):
    W={}; R={}
    if method=='PC_ORACLE':
        for k in BLOCKS:
            v=V[k]; w=SUPPORT_GATE*min(MAX_WEIGHT,v/(v+true_bias_sq+RISK_COEFFICIENT*TRANSPORT_RISK_PROXY+1e-12)); W[k]=w; R[k]=(1-w)**2*v+w*w*true_bias_sq
    elif method in {'PC_PLUGIN','PC_PLUGIN_VARGATE'}:
        for k in BLOCKS:
            s=OPPOSITE[k]; bh=max(0.,(A[s]-hist)**2-V[s]); w=weight_plugin(V[k],bh); W[k]=w; R[k]=(1-w)**2*V[k]+w*w*bh
    else:
        base=method.replace('_VARGATE','')
        for k in BLOCKS:
            s=OPPOSITE[k]
            if base=='PC_PAIRED_HOEFFDING': sv,_,n=P[s]
            else: sv=A[s]; n=int(P[s][2])
            u=min(1.,abs(sv-hist)+radius(base,n,V[s]))**2; w=weight_ucb(V[k],u); W[k]=w; R[k]=(1-w)**2*V[k]+w*w*u
    pre=float(np.mean(list(R.values()))); fallback=False
    if method.endswith('_VARGATE') and pre>full_var: W={k:0. for k in W}; fallback=True
    est=float(np.mean([(1-W[k])*A[k]+W[k]*hist for k in BLOCKS]))
    return est,float(np.mean(list(W.values()))),fallback


def cal_seed(ia,ib,r): return BASE_SEED+500_000_000+ia*1_000_000+ib*10_000+r
def eval_seed(ia,ib,il,sign_code,r): return BASE_SEED+100_000_000+(ia*10_000+ib*1_000+il*10+sign_code)*1_000+r


def calibrate(auc,budget,ia,ib):
    x=[]
    for r in range(N_CALIBRATION):
        rng=np.random.default_rng(cal_seed(ia,ib,r)); n=budget//2; d=separation(auc)
        x.append(auc_and_variance(rng.normal(d,1.,n),rng.normal(0.,1.,n))[0])
    return float(np.var(x,ddof=1))


def signs(lam): return [(0,0)] if lam==0 else [(-1,0),(1,2)]


def run(outdir:Path):
    outdir.mkdir(parents=True,exist_ok=True); vref={}; cal=[]
    print('[1/3] Calibrating V_ref')
    for ia,auc0 in enumerate(TRUE_AUCS):
        for ib,b0 in enumerate(BUDGETS):
            auc=float(auc0); b=int(b0); v=calibrate(auc,b,ia,ib); vref[(auc,b)]=v; cal.append({'true_auc':auc,'budget':b,'v_ref':v}); print(f'  AUC={auc:.2f} m={b:3d} V_ref={v:.10f}')
    rows=[]
    print('[2/3] Running 225 states x 200 repeats')
    for ia,auc0 in enumerate(TRUE_AUCS):
      auc=float(auc0)
      for ib,b0 in enumerate(BUDGETS):
       b=int(b0); Vr=vref[(auc,b)]
       for il,l0 in enumerate(LAMBDAS):
        lam=float(l0)
        for sign,scode in signs(lam):
         hist=float(np.clip(auc+(0 if lam==0 else sign*math.sqrt(lam*Vr)),0,1)); true_bias_sq=(hist-auc)**2
         store={m:[] for m in METHODS}; weights={m:[] for m in METHODS}; falls={m:[] for m in METHODS}
         for r in range(N_REPLICATES):
            rng=np.random.default_rng(eval_seed(ia,ib,il,scode,r)); pa,pb,na,nb=sample_current(auc,b,rng); pos=np.r_[pa,pb]; neg=np.r_[na,nb]
            direct,full_var=auc_and_variance(pos,neg); A,V,P=compute_blocks(pa,pb,na,nb,rng)
            store['DIRECT'].append(abs(direct-auc)); weights['DIRECT'].append(0.); falls['DIRECT'].append(False)
            for m in METHODS[1:]:
                est,w,fb=build(m,A,V,P,hist,true_bias_sq,full_var); store[m].append(abs(est-auc)); weights[m].append(w); falls[m].append(fb)
         dmae=float(np.mean(store['DIRECT']))
         for m in METHODS:
            mae=float(np.mean(store[m])); rows.append({'true_auc':auc,'budget':b,'lambda_nominal':lam,'bias_sign':sign,'historical_bias':hist-auc,'transport_auc':hist,'v_ref':Vr,'method':m,'method_label':LABEL[m],'mae':mae,'direct_mae':dmae,'mean_excess_mae':mae-dmae,'gain_percent':0. if m=='DIRECT' else 100*(dmae-mae)/dmae,'mean_weight':float(np.mean(weights[m])),'fallback_rate':float(np.mean(falls[m])),'n_replicates':N_REPLICATES})
    T=pd.DataFrame(rows).sort_values(['true_auc','budget','lambda_nominal','bias_sign','method']).reset_index(drop=True)
    state=outdir/'CMDO_SystemStress_AUC_StateSummary_v1_1.csv'; T.to_csv(state,index=False,float_format='%.12g')
    pd.DataFrame(cal).to_csv(outdir/'CMDO_SystemStress_AUC_Calibration_v1_1.csv',index=False,float_format='%.12g')
    disp=['PC_PAIRED_HOEFFDING','PC_USTAT_MCDIARMID','PC_DELONG','PC_PLUGIN']; critical={}
    for b in BUDGETS:
        critical[str(int(b))]={}
        for m in disp:
            d=T[(T.method==m)&(T.budget==b)]; c=0.
            for lam in LAMBDAS:
                q=d[np.isclose(d.lambda_nominal,lam)]
                if len(q) and q.mean_excess_mae.max()<=0: c=float(lam)
                else: break
            critical[str(int(b))][m]=c
    keys=['true_auc','budget','lambda_nominal','bias_sign']; C=T[T.method==disp[0]][keys+['gain_percent']].rename(columns={'gain_percent':'c'}); U=T[T.method==disp[1]][keys+['gain_percent']].rename(columns={'gain_percent':'u'}); P=C.merge(U,on=keys); P=P[P.lambda_nominal<=1+1e-12]; adv=P.c-P.u
    manifest={'name':'CMDO_SYSTEM_STRESS_AUC_V1_1_DENSELAMBDA_RECONSTRUCTED','status':'faithful_reconstruction_not_byte_identical_original','config':{'true_aucs':TRUE_AUCS.tolist(),'budgets':BUDGETS.tolist(),'lambdas':LAMBDAS.tolist(),'n_calibration':N_CALIBRATION,'n_replicates':N_REPLICATES,'base_seed':BASE_SEED,'delta_block':DELTA_BLOCK,'max_weight':MAX_WEIGHT,'risk_coefficient':RISK_COEFFICIENT},'state_count_per_method':225,'critical_lambda_by_budget':critical,'lambda_le_1_mean_cmdo_minus_ustat_advantage_pp':float(adv.mean()),'lambda_le_1_fraction_cmdo_gt_ustat':float((adv>0).mean()),'state_summary_sha256':sha256_file(state)}
    (outdir/'CMDO_SystemStress_AUC_v1_1.json').write_text(json.dumps(manifest,indent=2,sort_keys=True),encoding='utf-8')
    print('[3/3] Complete:',state)
    for b in BUDGETS: print(' ',b,critical[str(int(b))])
    print(f' Lambda<=1 CMDO-Ustat advantage={adv.mean():.4f} pp; CMDO higher={100*(adv>0).mean():.2f}%')


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--outdir',default=''); a=ap.parse_args(); here=Path(__file__).resolve().parent; out=Path(a.outdir).expanduser().resolve() if a.outdir else here.parent/'source_data'/'figure5_stress_reconstructed'; run(out)
if __name__=='__main__': main()
