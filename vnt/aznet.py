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

    # Get the VNet's subnets
    vnet_subnets = network_client.subnets.list(resource_group_name, vnet_name)

    # Split each address space and collect the results
    result = []
    for ip_network in vnet_address_space:
        subnet_result = split_cidr(ip_network, new_prefix)
        if subnet_result is not None and len(subnet_result) > 0:
            result.extend(subnet_result)

    # Check existing subnets and remove from result
    for subnet in vnet_subnets:
        if subnet.address_prefix in result:
            print("Already existing subnet: {}".format(subnet.address_prefix))
            result.remove(subnet.address_prefix)

    # Create new subnets
    for subnet in result:
        print("Creating subnet: {}".format(subnet))
        subnet_mask = subnet.split("/")[1]
        subnet_name = "unused-" + subnet_mask + "-" + hashlib.md5(subnet.encode("utf-8")).hexdigest()
        network_client.subnets.begin_create_or_update(
            resource_group_name,
            vnet_name,
            subnet_name,
            {
                "address_prefix": subnet
            }
        ).wait()

    return result

def generate_csv_report(vnet_id, output_file_path):
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

    # Get the VNet's subnets
    vnet_subnets = network_client.subnets.list(resource_group_name, vnet_name)

    # Print the subnets in CSV format
    result = "Name,Address Prefix,Network Security Group,Route Table,Service Endpoints,Delegation,Private Endpoint\n"
    for subnet in vnet_subnets:
        subnet_name = subnet.name
        subnet_address_prefix = subnet.address_prefix
        subnet_nsg = subnet.network_security_group.id if subnet.network_security_group else ""
        subnet_route_table = subnet.route_table.id if subnet.route_table else ""
        subnet_service_endpoints = ",".join(subnet.service_endpoints) if subnet.service_endpoints else ""
        subnet_delegation = ",".join([delegation.service_name + ":" + delegation.name for delegation in subnet.delegations]) if subnet.delegations else ""
        subnet_private_endpoint = ",".join([private_endpoint.id for private_endpoint in subnet.private_endpoints]) if subnet.private_endpoints else ""
        result += "{},{},{},{},{},{},{}\n".format(
            subnet_name,
            subnet_address_prefix,
            subnet_nsg,
            subnet_route_table,
            subnet_service_endpoints,
            subnet_delegation,
            subnet_private_endpoint
        )
    
    # Write the result to the output file
    if output_file_path:
        with open(output_file_path, "w") as output_file:
            output_file.write(result)
    else:
        return result

def main():

    parser = argparse.ArgumentParser(description='A CLI for managing VNets.')
    subparsers = parser.add_subparsers(dest='command', help='The command to execute.')

    # Split command
    split_parser = subparsers.add_parser('split', help='Split a VNet\'s address space into smaller subnets.')
    split_parser.add_argument('vnet_id', type=str, help='The resource ID of the VNet.')
    split_parser.add_argument('new_prefix', type=int, help='The new prefix length.')

    # Print command. Return VNet's subnet list inc CSV format
    print_parser = subparsers.add_parser('print', help='Print a VNet\'s subnet list.')
    print_parser.add_argument('vnet_id', type=str, help='The resource ID of the VNet.')
    print_parser.add_argument('--output', type=str, help='The output file path.')

    args = parser.parse_args()

    if args.command == 'split':
        result = split_vnet(args.vnet_id, args.new_prefix)
    elif args.command == 'print':
        result = generate_csv_report(args.vnet_id, args.output)
    else:
        parser.print_help()
        return
    print(result)


if __name__ == "__main__":
    main()