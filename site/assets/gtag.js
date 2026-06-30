/* Google Ads global tag + conversion на отправку формы.
   Один источник правды для тега: меняйте AW/LABEL только здесь.
   Подключается строкой <script src="/assets/gtag.js" defer></script> на каждой странице. */
(function () {
  var AW = 'AW-11012690511';
  var LABEL = 'AW-11012690511/aGVPCLngocgcEM-koYMp'; // conversion: «Заявка с сайта · форма»

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

  // конверсия при отправке любой лид-формы (значение берётся из conversion action по умолчанию)
  function bind() {
    var forms = document.querySelectorAll(
      '#callbackForm, form[name="lead"], form.lead-form, form.callback-form'
    );
    forms.forEach(function (f) {
      f.addEventListener('submit', function () {
        if (typeof gtag === 'function') {
          gtag('event', 'conversion', { send_to: LABEL });
        }
      }, { once: true });
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bind);
  } else {
    bind();
  }
})();
