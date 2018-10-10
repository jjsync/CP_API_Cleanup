#
# ping_hosts.py
# version 1.1
#
# Pings IP address of all Check Point host objects
# Author: JJSYNC
# October 2018

# A package for reading passwords without displaying them on the console.
from __future__ import print_function
from threading import Thread
import Queue
import subprocess
import platform
import getpass
import sys
import os
import csv
import collections
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# lib is a library that handles the communication with the Check Point management server.
from lib import APIClient, APIClientArgs


def determine_platform_arg():
    """
    Provides ping arguments based on platform of device executing program.
    Needed due to differences between OS ping options
    :return: list of ping with arguments
    """
    # Platform determination for ping command arguments
    plat = platform.system()
    if plat == 'Windows':
        ping_args = ["ping", "-n", "1", "-w", "1"]
    elif plat == 'Linux':
        ping_args = ["ping", "-c", "1", "-w", "1"]
    else:
        raise ValueError("Unknown platform")
    return ping_args


def thread_pinger(pingArgs, ips_q, out_q):
    """
    ping function wrapper for threads
    :param pingArgs: List of ping command with arguments
    :param ips_q: queue of ip addresses
    :param out_q: output queue to hold results
    :return:
    """
    try:
        while True:
            # get an IP item from queue
            address = ips_q.get_nowait()

            # ping IP address
            # os.devnull to send output to null
            with open(os.devnull, "wb") as limbo:
                result = subprocess.Popen(pingArgs + [address], stdout=limbo, stderr=limbo).wait()
                # add results to output queue
                if result:
                    out_q.put((address, "inactive"))
                else:
                    out_q.put((address, "active"))
    except Queue.Empty:
        # No more addresses.
        pass
    finally:
        out_q.put(None)


def ping_host_objects(number_of_thread, host_dictionary):
    """
    Thread function to ping list of IP addresses
    :param number_of_thread: number of worker threads to execute
    :param host_dictionary: dictionary with IP addresses as keys
    :return: output queue FIFO queue list
    """
    # Number of workers
    num_threads = number_of_thread

    # platform ping determination
    ping_args = determine_platform_arg()

    # The queue of addresses to ping
    ips_q = Queue.Queue()

    # The queue of results
    out_q = Queue.Queue()

    # build IP array from passed dictionary
    ips = host_dictionary.keys()

    # create the workers
    workers = []
    for i in range(num_threads):
        workers.append(Thread(target=thread_pinger, args=(ping_args, ips_q, out_q)))

    # put all of the IPs in the ips_q queue
    for ip in ips:
        ips_q.put(ip)

    # Start all the workers
    for w in workers:
        w.daemon = True
        w.start()

    # wait until worker threads are done to exit
    for w in workers:
        w.join()

    return out_q.queue


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

    # Send host object dictionary to ping thread returns result lists
    queue_list = ping_host_objects(32, obj_dictionary)

    # Updates dictionary in place with status of ping results
    for i in queue_list:
        if i is None:
            continue
        else:
            obj_dictionary[i[0]]['status'] = i[1]

    od_obj_dictionary = collections.OrderedDict(sorted(obj_dictionary.items()))

    ips_dict = []

    for item in od_obj_dictionary:
        sub_item = []
        sub_item.append(item)
        for key, value in od_obj_dictionary[item].iteritems():
            sub_item.append(value)
        ips_dict.append(sub_item)

    with open("output.csv", "wb") as f:
        writer = csv.writer(f)
        writer.writerows(ips_dict)


if __name__ == "__main__":
    main()
