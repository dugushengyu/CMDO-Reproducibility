#!/usr/bin/env python3
"""
CMDO U10 PhysioNet FAST staged downloader v0.2

Key changes from v0.1
---------------------
- No HEAD-before-GET for every file.
- Persistent HTTP sessions (one per worker thread).
- Resume support via HTTP Range.
- SQLite completion cache: once a file is verified/downloaded, reruns skip it
  without touching the network.
- No SHA256 during network transfer; hashing is deferred to a separate local-only
  verification phase.
- Target labels remain blocked before the pre-outcome seal.

PRESEAL
-------
  source PTB-XL: .mat + .hea
  target Georgia: .mat only
  target CPSC 2018: .mat only

UNSEAL
------
  target .hea files only, and only if the required seal file already exists.

Scientific note
---------------
This is protocol blinding, not cryptographic sequestration. The public target
labels are deliberately not fetched into the U10 root before the seal.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import html.parser
import json
import os
import re
import sqlite3
import sys
import threading
import time
import urllib.parse
from pathlib import Path

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except Exception:
    print("ERROR: Python package 'requests' is required.", file=sys.stderr)
    print("Install it with: python -m pip install requests", file=sys.stderr)
    sys.exit(2)

BASE = "https://physionet.org/files/challenge-2020/1.0.2/training/"
DATASETS = {
    "source": "ptb-xl",
    "target_a": "georgia",
    "target_b": "cpsc_2018",
}
UA = "CMDO-U10-FAST/0.2"
TLS = threading.local()
CHUNK = 1024 * 1024

class LinkParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

def get_session():
    s = getattr(TLS, "session", None)
    if s is None:
        s = requests.Session()
        retry = Retry(
            total=5,
            connect=5,
            read=5,
            backoff_factor=0.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET"]),
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=4, pool_maxsize=4)
        s.mount("https://", adapter)
        s.headers.update({"User-Agent": UA, "Accept-Encoding": "identity"})
        TLS.session = s
    return s

def list_directory(url: str) -> list[str]:
    r = get_session().get(url, timeout=(15, 60))
    r.raise_for_status()
    p = LinkParser()
    p.feed(r.text)
    out = []
    for href in p.links:
        if href in ("../", "./", "/") or href.startswith(("?", "#")):
            continue
        absolute = urllib.parse.urljoin(url, href)
        if absolute.startswith(url):
            out.append(absolute)
    return sorted(set(out))

def crawl_files(dataset: str, allowed_exts: set[str]) -> list[str]:
    root = urllib.parse.urljoin(BASE, dataset + "/")
    todo = [root]
    seen = set()
    files = []
    while todo:
        u = todo.pop()
        if u in seen:
            continue
        seen.add(u)
        for link in list_directory(u):
            if link.endswith("/"):
                todo.append(link)
            else:
                ext = Path(urllib.parse.urlparse(link).path).suffix.lower()
                if ext in allowed_exts:
                    files.append(link)
    return sorted(set(files))

def relpath_for_url(url: str, dataset: str) -> Path:
    marker = f"/training/{dataset}/"
    path = urllib.parse.urlparse(url).path
    i = path.find(marker)
    if i < 0:
        raise ValueError(f"Unexpected URL: {url}")
    return Path(path[i + len(marker):])

def parse_total_from_content_range(value: str | None) -> int | None:
    if not value:
        return None
    # bytes 100-199/1000  OR  bytes */1000
    m = re.search(r"/(\d+)$", value)
    return int(m.group(1)) if m else None

def stream_response_to_file(resp, path: Path, mode: str) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with path.open(mode) as f:
        for chunk in resp.iter_content(chunk_size=CHUNK):
            if not chunk:
                continue
            f.write(chunk)
            written += len(chunk)
    return written

def probe_or_download(url: str, final: Path) -> dict:
    """
    One HTTP GET at most in the normal case.
    For legacy v0.1 final files we use a Range GET to verify/complete them.
    New downloads use .part files and atomic rename.
    """
    s = get_session()
    final.parent.mkdir(parents=True, exist_ok=True)
    part = final.with_name(final.name + ".part")

    # Prefer a resumable .part if present.
    if part.exists():
        local = part.stat().st_size
        headers = {"Range": f"bytes={local}-"} if local > 0 else {}
        r = s.get(url, headers=headers, stream=True, timeout=(15, 120))
        if local > 0 and r.status_code == 416:
            total = parse_total_from_content_range(r.headers.get("Content-Range"))
            r.close()
            if total is not None and local == total:
                os.replace(part, final)
                return {"status": "resumed-complete", "size": total, "net_bytes": 0}
            part.unlink(missing_ok=True)
            return probe_or_download(url, final)

        if local > 0 and r.status_code == 206:
            total = parse_total_from_content_range(r.headers.get("Content-Range"))
            n = stream_response_to_file(r, part, "ab")
            r.close()
            size = part.stat().st_size
            if total is not None and size != total:
                raise IOError(f"resume size mismatch local={size} expected={total} for {url}")
            os.replace(part, final)
            return {"status": "resumed", "size": size, "net_bytes": n}

        # Server ignored Range or this is a zero-byte part: restart cleanly.
        r.raise_for_status()
        n = stream_response_to_file(r, part, "wb")
        r.close()
        size = part.stat().st_size
        clen = r.headers.get("Content-Length")
        if clen and size != int(clen):
            raise IOError(f"size mismatch local={size} expected={clen} for {url}")
        os.replace(part, final)
        return {"status": "downloaded", "size": size, "net_bytes": n}

    # Legacy v0.1 file: verify with one Range GET, then cache completion in SQLite.
    if final.exists():
        local = final.stat().st_size
        if local == 0:
            final.unlink(missing_ok=True)
            return probe_or_download(url, final)

        r = s.get(url, headers={"Range": f"bytes={local}-"}, stream=True, timeout=(15, 120))

        if r.status_code == 416:
            total = parse_total_from_content_range(r.headers.get("Content-Range"))
            r.close()
            if total is not None and local == total:
                return {"status": "verified-existing", "size": local, "net_bytes": 0}
            # abnormal legacy file; redownload
            final.unlink(missing_ok=True)
            return probe_or_download(url, final)

        if r.status_code == 206:
            # Legacy file was partial. Move it to .part and finish it.
            total = parse_total_from_content_range(r.headers.get("Content-Range"))
            os.replace(final, part)
            n = stream_response_to_file(r, part, "ab")
            r.close()
            size = part.stat().st_size
            if total is not None and size != total:
                raise IOError(f"legacy resume mismatch local={size} expected={total} for {url}")
            os.replace(part, final)
            return {"status": "completed-legacy-partial", "size": size, "net_bytes": n}

        # Server ignored Range. We already have response headers without consuming the body.
        r.raise_for_status()
        clen = r.headers.get("Content-Length")
        if clen and local == int(clen):
            r.close()
            return {"status": "verified-existing", "size": local, "net_bytes": 0}

        # Not complete: overwrite via this already-open response.
        n = stream_response_to_file(r, part, "wb")
        r.close()
        size = part.stat().st_size
        if clen and size != int(clen):
            raise IOError(f"legacy replacement mismatch local={size} expected={clen} for {url}")
        os.replace(part, final)
        return {"status": "replaced-legacy", "size": size, "net_bytes": n}

    # Fresh file.
    r = s.get(url, stream=True, timeout=(15, 120))
    r.raise_for_status()
    n = stream_response_to_file(r, part, "wb")
    clen = r.headers.get("Content-Length")
    r.close()
    size = part.stat().st_size
    if clen and size != int(clen):
        raise IOError(f"fresh size mismatch local={size} expected={clen} for {url}")
    os.replace(part, final)
    return {"status": "downloaded", "size": size, "net_bytes": n}

def db_connect(root: Path):
    mdir = root / "manifests"
    mdir.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(mdir / "u10_download_state.sqlite")
    db.execute("""
        CREATE TABLE IF NOT EXISTS completed (
            relpath TEXT PRIMARY KEY,
            size INTEGER NOT NULL,
            phase TEXT NOT NULL,
            updated_utc TEXT NOT NULL
        )
    """)
    db.commit()
    return db

def load_cached(db, root: Path) -> dict[str, int]:
    out = {}
    for relpath, size in db.execute("SELECT relpath, size FROM completed"):
        p = root / relpath
        if p.exists() and p.stat().st_size == size:
            out[relpath] = size
    return out

def find_forbidden_target_headers(root: Path) -> list[Path]:
    hits = []
    for ds in (DATASETS["target_a"], DATASETS["target_b"]):
        d = root / "data" / ds
        if d.exists():
            hits.extend(d.rglob("*.hea"))
    return hits

def phase_plan(phase: str):
    if phase == "preseal":
        return [
            (DATASETS["source"], {".mat", ".hea"}),
            (DATASETS["target_a"], {".mat"}),
            (DATASETS["target_b"], {".mat"}),
        ]
    if phase == "unseal":
        return [
            (DATASETS["target_a"], {".hea"}),
            (DATASETS["target_b"], {".hea"}),
        ]
    raise ValueError(phase)

def worker(url: str, dest: Path):
    try:
        rec = probe_or_download(url, dest)
        rec.update({"url": url, "path": str(dest)})
        return rec
    except Exception as e:
        return {"status": "error", "url": url, "path": str(dest), "error": repr(e), "net_bytes": 0}

def status(root: Path):
    print(f"Root: {root}")
    for role, ds in DATASETS.items():
        d = root / "data" / ds
        mats = len(list(d.rglob("*.mat"))) if d.exists() else 0
        heas = len(list(d.rglob("*.hea"))) if d.exists() else 0
        parts = len(list(d.rglob("*.part"))) if d.exists() else 0
        print(f"{role:8s} {ds:12s} .mat={mats:6d}  .hea={heas:6d}  .part={parts:4d}")
    forbidden = find_forbidden_target_headers(root)
    print(f"Target headers present: {len(forbidden)}")
    db = db_connect(root)
    n = db.execute("SELECT COUNT(*) FROM completed").fetchone()[0]
    db.close()
    print(f"Cached completed files: {n}")

def verify_local(root: Path):
    """Local-only SHA256 inventory after download; no network calls."""
    data = root / "data"
    files = sorted([p for p in data.rglob("*") if p.is_file() and not p.name.endswith(".part")])
    out = root / "manifests" / "U10_LOCAL_SHA256.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    print(f"[verify] hashing {len(files)} local files (network is not used)")
    with out.open("w", encoding="utf-8") as f:
        for i, p in enumerate(files, 1):
            h = hashlib.sha256()
            with p.open("rb") as src:
                while True:
                    b = src.read(4 * 1024 * 1024)
                    if not b:
                        break
                    h.update(b)
            rec = {"relpath": str(p.relative_to(root)).replace("\\", "/"),
                   "size": p.stat().st_size, "sha256": h.hexdigest()}
            f.write(json.dumps(rec) + "\n")
            if i % 1000 == 0 or i == len(files):
                print(f"[verify] {i}/{len(files)}")
    print(f"[verify] wrote {out}")

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="command", required=True)

    for name in ("preseal", "unseal"):
        p = sub.add_parser(name)
        p.add_argument("--root", required=True)
        p.add_argument("--workers", type=int, default=48)
        if name == "unseal":
            p.add_argument("--seal", required=True)

    p = sub.add_parser("status")
    p.add_argument("--root", required=True)

    p = sub.add_parser("verify-local")
    p.add_argument("--root", required=True)

    args = ap.parse_args()
    root = Path(args.root).expanduser().resolve()

    if args.command == "status":
        status(root)
        return
    if args.command == "verify-local":
        verify_local(root)
        return

    if args.command == "preseal":
        forbidden = find_forbidden_target_headers(root)
        if forbidden:
            print("ERROR: target .hea files already exist under this U10 root.", file=sys.stderr)
            print("Use a new clean root before claiming a pre-outcome seal.", file=sys.stderr)
            sys.exit(3)

    if args.command == "unseal":
        seal = Path(args.seal).expanduser().resolve()
        if not seal.exists() or seal.stat().st_size == 0:
            print(f"ERROR: required pre-outcome seal missing/empty: {seal}", file=sys.stderr)
            sys.exit(4)

    db = db_connect(root)
    cache = load_cached(db, root)
    print(f"[cache] {len(cache)} files already verified/downloaded by v0.2")

    jobs = []
    for dataset, exts in phase_plan(args.command):
        print(f"[crawl] {dataset} extensions={sorted(exts)}")
        urls = crawl_files(dataset, exts)
        print(f"[crawl] {dataset}: {len(urls)} files")
        for u in urls:
            rel = Path("data") / dataset / relpath_for_url(u, dataset)
            dest = root / rel
            rels = str(rel).replace("\\", "/")
            if rels in cache and dest.exists() and dest.stat().st_size == cache[rels]:
                continue
            jobs.append((u, dest, rels))

    print(f"[plan] phase={args.command} remaining_network_jobs={len(jobs)} workers={args.workers}")
    if not jobs:
        print("DONE: nothing left to download.")
        db.close()
        return

    started = time.time()
    net_bytes = 0
    done = 0
    errors = 0
    pending_db = 0

    with cf.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        future_map = {
            pool.submit(worker, u, d): (u, d, rels)
            for (u, d, rels) in jobs
        }
        for fut in cf.as_completed(future_map):
            u, d, rels = future_map[fut]
            rec = fut.result()
            done += 1
            net_bytes += int(rec.get("net_bytes", 0) or 0)

            if rec.get("status") == "error":
                errors += 1
                print(f"[ERROR] {u} -> {rec.get('error')}", file=sys.stderr)
            else:
                size = int(rec["size"])
                db.execute(
                    "INSERT OR REPLACE INTO completed(relpath,size,phase,updated_utc) VALUES(?,?,?,datetime('now'))",
                    (rels, size, args.command),
                )
                pending_db += 1
                if pending_db >= 200:
                    db.commit()
                    pending_db = 0

            if done % 250 == 0 or done == len(jobs):
                elapsed = max(time.time() - started, 1e-6)
                mbps = (net_bytes * 8 / 1_000_000) / elapsed
                print(f"[progress] {done}/{len(jobs)}  errors={errors}  transferred={net_bytes/1e9:.3f} GB  avg_net={mbps:.1f} Mbps")

    db.commit()
    db.close()

    if errors:
        print(f"Completed with {errors} errors. Re-run the same command to retry only unfinished files.", file=sys.stderr)
        sys.exit(5)

    print("DONE")
    print("Next: run 'status'. Do NOT unseal target headers until the pre-outcome seal is frozen.")

if __name__ == "__main__":
    main()
