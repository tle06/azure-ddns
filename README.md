[![CI](https://github.com/tle06/azure-ddns/actions/workflows/ci.yml/badge.svg)](https://github.com/tle06/azure-ddns/actions/workflows/ci.yml)
[![Packages](https://img.shields.io/badge/packages-latest-blue.svg)](https://pypi.org/project/azure-ddns/)
![python-version](https://img.shields.io/pypi/pyversions/azure-ddns)
![license](https://img.shields.io/github/license/tle06/azure-ddns)

# Azure-ddns

Azure Dynamic DNS from [FrodeHus](https://www.frodehus.dev/azure-dyndns/) ([repo](https://github.com/FrodeHus/azure-dyndns)) work.

Checks your current public IP and updates an Azure DNS `A` record to match it.
Available as a [PyPI package](https://pypi.org/project/azure-ddns/) and as a
container image on GHCR.

# Requirement

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) for local development
- Azure service principal (or managed identity) with contributor permission on
  the DNS zone targeted

# Configuration

Configuration can be provided via CLI flags, a JSON config file, or
environment variables (highest priority first: CLI flags > `--config` file >
environment variables).

```json
{
    "subscriptionId": "",
    "resourceGroup": "",
    "zoneName": "",
    "recordName": "",
    "clientId": "",
    "clientSecret": "",
    "tenantId": ""
}
```

See `azure_ddns/example-config.json`. Recognized environment variables:
`AZURE_SUBSCRIPTION_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`,
`AZURE_CLIENT_SECRET`. If tenant/client id/secret are not all provided, the
tool falls back to `DefaultAzureCredential` (managed identity, Azure CLI
login, etc.).

# Run with Docker (recommended for a local server)

The container runs in a loop by default, checking the public IP every
`AZURE_DDNS_INTERVAL_SECONDS` seconds (300s / 5 min by default) and only
calling the Azure DNS API when the IP actually changed.

```bash
docker run -d \
  --name azure-ddns \
  --restart unless-stopped \
  -e AZURE_SUBSCRIPTION_ID=your_subscription_id \
  -e AZURE_TENANT_ID=your_tenant_id \
  -e AZURE_CLIENT_ID=your_client_id \
  -e AZURE_CLIENT_SECRET=your_client_secret \
  ghcr.io/tle06/azure-ddns:latest \
  --resource-group your_resource_group --zone your_zone_name --record your_record_name
```

Or with a mounted config file:

```bash
docker run -d \
  --name azure-ddns \
  --restart unless-stopped \
  -v /path/to/config.json:/config.json:ro \
  ghcr.io/tle06/azure-ddns:latest \
  --config /config.json
```

Logs (including retries on transient failures) are written to stdout:

```bash
docker logs -f azure-ddns
```

To build the image locally instead of pulling from GHCR:

```bash
docker build -t azure-ddns azure_ddns/
docker run --rm azure-ddns --help
```

## Run with Docker Compose

A `docker-compose.yml` with an example `.env` file is provided in
`azure_ddns/`:

```bash
cd azure_ddns
cp .env.example .env
# edit .env with your Azure credentials and DNS zone/record

docker compose up -d
docker compose logs -f
```

`.env` is gitignored -- never commit real credentials.

# Run as a Python package

## Install from PyPI

```bash
pip install azure-ddns
```

## Local development setup

```bash
git clone https://github.com/tle06/azure-ddns.git
cd azure-ddns/azure_ddns
uv sync
```

## Execute locally

```bash
uv run azure-ddns --config path/to/config.json
```

Or run continuously without a container (useful for testing loop mode):

```bash
uv run azure-ddns --config path/to/config.json --interval-seconds 300
```

## Lint and test

```bash
uv run black --check --diff .
uv run flake8 .
uv run pytest -v
```

## Build package

```bash
uv build
pip install dist/azure_ddns-*-py3-none-any.whl --force-reinstall
```

## Cron task on Linux (bare-metal, without the container's built-in loop)

If you need a cron generator check [here](https://crontab.guru/)

```bash
crontab -e
*/30 * * * * /path/to/azure-ddns --config /home/user/azure-dyndns.json >> /var/log/azure-ddns.log 2>&1
```

# Releasing

Publishing to PyPI and pushing the container image to GHCR are both handled
by GitHub Actions and triggered by publishing a GitHub Release (see
`.github/workflows/publish-package.yml` and `.github/workflows/publish-container.yml`).

To cut a release:

1. Bump `version` in `azure_ddns/pyproject.toml` and `__version__` in
   `azure_ddns/azure_ddns/__init__.py` to the same value, e.g. `0.2.0`.
2. Commit, then create a GitHub Release with tag `v0.2.0` (the `v` prefix is
   required for correct semver tagging of the container image).
3. The `Publish package` and `Publish container` workflows run automatically.

**First-time setup:** publishing to PyPI uses
[trusted publishing](https://docs.pypi.org/trusted-publishers/) (OIDC, no
stored token). Before the first release, register a trusted publisher on PyPI
for this project with owner `tle06`, repository `azure-ddns`, workflow
`publish-package.yml`, and environment `pypi` -- and make sure a matching
`pypi` environment exists under the repo's Settings > Environments.
