#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ассеты уровня кампании для [SKAG] СИП-панельные дома Астана (ID 23991449173).
По SOP ad-assets-best-practices.md:
- Sitelinks ×8  (link_text ≤25, описания ≤35), каждая на отдельную страницу/якорь.
- Callouts ×12  (≤25), дифференцированные выгоды.
- Structured snippets ×2 заголовка: «Услуги» и «Типы».
Бизнес-имя и логотип НЕ добавляем: логотипу нужен квадратный файл 1200×1200 + проверка
рекламодателя (на сайте только favicon.svg и og-cover 1200×630) — добавим, когда дадите логотип.

Идемпотентность: повторный запуск создаст дубли ассетов. Запускать один раз.
Длины валидируются до API.
"""
import os, sys
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CID = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
CAMPAIGN_ID = os.environ.get("CAMPAIGN_ID", "23991449173")
camp_rn = "customers/%s/campaigns/%s" % (CID, CAMPAIGN_ID)
LP = "https://hotwellkz.kz/astana-sip-doma.html"

SITELINKS = [
    ("Проекты домов", "Более 550 готовых проектов", "Цены и планировки онлайн", "https://hotwellkz.kz/proekty.html"),
    ("Расчёт цены", "Узнайте стоимость за 5 минут", "Онлайн-калькулятор дома", LP + "#calc"),
    ("Что входит", "Фундамент, кровля, монтаж в цене", "Без скрытых доплат", LP + "#includes"),
    ("Наши работы", "Фото построенных домов", "Реальные объекты по РК", LP + "#works"),
    ("Технология СИП", "Тёплые дома для зим Казахстана", "Энергоэффективные панели", LP + "#tech"),
    ("Отзывы", "Видео и отзывы клиентов", "Реальные истории заказчиков", LP + "#reviews"),
    ("Контакты", "Бесплатный замер и консультация", "Перезвоним за 15 минут", LP + "#contacts"),
    ("О компании", "Своё производство СИП-панелей", "Строим дома с гарантией", LP + "#about"),
]

CALLOUTS = [
    "Дом под ключ за 30 дней", "Фундамент в цене", "Своё производство СИП",
    "Гарантия на дом 1 год", "Цена и сроки в договоре", "Бесплатный замер",
    "Монтаж своими бригадами", "Тёплый дом для зимы", "Расчёт цены онлайн",
    "Без скрытых доплат", "Строим по Казахстану", "Кровля и доставка в цене",
]

SNIPPETS = [
    ("Услуги", ["СИП-дома", "Дома под ключ", "Бани из СИП", "Дачные дома",
                "Коттеджи", "Гаражи", "Фундаменты", "Кровельные работы"]),
    ("Типы", ["Одноэтажные", "Двухэтажные", "С мансардой", "Каркасные",
             "Панельные", "Под ключ"]),
]

# ---- валидация длин ----
errs = []
for lt, d1, d2, url in SITELINKS:
    if len(lt) > 25: errs.append("sitelink title >25: %r (%d)" % (lt, len(lt)))
    if len(d1) > 35: errs.append("sitelink desc1 >35: %r (%d)" % (d1, len(d1)))
    if len(d2) > 35: errs.append("sitelink desc2 >35: %r (%d)" % (d2, len(d2)))
for c in CALLOUTS:
    if len(c) > 25: errs.append("callout >25: %r (%d)" % (c, len(c)))
for hdr, vals in SNIPPETS:
    for v in vals:
        if len(v) > 25: errs.append("snippet value >25: %r (%d)" % (v, len(v)))
    if len(vals) < 3: errs.append("snippet '%s' <3 values" % hdr)
if errs:
    sys.exit("Длины не проходят:\n  " + "\n  ".join(errs))

cfg = dict(developer_token=os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
           client_id=os.environ["GOOGLE_ADS_CLIENT_ID"],
           client_secret=os.environ["GOOGLE_ADS_CLIENT_SECRET"],
           refresh_token=os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
           login_customer_id=CID, use_proto_plus=True)
client = GoogleAdsClient.load_from_dict(cfg)


def run():
    asvc = client.get_service("AssetService")
    asset_ops = []
    plan = []  # (field_type_enum, kind)

    F = client.enums.AssetFieldTypeEnum
    # sitelinks
    for lt, d1, d2, url in SITELINKS:
        op = client.get_type("AssetOperation")
        a = op.create
        a.sitelink_asset.link_text = lt
        a.sitelink_asset.description1 = d1
        a.sitelink_asset.description2 = d2
        a.final_urls.append(url)
        asset_ops.append(op); plan.append((F.SITELINK, "sitelink:%s" % lt))
    # callouts
    for c in CALLOUTS:
        op = client.get_type("AssetOperation")
        op.create.callout_asset.callout_text = c
        asset_ops.append(op); plan.append((F.CALLOUT, "callout:%s" % c))
    # structured snippets
    for hdr, vals in SNIPPETS:
        op = client.get_type("AssetOperation")
        op.create.structured_snippet_asset.header = hdr
        op.create.structured_snippet_asset.values.extend(vals)
        asset_ops.append(op); plan.append((F.STRUCTURED_SNIPPET, "snippet:%s" % hdr))

    res = asvc.mutate_assets(customer_id=CID, operations=asset_ops)
    asset_rns = [r.resource_name for r in res.results]
    print(" ✓ Создано ассетов: %d" % len(asset_rns))

    # привязка к кампании
    casvc = client.get_service("CampaignAssetService")
    ca_ops = []
    for (ftype, _label), rn in zip(plan, asset_rns):
        op = client.get_type("CampaignAssetOperation")
        op.create.campaign = camp_rn
        op.create.asset = rn
        op.create.field_type = ftype
        ca_ops.append(op)
    cres = casvc.mutate_campaign_assets(customer_id=CID, operations=ca_ops)
    print(" ✓ Привязано к кампании: %d" % len(cres.results))
    print("   Sitelinks: %d · Callouts: %d · Structured snippets: %d (заголовки: %s)" % (
        len(SITELINKS), len(CALLOUTS), len(SNIPPETS), ", ".join(h for h, _ in SNIPPETS)))
    print("\n ГОТОВО. Проверка: https://ads.google.com/aw/campaigns?campaignId=%s" % CAMPAIGN_ID)


if __name__ == "__main__":
    try:
        run()
    except GoogleAdsException as ex:
        print("GoogleAdsException:")
        for e in ex.failure.errors:
            print("  -", e.message)
        sys.exit(1)
