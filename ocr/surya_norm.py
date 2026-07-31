#!/usr/bin/env python3
"""Normalize surya OCR JSON outputs into per-page text shards, and assemble the book."""
import json, os, re, sys, glob

def page_key_from_name(name):
    m = re.search(r'p-(\d+)', os.path.basename(str(name)))
    return "p-%03d" % int(m.group(1)) if m else None

def extract_text(item):
    if not isinstance(item, dict):
        return ""
    lines = item.get("text_lines") or item.get("lines") or []
    texts = []
    for ln in lines:
        if isinstance(ln, dict) and isinstance(ln.get("text"), str):
            texts.append(ln["text"])
        elif isinstance(ln, str):
            texts.append(ln)
    if not texts and isinstance(item.get("text"), str):
        texts.append(item["text"])
    return "\n".join(texts).strip()

def iter_entries(data, jf):
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, list):
                for item in v:
                    yield k, item
            elif isinstance(v, dict):
                yield k, v
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                fname = (item.get("file") or item.get("filename") or item.get("name")
                         or item.get("image_path") or "")
                yield fname, item

def normalize(indir, outdir):
    os.makedirs(outdir, exist_ok=True)
    jfiles = glob.glob(os.path.join(indir, "**", "*.json"), recursive=True)
    print(f"[norm] json files in {indir}: {len(jfiles)}")
    wrote = 0
    for jf in jfiles:
        try:
            with open(jf, encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as e:
            print(f"[norm] cannot parse {jf}: {e}")
            continue
        for fname, item in iter_entries(data, jf):
            text = extract_text(item)
            if not text:
                continue
            key = page_key_from_name(fname)
            if key is None:
                key = page_key_from_name(jf)
            if key is None:
                print(f"[norm] cannot determine page for entry in {jf}")
                continue
            outp = os.path.join(outdir, key + ".txt")
            with open(outp, "w", encoding="utf-8") as fh:
                fh.write(text + "\n")
            wrote += 1
    print(f"[norm] wrote {wrote} shards to {outdir}")

def assemble(pages_dir, out):
    shards = sorted(glob.glob(os.path.join(pages_dir, "p-*.txt")))
    missing = []
    if shards:
        nums = [int(re.search(r'p-(\d+)', s).group(1)) for s in shards]
        have = set(nums)
        missing = [n for n in range(min(nums), max(nums) + 1) if n not in have]
    with open(out, "w", encoding="utf-8") as fh:
        for s in shards:
            num = int(re.search(r'p-(\d+)', s).group(1))
            fh.write("\n\n===== [صفحة %d] =====\n\n" % num)
            with open(s, encoding="utf-8") as sf:
                fh.write(sf.read().strip() + "\n")
    print(f"[assemble] {len(shards)} pages -> {out}; missing pages so far: {missing[:50]}")

if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "--assemble":
        assemble(sys.argv[2], sys.argv[3])
    else:
        normalize(sys.argv[1], sys.argv[2])
