from __future__ import annotations
from pathlib import Path
import re, shutil, zipfile, time, concurrent.futures
import requests

UA = {"User-Agent": "CMDO-U9-OpenClinical/1.0 (academic reproducibility)"}

def _download(url: str, out: Path, timeout=120) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".part")
    with requests.get(url, stream=True, timeout=timeout, headers=UA) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1024*1024):
                if chunk:
                    f.write(chunk)
    tmp.replace(out)
    return out

def ensure_uci_heart(raw_dir: Path, manual_dir: Path) -> Path:
    dst = raw_dir / "uci_heart"
    marker = dst / ".complete"
    if marker.exists():
        return dst
    dst.mkdir(parents=True, exist_ok=True)
    manual = manual_dir / "heart_disease.zip"
    archive = raw_dir / "heart_disease.zip"
    if manual.exists():
        shutil.copy2(manual, archive)
    elif not archive.exists():
        urls = [
            "https://archive.ics.uci.edu/static/public/45/heart%2Bdisease.zip",
            "https://archive.ics.uci.edu/static/public/45/heart+disease.zip",
        ]
        last = None
        for u in urls:
            try:
                _download(u, archive)
                break
            except Exception as e:
                last = e
        else:
            raise RuntimeError(f"UCI automatic download failed: {last}. Put official ZIP at {manual}.")
    with zipfile.ZipFile(archive) as z:
        z.extractall(dst)
    processed = list(dst.rglob("processed.*.data"))
    if len(processed) < 4:
        # UCI's modern landing page may surface only a subset of archive
        # members. Fall back to the long-standing official UCI
        # machine-learning-databases paths for the four standard processed
        # centre tables.
        official = {
            "processed.cleveland.data": "https://archive.ics.uci.edu/ml/machine-learning-databases/heart-disease/processed.cleveland.data",
            "processed.hungarian.data": "https://archive.ics.uci.edu/ml/machine-learning-databases/heart-disease/processed.hungarian.data",
            "processed.switzerland.data": "https://archive.ics.uci.edu/ml/machine-learning-databases/heart-disease/processed.switzerland.data",
            "processed.va.data": "https://archive.ics.uci.edu/ml/machine-learning-databases/heart-disease/processed.va.data",
        }
        for name,url in official.items():
            out=dst/name
            if not out.exists():
                try:
                    _download(url,out)
                except Exception:
                    pass
        processed = list(dst.rglob("processed.*.data"))
    if len(processed) < 4:
        names = [p.name for p in dst.rglob("*") if p.is_file()]
        raise RuntimeError("Could not obtain the four standard processed UCI centre files from official UCI routes. "
                           f"Found files include: {names[:50]}")
    marker.write_text("official UCI Heart Disease archive/routes extracted\n", encoding="utf-8")
    return dst

def _try_physionet_zip(set_name: str, raw_dir: Path, manual_dir: Path) -> Path | None:
    dst = raw_dir / set_name
    marker = dst / ".complete"
    if marker.exists():
        return dst
    dst.mkdir(parents=True, exist_ok=True)
    manual = manual_dir / f"{set_name}.zip"
    archive = raw_dir / f"{set_name}.zip"
    if manual.exists():
        shutil.copy2(manual, archive)
    elif not archive.exists():
        candidates = [
            f"https://archive.physionet.org/users/shared/challenge-2019/{set_name}.zip",
            f"https://physionet.org/files/challenge-2019/1.0.0/training/{set_name}.zip",
        ]
        ok = False
        for u in candidates:
            try:
                _download(u, archive)
                if zipfile.is_zipfile(archive):
                    ok = True
                    break
                archive.unlink(missing_ok=True)
            except Exception:
                archive.unlink(missing_ok=True)
        if not ok:
            return None
    if not zipfile.is_zipfile(archive):
        return None
    with zipfile.ZipFile(archive) as z:
        z.extractall(dst)
    return dst

def _download_physionet_directory(set_name: str, raw_dir: Path) -> Path:
    dst = raw_dir / set_name
    dst.mkdir(parents=True, exist_ok=True)
    base = f"https://physionet.org/files/challenge-2019/1.0.0/training/{set_name}/"
    html = requests.get(base, timeout=120, headers=UA)
    html.raise_for_status()
    names = sorted(set(re.findall(r'href="(p\d+\.psv)"', html.text)))
    if not names:
        raise RuntimeError(f"No PSV files discovered at {base}")
    def one(name):
        out = dst / name
        if out.exists() and out.stat().st_size > 0:
            return
        for attempt in range(4):
            try:
                _download(base + name, out, timeout=120)
                return
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(1.5*(attempt+1))
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
        list(ex.map(one, names))
    return dst

def ensure_physionet_2019(raw_dir: Path, manual_dir: Path) -> tuple[Path,Path]:
    expected = {"training_setA": 20336, "training_setB": 20000}
    outputs = []
    for name in ("training_setA","training_setB"):
        dst = raw_dir / name
        marker = dst / ".complete"
        if not marker.exists():
            got = _try_physionet_zip(name, raw_dir, manual_dir)
            if got is None:
                got = _download_physionet_directory(name, raw_dir)
            # archives sometimes add a nested directory
            files = list(got.rglob("*.psv"))
            if len(files) != expected[name]:
                raise RuntimeError(f"{name}: expected {expected[name]} official subjects, found {len(files)}.")
            marker.write_text(f"{len(files)} official PSV files verified by count\n", encoding="utf-8")
        outputs.append(dst)
    return outputs[0], outputs[1]
