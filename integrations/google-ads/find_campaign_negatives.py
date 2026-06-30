#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Поиск кандидатов в минус-слова по SOP find-and-add-negatives.md.
Находит кампанию по имени (CAMPAIGN_NAME) или ID (CAMPAIGN_ID), тянет search_term_view
за DAYS дней, помечает кандидатов (показы >= MIN_IMPR и (0 конверсий или дорого).
НИЧЕГО НЕ ДОБАВЛЯЕТ — только выводит список и пишет JSON для ревью.
"""
import os, sys, json
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CID = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
CAMPAIGN_NAME = os.environ.get("CAMPAIGN_NAME", "")
CAMPAIGN_ID = os.environ.get("CAMPAIGN_ID", "")
DAYS = int(os.environ.get("DAYS", "30"))
MIN_IMPR = int(os.environ.get("MIN_IMPR", "100"))
MIN_COST = float(os.environ.get("MIN_COST", "10"))
OUT = os.environ.get("OUT", "")

cfg = dict(developer_token=os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
           client_id=os.environ["GOOGLE_ADS_CLIENT_ID"],
           client_secret=os.environ["GOOGLE_ADS_CLIENT_SECRET"],
           refresh_token=os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
           login_customer_id=CID, use_proto_plus=True)
client = GoogleAdsClient.load_from_dict(cfg)
ga = client.get_service("GoogleAdsService")


def find_campaign():
    if CAMPAIGN_ID:
        q = "SELECT campaign.id, campaign.name FROM campaign WHERE campaign.id = %s" % CAMPAIGN_ID
    else:
        nm = CAMPAIGN_NAME.replace("'", "\\'")
        q = "SELECT campaign.id, campaign.name FROM campaign WHERE campaign.name = '%s'" % nm
    for r in ga.search(customer_id=CID, query=q):
        return str(r.campaign.id), r.campaign.name
    return None, None


def main():
    cid, cname = find_campaign()
    if not cid:
        sys.exit("Кампания не найдена: %r" % (CAMPAIGN_NAME or CAMPAIGN_ID))
    print("Кампания: %s (id=%s)" % (cname, cid))

    q = ("SELECT search_term_view.search_term, metrics.impressions, metrics.clicks, "
         "metrics.cost_micros, metrics.conversions, metrics.conversions_value, metrics.ctr "
         "FROM search_term_view "
         "WHERE campaign.id = %s AND segments.date DURING LAST_%d_DAYS "
         "ORDER BY metrics.cost_micros DESC" % (cid, DAYS))
    terms = []
    tot_cost = tot_conv = 0.0
    for r in ga.search(customer_id=CID, query=q):
        m = r.metrics
        cost = m.cost_micros / 1e6
        terms.append({
            "term": r.search_term_view.search_term,
            "impr": int(m.impressions), "clicks": int(m.clicks),
            "cost": round(cost, 2), "conv": round(m.conversions, 2),
            "ctr": round(m.ctr * 100, 2),
        })
        tot_cost += cost
        tot_conv += m.conversions
    avg_cpa = (tot_cost / tot_conv) if tot_conv else 0.0

    # пометка кандидатов
    for t in terms:
        strong = t["impr"] >= MIN_IMPR and t["conv"] == 0 and t["cost"] >= MIN_COST
        expensive = avg_cpa > 0 and t["conv"] > 0 and t["cost"] > 2 * avg_cpa
        loose = t["impr"] >= 50 and t["conv"] == 0           # мягкий критерий для малого бюджета
        t["candidate"] = bool(strong or expensive)
        t["loose_candidate"] = bool(loose)

    print("Всего уникальных запросов: %d | расход $%.2f | конверсии %.2f | средн. CPA $%.2f" %
          (len(terms), tot_cost, tot_conv, avg_cpa))
    strict = [t for t in terms if t["candidate"]]
    loose = [t for t in terms if t["loose_candidate"] and not t["candidate"]]
    print("Кандидатов (строгий фильтр ≥%d показов, 0 конв., ≥$%.0f): %d" % (MIN_IMPR, MIN_COST, len(strict)))
    print("Доп. кандидатов (мягкий ≥50 показов, 0 конв.): %d" % len(loose))

    print("\n— Топ запросов по расходу —")
    print("%-5s %-7s %-7s %-6s %-6s  %s" % ("показ", "клики", "расход", "конв", "CTR%", "запрос"))
    for t in terms[:30]:
        flag = "★" if t["candidate"] else ("·" if t["loose_candidate"] else " ")
        print("%1s %4d  %5d  $%-6.2f %-5.2f %-5.1f  %s" %
              (flag, t["impr"], t["clicks"], t["cost"], t["conv"], t["ctr"], t["term"]))

    if OUT:
        json.dump({"campaign_id": cid, "campaign_name": cname, "avg_cpa": round(avg_cpa, 2),
                   "days": DAYS, "terms": terms}, open(OUT, "w"), ensure_ascii=False, indent=2)
        print("\nwritten", OUT)


if __name__ == "__main__":
    try:
        main()
    except GoogleAdsException as ex:
        print("GoogleAdsException:")
        for e in ex.failure.errors:
            print("  -", e.message)
        sys.exit(1)
