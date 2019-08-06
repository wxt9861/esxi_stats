from __future__ import print_function
import atexit
from pyVim.connect import SmartConnect, SmartConnectNoSSL, Disconnect
from pyVmomi import vim  # pylint: disable=no-name-in-module
from .tools import cli

MAX_DEPTH = 10

def get_content(host, user, pwd, port, ssl):
    si = None

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
        "virtual_machines": len(ds.vm)
    }

    #print(ds_data)
    return ds_data

def get_vm_info(vm):
    vm_summary = vm.summary
    vm_name = vm_summary.config.name.replace(" ", "_").lower()
    vm_data = {
        "vm_name": vm_name,
        "vm_status": vm_summary.overallStatus,
        "vm_state": vm_summary.runtime.powerState,
        "vm_cpu_count": vm_summary.config.numCpu,
        "vm_memory_mb": vm_summary.config.memorySizeMB,
    }

    return vm_data
