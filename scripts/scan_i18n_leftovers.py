#!/usr/bin/env python3
"""Scan Vue files for remaining hardcoded UI strings."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "vuejs" / "src"
VI = re.compile(r"[À-ỹĐđ]")
TOAST_EN = re.compile(
    r"""toast\.(success|error|warning|info)\(\s*['"][A-Za-z]"""
)
PLACEHOLDER_EN = re.compile(
    r"""(?:placeholder|title|aria-label)=["']([A-Za-z][^"']{2,})["']"""
)
TAG_TEXT = re.compile(
    r""">\s*(Log [Ii]n|Sign [Uu]p|Settings|Loading…?|Cancel|Submit|Delete|Save|Share|Follow|Search|Admin|Overview|Create|Messages|Apply|Report)\s*<"""
)

no_i18n = []
vi_hard = []
toast_hard = []
placeholder_hard = []

for p in sorted(ROOT.rglob("*.vue")):
    text = p.read_text(encoding="utf-8")
    rel = str(p.relative_to(ROOT))
    if "LanguageSwitcher" in rel:
        continue
    if "useI18n" not in text and len(text) > 800:
        # allow tiny presentational
        if any(x in rel for x in ("views", "components")):
            no_i18n.append(rel)
    for i, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("//") or s.startswith("*") or s.startswith("<!--"):
            continue
        if VI.search(line) and "t(" not in line and ("'" in line or '"' in line or ">" in line):
            # skip style/class-only
            if "class=" in line and not any(x in line for x in ("'", '"', "toast", "placeholder", "title", ">")):
                continue
            vi_hard.append(f"{rel}:{i}:{s[:120]}")
        if TOAST_EN.search(line) and "t(" not in line:
            toast_hard.append(f"{rel}:{i}:{s[:120]}")
        m = PLACEHOLDER_EN.search(line)
        if m and "t(" not in line and ":" not in m.group(1)[:3]:
            placeholder_hard.append(f"{rel}:{i}:{m.group(1)[:80]}")

print("=== NO useI18n ===", len(no_i18n))
for x in no_i18n:
    print(x)
print("=== VI hardcoded ===", len(vi_hard))
for x in vi_hard[:40]:
    print(x)
print("=== toast EN hardcoded ===", len(toast_hard))
for x in toast_hard[:40]:
    print(x)
print("=== placeholder/title EN ===", len(placeholder_hard))
for x in placeholder_hard[:40]:
    print(x)
