# Google Ads API — интеграция

Авторизация в Google уже выполнена (OAuth, scope `https://www.googleapis.com/auth/adwords`).
Получены `client_id`, `client_secret`, `refresh_token`. Здесь — код, который их использует.

> Приложение опубликовано (In production) — refresh-токен бессрочный.

## Что ещё нужно для рабочих вызовов Ads API

OAuth-токена недостаточно. Дополнительно требуются:

1. **Developer token** — Google Ads → *Tools & Settings → Setup → API Center*.
   У нового токена обычно уровень *Test account* — он работает только с тестовыми
   аккаунтами, пока вы не подадите заявку на *Basic/Standard access*.
2. **Login customer ID** — ID управляющего (MCC) аккаунта, цифрами без дефисов.
   Нужен, если обращаетесь к клиентским аккаунтам под менеджером.

## Секреты (имена для GitHub Secrets / env)

| Secret | Откуда |
|---|---|
| `GOOGLE_ADS_CLIENT_ID` | из OAuth credentials |
| `GOOGLE_ADS_CLIENT_SECRET` | из OAuth credentials |
| `GOOGLE_ADS_REFRESH_TOKEN` | получен при авторизации |
| `GOOGLE_ADS_DEVELOPER_TOKEN` | API Center |
| `GOOGLE_ADS_LOGIN_CUSTOMER_ID` | ID MCC-аккаунта (цифры) |

> ⚠️ Refresh-токен сейчас живёт ~7 дней (OAuth-приложение в режиме *Testing*).
> Чтобы сделать бессрочным — опубликуйте приложение в *OAuth consent screen → Publish app*.

### Добавить секреты в GitHub (вручную)

Repo **hotwellkz/sam** → *Settings* → *Secrets and variables* → *Actions* →
*New repository secret* → создать каждый из секретов выше.

## Локальный запуск

```bash
pip install -r requirements.txt

export GOOGLE_ADS_CLIENT_ID=...
export GOOGLE_ADS_CLIENT_SECRET=...
export GOOGLE_ADS_REFRESH_TOKEN=...
export GOOGLE_ADS_DEVELOPER_TOKEN=...
export GOOGLE_ADS_LOGIN_CUSTOMER_ID=...      # цифры без дефисов

python ads_client.py test                 # проверка авторизации (список аккаунтов)
python ads_client.py campaigns 1234567890 # кампании конкретного аккаунта
```

## Проверка в CI

Workflow `.github/workflows/google-ads-test.yml` запускается вручную
(*Actions → Google Ads API smoke test → Run workflow*) и вызывает
`ads_client.py test`, читая значения из GitHub Secrets.
