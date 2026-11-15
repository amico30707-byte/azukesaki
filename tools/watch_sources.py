#!/usr/bin/env python3
"""公式ページの変化チェック（あずけさき手帖）

施設データ（data/azukesaki_facilities.json）の出典と、記事（content/*.md）に
書かれている外部の公式ページを読みにいき、前回の中身とくらべます。

- 本文だけをとりだしてくらべます（日付・閲覧数など、よく変わる文字はのぞく）
- 変わったページ、読めなかったページを data/watch/report.md にまとめます
- 前回の状態は data/watch/state.json に保存します（GitHubのキャッシュに置き、リポジトリには入れません）

使い方：
  python3 tools/watch_sources.py            # すべて確認
  python3 tools/watch_sources.py --limit 50 # ためしに50件だけ
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "azukesaki_facilities.json")
CONTENT = os.path.join(ROOT, "content")
OUTDIR = os.path.join(ROOT, "data", "watch")
STATE = os.path.join(OUTDIR, "state.json")
REPORT = os.path.join(OUTDIR, "report.md")
SUMMARY = os.path.join(OUTDIR, "summary.json")

UA = ("Mozilla/5.0 (compatible; azukesaki-watch/1.0; "
      "+https://azukesaki.jp/ ; info@azukesaki.jp)")
TIMEOUT = 30
PER_HOST_DELAY = 2.0      # 同じサイトへは2秒あける
WORKERS = 12
MAX_BYTES = 15 * 1024 * 1024
SKIP_HOSTS = {"azukesaki.jp", "www.azukesaki.jp"}

JST = dt.timezone(dt.timedelta(hours=9))


# ---------- 出典の集め方 ----------

def collect_urls():
    """{url: [どこで使っているか(文字)]} を返す"""
    refs = defaultdict(list)
    d = json.load(open(DATA, encoding="utf-8"))
    items = d if isinstance(d, list) else d.get("facilities", [])
    for f in items:
        label = f"施設：{f.get('name','')}（{f.get('id','')}）"
        for s in f.get("sources", []) or []:
            u = s[1] if isinstance(s, (list, tuple)) and len(s) > 1 else (
                s.get("url") if isinstance(s, dict) else s)
            if isinstance(u, str) and u.startswith("http"):
                refs[u.strip()].append(label)
    url_re = re.compile(r"https?://[^\s<>\"'）)」』\]]+")
    for fn in sorted(os.listdir(CONTENT)):
        if not fn.endswith(".md"):
            continue
        text = open(os.path.join(CONTENT, fn), encoding="utf-8").read()
        # 記事ごとに分ける（記事番号をラベルにする）
        for block in re.split(r"\n-{5,}\n", text):
            m = re.search(r"記事番号：(\d+)", block)
            t = re.search(r"タイトル：(.+)", block)
            label = (f"記事{m.group(1)}：{t.group(1).split('｜')[0]}"
                     if m and t else f"記事ファイル：{fn}")
            for u in url_re.findall(block):
                u = u.rstrip("。、.,;:")
                host = urllib.parse.urlparse(u).hostname or ""
                if host in SKIP_HOSTS:
                    continue
                if label not in refs[u]:
                    refs[u].append(label)
    return refs


# ---------- 本文のとりだし ----------

DROP_BLOCKS = re.compile(
    r"<(script|style|noscript|svg|nav|header|footer|form|iframe|template)\b.*?</\1\s*>",
    re.S | re.I)
TAG = re.compile(r"<[^>]+>")
VOLATILE = [
    # 日付・時刻（更新日やカレンダー表示など）
    re.compile(r"(令和|平成)\s*\d+\s*年(\s*\d+\s*月)?(\s*\d+\s*日)?"),
    re.compile(r"\d{4}\s*[年/.\-]\s*\d{1,2}\s*[月/.\-]\s*\d{1,2}\s*日?"),
    re.compile(r"\d{1,2}\s*月\s*\d{1,2}\s*日\s*(\([^)]{1,3}\)|（[^）]{1,3}）)?"),
    re.compile(r"\d{1,2}:\d{2}(:\d{2})?"),
    # 閲覧数・アクセス数
    re.compile(r"(閲覧数|アクセス数|PV|ビュー)\s*[:：]?\s*[\d,]+"),
    # 「ページ番号」「ID」など
    re.compile(r"(ページ番号|記事ID|ページID)\s*[:：]?\s*\d+"),
]


def html_to_text(raw: bytes, charset_hint: str | None) -> str:
    enc = charset_hint
    if not enc:
        m = re.search(rb'charset=["\']?([A-Za-z0-9_\-]+)', raw[:4096])
        enc = m.group(1).decode("ascii", "ignore") if m else "utf-8"
    try:
        s = raw.decode(enc, errors="replace")
    except LookupError:
        s = raw.decode("utf-8", errors="replace")
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    main = re.search(r"<main\b.*?</main\s*>", s, re.S | re.I)
    if main:
        s = main.group(0)
    s = DROP_BLOCKS.sub(" ", s)
    s = re.sub(r"<(br|p|div|li|tr|h\d)\b[^>]*>", "\n", s, flags=re.I)
    s = TAG.sub(" ", s)
    s = html.unescape(s)
    return s


def pdf_to_text(raw: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tf:
        tf.write(raw)
        tf.flush()
        try:
            out = subprocess.run(["pdftotext", "-q", "-layout", tf.name, "-"],
                                 capture_output=True, timeout=60)
            return out.stdout.decode("utf-8", "replace")
        except Exception:
            return ""


def normalize(text: str) -> str:
    for r in VOLATILE:
        text = r.sub(" ", text)
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)


# ---------- 読みにいく ----------

_host_lock = defaultdict(threading.Lock)
_host_last = {}


def polite_wait(host):
    with _host_lock[host]:
        last = _host_last.get(host, 0)
        wait = PER_HOST_DELAY - (time.time() - last)
        if wait > 0:
            time.sleep(wait)
        _host_last[host] = time.time()


def fetch(url):
    host = urllib.parse.urlparse(url).hostname or ""
    polite_wait(host)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
        "Accept-Language": "ja,en;q=0.5",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read(MAX_BYTES + 1)
            ctype = r.headers.get("Content-Type", "")
            final = r.geturl()
            status = r.status
    except urllib.error.HTTPError as e:
        return {"ok": False, "status": e.code, "error": f"HTTP {e.code}"}
    except Exception as e:  # タイムアウト・名前解決など
        return {"ok": False, "status": None, "error": type(e).__name__ + ": " + str(e)[:120]}
    if len(raw) > MAX_BYTES:
        return {"ok": False, "status": status, "error": "too large"}
    is_pdf = "pdf" in ctype.lower() or raw[:5] == b"%PDF-"
    if is_pdf:
        text = pdf_to_text(raw)
        kind = "pdf"
        if not text.strip():  # 画像だけのPDFなど：ファイルそのものでくらべる
            text = "BINARY:" + hashlib.sha256(raw).hexdigest()
    elif "html" in ctype.lower() or raw.lstrip()[:1] == b"<":
        m = re.search(r"charset=([A-Za-z0-9_\-]+)", ctype)
        text = html_to_text(raw, m.group(1) if m else None)
        kind = "html"
    else:
        text = "BINARY:" + hashlib.sha256(raw).hexdigest()
        kind = "other"
    norm = normalize(text)
    return {
        "ok": True, "status": status, "final": final, "kind": kind,
        "hash": hashlib.sha256(norm.encode("utf-8")).hexdigest(),
        "length": len(norm),
        "lines": [hashlib.sha1(ln.encode("utf-8")).hexdigest()[:10]
                  for ln in norm.splitlines()[:400]],
        "text": norm,
    }


# ---------- くらべる ----------

def diff_hint(old_lines, new_text: str, new_lines, limit=8):
    """ふえた行を少しだけ見せる（くわしい比較は人が公式ページで行う）"""
    if not old_lines:
        return []
    o = set(old_lines)
    texts = new_text.splitlines()[:400]
    added = [texts[i] for i, h in enumerate(new_lines) if h not in o][:limit]
    removed = len(set(old_lines) - set(new_lines))
    out = [f"＋ {a[:120]}" for a in added]
    if removed:
        out.append(f"（なくなった行：{removed}行）")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=WORKERS)
    args = ap.parse_args()

    os.makedirs(OUTDIR, exist_ok=True)
    state = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {}
    refs = collect_urls()
    urls = sorted(refs)
    if args.limit:
        urls = urls[: args.limit]
    now = dt.datetime.now(JST).strftime("%Y-%m-%d %H:%M")
    first_run = not state

    results = {}
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(fetch, u): u for u in urls}
        for i, fu in enumerate(cf.as_completed(futs), 1):
            u = futs[fu]
            try:
                results[u] = fu.result()
            except Exception as e:
                results[u] = {"ok": False, "status": None, "error": str(e)[:120]}
            if i % 200 == 0:
                print(f"{i}/{len(urls)}", file=sys.stderr, flush=True)

    changed, failed, new_urls, recovered = [], [], [], []
    for u in urls:
        r = results[u]
        prev = state.get(u)
        entry = dict(prev or {})
        entry["checked"] = now
        if r["ok"]:
            if prev and prev.get("hash") and prev["hash"] != r["hash"]:
                changed.append((u, diff_hint(prev.get("lines"), r["text"], r["lines"])))
                entry["lastChanged"] = now
            elif not prev or not prev.get("hash"):
                if prev and prev.get("fails"):
                    recovered.append(u)
                else:
                    new_urls.append(u)
            entry.update({k: r[k] for k in ("hash", "length", "kind", "final", "lines")})
            entry["status"] = r["status"]
            entry["fails"] = 0
            entry.pop("error", None)
        else:
            entry["fails"] = (prev or {}).get("fails", 0) + 1
            entry["error"] = r["error"]
            entry["status"] = r["status"]
            failed.append(u)
        state[u] = entry

    # もう使っていない出典は消す（--limit のときは消さない）
    if not args.limit:
        for u in list(state):
            if u not in refs:
                del state[u]

    json.dump(state, open(STATE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=0, sort_keys=True)

    # 2回つづけて読めなかったものだけを「読めない」として出す（一時的な失敗をのぞく）
    persistent = [u for u in failed if state[u]["fails"] >= 2]

    lines = [f"# 公式ページの変化チェック（{now}）", ""]
    lines.append(f"- 確認したページ：{len(urls)}")
    lines.append(f"- 前回から変わったページ：{len(changed)}")
    lines.append(f"- 2回つづけて読めなかったページ：{len(persistent)}")
    lines.append(f"- 今回はじめて記録したページ：{len(new_urls)}")
    if first_run:
        lines += ["", "はじめての確認なので、今回は記録だけです。次の回から変化を知らせます。"]
    lines.append("")
    if changed:
        lines += ["## 変わったページ", "",
                  "公式ページを開いて、サイトの内容を直す必要があるか確かめてください。", ""]
        for u, hint in changed:
            lines.append(f"### {u}")
            for ref in refs[u][:8]:
                lines.append(f"- {ref}")
            if len(refs[u]) > 8:
                lines.append(f"- ほか{len(refs[u]) - 8}か所")
            if hint:
                lines.append("")
                lines.append("変わった行の例：")
                lines += [f"    {h}" for h in hint]
            lines.append("")
    if persistent:
        lines += ["## 読めなかったページ（2回つづけて）", "",
                  "ページが消えた・アドレスが変わった・読みこみをことわられた、などが考えられます。", ""]
        for u in persistent:
            e = state[u].get("error", "")
            lines.append(f"- {u}（{e}）")
            for ref in refs[u][:3]:
                lines.append(f"    - {ref}")
        lines.append("")
    open(REPORT, "w", encoding="utf-8").write("\n".join(lines))
    json.dump({"date": now, "checked": len(urls), "changed": len(changed),
               "failed": len(persistent), "new": len(new_urls), "first_run": first_run},
              open(SUMMARY, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"確認 {len(urls)} / 変化 {len(changed)} / 読めない(2回) {len(persistent)} / 新規 {len(new_urls)}")


if __name__ == "__main__":
    main()
