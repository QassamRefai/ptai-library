#!/usr/bin/env python3
"""Builds manifest.json for the Personal AI Tutor app.

Runs on GitHub Actions (which has internet access). For every source in
catalog/sources.json it pins the upstream commit, resolves the real download URL,
size and SHA-256, and writes them to manifest.json. Nothing is invented: a source
that cannot be resolved or has a non-allowed licence is skipped with a warning.
"""
import hashlib, json, os, re, sys, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "ptai-library-builder"}
MAX_OCR_BYTES = 60 * 1024 * 1024
warnings = []


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def sha256_of_url(url, limit):
    h, size = hashlib.sha256(), 0
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r:
        while True:
            b = r.read(1 << 20)
            if not b:
                break
            size += len(b)
            if size > limit:
                raise ValueError("file too large")
            h.update(b)
    return h.hexdigest(), size


def norm_license(s):
    return {"apache-2.0": "Apache-2.0", "mit": "MIT", "bsd-3-clause": "BSD-3-Clause", "cc-by-4.0": "CC-BY-4.0"}.get(s, s)


def llm_component(src, allowed):
    repo = src["hf_repo"]
    info = get_json(f"https://huggingface.co/api/models/{repo}")
    if info.get("gated"):
        raise RuntimeError("gated repository (needs login), skipped")
    lic = (info.get("cardData") or {}).get("license") or ""
    lic = lic.lower() if isinstance(lic, str) else ""
    if lic not in allowed:
        raise RuntimeError(f"licence '{lic}' not in allowed list")
    sha = info["sha"]
    tree = get_json(f"https://huggingface.co/api/models/{repo}/tree/{sha}")
    files = {t["path"]: t for t in tree if t.get("type") == "file"}
    chosen = None
    for pattern in src["file_prefer"]:
        matches = sorted(p for p in files if re.search(pattern, p))
        if matches:
            chosen = matches[0]
            break
    if not chosen:
        raise RuntimeError("no file matching file_prefer")
    f = files[chosen]
    lfs = f.get("lfs") or {}
    digest, size = lfs.get("oid"), lfs.get("size") or f.get("size")
    if not digest or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise RuntimeError("no sha256 published for file")
    kv = re.search(r"ekv(\d+)", chosen)
    cid = src["id"] + (f"-ekv{kv.group(1)}" if kv else "")
    return {
        "id": cid,
        "name": src["name"],
        "description": src["description"],
        "category": "llm",
        "version": sha[:8],
        "url": f"https://huggingface.co/{repo}/resolve/{sha}/{chosen}",
        "sizeBytes": int(size),
        "sha256": digest,
        "minRamMb": src["minRamMb"],
        "license": norm_license(lic),
        "licenseUrl": f"https://huggingface.co/{repo}",
        "required": False,
        "languages": src["languages"],
    }


def ocr_component(src, repo, sha):
    url = f"https://github.com/{repo}/raw/{sha}/{src['lang']}.traineddata"
    digest, size = sha256_of_url(url, MAX_OCR_BYTES)
    return {
        "id": src["id"],
        "name": src["name"],
        "description": src["description"],
        "category": "ocr",
        "version": sha[:8],
        "url": url,
        "sizeBytes": size,
        "sha256": digest,
        "minRamMb": 0,
        "license": "Apache-2.0",
        "licenseUrl": f"https://github.com/{repo}/blob/{sha}/LICENSE",
        "required": False,
        "languages": [src["lang"]],
    }


def main():
    with open(os.path.join(ROOT, "catalog", "sources.json"), encoding="utf-8") as fh:
        cfg = json.load(fh)
    allowed = set(cfg["allowed_licenses"])
    components = []

    for src in cfg["llm"]:
        try:
            components.append(llm_component(src, allowed))
        except Exception as e:  # skip, never invent
            warnings.append(f"{src['id']}: {e}")

    try:
        headers = {}
        if os.environ.get("GITHUB_TOKEN"):
            headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
        repo = cfg["tessdata_repo"]
        sha = get_json(f"https://api.github.com/repos/{repo}/commits/main", headers)["sha"]
        for src in cfg["ocr"]:
            try:
                components.append(ocr_component(src, repo, sha))
            except Exception as e:
                warnings.append(f"{src['id']}: {e}")
    except Exception as e:
        warnings.append(f"ocr: {e}")

    manifest = {"schemaVersion": 1, "components": components}
    with open(os.path.join(ROOT, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    for c in components:
        print(f"OK   {c['id']:<28} {c['sizeBytes']/1048576:8.1f} MB  {c['license']}  {c['version']}")
    for w in warnings:
        print("WARN", w)
    if not components:
        sys.exit("no components resolved")


if __name__ == "__main__":
    main()
