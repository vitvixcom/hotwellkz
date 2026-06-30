#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Снимок данных для дашборда /dashboard:
- ROAS по кампаниям за последние 30 дней;
- рекомендации Google Ads, отсортированные по потенциально возвращаемым деньгам.
Пишет site/dashboard-data.json (статический снимок; обновляется повторным запуском).
"""
import os, json, datetime
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CID = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
OUT = os.environ.get("OUT", "site/dashboard-data.json")
AVG_VALUE = 50.0  # ценность конверсии для оценки прироста, если value не заполнен

cfg = dict(developer_token=os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
           client_id=os.environ["GOOGLE_ADS_CLIENT_ID"],
           client_secret=os.environ["GOOGLE_ADS_CLIENT_SECRET"],
           refresh_token=os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
           login_customer_id=CID, use_proto_plus=True)
client = GoogleAdsClient.load_from_dict(cfg)
ga = client.get_service("GoogleAdsService")

TYPE_RU = {
    "CAMPAIGN_BUDGET": "Поднять дневной бюджет (упираетесь в лимит)",
    "KEYWORD": "Добавить ключевые слова",
    "TEXT_AD": "Добавить объявления",
    "RESPONSIVE_SEARCH_AD": "Добавить адаптивное поисковое объявление",
    "RESPONSIVE_SEARCH_AD_ASSET": "Добавить заголовки/описания в RSA",
    "RESPONSIVE_SEARCH_AD_IMPROVE_AD_STRENGTH": "Улучшить силу объявления (Ad Strength)",
    "TARGET_CPA_OPT_IN": "Включить ставки по целевой цене за конверсию (tCPA)",
    "SET_TARGET_CPA": "Задать целевую цену за конверсию (tCPA)",
    "MAXIMIZE_CONVERSIONS_OPT_IN": "Включить «Максимум конверсий»",
    "MAXIMIZE_CONVERSION_VALUE_OPT_IN": "Включить «Максимум ценности конверсий»",
    "TARGET_ROAS_OPT_IN": "Включить ставки по целевому ROAS",
    "ENHANCED_CPC_OPT_IN": "Включить улучшенный CPC",
    "SEARCH_PARTNERS_OPT_IN": "Включить поисковых партнёров",
    "OPTIMIZE_AD_ROTATION": "Оптимизировать ротацию объявлений",
    "MOVE_UNUSED_BUDGET": "Перераспределить неиспользуемый бюджет",
    "FORECASTING_CAMPAIGN_BUDGET": "Поднять бюджет к сезонному всплеску",
    "MAXIMIZE_CLICKS_OPT_IN": "Включить «Максимум кликов»",
    "DISPLAY_EXPANSION_OPT_IN": "Включить расширение на КМС",
    "UPGRADE_SMART_SHOPPING_CAMPAIGN": "Обновить кампанию",
    "USE_BROAD_MATCH_KEYWORD": "Использовать широкое соответствие",
    "RAISE_TARGET_CPA": "Поднять tCPA (упускаете конверсии)",
    "LOWER_TARGET_CPA": "Снизить tCPA",
    "IMPROVE_GOOGLE_TAG_COVERAGE": "Доустановить Google-тег",
    "DYNAMIC_IMAGE_EXTENSION_OPT_IN": "Включить динамические изображения",
    "CALLOUT_ASSET": "Добавить уточнения (callouts)",
    "SITELINK_ASSET": "Добавить дополнительные ссылки (sitelinks)",
    "CALL_ASSET": "Добавить номер телефона",
    "KEYWORD_MATCH_TYPE": "Сменить тип соответствия ключа",
    "IMPROVE_PERFORMANCE_MAX_AD_STRENGTH": "Улучшить ассеты Performance Max",
}


def m(v):
    return (v or 0) / 1_000_000.0


def campaigns():
    q = """SELECT campaign.id, campaign.name, campaign.status,
      campaign.advertising_channel_type,
      metrics.cost_micros, metrics.conversions, metrics.conversions_value,
      metrics.clicks, metrics.impressions
      FROM campaign WHERE segments.date DURING LAST_30_DAYS
      ORDER BY metrics.cost_micros DESC"""
    rows, names = [], {}
    for r in ga.search(customer_id=CID, query=q):
        c, mt = r.campaign, r.metrics
        names[str(c.id)] = c.name
        cost = m(mt.cost_micros)
        val = mt.conversions_value or 0.0
        conv = mt.conversions or 0.0
        if mt.impressions == 0 and cost == 0:
            continue
        rows.append({
            "id": str(c.id), "name": c.name, "status": c.status.name,
            "channel": c.advertising_channel_type.name,
            "cost": round(cost, 2), "conv": round(conv, 1),
            "conv_value": round(val, 2),
            "roas": round(val / cost, 2) if cost > 0 else 0.0,
            "cpa": round(cost / conv, 2) if conv > 0 else 0.0,
            "clicks": int(mt.clicks), "impr": int(mt.impressions),
        })
    return rows, names


# вес типа = доля месячного расхода кампании, на которую этот тип реально влияет
WEIGHTS = {
    "CAMPAIGN_BUDGET": 0.30, "FORECASTING_CAMPAIGN_BUDGET": 0.30, "MOVE_UNUSED_BUDGET": 0.30,
    "MAXIMIZE_CONVERSIONS_OPT_IN": 0.25, "MAXIMIZE_CONVERSION_VALUE_OPT_IN": 0.25,
    "SET_TARGET_CPA": 0.22, "TARGET_CPA_OPT_IN": 0.22, "TARGET_ROAS_OPT_IN": 0.22, "RAISE_TARGET_CPA": 0.22,
    "LOWER_TARGET_CPA": 0.15, "KEYWORD": 0.20, "USE_BROAD_MATCH_KEYWORD": 0.18, "KEYWORD_MATCH_TYPE": 0.15,
    "RESPONSIVE_SEARCH_AD": 0.15, "RESPONSIVE_SEARCH_AD_ASSET": 0.12,
    "RESPONSIVE_SEARCH_AD_IMPROVE_AD_STRENGTH": 0.12, "IMPROVE_PERFORMANCE_MAX_AD_STRENGTH": 0.12,
    "DYNAMIC_IMAGE_EXTENSION_OPT_IN": 0.08, "CALLOUT_ASSET": 0.10, "SITELINK_ASSET": 0.10, "CALL_ASSET": 0.10,
    "SEARCH_PARTNERS_OPT_IN": 0.05, "DISPLAY_EXPANSION_OPT_IN": 0.05,
}


def tier(w):
    return "high" if w >= 0.2 else ("medium" if w >= 0.1 else "low")


def recommendations(names, costs):
    avg_cost = (sum(costs.values()) / len(costs)) if costs else 0.0
    q = """SELECT recommendation.resource_name, recommendation.type, recommendation.campaign,
      recommendation.impact
      FROM recommendation"""
    out = []
    for r in ga.search(customer_id=CID, query=q):
        rec = r.recommendation
        b, p = rec.impact.base_metrics, rec.impact.potential_metrics
        d_val = (p.conversions_value or 0) - (b.conversions_value or 0)
        d_conv = (p.conversions or 0) - (b.conversions or 0)
        d_cost_save = m(b.cost_micros) - m(p.cost_micros)
        camp_id = rec.campaign.split("/")[-1] if rec.campaign else ""
        # реальные деньги из API, если Google их вернул
        if d_val > 0:
            gain, basis, estimated = d_val, "ценность конверсий (из Google)", False
        elif d_conv > 0:
            gain, basis, estimated = d_conv * AVG_VALUE, "доп. конверсии × $%d" % AVG_VALUE, False
        elif d_cost_save > 0:
            gain, basis, estimated = d_cost_save, "экономия бюджета (из Google)", False
        else:
            # Google не вернул сумму → оценка по типу × расход кампании
            w = WEIGHTS.get(rec.type_.name, 0.10)
            base_cost = costs.get(camp_id, avg_cost)
            gain, basis, estimated = w * base_cost, "оценка: %d%% расхода кампании/мес" % int(w * 100), True
        t = tier(WEIGHTS.get(rec.type_.name, 0.10))
        out.append({
            "type": rec.type_.name,
            "type_ru": TYPE_RU.get(rec.type_.name, rec.type_.name.replace("_", " ").title()),
            "campaign": names.get(camp_id, "Аккаунт" if not camp_id else camp_id),
            "gain": round(gain, 2), "basis": basis, "estimated": estimated, "tier": t,
            "d_conv": round(d_conv, 1),
            "resource": rec.resource_name,
        })
    out.sort(key=lambda x: x["gain"], reverse=True)
    return out


def main():
    camps, names = campaigns()
    costs = {c["id"]: c["cost"] for c in camps}
    recs = recommendations(names, costs)
    data = {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "customer_id": CID,
        "currency": "USD",
        "period": "Последние 30 дней",
        "campaigns": camps,
        "recommendations": recs,
        "totals": {
            "cost": round(sum(c["cost"] for c in camps), 2),
            "conv_value": round(sum(c["conv_value"] for c in camps), 2),
            "potential_gain": round(sum(r["gain"] for r in recs), 2),
        },
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("кампаний: %d | рекомендаций: %d | потенциал: $%.0f" %
          (len(camps), len(recs), data["totals"]["potential_gain"]))
    print("written", OUT)


if __name__ == "__main__":
    try:
        main()
    except GoogleAdsException as ex:
        print("GoogleAdsException:")
        for e in ex.failure.errors:
            print("  -", e.message)
        raise
