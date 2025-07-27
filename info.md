# ESXi Stats Integration

Complete ESXi and vCenter monitoring and management integration for Home Assistant.

## Features

- **Full vCenter Support**: Monitor and control multiple ESXi hosts through vCenter
- **UI Controls**: VM power switches, host reboot buttons, and power policy selectors
- **Service Calls**: Host power management, VM operations, and snapshot management
- **Comprehensive Monitoring**: Host, datastore, license, and VM information
- **Production Ready**: Enhanced error handling and safety mechanisms

# Configuration options

| Key                    | Type      | Required | Default | Description                                                                                                                                                                                                                                                                                                    |
| ---------------------- | --------- | -------- | ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `host`                 | `string`  | `True`   | None    | ESXi host or vCenter                                                                                                                                                                                                                                                                                           |
| `username`             | `string`  | `True`   | None    | Username to ESXi host or vCenter                                                                                                                                                                                                                                                                               |
| `password`             | `string`  | `True`   | None    | Password to ESXi host or vCenter                                                                                                                                                                                                                                                                               |
| `verify_ssl`           | `boolean` | False    | False   | Leave at default if your ESXi host or vCenter is using a self-signed certificate (most likely scneario). Change to **true** if you replaced a self-signed certificate. If you're using a self-signed cert and set this to True, the component will not be able to establish a connection with the host/vcenter |
| `monitored_conditions` | `list`    | False    | all     | What information do you want to get from the host/vcenter. Available options are **vmhost**, **datastore**, **license**, and **vm**                                                                                                                                                                            |

ESXi Stats can be configured via Integrations UI

## Integration Setup

1. From Home Assistant UI go to Configuration > Integrations
2. Click the orange + icon at the bottom right to bring up new integration window
3. Find and click on ESXi Stats
4. Enter required information/select wanted stats and click Submit

## UI Controls

After setup, you'll have access to:
- **VM Power Switches**: Control individual virtual machines
- **Host Power Switches**: Safely shutdown ESXi hosts
- **Host Reboot Buttons**: Restart ESXi hosts with safety checks
- **Power Policy Selectors**: Change host power management policies

## Debug Logging

```yaml
logger:
  logs:
    custom_components.esxi_stats: debug
```
