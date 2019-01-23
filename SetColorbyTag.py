#
# ping_hosts.py
# version 1.1
#
# Purpose: Set Check Point host objects color and tag
# Author: Joshua J. Smith (JJSYNC)
# October 2018

# A package for reading passwords without displaying them on the console.
from __future__ import print_function
import getpass
import sys
import os
import csv
import collections
import argparse
import ipaddress
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# lib is a library that handles the communication with the Check Point management server.
from lib import APIClient, APIClientArgs


def change_host_color_tag(api_client, tag_name, show_hosts_res):
    for cpobject in show_hosts_res.data:
        cpname = cpobject.get("name")
        tags = cpobject.get("tags")
        ip = ipaddress.ip_address(unicode(cpobject.get("ipv4-address")))
        for tag in tags:
            if tag.get("name") == tag_name and ip.is_private:
                host_change_color_res = api_client.api_call("set-host",
                                                            payload={"name": cpname, "color": "forest green"})
                if host_change_color_res.success is False:
                    print("Failed to set host color: {}".format(host_change_color_res.error_message))
                    exit(1)

def change_net_color_tag():
    pass

def main(argv):
    """
    Function to pull all host info from check point management server.
    :param argv: optional arguments to run script without need of user input
    :return: None - outputs csv file
    """

    if argv:
        parser = argparse.ArgumentParser(description="Ping IP address of host objects and outputs to csv file")
        parser.add_argument("-s", type=str, action="store", help="API Server IP address or hostname", dest="api_server")
        parser.add_argument("-u", type=str, action="store", help="User name", dest="username")
        parser.add_argument("-p", type=str, action="store", help="Password", dest="password")

        args = parser.parse_args()

        required = "api_server username password".split()
        for r in required:
            if args.__dict__[r] is None:
                parser.error("parameter '%s' required" % r)

        api_server = args.api_server
        username = args.username
        password = args.password

    else:
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
        print("Gathering all objects\nProcessing. Please wait...")
        show_hosts_res = client.api_query("show-hosts", "full")
        if show_hosts_res.success is False:
            print("Failed to get the list of all host objects: {}".format(show_hosts_res.error_message))
            exit(1)

        print(type(show_hosts_res))
        print(type(show_hosts_res.data))
        # obj_dictionary - for a given IP address, get an array of hosts (name) that use this IP address.
        obj_dictionary = {}

        change_host_color_tag(client, "CiscoASA", show_hosts_res)

        print("DONE")







if __name__ == "__main__":
    main(sys.argv[1:])
