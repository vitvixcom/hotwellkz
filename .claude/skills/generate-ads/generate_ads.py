#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Движок скилла /generate-ads: валидация и сборка RSA-объявлений + ассетов кампании
по anatomy-of-a-good-ad.md и ad-assets-best-practices.md. Всё создаётся PAUSED.

Использование:
  python generate_ads.py validate spec.json          # только проверка длин/редполитики
  python generate_ads.py build    spec.json          # проверка + создание через Google Ads API

Формат spec.json:
{
  "customer_id": "8802382037",
  "ad_group_id": "206423446508",          # для RSA (можно опустить, если только ассеты)
  "campaign_id": "23991449173",            # для ассетов уровня кампании (можно опустить)
  "final_url": "https://hotwellkz.kz/astana-sip-doma.html",
  "path1": "Астана", "path2": "СИП-дома",
  "rsas": [
    {"pinned_h1": ["...", "...", "..."], "headlines": ["...12 шт..."], "descriptions": ["...4 шт..."]}
  ],
  "assets": {
    "sitelinks": [{"text":"...", "desc1":"...", "desc2":"...", "url":"https://..."}],
    "callouts": ["...", "..."],
    "snippets": [{"header":"Услуги", "values":["...", "..."]}]
  }
}
Длины (символы): заголовок ≤30, описание ≤90, path ≤15; sitelink title ≤25, desc ≤35;
callout ≤25; значение snippet ≤25; business name ≤25.
"""
import os, sys, json, re

# ---------- РЕДПОЛИТИКА (проверки строк) ----------
EMOJI = re.compile("[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]")

def is_caps_word(w):
    letters = [c for c in w if c.isalpha()]
    return len(letters) > 1 and "".join(letters) == "".join(letters).upper()

def caps_run(s):
    words = re.findall(r"[^\s]+", s)
    run = 0
    for w in words:
        if is_caps_word(w):
            run += 1
            if run >= 2:
                return True
        else:
            run = 0
    return False

def check_headline(h):
    errs, warns = [], []
    if len(h) > 30: errs.append("заголовок >30 (%d): %r" % (len(h), h))
    if "!" in h: errs.append("в заголовке нельзя '!': %r" % h)
    if caps_run(h): errs.append("два КАПС-слова подряд: %r" % h)
    if re.search(r"\d[\d\s\-\(\)]{5,}\d", h): errs.append("похоже на телефон в заголовке: %r" % h)
    if EMOJI.search(h) or h.count("★") > 1 or re.search(r"(→|>>>|·{2,}|!{2,}|\.{3,})", h):
        errs.append("запрещённые символы/повтор пунктуации: %r" % h)
    if re.search(r"#\s*1|№\s*1", h): errs.append("необоснованный '#1/№1': %r" % h)
    if re.search(r"\bлучш", h.lower()): warns.append("превосходная степень без пруфа ('лучший'): %r" % h)
    return errs, warns

def check_desc(d):
    errs, warns = [], []
    if len(d) > 90: errs.append("описание >90 (%d): %r" % (len(d), d))
    if d.count("!") > 1: errs.append("в описании больше одного '!': %r" % d)
    if caps_run(d): errs.append("два КАПС-слова подряд: %r" % d)
    if EMOJI.search(d) or d.count("★") > 1 or re.search(r"(→|>>>|!{2,}|\.{3,})", d):
        errs.append("запрещённые символы/повтор пунктуации: %r" % d)
    return errs, warns


def validate(spec):
    errs, warns = [], []
    p1, p2 = spec.get("path1", ""), spec.get("path2", "")
    if len(p1) > 15: errs.append("path1 >15: %r" % p1)
    if len(p2) > 15: errs.append("path2 >15: %r" % p2)

    for i, rsa in enumerate(spec.get("rsas", []), 1):
        pin = rsa.get("pinned_h1", []); free = rsa.get("headlines", []); desc = rsa.get("descriptions", [])
        if len(pin) < 2: errs.append("RSA %d: нужно ≥2 закреплённых заголовка (ключ) в поз.1" % i)
        if len(pin) + len(free) > 15: errs.append("RSA %d: суммарно >15 заголовков" % i)
        if len(pin) + len(free) < 3: errs.append("RSA %d: <3 заголовков" % i)
        if not (2 <= len(desc) <= 4): errs.append("RSA %d: описаний должно быть 2–4 (есть %d)" % (i, len(desc)))
        seen = set()
        for h in pin + free:
            e, w = check_headline(h); errs += ["RSA %d: %s" % (i, x) for x in e]; warns += ["RSA %d: %s" % (i, x) for x in w]
            k = h.lower().strip()
            if k in seen: warns.append("RSA %d: дубль заголовка: %r" % (i, h))
            seen.add(k)
        dl = sum(d.count("!") for d in desc)
        if dl > 1: errs.append("RSA %d: '!' встречается в описаниях %d раз (макс 1 на объявление)" % (i, dl))
        for d in desc:
            e, w = check_desc(d); errs += ["RSA %d: %s" % (i, x) for x in e]; warns += ["RSA %d: %s" % (i, x) for x in w]

    a = spec.get("assets", {})
    for sl in a.get("sitelinks", []):
        if len(sl.get("text", "")) > 25: errs.append("sitelink title >25: %r" % sl.get("text"))
        if len(sl.get("desc1", "")) > 35: errs.append("sitelink desc1 >35: %r" % sl.get("desc1"))
        if len(sl.get("desc2", "")) > 35: errs.append("sitelink desc2 >35: %r" % sl.get("desc2"))
        if not sl.get("url", "").startswith("http"): errs.append("sitelink без url: %r" % sl.get("text"))
    for c in a.get("callouts", []):
        if len(c) > 25: errs.append("callout >25: %r" % c)
    for sn in a.get("snippets", []):
        if len(sn.get("values", [])) < 3: errs.append("snippet '%s': <3 значений" % sn.get("header"))
        for v in sn.get("values", []):
            if len(v) > 25: errs.append("snippet значение >25: %r" % v)
    return errs, warns


def report(spec):
    errs, warns = validate(spec)
    print("=== ВАЛИДАЦИЯ ===")
    for r_i, rsa in enumerate(spec.get("rsas", []), 1):
        print("RSA %d: %d заголовков (%d закреплены), %d описаний" %
              (r_i, len(rsa.get("pinned_h1", [])) + len(rsa.get("headlines", [])),
               len(rsa.get("pinned_h1", [])), len(rsa.get("descriptions", []))))
    a = spec.get("assets", {})
    print("Ассеты: sitelinks %d, callouts %d, snippets %d" %
          (len(a.get("sitelinks", [])), len(a.get("callouts", [])), len(a.get("snippets", []))))
    for w in warns: print("  ⚠︎", w)
    for e in errs: print("  ✗", e)
    print("ИТОГ:", "ОШИБОК НЕТ — можно собирать" if not errs else "ЕСТЬ ОШИБКИ (%d) — собирать нельзя" % len(errs))
    return errs


# ---------- СБОРКА ЧЕРЕЗ API (PAUSED) ----------
def build(spec):
    if report(spec):
        sys.exit("Сборка отменена: исправьте ошибки.")
    from google.ads.googleads.client import GoogleAdsClient
    from google.ads.googleads.errors import GoogleAdsException
    CID = spec.get("customer_id") or os.environ["GOOGLE_ADS_CUSTOMER_ID"]
    CID = CID.replace("-", "")
    cfg = dict(developer_token=os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
               client_id=os.environ["GOOGLE_ADS_CLIENT_ID"],
               client_secret=os.environ["GOOGLE_ADS_CLIENT_SECRET"],
               refresh_token=os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
               login_customer_id=CID, use_proto_plus=True)
    client = GoogleAdsClient.load_from_dict(cfg)
    E = client.enums
    try:
        # RSA
        ag_id = spec.get("ad_group_id")
        if ag_id and spec.get("rsas"):
            ag_rn = "customers/%s/adGroups/%s" % (CID, ag_id)
            adsvc = client.get_service("AdGroupAdService")
            for n, rsa in enumerate(spec["rsas"], 1):
                op = client.get_type("AdGroupAdOperation")
                aga = op.create
                aga.ad_group = ag_rn
                aga.status = E.AdGroupAdStatusEnum.PAUSED
                aga.ad.final_urls.append(spec["final_url"])
                r = aga.ad.responsive_search_ad
                for h in rsa["pinned_h1"]:
                    a = client.get_type("AdTextAsset"); a.text = h
                    a.pinned_field = E.ServedAssetFieldTypeEnum.HEADLINE_1; r.headlines.append(a)
                for h in rsa["headlines"]:
                    a = client.get_type("AdTextAsset"); a.text = h; r.headlines.append(a)
                for d in rsa["descriptions"]:
                    a = client.get_type("AdTextAsset"); a.text = d; r.descriptions.append(a)
                if spec.get("path1"): r.path1 = spec["path1"]
                if spec.get("path2"): r.path2 = spec["path2"]
                adsvc.mutate_ad_group_ads(customer_id=CID, operations=[op])
                print(" ✓ RSA %d создан (PAUSED)" % n)

        # Ассеты уровня кампании
        camp_id = spec.get("campaign_id"); a = spec.get("assets", {})
        if camp_id and a:
            camp_rn = "customers/%s/campaigns/%s" % (CID, camp_id)
            asvc = client.get_service("AssetService")
            F = E.AssetFieldTypeEnum
            ops, plan = [], []
            for sl in a.get("sitelinks", []):
                op = client.get_type("AssetOperation"); x = op.create
                x.sitelink_asset.link_text = sl["text"]
                if sl.get("desc1"): x.sitelink_asset.description1 = sl["desc1"]
                if sl.get("desc2"): x.sitelink_asset.description2 = sl["desc2"]
                x.final_urls.append(sl["url"]); ops.append(op); plan.append(F.SITELINK)
            for c in a.get("callouts", []):
                op = client.get_type("AssetOperation"); op.create.callout_asset.callout_text = c
                ops.append(op); plan.append(F.CALLOUT)
            for sn in a.get("snippets", []):
                op = client.get_type("AssetOperation")
                op.create.structured_snippet_asset.header = sn["header"]
                op.create.structured_snippet_asset.values.extend(sn["values"])
                ops.append(op); plan.append(F.STRUCTURED_SNIPPET)
            if ops:
                res = asvc.mutate_assets(customer_id=CID, operations=ops)
                casvc = client.get_service("CampaignAssetService")
                ca_ops = []
                for ftype, rn in zip(plan, [r.resource_name for r in res.results]):
                    o = client.get_type("CampaignAssetOperation")
                    o.create.campaign = camp_rn; o.create.asset = rn; o.create.field_type = ftype
                    ca_ops.append(o)
                casvc.mutate_campaign_assets(customer_id=CID, operations=ca_ops)
                print(" ✓ Ассетов привязано к кампании: %d" % len(ca_ops))
        print("\nГОТОВО · всё PAUSED.")
    except GoogleAdsException as ex:
        print("GoogleAdsException:")
        for e in ex.failure.errors: print("  -", e.message)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Использование: generate_ads.py [validate|build] spec.json")
    mode, path = sys.argv[1], sys.argv[2]
    spec = json.load(open(path, encoding="utf-8"))
    if mode == "validate":
        sys.exit(1 if report(spec) else 0)
    elif mode == "build":
        build(spec)
    else:
        sys.exit("Неизвестный режим: %s" % mode)
