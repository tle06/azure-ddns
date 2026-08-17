# Azure Dynamic DNS

## Installation

pip install azure-ddns

## Run

You can run the cli tool with all the parameters like this

```cmd
azure-ddns --subscription-id your_ubscription_id --tenant-id your_tenant_id --client-id your_client_id --client-secret your_client_secret --resource-group your_ressource_group_name --zone your_zone_name --record your_record-name
```

You can also use a json file

```cmd
azure-ddns --config path/to/your/config.json
```

The json should be formated like this:

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

CLI flags take priority over the config file, which takes priority over
environment variables (`AZURE_SUBSCRIPTION_ID`, `AZURE_TENANT_ID`,
`AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`). If tenant/client id/secret aren't
all resolved, `DefaultAzureCredential` is used instead (managed identity,
Azure CLI login, etc.).

## Run continuously

By default the tool checks the IP once and exits. Pass `--interval-seconds`
(or set `AZURE_DDNS_INTERVAL_SECONDS`) to run forever, checking on that
interval and only calling the Azure DNS API when the public IP changed:

```cmd
azure-ddns --config path/to/your/config.json --interval-seconds 300
```

Use `--log-level` (or `LOG_LEVEL`) to control verbosity (`DEBUG`, `INFO`,
`WARNING`, `ERROR`; defaults to `INFO`).