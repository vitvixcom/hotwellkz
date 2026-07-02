/* Геоподсказка города — только на общенациональных страницах (kazakhstan-*).
   Первый визит: по IP определяем ближайший из наших городов и предлагаем перейти
   на его страницу. Повторный визит: тонкая плашка «Ваш город». Выбор сохраняется.
   CSS инъектируется здесь же, чтобы не трогать общий style.css. */
(function () {
  "use strict";
  var page = (location.pathname.split('/').pop() || '').toLowerCase();
  if (page.indexOf('kazakhstan-') !== 0) return; // только национальные страницы

  var RULES = [
    ['sendvich', ['sendvich', 'sandvich']], ['sip', ['sip']], ['karkas', ['karkas']],
    ['bystro', ['bystrovozvod']], ['derevo', ['derevyan']], ['shchit', ['shitov', 'shchitov', 'shhitov']],
    ['dacha', ['dach']], ['kanada', ['kanadsk', 'canad']], ['kottedzh', ['kottedzh', 'cottage']],
    ['modul', ['moduln']], ['garazh', ['garazh']], ['banya', ['proekt-bani', '-bani', 'banya']],
    ['panel', ['panel']], ['pod-klyuch', ['pod-klyuch', 'stroitelstvo']]
  ];
  function catOf(slug) {
    for (var i = 0; i < RULES.length; i++) {
      for (var j = 0; j < RULES[i][1].length; j++) if (slug.indexOf(RULES[i][1][j]) >= 0) return RULES[i][0];
    }
    return null;
  }
  var CURCAT = catOf(page) || 'sip';
  var KEY = 'hw_city_choice', DISMISS = 'hw_geo_dismissed';
  var IDX = null;

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function haversine(a, b, c, d) {
    var R = 6371, p = Math.PI / 180, dLat = (c - a) * p, dLon = (d - b) * p;
    var s = Math.sin(dLat / 2) * Math.sin(dLat / 2) + Math.cos(a * p) * Math.cos(c * p) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return 2 * R * Math.asin(Math.sqrt(s));
  }
  function targetUrl(city) {
    if (!city || !city.pages) return null;
    return city.pages[CURCAT] || city.pages.sip || city.pages.karkas || city.pages['pod-klyuch'] || null;
  }
  function setDeliveryCity(name) { try { sessionStorage.setItem('hw_city', name); } catch (e) {} }
  function loadIndex(cb) {
    if (IDX) { cb(IDX); return; }
    fetch('city-index.json').then(function (r) { return r.json(); }).then(function (d) { IDX = d; cb(d); }).catch(function () { cb(null); });
  }
  function findCity(name) { if (!IDX) return null; for (var i = 0; i < IDX.cities.length; i++) if (IDX.cities[i].name === name) return IDX.cities[i]; return null; }
  function nearest(lat, lon) { var best = null, bd = 1e9; for (var i = 0; i < IDX.cities.length; i++) { var c = IDX.cities[i], dd = haversine(lat, lon, c.lat, c.lon); if (dd < bd) { bd = dd; best = c; } } return best; }

  function go(city) {
    try { localStorage.setItem(KEY, city.name); } catch (e) {}
    setDeliveryCity(city.name);
    var u = targetUrl(city);
    if (u) location.href = u; else closeAll();
  }

  function injectCss() {
    if (document.getElementById('hw-geo-css')) return;
    var s = document.createElement('style'); s.id = 'hw-geo-css';
    s.textContent =
      ".hw-geo{position:fixed;inset:0;z-index:1200;display:flex;align-items:flex-end;justify-content:center;background:rgba(20,22,16,.42);opacity:0;transition:opacity .22s ease}" +
      ".hw-geo.is-open{opacity:1}" +
      ".hw-geo__box{position:relative;width:100%;max-width:460px;background:#fff;border-radius:18px 18px 0 0;box-shadow:0 -8px 40px rgba(20,22,16,.28);padding:22px 20px 20px;transform:translateY(18px);transition:transform .24s cubic-bezier(.2,.8,.2,1);display:flex;gap:14px}" +
      ".hw-geo.is-open .hw-geo__box{transform:none}" +
      ".hw-geo__box--pick{flex-direction:column;gap:0;align-items:stretch}" +
      ".hw-geo__box--pick .hw-geo__list{max-height:min(50vh,440px)}" +
      "@media(min-width:560px){.hw-geo{align-items:center}.hw-geo__box{border-radius:18px}}" +
      ".hw-geo__x{position:absolute;top:10px;right:12px;background:none;border:0;font-size:1.7rem;line-height:1;color:#9a9a90;cursor:pointer;padding:2px 8px;border-radius:8px}" +
      ".hw-geo__x:hover{background:#f0efe9;color:#333}" +
      ".hw-geo__pin{flex:none;width:46px;height:46px;border-radius:50%;background:var(--c-badge,#e7efe0);color:var(--c-green,#4a6a2f);display:grid;place-items:center}" +
      ".hw-geo__main{flex:1;min-width:0}" +
      ".hw-geo__t{font-weight:800;font-size:1.12rem;color:var(--c-ink,#22241c);line-height:1.25}" +
      ".hw-geo__s{color:#6b6f62;margin-top:5px;font-size:.95rem}" +
      ".hw-geo__btns{display:flex;flex-direction:column;gap:9px;margin-top:15px}" +
      ".hw-geo__yes{background:var(--c-green,#4a6a2f);color:#fff;border:0;border-radius:12px;padding:13px 16px;font:inherit;font-weight:800;font-size:1rem;cursor:pointer}" +
      ".hw-geo__yes:hover{background:var(--c-green-600,#3e5a27)}" +
      ".hw-geo__other{background:#f2f1ea;color:var(--c-ink,#22241c);border:0;border-radius:12px;padding:12px 16px;font:inherit;font-weight:700;cursor:pointer}" +
      ".hw-geo__other:hover{background:#e8e7df}" +
      ".hw-geo__t--pick{margin-bottom:12px}" +
      ".hw-geo__search{width:100%;box-sizing:border-box;padding:12px 14px;border:1.5px solid #e2e1d8;border-radius:12px;font:inherit;font-size:1rem;margin-bottom:10px}" +
      ".hw-geo__search:focus{outline:none;border-color:var(--c-green,#4a6a2f)}" +
      ".hw-geo__list{max-height:46vh;overflow-y:auto;-webkit-overflow-scrolling:touch;display:flex;flex-direction:column;gap:2px}" +
      ".hw-geo__city{text-align:left;background:none;border:0;padding:11px 12px;border-radius:9px;font:inherit;font-size:1rem;color:var(--c-ink,#22241c);cursor:pointer}" +
      ".hw-geo__city:hover{background:var(--c-badge,#eef2e6);color:var(--c-green,#4a6a2f)}" +
      ".hw-geobar{position:fixed;left:12px;right:12px;bottom:12px;z-index:1150;display:flex;align-items:center;gap:10px;background:#fff;border:1px solid #e6e5db;border-radius:14px;box-shadow:0 6px 24px rgba(20,22,16,.16);padding:10px 12px;max-width:520px;margin:0 auto;transform:translateY(16px);opacity:0;transition:.24s}" +
      ".hw-geobar.is-open{transform:none;opacity:1}" +
      ".hw-geobar svg{color:var(--c-green,#4a6a2f);flex:none}" +
      ".hw-geobar span{flex:1;min-width:0;font-size:.95rem;color:var(--c-ink,#22241c);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}" +
      ".hw-geobar__go{background:var(--c-green,#4a6a2f);color:#fff;text-decoration:none;font-weight:700;padding:8px 14px;border-radius:10px;font-size:.9rem;white-space:nowrap}" +
      ".hw-geobar__ch{background:none;border:0;color:#6b6f62;text-decoration:underline;cursor:pointer;font:inherit;font-size:.88rem;white-space:nowrap}" +
      ".hw-geobar__x{background:none;border:0;font-size:1.4rem;line-height:1;color:#9a9a90;cursor:pointer;padding:0 4px}";
    document.head.appendChild(s);
  }

  function close(wrap) { if (!wrap) return; wrap.classList.remove('is-open'); setTimeout(function () { if (wrap.parentNode) wrap.parentNode.removeChild(wrap); }, 220); }
  function closeAll() { close(document.getElementById('hwGeo')); }
  function dismiss(wrap) { try { sessionStorage.setItem(DISMISS, '1'); } catch (e) {} close(wrap); }

  function modal(city) {
    injectCss();
    var wrap = document.createElement('div'); wrap.className = 'hw-geo'; wrap.id = 'hwGeo';
    wrap.innerHTML =
      '<div class="hw-geo__box" role="dialog" aria-modal="true" aria-label="Выбор города">' +
      '<button class="hw-geo__x" aria-label="Закрыть">&times;</button>' +
      '<div class="hw-geo__pin"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21s7-5.5 7-11a7 7 0 1 0-14 0c0 5.5 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/></svg></div>' +
      '<div class="hw-geo__main">' +
      '<div class="hw-geo__t">Похоже, вы из города <b>' + esc(city.name) + '</b></div>' +
      '<div class="hw-geo__s">Показать предложения и цены для вашего города?</div>' +
      '<div class="hw-geo__btns">' +
      '<button class="hw-geo__yes">Да, я из г. ' + esc(city.name) + '</button>' +
      '<button class="hw-geo__other">Выбрать другой город</button>' +
      '</div></div></div>';
    document.body.appendChild(wrap);
    requestAnimationFrame(function () { wrap.classList.add('is-open'); });
    wrap.querySelector('.hw-geo__yes').onclick = function () { go(city); };
    wrap.querySelector('.hw-geo__other').onclick = function () { picker(wrap); };
    wrap.querySelector('.hw-geo__x').onclick = function () { dismiss(wrap); };
    wrap.addEventListener('click', function (e) { if (e.target === wrap) dismiss(wrap); });
  }

  function picker(wrap) {
    var box = wrap.querySelector('.hw-geo__box');
    box.classList.add('hw-geo__box--pick');
    var list = IDX.cities.slice().sort(function (a, b) { return a.name.localeCompare(b.name, 'ru'); });
    box.innerHTML =
      '<button class="hw-geo__x" aria-label="Закрыть">&times;</button>' +
      '<div class="hw-geo__t hw-geo__t--pick">Выберите ваш город</div>' +
      '<input class="hw-geo__search" type="search" placeholder="Поиск города…" autocomplete="off">' +
      '<div class="hw-geo__list"></div>';
    var listEl = box.querySelector('.hw-geo__list');
    function render(q) {
      q = (q || '').toLowerCase().trim(); listEl.innerHTML = '';
      list.forEach(function (c) {
        if (q && c.name.toLowerCase().indexOf(q) < 0) return;
        var b = document.createElement('button'); b.className = 'hw-geo__city'; b.textContent = c.name;
        b.onclick = function () { go(c); };
        listEl.appendChild(b);
      });
    }
    render('');
    var inp = box.querySelector('.hw-geo__search');
    inp.oninput = function () { render(inp.value); };
    box.querySelector('.hw-geo__x').onclick = function () { dismiss(wrap); };
    setTimeout(function () { try { inp.focus(); } catch (e) {} }, 60);
  }

  function bar(city) {
    var u = targetUrl(city); if (!u) return;
    injectCss(); setDeliveryCity(city.name);
    var el = document.createElement('div'); el.className = 'hw-geobar'; el.id = 'hwGeoBar';
    el.innerHTML =
      '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21s7-5.5 7-11a7 7 0 1 0-14 0c0 5.5 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/></svg>' +
      '<span title="Ваш город"><b>' + esc(city.name) + '</b></span>' +
      '<a class="hw-geobar__go" href="' + u + '">Открыть</a>' +
      '<button class="hw-geobar__ch">сменить</button>' +
      '<button class="hw-geobar__x" aria-label="Скрыть">&times;</button>';
    document.body.appendChild(el);
    requestAnimationFrame(function () { el.classList.add('is-open'); });
    el.querySelector('.hw-geobar__ch').onclick = function () { if (el.parentNode) el.parentNode.removeChild(el); openPicker(); };
    el.querySelector('.hw-geobar__x').onclick = function () { el.classList.remove('is-open'); setTimeout(function () { if (el.parentNode) el.parentNode.removeChild(el); }, 220); };
  }
  function openPicker() {
    injectCss();
    var wrap = document.createElement('div'); wrap.className = 'hw-geo is-open'; wrap.id = 'hwGeo';
    wrap.innerHTML = '<div class="hw-geo__box"></div>'; document.body.appendChild(wrap);
    loadIndex(function () { picker(wrap); });
  }

  function ipGeo(cb) {
    fetch('https://ipwho.is/').then(function (r) { return r.json(); }).then(function (d) {
      if (d && d.success !== false && d.latitude != null) cb({ lat: d.latitude, lon: d.longitude, country: d.country_code }); else throw 0;
    }).catch(function () {
      fetch('https://ipapi.co/json/').then(function (r) { return r.json(); }).then(function (d) {
        if (d && d.latitude != null) cb({ lat: d.latitude, lon: d.longitude, country: d.country_code }); else cb(null);
      }).catch(function () { cb(null); });
    });
  }

  function start() {
    var saved = null; try { saved = localStorage.getItem(KEY); } catch (e) {}
    if (saved) { loadIndex(function () { var c = findCity(saved); if (c) bar(c); }); return; }
    var dism = false; try { dism = sessionStorage.getItem(DISMISS) === '1'; } catch (e) {}
    if (dism) return;
    loadIndex(function (idx) {
      if (!idx) return;
      ipGeo(function (g) {
        if (!g || g.country !== 'KZ') return; // вне Казахстана — не предлагаем
        var c = nearest(g.lat, g.lon);
        if (c) modal(c);
      });
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { setTimeout(start, 1200); });
  else setTimeout(start, 1200);
})();
