#
# ping_hosts.py
# version 1.1
#
# Pings IP address of all Check Point host objects
# Author: JJSYNC
# October 2018

# A package for reading passwords without displaying them on the console.
from __future__ import print_function
import getpass
import sys
import os
import csv
import collections
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# lib is a library that handles the communication with the Check Point management server.
from lib import APIClient, APIClientArgs, Pinger


def main():
    # getting details from the user
    api_server = raw_input("Enter server IP address or hostname:")
    username = raw_input("Enter username: ")
    if sys.stdin.isatty():
        password = getpass.getpass("Enter password: ")
    else:
        print("Attention! Your password will be shown on the screen!")
        password = raw_input("Enter password: ")

    client_args = APIClientArgs(server=api_server)

    with APIClient(client_args) as client:

        # create debug file. The debug file will hold all the communication between the python script and
        # Check Point's management server.
        client.debug_file = "api_calls.json"

        # The API client, would look for the server's certificate SHA1 fingerprint in a file.
        # If the fingerprint is not found on the file, it will ask the user if he accepts the server's fingerprint.
        # In case the user does not accept the fingerprint, exit the program.
        if client.check_fingerprint() is False:
            print("Could not get the server's fingerprint - Check connectivity with the server.")
            exit(1)

        # login to server:
        login_res = client.login(username, password)

        if login_res.success is False:
            print("Login failed: {}".format(login_res.error_message))
            exit(1)

        # show hosts
        print("Processing. Please wait...")
        show_hosts_res = client.api_query("show-hosts", "standard")
        if show_hosts_res.success is False:
            print("Failed to get the list of all host objects: {}".format(show_hosts_res.error_message))
            exit(1)

    # obj_dictionary - for a given IP address, get an array of hosts (name) that use this IP address.
    obj_dictionary = {}

    # iterates through hosts creating dictionary of key: IP value: host name
    for host in show_hosts_res.data:
        ipaddr = host.get("ipv4-address")
        if ipaddr is None:
            print(host["name"] + " has no IPv4 address. Skipping...")
            continue
        host_data = {"name": host["name"]}
        obj_dictionary[ipaddr] = host_data

    # build IP array from passed dictionary
    ips = obj_dictionary.keys()

    # Calls Pinger class with number of threads and ip list
    ping = Pinger(32, ips)
    # starts ping test of IP addresses
    queue_list = ping.start_ping()

    # Updates dictionary in place with status of ping results
    for i in queue_list:
        if i is None:
            continue
        else:
            obj_dictionary[i[0]]['status'] = i[1]

    od_obj_dictionary = collections.OrderedDict(sorted(obj_dictionary.items()))

    ips_dict = []

    for item in od_obj_dictionary:
        sub_item = list()
        sub_item.append(item)
        for key, value in od_obj_dictionary[item].iteritems():
            sub_item.append(value)
        ips_dict.append(sub_item)

    with open("output.csv", "wb") as f:
        writer = csv.writer(f)
        writer.writerows(ips_dict)


if __name__ == "__main__":
    main()
