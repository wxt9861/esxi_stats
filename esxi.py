from __future__ import print_function
import atexit
from pyVim.connect import SmartConnectNoSSL, Disconnect
from pyVmomi import vim
from .tools import cli

MAX_DEPTH = 10

def setup_args():

    """
    Get standard connection arguments
    """
    #parser = cli.build_arg_parser()
    #my_args = parser.parse_args()

    #return cli.prompt_for_password(my_args)

def printvminfo(vm, depth=1):
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
            printvminfo(child, depth+1)
        return

    summary = vm.summary
    print(summary.config.name)

def main(host,user,password):
    """
    Simple command-line program for listing the virtual machines on a host.
    """

    #args = setup_args()
    si = None
    try:
        si = SmartConnectNoSSL(host=host,
                               user=user,
                               pwd=password,
                               port=int(443))
        atexit.register(Disconnect, si)
    except vim.fault.InvalidLogin:
        raise SystemExit("Unable to connect to host "
                         "with supplied credentials.")

    content = si.RetrieveContent()
    for child in content.rootFolder.childEntity:
        if hasattr(child, 'vmFolder'):
            datacenter = child
            vmfolder = datacenter.vmFolder
            vmlist = vmfolder.childEntity
            for vm in vmlist:
                printvminfo(vm)

# Start program
#if __name__ == "__main__":
#    main()