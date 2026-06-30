# Автообновление дашборда /dashboard по расписанию

GitHub Actions на аккаунте отключены, поэтому обновление сделано через Netlify:
сборка обновляет `site/dashboard-data.json`, а запланированная функция раз в день
запускает сборку.

## Как это работает

1. `netlify/functions/refresh-dashboard.mjs` — **запланированная функция** (cron
   `0 6 * * *`, ежедневно 06:00 UTC ≈ 11:00 Астана). По расписанию POST'ит на
   build hook → Netlify запускает новую сборку.
2. `netlify/refresh-dashboard.sh` (команда сборки в `netlify.toml`) — при каждой
   сборке, если заданы `GOOGLE_ADS_*` env, ставит SDK и перезапускает
   `integrations/google-ads/build_dashboard_data.py` → свежий `dashboard-data.json`.
   Скрипт **никогда не валит сборку**: без кредов/при ошибке публикуется прежний снимок.

## Что нужно настроить в Netlify (один раз)

### 1. Переменные окружения
Site configuration → **Environment variables** → добавить:

| Переменная | Значение |
|---|---|
| `GOOGLE_ADS_CLIENT_ID` | ваш OAuth client id |
| `GOOGLE_ADS_CLIENT_SECRET` | ваш OAuth client secret |
| `GOOGLE_ADS_REFRESH_TOKEN` | ваш refresh token |
| `GOOGLE_ADS_DEVELOPER_TOKEN` | developer token |
| `GOOGLE_ADS_LOGIN_CUSTOMER_ID` | `8802382037` |
| `GOOGLE_ADS_CUSTOMER_ID` | `8802382037` |

> Это те же значения, что использовались в сессии. Хранить их в Netlify env — нормально
> (шифруются, доступны только сборке). В репозиторий их не коммитим.

### 2. Build hook
Site configuration → Build & deploy → **Build hooks** → Add build hook
(назвать, например, `dashboard-cron`) → скопировать URL и добавить его как env:

| Переменная | Значение |
|---|---|
| `NETLIFY_BUILD_HOOK_URL` | `https://api.netlify.com/build_hooks/XXXXXXXX` |

### 3. Проверка
- Откройте Netlify → Functions → должна появиться `refresh-dashboard` со значком расписания.
- Нажмите на build hook вручную (или дождитесь крона) → в логах сборки строка
  «✓ Снимок дашборда обновлён», на `/dashboard` обновится дата снимка.

## Поменять расписание
В `netlify/functions/refresh-dashboard.mjs` → `export const config = { schedule: "0 6 * * *" }`.
Примеры: `"0 */6 * * *"` каждые 6 часов; `"0 6 * * 1"` по понедельникам.

## Важно
- Данные обновляются при **каждой** сборке (в т.ч. при обычных пушах контента), пока
  заданы `GOOGLE_ADS_*` — это нормально, дашборд всегда свежий.
- Пока переменные не заданы, сборки идут как раньше, публикуется закоммиченный снимок.
