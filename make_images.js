// あずけさき手帖：ファビコン・アプリのアイコン・OGP画像を作る
// 使い方: node make_images.js   （static/icons/ と static/ogp.png ができます）
// ロゴやサイト名を変えたときだけ、もう一度実行します。
const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const OUT = path.join(__dirname, "static", "icons");
const PAPER = "#f5f1e8";

// build.py の LOGO_SVG と同じ形（32×32）
const MARK = `
<rect x="5" y="2.5" width="22" height="26" rx="3.2" fill="#24564a"/>
<rect x="5" y="2.5" width="5.5" height="26" rx="2.4" fill="#183f35"/>
<path d="M22.6 8.4c-5.6.6-8.6 4.4-8.3 10.6 5.4-.3 8.6-4 8.3-10.6z" fill="#f2c39c"/>
<path d="M14.9 18.6c1.6-3.1 3.6-5.6 6.2-7.6" stroke="#24564a" stroke-width="1.1" fill="none" stroke-linecap="round"/>
<path d="M21 28.5v3l1.6-1.3 1.6 1.3v-3z" fill="#e39a66"/>`;

// ファビコン（背景なし）
const FAVICON_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">${MARK}
</svg>
`;

// アプリのアイコン（紙の色の背景。まわりに余白をとる）
function appIconSvg(size) {
  // マークは 32 の中で x5〜27・y2.5〜31.5。中心をそろえて、全体の 62% ほどの大きさにする
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 32 32">
<rect width="32" height="32" fill="${PAPER}"/>
<g transform="translate(16 16) scale(0.62) translate(-16 -17)">${MARK}</g>
</svg>`;
}

const OGP_HTML = `<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><style>
html,body{margin:0;width:1200px;height:630px;overflow:hidden}
body{background:${PAPER};position:relative;
  font-family:"Hiragino Sans","Noto Sans CJK JP","Noto Sans JP",sans-serif;color:#23302c}
.page{position:absolute;inset:56px 72px 56px 96px;background:#fffdf8;border:2px solid #ddd5c4;
  border-radius:10px 26px 26px 10px;box-shadow:0 2px 0 #ddd5c4,0 30px 60px -36px rgba(35,48,44,.45);
  background-image:repeating-linear-gradient(to bottom,transparent 0 63px,rgba(36,86,74,.07) 63px 65px)}
.spine{position:absolute;left:0;top:0;bottom:0;width:34px;background:#24564a;border-radius:9px 0 0 9px}
.spine::after{content:"";position:absolute;left:20px;top:0;bottom:0;width:3px;
  background:repeating-linear-gradient(to bottom,transparent 0 18px,rgba(255,255,255,.35) 18px 28px)}
.ribbon{position:absolute;right:70px;top:-2px;width:30px;height:84px;background:#e8a06b;
  clip-path:polygon(0 0,100% 0,100% 100%,50% 80%,0 100%)}
.inner{position:absolute;left:110px;right:90px;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center}
.brand{display:flex;align-items:center;gap:24px;margin-left:-14px}
.brand svg{width:120px;height:120px;flex:none}
h1{margin:0;font-family:"Hiragino Mincho ProN","Noto Serif CJK JP","Noto Serif JP",serif;font-weight:700;
  font-size:84px;letter-spacing:.08em;line-height:1.2;color:#183f35;white-space:nowrap}
.rule{width:96px;height:5px;border-radius:3px;background:#24564a;margin:40px 0 30px}
p{margin:0;font-size:40px;line-height:1.6;letter-spacing:.06em;color:#23302c;font-weight:500}
</style></head><body><div class="page"><div class="spine"></div><div class="ribbon"></div>
<div class="inner"><div class="brand"><svg viewBox="0 0 32 32">${MARK}</svg><h1>あずけさき手帖</h1></div>
<div class="rule"></div>
<p>重い障害のあるお子様の、<br>あずけ先さがしと将来のじゅんび</p></div></div></body></html>`;

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(path.join(OUT, "favicon.svg"), FAVICON_SVG);
  const browser = await chromium.launch();
  const page = await browser.newPage({ deviceScaleFactor: 1 });

  // 32px は背景なし、180・512 は紙の色の背景
  const shots = [
    ["favicon-32.png", 32, FAVICON_SVG.replace("<svg ", '<svg width="32" height="32" '), true],
    ["apple-touch-icon.png", 180, appIconSvg(180), false],
    ["icon-512.png", 512, appIconSvg(512), false],
  ];
  for (const [name, size, svg, transparent] of shots) {
    await page.setViewportSize({ width: size, height: size });
    await page.setContent(`<html><body style="margin:0;background:transparent">${svg.replace(/width="\d+" height="\d+"/, `width="${size}" height="${size}"`)}</body></html>`);
    await page.screenshot({ path: path.join(OUT, name), omitBackground: transparent, clip: { x: 0, y: 0, width: size, height: size } });
  }

  await page.setViewportSize({ width: 1200, height: 630 });
  await page.setContent(OGP_HTML, { waitUntil: "load" });
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: path.join(__dirname, "static", "ogp.png"), clip: { x: 0, y: 0, width: 1200, height: 630 } });
  await browser.close();
  console.log("完了: static/icons/（favicon.svg, favicon-32.png, apple-touch-icon.png, icon-512.png）と static/ogp.png");
})();
