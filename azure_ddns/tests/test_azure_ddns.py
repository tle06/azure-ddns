import argparse
import json

import pytest

from azure_ddns import __version__
from azure_ddns.cli import build_config, parse_args


def test_version():
    assert __version__ == "0.0.4"


def _args(**overrides) -> argparse.Namespace:
    base = dict(
        config=None,
        subscription_id=None,
        resource_group=None,
        zone=None,
        record=None,
        tenant_id=None,
        client_id=None,
        client_secret=None,
        interval_seconds=None,
        log_level=None,
    )
    base.update(overrides)
    return argparse.Namespace(**base)


def test_parse_args_defaults():
    args = parse_args([])
    assert args.config is None
    assert args.interval_seconds is None


def test_build_config_from_cli_args(monkeypatch):
    monkeypatch.delenv("AZURE_SUBSCRIPTION_ID", raising=False)
    monkeypatch.delenv("AZURE_TENANT_ID", raising=False)
    monkeypatch.delenv("AZURE_CLIENT_ID", raising=False)
    monkeypatch.delenv("AZURE_CLIENT_SECRET", raising=False)

    args = _args(
        subscription_id="sub-id",
        resource_group="rg",
        zone="example.com",
        record="home",
    )
    config = build_config(args)
    assert config["subscriptionId"] == "sub-id"
    assert config["resourceGroup"] == "rg"
    assert config["zoneName"] == "example.com"
    assert config["recordName"] == "home"


def test_build_config_from_file(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "subscriptionId": "sub-id",
                "resourceGroup": "rg",
                "zoneName": "example.com",
                "recordName": "home",
            }
        )
    )
    args = _args(config=str(config_path))
    config = build_config(args)
    assert config["zoneName"] == "example.com"


def test_build_config_cli_overrides_file(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "subscriptionId": "file-sub",
                "resourceGroup": "rg",
                "zoneName": "example.com",
                "recordName": "home",
            }
        )
    )
    args = _args(config=str(config_path), subscription_id="cli-sub")
    config = build_config(args)
    assert config["subscriptionId"] == "cli-sub"


def test_build_config_uses_env_fallback(monkeypatch):
    monkeypatch.setenv("AZURE_SUBSCRIPTION_ID", "env-sub")
    args = _args(resource_group="rg", zone="example.com", record="home")
    config = build_config(args)
    assert config["subscriptionId"] == "env-sub"


def test_build_config_missing_raises(monkeypatch):
    monkeypatch.delenv("AZURE_SUBSCRIPTION_ID", raising=False)
    args = _args()
    with pytest.raises(ValueError):
        build_config(args)
