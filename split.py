import ipaddress
import argparse
import re

def validate_cidr(ip_network):
    # Regex pattern for CIDR
    pattern = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)/(?:[0-2]?[0-9]|3[0-2])$"
    return re.match(pattern, ip_network) is not None

def validate_mask(new_prefix, old_prefix):
    # Check if new prefix is a number between 0 and 32 and is greater than the old prefix
    if not isinstance(new_prefix, int) or new_prefix < 0 or new_prefix > 32 or new_prefix <= old_prefix:
        return False
    return True

def split_cidr(ip_network, new_prefix):
    if not validate_cidr(ip_network):
        print("Error: Invalid CIDR notation.")
        return None
    try:
        ip_network_obj = ipaddress.ip_network(ip_network)
        old_prefix = ip_network_obj.prefixlen
        if not validate_mask(new_prefix, old_prefix):
            print("Error: Invalid subnet mask.")
            return None
        subnets = list(ip_network_obj.subnets(new_prefix=new_prefix))
        return [str(subnet) for subnet in subnets]
    except ValueError as e:
        print(f"Error: {e}")
        return None
