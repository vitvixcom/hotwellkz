#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Дозаливка RSA в существующую ad group из пулов spec.json (ротация + дедуп free/pinned).
env: AD_GROUP_ID (обязательно), COUNT (по умолч. 5), START_OFFSET (по умолч. 0).
Аргумент: spec.json (с final_url, path1/2, rsa_pools).
"""
import os, sys, json
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CID = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
AG_ID = os.environ["AD_GROUP_ID"]
COUNT = int(os.environ.get("COUNT", "5"))
START = int(os.environ.get("START_OFFSET", "0"))
spec = json.load(open(sys.argv[1], encoding="utf-8"))
FINAL_URL = spec["final_url"]; P1 = spec.get("path1", ""); P2 = spec.get("path2", "")
PIN = spec["rsa_pools"]["pinned"]; FREE = spec["rsa_pools"]["free"]; DESCS = spec["rsa_pools"]["descriptions"]

cfg = dict(developer_token=os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
           client_id=os.environ["GOOGLE_ADS_CLIENT_ID"],
           client_secret=os.environ["GOOGLE_ADS_CLIENT_SECRET"],
           refresh_token=os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
           login_customer_id=CID, use_proto_plus=True)
client = GoogleAdsClient.load_from_dict(cfg)
E = client.enums


def rot(lst, n):
    n %= len(lst); return lst[n:] + lst[:n]


def run():
    ag_rn = "customers/%s/adGroups/%s" % (CID, AG_ID)
    svc = client.get_service("AdGroupAdService")
    ops = []
    for i in range(START, START + COUNT):
        op = client.get_type("AdGroupAdOperation"); aga = op.create
        aga.ad_group = ag_rn; aga.status = E.AdGroupAdStatusEnum.PAUSED
        aga.ad.final_urls.append(FINAL_URL)
        rsa = aga.ad.responsive_search_ad
        pin3 = rot(PIN, i)[:3]
        for h in pin3:
            a = client.get_type("AdTextAsset"); a.text = h
            a.pinned_field = E.ServedAssetFieldTypeEnum.HEADLINE_1; rsa.headlines.append(a)
        for h in [x for x in rot(FREE, i) if x not in pin3][:12]:
            a = client.get_type("AdTextAsset"); a.text = h; rsa.headlines.append(a)
        for d in rot(DESCS, i)[:4]:
            a = client.get_type("AdTextAsset"); a.text = d; rsa.descriptions.append(a)
        if P1: rsa.path1 = P1
        if P2: rsa.path2 = P2
        ops.append(op)
    req = client.get_type("MutateAdGroupAdsRequest")
    req.customer_id = CID; req.operations = ops; req.partial_failure = True
    res = svc.mutate_ad_group_ads(request=req)
    print("✓ Добавлено RSA: %d из %d (PAUSED)" % (sum(1 for r in res.results if r.resource_name), COUNT))


if __name__ == "__main__":
    try:
        run()
    except GoogleAdsException as ex:
        print("GoogleAdsException:")
        for e in ex.failure.errors:
            print("  -", e.message)
        sys.exit(1)
