#!/usr/bin/env python3
"""Markdown relative-link integrity gate. Exit 1 on any broken link."""
import os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
bad = []
for base, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", ".ruff_cache", "node_modules"}]
    for fn in files:
        if not fn.endswith(".md"):
            continue
        p = os.path.join(base, fn)
        with open(p, encoding="utf-8") as fh:
            for m in re.finditer(r"\]\(([^)#][^)]*)\)", fh.read()):
                t = m.group(1).split("#")[0]
                if t.startswith("http") or not t:
                    continue
                if not os.path.exists(os.path.normpath(os.path.join(base, t))):
                    bad.append((os.path.relpath(p, ROOT), t))
for f, t in bad:
    print(f"  BROKEN {f} -> {t}")
print(f"broken links: {len(bad)}")
sys.exit(1 if bad else 0)
