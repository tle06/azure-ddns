# Azure Dynamic DNS

## Installation

pip install azure_ddns

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