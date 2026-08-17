"""Update an Azure DNS record with the caller's current public IP.

Originally based on https://www.frodehus.dev/azure-dyndns/
(https://github.com/FrodeHus/azure-dyndns).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

import urllib3
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.mgmt.dns import DnsManagementClient

logger = logging.getLogger("azure_ddns")

DEFAULT_IP_LOOKUP_URL = "https://ifconfig.me/ip"
DEFAULT_TTL_SECONDS = 300

REQUIRED_CONFIG_KEYS = ("subscriptionId", "resourceGroup", "zoneName", "recordName")

# Maps config keys to the environment variables Azure SDKs/tools conventionally use.
ENV_FALLBACKS = {
    "subscriptionId": "AZURE_SUBSCRIPTION_ID",
    "tenantId": "AZURE_TENANT_ID",
    "clientId": "AZURE_CLIENT_ID",
    "clientSecret": "AZURE_CLIENT_SECRET",
}


def parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Update an Azure DNS record based on the current public IP"
    )
    parser.add_argument("--config", help="Path to JSON configuration file")
    parser.add_argument("--subscription-id", help="Azure subscription ID")
    parser.add_argument("--resource-group", help="Azure resource group name")
    parser.add_argument("--zone", help="Azure DNS zone name")
    parser.add_argument("--record", help="DNS record name to create/update")
    parser.add_argument("--tenant-id", help="Azure tenant ID (or set AZURE_TENANT_ID)")
    parser.add_argument(
        "--client-id",
        help="Azure service principal client id (or set AZURE_CLIENT_ID)",
    )
    parser.add_argument(
        "--client-secret",
        help="Service principal client secret (or set AZURE_CLIENT_SECRET)",
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=None,
        help=(
            "If set, run continuously and check/update the record every N seconds "
            "instead of exiting after a single run (or set AZURE_DDNS_INTERVAL_SECONDS)"
        ),
    )
    parser.add_argument(
        "--log-level",
        default=None,
        help="Logging level (DEBUG, INFO, WARNING, ERROR). Defaults to INFO (or set LOG_LEVEL)",
    )
    return parser.parse_args(argv)


def setup_logging(level: Optional[str] = None) -> None:
    resolved = (level or os.getenv("LOG_LEVEL") or "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, resolved, logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def build_config(args: argparse.Namespace) -> dict:
    """Resolve configuration from (in order of priority) CLI args, config file,
    then well-known Azure environment variables."""
    config: dict = {}

    if args.config:
        logger.debug("Loading configuration from %s", args.config)
        with open(args.config, "r") as config_file:
            config.update(json.load(config_file))

    cli_overrides = {
        "subscriptionId": args.subscription_id,
        "resourceGroup": args.resource_group,
        "zoneName": args.zone,
        "recordName": args.record,
        "tenantId": args.tenant_id,
        "clientId": args.client_id,
        "clientSecret": args.client_secret,
    }
    for key, value in cli_overrides.items():
        if value is not None:
            config[key] = value

    for key, env_var in ENV_FALLBACKS.items():
        if not config.get(key) and os.getenv(env_var):
            config[key] = os.getenv(env_var)

    missing = [key for key in REQUIRED_CONFIG_KEYS if not config.get(key)]
    if missing:
        raise ValueError(
            f"Missing required configuration value(s): {', '.join(missing)}. "
            "Provide them via --config, CLI flags, or environment variables."
        )

    return config


def build_credential(config: dict):
    """Use an explicit service principal if provided, otherwise fall back to
    DefaultAzureCredential (env vars, managed identity, Azure CLI login, etc.)."""
    if config.get("tenantId") and config.get("clientId") and config.get("clientSecret"):
        logger.debug("Using ClientSecretCredential")
        return ClientSecretCredential(
            config["tenantId"], config["clientId"], config["clientSecret"]
        )
    logger.debug("Using DefaultAzureCredential")
    return DefaultAzureCredential()


def get_external_ip(lookup_url: Optional[str] = None, timeout: float = 10.0) -> str:
    lookup_url = lookup_url or os.getenv("IP_LOOKUP_URL", DEFAULT_IP_LOOKUP_URL)
    retries = urllib3.Retry(total=3, backoff_factor=1)
    with urllib3.PoolManager(retries=retries, timeout=timeout) as http:
        response = http.request("GET", lookup_url)
        if response.status != 200:
            raise RuntimeError(
                f"Failed to resolve public IP from {lookup_url}: HTTP {response.status}"
            )
        ip = response.data.decode("utf-8").strip()
        logger.debug("Resolved external IP %s via %s", ip, lookup_url)
        return ip


def update_dns(config: dict, credential, ip: str) -> None:
    dns_client = DnsManagementClient(credential, subscription_id=config["subscriptionId"])
    record_set = dns_client.record_sets.create_or_update(
        config["resourceGroup"],
        config["zoneName"],
        config["recordName"],
        "A",
        {
            "ttl": DEFAULT_TTL_SECONDS,
            "arecords": [{"ipv4_address": ip}],
            "metadata": {
                "createdBy": "azure-ddns (python)",
                "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        },
    )
    logger.info(
        "Updated DNS record %s -> %s (state=%s)",
        record_set.fqdn,
        ip,
        record_set.provisioning_state,
    )


def run_once(config: dict, credential, last_ip: Optional[str] = None) -> str:
    ip = get_external_ip()
    if ip == last_ip:
        logger.debug("Public IP unchanged (%s), skipping Azure DNS update", ip)
        return ip
    update_dns(config, credential, ip)
    return ip


def main(argv: Optional[list] = None) -> None:
    args = parse_args(argv)
    setup_logging(args.log_level)

    try:
        config = build_config(args)
    except ValueError as exc:
        logger.error(str(exc))
        raise SystemExit(1) from exc

    credential = build_credential(config)

    interval = args.interval_seconds
    if interval is None:
        interval = int(os.getenv("AZURE_DDNS_INTERVAL_SECONDS", "0"))

    if interval > 0:
        logger.info("Starting azure-ddns in loop mode (interval=%ss)", interval)
        last_ip = None
        while True:
            try:
                last_ip = run_once(config, credential, last_ip)
            except Exception:  # noqa: BLE001 - keep the loop alive on transient errors
                logger.exception("Failed to check/update DNS record, will retry next interval")
            time.sleep(interval)
    else:
        run_once(config, credential)


if __name__ == "__main__":
    main()
