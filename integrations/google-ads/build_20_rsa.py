#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
20 RSA-объявлений (все PAUSED) в ad group кампании
[SKAG] СИП-панельные дома Астана | 20260630_0913 (ID 23991449173).

По SOP anatomy-of-a-good-ad.md:
- 15 заголовков на объявление: 3 keyword-варианта закреплены в позиции 1
  + 12 незакреплённых, покрывающих 6 паттернов (offer/trust/urgency/guarantee/CTA/benefit).
- 4 описания (≤90), разные углы.
- path1=Астана, path2=СИП-дома.
- 20 объявлений сделаны уникальными за счёт ротации пулов (закреплённые/свободные/описания),
  чтобы Google не отклонил их как дубликаты.
Длины валидируются ДО вызова API. Создание — батчем с partial_failure, чтобы
увидеть, какие прошли.
"""
import os, sys
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CID = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
CAMPAIGN_ID = os.environ.get("CAMPAIGN_ID", "23991449173")
FINAL_URL = "https://hotwellkz.kz/astana-sip-doma.html"
PATH1, PATH2 = "Астана", "СИП-дома"
N_ADS = 20

# --- закрепляемые в позиции 1 (keyword-варианты), ≤30 ---
PINNED = [
    "СИП-панельные дома Астана",
    "СИП дома в Астане",
    "Дома из СИП-панелей Астана",
    "СИП-панельный дом в Астане",
    "Строим СИП-дома в Астане",
]

# --- свободные заголовки (без закрепления), ≤30, 6 паттернов ---
FREE = [
    # offer / USP
    "Дом под ключ за 30 дней",
    "Цена и сроки в договоре",
    "Фундамент входит в цену",
    "Кровля и доставка в цене",
    "Сборка дома за 30 дней",
    "Монтаж своими бригадами",
    # trust / social proof
    "Своё производство СИП",
    "Тёплый дом без переплат",
    "Строим по Казахстану",
    "Опыт с 2018 года",
    "Производим СИП сами",
    # urgency
    "Заселение через месяц",
    "Тёплый дом к зиме",
    "Старт стройки сразу",
    "Готовый дом за 30 дней",
    # guarantee
    "Гарантия на дом 1 год",
    "Без скрытых доплат",
    "Цену фиксируем в договоре",
    # CTA
    "Расчёт стоимости онлайн",
    "Узнайте цену за 5 минут",
    "Бесплатный выезд замера",
    "Закажите расчёт дома",
    "Получите смету бесплатно",
    # benefit / quality
    "Тёплый дом для зим РК",
    "Энергоэффективный дом",
    "Дом мечты из СИП-панелей",
    "Прочный и тёплый дом",
    "Дом для всей семьи",
]

# --- описания, ≤90 ---
DESCS = [
    "Строим дома из СИП-панелей в Астане под ключ. Цену и сроки фиксируем в договоре.",
    "Своё производство СИП-панелей. Тёплый дом и экономия на отоплении круглый год.",
    "Рассчитайте стоимость онлайн за 5 минут. Гарантия на дом, монтаж нашими бригадами.",
    "Фундамент, проект, кровля и доставка уже в цене. Строим по всему Казахстану.",
    "Дом под ключ за 30 дней. Без скрытых доплат, цена зафиксирована в договоре.",
    "Тёплый дом для суровых зим Казахстана. Энергоэффективные СИП-панели от производителя.",
    "Бесплатный выезд замерщика по Астане. Точный расчёт сметы и сроков строительства.",
    "Работаем с 2018 года, строим по всему Казахстану. Гарантия на дом и честная цена.",
    "Заселяйтесь уже через месяц. Монтаж своими бригадами, фундамент входит в стоимость.",
    "Закажите онлайн-расчёт дома из СИП-панелей. Цена под ключ без скрытых платежей.",
    "Производим СИП-панели сами — поэтому цена ниже, а качество под контролем.",
    "Готовый тёплый дом к зиме. Фундамент, кровля и доставка уже включены в цену.",
    "Дом мечты из СИП-панелей в Астане. Расчёт стоимости за 5 минут, гарантия 1 год.",
    "Строительство домов под ключ в Астане и области. Сроки и цена закреплены договором.",
    "Экономьте на отоплении круглый год. Тёплые СИП-дома от собственного производства.",
    "Прочный дом для всей семьи за 30 дней. Монтаж выполняют наши штатные бригады.",
    "Узнайте цену дома онлайн за 5 минут. Бесплатная консультация и выезд на участок.",
    "СИП-дома под ключ с гарантией. Фундамент, стены, кровля и доставка уже в цене.",
    "Честная цена без переплат и скрытых доплат. Фиксируем стоимость и сроки в договоре.",
    "Тёплый и энергоэффективный дом в Астане. Своё производство, монтаж под ключ за месяц.",
]

# ---- валидация длин ДО API ----
errs = []
for h in PINNED + FREE:
    if len(h) > 30:
        errs.append("Заголовок >30: %r (%d)" % (h, len(h)))
for d in DESCS:
    if len(d) > 90:
        errs.append("Описание >90: %r (%d)" % (d, len(d)))
for p in (PATH1, PATH2):
    if len(p) > 15:
        errs.append("Path >15: %r (%d)" % (p, len(p)))
if len(FREE) < 12:
    errs.append("Свободных заголовков <12")
if errs:
    sys.exit("Длины не проходят:\n  " + "\n  ".join(errs))


def rot(lst, n):
    n %= len(lst)
    return lst[n:] + lst[:n]


cfg = dict(developer_token=os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
           client_id=os.environ["GOOGLE_ADS_CLIENT_ID"],
           client_secret=os.environ["GOOGLE_ADS_CLIENT_SECRET"],
           refresh_token=os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
           login_customer_id=CID, use_proto_plus=True)
client = GoogleAdsClient.load_from_dict(cfg)
ga = client.get_service("GoogleAdsService")


def get_ad_group_rn():
    q = ("SELECT ad_group.resource_name FROM ad_group "
         "WHERE campaign.id=%s AND ad_group.status != 'REMOVED' LIMIT 1" % CAMPAIGN_ID)
    for r in ga.search(customer_id=CID, query=q):
        return r.ad_group.resource_name
    sys.exit("Не найдена ad group в кампании %s" % CAMPAIGN_ID)


def build_op(ag_rn, i):
    op = client.get_type("AdGroupAdOperation")
    aga = op.create
    aga.ad_group = ag_rn
    aga.status = client.enums.AdGroupAdStatusEnum.PAUSED
    ad = aga.ad
    ad.final_urls.append(FINAL_URL)
    rsa = ad.responsive_search_ad
    pinned = rot(PINNED, i)[:3]
    free = rot(FREE, i)[:12]
    descs = rot(DESCS, i)[:4]
    for h in pinned:
        a = client.get_type("AdTextAsset")
        a.text = h
        a.pinned_field = client.enums.ServedAssetFieldTypeEnum.HEADLINE_1
        rsa.headlines.append(a)
    for h in free:
        a = client.get_type("AdTextAsset")
        a.text = h
        rsa.headlines.append(a)
    for d in descs:
        a = client.get_type("AdTextAsset")
        a.text = d
        rsa.descriptions.append(a)
    rsa.path1 = PATH1
    rsa.path2 = PATH2
    return op


def run():
    ag_rn = get_ad_group_rn()
    print("Ad group:", ag_rn)
    adsvc = client.get_service("AdGroupAdService")
    ops = [build_op(ag_rn, i) for i in range(N_ADS)]

    req = client.get_type("MutateAdGroupAdsRequest")
    req.customer_id = CID
    req.operations = ops
    req.partial_failure = True
    res = adsvc.mutate_ad_group_ads(request=req)

    ok = sum(1 for r in res.results if r.resource_name)
    print(" ✓ Создано RSA: %d из %d (все PAUSED)" % (ok, N_ADS))
    if res.partial_failure_error and res.partial_failure_error.code != 0:
        # распарсить ошибки по операциям
        from google.rpc import status_pb2
        from google.ads.googleads.errors import GoogleAdsFailure
        detail_type = "google.ads.googleads.v24.errors.GoogleAdsFailure"
        st = res.partial_failure_error
        print(" ! Часть операций не прошла:")
        for d in st.details:
            if d.type_url.endswith(detail_type):
                fail = client.get_type("GoogleAdsFailure")
                fail._pb.MergeFromString(d.value)
                for e in fail.errors:
                    idx = None
                    for el in e.location.field_path_elements:
                        if el.field_name == "operations" and el.HasField("index"):
                            idx = el.index
                    print("   - op[%s]: %s" % (idx, e.message))
    # вывести список созданных id
    ids = [r.resource_name.split("~")[-1] for r in res.results if r.resource_name]
    if ids:
        print(" Созданные ad IDs:", ", ".join(ids))


if __name__ == "__main__":
    try:
        run()
    except GoogleAdsException as ex:
        print("GoogleAdsException:")
        for e in ex.failure.errors:
            print("  -", e.message)
        sys.exit(1)
