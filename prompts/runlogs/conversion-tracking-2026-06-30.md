# Runlog · Conversion tracking + warm-pixel audience · 2026-06-30

SOP: `setup-conversion-tracking-and-audience.md`
Аккаунт Google Ads: **8802382037** (USD) · Домен: **hotwellkz.kz**

## Параметры (по умолчанию, согласовать/менять можно)
- Ценность заявки: **$750** (дом ~$15k × ~5% закрытия) — меняется в UI за секунду.
- Имя конверсии: **Заявка с сайта · форма**
- Установка тега: **на весь сайт** (1303 страницы)
- Корректировка ставки для warm-pixel: **+50%**

## Созданное в Google Ads
- Conversion action: `customers/8802382037/conversionActions/7667740729`
  - SUBMIT_LEAD_FORM · WEBPAGE · ENABLED · primary_for_goal=True
  - default_value=750 USD · counting=ONE_PER_CLICK · click-lookback 90д · view 1д
  - attribution: data-driven
- **Глобальный тег:** `AW-11012690511`
- **Conversion label:** `AW-11012690511/aGVPCLngocgcEM-koYMp`
- Warm-pixel audience: `customers/8802382037/userLists/9420982384`
  - «Warm pixel · all visitors · hotwellkz.kz · 540d» · OPEN · 540 дней
  - правило: URL содержит `hotwellkz.kz` (любая страница)
- RLSA attach: ad group `206423446508` (СИП-панельные дома Астана)
  - USER_LIST · Observation (bid_only) · bid_modifier **1.5 (+50%)** · ENABLED

## Сайт (статический, Netlify, деплой из main)
- `site/assets/gtag.js` — загрузка gtag + конверсия на submit лид-форм
  (`#callbackForm`, `form[name="lead"]`, `.lead-form`, `.callback-form`).
- В `<head>` всех 1303 .html добавлена строка `<script src="/assets/gtag.js" defer>`.
- Генераторы обновлены: `import.py` (страницы проектов + каталог),
  `generate-landing` наследует тег из `index.html`.

## Статус проверки
- Статическая проверка: тег и label присутствуют на страницах, селекторы форм совпадают. ✓
- Живой fire-test (Playwright/Tag Assistant) НЕ выполнялся: сайт статический, тег
  станет активным только ПОСЛЕ мержа ветки в `main` и деплоя Netlify.

## Что сделать после деплоя
1. Смержить ветку в `main` → Netlify задеплоит тег.
2. Tag Assistant (https://tagassistant.google.com/) → открыть hotwellkz.kz →
   отправить форму → убедиться, что конверсия «Заявка с сайта · форма» зафиксирована.
3. Через 24–48ч проверить в Google Ads, что статус конверсии = «Записывает конверсии».
4. Аудитория наполняется по мере трафика; RLSA-корректировка начнёт работать при ~100 членах.

## Важные замечания
- `primary_for_goal=True` — новая конверсия попадает в цель «Отправка формы» на уровне
  аккаунта, поэтому может влиять на ставки и других кампаний, использующих цели по умолчанию.
- Кампания Астана всё ещё на PAUSED.
