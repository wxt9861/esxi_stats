{% if prerelease %}

## This is a BETA version

{% endif %}

# **Breaking Changes in 0.5**

## Each ESXi related objects (vm, datastore, etc) are now their own sensors, this will require you to change lovelace configuration and any template sensors

## If configured via Integrations UI, follow these steps

- Update the component
- Restart HASS - when hass boots the component will fail to load. That's ok
- Once HASS UI is back, go to Configuration > Integrations > ESXi Stats integrtion and remove the integration
- Add the Integration back

## YAML configuration is no longer supported, re-configure via the Integrations UI

## Services now require host as part of service call data. See documentation

## See changelog for more details

# Configuration options

| Key                    | Type      | Required | Default | Description                                                                                                                                                                                                                                                                                                    |
| ---------------------- | --------- | -------- | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `host`                 | `string`  | `True`   | None    | ESXi host or vCenter                                                                                                                                                                                                                                                                                           |
| `username`             | `string`  | `True`   | None    | Username to ESXi host or vCenter                                                                                                                                                                                                                                                                               |
| `password`             | `string`  | `True`   | None    | Password to ESXi host or vCenter                                                                                                                                                                                                                                                                               |
| `verify_ssl`           | `boolean` | False    | False   | Leave at default if your ESXi host or vCenter is using a self-signed certificate (most likely scneario). Change to **true** if you replaced a self-signed certificate. If you're using a self-signed cert and set this to True, the component will not be able to establish a connection with the host/vcenter |
| `monitored_conditions` | `list`    | False    | all     | What information do you want to get from the host/vcenter. Available options are **vmhost**, **datastore**, **license**, and **vm**                                                                                                                                                                            |

ESXi Stats can be configured via Integrations UI

## Integration page

1. From Home Assistant UI go to Confinguration > Integrations
2. Click the orange + icon at the bottom right to bring up new integration window
3. Find and click on ESXi Stats
4. Enter required information/select wanted stats and click Submit

To enable debug

```yaml
logger:
  logs:
    custom_components.esxi_stats: debug
```
