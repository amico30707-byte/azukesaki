/* あずけさき手帖 施設さがし（外部ライブラリなし） */
(function () {
  "use strict";
  var form = document.getElementById("search-form");
  var list = document.getElementById("results");
  var countEl = document.getElementById("result-count");
  if (!form || !list) return;
  var data = null;

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
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

  function render() {
    if (!data) return;
    var pref = form.pref.value;
    var type = form.type.value;
    var q = (form.q.value || "").trim();
    var sups = Array.prototype.map.call(form.querySelectorAll('input[name="support"]:checked'), function (b) { return b.value; });
    writeParams(pref, type, sups, q);
    var hits = data.items.filter(function (it) {
      if (pref && it.pref !== pref) return false;
      if (type && it.types.indexOf(type) === -1) return false;
      for (var i = 0; i < sups.length; i++) if (it.support.indexOf(sups[i]) === -1) return false;
      if (q && (it.name + " " + it.area + " " + (data.prefs[it.pref] || "")).indexOf(q) === -1) return false;
      return true;
    });
    var shown = hits.slice(0, 200);
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
    countEl.textContent = hits.length === 0
      ? "条件に合う施設が見つかりませんでした。条件を少しへらしてみてください。"
      : hits.length + "か所が見つかりました" + (hits.length > shown.length ? "（はじめの" + shown.length + "か所を表示）" : "") + "。";
  }

  readParams();
  form.addEventListener("change", render);
  form.addEventListener("input", render);
  countEl.textContent = "読みこみ中です…";
  fetch("/search/index.json")
    .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then(function (j) { data = j; render(); })
    .catch(function () { countEl.textContent = "施設のデータを読みこめませんでした。都道府県のページからご覧ください。"; });
})();
