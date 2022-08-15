# Azure-ddns
Azure Dynamic DNS from [FrodeHus](https://www.frodehus.dev/azure-dyndns/) ([repo](https://github.com/FrodeHus/azure-dyndns)) work.
The package is available [here](https://pypi.org/project/azure-ddns/) to run directly from CLI


# Requirement

- python 3.10
- poetry
- Azure application id and secret with contribute permission on the DNS zone targeted

## Setup local

Create virtual environment:

``` cmd
git clone https://github.com/tle06/azure-ddns.git
cd azure-ddns/azure_ddns
poetry shell
poetry install
```

## Execute locally

``` cmd
poetry run python azure_ddns/cli.py
```

## Build package

``` cmd
poetry build
pip install dist/azure_ddns-0.0.1-py3-none-any.whl --force-reinstall
```
## Install the package build

If needed replace the version number

``` cmd
pip install dist/azure_ddns-*-py3-none-any.whl --force-reinstall
```

## Publish package

``` cmd

export PYPI_USERNAME=__token__
export PYPI_PASSWORD=pypi_token_to_be_replace_by_yours
poetry publish --build --username $PYPI_USERNAME --password $PYPI_PASSWORD
```

## Install package from Pypi.org

```cmd
pip install azure-ddns
```

## Cron task on your linux

If you need a cron generator check [here](https://crontab.guru/)

```cmd
crontab -e
*/30 * * * * azure-ddns -config /home/user/azure-dyndns.json > dyndns.txt
```