#!/usr/bin/env bash
# Обновление снимка дашборда (site/dashboard-data.json) во время сборки Netlify.
# БЕЗОПАСНО: никогда не валит сборку. Если кредов нет или API упал —
# публикуется уже закоммиченный снимок.
set +e

if [ -z "$GOOGLE_ADS_REFRESH_TOKEN" ]; then
  echo "ℹ︎  GOOGLE_ADS_* env не заданы — пропускаю обновление, публикую существующий dashboard-data.json"
  exit 0
fi

echo "→  Устанавливаю зависимости Google Ads SDK…"
pip3 install --quiet --disable-pip-version-check google-ads cryptography 2>/dev/null

echo "→  Обновляю site/dashboard-data.json из Google Ads API…"
OUT="site/dashboard-data.json" python3 integrations/google-ads/build_dashboard_data.py
if [ $? -eq 0 ]; then
  echo "✓  Снимок дашборда обновлён"
else
  echo "⚠︎  Не удалось обновить (публикуется прежний снимок) — сборку не валю"
fi
exit 0
