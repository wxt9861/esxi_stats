from __future__ import print_function
import atexit
from pyVim.connect import SmartConnect, SmartConnectNoSSL, Disconnect
from pyVmomi import vim  # pylint: disable=no-name-in-module

# from .tools import cli


def get_content(host, user, pwd, port, ssl):
    si = None

    # connect depending on SSL_VERIFY setting
    if ssl == False:
        si = SmartConnectNoSSL(host=host, user=user, pwd=pwd, port=port)
    else:
        si = SmartConnect(host=host, user=user, pwd=pwd, port=port)

    atexit.register(Disconnect, si)

    return si.RetrieveContent()


def get_host_info(host):
    host_summary = host.summary
    host_name = host_summary.config.name.replace(" ", "_").lower()
    host_version = host_summary.config.product.version
    host_uptime = round(host_summary.quickStats.uptime / 3600, 1)
    host_cpu_total = round(
        host_summary.hardware.cpuMhz * host_summary.hardware.numCpuCores / 1000, 1
    )
    host_mem_total = round(host_summary.hardware.memorySize / 1073741824, 2)
    host_cpu_usage = round(host_summary.quickStats.overallCpuUsage / 1000, 1)
    host_mem_usage = round(host_summary.quickStats.overallMemoryUsage / 1024, 2)

    host_data = {
        "name": host_name,
        "version": host_version,
        "uptime_hours": host_uptime,
        "cputotal_ghz": host_cpu_total,
        "cpuusage_ghz": host_cpu_usage,
        "memtotal_gb": host_mem_total,
        "memusage_gb": host_mem_usage,
    }

    return host_data


def get_datastore_info(ds):
    ds_summary = ds.summary
    ds_name = ds_summary.name.replace(" ", "_").lower()
    ds_capacity = round(ds_summary.capacity / 1073741824, 2)
    ds_freespace = round(ds_summary.freeSpace / 1073741824, 2)
    ds_type = ds_summary.type.lower()

    ds_data = {
        "name": ds_name,
        "type": ds_type,
        "free_space_gb": ds_freespace,
        "total_space_gb": ds_capacity,
        "connected_hosts": len(ds.host),
        "virtual_machines": len(ds.vm),
    }

    return ds_data


def get_vm_info(vm):
    vm_sum = vm.summary
    vm_run = vm.runtime
    vm_name = vm_sum.config.name.replace(" ", "_").lower()
    vm_used_space = round(vm_sum.storage.committed / 1073741824, 2)
    vm_tools_status = vm_sum.guest.toolsStatus

    # set vm_state based on power state
    if vm_sum.runtime.powerState == "poweredOn":
        vm_state = "running"
    elif vm_sum.runtime.powerState == "poweredOff":
        vm_state = "off"
    elif vm_sum.runtime.powerState == "suspended":
        vm_state = "suspended"
    else:
        vm_state = vm_sum.runtime.powerState

    # set other attributes based on vm power state
    if vm_state == "running":
        vm_cpu_usage = round(
            ((vm_sum.quickStats.overallCpuUsage / vm_run.maxCpuUsage) * 100), 0
        )

        vm_mem_usage = round(vm_sum.quickStats.hostMemoryUsage, 2)
        vm_uptime = round(vm_sum.quickStats.uptimeSeconds / 3600, 1)
        vm_guest_os = vm_sum.guest.guestFullName
    else:
        vm_cpu_usage = "n/a"
        vm_mem_usage = "n/a"
        vm_uptime = "n/a"
        vm_guest_os = vm_sum.config.guestFullName

    vm_data = {
        "name": vm_name,
        "status": vm_sum.overallStatus,
        "state": vm_state,
        "uptime_hours": vm_uptime,
        "cpu_count": vm_sum.config.numCpu,
        "cpu_use_%": vm_cpu_usage,
        "memory_allocated_mb": vm_sum.config.memorySizeMB,
        "memory_used_gb": vm_mem_usage,
        "used_space_gb": vm_used_space,
        "tools_status": vm_tools_status,
        "guest_os": vm_guest_os,
    }

    return vm_data
