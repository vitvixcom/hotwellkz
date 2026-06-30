#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Замена «2018» → «2012» в живых объявлениях (RSA нельзя редактировать — пересоздаём)
и в sitelink-ассетах указанных кампаний. Всё пересозданное — PAUSED.
"""
import os, sys
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CID = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
CAMPAIGNS = os.environ.get("CAMPAIGNS", "23991449173,23992790071,23992921168").split(",")
OLD, NEW = "2018", "2012"

cfg = dict(developer_token=os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
           client_id=os.environ["GOOGLE_ADS_CLIENT_ID"],
           client_secret=os.environ["GOOGLE_ADS_CLIENT_SECRET"],
           refresh_token=os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
           login_customer_id=CID, use_proto_plus=True)
client = GoogleAdsClient.load_from_dict(cfg)
E = client.enums
ga = client.get_service("GoogleAdsService")


def fix_rsas(camp_id):
    q = ("SELECT ad_group_ad.resource_name, ad_group_ad.ad_group, ad_group_ad.ad.final_urls, "
         "ad_group_ad.ad.responsive_search_ad.headlines, "
         "ad_group_ad.ad.responsive_search_ad.descriptions, "
         "ad_group_ad.ad.responsive_search_ad.path1, ad_group_ad.ad.responsive_search_ad.path2 "
         "FROM ad_group_ad WHERE campaign.id=%s AND ad_group_ad.ad.type='RESPONSIVE_SEARCH_AD' "
         "AND ad_group_ad.status != 'REMOVED'" % camp_id)
    svc = client.get_service("AdGroupAdService")
    create_ops, old_rns = [], []
    for r in ga.search(customer_id=CID, query=q):
        ad = r.ad_group_ad.ad
        rsa = ad.responsive_search_ad
        has = any(OLD in h.text for h in rsa.headlines) or any(OLD in d.text for d in rsa.descriptions)
        if not has:
            continue
        op = client.get_type("AdGroupAdOperation"); aga = op.create
        aga.ad_group = r.ad_group_ad.ad_group
        aga.status = E.AdGroupAdStatusEnum.PAUSED
        for u in ad.final_urls:
            aga.ad.final_urls.append(u)
        nr = aga.ad.responsive_search_ad
        for h in rsa.headlines:
            a = client.get_type("AdTextAsset"); a.text = h.text.replace(OLD, NEW)
            if h.pinned_field and h.pinned_field.name not in ("UNSPECIFIED", "UNKNOWN"):
                a.pinned_field = h.pinned_field
            nr.headlines.append(a)
        for d in rsa.descriptions:
            a = client.get_type("AdTextAsset"); a.text = d.text.replace(OLD, NEW)
            nr.descriptions.append(a)
        if rsa.path1: nr.path1 = rsa.path1
        if rsa.path2: nr.path2 = rsa.path2
        create_ops.append(op); old_rns.append(r.ad_group_ad.resource_name)

    if not create_ops:
        print("   RSA с %s: нет" % OLD); return
    req = client.get_type("MutateAdGroupAdsRequest")
    req.customer_id = CID; req.operations = create_ops; req.partial_failure = True
    res = svc.mutate_ad_group_ads(request=req)
    ok_old = [old_rns[i] for i, rr in enumerate(res.results) if rr.resource_name]
    print("   RSA пересоздано: %d из %d" % (len(ok_old), len(create_ops)))
    if ok_old:
        rm = []
        for rn in ok_old:
            o = client.get_type("AdGroupAdOperation"); o.remove = rn; rm.append(o)
        svc.mutate_ad_group_ads(customer_id=CID, operations=rm)
        print("   старых RSA удалено: %d" % len(rm))


def fix_sitelinks(camp_id):
    q = ("SELECT campaign.id, campaign_asset.resource_name, campaign.resource_name, "
         "asset.sitelink_asset.link_text, asset.sitelink_asset.description1, "
         "asset.sitelink_asset.description2, asset.final_urls "
         "FROM campaign_asset WHERE campaign.id=%s AND campaign_asset.field_type='SITELINK' "
         "AND campaign_asset.status='ENABLED'" % camp_id)
    asvc = client.get_service("AssetService")
    casvc = client.get_service("CampaignAssetService")
    fixed = 0
    for r in ga.search(customer_id=CID, query=q):
        sl = r.asset.sitelink_asset
        if not (OLD in sl.link_text or OLD in sl.description1 or OLD in sl.description2):
            continue
        op = client.get_type("AssetOperation"); x = op.create
        x.sitelink_asset.link_text = sl.link_text.replace(OLD, NEW)
        if sl.description1: x.sitelink_asset.description1 = sl.description1.replace(OLD, NEW)
        if sl.description2: x.sitelink_asset.description2 = sl.description2.replace(OLD, NEW)
        for u in r.asset.final_urls:
            x.final_urls.append(u)
        new_rn = asvc.mutate_assets(customer_id=CID, operations=[op]).results[0].resource_name
        lop = client.get_type("CampaignAssetOperation")
        lop.create.campaign = r.campaign.resource_name
        lop.create.asset = new_rn
        lop.create.field_type = E.AssetFieldTypeEnum.SITELINK
        casvc.mutate_campaign_assets(customer_id=CID, operations=[lop])
        rmo = client.get_type("CampaignAssetOperation"); rmo.remove = r.campaign_asset.resource_name
        casvc.mutate_campaign_assets(customer_id=CID, operations=[rmo])
        fixed += 1
    print("   sitelink с %s исправлено: %d" % (OLD, fixed))


def main():
    for cid in CAMPAIGNS:
        cid = cid.strip()
        print("Кампания", cid)
        fix_rsas(cid)
        fix_sitelinks(cid)
    print("\nГОТОВО.")


if __name__ == "__main__":
    try:
        main()
    except GoogleAdsException as ex:
        print("GoogleAdsException:")
        for e in ex.failure.errors:
            print("  -", e.message)
        sys.exit(1)
