#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Дозаполнение УЖЕ созданной кампании «СИП-панельные дома Астана» (ID берётся из
CAMPAIGN_ID). Бюджет и сама кампания (PAUSED) уже созданы build-скриптом — здесь
добавляем критерии (гео/язык/расписание/минус-слова), исключение стран,
ad group, ключ и RSA. Язык — только Russian (Kazakh в Google Ads не таргетируется).
"""
import os, sys
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CID = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
CAMPAIGN_ID = os.environ.get("CAMPAIGN_ID", "23991449173")
FINAL_URL = "https://hotwellkz.kz/astana-sip-doma.html"
KEYWORD = "СИП-панельные дома Астана"
ASTANA_LAT, ASTANA_LON = 51.1605, 71.4704
RADIUS_KM = 50
KZ_GEO_ID = "2398"
RU_LANG_ID = 1031  # Russian (kk Kazakh — targetable=False, нельзя)

HEADLINES_PINNED = [
    "СИП-панельные дома Астана", "СИП дома в Астане", "Дома из СИП-панелей Астана",
]
HEADLINES_FREE = [
    "Дом под ключ за 30 дней", "Цена и сроки в договоре", "Гарантия на дом 1 год",
    "Расчёт стоимости онлайн", "Тёплый дом без переплат", "Своё производство СИП",
    "Строим по Казахстану", "Фундамент входит в цену", "Монтаж своими бригадами",
    "Сборка дома за 30 дней", "Бесплатный выезд замера", "Дом мечты из СИП-панелей",
]
DESCRIPTIONS = [
    "Строим дома из СИП-панелей в Астане под ключ. Цену и сроки фиксируем в договоре.",
    "Своё производство СИП-панелей. Тёплый дом и экономия на отоплении круглый год.",
    "Рассчитайте стоимость онлайн за 5 минут. Гарантия на дом, монтаж нашими бригадами.",
    "Фундамент, проект, кровля и доставка уже в цене. Строим по всему Казахстану.",
]
PATH1, PATH2 = "Астана", "СИП-дома"
NEGATIVES = [
    "работа", "вакансии", "вакансия", "зарплата", "резюме", "курсы", "обучение",
    "своими руками", "как построить", "как сделать", "чертежи", "бесплатно",
    "реферат", "вики", "форум",
]

cfg = dict(developer_token=os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
           client_id=os.environ["GOOGLE_ADS_CLIENT_ID"],
           client_secret=os.environ["GOOGLE_ADS_CLIENT_SECRET"],
           refresh_token=os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
           login_customer_id=CID, use_proto_plus=True)
client = GoogleAdsClient.load_from_dict(cfg)
ga = client.get_service("GoogleAdsService")
camp_rn = "customers/%s/campaigns/%s" % (CID, CAMPAIGN_ID)


def run():
    ccsvc = client.get_service("CampaignCriterionService")
    ops = []

    # гео: проксимити Астана 50 км
    op = client.get_type("CampaignCriterionOperation")
    cr = op.create
    cr.campaign = camp_rn
    cr.proximity.radius = RADIUS_KM
    cr.proximity.radius_units = client.enums.ProximityRadiusUnitsEnum.KILOMETERS
    cr.proximity.geo_point.latitude_in_micro_degrees = int(ASTANA_LAT * 1_000_000)
    cr.proximity.geo_point.longitude_in_micro_degrees = int(ASTANA_LON * 1_000_000)
    ops.append(op)

    # язык: только Russian
    op = client.get_type("CampaignCriterionOperation")
    op.create.campaign = camp_rn
    op.create.language.language_constant = "languageConstants/%d" % RU_LANG_ID
    ops.append(op)

    # расписание: каждый день 08:00–22:00
    for day in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]:
        op = client.get_type("CampaignCriterionOperation")
        s = op.create
        s.campaign = camp_rn
        s.ad_schedule.day_of_week = client.enums.DayOfWeekEnum[day]
        s.ad_schedule.start_hour = 8
        s.ad_schedule.start_minute = client.enums.MinuteOfHourEnum.ZERO
        s.ad_schedule.end_hour = 22
        s.ad_schedule.end_minute = client.enums.MinuteOfHourEnum.ZERO
        ops.append(op)

    # минус-слова
    for kw in NEGATIVES:
        op = client.get_type("CampaignCriterionOperation")
        op.create.campaign = camp_rn
        op.create.negative = True
        op.create.keyword.text = kw
        op.create.keyword.match_type = client.enums.KeywordMatchTypeEnum.BROAD
        ops.append(op)

    ccsvc.mutate_campaign_criteria(customer_id=CID, operations=ops)
    print(" ✓ Гео (Астана 50км) + язык RU + расписание + %d минус-слов" % len(NEGATIVES))

    # исключение всех стран, кроме Казахстана
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

    # ad group
    agsvc = client.get_service("AdGroupService")
    agop = client.get_type("AdGroupOperation")
    ag = agop.create
    ag.name = "СИП-панельные дома Астана"
    ag.campaign = camp_rn
    ag.status = client.enums.AdGroupStatusEnum.PAUSED
    ag.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
    ag_rn = agsvc.mutate_ad_groups(customer_id=CID, operations=[agop]).results[0].resource_name
    print(" ✓ Ad group:", ag_rn)

    # ключ (phrase)
    agcsvc = client.get_service("AdGroupCriterionService")
    kop = client.get_type("AdGroupCriterionOperation")
    k = kop.create
    k.ad_group = ag_rn
    k.status = client.enums.AdGroupCriterionStatusEnum.ENABLED
    k.keyword.text = KEYWORD
    k.keyword.match_type = client.enums.KeywordMatchTypeEnum.PHRASE
    agcsvc.mutate_ad_group_criteria(customer_id=CID, operations=[kop])
    print(' ✓ Ключ: "%s" (phrase)' % KEYWORD)

    # RSA (PAUSED), H1 закреплён
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

    print("\n ГОТОВО · PAUSED · Campaign ID", CAMPAIGN_ID)
    print(" Проверка: https://ads.google.com/aw/campaigns?campaignId=%s" % CAMPAIGN_ID)


if __name__ == "__main__":
    try:
        run()
    except GoogleAdsException as ex:
        print("GoogleAdsException:")
        for e in ex.failure.errors:
            print("  -", e.message)
        sys.exit(1)
