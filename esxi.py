from __future__ import print_function
import atexit
from pyVim.connect import SmartConnectNoSSL, Disconnect
from pyVmomi import vim #pylint: disable=no-name-in-module
from .tools import cli

MAX_DEPTH = 10

def get_content(host, user, pwd, port):
    si = None
    si = si = SmartConnectNoSSL(
        host=host,
        user=user,
        pwd=pwd,
        port=port)
    atexit.register(Disconnect, si)

    return si.RetrieveContent()

def get_host_info(host):
    host_summary = host.summary
    host_name = host_summary.config.name.replace(" ", "_").lower()
    host_version = host_summary.config.product.version
    host_uptime = round(host_summary.quickStats.uptime / 3600, 1)
    host_cpu_total = round(host_summary.hardware.cpuMhz *
                    host_summary.hardware.numCpuCores
                    / 1000, 1)
    host_mem_total = round(host_summary.hardware.memorySize / 1073741824, 2)
    host_cpu_usage = round(host_summary.quickStats.overallCpuUsage / 1000, 1)
    host_mem_usage = round(host_summary.quickStats.overallMemoryUsage / 1024, 2)

    host_data = {
        "hname": host_name,
        "hversion": host_version,
        "huptime": host_uptime,
        "hcputotal": host_cpu_total,
        "hcpuusage": host_cpu_usage,
        "hmemtotal": host_mem_total,
        "hmemusage": host_mem_usage
    }

    return host_data

def getvminfo(vm, depth=1):
    """
    Print information for a particular virtual machine or recurse into a folder
    with depth protection
    """
    # if this is a group it will have children. if it does, recurse into them
    # and then return
    if hasattr(vm, 'childEntity'):
        if depth > MAX_DEPTH:
            return
        vmlist = vm.childEntity
        for child in vmlist:
            getvminfo(child, depth+1)
        return

    #summary = vm.summary
    return(vm)

# Start program
#if __name__ == "__main__":
#    main()