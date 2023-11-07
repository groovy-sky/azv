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

def split_cidr(ip_network, new_prefix, verbose=False):
    if not validate_cidr(ip_network):
        if verbose:
            print("Error: Invalid CIDR notation.")
        return None
    try:
        ip_network_obj = ipaddress.ip_network(ip_network)
        old_prefix = ip_network_obj.prefixlen
        if not validate_mask(new_prefix, old_prefix):
            if verbose:
                print("Error: Invalid subnet mask.")
            return None
        subnets = list(ip_network_obj.subnets(new_prefix=new_prefix))
        return [str(subnet) for subnet in subnets]
    except ValueError as e:
        if verbose:
            print(f"Error: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Split a CIDR block into smaller subnets.')
    parser.add_argument('ip_network', type=str, help='The IP network in CIDR format.')
    parser.add_argument('new_prefix', type=int, help='The new prefix length.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output.')
    args = parser.parse_args()

    result = split_cidr(args.ip_network, args.new_prefix, verbose=args.verbose)
    if result is not None:
        print(result)

if __name__ == "__main__":
    main()