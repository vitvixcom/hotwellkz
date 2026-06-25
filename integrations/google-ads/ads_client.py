#!/usr/bin/env python3
"""Thin wrapper that builds a Google Ads API client from environment variables.

Credentials are read from GOOGLE_ADS_* env vars (set them from GitHub Secrets in
CI, or export locally). Nothing secret is committed to the repo.

Usage:
    python ads_client.py test                       # list accessible customers
    python ads_client.py accounts                   # same, formatted
    python ads_client.py campaigns <customer_id>    # list campaigns for an account
"""
import os
import sys

REQUIRED = ("developer_token", "client_id", "client_secret", "refresh_token")


def _env(name):
    # strip whitespace/newlines that often sneak into copied secret values —
    # gRPC metadata headers reject them with "Invalid metadata".
    return os.environ.get(name, "").strip()


def load_config():
    cfg = {
        "developer_token": _env("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id": _env("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": _env("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": _env("GOOGLE_ADS_REFRESH_TOKEN"),
        "use_proto_plus": True,
    }
    login_cid = "".join(ch for ch in _env("GOOGLE_ADS_LOGIN_CUSTOMER_ID") if ch.isdigit())
    if login_cid:
        cfg["login_customer_id"] = login_cid

    missing = [k for k in REQUIRED if not cfg.get(k)]
    if missing:
        sys.exit(
            "Missing credentials: "
            + ", ".join("GOOGLE_ADS_" + k.upper() for k in missing)
            + "\nSet them as env vars / GitHub Secrets (see README.md)."
        )
    return cfg


def get_client():
    try:
        from google.ads.googleads.client import GoogleAdsClient
    except ImportError:
        sys.exit("google-ads not installed. Run: pip install -r requirements.txt")
    return GoogleAdsClient.load_from_dict(load_config())


def list_accessible_customers():
    client = get_client()
    svc = client.get_service("CustomerService")
    res = svc.list_accessible_customers()
    return [name.split("/")[-1] for name in res.resource_names]


def list_campaigns(customer_id):
    client = get_client()
    ga = client.get_service("GoogleAdsService")
    query = """
        SELECT campaign.id, campaign.name, campaign.status
        FROM campaign
        ORDER BY campaign.id
    """
    rows = ga.search(customer_id=customer_id.replace("-", ""), query=query)
    return [(r.campaign.id, r.campaign.name, r.campaign.status.name) for r in rows]


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "test"
    if cmd in ("test", "accounts"):
        ids = list_accessible_customers()
        print(f"OK — authentication works. Accessible customers ({len(ids)}):")
        for cid in ids:
            print(f"  - {cid}")
    elif cmd == "campaigns":
        if len(sys.argv) < 3:
            sys.exit("usage: python ads_client.py campaigns <customer_id>")
        for cid, name, status in list_campaigns(sys.argv[2]):
            print(f"  {cid}\t{status}\t{name}")
    else:
        sys.exit(f"unknown command: {cmd}")


if __name__ == "__main__":
    main()
