/* あずけさき手帖 施設さがし（外部ライブラリなし） */
(function () {
  "use strict";
  var form = document.getElementById("search-form");
  var list = document.getElementById("results");
  var countEl = document.getElementById("result-count");
  var helpEl = document.getElementById("no-result-help");
  if (!form || !list) return;
  var data = null;
  var MAX = 200;

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function hasParams() {
    var p = new URLSearchParams(location.search);
    return !!(p.get("pref") || p.get("type") || p.get("q") || p.getAll("support").length);
  }

  function readParams() {
    var p = new URLSearchParams(location.search);
    if (p.get("pref")) form.pref.value = p.get("pref");
    if (p.get("type")) form.type.value = p.get("type");
    if (p.get("q")) form.q.value = p.get("q");
    var sups = p.getAll("support");
    Array.prototype.forEach.call(form.querySelectorAll('input[name="support"]'), function (b) {
      b.checked = sups.indexOf(b.value) !== -1;
    });
  }

  function writeParams(pref, type, sups, q) {
    var p = new URLSearchParams();
    if (pref) p.set("pref", pref);
    if (type) p.set("type", type);
    sups.forEach(function (s) { p.append("support", s); });
    if (q) p.set("q", q);
    var qs = p.toString();
    history.replaceState(null, "", location.pathname + (qs ? "?" + qs : ""));
  }

  function scrollToResults() {
    if (!countEl) return;
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    countEl.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
  }

  function current() {
    return {
      pref: form.pref.value,
      type: form.type.value,
      q: (form.q.value || "").trim(),
      sups: Array.prototype.map.call(form.querySelectorAll('input[name="support"]:checked'), function (b) { return b.value; })
    };
  }

  function noResultHelp(c) {
    if (!helpEl) return;
    var items = [];
    if (c.type || c.sups.length) {
      items.push('<li><button type="button" class="button button-sub" data-clear="conditions">使いたい支援とお子様の状態の条件をはずす</button></li>');
    }
    if (c.q) {
      items.push('<li><button type="button" class="button button-sub" data-clear="q">名前・地域の言葉をはずす</button></li>');
    }
    if (c.pref && data.prefs[c.pref]) {
      var pn = esc(data.prefs[c.pref]);
      items.push('<li><a href="/' + esc(c.pref) + '/">' + pn + "のページを見る（施設の一覧・相談先）</a></li>");
      items.push('<li><a href="/' + esc(c.pref) + '/#center">' + pn + "の医療的ケア児支援センターを見る</a></li>");
    }
    items.push('<li><a href="/blog/iryocare-center.html">医療的ケア児支援センターとは（相談できること）</a></li>');
    items.push('<li><a href="/blog/sodan-shien.html">相談支援事業所に相談する</a></li>');
    helpEl.innerHTML = '<p>ここにのっていない施設もあります。次のこともためしてみてください。</p><ul class="help-list">' + items.join("") + "</ul>";
    helpEl.hidden = false;
  }

  function render() {
    if (!data) return;
    var c = current();
    writeParams(c.pref, c.type, c.sups, c.q);
    if (helpEl) { helpEl.hidden = true; helpEl.innerHTML = ""; }
    if (!c.pref && !c.type && !c.q && !c.sups.length) {
      list.innerHTML = "";
      countEl.textContent = "都道府県や条件をえらぶと、ここに施設が出ます（ぜんぶで" + data.items.length + "か所）。";
      return;
    }
    var hits = data.items.filter(function (it) {
      if (c.pref && it.pref !== c.pref) return false;
      if (c.type && it.types.indexOf(c.type) === -1) return false;
      for (var i = 0; i < c.sups.length; i++) if (it.support.indexOf(c.sups[i]) === -1) return false;
      if (c.q && (it.name + " " + it.area + " " + (it.addr || "") + " " + (data.prefs[it.pref] || "")).indexOf(c.q) === -1) return false;
      return true;
    });
    var shown = hits.slice(0, MAX);
    list.innerHTML = shown.map(function (it) {
      var types = it.types.map(function (t) { return '<span class="tag">' + esc(data.types[t] || t) + "</span>"; }).join("");
      var sp = it.support.map(function (s) { return '<span class="tag tag-soft">' + esc(data.supports[s] || s) + "</span>"; }).join("");
      var href = "/facility/" + encodeURIComponent(it.pref) + "/" + encodeURIComponent(it.id) + ".html";
      return '<li class="card fac-card"><h3>' + esc(it.name) + "</h3>" +
        (it.status ? '<p class="tags"><span class="tag tag-alert">' + esc(it.status) + "</span></p>" : "") +
        '<p class="fac-area">' + esc(data.prefs[it.pref] || "") + (it.area ? "・" + esc(it.area) : "") + "</p>" +
        '<p class="tags">' + types + "</p>" + (sp ? '<p class="tags">' + sp + "</p>" : "") +
        '<p class="more"><a href="' + href + '">くわしく<span class="visually-hidden">（' + esc(it.name) + "）</span></a></p></li>";
    }).join("");
    if (hits.length === 0) {
      countEl.textContent = "条件に合う施設が見つかりませんでした。条件を少しへらしてみてください。";
      noResultHelp(c);
    } else {
      countEl.textContent = hits.length + "か所が見つかりました" +
        (hits.length > shown.length ? "（はじめの" + shown.length + "か所を表示。都道府県や条件をえらぶと、しぼりこめます）" : "") + "。";
    }
  }

  if (helpEl) {
    helpEl.addEventListener("click", function (e) {
      var b = e.target.closest("button[data-clear]");
      if (!b) return;
      if (b.getAttribute("data-clear") === "conditions") {
        form.type.value = "";
        Array.prototype.forEach.call(form.querySelectorAll('input[name="support"]'), function (x) { x.checked = false; });
      } else {
        form.q.value = "";
      }
      render();
      scrollToResults();
    });
  }

  readParams();
  var scrollOnLoad = hasParams();
  form.addEventListener("change", render);
  form.addEventListener("input", render);
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    render();
    scrollToResults();
  });
  countEl.textContent = "読みこみ中です…";
  fetch("/search/index.json")
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (j) {
      data = j;
      render();
      if (scrollOnLoad) scrollToResults();
    })
    .catch(function () { countEl.textContent = "施設のデータを読みこめませんでした。都道府県のページからご覧ください。"; });
})();
