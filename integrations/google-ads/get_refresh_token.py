#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генерация GOOGLE_ADS_REFRESH_TOKEN для Google Ads API.

⚠️ Запускать ТОЛЬКО локально, на своём компьютере (нужен браузер и вход в Google).
   В headless-окружении (CI, сервер без браузера) работать не будет — токен
   выдаётся только после интерактивного согласия пользователя.

Установка зависимостей:
    python3 -m pip install google-auth-oauthlib

Запуск (вариант 1 — переменными окружения):
    GOOGLE_ADS_CLIENT_ID=xxx GOOGLE_ADS_CLIENT_SECRET=yyy python3 get_refresh_token.py

Запуск (вариант 2 — скрипт сам спросит client_id/secret):
    python3 get_refresh_token.py

Что произойдёт:
1. Откроется браузер со входом в Google.
2. Войди под аккаунтом, у которого есть доступ к нужному Google Ads.
3. Разреши доступ (scope: adwords).
4. Скрипт напечатает строку REFRESH TOKEN — скопируй её в GitHub Secret
   GOOGLE_ADS_REFRESH_TOKEN.
"""
import os
import sys

SCOPES = ["https://www.googleapis.com/auth/adwords"]


def main():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        sys.exit("Нет библиотеки. Установи: python3 -m pip install google-auth-oauthlib")

    client_id = os.environ.get("GOOGLE_ADS_CLIENT_ID", "").strip() or input("Client ID: ").strip()
    client_secret = os.environ.get("GOOGLE_ADS_CLIENT_SECRET", "").strip() or input("Client secret: ").strip()
    if not client_id or not client_secret:
        sys.exit("Нужны client_id и client_secret.")

    config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(config, scopes=SCOPES)
    # access_type=offline + prompt=consent — обязательны, чтобы вернулся refresh_token
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent",
                                  authorization_prompt_message="Открываю браузер для входа в Google…")

    if not creds.refresh_token:
        sys.exit("Refresh token не получен. Повтори с prompt=consent (он уже задан) "
                 "или проверь, что приложение опубликовано/добавлен тестовый пользователь.")

    print("\n" + "=" * 60)
    print("GOOGLE_ADS_REFRESH_TOKEN:")
    print(creds.refresh_token)
    print("=" * 60)
    print("\nСкопируй значение выше в GitHub → Settings → Secrets and variables →")
    print("Actions → New repository secret → имя GOOGLE_ADS_REFRESH_TOKEN.")


if __name__ == "__main__":
    main()
