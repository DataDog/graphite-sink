#!/usr/bin/python

"""Generate graphite style metrics for testing metric conversion and ingestion. Forked from
   https://github.com/graphite-project/carbon/blob/master/examples/example-pickle-client.py"""

import random
import sys
import time
import socket
import pickle
import struct

# If using multiple sinks set to Haproxy ip and port
GRAPHITE_SINK = '127.0.0.1'
GRAPHITE_SINK_PORT = 17310
DELAY = 1
METRIC_LOAD = 1000

def generate_metrics():
    """Generate metric names.  Increase range(s) for higher cardinality"""
    d_list = ['dc_' + str(i) for i in range(5)]
    i_list = ['instance_' + str(i) for i in range(10)]
    t_list = [str(i) for i in range(100)]
    d_len = len(d_list)
    i_len = len(i_list)
    t_len = len(t_list)
    met_list = []
    for i in range(d_len * t_len * i_len):
        d_id = d_list[random.randint(0, d_len-1)]
        t_id = t_list[random.randint(0, t_len-1)]
        i_id = i_list[random.randint(0, i_len-1)]
        met = "myapp.prefix." + d_id + ".prod." + i_id + ".storage." + t_id + ".save.carbon"
        met_list.append(met)
    return met_list

def run(sock, delay, load):
    met_list = generate_metrics()
    m_len = len(met_list)
    count = 0
    while True:
        count += 1
        now = int(time.time())
        tuples = ([])
        lines = []
        loadavg = 1
        met = met_list[random.randint(0, m_len-1)]
        tuples.append((met, (now, loadavg)))
        lines.append("%s %s %d" % (met, loadavg, now))
        package = pickle.dumps(tuples, 1)
        size = struct.pack('!L', len(package))
        sock.sendall(size)
        sock.sendall(package)
        if count % load == 0:
            # create a new connection to allow load balancing
            time.sleep(delay)
            sock.close()
            sock = socket.socket()
            try:
                sock.connect((GRAPHITE_SINK, GRAPHITE_SINK_PORT))
            except socket.error:
                raise SystemExit("Couldn't connect to %(server)s on port %(port)d, is the server \
                                 running?" % {'server':GRAPHITE_SINK, 'port':GRAPHITE_SINK_PORT})

def main():
    delay = DELAY
    load = METRIC_LOAD
    for i, val in enumerate(sys.argv):
        if i == 1:
            if val.isdigit():
                delay = int(val)
            else:
                sys.stderr.write("Ignoring non-int argument. Using default delay: %ss\n" % delay)

        if i == 2:
            if val.isdigit():
                load = int(val)
            else:
                sys.stderr.write("Ignoring non-int argument. Using default load: %ss\n" % load)

    sock = socket.socket()
    try:
        sock.connect((GRAPHITE_SINK, GRAPHITE_SINK_PORT))
    except socket.error:
        raise SystemExit("Couldn't connect to %(server)s on port %(port)d, is the server \
                         running?" % {'server':GRAPHITE_SINK, 'port':GRAPHITE_SINK_PORT})

    try:
        run(sock, delay, load)
    except KeyboardInterrupt:
        sys.stderr.write("\nExiting on CTRL-c\n")
        sys.exit(0)

if __name__ == "__main__":
    main()
