#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Прикрепляет существующие общие списки минус-слов (Shared Negative Keyword Lists)
к кампании CAMPAIGN_ID. Идемпотентно: уже прикреплённые — пропускает.
По умолчанию цепляет русско-казахский список (рабочий) и, если есть, английский.
"""
import os, sys
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CID = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
CAMPAIGN_ID = os.environ["CAMPAIGN_ID"]
# какие списки цеплять (по имени); порядок = приоритет
WANT = [n.strip() for n in os.environ.get(
    "LIST_NAMES", "Универсальные минус-слова RU+KZ v1|Universal Service Business Negatives v1"
).split("|") if n.strip()]
camp_rn = "customers/%s/campaigns/%s" % (CID, CAMPAIGN_ID)

cfg = dict(developer_token=os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
           client_id=os.environ["GOOGLE_ADS_CLIENT_ID"],
           client_secret=os.environ["GOOGLE_ADS_CLIENT_SECRET"],
           refresh_token=os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
           login_customer_id=CID, use_proto_plus=True)
client = GoogleAdsClient.load_from_dict(cfg)
ga = client.get_service("GoogleAdsService")


def shared_sets():
    out = {}
    for r in ga.search(customer_id=CID, query=(
            "SELECT shared_set.id, shared_set.name, shared_set.member_count "
            "FROM shared_set WHERE shared_set.type = 'NEGATIVE_KEYWORDS' "
            "AND shared_set.status = 'ENABLED'")):
        out[r.shared_set.name] = (r.shared_set.resource_name, r.shared_set.member_count)
    return out


def attached():
    have = set()
    for r in ga.search(customer_id=CID, query=(
            "SELECT shared_set.resource_name FROM campaign_shared_set "
            "WHERE campaign.id = %s" % CAMPAIGN_ID)):
        have.add(r.shared_set.resource_name)
    return have


def main():
    sets = shared_sets()
    have = attached()
    svc = client.get_service("CampaignSharedSetService")
    ops, done = [], []
    for name in WANT:
        if name not in sets:
            print("• список не найден, пропуск:", name); continue
        rn, cnt = sets[name]
        if rn in have:
            print("• уже прикреплён:", name); continue
        op = client.get_type("CampaignSharedSetOperation")
        op.create.campaign = camp_rn
        op.create.shared_set = rn
        ops.append(op); done.append((name, cnt))
    if not ops:
        print("Нечего прикреплять."); return
    svc.mutate_campaign_shared_sets(customer_id=CID, operations=ops)
    for name, cnt in done:
        print("✓ Прикреплён список «%s» (%d слов)" % (name, cnt))
    print("\nПроверка: https://ads.google.com/aw/campaigns?campaignId=%s" % CAMPAIGN_ID)


if __name__ == "__main__":
    try:
        main()
    except GoogleAdsException as ex:
        print("GoogleAdsException:")
        for e in ex.failure.errors:
            print("  -", e.message)
        sys.exit(1)
