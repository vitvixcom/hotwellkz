#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборка SKAG-кампании «СИП-панельные дома Астана» в Google Ads (всё PAUSED).
По SOP campaign.md. Читает креды из GOOGLE_ADS_* env. Аккаунт — из GOOGLE_ADS_CUSTOMER_ID.

Создаёт: бюджет → Search-кампанию (Max Conversions, PAUSED) → гео Астана 50км (presence)
→ исключение всех стран кроме Казахстана → расписание → языки RU+KK → 15 минус-слов
→ ad group → ключ "СИП-панельные дома Астана" (phrase) → 3 RSA (РУ), H1 закреплён.
"""
import os, sys, time
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CID = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
DAILY_BUDGET_USD = 15
FINAL_URL = "https://hotwellkz.kz/astana-sip-doma.html"
KEYWORD = "СИП-панельные дома Астана"
CAMPAIGN_NAME = "[SKAG] СИП-панельные дома Астана"
# Астана (центр), микроградусы
ASTANA_LAT, ASTANA_LON = 51.1605, 71.4704
RADIUS_KM = 50
KZ_GEO_ID = "2398"  # Kazakhstan geoTargetConstant

HEADLINES_PINNED = [  # закрепляются в позиции 1 (варианты ключа), ≤30 симв.
    "СИП-панельные дома Астана",
    "СИП дома в Астане",
    "Дома из СИП-панелей Астана",
]
HEADLINES_FREE = [  # без закрепления, ≤30 симв.
    "Дом под ключ за 30 дней",
    "Цена и сроки в договоре",
    "Гарантия на дом 1 год",
    "Расчёт стоимости онлайн",
    "Тёплый дом без переплат",
    "Своё производство СИП",
    "Строим по Казахстану",
    "Фундамент входит в цену",
    "Монтаж своими бригадами",
    "Сборка дома за 30 дней",
    "Бесплатный выезд замера",
    "Дом мечты из СИП-панелей",
]
DESCRIPTIONS = [  # ≤90 симв.
    "Строим дома из СИП-панелей в Астане под ключ. Цену и сроки фиксируем в договоре.",
    "Своё производство СИП-панелей. Тёплый дом и экономия на отоплении круглый год.",
    "Рассчитайте стоимость онлайн за 5 минут. Гарантия на дом, монтаж нашими бригадами.",
    "Фундамент, проект, кровля и доставка уже в цене. Строим по всему Казахстану.",
]
PATH1, PATH2 = "Астана", "СИП-дома"  # display URL paths, ≤15 симв.
NEGATIVES = [  # минус-слова (broad), под рынок РУ
    "работа", "вакансии", "вакансия", "зарплата", "резюме", "курсы", "обучение",
    "своими руками", "как построить", "как сделать", "чертежи", "бесплатно",
    "реферат", "вики", "форум",
]

# ---- валидация длин ДО любых вызовов API ----
errs = []
for h in HEADLINES_PINNED + HEADLINES_FREE:
    if len(h) > 30:
        errs.append("Заголовок >30: %r (%d)" % (h, len(h)))
for d in DESCRIPTIONS:
    if len(d) > 90:
        errs.append("Описание >90: %r (%d)" % (d, len(d)))
for p in (PATH1, PATH2):
    if len(p) > 15:
        errs.append("Path >15: %r (%d)" % (p, len(p)))
if errs:
    sys.exit("Длины не проходят:\n  " + "\n  ".join(errs))


def cfg():
    c = dict(developer_token=os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
             client_id=os.environ["GOOGLE_ADS_CLIENT_ID"],
             client_secret=os.environ["GOOGLE_ADS_CLIENT_SECRET"],
             refresh_token=os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
             login_customer_id=CID, use_proto_plus=True)
    return c


client = GoogleAdsClient.load_from_dict(cfg())
ga = client.get_service("GoogleAdsService")


def run():
    # 1) БЮДЖЕТ
    bsvc = client.get_service("CampaignBudgetService")
    bop = client.get_type("CampaignBudgetOperation")
    b = bop.create
    b.name = "%s — budget %d" % (CAMPAIGN_NAME, int(time.time()))
    b.amount_micros = DAILY_BUDGET_USD * 1_000_000
    b.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
    b.explicitly_shared = False
    budget_rn = bsvc.mutate_campaign_budgets(customer_id=CID, operations=[bop]).results[0].resource_name
    print(" ✓ Бюджет:", budget_rn)

    # 2) КАМПАНИЯ (PAUSED, Search, Max Conversions)
    csvc = client.get_service("CampaignService")
    cop = client.get_type("CampaignOperation")
    c = cop.create
    c.name = "%s | %s" % (CAMPAIGN_NAME, time.strftime("%Y%m%d_%H%M"))
    c.status = client.enums.CampaignStatusEnum.PAUSED
    c.advertising_channel_type = client.enums.AdvertisingChannelTypeEnum.SEARCH
    c.campaign_budget = budget_rn
    c.maximize_conversions.target_cpa_micros = 0  # объявляем oneof bidding
    c.contains_eu_political_advertising = client.enums.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
    ns = c.network_settings
    ns.target_google_search = True
    ns.target_search_network = False        # без поисковых партнёров
    ns.target_content_network = False        # без КМС
    ns.target_partner_search_network = False
    gt = c.geo_target_type_setting
    gt.positive_geo_target_type = client.enums.PositiveGeoTargetTypeEnum.PRESENCE
    gt.negative_geo_target_type = client.enums.NegativeGeoTargetTypeEnum.PRESENCE
    camp_rn = csvc.mutate_campaigns(customer_id=CID, operations=[cop]).results[0].resource_name
    camp_id = camp_rn.split("/")[-1]
    print(" ✓ Кампания:", camp_rn)

    ccsvc = client.get_service("CampaignCriterionService")

    # 3) ГЕО: проксимити Астана 50 км
    geo_ops = []
    op = client.get_type("CampaignCriterionOperation")
    cr = op.create
    cr.campaign = camp_rn
    cr.proximity.radius = RADIUS_KM
    cr.proximity.radius_units = client.enums.ProximityRadiusUnitsEnum.KILOMETERS
    cr.proximity.geo_point.latitude_in_micro_degrees = int(ASTANA_LAT * 1_000_000)
    cr.proximity.geo_point.longitude_in_micro_degrees = int(ASTANA_LON * 1_000_000)
    geo_ops.append(op)

    # 4) ЯЗЫКИ: RU + KK
    langs = {}
    for r in ga.search(customer_id=CID, query="SELECT language_constant.id, language_constant.code FROM language_constant WHERE language_constant.code IN ('ru','kk')"):
        langs[r.language_constant.code] = r.language_constant.id
    for code in ("ru", "kk"):
        if code in langs:
            op = client.get_type("CampaignCriterionOperation")
            op.create.campaign = camp_rn
            op.create.language.language_constant = "languageConstants/%d" % langs[code]
            geo_ops.append(op)

    # 5) РАСПИСАНИЕ: каждый день 08:00–22:00
    for day in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]:
        op = client.get_type("CampaignCriterionOperation")
        s = op.create
        s.campaign = camp_rn
        s.ad_schedule.day_of_week = client.enums.DayOfWeekEnum[day]
        s.ad_schedule.start_hour = 8
        s.ad_schedule.start_minute = client.enums.MinuteOfHourEnum.ZERO
        s.ad_schedule.end_hour = 22
        s.ad_schedule.end_minute = client.enums.MinuteOfHourEnum.ZERO
        geo_ops.append(op)

    # 6) МИНУС-СЛОВА (broad)
    for kw in NEGATIVES:
        op = client.get_type("CampaignCriterionOperation")
        op.create.campaign = camp_rn
        op.create.negative = True
        op.create.keyword.text = kw
        op.create.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
        geo_ops.append(op)

    ccsvc.mutate_campaign_criteria(customer_id=CID, operations=geo_ops)
    print(" ✓ Гео (Астана 50км, presence) + языки RU/KK + расписание + %d минус-слов" % len(NEGATIVES))

    # 7) ИСКЛЮЧЕНИЕ ВСЕХ СТРАН, КРОМЕ КАЗАХСТАНА
    countries = []
    for r in ga.search(customer_id=CID, query="SELECT geo_target_constant.id FROM geo_target_constant WHERE geo_target_constant.target_type = 'Country' AND geo_target_constant.status = 'ENABLED'"):
        gid = str(r.geo_target_constant.id)
        if gid != KZ_GEO_ID:
            countries.append(gid)
    neg_ops = []
    for gid in countries:
        op = client.get_type("CampaignCriterionOperation")
        op.create.campaign = camp_rn
        op.create.negative = True
        op.create.location.geo_target_constant = "geoTargetConstants/%s" % gid
        neg_ops.append(op)
    req = client.get_type("MutateCampaignCriteriaRequest")
    req.customer_id = CID
    req.operations = neg_ops
    req.partial_failure = True
    res = ccsvc.mutate_campaign_criteria(request=req)
    ok = sum(1 for x in res.results if x.resource_name)
    print(" ✓ Исключено стран (кроме Казахстана): %d" % ok)

    # 8) AD GROUP (PAUSED)
    agsvc = client.get_service("AdGroupService")
    agop = client.get_type("AdGroupOperation")
    ag = agop.create
    ag.name = "СИП-панельные дома Астана"
    ag.campaign = camp_rn
    ag.status = client.enums.AdGroupStatusEnum.PAUSED
    ag.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
    ag_rn = agsvc.mutate_ad_groups(customer_id=CID, operations=[agop]).results[0].resource_name
    print(" ✓ Ad group:", ag_rn)

    # 9) КЛЮЧ (phrase)
    agcsvc = client.get_service("AdGroupCriterionService")
    kop = client.get_type("AdGroupCriterionOperation")
    k = kop.create
    k.ad_group = ag_rn
    k.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
    k.keyword.text = KEYWORD
    k.keyword.match_type = client.enums.KeywordMatchTypeEnum.PHRASE
    agcsvc.mutate_ad_group_criteria(customer_id=CID, operations=[kop])
    print(' ✓ Ключ: "%s" (phrase match)' % KEYWORD)

    # 10) RSA (PAUSED), H1 закреплён (один уникальный RSA — дубликаты запрещены)
    adsvc = client.get_service("AdGroupAdService")
    op = client.get_type("AdGroupAdOperation")
    aga = op.create
    aga.ad_group = ag_rn
    aga.status = client.enums.AdGroupAdStatusEnum.PAUSED
    ad = aga.ad
    ad.final_urls.append(FINAL_URL)
    rsa = ad.responsive_search_ad
    for h in HEADLINES_PINNED:
        a = client.get_type("AdTextAsset")
        a.text = h
        a.pinned_field = client.enums.ServedAssetFieldTypeEnum.HEADLINE_1
        rsa.headlines.append(a)
    for h in HEADLINES_FREE:
        a = client.get_type("AdTextAsset")
        a.text = h
        rsa.headlines.append(a)
    for d in DESCRIPTIONS:
        a = client.get_type("AdTextAsset")
        a.text = d
        rsa.descriptions.append(a)
    rsa.path1 = PATH1
    rsa.path2 = PATH2
    adsvc.mutate_ad_group_ads(customer_id=CID, operations=[op])
    print(" ✓ RSA создан")

    print("\n ALL CREATED · PAUSED · Campaign ID", camp_id)
    print(" Проверка: https://ads.google.com/aw/campaigns?campaignId=%s" % camp_id)


if __name__ == "__main__":
    try:
        run()
    except GoogleAdsException as ex:
        print("GoogleAdsException:")
        for e in ex.failure.errors:
            print("  -", e.message)
        sys.exit(1)
