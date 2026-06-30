#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SKAG-кампания «Каркасные дома Астана» (всё PAUSED) по campaign.md.
Бюджет $5/день, Search-only, Max Conversions, гео Астана 50км (presence),
исключение всех стран кроме Казахстана, расписание 8–22, 15 минус-слов,
язык русский (казахский Google не таргетирует), ключ phrase, 3 RSA, ассеты.
"""
import os, sys
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CID = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
BUDGET_USD = 5
KEYWORD = "каркасные дома Астана"
FINAL_URL = "https://hotwellkz.kz/astana-karkasnye-doma.html"
CAMPAIGN_NAME = "[SKAG] Каркасные дома Астана"
ASTANA_LAT, ASTANA_LON = 51.1605, 71.4704
RADIUS_KM = 50
KZ_GEO_ID = "2398"
RU_LANG_ID = 1031
PATH1, PATH2 = "Астана", "Каркасные"

PINNED = ["Каркасные дома Астана", "Каркасный дом в Астане", "Каркасные дома в Астане"]
FREE = [
    "Дом под ключ за 30 дней", "Цена и сроки в договоре", "Фундамент входит в цену",
    "Тёплый дом для зим РК", "Монтаж своими бригадами", "Гарантия на дом 1 год",
    "Расчёт стоимости онлайн", "Строим по Казахстану", "Без скрытых доплат",
    "Опыт с 2012 года", "Каркасный дом под ключ", "Заселение через месяц",
    "Энергоэффективный дом", "Своё производство", "Кровля и доставка в цене",
    "Прочный и тёплый дом", "Дом мечты под ключ", "Сборка дома за 30 дней",
]
DESCS = [
    "Строим каркасные дома в Астане под ключ. Цену и сроки фиксируем в договоре.",
    "Тёплый каркасный дом для суровых зим Казахстана. Монтаж нашими бригадами.",
    "Рассчитайте стоимость онлайн за 5 минут. Фундамент и кровля уже в цене.",
    "Каркасный дом под ключ за 30 дней. Работаем по всему Казахстану с 2012 года.",
    "Без скрытых доплат — цена и сроки зафиксированы в договоре. Гарантия на дом.",
    "Энергоэффективный каркасный дом в Астане. Своё производство, монтаж за месяц.",
]
NEGATIVES = ["работа", "вакансии", "вакансия", "зарплата", "резюме", "курсы", "обучение",
             "своими руками", "как построить", "как сделать", "чертежи", "бесплатно",
             "форум", "модульные", "контейнер"]

SITELINKS = [
    ("Проекты домов", "Более 550 готовых проектов", "Цены и планировки онлайн", "https://hotwellkz.kz/proekty.html"),
    ("Расчёт цены", "Стоимость каркасного дома", "Онлайн-калькулятор за 5 минут", FINAL_URL + "#calc"),
    ("Что входит", "Фундамент, кровля, монтаж в цене", "Без скрытых доплат", FINAL_URL + "#includes"),
    ("Наши работы", "Фото построенных домов", "Реальные объекты по РК", FINAL_URL + "#works"),
    ("Технология", "Тёплый каркас для зим РК", "Энергоэффективные стены", FINAL_URL + "#tech"),
    ("Отзывы", "Видео и отзывы клиентов", "Реальные истории заказчиков", FINAL_URL + "#reviews"),
    ("Контакты", "Бесплатный замер и расчёт", "Перезвоним за 15 минут", FINAL_URL + "#contacts"),
    ("О компании", "Своё производство, с 2012", "Строим дома с гарантией", FINAL_URL + "#about"),
]
CALLOUTS = ["Дом под ключ за 30 дней", "Фундамент в цене", "Гарантия на дом 1 год",
            "Цена и сроки в договоре", "Бесплатный замер", "Монтаж своими бригадами",
            "Тёплый дом для зимы", "Расчёт цены онлайн", "Без скрытых доплат",
            "Строим по Казахстану", "Кровля и доставка в цене", "Опыт с 2012 года"]
SNIPPETS = [
    ("Услуги", ["Каркасные дома", "СИП-дома", "Дома под ключ", "Бани", "Дачные дома", "Коттеджи", "Фундаменты", "Кровля"]),
    ("Типы", ["Одноэтажные", "Двухэтажные", "С мансардой", "Под ключ", "Дачные"]),
]

# ---- валидация длин ДО API ----
errs = []
for h in PINNED + FREE:
    if len(h) > 30: errs.append("Заголовок >30: %r (%d)" % (h, len(h)))
for d in DESCS:
    if len(d) > 90: errs.append("Описание >90: %r (%d)" % (d, len(d)))
for p in (PATH1, PATH2):
    if len(p) > 15: errs.append("Path >15: %r (%d)" % (p, len(p)))
for lt, d1, d2, u in SITELINKS:
    if len(lt) > 25: errs.append("sitelink >25: %r" % lt)
    if len(d1) > 35 or len(d2) > 35: errs.append("sitelink desc >35: %r" % lt)
for c in CALLOUTS:
    if len(c) > 25: errs.append("callout >25: %r" % c)
for hdr, vals in SNIPPETS:
    for v in vals:
        if len(v) > 25: errs.append("snippet >25: %r" % v)
if errs:
    sys.exit("Длины не проходят:\n  " + "\n  ".join(errs))


def rot(lst, n):
    n %= len(lst); return lst[n:] + lst[:n]


cfg = dict(developer_token=os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
           client_id=os.environ["GOOGLE_ADS_CLIENT_ID"],
           client_secret=os.environ["GOOGLE_ADS_CLIENT_SECRET"],
           refresh_token=os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
           login_customer_id=CID, use_proto_plus=True)
client = GoogleAdsClient.load_from_dict(cfg)
E = client.enums
ga = client.get_service("GoogleAdsService")


def run():
    import time
    # 1) бюджет
    bsvc = client.get_service("CampaignBudgetService")
    bop = client.get_type("CampaignBudgetOperation")
    b = bop.create
    b.name = "%s — budget %d" % (CAMPAIGN_NAME, int(time.time()))
    b.amount_micros = BUDGET_USD * 1_000_000
    b.delivery_method = E.BudgetDeliveryMethodEnum.STANDARD
    b.explicitly_shared = False
    budget_rn = bsvc.mutate_campaign_budgets(customer_id=CID, operations=[bop]).results[0].resource_name
    print(" ✓ Бюджет $%d:" % BUDGET_USD, budget_rn)

    # 2) кампания
    csvc = client.get_service("CampaignService")
    cop = client.get_type("CampaignOperation")
    c = cop.create
    c.name = "%s | %s" % (CAMPAIGN_NAME, time.strftime("%Y%m%d_%H%M"))
    c.status = E.CampaignStatusEnum.PAUSED
    c.advertising_channel_type = E.AdvertisingChannelTypeEnum.SEARCH
    c.campaign_budget = budget_rn
    c.maximize_conversions.target_cpa_micros = 0
    c.contains_eu_political_advertising = E.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
    ns = c.network_settings
    ns.target_google_search = True
    ns.target_search_network = False
    ns.target_content_network = False
    ns.target_partner_search_network = False
    c.geo_target_type_setting.positive_geo_target_type = E.PositiveGeoTargetTypeEnum.PRESENCE
    c.geo_target_type_setting.negative_geo_target_type = E.NegativeGeoTargetTypeEnum.PRESENCE
    camp_rn = csvc.mutate_campaigns(customer_id=CID, operations=[cop]).results[0].resource_name
    camp_id = camp_rn.split("/")[-1]
    print(" ✓ Кампания:", camp_rn)

    ccsvc = client.get_service("CampaignCriterionService")
    ops = []
    # гео проксимити
    op = client.get_type("CampaignCriterionOperation"); cr = op.create
    cr.campaign = camp_rn
    cr.proximity.radius = RADIUS_KM
    cr.proximity.radius_units = E.ProximityRadiusUnitsEnum.KILOMETERS
    cr.proximity.geo_point.latitude_in_micro_degrees = int(ASTANA_LAT * 1_000_000)
    cr.proximity.geo_point.longitude_in_micro_degrees = int(ASTANA_LON * 1_000_000)
    ops.append(op)
    # язык RU
    op = client.get_type("CampaignCriterionOperation")
    op.create.campaign = camp_rn
    op.create.language.language_constant = "languageConstants/%d" % RU_LANG_ID
    ops.append(op)
    # расписание 8–22
    for day in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]:
        op = client.get_type("CampaignCriterionOperation"); s = op.create
        s.campaign = camp_rn
        s.ad_schedule.day_of_week = E.DayOfWeekEnum[day]
        s.ad_schedule.start_hour = 8; s.ad_schedule.start_minute = E.MinuteOfHourEnum.ZERO
        s.ad_schedule.end_hour = 22; s.ad_schedule.end_minute = E.MinuteOfHourEnum.ZERO
        ops.append(op)
    # минус-слова
    for kw in NEGATIVES:
        op = client.get_type("CampaignCriterionOperation")
        op.create.campaign = camp_rn; op.create.negative = True
        op.create.keyword.text = kw; op.create.keyword.match_type = E.KeywordMatchTypeEnum.BROAD
        ops.append(op)
    ccsvc.mutate_campaign_criteria(customer_id=CID, operations=ops)
    print(" ✓ Гео Астана 50км + язык RU + расписание + %d минус-слов" % len(NEGATIVES))

    # исключение стран
    countries = []
    for r in ga.search(customer_id=CID, query="SELECT geo_target_constant.id FROM geo_target_constant WHERE geo_target_constant.target_type = 'Country' AND geo_target_constant.status = 'ENABLED'"):
        gid = str(r.geo_target_constant.id)
        if gid != KZ_GEO_ID: countries.append(gid)
    neg_ops = []
    for gid in countries:
        op = client.get_type("CampaignCriterionOperation")
        op.create.campaign = camp_rn; op.create.negative = True
        op.create.location.geo_target_constant = "geoTargetConstants/%s" % gid
        neg_ops.append(op)
    req = client.get_type("MutateCampaignCriteriaRequest")
    req.customer_id = CID; req.operations = neg_ops; req.partial_failure = True
    res = ccsvc.mutate_campaign_criteria(request=req)
    print(" ✓ Исключено стран (кроме Казахстана):", sum(1 for x in res.results if x.resource_name))

    # ad group
    agsvc = client.get_service("AdGroupService")
    agop = client.get_type("AdGroupOperation"); ag = agop.create
    ag.name = KEYWORD
    ag.campaign = camp_rn
    ag.status = E.AdGroupStatusEnum.PAUSED
    ag.type_ = E.AdGroupTypeEnum.SEARCH_STANDARD
    ag_rn = agsvc.mutate_ad_groups(customer_id=CID, operations=[agop]).results[0].resource_name
    print(" ✓ Ad group:", ag_rn)

    # ключ
    agcsvc = client.get_service("AdGroupCriterionService")
    kop = client.get_type("AdGroupCriterionOperation"); k = kop.create
    k.ad_group = ag_rn; k.status = E.AdGroupCriterionStatusEnum.ENABLED
    k.keyword.text = KEYWORD; k.keyword.match_type = E.KeywordMatchTypeEnum.PHRASE
    agcsvc.mutate_ad_group_criteria(customer_id=CID, operations=[kop])
    print(' ✓ Ключ: "%s" (phrase)' % KEYWORD)

    # 3 RSA (PAUSED), уникальны за счёт ротации
    adsvc = client.get_service("AdGroupAdService")
    for i in range(3):
        op = client.get_type("AdGroupAdOperation"); aga = op.create
        aga.ad_group = ag_rn; aga.status = E.AdGroupAdStatusEnum.PAUSED
        aga.ad.final_urls.append(FINAL_URL)
        rsa = aga.ad.responsive_search_ad
        for h in PINNED:
            a = client.get_type("AdTextAsset"); a.text = h
            a.pinned_field = E.ServedAssetFieldTypeEnum.HEADLINE_1; rsa.headlines.append(a)
        for h in rot(FREE, i * 6)[:12]:
            a = client.get_type("AdTextAsset"); a.text = h; rsa.headlines.append(a)
        for d in rot(DESCS, i)[:4]:
            a = client.get_type("AdTextAsset"); a.text = d; rsa.descriptions.append(a)
        rsa.path1 = PATH1; rsa.path2 = PATH2
        adsvc.mutate_ad_group_ads(customer_id=CID, operations=[op])
        print(" ✓ RSA %d создан (PAUSED)" % (i + 1))

    # ассеты кампании
    asvc = client.get_service("AssetService")
    F = E.AssetFieldTypeEnum
    aops, plan = [], []
    for lt, d1, d2, u in SITELINKS:
        op = client.get_type("AssetOperation"); x = op.create
        x.sitelink_asset.link_text = lt; x.sitelink_asset.description1 = d1; x.sitelink_asset.description2 = d2
        x.final_urls.append(u); aops.append(op); plan.append(F.SITELINK)
    for c in CALLOUTS:
        op = client.get_type("AssetOperation"); op.create.callout_asset.callout_text = c
        aops.append(op); plan.append(F.CALLOUT)
    for hdr, vals in SNIPPETS:
        op = client.get_type("AssetOperation")
        op.create.structured_snippet_asset.header = hdr
        op.create.structured_snippet_asset.values.extend(vals)
        aops.append(op); plan.append(F.STRUCTURED_SNIPPET)
    ares = asvc.mutate_assets(customer_id=CID, operations=aops)
    casvc = client.get_service("CampaignAssetService")
    ca_ops = []
    for ftype, rn in zip(plan, [r.resource_name for r in ares.results]):
        o = client.get_type("CampaignAssetOperation")
        o.create.campaign = camp_rn; o.create.asset = rn; o.create.field_type = ftype
        ca_ops.append(o)
    casvc.mutate_campaign_assets(customer_id=CID, operations=ca_ops)
    print(" ✓ Ассеты: %d sitelinks + %d callouts + %d snippets" % (len(SITELINKS), len(CALLOUTS), len(SNIPPETS)))

    print("\n ГОТОВО · PAUSED · Campaign ID", camp_id)
    print(" Проверка: https://ads.google.com/aw/campaigns?campaignId=%s" % camp_id)


if __name__ == "__main__":
    try:
        run()
    except GoogleAdsException as ex:
        print("GoogleAdsException:")
        for e in ex.failure.errors:
            print("  -", e.message)
        sys.exit(1)
