#!/usr/bin/env python3
"""あずけさき手帖 静的サイト生成スクリプト

使い方: python3 build.py
出力先: docs/ （GitHub Pages の /docs 配信用）
"""
import datetime
import html
import json
import os
import re
import shutil
import sys

import markdown

# ---------------------------------------------------------------- 設定
BASE_URL = "https://azukesaki.jp"  # 本番のドメインが決まったらここを変える
SITE_NAME = "あずけさき手帖"
SITE_SUBTITLE = "重い障害のあるお子様の、あずけ先さがしと将来のじゅんび"
CONTACT_EMAIL = "info@azukesaki.jp"
GA_ID = "G-BTXQ8P2HPG"  # Googleアナリティクスの測定ID
BUILD_DATE = datetime.date.today().isoformat()
OGP_IMAGE = "/static/ogp.png"  # 1200×630。作り直すときは node make_images.js

ROOT = os.path.dirname(os.path.abspath(__file__))
CONTENT_DIR = os.path.join(ROOT, "content")
STATIC_DIR = os.path.join(ROOT, "static")
OUT_DIR = os.path.join(ROOT, "docs")
FACILITY_FILE = os.path.join(ROOT, "data", "azukesaki_facilities.json")

ABOUT_FILE = "01_運営者情報.md"
GUIDE_FILE = "02_はじめての方へ.md"  # この中の3本がトップの「はじめての方へ」カード

CATEGORIES = [  # (名前, スラッグ)
    ("はじめての方へ", "hajimete"),
    ("あずけ先の種類と使い方", "shurui"),
    ("お子様の状態別", "jotai"),
    ("家族の暮らしと気持ち", "kurashi"),
    ("18歳から先のこと", "18sai"),
    ("都道府県のあずけ先", "todofuken"),
    ("市ごとのあずけ先", "shi"),
]
CAT_SLUG = dict(CATEGORIES)

REGIONS = ["北海道・東北", "関東", "中部", "近畿", "中国", "四国", "九州・沖縄"]
PREFS = [  # (スラッグ, 名前, 地方)
    ("hokkaido", "北海道", 0), ("aomori", "青森県", 0), ("iwate", "岩手県", 0),
    ("miyagi", "宮城県", 0), ("akita", "秋田県", 0), ("yamagata", "山形県", 0),
    ("fukushima", "福島県", 0),
    ("ibaraki", "茨城県", 1), ("tochigi", "栃木県", 1), ("gunma", "群馬県", 1),
    ("saitama", "埼玉県", 1), ("chiba", "千葉県", 1), ("tokyo", "東京都", 1),
    ("kanagawa", "神奈川県", 1),
    ("niigata", "新潟県", 2), ("toyama", "富山県", 2), ("ishikawa", "石川県", 2),
    ("fukui", "福井県", 2), ("yamanashi", "山梨県", 2), ("nagano", "長野県", 2),
    ("gifu", "岐阜県", 2), ("shizuoka", "静岡県", 2), ("aichi", "愛知県", 2),
    ("mie", "三重県", 3), ("shiga", "滋賀県", 3), ("kyoto", "京都府", 3),
    ("osaka", "大阪府", 3), ("hyogo", "兵庫県", 3), ("nara", "奈良県", 3),
    ("wakayama", "和歌山県", 3),
    ("tottori", "鳥取県", 4), ("shimane", "島根県", 4), ("okayama", "岡山県", 4),
    ("hiroshima", "広島県", 4), ("yamaguchi", "山口県", 4),
    ("tokushima", "徳島県", 5), ("kagawa", "香川県", 5), ("ehime", "愛媛県", 5),
    ("kochi", "高知県", 5),
    ("fukuoka", "福岡県", 6), ("saga", "佐賀県", 6), ("nagasaki", "長崎県", 6),
    ("kumamoto", "熊本県", 6), ("oita", "大分県", 6), ("miyazaki", "宮崎県", 6),
    ("kagoshima", "鹿児島県", 6), ("okinawa", "沖縄県", 6),
]
PREF_NAME = {s: n for s, n, _ in PREFS}

# 市の記事 → 都道府県（タイトルの市名で判定）
CITY_PREF = {
    "札幌市": "hokkaido", "仙台市": "miyagi", "さいたま市": "saitama", "川口市": "saitama",
    "千葉市": "chiba", "船橋市": "chiba", "八王子市": "tokyo", "横浜市": "kanagawa",
    "川崎市": "kanagawa", "相模原市": "kanagawa", "新潟市": "niigata", "富山市": "toyama",
    "金沢市": "ishikawa", "岐阜市": "gifu", "静岡市": "shizuoka", "浜松市": "shizuoka",
    "名古屋市": "aichi", "豊田市": "aichi", "京都市": "kyoto", "大阪市": "osaka",
    "堺市": "osaka", "東大阪市": "osaka", "神戸市": "hyogo", "姫路市": "hyogo",
    "西宮市": "hyogo", "尼崎市": "hyogo", "岡山市": "okayama", "倉敷市": "okayama",
    "広島市": "hiroshima", "福山市": "hiroshima", "高松市": "kagawa", "松山市": "ehime",
    "北九州市": "fukuoka", "福岡市": "fukuoka", "長崎市": "nagasaki", "熊本市": "kumamoto",
    "大分市": "oita", "宮崎市": "miyazaki", "鹿児島市": "kagoshima", "宇都宮市": "tochigi",
    "柏市": "chiba", "豊中市": "osaka", "枚方市": "osaka", "高槻市": "osaka",
    "横須賀市": "kanagawa", "一宮市": "aichi", "岡崎市": "aichi", "越谷市": "saitama",
    "和歌山市": "wakayama", "奈良市": "nara", "旭川市": "hokkaido", "郡山市": "fukushima",
    "いわき市": "fukushima", "前橋市": "gunma", "高崎市": "gunma", "長野市": "nagano",
    "那覇市": "okinawa", "下関市": "yamaguchi", "秋田市": "akita", "盛岡市": "iwate",
    "世田谷区": "tokyo", "練馬区": "tokyo", "大田区": "tokyo", "江戸川区": "tokyo",
    "足立区": "tokyo", "杉並区": "tokyo", "板橋区": "tokyo", "江東区": "tokyo",
    "葛飾区": "tokyo", "品川区": "tokyo",
    "松本市": "nagano", "吹田市": "osaka", "豊橋市": "aichi", "川越市": "saitama",
    "大津市": "shiga", "所沢市": "saitama", "高知市": "kochi", "明石市": "hyogo",
    "久留米市": "fukuoka", "函館市": "hokkaido",
    "八尾市": "osaka", "寝屋川市": "osaka", "水戸市": "ibaraki", "福島市": "fukushima",
    "青森市": "aomori", "甲府市": "yamanashi", "福井市": "fukui", "山形市": "yamagata",
    "佐世保市": "nagasaki", "松江市": "shimane",
    "鳥取市": "tottori", "呉市": "hiroshima", "八戸市": "aomori", "町田市": "tokyo",
    "藤沢市": "kanagawa",
    "中野区": "tokyo", "北区": "tokyo", "新宿区": "tokyo", "豊島区": "tokyo",
    "目黒区": "tokyo", "徳島市": "tokushima", "佐賀市": "saga", "山口市": "yamaguchi",
    "津市": "mie", "松戸市": "chiba",
}

TYPE_LABELS = {
    "stay": "お泊まり（短期入所）",
    "day": "日中のあずかり",
    "home": "家に来るヘルパー",
    "out": "外出の付きそい",
    "therapy": "通う療育",
}
SUPPORT_LABELS = {
    "pimd": "重症心身障害",
    "medical": "医療的ケア",
    "ventilator": "人工呼吸器",
    "tube": "経管栄養",
    "suction": "たんの吸引",
    "oxygen": "在宅酸素",
    "behavior": "強度行動障害",
    "intellectual": "知的障害",
    "autism": "自閉症",
    "physical": "肢体不自由",
    "epilepsy": "てんかん",
    "mobility": "移動に支えが必要",
}
SUPPORT_STATUS_LABELS = {
    "yes": "受け入れの記載あり",
    "ok": "受け入れの記載あり",
    "available": "受け入れの記載あり",
    "ask": "施設に相談",
    "consult": "施設に相談",
    "maybe": "施設に相談",
    "unknown": "記載なし",
    "no": "受け入れの記載なし",
}
SUPPORT_NEGATIVE = {"no", "none", "unknown", "", "false", "不可"}

FACILITY_NOTE = "空きや受け入れは、かならず施設にご確認ください"

# ---------------------------------------------------------------- 共通
esc = html.escape
PAGES = []  # sitemap 用の URL パス


def write_page(path, content, sitemap=True):
    """path はサイト内のパス（/blog/x.html や /about/）"""
    rel = path.lstrip("/")
    if rel == "" or rel.endswith("/"):
        rel += "index.html"
    full = os.path.join(OUT_DIR, rel)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    if sitemap:
        PAGES.append(path)


def abs_url(path):
    return BASE_URL.rstrip("/") + path


def breadcrumb_html(items):
    """items: [(名前, パス or None)]"""
    lis = []
    for i, (name, href) in enumerate(items):
        if href and i < len(items) - 1:
            lis.append(f'<li><a href="{esc(href)}">{esc(name)}</a></li>')
        else:
            lis.append(f'<li aria-current="page">{esc(name)}</li>')
    return '<nav class="breadcrumb" aria-label="パンくずリスト"><ol>' + "".join(lis) + "</ol></nav>"


def breadcrumb_ld(items):
    elems = []
    for i, (name, href) in enumerate(items, 1):
        e = {"@type": "ListItem", "position": i, "name": name}
        if href:
            e["item"] = abs_url(href)
        elems.append(e)
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": elems}


LOGO_SVG = """<svg class="logo-mark" viewBox="0 0 32 32" width="30" height="30" aria-hidden="true" focusable="false">
<rect x="5" y="2.5" width="22" height="26" rx="3.2" fill="#24564a"/>
<rect x="5" y="2.5" width="5.5" height="26" rx="2.4" fill="#183f35"/>
<path d="M22.6 8.4c-5.6.6-8.6 4.4-8.3 10.6 5.4-.3 8.6-4 8.3-10.6z" fill="#f2c39c"/>
<path d="M14.9 18.6c1.6-3.1 3.6-5.6 6.2-7.6" stroke="#24564a" stroke-width="1.1" fill="none" stroke-linecap="round"/>
<path d="M21 28.5v3l1.6-1.3 1.6 1.3v-3z" fill="#e39a66"/>
</svg>"""

NAV_ITEMS = [("よみもの", "/blog/"), ("都道府県", "/#prefectures"), ("施設さがし", "/search/")]

# カテゴリのアイコン（線だけのやさしい形）
CAT_ICONS = {
    "hajimete": '<path d="M12 20V11"/><path d="M12 13c0-3.5-2.4-5.6-6.5-5.6 0 3.8 2.4 5.6 6.5 5.6z"/><path d="M12 11.5c0-3.2 2.2-5.2 6-5.2 0 3.5-2.2 5.2-6 5.2z"/><path d="M7 20h10"/>',
    "shurui": '<path d="M4 11.2 12 4.5l8 6.7"/><path d="M6 9.8V19.5h12V9.8"/><path d="M10.2 19.5v-5h3.6v5"/>',
    "jotai": '<path d="M12 19.5s-7.5-4.4-7.5-9.6A4.1 4.1 0 0 1 12 7.6a4.1 4.1 0 0 1 7.5 2.3c0 5.2-7.5 9.6-7.5 9.6z"/>',
    "kurashi": '<path d="M5 9.5h11v5a5 5 0 0 1-5 5h-1a5 5 0 0 1-5-5z"/><path d="M16 11h1.5a2.3 2.3 0 0 1 0 4.6H16"/><path d="M9 3.8c-.8 1 .8 2 0 3M12.2 3.8c-.8 1 .8 2 0 3"/>',
    "18sai": '<path d="M3.5 17.5h17"/><path d="M7 17.5a5 5 0 0 1 10 0"/><path d="M12 6v2.2M5.6 8.7l1.5 1.5M18.4 8.7l-1.5 1.5"/>',
    "todofuken": '<path d="M12 20.5s-6-5.6-6-10.3a6 6 0 0 1 12 0c0 4.7-6 10.3-6 10.3z"/><circle cx="12" cy="10.2" r="2.2"/>',
    "shi": '<path d="M4 20V9.5l5-2.5V20"/><path d="M9 20V4.5l7 3V20"/><path d="M16 20v-7.5h4V20"/><path d="M3 20h18"/><path d="M11.5 9.5h2M11.5 12.5h2M11.5 15.5h2"/>',
}


def icon_svg(slug, cls="cat-icon"):
    return (f'<svg class="{cls}" viewBox="0 0 24 24" width="28" height="28" aria-hidden="true" focusable="false" '
            f'fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">'
            f'{CAT_ICONS.get(slug, "")}</svg>')


def jp_date(iso):
    y, m, d = iso.split("-")
    return f"{int(y)}年{int(m)}月{int(d)}日"


FOOTER = f"""<footer class="site-footer">
  <div class="wrap wrap-wide">
    <p class="footer-brand">{LOGO_SVG}<span>{SITE_NAME}</span></p>
    <nav aria-label="サイト内リンク">
      <ul class="footer-links">
        <li><a href="/">トップ</a></li>
        <li><a href="/blog/">よみもの</a></li>
        <li><a href="/#prefectures">都道府県から</a></li>
        <li><a href="/about/">運営者情報</a></li>
        <li><a href="/contact/">お問い合わせ</a></li>
        <li><a href="/for-facilities/">施設・事業所の方へ</a></li>
        <li><a href="/privacy/">プライバシー</a></li>
      </ul>
    </nav>
    <p class="footer-note">一部の記事には広告（PR）がふくまれます。Amazonのアソシエイトとして、あずけさき手帖は適格販売により収入を得ています。</p>
    <p class="footer-note">公式情報をもとに整理しています。空きや受け入れは、各施設にご確認ください。</p>
    <p class="copyright">&copy; {SITE_NAME}</p>
  </div>
</footer>"""


def page(title, description, path, body, *, crumbs=None, og_type="website",
         extra_ld=None, full_title=None, scripts="", noindex=False, wide=False):
    """HTML 全体を組み立てる"""
    doc_title = full_title or (f"{title}｜{SITE_NAME}" if title != SITE_NAME else f"{SITE_NAME}｜{SITE_SUBTITLE}")
    lds = []
    if crumbs:
        lds.append(breadcrumb_ld(crumbs))
    if extra_ld:
        lds.append(extra_ld)
    ld_html = "".join(
        '<script type="application/ld+json">' + json.dumps(ld, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"
        for ld in lds)
    crumb_html = breadcrumb_html(crumbs) if crumbs else ""
    robots = '<meta name="robots" content="noindex">\n' if noindex else ""
    canonical = abs_url(path)
    nav_links = "".join(f'<li><a href="{h}">{n}</a></li>' for n, h in NAV_ITEMS)
    main_cls = "wrap wrap-wide" if wide else "wrap"
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{GA_ID}');</script>
<title>{esc(doc_title)}</title>
<meta name="description" content="{esc(description)}">
{robots}<link rel="canonical" href="{esc(canonical)}">
<meta property="og:site_name" content="{SITE_NAME}">
<meta property="og:locale" content="ja_JP">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{esc(doc_title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:image" content="{esc(abs_url(OGP_IMAGE))}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{SITE_NAME}｜{SITE_SUBTITLE}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(doc_title)}">
<meta name="twitter:description" content="{esc(description)}">
<meta name="twitter:image" content="{esc(abs_url(OGP_IMAGE))}">
<meta name="theme-color" content="#f5f1e8">
<link rel="icon" href="/static/icons/favicon.svg" type="image/svg+xml">
<link rel="icon" href="/static/icons/favicon-32.png" type="image/png" sizes="32x32">
<link rel="apple-touch-icon" href="/static/icons/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<link rel="stylesheet" href="/static/style.css">
{ld_html}</head>
<body>
<a class="skip-link" href="#main">本文へ移動</a>
<header class="site-header">
  <div class="wrap wrap-wide header-inner">
    <a class="site-name" href="/">{LOGO_SVG}<span>{SITE_NAME}</span></a>
    <nav class="nav-inline" aria-label="メインメニュー">
      <ul class="header-links">{nav_links}</ul>
    </nav>
    <details class="nav-menu">
      <summary><span class="menu-bars" aria-hidden="true"></span>メニュー</summary>
      <nav aria-label="メインメニュー（スマホ）"><ul>{nav_links}</ul></nav>
    </details>
  </div>
</header>
<main id="main" class="{main_cls}">
{crumb_html}
{body}
</main>
{FOOTER}
<script>document.querySelectorAll(".nav-menu a").forEach(function(a){{a.addEventListener("click",function(){{a.closest("details").open=false;}});}});</script>
{scripts}</body>
</html>
"""


# ---------------------------------------------------------------- Markdown 変換
PLACEHOLDER_RE = re.compile(r"【[^【】]*あとで入れる[^【】]*】")
URL_RE = re.compile(r"(?<![(<\"'=])(https?://[A-Za-z0-9\-._~:/?#@!$&*+,;=%]+)")
LIST_RE = re.compile(r"^(\s*)([-*+]|\d+\.)\s")


def clean_placeholders(text):
    out = []
    for line in text.split("\n"):
        if "あとで入れる" in line:
            new = PLACEHOLDER_RE.sub("", line).rstrip()
            # 中身がなくなった行・「あとで入れる」だけの行は消す
            if "あとで入れる" in new or not re.sub(r"^[\s\-*+0-9.]*", "", new):
                continue
            line = new
        out.append(line)
    return "\n".join(out)


def autolink(line):
    def rep(m):
        url = m.group(1)
        trail = ""
        while url and url[-1] in ".,;:!?":
            trail = url[-1] + trail
            url = url[:-1]
        return f"<{url}>{trail}"
    return URL_RE.sub(rep, line)


def preprocess(md):
    """Python-Markdown が読みやすいように、リストと表の前に空行を入れ、裸のURLをリンクにする"""
    md = clean_placeholders(md)
    lines = md.split("\n")
    out = []
    for i, line in enumerate(lines):
        prev = out[-1] if out else ""
        is_list = bool(LIST_RE.match(line))
        is_table = line.lstrip().startswith("|")
        prev_list = bool(LIST_RE.match(prev)) or (prev.startswith("   ") and prev.strip())
        prev_table = prev.lstrip().startswith("|")
        if prev.strip():
            if is_list and not prev_list:
                out.append("")
            elif is_table and not prev_table:
                out.append("")
            elif not is_table and prev_table and line.strip():
                out.append("")
        if not is_table:
            line = autolink(line)
        out.append(line)
    return "\n".join(out)


def md_to_html(md):
    h = markdown.markdown(preprocess(md), extensions=["tables", "sane_lists"], output_format="html5")
    h = h.replace("<table>", '<div class="table-wrap" role="region" aria-label="表（横にスクロールできます）" tabindex="0"><table>')
    h = h.replace("</table>", "</table></div>")
    # 外部リンクは新しいタブにしない（戻りやすさ優先）。rel だけ付ける
    h = re.sub(r'<a href="(https?://[^"]+)"', r'<a href="\1" rel="noopener"', h)
    # 「※」で始まる段落は、注意書きのかこみにする
    h = h.replace("<p>※", '<p class="callout">※')
    # 「出典：」の段落（とすぐ後ろのリスト）は、小さめの文字にする
    h = re.sub(r"<p>(出典[：:].*?)</p>(\s*<ul>.*?</ul>)?",
               lambda m: f'<div class="sources"><p>{m.group(1)}</p>{m.group(2) or ""}</div>', h, flags=re.S)
    return h


TOC_SKIP = {"はじめに", "さいごに", "出典", "参考", "運営者から、ひとこと"}


def add_heading_ids(h):
    """本文の h2 に id をつけ、[(id, 見出し)] を返す"""
    toc = []

    def rep(m):
        n = len(toc) + 1
        text = strip_tags(m.group(1)).strip()
        hid = f"s{n}"
        toc.append((hid, text))
        return f'<h2 id="{hid}">{m.group(1)}</h2>'
    h = re.sub(r"<h2>(.*?)</h2>", rep, h)
    toc = [(i, t) for i, t in toc if t not in TOC_SKIP and "（PR）" not in t]
    return h, toc


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)


# ---------------------------------------------------------------- 記事の読み込み
SETTING_RE = re.compile(r"【設定】(.*?)【設定ここまで】", re.S)


def parse_settings(block):
    d = {}
    for line in block.strip().split("\n"):
        line = line.strip()
        m = re.match(r"^([^：:]+)[：:](.*)$", line)
        if m:
            d[m.group(1).strip()] = m.group(2).strip()
    return d


def parse_links(s):
    """jukyushasho（タイトル）、sodan-shien（タイトル） → [(slug, title)]"""
    res = []
    for m in re.finditer(r"([A-Za-z0-9][A-Za-z0-9_-]*)\s*(?:[（(]([^）)]*)[）)])?", s or ""):
        res.append((m.group(1), m.group(2) or ""))
    return res


def load_articles():
    articles = []
    for fn in sorted(os.listdir(CONTENT_DIR)):
        if not fn.endswith(".md") or fn == ABOUT_FILE:
            continue
        text = open(os.path.join(CONTENT_DIR, fn), encoding="utf-8").read().replace("\r\n", "\n")
        matches = list(SETTING_RE.finditer(text))
        for i, m in enumerate(matches):
            st = parse_settings(m.group(1))
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[m.end():end]
            # 記事の区切り線（----------）より後ろは次の記事のもの
            body = re.split(r"\n-{6,}\s*\n", body)[0].strip()
            h1 = ""
            mh = re.match(r"^#\s+(.+)\n", body + "\n")
            if mh:
                h1 = mh.group(1).strip()
                body = body[mh.end():].strip()
            slug = st.get("スラッグ") or ""
            if not slug:
                url = st.get("URL", "")
                slug = os.path.splitext(os.path.basename(url))[0]
            if not slug:
                print(f"警告: スラッグがない記事を飛ばしました ({fn})", file=sys.stderr)
                continue
            title_full = st.get("タイトル", h1)
            title = re.sub(r"｜" + SITE_NAME + r"$", "", title_full).strip()
            articles.append({
                "file": fn,
                "num": int(re.sub(r"\D", "", st.get("記事番号", "0")) or 0),
                "slug": slug,
                "path": f"/blog/{slug}.html",
                "title_full": title_full if title_full.endswith(SITE_NAME) else f"{title_full}｜{SITE_NAME}",
                "title": title,
                "h1": h1 or title,
                "description": st.get("説明文", ""),
                "category": st.get("カテゴリ", ""),
                "links": parse_links(st.get("つなぐ記事", "")),
                "body": body,
                "guide": fn == GUIDE_FILE,
            })
    return articles


def article_pref(a):
    """記事が関係する都道府県スラッグ（なければ None）"""
    if a["category"] == "都道府県のあずけ先":
        if a["slug"] in PREF_NAME:
            return a["slug"]
        for s, n, _ in PREFS:
            if a["title"].startswith(n) or a["title"].startswith(n.rstrip("都府県")):
                return s
    if a["category"] == "市ごとのあずけ先":
        for city, pref in sorted(CITY_PREF.items(), key=lambda x: -len(x[0])):
            if a["title"].startswith(city):
                return pref
    return None


# ---------------------------------------------------------------- 施設データ
def load_facilities():
    if not os.path.exists(FACILITY_FILE):
        return None
    with open(FACILITY_FILE, encoding="utf-8") as f:
        data = json.load(f)
    # 同じ意味のキーをそろえる
    for fac in data.get("facilities", []):
        sup = fac.get("supports") or {}
        if "tubeFeeding" in sup and "tube" not in sup:
            sup["tube"] = sup.pop("tubeFeeding")
        elif "tubeFeeding" in sup:
            sup.pop("tubeFeeding")
    return data


def safe_id(s):
    s = re.sub(r"[^A-Za-z0-9_-]+", "-", str(s)).strip("-")
    return s or "x"


def facility_path(f):
    return f"/facility/{f['pref']}/{safe_id(f['id'])}.html"


def support_on(v):
    if isinstance(v, dict):
        st = str(v.get("status", "")).strip().lower()
    else:
        st = str(v).strip().lower()
    return st not in SUPPORT_NEGATIVE


def type_labels(types):
    return [TYPE_LABELS.get(t, t) for t in (types or [])]


def tags_html(labels, cls="tag"):
    return "".join(f'<span class="{cls}">{esc(l)}</span>' for l in labels)


def facility_card(f):
    supports = [SUPPORT_LABELS.get(k, k) for k, v in (f.get("supports") or {}).items() if support_on(v)]
    rows = []
    if f.get("area"):
        rows.append(f'<p class="fac-area">{esc(f["area"])}</p>')
    rows.append(f'<p class="tags">{tags_html(type_labels(f.get("types")))}</p>')
    if f.get("age"):
        rows.append(f'<p class="fac-meta">対象：{esc(str(f["age"]))}</p>')
    if f.get("summary"):
        rows.append(f'<p>{esc(f["summary"])}</p>')
    if supports:
        rows.append(f'<p class="tags">{tags_html(supports, "tag tag-soft")}</p>')
    rows.append(f'<p class="more"><a href="{facility_path(f)}">くわしく<span class="visually-hidden">（{esc(f["name"])}）</span></a></p>')
    return f'<li class="card fac-card"><h3>{esc(f["name"])}</h3>' + "".join(rows) + "</li>"


def fmt_value(v):
    if isinstance(v, bool):
        return "あり" if v else "なし"
    if isinstance(v, list):
        return "、".join(fmt_value(x) for x in v)
    if isinstance(v, dict):
        return "、".join(f"{k}：{fmt_value(x)}" for k, x in v.items())
    return str(v)


def link_or_text(label, url):
    if url and re.match(r"^https?://", str(url)):
        return f'<a href="{esc(str(url))}" rel="noopener">{esc(str(label or url))}</a>'
    return esc(str(label or url or ""))


def build_facility_detail(f, prefinfo):
    pref = f["pref"]
    pname = prefinfo.get("name") or PREF_NAME.get(pref, pref)
    crumbs = [("トップ", "/"), (pname, f"/{pref}/"), (f["name"], facility_path(f))]
    dl = []

    def row(k, v):
        if v not in (None, "", [], {}):
            dl.append(f"<dt>{esc(k)}</dt><dd>{v}</dd>")

    row("地域", esc(str(f.get("area", ""))))
    row("サービスの種類", tags_html(type_labels(f.get("types"))) if f.get("types") else "")
    row("対象年齢", esc(str(f.get("age", ""))) if f.get("age") else "")
    row("ひとこと", esc(str(f.get("summary", ""))) if f.get("summary") else "")
    row("利用の条件", esc(fmt_value(f["condition"])) if f.get("condition") else "")
    row("利用までの流れ", esc(fmt_value(f["flow"])) if f.get("flow") else "")
    if f.get("medical") not in (None, ""):
        row("医療的ケア", esc(fmt_value(f["medical"])))
    row("医療的ケアについて", esc(str(f.get("medicalNote", ""))) if f.get("medicalNote") else "")
    if f.get("phone"):
        tel = re.sub(r"[^0-9+]", "", str(f["phone"]))
        row("電話", f'<a href="tel:{esc(tel)}">{esc(str(f["phone"]))}</a>' if tel else esc(str(f["phone"])))
    row("確認日", esc(str(f.get("checked", ""))) if f.get("checked") else "")

    sup_html = ""
    sups = f.get("supports") or {}
    if sups:
        items = []
        for k, v in sups.items():
            label = SUPPORT_LABELS.get(k, k)
            if isinstance(v, dict):
                st = str(v.get("status", ""))
                parts = [esc(SUPPORT_STATUS_LABELS.get(st.lower(), st))] if st else []
                if v.get("note"):
                    parts.append(esc(str(v["note"])))
                if v.get("source"):
                    src = v["source"]
                    if isinstance(src, (list, tuple)) and len(src) == 2:
                        parts.append("出典：" + link_or_text(src[0], src[1]))
                    else:
                        parts.append("出典：" + link_or_text(src, src))
                if v.get("checked"):
                    parts.append(f"確認日：{esc(str(v['checked']))}")
                for ek, ev in v.items():
                    if ek not in ("status", "note", "source", "checked") and ev not in (None, "", [], {}):
                        parts.append(f"{esc(ek)}：{esc(fmt_value(ev))}")
                txt = "<br>".join(parts)
            else:
                txt = esc(SUPPORT_STATUS_LABELS.get(str(v).lower(), fmt_value(v)))
            items.append(f"<dt>{esc(label)}</dt><dd>{txt}</dd>")
        sup_html = '<h2>お子様の状態ごとの受け入れ</h2><dl class="info">' + "".join(items) + "</dl>"

    src_html = ""
    if f.get("sources"):
        lis = []
        for s in f["sources"]:
            if isinstance(s, (list, tuple)):
                lis.append("<li>" + link_or_text(s[0] if s else "", s[1] if len(s) > 1 else "") + "</li>")
            elif isinstance(s, dict):
                lis.append("<li>" + link_or_text(s.get("label"), s.get("url")) + "</li>")
            else:
                lis.append("<li>" + link_or_text(s, s) + "</li>")
        src_html = "<h2>出典</h2><ul>" + "".join(lis) + "</ul>"

    body = f"""<article class="prose">
<h1>{esc(f['name'])}</h1>
<p class="notice">{FACILITY_NOTE}</p>
<h2>施設のこと</h2>
<dl class="info">{''.join(dl)}</dl>
{sup_html}
{src_html}
<p class="notice">{FACILITY_NOTE}</p>
<p><a href="/{pref}/">{esc(pname)}のページにもどる</a>　<a href="/search/">ほかの施設をさがす</a></p>
</article>"""
    desc = f"{pname}{('・' + f['area']) if f.get('area') else ''}の{f['name']}。" + (f.get("summary") or "") + FACILITY_NOTE + "。"
    write_page(facility_path(f), page(f["name"], desc[:160], facility_path(f), body, crumbs=crumbs))


# ---------------------------------------------------------------- ページ生成
def article_list_html(arts, cls="link-list"):
    return f'<ul class="{cls}">' + "".join(
        f'<li><a href="{a["path"]}">{esc(a["h1"])}</a></li>' for a in arts) + "</ul>"


def build_article(a, by_slug):
    cat = a["category"]
    cat_path = f"/category/{CAT_SLUG[cat]}/" if cat in CAT_SLUG else "/blog/"
    crumbs = [("トップ", "/"), (cat or "よみもの", cat_path), (a["title"], a["path"])]
    related = []
    for slug, t in a["links"]:
        r = by_slug.get(slug)
        if r and r["slug"] != a["slug"]:
            related.append(article_card(r))
        else:
            print(f"警告: つなぐ記事が見つかりません {a['slug']} → {slug}", file=sys.stderr)
    rel_html = ('<aside class="related" aria-labelledby="rel-h"><h2 id="rel-h">あわせて読みたい</h2><ul class="a-cards">'
                + "".join(related) + "</ul></aside>") if related else ""
    pref = article_pref(a)
    pref_box = ""
    if pref:
        pref_box = (f'<p class="pref-box"><a href="/{pref}/">{esc(PREF_NAME[pref])}のページを見る'
                    f'（施設の一覧・相談先）</a></p>')
    body_html, toc = add_heading_ids(md_to_html(a["body"]))
    toc_html = ""
    if len(toc) >= 2:
        toc_html = ('<nav class="toc" aria-labelledby="toc-h"><p class="toc-title" id="toc-h">この記事でわかること</p><ul>'
                    + "".join(f'<li><a href="#{i}">{esc(t)}</a></li>' for i, t in toc) + "</ul></nav>")
    body = f"""<article class="prose">
<header class="article-head">
<p class="cat-label"><a href="{cat_path}">{esc(cat)}</a></p>
<h1>{esc(a['h1'])}</h1>
<p class="updated">更新日：<time datetime="{BUILD_DATE}">{jp_date(BUILD_DATE)}</time></p>
</header>
{toc_html}
{body_html}
{pref_box}
</article>
<p class="cta-box"><a href="/search/"><span class="cta-text">お住まいの地域のあずけ先をさがす →</span><span class="cta-sub">都道府県や、お子様に必要なケアからさがせます</span></a></p>
{rel_html}"""
    ld = {
        "@context": "https://schema.org", "@type": "Article",
        "headline": a["h1"], "description": a["description"],
        "inLanguage": "ja", "mainEntityOfPage": abs_url(a["path"]),
        "datePublished": BUILD_DATE, "dateModified": BUILD_DATE,
        "author": {"@type": "Organization", "name": SITE_NAME, "url": abs_url("/about/")},
        "publisher": {"@type": "Organization", "name": "株式会社Bright Future Family"},
    }
    write_page(a["path"], page(a["title"], a["description"], a["path"], body, crumbs=crumbs,
                               og_type="article", extra_ld=ld, full_title=a["title_full"]))


def article_card(r):
    return (f'<li><a class="a-card" href="{r["path"]}"><span class="a-card-title">{esc(r["h1"])}</span>'
            f'<span class="a-card-desc">{esc(r["description"])}</span></a></li>')


def pref_grid_html(hlevel=3):
    parts = []
    for ri, rname in enumerate(REGIONS):
        links = "".join(f'<li><a href="/{s}/">{esc(n)}</a></li>' for s, n, r in PREFS if r == ri)
        parts.append(f'<div class="region"><h{hlevel} class="region-name">{esc(rname)}</h{hlevel}>'
                     f'<ul class="pref-list">{links}</ul></div>')
    return '<div class="regions">' + "".join(parts) + "</div>"


QUICK_SUPPORTS = ["medical", "pimd", "ventilator", "tube", "suction", "behavior"]


def about_excerpt():
    """運営者情報の「このサイトを作った理由」のはじめの2文"""
    text = open(os.path.join(CONTENT_DIR, ABOUT_FILE), encoding="utf-8").read()
    sec = text.split("作った理由", 1)[-1]
    paras = [p.strip() for p in sec.split("\n") if p.strip() and not p.startswith(("#", "-", "【"))]
    sents = re.findall(r"[^。]+。", "".join(paras[:2]))
    return "".join(sents[:2])


def quick_search_html(fac_data):
    pref_opts = "".join(f'<option value="{s}">{esc(n)}</option>' for s, n, _ in PREFS)
    type_chips = '<label class="chip"><input type="radio" name="type" value="" checked><span>こだわらない</span></label>' + "".join(
        f'<label class="chip"><input type="radio" name="type" value="{k}"><span>{esc(v)}</span></label>'
        for k, v in TYPE_LABELS.items())
    sup_chips = "".join(
        f'<label class="chip"><input type="checkbox" name="support" value="{k}"><span>{esc(SUPPORT_LABELS[k])}</span></label>'
        for k in QUICK_SUPPORTS if k in SUPPORT_LABELS)
    has = "1" if fac_data else "0"
    return f"""<form id="quick-search" class="finder" action="/search/" method="get" data-facilities="{has}" aria-labelledby="finder-h">
  <h2 id="finder-h" class="finder-title">あずけ先をさがす</h2>
  <div class="finder-field finder-pref">
    <label for="qs-pref" class="finder-label">お住まいの都道府県</label>
    <select id="qs-pref" name="pref"><option value="">えらんでください</option>{pref_opts}</select>
  </div>
  <fieldset class="finder-field">
    <legend class="finder-label">使いたい支援</legend>
    <div class="chip-row">{type_chips}</div>
  </fieldset>
  <fieldset class="finder-field">
    <legend class="finder-label">お子様の状態<span class="finder-hint">（いくつでも）</span></legend>
    <div class="chip-row">{sup_chips}</div>
  </fieldset>
  <p class="finder-submit"><button type="submit" class="button">この条件でさがす</button></p>
</form>
<script>
(function () {{
  var f = document.getElementById("quick-search");
  if (!f || f.getAttribute("data-facilities") === "1") return;
  f.addEventListener("submit", function (e) {{
    e.preventDefault();
    var p = f.elements.pref.value;
    location.href = p ? "/" + p + "/" : "/search/";
  }});
}})();
</script>"""


def build_top(articles, by_cat, fac_data):
    guides = [a for a in articles if a["guide"]]
    cards = "".join(article_card(a) for a in guides)
    tiles = []
    for name, slug in CATEGORIES:
        arts = by_cat.get(name, [])
        if not arts:
            continue
        tiles.append(f'<li><a class="tile" href="/category/{slug}/">{icon_svg(slug)}'
                     f'<span class="tile-name">{esc(name)}</span><span class="tile-count">{len(arts)}本</span></a></li>')
    body = f"""<div class="top-intro">
<h1 class="top-title">{SITE_SUBTITLE}</h1>
<p class="trust">自治体や施設の公式情報をもとに、やさしくまとめています</p>
</div>
{quick_search_html(fac_data)}

<section class="top-sec" aria-labelledby="h-guide">
<h2 id="h-guide" class="sec-title">はじめての方へ</h2>
<ul class="a-cards a-cards-3">{cards}</ul>
</section>

<section class="top-sec" aria-labelledby="h-cat">
<h2 id="h-cat" class="sec-title">よみもの</h2>
<ul class="tiles">{''.join(tiles)}</ul>
<p class="more"><a href="/blog/">よみものの一覧を見る</a></p>
</section>

<section id="prefectures" class="top-sec" aria-labelledby="h-pref">
<h2 id="h-pref" class="sec-title">都道府県からさがす</h2>
<p class="sec-lead">相談先や施設の一覧、まとめの記事を見られます。</p>
{pref_grid_html()}
</section>

<section class="top-sec owner" aria-labelledby="h-owner">
<h2 id="h-owner" class="sec-title">運営者より</h2>
<p class="owner-text">{esc(about_excerpt())}</p>
<p class="owner-sign">藤川海美（株式会社Bright Future Family）</p>
<p class="more"><a href="/about/">このサイトを作った理由を読む</a></p>
</section>"""
    ld = {"@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME,
          "url": abs_url("/"), "inLanguage": "ja", "description": SITE_SUBTITLE}
    write_page("/", page(SITE_NAME, f"{SITE_SUBTITLE}。短期入所や日中一時支援などのあずけ先を、都道府県や必要なケアからさがせます。",
                         "/", body, extra_ld=ld, wide=True))


def build_blog_index(by_cat):
    secs = []
    for name, slug in CATEGORIES:
        arts = sorted(by_cat.get(name, []), key=lambda x: x["num"])
        if arts:
            secs.append(f'<section><h2 id="{slug}"><a href="/category/{slug}/">{esc(name)}</a></h2>{article_list_html(arts)}</section>')
    toc = "".join(f'<li><a href="#{s}">{esc(n)}</a></li>' for n, s in CATEGORIES if by_cat.get(n))
    body = f'<h1>よみもの</h1><nav aria-label="カテゴリ"><ul class="chips">{toc}</ul></nav>' + "".join(secs)
    crumbs = [("トップ", "/"), ("よみもの", "/blog/")]
    write_page("/blog/", page("よみもの", "あずけさき手帖の記事の一覧です。はじめての方へ、あずけ先の種類、お子様の状態別、家族の暮らし、18歳から先のこと、都道府県・市ごとのあずけ先。",
                              "/blog/", body, crumbs=crumbs))


def build_categories(by_cat):
    for name, slug in CATEGORIES:
        arts = sorted(by_cat.get(name, []), key=lambda x: x["num"])
        path = f"/category/{slug}/"
        items = "".join(f'<li><a href="{a["path"]}"><span class="li-title">{esc(a["h1"])}</span></a>'
                        f'<p class="li-desc">{esc(a["description"])}</p></li>' for a in arts)
        body = (f'<header class="cat-head">{icon_svg(slug, "cat-icon cat-icon-lg")}<h1>{esc(name)}</h1>'
                f'<p class="small">{len(arts)}本の記事があります。</p></header><ul class="article-list">{items}</ul>')
        crumbs = [("トップ", "/"), ("よみもの", "/blog/"), (name, path)]
        write_page(path, page(name, f"あずけさき手帖の「{name}」の記事の一覧です。", path, body, crumbs=crumbs))


def build_prefs(articles, fac_data):
    pref_info = {}
    facs_by_pref = {}
    if fac_data:
        for p in fac_data.get("prefectures", []):
            if p.get("slug"):
                pref_info[p["slug"]] = p
        for f in fac_data.get("facilities", []):
            if f.get("pref") not in PREF_NAME or not f.get("id") or not f.get("name"):
                print(f"警告: pref/id/name が足りない施設を飛ばしました: {f.get('id')} {f.get('name')}", file=sys.stderr)
                continue
            facs_by_pref.setdefault(f.get("pref"), []).append(f)
    for slug, name, ri in PREFS:
        path = f"/{slug}/"
        info = pref_info.get(slug, {})
        matome = [a for a in articles if a["category"] == "都道府県のあずけ先" and article_pref(a) == slug]
        cities = [a for a in articles if a["category"] == "市ごとのあずけ先" and article_pref(a) == slug]
        jumps = [("#center", "相談先")]
        if matome or cities:
            jumps.append(("#articles", "まとめの記事"))
        jumps.append(("#facilities", "施設の一覧"))
        parts = [f'<header class="pref-head"><p class="pref-region">{esc(REGIONS[ri])}</p>'
                 f"<h1>{esc(name)}のあずけ先</h1>"
                 f'<p class="pref-lead">{esc(name)}で、障害のあるお子様が使えるあずけ先と、相談先をまとめています。</p>'
                 f'<nav class="jump" aria-label="このページの中"><ul class="chips">'
                 + "".join(f'<li><a href="{h}">{t}</a></li>' for h, t in jumps) + "</ul></nav></header>",
                 f'<p class="notice">{FACILITY_NOTE}</p>']
        # 医療的ケア児支援センター
        c = info.get("center") or {}
        parts.append('<h2 id="center">医療的ケア児支援センター</h2>')
        if c.get("name"):
            ctext = [f'<p class="center-name">{link_or_text(c["name"], c.get("url"))}</p>']
            if c.get("note"):
                ctext.append(f"<p>{esc(str(c['note']))}</p>")
            for k, lab in (("phone", "電話"), ("address", "住所"), ("hours", "受付時間")):
                if c.get(k):
                    ctext.append(f"<p>{lab}：{esc(str(c[k]))}</p>")
            srcs = []
            if c.get("source"):
                srcs.append("出典：" + link_or_text(c["source"], c["source"]) if re.match(r"^https?://", str(c["source"])) else "出典：" + esc(str(c["source"])))
            if c.get("sourceAsOf"):
                srcs.append(f"確認日：{esc(str(c['sourceAsOf']))}")
            if srcs:
                ctext.append(f'<p class="small">{"　".join(srcs)}</p>')
            parts.append('<div class="box center-box">' + "".join(ctext) + "</div>")
        else:
            parts.append(f'<p class="box center-box">{esc(name)}の医療的ケア児支援センターの情報は、ただいま整理しています。'
                         f'くわしくは「<a href="/blog/iryocare-center.html">医療的ケア児支援センター</a>」の記事もご覧ください。</p>')
        if info.get("resources"):
            lis = []
            for r in info["resources"]:
                t = link_or_text(r.get("label"), r.get("url"))
                extra = []
                if r.get("note"):
                    extra.append(esc(str(r["note"])))
                if r.get("checked"):
                    extra.append(f"確認日：{esc(str(r['checked']))}")
                lis.append(f"<li>{t}" + (f'<br><span class="small">{"　".join(extra)}</span>' if extra else "") + "</li>")
            parts.append("<h2>公式の相談先・案内</h2><ul>" + "".join(lis) + "</ul>")
        if matome or cities:
            parts.append('<h2 id="articles">まとめの記事</h2><ul class="a-cards">'
                         + "".join(article_card(a) for a in matome + cities) + "</ul>")
        # 施設一覧
        parts.append('<h2 id="facilities">施設の一覧</h2>')
        if fac_data is None:
            parts.append('<p class="box">施設の一覧は、ただいま準備しています。それまでは、上のまとめの記事や、お住まいの市区町村の窓口をご覧ください。</p>')
        else:
            facs = sorted(facs_by_pref.get(slug, []), key=lambda f: (f.get("area") or "", f.get("name") or ""))
            if facs:
                parts.append(f"<p>{len(facs)}か所をのせています。</p>")
                parts.append('<ul class="fac-list">' + "".join(facility_card(f) for f in facs) + "</ul>")
            else:
                parts.append('<p class="box">この県の施設は、ただいま整理しています。まとめの記事や、お住まいの市区町村の窓口もご覧ください。</p>')
            for f in facs:
                build_facility_detail(f, info or {"name": name})
        parts.append('<p class="more"><a href="/search/">条件をえらんで施設をさがす</a></p>')
        crumbs = [("トップ", "/"), (name, path)]
        desc = f"{name}で、重い障害や医療的ケアのあるお子様をあずけられる短期入所・日中一時支援などの施設と、医療的ケア児支援センターなどの相談先をまとめています。"
        write_page(path, page(f"{name}の障害児のあずけ先・短期入所", desc, path,
                              '<div class="prose">' + "".join(parts) + "</div>", crumbs=crumbs))


def build_search(fac_data):
    path = "/search/"
    crumbs = [("トップ", "/"), ("施設さがし", path)]
    if fac_data is None:
        body = """<div class="prose"><h1>施設さがし</h1>
<p class="box">施設のデータは、ただいま準備しています。それまでは、都道府県のページやまとめの記事をご覧ください。</p>
<p id="pref-jump" class="pref-box" hidden></p>
<h2>都道府県からさがす</h2>""" + pref_grid_html() + "</div>"
        names = json.dumps({s: n for s, n, _ in PREFS}, ensure_ascii=False)
        script = f"""<script>
(function () {{
  var names = {names};
  var p = new URLSearchParams(location.search).get("pref");
  var el = document.getElementById("pref-jump");
  if (!p || !names[p] || !el) return;
  var a = document.createElement("a");
  a.href = "/" + p + "/";
  a.textContent = names[p] + "のページを見る（相談先・まとめの記事）";
  el.appendChild(a);
  el.hidden = false;
}})();
</script>
"""
        write_page(path, page("施設さがし", "あずけさき手帖の施設さがしのページです。", path, body, crumbs=crumbs, scripts=script))
        return
    facs = [f for f in fac_data.get("facilities", []) if f.get("pref") in PREF_NAME and f.get("id") and f.get("name")]
    used_sup = []
    for f in facs:
        for k, v in (f.get("supports") or {}).items():
            if support_on(v) and k not in used_sup:
                used_sup.append(k)
    used_types = []
    for f in facs:
        for t in f.get("types") or []:
            if t not in used_types:
                used_types.append(t)
    used_types.sort(key=lambda t: list(TYPE_LABELS).index(t) if t in TYPE_LABELS else 99)
    index = {
        "prefs": {s: n for s, n, _ in PREFS},
        "types": {t: TYPE_LABELS.get(t, t) for t in used_types},
        "supports": {k: SUPPORT_LABELS.get(k, k) for k in used_sup},
        "items": [{
            "id": safe_id(f["id"]), "pref": f.get("pref"), "name": f.get("name"), "area": f.get("area", ""),
            "types": f.get("types") or [],
            "support": [k for k, v in (f.get("supports") or {}).items() if support_on(v)],
        } for f in facs],
    }
    os.makedirs(os.path.join(OUT_DIR, "search"), exist_ok=True)
    with open(os.path.join(OUT_DIR, "search", "index.json"), "w", encoding="utf-8") as fp:
        json.dump(index, fp, ensure_ascii=False, separators=(",", ":"))
    pref_opts = "".join(f'<option value="{s}">{esc(n)}</option>' for s, n, _ in PREFS)
    type_opts = "".join(f'<option value="{t}">{esc(TYPE_LABELS.get(t, t))}</option>' for t in used_types)
    sup_boxes = "".join(
        f'<label class="check"><input type="checkbox" name="support" value="{esc(k)}"> {esc(SUPPORT_LABELS.get(k, k))}</label>'
        for k in used_sup)
    body = f"""<div class="prose">
<h1>施設さがし</h1>
<p>都道府県や、使いたい支援、お子様に必要なケアをえらんでください。</p>
<p class="notice">{FACILITY_NOTE}</p>
<form id="search-form" class="search-form" role="search" onsubmit="return false">
  <div class="field"><label for="f-pref">都道府県</label>
    <select id="f-pref" name="pref"><option value="">すべて</option>{pref_opts}</select></div>
  <div class="field"><label for="f-type">使いたい支援</label>
    <select id="f-type" name="type"><option value="">すべて</option>{type_opts}</select></div>
  {'<fieldset class="field"><legend>お子様に必要なこと（えらんだものすべてに合う施設）</legend>' + sup_boxes + '</fieldset>' if sup_boxes else ''}
  <div class="field"><label for="f-q">名前・地域で しぼりこむ</label>
    <input id="f-q" name="q" type="search" autocomplete="off"></div>
</form>
<p id="result-count" class="result-count" aria-live="polite"></p>
<ul id="results" class="fac-list"></ul>
<noscript><p class="box">この検索はJavaScriptを使います。都道府県のページからも施設の一覧を見られます。</p></noscript>
<h2>都道府県からさがす</h2>
{pref_grid_html()}
</div>"""
    write_page(path, page("施設さがし", "都道府県・使いたい支援・必要なケアから、障害のあるお子様のあずけ先をさがせます。", path, body,
                          crumbs=crumbs, scripts='<script src="/static/search.js" defer></script>\n'))


def build_about():
    text = open(os.path.join(CONTENT_DIR, ABOUT_FILE), encoding="utf-8").read()
    text = SETTING_RE.sub("", text).strip()
    text = re.sub(r"^#\s+.+\n", "", text, count=1).strip()
    # 「お問い合わせ」ページへのリンク
    h = md_to_html(text).replace("「お問い合わせ」ページ", '「<a href="/contact/">お問い合わせ</a>」ページ', 1)
    body = f'<article class="prose"><h1>運営者情報</h1>{h}</article>'
    crumbs = [("トップ", "/"), ("運営者情報", "/about/")]
    write_page("/about/", page("運営者情報", "あずけさき手帖の運営者情報です。運営は株式会社Bright Future Family。サイトを作った理由や、情報の確かめ方をのせています。",
                               "/about/", body, crumbs=crumbs))


def build_contact():
    mail = esc(CONTACT_EMAIL)
    mail_html = f'<a href="mailto:{mail}">{mail}</a>' if "@" in CONTACT_EMAIL else mail
    body = f"""<article class="prose"><h1>お問い合わせ</h1>
<p>お問い合わせは、メールでお願いします。</p>
<p class="box">メールアドレス：{mail_html}</p>
<ul>
<li>内容のまちがいや、修正のご希望</li>
<li>施設の掲載・取り下げのご希望</li>
<li>そのほか、サイトについてのご意見</li>
</ul>
<p class="pref-box">施設・事業所の方へ：掲載プランや、のせている内容のご確認については「<a href="/for-facilities/">施設・事業所の方へ</a>」のページもご覧ください。</p>
<p>確認して、順番にお返事します。お返事まで数日かかることがあります。</p>
<p>このサイトは、医療や福祉の専門の相談窓口ではありません。お子様のことで迷ったときは、相談支援事業所、市区町村の窓口、医療的ケア児支援センターにご相談ください。</p>
</article>"""
    crumbs = [("トップ", "/"), ("お問い合わせ", "/contact/")]
    write_page("/contact/", page("お問い合わせ", "あずけさき手帖へのお問い合わせはメールで受けつけています。", "/contact/", body, crumbs=crumbs))


def build_for_facilities():
    path = "/for-facilities/"
    mail = esc(CONTACT_EMAIL)
    mail_html = f'<a href="mailto:{mail}">{mail}</a>' if "@" in CONTACT_EMAIL else mail
    rows = [  # (できること, 無料掲載, スタンダード, プラス)
        ("名前・場所・対象・ケアの内容・確かめた日", "○", "○", "○"),
        ("内容の修正（お問い合わせから）", "○", "○", "○"),
        ("写真（施設の中や外のようす）", "なし", "5枚まで", "15枚まで"),
        ("施設からのひとこと（紹介文）", "なし", "400字まで", "1,000字まで"),
        ("空き状況の目安（施設の方が更新）", "なし", "○", "○"),
        ("見学・相談の予約ボタン（施設のフォームや電話へ）", "なし", "○", "○"),
        ("お知らせ（見学会、職員さんの紹介など）", "なし", "月2件まで", "何件でも"),
        ("都道府県ページの「PR」枠での紹介", "なし", "なし", "○"),
        ("求人の掲載（準備中）", "なし", "なし", "1件まで料金なし"),
    ]

    def cell(v):
        if v == "○":
            return '<td class="yes"><span aria-hidden="true">○</span><span class="visually-hidden">あり</span></td>'
        cls = ' class="no"' if v == "なし" else ""
        t = esc(v).replace("まで料金", "まで<wbr>料金")
        if t.endswith("まで") and len(v) > 5:
            t = t[:-2] + "<wbr>まで"
        return f"<td{cls}>{t}</td>"
    trs = "".join(f"<tr><th scope=\"row\">{esc(r[0])}</th>{''.join(cell(v) for v in r[1:])}</tr>" for r in rows)
    table = f"""<div class="table-wrap" role="region" aria-label="プランのちがい（表）" tabindex="0"><table class="plan-table">
<thead><tr><th scope="col">できること</th><th scope="col">無料<wbr>掲載</th><th scope="col">スタン<wbr>ダード</th><th scope="col">プラス</th></tr>
<tr class="price-row"><th scope="row">月の料金（税込）</th><td>0円</td><td>3,300円</td><td>6,600円</td></tr></thead>
<tbody>{trs}</tbody></table></div>"""
    body = f"""<article class="prose">
<h1>施設・事業所の方へ</h1>
<p class="lead">掲載プランのご案内</p>
<p>{SITE_NAME}は、重い障害や医療的ケアのあるお子様のご家族が、あずけ先をさがすためのサイトです。短期入所、日中一時支援、ヘルパー、移動支援、療育などの施設をのせています。</p>
<p>訪問看護ステーション（お子様に対応しているところ）も、施設と同じプランでご利用いただけます。</p>
<div class="box free-box">
<p><strong>施設の基本の掲載は無料です。</strong>お申し込みがなくても、公式ページや市区町村の案内をもとに、施設の名前、場所、対象、ケアの内容、確かめた日をのせています。</p>
</div>
<p>もっとくわしく施設のことを伝えたい方のために、有料のプランもご用意しました。ご家族が「ここなら見学に行ってみたい」と思えるような情報を、施設の方ご自身の言葉でのせることができます。</p>

<h2 id="plans">プランのちがい</h2>
{table}
<p class="small">空き状況は「空きがある」「必ず使える」とは書かず、「〇月ごろ相談可」のような目安としてのせます。いちばん新しい更新日も、あわせて表示します。</p>

<h2 id="campaign">はじめのキャンペーン</h2>
<div class="box campaign-box">
<p class="campaign-title">はじめの3か月は、料金をいただきません</p>
<p>2027年3月31日までにお申し込みの施設は、はじめの3か月の料金はいただきません。4か月目から、えらんだプランの料金になります。3か月のあいだにやめられても、料金はかかりません。</p>
</div>

<h2 id="benefits">お申し込みでもらえるもの</h2>
<ul>
<li>施設ページに、写真や紹介文をのせる作業は、こちらでお手伝いします。原稿と写真を送っていただければ、3営業日ほどでのせます</li>
<li>空き状況やお知らせは、メールやフォームから送っていただければ、こちらで更新します</li>
<li>月に1回、施設ページが何回見られたかをお知らせします</li>
<li>契約は1か月ごとです。いつでもやめられます。やめたあとも、無料の掲載はそのまま残ります</li>
</ul>

<h2 id="flow">申し込みの流れ</h2>
<ol class="steps">
<li>メール（{mail_html}）の件名に「掲載プランについて」と書いて、施設の名前とご担当者様のお名前をお送りください</li>
<li>2営業日ほどで、こちらからメールでご連絡します。ご不明な点は、電話でもお答えします</li>
<li>写真と紹介文を送っていただき、こちらでページを作ります</li>
<li>施設の方に内容を見ていただき、よければ公開します</li>
</ol>
<p>お支払いは、毎月の請求書（銀行振込）を予定しています。</p>

<h2 id="promise">大切にしていること</h2>
<ul class="promise-list">
<li>有料プランでも、一覧の並び順は変わりません。ランキングもしません</li>
<li>目立つ場所での紹介には、かならず「PR」と表示します</li>
<li>ご家族からいただいた声を、施設の評価としてのせることはしません</li>
<li>料金をいただいているかどうかで、記事の中身を変えることはありません</li>
</ul>

<h2 id="kyujin">求人掲載（準備中）</h2>
<p>重症心身障害や医療的ケアのあるお子様を受け入れる施設の求人をのせるページを、準備しています。職種は、看護師、保育士、支援員（児童指導員など）、ヘルパーからはじめます。</p>
<ul>
<li>料金は、1件 月5,500円（税込）の予定です。プラスプランの施設は、1件まで料金はかかりません</li>
<li>応募は施設に直接していただく形です。{SITE_NAME}では、応募する方の情報をおあずかりしません</li>
<li>求人のページから、その施設のページへつなげます。「どんなお子様が通っているか」も、あわせて見ていただけます</li>
</ul>
<p>はじまったら、このページでお知らせします。</p>

<h2 id="contact">お問い合わせ</h2>
<p>掲載内容のまちがいや、取り下げのご希望も、こちらで受けつけています。ご不明な点は、お気軽にご連絡ください。</p>
<p class="box">メールアドレス：{mail_html}</p>
<p class="owner-sign"><span class="nw">株式会社Bright Future Family</span>　<span class="nw">{SITE_NAME}</span>　<span class="nw">代表 藤川海美</span></p>
</article>"""
    crumbs = [("トップ", "/"), ("施設・事業所の方へ", path)]
    write_page(path, page("施設・事業所の方へ（掲載プランのご案内）",
                          "あずけさき手帖の施設向けページです。施設の基本の掲載は無料。写真や空き状況をのせられる月ぎめの有料プラン（税込3,300円・6,600円）と、申し込みの流れをご案内します。",
                          path, body, crumbs=crumbs))


def build_privacy():
    body = f"""<article class="prose"><h1>プライバシーポリシー</h1>
<p>{SITE_NAME}（運営：株式会社Bright Future Family）は、このサイトを使う方の情報を、次のようにあつかいます。</p>
<h2>お問い合わせでいただく情報</h2>
<p>メールでいただいたお名前やメールアドレス、内容は、お返事と、サイトの内容を直すためだけに使います。法律で決められた場合をのぞき、ご本人の同意なく、ほかの人に渡すことはありません。</p>
<h2>アクセス解析について</h2>
<p>このサイトでは、Googleのアクセス解析ツール「Googleアナリティクス」を使っています。Googleアナリティクスは、Cookieを使って、どのページがどれくらい見られたかなどの情報を集めます。この情報に、お名前など個人を特定するものはふくまれません。Cookieは、ブラウザの設定で使わないようにできます。くわしくは、<a href="https://policies.google.com/technologies/partner-sites?hl=ja" rel="noopener">Googleのポリシーと規約</a>をご覧ください。</p>
<h2>広告について</h2>
<p>一部の記事には広告（PR）がふくまれます。広告がある場所には「PR」と表示しています。</p>
<p>{SITE_NAME}は、Amazon.co.jpを宣伝しリンクすることによってサイトが紹介料を獲得できる手段を提供することを目的に設定されたアフィリエイトプログラムである、Amazonアソシエイト・プログラムの参加者です。Amazonのアソシエイトとして、{SITE_NAME}は適格販売により収入を得ています。</p>
<h2>のせている情報について</h2>
<p>施設や制度の情報は、公式の情報をもとに整理しています。内容が変わっていることもあります。空きや受け入れは、各施設にご確認ください。</p>
<h2>このページの変更</h2>
<p>このページの内容は、必要に応じて変えることがあります。</p>
<p>お問い合わせは、<a href="/contact/">お問い合わせ</a>ページからお願いします。</p>
</article>"""
    crumbs = [("トップ", "/"), ("プライバシーポリシー", "/privacy/")]
    write_page("/privacy/", page("プライバシーポリシー", "あずけさき手帖のプライバシーポリシーです。アクセス解析と広告（Amazonアソシエイト）について説明しています。",
                                 "/privacy/", body, crumbs=crumbs))


def build_404():
    body = """<div class="prose"><h1>ページが見つかりませんでした</h1>
<p>お探しのページは、移動したか、なくなった可能性があります。</p>
<p class="back-home"><a class="button" href="/">トップページへもどる</a></p>
<h2>こちらもご覧ください</h2>
<ul><li><a href="/">トップページへ</a></li><li><a href="/blog/">よみものの一覧</a></li><li><a href="/search/">施設さがし</a></li></ul>
<h2>都道府県からさがす</h2>""" + pref_grid_html() + "</div>"
    write_page("/404.html", page("ページが見つかりませんでした", "ページが見つかりませんでした。", "/404.html", body, noindex=True), sitemap=False)


def build_meta_files():
    urls = "".join(f"<url><loc>{esc(abs_url(p))}</loc><lastmod>{BUILD_DATE}</lastmod></url>\n" for p in PAGES)
    with open(os.path.join(OUT_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n")
    with open(os.path.join(OUT_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\n\nSitemap: {abs_url('/sitemap.xml')}\n")
    open(os.path.join(OUT_DIR, ".nojekyll"), "w").close()
    manifest = {
        "name": SITE_NAME, "short_name": SITE_NAME, "description": SITE_SUBTITLE,
        "lang": "ja", "start_url": "/", "scope": "/", "display": "browser",
        "background_color": "#f5f1e8", "theme_color": "#f5f1e8",
        "icons": [
            {"src": "/static/icons/apple-touch-icon.png", "sizes": "180x180", "type": "image/png"},
            {"src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
        ],
    }
    with open(os.path.join(OUT_DIR, "site.webmanifest"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------- main
def main():
    if os.path.exists(OUT_DIR):
        # CNAME は消さずに残す
        cname = os.path.join(OUT_DIR, "CNAME")
        keep = open(cname).read() if os.path.exists(cname) else None
        shutil.rmtree(OUT_DIR)
        os.makedirs(OUT_DIR)
        if keep is not None:
            open(cname, "w").write(keep)
    else:
        os.makedirs(OUT_DIR)
    shutil.copytree(STATIC_DIR, os.path.join(OUT_DIR, "static"))

    articles = load_articles()
    slugs = [a["slug"] for a in articles]
    dups = {s for s in slugs if slugs.count(s) > 1}
    if dups:
        sys.exit(f"エラー: スラッグが重複しています: {sorted(dups)}")
    unknown = {a["category"] for a in articles} - set(CAT_SLUG)
    if unknown:
        print(f"警告: 知らないカテゴリ: {unknown}", file=sys.stderr)
    by_slug = {a["slug"]: a for a in articles}
    by_cat = {}
    for a in articles:
        by_cat.setdefault(a["category"], []).append(a)

    fac_data = load_facilities()
    if fac_data is None:
        print("お知らせ: data/azukesaki_facilities.json がないので、施設の一覧なしで作ります。")

    for a in articles:
        build_article(a, by_slug)
    build_top(articles, by_cat, fac_data)
    build_blog_index(by_cat)
    build_categories(by_cat)
    build_prefs(articles, fac_data)
    build_search(fac_data)
    build_about()
    build_contact()
    build_for_facilities()
    build_privacy()
    build_404()
    build_meta_files()
    nfac = sum(1 for p in PAGES if p.startswith("/facility/"))
    print(f"完了: 記事 {len(articles)} 本 / 施設 {nfac} 件 / sitemap {len(PAGES)} URL → {OUT_DIR}")


if __name__ == "__main__":
    main()
