#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Добавляет campaign-level минус-слова (по одобрению пользователя), SOP find-and-add-negatives.md.
Проверяет дубли, добавляет, затем верифицирует. NEGATIVES берётся из аргументов/по умолчанию.
"""
import os, sys
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CID = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
CAMPAIGN_ID = os.environ["CAMPAIGN_ID"]
camp_rn = "customers/%s/campaigns/%s" % (CID, CAMPAIGN_ID)

# (текст, match_type) — одобрено: BAD-группы 1–4
NEGATIVES = [
    ("модульный", "PHRASE"), ("модульные", "PHRASE"), ("модульных", "PHRASE"),  # гр.1 другой продукт
    ("контейнер", "PHRASE"), ("контейнеров", "PHRASE"),                          # гр.2 другой продукт
    ("модекс", "PHRASE"), ("модех", "PHRASE"), ("modex", "PHRASE"),              # гр.3 бренд конкурента
    ("на продажу", "PHRASE"),                                                     # гр.4 вторичка
]

cfg = dict(developer_token=os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
           client_id=os.environ["GOOGLE_ADS_CLIENT_ID"],
           client_secret=os.environ["GOOGLE_ADS_CLIENT_SECRET"],
           refresh_token=os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
           login_customer_id=CID, use_proto_plus=True)
client = GoogleAdsClient.load_from_dict(cfg)
ga = client.get_service("GoogleAdsService")
E = client.enums


def existing():
    q = ("SELECT campaign_criterion.keyword.text, campaign_criterion.keyword.match_type "
         "FROM campaign_criterion WHERE campaign.id = %s AND campaign_criterion.negative = TRUE "
         "AND campaign_criterion.type = KEYWORD" % CAMPAIGN_ID)
    have = set()
    for r in ga.search(customer_id=CID, query=q):
        k = r.campaign_criterion.keyword
        have.add((k.text.lower(), k.match_type.name))
    return have


def main():
    have = existing()
    svc = client.get_service("CampaignCriterionService")
    ops, planned = [], []
    for text, mt in NEGATIVES:
        if (text.lower(), mt) in have:
            print("• уже есть, пропускаю:", text, mt)
            continue
        op = client.get_type("CampaignCriterionOperation")
        c = op.create
        c.campaign = camp_rn
        c.negative = True
        c.keyword.text = text
        c.keyword.match_type = E.KeywordMatchTypeEnum[mt]
        ops.append(op); planned.append((text, mt))
    if not ops:
        print("Нечего добавлять."); return
    res = svc.mutate_campaign_criteria(customer_id=CID, operations=ops)
    print("✓ Добавлено минус-слов: %d" % len(res.results))
    for (text, mt), r in zip(planned, res.results):
        print("   · «%s» (%s) → %s" % (text, mt, r.resource_name))

    # верификация
    have2 = existing()
    ok = all((t.lower(), mt) in have2 for t, mt in NEGATIVES)
    print("\nВерификация: все %d на месте — %s" % (len(NEGATIVES), "ДА" if ok else "НЕТ"))


if __name__ == "__main__":
    try:
        main()
    except GoogleAdsException as ex:
        print("GoogleAdsException:")
        for e in ex.failure.errors:
            print("  -", e.message)
        sys.exit(1)
