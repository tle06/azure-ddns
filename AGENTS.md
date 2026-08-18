# Azure DDNS - Agent Guidance

## Project Structure

- Python 3.10+ package for Azure Dynamic DNS updates
- Primary package in `azure_ddns/azure_ddns/` directory (repo root contains the
  `azure_ddns/` project folder, which itself contains the `azure_ddns/` package)
- Uses `uv` for dependency management, locking, and packaging (migrated from Poetry)
- Single entrypoint: `azure_ddns.cli:main` (mapped to CLI command `azure-ddns`)
- Build backend is `hatchling` (declared in `azure_ddns/pyproject.toml`)

## Development Commands

All commands below run from the `azure_ddns/` subdirectory (where `pyproject.toml` lives).

**Local setup:**
```bash
cd azure_ddns
uv sync
```

**Run locally:**
```bash
uv run azure-ddns --help
```

**Lint / format (must pass in CI):**
```bash
uv run black --check --diff .
uv run flake8 .
```

**Run tests:**
```bash
uv run pytest -v
```

**Build package:**
```bash
uv build
```

**Publish to PyPI:**
- Handled by the `Publish package` GitHub Actions workflow via PyPI trusted
  publishing (OIDC) on `release: published`. No local publish command/token needed.

## Configuration

- Config resolution order (highest wins): CLI flags > `--config` JSON file > Azure env vars
- Required keys: `subscriptionId`, `resourceGroup`, `zoneName`, `recordName`
- Env var fallbacks: `AZURE_SUBSCRIPTION_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`
- Uses `ClientSecretCredential` if tenant/client id/secret are all resolved, otherwise
  falls back to `DefaultAzureCredential`
- `azure_ddns/example-config.json` shows the JSON config shape
- `cli.py` has no import-time side effects (safe to `import azure_ddns.cli` for tests) —
  logic lives in testable functions (`build_config`, `build_credential`, `update_dns`, etc.)

## Continuous / loop mode

- `--interval-seconds N` (or env `AZURE_DDNS_INTERVAL_SECONDS`) runs the check
  forever instead of exiting after one run; skips the Azure DNS API call if the
  public IP hasn't changed since the last check
- Exceptions during a loop iteration are logged (with traceback) and swallowed so
  the process keeps running and retries on the next interval
- `--log-level` (or env `LOG_LEVEL`) controls verbosity; defaults to `INFO`

## Container

- `azure_ddns/Dockerfile` is a multi-stage build: `ghcr.io/astral-sh/uv` builder
  stage + `python:3.12-alpine` runtime stage, runs as non-root user `azureddns`
- Build context is the `azure_ddns/` subdirectory, not the repo root
- **Important:** the builder must run `uv sync --frozen --no-dev --no-editable`
  (not the default editable install) or the entrypoint will fail at runtime with
  `ModuleNotFoundError: No module named 'azure_ddns'` because the runtime stage
  only copies `.venv`, not the source tree
- Default `ENTRYPOINT` is `azure-ddns`, with `AZURE_DDNS_INTERVAL_SECONDS=300`
  baked in as a default env var (override with `-e` at `docker run` time)
- Local build/run: `docker build -t azure-ddns azure_ddns/ && docker run --rm azure-ddns --help`
- `azure_ddns/docker-compose.yml` + `azure_ddns/.env.example` provide a ready-to-use
  local setup: `cp .env.example .env` (fill in real values), then `docker compose up -d`;
  `.env` is gitignored, never commit real credentials

## Testing

- Test suite: `azure_ddns/tests/test_azure_ddns.py` — covers version, arg parsing,
  and `build_config` precedence/validation (CLI > file > env, missing-key errors)
- No network or Azure credentials required to run the test suite
- Run with: `uv run pytest -v` from `azure_ddns/`

## CI/CD (GitHub Actions, `.github/workflows/`)

- `ci.yml` — on push/PR to `main`: `black --check`, `flake8`, `pytest`, `uv build`
- `container-ci.yml` — on push/PR touching `azure_ddns/**`: builds the Docker
  image (no push) and smoke-tests `--help` and the missing-config error path
- `publish-package.yml` — on GitHub Release published: builds and publishes to
  PyPI via trusted publishing (needs a `pypi` environment configured in repo
  settings; no stored token)
- `publish-container.yml` — on GitHub Release published: builds and pushes the
  image to GHCR (`ghcr.io/<owner>/<repo>`) tagged with semver + `latest`, using
  the built-in `GITHUB_TOKEN` (no extra secret needed)
- Releases (not plain tag pushes) trigger both publish workflows — cutting a
  GitHub Release is the actual release mechanism for this repo

## Releasing

- **Tag convention:** git tags/releases must be `vX.Y.Z` (e.g. `v0.2.0`), matching
  the `version` in `azure_ddns/pyproject.toml` and `__version__` in
  `azure_ddns/azure_ddns/__init__.py`. Bump both files first, then cut the tag/release.
  A bare tag like `0.0.1` (no `v`, or not matching the package version) will still
  build, but `docker/metadata-action`'s `type=semver` tagging in
  `publish-container.yml` expects a `v`-prefixed tag to produce clean version tags.
- **One-time PyPI setup required before the first release:** `publish-package.yml`
  uses PyPI trusted publishing (OIDC), which requires a trusted publisher to be
  registered on PyPI (https://pypi.org/manage/project/azure-ddns/settings/publishing/,
  or pre-register via https://pypi.org/manage/account/publishing/ if the project
  doesn't exist on PyPI yet) with exactly: owner `tle06`, repository `azure-ddns`,
  workflow `publish-package.yml`, environment `pypi`. The GitHub repo also needs a
  matching `pypi` environment (Settings → Environments) since the job declares
  `environment: pypi` — without it the OIDC token's `environment` claim won't be
  present and won't match the PyPI configuration. Missing/mismatched config fails
  with `invalid-publisher` at publish time, not before.

## Package Details

- CLI entrypoint registered in `pyproject.toml` as `azure-ddns`
- Dependencies: `azure-identity`, `azure-mgmt-dns` (kept in sync with latest
  stable PyPI releases; check for new majors before bumping blindly since
  `azure-mgmt-dns` has had breaking changes across majors)
- Dev dependencies (`dependency-groups.dev`): `pytest`, `black`, `flake8`
- License: MIT (see `LICENSE` file)
- Version tracking: keep `azure_ddns/azure_ddns/__init__.py` (`__version__`) and
  `azure_ddns/pyproject.toml` (`version`) in sync manually — nothing automates this
