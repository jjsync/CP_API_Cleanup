from __future__ import print_function
from threading import Thread
import Queue
import dns.reversename
import dns.resolver


class ReverseLookups:
    def __init__(self, thread_count, ip_list):
        self.thread_count = thread_count
        self.ip_list = ip_list
        # The queue of addresses to ping
        self.ips_q = Queue.Queue()
        # The queue of results
        self.out_q = Queue.Queue()
        # Resolver object
        self.resolver = dns.resolver.Resolver()
        self.resolver.timeout = 3
        self.resolver.lifetime = 3

    def lookups(self):
        """
        lookup function wrapper for threads
        :return: None
        """
        try:
            while True:
                # get an IP item from queue
                address = self.ips_q.get_nowait()

                rev_name = dns.reversename.from_address(address)
                try:
                    reversed_dns = str(self.resolver.query(rev_name, "PTR")[0])[:-1]
                    if reversed_dns:
                        self.out_q.put((address, reversed_dns))
                except dns.resolver.NXDOMAIN:
                    return False
                except dns.resolver.NoAnswer:
                    return False
                except dns.exception.Timeout:
                    return False
                except dns.resolver.NoNameservers:
                    return False
        except Queue.Empty:
            # No more addresses.
            pass
        finally:
            self.out_q.put(None)

    def start_lookups(self):
        """
        Thread function to perform reverse lookup of list of IP addresses
        :return: output queue as deque list (list of tuples)
        """
        # create the workers
        workers = []
        for i in range(self.thread_count):
            workers.append(Thread(target=self.lookups))

        # put all of the IPs in the ips_q queue
        for ip in self.ip_list:
            self.ips_q.put(ip)

        # Start all the workers
        for w in workers:
            w.daemon = True
            w.start()

        # wait until worker threads are done to exit
        for w in workers:
            w.join()

        return self.out_q.queue


if __name__ == '__main__':
    iplist = ['8.8.8.8', '8.8.4.4', '9.9.9.9', '172.217.10.68']
    iplookup = ReverseLookups(8, iplist)
    print(iplookup.start_lookups())
