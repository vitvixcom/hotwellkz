#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Warm-pixel аудитория (Step 5–7 SOP setup-conversion-tracking-and-audience.md):
- rule-based user list: кто был на любой странице домена за 540 дней;
- прикрепление к ad group как RLSA-observation с корректировкой ставки (+50% по умолчанию).
Идемпотентно по имени списка. Перед привязкой убеждаемся, что targeting setting
ad group = Observation (bid_only) для аудитории, иначе группа сузится только до неё.
"""
import os, sys
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CID = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
DOMAIN = os.environ.get("DOMAIN", "hotwellkz.kz")
AD_GROUP_ID = os.environ.get("AD_GROUP_ID", "206423446508")
BID_PCT = float(os.environ.get("BID_PCT", "50"))
LIST_NAME = f"Warm pixel · all visitors · {DOMAIN} · 540d"

cfg = dict(developer_token=os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
           client_id=os.environ["GOOGLE_ADS_CLIENT_ID"],
           client_secret=os.environ["GOOGLE_ADS_CLIENT_SECRET"],
           refresh_token=os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
           login_customer_id=CID, use_proto_plus=True)
client = GoogleAdsClient.load_from_dict(cfg)
ga = client.get_service("GoogleAdsService")
E = client.enums


def find_list():
    q = ("SELECT user_list.resource_name, user_list.id FROM user_list "
         "WHERE user_list.name = '%s'" % LIST_NAME.replace("'", "\\'"))
    for r in ga.search(customer_id=CID, query=q):
        return r.user_list.resource_name
    return None


def create_list():
    svc = client.get_service("UserListService")
    op = client.get_type("UserListOperation")
    ul = op.create
    ul.name = LIST_NAME
    ul.description = (f"Все, кто заходил на любую страницу {DOMAIN} за последние 540 дней. "
                      "Наполняется автоматически глобальным тегом gtag.")
    ul.membership_status = E.UserListMembershipStatusEnum.OPEN
    ul.membership_life_span = 540

    item = client.get_type("UserListRuleItemInfo")
    item.name = "url__"
    item.string_rule_item.operator = E.UserListStringRuleItemOperatorEnum.CONTAINS
    item.string_rule_item.value = DOMAIN

    group = client.get_type("UserListRuleItemGroupInfo")
    group.rule_items.append(item)

    operand = client.get_type("FlexibleRuleOperandInfo")
    operand.rule.rule_item_groups.append(group)
    operand.lookback_window_days = 540

    flex = ul.rule_based_user_list.flexible_rule_user_list
    flex.inclusive_rule_operator = E.UserListFlexibleRuleOperatorEnum.AND
    flex.inclusive_operands.append(operand)

    return svc.mutate_user_lists(customer_id=CID, operations=[op]).results[0].resource_name


def ensure_observation():
    """Убеждаемся, что для AUDIENCE стоит bid_only=True (Observation)."""
    ag_rn = "customers/%s/adGroups/%s" % (CID, AD_GROUP_ID)
    q = ("SELECT ad_group.resource_name, ad_group.targeting_setting.target_restrictions "
         "FROM ad_group WHERE ad_group.id = %s" % AD_GROUP_ID)
    restrictions = []
    for r in ga.search(customer_id=CID, query=q):
        restrictions = list(r.ad_group.targeting_setting.target_restrictions)
    has_obs = any(tr.targeting_dimension == E.TargetingDimensionEnum.AUDIENCE and tr.bid_only
                  for tr in restrictions)
    if has_obs:
        print("• Targeting setting уже Observation для аудитории")
        return
    svc = client.get_service("AdGroupService")
    op = client.get_type("AdGroupOperation")
    ag = op.update
    ag.resource_name = ag_rn
    # пересобираем список ограничений, AUDIENCE → bid_only=True
    ts = ag.targeting_setting
    kept = [tr for tr in restrictions if tr.targeting_dimension != E.TargetingDimensionEnum.AUDIENCE]
    for tr in kept:
        ts.target_restrictions.append(tr)
    new_tr = client.get_type("TargetRestriction")
    new_tr.targeting_dimension = E.TargetingDimensionEnum.AUDIENCE
    new_tr.bid_only = True
    ts.target_restrictions.append(new_tr)
    op.update_mask.paths.append("targeting_setting.target_restrictions")
    svc.mutate_ad_groups(customer_id=CID, operations=[op])
    print("• Targeting setting обновлён → Observation (bid_only) для аудитории")


def attach(list_rn):
    svc = client.get_service("AdGroupCriterionService")
    op = client.get_type("AdGroupCriterionOperation")
    c = op.create
    c.ad_group = "customers/%s/adGroups/%s" % (CID, AD_GROUP_ID)
    c.user_list.user_list = list_rn
    c.bid_modifier = 1.0 + BID_PCT / 100.0
    c.status = E.AdGroupCriterionStatusEnum.ENABLED
    try:
        rn = svc.mutate_ad_group_criteria(customer_id=CID, operations=[op]).results[0].resource_name
        print("• Аудитория прикреплена к ad group %s (+%.0f%%): %s" % (AD_GROUP_ID, BID_PCT, rn))
    except GoogleAdsException as ex:
        if any("already exists" in (e.message or "").lower() or e.error_code.ad_group_criterion_error
               for e in ex.failure.errors):
            print("• Аудитория уже была прикреплена (пропускаю):",
                  "; ".join(e.message for e in ex.failure.errors))
        else:
            raise


def main():
    list_rn = find_list()
    if list_rn:
        print("• User list уже существует:", list_rn)
    else:
        list_rn = create_list()
        print("• Создан warm-pixel user list:", list_rn)
    ensure_observation()
    attach(list_rn)
    print("\nГОТОВО. Аудитория наполнится по мере трафика (24–72ч до первых членов).")


if __name__ == "__main__":
    try:
        main()
    except GoogleAdsException as ex:
        print("GoogleAdsException:")
        for e in ex.failure.errors:
            print("  -", e.message)
        sys.exit(1)
