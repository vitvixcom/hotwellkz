#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Движок скилла /launch-campaign: из spec.json собирает ПОЛНУЮ SKAG-кампанию Google Ads
(всё PAUSED): бюджет → кампания (Max Conversions) → гео (проксимити город+радиус,
presence) → исключение всех стран кроме страны → язык → расписание → минус-слова
(на уровне кампании + прикрепление общих списков) → ad group → ключ (phrase) →
N RSA (ротация пулов) → ассеты (sitelinks/callouts/snippets) → warm-pixel аудитория +X%.

Использование:
  python launch_campaign.py validate spec.json
  python launch_campaign.py build    spec.json

Минимальный spec (остальное — дефолты ниже):
{
  "campaign_name": "[SKAG] Каркасные дома Астана",
  "budget_usd": 5,
  "keyword": "каркасные дома Астана",
  "final_url": "https://hotwellkz.kz/astana-karkasnye-doma.html",
  "path1": "Астана", "path2": "Каркасные",
  "geo": {"city": "Астана", "lat": 51.1605, "lon": 71.4704, "radius_km": 50},
  "rsa_pools": {"pinned": ["...×3-5"], "free": ["...×≥12"], "descriptions": ["...×≥4"]},
  "n_ads": 20,
  "assets": {"sitelinks": [{"text","desc1","desc2","url"}], "callouts": ["..."],
             "snippets": [{"header","values":[...]}]}
}
"""
import os, sys, json

# ---------- ДЕФОЛТЫ (HotWell.kz / рынок KZ) ----------
D = {
    "customer_id": "8802382037",
    "country_code": "KZ", "kz_geo_id": "2398",
    "language_id": 1031,                       # русский
    "schedule": {"start": 8, "end": 22},
    "negatives_campaign": ["работа", "вакансии", "вакансия", "зарплата", "резюме", "курсы",
                           "обучение", "своими руками", "как построить", "как сделать",
                           "чертежи", "бесплатно", "форум", "модульные", "контейнер"],
    "shared_lists": ["Универсальные минус-слова RU+KZ v1"],
    "warm_audience": {"name": "Warm pixel · all visitors · hotwellkz.kz · 540d", "bid_pct": 50},
    "business_identity": {"name": "HotWell.kz", "logo_path": "site/assets/logo-1200.png"},
}


def g(spec, key):
    return spec.get(key, D.get(key))


# ---------- ВАЛИДАЦИЯ ДЛИН ----------
def validate(spec):
    errs = []
    for k in ("campaign_name", "budget_usd", "keyword", "final_url"):
        if not spec.get(k):
            errs.append("нет поля: %s" % k)
    for p in (spec.get("path1", ""), spec.get("path2", "")):
        if len(p) > 15:
            errs.append("path >15: %r" % p)
    pools = spec.get("rsa_pools", {})
    pin, free, desc = pools.get("pinned", []), pools.get("free", []), pools.get("descriptions", [])
    if len(pin) < 3: errs.append("pinned заголовков <3")
    if len(free) < 12: errs.append("free заголовков <12")
    if len(desc) < 4: errs.append("descriptions <4")
    for h in pin + free:
        if len(h) > 30: errs.append("заголовок >30 (%d): %r" % (len(h), h))
    for d in desc:
        if len(d) > 90: errs.append("описание >90 (%d): %r" % (len(d), d))
    a = spec.get("assets", {})
    for sl in a.get("sitelinks", []):
        if len(sl.get("text", "")) > 25: errs.append("sitelink >25: %r" % sl.get("text"))
        if len(sl.get("desc1", "")) > 35 or len(sl.get("desc2", "")) > 35:
            errs.append("sitelink desc >35: %r" % sl.get("text"))
    for c in a.get("callouts", []):
        if len(c) > 25: errs.append("callout >25: %r" % c)
    for sn in a.get("snippets", []):
        if len(sn.get("values", [])) < 3: errs.append("snippet '%s' <3 значений" % sn.get("header"))
        for v in sn.get("values", []):
            if len(v) > 25: errs.append("snippet значение >25: %r" % v)
    geo = spec.get("geo", {})
    if not (geo.get("lat") and geo.get("lon")) and not geo.get("city"):
        errs.append("geo: нужен city или lat+lon")
    return errs


def report(spec):
    errs = validate(spec)
    print("=== ВАЛИДАЦИЯ spec ===")
    print("Кампания:", spec.get("campaign_name"), "| бюджет $%s/день" % spec.get("budget_usd"),
          "| ключ:", repr(spec.get("keyword")))
    p = spec.get("rsa_pools", {})
    print("Пулы: pinned %d, free %d, descriptions %d → RSA: %d" %
          (len(p.get("pinned", [])), len(p.get("free", [])), len(p.get("descriptions", [])),
           spec.get("n_ads", 20)))
    a = spec.get("assets", {})
    print("Ассеты: sitelinks %d, callouts %d, snippets %d" %
          (len(a.get("sitelinks", [])), len(a.get("callouts", [])), len(a.get("snippets", []))))
    for e in errs: print("  ✗", e)
    print("ИТОГ:", "ОК — можно собирать" if not errs else "ОШИБКИ (%d)" % len(errs))
    return errs


def rot(lst, n):
    n %= len(lst); return lst[n:] + lst[:n]


# ---------- СБОРКА ----------
def build(spec):
    if report(spec):
        sys.exit("Сборка отменена: исправьте ошибки spec.")
    from google.ads.googleads.client import GoogleAdsClient
    from google.ads.googleads.errors import GoogleAdsException
    import time

    CID = (spec.get("customer_id") or D["customer_id"]).replace("-", "")
    cfg = dict(developer_token=os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
               client_id=os.environ["GOOGLE_ADS_CLIENT_ID"],
               client_secret=os.environ["GOOGLE_ADS_CLIENT_SECRET"],
               refresh_token=os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
               login_customer_id=CID, use_proto_plus=True)
    client = GoogleAdsClient.load_from_dict(cfg)
    E = client.enums
    ga = client.get_service("GoogleAdsService")
    geo = spec["geo"]; sch = g(spec, "schedule")
    KEYWORD = spec["keyword"]; FINAL_URL = spec["final_url"]
    PATH1, PATH2 = spec.get("path1", ""), spec.get("path2", "")
    pools = spec["rsa_pools"]; N_ADS = spec.get("n_ads", 20)

    try:
        # 1) бюджет
        bsvc = client.get_service("CampaignBudgetService")
        bop = client.get_type("CampaignBudgetOperation"); b = bop.create
        b.name = "%s — budget %d" % (spec["campaign_name"], int(time.time()))
        b.amount_micros = int(spec["budget_usd"]) * 1_000_000
        b.delivery_method = E.BudgetDeliveryMethodEnum.STANDARD
        b.explicitly_shared = False
        budget_rn = bsvc.mutate_campaign_budgets(customer_id=CID, operations=[bop]).results[0].resource_name
        print(" ✓ Бюджет $%s:" % spec["budget_usd"], budget_rn)

        # 2) кампания
        csvc = client.get_service("CampaignService")
        cop = client.get_type("CampaignOperation"); c = cop.create
        c.name = "%s | %s" % (spec["campaign_name"], time.strftime("%Y%m%d_%H%M"))
        c.status = E.CampaignStatusEnum.PAUSED
        c.advertising_channel_type = E.AdvertisingChannelTypeEnum.SEARCH
        c.campaign_budget = budget_rn
        c.maximize_conversions.target_cpa_micros = 0
        c.contains_eu_political_advertising = E.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
        ns = c.network_settings
        ns.target_google_search = True; ns.target_search_network = False
        ns.target_content_network = False; ns.target_partner_search_network = False
        c.geo_target_type_setting.positive_geo_target_type = E.PositiveGeoTargetTypeEnum.PRESENCE
        c.geo_target_type_setting.negative_geo_target_type = E.NegativeGeoTargetTypeEnum.PRESENCE
        camp_rn = csvc.mutate_campaigns(customer_id=CID, operations=[cop]).results[0].resource_name
        camp_id = camp_rn.split("/")[-1]
        print(" ✓ Кампания:", camp_rn)

        ccsvc = client.get_service("CampaignCriterionService")
        ops = []
        # гео: проксимити (если есть координаты) либо позиционная локация по geo_target_constant
        op = client.get_type("CampaignCriterionOperation"); cr = op.create; cr.campaign = camp_rn
        if geo.get("lat") and geo.get("lon"):
            cr.proximity.radius = geo.get("radius_km", 50)
            cr.proximity.radius_units = E.ProximityRadiusUnitsEnum.KILOMETERS
            cr.proximity.geo_point.latitude_in_micro_degrees = int(geo["lat"] * 1_000_000)
            cr.proximity.geo_point.longitude_in_micro_degrees = int(geo["lon"] * 1_000_000)
            geo_desc = "проксимити %s %dкм" % (geo.get("city", ""), geo.get("radius_km", 50))
        else:
            gid = None
            q = ("SELECT geo_target_constant.id, geo_target_constant.target_type FROM geo_target_constant "
                 "WHERE geo_target_constant.name = '%s' AND geo_target_constant.country_code = '%s' "
                 "AND geo_target_constant.status = 'ENABLED'" % (geo["city"].replace("'", "\\'"), g(spec, "country_code")))
            for r in ga.search(customer_id=CID, query=q):
                gid = str(r.geo_target_constant.id)
                if r.geo_target_constant.target_type == "City": break
            if not gid: sys.exit("Не нашёл гео для города %r" % geo.get("city"))
            cr.location.geo_target_constant = "geoTargetConstants/%s" % gid
            geo_desc = "локация %s (geo %s)" % (geo.get("city"), gid)
        ops.append(op)
        # язык
        op = client.get_type("CampaignCriterionOperation")
        op.create.campaign = camp_rn
        op.create.language.language_constant = "languageConstants/%d" % g(spec, "language_id")
        ops.append(op)
        # расписание
        for day in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]:
            op = client.get_type("CampaignCriterionOperation"); s = op.create; s.campaign = camp_rn
            s.ad_schedule.day_of_week = E.DayOfWeekEnum[day]
            s.ad_schedule.start_hour = sch["start"]; s.ad_schedule.start_minute = E.MinuteOfHourEnum.ZERO
            s.ad_schedule.end_hour = sch["end"]; s.ad_schedule.end_minute = E.MinuteOfHourEnum.ZERO
            ops.append(op)
        # минус-слова кампании
        negs = g(spec, "negatives_campaign")
        for kw in negs:
            op = client.get_type("CampaignCriterionOperation")
            op.create.campaign = camp_rn; op.create.negative = True
            op.create.keyword.text = kw; op.create.keyword.match_type = E.KeywordMatchTypeEnum.BROAD
            ops.append(op)
        ccsvc.mutate_campaign_criteria(customer_id=CID, operations=ops)
        print(" ✓ Гео (%s) + язык + расписание + %d минус-слов" % (geo_desc, len(negs)))

        # 3) исключение стран (кроме целевой). ~218 операций — тяжело для дневной квоты.
        # Можно отключить: "exclude_other_countries": false в spec. Гео уже стоит по
        # присутствию (PRESENCE) в целевом городе, так что исключение стран — доп. защита.
        if g(spec, "exclude_other_countries") is not False:
            kz = g(spec, "kz_geo_id")
            countries = []
            for r in ga.search(customer_id=CID, query="SELECT geo_target_constant.id FROM geo_target_constant WHERE geo_target_constant.target_type = 'Country' AND geo_target_constant.status = 'ENABLED'"):
                gid = str(r.geo_target_constant.id)
                if gid != kz: countries.append(gid)
            neg_ops = []
            for gid in countries:
                op = client.get_type("CampaignCriterionOperation")
                op.create.campaign = camp_rn; op.create.negative = True
                op.create.location.geo_target_constant = "geoTargetConstants/%s" % gid
                neg_ops.append(op)
            req = client.get_type("MutateCampaignCriteriaRequest")
            req.customer_id = CID; req.operations = neg_ops; req.partial_failure = True
            res = ccsvc.mutate_campaign_criteria(request=req)
            print(" ✓ Исключено стран (кроме %s):" % g(spec, "country_code"), sum(1 for x in res.results if x.resource_name))
        else:
            print(" • Исключение стран пропущено (exclude_other_countries=false); гео по присутствию в городе")

        # 4) прикрепить общие списки минус-слов
        want = g(spec, "shared_lists")
        if want:
            sets = {}
            for r in ga.search(customer_id=CID, query="SELECT shared_set.id, shared_set.name FROM shared_set WHERE shared_set.type='NEGATIVE_KEYWORDS' AND shared_set.status='ENABLED'"):
                sets[r.shared_set.name] = r.shared_set.resource_name
            cssvc = client.get_service("CampaignSharedSetService"); css_ops = []
            for name in want:
                if name in sets:
                    o = client.get_type("CampaignSharedSetOperation")
                    o.create.campaign = camp_rn; o.create.shared_set = sets[name]; css_ops.append(o)
            if css_ops:
                cssvc.mutate_campaign_shared_sets(customer_id=CID, operations=css_ops)
                print(" ✓ Прикреплено общих списков минус-слов:", len(css_ops))

        # 5) ad group + ключ
        agsvc = client.get_service("AdGroupService")
        agop = client.get_type("AdGroupOperation"); ag = agop.create
        ag.name = KEYWORD; ag.campaign = camp_rn
        ag.status = E.AdGroupStatusEnum.PAUSED; ag.type_ = E.AdGroupTypeEnum.SEARCH_STANDARD
        ag_rn = agsvc.mutate_ad_groups(customer_id=CID, operations=[agop]).results[0].resource_name
        print(" ✓ Ad group:", ag_rn)
        agcsvc = client.get_service("AdGroupCriterionService")
        kop = client.get_type("AdGroupCriterionOperation"); k = kop.create
        k.ad_group = ag_rn; k.status = E.AdGroupCriterionStatusEnum.ENABLED
        k.keyword.text = KEYWORD; k.keyword.match_type = E.KeywordMatchTypeEnum.PHRASE
        agcsvc.mutate_ad_group_criteria(customer_id=CID, operations=[kop])
        print(' ✓ Ключ: "%s" (phrase)' % KEYWORD)

        # 6) N RSA (ротация пулов), PAUSED, partial_failure
        adsvc = client.get_service("AdGroupAdService")
        PIN, FREE, DESCS = pools["pinned"], pools["free"], pools["descriptions"]
        ad_ops = []
        for i in range(N_ADS):
            op = client.get_type("AdGroupAdOperation"); aga = op.create
            aga.ad_group = ag_rn; aga.status = E.AdGroupAdStatusEnum.PAUSED
            aga.ad.final_urls.append(FINAL_URL)
            rsa = aga.ad.responsive_search_ad
            pin3 = rot(PIN, i)[:3]
            for h in pin3:
                a = client.get_type("AdTextAsset"); a.text = h
                a.pinned_field = E.ServedAssetFieldTypeEnum.HEADLINE_1; rsa.headlines.append(a)
            for h in [x for x in rot(FREE, i) if x not in pin3][:12]:   # дедуп: free не дублируют pinned
                a = client.get_type("AdTextAsset"); a.text = h; rsa.headlines.append(a)
            for d in rot(DESCS, i)[:4]:
                a = client.get_type("AdTextAsset"); a.text = d; rsa.descriptions.append(a)
            if PATH1: rsa.path1 = PATH1
            if PATH2: rsa.path2 = PATH2
            ad_ops.append(op)
        req = client.get_type("MutateAdGroupAdsRequest")
        req.customer_id = CID; req.operations = ad_ops; req.partial_failure = True
        ares = adsvc.mutate_ad_group_ads(request=req)
        print(" ✓ Создано RSA: %d из %d (PAUSED)" % (sum(1 for r in ares.results if r.resource_name), N_ADS))

        # 7) ассеты кампании
        a = spec.get("assets", {})
        if a:
            asvc = client.get_service("AssetService"); F = E.AssetFieldTypeEnum
            aops, plan = [], []
            for sl in a.get("sitelinks", []):
                o = client.get_type("AssetOperation"); x = o.create
                x.sitelink_asset.link_text = sl["text"]
                if sl.get("desc1"): x.sitelink_asset.description1 = sl["desc1"]
                if sl.get("desc2"): x.sitelink_asset.description2 = sl["desc2"]
                x.final_urls.append(sl["url"]); aops.append(o); plan.append(F.SITELINK)
            for c in a.get("callouts", []):
                o = client.get_type("AssetOperation"); o.create.callout_asset.callout_text = c
                aops.append(o); plan.append(F.CALLOUT)
            for sn in a.get("snippets", []):
                o = client.get_type("AssetOperation")
                o.create.structured_snippet_asset.header = sn["header"]
                o.create.structured_snippet_asset.values.extend(sn["values"])
                aops.append(o); plan.append(F.STRUCTURED_SNIPPET)
            if aops:
                ares2 = asvc.mutate_assets(customer_id=CID, operations=aops)
                casvc = client.get_service("CampaignAssetService"); ca_ops = []
                for ftype, rn in zip(plan, [r.resource_name for r in ares2.results]):
                    o = client.get_type("CampaignAssetOperation")
                    o.create.campaign = camp_rn; o.create.asset = rn; o.create.field_type = ftype
                    ca_ops.append(o)
                casvc.mutate_campaign_assets(customer_id=CID, operations=ca_ops)
                print(" ✓ Ассеты: %d sitelinks + %d callouts + %d snippets" %
                      (len(a.get("sitelinks", [])), len(a.get("callouts", [])), len(a.get("snippets", []))))

        # 7.5) бизнес-имя + логотип (по умолчанию HotWell.kz; нужна проверка рекламодателя)
        bi = g(spec, "business_identity")
        if bi and bi.get("name"):
            try:
                asvc2 = client.get_service("AssetService"); F = E.AssetFieldTypeEnum
                top = client.get_type("AssetOperation")
                top.create.name = "Business name " + bi["name"]
                top.create.text_asset.text = bi["name"]
                name_rn = asvc2.mutate_assets(customer_id=CID, operations=[top]).results[0].resource_name
                logo_rn = None
                lp = bi.get("logo_path")
                if lp:
                    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
                    labs = lp if os.path.isabs(lp) else os.path.join(repo, lp)
                    if os.path.exists(labs):
                        with open(labs, "rb") as f:
                            data = f.read()
                        lop = client.get_type("AssetOperation")
                        lop.create.name = "Logo " + bi["name"]
                        lop.create.type_ = E.AssetTypeEnum.IMAGE
                        lop.create.image_asset.data = data
                        lop.create.image_asset.mime_type = E.MimeTypeEnum.IMAGE_PNG
                        logo_rn = asvc2.mutate_assets(customer_id=CID, operations=[lop]).results[0].resource_name
                casvc2 = client.get_service("CampaignAssetService"); link_ops = []
                o = client.get_type("CampaignAssetOperation")
                o.create.campaign = camp_rn; o.create.asset = name_rn; o.create.field_type = F.BUSINESS_NAME
                link_ops.append(o)
                if logo_rn:
                    o2 = client.get_type("CampaignAssetOperation")
                    o2.create.campaign = camp_rn; o2.create.asset = logo_rn; o2.create.field_type = F.BUSINESS_LOGO
                    link_ops.append(o2)
                casvc2.mutate_campaign_assets(customer_id=CID, operations=link_ops)
                print(" ✓ Бизнес-имя «%s»%s добавлены" % (bi["name"], " + логотип" if logo_rn else ""))
            except GoogleAdsException as ex:
                print(" ! Бизнес-имя/логотип не добавлены (нужна проверка рекламодателя?):",
                      "; ".join(e.message for e in ex.failure.errors))

        # 8) warm-pixel аудитория + bid
        wa = g(spec, "warm_audience")
        if wa and wa.get("name"):
            list_rn = None
            for r in ga.search(customer_id=CID, query="SELECT user_list.resource_name, user_list.name FROM user_list WHERE user_list.name = '%s'" % wa["name"].replace("'", "\\'")):
                list_rn = r.user_list.resource_name
            if list_rn:
                # ensure observation
                restr = []
                for r in ga.search(customer_id=CID, query="SELECT ad_group.targeting_setting.target_restrictions FROM ad_group WHERE ad_group.resource_name = '%s'" % ag_rn):
                    restr = list(r.ad_group.targeting_setting.target_restrictions)
                if not any(tr.targeting_dimension == E.TargetingDimensionEnum.AUDIENCE and tr.bid_only for tr in restr):
                    uop = client.get_type("AdGroupOperation"); ug = uop.update; ug.resource_name = ag_rn
                    ts = ug.targeting_setting
                    for tr in [t for t in restr if t.targeting_dimension != E.TargetingDimensionEnum.AUDIENCE]:
                        ts.target_restrictions.append(tr)
                    ntr = client.get_type("TargetRestriction")
                    ntr.targeting_dimension = E.TargetingDimensionEnum.AUDIENCE; ntr.bid_only = True
                    ts.target_restrictions.append(ntr)
                    uop.update_mask.paths.append("targeting_setting.target_restrictions")
                    agsvc.mutate_ad_groups(customer_id=CID, operations=[uop])
                op = client.get_type("AdGroupCriterionOperation"); cc = op.create
                cc.ad_group = ag_rn; cc.user_list.user_list = list_rn
                cc.bid_modifier = 1.0 + wa.get("bid_pct", 50) / 100.0
                cc.status = E.AdGroupCriterionStatusEnum.ENABLED
                agcsvc.mutate_ad_group_criteria(customer_id=CID, operations=[op])
                print(" ✓ Warm-pixel аудитория прикреплена (+%d%%)" % wa.get("bid_pct", 50))
            else:
                print(" ! Аудитория '%s' не найдена — пропущена" % wa["name"])

        print("\n ГОТОВО · PAUSED · Campaign ID", camp_id)
        print(" Проверка: https://ads.google.com/aw/campaigns?campaignId=%s" % camp_id)
    except GoogleAdsException as ex:
        print("GoogleAdsException:")
        for e in ex.failure.errors: print("  -", e.message)
        sys.exit(1)


def finish(spec):
    """Дозаливка только хвоста сборки (ассеты + бизнес-имя/логотип + warm-pixel
    аудитория) в УЖЕ существующую кампанию/группу. Нужно при обрыве build на
    дневной квоте API (RESOURCE_EXHAUSTED). Берёт campaign_id и ad_group_id из spec
    (или env CAMPAIGN_ID / AD_GROUP_ID). Идемпотентности нет — запускать один раз."""
    from google.ads.googleads.client import GoogleAdsClient
    from google.ads.googleads.errors import GoogleAdsException

    CID = (spec.get("customer_id") or D["customer_id"]).replace("-", "")
    camp_id = str(spec.get("campaign_id") or os.environ.get("CAMPAIGN_ID", "")).strip()
    ag_id = str(spec.get("ad_group_id") or os.environ.get("AD_GROUP_ID", "")).strip()
    if not camp_id or not ag_id:
        sys.exit("finish: нужны campaign_id и ad_group_id (в spec или env CAMPAIGN_ID/AD_GROUP_ID)")
    cfg = dict(developer_token=os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
               client_id=os.environ["GOOGLE_ADS_CLIENT_ID"],
               client_secret=os.environ["GOOGLE_ADS_CLIENT_SECRET"],
               refresh_token=os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
               login_customer_id=CID, use_proto_plus=True)
    client = GoogleAdsClient.load_from_dict(cfg)
    E = client.enums
    ga = client.get_service("GoogleAdsService")
    agsvc = client.get_service("AdGroupService")
    agcsvc = client.get_service("AdGroupCriterionService")
    camp_rn = "customers/%s/campaigns/%s" % (CID, camp_id)
    ag_rn = "customers/%s/adGroups/%s" % (CID, ag_id)
    print("=== FINISH · кампания %s · группа %s ===" % (camp_id, ag_id))
    try:
        # 7) ассеты кампании
        a = spec.get("assets", {})
        if a:
            asvc = client.get_service("AssetService"); F = E.AssetFieldTypeEnum
            aops, plan = [], []
            for sl in a.get("sitelinks", []):
                o = client.get_type("AssetOperation"); x = o.create
                x.sitelink_asset.link_text = sl["text"]
                if sl.get("desc1"): x.sitelink_asset.description1 = sl["desc1"]
                if sl.get("desc2"): x.sitelink_asset.description2 = sl["desc2"]
                x.final_urls.append(sl["url"]); aops.append(o); plan.append(F.SITELINK)
            for c in a.get("callouts", []):
                o = client.get_type("AssetOperation"); o.create.callout_asset.callout_text = c
                aops.append(o); plan.append(F.CALLOUT)
            for sn in a.get("snippets", []):
                o = client.get_type("AssetOperation")
                o.create.structured_snippet_asset.header = sn["header"]
                o.create.structured_snippet_asset.values.extend(sn["values"])
                aops.append(o); plan.append(F.STRUCTURED_SNIPPET)
            if aops:
                ares2 = asvc.mutate_assets(customer_id=CID, operations=aops)
                casvc = client.get_service("CampaignAssetService"); ca_ops = []
                for ftype, rn in zip(plan, [r.resource_name for r in ares2.results]):
                    o = client.get_type("CampaignAssetOperation")
                    o.create.campaign = camp_rn; o.create.asset = rn; o.create.field_type = ftype
                    ca_ops.append(o)
                casvc.mutate_campaign_assets(customer_id=CID, operations=ca_ops)
                print(" ✓ Ассеты: %d sitelinks + %d callouts + %d snippets" %
                      (len(a.get("sitelinks", [])), len(a.get("callouts", [])), len(a.get("snippets", []))))

        # 7.5) бизнес-имя + логотип
        bi = g(spec, "business_identity")
        if bi and bi.get("name"):
            try:
                asvc2 = client.get_service("AssetService"); F = E.AssetFieldTypeEnum
                top = client.get_type("AssetOperation")
                top.create.name = "Business name " + bi["name"]
                top.create.text_asset.text = bi["name"]
                name_rn = asvc2.mutate_assets(customer_id=CID, operations=[top]).results[0].resource_name
                logo_rn = None
                lp = bi.get("logo_path")
                if lp:
                    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
                    labs = lp if os.path.isabs(lp) else os.path.join(repo, lp)
                    if os.path.exists(labs):
                        with open(labs, "rb") as f:
                            data = f.read()
                        lop = client.get_type("AssetOperation")
                        lop.create.name = "Logo " + bi["name"]
                        lop.create.type_ = E.AssetTypeEnum.IMAGE
                        lop.create.image_asset.data = data
                        lop.create.image_asset.mime_type = E.MimeTypeEnum.IMAGE_PNG
                        logo_rn = asvc2.mutate_assets(customer_id=CID, operations=[lop]).results[0].resource_name
                casvc2 = client.get_service("CampaignAssetService"); link_ops = []
                o = client.get_type("CampaignAssetOperation")
                o.create.campaign = camp_rn; o.create.asset = name_rn; o.create.field_type = F.BUSINESS_NAME
                link_ops.append(o)
                if logo_rn:
                    o2 = client.get_type("CampaignAssetOperation")
                    o2.create.campaign = camp_rn; o2.create.asset = logo_rn; o2.create.field_type = F.BUSINESS_LOGO
                    link_ops.append(o2)
                casvc2.mutate_campaign_assets(customer_id=CID, operations=link_ops)
                print(" ✓ Бизнес-имя «%s»%s добавлены" % (bi["name"], " + логотип" if logo_rn else ""))
            except GoogleAdsException as ex:
                print(" ! Бизнес-имя/логотип не добавлены (нужна проверка рекламодателя?):",
                      "; ".join(e.message for e in ex.failure.errors))

        # 8) warm-pixel аудитория + bid
        wa = g(spec, "warm_audience")
        if wa and wa.get("name"):
            list_rn = None
            for r in ga.search(customer_id=CID, query="SELECT user_list.resource_name, user_list.name FROM user_list WHERE user_list.name = '%s'" % wa["name"].replace("'", "\\'")):
                list_rn = r.user_list.resource_name
            if list_rn:
                restr = []
                for r in ga.search(customer_id=CID, query="SELECT ad_group.targeting_setting.target_restrictions FROM ad_group WHERE ad_group.resource_name = '%s'" % ag_rn):
                    restr = list(r.ad_group.targeting_setting.target_restrictions)
                if not any(tr.targeting_dimension == E.TargetingDimensionEnum.AUDIENCE and tr.bid_only for tr in restr):
                    uop = client.get_type("AdGroupOperation"); ug = uop.update; ug.resource_name = ag_rn
                    ts = ug.targeting_setting
                    for tr in [t for t in restr if t.targeting_dimension != E.TargetingDimensionEnum.AUDIENCE]:
                        ts.target_restrictions.append(tr)
                    ntr = client.get_type("TargetRestriction")
                    ntr.targeting_dimension = E.TargetingDimensionEnum.AUDIENCE; ntr.bid_only = True
                    ts.target_restrictions.append(ntr)
                    uop.update_mask.paths.append("targeting_setting.target_restrictions")
                    agsvc.mutate_ad_groups(customer_id=CID, operations=[uop])
                op = client.get_type("AdGroupCriterionOperation"); cc = op.create
                cc.ad_group = ag_rn; cc.user_list.user_list = list_rn
                cc.bid_modifier = 1.0 + wa.get("bid_pct", 50) / 100.0
                cc.status = E.AdGroupCriterionStatusEnum.ENABLED
                agcsvc.mutate_ad_group_criteria(customer_id=CID, operations=[op])
                print(" ✓ Warm-pixel аудитория прикреплена (+%d%%)" % wa.get("bid_pct", 50))
            else:
                print(" ! Аудитория '%s' не найдена — пропущена" % wa["name"])

        print("\n ХВОСТ ДОБАВЛЕН · PAUSED · Campaign ID", camp_id)
        print(" Проверка: https://ads.google.com/aw/campaigns?campaignId=%s" % camp_id)
    except GoogleAdsException as ex:
        print("GoogleAdsException:")
        for e in ex.failure.errors: print("  -", e.message)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit("Использование: launch_campaign.py [validate|build|finish] spec.json")
    spec = json.load(open(sys.argv[2], encoding="utf-8"))
    if sys.argv[1] == "validate":
        sys.exit(1 if report(spec) else 0)
    elif sys.argv[1] == "build":
        build(spec)
    elif sys.argv[1] == "finish":
        finish(spec)
    else:
        sys.exit("Режим: validate|build|finish")
