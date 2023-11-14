import argparse
import re
import hashlib
from azure.identity import DefaultAzureCredential
from azure.mgmt.network import NetworkManagementClient
from split import split_cidr

def get_subscription_id(vnet_id):
    match = re.search(r"/subscriptions/(.*?)/", vnet_id)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid VNet resource ID.")

def validate_vnet_id(vnet_id):
    pattern = r"^/subscriptions/.*/resourcegroups/.*/providers/microsoft.network/virtualnetworks/.*$"
    if not re.match(pattern, vnet_id.lower()):
        raise ValueError("Invalid VNet resource ID.")
    
def get_resource_group_name(vnet_id):
    vnet_id = vnet_id.lower()
    match = re.search(r"/resourcegroups/(.*?)/", vnet_id)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid VNet resource ID.")

def get_vnet_name(vnet_id):
    vnet_id = vnet_id.lower()
    match = re.search(r"/virtualnetworks/(.*)", vnet_id)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid VNet resource ID.")
    
def split_vnet(vnet_id, new_prefix):
    # Validate the VNet resource ID
    validate_vnet_id(vnet_id)

    # Extract the subscription ID, resource group name, and VNet name from the VNet resource ID
    subscription_id = get_subscription_id(vnet_id)
    resource_group_name = get_resource_group_name(vnet_id)
    vnet_name = get_vnet_name(vnet_id)

    # Authenticate with DefaultAzureCredential
    credential = DefaultAzureCredential()

    # Create a NetworkManagementClient
    network_client = NetworkManagementClient(credential, subscription_id)

    # Get the VNet
    vnet = network_client.virtual_networks.get(resource_group_name, vnet_name)

    # Get the VNet's address space
    vnet_address_space = vnet.address_space.address_prefixes

    # Split each address space and collect the results
    result = []
    for ip_network in vnet_address_space:
        subnet_result = split_cidr(ip_network, new_prefix)
        if subnet_result is not None:
            result.extend(subnet_result)

    # Create new subnets
    for subnet in result:
        print("Creating subnet: {}".format(subnet))
        subnet_name = "unused-" + hashlib.md5(subnet.encode("utf-8")).hexdigest()
        network_client.subnets.begin_create_or_update(
            resource_group_name,
            vnet_name,
            subnet_name,
            {
                "address_prefix": subnet
            }
        ).wait()

    return result

def main():

    parser = argparse.ArgumentParser(description='A CLI for managing VNets.')
    subparsers = parser.add_subparsers(dest='command', help='The command to execute.')

    # Split command
    split_parser = subparsers.add_parser('split', help='Split a VNet\'s address space into smaller subnets.')
    split_parser.add_argument('vnet_id', type=str, help='The resource ID of the VNet.')
    split_parser.add_argument('new_prefix', type=int, help='The new prefix length.')

    args = parser.parse_args()

    if args.command == 'split':
        result = split_vnet(args.vnet_id, args.new_prefix)
        print(result)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()