#!/usr/bin/env python3
"""docs/ の中のサイト内リンク（/ で始まる href・src）が、すべて実在のファイルにつながっているか確かめる"""
import os
import re
import sys
from urllib.parse import unquote

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "docs")
ATTR_RE = re.compile(r'(?:href|src)="([^"]*)"')


def resolve(path):
    path = unquote(path.split("#")[0].split("?")[0])
    if not path.startswith("/") or path.startswith("//"):
        return True
    rel = path.lstrip("/")
    full = os.path.join(OUT, rel)
    if path.endswith("/"):
        return os.path.isfile(os.path.join(full, "index.html"))
    return os.path.isfile(full)


def main():
    broken = []
    pages = 0
    links = 0
    for d, _, files in os.walk(OUT):
        for fn in files:
            if not fn.endswith(".html"):
                continue
            pages += 1
            p = os.path.join(d, fn)
            for href in ATTR_RE.findall(open(p, encoding="utf-8").read()):
                href = href.replace("&amp;", "&")
                if href.startswith("/") and not href.startswith("//"):
                    links += 1
                    if not resolve(href):
                        broken.append((os.path.relpath(p, OUT), href))
    print(f"HTMLページ {pages} / サイト内リンク {links} / リンク切れ {len(broken)}")
    for src, href in broken:
        print(f"  {src} -> {href}")
    sys.exit(1 if broken else 0)


if __name__ == "__main__":
    main()
