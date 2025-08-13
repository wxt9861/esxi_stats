# pylint: disable=import-outside-toplevel

"""ESXi commands for ESXi Stats component."""
import logging
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl  # pylint: disable=no-name-in-module

from .const import SUPPORTED_PRODUCTS

_LOGGER = logging.getLogger(__name__)


def esx_connect(host, user, pwd, port, ssl):
    """Establish connection with host/vcenter."""
    service_instance = None

    try:
        # connect depending on SSL_VERIFY setting
        if ssl is False:
            service_instance = SmartConnect(
                host=host, user=user, pwd=pwd, port=port, disableSslCertValidation=True
            )
        else:
            service_instance = SmartConnect(host=host, user=user, pwd=pwd, port=port)

        if service_instance:
            current_session = service_instance.content.sessionManager.currentSession.key
            _LOGGER.debug("Logged in - session %s", current_session)
        else:
            _LOGGER.error("Failed to create service instance for %s", host)
            return None

    except ConnectionRefusedError as error:
        _LOGGER.error("Connection refused to %s: %s", host, error)
        return None
    except Exception as error:  # pylint: disable=broad-except
        _LOGGER.error("Failed to connect to %s: %s", host, error)
        return None

    return service_instance


def esx_disconnect(conn):
    """Kill connection from host/vcenter."""

    if conn:
        current_session = conn.content.sessionManager.currentSession.key
        try:
            Disconnect(conn)
            ## This is an old method to disconnect without leaving an active session on the ESXi host
            ## Keeping this commented out, but will remove in future release
            # conn._stub.pool[0][0].sock.shutdown(2)  # pylint: disable=protected-access
            _LOGGER.debug("Logged out - session %s", current_session)
        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.debug(error)


def check_license(lic):
    """Retrieve license from connected system."""
    _LOGGER.debug("Checking license type")

    if not lic or not hasattr(lic, 'licenses'):
        _LOGGER.warning("No license information available")
        return False

    for license_obj in lic.licenses:
        if not hasattr(license_obj, 'properties'):
            continue

        product_name = None
        for key in license_obj.properties:
            if key.key == "ProductName":
                product_name = key.value
                break

        if not product_name or product_name not in SUPPORTED_PRODUCTS:
            continue

        _LOGGER.debug("Found %s license", product_name)

        # Check for vCenter Server (index 1)
        if product_name == SUPPORTED_PRODUCTS[1]:
            return True

        # Check for ESX Server (index 0) with vSphere API feature
        if product_name == SUPPORTED_PRODUCTS[0]:
            for feature in license_obj.properties:
                if (feature.key == "feature" and
                    hasattr(feature.value, 'key') and
                    feature.value.key == "vimapi"):
                    _LOGGER.debug("vSphere API feature enabled")
                    return True

    _LOGGER.warning("No supported license found")
    return False


def get_license_info(lic, host):
    """Get license information."""
    expiration = "n/a"
    product = "n/a"
    status = "n/a"

    for key in lic.properties:
        if key.key == "ProductName":
            product = key.value
        if key.key == "count_disabled":
            expiration = "never"
        if key.key == "expirationHours":
            expiration = round((key.value / 24))

    if isinstance(expiration, int):
        if expiration > 30:
            status = "Ok"
        if expiration <= 30:
            status = "Expiring Soon"
        if expiration < 1:
            status = "expired"
    else:
        status = "Ok"

    license_data = {
        "name": lic.name,
        "status": status,
        "product": product,
        "expiration_days": expiration,
        "host": host,
        "license_key": getattr(lic, 'licenseKey', 'n/a'),
    }

    _LOGGER.debug(license_data)

    return license_data


def get_host_info(host):
    """Get host information."""
    host_summary = host.summary
    host_state = host_summary.runtime.powerState
    host_name = host_summary.config.name.replace(" ", "_").lower()
    host_capability = host.capability

    _LOGGER.debug("vmhost: %s state is %s", host_name, host_state)

    if hasattr(host_summary.runtime, "inMaintenanceMode"):
        host_mm_mode = host_summary.runtime.inMaintenanceMode
    else:
        host_mm_mode = "N/A"

    if host_state == "poweredOn":
        host_version = host_summary.config.product.version
        host_build = host_summary.config.product.build
        host_uptime = round(host_summary.quickStats.uptime / 3600, 1)
        host_cpu_total = round(
            host_summary.hardware.cpuMhz * host_summary.hardware.numCpuCores / 1000, 1
        )
        host_mem_total = round(host_summary.hardware.memorySize / 1073741824, 2)
        host_cpu_usage = round(host_summary.quickStats.overallCpuUsage / 1000, 1)
        host_mem_usage = round(host_summary.quickStats.overallMemoryUsage / 1024, 2)

        # Get current power policy
        try:
            host_power_policy = host.config.powerSystemInfo.currentPolicy.shortName
        except Exception as e:
            _LOGGER.debug("Could not get current power policy for %s: %s", host_name, e)
            host_power_policy = "n/a"

        # Get available power policies
        available_power_policies = []
        try:
            if (hasattr(host.config, 'powerSystemCapability') and
                host.config.powerSystemCapability):
                for policy in host.config.powerSystemCapability.availablePolicy:
                    available_power_policies.append(policy.shortName)
                available_power_policies = sorted(available_power_policies)
        except Exception as e:
            _LOGGER.debug("Could not get available power policies for %s: %s", host_name, e)

        host_vms = len(host.vm)
    else:
        host_version = "n/a"
        host_build = "n/a"
        host_uptime = "n/a"
        host_cpu_total = "n/a"
        host_cpu_usage = "n/a"
        host_mem_total = "n/a"
        host_mem_usage = "n/a"
        host_power_policy = "n/a"
        available_power_policies = []
        host_vms = "n/a"

        _LOGGER.debug("Unable to return stats for %s", host_name)

    host_data = {
        "name": host_name,
        "original_name": host_summary.config.name,  # Store original for exact matching
        "state": host_state,
        "version": host_version,
        "build": host_build,
        "uptime_hours": host_uptime,
        "cputotal_ghz": host_cpu_total,
        "cpuusage_ghz": host_cpu_usage,
        "memtotal_gb": host_mem_total,
        "memusage_gb": host_mem_usage,
        "maintenance_mode": host_mm_mode,
        "shutdown_supported": host_capability.shutdownSupported,
        "power_policy": host_power_policy,
        "available_power_policies": available_power_policies,
        "vms": host_vms,
    }

    _LOGGER.debug(host_data)

    return host_data


def get_datastore_info(datastore):
    """Get datastore information."""
    ds_summary = datastore.summary
    ds_name = ds_summary.name.replace(" ", "_").lower()
    ds_capacity = round(ds_summary.capacity / 1073741824, 2)
    ds_freespace = round(ds_summary.freeSpace / 1073741824, 2)
    ds_type = ds_summary.type.lower()

    ds_data = {
        "name": ds_name,
        "type": ds_type,
        "free_space_gb": ds_freespace,
        "total_space_gb": ds_capacity,
        "connected_hosts": len(datastore.host),
        "virtual_machines": len(datastore.vm),
    }

    _LOGGER.debug(ds_data)

    return ds_data


def get_vm_info(virtual_machine):
    """Get VM information."""
    vm_conf = virtual_machine.configStatus
    vm_sum = virtual_machine.summary
    vm_run = virtual_machine.runtime
    vm_snap = virtual_machine.snapshot

    vm_name = vm_sum.config.name.replace(" ", "_").lower()
    vm_proper_name = vm_sum.config.name

    # If a VM configuration is in INVALID state, return Inalid status
    if vm_conf == "red":
        vm_data = {"name": vm_name, "status": "Invalid"}
        _LOGGER.debug(vm_data)
        return vm_data

    vm_tools_status = vm_sum.guest.toolsStatus
    vm_used_space = round(vm_sum.storage.committed / 1073741824, 2)

    # if snapshots present, get number of snapshots
    if vm_snap is not None:
        vm_snapshots = len(list_snapshots(vm_snap.rootSnapshotList))
    else:
        vm_snapshots = 0

    # set vm_state based on power state
    if vm_sum.runtime.powerState == "poweredOn":
        vm_state = "running"
    elif vm_sum.runtime.powerState == "poweredOff":
        vm_state = "off"
    elif vm_sum.runtime.powerState == "suspended":
        vm_state = "suspended"
    else:
        vm_state = vm_sum.runtime.powerState

    # set runtime related attributes based on vm power state
    if vm_state == "running":
        # check if stats exist and set values, otherwise return "n/a"
        if vm_sum.quickStats.overallCpuUsage and vm_run.maxCpuUsage:
            vm_cpu_usage = round(
                ((vm_sum.quickStats.overallCpuUsage / vm_run.maxCpuUsage) * 100), 2
            )
        else:
            vm_cpu_usage = "n/a"
            _LOGGER.debug("Unable to return cpu usage for %s", vm_name)

        if vm_sum.quickStats.hostMemoryUsage:
            vm_mem_usage = round(vm_sum.quickStats.hostMemoryUsage, 2)
        else:
            vm_mem_usage = "n/a"
            _LOGGER.debug("Unable to return host memory usage for %s", vm_name)

        if vm_sum.quickStats.guestMemoryUsage:
            vm_mem_active = round(vm_sum.quickStats.guestMemoryUsage, 2)
        else:
            vm_mem_active = "n/a"
            _LOGGER.debug("Unable to return active memory usage")

        if vm_sum.quickStats.uptimeSeconds:
            vm_uptime = round(vm_sum.quickStats.uptimeSeconds / 3600, 1)
        else:
            vm_uptime = "n/a"
            _LOGGER.debug("Unable to return uptime for %s", vm_name)

        if vm_sum.guest.ipAddress:
            vm_ip = vm_sum.guest.ipAddress
        else:
            vm_ip = "n/a"
            _LOGGER.debug("Unable to return VM IP address for %s", vm_name)

        if vm_sum.guest.guestFullName:
            vm_guest_os = vm_sum.guest.guestFullName
        else:
            _LOGGER.debug(
                ("Unable to return Guest OS Name, using Configured Guest Name instead")
            )
            vm_guest_os = vm_sum.config.guestFullName
    else:
        vm_cpu_usage = "n/a"
        vm_mem_usage = "n/a"
        vm_mem_active = "n/a"
        vm_ip = "n/a"
        vm_uptime = "n/a"
        vm_guest_os = vm_sum.config.guestFullName

    vm_data = {
        "name": vm_name,
        "vm_name": vm_proper_name,
        "status": vm_sum.overallStatus,
        "state": vm_state,
        "uptime_hours": vm_uptime,
        "cpu_count": vm_sum.config.numCpu,
        "cpu_use_pct": vm_cpu_usage,
        "memory_allocated_mb": vm_sum.config.memorySizeMB,
        "memory_used_mb": vm_mem_usage,
        "memory_active_mb": vm_mem_active,
        "used_space_gb": vm_used_space,
        "tools_status": vm_tools_status,
        "guest_os": vm_guest_os,
        "guest_ip": vm_ip,
        "snapshots": vm_snapshots,
        "uuid": vm_sum.config.uuid,
        "host_name": vm_run.host.name,
    }

    _LOGGER.debug(vm_data)

    return vm_data


def list_snapshots(snapshots, tree=False):
    """Get VM snapshot information.

    tree=True will return snapshot tree details required for snapshot removal
    """
    snapshot_data = []

    for snapshot in snapshots:
        if tree is True:
            snapshot_data.append(snapshot)
        else:
            snapshot_data.append(snapshot.id)
        snapshot_data = snapshot_data + list_snapshots(snapshot.childSnapshotList, tree)

    return snapshot_data


def host_pwr(hass, target_host_name, target_cmnd, conn_details, force, notify):
    """Host power commands - supports both ESXi and vCenter."""
    import time
    start_time = time.time()

    conn = esx_connect(**conn_details)
    if not conn:
        _LOGGER.error("Failed to connect to %s", conn_details.get('host', 'host'))
        return False

    content = conn.RetrieveContent()
    obj_view = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.HostSystem], True
    )
    esxi_hosts = obj_view.view
    obj_view.Destroy()

    _LOGGER.info("Found %s host(s) in environment", len(esxi_hosts))

    # Determine target host(s)
    target_hosts = []

    if len(esxi_hosts) == 1:
        # Single ESXi host scenario
        if target_host_name:
            # Verify the target host name matches
            host = esxi_hosts[0]
            if (host.summary.config.name.lower() == target_host_name.lower() or
                host.name.lower() == target_host_name.lower()):
                target_hosts = [host]
            else:
                _LOGGER.error(
                    "Target host '%s' does not match available host '%s'",
                    target_host_name, host.summary.config.name
                )
                esx_disconnect(conn)
                return False
        else:
            # No target specified, use the single available host
            target_hosts = esxi_hosts
            _LOGGER.info("No target host specified, using single available host")

    elif len(esxi_hosts) > 1:
        # vCenter with multiple hosts scenario
        if not target_host_name:
            # List available hosts for user reference
            available_hosts = [host.summary.config.name for host in esxi_hosts]
            _LOGGER.error(
                "Multiple hosts found in vCenter. You must specify target_host. "
                "Available hosts: %s", ", ".join(available_hosts)
            )
            esx_disconnect(conn)
            return False
        else:
            # Find the specified target host
            for host in esxi_hosts:
                if (host.summary.config.name.lower() == target_host_name.lower() or
                    host.name.lower() == target_host_name.lower()):
                    target_hosts = [host]
                    break

            if not target_hosts:
                available_hosts = [host.summary.config.name for host in esxi_hosts]
                _LOGGER.error(
                    "Target host '%s' not found. Available hosts: %s",
                    target_host_name, ", ".join(available_hosts)
                )
                esx_disconnect(conn)
                return False

    else:
        # No hosts found
        _LOGGER.error("No ESXi hosts found")
        esx_disconnect(conn)
        return False

    # Execute power command on target host(s)
    try:
        for esxi_host in target_hosts:
            host_name = esxi_host.summary.config.name

            # Check if host is in maintenance mode
            if not force and esxi_host.runtime.inMaintenanceMode is False:
                _LOGGER.warning(
                    "Host '%s' is not in maintenance mode. Consider setting force=true "
                    "or putting the host in maintenance mode first", host_name
                )

            # Check for running VMs if not forced
            if not force:
                vm_count = len([vm for vm in esxi_host.vm if vm.runtime.powerState == "poweredOn"])
                if vm_count > 0:
                    _LOGGER.warning(
                        "Host '%s' has %d powered-on VMs. Consider migrating VMs or setting force=true",
                        host_name, vm_count
                    )

            # Execute the power command
            task = None
            if target_cmnd == "shutdown":
                _LOGGER.info(
                    "Sending shutdown command to host '%s' (forced: %s)",
                    host_name, force
                )
                task = esxi_host.ShutdownHost_Task(force)
            elif target_cmnd == "reboot":
                _LOGGER.info(
                    "Sending reboot command to host '%s' (forced: %s)",
                    host_name, force
                )
                task = esxi_host.RebootHost_Task(force)
            else:
                _LOGGER.error("Unsupported host power command: %s", target_cmnd)
                continue

            # Monitor task status
            if task:
                message = f"Host {target_cmnd} command sent to {host_name} (forced: {force})"
                task_status(hass, task, message, notify)
            else:
                _LOGGER.info("'%s' command does not provide task feedback", target_cmnd)

    except vmodl.MethodFault as error:
        _LOGGER.error("VMware method fault: %s", error.msg)
        return False
    except vmodl.HostConfigFault as error:
        _LOGGER.error("Host configuration fault: %s", str(error))
        return False
    except vmodl.RuntimeFault as error:
        _LOGGER.error("VMware runtime fault: %s", error.msg)
        return False
    except Exception as error:  # pylint: disable=broad-except
        _LOGGER.error("Unexpected error during host power operation: %s", str(error))
        return False
    finally:
        esx_disconnect(conn)
        operation_time = time.time() - start_time
        _LOGGER.info("Host power operation '%s' completed in %.2f seconds", target_cmnd, operation_time)

    return True


def host_pwr_policy(target_host_name, host_cmnd, conn_details):
    """Host power policy command - supports both ESXi and vCenter."""
    conn = esx_connect(**conn_details)
    if not conn:
        _LOGGER.error("Failed to connect to %s", conn_details.get('host', 'host'))
        return False

    content = conn.RetrieveContent()
    obj_view = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.HostSystem], True
    )
    esxi_hosts = obj_view.view
    obj_view.Destroy()

    _LOGGER.info("Found %s host(s) in environment", len(esxi_hosts))

    # Determine target host(s)
    target_hosts = []

    if len(esxi_hosts) == 1:
        # Single ESXi host scenario
        if target_host_name:
            # Verify the target host name matches
            host = esxi_hosts[0]
            if (host.summary.config.name.lower() == target_host_name.lower() or
                host.name.lower() == target_host_name.lower()):
                target_hosts = [host]
            else:
                _LOGGER.error(
                    "Target host '%s' does not match available host '%s'",
                    target_host_name, host.summary.config.name
                )
                esx_disconnect(conn)
                return False
        else:
            # No target specified, use the single available host
            target_hosts = esxi_hosts
            _LOGGER.info("No target host specified, using single available host")

    elif len(esxi_hosts) > 1:
        # vCenter with multiple hosts scenario
        if not target_host_name:
            # List available hosts for user reference
            available_hosts = [host.summary.config.name for host in esxi_hosts]
            _LOGGER.error(
                "Multiple hosts found in vCenter. You must specify target_host. "
                "Available hosts: %s", ", ".join(available_hosts)
            )
            esx_disconnect(conn)
            return False
        else:
            # Find the specified target host
            for host in esxi_hosts:
                if (host.summary.config.name.lower() == target_host_name.lower() or
                    host.name.lower() == target_host_name.lower()):
                    target_hosts = [host]
                    break

            if not target_hosts:
                available_hosts = [host.summary.config.name for host in esxi_hosts]
                _LOGGER.error(
                    "Target host '%s' not found. Available hosts: %s",
                    target_host_name, ", ".join(available_hosts)
                )
                esx_disconnect(conn)
                return False

    else:
        # No hosts found
        _LOGGER.error("No ESXi hosts found")
        esx_disconnect(conn)
        return False

    # Apply power policy to target host(s)
    try:
        for vm_host in target_hosts:
            host_name = vm_host.summary.config.name
            _LOGGER.info(
                "Sending power policy '%s' command to host '%s'", host_cmnd, host_name
            )

            policy_key = ""
            available_policy = []

            # Check if host supports power system capability
            if not hasattr(vm_host.config, 'powerSystemCapability') or not vm_host.config.powerSystemCapability:
                _LOGGER.warning("Host '%s' does not support power policy configuration", host_name)
                continue

            for policy in vm_host.config.powerSystemCapability.availablePolicy:
                available_policy.append(policy.shortName)
                if policy.shortName == host_cmnd:
                    policy_key = policy.key

            if host_cmnd in available_policy:
                vm_host.configManager.powerSystem.ConfigurePowerPolicy(policy_key)
                _LOGGER.info("Power policy '%s' applied to host '%s'", host_cmnd, host_name)
            else:
                _LOGGER.warning(
                    "Power policy '%s' not available on host '%s'. Available policies: %s",
                    host_cmnd, host_name, available_policy
                )

    except vmodl.MethodFault as error:
        _LOGGER.error("VMware method fault: %s", error.msg)
        return False
    except vmodl.HostConfigFault as error:
        _LOGGER.error("Host configuration fault: %s", str(error))
        return False
    except vmodl.RuntimeFault as error:
        _LOGGER.error("VMware runtime fault: %s", error.msg)
        return False
    except Exception as error:  # pylint: disable=broad-except
        _LOGGER.error("Unexpected error during power policy configuration: %s", str(error))
        return False
    finally:
        esx_disconnect(conn)

    return True


def vm_pwr(
    hass, target_host, target_vm, target_vm_uuid, target_cmnd, conn_details, notify
):
    """VM power commands."""
    conn = esx_connect(**conn_details)
    if not conn:
        _LOGGER.error("Failed to connect to %s", conn_details.get('host', 'host'))
        return False

    content = conn.RetrieveContent()
    obj_view = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True
    )
    data = obj_view.view
    obj_view.Destroy()

    try:
        for vm in [vm for vm in data if vm.summary.config.uuid in target_vm_uuid]:
            _LOGGER.info("Sending '%s' command to vm '%s'", target_cmnd, vm.name)

            if vm.name == target_vm:
                _LOGGER.debug(
                    "Provided name %s (UUID %s) matches name on target",
                    target_vm,
                    target_vm_uuid,
                )
            else:
                _LOGGER.debug(
                    "Provided name %s (UUID %s) does notmatch name on target",
                    target_vm,
                    target_vm_uuid,
                )

            # generate task based on requested command
            if target_cmnd == "on":
                task = vm.PowerOnVM_Task()
            elif target_cmnd == "off":
                task = vm.PowerOffVM_Task()
            elif target_cmnd == "suspend":
                task = vm.SuspendVM_Task()
            elif target_cmnd == "reset":
                task = vm.ResetVM_Task()
            elif target_cmnd == "reboot":
                task = vm.RebootGuest()
            elif target_cmnd == "shutdown":
                task = vm.ShutdownGuest()

            # while task is running, check status
            # some tasks are fire and forget, no status will be provided
            if task:
                message = "power " + target_cmnd + " on " + vm.name
                task_status(hass, task, message, notify)
            else:
                _LOGGER.info("'%s' task does not provide feedback", target_cmnd)

            break
        else:
            _LOGGER.info(
                "VM %s on host %s not found. Make sure the name is correct",
                target_vm,
                target_host,
            )
    except vmodl.MethodFault as error:
        _LOGGER.info(error.msg)
    except Exception as error:  # pylint: disable=broad-except
        _LOGGER.info(str(error))
    finally:
        esx_disconnect(conn)

    return True


def vm_snap_take(
    hass,
    target_host,
    target_vm,
    target_vm_uuid,
    snap_name,
    desc,
    memory,
    quiesce,
    conn_details,
    notify,
):
    """Take Snapshot commands."""
    conn = esx_connect(**conn_details)
    content = conn.RetrieveContent()
    obj_view = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True
    )
    data = obj_view.view
    obj_view.Destroy()

    try:
        for vm in [vm for vm in data if vm.summary.config.uuid in target_vm_uuid]:
            _LOGGER.info("Sending create snapshot command to vm '%s'", vm.name)

            if vm.name == target_vm:
                _LOGGER.debug(
                    "Provided name %s (UUID %s) matches name on target",
                    target_vm,
                    target_vm_uuid,
                )
            else:
                _LOGGER.debug(
                    "Provided name %s (UUID %s) does notmatch name on target",
                    target_vm,
                    target_vm_uuid,
                )
            task = vm.CreateSnapshot_Task(snap_name, desc, memory, quiesce)

            # while task is running, check status
            if task:
                message = "create snapshot on " + vm.name
                task_status(hass, task, message, notify)
            else:
                _LOGGER.info("Task does not provide feedback")

            break
        else:
            _LOGGER.info(
                "VM %s (UUID %s) on host %s not found. Make sure the name is correct",
                target_vm,
                target_vm_uuid,
                target_host,
            )
    except vmodl.MethodFault as error:
        _LOGGER.error("VMware method fault during snapshot creation: %s", error.msg)
        return False
    except Exception as error:  # pylint: disable=broad-except
        _LOGGER.error("Unexpected error during snapshot creation: %s", str(error))
        return False
    finally:
        esx_disconnect(conn)

    return True


def vm_snap_remove(
    hass, target_host, target_vm, target_vm_uuid, target_cmnd, conn_details, notify
):
    """Remove Snapshot commands."""
    conn = esx_connect(**conn_details)
    content = conn.RetrieveContent()
    obj_view = content.viewManager.CreateContainerView(
        content.rootFolder, [vim.VirtualMachine], True
    )
    data = obj_view.view
    obj_view.Destroy()

    try:
        for vm in [vm for vm in data if vm.summary.config.uuid in target_vm_uuid]:
            if vm.name == target_vm:
                _LOGGER.debug(
                    "Provided name %s (UUID %s) matches name on target",
                    target_vm,
                    target_vm_uuid,
                )
            else:
                _LOGGER.debug(
                    "Provided name %s (UUID %s) does notmatch name on target",
                    target_vm,
                    target_vm_uuid,
                )

            # if there are 0 snapshots, stop
            if vm.snapshot is None:
                _LOGGER.info("No snapshots to remove on %s", vm.name)
                break

            _LOGGER.info(
                "Sending remove '%s' snapshot command to vm '%s'", target_cmnd, vm.name
            )

            # get a list of all snapshots
            snapshots = list_snapshots(vm.snapshot.rootSnapshotList, True)

            # remove all snapshots
            if target_cmnd == "all":
                task = vm.RemoveAllSnapshots_Task()
            # remove first snapshot in a snapshot tree
            elif target_cmnd == "first":
                first_snap = snapshots[0].snapshot
                task = first_snap.RemoveSnapshot_Task(False)
            # remove last snapshot in a snapshot tree
            elif target_cmnd == "last":
                last_snap = snapshots[(len(snapshots) - 1)].snapshot
                task = last_snap.RemoveSnapshot_Task(False)

            # while task is running, check status
            if task:
                message = "remove " + target_cmnd + " snapshot(s) on " + vm.name
                task_status(hass, task, message, notify)
            else:
                _LOGGER.info("Task does not provide feedback")

            break
        else:
            _LOGGER.info(
                "VM %s on host %s not found. Make sure the name is correct",
                target_vm,
                target_host,
            )
    except vmodl.MethodFault as error:
        _LOGGER.info(error.msg)
    except Exception as error:  # pylint: disable=broad-except
        _LOGGER.info(str(error))
    finally:
        esx_disconnect(conn)

    return True


def task_status(hass, task, command, notify):
    """Check status of running task."""
    from time import sleep
    from homeassistant.components import persistent_notification

    # Wait while task is in progress
    state = vim.TaskInfo.State
    max_wait_time = 300  # 5 minutes timeout
    elapsed_time = 0

    while task.info.state not in [state.success, state.error] and elapsed_time < max_wait_time:
        if task.info.progress is not None:
            _LOGGER.debug(
                "Task %s progress %s%%", task.info.eventChainId, task.info.progress
            )

        sleep(2)
        elapsed_time += 2

    # Check for timeout
    if elapsed_time >= max_wait_time:
        _LOGGER.error("Task '%s' timed out after %d seconds", command, max_wait_time)
        message = f"Timeout - {command}\n\nTask did not complete within {max_wait_time} seconds"
        persistent_notification.create(hass, message, "ESXi Stats")
        return False

    # Output task status once complete
    if task.info.state == "success":
        _LOGGER.info("Task '%s' on '%s' completed successfully", command, task.info.entityName)
        message = "Complete - " + command
        if notify:
            persistent_notification.create(hass, message, "ESXi Stats")
        else:
            _LOGGER.debug("Not creating notification: notification flag is false")
        return True
    elif task.info.state == "error":
        _LOGGER.error("Task '%s' on '%s' failed: %s", command, task.info.entityName, task.info.error.msg)
        message = "Failed - " + command + "\n\n"
        message += task.info.error.msg
        persistent_notification.create(hass, message, "ESXi Stats")
        return False

    return False


def list_esxi_hosts(hass, conn_details):
    """List all ESXi hosts available in the environment (useful for vCenter)."""
    conn = esx_connect(**conn_details)
    if not conn:
        _LOGGER.error("Failed to connect to %s", conn_details.get('host', 'host'))
        return

    try:
        content = conn.RetrieveContent()
        obj_view = content.viewManager.CreateContainerView(
            content.rootFolder, [vim.HostSystem], True
        )
        esxi_hosts = obj_view.view
        obj_view.Destroy()

        if not esxi_hosts:
            _LOGGER.info("No ESXi hosts found")
            return

        _LOGGER.info("Found %d ESXi host(s):", len(esxi_hosts))

        host_info = []
        for host in esxi_hosts:
            host_name = host.summary.config.name
            connection_state = host.runtime.connectionState
            power_state = host.runtime.powerState
            maintenance_mode = host.runtime.inMaintenanceMode
            vm_count = len([vm for vm in host.vm if vm.runtime.powerState == "poweredOn"])

            info = (
                f"  - Name: {host_name}, "
                f"Connection: {connection_state}, "
                f"Power: {power_state}, "
                f"Maintenance: {maintenance_mode}, "
                f"Running VMs: {vm_count}"
            )
            host_info.append(info)
            _LOGGER.info(info)

        # Create a persistent notification for easy viewing
        try:
            from homeassistant.components import persistent_notification
            notification_message = (
                f"ESXi Hosts in {conn_details['host']}:\n\n" +
                "\n".join([info.replace("  - ", "") for info in host_info]) +
                "\n\nUse the 'Name' field as the target_host parameter for host power commands."
            )
            persistent_notification.create(
                hass,
                notification_message,
                title="ESXi Hosts List",
                notification_id="esxi_stats_hosts_list"
            )
        except Exception as e:
            _LOGGER.debug("Could not create persistent notification: %s", e)

    except Exception as error:  # pylint: disable=broad-except
        _LOGGER.error("Failed to list ESXi hosts: %s", error)
    finally:
        esx_disconnect(conn)


def list_power_policies(hass, target_host_name, conn_details):
    """List available power policies for a specific host."""
    conn = esx_connect(**conn_details)
    if not conn:
        _LOGGER.error("Failed to connect to %s", conn_details.get('host', 'host'))
        return

    try:
        content = conn.RetrieveContent()
        obj_view = content.viewManager.CreateContainerView(
            content.rootFolder, [vim.HostSystem], True
        )
        esxi_hosts = obj_view.view
        obj_view.Destroy()

        # Find the target host
        target_host = None
        if len(esxi_hosts) == 1:
            # Single ESXi host scenario
            if target_host_name:
                # Verify the target host name matches
                host = esxi_hosts[0]
                if (host.summary.config.name.lower() == target_host_name.lower() or
                    host.name.lower() == target_host_name.lower()):
                    target_host = host
                else:
                    _LOGGER.error(
                        "Target host '%s' does not match available host '%s'",
                        target_host_name, host.summary.config.name
                    )
                    return
            else:
                # No target specified, use the single available host
                target_host = esxi_hosts[0]
                _LOGGER.info("No target host specified, using single available host")

        elif len(esxi_hosts) > 1:
            # vCenter with multiple hosts scenario
            if not target_host_name:
                # List available hosts for user reference
                available_hosts = [host.summary.config.name for host in esxi_hosts]
                _LOGGER.error(
                    "Multiple hosts found in vCenter. You must specify target_host. "
                    "Available hosts: %s", ", ".join(available_hosts)
                )
                return
            else:
                # Find the specified target host
                for host in esxi_hosts:
                    if (host.summary.config.name.lower() == target_host_name.lower() or
                        host.name.lower() == target_host_name.lower()):
                        target_host = host
                        break

                if not target_host:
                    available_hosts = [host.summary.config.name for host in esxi_hosts]
                    _LOGGER.error(
                        "Target host '%s' not found. Available hosts: %s",
                        target_host_name, ", ".join(available_hosts)
                    )
                    return
        else:
            # No hosts found
            _LOGGER.error("No ESXi hosts found")
            return

        # Get power policies for the target host
        host_name = target_host.summary.config.name

        # Check if host supports power system capability
        if not hasattr(target_host.config, 'powerSystemCapability') or not target_host.config.powerSystemCapability:
            _LOGGER.warning("Host '%s' does not support power policy configuration", host_name)
            try:
                from homeassistant.components import persistent_notification
                notification_message = f"Host '{host_name}' does not support power policy configuration"
                persistent_notification.create(
                    hass,
                    notification_message,
                    title="Power Policies Not Supported",
                    notification_id="esxi_stats_power_policies_not_supported"
                )
            except Exception as e:
                _LOGGER.debug("Could not create persistent notification: %s", e)
            return

        # Get available policies and current policy
        available_policies = []
        current_policy = None

        try:
            current_policy = target_host.config.powerSystemInfo.currentPolicy.shortName
        except Exception as e:
            _LOGGER.debug("Could not get current power policy: %s", e)
            current_policy = "Unknown"

        for policy in target_host.config.powerSystemCapability.availablePolicy:
            policy_info = {
                'short_name': policy.shortName,
                'full_name': policy.fullName,
                'description': getattr(policy, 'description', 'No description available'),
                'is_current': policy.shortName == current_policy
            }
            available_policies.append(policy_info)

        _LOGGER.info("Found %d power policies for host '%s':", len(available_policies), host_name)

        policy_details = []
        for policy in available_policies:
            current_marker = " (CURRENT)" if policy['is_current'] else ""
            detail = (
                f"  - {policy['short_name']}{current_marker}\n"
                f"    Full Name: {policy['full_name']}\n"
                f"    Description: {policy['description']}"
            )
            policy_details.append(detail)
            _LOGGER.info(detail.replace("    ", ""))

        # Create a persistent notification for easy viewing
        try:
            from homeassistant.components import persistent_notification
            notification_message = (
                f"Power Policies for {host_name}:\n\n" +
                "\n\n".join(policy_details) +
                f"\n\nCurrent Policy: {current_policy}\n\n" +
                "Use the 'short_name' values (like 'static', 'dynamic', 'low') as the 'command' parameter in the host_power_policy service."
            )
            persistent_notification.create(
                hass,
                notification_message,
                title="ESXi Power Policies",
                notification_id="esxi_stats_power_policies"
            )
        except Exception as e:
            _LOGGER.debug("Could not create persistent notification: %s", e)

    except Exception as error:  # pylint: disable=broad-except
        _LOGGER.error("Failed to list power policies: %s", error)
    finally:
        esx_disconnect(conn)
