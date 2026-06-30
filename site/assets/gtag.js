/* Google Ads global tag + конверсии: отправка формы и клик по WhatsApp.
   Один источник правды для тегов: меняйте AW/LABEL только здесь.
   Подключается строкой <script src="/assets/gtag.js" defer></script> на каждой странице. */
(function () {
  var AW = 'AW-11012690511';
  var FORM_LABEL = 'AW-11012690511/aGVPCLngocgcEM-koYMp'; // «Заявка с сайта · форма» ($50)
  var WA_LABEL = 'AW-11012690511/kTjSCI_t664aEM-koYMp';   // «WhatsApp Клик» ($50)

  // загрузка gtag.js
  var s = document.createElement('script');
  s.async = true;
  s.src = 'https://www.googletagmanager.com/gtag/js?id=' + AW;
  document.head.appendChild(s);

  window.dataLayer = window.dataLayer || [];
  function gtag() { dataLayer.push(arguments); }
  window.gtag = gtag;
  gtag('js', new Date());
  gtag('config', AW);

  function fire(label) {
    if (typeof gtag === 'function') {
      gtag('event', 'conversion', { send_to: label }); // значение берётся из conversion action
    }
  }

  // Открыть WhatsApp с данными формы (наш единственный канал заявок)
  function waSend(f) {
    var val = function (sel) { var el = f.querySelector(sel); return el ? (el.value || '').trim() : ''; };
    var name = val('[name="Имя"]');
    var phone = val('[name="Телефон"], [type="tel"]');
    var comment = val('[name="Комментарий"], textarea');
    var msg = 'Здравствуйте! Меня зовут ' + name + ', телефон ' + phone + '.';
    if (comment) { msg += ' ' + comment; }
    msg += ' Оставил(а) заявку на сайте.';
    window.open('https://wa.me/77477434343?text=' + encodeURIComponent(msg), '_blank');
  }

  function bindForms() {
    // Контактная форма → конверсия + отправка в WhatsApp (на сервер ничего не уходит)
    document.querySelectorAll('form[name="lead"], form.lead-form').forEach(function (f) {
      f.addEventListener('submit', function (e) {
        e.preventDefault();
        fire(FORM_LABEL);
        waSend(f);
      });
    });
    // Форма обратного звонка: WhatsApp открывает её собственный скрипт — нам нужна только конверсия
    document.querySelectorAll('#callbackForm, form.callback-form').forEach(function (f) {
      f.addEventListener('submit', function () { fire(FORM_LABEL); });
    });
  }

  // 2) Конверсия при клике по любой кнопке/ссылке WhatsApp (делегирование — ловит все 2600+ страниц)
  document.addEventListener('click', function (e) {
    var t = e.target;
    var a = t && t.closest ? t.closest('a[href*="wa.me"], a[href*="api.whatsapp"], a[href*="whatsapp.com"]') : null;
    if (a) { fire(WA_LABEL); }
  }, true);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindForms);
  } else {
    bindForms();
  }
})();
