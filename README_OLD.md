### Threaded graphite sink for converting and forwarding graphite / carbon metrics to Datadog.

This configures a single endpoint and is suitable for collecting < 1000 metrics / sec.  For collecting > 1000 metrics / sec see the multi-worker sink here: https://github.com/DataDog/graphite-sink-multi-worker 

### Step 0 - Datadog Agent

This assumes the Datadog Agent, including the dogstatsd service is running on your host.  The metric collector sends metrics to Datadog using dogstatsd.

For information on installing the client see here:  https://docs.datadoghq.com/guides/basic_agent_usage/

### Step 1 - Graphite sink(s)

```
git clone https://github.com/DataDog/graphite-sink
cd graphite-sink
sudo apt-get update
sudo apt-get install supervisor
sudo apt-get install python-pip
sudo pip install datadog
sudo pip install tornado
```

Navigate to the repo directory and edit graphite_sink.py, updating 'myapp.prefix' with the metric prefix you are sending to datadog.

#### To run from the cli for testing purposes:

`python graphite_sink.py 17310`

carbon_client.py is included to generate metrics with unique tags and send high throughput to the graphite_sink(s).  

#### To install as a service:

Edit /etc/supervisor/conf.d/supervisor.conf.  Add the following, updating 'numprocs'.
```
[program:graphite_sink]
command=python /exact/path/to/graphite-sink/graphite_sink.py 1731%(process_num)01d
process_name=%(program_name)s_%(process_num)01d
redirect_stdout=true
user=ubuntu
stdout_logfile=/var/log/graphite_sink-%(process_num)01d.log
numprocs=1
```

Update supervisor and restart all services.

```
sudo supervisorctl
update
restart all
```

### Step 2 - Your carbon-relay

Point your carbon relay at the graphite sink specified in step 2.

sink-hostname:17310  

There are different options for distributing carbon relay, whether set with destinations directly in the carbon config or using haproxy.

If using relay rules it is advantageous to send only the metrics you wish to see in datadog to the sinks.  For example:

```
[datadog]
pattern = ^myapp\.prefix.+
destinations = haproxy:port

[default]
default = true
destinations = 127.0.0.1:2004
```
