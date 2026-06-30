#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
20 RSA (PAUSED) в ad group кампании «Каркасные дома Астана» (id 23992790071).
По anatomy-of-a-good-ad.md: 3 keyword-заголовка закреплены в поз.1 + 12 свободных
(6 паттернов) + 4 описания. Уникальность 20 объявлений — ротацией пулов.
"""
import os, sys
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CID = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
CAMPAIGN_ID = os.environ.get("CAMPAIGN_ID", "23992790071")
FINAL_URL = "https://hotwellkz.kz/astana-karkasnye-doma.html"
PATH1, PATH2 = "Астана", "Каркасные"
N_ADS = 20

PINNED = [
    "Каркасные дома Астана", "Каркасный дом в Астане", "Каркасные дома в Астане",
    "Каркасный дом Астана", "Строим каркасные дома",
]
FREE = [
    "Дом под ключ за 30 дней", "Цена и сроки в договоре", "Фундамент входит в цену",
    "Кровля и доставка в цене", "Сборка дома за 30 дней", "Монтаж своими бригадами",
    "Каркасный дом под ключ", "Своё производство", "Тёплый дом без переплат",
    "Строим по Казахстану", "Опыт с 2012 года", "Производим сами",
    "Заселение через месяц", "Тёплый дом к зиме", "Старт стройки сразу",
    "Готовый дом за 30 дней", "Гарантия на дом 1 год", "Без скрытых доплат",
    "Цену фиксируем в договоре", "Своя бригада монтажа", "Расчёт стоимости онлайн",
    "Узнайте цену за 5 минут", "Бесплатный выезд замера", "Закажите расчёт дома",
    "Получите смету бесплатно", "Тёплый дом для зим РК", "Энергоэффективный дом",
    "Прочный и тёплый дом", "Дом для всей семьи",
]
DESCS = [
    "Строим каркасные дома в Астане под ключ. Цену и сроки фиксируем в договоре.",
    "Тёплый каркасный дом для суровых зим Казахстана. Монтаж нашими бригадами.",
    "Рассчитайте стоимость онлайн за 5 минут. Фундамент и кровля уже в цене.",
    "Каркасный дом под ключ за 30 дней. Работаем по всему Казахстану с 2012 года.",
    "Без скрытых доплат — цена и сроки зафиксированы в договоре. Гарантия на дом.",
    "Энергоэффективный каркасный дом в Астане. Своё производство, монтаж за месяц.",
    "Бесплатный выезд замерщика по Астане. Точный расчёт сметы и сроков стройки.",
    "Работаем с 2012 года по всему Казахстану. Гарантия на дом и честная цена.",
    "Заселяйтесь уже через месяц. Монтаж своими бригадами, фундамент в стоимости.",
    "Закажите онлайн-расчёт каркасного дома. Цена под ключ без скрытых платежей.",
    "Производим домокомплекты сами — поэтому цена ниже, а качество под контролем.",
    "Готовый тёплый дом к зиме. Фундамент, кровля и доставка уже включены в цену.",
    "Дом мечты под ключ в Астане. Расчёт стоимости за 5 минут, гарантия 1 год.",
    "Строительство каркасных домов под ключ в Астане и области. Сроки в договоре.",
    "Экономьте на отоплении круглый год. Тёплые каркасные дома от производителя.",
    "Прочный дом для всей семьи за 30 дней. Монтаж выполняют наши штатные бригады.",
    "Узнайте цену дома онлайн за 5 минут. Бесплатная консультация и выезд на участок.",
    "Каркасные дома под ключ с гарантией. Фундамент, стены, кровля и доставка в цене.",
    "Честная цена без переплат и скрытых доплат. Фиксируем стоимость и сроки в договоре.",
    "Тёплый и энергоэффективный дом в Астане. Своё производство, монтаж под ключ за месяц.",
]

errs = []
for h in PINNED + FREE:
    if len(h) > 30: errs.append("Заголовок >30: %r (%d)" % (h, len(h)))
for d in DESCS:
    if len(d) > 90: errs.append("Описание >90: %r (%d)" % (d, len(d)))
for p in (PATH1, PATH2):
    if len(p) > 15: errs.append("Path >15: %r (%d)" % (p, len(p)))
if len(FREE) < 12: errs.append("Свободных заголовков <12")
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
ga = client.get_service("GoogleAdsService")
E = client.enums


def ad_group_rn():
    q = ("SELECT ad_group.resource_name FROM ad_group WHERE campaign.id=%s "
         "AND ad_group.status != 'REMOVED' LIMIT 1" % CAMPAIGN_ID)
    for r in ga.search(customer_id=CID, query=q):
        return r.ad_group.resource_name
    sys.exit("Ad group не найдена в кампании %s" % CAMPAIGN_ID)


def build_op(ag_rn, i):
    op = client.get_type("AdGroupAdOperation"); aga = op.create
    aga.ad_group = ag_rn; aga.status = E.AdGroupAdStatusEnum.PAUSED
    aga.ad.final_urls.append(FINAL_URL)
    rsa = aga.ad.responsive_search_ad
    for h in rot(PINNED, i)[:3]:
        a = client.get_type("AdTextAsset"); a.text = h
        a.pinned_field = E.ServedAssetFieldTypeEnum.HEADLINE_1; rsa.headlines.append(a)
    for h in rot(FREE, i)[:12]:
        a = client.get_type("AdTextAsset"); a.text = h; rsa.headlines.append(a)
    for d in rot(DESCS, i)[:4]:
        a = client.get_type("AdTextAsset"); a.text = d; rsa.descriptions.append(a)
    rsa.path1 = PATH1; rsa.path2 = PATH2
    return op


def run():
    ag_rn = ad_group_rn()
    print("Ad group:", ag_rn)
    adsvc = client.get_service("AdGroupAdService")
    req = client.get_type("MutateAdGroupAdsRequest")
    req.customer_id = CID
    req.operations = [build_op(ag_rn, i) for i in range(N_ADS)]
    req.partial_failure = True
    res = adsvc.mutate_ad_group_ads(request=req)
    ok = sum(1 for r in res.results if r.resource_name)
    print(" ✓ Создано RSA: %d из %d (все PAUSED)" % (ok, N_ADS))
    if res.partial_failure_error and res.partial_failure_error.code != 0:
        print(" ! Часть не прошла:")
        for d in res.partial_failure_error.details:
            if d.type_url.endswith("errors.GoogleAdsFailure"):
                fail = client.get_type("GoogleAdsFailure"); fail._pb.MergeFromString(d.value)
                for e in fail.errors:
                    print("   -", e.message)


if __name__ == "__main__":
    try:
        run()
    except GoogleAdsException as ex:
        print("GoogleAdsException:")
        for e in ex.failure.errors:
            print("  -", e.message)
        sys.exit(1)
