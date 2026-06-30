#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared Negative Keyword List «Universal Service Business Negatives v1»
по universal-negative-keywords.md (секции A.1–A.7, ~150 универсальных терминов).
Создаёт shared set, добавляет минус-слова и прикрепляет к кампании Астана.

Match type: BROAD для всех (в A.1–A.7 нет терминов в кавычках/скобках).
Если бы термин был "в кавычках" → PHRASE, [в скобках] → EXACT.
"""
import os, sys
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CID = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
CAMPAIGN_ID = os.environ.get("CAMPAIGN_ID", "23991449173")
camp_rn = "customers/%s/campaigns/%s" % (CID, CAMPAIGN_ID)
LIST_NAME = "Universal Service Business Negatives v1"

# --- A.1 Job seekers ---
A1 = ["jobs", "job", "hiring", "recruit", "recruiting", "recruitment", "recruiter",
      "career", "careers", "employment", "employer", "employee", "salary", "salaries",
      "wage", "wages", "hourly pay", "resume", "cv", "intern", "interns", "internship",
      "internships", "apprentice", "apprentices", "apprenticeship", "apprenticeships",
      "volunteer", "vacancy", "vacancies", "position open", "hiring near me",
      "work from home", "indeed", "glassdoor", "ziprecruiter"]
# --- A.2 DIY / How-to / Tutorial ---
A2 = ["diy", "do it yourself", "how to", "howto", "how do", "how do you", "tutorial",
      "tutorials", "guide", "guides", "step by step", "instructions", "youtube", "video",
      "videos", "template", "templates", "example", "examples", "how to fix",
      "how to repair", "how to install", "how to remove", "how to clean", "how to replace",
      "how to build", "homemade", "yourself"]
# --- A.3 Education / Training / Schools ---
A3 = ["school", "schools", "schooling", "college", "university", "class", "classes",
      "course", "courses", "training", "trainee", "trained", "certification",
      "certificate", "certified", "license cost", "licensing", "license requirement",
      "license requirements", "become a", "how to become", "exam"]
# --- A.4 Free / Discount / Cheap ---
A4 = ["free", "freebie", "giveaway", "giveaways", "sample", "samples", "trial",
      "discount", "discounted", "voucher", "coupon", "coupons", "promo code",
      "clearance", "secondhand"]
# --- A.5 Informational research ---
A5 = ["what is", "what is a", "what does", "what are", "meaning", "definition",
      "wikipedia", "wiki", "reddit", "quora", "forum", "forums", "blog", "review",
      "reviews", "ratings"]
# --- A.6 Customer support / existing customers ---
A6 = ["complaint", "complaints", "refund", "refunds", "return policy", "cancel",
      "cancellation", "warranty claim", "problem", "problems", "not working", "broken",
      "contact", "phone number", "customer service", "help", "login", "sign in"]
# --- A.7 Restricted / unsafe ---
A7 = ["porn", "adult", "nude", "sex", "gambling", "casino", "weed", "marijuana", "cbd",
      "crypto", "bitcoin", "nft", "mlm", "ponzi"]

SECTIONS = A1 + A2 + A3 + A4 + A5 + A6 + A7


def parse_term(t):
    """Возвращает (text, match_type_name). Кавычки → PHRASE, скобки → EXACT, иначе BROAD."""
    t = t.strip()
    if len(t) >= 2 and t[0] == '"' and t[-1] == '"':
        return t[1:-1].strip(), "PHRASE"
    if len(t) >= 2 and t[0] == '[' and t[-1] == ']':
        return t[1:-1].strip(), "EXACT"
    return t, "BROAD"


# дедуп без учёта регистра, сохраняя порядок
seen = set()
TERMS = []
for raw in SECTIONS:
    text, mt = parse_term(raw)
    key = (text.lower(), mt)
    if key in seen:
        continue
    seen.add(key)
    TERMS.append((text, mt))

# валидация: ≤80 символов, ≤10 слов
errs = [f"term too long/many words: {t!r}" for t, _ in TERMS if len(t) > 80 or len(t.split()) > 10]
if errs:
    sys.exit("Невалидные термины:\n  " + "\n  ".join(errs))

cfg = dict(developer_token=os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
           client_id=os.environ["GOOGLE_ADS_CLIENT_ID"],
           client_secret=os.environ["GOOGLE_ADS_CLIENT_SECRET"],
           refresh_token=os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
           login_customer_id=CID, use_proto_plus=True)
client = GoogleAdsClient.load_from_dict(cfg)


def run():
    by_mt = {}
    for _, mt in TERMS:
        by_mt[mt] = by_mt.get(mt, 0) + 1
    print("Терминов после дедупа: %d  %s" % (len(TERMS), by_mt))

    # 1) shared set
    ssvc = client.get_service("SharedSetService")
    sop = client.get_type("SharedSetOperation")
    sop.create.name = LIST_NAME
    sop.create.type_ = client.enums.SharedSetTypeEnum.NEGATIVE_KEYWORDS
    ss_rn = ssvc.mutate_shared_sets(customer_id=CID, operations=[sop]).results[0].resource_name
    print(" ✓ Shared set:", ss_rn)

    # 2) минус-слова в shared set
    scsvc = client.get_service("SharedCriterionService")
    ops = []
    for text, mt in TERMS:
        op = client.get_type("SharedCriterionOperation")
        op.create.shared_set = ss_rn
        op.create.keyword.text = text
        op.create.keyword.match_type = client.enums.KeywordMatchTypeEnum[mt]
        ops.append(op)
    # батчами по 1000 (лимит операций на запрос)
    added = 0
    for i in range(0, len(ops), 1000):
        res = scsvc.mutate_shared_criteria(customer_id=CID, operations=ops[i:i + 1000])
        added += len(res.results)
    print(" ✓ Добавлено минус-слов: %d" % added)

    # 3) прикрепить к кампании
    cssvc = client.get_service("CampaignSharedSetService")
    cop = client.get_type("CampaignSharedSetOperation")
    cop.create.campaign = camp_rn
    cop.create.shared_set = ss_rn
    cssvc.mutate_campaign_shared_sets(customer_id=CID, operations=[cop])
    print(" ✓ Список прикреплён к кампании", CAMPAIGN_ID)
    print("\n Проверка: https://ads.google.com/aw/campaigns?campaignId=%s" % CAMPAIGN_ID)


if __name__ == "__main__":
    try:
        run()
    except GoogleAdsException as ex:
        print("GoogleAdsException:")
        for e in ex.failure.errors:
            print("  -", e.message)
        sys.exit(1)
