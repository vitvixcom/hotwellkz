#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Бизнес-имя + логотип для кампании [SKAG] СИП-панельные дома Астана (ID 23991449173).
- Business name: текстовый ассет «HotWell.kz» (field_type BUSINESS_NAME).
- Business logo: image-ассет из site/assets/logo-1200.png (1200×1200, field_type BUSINESS_LOGO,
  при отказе пробуем LOGO).
Привязка пробуется на уровне кампании; если уровень не разрешён — на уровне аккаунта (CustomerAsset).
Каждый ассет — независимо, с обработкой ошибок (бизнес-имя/логотип в поиске требуют
проверки рекламодателя; если аккаунт не верифицирован, Google может отклонить показ).
"""
import os, sys
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

CID = os.environ["GOOGLE_ADS_CUSTOMER_ID"].replace("-", "")
CAMPAIGN_ID = os.environ.get("CAMPAIGN_ID", "23991449173")
camp_rn = "customers/%s/campaigns/%s" % (CID, CAMPAIGN_ID)
BUSINESS_NAME = "HotWell.kz"
LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "site", "assets", "logo-1200.png")

cfg = dict(developer_token=os.environ["GOOGLE_ADS_DEVELOPER_TOKEN"],
           client_id=os.environ["GOOGLE_ADS_CLIENT_ID"],
           client_secret=os.environ["GOOGLE_ADS_CLIENT_SECRET"],
           refresh_token=os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
           login_customer_id=CID, use_proto_plus=True)
client = GoogleAdsClient.load_from_dict(cfg)


def errmsg(ex):
    return "; ".join(e.message for e in ex.failure.errors)


def create_asset(build_fn):
    asvc = client.get_service("AssetService")
    op = client.get_type("AssetOperation")
    build_fn(op.create)
    return asvc.mutate_assets(customer_id=CID, operations=[op]).results[0].resource_name


def link(asset_rn, field_type):
    """Пробуем привязать на уровне кампании, при ошибке уровня — на уровне аккаунта."""
    F = client.enums.AssetFieldTypeEnum
    # campaign-level
    try:
        svc = client.get_service("CampaignAssetService")
        op = client.get_type("CampaignAssetOperation")
        op.create.campaign = camp_rn
        op.create.asset = asset_rn
        op.create.field_type = field_type
        svc.mutate_campaign_assets(customer_id=CID, operations=[op])
        return "campaign"
    except GoogleAdsException as ex:
        msg = errmsg(ex)
        # уровень не разрешён → customer-level
        try:
            svc = client.get_service("CustomerAssetService")
            op = client.get_type("CustomerAssetOperation")
            op.create.asset = asset_rn
            op.create.field_type = field_type
            svc.mutate_customer_assets(customer_id=CID, operations=[op])
            return "customer (campaign отклонён: %s)" % msg
        except GoogleAdsException as ex2:
            raise RuntimeError("campaign: %s | customer: %s" % (msg, errmsg(ex2)))


def main():
    F = client.enums.AssetFieldTypeEnum

    # 1) BUSINESS NAME
    try:
        def b_name(a):
            a.name = "HotWell business name"
            a.text_asset.text = BUSINESS_NAME
        rn = create_asset(b_name)
        where = link(rn, F.BUSINESS_NAME)
        print(" ✓ Бизнес-имя «%s» добавлено (%s)" % (BUSINESS_NAME, where))
    except (GoogleAdsException, RuntimeError) as ex:
        print(" ✗ Бизнес-имя не добавлено:", errmsg(ex) if isinstance(ex, GoogleAdsException) else ex)

    # 2) BUSINESS LOGO
    with open(os.path.abspath(LOGO_PATH), "rb") as f:
        logo_bytes = f.read()

    def make_logo(a):
        a.name = "HotWell logo 1200"
        a.type_ = client.enums.AssetTypeEnum.IMAGE
        a.image_asset.data = logo_bytes
        a.image_asset.mime_type = client.enums.MimeTypeEnum.IMAGE_PNG

    try:
        rn = create_asset(make_logo)
    except GoogleAdsException as ex:
        print(" ✗ Логотип не загружен (asset):", errmsg(ex))
        return

    last = None
    for ft_name in ("BUSINESS_LOGO", "LOGO"):
        ft = getattr(F, ft_name)
        try:
            where = link(rn, ft)
            print(" ✓ Логотип добавлен как %s (%s)" % (ft_name, where))
            break
        except (GoogleAdsException, RuntimeError) as ex:
            last = errmsg(ex) if isinstance(ex, GoogleAdsException) else str(ex)
    else:
        print(" ✗ Логотип не привязан:", last)

    print("\n Проверка: https://ads.google.com/aw/campaigns?campaignId=%s" % CAMPAIGN_ID)


if __name__ == "__main__":
    try:
        main()
    except GoogleAdsException as ex:
        print("GoogleAdsException:", errmsg(ex)); sys.exit(1)
