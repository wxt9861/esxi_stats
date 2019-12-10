{% if prerelease %}

## This is a BETA version

{% endif %}

# **Breaking Changes in 0.5.1**

## VM sensor attribute cpu_use_% has been changed to cpu_use_pct. If you have custom sensors relying on this attribute, please modify them to reflect new attribute name

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
