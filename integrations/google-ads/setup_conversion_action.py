#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Создаёт (или переиспользует) conversion action «Заявка с сайта · форма» в Google Ads
по SOP setup-conversion-tracking-and-audience.md (Step 1) и печатает tag IDs:
глобальный тег AW-XXXXXXXXXX и conversion label AW-XXXXXXXXXX/XXXX.
Идемпотентно: если действие с таким именем уже есть — берём его.
"""
import os, re, sys, json
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CID = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
NAME = os.environ.get("CONV_NAME", "Заявка с сайта · форма")
VALUE = float(os.environ.get("CONV_VALUE", "750"))
CURRENCY = os.environ.get("CONV_CURRENCY", "USD")
OUT = os.environ.get("CONV_OUT", "")  # путь для записи AW-id/label (не секрет)

cfg = dict(developer_token=os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
           client_id=os.environ["GOOGLE_ADS_CLIENT_ID"],
           client_secret=os.environ["GOOGLE_ADS_CLIENT_SECRET"],
           refresh_token=os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
           login_customer_id=CID, use_proto_plus=True)
client = GoogleAdsClient.load_from_dict(cfg)
ga = client.get_service("GoogleAdsService")
E = client.enums


def find_existing():
    q = ("SELECT conversion_action.resource_name, conversion_action.id, "
         "conversion_action.name, conversion_action.status FROM conversion_action "
         "WHERE conversion_action.name = '%s'" % NAME.replace("'", "\\'"))
    for r in ga.search(customer_id=CID, query=q):
        return r.conversion_action.resource_name
    return None


def create():
    svc = client.get_service("ConversionActionService")
    op = client.get_type("ConversionActionOperation")
    c = op.create
    c.name = NAME
    c.category = E.ConversionActionCategoryEnum.SUBMIT_LEAD_FORM
    c.type_ = E.ConversionActionTypeEnum.WEBPAGE
    c.status = E.ConversionActionStatusEnum.ENABLED
    c.value_settings.default_value = VALUE
    c.value_settings.default_currency_code = CURRENCY
    c.value_settings.always_use_default_value = False
    c.counting_type = E.ConversionActionCountingTypeEnum.ONE_PER_CLICK
    c.click_through_lookback_window_days = 90
    c.view_through_lookback_window_days = 1
    c.primary_for_goal = True
    c.attribution_model_settings.attribution_model = E.AttributionModelEnum.GOOGLE_SEARCH_ATTRIBUTION_DATA_DRIVEN
    try:
        return svc.mutate_conversion_actions(customer_id=CID, operations=[op]).results[0].resource_name
    except GoogleAdsException as ex:
        if any("attribution" in (e.message or "").lower() for e in ex.failure.errors):
            # data-driven недоступна (мало данных) → дефолтная модель
            c.ClearField("attribution_model_settings")
            return svc.mutate_conversion_actions(customer_id=CID, operations=[op]).results[0].resource_name
        raise


def fetch_snippets(rn):
    q = ("SELECT conversion_action.id, conversion_action.tag_snippets "
         "FROM conversion_action WHERE conversion_action.resource_name = '%s'" % rn)
    for r in ga.search(customer_id=CID, query=q):
        return list(r.conversion_action.tag_snippets), r.conversion_action.id
    return [], None


def main():
    rn = find_existing()
    if rn:
        print("• Уже существует, переиспользую:", rn)
    else:
        rn = create()
        print("• Создан conversion action:", rn)

    snippets, conv_id = fetch_snippets(rn)
    aw_id = label = None
    for s in snippets:
        g = s.global_site_tag or ""
        e = s.event_snippet or ""
        m = re.search(r"AW-\d+", g) or re.search(r"AW-\d+", e)
        if m and not aw_id:
            aw_id = m.group(0)
        m2 = re.search(r"send_to['\"]?\s*:\s*['\"](AW-\d+/[\w\-]+)['\"]", e)
        if m2:
            label = m2.group(1)
    print("AW_ID=%s" % aw_id)
    print("CONV_LABEL=%s" % label)
    print("CONV_RESOURCE=%s" % rn)
    if OUT and aw_id and label:
        with open(OUT, "w") as f:
            json.dump({"aw_id": aw_id, "label": label, "resource": rn}, f)
        print("written:", OUT)
    if not (aw_id and label):
        print("! Не удалось извлечь AW-id/label из tag_snippets (возможно, нужно подождать)", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except GoogleAdsException as ex:
        print("GoogleAdsException:")
        for e in ex.failure.errors:
            print("  -", e.message)
        sys.exit(1)
