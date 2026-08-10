from __future__ import annotations

import os, sys, json, math, time, shutil, tarfile, zipfile, hashlib, random, warnings
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

STAGE = 'StageU2'
VERSION = 'v0.1'
SEED = 20260724
RNG = np.random.default_rng(SEED)
BUDGETS = np.array([8, 16, 32, 64, 128], dtype=int)
OBS_ALPHA_DIRECT = 0.7164007705061357
OBS_ALPHA_FUSION = 0.5240471362144276
PARENT_FINAL_SHA = 'e18602ed16b242cfe5a220539ef46c525ca3c2f2046c16476afbaeb2cf8f5556'
PARENT_ZIP_SHA = '1e6368f9c5b73dfee953020f802cc4f7dd74df5a383326c73225cef65fa4e5fe'
PARENT_ZIP_NAME = 'StageU0-U1_Canonical_Records_v0.1.zip'
RUN_EXTERNAL = os.environ.get('CMDO_U2_EXTERNAL', '1') != '0'
N_NULL_REP = int(os.environ.get('CMDO_U2_NULL_REP', '300'))
N_WITNESS_REP = int(os.environ.get('CMDO_U2_WITNESS_REP', '200'))
TRAIN_EPOCHS = int(os.environ.get('CMDO_U2_TRAIN_EPOCHS', '12'))

DRIVE_ROOT = Path('/content/drive/MyDrive') if Path('/content/drive/MyDrive').exists() else Path('/tmp/cmdo_fake_drive')
PROJECT_ROOT = DRIVE_ROOT / 'Cross-Modal_Diagnostic_Observability'
OUTPUT_ROOT = PROJECT_ROOT / '06_Data_Records' / 'Cross_Modal' / 'StageU2_Mechanism_Multimetric_Label_Efficiency_External_NonBiomedical_v0.1'
DATA_ROOT = PROJECT_ROOT / '08_External_Data' / 'NonBiomedical' / 'CIFAR_External_v0.1'
CACHE_ROOT = Path('/content/cmdo_u2_cache') if Path('/content').exists() else Path('/tmp/cmdo_u2_cache')

SUBDIRS = {
    'integrity': '00_Integrity_And_Protocol',
    'mechanism': '01_Mechanism_Kill_Tests',
    'medical': '02_Medical_Label_Efficiency',
    'acquisition': '03_External_CIFAR_Acquisition',
    'external_scaling': '04_External_Multimetric_Scaling',
    'external_fusion': '05_External_Transport_And_Fusion',
    'sequential': '06_Sequential_Budget_Prediction',
    'reserve': '07_Reserve_Preregistration_Only',
    'figures': '08_Figures',
    'decision': '09_Decision_And_Manuscript',
}

for d in [OUTPUT_ROOT, DATA_ROOT, CACHE_ROOT]:
    d.mkdir(parents=True, exist_ok=True)
for d in SUBDIRS.values():
    (OUTPUT_ROOT / d).mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def write_json(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False), encoding='utf-8')


def find_parent_zip() -> Path:
    candidates = []
    search_roots = [PROJECT_ROOT / '06_Data_Records' / 'Cross_Modal', DRIVE_ROOT]
    for root in search_roots:
        if root.exists():
            candidates.extend(root.rglob(PARENT_ZIP_NAME))
    candidates = list(dict.fromkeys(candidates))
    exact = [p for p in candidates if sha256_file(p) == PARENT_ZIP_SHA]
    if not exact:
        # local dry-run fallback
        local = Path('/mnt/data') / PARENT_ZIP_NAME
        if local.exists() and sha256_file(local) == PARENT_ZIP_SHA:
            exact = [local]
    if len(exact) != 1:
        raise FileNotFoundError(f'Expected exactly one parent canonical ZIP with SHA {PARENT_ZIP_SHA}, found {len(exact)}')
    return exact[0]


def extract_parent(zip_path: Path) -> Path:
    target = CACHE_ROOT / 'parent_u01'
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(target)
    manifest = target / 'StageU0-U1_Durable_Commit_Manifest_v0.1.json'
    if not manifest.exists():
        raise RuntimeError('Parent durable manifest missing')
    m = json.loads(manifest.read_text())
    if m.get('final_record_sha256') != PARENT_FINAL_SHA:
        raise RuntimeError('Parent final record SHA mismatch')
    for row in m['files']:
        p = target / row['relative_path']
        if not p.exists() or sha256_file(p) != row['sha256']:
            raise RuntimeError(f'Parent internal integrity failed: {row["relative_path"]}')
    return target


def fit_fixed_effect_alpha(df: pd.DataFrame, value_col: str, target_col: str = 'target', budget_col: str = 'budget') -> Dict:
    q=df[[target_col,budget_col,value_col]].dropna().copy()
    q['_x']=np.log(q[budget_col].astype(float)/float(BUDGETS[0]))
    q['_y']=np.log(np.clip(q[value_col].astype(float),1e-12,None))
    gx=q.groupby(target_col)['_x'].transform('mean'); gy=q.groupby(target_col)['_y'].transform('mean')
    xc=q['_x'].values-gx.values; yc=q['_y'].values-gy.values
    den=float(np.sum(xc*xc)); beta=float(np.sum(xc*yc)/den) if den>0 else np.nan
    pred=gy.values+beta*xc
    ss_res=float(np.sum((q['_y'].values-pred)**2)); ss_tot=float(np.sum((q['_y'].values-q['_y'].mean())**2))
    return {'alpha':-beta,'within_target_r2':1.0-ss_res/ss_tot if ss_tot>0 else np.nan,'pred_log':pred,'resid_log':q['_y'].values-pred}

def target_bootstrap_alpha(df: pd.DataFrame, value_col: str, draws: int = 1000, seed: int = SEED) -> np.ndarray:
    q=df[['target','budget',value_col]].dropna().copy()
    q['_x']=np.log(q['budget'].astype(float)/float(BUDGETS[0])); q['_y']=np.log(np.clip(q[value_col].astype(float),1e-12,None))
    stats=[]
    for _,g in q.groupby('target'):
        xc=g['_x'].values-g['_x'].mean(); yc=g['_y'].values-g['_y'].mean()
        stats.append((float(np.sum(xc*yc)),float(np.sum(xc*xc))))
    stats=np.asarray(stats); rng=np.random.default_rng(seed); n=len(stats); out=np.empty(draws)
    for i in range(draws):
        idx=rng.integers(0,n,size=n); num=stats[idx,0].sum(); den=stats[idx,1].sum(); out[i]=-num/den
    return out

def auc_pairwise(pos: np.ndarray, neg: np.ndarray) -> np.ndarray:
    # pos: reps x npos, neg: reps x nneg
    return ((pos[:, :, None] > neg[:, None, :]).mean(axis=(1, 2)) +
            0.5 * (pos[:, :, None] == neg[:, None, :]).mean(axis=(1, 2)))


def draw_scores(rng, family: str, n: Tuple[int, int], delta: float) -> Tuple[np.ndarray, np.ndarray]:
    reps, count = n
    if family == 'gaussian':
        neg = rng.normal(0, 1, size=(reps, count)); pos = rng.normal(delta, 1, size=(reps, count))
    elif family == 'student_t3':
        scale = 1 / math.sqrt(3)
        neg = rng.standard_t(3, size=(reps, count)) * scale
        pos = rng.standard_t(3, size=(reps, count)) * scale + delta
    elif family == 'heteroscedastic':
        neg = rng.normal(0, 0.7, size=(reps, count)); pos = rng.normal(delta, 1.5, size=(reps, count))
    elif family == 'mixture':
        mixn = rng.integers(0, 2, size=(reps, count)); mixp = rng.integers(0, 2, size=(reps, count))
        neg = rng.normal(np.where(mixn == 0, -0.55, 0.55), 0.75)
        pos = rng.normal(np.where(mixp == 0, -0.55, 0.55) + delta, 0.75)
    else:
        raise ValueError(family)
    return pos, neg


def calibrate_delta(family: str, desired_auc: float, rng) -> float:
    from scipy.stats import norm
    z=float(norm.ppf(desired_auc))
    if family=='gaussian': return z*math.sqrt(2.0)
    if family=='heteroscedastic': return z*math.sqrt(0.7**2+1.5**2)
    if family=='student_t3': return z*math.sqrt(2.0)*1.15
    if family=='mixture': return z*math.sqrt(2.0)*1.25
    return z*math.sqrt(2.0)

def mechanism_null_simulation(panel: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    med_prev = panel[panel.budget == 32].groupby('target').witness_prevalence.median()
    prevs = np.clip(med_prev.values, 0.15, 0.85)
    n_targets = len(prevs)
    desired_aucs = np.linspace(0.62, 0.94, n_targets)
    families = ['gaussian', 'student_t3', 'heteroscedastic', 'mixture']
    protocols = ['balanced_independent', 'balanced_nested', 'natural_independent', 'natural_nested']
    rows = []
    target_rows = []
    master_rng = np.random.default_rng(SEED + 101)
    for family in families:
        deltas = [calibrate_delta(family, a, np.random.default_rng(SEED + i + 1000 * families.index(family))) for i, a in enumerate(desired_aucs)]
        for protocol in protocols:
            nested = protocol.endswith('nested')
            balanced = protocol.startswith('balanced')
            for ti in range(n_targets):
                p = float(prevs[ti]); delta = deltas[ti]
                if nested:
                    # generate a large pool per replicate, then use prefixes
                    maxn = int(BUDGETS[-1])
                    if balanced:
                        maxpos = maxn // 2; maxneg = maxn - maxpos
                        pos_pool, _ = draw_scores(master_rng, family, (N_NULL_REP, maxpos), delta)
                        _, neg_pool = draw_scores(master_rng, family, (N_NULL_REP, maxneg), delta)
                        # truth from independent large draw
                        tpos, tneg = draw_scores(master_rng, family, (10000, 1), delta)
                        true_auc = float(np.mean(tpos[:, 0] > tneg[:, 0]) + 0.5*np.mean(tpos[:, 0] == tneg[:, 0]))
                        for b in BUDGETS:
                            np_ = b // 2; nn_ = b - np_
                            est = auc_pairwise(pos_pool[:, :np_], neg_pool[:, :nn_])
                            mae = float(np.median(np.abs(est - true_auc)))
                            target_rows.append([family, protocol, f'T{ti:02d}', int(b), mae, true_auc, p])
                    else:
                        # natural prevalence: sample labels and scores as nested sequences
                        labels = master_rng.random((N_NULL_REP, maxn)) < p
                        # draw separate positive/negative score matrices then select by labels
                        pos_all, _ = draw_scores(master_rng, family, (N_NULL_REP, maxn), delta)
                        _, neg_all = draw_scores(master_rng, family, (N_NULL_REP, maxn), delta)
                        scores = np.where(labels, pos_all, neg_all)
                        tpos, tneg = draw_scores(master_rng, family, (10000, 1), delta)
                        true_auc = float(np.mean(tpos[:, 0] > tneg[:, 0]) + 0.5*np.mean(tpos[:, 0] == tneg[:, 0]))
                        for b in BUDGETS:
                            vals = []
                            for r in range(N_NULL_REP):
                                yy = labels[r, :b]; ss = scores[r, :b]
                                if yy.sum() == 0 or yy.sum() == b:
                                    continue
                                vals.append(float(auc_pairwise(ss[yy][None, :], ss[~yy][None, :])[0]))
                            mae = float(np.median(np.abs(np.asarray(vals) - true_auc))) if vals else np.nan
                            target_rows.append([family, protocol, f'T{ti:02d}', int(b), mae, true_auc, p])
                else:
                    # independent budget samples
                    tpos, tneg = draw_scores(master_rng, family, (10000, 1), delta)
                    true_auc = float(np.mean(tpos[:, 0] > tneg[:, 0]) + 0.5*np.mean(tpos[:, 0] == tneg[:, 0]))
                    for b in BUDGETS:
                        if balanced:
                            np_ = b // 2; nn_ = b - np_
                            pos, _ = draw_scores(master_rng, family, (N_NULL_REP, np_), delta)
                            _, neg = draw_scores(master_rng, family, (N_NULL_REP, nn_), delta)
                            est = auc_pairwise(pos, neg)
                        else:
                            vals = []
                            for _ in range(N_NULL_REP):
                                yy = master_rng.random(b) < p
                                if yy.sum() == 0 or yy.sum() == b:
                                    continue
                                pos, _ = draw_scores(master_rng, family, (1, int(yy.sum())), delta)
                                _, neg = draw_scores(master_rng, family, (1, int((~yy).sum())), delta)
                                vals.append(float(auc_pairwise(pos, neg)[0]))
                            est = np.asarray(vals)
                        mae = float(np.median(np.abs(est - true_auc)))
                        target_rows.append([family, protocol, f'T{ti:02d}', int(b), mae, true_auc, p])
            cell = pd.DataFrame([r for r in target_rows if r[0] == family and r[1] == protocol], columns=['family','protocol','target','budget','mae','true_auc','prevalence'])
            fit = fit_fixed_effect_alpha(cell.dropna(), 'mae')
            boot = target_bootstrap_alpha(cell.dropna(), 'mae', draws=250, seed=SEED + 17*families.index(family) + protocols.index(protocol))
            rows.append({
                'family': family, 'protocol': protocol, 'targets': n_targets,
                'alpha': fit['alpha'], 'within_target_r2': fit['within_target_r2'],
                'bootstrap_q025': float(np.quantile(boot, .025)),
                'bootstrap_q50': float(np.quantile(boot, .5)),
                'bootstrap_q975': float(np.quantile(boot, .975)),
                'observed_medical_alpha': OBS_ALPHA_DIRECT,
                'observed_above_cell_q975': bool(OBS_ALPHA_DIRECT > np.quantile(boot, .975)),
            })
    summary = pd.DataFrame(rows)
    ledger = pd.DataFrame(target_rows, columns=['family','protocol','target','budget','mae','true_auc','prevalence'])
    q975_all = float(summary.bootstrap_q975.max())
    mechanism = {
        'observed_medical_alpha': OBS_ALPHA_DIRECT,
        'maximum_null_cell_q975': q975_all,
        'observed_above_all_null_q975': bool(OBS_ALPHA_DIRECT > q975_all),
        'null_cells_reproducing_observed': int((summary.bootstrap_q975 >= OBS_ALPHA_DIRECT).sum()),
        'null_cells': int(len(summary)),
        'interpretation': 'AUC finite-sample null rejected' if OBS_ALPHA_DIRECT > q975_all else 'AUC finite-sample null not fully rejected',
    }
    return summary, ledger, mechanism


def medical_label_efficiency(panel: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    d = panel.copy()
    d['direct_to_fusion_leverage'] = d['direct_mae'] / d['fusion_mae']
    d['equivalent_direct_budget'] = d['budget'] * np.power(np.clip(d['direct_to_fusion_leverage'], 1e-8, None), 1.0 / OBS_ALPHA_DIRECT)
    d['labels_saved'] = d['equivalent_direct_budget'] - d['budget']
    by_budget = d.groupby(['role','budget']).agg(
        targets=('target','nunique'),
        median_leverage=('direct_to_fusion_leverage','median'),
        mean_leverage=('direct_to_fusion_leverage','mean'),
        median_equivalent_direct_budget=('equivalent_direct_budget','median'),
        median_labels_saved=('labels_saved','median'),
        positive_leverage_rate=('direct_to_fusion_leverage', lambda x: float(np.mean(x > 1))),
    ).reset_index()
    # Observed threshold crossing savings
    rows = []
    for role, q in d.groupby('role'):
        for target, t in q.groupby('target'):
            t = t.sort_values('budget')
            base = float(t.loc[t.budget == t.budget.min(), 'direct_mae'].iloc[0])
            for frac in [0.75, 0.50, 0.35, 0.25]:
                threshold = base * frac
                bd = t.loc[t.direct_mae <= threshold, 'budget']
                bf = t.loc[t.fusion_mae <= threshold, 'budget']
                rows.append({
                    'role': role, 'target': target, 'relative_threshold': frac,
                    'absolute_mae_threshold': threshold,
                    'direct_first_budget': int(bd.min()) if len(bd) else np.nan,
                    'fusion_first_budget': int(bf.min()) if len(bf) else np.nan,
                    'observed_budget_saved': (float(bd.min()) - float(bf.min())) if len(bd) and len(bf) else np.nan,
                })
    crossings = pd.DataFrame(rows)
    # sequential prediction: use budget 8 anchor and leave-one-target-out alpha
    pred_rows = []
    dev = d[d.role == 'DEVELOPMENT']
    for target in dev.target.unique():
        train = dev[dev.target != target]
        alpha = fit_fixed_effect_alpha(train, 'direct_mae')['alpha']
        test = dev[dev.target == target].sort_values('budget')
        a8 = float(test[test.budget == 8].direct_mae.iloc[0])
        for _, r in test.iterrows():
            pred_law = a8 * (r.budget/8.0)**(-alpha)
            pred_root = a8 * (r.budget/8.0)**(-0.5)
            pred_rows.append({
                'target': target, 'budget': int(r.budget), 'actual_direct_mae': r.direct_mae,
                'alpha_train_loto': alpha, 'law_prediction': pred_law, 'rootn_prediction': pred_root,
                'law_abs_error': abs(pred_law-r.direct_mae), 'rootn_abs_error': abs(pred_root-r.direct_mae),
            })
    seq = pd.DataFrame(pred_rows)
    return d, by_budget, crossings, seq


def safe_import_external_packages():
    global torch, nn, F, DataLoader, Dataset, Subset, transforms, CIFAR10
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import DataLoader, Dataset, Subset
    from torchvision import transforms
    from torchvision.datasets import CIFAR10
    return torch


def download_url(url: str, path: Path, expected_min_bytes: int = 1, chunk: int = 1 << 20):
    import requests
    if path.exists() and path.stat().st_size >= expected_min_bytes:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.part')
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(tmp, 'wb') as f:
            for b in r.iter_content(chunk_size=chunk):
                if b:
                    f.write(b)
    if tmp.stat().st_size < expected_min_bytes:
        raise RuntimeError(f'Download too small: {url}')
    tmp.replace(path)


def _tfds_arrays(config_name: str, data_dir: Path) -> Tuple[np.ndarray, np.ndarray]:
    import tensorflow_datasets as tfds
    ds = tfds.load(config_name, split='test', as_supervised=True, batch_size=-1, data_dir=str(data_dir), shuffle_files=False)
    images, labels = tfds.as_numpy(ds)
    return np.asarray(images), np.asarray(labels)

def acquire_cifar_external() -> Dict:
    # CIFAR-10 via torchvision; CIFAR-10.1 and CIFAR-10-C use official TFDS builders with persistent Drive cache.
    safe_import_external_packages()
    torchvision_root = DATA_ROOT / 'torchvision'
    _ = CIFAR10(root=str(torchvision_root), train=True, download=True)
    _ = CIFAR10(root=str(torchvision_root), train=False, download=True)
    tfds_dir = DATA_ROOT / 'tensorflow_datasets'
    c101_dir = DATA_ROOT / 'CIFAR-10.1'; c101_dir.mkdir(parents=True, exist_ok=True)
    c101_data = c101_dir / 'cifar10.1_v6_data.npy'; c101_labels = c101_dir / 'cifar10.1_v6_labels.npy'
    if not (c101_data.exists() and c101_labels.exists()):
        try:
            download_url('https://raw.githubusercontent.com/modestyachts/CIFAR-10.1/master/datasets/cifar10.1_v6_data.npy', c101_data, 5_000_000)
            download_url('https://raw.githubusercontent.com/modestyachts/CIFAR-10.1/master/datasets/cifar10.1_v6_labels.npy', c101_labels, 5_000)
        except Exception:
            x,y=_tfds_arrays('cifar10_1',tfds_dir); np.save(c101_data,x); np.save(c101_labels,y)
    meta = {
        'cifar10_root': str(torchvision_root),
        'cifar10_1_data': str(c101_data),
        'cifar10_1_labels': str(c101_labels),
        'cifar10_c_mode': 'tfds',
        'cifar10_c_tfds_data_dir': str(tfds_dir),
        'manual_download_required': False,
        'manual_fallback': {
            'CIFAR-10.1': 'https://github.com/modestyachts/CIFAR-10.1/tree/master/datasets',
            'CIFAR-10-C': 'https://zenodo.org/records/2535967',
        },
    }
    return meta


class BinaryCIFARDataset:
    def __init__(self, base, transform=None):
        self.base = base; self.transform = transform
    def __len__(self): return len(self.base)
    def __getitem__(self, idx):
        img, y = self.base[idx]
        yb = 1.0 if int(y) in {2,3,4,5,6,7} else 0.0
        if self.transform: img = self.transform(img)
        return img, np.float32(yb)


class NumpyCIFARDataset:
    def __init__(self, images, labels, transform=None):
        from PIL import Image
        self.images = images; self.labels = labels; self.transform = transform; self.Image = Image
    def __len__(self): return len(self.labels)
    def __getitem__(self, idx):
        img = self.Image.fromarray(self.images[idx].astype(np.uint8))
        y = 1.0 if int(self.labels[idx]) in {2,3,4,5,6,7} else 0.0
        if self.transform: img = self.transform(img)
        return img, np.float32(y)


def make_model():
    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.features = nn.Sequential(
                nn.Conv2d(3,64,3,padding=1), nn.BatchNorm2d(64), nn.ReLU(),
                nn.Conv2d(64,64,3,padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
                nn.Conv2d(64,128,3,padding=1), nn.BatchNorm2d(128), nn.ReLU(),
                nn.Conv2d(128,128,3,padding=1), nn.BatchNorm2d(128), nn.ReLU(), nn.MaxPool2d(2),
                nn.Conv2d(128,256,3,padding=1), nn.BatchNorm2d(256), nn.ReLU(),
                nn.AdaptiveAvgPool2d(1),
            )
            self.fc = nn.Linear(256,1)
        def forward(self,x,return_features=False):
            z=self.features(x).flatten(1); logit=self.fc(z).squeeze(1)
            return (logit,z) if return_features else logit
    return Net()


def infer_dataset(model, dataset, batch_size=512, max_feature_samples=3000):
    device = next(model.parameters()).device
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=2, pin_memory=True)
    scores=[]; labels=[]; feats=[]; nfeat=0
    model.eval()
    with torch.no_grad():
        for x,y in loader:
            x=x.to(device, non_blocking=True)
            logit,z=model(x,return_features=True)
            s=torch.sigmoid(logit).cpu().numpy()
            scores.append(s); labels.append(y.numpy())
            if nfeat < max_feature_samples:
                take=min(len(z), max_feature_samples-nfeat)
                feats.append(z[:take].cpu().numpy()); nfeat += take
    return np.concatenate(scores), np.concatenate(labels).astype(int), np.concatenate(feats)


def binary_metrics(y, s, threshold):
    from sklearn.metrics import roc_auc_score, average_precision_score, balanced_accuracy_score, brier_score_loss, log_loss
    pred=(s>=threshold).astype(int)
    return {
        'auc': float(roc_auc_score(y,s)),
        'auprc': float(average_precision_score(y,s)),
        'balanced_accuracy': float(balanced_accuracy_score(y,pred)),
        'brier': float(brier_score_loss(y,s)),
        'log_loss': float(log_loss(y, np.column_stack([1-s,s]), labels=[0,1])),
    }


def choose_threshold(y,s):
    from sklearn.metrics import balanced_accuracy_score
    grid=np.quantile(s,np.linspace(.05,.95,181))
    vals=[balanced_accuracy_score(y,(s>=t).astype(int)) for t in grid]
    return float(grid[int(np.argmax(vals))])


def train_cifar_model(meta: Dict):
    safe_import_external_packages()
    from sklearn.model_selection import train_test_split
    torch.manual_seed(SEED); np.random.seed(SEED); random.seed(SEED)
    normalize=transforms.Normalize((0.4914,0.4822,0.4465),(0.2470,0.2435,0.2616))
    train_tf=transforms.Compose([transforms.RandomCrop(32,padding=4),transforms.RandomHorizontalFlip(),transforms.ToTensor(),normalize])
    eval_tf=transforms.Compose([transforms.ToTensor(),normalize])
    base=CIFAR10(root=meta['cifar10_root'],train=True,download=False)
    idx=np.arange(len(base)); tr,va=train_test_split(idx,test_size=5000,random_state=SEED,stratify=np.array(base.targets))
    train_ds=BinaryCIFARDataset(Subset(base,tr),train_tf)
    val_ds=BinaryCIFARDataset(Subset(base,va),eval_tf)
    model=make_model(); device=torch.device('cuda' if torch.cuda.is_available() else 'cpu'); model.to(device)
    loader=DataLoader(train_ds,batch_size=256,shuffle=True,num_workers=2,pin_memory=True)
    opt=torch.optim.AdamW(model.parameters(),lr=2e-3,weight_decay=1e-4)
    sched=torch.optim.lr_scheduler.CosineAnnealingLR(opt,T_max=TRAIN_EPOCHS)
    hist=[]
    for epoch in range(TRAIN_EPOCHS):
        model.train(); losses=[]
        for x,y in loader:
            x=x.to(device,non_blocking=True); y=y.to(device,non_blocking=True)
            opt.zero_grad(set_to_none=True); logit=model(x); loss=F.binary_cross_entropy_with_logits(logit,y)
            loss.backward(); opt.step(); losses.append(float(loss.detach().cpu()))
        sched.step(); hist.append({'epoch':epoch+1,'loss':float(np.mean(losses))})
    vs,vy,vf=infer_dataset(model,val_ds)
    threshold=choose_threshold(vy,vs)
    val_metrics=binary_metrics(vy,vs,threshold)
    return model, eval_tf, threshold, pd.DataFrame(hist), val_metrics, (vs,vy,vf)


def external_environments(model, eval_tf, threshold, meta):
    clean_base=CIFAR10(root=meta['cifar10_root'],train=False,download=False)
    envs={}
    clean_ds=BinaryCIFARDataset(clean_base,eval_tf)
    envs['CIFAR10_CLEAN']={'family':'clean','dataset':clean_ds}
    x101=np.load(meta['cifar10_1_data']); y101=np.load(meta['cifar10_1_labels'])
    envs['CIFAR10_1_V6']={'family':'resampled_test','dataset':NumpyCIFARDataset(x101,y101,eval_tf)}
    corruptions=['gaussian_noise','shot_noise','impulse_noise','gaussian_blur','motion_blur','fog','frost','brightness','contrast','jpeg_compression','pixelate','zoom_blur']
    severities=[1,3,5]
    tfds_dir=Path(meta['cifar10_c_tfds_data_dir']); cache_dir=DATA_ROOT/'CIFAR-10-C_Selected'; cache_dir.mkdir(parents=True,exist_ok=True)
    for corr in corruptions:
        for sev in severities:
            xp=cache_dir/f'{corr}_{sev}_images.npy'; yp=cache_dir/f'{corr}_{sev}_labels.npy'
            if not (xp.exists() and yp.exists()):
                x,y=_tfds_arrays(f'cifar10_corrupted/{corr}_{sev}',tfds_dir); np.save(xp,x); np.save(yp,y)
            x=np.load(xp,mmap_mode='r'); y=np.load(yp,mmap_mode='r')
            envs[f'{corr.upper()}_S{sev}']={'family':corr,'dataset':NumpyCIFARDataset(x,y,eval_tf)}
    rows=[]; scores_dict={}; labels_dict={}; feature_rows=[]
    for name,info in envs.items():
        s,y,z=infer_dataset(model,info['dataset'])
        m=binary_metrics(y,s,threshold)
        rows.append({'target':name,'family':info['family'],'n':len(y),'prevalence':float(y.mean()),**m})
        scores_dict[name]=s; labels_dict[name]=y
        ent=-(s*np.log(np.clip(s,1e-8,1))+(1-s)*np.log(np.clip(1-s,1e-8,1)))
        feature_rows.append({'target':name,'family':info['family'],'feature_mean':z.mean(0),'feature_var':z.var(0)+1e-8,
                             'mean_score':float(s.mean()),'mean_entropy':float(ent.mean()),'mean_confidence':float(np.maximum(s,1-s).mean())})
    metrics=pd.DataFrame(rows)
    return metrics,scores_dict,labels_dict,feature_rows


def build_transport_predictions(metrics, feature_rows, source_feature_tuple):
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import Ridge
    source_scores, source_labels, source_z = source_feature_tuple
    src_mean=source_z.mean(0); src_var=source_z.var(0)+1e-8
    src_ent=-(source_scores*np.log(np.clip(source_scores,1e-8,1))+(1-source_scores)*np.log(np.clip(1-source_scores,1e-8,1)))
    src_stats={'mean_score':source_scores.mean(),'mean_entropy':src_ent.mean(),'mean_confidence':np.maximum(source_scores,1-source_scores).mean()}
    rows=[]
    for r in feature_rows:
        mean=r['feature_mean']; var=r['feature_var']
        rows.append({
            'target':r['target'],'family':r['family'],
            'mean_shift':float(np.sqrt(np.mean(((mean-src_mean)/np.sqrt(src_var))**2))),
            'variance_log_ratio':float(np.mean(np.abs(np.log(var/src_var)))),
            'score_shift':float(abs(r['mean_score']-src_stats['mean_score'])),
            'entropy_shift':float(abs(r['mean_entropy']-src_stats['mean_entropy'])),
            'confidence_shift':float(abs(r['mean_confidence']-src_stats['mean_confidence'])),
        })
    Xdf=pd.DataFrame(rows).merge(metrics[['target','family','auc']],on=['target','family'])
    feat_cols=['mean_shift','variance_log_ratio','score_shift','entropy_shift','confidence_shift']
    preds=[]
    for _,r in Xdf.iterrows():
        if r['family']=='clean':
            train=Xdf[Xdf.family!='clean']
        else:
            train=Xdf[(Xdf.family!=r['family']) & (Xdf.family!='clean')]
        if len(train)<6:
            train=Xdf[Xdf.target!=r.target]
        scaler=StandardScaler().fit(train[feat_cols])
        model=Ridge(alpha=1.0).fit(scaler.transform(train[feat_cols]),train['auc'])
        pred=float(model.predict(scaler.transform(pd.DataFrame([r[feat_cols].values],columns=feat_cols)))[0])
        preds.append({'target':r.target,'family':r.family,'true_auc':r.auc,'transport_auc':float(np.clip(pred,0.5,1.0)),
                      **{c:float(r[c]) for c in feat_cols},'train_environments':len(train)})
    return pd.DataFrame(preds)


def empirical_metric(y,s,metric,threshold,idx):
    from sklearn.metrics import roc_auc_score, average_precision_score, balanced_accuracy_score, brier_score_loss, log_loss
    yy=y[idx]; ss=s[idx]
    if metric=='auc': return float(roc_auc_score(yy,ss))
    if metric=='auprc': return float(average_precision_score(yy,ss))
    if metric=='balanced_accuracy': return float(balanced_accuracy_score(yy,(ss>=threshold).astype(int)))
    if metric=='brier': return float(brier_score_loss(yy,ss))
    if metric=='log_loss': return float(log_loss(yy,np.column_stack([1-ss,ss]),labels=[0,1]))
    raise ValueError(metric)


def witness_scaling(metrics, scores_dict, labels_dict, threshold, transport_df):
    rng=np.random.default_rng(SEED+303)
    rows=[]; rep_rows=[]
    metric_names=['auc','auprc','balanced_accuracy','brier','log_loss']
    transport_map=transport_df.set_index('target').transport_auc.to_dict()
    for _,mr in metrics.iterrows():
        name=mr.target; family=mr.family; y=labels_dict[name]; s=scores_dict[name]
        pos=np.flatnonzero(y==1); neg=np.flatnonzero(y==0); all_idx=np.arange(len(y))
        for b in BUDGETS:
            vals={m:[] for m in metric_names}; fusion_vals=[]
            for rep in range(N_WITNESS_REP):
                # AUC uses class-balanced witness; other metrics use natural prevalence witness.
                npos=b//2; nneg=b-npos
                idx_auc=np.concatenate([rng.choice(pos,npos,replace=False),rng.choice(neg,nneg,replace=False)])
                idx_nat=rng.choice(all_idx,b,replace=False)
                auc_est=empirical_metric(y,s,'auc',threshold,idx_auc)
                vals['auc'].append(auc_est)
                for m in metric_names[1:]: vals[m].append(empirical_metric(y,s,m,threshold,idx_nat))
                fusion_vals.append(0.6*transport_map[name]+0.4*auc_est)
                rep_rows.append({'target':name,'family':family,'budget':int(b),'replicate':rep,
                                 'auc_direct':auc_est,'auc_fusion':fusion_vals[-1]})
            for m in metric_names:
                arr=np.asarray(vals[m]); truth=float(mr[m])
                rows.append({'target':name,'family':family,'metric':m,'budget':int(b),'mae':float(np.median(np.abs(arr-truth))),
                             'mean_ae':float(np.mean(np.abs(arr-truth))),'truth':truth,'replicates':len(arr)})
            farr=np.asarray(fusion_vals); truth=float(mr.auc)
            rows.append({'target':name,'family':family,'metric':'auc_fusion','budget':int(b),'mae':float(np.median(np.abs(farr-truth))),
                         'mean_ae':float(np.mean(np.abs(farr-truth))),'truth':truth,'replicates':len(farr)})
    return pd.DataFrame(rows),pd.DataFrame(rep_rows)


def scaling_and_holdout(witness_df):
    summaries=[]; pred_rows=[]; boot_rows=[]
    for metric,q in witness_df.groupby('metric'):
        fit=fit_fixed_effect_alpha(q,'mae')
        boot=target_bootstrap_alpha(q,'mae',draws=600,seed=SEED+hash(metric)%10000)
        summaries.append({'metric':metric,'targets':q.target.nunique(),'families':q.family.nunique(),'alpha':fit['alpha'],
                          'within_target_r2':fit['within_target_r2'],'bootstrap_q025':float(np.quantile(boot,.025)),
                          'bootstrap_q50':float(np.quantile(boot,.5)),'bootstrap_q975':float(np.quantile(boot,.975))})
        for i,a in enumerate(boot): boot_rows.append({'metric':metric,'draw':i,'alpha':a})
        for family in q.family.unique():
            train=q[q.family!=family]; test=q[q.family==family]
            if train.target.nunique()<3: continue
            alpha=fit_fixed_effect_alpha(train,'mae')['alpha']
            for target,t in test.groupby('target'):
                t=t.sort_values('budget'); a8=float(t[t.budget==8].mae.iloc[0])
                for _,r in t.iterrows():
                    pl=a8*(r.budget/8.0)**(-alpha); pr=a8*(r.budget/8.0)**(-0.5)
                    pred_rows.append({'metric':metric,'holdout_family':family,'target':target,'budget':int(r.budget),
                                      'actual_mae':r.mae,'alpha_train':alpha,'law_prediction':pl,'rootn_prediction':pr,
                                      'law_abs_error':abs(pl-r.mae),'rootn_abs_error':abs(pr-r.mae)})
    return pd.DataFrame(summaries),pd.DataFrame(pred_rows),pd.DataFrame(boot_rows)


def sequential_budget_external(witness_df):
    rows=[]
    for metric,q in witness_df.groupby('metric'):
        for target,t in q.groupby('target'):
            t=t.sort_values('budget')
            train=q[q.target!=target]
            alpha=fit_fixed_effect_alpha(train,'mae')['alpha']
            anchor=float(t[t.budget==8].mae.iloc[0])
            for frac in [.75,.5,.35,.25]:
                threshold=anchor*frac
                predicted=8*(anchor/threshold)**(1/max(alpha,1e-6))
                observed=t.loc[t.mae<=threshold,'budget']
                rows.append({'metric':metric,'target':target,'relative_threshold':frac,'threshold':threshold,
                             'alpha_loto':alpha,'predicted_budget':float(predicted),
                             'observed_first_budget':float(observed.min()) if len(observed) else np.nan,
                             'prediction_abs_log2_error':abs(math.log2(predicted/float(observed.min()))) if len(observed) else np.nan})
    return pd.DataFrame(rows)


def make_figures(null_summary, med_budget, ext_summary=None, ext_witness=None, transport=None):
    import matplotlib.pyplot as plt
    # Mechanism null comparison
    fig,ax=plt.subplots(figsize=(11,5))
    labels=(null_summary.family+'\n'+null_summary.protocol.str.replace('_',' ')).tolist()
    x=np.arange(len(labels))
    ax.errorbar(x,null_summary.alpha,yerr=[null_summary.alpha-null_summary.bootstrap_q025,null_summary.bootstrap_q975-null_summary.alpha],fmt='o',capsize=3)
    ax.axhline(OBS_ALPHA_DIRECT,linestyle='--',label='Observed medical direct exponent')
    ax.axhline(.5,linestyle=':',label='root-n')
    ax.set_xticks(x); ax.set_xticklabels(labels,rotation=75,ha='right',fontsize=7); ax.set_ylabel('Evidence-scaling exponent'); ax.legend(); fig.tight_layout()
    fig.savefig(OUTPUT_ROOT/SUBDIRS['figures']/'StageU2_Mechanism_Null_Exponent_Comparison_v0.1.png',dpi=180); plt.close(fig)
    # medical leverage
    fig,ax=plt.subplots(figsize=(8,5))
    for role,q in med_budget.groupby('role'):
        ax.plot(q.budget,q.median_leverage,marker='o',label=role)
    ax.axhline(1,linestyle='--'); ax.set_xscale('log',base=2); ax.set_xlabel('Target-label budget'); ax.set_ylabel('Median direct/fusion MAE ratio'); ax.legend(); fig.tight_layout()
    fig.savefig(OUTPUT_ROOT/SUBDIRS['figures']/'StageU2_Medical_Label_Leverage_v0.1.png',dpi=180); plt.close(fig)
    if ext_summary is not None and len(ext_summary):
        fig,ax=plt.subplots(figsize=(8,5))
        ax.errorbar(np.arange(len(ext_summary)),ext_summary.alpha,yerr=[ext_summary.alpha-ext_summary.bootstrap_q025,ext_summary.bootstrap_q975-ext_summary.alpha],fmt='o',capsize=4)
        ax.axhline(OBS_ALPHA_DIRECT,linestyle='--',label='Medical AUC direct'); ax.axhline(.5,linestyle=':',label='root-n')
        ax.set_xticks(np.arange(len(ext_summary))); ax.set_xticklabels(ext_summary.metric,rotation=30,ha='right'); ax.set_ylabel('Scaling exponent'); ax.legend(); fig.tight_layout()
        fig.savefig(OUTPUT_ROOT/SUBDIRS['figures']/'StageU2_External_Multimetric_Exponents_v0.1.png',dpi=180); plt.close(fig)
    if ext_witness is not None and len(ext_witness):
        fig,ax=plt.subplots(figsize=(8,5))
        for metric,q in ext_witness.groupby('metric'):
            med=q.groupby('budget').mae.median(); ax.plot(med.index,med.values,marker='o',label=metric)
        ax.set_xscale('log',base=2); ax.set_yscale('log'); ax.set_xlabel('Witness budget'); ax.set_ylabel('Median target MAE'); ax.legend(fontsize=8); fig.tight_layout()
        fig.savefig(OUTPUT_ROOT/SUBDIRS['figures']/'StageU2_External_Multimetric_Collapse_v0.1.png',dpi=180); plt.close(fig)
    if transport is not None and len(transport):
        fig,ax=plt.subplots(figsize=(6,6)); ax.scatter(transport.true_auc,transport.transport_auc)
        lo=min(transport.true_auc.min(),transport.transport_auc.min()); hi=max(transport.true_auc.max(),transport.transport_auc.max()); ax.plot([lo,hi],[lo,hi],linestyle='--')
        ax.set_xlabel('True target AUC'); ax.set_ylabel('LOFO transport AUC'); fig.tight_layout()
        fig.savefig(OUTPUT_ROOT/SUBDIRS['figures']/'StageU2_External_Transport_Prediction_v0.1.png',dpi=180); plt.close(fig)


def save_df(df,path):
    path.parent.mkdir(parents=True,exist_ok=True); df.to_csv(path,index=False)


def main():
    t0=time.time()
    parent_zip=find_parent_zip(); parent_dir=extract_parent(parent_zip)
    panel_path=parent_dir/'01_Universal_Target_Budget_Panel'/'StageU0-U1_Universal_Target_Budget_Panel_v0.1.csv'
    panel=pd.read_csv(panel_path)
    integrity={
        'stage':STAGE,'version':VERSION,'seed':SEED,'parent_zip':str(parent_zip),'parent_zip_sha256':sha256_file(parent_zip),
        'parent_final_record_sha256':PARENT_FINAL_SHA,'run_external_nonbiomedical':RUN_EXTERNAL,
        'budgets':BUDGETS.tolist(),'new_blind_accessed':False,'stage12_authorised':False,
    }
    write_json(integrity,OUTPUT_ROOT/SUBDIRS['integrity']/'StageU2_Parent_Integrity_And_Protocol_v0.1.json')

    null_summary,null_ledger,mechanism=mechanism_null_simulation(panel)
    save_df(null_summary,OUTPUT_ROOT/SUBDIRS['mechanism']/'StageU2_AUC_Estimator_Null_Exponent_Summary_v0.1.csv')
    save_df(null_ledger,OUTPUT_ROOT/SUBDIRS['mechanism']/'StageU2_AUC_Estimator_Null_Target_Budget_Ledger_v0.1.csv')
    write_json(mechanism,OUTPUT_ROOT/SUBDIRS['mechanism']/'StageU2_Mechanism_Kill_Test_Decision_v0.1.json')

    med_ledger,med_budget,med_cross,med_seq=medical_label_efficiency(panel)
    save_df(med_ledger,OUTPUT_ROOT/SUBDIRS['medical']/'StageU2_Medical_Target_Budget_Label_Equivalence_v0.1.csv')
    save_df(med_budget,OUTPUT_ROOT/SUBDIRS['medical']/'StageU2_Medical_Label_Leverage_By_Budget_v0.1.csv')
    save_df(med_cross,OUTPUT_ROOT/SUBDIRS['medical']/'StageU2_Medical_Observed_Budget_Savings_v0.1.csv')
    save_df(med_seq,OUTPUT_ROOT/SUBDIRS['sequential']/'StageU2_Medical_LOTO_Sequential_Budget_Prediction_v0.1.csv')

    ext_metrics=transport=ext_witness=ext_reps=ext_summary=ext_holdout=ext_boot=ext_seq=pd.DataFrame()
    acquisition={'run_external':RUN_EXTERNAL,'status':'SKIPPED_BY_ENV' if not RUN_EXTERNAL else 'PENDING'}
    model_history=pd.DataFrame(); val_metrics={}
    external_error=None
    if RUN_EXTERNAL:
        try:
            meta=acquire_cifar_external(); acquisition.update(meta); acquisition['status']='ACQUIRED'
            model,eval_tf,threshold,model_history,val_metrics,source_tuple=train_cifar_model(meta)
            ext_metrics,scores_dict,labels_dict,feature_rows=external_environments(model,eval_tf,threshold,meta)
            transport=build_transport_predictions(ext_metrics,feature_rows,source_tuple)
            ext_witness,ext_reps=witness_scaling(ext_metrics,scores_dict,labels_dict,threshold,transport)
            ext_summary,ext_holdout,ext_boot=scaling_and_holdout(ext_witness)
            ext_seq=sequential_budget_external(ext_witness)
            acquisition['source_frozen_threshold']=threshold; acquisition['source_validation_metrics']=val_metrics
        except Exception as e:
            external_error=repr(e); acquisition['status']='FAILED'; acquisition['error']=external_error
            acquisition['manual_download_required']=True
    write_json(acquisition,OUTPUT_ROOT/SUBDIRS['acquisition']/'StageU2_External_CIFAR_Acquisition_Record_v0.1.json')
    if len(model_history): save_df(model_history,OUTPUT_ROOT/SUBDIRS['acquisition']/'StageU2_CIFAR_Model_Training_History_v0.1.csv')
    if len(ext_metrics):
        save_df(ext_metrics,OUTPUT_ROOT/SUBDIRS['external_scaling']/'StageU2_External_Target_True_Metrics_v0.1.csv')
        save_df(ext_witness,OUTPUT_ROOT/SUBDIRS['external_scaling']/'StageU2_External_Multimetric_Target_Budget_MAE_v0.1.csv')
        save_df(ext_summary,OUTPUT_ROOT/SUBDIRS['external_scaling']/'StageU2_External_Multimetric_Scaling_Exponents_v0.1.csv')
        save_df(ext_holdout,OUTPUT_ROOT/SUBDIRS['external_scaling']/'StageU2_External_Family_Holdout_Predictions_v0.1.csv')
        save_df(ext_boot,OUTPUT_ROOT/SUBDIRS['external_scaling']/'StageU2_External_Exponent_Bootstrap_v0.1.csv')
        save_df(transport,OUTPUT_ROOT/SUBDIRS['external_fusion']/'StageU2_External_LOFO_Transport_Predictions_v0.1.csv')
        save_df(ext_reps,OUTPUT_ROOT/SUBDIRS['external_fusion']/'StageU2_External_AUC_Direct_Fusion_Replicates_v0.1.csv')
        save_df(ext_seq,OUTPUT_ROOT/SUBDIRS['sequential']/'StageU2_External_Sequential_Budget_Prediction_v0.1.csv')

    # Reserve preregistration only; no acquisition or label access.
    reserve={
        'status':'DESIGN_ONLY_NOT_ACCESSED','new_blind_authorised':False,'stage12_authorised':False,
        'medical_reserve':{'independent_targets_recommended':'4-6','families_recommended':'2-3','primary_budget':32,
                           'frozen_transport_weight':0.6,'frozen_direct_weight':0.4,
                           'primary_predictions':['target performance MAE','direct exponent trajectory','fusion leverage','decision coverage']},
        'nonbiomedical_reserve':{'dataset':'DomainNet cleaned','planned_domains':['clipart','quickdraw','sketch','painting'],
                                 'reason':'independent visual-style domain family','download_not_started':True,
                                 'automatic_loader':'TensorFlow Datasets domainnet configs','manual_download_expected':False,
                                 'estimated_download_note':'domain-dependent; keep untouched until final preregistration hash'},
        'prohibited':['opening reserve labels before roster/hash freeze','retuning 0.6/0.4 on reserve','selecting domains from observed performance'],
    }
    write_json(reserve,OUTPUT_ROOT/SUBDIRS['reserve']/'StageU2_New_Reserve_Design_Preregistration_Draft_v0.1.json')

    # Gates
    gates=[]
    def gate(name,passed,observed): gates.append({'gate':name,'passed':bool(passed),'observed':observed})
    gate('parent_u01_integrity',True,PARENT_FINAL_SHA)
    gate('mechanism_null_panel_complete',len(null_summary)==16,f'cells={len(null_summary)}')
    gate('medical_direct_exponent_not_explained_by_auc_null',mechanism['observed_above_all_null_q975'],f"observed={OBS_ALPHA_DIRECT:.6f}; max_null_q975={mechanism['maximum_null_cell_q975']:.6f}")
    dev32=med_budget[(med_budget.role=='DEVELOPMENT')&(med_budget.budget==32)].iloc[0]
    prov32=med_budget[(med_budget.role=='PROVIDER_SEPARATED')&(med_budget.budget==32)].iloc[0]
    gate('medical_primary_budget_label_leverage',dev32.median_leverage>1.5 and prov32.median_leverage>1.5,f"development={dev32.median_leverage:.6f}; provider={prov32.median_leverage:.6f}")
    med_law=float(med_seq[med_seq.budget>8].law_abs_error.median()); med_root=float(med_seq[med_seq.budget>8].rootn_abs_error.median())
    gate('medical_sequential_budget_law_gain',med_law<med_root,f'law={med_law:.6f}; rootn={med_root:.6f}')
    external_ready=len(ext_summary)>0
    gate('external_nonbiomedical_acquisition',external_ready,acquisition.get('status'))
    if external_ready:
        aucrow=ext_summary[ext_summary.metric=='auc'].iloc[0]
        auc_hold=ext_holdout[(ext_holdout.metric=='auc')&(ext_holdout.budget>8)]
        auc_law=float(auc_hold.law_abs_error.median()); auc_root=float(auc_hold.rootn_abs_error.median())
        gate('external_auc_fixed_effect_collapse',aucrow.within_target_r2>=0.80,f"alpha={aucrow.alpha:.6f}; R2={aucrow.within_target_r2:.6f}")
        gate('external_auc_medical_exponent_compatibility',abs(aucrow.alpha-OBS_ALPHA_DIRECT)<=0.15 or (aucrow.bootstrap_q025<=OBS_ALPHA_DIRECT<=aucrow.bootstrap_q975),f"external={aucrow.alpha:.6f}; medical={OBS_ALPHA_DIRECT:.6f}; CI=[{aucrow.bootstrap_q025:.6f},{aucrow.bootstrap_q975:.6f}]")
        gate('external_auc_family_holdout_gain',auc_law<auc_root,f'law={auc_law:.6f}; rootn={auc_root:.6f}')
        strong_metrics=int((ext_summary.within_target_r2>=0.75).sum())
        gate('external_multimetric_scaling_regimes',strong_metrics>=3,f'strong_metrics={strong_metrics}/{len(ext_summary)}')
        ew=ext_witness[ext_witness.metric.isin(['auc','auc_fusion'])].pivot_table(index=['target','family','budget'],columns='metric',values='mae').reset_index()
        ew['leverage']=ew['auc']/ew['auc_fusion']
        e32=ew[ew.budget==32]
        gate('external_fixed_weight_fusion_leverage',e32.leverage.median()>1.0 and np.mean(e32.leverage>1)>=0.70,f"median={e32.leverage.median():.6f}; positive_rate={np.mean(e32.leverage>1):.6f}")
    else:
        for n in ['external_auc_fixed_effect_collapse','external_auc_medical_exponent_compatibility','external_auc_family_holdout_gain','external_multimetric_scaling_regimes','external_fixed_weight_fusion_leverage']:
            gate(n,False,external_error or acquisition.get('status'))
    gate('new_blind_accessed',True,False)
    gate('stage12_authorised',True,False)
    gates_df=pd.DataFrame(gates)
    save_df(gates_df,OUTPUT_ROOT/SUBDIRS['decision']/'StageU2_Frozen_Transparent_Gates_v0.1.csv')

    gate_map=dict(zip(gates_df.gate,gates_df.passed))
    strong=all(gate_map.get(k,False) for k in ['medical_direct_exponent_not_explained_by_auc_null','medical_primary_budget_label_leverage','medical_sequential_budget_law_gain','external_nonbiomedical_acquisition','external_auc_fixed_effect_collapse','external_auc_medical_exponent_compatibility','external_auc_family_holdout_gain','external_multimetric_scaling_regimes'])
    partial=all(gate_map.get(k,False) for k in ['medical_primary_budget_label_leverage','medical_sequential_budget_law_gain'])
    if strong:
        decision='SEAL_STAGEU2_MECHANISM_AND_CROSS_DOMAIN_EVIDENCE_SCALING_SUPPORTED_AUTHORISE_NEW_RESERVE_FINAL_PREREGISTRATION_ONLY'
    elif partial:
        decision='SEAL_STAGEU2_PARTIAL_SUPPORT_CONTINUE_TRANSPARENT_DEVELOPMENT_AND_RESERVE_PREREGISTRATION_ONLY'
    else:
        decision='SEAL_STAGEU2_MECHANISM_OR_LABEL_EFFICIENCY_NOT_SUPPORTED_PROHIBIT_NEW_BLIND'

    make_figures(null_summary,med_budget,ext_summary if external_ready else None,ext_witness if external_ready else None,transport if external_ready else None)

    result={
        'stage':STAGE,'version':VERSION,'decision':decision,'parent_final_record_sha256':PARENT_FINAL_SHA,
        'observed_medical_direct_alpha':OBS_ALPHA_DIRECT,'mechanism':mechanism,
        'medical_primary_budget32_development_leverage':float(dev32.median_leverage),
        'medical_primary_budget32_provider_leverage':float(prov32.median_leverage),
        'medical_sequential_law_mae':med_law,'medical_sequential_rootn_mae':med_root,
        'external_status':acquisition.get('status'),'external_targets':int(ext_metrics.target.nunique()) if external_ready else 0,
        'external_families':int(ext_metrics.family.nunique()) if external_ready else 0,
        'external_metric_exponents':ext_summary.set_index('metric').alpha.to_dict() if external_ready else {},
        'new_reserve_final_preregistration_authorised':bool(strong or partial),
        'new_blind_authorised':False,'stage12_authorised':False,'runtime_seconds':time.time()-t0,
    }
    # Freeze final scientific record hash from all payload files except Complete/manifest/ZIP.
    complete_path=OUTPUT_ROOT/SUBDIRS['decision']/'StageU2_Complete_v0.1.json'
    text=f"""# Stage U2 mechanism, label-efficiency and external non-biomedical validation\n\nThe Stage U0-U1 medical-imaging direct-witness exponent was {OBS_ALPHA_DIRECT:.3f}. Stage U2 tested whether this exponent could be reproduced by finite-sample AUC estimation alone across Gaussian, heavy-tailed, heteroscedastic and mixture score families under balanced/natural and independent/nested witness protocols. The maximum preregistered null 97.5th percentile was {mechanism['maximum_null_cell_q975']:.3f}. At the frozen 32-label budget, direct-transport fusion provided median evidence leverage of {dev32.median_leverage:.2f}x in development targets and {prov32.median_leverage:.2f}x in provider-separated targets. External non-biomedical validation status was {acquisition.get('status')}.\n\nDecision: {decision}. No new blind labels were accessed and Stage 12 remained prohibited.\n"""
    (OUTPUT_ROOT/SUBDIRS['decision']/'StageU2_Manuscript_Insert_v0.1.md').write_text(text,encoding='utf-8')
    payload_files=[]
    for p in sorted(OUTPUT_ROOT.rglob('*')):
        if p.is_file() and p.name not in ['StageU2_Complete_v0.1.json','StageU2_Canonical_Records_v0.1.zip','StageU2_Durable_Commit_Manifest_v0.1.json']:
            payload_files.append({'relative_path':str(p.relative_to(OUTPUT_ROOT)),'bytes':p.stat().st_size,'sha256':sha256_file(p)})
    final_sha=hashlib.sha256(json.dumps(payload_files,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    result['final_record_sha256']=final_sha
    write_json(result,complete_path)
    files=[]
    for p in sorted(OUTPUT_ROOT.rglob('*')):
        if p.is_file() and p.name not in ['StageU2_Canonical_Records_v0.1.zip','StageU2_Durable_Commit_Manifest_v0.1.json']:
            files.append({'relative_path':str(p.relative_to(OUTPUT_ROOT)),'bytes':p.stat().st_size,'sha256':sha256_file(p)})
    manifest={'stage':STAGE,'version':VERSION,'output_folder':str(OUTPUT_ROOT),'final_record_sha256':final_sha,'files':files}
    write_json(manifest,OUTPUT_ROOT/'StageU2_Durable_Commit_Manifest_v0.1.json')
    with zipfile.ZipFile(OUTPUT_ROOT/'StageU2_Canonical_Records_v0.1.zip','w',compression=zipfile.ZIP_DEFLATED) as zf:
        for row in files: zf.write(OUTPUT_ROOT/row['relative_path'],arcname=row['relative_path'])
        zf.write(OUTPUT_ROOT/'StageU2_Durable_Commit_Manifest_v0.1.json',arcname='StageU2_Durable_Commit_Manifest_v0.1.json')

    print('\n========== STAGE U2 COMPLETE ==========')
    print('Decision:',decision)
    print('Mechanism null max q975 / observed medical alpha:',mechanism['maximum_null_cell_q975'],OBS_ALPHA_DIRECT)
    print('Medical budget32 development / provider leverage:',float(dev32.median_leverage),float(prov32.median_leverage))
    print('Medical sequential law / root-n MAE:',med_law,med_root)
    print('External non-biomedical status / targets / families:',acquisition.get('status'),int(ext_metrics.target.nunique()) if external_ready else 0,int(ext_metrics.family.nunique()) if external_ready else 0)
    if external_ready:
        print('External metric exponents:',ext_summary.set_index('metric').alpha.to_dict())
    print('New reserve final preregistration authorised:',bool(strong or partial))
    print('New blind authorised:',False)
    print('Stage 12 authorised:',False)
    print('Final record SHA256:',final_sha)
    print('Committed to:',OUTPUT_ROOT)
    print(gates_df)

if __name__=='__main__':
    main()

