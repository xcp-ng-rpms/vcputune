#!/usr/bin/python3
#
# Copyright (C) 2013 Citrix Ltd.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published
# by the Free Software Foundation; version 2.1 only.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# host-cpu-tune: script to show, advise and set dom0 vcpu count and
#                host pinning strategy

import sys
import subprocess
import xcp.environ
import xcp.cmd
import xcp.logger
import xcp.dom0
from functools import reduce

# Absolute paths
xl            = "/usr/sbin/xl"
xenpm         = "/usr/sbin/xenpm"
xe            = "/opt/xensource/bin/xe"
xencmd        = "/opt/xensource/libexec/xen-cmdline"

# Helper function to interface with xcp.cmd.runCmd()
def call(c, exOnErr=True):
    rv, out, err = xcp.cmd.runCmd(c, with_stdout=True, with_stderr=True)
    if exOnErr and (rv!=0 or len(err))>0:
        msg="cmd=%s: rv=%s, stderr=%s" % (c,rv,err)
        raise RuntimeError(msg)
    return out.splitlines()

# Helper function to interface with xcp.environ.readInventory()
def get_host_uuid():
    try:
        return xcp.environ.readInventory()['INSTALLATION_UUID']
    except Exception:
        raise RuntimeError("INSTALLATION_UUID missing from inventory")

# Helper function to interface with xcp.environ.readInventory()
def get_dom0_uuid():
    try:
        return xcp.environ.readInventory()['CONTROL_DOMAIN_UUID']
    except Exception:
        raise RuntimeError("CONTROL_DOMAIN_UUID missing from inventory")

# Shows current running configuration
def show():
    # Fetch list of vcpus associated with Domain-0.
    xl_vcpulist = call([xl, "vcpu-list", "0"])[1:]

    # Generate a list of "vcpu, pcpu affinity" for each vCPU
    dom0_vcpus = [ [ x.split()[2], x.split()[6] ] for x in xl_vcpulist ]

    # Check if all vCPUs are pinned to the corresponding pCPU
    pinned = True
    for vcpu in dom0_vcpus:
        if vcpu[1] == 'all':
            pinned = False
            break

    # Query XAPI for VM vCPU affinity
    host_uuid = get_host_uuid()
    mask = call([xe, "host-param-get", "uuid=%s" % (host_uuid,), "param-name=guest_VCPUs_params", "param-key=mask"], exOnErr=False)
    xpinned = False
    if mask:
        xpinned = True

    # Print current vCPU count and pinning strategy
    pin_str = "not pinned"
    if pinned:
        if xpinned:
            pin_str = "exclusively pinned"
        else:
            pin_str = "pinned"

    print("dom0's vCPU count: %d, %s" % (len(dom0_vcpus), pin_str))

# Helper function to get number of host pCPUs
def get_nr_pcpus():
    # Get hosts's pCPUs from 'xl info'
    try:
        lines = call([xl, "info"])
        return int([line for line in lines if line.startswith("nr_cpus")][0].split(':')[1])
    except Exception:
        raise RuntimeError("no nr_cpus in xl info output.")

# Helper function to get amount of static-max memory in MB
def get_static_max_mb():
    dom0_uuid = get_dom0_uuid()
    mem_bytes = call([xe, "vm-list", "uuid=%s" % (dom0_uuid,), "params=memory-static-max", "--minimal"], exOnErr=False);
    if len(mem_bytes):
        return int(mem_bytes[0]) / 1024 / 1024
    else:
        return None

# Helper function to create a recommendation
def get_advise():
    # Use the same algorithm as the host-installer to determine the number of dom0 vCPUs.
    #  num of pCPUs <  48 ===> no   pinning
    #               >= 48 ===> excl pinning
    #

    # Get host's pCPUs
    nr_pcpus = get_nr_pcpus()

    recom_vcpu = xcp.dom0.default_vcpus(nr_pcpus, get_static_max_mb())
    recom_xpin = (nr_pcpus >= 48)

    return (recom_vcpu, recom_xpin)

# Function to print our recommendation for this host
def advise():
    # Fetch recommendations
    recom_vcpu, recom_xpin = get_advise()

    # Print recommendations
    if recom_xpin:
        pin_str = "using exclusive pinning"
        pin_cmd = "xpin"
    else:
        pin_str = "not using pinning"
        pin_cmd = "nopin"

    print("It is recommended to assign %d vCPUs to dom0, %s." % (recom_vcpu, pin_str))
    print("This can be achieved by running:\n")
    print("%s set %d %s\n" % (sys.argv[0], recom_vcpu, pin_cmd))

# Function to set a new host configuration
def cpuset(dom0_vcpus, typePin, forcePin=False):

    # Assume no conflict in pCPUs pinned to dom0 and specific VM affinity settings
    pin_conflict = False

    # Get host's pCPUs
    nr_pcpus = get_nr_pcpus()

    # Validate dom0_vcpus parameter
    if dom0_vcpus <= 0:
        print("ERROR: parameter 'dom0_vcpus' must be greater than zero.")
        return
    elif dom0_vcpus > nr_pcpus:
        print("ERROR: this host only has %d pCPUs. Cannot give dom0 %d vCPUs." % (nr_pcpus, dom0_vcpus))
        return

    # Validate pinning parameter
    if typePin != "nopin" and typePin != "xpin":
        print("ERROR: parameter 'pinning' must be set to 'nopin' or 'xpin'")
        return
    if typePin == "xpin" and dom0_vcpus >= nr_pcpus:
        print("ERROR: cannot exclusively pin %d vCPUs to dom0. No vCPUs will be available to other guests." % (dom0_vcpus,))
        return

    # Verify that this setting will not conflict with VMs in this pool
    if typePin == "xpin":
        # Fetch list of VMs from pool
        vms = call([xe, "vm-list", "--minimal", "is-control-domain=false"])
        if len(vms):
            vms = vms[0].split(',')

        # Evaluate each VM
        for vm in vms:
            vm_aff_s = call([xe, "vm-param-get", "uuid=%s" % (vm,), "param-name=VCPUs-params", "param-key=mask"], exOnErr=False)
            vm_aff_l = []
            if len(vm_aff_s):
                vm_aff_l = vm_aff_s[0].split(',')

            # Evaluate each VM's affinity
            warn_flag = False
            for vm_pcpu in vm_aff_l:
                if int(vm_pcpu) < dom0_vcpus:
                    if warn_flag == False:
                        print("ERROR: VM '%s' is pinned to pCPUs %s." % (vm, vm_aff_s[0]))
                        warn_flag = True
                        pin_conflict = True
                    print("       pCPU '%s' is being exclusively pinned to dom0." % (vm_pcpu,))
            if warn_flag:
                print("       PLEASE REVIEW THE MANUAL PINNING OF THIS VM.")
                print("       IT MIGHT FAIL TO START ON, RESUME ON OR MIGRATE TO THIS HOST.\n")

    # In pinning conflict cases, only go further if user is forcing
    if pin_conflict and forcePin == False:
        print("No configuration changes were made due to the errors above.")
        print("Please verify the VCPUs-params:mask of the conflicting VMs.")
        print("If you understand the implications of these errors, you may call this program again with '--force'.")
        return

    # Set dom0 vCPU count
    call([xencmd, "--set-xen", "dom0_max_vcpus=1-%d" % (dom0_vcpus,)])

    # Set pinning
    host_uuid = get_host_uuid()
    call([xencmd, "--delete-xen", "dom0_vcpus_pin"])
    call([xe, "host-param-remove", "uuid=%s" % (host_uuid,), "param-name=guest_VCPUs_params", "param-key=mask"], exOnErr=False)
    if typePin == "xpin":
        # Create list with VM's pCPUs
        vms_pcpus = list(range(dom0_vcpus, nr_pcpus))
        vms_str   = reduce(lambda a,x: (str(x), a+","+str(x))[a!=""], vms_pcpus, "")

        # Set XAPI VM vCPU affinity
        call([xe, "host-param-set", "uuid=%s" % (host_uuid,), "guest_VCPUs_params:mask=%s" % (vms_str,)])

        # Set xen command line dom0 pinning
        call([xencmd, "--set-xen", "dom0_vcpus_pin"])

    # Print final message
    print("Configuration successfully applied.")
    print("Reboot this host NOW.")

def reset():
    # Fetch defaults
    recom_vcpu, recom_xpin = get_advise()

    # Apply defaults without pinning
    cpuset(recom_vcpu, "nopin")

# Function to print help
def usage():
    print("Usage: %s { show | advise | set <dom0_vcpus> <pinning> [--force] }" % (sys.argv[0],))
    print("         show     Shows current running configuration")
    print("         advise   Advise on a configuration for current host")
    print("         reset    Reset host's configuration to default strategy")
    print("         set      Set host's configuration for next reboot")
    print("          <dom0_vcpus> specifies how many vCPUs to give dom0")
    print("          <pinning>    specifies the host's pinning strategy")
    print("                       allowed values are 'nopin' or 'xpin'")
    print("          [--force]    forces xpin even if VMs conflict\n")
    print("Examples: %s show" % (sys.argv[0],))
    print("          %s advise" % (sys.argv[0],))
    print("          %s set 4 nopin" % (sys.argv[0],))
    print("          %s set 8 xpin" % (sys.argv[0],))
    print("          %s set 8 xpin --force" % (sys.argv[0],))

# Main function that parses parameters
def main():
    xcp.logger.logToSyslog()
    if len(sys.argv) > 1:
        if sys.argv[1] == "show":
            show()
        elif sys.argv[1] == "advise":
            advise()
        elif sys.argv[1] == "reset":
            reset()
        elif sys.argv[1] == "set":
            if len(sys.argv) == 4:
                try:
                    dom0_vcpus = int(sys.argv[2])
                except ValueError:
                    print("ERROR: parameter 'dom0_vcpus' must be an integer, not: '%s'" % (sys.argv[2],))
                    return
                cpuset(dom0_vcpus, sys.argv[3])
            elif len(sys.argv) == 5 and sys.argv[4] == "--force":
                cpuset(dom0_vcpus, sys.argv[3], True)
            else:
                usage()
        else:
            usage()
    else:
        usage()

# Program entry point
if __name__ == "__main__":
    main()
