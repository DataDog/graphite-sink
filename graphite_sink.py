# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
from argparse import ArgumentParser
import cPickle as pickle
import logging
import threading
import time
import struct
import sys

from tornado.ioloop import IOLoop
from tornado.tcpserver import TCPServer
from tornado import netutil, process

from datadog import api, initialize, statsd

LOGGER = logging.getLogger(__name__)
OUT_HDLR = logging.StreamHandler(sys.stdout)
OUT_HDLR.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
OUT_HDLR.setLevel(logging.INFO)
LOGGER.addHandler(OUT_HDLR)
LOGGER.setLevel(logging.INFO)

METRIC_STORE = {}
METRIC_COUNT = 0
DELAY = 15  # Interval at which to aggregate and forward metrics
SEND_VIA_API = False

# Uncomment below to send via API.
# Best if you have < 100 unique metrics / tag combinations and don't want to install the agent

#from datadog import api, initialize
#SEND_VIA_API = True
#DD_API_KEY = os.getenv('DD_API_KEY', '<YOUR_API_KEY>')
#DD_APP_KEY = os.getenv('DD_APP_KEY', '<YOUR_APP_KEY>')
#
#options = {
#    'api_key': DD_API_KEY,
#    'app_key': DD_APP_KEY
#}
#
#initialize(**options)

def get_and_clear_store():
    global METRIC_STORE
    temp_store = METRIC_STORE.copy()
    METRIC_STORE = {}
    global METRIC_COUNT
    count = [METRIC_COUNT]
    METRIC_COUNT = 0
    return temp_store, count[0]


class GraphiteServer(TCPServer):

    def __init__(self, io_loop=None, ssl_options=None, **kwargs):
        TCPServer.__init__(self, io_loop=io_loop, ssl_options=ssl_options, **kwargs)
        self._send_metrics()

    def _send_metrics(self):
        temp_store, count = get_and_clear_store()
        all_metrics = []
        start_time = time.time()
        for metric, val in temp_store.iteritems():
            try:
                tags = []
                components = metric.split('.')

                # Customize to meet the format of you metric
                datacenter = 'datacenter:' + components.pop(2)
                env = 'env:' + components.pop(2)
                instance = 'instance:' + components.pop(2)
                tenant_id = 'tenant_id:' + components.pop(3)
                tags = [datacenter, env, instance, tenant_id]

                metric = '.'.join(components)
                all_metrics.append({'metric': metric, 'points': val, 'tags': tags})
            except Exception as ex:
                LOGGER.error(ex)
        if all_metrics:
            if SEND_VIA_API:
                api.Metric.send(all_metrics)
            else:
                for metric in all_metrics:
                    statsd.gauge(metric['metric'], metric['points'], tags=metric['tags'])
            LOGGER.info("sent %r metrics with %r unique names in %r seconds\n",
                        count, len(temp_store), time.time() - start_time)
        else:
            LOGGER.info("no metrics received")
        threading.Timer(DELAY, self._send_metrics).start()

    def handle_stream(self, stream, address):
        GraphiteConnection(stream, address)


class GraphiteConnection(object):

    def __init__(self, stream, address):
        LOGGER.info("received a new connection from %r", address)
        self.stream = stream
        self.address = address
        self.stream.set_close_callback(self._on_close)
        self.stream.read_bytes(4, self._on_read_header)

    def _on_read_header(self, data):
        try:
            size = struct.unpack("!L", data)[0]
            LOGGER.debug("Receiving a string of size: %r", size)
            self.stream.read_bytes(size, self._on_read_line)
        except Exception as ex:
            LOGGER.error(ex)

    def _on_read_line(self, data):
        LOGGER.debug('read a new line')
        self._decode(data)

    def _on_close(self):
        LOGGER.info('client quit')

    def _process_metric(self, metric, datapoint):
        # Update 'myapp.prefix' with the metric prefix you would like to send to Datadog.
        if metric is not None and metric.startswith('myapp.prefix'):
            global METRIC_COUNT
            METRIC_COUNT += 1
            try:
                val = datapoint[1]
                if metric in METRIC_STORE:
                    current = METRIC_STORE[metric]
                    new_val = current + val
                    METRIC_STORE[metric] = new_val
                else:
                    METRIC_STORE[metric] = val
            except Exception as ex:
                LOGGER.error(ex)

    def _decode(self, data):

        try:
            datapoints = pickle.loads(data)
        except Exception:
            LOGGER.exception("Cannot decode grapite points")
            return

        for (metric, datapoint) in datapoints:
            try:
                datapoint = (float(datapoint[0]), float(datapoint[1]))
            except Exception as ex:
                LOGGER.error(ex)
                continue

            self._process_metric(metric, datapoint)

        self.stream.read_bytes(4, self._on_read_header)


def start_graphite_listener(port):

    echo_server = GraphiteServer()
    echo_server.listen(port)
    IOLoop.instance().start()

if __name__ == '__main__':

    parser = ArgumentParser(description='run a tornado graphite sink')
    parser.add_argument('port', help='port num')
    args = parser.parse_args()
    port = args.port
    start_graphite_listener(port)
