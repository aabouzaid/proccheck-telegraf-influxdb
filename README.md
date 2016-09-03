procCheck.py
============

You can read the full post here: [Monitor processes with Telegraf/InfluxDB/Kapacitor](http://tech.aabouzaid.com/2016/08/monitoring-processes-with-telegraf-influxdb-kapacitor-python.html).

Intro.
------
Python script checks list of processes based on process name or pattern and print output in InfluxDB format.

This script provides "blackbox" monitoring for processes, and with [Telegraf](https://github.com/influxdata/telegraf) ([exec](https://github.com/influxdata/telegraf/tree/master/plugins/inputs/exec) plugin) you can store processes' status in InfluxDB then process that data and get alerts via [Kapacitor](https://github.com/influxdata/kapacitor) using dead man's switch (alerts will be sent if no data for any of processes).

I created this script quickly till [procstat](https://github.com/influxdata/telegraf/tree/master/plugins/inputs/procstat) bug is fixed! It reports wrong PIDs, because [it caches the PIDs](https://github.com/influxdata/telegraf/issues/1636). (I'd like to fix it but since I don't really "Go" language, I cannot really help).


How doest it work?
------------------
Unlike "procstat" which uses "pgrep", I tried to make this script pure Python. And even I didn't use an external module like "[psutil](https://pypi.python.org/pypi/psutil)" which totally fits here (but also it's not a part of default system packages and it will need to be installed). But since I don't need most of its features and this script will run on Linux systems only, so that's ok for me right now.

You can monitor process based on "name" (i.e exec/bin name) and/or using a fixed pattern or even using regex! So it will work with Java apps too! In java apps (e.g. ZooKeeper, Kafka, etc), the binary name for all processes is just "java", and the real application shows as argument for that java process.


How to use it.
--------------
In "procList.yml" you will find 3 sections. First one is "byName" for procs name. Second one is "byString" in case you want to monitor a process based on its arguments. Finally "byRegex" where you can use regular expression to search.

```
# Process name.
byName:
  - sshd
  - vnc

# Fixed string.
byString:
  zookeeper: "org.apache.zookeeper.server.quorum.QuorumPeerMain"

# Regular expression.
byRegex:
  nginx_master: "nginx: master process .+nginx.+"
```

Output example:

```
procCheck,host=LinuxRocks,process_name=sshd,exe=sshd,pid=2814 host=LinuxRocks,process_name="sshd",exe="sshd",pid=2814,pattern="",matched_regex""
procCheck,host=LinuxRocks,process_name=zookeeper,exe=java,pid=3546 host=LinuxRocks,process_name="zookeeper",exe="java",pid=3546,pattern="org.apache.zookeeper.server.quorum.QuorumPeerMain",matched_regex""
procCheck,host=LinuxRocks,process_name=nginx_master,exe=nginx,pid=5798 host=LinuxRocks,process_name="nginx_master",exe="nginx",pid=5798,pattern="nginx: master process .+nginx.+",matched_regex"nginx: master process /usr/sbin/nginx -c /etc/nginx/nginx.conf"
```


Options
-------
You can set path of Yaml file that has processes list. Or set measurement name which will be used in Telegraf.

```
usage: procCheck.py [-h] [-f YML_FILE] [-n MEASUREMENT_NAME]

optional arguments:
  -h, --help            show this help message and exit
  -f YML_FILE, --yml-file YML_FILE
                        Path for processes list in YAML file.
                        (default: procList.yml)
  -n MEASUREMENT_NAME, --measurement-name MEASUREMENT_NAME
                        It will be used as measurement name in Telegraf.
                        (default: procCheck)
```


Telegraf config.
----------------
Here is a [Telegraf config](influxdb/telegraf_proccheck.conf) file to make this script works with via "exec" plugin.


Kapacitor script.
-----------------
With Kapacitor you can get alerts when any process is stopped. I wrote [TICK script](influxdb/kapacitor_proccheck.tick) uses dead man's switch, so you will get an alert when the monitored process is not there anymore.

It makes a batch queries (I think we don't need "stream" here), and if there is no data for any of monitored processes it will send and alert via "VictorOps".

Of course you can uses whatever you use for altering, just check supported services in alerting. And if it's not there you can consume that data using "HTTPOut".

About.
------
* **By:** Ahmed M. AbouZaid ([tech.aabouzaid.com](http://tech.aabouzaid.com/)).
* **Version:** v0.1 - August 2016.
* **License:**  GPL v2.0 or later.
