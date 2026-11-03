# あずけさき手帖（静的サイト）

重い障害のあるお子様の、あずけ先さがしと将来のじゅんび。

## 作り方（ビルド）

```
pip install markdown --break-system-packages   # はじめの1回だけ
python3 build.py        # docs/ にサイトができます
python3 check_links.py  # サイト内のリンク切れを確かめます
```

GitHub Pages は「main ブランチの /docs」を公開するように設定します。

## 記事を直す・足すとき

- 記事は `content/` の .md ファイルにあります。直したら `python3 build.py` をもう一度実行します。
- 記事は【設定】〜【設定ここまで】（スラッグ・タイトル・説明文・カテゴリ・つなぐ記事）と本文のセットです。記事と記事のあいだは `----------` で区切ります。
- 「【Amazonリンク：あとで入れる】」などの「あとで入れる」は、ページには出ません。リンクができたら、本文を `[本の名前](https://...)` の形に書きかえてください。
- 運営者情報は `content/01_運営者情報.md`、トップの「はじめての方へ」カードは `content/02_はじめての方へ.md` の3本です。
- デザインは `static/style.css`、施設さがしの動きは `static/search.js` です。
- 「施設・事業所の方へ」（/for-facilities/：掲載プラン・申し込みの流れ・求人掲載の準備中のお知らせ）は `build.py` の `build_for_facilities()` にあります。料金やキャンペーンの期限を変えるときは、ここを直します。

## アイコンとOGP画像

- ファビコン・アプリのアイコン（`static/icons/`）と、SNSでシェアしたときの画像（`static/ogp.png`、1200×630）は `node make_images.js` で作ります（Playwright を使います）。ロゴやサイト名を変えたときだけ、もう一度実行します。
- OGP画像は全ページの `og:image`／`twitter:image` に入ります（`BASE_URL` をつけた絶対URL）。`site.webmanifest` は `build.py` が作ります。

## 設定（build.py の上のほう）

- `BASE_URL`：いまは `https://azukesaki.jp`。canonical・sitemap・OGP に使います。
- `CONTACT_EMAIL`：お問い合わせのメールアドレス。いまは「【メールアドレス】」のままです。

## 施設データ

- `data/azukesaki_facilities.json` に置くと、都道府県ページの施設一覧、施設ごとのページ（`/facility/<県>/<id>.html`）、施設さがし用の `/search/index.json` ができます。
- ファイルがないときは、施設の一覧の場所に「準備しています」と出して、ほかのページだけを作ります。
- 種類（types）や状態（supports）の日本語名は、`build.py` の `TYPE_LABELS`・`SUPPORT_LABELS` で足せます。

## ドメインの準備ができたら

- `docs/CNAME` を作り、中に `azukesaki.jp` と1行だけ書きます（いまはまだ作っていません）。`build.py` は CNAME を消さずに残します。
- GitHub の Settings → Pages で Custom domain を設定します。
