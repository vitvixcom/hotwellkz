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

  // 1) Конверсия при отправке лид-формы
  function bindForms() {
    var forms = document.querySelectorAll(
      '#callbackForm, form[name="lead"], form.lead-form, form.callback-form'
    );
    forms.forEach(function (f) {
      f.addEventListener('submit', function () { fire(FORM_LABEL); }, { once: true });
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
